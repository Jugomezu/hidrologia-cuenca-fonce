"""Analisis PRELIMINAR y liviano con los criterios v2.

No carga el shapefile ni hace geometria. Usa:
  - out/camels_col_master.csv (metadatos ya calculados)
  - lectura secuencial, una cuenca a la vez, de las series diarias SOLO de las
    cuencas que pasan el filtro de metadatos
  - catalogo IDEAM para nombres y para un indicador aproximado de subcuencas

Lo que queda para la fase pesada (geometria real):
  - anidamiento exacto (aforo dentro del poligono)
  - pixeles IMERG exactos por cuenca
Aqui se reportan aproximaciones marcadas como tales.

Salida: out/preliminar_v2.csv
"""
import pandas as pd, numpy as np
from pathlib import Path

TS = Path("data/camels_col/hydromet/3_Hydrometeorological_data")
IMERG0 = pd.Timestamp("1998-01-01")
PX_KM2 = 123.0                       # area de un pixel IMERG 0.1 deg cerca del ecuador

m = pd.read_csv("out/camels_col_master.csv")

# ---- 1. filtro de metadatos (sin leer series) --------------------------
f1 = (m["area"].between(100, 10000)
      & (m["n_years_obs"] >= 25)
      & (m["missing_pct"] <= 10))
c = m[f1].copy()
print(f"346 cuencas -> {len(c)} pasan area 100-10k, >=25 anios, <=10% faltantes (metadatos)\n")

# ---- 2. series diarias, una a la vez ------------------------------------
def stats(gid):
    d = pd.read_csv(TS / f"Hydromet_data_{gid}.txt", sep="\t", encoding="latin-1",
                    usecols=[0, 1, 3, 5])
    d.columns = ["date", "pr", "tmin", "q"]
    d["date"] = pd.to_datetime(d["date"], format="%d/%m/%Y")
    obs = d.loc[d["q"].notna(), "date"].sort_values().to_numpy()
    t0, t1 = obs[0], obs[-1]
    span = (t1 - t0).astype("timedelta64[D]").astype(int) + 1
    gaps = np.diff(obs).astype("timedelta64[D]").astype(int) - 1
    wi = obs[obs >= np.datetime64(IMERG0)]
    if len(wi):
        span_i = (wi[-1] - wi[0]).astype("timedelta64[D]").astype(int) + 1
        gaps_i = np.diff(wi).astype("timedelta64[D]").astype(int) - 1
    else:
        span_i, gaps_i = 0, np.array([0])
    inrec = d[(d["date"] >= t0) & (d["date"] <= t1)]
    return dict(
        gauge_id=gid,
        q_start=pd.Timestamp(t0).date(), q_end=pd.Timestamp(t1).date(),
        q_years=len(obs) / 365.25,
        q_miss=100 * (1 - len(obs) / span),
        q_gap_max=int(gaps.max()) if len(gaps) else 0,
        q_gaps_gt90=int((gaps > 90).sum()),
        pr_miss=100 * inrec["pr"].isna().mean(),
        t_miss=100 * inrec["tmin"].isna().mean(),
        imerg_q_years=len(wi) / 365.25,
        imerg_q_miss=100 * (1 - len(wi) / span_i) if span_i else np.nan,
        imerg_gap_max=int(gaps_i.max()) if len(gaps_i) else 0,
    )

rows = [stats(int(g)) for g in c["gauge_id"]]
s = pd.DataFrame(rows)
c = c.merge(s, on="gauge_id")

# ---- 3. nombres y proxy de subcuencas -----------------------------------
cne = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str,
                  usecols=["codigo", "nombre", "corriente", "municipio",
                           "subzona_hidrografica", "estado"])
cne["gauge_id"] = cne["codigo"].str.lstrip("0").astype("int64")
cne["nombre"] = cne["nombre"].str.replace(r"\s*\[\d+\]$", "", regex=True).str.strip()
cne = cne.drop_duplicates("gauge_id").set_index("gauge_id")
for col in ["nombre", "corriente", "municipio", "subzona_hidrografica", "estado"]:
    c[col] = c["gauge_id"].map(cne[col])

# Proxy de anidamiento (APROXIMADO): otras estaciones CAMELS-COL en la misma
# subzona IDEAM (primeros 4 digitos del codigo) con area menor y elevacion de
# aforo mayor, es decir, aguas arriba. Se confirma con geometria en la fase pesada.
mm = m.assign(sz=m["gauge_id"].astype(str).str.zfill(8).str[:4])
c["sz"] = c["gauge_id"].astype(str).str.zfill(8).str[:4]
def posibles_sub(r):
    o = mm[(mm["sz"] == r["sz"]) & (mm["gauge_id"] != r["gauge_id"])
           & (mm["area"] < 0.85 * r["area"]) & (mm["area"] > 0.02 * r["area"])
           & (mm["gauge_elev"] > r["gauge_elev"])]
    return pd.Series({"sub_aprox_n": len(o),
                      "sub_aprox": ";".join(o["gauge_id"].astype(str).head(6))})
c = c.join(c.apply(posibles_sub, axis=1))

c["imerg_px_aprox"] = c["area"] / PX_KM2

# ---- 4. filtros sobre las series y puntaje -------------------------------
f2 = ((c["q_miss"] <= 10) & (c["pr_miss"] <= 10) & (c["q_gap_max"] <= 365))
print("Sobre las series diarias:")
print(f"  faltantes Q <= 10%       : {int((c.q_miss <= 10).sum())}")
print(f"  faltantes P <= 10%       : {int((c.pr_miss <= 10).sum())}")
print(f"  hueco maximo <= 365 d    : {int((c.q_gap_max <= 365).sum())}")
print(f"  pasan los tres           : {int(f2.sum())}\n")

def nz(x, lo, hi, inv=False):
    v = ((x - lo) / (hi - lo)).clip(0, 1)
    return 1 - v if inv else v
c["score"] = (0.16 * nz(c["q_years"], 25, 42)
              + 0.18 * nz(c["imerg_q_years"], 15, 25)
              + 0.16 * nz(c["q_miss"], 0, 10, inv=True)
              + 0.18 * nz(c["q_gap_max"], 30, 365, inv=True)
              + 0.16 * (c["sub_aprox_n"].clip(0, 3) / 3)
              + 0.08 * nz(c["imerg_px_aprox"], 1, 25)
              + 0.08 * (pd.to_datetime(c["q_end"]) >= pd.Timestamp("2022-01-01")))
c["pasa_series"] = f2
c = c.sort_values(["pasa_series", "score"], ascending=[False, False])
c.to_csv("out/preliminar_v2.csv", index=False)

pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 22)
cols = ["gauge_id", "nombre", "corriente", "gauge_department", "area",
        "imerg_px_aprox", "q_years", "imerg_q_years", "q_miss", "q_gap_max",
        "sub_aprox_n", "q_end", "score"]
print("=== TOP 25 (pasan todos los filtros) ===")
print(c[c.pasa_series][cols].head(25).round(1).to_string(index=False))
print("\n=== con posibles subcuencas (aprox.) ===")
print(c[c.pasa_series & (c.sub_aprox_n >= 1)][cols + ["sub_aprox"]]
      .head(20).round(1).to_string(index=False))
print("\nregion:", c[c.pasa_series]["region"].value_counts().to_dict())
