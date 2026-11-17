"""Descarga de TerraClimate la evapotranspiración real (aet) y la de referencia (pet) sobre la cuenca del Fonce.

Fuente: TerraClimate v1.1 (Abatzoglou et al., 2018; actualización 2026), malla mensual de 1/24° (~4 km),
servida por OPeNDAP en el THREDDS de Northwest Knowledge Network, sin registro:
    http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_terraclimate_<var>_1950_CurrentYear_GLOBE.nc

Variables (definiciones de la documentación de TerraClimate):
    aet  evapotranspiración real (mm/mes), de un balance hídrico mensual de una capa de suelo.
    pet  evapotranspiración de referencia (mm/mes), Penman-Monteith para pasto de referencia (FAO-56).
Las dos vienen como enteros con scale_factor = 0.1; xarray aplica la escala al leer.

Período: 1998-01 a 2022-12, el mismo de la ETo de ERA5-Land (decisión del 2026-11-17).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/05_descarga_terraclimate.py

Salidas:
    datos/punto1/terraclimate/terraclimate_<var>_fonce_1998_2022.nc   recorte de la malla (caja de la cuenca + 1 celda)
    datos/punto1/terraclimate/metadatos_descarga.json                 fuente, versión, URL, fecha y SHA-256
    productos/punto1/terraclimate_mensual_cuenca.csv                   promedio de cuenca, mm/mes

Promedio de cuenca: cada celda pesa por el área de su intersección con el polígono de CAMELS-COL
(IDEAM 24027010), calculada en una proyección de área igual. Así las celdas del borde cuentan solo por la
parte que cae dentro.

Si la descarga falla, el script se detiene con el error; no hay valores de relleno.
"""

import datetime
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "terraclimate"
ARCHIVO_METADATOS = CARPETA_DATOS / "metadatos_descarga.json"
ARCHIVO_CUENCA = (RAIZ_ENTREGA / "datos" / "punto1" / "camels_col" / "boundaries"
                  / "03_CAMELS_COL_Basin_boundary" / "CAMELS_COL_catchments_boundaries.shp")
ARCHIVO_PRODUCTO = RAIZ_ENTREGA / "productos" / "punto1" / "terraclimate_mensual_cuenca.csv"

# --- Petición ---------------------------------------------------------------------------------------
URL_BASE = "http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_terraclimate_{var}_1950_CurrentYear_GLOBE.nc"
VARIABLES = ["aet", "pet"]
CODIGO_IDEAM = "24027010"
FECHA_INICIO = "1998-01-01"
FECHA_FIN = "2022-12-31"
CRS_AREA_IGUAL = "ESRI:54034"  # Lambert cilíndrica de área igual (mundo)


def cargar_cuenca():
    cuencas = gpd.read_file(ARCHIVO_CUENCA)
    cuenca = cuencas[cuencas["IDEAM_CODE"].astype(str) == CODIGO_IDEAM]
    if len(cuenca) != 1:
        raise RuntimeError(f"No se encontró un único polígono con IDEAM_CODE = {CODIGO_IDEAM}")
    return cuenca.to_crs("EPSG:4326")


def descargar(var, caja):
    """Lee por OPeNDAP solo la caja y el período pedidos."""
    url = URL_BASE.format(var=var)
    ds = xr.open_dataset(url)
    lon_min, lat_min, lon_max, lat_max = caja
    paso = float(abs(ds["lat"].diff("lat").median()))
    recorte = ds[[var]].sel(
        time=slice(FECHA_INICIO, FECHA_FIN),
        lon=slice(lon_min - paso, lon_max + paso),
        lat=slice(lat_max + paso, lat_min - paso),  # la latitud viene de norte a sur
    ).load()
    if recorte.sizes["lat"] == 0 or recorte.sizes["lon"] == 0:
        raise RuntimeError(f"El recorte de {var} quedó vacío; revisar el orden de lat/lon en {url}")
    meses_esperados = len(pd.date_range(FECHA_INICIO, FECHA_FIN, freq="MS"))
    if recorte.sizes["time"] != meses_esperados:
        raise RuntimeError(f"{var}: {recorte.sizes['time']} meses descargados, se esperaban {meses_esperados}")
    recorte.attrs.update({k: ds.attrs.get(k) for k in ("title", "version", "id", "references", "source",
                                                        "date_modified", "license")})
    recorte.attrs["url_opendap"] = url
    return recorte, paso


def pesos_por_area(lats, lons, paso, cuenca):
    """Área (km²) de la intersección de cada celda con la cuenca."""
    celdas = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            celdas.append({"i": i, "j": j, "geometry": box(lon - paso / 2, lat - paso / 2,
                                                          lon + paso / 2, lat + paso / 2)})
    malla = gpd.GeoDataFrame(celdas, crs="EPSG:4326").to_crs(CRS_AREA_IGUAL)
    poligono = cuenca.to_crs(CRS_AREA_IGUAL).geometry.iloc[0]
    malla["area_km2"] = malla.geometry.intersection(poligono).area / 1e6
    pesos = np.zeros((len(lats), len(lons)))
    for fila in malla.itertuples():
        pesos[fila.i, fila.j] = fila.area_km2
    return pesos


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)
    cuenca = cargar_cuenca()
    caja = cuenca.total_bounds
    area_cuenca = float(cuenca.to_crs(CRS_AREA_IGUAL).area.iloc[0] / 1e6)

    series = {}
    metadatos = {"fecha_descarga": datetime.date.today().isoformat(), "periodo": [FECHA_INICIO, FECHA_FIN],
                 "cuenca": f"CAMELS-COL IDEAM {CODIGO_IDEAM}", "area_cuenca_km2": round(area_cuenca, 1),
                 "ponderacion": "área de intersección celda-cuenca en " + CRS_AREA_IGUAL, "archivos": {}}

    for var in VARIABLES:
        print(f"Descargando {var} ...")
        recorte, paso = descargar(var, caja)
        archivo = CARPETA_DATOS / f"terraclimate_{var}_fonce_1998_2022.nc"
        recorte.to_netcdf(archivo)

        pesos = pesos_por_area(recorte["lat"].values, recorte["lon"].values, paso, cuenca)
        valores = recorte[var].values  # (tiempo, lat, lon), mm/mes
        celdas_validas = np.isfinite(valores) & (pesos > 0)[None, :, :]
        if (np.isfinite(valores[:, pesos > 0]).sum(axis=1) == 0).any():
            raise RuntimeError(f"{var}: hay meses sin ninguna celda válida dentro de la cuenca")
        suma_pesos = np.where(celdas_validas, pesos, 0).sum(axis=(1, 2))
        promedio = np.where(celdas_validas, valores * pesos, 0).sum(axis=(1, 2)) / suma_pesos
        cobertura = suma_pesos / pesos.sum()
        series[f"{var}_mm_mes"] = promedio
        series[f"{var}_fraccion_area_valida"] = cobertura

        metadatos["archivos"][archivo.name] = {
            "variable": var, "unidades": "mm/mes", "nombre_largo": recorte[var].attrs.get("long_name"),
            "url_opendap": recorte.attrs["url_opendap"], "version": recorte.attrs.get("version"),
            "doi": recorte.attrs.get("id"), "fecha_modificacion_fuente": recorte.attrs.get("date_modified"),
            "resolucion_grados": paso, "celdas_lat_lon": [recorte.sizes["lat"], recorte.sizes["lon"]],
            "celdas_con_area_en_cuenca": int((pesos > 0).sum()),
            "area_ponderada_km2": round(float(pesos.sum()), 1), "sha256": sha256(archivo),
        }
        print(f"  {var}: {recorte.sizes['time']} meses, {int((pesos > 0).sum())} celdas en la cuenca, "
              f"media anual {12 * np.nanmean(promedio):.0f} mm/año")

    tiempo = pd.to_datetime(recorte["time"].values).strftime("%Y-%m")
    tabla = pd.DataFrame({"mes": tiempo, **series})
    tabla.to_csv(ARCHIVO_PRODUCTO, index=False, float_format="%.3f")
    metadatos["producto"] = str(ARCHIVO_PRODUCTO.relative_to(RAIZ_ENTREGA)).replace("\\", "/")
    ARCHIVO_METADATOS.write_text(json.dumps(metadatos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Listo: {ARCHIVO_PRODUCTO.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
