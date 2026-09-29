"""Temperatura del aire a 2 m de ERA5-Land para la cuenca del Fonce (San Gil, 24027010), 1998-2022,
bajada desde Google Earth Engine y promediada sobre la cuenca ponderando por area.

POR QUE EARTH ENGINE Y NO EL CLIMATE DATA STORE
  Es el mismo producto (ERA5-Land diario del ECMWF), pero por dos caminos distintos. El camino del
  CDS (scripts/historico/27_era5land_temperatura.py) quedo inservible por congestion del servidor: el 2026-09-24
  la cola de peticiones "grandes" de ERA5 daily statistics tenia 2 907 peticiones esperando contra
  40 cupos de ejecucion, y una sola de nuestras 75 peticiones llevaba 53 minutos sin arrancar.
  Earth Engine sirve la misma coleccion ya agregada a diario y ademas calcula el promedio sobre el
  poligono en el servidor, asi que devuelve la serie en minutos y sin cola.

POR QUE ERA5-LAND Y NO ERA5
  Por resolucion espacial: ERA5-Land trabaja en una malla de 0.1 grados (unos 9 km, ~90 km2 por
  celda) y ERA5 en una de 0.25 grados (unos 31 km, ~880 km2). La cuenca de San Gil mide 2 124 km2,
  asi que con ERA5 la cubririan dos o tres celdas y con ERA5-Land unas veinte. En una cuenca de
  montana que va de 1 114 a 4 295 m eso importa: la temperatura cambia con la altura, y una malla
  gruesa promedia el valle con el paramo antes de que uno pueda separarlos.

COLECCION
  ECMWF/ERA5_LAND/DAILY_AGGR - "ERA5-Land Daily Aggregated - ECMWF Climate Reanalysis".
  Bandas usadas (en kelvin, aqui se convierten a grados Celsius):
      temperature_2m       -> temperatura media diaria
      temperature_2m_min   -> temperatura minima diaria
      temperature_2m_max   -> temperatura maxima diaria

DIFERENCIA QUE HAY QUE TENER PRESENTE
  Earth Engine agrega el dia en UTC; el producto del CDS permite definirlo en hora local. Para
  Colombia (UTC-05:00) eso corre el corte cinco horas: el dia de Earth Engine va de las 19:00 del
  dia anterior a las 19:00 del dia. En la media diaria el efecto es minimo, y en la agregacion
  mensual que usa el proyecto es despreciable; en la minima y la maxima diarias puede desplazar
  algun extremo de un dia al siguiente. Se documenta y no se corrige.

PROMEDIO SOBRE LA CUENCA
  ee.Reducer.mean() sobre el poligono pondera cada celda por la fraccion de su area que cae dentro
  de la cuenca, que es el mismo criterio que se usa con IMERG en el resto del proyecto.

REQUISITOS (una sola vez)
  1. Cuenta de Earth Engine asociada a un proyecto de Google Cloud:
     https://code.earthengine.google.com/register (gratis para uso academico).
  2. pip install earthengine-api
  3. earthengine authenticate      (abre el navegador; deja el token en ~/.config/earthengine)

USO
  python scripts/06_era5land_temperatura.py                  descarga lo que falte y arma el CSV
  python scripts/06_era5land_temperatura.py --solo-procesar  solo arma el CSV con los anios ya bajados
  python scripts/06_era5land_temperatura.py --proyecto ID    fuerza otro proyecto de Google Cloud

SALIDAS
  data/era5land_gee/t2m_<anio>.csv            crudo por anio, tal como lo devuelve Earth Engine
  out/era5land_temperatura_diaria_fonce.csv   fecha, t_media, t_min, t_max (grados Celsius)
  out/era5land_pixeles_fonce.csv              una fila por celda de la malla que toca la cuenca:
                                              lon, lat, t_media, t_min, t_max y la fraccion de la
                                              celda que cae dentro de la cuenca (para el mapa)
"""
import argparse, json, sys, time
from pathlib import Path

import truststore                     # usa el almacen de certificados de Windows:
truststore.inject_into_ssl()          # sin esto la verificacion TLS falla en este equipo

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
import ee

RAIZ = Path(__file__).resolve().parents[1]
SHP_CUENCAS = RAIZ / "out/shp_fonce/cuencas_fonce.shp"
DIR_CRUDO = RAIZ / "data/era5land_gee"
SALIDA = RAIZ / "out/era5land_temperatura_diaria_fonce.csv"
SALIDA_PIXELES = RAIZ / "out/era5land_pixeles_fonce.csv"

ID_CUENCA = 24027010                  # San Gil, el sujeto de estudio
ANIOS = range(1998, 2023)             # periodo del proyecto: 1998-2022
COLECCION = "ECMWF/ERA5_LAND/DAILY_AGGR"
BANDAS = {"temperature_2m": "t_media", "temperature_2m_min": "t_min", "temperature_2m_max": "t_max"}
ESCALA_M = 11132                      # 0.1 grados en metros: la resolucion nativa de ERA5-Land
CERO_ABSOLUTO = 273.15                # kelvin -> grados Celsius
TOLERANCIA_SIMPLIFICAR = 0.0005       # ~55 m, despreciable frente a celdas de 11 km
MAX_VERTICES = 5000                   # por encima de esto la peticion a Earth Engine pesa de mas

# Proyecto de Google Cloud contra el que corre Earth Engine. Se usa solo si el token guardado no
# trae uno (earthengine authenticate no siempre lo escribe). Se puede cambiar con --proyecto.
PROYECTO_GEE = "90988188721"


def proyecto_por_defecto():
    """Lee el proyecto de Google Cloud que quedo guardado al autenticar."""
    ruta = Path.home() / ".config/earthengine/credentials"
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text()).get("project")
    except (json.JSONDecodeError, OSError):
        return None


def iniciar(proyecto):
    """Arranca la sesion de Earth Engine, con un mensaje util si falta autenticar."""
    try:
        ee.Initialize(project=proyecto)
    except Exception as e:
        print("\nNo se pudo iniciar Earth Engine:", str(e).strip().splitlines()[0])
        print("Corre en la terminal:  earthengine authenticate")
        print("y vuelve a ejecutar este script.")
        sys.exit(1)


def poligono_cuenca():
    """Poligono de San Gil en coordenadas geograficas, simplificado si trae demasiados vertices."""
    cuencas = gpd.read_file(SHP_CUENCAS).to_crs("EPSG:4326")
    fila = cuencas[cuencas.gauge_id == ID_CUENCA]
    if fila.empty:
        sys.exit(f"No esta la cuenca {ID_CUENCA} en {SHP_CUENCAS}")
    poligono = fila.geometry.iloc[0]
    vertices = shapely.get_num_coordinates(poligono)
    if vertices > MAX_VERTICES:
        poligono = poligono.simplify(TOLERANCIA_SIMPLIFICAR, preserve_topology=True)
        print(f"poligono simplificado: {vertices} -> {shapely.get_num_coordinates(poligono)} vertices "
              f"(tolerancia {TOLERANCIA_SIMPLIFICAR} grados, ~55 m)")
    return poligono


def a_geometria(poligono):
    """El poligono de shapely, como geometria de Earth Engine."""
    return ee.Geometry(shapely.geometry.mapping(poligono), proj="EPSG:4326", geodesic=False)


def serie_del_anio(anio, geometria):
    """Promedio diario sobre la cuenca de las tres bandas de temperatura, para un anio."""
    coleccion = (ee.ImageCollection(COLECCION)
                 .filterDate(f"{anio}-01-01", f"{anio + 1}-01-01")
                 .select(list(BANDAS)))

    def promediar(imagen):
        valores = imagen.reduceRegion(reducer=ee.Reducer.mean(), geometry=geometria,
                                      scale=ESCALA_M, maxPixels=int(1e9))
        return ee.Feature(None, valores).set("fecha", imagen.date().format("YYYY-MM-dd"))

    filas = [f["properties"] for f in coleccion.map(promediar).getInfo()["features"]]
    tabla = pd.DataFrame(filas)
    if tabla.empty:
        return tabla
    for banda, nombre in BANDAS.items():
        if banda not in tabla:
            sys.exit(f"Earth Engine no devolvio la banda {banda} para {anio}")
        tabla[nombre] = tabla[banda] - CERO_ABSOLUTO      # kelvin -> grados Celsius
    return tabla[["fecha"] + list(BANDAS.values())].sort_values("fecha")


def malla_de_pixeles(poligono, geometria):
    """Temperatura media 1998-2022 de cada celda de la malla de ERA5-Land que toca la cuenca.

    Sirve para el mapa del informe: muestra como se reparte la temperatura dentro de la cuenca, que es
    justo lo que se pierde al promediarla en una sola serie. Los centros de la malla de ERA5-Land caen
    en multiplos exactos de 0.1 grados, asi que los bordes de cada celda estan en los multiplos +- 0.05.
    """
    medias = (ee.ImageCollection(COLECCION)
              .filterDate(f"{min(ANIOS)}-01-01", f"{max(ANIOS) + 1}-01-01")
              .select(list(BANDAS)).mean())

    # celdas de la malla que tocan el poligono de la cuenca
    x0, y0, x1, y1 = poligono.bounds
    paso = 0.1
    centros = []
    for k in range(int(np.floor(x0 / paso)), int(np.ceil(x1 / paso)) + 1):
        for l in range(int(np.floor(y0 / paso)), int(np.ceil(y1 / paso)) + 1):
            cx, cy = round(k * paso, 4), round(l * paso, 4)
            celda = shapely.geometry.box(cx - paso / 2, cy - paso / 2, cx + paso / 2, cy + paso / 2)
            if celda.intersects(poligono):
                centros.append({"lon": cx, "lat": cy, "geometry": celda})
    celdas = gpd.GeoDataFrame(centros, crs="EPSG:4326")

    # que fraccion del area de cada celda cae dentro de la cuenca (el mismo peso que usa el promedio)
    area_eq = "EPSG:3116"                       # MAGNA-SIRGAS Bogota, para medir areas en metros
    celdas["frac_dentro"] = (celdas.intersection(poligono).set_crs("EPSG:4326").to_crs(area_eq).area
                             / celdas.to_crs(area_eq).area)

    # el valor de cada celda se pide en su centro, con la escala nativa de ERA5-Land
    puntos = ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point([float(r.lon), float(r.lat)]), {"lon": float(r.lon), "lat": float(r.lat)})
        for r in celdas.itertuples()])
    muestreo = medias.reduceRegions(collection=puntos, reducer=ee.Reducer.first(), scale=ESCALA_M)
    valores = pd.DataFrame([f["properties"] for f in muestreo.getInfo()["features"]])
    for banda, nombre in BANDAS.items():
        valores[nombre] = valores[banda] - CERO_ABSOLUTO          # kelvin -> grados Celsius

    tabla = celdas.drop(columns="geometry").merge(valores[["lon", "lat"] + list(BANDAS.values())],
                                                  on=["lon", "lat"], how="left")
    tabla = tabla.round({"frac_dentro": 4, "t_media": 3, "t_min": 3, "t_max": 3})
    tabla.to_csv(SALIDA_PIXELES, index=False)
    dentro = tabla[tabla.frac_dentro > 0.5]
    print(f"{SALIDA_PIXELES.relative_to(RAIZ)}: {len(tabla)} celdas tocan la cuenca, "
          f"{len(dentro)} con mas de la mitad dentro")
    print(f"temperatura media por celda: {tabla.t_media.min():.2f} a {tabla.t_media.max():.2f} C")
    return tabla


def barra(hechos, total, mensaje):
    """Barra de avance de una linea, para no llenar la consola."""
    ancho = 28
    lleno = int(ancho * hechos / total)
    relleno = "#" * lleno + "-" * (ancho - lleno)
    print(f"\r[{relleno}] {hechos:>2}/{total} {100 * hechos // total:>3}% | {mensaje:<34}",
          end="", flush=True)


def descargar(geometria):
    """Baja anio por anio, saltando lo que ya este en disco (el script es reanudable)."""
    DIR_CRUDO.mkdir(parents=True, exist_ok=True)
    pendientes = [a for a in ANIOS if not (DIR_CRUDO / f"t2m_{a}.csv").exists()]
    print(f"ERA5-Land por Earth Engine: {len(ANIOS)} anios, {len(ANIOS) - len(pendientes)} ya bajados")
    hechos = len(ANIOS) - len(pendientes)
    barra(hechos, len(ANIOS), "arrancando")
    for anio in pendientes:
        for intento in (1, 2, 3):
            try:
                tabla = serie_del_anio(anio, geometria)
                tabla.to_csv(DIR_CRUDO / f"t2m_{anio}.csv", index=False)
                hechos += 1
                barra(hechos, len(ANIOS), f"{anio}: {len(tabla)} dias")
                break
            except Exception as e:
                if intento == 3:
                    print(f"\n{anio} fallo tras 3 intentos: {str(e)[:160]}")
                else:
                    barra(hechos, len(ANIOS), f"{anio}: reintento {intento}")
                    time.sleep(5 * intento)
    print()


def armar_csv():
    """Une los anios bajados en una sola serie diaria y la guarda."""
    archivos = sorted(DIR_CRUDO.glob("t2m_*.csv"))
    if not archivos:
        sys.exit("No hay nada descargado todavia en " + str(DIR_CRUDO))
    serie = pd.concat([pd.read_csv(a) for a in archivos], ignore_index=True)
    serie["fecha"] = pd.to_datetime(serie["fecha"])
    serie = serie.drop_duplicates("fecha").sort_values("fecha").reset_index(drop=True)
    serie[list(BANDAS.values())] = serie[list(BANDAS.values())].round(3)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    serie.to_csv(SALIDA, index=False)

    esperados = pd.date_range(f"{min(ANIOS)}-01-01", f"{max(ANIOS)}-12-31", freq="D")
    faltan = len(esperados) - serie.fecha.isin(esperados).sum()
    print(f"\n{SALIDA.relative_to(RAIZ)}: {len(serie)} dias, "
          f"{serie.fecha.min():%Y-%m-%d} a {serie.fecha.max():%Y-%m-%d}, faltan {faltan} dias")
    print(f"media del periodo: {serie.t_media.mean():.2f} C | "
          f"min: {serie.t_min.min():.2f} C | max: {serie.t_max.max():.2f} C")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solo-procesar", action="store_true", help="no descarga, solo arma el CSV")
    ap.add_argument("--proyecto", default=None, help="proyecto de Google Cloud de Earth Engine")
    args = ap.parse_args()

    if not args.solo_procesar:
        proyecto = args.proyecto or proyecto_por_defecto() or PROYECTO_GEE
        iniciar(proyecto)
        print(f"Earth Engine iniciado | proyecto {proyecto}")
        poligono = poligono_cuenca()
        descargar(a_geometria(poligono))
        malla_de_pixeles(poligono, a_geometria(poligono))
    armar_csv()
