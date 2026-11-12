"""¿Actúa el ENSO sobre el caudal de San Gil solo a través de la lluvia? (crítica 4 de la revisión adversarial)

La anomalía de Q se correlaciona más con el ONI que la de la lluvia (PL y PI). Si el ENSO actuara solo a través de la
lluvia, se esperaría lo contrario o algo parecido. Dos pruebas, con PL y PI en paralelo (regla 11), 1998-2022:

  1. Lluvia acumulada (y la ETP del mes, que con El Niño sube). La lluvia de un mes es ruidosa, y la cuenca guarda agua de un mes a otro: el caudal responde
     a la lluvia de varios meses. Se correlaciona con el ONI la anomalía de la lluvia promediada en los últimos
     1, 3 y 6 meses. Si la lluvia de varios meses se acerca a Q, la diferencia la explica el filtrado de la cuenca.
  2. Correlación parcial de Q con el ONI, quitando por regresión lo que explican: (a) los regresores de M4, ln P del
     mes y del anterior; (b) los de M5, ln P del mes, del anterior y ln ETP; (c) los de M5 más ln P de 2 y 3 meses
     antes. Si la parcial se acerca a 0, la lluvia (y la ETP) bastan para explicar la relación de Q con el ENSO.

Las anomalías son cada mes menos la media de su mes del calendario en 1998-2022 (en ln, para la parcial, la escala
de M4 y M5). El ONI es el de 1 mes antes (IND_REZAGO_CONTROL de 18_calculos_informe.py, su rezago más fuerte con Q).
Las tres parciales usan la misma muestra: los meses con Q y con la lluvia de los 3 meses anteriores.
Significancia: n efectivo de Bretherton et al. (1999) con la autocorrelación de un mes de las dos series (en la
parcial, de los dos residuos), menos un grado de libertad por cada variable controlada; el mismo criterio de
«Q frente al ONI y al TNA».

Lee  out/variables_mensuales.csv (PL depurada, PI, Q, ETP) y out/oni_mensual_1981_2022.csv.
Escribe out/enso_lluvia_acumulada.csv y out/enso_parcial_q_oni.csv.
"""
import numpy as np
import pandas as pd
from scipy import stats

PERIODOS = pd.period_range("1998-01", "2022-12", freq="M")
FUENTES = ("PL", "PI")
REZAGO_ONI = 1                 # meses: el ONI de 1 mes antes, su rezago más fuerte con Q
VENTANAS = (1, 3, 6)           # meses sobre los que se promedia la lluvia
CONTROLES = {                  # nombre -> (rezagos de ln P, ¿con ln ETP?)
    "M4": ((0, 1), False),
    "M5": ((0, 1), True),
    "M5 y lluvia de 2 y 3 meses antes": ((0, 1, 2, 3), True),
}

variables = pd.read_csv("out/variables_mensuales.csv", index_col=0)
variables.index = pd.PeriodIndex(variables.index, freq="M")
variables = variables.reindex(PERIODOS)
_oni = pd.read_csv("out/oni_mensual_1981_2022.csv")
oni = pd.Series(_oni["oni"].to_numpy(dtype=float), index=pd.PeriodIndex(_oni["periodo"], freq="M"))
oni_antes = oni.shift(REZAGO_ONI).reindex(PERIODOS)
assert oni_antes.notna().all()


def anomalia(serie):
    """Cada mes menos la media de su mes del calendario."""
    return serie - serie.groupby(serie.index.month).transform("mean")


def n_efectivo(x, y):
    """Bretherton et al. (1999): n (1 - a·b) / (1 + a·b), con a y b la autocorrelación de un mes de cada serie."""
    a, b = x.corr(x.shift(1)), y.corr(y.shift(1))
    return x.notna().sum() * (1 - a * b) / (1 + a * b)


def p_correlacion(r, gl):
    """p de dos colas de la prueba t de una correlación con gl grados de libertad."""
    return float(2 * stats.t.sf(abs(r) * np.sqrt(gl / (1 - r ** 2)), gl))


# ------------------------------------------------------------------ 1. lluvia acumulada contra el ONI
filas = []
q_anom = anomalia(variables["Q"])
for variable in ("Q", "ETP") + FUENTES:              # Q y la ETP, solo del mes; la lluvia, promediada
    for ventana in VENTANAS:
        if variable in ("Q", "ETP") and ventana > 1:
            continue
        serie = variables[variable].rolling(ventana, min_periods=ventana).mean()
        x = anomalia(serie)
        ok = x.notna() & q_anom.notna()            # los mismos meses en todas: los que tienen Q
        r = float(x[ok].corr(oni_antes[ok]))
        n_ef = n_efectivo(x.where(ok), oni_antes.where(ok))
        filas.append({"variable": variable, "meses_promediados": ventana, "r_con_oni": r, "n": int(ok.sum()),
                      "n_efectivo": n_ef, "p": p_correlacion(r, n_ef - 2)})
acumulada = pd.DataFrame(filas)
acumulada.to_csv("out/enso_lluvia_acumulada.csv", index=False, float_format="%.4f")

# ------------------------------------------------------------------ 2. parcial de Q con el ONI
ln = {v: anomalia(np.log(variables[v])) for v in ("Q", "ETP") + FUENTES}
max_rezago = max(max(r) for r, _ in CONTROLES.values())
filas = []
for fuente in FUENTES:
    columnas = {f"p{k}": ln[fuente].shift(k) for k in range(max_rezago + 1)} | {"etp": ln["ETP"]}
    datos = pd.DataFrame({"q": ln["Q"], "oni": oni_antes, **columnas}).dropna()    # misma muestra para las tres
    for nombre, (rezagos, con_etp) in CONTROLES.items():
        nombres = [f"p{k}" for k in rezagos] + (["etp"] if con_etp else [])
        X = np.column_stack([np.ones(len(datos))] + [datos[c] for c in nombres])
        quitar = lambda y: pd.Series(y - X @ np.linalg.lstsq(X, y, rcond=None)[0], index=datos.index)
        eq, eo = quitar(datos.q.to_numpy()), quitar(datos.oni.to_numpy())
        r = float(np.corrcoef(eq, eo)[0, 1])
        n_ef = n_efectivo(eq.reindex(PERIODOS), eo.reindex(PERIODOS))
        filas.append({"fuente": fuente, "controles": nombre, "r_parcial": r, "n": len(datos),
                      "n_efectivo": n_ef, "p": p_correlacion(r, n_ef - 2 - len(nombres))})
parcial = pd.DataFrame(filas)
parcial.to_csv("out/enso_parcial_q_oni.csv", index=False, float_format="%.4f")

print(acumulada.round(3).to_string(index=False))
print(parcial.round(3).to_string(index=False))
