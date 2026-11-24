"""Humedad relativa media de 5 estaciones del IDEAM en la cuenca del Fonce, 1998–2022 (punto 1, texto de la fase 5).

La cita el texto de la fase 5 para explicar por qué Hargreaves sale por encima de la ETo Penman–Monteith (FAO-56):
FAO-56 (p. 64) dice que Hargreaves tiende a sobreestimar con humedad relativa alta.

Entrada (DHIME, los mismos ZIP de los scripts 13 y 18):
    datos/punto1/ideam_estaciones/dhime_t_hr_parte1_1998_2022.zip
    datos/punto1/ideam_estaciones/dhime_hr_viento_tanque_parte2_1998_2022.zip

Cálculo (decisiones de Juan, 2026-11-24):
    1. HR diaria de cada estación. Mogotes-AUT trae la HR media diaria; las otras cuatro traen solo la máxima y la
       mínima, y su HR del día es el promedio de las dos. Se descartan los días con HR fuera de 0–100 % o con la
       mínima mayor que la máxima (mismo control que el script 13).
    2. HR de cada estación = promedio de todos sus días válidos de 1998–2022. Se dejan todos los días de
       Mogotes-AUT, también los 149 de 2016–2017 con HR menor de 30 %, que parecen falla del sensor.
    3. HR de la cuenca = promedio simple de las 5 estaciones, sin pesos.

Salida: productos/punto1/hr_estaciones.csv
"""

import zipfile
from pathlib import Path

import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DHIME = RAIZ_ENTREGA / "datos" / "punto1" / "ideam_estaciones"
ZIPS_DHIME = ["dhime_t_hr_parte1_1998_2022.zip", "dhime_hr_viento_tanque_parte2_1998_2022.zip"]
SALIDA = RAIZ_ENTREGA / "productos" / "punto1" / "hr_estaciones.csv"

INICIO, FIN = "1998-01-01", "2022-12-31"
HR_MAXIMA = "Húmeda relativa calculada máxima diaria"     # así viene escrito en DHIME («Húmeda»)
HR_MINIMA = "Húmeda relativa calculada mínima diaria"
HR_MEDIA = "Humedad relativa del aire a 2 metros media diaria"
ESTACION_CON_MEDIA = "24025090"                          # Mogotes-AUT
UMBRAL_SOSPECHOSO = 30                                   # % ; solo se cuentan, no se quitan


def leer_hr():
    """Series diarias de HR de los dos ZIP de DHIME, en formato ancho (una columna por parámetro)."""
    partes = []
    for nombre in ZIPS_DHIME:
        with zipfile.ZipFile(CARPETA_DHIME / nombre) as archivo:
            with archivo.open("descargaDhime.csv") as csv:
                partes.append(pd.read_csv(csv, dtype={"CodigoEstacion": str}))
    datos = pd.concat(partes, ignore_index=True)
    datos = datos[datos["Parametro"].isin([HR_MAXIMA, HR_MINIMA, HR_MEDIA])].copy()
    datos["fecha"] = pd.to_datetime(datos["Fecha"].str[:10])
    datos = datos[(datos["fecha"] >= INICIO) & (datos["fecha"] <= FIN)]
    assert not datos.duplicated(["CodigoEstacion", "Parametro", "fecha"]).any()
    nombres = datos.groupby("CodigoEstacion")["NombreEstacion"].first()
    ancho = datos.pivot(index=["CodigoEstacion", "fecha"], columns="Parametro", values="Valor")
    return ancho, nombres


def hr_diaria(estacion, tabla):
    """HR del día (%) de una estación, con el control de calidad del script 13."""
    if estacion == ESTACION_CON_MEDIA:
        hr = tabla[HR_MEDIA]
    else:
        maxima, minima = tabla[HR_MAXIMA], tabla[HR_MINIMA]
        hr = ((maxima + minima) / 2).where(minima <= maxima)
    return hr.where((hr >= 0) & (hr <= 100)).dropna()


def main():
    ancho, nombres = leer_hr()
    filas = []
    for estacion, tabla in ancho.groupby(level="CodigoEstacion"):
        hr = hr_diaria(estacion, tabla.droplevel("CodigoEstacion"))
        filas.append({
            "estacion": estacion,
            "nombre": nombres[estacion],
            "fuente_hr_diaria": "media diaria" if estacion == ESTACION_CON_MEDIA else "(máxima + mínima) / 2",
            "dias_validos": len(hr),
            "primer_dia": hr.index.min().date(),
            "ultimo_dia": hr.index.max().date(),
            "dias_hr_menor_30": int((hr < UMBRAL_SOSPECHOSO).sum()),
            "hr_media_pct": round(hr.mean(), 2),
        })
    tabla = pd.DataFrame(filas)
    assert len(tabla) == 5, "se esperaban 5 estaciones con HR"
    hr_cuenca = tabla["hr_media_pct"].mean()
    for columna in ["dias_validos", "dias_hr_menor_30"]:
        tabla[columna] = tabla[columna].astype("Int64")
    tabla = pd.concat([tabla, pd.DataFrame([{"estacion": "promedio", "nombre": "promedio simple de las 5",
                                             "hr_media_pct": round(hr_cuenca, 1)}])], ignore_index=True)
    tabla.to_csv(SALIDA, index=False)
    print(tabla.to_string(index=False))
    print(f"\nHR media de la cuenca (promedio simple de 5 estaciones, 1998–2022): {hr_cuenca:.1f} %")
    print(f"Listo: {SALIDA.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
