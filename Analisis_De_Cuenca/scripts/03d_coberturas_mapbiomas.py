"""Coberturas de la cuenca de San Gil en 2022 con MapBiomas Colombia, colección 3, recortadas por el proyecto.

CAMELS-COL publica las coberturas de cada cuenca a partir de MapBiomas Colombia 2022 (colección 2), calculadas sobre
su propio polígono. Aquí se recalculan con el mapa de la colección 3 y el polígono del proyecto, y se dibuja el mapa
(decisiones del usuario del 2026-10-09: un solo año, 2022, el mismo que usa CAMELS-COL; regla 13: se prefieren los
cálculos propios).

FUENTE
  Fundación Gaia Amazonas (2025). Proyecto MapBiomas Colombia Colección 3.0 - Mapeo Anual de Cobertura y Uso del
  Suelo (la forma de citar que pide el propio MapBiomas). Un GeoTIFF por año, celdas de 30 m (0.00027°), en la
  copia pública de Google Cloud Storage, sin cuenta:
  https://storage.googleapis.com/mapbiomas-public/initiatives/colombia/collection_3/coverage/colombia_coverage_2022.tif
  El archivo está organizado en bloques, así que se lee solo la ventana de la cuenca, sin bajar el país entero.
  Los códigos de las clases (CLASES, abajo) se copiaron de la hoja «LEYENDA» del archivo de estadísticas de la
  colección 3 (statistics_for_website_mb_colombia_transision_col3.xlsx, en la misma copia pública).

TRANSFORMACIONES
  1. Se lee la ventana del rectángulo que encierra la cuenca y se guarda tal cual en data/mapbiomas/.
  2. Una celda pertenece a la cuenca si su centro cae dentro del polígono de San Gil (out/shp_fonce/cuencas_fonce.shp).
  3. El área de cada celda se mide en el elipsoide WGS84 (regla 13): todas las celdas de una fila tienen la misma
     área, que depende de la latitud.
  4. El porcentaje de cada clase es su área dividida por el área de todas las celdas de la cuenca.

SALIDAS
  data/mapbiomas/colombia_coverage_2022_fonce.tif   la ventana de la cuenca, tal como se lee del archivo nacional
  out/coberturas_mapbiomas_fonce_2022.csv            área y porcentaje de cada clase, con su grupo (nivel 1)
  reporte/figuras/mapa_coberturas.png                mapa de las coberturas de 2022
"""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import rasterio
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from pyproj import Geod
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

RAIZ = Path(__file__).resolve().parents[1]
ANIO = 2022
URL = ("https://storage.googleapis.com/mapbiomas-public/initiatives/colombia/collection_3/coverage/"
       f"colombia_coverage_{ANIO}.tif")
RECORTE = RAIZ / f"data/mapbiomas/colombia_coverage_{ANIO}_fonce.tif"
POLIGONOS = RAIZ / "out/shp_fonce/cuencas_fonce.shp"
SALIDA = RAIZ / f"out/coberturas_mapbiomas_fonce_{ANIO}.csv"
FIGURA = RAIZ / "reporte/figuras/mapa_coberturas.png"
ID_SAN_GIL = 24027010

# código del píxel -> (clase, grupo de nivel 1, color), de la hoja «LEYENDA» de MapBiomas Colombia.
# Los colores son los de la leyenda; donde la leyenda trae un código hexadecimal incompleto se pone uno parecido.
CLASES = {
    3: ("Bosque", "Formación boscosa", "#1F8D49"),
    5: ("Manglar", "Formación boscosa", "#04381D"),
    6: ("Bosque inundable", "Formación boscosa", "#026975"),
    49: ("Vegetación leñosa sobre arena", "Formación boscosa", "#02D659"),
    11: ("Formación natural no forestal inundable", "Formación natural no boscosa", "#519799"),
    12: ("Formación herbácea", "Formación natural no boscosa", "#D6BC74"),
    32: ("Planicie de marea hipersalina", "Formación natural no boscosa", "#FC8114"),
    29: ("Afloramiento rocoso", "Formación natural no boscosa", "#FFAA5F"),
    50: ("Vegetación herbácea sobre arena", "Formación natural no boscosa", "#AD5100"),
    13: ("Otra formación natural no forestal", "Formación natural no boscosa", "#D89F5C"),
    81: ("Herbazales o arbustales andinos", "Formación natural no boscosa", "#DFEB62"),
    82: ("Herbazales o arbustales andinos inundables", "Formación natural no boscosa", "#6FC179"),
    9: ("Silvicultura", "Área agropecuaria", "#7A5900"),
    35: ("Palma aceitera", "Área agropecuaria", "#9065D0"),
    74: ("Plátano y banano", "Área agropecuaria", "#BE83F7"),
    21: ("Mosaico de agricultura o pasto", "Área agropecuaria", "#FFEFC3"),
    23: ("Playas, dunas y bancos de arena", "Área sin vegetación", "#FFA07A"),
    24: ("Infraestructura urbana", "Área sin vegetación", "#D4271E"),
    30: ("Minería", "Área sin vegetación", "#9C0027"),
    68: ("Otra área natural sin vegetación", "Área sin vegetación", "#E97A7A"),
    25: ("Otra área sin vegetación", "Área sin vegetación", "#DB4D4F"),
    75: ("Parques solares", "Área sin vegetación", "#C12100"),
    33: ("Río, lago u océano", "Cuerpo de agua", "#2532E4"),
    31: ("Acuicultura", "Cuerpo de agua", "#091077"),
    34: ("Glaciar y nival", "Cuerpo de agua", "#93DFE6"),
    27: ("No observado", "No observado", "#FFFFFF"),
}
SIN_DATO = 0          # valor «nodata» del archivo nacional


# ---------------------------------------------------------------- lectura de la ventana de la cuenca
cuenca = gpd.read_file(POLIGONOS).query("gauge_id == @ID_SAN_GIL").to_crs(4326)
if not RECORTE.exists():
    RECORTE.parent.mkdir(parents=True, exist_ok=True)
    # GDAL usa su propio cliente HTTP; si el sistema declara un archivo de certificados, se le pasa
    opciones = {"GDAL_CURL_CA_BUNDLE": os.environ["CURL_CA_BUNDLE"]} if "CURL_CA_BUNDLE" in os.environ else {}
    with rasterio.Env(**opciones), rasterio.open("/vsicurl/" + URL) as fuente:
        ventana = from_bounds(*cuenca.total_bounds, fuente.transform).round_offsets().round_lengths()
        datos = fuente.read(1, window=ventana)
        perfil = fuente.profile | {"width": datos.shape[1], "height": datos.shape[0],
                                   "transform": fuente.window_transform(ventana), "compress": "lzw"}
    with rasterio.open(RECORTE, "w", **perfil) as destino:
        destino.write(datos, 1)

with rasterio.open(RECORTE) as r:
    clases = r.read(1)
    transform = r.transform
    assert r.crs.to_epsg() == 4326

# ---------------------------------------------------------------- celdas dentro de la cuenca y su área
dentro = geometry_mask(cuenca.geometry, out_shape=clases.shape, transform=transform, invert=True)
assert not (clases[dentro] == SIN_DATO).any(), "hay celdas sin dato dentro de la cuenca"
desconocidos = set(np.unique(clases[dentro])) - set(CLASES)
assert not desconocidos, f"códigos sin clase en la leyenda: {desconocidos}"

geod = Geod(ellps="WGS84")
filas = np.arange(clases.shape[0])
lat_norte = transform.f + filas * transform.e
lat_sur = lat_norte + transform.e
lon0 = transform.c
area_celda_km2 = np.array([abs(geod.polygon_area_perimeter([lon0, lon0 + transform.a, lon0 + transform.a, lon0],
                                                            [s, s, n, n])[0]) / 1e6
                           for n, s in zip(lat_norte, lat_sur)])
areas = np.broadcast_to(area_celda_km2[:, None], clases.shape)

tabla = (pd.DataFrame({"codigo": clases[dentro], "area_km2": areas[dentro]})
         .groupby("codigo", as_index=False)["area_km2"].sum())
tabla["clase"] = tabla.codigo.map(lambda c: CLASES[c][0])
tabla["grupo"] = tabla.codigo.map(lambda c: CLASES[c][1])
area_total = tabla.area_km2.sum()
tabla["porcentaje"] = tabla.area_km2 / area_total * 100
tabla = tabla.sort_values("porcentaje", ascending=False)[["codigo", "clase", "grupo", "area_km2", "porcentaje"]]
tabla.to_csv(SALIDA, index=False, float_format="%.4f")

# el área de las celdas debe parecerse a la del polígono (geodésica, out/shp_fonce/areas_cuencas.csv);
# la diferencia viene de decidir por el centro de cada celda de 30 m
area_poligono = float(pd.read_csv(RAIZ / "out/shp_fonce/areas_cuencas.csv")
                      .set_index("gauge_id").loc[ID_SAN_GIL, "area_km2"])
assert abs(area_total - area_poligono) / area_poligono < 0.001, (area_total, area_poligono)
print(f"{ANIO}: {dentro.sum()} celdas, {area_total:.2f} km² (polígono: {area_poligono:.2f} km²)")
print(tabla.to_string(index=False, float_format="%.2f"))

# ---------------------------------------------------------------- mapa
presentes = list(tabla.codigo)
indice = {c: i for i, c in enumerate(presentes)}
imagen = np.full(clases.shape, np.nan)
for c in presentes:
    imagen[(clases == c) & dentro] = indice[c]
mapa_colores = ListedColormap([CLASES[c][2] for c in presentes])
izq, abajo = transform.c, transform.f + transform.e * clases.shape[0]
der, arriba = transform.c + transform.a * clases.shape[1], transform.f

fig, ax = plt.subplots(figsize=(9.0, 7.6), dpi=200)
ax.imshow(imagen, cmap=mapa_colores, vmin=-0.5, vmax=len(presentes) - 0.5, extent=(izq, der, abajo, arriba),
          interpolation="nearest")
cuenca.boundary.plot(ax=ax, color="black", linewidth=1.2)
leyenda = [Patch(facecolor=CLASES[c][2], edgecolor="#5a5a5a",
                 label=f"{CLASES[c][0]} ({p:.1f} %)" if p >= 0.1 else
                 f"{CLASES[c][0]} ({p:.2f} %)" if p >= 0.005 else f"{CLASES[c][0]} (< 0.01 %)")
           for c, p in zip(tabla.codigo, tabla.porcentaje)]
ax.legend(handles=leyenda, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=7.5, frameon=True,
          title=f"Cobertura {ANIO}", title_fontsize=8)
ax.set_xlabel("Longitud (°)")
ax.set_ylabel("Latitud (°)")
# un kilómetro mide lo mismo en las dos direcciones a la latitud de la cuenca
ax.set_aspect(1 / np.cos(np.radians(cuenca.geometry.iloc[0].centroid.y)))
ax.tick_params(labelsize=7)
ax.set_title(f"Coberturas de la cuenca del Fonce hasta San Gil, {ANIO}\n"
             "MapBiomas Colombia, colección 3 (celdas de 30 m)", fontsize=9)
fig.tight_layout()
FIGURA.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGURA)
print(f"figura: {FIGURA.relative_to(RAIZ)}")
