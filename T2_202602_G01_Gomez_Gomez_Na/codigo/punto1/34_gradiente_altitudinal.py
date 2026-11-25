"""Fase 9 (punto 1), tema a: gradiente altitudinal de la demanda y de la ET real.

Preguntas: ¿cómo cambian la ETo Penman–Monteith (FAO-56) y sus forzantes con la altura? ¿Y la ET real de los productos
en malla? ¿Qué fracción de la demanda se cumple (ET/ETo) en cada banda de altura?

Pasos:
1. Seis puntos de ERA5-Land (1 580 a 3 259 m): ETo anual, T, ea, u2, Rs y Rn medias 1998–2022, frente a la altura del
   modelo (z despejada de la presión, anexos/punto1/elevacion_puntos_dem.csv): la misma superficie a la que corresponden
   los forzantes. Recta por mínimos cuadrados (6 puntos: solo descriptiva, sin inferencia).
2. Hipsometría de la cuenca con el DEM ALOS de 12 m (cada 4.º píxel, 50 m; dentro del polígono de CAMELS-COL), en bandas
   de ANCHO_BANDA m. El DEM está en UTM 19N: su escala es casi igual en toda la cuenca, así que las FRACCIONES de área
   por banda no cambian (no se usa para áreas absolutas).
3. Productos en malla: cada celda recibe la altura media y el número de píxeles del DEM que caen en ella y en la cuenca
   (peso por área). ET real: TerraClimate aet (~4 km), GLEAM E (0.1°), SSEBop v6.1 (~1 km, 2012–2022). Demanda
   independiente: TerraClimate pet. Media anual del periodo de cada producto.
4. Por banda: ETo de la recta del paso 1 evaluada en la altura media de la banda (extrapolada fuera de 1 580–3 259 m,
   se marca), productos promediados por área, ET/ETo.
5. Comprobación: ETo de la cuenca por hipsometría (Σ ETo(z_banda)·fracción) frente a la ETo por Voronoi (script 04).
   Cenicafé (Jaramillo, 2006) implica −0.02 % por m (−20 % por km): se compara con el gradiente relativo de la ETo.

Escribe productos/punto1/gradiente_altitudinal_puntos.csv, gradiente_altitudinal_bandas.csv,
gradiente_altitudinal_celdas.csv, gradiente_altitudinal_resumen.csv y gradiente_altitudinal.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/34_gradiente_altitudinal.py
"""

from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from pyproj import Transformer
from rasterio.features import geometry_mask

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
DATOS = RAIZ_ENTREGA / "datos" / "punto1"
PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ARCHIVO_CUENCA = (DATOS / "camels_col" / "boundaries" / "03_CAMELS_COL_Basin_boundary"
                  / "CAMELS_COL_catchments_boundaries.shp")
ARCHIVO_DEM = DATOS / "dem" / "dem_fonce_alos_12m.tif"
ELEVACION_PUNTOS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"
CODIGO_IDEAM = "24027010"

SUBMUESTREO_DEM = 4          # cada 4.º píxel del DEM de 12 m (≈ 50 m): de sobra para alturas medias de celdas de ≥ 1 km
ANCHO_BANDA = 500            # m
CENICAFE_COEF = -0.0002      # 1/m, exponente de Jaramillo (2006): ETo = 4.37·exp(−0.0002 h)

PRODUCTOS_MALLA = {   # nombre -> (archivo, variable, años)
    "terraclimate_aet": (DATOS / "terraclimate" / "terraclimate_aet_fonce_1998_2022.nc", "aet", (1998, 2022)),
    "gleam_E": (DATOS / "gleam_v4" / "gleam_v4_E_mensual_1998_2022_fonce.nc", "E", (1998, 2022)),
    "ssebop_v61": (DATOS / "ssebop" / "ssebop_v61_eta_mensual_2012_2022_fonce.nc", "eta", (2012, 2022)),
    "terraclimate_pet": (DATOS / "terraclimate" / "terraclimate_pet_fonce_1998_2022.nc", "pet", (1998, 2022)),
}
ET_REAL = ["terraclimate_aet", "gleam_E", "ssebop_v61"]


# ---------------------------------------------------------------- 1. los seis puntos
def puntos():
    z = pd.read_csv(ELEVACION_PUNTOS).set_index("punto")
    eto = pd.read_csv(PRODUCTOS / "eto_mensual_puntos.csv")
    eto["anio"] = eto["mes"].str[:4].astype(int)
    eto_anual = eto.groupby(["punto", "anio"])["eto_mm_mes"].sum().groupby("punto").mean()
    rn = pd.read_csv(PRODUCTOS / "rn_mensual_puntos.csv")
    rn["anio"] = rn["mes"].str[:4].astype(int)
    rn_anual = rn.groupby(["punto", "anio"])["rn_MJm2_mes"].sum().groupby("punto").mean() / 365.25   # MJ/m²·d
    d = pd.read_csv(PRODUCTOS / "era5land_diario_puntos.csv")
    d["t"] = (d["tmax_C"] + d["tmin_C"]) / 2
    d["u2"] = d["viento10_ms"] * 4.87 / np.log(67.8 * 10 - 5.42)        # FAO-56 ec. 47, como el script 04
    medias = d.groupby("punto")[["t", "tmax_C", "tmin_C", "ea_kPa", "u2", "rs_MJm2"]].mean()
    tabla = pd.DataFrame({"z_modelo_m": z["z_modelo_m"], "z_celda_dem_m": z["z_celda_dem_m"],
                          "eto_mm_anio": eto_anual, "rn_MJm2_d": rn_anual}).join(medias)
    return tabla.rename(columns={"t": "t_C", "u2": "u2_ms"})


def recta(x, y):
    pendiente, corte = np.polyfit(x, y, 1)
    r2 = np.corrcoef(x, y)[0, 1] ** 2
    return pendiente, corte, r2


# ---------------------------------------------------------------- 2. DEM dentro de la cuenca
def dem_en_cuenca():
    cuencas = gpd.read_file(ARCHIVO_CUENCA)
    cuenca = cuencas[cuencas["IDEAM_CODE"].astype(str) == CODIGO_IDEAM]
    assert len(cuenca) == 1
    with rasterio.open(ARCHIVO_DEM) as r:
        alto, ancho = r.height // SUBMUESTREO_DEM, r.width // SUBMUESTREO_DEM
        z = r.read(1, out_shape=(alto, ancho)).astype(float)
        transform = r.transform * r.transform.scale(r.width / ancho, r.height / alto)
        poligono = cuenca.to_crs(r.crs).geometry.iloc[0]
        dentro = ~geometry_mask([poligono], out_shape=(alto, ancho), transform=transform)
        valido = dentro & (z != r.nodata)
        filas, cols = np.nonzero(valido)
        xs, ys = rasterio.transform.xy(transform, filas, cols)
        lon, lat = Transformer.from_crs(r.crs, "EPSG:4326", always_xy=True).transform(np.asarray(xs), np.asarray(ys))
    return pd.DataFrame({"lon": lon, "lat": lat, "z": z[valido]})


# ---------------------------------------------------------------- 3. productos en malla
def celdas_producto(nombre, dem):
    archivo, variable, (a0, a1) = PRODUCTOS_MALLA[nombre]
    ds = xr.open_dataset(archivo)[variable]
    nlat = "latitude" if "latitude" in ds.dims else "lat"
    nlon = "longitude" if "longitude" in ds.dims else "lon"
    nt = "valid_time" if "valid_time" in ds.dims else "time"
    ds = ds.sel({nt: slice(f"{a0}-01-01", f"{a1}-12-31")}).transpose(nt, nlat, nlon)
    valores = np.where(ds.values < 0, np.nan, ds.values.astype(float))
    anios = pd.to_datetime(ds[nt].values).year
    # media anual: suma de los 12 meses de cada año, solo años completos en la celda
    anual = []
    for a in range(a0, a1 + 1):
        sel = valores[anios == a]
        anual.append(np.where(np.isnan(sel).any(axis=0), np.nan, sel.sum(axis=0)) if len(sel) == 12 else
                     np.full(sel.shape[1:], np.nan))
    media = np.nanmean(np.stack(anual), axis=0)
    lats, lons = ds[nlat].values, ds[nlon].values
    paso_lat, paso_lon = float(np.abs(np.diff(lats)).mean()), float(np.abs(np.diff(lons)).mean())
    # cada píxel del DEM a la celda cuyo centro está más cerca
    i = np.abs(dem["lat"].to_numpy()[:, None] - lats[None, :]).argmin(axis=1)
    j = np.abs(dem["lon"].to_numpy()[:, None] - lons[None, :]).argmin(axis=1)
    lejos = (np.abs(dem["lat"].to_numpy() - lats[i]) > paso_lat / 2 + 1e-9) | \
            (np.abs(dem["lon"].to_numpy() - lons[j]) > paso_lon / 2 + 1e-9)
    assert not lejos.any(), f"{nombre}: la malla no cubre toda la cuenca"
    g = pd.DataFrame({"i": i, "j": j, "z": dem["z"].to_numpy()}).groupby(["i", "j"])["z"].agg(["mean", "size"])
    filas = [{"producto": nombre, "lat": lats[a], "lon": lons[b], "z_media_m": fila["mean"], "pixeles": int(fila["size"]),
              "mm_anio": media[a, b]} for (a, b), fila in g.iterrows()]
    celdas = pd.DataFrame(filas)
    celdas["peso"] = celdas["pixeles"] / celdas["pixeles"].sum()
    return celdas


def main():
    # 1. puntos
    tabla_p = puntos()
    resumen = []
    for col, unidad in [("eto_mm_anio", "mm/año"), ("t_C", "°C"), ("ea_kPa", "kPa"), ("u2_ms", "m/s"),
                        ("rs_MJm2", "MJ/m²·d"), ("rn_MJm2_d", "MJ/m²·d")]:
        m, b, r2 = recta(tabla_p["z_modelo_m"], tabla_p[col])
        media = tabla_p[col].mean()
        resumen.append({"variable": col, "unidad": unidad, "pendiente_por_km": m * 1000,
                        "pendiente_pct_por_km": 100 * m * 1000 / media, "corte": b, "r2": r2, "n": len(tabla_p)})
    resumen = pd.DataFrame(resumen)
    m_eto, b_eto, _ = recta(tabla_p["z_modelo_m"], tabla_p["eto_mm_anio"])

    # 2. hipsometría
    dem = dem_en_cuenca()
    bordes = np.arange(np.floor(dem["z"].min() / ANCHO_BANDA) * ANCHO_BANDA,
                       dem["z"].max() + ANCHO_BANDA, ANCHO_BANDA)
    dem["banda"] = pd.cut(dem["z"], bordes, right=False)

    # 3. productos
    celdas = pd.concat([celdas_producto(n, dem) for n in PRODUCTOS_MALLA], ignore_index=True)

    # 4. bandas
    bandas = dem.groupby("banda", observed=True)["z"].agg(z_media_m="mean", pixeles="size").reset_index()
    bandas["fraccion_area"] = bandas["pixeles"] / bandas["pixeles"].sum()
    bandas["eto_mm_anio"] = m_eto * bandas["z_media_m"] + b_eto
    zmin, zmax = tabla_p["z_modelo_m"].min(), tabla_p["z_modelo_m"].max()
    bandas["eto_extrapolada"] = (bandas["z_media_m"] < zmin) | (bandas["z_media_m"] > zmax)
    for n in PRODUCTOS_MALLA:
        c = celdas[celdas["producto"] == n].copy()
        c["banda"] = pd.cut(c["z_media_m"], bordes, right=False)
        c = c.dropna(subset=["mm_anio"])
        prom = c.groupby("banda", observed=True).apply(lambda g: np.average(g["mm_anio"], weights=g["pixeles"]),
                                                     include_groups=False)
        bandas[n] = bandas["banda"].astype(object).map(prom).astype(float)
        bandas[f"celdas_{n}"] = bandas["banda"].astype(object).map(c.groupby("banda", observed=True).size()).fillna(0).astype(int)
    for n in ET_REAL:
        bandas[f"{n}_sobre_eto"] = bandas[n] / bandas["eto_mm_anio"]
    bandas["banda"] = bandas["banda"].astype(str)

    # 5. comprobaciones
    eto_cuenca = pd.read_csv(PRODUCTOS / "eto_mensual_cuenca.csv")
    eto_voronoi = eto_cuenca["eto_mm_mes"].sum() / 25
    eto_hipso = float((bandas["eto_mm_anio"] * bandas["fraccion_area"]).sum())
    resumen = pd.concat([resumen, pd.DataFrame([
        {"variable": "eto_cuenca_hipsometria", "unidad": "mm/año", "corte": eto_hipso},
        {"variable": "eto_cuenca_voronoi", "unidad": "mm/año", "corte": eto_voronoi},
        {"variable": "cenicafe_implicito", "unidad": "%/km", "pendiente_pct_por_km": 100 * CENICAFE_COEF * 1000},
    ])], ignore_index=True)
    for n in PRODUCTOS_MALLA:
        c = celdas[(celdas["producto"] == n)].dropna(subset=["mm_anio"])
        m, b, r2 = recta(c["z_media_m"], c["mm_anio"])
        resumen = pd.concat([resumen, pd.DataFrame([{
            "variable": f"{n}_celdas", "unidad": "mm/año", "pendiente_por_km": m * 1000,
            "pendiente_pct_por_km": 100 * m * 1000 / np.average(c["mm_anio"], weights=c["pixeles"]),
            "corte": b, "r2": r2, "n": len(c)}])], ignore_index=True)

    tabla_p.round(4).to_csv(PRODUCTOS / "gradiente_altitudinal_puntos.csv")
    bandas.round(4).to_csv(PRODUCTOS / "gradiente_altitudinal_bandas.csv", index=False)
    celdas.round(4).to_csv(PRODUCTOS / "gradiente_altitudinal_celdas.csv", index=False)
    resumen.round(5).to_csv(PRODUCTOS / "gradiente_altitudinal_resumen.csv", index=False)
    figura(tabla_p, celdas, bandas, m_eto, b_eto)
    pd.set_option("display.width", 220)
    print(tabla_p.round(3).to_string())
    print(resumen.round(3).to_string())
    print(bandas.round(3).to_string())


# ---------------------------------------------------------------- figura
def figura(tabla_p, celdas, bandas, m_eto, b_eto):
    fig, ejes = plt.subplots(1, 3, figsize=(16, 5.2))
    colores = {"terraclimate_aet": "#009E73", "gleam_E": "#CC79A7", "ssebop_v61": "#E69F00", "terraclimate_pet": "#56B4E9"}
    nombres = {"terraclimate_aet": "TerraClimate aet", "gleam_E": "GLEAM E", "ssebop_v61": "SSEBop v6.1 (2012–2022)",
               "terraclimate_pet": "TerraClimate pet (demanda)"}
    # (a) demanda frente a la altura
    ax = ejes[0]
    c = celdas[celdas["producto"] == "terraclimate_pet"]
    ax.scatter(c["mm_anio"], c["z_media_m"], s=8 + 40 * c["peso"] / c["peso"].max(), color=colores["terraclimate_pet"],
               alpha=0.6, label=nombres["terraclimate_pet"])
    ax.scatter(tabla_p["eto_mm_anio"], tabla_p["z_modelo_m"], color="#0072B2", s=50, zorder=3,
               label="ETo Penman–Monteith (FAO-56), 6 puntos")
    z = np.array([bandas["z_media_m"].min(), bandas["z_media_m"].max()])
    ax.plot(m_eto * z + b_eto, z, "--", color="#0072B2", label=f"recta: {m_eto * 1000:+.0f} mm/año por km")
    ax.set_xlim(0, None)
    ax.set_xlabel("mm/año")
    ax.set_ylabel("altura (m)")
    ax.set_title("Demanda frente a la altura")
    ax.legend(fontsize=8)
    # (b) ET real frente a la altura
    ax = ejes[1]
    for n in ET_REAL:
        c = celdas[(celdas["producto"] == n)].dropna(subset=["mm_anio"])
        ax.scatter(c["mm_anio"], c["z_media_m"], s=8 + 40 * c["peso"] / c["peso"].max(), color=colores[n], alpha=0.6,
                   label=nombres[n])
    ax.plot(m_eto * z + b_eto, z, "--", color="#0072B2", label="ETo (recta de los 6 puntos)")
    ax.set_xlim(0, None)
    ax.set_xlabel("mm/año")
    ax.set_title("ET real de los productos, por celda")
    ax.legend(fontsize=8)
    # (c) hipsometría y ET/ETo por banda
    ax = ejes[2]
    etiquetas = [f"{int(z - ANCHO_BANDA / 2)}–{int(z + ANCHO_BANDA / 2)} m"
                 for z in (bandas["z_media_m"] // ANCHO_BANDA * ANCHO_BANDA + ANCHO_BANDA / 2)]
    y = np.arange(len(bandas))
    ax.barh(y, bandas["fraccion_area"], color="#BBBBBB", label="fracción del área")
    ax.set_yticks(y, etiquetas, fontsize=8)
    ax.set_xlabel("fracción del área de la cuenca")
    ax.set_title("Bandas de altura: área y ET/ETo")
    ax2 = ax.twiny()
    for n in ET_REAL:
        ax2.plot(bandas[f"{n}_sobre_eto"], y, "o-", color=colores[n], label=nombres[n])
    ax2.set_xlim(0, 1.4)
    ax2.axvline(1, color="k", lw=0.8)
    ax2.set_xlabel("ET/ETo")
    ax2.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(PRODUCTOS / "gradiente_altitudinal.png", dpi=150)


if __name__ == "__main__":
    main()
