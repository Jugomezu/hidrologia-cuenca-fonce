"""Fase 8 (punto 1): cambios en la demanda atmosférica, 1998–2022.

1. Tendencias de la ETo Penman–Monteith (FAO-56), de Thornthwaite y de sus forzantes (T, ea, u2, Rs), promedio de la
   cuenca (Voronoi), con los métodos de la Tarea 1 (Analisis_De_Cuenca/scripts/18_calculos_informe.py):
     - OLS sobre los 300 meses con una constante por mes del calendario (el ciclo anual no arrastra la pendiente) y
       error estándar de Newey-West con 12 rezagos (autocorrelación y heterocedasticidad).
     - Mann-Kendall estacional (Hirsch et al., 1982) con pendiente de Sen; p por permutación de años completos
       (conserva el ciclo y la dependencia dentro del año) e IC 95 % de Sen remuestreando años completos.
     - Mann-Kendall con la corrección de Hamed y Rao (1998) sobre las anomalías mensuales (dependencia temporal).
     - Pettitt (1979) sobre la media anual de las anomalías: ¿salto de nivel en vez de tendencia gradual?
     - Control de la tasa de falsos descubrimientos (Benjamini y Hochberg, 1995) sobre las 6 series, por método.
     - Sensibilidad a los extremos del registro: se repite la OLS quitando los primeros y los últimos AÑOS_EXTREMO años.
     - Dependencia: autocorrelación de lag 1 de las anomalías.
2. Atribución de la tendencia de la ETo: sensibilidad del script 28 (cambio % de la ETo anual por +1 °C con ea
   constante, +10 % de u2, −10 % de Rs, +10 % de ea) × tendencia relativa de cada forzante. Suma frente a la tendencia
   directa; la diferencia es el residuo (no linealidad, interacción, covariación entre meses y lo que la
   linealización no capta).
3. Tabla ETo frente a Thornthwaite.

Periodo 1998–2022 (el de toda la ETo, decidido el 17 nov); la Tarea 1 hizo tendencias desde 1981 con otras variables.
Tanque evaporímetro del DHIME: no entra (unidades imposibles, ver anexos/decisiones.md).

Escribe productos/punto1/tendencias_demanda.csv, atribucion_eto.csv, tendencias_demanda.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/32_tendencias_demanda.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_DIARIA = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"
ENTRADA_ETO = CARPETA_PRODUCTOS / "eto_mensual_cuenca.csv"
ENTRADA_METODOS = CARPETA_PRODUCTOS / "metodos_mensual.csv"
ENTRADA_SENSIBILIDAD = CARPETA_PRODUCTOS / "sensibilidad.csv"
SALIDA_TENDENCIAS = CARPETA_PRODUCTOS / "tendencias_demanda.csv"
SALIDA_ATRIBUCION = CARPETA_PRODUCTOS / "atribucion_eto.csv"
SALIDA_FIGURA = CARPETA_PRODUCTOS / "tendencias_demanda.png"

PESOS = {1: 0.124, 2: 0.173, 3: 0.120, 4: 0.146, 5: 0.186, 6: 0.252}   # Voronoi, los mismos del script 04
ALFA = 0.05                 # significancia (Tarea 1, decidida el 2026-10-09)
Q_FDR = 0.05                # Benjamini-Hochberg (Tarea 1)
REZAGOS_NW = 12             # Newey-West (Tarea 1)
REMUESTREOS = 400           # permutaciones y remuestreos de años (Tarea 1)
SEMILLA = 23                # la misma de la Tarea 1
AÑOS_EXTREMO = 3            # años que se quitan al inicio o al final en la prueba de extremos
rng = np.random.default_rng(SEMILLA)

NOMBRES = {"eto": "ETo Penman–Monteith (FAO-56)", "thornthwaite": "Thornthwaite", "t": "T media",
           "ea": "ea", "u2": "u2", "rs": "Rs"}
UNIDADES = {"eto": "mm/mes", "thornthwaite": "mm/mes", "t": "°C", "ea": "kPa", "u2": "m/s", "rs": "MJ/m²·d"}


# ---------------------------------------------------------------- series mensuales de la cuenca
def forzantes_mensuales():
    """Media mensual de T, ea, u2 y Rs diarios de cada punto, y promedio de la cuenca con los pesos de Voronoi."""
    d = pd.read_csv(ENTRADA_DIARIA, parse_dates=["fecha"])
    d["t"] = (d["tmax_C"] + d["tmin_C"]) / 2                        # la T de FAO-56 (ec. 9), la que usa la ETo
    d["ea"] = d["ea_kPa"]
    d["u2"] = d["viento10_ms"] * 4.87 / np.log(67.8 * 10 - 5.42)    # FAO-56 ec. 47, igual que el script 04
    d["rs"] = d["rs_MJm2"]
    d["mes"] = d["fecha"].dt.to_period("M")
    mensual = d.groupby(["mes", "punto"])[["t", "ea", "u2", "rs"]].mean().reset_index()
    peso = mensual["punto"].map(PESOS)
    cuenca = mensual[["t", "ea", "u2", "rs"]].mul(peso, axis=0).groupby(mensual["mes"]).sum()
    return cuenca.div(peso.groupby(mensual["mes"]).sum(), axis=0)


def series_cuenca():
    eto = pd.read_csv(ENTRADA_ETO)
    metodos = pd.read_csv(ENTRADA_METODOS)
    tabla = pd.DataFrame({"eto": eto["eto_mm_mes"].to_numpy(),
                          "thornthwaite": metodos["thornthwaite_mm_mes"].to_numpy()},
                         index=pd.PeriodIndex(eto["mes"], freq="M"))
    assert (metodos["mes"].to_numpy() == eto["mes"].to_numpy()).all()
    tabla = tabla.join(forzantes_mensuales())
    assert len(tabla) == 300 and tabla.notna().all().all()
    return tabla


# ---------------------------------------------------------------- pruebas (las de la Tarea 1)
def t_decimal(periodos):
    return np.asarray(periodos.year + (periodos.month - 0.5) / 12, dtype=float)


def ols_hac(y, X, rezagos):
    """OLS con error estándar de Newey-West (núcleo de Bartlett). Devuelve coeficientes, errores y p (normal)."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    s = u.T @ u
    for rezago in range(1, rezagos + 1):
        g = u[rezago:].T @ u[:-rezago]
        s += (1 - rezago / (rezagos + 1)) * (g + g.T)
    se = np.sqrt(np.diag(xtx_inv @ s @ xtx_inv))
    return beta, se, 2 * stats.norm.sf(np.abs(beta / se))


def ols_estacional(serie):
    """Pendiente por década con una constante por mes del calendario, su IC 95 % y p (Newey-West)."""
    t, meses = t_decimal(serie.index), np.asarray(serie.index.month)
    indicadoras = (meses[:, None] == np.arange(1, 13)[None, :]).astype(float)
    b, se, p = ols_hac(serie.to_numpy(), np.column_stack([t, indicadoras]), REZAGOS_NW)
    return b[0] * 10, (b[0] - 1.96 * se[0]) * 10, (b[0] + 1.96 * se[0]) * 10, p[0]


def mk_estacional(t, y, meses):
    """Mann-Kendall estacional y pendiente estacional de Sen (por año)."""
    pendientes = []
    for m in np.unique(meses):
        tm, ym = t[meses == m], y[meses == m]
        i, j = np.triu_indices(len(ym), 1)
        dt = tm[j] - tm[i]
        validos = dt != 0
        pendientes.extend((ym[j] - ym[i])[validos] / dt[validos])
    return float(np.median(pendientes))


def s_estacional(t, y, meses):
    total = 0.0
    for m in np.unique(meses):
        ym = y[meses == m][np.argsort(t[meses == m])]
        total += np.sign(ym[None, :] - ym[:, None])[np.triu_indices(len(ym), 1)].sum()
    return total


def mk_estacional_perm(serie):
    """Sen estacional por década, IC 95 % remuestreando años completos y p permutando años completos."""
    t, meses, anios = t_decimal(serie.index), np.asarray(serie.index.month), np.asarray(serie.index.year)
    y = serie.to_numpy()
    pendiente = mk_estacional(t, y, meses)
    s_obs = s_estacional(t, y, meses)
    unicos = np.unique(anios)
    pos = {a: np.where(anios == a)[0] for a in unicos}
    s_perm, pend_bs = np.empty(REMUESTREOS), np.empty(REMUESTREOS)
    for b in range(REMUESTREOS):
        orden = dict(zip(unicos, rng.permutation(unicos)))            # cada año recibe el tiempo de otro año
        t_perm = np.array([orden[a] for a in anios]) + (t - anios)
        s_perm[b] = s_estacional(t_perm, y, meses)
        idx = np.concatenate([pos[a] for a in rng.choice(unicos, len(unicos))])
        pend_bs[b] = mk_estacional(t[idx], y[idx], meses[idx])
    p = (np.sum(np.abs(s_perm) >= abs(s_obs)) + 1) / (REMUESTREOS + 1)
    return pendiente * 10, np.percentile(pend_bs, 2.5) * 10, np.percentile(pend_bs, 97.5) * 10, float(p)


def mk_hamed_rao(t, y):
    """Mann-Kendall con la corrección de varianza de Hamed y Rao (1998) por autocorrelación."""
    n = len(y)
    S = np.sign(y[None, :] - y[:, None])[np.triu_indices(n, 1)].sum()
    var = n * (n - 1) * (2 * n + 5) / 18
    pend = stats.theilslopes(y, t)[0]
    rangos = stats.rankdata(y - pend * t)
    rangos = rangos - rangos.mean()
    lim = 1.96 / np.sqrt(n)
    suma = 0.0
    for k in range(1, n - 1):
        rk = np.sum(rangos[k:] * rangos[:-k]) / np.sum(rangos ** 2)
        if abs(rk) > lim:
            suma += (n - k) * (n - k - 1) * (n - k - 2) * rk
    factor = max(1 + 2 / (n * (n - 1) * (n - 2)) * suma, 1e-6)
    z = (S - np.sign(S)) / np.sqrt(var * factor)
    return float(2 * stats.norm.sf(abs(z))), float(factor)


def pettitt(x):
    """Prueba de Pettitt (1979): índice del último elemento del primer tramo y p aproximado."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    u = np.cumsum(np.sign(x[:, None] - x[None, :]).sum(axis=1))[:-1]
    k = int(np.argmax(np.abs(u)))
    return k, min(1.0, 2 * np.exp(-6 * float(abs(u[k])) ** 2 / (n ** 3 + n ** 2)))


def benjamini_hochberg(p):
    p = np.asarray(p, dtype=float)
    n = len(p)
    orden = np.argsort(p)
    ajustado = np.minimum.accumulate((p[orden] * n / np.arange(1, n + 1))[::-1])[::-1]
    q = np.empty(n)
    q[orden] = np.minimum(ajustado, 1)
    return q


def anomalias(serie):
    """Anomalía mensual: el valor menos la media 1998–2022 de su mes del calendario."""
    return serie - serie.groupby(serie.index.month).transform("mean")


def tendencias(tabla):
    filas = []
    for v in NOMBRES:
        serie = tabla[v]
        media = serie.mean()
        ols, ols_inf, ols_sup, p_ols = ols_estacional(serie)
        sen, sen_inf, sen_sup, p_mk = mk_estacional_perm(serie)
        anom = anomalias(serie)
        p_hr, factor_hr = mk_hamed_rao(t_decimal(anom.index), anom.to_numpy())
        anual = anom.groupby(anom.index.year).mean()
        k, p_pettitt = pettitt(anual.to_numpy())
        sin_inicio = ols_estacional(serie[serie.index.year >= 1998 + AÑOS_EXTREMO])
        sin_final = ols_estacional(serie[serie.index.year <= 2022 - AÑOS_EXTREMO])
        filas.append({
            "variable": NOMBRES[v], "clave": v, "unidad": UNIDADES[v], "media": media,
            "ols_por_decada": ols, "ols_ic95_inf": ols_inf, "ols_ic95_sup": ols_sup, "p_ols_newey_west": p_ols,
            "ols_pct_por_decada": 100 * ols / media,
            "sen_por_decada": sen, "sen_ic95_inf": sen_inf, "sen_ic95_sup": sen_sup, "p_mk_permutacion": p_mk,
            "p_mk_hamed_rao": p_hr, "factor_hamed_rao": factor_hr,
            "autocorr_lag1_anomalias": float(np.corrcoef(anom.to_numpy()[1:], anom.to_numpy()[:-1])[0, 1]),
            "pettitt_ultimo_anio_tramo1": int(anual.index[k]), "p_pettitt": p_pettitt,
            "ols_sin_primeros_anios": sin_inicio[0], "p_sin_primeros_anios": sin_inicio[3],
            "ols_sin_ultimos_anios": sin_final[0], "p_sin_ultimos_anios": sin_final[3],
        })
    tabla_t = pd.DataFrame(filas)
    for p, q in (("p_ols_newey_west", "q_ols"), ("p_mk_permutacion", "q_mk"), ("p_mk_hamed_rao", "q_hamed_rao")):
        tabla_t[q] = benjamini_hochberg(tabla_t[p])
    tabla_t["significativa_ols_fdr"] = tabla_t["q_ols"] < Q_FDR
    tabla_t["significativa_mk_fdr"] = tabla_t["q_mk"] < Q_FDR
    return tabla_t


# ---------------------------------------------------------------- atribución
def atribucion(tabla_t):
    """Contribución de cada forzante = sensibilidad (% de ETo por unidad) × tendencia del forzante (por década)."""
    sens = pd.read_csv(ENTRADA_SENSIBILIDAD)
    sens = sens[(sens["metodo"] == NOMBRES["eto"]) & (sens["mes"] == "anual")].set_index("escenario")["cambio_pct"]
    # % de cambio de la ETo por unidad del forzante (linealización con las perturbaciones del script 28)
    por_unidad = {"t": (sens["t+1_ea"] / 1.0, "% por °C (ea constante)"),
                  "ea": (sens["ea+10"] / 10.0, "% por % de ea"),
                  "u2": (sens["u2+10"] / 10.0, "% por % de u2"),
                  "rs": (sens["rs-10"] / -10.0, "% por % de Rs")}
    tt = tabla_t.set_index("clave")
    eto_media_anual = tt.loc["eto", "media"] * 12
    filas = []
    for v, (s, unidad_s) in por_unidad.items():
        # la T entra en °C por década; los demás en % por década (relativos a su media)
        tendencia = tt.loc[v, "ols_por_decada"] if v == "t" else tt.loc[v, "ols_pct_por_decada"]
        contrib_pct = s * tendencia
        filas.append({"forzante": NOMBRES[v], "sensibilidad": s, "unidad_sensibilidad": unidad_s,
                      "tendencia_forzante_por_decada": tendencia,
                      "unidad_tendencia": "°C/década" if v == "t" else "%/década",
                      "p_tendencia_forzante": tt.loc[v, "p_ols_newey_west"],
                      "contribucion_pct_por_decada": contrib_pct,
                      "contribucion_mm_anio_por_decada": contrib_pct / 100 * eto_media_anual})
    atr = pd.DataFrame(filas)
    suma_pct = atr["contribucion_pct_por_decada"].sum()
    directa_pct = tt.loc["eto", "ols_pct_por_decada"]
    resumen = [
        {"forzante": "Suma de contribuciones", "contribucion_pct_por_decada": suma_pct},
        {"forzante": "Tendencia directa de la ETo", "contribucion_pct_por_decada": directa_pct,
         "p_tendencia_forzante": tt.loc["eto", "p_ols_newey_west"]},
        {"forzante": "Residuo (directa − suma)", "contribucion_pct_por_decada": directa_pct - suma_pct},
    ]
    for fila in resumen:
        fila["contribucion_mm_anio_por_decada"] = fila["contribucion_pct_por_decada"] / 100 * eto_media_anual
    atr = pd.concat([atr, pd.DataFrame(resumen)], ignore_index=True)
    # comprobación: contribuciones + residuo = tendencia directa
    assert np.isclose(atr["contribucion_pct_por_decada"].iloc[:4].sum() + atr["contribucion_pct_por_decada"].iloc[6],
                      directa_pct)
    return atr


# ---------------------------------------------------------------- figura
def figura(tabla, tabla_t, atr):
    fig, ejes = plt.subplots(1, 2, figsize=(12, 4.5))
    # totales anuales con eje desde 0 y solo la recta de Sen (Juan, 24 nov: sin OLS ni anomalías)
    anual = tabla[["eto", "thornthwaite"]].groupby(tabla.index.year).sum()
    tt = tabla_t.set_index("clave")
    colores = {"eto": "#1f77b4", "thornthwaite": "#d62728"}
    x = np.array([1998, 2022])
    for v in ("eto", "thornthwaite"):
        ejes[0].plot(anual.index, anual[v], "o-", color=colores[v], ms=3, label=NOMBRES[v])
        pendiente_sen = tt.loc[v, "sen_por_decada"] * 12 / 10            # mm/año por año
        ejes[0].plot(x, anual[v].median() + pendiente_sen * (x - np.median(anual.index)), "--", color=colores[v],
                     label=f"Sen: {tt.loc[v, 'sen_por_decada'] * 12:+.0f} mm/año por década "
                           f"(p = {tt.loc[v, 'p_mk_permutacion']:.3f})")
    ejes[0].set_ylim(0, None)
    ejes[0].set_xlabel("Año")
    ejes[0].set_ylabel("mm/año")
    ejes[0].set_title("Demanda anual de la cuenca, 1998–2022")
    ejes[0].legend(fontsize=8, loc="lower left")
    barras = atr.iloc[[0, 1, 2, 3, 6, 5]]
    etiquetas = ["T", "ea", "u2", "Rs", "Residuo", "Directa"]
    ejes[1].bar(etiquetas, barras["contribucion_mm_anio_por_decada"],
                color=["#ff7f0e", "#2ca02c", "#9467bd", "#8c564b", "#7f7f7f", "#1f77b4"])
    ejes[1].axhline(0, color="k", lw=0.8)
    ejes[1].set_ylabel("mm/año por década")
    ejes[1].set_title("Atribución de la tendencia de la ETo Penman–Monteith (FAO-56)")
    fig.tight_layout()
    fig.savefig(SALIDA_FIGURA, dpi=150)


def main():
    tabla = series_cuenca()
    tabla_t = tendencias(tabla)
    atr = atribucion(tabla_t)
    tabla_t.round(5).to_csv(SALIDA_TENDENCIAS, index=False)
    atr.round(5).to_csv(SALIDA_ATRIBUCION, index=False)
    figura(tabla, tabla_t, atr)
    pd.set_option("display.width", 200)
    print(tabla_t[["variable", "media", "ols_por_decada", "ols_pct_por_decada", "p_ols_newey_west", "q_ols",
                   "sen_por_decada", "p_mk_permutacion", "q_mk", "p_mk_hamed_rao", "pettitt_ultimo_anio_tramo1",
                   "p_pettitt", "ols_sin_primeros_anios", "ols_sin_ultimos_anios"]].round(4).to_string())
    print(atr[["forzante", "sensibilidad", "tendencia_forzante_por_decada", "contribucion_pct_por_decada",
               "contribucion_mm_anio_por_decada"]].round(3).to_string())
    print(f"Listo: {SALIDA_TENDENCIAS}, {SALIDA_ATRIBUCION}, {SALIDA_FIGURA}")


if __name__ == "__main__":
    main()
