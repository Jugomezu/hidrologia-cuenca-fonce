"""Procesa la segunda descarga del portal DHIME: precipitación total mensual 1998-2022.

Qué se bajó y por qué
---------------------
La primera descarga (`scripts/historico/23_pluviometros_dhime.py`) trajo solo tres estaciones. Esta segunda
barre **todas** las estaciones con serie "Precipitación total mensual" de los ocho municipios que
componen la cuenca del Fonce (Charalá, Coromoro, Encino, Mogotes, Ocamonte, Páramo, San Gil y
Valle de San José) y se queda con las que cubren el período de estudio.

De las 22 estaciones de esos municipios que tienen esa serie, 14 terminan su registro en 1994 o
antes (LAGUNA LA, LEJIA LA, MESON EL, CHAPA, VILLANUEVA, las CHARALA antiguas, etc.), así que no
alcanzan ni de lejos el período 1998-2022 y se descartaron en el portal. Las estaciones
automáticas de la zona (ENCINO-AUT, CHARALA-AUT, ESC AGR MOGOTES-AUT, MOGOTES-AUT) no publican
serie mensual totalizada, solo registros sub-diarios. Quedaron ocho candidatas, que son las que
trae el archivo.

Criterio de aceptación (el que pidió el usuario)
------------------------------------------------
Se conserva la estación cuya serie mensual tenga dato en **al menos el 70 % de los 300 meses**
del período 1998-2022, es decir 210 meses o más. El cálculo se hace aquí, sobre los datos
efectivamente descargados; no se confía en el número de registros que anuncia el portal.

Salidas
-------
  out/pluviometros_fonce_mensual_1998_2022.csv   fecha, codigo, nombre, precipitacion_mm, nivel_aprobacion
  out/pluviometros_fonce_1998_2022_resumen.csv   cobertura de cada estación y si fue aceptada
  out/pluviometros_fonce_catalogo.csv            código, nombre, altitud, latitud, longitud, dentro de la cuenca
  out/pluviometros_fonce_mensual_depurado.csv    la misma serie SIN los tramos excluidos (ver abajo):
                                                 es la que usan todos los análisis
  out/pluviometros_exclusiones.csv               qué se excluyó y por qué

Tramos excluidos (decidido el 2026-09-28)
-----------------------------------------
ENCINO (24020040), años 2016, 2017 y 2018. Sus totales anuales saltan a 4 283, 6 695 y 4 833 mm, cuando
el resto de su serie ronda los 3 100, y vuelven a su nivel en 2019. Ninguna otra fuente acompaña ese
salto: sin esos tres años, PL coincide con IMERG en 2016-2018 (con ellos, PL sale 23 % por encima del
promedio en 2017 mientras IMERG sale 3 %), y el caudal de esos años es normal o bajo. En junio de 2017
Encino marcó 932 mm, 7.2 veces su mediana de junio, y por sí solo volvía atípico ese mes de PL. Se trata
como un problema de registro: esos 36 meses de Encino se quitan de TODOS los análisis. La serie cruda se
conserva aparte solo para documentar la decisión.
"""
import hashlib
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()   # en este equipo algo intercepta TLS; sin esto requests no verifica

RAIZ = Path(__file__).resolve().parent.parent
ZIP = RAIZ / "data/ideam/pluviometros/dhime/dhime_mensual_1998_2022_8est.zip"
OUT = RAIZ / "out"

PERIODO = pd.period_range("1998-01", "2022-12", freq="M")   # 300 meses, el período del proyecto
COBERTURA_MINIMA = 0.70                                     # 70 % -> 210 meses

# Catálogo Nacional de Estaciones del IDEAM, servido como capa ArcGIS (público, sin credenciales).
CNE = "https://dhime.ideam.gov.co/server/rest/services/CNE/Estaciones/MapServer/0/query"


def leer_descarga(ruta):
    """Lee el CSV que viene dentro del zip de DHIME.

    El portal no es consistente con la codificación: la descarga de 2026-09-23 vino en latin-1 y
    la de 2026-09-24 en UTF-8. Se prueban las dos en vez de fijar una.
    """
    with zipfile.ZipFile(ruta) as z:
        nombre = z.namelist()[0]
        crudo = z.read(nombre)
    for codificacion in ("utf-8", "latin-1"):
        try:
            texto = crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
        if "Ã" not in texto:          # marca típica de UTF-8 leído como latin-1
            break
    else:
        raise ValueError(f"no se pudo decodificar {ruta}")

    from io import StringIO
    d = pd.read_csv(StringIO(texto))
    d = d.rename(columns={
        "CodigoEstacion": "codigo", "NombreEstacion": "nombre_completo", "Fecha": "fecha",
        "Valor": "precipitacion_mm", "NivelAprobacion": "nivel_aprobacion",
    })
    d["fecha"] = pd.to_datetime(d["fecha"])
    # "PAVAS LAS [24020220]" -> "PAVAS LAS"
    d["nombre"] = d["nombre_completo"].str.replace(r"\s*\[\d+\]\s*$", "", regex=True).str.strip()
    return d[["fecha", "codigo", "nombre", "precipitacion_mm", "nivel_aprobacion"]].sort_values(
        ["codigo", "fecha"]).reset_index(drop=True)


def cobertura(d):
    """Meses con dato dentro de 1998-2022 y fracción sobre los 300 del período."""
    filas = []
    for codigo, g in d.groupby("codigo"):
        meses = g.set_index(g.fecha.dt.to_period("M")).precipitacion_mm.reindex(PERIODO)
        con_dato = int(meses.notna().sum())
        filas.append({
            "codigo": codigo,
            "nombre": g.nombre.iloc[0],
            "meses_con_dato": con_dato,
            "meses_periodo": len(PERIODO),
            "cobertura_pct": round(con_dato / len(PERIODO) * 100, 1),
            "desde": g.fecha.min().date(),
            "hasta": g.fecha.max().date(),
            "media_mm_mes": round(g.precipitacion_mm.mean(), 1),
            "aceptada": con_dato >= COBERTURA_MINIMA * len(PERIODO),
        })
    return pd.DataFrame(filas).sort_values("cobertura_pct", ascending=False).reset_index(drop=True)


def catalogo(codigos):
    """Altitud y coordenadas de cada estación, tomadas del Catálogo Nacional de Estaciones."""
    codigos_sql = ",".join(f"'{c}'" for c in codigos)
    r = requests.get(CNE, params={
        "where": f"idestacion IN ({codigos_sql})",
        "outFields": "idestacion,nombre,altitud,latitud,longitud,idcategoria,idestadoestaciontm",
        "returnGeometry": "false", "f": "json",
    }, timeout=120)
    r.raise_for_status()
    atributos = [f["attributes"] for f in r.json()["features"]]
    c = pd.DataFrame(atributos).rename(columns={"idestacion": "codigo"})
    c["codigo"] = c["codigo"].astype(int)
    return c


def marcar_dentro_de_la_cuenca(c):
    """¿La estación cae dentro del polígono de San Gil? Se resuelve con el shapefile del proyecto."""
    cuencas = gpd.read_file(RAIZ / "out/shp_fonce/cuencas_fonce.shp")
    san_gil = cuencas[cuencas.gauge_id.astype(int) == 24027010].geometry.union_all()
    puntos = gpd.GeoSeries(gpd.points_from_xy(c.longitud, c.latitud), crs=cuencas.crs)
    c["dentro_cuenca"] = puntos.within(san_gil).values
    return c


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


d = leer_descarga(ZIP)
resumen = cobertura(d)
aceptadas = resumen.loc[resumen.aceptada, "codigo"].tolist()

cat = marcar_dentro_de_la_cuenca(catalogo(resumen.codigo.tolist()))
cat = cat.merge(resumen[["codigo", "cobertura_pct", "aceptada"]], on="codigo")

# Solo las estaciones aceptadas y solo el período de estudio.
d = d[d.codigo.isin(aceptadas)]
d = d[(d.fecha >= "1998-01-01") & (d.fecha <= "2022-12-31")]

d.to_csv(OUT / "pluviometros_fonce_mensual_1998_2022.csv", index=False)

# Tramos que se excluyen de todos los análisis (la razón está en el docstring). Se declaran aquí, en un
# solo lugar, y todo lo demás lee la serie depurada.
# Tramos que se sacan de PL en todos los análisis. `evidencia` dice en qué sección del notebook está la
# prueba: Encino en 1.7; los demás en 4.3, detectados por 07c_anomalias.py.
MESES_EN_CERO = {"razon": "0 mm en el mes mientras todos los demás pluviómetros midieron al menos 20 mm: "
                          "se trata como un mes no registrado, no como un mes sin lluvia (decidido el 2026-09-28)",
                 "solo_si_cero": True, "evidencia": "4.3"}
EXCLUSIONES = pd.DataFrame([
    {"codigo": 24020040, "desde": "2016-01", "hasta": "2018-12", "solo_si_cero": False, "evidencia": "1.7",
     "razon": "totales anuales 2016-2018 muy por encima del resto de su serie, sin respaldo en IMERG "
              "ni en el caudal; tratado como problema de registro"},
    {"codigo": 24020230, "desde": "1998-01", "hasta": "2004-11", "solo_si_cero": False, "evidencia": "4.3",
     "razon": "salto de nivel: hasta 2004-11 mide cerca de la cuarta parte que sus vecinos y desde 2004-12 "
              "unas tres cuartas partes (prueba de Pettitt, p < 0.001); el catálogo del IDEAM no registra el "
              "cambio; tratado como problema de registro (decidido el 2026-09-28)"},
    *[{"codigo": c, "desde": m, "hasta": m, **MESES_EN_CERO} for c, m in [
        (24020220, "2000-08"), (24020220, "2009-07"), (24020220, "2013-07"), (24020220, "2018-05"),
        (24020220, "2019-07"), (24020080, "2017-12"), (24020080, "2021-12")]],
])
fuera = pd.Series(False, index=d.index)
excluidos_por_fila = []
for _, e in EXCLUSIONES.iterrows():
    esta = ((d.codigo == e.codigo) & (d.fecha >= pd.Timestamp(e.desde + "-01"))
            & (d.fecha <= pd.Period(e.hasta, "M").to_timestamp(how="end")))
    if e.solo_si_cero:
        # salvaguarda: estas filas solo existen para meses en 0 mm; si el dato cambiara, se detiene
        assert (d.loc[esta, "precipitacion_mm"] == 0).all() and esta.sum() == 1, (e.codigo, e.desde)
    fuera |= esta
    excluidos_por_fila.append(int(esta.sum()))
d[~fuera].to_csv(OUT / "pluviometros_fonce_mensual_depurado.csv", index=False)
EXCLUSIONES.assign(meses_excluidos=excluidos_por_fila).to_csv(OUT / "pluviometros_exclusiones.csv", index=False)
resumen.to_csv(OUT / "pluviometros_fonce_1998_2022_resumen.csv", index=False)
cat.to_csv(OUT / "pluviometros_fonce_catalogo.csv", index=False)

print(f"archivo fuente: {ZIP.name}  SHA-256 {sha256(ZIP)}")
print(f"\nCobertura mensual en 1998-2022 (umbral: {COBERTURA_MINIMA:.0%} = "
      f"{int(COBERTURA_MINIMA * len(PERIODO))} de {len(PERIODO)} meses)")
print(resumen.to_string(index=False))
print(f"\nAceptadas: {len(aceptadas)} de {len(resumen)}")
print(f"\nUbicación (del Catálogo Nacional de Estaciones):")
print(cat[["codigo", "nombre", "altitud", "latitud", "longitud", "dentro_cuenca"]].to_string(index=False))
print(f"\nGuardado: {len(d)} registros mensuales en out/pluviometros_fonce_mensual_1998_2022.csv")
print(f"Depurado: {int((~fuera).sum())} registros ({int(fuera.sum())} excluidos) en "
      f"out/pluviometros_fonce_mensual_depurado.csv")
