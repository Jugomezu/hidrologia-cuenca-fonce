"""Fase 4 (punto 1): el Hargreaves de la Tarea 1 frente al de la Tarea 2 y la ETo Penman–Monteith (FAO-56), 1998–2022.

Pedido de Juan (2026-11-22): como Hargreaves ya estaba calculado en la Tarea 1, agregarlo al análisis.

Las cuatro series de Hargreaves usan la misma fórmula (Hargreaves y Samani, 1985; FAO-56 ec. 52):

    ETP = 0.0023 · 0.408 · Ra · (T + 17.8) · √(Tmáx − Tmín),   T = (Tmáx + Tmín)/2          mm/día

    Serie                   Temperatura                                   Día       Ra
    Tarea 2 (script 21)     ERA5-Land en los 6 puntos, promedio Voronoi   local     latitud de cada punto
    Tarea 1, ERA5-Land      ERA5-Land promediada sobre la cuenca (GEE)    UTC       centroide de la cuenca
    Tarea 1, MSWX           MSWX de CAMELS-COL                            -         centroide de la cuenca
    CAMELS-COL publicada    columna ETP_ de CAMELS-COL, tal como viene    -         -

La Tarea 1 (Analisis_De_Cuenca/scripts/06b_etp_hargreaves.py) ya encontró que la ETP publicada por CAMELS-COL sale
unas 2.75 veces más alta que la misma fórmula con sus mismas temperaturas (MSWX). Aquí se rehacen las dos series de la
Tarea 1 con los datos que están en datos/punto1/, para que la entrega no dependa de la carpeta de la Tarea 1.

Diferencias entre la Tarea 1 y la Tarea 2 con ERA5-Land (se declaran):
    - Tarea 1: Tmáx y Tmín diarias del promedio de la cuenca, con el día en UTC (Earth Engine). La amplitud del promedio
      es menor que el promedio de las amplitudes, y el día UTC corre 5 h la mínima y la máxima.
    - Tarea 2: Tmáx y Tmín de cada punto con el día en hora local; el método se calcula en cada punto y luego se
      promedia por Voronoi.

Escribe productos/punto1/hargreaves_tarea1_mensual.csv: por mes, las cuatro series y la ETo Penman–Monteith (FAO-56)
de la cuenca (mm/mes).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/23_hargreaves_tarea1.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1"
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_GEE = CARPETA_DATOS / "era5land_gee"   # t2m_<año>.csv: T media, mínima y máxima diaria de la cuenca (°C, UTC)
ENTRADA_CAMELS = (CARPETA_DATOS / "camels_col" / "hydromet" / "3_Hydrometeorological_data"
                  / "Hydromet_data_24027010.txt")
ENTRADA_METODOS = CARPETA_PRODUCTOS / "metodos_mensual.csv"
SALIDA = CARPETA_PRODUCTOS / "hargreaves_tarea1_mensual.csv"
# Si la carpeta de la Tarea 1 está al lado, se comprueba que esto la reproduce (no hace falta para la entrega).
TAREA1 = RAIZ_ENTREGA.parent / "Analisis_De_Cuenca" / "out" / "etp_hargreaves_fonce.csv"

DIAS = pd.date_range("1998-01-01", "2022-12-31", freq="D")
# Centroide del polígono de San Gil (Tarea 1, script 06b, medido en EPSG:3116). Con este valor la Ra de la Tarea 1 se
# reproduce con un error máximo de 6·10⁻⁵ mm/día.
LATITUD_CENTROIDE = 6.2649
MJ_A_MM = 0.408           # FAO-56 ec. 20


def radiacion_extraterrestre_mm(latitud_grados, dia_del_anio):
    """Ra en mm/día, FAO-56 ec. 21 a 25 (la misma función de la Tarea 1)."""
    phi = np.radians(latitud_grados)
    dr = 1 + 0.033 * np.cos(2 * np.pi * dia_del_anio / 365)
    declinacion = 0.409 * np.sin(2 * np.pi * dia_del_anio / 365 - 1.39)
    ws = np.arccos(-np.tan(phi) * np.tan(declinacion))
    ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(declinacion)
                                          + np.cos(phi) * np.cos(declinacion) * np.sin(ws))
    return ra * MJ_A_MM


def hargreaves(t_min, t_max, ra_mm):
    """mm/día. Un día con Tmáx < Tmín da NaN, como en la Tarea 1."""
    amplitud = (t_max - t_min).where(t_max >= t_min)
    return 0.0023 * ra_mm * ((t_max + t_min) / 2 + 17.8) * np.sqrt(amplitud)


def main():
    ra = pd.Series(radiacion_extraterrestre_mm(LATITUD_CENTROIDE, DIAS.dayofyear.values), index=DIAS)

    gee = pd.concat([pd.read_csv(ENTRADA_GEE / f"t2m_{anio}.csv", parse_dates=["fecha"]) for anio in range(1998, 2023)])
    gee = gee.set_index("fecha").reindex(DIAS)
    camels = pd.read_csv(ENTRADA_CAMELS, sep="\t", encoding="latin-1")
    camels.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
    camels["fecha"] = pd.to_datetime(camels["fecha"], format="%d/%m/%Y")
    camels = camels.set_index("fecha").sort_index().reindex(DIAS)

    diaria = pd.DataFrame({
        "tarea1_era5land": hargreaves(gee["t_min"], gee["t_max"], ra),
        "tarea1_mswx": hargreaves(camels["t_min"], camels["t_max"], ra),
        "camels_publicada": camels["etp"],
    })
    print("Días sin dato:", diaria.isna().sum().to_dict())

    if TAREA1.exists():
        t1 = pd.read_csv(TAREA1, parse_dates=["fecha"]).set_index("fecha").reindex(DIAS)
        for nuestra, suya in [("tarea1_era5land", "etp_era5land"), ("tarea1_mswx", "etp_mswx"),
                              ("camels_publicada", "etp_camels")]:
            diferencia = (diaria[nuestra] - t1[suya]).abs().max()
            assert diferencia < 1e-3, f"{nuestra}: no reproduce la Tarea 1 (máx. {diferencia:.4f} mm/día)"
        print("Reproduce out/etp_hargreaves_fonce.csv de la Tarea 1 (diferencia < 0.001 mm/día).")

    # Mensual = suma de los días; un mes con algún día faltante queda NaN (no se rellena).
    mensual = diaria.resample("MS").sum(min_count=1)
    mensual[diaria.isna().resample("MS").sum() > 0] = np.nan

    metodos = pd.read_csv(ENTRADA_METODOS)
    metodos.index = pd.to_datetime(metodos["mes"])
    mensual["tarea2_6_puntos"] = metodos["hargreaves_mm_mes"]
    mensual["eto_penman_monteith"] = metodos["eto_fao56_mm_mes"]
    mensual = mensual[["tarea2_6_puntos", "tarea1_era5land", "tarea1_mswx", "camels_publicada", "eto_penman_monteith"]]

    salida = mensual.add_suffix("_mm_mes")
    salida.index = salida.index.strftime("%Y-%m")
    salida.rename_axis("mes").round(3).to_csv(SALIDA)
    print(f"Listo: {SALIDA}")

    comunes = mensual.dropna()
    print(f"\nMedia anual, {len(comunes)} meses con todas las series (mm/año):")
    anual = comunes.mean() * 12
    for columna, valor in anual.items():
        print(f"  {columna:<22} {valor:7.0f}   {100 * (valor / anual['eto_penman_monteith'] - 1):+6.1f} % frente a la ETo")


if __name__ == "__main__":
    main()
