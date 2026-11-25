"""Fase 8 con todo el registro (punto 1): tendencias de la demanda, 1981–2022.

Pedido de Juan (24 nov): bajar ERA5-Land desde 1981 y repetir la fase 8 para ver si cambia la conclusión.
Las demás fases siguen en 1998–2022; por eso este script no toca ningún producto de 1998–2022.

Pasos, con las mismas funciones de los scripts 03, 04, 22 y 32 (se importan, no se copian):
1. 1981–1997: horas de punto_N_1981_1997.csv (más las 5 primeras horas UTC de punto_N.csv, que son las últimas 5
   horas locales de 1997), días en hora local (UTC−5), Rn de FAO-56 con la altura del modelo de 1998–2022 (la misma
   Rso de siempre), ETo diaria (ec. 6) y mensual (suma), promedio de la cuenca con Voronoi.
2. 1998–2022: los diarios de era5land_diario_puntos.csv, sin cambios.
3. Thornthwaite con el MISMO índice de calor I (climatología 1998–2022, script 22), para que 1998–2022 no cambie.
4. Forzantes (T, ea, u2, Rs) igual que el script 32.
5. Tendencias con los métodos de la Tarea 1 (script 32) sobre 1981–2022 (504 meses). La atribución usa las
   sensibilidades del script 28 (calculadas con 1998–2022).
Comprobación: con 1998–2022 el mismo camino reproduce eto_mensual_cuenca.csv, el Thornthwaite de metodos_mensual.csv
y tendencias_demanda.csv.

Escribe productos/punto1/demanda_mensual_cuenca_1981_2022.csv, tendencias_demanda_1981_2022.csv,
atribucion_eto_1981_2022.csv y tendencias_demanda_1981_2022.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/35_tendencias_demanda_1981_2022.py
"""

import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
# Variable de entorno solo para probar el script con archivos de prueba fuera del repo.
CARPETA_DATOS = Path(os.environ.get("CARPETA_ERA5LAND_PUNTOS", RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"))
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_PUNTOS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"
SALIDA_MENSUAL = CARPETA_PRODUCTOS / "demanda_mensual_cuenca_1981_2022.csv"
SALIDA_TENDENCIAS = CARPETA_PRODUCTOS / "tendencias_demanda_1981_2022.csv"
SALIDA_ATRIBUCION = CARPETA_PRODUCTOS / "atribucion_eto_1981_2022.csv"
SALIDA_FIGURA = CARPETA_PRODUCTOS / "tendencias_demanda_1981_2022.png"

INICIO_LOCAL = pd.Timestamp("1981-01-01 00:00")
FIN_LOCAL_EXTENSION = pd.Timestamp("1997-12-31 23:00")


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, Path(__file__).with_name(archivo))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


rn03 = cargar("series_diarias_rn", "03_series_diarias_rn.py")
eto04 = cargar("eto_fao56", "04_eto_fao56.py")
th22 = cargar("thornthwaite", "22_thornthwaite.py")
tend32 = cargar("tendencias_demanda", "32_tendencias_demanda.py")
PUNTOS = rn03.PUNTOS
PESOS = eto04.PESOS


def diaria_extension(n):
    """Días locales 1981-01-01 a 1997-12-31 de un punto, con Rn de FAO-56 (script 03)."""
    partes = [pd.read_csv(CARPETA_DATOS / f"punto_{n}_1981_1997.csv", parse_dates=["valid_time"]),
              pd.read_csv(CARPETA_DATOS / f"punto_{n}.csv", parse_dates=["valid_time"], nrows=24)]
    horaria = pd.concat(partes).drop_duplicates("valid_time").sort_values("valid_time")
    assert horaria["valid_time"].diff().dropna().eq(pd.Timedelta(hours=1)).all(), f"punto {n}: horas faltantes"
    latitud = float(horaria["latitude"].iloc[0])
    horaria["hora_local"] = horaria["valid_time"] + rn03.DESFASE_HORA_LOCAL
    horaria = horaria[(horaria["hora_local"] >= INICIO_LOCAL) & (horaria["hora_local"] <= FIN_LOCAL_EXTENSION)]
    tabla = pd.DataFrame({
        "hora_local": horaria["hora_local"],
        "t2m_C": horaria["t2m"] - rn03.KELVIN,
        "ea_kPa": rn03.presion_saturacion(horaria["d2m"] - rn03.KELVIN),
        "sp_kPa": horaria["sp"] / 1000.0,
        "viento10_ms": np.hypot(horaria["u10"], horaria["v10"]),
        "ssrd_Jm2": horaria["ssrd"],
    }).set_index("hora_local").sort_index()
    # Rso con la altura del modelo de 1998–2022 (la del script 03), para que la ec. 37 sea la misma en todo el registro
    horaria_9822, _ = rn03.leer_horaria_local(n)
    z_ref = rn03.altura_desde_presion(horaria_9822["sp_kPa"].mean())
    original = rn03.altura_desde_presion
    rn03.altura_desde_presion = lambda p: z_ref
    try:
        diaria, _ = rn03.diaria_de_un_punto(tabla, latitud)
    finally:
        rn03.altura_desde_presion = original
    assert (diaria["horas"] == 24).all() and diaria.notna().all().all()
    assert (diaria["rs_MJm2"] <= diaria["ra_MJm2"]).all()
    diaria.insert(0, "punto", n)
    return diaria


def diaria_completa():
    """Diarios por punto 1981–2022: extensión nueva + era5land_diario_puntos.csv (1998–2022, sin cambios)."""
    extension = pd.concat([diaria_extension(n) for n in PUNTOS])
    extension.index.name = "fecha"
    extension = extension.reset_index()
    actual = pd.read_csv(CARPETA_PRODUCTOS / "era5land_diario_puntos.csv", parse_dates=["fecha"])
    diaria = pd.concat([extension[actual.columns], actual], ignore_index=True).sort_values(["punto", "fecha"])
    assert (diaria.groupby("punto").size() == (pd.Timestamp("2022-12-31") - INICIO_LOCAL).days + 1).all()
    return diaria.reset_index(drop=True)


def promedio_cuenca(mensual, columnas):
    peso = mensual["punto"].map(PESOS)
    suma = mensual[columnas].mul(peso, axis=0).groupby(mensual["fecha"]).sum()
    return suma.div(peso.groupby(mensual["fecha"]).sum(), axis=0)


def demanda_mensual(diaria):
    """ETo (FAO-56), Thornthwaite (I de 1998–2022) y forzantes, promedio mensual de la cuenca."""
    eto = pd.concat([diaria[["fecha", "punto"]], eto04.eto_fao56(diaria)], axis=1)
    eto_mes = eto.set_index("fecha").groupby("punto")["eto_mm"].resample("MS").sum().reset_index()
    cuenca = promedio_cuenca(eto_mes, ["eto_mm"]).rename(columns={"eto_mm": "eto"})

    latitudes = pd.read_csv(ENTRADA_PUNTOS).set_index("punto")["lat"].to_dict()
    # T del mes = media de (Tmáx + Tmín)/2, como th22.temperatura_mensual (que exige 300 meses)
    t_mes = (diaria.assign(t_C=(diaria["tmax_C"] + diaria["tmin_C"]) / 2).set_index("fecha")
             .groupby("punto")["t_C"].resample("MS").mean().reset_index())
    actual = pd.read_csv(CARPETA_PRODUCTOS / "era5land_diario_puntos.csv", parse_dates=["fecha"])
    _, indice = th22.indice_de_calor(th22.temperatura_mensual(actual))      # I fijo: climatología 1998–2022
    a = th22.exponente(indice)
    t_mes["etp_sin_corregir_mm"] = th22.etp_sin_corregir(t_mes, indice, a)
    luz = th22.correccion_luz_y_dias(diaria, latitudes)
    t_mes = t_mes.merge(luz, on=["punto", "fecha"], validate="one_to_one")
    t_mes["thornthwaite"] = t_mes["etp_sin_corregir_mm"] * t_mes["factor"]
    cuenca["thornthwaite"] = promedio_cuenca(t_mes, ["thornthwaite"])["thornthwaite"]

    cuenca.index = cuenca.index.to_period("M")
    tabla = cuenca.join(forzantes(diaria))
    assert tabla.notna().all().all()
    return tabla


def forzantes(diaria):
    """Igual que tend32.forzantes_mensuales, pero con la tabla diaria que se le pase."""
    d = diaria.copy()
    d["t"] = (d["tmax_C"] + d["tmin_C"]) / 2
    d["ea"] = d["ea_kPa"]
    d["u2"] = d["viento10_ms"] * 4.87 / np.log(67.8 * 10 - 5.42)
    d["rs"] = d["rs_MJm2"]
    d["mes"] = d["fecha"].dt.to_period("M")
    mensual = d.groupby(["mes", "punto"])[["t", "ea", "u2", "rs"]].mean().reset_index()
    peso = mensual["punto"].map(PESOS)
    cuenca = mensual[["t", "ea", "u2", "rs"]].mul(peso, axis=0).groupby(mensual["mes"]).sum()
    return cuenca.div(peso.groupby(mensual["mes"]).sum(), axis=0)


def comprobar_1998_2022(tabla):
    """Con 1998–2022 este camino debe reproducir los productos y las tendencias de la fase 8."""
    sub = tabla[tabla.index.year >= 1998]
    guardada = tend32.series_cuenca()
    dif = (sub[guardada.columns] - guardada).abs().max()
    print("Diferencia máxima 1998–2022 frente a los productos actuales:")
    print(dif.round(5).to_string())
    assert (dif <= 2e-3).all(), dif      # los productos se guardaron redondeados a 3 decimales
    t_nueva = tend32.tendencias(sub).set_index("clave")
    t_guardada = pd.read_csv(CARPETA_PRODUCTOS / "tendencias_demanda.csv").set_index("clave")
    for c in ("ols_por_decada", "sen_por_decada", "p_ols_newey_west", "p_mk_permutacion"):
        assert np.allclose(t_nueva[c], t_guardada[c], atol=2e-3, rtol=1e-3), c
    print("Comprobación 1998–2022: reproduce las tendencias de la fase 8.")


def main():
    diaria = diaria_completa()
    tabla = demanda_mensual(diaria)
    assert len(tabla) == 42 * 12
    comprobar_1998_2022(tabla)

    tabla_t = tend32.tendencias(tabla)
    atr = tend32.atribucion(tabla_t)
    salida = tabla.copy()
    salida.index = salida.index.strftime("%Y-%m")
    salida.index.name = "mes"
    salida.round(4).to_csv(SALIDA_MENSUAL)
    tabla_t.round(5).to_csv(SALIDA_TENDENCIAS, index=False)
    atr.round(5).to_csv(SALIDA_ATRIBUCION, index=False)
    tend32.figura(tabla, tabla_t, atr, salida=SALIDA_FIGURA)

    pd.set_option("display.width", 200)
    anual = tabla[["eto", "thornthwaite"]].groupby(tabla.index.year).sum()
    print("\nMedia anual (mm/año): 1981–1997", anual.loc[:1997].mean().round(0).to_dict(),
          "| 1998–2022", anual.loc[1998:].mean().round(0).to_dict())
    print(tabla_t[["variable", "media", "ols_por_decada", "ols_pct_por_decada", "p_ols_newey_west", "q_ols",
                   "sen_por_decada", "p_mk_permutacion", "q_mk", "p_mk_hamed_rao", "pettitt_ultimo_anio_tramo1",
                   "p_pettitt", "ols_sin_primeros_anios", "ols_sin_ultimos_anios"]].round(4).to_string())
    print(atr[["forzante", "tendencia_forzante_por_decada", "contribucion_pct_por_decada",
               "contribucion_mm_anio_por_decada"]].round(3).to_string())
    print(f"Listo: {SALIDA_MENSUAL.name}, {SALIDA_TENDENCIAS.name}, {SALIDA_ATRIBUCION.name}, {SALIDA_FIGURA.name}")


if __name__ == "__main__":
    main()
