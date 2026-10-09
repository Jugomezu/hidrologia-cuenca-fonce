"""La página del informe: corre el análisis y escribe reporte/reporte-fonce.html.

Primero corre scripts/18_calculos_informe.py, que calcula todas las cifras, tablas y series; después arma el
HTML con la f-string `pagina` (texto, CSS y el JavaScript de las gráficas) y lo escribe. Las figuras van
incrustadas en base64 y Plotly va dentro del archivo (reporte/vendor/), así que el HTML es uno solo y abre
sin internet; solo las tipografías vienen de Google Fonts, y sin conexión se usan las de reemplazo.

El HTML no se edita a mano: se editan este script y el de cálculos, y se regenera. Desde la raíz:

    python scripts/18b_reporte_html.py

Dentro de la f-string, las llaves de CSS y de JavaScript van dobladas ({{ y }}); las sencillas son
expresiones de Python.
"""
import base64, hashlib, html, json
from pathlib import Path
from runpy import run_path
import pandas as pd

FIG = Path("reporte/figuras")
SALIDA = Path("reporte/reporte-fonce.html")

# Autoría del informe: se escribe en el encabezado de la página y en los metadatos del HTML.
AUTORES = ["Juan Pablo Gomez", "Andrea Gomez", "Diego Cantillo"]
PROFESOR = "Carlos David Hoyos"

# Uso de IA (política del curso): herramientas con su versión cuando se conoce. La versión de Claude Code es la de la
# sesión en que se escribió esta sección; la de sesiones anteriores no quedó registrada.
IA_HERRAMIENTAS = [
    ("Claude Code (Anthropic)", "2.1.293, el 2026-10-09",
     "asistente de programación que lee y edita el repositorio y corre los scripts, desde la terminal y VS Code"),
    ("Claude Opus 5.5 (claude-opus-5-5)", "modelo de lenguaje",
     "el modelo principal; figura como coautor en los commits del repositorio («Co-Authored-By»)"),
    ("Claude Sonnet 5.5 (claude-sonnet-5-5)", "modelo de lenguaje",
     "tareas delegadas a subagentes, como el dibujo de figuras y el encabezado de autores de esta página"),
]
# Las propuestas de la IA que el equipo rechazó o corrigió salen del registro de decisiones: las filas marcadas
# «Contradice al agente». Así el anexo no se escribe a mano y crece con el registro.
DECISIONES = Path("DECISIONES.md")


def _md_en_linea(texto):
    """Markdown mínimo de una celda del registro: **negrita** y `código`, con el resto escapado."""
    t = html.escape(texto.strip())
    partes = t.split("**")
    t = "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(partes))
    partes = t.split("`")
    return "".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(partes))


ia_rechazos = []
for _linea in DECISIONES.read_text(encoding="utf-8").splitlines():
    _celdas = [c.strip() for c in _linea.strip().strip("|").split("|")]
    if len(_celdas) == 5 and "Contradice al agente" in _celdas[4]:
        ia_rechazos.append(_celdas)
assert ia_rechazos, "el registro de decisiones no tiene propuestas rechazadas: revisar el anexo de uso de IA"
ia_filas_rechazos = "\n".join(
    "<tr>" + "".join(f"<td>{_md_en_linea(c)}</td>" for c in fila) + "</tr>" for fila in ia_rechazos)
ia_filas_herramientas = "\n".join(
    f"<tr><td><b>{html.escape(h)}</b></td><td>{html.escape(v)}</td><td>{html.escape(u)}</td></tr>"
    for h, v, u in IA_HERRAMIENTAS)
# cuántas comprobaciones automáticas tiene el análisis (líneas assert de los dos scripts)
ia_n_assert = sum(
    sum(1 for l in Path(f"scripts/{s}").read_text(encoding="utf-8").splitlines() if l.strip().startswith("assert"))
    for s in ("18_calculos_informe.py", "18b_reporte_html.py"))

# Corre el análisis y trae sus resultados a este archivo, para que la f-string de la página los use.
globals().update(run_path(str(Path(__file__).with_name("18_calculos_informe.py"))))


# ======================================================================================================
# Preparación de la página: lo que convierte los resultados del análisis en HTML. Filas de las tablas,
# textos con etiquetas, citas, formato de números y fechas, los datos de las gráficas en JSON e
# imágenes y Plotly incrustados. Va en el mismo orden en que estaba en el script de cálculos.
# ======================================================================================================
# Plotly se incrusta en el HTML para que abra sin internet. La copia está en el repositorio (origen y SHA-256
# en DATOS_FUENTES.md); si el archivo cambia, el script se detiene.
PLOTLY = Path("reporte/vendor/plotly-2.32.0.min.js")
PLOTLY_SHA256 = "0a17719a72751704861215da0e5c5cdb3f9a8d50eff5cb84cb6f8b80786682b0"
assert hashlib.sha256(PLOTLY.read_bytes()).hexdigest() == PLOTLY_SHA256, f"{PLOTLY} no es la versión registrada"
PLOTLY_JS = PLOTLY.read_text(encoding="utf-8")
assert "</script" not in PLOTLY_JS.lower()       # no puede cerrar la etiqueta <script> en la que va

def img(nombre):
    return "data:image/png;base64," + base64.b64encode((FIG / nombre).read_bytes()).decode()

def n(x, dec=0):
    return f"{x:,.{dec}f}".replace(",", " ")        # separador de miles con espacio

filas = "\n".join(
    f"<tr><td class='cod'>{i}</td><td>{html.escape(nom)}</td><td>{rio}</td>"
    f"<td class='num'>{n(m.loc[i, 'area'])}</td><td class='num'>{m.loc[i, 'area'] / sg['area'] * 100:.0f}%</td>"
    f"<td class='num'>{n(m.loc[i, 'minimum_ele'])}–{n(m.loc[i, 'maximum_ele'])}</td>"
    f"<td class='num'>{n(m.loc[i, 'mean_ele'])}</td><td class='num'>{n(p_imerg[i])}</td></tr>"
    for i, (nom, rio) in ESTACIONES.items())

cmp_json = json.dumps(cmp_datos, ensure_ascii=False)
filas_cmp = "\n".join(
    f"<tr><td>{html.escape(nom)}</td><td class='num'>{v['n']}</td><td class='num'>{v['imerg']:.0f}</td>"
    f"<td class='num'>{v['pluv']:.0f}</td><td class='num'>{v['sesgo']:+.0f}%</td>"
    f"<td class='num'>{v['r']:.2f}</td></tr>" for nom, v in cmp_stats.items())

bal_json = json.dumps(bal_datos, ensure_ascii=False)

# Un color por variable (paleta Okabe-Ito), el mismo en todas las figuras: es la única definición. La página
# la recibe como COLOR_VAR en el JavaScript, y la nota de colores del comienzo la usa para sus muestras.
# PL* (la serie larga de PL) va como PL. La temperatura de ERA5-Land va en una familia de púrpura: T mín más
# clara y T máx más oscura, del mismo matiz (tonos revisados para que se lean sobre el fondo claro y el oscuro).
# La de MSWX usa el color de su equivalente de ERA5-Land y se distingue por el trazo.
COLOR_VAR = {"PL": "#D55E00", "PL*": "#D55E00", "PI": "#0072B2", "Q": "#009E73",
             "T mín": "#DE98C0", "T media": "#CC79A7", "T máx": "#9A4878",
             "T ERA5": "#CC79A7", "T MSWX": "#CC79A7", "ETP": "#7C5BC7"}
color_var_json = json.dumps(COLOR_VAR, ensure_ascii=False)
# toda variable que se dibuja tiene su color
assert set(VARIABLES_CORR) | set(variables_resumen.columns) | set(LARGO_VARS) <= set(COLOR_VAR)


def revision(etiqueta):
    """Atributos de un bloque resaltado en gris para revisión: lo que esta rama agregó o cambió."""
    return f' class="revision" data-etiqueta="Revisión · {html.escape(etiqueta)}"'


_muestra = lambda v: (f'<span style="display:inline-block; width:0.9em; height:0.9em; border-radius:2px; '
                      f'vertical-align:-0.1em; background:{COLOR_VAR[v]}"></span>')
nota_colores = (
    "Cada variable tiene un solo color en todas las figuras: "
    f"{_muestra('PL')} PL (también PL* y los pluviómetros sueltos), naranja; {_muestra('PI')} PI, azul; "
    f"{_muestra('Q')} Q, verde; la temperatura de ERA5-Land en púrpura, {_muestra('T mín')} T mín más clara, "
    f"{_muestra('T media')} T media y {_muestra('T máx')} T máx más oscura (la de MSWX, del mismo color con otro trazo); "
    f"{_muestra('ETP')} ETP, violeta. Los colores que no son de una variable (fases del ENSO, años contrastantes, "
    "atípicos, calidad del registro) siguen como estaban.")

# para los diagramas de caja: los valores de cada variable agrupados por mes del calendario
NOMBRE_MES_COMPLETO = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio",
                       8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
UNIDAD_RESUMEN = {"PI": "mm/mes", "PL": "mm/mes", "Q": "m³/s", "T media": "°C", "T máx": "°C", "T mín": "°C"}

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
CITA_SHAPIRO = '<a class="cita" href="#ref-shapiro1965">Shapiro y Wilk, 1965</a>'
CITA_NEWEY = '<a class="cita" href="#ref-newey1987">Newey y West, 1987</a>'
CITA_MANN = '<a class="cita" href="#ref-mann1945">Mann, 1945</a>'
CITA_SEN = '<a class="cita" href="#ref-sen1968">Sen, 1968</a>'
CITA_HIRSCH = '<a class="cita" href="#ref-hirsch1982">Hirsch et al., 1982</a>'
CITA_LOESS = '<a class="cita" href="#ref-cleveland1979">Cleveland, 1979</a>'
CITA_HAMED = '<a class="cita" href="#ref-hamed1998">Hamed y Rao, 1998</a>'
CITA_BH = '<a class="cita" href="#ref-benjamini1995">Benjamini y Hochberg, 1995</a>'
CITA_LOMB = '<a class="cita" href="#ref-lomb1976">Lomb, 1976</a>'
CITA_SCARGLE = '<a class="cita" href="#ref-scargle1982">Scargle, 1982</a>'
CITA_WELCH = '<a class="cita" href="#ref-welch1967">Welch, 1967</a>'
CITA_MESA = '<a class="cita" href="#ref-mesa1997">Mesa et al., 1997</a>'
CITA_MESA_P90 = '<a class="cita" href="#ref-mesa1997">Mesa et al., 1997, p. 90</a>'
CITA_UNEP = '<a class="cita" href="#ref-middleton1997">Middleton y Thomas, 1997</a>'

# Resaltado en verde de lo que cambió en la revisión del PR #19 (2026-10-08), para quien lo revise. Se apaga con False
# cuando el revisor lo apruebe, como se hizo con el resaltado amarillo en el PR #16.
RESALTAR_CAMBIOS = True


def _cambio(etiqueta):
    """Atributos HTML que marcan un bloque como cambiado en la revisión (o nada, si el resaltado está apagado)."""
    return f' class="cambio" data-etiqueta="{html.escape(etiqueta)}"' if RESALTAR_CAMBIOS else ""

NOMBRE_MES_CORTO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 7: "jul", 8: "ago",
                    9: "sep", 10: "oct", 11: "nov", 12: "dic"}
fmt_mes = lambda p: f"{NOMBRE_MES_CORTO[p.month]} {p.year}"

CLASE_FASE = {"El Niño": "fase-nino", "La Niña": "fase-nina"}

def fecha_enso(p):
    clase = CLASE_FASE.get(oni_fase.get(p, "neutro"))
    texto = fmt_mes(p)
    return f"<span class='{clase}' title='{oni_fase.get(p)}'>{texto}</span>" if clase else texto

lista_meses = lambda meses: ", ".join(fecha_enso(p) for p in meses) if len(meses) else "ninguno"

lectura_enso_lluvia = (
    f"Todos, menos {lista_meses(_confirmada_otras)}, cayeron en episodios de La Niña."
    if _confirmada_nina and _confirmada_otras else
    "Todos cayeron en episodios de La Niña." if _confirmada_nina else "")

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

# solo los meses comunes (clima_meses, los mismos de la tabla del ciclo anual), no todos los válidos de cada variable
cajas_json = json.dumps({
    "variables": list(clima_series.columns),
    "unidades": [UNIDAD_RESUMEN[v] for v in clima_series.columns],
    "valores": {v: [[round(float(x), 2) for x in clima_series[v][clima_series.index.month == m].dropna()]
                    for m in range(1, 13)] for v in clima_series.columns},
    # el mes exacto de cada valor (año-mes), para que el cursor diga cuál es cada punto
    "fechas": {v: [[f"{NOMBRE_MES_COMPLETO[p.month]} de {p.year}"
                    for p in clima_series[v][clima_series.index.month == m].dropna().index]
                   for m in range(1, 13)] for v in clima_series.columns},
    "meses": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
}, ensure_ascii=False)

filas_resumen = "\n".join(
    f"<tr><td>{html.escape(fila)}</td>"
    + "".join(f"<td class='num'>{v:.0f}</td>" if fila == "meses válidos"
              else f"<td class='num'>{n(v, 2)}</td>" for v in tabla_resumen.loc[fila])
    + "</tr>" for fila in tabla_resumen.index)

def ciclo_tabla_html(clave, columna, decimales):
    # sobre los meses comunes (clima_meses): todas las variables con los mismos pares de meses
    e = ciclo_estadisticos(clima_series[columna])
    fmt = lambda v: f"{v:,.{decimales}f}".replace(",", " ")
    filas = "\n".join(
        f"<tr><td>{MESES_LARGOS_ES[m - 1]}</td><td class='num'>{int(f.n)}</td>"
        + "".join(f"<td class='num'>{fmt(f[c])}</td>" for c in ("media", "mediana", "sd", "p10", "q1", "q3", "p90"))
        + "</tr>" for m, f in e.iterrows())
    return filas

ciclo_tablas = {clave: ciclo_tabla_html(clave, col, dec) for clave, _, _, col, dec in CICLO_VARIABLES}

ciclo_json = json.dumps(ciclo_datos, ensure_ascii=False)

# mapa año–mes: una matriz por variable (años × meses), con null en los meses sin dato. PL y PI comparten el
# rango de color, para que el mismo color sea la misma lluvia en las dos; Q y T media tienen el suyo.
_mapa_rango_lluvia = (min(float(mapa_am[f].min().min()) for f in ("PL", "PI")),
                      max(float(mapa_am[f].max().max()) for f in ("PL", "PI")))
mapa_am_json = json.dumps({
    "anios": [str(a) for a in MAPA_AM_ANIOS],
    "variables": [{
        "nombre": v, "unidad": u, "dec": dec,
        "z": [[None if pd.isna(x) else round(float(x), 2) for x in fila] for fila in mapa_am[v].to_numpy()],
        "rango": _mapa_rango_lluvia if v in ("PL", "PI") else (float(mapa_am[v].min().min()), float(mapa_am[v].max().max())),
    } for v, u, dec in MAPA_AM_VARIABLES],
}, ensure_ascii=False)
mapa_botones = "\n".join(
    f'    <button type="button" role="tab" id="pestana-mapa-{i}" aria-controls="panel-mapa" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>{v} ({u})</button>'
    for i, (v, u, _) in enumerate(MAPA_AM_VARIABLES))

def _y_lista(xs):
    """1999 · 1999 y 2006 · 1999, 2006 y 2011"""
    xs = [str(x) for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]

def _mapa_sobre_txt(f):
    r = mapa_am_sobre[f]
    verbo = lambda xs: "tiene" if len(xs) == 1 else "tienen"
    return (f"con {f}, {_y_lista(r['anios_mas'])} {verbo(r['anios_mas'])} {r['mas']} de 12 meses por encima y "
            f"{_y_lista(r['anios_menos'])} solo {r['menos']}")

def _mapa_coincide_txt(f):
    r = mapa_am_sobre[f]
    partes = ([f"{_y_lista(r['coinciden_humedos'])} (entre los de más meses por encima)"] if r["coinciden_humedos"] else []) + \
             ([f"{_y_lista(r['coinciden_secos'])} (entre los de menos)"] if r["coinciden_secos"] else [])
    if not partes:
        return f"con {f} no coincide ninguno"
    n_coinciden = len(r["coinciden_humedos"]) + len(r["coinciden_secos"])
    return f"con {f} {'coincide' if n_coinciden == 1 else 'coinciden'} " + " y ".join(partes)

mapa_picos_txt = "; ".join(
    f"en {r['simple']} de {r['anios']} años con {f} (picos en {r['picos'][0]} y {r['picos'][1]}: "
    f"{r['ventanas'][0]} y {r['ventanas'][1]})" for f, r in mapa_am_picos.items())

_mes = lambda m: MESES_LARGOS_ES[m - 1]
var_filas = "\n".join(
    f"<tr><td><b>{v}</b></td><td>{_mes(var_mas[v][0])} ({var_tabla.loc[(v, var_mas[v][0]), 'cv']:.{2 if v == 'T media' else 0}f} %)</td>"
    f"<td>{_mes(var_mas[v][1])} ({var_tabla.loc[(v, var_mas[v][1]), 'de']:.{2 if v == 'T media' else 1}f} {VAR_SERIES[v][1]})</td>"
    f"<td>{', '.join(_mes(m) for m in var_fuertes[v]) or 'ninguno' if v in _VAR_LC else '—'}</td>"
    f"<td>{_mes(var_top[v][0][1])} de {var_top[v][0][0]} ({var_top[v][1]:+.{2 if v == 'T media' else 1}f} %)</td></tr>"
    for v in VAR_SERIES)

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

p2_pipl_json = json.dumps({"pi": _p2.IMERG.round(1).tolist(), "pl": _p2.RED.round(1).tolist(),
                           "mes": [p.month for p in _p2.index], "periodo": [str(p) for p in _p2.index]})

ev_filas = "\n".join(
    f"<tr><td>{'<b>' + m + '</b>' if m == ev_mejor else m}</td><td class='num'>{t['ajuste']['rmse']:.1f}</td>"
    f"<td class='num'>{t['validacion']['rmse']:.1f}</td><td class='num'>{t['validacion']['mae']:.1f}</td>"
    f"<td class='num'>{t['validacion']['sesgo']:+.1f}</td><td class='num'>{t['validacion']['n']}</td></tr>"
    for m, t in ev_tabla.items())

ev_json = json.dumps({"meses": [str(p) for p in _ev_val.index], "q": _ev_val.Q.round(2).tolist(),
                      **{k: ev_estimados[m].loc[_ev_val.index].round(2).tolist() for k, m in
                         (("clima", "climatología mensual de Q"), ("pl", "PL del mismo mes"), ("pi", "PI del mismo mes"))}},
                     default=lambda v: None).replace("NaN", "null")

t_json = json.dumps({"meses": MESES_ES, "ciclo": t_ciclo}, ensure_ascii=False)

_lista_y = lambda l: ", ".join(l[:-1]) + " y " + l[-1] if len(l) > 1 else (l[0] if l else "")

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

_red1 = lambda s: [None if pd.isna(v) else round(float(v), 1) for v in s]
pq_json = json.dumps({"meses": [f"{p}-01" for p in pq.index], "pl_q": _red1(pq.pl_q), "pi_q": _red1(pq.pi_q),
                      "etp": _red1(pq.etp), "anios": [str(a) for a in pq_anual.index],
                      "pl_q_anual": _red1(pq_anual.pl_q), "pi_q_anual": _red1(pq_anual.pi_q),
                      "etp_anual": _red1(pq_anual.etp)}, ensure_ascii=False)

etp_json = json.dumps({"meses": MESES_ES, **{k: _etp_ciclo[k].round(1).tolist() for k in etp_comun},
                       "pl_q": _etp_pq_ciclo.round(1).tolist()}, ensure_ascii=False)

# índice P/ETP: tablas, datos de la figura y textos (las cifras salen de pe_* en 18_calculos_informe.py)
PE_FUENTE = {"pl": "PL", "pi": "PI"}
pe_filas_anual = "\n".join(
    f"<tr><td><b>{PE_FUENTE[f]}</b></td><td class='num'>{n(r['p'])}</td><td class='num'>{n(pe_etp_anual)}</td>"
    f"<td class='num'><b>{r['ie']:.2f}</b></td><td>{r['clase']}</td>"
    f"<td class='num'>{r['min']:.2f} ({r['anio_min']})</td><td class='num'>{r['max']:.2f} ({r['anio_max']})</td>"
    f"<td class='num'>{len(r['bajo_humedo'])}</td></tr>" for f, r in pe_indice.items())
_pe_celda = lambda x: f"<td class='num'><b>{x:.2f}</b></td>" if x < 1 else f"<td class='num'>{x:.2f}</td>"
pe_filas_mes = "\n".join(
    f"<tr><td>{MESES_LARGOS_ES[m - 1]}</td>{_pe_celda(pe_mes.loc[m, 'pl'])}{_pe_celda(pe_mes.loc[m, 'pi'])}"
    f"<td class='num'>{pe_mes_deficit_anios.loc[m, 'pl']}</td><td class='num'>{pe_mes_deficit_anios.loc[m, 'pi']}</td></tr>"
    for m in range(1, 13))
pe_json = json.dumps({"meses": MESES_ES, "pl": pe_mes.pl.round(2).tolist(), "pi": pe_mes.pi.round(2).tolist()},
                     ensure_ascii=False)
# los límites de las clases de UNEP, escritos desde la constante del código
_pe_limites = [0] + [lim for lim, _ in UNEP_LIMITES[:-1]]
pe_clases_txt = html.escape("; ".join(
    f"{nombre} {'< ' + f'{lim:.2f}' if i == 0 else ('≥ ' + f'{_pe_limites[i]:.2f}' if lim == float('inf') else f'{_pe_limites[i]:.2f}–{lim:.2f}')}"
    for i, (lim, nombre) in enumerate(UNEP_LIMITES)))
_pe_meses_txt = lambda ms: _y_lista([MESES_LARGOS_ES[m - 1] for m in ms])
_pe_dos = all(r["clase"] == pe_indice["pl"]["clase"] for r in pe_indice.values())
pe_resultado_txt = (
    (f"<b>El clima de la cuenca es {pe_indice['pl']['clase']} con las dos fuentes</b>" if _pe_dos else
     f"<b>La clase depende de la fuente</b>: {pe_indice['pl']['clase']} con PL y {pe_indice['pi']['clase']} con PI")
    + f": P/ETP = {pe_indice['pl']['ie']:.2f} con PL y {pe_indice['pi']['ie']:.2f} con PI, contra el umbral de húmedo de "
    f"{UNEP_HUMEDO:.2f}. ")
_pe_bajo = {f: r["bajo_humedo"] for f, r in pe_indice.items()}
pe_anios_txt = (
    (f"<b>Ningún año baja de ese umbral</b>, con ninguna de las dos fuentes" if not _pe_bajo["pl"] and not _pe_bajo["pi"] else
     f"Bajan del umbral {len(_pe_bajo['pl'])} años con PL ({', '.join(map(str, _pe_bajo['pl'])) or 'ninguno'}) y "
     f"{len(_pe_bajo['pi'])} con PI ({', '.join(map(str, _pe_bajo['pi'])) or 'ninguno'})")
    + f": el índice de cada año va de {pe_indice['pl']['min']:.2f} ({pe_indice['pl']['anio_min']}) a "
    f"{pe_indice['pl']['max']:.2f} ({pe_indice['pl']['anio_max']}) con PL, y de {pe_indice['pi']['min']:.2f} "
    f"({pe_indice['pi']['anio_min']}) a {pe_indice['pi']['max']:.2f} ({pe_indice['pi']['anio_max']}) con PI.")
# el año más seco, con la fuente más baja, frente al umbral (para decir cuánto margen hay)
pe_min_global = min(r["min"] for r in pe_indice.values())
pe_margen_txt = (f"Incluso el año más seco, con la fuente más baja, queda en {pe_min_global:.2f}, "
                 f"{pe_min_global / UNEP_HUMEDO:.1f} veces el umbral: la clase no depende solo del promedio."
                 if pe_min_global >= UNEP_HUMEDO else
                 "La clase del promedio no se cumple todos los años: depende de cuáles se miren.")
# meses de déficit en el año típico, con cada fuente, y si coinciden
_pe_def_txt = lambda f: (f"hay déficit en {_pe_meses_txt(pe_meses_deficit[f])}" if pe_meses_deficit[f]
                         else "ningún mes tiene déficit")
pe_deficit_txt = f"Con PL, {_pe_def_txt('pl')}; con PI, {_pe_def_txt('pi')}."
if not pe_deficit_igual:
    _pe_dif = pe_solo_pi + pe_solo_pl
    pe_deficit_txt += (
        f" <b>Las dos fuentes no coinciden</b>: "
        + "; ".join(f"{MESES_LARGOS_ES[m - 1]} tiene déficit con {'PI' if m in pe_solo_pi else 'PL'} "
                    f"({pe_mes.loc[m, 'pi' if m in pe_solo_pi else 'pl']:.2f}) y no con {'PL' if m in pe_solo_pi else 'PI'} "
                    f"({pe_mes.loc[m, 'pl' if m in pe_solo_pi else 'pi']:.2f})" for m in _pe_dif) + ".")
# año por año: meses en que P < ETP en más de la mitad de los años con alguna fuente, y meses sin déficit nunca
_pe_frecuentes = [m for m in range(1, 13) if pe_mes_deficit_anios.loc[m].max() > pe_n_anios / 2]
_pe_nunca = [m for m in range(1, 13) if pe_mes_deficit_anios.loc[m].max() == 0]
pe_anios_mes_txt = (
    ("Año por año, el déficit es frecuente (más de la mitad de los años) en "
     + "; ".join(f"{MESES_LARGOS_ES[m - 1]} ({pe_mes_deficit_anios.loc[m, 'pl']} de {pe_n_anios} años con PL, "
                 f"{pe_mes_deficit_anios.loc[m, 'pi']} con PI)" for m in _pe_frecuentes) + ". "
     if _pe_frecuentes else "Año por año, ningún mes tiene déficit en más de la mitad de los años. ")
    + (f"{_pe_meses_txt(_pe_nunca).capitalize()} no {'tuvo' if len(_pe_nunca) == 1 else 'tuvieron'} déficit en ningún año, "
       "con ninguna de las dos fuentes." if _pe_nunca else ""))

UNIDAD_VAR = {"PI": "mm/mes", "PL": "mm/mes", "Q": "mm/mes",
              "ETP": "mm/mes", "T MSWX": "°C", "T ERA5": "°C"}

ciclo_lq_json = json.dumps({
    "meses": MESES_ES,
    "PL": ciclo_lq.PL.round(1).tolist(), "Q": ciclo_lq.Q.round(1).tolist(),
    "ajusteMes": ciclo_lq.Q_ajuste_PL_mes.round(1).tolist(),
    "ajusteMesAnterior": ciclo_lq.Q_ajuste_PL_mes_y_anterior.round(1).tolist(),
}, ensure_ascii=False)

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

filas_ciclo = "\n".join(
    f"<tr><td>{a} – {b}</td><td class='num'>{corr_ciclo_rho.loc[a, b]:+.2f}</td>"
    f"<td class='num'>{rho(a, b):+.2f}</td><td class='num'>{rho(a, b, anomalias=True):+.2f}</td></tr>"
    for a, b in PARES_CICLO)

cal_json = json.dumps({"meses": [f"{p}-01" for p in periodos], "fuentes": cal_filas,
                       "maxFaltantes": MAX_DIAS_FALTANTES}, ensure_ascii=False)

filas_disp = "\n".join(
    f"<tr><td>{html.escape(v['nombre'])}</td><td>{v['paso']}</td>"
    f"<td class='num'>{v['usables']}</td>"
    f"<td class='num'>{v['parciales'] if v['paso'] == 'diario' else '—'}</td>"
    f"<td class='num'>{v['perdidos']}</td>"
    f"<td class='num'>{v['usables'] / cal_total * 100:.0f}%</td></tr>" for v in cal_resumen)

fmt_p = lambda p: "&lt; 0.001" if p < 0.001 else f"{p:.3f}"

fmt_mes_an = lambda p: fmt_mes(pd.Period(p, "M"))
# «Explicaciones físicas» dice que enero y febrero de 2005 estuvieron sobre lo normal en PL, PI y Q
assert all(ene05[k] > 0 for k in ("z_pl", "z_pi", "z_q", "z_pl_feb", "z_pi_feb", "z_q_feb"))
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

filas_an = "\n".join(
    f"<tr><td>{html.escape(s)}</td><td class='detalle'>{html.escape(ref)}</td><td class='num'>{m}</td>"
    f"<td class='num'>{fecha_anomala(pm) if sig else fmt_mes_an(pm)}</td><td class='num{' res-revisar' if sig else ''}'>{fmt_p(p)}</td>"
    f"<td class='num'>{a:.2f}</td><td class='num'>{d:.2f}</td><td class='num'>{c:+.0f} %</td></tr>"
    for s, ref, m, pm, p, sig, a, d, c in an_h[["serie", "referencia", "meses", "primer_mes_despues", "p",
                                                "significativo", "razon_antes", "razon_despues", "cambio_pct"]].itertuples(index=False))
# "variable": la primera palabra del nombre de la serie (PL, PI o Q), para colorearla con COLOR_VAR
assert set(an_dm.serie.str.split().str[0]) <= set(COLOR_VAR)
an_dm_json = json.dumps({s: {"variable": s.split()[0],
                             "x": g.acumulado_referencia.round(0).tolist(), "y": g.acumulado_serie.round(0).tolist(),
                             "meses": g.periodo.tolist(), "referencia": g.referencia.iloc[0],
                             "corte": (an_fila(s).primer_mes_despues if an_fila(s).significativo else None)}
                         for s, g in an_dm.groupby("serie", sort=False)}, ensure_ascii=False)

filas_ceros = "\n".join(
    f"<tr><td>{html.escape(pl_)}</td><td>{fecha_anomala(m) if dif else fmt_mes_an(m)}</td><td class='num'>{mn:.0f}</td><td class='num'>{pr:.0f}</td>"
    f"<td class='num'>{pi_:.0f}</td><td class='{'res-revisar' if dif else ''}'>{'se excluye' if dif else 'se conserva'}</td></tr>"
    for pl_, m, mn, pr, pi_, dif in an_ceros[["pluviometro", "periodo", "otros_minimo_mm", "otros_promedio_mm",
                                               "pi_mm", "dificil_de_creer"]].itertuples(index=False))

exc_lista = "; ".join(
    f"{_nombre_pluvio[c]} de {fmt_mes_an(d)} a {fmt_mes_an(h)}" if d != h else f"{_nombre_pluvio[c]} en {fecha_anomala(d)}"
    for c, d, h in exclusiones[["codigo", "desde", "hasta"]].itertuples(index=False))

CLASE_RESULTADO = {"sin problemas": "", "anotado": "res-anotado", "revisar": "res-revisar", "no disponible": "res-nd"}
filas_cc = "\n".join(
    f"<tr><td>{html.escape(f)}</td><td>{html.escape(c)}</td><td class='{CLASE_RESULTADO[res]}'>{res}</td>"
    f"<td class='detalle'>{html.escape(d)}</td></tr>"
    for f, c, res, d in cc[["fuente", "chequeo", "resultado", "detalle"]].itertuples(index=False))
filas_naturaleza = "\n".join(
    f"<tr><td><b>{html.escape(v)}</b></td><td>{html.escape(fu)}</td><td>{html.escape(ti)}</td>"
    f"<td class='detalle'>{html.escape(co)}</td><td class='detalle'>{html.escape(re_)}</td></tr>"
    for v, fu, ti, co, re_ in cc_naturaleza.itertuples(index=False))

CLASE_ESTADO = {"corregido": "", "incierto": "res-revisar", "descartado": "res-nd"}
filas_reg = "\n".join(
    f"<tr><td class='num'>{n_}</td><td class='{CLASE_ESTADO[es]}'>{es}</td><td>{html.escape(se)}</td>"
    f"<td class='reg-anomalia'>{html.escape(an)}</td><td class='detalle'>{html.escape(co)}</td>"
    f"<td class='detalle'>{html.escape(de)}</td><td class='detalle'>{html.escape(ef)}</td></tr>"
    for n_, an, se, co, de, ef, es in reg[["n", "anomalia", "serie", "comprobacion", "decision", "efecto",
                                           "estado"]].itertuples(index=False))

grad_json = json.dumps(grad_datos, ensure_ascii=False)

filas_grad = "\n".join(
    f"<tr><td>{html.escape(e.nombre_corto)}</td><td class='num'>{n(e.altitud)}</td>"
    f"<td class='num'>{n(e.p_anual_mm)}</td>"
    f"<td>{'dentro' if e.dentro_cuenca else 'fuera'}</td></tr>"
    for e in grad_plu.itertuples())

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


# ¿se repite cada año? ¿es estable?: filas de las dos tablas
est_filas_anual = "\n".join(
    f"<tr><td><b>{v}</b> ({' y '.join(r['picos'])})</td><td class='num'>{r['anios']}</td>"
    f"<td class='num'>{r['bimodales']}</td><td class='num'>{r['p1']}</td><td class='num'>{r['p2']}</td>"
    f"<td class='num'>{r['dist_mediana']:.1f} (máx. {r['dist_max']:.1f})</td><td class='num'>{r['simple']}</td></tr>"
    for v, r in est_anual.items())


def _est_celda(m):
    return f"{m['clase']}, {' y '.join(m['picos'])}; A₂/A₁ {m['razon']:.2f} [{m['ic'][0]:.2f}–{m['ic'][1]:.2f}]"


est_filas_mitades = "\n".join(
    f"<tr><td><b>{v}</b></td><td>{_est_celda(r['1998–2010'])}</td><td>{_est_celda(r['2011–2022'])}</td>"
    f"<td class='num'>{' y '.join(f'{d:.1f}' for d in r['corrimiento']) if r['corrimiento'] else '—'}</td>"
    f"<td>{'sí' if r['estable'] else '<b>no</b>'}</td></tr>" for v, r in est_mitades.items())

# anomalías estandarizadas y tendencias: tablas y datos de las gráficas
ANZ_GRUPOS = {"Lluvia (PL* y PI)": ["PL*", "PI"], "Caudal (Q)": ["Q"], "Temperatura (mín, media y máx)": ["T mín", "T media", "T máx"]}
ANZ_DEC = {"PL*": 0, "PI": 0, "Q": 1, "T mín": 2, "T media": 2, "T máx": 2}


def _p_txt(p):
    return "&lt; 0.001" if p < 0.001 else f"{p:.3f}"


def _pend_txt(valor, p, dec):
    """Pendiente por década con su p; en negrita si es significativa."""
    texto = f"{valor:+.{dec}f} <small>(p {_p_txt(p)})</small>"
    return f"<b>{texto}</b>" if p < TEND_ALFA else texto


anz_filas = "\n".join(
    f"<tr><td>{MESES_LARGOS_ES[m - 1]}</td>"
    + "".join(f"<td class='num'>{anz_mu.loc[m, v]:.{ANZ_DEC[v]}f} / {anz_s.loc[m, v]:.{ANZ_DEC[v]}f} ({anz_n.loc[m, v]})</td>"
              for v in LARGO_VARS) + "</tr>" for m in range(1, 13))
anz_forma_filas = "\n".join(
    f"<tr><td><b>{v}</b></td><td class='num'>{anz_n[v].min()}–{anz_n[v].max()}</td>"
    f"<td class='num'>{anz_ancho_rel[v].min():.0f}–{anz_ancho_rel[v].max():.0f} %</td>"
    f"<td class='num'>{f['asim']:+.2f}</td><td class='num'>{f['extremos']:.1f} %</td>"
    f"<td class='num'>{_p_txt(f['shapiro_p'])}</td><td class='num'>{f['r_x_a']:.2f}</td><td class='num'>{f['r_a_z']:.2f}</td></tr>"
    for v, f in anz_forma.items())
largo_filas = "\n".join(
    f"<tr><td><b>{v}</b></td><td>{LARGO_FUENTE[v]}</td><td>{fmt_mes(r['inicio'])}</td><td>{fmt_mes(r['fin'])}</td>"
    f"<td class='num'>{r['meses']}</td><td class='num'>{r['validos']}</td><td class='num'>{r['vacios']}</td>"
    f"<td>{LARGO_CAMBIOS[v]}</td></tr>" for v, r in largo_registro.items())
_tend_filas = []
for v in LARGO_VARS:
    for per in TEND_PERIODOS:
        if v == "PI" and per != "completo":
            continue                     # para PI el registro completo es 1998-2022: sería la misma fila
        f = tend_todos[(v, per)]
        d = ANZ_DEC[v] + 1
        etiqueta = (f"{fmt_mes(f['inicio'])} a {fmt_mes(f['fin'])}" + (" (registro completo)" if per == "completo" else " (período común)"))
        _tend_filas.append(
            f"<tr><td><b>{v}</b> <small>({LARGO_UNIDADES[v]})</small></td><td>{etiqueta}</td><td class='num'>{f['n']}</td>"
            f"<td class='num'>{_pend_txt(f['X']['ols'], f['X']['p'], d)}</td><td class='num'>{_pend_txt(f['X']['mk'], f['X']['p_mk'], d)}</td>"
            f"<td class='num'>{_pend_txt(f['a']['ols'], f['a']['p'], d)}</td><td class='num'>{_pend_txt(f['z']['ols'], f['z']['p'], 3)}</td></tr>")
tend_filas = "\n".join(_tend_filas)


def _serie_json(s, dec):
    return [None if pd.isna(x) else round(float(x), dec) for x in s]


_anz_t = largo.index
anz_json = json.dumps({
    "fechas": [f"{p.year}-{p.month:02d}-15" for p in _anz_t],
    "ref": [f"{ANZ_REFERENCIA[0].year}-{ANZ_REFERENCIA[0].month:02d}-01", f"{ANZ_REFERENCIA[1].year}-{ANZ_REFERENCIA[1].month:02d}-28"],
    "grupos": ANZ_GRUPOS,
    "enso": [[f"{a.year}-{a.month:02d}-01", f"{b.year}-{b.month:02d}-28", f] for a, b, f in enso_tramos],
    "unidades": LARGO_UNIDADES,
    "series": {v: {"X": _serie_json(largo[v], ANZ_DEC[v] + 1), "a": _serie_json(anz_a[v], ANZ_DEC[v] + 1),
                   "z": _serie_json(anz_z[v], 2),
                   # recta de tendencia de a y de z sobre el registro completo (OLS), en sus dos extremos
                   "recta": {k: {"x": [f"{tend_todos[(v, 'completo')]['inicio'].year}-{tend_todos[(v, 'completo')]['inicio'].month:02d}-15",
                                       f"{tend_todos[(v, 'completo')]['fin'].year}-{tend_todos[(v, 'completo')]['fin'].month:02d}-15"],
                                 "y": [round(tend_todos[(v, 'completo')][k]["corte"] + tend_todos[(v, 'completo')][k]["ols"] / 10 * t, 4)
                                       for t in (_t_decimal(pd.PeriodIndex([tend_todos[(v, 'completo')]['inicio']]))[0],
                                                 _t_decimal(pd.PeriodIndex([tend_todos[(v, 'completo')]['fin']]))[0])]}
                             for k in ("a", "z")}}
               for v in LARGO_VARS},
}, ensure_ascii=False)
tend_json = json.dumps({
    per: {"vars": LARGO_VARS,
          "z": [[round(tend_mes[(v, per, m)]["z"], 3) for m in range(1, 13)] for v in LARGO_VARS],
          "x": [[round(tend_mes[(v, per, m)]["X"], ANZ_DEC[v] + 2) for m in range(1, 13)] for v in LARGO_VARS],
          "p": [[round(tend_mes[(v, per, m)]["p"], 4) for m in range(1, 13)] for v in LARGO_VARS],
          "n": [[tend_mes[(v, per, m)]["n"] for m in range(1, 13)] for v in LARGO_VARS],
          "unidades": [LARGO_UNIDADES[v] for v in LARGO_VARS]}
    for per in TEND_PERIODOS}, ensure_ascii=False)
_meses_txt = lambda ms: ", ".join(MESES_LARGOS_ES[m - 1] for m in ms) if ms else "ninguno"
tend_conteo_txt = "; ".join(
    f"{v}: {len(tend_conteo[(v, 'completo')]['meses'])} ({_meses_txt(tend_conteo[(v, 'completo')]['meses'])})"
    for v in LARGO_VARS)

anz_botones = "\n".join(
    f'    <button type="button" role="tab" id="pestana-anz-{i}" aria-controls="panel-anz" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>{g}</button>'
    for i, g in enumerate(ANZ_GRUPOS))
tend_botones = "\n".join(
    f'    <button type="button" role="tab" id="pestana-tend-{i}" aria-controls="panel-tend" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>'
    f'{"Registro completo de cada variable" if per == "completo" else "Período común " + per}</button>'
    for i, per in enumerate(TEND_PERIODOS))

# tendencias: tablas y datos de la comparación de métodos
def _ic_txt(pend, ic, dec):
    return f"{pend:+.{dec}f} ± {ic:.{dec}f}"


def _p_neg(texto, p):
    return f"<b>{texto}</b>" if p < TEND_ALFA else texto


def _per_txt(f):
    return f"{f['inicio'].year}–{f['fin'].year}"


def _forma_txt(tramos):
    if not tramos:
        return "plana"
    return ", ".join(f"{'sube' if s > 0 else 'baja'} {a:.0f}–{b:.0f}" for s, a, b in tramos)


_met_ols, _met_np = [], []
for (v, per), f in met_global.items():
    d = ANZ_DEC[v] + 1
    et = f"<b>{v}</b> <small>({LARGO_UNIDADES[v]})</small>"
    cel = f"<td>{et}</td><td>{_per_txt(f)}</td><td class='num'>{f['n']}</td>"
    o = {k: f[f"ols_{k}"] for k in ("X", "Xmes", "a", "z")}
    _met_ols.append(
        "<tr>" + cel
        + f"<td class='num'>{_p_neg(_ic_txt(o['X']['pend'], o['X']['ic_hac'], d), o['X']['p_hac'])}</td>"
        + f"<td class='num'>{_p_neg(_ic_txt(o['Xmes']['pend'], o['Xmes']['ic_hac'], d), o['Xmes']['p_hac'])} <small>(p {_p_txt(o['Xmes']['p_hac'])})</small></td>"
        + f"<td class='num'>{_p_neg(_ic_txt(o['a']['pend'], o['a']['ic_hac'], d), o['a']['p_hac'])} <small>(clásico ± {o['a']['ic_cl']:.{d}f})</small></td>"
        + f"<td class='num'>{_p_neg(_ic_txt(o['z']['pend'], o['z']['ic_hac'], 3), o['z']['p_hac'])}</td>"
        + f"<td class='num'>{o['a']['r1']:.2f} / {_p_txt(o['a']['p_lb'])}</td><td class='num'>{_p_txt(o['a']['p_bp'])}</td>"
        + f"<td class='num'>{_p_txt(o['a']['p_sw'])}</td></tr>")
    mx, ma = f["mk_X"], f["mk_a"]
    sen_x = f"{mx['pend']:+.{d}f} [{mx['lo']:+.{d}f}, {mx['hi']:+.{d}f}]"
    sen_a = f"{ma['pend']:+.{d}f} [{ma['lo']:+.{d}f}, {ma['hi']:+.{d}f}]"
    _met_np.append(
        "<tr>" + cel
        + f"<td class='num'>{_p_neg(sen_x, mx['p'])} <small>(p {_p_txt(mx['p'])})</small></td>"
        + f"<td class='num'>{_p_neg(sen_a, ma['p'])} <small>(p {_p_txt(ma['p'])}; sin corregir {_p_txt(ma['p_sin'])})</small></td>"
        + f"<td>{f['loess_a']['cambio']:+.{d}f}: {_forma_txt(f['loess_a']['forma'])}</td>"
        + f"<td class='num'>{f['seg']['dbic']:+.1f} <small>(mejor quiebre {f['seg']['tau']:.0f})</small></td></tr>")
met_ols_filas, met_np_filas = "\n".join(_met_ols), "\n".join(_met_np)
met_sens_filas = "\n".join(
    f"<tr><td><b>{v}</b> <small>({LARGO_UNIDADES[v]})</small></td>"
    + "".join(f"<td class='num'>{s[f'frac {fr}']['cambio']:+.{ANZ_DEC[v] + 1}f} <small>({s[f'frac {fr}']['tramos']} tramo{'s' if s[f'frac {fr}']['tramos'] != 1 else ''})</small></td>" for fr in MET_FRACS)
    + f"<td class='num'>{s['extremos']:.{ANZ_DEC[v] + 1}f}</td><td class='num'>{s['borde_vs_centro']:.1f} veces</td></tr>"
    for v, s in met_sens.items())
met_mes_detalles = "\n".join(
    f"<details class='plegable-mini'><summary><b>{v}</b> <small>({LARGO_UNIDADES[v]} por década)</small></summary>"
    "<div class='tabla-caja'><table class='sin-destacar'><thead><tr><th>Mes</th><th class='num'>Años</th>"
    "<th class='num'>OLS ± IC 95 %</th><th class='num'>p</th><th class='num'>Sen [IC 95 %]</th><th class='num'>p (MK)</th>"
    "<th class='num'>r₁</th><th>LOESS</th></tr></thead><tbody>"
    + "".join(
        f"<tr><td>{MESES_LARGOS_ES[m - 1]}</td><td class='num'>{r['n']} <small>({r['desde']}–{r['hasta']})</small></td>"
        f"<td class='num'>{_p_neg(_ic_txt(r['ols'], r['ic'], ANZ_DEC[v] + 1), r['p'])}</td><td class='num'>{_p_txt(r['p'])}</td>"
        f"<td class='num'>{r['sen']:+.{ANZ_DEC[v] + 1}f} [{r['sen_lo']:+.{ANZ_DEC[v] + 1}f}, {r['sen_hi']:+.{ANZ_DEC[v] + 1}f}]</td>"
        f"<td class='num'>{_p_txt(r['p_mk'])}</td><td class='num'>{r['r1']:+.2f}{' *' if r['r1_signif'] else ''}</td>"
        f"<td>{_forma_txt(r['forma'])}</td></tr>"
        for m in range(1, 13) for r in [met_mes[(v, m)]])
    + "</tbody></table></div></details>"
    for v in LARGO_VARS)
met_json = json.dumps({
    v: {k: {"fechas": [f"{p.year}-{p.month:02d}-15" for p in met_curvas[(v, k)]["t"]],
            "y": _serie_json({"X": largo[v], "a": anz_a[v], "z": anz_z[v]}[k].dropna(), 3),
            "curva": [round(float(x), 4) for x in met_curvas[(v, k)]["curva"]],
            "lo": [round(float(x), 4) for x in met_curvas[(v, k)]["lo"]],
            "hi": [round(float(x), 4) for x in met_curvas[(v, k)]["hi"]],
            "ols": [round(float(x), 4) for x in met_curvas[(v, k)]["ols_recta"]],
            "ols_lo": [round(float(x), 4) for x in met_curvas[(v, k)]["ols_lo"]],
            "ols_hi": [round(float(x), 4) for x in met_curvas[(v, k)]["ols_hi"]]}
        for k in ("X", "a", "z")}
    for v in LARGO_VARS}, ensure_ascii=False)
met_botones_var = "\n".join(
    f'    <button type="button" role="tab" id="pestana-met-v{i}" aria-controls="panel-met" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>{v}</button>'
    for i, v in enumerate(LARGO_VARS))
met_botones_rep = "\n".join(
    f'    <button type="button" role="tab" id="pestana-met-r{i}" aria-controls="panel-met" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>{nombre}</button>'
    for i, nombre in enumerate(("anomalía a", "original X", "estandarizada z")))


# tendencias: tabla resumen (pendiente por década con sus unidades, en X y en z, registro completo)
RES_UNIDAD_DECADA = {"PL*": "mm/mes por década", "PI": "mm/mes por década", "Q": "m³/s por década",
                     "T mín": "°C/década", "T media": "°C/década", "T máx": "°C/década"}


def _res_fila(v):
    f = met_global[(v, "completo")]
    x, z = f["ols_Xmes"], f["ols_z"]
    d = ANZ_DEC[v] + 1 if not v.startswith("T") else 2
    ols_sig, sen_sig = x["p_hac"] < TEND_ALFA, f["mk_X"]["p"] < TEND_ALFA
    if ols_sig and sen_sig:
        lectura = "<b>sube</b>" if x["pend"] > 0 else "<b>baja</b>"
        lectura += ", con los dos métodos"
    elif ols_sig or sen_sig:
        lectura = "señal débil: solo un método la da significativa"
    else:
        lectura = "sin tendencia"
    return (f"<tr><td><b>{v}</b></td><td>{f['inicio'].year}–{f['fin'].year}</td>"
            f"<td class='num'><b>{x['pend']:+.{d}f}</b> ± {x['ic_hac']:.{d}f} <small>{RES_UNIDAD_DECADA[v]}</small></td>"
            f"<td class='num'>{z['pend']:+.2f} ± {z['ic_hac']:.2f}</td>"
            f"<td>{lectura}</td></tr>")


res_filas = "\n".join(_res_fila(v) for v in LARGO_VARS)

# tendencias: tabla de Pettitt (¿tendencia gradual o salto?)
salto_filas = "\n".join(
    f"<tr><td><b>{v}</b> <small>({LARGO_UNIDADES[v]})</small></td><td class='num'>{r['anios']}</td>"
    f"<td class='num'>{r['anio_corte']}</td><td class='num'>{_p_neg(_p_txt(r['p']), r['p'])}</td>"
    f"<td class='num'>{_p_neg(_p_txt(r['p_perm']), r['p_perm'])}</td>"
    f"<td class='num'>{r['antes']:+.{ANZ_DEC[v] + 1}f} → {r['despues']:+.{ANZ_DEC[v] + 1}f}</td>"
    f"<td class='num'>{_p_txt(r['p_residuos'])}</td>"
    f"<td>{(r['mejor'] + (' (empate)' if r['empate'] else '')) if v in salto_con_corte else '—'}</td></tr>" for v, r in salto.items())

# tendencias: pendientes de los 12 meses con sus intervalos (gráfico), FDR
pend_json = json.dumps({
    v: {"unidad": RES_UNIDAD_DECADA[v],
        "ols": [round(met_mes[(v, m)]["ols"], 4) for m in range(1, 13)],
        "ic": [round(met_mes[(v, m)]["ic"], 4) for m in range(1, 13)],
        "sen": [round(met_mes[(v, m)]["sen"], 4) for m in range(1, 13)],
        "sen_lo": [round(met_mes[(v, m)]["sen_lo"], 4) for m in range(1, 13)],
        "sen_hi": [round(met_mes[(v, m)]["sen_hi"], 4) for m in range(1, 13)],
        "q": [round(met_mes[(v, m)]["q"], 4) for m in range(1, 13)],
        "q_mk": [round(met_mes[(v, m)]["q_mk"], 4) for m in range(1, 13)]}
    for v in LARGO_VARS}, ensure_ascii=False)
pend_botones = "\n".join(
    f'    <button type="button" role="tab" id="pestana-pend-v{i}" aria-controls="panel-pend" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>{v}</button>'
    for i, v in enumerate(LARGO_VARS))
_mes_lista = lambda ms: ", ".join(MESES_LARGOS_ES[m - 1] for m in ms) if ms else "ninguno"
fdr_filas = "\n".join(
    f"<tr><td><b>{v}</b></td><td>{len(inc_fdr[v]['sin'])}</td><td><b>{len(inc_fdr[v]['ols'])}</b> "
    f"<small>({_mes_lista(inc_fdr[v]['ols'])})</small></td><td>{len(inc_fdr[v]['mk'])}</td></tr>" for v in LARGO_VARS)

marzo_html = "".join(
    f"  <p><b>{MESES_LARGOS_ES[m - 1].capitalize()} es el único mes de la lluvia que resiste la corrección</b>: con PL*, "
    f"{r['pend']:+.0f} mm/mes por década (q = {r['q']:.3f}). Sube en las {r['suben']} estaciones de la red fija, ningún año "
    f"suelto lo explica (quitando cualquiera, p ≤ {r['p_jk']:.4f}) y su promedio crece década tras década ("
    + ", ".join(f"{d}–{d + 9}: {n(v)} mm" for d, v in r['decadas'].items())
    + f"). PI apunta en el mismo sentido ({r['pi']['ols']:+.0f} mm/mes por década, p {_p_txt(r['pi']['p'])}), pero con "
    f"{r['pi']['n']} años no resiste la corrección; el caudal de {MESES_LARGOS_ES[m - 1]} no lo acompaña "
    f"({r['q_mes']['ols']:+.1f} m³/s por década, p {_p_txt(r['q_mes']['p'])}).</p>"
    for m, r in inc_lluvia_fdr.items())

# frecuencias (Fourier): tablas y datos de la gráfica


def _fou_fila_de(nombre, e, ar1):
    b = e["bandas"]
    dec = 1 if e["dT"] < 1 else 0
    return (f"<tr><td>{nombre}</td><td class='num'>{e['N']}</td><td class='num'>{e['n']}</td>"
            f"<td class='num'>{e['pico']:.{dec}f} ± {e['dT']:.{dec}f}</td><td class='num'>{e['ciclos']:.1f}</td>"
            f"<td class='num'>{b['anual']:.1f}&nbsp;%</td><td class='num'>{b['semianual']:.1f}&nbsp;%</td>"
            f"<td class='num'>{b['interanual']:.1f}&nbsp;%</td><td class='num'>{b['alta']:.1f}&nbsp;%</td>{ar1}</tr>")


def _fou_fila(ven, v, tipo):
    e = fou[(ven, v, tipo)]
    ar1 = f"<td class='num'>{_p_txt(e['ar1_p'])}</td>" if "ar1_p" in e else ""
    return _fou_fila_de(f"<b>{v}</b>", e, ar1)


def _fou_fila_oni(ven, tipo):
    """El ONI, de referencia: la misma fila en las tres pestañas, porque el ONI ya es una anomalía."""
    ar1 = "<td class='num'>—</td>" if tipo == "anomalía sin tendencia" else ""
    return _fou_fila_de("<b>ONI</b> <small>(referencia)</small>", fou_oni[ven], ar1)


def _fou_tablas(ven):
    """Una tabla por versión de la serie; las pestañas de arriba muestran una y esconden las otras. La columna del ruido
    rojo solo existe en «anomalía sin tendencia», la única versión en que se calcula."""
    bloques = []
    for i, tipo in enumerate(FOU_TRANSFORMACIONES):
        ar1 = '<th class="num">Pico contra ruido rojo (p)</th>' if tipo == "anomalía sin tendencia" else ""
        filas = "\n".join([_fou_fila(ven, v, tipo) for v in FOU_VENTANAS[ven]] + [_fou_fila_oni(ven, tipo)])
        bloques.append(
            f'  <div class="tabla-caja fou-tabla" data-tipo="{i}" role="tabpanel" aria-labelledby="pestana-foutab-{i}"'
            f'{"" if i == 0 else " hidden"}>\n'
            '  <table class="sin-destacar">\n'
            '    <thead><tr><th>Variable</th><th class="num">N (meses)</th><th class="num">Con dato</th>'
            '<th class="num">Pico ± ΔT (meses)</th>\n    <th class="num">Ciclos observados</th><th class="num">Anual</th>'
            '<th class="num">Semianual</th><th class="num">Interanual (3–7 años)</th>\n'
            f'    <th class="num">Alta (&lt; 6 meses)</th>{ar1}</tr></thead>\n'
            f"    <tbody>\n{filas}\n    </tbody>\n  </table>\n  </div>")
    return "\n".join(bloques)


fou_tablas = _fou_tablas("común 1998–2022")
fou_tablas_ext = _fou_tablas("extendida 1981–2022")
fou_botones_tabla = "\n".join(
    f'    <button type="button" role="tab" id="pestana-foutab-{i}" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>{t}</button>'
    for i, t in enumerate(FOU_TRANSFORMACIONES))
_fou_datos = {
    ven: {v: {t: {"f": [round(float(x), 5) for x in fou[(ven, v, t)]["f"]],
                  "p": [round(float(x), 4) for x in fou[(ven, v, t)]["p"]]}
              for t in FOU_TRANSFORMACIONES} for v in series}
    for ven, series in FOU_VENTANAS.items()}
for _ven in _fou_datos:
    _fou_datos[_ven]["ONI"] = {t: {"f": [round(float(x), 5) for x in fou_oni[_ven]["f"]],
                                   "p": [round(float(x), 4) for x in fou_oni[_ven]["p"]]} for t in FOU_TRANSFORMACIONES}
fou_json = json.dumps(_fou_datos, ensure_ascii=False)
fou_botones_tipo = "\n".join(
    f'    <button type="button" role="tab" id="pestana-fou-t{i}" aria-controls="panel-fou" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>{t}</button>'
    for i, t in enumerate(FOU_TRANSFORMACIONES))
fou_botones_ven = "\n".join(
    f'    <button type="button" role="tab" id="pestana-fou-v{i}" aria-controls="panel-fou" '
    f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else ' tabindex="-1"'}>Ventana {ven}</button>'
    for i, ven in enumerate(FOU_VENTANAS))
_fc = "común 1998–2022"

# estabilidad frente a la ventana: solo cuentan las variables en que Welch usa más de un segmento
_fou_comparables = {v: r for v, r in fou_sens.items() if not r["un_segmento"]}
_fou_un_segmento = {v: r for v, r in fou_sens.items() if r["un_segmento"]}
fou_sens_txt = "; ".join(f"{v}: Hann {r['hann']:.1f} y Welch {r['welch']:.1f} meses" for v, r in _fou_comparables.items())
fou_inestables = {v: r for v, r in _fou_comparables.items() if not r["hann_welch_estable"]}
fou_ventana_txt = (
    ("Coinciden dentro de la resolución, salvo en " + "; ".join(
        f"{v}: con Hann el máximo queda en {r['hann']:.1f} meses y con Welch en {r['welch']:.1f}, así que ese máximo depende de la "
        "ventana y no se lee como un período estable" for v, r in fou_inestables.items()) + ".")
    if fou_inestables else "Coinciden dentro de la resolución en todas.")
fou_ventana_txt += "".join(
    f" En {v}, cuyo tramo continuo más largo tiene {r['tramo']} meses (menos que un segmento), Welch se reduciría al mismo "
    f"periodograma de Hann; en su lugar se promedia el periodograma de Lomb-Scargle de {r['tramos_lomb']} tramos de "
    f"{FOU_WELCH_SEGMENTO} meses que se traslapan la mitad, sobre toda la serie con sus vacíos (el tramo más incompleto tiene "
    f"{r['min_obs_lomb']} meses con dato): pico en {r['welch']:.1f} meses, contra {r['hann']:.1f} de Hann en el tramo de "
    f"{r['tramo']} meses. " + ("Coinciden dentro de la resolución." if r["hann_welch_estable"]
                              else "No coinciden: ese máximo depende del estimador y no se lee como un período estable.")
    for v, r in _fou_un_segmento.items())
# extremos: cuántos meses se quitaron en cada variable; donde no se quitó ninguno, la prueba no dice nada
_fou_cuantos = [f"{r['extremos']} {'mes' if r['extremos'] == 1 else 'meses'} de {v}" for v, r in fou_sens.items()]
fou_extremos_txt = ", ".join(_fou_cuantos[:-1]) + " y " + _fou_cuantos[-1]
_fou_sin_extremos = [v for v, r in fou_sens.items() if r["extremos"] == 0]
_fou_mueven_ext = {v: r for v, r in fou_sens.items() if not r["extremos_estable"]}
fou_extremos_efecto = (
    "no mueve el pico de ninguna anomalía" if not _fou_mueven_ext else
    "mueve el pico de la anomalía en " + "; ".join(
        f"{v}, de {fou[(_fc, v, 'anomalía')]['pico']:.0f} a {r['pico_sin_extremos']:.0f} meses" for v, r in _fou_mueven_ext.items())
    + " (ese pico depende de unos pocos meses), y no lo mueve en las demás")
fou_extremos_nada = (f" En {' y '.join(_fou_sin_extremos)} no hubo nada que quitar, así que ahí la prueba no dice nada."
                     if _fou_sin_extremos else "")
# tendencia: el reparto por bandas casi no cambia, pero el pico más alto de algunas anomalías sí se mueve
_fou_mueve_tend = [(ven, v, t) for (ven, v), t in fou_tendencia.items() if t["mueve"]]
_fou_signif_tend = [v for ven, v in fou_significativos if fou_tendencia[(ven, v)]["mueve"]]
(_fou_tmax_ven, _fou_tmax_v), _fou_tmax = fou_tendencia_max
fou_tendencia_txt = (
    f"Quitar la tendencia casi no cambia el reparto de la varianza por bandas: como mucho {_fou_tmax['puntos']:.1f} puntos "
    f"porcentuales ({_fou_tmax_v}, ventana {_fou_tmax_ven}).")
if _fou_mueve_tend:
    fou_tendencia_txt += (
        " Sí mueve el pico más alto de la anomalía en " + "; ".join(
            f"{v} (ventana {ven}), de {t['antes']:.0f} a {t['despues']:.0f} meses" for ven, v, t in _fou_mueve_tend)
        + ": son picos de muy baja frecuencia, con pocos ciclos en el registro, justo donde una tendencia pesa más, así que no "
        "se leen como períodos.")
    if _fou_signif_tend:
        fou_tendencia_txt += (f" El pico de {' y '.join(_fou_signif_tend)} que supera el ruido rojo es uno de ellos: solo aparece "
                              "al quitar la tendencia.")
else:
    fou_tendencia_txt += " Tampoco mueve el pico más alto de ninguna anomalía."
# vacíos de Q: el texto dice si distorsionan o no según el criterio declarado en 18
_fv = {k: fou_vacios[k] for k in ("original", "anomalía")}
_fv_mueve = [k for k, r in _fv.items() if r["mueve"]]
_fv_bandas = [k for k, r in _fv.items() if r["puntos"] >= FOU_TENDENCIA_MAX_PUNTOS]
fou_vacios_txt = (
    f"¿Distorsionan el espectro los {fou_vacios['meses']} meses vacíos de Q? Se calcula el de PL dejando vacíos esos mismos meses y se "
    "compara con el de PL completa. "
    + ("El pico no se mueve, ni en la serie original ni en la anomalía. " if not _fv_mueve else
       "El pico se mueve en " + "; ".join(f"la {k} (de {_fv[k]['antes']:.0f} a {_fv[k]['despues']:.0f} meses)" for k in _fv_mueve) + ". ")
    + ("Las bandas tampoco cambian más de " + f"{FOU_TENDENCIA_MAX_PUNTOS:.0f} puntos porcentuales." if not _fv_bandas else
       "Las bandas sí cambian: " + "; ".join(
           f"en la {k}, la {_fv[k]['banda']} pasa de {_fv[k]['sin']:.1f} a {_fv[k]['con']:.1f} %" for k in _fv_bandas)
       + f". Así que los vacíos no mueven los picos de Q, pero sus porcentajes por banda pueden estar corridos en unos "
         f"{max(_fv[k]['puntos'] for k in _fv_bandas):.0f} puntos por los vacíos.")
    + " Es una prueba indirecta: supone que los vacíos afectarían al caudal como afectan a la lluvia.")
# ¿cuadra con el ENSO?: tabla de coherencia y fase, y textos (cada afirmación protegida en 18 o redactada según el dato)
def _fou_rezago_txt(r):
    return f"{r['rezago']:.1f}" if r["lectura"] == "en fase" else "—"


fou_coh_filas = "\n".join(
    f"<tr><td><b>{a}–{b}</b></td><td>{ven}</td><td class='num'>{r['coh']:.2f}</td><td class='num'>{r['umbral']:.2f}</td>"
    f"<td>{'sí' if r['signif'] else 'no'}</td><td class='num'>{r['fase']:+.0f}°</td><td>{r['lectura']}</td>"
    f"<td class='num'>{_fou_rezago_txt(r)}</td></tr>"
    for (ven, a, b), r in fou_coh.items())
_fou_cq = [(ven, a, r) for (ven, a, b), r in fou_coh.items() if b == "Q"]
fou_coh_q_txt = "; ".join(f"{r['coh']:.2f} entre {a} y Q (ventana {ven})" for ven, a, r in _fou_cq)
fou_coh_q_rezago = (min(r["rezago"] for _, _, r in _fou_cq), max(r["rezago"] for _, _, r in _fou_cq))


def _fou_signif_oni_txt(ven):
    pares = [(a, r) for (v, a, b), r in fou_coh.items() if v == ven and b == "ONI"]
    si = [f"{a}–ONI {r['coh']:.2f} contra un umbral de {r['umbral']:.2f}" for a, r in pares if r["signif"]]
    no = [f"{a}–ONI {r['coh']:.2f} contra {r['umbral']:.2f}" for a, r in pares if not r["signif"]]
    if not no:
        return f"En la ventana {ven} la coherencia con el ONI es significativa en todos los pares ({'; '.join(si)})."
    if not si:
        return f"En la ventana {ven} no es significativa en ningún par ({'; '.join(no)})."
    return f"En la ventana {ven} solo es significativa en {'; '.join(si)}; queda por debajo en {'; '.join(no)}."


_fou_ext_signif = all(r["signif"] for (v, a, b), r in fou_coh.items() if v == "extendida 1981–2022" and b == "ONI")
_fou_com_signif = all(r["signif"] for (v, a, b), r in fou_coh.items() if v == "común 1998–2022" and b == "ONI")
fou_coh_oni_txt = (_fou_signif_oni_txt("extendida 1981–2022") + " " + _fou_signif_oni_txt("común 1998–2022")
                   + (" Esa es la evidencia que el pico solo no daba: en el registro largo, la variabilidad interanual de la cuenca"
                      " va con el ENSO, aunque su período no sea fijo." if _fou_ext_signif else "")
                   + ("" if _fou_com_signif else " Con 25 años la señal no alcanza a separarse del ruido en todas las series."))
def _fou_rezago_oni(r):
    k = r["rezago"]
    return "en el mismo mes" if k == 0 else f"{k} {'mes' if k == 1 else 'meses'} después"


fou_corr_oni_txt = "; ".join(
    f"en la ventana {ven}, " + ", ".join(
        f"{v} {_fou_rezago_oni(r)} (r = {r['r']:.2f})" for (v2, v), r in fou_corr_oni.items() if v2 == ven)
    for ven in ("común 1998–2022", "extendida 1981–2022"))
fou_pico_corto_txt = (
    f"PL tiene un máximo en {fou_pico_corto['periodo']:.1f} meses con el {fou_pico_corto['PL']:.1f} % de la varianza de su anomalía. "
    f"Pero en espectros de ruido blanco con los mismos {fou[(_fc, 'PL', 'anomalía')]['N']} meses ({FOU_SIMULACIONES} simulaciones), "
    f"el pico más alto tiene en promedio el {fou_pico_corto['blanco_medio']:.1f} % (el 95 % de las veces, hasta el "
    f"{fou_pico_corto['blanco_95']:.1f} %): no se distingue del azar. En la misma frecuencia, PI tiene el {fou_pico_corto['PI']:.1f} %, "
    f"Q el {fou_pico_corto['Q']:.1f} % y T el {fou_pico_corto['T']:.1f} %.")

# qué se atenúa al retirar la climatología, y la comparación de PI con PL (cada afirmación protegida en 18)
fou_atenua_txt = "; ".join(f"{v}, del {fou_estacional[v]:.1f} al {fou_estacional_anom[v]:.1f} %" for v in FOU_VENTANAS[_fc])
_fc_pl, _fc_pi = fou_coh[(_fc, "PL", "ONI")], fou_coh[(_fc, "PI", "ONI")]
if _fc_pi["signif"] and not _fc_pl["signif"]:
    fou_fuentes_oni_txt = (f"Con el ONI, en la ventana común solo PI es coherente ({_fc_pi['coh']:.2f} contra un umbral de "
                           f"{_fc_pi['umbral']:.2f}); PL queda por debajo ({_fc_pl['coh']:.2f} contra {_fc_pl['umbral']:.2f}).")
elif _fc_pl["signif"] and not _fc_pi["signif"]:
    fou_fuentes_oni_txt = (f"Con el ONI, en la ventana común solo PL es coherente ({_fc_pl['coh']:.2f} contra un umbral de "
                           f"{_fc_pl['umbral']:.2f}); PI queda por debajo ({_fc_pi['coh']:.2f} contra {_fc_pi['umbral']:.2f}).")
else:
    fou_fuentes_oni_txt = (f"Con el ONI, en la ventana común las dos fuentes dan lo mismo: PL {_fc_pl['coh']:.2f} y PI "
                           f"{_fc_pi['coh']:.2f}, {'las dos' if _fc_pl['signif'] else 'ninguna'} por encima del umbral.")

# conclusión: las frases que dependen del resultado se redactan según el dato
_fou_ruido_rojo_txt = (
    "Ningún pico de las anomalías supera el ruido rojo de forma convincente"
    + "".join(f": el único, el de {v} en {fou[(ven, v, 'anomalía sin tendencia')]['pico']:.0f} meses, cabe {c:.0f} veces en el registro"
              + (" y solo aparece al quitar la tendencia" if v in _fou_signif_tend else "")
              for (ven, v), c in fou_signif_ciclos.items())
    + ".") if fou_significativos else "Ningún pico de las anomalías supera el ruido rojo."
_fou_ext = "extendida 1981–2022"
fou_conclusion_enso_txt = (
    (f"Pero la coherencia muestra que, en el registro largo, la lluvia y el caudal varían en oposición con el ONI (PL*–ONI "
     f"{fou_coh[(_fou_ext, 'PL*', 'ONI')]['coh']:.2f} y Q–ONI {fou_coh[(_fou_ext, 'Q', 'ONI')]['coh']:.2f}, ambas significativas): menos "
     f"agua en El Niño. Además, el ONI y PL* tienen su pico en la misma escala, unos {fou_plx_ext['pico']:.0f} meses."
     if _fou_ext_signif else
     "Y la coherencia con el ONI, aunque va en oposición, no es significativa en todos los pares ni siquiera en el registro largo.")
    + ("" if _fou_com_signif else " Con 25 años la señal está, pero no alcanza a separarse del ruido en todas las series."))

# ventana extendida: en las originales no mueve el pico (protegido en 18); en las anomalías, se nombra dónde lo mueve
fou_extendida_txt = (
    "En las anomalías sí cambia el pico de " + "; ".join(
        f"{v} ({tipo}), de {a:.0f} a {b:.0f} meses" for v, tipo, a, b in fou_extendida_anom_mueve)
    + ": los picos de baja frecuencia dependen de qué años entran en el registro."
    if fou_extendida_anom_mueve else "En las anomalías tampoco cambia ningún pico.")

# años que se salen de lo normal: tabla y datos de las dos gráficas
def _anom_z(v):
    return "sin año completo" if v is None else f"{v:+.2f}"


anom_filas = "\n".join(
    f"<tr><td><b>{a}</b> ({r['tipo']})</td><td class='num'>{r['z_pl']:+.2f}</td><td class='num'>{r['z_pi']:+.2f}</td>"
    f"<td class='num'>{_anom_z(r['z_q'])}</td><td class='num'>{n(r['pl'])}</td><td class='num'>{r['meses_sobre']} de 12</td>"
    f"<td>{' y '.join(r['picos'])}</td><td class='num'>{r['razon']:.2f}</td>"
    f"<td>{r['nina']} de La Niña, {r['nino']} de El Niño</td></tr>" for a, r in anom_anios.items())
_anom_nube = atip_z[["PL", "Q"]].dropna()
anom_json = json.dumps({
    "nube": {"pl": _anom_nube.PL.round(2).tolist(), "q": _anom_nube.Q.round(2).tolist(),
             "anio": [p.year for p in _anom_nube.index], "mes": [f"{MESES_LARGOS_ES[p.month - 1]} de {p.year}" for p in _anom_nube.index]},
    "anios": {str(a): {"tipo": r["tipo"], "serie": r["serie"], "pi": anom_pl_pi[a]["pi"]} for a, r in anom_anios.items()},
    "mediana": [round(float(v), 1) for v in anom_mediana_pl],
    "meses": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
}, ensure_ascii=False)

# «Explicaciones físicas»: la tabla de la clasificación mensual y las frases que dependen del dato (las afirmaciones
# están protegidas con assert en el bloque «explicaciones físicas» de 18)
def _rango_txt(a, b, dec=2):
    """«1.40–1.91», o un solo número si los dos extremos se escriben igual."""
    return f"{a:.{dec}f}" if f"{a:.{dec}f}" == f"{b:.{dec}f}" else f"{a:.{dec}f}–{b:.{dec}f}"


_mes_minimo_pl = MESES_LARGOS_ES.index(regimen["PL"]["min"]) + 1
clas_filas = "\n".join(
    f"<tr><td><b>{r['clase'].capitalize()}</b></td><td>{r['nombre']}</td>"
    f"<td>{'sobre' if r['clase'] == 'húmedo' else 'bajo'} el mes típico"
    f"{'; el mínimo es ' + regimen['PL']['min'] if _mes_minimo_pl in r['meses'] else ''}"
    f" ({n(r['mediana_pl'][0])}–{n(r['mediana_pl'][1])})</td>"
    f"<td class='num'>{_rango_txt(*r['pe']['pl'])} / {_rango_txt(*r['pe']['pi'])}</td>"
    f"<td class='num'>{r['deficit_max']['pl']} / {r['deficit_max']['pi']}</td>"
    f"<td>{'sobre' if r['clase'] == 'húmedo' else 'bajo'} su mes típico en {r['q_nombre']}"
    f"{'; mínimo en ' + regimen['Q']['min'] if r['q_minimo'] else ''}</td></tr>"
    for r in clas_tabla)
# la temporada «seco relativo»: el mes de menor mediana de PL, para compararlo con el mínimo del año
_sr = clas_fila["seco relativo"]
fis_sr_mes_min = MESES_LARGOS_ES[min(_sr["meses"], key=lambda m: regimen["PL"]["medianas"][m - 1]) - 1]
# los meses en que P − Q supera a la ETP (con PL), con el nombre completo
fis_meses_guarda = nombre_meses([MESES_ES.index(m) + 1 for m in pq_meses_guarda])
# los meses de temporada húmeda que PI deja sin clase, y por qué
_razones_pi = {m: [x for x, c in ((f"P/ETP {pe_mes.loc[m, 'pi']:.2f}", pe_mes.loc[m, "pi"] < CLAS_PE_HUMEDO),
                                  (f"déficit en {pe_mes_deficit_anios.loc[m, 'pi']} "
                                   f"{'año' if pe_mes_deficit_anios.loc[m, 'pi'] == 1 else 'años'}",
                                   pe_mes_deficit_anios.loc[m, "pi"] > CLAS_MAX_ANIOS_DEFICIT)) if c]
               for m in clas_pi_sin_clase}
clas_pi_sin_clase_txt = (
    (f" Con los mismos criterios, PI deja sin clase a {_y_lista([MESES_LARGOS_ES[m - 1] for m in clas_pi_sin_clase])}, "
     f"meses de su temporada húmeda que no cumplen los umbrales ("
     + "; ".join(f"{MESES_LARGOS_ES[m - 1]}: {' y '.join(r)}" for m, r in _razones_pi.items()) + ").")
    if clas_pi_sin_clase else " Con los mismos criterios, PI clasifica todos los meses.")
fis_coef_txt = (f"entre el {min(fis_coef.values()) * 100:.0f} % ({'PL' if fis_coef['pl'] < fis_coef['pi'] else 'PI'}) "
                f"y el {max(fis_coef.values()) * 100:.0f} % ({'PI' if fis_coef['pl'] < fis_coef['pi'] else 'PL'})")
fis_sobre1_txt = (f"en {len(fis_sobre1_meses)} meses, {'todos de las temporadas secas' if fis_sobre1_en_secos else 'no todos de las temporadas secas'}, "
                  "sale por el río más agua de la que cae")
# abril, el mes siguiente a marzo, en Q
_q_abril = met_mes[("Q", 4)]
fis_q_abril_txt = (f"En abril, el mes siguiente, Q tampoco tiene tendencia significativa ({_q_abril['ols']:+.1f} m³/s por década, "
                   f"p = {_p_txt(_q_abril['p'])})." if _q_abril["p"] >= TEND_ALFA else
                   f"En abril, el mes siguiente, Q sí tiene tendencia ({_q_abril['ols']:+.1f} m³/s por década, p = {_p_txt(_q_abril['p'])}).")
_ev_pl, _ev_pi = ev_tabla["PL del mismo mes"]["validacion"]["rmse"], ev_tabla["PI del mismo mes"]["validacion"]["rmse"]

# Cabecera estándar: sin el charset, algunos navegadores leen mal las tildes al abrir el archivo directamente;
# sin el viewport, el celular dibuja la página a ancho de computador y la muestra diminuta.
pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte cuenca del Fonce</title>
<meta name="author" content="{html.escape(", ".join(AUTORES))}">
<script>{PLOTLY_JS}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --fondo: #F5F7F6; --superficie: #FFFFFF; --tinta: #17211E; --tenue: #56645F; --linea: #D5DDDA;
  --acento: #1B6A80; --acento-suave: #E2EFF2; --placa: #FFFFFF; --atip-alto: #F7D9C4; --atip-bajo: #CFE3F2; --nino: #B8321F; --nina: #1C63A8; --revision: #E6EAE8; --revision-borde: #4E5955; --anotado: #FFF4C2; --cambio: #E2F3E0; --cambio-borde: #2E7D32;
  --f-titulo: "Archivo", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --f-texto: "Source Serif 4", Georgia, "Times New Roman", serif;
  --f-dato: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
    --acento: #72B9CE; --acento-suave: #1C2D32; --placa: #F4F6F5; --atip-alto: #5A3420; --atip-bajo: #1F3A52; --nino: #F2836B; --nina: #6FB4EE; --revision: #262E2C; --revision-borde: #B4BFBB; --anotado: #37300F; --cambio: #16301B; --cambio-borde: #7BC67F;
  }}
}}
:root[data-theme="dark"] {{
  --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
  --acento: #72B9CE; --acento-suave: #1C2D32; --placa: #F4F6F5; --atip-alto: #5A3420; --atip-bajo: #1F3A52; --nino: #F2836B; --nina: #6FB4EE; --revision: #262E2C; --revision-borde: #B4BFBB; --anotado: #37300F; --cambio: #16301B; --cambio-borde: #7BC67F;
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
.plegable-mini {{ margin: 8px 0; }}
.plegable-mini > summary {{ cursor: pointer; font: 500 14px/1.4 var(--f-dato); padding: 4px 0; }}
.plegable > summary:focus-visible {{ outline: 2px solid var(--acento); outline-offset: 4px; border-radius: 4px; }}
.plegable-pista {{ font: 400 12px/1 var(--f-dato); color: var(--tenue); letter-spacing: .04em; }}
.sin-destacar tbody tr:first-child td {{ background: none; font-weight: 400; }}
.tratamiento {{ max-width: 66ch; padding-left: 20px; margin: 0; font-size: 15px; }}
.tratamiento li {{ margin-bottom: 6px; }}
.fase-nino {{ color: var(--nino); font-weight: 600; }}
.tratamiento .lectura {{ margin: 6px 0 0; }}
/* lo agregado o cambiado en esta rama va resaltado en gris para revisión (etiqueta en data-etiqueta) */
.revision {{ background: var(--revision); border-left: 4px solid var(--revision-borde); padding: 10px 14px;
  margin: 14px 0; border-radius: 0 4px 4px 0; }}
.revision > p {{ margin: 0 0 8px; }}
.revision > p:last-child {{ margin-bottom: 0; }}
.revision::before {{ content: attr(data-etiqueta); display: block; font: 600 11px/1.4 var(--f-dato);
  letter-spacing: .06em; text-transform: uppercase; color: var(--revision-borde); margin-bottom: 6px; }}
.cambio {{ background: var(--cambio); border-left: 4px solid var(--cambio-borde); padding: 10px 14px;
  margin: 14px 0; border-radius: 0 4px 4px 0; }}
.cambio > p {{ margin: 0 0 8px; }}
.cambio > p:last-child {{ margin-bottom: 0; }}
.cambio::before {{ content: attr(data-etiqueta); display: block; font: 600 11px/1.4 var(--f-dato);
  letter-spacing: .06em; text-transform: uppercase; color: var(--cambio-borde); margin-bottom: 6px; }}
.formula {{ font: 500 16px/1.5 var(--f-dato); margin: 4px 0 12px; overflow-wrap: anywhere; }}
td.res-revisar, .sin-destacar tbody tr:first-child td.res-revisar {{ background: var(--atip-alto); font-weight: 600; }}
td.res-anotado {{ background: var(--anotado); }}
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
.resumen-caja {{ border: 2px solid var(--acento); border-radius: 8px; padding: 6px 16px 12px; margin: 22px 0; background: var(--superficie); }}
.resumen-caja h3 {{ margin-top: 10px; }}
.resumen-caja table {{ font-size: 15px; }}
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
  <div{revision("autores")}>
    <p class="intro"><b>Autores:</b> {html.escape(", ".join(AUTORES))}</p>
    <p class="intro"><b>Profesor:</b> {html.escape(PROFESOR)}</p>
  </div>
  <p class="intro">Santander, Colombia. Estación de aforo IDEAM {24027010} en San Gil, con cinco subcuencas anidadas que también tienen caudal medido.</p>
  <div class="cifras">
    <div class="cifra"><b>{n(sg['area'])} km²</b><span>área de drenaje</span></div>
    <div class="cifra"><b>{n(elev_min)}–{n(elev_max)} m</b><span>rango de elevación (DEM)</span></div>
    <div class="cifra"><b>{n(elev_media)} m</b><span>elevación media (DEM)</span></div>
    <div class="cifra"><b>{n(p_imerg[24027010])} mm</b><span>lluvia anual IMERG 1998–2022</span></div>
  </div>
</header>

<div{revision("colores unificados en todas las figuras")}>
  <p class="nota">{nota_colores}</p>
</div>

<section>
  <h2>Contexto geográfico</h2>
  <p>La cuenca del Fonce está en Santander, en el flanco occidental de la <b>cordillera Oriental</b> de Colombia, el
  que mira al valle del Magdalena. El centroide de su polígono queda en {centroide_lat:.2f}° N,
  {abs(centroide_lon):.2f}° W.</p>
  <p><b>A sotavento de los alisios.</b> En las laderas que reciben los vientos alisios de frente, a barlovento, la
  lluvia tiende a ser mucho mayor que en sus vecinas del lado opuesto, a sotavento: del orden del doble
  ({CITA_MESA_P90}). Los alisios llegan del oriente, y la mayor parte de la cuenca está en el flanco occidental de la
  cordillera, a sotavento. De ahí sale una hipótesis que este trabajo no comprueba: la vertiente oriental de la
  cordillera, la que mira a los Llanos, debería recibir bastante más lluvia que el Fonce. La vecina inmediata al
  oriente, la vertiente del Chicamocha, no sirve para compararla, porque también es interandina.</p>

  <h3>La cuenca y sus subcuencas</h3>
  <p>El Fonce nace en el páramo al sureste (hasta {n(elev_max)} m) y corre hacia el norte por un valle ancho hasta San Gil.
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
  <p class="nota">Área: la del polígono de cada cuenca, calculada por el proyecto (geodésica). Elevación: atributos de
  CAMELS-COL. Lluvia: promedio de los totales anuales de IMERG mensual (1998–2022) ponderado por área sobre cada subcuenca.</p>
</section>

<section>
  <h2>En esta cuenca llueve menos arriba</h2>
  <p>Contra la intuición, las estaciones más altas de la red miden <b>menos</b> lluvia que varias del valle:
  <b>{html.escape(grad_mas_alta.nombre_corto)}</b>, a {n(grad_mas_alta.altitud)} m, registra
  {n(grad_mas_alta.p_anual_mm)} mm/año, y <b>{html.escape(grad_mas_lluviosa.nombre_corto)}</b>,
  {n(grad_mas_alta.altitud - grad_mas_lluviosa.altitud)} m más abajo, {n(grad_mas_lluviosa.p_anual_mm)} mm/año. Con
  {aj_plu['n']} estaciones podría ser casualidad, así que se contrasta con algo independiente.</p>

  <p>Ese algo es <b>IMERG cruzado contra el DEM</b>: la altitud media de cada una de las {aj_imerg['n']}
  celdas que tocan la cuenca, pesada por la fracción de su área dentro de ella. Es una muestra más densa e
  independiente de dónde están los pluviómetros. <b>Las dos fuentes coinciden en el signo.</b></p>

  <div class="cifras" style="margin: 18px 0 6px">
    <div class="cifra"><b>{aj_imerg['por_1000m']:+,.0f} mm/año</b><span>por cada 1 000 m · IMERG</span></div>
    <div class="cifra"><b>r² = {aj_imerg['r2']:.2f}</b><span>IMERG, {aj_imerg['n']} celdas</span></div>
    <div class="cifra"><b>{aj_plu['por_1000m']:+,.0f} mm/año</b><span>por cada 1 000 m · pluviómetros</span></div>
    <div class="cifra"><b>r² = {aj_plu['r2']:.2f}</b><span>pluviómetros, {aj_plu['n']} estaciones</span></div>
  </div>

  <div id="g-gradiente" class="grafico" style="min-height:460px"></div>
  <p class="nota">Azul: celdas de IMERG, más grandes cuanto más pesan en el ajuste. Naranja: pluviómetros; el
  círculo hueco es la estación fuera de la divisoria.</p>

  <h3>Las mismas estaciones, apartando las dos que no encajan</h3>
  <p>Dos estaciones tiran de la recta naranja: <b>{html.escape(grad_mas_lluviosa.nombre_corto)}</b> mide muy por
  encima de lo esperable (aun sin su tramo 2016-2018, ya excluido; ver «Comparando PI con PL»), y <b>{html.escape(grad_mas_seca.nombre_corto)}</b>,
  con {n(grad_mas_seca.p_anual_mm)} mm/año a {n(grad_mas_seca.altitud)} m, mide <b>menos que
  {html.escape(grad_mas_alta.nombre_corto)}</b>, {n(grad_mas_alta.altitud - grad_mas_seca.altitud)} m más arriba, algo
  que la altitud sola no explica.</p>

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

  <p><b>Sin ellas, las dos rectas se acercan</b>: {aj_limpio['por_1000m']:+,.0f} mm/año por cada 1 000 m con los
  pluviómetros y {aj_imerg['por_1000m']:+,.0f} con el satélite, {n(grad_brecha)} mm/año de diferencia contra
  {n(grad_brecha_7)} con las {aj_plu['n']} estaciones: <b>esas dos explican el {grad_parte_de_las_dos:.0f} % de la
  discrepancia</b>. Las dos pendientes dicen menos lluvia arriba, aunque la de los pluviómetros es débil
  (r² = {aj_limpio['r2']:.2f}).</p>

  <p class="aviso">Esto no autoriza a borrarlas. Lo de {html.escape(grad_mas_lluviosa.nombre_corto)} apunta a un
  problema de la serie; lo de {html.escape(grad_mas_seca.nombre_corto)} puede ser un efecto real de ladera, el
  tipo de detalle que IMERG borra al promediar sobre celdas de 122 km². Excluirlas escondería información.</p>

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
  {n(sub_seca.p_anual)} mm/año. Un mínimo entre dos estaciones más húmedas <b>de su
  propia subcuenca</b>, una más abajo y otra más arriba, no lo produce un gradiente con la altura.</p>

  <p class="aviso">Lo que más pesa: <b>IMERG ve las dos subcuencas casi idénticas</b>
  ({n(sub_humeda.p_imerg_subcuenca)} contra {n(sub_seca.p_imerg_subcuenca)} mm/año, {n(sub_brecha_imerg)} de
  diferencia), y los pluviómetros dicen {n(sub_humeda.p_anual)} contra {n(sub_seca.p_anual)}, un
  <b>{sub_brecha_plu * 100:.0f} %</b> de diferencia entre dos subcuencas contiguas, de tamaño y elevación
  parecidos. Eso deja a {html.escape(sub_humeda.etiqueta)} como el principal candidato a revisión.</p>

  <h3>La lluvia contra la altura</h3>
  <p>De las celdas más bajas de IMERG (unos {n(grad_alt_baja)} m, {n(grad_p_baja)} mm/año) a las más altas
  ({n(grad_alt_alta)} m, {n(grad_p_alta)} mm/año) se pierden unos <b>{n(grad_caida)} mm/año</b>. Por qué la lluvia
  disminuye con la altura en esta cuenca se explica en «Explicaciones físicas» (el óptimo pluviográfico).</p>

  <div class="tabla-caja">
  <table>
    <thead><tr><th>Estación</th><th class="num">Altitud (m)</th><th class="num">Lluvia (mm/año)</th><th>Divisoria</th></tr></thead>
    <tbody>
{filas_grad}
    </tbody>
  </table>
  </div>

  <p class="nota">Las pendientes difieren: {aj_imerg['por_1000m']:+,.0f} mm/año por cada 1 000 m con IMERG,
  {aj_limpio['por_1000m']:+,.0f} con los pluviómetros sin las dos apartadas y {aj_plu['por_1000m']:+,.0f} con las
  {aj_plu['n']}. Si hiciera falta corregir la lluvia por altura, habría que declarar cuál se usa y por qué.</p>
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
      <p>Los <b>{len(DENTRO)} pluviómetros</b> dentro de la divisoria, con su altitud, van de
      {html.escape(mapa_plu_baja.etiqueta)} ({n(mapa_plu_baja.altitud)} m), en el fondo del valle, a
      {html.escape(mapa_plu_alta.etiqueta)} ({n(mapa_plu_alta.altitud)} m). <b>Ninguno llega al páramo</b>: por
      encima de {n(mapa_plu_alta.altitud)} m, donde está el {mapa_pct_sin_pluvio:.0f} % de la cuenca, no se mide la lluvia.</p>
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
      <p>IMERG trabaja con píxeles de 0.1° (unos {mapa_km_lado:.0f} km de lado). La lluvia de la cuenca es el promedio de los
      píxeles que la tocan, ponderado por la fracción de cada uno dentro (el número rotulado).</p>
      <dl class="lista-datos">
        <dt>Píxeles que tocan la cuenca</dt><dd>{n_pix}</dd>
        <dt>Con más de la mitad dentro</dt><dd>{n_mitad}</dd>
        <dt>Totalmente dentro</dt><dd>{n_llenos}</dd>
        <dt>Lluvia media anual</dt><dd>{n(p_dmin)}–{n(p_dmax)} mm/año (píxeles con más de la mitad dentro)</dd>
      </dl>
      <p>Según IMERG, llueve más en el valle del oeste que en el páramo del sureste.</p>
      <p class="aviso">Con cautela: IMERG se corrige con pluviómetros, y aquí ninguno pasa de {n(mapa_plu_alta.altitud)} m, así que
      la parte alta no tiene con qué contrastarse.</p>
      <p class="nota">Monchía ({n(mapa_area_chicas['Monchía'])} km²) y Mogoticos ({n(mapa_area_chicas['Mogoticos'])} km²) miden
      {mapa_area_chicas['Monchía'] / mapa_km2_pixel:.1f} y {mapa_area_chicas['Mogoticos'] / mapa_km2_pixel:.1f} píxeles de IMERG
      (unos {n(mapa_km2_pixel)} km² cada uno): IMERG no ve variaciones de la lluvia dentro de ellas.</p>
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
      <p><b>De un extremo al otro de la cuenca hay {t_max_mitad - t_min_mitad:.1f} °C de diferencia</b>
      ({t_max_mitad:.1f} °C en el valle del noroeste y {t_min_mitad:.1f} °C en el páramo del sur, en los píxeles con más
      de la mitad dentro): {(t_max_mitad - t_min_mitad) / mapa_t_amplitud_anual:.0f} veces la diferencia entre el mes más
      cálido y el más frío ({mapa_t_amplitud_anual:.1f} °C). <b>Aquí la temperatura la manda la altura, no el
      calendario</b>: por eso se usa ERA5-Land, de malla más fina que ERA5. El patrón es el del relieve: los píxeles
      cálidos siguen el valle del Fonce y los fríos se acumulan en la mitad sureste, la más alta.</p>
      <p class="nota">El promedio ponderado del mapa ({t_ponderada:.2f} °C) y la serie diaria de la cuenca
      ({t_serie_media:.2f} °C) difieren en {abs(t_ponderada - t_serie_media):.2f} °C, el error de tomar el centro de cada
      píxel en vez de integrar sobre el polígono. Con los píxeles que solo rozan la cuenca el rango llega a
      {t_min_px:.1f}–{t_max_px:.1f} °C, pero describen terreno de afuera: el más cálido tiene apenas el
      {mapa_pct_px_calido:.0f} % de su área dentro.</p>
      <p class="aviso">La malla de ERA5-Land tiene el paso de la de IMERG pero <b>corrida medio píxel</b> (centros en
      múltiplos de 0.1° contra los terminados en 0.05°): por eso son {t_npix} píxeles aquí y {n_pix} allá.</p>
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
  <p>Las dos fuentes de lluvia: <b>PI</b>, la de IMERG, que el satélite estima sobre celdas de unos
  {n(mapa_km2_pixel)} km², y <b>PL</b>, el promedio de los <b>{len(DENTRO)} pluviómetros</b> del IDEAM dentro de la
  divisoria (datos <b>preliminares</b>), con los que tengan dato cada mes, sin rellenar. En las gráficas, los
  pluviómetros sueltos van tenues y su promedio a plena opacidad.</p>
  <p class="aviso"><b>De PL se excluyen 2016, 2017 y 2018 de Encino</b> ({exc_meses} meses): sus totales saltan a
  {n(enc_raros[2016])}, {n(enc_raros[2017])} y {n(enc_raros[2018])} mm, contra unos {n(enc_normal)} en el resto de su
  serie, y nada más acompaña el salto (en 2017, PL sale {exc_2017['crudo']:+.1f} % sobre su promedio con esos años y
  {exc_2017['depurado']:+.1f} % sin ellos, mientras PI sale {exc_2017['pi']:+.1f} %). Es un problema de registro.</p>
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
  <p><b>Las dos fuentes cuentan la misma historia con distinta magnitud:</b> coinciden en la forma del ciclo
  anual y mes a mes (correlación {cmp_stats[NOM_RED]["r"]:.2f}), pero <b>PI queda un
  {abs(cmp_stats[NOM_RED]["sesgo"]):.1f} % por debajo de PL</b> ({n(cmp_stats[NOM_RED]["imerg"])} contra
  {n(cmp_stats[NOM_RED]["pluv"])} mm/mes). Los pluviómetros sueltos van de
  {n(min(v["pluv"] for k, v in cmp_stats.items() if k != NOM_RED))} a
  {n(max(v["pluv"] for k, v in cmp_stats.items() if k != NOM_RED))} mm/mes, porque la lluvia cambia de ladera a
  ladera: por eso se usa su promedio.</p>

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
  <p class="nota">Cada punto es un mes. El sesgo conserva el signo del error, el MAE es su tamaño típico y el RMSE
  pesa más las diferencias grandes. Que el MAE sea mucho mayor que el sesgo dice que PI, además de quedarse corto
  en promedio, se aleja de PL hacia los dos lados.</p>
  <p class="aviso"><b>Se usan las dos en paralelo; cuando hay que escoger, manda PL</b>, porque mide la lluvia en
  la cuenca. Su límite: {len(DENTRO)} puntos sin validar para {n(AREA_SG_KM2)} km² de montaña, ninguno en el páramo.
  PI sirve de contraste y cubre toda la cuenca los {len(comp)} meses, sin huecos.</p>
</section>

<section>
  <h2>Qué meses tienen dato y cuáles no</h2>
  <p>Cada franja es un mes de una fuente, y en las series diarias su color es el <b>porcentaje de días del mes
  con registro</b>: así se distingue un mes completo de uno al que le faltan unos días.</p>
  <p class="nota"><b>PI</b>: lluvia de IMERG sobre la cuenca. <b>PL</b>: la de los pluviómetros del IDEAM dentro de
  la divisoria (su promedio o cada uno). <b>Q</b>: caudal en San Gil. <b>ETP</b>: evapotranspiración potencial de
  Hargreaves con ERA5-Land.</p>
  <p>La regla acepta un mes al que le falten <b>{MAX_DIAS_FALTANTES} días o menos</b>; como no es lo mismo que
  falten sueltos o seguidos, el detalle de cada mes (al pasar el cursor) dice también <b>cuántos son
  consecutivos</b>.</p>

  <div id="g-calidad" class="grafico" style="min-height:{150 + 26 * len(cal_filas)}px"></div>
  <p class="nota">Las fuentes mensuales (IMERG y los pluviómetros) solo están o no están: verde o rojo pleno. Los
  meses excluidos de PL aparecen vacíos: {exc_lista}.</p>

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
  <p>De las {len(cal_resumen)} fuentes, <b>{cal_completas} no pierden ni un mes</b>: las de malla (IMERG y
  ERA5-Land) y los pluviómetros completos. La que menos meses conserva es <b>{html.escape(" y ".join(n.split(" · ")[-1] for n in cal_peores))}</b>
  ({cal_min_usables} de {cal_total}), y le siguen <b>las {len(cal_camels)} series que vienen de CAMELS-COL</b>,
  con {cal_camels[0]["usables"]} cada una.</p>

  <p>El caudal de San Gil conserva {cal_q["usables"]} meses y pierde {cal_q["perdidos"]}, y
  <b>{cal_q["parciales"]} de los que conserva están incompletos</b> (de 1 a {MAX_DIAS_FALTANTES} días sin registro):
  válidos según la regla, pero no perfectos.</p>

  <p><b>Por qué {MAX_DIAS_FALTANTES} días.</b> Quitándoles {MAX_DIAS_FALTANTES} días seguidos a los
  {len(_q_completos)} meses completos de Q, el caudal medio se aleja del verdadero un {umbral_mediana:.1f} % en la
  mediana y hasta un {umbral_p95:.1f} % en el 95 % de los casos. El error crece parejo, sin un límite natural: el
  umbral es un compromiso que conserva {cal_q["usables"]} meses de Q, contra {umbral_meses_completos} si se
  exigieran meses completos.</p>

  <p><b>Un mes incompleto no se presenta como completo:</b> los acumulados (Q en mm) son el promedio de los días
  con dato por los días del mes. Sumando solo los días con dato, los {len(_q_incompletos)} meses incompletos
  quedarían un {suma_parcial_falta.mean():.1f} % por debajo en promedio, y hasta un {suma_parcial_falta.max():.1f} %.</p>

  <p>De los meses descartados, a <b>{cal_q_solo_dispersos} de {len(cal_q_rotos)}</b> les faltan días
  <b>dispersos</b> (ninguna racha pasa de {MAX_DIAS_FALTANTES}), y el peor, {cal_q_racha_mes}, se queda sin
  <b>{cal_q_racha_max} días seguidos</b>: la misma regla los descarta, pero no merecen la misma desconfianza.</p>

  <p class="aviso">En CAMELS-COL el caudal y las temperaturas de MSWX fallan <b>exactamente los mismos días</b>:
  los archivos omiten la fila entera de los días sin caudal. <b>Los huecos de MSWX en CAMELS-COL son heredados
  del caudal.</b></p>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Control de calidad básico</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <p>Los archivos se revisaron <b>tal como se descargaron</b>: fechas, duplicados, unidades, códigos de faltante
  (−9999, −999, 9999…), valores imposibles según la física de cada variable y banderas de calidad. De los {len(cc)} chequeos, <b>{cc_conteo.get("sin problemas", 0)}
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
  <p><b>Las unidades se confirmaron:</b> el caudal de CAMELS-COL, pasado a mm/día, da el que publica su archivo de
  firmas (está en m³/s); IMERG, en mm/h por las horas del mes, reproduce el archivo del análisis; ERA5-Land viene en °C.</p>
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
  <p>Solo Q y PL vienen de un instrumento en la cuenca, y sus huecos se quedan como huecos. PI es una estimación
  satelital, T la salida de un modelo y la ETP sale de él: que no tengan huecos no quiere decir que sean exactas.</p>
  </details>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Anomalías en las series</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <p>Un cambio de estación, de instrumento o de producto deja un <b>escalón</b>: desde cierta fecha la serie
  mide sistemáticamente más o menos que sus vecinas. Para buscarlo, cada pluviómetro se compara con el promedio
  de los demás, y PI y Q con PL.</p>
  <ul class="tratamiento">
    <li><b>Curva de doble masa:</b> el acumulado de la serie contra el de la referencia. Si miden lo mismo en
    proporción es una recta; un salto la quiebra.</li>
    <li><b>Prueba de Pettitt</b> ({CITA_PETTITT}): busca el punto que mejor parte la razón serie/referencia en
    dos niveles y da la probabilidad <i>p</i> de que eso ocurra por azar. Es significativo si <i>p</i> &lt; 0.05.</li>
  </ul>
  <p>Como una estación con salto contaminaría la referencia de las demás, se prueba por rondas: la peor se
  aparta y se repite. Se usa la serie anterior a estas decisiones, sin el tramo de Encino ya excluido.</p>
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
  <p><b>Pueblo Viejo tiene un segundo salto.</b> Como Pettitt encuentra un solo corte por serie, se repitió en el
  tramo posterior al primero (serie depurada, contra el {html.escape(an_pv2.referencia)}): Pueblo Viejo pasa de
  {an_pv2.razon_antes:.2f} a {an_pv2.razon_despues:.2f} veces sus vecinos desde
  {fecha_anomala(an_pv2.primer_mes_despues)} ({an_pv2.cambio_pct:+.0f} %, <i>p</i> {fmt_p_eq(an_pv2.p)}).
  {" ".join(f"{html.escape(s.split(' · ')[1])} no tiene un segundo salto (<i>p</i> {fmt_p_eq(p)})." for s, p in an_seg_sin_salto.p.items())}
  No se sabe cuál tramo está bien: <b>se conserva, marcado como incierto</b>, y PL puede estar algo baja desde
  ese mes.</p>
  <p><b>PI frente a PL: {an_pi.cambio_pct:+.0f} % desde {fecha_anomala(an_pi.primer_mes_despues)}</b> (<i>p</i>
  {fmt_p_eq(an_pi.p)}; de {an_pi.razon_antes:.2f} a {an_pi.razon_despues:.2f} veces PL). Coincide con el paso de
  IMERG de la calibración con TRMM a la de GPM, el 1 de junio de 2014 ({CITA_IMERG_DOC}), pero también llega
  {an_meses_pv2_pi} meses después del segundo salto de Pueblo Viejo, que baja PL. Con una
  {html.escape(an_pi_sin.referencia)}, el salto es de {an_pi_sin.cambio_pct:+.0f} % (<i>p</i> {fmt_p_eq(an_pi_sin.p)})
  {"y deja de ser significativo: buena parte viene de Pueblo Viejo, y TRMM → GPM no es la explicación principal." if not an_pi_sin.significativo else "y sigue siendo significativo: TRMM → GPM sigue siendo una explicación posible."}
  PI se conserva, marcado como incierto. <b>Q frente a PL</b> no tiene salto (<i>p</i> {fmt_p_eq(an_q.p)}).</p>
  <p class="nota">El catálogo del IDEAM no guarda reubicaciones ni cambios de instrumento (solo la fecha de
  instalación, anterior a 1998, y el estado), así que los saltos de los pluviómetros no se pueden confirmar con
  metadatos. Las pruebas corren en <code>scripts/07c_anomalias.py</code>.</p>

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
  <p>Un mes en 0 mm mientras todos los demás midieron al menos 20 mm es más probablemente una planilla vacía:
  esos {len(an_ceros_fuera)} se excluyen. Los {len(an_ceros_quedan)} restantes se conservan, porque algún vecino
  también midió casi nada.</p>

  <h3>Secuencias constantes, picos aislados y cobertura</h3>
  <p>{"No hay" if an_rachas_dia.empty else f"Hay {len(an_rachas_dia)}"} tramos de 5 días o más con el mismo
  valor en Q o en la temperatura (huella de un instrumento trabado o un dato copiado), y
  {"ningún día" if an_picos.empty else f"{len(an_picos)} día" + ("" if len(an_picos) == 1 else "s")} de Q que triplique a
  sus vecinos; en los pluviómetros, {len(an_rachas_pl)} pares de meses seguidos con el mismo total, sin efecto.
  Cuando a PL le falta algún pluviómetro ({len(an_cob)} meses), se aleja del promedio de los {len(DENTRO)} un
  {an_sesgo.median():.1f} % en la mediana y un {an_sesgo.max():.1f} % como máximo (estimado en los meses en que
  están todos): incertidumbre declarada, no se corrige.</p>
{nota_enso.replace("sin color, ninguno de los dos", "en negrita sin color, ninguno de los dos")}
  <p class="aviso"><b>Con todas las exclusiones, PI queda un {abs(sesgo_pi_pl):.1f} % por debajo de PL.</b> Los
  tramos excluidos: {exc_lista}.</p>
  </details>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Registro de anomalías</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <p>Lo que apareció raro en los datos, con qué se comprobó, qué se decidió y su efecto. De las {len(reg)} anomalías, <b>{reg_conteo.get("corregido", 0)}
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
  </details>
</section>

<section>
  <details class="plegable" open>
  <summary><h2>Las cuatro variables, en números</h2><span class="plegable-pista">clic para retraer o desplegar</span></summary>
  <p>Las variables mensuales del proyecto en San Gil: <b>PI</b> (IMERG, ponderada por área), <b>PL</b> (los
  {len(DENTRO)} pluviómetros dentro de la divisoria), <b>Q</b> (caudal) y la temperatura de ERA5-Land: <b>T media</b>,
  <b>T máx</b> y <b>T mín</b>, promedios mensuales de los valores diarios.</p>
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
  <div{revision(f"cajas sobre los {ciclo_n} meses comunes")}>
  <p>Un diagrama de caja por variable, con una caja por mes del calendario. Para comparar las variables con
  los mismos pares de meses, las cajas usan solo los <b>{ciclo_n} de los {len(PERIODOS)} meses</b> en que PI, PL,
  Q y la temperatura tienen dato a la vez (los huecos son de {" y ".join(clima_huecos_de)}), los mismos de la tabla
  del ciclo anual: cada caja reúne ese mes en esos años, entre {clima_anios_mes.min()} y {clima_anios_mes.max()}
  según el mes. La tabla de arriba, en cambio, usa todos los meses válidos de cada variable.</p>
  <div class="pestanas" role="tablist" aria-label="Variable" id="pestanas-cajas"></div>
  <div id="g-cajas" class="grafico" style="min-height:0; height:420px"></div>
  <p class="nota">Caja: del percentil 25 al 75. Línea dentro de la caja: la mediana. Bigotes: hasta 1.5 veces
  el rango intercuartil. Puntos, a la izquierda de cada caja: todos los meses comunes, uno por año; pasa el cursor
  por encima para ver cuál es. Los cuartiles se calculan por
  interpolación lineal, igual que en las tablas.</p>
  </div>

  <h3>Cómo se tratan los datos</h3>
  <ul class="tratamiento">
    <li><b>Período.</b> {PERIODOS[0]} a {PERIODOS[-1]}, {len(PERIODOS)} meses: el período en que existe
    IMERG. Toda serie se recorta a esa ventana.</li>
    <li><b>Faltantes.</b> No se rellena ni se interpola nada. Las series diarias (Q y las temperaturas) se pasan a mensual con
    una regla: un mes al que le falten {MAX_DIAS_FALTANTES + 1} días o más queda vacío, y con hasta
    {MAX_DIAS_FALTANTES} faltantes se calcula con los días que hay. PL se promedia cada mes con los
    pluviómetros que tengan dato. PI y las temperaturas no tienen huecos; Q sí.</li>
    <li{revision("nuevo punto")}><b>Meses comunes.</b> La tabla de arriba usa todos los meses válidos de cada variable. Los diagramas de
    caja por mes y la tabla por mes del ciclo anual usan solo los {ciclo_n} meses en que todas tienen dato, para
    comparar las fuentes con los mismos pares de meses.</li>
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
  <div{revision("texto ajustado: las cajas usan otros meses")}>
  <p>Un mes es atípico si se sale {FACTOR_ATIPICO:.1f} rangos intercuartiles por fuera de los cuartiles <b>de su
  propio mes del calendario</b>, el mismo criterio de los bigotes de los diagramas de caja, pero aquí con todos los
  meses válidos de cada variable, no solo los {ciclo_n} comunes. Hay {atip_conteo['PI']} en PI, {atip_conteo['PL']} en PL, {atip_conteo['Q']} en Q,
  {atip_conteo['T media']} en T media, {atip_conteo['T máx']} en T máx y {atip_conteo['T mín']} en T mín.
  La tabla los pone lado a lado, para ver qué pasó con las demás variables cuando una se salió de lo normal.</p>
  </div>
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
    <li><b>Un caso que no cumple el criterio pero salta a la vista: {fecha_enso(_F99)}.</b> Es el febrero más
    lluvioso del período en PL ({n(feb99['PL']['valor'])} mm, {(feb99['PL']['valor'] / feb99['PL']['segundo'] - 1) * 100:.0f} %
    más que el segundo) y en PI ({n(feb99['PI']['valor'])} mm, {(feb99['PI']['valor'] / feb99['PI']['segundo'] - 1) * 100:.0f} %
    más), pero queda a {feb99['PL']['factor']:.2f} y {feb99['PI']['factor']:.2f} rangos intercuartiles del percentil 75,
    bajo el umbral de {FACTOR_ATIPICO:.1f}. Desde la mediana de los febreros sí es alto (PI {atip_z.loc[_F99, "PI"]:+.1f},
    PL {atip_z.loc[_F99, "PL"]:+.1f}). {"El caudal de ese mes sí fue atípico. " if feb99_q_atipico else ""}Es un evento
    extremo a tener en cuenta.</li>
    <li><b>Enero y febrero de 2005: la emergencia
    invernal en Santander.</b> En la cuenca, enero de 2005 estuvo {ene05["z_pl"]:+.1f} rangos intercuartiles sobre lo normal
    en PL, {ene05["z_pi"]:+.1f} en PI y {ene05["z_q"]:+.1f} en Q, y febrero {ene05["z_pl_feb"]:+.1f}, {ene05["z_pi_feb"]:+.1f}
    y {ene05["z_q_feb"]:+.1f}. Enero ({n(ene05["pl"])} mm de PL) era atípico antes de excluir el primer tramo de Pueblo
    Viejo, que medía {an_pv.razon_antes:.2f} veces lo de sus vecinos y bajaba los eneros de 1998 a 2004: el umbral pasó
    de {n(ene05["umbral_antes"])} a {n(ene05["umbral_hoy"])} mm con el mismo valor del mes. Qué pasó en la atmósfera
    esos meses se explica en «Explicaciones físicas».</li>
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
  <div{revision("nota ajustada a los colores unificados")}>
  <p class="nota">Las dos fuentes van en el mismo color, porque es la misma variable: ERA5-Land con línea continua
  y banda rellena; MSWX con línea a trazos, rombos y su banda marcada por bordes punteados.
  Línea gruesa: mediana de cada mes. Banda: del percentil 10 al 90 de los días de ese mes.
  Se comparan los {n(t_n)} días en que existen las dos.</p>
  </div>

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
  <p>La <b>ETP</b> es el agua que evaporaría un pasto bien regado con el clima de cada día: se calcula, no se mide,
  y no es la evapotranspiración real. CAMELS-COL publica una con el método de Hargreaves ({CITA_HARGREAVES}) y la
  temperatura de MSWX ({CITA_JIMENEZ}, ecuación 1):</p>
  <p class="formula">ETP = 0.0023 · R<sub>a</sub> · (T + 17.8) · √(T<sub>máx</sub> − T<sub>mín</sub>) &nbsp;&nbsp;[mm/día]</p>
  <p class="nota">T = (T<sub>máx</sub> + T<sub>mín</sub>) / 2, en °C. R<sub>a</sub>, la radiación en el tope de la
  atmósfera, depende de la latitud y del día (FAO-56, ecuaciones 21 a 25; {CITA_FAO}) y pasa a mm/día por 0.408.</p>
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

  <p><b>La ETP de CAMELS-COL no cuadra con su propia fórmula:</b> sale {etp_cociente.median():.2f} veces la de
  Hargreaves con MSWX, con un factor casi constante (entre {etp_cociente.min():.2f} y {etp_cociente.max():.2f}). No
  es un error de unidades en R<sub>a</sub> (daría {etp_cociente_mj:.2f}); la causa no se pudo identificar.</p>
  <p><b>¿Está mal nuestra R<sub>a</sub>?</b> No: coincide con el ejemplo 8 de FAO-56 (20° S, 3 de septiembre:
  32.2 MJ m⁻² día⁻¹) y con integrarla minuto a minuto (las dos comprobaciones van en
  <code>06b_etp_hargreaves.py</code>). Y para obtener la ETP de CAMELS-COL haría falta una R<sub>a</sub> media de
  {etp_ra_implicita.mean():.1f} mm/día, cuando a {etp_lat:.1f}° N nunca pasa de {etp_ra_max:.1f}; como esa
  R<sub>a</sub> imposible tiene la misma forma estacional que la nuestra (cociente de
  {etp_ra_cociente_mes.min():.2f} a {etp_ra_cociente_mes.max():.2f} según el mes), es un factor de escala.</p>
  <p><b>El valor recalculado es el plausible:</b> {n(etp_anual.mswx)} a {n(etp_anual.era)} mm/año, dentro del rango
  de 1 200 a 1 400 mm/año que el artículo de CAMELS-COL da para Colombia ({CITA_JIMENEZ}) y por encima de lo que la
  cuenca pierde en el balance (PL − Q = {n(etp_pl_menos_q)} mm/año). Los {n(etp_anual.camels)} mm/año de CAMELS-COL{" superan incluso a la lluvia (PL = " + n(etp_pl_anual) + " mm/año)" if etp_anual.camels > etp_pl_anual else ""}.</p>
  <p><b>Con MSWX o con ERA5-Land da casi lo mismo</b> ({etp_era_vs_mswx:+.1f} %, r = {etp_r_era_mswx:.2f} mes a
  mes), aunque ERA5-Land es más fría: también tiene más amplitud diaria, y en la fórmula de Hargreaves las
  dos cosas se compensan.</p>
  <p class="aviso"><b>La ETP de este informe es Hargreaves con ERA5-Land</b>, la calculada por el proyecto.
  La que publica CAMELS-COL no se usa en ningún cálculo.</p>
</section>

<section>
  <h2>Cómo se relacionan las variables entre sí</h2>
  <p>Las {len(VARIABLES_CORR)} variables mensuales (PI, PL, Q, la <b>ETP</b> de Hargreaves y las temperaturas
  <b>T MSWX</b> y <b>T ERA5</b>), cruzadas todas contra todas sobre los <b>{corr_n} meses en que todas tienen
  dato</b>, para que los coeficientes sean comparables entre sí.</p>

  <p class="nota">Se muestra <b>solo Spearman</b>, que trabaja con rangos: no supone una recta y no lo
  arrastran unos pocos meses extremos. Con Pearson la lectura apenas cambia (diferencia máxima en la matriz:
  {corr_dif_max:.2f}).</p>

  <div class="pestanas" role="tablist" aria-label="Qué series comparar">
    <button type="button" role="tab" id="pestana-crudas" aria-controls="panel-corr" aria-selected="true">Series tal cual</button>
    <button type="button" role="tab" id="pestana-anomalias" aria-controls="panel-corr" aria-selected="false" tabindex="-1">Anomalías (sin el ciclo anual)</button>
    <button type="button" role="tab" id="pestana-rezago" aria-controls="panel-corr" aria-selected="false" tabindex="-1">Un mes de rezago</button>
  </div>
  <div role="tabpanel" id="panel-corr" aria-labelledby="pestana-crudas">
    <div id="g-corr-matriz" class="grafico" style="min-height:860px"></div>
  </div>
  <div{revision("nota ajustada a los colores unificados")}>
  <p class="nota">En la <b>diagonal</b>, cómo se reparte cada variable, en su color; <b>debajo</b>, la nube de puntos de
  cada par (un punto por mes); <b>encima</b>, su coeficiente, azul si suben juntas y naranja si van al revés.</p>
  </div>
  <p class="nota"><b>Los paneles están enlazados:</b> arrastra sobre uno para marcar meses y se resaltan en
  todos los demás. Doble clic para soltar la selección. <span id="corr-seleccion" style="color:var(--acento)"></span></p>

  <h3>Qué dicen</h3>
  <p><b>Las dos fuentes de lluvia concuerdan</b> (ρ = {rho('PI', 'PL'):.2f}), pero no es una confirmación
  mutua: IMERG se ajusta con redes de estaciones parecidas a PL, así que <b>no son del todo independientes</b>.</p>

  <p><b>El caudal se lleva mejor con los pluviómetros que con el satélite</b> (ρ = {rho('PL', 'Q'):.2f}
  contra {rho('PI', 'Q'):.2f}): la red parece captar algo que el satélite se pierde.</p>

  <p><b>Con más lluvia, el caudal es menos predecible.</b> Ajustando una recta, la varianza que no explica es
  {p2_dispersion["PL"]:.1f} veces mayor en el tercio de meses más lluviosos que en el más seco con PL, y
  {p2_dispersion["PI"]:.1f} con PI: el caudal depende también del agua que la cuenca trae guardada.</p>

  <p><b>Las dos temperaturas se mueven juntas</b>, ρ = {rho('T MSWX', 'T ERA5'):.2f}, pese a los
  {t_sesgo_media:.2f} °C que las separan. Discrepan en el nivel, no en el movimiento.</p>

  <h3>Lo que solo se ve al quitar el ciclo anual</h3>
  <p>En la pestaña de anomalías, la lluvia contra la temperatura y la evapotranspiración <b>se refuerza</b> al
  quitar el ciclo anual, al revés de lo usual. El caso más marcado es <b>{html.escape(corr_par_salto[0])} con
  {html.escape(corr_par_salto[1])}</b>: de ρ = {rho(*corr_par_salto):.2f} a
  <b>{rho(*corr_par_salto, anomalias=True):.2f}</b>; también {corr_tambien}. PL con Q, cuyos ciclos sí van juntos
  (ρ = {corr_ciclo_rho.loc['PL', 'Q']:.2f}), se debilita un poco ({rho('PL', 'Q'):.2f} a
  {rho('PL', 'Q', anomalias=True):.2f}).</p>
  <p>La razón: <b>la lluvia tiene un ciclo anual enorme y la temperatura casi no</b> (el ciclo explica el
  {corr_peso_ciclo['PI']:.0f} % de la variación de PI, el {corr_peso_ciclo['PL']:.0f} % de la de PL y solo el
  {corr_peso_ciclo['T ERA5']:.0f} % de la de T ERA5), y esos ciclos <b>no se relacionan entre sí</b> (primera
  columna de la tabla). En las series tal cual, la oscilación de la lluvia <b>diluye</b> la relación; sin ella
  aparece el vínculo esperable: <b>un mes más lluvioso de lo normal es más nublado</b>, más fresco y con menos
  evapotranspiración potencial.</p>

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
  <p>La tercera pestaña cruza cada variable con las demás <b>un mes después</b> ({corr_n_rezago} pares de meses
  consecutivos): cada casilla es la <b>columna en el mes t</b> contra la <b>fila en el mes t+1</b>, y la diagonal
  dice cuánto se parece cada variable a sí misma un mes después.</p>
  <p class="nota">Esta pestaña usa las series tal cual, así que mezcla la respuesta de la cuenca con el
  desfase de los ciclos anuales. La pregunta de si Q responde a la lluvia con un mes de rezago se
  contesta en «¿Sirve la lluvia para estimar el caudal?».</p>

  <p class="aviso">Una correlación mensual no es causa ni capacidad de predicción: que Q y PL vayan a
  ρ = {rho('PL', 'Q'):.2f} no quiere decir que la lluvia de un mes explique el caudal de ese mes. <b>La relación
  tiene memoria</b>, y la correlación del mismo mes no la captura.</p>
</section>

<section>
  <h2>Lo que le cae a la cuenca y lo que sale por el río</h2>
  <p class="nota">De aquí en adelante, y en todo el informe, tres siglas: <b>PI</b> es la precipitación de
  IMERG (satélite) promediada sobre la cuenca, <b>PL</b> la precipitación de los pluviómetros del IDEAM
  (el promedio de las {len(DENTRO)} estaciones de la red) y <b>Q</b> el caudal.</p>
  <p>Dividido por el área de la cuenca ({n(AREA_SG_KM2)} km²), el caudal queda como lámina de agua, en mm, y se
  compara con la lluvia en el mismo eje.</p>
  <div class="cifras" style="margin: 18px 0 6px">
    <div class="cifra"><b>{n(bal_p_anual)} mm/año</b><span>lluvia (PI), en los meses con caudal</span></div>
    <div class="cifra"><b>{n(bal_q_anual)} mm/año</b><span>caudal</span></div>
    <div class="cifra"><b>{coef_periodo:.2f}</b><span>coeficiente de escorrentía</span></div>
    <div class="cifra"><b>{bal_n}</b><span>meses con ambos datos</span></div>
  </div>
  <div id="g-balance" class="grafico" style="min-height:400px"></div>
  <div id="g-escorrentia" class="grafico" style="min-height:0; height:300px"></div>
  <div{revision("nota ajustada a los colores unificados")}>
  <p class="nota">La franja azul es la lluvia (PI); la línea verde, el caudal (Q). Abajo, Q / PL en naranja y Q / PI
  en azul punteado. Donde el caudal se interrumpe
  es porque ese mes no cumple la regla de los cuatro días faltantes.</p>
  </div>
  <p><b>Sale como caudal cerca del {coef_periodo * 100:.0f} % de la lluvia</b>; el resto se evapora o queda
  almacenado.</p>
  <p class="nota"><b>CAMELS-COL lo confirma por su cuenta:</b> publica para San Gil un <code>runoff_ratio</code> de
  {float(firmas_sg.runoff_ratio):.2f} y {n(float(firmas_sg.q_mean) * 365)} mm/año de caudal; aquí, por otro camino,
  salen {coef_periodo:.2f} y {n(bal_q_anual)} mm/año.</p>

  <p class="aviso">Meses en que salió más agua de la que cayó (coeficiente &gt; 1): <b>{bal_sobre1_pl} con PL</b>
  (máximo {bal_max_pl:.2f} en {fmt_mes(bal_max_mes_pl)}) y {bal_sobre1} con PI (máximo {bal_max:.2f} en
  {fmt_mes(bal_max_mes)}). Con PL, {bal_pl_tras_lluvia} de los {bal_sobre1_pl} siguen a dos meses más
  lluviosos que lo normal: agua guardada que sale después. Con PI son más porque PI mide menos lluvia.</p>

  <h3>Lo que llueve menos lo que sale, contra la evapotranspiración</h3>
  <p>La lluvia (P) se reparte en caudal (Q), evapotranspiración y lo que la cuenca guarda o libera, así que
  <b>P − Q no es la evapotranspiración</b>: mes a mes incluye el almacenamiento. Se compara con la ETP de
  Hargreaves, con las dos fuentes de lluvia.</p>
  <div id="g-pq-mensual" class="grafico" style="min-height:0; height:380px"></div>
  <p>Mes a mes, P − Q oscila mucho más que la ETP: con PL la supera en {pq_res["pl"]["sobre_etp"]} de
  {pq_n_meses} meses ({", ".join(pq_meses_guarda)} en el año típico, cuando la cuenca guarda agua), y en
  {pq_res["pl"]["negativo"]} meses sale más agua de la que cae ({pq_res["pi"]["negativo"]} con PI): el río drenando
  lo guardado.</p>
  <div id="g-pq-anual" class="grafico" style="min-height:0; height:340px"></div>
  <p>En el año, el almacenamiento casi se cancela. Sobre los {pq_n_anios} años con los 12 meses de caudal,
  PL − Q promedia {n(pq_res["pl"]["anual"])} mm/año y PI − Q {n(pq_res["pi"]["anual"])}, contra una ETP de
  {n(pq_etp_anual)} mm/año. {"Ningún año pasa de la ETP, como corresponde si la evapotranspiración real no supera a la potencial." if not pq_anios_sobre["pl"] and not pq_anios_sobre["pi"] else f"P − Q supera a la ETP en {pq_res['pl']['anios_sobre_etp']} años con PL ({', '.join(pq_anios_sobre['pl']) or 'ninguno'}) y en {pq_res['pi']['anios_sobre_etp']} con PI{' (' + ', '.join(pq_anios_sobre['pi']) + ')' if pq_anios_sobre['pi'] else ''}. Como P − Q = ET + ΔS + otras salidas, el agua que sobra pudo:"}</p>
  {"" if not pq_anios_sobre["pl"] and not pq_anios_sobre["pi"] else pq_explicaciones}

  <div{revision("índice P/ETP")}>
  <h3>¿Húmeda o árida? La lluvia contra la ETP</h3>
  <p>El índice <b>P/ETP</b> compara la lluvia con la evapotranspiración potencial: cuánta agua cae frente a cuánta
  podría evaporar el clima. <b>No es la lluvia total</b>: la misma lluvia es abundante en un clima frío y escasa en uno
  cálido, y por eso la clase de aridez de UNEP ({CITA_UNEP}) se define con este cociente y no con los milímetros.
  Se calcula con PL y con PI, y con la ETP de Hargreaves con ERA5-Land, sobre los {len(PERIODOS)} meses de
  {PERIODOS[0].year}–{PERIODOS[-1].year}: no usa Q, así que no se recorta a los meses con caudal.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Lluvia</th><th class="num">P (mm/año)</th><th class="num">ETP (mm/año)</th><th class="num">P/ETP</th>
    <th>Clase (UNEP)</th><th class="num">Año más seco</th><th class="num">Año más húmedo</th>
    <th class="num">Años bajo {UNEP_HUMEDO:.2f}</th></tr></thead>
    <tbody>
{pe_filas_anual}
    </tbody>
  </table>
  </div>
  <p class="nota">P y ETP: totales anuales medios de {PERIODOS[0].year}–{PERIODOS[-1].year} ({pe_n_anios} años). Año más
  seco y más húmedo: el índice de cada año por separado. Clases de UNEP: {pe_clases_txt}. UNEP las definió con la ETP de
  Thornthwaite; aquí se usa la de Hargreaves, así que la clase es aproximada.</p>
  <p>{pe_resultado_txt}{pe_anios_txt} {pe_margen_txt}</p>
  <div id="g-pe-mes" class="grafico" style="min-height:0; height:340px"></div>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Mes</th><th class="num">P/ETP con PL</th><th class="num">P/ETP con PI</th>
    <th class="num">Años con P &lt; ETP (PL)</th><th class="num">Años con P &lt; ETP (PI)</th></tr></thead>
    <tbody>
{pe_filas_mes}
    </tbody>
  </table>
  </div>
  <p class="nota">P/ETP del mes: la media de P de ese mes en los {pe_n_anios} años dividida por la media de la ETP del
  mismo mes (no el promedio de los cocientes de cada año). En negrita, P/ETP &lt; 1: déficit, llueve menos de lo que
  podría evaporarse; por encima de 1, excedente. Las dos últimas columnas cuentan los años en que ese mes tuvo P &lt; ETP.</p>
  <p>{pe_deficit_txt} {pe_anios_mes_txt}</p>
  <p><b>La ETP es potencial, no real</b>: es lo que evaporaría un pasto bien regado con el clima de ese mes. Un mes con
  P/ETP &lt; 1 no quiere decir que la cuenca se seque: la evapotranspiración real queda limitada por el agua disponible, y
  la cuenca gasta lo que guardó en los meses húmedos (ver P − Q, arriba).</p>
  </div>
</section>

<section>
  <h2>El ciclo anual</h2>
  <h3>Cada mes del calendario, y cuánto cambia de un año a otro</h3>
  <div{revision(f"tabla sobre los {ciclo_n} meses comunes")}>
  <p>El <b>ciclo anual</b> junta los eneros, los febreros…, de {PERIODOS[0].year} a {PERIODOS[-1].year}, y resume cada mes:
  la media y la mediana dicen cómo es el mes típico; la desviación estándar y el rango p10–p90, cuánto cambia
  de un año a otro. Para que las fuentes se comparen con los mismos pares de meses, se usan solo los meses en que
  PI, PL, Q y T media tienen dato a la vez: los mismos <b>{ciclo_n} meses</b> del año típico. Como
  {" y ".join(clima_huecos_de)} tiene huecos, cada mes reúne entre {clima_anios_mes.min()} y {clima_anios_mes.max()}
  años, no los {clima_anios_periodo} del período.</p>
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
  <p class="nota">Años válidos: años en que ese mes tienen dato las cuatro variables a la vez, así que la columna
  es la misma en las cuatro pestañas (los huecos son de {" y ".join(clima_huecos_de)}, por la regla de los
  {MAX_DIAS_FALTANTES + 1} días faltantes; PL va con sus exclusiones). Q es el promedio mensual del caudal diario, en m³/s; T media, la de ERA5-Land. Desviación
  estándar muestral; cuartiles y percentiles por interpolación lineal ({CITA_HYNDMAN}).</p>
  </div>
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

  <div{revision("subsección nueva: el mapa año–mes")}>
  <h3>Cada año, mes a mes</h3>
  <p>Cada fila es un año y cada columna, un mes; el color es el valor de ese mes. Leído por columnas, el mapa repite el
  ciclo anual; leído por filas, muestra cómo fue cada año.</p>
  <div class="pestanas" role="tablist" aria-label="Variable del mapa año–mes">
{mapa_botones}
  </div>
  <div role="tabpanel" id="panel-mapa" aria-labelledby="pestana-mapa-0">
    <div id="g-mapa-am" class="grafico" style="min-height:0; height:560px"></div>
  </div>
  <p class="nota">El mapa usa todos los meses válidos de cada variable ({len(PERIODOS) - mapa_am_vacias["PL"]} en PL,
  {len(PERIODOS) - mapa_am_vacias["PI"]} en PI, {len(PERIODOS) - mapa_am_vacias["Q"]} en Q y
  {len(PERIODOS) - mapa_am_vacias["T media"]} en T media), no solo los {ciclo_n} comunes de la tabla de arriba y de los
  diagramas de caja: aquí se quiere ver cada año, no comparar fuentes. Los {mapa_am_vacias["Q"]} meses sin dato de Q
  quedan en gris, sin rellenar. PL y PI comparten la escala de color, para que el mismo color sea la misma lluvia en
  las dos; Q y T media tienen la suya. Pasa el cursor por una casilla para ver su valor.</p>
  <ul>
    <li><b>Los dos picos aparecen en la mayoría de los años.</b> El mes más lluvioso de cada semestre cae a ±1 mes
    del pico promedio {mapa_picos_txt}. Es el método simple de «¿Se repite cada año? ¿Es estable?», más abajo.</li>
    <li><b>Hay años con la mayoría de los meses por encima de lo normal, y años con la mayoría por debajo.</b>
    Contando los meses por encima de la mediana de su mes: {_mapa_sobre_txt("PL")}; {_mapa_sobre_txt("PI")}.
    De los años contrastantes (los de «Los años contrastantes», más abajo; húmedos: {_y_lista(anom_humedos)}; secos:
    {_y_lista(anom_secos)}), {_mapa_coincide_txt("PL")}; {_mapa_coincide_txt("PI")}. No tienen por qué
    coincidir del todo: allí los años se ordenan por cuánto se apartan sus meses de lo normal, en promedio y con PL y
    PI juntas; aquí solo se cuenta cuántos meses quedan por encima, con cada fuente por separado.</li>
  </ul>
  </div>

  <h3>Qué meses cambian más de un año a otro</h3>
  <p>Para cada mes: la <b>desviación estándar</b> (DE) y el <b>coeficiente de variación</b> (CV = DE / media);
  la <b>asimetría</b> clásica y la de Bowley, que usa solo los cuartiles y no la mueve un año extremo; y la
  <b>influencia de cada año</b>, cuánto cambia la media al quitarlo. La temperatura va en kelvin, porque en °C el
  CV no tiene sentido (su cero es convencional).</p>
  <div{revision("nota nueva")}>
  <p class="nota">Esta sección usa todos los meses válidos de cada variable ({var_n["PL"][0]} años por mes en PL, PI y
  T media; entre {var_n["Q"][0]} y {var_n["Q"][1]} en Q), no los {ciclo_n} meses comunes de la tabla «Cada mes del
  calendario…», así que sus medias y DE pueden diferir un poco de las de esa tabla.</p>
  </div>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th></th><th>Mayor CV</th><th>Mayor DE</th><th>Asimetría clásica mayor que 1</th>
    <th>Año que más mueve una media</th></tr></thead>
    <tbody>
{var_filas}
    </tbody>
  </table>
  </div>
  <p><b>La DE crece con el tamaño del mes; el CV corrige por él</b>, así que un mes seco puede ser el más
  variable en proporción aunque no en milímetros. <b>El CV es inestable cerca de una media nula</b>: aquí,
  mientras menor es la media del mes, más ancho es su intervalo (correlación de {var_corr["PL"]:.2f} con PL,
  {var_corr["PI"]:.2f} con PI y {var_corr["Q"]:.2f} con Q), pero ningún mes se acerca a cero (mínimo:
  {var_tabla.loc["PI", "media"].min():.0f} mm/mes con PI), así que pierde precisión sin dispararse. En la
  temperatura en K, el CV ({var_tabla.loc["T media", "cv"].min():.2f} % a {var_tabla.loc["T media", "cv"].max():.2f} %)
  no agrega nada a la DE, y su intervalo mide entre {var_rel.loc["T media"].min():.0f} % y
  {var_rel.loc["T media"].max():.0f} % del propio CV, como en la lluvia: la imprecisión viene sobre todo de tener
  {var_tabla.n.max()} años por mes como mucho.</p>
  <p>{("<b>La asimetría fuerte la ponen pocos años:</b> donde la clásica pasa de 1, la de Bowley no pasa de " + f"{var_bowley_max:.2f}" + " en valor absoluto: uno o dos años muy altos cargan la distribución, no el conjunto.") if var_por_pocos else "<b>La asimetría fuerte es del conjunto de los años</b>, no de uno o dos: la de Bowley también es alta."}
  Con la temperatura, ningún año mueve una media más de {max(abs(x) for x in var_influencia["T media"].values()):.2f} %.</p>

  <h3>El régimen: picos, temporadas, concentración y forma</h3>
  <p>El régimen se describe con la <b>mediana</b> de cada mes. Un mes es <b>húmedo</b> si supera al <b>mes
  típico</b> (el promedio de las 12 medianas), y las temporadas son rachas de meses seguidos, con diciembre y
  enero contiguos. La <b>concentración</b> es la parte del total que cae en los meses húmedos (Q en mm/mes, para
  que sea un volumen). La <b>forma</b> sale de los armónicos de 12 y 6 meses, A₁ y A₂ ({CITA_HORN}): si domina
  A₂, hay dos picos, que se cuentan sobre la curva ajustada. La prueba de Kruskal-Wallis entre los 12 meses dice
  si hay estacionalidad ({CITA_KRUSKAL}).</p>
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
  <p><b>El régimen es {" y ".join(reg_clases)}{" en las tres series" if len(reg_clases) == 1 else ""}</b>
  (Kruskal-Wallis: <i>p</i> ≤ {reg_kw_max:.0e}). Picos: con PL en {" y ".join(regimen["PL"]["picos"])}, con PI en
  {" y ".join(regimen["PI"]["picos"])} y con Q en {" y ".join(regimen["Q"]["picos"])}. La concentración de PI y PL
  no se compara directamente: PI tiene {regimen["PI"]["conc_meses"]} meses húmedos y PL, {regimen["PL"]["conc_meses"]}.</p>

  <h3>¿Se repite cada año? ¿Es estable?</h3>
  <p>A cada año con los 12 meses se le ajusta la misma curva de dos armónicos y se mira si tiene dos picos y si
  cada uno cae a ±{EST_TOL:.0f} mes del pico promedio. Q solo tiene {est_anual["Q"]["anios"]} años completos: los meses
  faltantes no se rellenan. Como esa curva no puede tener más de dos picos, se contrasta con algo más simple: el mes más
  lluvioso de cada semestre a ±1 mes del pico promedio.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Serie (picos del promedio)</th><th class="num">Años</th><th class="num">Bimodales</th>
    <th class="num">Con el pico 1</th><th class="num">Con el pico 2</th><th class="num">Distancia al pico (meses)</th>
    <th class="num">Método simple</th></tr></thead>
    <tbody>
{est_filas_anual}
    </tbody>
  </table>
  </div>
  <p>{"<b>Los dos picos del promedio aparecen en la mayoría de los años</b>" if all(r["los_dos"] > r["anios"] / 2 for r in est_anual.values()) else "<b>Los picos del promedio no aparecen en la mayoría de los años</b> con alguna serie"}:
  con la curva, en {est_anual["PL"]["los_dos"]} de {est_anual["PL"]["anios"]} años con PL, {est_anual["PI"]["los_dos"]} de
  {est_anual["PI"]["anios"]} con PI y {est_anual["Q"]["los_dos"]} de {est_anual["Q"]["anios"]} con Q; con el método simple,
  {est_anual["PL"]["simple"]}, {est_anual["PI"]["simple"]} y {est_anual["Q"]["simple"]}. En {est_anual["PI"]["a1_domina"]} años
  de PI el armónico de 12 meses pesa más que el de 6 ({est_anual["PL"]["a1_domina"]} con PL, {est_anual["Q"]["a1_domina"]} con Q):
  su ciclo es el menos marcado.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th></th><th>1998–2010</th><th>2011–2022</th><th class="num">Corrimiento de los picos (meses)</th>
    <th>¿Estable?</th></tr></thead>
    <tbody>
{est_filas_mitades}
    </tbody>
  </table>
  </div>
  <p class="nota">Entre corchetes, el intervalo del 95 % de A₂/A₁ remuestreando años ({f"{EST_REMUESTREOS:,}".replace(",", " ")} veces).
  Estable: la misma clase en las dos mitades y los picos corridos a lo sumo {EST_TOL:.0f} mes.</p>
  <p><b>{"La clasificación es estable con las tres series." if est_todas_estables else "La clasificación no es estable con todas las series."}</b>
  La diferencia más grande es la de {est_mas_cambia}: A₂/A₁ pasa de {est_mitades[est_mas_cambia]["1998–2010"]["razon"]:.2f} a
  {est_mitades[est_mas_cambia]["2011–2022"]["razon"]:.2f}{" (los intervalos se traslapan)" if est_mitades[est_mas_cambia]["ic_se_traslapan"] else " (los intervalos no se traslapan)"}.
  No se atribuye a una tendencia climática: las dos mitades no tienen el mismo ENSO
  ({est_enso["1998–2010"].get("La Niña", 0)} meses de La Niña en la primera y {est_enso["2011–2022"].get("La Niña", 0)} en
  la segunda; {est_enso["1998–2010"].get("El Niño", 0)} y {est_enso["2011–2022"].get("El Niño", 0)} de El Niño).</p>

  <h3>Desfase estacional: cuánto se atrasa el río respecto a la lluvia</h3>
  <p>La <b>fase</b> de un armónico dice cuándo está su máximo. El <b>desfase estacional</b> es cuánto después
  llega el máximo del armónico de 6 meses de Q que el de la lluvia; medido sobre el año típico, da el atraso en
  días aunque los datos sean mensuales. La incertidumbre sale de remuestrear años completos
  {f"{DES_REMUESTREOS:,}".replace(",", " ")} veces.</p>
  <div class="cifras" style="margin-bottom:18px">
    <div class="cifra"><b>{desfase["Q_PL"]:.0f} días</b><span>Q después de PL · IC 95 % {desfase_ic["Q_PL"][0]:.0f} a {desfase_ic["Q_PL"][1]:.0f}</span></div>
    <div class="cifra"><b>{desfase["Q_PI"]:.0f} días</b><span>Q después de PI · IC 95 % {desfase_ic["Q_PI"][0]:.0f} a {desfase_ic["Q_PI"][1]:.0f}</span></div>
    <div class="cifra"><b>{desfase["PI_PL"]:.0f} días</b><span>PI después de PL · IC 95 % {desfase_ic["PI_PL"][0]:.1f} a {desfase_ic["PI_PL"][1]:.1f}</span></div>
  </div>
  <p><b>Con las dos fuentes, el río va atrasado respecto a la lluvia</b> mucho más que el tiempo de
  concentración ({desfase_tc[0]:.0f} a {desfase_tc[1]:.0f} horas): no es el viaje del agua por el cauce, sino agua
  que se guarda en el suelo y el acuífero. <b>La fuente cambia poco:</b> el ciclo de PI va {desfase["PI_PL"]:.0f}
  días detrás del de PL, y su desfase sale esos mismos días más corto (intervalo de la diferencia:
  {desfase_ic["PI_PL"][0]:.1f} a {desfase_ic["PI_PL"][1]:.1f} días;
  {(("excluye el cero por muy poco" if desfase_ic["PI_PL"][0] < 1 else "no incluye el cero") + ", y es pequeña frente a la resolución mensual") if desfase_dif_concluyente else "incluye el cero: no es concluyente"}).</p>
  <p class="nota">La fase del armónico de 12 meses no se usa: en PL y en Q explica el {regimen["PL"]["var1"]:.0f} % y el
  {regimen["Q"]["var1"]:.0f} % de la forma del ciclo, y su fase es casi ruido.</p>

  <h3>Mes a mes: correlación cruzada entre la lluvia y el caudal</h3>
  <p>La correlación entre la lluvia y el caudal es máxima en el mismo mes (ρ = {rho_cruzada('PL', 0, 'tal cual'):.2f}
  con PL), sigue alta con la lluvia del mes anterior ({rho_cruzada('PL', 1, 'tal cual'):.2f}) y cae a
  {rho_cruzada('PL', -1, 'tal cual'):.2f} con el caudal del mes anterior: la relación va de la lluvia al caudal y
  dura un mes. A tres meses es negativa ({rho_cruzada('PL', 3, 'tal cual'):.2f} y
  {rho_cruzada('PL', -3, 'tal cual'):.2f}), porque con dos temporadas al año ese corrimiento enfrenta la lluviosa
  con la seca.</p>
  <p class="nota">Sin el ciclo anual, la lluvia del mes anterior sigue aportando (correlación parcial con Q,
  descontada la del mes: {memoria.loc['PL', 'parcial_mes_anterior']:.2f}): la cuenca guarda agua de un mes al
  siguiente también en los años anómalos.</p>

  <h3>El año típico: cuándo llueve y cuándo baja el río</h3>
  <p>El <b>año típico</b> de PI, PL y Q, en mm/mes, promediados sobre los mismos <b>{ciclo_n} meses</b> en que
  las tres tienen dato, para que las curvas sean comparables.</p>

  <div id="g-ciclo-anual" class="grafico" style="min-height:420px"></div>

  <p>El mes más seco de PI es {ciclo_valle_imerg} y el caudal toca fondo en {ciclo_valle_q}.</p>

  <div class="cifras" style="margin: 18px 0 6px">
    <div class="cifra"><b>{ciclo_pico_imerg}</b><span>pico de lluvia · IMERG</span></div>
    <div class="cifra"><b>{ciclo_pico_red}</b><span>pico de lluvia · red</span></div>
    <div class="cifra"><b>{ciclo_pico_q}</b><span>pico de caudal</span></div>
    <div class="cifra"><b>{ciclo_valle_q}</b><span>caudal mínimo</span></div>
  </div>

  <p>Las dos fuentes tienen la misma forma: la red pone sus picos en {ciclo_picos_red[0]} y
  {ciclo_picos_red[1]}, y el satélite en {ciclo_picos_imerg[0]} y {ciclo_picos_imerg[1]}. Se separan en la
  magnitud: la red mide más en {ciclo_meses_red_mayor} de los 12 meses (el sesgo del
  {abs(cmp_stats[NOM_RED]['sesgo']):.1f} %).
  {"<b>Para decidir cuándo pasan las cosas en esta cuenca, da igual cuál de las dos se use.</b>" if ciclo_picos_red == ciclo_picos_imerg else "En el calendario difieren a lo sumo en un mes de pico."}</p>

</section>

<section>
  <h2>Anomalías y anomalías estandarizadas</h2>
  <p>Cada variable se puede mirar de tres maneras. La <b>serie original</b> X<sub>t</sub>. La <b>anomalía</b>
  a<sub>t</sub> = X<sub>t</sub> − µ<sub>j</sub>, donde µ<sub>j</sub> es la media del mes j del calendario: cuánto se
  aleja un mes de lo normal para ese mes, en las unidades de la variable. Y la <b>anomalía estandarizada</b>
  z<sub>t</sub> = a<sub>t</sub> / s<sub>j</sub>, donde s<sub>j</sub> es la desviación estándar de ese mes: la misma
  anomalía medida en desviaciones estándar, sin unidades.</p>
  <p>µ<sub>j</sub> y s<sub>j</sub> salen de un <b>período de referencia fijo, {ANZ_REFERENCIA[0].year}–{ANZ_REFERENCIA[1].year}</b>,
  el mismo para las seis variables: es el único en que existen todas, así que todas se miden contra lo mismo. No se
  resta una única media para todos los meses (dejaría el ciclo anual dentro) ni una climatología móvil (se llevaría
  parte de la tendencia). En Q y la temperatura, que llegan hasta {LARGO_DESDE[:4]}, los meses anteriores a
  {ANZ_REFERENCIA[0].year} se comparan con esa misma referencia.</p>
  <p><b>PL*</b>: en esta sección y en «Tendencias de largo plazo», la lluvia de los pluviómetros no es la PL de siempre sino
  una <b>red fija</b> de {len(pl_estrella_red)} estaciones con registro desde 1981
  ({", ".join(COD_PLUVIO[c].split(" (")[0] for c in pl_estrella_red)}), sin Pueblo Viejo en ningún año, sin los tramos excluidos
  de siempre, sin rachas de valores repetidos y sin {int((pl_estrella_excluidos.motivo == "pico extremo que los vecinos no acompañan").sum())} picos extremos que los
  vecinos no acompañan. Si la red cambiara de composición con los años (como la PL de siempre, a la que Pueblo Viejo entra en
  2004), ese cambio aparecería como una tendencia. El resto del informe sigue usando PL.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Mes</th>{"".join(f"<th class='num'>{v} <small>({LARGO_UNIDADES[v]})</small></th>" for v in LARGO_VARS)}</tr></thead>
    <tbody>
{anz_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">µ<sub>j</sub> / s<sub>j</sub> (n), con n el número de años válidos de cada mes en {ANZ_REFERENCIA[0].year}–{ANZ_REFERENCIA[1].year}.</p>

  <div class="pestanas" role="tablist" aria-label="Qué variables mostrar">
{anz_botones}
  </div>
  <div role="tabpanel" id="panel-anz" aria-labelledby="pestana-anz-0">
    <div id="g-anz" class="grafico" style="min-height:0; height:720px"></div>
  </div>
  <p class="nota">Arriba la serie original, en el medio la anomalía y abajo la anomalía estandarizada. Fondo: naranja en los
  meses de El Niño y azul en los de La Niña, según el ONI de la NOAA ({CITA_ONI}); sin color, neutro. Las líneas punteadas
  marcan el período de referencia. En a y z, la línea discontinua es la tendencia lineal del registro completo (ver «Tendencias de
  largo plazo»).</p>

  <h3>Qué conserva y qué cambia cada una</h3>
  <ul>
    <li><b>X<sub>t</sub></b> lo conserva todo: las unidades, el nivel, el ciclo anual y la variación de un año a otro.</li>
    <li><b>a<sub>t</sub></b> quita el ciclo anual medio y conserva las unidades y la diferencia de variabilidad entre meses:
    un febrero lluvioso puede alejarse más de su media que un agosto. En la lluvia y el caudal, quitar el ciclo cambia mucho
    la serie (correlación de X con a: {anz_forma["PL*"]["r_x_a"]:.2f} con PL*, {anz_forma["PI"]["r_x_a"]:.2f} con PI y
    {anz_forma["Q"]["r_x_a"]:.2f} con Q); en la temperatura casi nada ({anz_forma["T media"]["r_x_a"]:.2f} con la media),
    porque su ciclo anual es pequeño frente a lo que cambia de un año a otro.</li>
    <li><b>z<sub>t</sub></b> quita además esa diferencia de variabilidad: pone todos los meses, y todas las variables, en la
    misma escala. Cambia poco la forma de la serie (correlación de a con z entre {min(f["r_a_z"] for f in anz_forma.values()):.2f}
    y {max(f["r_a_z"] for f in anz_forma.values()):.2f}), pero un +50 mm en el mes más variable pesa menos que en el más estable.</li>
  </ul>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th class="num">Años por mes (n)</th><th class="num">Ancho del IC 95 % de s<sub>j</sub></th>
    <th class="num">Asimetría de z</th><th class="num">Meses con |z| &gt; {ANZ_UMBRAL_Z:.0f}</th><th class="num">Shapiro-Wilk p</th>
    <th class="num">r(X, a)</th><th class="num">r(a, z)</th></tr></thead>
    <tbody>
{anz_forma_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">En el período de referencia. El ancho del intervalo de s<sub>j</sub> (remuestreando años) se da
  relativo al propio s<sub>j</sub>, del mes más preciso al menos preciso. En una normal, |z| &gt; {ANZ_UMBRAL_Z:.0f}
  en el {anz_normal_extremos:.1f} % de los meses.</p>
  <p><b>Ningún s<sub>j</sub> es cero</b>, así que la estandarización está definida en todos los meses. Los de la
  temperatura son pequeños en grados, pero eso no los hace inestables: con {anz_n["T media"].min()} años se estiman con
  una imprecisión relativa parecida a la de la lluvia. <b>La inestabilidad que pesa está en Q</b>: tiene entre
  {anz_n["Q"].min()} y {anz_n["Q"].max()} años por mes y, en sus meses menos precisos, el intervalo de s<sub>j</sub> mide
  hasta el {anz_ancho_rel["Q"].max():.0f} % del propio s<sub>j</sub>, porque uno o dos años extremos lo dominan. Allí un
  z grande puede deberse en parte a un s<sub>j</sub> mal estimado.</p>
  <p><b>Estandarizar no es normalizar.</b> z tiene media 0 y desviación 1 en cada mes, pero conserva la forma de la
  distribución: Q sigue cargada hacia los meses muy húmedos (asimetría {anz_forma["Q"]["asim"]:+.2f}) y la prueba de
  Shapiro-Wilk ({CITA_SHAPIRO}) rechaza la normalidad en {(", ".join(anz_no_normales[:-1]) + " y " + anz_no_normales[-1]) if len(anz_no_normales) > 1 else (anz_no_normales[0] if anz_no_normales else "ninguna")}.
  Por lo mismo, z <b>no es el SPI</b>: el índice estandarizado de precipitación ajusta primero una distribución a la
  lluvia y la transforma después en una normal, cosa que aquí no se hace.</p>
  <p class="nota">Las anomalías de «Revisión de outliers» y «Años que se salen de lo normal» son otras: se miden respecto a la
  mediana y en rangos intercuartiles, para buscar extremos sin que los propios extremos muevan la referencia. Se usan
  tal como estaban.</p>
</section>

<section>
  <h2>Años que se salen de lo normal</h2>
  <p>La <b>anomalía</b> de un mes es cuánto se aleja del valor normal de su mes del calendario, en rangos
  intercuartiles (la misma medida de «Revisión de outliers»): un abril más seco o más lluvioso que un abril
  normal. Quita el ciclo anual y deja la variación de un año a otro.</p>
  <h3>Las nubes del caudal, sin el calendario</h3>
  <p>Con los valores tal cual, parte de la relación entre lluvia y caudal viene de que comparten el calendario.
  Con anomalías, la de PL con Q pasa de ρ = {anom_rho["PL–Q"]["tal cual"]:.2f} a <b>{anom_rho["PL–Q"]["anomalías"]:.2f}</b>, la de
  PI con Q de {anom_rho["PI–Q"]["tal cual"]:.2f} a {anom_rho["PI–Q"]["anomalías"]:.2f} y la de PI con PL de
  {anom_rho["PI–PL"]["tal cual"]:.2f} a {anom_rho["PI–PL"]["anomalías"]:.2f}. <b>Un mes más lluvioso de lo normal trae más
  caudal de lo normal</b>, y con PL la relación se pierde menos que con PI.</p>
  <div id="g-anom-dispersion" class="grafico" style="min-height:0; height:440px; max-width:620px"></div>
  <p class="nota">Cada punto es un mes; en color, los años contrastantes.</p>
  <h3>Los años contrastantes</h3>
  <p>Los {ANOM_N_EXTREMOS} años más húmedos y los {ANOM_N_EXTREMOS} más secos según el promedio de las anomalías de PL y
  PI, para quedarse con años en que las dos fuentes de lluvia coinciden{(": con PL sola habría entrado " + ", ".join(f"{a} (PI {anom_anual.PI[a]:+.2f})" for a in anom_solo_pl)) if anom_solo_pl else ""}.
  La anomalía de Q solo se calcula en los {anom_n_q} años con los 12 meses; en ellos sigue a la de PL
  (ρ = {anom_rho_anual_pl_q:.2f}).</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Año</th><th class="num">Anomalía PL</th><th class="num">PI</th><th class="num">Q</th>
    <th class="num">PL del año (mm)</th><th class="num">Meses sobre lo normal</th><th>Picos</th><th class="num">A₂/A₁</th>
    <th>ENSO (meses)</th></tr></thead>
    <tbody>
{anom_filas}
    </tbody>
  </table>
  </div>
  <div class="pestanas" role="tablist" aria-label="Contra qué comparar">
    <button type="button" role="tab" id="pestana-anomc-0" aria-controls="panel-anomc" aria-selected="true">Contra el año típico</button>
    <button type="button" role="tab" id="pestana-anomc-1" aria-controls="panel-anomc" aria-selected="false" tabindex="-1">PL contra PI</button>
  </div>
  <div role="tabpanel" id="panel-anomc" aria-labelledby="pestana-anomc-0">
    <div id="g-anom-ciclo" class="grafico" style="min-height:0; height:440px"></div>
  </div>
  <p class="nota">Primera pestaña: PL mes a mes de cada año contrastante, contra el año típico (la mediana de cada mes,
  {n(anom_tipico_pl)} mm en el año). Segunda: cada año por separado, PL (línea continua) contra PI (discontinua).</p>
  <p><b>PL y PI no se separan igual todos los años.</b> En {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}, PL suma en promedio
  {anom_pl_pi_habitual:.2f} veces lo de PI. En los años contrastantes:
  {"; ".join(f"{a}, {r['razon']:.2f} ({n(r['pl_total'])} contra {n(r['pi_total'])} mm)" for a, r in anom_pl_pi.items())}.
  <b>{anom_pl_pi_raro} es el que más se aparta</b>, y la diferencia se concentra en
  {", ".join(anom_pl_pi[anom_pl_pi_raro]["meses_dif"][:-1])} y {anom_pl_pi[anom_pl_pi_raro]["meses_dif"][-1]}: los pluviómetros
  registraron mucha más lluvia que el satélite en esos meses. Con los datos disponibles no se puede saber cuál de los dos
  se acerca más a la lluvia real; por eso el año se clasifica con PL y PI juntas.</p>
  <p><b>{"Hasta en los años extremos el régimen sigue siendo bimodal" if anom_todos_bimodales else "En algún año extremo el régimen deja de ser bimodal"}</b>:
  lo que cambia de un año a otro es sobre todo cuánto llueve, no la forma.{"".join(f" En {a} el armónico de 12 meses pesa más (A₂/A₁ {anom_anios[a]['razon']:.2f}): sus meses muy húmedos ({', '.join(m)}) rellenan en parte el valle entre los dos picos." for a, m in anom_a1_domina.items())} Un año húmedo tiene la mayoría de sus meses
  sobre lo normal ({anom_anios[anom_humedos[0]]["meses_sobre"]} de 12 en {anom_humedos[0]}) y uno seco, pocos
  ({anom_anios[anom_secos[0]]["meses_sobre"]} de 12 en {anom_secos[0]}). Los dos más contrastantes coinciden con el ENSO:
  {anom_humedos[0]}, con {anom_anios[anom_humedos[0]]["nina"]} meses de La Niña, y {anom_secos[0]}, con
  {anom_anios[anom_secos[0]]["nino"]} de El Niño; es una coincidencia observada, no una causa demostrada. El mes más extremo
  de toda la serie es {MESES_LARGOS_ES[anom_mes_extremo.month - 1]} de {anom_mes_extremo.year}: PL
  {n(variables_resumen.loc[anom_mes_extremo, "PL"])} mm, {variables_resumen.loc[anom_mes_extremo, "PL"] / anom_mediana_pl[anom_mes_extremo.month]:.1f}
  veces su mediana, y caudal atípico también ({atip_z.loc[anom_mes_extremo, "PL"]:+.1f}, {atip_z.loc[anom_mes_extremo, "PI"]:+.1f} y
  {atip_z.loc[anom_mes_extremo, "Q"]:+.1f} rangos intercuartiles con PL, PI y Q).</p>
</section>

<section>
  <h2>Tendencias de largo plazo</h2>
  <p>Aquí la pregunta cambia: no se comparan variables, sino cómo cambia cada una con los años. Por eso cada variable
  se usa con <b>todo su registro</b>, desde {LARGO_DESDE[:4]} cuando existe, y no solo en {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}:
  la menor duración de IMERG no recorta a las demás. Aparte, todo se repite en el período común
  {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}, para comparar fuentes con la misma ventana.</p>
  <div class="resumen-caja">
  <h3>En resumen: cuánto cambia cada variable por década</h3>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th>Período</th><th class="num">Pendiente de X<br><small>(unidades de la variable por década)</small></th><th class="num">Pendiente de z<br><small>(unidades estandarizadas/década)</small></th>
    <th>Lectura</th></tr></thead>
    <tbody>
{res_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">Pendiente por década ± intervalo de 95 % (mínimos cuadrados con una constante por mes y error de
  Newey-West), sobre el registro completo de cada variable. En la lluvia (PL* y PI), la pendiente es el cambio del
  <b>acumulado mensual</b>, en mm/mes por década, <b>no del total anual</b>. z está en unidades estandarizadas (desviaciones
  estándar del mes) por década, comparable entre variables. «Con los dos métodos»: significativa con la recta (Newey-West)
  y con Mann-Kendall estacional (p &lt; {TEND_ALFA}).</p>
  </div>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th>Fuente</th><th>Desde</th><th>Hasta</th><th class="num">Meses</th>
    <th class="num">Válidos</th><th class="num">Vacíos</th><th>Cambios de fuente o de procesamiento</th></tr></thead>
    <tbody>
{largo_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">«Registro completo» no quiere decir rellenado: los meses vacíos quedan vacíos. PL* (la red fija, ver
  «Anomalías y anomalías estandarizadas») no tiene ningún mes vacío porque cada mes se promedia con las estaciones que tienen dato.</p>
  <p><b>El registro largo se revisó antes de usarlo</b>, con las mismas pruebas del control de calidad. <b>Q</b>:
  {n(largo_qc["q_dias_sin_dato"])} de {n(largo_qc["q_dias"])} días sin dato, sin rachas de valores repetidos, sin picos aislados y sin
  salto en el coeficiente de escorrentía anual ({largo_qc["coef_anios"]} años, Pettitt p = {largo_qc["coef_p"]:.2f}), así que la
  estación no muestra un cambio de curva de gasto; su media casi no cambia ({largo_qc["q_media_antes"]:.1f} m³/s en
  {LARGO_DESDE[:4]}–{ANIOS_ESTUDIO[0] - 1} y {largo_qc["q_media_despues"]:.1f} en {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}).
  <b>Temperatura de ERA5-Land</b>: sin días faltantes, sin rachas y sin días en que la media se salga de la mínima y la máxima;
  pero frente a MSWX la diferencia cambia {largo_qc["mswx_salto"]:+.2f} °C después de {largo_qc["mswx_corte"]} (Pettitt p
  {_p_txt(largo_qc["mswx_p"])}) y, sin un termómetro en la cuenca, no se sabe cuál de los dos productos salta: queda como
  incertidumbre de su tendencia. <b>PL*</b>: se quitaron
  {int((pl_estrella_excluidos.motivo == "pico extremo que los vecinos no acompañan").sum())} picos que los vecinos no acompañan
  ({"; ".join(f"{COD_PLUVIO[r.codigo].split(' (')[0]} {fmt_mes(pd.Period(r.fecha[:7], 'M'))}: {r.precipitacion_mm:.0f} mm" for r in pl_estrella_excluidos[pl_estrella_excluidos.motivo == "pico extremo que los vecinos no acompañan"].itertuples())};
  criterio de <code>scripts/07</code>: más de {PICO_VECES_MEDIANA_INF:.0f} veces la mediana del mes, más de {PICO_MINIMO_INF:.0f} mm y
  más de {PICO_VECES_VECINOS_INF:.0f} veces el promedio de los vecinos) y los meses de
  {len(pl_estrella_rachas)} racha{"s" if len(pl_estrella_rachas) != 1 else ""} de valores repetidos
  ({"; ".join(f"{COD_PLUVIO[r.codigo].split(' (')[0]}, {r.meses} meses desde {fmt_mes(pd.Period(r.desde, 'M'))} con {r.valor_mm:.0f} mm" for r in pl_estrella_rachas.itertuples())}),
  porque no se sabe cuál valor es el rellenado. Coromoro (desde 2003) y Valle de San José (desde 1998) tienen un salto de
  nivel marcado como incierto; su efecto se prueba abajo.</p>

  <h3>Tres maneras de medir una tendencia</h3>
  <p>Se usan tres aproximaciones, que responden preguntas distintas:</p>
  <ul>
    <li><b>Mínimos cuadrados (OLS)</b>, un ajuste <i>paramétrico</i>: X<sub>t</sub> = β₀ + β₁t + ε<sub>t</sub> (y lo mismo con a y z).
    Da una recta y su pendiente β₁. Para la serie original se compara además con un ajuste con una constante por mes del
    calendario (efectos estacionales), para que el ciclo anual no se confunda con tendencia.</li>
    <li><b>Mann-Kendall con la pendiente de Sen</b> ({CITA_MANN}; {CITA_SEN}), una prueba <i>no paramétrica</i>: pregunta si
    los valores tienden a crecer (o decrecer) con el tiempo, sin suponer una recta ni una distribución. «No paramétrico» no
    quiere decir «no lineal»: también da una sola pendiente y no reconstruye una curva. Para la serie original, en su
    variante estacional ({CITA_HIRSCH}), que compara cada mes solo con el mismo mes de otros años.</li>
    <li><b>LOESS</b> ({CITA_LOESS}), una curva <i>no lineal</i>: una recta local que se va moviendo por el registro, con una
    ventana del {MET_FRAC * 100:.0f} % de los datos. Muestra la forma (si sube, baja o se invierte), pero es una
    <b>curva exploratoria</b>: su banda sale de un remuestreo, no de un modelo con una prueba formal. Como contraste, una
    <b>regresión segmentada</b> prueba si hay evidencia de un cambio de pendiente.</li>
  </ul>
  <p>Todas las pendientes van <b>por década</b>, en las unidades de la variable (°C/década, m³/s por década, desviaciones
  estándar por década en z). En la lluvia son el cambio del <b>acumulado mensual</b> (mm/mes por década), no del total
  anual.</p>

  <h3>Todos los datos: la secuencia de meses</h3>
  <p><b>Diagnóstico de los residuos.</b> En las {len([1 for (v, per) in met_global if per == "completo"])} variables, los residuos del
  ajuste están autocorrelacionados (prueba de Ljung-Box con {MET_LB_REZAGOS} rezagos, p &lt; {TEND_ALFA}): un mes húmedo suele
  seguir a otro. {"No hay cambios de dispersión con el tiempo en el registro completo" if not met_hetero else "La dispersión cambia con el tiempo en " + ", ".join(met_hetero)}
  (Breusch-Pagan), y varios residuos no son normales (Shapiro-Wilk). Con dependencia, el error estándar usual
  subestima la incertidumbre, así que la inferencia se apoya en el de <b>Newey-West</b> ({CITA_NEWEY}), robusto a
  autocorrelación y heterocedasticidad: su intervalo es, en la mediana, {met_hac_mas_ancho:.1f} veces el usual. En
  Mann-Kendall, la p de la serie original sale de <b>permutar años completos</b> ({MET_REMUESTREOS} veces: los doce meses de
  un año viajan juntos, lo que conserva la dependencia dentro del año) y en a y z se corrige la varianza por
  autocorrelación ({CITA_HAMED}).</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th>Período</th><th class="num">Meses</th><th class="num">X: OLS</th>
    <th class="num">X: OLS con meses</th><th class="num">a: OLS</th><th class="num">z: OLS</th>
    <th class="num">r₁ / Ljung-Box p</th><th class="num">Breusch-Pagan p</th><th class="num">Shapiro-Wilk p</th></tr></thead>
    <tbody>
{met_ols_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">OLS: pendiente por década ± intervalo de 95 % con el error de Newey-West ({TEND_REZAGOS} meses); en a, también el
  intervalo usual, para compararlo. Diagnóstico sobre los residuos del ajuste de a. En negrita, p &lt; {TEND_ALFA}.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th>Período</th><th class="num">Meses</th><th class="num">X: Sen estacional [IC 95 %]</th>
    <th class="num">a: Sen [IC 95 %]</th><th>LOESS de a: cambio y forma</th><th class="num">Segmentada: ΔBIC</th></tr></thead>
    <tbody>
{met_np_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">Sen estacional: IC remuestreando años completos y p permutándolos. Sen de a: IC de Kendall y p con la corrección de
  Hamed y Rao (entre paréntesis, la p sin corregir). LOESS: cambio entre el comienzo y el final de la curva y sus tramos
  (se ignoran ondulaciones menores que {MET_UMBRAL_FORMA:.2f} s<sub>j</sub>). ΔBIC positivo favorece un quiebre de pendiente; se
  exige más de {MET_DELTA_BIC}.</p>
  <div class="pestanas" role="tablist" aria-label="Qué variable">
{met_botones_var}
  </div>
  <div class="pestanas" role="tablist" aria-label="Qué representación">
{met_botones_rep}
  </div>
  <div role="tabpanel" id="panel-met" aria-labelledby="pestana-met-v0">
    <div id="g-met" class="grafico" style="min-height:0; height:380px"></div>
  </div>
  <p class="nota">Registro completo de cada variable. Fondo: naranja El Niño, azul La Niña. Gris: los meses. Línea discontinua: la recta OLS. Línea y banda de color:
  la curva LOESS y su banda de 95 % (remuestreo de residuos por bloques de {MET_BLOQUE} meses).</p>
  <ul>
    <li><b>La temperatura sube</b> en las tres series desde {LARGO_DESDE[:4]}, y los tres métodos coinciden: OLS
    {met_global[("T media", "completo")]["ols_a"]["pend"]:+.2f} ± {met_global[("T media", "completo")]["ols_a"]["ic_hac"]:.2f} °C/década en la media
    (Newey-West), Sen {met_global[("T media", "completo")]["mk_a"]["pend"]:+.2f}, y una curva LOESS que sube sin
    invertirse en todo el registro. Ninguna variable muestra evidencia de un cambio de pendiente (ΔBIC menor que
    {MET_DELTA_BIC} en todas): una subida gradual describe los datos tan bien como una con quiebre. En
    {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]} solo, la señal es más débil y depende del método: con la mitad de los años, el
    intervalo se abre y la curva LOESS ondula.</li>
    <li><b>La lluvia no muestra tendencia.</b> Con PL*, {met_global[("PL*", "completo")]["ols_Xmes"]["pend"]:+.1f} mm/mes por década en
    {LARGO_DESDE[:4]}–{ANIOS_ESTUDIO[-1]} (OLS con Newey-West, p {_p_txt(met_global[("PL*", "completo")]["ols_Xmes"]["p_hac"])}; Sen estacional,
    p {_p_txt(met_global[("PL*", "completo")]["mk_X"]["p"])}) y {met_global[("PL*", "1998–2022")]["ols_Xmes"]["pend"]:+.1f} en
    {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]} (p {_p_txt(met_global[("PL*", "1998–2022")]["ols_Xmes"]["p_hac"])}). Sin las dos estaciones con
    salto, {tend_pl_sens["sin_saltos"]["ols"]:+.1f} (p {_p_txt(tend_pl_sens["sin_saltos"]["p"])}). La PL de siempre, cuya red cambia
    de composición, daba {tend_pl_sens["red_9822"]["ols"]:+.1f} mm/mes por década en {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}, y Mann-Kendall
    sin corregir la daba significativa (p {_p_txt(tend_pl_sens["red_9822"]["p_mk"])}). Como PL* y PL se parecen mes a mes
    (r = {tend_pl_sens["r_9822"]:.2f}), esa caída venía sobre todo de los cambios de la red (Pueblo Viejo, que mide menos que sus
    vecinos, entra en 2004 y baja su nivel en 2014), no de la lluvia. <b>PI tampoco muestra tendencia.</b></li>
    <li><b>Q no tiene tendencia</b> con ningún método, ni en el registro completo ni en {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}. Sus
    curvas LOESS ondulan (baja, sube y vuelve a bajar), pero esas ondas cambian con la ventana y caben dentro de la banda:
    no se deben leer como cambios físicos.</li>
  </ul>
  <p>Entre la serie original sin y con constantes por mes, y frente a a, la pendiente casi no cambia (en a y X con meses
  difieren a lo sumo un {tend_dif_x_a:.1f} %). Lo que sí cambia es la incertidumbre: sin controlar el mes, el ciclo anual queda en
  el residuo y ensancha el intervalo. a y z no son evidencias aparte: son la misma información en otra escala.</p>

  <h3>Sensibilidad de la curva LOESS</h3>
  <p><b>La subida de la temperatura no depende de cómo se suavice:</b> con las tres ventanas la curva sube entre
  {min(met_sens[v][f"frac {fr}"]["cambio"] for v in ("T mín", "T media", "T máx") for fr in MET_FRACS):+.2f} y
  {max(met_sens[v][f"frac {fr}"]["cambio"] for v in ("T mín", "T media", "T máx") for fr in MET_FRACS):+.2f} °C en el registro, y los meses
  extremos casi no la mueven. <b>Las ondulaciones de la lluvia y de Q sí dependen de la ventana</b> (cambia el número de tramos
  y, en {", ".join(v for v in ("PL*", "PI", "Q") if len({np.sign(met_sens[v][f"frac {fr}"]["cambio"]) for fr in MET_FRACS}) > 1)}, hasta el signo):
  no se pueden leer como cambios físicos. <b>Los bordes son lo menos confiable</b> de cada curva (banda
  {np.mean([s["borde_vs_centro"] for s in met_sens.values()]):.1f} veces más ancha), y nada se extrapola fuera del registro.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th>{"".join(f"<th class='num'>Ventana {fr * 100:.0f} %</th>" for fr in MET_FRACS)}
    <th class="num">Efecto de los extremos</th><th class="num">Banda en los bordes</th></tr></thead>
    <tbody>
{met_sens_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">Sobre a, registro completo. Ventanas: cambio de la curva de principio a fin (y tramos de subida o bajada).
  Extremos: diferencia máxima sin las iteraciones robustas. Bordes: ancho de la banda en el primer y último 10 % frente al centro.</p>

  <h3>¿Tendencia gradual o salto?</h3>
  <p><b>En la lluvia y en el caudal no hay saltos de nivel.</b> <b>En la temperatura, la prueba de Pettitt ({CITA_PETTITT}) sí marca uno</b>
  ({", ".join(f"{v} después de {salto[v]['anio_corte']}" for v in salto_con_corte)}), pero <b>es la misma subida gradual vista de
  otra forma</b>: una serie que sube parejo siempre tiene un «antes bajo» y un «después alto». Al quitar la recta no queda
  ningún salto, y una recta y un escalón describen los datos casi igual de bien. Con estos datos no se puede distinguir una
  tendencia gradual de un salto; lo que sí se puede decir es que no hay un salto además de la tendencia. Tampoco aparece un
  salto en 1993–1996, donde cambia la diferencia con MSWX, lo que apunta (sin probarlo) a que ese salto es de MSWX.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th class="num">Años</th><th class="num">Salto después de</th><th class="num">p (anual)</th>
    <th class="num">p (mensual, permutando años)</th><th class="num">Antes → después</th>
    <th class="num">p sin la recta</th><th>Mejor modelo (BIC)</th></tr></thead>
    <tbody>
{salto_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">Sobre la media anual de la anomalía a (años con al menos {SALTO_MIN_MESES} meses), registro completo. «p sin la
  recta»: Pettitt sobre los residuos de la tendencia lineal. Modelos: recta, escalón en el año de Pettitt, y recta más escalón;
  «empate» si el mejor le gana al segundo por menos de {SALTO_DBIC_EMPATE:.0f} de BIC. Los modelos solo se comparan
  donde Pettitt marca un salto: como el año del escalón lo elige la propia prueba, en las demás el BIC favorecería al
  escalón sin que haya salto. En negrita, p &lt; {TEND_ALFA}.</p>

  <h3>Mes a mes: las doce subseries</h3>
  <p>Cada mes del calendario se toma por separado (todos los eneros, todos los febreros…) y se ajusta su pendiente a
  través de los años. No se ajusta una tendencia a las doce medias climatológicas: eso describiría el ciclo anual, no su
  cambio en el tiempo.</p>
  <div class="pestanas" role="tablist" aria-label="Qué período">
{tend_botones}
  </div>
  <div role="tabpanel" id="panel-tend" aria-labelledby="pestana-tend-0">
    <div id="g-tend-mes" class="grafico" style="min-height:0; height:380px"></div>
  </div>
  <p class="nota">Color: pendiente de z por década (en desviaciones estándar, para comparar variables). Con asterisco,
  p &lt; {TEND_ALFA} (OLS), sin corregir por comparaciones múltiples (la corrección va abajo). Al pasar el cursor, la pendiente en las unidades de la variable.</p>
  <p><b>Dentro de un mismo mes y con la misma muestra, restar µ<sub>j</sub> no cambia la pendiente y dividir por
  s<sub>j</sub> solo la cambia de escala; la p es la misma en las tres representaciones.</b> El script lo comprueba en las
  {len(LARGO_VARS) * 12 * len(TEND_PERIODOS)} subseries y se detiene si no se cumple. Por eso el mapa muestra solo z: X y a
  dirían lo mismo en otra escala.</p>
  <p><b>Corrigiendo por comparaciones múltiples, la temperatura sigue subiendo en muchos meses del año y la lluvia solo
  en marzo.</b> Con doce pruebas por variable, algún mes saldría significativo solo por azar; por eso se controla la tasa de
  falsos descubrimientos con Benjamini y Hochberg ({CITA_BH}), tomando como familia las 12 subseries de cada variable
  (q &lt; {INC_Q_FDR}).</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Variable</th><th>Meses con p &lt; {TEND_ALFA} (sin corregir)</th><th>Con FDR (OLS)</th>
    <th>Con FDR (Mann-Kendall)</th></tr></thead>
    <tbody>
{fdr_filas}
    </tbody>
  </table>
  </div>
{marzo_html}
  <div class="pestanas" role="tablist" aria-label="Qué variable">
{pend_botones}
  </div>
  <div role="tabpanel" id="panel-pend" aria-labelledby="pestana-pend-v0">
    <div id="g-pend-mes" class="grafico" style="min-height:0; height:380px"></div>
  </div>
  <p class="nota">Pendiente por década de cada mes, en las unidades de la variable, con su intervalo de 95 %: círculo, OLS;
  rombo, Sen. Relleno: significativa después de la corrección FDR (q &lt; {INC_Q_FDR}); hueco: no.</p>
  <p><b>Cada subserie, con los tres métodos.</b> Todas tienen al menos {min(r["n"] for r in met_mes.values())} años, suficientes para una
  recta y para Mann-Kendall; la curva LOESS (ventana del {MET_FRAC_MES * 100:.0f} %) se muestra solo como descripción de la forma,
  porque con 20 a 42 puntos cualquier ondulación es frágil. Dependencia: de un año al siguiente casi no hay (autocorrelación
  de lag 1 significativa en {met_mes_r1} de {len(met_mes)} subseries, marcadas con *), así que en cada mes se usan la OLS y el
  Mann-Kendall usuales, con el intervalo de Sen de Kendall. Varias subseries de la lluvia y de Q suben y después bajan (o al
  revés): una sola pendiente puede ocultar esas inversiones, pero con tan pocos años no hay base para darlas por cambios reales.</p>
{met_mes_detalles}

  <h3>Significativo no es lo mismo que importante</h3>
  <p><b>«No significativo» no quiere decir «sin cambio».</b> El intervalo dice cuánto cambio no se puede descartar: en la
  lluvia de PL*, entre {inc_no_descartable["PL*"]["lo"]:+.1f} y {inc_no_descartable["PL*"]["hi"]:+.1f} mm/mes por década
  ({inc_no_descartable["PL*"]["lo_pct"]:+.1f} % a {inc_no_descartable["PL*"]["hi_pct"]:+.1f} % de su media); en PI, entre
  {inc_no_descartable["PI"]["lo"]:+.1f} y {inc_no_descartable["PI"]["hi"]:+.1f}; en Q, entre {inc_no_descartable["Q"]["lo"]:+.2f} y
  {inc_no_descartable["Q"]["hi"]:+.2f} m³/s por década ({inc_no_descartable["Q"]["lo_pct"]:+.1f} % a {inc_no_descartable["Q"]["hi_pct"]:+.1f} %).
  Lo que se puede afirmar es que, si la lluvia o el caudal cambian, cambian menos que eso.</p>
  <p><b>«Significativo» no quiere decir «hidrológicamente importante».</b> El calentamiento sí es significativo, pero en la
  fórmula de Hargreaves de la ETP ({CITA_FAO}) significa un {inc_etp["rel_pct"]:.2f} % más por década: unos
  {inc_etp["decada"]:.1f} mm/año sobre {n(inc_etp["anual"])} mm/año, o {inc_etp["registro"]:.0f} mm/año en todo el registro. Es
  menos que lo que la lluvia puede estar cambiando sin que se note (±{inc_etp["pl_ic_anual"]:.0f} mm/año por década con PL*):
  hoy, el efecto del calentamiento en el balance de agua de la cuenca es pequeño frente a la incertidumbre de la lluvia.</p>
  <p class="nota">ETP de Hargreaves como en <code>scripts/06b</code>, con la radiación fija; su cambio relativo se calcula a primer
  orden con las pendientes por década del punto medio de la temperatura ({inc_etp["d_tm"]:+.2f} °C) y de la amplitud diaria
  ({inc_etp["d_td"]:+.2f} °C). La ETP anual es la media de {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}. Los mm/mes de la lluvia se pasan a
  mm/año multiplicando por 12.</p>
</section>

<section>
  <h2>Frecuencias: análisis de Fourier</h2>
  <p>El espectro de potencia dice cómo se reparte la varianza de una serie entre escalas de tiempo: el ciclo anual
  (12 meses), el semianual (6 meses, el régimen bimodal), la variabilidad interanual (de 3 a 7 años, la escala del ENSO) y la
  alta frecuencia (menos de 6 meses). Se calcula para PL, PI, Q y T en tres versiones: la serie original, su anomalía (sin el
  ciclo anual) y la anomalía sin tendencia.</p>
  <ul>
    <li{_cambio('Cambio de la revisión · bandas con ±Δf, remisión a «El régimen» y la ZCIT')}><b>El espectro confirma el régimen bimodal</b> (ver «El régimen» en «El ciclo anual»): la lluvia y el caudal tienen
    su pico en 6 meses, no en 12: es el ritmo del doble paso de la Zona de Convergencia Intertropical (ZCIT) sobre el centro
    de Colombia, que trae dos temporadas de lluvias al año ({CITA_MESA}; {CITA_POVEDA}). La banda semianual tiene el
    {fou[(_fc, "PL", "original")]["bandas"]["semianual"]:.0f} % de la varianza de PL, el {fou[(_fc, "PI", "original")]["bandas"]["semianual"]:.0f} % de la de PI
    y el {fou[(_fc, "Q", "original")]["bandas"]["semianual"]:.0f} % de la de Q. Estos porcentajes no se comparan con los de «El régimen»:
    allí son de la forma del año típico (las 12 medias); aquí, de la varianza de todos los meses.</li>
    <li{_cambio('Nuevo · la temperatura')}><b>En la temperatura, el ciclo anual pesa poco</b>: su pico más alto está en {fou[(_fc, "T", "original")]["pico"]:.0f} meses,
    pero la banda anual tiene solo el {fou[(_fc, "T", "original")]["bandas"]["anual"]:.0f} % de su varianza y la interanual, el
    {fou[(_fc, "T", "original")]["bandas"]["interanual"]:.0f} %: la temperatura varía más de un año a otro que dentro del año. Coincide
    con «Lo que solo se ve al quitar el ciclo anual», donde el ciclo explica solo el {corr_peso_ciclo['T ERA5']:.0f} % de la variación de T.</li>
    <li{_cambio('Nuevo · lo que se atenúa al retirar la climatología')}><b>Al retirar la climatología, las bandas anual y
    semianual se reducen a menos de una décima parte</b>: juntas pasan, de la serie original a la anomalía, {fou_atenua_txt}
    de la varianza. Lo que queda se reparte entre la alta frecuencia y la banda interanual, que pesan más en proporción porque
    el total se achica (ver la pestaña «anomalía» de la tabla).</li>
    <li{_cambio('Nuevo · las dos fuentes de lluvia')}><b>PI y PL coinciden en el pico de 6 meses, pero no en la banda de 12</b>:
    la semianual tiene el {fou_fuentes["PL"]["semianual"]:.1f} % de la varianza de PL y el {fou_fuentes["PI"]["semianual"]:.1f} % de la de
    PI, pero la anual tiene el {fou_fuentes["PI"]["anual"]:.1f} % en PI y apenas el {fou_fuentes["PL"]["anual"]:.1f} % en PL. El satélite
    ve un ciclo de 12 meses que los pluviómetros casi no tienen; coincide con «El régimen», donde el armónico de 12 meses explica el
    {regimen["PI"]["var1"]:.0f} % de la forma del año típico de PI y el {regimen["PL"]["var1"]:.0f} % de la de PL. En las anomalías, en
    cambio, las dos fuentes se reparten la varianza casi igual: ninguna banda difiere más de {fou_fuentes_anom_dif:.1f} puntos
    porcentuales (alta frecuencia: {fou_fuentes_anom["PL"]["alta"]:.1f} % en PL y {fou_fuentes_anom["PI"]["alta"]:.1f} % en PI). {fou_fuentes_oni_txt}
    No se puede decidir cuál fuente tiene la razón: por eso se llevan las dos.</li>
    <li{_cambio('Cambio de la revisión · remisión al desfase y persistencia')}><b>El caudal es más suave que la lluvia</b>: en las anomalías, la alta frecuencia es el {fou_alta_q:.0f} % de la
    varianza de Q y el {fou_alta_lluvia:.0f} % de la lluvia (promedio de PL y PI). Es la misma memoria de la cuenca que
    muestran «Desfase estacional» (el río va {desfase["Q_PL"]:.0f} días detrás de PL) y la correlación cruzada (sin el ciclo
    anual, la lluvia del mes anterior sigue aportando: correlación parcial de {memoria.loc['PL', 'parcial_mes_anterior']:.2f}),
    vista ahora en frecuencia: el agua que se guarda en el suelo y el acuífero filtra las fluctuaciones rápidas. La
    persistencia lo confirma: la autocorrelación de un mes al siguiente, en las anomalías sin tendencia, es
    {fou_phi["Q"]:.2f} en Q contra {fou_phi["PL"]:.2f} en PL y {fou_phi["PI"]:.2f} en PI. Los vacíos de Q no explican la diferencia:
    con ellos, la alta frecuencia sube en vez de bajar (ver «Qué tan estables son los picos»).</li>
    <li><b>Quitado el ciclo anual, la temperatura varía sobre todo de un año a otro y la lluvia de un mes a otro</b>: la banda
    interanual es el {fou_interanual["T"]:.0f} % de la anomalía de T, el {fou_interanual["Q"]:.0f} % de la de Q y apenas el
    {fou_interanual["PL"]:.0f} y {fou_interanual["PI"]:.0f} % de la de PL y PI.</li>
    <li><b>Ningún pico de las anomalías es una periodicidad clara</b> (prueba contra ruido rojo AR(1)).{"".join(f" Solo {v} ({ven}) supera el ruido rojo, con su pico en {fou[(ven, v, 'anomalía sin tendencia')]['pico']:.0f} meses (p = {fou[(ven, v, 'anomalía sin tendencia')]['ar1_p']:.2f}), pero ese período cabe apenas {c:.1f} veces en el registro y es una de {sum(1 for k in fou if k[2] == 'anomalía sin tendencia')} pruebas: no alcanza para hablar de un ciclo." for (ven, v), c in fou_signif_ciclos.items())} La variabilidad
    interanual existe, pero no tiene un período fijo: el ENSO es casi periódico, y con 25 o 42 años el espectro no puede atribuirle un pico.
    Si la cuenca varía junto con el ENSO lo dice la coherencia (ver «¿Cuadra con el ENSO?»).</li>
    <li{_cambio('Corregido · antes decía que no cambiaba ningún pico')}><b>El registro extendido (1981–2022) no cambia los picos de las series originales</b>: {", ".join(f"{v} {b:.0f} meses" for v, (a, b) in fou_extendida.items())},
    los mismos que en la ventana común (PL* frente a PL). {fou_extendida_txt}</li>
  </ul>

  <div class="pestanas" role="tablist" aria-label="Qué versión de la serie">
{fou_botones_tipo}
  </div>
  <div class="pestanas" role="tablist" aria-label="Qué ventana">
{fou_botones_ven}
  </div>
  <div role="tabpanel" id="panel-fou" aria-labelledby="pestana-fou-t0">
    <div id="g-fou" class="grafico" style="min-height:0; height:420px"></div>
  </div>
  <p class="nota">Periodograma de Lomb-Scargle ({CITA_LOMB}; {CITA_SCARGLE}) normalizado para que el área sea 1 (el 100 % de la
  varianza): compara la forma del espectro entre variables con unidades distintas; la altura no es variabilidad absoluta. Eje
  inferior en ciclos por mes; arriba, el período. Franjas: las bandas de 12 y 6 meses (±Δf), y la banda interanual de 3 a 7 años. La curva punteada
  es el ONI, de referencia: es la misma en las tres versiones, porque el ONI ya es una anomalía.</p>

  <div class="pestanas" role="tablist" aria-label="Qué versión de la serie, en las tablas">
{fou_botones_tabla}
  </div>
{fou_tablas}
  <p class="nota">Ventana común {ANIOS_ESTUDIO[0]}–{ANIOS_ESTUDIO[-1]}. N: meses de la ventana, del primero al último con dato;
  «Con dato»: los observados (Q tiene vacíos). Porcentajes: fracción de la varianza en cada banda. La resolución
  es Δf = 1/N ciclos por mes y, en período, ΔT = T²·Δf: los decimales del pico no dicen más que eso. «Ciclos observados»:
  cuántas veces cabe el período en el registro; con pocos ciclos el pico es incierto. Ruido rojo (solo en la pestaña de la anomalía sin
  tendencia): su pico más alto contra el de {FOU_SIMULACIONES} series AR(1) con la misma autocorrelación y las mismas fechas observadas (al comparar
  el máximo se corrige que se buscó en todas las frecuencias a la vez).</p>

  <details class="plegable-mini"><summary><b>Ventana extendida 1981–2022</b> <small>(PL*, Q y T)</small></summary>
  <p class="nota">Se muestra la misma versión elegida en las pestañas de la tabla de arriba.</p>
{fou_tablas_ext}
  </details>

  <div{_cambio('Nuevo · el método (y las columnas N y «Con dato» de las tablas)')}>
  <h3>Cómo se calcula</h3>
  <p><b>Las series.</b> La secuencia mensual en orden cronológico, no las 12 medias del año típico, con Δt = 1 mes y
  N = {fou[(_fc, "PL", "original")]["N"]} meses en la ventana común ({fou[("extendida 1981–2022", "PL*", "original")]["N"]} en la extendida).
  No se borran meses ni se pegan los que quedan como si fueran seguidos, y no se rellena nada: Q tiene
  {fou[(_fc, "Q", "original")]["N"] - fou[(_fc, "Q", "original")]["n"]} meses vacíos en la ventana común, y por eso el estimador es el
  periodograma de Lomb-Scargle, que trabaja con las fechas observadas. Con muestreo regular y sin vacíos (PL, PI y T), en
  las frecuencias de Fourier coincide con el periodograma clásico de la FFT. Cada serie se centra antes (se le resta su media),
  así que la frecuencia cero, que es la media y no un período, se excluye.</p>
  <p><b>Las frecuencias.</b> f<sub>k</sub> = k/(N·Δt) ciclos por mes, de k = 1 hasta la frecuencia de Nyquist, 0.5 ciclos por mes:
  el período más corto que se puede resolver con datos mensuales es de 2 meses. El período es T<sub>k</sub> = 1/f<sub>k</sub> y la
  resolución, Δf = 1/(N·Δt) = 1/{fou[(_fc, "PL", "original")]["N"]} ciclos por mes. La gráfica usa {FOU_SOBREMUESTREO} puntos por cada frecuencia
  de Fourier: eso solo afina el dibujo, no agrega resolución.</p>
  <p><b>Convención y normalización.</b> Espectro unilateral (solo frecuencias positivas), dividido por su área para que integre 1:
  la altura es la fracción de la varianza por cada ciclo/mes, y el área de una banda es la parte de la varianza que cae en
  ella. Así se comparan formas entre variables con unidades distintas, pero la altura no es variabilidad absoluta.</p>
  <p><b>Fuga y resolución.</b> Un ciclo puro en un registro de N meses no da una línea, sino un pico: su lóbulo principal
  ocupa ±Δf y unos lóbulos laterales reparten algo de su potencia en frecuencias lejanas (la fuga espectral). El espectro
  principal no usa ventana, así que conserva la resolución completa (±Δf) a cambio de esa fuga; por eso las bandas anual y
  semianual miden ±Δf alrededor de 1/12 y 1/6. Las otras dos estimaciones se usan solo para probar la estabilidad de los
  picos. La ventana de Hann baja los lóbulos laterales, con menos fuga, pero ensancha el lóbulo principal a ±2Δf, así que
  pierde la mitad de la resolución. Welch ({CITA_WELCH}) promedia segmentos de {FOU_WELCH_SEGMENTO} meses con ventana de Hann y
  traslape de la mitad: el promedio da un espectro menos ruidoso, pero la resolución baja a 1/{FOU_WELCH_SEGMENTO} ciclos por mes.
  En Q, Welch se reemplaza por Lomb-Scargle promediado en segmentos del mismo largo, que admite los vacíos.</p>
  </div>

  <h3>Qué tan estables son los picos</h3>
  <div{_cambio('Corregido · la ventana en Q, los atípicos, la tendencia y los vacíos de Q')}>
  <p>El pico de la serie original con la FFT y ventana de Hann, contra el de Welch ({CITA_WELCH}), con segmentos de
  {FOU_WELCH_SEGMENTO} meses: {fou_sens_txt}. {fou_ventana_txt}
  Quitar los meses atípicos (los mismos de «Revisión de outliers»: más de {FACTOR_ATIPICO:.1f} rangos intercuartiles por fuera
  de los cuartiles de su mes del calendario) {fou_extremos_efecto}; se quitaron {fou_extremos_txt}.{fou_extremos_nada}</p>
  <p>{fou_tendencia_txt}</p>
  <p>{fou_vacios_txt}</p>
  </div>

  <div{_cambio('Nuevo · coherencia y fase con el ONI')}>
  <h3>¿Cuadra con el ENSO? Coherencia y fase con el ONI</h3>
  <p>El ONI de la NOAA ({CITA_ONI}) es la anomalía de la temperatura del mar en el Pacífico central (región Niño 3.4):
  positivo en El Niño, negativo en La Niña. En el registro largo, el pico más alto de su espectro está en
  {fou_oni["extendida 1981–2022"]["pico"]:.0f} ± {fou_oni["extendida 1981–2022"]["dT"]:.0f} meses, el mismo que el de la anomalía de
  PL* ({fou_plx_ext["pico"]:.0f} ± {fou_plx_ext["dT"]:.0f}). En la ventana común queda en {fou_oni["común 1998–2022"]["pico"]:.0f} ±
  {fou_oni["común 1998–2022"]["dT"]:.0f} meses: con 25 años, el ENSO no alcanza a definir un período.</p>
  <p>Que dos espectros tengan un pico en el mismo período no dice que las series varíen juntas. Eso lo mide la
  <b>coherencia</b> (de 0, nada en común, a 1, la misma señal desplazada), y la <b>fase</b> dice cuál va adelante.
  <b>La lluvia y el caudal varían juntos, y en fase</b>: en la banda de 3 a 7 años la coherencia es {fou_coh_q_txt}, por encima
  del umbral en todos los casos, y Q va entre {fou_coh_q_rezago[0]:.1f} y {fou_coh_q_rezago[1]:.1f} meses detrás de la lluvia.
  <b>Con el ONI van en oposición</b> (fase cerca de ±180°): cuando el Pacífico central se calienta, llueve menos y baja el caudal.
  {fou_coh_oni_txt}</p>
  <p>La correlación simple con el ONI de unos meses antes dice lo mismo. El rezago en que es más negativa es: {fou_corr_oni_txt}.
  El almacenamiento atrasa al río también en la escala del ENSO.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Par</th><th>Ventana</th><th class="num">Coherencia (3–7 años)</th><th class="num">Umbral 95 %</th>
    <th>¿Significativa?</th><th class="num">Fase</th><th>Lectura</th><th class="num">El segundo va detrás (meses)</th></tr></thead>
    <tbody>
{fou_coh_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">Cómo se calcula: anomalías sin tendencia de cada serie (también del ONI), espectro cruzado con segmentos de
  {FOU_WELCH_SEGMENTO} meses, ventana de Hann y traslape de la mitad; la banda de 3 a 7 años queda en las frecuencias de
  {fou_coh[next(iter(fou_coh))]["periodos"][0]:.0f} y {fou_coh[next(iter(fou_coh))]["periodos"][1]:.0f} meses. Umbral: el percentil 95 de la
  coherencia de {FOU_SIMULACIONES} pares de series AR(1) independientes, con la autocorrelación de cada serie y sus mismos vacíos.
  Fase: el ángulo del espectro cruzado; negativa, el segundo de la pareja va detrás. Se lee «en fase» por debajo de
  {FOU_EN_FASE_GRADOS:.0f}° y «en oposición» por encima de {FOU_OPOSICION_GRADOS:.0f}°; solo en fase tiene sentido pasarla a meses.
  <b>Vacíos:</b> la coherencia necesita meses seguidos, así que solo aquí los meses vacíos de Q se toman como anomalía cero (un mes
  normal). Con PL, eso baja la coherencia con el ONI de {fou_coh_vacios["común 1998–2022"][0]:.2f} a {fou_coh_vacios["común 1998–2022"][1]:.2f}
  en la ventana común y de {fou_coh_vacios["extendida 1981–2022"][0]:.2f} a {fou_coh_vacios["extendida 1981–2022"][1]:.2f} en la extendida: el
  relleno juega en contra de encontrar coherencia, no a favor.</p>
  </div>

  <div{_cambio('Nuevo · el pico de 2.2 meses')}>
  <p><b>¿Y el pico corto de la lluvia?</b> {fou_pico_corto_txt}</p>
  </div>
  <p class="nota"><b>Lo que el espectro no dice.</b> El espectro de potencia descarta la fase, así que no da el desfase entre la lluvia
  y el caudal: eso se mide con los armónicos (ver «Desfase estacional» en «El ciclo anual») y, en la escala interanual, con el
  espectro cruzado (ver «¿Cuadra con el ENSO?»). La FFT con Hann se calcula en el tramo
  continuo más largo de cada serie ({fou[(_fc, "Q", "original")]["n_fft"]} meses para Q). Análisis de angomezma-cyber, integrado a los scripts del proyecto.</p>

  <div{_cambio('Nuevo · conclusión')}>
  <h3>Conclusión</h3>
  <p>La variabilidad de la cuenca se concentra en dos escalas: <b>la semianual, que domina, y la interanual, que es débil pero
  real</b>.</p>
  <p><b>El pico de 6 meses es la señal más fuerte, y viene del clima regional.</b> Tiene el {fou_fuentes["PL"]["semianual"]:.1f} % de
  la varianza de PL, el {fou_fuentes["PI"]["semianual"]:.1f} % de la de PI y el {fou[(_fc, "Q", "original")]["bandas"]["semianual"]:.1f} % de la
  del caudal: es el doble paso de la ZCIT, que da dos temporadas de lluvias al año
  ({CITA_MESA}; {CITA_POVEDA}). Es un período bien determinado: cabe {fou[(_fc, "PL", "original")]["ciclos"]:.0f} veces en el registro
  y no se mueve con la ventana, con los vacíos de Q ni con el largo del registro. La temperatura es distinta: su ciclo anual
  pesa poco ({fou[(_fc, "T", "original")]["bandas"]["anual"]:.0f} %), y la mayor parte de su variación es de un año a otro
  ({fou[(_fc, "T", "original")]["bandas"]["interanual"]:.0f} %).</p>
  <p><b>La cuenca funciona como un filtro: atenúa lo rápido y conserva lo lento.</b> En las anomalías, la alta frecuencia es el
  {fou_alta_lluvia:.0f} % de la varianza de la lluvia y solo el {fou_alta_q:.0f} % de la del caudal; la autocorrelación de un mes es
  {fou_phi["Q"]:.2f} en Q contra {min(fou_phi["PL"], fou_phi["PI"]):.2f}–{max(fou_phi["PL"], fou_phi["PI"]):.2f} en la lluvia, y en la
  escala interanual el río va entre {fou_coh_q_rezago[0]:.1f} y {fou_coh_q_rezago[1]:.1f} meses detrás de la lluvia. Es el
  almacenamiento en el suelo y el acuífero que ya mostraban el desfase estacional y la correlación cruzada.</p>
  <p><b>La variabilidad interanual sigue al ENSO, pero no tiene un período fijo.</b> {_fou_ruido_rojo_txt}
  {fou_conclusion_enso_txt} Es una banda amplia, de {FOU_INTERANUAL[0] / 12:.0f} a {FOU_INTERANUAL[1] / 12:.0f} años, no una
  periodicidad.</p>
  <p><b>La conclusión depende poco de la fuente de lluvia, salvo en el ciclo anual.</b> PI y PL coinciden en la escala semianual
  y en las anomalías; difieren en la banda de 12 meses ({fou_fuentes["PI"]["anual"]:.1f} % contra {fou_fuentes["PL"]["anual"]:.1f} %),
  que el satélite ve y los pluviómetros no. Con los datos no se puede arbitrar cuál tiene la razón.</p>
  </div>
</section>

<section>
  <h2>¿Sirve la lluvia para estimar el caudal?</h2>
  <p>Dos pruebas, de menos a más exigente: reconstruir con la lluvia el ciclo del año típico, y estimar el caudal
  mes a mes en años que el ajuste no vio.</p>
  <h3>Primero, en el año típico</h3>
  <p>PL tiene sus picos en <b>{pico_pl[0]} y {pico_pl[1]}</b>, y Q en <b>{pico_q[0]} y {pico_q[1]}</b>. Para
  medirlo, el ciclo de Q se reconstruye con la lluvia del mismo mes, y luego con la del mes y la del anterior.</p>

  <div id="g-ciclo-rezago" class="grafico" style="min-height:0; height:420px"></div>
  <div{revision("nota ajustada a los colores unificados")}>
  <p class="nota">Barras: PL media de cada mes. Línea verde continua: Q observado. Líneas discontinuas (gris
  punteada, con la lluvia del mes; verde a trazos, con la del mes y la del anterior): Q
  <b>predicho a partir de PL</b>, no medido (ajuste lineal sobre las 12 medias mensuales, así que es una descripción de la forma
  del ciclo, no una prueba estadística fuerte).</p>
  </div>

  <p><b>Con la lluvia del mes sola, el ciclo de Q sale adelantado</b> y se explica el
  {ajuste_lq.loc[('PL', 'mes'), 'r2'] * 100:.0f} % de su forma; <b>sumando la del mes anterior, el
  {ajuste_lq.loc[('PL', 'mes_y_anterior'), 'r2'] * 100:.0f} %</b>, con cerca del {peso_mes_pl * 100:.0f} % de la señal
  del mes y el {(1 - peso_mes_pl) * 100:.0f} % del anterior: <b>el ciclo de PL condiciona el de Q, con un mes de
  arrastre</b>. Con PI el ajuste es más pobre ({ajuste_lq.loc[('PI', 'mes'), 'r2'] * 100:.0f} % →
  {ajuste_lq.loc[('PI', 'mes_y_anterior'), 'r2'] * 100:.0f} %).</p>

  <h3>Después, en años que el ajuste no vio</h3>
  <p>La prueba más exigente de la relación lluvia–caudal es usarla para <b>estimar el caudal en años que el ajuste
  no vio</b>: una recta ajustada con {EV_AJUSTE[0][:4]}–{EV_AJUSTE[1][:4]} se evalúa con
  {EV_VALIDACION[0][:4]}–{EV_VALIDACION[1][:4]}, en bloques continuos para que meses vecinos no queden uno en cada lado.
  La referencia es la <b>climatología</b> (el caudal medio de cada mes en el ajuste): superarla quiere decir que la
  lluvia dice algo que el calendario solo no dice.</p>
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
  <p><b>La mejor estimación sale de {ev_mejor}</b>: RMSE de {ev_tabla[ev_mejor]["validacion"]["rmse"]:.1f} m³/s en la
  evaluación, contra {ev_rmse_clima:.1f} de la climatología y {ev_tabla["PI del mismo mes"]["validacion"]["rmse"]:.1f}
  con PI. Con la lluvia del mes anterior sola el error crece ({ev_tabla["PL del mes anterior"]["validacion"]["rmse"]:.1f}
  con PL): el río responde sobre todo dentro del mismo mes. Ninguna estimación da caudales negativos.</p>
  <p><b>¿Y corregir PI con una recta contra PL?</b> Ajustada con los mismos años, la corrección deja un error de
  {ev_correccion["ols"]["rmse"]:.1f} mm/mes en la evaluación, contra {ev_correccion["sin"]["rmse"]:.1f} de PI sin
  corregir: casi no gana nada. Es otro argumento para no corregir PI y llevar las dos fuentes en paralelo.</p>
  <p class="nota">Una recta mensual simplifica mucho: no representa el agua guardada en el suelo, la humedad
  que trae la cuenca ni el tránsito por el cauce, y superar la climatología no prueba causalidad. Además,
  IMERG incorpora datos de pluviómetros, así que PI y PL no son del todo independientes.</p>
</section>


<section>
  <h2>Campos climáticos globales</h2>
  <div class="revision" data-etiqueta="Revisión · campos climáticos">
  <p>Para buscar qué patrones del océano y de la atmósfera acompañan a la lluvia y al caudal de la cuenca se usan tres
  <b>campos mensuales globales</b>, no índices: un índice como el ONI resume una región en un número, y un campo deja
  ver dónde está la señal. <b>La temperatura superficial del mar (SST)</b> es la fuente de la variabilidad de gran
  escala del ENSO. <b>El viento a 850 hPa</b> y
  <b>la humedad específica a 850 hPa</b> dicen por dónde viaja el vapor de agua en los niveles bajos, que es el que
  llega a la cuenca como lluvia; su producto, <b>q·V</b>, es el transporte de humedad. No se usan la presión al nivel
  del mar ni la altura geopotencial a 500 hPa.</p>

  <div class="tabla-caja"><table>
    <thead><tr><th>Campo</th><th>Fuente y versión</th><th>Variable y nivel</th><th>Unidades</th><th>Malla</th>
    <th>Máscara</th></tr></thead>
    <tbody>
      <tr><td>SST</td><td>ERSST v5, NOAA (<a href="#ref-huang2017">Huang et al., 2017</a>)</td><td>temperatura del agua en
      superficie</td><td>°C</td><td>2° (la nativa)</td><td>tierra vacía</td></tr>
      <tr><td>Viento</td><td rowspan="2">ERA5 medias mensuales, ECMWF (<a href="#ref-hersbach2020">Hersbach et al.,
      2020</a>), copia de NCAR GDEX (<a href="#ref-ecmwf2017">ECMWF, 2017</a>)</td><td>componente zonal u (+ hacia el
      este) y meridional v (+ hacia el norte), 850 hPa</td><td>m/s</td><td rowspan="2">0.25° → 2°</td>
      <td rowspan="2">850 hPa bajo el terreno</td></tr>
      <tr><td>Humedad</td><td>humedad específica q, 850 hPa</td><td>g/kg</td></tr>
      <tr><td>Transporte</td><td>calculado</td><td>q·u y q·v con las medias mensuales</td><td>(g/kg)·(m/s)</td>
      <td>2°</td><td>la de u, v y q</td></tr>
    </tbody>
  </table></div>
  <p class="nota">Período {cam_anios[0]}–{cam_anios[1]} ({cam_n_meses} meses), malla común de {cam_malla[0]} × {cam_malla[1]}
  cajas de 2° (la de ERSST). ERA5 se baja a 0.25° y se lleva a 2° con un <b>promedio por bloques ponderado por el área</b>
  de cada celda, que conserva la media en lugar de tomar muestras como una interpolación. La humedad viene en kg/kg y
  se pasa a g/kg. El transporte con medias mensuales pierde el que hacen los eventos de días dentro del mes (la media
  de q·u no es la media de q por la de u); a escala mensual y de gran escala es una aproximación usual. ERA5 se tomó
  de la copia del NCAR porque la cola del servicio de Copernicus tenía los pedidos detenidos; es el mismo producto.</p>

  <h3>850 hPa queda bajo los Andes</h3>
  <p>Un nivel de presión no es una altura fija: donde el terreno es alto, la presión en la superficie es menor que
  850 hPa y ese nivel queda <b>bajo tierra</b>, con valores que el modelo extrapola. Una caja de 2° queda vacía en un
  mes si <b>cualquiera</b> de sus celdas de 0.25° tiene ese mes una presión superficial menor que 850 hPa. Con esa regla
  estricta, el {cam_850_completas_pct:.0f} % del área del planeta tiene los {cam_n_meses} meses,
  el {cam_850_nunca_pct:.0f} % no tiene ninguno y {cam_850_parcial} cajas pierden algunos meses. <b>La caja de la cuenca
  ({cam_caja_cuenca["lat"]:.0f}° N, {360 - cam_caja_cuenca["lon"]:.0f}° O) no tiene ningún mes a 850 hPa</b>, y
  tampoco {cam_caja_cuenca["vecinas_sin_850"]} de sus 8 vecinas: en promedio el {cam_caja_cuenca["bajo_tierra"] * 100:.0f} % de su área
  está bajo ese nivel. En la misma latitud, las cajas más cercanas con los {cam_n_meses} meses están en
  {360 - cam_caja_cuenca["lon_este"]:.0f}° O, al oriente, y en {360 - cam_caja_cuenca["lon_oeste"]:.0f}° O, al occidente: el viento
  y la humedad que llegan a la cuenca en niveles bajos se leen a los lados de la cordillera.</p>
  <div class="placa"><img src="{img('campos_meses_validos_850.png')}" alt="Mapa del mundo con el número de meses válidos a 850 hPa en cada caja de 2°; los Andes, el Tíbet, la Antártida y otras zonas altas quedan en gris"></div>

  <h3>Los campos</h3>
  <p>La SST media va de {cam_rango["sst"][0]:.1f} a {cam_rango["sst"][1]:.1f} °C y la humedad específica media a
  850 hPa, de {cam_rango["q850"][0]:.1f} a {cam_rango["q850"][1]:.1f} g/kg. La cuenca va marcada en fucsia.</p>
  <div class="placa"><img src="{img('campos_sst_media.png')}" alt="Mapa del mundo con la temperatura superficial del mar media de 1998 a 2022"></div>
  <div class="placa"><img src="{img('campos_humedad_transporte.png')}" alt="Mapa del mundo con la humedad específica media a 850 hPa en colores y flechas del transporte medio de humedad"></div>
  <p class="nota"><b>Control de ERSST:</b> la temperatura media de la región Niño 3.4 calculada con este archivo sigue a la
  que publica la NOAA para el ONI en {cam_oni["n"]} trimestres (correlación {cam_oni["r"]:.3f}; diferencia media
  {cam_oni["dif_media"]:+.2f} °C y máxima {cam_oni["dif_max"]:.2f} °C), así que el producto se bajó y se leyó bien.</p>
  </div>
</section>

<section>
  <h2>Explicaciones físicas</h2>
  <p>Las secciones anteriores describen lo que muestran los datos. Esta reúne los mecanismos de la atmósfera que la
  literatura propone para explicarlo. Son marco conceptual, no resultados del proyecto: cada uno se contrasta con las
  cifras de la cuenca, pero ninguna de esas cifras prueba el mecanismo.</p>
  <p{revision("lo que agrega la sección")}>Después de los mecanismos, la sección resume cómo la cuenca transforma la
  lluvia que recibe, clasifica los meses del año y propone una hipótesis para contrastar con las relaciones entre variables
  y con las tendencias.</p>

  <div{revision("la ZCIT según Poveda (2004)")}>
  <h3>La migración de la ZCIT: por qué hay dos temporadas de lluvia</h3>
  <p>La lluvia y el caudal de la cuenca tienen dos picos al año (ver «El régimen» en «El ciclo anual» y el pico de 6 meses
  en «Frecuencias: análisis de Fourier»). La explicación está en la <b>Zona de Convergencia Intertropical (ZCIT)</b>, la
  franja de lluvias que migra de norte a sur a lo largo del año. Según {CITA_POVEDA}, esa oscilación «constituye el
  mecanismo físico de mayor importancia para explicar el ciclo anual (o semi-anual) de la hidro-climatología de Colombia»:
  sobre el centro del país «se presentan dos temporadas lluviosas (abril-mayo y octubre-noviembre), y dos temporadas secas
  (diciembre-febrero y junio-agosto), como resultado del doble paso de la ZCIT sobre el territorio». En las estaciones de
  los Andes tropicales el ciclo es bimodal, «con valores máximos en los períodos abril-mayo y octubre-noviembre». Según
  {CITA_MESA}, el paso de la segunda mitad del año ocurre en <b>septiembre, octubre y noviembre</b>.</p>
  <p>La cuenca lo reproduce. El primer pico cae en {pico_pl[0]} (PL), {pico_pi[0]} (PI) y {pico_q[0]} (Q), y el segundo en
  {pico_pl[1]}, {pico_pi[1]} y {pico_q[1]}: dentro de las dos temporadas lluviosas que da Poveda. El régimen es
  {" y ".join(reg_clases)} en las tres series (Kruskal-Wallis: <i>p</i> ≤ {reg_kw_max:.0e}; A₂/A₁ = {regimen["PL"]["a2a1"]:.2f}
  con PL), y los dos picos aparecen en {est_anual["PL"]["los_dos"]} de {est_anual["PL"]["anios"]} años con PL
  ({est_anual["PL"]["simple"]} con el método simple de «¿Se repite cada año? ¿Es estable?»).</p>
  </div>

  <h3>El óptimo pluviográfico: por qué llueve menos arriba</h3>
  <p>La lluvia no crece indefinidamente con la altura. Aumenta hasta una franja en la que es máxima, el
  <b>óptimo pluviográfico</b>, que normalmente no pasa de {n(ALTURA_OPTIMO_M)} m, y por encima <b>disminuye</b>
  ({CITA_MESA_P90}): las lluvias tropicales son sobre todo convectivas, y al subir y enfriarse el aire se le agota el
  vapor que condensar.</p>
  <p>El Fonce va de {n(elev_min)} a {n(elev_max)} m, y el <b>{frac_sobre_optimo * 100:.0f} % de su área</b> está por
  encima de {n(ALTURA_OPTIMO_M)} m (curva hipsométrica del proyecto). Salvo la parte más baja, cerca de San Gil, la
  cuenca queda en la rama descendente: por eso llueve menos arriba, como se ve en «En esta cuenca llueve menos arriba»,
  donde IMERG pierde unos {n(grad_caida)} mm/año de sus celdas más bajas a las más altas.</p>

  <h3>Un episodio aparte: los frentes fríos de enero y febrero de 2005</h3>
  <p>En el primer bimestre de 2005, la Defensoría del Pueblo documentó una emergencia invernal en Santander, Norte de
  Santander, Tolima y Huila: inundaciones, la avalancha del río de Oro y calamidad pública en Bucaramanga y Girón. Según
  el IDEAM, citado en el documento, las lluvias eran atípicas para la época y se debían a <b>cuatro frentes fríos del
  hemisferio norte</b>, cuando entre enero y febrero lo normal son uno o dos ({CITA_DEFENSORIA}).</p>
  <p><b>Qué es un frente frío.</b> El mismo documento lo explica (nota 2): las masas de aire casi no se mezclan, y el
  frente es la línea en que la superficie que separa dos de ellas toca el suelo. En un frente frío, el aire frío avanza
  sobre el cálido. Como es más denso, entra por debajo como una cuña, lo levanta y lo obliga a subir por la superficie
  frontal; en ese ascenso se forman «abundantes nubes de desarrollo vertical», que son las que dan los aguaceros. La
  Defensoría toma esa definición de una página web de divulgación, no de una publicación técnica.</p>
  <p><b>Qué se vio en la cuenca.</b> Enero de 2005 estuvo {ene05["z_pl"]:+.1f} rangos intercuartiles sobre lo normal en
  PL, {ene05["z_pi"]:+.1f} en PI y {ene05["z_q"]:+.1f} en Q; febrero, {ene05["z_pl_feb"]:+.1f}, {ene05["z_pi_feb"]:+.1f}
  y {ene05["z_q_feb"]:+.1f} (ver «Revisión de outliers»). El documento no nombra la cuenca del Fonce, así que no se
  puede confirmar que sean las mismas lluvias. Es un episodio de un bimestre, no un rasgo del clima de la cuenca.</p>

  <div{revision("subsección nueva: cómo la cuenca transforma la lluvia")}>
  <h3>Cómo la cuenca transforma la lluvia</h3>
  <p><b>Las dos temporadas secas no son iguales.</b> La de {clas_fila["seco"]["nombre"]} es la más profunda: con PL,
  {regimen["PL"]["min"]} tiene una mediana de {n(regimen["PL"]["medianas"][_mes_minimo_pl - 1])} mm, contra
  {n(_sr["mediana_pl"][0])} mm en {fis_sr_mes_min}, y es el mes de menor P/ETP: {pe_mes.loc[1, "pl"]:.2f} con PL y
  {pe_mes.loc[1, "pi"]:.2f} con PI (ver «¿Húmeda o árida? La lluvia contra la ETP»). La de {_sr["nombre"]} es un descenso
  entre los dos picos, con excedente todos los meses (P/ETP {_rango_txt(*_sr["pe"]["pl"])} con PL y
  {_rango_txt(*_sr["pe"]["pi"])} con PI).</p>
  <p><b>La humedad de la Amazonía.</b> Según {CITA_POVEDA}, «los vientos alisios del sureste transportan gran cantidad de
  humedad hacia los Andes» desde la cuenca Amazónica. Con los datos del proyecto no se puede contrastar a escala de la
  cuenca: la humedad y el viento a 850 hPa quedan bajo tierra en la caja de la cuenca (ver «850 hPa queda bajo los Andes»
  en «Campos climáticos globales»). Queda como contexto, no como resultado.</p>
  <p><b>Convección y relieve.</b> Según {CITA_POVEDA}, en la región Andina «el valle del Río Magdalena y el Norte de
  Antioquia presentan la mayor cantidad» de sistemas convectivos de mesoescala, y la cuenca está en el flanco de la
  cordillera que mira a ese valle (ver «Contexto geográfico»). Dos rasgos de los datos son coherentes con una lluvia de
  origen convectivo:</p>
  <ul>
    <li>un mes más lluvioso de lo normal es más fresco de día: en los {len(t_max_baja)} meses con T máx atípicamente baja,
    PL estuvo en promedio {fis_pl_tmax["baja"]:+.1f} rangos intercuartiles sobre lo normal, y en los {len(t_max_alta)} con
    T máx atípicamente alta, {fis_pl_tmax["alta"]:+.1f} (ver «Revisión de outliers»);</li>
    <li>la lluvia disminuye con la altura ({aj_imerg["por_1000m"]:+.0f} mm/año por cada 1 000 m con IMERG), la rama alta del
    óptimo pluviográfico de arriba.</li>
  </ul>
  <p><b>Lo que no se usa.</b> Los monzones no entran en la explicación: el ciclo se entiende con la ZCIT. Los frentes fríos
  no controlan el ciclo; aparecen como episodios aislados, como el de 2005. La nieve y los glaciares no aparecen en ningún
  dato del proyecto.</p>
  <p><b>La energía casi no cambia en el año.</b> La temperatura media de la cuenca varía {mapa_t_amplitud_anual:.1f} °C
  entre el mes más cálido y el más frío, y {t_max_mitad - t_min_mitad:.1f} °C de un extremo al otro de la cuenca (ver
  «Mapas de la cuenca»): la manda la altura, no el calendario. La ETP de Hargreaves va de
  {n(fis_ciclo_rango["etp"]["min"])} a {n(fis_ciclo_rango["etp"]["max"])} mm/mes según el mes, un
  {fis_ciclo_rango["etp"]["pct"]:.0f} % de su media; la lluvia, con la misma medida, un {fis_ciclo_rango["pl"]["pct"]:.0f} %
  con PL y un {fis_ciclo_rango["pi"]["pct"]:.0f} % con PI. Por eso el ciclo de P/ETP, y con él el del caudal, lo pone la
  lluvia y no la demanda de evaporación.</p>
  <p><b>Hay agua de sobra la mayor parte del año.</b> P/ETP anual es {pe_indice["pl"]["ie"]:.2f} con PL y
  {pe_indice["pi"]["ie"]:.2f} con PI: la cuenca es húmeda con las dos fuentes (UNEP, desde {UNEP_HUMEDO:.2f}) y en los
  {pe_n_anios} años. Con PL ningún mes tiene déficit en promedio (enero queda en {pe_mes.loc[1, "pl"]:.2f}); con PI, enero
  baja a {pe_mes.loc[1, "pi"]:.2f}. Sale por el río {fis_coef_txt} de la lluvia.</p>
  <p><b>El almacenamiento atrasa y suaviza al río.</b> El caudal llega unos {desfase["Q_PL"]:.0f} días después que la lluvia
  con PL (IC 95 %: {desfase_ic["Q_PL"][0]:.0f} a {desfase_ic["Q_PL"][1]:.0f}) y unos {desfase["Q_PI"]:.0f} con PI (ver
  «Desfase estacional»). Es mucho más que el tiempo de concentración ({desfase_tc[0]:.0f} a {desfase_tc[1]:.0f} horas): no es
  el viaje del agua por el cauce, sino agua que entra al suelo y al acuífero y sale después. Lo apoyan otras tres señales:</p>
  <ul>
    <li>los picos de Q caen en {" y ".join(regimen["Q"]["picos"])}, un mes después de los de PL ({" y ".join(regimen["PL"]["picos"])});</li>
    <li>sin el ciclo anual, la lluvia del mes anterior sigue explicando Q (correlación parcial de
    {memoria.loc["PL", "parcial_mes_anterior"]:.2f} con PL y {memoria.loc["PI", "parcial_mes_anterior"]:.2f} con PI; ver
    «Mes a mes: correlación cruzada entre la lluvia y el caudal»);</li>
    <li>con PL, en {fis_meses_guarda} P − Q supera a la ETP (la cuenca guarda agua), y {fis_sobre1_txt} (ver «Lo que le cae a
    la cuenca y lo que sale por el río»).</li>
  </ul>
  <p><b>Lo que no se sabe.</b> No hay datos de humedad del suelo, del acuífero, de captaciones de agua ni de la operación
  de obras hidráulicas en la cuenca. El almacenamiento se infiere del desfase; no se mide.</p>
  <p><b>Qué controla el ciclo y qué cambia de un año a otro.</b> El ciclo estacional lo controlan la ZCIT (cuándo llueve)
  y el almacenamiento (cuándo responde el río). Las diferencias entre años las modula el ENSO: según {CITA_POVEDA},
  «durante El Niño se presenta una disminución en la precipitación y en los caudales medios mensuales de los ríos de
  Colombia», y «durante La Niña ocurren anomalías contrarias». Los datos lo apoyan sin probarlo:</p>
  <ul>
    <li>en la banda de 3 a 7 años, la lluvia y el caudal varían en oposición al ONI; la coherencia es significativa con PI
    en 1998–2022 ({fis_coh_oni[("común 1998–2022", "PI")]["coh"]:.2f}), y con PL y Q solo en el registro largo (PL*
    {fis_coh_oni[("extendida 1981–2022", "PL*")]["coh"]:.2f} y Q {fis_coh_oni[("extendida 1981–2022", "Q")]["coh"]:.2f}; ver
    «¿Cuadra con el ENSO? Coherencia y fase con el ONI»);</li>
    <li>Q va unos {fis_q_rezago_oni} meses detrás del ONI (el rezago en que su correlación es más negativa);</li>
    <li>el año más seco con las dos fuentes es {fis_anio_seco} ({anom_anios[fis_anio_seco]["nino"]} meses de El Niño), y el
    más húmedo con las dos juntas, {fis_anio_humedo} ({anom_anios[fis_anio_humedo]["nina"]} meses de La Niña; ver «Los años
    contrastantes»).</li>
  </ul>
  <p>Con {pe_n_anios} años no se puede atribuir la variabilidad entre años solo al ENSO.</p>
  </div>

  <div{revision("subsección nueva: clasificación hidroclimática mensual")}>
  <h3>Síntesis: clasificación hidroclimática mensual</h3>
  <p>Los meses se clasifican con tres criterios, calculados con las series del proyecto en
  {PERIODOS[0].year}–{PERIODOS[-1].year}, con PL, que manda, y con PI en paralelo:</p>
  <ul>
    <li>si la mediana de la lluvia del mes supera al mes típico (las temporadas de «El régimen»);</li>
    <li>P/ETP del mes y en cuántos años hubo déficit, P &lt; ETP (de «¿Húmeda o árida? La lluvia contra la ETP»);</li>
    <li>cómo responde el caudal, con su atraso.</li>
  </ul>
  <p><b>Húmedo</b>: mes de temporada húmeda con P/ETP ≥ {CLAS_PE_HUMEDO:.1f} y
  {"sin déficit en ningún año" if CLAS_MAX_ANIOS_DEFICIT == 0 else f"con déficit en no más de {CLAS_MAX_ANIOS_DEFICIT} años"}. <b>Seco</b>: la temporada seca que contiene el mes de menos lluvia. <b>Seco relativo</b>:
  la otra temporada seca.</p>
  <div class="tabla-caja">
  <table class="sin-destacar">
    <thead><tr><th>Clase</th><th>Meses (PL)</th><th>Lluvia (mediana de PL, mm/mes)</th><th class="num">P/ETP (PL / PI)</th>
    <th class="num">Años con P &lt; ETP en el peor mes (PL / PI)</th><th>Caudal (régimen de Q)</th></tr></thead>
    <tbody>
{clas_filas}
    </tbody>
  </table>
  </div>
  <p class="nota">P/ETP: el rango de los meses de la clase. Años con déficit: el mayor número de años con P &lt; ETP entre los
  meses de la clase, de {pe_n_anios}; en enero son {pe_mes_deficit_anios.loc[1, "pl"]} con PL y
  {pe_mes_deficit_anios.loc[1, "pi"]} con PI. Caudal: las temporadas de Q que se cruzan con los meses de la clase. Con 1 año
  de déficit admitido en vez de {CLAS_MAX_ANIOS_DEFICIT}, la clasificación con PL es la misma.</p>
  <p><b>En una frase:</b> clima húmedo (P/ETP de {pe_indice["pl"]["ie"]:.2f} con PL y {pe_indice["pi"]["ie"]:.2f} con PI),
  con régimen bimodal por el doble paso de la ZCIT, sin estación con déficit de agua sostenido salvo
  {_y_lista([MESES_LARGOS_ES[m - 1] for m in clas_deficit_frecuente["pl"]])}, y un río que responde con
  {min(desfase["Q_PL"], desfase["Q_PI"]):.0f} a {max(desfase["Q_PL"], desfase["Q_PI"]):.0f} días de atraso por el
  almacenamiento.</p>
  <p><b>Alternativas e incertidumbres.</b></p>
  <ul>
    <li><i>La fuente cambia los bordes.</i> Con PI, {_y_lista([MESES_LARGOS_ES[m - 1] for m in clas_solo_pi_humedas])} caen
    en temporada húmeda (con PI, las temporadas húmedas son {nombre_meses(clas_pi_humedas)}), y enero tiene déficit, que con PL no tiene.
    {clas_pi_sin_clase_txt} La clase de esos meses depende de la fuente.</li>
    <li><i>Ningún pluviómetro mide por encima de {n(mapa_plu_alta.altitud)} m</i>, donde está el
    {mapa_pct_sin_pluvio:.0f} % de la cuenca. Si arriba llueve menos, PL podría sobrestimar la lluvia de la cuenca.</li>
    <li><i>La ETP es potencial y de Hargreaves.</i> UNEP definió las clases con Thornthwaite, así que el umbral es
    aproximado. Pero el año más seco queda en {fis_anio_mas_seco["min"]:.2f} ({fis_anio_mas_seco["anio_min"]}), más del doble
    del umbral de {UNEP_HUMEDO:.2f}: la clase «húmedo» no cambiaría.</li>
    <li><i>Los límites son convenciones.</i> El mes típico es el promedio de las medianas, y P/ETP ≥ {CLAS_PE_HUMEDO:.1f} es una
    elección; con otros umbrales, junio o septiembre podrían cambiar de clase.</li>
    <li><i>No es el atributo de CAMELS-COL:</i> la clasificación sale de estas series y de este período.</li>
  </ul>
  </div>

  <div{revision("subsección nueva: la hipótesis")}>
  <h3>Una hipótesis para las relaciones y las tendencias</h3>
  <p><b>H:</b> el caudal de San Gil lo controla la lluvia sobre la cuenca, amortiguada por un almacenamiento del orden de
  un mes. La evapotranspiración, casi constante en el año, no explica ni su ciclo ni sus diferencias entre años.</p>
  <p>Si H es cierta, debería cumplirse:</p>
  <ol>
    <li><b>En las relaciones entre variables</b>, la lluvia sigue explicando el caudal sin el ciclo anual, y la del mes
    anterior agrega información. Hoy: ρ(PL, Q) en anomalías = {rho("PL", "Q", anomalias=True):.2f}
    ({rho("PI", "Q", anomalias=True):.2f} con PI), y la correlación parcial de la lluvia del mes anterior es
    {memoria.loc["PL", "parcial_mes_anterior"]:.2f} ({memoria.loc["PI", "parcial_mes_anterior"]:.2f}). En años que el ajuste
    no vio, la lluvia del mismo mes ya supera a la climatología (RMSE de {_ev_pl:.1f} m³/s con PL y {_ev_pi:.1f} con PI,
    contra {ev_rmse_clima:.1f}; ver «¿Sirve la lluvia para estimar el caudal?»). Falta probar ahí un modelo con la lluvia del
    mes y la del anterior, que debería mejorar, más con PL que con PI.</li>
    <li><b>En las tendencias</b>, un cambio de la lluvia debería verse en el caudal de ese mes o del siguiente. Hoy: la
    lluvia de marzo sube ({fis_marzo["pend"]:+.0f} mm/mes por década con PL*, la única subserie de la lluvia que resiste la
    corrección FDR), pero el caudal de marzo no muestra tendencia significativa ({fis_marzo["q_mes"]["ols"]:+.1f} m³/s por
    década, p = {_p_txt(fis_marzo["q_mes"]["p"])}; ver «Mes a mes: las doce subseries»). {fis_q_abril_txt} O la señal es
    pequeña frente a la variabilidad del caudal, o el almacenamiento y el resto del año la diluyen.</li>
    <li><b>En las tendencias</b>, el calentamiento ({fis_t_decada:+.2f} °C por década) no debería mover el caudal, porque
    sube la ETP solo un {inc_etp["rel_pct"]:.2f} % por década (ver «Significativo no es lo mismo que importante»). Hoy, Q no
    tiene tendencia, lo que es coherente con H, pero no la prueba.</li>
  </ol>
  <p><b>Qué refutaría H:</b> que el caudal tuviera tendencias o diferencias entre años sin un cambio de lluvia que las
  acompañe (por ejemplo, por captaciones de agua o cambios de cobertura), o que los residuos de las estimaciones de Q con
  la lluvia conservaran estacionalidad.</p>
  </div>
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
    <li id="ref-benjamini1995">Benjamini, Y., y Hochberg, Y. (1995). Controlling the false discovery rate: a practical and
    powerful approach to multiple testing. <i>Journal of the Royal Statistical Society Series B</i>, 57(1), 289–300.
    <a href="https://doi.org/10.1111/j.2517-6161.1995.tb02031.x">https://doi.org/10.1111/j.2517-6161.1995.tb02031.x</a></li>
    <li id="ref-cleveland1979">Cleveland, W. S. (1979). Robust locally weighted regression and smoothing scatterplots.
    <i>Journal of the American Statistical Association</i>, 74(368), 829–836.
    <a href="https://doi.org/10.1080/01621459.1979.10481038">https://doi.org/10.1080/01621459.1979.10481038</a></li>
    <li id="ref-defensoria2005">Defensoría del Pueblo. (2005, 16 de marzo). <i>Resolución Defensorial No. 34:
    Emergencia invernal durante el primer bimestre de 2005</i>.
    <a href="https://www.defensoria.gov.co/documents/20123/1311006/defensorial34.pdf/d9d42d31-7913-c461-c3f5-fae0651d358c?t=1648529830362&amp;download=true">defensoria.gov.co</a></li>
    <li id="ref-ecmwf2017">European Centre for Medium-Range Weather Forecasts. (2017). <i>ERA5 Reanalysis Monthly
    Means</i> [conjunto de datos]. NSF National Center for Atmospheric Research, Geoscience Data Exchange.
    <a href="https://doi.org/10.5065/D63B5XW1">https://doi.org/10.5065/D63B5XW1</a></li>
    <li id="ref-hamed1998">Hamed, K. H., y Ramachandra Rao, A. (1998). A modified Mann-Kendall trend test for
    autocorrelated data. <i>Journal of Hydrology</i>, 204(1–4), 182–196.
    <a href="https://doi.org/10.1016/S0022-1694(97)00125-X">https://doi.org/10.1016/S0022-1694(97)00125-X</a></li>
    <li id="ref-hargreaves1985">Hargreaves, G. H., y Samani, Z. A. (1985). Reference crop evapotranspiration from
    temperature. <i>Applied Engineering in Agriculture</i>, 1(2), 96–99.
    <a href="https://doi.org/10.13031/2013.26773">https://doi.org/10.13031/2013.26773</a></li>
    <li id="ref-hersbach2020">Hersbach, H., Bell, B., Berrisford, P., et al. (2020). The ERA5 global reanalysis.
    <i>Quarterly Journal of the Royal Meteorological Society</i>, 146(730), 1999–2049.
    <a href="https://doi.org/10.1002/qj.3803">https://doi.org/10.1002/qj.3803</a></li>
    <li id="ref-hirsch1982">Hirsch, R. M., Slack, J. R., y Smith, R. A. (1982). Techniques of trend analysis for monthly
    water quality data. <i>Water Resources Research</i>, 18(1), 107–121.
    <a href="https://doi.org/10.1029/WR018i001p00107">https://doi.org/10.1029/WR018i001p00107</a></li>
    <li id="ref-horn1960">Horn, L. H., y Bryson, R. A. (1960). Harmonic analysis of the annual march of
    precipitation over the United States. <i>Annals of the Association of American Geographers</i>, 50, 157–171.
    <a href="https://doi.org/10.1111/j.1467-8306.1960.tb00342.x">https://doi.org/10.1111/j.1467-8306.1960.tb00342.x</a></li>
    <li id="ref-huang2017">Huang, B., Thorne, P. W., Banzon, V. F., et al. (2017). Extended Reconstructed Sea Surface
    Temperature, Version 5 (ERSSTv5): Upgrades, Validations, and Intercomparisons. <i>Journal of Climate</i>, 30(20),
    8179–8205. <a href="https://doi.org/10.1175/JCLI-D-16-0836.1">https://doi.org/10.1175/JCLI-D-16-0836.1</a></li>
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
    <li id="ref-lomb1976">Lomb, N. R. (1976). Least-squares frequency analysis of unequally spaced data. <i>Astrophysics and
    Space Science</i>, 39(2), 447–462. <a href="https://doi.org/10.1007/BF00648343">https://doi.org/10.1007/BF00648343</a></li>
    <li id="ref-mann1945">Mann, H. B. (1945). Nonparametric tests against trend. <i>Econometrica</i>, 13(3), 245 y siguientes.
    <a href="https://doi.org/10.2307/1907187">https://doi.org/10.2307/1907187</a></li>
    <li id="ref-mesa1997"{_cambio('Nuevo')}>Mesa, O. J., Poveda, G., y Carvajal, L. F. (1997). <i>Introducción al clima de Colombia</i>.
    Universidad Nacional de Colombia, Medellín.</li>
    <li id="ref-middleton1997"{revision("nuevo")}>Middleton, N., y Thomas, D. (eds.) (1997). <i>World Atlas of
    Desertification</i> (2.ª ed.). UNEP / Arnold, Londres.</li>
    <li id="ref-newey1987">Newey, W. K., y West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and
    autocorrelation consistent covariance matrix. <i>Econometrica</i>, 55(3), 703 y siguientes.
    <a href="https://doi.org/10.2307/1913610">https://doi.org/10.2307/1913610</a></li>
    <li id="ref-noaa-oni">NOAA Climate Prediction Center. <i>Oceanic Niño Index (ONI)</i>. Descargado el
    2026-09-28. <a href="https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt">https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt</a></li>
    <li id="ref-pettitt1979">Pettitt, A. N. (1979). A non-parametric approach to the change-point problem.
    <i>Journal of the Royal Statistical Society, Series C (Applied Statistics)</i>, 28(2), 126–135.
    <a href="https://doi.org/10.2307/2346729">https://doi.org/10.2307/2346729</a></li>
    <li id="ref-poveda2004">Poveda, G. (2004). La hidroclimatología de Colombia: una síntesis desde la escala
    inter-decadal hasta la escala diurna. <i>Revista de la Academia Colombiana de Ciencias Exactas, Físicas y
    Naturales</i>, 28(107), 201–221.
    <a href="https://doi.org/10.18257/raccefyn.28(107).2004.1991">https://doi.org/10.18257/raccefyn.28(107).2004.1991</a></li>
    <li id="ref-scargle1982">Scargle, J. D. (1982). Studies in astronomical time series analysis. II. Statistical aspects of
    spectral analysis of unevenly spaced data. <i>The Astrophysical Journal</i>, 263, 835 y siguientes.
    <a href="https://doi.org/10.1086/160554">https://doi.org/10.1086/160554</a></li>
    <li id="ref-sen1968">Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau.
    <i>Journal of the American Statistical Association</i>, 63(324), 1379–1389.
    <a href="https://doi.org/10.1080/01621459.1968.10480934">https://doi.org/10.1080/01621459.1968.10480934</a></li>
    <li id="ref-shapiro1965">Shapiro, S. S., y Wilk, M. B. (1965). An analysis of variance test for normality (complete
    samples). <i>Biometrika</i>, 52(3–4), 591–611.
    <a href="https://doi.org/10.1093/biomet/52.3-4.591">https://doi.org/10.1093/biomet/52.3-4.591</a></li>
    <li id="ref-welch1967">Welch, P. (1967). The use of fast Fourier transform for the estimation of power spectra: a method
    based on time averaging over short, modified periodograms. <i>IEEE Transactions on Audio and Electroacoustics</i>, 15(2),
    70–73. <a href="https://doi.org/10.1109/TAU.1967.1161901">https://doi.org/10.1109/TAU.1967.1161901</a></li>
  </ol>
  <p class="nota">Las fuentes de datos (CAMELS-COL, IMERG, ERA5-Land, IDEAM, DEM) están al pie de la página.</p>
</section>

<section>
  <div{revision("uso de IA")}>
  <h2>Uso de inteligencia artificial</h2>
  <p>Este informe se hizo con ayuda de herramientas de inteligencia artificial (IA) de Anthropic. Casi todo el código
  del repositorio se escribió con esa ayuda. Las decisiones de método las tomó el equipo: la IA presentó las opciones
  con su evidencia y una recomendación. Esta sección sigue la declaración que pide la política del curso; el anexo, al
  final, reúne las propuestas de la IA que el equipo rechazó o corrigió.</p>

  <h3>Herramientas y versión</h3>
  <div class="tabla-caja"><table>
    <thead><tr><th>Herramienta</th><th>Versión</th><th>Para qué</th></tr></thead>
    <tbody>
{ia_filas_herramientas}
    </tbody>
  </table></div>
  <p class="nota">En el repositorio no queda registro de otras herramientas de IA. Los modelos se identifican por su nombre y su
  identificador, que es la versión que informa la propia herramienta.</p>

  <h3>En qué tareas intervino</h3>
  <ul>
    <li><b>Código:</b> los scripts de <code>scripts/</code>, de la descarga de los datos (IMERG, ERA5-Land, los
    pluviómetros del IDEAM, ERSST y los campos de ERA5) a su procesamiento, el control de calidad, las pruebas de
    saltos, la climatología, las anomalías, las tendencias, el análisis de Fourier, los modelos lluvia–caudal, el índice
    P/ETP, las figuras y el script que genera esta página. El análisis de Fourier lo empezó angomezma-cyber en su rama y la IA lo
    integró a los scripts del proyecto.</li>
    <li><b>Textos:</b> borradores de las secciones del informe, que el equipo revisó, corrigió o descartó; en
    particular, la explicación física y la síntesis del ciclo anual se escribieron primero como borrador aparte para que
    el equipo los leyera antes de entrar al informe.</li>
    <li><b>Bibliografía:</b> búsqueda de fuentes y lectura de las disponibles para comprobar que digan lo que el informe
    les atribuye.</li>
    <li><b>Verificación:</b> correr el análisis de principio a fin y revisar la página después de cada cambio.</li>
  </ul>

  <h3>Qué se verificó y cómo</h3>
  <ul>
    <li><b>Cifras:</b> ninguna se escribe a mano. Todas se calculan en <code>scripts/18_calculos_informe.py</code> a
    partir de los datos descargados (procedencia y SHA-256 en <code>DATOS_FUENTES.md</code>), y las afirmaciones sobre
    los datos están protegidas por {ia_n_assert} comprobaciones automáticas (<code>assert</code>) en los dos scripts del
    informe: si los datos dejan de sostener una frase, el script se detiene.</li>
    <li><b>Datos:</b> los controles de «Control de calidad básico» (fechas, unidades, rangos físicos, códigos de
    faltante), las pruebas de «Anomalías en las series» y el «Registro de anomalías», que deja constancia de lo
    comprobado, lo decidido y su efecto.</li>
    <li><b>Cálculos contra referencias externas:</b> la radiación de la ETP contra el ejemplo de FAO-56 («La
    evapotranspiración potencial»), IMERG contra su archivo empaquetado, la temperatura de ERSST contra el ONI de la
    NOAA («Campos climáticos globales») y el área de la cuenca contra la publicada por CAMELS-COL.</li>
    <li><b>Recálculos independientes:</b> algunas cifras se recalcularon fuera del script, directamente desde los CSV de
    <code>out/</code>, antes de aceptarlas; por ejemplo, el índice P/ETP anual, sus años extremos y los valores de
    enero.</li>
    <li><b>Citas:</b> las frases entre comillas atribuidas a una fuente se copiaron del texto de esa fuente. Una fuente
    propuesta se descartó al leerla: el rango de altura de máxima lluvia que citaba se refería a la vertiente amazónica
    de los Andes, no a los valles interandinos.</li>
    <li><b>Cada cambio:</b> antes de entrar a la rama principal, el análisis corre sin errores desde la raíz, el
    JavaScript de la página pasa <code>node --check</code>, la página abre en un navegador sin errores de consola en los
    temas claro y oscuro, y el notebook congelado no cambia. Esa verificación queda escrita en cada commit y en la
    descripción de cada pull request.</li>
  </ul>

  <h3>Propuestas rechazadas o corregidas</h3>
  <p>El registro <code>DECISIONES.md</code> anota cada decisión del equipo junto con lo que recomendó la IA. En
  {len(ia_rechazos)} el equipo decidió distinto; están en el anexo. Además, la IA corrigió propuestas suyas al
  verificarlas: un umbral escogido a mano para describir un P/ETP «prácticamente en el límite» se quitó a pedido del
  equipo, y una fuente se descartó al leerla (ver «Citas», arriba).</p>
  <p>Un modelo de lenguaje puede equivocarse. La responsabilidad del contenido es de los autores, que deben poder
  explicar cada figura, rastrear cada resultado hasta los datos y el código, y justificar cada decisión.</p>

  <h3>Anexo: decisiones en que el equipo contradijo a la IA</h3>
  <div class="tabla-caja"><table>
    <thead><tr><th>Fecha</th><th>Tema</th><th>Decisión del equipo</th><th>Recomendación de la IA</th><th>¿Coinciden?</th></tr></thead>
    <tbody>
{ia_filas_rechazos}
    </tbody>
  </table></div>
  <p class="nota">Tomado de <code>DECISIONES.md</code> al generar la página: las filas marcadas «Contradice al
  agente».</p>
  </div>
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
  // Un color por variable, el mismo en todas las figuras (COLOR_VAR del script de Python). Ninguna figura
  // escribe el color de una variable a mano: lo toma de aquí.
  const COLOR_VAR = {color_var_json};
  // el color de una variable con transparencia, para bandas y rellenos
  const translucido = (hex, a) => "rgba(" + [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(",") + "," + a + ")";
  // mezcla un color con blanco (t > 0) o con negro (t < 0): para las escalas secuenciales de una variable
  const mezclar = (hex, t) => "rgb(" + [1, 3, 5].map(i => {{
    const c = parseInt(hex.slice(i, i + 2), 16);
    return Math.round(t >= 0 ? c + (255 - c) * t : c * (1 + t));
  }}).join(",") + ")";
  // escala secuencial de una variable: de un tono muy claro a su color y a uno oscuro del mismo matiz
  const escalaVar = v => [[0, mezclar(COLOR_VAR[v], 0.88)], [0.5, COLOR_VAR[v]], [1, mezclar(COLOR_VAR[v], -0.55)]];

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
    // la misma variable (T media) con dos fuentes: el mismo color, distinto trazo. ERA5-Land, línea continua y
    // banda rellena; MSWX, línea a trazos con rombos y su banda marcada solo por los bordes, punteados
    const color = COLOR_VAR["T media"];
    const FUENTES = [
      {{ clave: "mswx", nombre: "MSWX", guion: "dash", simbolo: "diamond", relleno: false }},
      {{ clave: "era", nombre: "ERA5-Land", guion: "solid", simbolo: "circle", relleno: true }}
    ];

    // --- ciclo anual: banda p10-p90 y mediana encima
    const trazas = [];
    FUENTES.forEach(f => {{
      const borde = f.relleno ? {{ width: 0 }} : {{ color: color, width: 1, dash: "dot" }};
      trazas.push({{
        type: "scatter", mode: "lines", x: TEMP.meses, y: TEMP.ciclo[f.clave + "_p90"],
        line: borde, showlegend: false, hoverinfo: "skip", legendgroup: f.clave
      }});
      trazas.push({{
        type: "scatter", mode: "lines", x: TEMP.meses, y: TEMP.ciclo[f.clave + "_p10"],
        line: borde, fill: f.relleno ? "tonexty" : "none", fillcolor: translucido(color, 0.2),
        name: f.nombre + " · p10–p90", legendgroup: f.clave,
        hovertemplate: "%{{y:.1f}} °C<extra>" + f.nombre + " · p10</extra>"
      }});
      trazas.push({{
        type: "scatter", mode: "lines+markers", x: TEMP.meses, y: TEMP.ciclo[f.clave + "_p50"],
        line: {{ color: color, width: 2.8, dash: f.guion }}, marker: {{ size: 7, symbol: f.simbolo }},
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
            marker: {{ color: COLOR_VAR[V[j]], opacity: 0.6, line: {{ color: "rgba(0,0,0,0)", width: 0 }} }},
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
    const v = CAJAS.variables[cajaActiva], color = COLOR_VAR[v];
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
    const trazas = [
      {{ type: "bar", name: "PL (lluvia)", x: CLQ.meses, y: CLQ.PL,
         marker: {{ color: COLOR_VAR.PL, opacity: 0.22 }}, hovertemplate: "PL %{{y:.0f}} mm/mes<extra></extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "Q observado", x: CLQ.meses, y: CLQ.Q,
         line: {{ color: COLOR_VAR.Q, width: 2.6 }}, marker: {{ size: 6, color: COLOR_VAR.Q }},
         hovertemplate: "Q %{{y:.0f}} mm/mes<extra></extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q predicho con PL del mes", x: CLQ.meses, y: CLQ.ajusteMes,
         line: {{ color: tenue, width: 1.8, dash: "dot" }},
         hovertemplate: "Q predicho con PL del mes: %{{y:.0f}}<extra></extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q predicho con PL del mes y del anterior", x: CLQ.meses,
         y: CLQ.ajusteMesAnterior, line: {{ color: COLOR_VAR.Q, width: 2.2, dash: "dash" }},
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
    // las tres son la misma variable (ETP): el mismo color, distinguidas por el trazo y el marcador
    const SERIES = [
      {{ clave: "camels", nombre: "CAMELS-COL, publicada", guion: "dot", simbolo: "circle" }},
      {{ clave: "mswx", nombre: "Hargreaves con MSWX", guion: "dash", simbolo: "square" }},
      {{ clave: "era", nombre: "Hargreaves con ERA5-Land", guion: "solid", simbolo: "diamond" }}
    ];
    const trazas = SERIES.map(s => ({{
      type: "scatter", mode: "lines+markers", name: s.nombre, x: ETP.meses, y: ETP[s.clave],
      line: {{ color: COLOR_VAR.ETP, width: 2, dash: s.guion }}, marker: {{ symbol: s.simbolo, size: 7 }},
      hovertemplate: "%{{y:.0f}} mm<extra>" + s.nombre + "</extra>" }}));
    trazas.push({{ type: "scatter", mode: "lines", name: "PL − Q", x: ETP.meses, y: ETP.pl_q,
      line: {{ color: css("--tenue"), width: 1.4, dash: "dot" }},
      hovertemplate: "%{{y:.0f}} mm<extra>PL − Q</extra>" }});
    Plotly.react("g-etp", trazas, base(), CONF);
  }}

  const DM = {an_dm_json};

  function dibujarDobleMasa() {{
    if (!window.Plotly) return;
    const series = Object.keys(DM), GRIS = css("--tenue");
    const trazas = [], botones = [];
    series.forEach((s, i) => {{
      // la línea lleva el color de su variable (PL, PI o Q); el salto lo marca el rombo
      const d = DM[s], color = COLOR_VAR[d.variable], n = d.x.length;
      trazas.push({{ type: "scatter", mode: "lines", name: s, x: d.x, y: d.y, customdata: d.meses, visible: i === 0,
        line: {{ color: color, width: 2 }}, hovertemplate: "%{{customdata}}<br>serie %{{y:,.0f}} mm<br>referencia %{{x:,.0f}} mm<extra></extra>" }});
      trazas.push({{ type: "scatter", mode: "lines", name: "proporción constante", x: [0, d.x[n - 1]], y: [0, d.y[n - 1]],
        visible: i === 0, line: {{ color: GRIS, width: 1, dash: "dot" }}, hoverinfo: "skip" }});
      const k = d.corte ? d.meses.indexOf(d.corte) : -1;
      trazas.push({{ type: "scatter", mode: "markers", name: "comienzo del 2.º tramo", visible: i === 0,
        x: k >= 0 ? [d.x[k]] : [], y: k >= 0 ? [d.y[k]] : [], marker: {{ symbol: "diamond", size: 12, color: css("--tinta") }},
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
    const GRIS = css("--tenue");
    const mensual = base();
    mensual.margin = {{ t: 46, r: 10, b: 30, l: 54 }};
    mensual.yaxis.rangemode = "normal";
    mensual.shapes = [{{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: {{ color: GRIS, width: 1 }} }}];
    Plotly.react("g-pq-mensual", [
      {{ type: "scatter", mode: "lines", name: "PL − Q", x: PQ.meses, y: PQ.pl_q, connectgaps: false,
         line: {{ color: COLOR_VAR.PL, width: 1.6 }}, hovertemplate: "%{{y:.0f}} mm<extra>PL − Q</extra>" }},
      {{ type: "scatter", mode: "lines", name: "PI − Q", x: PQ.meses, y: PQ.pi_q, connectgaps: false,
         line: {{ color: COLOR_VAR.PI, width: 1.2, dash: "dash" }}, hovertemplate: "%{{y:.0f}} mm<extra>PI − Q</extra>" }},
      {{ type: "scatter", mode: "lines", name: "ETP (Hargreaves, ERA5-Land)", x: PQ.meses, y: PQ.etp,
         line: {{ color: COLOR_VAR.ETP, width: 2.4 }}, hovertemplate: "%{{y:.0f}} mm<extra>ETP</extra>" }}
    ], mensual, CONF);
    const anual = base();
    anual.margin = {{ t: 46, r: 10, b: 40, l: 54 }};
    anual.yaxis.title.text = "mm/año";
    anual.xaxis.type = "category";
    anual.barmode = "group";
    Plotly.react("g-pq-anual", [
      {{ type: "bar", name: "PL − Q", x: PQ.anios, y: PQ.pl_q_anual, marker: {{ color: COLOR_VAR.PL }},
         hovertemplate: "%{{y:.0f}} mm<extra>PL − Q</extra>" }},
      {{ type: "bar", name: "PI − Q", x: PQ.anios, y: PQ.pi_q_anual, marker: {{ color: COLOR_VAR.PI, opacity: 0.75 }},
         hovertemplate: "%{{y:.0f}} mm<extra>PI − Q</extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "ETP", x: PQ.anios, y: PQ.etp_anual,
         line: {{ color: COLOR_VAR.ETP, width: 2.4 }}, hovertemplate: "%{{y:.0f}} mm<extra>ETP</extra>" }}
    ], anual, CONF);
  }}

  // P/ETP por mes del calendario, con PL y con PI lado a lado; la línea en 1 separa el déficit del excedente
  const PE = {pe_json};

  function dibujarPEMes() {{
    if (!window.Plotly) return;
    const d = base();
    d.margin = {{ t: 46, r: 10, b: 30, l: 54 }};
    d.barmode = "group";
    d.hovermode = "x unified";
    d.yaxis.title.text = "P/ETP";
    d.shapes = [{{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 1, y1: 1, line: {{ color: css("--tinta"), width: 1.2, dash: "dash" }} }}];
    d.annotations = [{{ xref: "paper", x: 1, xanchor: "right", y: 1, yanchor: "bottom", showarrow: false,
      text: "P = ETP", font: {{ size: 10, color: css("--tinta") }}, bgcolor: css("--fondo") }}];
    Plotly.react("g-pe-mes", [
      {{ type: "bar", name: "P/ETP con PL", x: PE.meses, y: PE.pl, marker: {{ color: COLOR_VAR.PL }},
         hovertemplate: "%{{y:.2f}}<extra>PL</extra>" }},
      {{ type: "bar", name: "P/ETP con PI", x: PE.meses, y: PE.pi, marker: {{ color: COLOR_VAR.PI }},
         hovertemplate: "%{{y:.2f}}<extra>PI</extra>" }}
    ], d, CONF);
  }}


  const ANOM = {anom_json};

  let anomModo = 0;
  (function () {{
    const botones = [0, 1].map(i => document.getElementById("pestana-anomc-" + i));
    if (botones.some(b => !b)) return;
    botones.forEach((boton, i) => boton.addEventListener("click", () => {{
      anomModo = i;
      botones.forEach((otro, j) => {{ otro.setAttribute("aria-selected", String(i === j)); otro.tabIndex = i === j ? 0 : -1; }});
      dibujarAnomalias();
    }}));
  }})();

  function dibujarAnomalias() {{
    if (!window.Plotly) return;
    const GRIS = css("--tenue");
    const COLOR = {{ "húmedo": ["#0072B2", "#56B4E9"], "seco": ["#D55E00", "#E69F00"] }};
    const anios = Object.keys(ANOM.anios);
    const usados = {{ "húmedo": 0, "seco": 0 }};
    const color = {{}};
    anios.forEach(a => {{ const t = ANOM.anios[a].tipo; color[a] = COLOR[t][usados[t]++]; }});
    const resto = ANOM.nube.anio.map(a => !(String(a) in ANOM.anios));
    const trazas = [{{
      type: "scatter", mode: "markers", name: "los demás meses",
      x: ANOM.nube.pl.filter((_, i) => resto[i]), y: ANOM.nube.q.filter((_, i) => resto[i]),
      text: ANOM.nube.mes.filter((_, i) => resto[i]),
      marker: {{ size: 6, color: GRIS, opacity: 0.45 }}, hovertemplate: "%{{text}}<extra></extra>"
    }}];
    anios.forEach(a => {{
      const idx = ANOM.nube.anio.map((x, i) => String(x) === a ? i : -1).filter(i => i >= 0);
      trazas.push({{ type: "scatter", mode: "markers", name: a + " (" + ANOM.anios[a].tipo + ")",
        x: idx.map(i => ANOM.nube.pl[i]), y: idx.map(i => ANOM.nube.q[i]), text: idx.map(i => ANOM.nube.mes[i]),
        marker: {{ size: 9, color: color[a] }}, hovertemplate: "%{{text}}<extra></extra>" }});
    }});
    const d1 = base();
    d1.hovermode = "closest";
    d1.margin = {{ t: 64, r: 10, b: 48, l: 58 }};
    d1.xaxis.title = {{ text: "anomalía de PL (rangos intercuartiles)", font: {{ size: 11, color: GRIS }} }};
    d1.yaxis.title.text = "anomalía de Q (rangos intercuartiles)";
    d1.yaxis.rangemode = "normal";
    d1.xaxis.zeroline = true; d1.yaxis.zeroline = true;
    d1.xaxis.zerolinecolor = GRIS; d1.yaxis.zerolinecolor = GRIS;
    Plotly.react("g-anom-dispersion", trazas, d1, CONF);

    const ciclo = [{{ type: "scatter", mode: "lines", name: "año típico (mediana)", x: ANOM.meses, y: ANOM.mediana,
      line: {{ color: css("--tinta"), width: 3, dash: "dash" }}, hovertemplate: "%{{y:.0f}} mm<extra>típico</extra>" }}];
    anios.forEach(a => ciclo.push({{ type: "scatter", mode: "lines+markers", name: a, x: ANOM.meses, y: ANOM.anios[a].serie,
      line: {{ color: color[a], width: 2 }}, marker: {{ size: 5 }}, hovertemplate: "%{{y:.0f}} mm<extra>" + a + "</extra>" }}));
    if (anomModo === 0) {{
      const d2 = base();
      d2.margin.t = 46;
      d2.yaxis.title.text = "PL (mm/mes)";
      Plotly.react("g-anom-ciclo", ciclo, d2, CONF);
      return;
    }}
    // PL contra PI, un panel por año (2 × 2)
    const pares = [], d3 = base();
    d3.margin = {{ t: 40, r: 10, b: 30, l: 54 }};
    d3.hovermode = "x";
    d3.annotations = [];
    const dominiosX = [[0, 0.47], [0.53, 1]], dominiosY = [[0.56, 0.92], [0, 0.36]];
    // el mismo eje y en los cuatro paneles, para poder comparar los años entre sí
    const ymax = 1.05 * Math.max(...anios.flatMap(a => ANOM.anios[a].serie.concat(ANOM.anios[a].pi)));
    anios.forEach((a, i) => {{
      const sx = i === 0 ? "" : String(i + 1);
      const fila = Math.floor(i / 2), col = i % 2;
      d3["xaxis" + sx] = {{ domain: dominiosX[col], anchor: "y" + sx, gridcolor: css("--linea"), tickfont: {{ color: GRIS }} }};
      d3["yaxis" + sx] = {{ domain: dominiosY[fila], anchor: "x" + sx, gridcolor: css("--linea"), tickfont: {{ color: GRIS }},
        range: [0, ymax], title: {{ text: col === 0 ? "mm/mes" : "", font: {{ size: 11, color: GRIS }} }} }};
      d3.annotations.push({{ xref: "x" + sx + " domain", yref: "y" + sx + " domain", x: 0, y: 1.02, xanchor: "left",
        yanchor: "bottom", showarrow: false, text: "<b>" + a + "</b> (" + ANOM.anios[a].tipo + ")",
        font: {{ size: 11, color: color[a] }} }});
      pares.push({{ type: "scatter", mode: "lines+markers", name: "PL", legendgroup: "PL", showlegend: i === 0,
        x: ANOM.meses, y: ANOM.anios[a].serie, xaxis: "x" + sx, yaxis: "y" + sx,
        // en este panel las líneas son variables (PL y PI) y llevan su color; el año lo dice el título del panel
        line: {{ color: COLOR_VAR.PL, width: 2.2 }}, marker: {{ size: 4 }}, hovertemplate: "%{{y:.0f}} mm<extra>PL " + a + "</extra>" }});
      pares.push({{ type: "scatter", mode: "lines+markers", name: "PI", legendgroup: "PI", showlegend: i === 0,
        x: ANOM.meses, y: ANOM.anios[a].pi, xaxis: "x" + sx, yaxis: "y" + sx,
        line: {{ color: COLOR_VAR.PI, width: 1.6, dash: "dash" }}, marker: {{ size: 4, symbol: "diamond" }},
        hovertemplate: "%{{y:.0f}} mm<extra>PI " + a + "</extra>" }});
    }});
    d3.legend.y = 1.0;
    Plotly.react("g-anom-ciclo", pares, d3, CONF);
  }}

  const ANZ = {anz_json};
  const TEND = {tend_json};
  let anzGrupo = 0, tendPeriodo = 0;

  // fondo según la fase del ENSO (ONI de la NOAA, scripts/17): rojo El Niño, azul La Niña, sin color neutro
  const ENSO_COLOR = {{ "El Niño": "rgba(213,94,0,0.13)", "La Niña": "rgba(0,114,178,0.13)" }};
  function fondoEnso(yref) {{
    return ANZ.enso.map(([x0, x1, f]) => ({{ type: "rect", xref: "x", yref: yref, x0: x0, x1: x1, y0: 0, y1: 1,
      fillcolor: ENSO_COLOR[f], line: {{ width: 0 }}, layer: "below" }}));
  }}
  function leyendaEnso() {{
    return Object.entries(ENSO_COLOR).map(([f, c]) => ({{ type: "scatter", mode: "markers", x: [null], y: [null], name: f,
      marker: {{ symbol: "square", size: 12, color: c.replace("0.13", "0.45") }}, hoverinfo: "skip" }}));
  }}

  function dibujarAnz() {{
    if (!window.Plotly) return;
    const GRIS = css("--tenue");
    const grupo = Object.keys(ANZ.grupos)[anzGrupo];
    const vars = ANZ.grupos[grupo];
    const unidad = ANZ.unidades[vars[0]];
    const trazas = [];
    const ejes = [["X", "y", unidad], ["a", "y2", unidad], ["z", "y3", "z"]];
    ejes.forEach(([rep, eje], k) => {{
      vars.forEach(v => {{
        trazas.push({{ type: "scatter", mode: "lines", name: v, legendgroup: v, showlegend: k === 0,
          x: ANZ.fechas, y: ANZ.series[v][rep], yaxis: eje, connectgaps: false,
          line: {{ color: COLOR_VAR[v], width: 1.2 }},
          hovertemplate: "%{{y}}<extra>" + v + " · " + rep + "</extra>" }});
        if (rep !== "X") {{
          const r = ANZ.series[v].recta[rep];
          trazas.push({{ type: "scatter", mode: "lines", x: r.x, y: r.y, yaxis: eje, showlegend: false,
            legendgroup: v, hoverinfo: "skip", line: {{ color: COLOR_VAR[v], width: 2.2, dash: "dash" }} }});
        }}
      }});
    }});
    const d = base();
    d.hovermode = "x";
    d.margin = {{ t: 46, r: 10, b: 36, l: 62 }};
    d.xaxis.type = "date";
    d.xaxis.anchor = "y3";
    // el eje arranca donde empieza el registro más largo del grupo (PL y PI desde 1998; Q y T desde 1981)
    const primero = Math.min(...vars.map(v => ANZ.series[v].X.findIndex(x => x !== null)));
    d.xaxis.range = [ANZ.fechas[primero], ANZ.fechas[ANZ.fechas.length - 1]];
    const ejeY = (titulo, dominio) => ({{ gridcolor: css("--linea"), zeroline: true, zerolinecolor: GRIS,
      linecolor: css("--linea"), tickfont: {{ color: GRIS }}, domain: dominio,
      title: {{ text: titulo, font: {{ size: 11, color: GRIS }} }} }});
    d.yaxis = ejeY("X (" + unidad + ")", [0.70, 1]);
    d.yaxis.zeroline = false;
    d.yaxis2 = ejeY("a (" + unidad + ")", [0.36, 0.64]);
    d.yaxis3 = ejeY("z", [0, 0.30]);
    d.shapes = ["y", "y2", "y3"].flatMap(e => fondoEnso(e + " domain"));
    // el período de referencia, con dos líneas verticales (el fondo lo ocupa el ENSO)
    ANZ.ref.forEach(x => d.shapes.push({{ type: "line", xref: "x", yref: "paper", x0: x, x1: x, y0: 0, y1: 1,
      line: {{ color: css("--tinta"), width: 1, dash: "dot" }} }}));
    d.annotations = [{{ xref: "x", yref: "paper", x: ANZ.ref[0], y: 1, xanchor: "left", yanchor: "bottom", showarrow: false,
      text: "período de referencia →", font: {{ size: 10, color: GRIS }} }}];
    trazas.push(...leyendaEnso());
    Plotly.react("g-anz", trazas, d, CONF);
  }}

  function dibujarTendMes() {{
    if (!window.Plotly) return;
    const per = Object.keys(TEND)[tendPeriodo];
    const T = TEND[per];
    const texto = T.p.map(fila => fila.map(p => p < {TEND_ALFA} ? "*" : ""));
    const info = T.x.map((fila, i) => fila.map((x, j) =>
      T.vars[i] + " · " + MES[j] + "<br>" + (x > 0 ? "+" : "") + x + " " + T.unidades[i] + " por década" +
      "<br>z: " + (T.z[i][j] > 0 ? "+" : "") + T.z[i][j] + " s por década<br>p = " + T.p[i][j] + " · " + T.n[i][j] + " años"));
    const lim = Math.max(...T.z.flat().map(Math.abs));
    const traza = {{ type: "heatmap", x: MES, y: T.vars, z: T.z, text: texto, texttemplate: "%{{text}}",
      textfont: {{ size: 16, color: css("--tinta") }}, customdata: info, hovertemplate: "%{{customdata}}<extra></extra>",
      zmin: -lim, zmax: lim, colorscale: "RdBu", reversescale: false, xgap: 2, ygap: 2,   // en plotly.js RdBu va de azul (negativo) a rojo (positivo)
      colorbar: {{ title: {{ text: "z / década", side: "right" }}, thickness: 12, tickfont: {{ color: css("--tenue") }} }} }};
    const d = base();
    d.hovermode = "closest";
    d.margin = {{ t: 16, r: 10, b: 36, l: 70 }};
    d.yaxis.rangemode = "normal";
    d.yaxis.autorange = "reversed";
    d.yaxis.title.text = "";
    d.xaxis.gridcolor = "rgba(0,0,0,0)";
    d.yaxis.gridcolor = "rgba(0,0,0,0)";
    Plotly.react("g-tend-mes", [traza], d, CONF);
  }}

  // mapa año–mes: una matriz por variable (años × meses); los meses sin dato van en una segunda capa, gris
  const MAPA = {mapa_am_json};
  let mapaVar = 0;

  function dibujarMapaAnioMes() {{
    if (!window.Plotly) return;
    const V = MAPA.variables[mapaVar];
    const info = V.z.map((fila, i) => fila.map((x, j) =>
      "<b>" + MES[j] + " " + MAPA.anios[i] + "</b><br>" + V.nombre + ": " +
      (x === null ? "sin dato" : x.toFixed(V.dec) + " " + V.unidad)));
    const vacios = V.z.map(fila => fila.map(x => x === null ? 1 : null));
    const tenue = css("--tenue");
    const trazas = [{{
      type: "heatmap", x: MES, y: MAPA.anios, z: V.z, customdata: info, hoverongaps: false,
      hovertemplate: "%{{customdata}}<extra></extra>", zmin: V.rango[0], zmax: V.rango[1],
      colorscale: escalaVar(V.nombre), xgap: 1, ygap: 1,      // escala secuencial del color de la variable
      colorbar: {{ title: {{ text: V.unidad, side: "right", font: {{ size: 10, color: tenue }} }},
                  thickness: 12, outlinewidth: 0, tickfont: {{ size: 9, color: tenue }} }}
    }}];
    if (vacios.flat().some(x => x !== null)) trazas.push({{
      type: "heatmap", x: MES, y: MAPA.anios, z: vacios, customdata: info, hoverongaps: false,
      hovertemplate: "%{{customdata}}<extra></extra>", zmin: 0, zmax: 1,
      // gris del tema a media opacidad: se distingue del tono más claro de las escalas en los dos temas
      colorscale: [[0, tenue], [1, tenue]], opacity: 0.45, showscale: false, xgap: 1, ygap: 1
    }});
    const d = base();
    d.hovermode = "closest";
    d.margin = {{ t: 10, r: 10, b: 36, l: 48 }};
    d.yaxis.type = "category";
    d.yaxis.rangemode = "normal";
    d.yaxis.autorange = "reversed";          // el primer año arriba
    d.yaxis.title.text = "";
    d.xaxis.gridcolor = "rgba(0,0,0,0)";
    d.yaxis.gridcolor = "rgba(0,0,0,0)";
    Plotly.react("g-mapa-am", trazas, d, CONF);
  }}

  // pestañas: cambian lo que se dibuja, no el panel que se muestra
  [["pestana-anz-", Object.keys(ANZ.grupos).length, i => {{ anzGrupo = i; dibujarAnz(); }}],
   ["pestana-tend-", Object.keys(TEND).length, i => {{ tendPeriodo = i; dibujarTendMes(); }}],
   ["pestana-mapa-", MAPA.variables.length, i => {{ mapaVar = i; dibujarMapaAnioMes(); }}]].forEach(([prefijo, cuantos, accion]) => {{
    const botones = Array.from({{ length: cuantos }}, (_, i) => document.getElementById(prefijo + i));
    if (botones.some(b => !b)) return;
    botones.forEach((boton, i) => boton.addEventListener("click", () => {{
      botones.forEach((otro, j) => {{ otro.setAttribute("aria-selected", String(i === j)); otro.tabIndex = i === j ? 0 : -1; }});
      accion(i);
    }}));
  }});

  const MET = {met_json};
  let metVar = 0, metRep = 0;
  const MET_REPS = ["a", "X", "z"];

  function dibujarMetodos() {{
    if (!window.Plotly) return;
    const v = Object.keys(MET)[metVar], k = MET_REPS[metRep];
    const D = MET[v][k];
    const color = COLOR_VAR[v];
    const trazas = [
      {{ type: "scatter", mode: "lines", name: "meses", x: D.fechas, y: D.y, line: {{ color: css("--tenue"), width: 0.8 }},
         opacity: 0.6, hovertemplate: "%{{y}}<extra>" + v + " · " + k + "</extra>" }},
      {{ type: "scatter", mode: "lines", x: D.fechas, y: D.hi, line: {{ width: 0 }}, showlegend: false, hoverinfo: "skip" }},
      {{ type: "scatter", mode: "lines", name: "banda LOESS 95 %", x: D.fechas, y: D.lo, fill: "tonexty",
         fillcolor: color + "33", line: {{ width: 0 }}, hoverinfo: "skip" }},
      {{ type: "scatter", mode: "lines", name: "LOESS", x: D.fechas, y: D.curva, line: {{ color: color, width: 2.6 }},
         hovertemplate: "%{{y:.2f}}<extra>LOESS</extra>" }},
      {{ type: "scatter", mode: "lines", x: D.fechas, y: D.ols_hi, line: {{ width: 0 }}, showlegend: false, hoverinfo: "skip" }},
      {{ type: "scatter", mode: "lines", name: "banda OLS 95 %", x: D.fechas, y: D.ols_lo, fill: "tonexty",
         fillcolor: "rgba(120,120,120,0.22)", line: {{ width: 0 }}, hoverinfo: "skip" }},
      {{ type: "scatter", mode: "lines", name: "recta OLS", x: D.fechas, y: D.ols,
         line: {{ color: css("--tinta"), width: 1.6, dash: "dash" }}, hoverinfo: "skip" }}
    ];
    const d = base();
    d.hovermode = "x";
    d.margin = {{ t: 46, r: 10, b: 36, l: 62 }};
    d.xaxis.type = "date";
    d.yaxis.rangemode = "normal";
    d.yaxis.title.text = k === "z" ? "z" : k + " (" + ANZ.unidades[v] + ")";
    d.shapes = fondoEnso("paper");
    trazas.push(...leyendaEnso());
    Plotly.react("g-met", trazas, d, CONF);
  }}

  [["pestana-met-v", Object.keys(MET).length, i => {{ metVar = i; dibujarMetodos(); }}],
   ["pestana-met-r", 3, i => {{ metRep = i; dibujarMetodos(); }}]].forEach(([prefijo, cuantos, accion]) => {{
    const botones = Array.from({{ length: cuantos }}, (_, i) => document.getElementById(prefijo + i));
    if (botones.some(b => !b)) return;
    botones.forEach((boton, i) => boton.addEventListener("click", () => {{
      botones.forEach((otro, j) => {{ otro.setAttribute("aria-selected", String(i === j)); otro.tabIndex = i === j ? 0 : -1; }});
      accion(i);
    }}));
  }});

  const PEND = {pend_json};
  let pendVar = 0;

  function dibujarPendMes() {{
    if (!window.Plotly) return;
    const v = Object.keys(PEND)[pendVar], D = PEND[v];
    const color = COLOR_VAR[v];
    const xs = d => MES.map((_, i) => i + d);
    const trazas = [
      {{ type: "scatter", mode: "markers", name: "OLS ± IC 95 %", x: xs(-0.15), y: D.ols,
         error_y: {{ type: "data", array: D.ic, color: color, thickness: 1.4, width: 3 }},
         marker: {{ size: 9, symbol: D.q.map(q => q < {INC_Q_FDR} ? "circle" : "circle-open"), color: color,
                    line: {{ width: 2, color: color }} }},
         customdata: D.q, hovertemplate: "%{{y:+.2f}} " + D.unidad + "<br>q (FDR) = %{{customdata}}<extra>OLS</extra>" }},
      {{ type: "scatter", mode: "markers", name: "Sen [IC 95 %]", x: xs(0.15), y: D.sen,
         error_y: {{ type: "data", symmetric: false, array: D.sen_hi.map((h, i) => h - D.sen[i]),
                    arrayminus: D.sen.map((x, i) => x - D.sen_lo[i]), color: css("--tinta"), thickness: 1.2, width: 3 }},
         marker: {{ size: 8, symbol: D.q_mk.map(q => q < {INC_Q_FDR} ? "diamond" : "diamond-open"), color: css("--tinta"),
                    line: {{ width: 1.5, color: css("--tinta") }} }},
         customdata: D.q_mk, hovertemplate: "%{{y:+.2f}} " + D.unidad + "<br>q (FDR) = %{{customdata}}<extra>Sen</extra>" }}
    ];
    const d = base();
    d.hovermode = "closest";
    d.margin = {{ t: 46, r: 10, b: 36, l: 70 }};
    d.xaxis.tickvals = MES.map((_, i) => i);
    d.xaxis.ticktext = MES;
    d.yaxis.rangemode = "normal";
    d.yaxis.zeroline = true;
    d.yaxis.zerolinecolor = css("--tenue");
    d.yaxis.title.text = D.unidad;
    Plotly.react("g-pend-mes", trazas, d, CONF);
  }}

  (function () {{
    const botones = Object.keys(PEND).map((_, i) => document.getElementById("pestana-pend-v" + i));
    if (botones.some(b => !b)) return;
    botones.forEach((boton, i) => boton.addEventListener("click", () => {{
      pendVar = i;
      botones.forEach((otro, j) => {{ otro.setAttribute("aria-selected", String(i === j)); otro.tabIndex = i === j ? 0 : -1; }});
      dibujarPendMes();
    }}));
  }})();

  const FOU = {fou_json};
  let fouTipo = 0, fouVen = 0;
  const FOU_TIPOS = ["original", "anomalía", "anomalía sin tendencia"];
  // Fourier llama T a la T media; el ONI es una referencia, no una variable de la cuenca: gris y punteado
  const FOU_COLOR = {{ ...COLOR_VAR, "T": COLOR_VAR["T media"], "ONI": "#8A8A8A" }};

  function dibujarFourier() {{
    if (!window.Plotly) return;
    const ven = Object.keys(FOU)[fouVen], tipo = FOU_TIPOS[fouTipo];
    const trazas = Object.entries(FOU[ven]).map(([v, d]) => ({{
      type: "scatter", mode: "lines", name: v, x: d[tipo].f, y: d[tipo].p,
      line: {{ color: FOU_COLOR[v], width: 1.6, dash: v === "ONI" ? "dot" : "solid" }},
      hovertemplate: "f = %{{x:.4f}} ciclos/mes (T = %{{customdata:.1f}} meses)<br>%{{y:.2f}}<extra>" + v + "</extra>",
      customdata: d[tipo].f.map(f => 1 / f) }}));
    const d = base();
    d.hovermode = "closest";
    d.margin = {{ t: 64, r: 10, b: 44, l: 62 }};
    d.xaxis.title = {{ text: "frecuencia (ciclos/mes)", font: {{ size: 11, color: css("--tenue") }} }};
    d.xaxis.range = [0, 0.5];
    d.yaxis.title.text = "potencia normalizada";
    const T = [84, 36, 12, 6, 4, 3, 2];
    d.xaxis2 = {{ overlaying: "x", side: "top", range: [0, 0.5], tickvals: T.map(t => 1 / t), ticktext: T.map(t => t + " m"),
                  tickfont: {{ color: css("--tenue"), size: 10 }}, showgrid: false }};
    trazas.push({{ type: "scatter", x: [0.25], y: [0], xaxis: "x2", showlegend: false, hoverinfo: "skip", mode: "markers",
                   marker: {{ opacity: 0 }} }});
    // las franjas de 12 y 6 meses son las bandas que se miden: ±Δf, con Δf = 1/N (la primera frecuencia de la grilla)
    const df = Object.values(FOU[ven])[0][tipo].f[0];
    d.shapes = [[1 / 84, 1 / 36, "rgba(124,91,199,0.10)"], [1 / 12 - df, 1 / 12 + df, "rgba(120,120,120,0.18)"],
                [1 / 6 - df, 1 / 6 + df, "rgba(120,120,120,0.18)"]].map(([x0, x1, c]) => ({{
      type: "rect", xref: "x", yref: "paper", x0: x0, x1: x1, y0: 0, y1: 1, fillcolor: c, line: {{ width: 0 }}, layer: "below" }}));
    Plotly.react("g-fou", trazas, d, CONF);
  }}

  [["pestana-foutab-", 3, i => document.querySelectorAll(".fou-tabla").forEach(d => {{ d.hidden = d.dataset.tipo !== String(i); }})],
   ["pestana-fou-t", 3, i => {{ fouTipo = i; dibujarFourier(); }}],
   ["pestana-fou-v", Object.keys(FOU).length, i => {{ fouVen = i; dibujarFourier(); }}]].forEach(([prefijo, cuantos, accion]) => {{
    const botones = Array.from({{ length: cuantos }}, (_, i) => document.getElementById(prefijo + i));
    if (botones.some(b => !b)) return;
    botones.forEach((boton, i) => boton.addEventListener("click", () => {{
      botones.forEach((otro, j) => {{ otro.setAttribute("aria-selected", String(i === j)); otro.tabIndex = i === j ? 0 : -1; }});
      accion(i);
    }}));
  }});

  const P2 = {p2_pipl_json};
  const EV = {ev_json};

  function dibujarPuntoDos() {{
    if (!window.Plotly) return;
    const GRIS = css("--tenue");
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
         line: {{ color: COLOR_VAR.Q, width: 2 }}, connectgaps: false, hovertemplate: "%{{y:.0f}} m³/s<extra>Q observado</extra>" }},
      {{ type: "scatter", mode: "lines", name: "climatología", x: EV.meses, y: EV.clima,
         line: {{ color: GRIS, width: 1.4, dash: "dot" }}, hovertemplate: "%{{y:.0f}} m³/s<extra>climatología</extra>" }},
      {{ type: "scatter", mode: "lines", name: "estimado con PL", x: EV.meses, y: EV.pl,
         line: {{ color: COLOR_VAR.PL, width: 1.6 }}, connectgaps: false, hovertemplate: "%{{y:.0f}} m³/s<extra>con PL</extra>" }},
      {{ type: "scatter", mode: "lines", name: "estimado con PI", x: EV.meses, y: EV.pi,
         line: {{ color: COLOR_VAR.PI, width: 1.2, dash: "dash" }}, connectgaps: false, hovertemplate: "%{{y:.0f}} m³/s<extra>con PI</extra>" }}
    ], d2, CONF);
  }}
  const BAL = {bal_json};

  function dibujarBalance() {{
    if (!window.Plotly) return;
    const GRIS = css("--tenue");

    Plotly.react("g-balance", [
      {{ type: "scatter", mode: "lines", name: "PI · precipitación IMERG", x: BAL.meses, y: BAL.p,
         line: {{ color: COLOR_VAR.PI, width: 1.6 }}, fill: "tozeroy",
         fillcolor: translucido(COLOR_VAR.PI, 0.16),
         hovertemplate: "%{{y:.0f}} mm<extra>PI</extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q · caudal observado", x: BAL.meses, y: BAL.q,
         line: {{ color: COLOR_VAR.Q, width: 1.6 }}, connectgaps: false,
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
         line: {{ color: COLOR_VAR.PI, width: 1.2, dash: "dash" }} }}
    ];
    disp.annotations = [
      {{ xref: "paper", x: 0.004, xanchor: "left", y: 1, yanchor: "bottom",
         text: "caudal = lluvia del mes", showarrow: false, font: {{ size: 10, color: GRIS }} }},
      {{ xref: "paper", x: 0.004, xanchor: "left", y: BAL.coef_medio, yanchor: "bottom",
         text: "promedio de Q / PI: " + BAL.coef_medio.toFixed(2), showarrow: false,
         font: {{ size: 10, color: COLOR_VAR.PI }} }}
    ];
    Plotly.react("g-escorrentia", [
      {{ type: "scatter", mode: "lines", name: "Q / PL", x: BAL.meses, y: BAL.coef_pl,
         line: {{ color: COLOR_VAR.PL, width: 1.4 }}, connectgaps: false,
         hovertemplate: "%{{y:.2f}}<extra>Q / PL</extra>" }},
      {{ type: "scatter", mode: "lines", name: "Q / PI", x: BAL.meses, y: BAL.coef,
         line: {{ color: COLOR_VAR.PI, width: 1, dash: "dot" }}, connectgaps: false,
         hovertemplate: "%{{y:.2f}}<extra>Q / PI</extra>" }}
    ], disp, CONF);
  }}

  const CICLO = {ciclo_json};

  function dibujarCicloAnual() {{
    if (!window.Plotly) return;
    const GRIS = css("--tenue");

    Plotly.react("g-ciclo-anual", [
      {{ type: "scatter", mode: "lines+markers", name: "PI · lluvia IMERG",
         x: CICLO.meses, y: CICLO.imerg,
         line: {{ color: COLOR_VAR.PI, width: 2.2 }}, marker: {{ size: 7 }},
         hovertemplate: "%{{y:.0f}} mm<extra>PI</extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "PL · lluvia de la red",
         x: CICLO.meses, y: CICLO.red,
         line: {{ color: COLOR_VAR.PL, width: 2.2, dash: "dash" }}, marker: {{ size: 7 }},
         hovertemplate: "%{{y:.0f}} mm<extra>PL</extra>" }},
      {{ type: "scatter", mode: "lines+markers", name: "Q · caudal", x: CICLO.meses, y: CICLO.caudal,
         line: {{ color: COLOR_VAR.Q, width: 2.6 }}, marker: {{ size: 8 }}, fill: "tozeroy",
         fillcolor: translucido(COLOR_VAR.Q, 0.15),
         hovertemplate: "%{{y:.0f}} mm<extra>Q</extra>" }}
    ], Object.assign(base(), {{ margin: {{ t: 58, r: 12, b: 38, l: 56 }} }}), CONF);

  }}

  const GRAD = {grad_json};

  function dibujarGradiente() {{
    if (!window.Plotly) return;
    const GRIS = css("--tenue");

    const trazas = [
      // todas las celdas que tocan la cuenca; el tamaño dice cuánto pesan en el ajuste
      {{ type: "scatter", mode: "markers", name: "celdas de IMERG (tamaño = % dentro)",
         x: GRAD.imerg.alt, y: GRAD.imerg.p,
         marker: {{ size: GRAD.imerg.frac.map(f => 5 + 0.09 * f), color: COLOR_VAR.PI,
                    line: {{ color: "#FFFFFF", width: 1.2 }} }},
         text: GRAD.imerg.frac,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<br>%{{text:.0f}} % dentro"
                      + "<extra>celda de IMERG</extra>" }},
      {{ type: "scatter", mode: "lines", name: "tendencia IMERG", x: GRAD.rectaImerg.x,
         y: GRAD.rectaImerg.y, line: {{ color: COLOR_VAR.PI, width: 2 }}, hoverinfo: "skip" }},
      // la estación fuera de la divisoria: hueca, tampoco entra en el ajuste
      {{ type: "scatter", mode: "markers", name: "estación fuera de la divisoria",
         x: GRAD.pluFuera.alt, y: GRAD.pluFuera.p,
         marker: {{ size: 11, color: "rgba(0,0,0,0)", line: {{ color: GRIS, width: 1.6 }} }},
         text: GRAD.pluFuera.nombre,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<extra>%{{text}}</extra>" }},
      {{ type: "scatter", mode: "markers", name: "pluviómetros de la cuenca",
         x: GRAD.plu.alt, y: GRAD.plu.p,
         marker: {{ size: 13, color: COLOR_VAR.PL, line: {{ color: "#FFFFFF", width: 1.4 }} }},
         text: GRAD.plu.nombre,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<extra>%{{text}}</extra>" }},
      {{ type: "scatter", mode: "lines", name: "tendencia pluviómetros", x: GRAD.rectaPlu.x,
         y: GRAD.rectaPlu.y, line: {{ color: COLOR_VAR.PL, width: 2, dash: "dash" }}, hoverinfo: "skip" }}
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
         marker: {{ size: 13, color: COLOR_VAR.PL, line: {{ color: "#FFFFFF", width: 1.4 }} }},
         text: GRAD.pluLimpio.nombre,
         hovertemplate: "%{{y:.0f}} mm/año a %{{x:.0f}} m<extra>%{{text}}</extra>" }},
      {{ type: "scatter", mode: "lines", name: "tendencia de estas estaciones",
         x: GRAD.rectaLimpio.x, y: GRAD.rectaLimpio.y,
         line: {{ color: COLOR_VAR.PL, width: 2.4 }}, hoverinfo: "skip" }},
      {{ type: "scatter", mode: "lines", name: "tendencia de IMERG",
         x: GRAD.rectaImergEnTramo.x, y: GRAD.rectaImergEnTramo.y,
         line: {{ color: COLOR_VAR.PI, width: 2.4, dash: "dash" }}, hoverinfo: "skip" }}
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
      line: {{ color: COLOR_VAR[s.variable], width: s.grosor, dash: s.guion || "solid" }}, connectgaps: false,
      opacity: s.opacidad === undefined ? 1 : s.opacidad,
      legendgroup: s.grupo || s.nombre,
      showlegend: s.enLeyenda === undefined ? true : s.enLeyenda,
      hovertemplate: "%{{y:.0f}} mm<extra>" + s.nombre + "</extra>"
    }}));
    Plotly.react("g-series", series, base(), CONF);

    const ciclo = D.ciclo.map(s => ({{
      type: "scatter", mode: s.opacidad === undefined ? "lines+markers" : "lines",
      name: s.nombre, x: MES, y: s.y,
      line: {{ color: COLOR_VAR[s.variable], width: s.opacidad === undefined ? 2 : 1.1,
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
    dibujarAnomalias();
    dibujarAnz();
    dibujarTendMes();
    dibujarMapaAnioMes();
    dibujarMetodos();
    dibujarPendMes();
    dibujarFourier();
    dibujarPQ();
    dibujarPEMes();
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
