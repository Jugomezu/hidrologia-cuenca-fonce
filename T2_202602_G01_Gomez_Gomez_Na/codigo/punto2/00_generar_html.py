#!/usr/bin/env python3
"""Genera el reporte hidrológico interactivo en un único HTML portable.

Las secciones se ensamblan desde SECTION_BUILDERS; gráficas y tablas se
embeben para que el archivo final no dependa de rutas locales ni de internet.
Todas las rutas de entrada/salida se resuelven desde la raíz del proyecto.
"""
from html import escape
from pathlib import Path
import csv
import math
import base64
import json

ROOT = Path(__file__).resolve().parents[2]
PRODUCTS = ROOT / "productos" / "punto2"
OUTPUT = PRODUCTS / "reporte_punto2.html"
EMBEDDED_IMAGE_NAMES = set()


def read_csv(name):
    path = PRODUCTS / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(name):
    path = ROOT / "datos" / "punto2" / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def repair_mojibake(value):
    """Repara secuencias UTF-8 interpretadas como Windows-1252 en texto antiguo."""
    text = str(value)
    fixes = {
        "ÃƒÂ¡": "á", "ÃƒÂ©": "é", "ÃƒÂ­": "í", "ÃƒÂ³": "ó", "ÃƒÂº": "ú", "ÃƒÂ±": "ñ",
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ",
        "Ã": "Á", "Ã‰": "É", "Ã": "Í", "Ã“": "Ó", "Ãš": "Ú", "Ã‘": "Ñ",
        "Â²": "²", "Â³": "³", "Â·": "·", "â¥": "≥", "â‰¥": "≥", "â‰¤": "≤",
        "Ã¢â€°Â¥": "≥", "Ã¢â€°Â¤": "≤", "Ã¢â‚¬â€œ": "–",
        "âˆ’": "−", "â‰ˆ": "≈", "â€“": "–", "â€”": "—", "â€‘": "‑",
        "â€™": "’", "â€œ": "“", "â€": "”", "Ï„": "τ", "Î¾": "ξ",
        "â‚ƒ": "₃", "â‚„": "₄", "ï¿½": "", "�": "",
    }
    for broken, corrected in fixes.items():
        text = text.replace(broken, corrected)
    return text


def cell(value):
    if value is None:
        return ""
    text = repair_mojibake(value)
    try:
        number = float(text)
        if math.isfinite(number):
            text = str(int(number)) if number.is_integer() else format(number, ".3g")
    except (TypeError, ValueError):
        pass
    return escape(text)


def as_float(row, key, default=float("nan")):
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return default


def homogeneity_note():
    maxima = read_csv("maximos_anuales_intensidad.csv")
    annual = read_csv("resumen_completitud_anual.csv")
    periods = ((1949, 1972), (1973, 1994))
    maxima_groups, coverage = [], []
    for start, end in periods:
        maxima_groups.append([as_float(r, "intensity_1h_mmh") for r in maxima
                              if start <= as_float(r, "hydro_year", -1) <= end and math.isfinite(as_float(r, "intensity_1h_mmh"))])
        rows = [r for r in annual if start <= as_float(r, "year", -1) <= end]
        coverage.append((len(rows),
                         sum(as_float(r, "annual_completeness", 0) for r in rows) / len(rows) if rows else float("nan"),
                         sum(as_float(r, "valid_hours", 0) for r in rows) / len(rows) if rows else float("nan")))
    if not all(maxima_groups) or not all(coverage):
        return "No hay suficientes máximos anuales o resúmenes de completitud para comparar ambos periodos."
    a, b = maxima_groups
    combined = [(v, 0) for v in a] + [(v, 1) for v in b]
    combined.sort(key=lambda z: z[0])
    ranks = [0.0] * len(combined)
    tie_sum = 0
    i = 0
    while i < len(combined):
        j = i + 1
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        rank = ((i + 1) + j) / 2
        for k in range(i, j):
            ranks[k] = rank
        tie = j - i
        if tie > 1:
            tie_sum += tie ** 3 - tie
        i = j
    n1, n2 = len(a), len(b)
    rank_sum_a = sum(rank for rank, item in zip(ranks, combined) if item[1] == 0)
    u = rank_sum_a - n1 * (n1 + 1) / 2
    total_n = n1 + n2
    variance = n1 * n2 / 12 * ((total_n + 1) - tie_sum / (total_n * (total_n - 1)))
    z = (abs(u - n1 * n2 / 2) - .5) / math.sqrt(variance) if variance > 0 else 0.0
    p = 1 - math.erf(z / math.sqrt(2))
    def describe(values):
        values = sorted(values)
        mid = len(values) // 2
        median = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
        return sum(values) / len(values), median
    mean_a, median_a = describe(a)
    mean_b, median_b = describe(b)
    ca, cb = coverage
    return (f"Control exploratorio de homogeneidad de máximos de 1 h: 1949–1972 (n={n1}) "
            f"media/mediana {mean_a:.2f}/{median_a:.2f} mm/h, frente a 1973–1994 (n={n2}) "
            f"{mean_b:.2f}/{median_b:.2f} mm/h; Mann–Whitney U={u:.1f}, p≈{p:.3g} (aproximación normal con corrección por empates). "
            f"La completitud media cae de {ca[1]:.1%} ({ca[2]:.0f} horas/año) a {cb[1]:.1%} "
            f"({cb[2]:.0f} horas/año). La diferencia es una señal de posible inhomogeneidad asociada al cambio de cobertura/frecuencia de reportes; "
            "no demuestra por sí sola que el muestreo sea la única causa y limita la comparación directa de extremos.")


def table(headers, rows, class_name="", exact=False):
    if not rows:
        return '<p class="empty">Aún no hay datos disponibles.</p>'
    head = "".join(f"<th>{cell(h)}</th>" for h in headers)
    formatter = (lambda value: escape(str(value if value is not None else ""))) if exact else cell
    body = "".join("<tr>" + "".join(f"<td>{formatter(r.get(h, ''))}</td>" for h in headers) + "</tr>" for r in rows)
    return f'<div class="table-wrap"><table class="{class_name}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def filterable_table(headers, rows, table_id, class_name="compact", exact=False):
    if not rows:
        return '<p class="empty">AÃºn no hay datos disponibles.</p>'
    head = "".join(f"<th>{cell(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        format_value = (lambda value: escape(str(value if value is not None else ""))) if exact else cell
        body_rows.append("<tr>" + "".join(f"<td>{format_value(row.get(h, ''))}</td>" for h in headers) + "</tr>")
    return (f'<label class="table-search-label" for="filter-{escape(table_id)}">Filtrar comparaciones (duraciÃ³n, T, intensidades): '
            f'<input id="filter-{escape(table_id)}" class="table-search" type="search" data-table="{escape(table_id)}" placeholder="Escriba un valor o tÃ©rmino"></label>'
            f'<div class="table-wrap"><table id="{escape(table_id)}" class="{escape(class_name)}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table></div>')


def completeness_chart(rows):
    by_year = {int(r["year"]): r for r in rows if r.get("year", "").isdigit()}
    years = range(1931, 2027)
    width, height, left, right, top, bottom = 1000, 330, 58, 18, 28, 56
    plot_w, plot_h = width - left - right, height - top - bottom
    bar_w = max(2.2, plot_w / len(list(years)) * .68)
    svg = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Completitud anual 1931 a 2026">']
    for tick in (0, 20, 40, 60, 80, 100):
        y = top + plot_h * (1 - tick / 100)
        svg.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        svg.append(f'<text x="{left-9}" y="{y+4:.1f}" text-anchor="end" class="axis">{tick}%</text>')
    for i, year in enumerate(years):
        r = by_year.get(year)
        x = left + (i + .5) * plot_w / 96
        if r:
            try:
                pct = float(r.get("annual_completeness", 0)) * 100
            except ValueError:
                pct = 0
            pct = min(100, max(0, pct))
            y = top + plot_h * (1 - pct / 100)
            color = "#16836b" if r.get("retained", "").strip().lower() in ("sí", "si", "true", "1") else "#d99a38"
            svg.append(f'<rect x="{x-bar_w/2:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{top+plot_h-y:.2f}" rx="1" fill="{color}"><title>{year}: {pct:.1f}%; {cell(r.get("retained", "descartado"))}</title></rect>')
        if year in (1931, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2026):
            svg.append(f'<text x="{x:.1f}" y="{height-26}" text-anchor="middle" class="axis">{year}</text>')
    threshold_y = top + plot_h * .2
    svg.append(f'<line x1="{left}" y1="{threshold_y:.1f}" x2="{width-right}" y2="{threshold_y:.1f}" class="threshold"/>')
    svg.append(f'<text x="{width-right-3}" y="{threshold_y-5:.1f}" text-anchor="end" class="axis">80% anual</text>')
    svg.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" class="axis-line"/>')
    svg.append('</svg>')
    return "".join(svg)


def section_21():
    annual = read_csv("resumen_completitud_anual.csv")
    events = read_csv("eventos_extremos_verificados.csv")
    sensitivity = read_csv("sensibilidad_completitud.csv")
    kept = [r for r in annual if r.get("retained", "").strip().lower() in ("sí", "si", "true", "1")]
    return f'''<section id="seccion-21">
      <div class="eyebrow">Apartado 2.1</div><h2>Sitio, Datos Subdiarios y Control de Calidad</h2>
      <div class="site-card"><div class="site-mark">DEN</div><div><h3>Denver Stapleton</h3><p><strong>Estación:</strong> USW00023062 &nbsp; <strong>Variable:</strong> precipitación horaria &nbsp; <strong>Unidades:</strong> mm</p><p>Fuente: NOAA GHCNh, archivo histórico por estación. Las horas sin observación válida se mantienen como faltantes; trazas se etiquetan aparte de los ceros medidos.</p></div></div>
      <h3>Completitud anual, 1931–2026</h3>
      <p class="lede">Cada barra muestra la fracción de horas válidas del año. Verde indica que cumple simultáneamente ≥80% anual y ≥90% entre abril y septiembre; ámbar indica año descartado. Años aceptados en la tabla: {len(kept)}.</p>
      <div class="chart">{completeness_chart(annual)}</div>
      <div class="legend"><span><i class="green"></i>Aceptado (regla conjunta)</span><span><i class="amber"></i>Descartado</span><span class="note">La segunda regla se detalla en el archivo anual.</span></div>
      <h3>Diez eventos horarios mayores: revisión de acumulados</h3>
      <p class="lede">Las ventanas previas y posteriores reportan suma de lluvia y horas válidas dentro de 24 h; los códigos conservan el contexto del registro. Esta inspección detecta picos cercanos a vacíos, pero la confirmación meteorológica requiere contrastar reportes y fuente original.</p>
      {table(["timestamp", "precip_mm", "rain_prev_24h_mm", "valid_prev_24h_hours", "rain_next_24h_mm", "valid_next_24h_hours", "quality_code", "measurement_code"], events, "compact")}
      <h3>Sensibilidad al filtro de completitud</h3>
      <p class="lede">Comparación de máximos anuales horarios y cuantiles preliminares T=10 y T=50. Las estimaciones se calcularon con Gumbel por momentos; la muestra de años y el supuesto de distribución limitan su interpretación.</p>
      {table(["criterio", "numero_anios", "media_maximos_anuales_mm", "cuantil_1h_T10_mm", "cuantil_1h_T50_mm", "metodo"], sensitivity, "compact")}
      <div class="callout"><strong>Resolución y uso en microcuencas.</strong> La serie tiene resolución horaria. No permite medir directamente máximos de 10, 15 o 30 minutos, que pueden controlar la respuesta de microcuencas. La corrección de Weiss (1964) ajusta máximos obtenidos con reloj fijo frente a máximos de duración móvil y se aplica a la duración observada; no reconstruye variabilidad subhoraria. Para duraciones menores de una hora se necesita una ley de escala intensidad–duración (idealmente regional y validada), además de cuantificar su incertidumbre.</div>
    </section>'''


def image_card(filename, title, caption):
    path = PRODUCTS / filename
    if not path.exists():
        return f'<div class="figure"><h3>{cell(title)}</h3><p class="empty">Figura pendiente: {cell(filename)}</p></div>'
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    EMBEDDED_IMAGE_NAMES.add(path.name)
    image_src = f"data:image/png;base64,{encoded}"
    return (f'<figure class="figure"><button class="lightbox-trigger" type="button" aria-label="Ampliar: {cell(title)}">'
            f'<img src="{image_src}" alt="{cell(title)}"></button>'
            f'<figcaption><strong>{cell(title)}</strong><br>{cell(caption)}</figcaption></figure>')


def idf_widget_markup():
    return '''<div class="widget" id="idf-widget">
      <h3>Calculadora IDF y Método Racional</h3>
      <div class="controls">
        <label>Duración <select id="idf-duration"><option>5</option><option>10</option><option>15</option><option>30</option><option selected>60</option><option>120</option><option>180</option><option>360</option><option>720</option><option>1440</option></select> min</label>
        <label>Retorno T <select id="idf-return"><option>2</option><option>5</option><option>10</option><option>25</option><option selected>50</option><option>100</option></select> años</label>
        <label>Área A <input id="idf-area" type="number" min="0.01" step="0.01" value="1.0269"> km²</label>
        <label>Coeficiente C <input id="idf-coeff" type="number" min="0.05" max="1" step="0.005" value="0.495"></label>
      </div><div id="idf-output" class="widget-output" aria-live="polite"></div>
    </div>'''


def problem_a_widget_markup():
    return '''<div class="widget" id="problem-a-widget">
      <h3>Explorador del Problema A · Alcantarilla</h3>
      <div class="controls sliders">
        <label>t<sub>c</sub>: <output id="a-tc-value">60</output> min<input id="a-tc" type="range" min="30" max="120" step="1" value="60"></label>
        <label>C: <output id="a-c-value">0.495</output><input id="a-c" type="range" min="0.25" max="0.85" step="0.005" value="0.495"></label>
        <label>Retorno T<select id="a-t"><option>10</option><option>25</option><option selected>50</option><option>100</option></select> años</label>
      </div><div id="a-output" class="widget-output" aria-live="polite"></div>
    </div>'''


def problem_b_widget_markup():
    return '''<div class="widget" id="problem-b-widget">
      <h3>Explorador del Problema B · Tanque de detención</h3>
      <div class="controls">
        <label>Tormenta<select id="b-scenario"><option value="trap">Trapezoidal crítico · 75 min</option><option value="initial">Tiempo-área · pico inicial · 180 min</option><option value="center">Tiempo-área · pico central · 180 min</option><option value="final">Tiempo-área · pico final · 180 min</option></select></label>
        <label>Orificio D<sub>o</sub>: <output id="b-do-value">1500</output> mm<input id="b-do" type="range" min="1000" max="1800" step="10" value="1500"></label>
      </div><div id="b-metrics" class="widget-output" aria-live="polite"></div>
      <div class="canvas-wrap"><canvas id="tank-canvas" aria-label="Hidrograma de entrada y salida del tanque"></canvas><div id="tank-tooltip" class="chart-tooltip" hidden></div></div>
      <p class="technical-note">Tránsito local RK4 con Δt=1 min; S=A<sub>tanque</sub>h, A<sub>tanque</sub>=18.000 m², H<sub>max</sub>=3,5 m y orificio Cd=0,61. El modelo es ilustrativo y se recalcula íntegramente en este navegador.</p>
    </div>'''


def widget_data_script():
    master = read_csv("tabla_idf_completa.csv")
    atlas = [r for r in read_csv("idf_comparacion_oficial_y_evento.csv")
             if r.get("record_type") == "comparacion_atlas14"]
    params = read_csv("parametros_idf.csv")
    tw = next((r for r in params if r.get("formulacion", "").lower() == "talbot-wenzel"), {})
    design_rows = read_csv("problemaA_alcantarilla.csv")
    tank_rows = read_csv("problemaB_tanque_detencion.csv")
    bonus = {
        "cost": read_csv("bono_251_costo_esperado.csv"),
        "pot": read_csv("bono_252_pot_langbein.csv"),
        "climate": read_csv("bono_253_cambio_climatico.csv"),
    }
    design = design_rows[0] if design_rows else {}
    tank = tank_rows[0] if tank_rows else {}
    payload = {"idf": master, "atlas": atlas, "idf_params": tw,
               "design": design, "tank": tank, "bonus": bonus}
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    raw = raw.replace("</", "<\\/")
    return f'<script type="application/json" id="hydro-data">{raw}</script>'


def write_bonus_markdown():
    """Actualiza el suplemento técnico Markdown con los CSV generados."""
    cost = read_csv("bono_251_costo_esperado.csv")
    sensitivity = read_csv("bono_251_sensibilidad.csv")
    pot = [r for r in read_csv("bono_252_pot_langbein.csv") if r.get("record_type") == "cuantil_POT_Langbein"]
    climate = read_csv("bono_253_cambio_climatico.csv")
    hashimoto = read_csv("bono_254_hashimoto_crv.csv")
    summaries = [r for r in hashimoto if r.get("record_type") == "metricas_Hashimoto_1982"]
    events = [r for r in hashimoto if r.get("record_type") == "evento_superacion"]

    def md_table(headers, rows):
        def clean(value):
            text = str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")
            try:
                value_float = float(text)
                if math.isfinite(value_float):
                    return f"{value_float:.4g}"
            except ValueError:
                pass
            return text
        header = "| " + " | ".join(headers) + " |"
        line = "|" + "|".join("---" for _ in headers) + "|"
        body = ["| " + " | ".join(clean(row.get(h, "")) for h in headers) + " |" for row in rows]
        return "\n".join([header, line, *body])

    selected_cost = [r for r in cost if as_float(r, "T_d_y") in (2, 50, 227, 500)]
    content = f'''# Informe hidrológico · Punto 2

## 2.5 · Bonificaciones de Diseño y Riesgo

Los cálculos complementarios se procesaron con los archivos locales de la estación NOAA GHCNh Denver Stapleton (`USW00023062`). Los costos del apartado 2.5.1 se expresan en múltiplos normalizados de `C0`, ya que no se proporcionó un costo monetario base.

### 2.5.1 · Costo esperado de protección

Se calcula la intensidad con la IDF y el caudal racional `Q(T)=C·i(tc,T)·A/3.6`. El costo de obra es `Cobra=C0·(Qd/Q2)^0.6`, anualizado mediante el factor de recuperación de capital `FRC=r(1+r)^n/((1+r)^n−1)`. El daño para `Q>Qd` es `Dmax·[1−exp(−(Q−Qd)/(0.5Qd))]`; su integral en probabilidad anual de excedencia entrega el DAE, y `CTAE=Canual+DAE`.

Con `n=25`, `r=6%` y `Dmax=20C0`, el mínimo es **Tóptimo=227 años**. La integración numérica emplea 5,000 puntos medios entre 0 y `1/Td`.

{md_table(["T_d_y", "Canual_C0_per_year", "DAE_C0_per_year", "CTAE_C0_per_year"], selected_cost)}

Sensibilidad factorial `Dmax/C0 ∈ {{10,20,40}}` y `r ∈ {{3%,6%,10%}}`:

{md_table(["Dmax_multiplier_C0", "rate_sensitivity", "T_d_y", "CTAE_C0_per_year"], sensitivity)}

### 2.5.2 · Frecuencia POT/GPD y Langbein

Los máximos de tormenta se independizaron con al menos 6 horas secas. Se aplicó Weiss=1.14 a las intensidades horarias observadas, se escogió un umbral que produce aproximadamente 2 excedencias anuales y se ajustó una Pareto Generalizada (`scipy.stats.genpareto`, `c=+ξ`) a los excesos. La conversión a retorno AMS es `T_AMS=1/[1−exp(−1/T_E)]`.

{md_table(["return_period_AMS_y", "return_period_event_T_E_y", "POT_quantile_mm_h", "AMS_LP3_LMOM_quantile_mm_h", "AMS_empirical_quantile_mm_h"], pot)}

El umbral aplicado fue 9.40 mm/h antes de Weiss (10.72 mm/h después); se obtuvieron 91 eventos en 45 años válidos (`λ=2.022/año`). POT y AMS son métodos distintos: sus diferencias reflejan la tasa de eventos, el umbral y la extrapolación GPD.

### 2.5.3 · Cambio climático y no estacionariedad

Se aplicó el escalamiento de intensidad `1+0.07·ΔT` (Westra et al., 2014). La GEV no estacionaria usa `μ(t)=μ0+μ1t`, se evalúa en `t_final+25` y calcula la supervivencia sobre el mismo umbral crítico de la obra `i*=3.6Qc/(CA)=44.04 mm/h`. La fila base `ΔT=0` recupera `i(25.09 min,50)=40.96 mm/h`, `Q50=6.426 m³/s` y `Dcom=1500 mm`.

{md_table(["delta_temperature_C", "i_tc_future_mmh", "Qp_future_m3s", "D_commercial_mm", "T_effective_IDF_y", "risk_25y_IDF", "GEV_future_evaluation_year_t_final_plus_25", "T_effective_GEV_nonstationary_y", "risk_25y_GEV"], climate)}

**Discusión:** la IDF determinística y la GEV futura no son intercambiables; la segunda incorpora una tendencia extrapolada y puede ser muy sensible al periodo de ajuste. El 7%/°C es un escenario de sensibilidad, no un pronóstico local calibrado.

### 2.5.4 · Confiabilidad, resiliencia y vulnerabilidad de Hashimoto

Se estimó el caudal horario equivalente `Q(t)=C·A·i(t)/3.6`, con corrección Weiss=1.14. La confiabilidad `α` es la fracción temporal sin excedencia; la resiliencia `γ` es la tasa de transición de falla a cumplimiento, y `1/γ` aproxima la duración media de falla bajo esa definición. La vulnerabilidad `ν` se resume con el exceso medio y máximo sobre la capacidad.

{md_table(["diameter_mm", "Qc_m3s", "valid_hours_evaluated", "failed_hours", "reliability_alpha", "resilience_gamma_per_hour", "mean_failure_duration_1_over_gamma_hours", "vulnerability_mean_excess_m3s", "vulnerability_max_excess_m3s", "historical_exceedance_events"], summaries)}

Eventos de excedencia históricos guardados:

{md_table(["diameter_mm", "start_utc", "end_utc", "duration_hours", "peak_Q_m3s", "peak_excess_m3s"], events)}

Para la tubería de 1500 mm, el evento del 26 de julio de 1965 alcanza aproximadamente 7.226 m³/s, por encima de `Qc=6.909 m³/s`. La evaluación se limita a resolución horaria y al modelo racional equivalente; no sustituye un tránsito hidráulico.

![Figura 2.5 · Resumen gráfico de bonificaciones](fig_25_bonificaciones.png)
'''
    (PRODUCTS / "reporte_punto2_completo.md").write_text(content, encoding="utf-8")


def section_22():
    maxima = read_csv("maximos_anuales_intensidad.csv")
    params = read_csv("parametros_distribuciones.csv")
    quantiles = read_csv("cuantiles_distribuciones.csv") or read_csv("cuantiles_y_bootstrap.csv")
    goodness = read_csv("bondad_y_estacionariedad.csv")
    if not any((maxima, params, quantiles, goodness)):
        return '<section id="seccion-22"><div class="eyebrow">Apartado 2.2</div><h2>Extremos y distribuciones</h2><p class="empty">Ejecute 02_extremos_y_distribuciones.py para generar los resultados.</p></section>'
    max_headers = list(maxima[0]) if maxima else []
    param_headers = list(params[0]) if params else []
    quant_headers = list(quantiles[0]) if quantiles else []
    gof_headers = list(goodness[0]) if goodness else []
    quantiles_lp3 = sorted(
        [r for r in quantiles if r.get("distribution", "").strip().upper() == "LP3"
         and r.get("method", "").strip().upper() == "LMOM"],
        key=lambda r: (as_float(r, "duration_h"), as_float(r, "return_period_y")))
    return f'''<section id="seccion-22">
      <div class="eyebrow">Apartado 2.2</div><h2>Máximos, distribuciones e incertidumbre</h2>
      <p class="lede">Se estiman máximos móviles por año hidrológico octubre–septiembre. Las intensidades incluyen la corrección de Weiss (1964), con <em>f</em><sub>W</sub> = 1/(1 − 1/(8n)); la columna de coherencia verifica que las láminas corregidas no decrezcan al aumentar la duración. El año hidrológico se identifica por el año en que termina.</p>
      <h3>Lectura de las figuras</h3>
      <p class="lede">El papel de probabilidad permite comparar las colas observadas con tres familias de extremos; el diagrama L‑momento resume la forma de las muestras y la figura bootstrap muestra cómo crece la incertidumbre con T/N.</p>
      <div class="fig-grid">
        {image_card("fig2_papel_probabilidad.png", "Papel de probabilidad", "Gringorten (a=0,44), observaciones y ajustes LMOM Gumbel, GEV y LP3 para 1, 6 y 24 h.")}
        {image_card("fig2_diagrama_lmomentos.png", "Diagrama de razones L‑momento", "τ₃ y τ₄ muestrales por duración frente a curvas teóricas GEV, Gumbel, Log‑normal y Pearson III.")}
        {image_card("fig2_incertidumbre_bootstrap.png", "Incertidumbre bootstrap", "Ancho relativo del intervalo del 95% frente a T/N para el ajuste Gumbel LMOM.")}
      </div>
      <h3>Máximos anuales por duración</h3>
      {filterable_table(max_headers, maxima, "annual-maxima-filter", "compact")}
      <h3>Parámetros ajustados</h3>
      <p class="lede">MOM: momentos; LMOM: L‑momentos muestrales no sesgados según las fórmulas PWM de Hosking y Wallis; MLE: máxima verosimilitud. En GEV se informa explícitamente ξ y el parámetro de SciPy c = −ξ.</p>
      {table(param_headers, params, "compact")}
      <h3>Cuantiles e intervalos bootstrap del 95% · modelo principal LP3/LMOM</h3>
      <p class="lede">Se muestran las 36 combinaciones de seis duraciones y seis periodos de retorno para el ajuste seleccionado. Las cifras conservan la precisión de los CSV. Las demás distribuciones y métodos siguen disponibles en {escape("cuantiles_distribuciones.csv" if (PRODUCTS / "cuantiles_distribuciones.csv").exists() else "cuantiles_y_bootstrap.csv")} para trazabilidad.</p>
      {filterable_table(quant_headers, quantiles_lp3, "lp3-quantiles-filter", "compact exact-values", exact=True)}
      <h3>Bondad de ajuste y estacionariedad</h3>
      <p class="lede">KS y AD comparan la distribución ajustada con los máximos observados; PPCC es la correlación producto‑momento en el gráfico de probabilidad. Mann–Kendall evalúa tendencia monotónica y la pendiente de Sen se expresa en mm/h por año hidrológico.</p>
      {table(gof_headers, goodness, "compact")}
    </section>'''


def section_23():
    params = read_csv("parametros_idf.csv")
    master = read_csv("tabla_idf_completa.csv")
    if not params and not master:
        return '<section id="seccion-23"><div class="eyebrow">Apartado 2.3</div><h2>Curvas IDF</h2><p class="empty">Ejecute 03_curvas_idf.py para generar los resultados.</p></section>'
    stats_headers = [h for h in ("formulacion", "MAPE_pct", "RMSE_mmh", "R2", "T_curve_crossings", "ganador_global", "modelo_maestro_b_positivo") if params and h in params[0]]
    master_headers = [h for h in ("duration_min", "duration_h", "return_period_y", "intensity_mmh", "depth_mm", "ci95_low_mmh", "ci95_high_mmh", "ci95_low_depth_mm", "ci95_high_depth_mm", "extrapolated_subhour", "model") if master and h in master[0]]
    diagnostic = read_csv("bondad_y_estacionariedad.csv")
    lp3_trend = [r for r in diagnostic if r.get("distribution") == "LP3" and r.get("method") == "LMOM"]
    negative = bool(lp3_trend) and all(float(r.get("MK_S", "0") or 0) < 0 for r in lp3_trend)
    comparison = []
    for duration in (1, 2, 3, 6, 12, 24):
        same_method = {r.get("distribution"): r for r in diagnostic
                       if r.get("method") == "LMOM" and r.get("duration_h") == str(duration)}
        if all(name in same_method for name in ("LP3", "GEV", "Gumbel")):
            comparison.append({"duration_h": duration,
                               "LP3_KS": same_method["LP3"].get("KS"),
                               "GEV_KS": same_method["GEV"].get("KS"),
                               "Gumbel_KS": same_method["Gumbel"].get("KS"),
                               "LP3_AD": same_method["LP3"].get("AD"),
                               "GEV_AD": same_method["GEV"].get("AD"),
                               "Gumbel_AD": same_method["Gumbel"].get("AD")})
    validation = read_csv("idf_comparacion_oficial_y_evento.csv")
    atlas_rows = [r for r in validation if r.get("record_type") == "comparacion_atlas14"]
    atlas_headers = [h for h in ("duration_min", "T_y", "our_intensity_mmh",
                                 "atlas14_intensity_mmh", "atlas14_lower90_intensity_mmh",
                                 "atlas14_upper90_intensity_mmh", "relative_bias_pct")
                     if atlas_rows and h in atlas_rows[0]]
    grid_rows = [r for r in validation if r.get("record_type") == "comparacion_idf_malla"]
    event_rows = []
    for row in validation:
        if row.get("record_type") == "evento_historico_1965":
            event_rows.append({"Fecha": row.get("event_date"), "Intensidad (mm/h)": row.get("event_intensity_mmh"),
                               "Periodo de retorno": f"T = {as_float(row, 'T_years'):.1f} aÃ±os",
                               "Fuente / criterio": row.get("event_basis")})
        elif row.get("record_type") == "evento_reciente_denver":
            event_rows.append({"Fecha": row.get("event_date"), "Intensidad (mm/h)": row.get("event_intensity_mmh"),
                               "Periodo de retorno": f"T â‰¥ {as_float(row, 'T_years'):.1f} aÃ±os",
                               "Fuente / criterio": row.get("event_basis")})
    grid_headers = [h for h in ("grid_product", "duration_min", "T_y", "our_intensity_mmh",
                                "grid_intensity_mmh", "idf_grid_over_point_ratio")
                    if grid_rows and h in grid_rows[0]]
    return f'''<section id="seccion-23">
      <div class="eyebrow">Apartado 2.3</div><h2>Curvas Intensidad–Duración–Frecuencia</h2>
      <p class="lede">Se toman los cuantiles de Log‑Pearson III ajustado por L‑momentos (LP3/LMOM) como base y se comparan con GEV y Gumbel. En la comparación homogénea de ajustes LMOM, los CSV de bondad de ajuste muestran que LP3 tiene KS y AD menores o iguales frente a ambas alternativas en las seis duraciones; las formulaciones paramétricas se evalúan luego contra esos cuantiles.</p>
      <p class="lede">Se impuso coherencia física con regresión isotónica sobre P(d,T)=i·d para hacer no decreciente la lámina con duración y sobre la intensidad frente al periodo de retorno para evitar cruces. Las curvas paramétricas tienen exponente temporal m positivo. Las bandas subhorarias se obtienen ajustando los límites bootstrap por duración con el modelo IDF elegido.</p>
      <p class="technical-note"><strong>Nota sobre el límite bootstrap:</strong> para T=5 años y duraciones subhorarias, la cota <code>ci95_low_mmh</code> puede coincidir con <code>intensity_mmh</code> después de la proyección isotónica. Al imponer simultáneamente orden creciente de lámina con duración y de intensidad con T, la proyección eleva cotas inferiores que violan esas restricciones hasta la frontera factible; no significa que el bootstrap original tuviera un intervalo degenerado.</p>
      <p class="callout"><strong>Selección:</strong> Bernard/Sherman, Talbot/Wenzel y Koutsoyiannis se compararon con MAPE, RMSE y R². La tabla marca el mejor ajuste global y, por separado, el mejor de los modelos con desplazamiento b&gt;0 utilizado para la tabla maestra y la extrapolación a duraciones cortas, lo que limita la intensidad cuando d tiende a cero.</p>
      <div class="fig-grid">
        {image_card("fig3_curvas_idf_loglog.png", "Curvas IDF en escala log–log", "Puntos LP3/LMOM ajustados, curvas para T=2–100 años, bandas bootstrap al 95% en T=10 y 50; sombreado indica extrapolación menor de una hora.")}
        {image_card("fig3_comparacion_modelos_idf.png", "Residuales de los modelos", "Comparación de errores relativos por duración para las tres formulaciones paramétricas.")}
      </div>
      <h3>Bondad relativa de las distribuciones base</h3>
      {table(["duration_h", "LP3_KS", "GEV_KS", "Gumbel_KS", "LP3_AD", "GEV_AD", "Gumbel_AD"], comparison, "compact")}
      <h3>Comparación de ecuaciones IDF</h3>
      {table(stats_headers, params, "compact")}
      <h3>Tabla maestra de intensidades y láminas</h3>
      <p class="lede">Intensidad en mm/h y lámina acumulada en mm para 5 minutos a 24 horas, con bandas del 95%. Las duraciones inferiores a 60 minutos son extrapolaciones del modelo, no mediciones subhorarias.</p>
      {idf_widget_markup()}
      {table(master_headers, master, "compact")}
      <h3>2.3.3 Validación oficial NOAA Atlas 14 Vol. 8 y escala malla/punto</h3>
      <p class="lede">Se cotejan las 36 combinaciones de duración y periodo de retorno con las profundidades PDS puntuales obtenidas del endpoint oficial NOAA HDSC para Denver Stapleton. La diferencia relativa compara nuestra IDF LP3/LMOM–Talbot/Wenzel con NOAA. Use el filtro para localizar duraciones, T o valores específicos.</p>
      {filterable_table(atlas_headers, atlas_rows, "atlas14-comparison", "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica — punto frente a malla:</strong> una IDF puntual de pluvi�metro/Atlas 14 y una IDF derivada de una celda ERA5-Land o IMERG no representan el mismo soporte espacial, periodo ni proceso. La razón IDF<sub>malla</sub>/IDF<sub>puntual</sub> mezcla reducción areal (FRA), suavizado espacial y sesgo del producto; debe derivarse con series y periodos comparables. {("La comparación de malla aparece en la tabla siguiente." if grid_rows else "Los CSV no contienen IDF de celda ERA5-Land/IMERG: no se inventa una razón numérica malla/punto.")}</div>
      {table(grid_headers, grid_rows, "compact") if grid_rows else ""}
      <h3>2.3.4 Periodo de retorno de eventos históricos reales</h3>
      <p class="lede">Los periodos se estiman con LP3/LMOM sobre la serie de máximos anuales aceptada. Para el evento de 2022 se usa un umbral espacial/subhorario documentado, por lo que el resultado es una cota inferior y no un periodo puntual observado en la estación.</p>
      {table(["Fecha", "Intensidad (mm/h)", "Periodo de retorno", "Fuente / criterio"], event_rows, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica — extremos:</strong> el máximo del 26-jul-1965 equivale a T=75.7 años tras la corrección de Weiss; el evento intenso del 07-ago-2022 alcanza T≥137.3 años en la distribución ajustada. Son estimaciones extrapoladas de una muestra finita y dependen del control de homogeneidad; no son intervalos deterministas entre tormentas.</div>
      <h3>Estacionariedad de los máximos</h3>
      <p class="lede">{("Los estadísticos Mann–Kendall de LP3/LMOM son negativos en las seis duraciones. Un cambio en la frecuencia de muestreo/reportes después de 1973 puede contribuir a una inhomogeneidad y a una tendencia aparente; esta explicación es una hipótesis que requiere una prueba de homogeneidad independiente." if negative else "Consulte los estadísticos Mann–Kendall y las pendientes de Sen presentados en la Sección 2.2; la atribución de tendencias a cambios de muestreo requiere pruebas de homogeneidad independientes.")}</p>
    </section>'''


def section_24():
    meta = read_json("metadatos_microcuenca.json")
    problem_a_rows = read_csv("problemaA_alcantarilla.csv")
    mc_rows = read_csv("problemaA_montecarlo.csv")
    sensitivity_all = read_csv("problemaA_sensibilidad.csv")
    problem_b_all = read_csv("problemaB_tanque_detencion.csv")
    base_results = read_csv("resultados_diseno_hidrologico.csv")
    design = problem_a_rows[0] if problem_a_rows else {}
    mc = next((r for r in mc_rows if r.get("record_type") == "resumen_montecarlo"), {})
    sensitivity = sorted((r for r in sensitivity_all if r.get("record_type") == "sensibilidad"),
                         key=lambda r: as_float(r, "impact_rank", 999))
    b_rows = sorted(problem_b_all, key=lambda r: (0 if r.get("scenario_type") == "racional_modificado" else 1,
                                                   as_float(r, "duration_min")))
    area = as_float(meta, "area_km2")
    length = as_float(meta, "main_channel_length_m")
    slope = as_float(meta, "relief_slope_S0_m_per_m")
    distance_km = as_float(meta, "distance_basin_centroid_to_station_m") / 1000
    meta_rows = [
        {"Parámetro": "Estación", "Valor": meta.get("station", "USW00023062")},
        {"Parámetro": "Modelo DEM", "Valor": "Copernicus GLO-30 (DSM, 30 m)"},
        {"Parámetro": "Área", "Valor": f"{area:.4f} km² ({as_float(meta, 'area_ha'):.2f} ha)"},
        {"Parámetro": "Longitud de cauce principal", "Valor": f"{length:.1f} m"},
        {"Parámetro": "Desnivel cuenca–salida", "Valor": f"{as_float(meta, 'elevation_max_m')-as_float(meta, 'outlet_elevation_m'):.2f} m"},
        {"Parámetro": "Pendiente S₀", "Valor": f"{slope:.5f} m/m"},
        {"Parámetro": "Distancia al pluviómetro (centroide)", "Valor": f"{distance_km:.2f} km"},
    ]
    meta_headers = ["Parámetro", "Valor"]
    a_headers = ["Parámetro", "Valor"]
    a_rows = [
        {"Parámetro": "Coeficiente ponderado C", "Valor": f"{as_float(design, 'C_weighted'):.3f}"},
        {"Parámetro": "Tiempo de concentración adoptado", "Valor": f"{as_float(design, 'tc_design_min'):.0f} min"},
        {"Parámetro": "Periodo de retorno", "Valor": f"T={as_float(design, 'T_design_y'):.0f} años"},
        {"Parámetro": "Intensidad IDF", "Valor": f"{as_float(design, 'idf_intensity_point_mmh'):.2f} mm/h"},
        {"Parámetro": "FRA cuenca pequeña", "Valor": f"{as_float(design, 'FRA'):.3f}"},
        {"Parámetro": "Caudal racional Qp", "Valor": f"{as_float(design, 'Qp_rational_m3s'):.3f} m³/s"},
        {"Parámetro": "Diámetro requerido / comercial", "Valor": f"{as_float(design, 'D_required_mm'):.0f} / {as_float(design, 'D_commercial_mm'):.0f} mm"},
        {"Parámetro": "Capacidad Manning a tubo lleno", "Valor": f"{as_float(design, 'Qc_full_m3s'):.3f} m³/s"},
        {"Parámetro": "Factor de seguridad nominal", "Valor": f"{as_float(design, 'FS_nominal'):.2f}"},
        {"Parámetro": "FRA ilustrativo para 250 km²", "Valor": "0.662"},
    ]
    sens_headers = [h for h in ("impact_rank", "factor", "min_D_mm", "max_D_mm", "impact_D_mm") if sensitivity and h in sensitivity[0]]
    sens_labels = {"impact_rank": "Orden", "factor": "Fuente de incertidumbre",
                   "min_D_mm": "D mínimo (mm)", "max_D_mm": "D máximo (mm)", "impact_D_mm": "Rango ΔD (mm)"}
    sensitivity_view = [{sens_labels.get(k, k): r.get(k, "") for k in sens_headers} for r in sensitivity]
    sens_headers = [sens_labels.get(k, k) for k in sens_headers]
    b_headers = [h for h in ("scenario_type", "pattern", "duration_min", "d_crit_min",
                             "Imax_m3s", "Omax_m3s", "Qlim_m3s", "Vreq_m3", "hmax_m")
                 if b_rows and h in b_rows[0]]
    b_labels = {"scenario_type": "Método", "pattern": "Hietograma", "duration_min": "Duración (min)",
                "d_crit_min": "d crítica (min)", "Imax_m3s": "I máx. (m³/s)",
                "Omax_m3s": "O máx. (m³/s)", "Qlim_m3s": "Q límite (m³/s)",
                "Vreq_m3": "V requerido (m³)", "hmax_m": "Tirante máx. (m)"}
    b_view = [{b_labels.get(k, k): r.get(k, "") for k in b_headers} for r in b_rows]
    b_headers = [b_labels.get(k, k) for k in b_headers]
    base_design = [r for r in base_results if r.get("scenario_type", "").strip().casefold().startswith("dise")
                   and r.get("AMC", "").strip() == "AMC-II"
                   and math.isclose(as_float(r, "Ia_fraction"), .20, abs_tol=1e-9)
                   and math.isclose(as_float(r, "duration_h"), 2.0, abs_tol=1e-9)]
    amc50 = [r for r in base_results if r.get("scenario_type", "").strip().casefold().startswith("dise")
             and as_float(r, "T") == 50 and math.isclose(as_float(r, "duration_h"), 2.0, abs_tol=1e-9)
             and math.isclose(as_float(r, "Ia_fraction"), .20, abs_tol=1e-9)]
    design_headers = [h for h in ("T", "rain_depth_mm", "effective_depth_mm", "Qp_rational_m3s",
                                  "Qp_scs_m3s", "Qp_scs_low95_m3s", "Qp_scs_high95_m3s", "Ve_scs_m3")
                      if base_design and h in base_design[0]]
    amc_headers = [h for h in ("AMC", "rain_depth_mm", "effective_depth_mm", "Qp_scs_m3s", "Ve_scs_m3")
                   if amc50 and h in amc50[0]]
    p_effective = 100 * as_float(mc, "annual_effective_failure_probability")
    risk_effective = 100 * as_float(mc, "effective_risk_life_25y")
    fs = as_float(mc, "FS_nominal", as_float(design, "FS_nominal"))
    return f'''<section id="seccion-24">
      <div class="eyebrow">Apartado 2.4</div><h2>Diseño hidrológico de microcuenca</h2>
      <p class="lede">La sección separa la cuenca topográfica delimitada con DEM del escenario metodológico NRCS que se conserva como respaldo. El DEM Copernicus es un modelo de superficie y la cuenca automática requiere validación de drenaje urbano antes de usarla para construcción.</p>
      <h3>Caracterización de la microcuenca real · DEM Copernicus GLO-30</h3>
      {image_card("fig_24_microcuenca_dem.png", "Microcuenca delimitada junto a Denver Stapleton", "Cuenca candidata y cauce extraídos del DEM Copernicus GLO-30 reproyectado a UTM 13N.")}
      {table(meta_headers, meta_rows, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> el área de {area:.4f} km² y la distancia de {distance_km:.2f} km sitúan la cuenca en escala de respuesta rápida; el DSM puede incluir edificios/vegetación y no representa por sí solo cunetas, sumideros ni conexiones de alcantarillado.</div>

      <h3>Problema A · Alcantarilla circular por Método Racional y Manning</h3>
      <p class="lede">Predimensionamiento con geometría leída de los metadatos DEM, cobertura periurbana ponderada, IDF LP3/LMOM y Talbot–Wenzel, Manning a tubo lleno y diámetro comercial superior. El diseño usa T=50 años y contrasta el criterio de riesgo con Chow et al. (1988).</p>
      {problem_a_widget_markup()}
      {table(a_headers, a_rows, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> el resumen de Monte Carlo (N=5.000) da p<sub>ef</sub>={p_effective:.2f}% anual, R<sub>ef</sub>(25 años)={risk_effective:.1f}% y FS={fs:.2f}; la probabilidad se estima con LP3 en log<sub>10</sub>(mm/h), anclada a la IDF de 45.51 mm/h para T=50. Para 250 km² el FRA ilustrativo 0.662 reduce la lluvia puntual a un promedio areal y muestra por qué la lluvia convectiva no puede suponerse uniforme en cuencas extensas.</div>
      {image_card("fig_24_problemaA_sensibilidad_mc.png", "Sensibilidad y Monte Carlo de la alcantarilla", "Tornado de variación del diámetro requerido y distribuciones Monte Carlo de carga y capacidad; línea de capacidad y factor de seguridad del diseño.")}
      <h4>Sensibilidad del diámetro requerida · ordenada por impacto</h4>
      {table(sens_headers, sensitivity_view, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> el tiempo de concentración domina la sensibilidad del diámetro, seguido por el intervalo bootstrap de la IDF y la incertidumbre de C; la distribución alternativa tiene menor impacto en este predimensionamiento.</div>

      <h3>Problema B · Tanque de detención por urbanización</h3>
      <p class="lede">El escenario cambia de C=0.495 y t<sub>c</sub>=60 min a C=0.78 y t<sub>c</sub>=30 min, manteniendo T=50 años y limitando la descarga a Q<sub>lim</sub>=Q<sub>p,previo</sub>={as_float(b_rows[0], 'Qlim_m3s') if b_rows else 6.426:.3f} m³/s. El tanque prismático tiene huella 18.000 m², altura útil 3.5 m y volumen geométrico 63.000 m³; la salida se controla con orificio dimensionado y RK4 de 1 min.</p>
      {problem_b_widget_markup()}
      {image_card("fig_24_problemaB_tanque.png", "Volumen de detención y tránsito del tanque", "Duración crítica trapezoidal; hidrogramas de entrada/salida y almacenamiento con pico inicial, central y final.")}
      {table(b_headers, b_view, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> para la tormenta de 180 min, el patrón con pico al final necesita {as_float(next((r for r in b_rows if r.get('pattern') == 'pico_al_final_creciente'), {}), 'Vreq_m3'):.0f} m³, frente a {as_float(next((r for r in b_rows if r.get('pattern') == 'pico_al_inicio_decreciente'), {}), 'Vreq_m3'):.0f} m³ con pico inicial. Al concentrar la lluvia intensa hacia el final, llega más volumen antes de que el tanque y el orificio hayan evacuado agua.</div>

      <h3>Respaldo metodológico · Hietogramas NRCS-UH y AMC</h3>
      <p class="lede">Se conserva el ejercicio NRCS de bloques alternos del escenario representativo previo (A=1.85 km², C=0.52, C<sub>N,II</sub>=78 y t<sub>c</sub>=35 min). Estos resultados documentan el método y no se mezclan con los metadatos de la cuenca DEM de 1.0269 km².</p>
      {image_card("fig4_hietograma_lluvia_efectiva.png", "Hietograma NRCS de lluvia efectiva", "Bloques alternos, abstracciones y exceso para T=50 años, D=2 h, AMC-II.")}
      {image_card("fig4_hidrogramas_diseno.png", "Hidrogramas NRCS-UH", "Q(t) para T=10–100 años con AMC-II y sensibilidad AMC-I/II/III para T=50 años.")}
      {image_card("fig4_caudales_pico_incertidumbre.png", "Caudales pico e incertidumbre NRCS", "Comparación Racional/NRCS-UH, intervalos bootstrap y efecto de duración.")}
      <h4>Diseño complementario · AMC-II, I<sub>a</sub>=0.20S, D=2 h</h4>
      {table(design_headers, base_design, "compact")}
      <h4>Sensibilidad de humedad antecedente · T=50, D=2 h</h4>
      {table(amc_headers, amc50, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> AMC-I/II/III modifica el almacenamiento inicial y la lluvia efectiva NRCS; conserva valor como comparación de pérdidas, mientras que los escenarios nuevos A y B usan los parámetros y el control de descarga indicados en sus respectivos CSV.</div>
    </section>'''

def section_25():
    problem_a = read_csv("problemaA_alcantarilla.csv")
    mc_rows = read_csv("problemaA_montecarlo.csv")
    problem_b = read_csv("problemaB_tanque_detencion.csv")
    meta = read_json("metadatos_microcuenca.json")
    annual = read_csv("resumen_completitud_anual.csv")
    kept = sum(1 for r in annual if r.get("retained", "").strip().casefold() in ("sí", "si", "true", "1"))
    design = problem_a[0] if problem_a else {}
    mc = next((r for r in mc_rows if r.get("record_type") == "resumen_montecarlo"), {})
    b_final = next((r for r in problem_b if r.get("pattern") == "pico_al_final_creciente"), {})
    a_headers = ["Resultado", "Valor"]
    a_rows = [
        {"Resultado": "Microcuenca real DEM", "Valor": f"A={as_float(meta, 'area_km2'):.4f} km²; L={as_float(meta, 'main_channel_length_m'):.1f} m; S₀={as_float(meta, 'relief_slope_S0_m_per_m'):.5f}"},
        {"Resultado": "Alcantarilla T=50", "Valor": f"Dcom={as_float(design, 'D_commercial_mm'):.0f} mm; FS={as_float(design, 'FS_nominal'):.2f}; p anual MC={100*as_float(mc, 'annual_effective_failure_probability'):.2f}%"},
        {"Resultado": "Tanque 180 min, pico final", "Valor": f"Vreq={as_float(b_final, 'Vreq_m3'):.0f} m³; hmax={as_float(b_final, 'hmax_m'):.2f} m; Qlim={as_float(b_final, 'Qlim_m3s'):.3f} m³/s"},
        {"Resultado": "Completitud GHCNh", "Valor": f"{kept} años aceptados con el filtro anual y abril–septiembre"},
    ]
    homogeneity = homogeneity_note()
    return f'''<section id="seccion-25">
      <div class="eyebrow">Cierre</div><h2>Síntesis Ejecutiva, Limitaciones y Recomendaciones</h2>
      <p>La lluvia horaria de Denver Stapleton se depuró con criterios de completitud, se ajustó como IDF y se contrastó con NOAA Atlas 14. Los eventos del 26-jul-1965 (T≈75.7 años) y 07-ago-2022 (T≥137.3 años) ilustran extremos que exceden la escala frecuente, sujetos a incertidumbre y homogeneidad.</p>
      {table(a_headers, a_rows, "compact")}
      <p class="technical-note"><strong>Control de homogeneidad 1949–1972 vs. 1973–1994:</strong> {homogeneity}</p>
      <div class="interpretation"><strong>Conclusión de diseño:</strong> el Problema A entrega un predimensionamiento de alcantarilla circular con riesgo explícito y FS nominal; el Problema B cuantifica el almacenamiento incremental tras urbanización y muestra que el patrón temporal de la lluvia controla el volumen requerido. Confirmar la cuenca, obras de entrada, remanso y operación antes de diseño final.</div>
      <h3>Limitaciones y recomendaciones</h3>
      <ul class="recommendations">
        <li>La cuenca derivada de Copernicus GLO-30 es una candidata topográfica; validar con topografía bare-earth, red pluvial levantada y modelación de drenaje de Denver.</li>
        <li>La IDF subhoraria es extrapolada desde datos horarios; validar con pluviógrafos/radar y una ley de escala regional antes de dimensionar microdrenaje.</li>
        <li>La comparación NOAA es puntual. No hay todavía una serie de celda ERA5-Land/IMERG en los productos locales para estimar una razón malla/punto homogénea.</li>
        <li>El escenario NRCS AMC-I/II/III conserva valor metodológico y corresponde a una cuenca representativa diferente de la delimitación DEM usada por los Problemas A y B.</li>
        <li>Verificar criterios municipales, pérdidas locales, sumergencia, remanso, bloqueo por sedimentos, seguridad estructural y rutas de excedencia superficial antes de construcción.</li>
      </ul>
      <div class="callout"><strong>Uso recomendado:</strong> reporte de análisis y predimensionamiento. No reemplaza los planos, la revisión normativa ni el modelo hidráulico/hidrológico de detalle.</div>
    </section>'''

# Punto de extensión para las próximas secciones del informe.
def bonus_widget_markup():
    return '''<div class="widget" id="bonus-widget">
      <h3>Simulador de costo y calentamiento</h3>
      <div class="controls sliders">
        <label>D<sub>max</sub>/C<sub>0</sub>: <output id="bonus-dmax-label">20</output><input id="bonus-dmax" type="range" min="10" max="40" step="1" value="20"></label>
        <label>Tasa de descuento r: <output id="bonus-rate-label">6%</output><input id="bonus-rate" type="range" min="3" max="10" step="1" value="6"></label>
        <label>Calentamiento ΔT: <output id="bonus-dt-label">0.0 °C</output><input id="bonus-dt" type="range" min="0" max="3" step="0.1" value="0"></label>
      </div><div id="bonus-output" class="widget-output" aria-live="polite"></div>
    </div>'''


def section_26():
    cost = read_csv("bono_251_costo_esperado.csv")
    sensitivity = read_csv("bono_251_sensibilidad.csv")
    pot = [r for r in read_csv("bono_252_pot_langbein.csv") if r.get("record_type") == "cuantil_POT_Langbein"]
    climate = read_csv("bono_253_cambio_climatico.csv")
    hashimoto = read_csv("bono_254_hashimoto_crv.csv")
    hash_summary = [r for r in hashimoto if r.get("record_type") == "metricas_Hashimoto_1982"]
    events = [r for r in hashimoto if r.get("record_type") == "evento_superacion"]
    selected_cost = [r for r in cost if as_float(r, "T_d_y") in (2, 50, 227, 500)]
    cost_headers = ["T_d_y", "Canual_C0_per_year", "DAE_C0_per_year", "CTAE_C0_per_year"]
    sens_headers = ["Dmax_multiplier_C0", "rate_sensitivity", "T_d_y", "CTAE_C0_per_year"]
    pot_headers = ["return_period_AMS_y", "return_period_event_T_E_y", "POT_quantile_mm_h", "AMS_LP3_LMOM_quantile_mm_h", "AMS_empirical_quantile_mm_h"]
    climate_headers = ["delta_temperature_C", "i_tc_future_mmh", "Qp_future_m3s", "D_commercial_mm", "T_effective_IDF_y", "risk_25y_IDF", "GEV_future_evaluation_year_t_final_plus_25", "T_effective_GEV_nonstationary_y", "risk_25y_GEV"]
    hash_headers = ["diameter_mm", "Qc_m3s", "reliability_alpha", "resilience_gamma_per_hour", "mean_failure_duration_1_over_gamma_hours", "vulnerability_mean_excess_m3s", "vulnerability_max_excess_m3s", "historical_exceedance_events"]
    event_headers = ["diameter_mm", "start_utc", "end_utc", "duration_hours", "peak_Q_m3s", "peak_excess_m3s"]
    return f'''<section id="seccion-26">
      <div class="eyebrow">Apartado 2.5</div><h2>Bonificaciones de Diseño y Riesgo</h2>
      <p class="lede">Cuatro análisis complementarios cuantifican el compromiso entre costo de protección, extremos por excedencias, calentamiento futuro y desempeño histórico de la alcantarilla. Los costos se expresan en unidades de C<sub>0</sub> normalizadas porque los archivos fuente no especifican un costo monetario base.</p>
      <div class="fig-grid">{image_card("fig_25_bonificaciones.png", "Síntesis gráfica de las bonificaciones", "Paneles A–D: costo-riesgo, POT/AMS, calentamiento y confiabilidad histórica.")}</div>
      <h3>2.5.1 · Costo esperado de protección</h3>
      <p>Se evalúan T<sub>d</sub>=2–500 años con Q<sub>d</sub>=Q(1/T<sub>d</sub>), costo anualizado FRC·C<sub>obra</sub> y daño anual esperado integrado entre p=0 y 1/T<sub>d</sub>. El mínimo guardado es T<sub>óptimo</sub>=227 años para D<sub>max</sub>=20C<sub>0</sub> y r=6%.</p>
      {table(cost_headers, selected_cost, "compact")}{table(sens_headers, sensitivity, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> el óptimo balancea la reducción del daño con el costo de una obra mayor; cambia de 96 a 500 años en la sensibilidad factorial de D<sub>max</sub> y r. La cifra es normalizada y no representa un presupuesto monetario.</div>
      <h3>2.5.2 · POT/GPD y relación de Langbein</h3>
      <p>La serie horaria se declusterizó con separación mínima de seis horas secas. El umbral seleccionado genera alrededor de dos eventos por año válido; se ajustó GPD a los excesos con convención scipy c=+ξ y se transformó el retorno de evento a retorno AMS mediante Langbein.</p>
      {table(pot_headers, pot, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> POT utiliza varios eventos por año, mientras AMS retiene un máximo anual. Langbein hace comparables los retornos; las diferencias también reflejan el umbral y el ajuste GPD.</div>
      <h3>2.5.3 · Cambio climático y GEV no estacionaria</h3>
      <p>La curva IDF se escala con 7% por °C. La GEV evalúa μ(t)=μ<sub>0</sub>+μ<sub>1</sub>t en t<sub>final</sub>+25 años contra el umbral fijo i*=44.04 mm/h. La fila ΔT=0 recupera Q<sub>50</sub>=6.426 m³/s y D<sub>com</sub>=1500 mm.</p>
      {table(climate_headers, climate, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> el escalamiento climático reduce el retorno efectivo de la obra y eleva Q<sub>p</sub>. La GEV futura puede diferir de la curva IDF por la tendencia ajustada y la limitada muestra anual.</div>
      <h3>2.5.4 · Confiabilidad, resiliencia y vulnerabilidad</h3>
      <p>Hashimoto se calculó con caudal horario, Weiss=1.14 y capacidades a tubo lleno de Manning. α es la fracción de horas sin falla; γ es la tasa de recuperación por hora fallida; ν resume el exceso sobre capacidad.</p>
      {table(hash_headers, hash_summary, "compact")}<h4>Eventos históricos que superan la capacidad</h4>{table(event_headers, events, "compact")}
      <div class="interpretation"><strong>Interpretación hidrológica:</strong> el evento del 26-jul-1965 alcanza aproximadamente 7.226 m³/s y supera la capacidad de 1500 mm; 1800 mm no presenta superaciones en el registro horario. Las métricas están limitadas por la resolución horaria.</div>
      {bonus_widget_markup()}
    </section>'''


SECTION_BUILDERS = [section_21, section_22, section_23, section_24, section_25, section_26]

INTERACTIVE_JS = r'''<script>
(() => {
  "use strict";
  const dataNode = document.getElementById("hydro-data");
  const DATA = dataNode ? JSON.parse(dataNode.textContent) : {};
  const byId = id => document.getElementById(id);
  const num = value => Number(value);
  const fmt = (value, digits=2) => Number.isFinite(value) ? value.toLocaleString("es-CO", {maximumFractionDigits:digits, minimumFractionDigits:digits}) : "—";
  const tw = DATA.idf_params || {};
  const idfFormula = (durationMin, T) => {
    const a=num(tw.a), m=num(tw.m), b=num(tw.b_h), c=num(tw.c), d=durationMin/60;
    return a*Math.pow(T,m)/Math.pow(d+b,c);
  };
  const master = DATA.idf || [];
  const idfRow = (d,T) => master.find(r => Math.abs(num(r.duration_min)-d)<1e-6 && Math.abs(num(r.return_period_y)-T)<1e-6);

  // Navegación por pestañas o lectura continua.
  const sections = [...document.querySelectorAll("main section[id^='seccion-']")];
  let continuous = false;
  const showSection = id => {
    if (continuous) { document.getElementById(id)?.scrollIntoView({behavior:"smooth",block:"start"}); return; }
    sections.forEach(s => s.hidden = s.id !== id);
    document.querySelectorAll(".topnav [data-section]").forEach(b => b.setAttribute("aria-current", b.dataset.section===id ? "page" : "false"));
    window.scrollTo({top:0,behavior:"smooth"});
    window.setTimeout(()=>window.dispatchEvent(new Event("resize")),80);
  };
  document.querySelectorAll(".topnav [data-section]").forEach(b => b.addEventListener("click",()=>showSection(b.dataset.section)));
  const viewButton=byId("toggle-view");
  viewButton?.addEventListener("click",()=>{
    continuous=!continuous;
    sections.forEach(s=>s.hidden=!continuous && s.id!==document.querySelector(".topnav [aria-current='page']")?.dataset.section);
    viewButton.textContent=continuous?"Vista por pestañas":"Vista continua";
    if(continuous) window.scrollTo({top:0,behavior:"smooth"});
  });
  if(sections.length) showSection("seccion-25");

  // Descarga CSV desde cualquier tabla con su encabezado y filas visibles.
  document.querySelectorAll(".table-wrap table").forEach((table,index)=>{
    const button=document.createElement("button"); button.type="button"; button.className="download-csv"; button.textContent="Descargar tabla CSV";
    button.addEventListener("click",()=>{
      const rows=[...table.querySelectorAll("tr")].filter(r=>!r.hidden).map(row=>[...row.querySelectorAll("th,td")].map(c=>'"'+c.innerText.replaceAll('"','""')+'"').join(","));
      const blob=new Blob(["\ufeff"+rows.join("\r\n")],{type:"text/csv;charset=utf-8"});
      const link=document.createElement("a");link.href=URL.createObjectURL(blob);link.download=(table.id||`tabla-${index+1}`)+".csv";link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
    }); table.closest(".table-wrap").before(button);
  });
  document.querySelectorAll(".table-search").forEach(input=>input.addEventListener("input",()=>{
    const table=byId(input.dataset.table); if(!table)return; const q=input.value.toLocaleLowerCase();
    table.querySelectorAll("tbody tr").forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase().includes(q));
  }));
  // También identifica y equipa las tres tablas prioritarias si el HTML previo
  // se generó antes de que existieran los controles de filtro.
  const tableSpecs=[
    {id:"annual-maxima-filter",label:"Filtrar máximos anuales",match:h=>h.includes("hydro_year")&&h.some(x=>x.includes("intensity"))},
    {id:"lp3-quantiles-filter",label:"Filtrar cuantiles LP3/LMOM",match:h=>h.includes("distribution")&&h.includes("method")&&h.includes("return_period_y")},
    {id:"atlas14-comparison",label:"Filtrar NOAA Atlas 14",match:h=>h.includes("atlas14_intensity_mmh")},
  ];
  tableSpecs.forEach(spec=>{
    const table=[...document.querySelectorAll(".table-wrap table")].find(t=>spec.match([...t.querySelectorAll("thead th")].map(x=>x.textContent.trim().toLowerCase())));
    if(!table)return;table.id=spec.id;if(document.querySelector(`[data-table="${spec.id}"]`))return;
    const label=document.createElement("label");label.className="table-search-label";label.textContent=spec.label+" ";
    const input=document.createElement("input");input.className="table-search";input.type="search";input.dataset.table=spec.id;input.placeholder="Escriba para filtrar";label.append(input);table.closest(".table-wrap").before(label);
    input.addEventListener("input",()=>{const q=input.value.toLocaleLowerCase();table.querySelectorAll("tbody tr").forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase().includes(q));});
  });

  // Lightbox con zoom de rueda y botones, sin dependencias externas.
  const lightbox=byId("image-lightbox"), large=lightbox?.querySelector("img"); let zoom=1;
  const applyZoom=()=>{if(large)large.style.transform=`scale(${zoom})`;};
  document.querySelectorAll(".lightbox-trigger").forEach(item=>item.addEventListener("click",event=>{
    const button=event.currentTarget.closest(".lightbox-trigger");
    const img=button?.querySelector("img")||event.currentTarget;
    if(!lightbox||!large)return;large.src=button?.dataset.lightboxSrc||img.src;large.alt=img.alt;zoom=1;applyZoom();lightbox.showModal();
  }));
  document.querySelectorAll(".figure > img").forEach(img=>img.addEventListener("click",()=>{
    if(!lightbox||!large)return;large.src=img.src;large.alt=img.alt;zoom=1;applyZoom();lightbox.showModal();
  }));
  lightbox?.querySelector(".lightbox-close")?.addEventListener("click",()=>lightbox.close());
  lightbox?.querySelector(".zoom-in")?.addEventListener("click",()=>{zoom=Math.min(4,zoom+.25);applyZoom();});
  lightbox?.querySelector(".zoom-out")?.addEventListener("click",()=>{zoom=Math.max(.5,zoom-.25);applyZoom();});
  large?.addEventListener("wheel",e=>{e.preventDefault();zoom=Math.max(.5,Math.min(4,zoom+(e.deltaY<0?.15:-.15)));applyZoom();},{passive:false});
  lightbox?.addEventListener("click",e=>{if(e.target===lightbox)lightbox.close();});

  // Calculadora IDF/Racional: tabla maestra para intervalos e IC; NOAA cuando coincide.
  const updateIdf=()=>{
    const d=num(byId("idf-duration")?.value),T=num(byId("idf-return")?.value),A=num(byId("idf-area")?.value),C=num(byId("idf-coeff")?.value);
    const r=idfRow(d,T); if(!r||!(A>0)){byId("idf-output").textContent="No hay cuantil para esa combinación.";return;}
    const i=num(r.intensity_mmh),P=num(r.depth_mm),lo=num(r.ci95_low_mmh),hi=num(r.ci95_high_mmh),atlas=(DATA.atlas||[]).find(x=>Math.abs(num(x.duration_min)-d)<1e-6&&num(x.T_y)===T);
    const Q=.278*C*i*A;
    byId("idf-output").innerHTML=`<div class="metric-grid"><div><b>i(d,T)</b><strong>${fmt(i)} mm/h</strong></div><div><b>Lámina P</b><strong>${fmt(P)} mm</strong></div><div><b>IC95% de i</b><strong>${fmt(lo)}–${fmt(hi)} mm/h</strong></div><div><b>Qp racional</b><strong>${fmt(Q)} m³/s</strong></div><div><b>NOAA Atlas 14</b><strong>${atlas?fmt(num(atlas.atlas14_intensity_mmh))+" mm/h":"sin coincidencia oficial"}</strong></div></div>`;
  };
  ["idf-duration","idf-return","idf-area","idf-coeff"].forEach(id=>byId(id)?.addEventListener("input",updateIdf));updateIdf();

  // Explorador A: caudal, Manning, diámetro comercial, FS y retorno implícito.
  const pipeSizes=[600,750,900,1050,1200,1350,1500];
  const updateA=()=>{
    const tc=num(byId("a-tc")?.value),C=num(byId("a-c")?.value),T=num(byId("a-t")?.value);
    byId("a-tc-value").value=tc;byId("a-c-value").value=C.toFixed(3);
    const area=num(DATA.design?.area_km2)||1.0269,S=num(DATA.design?.slope_S0)||.00953,n=.013;
    const i=idfFormula(tc,T),Qp=.278*C*i*area,Dreq=Math.pow(n*Qp/(.312*Math.sqrt(S)),3/8)*1000;
    const Dcom=pipeSizes.find(d=>d>=Dreq)||pipeSizes.at(-1),Qc=.312/n*Math.pow(Dcom/1000,8/3)*Math.sqrt(S),FS=Qc/Qp;
    const critI=3.6*Qc/(C*area),Tcrit=Math.pow(critI*Math.pow(tc/60+num(tw.b_h),num(tw.c))/num(tw.a),1/num(tw.m));
    const p=Tcrit>1?Math.min(1,1/Tcrit):1,risk=1-Math.pow(1-p,25);
    byId("a-output").innerHTML=`<div class="metric-grid"><div><b>i(tc,T)</b><strong>${fmt(i)} mm/h</strong></div><div><b>Qp</b><strong>${fmt(Qp)} m³/s</strong></div><div><b>D requerido</b><strong>${fmt(Dreq,0)} mm</strong></div><div><b>Diámetro comercial</b><strong>${Dcom} mm</strong></div><div><b>FS = Qc/Qp</b><strong>${fmt(FS)}</strong></div><div><b>Riesgo 25 años aprox.</b><strong>${fmt(100*risk)}%</strong></div></div><p>Capacidad a tubo lleno Qc=${fmt(Qc)} m³/s; riesgo derivado de la curva IDF paramétrica como T de excedencia implícito.</p>`;
  };
  ["a-tc","a-c","a-t"].forEach(id=>byId(id)?.addEventListener("input",updateA));updateA();

  // Problema B: bloques alternos, método tiempo-área y tránsito RK4 en piscina nivelada.
  const intensity=(d,T)=>idfFormula(d,T), depth=(d,T)=>intensity(d,T)*d/60;
  const outlet=(h,Do)=>.61*Math.PI*Do*Do/4*Math.sqrt(2*9.81*Math.max(h-Do/2,0));
  const buildInput=kind=>{
    if(kind==="trap"){
      const tc=30,d=75,qpk=.278*.78*intensity(d,50)*(num(DATA.design?.area_km2)||1.0269),end=d+tc;
      return {end,at:t=>t<0||t>end?0:t<tc?qpk*t/tc:t<d?qpk:qpk*(end-t)/tc};
    }
    const duration=180,bins=duration/5,inc=[];
    for(let k=1;k<=bins;k++)inc.push(Math.max(0,depth(5*k,50)-depth(5*(k-1),50)));
    const sorted=[...inc].sort((a,b)=>b-a),rain=new Array(bins).fill(0);
    if(kind==="initial")rain.splice(0,bins,...sorted);
    else if(kind==="final")rain.splice(0,bins,...sorted.slice().reverse());
    else {let slots=[Math.floor(bins/2)];for(let j=1;slots.length<bins;j++){if(Math.floor(bins/2)+j<bins)slots.push(Math.floor(bins/2)+j);if(Math.floor(bins/2)-j>=0)slots.push(Math.floor(bins/2)-j);}slots.forEach((slot,j)=>rain[slot]=sorted[j]);}
    const rainI=rain.map(x=>x*12); // mm per 5 min -> mm/h
    const q=[]; for(let k=0;k<bins+6;k++){let sum=0;for(let j=Math.max(0,k-5);j<=Math.min(k,bins-1);j++)sum+=rainI[j]||0;q.push(.78*(num(DATA.design?.area_km2)||1.0269)/3.6*(sum/6));}
    return {end:(bins+6)*5,at:t=>{const k=Math.floor(t/5);return q[Math.max(0,Math.min(q.length-1,k))]||0;}};
  };
  let tankSeries=[];
  const routeTank=(kind,Do)=>{
    const storm=buildInput(kind),tankArea=18000,dt=60,steps=Math.ceil(storm.end)+40,series=[];let h=0;
    const dh=(t,x)=>(storm.at(t)-outlet(Math.max(0,x),Do))/tankArea;
    for(let k=0;k<=steps;k++){
      const t=k, Qin=storm.at(t),Qout=outlet(h,Do);series.push({t,Qin,Qout,h});
      const k1=dh(t,h),k2=dh(t+.5,h+30*k1),k3=dh(t+.5,h+30*k2),k4=dh(t+1,h+60*k3);
      h=Math.max(0,Math.min(3.5,h+60*(k1+2*k2+2*k3+k4)/6));
    }
    return series;
  };
  const drawTank=series=>{
    const canvas=byId("tank-canvas"),ctx=canvas.getContext("2d"),rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
    canvas.width=Math.max(500,rect.width*dpr);canvas.height=320*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
    const w=canvas.width/dpr,h=canvas.height/dpr,p={l:54,r:48,t:18,b:36},pw=w-p.l-p.r,ph=h-p.t-p.b;
    const maxQ=Math.max(8,...series.map(x=>Math.max(x.Qin,x.Qout))),maxH=Math.max(.5,...series.map(x=>x.h)),maxT=series.at(-1).t;
    ctx.clearRect(0,0,w,h);ctx.font="11px Segoe UI,Arial";ctx.strokeStyle="#dce5e9";ctx.fillStyle="#61727d";
    for(let j=0;j<=4;j++){let y=p.t+ph*j/4;ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();ctx.fillText(fmt(maxQ*(1-j/4),0),6,y+4);}
    const X=t=>p.l+pw*t/maxT,Y=q=>p.t+ph*(1-q/maxQ),Yh=x=>p.t+ph*(1-x/(maxH*1.15));
    const line=(field,color,dash=[],depthAxis=false)=>{ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=2;ctx.setLineDash(dash);series.forEach((v,i)=>{const x=X(v.t),y=depthAxis?Yh(v[field]):Y(v[field]);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.stroke();ctx.setLineDash([]);};
    line("Qin","#1676d2");line("Qout","#e27b25");line("h","#39865a",[5,4],true);
    ctx.strokeStyle="#b52b3b";ctx.setLineDash([6,4]);ctx.beginPath();ctx.moveTo(p.l,Y(6.426));ctx.lineTo(w-p.r,Y(6.426));ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle="#1676d2";ctx.fillText("I/Q entrada",p.l+6,p.t+12);ctx.fillStyle="#e27b25";ctx.fillText("O salida",p.l+94,p.t+12);ctx.fillStyle="#39865a";ctx.fillText("h (m)",w-p.r-44,p.t+12);ctx.fillStyle="#b52b3b";ctx.fillText("Qlim",w-p.r-42,Y(6.426)-5);
    ctx.fillStyle="#61727d";ctx.fillText("Tiempo (min)",w/2-32,h-8);canvas._chart={series,X,Y,Yh,p,pw,ph,maxQ,maxH,maxT};
  };
  const updateB=()=>{
    const kind=byId("b-scenario").value,Do=num(byId("b-do").value)/1000;byId("b-do-value").value=(Do*1000).toFixed(0);
    tankSeries=routeTank(kind,Do);const peakIn=Math.max(...tankSeries.map(x=>x.Qin)),peakOut=Math.max(...tankSeries.map(x=>x.Qout)),store=Math.max(...tankSeries.map(x=>x.h))*18000,head=Math.max(...tankSeries.map(x=>x.h));
    byId("b-metrics").innerHTML=`<div class="metric-grid"><div><b>I máx.</b><strong>${fmt(peakIn)} m³/s</strong></div><div><b>O máx.</b><strong>${fmt(peakOut)} m³/s</strong></div><div><b>Almacenamiento máx.</b><strong>${fmt(store,0)} m³</strong></div><div><b>Tirante máx.</b><strong>${fmt(head)} m</strong></div><div><b>Qlim</b><strong>6.426 m³/s</strong></div><div><b>Hmáx</b><strong>3.50 m</strong></div></div>`;
    drawTank(tankSeries);
  };
  ["b-scenario","b-do"].forEach(id=>byId(id)?.addEventListener("input",updateB));updateB();
  const canvas=byId("tank-canvas"),tooltip=byId("tank-tooltip");
  canvas?.addEventListener("mousemove",e=>{const chart=canvas._chart;if(!chart||!tankSeries.length)return;const rect=canvas.getBoundingClientRect(),x=(e.clientX-rect.left)*canvas.width/rect.width/(window.devicePixelRatio||1);const t=Math.max(0,Math.min(chart.maxT,(x-chart.p.l)/chart.pw*chart.maxT));const item=tankSeries[Math.round(t)];tooltip.hidden=false;tooltip.style.left=`${Math.min(rect.width-205,Math.max(8,e.clientX-rect.left+12))}px`;tooltip.style.top=`${Math.max(4,e.clientY-rect.top-55)}px`;tooltip.innerHTML=`t=${item.t} min<br>I=${fmt(item.Qin)} · O=${fmt(item.Qout)} m³/s<br>h=${fmt(item.h)} m`;});
  canvas?.addEventListener("mouseleave",()=>tooltip.hidden=true);
  window.addEventListener("resize",()=>{if(tankSeries.length)drawTank(tankSeries);});
})();
</script>'''

BONUS_INTERACTIVE_JS = r'''<script>
(() => {
  const byId = id => document.getElementById(id);
  const dataNode = byId("hydro-data");
  if (!dataNode || !byId("bonus-widget")) return;
  const data = JSON.parse(dataNode.textContent);
  const rows = (data.bonus && data.bonus.cost || []).map(r => ({
    T: Number(r.T_d_y), obra: Number(r.Cobra_C0_units), dae: Number(r.DAE_C0_per_year),
    dmaxBase: Number(r.Dmax_C0_units)
  })).filter(r => Number.isFinite(r.T) && Number.isFinite(r.obra) && Number.isFinite(r.dae));
  const dmax = byId("bonus-dmax"), rate = byId("bonus-rate"), delta = byId("bonus-dt");
  const fmt = (x,n=2) => Number.isFinite(x) ? x.toLocaleString("es-CO",{maximumFractionDigits:n,minimumFractionDigits:n}) : "—";
  const frc = r => r*Math.pow(1+r,25)/(Math.pow(1+r,25)-1);
  const update = () => {
    const dm=Number(dmax.value), r=Number(rate.value)/100, dt=Number(delta.value), fr=frc(r), f0=frc(.06);
    let optimum=null;
    rows.forEach(row=>{
      const annual=row.obra*fr;
      const damage=row.dae*(dm/row.dmaxBase);
      const total=annual+damage;
      if(!optimum||total<optimum.total)optimum={T:row.T,annual,damage,total};
    });
    const factor=1+.07*dt, intensity=40.96*factor, q=6.426112*factor;
    const m=Number((data.idf_params||{}).m)||.32660717;
    const teff=62.418/(factor**(1/m));
    byId("bonus-dmax-label").textContent=fmt(dm,0)+" C₀";
    byId("bonus-rate-label").textContent=fmt(r*100,0)+"%";
    byId("bonus-dt-label").textContent=fmt(dt,1)+" °C";
    byId("bonus-output").innerHTML=`<div class="metric-grid">
      <div><b>T óptimo simulado</b><strong>${fmt(optimum?.T,0)} años</strong></div>
      <div><b>Costo anualizado</b><strong>${fmt(optimum?.annual)} C₀/año</strong></div>
      <div><b>DAE</b><strong>${fmt(optimum?.damage)} C₀/año</strong></div>
      <div><b>CTAE mínimo</b><strong>${fmt(optimum?.total)} C₀/año</strong></div>
      <div><b>i(tc,T=50) escalada</b><strong>${fmt(intensity)} mm/h</strong></div>
      <div><b>Qp resultante</b><strong>${fmt(q)} m³/s</strong></div>
      <div><b>T efectivo IDF</b><strong>${fmt(teff)} años</strong></div>
    </div>`;
  };
  [dmax,rate,delta].forEach(el=>el.addEventListener("input",update));
  update();
})();
</script>'''


def main():
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    write_bonus_markdown()
    EMBEDDED_IMAGE_NAMES.clear()
    sections = "\n".join(builder() for builder in SECTION_BUILDERS)
    # Se incluyen automáticamente también PNG nuevos aún no referenciados por
    # una sección, para que el reporte no dependa de archivos locales al abrirlo.
    loose_images = []
    for image_path in sorted(PRODUCTS.glob("*.png")):
        if image_path.name not in EMBEDDED_IMAGE_NAMES:
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            loose_images.append(f'<img alt="Recurso embebido: {cell(image_path.name)}" src="data:image/png;base64,{encoded}">')
            EMBEDDED_IMAGE_NAMES.add(image_path.name)
    image_library = '<div class="image-library" hidden aria-hidden="true">' + "".join(loose_images) + "</div>"
    navigation_items = [
        ("Resumen Ejecutivo", "seccion-25"), ("2.1 Datos y Calidad", "seccion-21"),
        ("2.2 Extremos e Incertidumbre", "seccion-22"),
        ("2.3 Curvas IDF y NOAA", "seccion-23"),
        ("2.4 Diseño Hidrológico: DEM, Prob. A y Prob. B", "seccion-24"),
        ("2.5 Bonificaciones", "seccion-26"),
    ]
    navigation = "".join(f'<button type="button" data-section="{section_id}">{escape(label)}</button>'
                         for label, section_id in navigation_items)
    html = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hidrología · Punto 2</title><style>
    :root{{--ink:#172b3a;--muted:#5c6f7e;--line:#dce5e9;--paper:#f3f7f7;--teal:#087e78;--green:#16836b;--amber:#d99a38}}
    .topnav{{position:sticky;top:0;z-index:1000;display:flex;align-items:center;gap:7px;overflow-x:auto;padding:9px max(16px,calc((100vw - 1180px)/2));background:#0d2935;color:#fff;box-shadow:0 3px 14px #0c243333;white-space:nowrap}}.topnav button{{border:1px solid #64808b;border-radius:999px;padding:8px 13px;color:#eaf3f5;background:transparent;font-family:inherit;font-size:12px;font-weight:600;line-height:1.2;cursor:pointer}}.topnav button:hover,.topnav button[aria-current="page"]{{background:#e4f4f0;color:#123a43;border-color:#e4f4f0}}.topnav .view-toggle{{margin-left:auto;background:#087e78;border-color:#087e78;color:#fff}}section[hidden]{{display:none!important}}
    *{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.58 Inter,Segoe UI,Arial,sans-serif}}
    header{{padding:42px max(24px,calc((100vw - 1100px)/2));background:#102e3b;color:white}}header .kicker{{color:#9bd6ce;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:700}}header h1{{font-size:clamp(28px,4vw,42px);line-height:1.1;margin:9px 0}}header p{{margin:0;color:#c2d2d8}}
    main{{max-width:1100px;margin:30px auto;padding:0 22px}}section{{background:white;border:1px solid var(--line);border-radius:16px;padding:clamp(20px,4vw,42px);box-shadow:0 10px 35px #102e3b0a;margin-bottom:24px}}
    h2{{font-size:30px;line-height:1.2;margin:4px 0 22px}}h3{{font-size:19px;margin:30px 0 8px}}.eyebrow{{color:var(--teal);font-size:12px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}.lede{{color:var(--muted);max-width:900px;margin:0 0 14px}}
    .site-card{{display:flex;gap:18px;padding:19px;background:#eff8f6;border:1px solid #d3e9e3;border-radius:12px}}.site-card h3{{margin:0 0 5px}}.site-card p{{margin:3px 0;color:#496270}}.site-mark{{width:58px;height:58px;flex:0 0 58px;border-radius:14px;background:#d5eee7;color:#09655e;display:grid;place-items:center;font-weight:800;letter-spacing:.06em}}
    .chart{{border:1px solid var(--line);border-radius:12px;padding:10px 12px 2px;overflow:hidden}}svg{{display:block;width:100%;height:auto}}.grid{{stroke:#e8eef0;stroke-width:1}}.axis{{fill:#72838d;font-size:11px}}.axis-line{{stroke:#adbbc1;stroke-width:1}}.threshold{{stroke:#71828a;stroke-dasharray:5 5;stroke-width:1.2}}
    .legend{{display:flex;gap:22px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:13px;margin:10px 2px}}.legend span{{display:flex;align-items:center;gap:7px}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px}}.green{{background:var(--green)}}.amber{{background:var(--amber)}}.note{{margin-left:auto}}
    .table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:10px;margin:12px 0 20px}}table{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}th{{background:#edf4f4;color:#31505c;text-align:left;font-weight:700}}td,th{{padding:10px 12px;border-bottom:1px solid #e8eef0}}tbody tr:nth-child(even){{background:#fafcfc}}tbody tr:last-child td{{border-bottom:0}}.empty{{color:var(--muted);font-style:italic}}
    .callout{{padding:17px 19px;background:#fff8ec;border-left:4px solid var(--amber);border-radius:5px;color:#514531;margin-top:26px}}.technical-note{{padding:12px 15px;background:#f1f6fa;border-left:3px solid #648aa0;border-radius:4px;color:#3f5664;margin:14px 0;font-size:14px}}.interpretation{{padding:16px 19px;background:#eaf6f3;border:1px solid #c8e5da;border-left:5px solid #16836b;border-radius:8px;color:#244b43;margin:16px 0 24px}}footer{{display:flex;justify-content:center;gap:18px;flex-wrap:wrap;text-align:center;color:#788993;padding:8px 20px 32px;font-size:12px}}
    .fig-grid{{display:grid;grid-template-columns:1fr;width:100%;gap:22px;margin:24px 0}}.figure{{width:100%;min-width:0;margin:0;border:1px solid var(--line);border-radius:12px;padding:16px;background:#fbfdfd;break-inside:avoid;page-break-inside:avoid}}.figure img{{display:block;width:100%;max-height:510px;height:auto;object-fit:contain;margin:0 auto}}.lightbox-trigger{{display:block;width:100%;border:0;padding:0;background:transparent;cursor:zoom-in}}.lightbox-trigger:focus-visible{{outline:3px solid var(--teal);outline-offset:3px}}#image-lightbox{{width:min(96vw,1500px);max-width:96vw;max-height:96vh;border:0;border-radius:12px;padding:44px 12px 12px;background:#10202a}}#image-lightbox::backdrop{{background:#06131ddd}}#image-lightbox img{{display:block;max-width:100%;max-height:calc(96vh - 60px);margin:auto;object-fit:contain}}.lightbox-tools{{position:absolute;right:10px;top:8px;display:flex;gap:6px}}.lightbox-tools button{{border:0;border-radius:6px;padding:6px 10px;background:#fff;color:#172b3a;cursor:pointer}}.lightbox-close{{position:static;border:0;border-radius:6px;padding:7px 12px;background:#fff;color:#172b3a;cursor:pointer}}.table-search-label{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:14px 0 6px}}.table-search{{min-width:min(320px,100%);padding:8px 10px;border:1px solid var(--line);border-radius:6px;font:inherit}}figcaption{{font-size:13px;color:var(--muted);padding:12px 3px 2px}}.figure h3{{margin:0}}.exact-values{{font-variant-numeric:tabular-nums;font-size:11px;white-space:normal;overflow-wrap:anywhere}}.exact-values td,.exact-values th{{padding:6px 7px}}
    .source-note{{font-size:12px;color:var(--muted);margin-top:18px}}.recommendations{{padding-left:22px;color:#405867}}.recommendations li{{margin:.55em 0}}
    .widget{{border:1px solid #cbdfe0;border-radius:13px;padding:20px;margin:22px 0 28px;background:linear-gradient(135deg,#f4faf9,#f8fbff)}}.widget h3{{margin:0 0 14px}}.controls{{display:flex;align-items:end;gap:16px;flex-wrap:wrap}}.controls label{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;color:#38515c;font-weight:600}}.controls input[type=number],.controls select{{padding:8px 10px;border:1px solid #b8cbd0;border-radius:7px;font:inherit;background:white;color:var(--ink)}}.controls input[type=range]{{accent-color:#087e78;min-width:150px}}.sliders label{{display:grid;gap:5px;min-width:220px}}.widget-output{{margin-top:16px;color:#3c535e}}.metric-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}.metric-grid>div{{padding:12px;background:#fff;border:1px solid #dce8e9;border-radius:9px;display:grid;gap:5px}}.metric-grid b{{font-size:12px;color:#60717b}}.metric-grid strong{{font-size:17px;color:#153c49;font-variant-numeric:tabular-nums}}.download-csv{{margin:0 0 6px;padding:6px 10px;border:1px solid #9cb8be;border-radius:6px;background:#f4faf9;color:#24505a;font-family:inherit;font-size:12px;font-weight:600;cursor:pointer}}.canvas-wrap{{position:relative;width:100%;margin-top:14px}}#tank-canvas{{display:block;width:100%;height:320px;background:#fff;border:1px solid #dce5e9;border-radius:9px}}.chart-tooltip{{position:absolute;pointer-events:none;padding:8px 10px;border-radius:7px;background:#102e3b;color:white;font-size:12px;box-shadow:0 4px 14px #0003;z-index:5}}
    @media(max-width:640px){{header{{padding:30px 22px}}section{{padding:20px 15px}}.note{{margin-left:0}}.site-card{{gap:12px}}.topnav{{padding:8px}}.topnav .view-toggle{{margin-left:0}}.controls label{{width:100%}}}}
    @media print{{
      @page{{size:A4 landscape;margin:8mm}}
      body{{background:#fff;font-size:8pt}}
      .topnav,.widget,.download-csv{{display:none!important}}
      section[hidden]{{display:block!important}}
      header{{padding:8mm 10mm;background:#fff;color:#172b3a;border-bottom:1px solid #9aabb3}}
      header p{{color:#496270}}
      main{{max-width:none;margin:0;padding:0}}
      section{{box-shadow:none;border:0;border-radius:0;margin:0;padding:5mm 2mm;break-inside:auto}}
      h2{{font-size:16pt;margin:2mm 0 4mm}}h3{{font-size:11pt;margin:4mm 0 2mm}}h4{{font-size:9pt;margin:3mm 0 1mm}}
      .table-wrap{{overflow:visible!important;border:0;margin:2mm 0 4mm;break-inside:avoid}}
      table{{width:100%;font-size:7pt;table-layout:auto;overflow-x:visible;white-space:normal}}
      td,th{{padding:2pt 3pt;overflow-wrap:anywhere}}
      thead{{display:table-header-group}}tr{{break-inside:avoid}}
      .fig-grid{{display:grid;grid-template-columns:1fr;width:100%;gap:6mm;margin:5mm 0}}
      .figure{{width:100%;break-inside:avoid;page-break-inside:avoid;padding:3mm;margin:0}}
      .figure img{{width:100%;max-height:175mm;height:auto;object-fit:contain}}
      .lightbox-trigger{{display:block;width:100%;border:0;padding:0;background:transparent}}
      #image-lightbox{{display:none}}
      .table-search-label{{display:none}}
      .exact-values{{font-size:6.5pt;white-space:normal;overflow-wrap:anywhere}}
      footer{{padding:4mm;font-size:7pt}}
    }}
    </style></head><body><nav class="topnav" aria-label="Navegación del reporte">{navigation}<button id="toggle-view" class="view-toggle" type="button">Vista continua</button></nav>
    <header><div class="kicker">Hidrología · Punto 2</div><h1>Caracterización de precipitación</h1><p>Denver Stapleton · GHCNh · Control de calidad y datos subdiarios</p></header>
    <main>{sections}{image_library}</main><footer><span>Reporte autocontenido · archivos e imágenes embebidos</span><span>script 00_generar_html.py</span></footer>
    {widget_data_script()}
    <dialog id="image-lightbox" aria-label="Figura ampliada"><div class="lightbox-tools"><button class="zoom-out" type="button" aria-label="Reducir">−</button><button class="zoom-in" type="button" aria-label="Ampliar">+</button><button class="lightbox-close" type="button" aria-label="Cerrar">Cerrar</button></div><img alt="Figura ampliada"></dialog>
    {INTERACTIVE_JS}{BONUS_INTERACTIVE_JS}</body></html>'''
    html = repair_mojibake(html)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Reporte HTML creado: {OUTPUT}")


if __name__ == "__main__":
    main()
