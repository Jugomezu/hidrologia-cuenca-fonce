"""Mapas globales de los campos climáticos del Punto 5 (figuras fijas del informe).

Lee los campos en la malla de 2° que produce scripts/19_campos_climaticos.py y dibuja:
  - campos_sst_media.png           SST media 1998-2022 (ERSST v5).
  - campos_humedad_transporte.png  humedad específica media a 850 hPa y el transporte medio de humedad q·V (ERA5).
  - campos_meses_validos_850.png   cuántos de los 300 meses tiene cada caja a 850 hPa (las demás quedaron bajo el
                                   terreno con la máscara estricta).

Las funciones `dibujar_campo` y `dibujar_correlacion` son las mismas que usarán los mapas de correlación del Punto 5,
para que todos compartan las mismas convenciones:
  - Malla centrada en el Pacífico (longitudes de 0° a 360° E), donde están las señales de gran escala del ENSO.
  - Línea de costa: el borde de la máscara de tierra de ERSST (las cajas de 2° sin SST en ningún mes). Sale de los
    datos del proyecto, sin otra fuente; es tan gruesa como la malla.
  - La cuenca del Fonce hasta San Gil se marca con su polígono (out/shp_fonce/cuencas_fonce.shp) y un círculo, porque a
    escala global el polígono mide menos de una caja.
  - Lo que no tiene valor (tierra en la SST, cajas bajo el terreno, cajas con pocos pares) va en gris.
  - Las correlaciones usan una escala divergente común de -1 a 1 centrada en cero (RdBu_r): el mismo color significa
    lo mismo en todos los mapas.

Uso:  python scripts/20_mapas_campos.py
"""
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import xarray as xr

matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402  (después de elegir el backend sin ventana)
from matplotlib.colors import ListedColormap, TwoSlopeNorm  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CAMPOS = RAIZ / "out/campos_climaticos_2deg_1998_2022.nc"
CUENCAS = RAIZ / "out/shp_fonce/cuencas_fonce.shp"
GAUGE_SAN_GIL = "24027010"
FIGURAS = RAIZ / "reporte/figuras"

GRIS_SIN_DATO = "#d9d9d9"
COSTA = "#3a3a3a"
CUENCA = "#e6007e"
PASO_FLECHAS = 3              # se dibuja una flecha cada 3 cajas (6°) para que el campo se lea
DPI = 160


# ====================================================================== piezas comunes de los mapas
def cuenca_san_gil():
    """Polígono de la cuenca hasta San Gil en longitudes de 0° a 360° E, y su centroide."""
    c = gpd.read_file(CUENCAS).to_crs(4326)
    g = c.loc[c.gauge_id.astype(str) == GAUGE_SAN_GIL].geometry.iloc[0]
    x, y = g.exterior.xy if g.geom_type == "Polygon" else max(g.geoms, key=lambda p: p.area).exterior.xy
    return np.asarray(x) % 360, np.asarray(y), (g.centroid.x % 360, g.centroid.y)


def mascara_tierra(sst):
    """True en las cajas sin SST en ningún mes: la tierra de ERSST."""
    return sst.isnull().all("tiempo").values


def bordes(centros):
    """Bordes de las cajas a partir de sus centros (para pcolormesh)."""
    c = np.asarray(centros, dtype=float)
    medio = (c[1:] + c[:-1]) / 2
    return np.concatenate([[c[0] - (medio[0] - c[0])], medio, [c[-1] + (c[-1] - medio[-1])]])


def marco(ax, lat, lon, tierra, titulo):
    """Costa, cuenca, ejes y título comunes a todos los mapas."""
    ax.contour(lon, lat, tierra.astype(float), levels=[0.5], colors=COSTA, linewidths=0.6)
    x, y, (cx, cy) = cuenca_san_gil()
    ax.fill(x, y, color=CUENCA, lw=0)
    ax.plot(cx, cy, "o", ms=9, mfc="none", mec=CUENCA, mew=1.6)
    ax.set_xlim(0, 360)
    ax.set_ylim(-80, 80)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, 361, 60))
    ax.set_xticklabels([f"{v}°E" if v <= 180 else f"{360 - v}°O" for v in range(0, 361, 60)], fontsize=8)
    ax.set_yticks(range(-60, 61, 30))
    ax.set_yticklabels([f"{abs(v)}°{'N' if v > 0 else 'S' if v < 0 else ''}" for v in range(-60, 61, 30)], fontsize=8)
    ax.set_title(titulo, fontsize=10.5, loc="left")


def dibujar_campo(ax, lat, lon, valores, tierra, titulo, cmap, vmin, vmax, unidad):
    """Campo con escala secuencial; lo que no tiene valor va en gris."""
    ax.set_facecolor(GRIS_SIN_DATO)
    m = ax.pcolormesh(bordes(lon), bordes(lat), np.ma.masked_invalid(valores), cmap=cmap, vmin=vmin, vmax=vmax,
                      shading="flat")
    marco(ax, lat, lon, tierra, titulo)
    barra = plt.colorbar(m, ax=ax, orientation="horizontal", fraction=0.05, pad=0.08, aspect=40)
    barra.set_label(unidad, fontsize=9)
    return m


def dibujar_correlacion(ax, lat, lon, r, n, n_minimo, tierra, titulo):
    """Mapa de correlación con la escala divergente común de -1 a 1 centrada en cero. Las cajas con menos de
    `n_minimo` pares válidos (o sin valor) quedan en gris. Devuelve el objeto de la escala para una barra común."""
    ax.set_facecolor(GRIS_SIN_DATO)
    r = np.where((n >= n_minimo) & np.isfinite(r), r, np.nan)
    m = ax.pcolormesh(bordes(lon), bordes(lat), np.ma.masked_invalid(r), cmap="RdBu_r",
                      norm=TwoSlopeNorm(vcenter=0.0, vmin=-1.0, vmax=1.0), shading="flat")
    marco(ax, lat, lon, tierra, titulo)
    return m


# ====================================================================== mapas de control del Punto 5.1
def main():
    FIGURAS.mkdir(parents=True, exist_ok=True)
    ds = xr.open_dataset(CAMPOS)
    lat, lon = ds.lat.values, ds.lon.values
    tierra = mascara_tierra(ds.sst)
    anios = f"{ds.tiempo.dt.year.values.min()}–{ds.tiempo.dt.year.values.max()}"

    # 1) SST media
    fig, ax = plt.subplots(figsize=(11, 5.2))
    dibujar_campo(ax, lat, lon, ds.sst.mean("tiempo").values, tierra,
                  f"Temperatura superficial del mar media, {anios} (ERSST v5, malla de 2°)",
                  "RdYlBu_r", -2, 30, "°C")
    fig.savefig(FIGURAS / "campos_sst_media.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    # 2) humedad específica media a 850 hPa y transporte medio de humedad
    q = ds.q850.mean("tiempo", skipna=False).values            # solo cajas con los 300 meses
    qu = ds.qu850.mean("tiempo", skipna=False).values
    qv = ds.qv850.mean("tiempo", skipna=False).values
    fig, ax = plt.subplots(figsize=(11, 5.2))
    dibujar_campo(ax, lat, lon, q, tierra,
                  f"Humedad específica media a 850 hPa y transporte medio de humedad q·V, {anios} (ERA5)",
                  ListedColormap(plt.get_cmap("YlGnBu")(np.linspace(0.08, 1, 256))), 0, 16, "q a 850 hPa (g/kg)")
    sel = (slice(None, None, PASO_FLECHAS), slice(None, None, PASO_FLECHAS))
    LON, LAT = np.meshgrid(lon, lat)
    flechas = ax.quiver(LON[sel], LAT[sel], qu[sel], qv[sel], color="#222222", scale=1500, width=0.0016,
                        headwidth=3.5)
    ax.quiverkey(flechas, 0.04, 0.05, 100, "100 (g/kg)·(m/s)", labelpos="E", coordinates="axes",
                 fontproperties={"size": 8})   # sobre la Antártida, que está en gris
    fig.savefig(FIGURAS / "campos_humedad_transporte.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    # 3) meses válidos a 850 hPa: el tamaño de muestra varía en el espacio
    n = ds.q850.notnull().sum("tiempo").values.astype(float)
    n = np.where(n > 0, n, np.nan)
    fig, ax = plt.subplots(figsize=(11, 5.2))
    dibujar_campo(ax, lat, lon, n, tierra,
                  f"Meses con dato a 850 hPa en cada caja de 2°, de {ds.sizes['tiempo']} (en gris, ninguno)",
                  "viridis", 0, ds.sizes["tiempo"], "meses válidos")
    fig.savefig(FIGURAS / "campos_meses_validos_850.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("figuras en", FIGURAS.relative_to(RAIZ))


if __name__ == "__main__":
    main()
