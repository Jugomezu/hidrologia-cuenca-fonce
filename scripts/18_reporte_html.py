"""Arma reporte/reporte-fonce.html a partir de las figuras de reporte/figuras/ y de los datos del proyecto.

Las figuras se incrustan en base64 para que el HTML sea un solo archivo. Los números del texto se calculan
aquí a partir de los datos, no se escriben a mano. Para regenerar:

    python scripts/08_mapas_y_pixeles.py
    python scripts/09_gradiente_altitudinal.py
    python scripts/18_reporte_html.py
"""
import base64, html, json
from pathlib import Path
import geopandas as gpd
from scipy import stats
import numpy as np
import pandas as pd

FIG = Path("reporte/figuras")
SALIDA = Path("reporte/reporte-fonce.html")

ESTACIONES = {
    24027010: ("San Gil", "Fonce"), 24027070: ("Mérida", "Fonce"), 24027030: ("Nemizaque", "Pienta"),
    24027050: ("Puente Llano", "Taquiza"), 24027040: ("Puente Cabra", "Mogoticos"), 24027060: ("Puente Arco", "Monchía"),
}

m = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id").loc[list(ESTACIONES)]
# El área de cada cuenca es la del polígono, medida por scripts/02_shp_cuencas_estaciones.py (geodésica);
# no la que publica CAMELS-COL en su tabla de atributos, que es 1,2 % mayor para San Gil.
_areas = pd.read_csv("out/shp_fonce/areas_cuencas.csv").set_index("gauge_id")["area_km2"]
m["area"] = _areas.reindex(m.index)
im = pd.read_csv("out/imerg_mensual_fonce.csv")
im["anio"] = im["periodo"].str[:4].astype(int)
p_imerg = im.groupby(["id_estacion", "anio"])["p_imerg_mm"].sum().groupby("id_estacion").mean()
pix = pd.read_csv("out/imerg_pixeles_fonce.csv")


def img(nombre):
    return "data:image/png;base64," + base64.b64encode((FIG / nombre).read_bytes()).decode()


def n(x, dec=0):
    return f"{x:,.{dec}f}".replace(",", " ")        # separador de miles con espacio


sg = m.loc[24027010]
filas = "\n".join(
    f"<tr><td class='cod'>{i}</td><td>{html.escape(nom)}</td><td>{rio}</td>"
    f"<td class='num'>{n(m.loc[i, 'area'])}</td><td class='num'>{m.loc[i, 'area'] / sg['area'] * 100:.0f}%</td>"
    f"<td class='num'>{n(m.loc[i, 'minimum_ele'])}–{n(m.loc[i, 'maximum_ele'])}</td>"
    f"<td class='num'>{n(m.loc[i, 'mean_ele'])}</td><td class='num'>{n(p_imerg[i])}</td></tr>"
    for i, (nom, rio) in ESTACIONES.items())

n_pix = len(pix)
n_mitad = int((pix.frac_dentro > 0.5).sum())
n_llenos = int((pix.frac_dentro > 0.99).sum())
pmin, pmax = pix.p_anual.min(), pix.p_anual.max()
dentro = pix[pix.frac_dentro > 0.5]
p_dmin, p_dmax = dentro.p_anual.min(), dentro.p_anual.max()

# --- píxeles de ERA5-Land con su temperatura media (scripts/06_era5land_temperatura.py) ---
# Misma malla de 0.1° que IMERG pero corrida medio píxel: los centros de ERA5-Land caen en múltiplos
# exactos de 0.1° y los de IMERG en los terminados en 0.05°, así que no son las mismas celdas.
tpx = pd.read_csv("out/era5land_pixeles_fonce.csv")
tpx_dentro = tpx[tpx.frac_dentro > 0]
t_npix = len(tpx)
t_nmitad = int((tpx.frac_dentro > 0.5).sum())
t_min_px, t_max_px = tpx.t_media.min(), tpx.t_media.max()
# Para el titular se usan solo los píxeles con más de la mitad del área dentro de la cuenca, el mismo
# criterio que la figura de IMERG: el píxel más cálido de todos los que la tocan apenas tiene un 6 %
# de su área adentro y exageraría el gradiente.
tpx_mitad = tpx[tpx.frac_dentro > 0.5]
t_min_mitad, t_max_mitad = tpx_mitad.t_media.min(), tpx_mitad.t_media.max()
t_ponderada = (tpx_dentro.t_media * tpx_dentro.frac_dentro).sum() / tpx_dentro.frac_dentro.sum()
t_serie = pd.read_csv("out/era5land_temperatura_diaria_fonce.csv", parse_dates=["fecha"])
t_serie_media = t_serie.t_media.mean()
t_amplitud_px = t_max_px - t_min_px

# ---------------------------------------------------------------- series de CAMELS-COL (San Gil)
# Un mes de una serie diaria cuenta como completo si le faltan MAX_DIAS_FALTANTES días o menos
# (regla del proyecto, la misma del notebook).
MAX_DIAS_FALTANTES = 4
ANIOS_ESTUDIO = range(1998, 2023)
PERIODOS = pd.period_range(f"{min(ANIOS_ESTUDIO)}-01", f"{max(ANIOS_ESTUDIO)}-12", freq="M")

cam = pd.read_csv("data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_24027010.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam["fecha"], format="%d/%m/%Y")
cam = cam.set_index("fecha").sort_index().reindex(
    pd.date_range(f"{min(ANIOS_ESTUDIO)}-01-01", f"{max(ANIOS_ESTUDIO)}-12-31", freq="D"))


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


p_camels = a_mensual(cam["p_chirps"], "sum")
q_mes_ok = a_mensual(cam["caudal"], "mean").notna()


# ---------------------------------------------------------------- IMERG vs pluviómetros
# Los 8 pluviómetros del IDEAM con serie mensual en 1998-2022. Solo los 7 que caen dentro de la
# divisoria entran al promedio de la red; Mamonal El Hacienda está en la vertiente del Chicamocha.
cat_plu = pd.read_csv("out/pluviometros_fonce_catalogo.csv").set_index("codigo")
cat_plu["etiqueta"] = (cat_plu["nombre"].str.replace(r"\s*\[\d+\]", "", regex=True)
                       .str.title().str.replace(" De ", " de "))
DENTRO = cat_plu.index[cat_plu["dentro_cuenca"]].tolist()
COD_PLUVIO = {c: f"{cat_plu.loc[c, 'etiqueta']} ({cat_plu.loc[c, 'altitud']:,.0f} m)".replace(",", " ")
              for c in DENTRO}
n_plu_fuera = int((~cat_plu["dentro_cuenca"]).sum())

pm = pd.read_csv("out/pluviometros_fonce_mensual_depurado.csv", parse_dates=["fecha"])
pm["periodo"] = pm["fecha"].dt.to_period("M")
plu = pm.pivot(index="periodo", columns="codigo", values="precipitacion_mm")

# El promedio de la red usa, cada mes, los pluviómetros que tengan dato ese mes. No se rellena ninguno.
red = plu[DENTRO].mean(axis=1, skipna=True)
plu_por_mes = plu[DENTRO].notna().sum(axis=1)

imm = pd.read_csv("out/imerg_mensual_fonce.csv")
imm["periodo"] = pd.PeriodIndex(imm["periodo"], freq="M")
comp = pd.concat([imm[imm.id_estacion == 24027010].set_index("periodo")["p_imerg_mm"].rename("IMERG"),
                  p_camels.rename("CAMELS"), red.rename("RED"), plu[DENTRO]], axis=1).sort_index()
comp = comp.loc[imm.periodo.min():imm.periodo.max()]      # solo el período en que existe IMERG
plu_por_mes = plu_por_mes.reindex(comp.index).fillna(0).astype(int)


def serie(col):
    return [None if pd.isna(v) else round(float(v), 1) for v in comp[col]]


# Paleta apta para daltonismo (Okabe-Ito). Decisión de dibujo: los pluviómetros individuales van
# tenues, como nube de fondo, y el promedio de la red va a plena opacidad encima. Lo que compite con
# el satélite es la red, no cada aparato.
AZUL, VERDE, NARANJA = "#0072B2", "#009E73", "#D55E00"
nube = [{"nombre": nom, "color": NARANJA, "grosor": 1.0, "guion": None, "opacidad": 0.20,
         "enLeyenda": i == 0, "grupo": "pluviometros",
         "etiquetaGrupo": "pluviómetros, uno a uno", "y": serie(cod)}
        for i, (cod, nom) in enumerate(COD_PLUVIO.items())]
cmp_datos = {
    "meses": [str(x) for x in comp.index],
    "series": nube + [
        {"nombre": "PI · IMERG", "color": AZUL, "grosor": 2.2, "guion": None, "y": serie("IMERG")},
        {"nombre": f"PL · promedio de {len(DENTRO)} pluviómetros", "color": NARANJA,
         "grosor": 2.0, "guion": "dash", "y": serie("RED")}],
}
ciclo = comp.groupby(comp.index.month).mean()
cmp_datos["ciclo"] = (
    [{"nombre": COD_PLUVIO[cod], "color": NARANJA, "guion": None, "opacidad": 0.22,
      "enLeyenda": False, "grupo": "pluviometros",
      "y": [round(float(v), 1) for v in ciclo[cod]]}
     for cod in COD_PLUVIO]
    + [{"nombre": nombre, "color": color, "guion": guion,
        "y": [round(float(v), 1) for v in ciclo[col]]}
       for col, nombre, color, guion in [("IMERG", "PI · IMERG", AZUL, None),
                                         ("RED", f"PL · promedio de {len(DENTRO)} pluviómetros",
                                          NARANJA, "dash")]])
cmp_stats = {}
for cod, nom in ([("RED", f"promedio de los {len(DENTRO)} pluviómetros")]
                 + list(COD_PLUVIO.items())):
    par = comp[["IMERG", cod]].dropna()
    cmp_stats[nom] = {"n": len(par), "imerg": par["IMERG"].mean(), "pluv": par[cod].mean(),
                      "sesgo": (par["IMERG"].mean() / par[cod].mean() - 1) * 100,
                      "r": par["IMERG"].corr(par[cod])}
NOM_RED = f"promedio de los {len(DENTRO)} pluviómetros"
red_anual = comp[["IMERG", "RED"]].dropna()
red_anual = red_anual.groupby(red_anual.index.year).sum()[
    comp[["IMERG", "RED"]].dropna().groupby(comp[["IMERG", "RED"]].dropna().index.year).size() == 12]
# elevación de la cuenca: la que mide el proyecto sobre el DEM (13_morfometria.py) y la que publica
# CAMELS-COL, para compararlas
_morfo = pd.read_csv("out/morfometria_fonce.csv").set_index("magnitud")["valor"]
elev_min, elev_media, elev_max = (float(_morfo[k]) for k in ("altura mínima", "altura media", "altura máxima"))
elev_dif_max = max(abs(elev_min - sg["minimum_ele"]), abs(elev_max - sg["maximum_ele"]),
                   abs(elev_media - sg["mean_ele"]))

# Encino con su tramo 2016-2018: solo para explicar por qué se excluyó, así que se lee la serie CRUDA
pm_crudo = pd.read_csv("out/pluviometros_fonce_mensual_1998_2022.csv", parse_dates=["fecha"])
enc = pm_crudo[pm_crudo.codigo == 24020040].set_index("fecha")["precipitacion_mm"]
enc_media = enc.mean() * 12        # promedio de todo el período, igual que en la tabla de arriba
enc_conteo = enc.groupby(enc.index.year).count()
enc_anual = enc.groupby(enc.index.year).sum()[enc_conteo == 12]   # solo años con los 12 meses
enc_raros = enc_anual.loc[[2016, 2017, 2018]]
enc_normal = enc_anual.drop([2016, 2017, 2018]).mean()
# qué le hacía ese tramo a PL: anomalía anual de 2017 con y sin Encino, contra la de PI
_red_cruda = (pm_crudo.assign(p=pm_crudo.fecha.dt.to_period("M"))
              .pivot(index="p", columns="codigo", values="precipitacion_mm")[DENTRO].mean(axis=1))
_anom = lambda s: (s.groupby(s.index.year).sum() / s.groupby(s.index.year).sum().mean() - 1) * 100
_pi_mensual = imm[imm.id_estacion == 24027010].set_index("periodo")["p_imerg_mm"]
exc_2017 = {"crudo": _anom(_red_cruda)[2017], "depurado": _anom(red)[2017], "pi": _anom(_pi_mensual)[2017]}
exclusiones = pd.read_csv("out/pluviometros_exclusiones.csv", dtype={"evidencia": str})
exc_meses = int(exclusiones[exclusiones.codigo == 24020040].meses_excluidos.sum())      # los de Encino
cmp_json = json.dumps(cmp_datos, ensure_ascii=False)
filas_cmp = "\n".join(
    f"<tr><td>{html.escape(nom)}</td><td class='num'>{v['n']}</td><td class='num'>{v['imerg']:.0f}</td>"
    f"<td class='num'>{v['pluv']:.0f}</td><td class='num'>{v['sesgo']:+.0f}%</td>"
    f"<td class='num'>{v['r']:.2f}</td></tr>" for nom, v in cmp_stats.items())
mes_ini, mes_fin = str(comp.index.min()), str(comp.index.max())


# ---------------------------------------------------------------- lluvia y caudal en las mismas unidades
# El caudal viene en m3/s; dividido por el área de la cuenca queda como lámina (mm), comparable
# directamente con la lluvia. Área de San Gil: la del polígono (areas_cuencas.csv).
AREA_SG_KM2 = float(m.loc[24027010, "area"])
cam["caudal_mm"] = cam["caudal"] * 86400 / (AREA_SG_KM2 * 1e6) * 1000      # m3/s -> mm/día
q_camels = a_mensual(cam["caudal_mm"], "sum")

balance = pd.DataFrame({"p": imm[imm.id_estacion == 24027010].set_index("periodo")["p_imerg_mm"],
                        "q": q_camels}).reindex(PERIODOS)
balance["escorrentia"] = balance.q / balance.p
bal_completos = balance.dropna(subset=["p", "q"])
coef_periodo = bal_completos.q.sum() / bal_completos.p.sum()
bal_datos = {
    "meses": [str(x) for x in balance.index],
    "p": [None if pd.isna(v) else round(float(v), 1) for v in balance.p],
    "q": [None if pd.isna(v) else round(float(v), 1) for v in balance.q],
    "coef": [None if pd.isna(v) else round(float(v), 3) for v in balance.escorrentia],
    "coef_medio": round(float(coef_periodo), 3),
    # el mismo coeficiente con PL, que manda
    "coef_pl": [None if pd.isna(v) else round(float(v), 3) for v in (balance.q / red.reindex(PERIODOS))],
}
bal_json = json.dumps(bal_datos, ensure_ascii=False)


# ---------------------------------------------------------------- estadísticos de las cuatro variables
_t_era5 = pd.read_csv("out/era5land_temperatura_diaria_fonce.csv", parse_dates=["fecha"]).set_index("fecha")
# Cada variable con TODOS sus meses válidos (no se cruzan entre sí): PI y PL tienen los 300 meses, Q y
# la temperatura pierden los que no cumplen la regla de los días faltantes. Es la misma tabla de la
# sección 1.0 del notebook, calculada igual.
variables_resumen = pd.DataFrame({
    "PI": comp["IMERG"].reindex(PERIODOS),
    "PL": red.reindex(PERIODOS),
    # en la tabla el caudal va en m³/s: promedio mensual del caudal diario, con la regla de los días
    "Q": a_mensual(cam["caudal"], "mean"),
    # ERA5-Land: media diaria verdadera (promedio de 24 h), sin huecos (decisión del 2026-09-27)
    # la máxima y la mínima: promedio mensual de la máxima y de la mínima diarias
    **{nombre: a_mensual(_t_era5[col].reindex(cam.index), "mean")
       for nombre, col in (("T media", "t_media"), ("T máx", "t_max"), ("T mín", "t_min"))},
})


def estadisticos(serie):
    """Estadística descriptiva de una serie mensual. Percentiles por interpolación lineal (método 7 de
    Hyndman y Fan), fijada a propósito; desviación estándar muestral."""
    s = serie.dropna()
    p = lambda q: s.quantile(q, interpolation="linear")
    return {
        "meses válidos": len(s), "media": s.mean(), "mediana": s.median(),
        "desviación estándar": s.std(ddof=1), "mínimo": s.min(), "máximo": s.max(),
        "rango": s.max() - s.min(), "Q1 (percentil 25)": p(0.25), "Q3 (percentil 75)": p(0.75),
        "rango intercuartil": p(0.75) - p(0.25), "percentil 5": p(0.05), "percentil 10": p(0.10),
        "percentil 90": p(0.90), "percentil 95": p(0.95),
    }


tabla_resumen = pd.DataFrame({col: estadisticos(variables_resumen[col]) for col in variables_resumen})
# para los diagramas de caja: los valores de cada variable agrupados por mes del calendario
NOMBRE_MES_COMPLETO = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio",
                       8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
UNIDAD_RESUMEN = {"PI": "mm/mes", "PL": "mm/mes", "Q": "m³/s", "T media": "°C", "T máx": "°C", "T mín": "°C"}
# ---------------------------------------------------------------- revisión de atípicos
# Mismo criterio que los diagramas de caja: un mes es atípico si se sale FACTOR_ATIPICO rangos
# intercuartiles por encima del percentil 75 o por debajo del 25 DE SU PROPIO MES DEL CALENDARIO
FACTOR_ATIPICO = 1.5
# (un abril se compara
# con los otros abriles). Para leerlos juntos, cada valor se expresa además como su desvío respecto a la
# mediana de su mes, en rangos intercuartiles (z): z = +2 es "dos rangos intercuartiles sobre lo normal
# para ese mes".
def _atipicos(serie):
    marca = pd.Series("", index=serie.index)
    for m in range(1, 13):
        x = serie[serie.index.month == m].dropna()
        q1, q3 = x.quantile(0.25, interpolation="linear"), x.quantile(0.75, interpolation="linear")
        ric = q3 - q1
        marca[x.index[x > q3 + FACTOR_ATIPICO * ric]] = "alto"
        marca[x.index[x < q1 - FACTOR_ATIPICO * ric]] = "bajo"
    return marca


def _z(serie):
    por_mes = serie.groupby(serie.index.month)
    q1 = por_mes.transform(lambda x: x.quantile(0.25, interpolation="linear"))
    q3 = por_mes.transform(lambda x: x.quantile(0.75, interpolation="linear"))
    return (serie - por_mes.transform("median")) / (q3 - q1)


VARS_ATIP = list(variables_resumen.columns)          # PI, PL, Q, T media, T máx, T mín
atip_marca = pd.DataFrame({v: _atipicos(variables_resumen[v]) for v in VARS_ATIP})
atip_z = pd.DataFrame({v: _z(variables_resumen[v]) for v in VARS_ATIP})
atip_meses = atip_marca.index[(atip_marca != "").any(axis=1)]
atip_conteo = {v: int((atip_marca[v] != "").sum()) for v in VARS_ATIP}

# Lecturas, con reglas explícitas:
UMBRAL_RESPUESTA = 1.0     # el río "responde" si su z llega a ±1 en el mes o en el siguiente
_zq = atip_z["Q"]
_zq_sig = _zq.shift(-1)
_resp_alta = pd.concat([_zq, _zq_sig], axis=1).max(axis=1) >= UMBRAL_RESPUESTA
_resp_baja = pd.concat([_zq, _zq_sig], axis=1).min(axis=1) <= -UMBRAL_RESPUESTA
_lluvia_alta = (atip_marca.PI == "alto") | (atip_marca.PL == "alto")
_lluvia_baja = (atip_marca.PI == "bajo") | (atip_marca.PL == "bajo")
# 1. lluvia extrema que el río confirma
lluvia_confirmada = atip_meses[(_lluvia_alta & _resp_alta).reindex(atip_meses)]
seco_confirmado = atip_meses[(_lluvia_baja & _resp_baja).reindex(atip_meses)]
# fase ENSO de los meses de lluvia extrema confirmada (el ONI se lee más abajo; aquí se reparte la lista)
# 2. posible error de PI: solo PI es atípico, PL está dentro de ±1 y el río no acompaña
_solo_pi_alto = (atip_marca.PI == "alto") & (atip_marca.PL == "") & (atip_z.PL.abs() < 1) & ~_resp_alta
_solo_pi_bajo = (atip_marca.PI == "bajo") & (atip_marca.PL == "") & (atip_z.PL.abs() < 1) & ~_resp_baja
error_pi = atip_meses[(_solo_pi_alto | _solo_pi_bajo).reindex(atip_meses)]
# 3. caudal atípico sin lluvia atípica ni ese mes ni el anterior: cuánto llovió en esos dos meses
_q_alto = atip_marca.Q == "alto"
_lluvia_atip_2m = _lluvia_alta | _lluvia_alta.shift(1, fill_value=False)
q_sin_lluvia = atip_meses[(_q_alto & ~_lluvia_atip_2m).reindex(atip_meses)]
q_sin_lluvia_zpl = {p: float(max(atip_z.PL.get(p, np.nan), atip_z.PL.get(p - 1, np.nan))) for p in q_sin_lluvia}
# 4. temperaturas: cómo estaban la lluvia y el caudal en los meses con temperatura atípica
def _media_z(meses, v):
    return float(atip_z.loc[meses, v].mean())
t_min_alta = atip_marca.index[atip_marca["T mín"] == "alto"]
t_max_baja = atip_marca.index[atip_marca["T máx"] == "bajo"]
t_max_alta = atip_marca.index[atip_marca["T máx"] == "alto"]
t_min_alta_anios = sorted({p.year for p in t_min_alta})

# Febrero de 1999: no alcanza el criterio de atípico en PI ni en PL, pero es el febrero más lluvioso del
# período en las dos fuentes. Se calcula cuánto le falta y cuánto supera al segundo febrero más lluvioso.
_F99 = pd.Period("1999-02", "M")


def _record_mes(v, p):
    x = variables_resumen[v][variables_resumen.index.month == p.month].dropna().sort_values(ascending=False)
    q1, q3 = x.quantile(0.25, interpolation="linear"), x.quantile(0.75, interpolation="linear")
    return {"valor": float(x[p]), "es_maximo": x.index[0] == p, "segundo": float(x.iloc[1]),
            "factor": float((x[p] - q3) / (q3 - q1))}


feb99 = {v: _record_mes(v, _F99) for v in ("PI", "PL")}
feb99_q_atipico = atip_marca.loc[_F99, "Q"] == "alto"

# Enero de 2005: hoy no es atípico, pero lo era en PL antes de excluir el primer tramo de Pueblo Viejo
# (1998-01 a 2004-11). Su valor no cambió: cambió el umbral, porque ese tramo bajaba los eneros de 1998-2004.
# Para documentarlo se rearma PL con todas las exclusiones menos esa (solo aquí; el análisis usa la depurada).
_E05, _F05 = pd.Period("2005-01", "M"), pd.Period("2005-02", "M")
_pm_crudo = pd.read_csv("out/pluviometros_fonce_mensual_1998_2022.csv", parse_dates=["fecha"])
_pm_crudo["periodo"] = _pm_crudo.fecha.dt.to_period("M")
_plu_con_pv = _pm_crudo.pivot(index="periodo", columns="codigo", values="precipitacion_mm")[DENTRO].copy()
for _e in pd.read_csv("out/pluviometros_exclusiones.csv").itertuples():
    if _e.codigo != 24020230 or _e.desde != "1998-01":
        _plu_con_pv.loc[pd.Period(_e.desde, "M"):pd.Period(_e.hasta, "M"), _e.codigo] = np.nan
_red_con_pv = _plu_con_pv.mean(axis=1).reindex(PERIODOS)


def _umbral_alto(serie, mes):
    x = serie[serie.index.month == mes].dropna()
    q1, q3 = x.quantile(0.25, interpolation="linear"), x.quantile(0.75, interpolation="linear")
    return q3 + FACTOR_ATIPICO * (q3 - q1)


ene05 = {"pl": float(variables_resumen.loc[_E05, "PL"]), "pl_con_pv": float(_red_con_pv[_E05]),
         "umbral_hoy": _umbral_alto(variables_resumen["PL"], 1), "umbral_antes": _umbral_alto(_red_con_pv, 1),
         "z_pl": atip_z.loc[_E05, "PL"], "z_pi": atip_z.loc[_E05, "PI"], "z_q": atip_z.loc[_E05, "Q"],
         "z_pl_feb": atip_z.loc[_F05, "PL"], "z_pi_feb": atip_z.loc[_F05, "PI"], "z_q_feb": atip_z.loc[_F05, "Q"]}
# el valor de enero de 2005 es el mismo con y sin el tramo (Pueblo Viejo sí tiene dato desde 2004-12)
assert abs(ene05["pl"] - ene05["pl_con_pv"]) < 1e-9
# el texto dice que antes era atípico y hoy no: si los datos dejan de respaldarlo, el script se detiene
assert ene05["umbral_antes"] < ene05["pl"] <= ene05["umbral_hoy"]

# citas de la bibliografía (la lista completa está en la sección «Bibliografía», al final)
CITA_POVEDA = '<a class="cita" href="#ref-poveda2004">Poveda, 2004</a>'
CITA_JIMENEZ = '<a class="cita" href="#ref-jimenez2025">Jimenez et al., 2025</a>'
CITA_HARGREAVES = '<a class="cita" href="#ref-hargreaves1985">Hargreaves y Samani, 1985</a>'
CITA_PETTITT = '<a class="cita" href="#ref-pettitt1979">Pettitt, 1979</a>'
CITA_IMERG_DOC = '<a class="cita" href="#ref-huffman2023">Huffman et al., 2023</a>'
CITA_FAO = '<a class="cita" href="#ref-allen1998">Allen et al., 1998</a>'
CITA_DEFENSORIA = '<a class="cita" href="#ref-defensoria2005">Defensoría del Pueblo, 2005</a>'
CITA_BECK = '<a class="cita" href="#ref-beck2022">Beck et al., 2022</a>'
CITA_HYNDMAN = '<a class="cita" href="#ref-hyndman1996">Hyndman y Fan, 1996</a>'
CITA_ONI = '<a class="cita" href="#ref-noaa-oni">NOAA CPC</a>'
CITA_KRUSKAL = '<a class="cita" href="#ref-kruskal1952">Kruskal y Wallis, 1952</a>'
CITA_HORN = '<a class="cita" href="#ref-horn1960">Horn y Bryson, 1960</a>'

NOMBRE_MES_CORTO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 7: "jul", 8: "ago",
                    9: "sep", 10: "oct", 11: "nov", 12: "dic"}
fmt_mes = lambda p: f"{NOMBRE_MES_CORTO[p.month]} {p.year}"

# fase de El Niño / La Niña de cada mes según el ONI de la NOAA (17_oni_enso.py); solo se usa para
# colorear las fechas, sin sacar conclusiones todavía
oni_fase = pd.read_csv("out/oni_mensual.csv")
oni_fase = oni_fase.set_index(pd.PeriodIndex(oni_fase.periodo, freq="M"))["fase"]
CLASE_FASE = {"El Niño": "fase-nino", "La Niña": "fase-nina"}


def fecha_enso(p):
    clase = CLASE_FASE.get(oni_fase.get(p, "neutro"))
    texto = fmt_mes(p)
    return f"<span class='{clase}' title='{oni_fase.get(p)}'>{texto}</span>" if clase else texto


lista_meses = lambda meses: ", ".join(fecha_enso(p) for p in meses) if len(meses) else "ninguno"

# Lectura ENSO de la lluvia extrema confirmada: cuáles cayeron en La Niña y cuáles no. Para enero de 2005,
# la única excepción al escribir esto, hay un documento que describe el evento; si la lista cambiara, el
# texto se arma igual con lo que haya.
_confirmada_nina = [p for p in lluvia_confirmada if oni_fase.get(p) == "La Niña"]
_confirmada_otras = [p for p in lluvia_confirmada if oni_fase.get(p) != "La Niña"]
lectura_enso_lluvia = (
    f"Todos, menos {lista_meses(_confirmada_otras)}, cayeron en episodios de La Niña."
    if _confirmada_nina and _confirmada_otras else
    "Todos cayeron en episodios de La Niña." if _confirmada_nina else "")
# enero y febrero de 2005 (emergencia invernal en Santander) tienen su propio punto en la lista, siempre visible


def _celda_atip(p, v):
    z = atip_z.loc[p, v]
    if pd.isna(z):
        return "<td class='num cod'>—</td>"
    marca = atip_marca.loc[p, v]
    clase = {"alto": " atip-alto", "bajo": " atip-bajo"}.get(marca, "")
    return f"<td class='num{clase}'>{z:+.1f}</td>"


filas_atip = "\n".join(
    f"<tr><td>{fmt_mes(p)}</td>" + "".join(_celda_atip(p, v) for v in VARS_ATIP) + "</tr>"
    for p in atip_meses)

cajas_json = json.dumps({
    "variables": list(variables_resumen.columns),
    "unidades": [UNIDAD_RESUMEN[v] for v in variables_resumen.columns],
    "valores": {v: [[round(float(x), 2) for x in variables_resumen[v][variables_resumen.index.month == m].dropna()]
                    for m in range(1, 13)] for v in variables_resumen.columns},
    # el mes exacto de cada valor (año-mes), para que el cursor diga cuál es cada punto
    "fechas": {v: [[f"{NOMBRE_MES_COMPLETO[p.month]} de {p.year}"
                    for p in variables_resumen[v][variables_resumen.index.month == m].dropna().index]
                   for m in range(1, 13)] for v in variables_resumen.columns},
    "meses": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
}, ensure_ascii=False)

filas_resumen = "\n".join(
    f"<tr><td>{html.escape(fila)}</td>"
    + "".join(f"<td class='num'>{v:.0f}</td>" if fila == "meses válidos"
              else f"<td class='num'>{n(v, 2)}</td>" for v in tabla_resumen.loc[fila])
    + "</tr>" for fila in tabla_resumen.index)
bal_n = len(bal_completos)
bal_p_anual = bal_completos.p.mean() * 12
bal_q_anual = bal_completos.q.mean() * 12
bal_sobre1 = int((bal_completos.escorrentia > 1).sum())
bal_max = bal_completos.escorrentia.max()
bal_max_mes = bal_completos.escorrentia.idxmax()
# con PL: meses con coeficiente > 1, y cuántos vienen después de dos meses más lluviosos que lo normal
_bal_pl = pd.DataFrame({"p": red.reindex(PERIODOS), "q": balance.q}).dropna()
_bal_pl_coef = _bal_pl.q / _bal_pl.p
bal_sobre1_pl = int((_bal_pl_coef > 1).sum())
bal_max_pl, bal_max_mes_pl = _bal_pl_coef.max(), _bal_pl_coef.idxmax()
_pl_dos_antes = red.reindex(PERIODOS).rolling(2).mean().shift(1)
bal_pl_tras_lluvia = int((_pl_dos_antes.reindex(_bal_pl_coef.index[_bal_pl_coef > 1]) > red.mean()).sum())

# Firmas hidrológicas que publica CAMELS-COL (archivo 09 del registro de Zenodo). Son atributos por
# cuenca, no series: sirven para contrastar contra ellas lo que calculamos por nuestra cuenta.
firmas_sg = pd.read_csv("data/camels_col/signatures/09_CAMELS_COL_Hydrological_signatures.csv"
                        ).set_index("gauge_id").loc[24027010]


# ---------------------------------------------------------------- ciclo anual: lluvia contra caudal
# Las tres series se promedian SOLO sobre los meses en que las tres tienen dato. El caudal tiene 262 de
# los 300 meses y la lluvia los 300; si cada una usara su propia muestra, las curvas no serían
# comparables de frente. La diferencia es pequeña (el total anual de IMERG cambia de 2 224 a 2 229
# mm/año), pero la comparación así queda limpia.
MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# ---------------------------------------------------------------- el ciclo anual, mes a mes
# Para cada variable y cada mes del calendario: años con dato y estadísticos de esos años. Percentiles
# con interpolación lineal (Hyndman y Fan, tipo 7, el de pandas); desviación estándar muestral (n − 1).
MESES_LARGOS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                   "octubre", "noviembre", "diciembre"]
CICLO_VARIABLES = [("pl", "PL", "mm/mes", "PL", 0), ("pi", "PI", "mm/mes", "PI", 0),
                   ("q", "Q", "m³/s", "Q", 1), ("t", "T media", "°C", "T media", 1)]


def ciclo_estadisticos(serie):
    g = serie.groupby(serie.index.month)
    return pd.DataFrame({"n": g.count(), "media": g.mean(), "mediana": g.median(), "sd": g.std(),
                         "p10": g.quantile(0.10), "q1": g.quantile(0.25), "q3": g.quantile(0.75),
                         "p90": g.quantile(0.90)})


def ciclo_tabla_html(clave, columna, decimales):
    e = ciclo_estadisticos(variables_resumen[columna])
    fmt = lambda v: f"{v:,.{decimales}f}".replace(",", " ")
    filas = "\n".join(
        f"<tr><td>{MESES_LARGOS_ES[m - 1]}</td><td class='num'>{int(f.n)}</td>"
        + "".join(f"<td class='num'>{fmt(f[c])}</td>" for c in ("media", "mediana", "sd", "p10", "q1", "q3", "p90"))
        + "</tr>" for m, f in e.iterrows())
    return filas


ciclo_tablas = {clave: ciclo_tabla_html(clave, col, dec) for clave, _, _, col, dec in CICLO_VARIABLES}
ciclo_base = pd.DataFrame({
    "imerg": imm[imm.id_estacion == 24027010].set_index("periodo")["p_imerg_mm"],
    "red": red,
    "caudal": q_camels,
}).reindex(PERIODOS)
ciclo_comun = ciclo_base.dropna()
ciclo = ciclo_comun.groupby(ciclo_comun.index.month).mean()
ciclo["escorrentia_imerg"] = ciclo.caudal / ciclo.imerg
ciclo["escorrentia_red"] = ciclo.caudal / ciclo.red

ciclo_datos = {
    "meses": MESES_ES,
    "imerg": ciclo.imerg.round(1).tolist(),
    "red": ciclo.red.round(1).tolist(),
    "caudal": ciclo.caudal.round(1).tolist(),
    "escImerg": ciclo.escorrentia_imerg.round(3).tolist(),
    "escRed": ciclo.escorrentia_red.round(3).tolist(),
}
ciclo_json = json.dumps(ciclo_datos, ensure_ascii=False)

ciclo_n = len(ciclo_comun)


def mes_de(serie, extremo="max"):
    """Nombre del mes en que la serie del ciclo alcanza su máximo o su mínimo."""
    pos = int(serie.values.argmax() if extremo == "max" else serie.values.argmin())
    return MESES_ES[pos]


ciclo_pico_imerg = mes_de(ciclo.imerg)
ciclo_valle_imerg = mes_de(ciclo.imerg, "min")
ciclo_pico_red = mes_de(ciclo.red)
ciclo_pico_q = mes_de(ciclo.caudal)
# los dos picos de cada fuente de lluvia, uno por semestre (el régimen es bimodal)
picos_semestre = lambda s: (mes_de(s.iloc[:6]), MESES_ES[6 + int(s.iloc[6:].values.argmax())])
ciclo_picos_imerg, ciclo_picos_red = picos_semestre(ciclo.imerg), picos_semestre(ciclo.red)
ciclo_meses_red_mayor = int((ciclo.red > ciclo.imerg).sum())
ciclo_valle_q = mes_de(ciclo.caudal, "min")
ciclo_esc_min_mes, ciclo_esc_max_mes = mes_de(ciclo.escorrentia_imerg, "min"), mes_de(ciclo.escorrentia_imerg)
ciclo_esc_min = ciclo.escorrentia_imerg.min()
ciclo_esc_max = ciclo.escorrentia_imerg.max()

# ---------------------------------------------------------------- régimen del ciclo anual
# El mismo cálculo de la sección 1.9 del notebook. Mediana de cada mes del calendario; mes típico = promedio de
# las 12 medianas; mes húmedo si su mediana lo supera. Concentración: % de la suma de las medianas en los
# meses húmedos. Q va en mm/mes en todo el régimen (volumen por área, misma unidad que PL y PI). Forma: armónicos 1 y 2 (Horn y Bryson, 1960); los
# picos se cuentan sobre la curva ajustada. Estacionalidad: Kruskal-Wallis entre los 12 meses (Kruskal y
# Wallis, 1952). Clasificación: débil si p >= ALFA_KW; si no, bimodal con dos picos; si no, unimodal.
ALFA_KW = 0.05
REG_PASOS = 1200
_reg_t = np.arange(12)


def _reg_medianas(serie):
    return serie.groupby(serie.index.month).median().reindex(range(1, 13)).to_numpy()


def _reg_armonico(x, k):
    return (2 / 12 * np.sum(x * np.cos(2 * np.pi * k * _reg_t / 12)),
            2 / 12 * np.sum(x * np.sin(2 * np.pi * k * _reg_t / 12)))


def _reg_curva(x, t):
    y = np.full(len(t), x.mean())
    for k in (1, 2):
        a, b = _reg_armonico(x, k)
        y += a * np.cos(2 * np.pi * k * t / 12) + b * np.sin(2 * np.pi * k * t / 12)
    return y


def _reg_rachas(es_humedo):
    """Rachas circulares de meses con el mismo estado: [(primer mes 0-11, duración, húmedo)]."""
    if es_humedo.all() or (~es_humedo).all():
        return [(0, 12, bool(es_humedo[0]))]
    inicio = next(m for m in range(12) if es_humedo[m] != es_humedo[m - 1])
    rachas = []
    for m in [(inicio + i) % 12 for i in range(12)]:
        if rachas and es_humedo[m] == rachas[-1][2]:
            rachas[-1][1] += 1
        else:
            rachas.append([m, 1, bool(es_humedo[m])])
    return rachas


def _reg_nombre(m, d):
    meses = MESES_LARGOS_ES[m] if d == 1 else f"{MESES_LARGOS_ES[m]} a {MESES_LARGOS_ES[(m + d - 1) % 12]}"
    return f"{meses} ({d} {'mes' if d == 1 else 'meses'})"


_reg_q_mm = variables_resumen["Q"] * variables_resumen.index.days_in_month * 86400 / (AREA_SG_KM2 * 1e6) * 1000
REG_SERIES = {"PL": (variables_resumen["PL"], variables_resumen["PL"], "mm/mes"),
              "PI": (variables_resumen["PI"], variables_resumen["PI"], "mm/mes"),
              "Q": (_reg_q_mm, _reg_q_mm, "mm/mes")}
regimen = {}
for _n, (_s, _s_conc, _u) in REG_SERIES.items():
    _med = _reg_medianas(_s)
    _tipico = _med.mean()
    _rachas = _reg_rachas(_med > _tipico)
    _mc = _reg_medianas(_s_conc)
    _hc = _mc > _mc.mean()
    _amp = {k: np.hypot(*_reg_armonico(_med, k)) for k in (1, 2)}
    _ta = np.arange(REG_PASOS) * 12 / REG_PASOS
    _ya = _reg_curva(_med, _ta)
    _picos = _ta[(_ya > np.roll(_ya, 1)) & (_ya > np.roll(_ya, -1))]
    _kw = stats.kruskal(*[_s[_s.index.month == m].dropna() for m in range(1, 13)])
    regimen[_n] = {
        "unidad": _u, "medianas": _med, "tipico": _tipico,
        "max": MESES_LARGOS_ES[int(np.argmax(_med))], "min": MESES_LARGOS_ES[int(np.argmin(_med))],
        "amp": _med.max() - _med.min(), "amp_rel": (_med.max() - _med.min()) / _tipico * 100,
        "humedas": [_reg_nombre(m, d) for m, d, h in _rachas if h],
        "secas": [_reg_nombre(m, d) for m, d, h in _rachas if not h],
        "conc": _mc[_hc].sum() / _mc.sum() * 100, "conc_meses": int(_hc.sum()),
        "a2a1": _amp[2] / _amp[1],
        "var1": _amp[1] ** 2 / 2 / _med.var(ddof=0) * 100, "var2": _amp[2] ** 2 / 2 / _med.var(ddof=0) * 100,
        "picos": [MESES_LARGOS_ES[int(round(p)) % 12] for p in _picos],
        "kw_p": _kw.pvalue,
        "clase": "estacionalidad débil" if _kw.pvalue >= ALFA_KW else ("bimodal" if len(_picos) == 2 else "unimodal"),
    }
reg_clases = sorted({r["clase"] for r in regimen.values()})
reg_kw_max = max(r["kw_p"] for r in regimen.values())
_reg_indicadores = [
    ("Máximo", lambda r: r["max"]), ("Mínimo", lambda r: r["min"]),
    ("Amplitud (% del mes típico)", lambda r: f"{r['amp']:.1f} {r['unidad']} ({r['amp_rel']:.0f} %)"),
    ("Temporadas húmedas", lambda r: "; ".join(r["humedas"])),
    ("Temporadas secas", lambda r: "; ".join(r["secas"])),
    ("Concentración en los meses húmedos", lambda r: f"{r['conc']:.1f} % en {r['conc_meses']} meses"),
    ("A₂/A₁", lambda r: f"{r['a2a1']:.2f}"),
    ("Varianza que explican A₁ · A₂", lambda r: f"{r['var1']:.0f} % · {r['var2']:.0f} %"),
    ("Picos de la curva", lambda r: f"{len(r['picos'])} ({' y '.join(r['picos'])})"),
    ("Kruskal-Wallis <i>p</i>", lambda r: f"{r['kw_p']:.0e}"),
    ("Régimen", lambda r: f"<b>{r['clase']}</b>"),
]
reg_filas = "\n".join(f"<tr><td>{nombre}</td>" + "".join(f"<td>{f(r)}</td>" for r in regimen.values()) + "</tr>"
                      for nombre, f in _reg_indicadores)

# ---------------------------------------------------------------- desfase estacional (sección 1.10 del notebook)
# Fase del armónico de 6 meses de PL, PI y Q (Q en mm/mes), sobre las mismas medianas del régimen: el desfase
# es cuánto después llega el máximo de Q que el de la lluvia. Incertidumbre: bootstrap por bloques de un año.
DES_DIAS_POR_MES = 365.25 / 12
DES_REMUESTREOS = 2000
DES_SEMILLA = 1
_des_series = pd.DataFrame({"PL": variables_resumen["PL"], "PI": variables_resumen["PI"], "Q": _reg_q_mm})


def _des_fase(x):
    a, b = _reg_armonico(x, 2)
    return (np.arctan2(b, a) / (2 * np.pi) * 6) % 6


def _des_circular(t1, t0):
    return (t1 - t0 + 3) % 6 - 3


def _des_desfases(tabla):
    f = {c: _des_fase(_reg_medianas(tabla[c])) for c in tabla}
    d = {"Q_PL": _des_circular(f["Q"], f["PL"]) * DES_DIAS_POR_MES,
         "Q_PI": _des_circular(f["Q"], f["PI"]) * DES_DIAS_POR_MES,
         "PI_PL": _des_circular(f["PI"], f["PL"]) * DES_DIAS_POR_MES}
    return d   # la diferencia entre fuentes, (Q − PL) − (Q − PI), es por construcción PI_PL


desfase = _des_desfases(_des_series)
_des_rng = np.random.default_rng(DES_SEMILLA)
_des_anios = np.unique(_des_series.index.year)
_des_por_anio = {a: _des_series[_des_series.index.year == a] for a in _des_anios}
_des_boot = pd.DataFrame([_des_desfases(pd.concat([_des_por_anio[a] for a in
                                                    _des_rng.choice(_des_anios, len(_des_anios), replace=True)]))
                          for _ in range(DES_REMUESTREOS)])
desfase_ic = {k: (_des_boot[k].quantile(0.025), _des_boot[k].quantile(0.975)) for k in desfase}
desfase_dif_concluyente = not (desfase_ic["PI_PL"][0] <= 0 <= desfase_ic["PI_PL"][1])
_des_tc = pd.read_csv("out/tiempos_concentracion.csv").con_pendiente_medida_h
desfase_tc = (_des_tc.min(), _des_tc.max())
# el texto dice que el desfase es mucho mayor que el tiempo de concentración: si deja de serlo, se detiene
assert min(desfase["Q_PL"], desfase["Q_PI"]) * 24 > 10 * desfase_tc[1]

# ---------------------------------------------------------------- PI contra PL, mes a mes (Punto 2)
# Correlación no es concordancia: dos series pueden subir y bajar juntas y aun así diferir en cantidad.
# Errores de PI con PL como referencia, en los meses en que las dos tienen dato.
_p2 = comp[["IMERG", "RED"]].dropna()
_p2_err = _p2.IMERG - _p2.RED
p2_pipl = {"n": len(_p2), "sesgo": _p2_err.mean(), "mae": _p2_err.abs().mean(),
           "rmse": float(np.sqrt((_p2_err ** 2).mean())), "debajo_pct": (_p2_err < 0).mean() * 100}
assert p2_pipl["mae"] > 1.5 * abs(p2_pipl["sesgo"])
p2_pipl_json = json.dumps({"pi": _p2.IMERG.round(1).tolist(), "pl": _p2.RED.round(1).tolist(),
                           "mes": [p.month for p in _p2.index], "periodo": [str(p) for p in _p2.index]})


# ---------------------------------------------------------------- lluvia contra caudal: cómo cambia la dispersión
# Residuos de un ajuste lineal de Q (m³/s) contra la lluvia; razón entre la varianza de los residuos en el
# tercio de meses más lluviosos y en el tercio más seco. Mayor que P2_RAZON_VARIANZA: la dispersión crece.
P2_RAZON_VARIANZA = 1.5


def _p2_razon_dispersion(lluvia, caudal):
    par = pd.concat([lluvia.rename("x"), caudal.rename("y")], axis=1).dropna().sort_values("x")
    residuo = par.y - np.polyval(np.polyfit(par.x, par.y, 1), par.x)
    tercios = np.array_split(residuo.to_numpy(), 3)
    return float(np.var(tercios[-1], ddof=1) / np.var(tercios[0], ddof=1))


p2_dispersion = {f: _p2_razon_dispersion(variables_resumen[f], variables_resumen["Q"]) for f in ("PL", "PI")}
assert all(v > P2_RAZON_VARIANZA for v in p2_dispersion.values())   # el texto dice que la dispersión crece


# ---------------------------------------------------------------- estimación fuera del período de ajuste (Punto 2)
# Los modelos se ajustan con 1998-2014 y se evalúan con 2015-2022, en bloques continuos para no mezclar
# meses vecinos (que se parecen entre sí) entre el ajuste y la evaluación. Q en m³/s. La referencia es la
# climatología mensual de Q del bloque de ajuste: superarla quiere decir que la lluvia aporta algo más que
# el calendario. Sesgo = estimado − observado.
EV_AJUSTE, EV_VALIDACION = ("1998-01", "2014-12"), ("2015-01", "2022-12")
_ev = pd.read_csv("out/variables_mensuales.csv", index_col=0)[["PI", "PL", "Q"]]
_ev.index = pd.PeriodIndex(_ev.index, freq="M")
_ev = _ev.reindex(PERIODOS)
_ev["Q"] = _ev.Q * AREA_SG_KM2 * 1000 / (_ev.index.days_in_month * 86400)        # mm/mes -> m³/s
_ev_aj, _ev_val = _ev.loc[EV_AJUSTE[0]:EV_AJUSTE[1]], _ev.loc[EV_VALIDACION[0]:EV_VALIDACION[1]]


def _ev_metricas(observado, estimado):
    par = pd.concat([observado.rename("o"), estimado.rename("e")], axis=1).dropna()
    err = par.e - par.o
    return {"n": len(par), "sesgo": err.mean(), "mae": err.abs().mean(), "rmse": float(np.sqrt((err ** 2).mean())),
            "negativas": int((par.e < 0).sum())}


def _ev_ols(x, y, rezago=0):
    muestra = pd.concat([_ev_aj[x].shift(rezago).rename("x"), _ev_aj[y].rename("y")], axis=1).dropna()
    pendiente, intercepto = np.polyfit(muestra.x, muestra.y, 1)
    return intercepto + pendiente * _ev[x].shift(rezago), pendiente


_ev_clima = _ev_aj.groupby(_ev_aj.index.month).Q.mean()
ev_estimados = {"climatología mensual de Q": pd.Series([_ev_clima[p.month] for p in _ev.index], index=_ev.index)}
ev_pendientes = {}
for _f in ("PL", "PI"):
    for _r, _nombre in ((0, f"{_f} del mismo mes"), (1, f"{_f} del mes anterior")):
        ev_estimados[_nombre], ev_pendientes[_nombre] = _ev_ols(_f, "Q", _r)
ev_tabla = {m: {"ajuste": _ev_metricas(_ev_aj.Q, e.loc[_ev_aj.index]), "validacion": _ev_metricas(_ev_val.Q, e.loc[_ev_val.index])}
            for m, e in ev_estimados.items()}
ev_mejor = min((m for m in ev_tabla if m != "climatología mensual de Q"), key=lambda m: ev_tabla[m]["validacion"]["rmse"])
ev_rmse_clima = ev_tabla["climatología mensual de Q"]["validacion"]["rmse"]
ev_filas = "\n".join(
    f"<tr><td>{'<b>' + m + '</b>' if m == ev_mejor else m}</td><td class='num'>{t['ajuste']['rmse']:.1f}</td>"
    f"<td class='num'>{t['validacion']['rmse']:.1f}</td><td class='num'>{t['validacion']['mae']:.1f}</td>"
    f"<td class='num'>{t['validacion']['sesgo']:+.1f}</td><td class='num'>{t['validacion']['n']}</td></tr>"
    for m, t in ev_tabla.items())
# ¿sirve corregir PI con una regresión contra PL? (el proyecto decidió no corregirla)
_ev_pl_ols, _ = _ev_ols("PI", "PL")
ev_correccion = {"ols": _ev_metricas(_ev_val.PL, _ev_pl_ols.loc[_ev_val.index]),
                 "sin": _ev_metricas(_ev_val.PL, _ev_val.PI)}
ev_json = json.dumps({"meses": [str(p) for p in _ev_val.index], "q": _ev_val.Q.round(2).tolist(),
                      **{k: ev_estimados[m].loc[_ev_val.index].round(2).tolist() for k, m in
                         (("clima", "climatología mensual de Q"), ("pl", "PL del mismo mes"), ("pi", "PI del mismo mes"))}},
                     default=lambda v: None).replace("NaN", "null")
assert all(t["validacion"]["negativas"] == 0 for t in ev_tabla.values())   # el texto dice que no hay estimados negativos
# el texto dice que corregir PI «casi no gana nada»: menos de un 10 % de mejora en el RMSE
assert ev_correccion["ols"]["rmse"] > 0.9 * ev_correccion["sin"]["rmse"]

# cuánto se multiplica el coeficiente entre el mes más bajo y el más alto, con cada fuente de lluvia
ciclo_esc_razon_imerg = ciclo_esc_max / ciclo_esc_min
ciclo_esc_razon_red = ciclo.escorrentia_red.max() / ciclo.escorrentia_red.min()
ciclo_esc_max_red = ciclo.escorrentia_red.max()
ciclo_esc_max_mes_red = mes_de(ciclo.escorrentia_red)
ciclo_esc_min_red = ciclo.escorrentia_red.min()
ciclo_esc_min_mes_red = mes_de(ciclo.escorrentia_red, "min")
# los dos picos de lluvia del régimen bimodal, para poder decir cuál manda
ciclo_pico1 = ciclo.imerg.iloc[2:6].max()          # mar-jun
ciclo_pico2 = ciclo.imerg.iloc[8:12].max()         # sep-dic
ciclo_q_pico1 = ciclo.caudal.iloc[2:6].max()
ciclo_q_pico2 = ciclo.caudal.iloc[8:12].max()
ciclo_amplifica = ciclo_q_pico2 / ciclo_q_pico1 - 1
ciclo_lluvia_igual = abs(ciclo_pico2 / ciclo_pico1 - 1)


# ---------------------------------------------------------------- las dos fuentes de temperatura
# MSWX (llega dentro de CAMELS-COL) contra ERA5-Land (bajado aparte). CAMELS-COL solo trae t_min y
# t_max de MSWX, así que la media diaria se arma como (min + max) / 2; ERA5-Land sí publica la media
# directamente. Se comparan sobre los días en que las dos existen.
DIAS_T = pd.date_range(f"{min(ANIOS_ESTUDIO)}-01-01", f"{max(ANIOS_ESTUDIO)}-12-31", freq="D")
_era_dia = pd.read_csv("out/era5land_temperatura_diaria_fonce.csv",
                       parse_dates=["fecha"]).set_index("fecha").reindex(DIAS_T)
temp = pd.DataFrame({
    "mswx_media": ((cam["t_min"] + cam["t_max"]) / 2).reindex(DIAS_T),
    "mswx_min": cam["t_min"].reindex(DIAS_T), "mswx_max": cam["t_max"].reindex(DIAS_T),
    "era_media": _era_dia["t_media"], "era_min": _era_dia["t_min"], "era_max": _era_dia["t_max"],
})
t_dias_mswx = int(temp.mswx_media.notna().sum())
t_dias_era = int(temp.era_media.notna().sum())
tc = temp.dropna()                                   # días con las dos fuentes
t_n = len(tc)

CUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
t_cuantiles = pd.DataFrame({"MSWX": tc.mswx_media.quantile(CUANTILES).values,
                            "ERA5-Land": tc.era_media.quantile(CUANTILES).values},
                           index=[f"p{int(q * 100)}" for q in CUANTILES])
t_cuantiles["dif"] = t_cuantiles.MSWX - t_cuantiles["ERA5-Land"]

# ciclo anual con la mediana y dos bandas de cuantiles, para no resumirlo todo en la media
_g = tc.groupby(tc.index.month)
t_ciclo = {}
for fuente, col in [("mswx", "mswx_media"), ("era", "era_media")]:
    for etiqueta, q in [("p10", 0.10), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p90", 0.90)]:
        t_ciclo[f"{fuente}_{etiqueta}"] = _g[col].quantile(q).round(2).tolist()

t_json = json.dumps({"meses": MESES_ES, "ciclo": t_ciclo}, ensure_ascii=False)

# ---------------------------------------------------------------- ETP: la de CAMELS-COL y Hargreaves recalculado
# 06b_etp_hargreaves.py aplica la fórmula que declara CAMELS-COL (Hargreaves y Samani, 1985, con Ra de
# FAO-56) con la temperatura de MSWX y con la de ERA5-Land. Aquí se pasan a mensual y se comparan.
_etp_d = pd.read_csv("out/etp_hargreaves_fonce.csv", parse_dates=["fecha"]).set_index("fecha")
etp_m = pd.DataFrame({k: a_mensual(_etp_d[c], "sum") for k, c in
                      (("camels", "etp_camels"), ("mswx", "etp_mswx"), ("era", "etp_era5land"))})
etp_comun = etp_m.dropna()                         # meses en que las tres tienen dato
etp_anual = etp_comun.mean() * 12
etp_cociente = etp_comun.camels / etp_comun.mswx
etp_cociente_mj = (etp_comun.camels / (etp_comun.mswx / 0.408)).median()   # si Ra se hubiera dejado en MJ
etp_r_camels_mswx = etp_comun.camels.corr(etp_comun.mswx)
etp_era_vs_mswx = (etp_comun.era / etp_comun.mswx).mean() * 100 - 100
etp_r_era_mswx = etp_comun.era.corr(etp_comun.mswx)
_etp_pq = pd.DataFrame({"pl": red.reindex(PERIODOS), "q": q_camels}).reindex(etp_comun.index).dropna()
etp_pl_anual = _etp_pq.pl.mean() * 12
etp_pl_menos_q = (_etp_pq.pl - _etp_pq.q).mean() * 12
_etp_cuencas = gpd.read_file("out/shp_fonce/cuencas_fonce.shp")
# la Ra que CAMELS-COL habría tenido que usar para obtener su ETP con la fórmula que declara
_etp_t = cam[["t_min", "t_max"]].reindex(_etp_d.index)
_etp_ok = _etp_d.etp_camels.notna() & (_etp_t.t_max > _etp_t.t_min)
etp_ra_implicita = (_etp_d.etp_camels[_etp_ok] / (0.0023 * ((_etp_t.t_max + _etp_t.t_min) / 2 + 17.8)[_etp_ok]
                                                  * np.sqrt((_etp_t.t_max - _etp_t.t_min)[_etp_ok])))
etp_ra_max = float(_etp_d.ra_mm.max())
etp_ra_cociente_mes = (etp_ra_implicita.groupby(etp_ra_implicita.index.month).mean()
                       / _etp_d.ra_mm[_etp_ok].groupby(etp_ra_implicita.index.month).mean())
etp_lat = float(_etp_cuencas[_etp_cuencas.gauge_id == 24027010].to_crs(3116).centroid.to_crs(4326).y.iloc[0])
_etp_ciclo = etp_comun.groupby(etp_comun.index.month).mean()
_etp_pq_ciclo = (_etp_pq.pl - _etp_pq.q).groupby(_etp_pq.index.month).mean()
# ---------------------------------------------------------------- P − Q contra la ETP
# P − Q = ET + ΔS (+ otros intercambios): no es la evapotranspiración. Mes a mes pesa el almacenamiento; en
# totales anuales casi se cancela. Se hace con PL (manda) y con PI, contra la ETP de Hargreaves con ERA5-Land.
pq = pd.DataFrame({"pl": red.reindex(PERIODOS), "pi": comp["IMERG"].reindex(PERIODOS),
                   "q": q_camels.reindex(PERIODOS), "etp": etp_m["era"].reindex(PERIODOS)})
pq["pl_q"], pq["pi_q"] = pq.pl - pq.q, pq.pi - pq.q
_pq_meses_q = pq.q.notna().groupby(pq.index.year).sum()
pq_anual = pq.groupby(pq.index.year).sum(min_count=12).loc[_pq_meses_q.index[_pq_meses_q == 12]]
_pq_con_q = pq.dropna(subset=["q"])
pq_res = {f: {"sobre_etp": int((_pq_con_q[f"{f}_q"] > _pq_con_q.etp).sum()),
              "negativo": int((_pq_con_q[f"{f}_q"] < 0).sum()),
              "anual": pq_anual[f"{f}_q"].mean(),
              "anios_sobre_etp": int((pq_anual[f"{f}_q"] > pq_anual.etp).sum())} for f in ("pl", "pi")}
pq_n_meses, pq_n_anios, pq_etp_anual = len(_pq_con_q), len(pq_anual), pq_anual.etp.mean()
pq_anios_sobre = {f: [str(x) for x in pq_anual.index[pq_anual[f"{f}_q"] > pq_anual.etp]] for f in ("pl", "pi")}
# la estación más seca de la red (en la serie depurada); cuando falta, PL se arma con estaciones más lluviosas
pq_seca = plu[DENTRO].mean().idxmin()
pq_seca_nombre = cat_plu.loc[pq_seca, "etiqueta"]
pq_falta_seca = {a: int(plu.loc[plu.index.year == int(a), pq_seca].isna().sum()) for a in pq_anios_sobre["pl"]}
_lista_y = lambda l: ", ".join(l[:-1]) + " y " + l[-1] if len(l) > 1 else (l[0] if l else "")


def prueba_recarga(lluvia, caudal):
    """Caudal de ene-mar de cada año contra su propia lluvia (recta), y el residuo contra la lluvia de
    sep-nov del año anterior: si la cuenca guarda agua entre temporadas, el residuo crece con ella."""
    filas = []
    for anio in range(1999, 2023):
        secos = (caudal.index.year == anio) & caudal.index.month.isin([1, 2, 3])
        if caudal[secos].notna().sum() < 3:
            continue
        antes = (lluvia.index.year == anio - 1) & lluvia.index.month.isin([9, 10, 11])
        filas.append((anio, caudal[secos].sum(), lluvia[secos].sum(), lluvia[antes].sum()))
    tabla = pd.DataFrame(filas, columns=["anio", "q", "p", "p_sep_nov_antes"]).set_index("anio")
    recta = stats.linregress(tabla.p, tabla.q)
    tabla["residuo"] = tabla.q - (recta.intercept + recta.slope * tabla.p)
    return tabla, stats.spearmanr(tabla.p_sep_nov_antes, tabla.residuo)


# ¿fue recarga? (solo tiene sentido para el primer año con P − Q > ETP que tenga ene-mar siguiente completo)
rec = {f: prueba_recarga(pq[f], pq.q) for f in ("pl", "pi")}
_rec_anio = next((int(a) for a in pq_anios_sobre["pl"] if int(a) + 1 in rec["pl"][0].index), None)
_pi_anual = pq.pi.groupby(pq.index.year).sum()
pq_recarga = "" if _rec_anio is None else (
    f"""<p><b>¿Fue recarga?</b> Si un año recarga, en la temporada seca siguiente (enero a marzo) el río trae más
  caudal del que explica su lluvia. Con PI se ve claro: ese exceso crece con la lluvia de septiembre a
  noviembre anterior (ρ = {rec['pi'][1].statistic:.2f}, p = {rec['pi'][1].pvalue:.3f}); con PL va en el mismo sentido,
  sin ser significativo (ρ = {rec['pl'][1].statistic:.2f}, p = {rec['pl'][1].pvalue:.2f}). Pero después de {_rec_anio} el río trajo
  {"menos" if rec['pl'][0].residuo[_rec_anio + 1] < 0 else "más"} de lo esperado
  ({rec['pl'][0].residuo[_rec_anio + 1]:+.0f} mm con PL), y PI {"no ve" if _pi_anual[_rec_anio] < _pi_anual.mean() else "sí ve"}
  {_rec_anio} como un año lluvioso. {"La recarga no explica ese año; apunta más a la lluvia sobrestimada." if rec['pl'][0].residuo[_rec_anio + 1] < 0 and _pi_anual[_rec_anio] < _pi_anual.mean() else ""}</p>""")
pq_explicaciones = f"""<ul class="tratamiento">
    <li><b>Quedarse guardada:</b> recargar el suelo o el acuífero y salir por el río meses o años después.</li>
    <li><b>Salir sin pasar por la estación:</b> por flujo subterráneo profundo, o por captaciones de acueductos y
    riego que no vuelven al río.</li>
    <li><b>Evaporarse más de lo que dice la ETP:</b> la de Hargreaves es la de un pasto de referencia y un
    bosque puede superarla; además es una estimación, no una medida.</li>
    <li><b>No haber existido:</b> lluvia sobrestimada o caudal subestimado. Para PL hay una causa conocida: en
    esos años le falta {pq_seca_nombre}, la estación más seca, en {_lista_y([f"{k} meses de {a}" for a, k in pq_falta_seca.items()])},
    y sin ella PL queda alta (el sesgo de cobertura de «Anomalías en las series»).</li>
  </ul>
  <p class="nota">Ninguna de las cuatro está comprobada.</p>
  {pq_recarga}"""
_pq_ciclo = (_pq_con_q.groupby(_pq_con_q.index.month).pl_q.mean() - _pq_con_q.groupby(_pq_con_q.index.month).etp.mean())
pq_meses_guarda = [MESES_ES[m - 1] for m in _pq_ciclo.index[_pq_ciclo > 0]]
_red1 = lambda s: [None if pd.isna(v) else round(float(v), 1) for v in s]
pq_json = json.dumps({"meses": [f"{p}-01" for p in pq.index], "pl_q": _red1(pq.pl_q), "pi_q": _red1(pq.pi_q),
                      "etp": _red1(pq.etp), "anios": [str(a) for a in pq_anual.index],
                      "pl_q_anual": _red1(pq_anual.pl_q), "pi_q_anual": _red1(pq_anual.pi_q),
                      "etp_anual": _red1(pq_anual.etp)}, ensure_ascii=False)

etp_json = json.dumps({"meses": MESES_ES, **{k: _etp_ciclo[k].round(1).tolist() for k in etp_comun},
                       "pl_q": _etp_pq_ciclo.round(1).tolist()}, ensure_ascii=False)

t_sesgo_media = tc.mswx_media.mean() - tc.era_media.mean()
t_sesgo_p5 = float(t_cuantiles.loc["p5", "dif"])
t_sesgo_p95 = float(t_cuantiles.loc["p95", "dif"])
t_r = float(np.corrcoef(tc.mswx_media, tc.era_media)[0, 1])
t_amp_mswx = float((tc.mswx_max - tc.mswx_min).mean())
t_amp_era = float((tc.era_max - tc.era_min).mean())
t_iqr_mswx = float(tc.mswx_media.quantile(0.75) - tc.mswx_media.quantile(0.25))
t_iqr_era = float(tc.era_media.quantile(0.75) - tc.era_media.quantile(0.25))
t_ciclo_amp_mswx = max(t_ciclo["mswx_p50"]) - min(t_ciclo["mswx_p50"])
t_ciclo_amp_era = max(t_ciclo["era_p50"]) - min(t_ciclo["era_p50"])
# Cuánto se equivoca el punto medio (min + max) / 2 frente a la media real de 24 h. Solo se puede medir
# en ERA5-Land, que trae las dos cosas; es la aproximación a la que obliga MSWX dentro de CAMELS-COL.
t_sesgo_metodo = float(((temp.era_min + temp.era_max) / 2 - temp.era_media).mean())

# gradiente térmico de ERA5-Land contra el DEM: sirve para juzgar si el reanálisis representa bien el
# relieve. La malla de MSWX no está disponible (llega ya promediada por cuenca), así que no se le puede
# hacer la misma prueba; eso mismo es parte de la comparación.
t_grad = pd.read_csv("out/gradiente_termico_era5land.csv")
# todas las celdas que tocan la cuenca, ponderadas por su fracción dentro (mismo criterio que IMERG)
t_grad_nucleo = t_grad
_w, _x, _y = t_grad.frac_dentro.values, t_grad.altitud_media_m.values, t_grad.t_media.values
_b, _a = np.polyfit(_x, _y, 1, w=np.sqrt(_w))            # polyfit pondera los residuos, de ahí la raíz
_mx, _my = np.average(_x, weights=_w), np.average(_y, weights=_w)
_r_t = np.sum(_w * (_x - _mx) * (_y - _my)) / np.sqrt(np.sum(_w * (_x - _mx) ** 2) * np.sum(_w * (_y - _my) ** 2))
t_grad_por_km = _b * 1000
t_grad_r2 = float(_r_t) ** 2
GRADIENTE_FISICO = -6.5      # °C/km, valor de referencia del gradiente ambiental en aire húmedo


# ---------------------------------------------------------------- cómo se relacionan las variables
# Las siete variables mensuales cruzadas todas contra todas. Se usa **solo Spearman**, la correlación
# sobre los rangos: no supone que la relación sea una recta y no se deja arrastrar por unos pocos meses
# extremos, que es lo prudente con variables meteorológicas. En estos datos da casi lo mismo que Pearson
# —la diferencia mayor entre las dos es de 0,08— así que elegir la robusta no cuesta nada.
# Requiere haber corrido antes scripts/16_correlaciones_variables.py.
corr_vars = pd.read_csv("out/variables_mensuales.csv", index_col=0)
corr_vars.index = pd.PeriodIndex(corr_vars.index, freq="M")
corr_anom = corr_vars - corr_vars.groupby(corr_vars.index.month).transform("mean")
VARIABLES_CORR = list(corr_vars.columns)
UNIDAD_VAR = {"PI": "mm/mes", "PL": "mm/mes", "Q": "mm/mes",
              "ETP": "mm/mes", "T MSWX": "°C", "T ERA5": "°C"}

corr_spearman = pd.read_csv("out/correlaciones_spearman.csv", index_col=0)
corr_spearman_anom = pd.read_csv("out/correlaciones_spearman_anomalias.csv", index_col=0)
corr_pearson = pd.read_csv("out/correlaciones_pearson.csv", index_col=0)
# con un mes de rezago (16_correlaciones_variables.py): fila en el mes t+1, columna en el mes t
corr_rezago = pd.read_csv("out/correlaciones_spearman_rezago1.csv", index_col=0)
_completo = corr_vars.reindex(PERIODOS)
corr_n_rezago = int((_completo.notna().all(axis=1) & _completo.shift(-1).notna().all(axis=1)).sum())


# ¿responde Q a la lluvia con rezago? correlación cruzada y aporte de la lluvia del mes anterior
cruzada = pd.read_csv("out/correlacion_cruzada_lluvia_caudal.csv")
memoria = pd.read_csv("out/memoria_lluvia_caudal.csv").set_index("lluvia")


def rho_cruzada(lluvia, k, series="anomalías"):
    fila = cruzada[(cruzada.lluvia == lluvia) & (cruzada.series == series) & (cruzada.rezago_meses == k)]
    return float(fila.rho.iloc[0])


# el año típico de la lluvia y del caudal, y el ciclo de Q reconstruido con la lluvia (16_correlaciones_variables.py)
ciclo_lq = pd.read_csv("out/ciclo_lluvia_caudal.csv").set_index("mes")
ajuste_lq = pd.read_csv("out/ajuste_ciclo_lluvia_caudal.csv").set_index(["lluvia", "modelo"])
NOMBRE_MES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio",
              8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}


def picos(serie):
    """Mes del máximo en cada mitad del año (el régimen es bimodal)."""
    return NOMBRE_MES[int(serie.loc[1:6].idxmax())], NOMBRE_MES[int(serie.loc[7:12].idxmax())]


pico_pl, pico_q = picos(ciclo_lq.PL), picos(ciclo_lq.Q)
_c = ajuste_lq.loc[("PL", "mes_y_anterior")]
peso_mes_pl = _c.coef_mes / (_c.coef_mes + _c.coef_mes_anterior)      # parte que viene del mismo mes
ciclo_lq_json = json.dumps({
    "meses": MESES_ES,
    "PL": ciclo_lq.PL.round(1).tolist(), "Q": ciclo_lq.Q.round(1).tolist(),
    "ajusteMes": ciclo_lq.Q_ajuste_PL_mes.round(1).tolist(),
    "ajusteMesAnterior": ciclo_lq.Q_ajuste_PL_mes_y_anterior.round(1).tolist(),
}, ensure_ascii=False)



def rho_rezago(antes, despues):
    """Spearman entre `antes` en el mes t y `despues` en el mes t+1."""
    return float(corr_rezago.loc[despues, antes])


corr_json = json.dumps({
    "variables": VARIABLES_CORR,
    "unidades": [UNIDAD_VAR[v] for v in VARIABLES_CORR],
    "crudas": {v: corr_vars[v].round(2).tolist() for v in VARIABLES_CORR},
    "anomalias": {v: corr_anom[v].round(2).tolist() for v in VARIABLES_CORR},
    "rhoCrudas": corr_spearman.round(3).values.tolist(),
    "rhoAnomalias": corr_spearman_anom.round(3).values.tolist(),
    "rhoRezago": corr_rezago.round(3).values.tolist(),
    "meses": [str(p) for p in corr_vars.index],
}, ensure_ascii=False)

corr_n = len(corr_vars)
# la mayor distancia entre Pearson y Spearman en toda la matriz, para justificar quedarse con una sola
_dif = (corr_pearson - corr_spearman).abs().values
corr_dif_max = float(_dif[~np.eye(len(VARIABLES_CORR), dtype=bool)].max())


def rho(a, b, anomalias=False):
    m = corr_spearman_anom if anomalias else corr_spearman
    return float(m.loc[a, b])


# cuánto se refuerzan las relaciones con la temperatura al quitar el ciclo anual
corr_saltos = sorted(
    (("PI", "T MSWX"), ("PL", "T MSWX"), ("PI", "ETP"), ("Q", "T ERA5")),
    key=lambda par: abs(rho(*par, anomalias=True)) - abs(rho(*par)), reverse=True)
corr_par_salto = corr_saltos[0]

# Por qué se refuerzan: se mira cuánto pesa el ciclo anual en cada variable (fracción de la varianza
# mensual que explican las 12 medias mensuales) y si los ciclos de lluvia y temperatura tienen relación
# entre sí (Spearman sobre las 12 medias). Si el ciclo de la lluvia es grande y no tiene contraparte en
# la temperatura, en las series tal cual diluye la relación que aparece en las anomalías.
corr_ciclo = corr_vars.groupby(corr_vars.index.month).mean()
corr_ciclo_rho = corr_ciclo.corr(method="spearman")
corr_peso_ciclo = (corr_vars.groupby(corr_vars.index.month).transform("mean").var()
                   / corr_vars.var() * 100)
corr_tambien = " y ".join(f"{x} con {y}, de {rho(x, y):.2f} a {rho(x, y, anomalias=True):.2f}"
                           for x, y in corr_saltos[1:3])
PARES_CICLO = [("PI", "T ERA5"), ("PL", "T ERA5"), ("Q", "T ERA5"), ("PI", "ETP"), ("PL", "T MSWX"),
               ("Q", "ETP"), ("PL", "Q")]
filas_ciclo = "\n".join(
    f"<tr><td>{a} – {b}</td><td class='num'>{corr_ciclo_rho.loc[a, b]:+.2f}</td>"
    f"<td class='num'>{rho(a, b):+.2f}</td><td class='num'>{rho(a, b, anomalias=True):+.2f}</td></tr>"
    for a, b in PARES_CICLO)


# ---------------------------------------------------------------- control de calidad de los datos
# Una fila por fuente, un color por mes. Para las series que vienen en paso diario el color es el
# porcentaje de días del mes con registro, y el detalle dice cuántos días faltan y cuántos de ellos son
# consecutivos: un mes al que le faltan cuatro días sueltos no es lo mismo que uno al que le falta una
# semana seguida, aunque la regla del proyecto acepte al primero y rechace al segundo.
periodos = PERIODOS
DIAS = pd.date_range(f"{min(ANIOS_ESTUDIO)}-01-01", f"{max(ANIOS_ESTUDIO)}-12-31", freq="D")


def racha_mas_larga(faltan):
    """Longitud de la racha más larga de días faltantes dentro del mes."""
    mejor = actual = 0
    for sin_dato in faltan:
        actual = actual + 1 if sin_dato else 0
        mejor = max(mejor, actual)
    return mejor


def calidad_de_serie_diaria(serie):
    """Por cada mes: % de días con registro, cuántos faltan y cuántos de ellos son consecutivos."""
    s = serie.reindex(DIAS)
    filas = []
    for per, g in s.groupby(s.index.to_period("M")):
        con = int(g.notna().sum())
        filas.append({"periodo": per, "pct": con / len(g) * 100, "faltan": len(g) - con,
                      "racha": racha_mas_larga(g.isna().values), "dias": len(g)})
    return pd.DataFrame(filas).set_index("periodo").reindex(periodos)


def calidad_de_serie_mensual(serie):
    """Las fuentes que solo existen en paso mensual: el mes está o no está, sin medias tintas."""
    s = serie.reindex(periodos)
    return pd.DataFrame({"pct": s.notna() * 100.0, "faltan": np.nan, "racha": np.nan,
                         "dias": np.nan}, index=periodos)


era_diaria = pd.read_csv("out/era5land_temperatura_diaria_fonce.csv",
                         parse_dates=["fecha"]).set_index("fecha")

# El orden agrupa por origen: primero lo que sale de un instrumento en el terreno, después los
# productos de malla. `paso` distingue las series que permiten contar días de las que no.
FUENTES_CALIDAD = [
    ("Q · caudal de San Gil (CAMELS-COL)", "diario", cam["caudal"]),
    ("ETP · Hargreaves con ERA5-Land", "diario", _etp_d["etp_era5land"]),
    ("T mínima · MSWX (CAMELS-COL)", "diario", cam["t_min"]),
    ("T máxima · MSWX (CAMELS-COL)", "diario", cam["t_max"]),
    ("T media · ERA5-Land", "diario", era_diaria["t_media"]),
    ("T mínima · ERA5-Land", "diario", era_diaria["t_min"]),
    ("T máxima · ERA5-Land", "diario", era_diaria["t_max"]),
    ("PI · precipitación IMERG en la cuenca", "mensual",
     imm[imm.id_estacion == 24027010].set_index("periodo")["p_imerg_mm"]),
    ("PL · promedio de la red de pluviómetros", "mensual", red),
] + [(f"PL · {cat_plu.loc[c, 'etiqueta']}", "mensual", plu[c]) for c in DENTRO]

def detalle_del_mes(paso, faltan, racha, utilizable):
    """Frase que se muestra al pasar el cursor. Se arma aquí y no en el navegador porque el globo de
    Plotly no admite condicionales, y lo que hay que decir cambia según el paso y según si el mes pasa
    la regla."""
    if paso != "diario":
        return "con dato" if utilizable else "sin dato"
    if faltan == 0:
        return "mes completo, sin un solo día perdido"
    veredicto = ("entra al análisis" if utilizable
                 else f"queda fuera: el límite son {MAX_DIAS_FALTANTES} días")
    if faltan == 1:
        return f"falta 1 día · {veredicto}"
    if racha == 1:
        reparto = "todos sueltos"
    elif racha == faltan:
        reparto = "todos seguidos"
    else:
        reparto = f"{racha} de ellos seguidos"
    return f"faltan {faltan} días, {reparto} · {veredicto}"


cal_filas, cal_resumen = [], []
for nombre, paso, serie in FUENTES_CALIDAD:
    c = calidad_de_serie_diaria(serie) if paso == "diario" else calidad_de_serie_mensual(serie)
    # "utilizable" = el mes entra al análisis con la regla del proyecto
    utilizable = (c.faltan <= MAX_DIAS_FALTANTES) if paso == "diario" else (c.pct > 0)
    usable_lista = [bool(v) for v in utilizable.fillna(False)]
    cal_filas.append({
        "nombre": nombre, "paso": paso,
        "pct": [None if pd.isna(v) else round(float(v), 1) for v in c.pct],
        "detalle": [detalle_del_mes(paso, f, r, u) for f, r, u
                    in zip(c.faltan, c.racha, usable_lista)],
        "usable": usable_lista,
    })
    cal_resumen.append({
        "nombre": nombre, "paso": paso, "usables": int(utilizable.fillna(False).sum()),
        "parciales": int(((c.faltan > 0) & (c.faltan <= MAX_DIAS_FALTANTES)).sum()) if paso == "diario" else 0,
        "perdidos": int((~utilizable.fillna(False)).sum()),
    })

cal_json = json.dumps({"meses": [f"{p}-01" for p in periodos], "fuentes": cal_filas,
                       "maxFaltantes": MAX_DIAS_FALTANTES}, ensure_ascii=False)
cal_total = len(periodos)
filas_disp = "\n".join(
    f"<tr><td>{html.escape(v['nombre'])}</td><td>{v['paso']}</td>"
    f"<td class='num'>{v['usables']}</td>"
    f"<td class='num'>{v['parciales'] if v['paso'] == 'diario' else '—'}</td>"
    f"<td class='num'>{v['perdidos']}</td>"
    f"<td class='num'>{v['usables'] / cal_total * 100:.0f}%</td></tr>" for v in cal_resumen)

# Las cinco series de CAMELS-COL deberían fallar exactamente los mismos días, porque el archivo omite
# la fila completa de los días sin caudal. Se comprueba en vez de darlo por hecho.
_camels_nan = {c: cam[c].reindex(DIAS).isna() for c in ["caudal", "etp", "t_min", "t_max"]}
assert all(v.equals(_camels_nan["caudal"]) for v in _camels_nan.values()), \
    "CAMELS-COL: las cinco series ya no fallan los mismos días"

# cifras para el texto, todas calculadas
cal_completas = sum(1 for v in cal_resumen if v["perdidos"] == 0)
cal_min_usables = min(v["usables"] for v in cal_resumen)
cal_peores = [v["nombre"] for v in cal_resumen if v["usables"] == cal_min_usables]
# las series que vienen de CAMELS-COL fallan los mismos días (se comprueba abajo), así que conservan lo mismo
cal_camels = [v for v in cal_resumen if "CAMELS-COL" in v["nombre"]]
assert len({v["usables"] for v in cal_camels}) == 1
cal_q = next(v for v in cal_resumen if v["nombre"].startswith("Q ·"))
cal_q_detalle = calidad_de_serie_diaria(cam["caudal"])
cal_q_rotos = cal_q_detalle[cal_q_detalle.faltan > MAX_DIAS_FALTANTES]
cal_q_racha_max = int(cal_q_rotos.racha.max())
cal_q_racha_mes = cal_q_rotos.racha.idxmax()
cal_q_solo_dispersos = int((cal_q_rotos.racha <= MAX_DIAS_FALTANTES).sum())

# ---------------------------------------------------------------- anomalías en las series
# Las pruebas las corre scripts/07c_anomalias.py: saltos (Pettitt y doble masa), secuencias constantes,
# picos aislados de Q, cobertura de PL y meses en 0 mm. Aquí solo se leen y se redactan.
an_h = pd.read_csv("out/anomalias_homogeneidad.csv")
an_dm = pd.read_csv("out/anomalias_doble_masa.csv")
an_rachas = pd.read_csv("out/anomalias_rachas.csv")
an_picos = pd.read_csv("out/anomalias_picos_q.csv")
an_cob = pd.read_csv("out/anomalias_cobertura_pl.csv")
an_ceros = pd.read_csv("out/anomalias_ceros_pl.csv")
an_fila = lambda serie: an_h.set_index("serie").loc[serie]
fmt_p = lambda p: "&lt; 0.001" if p < 0.001 else f"{p:.3f}"
fmt_p_eq = lambda p: "&lt; 0.001" if p < 0.001 else f"= {p:.3f}"     # para escribir «p < 0.001» o «p = 0.006»
fmt_mes_an = lambda p: fmt_mes(pd.Period(p, "M"))
nota_enso = f"""  <p class="nota">Color de las fechas, según el Índice Oceánico El Niño (ONI) de la NOAA ({CITA_ONI}):
  <span class="fase-nino">rojo</span>, el mes cae dentro de un episodio de El Niño;
  <span class="fase-nina">azul</span>, dentro de uno de La Niña; sin color, ninguno de los dos. Un episodio
  exige al menos 5 trimestres móviles seguidos con el ONI en +0.5 °C o más (El Niño) o en −0.5 °C o menos
  (La Niña).</p>"""


def fecha_anomala(p):
    """Mes marcado como anómalo: con el color de su fase ENSO (como en «Revisión de outliers»), o en
    negrita si no cae en El Niño ni en La Niña."""
    p = pd.Period(p, "M")
    return fecha_enso(p) if CLASE_FASE.get(oni_fase.get(p, "neutro")) else f"<span class='fase-neutra'>{fmt_mes(p)}</span>"
an_pl = an_h[an_h.serie.str.startswith("PL")]
an_pl_sig = an_pl[an_pl.significativo]
an_pl_ok = an_pl[~an_pl.significativo]
filas_an = "\n".join(
    f"<tr><td>{html.escape(s)}</td><td class='detalle'>{html.escape(ref)}</td><td class='num'>{m}</td>"
    f"<td class='num'>{fecha_anomala(pm) if sig else fmt_mes_an(pm)}</td><td class='num{' res-revisar' if sig else ''}'>{fmt_p(p)}</td>"
    f"<td class='num'>{a:.2f}</td><td class='num'>{d:.2f}</td><td class='num'>{c:+.0f} %</td></tr>"
    for s, ref, m, pm, p, sig, a, d, c in an_h[["serie", "referencia", "meses", "primer_mes_despues", "p",
                                                "significativo", "razon_antes", "razon_despues", "cambio_pct"]].itertuples(index=False))
an_dm_json = json.dumps({s: {"x": g.acumulado_referencia.round(0).tolist(), "y": g.acumulado_serie.round(0).tolist(),
                             "meses": g.periodo.tolist(), "referencia": g.referencia.iloc[0],
                             "corte": (an_fila(s).primer_mes_despues if an_fila(s).significativo else None)}
                         for s, g in an_dm.groupby("serie", sort=False)}, ensure_ascii=False)
an_pi, an_q = an_fila("PI (IMERG)"), an_fila("Q")
an_pv = an_fila("PL · Pueblo Viejo")
# segundo corte (07c, paso 1b): la prueba repetida en el tramo posterior al primer salto de cada pluviómetro
# marcado, y PI contra una PL sin los pluviómetros que tienen un segundo salto significativo
an_seg = pd.read_csv("out/anomalias_segundo_corte.csv").set_index("serie")
an_seg_pl = an_seg[an_seg.index.str.startswith("PL")]
an_pv2 = an_seg.loc["PL · Pueblo Viejo"]
an_seg_sin_salto = an_seg_pl[~an_seg_pl.significativo]
an_pi_sin = an_seg.loc["PI (IMERG)"]
# meses entre el segundo salto de Pueblo Viejo y el salto de PI frente a PL
an_meses_pv2_pi = (pd.Period(an_pi.primer_mes_despues, "M") - pd.Period(an_pv2.primer_mes_despues, "M")).n
an_ceros_fuera = an_ceros[an_ceros.dificil_de_creer]
an_ceros_quedan = an_ceros[~an_ceros.dificil_de_creer]
filas_ceros = "\n".join(
    f"<tr><td>{html.escape(pl_)}</td><td>{fecha_anomala(m) if dif else fmt_mes_an(m)}</td><td class='num'>{mn:.0f}</td><td class='num'>{pr:.0f}</td>"
    f"<td class='num'>{pi_:.0f}</td><td class='{'res-revisar' if dif else ''}'>{'se excluye' if dif else 'se conserva'}</td></tr>"
    for pl_, m, mn, pr, pi_, dif in an_ceros[["pluviometro", "periodo", "otros_minimo_mm", "otros_promedio_mm",
                                               "pi_mm", "dificil_de_creer"]].itertuples(index=False))
an_rachas_pl = an_rachas[an_rachas.variable.str.startswith("PL")]
an_rachas_dia = an_rachas[~an_rachas.variable.str.startswith("PL")]
an_sesgo = an_cob.sesgo_estimado_pct.abs()
_nombre_pluvio = {c: cat_plu.loc[c, "etiqueta"] for c in cat_plu.index}
exc_lista = "; ".join(
    f"{_nombre_pluvio[c]} de {fmt_mes_an(d)} a {fmt_mes_an(h)}" if d != h else f"{_nombre_pluvio[c]} en {fecha_anomala(d)}"
    for c, d, h in exclusiones[["codigo", "desde", "hasta"]].itertuples(index=False))
sesgo_pi_pl = (comp["IMERG"].mean() / comp["RED"].mean() - 1) * 100

# ---------------------------------------------------------------- control de calidad básico (4.2)
# Los chequeos sobre los archivos crudos los hace scripts/07b_control_calidad_basico.py; aquí se leen, y
# la revisión a mano de un mes completo está solo en la sección 4.2 del notebook.
cc = pd.read_csv("out/control_calidad_basico.csv")
cc_naturaleza = pd.read_csv("out/naturaleza_fuentes.csv")
cc_conteo = cc.resultado.value_counts()
cc_revisar = cc[cc.resultado == "revisar"]
CLASE_RESULTADO = {"sin problemas": "", "anotado": "res-anotado", "revisar": "res-revisar", "no disponible": "res-nd"}
filas_cc = "\n".join(
    f"<tr><td>{html.escape(f)}</td><td>{html.escape(c)}</td><td class='{CLASE_RESULTADO[res]}'>{res}</td>"
    f"<td class='detalle'>{html.escape(d)}</td></tr>"
    for f, c, res, d in cc[["fuente", "chequeo", "resultado", "detalle"]].itertuples(index=False))
filas_naturaleza = "\n".join(
    f"<tr><td><b>{html.escape(v)}</b></td><td>{html.escape(fu)}</td><td>{html.escape(ti)}</td>"
    f"<td class='detalle'>{html.escape(co)}</td><td class='detalle'>{html.escape(re_)}</td></tr>"
    for v, fu, ti, co, re_ in cc_naturaleza.itertuples(index=False))

# ---------------------------------------------------------------- registro de anomalías (4.4)
# El registro lo arma scripts/07d_trazabilidad.py con las cifras de los demás scripts; aquí solo se muestra.
# La columna «evidencia» (sección del notebook) no se muestra: el informe no nombra los puntos del taller.
reg = pd.read_csv("out/registro_anomalias.csv")
reg_conteo = reg.estado.value_counts()
CLASE_ESTADO = {"corregido": "", "incierto": "res-revisar", "descartado": "res-nd"}
filas_reg = "\n".join(
    f"<tr><td class='num'>{n_}</td><td class='{CLASE_ESTADO[es]}'>{es}</td><td>{html.escape(se)}</td>"
    f"<td class='reg-anomalia'>{html.escape(an)}</td><td class='detalle'>{html.escape(co)}</td>"
    f"<td class='detalle'>{html.escape(de)}</td><td class='detalle'>{html.escape(ef)}</td></tr>"
    for n_, an, se, co, de, ef, es in reg[["n", "anomalia", "serie", "comprobacion", "decision", "efecto",
                                           "estado"]].itertuples(index=False))


# ¿Por qué cuatro días? La misma prueba de la sección 4.1 del notebook: a cada mes COMPLETO de Q se le quita
# un bloque de MAX_DIAS_FALTANTES días seguidos (el peor caso) en cada posición posible del mes, y se mide
# cuánto se aleja el caudal medio del mes del verdadero. No hay nada aleatorio.
_q_dia = cam["caudal"].reindex(DIAS)
_q_completos = [g.to_numpy() for _, g in _q_dia.groupby(_q_dia.index.to_period("M")) if g.notna().all()]
_errores = np.array([abs(np.delete(d, range(i, i + MAX_DIAS_FALTANTES)).mean() / d.mean() - 1) * 100
                     for d in _q_completos for i in range(len(d) - MAX_DIAS_FALTANTES + 1)])
umbral_mediana, umbral_p95 = np.median(_errores), np.percentile(_errores, 95)
umbral_meses_completos = int((cal_q_detalle.faltan == 0).sum())

# Acumulados de los meses incompletos: cuánto les faltaría si solo se sumaran los días con dato, en vez
# del acumulado de a_mensual (promedio x días del mes). La proporción no depende de la unidad.
_q_incompletos = cal_q_detalle.index[(cal_q_detalle.faltan > 0) & (cal_q_detalle.faltan <= MAX_DIAS_FALTANTES)]
_q_suma = _q_dia.resample("MS").sum()
_q_suma.index = _q_suma.index.to_period("M")
suma_parcial_falta = (1 - _q_suma[_q_incompletos] / a_mensual(cam["caudal"], "sum")[_q_incompletos]) * 100


# ---------------------------------------------------------------- lluvia contra altitud
# Dos fuentes independientes para la misma pregunta: los pluviómetros (medida directa, pocos puntos) y
# las celdas de IMERG cruzadas contra el DEM (muestra densa, ajena a la red de estaciones).
# Requiere haber corrido antes scripts/09_gradiente_altitudinal.py, que produce el CSV de las celdas.
grad_celdas = pd.read_csv("out/gradiente_altitudinal_imerg.csv")
grad_cat = pd.read_csv("out/pluviometros_fonce_catalogo.csv")
grad_men = pd.read_csv("out/pluviometros_fonce_mensual_depurado.csv")

# Media mensual x 12: no se suman años incompletos, que subestimarían el total.
_media_mes = grad_men.groupby("codigo").precipitacion_mm.mean().rename("p_mes_mm")
grad_plu = grad_cat.merge(_media_mes, on="codigo")
grad_plu["p_anual_mm"] = grad_plu.p_mes_mm * 12
grad_plu["nombre_corto"] = grad_plu.nombre.str.replace(r"\s*\[\d+\]", "", regex=True).str.strip()
grad_plu = grad_plu.sort_values("altitud")
grad_dentro = grad_plu[grad_plu.dentro_cuenca]
grad_fuera = grad_plu[~grad_plu.dentro_cuenca]

FRAC_MINIMA_GRAD = 0.30                    # solo para el dibujo: separa las celdas que apenas rozan
grad_nucleo = grad_celdas[grad_celdas.frac_dentro > FRAC_MINIMA_GRAD]
grad_borde = grad_celdas[grad_celdas.frac_dentro <= FRAC_MINIMA_GRAD]


def ajuste_lineal(altitud, precipitacion, pesos=None):
    """Recta de precipitación contra altitud, con su correlación. Con `pesos`, mínimos cuadrados
    ponderados y correlación ponderada (cada celda cuenta según la fracción de su área dentro)."""
    x, y = np.asarray(altitud, float), np.asarray(precipitacion, float)
    w = np.ones_like(x) if pesos is None else np.asarray(pesos, float)
    pendiente, intercepto = np.polyfit(x, y, 1, w=np.sqrt(w))   # polyfit pondera los residuos
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    r = float(np.sum(w * (x - mx) * (y - my))
              / np.sqrt(np.sum(w * (x - mx) ** 2) * np.sum(w * (y - my) ** 2)))
    return {"intercepto": float(intercepto), "por_1000m": float(pendiente * 1000),
            "r": r, "r2": r ** 2, "n": int(len(x))}


# el ajuste usa TODAS las celdas que tocan la cuenca, ponderadas por la fracción de su área dentro
aj_imerg = ajuste_lineal(grad_celdas.altitud_media_m, grad_celdas.p_anual_mm, pesos=grad_celdas.frac_dentro)
aj_plu = ajuste_lineal(grad_dentro.altitud, grad_dentro.p_anual_mm)

# El mismo ajuste sin las dos estaciones que se salen de la tendencia. No se descartan por estorbar:
# Encino tiene un tramo dudoso de 2016 a 2018 que ya estaba marcado, y Pueblo Viejo mide menos que una
# estación 518 m más alta, cosa que la altitud por sí sola no puede explicar. Verlas fuera sirve para
# medir cuánto de la diferencia entre las dos fuentes venía solo de ellas dos.
CODIGOS_APARTE = [24020040, 24020230]                     # ENCINO, PUEBLO VIEJO
grad_limpio = grad_dentro[~grad_dentro.codigo.isin(CODIGOS_APARTE)]
grad_aparte = grad_dentro[grad_dentro.codigo.isin(CODIGOS_APARTE)]
aj_limpio = ajuste_lineal(grad_limpio.altitud, grad_limpio.p_anual_mm)
grad_brecha = abs(aj_limpio["por_1000m"] - aj_imerg["por_1000m"])
grad_brecha_7 = abs(aj_plu["por_1000m"] - aj_imerg["por_1000m"])
grad_parte_de_las_dos = (1 - grad_brecha / grad_brecha_7) * 100    # cuánto de la brecha se va al apartarlas

# En qué subcuenca cae cada estación. El cruce geométrico lo hace scripts/10_estaciones_subcuencas.py,
# que además dibuja el mapa; aquí solo se lee su resultado para no repetir la lógica.
sub_est = pd.read_csv("out/estaciones_subcuencas.csv").set_index("codigo")
sub_humeda = sub_est.loc[COD_HUMEDA := 24020040]        # ENCINO
sub_seca = sub_est.loc[COD_SECA := 24020230]            # PUEBLO VIEJO
# las vecinas de Pueblo Viejo dentro de su propia subcuenca, ordenadas por altura
vecinas_seca = sub_est[(sub_est.subcuenca == sub_seca.subcuenca)
                       & (sub_est.index != COD_SECA)].sort_values("altitud")
sub_brecha_imerg = abs(sub_humeda.p_imerg_subcuenca - sub_seca.p_imerg_subcuenca)
sub_brecha_plu = sub_humeda.p_anual / sub_seca.p_anual - 1

# rango de altitud y de lluvia que ve IMERG, para el texto
grad_alt_baja, grad_alt_alta = grad_celdas.altitud_media_m.min(), grad_celdas.altitud_media_m.max()
grad_p_baja = aj_imerg["intercepto"] + aj_imerg["por_1000m"] / 1000 * grad_alt_baja
grad_p_alta = aj_imerg["intercepto"] + aj_imerg["por_1000m"] / 1000 * grad_alt_alta
grad_caida = grad_p_baja - grad_p_alta

grad_datos = {
    "imerg": {"alt": grad_celdas.altitud_media_m.round(0).tolist(),
              "p": grad_celdas.p_anual_mm.round(0).tolist(),
              "frac": (grad_celdas.frac_dentro * 100).round(0).tolist()},
    "imergBorde": {"alt": grad_borde.altitud_media_m.round(0).tolist(),
                   "p": grad_borde.p_anual_mm.round(0).tolist(),
                   "frac": (grad_borde.frac_dentro * 100).round(0).tolist()},
    "plu": {"alt": grad_dentro.altitud.round(0).tolist(),
            "p": grad_dentro.p_anual_mm.round(0).tolist(),
            "nombre": grad_dentro.nombre_corto.tolist()},
    "pluFuera": {"alt": grad_fuera.altitud.round(0).tolist(),
                 "p": grad_fuera.p_anual_mm.round(0).tolist(),
                 "nombre": grad_fuera.nombre_corto.tolist()},
    "rectaImerg": {"x": [float(grad_alt_baja), float(grad_alt_alta)],
                   "y": [round(grad_p_baja, 0), round(grad_p_alta, 0)]},
    "rectaPlu": {"x": [float(grad_dentro.altitud.min()), float(grad_dentro.altitud.max())],
                 "y": [round(aj_plu["intercepto"] + aj_plu["por_1000m"] / 1000 * grad_dentro.altitud.min(), 0),
                       round(aj_plu["intercepto"] + aj_plu["por_1000m"] / 1000 * grad_dentro.altitud.max(), 0)]},
    # las mismas estaciones, apartando Encino y Pueblo Viejo
    "pluLimpio": {"alt": grad_limpio.altitud.round(0).tolist(),
                  "p": grad_limpio.p_anual_mm.round(0).tolist(),
                  "nombre": grad_limpio.nombre_corto.tolist()},
    "pluAparte": {"alt": grad_aparte.altitud.round(0).tolist(),
                  "p": grad_aparte.p_anual_mm.round(0).tolist(),
                  "nombre": grad_aparte.nombre_corto.tolist()},
    "rectaLimpio": {"x": [float(grad_limpio.altitud.min()), float(grad_limpio.altitud.max())],
                    "y": [round(aj_limpio["intercepto"] + aj_limpio["por_1000m"] / 1000 * grad_limpio.altitud.min(), 0),
                          round(aj_limpio["intercepto"] + aj_limpio["por_1000m"] / 1000 * grad_limpio.altitud.max(), 0)]},
    # la recta de IMERG extendida al mismo tramo de altitud, para poder compararlas de frente
    "rectaImergEnTramo": {"x": [float(grad_limpio.altitud.min()), float(grad_limpio.altitud.max())],
                          "y": [round(aj_imerg["intercepto"] + aj_imerg["por_1000m"] / 1000 * grad_limpio.altitud.min(), 0),
                                round(aj_imerg["intercepto"] + aj_imerg["por_1000m"] / 1000 * grad_limpio.altitud.max(), 0)]},
}
grad_json = json.dumps(grad_datos, ensure_ascii=False)

filas_grad = "\n".join(
    f"<tr><td>{html.escape(e.nombre_corto)}</td><td class='num'>{n(e.altitud)}</td>"
    f"<td class='num'>{n(e.p_anual_mm)}</td>"
    f"<td>{'dentro' if e.dentro_cuenca else 'fuera'}</td></tr>"
    for e in grad_plu.itertuples())

# la estación con más lluvia y la más alta, para el texto
grad_mas_lluviosa = grad_dentro.loc[grad_dentro.p_anual_mm.idxmax()]
grad_mas_alta = grad_dentro.loc[grad_dentro.altitud.idxmax()]
grad_mas_seca = grad_dentro.loc[grad_dentro.p_anual_mm.idxmin()]



# ---------------------------------------------------------------- índice lateral
# Panel fijo que se abre y se cierra. El esquema se arma en el navegador a partir de los h2 y h3 del
# documento, así que se mantiene al día solo cuando se agregan o se mueven secciones. Van como texto
# normal (no f-string) para no tener que doblar cada llave del CSS y del JS.
INDICE_CSS = """
.indice-boton { position: fixed; top: 14px; left: 14px; z-index: 40; display: flex; align-items: center; gap: 8px;
  font: 600 12px/1 var(--f-dato); letter-spacing: .08em; text-transform: uppercase; color: var(--tinta);
  background: var(--superficie); border: 1px solid var(--linea); border-radius: 6px; padding: 10px 12px; cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.indice-boton:hover { border-color: var(--acento); color: var(--acento); }
.indice-boton:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }
.indice-boton svg { width: 16px; height: 16px; stroke: currentColor; }
.indice { position: fixed; top: 0; left: 0; bottom: 0; z-index: 30; width: 290px; max-width: 86vw;
  background: var(--superficie); border-right: 1px solid var(--linea); padding: 64px 0 24px;
  overflow-y: auto; transform: translateX(-100%); transition: transform .2s ease; visibility: hidden; }
.indice-abierto .indice { transform: none; visibility: visible; }
.indice h2 { font: 600 11px/1 var(--f-dato); letter-spacing: .12em; text-transform: uppercase; color: var(--tenue);
  margin: 0 0 10px; padding: 0 20px; }
.indice ol { list-style: none; margin: 0; padding: 0; }
.indice a { display: block; text-decoration: none; color: var(--tinta); border-left: 3px solid transparent;
  font: 500 14px/1.3 var(--f-titulo); padding: 7px 20px 7px 17px; }
.indice a:hover { background: var(--acento-suave); }
.indice a:focus-visible { outline: 2px solid var(--acento); outline-offset: -2px; }
.indice ol ol a { font: 400 13px/1.3 var(--f-texto); color: var(--tenue); padding: 4px 20px 4px 33px; }
.indice a.activo { border-left-color: var(--acento); color: var(--acento); background: var(--acento-suave); }
.indice ol ol a.activo { background: none; }
.indice-velo { position: fixed; inset: 0; z-index: 25; background: rgba(0,0,0,.35); display: none; }
.envoltura { transition: margin-left .2s ease; }
section, section h3 { scroll-margin-top: 20px; }
/* con pantalla ancha el panel empuja el contenido; en pantallas angostas va encima, con un velo */
@media (min-width: 1200px) {
  .indice-abierto .envoltura { margin-left: max(310px, calc((100vw - 1080px) / 2)); }
}
@media (max-width: 1199px) {
  .indice-abierto .indice-velo { display: block; }
  .envoltura { padding-top: 64px; }
}
@media (prefers-reduced-motion: reduce) { .indice, .envoltura { transition: none; } }
"""

INDICE_HTML = """
<button class="indice-boton" type="button" aria-controls="indice" aria-expanded="false">
  <svg viewBox="0 0 16 16" fill="none" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
    <path d="M2 4h12M2 8h12M2 12h8"/></svg><span>Índice</span>
</button>
<div class="indice-velo" hidden></div>
<nav class="indice" id="indice" aria-label="Índice del documento">
  <h2>Contenido</h2>
  <ol></ol>
</nav>
<script>
(() => {
  const raiz = document.documentElement;
  const boton = document.querySelector(".indice-boton");
  const velo = document.querySelector(".indice-velo");
  const lista = document.querySelector("#indice > ol");
  const CLAVE = "indice-abierto";
  const ancho = window.matchMedia("(min-width: 1200px)");

  // --- el esquema, a partir de los títulos del documento ---
  const slug = s => s.toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
                     .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const usados = new Set();
  const idPara = (el, texto) => {
    if (el.id) return el.id;
    let base = slug(texto) || "seccion", id = base, k = 2;
    while (usados.has(id) || document.getElementById(id)) id = base + "-" + k++;
    usados.add(id); el.id = id; return id;
  };
  const enlaces = [];
  let sublista = null;
  document.querySelectorAll(".envoltura section h2, .envoltura section h3").forEach(h => {
    const texto = h.textContent.trim();
    const destino = h.tagName === "H2" ? h.closest("section") : h;
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = "#" + idPara(destino, texto);
    a.textContent = texto;
    li.appendChild(a);
    if (h.tagName === "H2") {
      lista.appendChild(li);
      sublista = document.createElement("ol");
      li.appendChild(sublista);
    } else if (sublista) {
      sublista.appendChild(li);
    } else {
      lista.appendChild(li);
    }
    enlaces.push({ a, destino });
  });

  // --- abrir y cerrar; se recuerda la preferencia (si el navegador deja guardarla) ---
  const leer = () => { try { return localStorage.getItem(CLAVE); } catch (e) { return null; } };
  const guardar = v => { try { localStorage.setItem(CLAVE, v); } catch (e) {} };
  const avisarGraficos = () => setTimeout(() => window.dispatchEvent(new Event("resize")), 230);
  function fijar(abierto, recordar) {
    raiz.classList.toggle("indice-abierto", abierto);
    boton.setAttribute("aria-expanded", String(abierto));
    velo.hidden = !abierto;
    if (recordar) guardar(abierto ? "1" : "0");
    avisarGraficos();
  }
  const guardado = leer();
  fijar(guardado === null ? ancho.matches : guardado === "1" && ancho.matches, false);
  boton.addEventListener("click", () => fijar(!raiz.classList.contains("indice-abierto"), true));
  velo.addEventListener("click", () => fijar(false, true));
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && raiz.classList.contains("indice-abierto") && !ancho.matches) {
      fijar(false, true); boton.focus();
    }
  });

  // --- al saltar: si el destino está dentro de un bloque plegado, se despliega primero ---
  lista.addEventListener("click", e => {
    const a = e.target.closest("a");
    if (!a) return;
    const destino = document.getElementById(a.getAttribute("href").slice(1));
    const plegado = destino && destino.closest("details:not([open])");
    if (plegado) plegado.open = true;
    if (!ancho.matches) fijar(false, false);
  });

  // --- resaltar dónde va el lector ---
  let actual = null;
  function marcar() {
    const tope = window.innerHeight * 0.25;
    let elegido = enlaces[0];
    for (const x of enlaces) {
      if (x.destino.offsetParent === null) continue;          // oculto dentro de un plegado
      if (x.destino.getBoundingClientRect().top <= tope) elegido = x; else break;
    }
    if (elegido === actual) return;
    lista.querySelectorAll("a.activo").forEach(a => a.classList.remove("activo", "padre"));
    elegido.a.classList.add("activo");
    actual = elegido;
    // la sección padre también se marca, para que se vea en qué parte del documento se está
    const padre = elegido.a.closest("ol ol");
    if (padre) padre.parentElement.firstElementChild.classList.add("padre", "activo");
  }
  let pendiente = false;
  window.addEventListener("scroll", () => {
    if (pendiente) return;
    pendiente = true;
    requestAnimationFrame(() => { marcar(); pendiente = false; });
  }, { passive: true });
  marcar();
})();
</script>
"""


pagina = f"""<title>Reporte cuenca del Fonce</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.32.0/plotly.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --fondo: #F5F7F6; --superficie: #FFFFFF; --tinta: #17211E; --tenue: #56645F; --linea: #D5DDDA;
  --acento: #1B6A80; --acento-suave: #E2EFF2; --placa: #FFFFFF; --atip-alto: #F7D9C4; --atip-bajo: #CFE3F2; --nino: #B8321F; --nina: #1C63A8; --revision: #FFF4C2; --revision-borde: #8A6500;
  --f-titulo: "Archivo", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --f-texto: "Source Serif 4", Georgia, "Times New Roman", serif;
  --f-dato: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
    --acento: #72B9CE; --acento-suave: #1C2D32; --placa: #F4F6F5; --atip-alto: #5A3420; --atip-bajo: #1F3A52; --nino: #F2836B; --nina: #6FB4EE; --revision: #37300F; --revision-borde: #E0B84A;
  }}
}}
:root[data-theme="dark"] {{
  --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
  --acento: #72B9CE; --acento-suave: #1C2D32; --placa: #F4F6F5; --atip-alto: #5A3420; --atip-bajo: #1F3A52; --nino: #F2836B; --nina: #6FB4EE; --revision: #37300F; --revision-borde: #E0B84A;
}}
* {{ box-sizing: border-box; }}
body {{ background: var(--fondo); color: var(--tinta); font: 400 17px/1.6 var(--f-texto); margin: 0; }}
.envoltura {{ max-width: 1080px; margin: 0 auto; padding-inline: 20px; padding-block: 48px 72px; }}
header {{ border-bottom: 1px solid var(--linea); padding-bottom: 28px; margin-bottom: 40px; }}
.antetitulo {{ font: 600 12px/1 var(--f-dato); letter-spacing: .12em; text-transform: uppercase; color: var(--acento); margin: 0 0 14px; }}
h1 {{ font: 800 clamp(32px, 5vw, 50px)/1.05 var(--f-titulo); font-stretch: 82%; letter-spacing: -.01em; margin: 0 0 16px; text-wrap: balance; }}
h2 {{ font: 700 26px/1.2 var(--f-titulo); font-stretch: 88%; margin: 0 0 12px; text-wrap: balance; }}
h3 {{ font: 600 13px/1.3 var(--f-dato); letter-spacing: .08em; text-transform: uppercase; color: var(--tenue); margin: 0 0 10px; }}
p {{ margin: 0 0 14px; max-width: 66ch; }}
.intro {{ font-size: 19px; color: var(--tenue); max-width: 60ch; margin: 0; }}
.cifras {{ display: flex; flex-wrap: wrap; gap: 12px 36px; margin-top: 24px; }}
.cifra {{ display: flex; flex-direction: column; gap: 2px; }}
.cifra b {{ font: 500 24px/1.1 var(--f-dato); font-variant-numeric: tabular-nums; }}
.cifra span {{ font: 400 12px/1.3 var(--f-dato); color: var(--tenue); letter-spacing: .04em; }}
section {{ margin-bottom: 64px; }}
.tabla-caja {{ overflow-x: auto; margin: 20px 0 8px; border: 1px solid var(--linea); border-radius: 6px; background: var(--superficie); }}
table {{ border-collapse: collapse; width: 100%; min-width: 640px; font: 400 14px/1.4 var(--f-dato); font-variant-numeric: tabular-nums; }}
th {{ font: 600 11px/1.3 var(--f-dato); text-transform: uppercase; letter-spacing: .06em; color: var(--tenue); text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--linea); vertical-align: bottom; }}
td {{ padding: 8px 12px; border-bottom: 1px solid var(--linea); }}
tr:last-child td {{ border-bottom: 0; }}
tbody tr:first-child td {{ background: var(--acento-suave); font-weight: 500; }}
.num, th.num {{ text-align: right; }}
.cod {{ color: var(--tenue); }}
.nota {{ font-size: 14px; color: var(--tenue); }}
.plegable > summary {{ list-style: none; cursor: pointer; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; }}
.plegable > summary::-webkit-details-marker {{ display: none; }}
.plegable > summary h2 {{ display: inline; margin: 0 0 12px; }}
.plegable > summary h2::before {{ content: "▸"; display: inline-block; width: 1.1em; color: var(--acento); transition: transform .15s; }}
.plegable[open] > summary h2::before {{ transform: rotate(90deg); }}
.plegable > summary:focus-visible {{ outline: 2px solid var(--acento); outline-offset: 4px; border-radius: 4px; }}
.plegable-pista {{ font: 400 12px/1 var(--f-dato); color: var(--tenue); letter-spacing: .04em; }}
.sin-destacar tbody tr:first-child td {{ background: none; font-weight: 400; }}
.tratamiento {{ max-width: 66ch; padding-left: 20px; margin: 0; font-size: 15px; }}
.tratamiento li {{ margin-bottom: 6px; }}
.fase-nino {{ color: var(--nino); font-weight: 600; }}
.tratamiento .lectura {{ margin: 6px 0 0; }}
/* control de calidad: lo agregado o cambiado en esta etapa va resaltado para revisión */
.revision {{ background: var(--revision); border-left: 4px solid var(--revision-borde); padding: 10px 14px;
  margin: 14px 0; border-radius: 0 4px 4px 0; }}
.revision > p {{ margin: 0 0 8px; }}
.revision > p:last-child {{ margin-bottom: 0; }}
.revision::before {{ content: attr(data-etiqueta); display: block; font: 600 11px/1.4 var(--f-dato);
  letter-spacing: .06em; text-transform: uppercase; color: var(--revision-borde); margin-bottom: 6px; }}
.formula {{ font: 500 16px/1.5 var(--f-dato); margin: 4px 0 12px; overflow-wrap: anywhere; }}
td.res-revisar, .sin-destacar tbody tr:first-child td.res-revisar {{ background: var(--atip-alto); font-weight: 600; }}
td.res-anotado {{ background: var(--revision); }}
td.res-nd {{ color: var(--tenue); }}
td.reg-anomalia {{ min-width: 16em; }}
td.detalle {{ font-size: 13px; min-width: 260px; }}
.cita {{ color: inherit; text-decoration: underline dotted; text-underline-offset: 2px; }}
.bibliografia {{ max-width: 72ch; padding-left: 22px; font-size: 15px; }}
.bibliografia li {{ margin-bottom: 10px; overflow-wrap: anywhere; }}
.bibliografia li:target {{ background: var(--acento-suave); }}
.fase-nina {{ color: var(--nina); font-weight: 600; }}
.fase-neutra {{ font-weight: 600; }}
.fase-nino, .fase-nina, .fase-neutra {{ white-space: nowrap; }}
td.atip-alto, .sin-destacar tbody tr:first-child td.atip-alto {{ background: var(--atip-alto); font-weight: 600; }}
td.atip-bajo, .sin-destacar tbody tr:first-child td.atip-bajo {{ background: var(--atip-bajo); font-weight: 600; }}
.pestanas {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 18px; border-bottom: 1px solid var(--linea); }}
.pestanas button {{ font: 500 14px/1 var(--f-dato); letter-spacing: .02em; color: var(--tenue); background: none; border: 1px solid transparent;
  border-bottom: 0; border-radius: 6px 6px 0 0; padding: 11px 16px; margin-bottom: -1px; cursor: pointer; }}
.pestanas button:hover {{ color: var(--tinta); }}
.pestanas button[aria-selected="true"] {{ color: var(--acento); background: var(--fondo); border-color: var(--linea); border-bottom: 1px solid var(--fondo); font-weight: 600; }}
.pestanas button:focus-visible {{ outline: 2px solid var(--acento); outline-offset: 2px; }}
.grafico {{ width: 100%; min-height: 440px; }}
.dos-graficos {{ display: grid; grid-template-columns: minmax(0, 1.9fr) minmax(0, 1fr); gap: 20px; align-items: start; margin-top: 12px; }}
@media (max-width: 860px) {{ .dos-graficos {{ grid-template-columns: 1fr; }} }}
figure {{ margin: 24px 0 0; display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 32px; align-items: start; }}
.placa {{ background: var(--placa); border: 1px solid var(--linea); border-radius: 6px; padding: 10px; }}
.placa img {{ display: block; width: 100%; height: auto; }}
figcaption {{ font-size: 16px; }}
figcaption p {{ max-width: none; }}
.lista-datos {{ display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; margin: 18px 0; padding: 14px 0; border-block: 1px solid var(--linea); font: 400 13px/1.45 var(--f-dato); }}
.lista-datos dt {{ color: var(--tenue); }}
.lista-datos dd {{ margin: 0; font-variant-numeric: tabular-nums; }}
.aviso {{ border-left: 3px solid var(--acento); padding: 4px 0 4px 14px; font-size: 15px; }}
footer {{ border-top: 1px solid var(--linea); padding-top: 24px; font-size: 14px; color: var(--tenue); }}
footer ul {{ padding-left: 18px; margin: 8px 0 0; }}
footer li {{ margin-bottom: 6px; }}
code {{ font: 400 .86em var(--f-dato); }}
a {{ color: var(--acento); }}
@media (max-width: 760px) {{
  figure {{ grid-template-columns: 1fr; gap: 16px; }}
  body {{ font-size: 16px; }}
}}
{INDICE_CSS}
</style>

<div class="envoltura">
<header>
  <p class="antetitulo">Hidrología · Tarea 1 · Análisis de cuenca</p>
  <h1>Cuenca del río Fonce hasta San Gil</h1>
  <p class="intro">Santander, Colombia. Estación de aforo IDEAM {24027010} en San Gil, con cinco subcuencas anidadas que también tienen caudal medido.</p>
  <div class="cifras">
    <div class="cifra"><b>{n(sg['area'])} km²</b><span>área de drenaje</span></div>
    <div class="cifra"><b>{n(elev_min)}–{n(elev_max)} m</b><span>rango de elevación (DEM)</span></div>
    <div class="cifra"><b>{n(elev_media)} m</b><span>elevación media (DEM)</span></div>
    <div class="cifra"><b>{n(p_imerg[24027010])} mm</b><span>lluvia anual IMERG 1998–2022</span></div>
  </div>
</header>

<section>
  <h2>La cuenca y sus subcuencas</h2>
  <p>El Fonce nace en el páramo al sureste (por encima de 4 000 m) y corre hacia el norte por un valle ancho hasta San Gil.
  Las cinco estaciones aguas arriba dividen la cuenca en subcuencas de tamaños muy distintos: Mérida, sobre el mismo Fonce,
  drena casi toda la cuenca; Monchía y Mogoticos son pequeñas.</p>
  <div class="tabla-caja">
  <table>
    <thead><tr><th>Código IDEAM</th><th>Estación</th><th>Río</th><th class="num">Área (km²)</th><th class="num">% de San Gil</th>
    <th class="num">Elevación (m)</th><th class="num">Elev. media (m)</th><th class="num">Lluvia IMERG (mm/año)</th></tr></thead>
    <tbody>
{filas}
    </tbody>
  </table>
  </div>
  <p class="nota">Área y elevación: atributos de CAMELS-COL. Lluvia: promedio de los totales anuales de IMERG mensual (1998–2022) ponderado por área sobre cada subcuenca.</p>
</section>

<section>
  <h2>Mapas de la cuenca</h2>
  <div class="pestanas" role="tablist" aria-label="Mapa a mostrar">
    <button type="button" role="tab" id="pestana-dem" aria-controls="panel-dem" aria-selected="true">Relieve (DEM)</button>
    <button type="button" role="tab" id="pestana-imerg" aria-controls="panel-imerg" aria-selected="false" tabindex="-1">Píxeles de IMERG</button>
    <button type="button" role="tab" id="pestana-era5" aria-controls="panel-era5" aria-selected="false" tabindex="-1">Píxeles de ERA5-Land</button>
  </div>
  <div role="tabpanel" id="panel-dem" aria-labelledby="pestana-dem">
  <figure>
    <div class="placa"><img src="{img('dem_fonce.png')}" alt="Mapa de elevación de la cuenca del Fonce con sombreado, la estación de aforo de San Gil y los siete pluviómetros del IDEAM que están dentro de la cuenca" width="1024" height="1376"></div>
    <figcaption>
      <h3>Figura 1 · Modelo digital de elevación</h3>
      <p>La mitad norte y oeste es un valle entre 1 100 y 2 000 m, donde está la estación de aforo de San Gil, la salida de la cuenca.
      La mitad sureste sube hasta el páramo, por encima de 3 500 m.</p>
      <p>Los <b>{len(DENTRO)} pluviómetros</b> del IDEAM que caen dentro de la divisoria están marcados en el mapa, con su altitud.
      Van de Valle de San Jose (1 300 m), en el fondo del valle, a Las Pavas (2 625 m), la estación más alta de la cuenca.
      Se reparten entre el valle del norte y la vertiente oriental, pero <b>ninguno llega al páramo</b>: por encima de 2 625 m,
      donde está casi un tercio del área, no hay ningún aparato midiendo lluvia.</p>
      <p class="nota">Se descargó un octavo pluviómetro, Mamonal El Hacienda, que queda fuera de la divisoria, en la vertiente del
      Chicamocha. No aparece en el mapa ni entra en el promedio de la cuenca.</p>
      <dl class="lista-datos">
        <dt>Fuente</dt><dd>ALOS PALSAR</dd>
        <dt>Resolución</dt><dd>12.5 m original; remuestreado a 50 m para la figura</dd>
        <dt>Proyección</dt><dd>UTM 19N (EPSG:32619); áreas y longitudes, en el elipsoide o en EPSG:3116</dd>
        <dt>Elevación en la cuenca</dt><dd>{n(elev_min)}–{n(elev_max)} m, media {n(elev_media)} m</dd>
      </dl>
      <p class="nota">CAMELS-COL publica {n(sg['minimum_ele'])}–{n(sg['maximum_ele'])} m, media
      {n(sg['mean_ele'])} m: la mayor diferencia es de {n(elev_dif_max)} m, así que el polígono y el DEM
      están bien alineados.</p>
    </figcaption>
  </figure>
  </div>
  <div role="tabpanel" id="panel-imerg" aria-labelledby="pestana-imerg" hidden>
  <figure>
    <div class="placa"><img src="{img('imerg_pixeles.png')}" alt="Grilla de píxeles de IMERG sobre la cuenca, coloreados por lluvia media anual, rotulados con el porcentaje de cada píxel dentro de la cuenca, con el aforo de San Gil y los siete pluviómetros" width="1088" height="1376"></div>
    <figcaption>
      <h3>Figura 2 · Píxeles de IMERG sobre la cuenca</h3>
      <p>IMERG trabaja con píxeles de 0.1° (unos 11 km de lado). La lluvia de cada cuenca es el promedio de los píxeles que la
      tocan, ponderado por la fracción de cada píxel que cae dentro (el número rotulado).</p>
      <dl class="lista-datos">
        <dt>Píxeles que tocan la cuenca</dt><dd>{n_pix}</dd>
        <dt>Con más de la mitad dentro</dt><dd>{n_mitad}</dd>
        <dt>Totalmente dentro</dt><dd>{n_llenos}</dd>
        <dt>Lluvia media anual</dt><dd>{n(p_dmin)}–{n(p_dmax)} mm/año (píxeles con más de la mitad dentro)</dd>
      </dl>
      <p>Según IMERG, llueve más en el valle del oeste (unos 2 400 mm/año) que en el páramo del sureste (cerca de 2 000 mm/año).</p>
      <p class="aviso">Hay que tomarlo con cautela. IMERG estima la lluvia con satélites y la corrige con pluviómetros, y en esta cuenca
      no hay ningún pluviómetro por encima de 2 625 m, así que la parte alta del gradiente no tiene con qué contrastarse.</p>
      <p class="nota">Las subcuencas pequeñas quedan cubiertas por muy pocos píxeles: Monchía (167 km²) y Mogoticos (185 km²) tienen
      apenas el área de un píxel y medio de IMERG (cada píxel mide unos 122 km² a esta latitud), así que IMERG no puede ver variaciones de la lluvia dentro de ellas.</p>
    </figcaption>
  </figure>
  </div>
  <div role="tabpanel" id="panel-era5" aria-labelledby="pestana-era5" hidden>
  <figure>
    <div class="placa"><img src="{img('era5land_pixeles.png')}" alt="Grilla de píxeles de ERA5-Land sobre la cuenca, coloreados por la temperatura media del aire a 2 m entre 1998 y 2022, con el valor de cada píxel rotulado" width="1088" height="1376"></div>
    <figcaption>
      <h3>Figura 3 · Píxeles de ERA5-Land sobre la cuenca</h3>
      <p>La temperatura del aire a 2 m sale de <b>ERA5-Land</b>, el reanálisis del ECMWF, en píxeles de 0.1° igual que IMERG.
      Cada número es la temperatura media de ese píxel entre 1998 y 2022.</p>
      <dl class="lista-datos">
        <dt>Píxeles que tocan la cuenca</dt><dd>{t_npix}</dd>
        <dt>Con más de la mitad dentro</dt><dd>{t_nmitad}</dd>
        <dt>Temperatura media por píxel</dt><dd>{t_min_mitad:.1f}–{t_max_mitad:.1f} °C (píxeles con más de la mitad dentro)</dd>
        <dt>Promedio sobre la cuenca</dt><dd>{t_ponderada:.2f} °C (ponderado por área)</dd>
      </dl>
      <p><b>De un extremo al otro de la cuenca hay {t_max_mitad - t_min_mitad:.1f} °C de diferencia</b>:
      {t_max_mitad:.1f} °C en el píxel del noroeste, sobre el valle, y {t_min_mitad:.1f} °C en el del sur, sobre el
      páramo, contando solo los píxeles que tienen más de la mitad del área dentro de la cuenca. Es más de diez veces
      la diferencia entre el mes más frío y el más cálido del año, que en esta cuenca no llega a un grado. Aquí la
      temperatura la manda la altura, no el calendario, y esa es la razón de haber preferido ERA5-Land sobre ERA5: con
      los píxeles de 0.25° de ERA5 toda esta variación quedaría promediada dentro de dos o tres celdas.</p>
      <p>Compara esta pestaña con la del relieve: el patrón es el mismo mapa. Los píxeles cálidos siguen el valle del
      Fonce hacia el norte y los fríos se acumulan en la mitad sureste, que es donde el DEM pasa de 3 500 m.</p>
      <p class="nota">El promedio ponderado de este mapa da {t_ponderada:.2f} °C y la serie diaria de la cuenca da
      {t_serie_media:.2f} °C: la diferencia es de {abs(t_ponderada - t_serie_media):.2f} °C, que es el error de tomar
      el valor en el centro de cada píxel en vez de dejar que Earth Engine lo integre sobre el polígono. Sirve como
      chequeo de que el mapa y la serie están hablando del mismo dato.</p>
      <p class="nota">Contando también los píxeles que solo rozan la cuenca, el rango llega a
      {t_min_px:.1f}–{t_max_px:.1f} °C, pero esos valores describen sobre todo terreno de afuera: el más cálido de
      todos apenas tiene un 6 % de su área dentro de la divisoria.</p>
      <p class="aviso">La malla de ERA5-Land tiene el mismo paso que la de IMERG pero está <b>corrida medio píxel</b>:
      sus centros caen en múltiplos exactos de 0.1° y los de IMERG en los terminados en 0.05°. Por eso son
      {t_npix} píxeles aquí y {n_pix} allá, y por eso las dos cuadrículas no se superponen.</p>
    </figcaption>
  </figure>
  </div>
</section>
<script>
(function () {{
  const pestanas = [...document.querySelectorAll('[role="tab"]')];
  function activar(p, enfocar) {{
    pestanas.forEach(t => {{
      const activa = t === p;
      t.setAttribute("aria-selected", activa);
      t.tabIndex = activa ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !activa;
    }});
    if (enfocar) p.focus();
  }}
  pestanas.forEach((t, i) => {{
    t.addEventListener("click", () => activar(t));
    t.addEventListener("keydown", e => {{
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const j = (i + (e.key === "ArrowRight" ? 1 : pestanas.length - 1)) % pestanas.length;
      activar(pestanas[j], true);
    }});
  }});
}})();
</script>

<section>
  <h2>Comparando PI con PL</h2>
  <p>Se comparan las dos fuentes de lluvia del proyecto: <b>PI</b>, la precipitación de IMERG, que el
  satélite estima como promedio de celdas de unos 100 km², y <b>PL</b>, la que miden en el suelo los
  <b>{len(DENTRO)} pluviómetros</b> del IDEAM dentro de la divisoria (portal DHIME, datos
  <b>preliminares</b>). Los pluviómetros aparecen tenues, uno a uno, y su promedio mensual (PL) a plena
  opacidad; cada mes se promedia con los que tengan dato, sin rellenar ninguno.</p>
  <p class="aviso"><b>De PL se excluyen los años 2016, 2017 y 2018 de Encino</b> ({exc_meses} meses), en
  todos los análisis. Sus totales anuales saltan a {n(enc_raros[2016])}, {n(enc_raros[2017])} y
  {n(enc_raros[2018])} mm, cuando el resto de su serie ronda los {n(enc_normal)}, y vuelven a su nivel en
  2019. Nada más acompaña ese salto: con esos años, PL sale {exc_2017['crudo']:+.1f} % sobre su promedio en
  2017 mientras PI sale {exc_2017['pi']:+.1f} %; sin ellos, PL queda en {exc_2017['depurado']:+.1f} %, y el
  caudal de esos años es normal o bajo. Se trata como un problema de
  registro de la estación.</p>
  <p class="nota">La precipitación CHIRPS que trae CAMELS-COL se retiró: no aporta un punto de vista
  independiente de las otras dos y arrastra los huecos del caudal.</p>
  <div class="tabla-caja">
  <table>
    <thead><tr><th>Fuente comparada con IMERG</th><th class="num">Meses comparables</th><th class="num">IMERG (mm/mes)</th>
    <th class="num">La otra fuente (mm/mes)</th><th class="num">Diferencia de IMERG</th><th class="num">Correlación mensual</th></tr></thead>
    <tbody>
{filas_cmp}
    </tbody>
  </table>
  </div>
  <div class="dos-graficos">
    <div>
      <h3>Serie mensual, {mes_ini} a {mes_fin}</h3>
      <div id="g-series" class="grafico"></div>
    </div>
    <div>
      <h3>Ciclo anual medio</h3>
      <div id="g-ciclo" class="grafico"></div>
    </div>
  </div>
  <p class="nota">Las dos figuras comparten la leyenda de arriba. Pasa el cursor por encima para ver los
  valores de un mes; arrastra sobre el gráfico para acercarte y haz doble clic para volver.</p>
  <p><b>Las dos fuentes cuentan la misma historia con distinta magnitud.</b> Coinciden en el ciclo anual
  —bimodal, con picos en abril-mayo y en octubre— y mes a mes (correlación
  {cmp_stats[NOM_RED]["r"]:.2f}), pero <b>PI queda un {abs(cmp_stats[NOM_RED]["sesgo"]):.1f}% por debajo de
  PL</b>: {n(cmp_stats[NOM_RED]["imerg"])} contra {n(cmp_stats[NOM_RED]["pluv"])} mm/mes, lo esperable en
  lluvia orográfica de montaña, que los satélites tienden a subestimar. Los pluviómetros sueltos difieren
  mucho entre sí ({n(min(v["pluv"] for k, v in cmp_stats.items() if k != NOM_RED))} a
  {n(max(v["pluv"] for k, v in cmp_stats.items() if k != NOM_RED))} mm/mes), porque la lluvia cambia de
  ladera a ladera; por eso se usa su promedio y no una estación suelta.</p>

  <div class="revision" data-etiqueta="Revisión · PI contra PL, mes a mes">
  <h3>Mes a mes, uno contra otro</h3>
  <p>Que las dos fuentes suban y bajen juntas no quiere decir que midan lo mismo: <b>correlación no es
  concordancia</b>. Puestas una contra otra, con la línea en que serían iguales, la diferencia se ve en cada mes:
  en el {p2_pipl["debajo_pct"]:.0f} % de los {p2_pipl["n"]} meses PI queda por debajo de PL.</p>
  <div class="cifras" style="margin-bottom:14px">
    <div class="cifra"><b>{p2_pipl["sesgo"]:+.1f} mm/mes</b><span>sesgo medio (PI − PL)</span></div>
    <div class="cifra"><b>{p2_pipl["mae"]:.1f} mm/mes</b><span>error absoluto medio (MAE)</span></div>
    <div class="cifra"><b>{p2_pipl["rmse"]:.1f} mm/mes</b><span>raíz del error cuadrático medio (RMSE)</span></div>
  </div>
  <div id="g-pi-pl" class="grafico" style="min-height:0; height:460px; max-width:560px"></div>
  <p class="nota">Cada punto es un mes, coloreado según el mes del calendario. El sesgo conserva el signo del
  error; el MAE es el tamaño típico de la diferencia, con el signo que sea, y el RMSE pesa más las diferencias
  grandes. Que el MAE sea mucho mayor que el sesgo dice que, además de quedarse corto en promedio, PI se aleja
  de PL hacia los dos lados según el mes.</p>
  </div>
  <p class="aviso"><b>En la mayoría de los cálculos se usan las dos, PI y PL, y se reportan en paralelo;
  cuando haya que escoger, manda PL</b>, porque son medidas reales de lluvia en la cuenca y no una
  estimación indirecta. Se tiene presente su límite: son {len(DENTRO)} puntos sin validar para
  {n(AREA_SG_KM2)} km² de montaña, y ninguno llega al páramo. PI sirve de contraste, con la ventaja de cubrir
  toda la cuenca y los {len(comp)} meses sin huecos.</p>
</section>

<section>
  <h2>Qué meses tienen dato y cuáles no</h2>
  <p>Antes de analizar nada hay que ver dónde están los huecos. Cada franja es un mes de una fuente. El
  color no es un sí o un no: es el <b>porcentaje de días del mes con registro</b>, para las series que
  vienen en paso diario. Así se distingue un mes completo de uno al que le faltan tres días, cosa que un
  mapa de dos colores esconde.</p>
  <p class="nota">Las variables llevan las siglas que se usan en todo el informe: <b>PI</b>, la
  precipitación de IMERG promediada sobre la cuenca; <b>PL</b>, la de los pluviómetros del IDEAM dentro de
  la divisoria (su promedio, o cada uno); <b>Q</b>, el caudal en San Gil, y <b>ETP</b>, la
  evapotranspiración potencial, calculada por el proyecto con Hargreaves y ERA5-Land (ver «La
  evapotranspiración potencial (ETP)»).</p>
  <p>La regla del proyecto acepta un mes al que le falten <b>{MAX_DIAS_FALTANTES} días o menos</b>. Pero
  cuatro días sueltos no son lo mismo que cuatro seguidos, así que el detalle de cada mes dice también
  <b>cuántos de los días faltantes son consecutivos</b>. Pasa el cursor por cualquier franja, y arrastra
  sobre el gráfico para ampliar un tramo.</p>

  <div id="g-calidad" class="grafico" style="min-height:{150 + 26 * len(cal_filas)}px"></div>
  <p class="nota">Las fuentes de paso mensual (IMERG y los pluviómetros del IDEAM) solo pueden estar o no
  estar: se pintan del verde pleno o del rojo pleno, sin valores intermedios. Los meses excluidos de PL
  aparecen vacíos: {exc_lista} (ver «Comparando PI con PL» y «Anomalías en las series»).</p>

  <div class="tabla-caja">
  <table>
    <thead><tr><th>Fuente</th><th>Paso</th><th class="num">Meses utilizables</th>
    <th class="num">…de ellos, incompletos</th><th class="num">Meses perdidos</th>
    <th class="num">Cobertura</th></tr></thead>
    <tbody>
{filas_disp}
    </tbody>
  </table>
  </div>
  <p class="nota">«Incompletos» son meses que entran al análisis pero a los que les falta entre 1 y
  {MAX_DIAS_FALTANTES} días. «Perdidos» son los que la regla descarta, más los que no existen.</p>
  <p>De las {len(cal_resumen)} fuentes, <b>{cal_completas} no pierden ni un mes</b>: las de malla —IMERG y
  ERA5-Land— y los pluviómetros que el IDEAM tiene completos. No dependen de que alguien vaya a leer un
  instrumento todos los días. La que menos meses conserva es <b>{html.escape(" y ".join(n.split(" · ")[-1] for n in cal_peores))}</b>
  ({cal_min_usables} de {cal_total}), y le siguen <b>las {len(cal_camels)} series que vienen de CAMELS-COL</b>,
  con {cal_camels[0]["usables"]} cada una.</p>

  <p>El caudal de San Gil conserva {cal_q["usables"]} meses y pierde {cal_q["perdidos"]}. Pero hay un
  dato que un mapa de dos colores no deja ver: <b>{cal_q["parciales"]} de los meses que sí entran al
  análisis están incompletos</b>, con entre 1 y {MAX_DIAS_FALTANTES} días sin registro. Son válidos según
  la regla, pero no son meses perfectos, y en el degradado se distinguen.</p>

  <p><b>Por qué {MAX_DIAS_FALTANTES} días.</b> Se probó sobre los {len(_q_completos)} meses completos de Q:
  si se les quitan {MAX_DIAS_FALTANTES} días seguidos, en cualquier posición, el caudal medio del mes se
  aleja del verdadero un {umbral_mediana:.1f} % en la mediana y hasta un {umbral_p95:.1f} % en el 95 % de
  los casos. El error crece parejo con los días que faltan, sin un salto que marque un límite natural. El
  umbral es un compromiso: con él se conservan {cal_q["usables"]} meses de Q; exigiendo meses completos
  quedarían {umbral_meses_completos}.</p>

  <p><b>Un mes incompleto no se presenta como completo.</b> En los promedios (Q en m³/s, temperatura) se
  promedian los días que hay. En los acumulados (Q en mm) el valor del mes es ese promedio por los
  días del mes. Si solo se sumaran los días con dato, los {len(_q_incompletos)} meses incompletos quedarían
  en promedio un {suma_parcial_falta.mean():.1f} % por debajo, y hasta un {suma_parcial_falta.max():.1f} %.</p>

  <p>Entre los meses que la regla descarta, el detalle importa: a
  <b>{cal_q_solo_dispersos} de {len(cal_q_rotos)}</b> les faltan días <b>dispersos</b> —ninguna racha pasa
  de {MAX_DIAS_FALTANTES} días seguidos—, mientras que el peor caso, {cal_q_racha_mes}, se queda sin
  <b>{cal_q_racha_max} días consecutivos</b>. Un mes con cinco faltantes sueltos y otro sin medio mes
  seguido caen los dos fuera por la misma regla, pero no merecen la misma desconfianza.</p>

  <p class="aviso">Las series de CAMELS-COL tienen <b>exactamente el mismo patrón</b>: el caudal y las dos
  temperaturas de MSWX fallan los mismos días, sin una sola excepción. No es casualidad: esos archivos
  omiten la fila completa de los días sin caudal, y con ella se va todo lo demás, aunque MSWX sí tenga ese
  día. <b>Los huecos de la temperatura de MSWX en CAMELS-COL no son suyos: son heredados del
  caudal.</b></p>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Control de calidad básico</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <p>Se revisaron los archivos <b>tal como se descargaron</b>, antes de procesarlos: fechas legibles y en
  orden, duplicados, unidades, códigos de faltante (−9999, −999, 9999…), valores imposibles según la física
  de cada variable y banderas de calidad. Cada variable se juzga por lo suyo: una temperatura negativa es
  posible, una lluvia o un caudal negativos no. De los {len(cc)} chequeos, <b>{cc_conteo.get("sin problemas", 0)}
  pasan sin problemas</b>, {cc_conteo.get("anotado", 0)} dejan algo anotado, {cc_conteo.get("no disponible", 0)}
  no se pueden hacer porque la fuente no trae con qué y {cc_conteo.get("revisar", 0)} queda para revisar.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Fuente</th><th>Chequeo</th><th>Resultado</th><th>Detalle</th></tr></thead>
    <tbody>
{filas_cc}
    </tbody>
  </table>
  </div>
  <p class="nota">Los chequeos corren en <code>scripts/07b_control_calidad_basico.py</code>. «Anotado» es un
  hallazgo que no es un error pero hay que tener presente; «no disponible», que la fuente no trae con qué
  hacer el chequeo.</p>
  <p><b>Las unidades se confirmaron, no se supusieron.</b> El archivo de CAMELS-COL no dice en qué viene el
  caudal, pero su caudal medio pasado a mm/día da justo el que publica su archivo de firmas: está en m³/s.
  IMERG llega en mm/h y, por las horas del mes, reproduce el archivo que usa el análisis. ERA5-Land ya viene
  en °C.</p>
  <p><b>Para revisar:</b> {html.escape(cc_revisar.detalle.iloc[0]) if len(cc_revisar) else "nada"}</p>

  <h3>Qué es cada dato</h3>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th>Fuente</th><th>Tipo</th><th>Cómo se obtiene</th><th>¿Relleno?</th></tr></thead>
    <tbody>
{filas_naturaleza}
    </tbody>
  </table>
  </div>
  <p>Solo Q y PL vienen de un instrumento en la cuenca, y ninguno tiene valores rellenados: sus huecos se
  quedan como huecos. PI es una estimación satelital, T la salida de un modelo y la ETP se calcula a partir
  de él. Que no tengan huecos no quiere decir que sean exactas: un modelo o un algoritmo siempre da un
  número.</p>
  </details>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Anomalías en las series</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <div class="revision" data-etiqueta="Revisión · anomalías en las series">
  <p>Si un dato es posible no quiere decir que la serie sea coherente en el tiempo. Un cambio de estación, de
  instrumento o de producto deja un <b>escalón</b>: desde cierta fecha la serie mide sistemáticamente más o
  menos que sus vecinas. Para buscarlo, cada serie se compara con una referencia: cada pluviómetro con el
  promedio de los demás, y PI y Q con PL.</p>
  <ul class="tratamiento">
    <li><b>Curva de doble masa:</b> el acumulado de la serie contra el de la referencia. Si miden lo mismo en
    proporción es una recta; un salto la quiebra.</li>
    <li><b>Prueba de Pettitt</b> ({CITA_PETTITT}): busca el punto que mejor parte la razón serie/referencia en
    dos niveles y da la probabilidad <i>p</i> de que eso ocurra por azar. Es significativo si <i>p</i> &lt; 0.05.</li>
  </ul>
  <p>Una estación con un salto contaminaría la referencia de sus vecinas, así que se prueba por rondas: la
  peor se aparta de las referencias y se vuelven a probar las demás. Los pluviómetros se revisan sobre la
  serie como estaba antes de estas decisiones, sin el tramo de Encino ya excluido.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Serie</th><th>Referencia</th><th class="num">Meses</th><th class="num">Primer mes del 2.º tramo</th>
    <th class="num">p</th><th class="num">Razón antes</th><th class="num">Razón después</th><th class="num">Cambio</th></tr></thead>
    <tbody>
{filas_an}
    </tbody>
  </table>
  </div>
  <p class="nota">Razón: la mediana de serie/referencia en cada tramo. Las pruebas corren en
  <code>scripts/07c_anomalias.py</code>.</p>
  <div id="g-doble-masa" class="grafico" style="min-height:0; height:460px"></div>
  <p class="nota">Elige la serie en el menú. Línea punteada: la proporción constante entre el primer y el
  último mes. El rombo marca el comienzo del segundo tramo cuando el salto es significativo.</p>

  <p><b>{len(an_pl_ok)} de los {len(an_pl)} pluviómetros no tienen salto.</b> Los que sí:</p>
  <ul class="tratamiento">
    <li><b>Pueblo Viejo</b> mide {an_pv.razon_antes:.2f} veces lo que sus vecinos antes de
    {fecha_anomala(an_pv.primer_mes_despues)}, y {an_pv.razon_despues:.2f} desde entonces (<i>p</i>
    {fmt_p_eq(an_pv.p)}). Es un problema de registro del primer tramo: sus vecinos no lo acompañan. <b>Ese tramo
    sale de PL.</b></li>
    {"".join(f"<li><b>{html.escape(s.split(' · ')[1])}</b>: {c:+.0f} % desde {fecha_anomala(pm)} (<i>p</i> {fmt_p_eq(p)}), pero año por año no se ve un escalón limpio. <b>Se conserva, marcado como incierto.</b></li>" for s, c, pm, p in an_pl_sig[an_pl_sig.serie != "PL · Pueblo Viejo"][["serie", "cambio_pct", "primer_mes_despues", "p"]].itertuples(index=False))}
  </ul>
  <div class="revision" data-etiqueta="Revisión · segundo salto de Pueblo Viejo y salto de PI">
  <p><b>Pueblo Viejo tiene un segundo salto.</b> La prueba de Pettitt encuentra un solo corte por serie, así
  que a cada pluviómetro con salto se le repitió en el tramo que queda después del primero, sobre la serie
  depurada y contra el {html.escape(an_pv2.referencia)}. Pueblo Viejo pasa de {an_pv2.razon_antes:.2f} a
  {an_pv2.razon_despues:.2f} veces sus vecinos desde {fecha_anomala(an_pv2.primer_mes_despues)}
  ({an_pv2.cambio_pct:+.0f} %, <i>p</i> {fmt_p_eq(an_pv2.p)}).
  {" ".join(f"{html.escape(s.split(' · ')[1])} no tiene un segundo salto (<i>p</i> {fmt_p_eq(p)})." for s, p in an_seg_sin_salto.p.items())}
  Como en Coromoro, no hay forma de saber cuál de los dos tramos de Pueblo Viejo está bien. <b>Se conserva,
  marcado como incierto:</b> PL puede estar algo baja desde ese mes.</p>
  <p><b>PI frente a PL: {an_pi.cambio_pct:+.0f} % desde {fecha_anomala(an_pi.primer_mes_despues)}</b> (<i>p</i>
  {fmt_p_eq(an_pi.p)}): antes PI era {an_pi.razon_antes:.2f} veces PL, después {an_pi.razon_despues:.2f}. El corte
  cae en el cambio de era de IMERG: hasta mayo de 2014 se calibra con el satélite TRMM, y desde el 1 de junio
  de 2014 con GPM ({CITA_IMERG_DOC}). Pero cae también {an_meses_pv2_pi} meses después del segundo salto de
  Pueblo Viejo, que baja PL. Con una {html.escape(an_pi_sin.referencia)}, el salto de PI es de
  {an_pi_sin.cambio_pct:+.0f} % (<i>p</i> {fmt_p_eq(an_pi_sin.p)})
  {"y deja de ser significativo: buena parte del salto viene de Pueblo Viejo, no de IMERG. El cambio de TRMM a GPM puede aportar algo, pero no es la explicación principal." if not an_pi_sin.significativo else "y sigue siendo significativo: el cambio de TRMM a GPM sigue siendo una explicación posible."}
  PI se conserva, marcado como incierto; en lo que hay que escoger, manda PL. <b>Q frente a PL</b> no tiene
  salto (<i>p</i> {fmt_p_eq(an_q.p)}).</p>
  <p class="nota">El catálogo del IDEAM no guarda historia de reubicaciones ni de cambios de instrumento: de
  cada estación solo da la fecha de instalación, todas anteriores a 1998, y el estado. Los saltos de los
  pluviómetros no se pueden confirmar ni descartar con metadatos. El cambio de calibración de IMERG sí está
  documentado, pero no basta para atribuirle el salto de PI. Las pruebas del segundo salto corren en
  <code>scripts/07c_anomalias.py</code> y quedan en <code>out/anomalias_segundo_corte.csv</code>.</p>
  </div>

  <h3>Meses en 0 mm</h3>
  <div class="tabla-caja">
  <table class="sin-destacar" style="min-width:0">
    <thead><tr><th>Pluviómetro</th><th>Mes</th><th class="num">Mínimo de los demás (mm)</th>
    <th class="num">Promedio de los demás (mm)</th><th class="num">PI (mm)</th><th>Decisión</th></tr></thead>
    <tbody>
{filas_ceros}
    </tbody>
  </table>
  </div>
  <p>Un mes sin una gota en un pluviómetro, mientras todos los demás midieron al menos 20 mm, es más
  probablemente una planilla vacía que un mes sin lluvia. Esos {len(an_ceros_fuera)} se tratan como no
  registrados. Los {len(an_ceros_quedan)} restantes se conservan, porque algún vecino también midió casi
  nada.</p>

  <h3>Secuencias constantes, picos aislados y cobertura</h3>
  <p>{"No hay" if an_rachas_dia.empty else f"Hay {len(an_rachas_dia)}"} tramos de 5 días o más con el mismo
  valor exacto en Q o en la temperatura, que es la huella de un instrumento trabado o de un dato copiado, y
  {"ningún día" if an_picos.empty else f"{len(an_picos)} día" + ("" if len(an_picos) == 1 else "s")} de Q que triplique a
  sus dos vecinos. En los pluviómetros hay {len(an_rachas_pl)} pares de
  meses seguidos con el mismo total, que no cambian nada. Cuando a PL le falta algún pluviómetro
  ({len(an_cob)} meses), su valor se aleja del de los 7 un {an_sesgo.median():.1f} % en la mediana y un
  {an_sesgo.max():.1f} % como máximo. Se estima en los meses en que están los 7, con el mismo grupo de
  estaciones presentes. Queda como incertidumbre declarada; no se corrige.</p>
{nota_enso.replace("sin color, ninguno de los dos", "en negrita sin color, ninguno de los dos")}
  <p class="aviso"><b>Con todas las exclusiones, PI queda un {abs(sesgo_pi_pl):.1f} % por debajo de PL.</b> Los
  tramos excluidos: {exc_lista}.</p>
  </div>
  </details>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Registro de anomalías</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <div class="revision" data-etiqueta="Revisión · registro de anomalías">
  <p>Todo lo que apareció raro en los datos, en un solo lugar: qué se comprobó, qué se decidió, qué efecto
  tiene en el análisis y en qué estado quedó. De las {len(reg)} anomalías, <b>{reg_conteo.get("corregido", 0)}
  quedaron corregidas</b> (se excluyó el tramo o se cambió la fuente o el cálculo), <b>{reg_conteo.get("incierto", 0)}
  quedan inciertas</b> (el dato se conserva, pero no hay forma de saber si está bien, y la duda se arrastra) y
  {reg_conteo.get("descartado", 0)} se descartaron (se revisaron y no eran un problema).</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>#</th><th>Estado</th><th>Serie</th><th>Anomalía</th><th>Comprobación</th><th>Decisión</th><th>Efecto</th></tr></thead>
    <tbody>
{filas_reg}
    </tbody>
  </table>
  </div>
  <p class="nota">El registro lo arma <code>scripts/07d_trazabilidad.py</code> a partir de lo que producen los
  demás scripts, así que sus cifras cambian si cambian los datos.</p>
  </div>
  </details>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Las cuatro variables, en números</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <p>El resumen de las cuatro variables mensuales con que trabaja el proyecto, en San Gil: <b>PI</b>, la
  precipitación de IMERG promediada sobre la cuenca ponderando cada celda por su área; <b>PL</b>, la
  precipitación de la red de {len(DENTRO)} pluviómetros del IDEAM dentro de la divisoria; <b>Q</b>, el
  caudal, y la temperatura de ERA5-Land en sus tres versiones: <b>T media</b>, <b>T máx</b> y <b>T mín</b>,
  cada una el promedio mensual del valor diario correspondiente.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Estadístico</th><th class="num">PI (mm/mes)</th><th class="num">PL (mm/mes)</th>
    <th class="num">Q (m³/s)</th><th class="num">T media (°C)</th>
    <th class="num">T máx (°C)</th><th class="num">T mín (°C)</th></tr></thead>
    <tbody>
{filas_resumen}
    </tbody>
  </table>
  </div>
  <h3>Cómo se reparte cada variable a lo largo del año</h3>
  <p>Un diagrama de caja por variable, con una caja por mes del calendario: cada caja reúne ese mes en
  todos los años del período.</p>
  <div class="pestanas" role="tablist" aria-label="Variable" id="pestanas-cajas"></div>
  <div id="g-cajas" class="grafico" style="min-height:0; height:420px"></div>
  <p class="nota">Caja: del percentil 25 al 75. Línea dentro de la caja: la mediana. Bigotes: hasta 1.5 veces
  el rango intercuartil. Puntos, a la izquierda de cada caja: todos los meses, uno por año; pasa el cursor
  por encima para ver cuál es. Los cuartiles se calculan por
  interpolación lineal, igual que en la tabla.</p>

  <h3>Cómo se tratan los datos</h3>
  <ul class="tratamiento">
    <li><b>Período.</b> {PERIODOS[0]} a {PERIODOS[-1]}, {len(PERIODOS)} meses: el período en que existe
    IMERG. Toda serie se recorta a esa ventana.</li>
    <li><b>Faltantes.</b> No se rellena ni se interpola nada. Las series diarias (Q y las temperaturas) se pasan a mensual con
    una regla: un mes al que le falten {MAX_DIAS_FALTANTES + 1} días o más queda vacío, y con hasta
    {MAX_DIAS_FALTANTES} faltantes se calcula con los días que hay. PL se promedia cada mes con los
    pluviómetros que tengan dato. PI y las temperaturas no tienen huecos; Q sí.</li>
    <li><b>Unidades.</b> PI y PL en mm/mes (sumas mensuales). Q en m³/s (promedio mensual del caudal
    diario); donde se compara con la lluvia, en el resto del informe, se pasa a lámina en mm/mes
    dividiéndolo por el área de la cuenca ({n(AREA_SG_KM2)} km²). Las temperaturas, en °C (promedios
    mensuales).</li>
    <li><b>Percentiles.</b> Interpolación lineal entre los valores ordenados (método 7 de {CITA_HYNDMAN},
    el de pandas, R y Excel). La desviación estándar es la muestral.</li>
  </ul>
  </details>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Revisión de outliers</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <p>Los meses atípicos de las seis variables, con el mismo criterio de los diagramas de caja: un mes es
  atípico si se sale {FACTOR_ATIPICO:.1f} rangos intercuartiles por fuera de los cuartiles <b>de su propio
  mes del calendario</b>. Hay {atip_conteo['PI']} en PI, {atip_conteo['PL']} en PL, {atip_conteo['Q']} en Q,
  {atip_conteo['T media']} en T media, {atip_conteo['T máx']} en T máx y {atip_conteo['T mín']} en T mín.
  La tabla pone todas las variables de esos meses lado a lado, para ver qué pasó con las demás cuando
  una se salió de lo normal.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Mes</th>{"".join(f"<th class='num'>{html.escape(v)}</th>" for v in VARS_ATIP)}</tr></thead>
    <tbody>
{filas_atip}
    </tbody>
  </table>
  </div>
  <p class="nota">Cada número es cuánto se aleja el valor de la mediana de su mes, en rangos intercuartiles
  (+2 = dos rangos intercuartiles por encima de lo normal para ese mes). En color, los atípicos: cálido si
  es alto, frío si es bajo. Para PI, PL y Q, «alto» es más agua; para las temperaturas, más calor.</p>

  <h3>Lo que conecta a los atípicos</h3>
  <ul class="tratamiento">
    <li><b>Lluvia extrema que el río confirma:</b> {lista_meses(lluvia_confirmada)}. En esos meses la lluvia
    atípica viene con caudal por encima de lo normal (z ≥ {UMBRAL_RESPUESTA:.0f}) en el mismo mes o el
    siguiente. Meses secos confirmados de la misma forma: {lista_meses(seco_confirmado)}.
    <p class="lectura">{lectura_enso_lluvia}</p></li>
    <li><b>Posibles errores de PI:</b> {lista_meses(error_pi)}. Solo el satélite se sale de lo normal; la red
    está dentro de ±1 y el río no acompaña. Son el tipo de mes en que conviene creerle a PL.</li>
    <li><b>Un caso que no cumple el criterio pero salta a la vista: {fecha_enso(_F99)}.</b> Es el febrero
    más lluvioso del período en PL ({n(feb99['PL']['valor'])} mm, {(feb99['PL']['valor'] / feb99['PL']['segundo'] - 1) * 100:.0f} %
    más que el segundo) y en PI ({n(feb99['PI']['valor'])} mm, {(feb99['PI']['valor'] / feb99['PI']['segundo'] - 1) * 100:.0f} %
    más que el segundo), pero se queda a {feb99['PL']['factor']:.2f} y {feb99['PI']['factor']:.2f} rangos
    intercuartiles del percentil 75, por debajo del umbral de {FACTOR_ATIPICO:.1f}. Medido como en la tabla,
    desde la mediana de los febreros, de hecho sí es bastante alto: PI está {atip_z.loc[_F99, "PI"]:+.1f} y
    PL {atip_z.loc[_F99, "PL"]:+.1f} rangos intercuartiles por encima de lo normal para febrero.
    {"El caudal de ese mes sí fue atípico. " if feb99_q_atipico else ""}Vale la pena tenerlo en cuenta como
    evento extremo.</li>
    <li class="revision" data-etiqueta="Revisión · enero y febrero de 2005"><b>Enero y febrero de 2005: la emergencia
    invernal en Santander.</b> La Defensoría del Pueblo documentó una emergencia invernal en el primer bimestre de
    2005, con Santander entre los departamentos más golpeados: inundaciones, la avalancha del río de Oro y la
    declaratoria de calamidad pública en Bucaramanga y Girón. Según el IDEAM, citado en ese documento, las lluvias,
    atípicas para la época, se debieron a cuatro frentes fríos del hemisferio norte, cuando entre enero y febrero
    normalmente ocurren uno o dos ({CITA_DEFENSORIA}). En la cuenca, enero de 2005 estuvo
    {ene05["z_pl"]:+.1f} rangos intercuartiles sobre lo normal para enero en PL, {ene05["z_pi"]:+.1f} en PI y
    {ene05["z_q"]:+.1f} en Q; febrero, {ene05["z_pl_feb"]:+.1f}, {ene05["z_pi_feb"]:+.1f} y {ene05["z_q_feb"]:+.1f}.
    Enero de 2005 salía como atípico de PL ({n(ene05["pl"])} mm) antes de excluir el primer tramo de Pueblo Viejo:
    el umbral de enero era {n(ene05["umbral_antes"])} mm y hoy es {n(ene05["umbral_hoy"])} mm. El valor del mes
    no cambió; subió el umbral, porque ese tramo, que medía cerca de la cuarta parte que sus vecinos, bajaba los
    eneros de 1998 a 2004. El documento no nombra la cuenca del Fonce, así que no se puede confirmar que esas lluvias
    fueran las mismas que se ven aquí.</li>
    <li><b>Caudal atípico sin lluvia atípica:</b> {lista_meses(q_sin_lluvia)}. Ni ese mes ni el anterior la
    lluvia fue atípica, pero sí estuvo sobre lo normal (z de PL hasta
    {", ".join(f"{v:+.1f}" for v in q_sin_lluvia_zpl.values())}): el río acumula varios meses húmedos
    seguidos, la memoria de la cuenca que se vio en «Cómo se relacionan las variables entre sí».</li>
    <li><b>Noches cálidas en meses secos:</b> los {len(t_min_alta)} meses con T mín atípicamente alta son
    {lista_meses(t_min_alta)}, y en ellos PL estuvo en promedio en
    {_media_z(t_min_alta, "PL"):+.1f} y Q en {_media_z(t_min_alta, "Q"):+.1f}: menos lluvia y menos caudal
    de lo normal.</li>
    <li><b>Días frescos en meses lluviosos, y al revés:</b> cuando T máx fue atípicamente baja
    ({lista_meses(t_max_baja)}), PL estuvo en promedio en {_media_z(t_max_baja, "PL"):+.1f}; cuando fue
    atípicamente alta ({lista_meses(t_max_alta)}), en {_media_z(t_max_alta, "PL"):+.1f}.
    Un mes lluvioso es un mes nublado, con menos sol de día.</li>
  </ul>
{nota_enso}
  </details>
</section>

<section>
  <h2>Dos fuentes de temperatura, y por qué se usa ERA5-Land</h2>
  <p>La cuenca no tiene <b>ninguna estación que mida temperatura</b>, así que toda viene de productos de
  malla. Hay dos:</p>

  <div class="tabla-caja">
  <table>
    <thead><tr><th>&nbsp;</th><th>MSWX (vía CAMELS-COL)</th><th>ERA5-Land</th></tr></thead>
    <tbody>
      <tr><td>Naturaleza</td><td><b>reanálisis corregido contra observaciones</b></td><td>reanálisis, sin corrección</td></tr>
      <tr><td>Resolución</td><td>0.1°</td><td>0.1°</td></tr>
      <tr><td>Días con dato</td><td class="num">{n(t_dias_mswx)}</td><td class="num">{n(t_dias_era)}</td></tr>
      <tr><td>Variables que llegan</td><td>mínima y máxima</td><td>media, mínima y máxima</td></tr>
      <tr><td>T media del período</td><td class="num">{tc.mswx_media.mean():.2f} °C</td><td class="num">{tc.era_media.mean():.2f} °C</td></tr>
      <tr><td>Amplitud diaria media</td><td class="num">{t_amp_mswx:.2f} °C</td><td class="num">{t_amp_era:.2f} °C</td></tr>
      <tr><td>Malla disponible</td><td>no, llega promediada por cuenca</td><td>sí, {len(t_grad)} celdas</td></tr>
    </tbody>
  </table>
  </div>

  <p><b>MSWX sale {t_sesgo_media:.2f} °C más cálido</b>, pero las dos siguen el mismo día a día
  (r = {t_r:.2f}). La separación es casi constante en toda la distribución ({t_sesgo_p5:+.2f} °C en el
  percentil 5, {t_sesgo_p95:+.2f} °C en el 95), y el ciclo anual es plano en las dos: aquí manda la
  altura, no la estación del año.</p>

  <div id="g-temp-ciclo" class="grafico" style="min-height:420px"></div>
  <p class="nota">Línea gruesa: mediana de cada mes. Banda: del percentil 10 al 90 de los días de ese mes.
  Se comparan los {n(t_n)} días en que existen las dos.</p>

  <h3>Por qué se elige ERA5-Land</h3>
  <ul class="tratamiento">
    <li><b>Trae la media diaria de verdad.</b> De MSWX, CAMELS-COL solo publica mínima y máxima, y el punto
    medio (mínima + máxima) ÷ 2 sobreestima la media: medido dentro de ERA5-Land, le suma
    {t_sesgo_metodo:+.2f} °C. Parte de la diferencia entre las dos fuentes es ese atajo.</li>
    <li><b>No tiene huecos:</b> los {len(PERIODOS)} meses completos. MSWX hereda los del caudal.</li>
    <li><b>Tenemos su malla</b>, así que se promedia sobre la divisoria ponderando por área, igual que
    IMERG.</li>
  </ul>

  <p class="aviso">Lo que se pierde: MSWX está corregido contra estaciones y ERA5-Land no
  ({CITA_BECK}), y ERA5-Land suaviza el relieve: con la altura baja {t_grad_por_km:.2f} °C por cada 1 000 m
  (r² = {t_grad_r2:.2f}, {len(t_grad_nucleo)} celdas ponderadas), cuando lo esperable ronda
  {GRADIENTE_FISICO:.1f} °C/km. Sin termómetros en la cuenca no hay forma de saber cuál acierta. MSWX se conserva
  para repetir cualquier cálculo con la otra fuente.</p>
</section>

<section>
  <h2>La evapotranspiración potencial (ETP)</h2>
  <p><b>Qué es y de dónde sale.</b> La ETP es el agua que evaporaría y transpiraría un pasto bien regado
  con el clima de cada día. No se mide, se calcula, y no es la evapotranspiración real de la cuenca.
  CAMELS-COL publica una, calculada con el método de Hargreaves ({CITA_HARGREAVES}) a partir de la
  temperatura de MSWX ({CITA_JIMENEZ}, ecuación 1):</p>
  <p class="formula">ETP = 0.0023 · R<sub>a</sub> · (T + 17.8) · √(T<sub>máx</sub> − T<sub>mín</sub>) &nbsp;&nbsp;[mm/día]</p>
  <p class="nota">T = (T<sub>máx</sub> + T<sub>mín</sub>) / 2, en °C. R<sub>a</sub> es la radiación que llega al
  tope de la atmósfera: depende solo de la latitud y del día del año, se calcula con las ecuaciones 21 a 25
  de FAO-56 ({CITA_FAO}) y se pasa a mm/día multiplicándola por 0.408.</p>
  <p><b>La recalculamos</b> con esa misma fórmula (<code>scripts/06b_etp_hargreaves.py</code>), dos veces: con
  la temperatura de MSWX, la misma que usó CAMELS-COL, y con la de ERA5-Land, la del proyecto. La latitud
  es la del centroide del polígono ({etp_lat:.2f}° N).</p>

  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>ETP</th><th class="num">mm/año</th><th class="num">CAMELS-COL ÷ esta</th>
    <th class="num">r mensual con CAMELS-COL</th></tr></thead>
    <tbody>
      <tr><td>CAMELS-COL, publicada</td><td class="num">{n(etp_anual.camels)}</td><td class="num">—</td><td class="num">—</td></tr>
      <tr><td>Hargreaves con MSWX (recalculada)</td><td class="num">{n(etp_anual.mswx)}</td><td class="num">{etp_cociente.median():.2f}</td><td class="num">{etp_r_camels_mswx:.2f}</td></tr>
      <tr><td>Hargreaves con ERA5-Land (del proyecto)</td><td class="num">{n(etp_anual.era)}</td><td class="num">{(etp_comun.camels / etp_comun.era).median():.2f}</td><td class="num">{etp_comun.camels.corr(etp_comun.era):.2f}</td></tr>
    </tbody>
  </table>
  </div>
  <p class="nota">Promedios sobre los {len(etp_comun)} meses en que las tres tienen dato; el cociente es la
  mediana de los cocientes mes a mes.</p>
  <div id="g-etp" class="grafico" style="min-height:0; height:420px"></div>

  <p><b>La ETP de CAMELS-COL no cuadra con su propia fórmula.</b> Sale {etp_cociente.median():.2f} veces la
  de Hargreaves con MSWX, y ese factor casi no cambia de un mes a otro (entre {etp_cociente.min():.2f} y
  {etp_cociente.max():.2f}): es la misma cuenta multiplicada por una constante. No es solo un error de
  unidades en R<sub>a</sub>: si se hubiera dejado en MJ m⁻² día⁻¹, el factor sería {etp_cociente_mj:.2f}. No
  se pudo identificar la causa.</p>
  <p><b>¿Está mal nuestra R<sub>a</sub>?</b> No. Se comprobó de tres formas. Coincide con el ejemplo 8 de FAO-56
  (20° S, 3 de septiembre: 32.2 MJ m⁻² día⁻¹). Coincide con integrar minuto a minuto la radiación que llega
  al tope de la atmósfera; estas dos comprobaciones van dentro de <code>06b_etp_hargreaves.py</code>, que se
  detiene si fallan. Y, al revés, para obtener la ETP de CAMELS-COL con su fórmula haría falta una
  R<sub>a</sub> media de {etp_ra_implicita.mean():.1f} mm/día, cuando en el tope de la atmósfera, a
  {etp_lat:.1f}° N, nunca pasa de {etp_ra_max:.1f} mm/día ({etp_ra_max / 0.408:.1f} MJ m⁻² día⁻¹). Esa
  R<sub>a</sub> imposible tiene la misma forma estacional que la nuestra (el cociente va de
  {etp_ra_cociente_mes.min():.2f} a {etp_ra_cociente_mes.max():.2f} según el mes), así que no es un error de
  latitud ni de fecha: es un factor de escala.</p>
  <p><b>El valor recalculado es el plausible.</b> Los {n(etp_anual.mswx)} a {n(etp_anual.era)} mm/año caen en
  el rango de 1 200 a 1 400 mm/año que el propio artículo de CAMELS-COL da para Colombia, según el IDEAM
  ({CITA_JIMENEZ}), y quedan por encima de lo que la cuenca pierde en el balance (PL − Q =
  {n(etp_pl_menos_q)} mm/año), como corresponde si la evapotranspiración real no supera a la potencial. Los
  {n(etp_anual.camels)} mm/año de CAMELS-COL{" superan incluso a la lluvia (PL = " + n(etp_pl_anual) + " mm/año)" if etp_anual.camels > etp_pl_anual else ""}.</p>
  <p><b>Con MSWX o con ERA5-Land da casi lo mismo</b> ({etp_era_vs_mswx:+.1f} %, r = {etp_r_era_mswx:.2f} mes a
  mes), aunque ERA5-Land es más fría: también tiene más amplitud diaria, y en la fórmula de Hargreaves las
  dos cosas se compensan.</p>
  <p class="aviso"><b>La ETP de este informe es Hargreaves con ERA5-Land</b>, la calculada por el proyecto.
  La que publica CAMELS-COL no se usa en ningún cálculo.</p>
</section>

<section>
  <h2>Cómo se relacionan las variables entre sí</h2>
  <p>Las {len(VARIABLES_CORR)} variables mensuales de la cuenca, cruzadas todas contra todas sobre los
  <b>{corr_n} meses en que todas tienen dato</b>. Además de PI, PL y Q entran <b>ETP</b>, la
  evapotranspiración potencial mensual de Hargreaves con ERA5-Land, y las dos temperaturas, <b>T MSWX</b> y <b>T ERA5</b>. Se usa la muestra común y no la propia de cada par
  para que los coeficientes de la matriz sean comparables entre sí.</p>

  <p class="nota">Se muestra <b>solo el coeficiente de Spearman</b>, que mide la correlación sobre los
  rangos en vez de sobre los valores: no supone que la relación sea una recta y no se deja arrastrar por
  unos pocos meses extremos, que es lo prudente con variables meteorológicas. En estos datos apenas
  cambia la lectura —la mayor distancia entre Spearman y Pearson en toda la matriz es de
  {corr_dif_max:.2f}—, así que quedarse con la robusta no cuesta nada.</p>

  <div class="pestanas" role="tablist" aria-label="Qué series comparar">
    <button type="button" role="tab" id="pestana-crudas" aria-controls="panel-corr" aria-selected="true">Series tal cual</button>
    <button type="button" role="tab" id="pestana-anomalias" aria-controls="panel-corr" aria-selected="false" tabindex="-1">Anomalías (sin el ciclo anual)</button>
    <button type="button" role="tab" id="pestana-rezago" aria-controls="panel-corr" aria-selected="false" tabindex="-1">Un mes de rezago</button>
  </div>
  <div role="tabpanel" id="panel-corr" aria-labelledby="pestana-crudas">
    <div id="g-corr-matriz" class="grafico" style="min-height:860px"></div>
  </div>
  <p class="nota">Cómo leer la matriz: en la <b>diagonal</b>, cómo se reparte cada variable; <b>debajo</b>,
  la nube de puntos de cada par, donde cada punto es un mes; <b>encima</b>, el coeficiente de ese mismo
  par, en azul si suben y bajan juntas y en naranja si van al revés.</p>
  <p class="nota"><b>Los paneles están enlazados.</b> Arrastra sobre cualquiera de ellos para marcar un
  grupo de meses y esos mismos meses se resaltan en todos los demás: sirve para seguir, por ejemplo, a
  dónde van a parar los meses más lluviosos en el resto de las variables. Doble clic para soltar la
  selección. <span id="corr-seleccion" style="color:var(--acento)"></span></p>

  <h3>Qué dicen</h3>
  <p><b>Las dos fuentes de lluvia concuerdan</b>: ρ = {rho('PI', 'PL'):.2f} entre PI y PL. Conviene no
  leer eso como una confirmación mutua, porque <b>no son del todo independientes</b>: IMERG incorpora
  ajuste con redes de estaciones parecidas a la que forma PL, así que parte del acuerdo viene de cómo
  están construidas.</p>

  <p><b>El caudal se lleva mejor con los pluviómetros que con el satélite</b>: ρ = {rho('PL', 'Q'):.2f}
  contra {rho('PI', 'Q'):.2f}. La diferencia no es enorme, pero va siempre en el mismo sentido y apunta a
  que la red mide algo que el satélite se pierde. Es un dato que pesa sobre la decisión de arrastrar las
  dos fuentes en paralelo: en su relación con el caudal no están empatadas.</p>

  <div class="revision" data-etiqueta="Revisión · dispersión de la lluvia contra el caudal">
  <p><b>Con más lluvia, el caudal es menos predecible.</b> En las nubes de lluvia contra caudal, los puntos se
  abren a medida que llueve más: ajustando una recta, la varianza de lo que la recta no explica es
  {p2_dispersion["PL"]:.1f} veces mayor en el tercio de meses más lluviosos que en el más seco con PL, y
  {p2_dispersion["PI"]:.1f} veces con PI. Un mes muy lluvioso puede dar caudales muy distintos, lo que es
  coherente con que el caudal dependa también del agua que la cuenca trae guardada de los meses anteriores.</p>
  </div>

  <p><b>Las dos temperaturas se mueven juntas</b>, ρ = {rho('T MSWX', 'T ERA5'):.2f}, pese a los
  {t_sesgo_media:.2f} °C que las separan. Discrepan en el nivel, no en el movimiento.</p>

  <h3>Lo que solo se ve al quitar el ciclo anual</h3>
  <p>Cambia a la pestaña de anomalías y mira las casillas de la lluvia contra la temperatura y la
  evapotranspiración. Esas relaciones <b>se refuerzan</b> al restarle a cada variable su propio ciclo
  anual, que es lo contrario de lo que suele pasar. El caso más marcado es
  <b>{html.escape(corr_par_salto[0])} con {html.escape(corr_par_salto[1])}</b>, que pasa de
  ρ = {rho(*corr_par_salto):.2f} a <b>{rho(*corr_par_salto, anomalias=True):.2f}</b>. También
  {corr_tambien}. No es general: PL con Q, el par cuyos ciclos anuales sí van juntos
  (ρ = {corr_ciclo_rho.loc['PL', 'Q']:.2f}), no se refuerza sino que se debilita un poco ({rho('PL', 'Q'):.2f}
  a {rho('PL', 'Q', anomalias=True):.2f}): donde no hay dilución, quitar el ciclo no agrega nada.</p>
  <p>La razón está en el tamaño de los ciclos. <b>La lluvia tiene un ciclo anual enorme y la temperatura
  casi no tiene</b>: las doce medias mensuales explican el {corr_peso_ciclo['PI']:.0f} % de la
  variación mensual de PI y el {corr_peso_ciclo['PL']:.0f} % de la de PL, pero solo el
  {corr_peso_ciclo['T ERA5']:.0f} % de la de T ERA5. Y esos ciclos <b>no tienen relación entre sí</b>
  (primera columna de la tabla): la temporada de lluvias no coincide ni con los meses cálidos ni con
  los fríos. En las series tal cual, esa gran oscilación estacional de la lluvia, sin contraparte en la
  temperatura, <b>diluye</b> la relación. Al quitarla queda solo la diferencia de cada mes con lo normal
  para ese mes, y ahí aparece el vínculo, negativo y físicamente esperable: <b>un mes más lluvioso de lo
  normal es un mes más nublado</b>, y por eso más fresco y con menos evapotranspiración potencial.</p>

  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Par</th><th class="num">ρ entre los ciclos anuales (12 medias)</th>
    <th class="num">ρ series tal cual</th><th class="num">ρ anomalías</th></tr></thead>
    <tbody>
{filas_ciclo}
    </tbody>
  </table>
  </div>
  <p class="nota">La fuerza del efecto depende de la fuente de temperatura. Con ERA5-Land la relación
  ya asoma en las series tal cual (Q – T ERA5, ρ = {rho('Q', 'T ERA5'):.2f}); con MSWX desaparece del
  todo (PL – T MSWX, ρ = {rho('PL', 'T MSWX'):+.2f}) y solo se ve en las anomalías.</p>
  <h3>Con un mes de rezago</h3>
  <p>La tercera pestaña cruza cada variable en un mes con cada variable en el <b>mes siguiente</b>, sobre
  los {corr_n_rezago} pares de meses consecutivos en que las seis tienen dato. La matriz ya no es
  simétrica: cada casilla es la correlación entre la variable de la <b>columna en el mes t</b> y la de la
  <b>fila en el mes t+1</b>, y la diagonal dice cuánto se parece cada variable a sí misma un mes después.</p>
  <p class="nota">Esta pestaña usa las series tal cual, así que mezcla la respuesta de la cuenca con el
  desfase de los ciclos anuales. La pregunta de si Q responde a la lluvia con un mes de rezago se
  contesta mejor abajo.</p>

  <h3>¿Cuánto condiciona el ciclo de la lluvia al ciclo del caudal?</h3>
  <p>El año típico lo dice a simple vista: PL tiene sus picos en <b>{pico_pl[0]} y {pico_pl[1]}</b>, y Q en
  <b>{pico_q[0]} y {pico_q[1]}</b>. Para medirlo, el ciclo de Q se reconstruye con la lluvia: primero solo
  con la del mismo mes, después con la del mes y la del mes anterior.</p>

  <div id="g-ciclo-rezago" class="grafico" style="min-height:0; height:420px"></div>
  <p class="nota">Barras: PL media de cada mes. Línea negra: Q observado. Líneas punteadas: Q
  <b>predicho a partir de PL</b>, no medido (ajuste lineal sobre las 12 medias mensuales, así que es una descripción de la forma
  del ciclo, no una prueba estadística fuerte).</p>

  <p><b>Con la lluvia del mes sola, el ciclo de Q sale adelantado</b> y explica el
  {ajuste_lq.loc[('PL', 'mes'), 'r2'] * 100:.0f} % de su forma. <b>Sumándole la del mes anterior, explica el
  {ajuste_lq.loc[('PL', 'mes_y_anterior'), 'r2'] * 100:.0f} %</b> y los picos caen donde deben. En ese ajuste el
  caudal de cada mes toma cerca del {peso_mes_pl * 100:.0f} % de su señal de la lluvia de ese mes y el
  {(1 - peso_mes_pl) * 100:.0f} % de la del anterior: <b>el ciclo de PL condiciona el de Q, con un mes de
  arrastre</b>. Con PI el ajuste es más pobre ({ajuste_lq.loc[('PI', 'mes'), 'r2'] * 100:.0f} % →
  {ajuste_lq.loc[('PI', 'mes_y_anterior'), 'r2'] * 100:.0f} %): el ciclo del satélite se parece menos al del
  caudal que el de los pluviómetros.</p>

  <p class="aviso">Una correlación mensual no es ni causa ni capacidad de predicción. Que Q y PL vayan a
  ρ = {rho('PL', 'Q'):.2f} no quiere decir que la lluvia de un mes explique el caudal de ese mes. <b>La
  relación entre lluvia y caudal tiene memoria</b>, y una correlación en la misma casilla temporal no la
  captura; las correlaciones con un mes de rezago, arriba, muestran una parte.</p>
</section>

<section>
  <h2>Lo que le cae a la cuenca y lo que sale por el río</h2>
  <p class="nota">De aquí en adelante, y en todo el informe, tres siglas: <b>PI</b> es la precipitación de
  IMERG (satélite) promediada sobre la cuenca, <b>PL</b> la precipitación de los pluviómetros del IDEAM
  (el promedio de las {len(DENTRO)} estaciones de la red) y <b>Q</b> el caudal.</p>
  <p>El caudal se mide en m³/s y la lluvia en milímetros, así que no se pueden comparar de frente.
  Dividiendo el caudal por el área de la cuenca ({n(AREA_SG_KM2)} km²) queda también como lámina de agua,
  en mm: lo que sale por el río, repartido sobre toda la cuenca. Así entran los dos en el mismo eje, sin
  necesidad de ejes dobles que engañan la lectura.</p>
  <div class="cifras" style="margin: 18px 0 6px">
    <div class="cifra"><b>{n(bal_p_anual)} mm/año</b><span>lluvia (PI), en los meses con caudal</span></div>
    <div class="cifra"><b>{n(bal_q_anual)} mm/año</b><span>caudal</span></div>
    <div class="cifra"><b>{coef_periodo:.2f}</b><span>coeficiente de escorrentía</span></div>
    <div class="cifra"><b>{bal_n}</b><span>meses con ambos datos</span></div>
  </div>
  <div id="g-balance" class="grafico" style="min-height:400px"></div>
  <div id="g-escorrentia" class="grafico" style="min-height:0; height:300px"></div>
  <p class="nota">La franja azul es la lluvia; la línea naranja, el caudal. Donde el caudal se interrumpe
  es porque ese mes no cumple la regla de los cuatro días faltantes.</p>
  <p><b>Sale como caudal cerca del {coef_periodo * 100:.0f} % de la lluvia.</b> El resto se evapora o se
  queda almacenado en el suelo. Es un valor alto, pero razonable en una cuenca andina húmeda y empinada.
  La distancia entre las dos curvas se angosta en las temporadas húmedas: cuando el suelo ya está mojado,
  una fracción mayor de la lluvia se convierte en caudal.</p>
  <p class="nota"><b>CAMELS-COL confirma este número por su cuenta.</b> Su archivo de firmas
  hidrológicas publica para San Gil un <code>runoff_ratio</code> de
  {float(firmas_sg.runoff_ratio):.2f} y un caudal medio de {float(firmas_sg.q_mean):.2f} mm/día, es decir
  {n(float(firmas_sg.q_mean) * 365)} mm/año. Nosotros obtuvimos {coef_periodo:.2f} y
  {n(bal_q_anual)} mm/año por un camino distinto —agregando la serie diaria con la regla del proyecto y
  dividiendo por el área—, así que los dos cálculos coinciden.</p>

  <div class="revision" data-etiqueta="Revisión · coeficiente con PL y PI">
  <p class="aviso">Meses en que salió más agua de la que cayó (coeficiente &gt; 1): <b>{bal_sobre1_pl} con PL</b>
  (máximo {bal_max_pl:.2f} en {fmt_mes(bal_max_mes_pl)}) y {bal_sobre1} con PI (máximo {bal_max:.2f} en
  {fmt_mes(bal_max_mes)}). Con PL, {bal_pl_tras_lluvia} de los {bal_sobre1_pl} vienen después de dos meses más
  lluviosos que lo normal: es agua guardada que sale después. Con PI son más porque PI mide menos lluvia.</p>
  </div>

  <div class="revision" data-etiqueta="Revisión · P − Q contra la evapotranspiración">
  <h3>Lo que llueve menos lo que sale, contra la evapotranspiración</h3>
  <p>Lo que llueve (P) se reparte en lo que sale por el río (Q), lo que se evapora y transpira y lo que la
  cuenca guarda o libera del suelo y del acuífero. Por eso <b>P − Q no es la evapotranspiración</b>: mes a
  mes incluye el almacenamiento. Aquí se compara con la ETP de Hargreaves (ver «La evapotranspiración
  potencial (ETP)»), con las dos fuentes de lluvia.</p>
  <div id="g-pq-mensual" class="grafico" style="min-height:0; height:380px"></div>
  <p>Mes a mes, P − Q oscila mucho más que la ETP. Con PL supera a la ETP en {pq_res["pl"]["sobre_etp"]} de
  {pq_n_meses} meses: en el año típico, en {", ".join(pq_meses_guarda)}, que es cuando la cuenca guarda agua. En
  {pq_res["pl"]["negativo"]} meses sale más agua de la que cae (P − Q &lt; 0); con PI son {pq_res["pi"]["negativo"]}.
  Eso no es un error: es el río drenando lo que la cuenca guardó.</p>
  <div id="g-pq-anual" class="grafico" style="min-height:0; height:340px"></div>
  <p>En el año, el almacenamiento casi se cancela. Sobre los {pq_n_anios} años con los 12 meses de caudal,
  PL − Q promedia {n(pq_res["pl"]["anual"])} mm/año y PI − Q {n(pq_res["pi"]["anual"])}, contra una ETP de
  {n(pq_etp_anual)} mm/año. {"Ningún año pasa de la ETP, como corresponde si la evapotranspiración real no supera a la potencial." if not pq_anios_sobre["pl"] and not pq_anios_sobre["pi"] else f"P − Q supera a la ETP en {pq_res['pl']['anios_sobre_etp']} años con PL ({', '.join(pq_anios_sobre['pl']) or 'ninguno'}) y en {pq_res['pi']['anios_sobre_etp']} con PI{' (' + ', '.join(pq_anios_sobre['pi']) + ')' if pq_anios_sobre['pi'] else ''}. Como P − Q = ET + ΔS + otras salidas, el agua que sobra pudo:"}</p>
  {"" if not pq_anios_sobre["pl"] and not pq_anios_sobre["pi"] else pq_explicaciones}
  </div>
</section>

<section>
  <h2>El ciclo anual</h2>
  <div class="revision" data-etiqueta="Revisión · ciclo anual, mes a mes">
  <h3>Cada mes del calendario, y cuánto cambia de un año a otro</h3>
  <p>El <b>ciclo anual</b> es cómo se comporta cada variable en cada mes del calendario, separado de la
  variabilidad de un año a otro: se juntan todos los eneros, todos los febreros…, de 1998 a 2022, y se resume
  cada mes. La media y la mediana dicen cómo es el mes típico; la desviación estándar y el rango entre p10 y
  p90 dicen cuánto cambia ese mes de un año a otro.</p>
  <div class="pestanas" role="tablist" aria-label="Variable del ciclo anual">
    <button type="button" role="tab" id="pestana-ciclo-pl" aria-controls="panel-ciclo-pl" aria-selected="true">PL (mm/mes)</button>
    <button type="button" role="tab" id="pestana-ciclo-pi" aria-controls="panel-ciclo-pi" aria-selected="false" tabindex="-1">PI (mm/mes)</button>
    <button type="button" role="tab" id="pestana-ciclo-q" aria-controls="panel-ciclo-q" aria-selected="false" tabindex="-1">Q (m³/s)</button>
    <button type="button" role="tab" id="pestana-ciclo-t" aria-controls="panel-ciclo-t" aria-selected="false" tabindex="-1">T media (°C)</button>
  </div>
  <div role="tabpanel" id="panel-ciclo-pl" aria-labelledby="pestana-ciclo-pl">
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Mes</th><th class="num">Años válidos</th><th class="num">Media</th><th class="num">Mediana</th>
    <th class="num">Desv. estándar</th><th class="num">p10</th><th class="num">Q1 (p25)</th><th class="num">Q3 (p75)</th>
    <th class="num">p90</th></tr></thead>
    <tbody>
{ciclo_tablas["pl"]}
    </tbody>
  </table>
  </div>
  </div>
  <div role="tabpanel" id="panel-ciclo-pi" aria-labelledby="pestana-ciclo-pi" hidden>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Mes</th><th class="num">Años válidos</th><th class="num">Media</th><th class="num">Mediana</th>
    <th class="num">Desv. estándar</th><th class="num">p10</th><th class="num">Q1 (p25)</th><th class="num">Q3 (p75)</th>
    <th class="num">p90</th></tr></thead>
    <tbody>
{ciclo_tablas["pi"]}
    </tbody>
  </table>
  </div>
  </div>
  <div role="tabpanel" id="panel-ciclo-q" aria-labelledby="pestana-ciclo-q" hidden>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Mes</th><th class="num">Años válidos</th><th class="num">Media</th><th class="num">Mediana</th>
    <th class="num">Desv. estándar</th><th class="num">p10</th><th class="num">Q1 (p25)</th><th class="num">Q3 (p75)</th>
    <th class="num">p90</th></tr></thead>
    <tbody>
{ciclo_tablas["q"]}
    </tbody>
  </table>
  </div>
  </div>
  <div role="tabpanel" id="panel-ciclo-t" aria-labelledby="pestana-ciclo-t" hidden>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Mes</th><th class="num">Años válidos</th><th class="num">Media</th><th class="num">Mediana</th>
    <th class="num">Desv. estándar</th><th class="num">p10</th><th class="num">Q1 (p25)</th><th class="num">Q3 (p75)</th>
    <th class="num">p90</th></tr></thead>
    <tbody>
{ciclo_tablas["t"]}
    </tbody>
  </table>
  </div>
  </div>
  <p class="nota">Años válidos: años con dato ese mes (Q con la regla de los 5 días faltantes; PL con sus
  exclusiones). Q es el promedio mensual del caudal diario, en m³/s; T media, la de ERA5-Land. Desviación
  estándar muestral; cuartiles y percentiles por interpolación lineal ({CITA_HYNDMAN}).</p>
  <script>
  (() => {{
    const botones = document.querySelectorAll('[id^="pestana-ciclo-"]');
    botones.forEach(b => b.addEventListener("click", () => {{
      botones.forEach(o => {{
        const activo = o === b;
        o.setAttribute("aria-selected", activo ? "true" : "false");
        o.tabIndex = activo ? 0 : -1;
        document.getElementById(o.getAttribute("aria-controls")).hidden = !activo;
      }});
    }}));
  }})();
  </script>
  </div>

  <div class="revision" data-etiqueta="Revisión · régimen del ciclo anual">
  <h3>El régimen: picos, temporadas, concentración y forma</h3>
  <p>Con la <b>mediana</b> de cada mes del calendario se describe el régimen de PL, PI y Q. El <b>mes típico</b> es el
  promedio de las 12 medianas: un mes es <b>húmedo</b> si su mediana lo supera y <b>seco</b> si no, y las temporadas
  son las rachas de meses seguidos (diciembre y enero cuentan como seguidos). La <b>concentración</b> es la parte de
  la suma de las medianas que cae en los meses húmedos. Q va en mm/mes: sumar caudales medios en m³/s no da un
  volumen, y en mm/mes las tres series quedan en la misma unidad. La <b>forma</b> sale de los dos primeros armónicos de Fourier, el de 12 meses (A₁) y el de 6 meses
  (A₂) ({CITA_HORN}): si A₂ domina, el ciclo tiene dos picos, y los picos se cuentan sobre la curva ajustada con esos
  dos armónicos. Si hay estacionalidad lo dice la prueba de Kruskal-Wallis entre los 12 meses ({CITA_KRUSKAL}).</p>
  <p><b>Clasificación:</b> estacionalidad débil si Kruskal-Wallis no es significativa (<i>p</i> ≥ {ALFA_KW}); si no,
  bimodal si la curva ajustada tiene dos picos; si no, unimodal.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Indicador</th><th>PL</th><th>PI</th><th>Q</th></tr></thead>
    <tbody>
{reg_filas}
    </tbody>
  </table>
  </div>
  <p><b>El régimen es {" y ".join(reg_clases)}{" en las tres series" if len(reg_clases) == 1 else ""}.</b> Kruskal-Wallis
  rechaza que los 12 meses sean iguales con <i>p</i> de {reg_kw_max:.0e} o menos. Con PL los picos caen en
  {" y ".join(regimen["PL"]["picos"])}, con PI en {" y ".join(regimen["PI"]["picos"])} y con Q en
  {" y ".join(regimen["Q"]["picos"])}. Los porcentajes de concentración de PI y PL no se comparan directamente: con PI
  hay {regimen["PI"]["conc_meses"]} meses húmedos y con PL, {regimen["PL"]["conc_meses"]}.</p>
  </div>

  <div class="revision" data-etiqueta="Revisión · desfase estacional">
  <h3>Desfase estacional: cuánto se atrasa el río respecto a la lluvia</h3>
  <p>Cada armónico es una onda, y su <b>fase</b> dice en qué momento del año está su máximo. Con el armónico de
  6 meses, que da la forma de dos picos, el <b>desfase estacional</b> es cuánto después llega el máximo de Q que el
  de la lluvia. Se mide sobre el año típico (las mismas medianas del régimen), así que da el atraso en días aunque
  los datos sean mensuales. La incertidumbre sale de remuestrear años completos {f"{DES_REMUESTREOS:,}".replace(",", " ")} veces.</p>
  <div class="cifras" style="margin-bottom:18px">
    <div class="cifra"><b>{desfase["Q_PL"]:.0f} días</b><span>Q después de PL · IC 95 % {desfase_ic["Q_PL"][0]:.0f} a {desfase_ic["Q_PL"][1]:.0f}</span></div>
    <div class="cifra"><b>{desfase["Q_PI"]:.0f} días</b><span>Q después de PI · IC 95 % {desfase_ic["Q_PI"][0]:.0f} a {desfase_ic["Q_PI"][1]:.0f}</span></div>
    <div class="cifra"><b>{desfase["PI_PL"]:.0f} días</b><span>PI después de PL · IC 95 % {desfase_ic["PI_PL"][0]:.1f} a {desfase_ic["PI_PL"][1]:.1f}</span></div>
  </div>
  <p><b>Con las dos fuentes, el río va atrasado respecto a la lluvia</b>, mucho más que el tiempo de
  concentración, que va de {desfase_tc[0]:.0f} a {desfase_tc[1]:.0f} horas según la fórmula. El atraso del año
  típico no es el tiempo de viaje del agua por el cauce: apunta a agua que se guarda en el suelo y el acuífero y
  sale después. <b>La fuente cambia poco el resultado:</b> el ciclo de PI tiene sus máximos {desfase["PI_PL"]:.0f}
  días después que el de PL, y en esa misma cantidad el desfase con PI sale más corto. El intervalo de esa
  diferencia va de {desfase_ic["PI_PL"][0]:.1f} a {desfase_ic["PI_PL"][1]:.1f} días
  ({(("excluye el cero por muy poco" if desfase_ic["PI_PL"][0] < 1 else "no incluye el cero") + ", y es pequeña frente a la resolución mensual de los datos") if desfase_dif_concluyente else "incluye el cero: la diferencia entre fuentes no es concluyente"}).</p>
  <p class="nota">La fase del armónico de 12 meses no se usa: en PL y en Q explica el {regimen["PL"]["var1"]:.0f} % y el
  {regimen["Q"]["var1"]:.0f} % de la forma del ciclo, y su fase es casi ruido.</p>
  </div>

  <h3>Mes a mes: correlación cruzada entre la lluvia y el caudal</h3>
  <p>Comparando la lluvia de cada mes con el caudal de ese mes, del siguiente y del anterior, en toda la
  serie: la correlación es máxima en el mismo mes (ρ = {rho_cruzada('PL', 0, 'tal cual'):.2f} con PL) y sigue
  alta con la lluvia un mes antes ({rho_cruzada('PL', 1, 'tal cual'):.2f}), mientras que con el caudal un
  mes antes cae a {rho_cruzada('PL', -1, 'tal cual'):.2f}: la relación va de la lluvia al caudal, y dura un
  mes. A tres meses de distancia la correlación es negativa ({rho_cruzada('PL', 3, 'tal cual'):.2f} y
  {rho_cruzada('PL', -3, 'tal cual'):.2f}): es el mismo ciclo visto de otro lado, porque con dos temporadas al
  año, tres meses de corrimiento enfrentan la temporada de lluvias con la seca.</p>
  <p class="nota">¿Es solo el calendario? No del todo. Quitándole a cada serie su ciclo anual medio, la
  lluvia del mes anterior sigue aportando: la correlación parcial con Q, descontada la lluvia del mes, es
  {memoria.loc['PL', 'parcial_mes_anterior']:.2f}. La cuenca guarda agua de un mes al siguiente también en
  los años que se salen de lo normal.</p>

  <h3>El año típico: cuándo llueve y cuándo baja el río</h3>
  <p>Promediando cada mes del calendario a lo largo del período se ve el <b>año típico</b> de la cuenca.
  Aquí van las tres series juntas: la lluvia según el satélite, la lluvia según la red de pluviómetros y
  el caudal, todas en mm/mes. Las tres se promedian sobre los mismos <b>{ciclo_n} meses</b>, los que
  tienen dato en las tres a la vez; si cada una usara su propia muestra las curvas no serían comparables
  de frente.</p>

  <div id="g-ciclo-anual" class="grafico" style="min-height:420px"></div>

  <p><b>El régimen es bimodal</b>, como corresponde a los Andes colombianos: dos temporadas de lluvia
  separadas por dos secas. La primera lluviosa va de marzo a junio, la segunda de septiembre a diciembre.
  El mes más seco es {ciclo_valle_imerg}, y el caudal toca fondo un mes después, en {ciclo_valle_q}.</p>

  <div class="cifras" style="margin: 18px 0 6px">
    <div class="cifra"><b>{ciclo_pico_imerg}</b><span>pico de lluvia · IMERG</span></div>
    <div class="cifra"><b>{ciclo_pico_red}</b><span>pico de lluvia · red</span></div>
    <div class="cifra"><b>{ciclo_pico_q}</b><span>pico de caudal</span></div>
    <div class="cifra"><b>{ciclo_valle_q}</b><span>caudal mínimo</span></div>
  </div>

  <p>Las dos fuentes de lluvia tienen la misma forma bimodal: la red pone sus picos en
  {ciclo_picos_red[0]} y {ciclo_picos_red[1]}, y el satélite en {ciclo_picos_imerg[0]} y {ciclo_picos_imerg[1]}.
  Se separan sobre todo en la magnitud: la red mide más que el satélite en {ciclo_meses_red_mayor} de los 12
  meses, que es el sesgo del {abs(cmp_stats[NOM_RED]['sesgo']):.1f} % ya conocido.
  {"<b>Para decidir cuándo pasan las cosas en esta cuenca, da igual cuál de las dos se use.</b>" if ciclo_picos_red == ciclo_picos_imerg else "En el calendario difieren a lo sumo en un mes de pico."}</p>

</section>

<section>
  <h2>¿Sirve la lluvia para estimar el caudal?</h2>
  <div class="revision" data-etiqueta="Revisión · estimación fuera del período de ajuste">
  <p>Hasta aquí, el caudal sigue a la lluvia del mismo mes y arrastra algo del anterior. La prueba más exigente
  de esa relación es usarla para <b>estimar el caudal en años que el ajuste no vio</b>. Se ajusta una recta del
  caudal contra la lluvia con {EV_AJUSTE[0][:4]}–{EV_AJUSTE[1][:4]} y se evalúa con {EV_VALIDACION[0][:4]}–{EV_VALIDACION[1][:4]}. Los
  dos bloques son continuos, para que meses vecinos, que se parecen entre sí, no queden uno en cada lado. La
  referencia es la <b>climatología</b>: el caudal medio de cada mes del calendario en el bloque de ajuste.
  Superarla quiere decir que la lluvia dice algo del caudal que el calendario solo no dice.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Estimación del caudal con…</th><th class="num">RMSE en el ajuste (m³/s)</th>
    <th class="num">RMSE en la evaluación (m³/s)</th><th class="num">MAE en la evaluación</th>
    <th class="num">Sesgo en la evaluación</th><th class="num">Meses evaluados</th></tr></thead>
    <tbody>
{ev_filas}
    </tbody>
  </table>
  </div>
  <div id="g-evaluacion" class="grafico" style="min-height:0; height:380px"></div>
  <p><b>La mejor estimación sale de {ev_mejor}</b>: en los años de evaluación se equivoca en
  {ev_tabla[ev_mejor]["validacion"]["rmse"]:.1f} m³/s (RMSE), contra {ev_rmse_clima:.1f} de la climatología.
  Con PI del mismo mes el error es de {ev_tabla["PI del mismo mes"]["validacion"]["rmse"]:.1f} m³/s: otra vez los
  pluviómetros le ganan al satélite. Con la lluvia del mes anterior sola el error es mayor
  ({ev_tabla["PL del mes anterior"]["validacion"]["rmse"]:.1f} con PL), como se espera de un río que responde sobre
  todo dentro del mismo mes. Ninguna estimación da caudales negativos.</p>
  <p><b>¿Y corregir PI con una recta contra PL?</b> Ajustada con los mismos años, la corrección deja un error de
  {ev_correccion["ols"]["rmse"]:.1f} mm/mes en la evaluación, contra {ev_correccion["sin"]["rmse"]:.1f} de PI sin
  corregir: casi no gana nada. Es otro argumento para no corregir PI y llevar las dos fuentes en paralelo.</p>
  <p class="nota">Una recta mensual simplifica mucho: no representa el agua guardada en el suelo, la humedad
  que trae la cuenca ni el tránsito por el cauce, y superar la climatología no prueba causalidad. Además,
  IMERG incorpora datos de pluviómetros, así que PI y PL no son del todo independientes.</p>
  </div>
</section>

<section>
  <h2>En esta cuenca llueve menos arriba</h2>
  <p>Al ordenar los pluviómetros por altura aparece algo que va contra la intuición: las dos estaciones
  más altas de la red miden <b>menos</b> lluvia que varias del valle. <b>{html.escape(grad_mas_alta.nombre_corto)}</b>,
  a {n(grad_mas_alta.altitud)} m, registra {n(grad_mas_alta.p_anual_mm)} mm/año, mientras que
  <b>{html.escape(grad_mas_lluviosa.nombre_corto)}</b>, {n(grad_mas_alta.altitud - grad_mas_lluviosa.altitud)} m
  más abajo, registra {n(grad_mas_lluviosa.p_anual_mm)} mm/año. Con siete estaciones eso podría ser
  casualidad, así que hay que contrastarlo con algo independiente.</p>

  <p>Ese algo es <b>IMERG cruzado contra el DEM</b>: para cada celda del satélite que toca la cuenca se
  promedia la altitud del modelo de elevación dentro de ella. Son {aj_imerg['n']} celdas, y entran todas
  al ajuste, cada una con un peso igual a la fracción de su área que cae dentro de la cuenca: las que
  apenas rozan la divisoria cuentan poco. Es una muestra más densa y que no sabe nada de dónde están los
  pluviómetros. <b>Las dos fuentes coinciden en el signo.</b></p>

  <div class="cifras" style="margin: 18px 0 6px">
    <div class="cifra"><b>{aj_imerg['por_1000m']:+,.0f} mm/año</b><span>por cada 1 000 m · IMERG</span></div>
    <div class="cifra"><b>r² = {aj_imerg['r2']:.2f}</b><span>IMERG, {aj_imerg['n']} celdas</span></div>
    <div class="cifra"><b>{aj_plu['por_1000m']:+,.0f} mm/año</b><span>por cada 1 000 m · pluviómetros</span></div>
    <div class="cifra"><b>r² = {aj_plu['r2']:.2f}</b><span>pluviómetros, {aj_plu['n']} estaciones</span></div>
  </div>

  <div id="g-gradiente" class="grafico" style="min-height:460px"></div>
  <p class="nota">Cada punto azul es una celda de IMERG, más grande cuanto más de su área cae dentro de la
  cuenca (ese es su peso en el ajuste); cada punto naranja, un pluviómetro. El círculo hueco es la
  estación que cae fuera de la divisoria. Pasa el cursor por encima para ver el detalle.</p>

  <h3>Las mismas estaciones, apartando las dos que no encajan</h3>
  <p>Dos estaciones se salen de la tendencia y tiran de la recta naranja.
  <b>{html.escape(grad_mas_lluviosa.nombre_corto)}</b> mide muy por encima de lo que le correspondería
  —aun sin su tramo 2016-2018, que ya está excluido— y
  <b>{html.escape(grad_mas_seca.nombre_corto)}</b> mide {n(grad_mas_seca.p_anual_mm)} mm/año a
  {n(grad_mas_seca.altitud)} m, es decir <b>menos que {html.escape(grad_mas_alta.nombre_corto)}</b>, que está
  {n(grad_mas_alta.altitud - grad_mas_seca.altitud)} m más arriba. Ninguna explicación altitudinal admite eso.</p>

  <p>Este segundo gráfico repite el ajuste con las {aj_limpio['n']} estaciones restantes. <b>No es una
  depuración</b>: las dos apartadas siguen dibujadas, huecas, y sus datos siguen en el análisis. Es una
  comprobación de cuánto pesaban ellas dos en el desacuerdo entre las fuentes.</p>

  <div class="cifras" style="margin: 18px 0 6px">
    <div class="cifra"><b>{aj_limpio['por_1000m']:+,.0f} mm/año</b><span>por 1 000 m · {aj_limpio['n']} estaciones</span></div>
    <div class="cifra"><b>{aj_imerg['por_1000m']:+,.0f} mm/año</b><span>por 1 000 m · IMERG</span></div>
    <div class="cifra"><b>{n(grad_brecha)} mm/año</b><span>diferencia entre las dos</span></div>
    <div class="cifra"><b>{aj_plu['por_1000m']:+,.0f} mm/año</b><span>con las 7, para comparar</span></div>
  </div>

  <div id="g-gradiente-limpio" class="grafico" style="min-height:420px"></div>
  <p class="nota">Línea naranja: las {aj_limpio['n']} estaciones restantes. Línea azul: la tendencia de IMERG,
  dibujada sobre el mismo tramo de altitud para poder compararlas de frente. Los círculos huecos son las dos
  estaciones apartadas.</p>

  <p><b>Las dos rectas se acercan</b>: {aj_limpio['por_1000m']:+,.0f} mm/año por cada 1 000 m según los
  pluviómetros y {aj_imerg['por_1000m']:+,.0f} según el satélite, una diferencia de {n(grad_brecha)} mm/año, frente
  a {n(grad_brecha_7)} con las 7 estaciones. <b>Esas dos estaciones explican el {grad_parte_de_las_dos:.0f} % de
  la discrepancia</b>; el resto es una diferencia que queda entre medir en un punto y medir sobre 122 km².
  Las dos pendientes van en el mismo sentido, menos lluvia arriba, aunque con tan pocas estaciones la de los
  pluviómetros es débil (r² = {aj_limpio['r2']:.2f}).</p>

  <p class="aviso">Esto no autoriza a borrarlas. Lo de {html.escape(grad_mas_lluviosa.nombre_corto)} apunta a un
  problema de la serie y habría que revisarlo dato por dato; lo de {html.escape(grad_mas_seca.nombre_corto)}
  probablemente no sea un error sino un efecto real de exposición de ladera, que es justamente el tipo de
  detalle que IMERG borra al promediar sobre celdas de 122 km². Un promedio de la cuenca que las excluya
  estaría escondiendo información, no limpiándola.</p>

  <h3>Dónde están, y en qué subcuenca cae cada una</h3>
  <p>No están en la misma parte de la cuenca. Caen en las <b>dos subcuencas grandes de cabecera</b>, que son
  vecinas y casi gemelas: <b>{html.escape(sub_humeda.nombre_subcuenca)}</b> tiene
  {n(sub_humeda.area_subcuenca_km2)} km² y <b>{html.escape(sub_seca.nombre_subcuenca)}</b>
  {n(sub_seca.area_subcuenca_km2)} km². Comparten la divisoria que cruza el mapa en diagonal.</p>

  <figure>
    <div class="placa"><img src="{img('estaciones_subcuencas.png')}" alt="Mapa del relieve de la cuenca del Fonce con las subcuencas de Nemizaque y Puente Llano resaltadas y las siete estaciones ubicadas, junto a un diagrama de lluvia contra altitud coloreado por subcuenca"></div>
    <figcaption>
      <p>El Pienta ocupa el flanco suroccidental, más bajo y de valle ancho. El Taquiza ocupa la vertiente
      oriental, la parte más alta y escarpada de la cuenca.</p>
      <p class="nota">Relieve: DEM ALOS PALSAR. Cada estación se asigna a la subcuenca <b>más pequeña</b>
      que la contiene, porque están anidadas unas dentro de otras.</p>
    </figcaption>
  </figure>

  <p>El mapa deja ver dos cosas que los gráficos anteriores no cuentan:</p>

  <p><b>{html.escape(sub_humeda.etiqueta)} está sola.</b> Es la única estación de los
  {n(sub_humeda.area_subcuenca_km2)} km² del {html.escape(sub_humeda.nombre_subcuenca.split(' (')[1].rstrip(')'))}.
  Su valor no tiene ninguna vecina que lo confirme ni que lo desmienta, y queda muy por encima de los
  {n(sub_humeda.p_imerg_subcuenca)} mm/año que IMERG estima para esa misma subcuenca.</p>

  <p><b>{html.escape(sub_seca.etiqueta)} está rodeada, y aun así hunde.</b> Las
  {sub_seca.estaciones_en_subcuenca} estaciones del
  {html.escape(sub_seca.nombre_subcuenca.split(' (')[1].rstrip(')'))} dibujan una V:
  {" y ".join(f"{html.escape(v.etiqueta)} a {n(v.altitud)} m mide {n(v.p_anual)} mm/año" for v in vecinas_seca.itertuples())},
  mientras que {html.escape(sub_seca.etiqueta)}, entre las dos a {n(sub_seca.altitud)} m, cae a
  {n(sub_seca.p_anual)} mm/año. Es un mínimo flanqueado por dos estaciones más húmedas <b>de su propia
  subcuenca</b>, una más abajo y otra más arriba. Ningún gradiente altitudinal produce esa forma.</p>

  <p class="aviso">Y aquí está lo que más pesa: <b>IMERG ve las dos subcuencas casi idénticas</b>,
  {n(sub_humeda.p_imerg_subcuenca)} contra {n(sub_seca.p_imerg_subcuenca)} mm/año, una diferencia de
  {n(sub_brecha_imerg)} mm/año. Los pluviómetros dicen {n(sub_humeda.p_anual)} contra
  {n(sub_seca.p_anual)}: una diferencia del <b>{sub_brecha_plu * 100:.0f} %</b> sobre dos subcuencas
  contiguas, del mismo tamaño y de elevación media parecida. Eso no lo explica la altura, y deja a
  {html.escape(sub_humeda.etiqueta)} como el principal candidato a revisión dato por dato.</p>

  <h3>Por qué pasa: el óptimo pluviográfico</h3>
  <p>La lluvia no crece indefinidamente con la altura. En los valles interandinos colombianos existe una
  franja de altitud en la que la precipitación es máxima —el <b>óptimo pluviográfico</b> ({CITA_POVEDA})— y por encima de
  ella la precipitación <b>disminuye</b>. La razón es que las lluvias tropicales son sobre todo
  convectivas: a medida que el aire asciende y se enfría, su humedad absoluta y el agua precipitable
  disponible en las nubes se van agotando. El relieve sigue empujando el aire hacia arriba, pero ya no
  queda vapor que condensar.</p>

  <p>La clave para leer esta cuenca es que el Fonce va de {n(elev_min)} a {n(elev_max)} m,
  es decir <b>está entera por encima de esa franja óptima</b>. Por eso en todo su rango solo se observa la
  rama descendente de la curva: de las celdas más bajas que ve IMERG (unos {n(grad_alt_baja)} m,
  {n(grad_p_baja)} mm/año) a las más altas ({n(grad_alt_alta)} m, {n(grad_p_alta)} mm/año) se pierden unos
  <b>{n(grad_caida)} mm/año</b>. Si la cuenca bajara hasta el piso del valle del Magdalena veríamos la otra
  mitad de la curva.</p>

  <table>
    <thead><tr><th>Estación</th><th class="num">Altitud (m)</th><th class="num">Lluvia (mm/año)</th><th>Divisoria</th></tr></thead>
    <tbody>
{filas_grad}
    </tbody>
  </table>

  <p class="nota">Cuidado al usar estas pendientes. La de IMERG ({aj_imerg['por_1000m']:+,.0f} mm/año por cada
  1 000 m) y la de los pluviómetros sin las dos estaciones apartadas ({aj_limpio['por_1000m']:+,.0f}) coinciden,
  pero la de las {aj_plu['n']} estaciones completas es {aj_plu['por_1000m']:+,.0f}, casi el doble. Si en algún
  cálculo hace falta corregir la lluvia por altura, hay que declarar cuál de las tres se tomó y por qué.</p>
</section>

<section>
  <h2>Bibliografía</h2>
  <ol class="bibliografia">
    <li id="ref-allen1998">Allen, R. G., Pereira, L. S., Raes, D., y Smith, M. (1998). <i>Crop evapotranspiration:
    Guidelines for computing crop water requirements</i> (FAO Irrigation and Drainage Paper 56). FAO, Roma.
    Edición en español: <i>Evapotranspiración del cultivo</i> (Estudio FAO Riego y Drenaje 56), 2006.</li>
    <li id="ref-beck2022">Beck, H. E., et al. (2022). MSWX: Global 3-hourly 0.1° bias-corrected meteorological
    data. <i>Bulletin of the American Meteorological Society</i>.
    <a href="https://doi.org/10.1175/BAMS-D-21-0145.1">https://doi.org/10.1175/BAMS-D-21-0145.1</a></li>
    <li id="ref-defensoria2005">Defensoría del Pueblo. (2005, 16 de marzo). <i>Resolución Defensorial No. 34:
    Emergencia invernal durante el primer bimestre de 2005</i>.
    <a href="https://www.defensoria.gov.co/documents/20123/1311006/defensorial34.pdf/d9d42d31-7913-c461-c3f5-fae0651d358c?t=1648529830362&amp;download=true">defensoria.gov.co</a></li>
    <li id="ref-hargreaves1985">Hargreaves, G. H., y Samani, Z. A. (1985). Reference crop evapotranspiration from
    temperature. <i>Applied Engineering in Agriculture</i>, 1(2), 96–99.
    <a href="https://doi.org/10.13031/2013.26773">https://doi.org/10.13031/2013.26773</a></li>
    <li id="ref-horn1960">Horn, L. H., y Bryson, R. A. (1960). Harmonic analysis of the annual march of
    precipitation over the United States. <i>Annals of the Association of American Geographers</i>, 50, 157–171.
    <a href="https://doi.org/10.1111/j.1467-8306.1960.tb00342.x">https://doi.org/10.1111/j.1467-8306.1960.tb00342.x</a></li>
    <li id="ref-huffman2023">Huffman, G. J., Bolvin, D. T., Joyce, R., Kelley, O. A., Nelkin, E. J., Tan, J., Watters,
    D. C., y West, B. J. (2023, 13 de julio). <i>Integrated Multi-satellitE Retrievals for GPM (IMERG) Technical
    Documentation</i> (V07). NASA Goddard Space Flight Center.
    <a href="https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation">gpm.nasa.gov</a></li>
    <li id="ref-hyndman1996">Hyndman, R. J., y Fan, Y. (1996). Sample quantiles in statistical packages.
    <i>The American Statistician</i>, 50(4), 361–365.
    <a href="https://doi.org/10.1080/00031305.1996.10473566">https://doi.org/10.1080/00031305.1996.10473566</a></li>
    <li id="ref-jimenez2025">Jimenez, D. A., Meneses, J. E., Solha, P. H. B., Avila-Diaz, A., Quesada, B., Brentan,
    B. M., y Rodrigues, A. F. (2025). CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia.
    <i>Earth System Science Data Discussions</i> (preprint).
    <a href="https://doi.org/10.5194/essd-2025-200">https://doi.org/10.5194/essd-2025-200</a></li>
    <li id="ref-kruskal1952">Kruskal, W. H., y Wallis, W. A. (1952). Use of ranks in one-criterion variance
    analysis. <i>Journal of the American Statistical Association</i>, 47(260), 583–621.
    <a href="https://doi.org/10.2307/2280779">https://doi.org/10.2307/2280779</a></li>
    <li id="ref-noaa-oni">NOAA Climate Prediction Center. <i>Oceanic Niño Index (ONI)</i>. Descargado el
    2026-09-28. <a href="https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt">https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt</a></li>
    <li id="ref-pettitt1979">Pettitt, A. N. (1979). A non-parametric approach to the change-point problem.
    <i>Journal of the Royal Statistical Society, Series C (Applied Statistics)</i>, 28(2), 126–135.
    <a href="https://doi.org/10.2307/2346729">https://doi.org/10.2307/2346729</a></li>
    <li id="ref-poveda2004">Poveda, G. (2004). La hidroclimatología de Colombia: una síntesis desde la escala
    inter-decadal hasta la escala diurna. <i>Revista de la Academia Colombiana de Ciencias Exactas, Físicas y
    Naturales</i>, 28(107), 201–221.
    <a href="https://doi.org/10.18257/raccefyn.28(107).2004.1991">https://doi.org/10.18257/raccefyn.28(107).2004.1991</a></li>
  </ol>
  <p class="nota">Las fuentes de datos (CAMELS-COL, IMERG, ERA5-Land, IDEAM, DEM) están al pie de la página.</p>
</section>

<footer>
  <h3>Fuentes</h3>
  <ul>
    <li><b>DEM:</b> ALOS PALSAR, 12.5 m. El proyecto usa un recorte de la zona (<code>data/dem/dem_fonce_alos_12m.tif</code>).</li>
    <li><b>Polígonos, áreas y elevaciones:</b> CAMELS-COL, Zenodo, DOI <a href="https://doi.org/10.5281/zenodo.18794895">10.5281/zenodo.18794895</a>.</li>
    <li><b>Lluvia:</b> IMERG Final V07 mensual (NASA GPM), DOI <a href="https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07">10.5067/GPM/IMERG/3B-MONTH/07</a>.</li>
    <li><b>Estaciones de aforo:</b> IDEAM, a través de CAMELS-COL.</li>
    <li><b>Pluviómetros:</b> IDEAM, portal DHIME (<code>atencionciudadano.ideam.gov.co</code>), precipitación total mensual 1998–2022, nivel preliminar y definitivo.</li>
    <li><b>El Niño y La Niña:</b> ONI de la NOAA; ver la bibliografía.</li>
  </ul>
  <p style="margin-top:14px">Generado con <code>scripts/08_mapas_y_pixeles.py</code> y <code>scripts/18_reporte_html.py</code>.</p>
</footer>
<script>
(function () {{
  const D = {cmp_json};
  const MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const CONF = {{ displayModeBar: false, responsive: true }};

  function base() {{
    const tinta = css("--tinta"), tenue = css("--tenue"), linea = css("--linea");
    return {{
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: {{ family: "IBM Plex Mono, ui-monospace, monospace", size: 11, color: tinta }},
      margin: {{ t: 64, r: 10, b: 40, l: 54 }},
      hovermode: "x unified",
      legend: {{ orientation: "h", yanchor: "bottom", y: 1.04, xanchor: "left", x: 0,
                font: {{ size: 10.5 }}, itemwidth: 30, tracegroupgap: 4 }},
      xaxis: {{ gridcolor: linea, zeroline: false, linecolor: linea, tickcolor: linea,
               tickfont: {{ color: tenue }} }},
      yaxis: {{ gridcolor: linea, zeroline: false, linecolor: linea, tickcolor: linea,
               tickfont: {{ color: tenue }}, rangemode: "tozero",
               title: {{ text: "mm/mes", font: {{ size: 11, color: tenue }} }} }}
    }};
  }}


  const TEMP = {t_json};

  function dibujarTemperatura() {{
    if (!window.Plotly) return;
    const VERDE = "#009E73", MORADO = "#7C5BC7", GRIS = css("--tenue");
    const FUENTES = [
      {{ clave: "mswx", nombre: "MSWX", color: VERDE, relleno: "rgba(0,158,115,0.18)" }},
      {{ clave: "era", nombre: "ERA5-Land", color: MORADO, relleno: "rgba(124,91,199,0.18)" }}
    ];

    // --- ciclo anual: banda p10-p90 y mediana encima
    const trazas = [];
    FUENTES.forEach(f => {{
      trazas.push({{
        type: "scatter", mode: "lines", x: TEMP.meses, y: TEMP.ciclo[f.clave + "_p90"],
        line: {{ width: 0 }}, showlegend: false, hoverinfo: "skip", legendgroup: f.clave
      }});
      trazas.push({{
        type: "scatter", mode: "lines", x: TEMP.meses, y: TEMP.ciclo[f.clave + "_p10"],
        line: {{ width: 0 }}, fill: "tonexty", fillcolor: f.relleno,
        name: f.nombre + " · p10–p90", legendgroup: f.clave,
        hovertemplate: "%{{y:.1f}} °C<extra>" + f.nombre + " · p10</extra>"
      }});
      trazas.push({{
        type: "scatter", mode: "lines+markers", x: TEMP.meses, y: TEMP.ciclo[f.clave + "_p50"],
        line: {{ color: f.color, width: 2.8 }}, marker: {{ size: 7 }},
        name: f.nombre + " · mediana", legendgroup: f.clave,
        hovertemplate: "%{{y:.1f}} °C<extra>" + f.nombre + " · mediana</extra>"
      }});
    }});
    const disp = base();
    disp.margin = {{ t: 64, r: 12, b: 40, l: 58 }};
    disp.yaxis.title.text = "temperatura media diaria (°C)";
    disp.yaxis.rangemode = "normal";
    Plotly.react("g-temp-ciclo", trazas, disp, CONF);

  }}


  const CORR = {corr_json};
  let corrModo = "crudas";          // pestaña activa: "crudas", "anomalias" o "rezago"

  function dibujarCorrelaciones() {{
    if (!window.Plotly) return;
    const tenue = css("--tenue"), linea = css("--linea"), tinta = css("--tinta");
    const V = CORR.variables, n = V.length;
    const rezago = corrModo === "rezago";
    const rho = corrModo === "anomalias" ? CORR.rhoAnomalias
              : rezago ? CORR.rhoRezago : CORR.rhoCrudas;
    const datos = corrModo === "anomalias" ? CORR.anomalias : CORR.crudas;
    const AZUL = "#0072B2", NARANJA = "#D55E00";

    // Una rejilla de n x n paneles montada a mano: abajo las nubes de puntos, en la diagonal los
    // histogramas y arriba el coeficiente sobre fondo de color. Plotly no trae esta figura hecha
    // —su tipo `splom` no admite ni histogramas en la diagonal ni celdas de color—, así que se
    // reparten los dominios de los ejes y se colocan los paneles uno por uno.
    const HUECO = 0.012;
    const lado = (1 - HUECO * (n - 1)) / n;
    const dominioX = j => [j * (lado + HUECO), j * (lado + HUECO) + lado];
    const dominioY = i => [1 - (i * (lado + HUECO) + lado), 1 - i * (lado + HUECO)];
    const eje = (i, j) => i * n + j + 1;                 // número de eje de la celda (fila, columna)
    const suf = k => (k === 1 ? "" : k);

    // color de fondo del triángulo superior: naranja si la relación es negativa, azul si positiva
    const colorCelda = v => {{
      const base = v < 0 ? [213, 94, 0] : [0, 114, 178];
      const fuerza = Math.min(Math.abs(v), 1);
      const mezcla = base.map(c => Math.round(255 + (c - 255) * fuerza));
      return "rgb(" + mezcla.join(",") + ")";
    }};

    const trazas = [], formas = [], anotaciones = [];
    const indicesNubes = [];          // qué trazas son nubes de puntos, para enlazarlas
    const disposicion = {{
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: {{ family: "IBM Plex Mono, ui-monospace, monospace", size: 9, color: tenue }},
      margin: {{ t: 14, r: 14, b: 92, l: 96 }},
      showlegend: false, hovermode: "closest", bargap: 0.06, dragmode: "select"
    }};

    for (let i = 0; i < n; i++) {{
      for (let j = 0; j < n; j++) {{
        const k = eje(i, j), ex = "xaxis" + suf(k), ey = "yaxis" + suf(k);
        const esBorde = {{ abajo: i === n - 1, izquierda: j === 0 }};

        if (j > i || rezago) {{
          // triángulo superior (o, con rezago, todas las casillas): un rectángulo de color y el
          // coeficiente encima, sin ejes
          const v = rho[i][j];
          const [x0, x1] = dominioX(j), [y0, y1] = dominioY(i);
          formas.push({{ type: "rect", xref: "paper", yref: "paper", x0, x1, y0, y1,
                        fillcolor: colorCelda(v), line: {{ width: 0 }}, layer: "below" }});
          anotaciones.push({{
            xref: "paper", yref: "paper", x: (x0 + x1) / 2, y: (y0 + y1) / 2,
            text: (v > 0 ? "+" : "") + v.toFixed(2), showarrow: false,
            font: {{ size: 11 + Math.abs(v) * 9,
                    color: Math.abs(v) > 0.55 ? "#FFFFFF" : "#1A1A1A" }}
          }});
          continue;
        }}

        disposicion[ex] = {{
          domain: dominioX(j), anchor: "y" + suf(k), showgrid: false, zeroline: false,
          linecolor: linea, tickfont: {{ size: 7.5, color: tenue }}, nticks: 3,
          showticklabels: esBorde.abajo
        }};
        disposicion[ey] = {{
          domain: dominioY(i), anchor: "x" + suf(k), showgrid: false, zeroline: false,
          linecolor: linea, tickfont: {{ size: 7.5, color: tenue }}, nticks: 3,
          showticklabels: esBorde.izquierda && i !== j
        }};

        if (i === j) {{
          // diagonal: cómo se reparte cada variable
          disposicion[ey].showticklabels = false;
          trazas.push({{
            type: "histogram", x: datos[V[j]], nbinsx: 22,
            marker: {{ color: tenue, opacity: 0.55, line: {{ color: "rgba(0,0,0,0)", width: 0 }} }},
            xaxis: "x" + suf(k), yaxis: "y" + suf(k),
            hovertemplate: V[j] + " %{{x}}<br>%{{y}} meses<extra></extra>"
          }});
        }} else {{
          // triángulo inferior: la nube de puntos del par
          indicesNubes.push(trazas.length);
          trazas.push({{
            type: "scattergl", mode: "markers", x: datos[V[j]], y: datos[V[i]],
            text: CORR.meses,
            marker: {{ color: AZUL, size: 3.2, opacity: 0.42 }},
            // al seleccionar en un panel, los mismos meses se marcan en todos los demás
            selected: {{ marker: {{ color: NARANJA, size: 5, opacity: 1 }} }},
            unselected: {{ marker: {{ opacity: 0.05 }} }},
            xaxis: "x" + suf(k), yaxis: "y" + suf(k),
            hovertemplate: "%{{text}}<br>" + V[j] + " %{{x}}<br>" + V[i] + " %{{y}}<extra></extra>"
          }});
        }}
      }}
    }}

    // nombres de las variables: solo en el borde izquierdo y en el inferior
    V.forEach((nombre, idx) => {{
      const unidad = CORR.unidades[idx];
      const [x0, x1] = dominioX(idx), [y0, y1] = dominioY(idx);
      anotaciones.push({{
        xref: "paper", yref: "paper", x: -0.012, xanchor: "right", y: (y0 + y1) / 2,
        text: "<b>" + nombre + "</b><br>" + (rezago ? "mes t+1" : unidad), showarrow: false, align: "right",
        font: {{ size: 10, color: tinta }}
      }});
      anotaciones.push({{
        xref: "paper", yref: "paper", x: (x0 + x1) / 2, y: -0.045, yanchor: "top",
        text: "<b>" + nombre + "</b><br>" + (rezago ? "mes t" : unidad), showarrow: false,
        font: {{ size: 10, color: tinta }}
      }});
    }});

    disposicion.shapes = formas;
    disposicion.annotations = anotaciones;
    if (rezago) {{
      // sin trazas, Plotly dibujaría un par de ejes vacíos por detrás de las casillas
      disposicion.xaxis = {{ visible: false }};
      disposicion.yaxis = {{ visible: false }};
    }}

    const nodo = document.getElementById("g-corr-matriz");
    Plotly.react("g-corr-matriz", trazas, disposicion, CONF).then(() => {{
      if (nodo.dataset.enlazado === "si") return;     // los eventos se enganchan una sola vez
      nodo.dataset.enlazado = "si";

      // Los 262 meses van en el mismo orden en todas las nubes, así que el índice de un punto
      // identifica al mismo mes en cualquier panel: basta con propagar los índices seleccionados.
      const propagar = indices => Plotly.restyle(nodo, {{ selectedpoints: [indices] }},
                                                 indicesNubes);
      const contador = document.getElementById("corr-seleccion");

      nodo.on("plotly_selected", ev => {{
        if (!ev || !ev.points || !ev.points.length) return;
        const indices = ev.points.map(p => p.pointIndex);
        propagar(indices);
        if (contador) {{
          contador.textContent = indices.length + " de " + CORR.meses.length +
            " meses resaltados. Doble clic para soltar la selección.";
        }}
      }});
      nodo.on("plotly_deselect", () => {{
        propagar(null);
        if (contador) contador.textContent = "";
      }});
    }});
  }}

  // las dos pestañas de esta sección cambian la serie que se dibuja, no el panel que se muestra
  (function () {{
    const MODOS = ["crudas", "anomalias", "rezago"];
    const botones = ["pestana-crudas", "pestana-anomalias", "pestana-rezago"].map(id => document.getElementById(id));
    if (botones.some(b => !b)) return;
    botones.forEach((boton, i) => boton.addEventListener("click", () => {{
      corrModo = MODOS[i];
      botones.forEach((otro, j) => {{
        otro.setAttribute("aria-selected", String(i === j));
        otro.tabIndex = i === j ? 0 : -1;
      }});
      dibujarCorrelaciones();
    }}));
  }})();



  const CAJAS = {cajas_json};
  let cajaActiva = 0;

  function dibujarCajas() {{
    if (!window.Plotly) return;
    const COLORES = {{ "PI": "#0072B2", "PL": "#D55E00", "Q": css("--tenue"),
                      "T media": "#009E73", "T máx": "#CC79A7", "T mín": "#56B4E9" }};
    const v = CAJAS.variables[cajaActiva], color = COLORES[v];
    const x = [], y = [], fecha = [];
    CAJAS.valores[v].forEach((vals, m) => vals.forEach((val, k) => {{
      x.push(CAJAS.meses[m]); y.push(val); fecha.push(CAJAS.fechas[v][m][k]);
    }}));
    const disposicion = base();
    Object.assign(disposicion, {{ height: 420, showlegend: false, hovermode: "closest" }});
    disposicion.margin.t = 20;
    disposicion.yaxis.title.text = v + " (" + CAJAS.unidades[cajaActiva] + ")";
    disposicion.yaxis.rangemode = CAJAS.unidades[cajaActiva] === "°C" ? "normal" : "tozero";
    disposicion.xaxis.categoryorder = "array";
    disposicion.xaxis.categoryarray = CAJAS.meses;
    Plotly.react("g-cajas", [{{
      type: "box", x, y, name: v, quartilemethod: "linear",
      // todos los meses como puntos, dispersos a la izquierda de su caja para que no se encimen
      boxpoints: "all", jitter: 0.5, pointpos: -1.7, text: fecha,
      marker: {{ color, size: 4.5, opacity: 0.7 }}, line: {{ color, width: 1.5 }}, fillcolor: color + "33",
      hoveron: "points",
      hovertemplate: "<b>%{{text}}</b><br>" + v + ": %{{y}} " + CAJAS.unidades[cajaActiva] + "<extra></extra>"
    }}], disposicion, CONF);
  }}

  (function () {{
    const cont = document.getElementById("pestanas-cajas");
    if (!cont) return;
    const botones = CAJAS.variables.map((v, i) => {{
      const b = document.createElement("button");
      b.type = "button"; b.setAttribute("role", "tab"); b.textContent = v;
      b.setAttribute("aria-selected", String(i === 0)); b.tabIndex = i === 0 ? 0 : -1;
      b.addEventListener("click", () => {{
        cajaActiva = i;
        botones.forEach((o, j) => {{ o.setAttribute("aria-selected", String(i === j)); o.tabIndex = i === j ? 0 : -1; }});
        dibujarCajas();
      }});
      cont.appendChild(b); return b;
    }});
  }})();

  const CLQ = {ciclo_lq_json};

  function dibujarCicloRezago() {{
    if (!window.Plotly) return;
    const tinta = css("--tinta"), tenue = css("--tenue");
    const NARANJA = "#D55E00", AZUL = "#0072B2";
    const trazas = [
      {{ type: "bar", name: "PL (lluvia)", x: CLQ.meses, y: CLQ.PL,
         marker: {{ color: NARANJA, opacity: 0.22 }}, hovertemplate: "PL %{{y:.0f}} mm/mes<extra></extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "Q observado", x: CLQ.meses, y: CLQ.Q,
         line: {{ color: tinta, width: 2.6 }}, marker: {{ size: 6, color: tinta }},
         hovertemplate: "Q %{{y:.0f}} mm/mes<extra></extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q predicho con PL del mes", x: CLQ.meses, y: CLQ.ajusteMes,
         line: {{ color: tenue, width: 1.8, dash: "dot" }},
         hovertemplate: "Q predicho con PL del mes: %{{y:.0f}}<extra></extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q predicho con PL del mes y del anterior", x: CLQ.meses,
         y: CLQ.ajusteMesAnterior, line: {{ color: AZUL, width: 2.2, dash: "dash" }},
         hovertemplate: "Q predicho con PL del mes y del anterior: %{{y:.0f}}<extra></extra>" }}
    ];
    const disposicion = base();
    Object.assign(disposicion, {{ height: 420, bargap: 0.35 }});
    Object.assign(disposicion.legend, {{ itemwidth: 44, entrywidth: 330 }});
    disposicion.yaxis.title.text = "mm/mes";
    Plotly.react("g-ciclo-rezago", trazas, disposicion, CONF);
  }}

  const CAL = {cal_json};

  function dibujarCalidad() {{
    if (!window.Plotly) return;
    const tinta = css("--tinta"), tenue = css("--tenue"), linea = css("--linea");
    // rojo -> amarillo -> verde. El amarillo marca los meses a medio registrar, que son el punto de
    // esta figura: con dos colores se perderían.
    const ESCALA = [[0, "#B3261E"], [0.35, "#D1651E"], [0.65, "#E8C547"],
                    [0.88, "#6BAE5C"], [1, "#1B7F3B"]];

    const disposicion = {{
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: {{ family: "IBM Plex Mono, ui-monospace, monospace", size: 10.5, color: tinta }},
      margin: {{ t: 16, r: 14, b: 52, l: 238 }},
      xaxis: {{ type: "date", showgrid: true, gridcolor: linea, zeroline: false,
               tickfont: {{ color: tenue }}, linecolor: linea,
               title: {{ text: "mes  ·  arrastra sobre el gráfico para ampliar un tramo",
                         font: {{ size: 11, color: tenue }} }} }},
      yaxis: {{ autorange: "reversed", showgrid: false, zeroline: false,
               tickfont: {{ color: tinta, size: 10.5 }}, linecolor: linea, ticklen: 4 }},
      dragmode: "zoom"
    }};

    Plotly.react("g-calidad", [{{
      type: "heatmap",
      z: CAL.fuentes.map(f => f.pct),
      x: CAL.meses,
      y: CAL.fuentes.map(f => f.nombre),
      customdata: CAL.fuentes.map(f => f.detalle),
      colorscale: ESCALA, zmin: 0, zmax: 100, xgap: 0, ygap: 3,
      colorbar: {{ title: {{ text: "% de días<br>con dato", font: {{ size: 10, color: tenue }} }},
                  thickness: 12, len: 0.75, tickfont: {{ size: 9, color: tenue }},
                  outlinewidth: 0, ticksuffix: " %" }},
      hovertemplate: "<b>%{{y}}</b><br>%{{x|%b %Y}} · %{{z:.0f}} %% de los días<br>" +
                     "%{{customdata}}<extra></extra>"
    }}], disposicion, CONF);
  }}


  const ETP = {etp_json};

  function dibujarEtp() {{
    if (!window.Plotly) return;
    const SERIES = [
      {{ clave: "camels", nombre: "CAMELS-COL, publicada", color: "#CC79A7", guion: "solid", simbolo: "circle" }},
      {{ clave: "mswx", nombre: "Hargreaves con MSWX", color: "#009E73", guion: "dash", simbolo: "square" }},
      {{ clave: "era", nombre: "Hargreaves con ERA5-Land", color: "#0072B2", guion: "solid", simbolo: "diamond" }}
    ];
    const trazas = SERIES.map(s => ({{
      type: "scatter", mode: "lines+markers", name: s.nombre, x: ETP.meses, y: ETP[s.clave],
      line: {{ color: s.color, width: 2, dash: s.guion }}, marker: {{ symbol: s.simbolo, size: 6 }},
      hovertemplate: "%{{y:.0f}} mm<extra>" + s.nombre + "</extra>" }}));
    trazas.push({{ type: "scatter", mode: "lines", name: "PL − Q", x: ETP.meses, y: ETP.pl_q,
      line: {{ color: css("--tenue"), width: 1.4, dash: "dot" }},
      hovertemplate: "%{{y:.0f}} mm<extra>PL − Q</extra>" }});
    Plotly.react("g-etp", trazas, base(), CONF);
  }}

  const DM = {an_dm_json};

  function dibujarDobleMasa() {{
    if (!window.Plotly) return;
    const series = Object.keys(DM), AZUL = "#0072B2", NARANJA = "#D55E00", GRIS = css("--tenue");
    const trazas = [], botones = [];
    series.forEach((s, i) => {{
      const d = DM[s], color = d.corte ? NARANJA : AZUL, n = d.x.length;
      trazas.push({{ type: "scatter", mode: "lines", name: s, x: d.x, y: d.y, customdata: d.meses, visible: i === 0,
        line: {{ color: color, width: 2 }}, hovertemplate: "%{{customdata}}<br>serie %{{y:,.0f}} mm<br>referencia %{{x:,.0f}} mm<extra></extra>" }});
      trazas.push({{ type: "scatter", mode: "lines", name: "proporción constante", x: [0, d.x[n - 1]], y: [0, d.y[n - 1]],
        visible: i === 0, line: {{ color: GRIS, width: 1, dash: "dot" }}, hoverinfo: "skip" }});
      const k = d.corte ? d.meses.indexOf(d.corte) : -1;
      trazas.push({{ type: "scatter", mode: "markers", name: "comienzo del 2.º tramo", visible: i === 0,
        x: k >= 0 ? [d.x[k]] : [], y: k >= 0 ? [d.y[k]] : [], marker: {{ symbol: "diamond", size: 11, color: NARANJA }},
        hovertemplate: (d.corte || "") + "<extra>comienzo del 2.º tramo</extra>" }});
      botones.push({{ label: s, method: "update",
        args: [{{ visible: series.flatMap((_, j) => [j === i, j === i, j === i]) }},
               {{ "xaxis.title.text": "acumulado de la referencia (mm): " + d.referencia }}] }});
    }});
    const disp = base();
    disp.hovermode = "closest";
    disp.showlegend = false;
    disp.margin = {{ t: 56, r: 10, b: 50, l: 70 }};
    disp.yaxis.title.text = "acumulado de la serie (mm)";
    disp.separators = ". ";                                   // punto decimal, espacio para los miles
    disp.yaxis.tickformat = ",.0f";
    disp.xaxis.title = {{ text: "acumulado de la referencia (mm): " + DM[series[0]].referencia,
                         font: {{ size: 11, color: GRIS }} }};
    disp.xaxis.tickformat = ",.0f";
    disp.updatemenus = [{{ buttons: botones, x: 0, xanchor: "left", y: 1.14, yanchor: "top",
                          bgcolor: css("--superficie"), bordercolor: css("--linea"), font: {{ size: 11, color: css("--tinta") }} }}];
    Plotly.react("g-doble-masa", trazas, disp, CONF);
  }}

  const PQ = {pq_json};

  function dibujarPQ() {{
    if (!window.Plotly) return;
    const NARANJA = "#D55E00", AZUL = "#0072B2", VERDE = "#009E73", GRIS = css("--tenue");
    const mensual = base();
    mensual.margin = {{ t: 46, r: 10, b: 30, l: 54 }};
    mensual.yaxis.rangemode = "normal";
    mensual.shapes = [{{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: {{ color: GRIS, width: 1 }} }}];
    Plotly.react("g-pq-mensual", [
      {{ type: "scatter", mode: "lines", name: "PL − Q", x: PQ.meses, y: PQ.pl_q, connectgaps: false,
         line: {{ color: NARANJA, width: 1.6 }}, hovertemplate: "%{{y:.0f}} mm<extra>PL − Q</extra>" }},
      {{ type: "scatter", mode: "lines", name: "PI − Q", x: PQ.meses, y: PQ.pi_q, connectgaps: false,
         line: {{ color: AZUL, width: 1.2, dash: "dash" }}, hovertemplate: "%{{y:.0f}} mm<extra>PI − Q</extra>" }},
      {{ type: "scatter", mode: "lines", name: "ETP (Hargreaves, ERA5-Land)", x: PQ.meses, y: PQ.etp,
         line: {{ color: VERDE, width: 2.4 }}, hovertemplate: "%{{y:.0f}} mm<extra>ETP</extra>" }}
    ], mensual, CONF);
    const anual = base();
    anual.margin = {{ t: 46, r: 10, b: 40, l: 54 }};
    anual.yaxis.title.text = "mm/año";
    anual.xaxis.type = "category";
    anual.barmode = "group";
    Plotly.react("g-pq-anual", [
      {{ type: "bar", name: "PL − Q", x: PQ.anios, y: PQ.pl_q_anual, marker: {{ color: NARANJA }},
         hovertemplate: "%{{y:.0f}} mm<extra>PL − Q</extra>" }},
      {{ type: "bar", name: "PI − Q", x: PQ.anios, y: PQ.pi_q_anual, marker: {{ color: AZUL, opacity: 0.75 }},
         hovertemplate: "%{{y:.0f}} mm<extra>PI − Q</extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "ETP", x: PQ.anios, y: PQ.etp_anual,
         line: {{ color: VERDE, width: 2.4 }}, hovertemplate: "%{{y:.0f}} mm<extra>ETP</extra>" }}
    ], anual, CONF);
  }}


  const P2 = {p2_pipl_json};
  const EV = {ev_json};

  function dibujarPuntoDos() {{
    if (!window.Plotly) return;
    const AZUL = "#0072B2", NARANJA = "#D55E00", GRIS = css("--tenue");
    const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
    const tope = Math.ceil(Math.max(...P2.pi, ...P2.pl) / 50) * 50;
    const d1 = base();
    d1.hovermode = "closest";
    d1.margin = {{ t: 30, r: 10, b: 48, l: 58 }};
    d1.showlegend = false;
    d1.xaxis.range = [0, tope]; d1.yaxis.range = [0, tope];
    d1.xaxis.title = {{ text: "PI (mm/mes)", font: {{ size: 11, color: GRIS }} }};
    d1.yaxis.title.text = "PL (mm/mes)";
    d1.yaxis.scaleanchor = "x";
    d1.shapes = [{{ type: "line", x0: 0, y0: 0, x1: tope, y1: tope, line: {{ color: GRIS, width: 1, dash: "dash" }} }}];
    d1.annotations = [{{ x: tope * 0.97, y: tope * 0.97, xanchor: "right", yanchor: "bottom", showarrow: false,
                         text: "PI = PL", font: {{ size: 10, color: GRIS }} }}];
    Plotly.react("g-pi-pl", [{{
      type: "scatter", mode: "markers", x: P2.pi, y: P2.pl,
      customdata: P2.periodo,
      marker: {{ size: 7, opacity: 0.8, color: P2.mes, colorscale: "Viridis", cmin: 1, cmax: 12,
                 colorbar: {{ title: {{ text: "mes", font: {{ size: 10 }} }}, tickvals: [1,2,3,4,5,6,7,8,9,10,11,12],
                              ticktext: MESES_CORTOS, thickness: 10, len: 0.9 }} }},
      hovertemplate: "%{{customdata}}<br>PI %{{x:.0f}} mm · PL %{{y:.0f}} mm<extra></extra>"
    }}], d1, CONF);

    const d2 = base();
    d2.margin.t = 46;
    d2.yaxis.title.text = "Q (m³/s)";
    Plotly.react("g-evaluacion", [
      {{ type: "scatter", mode: "lines", name: "Q observado", x: EV.meses, y: EV.q,
         line: {{ color: css("--tinta"), width: 2 }}, connectgaps: false, hovertemplate: "%{{y:.0f}} m³/s<extra>Q observado</extra>" }},
      {{ type: "scatter", mode: "lines", name: "climatología", x: EV.meses, y: EV.clima,
         line: {{ color: GRIS, width: 1.4, dash: "dot" }}, hovertemplate: "%{{y:.0f}} m³/s<extra>climatología</extra>" }},
      {{ type: "scatter", mode: "lines", name: "estimado con PL", x: EV.meses, y: EV.pl,
         line: {{ color: NARANJA, width: 1.6 }}, connectgaps: false, hovertemplate: "%{{y:.0f}} m³/s<extra>con PL</extra>" }},
      {{ type: "scatter", mode: "lines", name: "estimado con PI", x: EV.meses, y: EV.pi,
         line: {{ color: AZUL, width: 1.2, dash: "dash" }}, connectgaps: false, hovertemplate: "%{{y:.0f}} m³/s<extra>con PI</extra>" }}
    ], d2, CONF);
  }}
  const BAL = {bal_json};

  function dibujarBalance() {{
    if (!window.Plotly) return;
    const AZUL = "#0072B2", NARANJA = "#D55E00", GRIS = css("--tenue");

    Plotly.react("g-balance", [
      {{ type: "scatter", mode: "lines", name: "PI · precipitación IMERG", x: BAL.meses, y: BAL.p,
         line: {{ color: AZUL, width: 1.6 }}, fill: "tozeroy",
         fillcolor: "rgba(0,114,178,0.16)",
         hovertemplate: "%{{y:.0f}} mm<extra>PI</extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q · caudal observado", x: BAL.meses, y: BAL.q,
         line: {{ color: NARANJA, width: 1.6 }}, connectgaps: false,
         hovertemplate: "%{{y:.0f}} mm<extra>Q</extra>" }}
    ], Object.assign(base(), {{ margin: {{ t: 46, r: 10, b: 30, l: 54 }} }}), CONF);

    const disp = base();
    disp.margin = {{ t: 10, r: 10, b: 40, l: 54 }};
    disp.showlegend = true;
    disp.margin.t = 40;
    disp.yaxis.title.text = "caudal / lluvia";
    disp.yaxis.rangemode = "tozero";
    disp.shapes = [
      {{ type: "line", xref: "paper", x0: 0, x1: 1, yref: "y", y0: 1, y1: 1,
         line: {{ color: GRIS, width: 1, dash: "dot" }} }},
      {{ type: "line", xref: "paper", x0: 0, x1: 1, yref: "y", y0: BAL.coef_medio, y1: BAL.coef_medio,
         line: {{ color: NARANJA, width: 1.2, dash: "dash" }} }}
    ];
    disp.annotations = [
      {{ xref: "paper", x: 0.004, xanchor: "left", y: 1, yanchor: "bottom",
         text: "caudal = lluvia del mes", showarrow: false, font: {{ size: 10, color: GRIS }} }},
      {{ xref: "paper", x: 0.004, xanchor: "left", y: BAL.coef_medio, yanchor: "bottom",
         text: "promedio de Q / PI: " + BAL.coef_medio.toFixed(2), showarrow: false,
         font: {{ size: 10, color: NARANJA }} }}
    ];
    Plotly.react("g-escorrentia", [
      {{ type: "scatter", mode: "lines", name: "Q / PL", x: BAL.meses, y: BAL.coef_pl,
         line: {{ color: "#4A5259", width: 1.4 }}, connectgaps: false,
         hovertemplate: "%{{y:.2f}}<extra>Q / PL</extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q / PI", x: BAL.meses, y: BAL.coef,
         line: {{ color: AZUL, width: 1, dash: "dot" }}, connectgaps: false,
         hovertemplate: "%{{y:.2f}}<extra>Q / PI</extra>" }}
    ], disp, CONF);
  }}

  const CICLO = {ciclo_json};

  function dibujarCicloAnual() {{
    if (!window.Plotly) return;
    const AZUL = "#0072B2", NARANJA = "#D55E00", VERDE = "#009E73", GRIS = css("--tenue");

    Plotly.react("g-ciclo-anual", [
      {{ type: "scatter", mode: "lines+markers", name: "PI · lluvia IMERG",
         x: CICLO.meses, y: CICLO.imerg,
         line: {{ color: AZUL, width: 2.2 }}, marker: {{ size: 7 }},
         hovertemplate: "%{{y:.0f}} mm<extra>PI</extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "PL · lluvia de la red",
         x: CICLO.meses, y: CICLO.red,
         line: {{ color: NARANJA, width: 2.2, dash: "dash" }}, marker: {{ size: 7 }},
         hovertemplate: "%{{y:.0f}} mm<extra>PL</extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "Q · caudal", x: CICLO.meses, y: CICLO.caudal,
         line: {{ color: VERDE, width: 2.6 }}, marker: {{ size: 8 }}, fill: "tozeroy",
         fillcolor: "rgba(0,158,115,0.15)",
         hovertemplate: "%{{y:.0f}} mm<extra>Q</extra>" }}
    ], Object.assign(base(), {{ margin: {{ t: 58, r: 12, b: 38, l: 56 }} }}), CONF);

  }}

  const GRAD = {grad_json};

  function dibujarGradiente() {{
    if (!window.Plotly) return;
    const AZUL = "#0072B2", NARANJA = "#D55E00", GRIS = css("--tenue");

    const trazas = [
      // todas las celdas que tocan la cuenca; el tamaño dice cuánto pesan en el ajuste
      {{ type: "scatter", mode: "markers", name: "celdas de IMERG (tamaño = % dentro)",
         x: GRAD.imerg.alt, y: GRAD.imerg.p,
         marker: {{ size: GRAD.imerg.frac.map(f => 5 + 0.09 * f), color: AZUL,
                    line: {{ color: "#FFFFFF", width: 1.2 }} }},
         text: GRAD.imerg.frac,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<br>%{{text:.0f}} % dentro"
                      + "<extra>celda de IMERG</extra>" }},
      {{ type: "scatter", mode: "lines", name: "tendencia IMERG", x: GRAD.rectaImerg.x,
         y: GRAD.rectaImerg.y, line: {{ color: AZUL, width: 2 }}, hoverinfo: "skip" }},
      // la estación fuera de la divisoria: hueca, tampoco entra en el ajuste
      {{ type: "scatter", mode: "markers", name: "estación fuera de la divisoria",
         x: GRAD.pluFuera.alt, y: GRAD.pluFuera.p,
         marker: {{ size: 11, color: "rgba(0,0,0,0)", line: {{ color: GRIS, width: 1.6 }} }},
         text: GRAD.pluFuera.nombre,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<extra>%{{text}}</extra>" }},
      {{ type: "scatter", mode: "markers", name: "pluviómetros de la cuenca",
         x: GRAD.plu.alt, y: GRAD.plu.p,
         marker: {{ size: 13, color: NARANJA, line: {{ color: "#FFFFFF", width: 1.4 }} }},
         text: GRAD.plu.nombre,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<extra>%{{text}}</extra>" }},
      {{ type: "scatter", mode: "lines", name: "tendencia pluviómetros", x: GRAD.rectaPlu.x,
         y: GRAD.rectaPlu.y, line: {{ color: NARANJA, width: 2, dash: "dash" }}, hoverinfo: "skip" }}
    ];

    const disp = base();
    disp.hovermode = "closest";               // es una nube de puntos, no una serie de tiempo
    disp.margin = {{ t: 74, r: 14, b: 48, l: 62 }};
    disp.xaxis.title = {{ text: "altitud (m s. n. m.)", font: {{ size: 11, color: css("--tenue") }} }};
    disp.yaxis.title.text = "precipitación media anual (mm/año)";
    disp.yaxis.rangemode = "normal";          // el interés está en la pendiente, no en el cero
    Plotly.react("g-gradiente", trazas, disp, CONF);

    // --- el mismo ajuste apartando las dos estaciones que no encajan ---
    const trazasLimpio = [
      {{ type: "scatter", mode: "markers", name: "apartadas del ajuste",
         x: GRAD.pluAparte.alt, y: GRAD.pluAparte.p,
         marker: {{ size: 13, color: "rgba(0,0,0,0)", line: {{ color: GRIS, width: 1.6 }} }},
         text: GRAD.pluAparte.nombre,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<extra>%{{text}} · apartada</extra>" }},
      {{ type: "scatter", mode: "markers", name: "estaciones del ajuste",
         x: GRAD.pluLimpio.alt, y: GRAD.pluLimpio.p,
         marker: {{ size: 13, color: NARANJA, line: {{ color: "#FFFFFF", width: 1.4 }} }},
         text: GRAD.pluLimpio.nombre,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<extra>%{{text}}</extra>" }},
      {{ type: "scatter", mode: "lines", name: "tendencia de estas estaciones",
         x: GRAD.rectaLimpio.x, y: GRAD.rectaLimpio.y,
         line: {{ color: NARANJA, width: 2.4 }}, hoverinfo: "skip" }},
      {{ type: "scatter", mode: "lines", name: "tendencia de IMERG",
         x: GRAD.rectaImergEnTramo.x, y: GRAD.rectaImergEnTramo.y,
         line: {{ color: AZUL, width: 2.4, dash: "dash" }}, hoverinfo: "skip" }}
    ];

    const dispLimpio = base();
    dispLimpio.hovermode = "closest";
    dispLimpio.margin = {{ t: 64, r: 14, b: 48, l: 62 }};
    dispLimpio.xaxis.title = {{ text: "altitud (m s. n. m.)",
                               font: {{ size: 11, color: css("--tenue") }} }};
    dispLimpio.yaxis.title.text = "precipitación media anual (mm/año)";
    dispLimpio.yaxis.rangemode = "normal";
    Plotly.react("g-gradiente-limpio", trazasLimpio, dispLimpio, CONF);
  }}

  function dibujar() {{
    if (!window.Plotly) return;
    // los pluviómetros sueltos van tenues y comparten una sola entrada de leyenda
    const series = D.series.map(s => ({{
      type: "scatter", mode: "lines", name: s.etiquetaGrupo || s.nombre, x: D.meses, y: s.y,
      line: {{ color: s.color, width: s.grosor, dash: s.guion || "solid" }}, connectgaps: false,
      opacity: s.opacidad === undefined ? 1 : s.opacidad,
      legendgroup: s.grupo || s.nombre,
      showlegend: s.enLeyenda === undefined ? true : s.enLeyenda,
      hovertemplate: "%{{y:.0f}} mm<extra>" + s.nombre + "</extra>"
    }}));
    Plotly.react("g-series", series, base(), CONF);

    const ciclo = D.ciclo.map(s => ({{
      type: "scatter", mode: s.opacidad === undefined ? "lines+markers" : "lines",
      name: s.nombre, x: MES, y: s.y,
      line: {{ color: s.color, width: s.opacidad === undefined ? 2 : 1.1,
              dash: s.guion || "solid" }},
      marker: {{ size: 6 }}, opacity: s.opacidad === undefined ? 1 : s.opacidad,
      legendgroup: s.grupo || s.nombre,
      hovertemplate: "%{{y:.0f}} mm<extra>" + s.nombre + "</extra>"
    }}));
    const disposicion = base();
    disposicion.yaxis.title.text = "mm/mes (media)";
    disposicion.showlegend = false;          // comparte la leyenda con el gráfico de la izquierda
    disposicion.margin.t = 12;
    Plotly.react("g-ciclo", ciclo, disposicion, CONF);
    dibujarCalidad();
    dibujarTemperatura();
    dibujarEtp();
    dibujarDobleMasa();
    dibujarCorrelaciones();
    dibujarCicloRezago();
    dibujarCajas();
    dibujarBalance();
    dibujarPuntoDos();
    dibujarPQ();
    dibujarCicloAnual();
    dibujarGradiente();
  }}

  dibujar();
  if (window.matchMedia) {{
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dibujar);
  }}
  new MutationObserver(dibujar).observe(document.documentElement,
                                        {{ attributes: true, attributeFilter: ["data-theme"] }});
}})();
</script>
</div>
{INDICE_HTML}
"""
SALIDA.write_text(pagina, encoding="utf-8")
print(f"{SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB)")
print(p_imerg.round(0).to_dict())
print(f"píxeles >50% dentro: P {p_dmin:.0f}–{p_dmax:.0f}")
print(f"ERA5-Land: {t_npix} píxeles, T {t_min_px:.1f}–{t_max_px:.1f} °C, "
      f"promedio ponderado {t_ponderada:.2f} °C (serie: {t_serie_media:.2f} °C)")
