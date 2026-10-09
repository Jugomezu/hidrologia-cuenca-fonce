"""Mapas globales de los campos climáticos del Punto 5 (figuras fijas del informe).

Lee los campos en la malla de 2° que produce scripts/19_campos_climaticos.py y dibuja:
  - campos_sst_media.png           SST media 1998-2022 (ERSST v5).
  - campos_humedad_transporte.png  humedad específica media a 850 hPa y el transporte medio de humedad q·V (ERA5).
  - campos_transporte_mensual.png  humedad específica y transporte de humedad a 850 hPa de cada mes del calendario
                                   (media de los 25 años), en el norte de Sudamérica, el Caribe y el Pacífico oriental.

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
PASO_FLECHAS_REGION = 2       # en el mapa regional, una flecha cada 2 cajas (4°)
REGION = (240, 330, -30, 30)  # longitud de 120° O a 30° O y latitud de 30° S a 30° N (0-360 °E)
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


def marco(ax, lat, lon, tierra, titulo, extension=(0, 360, -80, 80), pasos=(60, 30), tam_titulo=10.5):
    """Costa, cuenca, ejes y título comunes a todos los mapas. `extension` = (lon0, lon1, lat0, lat1) en 0-360 °E."""
    ax.contour(lon, lat, tierra.astype(float), levels=[0.5], colors=COSTA, linewidths=0.6)
    x, y, (cx, cy) = cuenca_san_gil()
    ax.fill(x, y, color=CUENCA, lw=0)
    ax.plot(cx, cy, "o", ms=9, mfc="none", mec=CUENCA, mew=1.6)
    lon0, lon1, lat0, lat1 = extension
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(lat0, lat1)
    ax.set_aspect("equal")
    xs = range(int(np.ceil(lon0 / pasos[0]) * pasos[0]), int(lon1) + 1, pasos[0])
    ys = [v for v in range(-90, 91, pasos[1]) if lat0 < v < lat1 or (lat0 == -80 and abs(v) <= 60)]
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{v}°E" if v <= 180 else f"{360 - v}°O" for v in xs], fontsize=8)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{abs(v)}°{'N' if v > 0 else 'S' if v < 0 else ''}" for v in ys], fontsize=8)
    ax.set_title(titulo, fontsize=tam_titulo, loc="left")


def dibujar_campo(ax, lat, lon, valores, tierra, titulo, cmap, vmin, vmax, unidad):
    """Campo con escala secuencial; lo que no tiene valor va en gris."""
    ax.set_facecolor(GRIS_SIN_DATO)
    m = ax.pcolormesh(bordes(lon), bordes(lat), np.ma.masked_invalid(valores), cmap=cmap, vmin=vmin, vmax=vmax,
                      shading="flat")
    marco(ax, lat, lon, tierra, titulo)
    barra = plt.colorbar(m, ax=ax, orientation="horizontal", fraction=0.05, pad=0.08, aspect=40)
    barra.set_label(unidad, fontsize=9)
    return m


def dibujar_correlacion(ax, lat, lon, r, n, n_minimo, tierra, titulo, **marco_opciones):
    """Mapa de correlación con la escala divergente común de -1 a 1 centrada en cero. Las cajas con menos de
    `n_minimo` pares válidos (o sin valor) quedan en gris. Devuelve el objeto de la escala para una barra común."""
    ax.set_facecolor(GRIS_SIN_DATO)
    r = np.where((n >= n_minimo) & np.isfinite(r), r, np.nan)
    m = ax.pcolormesh(bordes(lon), bordes(lat), np.ma.masked_invalid(r), cmap="RdBu_r",
                      norm=TwoSlopeNorm(vcenter=0.0, vmin=-1.0, vmax=1.0), shading="flat")
    marco(ax, lat, lon, tierra, titulo, **marco_opciones)
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

    # 3) transporte de humedad por mes del calendario, en la región de la cuenca. Cada panel es la media de los 25
    #    años de ese mes; una caja queda en gris si 850 hPa estuvo bajo tierra en alguno de esos 25 meses.
    q_mes = ds.q850.groupby("tiempo.month").mean("tiempo", skipna=False)
    qu_mes = ds.qu850.groupby("tiempo.month").mean("tiempo", skipna=False)
    qv_mes = ds.qv850.groupby("tiempo.month").mean("tiempo", skipna=False)
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
             "noviembre", "diciembre"]
    cmap_q = ListedColormap(plt.get_cmap("YlGnBu")(np.linspace(0.08, 1, 256)))
    fig, ejes = plt.subplots(4, 3, figsize=(13, 13.5), constrained_layout=True)
    LON, LAT = np.meshgrid(lon, lat)
    sel = (slice(None, None, PASO_FLECHAS_REGION), slice(None, None, PASO_FLECHAS_REGION))
    for k, ax in enumerate(ejes.flat):
        ax.set_facecolor(GRIS_SIN_DATO)
        m = ax.pcolormesh(bordes(lon), bordes(lat), np.ma.masked_invalid(q_mes.isel(month=k).values), cmap=cmap_q,
                          vmin=0, vmax=18, shading="flat")
        marco(ax, lat, lon, tierra, meses[k], extension=REGION, pasos=(30, 15), tam_titulo=11)
        flechas = ax.quiver(LON[sel], LAT[sel], qu_mes.isel(month=k).values[sel], qv_mes.isel(month=k).values[sel],
                            color="#222222", scale=1800, width=0.004, headwidth=3.5)
    ax.quiverkey(flechas, 0.62, 0.06, 100, "100 (g/kg)·(m/s)", labelpos="E", coordinates="axes",
                 fontproperties={"size": 8})
    barra = fig.colorbar(m, ax=ejes, orientation="horizontal", fraction=0.025, pad=0.01, aspect=50)
    barra.set_label("humedad específica a 850 hPa (g/kg); flechas: transporte de humedad q·V a 850 hPa", fontsize=10)
    fig.suptitle(f"Humedad y transporte de humedad a 850 hPa, cada mes del calendario (media {anios}, ERA5). "
                 "Gris: 850 hPa bajo el terreno", fontsize=12, x=0.01, ha="left")
    fig.savefig(FIGURAS / "campos_transporte_mensual.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("figuras en", FIGURAS.relative_to(RAIZ))


if __name__ == "__main__":
    main()
