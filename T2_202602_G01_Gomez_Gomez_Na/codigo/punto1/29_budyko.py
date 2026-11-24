"""Fase 7 (punto 1): la cuenca en el espacio de Budyko, ω de Fu y elasticidad del caudal a la precipitación.

Entrada: productos/punto1/et_balance_anual.csv (script 24), años calendario con los 12 meses de Q (Juan, 2026-11-23:
el año hidrológico desde febrero no redujo ΔS, así que se usa el calendario).

La ET anual principal es P − Q con P̄ = (PI + PL)/2 (Juan, 2026-11-23: ET = P − Q porque ΔS anual es pequeño; P̄ porque
PI y PL son dos medidas de la misma lluvia). Juan (2026-11-24): solo P̄; las series con PI y PL se quitaron (siguen como
sensibilidad en la fase 6). Comparación:
    mediana de productos  columna mediana_productos del script 24: mediana del año de ERA5-Land e, GLEAM, MOD16,
                          TerraClimate, SSEBop v6.1 y v5 y la AA (los que tengan los 12 meses), con P̄
El ΔS anual del suelo (ERA5-Land, script 24) se deja fuera: es de −90 a +82 mm, frente a P − Q de 700 a 1 500 mm.

Índice de aridez φ = ETP/P; índice evaporativo ε = ET/P. ETP principal: ETo Penman–Monteith (FAO-56) de la cuenca.
Sensibilidad de la ETP, con P − Q (P̄) (Juan, 2026-11-24):
    Rn/λ              radiación neta de ERA5-Land (script 24): el techo de energía, la ETP original de Budyko
    Priestley–Taylor  α = 1.26 (script 21): ETP casi solo de energía
Thornthwaite se deja fuera: subestima la ETo en 38 % (fase 4).

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
ENTRADA_METODOS = CARPETA_PRODUCTOS / "metodos_mensual.csv"
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
    anual["Pm"] = (anual["PI"] + anual["PL"]) / 2   # P̄, la lluvia principal (Juan, 23 nov)
    metodos = pd.read_csv(ENTRADA_METODOS)
    metodos["anio"] = metodos["mes"].str[:4].astype(int)
    pt = metodos.groupby("anio")["priestley_taylor_mm_mes"].sum(min_count=12)
    anual["PT"] = anual["anio"].map(pt)
    eto = anual["ETo"]
    fuente_p = {}
    series = {   # nombre: (P, ET, ETP)
        "P − Q (P̄)": (anual["Pm"], anual["Pm"] - anual["Q"], eto),
        "P − Q (P̄), ETP = Rn/λ": (anual["Pm"], anual["Pm"] - anual["Q"], anual["Rn_lambda"]),
        "P − Q (P̄), ETP = Priestley–Taylor": (anual["Pm"], anual["Pm"] - anual["Q"], anual["PT"]),
        "mediana de productos, P = P̄": (anual["Pm"], anual["mediana_productos"], eto),
    }

    for nombre in series:
        fuente_p[nombre] = "Pm"
    filas_anual, filas_resumen = [], []
    for nombre, (p, et, etp) in series.items():
        validos = p.notna() & et.notna() & etp.notna()
        for anio, p_t, et_t, etp_t in zip(anual["anio"][validos], p[validos], et[validos], etp[validos]):
            filas_anual.append({"serie": nombre, "anio": anio, "P": p_t, "ET": et_t, "ETP": etp_t,
                                "phi": etp_t / p_t, "epsilon": et_t / p_t})
        p_m, et_m, eto_m = p[validos].mean(), et[validos].mean(), etp[validos].mean()
        phi, eps = eto_m / p_m, et_m / p_m
        omega = ajustar_omega(phi, eps)
        if np.isnan(omega):
            teorica = np.nan
        else:
            assert abs(fu(phi, omega) - eps) < 1e-9
            teorica = 1 + phi * fu_derivada(phi, omega) / (1 - fu(phi, omega))
        filas_resumen.append({"serie": nombre, "anios": int(validos.sum()), "P_mm": p_m, "ET_mm": et_m, "ETP_mm": eto_m,
                              "phi": phi, "epsilon": eps, "omega_fu": omega, "elasticidad_teorica": teorica,
                              "nota": "" if not np.isnan(omega) else "ε > φ (ET > ETP): sobre el límite de energía"})

    # Elasticidad empírica: solo depende de P y Q.
    for nombre_p in ["Pm"]:
        p, q = anual[nombre_p], anual["Q"]
        cociente = (q - q.mean()) / (p - p.mean())
        empirica = float(np.median(cociente) * p.mean() / q.mean())
        for fila in filas_resumen:
            if fuente_p[fila["serie"]] == nombre_p:
                fila["elasticidad_empirica_sankarasubramanian"] = empirica

    # ET frente a la demanda en años secos y húmedos (mitad inferior y superior de P de cada serie).
    for fila in filas_resumen:
        p, et, _ = series[fila["serie"]]
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
    colores = ["#000000", "#C8553D", "#882255", "#7C5BC7"]
    tabla = pd.DataFrame(filas_anual)
    for (nombre, fila), color in zip(resumen.set_index("serie").iterrows(), colores):
        t = tabla[tabla["serie"] == nombre]
        eje.scatter(t["phi"], t["epsilon"], s=12, color=color, alpha=0.5)
        eje.scatter(fila["phi"], fila["epsilon"], s=60, color=color, edgecolor="k", label=nombre)
        if not np.isnan(fila["omega_fu"]):
            eje.plot(x, fu(x, fila["omega_fu"]), color=color, lw=1, ls="--")
    eje.set_xlim(0, 1.2)
    eje.set_ylim(0, 1)
    eje.set_xlabel("φ = ETP/P (ETo salvo donde se indica)")
    eje.set_ylabel("ε = ET/P")
    eje.legend(fontsize=7, loc="lower right")
    eje.set_title("Budyko, años calendario (puntos pequeños) y media (grandes)", fontsize=9)
    fig.tight_layout()
    fig.savefig(SALIDA_PNG, dpi=150)
    print(f"Listo: {SALIDA_PNG}")


if __name__ == "__main__":
    main()
