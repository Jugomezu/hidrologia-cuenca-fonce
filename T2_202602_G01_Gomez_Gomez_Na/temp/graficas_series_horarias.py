"""Documento de trabajo (temporal): series horarias de ERA5-Land en los 6 puntos, en un HTML con zoom.

Lee datos/punto1/era5land_puntos/punto_N.csv (salida de codigo/punto1/01_descarga_era5land_puntos.py) y escribe
temp/series_horarias_era5land.html: una gráfica Plotly por variable, con los 6 puntos, a la que se le puede hacer
zoom (arrastrar un recuadro, rueda del ratón, doble clic para volver).

Hora local de Colombia = valid_time (UTC) − 5 h (decisión del 2026-11-12, temp/decisiones.md).
Conversiones solo de unidades, para leer mejor: K → °C, Pa → kPa, ssrd J/m² en la hora → W/m² promedio de la hora
(÷ 3600). u10 y v10 se muestran tal cual (m/s).

Las 219 144 horas × 6 puntos × 6 variables se guardan dentro del HTML como Float32 en base64, y el eje de tiempo
se reconstruye en el navegador a partir de la primera hora (las series son horarias y sin huecos; se verifica).
Por eso el archivo pesa unos 40 MB: es para abrirlo en el computador, no para el repositorio ni para la entrega.

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

DESFASE_HORA_LOCAL = pd.Timedelta(hours=-5)  # Colombia, UTC−5, sin horario de verano
PUNTOS = [1, 2, 3, 4, 5, 6]

# columna del CSV -> (nombre en la gráfica, unidades, función de conversión)
VARIABLES = {
    "t2m": ("Temperatura del aire a 2 m (t2m)", "°C", lambda x: x - 273.15),
    "d2m": ("Temperatura de punto de rocío a 2 m (d2m)", "°C", lambda x: x - 273.15),
    "sp": ("Presión en superficie (sp)", "kPa", lambda x: x / 1000.0),
    "u10": ("Viento a 10 m, componente hacia el este (u10)", "m/s", lambda x: x),
    "v10": ("Viento a 10 m, componente hacia el norte (v10)", "m/s", lambda x: x),
    "ssrd": ("Radiación solar entrante (ssrd), promedio de la hora", "W/m²", lambda x: x / 3600.0),
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


def main():
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

    html = PLANTILLA.replace("__CARGA__", json.dumps(carga))
    SALIDA.write_text(html, encoding="utf-8")
    print(f"Listo: {SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB), {largo} horas por punto")


PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Series horarias ERA5-Land</title>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<style>
  body { font-family: system-ui, sans-serif; margin: 16px; color: #222; background: #fff; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  p { margin: 4px 0 12px; color: #555; max-width: 900px; }
  .grafica { height: 420px; margin-bottom: 28px; }
</style>
</head>
<body>
<h1>Series horarias de ERA5-Land en los 6 puntos de la cuenca (1998–2022)</h1>
<p>Hora local (UTC−5). Para hacer zoom: arrastra un recuadro o usa la rueda del ratón; doble clic vuelve a la vista
completa. Clic en un punto de la leyenda lo oculta o lo muestra. Los botones de arriba a la izquierda fijan
una ventana de tiempo. Documento de trabajo temporal.</p>
<div id="contenedor"></div>
<script>
const CARGA = __CARGA__;
const decodificar = b64 => { const s = atob(b64), b = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return new Float32Array(b.buffer); };
// Eje de tiempo: la primera hora local más una hora por posición (la serie no tiene huecos).
const t0 = new Date(CARGA.inicio_local + 'Z').getTime();
const pad = v => String(v).padStart(2, '0');
const tiempos = Array.from({length: CARGA.horas}, (_, i) => { const d = new Date(t0 + i * 3600000);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:00`; });
const colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'];
const botones = [
  {count: 7, label: '1 semana', step: 'day', stepmode: 'backward'},
  {count: 1, label: '1 mes', step: 'month', stepmode: 'backward'},
  {count: 1, label: '1 año', step: 'year', stepmode: 'backward'},
  {step: 'all', label: 'todo'}];
for (const v of CARGA.variables) {
  const div = document.createElement('div'); div.className = 'grafica';
  document.getElementById('contenedor').appendChild(div);
  const trazas = CARGA.puntos.map((n, k) => ({
    type: 'scattergl', mode: 'lines', name: `Punto ${n}`, x: tiempos, y: decodificar(v.series[String(n)]),
    line: {width: 1, color: colores[k]}, hovertemplate: `Punto ${n}<br>%{x}<br>%{y:.2f} ${v.unidades}<extra></extra>`}));
  Plotly.newPlot(div, trazas, {
    title: {text: v.titulo, x: 0, font: {size: 15}},
    xaxis: {type: 'date', rangeselector: {buttons: botones}},
    yaxis: {title: {text: v.unidades}},
    margin: {l: 60, r: 20, t: 60, b: 40}, legend: {orientation: 'h', y: -0.15}, hovermode: 'closest'},
    {scrollZoom: true, displaylogo: false, responsive: true, locale: 'es'});
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
