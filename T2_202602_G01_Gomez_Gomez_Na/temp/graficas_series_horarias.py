"""Documento de trabajo (temporal): series mensuales de ETo y series horarias de ERA5-Land, en un HTML con zoom.

Arriba, dos gráficas mensuales de la cuenca:
  - ETo de Penman–Monteith FAO-56 (productos/punto1/eto_mensual_cuenca.csv, de codigo/punto1/04_eto_fao56.py)
    contra la ETP de Hargreaves de la Tarea 1 (../Analisis_De_Cuenca/out/etp_hargreaves_fonce.csv, columna
    etp_era5land, diaria, sumada aquí por mes).
  - La ETo separada en su término radiativo y su término aerodinámico (suman la ETo).
Debajo, las series horarias de las 6 variables descargadas.

Lee datos/punto1/era5land_puntos/punto_N.csv (salida de codigo/punto1/01_descarga_era5land_puntos.py) y escribe
temp/series_horarias_era5land.html: una gráfica Plotly por variable, con los 6 puntos, a la que se le puede hacer
zoom (arrastrar un recuadro, rueda del ratón, doble clic para volver).

Hora local de Colombia = valid_time (UTC) − 5 h (decisión del 2026-11-12, temp/decisiones.md).
Conversiones solo de unidades, para leer mejor: K → °C, Pa → kPa, ssrd J/m² en la hora → W/m² promedio de la hora
(÷ 3600). u10 y v10 se muestran tal cual (m/s).

Al final, la fase 3 (pruebas de la referencia): Rs de Angstrom con el brillo solar de 3 estaciones del IDEAM frente
a la ssrd de ERA5-Land, y ETo FAO-56 de estación frente a la de ERA5-Land, con sus dos variantes de viento. Lee las
salidas de codigo/punto1/12_rs_brillo_solar_vs_era5land.py y 13_eto_estaciones_vs_era5land.py; no calcula nada nuevo.

Escribe también temp/documento_trabajo_ligero.html: lo mismo sin las series horarias (pesa menos de 1 MB), para
abrirlo con un enlace.

Las 219 144 horas × 6 puntos × 6 variables se guardan dentro del HTML como Float32 en base64, y el eje de tiempo
se reconstruye en el navegador a partir de la primera hora (las series son horarias y sin huecos; se verifica).
Por eso el archivo pesa unos 40 MB. Va en temp/, que se borra antes de armar el ZIP de la entrega.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python temp/graficas_series_horarias.py
"""

import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[1]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"
SALIDA = RAIZ_ENTREGA / "temp" / "series_horarias_era5land.html"
SALIDA_LIGERA = RAIZ_ENTREGA / "temp" / "documento_trabajo_ligero.html"
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
NOMBRES_ESTACION = {"24025040": "Mogotes (1 673 m)", "24025030": "La Sierra (2 850 m)", "24025050": "Charalá (1 350 m)"}
ETO_CUENCA = RAIZ_ENTREGA / "productos" / "punto1" / "eto_mensual_cuenca.csv"
# La ETP de Hargreaves de la Tarea 1 (fuera de la carpeta de la entrega): solo para comparar en este documento.
HARGREAVES_TAREA1 = RAIZ_ENTREGA.parent / "Analisis_De_Cuenca" / "out" / "etp_hargreaves_fonce.csv"

DESFASE_HORA_LOCAL = pd.Timedelta(hours=-5)  # Colombia, UTC−5, sin horario de verano
PUNTOS = [1, 2, 3, 4, 5, 6]

# columna del CSV -> (nombre en la gráfica, unidades, función de conversión)
VARIABLES = {
    "t2m": ("Temperatura a 2 m · t2m", "°C", lambda x: x - 273.15),
    "d2m": ("Punto de rocío a 2 m · d2m", "°C", lambda x: x - 273.15),
    "sp": ("Presión en superficie · sp", "kPa", lambda x: x / 1000.0),
    "u10": ("Viento a 10 m hacia el este · u10", "m/s", lambda x: x),
    "v10": ("Viento a 10 m hacia el norte · v10", "m/s", lambda x: x),
    "ssrd": ("Radiación solar entrante · ssrd", "W/m²", lambda x: x / 3600.0),
}


def a_base64(valores):
    """Serie numérica -> texto base64 de sus bytes Float32 (little-endian)."""
    return base64.b64encode(np.asarray(valores, dtype="<f4").tobytes()).decode("ascii")


def leer_punto(n):
    """Lee la serie de un punto, ordenada por hora, y comprueba que sea horaria y sin huecos."""
    datos = pd.read_csv(CARPETA_DATOS / f"punto_{n}.csv", parse_dates=["valid_time"])
    datos = datos.sort_values("valid_time").reset_index(drop=True)
    pasos = datos["valid_time"].diff().dropna().unique()
    assert len(pasos) == 1 and pasos[0] == np.timedelta64(1, "h"), f"punto {n}: la serie no es horaria continua"
    return datos


def series_mensuales_eto():
    """ETo mensual de la cuenca con sus términos, y la ETP de Hargreaves mensual (mm/mes), mes a mes."""
    eto = pd.read_csv(ETO_CUENCA)
    hargreaves = pd.read_csv(HARGREAVES_TAREA1, parse_dates=["fecha"])
    hargreaves = hargreaves.set_index("fecha")["etp_era5land"].resample("MS").agg(["sum", "count"])
    hargreaves.index = hargreaves.index.strftime("%Y-%m")
    assert (hargreaves["count"] == hargreaves.index.map(lambda m: pd.Period(m).days_in_month)).all()
    juntas = eto.set_index("mes").join(hargreaves["sum"].rename("hargreaves_mm_mes"), how="left")
    assert juntas["hargreaves_mm_mes"].notna().all(), "faltan meses de Hargreaves"
    return {
        "meses": list(juntas.index),
        "eto": juntas["eto_mm_mes"].round(2).tolist(),
        "radiativa": juntas["eto_radiativa_mm_mes"].round(2).tolist(),
        "aerodinamica": juntas["eto_aerodinamica_mm_mes"].round(2).tolist(),
        "hargreaves": juntas["hargreaves_mm_mes"].round(2).tolist(),
    }


def datos_fase3():
    """Salidas de los scripts 12 y 13: ciclo anual, sesgo por mes, series diarias y resumen, por estación."""
    rs_mes = pd.read_csv(CARPETA_PRODUCTOS / "rs_estaciones_vs_era5land_por_mes.csv", dtype={"estacion": str})
    rs_res = pd.read_csv(CARPETA_PRODUCTOS / "rs_estaciones_vs_era5land_resumen.csv", dtype={"estacion": str})
    rs_dia = pd.read_csv(CARPETA_PRODUCTOS / "rs_estaciones_diaria.csv", dtype={"estacion": str})
    eto_mes = pd.read_csv(CARPETA_PRODUCTOS / "eto_estaciones_vs_era5land_por_mes.csv", dtype={"estacion": str})
    eto_res = pd.read_csv(CARPETA_PRODUCTOS / "eto_estaciones_vs_era5land_resumen.csv", dtype={"estacion": str})
    eto_dia = pd.read_csv(CARPETA_PRODUCTOS / "eto_estaciones_diaria.csv", dtype={"estacion": str})
    estaciones = []
    for codigo, nombre in NOMBRES_ESTACION.items():
        r = rs_mes[rs_mes["estacion"] == codigo].sort_values("mes")
        rr = rs_res[rs_res["estacion"] == codigo].iloc[0]
        e = {v: eto_mes[(eto_mes["estacion"] == codigo) & (eto_mes["variante_viento"] == v)].sort_values("mes")
             for v in ["mogotes_aut", "2ms"]}
        er = eto_res[eto_res["estacion"] == codigo].set_index("variante_viento")
        # Días sin dato como vacíos (null en el JSON), para que la línea se corte en los huecos y no los una.
        todos = pd.date_range("1998-01-01", "2022-12-31", freq="D").strftime("%Y-%m-%d")
        rd = rs_dia[rs_dia["estacion"] == codigo].set_index("fecha").reindex(todos).rename_axis("fecha").reset_index()
        ed = eto_dia[eto_dia["estacion"] == codigo].set_index("fecha").reindex(todos).rename_axis("fecha").reset_index()
        rd = rd.astype(object).where(rd.notna(), None)
        ed = ed.astype(object).where(ed.notna(), None)
        estaciones.append({
            "codigo": codigo, "nombre": nombre, "punto": int(rr["punto_era5"]),
            "distancia_km": float(rr["distancia_km"]), "dz_celda_m": float(rr["estacion_menos_celda_dem_m"]),
            "rs": {"estacion": r["rs_estacion_media"].round(2).tolist(), "era5": r["rs_era5_media"].round(2).tolist(),
                   "sesgo": r["sesgo_MJm2"].round(2).tolist(),
                   "sesgo_total": round(float(rr["sesgo_MJm2"]), 2), "sesgo_pct": round(float(rr["sesgo_pct"]), 1),
                   "rmse": round(float(rr["rmse_MJm2"]), 2), "dias": int(rr["dias"])},
            "eto": {"a": e["mogotes_aut"]["eto_estacion_media_mm_dia"].round(3).tolist(),
                    "b": e["2ms"]["eto_estacion_media_mm_dia"].round(3).tolist(),
                    "era5": e["mogotes_aut"]["eto_era5_media_mm_dia"].round(3).tolist(),
                    "sesgo_a": e["mogotes_aut"]["sesgo_mm_dia"].round(3).tolist(),
                    "sesgo_b": e["2ms"]["sesgo_mm_dia"].round(3).tolist(),
                    "resumen": {v: {"sesgo": round(float(er.loc[v, "sesgo_mm_dia"]), 2),
                                    "pct": round(float(er.loc[v, "sesgo_pct"]), 1),
                                    "rmse": round(float(er.loc[v, "rmse_mm_dia"]), 2), "dias": int(er.loc[v, "dias"])}
                                for v in ["mogotes_aut", "2ms"]}},
            "diaria_rs": {"fecha": rd["fecha"].tolist(), "estacion": [None if v is None else round(float(v), 2) for v in rd["rs_estacion_MJm2"]],
                          "era5": [None if v is None else round(float(v), 2) for v in rd["rs_era5_MJm2"]]},
            "diaria_eto": {"fecha": ed["fecha"].tolist(), "a": [None if v is None else round(float(v), 2) for v in ed["eto_mogotes_aut_mm"]],
                           "b": [None if v is None else round(float(v), 2) for v in ed["eto_2ms_mm"]], "era5": [None if v is None else round(float(v), 2) for v in ed["eto_era5_mm"]]},
        })
    return estaciones


def main():
    mensual = series_mensuales_eto()
    series = {n: leer_punto(n) for n in PUNTOS}

    # Todas las series deben empezar a la misma hora y tener el mismo largo, para compartir el eje de tiempo.
    inicio_utc = series[PUNTOS[0]]["valid_time"].iloc[0]
    largo = len(series[PUNTOS[0]])
    for n, datos in series.items():
        assert datos["valid_time"].iloc[0] == inicio_utc and len(datos) == largo, f"punto {n}: otro eje de tiempo"
    inicio_local = inicio_utc + DESFASE_HORA_LOCAL

    carga = {
        "inicio_local": inicio_local.strftime("%Y-%m-%dT%H:%M:%S"),
        "horas": largo,
        "mensual": mensual,
        "fase3": datos_fase3(),
        "puntos": PUNTOS,
        "variables": [
            {
                "columna": col,
                "titulo": titulo,
                "unidades": unidades,
                "series": {str(n): a_base64(convertir(series[n][col].to_numpy(dtype=float))) for n in PUNTOS},
            }
            for col, (titulo, unidades, convertir) in VARIABLES.items()
        ],
    }

    # Cifras del encabezado, calculadas de las series mensuales de la cuenca (25 años completos).
    anios = len(mensual["meses"]) / 12
    carga["cifras"] = [
        [f"{sum(mensual['eto']) / anios:,.0f}".replace(",", " ") + " mm/año", "ETo Penman–Monteith, cuenca"],
        [f"{sum(mensual['hargreaves']) / anios:,.0f}".replace(",", " ") + " mm/año", "ETP Hargreaves (Tarea 1), cuenca"],
        [f"{100 * sum(mensual['aerodinamica']) / sum(mensual['eto']):.1f} %", "de la ETo sale del término aerodinámico"],
        [f"{largo:,}".replace(",", " ") + " h", "horas por punto, 6 puntos"],
    ]
    html = PLANTILLA.replace("__CARGA__", json.dumps(carga, ensure_ascii=False))
    SALIDA.write_text(html, encoding="utf-8")
    print(f"Listo: {SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB), {largo} horas por punto")

    # Versión ligera: sin las series horarias.
    carga["variables"] = []
    carga["horas"] = 0
    carga["cifras"] = carga["cifras"][:3]
    SALIDA_LIGERA.write_text(PLANTILLA.replace("__CARGA__", json.dumps(carga, ensure_ascii=False)), encoding="utf-8")
    print(f"Listo: {SALIDA_LIGERA} ({SALIDA_LIGERA.stat().st_size / 1e6:.1f} MB)")


PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Documento de trabajo ETo</title>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Mismo estilo que el informe de la Tarea 1 (Analisis_De_Cuenca/scripts/18b_reporte_html.py). */
:root {
  --fondo: #F5F7F6; --superficie: #FFFFFF; --tinta: #17211E; --tenue: #56645F; --linea: #D5DDDA;
  --acento: #1B6A80; --acento-suave: #E2EFF2;
  --f-titulo: "Archivo", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --f-texto: "Source Serif 4", Georgia, "Times New Roman", serif;
  --f-dato: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
    --acento: #72B9CE; --acento-suave: #1C2D32;
  }
}
:root[data-theme="dark"] {
  --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
  --acento: #72B9CE; --acento-suave: #1C2D32;
}
* { box-sizing: border-box; }
body { background: var(--fondo); color: var(--tinta); font: 400 17px/1.6 var(--f-texto); margin: 0; }
.envoltura { max-width: 1240px; margin: 0 auto; padding-inline: 20px; padding-block: 48px 72px; }
header { border-bottom: 1px solid var(--linea); padding-bottom: 28px; margin-bottom: 40px; }
.antetitulo { font: 600 12px/1 var(--f-dato); letter-spacing: .12em; text-transform: uppercase; color: var(--acento); margin: 0 0 14px; }
h1 { font: 800 clamp(32px, 5vw, 50px)/1.05 var(--f-titulo); font-stretch: 82%; letter-spacing: -.01em; margin: 0 0 16px; text-wrap: balance; }
h2 { font: 800 34px/1.15 var(--f-titulo); font-stretch: 88%; margin: 0 0 16px; text-wrap: balance;
     color: var(--acento); border-left: 6px solid var(--acento); padding-left: 14px; }
h3 { font: 600 13px/1.3 var(--f-dato); letter-spacing: .08em; text-transform: uppercase; color: var(--tenue); margin: 0 0 6px; }
p { margin: 0 0 14px; max-width: 66ch; }
.intro { font-size: 19px; color: var(--tenue); max-width: 64ch; margin: 0; }
.cifras { display: flex; flex-wrap: wrap; gap: 12px 36px; margin-top: 24px; }
.cifra { display: flex; flex-direction: column; gap: 2px; }
.cifra b { font: 500 24px/1.1 var(--f-dato); font-variant-numeric: tabular-nums; }
.cifra span { font: 400 12px/1.3 var(--f-dato); color: var(--tenue); letter-spacing: .04em; }
section { margin-bottom: 64px; }
.nota { font-size: 14px; color: var(--tenue); }
.tarjeta { background: var(--superficie); border: 1px solid var(--linea); border-radius: 6px; padding: 14px 12px 4px; }
.dos { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 12px; }
.rejilla { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 12px; }
.grafico { width: 100%; height: 380px; }
.rejilla .grafico { height: 300px; }
.controles { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 14px; }
.controles button { font: 500 13px/1 var(--f-dato); color: var(--tenue); background: var(--superficie); border: 1px solid var(--linea);
  border-radius: 6px; padding: 8px 12px; cursor: pointer; }
.controles button:hover { color: var(--tinta); }
.controles button[aria-pressed="true"] { color: var(--acento); border-color: var(--acento); background: var(--acento-suave); font-weight: 600; }
.tabla { overflow-x: auto; margin: 8px 0 4px; }
.tabla table { border-collapse: collapse; font: 400 13px/1.4 var(--f-dato); font-variant-numeric: tabular-nums; }
.tabla th, .tabla td { padding: 6px 12px; border-bottom: 1px solid var(--linea); text-align: right; white-space: nowrap; }
.tabla th:first-child, .tabla td:first-child { text-align: left; }
.tabla th { color: var(--tenue); font-weight: 500; }
footer { border-top: 1px solid var(--linea); padding-top: 24px; font-size: 14px; color: var(--tenue); }
code { font: 400 .86em var(--f-dato); }
@media (max-width: 1000px) { .rejilla { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 760px) { .dos, .rejilla { grid-template-columns: 1fr; } body { font-size: 16px; } }
</style>
</head>
<body>
<div class="envoltura">
<header>
  <p class="antetitulo">Tarea 2 · Punto 1 · Documento de trabajo (temporal)</p>
  <h1>Evapotranspiración de referencia en la cuenca del Fonce</h1>
  <p class="intro">ERA5-Land en 6 puntos de la cuenca, 1998–2022, en hora local (UTC−5). La cuenca es el promedio
  de los puntos ponderado por el área de su región de Voronoi.</p>
  <div class="cifras" id="cifras"></div>
</header>

<section>
  <h2>ETo mensual</h2>
  <p>Arrastra un recuadro o usa la rueda del ratón para hacer zoom; doble clic vuelve a la vista completa.</p>
  <div class="dos">
    <div class="tarjeta"><h3>Penman–Monteith contra Hargreaves</h3><div class="grafico" id="g-comparacion"></div></div>
    <div class="tarjeta"><h3>ETo por términos (apilados, suman la ETo)</h3><div class="grafico" id="g-terminos"></div></div>
  </div>
</section>

<section id="s-horarias">
  <h2>Series horarias de las 6 variables</h2>
  <p>El zoom en el tiempo se sincroniza en las 6 gráficas. Clic en un punto de la leyenda lo oculta o lo muestra en todas.</p>
  <div class="controles" id="ventanas"></div>
  <div class="rejilla" id="rejilla"></div>
</section>

<section>
  <h2>Fase 3 · Radiación de estaciones frente a ERA5-Land</h2>
  <p>Rs de estación con Angstrom (FAO-56 ec. 35, a<sub>s</sub> = 0.25, b<sub>s</sub> = 0.50) a partir del brillo solar
  diario del IDEAM. Cada estación se compara con el punto de ERA5-Land más cercano, en los mismos días. Sesgo =
  ERA5-Land − estación.</p>
  <div class="tabla" id="t-rs"></div>
  <div class="rejilla" id="r-rs"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Sesgo de Rs por mes (ERA5-Land − estación)</h3><div class="grafico" id="g-rs-sesgo"></div></div>
</section>

<section>
  <h2>Fase 3 · ETo de estación frente a ERA5-Land</h2>
  <p>ETo FAO-56 con Tmáx, Tmín y HR de estación, la Rs de Angstrom y la presión por altura. Viento: (a), la
  variante final, es la media mensual de Mogotes-AUT medida a 10 m (altura de los anemómetros del IDEAM, Manual del
  Observador Meteorológico) y llevada a 2 m con la ec. 47; (b), u2 = 2 m/s, queda como sensibilidad. Solo días con todas
  las entradas.</p>
  <div class="tabla" id="t-eto"></div>
  <div class="rejilla" id="r-eto"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Sesgo de ETo por mes (ERA5-Land − estación)</h3><div class="grafico" id="g-eto-sesgo"></div></div>
</section>

<section>
  <h2>Fase 3 · Series diarias por estación</h2>
  <p>Rs y ETo de cada día con dato. Elige la estación; el zoom en el tiempo se sincroniza entre las dos gráficas.</p>
  <div class="controles" id="c-estacion"></div>
  <div class="tarjeta"><h3>Rs diaria</h3><div class="grafico" id="g-rs-diaria"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3>ETo diaria</h3><div class="grafico" id="g-eto-diaria"></div></div>
</section>

<footer>
  <p>Fase 3: salidas de <code>codigo/punto1/12_rs_brillo_solar_vs_era5land.py</code> y
  <code>13_eto_estaciones_vs_era5land.py</code> en <code>productos/punto1/</code>.</p>
  <p>Generado por <code>temp/graficas_series_horarias.py</code> a partir de <code>datos/punto1/era5land_puntos/</code>,
  <code>productos/punto1/eto_mensual_cuenca.csv</code> y la ETP de Hargreaves de la Tarea 1. Conversiones solo de
  unidades: K → °C, Pa → kPa, ssrd J/m² en la hora → W/m² (÷ 3600).</p>
</footer>
</div>
<script>
const CARGA = __CARGA__;
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const OPCIONES = {scrollZoom: true, displaylogo: false, responsive: true};
// Colores: Okabe–Ito para los 6 puntos; la ETP de Hargreaves con el color de la ETP en el informe de la Tarea 1.
const COLOR_PUNTO = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9'];
const COLOR = {eto: '#1B6A80', hargreaves: '#7C5BC7', radiativa: '#E69F00', aerodinamica: '#56B4E9'};

function base(unidad) {
  const tinta = css('--tinta'), tenue = css('--tenue'), linea = css('--linea');
  return {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: 'IBM Plex Mono, ui-monospace, monospace', size: 11, color: tinta},
    margin: {t: 36, r: 10, b: 36, l: 54}, hovermode: 'x unified', showlegend: true,
    legend: {orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'left', x: 0, font: {size: 10.5}},
    xaxis: {type: 'date', gridcolor: linea, zeroline: false, linecolor: linea, tickcolor: linea, tickfont: {color: tenue}},
    yaxis: {gridcolor: linea, zeroline: false, linecolor: linea, tickcolor: linea, tickfont: {color: tenue},
            title: {text: unidad, font: {size: 11, color: tenue}}}
  };
}

// Encabezado: cifras calculadas en Python.
for (const [valor, texto] of CARGA.cifras) {
  const d = document.createElement('div'); d.className = 'cifra';
  d.innerHTML = `<b>${valor}</b><span>${texto}</span>`;
  document.getElementById('cifras').appendChild(d);
}

// ETo mensual.
(() => {
  const M = CARGA.mensual, x = M.meses.map(m => m + '-01');
  const l1 = base('mm/mes'); l1.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-comparacion', [
    {type: 'scatter', mode: 'lines', name: 'ETo Penman–Monteith', x, y: M.eto, line: {color: COLOR.eto, width: 2}},
    {type: 'scatter', mode: 'lines', name: 'ETP Hargreaves', x, y: M.hargreaves, line: {color: COLOR.hargreaves, width: 1.6, dash: 'dot'}}],
    l1, OPCIONES);
  const l2 = base('mm/mes'); l2.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-terminos', [
    {type: 'scatter', mode: 'lines', stackgroup: 'eto', name: 'Radiativo', x, y: M.radiativa, line: {color: COLOR.radiativa, width: 1}},
    {type: 'scatter', mode: 'lines', stackgroup: 'eto', name: 'Aerodinámico', x, y: M.aerodinamica, line: {color: COLOR.aerodinamica, width: 1}}],
    l2, OPCIONES);
})();

// ---------- Fase 3 ----------
(() => {
  const F = CARGA.fase3, MESES = ['E','F','M','A','M','J','J','A','S','O','N','D'], xm = [1,2,3,4,5,6,7,8,9,10,11,12];
  const COLOR_EST = ['#0072B2', '#D55E00', '#009E73'];
  const C = {estacion: '#1B6A80', era5: '#C8553D', b: '#5A9E6F'};
  const fmt = (v, d = 2) => (v > 0 ? '+' : '') + v.toFixed(d);
  const ejeMes = l => { l.xaxis = Object.assign(l.xaxis, {type: 'linear', tickvals: xm, ticktext: MESES}); l.hovermode = 'x unified'; return l; };
  const tabla = (id, cab, filas) => { document.getElementById(id).innerHTML =
    `<table><thead><tr>${cab.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>` +
    filas.map(f => `<tr>${f.map(c => `<td>${c}</td>`).join('')}</tr>`).join('') + '</tbody></table>'; };
  const tarjeta = (cont, titulo) => { const t = document.createElement('div'); t.className = 'tarjeta';
    t.innerHTML = `<h3>${titulo}</h3>`; const g = document.createElement('div'); g.className = 'grafico';
    t.appendChild(g); document.getElementById(cont).appendChild(t); return g; };

  tabla('t-rs', ['Estación', 'Punto ERA5', 'Distancia', 'Estación − celda DEM', 'Días', 'Sesgo (MJ/m²·día)', 'Sesgo %', 'RMSE diario'],
    F.map(e => [e.nombre, e.punto, e.distancia_km.toFixed(1) + ' km', fmt(e.dz_celda_m, 0) + ' m', e.rs.dias,
                fmt(e.rs.sesgo_total), fmt(e.rs.sesgo_pct, 1), e.rs.rmse.toFixed(2)]));
  tabla('t-eto', ['Estación', 'Días', 'Sesgo (a), mm/día', 'Sesgo (a) %', 'RMSE (a)', 'Sesgo (b), mm/día', 'Sesgo (b) %', 'RMSE (b)'],
    F.map(e => { const a = e.eto.resumen.mogotes_aut, b = e.eto.resumen['2ms'];
      return [e.nombre, a.dias, fmt(a.sesgo), fmt(a.pct, 1), a.rmse.toFixed(2), fmt(b.sesgo), fmt(b.pct, 1), b.rmse.toFixed(2)]; }));

  F.forEach(e => {
    Plotly.newPlot(tarjeta('r-rs', e.nombre), [
      {type: 'scatter', mode: 'lines+markers', name: 'Estación (Angstrom)', x: xm, y: e.rs.estacion, line: {color: C.estacion}},
      {type: 'scatter', mode: 'lines+markers', name: `ERA5-Land (punto ${e.punto})`, x: xm, y: e.rs.era5, line: {color: C.era5, dash: 'dash'}}],
      ejeMes(base('MJ/m²·día')), OPCIONES);
    Plotly.newPlot(tarjeta('r-eto', e.nombre), [
      {type: 'scatter', mode: 'lines+markers', name: 'Estación (a)', x: xm, y: e.eto.a, line: {color: C.estacion}},
      {type: 'scatter', mode: 'lines+markers', name: 'Estación (b)', x: xm, y: e.eto.b, line: {color: C.b, dash: 'dot'}},
      {type: 'scatter', mode: 'lines+markers', name: `ERA5-Land (punto ${e.punto})`, x: xm, y: e.eto.era5, line: {color: C.era5, dash: 'dash'}}],
      ejeMes(base('mm/día')), OPCIONES);
  });
  Plotly.newPlot('g-rs-sesgo', F.map((e, k) => ({type: 'scatter', mode: 'lines+markers', name: e.nombre, x: xm, y: e.rs.sesgo,
    line: {color: COLOR_EST[k]}})), ejeMes(base('MJ/m²·día')), OPCIONES);
  Plotly.newPlot('g-eto-sesgo', F.flatMap((e, k) => [
    {type: 'scatter', mode: 'lines+markers', name: e.nombre + ' (a)', x: xm, y: e.eto.sesgo_a, line: {color: COLOR_EST[k]}},
    {type: 'scatter', mode: 'lines+markers', name: e.nombre + ' (b)', x: xm, y: e.eto.sesgo_b, line: {color: COLOR_EST[k], dash: 'dot'}}]),
    ejeMes(base('mm/día')), OPCIONES);

  // Series diarias con selector de estación y zoom sincronizado
  const dibujar = k => {
    const e = F[k];
    const l1 = base('MJ/m²·día'); l1.hovermode = 'closest';
    Plotly.react('g-rs-diaria', [
      {type: 'scattergl', mode: 'lines', name: 'Estación (Angstrom)', x: e.diaria_rs.fecha, y: e.diaria_rs.estacion, line: {color: C.estacion, width: 1}},
      {type: 'scattergl', mode: 'lines', name: `ERA5-Land (punto ${e.punto})`, x: e.diaria_rs.fecha, y: e.diaria_rs.era5, line: {color: C.era5, width: 1}}],
      l1, OPCIONES);
    const l2 = base('mm/día'); l2.hovermode = 'closest';
    Plotly.react('g-eto-diaria', [
      {type: 'scattergl', mode: 'lines', name: 'Estación (a)', x: e.diaria_eto.fecha, y: e.diaria_eto.a, line: {color: C.estacion, width: 1}},
      {type: 'scattergl', mode: 'lines', name: 'Estación (b)', x: e.diaria_eto.fecha, y: e.diaria_eto.b, line: {color: C.b, width: 1}, visible: 'legendonly'},
      {type: 'scattergl', mode: 'lines', name: `ERA5-Land (punto ${e.punto})`, x: e.diaria_eto.fecha, y: e.diaria_eto.era5, line: {color: C.era5, width: 1}}],
      l2, OPCIONES);
  };
  F.forEach((e, k) => { const b = document.createElement('button'); b.textContent = e.nombre; b.setAttribute('aria-pressed', String(k === 0));
    b.onclick = () => { document.querySelectorAll('#c-estacion button').forEach(o => o.setAttribute('aria-pressed', String(o === b))); dibujar(k); };
    document.getElementById('c-estacion').appendChild(b); });
  dibujar(0);
  let enSincronia = false;
  const pares = [['g-rs-diaria', 'g-eto-diaria'], ['g-eto-diaria', 'g-rs-diaria']];
  pares.forEach(([a, b]) => document.getElementById(a).on('plotly_relayout', ev => {
    if (enSincronia) return; const cambio = {};
    if (ev['xaxis.range[0]'] !== undefined) cambio['xaxis.range'] = [ev['xaxis.range[0]'], ev['xaxis.range[1]']];
    else if (ev['xaxis.autorange']) cambio['xaxis.autorange'] = true; else return;
    enSincronia = true; Plotly.relayout(b, cambio).then(() => { enSincronia = false; });
  }));
})();

// Series horarias en rejilla, con el zoom en el tiempo sincronizado.
if (!CARGA.variables.length) document.getElementById('s-horarias').hidden = true;
const decodificar = b64 => { const s = atob(b64), b = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return new Float32Array(b.buffer); };
const t0 = new Date(CARGA.inicio_local + 'Z').getTime();
const pad = v => String(v).padStart(2, '0');
const tiempos = Array.from({length: CARGA.horas}, (_, i) => { const d = new Date(t0 + i * 3600000);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:00`; });
const nodos = [];
let sincronizando = false;
for (const v of CARGA.variables) {
  const tarjeta = document.createElement('div'); tarjeta.className = 'tarjeta';
  tarjeta.innerHTML = `<h3>${v.titulo}</h3>`;
  const nodo = document.createElement('div'); nodo.className = 'grafico';
  tarjeta.appendChild(nodo); document.getElementById('rejilla').appendChild(tarjeta);
  const trazas = CARGA.puntos.map((n, k) => ({
    type: 'scattergl', mode: 'lines', name: `P${n}`, legendgroup: `P${n}`, x: tiempos, y: decodificar(v.series[String(n)]),
    line: {width: 1, color: COLOR_PUNTO[k]}, hovertemplate: `P${n}: %{y:.2f} ${v.unidades}<extra></extra>`}));
  const disposicion = base(v.unidades); disposicion.hovermode = 'closest';
  Plotly.newPlot(nodo, trazas, disposicion, OPCIONES);
  nodos.push(nodo);
  // Zoom en el tiempo: se copia a las demás gráficas.
  nodo.on('plotly_relayout', ev => {
    if (sincronizando) return;
    const cambio = {};
    if (ev['xaxis.range[0]'] !== undefined) { cambio['xaxis.range'] = [ev['xaxis.range[0]'], ev['xaxis.range[1]']]; }
    else if (ev['xaxis.autorange']) { cambio['xaxis.autorange'] = true; }
    else return;
    sincronizando = true;
    Promise.all(nodos.filter(o => o !== nodo).map(o => Plotly.relayout(o, cambio))).then(() => { sincronizando = false; });
  });
  // Leyenda: ocultar o mostrar un punto en todas.
  nodo.on('plotly_legendclick', ev => {
    const k = ev.curveNumber, visible = ev.data[k].visible === 'legendonly' ? true : 'legendonly';
    nodos.forEach(o => Plotly.restyle(o, {visible}, [k]));
    return false;
  });
}

// Ventanas de tiempo para las series horarias.
const ventanas = [['Todo', null], ['1 año', 365], ['1 mes', 31], ['1 semana', 7]];
for (const [nombre, dias] of ventanas) {
  const b = document.createElement('button'); b.textContent = nombre; b.setAttribute('aria-pressed', String(dias === null));
  b.onclick = () => {
    document.querySelectorAll('#ventanas button').forEach(o => o.setAttribute('aria-pressed', String(o === b)));
    const fin = tiempos[tiempos.length - 1];
    const cambio = dias === null ? {'xaxis.autorange': true}
      : {'xaxis.range': [new Date(new Date(fin.replace(' ', 'T') + 'Z').getTime() - dias * 86400000).toISOString().slice(0, 16).replace('T', ' '), fin]};
    sincronizando = true;
    Promise.all(nodos.map(o => Plotly.relayout(o, cambio))).then(() => { sincronizando = false; });
  };
  document.getElementById('ventanas').appendChild(b);
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
