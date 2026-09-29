"""Dónde están las dos estaciones que se salen de la tendencia, y en qué subcuenca cae cada una.

ENCINO (el extremo húmedo, la que más lluvia mide) y PUEBLO VIEJO (el extremo seco) no están en la
misma parte de la cuenca: caen en las dos subcuencas grandes de cabecera, que son vecinas y casi
gemelas en tamaño y en elevación media. Esta figura lo muestra sobre el relieve.

  reporte/figuras/estaciones_subcuencas.png

  Panel izquierdo  — el DEM ALOS PALSAR con las dos subcuencas resaltadas y las siete estaciones que
                     caen dentro de la divisoria de San Gil.
  Panel derecho    — lluvia contra altitud, con cada estación coloreada según su subcuenca. Sirve para
                     ver que PUEBLO VIEJO es un mínimo dentro de su propia subcuenca y que ENCINO es la
                     única estación de la suya.

El DEM se lee solo en la ventana de la cuenca y remuestreado, como en scripts/08_mapas_y_pixeles.py.
"""
from pathlib import Path

import geopandas as gpd
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

RAIZ = Path(__file__).resolve().parent.parent
DEM = RAIZ / "data/dem/dem_fonce_alos_12m.tif"   # recorte del mosaico nacional (scripts/03_recorte_dem.py)
OUT = RAIZ / "reporte/figuras"
FACTOR = 4                      # 12.5 m -> 50 m, suficiente para una figura

ID_PRINCIPAL = 24027010
# Las dos subcuencas donde caen las estaciones extremas. El color sigue el sentido del dato:
# azul para la del extremo húmedo, naranja para la del extremo seco.
SUBCUENCA_HUMEDA = 24027030     # Nemizaque, río Pienta  -> ENCINO
SUBCUENCA_SECA = 24027050       # Puente Llano, río Taquiza -> PUEBLO VIEJO
COD_HUMEDA, COD_SECA = 24020040, 24020230       # ENCINO, PUEBLO VIEJO

AZUL, NARANJA, GRIS = "#0072B2", "#D55E00", "#6B7280"
OTRAS = "#8C8C8C"

# Dónde va el rótulo de cada subcuenca, en coordenadas del DEM (EPSG:32619). Se fija a mano porque el
# centroide de Puente Llano cae justo encima de Pueblo Viejo y el texto tapaba el punto.
ROTULO_SUBCUENCA = {SUBCUENCA_HUMEDA: (39000, 668000), SUBCUENCA_SECA: (61500, 703800)}

# Hacia dónde sale la etiqueta de cada estación: (dx, dy) en puntos, alineación horizontal y vertical.
# Con siete estaciones y dos muy juntas (Encino y Pavas Las) es más limpio fijarlo que calcularlo.
ETIQUETA_ESTACION = {
    "ENCINO":                   (-12, -14, "right", "top"),
    "PAVAS LAS":                (-12, 11, "right", "bottom"),
    "PUEBLO VIEJO":             (0, 13, "center", "bottom"),
    "COROMORO":                 (-12, 2, "right", "center"),
    "CHARALÁ":                  (-12, 2, "right", "center"),
    "VALLE DE SAN JOSE":        (12, 2, "left", "center"),
    "ESCUELA AGRICOLA MOGOTES": (-12, 2, "right", "center"),
}


# ------------------------------------------------------------------ datos
cuencas = gpd.read_file(RAIZ / "out/shp_fonce/cuencas_fonce.shp")
cuencas["gauge_id"] = cuencas.gauge_id.astype(int)
madre = cuencas[cuencas.gauge_id == ID_PRINCIPAL]

catalogo = pd.read_csv(RAIZ / "out/pluviometros_fonce_catalogo.csv")
mensual = pd.read_csv(RAIZ / "out/pluviometros_fonce_mensual_depurado.csv")
# Media mensual x 12: no se suman años incompletos, que subestimarían el total.
catalogo = catalogo.merge(mensual.groupby("codigo").precipitacion_mm.mean().rename("p_mes"), on="codigo")
catalogo["p_anual"] = catalogo.p_mes * 12
catalogo["etiqueta"] = (catalogo.nombre.str.replace(r"\s*\[\d+\]", "", regex=True)
                        .str.title().str.replace(" De ", " de "))

est = gpd.GeoDataFrame(catalogo[catalogo.dentro_cuenca].copy(),
                       geometry=gpd.points_from_xy(catalogo.loc[catalogo.dentro_cuenca, "longitud"],
                                                   catalogo.loc[catalogo.dentro_cuenca, "latitud"]),
                       crs=4326)

# ¿en qué subcuenca cae cada estación? Como están anidadas, se toma la más pequeña que la contiene.
def subcuenca_de(punto):
    dentro = cuencas[cuencas.contains(punto)].sort_values("area_km2")
    return dentro.iloc[0].gauge_id if len(dentro) else np.nan


est["subcuenca"] = est.geometry.apply(subcuenca_de)
est["nombre_subcuenca"] = est.subcuenca.map(cuencas.set_index("gauge_id").nombre)


def color_de(fila):
    if fila.subcuenca == SUBCUENCA_HUMEDA:
        return AZUL
    if fila.subcuenca == SUBCUENCA_SECA:
        return NARANJA
    return OTRAS


est["color"] = est.apply(color_de, axis=1)
est["extrema"] = est.codigo.isin([COD_HUMEDA, COD_SECA])

# ------------------------------------------------------------------ DEM
with rasterio.open(DEM) as src:
    madre_utm = madre.to_crs(src.crs)
    xmin, ymin, xmax, ymax = madre_utm.total_bounds
    pad = 2000
    ventana = from_bounds(xmin - pad, ymin - pad, xmax + pad, ymax + pad,
                          src.transform).round_offsets().round_lengths()
    alto, ancho = int(ventana.height // FACTOR), int(ventana.width // FACTOR)
    z = src.read(1, window=ventana, out_shape=(alto, ancho), masked=True).astype("float32").filled(np.nan)
    tr = src.window_transform(ventana) * rasterio.Affine.scale(ventana.width / ancho,
                                                               ventana.height / alto)
    crs = src.crs

fuera = geometry_mask(madre_utm.geometry, out_shape=z.shape, transform=tr)   # True = fuera de la cuenca
z_cuenca = np.where(fuera, np.nan, z)
res = abs(tr.a)
ext = (tr.c, tr.c + tr.a * z.shape[1], tr.f + tr.e * z.shape[0], tr.f)
sombra = LightSource(azdeg=315, altdeg=45).hillshade(np.nan_to_num(z, nan=np.nanmean(z)),
                                                     vert_exag=2, dx=res, dy=res)

# ------------------------------------------------------------------ figura
fig = plt.figure(figsize=(14.5, 9.4))
rejilla = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=0.16)
mapa = fig.add_subplot(rejilla[0, 0])
perfil = fig.add_subplot(rejilla[0, 1])

# --- panel izquierdo: el relieve y las subcuencas
mapa.imshow(np.where(fuera, sombra, np.nan), cmap="gray", extent=ext, alpha=0.3, vmin=0, vmax=1)
mapa.imshow(sombra * ~fuera + np.where(fuera, np.nan, 0), cmap="gray", extent=ext, vmin=0, vmax=1)
relieve = mapa.imshow(z_cuenca, cmap="terrain", extent=ext, alpha=0.42,
                      vmin=np.nanpercentile(z_cuenca, 0.5) - 400, vmax=np.nanmax(z_cuenca))

cuencas_utm = cuencas.to_crs(crs)
# las subcuencas que no son protagonistas, apenas insinuadas
otras = cuencas_utm[~cuencas_utm.gauge_id.isin([ID_PRINCIPAL, SUBCUENCA_HUMEDA, SUBCUENCA_SECA])]
otras.boundary.plot(ax=mapa, color="0.35", lw=0.7, linestyle=":", zorder=3)

for gid, color in [(SUBCUENCA_HUMEDA, AZUL), (SUBCUENCA_SECA, NARANJA)]:
    sub = cuencas_utm[cuencas_utm.gauge_id == gid]
    sub.plot(ax=mapa, color=color, alpha=0.26, zorder=3)
    sub.boundary.plot(ax=mapa, color=color, lw=2.6, zorder=4)
    fila = sub.iloc[0]
    mapa.annotate(f"{fila.nombre}\n{fila.area_km2:.0f} km²", ROTULO_SUBCUENCA[gid],
                  ha="center", va="center", fontsize=10, weight="bold", color=color, zorder=6,
                  path_effects=[pe.withStroke(linewidth=3.2, foreground="white")])

madre_utm.boundary.plot(ax=mapa, color="k", lw=1.9, zorder=5)

est_utm = est.to_crs(crs)
normales = est_utm[~est_utm.extrema]
extremas = est_utm[est_utm.extrema]
mapa.scatter(normales.geometry.x, normales.geometry.y, s=90, c=normales.color,
             edgecolor="white", linewidth=1.2, zorder=7)
mapa.scatter(extremas.geometry.x, extremas.geometry.y, s=330, c=extremas.color, marker="*",
             edgecolor="white", linewidth=1.3, zorder=8)

for _, e in est_utm.iterrows():
    nombre_crudo = e.nombre.replace(f" [{e.codigo}]", "").strip()
    dx, dy, ha, va = ETIQUETA_ESTACION[nombre_crudo]
    texto = f"{e.etiqueta}\n{e.altitud:.0f} m · {e.p_anual:,.0f} mm/año".replace(",", " ")
    mapa.annotate(texto, (e.geometry.x, e.geometry.y),
                  xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                  fontsize=8.4 if e.extrema else 7.4,
                  weight="bold" if e.extrema else "normal",
                  color=e.color if e.extrema else "#2B2B2B", zorder=9,
                  path_effects=[pe.withStroke(linewidth=2.6, foreground="white")])

mapa.set_xlim(ext[0], ext[1])
mapa.set_ylim(ext[2], ext[3])
mapa.set_xlabel(f"este (m, {crs.to_string()})", fontsize=9)
mapa.set_ylabel("norte (m)", fontsize=9)
mapa.ticklabel_format(style="plain")
mapa.tick_params(labelsize=7)
barra = fig.colorbar(relieve, ax=mapa, shrink=0.55, pad=0.02)
barra.set_label("elevación (m s. n. m.)", fontsize=9)
barra.ax.tick_params(labelsize=7)

mapa.legend(handles=[
    Line2D([], [], marker="*", color="none", markerfacecolor=AZUL, markeredgecolor="white",
           markersize=17, label="Encino — el extremo húmedo"),
    Line2D([], [], marker="*", color="none", markerfacecolor=NARANJA, markeredgecolor="white",
           markersize=17, label="Pueblo Viejo — el extremo seco"),
    Line2D([], [], marker="o", color="none", markerfacecolor=OTRAS, markeredgecolor="white",
           markersize=9, label="las otras cinco estaciones"),
], loc="lower left", fontsize=8.2, framealpha=0.9)
mapa.set_title("Las dos estaciones extremas caen en subcuencas distintas",
               fontsize=11.5, weight="semibold")

# --- panel derecho: lluvia contra altitud, agrupada por subcuenca
# se fijan los límites antes de anotar, para que las etiquetas no se salgan del panel
perfil.set_xlim(est.altitud.min() - 180, est.altitud.max() + 230)
perfil.set_ylim(est.p_anual.min() - 320, est.p_anual.max() + 520)

for _, e in est.sort_values("altitud").iterrows():
    perfil.scatter(e.altitud, e.p_anual, s=340 if e.extrema else 120, c=e.color,
                   marker="*" if e.extrema else "o", edgecolor="white", linewidth=1.3, zorder=4)
    perfil.annotate(f"{e.etiqueta}\n{e.altitud:.0f} m",
                    (e.altitud, e.p_anual), textcoords="offset points", xytext=(0, 16),
                    ha="center", fontsize=7.6,
                    weight="bold" if e.extrema else "normal",
                    color=e.color if e.extrema else "#2B2B2B",
                    path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])

# las tres estaciones del Taquiza, unidas para que se vea el hundimiento de Pueblo Viejo
taquiza = est[est.subcuenca == SUBCUENCA_SECA].sort_values("altitud")
perfil.plot(taquiza.altitud, taquiza.p_anual, color=NARANJA, lw=1.4, linestyle="--", zorder=3, alpha=0.8)

# lo que IMERG estima para cada una de las dos subcuencas
imerg = pd.read_csv(RAIZ / "out/imerg_mensual_fonce.csv")
imerg["anio"] = imerg.periodo.str[:4].astype(int)
p_sub = imerg.groupby(["id_estacion", "anio"]).p_imerg_mm.sum().groupby("id_estacion").mean()
nombres_sub = cuencas.set_index("gauge_id").nombre
for gid, color, dy in [(SUBCUENCA_HUMEDA, AZUL, -13), (SUBCUENCA_SECA, NARANJA, 5)]:
    perfil.axhline(p_sub[gid], color=color, lw=1.2, linestyle=":", zorder=2)
    perfil.annotate(f"IMERG sobre {nombres_sub[gid].split(' (')[0]}: "
                    f"{p_sub[gid]:,.0f} mm/año".replace(",", " "),
                    (perfil.get_xlim()[1], p_sub[gid]), xytext=(-5, dy),
                    textcoords="offset points", ha="right", fontsize=7.6, color=color, zorder=5,
                    path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])

perfil.set_xlabel("altitud de la estación (m s. n. m.)", fontsize=9)
perfil.set_ylabel("precipitación media anual 1998–2022 (mm/año)", fontsize=9)
perfil.grid(axis="y", color="#E5E7EB", linewidth=0.8)
perfil.set_axisbelow(True)
for lado in ("top", "right"):
    perfil.spines[lado].set_visible(False)
perfil.tick_params(labelsize=8)
perfil.set_title("Encino es la única estación del Pienta;\nPueblo Viejo es un mínimo dentro del Taquiza",
                 fontsize=11.5, weight="semibold")

fig.suptitle("Dónde están las dos estaciones que se salen de la tendencia altitudinal",
             fontsize=14, weight="bold", y=0.985)
fig.savefig(OUT / "estaciones_subcuencas.png", dpi=160, bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ salidas
# El informe HTML lee este CSV en vez de repetir el cruce geométrico.
areas = cuencas.set_index("gauge_id").area_km2
salida = est[["codigo", "etiqueta", "altitud", "p_anual", "subcuenca", "nombre_subcuenca"]].copy()
salida["area_subcuenca_km2"] = salida.subcuenca.map(areas)
salida["p_imerg_subcuenca"] = salida.subcuenca.map(p_sub)
salida["estaciones_en_subcuenca"] = salida.subcuenca.map(est.subcuenca.value_counts())
salida.sort_values("altitud").to_csv(RAIZ / "out/estaciones_subcuencas.csv", index=False)

tabla = est[["etiqueta", "altitud", "p_anual", "nombre_subcuenca"]].sort_values("altitud")
print(tabla.round(0).to_string(index=False))
print()
for gid in (SUBCUENCA_HUMEDA, SUBCUENCA_SECA):
    fila = cuencas[cuencas.gauge_id == gid].iloc[0]
    cuantas = int((est.subcuenca == gid).sum())
    print(f"{fila.nombre}: {fila.area_km2:.0f} km², {cuantas} estación(es), "
          f"IMERG {p_sub[gid]:.0f} mm/año")
print(f"\nFigura: {OUT / 'estaciones_subcuencas.png'}")
