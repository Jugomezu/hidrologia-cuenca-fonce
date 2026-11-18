"""Comprueba si los datos de ERA5-Land del punto 1 están afectados por el error de sep-2022 a feb-2024 (punto 1).

El 2024-04-02 ECMWF anunció que en «reanalysis-era5-land-monthly-means» (tipo «monthly_averaged_reanalysis») todas
las variables acumuladas de sep-2022 a feb-2024 están mal y no se van a reemplazar; propone usar en su lugar el tipo
«monthly_averaged_reanalysis_by_hour_of_day» a las 00:00. Fuente:
https://forum.ecmwf.int/t/issue-affecting-era5-land-monthly-averaged-reanalysis-for-the-period-september-2022-to-february-2024/2370

Nuestro período termina en 2022-12, así que solo pueden estar afectados sep, oct, nov y dic de 2022. Se revisan:
    1. datos/punto1/era5land_mensual_balance/  (medias mensuales: ssr, str, e, pev; producto afectado)
    2. productos/punto1/era5land_diario_puntos.csv  (Rs diaria del producto de series de tiempo; no nombrado)
Para cada variable y cada uno de esos 4 meses se compara el valor de 2022 con el mismo mes de 1998–2021: media,
mínimo, máximo y cociente 2022 / media. Un cociente fuera del rango histórico indica que el dato está mal.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/04d_comprobacion_era5land_sep2022.py

Salida: anexos/punto1/era5land_sep_dic_2022_comprobacion.csv
"""

from pathlib import Path

import pandas as pd
import xarray as xr

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
MENSUAL_BALANCE = (RAIZ_ENTREGA / "datos" / "punto1" / "era5land_mensual_balance"
                   / "era5land_mensual_balance_1998_2022_fonce.nc")
DIARIA_PUNTOS = RAIZ_ENTREGA / "productos" / "punto1" / "era5land_diario_puntos.csv"
SALIDA = RAIZ_ENTREGA / "anexos" / "punto1" / "era5land_sep_dic_2022_comprobacion.csv"

MESES_AFECTABLES = [9, 10, 11, 12]  # sep a dic de 2022: lo que cae dentro de nuestro período
ANIO_REVISADO = 2022


def serie_mensual_balance():
    """Media simple de la caja de 0.1° por mes, para cada variable (solo se usa para comparar meses entre sí)."""
    ds = xr.open_dataset(MENSUAL_BALANCE)
    medias = ds[["ssr", "str", "e", "pev"]].mean(["latitude", "longitude"]).to_dataframe()
    medias.index = pd.to_datetime(medias.index)
    return {f"{v} (reanalysis-era5-land-monthly-means, caja)": medias[v] for v in ["ssr", "str", "e", "pev"]}


def serie_mensual_rs_puntos():
    """Rs diaria media de los 6 puntos, promediada por mes (producto de series de tiempo)."""
    diaria = pd.read_csv(DIARIA_PUNTOS, parse_dates=["fecha"])
    por_dia = diaria.groupby("fecha")["rs_MJm2"].mean()
    return {"rs_MJm2 (reanalysis-era5-land-timeseries, 6 puntos)": por_dia.resample("MS").mean()}


def comparar(series):
    filas = []
    for nombre, serie in series.items():
        for mes in MESES_AFECTABLES:
            historico = serie[(serie.index.month == mes) & (serie.index.year < ANIO_REVISADO)]
            valor = serie[(serie.index.month == mes) & (serie.index.year == ANIO_REVISADO)].iloc[0]
            fuera = not (historico.min() <= valor <= historico.max())
            filas.append({
                "variable": nombre,
                "mes": f"{ANIO_REVISADO}-{mes:02d}",
                "valor_2022": valor,
                "media_1998_2021": historico.mean(),
                "minimo_1998_2021": historico.min(),
                "maximo_1998_2021": historico.max(),
                "cociente_2022_sobre_media": valor / historico.mean(),
                "fuera_del_rango_historico": fuera,
            })
    return pd.DataFrame(filas)


def main():
    tabla = comparar(serie_mensual_balance() | serie_mensual_rs_puntos())
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(SALIDA, index=False, float_format="%.6g")
    resumen = tabla.groupby("variable").agg(cociente_min=("cociente_2022_sobre_media", "min"),
                                            cociente_max=("cociente_2022_sobre_media", "max"),
                                            meses_fuera=("fuera_del_rango_historico", "sum"))
    print(resumen.round(2).to_string())
    print(f"Escrito {SALIDA.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
