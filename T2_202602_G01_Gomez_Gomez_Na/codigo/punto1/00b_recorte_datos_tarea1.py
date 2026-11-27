"""Recorta a la cuenca del Fonce los dos archivos nacionales de la Tarea 1 que el punto 1 sí lee (punto 1, fase 0).

El enunciado pide los datos «recortados a la cuenca y al periodo analizado», sin bases nacionales completas. De la
copia de la Tarea 1 en datos/punto1/ hay dos archivos que el código lee y que venían para todo el país:

    camels_col/boundaries/03_CAMELS_COL_Basin_boundary/CAMELS_COL_catchments_boundaries.shp
        Divisorias de las 347 cuencas de CAMELS-COL (42 MB). Se deja solo la de San Gil (IDEAM_CODE 24027010).
    imerg/imerg_mensual_col.npz
        IMERG V07 mensual sobre toda Colombia (133 × 185 celdas de 0.1°). Se deja la caja de la cuenca más 2 celdas
        de margen por lado; el promedio ponderado por área del script 15 solo usa las celdas que tocan la cuenca.

Los archivos se reescriben en el mismo lugar y con el mismo nombre, así ningún otro script cambia. Los valores no
cambian: solo se quitan cuencas y celdas. Después del recorte se actualizan el tamaño, el SHA-256 y el
procesamiento de su .meta.json.

El script se puede correr de nuevo: si un archivo ya está recortado, lo dice y no lo toca. Para rehacer el recorte
desde el original hay que volver a bajar CAMELS-COL (https://doi.org/10.5281/zenodo.18794895) o IMERG
(https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07), como se hizo en la Tarea 1.

Uso, desde la carpeta de la entrega:
    python codigo/punto1/00b_recorte_datos_tarea1.py
"""

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
DATOS = RAIZ_ENTREGA / "datos" / "punto1"
DIVISORIAS = (DATOS / "camels_col" / "boundaries" / "03_CAMELS_COL_Basin_boundary"
              / "CAMELS_COL_catchments_boundaries.shp")
IMERG = DATOS / "imerg" / "imerg_mensual_col.npz"
CODIGO_IDEAM = "24027010"
MARGEN_CELDAS = 2            # celdas de 0.1° de margen alrededor de la caja de la cuenca
MEDIO_LADO = 0.05            # medio lado de una celda de IMERG, en grados


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def actualizar_meta(ruta, procesamiento_extra):
    """Agrega el recorte al campo «procesamiento» y pone al día tamaño y SHA-256."""
    ruta_meta = ruta.with_name(ruta.name + ".meta.json")
    if not ruta_meta.exists():
        return
    meta = json.loads(ruta_meta.read_text(encoding="utf-8"))
    if procesamiento_extra not in meta.get("procesamiento", ""):
        meta["procesamiento"] = meta.get("procesamiento", "") + "; " + procesamiento_extra
    meta["tamano_bytes"] = ruta.stat().st_size
    meta["sha256"] = sha256(ruta)
    ruta_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recortar_divisorias():
    """Deja en el shapefile solo la cuenca de San Gil. Devuelve su polígono en WGS84."""
    cuencas = gpd.read_file(DIVISORIAS)
    san_gil = cuencas[cuencas["IDEAM_CODE"].astype(str) == CODIGO_IDEAM]
    assert len(san_gil) == 1, f"se esperaba una sola cuenca {CODIGO_IDEAM}"
    if len(cuencas) == 1:
        print(f"Divisorias: ya recortadas (solo {CODIGO_IDEAM}).")
    else:
        crs_original = cuencas.crs
        san_gil.to_file(DIVISORIAS)
        print(f"Divisorias: {len(cuencas)} cuencas -> 1 ({CODIGO_IDEAM}), CRS {crs_original}.")
        for extension in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            actualizar_meta(DIVISORIAS.with_suffix(extension),
                            f"recortado a la cuenca {CODIGO_IDEAM} con codigo/punto1/00b_recorte_datos_tarea1.py")
    return san_gil.to_crs(4326).geometry.iloc[0]


def recortar_imerg(cuenca):
    """Deja en el .npz de IMERG la caja de la cuenca más MARGEN_CELDAS celdas por lado."""
    datos = np.load(IMERG, allow_pickle=True)
    p, lon, lat, fechas = datos["precip_mm_mes"], datos["lon"], datos["lat"], datos["fechas"]
    minx, miny, maxx, maxy = cuenca.bounds
    margen = MARGEN_CELDAS * 2 * MEDIO_LADO
    ii = np.flatnonzero((lon + MEDIO_LADO > minx - margen) & (lon - MEDIO_LADO < maxx + margen))
    jj = np.flatnonzero((lat + MEDIO_LADO > miny - margen) & (lat - MEDIO_LADO < maxy + margen))
    if len(ii) == len(lon) and len(jj) == len(lat):
        print(f"IMERG: ya recortado ({len(lon)} × {len(lat)} celdas).")
        return
    # Las celdas que tocan la cuenca deben quedar todas dentro del recorte.
    toca_lon = np.flatnonzero((lon + MEDIO_LADO > minx) & (lon - MEDIO_LADO < maxx))
    toca_lat = np.flatnonzero((lat + MEDIO_LADO > miny) & (lat - MEDIO_LADO < maxy))
    assert set(toca_lon) <= set(ii) and set(toca_lat) <= set(jj)
    np.savez_compressed(IMERG, precip_mm_mes=p[:, ii][:, :, jj], lon=lon[ii], lat=lat[jj], fechas=fechas)
    print(f"IMERG: {len(lon)} × {len(lat)} celdas -> {len(ii)} × {len(jj)} "
          f"(lon {lon[ii][0]:.2f} a {lon[ii][-1]:.2f}, lat {lat[jj][0]:.2f} a {lat[jj][-1]:.2f}).")
    actualizar_meta(IMERG, f"recortado a la caja de la cuenca {CODIGO_IDEAM} más {MARGEN_CELDAS} celdas por lado "
                           f"(lon {lon[ii][0]:.2f} a {lon[ii][-1]:.2f}, lat {lat[jj][0]:.2f} a {lat[jj][-1]:.2f}) "
                           "con codigo/punto1/00b_recorte_datos_tarea1.py")


def main():
    cuenca = recortar_divisorias()
    recortar_imerg(cuenca)


if __name__ == "__main__":
    main()
