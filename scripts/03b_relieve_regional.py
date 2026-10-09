"""Relieve y límites de la región de la cuenca, para el mapa de ubicación del informe.

El DEM del proyecto (03_recorte_dem.py) solo cubre la cuenca; para mostrar dónde queda el Fonce dentro de la
cordillera Oriental hace falta el relieve de la región. Este script baja dos fuentes y deja en out/ solo el
recorte que usa el mapa (decisiones del usuario del 2026-10-09):

  1. Copernicus DEM GLO-90 (ESA, programa Copernicus): modelo digital de superficie con celdas de 3" (~90 m),
     en archivos de 1° x 1°, de la copia pública en Amazon S3 (sin cuenta):
     https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_<norte>_<oeste>_DEM/...tif
     Cada archivo se nombra por la esquina suroccidental: N04_00_W074_00 cubre de 4° a 5° N y de 74° a 73° O.
  2. Natural Earth 1:10 m, límites de países (admin 0) y de departamentos (admin 1), de la copia oficial de
     Natural Earth en Amazon S3: https://naturalearth.s3.amazonaws.com/10m_cultural/...zip. El sitio
     naturalearthdata.com no se pudo usar desde el entorno donde se corrió (la red lo bloqueaba).

Recuadro: 73.5° O a 71.5° O y 4.5° N a 8° N (decidido por el usuario). Alcanza para ver el valle del Magdalena
al occidente, la cordillera Oriental y el borde de los Llanos al oriente.

TRANSFORMACIONES
  - DEM: se unen los archivos, se recorta al recuadro y se promedia por bloques de PASO_DEM_CELDAS x PASO_DEM_CELDAS
    celdas (de 3" a 18", ~550 m). Para un mapa de ubicación basta, y el producto pesa poco. Un promedio por bloques
    conserva la elevación media de cada bloque, sin inventar valores.
  - Límites: se recortan al recuadro, ampliado en MARGEN_LIMITES_GRADOS para que las líneas lleguen al borde.

SALIDAS
  data/dem/copernicus_glo90/*.tif     los archivos del DEM tal como se descargan (fuera de git, ~60 MB)
  data/natural_earth/*.zip            los límites tal como se descargan (fuera de git, ~20 MB)
  out/relieve_region_copernicus.tif   el relieve del recuadro, promediado (elevación en m; EPSG:4326)
  out/limites_region.gpkg             capas «paises» y «departamentos», recortadas al recuadro

Los archivos se bajan solo si no existen; sus SHA-256 se imprimen y están en DATOS_FUENTES.md.
"""
import hashlib
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.windows import from_bounds
from shapely.geometry import box
import truststore

truststore.inject_into_ssl()      # usa los certificados del sistema operativo para verificar las descargas

RAIZ = Path(__file__).resolve().parents[1]
DIR_DEM = RAIZ / "data/dem/copernicus_glo90"
DIR_NE = RAIZ / "data/natural_earth"
SALIDA_DEM = RAIZ / "out/relieve_region_copernicus.tif"
SALIDA_LIMITES = RAIZ / "out/limites_region.gpkg"

RECUADRO = {"oeste": -73.5, "este": -71.5, "sur": 4.5, "norte": 8.0}     # grados (decidido por el usuario)
URL_DEM = "https://copernicus-dem-90m.s3.amazonaws.com"
CELDAS_POR_GRADO = 1200            # GLO-90 entre 0° y 50° de latitud: 3" = 1/1200 de grado
PASO_DEM_CELDAS = 6                # promedio de 6 x 6 celdas: de 3" a 18" (~550 m)
URL_NE = "https://naturalearth.s3.amazonaws.com/10m_cultural"
ARCHIVOS_NE = {"paises": "ne_10m_admin_0_countries.zip", "departamentos": "ne_10m_admin_1_states_provinces.zip"}
MARGEN_LIMITES_GRADOS = 0.5


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def bajar(url, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        print(f"bajando {url} ...")
        urllib.request.urlretrieve(url, ruta)
    print(f"{ruta.relative_to(RAIZ)}: {ruta.stat().st_size / 1e6:.1f} MB, SHA-256 {sha256(ruta)}")
    return ruta


def nombre_celda(lat, lon):
    """Nombre del archivo de GLO-90 cuya esquina suroccidental es (lat, lon), en grados enteros."""
    norte = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00"
    este = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00"
    return f"Copernicus_DSM_COG_30_{norte}_{este}_DEM"


# ------------------------------------------------------------------ 1. relieve
latitudes = range(int(np.floor(RECUADRO["sur"])), int(np.ceil(RECUADRO["norte"])))
longitudes = range(int(np.floor(RECUADRO["oeste"])), int(np.ceil(RECUADRO["este"])))
celdas = []
for lat in latitudes:
    for lon in longitudes:
        nombre = nombre_celda(lat, lon)
        celdas.append(bajar(f"{URL_DEM}/{nombre}/{nombre}.tif", DIR_DEM / f"{nombre}.tif"))

limites = (RECUADRO["oeste"], RECUADRO["sur"], RECUADRO["este"], RECUADRO["norte"])
fuentes = [rasterio.open(c) for c in celdas]
assert all(f.crs.to_epsg() == 4326 for f in fuentes)
assert all(np.isclose(abs(f.res[0]), 1 / CELDAS_POR_GRADO) and np.isclose(abs(f.res[1]), 1 / CELDAS_POR_GRADO)
           for f in fuentes)
# Los archivos de esta copia tienen el centro de sus celdas en los grados enteros (sus bordes quedan medio píxel
# corridos). El mosaico se arma en esa misma malla, sin remuestrear, y se recorta por índices al recuadro.
mosaico, malla = merge(fuentes, nodata=np.nan)
for f in fuentes:
    f.close()
ventana = from_bounds(*limites, malla).round_offsets().round_lengths()
z = mosaico[0, ventana.row_off:ventana.row_off + ventana.height,
            ventana.col_off:ventana.col_off + ventana.width].astype("float64")
esquina_oeste, esquina_norte = malla * (ventana.col_off, ventana.row_off)
assert np.isfinite(z).all(), "el recuadro es todo tierra: no debería haber celdas vacías"

# promedio por bloques: se descartan las filas y columnas que no completan un bloque (a lo sumo PASO - 1 celdas)
filas, columnas = (z.shape[0] // PASO_DEM_CELDAS) * PASO_DEM_CELDAS, (z.shape[1] // PASO_DEM_CELDAS) * PASO_DEM_CELDAS
z = z[:filas, :columnas]
promedio = z.reshape(filas // PASO_DEM_CELDAS, PASO_DEM_CELDAS, columnas // PASO_DEM_CELDAS, PASO_DEM_CELDAS).mean(axis=(1, 3))
paso = PASO_DEM_CELDAS / CELDAS_POR_GRADO
transformacion = from_origin(esquina_oeste, esquina_norte, paso, paso)
SALIDA_DEM.parent.mkdir(parents=True, exist_ok=True)
with rasterio.open(SALIDA_DEM, "w", driver="GTiff", height=promedio.shape[0], width=promedio.shape[1], count=1,
                   dtype="float32", crs="EPSG:4326", transform=transformacion, compress="deflate") as destino:
    destino.write(promedio.astype("float32"), 1)
print(f"{SALIDA_DEM.relative_to(RAIZ)}: {promedio.shape[1]} x {promedio.shape[0]} celdas de {paso * 3600:.0f}\", "
      f"elevación {promedio.min():.0f} a {promedio.max():.0f} m")

# ------------------------------------------------------------------ 2. límites
marco = box(RECUADRO["oeste"] - MARGEN_LIMITES_GRADOS, RECUADRO["sur"] - MARGEN_LIMITES_GRADOS,
            RECUADRO["este"] + MARGEN_LIMITES_GRADOS, RECUADRO["norte"] + MARGEN_LIMITES_GRADOS)
paises = gpd.read_file(bajar(f"{URL_NE}/{ARCHIVOS_NE['paises']}", DIR_NE / ARCHIVOS_NE["paises"]))
departamentos = gpd.read_file(bajar(f"{URL_NE}/{ARCHIVOS_NE['departamentos']}", DIR_NE / ARCHIVOS_NE["departamentos"]))
# Natural Earth trae los nombres en varios idiomas: NAME_ES (países) y name (departamentos, en su idioma local)
paises = gpd.clip(paises, marco)[["NAME_ES", "ADM0_A3", "geometry"]].rename(
    columns={"NAME_ES": "nombre", "ADM0_A3": "codigo_pais"})
departamentos = gpd.clip(departamentos, marco)[["name", "adm0_a3", "geometry"]].rename(
    columns={"name": "nombre", "adm0_a3": "codigo_pais"})
assert {"COL", "VEN"} <= set(paises.codigo_pais)          # el recuadro toca la frontera con Venezuela
assert "Santander" in set(departamentos.nombre)
if SALIDA_LIMITES.exists():
    SALIDA_LIMITES.unlink()                                  # se reescribe completo
paises.to_file(SALIDA_LIMITES, layer="paises", driver="GPKG")
departamentos.to_file(SALIDA_LIMITES, layer="departamentos", driver="GPKG")
print(f"{SALIDA_LIMITES.relative_to(RAIZ)}: {len(paises)} países ({', '.join(sorted(paises.nombre))}) y "
      f"{len(departamentos)} departamentos o estados ({', '.join(sorted(departamentos.nombre))})")
