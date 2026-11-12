"""Gradiente térmico de ERA5-Land: ¿cae la temperatura con la altura como debería?

Cada celda de ERA5-Land que toca la cuenca se cruza contra la altitud media del DEM ALOS PALSAR dentro
de ella, igual que se hace con la lluvia de IMERG en `scripts/09_gradiente_altitudinal.py`. La pregunta
es si el reanálisis reproduce el gradiente térmico real de la montaña: en aire húmedo la temperatura
cae del orden de 6,5 °C por cada 1 000 m de ascenso.

Es la única de las dos fuentes de temperatura del proyecto a la que se le puede hacer esta prueba.
MSWX llega dentro de CAMELS-COL **ya promediado sobre el polígono de la cuenca**, sin la malla, así que
no hay forma de medirle el gradiente con lo que tenemos.

Salida:
  out/gradiente_termico_era5land.csv   altitud y temperatura media de cada celda
"""
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

RAIZ = Path(__file__).resolve().parent.parent
DEM = RAIZ / "data/dem/dem_fonce_alos_12m.tif"   # recorte del mosaico nacional (scripts/03_recorte_dem.py)

LADO_CELDA = 0.1        # grados; el paso de la malla de ERA5-Land, el mismo que el de IMERG
MUESTREO = 60           # malla de submuestreo del DEM dentro de cada celda
GRADIENTE_FISICO = -6.5  # °C/km de referencia en aire húmedo

dem = rasterio.open(DEM)
a_dem = Transformer.from_crs("EPSG:4326", dem.crs, always_xy=True)
mitad = LADO_CELDA / 2

filas = []
for _, celda in pd.read_csv(RAIZ / "out/era5land_pixeles_fonce.csv").iterrows():
    esquinas_x, esquinas_y = a_dem.transform(
        [celda.lon - mitad, celda.lon + mitad, celda.lon - mitad, celda.lon + mitad],
        [celda.lat - mitad, celda.lat - mitad, celda.lat + mitad, celda.lat + mitad])
    ventana = from_bounds(min(esquinas_x), min(esquinas_y),
                          max(esquinas_x), max(esquinas_y), dem.transform)
    alturas = np.asarray(dem.read(1, window=ventana, out_shape=(1, MUESTREO, MUESTREO))).ravel()
    alturas = alturas[alturas > -1000]          # el DEM marca el vacío con -32768
    if alturas.size == 0:
        continue
    filas.append({"lon": celda.lon, "lat": celda.lat, "frac_dentro": celda.frac_dentro,
                  "t_media": celda.t_media, "t_min": celda.t_min, "t_max": celda.t_max,
                  "altitud_media_m": float(alturas.mean())})
dem.close()

d = pd.DataFrame(filas)
d.to_csv(RAIZ / "out/gradiente_termico_era5land.csv", index=False)

# Todas las celdas que tocan la cuenca, cada una ponderada por la fracción de su área que cae dentro
# (el mismo criterio que el gradiente de IMERG en 09_gradiente_altitudinal.py).
w = d.frac_dentro.values
pendiente, _ = np.polyfit(d.altitud_media_m, d.t_media, 1, w=np.sqrt(w))
mx, my = np.average(d.altitud_media_m, weights=w), np.average(d.t_media, weights=w)
r = float(np.sum(w * (d.altitud_media_m - mx) * (d.t_media - my))
          / np.sqrt(np.sum(w * (d.altitud_media_m - mx) ** 2) * np.sum(w * (d.t_media - my) ** 2)))
print(f"las {len(d)} celdas que tocan la cuenca, ponderadas: {pendiente * 1000:+.2f} °C por cada 1 000 m  "
      f"| r = {r:.3f}  r² = {r ** 2:.2f}")
print(f"referencia física en aire húmedo: {GRADIENTE_FISICO:+.1f} °C por cada 1 000 m")
print(f"\nGuardado: out/gradiente_termico_era5land.csv ({len(d)} celdas)")
