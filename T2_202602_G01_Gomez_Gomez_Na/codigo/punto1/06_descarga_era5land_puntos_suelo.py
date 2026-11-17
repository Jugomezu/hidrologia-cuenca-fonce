"""Descarga la humedad del suelo de ERA5-Land, por capas, en los 6 puntos de la cuenca del Fonce en San Gil.

Fuente: Copernicus Climate Data Store (CDS), producto «reanalysis-era5-land-timeseries» (series horarias de la
celda de 0.1° más cercana al punto pedido), los mismos 6 puntos de 01_descarga_era5land_puntos.py.

Variables (las únicas del balance de agua que ofrece el producto de series de tiempo, consultado en la API del
CDS el 2026-11-17; la radiación neta, la evaporación total y la evaporación potencial solo están en el producto
por malla y se descargan con 07_descarga_era5land_mensual_balance.py):
    volumetric_soil_water_level_1   swvl1, contenido volumétrico de agua del suelo, capa 0–7 cm (m³/m³)
    volumetric_soil_water_level_2   swvl2, capa 7–28 cm (m³/m³)
    volumetric_soil_water_level_3   swvl3, capa 28–100 cm (m³/m³)
    volumetric_soil_water_level_4   swvl4, capa 100–289 cm (m³/m³)

Período: 1998-01-01 a 2022-12-31, horario, en UTC (valid_time).

Requisito: una cuenta del CDS con su clave en ~/.cdsapirc (nunca dentro del repositorio).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/06_descarga_era5land_puntos_suelo.py            # los 6 puntos
    python codigo/punto1/06_descarga_era5land_puntos_suelo.py 1 3        # solo los puntos 1 y 3

Salidas, en datos/punto1/era5land_puntos_balance/:
    suelo_punto_N.csv              una por punto, tal como la entrega el CDS (los CSV del ZIP unidos por hora)
    suelo_punto_N.csv.meta.json    fuente, variables, unidades, período, celda, fecha, procesamiento y SHA-256
Si un CSV ya existe no se vuelve a descargar. Si la descarga falla o faltan columnas, el script se detiene.
"""

import datetime
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import cdsapi
import pandas as pd

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos_balance"

# --- Petición ---------------------------------------------------------------------------------------
PRODUCTO = "reanalysis-era5-land-timeseries"
URL_PRODUCTO = "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries"
VARIABLES = [
    "volumetric_soil_water_level_1",
    "volumetric_soil_water_level_2",
    "volumetric_soil_water_level_3",
    "volumetric_soil_water_level_4",
]
COLUMNAS_ESPERADAS = ["swvl1", "swvl2", "swvl3", "swvl4"]
CAPAS = {"swvl1": "0-7 cm", "swvl2": "7-28 cm", "swvl3": "28-100 cm", "swvl4": "100-289 cm"}
FECHA_INICIO = "1998-01-01"
FECHA_FIN = "2022-12-31"
HORAS_ESPERADAS = 219144  # 9 131 días × 24 h

# Los mismos puntos de 01_descarga_era5land_puntos.py (temp/decisiones.md).
PUNTOS = [
    {"punto": 1, "lon": -73.1, "lat": 6.0},
    {"punto": 2, "lon": -73.1, "lat": 6.2},
    {"punto": 3, "lon": -73.1, "lat": 6.3},
    {"punto": 4, "lon": -73.1, "lat": 6.4},
    {"punto": 5, "lon": -73.0, "lat": 6.1},
    {"punto": 6, "lon": -73.0, "lat": 6.4},
]


def sha256_de(archivo):
    """SHA-256 de un archivo, para dejar constancia de qué se descargó."""
    resumen = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def descargar_punto(cliente, punto):
    """Descarga la serie de un punto en CSV y escribe su .meta.json. Devuelve la ruta del CSV."""
    destino = CARPETA_SALIDA / f"suelo_punto_{punto['punto']}.csv"
    if destino.exists():
        print(f"Punto {punto['punto']}: ya existe {destino.name}, no se descarga de nuevo.")
        return destino

    peticion = {
        "variable": VARIABLES,
        "location": {"longitude": punto["lon"], "latitude": punto["lat"]},
        "date": [f"{FECHA_INICIO}/{FECHA_FIN}"],
        "data_format": "csv",
    }
    temporal = CARPETA_SALIDA / f"suelo_punto_{punto['punto']}.descarga"
    if temporal.exists() and zipfile.is_zipfile(temporal):
        print(f"Punto {punto['punto']}: se reutiliza la descarga cruda {temporal.name}.")
    else:
        print(f"Punto {punto['punto']} ({punto['lon']}, {punto['lat']}): pidiendo al CDS...", flush=True)
        cliente.retrieve(PRODUCTO, peticion).download(str(temporal))

    # El CDS puede entregar un CSV suelto o un ZIP con un CSV por grupo de variables; se unen por valid_time.
    if zipfile.is_zipfile(temporal):
        with zipfile.ZipFile(temporal) as zf:
            partes = [pd.read_csv(zf.open(n)) for n in sorted(zf.namelist()) if n.lower().endswith(".csv")]
    else:
        partes = [pd.read_csv(temporal)]
    serie = partes[0]
    for parte in partes[1:]:
        assert (parte[["latitude", "longitude"]].drop_duplicates().values
                == serie[["latitude", "longitude"]].drop_duplicates().values).all()
        serie = serie.merge(parte.drop(columns=["latitude", "longitude"]), on="valid_time", how="outer")
    faltan = [v for v in COLUMNAS_ESPERADAS if v not in serie.columns]
    if faltan:
        raise RuntimeError(f"Al punto {punto['punto']} le faltan las columnas {faltan}; trae {list(serie.columns)}")
    if len(serie) != HORAS_ESPERADAS:
        raise RuntimeError(f"El punto {punto['punto']} trae {len(serie)} horas; se esperaban {HORAS_ESPERADAS}")
    serie = serie.sort_values("valid_time")
    serie.to_csv(destino, index=False)
    temporal.unlink()

    celda = serie[["latitude", "longitude"]].iloc[0]
    meta = {
        "archivo": destino.name,
        "fuente": "ERA5-Land (Muñoz-Sabater et al., 2021), Copernicus Climate Data Store",
        "producto": PRODUCTO,
        "version": "ERA5-Land, series de tiempo horarias (versión servida por el CDS en la fecha de descarga)",
        "variables": {c: {"nombre_cds": v, "capa": CAPAS[c], "unidades": "m3/m3 (contenido volumétrico de agua)"}
                      for c, v in zip(COLUMNAS_ESPERADAS, VARIABLES)},
        "periodo": f"{FECHA_INICIO} 00:00 a {FECHA_FIN} 23:00 UTC, horario ({len(serie)} horas)",
        "recorte_espacial": (f"punto pedido lon {punto['lon']}, lat {punto['lat']}; celda de 0.1° entregada "
                             f"lon {float(celda.longitude):.4f}, lat {float(celda.latitude):.4f}"),
        "url": URL_PRODUCTO,
        "fecha_descarga": datetime.date.today().isoformat(),
        "procesamiento": "los CSV del ZIP del CDS unidos por valid_time y ordenados; valores sin transformar",
        "script": "codigo/punto1/06_descarga_era5land_puntos_suelo.py",
        "sha256": sha256_de(destino),
    }
    (CARPETA_SALIDA / f"{destino.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Punto {punto['punto']}: {len(serie)} horas, columnas {list(serie.columns)}", flush=True)
    return destino


def main():
    pedidos = [int(a) for a in sys.argv[1:]] or [p["punto"] for p in PUNTOS]
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    cliente = cdsapi.Client()
    for punto in PUNTOS:
        if punto["punto"] in pedidos:
            descargar_punto(cliente, punto)
    print("Listo.")


if __name__ == "__main__":
    main()
