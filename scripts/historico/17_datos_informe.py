"""Prepara out/informe_datos.json para los dos informes HTML.

REGLA DE ORO: ningun umbral, peso ni rampa se escribe aqui. Todo sale de
out/reglas_extraidas.json, que scripts/historico/18_extraer_reglas.py lee directamente del
codigo que se ejecuto (13_preliminar.py, 16_analisis_completo.py, 10a_geometria.py)
y verifica contra los resultados guardados.

Este script solo: (1) junta valores por cuenca, (2) cuenta el embudo aplicando las
reglas extraidas, (3) hace la prueba de sensibilidad de pesos (posterior a la
decision, no es parte de la regla) y (4) incorpora la investigacion manual
(POMCA y notas) con su enlace de fuente.

Ejecutar en orden:  python scripts/historico/18_extraer_reglas.py  ->  python scripts/historico/17_datos_informe.py
"""
import json
import numpy as np, pandas as pd
from pathlib import Path

R = json.loads(Path("out/reglas_extraidas.json").read_text(encoding="utf-8"))
FONCE = R["verificacion"]["primero"]          # la primera del ranking segun el codigo
a = pd.read_csv("out/analisis_174.csv")
master = pd.read_csv("out/camels_col_master.csv")
pre = pd.read_csv("out/preliminar_v2.csv")
geo = pd.read_csv("out/geometria.csv").set_index("gauge_id")

# ------------------------------------------------------------------ nombres
cne = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str,
                  usecols=["codigo", "nombre", "corriente", "categoria", "estado", "municipio"])
cne["gauge_id"] = cne["codigo"].str.lstrip("0").astype("int64")
cne["nombre"] = cne["nombre"].str.replace(r"\s*\[\d+\]$", "", regex=True).str.strip()
cne = cne.drop_duplicates("gauge_id").set_index("gauge_id")
for c in ["nombre", "corriente", "categoria", "estado", "municipio"]:
    a[c] = a["gauge_id"].map(cne[c])

# ------------------------------------- niveles de anidamiento (descriptivo, no es regla)
subs_of = {}
for g, r in geo.iterrows():
    subs_of[int(g)] = [] if pd.isna(r["subs"]) or r["subs"] == "" else [int(x) for x in str(r["subs"]).split(";")]

def depth(g, memo={}):
    if g in memo:
        return memo[g]
    hijos = [s for s in subs_of.get(g, []) if s in subs_of]
    memo[g] = 1 + (max(depth(s) for s in hijos) if hijos else 0)
    return memo[g]

a["niveles"] = a["gauge_id"].map(lambda g: depth(int(g)))

# ------------------------------------------------------------------ componentes (de 16)
CID = R["comp_id"]                                   # s_registro -> reg ...
CNOM = R["comp_nombre"]
COMPONENTES = []
for c in R["puntaje"]["componentes"]:
    COMPONENTES.append(dict(
        id=CID[c["col"]], col=c["col"], nombre=CNOM[CID[c["col"]]], peso=c["peso"],
        archivo=c["archivo"], desde=c["desde"], hasta=c["hasta"], codigo=c["codigo"],
        terminos=[dict(tipo=t["tipo"], peso=t.get("peso"), codigo=t["codigo"],
                       col=t.get("col"), curva=t.get("curva"),
                       factores=[dict(col=f["col"], curva=f["curva"], codigo=f["codigo"]) for f in t.get("factores", [])])
                  for t in c["terminos"]]))
PESOS = {c["id"]: c["peso"] for c in COMPONENTES}
COMP_COL = {c["id"]: c["col"] for c in COMPONENTES}

# ---------------------------------------------- criterios (metricas) tal como los extrae 18
CRITERIOS = []
for m in R["metricas"]:
    if not (m["filtros"] or m["banderas"] or m["puntajes"]):
        continue
    CRITERIOS.append(dict(
        id=m["id"], nombre=m["nombre"], corto=m["corto"], origen=m["origen"], campo=m["campo"],
        unidad=m["unidad"], columnas=m["columnas"], porque=m["porque"], fuente=m["fuente"],
        filtros=m["filtros"], banderas=m["banderas"], puntajes=m["puntajes"]))

# --------------------------------------------------------------- por cuenca
def f(x, nd=3):
    return None if pd.isna(x) else round(float(x), nd)

def t(x):
    return None if pd.isna(x) else str(x)

basins = []
for _, r in a.iterrows():
    basins.append(dict(
        id=int(r.gauge_id), nombre=t(r.nombre), rio=t(r.corriente), dpto=t(r.gauge_department),
        muni=t(r.municipio), tipo_est=t(r.categoria), estado=t(r.estado), region=t(r.region),
        pool=bool(r.pasa_series),
        area=f(r.area, 1), imerg_px=int(r.imerg_px), imerg_cob=f(r.imerg_cobertura, 3),
        q_years=f(r.q_years, 2), imerg_years=f(r.imerg_q_years, 2), q_miss=f(r.q_miss, 2),
        pr_miss=f(r.pr_miss, 2), q_gap_max=int(r.q_gap_max), q_end=str(r.q_end)[:10],
        n_years_obs=f(r.n_years_obs, 2), missing_pct=f(r.missing_pct, 2),
        n_sub=int(r.n_sub), n_sub_ok=int(r.n_sub_ok), niveles=int(r.niveles),
        fase_imerg=f(r.fase_imerg, 2), fase_chirps=f(r.fase_chirps, 2),
        r_mes_imerg=f(r.r_mes_imerg, 2), RR_imerg=f(r.RR_imerg, 2), RRcv_imerg=f(r.RRcv_imerg, 2),
        escalon=f(r.escalon, 1), flat=f(r.flat, 2),
        urban_perc=f(r.urban_perc, 2), water_bodies_perc=f(r.water_bodies_perc, 2),
        bosque=f(r.forest_perc, 0), agro=f(r.agricul_livestock_perc, 0), P_imerg=f(r.P_imerg_anual, 0),
        banderas=[x for x in str(r.banderas).split(";") if x and x != "nan"],
        comp={cid: f(r[col]) for cid, col in COMP_COL.items()},
        score=f(r.score),
    ))

# ------------------------------------------------------------------ embudo (reglas extraidas)
def aplica(op, x, v):
    return {"<": x < v, "<=": x <= v, ">": x > v, ">=": x >= v, "==": x == v}[op]

def pasa(df, it):
    x = df[it["col"]]
    return x.between(it["min"], it["max"]) if it["op"] == "between" else aplica(it["op"], x, it["valor"])

fmeta, fser = R["filtros"][0], R["filtros"][1]
solo, ok_meta = [], pd.Series(True, index=master.index)
for it in fmeta["items"]:
    p = pasa(master, it)
    ok_meta &= p
    solo.append(dict(col=it["col"], etapa="metadatos", base=int(len(master)), falla=int((~p).sum()), **{k: it[k] for k in it if k in ("op", "valor", "min", "max")}))
ok_ser = pd.Series(True, index=pre.index)
for it in fser["items"]:
    p = pasa(pre, it)
    ok_ser &= p
    solo.append(dict(col=it["col"], etapa="series", base=int(len(pre)), falla=int((~p).sum()), **{k: it[k] for k in it if k in ("op", "valor", "min", "max")}))
n_meta, n_ser = int(ok_meta.sum()), int(ok_ser.sum())
assert n_meta == 174 and n_ser == 134
cob_ok = int((a["imerg_cobertura"] >= 0.98).sum())
embudo = [
    dict(paso="Todo CAMELS-COL", n=int(len(master)), nota="346 cuencas con caudal diario 1981–2022."),
    dict(paso="Filtros de metadatos", n=n_meta,
         archivo=fmeta["archivo"], desde=fmeta["desde"], hasta=fmeta["hasta"],
         nota="Área, años de registro y faltantes de caudal, leídos de los metadatos de CAMELS-COL."),
    dict(paso="Filtros sobre la serie diaria", n=n_ser,
         archivo=fser["archivo"], desde=fser["desde"], hasta=fser["hasta"],
         nota="Faltantes de caudal, faltantes de precipitación y hueco continuo más largo, medidos en la serie diaria."),
    dict(paso="Ranking por puntaje", n=1,
         archivo=R["puntaje"]["ranking"]["archivo"], desde=R["puntaje"]["ranking"]["desde"], hasta=R["puntaje"]["ranking"]["hasta"],
         nota="Las 134 se ordenan por puntaje; la primera es la elegida. Las banderas se anotan pero no descartan."),
]

# ------------------------------------------------------ sensibilidad (posterior a la decision)
pool = a[a["pasa_series"]].copy()
cols = [COMP_COL[k] for k in ("reg", "sub", "imerg", "bal", "nat")]
C = pool[cols].fillna(0).to_numpy()
ids = pool["gauge_id"].to_numpy()
iF = int(np.where(ids == FONCE)[0][0])
nombres = [CNOM[k] for k in ("reg", "sub", "imerg", "bal", "nat")]
w0 = np.array([PESOS[k] for k in ("reg", "sub", "imerg", "bal", "nat")], dtype=float)
rng = np.random.default_rng(20260919)

rob = {}
for nombre, alpha in [("uniforme", 1.0), ("extremos", 0.3)]:
    W = rng.dirichlet([alpha] * 5, size=20000)
    S = W @ C.T
    rank = (S > S[:, [iF]]).sum(axis=1) + 1
    vc = pd.Series(ids[S.argmax(axis=1)]).value_counts()
    rob[nombre] = dict(n=20000, p1=float((rank == 1).mean()), p3=float((rank <= 3).mean()),
                       p5=float((rank <= 5).mean()), mediana=int(np.median(rank)), peor=int(rank.max()),
                       lideres=[dict(id=int(k), p=float(v / 20000)) for k, v in vc.head(6).items()])
rob["solo_componente"] = [dict(componente=nombres[k], rango=int((C[:, k] > C[iF, k]).sum() + 1),
                               empates=int((C[:, k] == C[iF, k]).sum() - 1)) for k in range(5)]
quitar = []
for k in range(5):
    w = w0.copy(); w[k] = 0; w = w / w.sum()
    S = C @ w
    quitar.append(dict(sin=nombres[k], rango=int((S > S[iF]).sum() + 1), lider=int(ids[S.argmax()])))
rob["quitar"] = quitar
rob["n_pool"] = int(len(pool))
rob["pesos_usados"] = {k: PESOS[k] for k in ("reg", "sub", "imerg", "bal", "nat")}

# ------------------------------------------------- investigacion manual (con fuente)
# estado POMCA: ok = existe/aprobado | proc = en formulación | parc = solo una parte | nc = sin confirmar
MANUAL = {
 "24027010": dict(corto="Fonce", largo="Fonce @ San Gil",
    pomca=dict(estado="ok", etiqueta="2010 · en actualización",
               texto="Existe un POMCA formulado en 2010 que se está reemplazando: en abril de 2026 la CAS inició la formulación del nuevo, con Corpoboyacá.",
               url="https://www.vanguardia.com/santander/guanenta/2026/04/17/iniciaron-proceso-de-creacion-del-nuevo-pomca-del-rio-fonce/"),
    nota="Estación madre limnimétrica (lectura de mira). En la rama Mérida–Pienta–Taquiza falta todo 2015 (Mérida y Pienta) y hay huecos en Taquiza en 2015–2016."),
 "23107020": dict(corto="Regla", largo="Regla @ La Bodega",
    pomca=dict(estado="proc", etiqueta="En formulación",
               texto="POMCA del río San Bartolo y otros directos al Magdalena Medio (SZH 2310): Corantioquia convocó el consejo de cuenca para su formulación.",
               url="https://www.corantioquia.gov.co/convocatoria-consejo-de-cuenca-pomca-del-rio-san-bartolo-codigo-szh-2310/"),
    nota="Escorrentía de 0.32 con IMERG (3 142 mm/año de lluvia): o IMERG sobreestima la lluvia o el caudal pierde agua. Solo 2 subcuencas, ambas limnimétricas."),
 "35017020": dict(corto="Meta", largo="Meta @ Puente Lleras",
    pomca=dict(estado="parc", etiqueta="Parcial (Guayuriba)",
               texto="La subcuenca del Guayuriba tiene POMCA adoptado (Res. CAR 3415 de 2019). Para el resto de la cuenca del Meta no lo verifiqué.",
               url="https://datosgeograficos.car.gov.co/datasets/15f2dbc999404c1ebc8fc5537b70927f_0/about"),
    nota="Solape con IMERG de solo 14.9 años. Tiene la bandera de cuerpos de agua (1.52 %, umbral 1.5 %): falta descartar regulación o trasvases. Sus 3 subcuencas válidas tienen entre 21 y 35 años y entre 5 y 10 % de faltantes."),
 "22057010": dict(corto="Saldaña", largo="Saldaña @ Piedras de Cobre",
    pomca=dict(estado="nc", etiqueta="Sin confirmar",
               texto="No confirmé un POMCA de toda la cuenca del Saldaña: solo aparecen POMCAs de subzonas y un estudio de evaluación regional de Cortolima.",
               url="https://cortolima.gov.co/sala-de-prensa/noticias/3289-era-el-estudio-que-evaluara-la-gran-cuenca-del-rio-saldana"),
    nota="Contiene una estación llamada «Bocatoma Triángulo» (posible captación, por verificar) y el aforo Gaitania del Atá, cuya fase con CHIRPS era ≈ 0. Con IMERG tiene fase 0.60 y CV 0.24: sin bandera, pero por debajo de Fonce (0.79 y 0.09)."),
 "24017570": dict(corto="Suárez", largo="Suárez @ San Benito",
    pomca=dict(estado="ok", etiqueta="Aprobado (2018)",
               texto="POMCA del Medio y Bajo Suárez aprobado por resolución conjunta CAR–CAS–Corpoboyacá (Res. 2110 de 2018); el del Alto Suárez fue aprobado por la CAR (Res. 1712 de 2018).",
               url="https://www.corpoboyaca.gov.co/importante/se-aprueba-el-pomca-del-rio-medio-y-bajo-suarez/"),
    nota="Hueco máximo de 365 días, exactamente el límite del filtro, y estación madre limnimétrica. Incluye la cuenca de la laguna de Fúquene: posible regulación por compuertas (por verificar)."),
 "26057040": dict(corto="Timba", largo="Timba @ Timba",
    pomca=dict(estado="nc", etiqueta="Sin confirmar",
               texto="La CVC y la CRC han hablado de la formulación del POMCA del Timba, pero no encontré fecha de aprobación.",
               url="https://cvc.gov.co/carousel/422-timba-2015"),
    nota="Sin subcuencas y solo 3 píxeles IMERG. Es de las mejores en registro y naturalidad, y lidera en el 18 % de los pesos aleatorios."),
 "21017040": dict(corto="Salado Blanco", largo="Magdalena @ Salado Blanco",
    pomca=dict(estado="parc", etiqueta="Parcial (Guarapas)",
               texto="Contiene la subcuenca del Guarapas, con POMCA adoptado por la CAM. Para el resto de la cuenca no lo confirmé.",
               url="https://www.cam.gov.co/prensa/blog/2023/03/22/huila-una-f%C3%A1brica-de-agua/"),
    nota="Fase con IMERG de 0.13 (bandera; 0.21 con CHIRPS): ninguno de los dos productos ve el pico de caudal de julio del Alto Magdalena. Si se quita la coherencia IMERG del puntaje, pasa a liderar el ranking."),
 "21017050": dict(corto="Guarapas", largo="Guarapas @ Pitalito 2",
    pomca=dict(estado="ok", etiqueta="Adoptado",
               texto="POMCA formulado en 2009, adoptado y con ajuste en marcha (CAM).",
               url="https://www.cam.gov.co/prensa/blog/2023/03/22/huila-una-f%C3%A1brica-de-agua/"),
    nota="La recomendación anterior. Cumple los filtros, pero tiene 2 píxeles IMERG, ninguna subcuenca y fase 0.52 con IMERG (0.88 con CHIRPS)."),
 "23147020": dict(corto="Opón", largo="Opón @ Puente Ferrocarril",
    pomca=dict(estado="ok", etiqueta="Aprobado",
               texto="POMCA del río Opón aprobado por la CAS; hoy formula el plan de ordenamiento del recurso hídrico.",
               url="https://www.redjurista.com/NewsPaper/47/ambiente/14284/plan-de-ordenacion-y-manejo-de-la-cuenca-hidrografica-del-rio-opon-fue-aprobado"),
    nota="Sin subcuencas y con una sola estación IDEAM dentro de la cuenca, no activa (análisis anterior): la lluvia no se puede contrastar con pluviómetros."),
 "51027060": dict(corto="Mira", largo="Mira @ San Juan",
    pomca=dict(estado="nc", etiqueta="No verificado",
               texto="No busqué el POMCA de esta cuenca.", url=""),
    nota="Q/P = 2.02 con IMERG (bandera RR_IMERG>1), físicamente imposible. Hipótesis: el río nace en Ecuador y el polígono, delineado con el DEM colombiano, no incluye toda el área aportante."),
 "35087020": dict(corto="Lengupá", largo="Lengupá @ Páez",
    pomca=dict(estado="nc", etiqueta="Sin confirmar",
               texto="No encontré un POMCA propio del Lengupá; sí está aprobado el del Garagoa, cuenca vecina.",
               url="https://www.corpoboyaca.gov.co/noticias/aprobado-el-pomca-rio-garagoa/"),
    nota="Queda fuera de las 134 por un hueco de 549 días (2011–2013). Aguas abajo, San Agustín da Q/P = 1.4 con IMERG, compatible con el agua que Chivor trasvasa al Lengupá; no verifiqué dónde queda la descarga respecto a Páez.",
    nota_url="https://informesdelaconstruccion.revistas.csic.es/index.php/informesdelaconstruccion/article/download/2671/2983/3424"),
}
COMPETIDORAS = [23107020, 35017020, 22057010, 24017570, 26057040,      # las 5 por defecto
                21017040, 21017050, 23147020, 51027060, 35087020]

# --------------------------------------------- lo que el codigo calcula pero NO usa como regla
NO_USADOS = [
 dict(id="temp", nombre="Temperatura observada", nota="El código calcula `t_miss` pero ningún filtro ni el puntaje lo usan; la temperatura se completará con ERA5.", col="t_miss"),
 dict(id="solape", nombre="Solape del caudal con IMERG", nota="Se calcula (`imerg_q_years`) y se muestra, pero solo entraba al puntaje preliminar de 13_preliminar.py, no al que decidió.", col="imerg_q_years"),
 dict(id="px", nombre="Píxeles IMERG dentro de la cuenca", nota="Se calcula y se muestra; solo entraba al puntaje preliminar (`imerg_px_aprox`), no al que decidió.", col="imerg_px"),
 dict(id="pomca", nombre="POMCA", nota="Investigación manual en las páginas de las corporaciones; no está en el código, no descarta y no puntúa.", col=None),
]
usadas = {c for m in R["metricas"] for c in m["columnas"] if (m["filtros"] or m["banderas"] or m["puntajes"])}
for n in NO_USADOS:
    assert n["col"] not in usadas, n

fs = pd.read_csv("out/fonce_subcuencas.csv").set_index("gauge_id")     # calculado por 14_fonce_subcuencas.py
fonce_extra = dict(merida_mayor_pct=f(fs.loc[24027070, "pct_Qsub_mayor"], 1), merida_frac=f(fs.loc[24027070, "frac_madre"], 2),
                   q_esp_monchia=f(fs.loc[24027060, "q_esp_mmd"], 2), q_esp_mogoticos=f(fs.loc[24027040, "q_esp_mmd"], 2))


# ------------------------------------------- lo que pidio el usuario (citas textuales)
# Las citas son sus propias palabras (solo se restauran acentos). La `traduccion` describe
# COMO se convirtio en regla, sin cifras: los numeros salen del codigo extraido.
PEDIDO_TEXTO = [
 dict(cuando="Tu primer mensaje", idioma="en",
      texto="find a basin in Colombia that is not too big and that we have good reliable data for … they should have hydrological and climatological data available in good resolution and shouldnt be too noisy."),
 dict(cuando="Tus criterios", idioma="es",
      texto="Debe haber mínimo 25 años de registros, preferiblemente más. Debe haber máximo un 10% de los datos diarios faltantes por variable, y no debe haber tramos muy largos sin datos. Adicionalmente, como un plus, sería bueno que hubiera datos de una o más subcuencas. Si no hay reporte de temperatura no hay problema, podemos usar ERA5, y el tamaño debe estar entre 100 y 10k km2. Y debe haber datos de precipitación IMERG para la cuenca. Además, si la cuenca es en Colombia, sería ideal que tenga POMCA. Puedes buscar en CAMELS-COL, pero si no hay ninguna de calidad suficientemente alta puedes decirme y vemos qué hacemos."),
 dict(cuando="Tu aclaración sobre píxeles", idioma="es",
      texto="el tamaño de la cuenca digamos que no es necesario que ocupe muchos píxeles de temperatura, no voy a hacer ningún análisis de la variación de temperatura en la cuenca todavía, solo necesito una serie de tiempo de la temperatura en promedio en toda el área de la cuenca y para eso sirve tener un solo píxel, especialmente en el caso de que usemos una cuenca con pocas o 0 subcuencas disponibles."),
]
PEDIDOS = {
 "area":   dict(cita="el tamaño debe estar entre 100 y 10k km2",
                traduccion="Se aplica tal cual, como filtro."),
 "anios":  dict(cita="Debe haber mínimo 25 años de registros, preferiblemente más.",
                traduccion="El mínimo se aplica como filtro. «Preferiblemente más» se tradujo en puntos: a más años, más puntaje."),
 "falt":   dict(cita="Debe haber máximo un 10% de los datos diarios faltantes por variable",
                traduccion="Se aplica como filtro al caudal, primero en los metadatos y luego medido en la serie diaria. Además, menos faltantes da más puntaje."),
 "falt_p": dict(cita="… faltantes por variable",
                traduccion="«Por variable»: se revisó también la precipitación. La temperatura no se filtra, porque dijiste que no hacía falta."),
 "hueco":  dict(cita="y no debe haber tramos muy largos sin datos.",
                traduccion="No diste cifra: el umbral que ves es una decisión mía y queda por confirmar. Menos hueco da más puntaje."),
 "sub":    dict(cita="como un plus, sería bueno que hubiera datos de una o más subcuencas.",
                traduccion="Es un plus: no descarta, suma puntos. «Una o más» se tradujo en una rampa de puntos que se satura (ver la regla)."),
 "cob":    dict(cita="Y debe haber datos de precipitación IMERG para la cuenca.",
                traduccion="Se comprueba como bandera de cobertura. IMERG además es la precipitación con la que se miden las pruebas de coherencia."),
 "pomca":  dict(cita="si la cuenca es en Colombia, sería ideal que tenga POMCA.",
                traduccion="Se revisó a mano en las páginas de las corporaciones. No está en el código: no descarta y no puntúa."),
 "temp":   dict(cita="Si no hay reporte de temperatura no hay problema, podemos usar ERA5",
                traduccion="Ninguna regla la usa: el código calcula `t_miss` pero no filtra ni puntúa con él."),
 "px":     dict(cita="no es necesario que ocupe muchos píxeles de temperatura … sirve tener un solo píxel",
                traduccion="Lo dijiste de la temperatura; lo apliqué también al conteo de píxeles IMERG: ninguna regla filtra por píxeles, solo se reporta."),
}
MOTIVO_AGREGADOS = dict(cita="they should have hydrological and climatological data available in good resolution and shouldnt be too noisy",
                        traduccion="No lo pediste como regla: lo agregué para medir «confiable» y «poco ruidoso».")

datos = dict(
    fonce=FONCE, fonce_extra=fonce_extra, pedidos=PEDIDOS, pedido_texto=PEDIDO_TEXTO, motivo_agregados=MOTIVO_AGREGADOS, criterios=CRITERIOS, componentes=COMPONENTES, embudo=embudo, solo=solo,
    reglas=dict(filtros=R["filtros"], sub_valida=R["sub_valida"], anidamiento=R["anidamiento"],
                banderas=R["banderas"], banderas_snip=R["banderas_snip"], puntaje_nz=R["puntaje"]["nz"],
                puntaje_score=R["puntaje"]["score"], ranking=R["puntaje"]["ranking"], preliminar=R["preliminar"]),
    verificacion=R["verificacion"], no_usados=NO_USADOS, cob_ok=cob_ok,
    basins=basins, robustez=rob, manual=MANUAL, competidoras=COMPETIDORAS, generado="2026-09-19",
)
Path("out/informe_datos.json").write_text(json.dumps(datos, ensure_ascii=False, allow_nan=False), encoding="utf-8")

pool_s = pool.sort_values("score", ascending=False).reset_index(drop=True)
print("OK  criterios:", [c["id"] for c in CRITERIOS])
print("OK  embudo:", [(e["paso"], e["n"]) for e in embudo], "| cobertura IMERG >= 98 %:", cob_ok, "de", len(a))
print("OK  fallas por filtro:", [(s["col"], s["falla"], "de", s["base"]) for s in solo])
print("OK  ranking:", [(int(r.gauge_id), round(float(r.score), 3)) for r in pool_s.head(5).itertuples()])
print("OK  robustez:", {k: rob["uniforme"][k] for k in ("p1", "p3", "mediana", "peor")})
print("OK  json KB:", round(len(json.dumps(datos, ensure_ascii=False)) / 1024))
