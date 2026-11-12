"""Evapotranspiración potencial (ETP) diaria de la cuenca de San Gil con Hargreaves y Samani (1985),
calculada por el proyecto con la temperatura de ERA5-Land, y la misma cuenta con la temperatura de MSWX
para confrontarla con la ETP que publica CAMELS-COL.

POR QUÉ
  CAMELS-COL publica una ETP diaria (columna poten_evapo) calculada con Hargreaves y la temperatura de
  MSWX (Jimenez et al., 2025, ecuación 1, doi:10.5194/essd-2025-200). Sus valores salen unas 2.75 veces
  más altos que la misma fórmula recalculada con las mismas temperaturas. Aquí se recalcula todo con la
  fórmula publicada, sin ajustes, para tener una ETP propia y ver de dónde viene la diferencia.

LA FÓRMULA (la misma que declara CAMELS-COL)
      ETP = 0.0023 · Ra · (T + 17.8) · (Tmáx − Tmín)^0.5                  [mm/día]
  - T = (Tmáx + Tmín) / 2, como en la formulación original y en CAMELS-COL. Con ERA5-Land se podría usar
    la media de 24 h, pero la constante 0.0023 se calibró con el punto medio, así que se respeta.
  - Ra: radiación extraterrestre, ecuaciones 21 a 25 de FAO-56 (Allen et al., 1998; edición en español
    de 2006, la que cita CAMELS-COL), convertida de MJ m⁻² día⁻¹ a mm/día (equivalente de evaporación)
    multiplicando por 0.408 (ecuación 20 de FAO-56).
  - Latitud: la del centroide del polígono de San Gil (medido en EPSG:3116). CAMELS-COL no dice qué
    latitud usó; en 6° N, un cambio de unas décimas de grado mueve Ra menos del 0.1 %.

ADVERTENCIA SOBRE ERA5-LAND
  Earth Engine agrega el día en UTC (ver 06_era5land_temperatura.py): la mínima y la máxima de un día
  pueden correrse al día vecino. Eso toca la amplitud Tmáx − Tmín que usa Hargreaves; en la escala
  mensual del proyecto el efecto se diluye, pero se declara.

Salidas:
  out/etp_hargreaves_fonce.csv   fecha, ra_mm, etp_era5land, etp_mswx, etp_camels   (mm/día, 1998-2022)
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ID_PRINCIPAL = 24027010
DIAS = pd.date_range("1998-01-01", "2022-12-31", freq="D")

G_SC = 0.0820            # constante solar, MJ m⁻² min⁻¹ (FAO-56)
MJ_A_MM = 0.408          # MJ m⁻² día⁻¹ -> mm/día (FAO-56, ecuación 20)


def radiacion_extraterrestre(latitud_grados, dia_del_anio):
    """Ra en MJ m⁻² día⁻¹, ecuaciones 21-25 de FAO-56."""
    phi = np.radians(latitud_grados)
    dr = 1 + 0.033 * np.cos(2 * np.pi * dia_del_anio / 365)            # distancia relativa Tierra-Sol
    delta = 0.409 * np.sin(2 * np.pi * dia_del_anio / 365 - 1.39)      # declinación solar
    ws = np.arccos(-np.tan(phi) * np.tan(delta))                       # ángulo horario de la puesta del sol
    return 24 * 60 / np.pi * G_SC * dr * (ws * np.sin(phi) * np.sin(delta)
                                          + np.cos(phi) * np.cos(delta) * np.sin(ws))


def radiacion_extraterrestre_integrada(latitud_grados, dia_del_anio):
    """Ra por otro camino, para comprobar la de arriba: integrando minuto a minuto la radiación que llega
    al tope de la atmósfera (constante solar x coseno del ángulo cenital) durante las horas de sol."""
    phi = np.radians(latitud_grados)
    dr = 1 + 0.033 * np.cos(2 * np.pi * dia_del_anio / 365)
    delta = 0.409 * np.sin(2 * np.pi * dia_del_anio / 365 - 1.39)
    angulo_horario = np.linspace(-np.pi, np.pi, 24 * 60 + 1)          # un paso por minuto
    cos_cenital = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(angulo_horario)
    return np.trapezoid(G_SC * dr * np.clip(cos_cenital, 0, None), dx=1.0)


# --- comprobaciones de Ra antes de usarla
# (1) ejemplo 8 de FAO-56: 20° S, 3 de septiembre (día 246) -> Ra = 32.2 MJ m⁻² día⁻¹
assert abs(radiacion_extraterrestre(-20, 246) - 32.2) < 0.05
# (2) la fórmula cerrada coincide con la integración numérica, en la latitud de la cuenca, todo el año
_dias = np.arange(1, 366)
assert max(abs(radiacion_extraterrestre(6.26, d) - radiacion_extraterrestre_integrada(6.26, d)) for d in _dias) < 0.01


def hargreaves(t_min, t_max, ra_mm):
    """ETP de Hargreaves y Samani (1985), mm/día. Un día con Tmáx < Tmín (no debería haber) da NaN."""
    amplitud = (t_max - t_min).where(t_max >= t_min)
    return 0.0023 * ra_mm * ((t_max + t_min) / 2 + 17.8) * np.sqrt(amplitud)


# --- latitud: centroide del polígono de San Gil
cuencas = gpd.read_file(RAIZ / "out/shp_fonce/cuencas_fonce.shp")
latitud = float(cuencas[cuencas.gauge_id == ID_PRINCIPAL].to_crs(3116).centroid.to_crs(4326).y.iloc[0])
ra_mm = pd.Series(radiacion_extraterrestre(latitud, DIAS.dayofyear.values) * MJ_A_MM, index=DIAS)

# --- temperaturas: ERA5-Land (06_era5land_temperatura.py) y MSWX (dentro de CAMELS-COL)
era = pd.read_csv(RAIZ / "out/era5land_temperatura_diaria_fonce.csv", parse_dates=["fecha"]).set_index("fecha").reindex(DIAS)
cam = pd.read_csv(RAIZ / f"data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_{ID_PRINCIPAL}.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam["fecha"], format="%d/%m/%Y")
cam = cam.set_index("fecha").sort_index().reindex(DIAS)

salida = pd.DataFrame({
    "ra_mm": ra_mm,
    "etp_era5land": hargreaves(era["t_min"], era["t_max"], ra_mm),
    "etp_mswx": hargreaves(cam["t_min"], cam["t_max"], ra_mm),
    "etp_camels": cam["etp"],                       # tal como la publica CAMELS-COL
}).rename_axis("fecha")
salida.round(4).to_csv(RAIZ / "out/etp_hargreaves_fonce.csv")

cociente = (salida.etp_camels / salida.etp_mswx).dropna()
print(f"latitud del centroide: {latitud:.4f}°")
print(f"días con ETP: ERA5-Land {salida.etp_era5land.notna().sum()}, MSWX {salida.etp_mswx.notna().sum()}, "
      f"CAMELS-COL {salida.etp_camels.notna().sum()}")
print("media (mm/año):", (salida[["etp_era5land", "etp_mswx", "etp_camels"]].mean() * 365.25).round(0).to_dict())
print(f"CAMELS-COL / Hargreaves con MSWX: mediana {cociente.median():.3f}, "
      f"p5-p95 {cociente.quantile(0.05):.3f}-{cociente.quantile(0.95):.3f}")
