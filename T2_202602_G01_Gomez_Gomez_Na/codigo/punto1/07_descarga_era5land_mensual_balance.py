"""Descarga de ERA5-Land las medias mensuales de radiación neta y evaporación sobre la cuenca del Fonce.

Fuente: Copernicus Climate Data Store (CDS), producto «reanalysis-era5-land-monthly-means», tipo
«monthly_averaged_reanalysis», malla de 0.1°.

Por qué este producto: el de series de tiempo («reanalysis-era5-land-timeseries», el de los 6 puntos) no ofrece
estas variables (consultado en la API del CDS el 2026-11-17). Se piden en una caja que cubre la cuenca:
    surface_net_solar_radiation     ssr   radiación neta de onda corta en superficie
    surface_net_thermal_radiation   str   radiación neta de onda larga en superficie
    total_evaporation               e     evaporación total (negativa = del suelo hacia la atmósfera)
    potential_evaporation           pev   evaporación potencial del esquema de ERA5-Land

Ojo con las unidades: en las medias mensuales de ERA5-Land las variables acumuladas son el promedio de la
acumulación DIARIA (J/m² por día para la radiación, m de agua por día para la evaporación). Las unidades y el
signo se leen del archivo y se guardan en el .meta.json; aquí no se transforma ningún valor.

Caja: N 6.7, O −73.4, S 5.8, E −72.7 (la caja del polígono CAMELS-COL 24027010, de −73.25 a −72.86 y de 5.93 a
6.62, más una celda de 0.1° de margen). Período: 1998-01 a 2022-12.

Requisito: una cuenta del CDS con su clave en ~/.cdsapirc (nunca dentro del repositorio).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/07_descarga_era5land_mensual_balance.py

Salidas, en datos/punto1/era5land_mensual_balance/:
    era5land_mensual_balance_1998_2022_fonce.nc            tal como lo entrega el CDS
    era5land_mensual_balance_1998_2022_fonce.nc.meta.json  fuente, variables, unidades, período, caja, SHA-256
Si el archivo ya existe no se vuelve a descargar. Si la descarga falla o el archivo no trae los 300 meses y las
4 variables, el script se detiene con un error.
"""

import datetime
import hashlib
import json
import zipfile
from pathlib import Path

import cdsapi
import numpy as np
import xarray as xr

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_mensual_balance"
ARCHIVO = CARPETA_SALIDA / "era5land_mensual_balance_1998_2022_fonce.nc"

# --- Petición ---------------------------------------------------------------------------------------
PRODUCTO = "reanalysis-era5-land-monthly-means"
URL_PRODUCTO = "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means"
VARIABLES = {
    "surface_net_solar_radiation": "ssr",
    "surface_net_thermal_radiation": "str",
    "total_evaporation": "e",
    "potential_evaporation": "pev",
}
ANIOS = [str(a) for a in range(1998, 2023)]
MESES = [f"{m:02d}" for m in range(1, 13)]
CAJA = [6.7, -73.4, 5.8, -72.7]  # N, O, S, E
MESES_ESPERADOS = 300


def sha256_de(archivo):
    """SHA-256 de un archivo, para dejar constancia de qué se descargó."""
    resumen = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def descargar():
    if ARCHIVO.exists():
        print(f"Ya existe {ARCHIVO.name}, no se descarga de nuevo.")
        return
    peticion = {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": list(VARIABLES),
        "year": ANIOS,
        "month": MESES,
        "time": ["00:00"],
        "area": CAJA,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }
    temporal = ARCHIVO.with_suffix(".descarga")
    print("Pidiendo al CDS las medias mensuales...", flush=True)
    cdsapi.Client().retrieve(PRODUCTO, peticion).download(str(temporal))
    if zipfile.is_zipfile(temporal):
        raise RuntimeError(f"El CDS entregó un ZIP en vez de un NetCDF: {zipfile.ZipFile(temporal).namelist()}")
    temporal.rename(ARCHIVO)


def comprobar_y_describir():
    """Comprueba meses y variables y devuelve lo que se escribe en el .meta.json."""
    ds = xr.open_dataset(ARCHIVO)
    tiempo = "valid_time" if "valid_time" in ds.dims else "time"
    faltan = [c for c in VARIABLES.values() if c not in ds.data_vars]
    if faltan:
        raise RuntimeError(f"Al archivo le faltan las variables {faltan}; trae {list(ds.data_vars)}")
    if ds.sizes[tiempo] != MESES_ESPERADOS:
        raise RuntimeError(f"El archivo trae {ds.sizes[tiempo]} meses; se esperaban {MESES_ESPERADOS}")
    variables = {}
    for nombre_cds, corto in VARIABLES.items():
        da = ds[corto]
        variables[corto] = {
            "nombre_cds": nombre_cds,
            "nombre_largo": da.attrs.get("long_name"),
            "unidades_en_archivo": da.attrs.get("units"),
            "nota_unidades": ("media mensual de la acumulación diaria (por día); "
                              + ("valores negativos = flujo hacia arriba" if corto in ("e", "pev", "str") else
                                 "positivo hacia la superficie")),
            "nan": int(np.isnan(da.values).sum()),
        }
    lat, lon = ds["latitude"].values, ds["longitude"].values
    return {
        "dims": {k: int(v) for k, v in ds.sizes.items()},
        "periodo": f"{str(ds[tiempo].values[0])[:7]} a {str(ds[tiempo].values[-1])[:7]} ({ds.sizes[tiempo]} meses)",
        "recorte": (f"{lat.size} x {lon.size} celdas de 0.1° (lat x lon); centros lat {lat.min():.2f} a "
                    f"{lat.max():.2f}, lon {lon.min():.2f} a {lon.max():.2f}; caja pedida N/O/S/E {CAJA}"),
        "variables": variables,
    }


def main():
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    descargar()
    info = comprobar_y_describir()
    meta = {
        "archivo": ARCHIVO.name,
        "fuente": "ERA5-Land (Muñoz-Sabater et al., 2021), Copernicus Climate Data Store",
        "producto": PRODUCTO,
        "version": "ERA5-Land monthly averaged reanalysis (versión servida por el CDS en la fecha de descarga)",
        "variables": info["variables"],
        "periodo": info["periodo"],
        "resolucion": "0.1°, mensual",
        "recorte_espacial": info["recorte"],
        "dimensiones": info["dims"],
        "url": URL_PRODUCTO,
        "fecha_descarga": datetime.date.today().isoformat(),
        "procesamiento": "ninguno: el NetCDF tal como lo entrega el CDS",
        "script": "codigo/punto1/07_descarga_era5land_mensual_balance.py",
        "sha256": sha256_de(ARCHIVO),
    }
    (CARPETA_SALIDA / f"{ARCHIVO.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
