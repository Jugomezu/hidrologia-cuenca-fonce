"""Precipitación mensual de IMERG promediada sobre cada cuenca del Fonce.

Toma la grilla de IMERG mensual ya descargada (data/imerg/imerg_mensual_col.npz, 1998-01 a 2022-12,
mm/mes) y la promedia sobre el polígono de cada estación, ponderando cada píxel de 0.1° por la
fracción de su área que cae dentro de la cuenca (sirve también para cuencas de 1-3 píxeles).

Es el mismo cálculo de scripts/historico/16_analisis_completo.py (función imerg_cuenca), aplicado solo a
las seis estaciones del Fonce.

Salida: out/imerg_mensual_fonce.csv   (columnas: periodo, id_estacion, p_imerg_mm)
"""
import numpy as np, pandas as pd, geopandas as gpd, shapely

ESTACIONES = [24027010, 24027070, 24027030, 24027050, 24027040, 24027060]
SHP = "data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/CAMELS_COL_catchments_boundaries.shp"

z = np.load("data/imerg/imerg_mensual_col.npz", allow_pickle=True)
P, LON, LAT, FECHAS = z["precip_mm_mes"], z["lon"], z["lat"], z["fechas"]
periodo = pd.PeriodIndex(FECHAS, freq="M")

lista = ",".join(f"'{i}'" for i in ESTACIONES)
g = gpd.read_file(SHP, where=f"IDEAM_CODE IN ({lista})")
g["id"] = g["IDEAM_CODE"].astype("int64")
g = g.to_crs(4326).set_index("id")

filas = []
for id_est in ESTACIONES:
    poly = shapely.simplify(g.loc[id_est, "geometry"], 0.002)         # ~200 m, irrelevante frente a píxeles de 11 km
    minx, miny, maxx, maxy = poly.bounds
    ii = np.flatnonzero((LON + .05 > minx) & (LON - .05 < maxx))
    jj = np.flatnonzero((LAT + .05 > miny) & (LAT - .05 < maxy))
    I, J = np.meshgrid(ii, jj, indexing="ij")
    celdas = shapely.box(LON[I] - .05, LAT[J] - .05, LON[I] + .05, LAT[J] + .05)
    shapely.prepare(poly)
    w = shapely.area(shapely.intersection(poly, celdas)); w = w / w.sum()
    serie = np.nansum(P[:, I, J] * w[None], axis=(1, 2))
    n_px = int((w > 0).sum())
    print(f"{id_est}: {n_px} píxeles que tocan la cuenca | media anual 1998-2022 = {serie.mean() * 12:.0f} mm")
    filas.append(pd.DataFrame({"periodo": periodo.astype(str), "id_estacion": id_est, "p_imerg_mm": serie.round(2)}))

out = pd.concat(filas, ignore_index=True)
out.to_csv("out/imerg_mensual_fonce.csv", index=False)
print(f"\nout/imerg_mensual_fonce.csv escrito: {len(out)} filas ({out.id_estacion.nunique()} estaciones × {out.periodo.nunique()} meses)")
