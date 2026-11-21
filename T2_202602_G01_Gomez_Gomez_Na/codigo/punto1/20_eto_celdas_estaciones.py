"""Nuestra ETo FAO-56 en la celda de ERA5-Land que contiene cada estación del IDEAM (punto 1, fase 3).

Mismo cálculo que los scripts 03 (días locales, Rn) y 04 (ETo, ec. 6): se importan sus funciones y solo cambia la
carpeta de entrada. Así la ETo de estas celdas es la misma que tendríamos si fueran puntos de la cuenca.

Lee:
    datos/punto1/era5land_celdas_estaciones/punto_<código>.csv   salida de 19_descarga_era5land_celdas_estaciones.py
Escribe en productos/punto1/:
    era5land_diario_celdas_estaciones.csv   entradas diarias y Rn por estación (columnas de era5land_diario_puntos.csv)
    eto_diaria_celdas_estaciones.csv        ETo diaria y sus términos por estación (columnas de eto_diaria_puntos.csv)

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/20_eto_celdas_estaciones.py
"""

import importlib.util
from pathlib import Path

import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_celdas_estaciones"
SALIDA_DIARIA = RAIZ_ENTREGA / "productos" / "punto1" / "era5land_diario_celdas_estaciones.csv"
SALIDA_ETO = RAIZ_ENTREGA / "productos" / "punto1" / "eto_diaria_celdas_estaciones.csv"
ESTACIONES = ["24025040", "24025030", "24025050"]


def cargar(nombre_archivo):
    spec = importlib.util.spec_from_file_location(nombre_archivo[:-3], Path(__file__).with_name(nombre_archivo))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main():
    s03 = cargar("03_series_diarias_rn.py")
    s04 = cargar("04_eto_fao56.py")
    s03.CARPETA_DATOS = CARPETA_DATOS
    diarias, etos = [], []
    for codigo in ESTACIONES:
        horaria, latitud = s03.leer_horaria_local(codigo)
        diaria, z_modelo = s03.diaria_de_un_punto(horaria, latitud)
        assert len(diaria) == 9131 and diaria.drop(columns="horas").notna().all().all()
        assert (diaria["rs_MJm2"] <= diaria["ra_MJm2"]).all()
        eto = s04.eto_fao56(diaria)
        assert (eto["eto_mm"] > 0).all()
        print(f"{codigo}: latitud de la celda {latitud:.1f}°, altura del modelo ≈ {z_modelo:.0f} m, "
              f"ETo media {eto['eto_mm'].mean():.2f} mm/día")
        diaria.insert(0, "estacion", codigo)
        diaria.insert(1, "z_modelo_m", round(z_modelo, 1))
        eto.insert(0, "estacion", codigo)
        diarias.append(diaria)
        etos.append(eto)
    for tabla, salida in ((pd.concat(diarias), SALIDA_DIARIA), (pd.concat(etos), SALIDA_ETO)):
        tabla.index = tabla.index.strftime("%Y-%m-%d")
        tabla.index.name = "fecha"
        tabla.round(4).to_csv(salida)
        print(f"Listo: {salida.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
