"""PL con un método espacial: polígonos de Thiessen y corrección por altura (prueba de sensibilidad).

PL, la lluvia de los pluviómetros, es el promedio simple de las estaciones que caen dentro de la divisoria y tienen
dato ese mes (regla 11). Las 7 estaciones están entre 1 300 y 2 625 m, la cuenca llega a 4 297 m, y según IMERG
llueve menos arriba: el promedio simple puede no representar la lluvia de toda la cuenca. Este script mide cuánto
cambia PL con dos métodos espaciales usuales. No reemplaza a PL: es una prueba de sensibilidad.

1. THIESSEN (Thiessen, 1911). Cada punto de la cuenca toma la lluvia del pluviómetro más cercano: la cuenca se
   parte en polígonos de Voronoi alrededor de las estaciones, recortados con la divisoria, y cada estación pesa
   según el área de su polígono. Como no todas las estaciones tienen dato todos los meses, los polígonos se
   rehacen para cada combinación de estaciones presentes; nada se rellena.
2. THIESSEN CON CORRECCIÓN POR ALTURA. La lluvia de cada estación se lleva a la altura media de su polígono con la
   recta de lluvia contra altura de IMERG (09_gradiente_altitudinal.py: P = a + b·z, con b = -222 mm/año por cada
   1 000 m, r² = 0.83 en 30 celdas). Se usa la de IMERG y no la de los pluviómetros (r² = 0.10 con 7 estaciones)
   porque es la única que es significativa. La corrección es proporcional: P_polígono = P_estación ·
   (a + b·z_polígono) / (a + b·z_estación). Decisión de método tomada en la versión alterna del informe
   (2026-10-11): queda declarada aquí y en el informe para que el equipo la acepte o la cambie.

Áreas en EPSG:3116 (regla 13). La altura media de cada polígono sale del DEM ALOS PALSAR del proyecto, leído
cada 4 celdas (unos 50 m), suficiente para un promedio sobre polígonos de cientos de km².

Ejecutar desde la raíz del proyecto: python scripts/07e_pl_thiessen.py
Salidas (out/):
  pl_thiessen_mensual.csv     por mes: PL (promedio simple), PL de Thiessen y PL de Thiessen corregida por altura
  pl_thiessen_poligonos.csv   con las 7 estaciones: área, peso y altura media de cada polígono
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import MultiPoint
from shapely.ops import voronoi_diagram

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
CRS_AREAS = "EPSG:3116"          # MAGNA-SIRGAS / Colombia Bogotá: áreas en metros (regla 13)
PASO_DEM = 4                     # se lee una de cada 4 celdas del DEM de 12.5 m

# ---------------------------------------------------------------- datos
catalogo = pd.read_csv(OUT / "pluviometros_fonce_catalogo.csv")
catalogo = catalogo[catalogo.dentro_cuenca].set_index("codigo")
pluvio = pd.read_csv(OUT / "pluviometros_fonce_mensual_depurado.csv", parse_dates=["fecha"])
pluvio["periodo"] = pluvio.fecha.dt.to_period("M")
tabla = pluvio.pivot(index="periodo", columns="codigo", values="precipitacion_mm")[catalogo.index.tolist()]
assert len(tabla.columns) == 7

cuencas = gpd.read_file(OUT / "shp_fonce/cuencas_fonce.shp")
cuenca = cuencas[cuencas.gauge_id.astype(int) == ID_PRINCIPAL].to_crs(CRS_AREAS).geometry.iloc[0]
estaciones = gpd.GeoSeries(gpd.points_from_xy(catalogo.longitud, catalogo.latitud), index=catalogo.index,
                           crs="EPSG:4326").to_crs(CRS_AREAS)

gradiente = pd.read_csv(OUT / "gradiente_altitudinal_resumen.csv")
recta_imerg = gradiente[gradiente.fuente.str.startswith("IMERG")].iloc[0]
A_GRAD, B_GRAD = recta_imerg.intercepto_mm, recta_imerg.mm_por_1000m / 1000     # mm/año y mm/año por metro
assert B_GRAD < 0 and recta_imerg.r2 > 0.5

dem = rasterio.open(RAIZ / "data/dem/dem_fonce_alos_12m.tif")


def altura_media(poligono):
    """Altura media del DEM dentro de un polígono en EPSG:3116 (el DEM está en otra proyección)."""
    geom = gpd.GeoSeries([poligono], crs=CRS_AREAS).to_crs(dem.crs).iloc[0]
    datos, _ = mask(dem, [geom], crop=True, filled=True, nodata=dem.nodata)
    z = datos[0, ::PASO_DEM, ::PASO_DEM].astype(float)
    z = z[z != dem.nodata]
    return float(z.mean())


def poligonos(codigos):
    """Polígonos de Thiessen de las estaciones dadas, recortados con la cuenca: área (km²) y altura media (m)."""
    puntos = estaciones.loc[list(codigos)]
    if len(puntos) == 1:
        celdas = {puntos.index[0]: cuenca}
    else:
        diagrama = voronoi_diagram(MultiPoint(list(puntos)), envelope=cuenca.buffer(50_000))
        celdas = {}
        for celda in diagrama.geoms:
            dueno = [c for c, p in puntos.items() if celda.contains(p)]
            assert len(dueno) == 1
            celdas[dueno[0]] = celda.intersection(cuenca)
    return pd.DataFrame({"area_km2": {c: g.area / 1e6 for c, g in celdas.items()},
                         "altura_poligono_m": {c: altura_media(g) for c, g in celdas.items()}})


# ---------------------------------------------------------------- un juego de polígonos por combinación de estaciones
presentes = tabla.notna()
combinaciones = {tuple(c for c in tabla.columns if fila[c]) for _, fila in presentes.iterrows()}
assert all(len(c) > 0 for c in combinaciones)      # todos los meses tienen al menos una estación
juegos = {c: poligonos(c) for c in sorted(combinaciones)}
print(f"{len(combinaciones)} combinaciones de estaciones presentes en {len(tabla)} meses")


def lluvia_mes(fila, corregida):
    codigos = tuple(c for c in tabla.columns if pd.notna(fila[c]))
    pol = juegos[codigos]
    pesos = pol.area_km2 / pol.area_km2.sum()
    p = fila[list(codigos)].astype(float)
    if corregida:
        z_est = catalogo.loc[list(codigos), "altitud"]
        p = p * (A_GRAD + B_GRAD * pol.altura_poligono_m) / (A_GRAD + B_GRAD * z_est)
    return float((pesos * p).sum())


salida = pd.DataFrame({
    "pl_promedio_simple": tabla.mean(axis=1),
    "pl_thiessen": tabla.apply(lluvia_mes, axis=1, corregida=False),
    "pl_thiessen_altura": tabla.apply(lluvia_mes, axis=1, corregida=True),
    "estaciones_con_dato": presentes.sum(axis=1),
})
salida.index.name = "periodo"
assert salida.notna().all().all() and len(salida) == 300

# comprobación: el promedio simple es exactamente la PL de siempre (16_correlaciones_variables.py guarda los 262
# meses en que todas las variables tienen dato)
pl_16 = pd.read_csv(OUT / "variables_mensuales.csv", index_col=0)["PL"]
pl_16.index = pd.PeriodIndex(pl_16.index, freq="M")
assert len(pl_16) > 250 and np.allclose(salida.pl_promedio_simple.reindex(pl_16.index), pl_16)

# los 7 polígonos con todas las estaciones, para la tabla del informe
completo = juegos[tuple(tabla.columns)].copy()
completo["peso"] = completo.area_km2 / completo.area_km2.sum()
completo["nombre"] = catalogo.nombre.str.replace(r"\s*\[\d+\]", "", regex=True)
completo["altitud_estacion_m"] = catalogo.altitud
completo["factor_altura"] = ((A_GRAD + B_GRAD * completo.altura_poligono_m)
                             / (A_GRAD + B_GRAD * completo.altitud_estacion_m))
completo.index.name = "codigo"
area_total = completo.area_km2.sum()
area_proyecto = float(pd.read_csv(OUT / "shp_fonce/areas_cuencas.csv").set_index("gauge_id").loc[ID_PRINCIPAL,
                                                                                                    "area_km2"])
assert abs(area_total / area_proyecto - 1) < 0.01      # los polígonos cubren la cuenca (EPSG:3116 contra geodésica)

salida.to_csv(OUT / "pl_thiessen_mensual.csv")
completo[["nombre", "altitud_estacion_m", "area_km2", "peso", "altura_poligono_m", "factor_altura"]].to_csv(
    OUT / "pl_thiessen_poligonos.csv")
print(completo.round(3).to_string())
print((salida.mean() * 12).round(0).to_string())
