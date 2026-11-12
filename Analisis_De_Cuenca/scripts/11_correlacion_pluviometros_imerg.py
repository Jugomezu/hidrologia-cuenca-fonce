"""Correlación mes a mes de cada pluviómetro del IDEAM contra la celda de IMERG que lo contiene.

El proyecto ya compara IMERG contra el PROMEDIO de la red de pluviómetros (regla 11 de CLAUDE.md).
Este script hace la comparación estación por estación: a cada pluviómetro se le asigna la celda de
IMERG (0.1°) cuyo centro cae más cerca, y sobre los meses en que ambas series tienen dato se calculan
correlación (Pearson y Spearman, en valores y en anomalías), sesgo y RMSE.

Se incluyen las 8 estaciones descargadas, también Mamonal El Hacienda aunque quede fuera de la
divisoria de San Gil (columna `dentro_cuenca`): la pregunta de qué tan bien mide cada pluviómetro
frente al satélite no depende de si esa estación entra o no al promedio de la red.

Entradas
--------
  out/pluviometros_fonce_mensual_depurado.csv   fecha, codigo, nombre, precipitacion_mm, nivel_aprobacion
  out/pluviometros_fonce_catalogo.csv             codigo, nombre, altitud, latitud, longitud, dentro_cuenca
  out/estaciones_subcuencas.csv                   a qué subcuenca pertenece cada estación (solo las 7 de adentro)
  data/imerg/imerg_mensual_col.npz                precip_mm_mes (mes, lon, lat), lon, lat, fechas

Salida
------
  out/correlacion_pluviometros_imerg.csv   una fila por estación, ordenado por r_pearson_anomalias desc.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"

PERIODO = pd.period_range("1998-01", "2022-12", freq="M")   # los 300 meses del período de estudio
RADIO_CELDA = 0.05                                            # medio paso de la malla IMERG (0.1°)

# ---------------------------------------------------------------- 1. cargar pluviómetros
catalogo = pd.read_csv(OUT / "pluviometros_fonce_catalogo.csv")
catalogo["dentro_cuenca"] = catalogo["dentro_cuenca"].astype(bool)

mensual = pd.read_csv(OUT / "pluviometros_fonce_mensual_depurado.csv", parse_dates=["fecha"])
mensual["periodo"] = mensual["fecha"].dt.to_period("M")

subcuencas = pd.read_csv(OUT / "estaciones_subcuencas.csv")[["codigo", "nombre_subcuenca"]]
catalogo = catalogo.merge(subcuencas, on="codigo", how="left")   # NaN para Mamonal El Hacienda (fuera)

assert len(catalogo) == 8, f"se esperaban 8 pluviómetros en el catálogo, hay {len(catalogo)}"

# ---------------------------------------------------------------- 2. cargar IMERG y verificar el eje temporal
npz = np.load(RAIZ / "data/imerg/imerg_mensual_col.npz", allow_pickle=True)
lon, lat, P, fechas_imerg = npz["lon"], npz["lat"], npz["precip_mm_mes"], npz["fechas"]

periodo_imerg = pd.PeriodIndex(fechas_imerg, freq="M")
if len(periodo_imerg) != len(PERIODO) or not (periodo_imerg == PERIODO).all():
    raise SystemExit(
        f"el eje temporal de IMERG no coincide con 1998-01..2022-12 (300 meses): "
        f"trae {len(periodo_imerg)} meses, de {periodo_imerg.min()} a {periodo_imerg.max()}. "
        "Revisar data/imerg/imerg_mensual_col.npz antes de seguir.")

# P puede venir como (mes, lat, lon) o (mes, lon, lat); se deja siempre como (mes, lat, lon),
# igual que en scripts/08_mapas_y_pixeles.py.
if P.shape[1:] == (len(lon), len(lat)):
    P = P.transpose(0, 2, 1)
assert P.shape == (len(PERIODO), len(lat), len(lon)), f"forma inesperada de precip_mm_mes: {P.shape}"

# ---------------------------------------------------------------- 3. asignar a cada estación su celda de IMERG
def celda_mas_cercana(lon_est, lat_est):
    """Índice (i_lat, j_lon) de la celda de IMERG cuyo centro está a menos de RADIO_CELDA en cada eje.

    Con una malla de 0.1°, para un punto dentro de Colombia debe haber exactamente una celda así.
    """
    j_candidatas = np.where(np.abs(lon - lon_est) < RADIO_CELDA)[0]
    i_candidatas = np.where(np.abs(lat - lat_est) < RADIO_CELDA)[0]
    if len(j_candidatas) != 1 or len(i_candidatas) != 1:
        raise SystemExit(
            f"la estación en ({lon_est}, {lat_est}) no cae en una única celda de IMERG "
            f"(candidatas en lon: {len(j_candidatas)}, en lat: {len(i_candidatas)})")
    return i_candidatas[0], j_candidatas[0]


def distancia_km(lon1, lat1, lon2, lat2):
    """Distancia entre dos puntos geográficos (fórmula de Haversine, radio de la Tierra 6371 km)."""
    r = 6371.0
    f1, f2 = np.radians(lat1), np.radians(lat2)
    df, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(df / 2) ** 2 + np.cos(f1) * np.cos(f2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------- 4. estadísticos estación vs. celda
def climatologia(serie):
    """Media de cada mes del calendario (1 a 12), calculada sobre todo el registro disponible de la serie."""
    return serie.groupby(serie.index.month).transform("mean")


def calcular_estadisticos(serie_est, serie_imerg):
    """Recibe dos pd.Series indexadas por período mensual (pueden tener NaN o meses faltantes) y
    devuelve un diccionario con n_meses, correlaciones, sesgo y RMSE sobre los meses en que ambas
    tienen dato."""
    df = pd.concat({"est": serie_est, "imerg": serie_imerg}, axis=1).dropna()
    n = len(df)
    if n < 3:   # con menos de 3 pares no hay correlación que valga la pena reportar
        return dict(n_meses=n, r_pearson=np.nan, r_spearman=np.nan,
                     r_pearson_anomalias=np.nan, r_spearman_anomalias=np.nan,
                     sesgo_razon=np.nan, sesgo_diferencia_mm_mes=np.nan, rmse_mm_mes=np.nan,
                     media_estacion_mm_mes=np.nan, media_imerg_mm_mes=np.nan)

    # anomalías: a cada serie se le quita su propio ciclo anual medio (media de ese mes del
    # calendario, calculada sobre todo el registro disponible de esa serie, no solo el traslape)
    anom_est = (serie_est - climatologia(serie_est)).reindex(df.index)
    anom_imerg = (serie_imerg - climatologia(serie_imerg)).reindex(df.index)

    r_p, _ = pearsonr(df.est, df.imerg)
    r_s, _ = spearmanr(df.est, df.imerg)
    r_pa, _ = pearsonr(anom_est, anom_imerg)
    r_sa, _ = spearmanr(anom_est, anom_imerg)

    media_est, media_imerg = df.est.mean(), df.imerg.mean()
    rmse = np.sqrt(((df.est - df.imerg) ** 2).mean())

    return dict(n_meses=n, r_pearson=r_p, r_spearman=r_s,
                r_pearson_anomalias=r_pa, r_spearman_anomalias=r_sa,
                sesgo_razon=media_est / media_imerg, sesgo_diferencia_mm_mes=media_est - media_imerg,
                rmse_mm_mes=rmse, media_estacion_mm_mes=media_est, media_imerg_mm_mes=media_imerg)


filas = []
for _, est in catalogo.iterrows():
    i_lat, j_lon = celda_mas_cercana(est.longitud, est.latitud)
    lon_celda, lat_celda = lon[j_lon], lat[i_lat]

    serie_est = (mensual.loc[mensual.codigo == est.codigo]
                 .set_index("periodo")["precipitacion_mm"].reindex(PERIODO))
    serie_imerg = pd.Series(P[:, i_lat, j_lon], index=PERIODO)

    stats = calcular_estadisticos(serie_est, serie_imerg)
    filas.append({
        "codigo": est.codigo, "nombre": est.nombre, "dentro_cuenca": est.dentro_cuenca,
        "subcuenca": est.nombre_subcuenca, "altitud": est.altitud,
        "celda_imerg_lon": lon_celda, "celda_imerg_lat": lat_celda,
        "distancia_estacion_celda_km": distancia_km(est.longitud, est.latitud, lon_celda, lat_celda),
        **stats,
    })

resultado = pd.DataFrame(filas).sort_values("r_pearson_anomalias", ascending=False).reset_index(drop=True)
resultado.to_csv(OUT / "correlacion_pluviometros_imerg.csv", index=False)

# ---------------------------------------------------------------- 5. tabla por consola
columnas_consola = ["codigo", "nombre", "dentro_cuenca", "n_meses", "r_pearson", "r_spearman",
                     "r_pearson_anomalias", "r_spearman_anomalias", "sesgo_razon",
                     "sesgo_diferencia_mm_mes", "rmse_mm_mes", "distancia_estacion_celda_km"]
with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
    print("Correlación mensual de cada pluviómetro contra su celda de IMERG (1998-2022)")
    print(resultado[columnas_consola].to_string(index=False))

# celdas compartidas por más de una estación
compartidas = resultado.groupby(["celda_imerg_lon", "celda_imerg_lat"]).codigo.apply(list)
compartidas = compartidas[compartidas.apply(len) > 1]
if len(compartidas):
    print("\nEstaciones que comparten la misma celda de IMERG:")
    for (lon_c, lat_c), codigos in compartidas.items():
        nombres = resultado.loc[resultado.codigo.isin(codigos), "nombre"].tolist()
        print(f"  celda ({lon_c:.2f}, {lat_c:.2f}): {nombres}")
else:
    print("\nNinguna celda de IMERG es compartida por más de una estación.")

mejor = resultado.iloc[0]
peor = resultado.iloc[-1]
print(f"\nLectura: la que mejor concuerda con el satélite mes a mes es {mejor.nombre} "
      f"(r_pearson_anomalias={mejor.r_pearson_anomalias:.2f}); la que peor, {peor.nombre} "
      f"(r_pearson_anomalias={peor.r_pearson_anomalias:.2f}).")
concuerdan = resultado[resultado.r_pearson_anomalias >= 0.5].nombre.tolist()
no_concuerdan = resultado[resultado.r_pearson_anomalias < 0.5].nombre.tolist()
print(f"Con r_pearson_anomalias >= 0.5: {concuerdan if concuerdan else 'ninguna'}.")
print(f"Con r_pearson_anomalias < 0.5: {no_concuerdan if no_concuerdan else 'ninguna'}.")

# ---------------------------------------------------------------- 6. Encino, con y sin 2016-2018
print("\n--- Encino (24020040): con y sin el tramo 2016-2018 ---")
est_encino = catalogo.loc[catalogo.codigo == 24020040].iloc[0]
i_lat, j_lon = celda_mas_cercana(est_encino.longitud, est_encino.latitud)
# este bloque documenta por qué se excluyó el tramo, así que lee la serie CRUDA (con 2016-2018)
crudo = pd.read_csv(OUT / "pluviometros_fonce_mensual_1998_2022.csv", parse_dates=["fecha"])
crudo["periodo"] = crudo["fecha"].dt.to_period("M")
serie_encino = (crudo.loc[crudo.codigo == 24020040]
                .set_index("periodo")["precipitacion_mm"].reindex(PERIODO))
serie_imerg_encino = pd.Series(P[:, i_lat, j_lon], index=PERIODO)

stats_con = calcular_estadisticos(serie_encino, serie_imerg_encino)
fuera_2016_2018 = ~serie_encino.index.year.isin([2016, 2017, 2018])
stats_sin = calcular_estadisticos(serie_encino[fuera_2016_2018], serie_imerg_encino[fuera_2016_2018])

print(f"  con 2016-2018    (n={stats_con['n_meses']}): r_pearson={stats_con['r_pearson']:.2f}, "
      f"r_pearson_anomalias={stats_con['r_pearson_anomalias']:.2f}, "
      f"sesgo={stats_con['sesgo_razon']:.2f}, rmse={stats_con['rmse_mm_mes']:.1f} mm/mes")
print(f"  sin 2016-2018    (n={stats_sin['n_meses']}): r_pearson={stats_sin['r_pearson']:.2f}, "
      f"r_pearson_anomalias={stats_sin['r_pearson_anomalias']:.2f}, "
      f"sesgo={stats_sin['sesgo_razon']:.2f}, rmse={stats_sin['rmse_mm_mes']:.1f} mm/mes")
mejora = stats_sin["r_pearson_anomalias"] > stats_con["r_pearson_anomalias"]
print(f"  -> quitar 2016-2018 {'mejora' if mejora else 'NO mejora'} la correlación de anomalías "
      f"({stats_con['r_pearson_anomalias']:.2f} -> {stats_sin['r_pearson_anomalias']:.2f}).")

# ---------------------------------------------------------------- 7. Pueblo Viejo
print("\n--- Pueblo Viejo (24020230) ---")
fila_pv = resultado.loc[resultado.codigo == 24020230].iloc[0]
print(f"  n_meses={fila_pv.n_meses}, r_pearson={fila_pv.r_pearson:.2f}, "
      f"r_pearson_anomalias={fila_pv.r_pearson_anomalias:.2f}, sesgo_razon={fila_pv.sesgo_razon:.2f} "
      f"(estación mide {fila_pv.media_estacion_mm_mes:.0f} mm/mes en promedio, IMERG "
      f"{fila_pv.media_imerg_mm_mes:.0f} mm/mes en su celda)")
if fila_pv.r_pearson_anomalias >= 0.5 and fila_pv.sesgo_razon < 0.85:
    print("  -> correlaciona razonablemente bien pese al sesgo grande: apunta a un problema de "
          "calibración del pluviómetro (mide sistemáticamente de menos), no a datos erráticos.")
else:
    print("  -> no se cumple el patrón 'r alto con sesgo grande'; revisar el número directamente.")
