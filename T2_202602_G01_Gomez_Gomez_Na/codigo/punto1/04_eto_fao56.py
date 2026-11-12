"""Evapotranspiración de referencia ETo (FAO-56, ecuación 6) en los 6 puntos y en la cuenca del Fonce, 1998–2022.

Lee productos/punto1/era5land_diario_puntos.csv (salida de 03_series_diarias_rn.py) y escribe:
    productos/punto1/eto_diaria_puntos.csv     ETo diaria por punto (mm/día)
    productos/punto1/eto_mensual_puntos.csv    ETo mensual por punto (mm/mes) = suma de las diarias
    productos/punto1/eto_mensual_cuenca.csv    ETo mensual de la cuenca (mm/mes) = promedio de los 6 puntos
                                               ponderado por el área de su región de Voronoi

Ecuación 6 de FAO-56 (Allen et al., 1998), diaria:

    ETo = [0.408 Δ (Rn − G) + γ · 900/(T + 273) · u2 · (es − ea)] / [Δ + γ (1 + 0.34 u2)]

De dónde sale cada término:
    T     temperatura media diaria = (Tmax + Tmin)/2 (ec. 9), en °C
    Δ     pendiente de la curva de presión de saturación a T (ec. 13), kPa/°C
    es    presión de saturación media = [e°(Tmax) + e°(Tmin)]/2 (ec. 12), kPa
    ea    presión real de vapor: promedio diario de e°(Td) horario (03_series_diarias_rn.py), kPa
    γ     constante psicrométrica = 0.665·10⁻³ P (ec. 8), con P = presión media diaria sp, kPa/°C
    u2    viento a 2 m = rapidez media diaria a 10 m × 4.87/ln(67.8·10 − 5.42) (ec. 47), m/s
    Rn    radiación neta diaria (03_series_diarias_rn.py), MJ/m²·día
    G     0 a escala diaria (ec. 42)

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/04_eto_fao56.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_DIARIA = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"
SALIDA_DIARIA = CARPETA_PRODUCTOS / "eto_diaria_puntos.csv"
SALIDA_MENSUAL = CARPETA_PRODUCTOS / "eto_mensual_puntos.csv"
SALIDA_CUENCA = CARPETA_PRODUCTOS / "eto_mensual_cuenca.csv"

# Peso de cada punto = fracción del área de la cuenca en su región de Voronoi (temp/decisiones.md).
PESOS = {1: 0.124, 2: 0.173, 3: 0.120, 4: 0.146, 5: 0.186, 6: 0.252}

ALTURA_VIENTO_M = 10.0
G_DIARIO = 0.0  # ec. 42


def presion_saturacion(t_c):
    """e°(T) en kPa, FAO-56 ec. 11."""
    return 0.6108 * np.exp(17.27 * t_c / (t_c + 237.3))


def pendiente_saturacion(t_c):
    """Δ en kPa/°C, FAO-56 ec. 13."""
    return 4098 * presion_saturacion(t_c) / (t_c + 237.3) ** 2


def viento_a_2m(u_z, z=ALTURA_VIENTO_M):
    """u2 en m/s a partir del viento a z metros, FAO-56 ec. 47 (perfil logarítmico sobre pasto)."""
    return u_z * 4.87 / np.log(67.8 * z - 5.42)


def eto_fao56(diaria):
    """ETo diaria (mm/día) con la ec. 6 de FAO-56. Devuelve también sus términos para revisarlos."""
    t = (diaria["tmax_C"] + diaria["tmin_C"]) / 2                                            # ec. 9
    delta = pendiente_saturacion(t)                                                           # ec. 13
    es = (presion_saturacion(diaria["tmax_C"]) + presion_saturacion(diaria["tmin_C"])) / 2    # ec. 12
    gamma = 0.665e-3 * diaria["sp_kPa"]                                                       # ec. 8
    u2 = viento_a_2m(diaria["viento10_ms"])                                                   # ec. 47
    deficit = (es - diaria["ea_kPa"]).clip(lower=0)  # ea > es solo por redondeo; el déficit no es negativo

    termino_radiativo = 0.408 * delta * (diaria["rn_MJm2"] - G_DIARIO)
    termino_aerodinamico = gamma * 900 / (t + 273) * u2 * deficit
    denominador = delta + gamma * (1 + 0.34 * u2)
    return pd.DataFrame({
        "t_C": t, "es_kPa": es, "deficit_kPa": deficit, "u2_ms": u2,
        "eto_radiativa_mm": termino_radiativo / denominador,
        "eto_aerodinamica_mm": termino_aerodinamico / denominador,
        "eto_mm": (termino_radiativo + termino_aerodinamico) / denominador,
    }, index=diaria.index)


def main():
    diaria = pd.read_csv(ENTRADA_DIARIA, parse_dates=["fecha"])
    eto = pd.concat([diaria[["fecha", "punto"]], eto_fao56(diaria)], axis=1)

    assert eto["eto_mm"].notna().all() and (eto["eto_mm"] > 0).all()
    eto.assign(fecha=eto["fecha"].dt.strftime("%Y-%m-%d")).round(4).to_csv(SALIDA_DIARIA, index=False)
    print(f"Listo: {SALIDA_DIARIA} ({len(eto)} filas)")

    # Mensual por punto: suma de las ETo diarias del mes (mm/mes).
    mensual = (eto.set_index("fecha").groupby("punto")["eto_mm"].resample("MS").sum()
               .rename("eto_mm_mes").reset_index())
    mensual["dias"] = mensual["fecha"].dt.days_in_month
    assert (mensual.groupby("punto").size() == 300).all()
    mensual.assign(mes=mensual["fecha"].dt.strftime("%Y-%m"))[["mes", "punto", "dias", "eto_mm_mes"]] \
        .round(3).to_csv(SALIDA_MENSUAL, index=False)
    print(f"Listo: {SALIDA_MENSUAL} ({len(mensual)} filas)")

    # Cuenca: promedio ponderado por el área de Voronoi de cada punto.
    assert abs(sum(PESOS.values()) - 1) < 0.002
    mensual["peso"] = mensual["punto"].map(PESOS)
    cuenca = (mensual.assign(ponderada=mensual["eto_mm_mes"] * mensual["peso"])
              .groupby("fecha")[["ponderada", "peso"]].sum())
    cuenca["eto_mm_mes"] = cuenca["ponderada"] / cuenca["peso"]
    cuenca = cuenca.reset_index()
    cuenca.assign(mes=cuenca["fecha"].dt.strftime("%Y-%m"))[["mes", "eto_mm_mes"]] \
        .round(3).to_csv(SALIDA_CUENCA, index=False)
    print(f"Listo: {SALIDA_CUENCA} ({len(cuenca)} filas)")


if __name__ == "__main__":
    main()
