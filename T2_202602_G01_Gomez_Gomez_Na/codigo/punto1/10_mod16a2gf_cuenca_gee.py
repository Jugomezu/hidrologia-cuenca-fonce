"""ET real de MOD16A2GF (MODIS, Penman-Monteith) promediada sobre la cuenca del Fonce, por Google Earth Engine.

Fuente: MOD16A2GF versión 6.1 (Running et al., 2021), colección de Earth Engine «MODIS/061/MOD16A2GF»: ET real
(banda ET) de compuestos de 8 días a 500 m, con huecos rellenados (gap-filled). El algoritmo es Penman-Monteith
con entradas de MODIS (cobertura, LAI/FPAR, albedo) y meteorología de reanálisis.
    Banda ET: kg/m² por compuesto (= mm por compuesto), factor de escala 0.1.
    Valores de 32761 a 32767 son códigos de relleno (agua, urbano, nieve, roca, sin clasificar...) y se descartan.
    Cada compuesto suma 8 días; el último de cada año suma 5 (o 6 en año bisiesto) días.

Período: los compuestos con fecha de inicio entre 2000-01-01 y 2022-12-31 que tenga la colección (MODIS Terra
empieza en 2000-02; las fechas reales se leen de la colección, no se suponen).

Promedio de cuenca: media de los píxeles con dato dentro del polígono CAMELS-COL 24027010, en la proyección
sinusoidal de MODIS a 500 m. Se guarda también el porcentaje de píxeles válidos del compuesto.

Requisitos: cuenta de Earth Engine y su proyecto de Google Cloud; autenticar una vez con
    earthengine authenticate
El proyecto se pasa con --proyecto ID o se toma del que dejó guardado «earthengine set_project ID».
Ninguna credencial se guarda en el repositorio. En este equipo la verificación TLS de Python necesita el almacén
de certificados de Windows; por eso se usa truststore.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/10_mod16a2gf_cuenca_gee.py --proyecto ID

Salidas:
    datos/punto1/mod16a2gf/mod16a2gf_et_cuenca_2000_2022.csv            una fila por compuesto
    datos/punto1/mod16a2gf/mod16a2gf_et_cuenca_2000_2022.csv.meta.json  fuente, versión, unidades, SHA-256
Si Earth Engine falla, el script se detiene con el error.
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import truststore

truststore.inject_into_ssl()

import ee  # noqa: E402  (después de truststore, para que use los certificados de Windows)
import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402
from shapely.geometry import mapping  # noqa: E402

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "mod16a2gf"
ARCHIVO = CARPETA_SALIDA / "mod16a2gf_et_cuenca_2000_2022.csv"
ARCHIVO_CUENCA = (RAIZ_ENTREGA / "datos" / "punto1" / "camels_col" / "boundaries"
                  / "03_CAMELS_COL_Basin_boundary" / "CAMELS_COL_catchments_boundaries.shp")

# --- Petición ---------------------------------------------------------------------------------------
COLECCION = "MODIS/061/MOD16A2GF"
BANDA = "ET"
ESCALA_VALOR = 0.1          # factor de escala de la banda ET
MAXIMO_VALIDO = 32700       # 32761–32767 son códigos de relleno
ESCALA_M = 500              # resolución nativa, m
FECHA_INICIO = "2000-01-01"
FECHA_FIN_EXCLUSIVA = "2023-01-01"
CODIGO_IDEAM = "24027010"


def sha256_de(archivo):
    resumen = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def geometria_cuenca():
    cuencas = gpd.read_file(ARCHIVO_CUENCA)
    cuenca = cuencas[cuencas["IDEAM_CODE"].astype(str) == CODIGO_IDEAM]
    if len(cuenca) != 1:
        raise RuntimeError(f"No se encontró una única cuenca {CODIGO_IDEAM} en {ARCHIVO_CUENCA.name}")
    geojson = json.loads(json.dumps(mapping(cuenca.to_crs(4326).geometry.iloc[0])))  # tuplas -> listas
    return ee.Geometry(geojson, proj="EPSG:4326", geodesic=False)


def por_compuesto(cuenca):
    """FeatureCollection con la media de ET y el % de píxeles válidos de cada compuesto."""
    coleccion = ee.ImageCollection(COLECCION).filterDate(FECHA_INICIO, FECHA_FIN_EXCLUSIVA).select(BANDA)

    def resumir(imagen):
        crudo = imagen.select(BANDA)
        valido = crudo.lte(MAXIMO_VALIDO)
        et = crudo.updateMask(valido).multiply(ESCALA_VALOR)
        media = et.reduceRegion(ee.Reducer.mean(), cuenca, ESCALA_M, maxPixels=1e9).get(BANDA)
        conteo = valido.unmask(0).reduceRegion(ee.Reducer.mean(), cuenca, ESCALA_M, maxPixels=1e9).get(BANDA)
        inicio = imagen.date()
        fin_anio = ee.Date.fromYMD(inicio.get("year").add(1), 1, 1)
        dias = fin_anio.difference(inicio, "day").min(8)
        return ee.Feature(None, {"fecha_inicio": inicio.format("YYYY-MM-dd"), "dias": dias,
                                 "et_mm_compuesto": media, "fraccion_pixeles_validos": conteo})

    return coleccion.map(resumir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proyecto", help="ID del proyecto de Google Cloud registrado en Earth Engine")
    args = parser.parse_args()
    ee.Initialize(project=args.proyecto) if args.proyecto else ee.Initialize()

    cuenca = geometria_cuenca()
    filas = por_compuesto(cuenca).getInfo()["features"]
    tabla = pd.DataFrame([f["properties"] for f in filas]).sort_values("fecha_inicio")
    tabla["pct_pixeles_validos"] = (100 * tabla.pop("fraccion_pixeles_validos")).round(2)
    tabla["et_mm_compuesto"] = tabla["et_mm_compuesto"].round(3)
    tabla["dias"] = tabla["dias"].round().astype(int)
    tabla = tabla[["fecha_inicio", "dias", "et_mm_compuesto", "pct_pixeles_validos"]]
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ARCHIVO, index=False)

    meta = {
        "archivo": ARCHIVO.name,
        "fuente": "MOD16A2GF, NASA LP DAAC (Running et al., 2021), vía Google Earth Engine",
        "version": "v061 (colección MODIS/061/MOD16A2GF)",
        "variable": "et_mm_compuesto: ET real media de la cuenca en el compuesto (banda ET × 0.1)",
        "unidades": "mm por compuesto (kg/m²); 'dias' da la longitud del compuesto (8, o 5–6 al final del año)",
        "periodo": (f"{tabla['fecha_inicio'].iloc[0]} a {tabla['fecha_inicio'].iloc[-1]} "
                    f"({len(tabla)} compuestos; fechas de inicio leídas de la colección)"),
        "resolucion": "500 m (sinusoidal MODIS), compuestos de 8 días",
        "recorte_espacial": f"polígono CAMELS-COL {CODIGO_IDEAM}; media de los píxeles con dato dentro de él",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD16A2GF",
        "fecha_descarga": datetime.date.today().isoformat(),
        "procesamiento": ("códigos de relleno (> 32700) descartados; factor 0.1 aplicado; media espacial en "
                          "Earth Engine; pct_pixeles_validos = % de píxeles de la cuenca con dato"),
        "script": "codigo/punto1/10_mod16a2gf_cuenca_gee.py",
        "sha256": sha256_de(ARCHIVO),
    }
    (CARPETA_SALIDA / f"{ARCHIVO.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(tabla.describe().round(2).to_string())
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
