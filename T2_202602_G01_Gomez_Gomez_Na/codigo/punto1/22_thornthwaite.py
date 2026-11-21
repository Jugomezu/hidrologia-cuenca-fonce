"""Fase 4 (punto 1): ETP de Thornthwaite (1948) en los 6 puntos y en la cuenca, 1998–2022. Programado paso a paso
con Juan, sin librería.

Ecuación (notas del curso de C. D. Hoyos, Parte 7):

    ETP = 16 · (L/12) · (N/30) · (10·T/I)^a          mm/mes
    I   = Σ (Tᵢ/5)^1.514                             suma sobre los 12 meses
    a   = 6.75·10⁻⁷ I³ − 7.71·10⁻⁵ I² + 0.01792 I + 0.49239

Decisiones de Juan (2026-11-20):
    - T del mes = media de las T diarias (Tmáx + Tmín)/2, la misma T que usan FAO-56 y los demás métodos.
    - I fijo: se calcula una vez por punto con las 12 medias mensuales climatológicas de 1998–2022.

Pasos (se completan uno a uno):
    1. T mensual de cada punto e índice de calor I.            <- hecho
    2. Exponente a y ETP sin corregir.
    3. Corrección por duración del día L y días del mes N.
    4. Cuenca (Voronoi) y ajuste frente a FAO-56.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/22_thornthwaite.py
"""

from pathlib import Path

import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_DIARIA = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"


def temperatura_mensual(diaria):
    """Paso 1a. T media de cada mes y punto (°C): promedio de las T diarias (Tmáx + Tmín)/2."""
    diaria = diaria.assign(t_C=(diaria["tmax_C"] + diaria["tmin_C"]) / 2)
    mensual = diaria.set_index("fecha").groupby("punto")["t_C"].resample("MS").mean().reset_index()
    assert (mensual.groupby("punto").size() == 300).all()
    return mensual


def indice_de_calor(mensual):
    """Paso 1b. I de cada punto con las 12 medias climatológicas de 1998–2022 (I fijo).

    Los meses con T ≤ 0 °C no aportan calor (no pasa en esta cuenca: el mínimo es de unos 10 °C).
    """
    climatologia = mensual.groupby(["punto", mensual["fecha"].dt.month])["t_C"].mean().unstack()
    assert climatologia.shape[1] == 12
    indice = ((climatologia.clip(lower=0) / 5) ** 1.514).sum(axis=1)
    return climatologia, indice


def main():
    diaria = pd.read_csv(ENTRADA_DIARIA, parse_dates=["fecha"])
    mensual = temperatura_mensual(diaria)
    climatologia, indice = indice_de_calor(mensual)
    print("T media climatológica por mes (°C):")
    print(climatologia.round(1).to_string())
    print("\nÍndice de calor I por punto:")
    print(indice.round(2).to_string())


if __name__ == "__main__":
    main()
