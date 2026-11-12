"""Descarga las series horarias de ERA5-Land en los 6 puntos de la cuenca del Fonce en San Gil.

Fuente: Copernicus Climate Data Store (CDS), producto «reanalysis-era5-land-timeseries»
(ERA5-Land hourly time-series data from 1950 to present). El servicio devuelve la serie de la celda de
la malla más cercana al punto pedido; por eso los puntos son centros de celda (0.1°).

Los puntos y sus pesos se escogieron el 2026-11-12 (ver temp/decisiones.md): celdas con al menos el 90 %
de su área dentro de la cuenca, una por franja de altura de igual área, con la menor diferencia de altura
entre la celda y su región de Voronoi.

Variables: las que necesita la ETo de Penman-Monteith de FAO-56 (ecuación 6):
    2m_temperature                    -> T media, máxima y mínima, Δ y es
    2m_dewpoint_temperature           -> ea
    surface_pressure                  -> γ
    10m_u_component_of_wind, 10m_v_component_of_wind -> rapidez del viento a 10 m, luego u2 (ec. 47)
    surface_solar_radiation_downwards -> Rs, y con ella Rn

Período: 1998-01-01 a 2022-12-31.

Requisito: una cuenta del CDS con su clave en ~/.cdsapirc (nunca dentro del repositorio).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/01_descarga_era5land_puntos.py

Salida: datos/punto1/era5land_puntos/punto_N.csv (una por punto; el CDS entrega un ZIP con un CSV por grupo
de variables y aquí se unen por hora, sin cambiar ningún valor) y
datos/punto1/era5land_puntos/metadatos_descarga.json (petición, fecha de descarga y SHA-256 de cada archivo).
Si el CSV de un punto ya existe, no se vuelve a descargar; si ya está el ZIP crudo (punto_N.descarga), se reutiliza.
"""

import datetime
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import cdsapi
import pandas as pd

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"
ARCHIVO_METADATOS = CARPETA_SALIDA / "metadatos_descarga.json"

# --- Petición ---------------------------------------------------------------------------------------
PRODUCTO = "reanalysis-era5-land-timeseries"
VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "surface_pressure",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "surface_solar_radiation_downwards",
]
# Nombres cortos con que el CDS escribe esas variables en el CSV.
COLUMNAS_ESPERADAS = ["t2m", "d2m", "sp", "u10", "v10", "ssrd"]
FECHA_INICIO = "1998-01-01"
FECHA_FIN = "2022-12-31"

# Puntos escogidos (temp/decisiones.md). El peso es la fracción del área de la cuenca que ocupa la región
# de Voronoi de cada punto; se usa después, al promediar la cuenca, no en la descarga.
PUNTOS = [
    {"punto": 1, "lon": -73.1, "lat": 6.0, "peso": 0.124},
    {"punto": 2, "lon": -73.1, "lat": 6.2, "peso": 0.173},
    {"punto": 3, "lon": -73.1, "lat": 6.3, "peso": 0.120},
    {"punto": 4, "lon": -73.1, "lat": 6.4, "peso": 0.146},
    {"punto": 5, "lon": -73.0, "lat": 6.1, "peso": 0.186},
    {"punto": 6, "lon": -73.0, "lat": 6.4, "peso": 0.252},
]


def sha256_de(archivo):
    """SHA-256 de un archivo, para dejar constancia de qué se descargó."""
    resumen = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def descargar_punto(cliente, punto):
    """Descarga la serie de un punto en CSV. Devuelve la ruta del CSV final."""
    destino = CARPETA_SALIDA / f"punto_{punto['punto']}.csv"
    if destino.exists():
        print(f"Punto {punto['punto']}: ya existe {destino.name}, no se descarga de nuevo.")
        return destino

    peticion = {
        "variable": VARIABLES,
        "location": {"longitude": punto["lon"], "latitude": punto["lat"]},
        "date": [f"{FECHA_INICIO}/{FECHA_FIN}"],
        "data_format": "csv",
    }
    temporal = CARPETA_SALIDA / f"punto_{punto['punto']}.descarga"
    if temporal.exists() and zipfile.is_zipfile(temporal):
        print(f"Punto {punto['punto']}: se reutiliza la descarga cruda {temporal.name}.")
    else:
        print(f"Punto {punto['punto']} ({punto['lon']}, {punto['lat']}): pidiendo al CDS...")
        cliente.retrieve(PRODUCTO, peticion).download(str(temporal))

    # El CDS entrega un ZIP con un CSV por grupo de variables (viento, temperatura, radiación, presión).
    # Todos traen las columnas valid_time, latitude y longitude; se unen por valid_time.
    if zipfile.is_zipfile(temporal):
        with zipfile.ZipFile(temporal) as zf:
            partes = [pd.read_csv(zf.open(n)) for n in sorted(zf.namelist()) if n.lower().endswith(".csv")]
    else:
        partes = [pd.read_csv(temporal)]
    serie = partes[0]
    for parte in partes[1:]:
        # Cada parte debe ser de la misma celda; latitude y longitude se conservan una sola vez.
        assert (parte[["latitude", "longitude"]].drop_duplicates().values
                == serie[["latitude", "longitude"]].drop_duplicates().values).all()
        serie = serie.merge(parte.drop(columns=["latitude", "longitude"]), on="valid_time", how="outer")
    faltan = [v for v in COLUMNAS_ESPERADAS if v not in serie.columns]
    if faltan:
        raise RuntimeError(f"Al punto {punto['punto']} le faltan las columnas {faltan}")
    serie = serie.sort_values("valid_time")
    serie.to_csv(destino, index=False)
    temporal.unlink()
    print(f"Punto {punto['punto']}: {len(serie)} horas, columnas {list(serie.columns)}")
    return destino


def main():
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    cliente = cdsapi.Client()

    archivos = []
    for punto in PUNTOS:
        ruta = descargar_punto(cliente, punto)
        celda = pd.read_csv(ruta, usecols=["latitude", "longitude"], nrows=1).iloc[0]
        archivos.append({**punto, "archivo": ruta.name, "sha256": sha256_de(ruta),
                         "celda_entregada": {"lat": float(celda.latitude), "lon": float(celda.longitude)}})

    metadatos = {
        "fuente": "Copernicus Climate Data Store",
        "producto": PRODUCTO,
        "variables": VARIABLES,
        "periodo": [FECHA_INICIO, FECHA_FIN],
        "resolucion_temporal": "horaria",
        "seleccion_del_punto": "celda de la malla de ERA5-Land más cercana a lon, lat (la hace el CDS)",
        "fecha_de_descarga": datetime.date.today().isoformat(),
        "archivos": archivos,
    }
    ARCHIVO_METADATOS.write_text(json.dumps(metadatos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {len(archivos)} archivos en {CARPETA_SALIDA}")


if __name__ == "__main__":
    main()
