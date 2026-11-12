"""Series mensuales de ERA5-Land en los 6 puntos de la cuenca del Fonce (San Gil), 1998–2022.

Lee las series horarias de datos/punto1/era5land_puntos/punto_N.csv (salida de 01_descarga_era5land_puntos.py)
y escribe dos productos:
    productos/punto1/era5land_viento_horario_puntos.csv   rapidez horaria del viento a 10 m (m/s), un punto por columna
    productos/punto1/era5land_mensual_puntos.csv          una fila por punto y mes (columnas abajo)

Decisiones (temp/decisiones.md):
- Los días y los meses se arman en hora local de Colombia: hora local = valid_time (UTC) − 5 h. Las 5 primeras
  horas descargadas (1997-12-31 19:00–23:00 local) quedan fuera del período; a diciembre de 2022 le faltan sus
  últimas 5 horas (31-12, 19:00–23:00 local), sin consecuencia práctica.
- Solo la radiación se acumula: ssrd es la energía que llega en cada hora (J/m²), así que el total del mes es la
  suma de sus horas y crece con el número de días del mes. Temperatura, punto de rocío, presión y viento son
  estados del aire: su suma no tiene sentido físico y se reporta el promedio del mes.
- Tmax y Tmin mensuales = promedio de las máximas y de las mínimas diarias (día local), como las usa FAO-56; no
  son el extremo absoluto del mes.
- El viento es la rapidez de cada hora, √(u10² + v10²), promediada después; promediar primero u y v cancelaría
  los vientos que cambian de dirección.

Columnas de la salida:
    mes                 AAAA-MM, hora local
    punto               1 a 6
    dias, horas         días del calendario del mes y horas con dato
    ssrd_MJm2_mes       radiación solar entrante acumulada en el mes (MJ/m²)
    t2m_media_C         temperatura media a 2 m (°C)
    tmax_media_C        promedio de las temperaturas máximas diarias (°C)
    tmin_media_C        promedio de las temperaturas mínimas diarias (°C)
    d2m_media_C         punto de rocío medio a 2 m (°C)
    sp_media_kPa        presión media en superficie (kPa)
    viento10_media_ms   rapidez media del viento a 10 m (m/s)

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/02_series_mensuales_era5land.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"
SALIDA = RAIZ_ENTREGA / "productos" / "punto1" / "era5land_mensual_puntos.csv"
SALIDA_VIENTO = RAIZ_ENTREGA / "productos" / "punto1" / "era5land_viento_horario_puntos.csv"

PUNTOS = [1, 2, 3, 4, 5, 6]
DESFASE_HORA_LOCAL = pd.Timedelta(hours=-5)  # Colombia, UTC−5, sin horario de verano
INICIO_LOCAL = pd.Timestamp("1998-01-01 00:00")
FIN_LOCAL = pd.Timestamp("2022-12-31 23:00")
KELVIN = 273.15
JULIOS_POR_MJ = 1e6


def leer_horaria_local(n):
    """Serie horaria de un punto en hora local, con las unidades que se usan aquí (°C, kPa, m/s, J/m²)."""
    horaria = pd.read_csv(CARPETA_DATOS / f"punto_{n}.csv", parse_dates=["valid_time"])
    horaria["hora_local"] = horaria["valid_time"] + DESFASE_HORA_LOCAL
    horaria = horaria[(horaria["hora_local"] >= INICIO_LOCAL) & (horaria["hora_local"] <= FIN_LOCAL)]
    return pd.DataFrame({
        "hora_local": horaria["hora_local"],
        "t2m_C": horaria["t2m"] - KELVIN,
        "d2m_C": horaria["d2m"] - KELVIN,
        "sp_kPa": horaria["sp"] / 1000.0,
        "viento10_ms": np.hypot(horaria["u10"], horaria["v10"]),
        "ssrd_Jm2": horaria["ssrd"],
    }).set_index("hora_local").sort_index()


def mensual_de_un_punto(horaria):
    """Agrega una serie horaria (hora local) a mensual según las reglas del encabezado."""
    # Extremos diarios de temperatura, por día local.
    diaria = horaria["t2m_C"].resample("D").agg(["max", "min"])

    por_mes = horaria.resample("MS")
    mensual = pd.DataFrame({
        "horas": por_mes["t2m_C"].count(),
        "ssrd_MJm2_mes": por_mes["ssrd_Jm2"].sum() / JULIOS_POR_MJ,
        "t2m_media_C": por_mes["t2m_C"].mean(),
        "tmax_media_C": diaria["max"].resample("MS").mean(),
        "tmin_media_C": diaria["min"].resample("MS").mean(),
        "d2m_media_C": por_mes["d2m_C"].mean(),
        "sp_media_kPa": por_mes["sp_kPa"].mean(),
        "viento10_media_ms": por_mes["viento10_ms"].mean(),
    })
    mensual["dias"] = mensual.index.days_in_month
    return mensual


def main():
    horarias = {n: leer_horaria_local(n) for n in PUNTOS}

    # Paso 1: rapidez horaria del viento, √(u10² + v10²), en hora local.
    viento = pd.DataFrame({f"punto_{n}": horarias[n]["viento10_ms"] for n in PUNTOS})
    assert not viento.isna().any().any()
    SALIDA_VIENTO.parent.mkdir(parents=True, exist_ok=True)
    viento.index = viento.index.strftime("%Y-%m-%d %H:00")
    viento.round(3).to_csv(SALIDA_VIENTO, index_label="hora_local")
    print(f"Listo: {SALIDA_VIENTO} ({len(viento)} horas)")

    # Paso 2: series mensuales.
    tablas = []
    for n in PUNTOS:
        mensual = mensual_de_un_punto(horarias[n])
        mensual.insert(0, "punto", n)
        tablas.append(mensual)
    salida = pd.concat(tablas)
    salida.index = salida.index.strftime("%Y-%m")
    salida.index.name = "mes"
    salida = salida.reset_index()[[
        "mes", "punto", "dias", "horas", "ssrd_MJm2_mes", "t2m_media_C", "tmax_media_C", "tmin_media_C",
        "d2m_media_C", "sp_media_kPa", "viento10_media_ms"]]

    # Comprobaciones: 300 meses por punto; todos los meses completos salvo diciembre de 2022 (5 horas menos).
    assert (salida.groupby("punto").size() == 300).all()
    incompletos = salida[salida["horas"] != salida["dias"] * 24]
    assert set(incompletos["mes"]) <= {"2022-12"}, incompletos
    assert (incompletos["horas"] == 31 * 24 - 5).all()
    assert (salida["tmin_media_C"] < salida["t2m_media_C"]).all() and (salida["t2m_media_C"] < salida["tmax_media_C"]).all()

    salida.round(3).to_csv(SALIDA, index=False)
    print(f"Listo: {SALIDA} ({len(salida)} filas)")


if __name__ == "__main__":
    main()
