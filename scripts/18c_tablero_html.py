"""El tablero: un resumen de una página del informe, con sus cifras principales, los mecanismos y las conclusiones.

Corre scripts/18_calculos_informe.py, el mismo análisis del informe, y escribe reporte/tablero-fonce.html. No calcula
nada nuevo ni saca conclusiones propias: toma resultados que el informe ya muestra y los presenta resumidos. Toda cifra
sale de una variable del análisis; las frases que afirman algo sobre los datos van protegidas con un assert.

Es la excepción a la regla 22 que decidió el usuario el 2026-10-09 (DECISIONES.md): el informe sigue siendo uno solo y
el tablero no agrega contenido. Solo resume lo que ya está hecho; las secciones pendientes no aparecen.

Como el informe, el HTML es un solo archivo que abre sin internet: Plotly va dentro (reporte/vendor/). Los colores de
las variables y las referencias se leen de scripts/18b_reporte_html.py, donde está su única definición. Desde la raíz:

    python scripts/18c_tablero_html.py

Dentro de la f-string `pagina`, las llaves de CSS y de JavaScript van dobladas ({{ y }}).
"""
import ast, hashlib, html, json, re
from pathlib import Path
from runpy import run_path

SALIDA = Path("reporte/tablero-fonce.html")
SCRIPT_PAGINA = Path("scripts/18b_reporte_html.py")
VENTANA_COMUN = "común 1998–2022"           # las claves de las ventanas de Fourier, como las nombra 18_calculos
VENTANA_LARGA = "extendida 1981–2022"

# ---------------------------------------------------------------- lo que se toma de 18b, sin copiarlo
# 18b no se puede importar sin regenerar el informe entero, así que se lee su texto: el diccionario de colores (una
# asignación literal) y las referencias de la bibliografía que cita el tablero.
_fuente_18b = SCRIPT_PAGINA.read_text(encoding="utf-8")
COLOR_VAR = next(ast.literal_eval(nodo.value) for nodo in ast.parse(_fuente_18b).body
                 if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", None) == "COLOR_VAR")
REFERENCIAS = ["poveda2004", "mesa1997", "defensoria2005"]


def referencia(clave):
    """El <li> de la bibliografía de 18b, sin las marcas de revisión (expresiones de Python entre llaves)."""
    m = re.search(rf'<li id="ref-{clave}"[^>]*>(.*?)</li>', _fuente_18b, flags=re.S)
    assert m, f"la referencia {clave} no está en la bibliografía de {SCRIPT_PAGINA}"
    texto = re.sub(r"\s+", " ", m.group(1)).strip()
    assert "{" not in texto, f"la referencia {clave} tiene expresiones de Python: revisar"
    return f'<li id="ref-{clave}">{texto}</li>'


# Plotly, el mismo archivo y la misma comprobación que en 18b.
PLOTLY = Path("reporte/vendor/plotly-2.32.0.min.js")
PLOTLY_SHA256 = "0a17719a72751704861215da0e5c5cdb3f9a8d50eff5cb84cb6f8b80786682b0"
assert hashlib.sha256(PLOTLY.read_bytes()).hexdigest() == PLOTLY_SHA256, f"{PLOTLY} no es la versión registrada"
PLOTLY_JS = PLOTLY.read_text(encoding="utf-8")
assert "</script" not in PLOTLY_JS.lower()

# ---------------------------------------------------------------- el análisis
globals().update(run_path(str(Path(__file__).with_name("18_calculos_informe.py"))))


def n(x, dec=0):
    """Punto decimal y espacio para los miles (regla 14); el signo menos, con guion."""
    return f"{x:,.{dec}f}".replace(",", " ")


# ---------------------------------------------------------------- cifras del encabezado
comp = cmp_stats[NOM_RED]                    # PI contra PL, 1998–2022 (sección «Comparando PI con PL»)
meses_q = int(variables_resumen["Q"].notna().sum())
assert comp["sesgo"] < 0                     # el texto dice que PI queda por debajo de PL

# ---------------------------------------------------------------- régimen y clasificación
assert all(regimen[v]["clase"] == "bimodal" for v in ("PL", "PI", "Q"))      # «régimen bimodal» en las tres
assert clas_deficit_frecuente["pl"] == [1]   # «sin estación con déficit sostenido salvo enero» (con PL, que manda)
des_min, des_max = min(desfase["Q_PL"], desfase["Q_PI"]), max(desfase["Q_PL"], desfase["Q_PI"])
assert pe_indice["pl"]["clase"] == pe_indice["pi"]["clase"] == "húmedo"
clas_filas = "\n".join(
    f"<tr><td><b>{c['clase']}</b></td><td>{c['nombre']}</td>"
    f"<td class='num'>{n(c['mediana_pl'][0])}–{n(c['mediana_pl'][1])}</td>"
    f"<td class='num'>{c['pe']['pl'][0]:.2f}–{c['pe']['pl'][1]:.2f}</td><td class='num'>{c['pe']['pi'][0]:.2f}–{c['pe']['pi'][1]:.2f}</td>"
    f"<td class='num'>{c['deficit_max']['pl']} / {c['deficit_max']['pi']}</td><td>{c['q_nombre']}</td></tr>"
    for c in clas_tabla)

# ---------------------------------------------------------------- tendencias: la misma lectura de la tabla resumen de 18b
UNIDAD_DECADA = {"PL*": "mm/mes", "PI": "mm/mes", "Q": "m³/s", "T mín": "°C", "T media": "°C", "T máx": "°C"}
DEC_TEND = {"PL*": 1, "PI": 1, "Q": 2, "T mín": 2, "T media": 2, "T máx": 2}
tend = {}
for v in LARGO_VARS:
    f = met_global[(v, "completo")]
    x, z = f["ols_Xmes"], f["ols_z"]
    ols_sig, mk_sig = x["p_hac"] < TEND_ALFA, f["mk_X"]["p"] < TEND_ALFA
    if ols_sig and mk_sig:
        lectura = ("sube" if x["pend"] > 0 else "baja") + ", con los dos métodos"
    elif ols_sig or mk_sig:
        lectura = "señal débil: un solo método"
    else:
        lectura = "sin tendencia"
    tend[v] = {"periodo": f"{f['inicio'].year}–{f['fin'].year}", "x": x["pend"], "ic": x["ic_hac"],
               "z": z["pend"], "ic_z": z["ic_hac"], "lectura": lectura}
# el título dice «sube la temperatura, no la lluvia ni el caudal»
assert all(tend[v]["lectura"] == "sube, con los dos métodos" for v in LARGO_VARS if v.startswith("T"))
assert all(tend[v]["lectura"] == "sin tendencia" for v in ("PL*", "PI", "Q"))
tend_filas = "\n".join(
    f"<tr><td><b>{v}</b></td><td>{t['periodo']}</td>"
    f"<td class='num'>{t['x']:+.{DEC_TEND[v]}f} ± {t['ic']:.{DEC_TEND[v]}f}</td><td>{UNIDAD_DECADA[v]} por década</td>"
    f"<td><span class='pastilla{' sube' if t['lectura'].startswith('sube') else ''}'>{t['lectura']}</span></td></tr>"
    for v, t in tend.items())
tend_json = json.dumps([{"v": v, "z": round(t["z"], 3), "ic": round(t["ic_z"], 3), "periodo": t["periodo"]}
                        for v, t in tend.items()], ensure_ascii=False)
# marzo: la única subserie de la lluvia que resiste la FDR; el caudal de marzo y el de abril, sin tendencia
_q_abril = met_mes[("Q", 4)]
assert fis_marzo["q_mes"]["p"] >= TEND_ALFA and _q_abril["p"] >= TEND_ALFA

# ---------------------------------------------------------------- frecuencias
_bandas = {v: fou[(VENTANA_COMUN, v, "original")]["bandas"] for v in ("PL", "PI", "Q", "T")}
# «domina el pico de 6 meses»: en la lluvia y el caudal, la semianual es la mayor de las cuatro bandas
assert all(_bandas[v]["semianual"] == max(_bandas[v].values()) for v in ("PL", "PI", "Q"))
assert fou_alta_q < fou_alta_lluvia and fou_phi["Q"] > max(fou_phi["PL"], fou_phi["PI"])     # «la cuenca filtra»
_coh_pl, _coh_q = fou_coh[(VENTANA_LARGA, "PL*", "ONI")], fou_coh[(VENTANA_LARGA, "Q", "ONI")]
assert _coh_pl["signif"] and _coh_q["signif"] and _coh_pl["lectura"] == _coh_q["lectura"] == "en oposición"
fou_json = json.dumps({v: {b: round(p, 1) for b, p in _bandas[v].items()} for v in _bandas}, ensure_ascii=False)
ciclos_semianual = fou[(VENTANA_COMUN, "PL", "original")]["ciclos"]

# ---------------------------------------------------------------- de la lluvia al caudal
_val = {k: t["validacion"] for k, t in ev_tabla.items()}
assert ev_mejor == "PL del mismo mes"
assert _val["PL del mismo mes"]["rmse"] < ev_rmse_clima and _val["PI del mismo mes"]["rmse"] < ev_rmse_clima
assert all(_val[f"{f} del mes anterior"]["rmse"] > _val[f"{f} del mismo mes"]["rmse"] for f in ("PL", "PI"))
ev_json = json.dumps([{"e": k, "rmse": round(v["rmse"], 1), "n": int(v["n"])} for k, v in _val.items()], ensure_ascii=False)
rho_pl_q, rho_pi_q = float(corr_spearman_anom.loc["PL", "Q"]), float(corr_spearman_anom.loc["PI", "Q"])

# ---------------------------------------------------------------- mecanismos
assert frac_sobre_optimo > 0.5               # «casi toda la cuenca queda en la rama descendente»
assert fis_ciclo_rango["etp"]["pct"] < fis_ciclo_rango["pl"]["pct"]   # «la energía casi no cambia en el año»

ciclo_json = json.dumps({"meses": ciclo_datos["meses"], "PL": ciclo_datos["red"], "PI": ciclo_datos["imerg"],
                         "Q": ciclo_datos["caudal"]}, ensure_ascii=False)
pe_json = json.dumps({"meses": MESES_ES, "PL": [round(float(x), 2) for x in pe_mes["pl"]],
                      "PI": [round(float(x), 2) for x in pe_mes["pi"]]}, ensure_ascii=False)
color_json = json.dumps(COLOR_VAR, ensure_ascii=False)
refs_html = "\n".join(referencia(c) for c in REFERENCIAS)
CITA = {c: f'<a class="cita" href="#ref-{c}">{t}</a>' for c, t in
        [("poveda2004", "Poveda, 2004"), ("mesa1997", "Mesa et al., 1997"), ("defensoria2005", "Defensoría del Pueblo, 2005")]}

# ======================================================================================================
pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tablero del Fonce</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Los mismos tonos y tipografías del informe. Rejilla de tarjetas: el resumen arriba, el detalle debajo. */
:root {{
  --fondo: #F5F7F6; --superficie: #FFFFFF; --tinta: #17211E; --tenue: #56645F; --linea: #D5DDDA;
  --acento: #1B6A80; --sube: #B8321F; --referencia: #8A9893;
  --f-titulo: "Archivo", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --f-texto: "Source Serif 4", Georgia, "Times New Roman", serif;
  --f-dato: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
    --acento: #72B9CE; --sube: #F2836B; --referencia: #6E7C77; color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
  --acento: #72B9CE; --sube: #F2836B; --referencia: #6E7C77; color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--fondo); color: var(--tinta); font-family: var(--f-texto); font-size: 17px; line-height: 1.55; }}
.envoltura {{ max-width: 76rem; margin-inline: auto; padding-inline: 16px; padding-block: 28px 56px;
  display: flex; flex-direction: column; gap: 36px; font-variant-numeric: tabular-nums; }}
h1, h2, h3 {{ font-family: var(--f-titulo); font-stretch: 85%; margin: 0; text-wrap: balance; line-height: 1.15; }}
h1 {{ font-size: clamp(1.9rem, 4vw, 2.7rem); font-weight: 700; }}
h2 {{ font-size: 1.35rem; font-weight: 700; }}
h3 {{ font-size: 1.02rem; font-weight: 600; }}
p {{ margin: 0; max-width: 70ch; }}
.cab {{ display: flex; flex-direction: column; gap: 10px; }}
.sub, .nota, .fuente {{ font-family: var(--f-titulo); color: var(--tenue); font-size: .88rem; line-height: 1.45; }}
.lema {{ font-size: 1.12rem; max-width: 74ch; }}
.seccion {{ display: flex; flex-direction: column; gap: 14px; }}
.rejilla {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr)); }}
.tarjeta {{ background: var(--superficie); border: 1px solid var(--linea); border-radius: 8px; padding: 18px;
  display: flex; flex-direction: column; gap: 10px; min-width: 0; }}
.cifras {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 11rem), 1fr)); }}
.cifra {{ background: var(--superficie); border: 1px solid var(--linea); border-radius: 8px; padding: 12px 16px;
  display: flex; flex-direction: column; gap: 4px; }}
.cifra .et {{ font-family: var(--f-titulo); font-size: .82rem; color: var(--tenue); letter-spacing: .02em; }}
.cifra .gr {{ font-family: var(--f-dato); font-size: 1.6rem; font-weight: 500; line-height: 1.15; }}
.cifra .gr small {{ font-family: var(--f-titulo); font-size: .8rem; color: var(--tenue); margin-left: .3em; font-weight: 400; }}
.grafico {{ min-height: 280px; width: 100%; }}
.tabla {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-family: var(--f-titulo); font-size: .88rem; }}
th, td {{ text-align: left; padding: .45em .6em; border-bottom: 1px solid var(--linea); vertical-align: top; }}
th {{ color: var(--tenue); font-weight: 600; }}
td.num, th.num {{ text-align: right; white-space: nowrap; font-family: var(--f-dato); font-size: .84rem; }}
.pastilla {{ display: inline-block; padding: .05em .55em; border-radius: 999px; border: 1px solid var(--linea);
  color: var(--tenue); }}
.pastilla.sube {{ color: var(--sube); border-color: currentColor; }}
.mec {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); }}
ul {{ margin: 0; padding-left: 1.2em; display: flex; flex-direction: column; gap: 8px; max-width: 74ch; }}
.pl {{ color: {COLOR_VAR["PL"]}; }} .pi {{ color: {COLOR_VAR["PI"]}; }} .q {{ color: {COLOR_VAR["Q"]}; }}
a {{ color: var(--acento); }}
a.cita {{ text-decoration: none; border-bottom: 1px dotted currentColor; }}
.refs li {{ font-size: .92rem; }}
a:focus-visible {{ outline: 2px solid var(--acento); outline-offset: 2px; }}
</style>
</head>
<body>
<div class="envoltura">
  <header class="cab">
    <h1>Cuenca del río Fonce hasta San Gil</h1>
    <p class="sub">Estación de aforo IDEAM 24027010 · Santander, Colombia · resumen de <a href="reporte-fonce.html">reporte-fonce.html</a>.
      Comparaciones en {PERIODOS[0].year}–{PERIODOS[-1].year}; tendencias con el registro desde {LARGO_DESDE[:4]} cuando existe.</p>
    <p class="lema">Clima <b>{pe_indice["pl"]["clase"]}</b> (P/ETP de {pe_indice["pl"]["ie"]:.2f} con PL y {pe_indice["pi"]["ie"]:.2f} con PI),
      con <b>régimen bimodal</b> por el doble paso de la ZCIT, sin estación con déficit de agua sostenido salvo enero, y un río
      que responde con {des_min:.0f} a {des_max:.0f} días de atraso por el almacenamiento.</p>
    <p class="nota"><b class="pi">PI</b>: precipitación de IMERG (satélite), promediada sobre la cuenca ponderando cada celda por su área.
      <b class="pl">PL</b>: promedio de los {len(DENTRO)} pluviómetros del IDEAM dentro de la divisoria, con los tramos dudosos excluidos.
      <b class="q">Q</b>: caudal en San Gil. Todo análisis de lluvia se hace con las dos fuentes; cuando hay que escoger, manda PL.</p>
  </header>

  <section class="cifras" aria-label="Cifras principales">
    <div class="cifra"><span class="et">Área de drenaje (polígono, geodésica)</span><span class="gr">{n(AREA_SG_KM2, 2)}<small>km²</small></span></div>
    <div class="cifra"><span class="et">Lluvia media, PL</span><span class="gr pl">{comp["pluv"]:.1f}<small>mm/mes</small></span></div>
    <div class="cifra"><span class="et">Lluvia media, PI</span><span class="gr pi">{comp["imerg"]:.1f}<small>mm/mes</small></span></div>
    <div class="cifra"><span class="et">PI respecto a PL</span><span class="gr">{comp["sesgo"]:.1f}<small>%</small></span></div>
    <div class="cifra"><span class="et">Coeficiente de escorrentía, PL / PI</span><span class="gr">{fis_coef["pl"]:.2f}<small>/</small>{fis_coef["pi"]:.2f}</span></div>
    <div class="cifra"><span class="et">Meses con Q válido</span><span class="gr q">{meses_q}<small>de {len(PERIODOS)}</small></span></div>
  </section>
  <p class="nota">Las dos fuentes cuentan la misma historia con distinta magnitud: correlación mes a mes de {comp["r"]:.2f}
    (Pearson, {PERIODOS[0].year}–{PERIODOS[-1].year}). No hay forma de arbitrar cuál tiene la razón: el satélite estima indirectamente
    sobre celdas grandes y los pluviómetros miden en puntos. Por eso no se corrige PI y se llevan las dos.</p>

  <section class="seccion">
    <h2>El año típico: dos temporadas de lluvia</h2>
    <div class="rejilla">
      <div class="tarjeta">
        <h3>Ciclo anual medio de la lluvia y del caudal</h3>
        <p class="nota">mm/mes; Q pasado a lámina dividiéndolo por el área. Promedios sobre los {ciclo_n} meses en que PL, PI y Q tienen dato.</p>
        <div class="grafico" id="g-ciclo"></div>
      </div>
      <div class="tarjeta">
        <h3>La lluvia contra la ETP, mes a mes</h3>
        <p class="nota">P/ETP con la ETP de Hargreaves calculada con ERA5-Land, {PERIODOS[0].year}–{PERIODOS[-1].year}. Bajo la línea punteada
          (P = ETP) llueve menos de lo que la atmósfera podría evaporar.</p>
        <div class="grafico" id="g-pe"></div>
      </div>
    </div>
    <div class="tarjeta">
      <h3>Clasificación hidroclimática mensual</h3>
      <p class="nota">Húmedo: mes de temporada húmeda con P/ETP ≥ {CLAS_PE_HUMEDO:.1f} y sin déficit en ningún año. Seco: la temporada que
        contiene el mes de menos lluvia. Seco relativo: la otra. Años con déficit: el mayor número de años con P &lt; ETP entre los meses de
        la clase, de {pe_n_anios}.</p>
      <div class="tabla"><table>
        <thead><tr><th>Clase</th><th>Meses (PL)</th><th class="num">Mediana de PL (mm/mes)</th><th class="num">P/ETP con PL</th>
          <th class="num">P/ETP con PI</th><th class="num">Años con déficit (PL / PI)</th><th>Caudal sobre o bajo su mes típico</th></tr></thead>
        <tbody>
{clas_filas}
        </tbody></table></div>
    </div>
  </section>

  <section class="seccion">
    <h2>Tendencias de largo plazo: sube la temperatura, no la lluvia ni el caudal</h2>
    <div class="rejilla">
      <div class="tarjeta">
        <h3>Pendiente por década, en unidades estandarizadas</h3>
        <p class="nota">z por década ± intervalo de 95 % (mínimos cuadrados con una constante por mes y error de Newey-West), en el registro
          completo de cada variable. Si la barra cruza el cero, no se puede descartar que no haya tendencia.</p>
        <div class="grafico" id="g-tend"></div>
      </div>
      <div class="tarjeta">
        <h3>En las unidades de cada variable</h3>
        <p class="nota">«Con los dos métodos»: significativa con la recta (Newey-West) y con Mann-Kendall estacional (p &lt; {TEND_ALFA}).
          En la lluvia es el cambio del acumulado mensual, no del total anual.</p>
        <div class="tabla"><table>
          <thead><tr><th>Variable</th><th>Período</th><th class="num">Pendiente ± IC 95 %</th><th>Unidad</th><th>Lectura</th></tr></thead>
          <tbody>
{tend_filas}
          </tbody></table></div>
      </div>
    </div>
    <p class="nota">PL* es la red fija de pluviómetros desde {LARGO_DESDE[:4]}. PI empieza en {PERIODOS[0].year} y no se extiende. La única
      subserie mensual de la lluvia que resiste la corrección por pruebas múltiples (FDR) es marzo con PL*: {fis_marzo["pend"]:+.0f} mm/mes
      por década, sin una tendencia significativa del caudal de marzo ({fis_marzo["q_mes"]["ols"]:+.1f} m³/s por década,
      p = {fis_marzo["q_mes"]["p"]:.3f}) ni del de abril ({_q_abril["ols"]:+.1f} m³/s por década, p = {_q_abril["p"]:.3f}).</p>
  </section>

  <section class="seccion">
    <h2>Escalas de variabilidad: domina el pico de 6 meses</h2>
    <div class="rejilla">
      <div class="tarjeta">
        <h3>Parte de la varianza en cada banda de frecuencia</h3>
        <p class="nota">Series originales, {PERIODOS[0].year}–{PERIODOS[-1].year}. Anual y semianual: ±Δf alrededor de 12 y 6 meses; interanual:
          {FOU_INTERANUAL[0] / 12:.0f} a {FOU_INTERANUAL[1] / 12:.0f} años; alta: períodos menores que {FOU_ALTA_MAX:.0f} meses. Las bandas no
          suman 100 %: queda varianza fuera de ellas.</p>
        <div class="grafico" id="g-four"></div>
      </div>
      <div class="tarjeta">
        <h3>Lo que dicen las frecuencias</h3>
        <ul>
          <li><b>El pico de 6 meses es la señal más fuerte.</b> Tiene el {_bandas["PL"]["semianual"]:.1f} % de la varianza de PL, el
            {_bandas["PI"]["semianual"]:.1f} % de la de PI y el {_bandas["Q"]["semianual"]:.1f} % de la del caudal, y cabe
            {ciclos_semianual:.0f} veces en el registro.</li>
          <li><b>La cuenca funciona como un filtro.</b> En las anomalías, la alta frecuencia es el {fou_alta_lluvia:.0f} % de la varianza
            de la lluvia y solo el {fou_alta_q:.0f} % de la del caudal. La autocorrelación de un mes es {fou_phi["Q"]:.2f} en Q, contra
            {min(fou_phi["PL"], fou_phi["PI"]):.2f}–{max(fou_phi["PL"], fou_phi["PI"]):.2f} en la lluvia.</li>
          <li><b>La variabilidad interanual sigue al ENSO, sin período fijo.</b> En el registro desde {LARGO_DESDE[:4]}, la lluvia y el
            caudal varían en oposición con el ONI (coherencia PL*–ONI {_coh_pl["coh"]:.2f} y Q–ONI {_coh_q["coh"]:.2f}, ambas
            significativas): menos agua en El Niño. El ONI tiene su pico en unos {fou_oni_pico_ext:.0f} meses; es una banda de
            {FOU_INTERANUAL[0] / 12:.0f} a {FOU_INTERANUAL[1] / 12:.0f} años, no una periodicidad.</li>
        </ul>
      </div>
    </div>
  </section>

  <section class="seccion">
    <h2>¿Sirve la lluvia para estimar el caudal?</h2>
    <div class="rejilla">
      <div class="tarjeta">
        <h3>Error al estimar Q en años que el ajuste no vio</h3>
        <p class="nota">RMSE en m³/s. Recta ajustada con {EV_AJUSTE[0][:4]}–{EV_AJUSTE[1][:4]} y evaluada con {EV_VALIDACION[0][:4]}–{EV_VALIDACION[1][:4]}.
          La referencia, en gris, es la climatología: el caudal medio de cada mes en el ajuste. Una barra más corta que la gris quiere
          decir que la lluvia dice algo que el calendario solo no dice.</p>
        <div class="grafico" id="g-rmse"></div>
      </div>
      <div class="tarjeta">
        <h3>Las relaciones, sin el ciclo anual</h3>
        <ul>
          <li>Correlación de Spearman entre la lluvia y el caudal en anomalías: <b class="pl">{rho_pl_q:.2f}</b> con PL y
            <b class="pi">{rho_pi_q:.2f}</b> con PI.</li>
          <li>La lluvia del mes anterior agrega información: correlación parcial de {memoria.loc["PL", "parcial_mes_anterior"]:.2f}
            con PL y {memoria.loc["PI", "parcial_mes_anterior"]:.2f} con PI.</li>
          <li>Pero sola, la lluvia del mes anterior estima peor que la del mismo mes: el río responde sobre todo dentro del mismo mes.</li>
          <li>Una recta mensual simplifica mucho: no representa el agua guardada en el suelo ni el tránsito por el cauce. Además, IMERG
            incorpora datos de pluviómetros, así que PI y PL no son del todo independientes.</li>
        </ul>
      </div>
    </div>
  </section>

  <section class="seccion">
    <h2>Mecanismos físicos</h2>
    <div class="mec">
      <div class="tarjeta">
        <h3>Doble paso de la ZCIT</h3>
        <p>La Zona de Convergencia Intertropical migra de norte a sur a lo largo del año y pasa dos veces sobre el centro del país. Da las
          dos temporadas lluviosas, abril–mayo y octubre–noviembre, que la cuenca reproduce en PL, PI y Q.</p>
        <p class="fuente">{CITA["poveda2004"]}; {CITA["mesa1997"]}. Evidencia: régimen bimodal (Kruskal-Wallis) y pico de 6 meses en Fourier.</p>
      </div>
      <div class="tarjeta">
        <h3>Óptimo pluviográfico: llueve menos arriba</h3>
        <p>La lluvia crece con la altura hasta una franja que normalmente no pasa de {n(ALTURA_OPTIMO_M)} m, y por encima disminuye. El
          Fonce va de {n(elev_min)} a {n(elev_max)} m, y el {frac_sobre_optimo * 100:.0f} % de su área está por encima: casi toda la cuenca
          queda en la rama descendente. IMERG pierde unos {n(grad_caida)} mm/año de sus celdas más bajas a las más altas.</p>
        <p class="fuente">{CITA["mesa1997"]}, p. 90. Evidencia: curva hipsométrica del proyecto y lluvia de IMERG contra la altura.</p>
      </div>
      <div class="tarjeta">
        <h3>Almacenamiento: la cuenca amortigua la lluvia</h3>
        <p>El río va {des_min:.0f} a {des_max:.0f} días detrás de la lluvia en el ciclo anual, conserva más memoria de un mes al siguiente
          que la lluvia y atenúa la alta frecuencia. Es el agua guardada en el suelo y el acuífero.</p>
        <p class="fuente">Evidencia: desfase del armónico de 6 meses, correlación cruzada y espectros de las anomalías.</p>
      </div>
      <div class="tarjeta">
        <h3>ENSO: menos agua en El Niño</h3>
        <p>En la escala de {FOU_INTERANUAL[0] / 12:.0f} a {FOU_INTERANUAL[1] / 12:.0f} años, la lluvia y el caudal varían en oposición
          con el ONI, la anomalía de la temperatura del mar en el Pacífico central.</p>
        <p class="fuente">Evidencia: coherencia y fase con el ONI en el registro desde {LARGO_DESDE[:4]}; correlación de la cuenca con la
          región Niño 3.4.</p>
      </div>
      <div class="tarjeta">
        <h3>La energía casi no cambia en el año</h3>
        <p>La ETP de Hargreaves varía un {fis_ciclo_rango["etp"]["pct"]:.0f} % de su media entre meses; la lluvia, un
          {fis_ciclo_rango["pl"]["pct"]:.0f} % con PL. El ciclo del caudal lo manda la lluvia, no la evaporación.</p>
        <p class="fuente">Evidencia: ETP del proyecto con ERA5-Land.</p>
      </div>
      <div class="tarjeta">
        <h3>Frentes fríos: episodios, no clima</h3>
        <p>En enero y febrero de 2005 hubo una emergencia invernal en Santander que el IDEAM atribuyó a cuatro frentes fríos del
          hemisferio norte. El documento no nombra la cuenca del Fonce: es un episodio de un bimestre, no un rasgo de su clima.</p>
        <p class="fuente">{CITA["defensoria2005"]}, que cita al IDEAM.</p>
      </div>
    </div>
  </section>

  <section class="seccion">
    <h2>Hipótesis y conclusiones</h2>
    <div class="rejilla">
      <div class="tarjeta">
        <h3>Hipótesis de trabajo</h3>
        <p><b>H:</b> el caudal de San Gil lo controla la lluvia sobre la cuenca, amortiguada por un almacenamiento del orden de un mes. La
          evapotranspiración, casi constante en el año, no explica ni su ciclo ni sus diferencias entre años.</p>
        <ul>
          <li><b>Lo que la apoya:</b> la lluvia explica el caudal aun sin el ciclo anual, y la lluvia del mes supera a la climatología al
            estimar Q en años no vistos.</li>
          <li><b>Lo que queda abierto:</b> la lluvia de marzo sube, pero el caudal de marzo y el de abril no muestran tendencia
            significativa. O la señal es pequeña frente a la variabilidad del caudal, o el almacenamiento la diluye.</li>
          <li><b>Coherente, pero no la prueba:</b> el calentamiento ({fis_t_decada:+.2f} °C por década) sube la ETP solo un
            {inc_etp["rel_pct"]:.2f} % por década, y Q no tiene tendencia.</li>
          <li><b>Qué la refutaría:</b> tendencias o diferencias de caudal entre años sin un cambio de lluvia que las acompañe, o residuos
            de las estimaciones de Q que conservaran estacionalidad.</li>
        </ul>
      </div>
      <div class="tarjeta">
        <h3>Lo que muestra el informe</h3>
        <ul>
          <li>Cuenca <b>húmeda y bimodal</b>: dos temporadas de lluvia por el doble paso de la ZCIT, sin estación con déficit de agua
            sostenido salvo enero.</li>
          <li>La variabilidad se concentra en <b>la escala semianual, que domina, y la interanual</b>, débil pero ligada al ENSO.</li>
          <li><b>La temperatura sube</b> con los dos métodos; la lluvia y el caudal no muestran tendencia en el registro completo.</li>
          <li>La mejor estimación del caudal sale de <b>PL del mismo mes</b>.</li>
          <li>PI queda por debajo de PL y <b>no se puede arbitrar cuál tiene la razón</b>: la incertidumbre se arrastra con las dos fuentes
            hasta el final.</li>
        </ul>
      </div>
    </div>
  </section>

  <section class="seccion">
    <h2>Referencias</h2>
    <ul class="refs">
{refs_html}
    </ul>
  </section>
</div>

<script>{PLOTLY_JS}</script>
<script>
const COLOR_VAR = {color_json};
const CICLO = {ciclo_json};
const PE = {pe_json};
const TEND = {tend_json};
const FOU = {fou_json};
const EV = {ev_json};

const css = nombre => getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
// punto decimal y espacio para los miles (regla 14)
const fmt = (v, dec) => v.toFixed(dec).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, " ");

function base(extra) {{
  const tinta = css("--tinta"), tenue = css("--tenue"), linea = css("--linea");
  return Object.assign({{
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", separators: ". ",
    font: {{ family: css("--f-titulo"), color: tinta, size: 13 }},
    margin: {{ l: 48, r: 14, t: 10, b: 40 }},
    legend: {{ orientation: "h", y: 1.12, x: 0, font: {{ color: tenue }} }},
    xaxis: {{ gridcolor: linea, linecolor: linea, tickfont: {{ color: tenue }}, zeroline: false }},
    yaxis: {{ gridcolor: linea, linecolor: linea, tickfont: {{ color: tenue }}, zeroline: false }},
    hoverlabel: {{ font: {{ family: css("--f-titulo") }} }},
  }}, extra);
}}
const CONF = {{ displayModeBar: false, responsive: true }};
const colorDe = v => v.startsWith("T") ? COLOR_VAR["T media"] : COLOR_VAR[v];

function dibujarCiclo() {{
  const trazas = ["PL", "PI", "Q"].map(k => ({{
    x: CICLO.meses, y: CICLO[k], name: k, type: "scatter", mode: "lines+markers",
    line: {{ color: COLOR_VAR[k], width: 2.5 }}, marker: {{ size: 6 }},
    hovertemplate: `${{k}}: %{{y:.1f}} mm/mes<extra></extra>`,
  }}));
  Plotly.react("g-ciclo", trazas, base({{ yaxis: Object.assign(base().yaxis, {{ title: "mm/mes", rangemode: "tozero" }}), hovermode: "x unified" }}), CONF);
}}

function dibujarPE() {{
  const trazas = ["PL", "PI"].map(k => ({{
    x: PE.meses, y: PE[k], name: `${{k}} / ETP`, type: "bar", marker: {{ color: COLOR_VAR[k] }},
    hovertemplate: `${{k}}/ETP: %{{y:.2f}}<extra></extra>`,
  }}));
  // P = ETP: la referencia fija del índice, no un dato
  const lay = base({{ barmode: "group", hovermode: "x unified",
    shapes: [{{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 1, y1: 1, line: {{ color: css("--referencia"), dash: "dash", width: 1.5 }} }}],
    yaxis: Object.assign(base().yaxis, {{ title: "P / ETP", rangemode: "tozero" }}) }});
  Plotly.react("g-pe", trazas, lay, CONF);
}}

function dibujarTend() {{
  const filas = TEND.slice().reverse();
  const traza = {{
    type: "scatter", mode: "markers", y: filas.map(f => f.v), x: filas.map(f => f.z),
    error_x: {{ type: "data", array: filas.map(f => f.ic), thickness: 3, width: 0, color: css("--tenue") }},
    marker: {{ size: 11, color: filas.map(f => colorDe(f.v)) }},
    customdata: filas.map(f => [f.ic, f.periodo]),
    hovertemplate: "%{{y}} (%{{customdata[1]}}): %{{x:+.2f}} ± %{{customdata[0]:.2f}} z por década<extra></extra>", showlegend: false,
  }};
  const lay = base({{ margin: {{ l: 70, r: 14, t: 10, b: 40 }},
    shapes: [{{ type: "line", yref: "paper", y0: 0, y1: 1, x0: 0, x1: 0, line: {{ color: css("--referencia"), width: 1.5 }} }}],
    xaxis: Object.assign(base().xaxis, {{ title: "z por década" }}) }});
  Plotly.react("g-tend", [traza], lay, CONF);
}}

function dibujarFour() {{
  const bandas = [["anual", "Anual"], ["semianual", "Semianual"], ["interanual", "Interanual"], ["alta", "Alta"]];
  const nombres = {{ PL: "PL", PI: "PI", Q: "Q", T: "T media" }};
  const trazas = Object.keys(FOU).map(v => ({{
    x: bandas.map(b => b[1]), y: bandas.map(b => FOU[v][b[0]]), name: nombres[v], type: "bar",
    marker: {{ color: COLOR_VAR[nombres[v]] }}, hovertemplate: `${{nombres[v]}}: %{{y:.1f}} %<extra></extra>`,
  }}));
  Plotly.react("g-four", trazas, base({{ barmode: "group", hovermode: "x unified",
    yaxis: Object.assign(base().yaxis, {{ title: "% de la varianza", rangemode: "tozero" }}) }}), CONF);
}}

function dibujarRMSE() {{
  const filas = EV.slice().reverse();
  const traza = {{
    type: "bar", orientation: "h", y: filas.map(f => f.e), x: filas.map(f => f.rmse),
    marker: {{ color: filas.map(f => f.e.startsWith("PL") ? COLOR_VAR.PL : f.e.startsWith("PI") ? COLOR_VAR.PI : css("--referencia")) }},
    text: filas.map(f => fmt(f.rmse, 1)), textposition: "outside", cliponaxis: false,
    customdata: filas.map(f => f.n),
    hovertemplate: "%{{y}}: RMSE %{{x:.1f}} m³/s (%{{customdata}} meses evaluados)<extra></extra>", showlegend: false,
  }};
  Plotly.react("g-rmse", [traza], base({{ margin: {{ l: 190, r: 40, t: 10, b: 40 }},
    xaxis: Object.assign(base().xaxis, {{ title: "RMSE en la evaluación (m³/s)", rangemode: "tozero" }}) }}), CONF);
}}

function dibujar() {{ dibujarCiclo(); dibujarPE(); dibujarTend(); dibujarFour(); dibujarRMSE(); }}
dibujar();
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dibujar);
new MutationObserver(dibujar).observe(document.documentElement, {{ attributes: true, attributeFilter: ["data-theme"] }});
</script>
</body>
</html>
"""

SALIDA.write_text(pagina, encoding="utf-8")
print(f"{SALIDA}: {SALIDA.stat().st_size / 1e6:.1f} MB")
