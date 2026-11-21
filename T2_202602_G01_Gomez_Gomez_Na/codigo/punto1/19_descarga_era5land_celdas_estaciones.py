"""Descarga las series horarias de ERA5-Land en la celda que contiene cada estación del IDEAM de la fase 3.

Hasta el 2026-11-20 las estaciones se comparaban con el más cercano de los 6 puntos de la cuenca, que no siempre es la
celda donde está la estación. Juan decidió (anexos/decisiones.md, 2026-11-20) bajar la celda propia de cada estación y
rehacer con ella las comparaciones de los scripts 12, 13 y 17.

Mismo producto, variables, periodo y procesamiento que 01_descarga_era5land_puntos.py (se reutiliza su función de
descarga). Se pide el centro de la celda de 0.1° que contiene la estación (coordenada redondeada a 0.1°); el CDS
devuelve la celda más cercana a ese centro, que es la misma.

    estación                      lat, lon de la estación    celda pedida
    24025040 Escuela Agrícola Mogotes   6.470, −72.969       6.5, −73.0
    24025030 La Sierra-AUT              5.967, −73.162       6.0, −73.2
    24025050 Charalá                    6.274, −73.151       6.3, −73.2   (a 0.0006° del borde con −73.1)

Mogotes-AUT (24025090, solo viento) tiene las mismas coordenadas que 24025040.

Requisito: una cuenta del CDS con su clave en ~/.cdsapirc (nunca dentro del repositorio). Corre en el PC de Juan.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/19_descarga_era5land_celdas_estaciones.py

Salida: datos/punto1/era5land_celdas_estaciones/punto_<código>.csv y metadatos_descarga.json, con el mismo formato que
datos/punto1/era5land_puntos/.
"""

import datetime
import importlib.util
import json
from pathlib import Path

import cdsapi
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_celdas_estaciones"

CELDAS = [
    {"punto": "24025040", "nombre": "Escuela Agrícola Mogotes", "lon": -73.0, "lat": 6.5},
    {"punto": "24025030", "nombre": "La Sierra-AUT", "lon": -73.2, "lat": 6.0},
    {"punto": "24025050", "nombre": "Charalá", "lon": -73.2, "lat": 6.3},
]


def cargar_script_01():
    ruta = Path(__file__).with_name("01_descarga_era5land_puntos.py")
    spec = importlib.util.spec_from_file_location("descarga_01", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.CARPETA_SALIDA = CARPETA_SALIDA
    return modulo


def main():
    d01 = cargar_script_01()
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    cliente = cdsapi.Client()
    archivos = []
    for celda in CELDAS:
        ruta = d01.descargar_punto(cliente, celda)
        entregada = pd.read_csv(ruta, usecols=["latitude", "longitude"], nrows=1).iloc[0]
        assert abs(entregada.latitude - celda["lat"]) < 0.051 and abs(entregada.longitude - celda["lon"]) < 0.051, \
            f"{celda['punto']}: el CDS entregó otra celda ({entregada.latitude}, {entregada.longitude})"
        archivos.append({**celda, "archivo": ruta.name, "sha256": d01.sha256_de(ruta),
                         "celda_entregada": {"lat": float(entregada.latitude), "lon": float(entregada.longitude)}})
    metadatos = {
        "fuente": "Copernicus Climate Data Store",
        "producto": d01.PRODUCTO,
        "variables": d01.VARIABLES,
        "periodo": [d01.FECHA_INICIO, d01.FECHA_FIN],
        "resolucion_temporal": "horaria",
        "seleccion_del_punto": "centro de la celda de 0.1° que contiene cada estación del IDEAM",
        "fecha_de_descarga": datetime.date.today().isoformat(),
        "archivos": archivos,
    }
    (CARPETA_SALIDA / "metadatos_descarga.json").write_text(json.dumps(metadatos, ensure_ascii=False, indent=2),
                                                           encoding="utf-8")
    print(f"Listo: {len(archivos)} archivos en {CARPETA_SALIDA}")


if __name__ == "__main__":
    main()
