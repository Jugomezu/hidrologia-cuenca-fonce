"""Correlación entre todas las variables mensuales de la cuenca, por Pearson y por Spearman.

Se cruzan las seis variables mensuales del proyecto sobre los meses en que todas tienen dato, y se
calculan dos coeficientes por cada par:

  - **Pearson**, la correlación de siempre: mide cuánto se parece la nube de puntos a una recta.
  - **Spearman**, sobre los rangos en vez de sobre los valores: detecta relaciones que suben o bajan
    de forma consistente aunque no sean rectas, y no se deja arrastrar por unos pocos meses extremos.

Además de las series tal cual, todo se repite sobre las **anomalías**, es decir restándole a cada
variable su propio ciclo anual medio. Esto importa mucho aquí: en una cuenca tropical casi todas las
variables suben y bajan con las mismas dos temporadas de lluvia, así que la correlación de las series
crudas mide sobre todo "comparten el calendario". La de las anomalías dice si además se mueven juntas
cuando un mes se sale de lo normal, que es la pregunta interesante.

Salidas:
  out/correlaciones_pearson.csv             matriz de Pearson, series crudas
  out/correlaciones_spearman.csv            matriz de Spearman, series crudas
  out/correlaciones_pearson_anomalias.csv   matriz de Pearson sobre anomalías
  out/correlaciones_spearman_anomalias.csv  matriz de Spearman sobre anomalías
  out/correlaciones_spearman_rezago1.csv    Spearman con un mes de rezago (fila en t+1, columna en t)
  out/variables_mensuales.csv               la tabla de variables, para que la figura no la rehaga

La precipitación de CHIRPS que trae CAMELS-COL se retiró del proyecto el 2026-09-26: con IMERG (PI) y la
red de pluviómetros (PL) hay fuentes de sobra, y CHIRPS no era independiente de ninguna de las dos.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
ANIOS = range(1998, 2023)
MAX_DIAS_FALTANTES = 4                      # la regla del proyecto

PERIODOS = pd.period_range(f"{min(ANIOS)}-01", f"{max(ANIOS)}-12", freq="M")
DIAS = pd.date_range(f"{min(ANIOS)}-01-01", f"{max(ANIOS)}-12-31", freq="D")


def a_mensual(serie_diaria, agregacion):
    """Serie diaria -> mensual; el mes queda vacío si le faltan más de MAX_DIAS_FALTANTES días.

    `agregacion` es "sum" para acumulados (lluvia, caudal en mm, ETP) o "mean" para promedios.
    """
    g = serie_diaria.resample("MS")
    faltantes = g.apply(lambda x: x.index.days_in_month[0] - x.notna().sum())
    # Acumulado del mes ("sum"): el promedio de los días con dato por los días del mes. En un mes completo
    # es la suma exacta; en uno incompleto (1 a MAX_DIAS_FALTANTES días faltantes) evita presentar una suma
    # parcial como si fuera el acumulado del mes. Supone que los días faltantes se parecen al resto del
    # mes. Para el caudal es la definición usual: volumen del mes = caudal medio x duración del mes.
    promedio = g.mean()
    valores = {"sum": promedio * promedio.index.days_in_month, "mean": promedio}[agregacion]
    valores = valores.where(faltantes <= MAX_DIAS_FALTANTES)
    valores.index = valores.index.to_period("M")
    return valores.reindex(PERIODOS)


# ------------------------------------------------------------------ las seis variables
cam = pd.read_csv(RAIZ / "data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_24027010.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam["fecha"], format="%d/%m/%Y")
cam = cam.set_index("fecha").sort_index().reindex(DIAS)

# área del polígono (geodésica), medida por 02_shp_cuencas_estaciones.py; es la única fuente del área
area_km2 = float(pd.read_csv(OUT / "shp_fonce/areas_cuencas.csv").set_index("gauge_id").loc[ID_PRINCIPAL, "area_km2"])
era = pd.read_csv(OUT / "era5land_temperatura_diaria_fonce.csv",
                  parse_dates=["fecha"]).set_index("fecha").reindex(DIAS)
# ETP: la de Hargreaves con ERA5-Land que calcula el proyecto (06b_etp_hargreaves.py), no la que publica
# CAMELS-COL, que sale 2.75 veces más alta que su propia fórmula (decidido el 2026-09-28)
etp = pd.read_csv(OUT / "etp_hargreaves_fonce.csv", parse_dates=["fecha"]).set_index("fecha").reindex(DIAS)
imerg = pd.read_csv(OUT / "imerg_mensual_fonce.csv")
imerg["periodo"] = pd.PeriodIndex(imerg["periodo"], freq="M")
catalogo = pd.read_csv(OUT / "pluviometros_fonce_catalogo.csv").set_index("codigo")
DENTRO = catalogo.index[catalogo["dentro_cuenca"]].tolist()
pluvio = pd.read_csv(OUT / "pluviometros_fonce_mensual_depurado.csv", parse_dates=["fecha"])
pluvio["periodo"] = pluvio["fecha"].dt.to_period("M")

variables = pd.DataFrame({
    # PI, PL y Q son las tres siglas del proyecto (regla 12 de CLAUDE.md)
    "PI": imerg[imerg.id_estacion == ID_PRINCIPAL].set_index("periodo")["p_imerg_mm"],
    "PL": pluvio.pivot(index="periodo", columns="codigo",
                       values="precipitacion_mm")[DENTRO].mean(axis=1),
    "Q": a_mensual(cam["caudal"] * 86400 / (area_km2 * 1e6) * 1000, "sum"),   # m3/s -> mm/mes
    "ETP": a_mensual(etp["etp_era5land"], "sum"),
    "T MSWX": a_mensual((cam["t_min"] + cam["t_max"]) / 2, "mean"),
    "T ERA5": a_mensual(era["t_media"], "mean"),
}).reindex(PERIODOS)

UNIDADES = {"PI": "mm/mes", "PL": "mm/mes", "Q": "mm/mes",
            "ETP": "mm/mes", "T MSWX": "°C", "T ERA5": "°C"}

# Solo los meses en que TODAS tienen dato: si cada par usara su propia muestra, los coeficientes de la
# matriz no serían comparables entre sí.
completos = variables.dropna()
anomalias = completos - completos.groupby(completos.index.month).transform("mean")


def matriz_spearman(df):
    rho, _ = spearmanr(df.values)
    return pd.DataFrame(rho, index=df.columns, columns=df.columns)


matrices = {
    "pearson": completos.corr(method="pearson"),
    "spearman": matriz_spearman(completos),
    "pearson_anomalias": anomalias.corr(method="pearson"),
    "spearman_anomalias": matriz_spearman(anomalias),
}
# --- con un mes de rezago: cada variable en el mes t contra cada variable en el mes t+1 ---
# La matriz deja de ser simétrica: la casilla (fila, columna) es la correlación entre la COLUMNA en el mes
# t y la FILA en el mes siguiente; la diagonal es la persistencia de cada variable de un mes al otro. Se
# usan solo los meses t en que las seis variables tienen dato en t y también en t+1.
siguiente = variables.shift(-1)
consecutivos = variables.notna().all(axis=1) & siguiente.notna().all(axis=1)
antes, despues = variables[consecutivos], siguiente[consecutivos]
matrices["spearman_rezago1"] = pd.DataFrame(
    [[spearmanr(antes[col], despues[fila])[0] for col in variables.columns] for fila in variables.columns],
    index=variables.columns, columns=variables.columns)

for nombre, m in matrices.items():
    m.round(4).to_csv(OUT / f"correlaciones_{nombre}.csv")
completos.to_csv(OUT / "variables_mensuales.csv")

# ------------------------------------------------------------------ resumen por consola
pd.set_option("display.width", 140)
print(f"{len(completos)} meses con dato en las seis variables, de {len(PERIODOS)} del período")
print(f"{int(consecutivos.sum())} pares de meses consecutivos con las seis variables (para el rezago)\n")
for nombre in ["pearson", "spearman", "pearson_anomalias", "spearman_anomalias", "spearman_rezago1"]:
    print(f"--- {nombre.replace('_', ' ')} ---")
    print(matrices[nombre].round(2).to_string())
    print()

# los pares ordenados por cuánto cae la correlación al quitar el ciclo anual: ahí está lo interesante
pares = []
for i, a in enumerate(completos.columns):
    for b in completos.columns[i + 1:]:
        pares.append({"par": f"{a} – {b}",
                      "pearson": matrices["pearson"].loc[a, b],
                      "spearman": matrices["spearman"].loc[a, b],
                      "pearson_anom": matrices["pearson_anomalias"].loc[a, b],
                      "caida": matrices["pearson"].loc[a, b] - matrices["pearson_anomalias"].loc[a, b]})
pares = pd.DataFrame(pares).sort_values("pearson", key=abs, ascending=False)
print(f"--- los {len(pares)} pares, por correlación de Pearson ---")
print(pares.round(3).to_string(index=False))


# ------------------------------------------------------------------ ¿responde Q a la lluvia con rezago?
# Correlación cruzada entre la lluvia (PL y PI) en el mes t-k y el caudal en el mes t, para k de -3 a +3.
# Con k > 0 la lluvia va antes que el caudal; con k < 0, después, y esos rezagos sirven de control: si
# la lluvia causa el caudal, no deberían dar nada. Aquí cada par usa todos los meses en que las dos
# series tienen dato (no la muestra común de las seis variables), porque solo intervienen dos.
# Se hace sobre las series tal cual y sobre las anomalías (cada serie menos su ciclo anual medio): en
# las series tal cual, el desfase de los ciclos anuales basta para dar una correlación con rezago aunque
# la cuenca no tuviera memoria alguna; en las anomalías, no.
REZAGOS = range(-3, 4)
serie_anom = variables - variables.groupby(variables.index.month).transform("mean")
filas_cruzada = []
for lluvia in ("PL", "PI"):
    for tipo, tabla in (("tal cual", variables), ("anomalías", serie_anom)):
        for k in REZAGOS:
            par = pd.DataFrame({"p": tabla[lluvia].shift(k), "q": tabla["Q"]}).dropna()
            filas_cruzada.append({"lluvia": lluvia, "series": tipo, "rezago_meses": k,
                                  "rho": spearmanr(par.p, par.q)[0], "n": len(par)})
cruzada = pd.DataFrame(filas_cruzada)
cruzada.to_csv(OUT / "correlacion_cruzada_lluvia_caudal.csv", index=False)

# ¿Aporta algo la lluvia del mes anterior cuando ya se conoce la del mes? Regresión lineal de las
# anomalías de Q contra las de la lluvia del mes, con y sin la del mes anterior, y la correlación
# parcial de la lluvia del mes anterior con Q descontando la del mes.
def r2_de(y, *xs):
    a = np.column_stack([np.ones(len(y)), *xs])
    ajuste = a @ np.linalg.lstsq(a, y, rcond=None)[0]
    return 1 - ((y - ajuste) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def residuo(y, x):
    a = np.column_stack([np.ones(len(x)), x])
    return y - a @ np.linalg.lstsq(a, y, rcond=None)[0]


filas_memoria = []
for lluvia in ("PL", "PI"):
    d = pd.DataFrame({"p0": serie_anom[lluvia], "p1": serie_anom[lluvia].shift(1),
                      "q": serie_anom["Q"]}).dropna()
    filas_memoria.append({
        "lluvia": lluvia, "n": len(d),
        "r2_solo_mes": r2_de(d.q.values, d.p0.values),
        "r2_mes_y_anterior": r2_de(d.q.values, d.p0.values, d.p1.values),
        "parcial_mes_anterior": float(np.corrcoef(residuo(d.p1.values, d.p0.values),
                                                  residuo(d.q.values, d.p0.values))[0, 1]),
        # cuánto se parece la anomalía de lluvia de un mes a la del siguiente: si persiste, el caudal
        # de un mes también "anticipa" la lluvia del siguiente sin que eso signifique nada causal
        "persistencia_lluvia": spearmanr(d.p0, d.p1)[0],
    })
memoria = pd.DataFrame(filas_memoria)
memoria.to_csv(OUT / "memoria_lluvia_caudal.csv", index=False)

print("\n--- correlación cruzada: lluvia en t-k contra Q en t (Spearman) ---")
print(cruzada.pivot_table(index="rezago_meses", columns=["lluvia", "series"], values="rho").round(2).to_string())
print("\n--- ¿aporta la lluvia del mes anterior? (anomalías) ---")
print(memoria.round(3).to_string(index=False))


# ------------------------------------------------------------------ ¿cuánto condiciona el ciclo de la lluvia al de Q?
# Sobre el año típico (las 12 medias mensuales de cada serie, con todos sus meses válidos): se ajusta el
# ciclo de Q como combinación lineal de la lluvia del mismo mes y de la del mes anterior (el mes anterior
# a enero es diciembre, porque el ciclo es circular), y se compara con el ajuste que usa solo la lluvia
# del mes. Son 12 puntos: el R² describe qué tan bien se reproduce la forma del ciclo, no es una prueba
# estadística fuerte.
MESES = range(1, 13)
ciclo_anual = variables[["PL", "PI", "Q"]].groupby(variables.index.month).mean().reindex(MESES)
filas_ciclo = []
for lluvia in ("PL", "PI"):
    p_mes = ciclo_anual[lluvia].values
    p_ant = np.roll(p_mes, 1)                          # lluvia del mes anterior
    q = ciclo_anual["Q"].values
    ajustes_ciclo = {}
    for nombre, columnas in (("mes", [p_mes]), ("mes_y_anterior", [p_mes, p_ant])):
        a = np.column_stack([np.ones(12), *columnas])
        coef = np.linalg.lstsq(a, q, rcond=None)[0]
        ajustes_ciclo[nombre] = a @ coef
        filas_ciclo.append({"lluvia": lluvia, "modelo": nombre, "r2": r2_de(q, *columnas),
                            "intercepto": coef[0], "coef_mes": coef[1],
                            "coef_mes_anterior": coef[2] if len(coef) > 2 else np.nan})
    ciclo_anual[f"Q_ajuste_{lluvia}_mes"] = ajustes_ciclo["mes"]
    ciclo_anual[f"Q_ajuste_{lluvia}_mes_y_anterior"] = ajustes_ciclo["mes_y_anterior"]
ciclo_anual.rename_axis("mes").to_csv(OUT / "ciclo_lluvia_caudal.csv")
ajuste_ciclo = pd.DataFrame(filas_ciclo)
ajuste_ciclo.to_csv(OUT / "ajuste_ciclo_lluvia_caudal.csv", index=False)

print("\n--- el año típico de la lluvia y del caudal (mm/mes) ---")
print(ciclo_anual[["PL", "PI", "Q"]].round(0).T.to_string())
print("\n--- el ciclo de Q reconstruido con la lluvia del mes, y con la del mes y la del anterior ---")
print(ajuste_ciclo.round(3).to_string(index=False))
