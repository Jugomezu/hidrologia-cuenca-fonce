"""Control de calidad básico de las series crudas (sección 4.2 del notebook).

Revisa, sobre los archivos TAL COMO SE DESCARGARON (antes de que el procesamiento los ordene, reindexe o
agregue), lo que pide el taller: fechas, duplicados, unidades, códigos de faltante, valores negativos o
fuera de rango según la física de cada variable, y banderas de calidad. Cada variable se juzga por su
propia física: una temperatura negativa es posible, una lluvia o un caudal negativos no.

Fuentes revisadas:
  - CAMELS-COL, archivo diario de San Gil (caudal Q, y T mín / T máx de MSWX, P de CHIRPS y ETP que trae)
  - DHIME (IDEAM), totales mensuales de los pluviómetros (PL), el zip descargado
  - IMERG Final V07 mensual (PI), los 300 archivos de texto crudos (mm/h)
  - ERA5-Land diario de Earth Engine (temperatura), los 25 archivos anuales crudos
  - ETP de Hargreaves con ERA5-Land (06b_etp_hargreaves.py)

Además deja lista la parte de IMERG de la revisión a mano de un mes (MES_REVISADO): el valor crudo de
cada píxel que toca la cuenca, en mm/h, su conversión a mm/mes y su peso, para que el notebook rehaga la
cuenta a la vista.

Salidas:
  out/control_calidad_basico.csv           fuente, chequeo, resultado, detalle
  out/control_calidad_pi_mes_revisado.csv  un renglón por píxel de IMERG en MES_REVISADO
  out/naturaleza_fuentes.csv               si cada variable es medida, estimada, simulada o calculada
"""
import calendar
import io
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

RAIZ = Path(__file__).resolve().parent.parent
ID_PRINCIPAL = 24027010
DIAS = pd.date_range("1998-01-01", "2022-12-31", freq="D")
MESES = pd.period_range("1998-01", "2022-12", freq="M")

# Códigos con que las bases de datos suelen marcar un faltante en vez de dejar la casilla vacía
CODIGOS_FALTANTE = [-9999.9, -9999, -999.9, -999, -99.9, -99, 9999, 99999]
# Rango plausible de temperatura del aire en una cuenca andina entre 1 100 y 4 300 m (°C): amplio a
# propósito; solo busca valores imposibles (por ejemplo, kelvin sin convertir), no extremos raros
T_MIN_PLAUSIBLE, T_MAX_PLAUSIBLE = -15.0, 45.0
# Tolerancia para comparar el caudal medio con el que publica CAMELS-COL: un error de unidades daría
# factores de 86.4 o de 1 000, así que un 5 % separa sin ambigüedad "mismas unidades" de "otras"
TOLERANCIA_UNIDADES = 0.05
MES_REVISADO = pd.Period("2019-10", "M")      # mes completo en Q y con los 7 pluviómetros (ver 4.2)

filas = []


ANOTADO, NO_DISPONIBLE = "anotado", "no disponible"


def registrar(fuente, chequeo, sin_problema, detalle):
    """Una fila del informe de control. `sin_problema` es True ("sin problemas"), False ("revisar") o uno
    de dos textos: ANOTADO, un hallazgo que no es un error pero hay que tener presente, o NO_DISPONIBLE,
    cuando la fuente no trae con qué hacer el chequeo."""
    resultado = sin_problema if isinstance(sin_problema, str) else ("sin problemas" if sin_problema else "revisar")
    filas.append({"fuente": fuente, "chequeo": chequeo, "resultado": resultado, "detalle": detalle})


miles = lambda x: f"{x:,.0f}".replace(",", " ")


def codigos_faltante(serie):
    return int(serie.isin(CODIGOS_FALTANTE).sum())


# ====================================================================== CAMELS-COL, diario de San Gil
F = "CAMELS-COL (diario de San Gil)"
crudo = pd.read_csv(RAIZ / f"data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_{ID_PRINCIPAL}.txt",
                    sep="\t", encoding="latin-1")
columnas_originales = list(crudo.columns)
crudo.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
crudo["fecha"] = pd.to_datetime(crudo["fecha"], format="%d/%m/%Y", errors="coerce")

n_ilegibles = int(crudo.fecha.isna().sum())
registrar(F, "fechas legibles", n_ilegibles == 0,
          f"{miles(len(crudo))} filas, {n_ilegibles} fechas que no se pueden leer; formato día/mes/año; "
          f"de {crudo.fecha.min():%Y-%m-%d} a {crudo.fecha.max():%Y-%m-%d}")
registrar(F, "fechas en orden", bool(crudo.fecha.is_monotonic_increasing), "orden cronológico estricto" if crudo.fecha.is_monotonic_increasing else "hay fechas fuera de orden")
n_dup = int(crudo.fecha.duplicated().sum())
registrar(F, "fechas duplicadas", n_dup == 0, f"{n_dup} fechas repetidas")
periodo = crudo[crudo.fecha.between(DIAS[0], DIAS[-1])].set_index("fecha")
n_ausentes = len(DIAS.difference(periodo.index))
registrar(F, "días ausentes en 1998-2022", ANOTADO if n_ausentes else True,
          f"{n_ausentes} de {miles(len(DIAS))} días no tienen fila: el archivo omite el día entero cuando no hay caudal, "
          f"en vez de marcarlo como faltante; son los huecos que cuenta la regla de completitud")
n_nan = int(periodo.isna().sum().sum())
n_cod = sum(codigos_faltante(periodo[c]) for c in ["p_chirps", "etp", "t_min", "t_max", "caudal"])
registrar(F, "códigos de faltante (−9999, −999, 9999…) y vacíos", n_nan == 0 and n_cod == 0,
          f"{n_cod} valores con códigos de faltante y {n_nan} casillas vacías en las filas que existen")
q = periodo.caudal
registrar(F, "Q ≥ 0 (un caudal no puede ser negativo)", bool((q >= 0).all()),
          f"{int((q < 0).sum())} días negativos; mínimo {q.min():.2f} m³/s, máximo {q.max():.1f} m³/s; "
          f"{int((q == 0).sum())} días con caudal exactamente 0")
for col, nombre in (("p_chirps", "P de CHIRPS"), ("etp", "ETP de CAMELS-COL")):
    registrar(F, f"{nombre} ≥ 0", bool((periodo[col] >= 0).all()),
              f"{int((periodo[col] < 0).sum())} días negativos (la columna viene en el archivo pero el proyecto no la usa)")
t_fuera = int(((periodo[["t_min", "t_max"]] < T_MIN_PLAUSIBLE) | (periodo[["t_min", "t_max"]] > T_MAX_PLAUSIBLE)).sum().sum())
registrar(F, f"T de MSWX en rango físico ({T_MIN_PLAUSIBLE:.0f} a {T_MAX_PLAUSIBLE:.0f} °C)", t_fuera == 0,
          f"T mín entre {periodo.t_min.min():.1f} y {periodo.t_min.max():.1f} °C, T máx entre "
          f"{periodo.t_max.min():.1f} y {periodo.t_max.max():.1f} °C; {t_fuera} valores fuera de rango")
n_inv = int((periodo.t_max < periodo.t_min).sum())
registrar(F, "T máx ≥ T mín", n_inv == 0, f"{n_inv} días con la máxima por debajo de la mínima")

# unidades del caudal: el caudal medio del archivo, pasado a mm/día con el área que usa CAMELS-COL, debe
# dar el q_mean (mm/día) que publica su archivo de firmas; si el archivo estuviera en L/s o en mm, no daría
firmas = pd.read_csv(RAIZ / "data/camels_col/signatures/09_CAMELS_COL_Hydrological_signatures.csv").set_index("gauge_id")
maestra = pd.read_csv(RAIZ / "out/camels_col_master.csv").set_index("gauge_id")
area_camels = float(maestra.loc[ID_PRINCIPAL, "area"])
q_mm_dia = crudo.caudal.mean() * 86400 / (area_camels * 1e6) * 1000
q_publicado = float(firmas.loc[ID_PRINCIPAL, "q_mean"])
registrar(F, "unidades de Q (m³/s)", abs(q_mm_dia / q_publicado - 1) <= TOLERANCIA_UNIDADES,
          f"encabezado '{columnas_originales[-1]}' sin unidad; el caudal medio del archivo ({crudo.caudal.mean():.1f} m³/s) "
          f"equivale a {q_mm_dia:.2f} mm/día sobre los {miles(area_camels)} km² de CAMELS-COL, y su archivo de firmas publica "
          f"{q_publicado:.2f} mm/día: las unidades son m³/s")
registrar(F, "banderas de calidad", NO_DISPONIBLE,
          "el archivo no trae banderas ni el nivel de aprobación del IDEAM, y el artículo de CAMELS-COL no describe "
          "control de calidad ni relleno del caudal")

# ====================================================================== DHIME (pluviómetros, PL)
F = "DHIME (pluviómetros, PL)"
catalogo = pd.read_csv(RAIZ / "out/pluviometros_fonce_catalogo.csv").set_index("codigo")
DENTRO = catalogo.index[catalogo.dentro_cuenca].tolist()
with zipfile.ZipFile(RAIZ / "data/ideam/pluviometros/dhime/dhime_mensual_1998_2022_8est.zip") as z:
    bruto = z.read(z.namelist()[0])
for codificacion in ("utf-8", "latin-1"):           # misma lógica que 07_pluviometros_dhime.py
    try:
        texto = bruto.decode(codificacion)
    except UnicodeDecodeError:
        continue
    if "Ã" not in texto:
        break
dh = pd.read_csv(io.StringIO(texto))
dh["fecha"] = pd.to_datetime(dh["Fecha"], errors="coerce")
dh = dh[dh.CodigoEstacion.isin(DENTRO)]
registrar(F, "fechas legibles y en el día 1 del mes", bool(dh.fecha.notna().all() and (dh.fecha.dt.day == 1).all()),
          f"{miles(len(dh))} registros de {dh.CodigoEstacion.nunique()} pluviómetros dentro de la cuenca, de "
          f"{dh.fecha.min():%Y-%m} a {dh.fecha.max():%Y-%m}")
n_dup = int(dh.duplicated(["CodigoEstacion", "fecha"]).sum())
registrar(F, "registros duplicados (estación y mes)", n_dup == 0, f"{n_dup} repetidos")
unidades = sorted(dh.Unidad.unique())
parametros = sorted(dh.Parametro.unique())
registrar(F, "unidades y variable", unidades == ["mm"] and len(parametros) == 1,
          f"unidad: {', '.join(unidades)}; parámetro: {', '.join(parametros)}")
n_cod = codigos_faltante(dh.Valor)
registrar(F, "códigos de faltante y vacíos", n_cod == 0 and dh.Valor.notna().all(),
          f"{n_cod} códigos de faltante, {int(dh.Valor.isna().sum())} vacíos; los meses sin dato simplemente no aparecen")
registrar(F, "P ≥ 0", bool((dh.Valor >= 0).all()),
          f"{int((dh.Valor < 0).sum())} negativos; máximo {dh.Valor.max():.1f} mm en un mes")
ceros = dh[dh.Valor == 0]
registrar(F, "meses con 0 mm", False if len(ceros) else True,
          (f"{len(ceros)} meses con lluvia exactamente 0: "
           + "; ".join(f"{catalogo.loc[c, 'nombre'].split(' [')[0].title().replace(' De ', ' de ')} {f:%Y-%m}"
                       for c, f in zip(ceros.CodigoEstacion, ceros.fecha))
           + ". Son posibles en un mes seco, pero en esta cuenca húmeda hay que revisarlos contra los pluviómetros vecinos") if len(ceros) else "ninguno")
niveles = dh.NivelAprobacion.value_counts()
por_est = (dh.assign(pre=dh.NivelAprobacion.eq("Preliminar")).groupby("CodigoEstacion").pre.mean() * 100)
registrar(F, "banderas: nivel de aprobación del IDEAM", ANOTADO if niveles.get("Preliminar", 0) else True,
          f"{miles(niveles.get('Preliminar', 0))} registros preliminares y {niveles.get('Definitivo', 0)} definitivos "
          f"({niveles.get('Preliminar', 0) / len(dh) * 100:.0f} % preliminar); por estación, entre "
          f"{por_est.min():.0f} % y {por_est.max():.0f} % preliminar. 'Preliminar' quiere decir que el IDEAM aún no "
          f"validó el dato; no es una marca de error")

# ====================================================================== IMERG (PI)
F = "IMERG Final V07 (PI)"
I0, J0 = 1004, 853                                   # índices del recorte, como en 04_imerg_descarga_mensual.py
archivos = {m: RAIZ / f"data/imerg/mensual/{m.year}{m.month:02d}.txt" for m in MESES}
faltan = [str(m) for m, p in archivos.items() if not p.exists()]
registrar(F, "un archivo por mes, 1998-2022", not faltan, f"{len(MESES) - len(faltan)} de {len(MESES)} archivos" + (f"; faltan {faltan}" if faltan else ""))
versiones = {p.read_text().splitlines()[0].split(".")[-2] for p in archivos.values() if p.exists()}
registrar(F, "versión del producto", versiones == {"V07B"}, f"versiones en los encabezados: {', '.join(sorted(versiones))}")


def leer_imerg(ruta):
    """Matriz lon x lat en mm/h, tal como viene en el texto de OPeNDAP."""
    filas_txt = [l for l in ruta.read_text().splitlines() if l.startswith("precipitation[")]
    return np.array([[float(x) for x in l.split(",", 1)[1].split(",")] for l in filas_txt])


# los píxeles que tocan la cuenca y su peso: exactamente el cálculo de 05_imerg_mensual_cuencas.py
z = np.load(RAIZ / "data/imerg/imerg_mensual_col.npz", allow_pickle=True)
LON, LAT = z["lon"], z["lat"]
g = gpd.read_file(RAIZ / "data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/CAMELS_COL_catchments_boundaries.shp",
                  where=f"IDEAM_CODE IN ('{ID_PRINCIPAL}')").to_crs(4326)
poly = shapely.simplify(g.geometry.iloc[0], 0.002)
minx, miny, maxx, maxy = poly.bounds
ii = np.flatnonzero((LON + .05 > minx) & (LON - .05 < maxx))
jj = np.flatnonzero((LAT + .05 > miny) & (LAT - .05 < maxy))
I, J = np.meshgrid(ii, jj, indexing="ij")
w = shapely.area(shapely.intersection(poly, shapely.box(LON[I] - .05, LAT[J] - .05, LON[I] + .05, LAT[J] + .05)))
w = w / w.sum()
dentro = w > 0

n_relleno = n_neg = 0
dif_conversion = 0.0
for m, ruta in archivos.items():
    v = leer_imerg(ruta)[I, J]                        # mm/h en los píxeles del rectángulo de la cuenca
    n_relleno += int((v[dentro] < -9000).sum())
    n_neg += int(((v[dentro] < 0) & (v[dentro] > -9000)).sum())
    horas = calendar.monthrange(m.year, m.month)[1] * 24
    dif_conversion = max(dif_conversion, float(np.nanmax(np.abs(v * horas - z["precip_mm_mes"][MESES.get_loc(m)][I, J]))))
registrar(F, "códigos de faltante (−9999.9) en los píxeles de la cuenca", n_relleno == 0,
          f"{n_relleno} casos en {int(dentro.sum())} píxeles × {len(MESES)} meses")
registrar(F, "P ≥ 0", n_neg == 0, f"{n_neg} valores negativos")
registrar(F, "unidades: mm/h a mm/mes", dif_conversion < 0.01,
          f"el producto entrega la tasa media del mes en mm/h; multiplicada por las horas del mes reproduce el "
          f"archivo empaquetado (diferencia máxima {dif_conversion:.4f} mm)")
registrar(F, "banderas de calidad", NO_DISPONIBLE,
          "la descarga trae solo la variable 'precipitation'; el producto trae además variables de error y del peso "
          "de los pluviómetros en la estimación (randomError, gaugeRelativeWeighting) que no se descargaron")

# el mes revisado a mano: cada píxel con su valor crudo, su conversión y su peso
v = leer_imerg(archivos[MES_REVISADO])[I, J]
horas = calendar.monthrange(MES_REVISADO.year, MES_REVISADO.month)[1] * 24
pixeles = pd.DataFrame({"lon": LON[I][dentro].round(2), "lat": LAT[J][dentro].round(2),
                        "mm_por_hora": v[dentro], "horas_del_mes": horas,
                        "mm_en_el_mes": v[dentro] * horas, "peso": w[dentro]})
pixeles.to_csv(RAIZ / "out/control_calidad_pi_mes_revisado.csv", index=False)

# ====================================================================== ERA5-Land (temperatura)
F = "ERA5-Land (temperatura)"
anuales = sorted((RAIZ / "data/era5land_gee").glob("t2m_*.csv"))
era = pd.concat([pd.read_csv(p) for p in anuales], ignore_index=True)
era["fecha"] = pd.to_datetime(era.fecha, errors="coerce")
registrar(F, "fechas legibles, en orden y sin duplicados",
          bool(era.fecha.notna().all() and era.fecha.is_monotonic_increasing and not era.fecha.duplicated().any()),
          f"{len(anuales)} archivos, {miles(len(era))} días; {int(era.fecha.duplicated().sum())} fechas repetidas")
n_aus = len(DIAS.difference(era.fecha))
registrar(F, "días ausentes en 1998-2022", n_aus == 0, f"{n_aus} días sin dato")
T = era[["t_media", "t_min", "t_max"]]
fuera = int(((T < T_MIN_PLAUSIBLE) | (T > T_MAX_PLAUSIBLE)).sum().sum())
registrar(F, f"unidades (°C) y rango físico ({T_MIN_PLAUSIBLE:.0f} a {T_MAX_PLAUSIBLE:.0f} °C)", fuera == 0 and int(T.isna().sum().sum()) == 0,
          f"entre {T.min().min():.1f} y {T.max().max():.1f} °C: ya en grados Celsius (en kelvin estarían cerca de 290); "
          f"{fuera} valores fuera de rango, {int(T.isna().sum().sum())} vacíos")
n_orden = int(((era.t_min > era.t_media) | (era.t_media > era.t_max)).sum())
registrar(F, "T mín ≤ T media ≤ T máx", n_orden == 0, f"{n_orden} días que no cumplen")
registrar(F, "banderas de calidad", NO_DISPONIBLE, "un reanálisis no trae banderas: da un valor para todos los días por construcción")

# ====================================================================== ETP de Hargreaves (ERA5-Land)
F = "ETP (Hargreaves con ERA5-Land)"
etp = pd.read_csv(RAIZ / "out/etp_hargreaves_fonce.csv", parse_dates=["fecha"]).set_index("fecha")["etp_era5land"]
registrar(F, "días completos y ETP ≥ 0", bool(etp.notna().all() and (etp >= 0).all() and len(etp) == len(DIAS)),
          f"{miles(etp.notna().sum())} días con valor, {int((etp < 0).sum())} negativos; entre {etp.min():.2f} y {etp.max():.2f} mm/día")

salida = pd.DataFrame(filas)
salida.to_csv(RAIZ / "out/control_calidad_basico.csv", index=False)

# ====================================================================== qué es cada dato
# Tabla declarada, con las cifras calculadas arriba: si cada variable es medida, estimada, simulada o
# calculada, y si tiene valores rellenados o reconstruidos. Las afirmaciones sobre cómo se construye cada
# producto vienen de su documentación (DATOS_FUENTES.md).
naturaleza = pd.DataFrame([
    {"variable": "Q", "fuente": "IDEAM, vía CAMELS-COL",
     "tipo": "observado",
     "cómo se obtiene": "el IDEAM registra el nivel del río en la estación y lo convierte en caudal con la curva de "
                        "gasto de la estación, como en toda estación hidrométrica; la curva no viene en CAMELS-COL",
     "relleno": f"no se ve relleno: los días sin dato faltan ({n_ausentes} en 1998-2022) y CAMELS-COL no describe ninguno"},
    {"variable": "PL", "fuente": "IDEAM, portal DHIME",
     "tipo": "observado",
     "cómo se obtiene": f"total mensual de cada pluviómetro, calculado por el IDEAM; {niveles.get('Preliminar', 0) / len(dh) * 100:.0f} % "
                        "de los registros son preliminares",
     "relleno": "no se sabe con cuántos días se armó cada total mensual; los meses sin dato no aparecen; el "
                "proyecto excluyó Encino 2016-2018"},
    {"variable": "PI", "fuente": "NASA, IMERG Final V07",
     "tipo": "estimado",
     "cómo se obtiene": "estimación satelital (sensores de microondas e infrarrojo) ajustada mes a mes con "
                        "pluviómetros (análisis del GPCC), en malla de 0.1° (Huffman et al., 2023)",
     "relleno": "completo por construcción: el producto da un valor en cada celda y cada mes"},
    {"variable": "T", "fuente": "ECMWF, ERA5-Land",
     "tipo": "simulado",
     "cómo se obtiene": "reanálisis: un modelo de superficie terrestre forzado con el reanálisis ERA5, en malla "
                        "de 0.1° (Muñoz-Sabater et al.)",
     "relleno": "completo por construcción: no hay huecos que rellenar"},
    {"variable": "ETP", "fuente": "el proyecto (06b_etp_hargreaves.py)",
     "tipo": "calculado",
     "cómo se obtiene": "fórmula de Hargreaves y Samani (1985) con la temperatura de ERA5-Land",
     "relleno": "completa, porque ERA5-Land lo es"},
])
naturaleza.to_csv(RAIZ / "out/naturaleza_fuentes.csv", index=False)
print(salida.resultado.value_counts().to_string())
print(salida[salida.resultado != "sin problemas"][["fuente", "chequeo", "resultado"]].to_string(index=False))
print(f"\nmes revisado {MES_REVISADO}: {len(pixeles)} píxeles de IMERG; PI = {(pixeles.mm_en_el_mes * pixeles.peso).sum():.2f} mm")
