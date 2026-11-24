"""Fase 7 (punto 1): la cuenca en el espacio de Budyko, ω de Fu y elasticidad del caudal a la precipitación.

Entrada: productos/punto1/et_balance_anual.csv (script 24), años calendario con los 12 meses de Q (Juan, 2026-11-23:
el año hidrológico desde febrero no redujo ΔS, así que se usa el calendario).

Tres maneras de poner la ET anual, porque la fuente de ET es una decisión de Juan que sigue abierta:
    P − Q (PI)            balance con la precipitación interpolada
    P − Q (PL)            balance con la precipitación de la Tarea 1 (PL)
    mediana de productos  columna mediana_productos del script 24: mediana del año de ERA5-Land e, GLEAM, MOD16,
                          TerraClimate, SSEBop v6.1 y v5 y la AA (los que tengan los 12 meses), con la P de cada serie
El ΔS anual del suelo (ERA5-Land, script 24) se deja fuera: es de −90 a +82 mm, frente a P − Q de 700 a 1 500 mm.

Índice de aridez φ = ETo/P (ETo Penman–Monteith FAO-56 de la cuenca); índice evaporativo ε = ET/P.

Curva de Fu (1981):  F(φ) = 1 + φ − (1 + φ^ω)^(1/ω)
ω se ajusta para que la curva pase por el punto multianual (P, Q y ETo medios del periodo). Si el punto queda por
encima del límite de energía (ε > φ, o sea ET > ETo) no hay ω que lo reproduzca: se deja vacío y se dice.

Elasticidad del caudal a la precipitación (ε_P = (dQ/Q)/(dP/P)):
    teórica, con ETo fija:  Q = P·(1 − F(φ))  ⇒  ε_P = 1 + φ·F′(φ)/(1 − F(φ)),
                            F′(φ) = 1 − φ^(ω−1)·(1 + φ^ω)^(1/ω − 1)
    empírica: estimador de mediana de Sankarasubramanian et al. (2001, doi:10.1029/2000WR900330),
              ε_P = mediana[(Q_t − Q̄)/(P_t − P̄)] · P̄/Q̄

Escribe:
    productos/punto1/budyko_anual.csv      φ y ε de cada año y cada ET
    productos/punto1/budyko_resumen.csv    punto multianual, ω, elasticidad teórica y empírica
    productos/punto1/budyko.png

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/29_budyko.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy.optimize import brentq

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA = CARPETA_PRODUCTOS / "et_balance_anual.csv"
SALIDA_ANUAL = CARPETA_PRODUCTOS / "budyko_anual.csv"
SALIDA_RESUMEN = CARPETA_PRODUCTOS / "budyko_resumen.csv"
SALIDA_PNG = CARPETA_PRODUCTOS / "budyko.png"


def fu(phi, omega):
    return 1 + phi - (1 + phi ** omega) ** (1 / omega)


def fu_derivada(phi, omega):
    return 1 - phi ** (omega - 1) * (1 + phi ** omega) ** (1 / omega - 1)


def ajustar_omega(phi, eps):
    """ω de Fu que pasa por (φ, ε). NaN si el punto queda fuera de los límites (ε ≥ min(1, φ))."""
    if not 0 < eps < min(1.0, phi):
        return np.nan
    return brentq(lambda w: fu(phi, w) - eps, 1.0 + 1e-9, 50.0)


def main():
    datos = pd.read_csv(ENTRADA)
    anual = datos[datos["tipo_de_anio"] == "calendario"].copy()   # Juan, 23 nov
    assert len(anual) > 0
    series = {
        "P − Q (PI)": (anual["PI"], anual["PI"] - anual["Q"]),
        "P − Q (PL)": (anual["PL"], anual["PL"] - anual["Q"]),
        "mediana de productos, P = PI": (anual["PI"], anual["mediana_productos"]),
        "mediana de productos, P = PL": (anual["PL"], anual["mediana_productos"]),
    }

    filas_anual, filas_resumen = [], []
    for nombre, (p, et) in series.items():
        for anio, p_t, et_t, eto_t in zip(anual["anio"], p, et, anual["ETo"]):
            filas_anual.append({"serie": nombre, "anio": anio, "P": p_t, "ET": et_t, "ETo": eto_t,
                                "phi": eto_t / p_t, "epsilon": et_t / p_t})
        p_m, et_m, eto_m, q_m = p.mean(), et.mean(), anual["ETo"].mean(), anual["Q"].mean()
        phi, eps = eto_m / p_m, et_m / p_m
        omega = ajustar_omega(phi, eps)
        if np.isnan(omega):
            teorica = np.nan
        else:
            assert abs(fu(phi, omega) - eps) < 1e-9
            teorica = 1 + phi * fu_derivada(phi, omega) / (1 - fu(phi, omega))
        filas_resumen.append({"serie": nombre, "anios": len(anual), "P_mm": p_m, "ET_mm": et_m, "ETo_mm": eto_m,
                              "phi": phi, "epsilon": eps, "omega_fu": omega, "elasticidad_teorica": teorica,
                              "nota": "" if not np.isnan(omega) else "ε > φ (ET > ETo): sobre el límite de energía"})

    # Elasticidad empírica: solo depende de P y Q.
    for nombre_p in ["PI", "PL"]:
        p, q = anual[nombre_p], anual["Q"]
        cociente = (q - q.mean()) / (p - p.mean())
        empirica = float(np.median(cociente) * p.mean() / q.mean())
        for fila in filas_resumen:
            if fila["serie"].endswith(f"({nombre_p})") or fila["serie"].endswith(f"P = {nombre_p}"):
                fila["elasticidad_empirica_sankarasubramanian"] = empirica

    # ET frente a la demanda en años secos y húmedos (mitad inferior y superior de P de cada serie).
    for fila in filas_resumen:
        p, et = series[fila["serie"]]
        seco = p <= p.median()
        fila["ET_sobre_ETo_anios_secos"] = float((et[seco] / anual["ETo"][seco]).mean())
        fila["ET_sobre_ETo_anios_humedos"] = float((et[~seco] / anual["ETo"][~seco]).mean())

    pd.DataFrame(filas_anual).round(4).to_csv(SALIDA_ANUAL, index=False)
    resumen = pd.DataFrame(filas_resumen)
    resumen.round(4).to_csv(SALIDA_RESUMEN, index=False)
    print(f"Listo: {SALIDA_ANUAL}\nListo: {SALIDA_RESUMEN}")
    print(resumen.drop(columns=["anios"]).round(3).to_string(index=False))

    fig, eje = plt.subplots(figsize=(6, 5))
    x = np.linspace(0.01, 1.2, 200)
    eje.plot(x, np.minimum(x, 1), "k-", lw=1, label="límites de energía y de agua")
    colores = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
    tabla = pd.DataFrame(filas_anual)
    for (nombre, fila), color in zip(resumen.set_index("serie").iterrows(), colores):
        t = tabla[tabla["serie"] == nombre]
        eje.scatter(t["phi"], t["epsilon"], s=12, color=color, alpha=0.5)
        eje.scatter(fila["phi"], fila["epsilon"], s=60, color=color, edgecolor="k", label=nombre)
        if not np.isnan(fila["omega_fu"]):
            eje.plot(x, fu(x, fila["omega_fu"]), color=color, lw=1, ls="--")
    eje.set_xlim(0, 1.2)
    eje.set_ylim(0, 1)
    eje.set_xlabel("φ = ETo/P")
    eje.set_ylabel("ε = ET/P")
    eje.legend(fontsize=7, loc="lower right")
    eje.set_title("Budyko, años calendario (puntos pequeños) y media (grandes)", fontsize=9)
    fig.tight_layout()
    fig.savefig(SALIDA_PNG, dpi=150)
    print(f"Listo: {SALIDA_PNG}")


if __name__ == "__main__":
    main()
