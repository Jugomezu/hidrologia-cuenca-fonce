"""Deriva el cauce principal del Fonce desde el DEM y lo compara con el que publica CAMELS-COL.

CAMELS-COL trae su propia red de drenaje, pero no dice cómo la obtuvo ni con qué DEM. Aquí se rehace el
trabajo desde cero sobre el DEM ALOS PALSAR con el procedimiento estándar —llenar depresiones, resolver
los planos, calcular direcciones de flujo D8 y acumular— y se mide el cauce resultante para ver si las
dos versiones coinciden. Sirve para dos cosas: validar la longitud de 99,12 km que publica CAMELS-COL, y
tener una pendiente de cauce medida sobre un trazado propio, no heredado.

El DEM se remuestrea a 50 m. A 12,5 m la cuenca tendría unos 13,5 millones de celdas y el cálculo de
direcciones de flujo se vuelve pesado sin aportar nada al resultado a esta escala: lo que se busca es la
geometría del cauce principal, no el detalle de cada quebrada.

Salidas:
  out/perfil_cauce_dem.csv        perfil del cauce derivado del DEM
  out/comparacion_cauces.csv      las dos versiones del cauce, una al lado de la otra
  out/shp_fonce/cauce_dem.shp     el trazado derivado
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pysheds.grid import Grid
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry import LineString

RAIZ = Path(__file__).resolve().parent.parent
DEM = RAIZ / "data/dem/dem_fonce_alos_12m.tif"   # recorte del mosaico nacional (scripts/03_recorte_dem.py)
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
UTM = "EPSG:32619"
# Las longitudes y áreas se miden en MAGNA-SIRGAS / Colombia Bogotá (EPSG:3116), la proyección oficial
# para esta zona. El DEM viene en UTM 19N, pero la cuenca (73° O) cae en la zona 18: medida en UTM 19N
# el área sale 0,42 % más grande y las longitudes 0,21 % más largas. El DEM se sigue leyendo en su grilla
# nativa (las alturas no cambian); solo las medidas de distancia y superficie se hacen en EPSG:3116.
MEDICION = "EPSG:3116"
FACTOR = 4                  # 12,5 m -> 50 m
PASO_PERFIL = 250           # m entre puntos del perfil

# Direcciones D8 en el orden que espera pysheds: N, NE, E, SE, S, SO, O, NO
DIRECCIONES_D8 = (64, 128, 1, 2, 4, 8, 16, 32)


# ------------------------------------------------------------------ recorte del DEM a la cuenca
cuencas = gpd.read_file(OUT / "shp_fonce/cuencas_fonce.shp")
cuencas["gauge_id"] = cuencas.gauge_id.astype(int)
cuenca = cuencas[cuencas.gauge_id == ID_PRINCIPAL].to_crs(UTM)

with rasterio.open(DEM) as src:
    xmin, ymin, xmax, ymax = cuenca.total_bounds
    margen = 1000                                   # un poco de aire para no cortar el borde
    ventana = from_bounds(xmin - margen, ymin - margen, xmax + margen, ymax + margen,
                          src.transform).round_offsets().round_lengths()
    alto, ancho = int(ventana.height // FACTOR), int(ventana.width // FACTOR)
    z = src.read(1, window=ventana, out_shape=(1, alto, ancho)).astype("float64")
    transform = src.window_transform(ventana) * rasterio.Affine.scale(
        ventana.width / ancho, ventana.height / alto)
    crs = src.crs
    perfil_ras = src.profile

# El DEM se deja entero, sin recortar a la divisoria. Enmascarar el exterior con un valor bajo haría
# que el agua se fugara por los bordes del recorte y la máxima acumulación acabaría fuera de la cuenca;
# con el terreno completo el flujo es el que manda el relieve. La divisoria se usa después, solo para
# buscar la salida dentro de ella.
fuera = geometry_mask(cuenca.geometry, out_shape=z.shape, transform=transform)

paso_m = abs(transform.a)
ruta_tmp = OUT / "_dem_cuenca_50m.tif"
perfil_ras.update(driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                  dtype="float64", transform=transform, crs=crs, nodata=-32768.0)
with rasterio.open(ruta_tmp, "w", **perfil_ras) as dst:
    dst.write(z, 1)


# ------------------------------------------------------------------ hidrología del terreno
grid = Grid.from_raster(str(ruta_tmp))
elevacion = grid.read_raster(str(ruta_tmp))

# El procedimiento estándar, en este orden: primero se rellenan los hoyos, después se resuelven los
# tramos planos que quedan, y solo entonces se pueden calcular direcciones de flujo coherentes.
sin_hoyos = grid.fill_pits(elevacion)
sin_depresiones = grid.fill_depressions(sin_hoyos)
resuelto = grid.resolve_flats(sin_depresiones)

direccion = grid.flowdir(resuelto, dirmap=DIRECCIONES_D8)
acumulacion = grid.accumulation(direccion, dirmap=DIRECCIONES_D8)

# La salida es la celda de mayor acumulación DENTRO de la divisoria: por ahí sale toda el agua.
acum = np.array(acumulacion)
acum_valida = np.where(np.isfinite(acum), acum, -1.0)
acum_en_cuenca = np.where(fuera, -1.0, acum_valida)
fila_salida, col_salida = np.unravel_index(np.argmax(acum_en_cuenca), acum.shape)
x_salida, y_salida = transform * (col_salida + 0.5, fila_salida + 0.5)
# el área de cada celda está en metros de UTM 19N; se pasa a la escala de EPSG:3116 con la razón entre
# las dos áreas del mismo polígono (el factor de escala es prácticamente constante sobre la cuenca)
ESCALA_AREA = cuenca.to_crs(MEDICION).area.iloc[0] / cuenca.area.iloc[0]
area_drenada_km2 = float(acum_en_cuenca[fila_salida, col_salida]) * paso_m ** 2 / 1e6 * ESCALA_AREA

# Desde la salida se sube por el cauce: en cada paso, de entre las celdas que desaguan en la actual se
# toma la que más área acumula. Ese camino es el cauce principal. Se hace así, remontando la red, en vez
# de con `distance_to_outlet` de pysheds, que en esta versión provoca un fallo de memoria.
DESPLAZAMIENTO = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1),
                  4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
# para cada vecino, qué código D8 tendría que llevar para desaguar en la celda del centro
VECINO_QUE_ENTRA = {(-df, -dc): codigo for codigo, (df, dc) in DESPLAZAMIENTO.items()}
fdir = np.array(direccion)
filas, columnas = fdir.shape

camino = [(fila_salida, col_salida)]
visitadas = {(fila_salida, col_salida)}
fila, col = fila_salida, col_salida
while True:
    mejor, mejor_acum = None, -1.0
    for (df, dc), codigo in VECINO_QUE_ENTRA.items():
        f, c = fila + df, col + dc
        if not (0 <= f < filas and 0 <= c < columnas) or (f, c) in visitadas:
            continue
        if int(fdir[f, c]) == codigo and acum_valida[f, c] > mejor_acum:
            mejor, mejor_acum = (f, c), acum_valida[f, c]
    if mejor is None:
        break
    visitadas.add(mejor)
    camino.append(mejor)
    fila, col = mejor

camino = camino[::-1]                       # de la cabecera hacia la salida
puntos = [transform * (c + 0.5, f + 0.5) for f, c in camino]
cauce_dem = LineString(puntos)
longitud_dem_km = gpd.GeoSeries([cauce_dem], crs=UTM).to_crs(MEDICION).length.iloc[0] / 1000
ESCALA_UTM = longitud_dem_km * 1000 / cauce_dem.length

# perfil sobre el cauce derivado
z_limpio = z
alturas_camino = np.array([z_limpio[f, c] for f, c in camino])
distancias = np.concatenate([[0], np.cumsum(
    [np.hypot(*(np.array(puntos[i + 1]) - np.array(puntos[i]))) for i in range(len(puntos) - 1)])])

perfil_dem = pd.DataFrame({"distancia_km": distancias * ESCALA_UTM / 1000, "altura_m": alturas_camino})
perfil_dem = perfil_dem[np.isfinite(perfil_dem.altura_m)].reset_index(drop=True)
perfil_dem["altura_suavizada_m"] = perfil_dem.altura_m[::-1].cummax()[::-1]

desnivel_dem = perfil_dem.altura_suavizada_m.iloc[0] - perfil_dem.altura_suavizada_m.iloc[-1]
pendiente_media_dem = desnivel_dem / (longitud_dem_km * 1000)

dl = np.diff(perfil_dem.distancia_km.values) * 1000
dz = -np.diff(perfil_dem.altura_suavizada_m.values)
validos = (dl > 0) & (dz > 0)
pendiente_taylor_dem = (dl[validos].sum()
                        / np.sum(dl[validos] / np.sqrt(dz[validos] / dl[validos]))) ** 2


# ------------------------------------------------------------------ comparación con CAMELS-COL
morfo = pd.read_csv(OUT / "morfometria_fonce.csv").set_index("magnitud")
fisio = pd.read_csv(RAIZ / "data/camels_col/signatures/10_CAMELS_COL_Physiograpic_characteristics.csv",
                    sep=";")
fisio.columns = [c.strip() for c in fisio.columns]
fisio_sg = fisio.set_index("gauge_id").loc[ID_PRINCIPAL]

comparacion = pd.DataFrame([
    ("longitud del cauce principal (km)", float(morfo.loc["longitud del cauce principal", "valor"]),
     longitud_dem_km, float(fisio_sg["streng_chanel"])),
    ("desnivel del cauce (m)", float(morfo.loc["desnivel del cauce", "valor"]), desnivel_dem, np.nan),
    ("pendiente media (m/m)", float(morfo.loc["pendiente media del cauce", "valor"]),
     pendiente_media_dem, np.nan),
    ("pendiente Taylor-Schwarz (m/m)",
     float(morfo.loc["pendiente del cauce (Taylor-Schwarz)", "valor"]), pendiente_taylor_dem,
     float(fisio_sg["equi_slope"])),
    ("área drenada en la salida (km²)", float(morfo.loc["área", "valor"]), area_drenada_km2,
     float(fisio_sg["area"])),
], columns=["magnitud", "red_de_camels", "derivado_del_dem", "publicado_camels"])
comparacion["dif_pct"] = ((comparacion.derivado_del_dem / comparacion.red_de_camels - 1) * 100).round(1)

perfil_dem.to_csv(OUT / "perfil_cauce_dem.csv", index=False)
comparacion.to_csv(OUT / "comparacion_cauces.csv", index=False)
gpd.GeoDataFrame(geometry=[cauce_dem], crs=UTM).to_file(OUT / "shp_fonce/cauce_dem.shp")
ruta_tmp.unlink(missing_ok=True)

pd.set_option("display.width", 120)
print(f"DEM a {paso_m:.0f} m: {z.shape[1]} x {z.shape[0]} celdas")
print(f"salida en ({x_salida:.0f}, {y_salida:.0f}), drena {area_drenada_km2:.0f} km²")
print(f"cauce derivado: {len(camino)} celdas, {longitud_dem_km:.2f} km\n")
print(comparacion.to_string(index=False, float_format=lambda v: f"{v:,.4g}".replace(",", " ")))
