"""ETo FAO-56 calculada con datos de 3 estaciones del IDEAM, comparada con la ETo de ERA5-Land (punto 1, fase 3).

Prueba de estaciones del plan: recalcular la ETo completa con datos medidos y compararla con la de los scripts 01–04
en el punto de ERA5-Land más cercano (el mismo que usa 12_rs_brillo_solar_vs_era5land.py).

Lee:
    datos/punto1/ideam_estaciones/dhime_t_hr_parte1_1998_2022.zip              Tmax, Tmin y HR máxima diarias (DHIME)
    datos/punto1/ideam_estaciones/dhime_hr_viento_tanque_parte2_1998_2022.zip  HR mínima diaria y viento de Mogotes-AUT
    datos/punto1/ideam/cne_ideam.csv                                           altura y latitud de cada estación
    productos/punto1/rs_estaciones_diaria.csv     Rs de Angstrom por estación y día (salida de 12)
    productos/punto1/era5land_diario_puntos.csv   entradas diarias de ERA5-Land (salida de 03)
    productos/punto1/eto_diaria_puntos.csv        ETo diaria de ERA5-Land (salida de 04)

Escribe en productos/punto1/:
    eto_estaciones_diaria.csv                   ETo de estación por día, sus entradas y las de ERA5-Land del mismo día
    eto_estaciones_vs_era5land_por_mes.csv      medias, sesgo y RMSE por estación, variante de viento y mes calendario
    eto_estaciones_vs_era5land_resumen.csv      lo mismo con todos los días, y la media de cada entrada en los dos
    eto_estaciones_vs_era5land_ciclo_anual.png  ciclo anual de la ETo en cada estación

Estaciones: Escuela Agrícola Mogotes (24025040), La Sierra (24025030) y Charalá (24025050), las tres del brillo solar.
Andalucía (24035350) no entra: queda fuera de la cuenca y no tiene brillo solar.

Cálculo, FAO-56 (Allen et al., 1998), igual que 03 y 04 salvo de dónde sale cada entrada:
    Tmax, Tmin   medidas en la estación
    ea           ec. 17, con HR máxima y mínima: ea = [e°(Tmin) HRmax/100 + e°(Tmax) HRmin/100] / 2
    Rs           Angstrom con el brillo solar (script 12)
    Rso          ec. 37 con la altura de la estación
    Rn           ec. 38 a 40, α = 0.23 (como en 03)
    P            ec. 7 con la altura de la estación; γ con la ec. 8
    G            0 (ec. 42)
    u2           no hay viento medido en La Sierra ni en Charalá, y en Mogotes solo Mogotes-AUT (24025090, mismas
                 coordenadas que 24025040) desde 2005, con media de 0.99 m/s. Dos variantes:
                   «mogotes_aut» (VARIANTE FINAL, decisión del 2026-11-17 en el registro de decisiones): el promedio de
                     Mogotes-AUT por mes calendario, el mismo en las tres estaciones, medido a 10 m y llevado a 2 m con
                     la ec. 47. La altura de 10 m sale del Manual del Observador Meteorológico del IDEAM (GDI-M003,
                     versión 03), según el cual los sensores de viento en Colombia están a 10 m.
                   «2ms»: u2 = 2 m/s, el valor que FAO-56 propone cuando no hay datos de viento (cap. 3). Se conserva
                     solo como sensibilidad al viento.

Control de calidad (se descartan los días, no se rellena; se cuenta cuántos):
    Tmin ≥ Tmax; HRmin > HRmax; HR fuera de 0–100 %.
    Solo se calcula la ETo en días con Tmax, Tmin, HRmax, HRmin y brillo solar.

Sesgo = media de (ETo ERA5-Land − ETo estación); positivo es ERA5-Land por encima. Mismos días en los dos.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/13_eto_estaciones_vs_era5land.py
"""

import zipfile
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (va después de fijar el backend sin pantalla)

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DHIME = RAIZ_ENTREGA / "datos" / "punto1" / "ideam_estaciones"
ZIPS_DHIME = ["dhime_t_hr_parte1_1998_2022.zip", "dhime_hr_viento_tanque_parte2_1998_2022.zip"]
CATALOGO_IDEAM = RAIZ_ENTREGA / "datos" / "punto1" / "ideam" / "cne_ideam.csv"
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
RS_ESTACIONES = CARPETA_PRODUCTOS / "rs_estaciones_diaria.csv"
DIARIO_ERA5 = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"
ETO_ERA5 = CARPETA_PRODUCTOS / "eto_diaria_puntos.csv"

SALIDA_DIARIA = CARPETA_PRODUCTOS / "eto_estaciones_diaria.csv"
SALIDA_POR_MES = CARPETA_PRODUCTOS / "eto_estaciones_vs_era5land_por_mes.csv"
SALIDA_RESUMEN = CARPETA_PRODUCTOS / "eto_estaciones_vs_era5land_resumen.csv"
SALIDA_FIGURA = CARPETA_PRODUCTOS / "eto_estaciones_vs_era5land_ciclo_anual.png"

ESTACIONES = ["24025040", "24025030", "24025050"]   # Escuela Agrícola Mogotes, La Sierra, Charalá
ESTACION_VIENTO = "24025090"                         # Mogotes-AUT
INICIO, FIN = "1998-01-01", "2022-12-31"

PARAMETROS = {
    "Temperatura máxima diaria": "tmax_C",
    "Temperatura mínima diaria": "tmin_C",
    "Húmeda relativa calculada máxima diaria": "hrmax_pct",
    "Húmeda relativa calculada mínima diaria": "hrmin_pct",
}
PARAMETRO_VIENTO = "Velocidad 10 minutal del viento media diaria"

ALTURA_ANEMOMETRO_M = 10.0            # IDEAM, Manual del Observador Meteorológico (GDI-M003, v. 03)
U2_SIN_DATOS = 2.0                    # m/s, FAO-56 cap. 3, cuando no hay datos de viento
ALBEDO_REFERENCIA = 0.23
STEFAN_BOLTZMANN = 4.903e-9           # MJ/K⁴·m²·día
KELVIN = 273.15


def presion_saturacion(t_c):
    """e°(T) en kPa, FAO-56 ec. 11."""
    return 0.6108 * np.exp(17.27 * t_c / (t_c + 237.3))


def pendiente_saturacion(t_c):
    """Δ en kPa/°C, FAO-56 ec. 13."""
    return 4098 * presion_saturacion(t_c) / (t_c + 237.3) ** 2


def presion_por_altura(z_m):
    """P en kPa, FAO-56 ec. 7."""
    return 101.3 * ((293 - 0.0065 * z_m) / 293) ** 5.26


def viento_a_2m(u_z, z):
    """u2 en m/s, FAO-56 ec. 47 (perfil logarítmico sobre pasto)."""
    return u_z * 4.87 / np.log(67.8 * z - 5.42)


def leer_dhime():
    """Todas las series diarias de los dos ZIP de DHIME, en formato largo."""
    partes = []
    for nombre in ZIPS_DHIME:
        with zipfile.ZipFile(CARPETA_DHIME / nombre) as archivo:
            with archivo.open("descargaDhime.csv") as csv:
                partes.append(pd.read_csv(csv, dtype={"CodigoEstacion": str}))
    datos = pd.concat(partes, ignore_index=True)
    datos["fecha"] = pd.to_datetime(datos["Fecha"].str[:10])
    assert not datos.duplicated(["CodigoEstacion", "Parametro", "fecha"]).any()
    return datos


def u2_mensual_mogotes_aut(dhime):
    """u2 media por mes calendario de Mogotes-AUT, llevada de 10 m a 2 m con la ec. 47."""
    viento = dhime[(dhime["CodigoEstacion"] == ESTACION_VIENTO) & (dhime["Parametro"] == PARAMETRO_VIENTO)]
    viento = viento.set_index("fecha")["Valor"].loc[INICIO:FIN]
    por_mes = viento.groupby(viento.index.month).mean()
    assert len(por_mes) == 12
    return viento_a_2m(por_mes, ALTURA_ANEMOMETRO_M), len(viento)


def eto_fao56(tmax, tmin, ea, rn, presion, u2):
    """ETo diaria (mm/día), FAO-56 ec. 6 con G = 0, como en 04_eto_fao56.py."""
    t = (tmax + tmin) / 2                                                       # ec. 9
    delta = pendiente_saturacion(t)                                             # ec. 13
    es = (presion_saturacion(tmax) + presion_saturacion(tmin)) / 2              # ec. 12
    gamma = 0.665e-3 * presion                                                  # ec. 8
    deficit = (es - ea).clip(lower=0)
    return ((0.408 * delta * rn + gamma * 900 / (t + 273) * u2 * deficit)
            / (delta + gamma * (1 + 0.34 * u2)))


def main():
    catalogo = pd.read_csv(CATALOGO_IDEAM, dtype=str)
    catalogo["estacion"] = catalogo["codigo"].str.lstrip("0")
    catalogo = catalogo.set_index("estacion")
    dhime = leer_dhime()
    u2_mogotes, dias_viento = u2_mensual_mogotes_aut(dhime)
    rs = pd.read_csv(RS_ESTACIONES, dtype={"estacion": str}, parse_dates=["fecha"])
    era5 = pd.read_csv(DIARIO_ERA5, parse_dates=["fecha"]).set_index(["punto", "fecha"])
    eto_era5 = pd.read_csv(ETO_ERA5, parse_dates=["fecha"]).set_index(["punto", "fecha"])

    diarias, conteos = [], []
    for codigo in ESTACIONES:
        z = float(catalogo.loc[codigo, "altitud"])
        medidas = (dhime[(dhime["CodigoEstacion"] == codigo) & dhime["Parametro"].isin(PARAMETROS)]
                   .pivot(index="fecha", columns="Parametro", values="Valor").rename(columns=PARAMETROS)
                   .loc[INICIO:FIN])
        rs_est = rs[rs["estacion"] == codigo].set_index("fecha")
        tabla = medidas.join(rs_est[["punto_era5", "ra_MJm2", "rs_estacion_MJm2"]], how="inner").dropna()
        dias_completos = len(tabla)
        malos = ((tabla["tmin_C"] >= tabla["tmax_C"]) | (tabla["hrmin_pct"] > tabla["hrmax_pct"])
                 | (tabla[["hrmax_pct", "hrmin_pct"]] < 0).any(axis=1)
                 | (tabla[["hrmax_pct", "hrmin_pct"]] > 100).any(axis=1))
        tabla = tabla[~malos].copy()
        conteos.append({"estacion": codigo, "z_estacion_m": z, "dias_con_todas_las_entradas": dias_completos,
                        "dias_descartados_control_calidad": int(malos.sum()), "dias_usados": len(tabla),
                        "dias_viento_mogotes_aut": dias_viento})

        # Entradas de estación, FAO-56
        tabla["ea_kPa"] = (presion_saturacion(tabla["tmin_C"]) * tabla["hrmax_pct"] / 100       # ec. 17
                           + presion_saturacion(tabla["tmax_C"]) * tabla["hrmin_pct"] / 100) / 2
        rso = (0.75 + 2e-5 * z) * tabla["ra_MJm2"]                                               # ec. 37
        rs_sobre_rso = (tabla["rs_estacion_MJm2"] / rso).clip(upper=1.0)
        t4 = ((tabla["tmax_C"] + KELVIN) ** 4 + (tabla["tmin_C"] + KELVIN) ** 4) / 2
        rnl = (STEFAN_BOLTZMANN * t4 * (0.34 - 0.14 * np.sqrt(tabla["ea_kPa"]))                  # ec. 39
               * (1.35 * rs_sobre_rso - 0.35))
        tabla["rn_MJm2"] = (1 - ALBEDO_REFERENCIA) * tabla["rs_estacion_MJm2"] - rnl              # ec. 38 y 40
        presion = presion_por_altura(z)                                                           # ec. 7
        u2_variantes = {"mogotes_aut": tabla.index.month.map(u2_mogotes).to_numpy(), "2ms": U2_SIN_DATOS}
        for nombre, u2 in u2_variantes.items():
            tabla[f"u2_{nombre}_ms"] = u2
            tabla[f"eto_{nombre}_mm"] = eto_fao56(tabla["tmax_C"], tabla["tmin_C"], tabla["ea_kPa"],
                                                  tabla["rn_MJm2"], presion, tabla[f"u2_{nombre}_ms"])

        # Lo mismo de ERA5-Land, en el punto más cercano y los mismos días
        punto = int(tabla["punto_era5"].iloc[0])
        claves = pd.MultiIndex.from_arrays([np.full(len(tabla), punto), tabla.index])
        tabla["tmax_era5_C"] = era5.loc[claves, "tmax_C"].to_numpy()
        tabla["tmin_era5_C"] = era5.loc[claves, "tmin_C"].to_numpy()
        tabla["ea_era5_kPa"] = era5.loc[claves, "ea_kPa"].to_numpy()
        tabla["rs_era5_MJm2"] = era5.loc[claves, "rs_MJm2"].to_numpy()
        tabla["rn_era5_MJm2"] = era5.loc[claves, "rn_MJm2"].to_numpy()
        tabla["u2_era5_ms"] = eto_era5.loc[claves, "u2_ms"].to_numpy()
        tabla["eto_era5_mm"] = eto_era5.loc[claves, "eto_mm"].to_numpy()
        tabla.insert(0, "estacion", codigo)
        diarias.append(tabla)

    diaria = pd.concat(diarias)
    diaria.index.name = "fecha"
    assert diaria.notna().all().all()
    assert (diaria[["eto_mogotes_aut_mm", "eto_2ms_mm"]] > 0).all().all()

    # Tabla larga: una fila por estación, variante de viento y día
    largas = []
    for nombre in ["mogotes_aut", "2ms"]:
        parte = diaria[["estacion", "eto_era5_mm"]].copy()
        parte["variante_viento"] = nombre
        parte["eto_estacion_mm"] = diaria[f"eto_{nombre}_mm"]
        largas.append(parte)
    larga = pd.concat(largas)
    larga["mes"] = larga.index.month

    def metricas(grupo):
        diferencia = grupo["eto_era5_mm"] - grupo["eto_estacion_mm"]
        return pd.Series({
            "dias": len(grupo),
            "eto_estacion_media_mm_dia": grupo["eto_estacion_mm"].mean(),
            "eto_era5_media_mm_dia": grupo["eto_era5_mm"].mean(),
            "sesgo_mm_dia": diferencia.mean(),
            "sesgo_pct": 100 * diferencia.mean() / grupo["eto_estacion_mm"].mean(),
            "rmse_mm_dia": np.sqrt((diferencia ** 2).mean()),
            "correlacion_diaria": grupo["eto_era5_mm"].corr(grupo["eto_estacion_mm"]),
        })

    por_mes = larga.groupby(["estacion", "variante_viento", "mes"]).apply(metricas, include_groups=False)
    resumen = larga.groupby(["estacion", "variante_viento"]).apply(metricas, include_groups=False)

    # Media de cada entrada en la estación y en ERA5-Land, mismos días
    entradas = diaria.groupby("estacion")[[
        "tmax_C", "tmax_era5_C", "tmin_C", "tmin_era5_C", "ea_kPa", "ea_era5_kPa",
        "rs_estacion_MJm2", "rs_era5_MJm2", "rn_MJm2", "rn_era5_MJm2",
        "u2_mogotes_aut_ms", "u2_era5_ms"]].mean().add_prefix("media_")
    resumen = (resumen.reset_index().merge(pd.DataFrame(conteos), on="estacion")
               .merge(entradas.reset_index(), on="estacion"))
    resumen.insert(1, "punto_era5", resumen["estacion"].map(diaria.groupby("estacion")["punto_era5"].first()))

    salida_diaria = diaria.copy()
    salida_diaria.index = salida_diaria.index.strftime("%Y-%m-%d")
    salida_diaria.round(4).to_csv(SALIDA_DIARIA)
    por_mes.round(3).to_csv(SALIDA_POR_MES)
    resumen.round(3).to_csv(SALIDA_RESUMEN, index=False)

    # Figura: ciclo anual de la ETo (media por mes calendario de los días usados)
    nombres_mes = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    figura, ejes = plt.subplots(1, 3, figsize=(12, 4.3), sharey=True)
    for eje, codigo in zip(ejes, ESTACIONES):
        datos = por_mes.loc[codigo]
        punto = int(diaria.loc[diaria["estacion"] == codigo, "punto_era5"].iloc[0])
        eje.plot(range(1, 13), datos.loc["mogotes_aut", "eto_estacion_media_mm_dia"], "o-", color="#1f6f8b",
                 label="Estación, viento Mogotes-AUT a 10 m (final)")
        eje.plot(range(1, 13), datos.loc["2ms", "eto_estacion_media_mm_dia"], "^:", color="#5a9e6f",
                 label="Estación, u2 = 2 m/s (sensibilidad)")
        eje.plot(range(1, 13), datos.loc["mogotes_aut", "eto_era5_media_mm_dia"], "s--", color="#c8553d",
                 label=f"ERA5-Land (punto {punto})")
        nombre = catalogo.loc[codigo, "nombre"].split(" [")[0].title()
        eje.set_title(f"{nombre} ({int(float(catalogo.loc[codigo, 'altitud']))} m)", fontsize=10)
        eje.set_xticks(range(1, 13), nombres_mes)
        eje.grid(alpha=0.3)
    ejes[0].set_ylabel("ETo media (mm/día)")
    manijas, etiquetas = ejes[0].get_legend_handles_labels()
    etiquetas[-1] = "ERA5-Land (punto más cercano)"
    figura.legend(manijas, etiquetas, loc="lower center", ncol=3, frameon=False, fontsize=9)
    figura.suptitle("Ciclo anual de la ETo FAO-56, 1998–2022 (solo días con todas las entradas de estación)",
                    fontsize=11)
    figura.tight_layout(rect=(0, 0.07, 1, 1))
    figura.savefig(SALIDA_FIGURA, dpi=150)

    pd.set_option("display.width", 250)
    print(resumen.round(2).T.to_string())
    print(por_mes["sesgo_mm_dia"].unstack("mes").round(2).to_string())
    print("u2 de Mogotes-AUT por mes (m/s):", u2_mogotes.round(2).to_dict())
    for ruta in (SALIDA_DIARIA, SALIDA_POR_MES, SALIDA_RESUMEN, SALIDA_FIGURA):
        print(f"Listo: {ruta.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
