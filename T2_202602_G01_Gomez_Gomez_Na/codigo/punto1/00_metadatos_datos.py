"""Escribe un .meta.json junto a cada archivo de datos/punto1/ que todavía no lo tenga (punto 1).

El enunciado pide, para cada archivo de entrada, su fuente, versión, unidades, fecha de descarga y procesamiento.
Los scripts de descarga nuevos (05 en adelante) ya escriben su propio .meta.json; este script cubre el resto:
la copia de los datos de la Tarea 1, los 6 puntos de ERA5-Land (01) y el brillo solar del IDEAM.

Cómo funciona:
    - La tabla FUENTES asigna a cada carpeta (por prefijo de ruta) su fuente, versión, unidades, fecha de descarga
      y procesamiento. Se escribió a partir de ../Analisis_De_Cuenca/DATOS_FUENTES.md (Tarea 1),
      datos/punto1/era5land_puntos/metadatos_descarga.json y anexos/decisiones.md.
    - A cada archivo se le agrega su nombre, tamaño y SHA-256, calculados aquí.
    - Un .meta.json que ya existe NO se sobrescribe (puede venir del script de descarga, que sabe más).
    - Si un archivo no cae en ninguna carpeta de FUENTES, el script se detiene: hay que describirlo antes.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/00_metadatos_datos.py
Se puede correr otra vez después de recortar datos/punto1/: solo escribe lo que falte.
"""

import hashlib
import json
from pathlib import Path

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
DATOS = RAIZ_ENTREGA / "datos" / "punto1"

# Archivos que no son datos: no llevan .meta.json.
NO_SON_DATOS = {"metadatos_descarga.json", "LEEME.md", ".gitkeep"}

T1 = "copia sin cambios de ../Analisis_De_Cuenca/data/ (Tarea 1); detalle en ../Analisis_De_Cuenca/DATOS_FUENTES.md"

# Prefijo de ruta (relativa a datos/punto1/) → descripción. Gana el prefijo más largo.
FUENTES = {
    "camels_col/": {
        "fuente": "CAMELS-COL (Jimenez et al., 2026), Zenodo, doi:10.5281/zenodo.18794895; licencia CC-BY-4.0",
        "version": "publicada 2026-02-26 (3a versión del registro)",
        "unidades": "series diarias: pr mm, poten_evapo mm/día, t_max/t_min/t_mean °C, streamflow m³/s; "
                    "atributos según attrs/01_CAMELS_COL_Attributes/CAMELS_COL_readme.txt",
        "fecha_descarga": "2026-09-18",
        "procesamiento": T1,
    },
    "camels_col/essd-2025-200.pdf": {
        "fuente": "Artículo de CAMELS-COL, preprint de discusión en Earth System Science Data, doi:10.5194/essd-2025-200",
        "version": "preprint de discusión",
        "unidades": "no aplica (documento)",
        "fecha_descarga": "2026-09-18",
        "procesamiento": T1,
    },
    "dem/": {
        "fuente": "DEM ALOS PALSAR 12.5 m (Alaska Satellite Facility), recorte de la zona de la cuenca",
        "version": "no registrada: el mosaico ya estaba recortado para Colombia (ver DATOS_FUENTES.md de la Tarea 1)",
        "unidades": "altura en m",
        "fecha_descarga": "no registrada; recorte hecho el 2026-09-27",
        "procesamiento": T1 + "; recorte con ../Analisis_De_Cuenca/scripts/03_recorte_dem.py",
    },
    "era5land_gee/": {
        "fuente": "ERA5-Land, temperatura del aire a 2 m, agregados diarios, vía Google Earth Engine; "
                  "doi:10.24381/cds.e2161bac; licencia Copernicus",
        "version": "ERA5-Land, agregado diario (ECMWF/ERA5_LAND/DAILY_AGGR)",
        "unidades": "t_media, t_min, t_max en °C, promedio de la cuenca por día",
        "fecha_descarga": "2026-09-24",
        "procesamiento": T1,
    },
    "era5land_puntos/": {
        "fuente": "ERA5-Land (Muñoz-Sabater et al., 2021), Copernicus Climate Data Store, "
                  "producto reanalysis-era5-land-timeseries; licencia Copernicus",
        "version": "servida por el CDS el día de la descarga",
        "unidades": "t2m y d2m en K, sp en Pa, u10 y v10 en m/s, ssrd en J/m² por hora (no acumulada); "
                    "valid_time en UTC",
        "fecha_descarga": "2026-11-12",
        "procesamiento": "ninguno: CSV tal como lo entrega el CDS, las 4 partes de cada punto unidas por "
                         "codigo/punto1/01_descarga_era5land_puntos.py; ver metadatos_descarga.json",
    },
    "era5land_puntos/regiones_voronoi_puntos.geojson": {
        "fuente": "Elaboración propia: regiones de Voronoi de los 6 puntos de ERA5-Land, recortadas al polígono "
                  "de CAMELS-COL 24027010",
        "version": "opción E (decisión del 2026-11-12, anexos/decisiones.md)",
        "unidades": "geometrías en lon/lat (CRS84); peso = fracción del área de la cuenca",
        "fecha_descarga": "2026-11-17 (copiado del proyecto)",
        "procesamiento": "copiado por codigo/punto1/04b_comprobaciones_eto.py",
    },
    "ideam/": {
        "fuente": "IDEAM, DHIME (atencionciudadano.ideam.gov.co), precipitación de pluviómetros; uso investigativo "
                  "no comercial citando al IDEAM",
        "version": "datos con nivel de aprobación «Preliminar»",
        "unidades": "precipitación en mm (diaria o mensual según el archivo)",
        "fecha_descarga": "2026-09-23 (primera descarga), 2026-09-24 (mensual 1998-2022 de 8 estaciones) y 2026-10-07 (mensual 1981-1997)",
        "procesamiento": T1,
    },
    "ideam/cne_ideam.csv": {
        "fuente": "Catálogo Nacional de Estaciones del IDEAM, datos.gov.co (Socrata hp9r-jxuu)",
        "version": "instantánea del 2026-09-18",
        "unidades": "altitud en m, longitud y latitud en grados",
        "fecha_descarga": "2026-09-18",
        "procesamiento": T1,
    },
    "ideam_brillo_solar/": {
        "fuente": "IDEAM, DHIME, brillo solar total diario de Escuela Agrícola Mogotes (24025040), La Sierra "
                  "(24025030) y Charalá (24025050)",
        "version": "datos con nivel de aprobación «Preliminar»",
        "unidades": "horas de sol por día",
        "fecha_descarga": "2026-11-17",
        "procesamiento": "ninguno: ZIP tal como lo entrega DHIME (anexos/decisiones.md, 2026-11-17)",
    },
    "imerg/": {
        "fuente": "NASA GPM IMERG Final, mensual 0.1° V07 (GPM_3IMERGM), doi:10.5067/GPM/IMERG/3B-MONTH/07; "
                  "dominio público",
        "version": "V07B",
        "unidades": "mensual/AAAAMM.txt: mm/h (tal como lo entrega la NASA); imerg_mensual_col.npz: mm/mes",
        "fecha_descarga": "2026-09-18",
        "procesamiento": T1 + "; recorte a Colombia (lon -79.55 a -66.35, lat -4.65 a 13.75)",
    },
    "imerg/imerg_v07_technical_documentation.pdf": {
        "fuente": "Documentación técnica de IMERG V07 (NASA GES DISC)",
        "version": "V07",
        "unidades": "no aplica (documento)",
        "fecha_descarga": "2026-09-18",
        "procesamiento": T1,
    },
    "mapbiomas/": {
        "fuente": "MapBiomas Colombia, colección 3, cobertura y uso del suelo 2022 (Google Cloud Storage público)",
        "version": "colección 3, año 2022",
        "unidades": "clase de cobertura (código entero de MapBiomas)",
        "fecha_descarga": "2026-10-09",
        "procesamiento": T1 + "; ventana leída con ../Analisis_De_Cuenca/scripts/03d_coberturas_mapbiomas.py",
    },
    "noaa/oni.ascii.txt": {
        "fuente": "NOAA Climate Prediction Center, Oceanic Niño Index (ONI); dominio público",
        "version": "versión publicada el día de la descarga",
        "unidades": "anomalía de temperatura del mar en °C",
        "fecha_descarga": "2026-09-28",
        "procesamiento": T1,
    },
    "noaa/tna.txt": {
        "fuente": "NOAA PSL, índice del Atlántico tropical norte (TNA); dominio público",
        "version": "versión publicada el día de la descarga",
        "unidades": "anomalía de temperatura del mar en °C",
        "fecha_descarga": "2026-10-11",
        "procesamiento": T1,
    },
    "sgc/": {
        "fuente": "Servicio Geológico Colombiano, Mapa Geológico de Colombia 2023, escala 1:1 500 000",
        "version": "2023",
        "unidades": "no aplica (unidades cronoestratigráficas y fallas)",
        "fecha_descarga": "2026-10-09",
        "procesamiento": T1,
    },
}


def descripcion(relativa):
    """La entrada de FUENTES con el prefijo más largo que coincide con la ruta."""
    candidatos = [p for p in FUENTES if relativa == p or (p.endswith("/") and relativa.startswith(p))]
    if not candidatos:
        raise KeyError(f"{relativa} no tiene fuente en FUENTES: descríbalo antes de entregar.")
    return FUENTES[max(candidatos, key=len)]


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    escritos = existentes = 0
    for ruta in sorted(DATOS.rglob("*")):
        if not ruta.is_file() or ruta.name in NO_SON_DATOS or ruta.name.endswith(".meta.json"):
            continue
        meta = ruta.with_name(ruta.name + ".meta.json")
        if meta.exists():
            existentes += 1
            continue
        relativa = ruta.relative_to(DATOS).as_posix()
        contenido = {"archivo": relativa, **descripcion(relativa),
                     "tamano_bytes": ruta.stat().st_size, "sha256": sha256(ruta),
                     "metadatos_escritos_por": "codigo/punto1/00_metadatos_datos.py"}
        meta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        escritos += 1
    print(f"Escritos {escritos} .meta.json; {existentes} ya existían y no se tocaron.")


if __name__ == "__main__":
    main()
