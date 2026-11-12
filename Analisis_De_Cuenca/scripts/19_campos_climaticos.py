"""Campos climáticos globales mensuales para el Punto 5: temperatura superficial del mar (SST), viento y humedad
específica a 850 hPa, y el transporte de humedad a 850 hPa, en una malla común de 2°, 1998-2022.

QUÉ SE BAJA Y POR QUÉ (decisiones del usuario del 2026-10-08, ver DECISIONES.md)
  - SST: ERSST v5 de NOAA (Huang et al., 2017), la misma base del ONI que usa el proyecto para el ENSO. Malla de 2°.
  - Viento a 850 hPa, componentes zonal (u, hacia el este) y meridional (v, hacia el norte): los chorros de bajo nivel
    que traen la humedad a la región (el del Caribe, el del Chocó y los alisios del Orinoco).
  - Humedad específica a 850 hPa (q): cuánto vapor de agua viaja con ese viento.
  - Transporte de humedad a 850 hPa: q·u y q·v, calculados con las MEDIAS MENSUALES de q y del viento. Limitación
    declarada: la media del mes de q·u no es igual a (media de q)·(media de u); se pierde el transporte de los
    eventos de días (la covarianza dentro del mes). A escala mensual y de gran escala es una aproximación usual.
  - Presión superficial (sp): solo para saber dónde 850 hPa queda bajo el terreno.
  No se usan la presión al nivel del mar ni la altura geopotencial (decisión del usuario).

FUENTES
  - ERSST v5, NOAA PSL: https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc (NetCDF, °C, 2° x 2°,
    de 1854 a la fecha; la tierra viene vacía).
  - ERA5 monthly means (ECMWF), copia del NSF NCAR Geoscience Data Exchange (GDEX), dataset d633001 «ERA5
    Reanalysis Monthly Means»: https://data.gdex.ucar.edu/d633001/ . Es el mismo producto mensual de ECMWF que
    distribuye el Copernicus Climate Data Store; se usó GDEX porque la cola del CDS tenía los pedidos horas sin
    empezar (decisión del usuario del 2026-10-08). Acceso por HTTPS, sin cuenta. Malla de 0.25°. Cada archivo de GDEX
    trae un año de una variable: en niveles de presión, con los 37 niveles (e5.moda.an.pl, ~600 MB); en superficie,
    la presión superficial (e5.moda.an.sfc). Se lee por HTTPS y se guarda solo el nivel de 850 hPa.

TRANSFORMACIONES
  1. Período 1998-2022 (decisión del usuario).
  2. Celdas bajo tierra: a 850 hPa, una celda de 0.25° está bajo el terreno en un mes si su presión superficial media
     es menor que 850 hPa; sus valores de 850 hPa son extrapolados y no se usan.
  3. Remuestreo de ERA5 a la malla de ERSST (2°): promedio por bloques ponderado por el área de cada celda (coseno de
     la latitud), en cajas de 2° centradas en los puntos de ERSST. Las celdas de 0.25° que caen justo en el borde de
     dos cajas cuentan la mitad en cada una. Un promedio por bloques conserva la media y no inventa valores, a
     diferencia de una interpolación, que en una malla más gruesa solo toma muestras.
  4. Máscara a 2° (decisión del usuario): una caja queda vacía en un mes si CUALQUIERA de sus celdas de 0.25° está
     bajo tierra ese mes. Es estricta: sobre la cordillera de los Andes casi no quedan cajas a 850 hPa.
  5. Unidades: SST en °C; u y v en m/s; q en g/kg (ERA5 la da en kg/kg); q·u y q·v en (g/kg)·(m/s).

SALIDAS
  data/noaa/ersst_v5/sst.mnmean.nc              ERSST v5 tal como se descarga (fuera de git: pasa de 100 MB)
  data/era5_campos/<variable>_<año>.nc            ERA5 de GDEX, un año por archivo: 850 hPa (u, v, q) o la presión
                                                  superficial (sp), sin otro cambio que quitar los demás niveles (fuera de git)
  out/campos_climaticos_2deg_1998_2022.nc         los campos en la malla de 2°, con unidades y descripción
  out/ersst_nino34_contra_oni.csv                 control de calidad de ERSST: Niño 3.4 calculado aquí contra el ONI

CONTROL DE CALIDAD DE ERSST
  El ONI de la NOAA (scripts/17) sale de ERSST v5: es la temperatura media de la región Niño 3.4 en trimestres móviles
  (columna TOTAL) y su anomalía (columna ANOM, con climatologías de 30 años que la NOAA actualiza cada 5). Si con
  nuestro archivo se calcula la misma temperatura media, queda comprobado que se bajó y se leyó bien el producto. Se
  compara TOTAL directamente (no depende de la climatología) y, como referencia, ANOM contra una anomalía con la
  climatología 1991-2020, que no es la misma que usa la NOAA en todos los años.

Uso:  python scripts/19_campos_climaticos.py            (descarga lo que falte y procesa)
      python scripts/19_campos_climaticos.py --solo-procesar
      python scripts/19_campos_climaticos.py --solo-ersst      (solo baja ERSST y hace su control de calidad)
"""
import argparse
import hashlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fsspec
import numpy as np
import pandas as pd
import truststore
import xarray as xr

truststore.inject_into_ssl()      # en este equipo algo intercepta TLS; sin esto no se verifican los certificados

RAIZ = Path(__file__).resolve().parents[1]
DIR_ERSST = RAIZ / "data/noaa/ersst_v5"
ERSST = DIR_ERSST / "sst.mnmean.nc"
URL_ERSST = "https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc"
DIR_ERA5 = RAIZ / "data/era5_campos"
SALIDA = RAIZ / "out/campos_climaticos_2deg_1998_2022.nc"
ONI = RAIZ / "data/noaa/oni.ascii.txt"                       # el ONI que ya usa el proyecto (scripts/17)
SALIDA_NINO34 = RAIZ / "out/ersst_nino34_contra_oni.csv"
NINO34 = {"lat": (-5, 5), "lon": (190, 240)}                 # región Niño 3.4: 5° S-5° N, 170° O-120° O

ANIO_INICIO, ANIO_FIN = 1998, 2022        # período de estudio (decisión del usuario)
NIVEL_HPA = 850
PA_POR_HPA = 100.0
G_POR_KG = 1000.0
URL_GDEX = "https://data.gdex.ucar.edu/d633001"
# variable -> (carpeta de GDEX, nombre del archivo con {a} para el año, nombre de la variable dentro del archivo)
ERA5_GDEX = {
    "u": ("e5.moda.an.pl", "e5.moda.an.pl.128_131_u.ll025uv.{a}010100_{a}120100.nc", "U"),
    "v": ("e5.moda.an.pl", "e5.moda.an.pl.128_132_v.ll025uv.{a}010100_{a}120100.nc", "V"),
    "q": ("e5.moda.an.pl", "e5.moda.an.pl.128_133_q.ll025sc.{a}010100_{a}120100.nc", "Q"),
    "sp": ("e5.moda.an.sfc", "e5.moda.an.sfc.128_134_sp.ll025sc.{a}010100_{a}120100.nc", "SP"),
}
DESCARGAS_SIMULTANEAS = 4                 # archivos de GDEX leídos a la vez


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


# ====================================================================== descargas
def bajar_ersst():
    DIR_ERSST.mkdir(parents=True, exist_ok=True)
    if not ERSST.exists():
        print(f"bajando ERSST v5 de {URL_ERSST} ...")
        urllib.request.urlretrieve(URL_ERSST, ERSST)
    print(f"{ERSST.relative_to(RAIZ)}: {ERSST.stat().st_size / 1e6:.1f} MB, SHA-256 {sha256(ERSST)}")


def bajar_un_anio(corto, anio):
    """Lee por HTTPS el archivo anual de GDEX y guarda solo 850 hPa (o la presión superficial). Se escribe primero a
    .part y se renombra al terminar, para que un corte no deje un archivo a medias que se dé por bueno."""
    destino = DIR_ERA5 / f"{corto}_{anio}.nc"
    if destino.exists():
        return
    carpeta, archivo, nombre = ERA5_GDEX[corto]
    url = f"{URL_GDEX}/{carpeta}/{anio}/{archivo.format(a=anio)}"
    with fsspec.open(url, "rb", block_size=8 * 2**20, cache_type="bytes") as f:
        ds = xr.open_dataset(f, engine="h5netcdf")
        da = ds[nombre]
        if "level" in da.dims:
            da = da.sel(level=NIVEL_HPA)
        da = da.load()
    da = da.rename(time="tiempo", latitude="lat", longitude="lon").rename(corto)
    da = da.drop_vars([c for c in da.coords if c not in ("tiempo", "lat", "lon")])
    da.attrs["fuente"] = url
    parcial = destino.with_suffix(".nc.part")
    da.to_netcdf(parcial, encoding={corto: {"zlib": True, "complevel": 4}})
    parcial.replace(destino)
    print(f"listo {destino.name}", flush=True)


def bajar_era5():
    DIR_ERA5.mkdir(parents=True, exist_ok=True)
    tareas = [(c, a) for c in ERA5_GDEX for a in range(ANIO_INICIO, ANIO_FIN + 1)]
    with ThreadPoolExecutor(max_workers=DESCARGAS_SIMULTANEAS) as grupo:
        for futuro in [grupo.submit(bajar_un_anio, *t) for t in tareas]:
            futuro.result()                # si una lectura falla, el error se ve aquí
    for ruta in sorted(DIR_ERA5.glob("*.nc")):
        print(f"{ruta.relative_to(RAIZ)}: {ruta.stat().st_size / 1e6:.1f} MB, SHA-256 {sha256(ruta)}")


# ====================================================================== control de calidad de ERSST
def controlar_ersst():
    """Niño 3.4 calculado con nuestro ERSST contra el ONI publicado por la NOAA (ver docstring)."""
    sst = xr.open_dataset(ERSST)["sst"]
    caja = sst.sel(lat=slice(NINO34["lat"][1], NINO34["lat"][0]), lon=slice(*NINO34["lon"]))
    peso = np.cos(np.deg2rad(caja.lat))
    nino34 = caja.weighted(peso).mean(dim=("lat", "lon")).to_series()
    nino34.index = nino34.index.to_period("M")
    tri = nino34.rolling(3, center=True).mean()                       # trimestre móvil centrado (DJF -> enero)
    ref = nino34.loc["1991-01":"2020-12"]
    anom = (nino34 - ref.groupby(ref.index.month).mean().reindex(nino34.index.month).to_numpy()).rolling(3, center=True).mean()
    oni = pd.read_csv(ONI, sep=r"\s+")
    meses = {s: i + 1 for i, s in enumerate(["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"])}
    oni.index = pd.PeriodIndex([pd.Period(year=y, month=meses[s], freq="M") for s, y in zip(oni.SEAS, oni.YR)])
    tabla = pd.DataFrame({"nino34_ersst_C": tri, "oni_total_C": oni.TOTAL, "anomalia_ersst_9120_C": anom,
                          "oni_anom_C": oni.ANOM}).loc[f"{ANIO_INICIO}-01":f"{ANIO_FIN}-12"]
    tabla.index.name = "mes_central"
    SALIDA_NINO34.parent.mkdir(parents=True, exist_ok=True)
    tabla.round(3).to_csv(SALIDA_NINO34)
    dif = tabla.nino34_ersst_C - tabla.oni_total_C
    dif_a = tabla.anomalia_ersst_9120_C - tabla.oni_anom_C
    print(f"\nControl de ERSST contra el ONI, {ANIO_INICIO}-{ANIO_FIN} ({len(tabla)} trimestres):")
    print(f"  temperatura de Niño 3.4: diferencia media {dif.mean():+.3f} °C, máxima {dif.abs().max():.3f} °C, "
          f"correlación {tabla.nino34_ersst_C.corr(tabla.oni_total_C):.4f}")
    print(f"  anomalía (climatología 1991-2020 contra la de la NOAA): diferencia media {dif_a.mean():+.3f} °C, "
          f"máxima {dif_a.abs().max():.3f} °C, correlación {tabla.anomalia_ersst_9120_C.corr(tabla.oni_anom_C):.4f}")
    print(f"  {SALIDA_NINO34.relative_to(RAIZ)}")
    return tabla


# ====================================================================== procesamiento
def abrir_era5(corto):
    """Une los años de una variable de ERA5 en un solo DataArray (tiempo, latitud, longitud)."""
    da = xr.open_mfdataset(sorted(DIR_ERA5.glob(f"{corto}_*.nc")), combine="by_coords")[corto]
    da["tiempo"] = pd.to_datetime(da.tiempo.values).to_period("M").to_timestamp()
    return da.sortby("tiempo").sel(tiempo=slice(f"{ANIO_INICIO}-01", f"{ANIO_FIN}-12"))


def pesos_bloque(fino, centros, paso, circular=False):
    """Matriz (centros x fino) con la fracción de cada celda fina dentro de la caja de cada centro: 1 si está adentro,
    0.5 si su centro cae justo en el borde (la comparte con la caja vecina), 0 si está afuera."""
    d = fino[None, :] - centros[:, None]
    if circular:
        d = (d + 180) % 360 - 180
    mitad = paso / 2
    w = np.where(np.abs(d) < mitad - 1e-9, 1.0, 0.0)
    w = np.where(np.isclose(np.abs(d), mitad), 0.5, w)
    return w


class Remuestreo:
    """Promedio por bloques ponderado por área, de la malla de 0.25° de ERA5 a las cajas de 2° de ERSST. Si se da una
    máscara, la caja queda vacía cuando cualquiera de sus celdas finas está enmascarada (decisión del usuario)."""

    def __init__(self, lat_fino, lon_fino, lat2, lon2, paso):
        self.Wlat = pesos_bloque(lat_fino, lat2, paso) * np.cos(np.deg2rad(lat_fino))[None, :]
        self.Wlon = pesos_bloque(lon_fino, lon2, paso, circular=True)
        self.Blat, self.Blon = (self.Wlat > 0).astype(float), (self.Wlon > 0).astype(float)
        self.total = self.Wlat.sum(axis=1)[:, None] * self.Wlon.sum(axis=1)[None, :]

    def __call__(self, x, malos):
        """x y malos: arreglos 2-D (lat, lon) de un mes."""
        x0 = np.where(malos, 0.0, x)
        suma = self.Wlat @ x0 @ self.Wlon.T
        hay_malos = (self.Blat @ malos.astype(float) @ self.Blon.T) > 0
        return np.where(hay_malos, np.nan, suma / self.total)


def procesar():
    sst = xr.open_dataset(ERSST)["sst"].rename(time="tiempo")
    sst = sst.sel(tiempo=slice(f"{ANIO_INICIO}-01", f"{ANIO_FIN}-12"))
    lat2, lon2 = sst.lat.values, sst.lon.values
    paso = float(np.round(np.diff(lon2).mean(), 6))
    assert paso == 2.0 and np.allclose(np.diff(lat2) ** 2, 4.0), "ERSST no está en la malla de 2° esperada"
    assert len(sst.tiempo) == 12 * (ANIO_FIN - ANIO_INICIO + 1)

    era = {c: abrir_era5(c) for c in ("u", "v", "q", "sp")}
    tiempos = era["sp"].tiempo.values
    for da in era.values():
        assert (da.tiempo.values == tiempos).all() and len(tiempos) == len(sst.tiempo)
    r = Remuestreo(era["sp"].lat.values, era["sp"].lon.values, lat2, lon2, paso)
    nombres = ("u850", "v850", "q850", "qu850", "qv850", "fraccion_bajo_tierra_850")
    datos = {k: np.empty((len(tiempos), len(lat2), len(lon2)), dtype="float32") for k in nombres}
    sin_mascara = np.zeros((len(era["sp"].lat), len(era["sp"].lon)), dtype=bool)
    for i in range(len(tiempos)):                                         # mes por mes, para no llenar la memoria
        u, v, q, sp = (era[c].isel(tiempo=i).values.astype(float) for c in ("u", "v", "q", "sp"))
        bajo_tierra = (sp / PA_POR_HPA) < NIVEL_HPA                        # 850 hPa bajo el terreno ese mes
        q_g = q * G_POR_KG                                                # kg/kg -> g/kg
        mes = {"u850": u, "v850": v, "q850": q_g, "qu850": q_g * u, "qv850": q_g * v}   # transporte con medias mensuales
        for k, x in mes.items():
            datos[k][i] = r(x, bajo_tierra | np.isnan(x))
        datos["fraccion_bajo_tierra_850"][i] = r(bajo_tierra.astype(float), sin_mascara)
    coords = {"tiempo": tiempos, "lat": lat2, "lon": lon2}
    salida = xr.Dataset({k: (("tiempo", "lat", "lon"), d) for k, d in datos.items()}, coords=coords)
    salida["sst"] = sst.assign_coords(tiempo=tiempos)

    atributos = {
        "sst": ("°C", "Temperatura superficial del mar, ERSST v5 (NOAA). La tierra está vacía."),
        "u850": ("m/s", "Viento zonal a 850 hPa (positivo hacia el este), ERA5 mensual."),
        "v850": ("m/s", "Viento meridional a 850 hPa (positivo hacia el norte), ERA5 mensual."),
        "q850": ("g/kg", "Humedad específica a 850 hPa, ERA5 mensual."),
        "qu850": ("(g/kg)·(m/s)", "Transporte zonal de humedad a 850 hPa, q·u con las medias mensuales."),
        "qv850": ("(g/kg)·(m/s)", "Transporte meridional de humedad a 850 hPa, q·v con las medias mensuales."),
        "fraccion_bajo_tierra_850": ("1", "Fracción del área de la caja donde 850 hPa queda bajo el terreno ese mes."),
    }
    for k, (unidad, descripcion) in atributos.items():
        salida[k].attrs = {"unidades": unidad, "descripcion": descripcion}
    salida.attrs = {
        "titulo": "Campos climáticos mensuales 1998-2022 en la malla de 2° de ERSST v5",
        "fuentes": "ERSST v5 (NOAA PSL); ERA5 monthly means (ECMWF), copia de NSF NCAR GDEX d633001",
        "remuestreo": "ERA5 0.25° -> 2°: promedio por bloques ponderado por cos(latitud), cajas centradas en los puntos de ERSST",
        "mascara_850": "caja vacía si alguna celda de 0.25° tiene presión superficial < 850 hPa ese mes",
        "generado_por": "scripts/19_campos_climaticos.py",
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    codificacion = {k: {"zlib": True, "complevel": 4, "dtype": "float32"} for k in salida.data_vars}
    salida.to_netcdf(SALIDA, encoding=codificacion)

    print(f"\n{SALIDA.relative_to(RAIZ)}: {SALIDA.stat().st_size / 1e6:.1f} MB, {len(salida.tiempo)} meses, "
          f"malla {len(lat2)} x {len(lon2)} (2°)")
    for k in salida.data_vars:
        x = salida[k]
        print(f"  {k:26s} {x.attrs['unidades']:14s} mín {float(x.min()):8.2f}  máx {float(x.max()):8.2f}  "
              f"cajas vacías {float(x.isnull().mean()) * 100:5.1f} %")
    tierra_alta = float((salida.fraccion_bajo_tierra_850 > 0).mean()) * 100
    print(f"  cajas con alguna celda bajo tierra a 850 hPa (en promedio, por mes): {tierra_alta:.1f} %")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solo-procesar", action="store_true", help="no descarga, solo procesa lo que ya está en data/")
    ap.add_argument("--solo-ersst", action="store_true", help="solo baja ERSST y hace su control de calidad")
    args = ap.parse_args()
    if not args.solo_procesar:
        bajar_ersst()
    controlar_ersst()
    if args.solo_ersst:
        raise SystemExit
    if not args.solo_procesar:
        bajar_era5()
    procesar()
