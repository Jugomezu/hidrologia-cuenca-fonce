"""Radiación solar Rs estimada con el brillo solar de 3 estaciones del IDEAM, comparada con la ssrd de ERA5-Land (punto 1, fase 3).

Lee:
    datos/punto1/ideam_brillo_solar/brillo_solar_diario_1998_2022_3est.zip   brillo solar total diario (h), DHIME
    datos/punto1/ideam/cne_ideam.csv                                         coordenadas y altura de cada estación
    datos/punto1/era5land_puntos/metadatos_descarga.json                     coordenadas de los 6 puntos de ERA5-Land
    productos/punto1/era5land_diario_puntos.csv                              Rs diaria de ERA5-Land (salida de 03)
    anexos/punto1/elevacion_puntos_dem.csv                                   altura de cada punto (salida de 04b)

Escribe en productos/punto1/:
    rs_estaciones_diaria.csv                   Rs de Angstrom por estación y día, con la Rs de ERA5-Land del mismo día
    rs_estaciones_vs_era5land_por_mes.csv      sesgo, RMSE y ciclo anual por estación y mes calendario
    rs_estaciones_vs_era5land_resumen.csv      lo mismo con todos los meses juntos, distancia y diferencia de altura
    rs_estaciones_vs_era5land_ciclo_anual.png  ciclo anual de las dos Rs en cada estación

Método, FAO-56 (Allen et al., 1998), cap. 3:
    N   horas de luz del día, ec. 34: N = (24/π) ωs, con ωs de la ec. 25 y la latitud de la estación
    Ra  radiación extraterrestre, ec. 21 (con ec. 23, 24 y 25), latitud de la estación
    Rs  ecuación de Angstrom, ec. 35: Rs = (a_s + b_s n/N) Ra, con a_s = 0.25 y b_s = 0.50, los valores que FAO-56
        recomienda cuando no hay calibración local (no la hay: no existe radiación medida en la cuenca).

Celda de ERA5-Land: solo se descargaron los 6 puntos de la cuenca, así que cada estación se compara con el punto más
cercano de esos 6 (distancia geodésica en una esfera de radio 6 371 km). No es necesariamente la celda que contiene
a la estación. Se reportan la distancia y la diferencia de altura estación − punto, con dos alturas del punto: la
media del DEM en su celda y la altura del modelo despejada de sp (ambas de anexos/punto1/elevacion_puntos_dem.csv).

Días: DHIME entrega el brillo solar con fecha «AAAA-MM-DD 00:00», que se toma como el día civil local. La Rs de
ERA5-Land ya está en días locales (UTC−5, script 03). Se comparan solo los días con dato en la estación; no se rellena.

Control de calidad del brillo solar: se descarta el día con n > N (más horas de sol que horas de luz) o n < 0, y se
cuenta cuántos fueron. Todo el registro de DHIME viene marcado «Preliminar».

Sesgo = media de (Rs ERA5-Land − Rs estación); positivo es ERA5-Land por encima. RMSE con los mismos días.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/12_rs_brillo_solar_vs_era5land.py
"""

import json
import zipfile
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (va después de fijar el backend sin pantalla)

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
ZIP_BRILLO = RAIZ_ENTREGA / "datos" / "punto1" / "ideam_brillo_solar" / "brillo_solar_diario_1998_2022_3est.zip"
CATALOGO_IDEAM = RAIZ_ENTREGA / "datos" / "punto1" / "ideam" / "cne_ideam.csv"
METADATOS_ERA5 = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos" / "metadatos_descarga.json"
DIARIO_ERA5 = RAIZ_ENTREGA / "productos" / "punto1" / "era5land_diario_puntos.csv"
ALTURAS_PUNTOS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"

CARPETA_SALIDA = RAIZ_ENTREGA / "productos" / "punto1"
SALIDA_DIARIA = CARPETA_SALIDA / "rs_estaciones_diaria.csv"
SALIDA_POR_MES = CARPETA_SALIDA / "rs_estaciones_vs_era5land_por_mes.csv"
SALIDA_RESUMEN = CARPETA_SALIDA / "rs_estaciones_vs_era5land_resumen.csv"
SALIDA_FIGURA = CARPETA_SALIDA / "rs_estaciones_vs_era5land_ciclo_anual.png"

ESTACIONES = ["24025040", "24025030", "24025050"]   # Escuela Agrícola Mogotes, La Sierra, Charalá
INICIO, FIN = "1998-01-01", "2022-12-31"

# Coeficientes de Angstrom sin calibración local, FAO-56 cap. 3 (ec. 35)
A_S = 0.25
B_S = 0.50
CONSTANTE_SOLAR = 0.0820     # Gsc, MJ/m²·min
RADIO_TIERRA_KM = 6371.0


def radiacion_extraterrestre_y_horas_luz(latitud_grados, dia_del_anio):
    """Ra (MJ/m²·día, ec. 21) y N (h, ec. 34) de FAO-56, con dr (ec. 23), δ (ec. 24) y ωs (ec. 25)."""
    phi = np.radians(latitud_grados)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * dia_del_anio)                  # ec. 23
    delta = 0.409 * np.sin(2 * np.pi / 365 * dia_del_anio - 1.39)            # ec. 24
    omega_s = np.arccos(-np.tan(phi) * np.tan(delta))                        # ec. 25
    ra = (24 * 60 / np.pi) * CONSTANTE_SOLAR * dr * (                        # ec. 21
        omega_s * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(omega_s))
    horas_luz = 24 / np.pi * omega_s                                         # ec. 34
    return ra, horas_luz


def distancia_km(lon1, lat1, lon2, lat2):
    """Distancia de círculo máximo (haversine) en km."""
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * RADIO_TIERRA_KM * np.arcsin(np.sqrt(a))


def leer_estaciones():
    """Código, nombre, lon, lat y altura de las 3 estaciones, del catálogo nacional de estaciones del IDEAM."""
    catalogo = pd.read_csv(CATALOGO_IDEAM, dtype=str)
    catalogo["estacion"] = catalogo["codigo"].str.lstrip("0")
    estaciones = catalogo[catalogo["estacion"].isin(ESTACIONES)].copy()
    assert len(estaciones) == len(ESTACIONES)
    for columna in ["longitud", "latitud", "altitud"]:
        estaciones[columna] = estaciones[columna].astype(float)
    return estaciones.set_index("estacion")[["nombre", "longitud", "latitud", "altitud"]]


def leer_brillo_solar():
    """Brillo solar diario (h) de DHIME, una columna por estación."""
    with zipfile.ZipFile(ZIP_BRILLO) as archivo:
        with archivo.open("descargaDhime.csv") as csv:
            crudo = pd.read_csv(csv, dtype={"CodigoEstacion": str})
    assert (crudo["Parametro"] == "Brillo solar total diario").all()
    crudo["fecha"] = pd.to_datetime(crudo["Fecha"].str[:10])
    assert not crudo.duplicated(["CodigoEstacion", "fecha"]).any()
    return crudo.pivot(index="fecha", columns="CodigoEstacion", values="Valor")


def punto_mas_cercano(estaciones):
    """Para cada estación, el punto de ERA5-Land más cercano de los 6, su distancia y sus alturas."""
    puntos = pd.DataFrame(json.loads(METADATOS_ERA5.read_text(encoding="utf-8"))["archivos"])[["punto", "lon", "lat"]]
    alturas = pd.read_csv(ALTURAS_PUNTOS).set_index("punto")[["z_celda_dem_m", "z_modelo_m"]]
    filas = []
    for codigo, est in estaciones.iterrows():
        d = distancia_km(est["longitud"], est["latitud"], puntos["lon"], puntos["lat"])
        cercano = puntos.loc[d.idxmin()]
        n = int(cercano["punto"])
        filas.append({
            "estacion": codigo,
            "nombre": est["nombre"],
            "lon_estacion": est["longitud"],
            "lat_estacion": est["latitud"],
            "z_estacion_m": est["altitud"],
            "punto_era5": n,
            "lon_punto": cercano["lon"],
            "lat_punto": cercano["lat"],
            "distancia_km": round(float(d.min()), 1),
            "z_celda_dem_m": round(alturas.loc[n, "z_celda_dem_m"], 0),
            "z_modelo_m": round(alturas.loc[n, "z_modelo_m"], 0),
        })
    tabla = pd.DataFrame(filas).set_index("estacion")
    tabla["estacion_menos_celda_dem_m"] = tabla["z_estacion_m"] - tabla["z_celda_dem_m"]
    tabla["estacion_menos_modelo_m"] = tabla["z_estacion_m"] - tabla["z_modelo_m"]
    return tabla


def metricas(grupo):
    """Medias, sesgo y RMSE de un conjunto de días pareados."""
    diferencia = grupo["rs_era5_MJm2"] - grupo["rs_estacion_MJm2"]
    return pd.Series({
        "dias": len(grupo),
        "rs_estacion_media": grupo["rs_estacion_MJm2"].mean(),
        "rs_era5_media": grupo["rs_era5_MJm2"].mean(),
        "sesgo_MJm2": diferencia.mean(),
        "sesgo_pct": 100 * diferencia.mean() / grupo["rs_estacion_MJm2"].mean(),
        "rmse_MJm2": np.sqrt((diferencia ** 2).mean()),
        "correlacion_diaria": grupo["rs_era5_MJm2"].corr(grupo["rs_estacion_MJm2"]),
    })


def main():
    estaciones = leer_estaciones()
    brillo = leer_brillo_solar()
    vecinos = punto_mas_cercano(estaciones)
    era5 = pd.read_csv(DIARIO_ERA5, parse_dates=["fecha"])[["fecha", "punto", "rs_MJm2"]]
    era5 = era5.pivot(index="fecha", columns="punto", values="rs_MJm2")

    diarias = []
    for codigo in ESTACIONES:
        n_sol = brillo[codigo].loc[INICIO:FIN].dropna()
        ra, horas_luz = radiacion_extraterrestre_y_horas_luz(
            estaciones.loc[codigo, "latitud"], n_sol.index.day_of_year.to_numpy())
        tabla = pd.DataFrame({"brillo_h": n_sol, "N_h": horas_luz, "ra_MJm2": ra}, index=n_sol.index)
        fuera_de_rango = (tabla["brillo_h"] > tabla["N_h"]) | (tabla["brillo_h"] < 0)
        vecinos.loc[codigo, "dias_con_brillo"] = len(tabla)
        vecinos.loc[codigo, "dias_descartados_n_mayor_N"] = int(fuera_de_rango.sum())
        tabla = tabla[~fuera_de_rango]
        tabla["rs_estacion_MJm2"] = (A_S + B_S * tabla["brillo_h"] / tabla["N_h"]) * tabla["ra_MJm2"]   # ec. 35
        tabla["rs_era5_MJm2"] = era5.loc[tabla.index, vecinos.loc[codigo, "punto_era5"]].to_numpy()
        tabla.insert(0, "punto_era5", vecinos.loc[codigo, "punto_era5"])
        tabla.insert(0, "estacion", codigo)
        diarias.append(tabla)

    diaria = pd.concat(diarias)
    diaria.index.name = "fecha"
    assert diaria["rs_era5_MJm2"].notna().all()
    # Rs de Angstrom acotada por construcción entre 0.25 Ra y 0.75 Ra
    assert ((diaria["rs_estacion_MJm2"] >= A_S * diaria["ra_MJm2"] - 1e-9)
            & (diaria["rs_estacion_MJm2"] <= (A_S + B_S) * diaria["ra_MJm2"] + 1e-9)).all()

    diaria["mes"] = diaria.index.month
    por_mes = diaria.groupby(["estacion", "mes"]).apply(metricas, include_groups=False).reset_index()
    resumen = diaria.groupby("estacion").apply(metricas, include_groups=False)
    resumen = vecinos.join(resumen)

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    salida_diaria = diaria.drop(columns="mes").copy()
    salida_diaria.index = salida_diaria.index.strftime("%Y-%m-%d")
    salida_diaria.round(4).to_csv(SALIDA_DIARIA)
    por_mes.round(3).to_csv(SALIDA_POR_MES, index=False)
    resumen.round(3).to_csv(SALIDA_RESUMEN)

    # Figura: ciclo anual (media por mes calendario de los días pareados), una gráfica por estación
    nombres_mes = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    figura, ejes = plt.subplots(1, 3, figsize=(12, 4.3), sharey=True)
    for eje, codigo in zip(ejes, ESTACIONES):
        datos = por_mes[por_mes["estacion"] == codigo]
        info = resumen.loc[codigo]
        eje.plot(datos["mes"], datos["rs_estacion_media"], "o-", color="#1f6f8b", label="Estación (Angstrom)")
        eje.plot(datos["mes"], datos["rs_era5_media"], "s--", color="#c8553d",
                 label=f"ERA5-Land (punto {int(info['punto_era5'])})")
        eje.set_title(f"{info['nombre'].split(' [')[0].title()} ({int(info['z_estacion_m'])} m)", fontsize=10)
        eje.set_xticks(range(1, 13), nombres_mes)
        eje.grid(alpha=0.3)
        eje.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)
    ejes[0].set_ylabel("Rs media (MJ/m²·día)")
    figura.suptitle("Ciclo anual de Rs, 1998–2022 (solo días con brillo solar)", fontsize=11)
    figura.tight_layout()
    figura.savefig(SALIDA_FIGURA, dpi=150)

    pd.set_option("display.width", 200)
    print(resumen[["punto_era5", "distancia_km", "estacion_menos_celda_dem_m", "estacion_menos_modelo_m",
                   "dias", "dias_descartados_n_mayor_N", "rs_estacion_media", "rs_era5_media",
                   "sesgo_MJm2", "sesgo_pct", "rmse_MJm2", "correlacion_diaria"]].round(2).to_string())
    print(por_mes.pivot(index="mes", columns="estacion", values="sesgo_MJm2").round(2).to_string())
    for ruta in (SALIDA_DIARIA, SALIDA_POR_MES, SALIDA_RESUMEN, SALIDA_FIGURA):
        print(f"Listo: {ruta.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
