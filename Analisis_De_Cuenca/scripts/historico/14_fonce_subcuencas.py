"""Calidad de las subcuencas del Rio Fonce (madre: San Gil, 24027010).

Liviano: lee solo los poligonos de la subzona 2402 (filtro al abrir el
shapefile) y solo las series de esas estaciones.

Evalua, para cada estacion CAMELS-COL de la subzona:
  1. anidamiento REAL (aforo dentro del poligono de la madre) y fraccion de area
  2. calidad del registro: anios, faltantes, hueco maximo, huecos > 90 d,
     dias en valores repetidos (flatline), fecha final, tipo de estacion
  3. solape con la madre: dias en comun y anios completos en comun
  4. consistencia con la madre: correlacion diaria, fraccion de dias con
     Q_sub > Q_madre (imposible si esta anidada), caudal especifico
  5. firmas y coherencia P-Q estacional con CHIRPS (informativa)

Salida: out/fonce_subcuencas.csv
"""
import geopandas as gpd, pandas as pd, numpy as np, shapely
from pathlib import Path

TS = Path("data/camels_col/hydromet/3_Hydrometeorological_data")
SHP = ("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/"
       "CAMELS_COL_catchments_boundaries.shp")
MADRE = 24027010
IMERG0 = pd.Timestamp("1998-01-01")

m = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id")
sz = m.index.astype(str).str.zfill(8).str[:4]
ids = [int(g) for g in m.index[sz == "2402"]]
print("estaciones CAMELS-COL en la subzona 2402 (Rio Fonce):", ids)

# ---- poligonos: solo los de la subzona -------------------------------------
lista = ",".join(str(i) for i in ids)
try:
    g = gpd.read_file(SHP, where=f"IDEAM_CODE IN ({lista})")
except Exception:
    lista_s = ",".join(f"'{i}'" for i in ids)
    g = gpd.read_file(SHP, where=f"IDEAM_CODE IN ({lista_s})")
g["gauge_id"] = g["IDEAM_CODE"].astype("int64")
g = g.to_crs(4326).set_index("gauge_id")
a_km2 = g.to_crs(3395).geometry.area / 1e6
madre_geom = g.loc[MADRE, "geometry"]

# ---- series ----------------------------------------------------------------
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

dm = load(MADRE)
qm = dm["q"].dropna()
area_m = m.loc[MADRE, "area"]
to_mm = lambda q, A: q * 86400 / (A * 1e6) * 1000

cne = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str,
                  usecols=["codigo", "nombre", "corriente", "municipio",
                           "categoria", "estado"])
cne["gauge_id"] = cne["codigo"].str.lstrip("0").astype("int64")
cne["nombre"] = cne["nombre"].str.replace(r"\s*\[\d+\]$", "", regex=True).str.strip()
cne = cne.drop_duplicates("gauge_id").set_index("gauge_id")

rows = []
for gid in ids:
    d = load(gid); q = d["q"].dropna()
    fechas = q.index.to_numpy()
    span = (fechas[-1] - fechas[0]).astype("timedelta64[D]").astype(int) + 1
    gaps = np.diff(fechas).astype("timedelta64[D]").astype(int) - 1
    lon, lat = m.loc[gid, "lon_wgs84"], m.loc[gid, "lat_wgs84"]
    anidada = bool(shapely.contains_xy(madre_geom, lon, lat)) and gid != MADRE
    frac = a_km2[gid] / a_km2[MADRE]

    # solape y consistencia con la madre
    j = pd.concat([q.rename("s"), qm.rename("m")], axis=1).dropna()
    yrs_comun = j.resample("YE").size()
    area_s = m.loc[gid, "area"]
    qs_mm, qm_mm = to_mm(j["s"], area_s), to_mm(j["m"], area_m)

    # fase estacional P-Q con CHIRPS
    cl = d.dropna().groupby(d.dropna().index.month)[["pr", "q"]].mean()

    rows.append(dict(
        gauge_id=gid,
        nombre=cne.loc[gid, "nombre"] if gid in cne.index else "",
        rio=cne.loc[gid, "corriente"] if gid in cne.index else "",
        municipio=cne.loc[gid, "municipio"] if gid in cne.index else "",
        tipo=cne.loc[gid, "categoria"] if gid in cne.index else "",
        estado=cne.loc[gid, "estado"] if gid in cne.index else "",
        area=area_s, frac_madre=frac if gid != MADRE else 1.0,
        anidada=("MADRE" if gid == MADRE else ("si" if anidada else "NO")),
        inicio=q.index.min().date(), fin=q.index.max().date(),
        anios=len(q) / 365.25,
        falt=100 * (1 - len(q) / span),
        hueco_max=int(gaps.max()) if len(gaps) else 0,
        huecos_90d=int((gaps > 90).sum()),
        flat=flat_pct(q),
        anios_imerg=(q.index >= IMERG0).sum() / 365.25,
        dias_comun=len(j),
        anios_comun_ok=int((yrs_comun >= 330).sum()),
        r_diaria=j["s"].corr(j["m"]) if gid != MADRE else np.nan,
        pct_Qsub_mayor=(100 * (j["s"] > j["m"]).mean()) if gid != MADRE else np.nan,
        q_esp_mmd=qs_mm.mean(),
        q_esp_madre=qm_mm.mean(),
        RR=m.loc[gid, "runoff_ratio"], BFI=m.loc[gid, "baseflow_index"],
        fase_chirps=np.corrcoef(cl["pr"], cl["q"])[0, 1],
        bosque=m.loc[gid, "forest_perc"], agro=m.loc[gid, "agricul_livestock_perc"],
        urbano=m.loc[gid, "urban_perc"],
    ))

r = pd.DataFrame(rows).sort_values("area", ascending=False)

# anidamiento entre las propias subcuencas (quien contiene a quien)
contiene = {}
for a in r.gauge_id:
    ga = g.loc[a, "geometry"]
    hijos = [b for b in r.gauge_id if b != a and m.loc[b, "area"] < m.loc[a, "area"]
             and shapely.contains_xy(ga, m.loc[b, "lon_wgs84"], m.loc[b, "lat_wgs84"])]
    contiene[a] = hijos
r["contiene"] = r.gauge_id.map(lambda a: ";".join(str(x) for x in contiene[a]))

r.to_csv("out/fonce_subcuencas.csv", index=False)

pd.set_option("display.width", 260, "display.max_columns", 40, "display.max_colwidth", 22)
print("\n=== REGISTRO ===")
print(r[["gauge_id", "nombre", "rio", "tipo", "estado", "area", "frac_madre", "anidada",
         "inicio", "fin", "anios", "falt", "hueco_max", "huecos_90d", "flat",
         "anios_imerg"]].round(2).to_string(index=False))
print("\n=== CONSISTENCIA CON LA MADRE (San Gil) ===")
print(r[["gauge_id", "rio", "dias_comun", "anios_comun_ok", "r_diaria",
         "pct_Qsub_mayor", "q_esp_mmd", "q_esp_madre", "RR", "BFI",
         "fase_chirps", "bosque", "agro", "urbano", "contiene"]].round(2).to_string(index=False))
