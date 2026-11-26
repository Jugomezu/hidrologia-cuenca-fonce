#!/usr/bin/env python3
"""Delimita una microcuenca con Copernicus GLO-30 y contrasta la IDF.

Todas las rutas se construyen desde la raíz del proyecto. Los análisis que
dependen de servicios externos registran fallos explícitos; no se sustituyen
datos ausentes por geometrías, cotas ni cuantiles inventados.

Dependencias geoespaciales opcionales: rasterio, pysheds, shapely, pyproj.
Dependencias del análisis: numpy, pandas, scipy, matplotlib, requests.
"""
from __future__ import annotations

import csv
import ast
import importlib.util
import json
import math
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
if not hasattr(np, "in1d"):
    np.in1d = np.isin
import pandas as pd
import requests
from scipy.stats import pearson3

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datos" / "punto2"
PRODUCTS = ROOT / "productos" / "punto2"
DEM_PATH = DATA / "dem_microcuenca_denver.tif"
DEM_NATIVE_PATH = DATA / "dem_microcuenca_denver_nativo.tif"
GEOJSON_PATH = DATA / "microcuenca_denver.geojson"
METADATA_PATH = DATA / "metadatos_microcuenca.json"
FIG_PATH = PRODUCTS / "fig_24_microcuenca_dem.png"
COMPARE_PATH = PRODUCTS / "idf_comparacion_oficial_y_evento.csv"
GRID_IDF_PATHS = {
    "ERA5-Land": DATA / "idf_malla_era5land.csv",
    "IMERG": DATA / "idf_malla_imerg.csv",
}

STATION = "USW00023062"
STATION_LAT = 39.7633
STATION_LON = -104.8694
STATION_ELEV_M = 5286 * 0.3048
COP_DEM_TILE = "Copernicus_DSM_COG_10_N39_00_W105_00_DEM"
COP_DEM_URL = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    f"{COP_DEM_TILE}/{COP_DEM_TILE}.tif"
)
NOAA_ENDPOINTS = (
    # La ruta cgi-bin/new es la documentada actualmente por NOAA HDSC.
    "https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py",
    # Compatibilidad con el alias solicitado en el enunciado.
    "https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py",
)
NOAA_QUERY = {
    "type": "pf", "data": "depth", "lat": f"{STATION_LAT:.4f}",
    "lon": f"{STATION_LON:.4f}", "series": "pds", "units": "metric",
}
RECENT_EVENT = {
    "date": "2022-08-07",
    "intensity_mmh": 2.0 * 25.4,
    "basis": "Reporte de hasta 2 in en menos de 1 h en el área metropolitana; umbral regional conservador, no medición puntual de Stapleton.",
    "source": "https://www.accuweather.com/en/weather-news/motorists-stranded-across-denver-as-heavy-rains-trigger-flash-flooding/1228751; https://www.weather.gov/media/bou/August2022Climate.pdf",
}
N_BOOT = 1000
SEED = 42


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_lmom_module():
    """Carga las funciones LP3/LMOM ya usadas en el apartado 2.2."""
    module_path = ROOT / "codigo" / "punto2" / "02_extremos_y_distribuciones.py"
    spec = importlib.util.spec_from_file_location("punto2_extremos", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el ajuste LP3/LMOM: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def locate_rasterio():
    try:
        import rasterio
        return rasterio
    except Exception as exc:
        raise RuntimeError(f"No se pudo importar rasterio: {exc}") from exc


def download_crop_dem() -> tuple[Path, dict]:
    """Lee un recorte nativo dentro del contexto abierto y lo reproyecta a UTM.

    Se intenta primero el COG Copernicus por HTTP Range. Si falla o supera el
    timeout de GDAL, prueba OpenTopography SRTM GL1 cuando hay API key y luego
    TNM Access/USGS 3DEP 1 arc-second, que no requiere autenticación.
    """
    rasterio = locate_rasterio()
    from rasterio.enums import Resampling
    from rasterio.transform import array_bounds
    from rasterio.warp import calculate_default_transform, reproject
    from rasterio.windows import Window, from_bounds

    west, east = STATION_LON - 0.12, STATION_LON + 0.12
    south, north = STATION_LAT - 0.09, STATION_LAT + 0.09
    target_crs = "EPSG:32613"  # WGS84 / UTM Zone 13N.
    DATA.mkdir(parents=True, exist_ok=True)
    errors = []

    def crop_and_reproject(source, source_label: str, source_url: str,
                           approximate_resolution_m: float) -> tuple[Path, dict]:
        """Lee/escribe el recorte antes de cerrar el dataset de entrada."""
        with rasterio.open(source) as src:
            if src.crs is None:
                raise RuntimeError(f"{source_label}: el raster no declara CRS.")
            window = from_bounds(west, south, east, north, transform=src.transform)
            window = window.round_offsets().round_lengths()
            window = window.intersection(Window(0, 0, src.width, src.height))
            if window.width <= 0 or window.height <= 0:
                raise RuntimeError(f"{source_label}: la ventana solicitada no intersecta el raster.")

            # Lectura explícita por ventana mientras src sigue abierto. El
            # recorte nativo queda persistido antes de cualquier reproyección.
            native_masked = src.read(1, window=window, masked=True)
            native_transform = src.window_transform(window)
            native_profile = src.profile.copy()
            native_nodata = src.nodata if src.nodata is not None else -9999.0
            native_profile.update(
                driver="GTiff", count=1,
                width=int(window.width), height=int(window.height),
                transform=native_transform, crs=src.crs,
                nodata=native_nodata, compress="deflate", tiled=True,
            )
            native_array = np.asarray(native_masked.filled(native_nodata), dtype=np.float32)
            with rasterio.open(DEM_NATIVE_PATH, "w", **native_profile) as dst:
                dst.write(native_array, 1)
            native_crs = src.crs

        # Reproyección en memoria desde el recorte nativo guardado, sin VRT
        # asociado a un dataset ya cerrado.
        bounds = array_bounds(native_array.shape[0], native_array.shape[1], native_transform)
        dst_transform, dst_width, dst_height = calculate_default_transform(
            native_crs, target_crs, native_array.shape[1], native_array.shape[0],
            *bounds, resolution=30,
        )
        if dst_width <= 0 or dst_height <= 0:
            raise RuntimeError(f"{source_label}: reproyección produjo dimensiones vacías.")
        dst_nodata = -9999.0
        projected = np.full((dst_height, dst_width), dst_nodata, dtype=np.float32)
        reproject(
            source=native_array, destination=projected,
            src_transform=native_transform, src_crs=native_crs,
            src_nodata=native_nodata, dst_transform=dst_transform,
            dst_crs=target_crs, dst_nodata=dst_nodata,
            resampling=Resampling.bilinear,
        )
        out_profile = {
            "driver": "GTiff", "height": dst_height, "width": dst_width,
            "count": 1, "dtype": "float32", "crs": target_crs,
            "transform": dst_transform, "nodata": dst_nodata,
            "compress": "deflate", "tiled": True,
        }
        with rasterio.open(DEM_PATH, "w", **out_profile) as dst:
            dst.write(projected, 1)
        return DEM_PATH, {
            "dem_source": source_label, "dem_url": source_url,
            "dem_nominal_resolution_m": approximate_resolution_m,
            "dem_crs": target_crs,
            "dem_native_crop_path_relative": str(DEM_NATIVE_PATH.relative_to(ROOT)),
            "dem_recorte_wgs84": {"west": west, "south": south, "east": east, "north": north},
            "dem_date_accessed_utc": datetime.now(timezone.utc).isoformat(),
            "dem_note": "Recorte nativo guardado antes de reproject() a EPSG:32613. Copernicus GLO-30 es DSM; USGS 3DEP es fuente de elevación de mejor disponibilidad.",
        }

    # Fuente primaria: COG Copernicus S3, lectura HTTP-range de ventana.
    try:
        with rasterio.Env(
            AWS_NO_SIGN_REQUEST="YES",
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
            GDAL_HTTP_TIMEOUT="25",
            GDAL_HTTP_MAX_RETRY="0",
        ):
            return crop_and_reproject(COP_DEM_URL, "Copernicus GLO-30 COG (AWS)",
                                      COP_DEM_URL, 30.0)
    except Exception as exc:
        errors.append(f"Copernicus AWS: {type(exc).__name__}: {exc}")
        print(f"Aviso: fuente primaria DEM falló o agotó timeout: {errors[-1]}")

    # Respaldo global SRTM GL1 de 30 m. OpenTopography exige clave gratuita;
    # sin ella se registra el motivo y se continúa automáticamente al TNM.
    api_key = os.environ.get("OPEN_TOPOGRAPHY_API_KEY", "").strip()
    if api_key:
        try:
            response = requests.get(
                "https://portal.opentopography.org/API/globaldem",
                params={"demtype": "SRTMGL1", "south": south, "north": north,
                        "west": west, "east": east, "outputFormat": "GTiff", "API_Key": api_key},
                timeout=(15, 90),
            )
            response.raise_for_status()
            backup_path = DATA / "dem_respaldo_srtm30m_descarga.tif"
            backup_path.write_bytes(response.content)
            try:
                return crop_and_reproject(backup_path, "OpenTopography SRTM GL1 30 m",
                                          response.url, 30.0)
            finally:
                backup_path.unlink(missing_ok=True)
        except Exception as exc:
            errors.append(f"OpenTopography SRTM GL1: {type(exc).__name__}: {exc}")
            print(f"Aviso: respaldo OpenTopography falló: {errors[-1]}")
    else:
        errors.append("OpenTopography SRTM GL1 omitido: falta OPEN_TOPOGRAPHY_API_KEY.")

    # Respaldo sin clave: TNM Access busca el DEM USGS 3DEP de 1 arc-second
    # (~30 m) que cubre el bbox y devuelve URL(s) públicas de descarga.
    try:
        api_url = "https://tnmaccess.nationalmap.gov/api/v1/products"
        items = []
        payload = {}
        dataset_errors = []
        for dataset_name in (
            "Digital Elevation Model (DEM) 1 arc-second",
            "National Elevation Dataset (NED) 1 arc-second",
        ):
            params = {
                "bbox": f"{west},{south},{east},{north}",
                "datasets": dataset_name, "prodFormats": "GeoTIFF",
                "outputFormat": "JSON", "max": 20, "offset": 0,
            }
            response = requests.get(api_url, params=params, timeout=(15, 45))
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            if items:
                break
            dataset_errors.append(f"{dataset_name}: sin productos")
        if not items:
            raise RuntimeError(f"TNM Access no devolvió tiles 1 arc-second ({dataset_errors}); respuesta: {payload}")
        # Elige el producto cuyo URL cubre primero el punto central, priorizando
        # títulos 1 arc-second; el raster se recortará a la ventana pedida.
        items.sort(key=lambda item: ("1 Arc Second" not in item.get("title", ""),
                                     item.get("title", "")))
        item = items[0]
        tile_url = item.get("downloadURL") or item.get("downloadUrl") or item.get("download_url")
        if not tile_url:
            for link in item.get("webLinks", []):
                if isinstance(link, dict) and link.get("url", "").lower().endswith((".tif", ".tiff", ".zip")):
                    tile_url = link["url"]
                    break
        if not tile_url:
            raise RuntimeError(f"TNM Access no incluyó URL de descarga: {item}")
        tile_response = requests.get(tile_url, timeout=(15, 120))
        tile_response.raise_for_status()
        tile_path = DATA / "dem_respaldo_usgs_3dep_tile.tif"
        tile_path.write_bytes(tile_response.content)
        try:
            return crop_and_reproject(tile_path, "USGS National Map 3DEP 1 arc-second (~30 m)",
                                      tile_url, 30.0)
        finally:
            tile_path.unlink(missing_ok=True)
    except Exception as exc:
        errors.append(f"USGS TNM Access 3DEP: {type(exc).__name__}: {exc}")
        print(f"ERROR explícito en respaldo USGS National Map: {errors[-1]}")

    raise RuntimeError("Fallaron todas las fuentes DEM. " + " || ".join(errors))


def delineate_basin(dem_path: Path) -> tuple[dict, dict]:
    """Busca un outlet cercano con cuenca completa entre 0.1 y 5 km²."""
    try:
        import rasterio
        from rasterio.features import shapes
        from rasterio.transform import rowcol
        from pyproj import Geod, Transformer
        from pysheds.grid import Grid
        from shapely.geometry import shape, mapping, Point
        from shapely.ops import transform as shapely_transform, unary_union
    except Exception as exc:
        raise RuntimeError(
            "Faltan dependencias para delinear/poligonizar DEM "
            f"(rasterio, pysheds, shapely, pyproj): {exc}"
        ) from exc

    grid = Grid.from_raster(str(dem_path))
    with rasterio.open(dem_path) as dem_src:
        dem_crs = dem_src.crs
    if dem_crs is None:
        raise RuntimeError(f"El DEM local {dem_path} no declara CRS.")
    dem = grid.read_raster(str(dem_path))
    filled = grid.fill_pits(dem)
    filled = grid.fill_depressions(filled)
    filled = grid.resolve_flats(filled)
    fdir = grid.flowdir(filled, dirmap=(64, 128, 1, 2, 4, 8, 16, 32))
    accum = grid.accumulation(fdir, dirmap=(64, 128, 1, 2, 4, 8, 16, 32))
    acc = np.asarray(accum, dtype=float)
    elev = np.asarray(dem, dtype=float)
    dirs = np.asarray(fdir, dtype=int)
    transform = grid.affine
    cell_x = abs(float(transform.a))
    cell_y = abs(float(transform.e))
    cell_area = cell_x * cell_y
    row0, col0 = rowcol(transform, 0, 0)  # only used to make sure transform is valid
    del row0, col0
    # Usa el CRS que ya tiene el TIFF. Esto permite reutilizar DEMs locales
    # existentes aunque se hayan generado en la versión anterior (EPSG:26913).
    project_to_geo = Transformer.from_crs(dem_crs, "EPSG:4326", always_xy=True).transform
    project_to_utm = Transformer.from_crs("EPSG:4326", dem_crs, always_xy=True).transform
    sx, sy = project_to_utm(STATION_LON, STATION_LAT)
    affine = transform
    station_col = int(round((sx - affine.c) / affine.a))
    station_row = int(round((sy - affine.f) / affine.e))

    max_cells = int(5_000_000 / cell_area)
    min_cells = int(math.ceil(100_000 / cell_area))
    rows, cols = np.where(np.isfinite(acc) & (acc >= min_cells) & (acc <= max_cells))
    if len(rows) == 0:
        raise RuntimeError("No hay celdas de acumulación candidata con área potencial 0.1–5 km².")
    dist = np.hypot((cols - station_col) * cell_x, (rows - station_row) * cell_y)
    near = dist <= 5000
    rows, cols, dist = rows[near], cols[near], dist[near]
    if len(rows) == 0:
        raise RuntimeError("No se encontraron cauces candidatos a menos de 5 km del pluviómetro.")
    target_cells = 1_850_000 / cell_area
    score = dist + 140 * np.abs(np.log(np.maximum(acc[rows, cols], 1) / target_cells))
    order = np.argsort(score)[:100]

    # D8 codes de ESRI y desplazamientos fila/columna.
    d8 = {(0, 1): 1, (1, 1): 2, (1, 0): 4, (1, -1): 8,
          (0, -1): 16, (-1, -1): 32, (-1, 0): 64, (-1, 1): 128}
    best = None
    failures = []
    for k in order:
        rr, cc = int(rows[k]), int(cols[k])
        xout, yout = rasterio.transform.xy(transform, rr, cc, offset="center")
        try:
            catch = grid.catchment(x=xout, y=yout, fdir=fdir, xytype="coordinate",
                                   dirmap=(64, 128, 1, 2, 4, 8, 16, 32))
            mask = np.asarray(catch, dtype=bool)
            area_km2 = float(mask.sum() * cell_area / 1e6)
            if not 0.1 <= area_km2 <= 5.0:
                continue
            edge = bool(mask[0, :].any() or mask[-1, :].any() or
                        mask[:, 0].any() or mask[:, -1].any())
            if edge:
                failures.append(f"outlet {rr},{cc}: cuenca toca borde del DEM")
                continue
            objective = abs(area_km2 - 1.85) + float(dist[k]) / 10000
            if best is None or objective < best[0]:
                best = (objective, rr, cc, xout, yout, mask, area_km2)
        except Exception as exc:
            failures.append(f"outlet {rr},{cc}: {exc}")
    if best is None:
        detail = "; ".join(failures[:5])
        raise RuntimeError(
            "No se obtuvo una cuenca completa válida (0.1–5 km²) a partir del DEM. "
            + (f"Detalles: {detail}" if detail else "Revise relieve, outlets y cobertura del recorte.")
        )
    _, outlet_row, outlet_col, ox, oy, mask, area_km2 = best

    # Convierte la máscara de celdas a polígono en UTM y luego a WGS84.
    polygons = [shape(geom) for geom, value in shapes(mask.astype(np.uint8),
                 mask=mask, transform=transform) if value == 1]
    if not polygons:
        raise RuntimeError("La máscara de cuenca no produjo geometría poligonal.")
    basin_utm = unary_union(polygons)
    basin_geo = shapely_transform(project_to_geo, basin_utm)
    station_utm = Point(sx, sy)
    centroid_dist_m = float(basin_utm.centroid.distance(station_utm))
    outlet_dist_m = float(Point(ox, oy).distance(station_utm))

    basin_values = elev[mask]
    basin_values = basin_values[np.isfinite(basin_values) & (basin_values > -1000)]
    if not len(basin_values):
        raise RuntimeError("La cuenca no contiene cotas DEM válidas.")
    outlet_z = float(elev[outlet_row, outlet_col])
    z_min, z_max = float(np.min(basin_values)), float(np.max(basin_values))

    # Longitud de la ruta D8 más larga hacia aguas arriba desde el outlet.
    # Se construye recorriendo vecinos que descargan a cada celda visitada.
    path_length = np.full(mask.shape, np.nan, dtype=float)
    path_length[outlet_row, outlet_col] = 0.0
    stack = [(outlet_row, outlet_col)]
    while stack:
        cr, cc = stack.pop()
        base_len = path_length[cr, cc]
        for (dr, dc), code in d8.items():
            ur, uc = cr - dr, cc - dc
            if 0 <= ur < mask.shape[0] and 0 <= uc < mask.shape[1] and mask[ur, uc] and dirs[ur, uc] == code:
                step = math.hypot(dr * cell_y, dc * cell_x)
                candidate = base_len + step
                if not np.isfinite(path_length[ur, uc]) or candidate > path_length[ur, uc]:
                    path_length[ur, uc] = candidate
                    stack.append((ur, uc))
    lengths = path_length[mask]
    length_m = float(np.nanmax(lengths)) if np.isfinite(lengths).any() else float("nan")
    if not np.isfinite(length_m) or length_m <= 0:
        raise RuntimeError("No se pudo calcular la longitud del cauce principal por ruta D8.")
    slope = max(0.0, (z_max - outlet_z) / length_m)

    geojson = {
        "type": "FeatureCollection", "name": "microcuenca_denver",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [
            {"type": "Feature", "properties": {"feature": "microcuenca", "area_km2": area_km2,
             "outlet_station_distance_m": outlet_dist_m}, "geometry": mapping(basin_geo)},
            {"type": "Feature", "properties": {"feature": "outlet", "station": STATION},
             "geometry": {"type": "Point", "coordinates": list(project_to_geo(ox, oy))}},
            {"type": "Feature", "properties": {"feature": "pluviometro", "station": STATION},
             "geometry": {"type": "Point", "coordinates": [STATION_LON, STATION_LAT]}},
        ],
    }
    DATA.mkdir(parents=True, exist_ok=True)
    GEOJSON_PATH.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    meta = {
        "status": "ok", "station": STATION,
        "station_coordinates_wgs84": {"latitude": STATION_LAT, "longitude": STATION_LON},
        "area_km2": area_km2, "area_ha": area_km2 * 100,
        "main_channel_length_m": length_m,
        "elevation_min_m": z_min, "elevation_max_m": z_max,
        "outlet_elevation_m": outlet_z, "relief_slope_S0_m_per_m": slope,
        "slope_definition": "(cota máxima de la cuenca - cota outlet)/longitud de ruta D8 más larga; estimación topográfica DEM.",
        "distance_basin_centroid_to_station_m": centroid_dist_m,
        "distance_outlet_to_station_m": outlet_dist_m,
        "outlet_coordinates_utm13_m": {"x": ox, "y": oy},
        "dem_path_relative": "datos/punto2/dem_microcuenca_denver.tif",
        "geojson_path_relative": "datos/punto2/microcuenca_denver.geojson",
        "delineation": "Pysheds D8; fill pits/depressions and resolve flats; outlet candidato cercano a estación con área 0.1–5 km², seleccionado con preferencia por 1.85 km².",
        "caveats": [
            "El Copernicus GLO-30 es DSM e incluye edificios/vegetación; no sustituye un DEM bare-earth ni una validación de drenaje urbano.",
            "La selección automática del outlet identifica una cuenca topográfica candidata cercana al pluviómetro, no una delimitación de obra certificada.",
        ],
    }
    render_microbasin_map(dem_path, meta, geojson)
    return meta, geojson


def render_microbasin_map(dem_path: Path, metadata: dict, geojson: dict) -> None:
    """Renderiza DEM, relieve y geometrÃ­as guardadas sin volver a delimitar."""
    try:
        import matplotlib.pyplot as plt
        import rasterio
        from rasterio.features import rasterize
        from pyproj import Transformer
        from pysheds.grid import Grid
        from shapely.geometry import shape
        from shapely.ops import transform as shapely_transform
    except Exception as exc:
        raise RuntimeError(f"Faltan dependencias cartogrÃ¡ficas para el mapa: {exc}") from exc

    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(float)
        transform, crs = src.transform, src.crs
        nodata, bounds = src.nodata, src.bounds
        height, width = src.height, src.width
    if crs is None:
        raise ValueError("El DEM no declara CRS; no se puede ubicar el mapa.")

    # El enmascaramiento precede al cÃ¡lculo del rango de color y al hillshade.
    invalid = ~np.isfinite(dem) | (dem <= 0) | (dem < 1500) | (dem > 2000)
    if nodata is not None:
        invalid |= np.isclose(dem, nodata)
    valid_values = dem[~invalid]
    if not valid_values.size:
        raise ValueError("No hay cotas reales entre 1500 y 2000 m en el recorte DEM.")
    zmin, zmax = float(valid_values.min()), float(valid_values.max())
    vmin, vmax = (float(value) for value in np.percentile(valid_values, [2, 98]))
    z = np.ma.masked_array(dem, mask=invalid)

    to_dem = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    basin_feature = next(f for f in geojson["features"]
                         if f.get("properties", {}).get("feature") == "microcuenca")
    basin = shapely_transform(to_dem, shape(basin_feature["geometry"]))
    basin_mask = rasterize([(basin, 1)], out_shape=dem.shape, transform=transform,
                           fill=0, all_touched=True).astype(bool) & ~invalid
    centroid = basin.centroid
    ox = float(metadata["outlet_coordinates_utm13_m"]["x"])
    oy = float(metadata["outlet_coordinates_utm13_m"]["y"])
    station_x, station_y = to_dem(STATION_LON, STATION_LAT)
    outlet_row, outlet_col = rasterio.transform.rowcol(transform, ox, oy)
    outlet_row = int(np.clip(outlet_row, 0, dem.shape[0] - 1))
    outlet_col = int(np.clip(outlet_col, 0, dem.shape[1] - 1))

    # Obtiene el cauce de mayor longitud dentro del polÃ­gono existente.
    # No se llama catchment() ni se altera la mÃ¡scara/GeoJSON guardados.
    stream = np.empty((0, 2), dtype=float)
    try:
        grid = Grid.from_raster(str(dem_path))
        raw = grid.read_raster(str(dem_path))
        filled = grid.fill_pits(raw)
        filled = grid.fill_depressions(filled)
        filled = grid.resolve_flats(filled)
        fdir = np.asarray(grid.flowdir(filled, dirmap=(64, 128, 1, 2, 4, 8, 16, 32)), dtype=int)
        d8 = {(0, 1): 1, (1, 1): 2, (1, 0): 4, (1, -1): 8,
              (0, -1): 16, (-1, -1): 32, (-1, 0): 64, (-1, 1): 128}
        distance = np.full(dem.shape, -1.0)
        parent = {}
        distance[outlet_row, outlet_col] = 0.0
        stack = [(outlet_row, outlet_col)]
        dx, dy = abs(float(transform.a)), abs(float(transform.e))
        while stack:
            row, col = stack.pop()
            for (dr, dc), code in d8.items():
                ur, uc = row - dr, col - dc
                if (0 <= ur < dem.shape[0] and 0 <= uc < dem.shape[1]
                        and basin_mask[ur, uc] and fdir[ur, uc] == code):
                    candidate = distance[row, col] + math.hypot(dr * dy, dc * dx)
                    if candidate > distance[ur, uc]:
                        distance[ur, uc] = candidate
                        parent[(ur, uc)] = (row, col)
                        stack.append((ur, uc))
        candidates = np.where(basin_mask & (distance >= 0), distance, -1)
        endpoint = np.unravel_index(int(np.argmax(candidates)), candidates.shape)
        route = [endpoint]
        while route[-1] != (outlet_row, outlet_col) and route[-1] in parent:
            route.append(parent[route[-1]])
        route.reverse()
        stream = np.asarray([rasterio.transform.xy(transform, r, c, offset="center")
                             for r, c in route], dtype=float)
    except Exception as exc:
        print(f"Aviso: cauce no disponible para el mapa ({type(exc).__name__}: {exc}).")

    # Hillshade calculado por gradiente, en unidades horizontales y verticales métricas.
    safe = np.where(invalid, float(np.median(valid_values)), dem)
    gy, gx = np.gradient(safe, abs(float(transform.e)), abs(float(transform.a)))
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    azimuth, altitude = np.deg2rad(315.0), np.deg2rad(45.0)
    shade = np.clip(np.sin(altitude) * np.cos(slope)
                    + np.cos(altitude) * np.sin(slope) * np.cos(azimuth - aspect), 0, 1)
    shade = np.ma.masked_array(shade, mask=invalid)
    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)
    levels = np.arange(np.ceil(zmin / 2) * 2, np.floor(zmax / 2) * 2 + 0.1, 2)
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13, 5.8), dpi=300,
                                   constrained_layout=True)
    image = None
    for ax in (ax0, ax1):
        image = ax.imshow(z, extent=extent, origin="upper", cmap="terrain",
                          vmin=vmin, vmax=vmax, interpolation="nearest", zorder=1)
        ax.imshow(shade, extent=extent, origin="upper", cmap="gray", vmin=0,
                  vmax=1, alpha=0.34, interpolation="nearest", zorder=2)
        polys = [basin] if basin.geom_type == "Polygon" else list(basin.geoms)
        for j, poly in enumerate(polys):
            bx, by = poly.exterior.xy
            ax.plot(bx, by, color="#c8322c", lw=2.4 if ax is ax1 else 1.8,
                    zorder=6, label="Microcuenca (1.03 km²)" if j == 0 else None)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("UTM 13N Este (m)")
        ax.set_ylabel("UTM 13N Norte (m)")

    # Panel izquierdo: contexto regional centrado en outlet, 6 km por lado.
    ax0.set_xlim(ox - 3000, ox + 3000)
    ax0.set_ylim(oy - 3000, oy + 3000)
    ax0.scatter([ox], [oy], marker="*", s=125, c="#172b3a", edgecolor="white",
                linewidth=0.8, zorder=9, label="Outlet")
    ax0.scatter([centroid.x], [centroid.y], marker="D", s=48, c="#f3c33c",
                edgecolor="#473a10", zorder=9, label="Centroide")
    ax0.scatter([station_x], [station_y], marker="^", s=82, c="#2458df",
                edgecolor="white", linewidth=0.8, zorder=9, label="Estación NOAA")
    distance_km = float(metadata.get("distance_basin_centroid_to_station_m", 1079.0)) / 1000
    ax0.annotate(f"Denver Stapleton\nUSW00023062\n{distance_km:.2f} km al SE",
                 (station_x, station_y), xytext=(8, -12), textcoords="offset points",
                 fontsize=8, fontweight="bold", color="#183b91", zorder=10)
    ax0.set_title("Contexto regional + relieve · 6 × 6 km", fontweight="bold")
    ax0.legend(loc="upper left", fontsize=8, framealpha=0.93)

    # Panel derecho: caja de la cuenca y 350 m de margen.
    minx, miny, maxx, maxy = basin.bounds
    ax1.set_xlim(minx - 350, maxx + 350)
    ax1.set_ylim(miny - 350, maxy + 350)
    if len(levels) >= 2:
        cs = ax1.contour(z, levels=levels, colors="#384638", linewidths=0.55,
                         extent=extent, origin="upper", zorder=4)
        ax1.clabel(cs, inline=True, fmt="%.0f m", fontsize=7)
    if len(stream) > 1:
        ax1.plot(stream[:, 0], stream[:, 1], color="#064de0", lw=2.6, zorder=7,
                 label=f"Cauce principal (L = {metadata.get('main_channel_length_m', 2312.5):.1f} m)")
    ax1.scatter([ox], [oy], marker="*", s=135, c="#172b3a", edgecolor="white", zorder=10)
    ax1.annotate(f"Outlet · {metadata.get('outlet_elevation_m', 1607.5):.1f} m",
                 (ox, oy), xytext=(8, -22), textcoords="offset points", fontsize=8,
                 color="#172b3a", fontweight="bold", zorder=11)
    high_row, high_col = np.unravel_index(np.argmax(np.where(basin_mask, dem, -np.inf)), dem.shape)
    high_x, high_y = rasterio.transform.xy(transform, high_row, high_col, offset="center")
    ax1.scatter([high_x], [high_y], marker="^", s=72, c="#e44832", edgecolor="white", zorder=10)
    ax1.annotate(f"Punto más alto · {dem[high_row, high_col]:.1f} m",
                 (high_x, high_y), xytext=(8, 7), textcoords="offset points", fontsize=8,
                 color="#922416", fontweight="bold", zorder=11)
    ax1.set_title("Zoom a la cuenca · curvas cada 2 m", fontweight="bold")
    ax1.legend(loc="lower left", fontsize=8, framealpha=0.93)

    # Escala grÃ¡fica de 500 m, dibujada en coordenadas UTM.
    sx, sy = maxx - 700, miny - 250
    ax1.plot([sx, sx + 500], [sy, sy], color="#111", lw=3.2, zorder=12)
    ax1.plot([sx, sx], [sy - 20, sy + 20], color="#111", lw=1.5, zorder=12)
    ax1.plot([sx + 500, sx + 500], [sy - 20, sy + 20], color="#111", lw=1.5, zorder=12)
    ax1.text(sx + 250, sy + 34, "500 m", ha="center", fontsize=8, fontweight="bold", zorder=12)
    cbar = fig.colorbar(image, ax=ax1, fraction=0.046, pad=0.025)
    cbar.set_label("Elevación (m s.n.m.)")
    cbar.set_ticks(np.linspace(vmin, vmax, 6))
    fig.suptitle("Microcuenca Denver Stapleton · DEM Copernicus GLO-30",
                 fontsize=14, fontweight="bold")
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Figura cartogrÃ¡fica actualizada: {FIG_PATH.relative_to(ROOT)}")


ATLAS_DURATIONS_MIN = (60, 120, 180, 360, 720, 1440)
ATLAS_RETURN_PERIODS = (1, 2, 5, 10, 25, 50, 100, 200, 500, 1000)
ATLAS_DURATION_ROW = {duration: index for index, duration in enumerate(
    (5, 10, 15, 30, 60, 120, 180, 360, 720, 1440,
     2880, 4320, 5760, 10080, 14400, 28800, 43200, 64800, 86400))}


def _atlas_matrix(response_text: str, variable: str, required: bool = True) -> np.ndarray | None:
    """Extrae una matriz JS del CGI NOAA sin evaluar código ejecutable."""
    match = re.search(
        rf"(?:var\s+)?{re.escape(variable)}\s*=\s*(\[[\s\S]*?\])\s*;?\s*(?:\r?\n|$)",
        response_text,
    )
    if not match:
        if required:
            raise RuntimeError(f"La respuesta HDSC no contiene la matriz {variable}=[...].")
        return None
    try:
        # cgi_readH5.py serializa matrices como listas Python con celdas en
        # comillas simples y un punto y coma final: `quantiles = [['14.1']];`.
        # literal_eval evita ejecutar el resto del JavaScript de la respuesta.
        rhs = match.group(1).strip().removesuffix(";").strip()
        parsed = ast.literal_eval(rhs)

        def as_float(value):
            if value is None:
                return np.nan
            if isinstance(value, str):
                value = value.strip()
                if value.casefold() in {"", "nan", "none", "null", "-infinity", "infinity"}:
                    return np.nan
            try:
                return float(value)
            except (TypeError, ValueError):
                return np.nan

        matrix = np.asarray([[as_float(cell) for cell in row] for row in parsed], dtype=float)
    except Exception as exc:
        raise RuntimeError(f"No se pudo decodificar la matriz HDSC '{variable}': {exc}") from exc
    if matrix.ndim != 2:
        raise RuntimeError(f"La matriz HDSC '{variable}' no es bidimensional: shape={matrix.shape}.")
    # HDSC entrega normalmente [duraciones × ARI]; tolera también el orden
    # transpuesto por si cambia la serialización del CGI.
    if matrix.shape[0] == len(ATLAS_DURATION_ROW) and matrix.shape[1] >= len(ATLAS_RETURN_PERIODS):
        return matrix
    if matrix.shape[1] == len(ATLAS_DURATION_ROW) and matrix.shape[0] >= len(ATLAS_RETURN_PERIODS):
        return matrix.T
    raise RuntimeError(
        f"Dimensiones inesperadas en '{variable}': {matrix.shape}; "
        f"se esperaban {len(ATLAS_DURATION_ROW)} duraciones y al menos {len(ATLAS_RETURN_PERIODS)} ARI."
    )


def parse_atlas14_response(response_text: str) -> pd.DataFrame:
    """Convierte matrices quantiles/lower/upper del endpoint HDSC a filas."""
    quantiles = _atlas_matrix(response_text, "quantiles", required=True)
    lower = _atlas_matrix(response_text, "lower", required=False)
    upper = _atlas_matrix(response_text, "upper", required=False)
    rows = []
    for duration_min in ATLAS_DURATIONS_MIN:
        duration_idx = ATLAS_DURATION_ROW[duration_min]
        for period in (2, 5, 10, 25, 50, 100):
            period_idx = ATLAS_RETURN_PERIODS.index(period)
            depth = float(quantiles[duration_idx, period_idx])
            if not np.isfinite(depth):
                raise RuntimeError(
                    f"NOAA HDSC cuantiles faltantes para {duration_min} min, T={period} años."
                )
            lower_depth = (float(lower[duration_idx, period_idx])
                           if lower is not None else np.nan)
            upper_depth = (float(upper[duration_idx, period_idx])
                           if upper is not None else np.nan)
            rows.append({
                "duration_min": duration_min, "T_y": period,
                "atlas14_depth_mm": depth,
                "atlas14_intensity_mmh": depth / (duration_min / 60),
                "atlas14_lower90_depth_mm": lower_depth,
                "atlas14_upper90_depth_mm": upper_depth,
                "atlas14_lower90_intensity_mmh": lower_depth / (duration_min / 60),
                "atlas14_upper90_intensity_mmh": upper_depth / (duration_min / 60),
            })
    result = pd.DataFrame(rows)
    if len(result) != 36:
        raise RuntimeError(f"HDSC produjo {len(result)} comparaciones; se esperaban 36.")
    return result


def get_noaa_atlas14() -> tuple[pd.DataFrame, str]:
    errors = []
    for endpoint in NOAA_ENDPOINTS:
        try:
            response = requests.get(
                endpoint, params=NOAA_QUERY, timeout=60,
                headers={"User-Agent": "punto2-hydrology-validation/1.0"},
            )
            response.raise_for_status()
            atlas = parse_atlas14_response(response.text)
            return atlas, response.url
        except Exception as exc:
            errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Fallaron los endpoints HDSC: " + " || ".join(errors))


def event_return_period(values: np.ndarray, event_value: float, module) -> float:
    params = module.fit_distribution(values, "LP3", "LMOM")
    non_exceedance = float(module.cdf(np.asarray([event_value]), "LP3", params)[0])
    exceedance = max(1e-12, 1.0 - non_exceedance)
    return 1.0 / exceedance


def bootstrap_event_frequency(values: np.ndarray, event_value: float, module,
                              n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    sampled_T = []
    errors = 0
    for _ in range(n_boot):
        sample = rng.choice(values, size=len(values), replace=True)
        try:
            value = event_return_period(sample, event_value, module)
            if np.isfinite(value):
                sampled_T.append(min(value, 1e9))
        except Exception:
            errors += 1
    if len(sampled_T) < max(100, int(n_boot * 0.5)):
        raise RuntimeError(f"Bootstrap insuficiente: {len(sampled_T)}/{n_boot} réplicas válidas.")
    lo, hi = np.percentile(sampled_T, [2.5, 97.5])
    return {"T_years": event_return_period(values, event_value, module),
            "T_ci95_low_years": float(lo), "T_ci95_high_years": float(hi),
            "bootstrap_success": len(sampled_T), "bootstrap_attempts": n_boot,
            "bootstrap_failures": errors, "bootstrap_seed": seed}


def load_station_annual_maxima() -> tuple[pd.DataFrame, np.ndarray]:
    path = PRODUCTS / "maximos_anuales_intensidad.csv"
    maxima = pd.read_csv(path, low_memory=False)
    required = {"hydro_year", "intensity_1h_mmh"}
    if not required.issubset(maxima.columns):
        raise ValueError(f"Columnas faltantes en {path.name}: {sorted(required - set(maxima.columns))}")
    values = pd.to_numeric(maxima["intensity_1h_mmh"], errors="coerce").dropna().to_numpy(float)
    values = values[np.isfinite(values) & (values > 0)]
    if len(values) < 10:
        raise ValueError(f"Solo hay {len(values)} máximos válidos; insuficientes para análisis bootstrap.")
    return maxima, values


def historical_event(maxima: pd.DataFrame) -> dict:
    """Obtiene el evento de la fecha dada desde la serie limpia y aplica Weiss."""
    date = "1965-07-26"
    path = DATA / "precip_horaria_limpia.csv"
    hourly = pd.read_csv(path, usecols=["timestamp", "precip_mm", "precip_state"],
                         low_memory=False)
    hourly["timestamp"] = pd.to_datetime(hourly["timestamp"], errors="coerce", utc=True)
    hourly["precip_mm"] = pd.to_numeric(hourly["precip_mm"], errors="coerce")
    day = hourly[hourly.timestamp.dt.strftime("%Y-%m-%d") == date]
    day = day[day["precip_mm"].notna() & (day["precip_mm"] >= 0)]
    if day.empty:
        raise ValueError(f"No hay horas válidas en la serie local para el evento {date}; no se imputará intensidad.")
    raw_max = float(day["precip_mm"].max())
    weiss = 1 / (1 - 1 / 8)
    return {"date": date, "intensity_mmh": raw_max * weiss,
            "hourly_fixed_clock_mm": raw_max, "weiss_factor": weiss,
            "source": "datos/punto2/precip_horaria_limpia.csv",
            "basis": "Máximo horario medido el 1965-07-26 multiplicado por Weiss fW=1/(1−1/8)."}


def run_validation() -> tuple[pd.DataFrame, dict]:
    maxima, sample = load_station_annual_maxima()
    module = load_lmom_module()
    local_idf = pd.read_csv(PRODUCTS / "tabla_idf_completa.csv", low_memory=False)
    idf_parameters = pd.read_csv(PRODUCTS / "parametros_idf.csv", low_memory=False)
    selected_parameters = idf_parameters[idf_parameters["formulacion"].astype(str).str.casefold() == "talbot-wenzel"]
    if selected_parameters.empty:
        raise ValueError("parametros_idf.csv no contiene la formulación Talbot-Wenzel solicitada.")
    tw = selected_parameters.iloc[0]
    local_idf = local_idf[(local_idf["model"] == "Talbot-Wenzel")].copy()
    if local_idf.empty:
        raise ValueError("tabla_idf_completa.csv no contiene filas del modelo Talbot-Wenzel.")
    official_error = None
    try:
        atlas, atlas_url = get_noaa_atlas14()
    except Exception as exc:
        atlas = pd.DataFrame()
        atlas_url = " | ".join(NOAA_ENDPOINTS)
        official_error = f"{type(exc).__name__}: {exc}"
        print(f"ERROR Atlas 14: {official_error}")
    result_rows = []
    if not atlas.empty:
        atlas["duration_h"] = atlas["duration_min"] / 60
        local_idf["duration_h"] = pd.to_numeric(local_idf["duration_h"], errors="coerce")
        local_idf["return_period_y"] = pd.to_numeric(local_idf["return_period_y"], errors="coerce")
        local_idf["duration_h"] = pd.to_numeric(local_idf["duration_h"], errors="coerce")
        local_idf["return_period_y"] = pd.to_numeric(local_idf["return_period_y"], errors="coerce")
        for duration_h in (1, 2, 3, 6, 12, 24):
            duration_min = float(duration_h * 60)
            for T in (2, 5, 10, 25, 50, 100):
                loc = local_idf[(local_idf.duration_h == duration_h) &
                                (local_idf.return_period_y == T)]
                off = atlas[(np.isclose(atlas.duration_min, duration_min)) & (atlas.T_y == T)]
                if loc.empty or off.empty:
                    continue
                local = loc.iloc[0]
                official = off.iloc[0]
                atlas_i = float(official.atlas14_intensity_mmh)
                ours = float(local.intensity_mmh)
                result_rows.append({
                    "record_type": "comparacion_atlas14",
                    "duration_min": duration_min, "T_y": T,
                    "our_distribution": "LP3/LMOM", "our_idf_model": "Talbot-Wenzel",
                    "idf_parameter_a": tw.get("a"), "idf_parameter_m": tw.get("m"),
                    "idf_parameter_b_h": tw.get("b_h"), "idf_parameter_c": tw.get("c"),
                    "our_intensity_mmh": ours, "our_depth_mm": float(local.depth_mm),
                    "atlas14_station": "DENVER-STAPLETON / Denver PFDS point",
                    "atlas14_url": atlas_url, "atlas14_depth_mm": float(official.atlas14_depth_mm),
                    "atlas14_intensity_mmh": atlas_i,
                    "atlas14_lower90_depth_mm": official.atlas14_lower90_depth_mm,
                    "atlas14_upper90_depth_mm": official.atlas14_upper90_depth_mm,
                    "atlas14_lower90_intensity_mmh": official.atlas14_lower90_intensity_mmh,
                    "atlas14_upper90_intensity_mmh": official.atlas14_upper90_intensity_mmh,
                    "difference_ours_minus_atlas_mmh": ours - atlas_i,
                    "relative_bias_pct": (ours - atlas_i) / atlas_i * 100 if atlas_i else np.nan,
                    "atlas14_basis": "NOAA HDSC cgi_readH5.py; PDS point depth; límites oficiales del 90% si la respuesta los incluye.",
                    "method_note": "Nuestra AMS LP3/LMOM + Talbot-Wenzel puede diferir por AMS/PDS, periodo de datos, escala puntual/espacial, ajuste regional de frecuencia (RFA/FRA) de Atlas 14 y Weiss; la diferencia relativa es descriptiva, no demuestra sesgo sistemático sin una comparación homogénea.",
                })
    else:
        result_rows.append({"record_type": "error_atlas14", "atlas14_station": "DENVER-STAPLETON",
                            "atlas14_url": atlas_url, "source_error": official_error,
                            "method_note": "Sin cuantiles oficiales descargables no se calcula una diferencia ni se rellena con valores supuestos."})

    # Añade razón IDF_malla/IDF_puntual solo cuando existen IDF de celda
    # calculadas desde series reales, con sus periodos y escalas declarados.
    for product, grid_path in GRID_IDF_PATHS.items():
        if not grid_path.exists():
            result_rows.append({
                "record_type": "comparacion_idf_malla_no_disponible",
                "grid_product": product,
                "grid_source_expected": str(grid_path.relative_to(ROOT)),
                "grid_method_note": (
                    "Sin IDF derivada de la celda local no se calcula la razón malla/punto ni se "
                    "inventan valores. La razón puede reflejar suavizado espacial/FRA y sesgo "
                    "del producto, además de diferencias de periodo y muestreo."
                ),
            })
            continue
        grid = pd.read_csv(grid_path, low_memory=False)
        required = {"duration_h", "T_y", "intensity_mmh"}
        if not required.issubset(grid.columns):
            raise ValueError(f"{grid_path.relative_to(ROOT)} requiere {sorted(required)}.")
        for column in required:
            grid[column] = pd.to_numeric(grid[column], errors="coerce")
        for duration_h in (1, 2, 3, 6, 12, 24):
            for T in (2, 5, 10, 25, 50, 100):
                cell = grid[np.isclose(grid.duration_h, duration_h) & np.isclose(grid.T_y, T)]
                point = local_idf[np.isclose(local_idf.duration_h, duration_h) &
                                  np.isclose(local_idf.return_period_y, T)]
                if cell.empty or point.empty:
                    continue
                grid_i, point_i = float(cell.iloc[0].intensity_mmh), float(point.iloc[0].intensity_mmh)
                result_rows.append({
                    "record_type": "comparacion_idf_malla", "grid_product": product,
                    "duration_min": duration_h * 60, "T_y": T,
                    "our_distribution": "LP3/LMOM", "our_idf_model": "Talbot-Wenzel",
                    "our_intensity_mmh": point_i, "grid_intensity_mmh": grid_i,
                    "idf_grid_over_point_ratio": grid_i / point_i if point_i else np.nan,
                    "grid_source": str(grid_path.relative_to(ROOT)),
                    "grid_method_note": "IDF_malla/IDF_puntual es descriptiva: separa FRA/suavizado espacial de sesgo del producto solo con análisis homogéneo de periodo y muestreo.",
                })

    try:
        historic = historical_event(maxima)
        historic_frequency = bootstrap_event_frequency(sample, historic["intensity_mmh"], module)
        result_rows.append({"record_type": "evento_historico_1965", "event_date": historic["date"],
                            "event_intensity_mmh": historic["intensity_mmh"],
                            "event_source": historic["source"], "event_basis": historic["basis"], **historic_frequency,
                            "frequency_note": "Periodo de retorno AMS de la muestra aceptada, estimado con LP3/LMOM; bootstrap no paramétrico de máximos anuales."})
    except Exception as exc:
        result_rows.append({"record_type": "error_evento_historico_1965", "source_error": f"{type(exc).__name__}: {exc}"})
        print(f"ERROR evento histórico: {type(exc).__name__}: {exc}")

    recent = RECENT_EVENT
    try:
        recent_frequency = bootstrap_event_frequency(sample, recent["intensity_mmh"], module)
        result_rows.append({"record_type": "evento_reciente_denver", "event_date": recent["date"],
                            "event_intensity_mmh": recent["intensity_mmh"],
                            "event_source": recent["source"], "event_basis": recent["basis"],
                            "event_is_lower_bound": True, **recent_frequency,
                            "frequency_note": "T se evalúa en el umbral publicado de 50.8 mm/h; al ser un ‘hasta’ espacial y subhorario, el resultado es una referencia regional, no un T puntual observado."})
    except Exception as exc:
        result_rows.append({"record_type": "error_evento_reciente", "source_error": f"{type(exc).__name__}: {exc}"})
        print(f"ERROR evento reciente: {type(exc).__name__}: {exc}")
    result = pd.DataFrame(result_rows)
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    result.to_csv(COMPARE_PATH, index=False, encoding="utf-8-sig")
    return result, {"atlas14_error": official_error, "atlas14_rows": 0 if atlas.empty else len(atlas),
                    "event_records": int(result.record_type.astype(str).str.startswith("evento_").sum())}


def main() -> None:
    if "--map-only" in sys.argv:
        # Solo actualiza el PNG: no ejecuta delineaciÃ³n/validaciÃ³n ni escribe
        # metadatos o GeoJSON, conservando los productos ya aprobados.
        for required in (DEM_PATH, GEOJSON_PATH, METADATA_PATH):
            if not required.exists():
                raise FileNotFoundError(f"Se requiere el artefacto local {required.relative_to(ROOT)}")
        with METADATA_PATH.open(encoding="utf-8") as handle:
            existing_metadata = json.load(handle)
        with GEOJSON_PATH.open(encoding="utf-8") as handle:
            existing_geojson = json.load(handle)
        render_microbasin_map(DEM_PATH, existing_metadata, existing_geojson)
        print("Modo --map-only: delimitaciÃ³n, GeoJSON y metadatos permanecen sin cambios.")
        return

    DATA.mkdir(parents=True, exist_ok=True)
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    print("=== 05a · DEM real y validación de IDF ===")
    print(f"Raíz del proyecto: {ROOT}")
    dem_meta = {"status": "pending", "station": STATION,
                "station_coordinates_wgs84": {"latitude": STATION_LAT, "longitude": STATION_LON},
                "dem_source": "Copernicus GLO-30 public AWS COG", "dem_url": COP_DEM_URL}
    try:
        if DEM_PATH.exists():
            print(f"Reutilizando DEM local existente: {DEM_PATH.relative_to(ROOT)}")
            dem_meta.update({"status": "local_dem_present", "dem_path_relative": str(DEM_PATH.relative_to(ROOT))})
        else:
            _, download_meta = download_crop_dem()
            dem_meta.update(download_meta)
            print(f"DEM recortado y guardado: {DEM_PATH.relative_to(ROOT)}")
        delineation, _ = delineate_basin(DEM_PATH)
        dem_meta.update(delineation)
        print("Microcuenca delimitada:")
        for key in ("area_km2", "main_channel_length_m", "elevation_min_m", "elevation_max_m",
                    "outlet_elevation_m", "relief_slope_S0_m_per_m", "distance_basin_centroid_to_station_m"):
            print(f"  {key}: {dem_meta[key]}")
        print(f"GeoJSON: {GEOJSON_PATH.relative_to(ROOT)}")
        print(f"Figura DEM: {FIG_PATH.relative_to(ROOT)}")
    except Exception as exc:
        dem_meta.update({"status": "error", "error_type": type(exc).__name__,
                         "error": str(exc), "traceback": traceback.format_exc()})
        print(f"ERROR explícito al descargar/delimitar DEM: {type(exc).__name__}: {exc}")
        print("No se crearán GeoJSON ni figura con límites/cotas supuestos.")
    write_json(METADATA_PATH, dem_meta)
    print(f"Metadatos de DEM/estación: {METADATA_PATH.relative_to(ROOT)}")

    try:
        result, status = run_validation()
        print("\nValidación NOAA Atlas 14 y eventos:")
        print(f"  Endpoints NOAA HDSC: {NOAA_ENDPOINTS} con {NOAA_QUERY}")
        print(f"  Filas de comparación oficial: {status['atlas14_rows']}")
        print(f"  Filas de eventos calculados: {status['event_records']}")
        if status["atlas14_error"]:
            print(f"  Error oficial registrado: {status['atlas14_error']}")
        print(result.to_string(index=False, max_rows=40))
        print(f"CSV de comparación: {COMPARE_PATH.relative_to(ROOT)}")
    except Exception as exc:
        print(f"ERROR explícito en validación IDF/eventos: {type(exc).__name__}: {exc}")
        pd.DataFrame([{"record_type": "error_general", "source_error": f"{type(exc).__name__}: {exc}"}]).to_csv(
            COMPARE_PATH, index=False, encoding="utf-8-sig")
        print(f"Diagnóstico CSV escrito: {COMPARE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
