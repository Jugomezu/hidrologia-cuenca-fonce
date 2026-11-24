"""Fase 6: ET real de la cuenca por varios caminos, su incertidumbre y su techo de energía (punto 1).

Junta lo que ya calculan otros scripts y agrega lo que pide el plan de la fase 6:
    1. Balance P − Q por año hidrológico (inicia en el mes de menor agua en el suelo) y por año calendario.
    2. Incertidumbre del balance: sigma_ET² = sigma_P² + sigma_Q².
    3. Techo de energía: radiación neta real de la superficie de ERA5-Land (no la del pasto de FAO-56), Rn/λ en mm, y la
       fracción evaporativa λET/Rn de cada camino.
    4. Cuánto se aparta cada producto (y la AA de Brutsaert–Stricker) del balance, en los mismos meses.
    5. Marcas por año: P − Q negativo, P − Q mayor que Rn/λ, o P − Q fuera del rango de los productos. Solo se marcan;
       no se explican.

Decisiones (anexos/decisiones.md). Propuestas por el agente con Juan ausente (2026-11-22) y revisadas por Juan el
2026-11-23: σ_P aprobado; σ_Q al 95 % (25.6 %); año calendario como principal (el hidrológico se sigue calculando).
    - P̄ = (PI + PL)/2 es la lluvia del balance (Juan, 23 nov): PI y PL son dos medidas de la misma lluvia con el mismo
      error, independiente, así que la mejor estimación es su promedio. PI y PL quedan como sensibilidad.
    - sigma_P = 1.96 · |PL − PI| / 2: cada medida tiene sigma = |PL − PI|/√2 (la diferencia tiene varianza 2·sigma²) y
      el promedio de dos tiene sigma/√2 = |PL − PI|/2; × 1.96 para el 95 %, igual que sigma_Q (Juan, 23 nov).
    - sigma_Q = 25.6 % de Q (Juan, 23 nov): Di Baldassarre y Montanari (2009), error medio de la curva de gasto al
      95 %, sin pasarlo a 1 sigma. Se trata como sistemático (no se reduce al promediar años). Sensibilidad: 5.3 %
      (un aforo) y 42.8 % (el máximo del estudio), también al 95 %.
    - Año hidrológico: empieza en el mes calendario con la menor agua media en el suelo (ERA5-Land, 0–289 cm).
    - «Muy distinto de los productos»: el P − Q del año queda fuera del rango de los productos con los 12 meses ese año
      (ERA5-Land e, GLEAM E, MOD16A2GF, TerraClimate aet, SSEBop v6.1 y v5, y la AA), o fuera de ± sigma_ET (95 %) de su
      mediana. El rango solo casi nunca marca nada: SSEBop v5 (~470 mm) y la AA (~1 550 mm) lo abren mucho.

Lee (productos/punto1/):
    balance_hidrico_mensual.csv     PI, PL, Q y agua en el suelo, mm/mes (script 15)
    et_real_mensual_productos.csv   ET real de cada producto, mm/mes (script 14)
    metodos_mensual.csv             AA de Brutsaert–Stricker y ETo Penman–Monteith (FAO-56), mm/mes (script 21)
y datos/punto1/era5land_mensual_balance/era5land_mensual_balance_1998_2022_fonce.nc (ssr y str de ERA5-Land, script 07),
con el polígono y los pesos por área del script 14.

Escribe (productos/punto1/):
    et_balance_anual.csv        P − Q por año hidrológico y calendario (años con los 12 meses de Q), sigma, marcas
    et_productos_mensual.csv    todas las ET reales, ETo, Rn/λ y el balance, mm/mes, 1998-01 a 2022-12
    et_productos_vs_balance.csv cada producto frente al balance en los mismos meses, y su fracción evaporativa
    et_incertidumbre.csv        sigma_P, sigma_Q y sigma_ET de largo plazo, con la sensibilidad de sigma_Q
    et_techo_energia.csv        ciclo anual de Rn/λ, ETo, balance y productos, mm/mes

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/24_et_real_fase6.py
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CODIGO = RAIZ_ENTREGA / "codigo" / "punto1"
PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ARCHIVO_ERA5_MENSUAL = (RAIZ_ENTREGA / "datos" / "punto1" / "era5land_mensual_balance"
                        / "era5land_mensual_balance_1998_2022_fonce.nc")

MESES = pd.period_range("1998-01", "2022-12", freq="M")
ULTIMO_MES_ERA5_MENSUAL = pd.Period("2022-08", "M")   # error de ECMWF desde 2022-09 (anexos/decisiones.md)
LAMBDA_MJ_KG = 2.45                                    # calor latente de vaporización, FAO-56 (el mismo de la ETo)

# Incertidumbre del caudal: Di Baldassarre y Montanari (2009), HESS 13, 913–921, https://doi.org/10.5194/hess-13-913-2009
# (p. 919–920: error global de 6.2 % a 42.8 % de Q al 95 %, media 25.6 %; p. 915: un aforo, 5.3 % al 95 %).
# Juan (2026-11-23): σ_Q con el valor al 95 % tal cual (25.6 %), no dividido por 1.96, y σ_P también al 95 %
# (×1.96), para que σ_ET sea un intervalo del 95 % coherente.
Z_95_P = 1.96
SIGMA_Q_FRACCION = {"central": 0.256, "un aforo": 0.053, "máximo del estudio": 0.428}

# Productos de ET real (nombre en la salida -> columna de entrada) y la AA del script 21.
NOMBRES = {
    "era5land_e": "ERA5-Land e", "gleam_E": "GLEAM v4.3a E", "mod16a2gf": "MOD16A2GF v061",
    "terraclimate_aet": "TerraClimate aet", "ssebop_v61": "SSEBop v6.1", "ssebop_v5": "SSEBop v5",
    "aa_brutsaert_stricker": "AA (Brutsaert–Stricker)",
}
# Principio de cálculo, resolución y unidades de cada producto (lo que dicen sus fichas y referencias; ver
# anexos/referencias.md). Signo: en el archivo de ERA5-Land la evaporación es negativa (flujo hacia arriba); el script 14
# la cambia de signo. Los demás vienen positivos.
FICHAS = {
    "era5land_e": ("Modelo de superficie (HTESSEL) forzado por el reanálisis", "0.1°", "mensual",
                   "m/día, negativo hacia arriba"),
    "gleam_E": ("Modelo de evaporación con datos satelitales: evaporación potencial reducida por un factor de estrés",
                "0.1°", "mensual", "mm/mes"),
    "mod16a2gf": ("Penman–Monteith con datos de MODIS (índice de área foliar, albedo, cobertura)", "500 m",
                  "8 días", "mm por compuesto"),
    "terraclimate_aet": ("Balance hídrico del suelo de un solo nivel (Thornthwaite–Mather modificado)", "1/24°",
                         "mensual", "mm/mes"),
    "ssebop_v61": ("Balance de energía simplificado con temperatura de superficie (VIIRS)", "~1 km", "mensual",
                   "mm/mes"),
    "ssebop_v5": ("Balance de energía simplificado con temperatura de superficie (MODIS)", "~1 km", "mensual",
                  "mm/mes"),
    "aa_brutsaert_stricker": ("Relación complementaria: 2·Priestley–Taylor − Penman (script 21)",
                              "6 puntos ERA5-Land", "diaria", "mm/día"),
}


def cargar_script_14():
    """Reusa el polígono y los pesos por área del script 14 (mismo promedio de cuenca que los productos)."""
    especificacion = importlib.util.spec_from_file_location("et_real_productos",
                                                          CODIGO / "14_et_real_productos_cuenca.py")
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def leer_mensual(nombre, columnas):
    tabla = pd.read_csv(PRODUCTOS / nombre)
    tabla.index = pd.PeriodIndex(tabla["mes"], freq="M")
    return tabla[columnas].reindex(MESES)


def radiacion_neta_mm(script_14):
    """Rn real de la superficie (ssr + str de ERA5-Land), promedio de cuenca por área, en mm/mes equivalentes (Rn/λ).

    El archivo trae la media mensual de la acumulación diaria en J/m² (positivo hacia la superficie en ssr; str es
    negativo porque la superficie pierde onda larga). Rn/λ (mm/día) = (ssr + str) / (λ · 10⁶).
    """
    poligono = script_14.cargar_cuenca()
    ds = xr.open_dataset(ARCHIVO_ERA5_MENSUAL)
    rn = (ds["ssr"] + ds["str"]).transpose("valid_time", "latitude", "longitude")
    pesos = script_14.pesos_por_area(rn["latitude"].values, rn["longitude"].values, poligono)
    valores = rn.values.astype(float)
    assert not np.isnan(valores).any()
    media_j_m2_dia = (valores * pesos).sum(axis=(1, 2)) / pesos.sum()
    indice = pd.to_datetime(rn["valid_time"].values).to_period("M")
    mm_dia = pd.Series(media_j_m2_dia / (LAMBDA_MJ_KG * 1e6), index=indice)
    mm_mes = mm_dia * mm_dia.index.days_in_month
    mm_mes[mm_mes.index > ULTIMO_MES_ERA5_MENSUAL] = np.nan
    return mm_mes.reindex(MESES)


def suma_por_ciclo(tabla):
    """Total anual como suma del ciclo anual medio (media de cada mes calendario); exige los 12 meses."""
    ciclo = tabla.groupby(tabla.index.month).mean()
    assert len(ciclo) == 12, "falta algún mes calendario"
    return ciclo.sum()


def mes_inicio_anio_hidrologico(mensual):
    """Mes calendario con la menor agua media en el suelo: ahí empieza el año hidrológico."""
    ciclo_suelo = mensual["S_suelo"].groupby(mensual.index.month).mean()
    return int(ciclo_suelo.idxmin()), ciclo_suelo


def balance_por_anio(mensual, mes_inicio, etiqueta):
    """P − Q y ΔS del suelo por año que empieza en mes_inicio; solo años con los 12 meses de Q."""
    # el año hidrológico se nombra por el año calendario en que empieza
    anio = mensual.index.year - (mensual.index.month < mes_inicio).astype(int)
    agrupado = mensual.groupby(anio)
    anual = pd.DataFrame({
        "meses_con_Q": agrupado["Q"].count(),
        "PI": agrupado["PI"].sum(min_count=12), "PL": agrupado["PL"].sum(min_count=12),
        "Q": agrupado["Q"].sum(min_count=12),
        "Rn_lambda": agrupado["Rn_lambda"].sum(min_count=12),
        "ETo": agrupado["ETo"].sum(min_count=12),
    })
    # ΔS del año: agua del suelo en el último mes del año menos la del último mes del año anterior (con años calendario
    # es diciembre menos diciembre, como el script 15)
    mes_final = (mes_inicio - 2) % 12 + 1
    suelo_final = mensual.loc[mensual.index.month == mes_final, "S_suelo"]
    suelo_final.index = suelo_final.index.year - (1 if mes_final < mes_inicio else 0)
    anual["dS_suelo"] = suelo_final.reindex(anual.index) - suelo_final.shift(1).reindex(anual.index)
    for producto in NOMBRES:
        anual[producto] = agrupado[producto].sum(min_count=12)
    anual = anual[anual["meses_con_Q"] == 12].copy()
    anual.insert(0, "tipo_de_anio", etiqueta)
    anual.insert(1, "meses", f"{mes_inicio:02d} a {(mes_inicio - 2) % 12 + 1:02d}")
    anual["Pm"] = (anual["PI"] + anual["PL"]) / 2   # P̄, mejor estimación de la lluvia (Juan, 23 nov)
    for fuente in ["PI", "PL", "Pm"]:
        anual[f"P_menos_Q_{fuente}"] = anual[fuente] - anual["Q"]
        anual[f"P_menos_Q_menos_dS_{fuente}"] = anual[f"P_menos_Q_{fuente}"] - anual["dS_suelo"]
    anual["sigma_P"] = (anual["PL"] - anual["PI"]).abs() / 2 * Z_95_P
    anual["sigma_Q"] = SIGMA_Q_FRACCION["central"] * anual["Q"]
    anual["sigma_ET"] = np.hypot(anual["sigma_P"], anual["sigma_Q"])

    # Marcas (solo se señalan; no se explican aquí)
    productos_del_anio = anual[list(NOMBRES)]
    anual["productos_con_dato"] = productos_del_anio.notna().sum(axis=1)
    anual["min_productos"] = productos_del_anio.min(axis=1)
    anual["max_productos"] = productos_del_anio.max(axis=1)
    anual["mediana_productos"] = productos_del_anio.median(axis=1)
    for fuente in ["PI", "PL", "Pm"]:
        p_menos_q = anual[f"P_menos_Q_{fuente}"]
        marcas = []
        for anio_i in anual.index:
            fila = []
            if p_menos_q[anio_i] < 0:
                fila.append("P−Q negativo")
            if pd.notna(anual.at[anio_i, "Rn_lambda"]) and p_menos_q[anio_i] > anual.at[anio_i, "Rn_lambda"]:
                fila.append("P−Q > Rn/λ")
            if pd.notna(anual.at[anio_i, "ETo"]) and p_menos_q[anio_i] > anual.at[anio_i, "ETo"]:
                fila.append("P−Q > ETo")
            if p_menos_q[anio_i] < anual.at[anio_i, "min_productos"]:
                fila.append("bajo todos los productos")
            if p_menos_q[anio_i] > anual.at[anio_i, "max_productos"]:
                fila.append("sobre todos los productos")
            distancia = p_menos_q[anio_i] - anual.at[anio_i, "mediana_productos"]
            if abs(distancia) > anual.at[anio_i, "sigma_ET"]:
                fila.append(f"fuera de ± sigma_ET (95 %) de la mediana de los productos ({distancia:+.0f} mm)")
            marcas.append("; ".join(fila))
        anual[f"marcas_{fuente}"] = marcas
    return anual.rename_axis("anio")


def productos_frente_al_balance(mensual):
    """Cada producto frente al balance en los mismos meses (los que tienen Q y dato del producto), por ciclo anual."""
    filas = []
    for producto, nombre in NOMBRES.items():
        comunes = mensual[mensual["Q"].notna() & mensual[producto].notna()]
        meses_por_mes = comunes.groupby(comunes.index.month).size()
        if len(meses_por_mes) < 12:
            continue
        totales = suma_por_ciclo(comunes[[producto, "ETR_PI", "ETR_PL", "ETR_Pm", "Q", "PI", "PL"]])
        # fracción evaporativa con los meses que además tienen Rn de ERA5-Land
        con_rn = comunes[comunes["Rn_lambda"].notna()]
        totales_rn = suma_por_ciclo(con_rn[[producto, "ETR_PI", "ETR_PL", "Rn_lambda", "ETo"]])
        sigma_p = abs(totales["PL"] - totales["PI"]) / 2 * Z_95_P
        sigma_et = np.hypot(sigma_p, SIGMA_Q_FRACCION["central"] * totales["Q"])
        principio, resolucion, paso, unidades = FICHAS[producto]
        filas.append({
            "producto": nombre, "principio": principio, "resolucion": resolucion, "paso_original": paso,
            "unidades_originales": unidades,
            "primer_mes": str(mensual[producto].first_valid_index()),
            "ultimo_mes": str(mensual[producto].last_valid_index()),
            "meses_comunes_con_Q": len(comunes), "min_anios_por_mes": int(meses_por_mes.min()),
            "producto_mm_anio": totales[producto],
            "balance_PI_mm_anio": totales["ETR_PI"], "balance_PL_mm_anio": totales["ETR_PL"],
            "balance_Pm_mm_anio": totales["ETR_Pm"],
            "dif_vs_Pm_mm": totales[producto] - totales["ETR_Pm"],
            "dif_vs_Pm_pct": 100 * (totales[producto] / totales["ETR_Pm"] - 1),
            "dentro_de_sigma_ET_de_Pm": abs(totales[producto] - totales["ETR_Pm"]) <= sigma_et,
            "dif_vs_PI_mm": totales[producto] - totales["ETR_PI"],
            "dif_vs_PL_mm": totales[producto] - totales["ETR_PL"],
            "dif_vs_PI_pct": 100 * (totales[producto] / totales["ETR_PI"] - 1),
            "dif_vs_PL_pct": 100 * (totales[producto] / totales["ETR_PL"] - 1),
            "sigma_ET_balance_mm": sigma_et,
            "entre_balances": totales["ETR_PI"] <= totales[producto] <= totales["ETR_PL"],
            "fraccion_evaporativa": totales_rn[producto] / totales_rn["Rn_lambda"],
            "producto_sobre_ETo": totales_rn[producto] / totales_rn["ETo"],
        })
    return pd.DataFrame(filas)


def main():
    script_14 = cargar_script_14()
    balance = leer_mensual("balance_hidrico_mensual.csv", ["PI", "PL", "Q", "S_suelo", "ETR_PI", "ETR_PL"])
    productos = leer_mensual("et_real_mensual_productos.csv", [c for c in NOMBRES if c != "aa_brutsaert_stricker"])
    metodos = leer_mensual("metodos_mensual.csv", ["aa_brutsaert_stricker_mm_mes", "eto_fao56_mm_mes"])
    mensual = pd.concat([balance, productos], axis=1)
    mensual["Pm"] = (mensual["PI"] + mensual["PL"]) / 2           # P̄ (Juan, 23 nov)
    mensual["ETR_Pm"] = (mensual["ETR_PI"] + mensual["ETR_PL"]) / 2
    mensual["aa_brutsaert_stricker"] = metodos["aa_brutsaert_stricker_mm_mes"]
    mensual["ETo"] = metodos["eto_fao56_mm_mes"]
    mensual["Rn_lambda"] = radiacion_neta_mm(script_14)
    print(f"Rn/λ de ERA5-Land: {int(mensual['Rn_lambda'].notna().sum())} meses (hasta {ULTIMO_MES_ERA5_MENSUAL})")

    # --- 1. Años hidrológicos y calendario
    mes_inicio, ciclo_suelo = mes_inicio_anio_hidrologico(mensual)
    print(f"Agua en el suelo, media por mes (mm): {ciclo_suelo.round(0).to_dict()}")
    print(f"Año hidrológico: empieza en el mes {mes_inicio} (menor agua en el suelo)")
    anual = pd.concat([balance_por_anio(mensual, mes_inicio, "hidrologico"),
                       balance_por_anio(mensual, 1, "calendario")])

    # --- 2. Incertidumbre del balance de largo plazo (ciclo anual medio con los meses que tienen Q, como el script 15)
    con_q = mensual[mensual["Q"].notna()]
    largo = suma_por_ciclo(con_q[["PI", "PL", "Pm", "Q", "ETR_PI", "ETR_PL", "ETR_Pm"]])
    sigma_p = abs(largo["PL"] - largo["PI"]) / 2 * Z_95_P
    incertidumbre = []
    for caso, fraccion in SIGMA_Q_FRACCION.items():
        sigma_q = fraccion * largo["Q"]
        sigma_et = np.hypot(sigma_p, sigma_q)
        incertidumbre.append({
            "caso_sigma_Q": caso, "sigma_Q_pct_de_Q": 100 * fraccion,
            "P_PI": largo["PI"], "P_PL": largo["PL"], "P_media": largo["Pm"], "Q": largo["Q"],
            "ETR_Pm": largo["ETR_Pm"], "ETR_PI": largo["ETR_PI"], "ETR_PL": largo["ETR_PL"],
            "sigma_P": sigma_p, "sigma_Q": sigma_q, "sigma_ET": sigma_et,
            "sigma_ET_pct_de_ETR_Pm": 100 * sigma_et / largo["ETR_Pm"],
            "sigma_ET_pct_de_ETR_PI": 100 * sigma_et / largo["ETR_PI"],
            "sigma_ET_pct_de_ETR_PL": 100 * sigma_et / largo["ETR_PL"],
            "parte_de_P_en_varianza_pct": 100 * sigma_p ** 2 / sigma_et ** 2,
        })
    incertidumbre = pd.DataFrame(incertidumbre)

    # --- 3. Techo de energía y fracción evaporativa del balance (meses con Q y con Rn de ERA5-Land)
    con_q_rn = con_q[con_q["Rn_lambda"].notna()]
    techo = suma_por_ciclo(con_q_rn[["ETR_Pm", "ETR_PI", "ETR_PL", "Rn_lambda", "ETo"]])
    ciclo = mensual.groupby(mensual.index.month)[
        ["Rn_lambda", "ETo", "ETR_Pm", "ETR_PI", "ETR_PL", "Pm", "PI", "PL", "Q"] + list(NOMBRES)].mean()
    ciclo.index.name = "mes_calendario"
    # para el balance, el ciclo de P − Q solo con meses con Q (los demás meses no tienen P − Q)
    ciclo[["ETR_Pm", "ETR_PI", "ETR_PL"]] = con_q.groupby(con_q.index.month)[["ETR_Pm", "ETR_PI", "ETR_PL"]].mean()

    # --- 4. Productos frente al balance, en los mismos meses
    frente = productos_frente_al_balance(mensual)

    # --- Comprobaciones físicas del plan: λET/Rn ≤ 1 y ET ≤ ETo en el largo plazo
    print("\nTecho de energía, largo plazo (meses con Q y Rn, ciclo anual medio):")
    print(f"  Rn/λ = {techo['Rn_lambda']:.0f} mm/año; ETo = {techo['ETo']:.0f}")
    for fuente in ["Pm", "PI", "PL"]:
        fe = techo[f"ETR_{fuente}"] / techo["Rn_lambda"]
        print(f"  P − Q con {fuente} = {techo[f'ETR_{fuente}']:.0f}: λET/Rn = {fe:.2f} "
              f"({'≤ 1' if fe <= 1 else 'SUPERA 1'}); ET/ETo = {techo[f'ETR_{fuente}'] / techo['ETo']:.2f}")
    resumen_techo = pd.DataFrame([{"camino": f"balance con {f}", "ET_mm_anio": techo[f"ETR_{f}"],
                                   "Rn_lambda_mm_anio": techo["Rn_lambda"], "ETo_mm_anio": techo["ETo"],
                                   "fraccion_evaporativa": techo[f"ETR_{f}"] / techo["Rn_lambda"],
                                   "ET_sobre_ETo": techo[f"ETR_{f}"] / techo["ETo"]} for f in ["Pm", "PI", "PL"]])

    # --- Salidas
    salida_mensual = mensual.copy()
    salida_mensual.index = salida_mensual.index.strftime("%Y-%m")
    salida_mensual.rename_axis("mes").round(2).to_csv(PRODUCTOS / "et_productos_mensual.csv")
    anual.round(1).to_csv(PRODUCTOS / "et_balance_anual.csv")
    incertidumbre.round(3).to_csv(PRODUCTOS / "et_incertidumbre.csv", index=False)
    frente.round(3).to_csv(PRODUCTOS / "et_productos_vs_balance.csv", index=False)
    ciclo.round(2).to_csv(PRODUCTOS / "et_techo_energia.csv")
    resumen_techo.round(3).to_csv(PRODUCTOS / "et_techo_energia_resumen.csv", index=False)

    print("\nIncertidumbre del balance de largo plazo (mm/año):")
    print(incertidumbre.round(1).to_string(index=False))
    print("\nProductos frente al balance, mismos meses (mm/año):")
    print(frente[["producto", "meses_comunes_con_Q", "min_anios_por_mes", "producto_mm_anio", "balance_PI_mm_anio",
                  "balance_PL_mm_anio", "dif_vs_PI_pct", "dif_vs_PL_pct", "entre_balances",
                  "fraccion_evaporativa", "producto_sobre_ETo"]].round(2).to_string(index=False))
    print("\nAños con los 12 meses de Q y sus marcas:")
    print(anual[["tipo_de_anio", "P_menos_Q_PI", "P_menos_Q_PL", "dS_suelo", "sigma_ET", "Rn_lambda", "ETo",
                 "mediana_productos", "marcas_PI", "marcas_PL"]].round(0).to_string())
    print("\nListo: productos/punto1/et_productos_mensual.csv, et_balance_anual.csv, et_incertidumbre.csv, "
          "et_productos_vs_balance.csv, et_techo_energia.csv y et_techo_energia_resumen.csv")


if __name__ == "__main__":
    main()
