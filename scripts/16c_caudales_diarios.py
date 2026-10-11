"""Caudales diarios de San Gil: curva de duración, flujo base y extremos anuales.

El resto del informe trabaja con promedios mensuales. Este script mira el caudal diario de CAMELS-COL (IDEAM
24027010), sin rellenar ningún día, para tres descripciones estándar del régimen de un río:

1. CURVA DE DURACIÓN DE CAUDALES. Qué caudal se iguala o se supera qué fracción del tiempo. Con todos los días que
   tienen dato; posición de graficación de Weibull, p = rango / (n + 1). Q95 es el caudal superado el 95 % del
   tiempo (aguas bajas) y Q5 el superado el 5 % (aguas altas); la convención de CAMELS-COL es la inversa (su
   «Q5» es el percentil 5), y se compara con ella teniéndolo en cuenta. La pendiente entre los percentiles 33 y 66
   en logaritmos de base 10 es la firma que publica CAMELS-COL (slope_fdc).
2. FLUJO BASE. El caudal se separa en flujo rápido y flujo base con el filtro digital de Lyne y Hollick en la forma
   estándar de Ladson et al. (2013): α = 0.925, tres pasadas (adelante, atrás, adelante) y 30 días reflejados en
   cada extremo. Es el mismo método con que CAMELS-COL calcula su índice de flujo base (BFI). El filtro necesita
   días seguidos, así que se aplica a cada tramo continuo de al menos MIN_TRAMO días; los días sueltos entre
   huecos se dejan fuera. BFI = suma del flujo base / suma del caudal en los días filtrados.
3. EXTREMOS ANUALES. Por cada año, el caudal diario máximo y el mínimo del promedio móvil de 7 días. Un año entra
   solo si sus 12 meses cumplen la regla del proyecto (a ningún mes le faltan 5 días o más): en un año con huecos
   el máximo o el mínimo pudo caer en un día sin dato. A los máximos se les ajusta una distribución de Gumbel por
   momentos L (Hosking, 1990) y se dan los caudales de 2 a 50 años de período de retorno, con un intervalo de
   95 % remuestreando años (2 000 veces). Para los mínimos de 7 días se da el empírico de 10 años (7Q10), sin
   ajustar una distribución.

Ventanas (regla 6): la curva de duración y el flujo base, en 1998–2022 (la ventana común del informe) y, aparte, en
1981–2022; los extremos, con el registro completo 1981–2022, porque una estimación de frecuencias necesita todos
los años que haya y no compara variables.

Ejecutar desde la raíz del proyecto: python scripts/16c_caudales_diarios.py
Salidas (out/):
  caudales_curva_duracion.csv     curva de duración por ventana: probabilidad de excedencia y caudal (m³/s)
  caudales_firmas.csv             Q5, Q50, Q95, pendiente de la curva, BFI y su comparación con CAMELS-COL
  caudales_flujo_base_diario.csv  caudal y flujo base de cada día filtrado
  caudales_extremos_anuales.csv   por año válido: máximo diario, su fecha y mínimo de 7 días
  caudales_periodos_retorno.csv   caudal máximo diario de Gumbel para cada período de retorno, con su intervalo
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
MAX_DIAS_FALTANTES = 4           # regla del proyecto: un mes con 5 o más días faltantes queda vacío
ALFA_FILTRO = 0.925              # Ladson et al. (2013), el valor estándar del filtro de Lyne y Hollick
DIAS_REFLEJADOS = 30             # Ladson et al. (2013)
MIN_TRAMO = 90                   # tramo continuo mínimo para filtrar: tres veces lo que se refleja en cada extremo
PERIODOS_RETORNO = [2, 5, 10, 25, 50]
N_REMUESTREOS = 2000
EULER = 0.5772156649
VENTANAS = {"1998–2022": ("1998-01-01", "2022-12-31"), "1981–2022": ("1981-01-01", "2022-12-31")}
rng = np.random.default_rng(20261011)

# ---------------------------------------------------------------- caudal diario, sin rellenar
cam = pd.read_csv(RAIZ / f"data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_{ID_PRINCIPAL}.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam.fecha, format="%d/%m/%Y")
dias = pd.date_range("1981-01-01", "2022-12-31", freq="D")
q = cam.set_index("fecha").caudal.reindex(dias)          # m³/s; los días sin fila quedan vacíos
area_km2 = float(pd.read_csv(OUT / "shp_fonce/areas_cuencas.csv").set_index("gauge_id").loc[ID_PRINCIPAL, "area_km2"])
A_MM_DIA = 86400 / (area_km2 * 1e6) * 1000               # m³/s -> mm/día sobre la cuenca


# ---------------------------------------------------------------- 1. curva de duración
def curva_duracion(serie):
    valores = np.sort(serie.dropna().to_numpy())[::-1]
    excedencia = np.arange(1, len(valores) + 1) / (len(valores) + 1)
    return pd.DataFrame({"excedencia": excedencia, "caudal_m3s": valores})


def caudal_excedido(curva, p):
    """Caudal igualado o superado una fracción p del tiempo (interpolación en la curva)."""
    return float(np.interp(p, curva.excedencia, curva.caudal_m3s))


# ---------------------------------------------------------------- 2. flujo base (Lyne y Hollick, Ladson et al. 2013)
def _pasada(x, alfa):
    rapido = np.zeros_like(x)
    for i in range(1, len(x)):
        rapido[i] = alfa * rapido[i - 1] + (1 + alfa) / 2 * (x[i] - x[i - 1])
    rapido = np.clip(rapido, 0, x)           # el flujo rápido no es negativo ni mayor que el caudal
    return x - rapido                        # flujo base


def flujo_base(tramo, alfa=ALFA_FILTRO, reflejo=DIAS_REFLEJADOS):
    x = tramo.to_numpy(dtype=float)
    ext = np.concatenate([x[reflejo:0:-1], x, x[-2:-reflejo - 2:-1]])
    b = _pasada(ext, alfa)                   # adelante
    b = _pasada(b[::-1], alfa)[::-1]         # atrás
    b = _pasada(b, alfa)                     # adelante
    return pd.Series(b[reflejo:reflejo + len(x)], index=tramo.index)


hay = q.notna()
id_tramo = (hay != hay.shift()).cumsum()
partes = []
for _, tramo in q[hay].groupby(id_tramo[hay]):
    if len(tramo) >= MIN_TRAMO:
        partes.append(pd.DataFrame({"caudal_m3s": tramo, "flujo_base_m3s": flujo_base(tramo)}))
base = pd.concat(partes)
assert (base.flujo_base_m3s <= base.caudal_m3s + 1e-9).all() and (base.flujo_base_m3s >= 0).all()

# ---------------------------------------------------------------- firmas por ventana
camels = pd.read_csv(RAIZ / "data/camels_col/09_CAMELS_COL_Hydrological_signatures.csv").set_index("gauge_id")
camels = camels.loc[ID_PRINCIPAL]
curvas, firmas = [], []
for nombre, (ini, fin) in VENTANAS.items():
    serie = q.loc[ini:fin]
    curva = curva_duracion(serie)
    curvas.append(curva.assign(ventana=nombre))
    b = base.loc[ini:fin]
    q33, q66 = caudal_excedido(curva, 0.33), caudal_excedido(curva, 0.66)
    firmas.append({
        "ventana": nombre, "dias_con_dato": int(serie.notna().sum()), "dias": len(serie),
        "q_medio_m3s": serie.mean(),
        "q5_m3s": caudal_excedido(curva, 0.05), "q10_m3s": caudal_excedido(curva, 0.10),
        "q50_m3s": caudal_excedido(curva, 0.50), "q90_m3s": caudal_excedido(curva, 0.90),
        "q95_m3s": caudal_excedido(curva, 0.95),
        # pendiente de la curva entre los percentiles 33 y 66, en logaritmos de base 10: es la versión con que
        # se reproduce el valor que publica CAMELS-COL (con logaritmo natural sale 2.3 veces mayor)
        "pendiente_curva": (np.log10(q33) - np.log10(q66)) / (0.66 - 0.33),
        "dias_filtrados": len(b), "bfi": b.flujo_base_m3s.sum() / b.caudal_m3s.sum(),
    })
firmas = pd.DataFrame(firmas).set_index("ventana")
for c in ["q_medio", "q5", "q10", "q50", "q90", "q95"]:
    firmas[f"{c}_mm_dia"] = firmas[f"{c}_m3s"] * A_MM_DIA
    firmas[f"{c}_l_s_km2"] = firmas[f"{c}_m3s"] * 1000 / area_km2          # rendimiento específico
# lo que publica CAMELS-COL para San Gil (mm/día sobre sus 2 124 km²; su «Q95» es nuestro Q5 y su «Q5», nuestro Q95)
firmas["camels_q_alto_mm_dia"] = camels.Q95
firmas["camels_q_bajo_mm_dia"] = camels.Q5
firmas["camels_pendiente_curva"] = camels.slope_fdc
firmas["camels_bfi"] = camels.baseflow_index
assert firmas.q5_m3s.gt(firmas.q50_m3s).all() and firmas.q50_m3s.gt(firmas.q95_m3s).all()

# ---------------------------------------------------------------- 3. extremos anuales
faltan_mes = q.isna().resample("MS").sum()
anio_valido = (faltan_mes <= MAX_DIAS_FALTANTES).groupby(faltan_mes.index.year).all()
validos = anio_valido[anio_valido].index
q7 = q.rolling(7).mean()                     # promedio de 7 días que terminan ese día (vacío si falta alguno)
extremos = pd.DataFrame({
    "maximo_diario_m3s": q.groupby(q.index.year).max(),
    "fecha_maximo": q.groupby(q.index.year).idxmax().dt.strftime("%Y-%m-%d"),
    "minimo_7_dias_m3s": q7.groupby(q7.index.year).min(),
    "fecha_minimo_7_dias": q7.groupby(q7.index.year).idxmin().dt.strftime("%Y-%m-%d"),
    "dias_faltantes": q.isna().groupby(q.index.year).sum(),
}).loc[validos]
extremos.index.name = "anio"
assert len(extremos) >= 15


def gumbel_momentos_l(x):
    """Parámetros de Gumbel (posición, escala) por momentos L (Hosking, 1990)."""
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    b0 = x.mean()
    b1 = np.sum((np.arange(n) / (n - 1)) * x) / n
    l1, l2 = b0, 2 * b1 - b0
    escala = l2 / np.log(2)
    return l1 - EULER * escala, escala


def gumbel_cuantil(posicion, escala, T):
    return posicion - escala * np.log(-np.log(1 - 1 / np.asarray(T, dtype=float)))


maximos = extremos.maximo_diario_m3s.to_numpy()
pos, esc = gumbel_momentos_l(maximos)
remuestreos = np.array([gumbel_cuantil(*gumbel_momentos_l(rng.choice(maximos, len(maximos))), PERIODOS_RETORNO)
                        for _ in range(N_REMUESTREOS)])
retorno = pd.DataFrame({
    "periodo_retorno_anios": PERIODOS_RETORNO,
    "caudal_m3s": gumbel_cuantil(pos, esc, PERIODOS_RETORNO),
    "ic95_inferior_m3s": np.percentile(remuestreos, 2.5, axis=0),
    "ic95_superior_m3s": np.percentile(remuestreos, 97.5, axis=0),
    "n_anios": len(maximos), "posicion_gumbel": pos, "escala_gumbel": esc,
})
# bondad del ajuste: correlación entre los máximos ordenados y los cuantiles de Gumbel en las posiciones de Weibull
orden = np.sort(maximos)
p_weibull = np.arange(1, len(orden) + 1) / (len(orden) + 1)
r_ppcc = float(np.corrcoef(orden, pos - esc * np.log(-np.log(p_weibull)))[0, 1])
retorno["r_ajuste"] = r_ppcc
# 7Q10 empírico: el mínimo de 7 días que no se alcanza en 9 de cada 10 años (percentil 10, Weibull)
minimos = np.sort(extremos.minimo_7_dias_m3s.to_numpy())
q7_10 = float(np.interp(0.10, np.arange(1, len(minimos) + 1) / (len(minimos) + 1), minimos))
firmas["q7_10_m3s"] = q7_10
firmas["anios_extremos"] = len(extremos)

# ---------------------------------------------------------------- salidas
pd.concat(curvas).to_csv(OUT / "caudales_curva_duracion.csv", index=False)
firmas.to_csv(OUT / "caudales_firmas.csv")
base.rename_axis("fecha").to_csv(OUT / "caudales_flujo_base_diario.csv", float_format="%.3f")
extremos.to_csv(OUT / "caudales_extremos_anuales.csv")
retorno.to_csv(OUT / "caudales_periodos_retorno.csv", index=False)
print(firmas.T.round(3).to_string())
print(retorno.round(1).to_string())
print(f"r del ajuste de Gumbel: {r_ppcc:.3f}; 7Q10 = {q7_10:.1f} m³/s; años: {list(extremos.index)}")
