"""Fase 4 (punto 1): métodos de evapotranspiración de otras familias, en los 6 puntos y en la cuenca, 1998–2022.

Métodos elegidos por Juan el 2026-11-20. Thornthwaite se programó aparte, paso a paso con Juan (22_thornthwaite.py);
aquí se importa su función y se compara con los demás.

    Método                          Estima    Familia                     Fuente de la ecuación
    Thornthwaite (1948)             ETP       temperatura                 notas del curso, Parte 7 (script 22)
    Hargreaves–Samani (1985)        ETo       temperatura + Ra            notas del curso (C. D. Hoyos), Parte 7;
                                                                          FAO-56 ec. 52
    Priestley–Taylor (1972)         ETp       radiación                   notas del curso, Partes 2 y 7
    Makkink (1957)                  ETo       radiación + temperatura     notas del curso, Parte 7
    Brutsaert–Stricker (1979), AA   ET real   relación complementaria     notas del curso, Parte 7
    Penman (1948), forma FAO-24     E0        combinación (agua libre)    notas del curso, Parte 6 (lo usa la AA)
    Cenicafé, Jaramillo (2006)      ETo       altitud                     Cenicafé 57(4):288–298, p. 292

Ecuaciones (todas diarias, en mm/día; Rn, Rs y Ra en MJ/m²·día; T en °C; presiones en kPa):

    Hargreaves        0.0023 · 0.408 · Ra · (T + 17.8) · √(Tmáx − Tmín)
    Priestley–Taylor  α · Δ/(Δ + γ) · (Rn − G)/λ,                 α = 1.26
    Makkink           0.61 · Δ/(Δ + γ) · Rs/λ − 0.12
    Penman (FAO-24)   Δ/(Δ + γ) · Rn/λ + γ/(Δ + γ) · f(u) · (es − ea)·10,   f(u) = 0.27 · (1 + U2/100)
                      con U2 = viento a 2 m en km/día y el déficit pasado de kPa a mbar (×10)
    AA                ET = 2 · ETw − ETp,   ETw = Priestley–Taylor, ETp = Penman
    Cenicafé 2006     4.37 · exp(−0.0002 · h)

Supuestos (se declaran en anexos/ecuaciones_metodos.md):
    - Mismos forzantes y periodo que la ETo FAO-56: productos/punto1/era5land_diario_puntos.csv (salida de 03) y la
      misma T, Δ, γ, es, ea y u2 que 04_eto_fao56.py (se importan sus funciones).
    - λ = 2.45 MJ/kg constante, el mismo que FAO-56 usa en el factor 0.408 = 1/2.45, para que las diferencias con la
      ETo salgan del método y no de λ.
    - Rn es la del pasto de referencia (albedo 0.23, script 03). G = 0 a escala diaria, como en la ETo.
    - Rs y Ra salen de ERA5-Land y de FAO-56 (script 03).
    - AA: se deja tal cual aunque salga negativa un día; se cuenta cuántos días pasa.
    - Cenicafé: h = altura media del DEM en la región de Voronoi de cada punto (anexos/punto1/elevacion_puntos_dem.csv,
      columna z_region_dem_m). Da un valor fijo por punto; el mensual es ese valor por los días del mes.

Escribe en productos/punto1/:
    metodos_diaria_puntos.csv   por día y punto, cada método (mm/día)
    metodos_mensual.csv         por mes, cada método en la cuenca (mm/mes) y la ETo FAO-56, promedio ponderado por
                                Voronoi como en 04
    ajuste_por_mes.csv          por método y mes calendario, frente a la ETo FAO-56: sesgo, sesgo %, MAE, RMSE (mm/mes)
                                y si |sesgo %| supera la dispersión entre pruebas de la fase 3
    ajuste_ciclo_anual.csv      por método: error de amplitud y de fase del ciclo anual medio

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/21_metodos_et.py
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_DIARIA = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"
ENTRADA_ETO = CARPETA_PRODUCTOS / "eto_mensual_cuenca.csv"
ENTRADA_DISPERSION = CARPETA_PRODUCTOS / "dispersion_pruebas.csv"
ENTRADA_ALTURAS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"
SALIDA_DIARIA = CARPETA_PRODUCTOS / "metodos_diaria_puntos.csv"
SALIDA_MENSUAL = CARPETA_PRODUCTOS / "metodos_mensual.csv"
SALIDA_AJUSTE = CARPETA_PRODUCTOS / "ajuste_por_mes.csv"
SALIDA_CICLO = CARPETA_PRODUCTOS / "ajuste_ciclo_anual.csv"

# Las funciones de FAO-56 (e°, Δ, u2) y los pesos de Voronoi se toman de 04_eto_fao56.py para no reescribirlas.
_spec = importlib.util.spec_from_file_location("eto_fao56", Path(__file__).with_name("04_eto_fao56.py"))
eto_fao56 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eto_fao56)
PESOS = eto_fao56.PESOS
_spec = importlib.util.spec_from_file_location("thornthwaite", Path(__file__).with_name("22_thornthwaite.py"))
thornthwaite = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(thornthwaite)

LAMBDA_MJ_KG = 2.45        # calor latente de vaporización, el de FAO-56 (0.408 = 1/2.45)
ALFA_PT = 1.26             # Priestley y Taylor (1972)
G_DIARIO = 0.0             # FAO-56 ec. 42
CENICAFE_2006 = 4.37       # Jaramillo (2006), p. 292: ETo (mm/día) = 4.37·exp(−0.0002 h)
CENICAFE_EXPONENTE = -0.0002  # 1/m, Jaramillo (2006), p. 292
# Juan usa la versión de 2006 (ajustada a Penman–Monteith, como nuestra ETo), no la de 1989 (4.658, ajustada a Penman).

# Nombre de columna -> (nombre corto para tablas, cantidad que estima). La AA es ET real: no se mezcla sin decirlo.
METODOS = {
    "thornthwaite": ("Thornthwaite", "ETP"),
    "hargreaves": ("Hargreaves–Samani", "ETo"),
    "priestley_taylor": ("Priestley–Taylor", "ETp"),
    "makkink": ("Makkink", "ETo"),
    "penman_1948": ("Penman 1948 (FAO-24)", "E0"),
    "aa_brutsaert_stricker": ("Brutsaert–Stricker (AA)", "ET real"),
    "cenicafe_2006": ("Cenicafé 2006", "ETo"),
}


def metodos_diarios(diaria, altura_por_punto):
    """Cada método en mm/día, día a día y punto a punto."""
    tmax, tmin = diaria["tmax_C"], diaria["tmin_C"]
    t = (tmax + tmin) / 2                                                       # FAO-56 ec. 9, igual que la ETo
    delta = eto_fao56.pendiente_saturacion(t)                                   # ec. 13
    gamma = 0.665e-3 * diaria["sp_kPa"]                                         # ec. 8, con la presión de cada punto
    es = (eto_fao56.presion_saturacion(tmax) + eto_fao56.presion_saturacion(tmin)) / 2   # ec. 12
    deficit_kpa = (es - diaria["ea_kPa"]).clip(lower=0)
    u2 = eto_fao56.viento_a_2m(diaria["viento10_ms"])                           # ec. 47
    peso_radiativo = delta / (delta + gamma)

    salida = pd.DataFrame(index=diaria.index)
    salida["hargreaves"] = 0.0023 * 0.408 * diaria["ra_MJm2"] * (t + 17.8) * np.sqrt((tmax - tmin).clip(lower=0))
    salida["priestley_taylor"] = ALFA_PT * peso_radiativo * (diaria["rn_MJm2"] - G_DIARIO) / LAMBDA_MJ_KG
    salida["makkink"] = 0.61 * peso_radiativo * diaria["rs_MJm2"] / LAMBDA_MJ_KG - 0.12

    # Penman (1948) en la forma de FAO-24: f(u) en mm/día/mbar con U2 en km/día; 1 kPa = 10 mbar.
    u2_km_dia = u2 * 86.4
    funcion_viento = 0.27 * (1 + u2_km_dia / 100)
    salida["penman_1948"] = (peso_radiativo * diaria["rn_MJm2"] / LAMBDA_MJ_KG
                             + (1 - peso_radiativo) * funcion_viento * deficit_kpa * 10)
    salida["aa_brutsaert_stricker"] = 2 * salida["priestley_taylor"] - salida["penman_1948"]

    h = diaria["punto"].map(altura_por_punto)
    salida["cenicafe_2006"] = CENICAFE_2006 * np.exp(CENICAFE_EXPONENTE * h)
    return salida


def promedio_cuenca(mensual_puntos, columnas):
    """Promedio por mes ponderado por el área de Voronoi de cada punto, como en 04_eto_fao56.py."""
    peso = mensual_puntos["punto"].map(PESOS)
    return (mensual_puntos[columnas].mul(peso, axis=0).groupby(mensual_puntos["fecha"]).sum()
            .div(peso.groupby(mensual_puntos["fecha"]).sum(), axis=0))


def ajuste_por_mes(mensual, dispersion):
    """Por método y mes calendario, frente a la ETo FAO-56 de cada mes (25 valores por mes calendario)."""
    filas = []
    mes_calendario = mensual.index.month
    for columna, (nombre, cantidad) in METODOS.items():
        error = mensual[columna] - mensual["eto_fao56"]
        for mes in range(1, 13):
            e = error[mes_calendario == mes]
            referencia = mensual.loc[mes_calendario == mes, "eto_fao56"].mean()
            sesgo_pct = 100 * e.mean() / referencia
            umbral = dispersion.loc[mes, "dispersion_pct"]
            filas.append({
                "metodo": nombre, "cantidad": cantidad, "mes": mes, "n_anios": e.size,
                "eto_fao56_mm_mes": referencia, "metodo_mm_mes": referencia + e.mean(),
                "sesgo_mm_mes": e.mean(), "sesgo_pct": sesgo_pct,
                "mae_mm_mes": e.abs().mean(), "rmse_mm_mes": np.sqrt((e ** 2).mean()),
                "dispersion_pruebas_pct": umbral, "supera_dispersion": abs(sesgo_pct) > umbral,
            })
    return pd.DataFrame(filas)


def ajuste_ciclo_anual(mensual):
    """Error de amplitud y de fase del ciclo anual medio (media de los 25 años por mes calendario).

    Amplitud = máximo − mínimo del ciclo medio. Fase = mes del máximo y del mínimo; el error de fase es la diferencia
    en meses con la ETo FAO-56, tomada en el círculo de 12 meses (de −6 a +6). La ETo tiene dos máximos al año, así
    que se usa el máximo y el mínimo absolutos en vez de un armónico.
    """
    ciclo = mensual.groupby(mensual.index.month).mean()
    ref = ciclo["eto_fao56"]

    def desfase(a, b):
        return int((a - b + 6) % 12 - 6)

    filas = []
    for columna, (nombre, cantidad) in METODOS.items():
        serie = ciclo[columna]
        amplitud = serie.max() - serie.min()
        constante = columna.startswith("cenicafe")  # valor diario fijo: el ciclo sale solo de los días del mes
        filas.append({
            "metodo": nombre, "cantidad": cantidad,
            "amplitud_metodo_mm_mes": amplitud, "amplitud_eto_mm_mes": ref.max() - ref.min(),
            "error_amplitud_mm_mes": amplitud - (ref.max() - ref.min()),
            "error_amplitud_pct": 100 * (amplitud / (ref.max() - ref.min()) - 1),
            "mes_maximo": int(serie.idxmax()), "mes_minimo": int(serie.idxmin()),
            "error_fase_maximo_meses": desfase(serie.idxmax(), ref.idxmax()),
            "error_fase_minimo_meses": desfase(serie.idxmin(), ref.idxmin()),
            "nota": "solo cambia por los días del mes" if constante else "",
        })
    filas.append({"metodo": "ETo FAO-56", "cantidad": "ETo", "amplitud_metodo_mm_mes": ref.max() - ref.min(),
                  "amplitud_eto_mm_mes": ref.max() - ref.min(), "error_amplitud_mm_mes": 0.0,
                  "error_amplitud_pct": 0.0, "mes_maximo": int(ref.idxmax()), "mes_minimo": int(ref.idxmin()),
                  "error_fase_maximo_meses": 0, "error_fase_minimo_meses": 0, "nota": "referencia"})
    return pd.DataFrame(filas)


def main():
    diaria = pd.read_csv(ENTRADA_DIARIA, parse_dates=["fecha"])
    puntos = pd.read_csv(ENTRADA_ALTURAS).set_index("punto")
    alturas = puntos["z_region_dem_m"].to_dict()

    metodos = pd.concat([diaria[["fecha", "punto"]], metodos_diarios(diaria, alturas)], axis=1)
    columnas = [c for c in METODOS if c != "thornthwaite"]  # Thornthwaite es mensual: se agrega abajo
    assert metodos[columnas].notna().all().all()
    for columna in ["hargreaves", "priestley_taylor", "penman_1948", "cenicafe_2006"]:
        assert (metodos[columna] > 0).all(), f"{columna}: valores no positivos"
    dias_aa_negativa = int((metodos["aa_brutsaert_stricker"] < 0).sum())
    dias_makkink_negativa = int((metodos["makkink"] < 0).sum())
    print(f"Días-punto con AA < 0: {dias_aa_negativa}; con Makkink < 0: {dias_makkink_negativa} "
          f"(de {len(metodos)})")
    metodos.assign(fecha=metodos["fecha"].dt.strftime("%Y-%m-%d")).round(4).to_csv(SALIDA_DIARIA, index=False)
    print(f"Listo: {SALIDA_DIARIA} ({len(metodos)} filas)")

    # Mensual por punto = suma de los diarios (igual que la ETo); cuenca = promedio ponderado por Voronoi.
    mensual_puntos = (metodos.set_index("fecha").groupby("punto")[columnas].resample("MS").sum().reset_index())
    assert (mensual_puntos.groupby("punto").size() == 300).all()
    etp_th = thornthwaite.thornthwaite_mensual(diaria, puntos["lat"].to_dict())
    mensual_puntos = mensual_puntos.merge(
        etp_th[["punto", "fecha", "etp_thornthwaite_mm"]].rename(columns={"etp_thornthwaite_mm": "thornthwaite"}),
        on=["punto", "fecha"], validate="one_to_one")
    columnas = list(METODOS)
    mensual = promedio_cuenca(mensual_puntos, columnas)

    eto = pd.read_csv(ENTRADA_ETO)
    eto.index = pd.to_datetime(eto["mes"])
    mensual["eto_fao56"] = eto["eto_mm_mes"].reindex(mensual.index)
    assert mensual["eto_fao56"].notna().all() and len(mensual) == 300

    salida_mensual = mensual.rename(columns={c: f"{c}_mm_mes" for c in [*columnas, "eto_fao56"]})
    salida_mensual.index = salida_mensual.index.strftime("%Y-%m")
    salida_mensual.rename_axis("mes").round(3).to_csv(SALIDA_MENSUAL)
    print(f"Listo: {SALIDA_MENSUAL} ({len(salida_mensual)} meses)")

    dispersion = pd.read_csv(ENTRADA_DISPERSION).set_index("mes")
    ajuste = ajuste_por_mes(mensual, dispersion)
    ajuste.round(3).to_csv(SALIDA_AJUSTE, index=False)
    print(f"Listo: {SALIDA_AJUSTE} ({len(ajuste)} filas)")

    ciclo = ajuste_ciclo_anual(mensual)
    ciclo.round(3).to_csv(SALIDA_CICLO, index=False)
    print(f"Listo: {SALIDA_CICLO}")

    anual = mensual.mean() * 12
    print("\nMedia anual de la cuenca, 1998–2022 (mm/año):")
    for columna, valor in anual.items():
        print(f"  {METODOS.get(columna, ('ETo FAO-56', 'ETo'))[0]:<26} {valor:7.0f}")


if __name__ == "__main__":
    main()
