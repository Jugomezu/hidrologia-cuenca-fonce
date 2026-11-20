"""Cierre de la fase 3 (punto 1): las dos pruebas de la ETo en una tabla, su dispersión mes a mes y ETo frente a P − Q.

«Nuestra ETo» = la ETo FAO-56 de este trabajo (scripts 01–04), con forzantes de ERA5-Land.

Lee (productos/punto1/):
    eto_estaciones_diaria.csv        prueba 1: ETo de estación (viento (a), Mogotes-AUT) y nuestra ETo en el punto más
                                     cercano, los mismos días (salida de 13)
    eto_mensual_cuenca.csv           nuestra ETo mensual de la cuenca (salida de 04)
    terraclimate_mensual_cuenca.csv  prueba 2: pet de TerraClimate v1.1 de la cuenca (salida de 05)
    balance_hidrico_mensual.csv      P (PI y PL) y Q mensuales de la cuenca (salida de 15)
    balance_hidrico_anual.csv        P − Q de los 11 años con Q completo (salida de 15)

Escribe en productos/punto1/:
    pruebas_referencia.csv     por serie de referencia y mes calendario: medias, sesgo, sesgo %, MAE y RMSE (mm/día)
    dispersion_pruebas.csv     por mes calendario: sesgo % de cada serie y tres medidas de dispersión entre pruebas
    eto_vs_p_menos_q.csv       ETo multianual frente a P − Q multianual, con PI y con PL, en los mismos meses o años

Todo en mm/día para que las dos pruebas se lean en la misma unidad: la pet y nuestra ETo de cuenca se dividen por los
días de cada mes antes de promediar. Sesgo = nuestra ETo − referencia; sesgo % = sesgo / media de la referencia.
Las estaciones se comparan día a día y TerraClimate mes a mes, así que MAE y RMSE no son comparables entre pruebas;
el sesgo % sí.

Dispersión entre pruebas, por mes calendario. DEFINICIÓN FINAL (Juan, 2026-11-20): rango_2_pruebas_pct, que se copia
en la columna «dispersion_pct» para las fases 4 y 5. Las otras dos se dejan como referencia:
    rango_4_series_pct     máximo − mínimo del sesgo % de las 4 series (3 estaciones y TerraClimate)
    rango_2_pruebas_pct    |sesgo % de TerraClimate − media del sesgo % de las 3 estaciones| (cada prueba cuenta una vez)
    desv_est_4_series_pct  desviación estándar (n − 1) del sesgo % de las 4 series
Y la banda de la referencia para la fase 5: referencia / nuestra ETo, mínimo y máximo de las 4 series.

ETo frente a P − Q: dos caminos, los mismos de 15_balance_hidrico.py.
    «ciclo»  media por mes calendario de los meses con Q (262), sumada sobre los 12 meses; la ETo con los mismos meses.
    «años»   media de los 11 años con los 12 meses de Q; la ETo con los mismos años.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/17_pruebas_referencia_dispersion.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ESTACIONES_DIARIA = PRODUCTOS / "eto_estaciones_diaria.csv"
ETO_CUENCA = PRODUCTOS / "eto_mensual_cuenca.csv"
TERRACLIMATE = PRODUCTOS / "terraclimate_mensual_cuenca.csv"
BALANCE_MENSUAL = PRODUCTOS / "balance_hidrico_mensual.csv"
BALANCE_ANUAL = PRODUCTOS / "balance_hidrico_anual.csv"
SALIDA_PRUEBAS = PRODUCTOS / "pruebas_referencia.csv"
SALIDA_DISPERSION = PRODUCTOS / "dispersion_pruebas.csv"
SALIDA_BALANCE = PRODUCTOS / "eto_vs_p_menos_q.csv"

NOMBRES = {"24025040": "estacion_mogotes", "24025030": "estacion_la_sierra", "24025050": "estacion_charala"}


def metricas(nuestra, referencia):
    diferencia = nuestra - referencia
    return {
        "n": len(diferencia),
        "eto_nuestra_mm_dia": nuestra.mean(),
        "referencia_mm_dia": referencia.mean(),
        "sesgo_mm_dia": diferencia.mean(),
        "sesgo_pct": 100 * diferencia.mean() / referencia.mean(),
        "mae_mm_dia": diferencia.abs().mean(),
        "rmse_mm_dia": np.sqrt((diferencia ** 2).mean()),
    }


def tabla_pruebas():
    filas = []
    # Prueba 1: estaciones, día a día, viento (a)
    diaria = pd.read_csv(ESTACIONES_DIARIA, dtype={"estacion": str}, parse_dates=["fecha"])
    for codigo, nombre in NOMBRES.items():
        d = diaria[diaria["estacion"] == codigo]
        for mes, g in [("anual", d)] + list(d.groupby(d["fecha"].dt.month)):
            filas.append({"prueba": "estaciones", "serie": nombre, "base": "diaria", "mes": mes,
                          **metricas(g["eto_era5_mm"], g["eto_mogotes_aut_mm"])})
    # Prueba 2: TerraClimate pet, mes a mes, cuenca
    eto = pd.read_csv(ETO_CUENCA)[["mes", "eto_mm_mes"]]
    pet = pd.read_csv(TERRACLIMATE)[["mes", "pet_mm_mes"]]
    m = eto.merge(pet, on="mes")
    assert len(m) == 300 and m.notna().all().all()
    fechas = pd.to_datetime(m["mes"])
    m["eto"] = m["eto_mm_mes"] / fechas.dt.days_in_month
    m["pet"] = m["pet_mm_mes"] / fechas.dt.days_in_month
    for mes, g in [("anual", m)] + list(m.groupby(fechas.dt.month)):
        filas.append({"prueba": "terraclimate", "serie": "terraclimate_pet", "base": "mensual", "mes": mes,
                      **metricas(g["eto"], g["pet"])})
    return pd.DataFrame(filas)


def tabla_dispersion(pruebas):
    por_mes = pruebas[pruebas["mes"] != "anual"].copy()
    por_mes["mes"] = por_mes["mes"].astype(int)
    sesgo = por_mes.pivot(index="mes", columns="serie", values="sesgo_pct")
    razon = por_mes.pivot(index="mes", columns="serie", values="referencia_mm_dia") / \
        por_mes.pivot(index="mes", columns="serie", values="eto_nuestra_mm_dia")
    estaciones = [c for c in sesgo.columns if c.startswith("estacion_")]
    salida = sesgo.add_prefix("sesgo_pct_")
    salida["sesgo_pct_media_estaciones"] = sesgo[estaciones].mean(axis=1)
    salida["rango_4_series_pct"] = sesgo.max(axis=1) - sesgo.min(axis=1)
    salida["rango_2_pruebas_pct"] = (sesgo["terraclimate_pet"] - sesgo[estaciones].mean(axis=1)).abs()
    salida["desv_est_4_series_pct"] = sesgo.std(axis=1, ddof=1)
    salida["dispersion_pct"] = salida["rango_2_pruebas_pct"]   # definición final
    salida["banda_referencia_sobre_nuestra_min"] = razon.min(axis=1)
    salida["banda_referencia_sobre_nuestra_max"] = razon.max(axis=1)
    return salida


def tabla_balance():
    eto = pd.read_csv(ETO_CUENCA)[["mes", "eto_mm_mes"]]
    balance = pd.read_csv(BALANCE_MENSUAL).merge(eto, on="mes")
    assert len(balance) == 300
    filas = []
    # Camino «ciclo»: meses con Q
    con_q = balance[balance["Q"].notna()].copy()
    mes_cal = pd.to_datetime(con_q["mes"]).dt.month
    ciclo = con_q.groupby(mes_cal)[["PI", "PL", "Q", "eto_mm_mes"]].mean().sum()
    filas.append({"camino": "ciclo anual medio, meses con Q", "n": len(con_q), "unidad_n": "meses",
                  "eto_mm_anio": ciclo["eto_mm_mes"], "p_menos_q_PI_mm_anio": ciclo["PI"] - ciclo["Q"],
                  "p_menos_q_PL_mm_anio": ciclo["PL"] - ciclo["Q"]})
    # Camino «años»: los años completos de Q de 15
    anual = pd.read_csv(BALANCE_ANUAL)
    balance["anio"] = pd.to_datetime(balance["mes"]).dt.year
    eto_anual = balance.groupby("anio")["eto_mm_mes"].sum()
    anios = anual["anio"].tolist()
    filas.append({"camino": "años completos de Q", "n": len(anios), "unidad_n": "años",
                  "eto_mm_anio": eto_anual.loc[anios].mean(), "p_menos_q_PI_mm_anio": anual["ETR_PI"].mean(),
                  "p_menos_q_PL_mm_anio": anual["ETR_PL"].mean()})
    salida = pd.DataFrame(filas)
    for p in ["PI", "PL"]:
        salida[f"eto_menos_p_menos_q_{p}_mm_anio"] = salida["eto_mm_anio"] - salida[f"p_menos_q_{p}_mm_anio"]
        salida[f"p_menos_q_sobre_eto_{p}"] = salida[f"p_menos_q_{p}_mm_anio"] / salida["eto_mm_anio"]
    # Años sueltos: cuántos tienen P − Q > ETo
    por_anio = anual.set_index("anio")[["ETR_PI", "ETR_PL"]].assign(eto=eto_anual.loc[anios])
    for p in ["PI", "PL"]:
        salida[f"anios_con_p_menos_q_mayor_que_eto_{p}"] = int((por_anio[f"ETR_{p}"] > por_anio["eto"]).sum())
    return salida, por_anio


def main():
    pruebas = tabla_pruebas()
    dispersion = tabla_dispersion(pruebas)
    balance, por_anio = tabla_balance()
    pruebas.round(4).to_csv(SALIDA_PRUEBAS, index=False)
    dispersion.round(4).to_csv(SALIDA_DISPERSION)
    balance.round(2).to_csv(SALIDA_BALANCE, index=False)

    pd.set_option("display.width", 220)
    print(pruebas[pruebas["mes"] == "anual"].round(3).to_string(index=False))
    print(dispersion.round(2).to_string())
    print(dispersion.mean().round(2).to_string())
    print(balance.round(1).T.to_string())
    print(por_anio.round(0).to_string())
    for ruta in (SALIDA_PRUEBAS, SALIDA_DISPERSION, SALIDA_BALANCE):
        print(f"Listo: {ruta.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
