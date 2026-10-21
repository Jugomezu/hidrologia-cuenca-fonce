# Guion de Jython que corre dentro de HEC-HMS; lo escribe scripts/16d_hec_hms_san_gil.py
import os
import shutil
from hec.heclib.dss import HecDss
from hec.io import TimeSeriesContainer
from hms.model import Project
from hms import Hms

carpeta = r"/home/user/hidrologia-cuenca-fonce/out/hec_hms_san_gil"
archivo_dss = carpeta + "/fonce_san_gil.dss"

if not os.path.exists(archivo_dss):
    filas = [linea.strip().split(",") for linea in open(carpeta + "/series_entrada.csv").readlines()[1:]]
    tiempos = [int(f[0]) for f in filas]
    dss = HecDss.open(archivo_dss)
    for ruta, columna, unidades, tipo in [("/FONCE/SAN GIL/PRECIP-INC//1DAY/CAMELS-CHIRPS/", 1, "MM", "PER-CUM"),
                                          ("/FONCE/SAN GIL/FLOW//1DAY/CAMELS-OBS/", 2, "M3/S", "PER-AVER")]:
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
    proyecto = Project.open(carpeta + "/fonce_san_gil.hms")
    proyecto.computeRun("San Gil diario")
    proyecto.close()
    dss = HecDss.open(carpeta + "/San_Gil_diario.dss")
    rutas = [r for r in dss.getCatalogedPathnames() if r.split("/")[2] == "Salida San Gil"
             and r.split("/")[3] == "FLOW"]
    serie = dss.get(rutas[0], True)
    salida = open(archivo_salida, "w")
    salida.write("minutos,caudal_simulado_m3s\n")
    for t, v in zip(serie.times, serie.values):
        salida.write("%d,%.6f\n" % (t, v))
    salida.close()
    dss.close()
Hms.shutdownEngine()
