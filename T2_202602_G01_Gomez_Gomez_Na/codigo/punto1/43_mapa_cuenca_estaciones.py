"""Mapa de la cuenca del Fonce con las estaciones y los puntos que usa la Tarea 2 (punto 1, figura 1 del informe).

Parte del mapa de la Tarea 1 (Analisis_De_Cuenca/scripts/08_mapas_y_pixeles.py: DEM ALOS PALSAR con sombreado) y
resalta lo que entra en esta tarea:
    - estaciones climatológicas del IDEAM (DHIME): T, HR, brillo solar y viento para la ETo de estación (fase 3) y la HR
      media del texto de Hargreaves (script 30). Andalucía queda fuera de la divisoria y solo entra en esa HR.
    - los 6 puntos de ERA5-Land con sus regiones de Voronoi (la ETo de la cuenca).
    - los pluviómetros dentro de la divisoria (la lluvia PL del balance, script 15) y el aforo de San Gil (Q).

Lee (datos/punto1/): dem/dem_fonce_alos_12m.tif, camels_col/boundaries/.../CAMELS_COL_catchments_boundaries.shp,
    ideam/cne_ideam.csv, ideam/pluviometros/dhime/dhime_mensual_1998_2022_8est.zip,
    era5land_puntos/regiones_voronoi_puntos.geojson
Escribe: productos/punto1/mapa_cuenca_estaciones.png

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/43_mapa_cuenca_estaciones.py
"""

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import LightSource
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
DATOS = RAIZ_ENTREGA / "datos" / "punto1"
DEM = DATOS / "dem" / "dem_fonce_alos_12m.tif"
ARCHIVO_CUENCA = (DATOS / "camels_col" / "boundaries" / "03_CAMELS_COL_Basin_boundary"
                  / "CAMELS_COL_catchments_boundaries.shp")
ARCHIVO_CNE = DATOS / "ideam" / "cne_ideam.csv"
ARCHIVO_PLUVIOMETROS = DATOS / "ideam" / "pluviometros" / "dhime" / "dhime_mensual_1998_2022_8est.zip"
ARCHIVO_VORONOI = DATOS / "era5land_puntos" / "regiones_voronoi_puntos.geojson"
SALIDA = RAIZ_ENTREGA / "productos" / "punto1" / "mapa_cuenca_estaciones.png"
FACTOR = 4   # 12.5 m -> 50 m, suficiente para una figura

# Estaciones climatológicas usadas (scripts 12, 13, 18, 30). Mogotes-AUT y la Escuela Agrícola Mogotes tienen las
# mismas coordenadas en el CNE: van en un solo símbolo.
CLIMA = {
    "Mogotes (EA y AUT)": ([24025040, 24025090], "T, HR, brillo, viento"),
    "Charalá": ([24025050], "T, HR, brillo"),
    "La Sierra-AUT": ([24025030], "T, HR, brillo"),
    "Andalucía": ([24035350], "solo HR"),
}
NOMBRES = {24020040: "Encino", 24020080: "Valle de San José", 24020120: "Coromoro", 24020220: "Las Pavas",
           24020230: "Pueblo Viejo", 24025040: "Esc. Agrícola Mogotes", 24025050: "Charalá"}
COLOR_PLUVIO, COLOR_CLIMA, COLOR_ERA5 = "#D1741B", "#0072B2", "#6A3D9A"
HALO = [pe.withStroke(linewidth=2.6, foreground="white")]


def main():
    cuencas = gpd.read_file(ARCHIVO_CUENCA)
    cuenca = cuencas[cuencas["IDEAM_CODE"].astype(str) == "24027010"].to_crs(4326)
    assert len(cuenca) == 1

    cne = pd.read_csv(ARCHIVO_CNE, dtype={"codigo": str})
    cne["codigo"] = cne["codigo"].astype(int)
    cne = cne.set_index("codigo")

    with zipfile.ZipFile(ARCHIVO_PLUVIOMETROS) as z:
        crudo = z.read(z.namelist()[0])
    texto = crudo.decode("utf-8") if b"\xc3" in crudo else crudo.decode("latin-1")
    codigos = pd.read_csv(io.StringIO(texto))["CodigoEstacion"].unique()
    pl = cne.loc[codigos]
    pl = gpd.GeoDataFrame(pl, geometry=gpd.points_from_xy(pl["longitud"], pl["latitud"]), crs=4326)
    pl = pl[pl.within(cuenca.geometry.iloc[0])]
    assert len(pl) == 7, len(pl)

    filas = []
    for nombre, (cods, variables) in CLIMA.items():
        r = cne.loc[cods[0]]
        filas.append({"nombre": nombre, "variables": variables, "altitud": r["altitud"],
                      "lon": r["longitud"], "lat": r["latitud"]})
    clima = pd.DataFrame(filas)
    clima = gpd.GeoDataFrame(clima, geometry=gpd.points_from_xy(clima["lon"], clima["lat"]), crs=4326)

    voronoi = gpd.read_file(ARCHIVO_VORONOI)
    era5 = gpd.GeoDataFrame(voronoi[["punto"]], geometry=gpd.points_from_xy(voronoi["lon"], voronoi["lat"]), crs=4326)
    aforo = gpd.GeoDataFrame(geometry=gpd.points_from_xy([cne.loc[24027010, "longitud"]],
                                                         [cne.loc[24027010, "latitud"]]), crs=4326)

    with rasterio.open(DEM) as src:
        crs = src.crs
        cuenca_utm = cuenca.to_crs(crs)
        todos = pd.concat([cuenca_utm.geometry, clima.to_crs(crs).geometry])
        xmin, ymin, xmax, ymax = todos.total_bounds
        pad = 3000
        win = (from_bounds(xmin - pad, ymin - pad, xmax + pad, ymax + pad, src.transform)
               .round_offsets().round_lengths())
        alto, ancho = int(win.height // FACTOR), int(win.width // FACTOR)
        z = src.read(1, window=win, out_shape=(alto, ancho), masked=True).astype("float32").filled(np.nan)
        tr = src.window_transform(win) * rasterio.Affine.scale(win.width / ancho, win.height / alto)

    fuera = geometry_mask(cuenca_utm.geometry, out_shape=z.shape, transform=tr)
    z_cuenca = np.where(fuera, np.nan, z)
    res = abs(tr.a)
    ext = (tr.c, tr.c + tr.a * z.shape[1], tr.f + tr.e * z.shape[0], tr.f)
    sombra = LightSource(azdeg=315, altdeg=45).hillshade(np.nan_to_num(z, nan=np.nanmean(z)), vert_exag=2,
                                                        dx=res, dy=res)

    fig, ax = plt.subplots(figsize=(6.6, 8.6), constrained_layout=True)
    ax.imshow(np.where(fuera, sombra, np.nan), cmap="gray", extent=ext, alpha=0.35, vmin=0, vmax=1)
    ax.imshow(np.where(fuera, np.nan, sombra), cmap="gray", extent=ext, vmin=0, vmax=1)
    im = ax.imshow(z_cuenca, cmap="terrain", extent=ext, alpha=0.6,
                   vmin=np.nanpercentile(z_cuenca, 0.5) - 400, vmax=np.nanmax(z_cuenca))
    voronoi.to_crs(crs).boundary.plot(ax=ax, color=COLOR_ERA5, lw=0.9, ls="--", alpha=0.8)
    cuenca_utm.boundary.plot(ax=ax, color="k", lw=1.8)
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])

    p = pl.to_crs(crs)
    ax.scatter(p.geometry.x, p.geometry.y, s=30, color=COLOR_PLUVIO, edgecolor="k", lw=0.5, zorder=5,
               label=f"pluviómetro del IDEAM ({len(p)}): lluvia $P_L$")
    # Esc. Agrícola Mogotes y Charalá son pluviómetro y estación climatológica a la vez.
    for codigo, r in p.iterrows():
        if codigo in (24025040, 24025050):   # el rótulo de la estación climatológica ya los nombra
            continue
        ax.annotate(NOMBRES[codigo], (r.geometry.x, r.geometry.y), xytext=(5, -9), textcoords="offset points",
                    fontsize=6.5, color="#7A3E00", path_effects=HALO)

    c = clima.to_crs(crs)
    ax.scatter(c.geometry.x, c.geometry.y, marker="s", s=120, facecolor="none", edgecolor=COLOR_CLIMA, lw=2.2,
               zorder=6, label="estación climatológica del IDEAM")
    for _, r in c.iterrows():
        izquierda = r["nombre"] == "Mogotes (EA y AUT)"
        abajo = r["nombre"] == "Charalá"
        ax.annotate(f"{r['nombre']} ({r['altitud']:.0f} m)\n{r['variables']}", (r.geometry.x, r.geometry.y),
                    xytext=(-9 if izquierda else 9, -7 if abajo else 4), textcoords="offset points",
                    ha="right" if izquierda else "left", va="top" if abajo else "baseline", fontsize=7.8,
                    weight="bold", color=COLOR_CLIMA,
                    path_effects=HALO, zorder=7)

    e = era5.to_crs(crs)
    ax.scatter(e.geometry.x, e.geometry.y, marker="D", s=46, color=COLOR_ERA5, edgecolor="white", lw=0.8, zorder=6,
               label="punto de ERA5-Land (6) y su región de Voronoi")
    for _, r in e.iterrows():
        ax.annotate(f"P{r['punto']}", (r.geometry.x, r.geometry.y), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=8, weight="bold", color=COLOR_ERA5, path_effects=HALO, zorder=7)

    a = aforo.to_crs(crs)
    ax.scatter(a.geometry.x, a.geometry.y, marker="v", s=90, color="k", edgecolor="white", lw=0.8, zorder=6,
               label="aforo de San Gil: caudal Q")

    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.9)
    cb = fig.colorbar(im, ax=ax, shrink=0.55, pad=0.02)
    cb.set_label("elevación (m s.n.m.)")
    ax.set_xlabel(f"este (m, {crs.to_string()})")
    ax.set_ylabel("norte (m)")
    ax.ticklabel_format(style="plain")
    ax.tick_params(labelsize=7)
    fig.savefig(SALIDA, dpi=170)
    print(f"Listo: {SALIDA}")


if __name__ == "__main__":
    main()
