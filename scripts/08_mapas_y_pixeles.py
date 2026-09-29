"""Figuras de la cuenca del Fonce para el reporte HTML.

  1. reporte/figuras/dem_fonce.png    — DEM ALOS PALSAR (12.5 m, remuestreado a ~50 m) recortado a la cuenca de San Gil,
                                         con sombreado, la estación de aforo de San Gil y los pluviómetros que se usan.
  2. reporte/figuras/imerg_pixeles.png — píxeles de IMERG (0.1°) que tocan la cuenca, coloreados por la
                                         precipitación media anual 1998–2022 y con la fracción de cada píxel
                                         dentro de la cuenca (el peso que usa scripts/05_imerg_mensual_cuencas.py).
  3. reporte/figuras/era5land_pixeles.png — píxeles de ERA5-Land (0.1°) que tocan la cuenca, coloreados por la
                                         temperatura media del aire a 2 m, 1998–2022. Los datos los baja
                                         scripts/06_era5land_temperatura.py a out/era5land_pixeles_fonce.csv.

El DEM se lee solo en la ventana de la cuenca (lectura por bloques), no se copia el archivo completo.
"""
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask
from shapely.geometry import box
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from matplotlib.ticker import MultipleLocator
import matplotlib.patheffects as pe

DEM = Path("data/dem/dem_fonce_alos_12m.tif")   # recorte del mosaico nacional (scripts/03_recorte_dem.py)
FACTOR = 4                     # 12.5 m -> 50 m (suficiente para una figura)
OUT = Path("reporte/figuras"); OUT.mkdir(parents=True, exist_ok=True)

ESTACIONES = {
    24027010: "San Gil", 24027070: "Mérida", 24027030: "Nemizaque",
    24027050: "Puente Llano", 24027040: "Puente Cabra", 24027060: "Puente Arco",
}
RIO = {24027010: "Fonce", 24027070: "Fonce", 24027030: "Pienta", 24027050: "Taquiza",
       24027040: "Mogoticos", 24027060: "Monchía"}
# Los pluviómetros del IDEAM bajados del portal DHIME con serie mensual en 1998-2022. El catálogo
# trae las coordenadas, la altitud y si la estación cae dentro de la divisoria de San Gil. En los
# mapas se dibujan solo los que están DENTRO, que son los que entran al promedio de la red; el que
# queda fuera (Mamonal El Hacienda, vertiente del Chicamocha) se excluye del análisis y del mapa.
CAT_PLUVIO = "out/pluviometros_fonce_catalogo.csv"
COLOR_PLUVIO = "#D1741B"
ID_PRINCIPAL = 24027010

cuencas = gpd.read_file("out/shp_fonce/cuencas_fonce.shp")
m = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id")
aforos = gpd.GeoDataFrame(
    {"gauge_id": list(ESTACIONES)},
    geometry=gpd.points_from_xy(m.loc[list(ESTACIONES), "lon_wgs84"], m.loc[list(ESTACIONES), "lat_wgs84"]),
    crs=4326)
madre = cuencas[cuencas.gauge_id == ID_PRINCIPAL]
aforo_sg = aforos[aforos.gauge_id == ID_PRINCIPAL]

cat_pluvio = pd.read_csv(CAT_PLUVIO)
cat_pluvio["etiqueta"] = (cat_pluvio["nombre"].str.replace(r"\s*\[\d+\]", "", regex=True)
                          .str.title().str.replace(" De ", " de "))
pluvio = gpd.GeoDataFrame(
    cat_pluvio[cat_pluvio.dentro_cuenca].copy(),
    geometry=gpd.points_from_xy(cat_pluvio.loc[cat_pluvio.dentro_cuenca, "longitud"],
                                cat_pluvio.loc[cat_pluvio.dentro_cuenca, "latitud"]),
    crs=4326)
fuera_cuenca = int((~cat_pluvio.dentro_cuenca).sum())
print(f"pluviómetros en el mapa: {len(pluvio)} dentro de la cuenca "
      f"({fuera_cuenca} excluido por quedar fuera de la divisoria)")


def rotular(ax, gdf, columna, dy=3, tam=8):
    """Etiqueta cada punto. Los del tercio derecho se rotulan hacia la izquierda para que el texto
    no se salga del mapa; requiere que los límites del eje ya estén fijados."""
    x0, x1 = ax.get_xlim()
    corte = x0 + 0.62 * (x1 - x0)
    for _, r in gdf.iterrows():
        a_la_izquierda = r.geometry.x > corte
        ax.annotate(r[columna], (r.geometry.x, r.geometry.y),
                    xytext=(-7 if a_la_izquierda else 7, dy), textcoords="offset points",
                    ha="right" if a_la_izquierda else "left", fontsize=tam,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])


def dibujar_estaciones(ax, crs=None, rotulos=True):
    """Aforo de San Gil (triángulo negro) y los pluviómetros que se usan (círculos naranjas)."""
    af = aforo_sg if crs is None else aforo_sg.to_crs(crs)
    pl = pluvio if crs is None else pluvio.to_crs(crs)
    ax.scatter(af.geometry.x, af.geometry.y, marker="v", s=85, color="k", edgecolor="white",
               linewidth=0.8, zorder=5, label="aforo de San Gil (salida)")
    ax.scatter(pl.geometry.x, pl.geometry.y, marker="o", s=62, color=COLOR_PLUVIO, edgecolor="k",
               linewidth=0.6, zorder=5, label=f"pluviómetro del IDEAM ({len(pl)})")
    rotular(ax, af.assign(txt="San Gil"), "txt")
    if rotulos:
        # la altitud va en la etiqueta porque la lluvia de esta cuenca cambia sobre todo con la altura
        alturas = pl.altitud.astype(float).round().astype(int).astype(str)
        rotular(ax, pl.assign(txt=pl.etiqueta + " (" + alturas + " m)"), "txt", tam=7.2)
    ax.legend(loc="lower left", fontsize=8, framealpha=0.85)


# =============================================================== 1. DEM
with rasterio.open(DEM) as src:
    madre_utm = madre.to_crs(src.crs)
    xmin, ymin, xmax, ymax = madre_utm.total_bounds
    pad = 2000
    win = from_bounds(xmin - pad, ymin - pad, xmax + pad, ymax + pad, src.transform).round_offsets().round_lengths()
    alto, ancho = int(win.height // FACTOR), int(win.width // FACTOR)
    z = src.read(1, window=win, out_shape=(alto, ancho), masked=True).astype("float32").filled(np.nan)
    tr = src.window_transform(win) * rasterio.Affine.scale(win.width / ancho, win.height / alto)
    crs = src.crs

fuera = geometry_mask(madre_utm.geometry, out_shape=z.shape, transform=tr)   # True = fuera de la cuenca
z_cuenca = np.where(fuera, np.nan, z)
res = abs(tr.a)
ext = (tr.c, tr.c + tr.a * z.shape[1], tr.f + tr.e * z.shape[0], tr.f)

ls = LightSource(azdeg=315, altdeg=45)
sombra = ls.hillshade(np.nan_to_num(z, nan=np.nanmean(z)), vert_exag=2, dx=res, dy=res)

fig, ax = plt.subplots(figsize=(6.4, 8.6), constrained_layout=True)
ax.imshow(np.where(fuera, sombra, np.nan), cmap="gray", extent=ext, alpha=0.35, vmin=0, vmax=1)   # entorno, tenue
ax.imshow(sombra * ~fuera + np.where(fuera, np.nan, 0), cmap="gray", extent=ext, vmin=0, vmax=1)
im = ax.imshow(z_cuenca, cmap="terrain", extent=ext, alpha=0.65,
               vmin=np.nanpercentile(z_cuenca, 0.5) - 400, vmax=np.nanmax(z_cuenca))
madre_utm.boundary.plot(ax=ax, color="k", lw=1.8)
ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
dibujar_estaciones(ax, crs)
cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.02); cb.set_label("elevación (m s.n.m.)")
ax.set_xlabel(f"este (m, {crs.to_string()})"); ax.set_ylabel("norte (m)")
ax.ticklabel_format(style="plain"); ax.tick_params(labelsize=7)
ax.set_title("Cuenca del río Fonce hasta San Gil\nmodelo digital de elevación ALOS PALSAR",
             fontsize=11, weight="semibold")
fig.savefig(OUT / "dem_fonce.png", dpi=160)
plt.close(fig)
print(f"DEM: {z.shape[1]}x{z.shape[0]} celdas de {res:.1f} m; elevación en la cuenca "
      f"{np.nanmin(z_cuenca):.0f}–{np.nanmax(z_cuenca):.0f} m, media {np.nanmean(z_cuenca):.0f} m")

# =============================================================== 2. píxeles IMERG
npz = np.load("data/imerg/imerg_mensual_col.npz", allow_pickle=True)
lon, lat, P = npz["lon"], npz["lat"], npz["precip_mm_mes"]          # P: (mes, lat, lon) o (mes, lon, lat)
if P.shape[1:] == (len(lon), len(lat)):
    P = P.transpose(0, 2, 1)
p_anual = np.nanmean(P, axis=0) * 12                                   # mm/año, 1998–2022

d = 0.1
madre84 = madre.geometry.iloc[0]
area_eq = "EPSG:3116"                                                   # MAGNA-SIRGAS Bogotá, para áreas
celdas = []
x0, y0, x1, y1 = madre84.bounds
for j, x in enumerate(lon):
    if x + d / 2 < x0 or x - d / 2 > x1: continue
    for i, y in enumerate(lat):
        if y + d / 2 < y0 or y - d / 2 > y1: continue
        c = box(x - d / 2, y - d / 2, x + d / 2, y + d / 2)
        if c.intersects(madre84):
            celdas.append({"lon": x, "lat": y, "p_anual": p_anual[i, j], "geometry": c})
celdas = gpd.GeoDataFrame(celdas, crs=4326)
a_celda = celdas.to_crs(area_eq).area
a_dentro = celdas.intersection(madre84).set_crs(4326).to_crs(area_eq).area
celdas["frac_dentro"] = a_dentro / a_celda

fig, ax = plt.subplots(figsize=(6.8, 8.6), constrained_layout=True)
celdas.plot(ax=ax, column="p_anual", cmap="YlGnBu", edgecolor="0.3", lw=0.6, legend=True,
            legend_kwds={"label": "precipitación media anual IMERG 1998–2022 (mm/año)", "shrink": 0.6, "pad": 0.02})
madre.boundary.plot(ax=ax, color="k", lw=2)
for _, r in celdas.iterrows():
    ax.text(r.lon, r.lat, f"{r.frac_dentro * 100:.0f}%", ha="center", va="center", fontsize=6.5, color="0.15",
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])
dibujar_estaciones(ax, rotulos=False)   # los nombres van en el mapa del DEM
ax.set_aspect("equal"); ax.set_xlabel("longitud (°)"); ax.set_ylabel("latitud (°)")
ax.set_title(f"Píxeles de IMERG (0.1°) sobre la cuenca: {len(celdas)} píxeles\n"
             "número = % del píxel dentro de la cuenca", fontsize=11, weight="semibold")
fig.savefig(OUT / "imerg_pixeles.png", dpi=160)
plt.close(fig)
celdas.drop(columns="geometry").round(3).to_csv("out/imerg_pixeles_fonce.csv", index=False)
print(f"IMERG: {len(celdas)} píxeles tocan la cuenca; {(celdas.frac_dentro > 0.5).sum()} tienen más de la mitad dentro; "
      f"P media anual por píxel {celdas.p_anual.min():.0f}–{celdas.p_anual.max():.0f} mm/año")


# =============================================================== 3. píxeles de ERA5-Land
# La malla de ERA5-Land tiene el mismo paso que la de IMERG (0.1°) pero está corrida medio píxel: sus
# centros caen en múltiplos exactos de 0.1° y los de IMERG en los múltiplos terminados en 0.05°. Por eso
# no son las mismas celdas ni son el mismo número.
RUTA_ERA5 = Path("out/era5land_pixeles_fonce.csv")
if not RUTA_ERA5.exists():
    print(f"ERA5-Land: falta {RUTA_ERA5}; corre antes scripts/06_era5land_temperatura.py")
else:
    t = pd.read_csv(RUTA_ERA5)
    d = 0.1
    celdas_t = gpd.GeoDataFrame(
        t, geometry=[box(r.lon - d / 2, r.lat - d / 2, r.lon + d / 2, r.lat + d / 2) for r in t.itertuples()],
        crs=4326)

    fig, ax = plt.subplots(figsize=(6.8, 8.6), constrained_layout=True)
    celdas_t.plot(ax=ax, column="t_media", cmap="RdYlBu_r", edgecolor="0.3", lw=0.6, legend=True,
                  legend_kwds={"label": "temperatura media del aire a 2 m, 1998–2022 (°C)",
                               "shrink": 0.6, "pad": 0.02})
    madre.boundary.plot(ax=ax, color="k", lw=2)
    for _, r in celdas_t.iterrows():
        ax.text(r.lon, r.lat, f"{r.t_media:.1f}", ha="center", va="center", fontsize=6.5, color="0.12",
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    dibujar_estaciones(ax, rotulos=False)   # los nombres van en el mapa del DEM
    ax.set_aspect("equal"); ax.set_xlabel("longitud (°)"); ax.set_ylabel("latitud (°)")
    ax.xaxis.set_major_locator(MultipleLocator(0.1))     # si no, los rótulos se encaballan
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.set_title(f"Píxeles de ERA5-Land (0.1°) sobre la cuenca: {len(celdas_t)} píxeles\n"
                 "número = temperatura media del píxel (°C)", fontsize=11, weight="semibold")
    fig.savefig(OUT / "era5land_pixeles.png", dpi=160)
    plt.close(fig)

    dentro_t = celdas_t[celdas_t.frac_dentro > 0]
    media_ponderada = (dentro_t.t_media * dentro_t.frac_dentro).sum() / dentro_t.frac_dentro.sum()
    print(f"ERA5-Land: {len(celdas_t)} píxeles tocan la cuenca; "
          f"{(celdas_t.frac_dentro > 0.5).sum()} tienen más de la mitad dentro; "
          f"T media por píxel {celdas_t.t_media.min():.1f}–{celdas_t.t_media.max():.1f} °C; "
          f"promedio ponderado por área {media_ponderada:.2f} °C")
