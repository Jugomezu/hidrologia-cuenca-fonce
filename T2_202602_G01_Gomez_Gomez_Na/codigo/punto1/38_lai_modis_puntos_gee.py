"""Índice de área foliar (LAI) de MODIS MCD15A3H en la celda de cada uno de los 6 puntos, por Google Earth Engine.

Para el tema f de la fase 9 (resistencia del dosel, Jarvis): la rs de la hoja se reparte entre el área foliar, así que
hace falta el LAI de cada punto.

Fuente: MCD15A3H versión 6.1 (Myneni et al., 2021; Terra + Aqua), colección de Earth Engine «MODIS/061/MCD15A3H»:
LAI de compuestos de 4 días a 500 m.
    Banda Lai: m²/m², factor de escala 0.1; valores 249–255 son códigos de relleno y se descartan.
    Banda FparLai_QC: bits 5–7 (SCF_QC) dicen qué algoritmo dio el valor: 0 y 1 = algoritmo principal (radiativo),
    2–4 = algoritmo de respaldo (relación empírica con el NDVI) o sin dato. En los Andes hay muchas nubes y el
    respaldo es frecuente; por eso se guardan dos medias: con todos los píxeles válidos y solo con el algoritmo
    principal, y el porcentaje de cada una.

Período: compuestos con fecha de inicio entre 2002-07-01 (inicio de la serie combinada Terra + Aqua) y 2022-12-31;
las fechas reales se leen de la colección.

Recorte: la celda de 0.1° de ERA5-Land de cada punto (centro ± 0.05° en lat y lon), igual que la ET de GLEAM y SSEBop
en el script 37. Media de los píxeles con dato dentro de la celda, en la proyección sinusoidal de MODIS a 500 m.

Requisitos: cuenta de Earth Engine y su proyecto de Google Cloud; autenticar una vez con
    earthengine authenticate
El proyecto se pasa con --proyecto ID o se toma del que dejó guardado «earthengine set_project ID».
Ninguna credencial se guarda en el repositorio. Igual que el script 10, se usa truststore para la verificación TLS.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/38_lai_modis_puntos_gee.py --proyecto ID

Salidas:
    datos/punto1/mcd15a3h/mcd15a3h_lai_puntos_2002_2022.csv            una fila por punto y compuesto
    datos/punto1/mcd15a3h/mcd15a3h_lai_puntos_2002_2022.csv.meta.json  fuente, versión, unidades, SHA-256
Si Earth Engine falla, el script se detiene con el error.
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import truststore

truststore.inject_into_ssl()

import ee  # noqa: E402  (después de truststore, para que use los certificados del sistema)
import pandas as pd  # noqa: E402

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "mcd15a3h"
ARCHIVO = CARPETA_SALIDA / "mcd15a3h_lai_puntos_2002_2022.csv"
ARCHIVO_PUNTOS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"

# --- Petición ---------------------------------------------------------------------------------------
COLECCION = "MODIS/061/MCD15A3H"
ESCALA_VALOR = 0.1          # factor de escala de la banda Lai
MAXIMO_VALIDO = 100         # 0–100 válidos (LAI 0–10); 249–255 son códigos de relleno
SCF_ALGORITMO_PRINCIPAL = 1  # SCF_QC 0 o 1 = algoritmo principal
ESCALA_M = 500              # resolución nativa, m
MEDIA_CELDA = 0.05          # medio ancho de la celda de ERA5-Land (grados)
FECHA_INICIO = "2002-07-01"
FECHA_FIN_EXCLUSIVA = "2023-01-01"


def sha256_de(archivo):
    resumen = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def celdas_de_los_puntos():
    """FeatureCollection con el rectángulo de 0.1° de cada punto."""
    puntos = pd.read_csv(ARCHIVO_PUNTOS)
    rasgos = []
    for _, p in puntos.iterrows():
        caja = ee.Geometry.Rectangle([p["lon"] - MEDIA_CELDA, p["lat"] - MEDIA_CELDA,
                                      p["lon"] + MEDIA_CELDA, p["lat"] + MEDIA_CELDA], "EPSG:4326", False)
        rasgos.append(ee.Feature(caja, {"punto": int(p["punto"])}))
    return ee.FeatureCollection(rasgos)


def por_compuesto(celdas, inicio, fin_exclusiva):
    """Una fila por punto y compuesto: LAI medio (todos los válidos y solo algoritmo principal) y % de píxeles."""
    coleccion = ee.ImageCollection(COLECCION).filterDate(inicio, fin_exclusiva)

    def resumir(imagen):
        crudo = imagen.select("Lai")
        valido = crudo.lte(MAXIMO_VALIDO)
        principal = valido.And(imagen.select("FparLai_QC").rightShift(5).bitwiseAnd(7).lte(SCF_ALGORITMO_PRINCIPAL))
        lai = crudo.multiply(ESCALA_VALOR)
        bandas = ee.Image.cat([
            lai.updateMask(valido).rename("lai_todos"),
            lai.updateMask(principal).rename("lai_principal"),
            valido.unmask(0).rename("fraccion_valida"),
            principal.unmask(0).rename("fraccion_principal"),
        ])
        medias = bandas.reduceRegions(celdas, ee.Reducer.mean(), ESCALA_M)
        fecha = imagen.date().format("YYYY-MM-dd")
        return medias.map(lambda f: f.set("fecha_inicio", fecha).setGeometry(None))

    return coleccion.map(resumir).flatten()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proyecto", help="ID del proyecto de Google Cloud registrado en Earth Engine")
    args = parser.parse_args()
    ee.Initialize(project=args.proyecto) if args.proyecto else ee.Initialize()

    # Earth Engine devuelve a lo sumo 5000 elementos por petición: se pide un año a la vez.
    celdas = celdas_de_los_puntos()
    anio_inicio, anio_fin = int(FECHA_INICIO[:4]), int(FECHA_FIN_EXCLUSIVA[:4])
    filas = []
    for anio in range(anio_inicio, anio_fin):
        inicio = FECHA_INICIO if anio == anio_inicio else f"{anio}-01-01"
        filas += por_compuesto(celdas, inicio, f"{anio + 1}-01-01").getInfo()["features"]
    tabla = pd.DataFrame([f["properties"] for f in filas])
    for col in ("fraccion_valida", "fraccion_principal"):
        tabla[col.replace("fraccion", "pct_pixeles")] = (100 * tabla.pop(col)).round(2)
    tabla = (tabla[["punto", "fecha_inicio", "lai_todos", "lai_principal", "pct_pixeles_valida",
                    "pct_pixeles_principal"]]
             .sort_values(["punto", "fecha_inicio"]).round({"lai_todos": 3, "lai_principal": 3}))
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ARCHIVO, index=False)

    meta = {
        "archivo": ARCHIVO.name,
        "fuente": "MCD15A3H, NASA LP DAAC (Myneni et al., 2021), vía Google Earth Engine",
        "version": "v061 (colección MODIS/061/MCD15A3H)",
        "variable": ("lai_todos: LAI medio de los píxeles válidos de la celda; lai_principal: solo píxeles del "
                     "algoritmo principal (SCF_QC 0–1); pct_pixeles_*: % de píxeles de la celda en cada caso"),
        "unidades": "m²/m² (banda Lai × 0.1); compuestos de 4 días",
        "periodo": (f"{tabla['fecha_inicio'].min()} a {tabla['fecha_inicio'].max()} "
                    f"({tabla['fecha_inicio'].nunique()} compuestos; fechas leídas de la colección)"),
        "resolucion": "500 m (sinusoidal MODIS)",
        "recorte_espacial": "celda de 0.1° de ERA5-Land de cada uno de los 6 puntos (centro ± 0.05°)",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD15A3H",
        "doi": "10.5067/MODIS/MCD15A3H.061",
        "fecha_descarga": datetime.date.today().isoformat(),
        "procesamiento": "códigos de relleno (> 100) descartados; factor 0.1; media espacial en Earth Engine",
        "script": "codigo/punto1/38_lai_modis_puntos_gee.py",
        "sha256": sha256_de(ARCHIVO),
    }
    (CARPETA_SALIDA / f"{ARCHIVO.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(tabla.groupby("punto")[["lai_todos", "lai_principal", "pct_pixeles_principal"]].describe().round(2)
          .to_string())
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
