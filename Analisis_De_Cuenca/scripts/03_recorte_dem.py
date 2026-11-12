"""Recorta el DEM ALOS PALSAR de Colombia a la zona de la cuenca del Fonce y lo guarda en data/dem/.

El DEM original (`Dem_Colombia-002.tif`, 12,5 m, EPSG:32619) es un mosaico de todo el país de varios GB
que vive en la carpeta compartida del equipo en Google Drive (`G:/Shared drives/DEM_Colombia`). Ese
archivo no viaja con el proyecto, así que este script corta una sola vez la parte que se usa y la deja
en `data/dem/dem_fonce_alos_12m.tif`. Todos los demás scripts y el notebook leen el recorte, no el
original. **Este es el único paso que necesita la carpeta compartida**; el recorte ya viene incluido en
el proyecto, así que para reproducir el análisis no hace falta volver a correrlo.

Qué cubre el recorte: la envolvente de la cuenca de San Gil con 2 km de margen, más todas las celdas de
IMERG (0,1°) y de ERA5-Land (0,1°) que tocan la cuenca completas, porque los gradientes altitudinales
promedian el DEM dentro de cada celda y esas celdas se salen de la divisoria.

El recorte se hace sobre la grilla del original, en píxeles enteros y sin remuestrear: cada píxel del
recorte es exactamente el mismo del mosaico, así que cualquier cálculo da lo mismo con uno que con otro.

Requiere haber corrido antes 02_shp_cuencas_estaciones.py (el polígono de la cuenca). Las celdas de
IMERG y ERA5-Land no se leen de ningún archivo: se reconstruye la malla de 0,1° sobre la envolvente de
la cuenca con un anillo de margen, así el recorte no depende de haber corrido los scripts de esas
fuentes.

Salida: data/dem/dem_fonce_alos_12m.tif (GeoTIFF int16, nodata -32768, compresión DEFLATE sin pérdida).
"""
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

RAIZ = Path(__file__).resolve().parent.parent
DEM_ORIGINAL = Path(r"G:/Shared drives/DEM_Colombia/Dem_Colombia-002.tif")
SALIDA = RAIZ / "data/dem/dem_fonce_alos_12m.tif"
ID_PRINCIPAL = 24027010
MARGEN_M = 2000             # aire alrededor de la cuenca, como usan las figuras
LADO_CELDA = 0.1            # grados, IMERG y ERA5-Land

cuencas = gpd.read_file(RAIZ / "out/shp_fonce/cuencas_fonce.shp")
cuencas["gauge_id"] = cuencas.gauge_id.astype(int)
cuenca_geo = cuencas[cuencas.gauge_id == ID_PRINCIPAL].to_crs(4326)

# --- las celdas de 0,1° que pueden tocar la cuenca: toda la malla sobre la envolvente, más un anillo
lon0, lat0, lon1, lat1 = cuenca_geo.total_bounds
centros_lon = np.arange(math.floor(lon0 / LADO_CELDA) - 1, math.ceil(lon1 / LADO_CELDA) + 1) * LADO_CELDA
centros_lat = np.arange(math.floor(lat0 / LADO_CELDA) - 1, math.ceil(lat1 / LADO_CELDA) + 1) * LADO_CELDA
# IMERG tiene centros en x,x5 y ERA5-Land en x,x0: se cubren las dos mallas tomando medio lado extra
esquinas_lon = [centros_lon.min() - LADO_CELDA, centros_lon.max() + LADO_CELDA]
esquinas_lat = [centros_lat.min() - LADO_CELDA, centros_lat.max() + LADO_CELDA]

with rasterio.open(DEM_ORIGINAL) as src:
    a_utm = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
    # las cuatro esquinas de la caja de celdas, proyectadas (la proyección tuerce un poco la caja)
    xs, ys = a_utm.transform([min(esquinas_lon), max(esquinas_lon), min(esquinas_lon), max(esquinas_lon)],
                             [min(esquinas_lat), min(esquinas_lat), max(esquinas_lat), max(esquinas_lat)])
    cx0, cy0, cx1, cy1 = cuencas[cuencas.gauge_id == ID_PRINCIPAL].to_crs(src.crs).total_bounds
    x0, x1 = min(min(xs), cx0 - MARGEN_M), max(max(xs), cx1 + MARGEN_M)
    y0, y1 = min(min(ys), cy0 - MARGEN_M), max(max(ys), cy1 + MARGEN_M)

    # a píxeles enteros del original: así el recorte queda alineado con su grilla
    fila0, col0 = src.index(x0, y1, op=math.floor)
    fila1, col1 = src.index(x1, y0, op=math.ceil)
    ventana = Window(col0, fila0, col1 - col0 + 1, fila1 - fila0 + 1)
    datos = src.read(1, window=ventana)
    perfil = src.profile.copy()
    perfil.update(driver="GTiff", width=ventana.width, height=ventana.height,
                  transform=src.window_transform(ventana), compress="deflate", predictor=2,
                  tiled=True, blockxsize=512, blockysize=512, BIGTIFF="NO")

SALIDA.parent.mkdir(parents=True, exist_ok=True)
with rasterio.open(SALIDA, "w", **perfil) as dst:
    dst.write(datos, 1)

validos = datos[datos != perfil["nodata"]]
print(f"recorte: {ventana.width} x {ventana.height} píxeles de {abs(perfil['transform'].a):.2f} m")
print(f"extensión: x {x0:.0f}–{x1:.0f}, y {y0:.0f}–{y1:.0f} ({perfil['crs']})")
print(f"altura: {validos.min()}–{validos.max()} m; píxeles vacíos: {(datos == perfil['nodata']).mean():.1%}")
print(f"{SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB)")
