"""CAMINO ABANDONADO - NO EJECUTAR. Se conserva como registro del intento.

    La temperatura de ERA5-Land del proyecto se baja con scripts/06_era5land_temperatura.py, por Google
    Earth Engine. Este script pedia el mismo dato al Climate Data Store y quedo inservible por
    congestion del servidor: el 2026-09-24 la cola de peticiones "grandes" de ERA5 daily statistics
    tenia 2 907 peticiones esperando contra 40 cupos, y una sola de las 75 que necesitabamos llevaba
    53 minutos sin arrancar. La peticion encolada se borro del servidor ese mismo dia.
    Si se ejecuta, se queda esperando indefinidamente.

Descarga la temperatura del aire a 2 m de ERA5-Land para la cuenca del Fonce (San Gil, 24027010),
1998-2022, y la promedia sobre la cuenca ponderando cada celda por su área dentro del polígono.

¿Por qué ERA5-Land y no ERA5?
  Por resolución espacial: ERA5-Land trabaja en una malla de 0.1° (unos 9 km, ~90 km² por celda) y
  ERA5 en una de 0.25° (unos 31 km, ~880 km²). La cuenca de San Gil mide 2 124 km², así que con
  ERA5 la cubrirían dos o tres celdas y con ERA5-Land unas veinte. En una cuenca de montaña que va
  de 1 114 a 4 295 m eso importa: la temperatura cambia con la altura, y una malla gruesa promedia
  el valle con el páramo antes de que uno pueda separarlos.

Producto: "ERA5-Land post-processed daily statistics from 1950 to present"
  (derived-era5-land-daily-statistics), que entrega directamente el valor diario, sin tener que
  bajar las 24 horas de cada día. Se piden tres estadísticos por día:
      daily_mean     -> temperatura media diaria
      daily_minimum  -> temperatura mínima diaria
      daily_maximum  -> temperatura máxima diaria
  El día se define en hora local de Colombia (UTC-05:00), no en UTC, para que coincida con el día
  de las demás series del proyecto.

REQUISITOS (una sola vez)
  1. Cuenta gratuita en el Climate Data Store: https://cds.climate.copernicus.eu
  2. Aceptar los términos del dataset en su página (el CDS no deja descargar sin eso).
  3. Clave de API en C:/Users/<usuario>/.cdsapirc, con este contenido:
         url: https://cds.climate.copernicus.eu/api
         key: <la clave que aparece en el perfil del CDS>
  4. Paquetes: cdsapi, xarray, netCDF4 y truststore (este ultimo porque en este equipo la
     verificacion TLS falla si Python no usa el almacen de certificados de Windows).

Unidades: el archivo trae kelvin; aquí se convierte a grados Celsius.

Salidas:
  data/era5land/t2m_<estadistico>_<año inicial>_<año final>.nc   (crudo, tal como lo entrega el CDS)
  out/era5land_temperatura_diaria_fonce.csv     (fecha, t_media, t_min, t_max, en °C)
"""
import sys, time
import truststore                     # usa el almacen de certificados de Windows:
truststore.inject_into_ssl()          # sin esto el CDS falla por verificacion de certificado
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, shapely
import xarray as xr

ANIOS = range(1998, 2023)          # período de estudio del taller (el mismo de IMERG)
ESTADISTICOS = {"daily_mean": "t_media", "daily_minimum": "t_min", "daily_maximum": "t_max"}
ID_PRINCIPAL = 24027010
SHP = "out/shp_fonce/cuencas_fonce.shp"
CRUDO = Path("data/era5land"); CRUDO.mkdir(parents=True, exist_ok=True)
SALIDA = Path("out/era5land_temperatura_diaria_fonce.csv")

# recorte: la cuenca con un margen de 0.2° (área en el orden norte, oeste, sur, este)
cuenca = gpd.read_file(SHP).to_crs(4326)
poly = cuenca.loc[cuenca.gauge_id == ID_PRINCIPAL, "geometry"].iloc[0]
oeste, sur, este, norte = poly.bounds
AREA = [round(norte + 0.2, 1), round(oeste - 0.2, 1), round(sur - 0.2, 1), round(este + 0.2, 1)]
MESES = [f"{m:02d}" for m in range(1, 13)]
DIAS = [f"{d:02d}" for d in range(1, 32)]


# un año por petición: con tramos más largos el CDS responde "cost limits exceeded"
# (probado con 7 años; 1 año sí lo acepta)
TRAMO = 1
TRAMOS = [list(ANIOS)[i:i + TRAMO] for i in range(0, len(list(ANIOS)), TRAMO)]


def barra(hechas, total, inicio, etiqueta):
    """Barra de avance de una línea: [####----] 12/126  10% · 1981 daily_mean · faltan ~5.1 h"""
    ancho = 28
    llenas = round(ancho * hechas / total)
    transcurrido = time.time() - inicio
    if hechas:
        faltan_s = transcurrido / hechas * (total - hechas)
        falta = f"faltan ~{faltan_s / 3600:.1f} h" if faltan_s > 3600 else f"faltan ~{faltan_s / 60:.0f} min"
    else:
        falta = "calculando..."
    print(f"[{'#' * llenas}{'-' * (ancho - llenas)}] {hechas:3}/{total}  {hechas / total * 100:3.0f}% "
          f"· {etiqueta} · {falta}", flush=True)


def descargar():
    import cdsapi
    import logging
    logging.getLogger("cads_api_client").setLevel(logging.WARNING)   # menos ruido del CDS
    logging.getLogger("datapi").setLevel(logging.WARNING)
    cliente = cdsapi.Client(progress=False, quiet=True)
    fallidos = []
    total = len(TRAMOS) * len(ESTADISTICOS)
    hechas = sum(1 for e in ESTADISTICOS for anios in TRAMOS
                 if (CRUDO / f"t2m_{e}_{anios[0]}_{anios[-1]}.nc").exists())
    inicio = time.time()
    print(f"ERA5-Land: {total} peticiones ({len(TRAMOS)} años x {len(ESTADISTICOS)} estadísticos), "
          f"{hechas} ya descargadas", flush=True)
    barra(hechas, total, inicio, "arrancando")
    # se baja primero la serie completa de medias y despues minima y maxima, para poder
    # empezar a trabajar con la media sin esperar a que termine todo
    for estadistico in ESTADISTICOS:
        for anios in TRAMOS:
            destino = CRUDO / f"t2m_{estadistico}_{anios[0]}_{anios[-1]}.nc"
            if destino.exists() and destino.stat().st_size > 5000:
                continue                                  # reanudable: no repite lo ya bajado
            peticion = {
                "variable": ["2m_temperature"],
                "year": [str(a) for a in anios],
                "month": MESES,
                "day": DIAS,
                "daily_statistic": estadistico,
                "time_zone": "utc-05:00",                 # día local de Colombia
                "frequency": "1_hourly",
                "area": AREA,
                "data_format": "netcdf",
            }
            # hasta 3 intentos: una peticion que falle no debe tumbar la corrida entera
            for intento in range(1, 4):
                try:
                    cliente.retrieve("derived-era5-land-daily-statistics", peticion, str(destino))
                    break
                except Exception as error:
                    print(f"    {anios[0]} {estadistico} falló (intento {intento}): "
                          f"{type(error).__name__}: {error}", flush=True)
                    if destino.exists():
                        destino.unlink()                  # no dejar archivos a medias
                    if intento == 3:
                        fallidos.append((anios[0], estadistico))
            hechas += 1
            barra(hechas, total, inicio, f"{anios[0]} {estadistico}")
    print("descarga terminada; peticiones que fallaron:", fallidos if fallidos else "ninguna", flush=True)


def promedio_sobre_la_cuenca():
    """Serie diaria de cada estadístico, promediando las celdas por su área dentro de la cuenca."""
    series = {}
    for estadistico, nombre in ESTADISTICOS.items():
        archivos = sorted(CRUDO.glob(f"t2m_{estadistico}_*.nc"))
        if not archivos:
            print(f"{nombre}: todavía no hay archivos, se omite esta columna", flush=True)
            continue                                      # se procesa con lo que haya descargado
        d = xr.open_mfdataset(archivos, combine="by_coords")
        variable = [v for v in d.data_vars if v.lower() in ("t2m", "2m_temperature")][0]
        t = d[variable] - 273.15                          # kelvin -> grados Celsius

        lon = t["longitude"].values
        lat = t["latitude"].values
        paso = abs(float(lon[1] - lon[0]))
        I, J = np.meshgrid(np.arange(len(lon)), np.arange(len(lat)), indexing="ij")
        celdas = shapely.box(lon[I] - paso / 2, lat[J] - paso / 2, lon[I] + paso / 2, lat[J] + paso / 2)
        shapely.prepare(poly)
        w = shapely.area(shapely.intersection(poly, celdas))
        w = w / w.sum()                                   # peso = fracción del área de la cuenca

        valores = t.transpose("valid_time", "longitude", "latitude").values
        serie = np.nansum(valores * w[None], axis=(1, 2))
        fechas = pd.to_datetime(t["valid_time"].values).normalize()
        series[nombre] = pd.Series(serie, index=fechas).sort_index()
        print(f"{nombre}: {len(serie)} días | {int((w > 0).sum())} celdas de ERA5-Land tocan la cuenca "
              f"| media {np.nanmean(serie):.1f} °C")

    if not series:
        raise SystemExit(f"no hay ningún archivo descargado en {CRUDO}")
    out = pd.DataFrame(series).round(2)
    out.index.name = "fecha"
    out.to_csv(SALIDA)
    print(f"\n{SALIDA}: {len(out)} días, {out.index.min():%Y-%m-%d} a {out.index.max():%Y-%m-%d}")


if __name__ == "__main__":
    print(f"recorte solicitado (norte, oeste, sur, este): {AREA}")
    if "--solo-procesar" not in sys.argv:
        descargar()
    promedio_sobre_la_cuenca()
