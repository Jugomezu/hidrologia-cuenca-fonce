"""Índice Oceánico El Niño (ONI) de la NOAA: descarga y clasificación mensual en El Niño / La Niña / neutro.

El ONI es la anomalía de la temperatura superficial del mar en la región Niño 3.4 del Pacífico, promediada
en trimestres móviles (DJF, JFM, ..., NDJ). Lo publica el Climate Prediction Center de la NOAA y es el
índice con que la NOAA declara oficialmente los episodios de El Niño y La Niña.

Clasificación (la definición operativa de la NOAA):
  - el ONI se redondea a un decimal, como lo publica la NOAA en su tabla, y sobre ese valor un trimestre
    es "cálido" si es >= +0.5 °C y "frío" si es <= -0.5 °C;
  - hay episodio de El Niño (La Niña) cuando hay al menos 5 trimestres móviles CONSECUTIVOS cálidos (fríos);
  - cada trimestre se asigna a su mes central (DJF -> enero, JFM -> febrero, ..., NDJ -> diciembre).
Los trimestres cálidos o fríos sueltos, que no completan 5 seguidos, quedan como neutros.

Fuente: https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt (datos públicos del gobierno de EE. UU.)

Salidas:
  data/noaa/oni.ascii.txt      el archivo tal como se descargó
  out/oni_mensual.csv          periodo, oni, fase ("El Niño", "La Niña" o "neutro"), 1998-2022
"""
import hashlib
from pathlib import Path

import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()   # en este equipo algo intercepta TLS; sin esto requests no verifica

RAIZ = Path(__file__).resolve().parent.parent
URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
CRUDO = RAIZ / "data/noaa/oni.ascii.txt"
UMBRAL = 0.5                 # °C
MIN_TRIMESTRES = 5           # trimestres móviles consecutivos para declarar un episodio
MES_CENTRAL = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
               "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}

# --- descarga (solo si no está ya en data/: el crudo no se vuelve a bajar ni se edita)
if not CRUDO.exists():
    CRUDO.parent.mkdir(parents=True, exist_ok=True)
    respuesta = requests.get(URL, timeout=60)
    respuesta.raise_for_status()
    CRUDO.write_bytes(respuesta.content)

oni = pd.read_csv(CRUDO, sep=r"\s+")
oni["periodo"] = [pd.Period(year=int(a), month=MES_CENTRAL[s], freq="M") for s, a in zip(oni.SEAS, oni.YR)]
oni = oni.set_index("periodo")["ANOM"].rename("oni").sort_index()


def episodios(condicion):
    """Marca los meses que forman parte de una racha de al menos MIN_TRIMESTRES trimestres seguidos."""
    racha = (condicion != condicion.shift()).cumsum()
    largo = condicion.groupby(racha).transform("size")
    return condicion & (largo >= MIN_TRIMESTRES)


fase = pd.Series("neutro", index=oni.index)
oni_tabla = oni.round(1)                    # el valor que muestra la tabla oficial de la NOAA
fase[episodios(oni_tabla >= UMBRAL)] = "El Niño"
fase[episodios(oni_tabla <= -UMBRAL)] = "La Niña"

periodo = pd.period_range("1998-01", "2022-12", freq="M")
salida = pd.DataFrame({"oni": oni, "oni_tabla": oni_tabla, "fase": fase}).reindex(periodo).rename_axis("periodo")
salida.to_csv(RAIZ / "out/oni_mensual.csv")

sha = hashlib.sha256(CRUDO.read_bytes()).hexdigest()
print(f"{CRUDO.relative_to(RAIZ)}: {len(oni)} trimestres, {oni.index.min()} a {oni.index.max()}, SHA-256 {sha}")
print("meses por fase, 1998-2022:")
print(salida.fase.value_counts().to_string())
