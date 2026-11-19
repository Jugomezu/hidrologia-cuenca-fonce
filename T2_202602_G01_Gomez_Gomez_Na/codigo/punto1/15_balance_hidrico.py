"""Balance hídrico de largo plazo de la cuenca del Fonce en San Gil: ET real = P − Q − ΔS (punto 1).

Da una ET real que no depende de ningún modelo de evapotranspiración: sale de la lluvia medida o estimada (P), del
caudal observado en la salida (Q) y del cambio de agua en el suelo (ΔS). Sirve para contrastar los productos de ET
real (script 14) y la ETo.

Decisiones (Juan, 2026-11-19; anexos/decisiones.md):
    - P con dos fuentes en paralelo, como en la Tarea 1: PI (IMERG) y PL (pluviómetros del IDEAM, serie depurada).
    - Huecos de Q: el balance de largo plazo usa solo los meses en que hay Q y se arma como ciclo anual medio
      (la media de cada mes del calendario, sumada sobre los 12 meses). Los años completos se reportan aparte, como
      comprobación.
    - ΔS: humedad del suelo de ERA5-Land (4 capas, 0-289 cm) en los 6 puntos. En el largo plazo se supone ΔS ≈ 0; aquí
      se mide cuánto vale para comprobarlo. No incluye agua subterránea profunda.

Lee (datos/punto1/):
    camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_24027010.txt   Q diario en m³/s (columna Caudal)
    camels_col/boundaries/.../CAMELS_COL_catchments_boundaries.shp              polígono de la cuenca
    imerg/imerg_mensual_col.npz                                                 IMERG V07 mensual, mm/mes
    ideam/pluviometros/dhime/dhime_mensual_1998_2022_8est.zip                   precipitación total mensual, 8 estaciones
    ideam/cne_ideam.csv                                                         coordenadas de las estaciones (CNE)
    era5land_puntos_balance/suelo_punto_N.csv                                   swvl1-4 horario, m³/m³

Escribe (productos/punto1/):
    balance_hidrico_mensual.csv   PI, PL, Q, S y ΔS de la cuenca, mm/mes, 1998-01 a 2022-12
    balance_hidrico_anual.csv     años completos de Q: P, Q, ΔS y ET real con PI y con PL, mm/año
    balance_hidrico_resumen.csv   ET real de largo plazo con PI y con PL, por los dos caminos, y el ΔS medido

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/15_balance_hidrico.py
"""

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
DATOS = RAIZ_ENTREGA / "datos" / "punto1"
PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ARCHIVO_CUENCA = (DATOS / "camels_col" / "boundaries" / "03_CAMELS_COL_Basin_boundary"
                  / "CAMELS_COL_catchments_boundaries.shp")
ARCHIVO_Q = DATOS / "camels_col" / "hydromet" / "3_Hydrometeorological_data" / "Hydromet_data_24027010.txt"
ARCHIVO_IMERG = DATOS / "imerg" / "imerg_mensual_col.npz"
ARCHIVO_PLUVIOMETROS = DATOS / "ideam" / "pluviometros" / "dhime" / "dhime_mensual_1998_2022_8est.zip"
ARCHIVO_CNE = DATOS / "ideam" / "cne_ideam.csv"
CARPETA_SUELO = DATOS / "era5land_puntos_balance"

CODIGO_IDEAM = "24027010"
# Área del polígono de la cuenca, geodésica, medida en la Tarea 1 (Analisis_De_Cuenca/out/shp_fonce/areas_cuencas.csv).
# Se comprueba abajo contra el polígono para no depender de esa carpeta.
AREA_KM2 = 2098.85
DIAS = pd.date_range("1998-01-01", "2022-12-31", freq="D")
MESES = pd.period_range("1998-01", "2022-12", freq="M")
# Regla de la Tarea 1 para pasar de diario a mensual: un mes con 5 o más días sin dato queda vacío.
MAX_DIAS_FALTANTES = 4

# Pesos de Voronoi de los 6 puntos de ERA5-Land (los mismos de 04_eto_fao56.py; anexos/decisiones.md).
PESOS_PUNTOS = {1: 0.124, 2: 0.173, 3: 0.120, 4: 0.146, 5: 0.186, 6: 0.252}
# Espesor de las capas de suelo de ERA5-Land, en mm: 0-7, 7-28, 28-100 y 100-289 cm.
ESPESOR_CAPAS_MM = {"swvl1": 70, "swvl2": 210, "swvl3": 720, "swvl4": 1890}

# Tramos de pluviómetros excluidos en la Tarea 1 (Analisis_De_Cuenca/scripts/07_pluviometros_dhime.py, tabla
# EXCLUSIONES, decididos el 2026-09-28). Se copian tal cual: son problemas de registro, no lluvia.
EXCLUSIONES_PL = [
    (24020040, "2016-01", "2018-12"),   # Encino: totales 2016-2018 muy por encima de su serie, sin respaldo
    (24020230, "1998-01", "2004-11"),   # Pueblo Viejo: salto de nivel en 2004-12 (Pettitt, p < 0.001)
    # meses en 0 mm que los vecinos no acompañan (todos los demás midieron al menos 20 mm)
    (24020220, "2000-08", "2000-08"), (24020220, "2009-07", "2009-07"), (24020220, "2013-07", "2013-07"),
    (24020220, "2018-05", "2018-05"), (24020220, "2019-07", "2019-07"),
    (24020080, "2017-12", "2017-12"), (24020080, "2021-12", "2021-12"),
]


def a_mensual(serie_diaria):
    """Suma mensual de una serie diaria; vacía si al mes le faltan más de MAX_DIAS_FALTANTES días.

    Igual que en la Tarea 1: el acumulado es el promedio de los días con dato por los días del mes.
    """
    grupos = serie_diaria.resample("MS")
    faltantes = grupos.apply(lambda x: x.index.days_in_month[0] - x.notna().sum())
    promedio = grupos.mean()
    mensual = (promedio * promedio.index.days_in_month).where(faltantes <= MAX_DIAS_FALTANTES)
    mensual.index = mensual.index.to_period("M")
    return mensual.reindex(MESES)


def cargar_cuenca():
    cuencas = gpd.read_file(ARCHIVO_CUENCA)
    cuenca = cuencas[cuencas["IDEAM_CODE"].astype(str) == CODIGO_IDEAM].to_crs(4326)
    assert len(cuenca) == 1
    area_medida = float(cuenca.to_crs("ESRI:54034").area.iloc[0]) / 1e6
    assert abs(area_medida / AREA_KM2 - 1) < 0.005, area_medida
    return cuenca.geometry.iloc[0]


def caudal_mensual():
    """Q en mm/mes. En el archivo de CAMELS-COL los días sin dato no aparecen: se completa el calendario."""
    q = pd.read_csv(ARCHIVO_Q, sep="\t", encoding="latin-1")
    q.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
    q["fecha"] = pd.to_datetime(q["fecha"], format="%d/%m/%Y")
    caudal = q.set_index("fecha")["caudal"].reindex(DIAS)
    print(f"Q: {int(caudal.isna().sum())} de {len(DIAS)} días sin dato en 1998-2022 "
          f"({caudal.isna().mean() * 100:.1f} %)")
    lamina_diaria = caudal * 86400 / (AREA_KM2 * 1e6) * 1000   # m³/s -> mm/día
    return a_mensual(lamina_diaria)


def precipitacion_imerg(cuenca):
    """PI: cada celda de 0.1° pesa la fracción de su área que cae dentro de la cuenca (como la Tarea 1, script 05)."""
    imerg = np.load(ARCHIVO_IMERG, allow_pickle=True)
    p, lon, lat = imerg["precip_mm_mes"], imerg["lon"], imerg["lat"]
    poligono = shapely.simplify(cuenca, 0.002)   # ~200 m, despreciable frente a celdas de 11 km
    minx, miny, maxx, maxy = poligono.bounds
    ii = np.flatnonzero((lon + .05 > minx) & (lon - .05 < maxx))
    jj = np.flatnonzero((lat + .05 > miny) & (lat - .05 < maxy))
    i, j = np.meshgrid(ii, jj, indexing="ij")
    celdas = shapely.box(lon[i] - .05, lat[j] - .05, lon[i] + .05, lat[j] + .05)
    pesos = shapely.area(shapely.intersection(poligono, celdas))
    pesos = pesos / pesos.sum()
    serie = np.nansum(p[:, i, j] * pesos[None], axis=(1, 2))
    return pd.Series(serie, index=pd.PeriodIndex(imerg["fechas"], freq="M")).reindex(MESES)


def precipitacion_pluviometros(cuenca):
    """PL: promedio de los pluviómetros dentro de la divisoria que tengan dato ese mes, sin los tramos excluidos."""
    with zipfile.ZipFile(ARCHIVO_PLUVIOMETROS) as z:
        crudo = z.read(z.namelist()[0])
    # el portal DHIME entregó unas descargas en UTF-8 y otras en latin-1
    texto = crudo.decode("utf-8") if b"\xc3" in crudo else crudo.decode("latin-1")
    d = pd.read_csv(io.StringIO(texto))
    d["mes"] = pd.to_datetime(d["Fecha"]).dt.to_period("M")
    d = d[(d["mes"] >= MESES[0]) & (d["mes"] <= MESES[-1])]

    cne = pd.read_csv(ARCHIVO_CNE, dtype={"codigo": str})
    cne["codigo"] = cne["codigo"].astype(int)
    cne = cne[cne["codigo"].isin(d["CodigoEstacion"].unique())]
    puntos = gpd.points_from_xy(cne["longitud"], cne["latitud"], crs=4326)
    dentro = cne.loc[puntos.within(cuenca), "codigo"].tolist()
    print(f"PL: {len(dentro)} de {cne.shape[0]} pluviómetros dentro de la divisoria")

    for codigo, desde, hasta in EXCLUSIONES_PL:
        quitar = ((d["CodigoEstacion"] == codigo) & (d["mes"] >= pd.Period(desde, "M"))
                  & (d["mes"] <= pd.Period(hasta, "M")))
        d = d[~quitar]
    tabla = d[d["CodigoEstacion"].isin(dentro)].pivot(index="mes", columns="CodigoEstacion", values="Valor")
    return tabla.mean(axis=1).reindex(MESES)


def almacenamiento_suelo():
    """S: agua en las 4 capas de suelo de ERA5-Land (0-289 cm), en mm, media de cada mes, promedio de la cuenca."""
    por_punto = {}
    for punto in PESOS_PUNTOS:
        s = pd.read_csv(CARPETA_SUELO / f"suelo_punto_{punto}.csv", parse_dates=["valid_time"])
        s["lamina_mm"] = sum(s[capa] * espesor for capa, espesor in ESPESOR_CAPAS_MM.items())
        # hora UTC -> hora local (UTC−5), como el resto del punto 1
        s["mes"] = (s["valid_time"] - pd.Timedelta(hours=5)).dt.to_period("M")
        por_punto[punto] = s.groupby("mes")["lamina_mm"].mean()
    tabla = pd.DataFrame(por_punto).reindex(MESES)
    pesos = pd.Series(PESOS_PUNTOS)
    return (tabla * pesos).sum(axis=1, min_count=len(pesos)) / pesos.sum()


def main():
    cuenca = cargar_cuenca()
    mensual = pd.DataFrame({
        "PI": precipitacion_imerg(cuenca),
        "PL": precipitacion_pluviometros(cuenca),
        "Q": caudal_mensual(),
        "S_suelo": almacenamiento_suelo(),
    })
    # ΔS del mes: diferencia entre la media del mes y la del anterior. Es una aproximación (lo exacto sería el valor
    # al final de cada mes); en el ciclo anual y en años completos la diferencia se cancela casi por completo.
    mensual["dS"] = mensual["S_suelo"].diff()
    for fuente in ["PI", "PL"]:
        mensual[f"ETR_{fuente}"] = mensual[fuente] - mensual["Q"]
    print(f"Meses con Q: {int(mensual['Q'].notna().sum())} de {len(MESES)}")

    # --- Camino principal: ciclo anual medio con los meses que tienen Q
    con_q = mensual[mensual["Q"].notna()]
    ciclo = con_q.groupby(con_q.index.month)[["PI", "PL", "Q", "ETR_PI", "ETR_PL"]].mean()
    meses_por_mes = con_q.groupby(con_q.index.month).size()
    assert len(ciclo) == 12 and meses_por_mes.min() >= 15, meses_por_mes   # cada mes con al menos 15 años de dato
    largo_plazo = ciclo.sum()

    # --- Comprobación: años con los 12 meses de Q
    anual = mensual.groupby(mensual.index.year).agg(
        meses_con_Q=("Q", "count"), PI=("PI", "sum"), PL=("PL", "sum"), Q=("Q", "sum"))
    # ΔS del año: media de diciembre menos media del diciembre anterior
    diciembres = mensual.loc[mensual.index.month == 12, "S_suelo"]
    anual["dS_suelo"] = diciembres.diff().to_numpy()
    completos = anual[anual["meses_con_Q"] == 12].copy()
    for fuente in ["PI", "PL"]:
        completos[f"ETR_{fuente}"] = completos[fuente] - completos["Q"]
        completos[f"ETR_{fuente}_con_dS"] = completos[fuente] - completos["Q"] - completos["dS_suelo"]

    # --- ΔS de largo plazo: cambio neto del almacenamiento entre el primer y el último año, por año
    s_anual = mensual["S_suelo"].groupby(mensual.index.year).mean()
    ds_neto_por_anio = (s_anual.iloc[-1] - s_anual.iloc[0]) / (len(s_anual) - 1)

    resumen = pd.DataFrame([
        {"camino": "ciclo anual medio, meses con Q", "n": int(len(con_q)), "unidad_n": "meses",
         "P_PI": largo_plazo["PI"], "P_PL": largo_plazo["PL"], "Q": largo_plazo["Q"],
         "ETR_PI": largo_plazo["ETR_PI"], "ETR_PL": largo_plazo["ETR_PL"]},
        {"camino": "años completos de Q", "n": int(len(completos)), "unidad_n": "años",
         "P_PI": completos["PI"].mean(), "P_PL": completos["PL"].mean(), "Q": completos["Q"].mean(),
         "ETR_PI": completos["ETR_PI"].mean(), "ETR_PL": completos["ETR_PL"].mean()},
        {"camino": "años completos de Q, restando ΔS del suelo", "n": int(len(completos)), "unidad_n": "años",
         "P_PI": completos["PI"].mean(), "P_PL": completos["PL"].mean(), "Q": completos["Q"].mean(),
         "ETR_PI": completos["ETR_PI_con_dS"].mean(), "ETR_PL": completos["ETR_PL_con_dS"].mean()},
    ])
    resumen["dS_suelo_neto_mm_anio"] = ds_neto_por_anio
    resumen["dS_suelo_anual_desv_est_mm"] = anual["dS_suelo"].std()

    PRODUCTOS.mkdir(parents=True, exist_ok=True)
    mensual.rename_axis("mes").round(2).to_csv(PRODUCTOS / "balance_hidrico_mensual.csv")
    completos.rename_axis("anio").round(1).to_csv(PRODUCTOS / "balance_hidrico_anual.csv")
    resumen.round(1).to_csv(PRODUCTOS / "balance_hidrico_resumen.csv", index=False)

    print("\nET real de largo plazo (mm/año):")
    print(resumen.round(0).to_string(index=False))
    print(f"\nΔS del suelo: cambio neto {ds_neto_por_anio:+.1f} mm/año (1998 a 2022); de un año a otro, desviación "
          f"estándar {anual['dS_suelo'].std():.0f} mm")
    print(f"Años completos de Q: {', '.join(str(a) for a in completos.index)}")


if __name__ == "__main__":
    main()
