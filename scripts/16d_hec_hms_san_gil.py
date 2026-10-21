"""Modelo continuo de HEC-HMS para San Gil, a paso diario, con la lluvia diaria de CAMELS-COL (CHIRPS), y su calibración.

HEC-HMS (Hydrologic Engineering Center, Cuerpo de Ingenieros del Ejército de EE. UU.) es un programa que transforma la
lluvia en caudal. Aquí se usa en su modo continuo: el método de pérdidas "Soil Moisture Accounting" (SMA, en el
programa "Soil Moisture Account") lleva la cuenta del agua guardada en cinco depósitos (dosel, superficie, suelo y dos
capas de agua subterránea) día tras día, y con eso decide cuánta lluvia se vuelve caudal y cuánta se evapora.

El script arma el modelo, lo corre con valores de partida (sin calibrar), lo calibra y lo valida:
  - Calibrar es buscar los valores de los parámetros con los que el Q simulado se parece más al Q medido. Lo hace un
    optimizador (evolución diferencial, de scipy) que corre HEC-HMS cientos de veces con distintos valores.
  - El parecido se mide con el KGE (Gupta et al., 2009, el mismo del informe) del Q diario en el período de
    calibración. Se busca el mayor KGE.
  - Validar es medir el modelo calibrado en un período que el optimizador no vio. Si ahí también acierta, el modelo
    representa a la cuenca; si solo acierta en calibración, se aprendió esos años de memoria.

Decisiones y supuestos (decididos por el usuario el 2026-10-21, salvo donde se dice otra cosa):
  1. Lluvia: la columna `Precipitacion` de CAMELS-COL para San Gil, que es CHIRPS v2.0 promediado sobre la cuenca
     (ver DATOS_FUENTES.md). Es una tercera fuente, distinta de PI y PL: HEC-HMS necesita lluvia diaria, y PI y PL
     solo están en el proyecto a escala mensual.
  2. Ventana: el tramo continuo más largo de 1998-2022 en que CAMELS-COL tiene lluvia y caudal todos los días. Al
     archivo le faltan días como filas ausentes (sin lluvia ni caudal), y HEC-HMS no puede correr con lluvia
     faltante; los días faltantes no se rellenan (regla 1), así que el modelo corre solo en ese tramo. El tramo se
     busca en el código, no se escribe a mano.
  3. Períodos dentro del tramo: los primeros DIAS_CALENTAMIENTO días no se evalúan (los depósitos arrancan con un
     contenido supuesto y necesitan tiempo para acomodarse); después, calibración hasta FIN_CALIBRACION y validación
     desde el día siguiente hasta el final del tramo.
  4. Calibración con el KGE del Q diario (el agente recomendaba el mensual, para comparar con M4 y M5).
  5. ETP: la de Hargreaves con ERA5-Land del proyecto (regla 15), `out/etp_hargreaves_fonce.csv`, entregada a
     HEC-HMS como el promedio de cada mes del año (método "Monthly Evaporation"), con coeficiente 1. En la cuenca la
     ETP mensual cambia poco de un mes a otro, así que se pierde poco frente a darla día a día.
  6. Área: la del polígono del proyecto (regla 13), `out/shp_fonce/areas_cuencas.csv`.
  7. Una sola subcuenca: toda la cuenca de San Gil como un solo elemento (sin subdividir ni tránsito por cauces).
  8. Transformación de Clark (cómo se reparte en el tiempo la lluvia que se vuelve escorrentía). El tiempo de
     concentración de Kirpich con la pendiente medida por el proyecto (`out/tiempos_concentracion.csv`, script 13)
     es de unas 10 horas, menos que un paso de 24 horas: a paso diario el agua de un día sale casi toda ese mismo
     día. HEC-HMS no acepta un tiempo de concentración menor que un paso, así que se usa el mayor entre Kirpich y
     un paso. El coeficiente de almacenamiento se fija en un paso: con menos, HEC-HMS lo sube a medio paso y el
     hidrograma unitario pierde una cuarta parte de su volumen (comprobado: 0.75 mm en vez de 1 mm).
  9. Los valores de partida (PARAMETROS_INICIALES) y los rangos en que busca el optimizador (RANGOS_CALIBRACION) los
     puso el agente: no salen de los datos. Los rangos son amplios a propósito, para que decidan los datos. Los
     parámetros que no se calibran se quedan en su valor de partida.
 10. Los coeficientes de los dos embalses lineales del flujo base se igualan a los de las capas subterráneas que
     vacían, para no agregar dos parámetros más que el KGE no alcanza a distinguir.

HEC-HMS: versión HMS_VERSION para Linux. Si la variable de entorno HEC_HMS_HOME apunta a una instalación, se usa esa;
si no, se descarga una sola vez (unos 340 MB) a ~/.cache/hec-hms y se comprueba su SHA-256. El programa corre sin
ventana, con un guion de Jython (el Python que trae HEC-HMS) que este script escribe y le pasa. La calibración tarda
unos 15 minutos.

Salidas:
  out/hec_hms_san_gil/                   el proyecto de HEC-HMS, con los parámetros calibrados; se abre con la
                                         interfaz del programa
  out/hec_hms_san_gil_diario.csv         fecha, lluvia, Q observado, Q simulado sin calibrar y calibrado (m³/s), período
  out/hec_hms_san_gil_parametros.csv     cada parámetro: valor de partida, rango de búsqueda y valor calibrado
  out/hec_hms_san_gil_metricas.csv       NSE, KGE, r y sesgo por corrida, período y escala (diaria y mensual)
"""
import hashlib
import os
import shutil
import subprocess
import tarfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

RAIZ = Path(__file__).resolve().parent.parent
ID_PRINCIPAL = "24027010"                  # San Gil
ANIOS_ESTUDIO = (1998, 2022)               # período común del proyecto (regla 6)
DIAS_CALENTAMIENTO = 365                   # días al comienzo que no se evalúan (supuesto 3)
FIN_CALIBRACION = "2019-12-31"             # calibración hasta aquí; validación desde el día siguiente (supuesto 3)
MAX_DIAS_FALTANTES = 4                     # regla 5: un mes con 5 o más días faltantes queda vacío
PASO_H = 24.0                              # paso de cálculo de HEC-HMS: un día
SEMILLA = 2026                             # semilla del optimizador, para que la calibración se repita igual

HMS_VERSION = "4.13"
HMS_URL = ("https://github.com/HydrologicEngineeringCenter/hec-downloads/releases/download/1.0.38/"
           "HEC-HMS-4.13-linux64.tar.gz")
HMS_SHA256 = "379c087ce9e374cfa8095139bc92e648824392973ec4ca428615f85c9724a163"

CARPETA_PROYECTO = RAIZ / "out/hec_hms_san_gil"
NOMBRE_PROYECTO = "fonce_san_gil"
NOMBRE_CUENCA = "San Gil"                  # modelo de cuenca (basin model) de HEC-HMS
NOMBRE_SUBCUENCA = "Cuenca San Gil"        # sin tildes: son nombres internos de HEC-HMS
NOMBRE_SALIDA = "Salida San Gil"           # nodo (junction) donde se compara con Q
NOMBRE_METEO = "CHIRPS CAMELS"
NOMBRE_CONTROL = "Tramo continuo"
NOMBRE_CORRIDA = "San Gil diario"
ARCHIVO_CORRIDA = NOMBRE_CORRIDA.replace(" ", "_")   # así nombra HEC-HMS los archivos de la corrida
ARCHIVO_DSS = f"{NOMBRE_PROYECTO}.dss"
RUTA_DSS_LLUVIA = "/FONCE/SAN GIL/PRECIP-INC//1DAY/CAMELS-CHIRPS/"
RUTA_DSS_CAUDAL = "/FONCE/SAN GIL/FLOW//1DAY/CAMELS-OBS/"

# Valores de partida, NO calibrados (supuesto 9). Unidades del sistema métrico de HEC-HMS: mm, mm/h y horas.
PARAMETROS_INICIALES = {
    "dosel_almacenamiento_mm": 3.0,              # agua que retienen las hojas antes de llegar al suelo
    "superficie_almacenamiento_mm": 5.0,         # charcos y depresiones
    "suelo_infiltracion_max_mm_h": 10.0,
    "suelo_almacenamiento_mm": 200.0,
    "suelo_fraccion_tension": 0.6,               # parte del suelo que solo sale por evapotranspiración
    "suelo_percolacion_max_mm_h": 2.0,
    "subterranea1_almacenamiento_mm": 60.0,
    "subterranea1_coef_h": 240.0,                # ~10 días
    "subterranea1_percolacion_max_mm_h": 1.0,
    "subterranea2_almacenamiento_mm": 200.0,
    "subterranea2_coef_h": 1200.0,               # ~50 días
    "subterranea2_percolacion_max_mm_h": 0.0,    # 0: el modelo no pierde agua hacia acuíferos profundos
    "suelo_inicial_pct": 50.0,
    "subterranea1_inicial_pct": 50.0,
    "subterranea2_inicial_pct": 50.0,
}

# Los parámetros que se calibran y el rango en que se buscan (supuesto 9)
RANGOS_CALIBRACION = {
    "suelo_infiltracion_max_mm_h": (1.0, 50.0),
    "suelo_almacenamiento_mm": (50.0, 600.0),
    "suelo_fraccion_tension": (0.1, 0.95),
    "suelo_percolacion_max_mm_h": (0.05, 10.0),
    "subterranea1_coef_h": (24.0, 720.0),        # 1 a 30 días
    "subterranea1_percolacion_max_mm_h": (0.0, 5.0),
    "subterranea2_coef_h": (240.0, 6000.0),      # 10 a 250 días
}
TAMANO_POBLACION = 8                         # por cada parámetro calibrado: 8 x 7 = 56 juegos por generación
GENERACIONES_MAX = 30


# ------------------------------------------------------------------ 1. HEC-HMS: instalación
def carpeta_hec_hms():
    """Devuelve la carpeta de HEC-HMS; si no hay instalación indicada, descarga la versión de Linux una sola vez."""
    if os.environ.get("HEC_HMS_HOME"):
        return Path(os.environ["HEC_HMS_HOME"])
    cache = Path.home() / ".cache/hec-hms"
    carpeta = cache / f"HEC-HMS-{HMS_VERSION}"
    if (carpeta / "hms.jar").exists():
        return carpeta
    cache.mkdir(parents=True, exist_ok=True)
    archivo = cache / Path(HMS_URL).name
    if not archivo.exists():
        print(f"Descargando HEC-HMS {HMS_VERSION} (unos 340 MB)…")
        urllib.request.urlretrieve(HMS_URL, archivo)
    sha = hashlib.sha256(archivo.read_bytes()).hexdigest()
    if sha != HMS_SHA256:
        raise RuntimeError(f"El SHA-256 de {archivo} no coincide: {sha}")
    with tarfile.open(archivo) as tar:
        tar.extractall(cache)
    return carpeta


# ------------------------------------------------------------------ 2. datos diarios de CAMELS-COL
cam = pd.read_csv(RAIZ / f"data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_{ID_PRINCIPAL}.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam["fecha"], format="%d/%m/%Y")
cam = cam.set_index("fecha").sort_index()
cam = cam.loc[f"{ANIOS_ESTUDIO[0]}-01-01":f"{ANIOS_ESTUDIO[1]}-12-31"]

# Tramo continuo más largo con lluvia y caudal todos los días (supuesto 2)
con_dato = cam.dropna(subset=["p_chirps", "caudal"]).index
numero_tramo = (con_dato.to_series().diff() != pd.Timedelta(days=1)).cumsum()
tramos = con_dato.to_series().groupby(numero_tramo.values).agg(["min", "max", "count"])
tramo = tramos.loc[tramos["count"].idxmax()]
inicio, fin = tramo["min"], tramo["max"]
datos = cam.loc[inicio:fin, ["p_chirps", "caudal"]]
assert len(datos) == (fin - inicio).days + 1 and datos.notna().all().all(), "el tramo tiene días sin dato"
print(f"Tramo continuo: {inicio:%Y-%m-%d} a {fin:%Y-%m-%d} ({len(datos)} días); "
      f"{len(tramos)} tramos en {ANIOS_ESTUDIO[0]}-{ANIOS_ESTUDIO[1]}")

# Períodos dentro del tramo (supuesto 3)
periodo = pd.Series("calentamiento", index=datos.index)
inicio_evaluacion = datos.index[DIAS_CALENTAMIENTO]
periodo[inicio_evaluacion:FIN_CALIBRACION] = "calibración"
periodo[pd.Timestamp(FIN_CALIBRACION) + pd.Timedelta(days=1):] = "validación"
assert inicio_evaluacion < pd.Timestamp(FIN_CALIBRACION) < fin

# Área del polígono (regla 13) y tiempo de concentración de Kirpich con la pendiente medida (supuesto 8)
area_km2 = float(pd.read_csv(RAIZ / "out/shp_fonce/areas_cuencas.csv", dtype={"gauge_id": str})
                 .set_index("gauge_id").loc[ID_PRINCIPAL, "area_km2"])
tc_h = float(pd.read_csv(RAIZ / "out/tiempos_concentracion.csv")
             .set_index("formula").loc["Kirpich", "con_pendiente_medida_h"])

# ETP mensual promedio de cada mes del año, 1998-2022 (supuesto 5)
etp = pd.read_csv(RAIZ / "out/etp_hargreaves_fonce.csv", parse_dates=["fecha"]).set_index("fecha")["etp_era5land"]
etp_mensual = etp.resample("MS").sum()
etp_climatologia = etp_mensual.groupby(etp_mensual.index.month).mean()
assert len(etp_climatologia) == 12


# ------------------------------------------------------------------ 3. archivos del proyecto de HEC-HMS
def bloque(encabezado, campos):
    """Un bloque de texto de HEC-HMS: 'Encabezado: nombre', una línea por campo y 'End:'."""
    lineas = [encabezado] + [f"     {clave}: {valor}" for clave, valor in campos]
    return "\n".join(lineas) + "\nEnd:\n\n"


def fecha_hms(dia):
    return f"{dia.day} {dia.strftime('%B')} {dia.year}"


def texto_cuenca(p):
    """El modelo de cuenca (archivo .basin) con los parámetros del diccionario p."""
    return (
        bloque(f"Basin: {NOMBRE_CUENCA}", [
            ("Version", HMS_VERSION), ("Filepath Separator", "\\"), ("Unit System", "Metric"),
            ("Missing Flow To Zero", "No"), ("Enable Flow Ratio", "No"),
            ("Compute Local Flow At Junctions", "No"), ("Unregulated Output Required", "No")])
        + bloque(f"Subbasin: {NOMBRE_SUBCUENCA}", [
            ("Canvas X", "0.0"), ("Canvas Y", "100.0"), ("Area", f"{area_km2:.2f}"), ("Downstream", NOMBRE_SALIDA),
            ("Discretization", "None"),
            ("Canopy", "Simple"),
            # A paso diario casi todos los días tienen algo de lluvia; si se prohíbe evaporar mientras llueve
            # (la opción por defecto), el modelo casi no evapotranspira y devuelve como caudal agua que se evapora.
            ("Allow Simultaneous Precip Et", "Yes"),
            ("Plant Uptake Method", "Default Tension-Factor"), ("Initial Canopy Storage Percent", "0"),
            ("Canopy Storage Capacity", p["dosel_almacenamiento_mm"]), ("Crop Coefficient", "1.0"),
            ("End Canopy", ""),
            ("Surface", "Simple"), ("Initial Surface Storage Percent", "0"),
            ("Surface Storage Capacity", p["superficie_almacenamiento_mm"]), ("Surface Albedo", "0.20"),
            ("End Surface", ""),
            ("LossRate", "Soil Moisture Account"), ("Percent Impervious Area", "0.0"),
            ("Initial Soil Storage Percent", p["suelo_inicial_pct"]),
            ("Initial Gw1 Storage Percent", p["subterranea1_inicial_pct"]),
            ("Initial Gw2 Storage Percent", p["subterranea2_inicial_pct"]),
            ("Soil Maximum Infiltration", f"{p['suelo_infiltracion_max_mm_h']:.4f}"),
            ("Soil Storage Capacity", f"{p['suelo_almacenamiento_mm']:.4f}"),
            ("Soil Tension Capacity", f"{p['suelo_almacenamiento_mm'] * p['suelo_fraccion_tension']:.4f}"),
            ("Soil Maximum Percolation", f"{p['suelo_percolacion_max_mm_h']:.4f}"),
            ("Groundwater 1 Storage Capacity", p["subterranea1_almacenamiento_mm"]),
            ("Groundwater 1 Routing Coefficient", f"{p['subterranea1_coef_h']:.4f}"),
            ("Groundwater 1 Maximum Percolation", f"{p['subterranea1_percolacion_max_mm_h']:.4f}"),
            ("Groundwater 2 Storage Capacity", p["subterranea2_almacenamiento_mm"]),
            ("Groundwater 2 Routing Coefficient", f"{p['subterranea2_coef_h']:.4f}"),
            ("Groundwater 2 Maximum Percolation", p["subterranea2_percolacion_max_mm_h"]),
            ("Transform", "Clark"), ("Clark Method", "Specified"),
            ("Time of Concentration", f"{max(tc_h, PASO_H):.2f}"), ("Storage Coefficient", f"{PASO_H:.2f}"),
            ("Time Area Method", "Default"),
            # Embalses lineales del flujo base con el mismo coeficiente que la capa que vacían (supuesto 10)
            ("Baseflow", "Linear Reservoir"),
            ("Groundwater Layer", "1"), ("GW-1 Number Reservoirs", "1"),
            ("GW-1 Routing Coefficient", f"{p['subterranea1_coef_h']:.4f}"), ("GW-1 Initial Baseflow", "0.0"),
            ("Groundwater Layer", "2"), ("GW-2 Number Reservoirs", "1"),
            ("GW-2 Routing Coefficient", f"{p['subterranea2_coef_h']:.4f}"), ("GW-2 Initial Baseflow", "0.0")])
        + bloque(f"Junction: {NOMBRE_SALIDA}", [
            ("Canvas X", "0.0"), ("Canvas Y", "0.0"), ("Computation Point", "Yes"),
            ("Observed Hydrograph Gage", "Q San Gil")]))


if CARPETA_PROYECTO.exists():
    shutil.rmtree(CARPETA_PROYECTO)            # el proyecto se rehace completo en cada corrida
CARPETA_PROYECTO.mkdir(parents=True)
(CARPETA_PROYECTO / "lotes").mkdir()

textos = {
    f"{NOMBRE_PROYECTO}.hms":
        bloque(f"Project: {NOMBRE_PROYECTO}", [
            ("Description", "Fonce en San Gil (IDEAM 24027010), modelo continuo diario"),
            ("Version", HMS_VERSION), ("Filepath Separator", "\\"),
            ("DSS File Name", ARCHIVO_DSS), ("Time Zone ID", "America/Bogota")])
        + bloque(f"Precipitation: {NOMBRE_METEO}", [("Filename", "chirps_camels.met"), ("Description", "")])
        + bloque(f"Basin: {NOMBRE_CUENCA}", [("Filename", "san_gil.basin"), ("Description", "")])
        + bloque(f"Control: {NOMBRE_CONTROL}", [("FileName", "tramo_continuo.control"), ("Description", "")]),

    "san_gil.basin": texto_cuenca(PARAMETROS_INICIALES),

    "chirps_camels.met":
        bloque(f"Meteorology: {NOMBRE_METEO}", [
            ("Version", HMS_VERSION), ("Unit System", "Metric"), ("Set Missing Data to Default", "No"),
            ("Precipitation Method", "Specified Average"), ("Air Temperature Method", "None"),
            ("Atmospheric Pressure Method", "None"), ("Dew Point Method", "None"), ("Wind Speed Method", "None"),
            ("Shortwave Radiation Method", "None"), ("Longwave Radiation Method", "None"),
            ("Snowmelt Method", "None"), ("Evapotranspiration Method", "Monthly Evaporation"),
            ("Use Basin Model", NOMBRE_CUENCA)])
        + bloque("Precip Method Parameters: Specified Average", [("Allow Depth Override", "Yes")])
        + bloque("Evapotranspiration Method Parameters: Monthly Evaporation", [])
        + bloque(f"Subbasin: {NOMBRE_SUBCUENCA}", [("Gage", "P San Gil"), ("Begin Et", "Monthly Evaporation")]
                 + [("Pan Evaporation", f"{v:.2f}") for v in etp_climatologia]
                 + [("Evapotranspiration Coefficient", "1.0")] * 12 + [("End Et", "")]),

    "tramo_continuo.control":
        bloque(f"Control: {NOMBRE_CONTROL}", [
            ("Version", HMS_VERSION),
            # Los valores diarios se guardan al final de cada día (24:00), así que la corrida arranca a las 00:00
            # del primer día y termina a las 24:00 del último.
            ("Start Date", fecha_hms(inicio)), ("Start Time", "00:00"),
            ("End Date", fecha_hms(fin)), ("End Time", "24:00"), ("Time Interval", f"{PASO_H * 60:.0f}")]),

    f"{NOMBRE_PROYECTO}.gage":
        bloque(f"Gage Manager: {NOMBRE_PROYECTO}", [("Version", HMS_VERSION), ("Filepath Separator", "\\")])
        + bloque("Gage: P San Gil", [
            ("Gage Type", "Precipitation"), ("Data Source Type", "External DSS"),
            ("Filename", ARCHIVO_DSS), ("Pathname", RUTA_DSS_LLUVIA)])
        + bloque("Gage: Q San Gil", [
            ("Gage Type", "Flow"), ("Data Source Type", "External DSS"),
            ("Filename", ARCHIVO_DSS), ("Pathname", RUTA_DSS_CAUDAL)]),

    f"{NOMBRE_PROYECTO}.run":
        bloque(f"Run: {NOMBRE_CORRIDA}", [
            ("Log File", f"{ARCHIVO_CORRIDA}.log"), ("DSS File", f"{ARCHIVO_CORRIDA}.dss"), ("Basin", NOMBRE_CUENCA),
            ("Precip", NOMBRE_METEO), ("Control", NOMBRE_CONTROL), ("Save State Type", "None"),
            ("Time-Series Output", "Save All")]),
}
for nombre, texto in textos.items():
    (CARPETA_PROYECTO / nombre).write_text(texto, encoding="utf-8")

# Las series diarias pasan a HEC-HMS en un archivo DSS, que escribe el guion de Jython. DSS cuenta el tiempo en
# minutos desde el 31 de diciembre de 1899 a las 00:00, y cada valor diario se fecha al final de su día (24:00).
ORIGEN_DSS = datetime(1899, 12, 31)
minutos = [int((dia + timedelta(days=1) - ORIGEN_DSS).total_seconds() // 60) for dia in datos.index]
pd.DataFrame({"minutos": minutos, "lluvia_mm": datos["p_chirps"].values, "caudal_m3s": datos["caudal"].values}) \
    .to_csv(CARPETA_PROYECTO / "series_entrada.csv", index=False)

# Guion de Jython: escribe el DSS de entrada (la primera vez) y corre un lote de modelos de cuenca, uno tras otro, en
# un solo arranque de HEC-HMS. Para cada uno copia su .basin sobre san_gil.basin, corre y exporta el Q simulado.
# Correr en lotes es lo que hace viable la calibración: arrancar HEC-HMS tarda unos 5 s y una corrida, menos de 1 s.
GUION_JYTHON = f'''# Guion de Jython que corre dentro de HEC-HMS; lo escribe scripts/16d_hec_hms_san_gil.py
import os
import shutil
from hec.heclib.dss import HecDss
from hec.io import TimeSeriesContainer
from hms.model import Project
from hms import Hms

carpeta = r"{CARPETA_PROYECTO}"
archivo_dss = carpeta + "/{ARCHIVO_DSS}"

if not os.path.exists(archivo_dss):
    filas = [linea.strip().split(",") for linea in open(carpeta + "/series_entrada.csv").readlines()[1:]]
    tiempos = [int(f[0]) for f in filas]
    dss = HecDss.open(archivo_dss)
    for ruta, columna, unidades, tipo in [("{RUTA_DSS_LLUVIA}", 1, "MM", "PER-CUM"),
                                          ("{RUTA_DSS_CAUDAL}", 2, "M3/S", "PER-AVER")]:
        serie = TimeSeriesContainer()
        serie.fullName = ruta
        serie.times = tiempos
        serie.values = [float(f[columna]) for f in filas]
        serie.numberValues = len(filas)
        serie.units = unidades
        serie.type = tipo
        dss.put(serie)
    dss.close()

lote = [linea.strip().split(",") for linea in open(carpeta + "/lotes/lote.txt").readlines()]
for archivo_cuenca, archivo_salida in lote:
    shutil.copy(archivo_cuenca, carpeta + "/san_gil.basin")
    proyecto = Project.open(carpeta + "/{NOMBRE_PROYECTO}.hms")
    proyecto.computeRun("{NOMBRE_CORRIDA}")
    proyecto.close()
    dss = HecDss.open(carpeta + "/{ARCHIVO_CORRIDA}.dss")
    rutas = [r for r in dss.getCatalogedPathnames() if r.split("/")[2] == "{NOMBRE_SALIDA}"
             and r.split("/")[3] == "FLOW"]
    serie = dss.get(rutas[0], True)
    salida = open(archivo_salida, "w")
    salida.write("minutos,caudal_simulado_m3s\\n")
    for t, v in zip(serie.times, serie.values):
        salida.write("%d,%.6f\\n" % (t, v))
    salida.close()
    dss.close()
Hms.shutdownEngine()
'''
(CARPETA_PROYECTO / "correr_lote.py").write_text(GUION_JYTHON, encoding="utf-8")


# ------------------------------------------------------------------ 4. correr HEC-HMS sin ventana
hms = carpeta_hec_hms()
java = hms / "jre/bin" / ("java.exe" if os.name == "nt" else "java")
clases = os.pathsep.join(str(hms / c) for c in ("*", "lib/*", "lib/hec/*"))
librerias = os.pathsep.join(str(hms / c) for c in ("bin", "bin/gdal"))
entorno = dict(os.environ, GDAL_DATA=str(hms / "bin/gdal/gdal-data"), PROJ_LIB=str(hms / "bin/gdal/proj"))


def correr_hms(juegos_de_parametros):
    """Corre HEC-HMS una vez por cada juego de parámetros y devuelve el Q simulado de cada uno (Series diarias)."""
    carpeta_lote = CARPETA_PROYECTO / "lotes"
    for viejo in carpeta_lote.iterdir():
        viejo.unlink()
    lineas = []
    for i, p in enumerate(juegos_de_parametros):
        (carpeta_lote / f"cuenca_{i}.basin").write_text(texto_cuenca(p), encoding="utf-8")
        lineas.append(f"{carpeta_lote / f'cuenca_{i}.basin'},{carpeta_lote / f'q_{i}.csv'}")
    (carpeta_lote / "lote.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    corrida = subprocess.run([str(java), "-Djava.awt.headless=true", f"-Djava.library.path={librerias}",
                              "-classpath", clases, "hms.Hms", "-s", str(CARPETA_PROYECTO / "correr_lote.py")],
                             env=entorno, capture_output=True, text=True, timeout=3600)
    series = []
    for i in range(len(juegos_de_parametros)):
        archivo = carpeta_lote / f"q_{i}.csv"
        if not archivo.exists():
            print(corrida.stdout[-3000:], corrida.stderr[-3000:])
            raise RuntimeError(f"HEC-HMS no produjo el caudal simulado del juego {i}; ver la salida de arriba")
        sim = pd.read_csv(archivo)
        # El valor guardado a las 24:00 pertenece al día que termina
        fechas = [pd.Timestamp(ORIGEN_DSS + timedelta(minutes=int(m) - 1)).normalize() for m in sim["minutos"]]
        series.append(pd.Series(sim["caudal_simulado_m3s"].values, index=fechas).reindex(datos.index))
    return series


def kge(obs, sim):
    """KGE de Gupta et al. (2009), la misma fórmula del informe."""
    r = np.corrcoef(obs, sim)[0, 1]
    alfa, beta = sim.std() / obs.std(), sim.mean() / obs.mean()
    return 1 - np.sqrt((r - 1) ** 2 + (alfa - 1) ** 2 + (beta - 1) ** 2)


def metricas(obs, sim):
    """NSE, KGE, correlación y sesgo en % del volumen."""
    return {"n": len(obs),
            "nse": 1 - ((obs - sim) ** 2).sum() / ((obs - obs.mean()) ** 2).sum(),
            "kge": kge(obs, sim), "r": np.corrcoef(obs, sim)[0, 1], "sesgo_pct": (sim.mean() / obs.mean() - 1) * 100}


# ------------------------------------------------------------------ 5. corrida sin calibrar
q_sin_calibrar = correr_hms([PARAMETROS_INICIALES])[0]
assert q_sin_calibrar.notna().all(), "faltan días simulados"
lineas_bitacora = (CARPETA_PROYECTO / f"{ARCHIVO_CORRIDA}.log").read_text(encoding="latin-1").splitlines()
errores = [l for l in lineas_bitacora if l.startswith("ERROR")]
assert not errores, "\n".join(errores)
# El hidrograma unitario debe devolver toda la lluvia efectiva: 1 mm de entrada, 1 mm de salida (supuesto 8)
assert any("Unit hydrograph volume" in l and "is 1.0000 mm" in l for l in lineas_bitacora), "volumen del HU"


# ------------------------------------------------------------------ 6. calibración
nombres_calibrados = list(RANGOS_CALIBRACION)
en_calibracion = (periodo == "calibración").values
q_obs_calibracion = datos["caudal"].values[en_calibracion]


def parametros_desde_vector(x):
    return {**PARAMETROS_INICIALES, **dict(zip(nombres_calibrados, x))}


def objetivo(poblacion):
    """1 - KGE diario en calibración, para cada juego de la población (el optimizador minimiza).

    La evolución diferencial entrega toda una generación a la vez (columnas de `poblacion`), y se corre en un solo
    lote de HEC-HMS."""
    simulados = correr_hms([parametros_desde_vector(x) for x in poblacion.T])
    return np.array([1 - kge(q_obs_calibracion, s.values[en_calibracion]) for s in simulados])


def avance(intermediate_result):
    """Muestra el avance; scipy exige que el argumento se llame así para entregar el mejor resultado hasta ahora."""
    print(f"  generación {avance.n:>2}: mejor KGE de calibración {1 - intermediate_result.fun:.3f}", flush=True)
    avance.n += 1


avance.n = 1
print(f"Calibrando {len(nombres_calibrados)} parámetros con evolución diferencial…")
resultado = differential_evolution(objetivo, bounds=[RANGOS_CALIBRACION[n] for n in nombres_calibrados],
                                   popsize=TAMANO_POBLACION, maxiter=GENERACIONES_MAX, seed=SEMILLA,
                                   vectorized=True, updating="deferred", polish=False, callback=avance)
parametros_calibrados = parametros_desde_vector(resultado.x)

# Corrida final con los parámetros calibrados; el proyecto queda con ellos, para abrirlo en la interfaz
q_calibrado = correr_hms([parametros_calibrados])[0]
(CARPETA_PROYECTO / "san_gil.basin").write_text(texto_cuenca(parametros_calibrados), encoding="utf-8")
for viejo in (CARPETA_PROYECTO / "lotes").iterdir():
    viejo.unlink()
(CARPETA_PROYECTO / "lotes").rmdir()


# ------------------------------------------------------------------ 7. resultados
diario = pd.DataFrame({"lluvia_mm": datos["p_chirps"], "caudal_observado_m3s": datos["caudal"],
                       "caudal_sin_calibrar_m3s": q_sin_calibrar, "caudal_calibrado_m3s": q_calibrado,
                       "periodo": periodo})
diario.index.name = "fecha"
diario.round(4).to_csv(RAIZ / "out/hec_hms_san_gil_diario.csv")

unidades = {"mm_h": "mm/h", "mm": "mm", "_h": "h", "tension": "fracción", "pct": "%"}
tabla_parametros = pd.DataFrame([
    {"parametro": n, "unidad": next(u for clave, u in unidades.items() if n.endswith(clave)),
     "valor_inicial": PARAMETROS_INICIALES[n],
     "minimo": RANGOS_CALIBRACION.get(n, (np.nan, np.nan))[0], "maximo": RANGOS_CALIBRACION.get(n, (np.nan, np.nan))[1],
     "valor_calibrado": parametros_calibrados[n], "calibrado": n in RANGOS_CALIBRACION}
    for n in PARAMETROS_INICIALES])
tabla_parametros.round(4).to_csv(RAIZ / "out/hec_hms_san_gil_parametros.csv", index=False)


def a_mensual(serie_diaria, agregacion, periodos):
    """Copia de a_mensual de scripts/18_calculos_informe.py (regla 5): el mes queda vacío si le faltan más de
    MAX_DIAS_FALTANTES días. Aquí los días fuera del período cuentan como faltantes."""
    g = serie_diaria.resample("MS")
    faltantes = g.apply(lambda x: x.index.days_in_month[0] - x.notna().sum())
    promedio = g.mean()
    valores = {"sum": promedio * promedio.index.days_in_month, "mean": promedio}[agregacion]
    valores = valores.where(faltantes <= MAX_DIAS_FALTANTES)
    valores.index = valores.index.to_period("M")
    return valores.reindex(periodos)


filas = []
for nombre_periodo in ("calibración", "validación"):
    tramo_periodo = diario[diario["periodo"] == nombre_periodo]
    meses = pd.period_range(tramo_periodo.index.min(), tramo_periodo.index.max(), freq="M")
    calendario = pd.date_range(meses[0].start_time, meses[-1].end_time.normalize(), freq="D")
    for corrida, columna in (("sin calibrar", "caudal_sin_calibrar_m3s"), ("calibrado", "caudal_calibrado_m3s")):
        obs, sim = tramo_periodo["caudal_observado_m3s"], tramo_periodo[columna]
        filas.append({"corrida": corrida, "periodo": nombre_periodo, "escala": "diaria",
                      "desde": tramo_periodo.index.min().date(), "hasta": tramo_periodo.index.max().date(),
                      **metricas(obs, sim)})
        mensual = pd.DataFrame({c: a_mensual(s.reindex(calendario), "mean", meses)
                                for c, s in (("obs", obs), ("sim", sim))}).dropna()
        filas.append({"corrida": corrida, "periodo": nombre_periodo, "escala": "mensual",
                      "desde": tramo_periodo.index.min().date(), "hasta": tramo_periodo.index.max().date(),
                      **metricas(mensual["obs"], mensual["sim"])})
tabla = pd.DataFrame(filas)
tabla.round(3).to_csv(RAIZ / "out/hec_hms_san_gil_metricas.csv", index=False)
print(tabla_parametros[tabla_parametros["calibrado"]].round(3).to_string(index=False))
print(tabla.round(3).to_string(index=False))
