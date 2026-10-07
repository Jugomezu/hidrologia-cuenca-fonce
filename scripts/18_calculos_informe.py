"""El análisis del informe: lee out/ y data/ y calcula todo lo que muestra reporte/reporte-fonce.html.

Está organizado en bloques por tema, cada uno marcado con un comentario «# ---- tema». Cada bloque deja sus
resultados en variables (números, tablas de pandas, series para las gráficas) que usa la página. Las
cifras de los textos del informe salen de aquí, nunca escritas a mano.

No se corre solo: lo corre scripts/18b_reporte_html.py, que arma la página. Para regenerar el informe,
desde la raíz del repositorio:

    python scripts/18b_reporte_html.py

Las figuras fijas de reporte/figuras/ las hacen 08, 09, 10 y 14.
"""
import base64, hashlib, html, json
from pathlib import Path
import geopandas as gpd
from scipy import stats
import numpy as np
import pandas as pd

FIG = Path("reporte/figuras")
SALIDA = Path("reporte/reporte-fonce.html")
# Plotly se incrusta en el HTML para que abra sin internet. La copia está en el repositorio (origen y SHA-256
# en DATOS_FUENTES.md); si el archivo cambia, el script se detiene.
PLOTLY = Path("reporte/vendor/plotly-2.32.0.min.js")
PLOTLY_SHA256 = "0a17719a72751704861215da0e5c5cdb3f9a8d50eff5cb84cb6f8b80786682b0"
assert hashlib.sha256(PLOTLY.read_bytes()).hexdigest() == PLOTLY_SHA256, f"{PLOTLY} no es la versión registrada"
PLOTLY_JS = PLOTLY.read_text(encoding="utf-8")
assert "</script" not in PLOTLY_JS.lower()       # no puede cerrar la etiqueta <script> en la que va

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
_mes = lambda m: MESES_LARGOS_ES[m - 1]
var_filas = "\n".join(
    f"<tr><td><b>{v}</b></td><td>{_mes(var_mas[v][0])} ({var_tabla.loc[(v, var_mas[v][0]), 'cv']:.{2 if v == 'T media' else 0}f} %)</td>"
    f"<td>{_mes(var_mas[v][1])} ({var_tabla.loc[(v, var_mas[v][1]), 'de']:.{2 if v == 'T media' else 1}f} {VAR_SERIES[v][1]})</td>"
    f"<td>{', '.join(_mes(m) for m in var_fuertes[v]) or 'ninguno' if v in _VAR_LC else '—'}</td>"
    f"<td>{_mes(var_top[v][0][1])} de {var_top[v][0][0]} ({var_top[v][1]:+.{2 if v == 'T media' else 1}f} %)</td></tr>"
    for v in VAR_SERIES)

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
