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

Salida: datos/punto1/era5land_puntos/punto_N.csv (una por punto, tal como la entrega el CDS) y
datos/punto1/era5land_puntos/metadatos_descarga.json (petición, fecha de descarga y SHA-256 de cada archivo).
Si un archivo ya existe, no se vuelve a descargar.
"""

import datetime
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import cdsapi

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
    print(f"Punto {punto['punto']} ({punto['lon']}, {punto['lat']}): pidiendo al CDS...")
    cliente.retrieve(PRODUCTO, peticion).download(str(temporal))

    # El CDS puede entregar el CSV suelto o dentro de un ZIP; en el segundo caso se extrae el único CSV.
    if zipfile.is_zipfile(temporal):
        with zipfile.ZipFile(temporal) as zf:
            csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if len(csvs) != 1:
                raise RuntimeError(f"Se esperaba un CSV en el ZIP del punto {punto['punto']}, hay {csvs}")
            with zf.open(csvs[0]) as origen, open(destino, "wb") as salida:
                shutil.copyfileobj(origen, salida)
        temporal.unlink()
    else:
        temporal.rename(destino)
    return destino


def main():
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    cliente = cdsapi.Client()

    archivos = []
    for punto in PUNTOS:
        ruta = descargar_punto(cliente, punto)
        archivos.append({**punto, "archivo": ruta.name, "sha256": sha256_de(ruta)})

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
