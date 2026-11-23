"""Fase 5 (punto 1): experimento de sensibilidad de todos los métodos.

Se perturban las entradas diarias de ERA5-Land de los 6 puntos y se recalculan todos los métodos con las mismas
funciones de los scripts 04 (ETo Penman–Monteith FAO-56), 21 (métodos) y 22 (Thornthwaite):

    t+1_ea, t+2_ea     Tmáx y Tmín +1 y +2 °C, ea constante (el déficit crece; el punto de rocío no cambia)
    t+1_hr, t+2_hr     Tmáx y Tmín +1 y +2 °C, humedad relativa constante: ea · es(T nueva)/es(T)
    u2+10              viento +10 %
    rs-10              Rs −10 %
    ea+10              ea +10 %

Decisiones (Juan, 2026-11-23):
    - Se calienta Tmáx y Tmín por igual: la amplitud diaria no cambia (Hargreaves solo cambia por T).
    - Rnl (FAO-56 ec. 39) se recalcula con la T, el ea y la Rs nuevos; Rns = 0.77·Rs; Rso no cambia. Así Rn responde
      a T, ea y Rs como en el script 03.
    - Thornthwaite conserva el I y el a del clima base (I fijo, decisión del 20 nov); solo cambia la T del mes.
    - Cenicafé solo depende de la altitud: no cambia en ningún caso.

Cambio % = 100 · (media del escenario / media base − 1), con los totales mensuales de la cuenca (Voronoi), por mes
calendario (media 1998–2022) y anual.

Escribe productos/punto1/sensibilidad.csv (escenario, método, mes 1–12 y «anual», base mm/mes, escenario mm/mes,
cambio %).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/28_sensibilidad.py
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_DIARIA = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"
ENTRADA_PUNTOS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"
SALIDA = CARPETA_PRODUCTOS / "sensibilidad.csv"
STEFAN_BOLTZMANN, KELVIN, ALBEDO = 4.903e-9, 273.15, 0.23   # los mismos del script 03


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, Path(__file__).with_name(archivo))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


eto_fao56 = cargar("eto_fao56", "04_eto_fao56.py")
metodos_et = cargar("metodos_et", "21_metodos_et.py")
thornthwaite = cargar("thornthwaite", "22_thornthwaite.py")
PESOS = eto_fao56.PESOS

NOMBRES = {
    "eto_fao56": "ETo Penman–Monteith (FAO-56)", "eto_fao56_rs0": "Penman–Monteith (FAO-56) con rs = 0",
    "thornthwaite": "Thornthwaite", "hargreaves": "Hargreaves", "priestley_taylor": "Priestley–Taylor",
    "makkink": "Makkink", "penman_fao24": "Penman (FAO-24, c = 0.8)", "aa_brutsaert_stricker": "AA (ET real)",
    "cenicafe_2006": "Cenicafé 2006",
}


def es_diaria(d):
    return (eto_fao56.presion_saturacion(d["tmax_C"]) + eto_fao56.presion_saturacion(d["tmin_C"])) / 2


def recalcular_rn(d):
    """Rns, Rnl y Rn con FAO-56 ec. 38–40, como el script 03 (Rso tal como viene)."""
    d = d.copy()
    d["rns_MJm2"] = (1 - ALBEDO) * d["rs_MJm2"]
    rs_sobre_rso = (d["rs_MJm2"] / d["rso_MJm2"]).clip(upper=1.0)
    t4 = ((d["tmax_C"] + KELVIN) ** 4 + (d["tmin_C"] + KELVIN) ** 4) / 2
    d["rnl_MJm2"] = STEFAN_BOLTZMANN * t4 * (0.34 - 0.14 * np.sqrt(d["ea_kPa"])) * (1.35 * rs_sobre_rso - 0.35)
    d["rn_MJm2"] = d["rns_MJm2"] - d["rnl_MJm2"]
    return d


def calentar(d, grados, hr_constante):
    nueva = d.copy()
    nueva["tmax_C"] += grados
    nueva["tmin_C"] += grados
    if hr_constante:
        nueva["ea_kPa"] = d["ea_kPa"] * es_diaria(nueva) / es_diaria(d)
    return nueva


def escenarios(base):
    return {
        "base": base,
        "t+1_ea": calentar(base, 1, False), "t+2_ea": calentar(base, 2, False),
        "t+1_hr": calentar(base, 1, True), "t+2_hr": calentar(base, 2, True),
        "u2+10": base.assign(viento10_ms=base["viento10_ms"] * 1.1),
        "rs-10": base.assign(rs_MJm2=base["rs_MJm2"] * 0.9),
        "ea+10": base.assign(ea_kPa=base["ea_kPa"] * 1.1),
    }


def todos_los_metodos(d, alturas, latitudes, indice, a):
    """Todos los métodos de la cuenca por mes (mm/mes, Voronoi)."""
    d = recalcular_rn(d)
    diarios = pd.concat([d[["fecha", "punto"]], metodos_et.metodos_diarios(d, alturas),
                         eto_fao56.eto_fao56(d)[["eto_mm"]].rename(columns={"eto_mm": "eto_fao56"})], axis=1)
    columnas = [c for c in diarios.columns if c not in ("fecha", "punto")]
    mensual = diarios.set_index("fecha").groupby("punto")[columnas].resample("MS").sum().reset_index()

    t_mes = thornthwaite.temperatura_mensual(d)
    t_mes["etp_sin_corregir_mm"] = thornthwaite.etp_sin_corregir(t_mes, indice, a)   # I y a del clima base
    luz = thornthwaite.correccion_luz_y_dias(d, latitudes)
    t_mes = t_mes.merge(luz, on=["punto", "fecha"], validate="one_to_one")
    t_mes["thornthwaite"] = t_mes["etp_sin_corregir_mm"] * t_mes["factor"]
    mensual = mensual.merge(t_mes[["punto", "fecha", "thornthwaite"]], on=["punto", "fecha"], validate="one_to_one")
    return metodos_et.promedio_cuenca(mensual, [*columnas, "thornthwaite"])


def main():
    base = pd.read_csv(ENTRADA_DIARIA, parse_dates=["fecha"])
    puntos = pd.read_csv(ENTRADA_PUNTOS).set_index("punto")
    alturas, latitudes = puntos["z_region_dem_m"].to_dict(), puntos["lat"].to_dict()

    # Rn recalculado sin perturbar debe ser el del script 03.
    error = (recalcular_rn(base)["rn_MJm2"] - base["rn_MJm2"]).abs().max()
    assert error < 1e-3, f"Rn recalculado no coincide con el script 03 (máx. {error:.5f})"

    _, indice = thornthwaite.indice_de_calor(thornthwaite.temperatura_mensual(base))
    a = thornthwaite.exponente(indice)

    resultados = {nombre: todos_los_metodos(d, alturas, latitudes, indice, a)
                  for nombre, d in escenarios(base).items()}
    referencia = resultados["base"]

    # La base debe reproducir los métodos y la ETo del script 21.
    guardado = pd.read_csv(CARPETA_PRODUCTOS / "metodos_mensual.csv")
    guardado.index = pd.to_datetime(guardado["mes"])
    for col in NOMBRES:
        dif = (referencia[col].values - guardado[f"{col}_mm_mes"].values).__abs__().max()
        assert dif < 0.01, f"{col}: la base no reproduce el script 21 (máx. {dif:.4f} mm/mes)"

    base_ciclo = referencia.groupby(referencia.index.month).mean()
    filas = []
    for nombre, mensual in resultados.items():
        if nombre == "base":
            continue
        ciclo = mensual.groupby(mensual.index.month).mean()
        for col in NOMBRES:
            for mes in range(1, 13):
                filas.append({"escenario": nombre, "metodo": NOMBRES[col], "mes": str(mes),
                              "base_mm_mes": base_ciclo.loc[mes, col], "escenario_mm_mes": ciclo.loc[mes, col]})
            filas.append({"escenario": nombre, "metodo": NOMBRES[col], "mes": "anual",
                          "base_mm_mes": referencia[col].mean(), "escenario_mm_mes": mensual[col].mean()})
    salida = pd.DataFrame(filas)
    salida["cambio_pct"] = 100 * (salida["escenario_mm_mes"] / salida["base_mm_mes"] - 1)
    salida.round(4).to_csv(SALIDA, index=False)
    print(f"Listo: {SALIDA}")

    anual = salida[salida["mes"] == "anual"].pivot(index="metodo", columns="escenario", values="cambio_pct")
    orden = ["t+1_ea", "t+2_ea", "t+1_hr", "t+2_hr", "u2+10", "rs-10", "ea+10"]
    print("\nCambio anual (%):")
    print(anual[orden].reindex(list(NOMBRES.values())).round(2).to_string())


if __name__ == "__main__":
    main()
