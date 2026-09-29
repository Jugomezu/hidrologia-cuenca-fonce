"""Analisis completo sobre las cuencas prefiltradas (out/preliminar_v2.csv, pasa_series).

Integra:
  A. Geometria exacta (out/geometria.csv): subcuencas anidadas y pixeles IMERG.
  B. Calidad de las subcuencas: cuantas tienen a su vez un registro util.
  C. IMERG mensual promediado por cuenca, ponderando cada pixel por la fraccion
     de su area dentro de la cuenca (sirve tambien para cuencas de 1-2 pixeles).
  D. Coherencia P-Q con IMERG vs CHIRPS: fase estacional, correlacion mensual,
     coeficiente de escorrentia anual y su estabilidad.
  E. QC adicional de la serie de caudal: flatline y cambio de escalon.
  F. Indicadores de intervencion humana.

Salida: out/analisis_completo.csv
"""
import geopandas as gpd, pandas as pd, numpy as np, shapely
from scipy.stats import spearmanr
from pathlib import Path

TS = Path("data/camels_col/hydromet/3_Hydrometeorological_data")
SHP = ("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/"
       "CAMELS_COL_catchments_boundaries.shp")

import os
TODAS = os.environ.get("ANALISIS_TODAS") == "1"   # 1 = las 174 que pasan metadatos (no solo las 134)
SALIDA = "out/analisis_174.csv" if TODAS else "out/analisis_completo.csv"
pre = pd.read_csv("out/preliminar_v2.csv")
pre = pre if TODAS else pre[pre["pasa_series"]].copy()
geo = pd.read_csv("out/geometria.csv").set_index("gauge_id")
m = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id")
ids = pre["gauge_id"].astype(int).tolist()
print(f"cuencas prefiltradas: {len(ids)}")

# ---------- A/B. subcuencas exactas y su calidad --------------------------
def sub_ok(s):
    if s not in m.index:
        return False
    r = m.loc[s]
    return (r["n_years_obs"] >= 20) and (r["missing_pct"] <= 10)

def subs_info(g):
    if g not in geo.index or pd.isna(geo.loc[g, "subs"]) or geo.loc[g, "subs"] == "":
        return pd.Series({"n_sub": 0, "n_sub_ok": 0, "subs": "", "sub_frac": ""})
    ss = [int(x) for x in str(geo.loc[g, "subs"]).split(";") if x]
    ok = [s for s in ss if sub_ok(s)]
    return pd.Series({"n_sub": len(ss), "n_sub_ok": len(ok),
                      "subs": geo.loc[g, "subs"], "sub_frac": geo.loc[g, "sub_frac"]})

pre = pre.drop(columns=[c for c in ["n_sub", "subs", "sub_frac"] if c in pre.columns])
pre = pre.join(pre["gauge_id"].apply(subs_info))
pre["imerg_px"] = pre["gauge_id"].map(geo["imerg_px"])

# ---------- C. IMERG promediado por cuenca --------------------------------
z = np.load("data/imerg/imerg_mensual_col.npz", allow_pickle=True)
P, LON, LAT, FECHAS = z["precip_mm_mes"], z["lon"], z["lat"], z["fechas"]
fidx = pd.PeriodIndex(FECHAS, freq="M")
dlon, dlat = 0.1, 0.1

lista = ",".join(str(i) for i in ids)
try:
    g = gpd.read_file(SHP, where=f"IDEAM_CODE IN ({lista})")
except Exception:
    g = gpd.read_file(SHP, where="IDEAM_CODE IN (" + ",".join(f"'{i}'" for i in ids) + ")")
g["gauge_id"] = g["IDEAM_CODE"].astype("int64")
g = g.to_crs(4326).set_index("gauge_id")

def imerg_cuenca(poly):
    poly = shapely.simplify(poly, 0.002)            # ~200 m; irrelevante frente a 11 km
    minx, miny, maxx, maxy = poly.bounds
    ii = np.flatnonzero((LON + dlon / 2 > minx) & (LON - dlon / 2 < maxx))
    jj = np.flatnonzero((LAT + dlat / 2 > miny) & (LAT - dlat / 2 < maxy))
    if len(ii) == 0 or len(jj) == 0:
        return None, 0.0
    I, J = np.meshgrid(ii, jj, indexing="ij")
    cells = shapely.box(LON[I] - dlon / 2, LAT[J] - dlat / 2,
                        LON[I] + dlon / 2, LAT[J] + dlat / 2)
    shapely.prepare(poly)
    w = shapely.area(shapely.intersection(poly, cells))
    cob = w.sum() / poly.area                        # fraccion de la cuenca cubierta por el recorte
    w = w / w.sum()
    serie = np.nansum(P[:, I, J] * w[None, :, :], axis=(1, 2))
    return pd.Series(serie, index=fidx), cob

# ---------- D/E. series ----------------------------------------------------
def load(gid):
    d = pd.read_csv(TS / f"Hydromet_data_{gid}.txt", sep="\t", encoding="latin-1",
                    usecols=[0, 1, 5])
    d.columns = ["date", "pr", "q"]
    d["date"] = pd.to_datetime(d["date"], format="%d/%m/%Y")
    return d.set_index("date").sort_index()

def flat_pct(q, n=7):
    s = q.dropna()
    grp = (s != s.shift()).cumsum()
    size = s.groupby(grp).transform("size")
    return 100 * ((size >= n) & (s > 0)).sum() / len(s)

def coherencia(Pm, Qm):
    """Pm, Qm en mm/mes, mismo indice mensual, solo meses validos."""
    df = pd.concat([Pm.rename("p"), Qm.rename("q")], axis=1).dropna()
    if len(df) < 60:
        return dict(fase=np.nan, lag_opt=np.nan, r_mes=np.nan, rr=np.nan, rr_cv=np.nan)
    cl = df.groupby(df.index.month).mean()
    fase = np.corrcoef(cl["p"], cl["q"])[0, 1]
    lags = {L: np.corrcoef(np.roll(cl["p"].values, L), cl["q"].values)[0, 1] for L in range(0, 3)}
    lag_opt = max(lags, key=lags.get)
    r_mes = spearmanr(df["p"], df["q"]).statistic
    an = df.groupby(df.index.year).agg(p=("p", "sum"), q=("q", "sum"), n=("p", "size"))
    an = an[an["n"] == 12]
    rr = an["q"] / an["p"]
    return dict(fase=fase, lag_opt=lag_opt, r_mes=r_mes,
                rr=an["q"].sum() / an["p"].sum() if len(an) else np.nan,
                rr_cv=rr.std() / rr.mean() if len(an) > 4 else np.nan)

rows = []
for n, gid in enumerate(ids, 1):
    area = m.loc[gid, "area"]
    d = load(gid)
    q = d["q"]
    # caudal mensual en mm/mes, solo meses con >= 25 dias
    qm = q.resample("ME").agg(["mean", "count"])
    dias = qm.index.days_in_month
    qmm = (qm["mean"] * 86400 * dias / (area * 1e6) * 1000).where(qm["count"] >= 25)
    qmm.index = qmm.index.to_period("M")
    pch = d["pr"].resample("ME").sum(min_count=25)
    pch.index = pch.index.to_period("M")

    pim, cob = (None, 0.0)
    if gid in g.index:
        pim, cob = imerg_cuenca(g.loc[gid, "geometry"])
    ci = coherencia(pim, qmm) if pim is not None else dict(fase=np.nan, lag_opt=np.nan,
                                                            r_mes=np.nan, rr=np.nan, rr_cv=np.nan)
    ven = slice(pd.Period("1998-01", "M"), pd.Period("2022-12", "M"))
    cc = coherencia(pch.loc[ven], qmm.loc[ven])       # CHIRPS en la misma ventana

    obs = q.dropna()
    mid = obs.index[0] + (obs.index[-1] - obs.index[0]) / 2
    q1, q2 = obs[:mid], obs[mid:]
    rows.append(dict(
        gauge_id=gid, imerg_cobertura=cob,
        P_imerg_anual=pim.loc[ven].mean() * 12 if pim is not None else np.nan,
        P_chirps_anual=pch.loc[ven].mean() * 12,
        fase_imerg=ci["fase"], lag_imerg=ci["lag_opt"], r_mes_imerg=ci["r_mes"],
        RR_imerg=ci["rr"], RRcv_imerg=ci["rr_cv"],
        fase_chirps=cc["fase"], r_mes_chirps=cc["r_mes"], RR_chirps=cc["rr"],
        flat=flat_pct(q), escalon=100 * (q2.mean() - q1.mean()) / q1.mean(),
    ))
    if n % 20 == 0:
        print(f"  {n}/{len(ids)}", flush=True)

res = pd.DataFrame(rows)
a = pre.merge(res, on="gauge_id")

# ---------- F. banderas -----------------------------------------------------
def banderas(r):
    b = []
    if r["urban_perc"] >= 2: b.append("urbano>=2%")
    if r["water_bodies_perc"] >= 1.5: b.append("embalse?")
    if r["RR_imerg"] > 1.0: b.append("RR_IMERG>1")
    if r["RR_imerg"] < 0.15: b.append("RR_IMERG<0.15")
    if r["fase_imerg"] < 0.5: b.append("fase_IMERG<0.5")
    if r["RRcv_imerg"] > 0.30: b.append("RR_inestable")
    if abs(r["escalon"]) > 25: b.append("escalon>25%")
    if r["flat"] > 5: b.append("flatline>5%")
    if r["imerg_cobertura"] < 0.98: b.append("fuera_recorte_IMERG")
    return ";".join(b)
a["banderas"] = a.apply(banderas, axis=1)
a["n_banderas"] = a["banderas"].str.count(";") + (a["banderas"] != "").astype(int)

# ---------- puntaje ----------------------------------------------------------
def nz(x, lo, hi, inv=False):
    v = ((x - lo) / (hi - lo)).clip(0, 1)
    return 1 - v if inv else v

a["s_registro"] = (0.35 * nz(a["q_years"], 25, 42) + 0.35 * nz(a["q_miss"], 0, 10, inv=True)
                   + 0.30 * nz(a["q_gap_max"], 30, 365, inv=True))
a["s_subcuencas"] = a["n_sub_ok"].clip(0, 3) / 3
a["s_imerg"] = (0.40 * nz(a["fase_imerg"], 0.3, 0.95) + 0.30 * nz(a["r_mes_imerg"], 0.3, 0.85)
                + 0.30 * nz(a["RRcv_imerg"], 0.10, 0.35, inv=True))
a["s_balance"] = 1 - ((a["RR_imerg"] - 0.55).abs() / 0.45).clip(0, 1)
a["s_natural"] = (nz(a["urban_perc"], 0, 2, inv=True) * nz(a["water_bodies_perc"], 0, 1.5, inv=True))
a["score"] = (0.25 * a["s_registro"] + 0.20 * a["s_subcuencas"] + 0.25 * a["s_imerg"]
              + 0.15 * a["s_balance"] + 0.15 * a["s_natural"])
a = a.sort_values("score", ascending=False)
a.to_csv(SALIDA, index=False)

pd.set_option("display.width", 280, "display.max_columns", 40, "display.max_colwidth", 20)
cols = ["gauge_id", "nombre", "corriente", "gauge_department", "area", "imerg_px",
        "q_years", "q_miss", "q_gap_max", "n_sub", "n_sub_ok", "fase_imerg", "fase_chirps",
        "r_mes_imerg", "RR_imerg", "RRcv_imerg", "banderas", "score"]
print("\n=== TOP 30 ===")
print(a[cols].head(30).round(2).to_string(index=False))
print("\n=== IMERG vs CHIRPS (todas las prefiltradas) ===")
print(a[["fase_imerg", "fase_chirps", "r_mes_imerg", "r_mes_chirps",
         "RR_imerg", "RR_chirps"]].describe().round(2).to_string())
print("\nfase < 0.5  -> IMERG:", int((a.fase_imerg < 0.5).sum()),
      "| CHIRPS:", int((a.fase_chirps < 0.5).sum()))
print("RR > 1      -> IMERG:", int((a.RR_imerg > 1).sum()),
      "| CHIRPS:", int((a.RR_chirps > 1).sum()))
print("\nsin banderas:", int((a.n_banderas == 0).sum()), "de", len(a))
