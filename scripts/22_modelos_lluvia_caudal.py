"""Modelos para estimar el caudal de San Gil (Q) a partir de la lluvia: PL (pluviómetros) y PI (IMERG).

Dos partes: primero un diagnóstico, que no propone modelo; después los modelos y su comparación.

Diagnóstico. Antes de proponer un modelo se mira qué relación sugieren los datos entre la lluvia
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

Modelos. Con lo que mostró el diagnóstico (el error crece con la lluvia y el caudal tiene un mes de memoria),
se comparan cinco, de menos a más complejo, con PL y con PI:

  M0  climatología: el caudal medio de cada mes del calendario, sin lluvia (la referencia)
  M1  Q = a + b·P(t)                              la recta
  M2  Q = a + b0·P(t) + b1·P(t−1)                 la recta con la lluvia del mes anterior
  M3  ln Q = a + b·ln P(t)                        la transformación logarítmica
  M4  ln Q = a + b0·ln P(t) + b1·ln P(t−1)        la transformación y el rezago

En M3 y M4 el caudal estimado es exp(a + ...) multiplicado por el factor de Duan (1983, «smearing»): la media
de exp(residuo) en el ajuste. Sin ese factor, volver del logaritmo daría la mediana del caudal y no su media,
y el modelo quedaría sesgado hacia abajo.

Cómo se comparan (decidido por el usuario el 2026-10-09):
  - parámetros: ajustados con todos los meses, con intervalo de 95 % de Newey-West;
  - BIC: solo entre modelos de la misma escala (M1 con M2, M3 con M4), porque el de la escala logarítmica
    mide el error en ln Q y no en mm/mes;
  - error fuera del ajuste, en mm/mes para todos: (a) ajuste 1998-2014 y evaluación 2015-2022, la partición
    que ya usaba el informe; (b) validación cruzada con 5 bloques de 5 años seguidos: cada bloque se estima
    con un modelo ajustado con los otros 20 años.
Todos los modelos usan la misma muestra: los meses con Q desde 1998-02 (enero de 1998 no tiene mes anterior).

El elegido es M4 (decidido por el usuario el 2026-10-09): fuera del ajuste yerra lo mismo que M2, pero cumple
sus supuestos (error proporcional al caudal, residuos simétricos) y no puede dar caudales negativos; M2 sí,
con poca lluvia en dos meses seguidos. No se agrega la lluvia de hace dos meses (también decidido por el
usuario): la memoria más larga de la cuenca queda declarada como límite del modelo.

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
Salidas:
  out/modelos_diagnostico.csv               diagnóstico: una fila por fuente de lluvia y escala
  out/modelos_parametros.csv                parámetros de M1 a M4 con todos los meses, con su intervalo de 95 %
  out/modelos_ajuste.csv                    R², BIC y diagnóstico de los residuos de cada modelo
  out/modelos_evaluacion.csv                errores fuera del ajuste: partición, validación cruzada y cada bloque
  out/modelos_ficha.csv                     la ficha del modelo elegido, M4: una fila por fuente de lluvia
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
NIVEL_IC = 0.95                 # nivel de los intervalos de los parámetros
# los modelos: nombre -> (escala, ¿usa la lluvia del mes anterior?)
MODELOS = {"M1": ("lineal", False), "M2": ("lineal", True),
           "M3": ("logarítmica", False), "M4": ("logarítmica", True)}
ELEGIDO = "M4"                   # el modelo de la ficha (decidido por el usuario el 2026-10-09)
COMPETIDOR = "M2"                # el otro con el mismo error, contra el que se justifica la elección
REFERENCIA = "M0"                # la climatología mensual de Q
PARTICION = {"ajuste": ("1998-01", "2014-12"), "evaluacion": ("2015-01", "2022-12")}
BLOQUES_VC = [(1998, 2002), (2003, 2007), (2008, 2012), (2013, 2017), (2018, 2022)]   # 5 bloques de 5 años


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

# área del polígono de San Gil (geodésica), medida por 02_shp_cuencas_estaciones.py: la única fuente del área
AREA_KM2 = float(pd.read_csv(OUT / "shp_fonce/areas_cuencas.csv").set_index("gauge_id").loc[ID_PRINCIPAL, "area_km2"])

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


def ols_hac_cov(y, X, rezagos):
    """OLS con la matriz de covarianza de Newey-West (núcleo de Bartlett), como en 18_calculos_informe.py.

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
    return beta, xtx_inv @ s @ xtx_inv


def ols_hac(y, X, rezagos):
    """Coeficientes, error estándar de Newey-West y p (aproximación normal)."""
    beta, cov = ols_hac_cov(y, X, rezagos)
    se = np.sqrt(np.diag(cov))
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

# ------------------------------------------------------------------ modelos
# La misma muestra para todos: meses con Q que tienen mes anterior dentro del período.
MUESTRA = caudal.dropna().index[caudal.dropna().index > PERIODOS[0]]


def matriz(fuente, modelo, indice):
    """Columnas del modelo: la constante, la lluvia del mes y, si el modelo la usa, la del mes anterior."""
    escala, con_rezago = MODELOS[modelo]
    p = transformar(lluvia[fuente], escala)
    columnas = [np.ones(len(indice)), p.loc[indice].to_numpy()]
    if con_rezago:
        columnas.append(p.shift(1).loc[indice].to_numpy())
    return np.column_stack(columnas)


def ajustar(fuente, modelo, indice):
    """Ajusta el modelo con los meses de `indice`. Devuelve coeficientes, residuos y el factor de Duan."""
    escala = MODELOS[modelo][0]
    X, y = matriz(fuente, modelo, indice), transformar(caudal.loc[indice], escala).to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    residuo = y - X @ beta
    duan = np.mean(np.exp(residuo)) if escala == "logarítmica" else 1.0
    return {"beta": beta, "residuo": residuo, "duan": duan}


def estimar(fuente, modelo, ajuste, indice):
    """Caudal estimado en mm/mes para los meses de `indice`."""
    lineal = matriz(fuente, modelo, indice) @ ajuste["beta"]
    if MODELOS[modelo][0] == "logarítmica":
        lineal = np.exp(lineal) * ajuste["duan"]
    return pd.Series(lineal, index=indice)


def climatologia(indice_ajuste, indice):
    """M0: el caudal medio de cada mes del calendario en los meses de ajuste."""
    medias = caudal.loc[indice_ajuste].groupby(indice_ajuste.month).mean()
    return pd.Series(medias.loc[indice.month].to_numpy(), index=indice)


def estimar_cualquiera(fuente, modelo, indice_ajuste, indice):
    if modelo == REFERENCIA:
        return climatologia(indice_ajuste, indice)
    return estimar(fuente, modelo, ajustar(fuente, modelo, indice_ajuste), indice)


def metricas(observado, estimado):
    """Errores en mm/mes (estimado − observado) y NSE (Nash-Sutcliffe: 1 es perfecto, 0 es tan bueno
    como usar la media de los meses evaluados)."""
    error = estimado - observado
    return {"n_meses": len(error), "rmse": float(np.sqrt(np.mean(error ** 2))), "mae": float(np.mean(np.abs(error))),
            "sesgo": float(np.mean(error)),
            "nse": float(1 - np.sum(error ** 2) / np.sum((observado - observado.mean()) ** 2)),
            "estimados_negativos": int((estimado < 0).sum())}


# --- parámetros y ajuste con todos los meses
filas_parametros, filas_ajuste = [], []
z = stats.norm.ppf(0.5 + NIVEL_IC / 2)
for fuente in FUENTES:
    for modelo, (escala, con_rezago) in MODELOS.items():
        X = matriz(fuente, modelo, MUESTRA)
        y = transformar(caudal.loc[MUESTRA], escala).to_numpy()
        beta, se, p = ols_hac(y, X, REZAGOS_HAC)
        nombres = ["a", "b0", "b1"] if con_rezago else ["a", "b"]
        for nombre, valor, error_estandar, p_valor in zip(nombres, beta, se, p):
            filas_parametros.append({"fuente": fuente, "modelo": modelo, "escala": escala, "parametro": nombre,
                                     "valor": valor, "error_newey_west": error_estandar,
                                     "ic95_inferior": valor - z * error_estandar,
                                     "ic95_superior": valor + z * error_estandar, "p": p_valor})

        ajuste = ajustar(fuente, modelo, MUESTRA)
        e = ajuste["residuo"]
        n, k = len(y), X.shape[1]
        residuo = pd.Series(e, index=MUESTRA)
        en_serie = residuo.reindex(PERIODOS)
        # ¿sigue curvada la relación con el rezago incluido? término cuadrático sobre la lluvia del mes, centrada
        xc = X[:, 1] - X[:, 1].mean()
        _, _, p_c = ols_hac(y, np.column_stack([X, xc ** 2]), REZAGOS_HAC)
        estimado = estimar(fuente, modelo, ajuste, MUESTRA)
        filas_ajuste.append({
            "fuente": fuente, "modelo": modelo, "escala": escala, "n_meses": n, "n_parametros": k,
            "r2_en_su_escala": 1 - np.sum(e ** 2) / np.sum((y - y.mean()) ** 2),
            # R² del caudal en mm/mes, el mismo para las dos escalas: sí se puede comparar entre M1 y M4
            "r2_en_mm": metricas(caudal.loc[MUESTRA], estimado)["nse"],
            "bic": n * np.log(np.sum(e ** 2) / n) + k * np.log(n),
            "factor_duan": ajuste["duan"],
            "cuadratico_p_hac": p_c[-1],
            "varianza_tercio_lluvioso_sobre_seco": (lambda t: np.var(t[-1], ddof=1) / np.var(t[0], ddof=1))(
                np.array_split(e[np.argsort(X[:, 1])], 3)),
            "kruskal_residuo_por_mes_p": stats.kruskal(*[g.to_numpy() for _, g in residuo.groupby(residuo.index.month)]).pvalue,
            "autocorr_residuo_1_mes": pd.concat([en_serie, en_serie.shift(1)], axis=1).dropna().corr().iloc[0, 1],
            "shapiro_residuo_p": stats.shapiro(e).pvalue,
            "estimados_negativos": int((estimado < 0).sum()),
        })
parametros, ajustes = pd.DataFrame(filas_parametros), pd.DataFrame(filas_ajuste)
# BIC: diferencia con el mejor modelo de la misma fuente y la misma escala (0 = el mejor)
ajustes["delta_bic_en_su_escala"] = ajustes.bic - ajustes.groupby(["fuente", "escala"]).bic.transform("min")

# --- errores fuera del ajuste
filas_evaluacion = []
todos = [REFERENCIA, *MODELOS]
for fuente in FUENTES:
    # (a) partición: ajuste 1998-2014, evaluación 2015-2022
    indice_aj = MUESTRA[(MUESTRA >= PARTICION["ajuste"][0]) & (MUESTRA <= PARTICION["ajuste"][1])]
    indice_ev = MUESTRA[(MUESTRA >= PARTICION["evaluacion"][0]) & (MUESTRA <= PARTICION["evaluacion"][1])]
    for modelo in todos:
        estimado = estimar_cualquiera(fuente, modelo, indice_aj, indice_ev)
        filas_evaluacion.append({"fuente": fuente, "modelo": modelo, "esquema": "partición 2015-2022",
                                 **metricas(caudal.loc[indice_ev], estimado)})
    # (b) validación cruzada por bloques: cada bloque se estima con los otros cuatro
    for modelo in todos:
        estimados = []
        for inicio, fin in BLOQUES_VC:
            en_bloque = (MUESTRA.year >= inicio) & (MUESTRA.year <= fin)
            estimado = estimar_cualquiera(fuente, modelo, MUESTRA[~en_bloque], MUESTRA[en_bloque])
            estimados.append(estimado)
            filas_evaluacion.append({"fuente": fuente, "modelo": modelo, "esquema": f"bloque {inicio}-{fin}",
                                     **metricas(caudal.loc[MUESTRA[en_bloque]], estimado)})
        estimado = pd.concat(estimados).sort_index()
        assert estimado.index.equals(MUESTRA)          # cada mes se estimó una vez, sin haberlo visto
        filas_evaluacion.append({"fuente": fuente, "modelo": modelo, "esquema": "validación cruzada",
                                 **metricas(caudal.loc[MUESTRA], estimado)})
evaluacion = pd.DataFrame(filas_evaluacion)

# ------------------------------------------------------------------ la ficha del modelo elegido
# Q̂ = D · e^a · P(t)^b0 · P(t−1)^b1, en mm/mes. Todo lo que dice la ficha sale de las tablas de arriba o de
# los datos de la muestra; los textos de los supuestos se escriben en el informe a partir de estas cifras.
_ev_vc = evaluacion[evaluacion.esquema == "validación cruzada"].set_index(["fuente", "modelo"])
_ev_bl = evaluacion[evaluacion.esquema.str.startswith("bloque")].set_index(["fuente", "modelo"])
filas_ficha = []
for fuente in FUENTES:
    X = matriz(fuente, ELEGIDO, MUESTRA)
    y = transformar(caudal.loc[MUESTRA], "logarítmica").to_numpy()
    beta, cov = ols_hac_cov(y, X, REZAGOS_HAC)
    a, b0, b1 = beta
    # b0 + b1: cuánto cambia Q, en %, si la lluvia de los dos meses cambia 1 %; 1 sería proporcionalidad
    suma, se_suma = b0 + b1, float(np.sqrt(cov[1, 1] + cov[2, 2] + 2 * cov[1, 2]))
    fila_aj = ajustes.set_index(["fuente", "modelo"]).loc[(fuente, ELEGIDO)]
    residuo = pd.Series(ajustar(fuente, ELEGIDO, MUESTRA)["residuo"], index=MUESTRA)
    ajustado = y - residuo.to_numpy()
    # M2 da caudal negativo cuando a + (b0 + b1)·P < 0 con la misma lluvia P en los dos meses
    a2, b0_2, b1_2 = parametros.query("fuente == @fuente and modelo == @COMPETIDOR").valor.to_numpy()
    filas_ficha.append({
        "fuente": fuente, "modelo": ELEGIDO, "n_meses": len(MUESTRA),
        "a": a, "b0": b0, "b1": b1, "factor_duan": fila_aj.factor_duan,
        "coeficiente_C": fila_aj.factor_duan * np.exp(a),           # Q̂ = C · P(t)^b0 · P(t−1)^b1
        "b0_mas_b1": suma, "b0_mas_b1_ic95_inferior": suma - z * se_suma, "b0_mas_b1_ic95_superior": suma + z * se_suma,
        # rango de aplicación: lo que vio el ajuste
        "lluvia_mes_min": lluvia[fuente].loc[MUESTRA].min(), "lluvia_mes_max": lluvia[fuente].loc[MUESTRA].max(),
        "lluvia_mes_anterior_min": lluvia[fuente].shift(1).loc[MUESTRA].min(),
        "lluvia_mes_anterior_max": lluvia[fuente].shift(1).loc[MUESTRA].max(),
        "caudal_min": caudal.loc[MUESTRA].min(), "caudal_max": caudal.loc[MUESTRA].max(),
        "area_km2": AREA_KM2,
        # supuestos
        "cuadratico_p_hac": fila_aj.cuadratico_p_hac,
        "autocorr_residuo_1_mes": fila_aj.autocorr_residuo_1_mes,
        "varianza_tercio_lluvioso_sobre_seco": fila_aj.varianza_tercio_lluvioso_sobre_seco,
        "spearman_abs_residuo_ajustado_p": stats.spearmanr(np.abs(residuo), ajustado)[1],
        "shapiro_residuo_p": fila_aj.shapiro_residuo_p, "asimetria_residuo": stats.skew(residuo),
        "kruskal_residuo_por_mes_p": fila_aj.kruskal_residuo_por_mes_p,
        "pluviometros_min_por_mes": int(pluvio.pivot(index="periodo", columns="codigo", values="precipitacion_mm")[DENTRO]
                                        .reindex(MUESTRA).notna().sum(axis=1).min()) if fuente == "PL" else np.nan,
        # por qué se eligió: mismo error que M2, y la lluvia con que M2 se vuelve negativo
        "rmse_vc": _ev_vc.loc[(fuente, ELEGIDO), "rmse"], "rmse_vc_competidor": _ev_vc.loc[(fuente, COMPETIDOR), "rmse"],
        "rmse_bloques_min": _ev_bl.loc[(fuente, ELEGIDO), "rmse"].min(),
        "rmse_bloques_max": _ev_bl.loc[(fuente, ELEGIDO), "rmse"].max(),
        "nse_vc": _ev_vc.loc[(fuente, ELEGIDO), "nse"], "nse_vc_climatologia": _ev_vc.loc[(fuente, REFERENCIA), "nse"],
        "lluvia_q_cero_competidor": -a2 / (b0_2 + b1_2) if a2 < 0 else np.nan,
    })
ficha = pd.DataFrame(filas_ficha)
# lo que la ficha afirma: el elegido nunca da negativos, y la diferencia de error con M2 es menor que lo que
# cambia el error de M4 de un bloque a otro
assert (ajustes.query("modelo == @ELEGIDO").estimados_negativos == 0).all()
assert all(abs(f.rmse_vc - f.rmse_vc_competidor) < f.rmse_bloques_max - f.rmse_bloques_min for f in ficha.itertuples())

parametros.round(6).to_csv(OUT / "modelos_parametros.csv", index=False)
ficha.round(6).to_csv(OUT / "modelos_ficha.csv", index=False)
ajustes.round(6).to_csv(OUT / "modelos_ajuste.csv", index=False)
evaluacion.round(4).to_csv(OUT / "modelos_evaluacion.csv", index=False)


# ------------------------------------------------------------------ resumen por consola
pd.set_option("display.width", 160)
print(f"Diagnóstico de Q contra la lluvia del mismo mes, {tabla.n_meses.iloc[0]} meses con Q de {len(PERIODOS)}"
      f" (pruebas al {ALFA:.0%}; Newey-West con {REZAGOS_HAC} rezagos)")
print(tabla.set_index(["fuente", "escala"]).T.to_string(float_format=lambda v: f"{v:.4g}"))

print(f"\nModelos con todos los meses ({len(MUESTRA)}), parámetros con intervalo de {NIVEL_IC:.0%} (Newey-West)")
print(parametros.to_string(index=False, float_format=lambda v: f"{v:.4g}"))
print(ajustes.set_index(["fuente", "modelo"]).T.to_string(float_format=lambda v: f"{v:.4g}"))
print("\nErrores fuera del ajuste (mm/mes)")
resumen = evaluacion[~evaluacion.esquema.str.startswith("bloque")]
print(resumen.pivot_table(index=["fuente", "modelo"], columns="esquema", values=["rmse", "nse", "sesgo"]).round(2).to_string())
print("\nRMSE por bloque de la validación cruzada (mm/mes)")
print(evaluacion[evaluacion.esquema.str.startswith("bloque")].pivot_table(
    index=["fuente", "modelo"], columns="esquema", values="rmse").round(1).to_string())

print(f"\nFicha de {ELEGIDO}: Q̂ = C · P(t)^b0 · P(t−1)^b1, en mm/mes")
print(ficha.set_index("fuente").T.to_string(float_format=lambda v: f"{v:.4g}"))
