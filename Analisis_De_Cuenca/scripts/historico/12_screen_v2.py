"""Tamizaje v2 — criterios definidos por el usuario (2026-09-18):

  1. >= 25 anios de registro (preferiblemente mas)
  2. <= 10% de datos diarios faltantes POR VARIABLE
  3. sin tramos muy largos sin datos
  4. PLUS: que existan subcuencas anidadas con datos
  5. temperatura no obligatoria (se puede suplir con ERA5)
  6. area entre 100 y 10.000 km2
  7. precipitacion IMERG disponible para la cuenca
  8. si es Colombia, idealmente con POMCA

El tamanio NO se usa como filtro duro por resolucion IMERG: el usuario solo
necesita una serie promedio por cuenca, asi que se reporta el numero de pixeles
como informacion y se pondera suavemente.
"""
import pandas as pd, numpy as np
from pathlib import Path

pd.set_option("display.width", 260, "display.max_columns", 60)
m = pd.read_csv("out/master_v2.csv")

# ---- nombres de estacion / rio -------------------------------------------
cne = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str)
cne["gauge_id"] = cne["codigo"].str.lstrip("0").astype("int64")
cne["nombre"] = cne["nombre"].str.replace(r"\s*\[\d+\]$", "", regex=True).str.strip()
cne = cne.drop_duplicates("gauge_id").set_index("gauge_id")
for c in ["nombre", "corriente", "municipio", "subzona_hidrografica",
          "categoria", "estado"]:
    m[c] = m["gauge_id"].map(cne[c])

# ---- filtros duros --------------------------------------------------------
MAXGAP = 365          # "sin tramos muy largos": > 1 anio continuo se descarta
F = {
  "area 100-10.000 km2":      m["area"].between(100, 10000),
  ">= 25 anios de registro":  m["yrs_full"] >= 25,
  "faltantes Q <= 10%":       m["miss_q_full"] <= 10,
  "faltantes P <= 10%":       m["miss_pr"] <= 10,
  "hueco maximo <= 365 d":    m["gap_q_full"] <= MAXGAP,
  "registro llega a >=2015":  pd.to_datetime(m["end_obs"]) >= pd.Timestamp("2015-01-01"),
}
F = {k: v.fillna(False) for k, v in F.items()}

print(f"Punto de partida: {len(m)} cuencas CAMELS-COL\n")
print("Filtro                          | falla | solo-el | sobreviven-sin-el")
print("-" * 72)
allp = pd.Series(True, index=m.index)
for v in F.values(): allp &= v
for k, v in F.items():
    otros = pd.Series(True, index=m.index)
    for k2, v2 in F.items():
        if k2 != k: otros &= v2
    print(f"{k:<31s} | {int((~v).sum()):>5d} | {int((otros & ~v).sum()):>7d} | {int(otros.sum()):>17d}")
print("-" * 72)
print(f"{'PASAN TODOS':<31s} | {int(allp.sum()):>5d}\n")

c = m[allp].copy()

# ---- puntuacion -----------------------------------------------------------
def nz(s, lo, hi, inv=False):
    v = ((s - lo) / (hi - lo)).clip(0, 1)
    return 1 - v if inv else v

c["p_anios"]   = nz(c["yrs_full"], 25, 42)                 # mas es mejor
c["p_imerg"]   = nz(c["yrs_imerg"], 15, 25)                # solape con IMERG
c["p_faltaQ"]  = nz(c["miss_q_full"], 0, 10, inv=True)
c["p_hueco"]   = nz(c["gap_q_full"], 30, 365, inv=True)
c["p_sub"]     = c["n_sub"].clip(0, 3) / 3                 # PLUS: subcuencas
c["p_px"]      = nz(c["imerg_px"], 1, 25)                  # pixeles IMERG (suave)
c["p_reciente"]= (pd.to_datetime(c["end_obs"]) >= pd.Timestamp("2022-01-01")).astype(float)

W = {"p_anios":.16, "p_imerg":.18, "p_faltaQ":.16, "p_hueco":.18,
     "p_sub":.16, "p_px":.08, "p_reciente":.08}
c["score"] = sum(c[k] * w for k, w in W.items())
c = c.sort_values("score", ascending=False)
c.to_csv("out/candidatos_v2.csv", index=False)

cols = ["gauge_id", "nombre", "corriente", "gauge_department", "area", "imerg_px",
        "yrs_full", "yrs_imerg", "miss_q_full", "gap_q_full", "n_sub",
        "end_obs", "estado", "score"]
print("=== TOP 25 ===\n")
sh = c[cols].head(25).copy()
sh["end_obs"] = sh["end_obs"].astype(str).str[:10]
print(sh.round(2).to_string(index=False))

print("\n=== CON SUBCUENCAS ANIDADAS (el 'plus') ===\n")
sub = c[c.n_sub >= 1][["gauge_id", "nombre", "corriente", "gauge_department",
                       "area", "imerg_px", "yrs_full", "miss_q_full",
                       "gap_q_full", "n_sub", "subs", "sub_frac", "score"]]
print(sub.head(20).round(2).to_string(index=False))
print(f"\ncandidatos con >=1 subcuenca: {len(sub)} de {len(c)}")
