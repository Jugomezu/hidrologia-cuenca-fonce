"""Comprobaciones de la ETo de FAO-56 (punto 1): ETo con medias mensuales y alturas de los 6 puntos frente al DEM.

Dos comprobaciones independientes del cálculo principal (04_eto_fao56.py), que escriben en anexos/punto1/:

1. ETo con medias mensuales (anexos/punto1/eto_medias_mensuales_vs_suma_diarias.csv)
   El cálculo principal aplica la ec. 6 de FAO-56 a cada día y suma los días del mes. Aquí se hace aparte, como
   lo permite FAO-56 para datos mensuales (cap. 3): se promedian en el mes Tmax, Tmin, ea, P, el viento y Rs,
   se calcula Rn y la ETo de un "día medio" del mes, y se multiplica por los días del mes. La diferencia entre
   los dos mide el error de agregar antes de calcular: la ec. 6 no es lineal, así que el promedio de las ETo
   diarias no es la ETo de las condiciones promedio.
   - Ra del mes: la del día juliano de mitad de mes, J = int(30.4 M − 15) (FAO-56, nota de la ec. 21).
   - Rs/Rso, Rnl y z del modelo: igual que en 03_series_diarias_rn.py, pero con los promedios del mes.
   - G mensual con la ec. 43 de FAO-56, G = 0.07 (T_mes siguiente − T_mes anterior), como pide el plan del punto 1.
     En los extremos de la serie falta un vecino: en 1998-01 se usa la ec. 44 hacia adelante,
     G = 0.14 (T_siguiente − T_mes), y en 2022-12 la ec. 44, G = 0.14 (T_mes − T_anterior).
   - Se guarda también la ETo con medias mensuales y G = 0, para separar las dos causas de la diferencia: la de
     agregar antes de calcular (G = 0 contra la suma de diarias) y la del flujo de calor en el suelo.

2. Altura de los 6 puntos frente al DEM ALOS PALSAR 12.5 m (anexos/punto1/elevacion_puntos_dem.csv)
   Para cada punto se comparan tres alturas:
   - z_celda_dem: media del DEM dentro de la celda de 0.1° de ERA5-Land (el terreno real que la celda representa);
   - z_region_dem: media del DEM en su región de Voronoi recortada a la cuenca (lo que el punto debe representar);
   - z_modelo: altura de la superficie del modelo, despejada de la presión media sp con la ec. 7 de FAO-56, la
     misma que usa 03_series_diarias_rn.py. Es una aproximación: la ec. 7 supone una atmósfera estándar.
   La diferencia entre z_modelo y z_region_dem se traduce en el efecto sobre T y ea con dos gradientes: el de
   referencia de −6.5 °C/km (el que usa la Tarea 1, scripts/12_gradiente_termico.py) y el del propio ERA5-Land,
   la recta de T media y ea media de los 6 puntos contra su z_modelo.
   El DEM viene en UTM 19N (así se recortó en la Tarea 1); aquí solo se promedian alturas, no se miden áreas, así
   que la zona UTM no afecta el resultado.

Entradas: productos/punto1/era5land_diario_puntos.csv y eto_mensual_puntos.csv (salidas de 03 y 04),
datos/punto1/dem/dem_fonce_alos_12m.tif y datos/punto1/era5land_puntos/regiones_voronoi_puntos.geojson
(regiones de Voronoi de los 6 puntos recortadas a la cuenca, de la selección de puntos del 2026-11-12).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/04b_comprobaciones_eto.py
"""

import importlib.util
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.mask
from shapely.geometry import box

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_CODIGO = RAIZ_ENTREGA / "codigo" / "punto1"
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_DIARIA = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"
ENTRADA_ETO_MENSUAL = CARPETA_PRODUCTOS / "eto_mensual_puntos.csv"
ENTRADA_DEM = RAIZ_ENTREGA / "datos" / "punto1" / "dem" / "dem_fonce_alos_12m.tif"
ENTRADA_VORONOI = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos" / "regiones_voronoi_puntos.geojson"
CARPETA_ANEXOS = RAIZ_ENTREGA / "anexos" / "punto1"
SALIDA_MENSUAL = CARPETA_ANEXOS / "eto_medias_mensuales_vs_suma_diarias.csv"
SALIDA_ALTURAS = CARPETA_ANEXOS / "elevacion_puntos_dem.csv"

MEDIO_LADO_CELDA_GRADOS = 0.05      # las celdas de ERA5-Land miden 0.1°
GRADIENTE_TERMICO_C_POR_KM = -6.5   # gradiente de referencia en aire húmedo


def cargar_modulo(nombre_archivo):
    """Importa un script de codigo/punto1 para reusar sus funciones (sus nombres empiezan por un número)."""
    ruta = CARPETA_CODIGO / nombre_archivo
    especificacion = importlib.util.spec_from_file_location(ruta.stem.lstrip("0123456789_"), ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


# Mismas ecuaciones que el cálculo principal: Ra, e°(T), z desde P (03) y la ec. 6 (04).
rn_fao56 = cargar_modulo("03_series_diarias_rn.py")
eto_fao56 = cargar_modulo("04_eto_fao56.py")


def eto_con_medias_mensuales(diaria):
    """ETo mensual (mm/mes) de un punto calculada con las medias del mes, no con los días."""
    z_modelo = rn_fao56.altura_desde_presion(diaria["sp_kPa"].mean())
    medias = diaria.resample("MS")[["tmax_C", "tmin_C", "ea_kPa", "sp_kPa", "viento10_ms", "rs_MJm2"]].mean()
    medias["dias"] = medias.index.days_in_month

    dia_juliano = (30.4 * medias.index.month - 15).astype(int)            # mitad de mes, FAO-56
    latitud = float(diaria["latitud"].iloc[0])
    ra = rn_fao56.radiacion_extraterrestre(latitud, dia_juliano.to_numpy())
    rso = (0.75 + 2e-5 * z_modelo) * ra                                     # ec. 37
    rns = (1 - rn_fao56.ALBEDO_REFERENCIA) * medias["rs_MJm2"]              # ec. 38
    rs_sobre_rso = (medias["rs_MJm2"] / rso).clip(upper=1.0)
    t4 = ((medias["tmax_C"] + rn_fao56.KELVIN) ** 4 + (medias["tmin_C"] + rn_fao56.KELVIN) ** 4) / 2
    rnl = (rn_fao56.STEFAN_BOLTZMANN * t4 * (0.34 - 0.14 * np.sqrt(medias["ea_kPa"]))  # ec. 39
           * (1.35 * rs_sobre_rso - 0.35))
    medias["rn_MJm2"] = rns - rnl                                           # ec. 40

    eto_g0 = eto_fao56.eto_fao56(medias)  # G = 0: solo el efecto de agregar

    # G mensual (MJ/m²·día): ec. 43 con los meses vecinos; ec. 44 en los dos extremos de la serie.
    t_media = (medias["tmax_C"] + medias["tmin_C"]) / 2
    g_mensual = 0.07 * (t_media.shift(-1) - t_media.shift(1))                     # ec. 43
    g_mensual.iloc[0] = 0.14 * (t_media.iloc[1] - t_media.iloc[0])                # ec. 44, hacia adelante
    g_mensual.iloc[-1] = 0.14 * (t_media.iloc[-1] - t_media.iloc[-2])             # ec. 44
    # La ec. 6 es lineal en (Rn − G): restar G del numerador radiativo basta.
    delta = eto_fao56.pendiente_saturacion(eto_g0["t_C"])
    gamma = 0.665e-3 * medias["sp_kPa"]
    denominador = delta + gamma * (1 + 0.34 * eto_g0["u2_ms"])
    eto_con_g = eto_g0["eto_mm"] - 0.408 * delta * g_mensual / denominador

    return pd.DataFrame({"dias": medias["dias"],
                         "g_MJm2_dia": g_mensual,
                         "eto_medias_g0_mm_mes": eto_g0["eto_mm"] * medias["dias"],
                         "eto_medias_mm_mes": eto_con_g * medias["dias"]})


def comprobar_medias_mensuales():
    diaria = pd.read_csv(ENTRADA_DIARIA, parse_dates=["fecha"]).set_index("fecha")
    # La latitud de cada celda se toma de los CSV horarios, igual que en 03_series_diarias_rn.py.
    latitudes = {n: rn_fao56.leer_horaria_local(n)[1] for n in rn_fao56.PUNTOS}
    diaria["latitud"] = diaria["punto"].map(latitudes)

    partes = []
    for n, del_punto in diaria.groupby("punto"):
        mensual = eto_con_medias_mensuales(del_punto)
        mensual.insert(0, "punto", n)
        partes.append(mensual)
    medias = pd.concat(partes).reset_index().rename(columns={"fecha": "mes"})
    medias["mes"] = medias["mes"].dt.strftime("%Y-%m")

    suma_diarias = pd.read_csv(ENTRADA_ETO_MENSUAL)[["mes", "punto", "eto_mm_mes"]]
    tabla = suma_diarias.rename(columns={"eto_mm_mes": "eto_suma_diarias_mm_mes"}).merge(
        medias, on=["mes", "punto"], validate="one_to_one")
    assert len(tabla) == 6 * 300

    # Cuenca: promedio ponderado por Voronoi, con los mismos pesos del cálculo principal.
    peso = tabla["punto"].map(eto_fao56.PESOS)
    columnas = ["g_MJm2_dia", "eto_suma_diarias_mm_mes", "eto_medias_g0_mm_mes", "eto_medias_mm_mes"]
    cuenca = (tabla[columnas].mul(peso, axis=0).groupby(tabla["mes"]).sum()
              .div(peso.groupby(tabla["mes"]).sum(), axis=0).reset_index())
    cuenca["punto"] = "cuenca"
    cuenca["dias"] = pd.PeriodIndex(cuenca["mes"], freq="M").days_in_month
    tabla = pd.concat([tabla.astype({"punto": str}), cuenca], ignore_index=True)

    # Diferencia total (medias con G de la ec. 43 menos suma de diarias) y sus dos partes.
    tabla["diferencia_mm_mes"] = tabla["eto_medias_mm_mes"] - tabla["eto_suma_diarias_mm_mes"]
    tabla["diferencia_pct"] = 100 * tabla["diferencia_mm_mes"] / tabla["eto_suma_diarias_mm_mes"]
    tabla["parte_agregar_mm_mes"] = tabla["eto_medias_g0_mm_mes"] - tabla["eto_suma_diarias_mm_mes"]
    tabla["parte_g_mm_mes"] = tabla["eto_medias_mm_mes"] - tabla["eto_medias_g0_mm_mes"]
    tabla = tabla[["mes", "punto", "dias", "g_MJm2_dia", "eto_suma_diarias_mm_mes", "eto_medias_g0_mm_mes",
                   "eto_medias_mm_mes", "diferencia_mm_mes", "diferencia_pct", "parte_agregar_mm_mes",
                   "parte_g_mm_mes"]]
    CARPETA_ANEXOS.mkdir(parents=True, exist_ok=True)
    tabla.round(3).to_csv(SALIDA_MENSUAL, index=False)
    print(f"Listo: {SALIDA_MENSUAL} ({len(tabla)} filas)")

    print("\nETo con medias mensuales menos suma de diarias (mm/mes; % de la suma de diarias), 300 meses:")
    resumen = tabla.groupby("punto").agg(
        media_mm=("diferencia_mm_mes", "mean"), media_pct=("diferencia_pct", "mean"),
        min_pct=("diferencia_pct", "min"), max_pct=("diferencia_pct", "max"),
        agregar_media_mm=("parte_agregar_mm_mes", "mean"),
        g_max_abs_mm=("parte_g_mm_mes", lambda s: s.abs().max()))
    print(resumen.round(2).to_string())
    de_la_cuenca = tabla[tabla["punto"] == "cuenca"].copy()
    de_la_cuenca["mes_del_anio"] = de_la_cuenca["mes"].str[5:].astype(int)
    print("\nCuenca, por mes del año (media de los 25 años):")
    print(de_la_cuenca.groupby("mes_del_anio")[["eto_suma_diarias_mm_mes", "diferencia_mm_mes", "diferencia_pct",
                                                 "parte_agregar_mm_mes", "parte_g_mm_mes"]]
          .mean().round(2).to_string())


def media_dem(dem, geometria_lonlat):
    """Media del DEM y fracción de píxeles con dato dentro de un polígono en lon/lat."""
    geometria = gpd.GeoSeries([geometria_lonlat], crs="EPSG:4326").to_crs(dem.crs).iloc[0]
    recorte, _ = rasterio.mask.mask(dem, [geometria], crop=True, filled=False)
    valores = recorte[0]
    return float(valores.mean()), float(valores.count() / valores.size if valores.size else 0)


def comprobar_alturas():
    regiones = gpd.read_file(ENTRADA_VORONOI).to_crs("EPSG:4326").set_index("punto").sort_index()
    filas = []
    with rasterio.open(ENTRADA_DEM) as dem:
        for n, region in regiones.iterrows():
            horaria, _ = rn_fao56.leer_horaria_local(n)
            z_modelo = rn_fao56.altura_desde_presion(horaria["sp_kPa"].mean())
            # Medias del período en el punto, para el gradiente vertical del propio modelo.
            t_media = horaria["t2m_C"].mean()
            ea_media = horaria["ea_kPa"].mean()
            celda = box(region["lon"] - MEDIO_LADO_CELDA_GRADOS, region["lat"] - MEDIO_LADO_CELDA_GRADOS,
                        region["lon"] + MEDIO_LADO_CELDA_GRADOS, region["lat"] + MEDIO_LADO_CELDA_GRADOS)
            z_celda, cobertura_celda = media_dem(dem, celda)
            z_region, _ = media_dem(dem, region.geometry)
            filas.append({"punto": n, "lon": region["lon"], "lat": region["lat"],
                          "z_celda_dem_m": z_celda, "cobertura_dem_celda": cobertura_celda,
                          "z_region_dem_m": z_region, "z_modelo_m": z_modelo,
                          "t2m_media_C": t_media, "ea_media_kPa": ea_media})
    tabla = pd.DataFrame(filas)
    tabla["modelo_menos_celda_m"] = tabla["z_modelo_m"] - tabla["z_celda_dem_m"]
    tabla["modelo_menos_region_m"] = tabla["z_modelo_m"] - tabla["z_region_dem_m"]
    tabla["celda_menos_region_m"] = tabla["z_celda_dem_m"] - tabla["z_region_dem_m"]
    # Gradientes verticales del propio ERA5-Land entre los 6 puntos (recta de mínimos cuadrados contra z_modelo).
    gradiente_t = np.polyfit(tabla["z_modelo_m"] / 1000, tabla["t2m_media_C"], 1)[0]     # °C/km
    gradiente_ea = np.polyfit(tabla["z_modelo_m"] / 1000, tabla["ea_media_kPa"], 1)[0]   # kPa/km
    print(f"\nGradiente de ERA5-Land entre los 6 puntos: T {gradiente_t:.2f} °C/km, ea {gradiente_ea:.3f} kPa/km "
          f"(referencia para T: {GRADIENTE_TERMICO_C_POR_KM} °C/km)")
    # Si el modelo queda más bajo que su región (Δz < 0), la ve más caliente y más húmeda: ΔX = gradiente × Δz.
    dz_km = tabla["modelo_menos_region_m"] / 1000
    tabla["efecto_t_referencia_C"] = GRADIENTE_TERMICO_C_POR_KM * dz_km
    tabla["efecto_t_era5land_C"] = gradiente_t * dz_km
    tabla["efecto_ea_era5land_kPa"] = gradiente_ea * dz_km
    tabla.round(3).to_csv(SALIDA_ALTURAS, index=False)
    print(f"\nListo: {SALIDA_ALTURAS}")
    print(tabla.round(1).to_string(index=False))

    peso = tabla["punto"].map(eto_fao56.PESOS)
    for columna in ["z_celda_dem_m", "z_region_dem_m", "z_modelo_m", "efecto_t_era5land_C",
                    "efecto_ea_era5land_kPa"]:
        print(f"Media ponderada por Voronoi de {columna}: {np.average(tabla[columna], weights=peso):.3f}")


def main():
    comprobar_medias_mensuales()
    comprobar_alturas()


if __name__ == "__main__":
    main()
