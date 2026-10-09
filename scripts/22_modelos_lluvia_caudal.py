"""Modelos para estimar el caudal de San Gil (Q) a partir de la lluvia: PL (pluviómetros) y PI (IMERG).

Paso 1, diagnóstico. Antes de proponer un modelo se mira qué relación sugieren los datos entre la lluvia
de un mes y el caudal de ese mismo mes, con las dos fuentes de lluvia en paralelo (regla 11):

  - forma:      ¿es una recta o se curva? Se agrega un término cuadrático y se mira si es significativo.
  - dispersión: ¿crece el error con la lluvia (heterocedasticidad)? Razón entre la varianza de los
                residuos en el tercio de meses más lluviosos y en el más seco, y Spearman entre el
                tamaño del residuo y la lluvia.
  - calendario: ¿queda en los residuos parte del ciclo anual? Kruskal-Wallis de los residuos por mes.
  - memoria:    ¿se parecen los residuos de dos meses seguidos? ¿Los explica la lluvia del mes anterior?
  - residuos:   ¿son normales (Shapiro-Wilk)? ¿Son simétricos?

Todo se hace en dos escalas: la lineal (Q contra P) y la logarítmica (ln Q contra ln P). El logaritmo es
la alternativa usual cuando la dispersión crece con el nivel: convierte un error proporcional en uno
constante. Se puede usar porque no hay meses en cero (el script lo comprueba).

Unidades: P y Q en mm/mes; Q como lámina sobre el área de la cuenca (decidido el 2026-10-09), así la
pendiente de la escala lineal se lee en mm de caudal por mm de lluvia. En la escala logarítmica, la
pendiente es una elasticidad: el % que cambia Q cuando P cambia 1 %.
Período: 1998-2022, porque es una comparación entre variables (regla 6). Muestra: los meses con Q.

Entradas:
  out/variables_mensuales.csv               Q en mm/mes, ya pasada a mensual con la regla de los 4 días
                                            (16_correlaciones_variables.py)
  out/imerg_mensual_fonce.csv               PI (05_imerg_mensual_cuencas.py)
  out/pluviometros_fonce_mensual_depurado.csv, out/pluviometros_fonce_catalogo.csv
                                            PL depurada (07_pluviometros_dhime.py)
Salida:
  out/modelos_diagnostico.csv               una fila por fuente de lluvia y escala
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
PERIODOS = pd.period_range("1998-01", "2022-12", freq="M")
FUENTES = ("PL", "PI")          # regla 11: las dos en paralelo; cuando hay que escoger, manda PL
ESCALAS = ("lineal", "logarítmica")
ALFA = 0.05                     # nivel de significancia de todas las pruebas
REZAGOS_HAC = 12                # rezagos de Newey-West, los mismos que usan las tendencias en 18_calculos_informe.py


# ------------------------------------------------------------------ datos
# Q: la de la tabla de variables de 16, que ya aplica la regla de los 4 días (a_mensual). Vacía en los meses
# a los que les faltan 5 días o más.
variables = pd.read_csv(OUT / "variables_mensuales.csv", index_col=0)
variables.index = pd.PeriodIndex(variables.index, freq="M")
caudal = variables["Q"].reindex(PERIODOS)

# PI y PL se leen completas (300 meses), igual que en 16, y no de la tabla de variables: esa tabla solo
# guarda los meses en que todas las variables tienen dato, y la lluvia del mes anterior a un mes con Q
# puede caer en un mes sin Q.
imerg = pd.read_csv(OUT / "imerg_mensual_fonce.csv")
imerg["periodo"] = pd.PeriodIndex(imerg["periodo"], freq="M")
catalogo = pd.read_csv(OUT / "pluviometros_fonce_catalogo.csv").set_index("codigo")
DENTRO = catalogo.index[catalogo["dentro_cuenca"]].tolist()     # los 7 pluviómetros dentro de la divisoria
pluvio = pd.read_csv(OUT / "pluviometros_fonce_mensual_depurado.csv", parse_dates=["fecha"])
pluvio["periodo"] = pluvio["fecha"].dt.to_period("M")
lluvia = pd.DataFrame({
    "PI": imerg[imerg.id_estacion == ID_PRINCIPAL].set_index("periodo")["p_imerg_mm"],
    # cada mes, el promedio de los pluviómetros que tienen dato; no se rellena ninguno
    "PL": pluvio.pivot(index="periodo", columns="codigo", values="precipitacion_mm")[DENTRO].mean(axis=1),
}).reindex(PERIODOS)

assert lluvia.notna().all().all(), "PI y PL deberían tener los 300 meses"
# en los meses comunes, la lluvia es la misma de la tabla de variables de 16
assert np.allclose(lluvia.loc[variables.index, ["PI", "PL"]], variables[["PI", "PL"]])
# el logaritmo exige valores positivos: ni la lluvia ni el caudal tienen meses en cero
assert (lluvia > 0).all().all() and (caudal.dropna() > 0).all()


# ------------------------------------------------------------------ herramientas
def recta(x, y):
    """Mínimos cuadrados de y = a + b·x. Devuelve (a, b), los residuos y el R²."""
    X = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    residuo = y - X @ beta
    r2 = 1 - np.sum(residuo ** 2) / np.sum((y - y.mean()) ** 2)
    return beta, residuo, r2


def ols_hac(y, X, rezagos):
    """OLS con error estándar de Newey-West (núcleo de Bartlett), como en 18_calculos_informe.py.

    Los residuos de meses vecinos se parecen; con el error estándar usual las pruebas saldrían demasiado
    seguras. Aquí los meses con Q se toman en orden, como si fueran consecutivos aunque haya vacíos entre
    ellos: es una aproximación, y se declara.
    """
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    s = u.T @ u
    for l in range(1, rezagos + 1):
        g = u[l:].T @ u[:-l]
        s += (1 - l / (rezagos + 1)) * (g + g.T)
    se = np.sqrt(np.diag(xtx_inv @ s @ xtx_inv))
    return beta, se, 2 * stats.norm.sf(np.abs(beta / se))


def transformar(serie, escala):
    return np.log(serie) if escala == "logarítmica" else serie


# ------------------------------------------------------------------ diagnóstico
def diagnostico(fuente, escala):
    datos = pd.DataFrame({"p": transformar(lluvia[fuente], escala),
                          "p_anterior": transformar(lluvia[fuente].shift(1), escala),
                          "q": transformar(caudal, escala)}).dropna(subset=["q"])
    x, y = datos.p.to_numpy(), datos.q.to_numpy()
    (a, b), e, r2 = recta(x, y)
    residuo = pd.Series(e, index=datos.index)

    # forma: término cuadrático sobre la lluvia centrada (centrarla evita que x y x² sean casi iguales)
    xc = x - x.mean()
    beta_c, _, p_c = ols_hac(y, np.column_stack([np.ones_like(xc), xc, xc ** 2]), REZAGOS_HAC)

    # dispersión: residuos ordenados por lluvia y partidos en tercios
    tercios = np.array_split(e[np.argsort(x)], 3)
    razon_tercios = np.var(tercios[-1], ddof=1) / np.var(tercios[0], ddof=1)
    rho_abs, p_abs = stats.spearmanr(np.abs(e), x)

    # calendario: ¿difieren los residuos de un mes del calendario a otro?
    por_mes = residuo.groupby(residuo.index.month)
    p_kw = stats.kruskal(*[g.to_numpy() for _, g in por_mes]).pvalue
    medias_mes = por_mes.mean()

    # memoria: residuos de meses realmente consecutivos (ambos con Q), y la lluvia del mes anterior
    en_serie = residuo.reindex(PERIODOS)
    pares = pd.concat([en_serie, en_serie.shift(1)], axis=1).dropna()
    con_anterior = datos.p_anterior.notna()
    r_ant, p_ant = stats.pearsonr(e[con_anterior], datos.p_anterior[con_anterior])

    return {
        "fuente": fuente, "escala": escala, "n_meses": len(datos),
        "intercepto_a": a, "pendiente_b": b, "r2": r2,
        "cuadratico_coef": beta_c[2], "cuadratico_p_hac": p_c[2],
        "varianza_tercio_lluvioso_sobre_seco": razon_tercios,
        "spearman_abs_residuo_lluvia": rho_abs, "spearman_abs_residuo_lluvia_p": p_abs,
        "kruskal_residuo_por_mes_p": p_kw,
        "mes_residuo_medio_max": int(medias_mes.idxmax()), "residuo_medio_max": medias_mes.max(),
        "mes_residuo_medio_min": int(medias_mes.idxmin()), "residuo_medio_min": medias_mes.min(),
        "autocorr_residuo_1_mes": pares.corr().iloc[0, 1], "n_pares_consecutivos": len(pares),
        "corr_residuo_lluvia_mes_anterior": r_ant, "corr_residuo_lluvia_mes_anterior_p": p_ant,
        "shapiro_residuo_p": stats.shapiro(e).pvalue, "asimetria_residuo": stats.skew(e),
        "minimo_lluvia_mm": lluvia[fuente].min(), "minimo_caudal_mm": caudal.min(),
    }


tabla = pd.DataFrame([diagnostico(f, s) for f in FUENTES for s in ESCALAS])
tabla.round(4).to_csv(OUT / "modelos_diagnostico.csv", index=False)

# ------------------------------------------------------------------ resumen por consola
pd.set_option("display.width", 160)
print(f"Diagnóstico de Q contra la lluvia del mismo mes, {tabla.n_meses.iloc[0]} meses con Q de {len(PERIODOS)}"
      f" (pruebas al {ALFA:.0%}; Newey-West con {REZAGOS_HAC} rezagos)")
print(tabla.set_index(["fuente", "escala"]).T.to_string(float_format=lambda v: f"{v:.4g}"))
