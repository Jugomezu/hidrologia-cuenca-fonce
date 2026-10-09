"""El análisis del informe: lee out/ y data/ y calcula todo lo que muestra reporte/reporte-fonce.html.

Está organizado en bloques por tema, cada uno marcado con un comentario «# ---- tema». Cada bloque deja sus
resultados en variables (números, tablas de pandas, series para las gráficas) que usa la página. Las
cifras de los textos del informe salen de aquí, nunca escritas a mano.

No se corre solo: lo corre scripts/18b_reporte_html.py, que arma la página. Para regenerar el informe,
desde la raíz del repositorio:

    python scripts/18b_reporte_html.py

Las figuras fijas de reporte/figuras/ las hacen 08, 09, 10 y 14.
"""
import geopandas as gpd
from pyproj import Geod
from pathlib import Path
from scipy import stats
from scipy.signal import csd, lfilter, lombscargle, periodogram, welch
import numpy as np
import pandas as pd
import rasterio
import xarray as xr


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


sg = m.loc[24027010]

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


def a_mensual(serie_diaria, agregacion, periodos=None):
    """Serie diaria -> mensual; el mes queda vacío si le faltan más de MAX_DIAS_FALTANTES días.

    `agregacion` es "sum" para acumulados (lluvia, caudal en mm, ETP) o "mean" para promedios.
    `periodos` es la ventana de salida; por defecto, el período de estudio 1998-2022 (regla 6).
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
    return valores.reindex(PERIODOS if periodos is None else periodos)


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


# Cada serie dice de qué variable es ("variable"); el color lo pone la página, un solo color por variable
# (COLOR_VAR en scripts/18b_reporte_html.py). Decisión de dibujo: los pluviómetros individuales van
# tenues, como nube de fondo, y el promedio de la red va a plena opacidad encima. Lo que compite con
# el satélite es la red, no cada aparato.
nube = [{"nombre": nom, "variable": "PL", "grosor": 1.0, "guion": None, "opacidad": 0.20,
         "enLeyenda": i == 0, "grupo": "pluviometros",
         "etiquetaGrupo": "pluviómetros, uno a uno", "y": serie(cod)}
        for i, (cod, nom) in enumerate(COD_PLUVIO.items())]
cmp_datos = {
    "meses": [str(x) for x in comp.index],
    "series": nube + [
        {"nombre": "PI · IMERG", "variable": "PI", "grosor": 2.2, "guion": None, "y": serie("IMERG")},
        {"nombre": f"PL · promedio de {len(DENTRO)} pluviómetros", "variable": "PL",
         "grosor": 2.0, "guion": "dash", "y": serie("RED")}],
}
ciclo = comp.groupby(comp.index.month).mean()
cmp_datos["ciclo"] = (
    [{"nombre": COD_PLUVIO[cod], "variable": "PL", "guion": None, "opacidad": 0.22,
      "enLeyenda": False, "grupo": "pluviometros",
      "y": [round(float(v), 1) for v in ciclo[cod]]}
     for cod in COD_PLUVIO]
    + [{"nombre": nombre, "variable": variable, "guion": guion,
        "y": [round(float(v), 1) for v in ciclo[col]]}
       for col, nombre, variable, guion in [("IMERG", "PI · IMERG", "PI", None),
                                            ("RED", f"PL · promedio de {len(DENTRO)} pluviómetros",
                                             "PL", "dash")]])
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

# contexto geográfico: centroide del polígono de San Gil, calculado en EPSG:3116 (regla 13) y devuelto a grados
_poligono_sg = gpd.read_file("out/shp_fonce/cuencas_fonce.shp").query("gauge_id == 24027010")
_centroide_sg = _poligono_sg.to_crs(3116).centroid.to_crs(4326).iloc[0]
centroide_lat, centroide_lon = float(_centroide_sg.y), float(_centroide_sg.x)

# óptimo pluviográfico: según Mesa et al. (1997, p. 90), la lluvia máxima ocurre normalmente a no más de 1 500 m.
# Qué parte de la cuenca queda por encima, leída de la curva hipsométrica del proyecto (13_morfometria.py)
ALTURA_OPTIMO_M = 1500
_hipso = pd.read_csv("out/curva_hipsometrica_fonce.csv")
frac_sobre_optimo = float(np.interp(ALTURA_OPTIMO_M, _hipso.altura_m, _hipso.fraccion_area_encima))
# el texto dice que la cuenca empieza por debajo de esa altura y que la mayor parte queda por encima
assert elev_min < ALTURA_OPTIMO_M and frac_sobre_optimo > 0.5

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


# fase de El Niño / La Niña de cada mes según el ONI de la NOAA (17_oni_enso.py); solo se usa para
# colorear las fechas, sin sacar conclusiones todavía
oni_fase = pd.read_csv("out/oni_mensual.csv")
oni_fase = oni_fase.set_index(pd.PeriodIndex(oni_fase.periodo, freq="M"))["fase"]


# Lectura ENSO de la lluvia extrema confirmada: cuáles cayeron en La Niña y cuáles no. Para enero de 2005,
# la única excepción al escribir esto, hay un documento que describe el evento; si la lista cambiara, el
# texto se arma igual con lo que haya.
_confirmada_nina = [p for p in lluvia_confirmada if oni_fase.get(p) == "La Niña"]
_confirmada_otras = [p for p in lluvia_confirmada if oni_fase.get(p) != "La Niña"]
# enero y febrero de 2005 (emergencia invernal en Santander) tienen su propio punto en la lista, siempre visible


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
# Para cada variable y cada mes del calendario: años con dato y estadísticos de esos años (en el informe, sobre
# los meses comunes clima_meses, definidos más abajo junto al año típico). Percentiles
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

ciclo_n = len(ciclo_comun)

# Climatología de 12 meses (la tabla por mes del ciclo anual y los diagramas de caja por mes): se calcula
# sobre los MISMOS meses comunes del año típico, los de ciclo_comun (decisión del usuario, 2026-10-08), para
# comparar las fuentes con los mismos pares de meses válidos. Sin la máscara, PI, PL y T usarían todos los años
# del período en cada mes y Q solo los suyos. La máscara es la de arriba; aquí no se reescribe. Solo cambia estas dos
# salidas: la tabla general (variables_resumen, 300 meses), los atípicos, la variabilidad, el régimen, las
# anomalías y lo demás siguen con todos los meses válidos de cada variable.
clima_meses = ciclo_comun.index
clima_series = variables_resumen.loc[clima_meses]
# en la máscara, todas las variables de la tabla y de las cajas (PI, PL, Q y las tres temperaturas) tienen dato
assert len(clima_meses) == ciclo_n and clima_series.notna().all().all()
# años con dato de cada mes del calendario dentro de la máscara (iguales para todas las variables)
clima_anios_mes = clima_series.groupby(clima_series.index.month).size()
assert len(clima_anios_mes) == 12
clima_anios_periodo = PERIODOS[-1].year - PERIODOS[0].year + 1          # años del período, para el texto
# las variables con huecos en el período son las que recortan la máscara (el texto las nombra)
clima_huecos_de = [c for c in variables_resumen.columns if variables_resumen[c].isna().any()]
assert clima_huecos_de == ["Q"]       # el informe dice que PI, PL y las temperaturas no tienen huecos y Q sí


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
# ---------------------------------------------------------------- variabilidad, asimetría e influencia (1.11)
# El mismo cálculo de la sección 1.11 del notebook, con la misma semilla y en el mismo orden, para que el
# intervalo del CV salga idéntico. Temperatura en K: en °C el CV no tiene sentido (cero convencional).
VAR_KELVIN = 273.15
VAR_REMUESTREOS = 2000
VAR_SEMILLA = 1
VAR_SERIES = {"PL": (variables_resumen["PL"], "mm/mes"), "PI": (variables_resumen["PI"], "mm/mes"),
              "Q": (variables_resumen["Q"], "m³/s"), "T media": (variables_resumen["T media"] + VAR_KELVIN, "K")}


def _var_cv(x):
    return np.std(x, ddof=1) / np.mean(x) * 100


def _var_bowley(x):
    q1, me, q3 = np.quantile(x, [0.25, 0.5, 0.75])
    return (q3 + q1 - 2 * me) / (q3 - q1)


_var_rng = np.random.default_rng(VAR_SEMILLA)
_var_filas, var_influencia = [], {}
for _n, (_s, _u) in VAR_SERIES.items():
    var_influencia[_n] = {}
    for _m in range(1, 13):
        _x = _s[_s.index.month == _m].dropna()
        _v = _x.to_numpy()
        _cv = _var_cv(_v)
        _jk = np.array([_var_cv(np.delete(_v, i)) for i in range(len(_v))])
        _bs = np.array([_var_cv(_var_rng.choice(_v, len(_v))) for _ in range(VAR_REMUESTREOS)])
        for _a in _x.index.year:
            var_influencia[_n][(_a, _m)] = (_x[_x.index.year != _a].mean() / _x.mean() - 1) * 100
        _var_filas.append({"var": _n, "mes": _m, "n": len(_v), "unidad": _u, "media": _v.mean(), "de": np.std(_v, ddof=1),
                           "cv": _cv, "jk": np.abs(_jk - _cv).max(), "ic_bajo": np.percentile(_bs, 2.5),
                           "ic_alto": np.percentile(_bs, 97.5), "asim": stats.skew(_v, bias=False),
                           "bowley": _var_bowley(_v)})
var_tabla = pd.DataFrame(_var_filas).set_index(["var", "mes"])
var_tabla["ancho"] = var_tabla.ic_alto - var_tabla.ic_bajo
_VAR_LC = ["PL", "PI", "Q"]
var_corr = {v: np.corrcoef(var_tabla.loc[v, "media"], var_tabla.loc[v, "ancho"])[0, 1] for v in _VAR_LC}
var_rel = var_tabla.ancho / var_tabla.cv * 100
var_mas = {v: (var_tabla.loc[v, "cv"].idxmax(), var_tabla.loc[v, "de"].idxmax()) for v in VAR_SERIES}
var_fuertes = {v: [m for m in range(1, 13) if var_tabla.loc[(v, m), "asim"] > 1] for v in _VAR_LC}
_var_mf = [(v, m) for v in _VAR_LC for m in var_fuertes[v]]
var_bowley_max = var_tabla.loc[_var_mf, "bowley"].abs().max() if _var_mf else float("nan")
var_por_pocos = bool(_var_mf) and var_bowley_max < 0.5 * var_tabla.loc[_var_mf, "asim"].min()
var_top = {v: max(var_influencia[v].items(), key=lambda kv: abs(kv[1])) for v in VAR_SERIES}
# años por mes que usa esta sección (todos los meses válidos de cada variable, no los meses comunes de la
# tabla del ciclo anual): (mínimo, máximo) sobre los 12 meses, para la nota del informe
var_n = {v: (int(var_tabla.loc[v, "n"].min()), int(var_tabla.loc[v, "n"].max())) for v in VAR_SERIES}
# la nota agrupa PL, PI y T media con un solo número de años por mes: tiene que ser el mismo en las tres
assert var_n["PL"] == var_n["PI"] == var_n["T media"] and var_n["PL"][0] == var_n["PL"][1]

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


# ---------------------------------------------------------------- ¿corregir PI con una recta contra PL? (Punto 2)
# El proyecto no corrige PI (regla 11); aquí se mide cuánto ganaría una corrección lineal ajustada con 1998-2014
# y evaluada con 2015-2022, en bloques continuos, en los meses de la tabla de variables de 16.
EV_AJUSTE, EV_VALIDACION = ("1998-01", "2014-12"), ("2015-01", "2022-12")
_ev = pd.read_csv("out/variables_mensuales.csv", index_col=0)[["PI", "PL"]]
_ev.index = pd.PeriodIndex(_ev.index, freq="M")
_ev = _ev.reindex(PERIODOS)
_ev_aj, _ev_val = _ev.loc[EV_AJUSTE[0]:EV_AJUSTE[1]], _ev.loc[EV_VALIDACION[0]:EV_VALIDACION[1]]


def _ev_metricas(observado, estimado):
    par = pd.concat([observado.rename("o"), estimado.rename("e")], axis=1).dropna()
    err = par.e - par.o
    return {"n": len(par), "sesgo": err.mean(), "mae": err.abs().mean(), "rmse": float(np.sqrt((err ** 2).mean()))}


_muestra_ev = _ev_aj[["PI", "PL"]].dropna()
_ev_pend, _ev_int = np.polyfit(_muestra_ev.PI, _muestra_ev.PL, 1)
ev_correccion = {"ols": _ev_metricas(_ev_val.PL, _ev_int + _ev_pend * _ev_val.PI),
                 "sin": _ev_metricas(_ev_val.PL, _ev_val.PI)}
# el texto dice que corregir PI «casi no gana nada»: menos de un 10 % de mejora en el RMSE
assert ev_correccion["ols"]["rmse"] > 0.9 * ev_correccion["sin"]["rmse"]


# ---------------------------------------------------------------- modelos para estimar Q con la lluvia (Punto 2)
# Los calcula 16b_modelos_lluvia_caudal.py: el diagnóstico, cinco modelos (M0 a M4), sus errores fuera del ajuste
# (partición 1998-2014 / 2015-2022 y validación cruzada con 5 bloques de 5 años) y la ficha del elegido, M4. Aquí
# solo se leen y se comprueba lo que afirman los textos. Lluvia y Q en mm/mes.
MOD_ALFA = 0.05                                   # el mismo nivel de 16b
MOD_ELEGIDO, MOD_COMPETIDOR, MOD_REFERENCIA = "M4", "M2", "M0"
MOD_CON_LLUVIA = ("M1", "M2", "M3", "M4")
MOD_FUENTES = ("PL", "PI")                     # regla 11: las dos en paralelo; manda PL
mod_diag = pd.read_csv("out/modelos_diagnostico.csv").set_index(["fuente", "escala"])
mod_param = pd.read_csv("out/modelos_parametros.csv").set_index(["fuente", "modelo", "parametro"])
mod_ajuste = pd.read_csv("out/modelos_ajuste.csv").set_index(["fuente", "modelo"])
mod_eval = pd.read_csv("out/modelos_evaluacion.csv")
mod_ficha = pd.read_csv("out/modelos_ficha.csv").set_index("fuente")
mod_est = pd.read_csv("out/modelos_estimados.csv")
mod_vc = mod_eval[mod_eval.esquema == "validación cruzada"].set_index(["fuente", "modelo"])
mod_part = mod_eval[mod_eval.esquema == "partición 2015-2022"].set_index(["fuente", "modelo"])
mod_bloques = mod_eval[mod_eval.esquema.str.startswith("bloque")].pivot_table(
    index=["fuente", "modelo"], columns="esquema", values="rmse")
mod_n = int(mod_ajuste.n_meses.iloc[0])
mod_n_diag = int(mod_diag.n_meses.iloc[0])
mod_minimos = {"PL": mod_diag.loc[("PL", "lineal"), "minimo_lluvia_mm"], "PI": mod_diag.loc[("PI", "lineal"), "minimo_lluvia_mm"],
               "Q": mod_diag.loc[("PL", "lineal"), "minimo_caudal_mm"]}
assert min(mod_minimos.values()) > 0                  # el texto dice que no hay meses en cero


def mod_rmse(fuente, modelo, esquema="vc"):
    return float((mod_vc if esquema == "vc" else mod_part).loc[(fuente, modelo), "rmse"])


# lo que dice el diagnóstico (Q contra la lluvia del mismo mes, recta y logaritmos)
for _f in MOD_FUENTES:
    _lin, _log = mod_diag.loc[(_f, "lineal")], mod_diag.loc[(_f, "logarítmica")]
    assert _lin.cuadratico_p_hac < MOD_ALFA                                  # la recta se curva
    assert _lin.cuadratico_coef > 0                                          # hacia arriba
    assert _lin.varianza_tercio_lluvioso_sobre_seco > P2_RAZON_VARIANZA      # el error crece con la lluvia
    assert _log.varianza_tercio_lluvioso_sobre_seco < 1                      # en logaritmos se invierte
    assert _lin.kruskal_residuo_por_mes_p < MOD_ALFA                         # queda el calendario
    assert _lin.corr_residuo_lluvia_mes_anterior_p < MOD_ALFA                # la lluvia del mes anterior explica el residuo
    assert _lin.shapiro_residuo_p < MOD_ALFA and _lin.asimetria_residuo > 0  # residuos de la recta: asimétricos
assert (mod_diag.loc[("PL", "lineal"), "corr_residuo_lluvia_mes_anterior"]
        > mod_diag.loc[("PI", "lineal"), "corr_residuo_lluvia_mes_anterior"])
# el residuo medio de la recta con PL es más alto en diciembre y más bajo en marzo (el texto los nombra)
assert (mod_diag.loc[("PL", "lineal"), "mes_residuo_medio_max"], mod_diag.loc[("PL", "lineal"), "mes_residuo_medio_min"]) == (12, 3)

# lo que dice la comparación de modelos, en la validación cruzada
for _f in MOD_FUENTES:
    # la lluvia del mes anterior mejora, en todos los bloques
    assert mod_rmse(_f, "M2") < mod_rmse(_f, "M1") and mod_rmse(_f, "M4") < mod_rmse(_f, "M3")
    assert (mod_bloques.loc[(_f, "M2")] < mod_bloques.loc[(_f, "M1")]).all()
    # el logaritmo no baja el error
    assert mod_rmse(_f, "M3") >= mod_rmse(_f, "M1") and mod_rmse(_f, "M4") >= mod_rmse(_f, "M2")
    # la curvatura sigue con el rezago incluido
    assert mod_ajuste.loc[(_f, MOD_ELEGIDO), "cuadratico_p_hac"] < MOD_ALFA
    assert mod_ajuste.loc[(_f, MOD_ELEGIDO), "kruskal_residuo_por_mes_p"] < MOD_ALFA
# con PI, cada modelo yerra más que con PL, y el mejor con PI no alcanza a la recta con PL
assert all(mod_rmse("PI", m) > mod_rmse("PL", m) for m in MOD_CON_LLUVIA)
assert max(mod_vc.loc[("PI", m), "nse"] for m in MOD_CON_LLUVIA) < mod_vc.loc[("PL", "M1"), "nse"]
# KGE fuera del ajuste (Gupta et al., 2009; lo calcula 16b con r, α y β por separado), para M4 y la climatología
MOD_TOLERANCIA_VOLUMEN = 0.05     # el texto dice que M4 reproduce el volumen fuera del ajuste: |β − 1| < 5 %
mod_kge = {(f, m, esq): tabla.loc[(f, m)] for f in MOD_FUENTES for m in (MOD_REFERENCIA, MOD_ELEGIDO)
           for esq, tabla in (("vc", mod_vc), ("partición", mod_part))}
for _esq in ("vc", "partición"):
    # con PL, M4 supera a la climatología en NSE y en KGE
    assert mod_kge[("PL", MOD_ELEGIDO, _esq)].kge > mod_kge[("PL", MOD_REFERENCIA, _esq)].kge
    assert mod_kge[("PL", MOD_ELEGIDO, _esq)].nse > mod_kge[("PL", MOD_REFERENCIA, _esq)].nse
    for _f in MOD_FUENTES:
        assert abs(mod_kge[(_f, MOD_ELEGIDO, _esq)].kge_beta - 1) < MOD_TOLERANCIA_VOLUMEN
# con PI, M4 se correlaciona menos con Q que con PL y reproduce menos su variabilidad (el texto lo dice)
assert mod_vc.loc[("PI", MOD_ELEGIDO), "kge_r"] < mod_vc.loc[("PL", MOD_ELEGIDO), "kge_r"]
assert mod_vc.loc[("PI", MOD_ELEGIDO), "kge_alfa"] < mod_vc.loc[("PL", MOD_ELEGIDO), "kge_alfa"]
# ¿queda M4 con PI por debajo de la climatología en KGE? El texto lo dice según lo que salga, en cada esquema
mod_pi_kge_bajo_m0 = {esq: mod_kge[("PI", MOD_ELEGIDO, esq)].kge < mod_kge[("PI", MOD_REFERENCIA, esq)].kge
                      for esq in ("vc", "partición")}

# qué modelos no superan a la climatología (el texto lo dice según lo que salga)
mod_no_superan = {f: [m for m in MOD_CON_LLUVIA if mod_rmse(f, m) >= mod_rmse(f, MOD_REFERENCIA)] for f in MOD_FUENTES}

# la ficha de M4: cuánto cambia Q si la lluvia sube un 10 %
MOD_CAMBIO_EJEMPLO = 0.10
mod_elasticidad = {f: {"mes": (1 + MOD_CAMBIO_EJEMPLO) ** mod_ficha.loc[f, "b0"] - 1,
                       "anterior": (1 + MOD_CAMBIO_EJEMPLO) ** mod_ficha.loc[f, "b1"] - 1,
                       "ambos": (1 + MOD_CAMBIO_EJEMPLO) ** mod_ficha.loc[f, "b0_mas_b1"] - 1} for f in MOD_FUENTES}
# la ficha dice qué supuestos se cumplen; aquí se fija que el texto de PL coincide con las pruebas
assert mod_ficha.loc["PL", "shapiro_residuo_p"] >= MOD_ALFA and mod_ficha.loc["PI", "shapiro_residuo_p"] < MOD_ALFA
assert mod_ficha.loc["PL", "spearman_abs_residuo_ajustado_p"] >= MOD_ALFA
assert mod_ficha.loc["PI", "spearman_abs_residuo_ajustado_p"] >= MOD_ALFA
assert (mod_ajuste.loc[(list(MOD_FUENTES), MOD_ELEGIDO), "estimados_negativos"] == 0).all()
# M2 con PI da caudal negativo dentro del rango de lluvia que ya se observó; con PL, por debajo de ese rango no
assert mod_ficha.loc["PI", "lluvia_q_cero_competidor"] > mod_ficha.loc["PI", "lluvia_mes_min"]
# M2 no cumple sus supuestos como M4: su error crece con la lluvia y sus residuos no son normales
assert all(mod_ajuste.loc[(f, MOD_COMPETIDOR), "varianza_tercio_lluvioso_sobre_seco"] > P2_RAZON_VARIANZA
           and mod_ajuste.loc[(f, MOD_COMPETIDOR), "shapiro_residuo_p"] < MOD_ALFA for f in MOD_FUENTES)
# los residuos de M4 no son independientes: su autocorrelación supera la banda de 95 % de una serie sin memoria
mod_banda_autocorr = 1.96 / np.sqrt(mod_diag.n_pares_consecutivos.min())
assert all(mod_ajuste.loc[(f, MOD_ELEGIDO), "autocorr_residuo_1_mes"] > mod_banda_autocorr for f in MOD_FUENTES)

# ¿conserva masa M4? (16b): su caudal contra la lluvia y la ETP de Hargreaves con ERA5-Land
mod_balance = pd.read_csv("out/modelos_balance.csv").set_index("fuente")
for _f in MOD_FUENTES:
    _b = mod_balance.loc[_f]
    # el texto dice que el volumen total casi coincide (menos de 2 %), que M4 da menos meses con Q > P que los
    # observados y que ningún año estimado tiene más caudal que lluvia
    assert abs(_b.diferencia_volumen_pct) < 2
    assert _b.meses_q_mayor_p_estimado < _b.meses_q_mayor_p_observado
    assert _b.anios_q_mayor_p_estimado == 0

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
_pq_ciclo = (_pq_con_q.groupby(_pq_con_q.index.month).pl_q.mean() - _pq_con_q.groupby(_pq_con_q.index.month).etp.mean())
pq_meses_guarda = [MESES_ES[m - 1] for m in _pq_ciclo.index[_pq_ciclo > 0]]


# ---------------------------------------------------------------- índice P/ETP: ¿húmeda o árida?
# P/ETP con las dos fuentes de lluvia (PL, que manda, y PI) y la ETP de Hargreaves con ERA5-Land (regla 15), sobre
# los meses de 1998-2022: el índice no usa Q, así que no se recorta a los meses comunes con el caudal.
# Clases de aridez de UNEP (Middleton y Thomas, 1997, World Atlas of Desertification, 2.ª ed., UNEP / Arnold,
# Londres): hiperárido < 0.05; árido 0.05-0.20; semiárido 0.20-0.50; subhúmedo seco 0.50-0.65; húmedo >= 0.65.
# UNEP definió el índice con la ETP de Thornthwaite; aquí se usa la de Hargreaves, así que la clase es aproximada.
UNEP_LIMITES = [(0.05, "hiperárido"), (0.20, "árido"), (0.50, "semiárido"), (0.65, "subhúmedo seco"),
                (np.inf, "húmedo")]                          # cada clase llega hasta su límite, sin incluirlo
UNEP_HUMEDO = 0.65                                           # desde aquí, húmedo


def clase_unep(indice):
    return next(nombre for limite, nombre in UNEP_LIMITES if indice < limite)


# los límites van en orden y el borde es como dice UNEP: 0.65 ya es húmedo, 0.6499 todavía no
assert [lim for lim, _ in UNEP_LIMITES] == sorted(lim for lim, _ in UNEP_LIMITES)
assert clase_unep(UNEP_HUMEDO) == "húmedo" and clase_unep(UNEP_HUMEDO - 1e-4) == "subhúmedo seco"
pe = pq[["pl", "pi", "etp"]]
# las tres series completas: todos los meses del período, sin huecos, y 12 meses en cada año
assert len(pe) == len(PERIODOS) and pe.notna().all().all()
assert (pe.groupby(pe.index.year).size() == 12).all()
pe_anual = pe.groupby(pe.index.year).sum()                   # totales de cada año (mm/año)
pe_etp_anual = float(pe_anual.etp.mean())
pe_indice = {}
for _f in ("pl", "pi"):
    _ie_anios = pe_anual[_f] / pe_anual.etp                 # el índice de cada año
    _p = float(pe_anual[_f].mean())
    pe_indice[_f] = {"p": _p, "ie": _p / pe_etp_anual, "clase": clase_unep(_p / pe_etp_anual),
                     "min": float(_ie_anios.min()), "anio_min": int(_ie_anios.idxmin()),
                     "max": float(_ie_anios.max()), "anio_max": int(_ie_anios.idxmax()),
                     "bajo_humedo": [int(a) for a in _ie_anios.index[_ie_anios < UNEP_HUMEDO]],
                     "clases_anios": sorted(set(_ie_anios.map(clase_unep)))}
pe_n_anios = len(pe_anual)
# Por mes del calendario: media de P del mes / media de ETP del mes, y en cuántos años ese mes tuvo P < ETP
_pe_mes = pe.groupby(pe.index.month).mean()
pe_mes = pd.DataFrame({f: _pe_mes[f] / _pe_mes.etp for f in ("pl", "pi")})
pe_mes_deficit_anios = pd.DataFrame({f: (pe[f] < pe.etp).groupby(pe.index.month).sum().astype(int) for f in ("pl", "pi")})
pe_meses_deficit = {f: [m for m in range(1, 13) if pe_mes.loc[m, f] < 1] for f in ("pl", "pi")}
pe_deficit_igual = pe_meses_deficit["pl"] == pe_meses_deficit["pi"]
pe_solo_pi = [m for m in pe_meses_deficit["pi"] if m not in pe_meses_deficit["pl"]]
pe_solo_pl = [m for m in pe_meses_deficit["pl"] if m not in pe_meses_deficit["pi"]]
# el índice anual es el cociente de los totales medios, y los conteos por mes no pasan del número de años
assert all(np.isclose(pe_indice[f]["ie"], pe_anual[f].mean() / pe_anual.etp.mean()) for f in ("pl", "pi"))
assert pe_mes_deficit_anios.to_numpy().max() <= pe_n_anios


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
pico_pi = picos(ciclo_lq.PI)
# ZCIT: según Mesa et al. (1997), pasa por el interior de Colombia en septiembre, octubre y noviembre (SON).
# El texto dice que el segundo pico de PL, PI y Q cae en esa temporada
MESES_SON = ("septiembre", "octubre", "noviembre")
assert all(p[1] in MESES_SON for p in (pico_pl, pico_pi, pico_q))
_c = ajuste_lq.loc[("PL", "mes_y_anterior")]
peso_mes_pl = _c.coef_mes / (_c.coef_mes + _c.coef_mes_anterior)      # parte que viene del mismo mes


def rho_rezago(antes, despues):
    """Spearman entre `antes` en el mes t y `despues` en el mes t+1."""
    return float(corr_rezago.loc[despues, antes])


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

cal_total = len(periodos)

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
fmt_p_eq = lambda p: "&lt; 0.001" if p < 0.001 else f"= {p:.3f}"     # para escribir «p < 0.001» o «p = 0.006»


an_pl = an_h[an_h.serie.str.startswith("PL")]
an_pl_sig = an_pl[an_pl.significativo]
an_pl_ok = an_pl[~an_pl.significativo]
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
an_rachas_pl = an_rachas[an_rachas.variable.str.startswith("PL")]
an_rachas_dia = an_rachas[~an_rachas.variable.str.startswith("PL")]
an_sesgo = an_cob.sesgo_estimado_pct.abs()
_nombre_pluvio = {c: cat_plu.loc[c, "etiqueta"] for c in cat_plu.index}
sesgo_pi_pl = (comp["IMERG"].mean() / comp["RED"].mean() - 1) * 100

# ---------------------------------------------------------------- control de calidad básico (4.2)
# Los chequeos sobre los archivos crudos los hace scripts/07b_control_calidad_basico.py; aquí se leen, y
# la revisión a mano de un mes completo está solo en la sección 4.2 del notebook.
cc = pd.read_csv("out/control_calidad_basico.csv")
cc_naturaleza = pd.read_csv("out/naturaleza_fuentes.csv")
cc_conteo = cc.resultado.value_counts()
cc_revisar = cc[cc.resultado == "revisar"]

# ---------------------------------------------------------------- registro de anomalías (4.4)
# El registro lo arma scripts/07d_trazabilidad.py con las cifras de los demás scripts; aquí solo se muestra.
# La columna «evidencia» (sección del notebook) no se muestra: el informe no nombra los puntos del taller.
reg = pd.read_csv("out/registro_anomalias.csv")
reg_conteo = reg.estado.value_counts()


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


# ---------------------------------------------------------------- cifras de los mapas
# Lo que antes estaba escrito a mano en los textos de los mapas, calculado.
_plu_dentro = cat_plu.loc[DENTRO]
mapa_plu_baja = _plu_dentro.loc[_plu_dentro.altitud.idxmin()]          # el pluviómetro más bajo
mapa_plu_alta = _plu_dentro.loc[_plu_dentro.altitud.idxmax()]          # y el más alto
_hips = pd.read_csv("out/curva_hipsometrica_fonce.csv")                 # fracción del área por encima de cada altura
mapa_pct_sin_pluvio = float(np.interp(mapa_plu_alta.altitud, _hips.altura_m, _hips.fraccion_area_encima)) * 100

# mapa de ubicación: el relieve de la región (Copernicus GLO-90 promediado, de 03b_relieve_regional.py)
with rasterio.open("out/relieve_region_copernicus.tif") as _rel:
    _z_rel = _rel.read(1)
    ubic_limites = _rel.bounds                                  # oeste, sur, este, norte (grados)
    ubic_paso_seg = abs(_rel.transform.a) * 3600                # tamaño de la celda, en segundos de arco
ubic_elev_min, ubic_elev_max = float(_z_rel.min()), float(_z_rel.max())
ubic_limites_gpkg = gpd.read_file("out/limites_region.gpkg", layer="departamentos")
assert "Santander" in set(ubic_limites_gpkg.nombre)            # el texto dice que Santander va resaltado
# área de una celda de 0.1° x 0.1° a la latitud media de los píxeles de IMERG, en el elipsoide WGS84
_lat = float(pix.lat.mean())
mapa_km2_pixel = abs(Geod(ellps="WGS84").polygon_area_perimeter(
    [0, 0.1, 0.1, 0], [_lat - 0.05, _lat - 0.05, _lat + 0.05, _lat + 0.05])[0]) / 1e6
mapa_km_lado = mapa_km2_pixel ** 0.5
mapa_area_chicas = {"Monchía": float(m.loc[24027060, "area"]), "Mogoticos": float(m.loc[24027040, "area"])}
_t_ciclo_mes = variables_resumen["T media"].groupby(variables_resumen.index.month).mean()
mapa_t_amplitud_anual = float(_t_ciclo_mes.max() - _t_ciclo_mes.min())    # mes más cálido menos el más frío
mapa_pct_px_calido = float(tpx.loc[tpx.t_media.idxmax(), "frac_dentro"]) * 100   # el píxel más cálido, % dentro


# ---------------------------------------------------------------- ¿se repite cada año? ¿es estable?
# 1. Año por año: a cada año con los 12 meses se le ajusta la misma curva de dos armónicos del régimen; el año
#    es bimodal si la curva tiene dos picos, y un pico del promedio «aparece» si algún pico del año cae a
#    ±EST_TOL meses. Como esa curva no puede tener más de dos picos, se contrasta con un método simple: el mes
#    más lluvioso de cada semestre a ±1 mes del mes del pico promedio. Q solo tiene los años con 12 meses: los
#    meses faltantes no se rellenan.
# 2. Dos mitades: el régimen completo en cada una, con un intervalo de A2/A1 remuestreando años. La
#    clasificación es estable si las dos mitades dan la misma clase y los picos no se corren más de EST_TOL.
EST_TOL = 1.0                                   # meses (decidido por el usuario)
EST_MITADES = {"1998–2010": ("1998-01", "2010-12"), "2011–2022": ("2011-01", "2022-12")}
EST_REMUESTREOS, EST_SEMILLA = 2000, 1
_est_t = np.arange(REG_PASOS) * 12 / REG_PASOS
_est_series = {"PL": variables_resumen["PL"], "PI": variables_resumen["PI"], "Q": _reg_q_mm}


def _est_picos(x):
    y = _reg_curva(np.asarray(x, float), _est_t)
    return _est_t[(y > np.roll(y, 1)) & (y > np.roll(y, -1))]


def _est_dist(a, b):
    """Distancia circular en meses (diciembre está a un mes de enero)."""
    d = abs(a - b) % 12
    return min(d, 12 - d)


def _est_razon(x):
    return np.hypot(*_reg_armonico(np.asarray(x, float), 2)) / np.hypot(*_reg_armonico(np.asarray(x, float), 1))


est_anual = {}
for _n, _s in _est_series.items():
    _p_clim = _est_picos(_reg_medianas(_s))
    _anios = [a for a in sorted(set(_s.index.year)) if _s[_s.index.year == a].notna().sum() == 12]
    _f = []
    for _a in _anios:
        _x = _s[_s.index.year == _a].to_numpy()
        _pa = _est_picos(_x)
        _d = [min(_est_dist(pc, p) for p in _pa) for pc in _p_clim]
        _m1, _m2 = int(np.argmax(_x[:6])), 6 + int(np.argmax(_x[6:]))
        _f.append({"bimodal": len(_pa) == 2, "p1": _d[0] <= EST_TOL, "p2": _d[1] <= EST_TOL, "dist": max(_d),
                   "a1_domina": _est_razon(_x) < 1,
                   "simple": _est_dist(_m1, round(_p_clim[0]) % 12) <= 1 and _est_dist(_m2, round(_p_clim[1]) % 12) <= 1})
    _f = pd.DataFrame(_f)
    est_anual[_n] = {"anios": len(_anios), "picos": [MESES_LARGOS_ES[int(round(p)) % 12] for p in _p_clim],
                     "bimodales": int(_f.bimodal.sum()), "p1": int(_f.p1.sum()), "p2": int(_f.p2.sum()),
                     "los_dos": int((_f.p1 & _f.p2).sum()), "dist_mediana": float(_f.dist.median()),
                     "dist_max": float(_f.dist.max()), "a1_domina": int(_f.a1_domina.sum()), "simple": int(_f.simple.sum())}

_est_rng = np.random.default_rng(EST_SEMILLA)
est_mitades = {}
for _n, _s in _est_series.items():
    est_mitades[_n] = {}
    for _nom, (_ini, _fin) in EST_MITADES.items():
        _x = _s.loc[_ini:_fin]
        _med = _reg_medianas(_x)
        _kw = stats.kruskal(*[_x[_x.index.month == m].dropna() for m in range(1, 13)]).pvalue
        _pk = _est_picos(_med)
        _por = {a: _x[_x.index.year == a] for a in sorted(set(_x.index.year))}
        _bs = [_est_razon(_reg_medianas(pd.concat([_por[a] for a in _est_rng.choice(list(_por), len(_por))])))
               for _ in range(EST_REMUESTREOS)]
        est_mitades[_n][_nom] = {
            "clase": "estacionalidad débil" if _kw >= ALFA_KW else ("bimodal" if len(_pk) == 2 else "unimodal"),
            "kw": _kw, "pk": _pk, "picos": [MESES_LARGOS_ES[int(round(p)) % 12] for p in _pk],
            "razon": _est_razon(_med), "ic": tuple(np.percentile(_bs, [2.5, 97.5])), "meses": int(_x.notna().sum())}
    _m1, _m2 = est_mitades[_n].values()
    _corr = ([_est_dist(a, b) for a, b in zip(sorted(_m1["pk"]), sorted(_m2["pk"]))]
             if len(_m1["pk"]) == len(_m2["pk"]) else None)
    est_mitades[_n]["corrimiento"] = _corr
    est_mitades[_n]["estable"] = _m1["clase"] == _m2["clase"] and _corr is not None and all(d <= EST_TOL for d in _corr)
    est_mitades[_n]["ic_se_traslapan"] = _m1["ic"][0] <= _m2["ic"][1] and _m2["ic"][0] <= _m1["ic"][1]
est_todas_estables = all(est_mitades[n]["estable"] for n in _est_series)
# la serie cuya razón A2/A1 más cambia entre mitades, en proporción
est_mas_cambia = max(_est_series, key=lambda n: abs(np.log(est_mitades[n]["2011–2022"]["razon"] /
                                                            est_mitades[n]["1998–2010"]["razon"])))
est_enso = {nom: oni_fase[(oni_fase.index >= pd.Period(a, "M")) & (oni_fase.index <= pd.Period(b, "M"))].value_counts()
            for nom, (a, b) in EST_MITADES.items()}


# ---------------------------------------------------------------- años que se salen de lo normal
# Anomalía de un mes = (valor - mediana de su mes del calendario) / rango intercuartil de ese mes: es atip_z, la
# misma de «Revisión de outliers» (decidido por el usuario). La anomalía de un año es el promedio de sus 12
# anomalías mensuales; para Q solo en los años con los 12 meses. Los años contrastantes son los
# ANOM_N_EXTREMOS más húmedos y los ANOM_N_EXTREMOS más secos según el promedio de las anomalías anuales de PL
# y PI: años en que las dos fuentes de lluvia coinciden (decidido por el usuario).
ANOM_N_EXTREMOS = 2
_anom = atip_z[["PL", "PI", "Q"]]
anom_rho = {f"{a}–{b}": {"tal cual": stats.spearmanr(*variables_resumen[[a, b]].dropna().T.values)[0],
                         "anomalías": stats.spearmanr(*_anom[[a, b]].dropna().T.values)[0]}
            for a, b in (("PL", "Q"), ("PI", "Q"), ("PI", "PL"))}
anom_anual = pd.DataFrame({v: _anom[v].groupby(_anom.index.year).mean() for v in ("PL", "PI")})
_anom_q_meses = _anom.Q.notna().groupby(_anom.index.year).sum()
anom_anual["Q"] = _anom.Q.groupby(_anom.index.year).mean().where(_anom_q_meses == 12)
anom_n_q = int(anom_anual.Q.notna().sum())
anom_rho_anual_pl_q = stats.spearmanr(*anom_anual[["PL", "Q"]].dropna().T.values)[0]
anom_anual["PL y PI"] = anom_anual[["PL", "PI"]].mean(axis=1)
_orden = anom_anual["PL y PI"].sort_values()
anom_humedos = list(_orden.index[::-1][:ANOM_N_EXTREMOS])
anom_secos = list(_orden.index[:ANOM_N_EXTREMOS])
anom_pi_humedos = list(anom_anual.PI.sort_values().index[::-1][:ANOM_N_EXTREMOS])
anom_pi_secos = list(anom_anual.PI.sort_values().index[:ANOM_N_EXTREMOS])
anom_mediana_pl = variables_resumen.PL.groupby(variables_resumen.index.month).median()
anom_tipico_pl = float(anom_mediana_pl.sum())              # el año típico: la suma de las 12 medianas
anom_anios = {}
for _a in anom_humedos + anom_secos:
    _x = variables_resumen.PL[variables_resumen.index.year == _a].to_numpy()
    _y = _reg_curva(_x, _est_t)
    _fases = oni_fase[oni_fase.index.year == _a].value_counts()
    anom_anios[_a] = {"tipo": "húmedo" if _a in anom_humedos else "seco", "pl": float(_x.sum()),
                      "z_pl": float(anom_anual.PL[_a]), "z_pi": float(anom_anual.PI[_a]),
                      "z_q": None if pd.isna(anom_anual.Q[_a]) else float(anom_anual.Q[_a]),
                      "meses_sobre": int((_x > anom_mediana_pl.to_numpy()).sum()),
                      "picos": [MESES_LARGOS_ES[int(round(p)) % 12]
                                for p in _est_t[(_y > np.roll(_y, 1)) & (_y > np.roll(_y, -1))]],
                      "razon": _est_razon(_x), "nina": int(_fases.get("La Niña", 0)), "nino": int(_fases.get("El Niño", 0)),
                      "serie": [round(float(v), 1) for v in _x]}
anom_todos_bimodales = all(len(r["picos"]) == 2 for r in anom_anios.values())
# años que serían extremos con PL sola pero no con las dos fuentes
anom_solo_pl = [a for a in anom_anual.PL.sort_values().index[::-1][:ANOM_N_EXTREMOS] if a not in anom_humedos]
# el mes más extremo de la serie: el de mayor anomalía promedio de PL, PI y Q, con las tres sobre lo normal
_anom_tres = _anom.dropna()
anom_mes_extremo = _anom_tres[(_anom_tres > 0).all(axis=1)].mean(axis=1).idxmax()
# años contrastantes en que el armónico de 12 meses pesa más que el de 6, y sus meses muy húmedos (anomalía de PL > 1)
anom_a1_domina = {a: [MESES_LARGOS_ES[p.month - 1] for p in _anom.index[(_anom.index.year == a) & (_anom.PL > 1)]]
                  for a, r in anom_anios.items() if r["razon"] < 1}
# lo que el texto afirma; si los datos dejan de respaldarlo, el script se detiene
assert anom_rho["PL–Q"]["anomalías"] > 0
assert (anom_rho["PL–Q"]["tal cual"] - anom_rho["PL–Q"]["anomalías"]) < (anom_rho["PI–Q"]["tal cual"] - anom_rho["PI–Q"]["anomalías"])
assert anom_anios[anom_humedos[0]]["meses_sobre"] > 6 and anom_anios[anom_secos[0]]["meses_sobre"] < 6
assert anom_anios[anom_humedos[0]]["nina"] >= 6 and anom_anios[anom_secos[0]]["nino"] >= 6


# ---------------------------------------------------------------- mapa año–mes de valores
# Una matriz por variable: filas = años del período, columnas = los 12 meses, valor del mes tal cual. Va en la
# sección del ciclo anual, pero se calcula aquí porque su lectura usa los picos de «¿se repite cada año?» y los
# años contrastantes de las anomalías. Usa TODOS los meses válidos de cada variable (variables_resumen), no los
# meses comunes de la tabla y las cajas (decisión del usuario, 2026-10-08): el mapa muestra cada año, no compara
# fuentes. Los meses sin dato quedan vacíos (NaN); no se rellena nada.
MAPA_AM_VARIABLES = [("PL", "mm/mes", 0), ("PI", "mm/mes", 0), ("Q", "m³/s", 1), ("T media", "°C", 1)]
MAPA_AM_ANIOS = list(range(PERIODOS[0].year, PERIODOS[-1].year + 1))
mapa_am = {}
for _v, _u, _dec in MAPA_AM_VARIABLES:
    _s = variables_resumen[_v]
    mapa_am[_v] = (pd.DataFrame({"anio": _s.index.year, "mes": _s.index.month, "valor": _s.to_numpy()})
                   .pivot(index="anio", columns="mes", values="valor").reindex(index=MAPA_AM_ANIOS, columns=range(1, 13)))
mapa_am_vacias = {v: int(m.isna().sum().sum()) for v, m in mapa_am.items()}
# la matriz es la serie mensual reacomodada: 12 meses por año y los mismos vacíos que la serie
assert all(m.shape == (len(MAPA_AM_ANIOS), 12) for m in mapa_am.values())
assert all(mapa_am_vacias[v] == int(variables_resumen[v].isna().sum()) for v in mapa_am)
# la nota del mapa dice que los vacíos son solo de Q
assert [v for v, k in mapa_am_vacias.items() if k > 0] == ["Q"]


# Lectura del mapa, con PL y PI en paralelo:
# 1. Los dos picos año a año: es el «método simple» de est_anual (el mes más lluvioso de cada semestre a ±1 mes del
#    pico promedio de esa fuente); aquí solo se nombran las ventanas de meses que resultan.
def _ventana(nombre_pico):
    i = MESES_LARGOS_ES.index(nombre_pico)
    return f"{MESES_ES[(i - 1) % 12]}–{MESES_ES[(i + 1) % 12]}"


mapa_am_picos = {f: {"picos": est_anual[f]["picos"], "ventanas": [_ventana(p) for p in est_anual[f]["picos"]],
                     "anios": est_anual[f]["anios"], "simple": est_anual[f]["simple"]} for f in ("PL", "PI")}
# el texto dice que los dos picos aparecen en la mayoría de los años, con las dos fuentes
assert all(r["simple"] > r["anios"] / 2 for r in mapa_am_picos.values())
# 2. Años húmedos o secos de punta a punta: cuántos meses de cada año quedan por encima (y por debajo) de la mediana
#    de su mes; la cuenta «por encima» es la de «Meses sobre lo normal» de los años contrastantes. Se nombran los años
#    con más y con menos meses por encima, y si coinciden con los años contrastantes de las anomalías.
mapa_am_sobre = {}
for _f in ("PL", "PI"):
    _s = variables_resumen[_f]
    _mediana_mes = _s.groupby(_s.index.month).transform("median")
    _sobre = (_s > _mediana_mes).groupby(_s.index.year).sum().astype(int)
    _bajo = (_s < _mediana_mes).groupby(_s.index.year).sum().astype(int)
    _mas, _menos = int(_sobre.max()), int(_sobre.min())
    _anios_mas = [int(a) for a in _sobre.index[_sobre == _mas]]
    _anios_menos = [int(a) for a in _sobre.index[_sobre == _menos]]
    mapa_am_sobre[_f] = {"mas": _mas, "anios_mas": _anios_mas, "menos": _menos, "anios_menos": _anios_menos,
                         "bajo_menos": [int(_bajo[a]) for a in _anios_menos],
                         "coinciden_humedos": [a for a in _anios_mas if a in anom_humedos],
                         "coinciden_secos": [a for a in _anios_menos if a in anom_secos]}
    if _f == "PL":
        # es la misma cuenta de la tabla de los años contrastantes
        assert all(int(_sobre[a]) == r["meses_sobre"] for a, r in anom_anios.items())
# el texto dice que hay años con la mayoría de los meses por encima de lo normal y años con la mayoría por debajo
assert all(r["mas"] > 6 and min(r["bajo_menos"]) > 6 for r in mapa_am_sobre.values())


# ---------------------------------------------------------------- registro largo (1981-2022) para tendencias
# Regla 6: las tendencias usan el registro completo de cada variable desde 1981, cuando exista; las
# comparaciones entre variables, 1998-2022. Q (CAMELS-COL) y la temperatura (ERA5-Land, descargada desde
# 1981 por scripts/06) tienen registro largo; PI empieza en 1998 (IMERG) y PL, por ahora, solo está
# descargada para 1998-2022, así que para ellas el registro completo es 1998-2022.
LARGO_DESDE = "1981-01"
PERIODOS_LARGO = pd.period_range(LARGO_DESDE, f"{max(ANIOS_ESTUDIO)}-12", freq="M")
_cam_largo = pd.read_csv("data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_24027010.txt",
                         sep="\t", encoding="latin-1")
_cam_largo.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
_cam_largo["fecha"] = pd.to_datetime(_cam_largo["fecha"], format="%d/%m/%Y")
_cam_largo = _cam_largo.set_index("fecha").sort_index().reindex(
    pd.date_range(f"{LARGO_DESDE}-01", f"{max(ANIOS_ESTUDIO)}-12-31", freq="D"))
_era_largo = (pd.read_csv("out/era5land_temperatura_diaria_fonce_1981_2022.csv", parse_dates=["fecha"])
              .set_index("fecha").reindex(_cam_largo.index))
# PL* (decidido por el usuario el 2026-10-08): para tendencias y para las anomalías de esa sección, PL se arma con
# una RED FIJA, la que construye scripts/07 (estaciones con registro desde 1981, sin Pueblo Viejo, sin las
# exclusiones vigentes ni los picos extremos que los vecinos no acompañan). Así la composición de la red no cambia
# en el tiempo y no puede fabricar una tendencia. La PL del resto del informe no cambia.
_plf = pd.read_csv("out/pluviometros_pl_larga_1981_2022.csv", parse_dates=["fecha"])
_plf["periodo"] = _plf.fecha.dt.to_period("M")
pl_estrella_matriz = _plf.pivot(index="periodo", columns="codigo", values="precipitacion_mm").reindex(PERIODOS_LARGO)
pl_estrella_red = list(pl_estrella_matriz.columns)
pl_estrella_excluidos = pd.read_csv("out/pluviometros_pl_larga_excluidos.csv")
pl_estrella_rachas = pd.read_csv("out/pluviometros_pl_larga_rachas.csv")
# los umbrales del criterio de picos viven en scripts/07; aquí se repiten solo para citarlos en el texto, y se
# comprueba que coincidan con los de ese script
PICO_VECES_MEDIANA_INF, PICO_MINIMO_INF, PICO_VECES_VECINOS_INF = 3.0, 300.0, 3.0
_s07 = Path("scripts/07_pluviometros_dhime.py").read_text(encoding="utf-8")
assert all(f"{n} = {v}" in _s07 for n, v in (("PICO_VECES_MEDIANA", PICO_VECES_MEDIANA_INF), ("PICO_MINIMO_MM", PICO_MINIMO_INF),
                                              ("PICO_VECES_VECINOS", PICO_VECES_VECINOS_INF)))
largo = pd.DataFrame({
    "PL*": pl_estrella_matriz.mean(axis=1, skipna=True),
    "PI": variables_resumen["PI"].reindex(PERIODOS_LARGO),
    "Q": a_mensual(_cam_largo["caudal"], "mean", PERIODOS_LARGO),
    **{nombre: a_mensual(_era_largo[col], "mean", PERIODOS_LARGO)
       for nombre, col in (("T mín", "t_min"), ("T media", "t_media"), ("T máx", "t_max"))},
})
# el tramo 1998-2022 del registro largo es idéntico a la serie que usa todo el informe
_comunes = [c for c in largo.columns if c in variables_resumen.columns]
assert np.allclose(largo.loc[PERIODOS, _comunes].to_numpy(), variables_resumen[_comunes].to_numpy(), equal_nan=True)
LARGO_VARS = list(largo.columns)
# fase del ENSO de cada mes desde 1981 (scripts/17), para colorear el fondo de las series de tiempo; se agrupan los
# meses seguidos con la misma fase en tramos
_enso = pd.read_csv("out/oni_mensual_1981_2022.csv")
_enso = _enso.set_index(pd.PeriodIndex(_enso.periodo, freq="M"))["fase"].reindex(PERIODOS_LARGO)
enso_tramos = []
for _fase, _g in _enso.groupby((_enso != _enso.shift()).cumsum()):
    if _g.iloc[0] in ("El Niño", "La Niña"):
        enso_tramos.append((_g.index[0], _g.index[-1], _g.iloc[0]))
LARGO_UNIDADES = {"PL*": "mm/mes", "PI": "mm/mes", "Q": "m³/s", "T mín": "°C", "T media": "°C", "T máx": "°C"}
LARGO_FUENTE = {"PL*": "red fija de pluviómetros del IDEAM (DHIME)", "PI": "IMERG V07", "Q": "CAMELS-COL (IDEAM)",
                "T mín": "ERA5-Land", "T media": "ERA5-Land", "T máx": "ERA5-Land"}
# cambios de fuente o de procesamiento dentro de cada serie, conocidos y documentados en DATOS_FUENTES.md
LARGO_CAMBIOS = {"PL*": "ninguno en la composición (red fija); dos estaciones con salto de nivel marcado como incierto",
                 "PI": "calibración con TRMM hasta 2014-05 y con GPM desde 2014-06",
                 "Q": "ninguno conocido", "T mín": "ninguno conocido", "T media": "ninguno conocido",
                 "T máx": "ninguno conocido"}
largo_registro = {}
for _v in LARGO_VARS:
    _s = largo[_v].dropna()
    _tramo = largo[_v].loc[_s.index[0]:_s.index[-1]]
    largo_registro[_v] = {"inicio": _s.index[0], "fin": _s.index[-1], "meses": len(_tramo),
                          "validos": int(_tramo.notna().sum()), "vacios": int(_tramo.isna().sum())}


def _pettitt(x):
    """Prueba de Pettitt (1979), la misma de scripts/07c: índice del último elemento del primer tramo y p."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    # U_t = Σ_{i<=t} Σ_{j>t} sgn(x_i - x_j) = suma acumulada de Σ_j sgn(x_i - x_j): la misma U que en scripts/07c,
    # calculada en orden n² en vez de n³ (comprobado igual, también con empates)
    u = np.cumsum(np.sign(x[:, None] - x[None, :]).sum(axis=1))[:-1]
    k = int(np.argmax(np.abs(u)))
    return k, min(1.0, 2 * np.exp(-6 * float(abs(u[k])) ** 2 / (n ** 3 + n ** 2)))


# Control de calidad de lo anterior a 1998 (regla 6: antes de usarlo se revisa). Q: las pruebas de scripts/07c
# (rachas de valores iguales y picos aislados en el caudal diario) y un salto en el coeficiente de escorrentía
# anual Q / P, con la P de CHIRPS que trae CAMELS-COL desde 1981: si la curva de gasto de la estación hubiera
# cambiado, ese coeficiente saltaría. Temperatura: rachas, la desigualdad mín <= media <= máx y el contraste
# con la temperatura MSWX de CAMELS-COL, el único otro producto que llega a 1981.
LARGO_RACHA_DIAS = 5        # los mismos umbrales de scripts/07c
LARGO_FACTOR_PICO = 3.0
LARGO_MESES_ANIO = 10       # un año entra al coeficiente de escorrentía si tiene al menos 10 meses con Q y P
_qv = _cam_largo["caudal"].dropna()
_vecino = np.maximum(_cam_largo["caudal"].shift(1), _cam_largo["caudal"].shift(-1))
_q_mm = largo["Q"] * largo.index.days_in_month * 86400 / (AREA_SG_KM2 * 1e6) * 1000
_p_ch = a_mensual(_cam_largo["p_chirps"], "sum", PERIODOS_LARGO)
_ok = _q_mm.notna() & _p_ch.notna()
_coef = pd.DataFrame({"q": _q_mm[_ok], "p": _p_ch[_ok]}).groupby(lambda p: p.year).sum()
_coef = (_coef.q / _coef.p)[_ok.groupby(lambda p: p.year).sum() >= LARGO_MESES_ANIO]
_k_coef, _p_coef = _pettitt(_coef.to_numpy())
_era_ok = _era_largo.dropna()
_mswx = ((_cam_largo["t_min"] + _cam_largo["t_max"]) / 2).groupby(lambda d: d.year).mean()
_dif_t = (_era_largo["t_media"].groupby(lambda d: d.year).mean() - _mswx).dropna()
_k_dif, _p_dif = _pettitt(_dif_t.to_numpy())
largo_qc = {
    "q_dias_sin_dato": int(_cam_largo["caudal"].isna().sum()), "q_dias": len(_cam_largo),
    "q_rachas": int((_qv.groupby((_qv != _qv.shift()).cumsum()).size() >= LARGO_RACHA_DIAS).sum()),
    "q_picos": int((_cam_largo["caudal"] >= LARGO_FACTOR_PICO * _vecino).sum()),
    "q_min": float(_qv.min()),
    "coef_anios": len(_coef), "coef_p": _p_coef,
    "q_media_antes": float(largo["Q"].loc[:"1997-12"].mean()), "q_media_despues": float(largo["Q"].loc["1998-01":].mean()),
    "t_faltantes": int(_era_largo["t_media"].isna().sum()),
    "t_desigualdad": int((~((_era_ok.t_min <= _era_ok.t_media) & (_era_ok.t_media <= _era_ok.t_max))).sum()),
    "t_rachas": int(sum((_era_ok[c].groupby((_era_ok[c] != _era_ok[c].shift()).cumsum()).size() >= LARGO_RACHA_DIAS).sum()
                        for c in ("t_min", "t_media", "t_max"))),
    "mswx_dif_media": float(_dif_t.mean()), "mswx_corte": int(_dif_t.index[_k_dif]), "mswx_p": _p_dif,
    "mswx_salto": float(_dif_t.iloc[_k_dif + 1:].mean() - _dif_t.iloc[: _k_dif + 1].mean()),
}
assert largo_qc["q_rachas"] == 0 and largo_qc["q_picos"] == 0 and largo_qc["q_min"] > 0
assert largo_qc["t_faltantes"] == 0 and largo_qc["t_desigualdad"] == 0 and largo_qc["t_rachas"] == 0


# ---------------------------------------------------------------- anomalías y anomalías estandarizadas
# a_t = X_t − µ_j y z_t = a_t / s_j, con µ_j y s_j la media y la desviación estándar del mes j del calendario en
# un período de referencia FIJO: 1998-2022 (decidido por el usuario), el único en que existen las seis variables,
# así que todas se miden contra la misma referencia. No se usa una media única para todos los meses ni una
# climatología móvil (que se llevaría parte de la tendencia). Con registro largo (Q y temperatura), la misma
# µ_j y s_j de 1998-2022 se aplica a todos sus meses. Las anomalías robustas (mediana y RIC) de «Revisión de
# outliers» y «Años que se salen de lo normal» se usan tal como están (decidido por el usuario).
ANZ_REFERENCIA = (PERIODOS[0], PERIODOS[-1])
ANZ_SEMILLA, ANZ_REMUESTREOS = 11, 2000
ANZ_UMBRAL_Z = 2.0          # para contar meses extremos: en una normal, |z| > 2 en el 4.55 % de los casos
ANZ_ALFA = 0.05
_mes_largo = largo.index.month
_ref = largo.loc[ANZ_REFERENCIA[0]:ANZ_REFERENCIA[1]]
anz_mu = _ref.groupby(_ref.index.month).mean()
anz_s = _ref.groupby(_ref.index.month).std(ddof=1)
anz_n = _ref.groupby(_ref.index.month).count()
assert (anz_s > 0).all().all(), "s_j = 0: la estandarización no está definida en ese mes"
anz_a = largo - anz_mu.reindex(_mes_largo).to_numpy()
anz_z = anz_a / anz_s.where(anz_s > 0).reindex(_mes_largo).to_numpy()
# inestabilidad de s_j: intervalo de confianza 95 % por remuestreo de años, relativo al propio s_j
_rng_anz = np.random.default_rng(ANZ_SEMILLA)
anz_s_ic = {}
for _v in LARGO_VARS:
    for _m in range(1, 13):
        _x = _ref[_v][_ref.index.month == _m].dropna().to_numpy()
        _bs = np.array([np.std(_rng_anz.choice(_x, len(_x)), ddof=1) for _ in range(ANZ_REMUESTREOS)])
        anz_s_ic[(_v, _m)] = (np.percentile(_bs, 2.5), np.percentile(_bs, 97.5))
anz_ancho_rel = pd.DataFrame({_v: [(anz_s_ic[(_v, m)][1] - anz_s_ic[(_v, m)][0]) / anz_s.loc[m, _v] * 100
                                   for m in range(1, 13)] for _v in LARGO_VARS}, index=range(1, 13))
# estandarizar no normaliza: forma de z en el período de referencia
_z_ref = anz_z.loc[ANZ_REFERENCIA[0]:ANZ_REFERENCIA[1]]
_a_ref = anz_a.loc[ANZ_REFERENCIA[0]:ANZ_REFERENCIA[1]]
anz_forma = {}
for _v in LARGO_VARS:
    _zz = _z_ref[_v].dropna()
    anz_forma[_v] = {"n": len(_zz), "asim": float(stats.skew(_zz, bias=False)),
                     "extremos": float((_zz.abs() > ANZ_UMBRAL_Z).mean() * 100),
                     "shapiro_p": float(stats.shapiro(_zz)[1]),
                     "r_x_a": float(_ref[_v].corr(_a_ref[_v])), "r_a_z": float(_a_ref[_v].corr(_z_ref[_v]))}
anz_normal_extremos = float(2 * stats.norm.sf(ANZ_UMBRAL_Z) * 100)
anz_no_normales = [v for v in LARGO_VARS if anz_forma[v]["shapiro_p"] < ANZ_ALFA]
# lo que el texto afirma
assert anz_forma["Q"]["asim"] == max(f["asim"] for f in anz_forma.values())
assert anz_forma["T media"]["r_x_a"] > max(anz_forma[v]["r_x_a"] for v in ("PL*", "PI", "Q"))
assert min(f["r_a_z"] for f in anz_forma.values()) > 0.9
assert anz_ancho_rel["Q"].max() == anz_ancho_rel.max().max()


# ---------------------------------------------------------------- tendencias
# Dos preguntas (enunciado del taller): (1) todos los datos, la secuencia cronológica de meses, y (2) mes a mes,
# las doce subseries (todos los eneros, todos los febreros…). Cada una en las tres representaciones: X, a y z.
# El tiempo es la fecha real del mes en años decimales (año + (mes − 0.5) / 12), aun con vacíos. Las pendientes
# se dan por década. No se ajusta una tendencia a las 12 medias climatológicas: eso describe el ciclo anual.
#
# Métodos (escogidos por el agente; ver PR):
# - Pendiente por mínimos cuadrados (OLS). En la secuencia de meses, los errores están autocorrelacionados
#   (un mes húmedo suele seguir a otro), así que su error estándar se corrige con Newey-West (1987), con
#   TEND_REZAGOS meses de rezago. En la serie original X se controla la estacionalidad con una constante
#   por mes del calendario (12 variables indicadoras), de modo que la pendiente no la arrastre el ciclo anual.
# - Como contraste no paramétrico: Mann-Kendall con la pendiente de Sen (Sen, 1968); para X, la versión
#   estacional de Hirsch, Slack y Smith (1982), que compara cada mes solo con el mismo mes de otros años.
# - Mes a mes: OLS y Mann-Kendall en cada subserie anual (12 a 42 años), sin corrección de autocorrelación.
# Período de cada prueba: el registro completo de cada variable (la pregunta de largo plazo) y, aparte,
# 1998-2022 (el período común, para comparar fuentes). Para PI los dos coinciden.
TEND_ALFA = 0.05
TEND_REZAGOS = 12


def _t_decimal(periodos):
    return np.asarray(periodos.year + (periodos.month - 0.5) / 12, dtype=float)


def _ols_hac(y, X, rezagos):
    """OLS con error estándar de Newey-West (núcleo de Bartlett). Devuelve coeficientes, errores y p (normal)."""
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


def _mk_estacional(t, y, meses):
    """Mann-Kendall estacional (Hirsch et al., 1982) y pendiente estacional de Sen: suma de las S de cada mes."""
    S, var, pendientes = 0.0, 0.0, []
    for m in np.unique(meses):
        tm, ym = t[meses == m], y[meses == m]
        n = len(ym)
        if n < 3:
            continue
        S += np.sign(ym[None, :] - ym[:, None])[np.triu_indices(n, 1)].sum()
        var += n * (n - 1) * (2 * n + 5) / 18
        i, j = np.triu_indices(n, 1)
        dt = tm[j] - tm[i]
        validos = dt != 0          # al remuestrear años un mismo año puede repetirse: esos pares no dan pendiente
        pendientes.extend((ym[j] - ym[i])[validos] / dt[validos])
    zc = (S - np.sign(S)) / np.sqrt(var)
    return float(np.median(pendientes)), float(2 * stats.norm.sf(abs(zc)))


def _mk(t, y):
    """Mann-Kendall (con la tau de Kendall) y pendiente de Sen."""
    return float(stats.theilslopes(y, t)[0]), float(stats.kendalltau(t, y).pvalue)


TEND_PERIODOS = {"completo": None, "1998–2022": (PERIODOS[0], PERIODOS[-1])}
tend_todos, tend_mes = {}, {}
for _v in LARGO_VARS:
    for _per, _lim in TEND_PERIODOS.items():
        _rep = {"X": largo[_v], "a": anz_a[_v], "z": anz_z[_v]}
        if _lim is not None:
            _rep = {k: s.loc[_lim[0]:_lim[1]] for k, s in _rep.items()}
        _rep = {k: s.dropna() for k, s in _rep.items()}
        _idx = _rep["X"].index
        _t = _t_decimal(_idx)
        _meses = np.asarray(_idx.month)
        # (1) todos los datos
        _ind = (_meses[:, None] == np.arange(1, 13)[None, :]).astype(float)
        _bx, _sx, _px = _ols_hac(_rep["X"].to_numpy(), np.column_stack([_t, _ind]), TEND_REZAGOS)
        _fila = {"inicio": _idx[0], "fin": _idx[-1], "n": len(_idx),
                 "X": {"ols": _bx[0] * 10, "p": _px[0], "mk": None, "p_mk": None}}
        _sen, _pmk = _mk_estacional(_t, _rep["X"].to_numpy(), _meses)
        _fila["X"].update(mk=_sen * 10, p_mk=_pmk)
        for _k in ("a", "z"):
            _b, _se, _p = _ols_hac(_rep[_k].to_numpy(), np.column_stack([np.ones_like(_t), _t]), TEND_REZAGOS)
            _sen, _pmk = _mk(_t, _rep[_k].to_numpy())
            _fila[_k] = {"ols": _b[1] * 10, "p": _p[1], "mk": _sen * 10, "p_mk": _pmk, "corte": _b[0]}
        tend_todos[(_v, _per)] = _fila
        # (2) mes a mes
        for _m in range(1, 13):
            _sel = _meses == _m
            _tm = _t[_sel]
            _r = {k: stats.linregress(_tm, _rep[k].to_numpy()[_sel]) for k in ("X", "a", "z")}
            # dentro de un mes y con la misma muestra: restar µ_j no cambia la pendiente; dividir por s_j > 0
            # solo cambia su escala; y la p es la misma en las tres. No son evidencias independientes.
            assert np.isclose(_r["a"].slope, _r["X"].slope) and np.isclose(_r["a"].pvalue, _r["X"].pvalue)
            assert np.isclose(_r["z"].slope, _r["a"].slope / anz_s.loc[_m, _v]) and np.isclose(_r["z"].pvalue, _r["X"].pvalue)
            _sen, _pmk = _mk(_tm, _rep["X"].to_numpy()[_sel])
            tend_mes[(_v, _per, _m)] = {"n": int(_sel.sum()), "X": _r["X"].slope * 10, "z": _r["z"].slope * 10,
                                        "p": _r["X"].pvalue, "sen": _sen * 10, "p_mk": _pmk}
# en la secuencia de meses, X (con constantes por mes) y a (sin ellas) dan casi la misma pendiente; no es
# exactamente igual porque µ_j sale de 1998-2022 y los vacíos no caen parejo en todos los meses
tend_dif_x_a = max(abs(f["X"]["ols"] - f["a"]["ols"]) / abs(f["a"]["ols"]) * 100
                   for f in tend_todos.values() if abs(f["a"]["ols"]) > 0)
# mes a mes: cuántos meses tienen tendencia significativa, contra los que saldrían solo por azar
tend_conteo = {}
for _v in LARGO_VARS:
    for _per in TEND_PERIODOS:
        _sig = [m for m in range(1, 13) if tend_mes[(_v, _per, m)]["p"] < TEND_ALFA]
        _sig_mk = [m for m in range(1, 13) if tend_mes[(_v, _per, m)]["p_mk"] < TEND_ALFA]
        tend_conteo[(_v, _per)] = {"meses": _sig, "meses_mk": _sig_mk,
                                   "p_azar": float(stats.binom.sf(len(_sig) - 1, 12, TEND_ALFA)) if _sig else 1.0}
tend_esperados_azar = 12 * TEND_ALFA


def tend_signif(fila, clave="p"):
    return fila[clave] < TEND_ALFA


# lo que el texto afirma sobre la temperatura de largo plazo: sube en las tres, con las dos pruebas
tend_t_sube = all(tend_todos[(v, "completo")]["a"]["ols"] > 0 and tend_todos[(v, "completo")]["a"]["p"] < TEND_ALFA
                  and tend_todos[(v, "completo")]["X"]["p_mk"] < TEND_ALFA for v in ("T mín", "T media", "T máx"))

# Sensibilidad de la tendencia de PL*. Dos estaciones de la red fija tienen un salto de nivel marcado como
# incierto (Coromoro desde 2003-03 y Valle de San José desde 1998-04, este visto al extender el registro); un salto
# dentro de un promedio puede aparecer como tendencia. Se repite la prueba (1) sin esas dos estaciones y (2) con la
# PL de siempre (la red completa) en 1998-2022, para ver si la conclusión depende de la red.
TEND_ESTACIONES_CON_SALTO = [24020120, 24020080]


def _tend_x(serie):
    serie = serie.dropna()
    _t, _m = _t_decimal(serie.index), np.asarray(serie.index.month)
    _b, _se, _p = _ols_hac(serie.to_numpy(), np.column_stack([_t, (_m[:, None] == np.arange(1, 13)[None, :]).astype(float)]),
                           TEND_REZAGOS)
    _sen, _pmk = _mk_estacional(_t, serie.to_numpy(), _m)
    return {"ols": _b[0] * 10, "p": _p[0], "mk": _sen * 10, "p_mk": _pmk, "n": len(serie)}


tend_pl_sens = {
    "sin_saltos": _tend_x(pl_estrella_matriz.drop(columns=TEND_ESTACIONES_CON_SALTO).mean(axis=1, skipna=True)),
    "red_9822": _tend_x(variables_resumen["PL"]),
    "estrella_9822": _tend_x(largo["PL*"].loc[PERIODOS[0]:PERIODOS[-1]]),
    "r_9822": float(largo["PL*"].loc[PERIODOS[0]:PERIODOS[-1]].corr(variables_resumen["PL"])),
    "media_9822": float(largo["PL*"].loc[PERIODOS[0]:PERIODOS[-1]].mean()), "media_red": float(variables_resumen["PL"].mean()),
}

# lo que el texto de tendencias afirma; si los datos dejan de respaldarlo, el script se detiene
assert tend_t_sube
assert all(tend_todos[(v, per)][k]["p"] >= TEND_ALFA for v in ("PI", "Q") for per in TEND_PERIODOS for k in ("X", "a", "z"))
assert all(tend_todos[(v, per)]["X"]["p_mk"] >= TEND_ALFA for v in ("PI", "Q") for per in TEND_PERIODOS)


# ---------------------------------------------------------------- tendencias: tres métodos y diagnóstico
# Tres aproximaciones (enunciado del taller), sobre las tres representaciones:
# 1. OLS (paramétrico): X = b0 + b1·t + e (y lo mismo para a y z). Para X además el ajuste con una constante por
#    mes (efectos estacionales). Se reportan pendiente, IC 95 %, período, n y el diagnóstico de los residuos:
#    autocorrelación (lag 1 y Ljung-Box con MET_LB_REZAGOS rezagos), cambio de la dispersión con el tiempo
#    (Breusch-Pagan: e² contra t) y normalidad (Shapiro-Wilk). Si hay dependencia o heterocedasticidad, la
#    inferencia se apoya en el error de Newey-West (HAC), que corrige las dos.
# 2. Monotónica no paramétrica: Mann-Kendall con pendiente de Sen. Para X, la variante estacional (cada mes solo
#    contra el mismo mes de otros años). Dependencia: en la secuencia de meses la p se obtiene PERMUTANDO AÑOS
#    COMPLETOS (los 12 meses de un año viajan juntos), lo que conserva el ciclo y la dependencia dentro del año y
#    supone despreciable la de un año al siguiente; el IC de Sen sale de remuestrear años completos. Para a y z se
#    usa además la corrección de varianza de Hamed y Rao (1998) por autocorrelación. Mes a mes (subseries
#    anuales), Mann-Kendall por mes con el IC de Sen de Kendall, y se reporta la autocorrelación de lag 1.
# 3. No lineal: LOESS (Cleveland, 1979), regresión local lineal con pesos tricúbicos e iteraciones robustas. Es
#    una CURVA EXPLORATORIA: su banda de 95 % sale de un remuestreo de residuos por bloques de MET_BLOQUE meses,
#    no de un modelo con inferencia formal. El ciclo anual: en a y z ya no está; en X la ventana (MET_FRAC del
#    registro, varios años) lo promedia. Se prueba la sensibilidad a la ventana, a los extremos (sin iteraciones
#    robustas), a los bordes y a la longitud del registro, y se compara con una regresión segmentada (un quiebre
#    de pendiente) para ver si hay evidencia de un cambio de pendiente (BIC).
MET_LB_REZAGOS = 12
MET_BLOQUE = 12
MET_FRAC = 0.5               # ventana de LOESS: la mitad del registro (decisión del agente, ver sensibilidad)
MET_FRACS = (0.3, 0.5, 0.75)
MET_FRAC_MES = 0.75          # en las subseries anuales (25 a 42 puntos) se usa una ventana más ancha
MET_ITER_ROBUSTAS = 2
MET_REMUESTREOS = 400
MET_SEMILLA = 23
MET_UMBRAL_FORMA = 0.10      # un tramo de subida o bajada cuenta si mueve la curva más de 0.10 s_j (o 0.10 de z)
MET_DELTA_BIC = 10           # diferencia de BIC que se considera evidencia fuerte a favor del modelo con quiebre
MET_MIN_ANIOS_TRAMO = 5      # el quiebre se busca dejando al menos 5 años a cada lado
_rng_met = np.random.default_rng(MET_SEMILLA)


def _ljung_box(e, rezagos):
    n = len(e)
    e = e - e.mean()
    r = np.array([np.sum(e[k:] * e[:-k]) for k in range(1, rezagos + 1)]) / np.sum(e ** 2)
    q = n * (n + 2) * np.sum(r ** 2 / (n - np.arange(1, rezagos + 1)))
    return float(r[0]), float(stats.chi2.sf(q, rezagos))


def _breusch_pagan(e, t):
    """e² contra t: n·R² ~ chi² con 1 grado de libertad. p pequeña = la dispersión cambia con el tiempo."""
    r = np.corrcoef(e ** 2, t)[0, 1]
    return float(stats.chi2.sf(len(e) * r ** 2, 1))


def _ols_completo(y, X):
    """Pendiente (columna 0 del tiempo, que se pasa en la posición indicada), IC clásico y HAC, y diagnóstico."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    n, k = X.shape
    se_cl = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * np.sum(e ** 2) / (n - k))
    _, se_hac, p_hac = _ols_hac(y, X, TEND_REZAGOS)
    return beta, se_cl, se_hac, p_hac, e


_loess_pesos = {}          # los pesos tricúbicos solo dependen de las fechas y la ventana: se calculan una vez


def _loess(t, y, frac, iteraciones=MET_ITER_ROBUSTAS):
    """LOESS local lineal (Cleveland, 1979), vectorizado. t ordenado, sin vacíos."""
    n = len(t)
    clave = (t.tobytes(), frac)
    if clave not in _loess_pesos:
        k = max(int(np.ceil(frac * n)), 3)
        d = np.abs(t[:, None] - t[None, :])
        h = np.sort(d, axis=1)[:, k - 1][:, None]
        _loess_pesos[clave] = np.clip(1 - (d / np.where(h > 0, h, 1)) ** 3, 0, None) ** 3
    w0 = _loess_pesos[clave]
    robusto = np.ones(n)
    for _ in range(iteraciones + 1):
        w = w0 * robusto[None, :]
        s0, s1, s2 = w.sum(1), w @ t, w @ t ** 2
        sy, sty = w @ y, w @ (t * y)
        den = s0 * s2 - s1 ** 2
        b1 = (s0 * sty - s1 * sy) / den
        b0 = (sy - b1 * s1) / s0
        ajuste = b0 + b1 * t
        res = y - ajuste
        mad = np.median(np.abs(res))
        robusto = np.clip(1 - (res / (6 * mad)) ** 2, 0, None) ** 2 if mad > 0 else np.ones(n)
    return ajuste


def _banda_loess(t, y, frac):
    """Banda 95 % de la curva LOESS por remuestreo de residuos en bloques móviles de MET_BLOQUE meses."""
    ajuste = _loess(t, y, frac)
    res = y - ajuste
    n = len(y)
    inicios = np.arange(n - MET_BLOQUE + 1)
    curvas = np.empty((MET_REMUESTREOS, n))
    for b in range(MET_REMUESTREOS):
        idx = np.concatenate([np.arange(i, i + MET_BLOQUE)
                              for i in _rng_met.choice(inicios, int(np.ceil(n / MET_BLOQUE)))])[:n]
        curvas[b] = _loess(t, ajuste + res[idx], frac)
    return ajuste, np.percentile(curvas, 2.5, axis=0), np.percentile(curvas, 97.5, axis=0)


def _mk_hamed_rao(t, y):
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


def _anios_bloques(periodos):
    anios = np.asarray(periodos.year)
    return anios, np.unique(anios)


def _mk_estacional_perm(t, y, meses, anios):
    """p del Mann-Kendall estacional permutando años completos, e IC de Sen remuestreando años completos."""
    pend, _ = _mk_estacional(t, y, meses)
    S_obs = sum(np.sign(y[meses == m][None, :] - y[meses == m][:, None])[np.triu_indices((meses == m).sum(), 1)].sum()
                for m in np.unique(meses))
    unicos = np.unique(anios)
    S_perm = np.empty(MET_REMUESTREOS)
    pend_bs = np.empty(MET_REMUESTREOS)
    pos = {a: np.where(anios == a)[0] for a in unicos}
    for b in range(MET_REMUESTREOS):
        # permutación: cada año recibe el tiempo de otro año (el mes se conserva)
        orden = dict(zip(unicos, _rng_met.permutation(unicos)))
        t_perm = np.array([orden[a] for a in anios]) + (t - anios)
        S = 0.0
        for m in np.unique(meses):
            sel = meses == m
            o = np.argsort(t_perm[sel])
            ym = y[sel][o]
            S += np.sign(ym[None, :] - ym[:, None])[np.triu_indices(len(ym), 1)].sum()
        S_perm[b] = S
        # remuestreo de años con reemplazo para el IC de la pendiente
        elegidos = _rng_met.choice(unicos, len(unicos))
        idx = np.concatenate([pos[a] for a in elegidos])
        pend_bs[b] = _mk_estacional(t[idx], y[idx], meses[idx])[0] if len(np.unique(t[idx])) > 2 else np.nan
    p = (np.sum(np.abs(S_perm) >= abs(S_obs)) + 1) / (MET_REMUESTREOS + 1)
    return pend, float(p), float(np.nanpercentile(pend_bs, 2.5)), float(np.nanpercentile(pend_bs, 97.5))


def _segmentada(t, y):
    """Mejor quiebre de pendiente (modelo continuo con bisagra) y su ΔBIC frente a la recta (positivo = gana el quiebre)."""
    n = len(t)
    X1 = np.column_stack([np.ones(n), t])
    sse1 = np.sum((y - X1 @ np.linalg.lstsq(X1, y, rcond=None)[0]) ** 2)
    mejor = (np.inf, None, None)
    for tau in np.arange(t.min() + MET_MIN_ANIOS_TRAMO, t.max() - MET_MIN_ANIOS_TRAMO, 0.25):
        X2 = np.column_stack([X1, np.clip(t - tau, 0, None)])
        b = np.linalg.lstsq(X2, y, rcond=None)[0]
        sse = np.sum((y - X2 @ b) ** 2)
        if sse < mejor[0]:
            mejor = (sse, tau, b)
    bic1 = n * np.log(sse1 / n) + 2 * np.log(n)
    bic2 = n * np.log(mejor[0] / n) + 4 * np.log(n)        # pendiente extra y quiebre
    return float(mejor[1]), float(bic1 - bic2), float(mejor[2][1] * 10), float((mejor[2][1] + mejor[2][2]) * 10)


def _forma(t, curva, escala):
    """Tramos de subida y bajada de una curva: se ignoran las ondulaciones menores que MET_UMBRAL_FORMA·escala."""
    umbral = MET_UMBRAL_FORMA * escala
    tramos = []                      # (sentido, desde, hasta)
    ancla_i, sentido = 0, 0
    extremo_i = 0
    for i in range(1, len(curva)):
        if sentido >= 0 and curva[i] > curva[extremo_i]:
            extremo_i = i
        if sentido <= 0 and curva[i] < curva[extremo_i]:
            extremo_i = i
        cambio = curva[extremo_i] - curva[ancla_i]
        if sentido == 0 and abs(cambio) > umbral:
            sentido = 1 if cambio > 0 else -1
        elif sentido != 0 and (curva[i] - curva[extremo_i]) * -sentido > umbral:
            tramos.append((sentido, t[ancla_i], t[extremo_i]))
            ancla_i, sentido = extremo_i, -sentido
            extremo_i = i
    if sentido != 0:
        tramos.append((sentido, t[ancla_i], t[extremo_i]))
    return tramos


met_global, met_curvas, met_mes, met_sens = {}, {}, {}, {}
for _v in LARGO_VARS:
    for _per, _lim in TEND_PERIODOS.items():
        if _v == "PI" and _per != "completo":
            continue
        _rep = {"X": largo[_v], "a": anz_a[_v], "z": anz_z[_v]}
        if _lim is not None:
            _rep = {k: s.loc[_lim[0]:_lim[1]] for k, s in _rep.items()}
        _rep = {k: s.dropna() for k, s in _rep.items()}
        _idx = _rep["X"].index
        _t = _t_decimal(_idx)
        _meses = np.asarray(_idx.month)
        _anios, _ = _anios_bloques(_idx)
        _uno = np.column_stack([np.ones_like(_t), _t])
        _ind = (_meses[:, None] == np.arange(1, 13)[None, :]).astype(float)
        fila = {"n": len(_t), "inicio": _idx[0], "fin": _idx[-1], "anios": len(np.unique(_anios))}
        for _k in ("X", "a", "z"):
            _y = _rep[_k].to_numpy()
            b, se_cl, se_hac, p_hac, e = _ols_completo(_y, _uno)
            r1, p_lb = _ljung_box(e, MET_LB_REZAGOS)
            fila[f"ols_{_k}"] = {"pend": b[1] * 10, "ic_cl": 1.96 * se_cl[1] * 10, "ic_hac": 1.96 * se_hac[1] * 10,
                                 "p_cl": float(2 * stats.t.sf(abs(b[1] / se_cl[1]), len(_y) - 2)), "p_hac": p_hac[1],
                                 "r1": r1, "p_lb": p_lb, "p_bp": _breusch_pagan(e, _t),
                                 "p_sw": float(stats.shapiro(e)[1])}
        # X con efectos estacionales (una constante por mes)
        b, se_cl, se_hac, p_hac, e = _ols_completo(_rep["X"].to_numpy(), np.column_stack([_t, _ind]))
        r1, p_lb = _ljung_box(e, MET_LB_REZAGOS)
        fila["ols_Xmes"] = {"pend": b[0] * 10, "ic_cl": 1.96 * se_cl[0] * 10, "ic_hac": 1.96 * se_hac[0] * 10,
                            "p_cl": float(2 * stats.t.sf(abs(b[0] / se_cl[0]), len(_t) - 13)), "p_hac": p_hac[0],
                            "r1": r1, "p_lb": p_lb, "p_bp": _breusch_pagan(e, _t), "p_sw": float(stats.shapiro(e)[1])}
        # Mann-Kendall: estacional en X (p por permutación de años), con Hamed-Rao en a y z
        pend, p, lo, hi = _mk_estacional_perm(_t, _rep["X"].to_numpy(), _meses, _anios)
        fila["mk_X"] = {"pend": pend * 10, "p": p, "lo": lo * 10, "hi": hi * 10}
        for _k in ("a", "z"):
            _y = _rep[_k].to_numpy()
            ts = stats.theilslopes(_y, _t)
            p_hr, factor = _mk_hamed_rao(_t, _y)
            fila[f"mk_{_k}"] = {"pend": ts[0] * 10, "lo": ts[2] * 10, "hi": ts[3] * 10, "p": p_hr, "factor": factor,
                                "p_sin": float(stats.kendalltau(_t, _y).pvalue)}
        # LOESS en las tres representaciones; banda solo en el registro completo (es la que se dibuja)
        for _k in ("X", "a", "z"):
            _y = _rep[_k].to_numpy()
            if _per == "completo":
                curva, lo_b, hi_b = _banda_loess(_t, _y, MET_FRAC)
                met_curvas[(_v, _k)] = {"t": _idx, "curva": curva, "lo": lo_b, "hi": hi_b,
                                        "ols": fila[f"ols_{_k}"]}
            else:
                curva = _loess(_t, _y, MET_FRAC)
            escala = 1.0 if _k == "z" else float(anz_s[_v].mean())
            if _k == "X":
                escala = float(anz_s[_v].mean())
            fila[f"loess_{_k}"] = {"cambio": float(curva[-1] - curva[0]), "forma": _forma(_t, curva, escala),
                                   "escala": escala}
        # regresión segmentada sobre a: ¿hay evidencia de un cambio de pendiente?
        tau, dbic, p1, p2 = _segmentada(_t, _rep["a"].to_numpy())
        fila["seg"] = {"tau": tau, "dbic": dbic, "pend_antes": p1, "pend_despues": p2}
        met_global[(_v, _per)] = fila
    # sensibilidad de LOESS (sobre a, registro completo): ventana, extremos, bordes
    _a = anz_a[_v].dropna()
    _t = _t_decimal(_a.index)
    _y = _a.to_numpy()
    _s = {}
    for _f in MET_FRACS:
        c = _loess(_t, _y, _f)
        _s[f"frac {_f}"] = {"cambio": float(c[-1] - c[0]), "tramos": len(_forma(_t, c, float(anz_s[_v].mean())))}
    c_nr = _loess(_t, _y, MET_FRAC, iteraciones=0)
    c_r = met_curvas[(_v, "a")]["curva"]
    _s["extremos"] = float(np.max(np.abs(c_nr - c_r)))
    _anchos = met_curvas[(_v, "a")]["hi"] - met_curvas[(_v, "a")]["lo"]
    _borde = max(int(len(_anchos) * 0.1), 1)
    _s["borde_vs_centro"] = float(np.mean(np.r_[_anchos[:_borde], _anchos[-_borde:]]) / np.mean(_anchos[_borde:-_borde]))
    met_sens[_v] = _s
    # mes a mes: OLS con IC, Mann-Kendall con IC de Sen, autocorrelación de lag 1, LOESS y su forma
    for _m in range(1, 13):
        _xm = largo[_v][largo.index.month == _m].dropna()
        _tm = _t_decimal(_xm.index)
        _ym = _xm.to_numpy()
        r = stats.linregress(_tm, _ym)
        ts = stats.theilslopes(_ym, _tm)
        e = _ym - (r.intercept + r.slope * _tm)
        r1 = float(np.corrcoef(e[1:], e[:-1])[0, 1])
        curva = _loess(_tm, _ym, MET_FRAC_MES)
        met_mes[(_v, _m)] = {"n": len(_ym), "desde": int(_xm.index[0].year), "hasta": int(_xm.index[-1].year),
                             "ols": r.slope * 10, "ic": 1.96 * r.stderr * 10 * stats.t.ppf(0.975, len(_ym) - 2) / 1.96,
                             "p": r.pvalue, "sen": ts[0] * 10, "sen_lo": ts[2] * 10, "sen_hi": ts[3] * 10,
                             "p_mk": float(stats.kendalltau(_tm, _ym).pvalue), "r1": r1,
                             "r1_signif": abs(r1) > 1.96 / np.sqrt(len(_ym)),
                             "forma": _forma(_tm, curva, float(anz_s.loc[_m, _v])),
                             "curva": curva, "t": _tm, "y": _ym}

# resúmenes para el texto
met_dependencia = [f"{v}" for (v, per), f in met_global.items() if per == "completo" and f["ols_a"]["p_lb"] < TEND_ALFA]
met_hetero = [f"{v}" for (v, per), f in met_global.items() if per == "completo" and f["ols_a"]["p_bp"] < TEND_ALFA]
met_hac_mas_ancho = np.median([f["ols_a"]["ic_hac"] / f["ols_a"]["ic_cl"] for f in met_global.values()])
met_quiebres = {v: f["seg"] for (v, per), f in met_global.items() if per == "completo" and f["seg"]["dbic"] > MET_DELTA_BIC}
met_mes_r1 = sum(m["r1_signif"] for m in met_mes.values())
met_mes_reversos = {k: m["forma"] for k, m in met_mes.items() if len(m["forma"]) > 1}
# lo que el texto afirma
assert all(f["ols_Xmes"]["pend"] * f["ols_a"]["pend"] > 0 or abs(f["ols_a"]["pend"]) < 1e-9 for f in met_global.values())

# lo que el texto de los tres métodos afirma; si los datos dejan de respaldarlo, el script se detiene
_mc = {v: f for (v, per), f in met_global.items() if per == "completo"}
assert all(f["ols_a"]["p_lb"] < TEND_ALFA for f in _mc.values())
assert sum(f["ols_a"]["p_sw"] < TEND_ALFA for f in _mc.values()) >= 2
assert not met_quiebres
for _v in ("T mín", "T media", "T máx"):
    _f = _mc[_v]
    assert _f["ols_a"]["p_hac"] < TEND_ALFA and _f["mk_a"]["p"] < TEND_ALFA and _f["mk_X"]["p"] < TEND_ALFA
    assert len(_f["loess_a"]["forma"]) == 1 and _f["loess_a"]["forma"][0][0] > 0
    assert all(met_sens[_v][f"frac {fr}"]["cambio"] > 0 for fr in MET_FRACS)
assert any((met_global[(v, "1998–2022")]["ols_a"]["p_hac"] < TEND_ALFA) != (met_global[(v, "1998–2022")]["mk_a"]["p"] < TEND_ALFA)
           for v in ("T mín", "T media", "T máx"))
assert all(len({met_sens[v][f"frac {fr}"]["tramos"] for fr in MET_FRACS}) > 1 for v in ("PL*", "PI", "Q"))
assert any(len({np.sign(met_sens[v][f"frac {fr}"]["cambio"]) for fr in MET_FRACS}) > 1 for v in ("PL*", "PI", "Q"))
assert all(f[k]["p_hac"] >= TEND_ALFA for (v, per), f in met_global.items() if v in ("PI", "Q") for k in ("ols_X", "ols_Xmes", "ols_a", "ols_z"))
assert all(f[k]["p"] >= TEND_ALFA for (v, per), f in met_global.items() if v in ("PI", "Q") for k in ("mk_X", "mk_a"))
assert all(s["borde_vs_centro"] > 1 for s in met_sens.values())
assert len(_mc["Q"]["loess_a"]["forma"]) > 1

# lo que el texto afirma sobre PL* (la red fija); si los datos dejan de respaldarlo, el script se detiene
for _per in TEND_PERIODOS:
    _f = met_global[("PL*", _per)]
    assert _f["ols_Xmes"]["p_hac"] >= TEND_ALFA and _f["mk_X"]["p"] >= TEND_ALFA and _f["mk_a"]["p"] >= TEND_ALFA
assert tend_pl_sens["sin_saltos"]["p"] >= TEND_ALFA and tend_pl_sens["sin_saltos"]["p_mk"] >= TEND_ALFA
assert tend_pl_sens["red_9822"]["ols"] < tend_pl_sens["estrella_9822"]["ols"] and tend_pl_sens["red_9822"]["p_mk"] < TEND_ALFA
assert tend_pl_sens["r_9822"] > 0.95

# años contrastantes: PL contra PI, año por año (pedido por el usuario el 2026-10-08). Cuánto supera PL a PI en el
# año, contra lo habitual en 1998-2022, y los meses en que más se separan.
ANOM_MESES_DIF = 3
anom_pl_pi = {}
_habitual = float(variables_resumen.PL.sum() / variables_resumen.PI.sum())
for _a in anom_anios:
    _x = variables_resumen[variables_resumen.index.year == _a]
    _dif = (_x.PL - _x.PI).sort_values(ascending=False)
    anom_pl_pi[_a] = {"pi": [round(float(v), 1) for v in _x.PI], "pl_total": float(_x.PL.sum()), "pi_total": float(_x.PI.sum()),
                      "razon": float(_x.PL.sum() / _x.PI.sum()),
                      "meses_dif": [MESES_LARGOS_ES[p.month - 1] for p in _dif.index[:ANOM_MESES_DIF]]}
anom_pl_pi_habitual = _habitual
anom_pl_pi_raro = max(anom_pl_pi, key=lambda a: anom_pl_pi[a]["razon"])
assert anom_pl_pi[anom_pl_pi_raro]["razon"] > anom_pl_pi_habitual


# ---------------------------------------------------------------- ¿tendencia gradual o salto? (Pettitt)
# Pettitt (1979) busca el punto donde la serie cambia de nivel. Se aplica a la media anual de la anomalía a de cada
# variable (años con al menos SALTO_MIN_MESES meses), sobre su registro completo, y además a la serie mensual con la p
# obtenida permutando años completos (los meses vecinos se parecen y eso infla la significancia de la p usual).
# Trampa: una serie que sube de forma pareja también tiene un «antes bajo» y un «después alto», así que Pettitt puede
# encontrar un salto donde solo hay tendencia. Para distinguirlos: (1) Pettitt sobre los residuos de la recta (si
# después de quitar la tendencia no queda salto, no hay un salto ADEMÁS de ella) y (2) BIC de tres modelos: recta,
# escalón en el año de Pettitt, y recta más escalón. Diferencias de BIC menores que SALTO_DBIC_EMPATE se leen como
# «no se pueden distinguir» (umbral decidido por el usuario el 2026-10-08).
SALTO_MIN_MESES = 10
SALTO_PERMUTACIONES = 400
SALTO_DBIC_EMPATE = 2.0
_rng_salto = np.random.default_rng(31)


def _pettitt_K(x):
    return np.abs(np.cumsum(np.sign(x[:, None] - x[None, :]).sum(axis=1))[:-1]).max()


def _bic(y, X):
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    n = len(y)
    return n * np.log(np.sum((y - X @ b) ** 2) / n) + X.shape[1] * np.log(n)


salto = {}
for _v in LARGO_VARS:
    _s = anz_a[_v]
    _cuantos = _s.notna().groupby(_s.index.year).sum()
    _an = _s.groupby(_s.index.year).mean()[_cuantos >= SALTO_MIN_MESES]
    _y, _t = _an.to_numpy(), _an.index.to_numpy().astype(float)
    _n = len(_y)
    _k, _p = _pettitt(_y)
    # mensual, con p por permutación de años completos
    _sm = _s.dropna()
    _km, _ = _pettitt(_sm.to_numpy())
    _anios = np.asarray(_sm.index.year)
    _pos = {a: np.where(_anios == a)[0] for a in np.unique(_anios)}
    _K = _pettitt_K(_sm.to_numpy())
    _Ks = np.array([_pettitt_K(_sm.to_numpy()[np.concatenate([_pos[a] for a in _rng_salto.permutation(list(_pos))])])
                    for _ in range(SALTO_PERMUTACIONES)])
    _X1 = np.column_stack([np.ones(_n), _t])
    _res = _y - _X1 @ np.linalg.lstsq(_X1, _y, rcond=None)[0]
    _escalon = (_t > _t[_k]).astype(float)
    _bics = {"recta": _bic(_y, _X1), "escalón": _bic(_y, np.column_stack([np.ones(_n), _escalon])),
             "recta y escalón": _bic(_y, np.column_stack([_X1, _escalon]))}
    _mejor = min(_bics, key=_bics.get)
    _segundo = sorted(_bics.values())[1]
    salto[_v] = {"anios": _n, "anio_corte": int(_t[_k]), "p": _p, "antes": float(_y[: _k + 1].mean()),
                 "despues": float(_y[_k + 1:].mean()), "corte_mensual": _sm.index[_km],
                 "p_perm": float((np.sum(_Ks >= _K) + 1) / (SALTO_PERMUTACIONES + 1)),
                 "p_residuos": _pettitt(_res)[1], "bic": _bics, "mejor": _mejor,
                 "empate": (_segundo - _bics[_mejor]) < SALTO_DBIC_EMPATE}
salto_con_corte = [v for v, r in salto.items() if r["p"] < TEND_ALFA and r["p_perm"] < TEND_ALFA]
# lo que el texto afirma; si los datos dejan de respaldarlo, el script se detiene
assert set(salto_con_corte) == {"T mín", "T media", "T máx"}
assert all(r["p_residuos"] >= TEND_ALFA for r in salto.values())
assert all(salto[v]["empate"] for v in salto_con_corte)
assert all(r["p"] >= TEND_ALFA and r["p_perm"] >= TEND_ALFA for v, r in salto.items() if v not in salto_con_corte)
assert all(not (1993 <= salto[v]["anio_corte"] <= 1996) for v in ("T mín", "T media", "T máx"))


# ---------------------------------------------------------------- tendencias: incertidumbre y relevancia
# (1) Comparaciones múltiples. La familia de pruebas es la de las 12 subseries mensuales de cada variable, en su
# registro completo (decidido con el usuario): con 12 pruebas por variable, algún mes saldría significativo solo
# por azar. Se controla la tasa de falsos descubrimientos (FDR) con Benjamini y Hochberg (1995), con
# INC_Q_FDR = 0.05, por separado para la OLS y para Mann-Kendall.
INC_Q_FDR = 0.05


def _benjamini_hochberg(p):
    """q-valores de Benjamini-Hochberg: un mes es significativo si su q es menor que INC_Q_FDR."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    orden = np.argsort(p)
    ajustado = p[orden] * n / np.arange(1, n + 1)
    ajustado = np.minimum.accumulate(ajustado[::-1])[::-1]
    q = np.empty(n)
    q[orden] = np.minimum(ajustado, 1)
    return q


inc_fdr = {}
for _v in LARGO_VARS:
    _q = _benjamini_hochberg([met_mes[(_v, m)]["p"] for m in range(1, 13)])
    _q_mk = _benjamini_hochberg([met_mes[(_v, m)]["p_mk"] for m in range(1, 13)])
    for _m in range(1, 13):
        met_mes[(_v, _m)]["q"], met_mes[(_v, _m)]["q_mk"] = float(_q[_m - 1]), float(_q_mk[_m - 1])
    inc_fdr[_v] = {"sin": [m for m in range(1, 13) if met_mes[(_v, m)]["p"] < TEND_ALFA],
                   "ols": [m for m in range(1, 13) if met_mes[(_v, m)]["q"] < INC_Q_FDR],
                   "mk": [m for m in range(1, 13) if met_mes[(_v, m)]["q_mk"] < INC_Q_FDR]}
inc_fdr_sobreviven = [v for v in LARGO_VARS if inc_fdr[v]["ols"]]


# (2) Banda de 95 % de la recta OLS (error de Newey-West) para la gráfica de series: var(ŷ) = x'Vx en cada punto.
def _ols_hac_cov(y, X, rezagos):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    s = u.T @ u
    for l in range(1, rezagos + 1):
        g = u[l:].T @ u[:-l]
        s += (1 - l / (rezagos + 1)) * (g + g.T)
    return beta, xtx_inv @ s @ xtx_inv


for (_v, _k), _c in met_curvas.items():
    _y = {"X": largo[_v], "a": anz_a[_v], "z": anz_z[_v]}[_k].dropna()
    _X = np.column_stack([np.ones(len(_y)), _t_decimal(_y.index)])
    _b, _V = _ols_hac_cov(_y.to_numpy(), _X, TEND_REZAGOS)
    _ajuste = _X @ _b
    _ancho = 1.96 * np.sqrt(np.einsum("ij,jk,ik->i", _X, _V, _X))
    _c.update(ols_recta=_ajuste, ols_lo=_ajuste - _ancho, ols_hi=_ajuste + _ancho)


# (3) Significancia contra relevancia.
# a) «No significativo» no es «sin cambio»: el intervalo de 95 % dice cuánto cambio no se puede descartar. Se da en
#    las unidades de la variable por década y como porcentaje de su media.
inc_no_descartable = {}
for _v in ("PL*", "PI", "Q"):
    _f = met_global[(_v, "completo")]["ols_Xmes"]
    _media = float(largo[_v].mean())
    inc_no_descartable[_v] = {"lo": _f["pend"] - _f["ic_hac"], "hi": _f["pend"] + _f["ic_hac"], "media": _media,
                              "lo_pct": (_f["pend"] - _f["ic_hac"]) / _media * 100,
                              "hi_pct": (_f["pend"] + _f["ic_hac"]) / _media * 100}
# b) «Significativo» no es «importante»: cuánto cambia la ETP de Hargreaves con el calentamiento observado. La fórmula
#    es la de scripts/06b: ETP = 0.0023 · Ra · (T + 17.8) · √(Tmáx − Tmín), con T = (Tmáx + Tmín) / 2. Con Ra fija, su
#    cambio relativo es ΔT / (T + 17.8) + Δ(Tmáx − Tmín) / (2 · (Tmáx − Tmín)) (primer orden), con las pendientes por
#    década del registro completo. Se compara con la ETP anual media y con lo que la lluvia (PL*) no permite descartar.
_etp = pd.read_csv("out/etp_hargreaves_fonce.csv", parse_dates=["fecha"]).set_index("fecha")["etp_era5land"]
inc_etp_anual = float(_etp.groupby(_etp.index.year).sum().mean())
_tm = float(((_era_largo["t_max"] + _era_largo["t_min"]) / 2).mean())
_td = float((_era_largo["t_max"] - _era_largo["t_min"]).mean())
_d_tm = (met_global[("T máx", "completo")]["ols_Xmes"]["pend"] + met_global[("T mín", "completo")]["ols_Xmes"]["pend"]) / 2
_d_td = met_global[("T máx", "completo")]["ols_Xmes"]["pend"] - met_global[("T mín", "completo")]["ols_Xmes"]["pend"]
inc_etp_rel = _d_tm / (_tm + 17.8) + _d_td / (2 * _td)
inc_etp_decada = inc_etp_anual * inc_etp_rel                  # mm/año por década
inc_etp_registro = inc_etp_decada * (largo_registro["T media"]["meses"] / 120)
inc_pl_anual_ic = met_global[("PL*", "completo")]["ols_Xmes"]["ic_hac"] * 12      # mm/año por década
inc_etp = {"anual": inc_etp_anual, "rel_pct": inc_etp_rel * 100, "decada": inc_etp_decada,
           "registro": inc_etp_registro, "d_tm": _d_tm, "d_td": _d_td, "pl_ic_anual": inc_pl_anual_ic}
# lo que el texto afirma
assert inc_etp["decada"] > 0 and inc_etp["decada"] < inc_etp["pl_ic_anual"]
assert all(r["lo"] < 0 < r["hi"] for r in inc_no_descartable.values())
# Los meses de la lluvia que sobreviven al FDR: qué tan robustos son. Para cada uno, cuántas estaciones de la red fija
# suben ese mes, la p más alta al quitar un año a la vez (¿lo explica un solo año?), el promedio por década, y qué
# hacen PI y Q en el mismo mes.
inc_lluvia_fdr = {}
for _m in inc_fdr["PL*"]["ols"]:
    _x = largo["PL*"][largo.index.month == _m].dropna()
    _t, _y = _x.index.year.to_numpy().astype(float), _x.to_numpy()
    _jk = max(stats.linregress(np.delete(_t, i), np.delete(_y, i)).pvalue for i in range(len(_y)))
    _est = pl_estrella_matriz[pl_estrella_matriz.index.month == _m]
    _suben = sum(stats.linregress(_est[c].dropna().index.year.astype(float), _est[c].dropna().to_numpy()).slope > 0
                 for c in _est.columns)
    _dec = {d: float(_y[(_t >= d) & (_t < d + 10)].mean()) for d in range(1981, 2021, 10) if ((_t >= d) & (_t < d + 10)).any()}
    inc_lluvia_fdr[_m] = {"pend": met_mes[("PL*", _m)]["ols"], "q": met_mes[("PL*", _m)]["q"], "p_jk": _jk,
                          "suben": int(_suben), "estaciones": len(_est.columns), "decadas": _dec,
                          "pi": met_mes[("PI", _m)], "q_mes": met_mes[("Q", _m)]}
assert set(inc_fdr["PL*"]["ols"]) == {3} and not inc_fdr["PI"]["ols"] and not inc_fdr["Q"]["ols"]
assert all(r["p_jk"] < TEND_ALFA and r["suben"] == r["estaciones"] and r["pi"]["ols"] > 0 and r["q_mes"]["p"] >= TEND_ALFA
           for r in inc_lluvia_fdr.values())


# ---------------------------------------------------------------- frecuencias: análisis de Fourier
# Integra el trabajo de angomezma-cyber (rama punto-4, 2026-10-08), pasado a la estructura de los scripts y a las
# decisiones vigentes (PL* y ERA5-Land en el registro extendido, referencia 1998-2022 para las anomalías).
#
# Qué se calcula. El espectro de potencia de cada serie mensual dice cómo se reparte su varianza entre las escalas de
# tiempo: el ciclo anual (12 meses), el semianual (6 meses, el régimen bimodal), la variabilidad interanual (de 3 a 7
# años, la escala del ENSO) y la alta frecuencia (menos de 6 meses). Se usa el periodograma de Lomb-Scargle (Lomb,
# 1976; Scargle, 1982), que trabaja con las fechas observadas y admite meses vacíos (Q los tiene); como contraste,
# el periodograma de la FFT con ventana de Hann sobre el tramo continuo más largo.
#
# Tres transformaciones de cada serie: la original centrada (menos su media), la anomalía (menos la media de su mes
# del calendario en 1998-2022, la misma referencia de «Anomalías y anomalías estandarizadas») y la anomalía sin
# tendencia (la anomalía menos su recta). Dos ventanas: la común 1998-2022 (PL, PI, Q y T, para comparar fuentes) y
# la extendida 1981-2022 (PL*, Q y T, regla 6).
#
# Normalización: cada espectro se divide por su área, así que integra 1 (el 100 % de la varianza) y se pueden comparar
# formas entre variables con unidades distintas; la altura no es variabilidad absoluta.
#
# Significancia: un pico no es una periodicidad por ser el más alto. Se contrasta el pico más alto de la anomalía sin
# tendencia con el de FOU_SIMULACIONES series de ruido rojo AR(1) con la misma autocorrelación, varianza y fechas
# observadas; comparar el MÁXIMO del espectro corrige que se buscó en todas las frecuencias a la vez.
#
# Correcciones al código original (documentadas en el PR): la «anomalía sin tendencia» se calcula sobre la anomalía
# (en el original se quitaba la recta a la serie con su ciclo anual); la banda interanual es una sola, 3-7 años (había
# 3-6 y 3-7); np.trapz, obsoleta, se reemplaza por np.trapezoid; la temperatura extendida es ERA5-Land, no MSWX.
FOU_SOBREMUESTREO = 4                 # puntos de frecuencia por cada frecuencia de Fourier: solo afina el dibujo
FOU_BANDAS = {"anual": 12.0, "semianual": 6.0}
FOU_INTERANUAL = (36.0, 84.0)         # meses: 3 a 7 años
FOU_ALTA_MAX = 6.0                    # meses: alta frecuencia = períodos menores que 6 meses
FOU_SIMULACIONES = 300
FOU_WELCH_SEGMENTO = 120              # meses por segmento de Welch (10 años)
# Meses extremos para la prueba de sensibilidad: los mismos atípicos de «Revisión de outliers» (atip_marca, FACTOR_ATIPICO
# rangos intercuartiles por fuera de los cuartiles de su mes del calendario). Decidido por el usuario el 2026-10-08, por
# consistencia con el resto del informe; el agente había recomendado quitar el 2 % más extremo de cada variable y el PR
# original usaba 3 RIC desde la mediana de todas las anomalías, un criterio que no aparece en otra parte (y que en PL y
# PI no quitaba ningún mes).
FOU_ATIPICOS_COLUMNA = {"T": "T media"}          # en Fourier la temperatura se llama T; en atip_marca, «T media»
_rng_fou = np.random.default_rng(41)

FOU_VENTANAS = {
    "común 1998–2022": {"PL": variables_resumen["PL"], "PI": variables_resumen["PI"], "Q": variables_resumen["Q"],
                        "T": variables_resumen["T media"]},
    "extendida 1981–2022": {"PL*": largo["PL*"], "Q": largo["Q"], "T": largo["T media"]},
}
FOU_TRANSFORMACIONES = ("original", "anomalía", "anomalía sin tendencia")


def _fou_transformar(serie, tipo):
    """Serie mensual (PeriodIndex) -> la transformación pedida, con los meses vacíos conservados."""
    if tipo == "original":
        return serie - serie.mean()
    ref = serie.loc[PERIODOS[0]:PERIODOS[-1]]
    anom = serie - ref.groupby(ref.index.month).mean().reindex(serie.index.month).to_numpy()
    if tipo == "anomalía":
        return anom
    ok = anom.notna().to_numpy()
    t = np.arange(len(anom), dtype=float)
    recta = np.polyval(np.polyfit(t[ok], anom.to_numpy()[ok], 1), t)
    return anom - recta


def _fou_lomb(serie, sobremuestreo=FOU_SOBREMUESTREO):
    """Periodograma de Lomb-Scargle normalizado a área 1, en ciclos/mes, desde 1/N hasta Nyquist (0.5)."""
    ok = serie.notna().to_numpy()
    t = np.flatnonzero(ok).astype(float)
    y = serie.to_numpy(dtype=float)[ok]
    y = y - y.mean()
    n_total = len(serie)
    f = np.linspace(1 / n_total, 0.5, n_total * sobremuestreo // 2)
    p = lombscargle(t, y, 2 * np.pi * f, normalize=True)
    return f, p / np.trapezoid(p, f), t, y


def _fou_fft(serie, ventana="hann"):
    """Periodograma de la FFT (o de Welch) sobre el tramo continuo más largo, normalizado a área 1. Devuelve también el
    largo del tramo y el de cada segmento (en Hann, el segmento es el tramo entero): la resolución es 1/segmento."""
    ok = np.flatnonzero(serie.notna().to_numpy())
    bloques = np.split(ok, np.flatnonzero(np.diff(ok) > 1) + 1)
    bloque = max(bloques, key=len)
    y = serie.to_numpy(dtype=float)[bloque]
    if ventana == "welch":
        segmento = min(FOU_WELCH_SEGMENTO, len(y))
        f, p = welch(y, window="hann", nperseg=segmento, detrend="constant")
    else:
        segmento = len(y)
        f, p = periodogram(y, window="hann", detrend="constant", scaling="density")
    f, p = f[1:], p[1:]
    return f, p / np.trapezoid(p, f), len(bloque), segmento


def _fou_lomb_segmentos(serie, segmento=FOU_WELCH_SEGMENTO):
    """Lomb-Scargle promediado por segmentos: el análogo de Welch para una serie con meses vacíos. Se parte la serie
    completa en tramos de `segmento` meses que se traslapan la mitad, se calcula el periodograma de Lomb-Scargle de cada
    tramo (normalizado a área 1) y se promedian. Como en Welch, promediar baja la varianza del estimador a cambio de una
    resolución más gruesa (Δf = 1/segmento); a diferencia de Welch, los tramos no llevan ventana de Hann. Devuelve también
    cuántos tramos se usaron y cuántos meses con dato tiene el más incompleto (no se exige un mínimo)."""
    inicios = range(0, len(serie) - segmento + 1, segmento // 2)
    tramos = [serie.iloc[i:i + segmento] for i in inicios]
    espectros = [_fou_lomb(tramo, sobremuestreo=1) for tramo in tramos]
    f = espectros[0][0]
    p = np.mean([e[1] for e in espectros], axis=0)
    return f, p / np.trapezoid(p, f), len(tramos), int(min(t.notna().sum() for t in tramos))


def _fou_fraccion(f, p, f_baja, f_alta):
    m = (f >= f_baja) & (f <= f_alta)
    return float(100 * np.trapezoid(p[m], f[m])) if m.sum() >= 2 else float("nan")


def _fou_ar1(t, y):
    """Autocorrelación de lag 1 con los pares de meses consecutivos observados."""
    pares = np.flatnonzero(np.diff(t) == 1)
    return float(np.corrcoef(y[pares], y[pares + 1])[0, 1])


def _fou_espectro(serie):
    n = len(serie)
    f, p, t, y = _fou_lomb(serie)
    df = 1 / n
    i = int(np.argmax(p))
    periodo = 1 / f[i]
    # Las bandas anual y semianual miden ±Δf alrededor de 1/12 y 1/6: un ciclo en un registro de N meses no da una
    # línea sino un pico cuyo lóbulo principal ocupa ±1/N. Con ±Δf/2 (la versión del PR) quedaban fuera los costados del
    # pico: la semianual de PL daba 32 % cuando el ciclo medio (57 % de la varianza) por la parte de su armónico de 6
    # meses (87 %) predice ~50 %; con ±Δf da 49 %. Decidido por el usuario el 2026-10-08, con la recomendación del
    # agente; se descartaron ±2Δf (agarra frecuencias vecinas que no son del ciclo) y dejar ±Δf/2 declarándolo.
    bandas = {nombre: _fou_fraccion(f, p, 1 / T - df, 1 / T + df) for nombre, T in FOU_BANDAS.items()}
    bandas["interanual"] = _fou_fraccion(f, p, 1 / FOU_INTERANUAL[1], 1 / FOU_INTERANUAL[0])
    bandas["alta"] = _fou_fraccion(f, p, 1 / FOU_ALTA_MAX + df, 0.5)     # empieza donde termina la semianual
    f_fft, p_fft, n_fft, _ = _fou_fft(serie)
    return {"f": f, "p": p, "n": int(serie.notna().sum()), "N": n, "df": df, "pico": periodo,
            "dT": periodo ** 2 * df, "ciclos": n / periodo, "bandas": bandas,
            "pico_fft": float(1 / f_fft[np.argmax(p_fft)]), "n_fft": n_fft, "t": t, "y": y}


fou = {}
for _ven, _series in FOU_VENTANAS.items():
    for _v, _s in _series.items():
        _s = _s.loc[_s.first_valid_index():_s.last_valid_index()]
        for _tipo in FOU_TRANSFORMACIONES:
            fou[(_ven, _v, _tipo)] = _fou_espectro(_fou_transformar(_s, _tipo))

# significancia del pico más alto de la anomalía sin tendencia contra ruido rojo AR(1)
for (_ven, _v, _tipo), _e in fou.items():
    if _tipo != "anomalía sin tendencia":
        continue
    _phi = max(_fou_ar1(_e["t"], _e["y"]), 0.0)
    _sd = np.std(_e["y"])
    _maximos = np.empty(FOU_SIMULACIONES)
    _idx = _e["t"].astype(int)
    for _b in range(FOU_SIMULACIONES):
        # AR(1) estacionario de varianza 1: x_k = φ x_(k-1) + √(1-φ²) ε_k, con x_0 ~ N(0, 1)
        _eps = _rng_fou.normal(size=_e["N"])
        _ruido = lfilter([np.sqrt(1 - _phi ** 2)], [1, -_phi], _eps, zi=[_phi * _rng_fou.normal()])[0]
        _sim = pd.Series(np.nan, index=range(_e["N"]))
        _sim.iloc[_idx] = _ruido[_idx] * _sd
        _f, _p, _, _ = _fou_lomb(_sim, sobremuestreo=1)      # basta con las frecuencias de Fourier (k/N)
        _maximos[_b] = _p.max()
    _e["ar1_phi"] = _phi
    _obs = _fou_lomb(pd.Series(_e["y"], index=_e["t"].astype(int)).reindex(range(_e["N"])), sobremuestreo=1)[1].max()
    _e["ar1_p"] = float((np.sum(_maximos >= _obs) + 1) / (FOU_SIMULACIONES + 1))
    _e["ar1_umbral"] = float(np.percentile(_maximos, 95))

# sensibilidad (ventana común, original): ventana Hann contra Welch, y anomalía con y sin los meses extremos; un pico
# es estable si cambia menos que la resolución del espectro (ΔT = T² Δf, con Δf = 1/largo del segmento: el tramo entero
# en Hann, el segmento en Welch). Si el tramo continuo es más corto que un segmento de Welch, Welch usa un solo segmento
# y da el mismo periodograma que Hann: la comparación no prueba nada y se marca como «un_segmento».
# En ese caso (hoy solo Q: su tramo continuo más largo tiene 69 meses), Welch se reemplaza por Lomb-Scargle promediado
# por segmentos de FOU_WELCH_SEGMENTO meses sobre la serie completa, con sus vacíos. Decidido por el usuario el
# 2026-10-08, con la recomendación del agente; las otras opciones eran Welch con segmentos de 36 meses dentro del tramo de
# 69 (solo 2 segmentos, Δf = 1/36) o no probarlo y declararlo.
fou_sens = {}
for _v, _s in FOU_VENTANAS["común 1998–2022"].items():
    _e = fou[("común 1998–2022", _v, "original")]
    _f_w, _p_w, _, _seg_w = _fou_fft(_s - _s.mean(), "welch")
    _un_segmento = _seg_w == _e["n_fft"]
    _tramos_ls, _min_obs_ls = None, None
    if _un_segmento:
        _f_w, _p_w, _tramos_ls, _min_obs_ls = _fou_lomb_segmentos(_s - _s.mean())
        _seg_w = FOU_WELCH_SEGMENTO
    _pico_w = float(1 / _f_w[np.argmax(_p_w)])
    _dT_w = _pico_w ** 2 / _seg_w
    _dT_hann = _e["pico_fft"] ** 2 / _e["n_fft"]
    _a = _fou_transformar(_s, "anomalía")
    _atipico = atip_marca[FOU_ATIPICOS_COLUMNA.get(_v, _v)].reindex(_a.index).fillna("") != ""
    _sin_ext = _a.where(~_atipico)
    _pico_a = fou[("común 1998–2022", _v, "anomalía")]["pico"]
    _pico_se = _fou_espectro(_sin_ext)["pico"]
    _dT_a = _pico_a ** 2 / len(_a)
    fou_sens[_v] = {"hann": _e["pico_fft"], "welch": _pico_w, "un_segmento": _un_segmento, "tramo": _e["n_fft"],
                    "tramos_lomb": _tramos_ls, "min_obs_lomb": _min_obs_ls,
                    "hann_welch_estable": abs(_e["pico_fft"] - _pico_w) <= max(_dT_w, _dT_hann),
                    "extremos": int(_a.notna().sum() - _sin_ext.notna().sum()), "pico_sin_extremos": _pico_se,
                    "extremos_estable": abs(_pico_se - _pico_a) <= _dT_a}

# lecturas para el texto (todas calculadas; los textos que dependen de ellas se protegen abajo)
_com = "común 1998–2022"
fou_estacional = {v: fou[(_com, v, "original")]["bandas"]["anual"] + fou[(_com, v, "original")]["bandas"]["semianual"]
                  for v in FOU_VENTANAS[_com]}
fou_semi_mayor = [v for v in FOU_VENTANAS[_com]
                  if fou[(_com, v, "original")]["bandas"]["semianual"] > fou[(_com, v, "original")]["bandas"]["anual"]]
fou_alta_lluvia = float(np.mean([fou[(_com, v, "anomalía")]["bandas"]["alta"] for v in ("PL", "PI")]))
fou_alta_q = fou[(_com, "Q", "anomalía")]["bandas"]["alta"]
fou_interanual = {v: fou[(_com, v, "anomalía sin tendencia")]["bandas"]["interanual"] for v in FOU_VENTANAS[_com]}
fou_significativos = [(ven, v) for (ven, v, tipo), e in fou.items()
                      if tipo == "anomalía sin tendencia" and e["ar1_p"] < TEND_ALFA]
fou_extendida = {v: (fou[(_com, "PL" if v == "PL*" else v, "original")]["pico"],
                     fou[("extendida 1981–2022", v, "original")]["pico"]) for v in ("PL*", "Q", "T")}


def _fou_se_mueve(a, b):
    """¿El pico más alto cambia entre dos espectros más que la resolución de ambos (ΔT = T² Δf)?"""
    return abs(a["pico"] - b["pico"]) > max(a["dT"], b["dT"])


# en las anomalías (con y sin tendencia), la ventana extendida sí puede mover el pico: se listan los casos en que lo mueve
fou_extendida_anom_mueve = [(v, tipo, fou[(_com, "PL" if v == "PL*" else v, tipo)]["pico"], fou[("extendida 1981–2022", v, tipo)]["pico"])
                            for tipo in ("anomalía", "anomalía sin tendencia") for v in ("PL*", "Q", "T")
                            if _fou_se_mueve(fou[(_com, "PL" if v == "PL*" else v, tipo)], fou[("extendida 1981–2022", v, tipo)])]
# sensibilidad a la tendencia: anomalía contra anomalía sin tendencia, en cada ventana. Se mira si se mueve el pico más
# alto y cuántos puntos porcentuales cambia, como mucho, la fracción de varianza de alguna banda
FOU_TENDENCIA_MAX_PUNTOS = 3.0        # el texto dice que quitar la tendencia «casi no cambia» las bandas: menos de 3 puntos
fou_tendencia = {}
for _ven, _series in FOU_VENTANAS.items():
    for _v in _series:
        _a, _st = fou[(_ven, _v, "anomalía")], fou[(_ven, _v, "anomalía sin tendencia")]
        fou_tendencia[(_ven, _v)] = {"mueve": _fou_se_mueve(_a, _st), "antes": _a["pico"], "despues": _st["pico"],
                                     "puntos": max(abs(_a["bandas"][b] - _st["bandas"][b]) for b in _a["bandas"])}
fou_tendencia_max = max(fou_tendencia.items(), key=lambda kv: kv[1]["puntos"])
# efecto de los vacíos de Q: el espectro de PL (sin vacíos) contra el de PL con vacíos en los mismos meses que le faltan a
# Q, en la ventana común. Si con ese patrón de vacíos el espectro de PL casi no cambia, tampoco debería distorsionar el de
# Q. Mismo criterio que la tendencia: el pico no se mueve más que ΔT y ninguna banda cambia FOU_TENDENCIA_MAX_PUNTOS
# puntos porcentuales o más (decidido por el usuario el 2026-10-08, con la recomendación del agente).
_pl_com, _q_com = FOU_VENTANAS[_com]["PL"], FOU_VENTANAS[_com]["Q"]
_vacio_q = _q_com.reindex(_pl_com.index).isna()
fou_vacios = {"meses": int(_vacio_q.sum())}
for _tipo in ("original", "anomalía"):
    _completo = fou[(_com, "PL", _tipo)]
    _con_vacios = _fou_espectro(_fou_transformar(_pl_com.where(~_vacio_q), _tipo))
    _dif = {b: _con_vacios["bandas"][b] - _completo["bandas"][b] for b in _completo["bandas"]}
    _banda = max(_dif, key=lambda b: abs(_dif[b]))
    fou_vacios[_tipo] = {"mueve": _fou_se_mueve(_completo, _con_vacios), "antes": _completo["pico"],
                         "despues": _con_vacios["pico"], "puntos": abs(_dif[_banda]), "banda": _banda,
                         "con": _con_vacios["bandas"][_banda], "sin": _completo["bandas"][_banda]}
fou_vacios_ok = all(not fou_vacios[k]["mueve"] and fou_vacios[k]["puntos"] < FOU_TENDENCIA_MAX_PUNTOS
                    for k in ("original", "anomalía"))
# lo que el texto de frecuencias afirma; si los datos dejan de respaldarlo, el script se detiene
_orig = {v: fou[(_com, v, "original")] for v in FOU_VENTANAS[_com]}
assert {"PL", "PI", "Q"} <= set(fou_semi_mayor) and "T" not in fou_semi_mayor
assert all(abs(_orig[v]["pico"] - 6) <= max(_orig[v]["dT"], 0.5) for v in ("PL", "PI", "Q"))
assert abs(_orig["T"]["pico"] - 12) <= max(_orig["T"]["dT"], 0.5)
assert fou_alta_q < fou_alta_lluvia
assert fou_interanual["T"] > fou_interanual["Q"] > max(fou_interanual["PL"], fou_interanual["PI"])
# si algún pico sale significativo, el texto lo nombra y advierte cuántas veces cabe en el registro
fou_signif_ciclos = {(ven, v): fou[(ven, v, "anomalía sin tendencia")]["ciclos"] for ven, v in fou_significativos}
assert all(c < 3 for c in fou_signif_ciclos.values())
assert all(abs(a - b) <= 0.5 for a, b in fou_extendida.values())   # en las originales, la ventana extendida no mueve el pico
assert fou_tendencia_max[1]["puntos"] < FOU_TENDENCIA_MAX_PUNTOS
# el texto dice que en T pesa más la banda interanual que la anual, aunque su pico más alto esté en 12 meses
assert _orig["T"]["bandas"]["interanual"] > _orig["T"]["bandas"]["anual"]
# el texto dice que el caudal tiene más memoria de un mes al siguiente que la lluvia (autocorrelación de lag 1)
fou_phi = {v: fou[(_com, v, "anomalía sin tendencia")]["ar1_phi"] for v in FOU_VENTANAS[_com]}
assert fou_phi["Q"] > max(fou_phi["PL"], fou_phi["PI"])
# el texto dice que los vacíos de Q empujan la alta frecuencia hacia arriba, así que no explican que Q tenga menos
assert fou_vacios["anomalía"]["banda"] != "alta" or fou_vacios["anomalía"]["con"] >= fou_vacios["anomalía"]["sin"]


# ---------------------------------------------------------------- frecuencias: ¿cuadra con el ENSO? (ONI, coherencia y fase)
# El ONI (17_oni_enso.py) es la anomalía de la temperatura del mar en la región Niño 3.4 del Pacífico. Entra como
# referencia, no como variable de la cuenca: su espectro, y la coherencia y la fase de la lluvia y el caudal con él.
# La coherencia mide, frecuencia por frecuencia, qué tanto varían juntas dos series (0: nada; 1: una es la otra
# desplazada y escalada); la fase dice cuál va adelante. A diferencia del espectro de potencia, el espectro cruzado sí
# conserva la fase entre las dos series.
#
# Decisiones del usuario (2026-10-08), todas con la recomendación del agente:
#  - segmentos de FOU_WELCH_SEGMENTO meses (120) con ventana de Hann y traslape de la mitad, el mismo largo de Welch de
#    la prueba de estabilidad; la banda de 3 a 7 años queda en las frecuencias 1/60 y 1/40 ciclos/mes. Se descartaron
#    96 meses (una sola frecuencia en la banda) y 180 (solo 2 segmentos en la ventana común);
#  - la coherencia necesita meses seguidos: SOLO aquí, un mes vacío de Q se toma como anomalía cero (un mes normal). Se
#    declara en el texto y se mide su efecto con PL (coherencia PL-ONI con PL completa contra PL con los vacíos de Q en
#    cero). Se descartó dejar a Q fuera;
#  - significancia por simulación: FOU_SIMULACIONES pares de series AR(1) independientes, con la autocorrelación de cada
#    serie y los mismos vacíos en cero; el umbral es el percentil 95 de su coherencia media en la banda. Se descartó la
#    fórmula analítica, que con segmentos traslapados da un umbral demasiado bajo.
# Las series son las anomalías sin tendencia (la tendencia inflaría la coherencia en las frecuencias bajas); el ONI recibe
# la misma transformación. Convención de la fase: el ángulo del espectro cruzado de (a, b), que en scipy es conj(A)·B;
# negativo quiere decir que b va detrás de a. Cerca de ±180°, las series van en oposición: una sube cuando la otra baja.
FOU_OPOSICION_GRADOS = 135.0          # |fase| desde la que se lee «en oposición»; por debajo de 45° se lee «en fase»
FOU_EN_FASE_GRADOS = 45.0
FOU_REZAGOS_ONI = range(0, 7)         # meses de rezago para la correlación simple con el ONI
_rng_coh = np.random.default_rng(43)

fou_oni_serie = {}
for _ven, _archivo in (("común 1998–2022", "out/oni_mensual.csv"), ("extendida 1981–2022", "out/oni_mensual_1981_2022.csv")):
    _d = pd.read_csv(_archivo)
    fou_oni_serie[_ven] = pd.Series(_d["oni"].to_numpy(dtype=float), index=pd.PeriodIndex(_d["periodo"], freq="M"))
# espectro del ONI (versión original: el ONI ya es una anomalía), con los mismos criterios que las demás series
fou_oni = {ven: _fou_espectro(s - s.mean()) for ven, s in fou_oni_serie.items()}

FOU_PARES = {"común 1998–2022": [("PL", "Q"), ("PI", "Q"), ("PL", "ONI"), ("PI", "ONI"), ("Q", "ONI")],
             "extendida 1981–2022": [("PL*", "Q"), ("PL*", "ONI"), ("Q", "ONI")]}


def _fou_serie_coh(ven, v):
    """Anomalía sin tendencia de la variable (o del ONI) en la ventana, con sus meses vacíos."""
    s = fou_oni_serie[ven] if v == "ONI" else FOU_VENTANAS[ven][v]
    s = s.loc[s.first_valid_index():s.last_valid_index()]
    return _fou_transformar(s, "anomalía sin tendencia")


def _fou_coherencia(a, b):
    """Coherencia media en la banda de 3 a 7 años y fase del espectro cruzado sumado en la banda (grados). a y b: arreglos
    del mismo largo, sin vacíos."""
    seg = FOU_WELCH_SEGMENTO
    f, pab = csd(a, b, window="hann", nperseg=seg, noverlap=seg // 2, detrend="constant")
    _, paa = welch(a, window="hann", nperseg=seg, noverlap=seg // 2, detrend="constant")
    _, pbb = welch(b, window="hann", nperseg=seg, noverlap=seg // 2, detrend="constant")
    banda = (f >= 1 / FOU_INTERANUAL[1]) & (f <= 1 / FOU_INTERANUAL[0])
    coh = np.abs(pab[banda]) ** 2 / (paa[banda] * pbb[banda])
    return float(coh.mean()), float(np.degrees(np.angle(pab[banda].sum()))), 1 / f[banda]


def _fou_ar1_sim(phi, n):
    """Serie AR(1) estacionaria de varianza 1 (la misma construcción de la prueba de ruido rojo)."""
    return lfilter([np.sqrt(1 - phi ** 2)], [1, -phi], _rng_coh.normal(size=n), zi=[phi * _rng_coh.normal()])[0]


fou_coh = {}
for _ven, _pares in FOU_PARES.items():
    for _a, _b in _pares:
        _sa, _sb = _fou_serie_coh(_ven, _a), _fou_serie_coh(_ven, _b)
        _idx = _sa.index.intersection(_sb.index)
        _sa, _sb = _sa.reindex(_idx), _sb.reindex(_idx)
        _va, _vb = _sa.isna().to_numpy(), _sb.isna().to_numpy()
        _coh, _fase, _periodos = _fou_coherencia(_sa.fillna(0).to_numpy(), _sb.fillna(0).to_numpy())
        # autocorrelación de cada serie con sus meses consecutivos observados, para las simulaciones
        _phis = []
        for _s in (_sa, _sb):
            _t = np.flatnonzero(_s.notna().to_numpy()).astype(float)
            _phis.append(max(_fou_ar1(_t, _s.dropna().to_numpy()), 0.0))
        _sims = np.empty(FOU_SIMULACIONES)
        for _k in range(FOU_SIMULACIONES):
            _xa, _xb = _fou_ar1_sim(_phis[0], len(_idx)), _fou_ar1_sim(_phis[1], len(_idx))
            _xa[_va], _xb[_vb] = 0.0, 0.0
            _sims[_k] = _fou_coherencia(_xa, _xb)[0]
        _umbral = float(np.percentile(_sims, 95))
        _lectura = ("en oposición" if abs(_fase) >= FOU_OPOSICION_GRADOS else
                    "en fase" if abs(_fase) <= FOU_EN_FASE_GRADOS else "con desfase intermedio")
        # en fase, la fase se pasa a meses con el período central de la banda (la media armónica de sus frecuencias)
        _periodo_c = 1 / np.mean(1 / _periodos)
        fou_coh[(_ven, _a, _b)] = {"coh": _coh, "umbral": _umbral, "signif": _coh > _umbral, "fase": _fase,
                                   "lectura": _lectura, "rezago": -_fase / 360 * _periodo_c,
                                   "vacios": int(_va.sum() + _vb.sum()), "periodos": [float(x) for x in _periodos]}

# efecto de tomar los vacíos de Q como anomalía cero: PL-ONI con PL completa contra PL con esos meses en cero
fou_coh_vacios = {}
for _ven, _pl in (("común 1998–2022", "PL"), ("extendida 1981–2022", "PL*")):
    _spl, _soni = _fou_serie_coh(_ven, _pl), _fou_serie_coh(_ven, "ONI")
    _vq = _fou_serie_coh(_ven, "Q").reindex(_spl.index).isna()
    _soni = _soni.reindex(_spl.index)
    fou_coh_vacios[_ven] = (_fou_coherencia(_spl.fillna(0).to_numpy(), _soni.to_numpy())[0],
                            _fou_coherencia(_spl.where(~_vq).fillna(0).to_numpy(), _soni.to_numpy())[0])

# correlación simple de las anomalías con el ONI de k meses antes: el rezago en que es más fuerte (más negativa)
fou_corr_oni = {}
for _ven, _vars in (("común 1998–2022", ("PL", "PI", "Q")), ("extendida 1981–2022", ("PL*", "Q"))):
    _soni = _fou_serie_coh(_ven, "ONI")
    for _v in _vars:
        _s = _fou_serie_coh(_ven, _v)
        _r = {k: float(_s.corr(_soni.reindex(_s.index).shift(k))) for k in FOU_REZAGOS_ONI}
        _k = min(_r, key=_r.get)
        fou_corr_oni[(_ven, _v)] = {"rezago": _k, "r": _r[_k], "r0": _r[0]}

# el pico de 2.2 meses de PL: ¿se distingue del ruido? Se compara con el pico más alto (±Δf) de espectros de ruido
# blanco con el mismo N, y se mira cuánto tienen PI, Q y T en la misma frecuencia
_e_pl = fou[(_com, "PL", "anomalía")]
_f, _p, _N = _e_pl["f"], _e_pl["p"], _e_pl["N"]
_m = (_f > 1 / 2.4) & (_f < 1 / 2.0)
_f0 = _f[np.flatnonzero(_m)[np.argmax(_p[_m])]]


def _fou_fraccion_en(f, p, f0, n):
    w = (f >= f0 - 1 / n) & (f <= f0 + 1 / n)
    return float(100 * np.trapezoid(p[w], f[w]))


_maximos_blanco = []
for _k in range(FOU_SIMULACIONES):
    _fb, _pb, _, _ = _fou_lomb(pd.Series(_rng_coh.normal(size=_N)))
    _maximos_blanco.append(max(_fou_fraccion_en(_fb, _pb, x, _N) for x in _fb[::FOU_SOBREMUESTREO]))
fou_pico_corto = {"periodo": float(1 / _f0), "PL": _fou_fraccion_en(_f, _p, _f0, _N),
                  "blanco_medio": float(np.mean(_maximos_blanco)), "blanco_95": float(np.percentile(_maximos_blanco, 95)),
                  **{v: _fou_fraccion_en(fou[(_com, v, "anomalía")]["f"], fou[(_com, v, "anomalía")]["p"], _f0, _N)
                     for v in ("PI", "Q", "T")}}

# lo que el texto afirma
_ext = "extendida 1981–2022"
fou_oni_pico_ext = fou_oni[_ext]["pico"]
# el texto dice que, en el registro largo, el pico del ONI coincide (dentro de la resolución) con el de la anomalía de PL*
# (se compara dentro de la misma ventana, regla 6)
fou_plx_ext = fou[(_ext, "PL*", "anomalía")]
assert abs(fou_oni_pico_ext - fou_plx_ext["pico"]) <= max(fou_oni[_ext]["dT"], fou_plx_ext["dT"])
# el texto dice que tomar los vacíos de Q como anomalía cero baja la coherencia: juega en contra de encontrarla
assert all(con <= sin for sin, con in fou_coh_vacios.values())
# el texto dice que la lluvia y el caudal van en oposición con el ONI, y PL y Q en fase
assert all(fou_coh[(ven, a, b)]["lectura"] == "en oposición" for ven, a, b in fou_coh if b == "ONI")
assert all(fou_coh[(ven, a, b)]["lectura"] == "en fase" for ven, a, b in fou_coh if b == "Q")
# el texto dice que PL y Q son coherentes en las dos ventanas
assert all(fou_coh[(ven, a, b)]["signif"] for ven, a, b in fou_coh if b == "Q")
# el texto dice que, con el ONI, Q responde con más rezago que la lluvia (en cada ventana)
assert all(fou_corr_oni[(ven, "Q")]["rezago"] > max(r["rezago"] for (v2, x), r in fou_corr_oni.items() if v2 == ven and x != "Q")
           for ven in ("común 1998–2022", "extendida 1981–2022"))
# qué se atenúa al retirar la climatología: las bandas anual y semianual juntas, en la serie original y en la anomalía
fou_estacional_anom = {v: fou[(_com, v, "anomalía")]["bandas"]["anual"] + fou[(_com, v, "anomalía")]["bandas"]["semianual"]
                       for v in FOU_VENTANAS[_com]}
# el texto dice que se reducen a menos de una décima parte en las cuatro variables
assert all(fou_estacional_anom[v] < fou_estacional[v] / 10 for v in FOU_VENTANAS[_com])
# comparación de las dos fuentes de lluvia (regla 11): coinciden en el pico de 6 meses, no en la banda de 12
fou_fuentes = {v: fou[(_com, v, "original")]["bandas"] for v in ("PL", "PI")}
fou_fuentes_anom = {v: fou[(_com, v, "anomalía")]["bandas"] for v in ("PL", "PI")}
# el texto dice que la banda anual de PI es varias veces la de PL (más del triple) y que coincide con «El régimen»
assert fou_fuentes["PI"]["anual"] > 3 * fou_fuentes["PL"]["anual"]
assert regimen["PI"]["var1"] > regimen["PL"]["var1"]
# el texto dice que en las anomalías el reparto de las dos fuentes difiere menos de FOU_TENDENCIA_MAX_PUNTOS puntos por
# banda (el mismo criterio de «casi no cambia» de la sección)
fou_fuentes_anom_dif = max(abs(fou_fuentes_anom["PL"][b] - fou_fuentes_anom["PI"][b]) for b in fou_fuentes_anom["PL"])
assert fou_fuentes_anom_dif < FOU_TENDENCIA_MAX_PUNTOS
# el texto dice que las dos fuentes tienen el pico más alto de la serie original en 6 meses (ya protegido arriba)
# la conclusión dice que el pico de 6 meses de la serie original de PL, PI y Q no se mueve con la ventana (Hann contra
# Welch, o Lomb por segmentos en Q), con los vacíos de Q ni con el largo del registro (este último, protegido arriba)
assert all(fou_sens[v]["hann_welch_estable"] for v in ("PL", "PI", "Q"))
assert not fou_vacios["original"]["mueve"]
# el texto dice que el pico corto de PL no se distingue del ruido blanco
assert fou_pico_corto["PL"] < fou_pico_corto["blanco_95"]


# ---------------------------------------------------------------- campos climáticos globales (Punto 5)
# Los campos los arma scripts/19_campos_climaticos.py (ERSST v5 y ERA5 a 850 hPa en la malla de 2° de ERSST); los mapas,
# scripts/20_mapas_campos.py. Aquí solo se cuentan lo que el texto del informe dice de ellos.
_cc = xr.open_dataset("out/campos_climaticos_2deg_1998_2022.nc")
_pesos = np.cos(np.deg2rad(_cc.lat.values))[:, None] * np.ones(_cc.sizes["lon"])[None, :]
_tierra = _cc.sst.isnull().all("tiempo").values
_n850 = _cc.q850.notnull().sum("tiempo").values
_cam_meses = _cc.sizes["tiempo"]
cam_n_meses = int(_cam_meses)
cam_malla = (int(_cc.sizes["lat"]), int(_cc.sizes["lon"]))
cam_anios = (int(_cc.tiempo.dt.year.min()), int(_cc.tiempo.dt.year.max()))
cam_cajas_oceano = int((~_tierra).sum())
cam_area_oceano_pct = float(_pesos[~_tierra].sum() / _pesos.sum() * 100)
cam_850_completas_pct = float(_pesos[_n850 == _cam_meses].sum() / _pesos.sum() * 100)      # % del área con los 300 meses
cam_850_nunca_pct = float(_pesos[_n850 == 0].sum() / _pesos.sum() * 100)               # % del área siempre bajo tierra
cam_850_parcial = int(((_n850 > 0) & (_n850 < _cam_meses)).sum())                          # cajas que pierden algunos meses
# la caja de 2° que contiene la cuenca (su centroide)
_cg = gpd.read_file("out/shp_fonce/cuencas_fonce.shp").to_crs(4326)
_cent = _cg.loc[_cg.gauge_id.astype(str) == "24027010"].geometry.iloc[0].centroid
_i = int(np.abs(_cc.lat.values - _cent.y).argmin())
_j = int(np.abs(_cc.lon.values - (_cent.x % 360)).argmin())
cam_caja_cuenca = {"lat": float(_cc.lat.values[_i]), "lon": float(_cc.lon.values[_j]), "n850": int(_n850[_i, _j]),
                   "bajo_tierra": float(_cc.fraccion_bajo_tierra_850.isel(lat=_i, lon=_j).mean())}
# en la latitud de la cuenca, las cajas más cercanas al oriente y al occidente que sí tienen los 300 meses a 850 hPa
_cam_fila = _n850[_i]
_este = next(k for k in range(_j + 1, _cc.sizes["lon"]) if _cam_fila[k] == _cam_meses)
_oeste = next(k for k in range(_j - 1, -1, -1) if _cam_fila[k] == _cam_meses)
cam_caja_cuenca["lon_este"] = float(_cc.lon.values[_este])
cam_caja_cuenca["lon_oeste"] = float(_cc.lon.values[_oeste])
cam_caja_cuenca["vecinas_sin_850"] = int(sum(_n850[_i + di, _j + dj] == 0 for di in (-1, 0, 1) for dj in (-1, 0, 1)
                                             if (di, dj) != (0, 0)))
# transporte de humedad a 850 hPa mes a mes en esas dos cajas (la del oriente y la del occidente de la cuenca): media
# de los 25 años de cada mes del calendario. Dirección en 8 rumbos, hacia donde va el transporte.
def _rumbo(u, v):
    nombres = ["el este", "el noreste", "el norte", "el noroeste", "el oeste", "el suroeste", "el sur", "el sureste"]
    return nombres[int(np.round(np.degrees(np.arctan2(v, u)) / 45)) % 8]
cam_transporte = {}
for _lado, _k in (("este", _este), ("oeste", _oeste)):
    _caja = _cc.isel(lat=_i, lon=_k)
    _qu = _caja.qu850.groupby("tiempo.month").mean().values
    _qv = _caja.qv850.groupby("tiempo.month").mean().values
    _mag = np.hypot(_qu, _qv)
    cam_transporte[_lado] = {"qu": _qu, "qv": _qv, "mag": _mag,
                             "mes_max": int(_mag.argmax()) + 1, "mes_min": int(_mag.argmin()) + 1,
                             "rumbo_max": _rumbo(_qu[_mag.argmax()], _qv[_mag.argmax()]),
                             "meses_hacia_este": [m + 1 for m in range(12) if _qu[m] > 0]}
# al occidente, los meses en que el transporte entra hacia el continente (hacia el este) forman un solo tramo
_me = cam_transporte["oeste"]["meses_hacia_este"]
assert _me and _me == list(range(_me[0], _me[-1] + 1))
assert all(_qu < 0 for _qu in cam_transporte["este"]["qu"][[m - 1 for m in (12, 1, 2)]])   # al oriente, hacia el oeste en DEF
# control de calidad de ERSST contra el ONI (scripts/19)
_oni = pd.read_csv("out/ersst_nino34_contra_oni.csv")
cam_oni = {"r": float(_oni.nino34_ersst_C.corr(_oni.oni_total_C)),
           "dif_media": float((_oni.nino34_ersst_C - _oni.oni_total_C).mean()),
           "dif_max": float((_oni.nino34_ersst_C - _oni.oni_total_C).abs().max()), "n": int(len(_oni))}
# rangos de los campos (para describir los mapas)
cam_rango = {k: (float(_cc[k].mean("tiempo").min()), float(_cc[k].mean("tiempo").max())) for k in ("sst", "q850")}
# lo que el texto afirma
assert cam_n_meses == 12 * (cam_anios[1] - cam_anios[0] + 1) and cam_malla == (89, 180)
assert cam_oni["r"] > 0.99 and cam_oni["dif_max"] < 0.5
assert cam_caja_cuenca["n850"] == 0          # con la máscara estricta, la caja de la cuenca no tiene 850 hPa
_cc.close()

# ---------------------------------------------------------------- explicaciones físicas: cómo la cuenca transforma la lluvia
# La sección «Explicaciones físicas» reúne lo que ya calcularon los bloques anteriores (régimen, desfase, P/ETP,
# ENSO, tendencias). Aquí se agrega lo que faltaba: el ciclo anual de la ETP frente al de la lluvia, el coeficiente
# de escorrentía con las dos fuentes y la clasificación hidroclimática de los meses. Período 1998–2022.

# 1) La energía casi no cambia en el año. Ciclo mensual de la ETP, de PL y de PI con la misma medida: las 12 medias
#    de cada mes del calendario (los 300 meses), y su rango (máximo menos mínimo) como % del promedio de las 12.
_fis_ciclo = pe.groupby(pe.index.month).mean()
fis_ciclo_rango = {c: {"min": float(_fis_ciclo[c].min()), "max": float(_fis_ciclo[c].max()),
                       "pct": float((_fis_ciclo[c].max() - _fis_ciclo[c].min()) / _fis_ciclo[c].mean() * 100)}
                   for c in ("pl", "pi", "etp")}
# el texto dice que la ETP varía mucho menos que la lluvia a lo largo del año (menos de la tercera parte, con las dos)
assert all(fis_ciclo_rango["etp"]["pct"] < fis_ciclo_rango[f]["pct"] / 3 for f in ("pl", "pi"))
# y que la temperatura cambia más de un extremo al otro de la cuenca que del mes más cálido al más frío
assert t_max_mitad - t_min_mitad > 5 * mapa_t_amplitud_anual

# 2) Coeficiente de escorrentía del período con las dos fuentes: suma de Q sobre suma de P en los meses con los dos
#    datos (con PI es el de «Lo que le cae a la cuenca y lo que sale por el río»).
fis_coef = {"pl": float(_bal_pl.q.sum() / _bal_pl.p.sum()), "pi": float(coef_periodo)}

# 3) Clasificación hidroclimática mensual. Se hace con PL, que manda (regla 11), y con PI como contraste, con
#    criterios declarados aquí:
#    - «húmedo»: un mes de una temporada húmeda del régimen (su mediana supera al mes típico, ver «El régimen») que
#      además tiene P/ETP >= CLAS_PE_HUMEDO (cociente de las medias del mes, como en el índice P/ETP) y P < ETP en no
#      más de CLAS_MAX_ANIOS_DEFICIT de los 25 años;
#    - «seco»: los meses de la temporada seca que contiene el mes de menor lluvia (la menor mediana);
#    - «seco relativo»: los de la otra temporada seca.
#    Un mes de temporada húmeda que no cumple los dos umbrales queda «sin clase»: la clasificación no se fuerza.
#    CLAS_MAX_ANIOS_DEFICIT = 0 (ningún año) es el criterio más estricto; con 1 la clasificación con PL no cambia.
CLAS_PE_HUMEDO = 2.0
CLAS_MAX_ANIOS_DEFICIT = 0
CLAS_ORDEN = ["húmedo", "seco relativo", "seco"]


def temporadas_del_regimen(fuente):
    """Temporadas del régimen de `fuente` (PL, PI o Q): [(meses 1-12, ¿húmeda?)], en el orden del calendario."""
    r = regimen[fuente]
    return [([(m + i) % 12 + 1 for i in range(d)], h) for m, d, h in _reg_rachas(r["medianas"] > r["tipico"])]


def nombre_meses(meses):
    """«marzo a mayo y octubre a noviembre»: los meses agrupados en tramos seguidos (diciembre sigue a enero)."""
    dentro = np.array([m in meses for m in range(1, 13)])
    tramos = sorted((m, d) for m, d, h in _reg_rachas(dentro) if h)
    return " y ".join(MESES_LARGOS_ES[m] if d == 1 else f"{MESES_LARGOS_ES[m]} a {MESES_LARGOS_ES[(m + d - 1) % 12]}"
                      for m, d in tramos)


def clasificar_meses(fuente, max_anios_deficit=CLAS_MAX_ANIOS_DEFICIT):
    """Clase de cada mes del calendario (1-12) con la lluvia `fuente` (PL o PI), según los criterios de arriba."""
    f = fuente.lower()
    temporadas = temporadas_del_regimen(fuente)
    mes_minimo = int(np.argmin(regimen[fuente]["medianas"])) + 1
    assert sum(not h for _, h in temporadas) == 2          # régimen bimodal: dos temporadas secas
    clase = {}
    for meses, humeda in temporadas:
        for mes in meses:
            if humeda:
                cumple = (pe_mes.loc[mes, f] >= CLAS_PE_HUMEDO
                          and pe_mes_deficit_anios.loc[mes, f] <= max_anios_deficit)
                clase[mes] = "húmedo" if cumple else "sin clase"
            else:
                clase[mes] = "seco" if mes_minimo in meses else "seco relativo"
    return pd.Series(clase).sort_index()


clas = {f: clasificar_meses(f) for f in ("PL", "PI")}
# con PL, la que manda, cada mes del calendario tiene una de las tres clases (si deja de ser así, hay que revisar
# los criterios con el usuario, no forzar el resultado)
assert set(clas["PL"]) == set(CLAS_ORDEN)
# con 1 año de déficit admitido, la clasificación con PL sería la misma (lo que dice el comentario de arriba)
assert clasificar_meses("PL", max_anios_deficit=1).equals(clas["PL"])
clas_pi_sin_clase = [m for m in range(1, 13) if clas["PI"][m] == "sin clase"]

# la tabla de la síntesis: una fila por clase, con PL (y PI en paralelo) y el caudal del régimen de Q
_q_temporadas = temporadas_del_regimen("Q")
_q_mes_minimo = int(np.argmin(regimen["Q"]["medianas"])) + 1
clas_tabla = []
for _clase in CLAS_ORDEN:
    _meses = [m for m in range(1, 13) if clas["PL"][m] == _clase]
    _humeda = _clase == "húmedo"
    # temporadas de Q del mismo tipo (húmeda o seca) que se cruzan con los meses de la clase
    _q_meses = sorted({m for meses, h in _q_temporadas if h == _humeda and set(meses) & set(_meses) for m in meses})
    clas_tabla.append({
        "clase": _clase, "meses": _meses, "nombre": nombre_meses(_meses),
        "mediana_pl": (float(min(regimen["PL"]["medianas"][m - 1] for m in _meses)),
                       float(max(regimen["PL"]["medianas"][m - 1] for m in _meses))),
        "pe": {f: (float(pe_mes.loc[_meses, f].min()), float(pe_mes.loc[_meses, f].max())) for f in ("pl", "pi")},
        "deficit_max": {f: int(pe_mes_deficit_anios.loc[_meses, f].max()) for f in ("pl", "pi")},
        "mes_mas_deficit": {f: int(pe_mes_deficit_anios.loc[_meses, f].idxmax()) for f in ("pl", "pi")},
        "q_meses": _q_meses, "q_nombre": nombre_meses(_q_meses), "q_minimo": _q_mes_minimo in _q_meses,
    })
clas_fila = {r["clase"]: r for r in clas_tabla}
# meses con déficit frecuente (P < ETP en más de la mitad de los años, el mismo criterio del índice P/ETP)
clas_deficit_frecuente = {f: [m for m in range(1, 13) if pe_mes_deficit_anios.loc[m, f] > pe_n_anios / 2]
                          for f in ("pl", "pi")}

# lo que afirman la tabla y la frase de síntesis
assert all(r["ie"] >= UNEP_HUMEDO and not r["bajo_humedo"] for r in pe_indice.values())   # húmeda con las dos y en todos los años
assert all(r["clase"] == "bimodal" for r in regimen.values())
assert clas_deficit_frecuente["pl"] == clas_deficit_frecuente["pi"] == [1]                # «sin déficit sostenido salvo enero»
assert regimen["PL"]["min"] == "enero" and 1 in clas_fila["seco"]["meses"]
assert clas_fila["seco"]["q_minimo"]                                                       # el mínimo de Q cae en la clase «seco»
assert all(r["q_meses"] for r in clas_tabla)

# las alternativas: qué cambia con PI
clas_pi_humedas = sorted({m for meses, h in temporadas_del_regimen("PI") if h for m in meses})
clas_pl_humedas = sorted({m for meses, h in temporadas_del_regimen("PL") if h for m in meses})
clas_solo_pi_humedas = [m for m in clas_pi_humedas if m not in clas_pl_humedas]
clas_solo_pl_humedas = [m for m in clas_pl_humedas if m not in clas_pi_humedas]
# el texto dice: con PI, junio y septiembre caen en temporada húmeda (con PL no), y enero tiene déficit con PI y no con PL
assert clas_solo_pi_humedas == [6, 9] and not clas_solo_pl_humedas
assert pe_solo_pi == [1] and not pe_meses_deficit["pl"]
# y que el año más seco, con cualquiera de las dos fuentes, sigue a más del doble del umbral de «húmedo» de UNEP
fis_anio_mas_seco = min(pe_indice.values(), key=lambda r: r["min"])
assert fis_anio_mas_seco["min"] > 2 * UNEP_HUMEDO

# los meses en que salió más agua de la que cayó (con PL) son todos de las temporadas secas
fis_sobre1_meses = list(_bal_pl_coef.index[_bal_pl_coef > 1])
fis_sobre1_en_secos = all(clas["PL"][p.month] != "húmedo" for p in fis_sobre1_meses)

# 4) La hipótesis y sus predicciones, con las cifras de hoy
#    a) los picos de Q caen un mes después de los de PL
_mes_num = {nombre: i + 1 for i, nombre in enumerate(MESES_LARGOS_ES)}
fis_atraso_picos = [(_mes_num[q] - _mes_num[p]) % 12 for p, q in zip(regimen["PL"]["picos"], regimen["Q"]["picos"])]
assert fis_atraso_picos == [1, 1]
#    b) la tendencia de marzo: PL* sube y Q no tiene tendencia significativa ese mes
fis_marzo = inc_lluvia_fdr[3]
assert inc_fdr["PL*"]["ols"] == [3] and fis_marzo["q_mes"]["p"] >= TEND_ALFA
#    c) el calentamiento y la ETP; Q sin tendencia en el registro completo
fis_t_decada = float(met_global[("T media", "completo")]["ols_Xmes"]["pend"])
fis_q_global = met_global[("Q", "completo")]["ols_Xmes"]
assert fis_t_decada > 0 and fis_q_global["p_hac"] >= TEND_ALFA and not inc_fdr["Q"]["ols"]
#    d) fuera del ajuste, la lluvia supera a la climatología, y la del mes anterior mejora la estimación,
#       más con PL que con PI
assert all(mod_rmse(f, "M1") < mod_rmse(f, MOD_REFERENCIA) for f in MOD_FUENTES)
assert mod_rmse("PL", "M1") - mod_rmse("PL", MOD_ELEGIDO) > mod_rmse("PI", "M1") - mod_rmse("PI", MOD_ELEGIDO) > 0

#    e) lo que dicen los textos de la ZCIT y del ENSO
# Poveda (2004): temporadas lluviosas en abril-mayo y octubre-noviembre. El primer pico de PL, PI y Q cae en la
# primera y el segundo en la segunda.
POVEDA_LLUVIOSAS = (("abril", "mayo"), ("octubre", "noviembre"))
assert all(p[0] in POVEDA_LLUVIOSAS[0] and p[1] in POVEDA_LLUVIOSAS[1] for p in (pico_pl, pico_pi, pico_q))
# enero es el mes de menor P/ETP con las dos fuentes, y la temporada «seco relativo» tiene excedente todos los meses
assert all(int(pe_mes[f].idxmin()) == 1 for f in ("pl", "pi"))
assert all(clas_fila["seco relativo"]["pe"][f][0] > 1 for f in ("pl", "pi"))
# el ciclo de P/ETP lo pone la lluvia: sus 12 valores van con las 12 medias de la lluvia
fis_rho_pe_lluvia = {f: float(stats.spearmanr(pe_mes[f], _fis_ciclo[f])[0]) for f in ("pl", "pi")}
assert all(r > 0.95 for r in fis_rho_pe_lluvia.values())
# ENSO: en la banda de 3 a 7 años, todo va en oposición al ONI; en 1998-2022 solo PI es significativa, en el registro
# largo PL* y Q sí lo son; Q tiene su correlación más negativa con el ONI dos meses antes, en las dos ventanas
_fis_com, _fis_ext = "común 1998–2022", "extendida 1981–2022"
fis_coh_oni = {(ven, v): fou_coh[(ven, v, "ONI")] for (ven, v, b) in fou_coh if b == "ONI"}
assert all(r["lectura"] == "en oposición" for r in fis_coh_oni.values())
assert fis_coh_oni[(_fis_com, "PI")]["signif"] and not fis_coh_oni[(_fis_com, "PL")]["signif"]
assert fis_coh_oni[(_fis_ext, "PL*")]["signif"] and fis_coh_oni[(_fis_ext, "Q")]["signif"]
fis_q_rezago_oni = fou_corr_oni[(_fis_com, "Q")]["rezago"]
assert fou_corr_oni[(_fis_ext, "Q")]["rezago"] == fis_q_rezago_oni > 0
# el año más seco es el mismo con PL y con PI, y el año de La Niña está entre los dos más húmedos
fis_anio_seco = int(anom_anual.PL.idxmin())
assert int(anom_anual.PI.idxmin()) == fis_anio_seco == anom_secos[0]
fis_anio_humedo = anom_humedos[0]
assert anom_anios[fis_anio_seco]["nino"] > anom_anios[fis_anio_seco]["nina"] == 0
assert anom_anios[fis_anio_humedo]["nina"] > anom_anios[fis_anio_humedo]["nino"]
# convección: con T máx atípicamente baja, PL estuvo sobre lo normal; con T máx atípicamente alta, bajo lo normal
fis_pl_tmax = {"baja": _media_z(t_max_baja, "PL"), "alta": _media_z(t_max_alta, "PL")}
assert fis_pl_tmax["baja"] > 0 > fis_pl_tmax["alta"]
assert aj_imerg["por_1000m"] < 0




# ---------------------------------------------------------------- correlaciones de la cuenca con los campos (Punto 5.2)
# En cada caja de 2° y para cada mes del calendario j se correlacionan, a través de los años, la anomalía de la
# variable de la cuenca en el mes j con la anomalía del campo ℓ meses antes:
#     r_j(caja; ℓ) = corr_{años} [ aX(año, j), aY(caja, (año, j) − ℓ) ]
# ℓ > 0: el campo antecede a la cuenca; con ℓ = 1, enero se empareja con diciembre del año anterior.
# Anomalías: el valor menos la media de su mes del calendario en 1998-2022, por variable y por caja (la misma
# referencia fija de la sección de anomalías). Pearson es la referencia; Spearman se calcula en todas las cajas para
# examinar dónde los extremos o la asimetría cambian la lectura. «mes 13» = todos los meses juntos, con anomalías.
# Decisiones del usuario (2026-10-09): PL, Q y PI contra la SST, la rapidez del viento a 850 hPa
# |V| = √(u² + v²) (de las medias mensuales de u y v) y la humedad específica a 850 hPa; ℓ = 0, y ℓ = 1 para la SST.
CORR_REZAGOS = {"sst": (0, 1), "viento850": (0, ), "q850": (0, )}
CORR_CUENCA = ("PL", "Q", "PI")
CORR_N_MINIMO = 20                 # pares mínimos para dibujar una caja (decisión del usuario): 80 % de 25 años


def _anomalia_mensual(x, meses):
    """Anomalía por mes del calendario: x (tiempo, ...) menos la media de su mes, con los valores válidos."""
    a = np.full_like(x, np.nan, dtype=float)
    for j in range(1, 13):
        sel = meses == j
        validos = np.isfinite(x[sel]).sum(axis=0)                 # la tierra en la SST no tiene ningún valor
        suma = np.nansum(x[sel], axis=0)
        media = np.divide(suma, validos, out=np.full_like(suma, np.nan, dtype=float), where=validos > 0)
        a[sel] = x[sel] - media
    return a


def _rangos_por_columna(m):
    """Rangos (empates promediados) de cada columna; las columnas no tienen NaN."""
    return np.apply_along_axis(stats.rankdata, 0, m)


def _correlacion(x, Y):
    """Pearson y Spearman de un vector x (años) contra cada columna de Y (años, cajas), con los pares válidos de
    cada caja. Devuelve r_pearson, r_spearman y n (pares)."""
    ok = np.isfinite(x)[:, None] & np.isfinite(Y)
    n = ok.sum(axis=0)
    r_p = np.full(Y.shape[1], np.nan)
    r_s = np.full(Y.shape[1], np.nan)
    # se agrupan las cajas por su patrón de años válidos: dentro de un grupo, la muestra es la misma
    patrones, grupo = np.unique(ok.T, axis=0, return_inverse=True)
    for g, patron in enumerate(patrones):
        if patron.sum() < 3:
            continue
        cols = np.flatnonzero(grupo.ravel() == g)
        xs, Ys = x[patron], Y[np.ix_(patron, cols)]
        xc, Yc = xs - xs.mean(), Ys - Ys.mean(axis=0)
        den = np.sqrt((xc ** 2).sum() * (Yc ** 2).sum(axis=0))
        with np.errstate(invalid="ignore", divide="ignore"):
            r_p[cols] = (xc[:, None] * Yc).sum(axis=0) / den
        xr_, Yr = stats.rankdata(xs), _rangos_por_columna(Ys)
        xrc, Yrc = xr_ - xr_.mean(), Yr - Yr.mean(axis=0)
        den = np.sqrt((xrc ** 2).sum() * (Yrc ** 2).sum(axis=0))
        with np.errstate(invalid="ignore", divide="ignore"):
            r_s[cols] = (xrc[:, None] * Yrc).sum(axis=0) / den
    return r_p, r_s, n


_cc = xr.open_dataset("out/campos_climaticos_2deg_1998_2022.nc")
_t_campo = pd.PeriodIndex(pd.to_datetime(_cc.tiempo.values), freq="M")
_meses_campo = _t_campo.month.to_numpy()
corr_campos = {
    "sst": _cc.sst.values.astype(float),
    "viento850": np.hypot(_cc.u850.values, _cc.v850.values).astype(float),
    "q850": _cc.q850.values.astype(float),
}
_forma = corr_campos["sst"].shape[1:]
_anom_campo = {k: _anomalia_mensual(v.reshape(len(_t_campo), -1), _meses_campo) for k, v in corr_campos.items()}
_cuenca = {"PL": red.reindex(PERIODOS), "Q": variables_resumen["Q"].reindex(PERIODOS),
           "PI": comp["IMERG"].reindex(PERIODOS)}
assert (PERIODOS == _t_campo).all()
_anom_cuenca = {k: _anomalia_mensual(v.to_numpy(dtype=float), PERIODOS.month.to_numpy()) for k, v in _cuenca.items()}

corr_resultados = {}          # (cuenca, campo, ℓ) -> {"r_p", "r_s", "n"} con forma (13, lat, lon); índice 12 = todos
for _campo, _rezagos in CORR_REZAGOS.items():
    for _l in _rezagos:
        # campo desplazado: en la posición t queda el campo de t − ℓ (vacío si cae antes de 1998-01)
        _Y = np.full_like(_anom_campo[_campo], np.nan)
        _Y[_l:] = _anom_campo[_campo][:len(_t_campo) - _l]
        if _l == 1:      # comprobación del cambio de año: enero de 2000 queda con diciembre de 1999
            _k = PERIODOS.get_loc(pd.Period("2000-01", "M"))
            assert np.array_equal(_Y[_k], _anom_campo[_campo][PERIODOS.get_loc(pd.Period("1999-12", "M"))], equal_nan=True)
        for _v in CORR_CUENCA:
            _x = _anom_cuenca[_v]
            _rp, _rs, _n = (np.full((13, _forma[0] * _forma[1]), np.nan) for _ in range(3))
            for _j in range(1, 13):
                _sel = PERIODOS.month.to_numpy() == _j
                _rp[_j - 1], _rs[_j - 1], _n[_j - 1] = _correlacion(_x[_sel], _Y[_sel])
            _rp[12], _rs[12], _n[12] = _correlacion(_x, _Y)          # todos los meses juntos (anomalías)
            corr_resultados[(_v, _campo, _l)] = {k: a.reshape(13, *_forma) for k, a in
                                                 (("r_p", _rp), ("r_s", _rs), ("n", _n))}

# (a) Centrar o estandarizar con constantes positivas no cambia Pearson (para un mes fijo y la misma muestra): se
#     comprueba repitiendo PL contra la SST con anomalías estandarizadas (divididas por la desviación de cada mes).
def _estandarizar(a, meses):
    z = np.full_like(a, np.nan)
    for j in range(1, 13):
        sel = meses == j
        validos = np.isfinite(a[sel]).sum(axis=0)
        de = np.full(a.shape[1:], np.nan)
        hay = validos >= 2
        de[..., hay] = np.nanstd(a[sel][..., hay], axis=0, ddof=1) if a.ndim > 1 else np.nanstd(a[sel], ddof=1)
        z[sel] = a[sel] / de
    return z
with np.errstate(invalid="ignore", divide="ignore"):
    _zx = _estandarizar(_anom_cuenca["PL"], PERIODOS.month.to_numpy())
    _zY = _estandarizar(_anom_campo["sst"], _meses_campo)
for _j in (1, 7):
    _sel = PERIODOS.month.to_numpy() == _j
    _rz = _correlacion(_zx[_sel], _zY[_sel])[0]
    assert np.allclose(_rz, corr_resultados[("PL", "sst", 0)]["r_p"][_j - 1].ravel(), equal_nan=True, atol=1e-9)

# (b) Resumen sobre la región Niño 3.4 (5° S-5° N, 170° O-120° O): correlación media de las cajas, ponderada por el
#     coseno de la latitud, para cada mes de la cuenca.
_lat_c, _lon_c = _cc.lat.values, _cc.lon.values
_caja34 = (np.abs(_lat_c)[:, None] <= 5) & (_lon_c[None, :] >= 190) & (_lon_c[None, :] <= 240)
_w34 = np.cos(np.deg2rad(_lat_c))[:, None] * _caja34
corr_nino34 = {}
for (_v, _campo, _l), _d in corr_resultados.items():
    if _campo == "sst":
        corr_nino34[(_v, _l)] = [float(np.nansum(_d["r_p"][k] * _w34) / _w34.sum()) for k in range(13)]
# (c) Pearson contra Spearman en Q contra la SST (ℓ = 0): en cuántas cajas dibujables (n mínimo, 60° S-60° N) difieren
#     más de 0.2, y en cuántas cambian de signo con |r| > 0.3 en alguno de los dos.
_d = corr_resultados[("Q", "sst", 0)]
_dom = (np.abs(_lat_c) <= 60)[None, :, None] & (_d["n"][:12] >= CORR_N_MINIMO)
_dif = np.abs(_d["r_p"][:12] - _d["r_s"][:12])
corr_spearman_q = {"cajas": int(_dom.sum()),
                   "dif_02_pct": float((_dif > 0.2)[_dom].mean() * 100),
                   "signo_pct": float(((np.sign(_d["r_p"][:12]) != np.sign(_d["r_s"][:12]))
                                       & (np.maximum(np.abs(_d["r_p"][:12]), np.abs(_d["r_s"][:12])) > 0.3))[_dom].mean() * 100),
                   "dif_media": float(np.nanmean(_dif[_dom]))}
# (d) Pares por combinación: el rango de n en las cajas dibujables, por mes (lo pide el enunciado en cada figura)
corr_n_rango = {k: (int(np.nanmin(np.where(d["n"][:12] >= CORR_N_MINIMO, d["n"][:12], np.nan))),
                    int(np.nanmax(d["n"][:12]))) for k, d in corr_resultados.items()}
# (e) Cuánto cambia la tabla de Niño 3.4 con ℓ = 1: la mayor diferencia, en qué variable y en qué mes
_cambios = [(abs(corr_nino34[(_v, 1)][k] - corr_nino34[(_v, 0)][k]), _v, k) for _v in CORR_CUENCA for k in range(12)]
corr_cambio_rezago = {"max": max(_cambios)[0], "var": max(_cambios)[1], "mes": max(_cambios)[2] + 1,
                      "mediana": float(np.median([c[0] for c in _cambios]))}
# lo que el texto afirma
assert corr_spearman_q["dif_02_pct"] < 10 and corr_spearman_q["signo_pct"] < 1
_n34 = corr_nino34[("PL", 0)][:12]
assert min(_n34) < -0.4                                   # algún mes con relación inversa clara con Niño 3.4
assert corr_nino34[("PL", 1)][12] < 0 and corr_nino34[("PL", 0)][12] < 0

# se guardan para los mapas (scripts/21_mapas_correlacion.py)
_vars = {}
for (_v, _campo, _l), _d in corr_resultados.items():
    for _k, _a in _d.items():
        _vars[f"{_k}__{_v}__{_campo}__l{_l}"] = (("mes", "lat", "lon"), _a.astype("float32"))
_salida = xr.Dataset(_vars, coords={"mes": np.arange(1, 14), "lat": _cc.lat.values, "lon": _cc.lon.values})
_salida.attrs = {"descripcion": "Correlación, a través de los años, de la anomalía de la cuenca en el mes j con la "
                 "anomalía del campo ℓ meses antes; mes 13 = todos los meses juntos. r_p: Pearson; r_s: Spearman; "
                 "n: pares válidos. Anomalías respecto a la media de cada mes en 1998-2022.",
                 "n_minimo": CORR_N_MINIMO, "generado_por": "scripts/18_calculos_informe.py"}
_salida.to_netcdf("out/correlaciones_campos.nc", encoding={k: {"zlib": True, "complevel": 4} for k in _vars})
_cc.close()
