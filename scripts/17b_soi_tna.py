"""Índice de Oscilación del Sur (SOI) y del Atlántico tropical norte (TNA) de la NOAA: descarga y tabla mensual.

SOI (Southern Oscillation Index): diferencia de la presión al nivel del mar entre Tahití y Darwin, cada una
estandarizada. Es la cara atmosférica del ENSO: SOI negativo acompaña a El Niño y SOI positivo a La Niña (al revés
que el ONI, que es la temperatura del mar). El archivo de la NOAA trae dos tablas, la anomalía en hPa y la versión
ESTANDARIZADA; se usa la estandarizada, que es la que la NOAA publica como el SOI.

TNA (Tropical Northern Atlantic Index): anomalía mensual de la temperatura superficial del mar en el Atlántico tropical
norte (5.5° N-23.5° N, 15° O-57.5° O), de Enfield et al. (1999), que publica NOAA PSL a partir de HadISST1.1 con la
climatología 1991-2020. Es el índice del Atlántico que entra para comparar su peso sobre el caudal con el del SOI.
(El 2026-10-11 el usuario lo eligió en lugar de la NAO, la Oscilación del Atlántico Norte.)

Fuentes (datos públicos del gobierno de EE. UU.):
  https://www.cpc.ncep.noaa.gov/data/indices/soi
  https://psl.noaa.gov/data/correlation/tna.data

Salidas:
  data/noaa/soi.txt, data/noaa/tna.txt     los archivos tal como se descargaron
  out/soi_tna_mensual_1981_2022.csv         periodo, soi, tna; 1981-2022 (la ventana común 1998-2022 es un recorte)
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()   # en algunos equipos algo intercepta TLS; sin esto requests no verifica

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = {
    "soi": ("https://www.cpc.ncep.noaa.gov/data/indices/soi", RAIZ / "data/noaa/soi.txt"),
    "tna": ("https://psl.noaa.gov/data/correlation/tna.data", RAIZ / "data/noaa/tna.txt"),
}
FALTANTE_SOI = -999.9        # así marca la NOAA los meses sin dato en el archivo del SOI
FALTANTE_TNA = -99.99        # y así NOAA PSL en el del TNA
INICIO, FIN = "1981-01", "2022-12"

# --- descarga (solo si no está ya en data/: el crudo no se vuelve a bajar ni se edita)
for url, crudo in FUENTES.values():
    if not crudo.exists():
        crudo.parent.mkdir(parents=True, exist_ok=True)
        respuesta = requests.get(url, timeout=60)
        respuesta.raise_for_status()
        crudo.write_bytes(respuesta.content)


def leer_soi(ruta):
    """Lee la tabla ESTANDARIZADA del archivo del SOI (la segunda del archivo).

    Las filas son de ancho fijo: 4 caracteres del año y 12 meses de 6 caracteres. No se separa por espacios porque
    los faltantes se pegan al valor anterior («-3.3-999.9»)."""
    lineas = ruta.read_text().splitlines()
    inicio = next(i for i, l in enumerate(lineas) if "STANDARDIZED" in l)
    valores = {}
    for linea in lineas[inicio:]:
        if not linea[:4].isdigit():
            continue
        anio = int(linea[:4])
        for mes in range(12):
            valores[pd.Period(year=anio, month=mes + 1, freq="M")] = float(linea[4 + 6 * mes: 10 + 6 * mes])
    serie = pd.Series(valores, name="soi").sort_index()
    return serie.replace(FALTANTE_SOI, np.nan)


def leer_tna(ruta):
    """Lee el TNA en el formato de NOAA PSL: una línea con el primer y el último año, luego una fila por año con los 12
    meses, y al final el código de faltante y unas líneas de descripción (que se saltan)."""
    lineas = ruta.read_text().splitlines()
    primero, ultimo = (int(x) for x in lineas[0].split())
    valores = {}
    for linea in lineas[1:]:
        campos = linea.split()
        if len(campos) != 13 or not campos[0].isdigit():
            continue
        anio = int(campos[0])
        assert primero <= anio <= ultimo
        for mes, x in enumerate(campos[1:], start=1):
            valores[pd.Period(year=anio, month=mes, freq="M")] = float(x)
    return pd.Series(valores, name="tna").sort_index().replace(FALTANTE_TNA, np.nan)


soi = leer_soi(FUENTES["soi"][1])
tna = leer_tna(FUENTES["tna"][1])

periodo = pd.period_range(INICIO, FIN, freq="M")
salida = pd.DataFrame({"soi": soi, "tna": tna}).reindex(periodo).rename_axis("periodo")
assert salida.notna().all().all(), "faltan meses de SOI o TNA en 1981-2022"
salida.to_csv(RAIZ / "out/soi_tna_mensual_1981_2022.csv")

for nombre, serie in (("SOI", soi), ("TNA", tna)):
    crudo = FUENTES[nombre.lower()][1]
    sha = hashlib.sha256(crudo.read_bytes()).hexdigest()
    validos = serie.dropna()
    print(f"{crudo.relative_to(RAIZ)}: {nombre}, {len(validos)} meses con dato, "
          f"{validos.index.min()} a {validos.index.max()}, SHA-256 {sha}")
print(f"out/soi_tna_mensual_1981_2022.csv: {len(salida)} meses, sin vacíos")
print(salida.describe().round(2).to_string())
