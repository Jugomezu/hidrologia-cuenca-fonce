"""Anomalías en las series (sección 4.3 del notebook): saltos bruscos, secuencias constantes, extremos
aislados y cambios de cobertura. Nada se elimina aquí: el script solo detecta y mide; las decisiones se
registran aparte.

1. SALTOS BRUSCOS (homogeneidad). Un cambio de estación, de instrumento o de producto suele dejar un
   escalón: desde cierta fecha la serie mide sistemáticamente más o menos que sus vecinas. Se busca así:
   - cada pluviómetro contra el promedio de los otros pluviómetros de la cuenca, el mismo mes
     (curva de doble masa y prueba de Pettitt sobre el logaritmo de la razón estación / resto);
   - PI contra PL, y Q contra PL, de la misma forma.
   La prueba de Pettitt (1979) es no paramétrica: busca el punto de la serie que mejor la parte en dos
   tramos con niveles distintos, y da una probabilidad aproximada de que eso ocurra por azar.
1b. SEGUNDO CORTE. Pettitt solo encuentra un corte por serie. A cada pluviómetro marcado en las rondas
   se le repite la prueba en el tramo de su serie depurada posterior a su primer corte, contra el promedio
   de los demás pluviómetros sin ninguno de los marcados. Si alguno tiene un segundo salto significativo,
   se repite también la prueba de PI contra una PL calculada sin ese pluviómetro, para ver si el salto de
   PI viene de IMERG o de ese pluviómetro. Nada de esto cambia la serie depurada.
2. SECUENCIAS CONSTANTES: días seguidos con exactamente el mismo valor (Q diario, temperatura diaria) y
   meses seguidos con el mismo total en un pluviómetro. Un instrumento trabado o un dato copiado dejan
   ese rastro.
3. EXTREMOS AISLADOS en el Q diario: un día que multiplica por FACTOR_PICO a sus dos días vecinos y vuelve
   enseguida. Puede ser una creciente corta real o un error de digitación; se lista, no se borra.
4. COBERTURA DE PL: los meses en que faltan pluviómetros, PL es el promedio de los que hay. Cuánto se
   aleja eso del promedio de los 7 se estima en los meses en que están los 7: para el mismo grupo de
   estaciones presentes, la mediana de (promedio del grupo / promedio de los 7).
5. MESES CON 0 mm en un pluviómetro, frente a lo que midieron los demás y PI ese mes.

Salidas (out/):
  anomalias_homogeneidad.csv   serie, prueba, n, fecha del cambio, p, razón antes y después
  anomalias_doble_masa.csv     acumulados para las curvas de doble masa
  anomalias_segundo_corte.csv  segundo corte de los pluviómetros marcados, y PI contra PL sin los que lo tienen
  anomalias_rachas.csv         secuencias constantes encontradas
  anomalias_picos_q.csv        picos aislados del Q diario
  anomalias_cobertura_pl.csv   sesgo estimado de PL en cada mes con pluviómetros faltantes
  anomalias_ceros_pl.csv       los meses con 0 mm, con sus vecinos y PI
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
DIAS = pd.date_range("1998-01-01", "2022-12-31", freq="D")
MESES = pd.period_range("1998-01", "2022-12", freq="M")

ALFA = 0.05              # nivel de significancia de la prueba de Pettitt
RACHA_MINIMA_DIAS = 5    # días seguidos con el mismo valor exacto para contar como secuencia constante
RACHA_MINIMA_MESES = 2   # meses seguidos con el mismo total (distinto de 0) en un pluviómetro
FACTOR_PICO = 3.0        # un día es un pico aislado si vale al menos 3 veces cada uno de sus dos vecinos
UMBRAL_CERO_MM = 20.0    # un mes en 0 mm es difícil de creer si TODOS los demás pluviómetros pasan de esto


def pettitt(x):
    """Prueba de Pettitt (1979). Devuelve el índice del último elemento del primer tramo, el estadístico K
    y la probabilidad aproximada p = 2·exp(−6K² / (n³ + n²))."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    signo = np.sign(x[:, None] - x[None, :])
    u = np.array([signo[: t + 1, t + 1:].sum() for t in range(n - 1)])
    k = int(np.argmax(np.abs(u)))
    K = float(abs(u[k]))
    return k, K, min(1.0, 2 * np.exp(-6 * K ** 2 / (n ** 3 + n ** 2)))


# ====================================================================== datos
catalogo = pd.read_csv(OUT / "pluviometros_fonce_catalogo.csv").set_index("codigo")
DENTRO = catalogo.index[catalogo.dentro_cuenca].tolist()
NOMBRE = {c: catalogo.loc[c, "nombre"].split(" [")[0].title().replace(" De ", " de ") for c in DENTRO}


def matriz_pluviometros(archivo):
    pm = pd.read_csv(OUT / archivo, parse_dates=["fecha"])
    return (pm.assign(periodo=pm.fecha.dt.to_period("M"))
            .pivot(index="periodo", columns="codigo", values="precipitacion_mm")[DENTRO].reindex(MESES))


# La detección por pluviómetro (saltos, rachas, ceros) se hace sobre la serie como estaba ANTES de las
# decisiones de esta sección: la cruda, sin las exclusiones cuya evidencia está en otra parte (Encino
# 2016-2018, sección 1.7), porque un tramo ya descartado contaminaría la referencia de sus vecinos. Así
# quedan a la vista los problemas que llevaron a las exclusiones con evidencia "4.3". La cobertura y las
# pruebas de PI y Q contra PL usan la serie depurada, que es la PL del proyecto.
plu_crudo = matriz_pluviometros("pluviometros_fonce_mensual_1998_2022.csv")
for e in pd.read_csv(OUT / "pluviometros_exclusiones.csv", dtype={"evidencia": str}).query("evidencia != '4.3'").itertuples():
    plu_crudo.loc[pd.Period(e.desde, "M"):pd.Period(e.hasta, "M"), e.codigo] = np.nan
plu = matriz_pluviometros("pluviometros_fonce_mensual_depurado.csv")
pl = plu.mean(axis=1)                                      # PL: el promedio de los que tienen dato
imerg = pd.read_csv(OUT / "imerg_mensual_fonce.csv")
imerg["periodo"] = pd.PeriodIndex(imerg.periodo, freq="M")
pi = imerg[imerg.id_estacion == ID_PRINCIPAL].set_index("periodo").p_imerg_mm.reindex(MESES)
variables = pd.read_csv(OUT / "variables_mensuales.csv", index_col=0)   # Q en mm, 262 meses (16_...)
variables.index = pd.PeriodIndex(variables.index, freq="M")
cam = pd.read_csv(RAIZ / f"data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_{ID_PRINCIPAL}.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam.fecha, format="%d/%m/%Y")
q_dia = cam.set_index("fecha").caudal.reindex(DIAS)
era = pd.read_csv(OUT / "era5land_temperatura_diaria_fonce.csv", parse_dates=["fecha"]).set_index("fecha").reindex(DIAS)

# ====================================================================== 1. homogeneidad
homog, doble_masa = [], []


def medir_corte(serie, referencia):
    """Pettitt sobre log(serie / referencia) en los meses en que las dos tienen dato y son mayores que 0.
    La razón de cada tramo es la exponencial de la mediana del logaritmo. Devuelve el resultado y los pares
    de meses usados (para la doble masa)."""
    par = pd.DataFrame({"s": serie, "r": referencia}).dropna()
    par = par[(par.s > 0) & (par.r > 0)]
    log_razon = np.log(par.s / par.r)
    k, K, p = pettitt(log_razon.values)
    antes, despues = np.exp(log_razon.iloc[: k + 1].median()), np.exp(log_razon.iloc[k + 1:].median())
    resultado = {"meses": len(par),
                 "ultimo_mes_antes": str(par.index[k]), "primer_mes_despues": str(par.index[k + 1]),
                 "p": p, "significativo": p < ALFA,
                 "razon_antes": antes, "razon_despues": despues, "cambio_pct": (despues / antes - 1) * 100}
    return resultado, par


def probar(nombre, serie, referencia, descripcion_ref):
    """Mide el corte (medir_corte) y lo guarda en la tabla de homogeneidad y en la de doble masa."""
    resultado, par = medir_corte(serie, referencia)
    homog.append({"serie": nombre, "referencia": descripcion_ref, **resultado})
    acum = par.cumsum()
    doble_masa.append(pd.DataFrame({"serie": nombre, "referencia": descripcion_ref, "periodo": acum.index.astype(str),
                                    "acumulado_serie": acum.s.values, "acumulado_referencia": acum.r.values}))


# Una estación con un salto contamina la referencia de las demás (el promedio del resto la incluye), así que
# se prueba por rondas: en cada ronda, cada pluviómetro contra el promedio de los otros que aún no se han
# marcado; el de menor p, si es significativo, se marca y sale de las referencias; se repite hasta que
# ninguno lo sea. De cada pluviómetro queda el resultado de la última ronda en que se probó.
marcados, ronda = [], 0
while True:
    ronda += 1
    ultimos = {}
    for c in [c for c in DENTRO if c not in marcados]:
        resto = plu_crudo.drop(columns=[c] + marcados).mean(axis=1)
        sin = f" (sin {', '.join(NOMBRE[m] for m in marcados)})" if marcados else ""
        homog_antes = len(homog)
        probar(f"PL · {NOMBRE[c]}", plu_crudo[c], resto, "promedio de los demás pluviómetros" + sin)
        ultimos[c] = homog[homog_antes]
        homog[homog_antes]["ronda"] = ronda
    peor = min(ultimos, key=lambda c: ultimos[c]["p"])
    if ultimos[peor]["p"] >= ALFA:
        break
    marcados.append(peor)
# de cada pluviómetro, la última ronda en que se probó (y su curva de doble masa de esa ronda)
tabla = pd.DataFrame(homog)
tabla = tabla.loc[tabla.groupby("serie").ronda.idxmax()]
doble_masa = [d for d, fila in zip(doble_masa, homog) if fila["ronda"] == tabla.set_index("serie").loc[fila["serie"], "ronda"]]
homog = tabla.sort_values("serie").to_dict("records")

# PI y Q contra la PL del proyecto (depurada)
probar("PI (IMERG)", pi, pl, "PL")
probar("Q", variables.Q, variables.PL, "PL")
pd.DataFrame(homog).drop(columns="ronda", errors="ignore").to_csv(OUT / "anomalias_homogeneidad.csv", index=False)
pd.concat(doble_masa).to_csv(OUT / "anomalias_doble_masa.csv", index=False)

# ---------------------------------------------------------------------- 1b. segundo corte
# Pettitt encuentra UN solo corte por serie. Un pluviómetro marcado en las rondas puede tener otro salto
# dentro del tramo que queda después del primero. Para verlo, se repite la prueba solo sobre ese tramo, en
# la serie depurada (la que entra a PL), contra el promedio de los demás pluviómetros sin ninguno de los
# marcados, para que el salto de uno no contamine la referencia del otro.
primer_corte = pd.DataFrame(homog).set_index("serie")
sin_marcados = f"sin {', '.join(NOMBRE[m] for m in marcados)}"
segundo = []
for c in marcados:
    desde = pd.Period(primer_corte.loc[f"PL · {NOMBRE[c]}", "primer_mes_despues"], "M")
    resto = plu.drop(columns=marcados).mean(axis=1)
    resultado, _ = medir_corte(plu[c].loc[desde:], resto.loc[desde:])
    segundo.append({"serie": f"PL · {NOMBRE[c]}", "prueba": "segundo corte, en el tramo posterior al primero",
                    "tramo_desde": str(desde),
                    "referencia": f"promedio de los demás pluviómetros ({sin_marcados})", **resultado})
# Si un pluviómetro tiene un segundo salto significativo, el salto de PI frente a PL podría venir de él y no
# de IMERG. Se repite entonces la prueba de PI contra una PL calculada sin esos pluviómetros.
con_segundo_corte = [c for c, fila in zip(marcados, segundo) if fila["significativo"]]
if con_segundo_corte:
    pl_sin = plu.drop(columns=con_segundo_corte).mean(axis=1)
    resultado, _ = medir_corte(pi, pl_sin)
    segundo.append({"serie": "PI (IMERG)", "prueba": "PI contra PL sin los pluviómetros con segundo corte",
                    "tramo_desde": str(MESES[0]),
                    "referencia": f"PL sin {', '.join(NOMBRE[c] for c in con_segundo_corte)}", **resultado})
pd.DataFrame(segundo).to_csv(OUT / "anomalias_segundo_corte.csv", index=False)

# ====================================================================== 2. secuencias constantes
rachas = []


def rachas_iguales(serie, minimo, variable, unidad, ignorar_cero=False):
    """Tramos de al menos `minimo` pasos seguidos con exactamente el mismo valor (los huecos cortan la racha)."""
    s = serie.dropna()
    if ignorar_cero:
        s = s[s != 0]
    # un paso nuevo empieza racha si cambia el valor o si no es el paso siguiente en el calendario
    paso = pd.Series(np.arange(len(serie)), index=serie.index).reindex(s.index)
    nueva = (s != s.shift()) | (paso.diff() != 1)
    grupo = nueva.cumsum()
    for _, g in s.groupby(grupo):
        if len(g) >= minimo:
            rachas.append({"variable": variable, "desde": str(g.index[0])[:10], "hasta": str(g.index[-1])[:10],
                           "largo": len(g), "valor": float(g.iloc[0]), "unidad": unidad})


rachas_iguales(q_dia, RACHA_MINIMA_DIAS, "Q diario", "m³/s")
for col, nombre in (("t_media", "T media ERA5-Land"), ("t_min", "T mín ERA5-Land"), ("t_max", "T máx ERA5-Land")):
    rachas_iguales(era[col], RACHA_MINIMA_DIAS, nombre, "°C")
for c in DENTRO:
    rachas_iguales(plu_crudo[c], RACHA_MINIMA_MESES, f"PL · {NOMBRE[c]} (mensual)", "mm", ignorar_cero=True)
pd.DataFrame(rachas, columns=["variable", "desde", "hasta", "largo", "valor", "unidad"]).to_csv(
    OUT / "anomalias_rachas.csv", index=False)

# ====================================================================== 3. picos aislados del Q diario
vecino_mayor = pd.concat([q_dia.shift(1), q_dia.shift(-1)], axis=1).max(axis=1, skipna=False)
es_pico = q_dia >= FACTOR_PICO * vecino_mayor
picos = pd.DataFrame({"fecha": q_dia.index[es_pico].strftime("%Y-%m-%d"),
                      "q_dia": q_dia[es_pico].values,
                      "q_dia_anterior": q_dia.shift(1)[es_pico].values,
                      "q_dia_siguiente": q_dia.shift(-1)[es_pico].values})
picos["veces_el_vecino_mayor"] = picos.q_dia / picos[["q_dia_anterior", "q_dia_siguiente"]].max(axis=1)
picos.to_csv(OUT / "anomalias_picos_q.csv", index=False)

# ====================================================================== 4. cobertura de PL
presentes = plu.notna()
completos = presentes.all(axis=1)
pl7 = plu[completos].mean(axis=1)
filas = []
for m in MESES[~completos.values]:
    grupo = [c for c in DENTRO if presentes.loc[m, c]]
    if not grupo:
        continue
    razon = (plu.loc[completos, grupo].mean(axis=1) / pl7).median()
    filas.append({"periodo": str(m), "pluviometros": len(grupo),
                  "faltan": ", ".join(NOMBRE[c] for c in DENTRO if c not in grupo),
                  "sesgo_estimado_pct": (razon - 1) * 100})
pd.DataFrame(filas).to_csv(OUT / "anomalias_cobertura_pl.csv", index=False)

# ====================================================================== 5. meses con 0 mm
ceros = []
for c in DENTRO:
    for m in plu_crudo.index[plu_crudo[c] == 0]:
        otros = plu_crudo.loc[m].drop(c).dropna()
        mismo_mes = plu_crudo[c][(plu_crudo.index.month == m.month) & (plu_crudo.index != m)].dropna()
        ceros.append({"pluviometro": NOMBRE[c], "periodo": str(m),
                      "otros_con_dato": len(otros), "otros_minimo_mm": otros.min(), "otros_promedio_mm": otros.mean(),
                      "pi_mm": pi[m], "mediana_propia_mismo_mes_mm": mismo_mes.median(),
                      "otros_ceros_propios_mismo_mes": int((mismo_mes == 0).sum()),
                      "dificil_de_creer": bool(len(otros) and otros.min() >= UMBRAL_CERO_MM)})
pd.DataFrame(ceros).to_csv(OUT / "anomalias_ceros_pl.csv", index=False)

# ====================================================================== resumen en pantalla
pd.set_option("display.width", 200)
print(pd.DataFrame(homog).round(3).to_string(index=False))
print("\nsegundo corte:")
print(pd.DataFrame(segundo).round(3).to_string(index=False))
print(f"\nrachas: {len(rachas)}; picos aislados de Q: {len(picos)}; meses con PL incompleta: {len(filas)}; ceros: {len(ceros)}")
