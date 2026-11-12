"""Series diarias de ERA5-Land y radiación neta Rn (FAO-56) en los 6 puntos de la cuenca del Fonce, 1998–2022.

Lee las series horarias de datos/punto1/era5land_puntos/punto_N.csv y escribe:
    productos/punto1/era5land_diario_puntos.csv   una fila por punto y día (hora local), con Rn
    productos/punto1/rn_mensual_puntos.csv        Rn acumulada por punto y mes (MJ/m²·mes)

Días en hora local de Colombia (UTC−5), como en 02_series_mensuales_era5land.py (temp/decisiones.md).

Radiación neta, FAO-56 (Allen et al., 1998), en MJ/m²·día:
    Ra   radiación extraterrestre, ec. 21, con dr (ec. 23), δ (ec. 24) y ωs (ec. 25)
    Rso  radiación de cielo despejado, ec. 37: Rso = (0.75 + 2·10⁻⁵ z) Ra
    Rns  onda corta neta, ec. 38: Rns = (1 − α) Rs, con α = 0.23 (pasto de referencia)
    Rnl  onda larga neta, ec. 39: Rnl = σ [(Tmax,K⁴ + Tmin,K⁴)/2] (0.34 − 0.14 √ea) (1.35 Rs/Rso − 0.35)
    Rn   = Rns − Rnl (ec. 40)

De dónde sale cada entrada:
    Rs     suma de las 24 horas de ssrd del día (J/m² → MJ/m²)
    Tmax, Tmin  máxima y mínima de las 24 temperaturas horarias t2m del día
    ea     promedio diario de la presión de saturación al punto de rocío horario, e°(Td) (ec. 14 con ec. 11)
    z      altura de la superficie del modelo en cada punto, despejada de la presión media sp con la ec. 7, para que
           Rso corresponda a la misma superficie que Rs y T (la ec. 37 es poco sensible a z: 1 000 m cambian Rso un 2.7 %)
    latitud  la de la celda entregada por el CDS

Rs/Rso se limita a 1 (FAO-56, nota de la ec. 39). El 2022-12-31 tiene 19 horas (le faltan 19:00–23:00 local):
su Rs está completa porque esas horas son de noche, pero su Tmin sale de 19 horas.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/03_series_diarias_rn.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"
SALIDA_DIARIA = RAIZ_ENTREGA / "productos" / "punto1" / "era5land_diario_puntos.csv"
SALIDA_RN_MENSUAL = RAIZ_ENTREGA / "productos" / "punto1" / "rn_mensual_puntos.csv"

PUNTOS = [1, 2, 3, 4, 5, 6]
DESFASE_HORA_LOCAL = pd.Timedelta(hours=-5)  # Colombia, UTC−5, sin horario de verano
INICIO_LOCAL = pd.Timestamp("1998-01-01 00:00")
FIN_LOCAL = pd.Timestamp("2022-12-31 23:00")
KELVIN = 273.15

# Constantes de FAO-56
CONSTANTE_SOLAR = 0.0820           # Gsc, MJ/m²·min
STEFAN_BOLTZMANN = 4.903e-9        # σ, MJ/K⁴·m²·día
ALBEDO_REFERENCIA = 0.23           # α del pasto de referencia


def presion_saturacion(t_c):
    """e°(T) en kPa, FAO-56 ec. 11."""
    return 0.6108 * np.exp(17.27 * t_c / (t_c + 237.3))


def altura_desde_presion(p_kpa):
    """Despeja z (m) de la ec. 7 de FAO-56: P = 101.3 [(293 − 0.0065 z)/293]^5.26."""
    return (293.0 - 293.0 * (p_kpa / 101.3) ** (1 / 5.26)) / 0.0065


def radiacion_extraterrestre(latitud_grados, dia_del_anio):
    """Ra en MJ/m²·día, FAO-56 ec. 21, 23, 24 y 25."""
    phi = np.radians(latitud_grados)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * dia_del_anio)                  # ec. 23
    delta = 0.409 * np.sin(2 * np.pi / 365 * dia_del_anio - 1.39)            # ec. 24
    omega_s = np.arccos(-np.tan(phi) * np.tan(delta))                        # ec. 25
    return (24 * 60 / np.pi) * CONSTANTE_SOLAR * dr * (                      # ec. 21
        omega_s * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(omega_s))


def leer_horaria_local(n):
    """Serie horaria de un punto en hora local (°C, kPa, m/s, J/m²) y la latitud de su celda."""
    horaria = pd.read_csv(CARPETA_DATOS / f"punto_{n}.csv", parse_dates=["valid_time"])
    latitud = float(horaria["latitude"].iloc[0])
    horaria["hora_local"] = horaria["valid_time"] + DESFASE_HORA_LOCAL
    horaria = horaria[(horaria["hora_local"] >= INICIO_LOCAL) & (horaria["hora_local"] <= FIN_LOCAL)]
    tabla = pd.DataFrame({
        "hora_local": horaria["hora_local"],
        "t2m_C": horaria["t2m"] - KELVIN,
        "ea_kPa": presion_saturacion(horaria["d2m"] - KELVIN),
        "sp_kPa": horaria["sp"] / 1000.0,
        "viento10_ms": np.hypot(horaria["u10"], horaria["v10"]),
        "ssrd_Jm2": horaria["ssrd"],
    }).set_index("hora_local").sort_index()
    return tabla, latitud


def diaria_de_un_punto(horaria, latitud):
    """Agrega a días locales y calcula Ra, Rso, Rns, Rnl y Rn."""
    por_dia = horaria.resample("D")
    diaria = pd.DataFrame({
        "horas": por_dia["t2m_C"].count(),
        "tmax_C": por_dia["t2m_C"].max(),
        "tmin_C": por_dia["t2m_C"].min(),
        "tmedia_C": por_dia["t2m_C"].mean(),
        "ea_kPa": por_dia["ea_kPa"].mean(),
        "sp_kPa": por_dia["sp_kPa"].mean(),
        "viento10_ms": por_dia["viento10_ms"].mean(),
        "rs_MJm2": por_dia["ssrd_Jm2"].sum() / 1e6,
    })

    z_modelo = altura_desde_presion(horaria["sp_kPa"].mean())
    diaria["ra_MJm2"] = radiacion_extraterrestre(latitud, diaria.index.day_of_year.to_numpy())
    diaria["rso_MJm2"] = (0.75 + 2e-5 * z_modelo) * diaria["ra_MJm2"]                       # ec. 37
    diaria["rns_MJm2"] = (1 - ALBEDO_REFERENCIA) * diaria["rs_MJm2"]                          # ec. 38
    rs_sobre_rso = (diaria["rs_MJm2"] / diaria["rso_MJm2"]).clip(upper=1.0)
    t4 = ((diaria["tmax_C"] + KELVIN) ** 4 + (diaria["tmin_C"] + KELVIN) ** 4) / 2
    diaria["rnl_MJm2"] = (STEFAN_BOLTZMANN * t4 * (0.34 - 0.14 * np.sqrt(diaria["ea_kPa"]))   # ec. 39
                          * (1.35 * rs_sobre_rso - 0.35))
    diaria["rn_MJm2"] = diaria["rns_MJm2"] - diaria["rnl_MJm2"]                               # ec. 40
    return diaria, z_modelo


def main():
    diarias, mensuales = [], []
    for n in PUNTOS:
        horaria, latitud = leer_horaria_local(n)
        diaria, z_modelo = diaria_de_un_punto(horaria, latitud)
        print(f"Punto {n}: latitud {latitud:.1f}°, altura del modelo despejada de sp ≈ {z_modelo:.0f} m")
        diaria.insert(0, "punto", n)
        diarias.append(diaria)
        rn_mes = diaria["rn_MJm2"].resample("MS").sum().to_frame("rn_MJm2_mes")
        rn_mes.insert(0, "punto", n)
        mensuales.append(rn_mes)

    diaria = pd.concat(diarias)
    diaria.index = diaria.index.strftime("%Y-%m-%d")
    diaria.index.name = "fecha"

    # Comprobaciones: 9 131 días por punto, todos con 24 horas salvo el último; Rs nunca mayor que Ra.
    assert (diaria.groupby("punto").size() == 9131).all()
    incompletos = diaria[diaria["horas"] != 24]
    assert set(incompletos.index) == {"2022-12-31"} and (incompletos["horas"] == 19).all()
    assert (diaria["rs_MJm2"] <= diaria["ra_MJm2"]).all()
    assert diaria.notna().all().all()

    SALIDA_DIARIA.parent.mkdir(parents=True, exist_ok=True)
    diaria.round(4).to_csv(SALIDA_DIARIA)
    print(f"Listo: {SALIDA_DIARIA} ({len(diaria)} filas)")

    rn_mensual = pd.concat(mensuales)
    rn_mensual.index = rn_mensual.index.strftime("%Y-%m")
    rn_mensual.index.name = "mes"
    rn_mensual.round(3).to_csv(SALIDA_RN_MENSUAL)
    print(f"Listo: {SALIDA_RN_MENSUAL} ({len(rn_mensual)} filas)")


if __name__ == "__main__":
    main()
