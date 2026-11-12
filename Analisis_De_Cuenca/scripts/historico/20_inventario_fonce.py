"""Inventario de los datos disponibles para el Rio Fonce (San Gil 24027010) y sus subcuencas.
Lee solo lo necesario (6 series, 1 poligono, el catalogo IDEAM y el npz de IMERG mensual).
Salida: out/fonce_inventario_estaciones.csv  y  resumen por consola."""
import numpy as np, pandas as pd, geopandas as gpd, shapely
from pathlib import Path

TS = Path("data/camels_col/hydromet/3_Hydrometeorological_data")
IDS = {24027010: "San Gil (madre, Fonce)", 24027070: "Merida (Fonce)", 24027030: "Nemizaque (Pienta)",
       24027050: "Puente Llano (Taquiza)", 24027040: "Puente Cabra (Mogoticos)", 24027060: "Puente Arco (Monchia)"}
m = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id")

# ---------------------------------------------------------------- 1. series diarias
print("=" * 78, "\n1. SERIES DIARIAS (CAMELS-COL, un archivo por cuenca)\n", "=" * 78, sep="")
rows = []
for g, n in IDS.items():
    d = pd.read_csv(TS / f"Hydromet_data_{g}.txt", sep="\t", encoding="latin-1")
    d.columns = ["date", "pr", "etp", "tmin", "tmax", "q"]
    d["date"] = pd.to_datetime(d["date"], format="%d/%m/%Y")
    q = d.dropna(subset=["q"])
    full = pd.date_range(d["date"].min(), d["date"].max())
    rows.append(dict(estacion=n, id=g, archivo_KB=round((TS / f"Hydromet_data_{g}.txt").stat().st_size / 1024),
                     dias_archivo=len(d), desde=d["date"].min().date(), hasta=d["date"].max().date(),
                     Q_dias=len(q), Q_desde=q["date"].min().date(), Q_hasta=q["date"].max().date(),
                     Q_faltante_pct=round(100 * (1 - len(q) / len(pd.date_range(q["date"].min(), q["date"].max()))), 2),
                     P_CHIRPS_nulos=int(d["pr"].isna().sum()), T_MSWX_nulos=int(d["tmin"].isna().sum()),
                     Qmedio_m3s=round(q["q"].mean(), 2), Qmin=round(q["q"].min(), 2), Qmax=round(q["q"].max(), 1)))
S = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_columns", 30)
print(S.to_string(index=False))

# ---------------------------------------------------------------- 2. atributos
print("\n" + "=" * 78, "\n2. ATRIBUTOS (CAMELS-COL, 90 columnas por cuenca; aqui las principales)\n", "=" * 78, sep="")
r = m.loc[24027010]
crude = (r["maximum_ele"] - r["minimum_ele"]) / (r["streng_chanel"] * 1000)
print(f"Area {r['area']:.0f} km2 | perimetro {r['perimeter']:.0f} km | Gravelius {r['gravelius_index']:.2f} | factor de forma {r['factor_form']:.2f}")
print(f"Cota min/media/max {r['minimum_ele']:.0f}/{r['mean_ele']:.0f}/{r['maximum_ele']:.0f} m | cauce principal {r['streng_chanel']:.1f} km | pendiente (H_max-H_min)/L = {crude:.4f}"
      f"  [equi_slope del archivo = {r['equi_slope']:.2e}: NO usar, ~700x menor]")
print(f"Curva numero {r['cn_catchment']:.1f} | aridez {r['aridity']:.2f} | dias secos/anio {r['low_prec_freq']:.0f} | dias de lluvia intensa/anio {r['high_prec_freq']:.1f}")
print(f"Firmas hidrologicas: q medio {r['q_mean']:.2f} mm/d | escorrentia {r['runoff_ratio']:.2f} | BFI {r['baseflow_index']:.2f} | pendiente FDC {r['slope_fdc']:.2f} | elasticidad {r['stream_elas']:.2f} | Q5 {r['Q5']:.2f} | Q95 {r['Q95']:.2f} mm/d")
for titulo, cols in [("Cobertura (MapBiomas 2022)", ["forest_perc", "nat_non_forest_form_perc", "agricul_livestock_perc", "non_vegeted_perc", "water_bodies_perc"]),
                     ("Litologia", ["unconso_depo_perc", "hypabyssal_rock_perc", "metamor_rock_perc", "plutonic_rock_perc", "sedimen_rock_perc", "volcaniclastic_rock_perc", "volcanic_rock_perc"]),
                     ("Suelos (IGAC)", [c for c in m.columns if c.endswith("_perc") and any(k in c for k in ("isols", "urban", "misce", "snow", "mine"))])]:
    v = r[cols].astype(float).sort_values(ascending=False)
    print(f"{titulo}: " + ", ".join(f"{k.replace('_perc', '')} {x:.0f}%" for k, x in v.items() if x >= 1))
luc = [c for c in m.columns if c.lower().startswith("class_")]
if luc:
    v = r[luc].astype(float).sort_values(ascending=False)
    print("Capacidad de uso de la tierra (IGAC): " + ", ".join(f"{k} {x:.0f}%" for k, x in v.items() if x >= 1))

# ---------------------------------------------------------------- 3. IMERG + CHIRPS + Q (climatologia)
print("\n" + "=" * 78, "\n3. PRECIPITACION: IMERG mensual (descargado) vs CHIRPS (en CAMELS-COL), y caudal\n", "=" * 78, sep="")
z = np.load("data/imerg/imerg_mensual_col.npz", allow_pickle=True)
P, LON, LAT, FE = z["precip_mm_mes"], z["lon"], z["lat"], z["fechas"]
g = gpd.read_file("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/CAMELS_COL_catchments_boundaries.shp", where="IDEAM_CODE = '24027010'").to_crs(4326)
poly = shapely.simplify(g.geometry.iloc[0], 0.002)
ii = np.flatnonzero((LON + .05 > poly.bounds[0]) & (LON - .05 < poly.bounds[2])); jj = np.flatnonzero((LAT + .05 > poly.bounds[1]) & (LAT - .05 < poly.bounds[3]))
I, J = np.meshgrid(ii, jj, indexing="ij")
cells = shapely.box(LON[I] - .05, LAT[J] - .05, LON[I] + .05, LAT[J] + .05); shapely.prepare(poly)
w = shapely.area(shapely.intersection(poly, cells)); npx = int((w > 0).sum()); w = w / w.sum()
pim = pd.Series(np.nansum(P[:, I, J] * w[None], axis=(1, 2)), index=pd.PeriodIndex(FE, freq="M"))
d = pd.read_csv(TS / "Hydromet_data_24027010.txt", sep="\t", encoding="latin-1"); d.columns = ["date", "pr", "etp", "tmin", "tmax", "q"]
d["date"] = pd.to_datetime(d["date"], format="%d/%m/%Y"); d = d.set_index("date")
pch = d["pr"].resample("ME").sum(min_count=25); pch.index = pch.index.to_period("M")
qm = d["q"].resample("ME").agg(["mean", "count"]); qmm = (qm["mean"] * 86400 * qm.index.days_in_month / (m.loc[24027010, "area"] * 1e6) * 1000).where(qm["count"] >= 25); qmm.index = qmm.index.to_period("M")
ven = slice(pd.Period("1998-01", "M"), pd.Period("2022-12", "M"))
print(f"IMERG toca {npx} pixeles de 0.1 grados en la cuenca; 300 meses (1998-01 a 2022-12) descargados")
print(f"Lluvia media anual 1998-2022:  IMERG {pim.loc[ven].mean() * 12:.0f} mm | CHIRPS {pch.loc[ven].mean() * 12:.0f} mm | caudal {qmm.loc[ven].mean() * 12:.0f} mm")
cl = pd.DataFrame({"IMERG_mm": pim.loc[ven], "CHIRPS_mm": pch.loc[ven], "Q_mm": qmm.loc[ven]})
cl = cl.groupby(cl.index.month).mean().round(0).astype(int).T
cl.columns = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
print(cl.to_string())
print(f"Temperatura MSWX (media de la cuenca, 1981-2022): tmin {d['tmin'].mean():.1f} C | tmax {d['tmax'].mean():.1f} C | ETP Hargreaves {d['etp'].mean():.2f} mm/d")

# ---------------------------------------------------------------- 4. estaciones IDEAM
print("\n" + "=" * 78, "\n4. ESTACIONES IDEAM (catalogo nacional) DENTRO DE LA CUENCA Y A <=10 km\n", "=" * 78, sep="")
c = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str)
c["lat"] = pd.to_numeric(c["latitud"], errors="coerce"); c["lon"] = pd.to_numeric(c["longitud"], errors="coerce"); c = c.dropna(subset=["lat", "lon"])
pts = gpd.GeoDataFrame(c, geometry=gpd.points_from_xy(c["lon"], c["lat"]), crs=4326)
dentro = pts[pts.within(g.geometry.iloc[0])].copy()
buf = g.to_crs(3395).buffer(10000).to_crs(4326).iloc[0]
cerca = pts[pts.within(buf) & ~pts.index.isin(dentro.index)]
dentro["nombre"] = dentro["nombre"].str.replace(r"\s*\[\d+\]$", "", regex=True)
print(f"Dentro: {len(dentro)} estaciones ({(dentro['estado'] == 'Activa').sum()} activas) | a <=10 km fuera del divisorio: {len(cerca)} mas")
print("Por tipo (dentro):", dentro["categoria"].value_counts().to_dict())
cols = ["codigo", "nombre", "categoria", "tecnologia", "estado", "municipio", "corriente", "altitud", "fecha_instalacion", "fecha_suspension"]
out = dentro[cols].sort_values(["categoria", "nombre"])
print(out.to_string(index=False))
out.to_csv("out/fonce_inventario_estaciones.csv", index=False)
