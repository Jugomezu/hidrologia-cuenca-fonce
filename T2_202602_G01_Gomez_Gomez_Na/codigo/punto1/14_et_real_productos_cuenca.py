"""ET real mensual de la cuenca del Fonce según cada producto descargado, y su media anual (punto 1, fase 6, datos).

Solo prepara las series: promedio de cuenca, unidades a mm/mes y medias anuales. No compara ni interpreta.

Lee (datos/punto1/):
    gleam_v4/gleam_v4_E_mensual_1998_2022_fonce.nc       GLEAM v4.3a, E (ET real) y Ep (evaporación potencial), mm/mes
    gleam_v4/gleam_v4_Ep_mensual_1998_2022_fonce.nc
    ssebop/ssebop_v61_eta_mensual_2012_2022_fonce.nc     SSEBop v6.1 (VIIRS), mm/mes, 2012-02 a 2022-12
    ssebop_v5/ssebop_v5_eta_mensual_2003_2022_fonce.nc   SSEBop v5 (MODIS), mm/mes, 2003-01 a 2022-04
    era5land_mensual_balance/era5land_mensual_balance_1998_2022_fonce.nc   ERA5-Land e y pev (m/día, negativo = hacia arriba)
    mod16a2gf/mod16a2gf_et_cuenca_2000_2022.csv          MOD16A2GF v061, mm por compuesto de 8 días, ya promediado en la cuenca
    camels_col/.../CAMELS_COL_catchments_boundaries.shp  polígono de la cuenca 24027010
y productos/punto1/terraclimate_mensual_cuenca.csv (aet, ya promediado en la cuenca por 05_descarga_terraclimate.py).

Escribe en productos/punto1/:
    et_real_mensual_productos.csv   una columna por producto, mm/mes, 1998-01 a 2022-12 (vacío donde el producto no tiene dato)
    et_real_anual_productos.csv     media anual de cada producto: en su propio periodo y en el periodo común

Promedio de cuenca de los productos en malla: cada celda pesa el área de su intersección con el polígono de la cuenca,
calculada en una proyección de área igual (ESRI:54034), igual que en 05_descarga_terraclimate.py. Si en un mes falta
una celda, los pesos se reparten entre las que tienen dato; el mes queda vacío si falta más del 10 % del área.

Conversiones:
    ERA5-Land e y pev: el archivo trae la media mensual de la acumulación diaria (m/día, negativo hacia arriba).
        ET (mm/mes) = −e × 1000 × días del mes; lo mismo para pev.
        Sep a dic de 2022 quedan vacíos: el producto mensual de ERA5-Land está dañado en esos meses por el error de
        ECMWF (decisión del 2026-11-17, anexos/decisiones.md; comprobación en 04d).
    MOD16A2GF: cada compuesto se reparte por igual entre sus días y se suman los días de cada mes. Un mes se calcula
        solo si todos sus días están cubiertos por algún compuesto.
    SSEBop: valores negativos se tratan como faltantes (no hubo ninguno al probar).

Media anual: suma de los 12 meses de cada año completo, promediada entre años. Dos versiones:
    «propio»: todos los años completos de cada producto.
    «comun»: solo los años en que todos los productos de ET real (no Ep ni pev) tienen los 12 meses.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/14_et_real_productos_cuenca.py
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
DATOS = RAIZ_ENTREGA / "datos" / "punto1"
ARCHIVO_CUENCA = (DATOS / "camels_col" / "boundaries" / "03_CAMELS_COL_Basin_boundary"
                  / "CAMELS_COL_catchments_boundaries.shp")
TERRACLIMATE = RAIZ_ENTREGA / "productos" / "punto1" / "terraclimate_mensual_cuenca.csv"
MOD16 = DATOS / "mod16a2gf" / "mod16a2gf_et_cuenca_2000_2022.csv"
SALIDA_MENSUAL = RAIZ_ENTREGA / "productos" / "punto1" / "et_real_mensual_productos.csv"
SALIDA_ANUAL = RAIZ_ENTREGA / "productos" / "punto1" / "et_real_anual_productos.csv"

CODIGO_IDEAM = "24027010"
CRS_AREA_IGUAL = "ESRI:54034"
MESES = pd.date_range("1998-01-01", "2022-12-01", freq="MS")
FRACCION_AREA_MINIMA = 0.90
ULTIMO_MES_ERA5_MENSUAL = "2022-08"   # error de ECMWF desde 2022-09 (anexos/decisiones.md)

# columna de salida -> (archivo, variable, tipo de conversión)
PRODUCTOS_EN_MALLA = {
    "gleam_E": (DATOS / "gleam_v4" / "gleam_v4_E_mensual_1998_2022_fonce.nc", "E", "mm_mes"),
    "gleam_Ep": (DATOS / "gleam_v4" / "gleam_v4_Ep_mensual_1998_2022_fonce.nc", "Ep", "mm_mes"),
    "ssebop_v61": (DATOS / "ssebop" / "ssebop_v61_eta_mensual_2012_2022_fonce.nc", "eta", "mm_mes"),
    "ssebop_v5": (DATOS / "ssebop_v5" / "ssebop_v5_eta_mensual_2003_2022_fonce.nc", "eta", "mm_mes"),
    "era5land_e": (DATOS / "era5land_mensual_balance" / "era5land_mensual_balance_1998_2022_fonce.nc", "e", "m_dia"),
    "era5land_pev": (DATOS / "era5land_mensual_balance" / "era5land_mensual_balance_1998_2022_fonce.nc", "pev", "m_dia"),
}
# Las que son ET real (entran al periodo común); gleam_Ep y era5land_pev son demanda, solo de referencia.
ET_REAL = ["era5land_e", "gleam_E", "mod16a2gf", "terraclimate_aet", "ssebop_v61", "ssebop_v5"]


def cargar_cuenca():
    cuencas = gpd.read_file(ARCHIVO_CUENCA)
    cuenca = cuencas[cuencas["IDEAM_CODE"].astype(str) == CODIGO_IDEAM]
    assert len(cuenca) == 1
    return cuenca.to_crs(CRS_AREA_IGUAL).geometry.iloc[0]


def pesos_por_area(lats, lons, poligono):
    """Área (km²) de la intersección de cada celda con la cuenca; celdas centradas en lats × lons."""
    paso_lat = float(np.abs(np.diff(lats)).mean())
    paso_lon = float(np.abs(np.diff(lons)).mean())
    celdas = [box(lon - paso_lon / 2, lat - paso_lat / 2, lon + paso_lon / 2, lat + paso_lat / 2)
              for lat in lats for lon in lons]
    malla = gpd.GeoSeries(celdas, crs="EPSG:4326").to_crs(CRS_AREA_IGUAL)
    return (malla.intersection(poligono).area.to_numpy() / 1e6).reshape(len(lats), len(lons))


def serie_de_malla(archivo, variable, conversion, poligono):
    """Promedio de cuenca ponderado por área, en mm/mes, indexado por el primer día del mes."""
    ds = xr.open_dataset(archivo)
    datos = ds[variable]
    nombre_lat = "latitude" if "latitude" in datos.dims else "lat"
    nombre_lon = "longitude" if "longitude" in datos.dims else "lon"
    nombre_t = "valid_time" if "valid_time" in datos.dims else "time"
    datos = datos.transpose(nombre_t, nombre_lat, nombre_lon)
    pesos = pesos_por_area(datos[nombre_lat].values, datos[nombre_lon].values, poligono)
    valores = datos.values.astype(float)
    if conversion == "mm_mes":
        valores = np.where(valores < 0, np.nan, valores)
    con_dato = ~np.isnan(valores)
    area_con_dato = (con_dato * pesos).sum(axis=(1, 2))
    media = np.nansum(valores * pesos, axis=(1, 2)) / np.where(area_con_dato > 0, area_con_dato, np.nan)
    media = np.where(area_con_dato / pesos.sum() >= FRACCION_AREA_MINIMA, media, np.nan)
    fechas = pd.to_datetime(datos[nombre_t].values).to_period("M").to_timestamp()
    serie = pd.Series(media, index=fechas)
    if conversion == "m_dia":
        serie = -serie * 1000 * serie.index.days_in_month
        serie[serie.index > pd.Timestamp(ULTIMO_MES_ERA5_MENSUAL + "-01")] = np.nan
    print(f"{archivo.name} [{variable}]: área de la cuenca en la malla {pesos.sum():.1f} km², "
          f"{int(serie.notna().sum())} meses con dato")
    return serie


def serie_mod16():
    """Compuestos de 8 días repartidos por día y sumados por mes; meses sin cobertura completa quedan vacíos."""
    compuestos = pd.read_csv(MOD16, parse_dates=["fecha_inicio"])
    diaria = []
    for fila in compuestos.itertuples():
        dias = pd.date_range(fila.fecha_inicio, periods=fila.dias, freq="D")
        diaria.append(pd.Series(fila.et_mm_compuesto / fila.dias, index=dias))
    diaria = pd.concat(diaria)
    assert not diaria.index.duplicated().any()
    por_mes = diaria.resample("MS").agg(["sum", "count"])
    completos = por_mes["count"] == por_mes.index.days_in_month
    return por_mes["sum"].where(completos)


def medias_anuales(mensual, anios):
    """Media de las sumas anuales en los años dados (solo años con 12 meses)."""
    filas = {}
    for columna in mensual.columns:
        anual = mensual[columna].groupby(mensual.index.year).agg(["sum", "count"])
        completos = anual[anual["count"] == 12]
        propio = completos["sum"]
        comun = completos["sum"].reindex(anios)
        filas[columna] = {
            "anios_completos_propio": len(propio),
            "primer_anio": int(propio.index.min()), "ultimo_anio": int(propio.index.max()),
            "media_anual_propio_mm": propio.mean(),
            "media_anual_comun_mm": comun.mean() if comun.notna().all() else np.nan,
        }
    return pd.DataFrame(filas).T


def main():
    poligono = cargar_cuenca()
    series = {nombre: serie_de_malla(archivo, variable, conversion, poligono)
              for nombre, (archivo, variable, conversion) in PRODUCTOS_EN_MALLA.items()}
    series["mod16a2gf"] = serie_mod16()
    terraclimate = pd.read_csv(TERRACLIMATE)
    series["terraclimate_aet"] = pd.Series(terraclimate["aet_mm_mes"].to_numpy(),
                                           index=pd.to_datetime(terraclimate["mes"]))
    mensual = pd.DataFrame({k: v.reindex(MESES) for k, v in series.items()})
    mensual = mensual[["era5land_e", "gleam_E", "mod16a2gf", "terraclimate_aet", "ssebop_v61", "ssebop_v5",
                       "gleam_Ep", "era5land_pev"]]

    # Años comunes: todos los productos de ET real con los 12 meses
    cuenta = mensual[ET_REAL].notna().groupby(mensual.index.year).sum()
    anios_comunes = [int(a) for a in cuenta.index if (cuenta.loc[a] == 12).all()]
    assert anios_comunes, "no hay años comunes"
    anual = medias_anuales(mensual, anios_comunes)
    anual["periodo_comun"] = f"{anios_comunes[0]}–{anios_comunes[-1]}"
    assert anios_comunes == list(range(anios_comunes[0], anios_comunes[-1] + 1))

    salida = mensual.copy()
    salida.index = salida.index.strftime("%Y-%m")
    salida.index.name = "mes"
    salida.round(2).to_csv(SALIDA_MENSUAL)
    anual.index.name = "producto"
    anual.round(1).to_csv(SALIDA_ANUAL)
    print(anual.round(1).to_string())
    print(f"Listo: {SALIDA_MENSUAL.relative_to(RAIZ_ENTREGA)} y {SALIDA_ANUAL.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
