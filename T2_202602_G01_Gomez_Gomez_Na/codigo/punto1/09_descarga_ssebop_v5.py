"""Descarga la ET real mensual de SSEBop versión 5 (MODIS, USGS FEWS NET) y la recorta a la cuenca del Fonce.

Fuente: SSEBop versión 5, USGS FEWS NET (Senay et al.; https://doi.org/10.5066/F72V2F1F), ET real (ETa)
mensual global de ~1 km (0.009652°) a partir de la temperatura de superficie de MODIS. Es un modelo de balance
de energía de superficie simplificado (Operational Simplified Surface Energy Balance). Acceso libre, sin cuenta:
    https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/fews/web/global/monthly/etav5/downloads/mYYYYMM.zip
Cada ZIP trae mYYYYMM_modisSSEBopETv5_actual_mm.tif: int16, ET real del mes en mm (sin factor de escala),
sin dato = −32768.

Período: lo que publica USGS para la v5, 2003-01 a 2022-04 (232 meses). No se rellena nada fuera de él.

OJO, NO HOMOGÉNEA CON LA v6.1: la v5 (MODIS, 2003–2022) y la v6.1 (VIIRS, desde 2012; script 08) usan sensores,
parametrización y mallas distintas. No se deben empalmar en una sola serie sin comparar antes el período común
(2012-02 a 2022-04).

Recorte: la caja del polígono CAMELS-COL 24027010 más una celda de margen por lado. Cada ZIP global se baja a un
archivo temporal, se recorta y se borra: no queda ningún archivo global.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/09_descarga_ssebop_v5.py

Salidas, en datos/punto1/ssebop_v5/:
    ssebop_v5_eta_mensual_2003_2022_fonce.nc            meses × lat × lon, int16, mm/mes, _FillValue −32768
    ssebop_v5_eta_mensual_2003_2022_fonce.nc.meta.json  fuente, versión, unidades, período, recorte, SHA-256
Si una descarga falla o falta un mes, el script se detiene con el error.
"""

import datetime
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
import xarray as xr
from rasterio.windows import from_bounds

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "ssebop_v5"
ARCHIVO = CARPETA_SALIDA / "ssebop_v5_eta_mensual_2003_2022_fonce.nc"
ARCHIVO_CUENCA = (RAIZ_ENTREGA / "datos" / "punto1" / "camels_col" / "boundaries"
                  / "03_CAMELS_COL_Basin_boundary" / "CAMELS_COL_catchments_boundaries.shp")

# --- Petición ---------------------------------------------------------------------------------------
URL_BASE = "https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/fews/web/global/monthly/etav5/downloads/"
PLANTILLA_TIF = "m{aaaamm}_modisSSEBopETv5_actual_mm.tif"
MESES = pd.period_range("2003-01", "2022-04", freq="M")
CODIGO_IDEAM = "24027010"
SIN_DATO = -32768


def sha256_de(archivo):
    """SHA-256 de un archivo, para dejar constancia de qué se guardó."""
    resumen = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def caja_cuenca():
    """Caja (oeste, sur, este, norte) del polígono de la cuenca, en grados."""
    cuencas = gpd.read_file(ARCHIVO_CUENCA)
    cuenca = cuencas[cuencas["IDEAM_CODE"].astype(str) == CODIGO_IDEAM]
    if len(cuenca) != 1:
        raise RuntimeError(f"No se encontró una única cuenca {CODIGO_IDEAM} en {ARCHIVO_CUENCA.name}")
    return cuenca.to_crs(4326).total_bounds


def recortar_mes(sesion, mes, caja, carpeta_temporal):
    """Descarga el ZIP global de un mes, recorta la caja y lo borra. Devuelve (valores, transform)."""
    aaaamm = mes.strftime("%Y%m")
    url = f"{URL_BASE}m{aaaamm}.zip"
    zip_temporal = Path(carpeta_temporal) / f"m{aaaamm}.zip"
    with sesion.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(zip_temporal, "wb") as f:
            for bloque in r.iter_content(1 << 20):
                f.write(bloque)
    try:
        if not zipfile.is_zipfile(zip_temporal):
            raise RuntimeError(f"{url} no es un ZIP válido")
        tif = PLANTILLA_TIF.format(aaaamm=aaaamm)
        ruta = "/vsizip/" + zip_temporal.resolve().as_posix() + "/" + tif
        with rasterio.open(ruta) as fuente:
            if fuente.nodata != SIN_DATO or fuente.dtypes[0] != "int16":
                raise RuntimeError(f"{tif}: nodata {fuente.nodata} y tipo {fuente.dtypes[0]} no son los esperados")
            oeste, sur, este, norte = caja
            paso = fuente.res[0]
            ventana = from_bounds(oeste - paso, sur - paso, este + paso, norte + paso, fuente.transform)
            ventana = ventana.round_offsets().round_lengths()
            valores = fuente.read(1, window=ventana)
            transform = fuente.window_transform(ventana)
    finally:
        zip_temporal.unlink()
    return valores, transform, url


def main():
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    caja = caja_cuenca()
    sesion = requests.Session()
    capas, urls, transform0 = [], [], None
    with tempfile.TemporaryDirectory() as carpeta_temporal:
        for mes in MESES:
            valores, transform, url = recortar_mes(sesion, mes, caja, carpeta_temporal)
            if transform0 is None:
                transform0 = transform
            elif transform != transform0 or valores.shape != capas[0].shape:
                raise RuntimeError(f"La malla de {mes} no coincide con la del primer mes")
            capas.append(valores)
            urls.append(url)
            validos = valores[valores != SIN_DATO]
            print(f"{mes}: {valores.shape}, media {validos.mean():.1f} mm, sin dato {np.mean(valores == SIN_DATO):.1%}",
                  flush=True)

    alto, ancho = capas[0].shape
    lon = transform0.c + transform0.a * (np.arange(ancho) + 0.5)
    lat = transform0.f + transform0.e * (np.arange(alto) + 0.5)  # de norte a sur, como en la fuente
    ds = xr.Dataset(
        {"eta": (("time", "lat", "lon"), np.stack(capas),
                 {"long_name": "SSEBop v5 actual evapotranspiration (monthly total)", "units": "mm/month",
                  "description": "SSEBop v5 ETa, valores del GeoTIFF de USGS sin transformar"})},
        coords={"time": MESES.to_timestamp(), "lat": ("lat", lat, {"units": "degrees_north"}),
                "lon": ("lon", lon, {"units": "degrees_east"})},
        attrs={"source": "USGS FEWS NET SSEBop v5 (MODIS), https://doi.org/10.5066/F72V2F1F",
               "crop": f"caja de la cuenca CAMELS-COL {CODIGO_IDEAM} + 1 celda"},
    )
    ds["eta"].encoding.update({"dtype": "int16", "_FillValue": SIN_DATO, "zlib": True})
    ds.to_netcdf(ARCHIVO)

    meta = {
        "archivo": ARCHIVO.name,
        "fuente": "SSEBop, USGS FEWS NET (Senay et al.), https://doi.org/10.5066/F72V2F1F",
        "version": "v5 (MODIS)",
        "variable": "eta: evapotranspiración real (actual ET) del mes",
        "unidades": "mm/mes; int16 sin factor de escala; _FillValue = -32768",
        "periodo": f"{MESES[0]} a {MESES[-1]} ({len(MESES)} meses); es todo lo que USGS publica de la v5",
        "resolucion": f"{abs(transform0.a):.6f}° (~1 km), mensual",
        "recorte_espacial": (f"{alto} x {ancho} celdas (lat x lon); centros lat {lat.min():.4f} a {lat.max():.4f}, "
                             f"lon {lon.min():.4f} a {lon.max():.4f}; caja del polígono CAMELS-COL {CODIGO_IDEAM} "
                             f"(O {caja[0]:.4f}, S {caja[1]:.4f}, E {caja[2]:.4f}, N {caja[3]:.4f}) + 1 celda"),
        "url": URL_BASE + "mYYYYMM.zip",
        "fecha_descarga": datetime.date.today().isoformat(),
        "procesamiento": ("cada GeoTIFF global se recortó a la caja y se apiló en un NetCDF; valores sin "
                          "transformar; los ZIP globales se borraron"),
        "script": "codigo/punto1/09_descarga_ssebop_v5.py",
        "homogeneidad": ("NO homogénea con SSEBop v6.1 (VIIRS, script 08): otro sensor, otra parametrización y otra malla; comparar en 2012-02 a 2022-04 antes de usarlas juntas"),
        "sha256": sha256_de(ARCHIVO),
    }
    (CARPETA_SALIDA / f"{ARCHIVO.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
