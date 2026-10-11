"""Índice de Oscilación del Sur (SOI) y Oscilación del Atlántico Norte (NAO) de la NOAA: descarga y tabla mensual.

SOI (Southern Oscillation Index): diferencia de la presión al nivel del mar entre Tahití y Darwin, cada una
estandarizada. Es la cara atmosférica del ENSO: SOI negativo acompaña a El Niño y SOI positivo a La Niña (al revés
que el ONI, que es la temperatura del mar). El archivo de la NOAA trae dos tablas, la anomalía en hPa y la versión
ESTANDARIZADA; se usa la estandarizada, que es la que la NOAA publica como el SOI.

NAO (North Atlantic Oscillation): índice mensual estandarizado del patrón de presión entre Islandia y las Azores,
calculado por la NOAA con componentes principales rotadas sobre la altura de 500 hPa. Es un modo del Atlántico
Norte; aquí entra para comparar su peso sobre el caudal con el del SOI.

Fuentes (datos públicos del gobierno de EE. UU.):
  https://www.cpc.ncep.noaa.gov/data/indices/soi
  https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii

Salidas:
  data/noaa/soi.txt, data/noaa/nao.txt     los archivos tal como se descargaron
  out/soi_nao_mensual_1981_2022.csv         periodo, soi, nao; 1981-2022 (la ventana común 1998-2022 es un recorte)
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
    "nao": ("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii",
            RAIZ / "data/noaa/nao.txt"),
}
FALTANTE_SOI = -999.9        # así marca la NOAA los meses sin dato en el archivo del SOI
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


def leer_nao(ruta):
    """Lee el NAO: una fila por mes con año, mes y valor."""
    d = pd.read_csv(ruta, sep=r"\s+", header=None, names=["anio", "mes", "nao"])
    indice = [pd.Period(year=a, month=m, freq="M") for a, m in zip(d.anio, d.mes)]
    return pd.Series(d.nao.to_numpy(dtype=float), index=indice, name="nao").sort_index()


soi = leer_soi(FUENTES["soi"][1])
nao = leer_nao(FUENTES["nao"][1])

periodo = pd.period_range(INICIO, FIN, freq="M")
salida = pd.DataFrame({"soi": soi, "nao": nao}).reindex(periodo).rename_axis("periodo")
assert salida.notna().all().all(), "faltan meses de SOI o NAO en 1981-2022"
salida.to_csv(RAIZ / "out/soi_nao_mensual_1981_2022.csv")

for nombre, serie in (("SOI", soi), ("NAO", nao)):
    crudo = FUENTES[nombre.lower()][1]
    sha = hashlib.sha256(crudo.read_bytes()).hexdigest()
    validos = serie.dropna()
    print(f"{crudo.relative_to(RAIZ)}: {nombre}, {len(validos)} meses con dato, "
          f"{validos.index.min()} a {validos.index.max()}, SHA-256 {sha}")
print(f"out/soi_nao_mensual_1981_2022.csv: {len(salida)} meses, sin vacíos")
print(salida.describe().round(2).to_string())
