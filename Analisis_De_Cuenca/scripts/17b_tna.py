"""Índice del Atlántico tropical norte (TNA) de NOAA PSL: descarga y tabla mensual.

TNA (Tropical Northern Atlantic Index): anomalía mensual de la temperatura superficial del mar en el Atlántico tropical
norte (5.5° N-23.5° N, 15° O-57.5° O), de Enfield et al. (1999), que publica NOAA PSL a partir de HadISST1.1 con la
climatología 1991-2020. Es el análogo atlántico del ONI (los dos son anomalías de la SST en un recuadro tropical) y entra
para comparar el peso del Atlántico sobre el caudal con el del Pacífico.
(El 2026-10-11 el usuario lo eligió en lugar de la NAO, la Oscilación del Atlántico Norte, y decidió comparar el ONI
contra el TNA, sin el SOI.)

Fuente (datos públicos del gobierno de EE. UU.): https://psl.noaa.gov/data/correlation/tna.data

Salidas:
  data/noaa/tna.txt                    el archivo tal como se descargó
  out/tna_mensual_1981_2022.csv        periodo, tna; 1981-2022 (la ventana común 1998-2022 es un recorte)
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()   # en algunos equipos algo intercepta TLS; sin esto requests no verifica

RAIZ = Path(__file__).resolve().parent.parent
URL = "https://psl.noaa.gov/data/correlation/tna.data"
CRUDO = RAIZ / "data/noaa/tna.txt"
FALTANTE = -99.99            # así marca NOAA PSL los meses sin dato
INICIO, FIN = "1981-01", "2022-12"

# --- descarga (solo si no está ya en data/: el crudo no se vuelve a bajar ni se edita)
if not CRUDO.exists():
    CRUDO.parent.mkdir(parents=True, exist_ok=True)
    respuesta = requests.get(URL, timeout=60)
    respuesta.raise_for_status()
    CRUDO.write_bytes(respuesta.content)


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
    return pd.Series(valores, name="tna").sort_index().replace(FALTANTE, np.nan)


tna = leer_tna(CRUDO)
salida = tna.reindex(pd.period_range(INICIO, FIN, freq="M")).rename_axis("periodo").to_frame()
assert salida.notna().all().all(), "faltan meses del TNA en 1981-2022"
salida.to_csv(RAIZ / "out/tna_mensual_1981_2022.csv")

sha = hashlib.sha256(CRUDO.read_bytes()).hexdigest()
validos = tna.dropna()
print(f"{CRUDO.relative_to(RAIZ)}: {len(validos)} meses con dato, {validos.index.min()} a {validos.index.max()}, "
      f"SHA-256 {sha}")
print(f"out/tna_mensual_1981_2022.csv: {len(salida)} meses, sin vacíos")
print(salida.describe().round(2).to_string())
