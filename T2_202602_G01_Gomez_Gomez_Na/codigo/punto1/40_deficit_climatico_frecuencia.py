"""Fase 10 (punto 1, bono 1.6): de la evapotranspiración al diseño.

Serie anual (Juan, 2026-11-25): déficit climático máximo acumulado del año,
    D(t) = max(0, D(t−1) + ETo(t) − P̄(t))      mes a mes, en mm
    déficit del año = máximo de D(t) en los meses del año calendario.
ETo = ETo Penman–Monteith (FAO-56) de la cuenca (script 04); P̄ = (PI + PL)/2 (Juan, 2026-11-24). Periodo 1998–2022.

Decisiones de este script:
    - (Juan, 2026-11-26) La suma no se reinicia en ninguna fecha fija; solo vuelve a 0 cuando la lluvia acumulada cubre el
      déficit. La suma no se reinicia el 1 de enero: la temporada seca dic–mar cruza el cambio de año y reiniciar la partiría.
      Como sensibilidad se calcula también la versión que reinicia en enero (columna deficit_reinicio_enero_mm).
    - (propuesta del agente, pendiente de Juan) Hay años sin ningún mes con ETo > P̄ (déficit 0). Las distribuciones del punto 2 no admiten ceros (LP3 usa log10),
      así que se usa la distribución mixta (probabilidad total):
          F(x) = p0 + (1 − p0)·F+(x),   p0 = fracción de años con déficit 0,  F+ ajustada a los años con déficit > 0.
      El cuantil de periodo de retorno T sale de F+(x) = (1 − 1/T − p0)/(1 − p0); si 1 − 1/T ≤ p0, el cuantil es 0.
    - (propuesta del agente, pendiente de Juan) Ajuste por momentos L (el método que eligió el punto 2) para Gumbel, GEV y LP3. IC 95 % por bootstrap de los
      25 años (se remuestrean años, con sus ceros, y se recalculan p0 y F+), 1 000 réplicas, semilla 42, como el punto 2.
    - T = 2, 5, 10 y 25 años. Con 25 años de datos, T mayores son extrapolación.

Funciones de frecuencia: las del punto 2, sin modificar (codigo/punto2/02_extremos_y_distribuciones.py:
fit_distribution, ppf, cdf, goodness, mann_kendall_sen). Se importan desde su archivo; el script falla con un mensaje
claro si ese archivo no está en la entrega.

Limitación: con datos mensuales el déficit queda subestimado, porque la lluvia de un mes compensa sus semanas secas.

Entrada: productos/punto1/et_productos_mensual.csv (script 24; columnas ETo y Pm = P̄).
Escribe en productos/punto1/:
    deficit_climatico_anual.csv        serie anual y su versión con reinicio en enero
    deficit_climatico_frecuencia.csv   cuantiles por distribución y T, con IC 95 % y bondad de ajuste
    deficit_climatico_frecuencia.png   serie anual y curva de frecuencia

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/40_deficit_climatico_frecuencia.py
"""

import importlib.util
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA = CARPETA_PRODUCTOS / "et_productos_mensual.csv"
MODULO_PUNTO2 = RAIZ_ENTREGA / "codigo" / "punto2" / "02_extremos_y_distribuciones.py"
SALIDA_SERIE = CARPETA_PRODUCTOS / "deficit_climatico_anual.csv"
SALIDA_FRECUENCIA = CARPETA_PRODUCTOS / "deficit_climatico_frecuencia.csv"
SALIDA_PNG = CARPETA_PRODUCTOS / "deficit_climatico_frecuencia.png"

ANIO_INICIO, ANIO_FIN = 1998, 2022
DISTRIBUCIONES = ("Gumbel", "GEV", "LP3")
METODO = "LMOM"                 # momentos L, como el punto 2
PERIODOS_RETORNO = (2, 5, 10, 25)
REPLICAS_BOOTSTRAP = 1000
SEMILLA = 42
COLORES = {"Gumbel": "#0072B2", "GEV": "#D55E00", "LP3": "#009E73"}


def cargar_punto2():
    """Importa el script 02 del punto 2 como módulo, sin ejecutar su main()."""
    if not MODULO_PUNTO2.exists():
        raise FileNotFoundError(f"Falta {MODULO_PUNTO2}: la fase 10 usa las funciones de frecuencia del punto 2.")
    especificacion = importlib.util.spec_from_file_location("frecuencia_punto2", MODULO_PUNTO2)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def deficit_acumulado(exceso, reiniciar):
    """D(t) = max(0, D(t−1) + exceso(t)); si reiniciar es verdadero en t, se arranca desde 0 ese mes."""
    acumulado, salida = 0.0, []
    for valor, reinicio in zip(exceso, reiniciar):
        if reinicio:
            acumulado = 0.0
        acumulado = max(0.0, acumulado + valor)
        salida.append(acumulado)
    return np.array(salida)


def serie_anual():
    d = pd.read_csv(ENTRADA)
    d["fecha"] = pd.to_datetime(d["mes"])
    d = d[(d["fecha"].dt.year >= ANIO_INICIO) & (d["fecha"].dt.year <= ANIO_FIN)].reset_index(drop=True)
    assert len(d) == 12 * (ANIO_FIN - ANIO_INICIO + 1), "faltan meses en 1998–2022"
    assert d[["ETo", "Pm"]].notna().all().all(), "ETo o P̄ con meses vacíos"
    exceso = (d["ETo"] - d["Pm"]).to_numpy()
    d["D_continuo"] = deficit_acumulado(exceso, np.zeros(len(d), dtype=bool))
    d["D_reinicio_enero"] = deficit_acumulado(exceso, (d["fecha"].dt.month == 1).to_numpy())
    d["anio"] = d["fecha"].dt.year
    anual = d.groupby("anio").agg(deficit_mm=("D_continuo", "max"),
                                  deficit_reinicio_enero_mm=("D_reinicio_enero", "max"),
                                  meses_con_deficit=("D_continuo", lambda s: int((s > 0).sum())))
    anual["mes_del_maximo"] = d.loc[d.groupby("anio")["D_continuo"].idxmax(), "fecha"].dt.month.to_numpy()
    anual.loc[anual["deficit_mm"] == 0, "mes_del_maximo"] = np.nan
    return anual.reset_index()


def cuantiles_mixtos(valores, distribucion, p2):
    """p0, parámetros de F+ y cuantiles de la distribución mixta para PERIODOS_RETORNO."""
    p0 = float(np.mean(valores == 0))
    positivos = valores[valores > 0]
    parametros = p2.fit_distribution(positivos, distribucion, METODO)
    prob_total = 1 - 1 / np.asarray(PERIODOS_RETORNO, dtype=float)
    cuantiles = np.zeros(len(PERIODOS_RETORNO))
    hay_deficit = prob_total > p0
    prob_positivos = (prob_total[hay_deficit] - p0) / (1 - p0)
    cuantiles[hay_deficit] = p2.ppf(prob_positivos, distribucion, parametros)
    return p0, parametros, cuantiles


def main():
    p2 = cargar_punto2()
    anual = serie_anual()
    anual.round(2).to_csv(SALIDA_SERIE, index=False)
    valores = anual["deficit_mm"].to_numpy()
    positivos = valores[valores > 0]
    s_mk, z_mk, p_mk, sen = p2.mann_kendall_sen(anual["anio"].to_numpy(), valores)
    print(f"Serie anual: {len(valores)} años, {int((valores == 0).sum())} con déficit 0; "
          f"media {valores.mean():.1f} mm, máximo {valores.max():.1f} mm")
    print(f"Mann-Kendall: S = {s_mk}, p = {p_mk:.3f}; Sen = {sen:.2f} mm/año")

    generador = np.random.default_rng(SEMILLA)
    filas = []
    for distribucion in DISTRIBUCIONES:
        p0, parametros, cuantiles = cuantiles_mixtos(valores, distribucion, p2)
        ks, ad, ppcc = p2.goodness(positivos, distribucion, parametros)
        replicas = np.full((REPLICAS_BOOTSTRAP, len(PERIODOS_RETORNO)), np.nan)
        for b in range(REPLICAS_BOOTSTRAP):
            remuestra = generador.choice(valores, size=len(valores), replace=True)
            try:
                replicas[b] = cuantiles_mixtos(remuestra, distribucion, p2)[2]
            except Exception:
                pass    # réplica sin ajuste posible (p. ej. fuera del dominio de momentos L); se cuenta abajo
        for j, periodo in enumerate(PERIODOS_RETORNO):
            validas = replicas[:, j][np.isfinite(replicas[:, j])]
            bajo, alto = np.percentile(validas, [2.5, 97.5])
            filas.append({"distribucion": distribucion, "metodo": METODO, "periodo_retorno_anios": periodo,
                          "deficit_mm": cuantiles[j], "ic95_bajo_mm": bajo, "ic95_alto_mm": alto,
                          "p0": p0, "n_anios": len(valores), "n_positivos": len(positivos),
                          "replicas_validas": len(validas), "KS": ks, "AD": ad, "PPCC": ppcc,
                          "MK_S": s_mk, "MK_p": p_mk, "Sen_mm_por_anio": sen})
    tabla = pd.DataFrame(filas)
    tabla.round(4).to_csv(SALIDA_FRECUENCIA, index=False)
    print(tabla[["distribucion", "periodo_retorno_anios", "deficit_mm", "ic95_bajo_mm", "ic95_alto_mm",
                 "PPCC", "replicas_validas"]].round(2).to_string(index=False))
    figura(anual, tabla, p2)
    print(f"Listo: {SALIDA_SERIE}, {SALIDA_FRECUENCIA}, {SALIDA_PNG}")


def figura(anual, tabla, p2):
    valores = anual["deficit_mm"].to_numpy()
    fig, (eje_serie, eje_frec) = plt.subplots(1, 2, figsize=(11, 4.2))

    eje_serie.bar(anual["anio"], anual["deficit_mm"], color="#999999")
    eje_serie.set_xlabel("año")
    eje_serie.set_ylabel("déficit máximo acumulado, Σ(ETo − P̄) (mm)")
    eje_serie.set_title("Serie anual, 1998–2022", fontsize=9)

    # puntos empíricos con la posición de graficación de Weibull, i/(n+1), sobre todos los años (ceros incluidos)
    ordenados = np.sort(valores)
    n = len(ordenados)
    t_empirico = 1 / (1 - np.arange(1, n + 1) / (n + 1))
    eje_frec.plot(t_empirico, ordenados, "ko", ms=4, label="años observados (Weibull)")
    t_curva = np.linspace(1.01, 50, 400)
    for distribucion in DISTRIBUCIONES:
        p0, parametros, _ = cuantiles_mixtos(valores, distribucion, p2)
        prob = 1 - 1 / t_curva
        curva = np.where(prob > p0, p2.ppf(np.clip((prob - p0) / (1 - p0), 1e-9, None), distribucion, parametros), 0)
        eje_frec.plot(t_curva, curva, color=COLORES[distribucion], lw=1.6, label=f"{distribucion} (momentos L)")
        filas = tabla[tabla["distribucion"] == distribucion]
        desplazamiento = {"Gumbel": 0.94, "GEV": 1.0, "LP3": 1.06}[distribucion]
        eje_frec.errorbar(filas["periodo_retorno_anios"] * desplazamiento, filas["deficit_mm"],
                          yerr=[filas["deficit_mm"] - filas["ic95_bajo_mm"], filas["ic95_alto_mm"] - filas["deficit_mm"]],
                          fmt="none", ecolor=COLORES[distribucion], capsize=3, lw=1)
    eje_frec.axvspan(25, 50, color="#E69F00", alpha=0.12, label="T > 25 años: extrapolación")
    eje_frec.set_xscale("log")
    eje_frec.set_xticks([1, 2, 5, 10, 25, 50])
    eje_frec.set_xticklabels(["1", "2", "5", "10", "25", "50"])
    eje_frec.set_xlim(1, 50)
    eje_frec.set_ylim(bottom=0)
    eje_frec.set_xlabel("periodo de retorno T (años)")
    eje_frec.set_ylabel("déficit (mm)")
    eje_frec.set_title("Frecuencia (distribución mixta con p0); barras = IC 95 % bootstrap", fontsize=9)
    eje_frec.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(SALIDA_PNG, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
