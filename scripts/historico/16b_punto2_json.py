"""Exporta las parejas mensuales PI-PL, PL-Q y PI-Q para reporte/punto2_i.html.

Ejecutar desde cualquier carpeta: python scripts/16b_punto2_json.py
Lee out/variables_mensuales.csv y escribe out/punto2_imerg_lluvia_local.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "out" / "variables_mensuales.csv"
SALIDA = RAIZ / "out" / "punto2_imerg_lluvia_local.json"


def preparar_pares(datos, columnas):
    pares = datos[["periodo", *columnas]].copy()
    for columna in columnas:
        pares[columna] = pd.to_numeric(pares[columna], errors="coerce")
    return pares.dropna(subset=columnas).sort_values("periodo").reset_index(drop=True)


def resumen(pares, columnas, unidad_x, unidad_y=None):
    resultado = {
        "periodo": {"inicio": str(pares.periodo.iloc[0]), "fin": str(pares.periodo.iloc[-1])},
        "n_pares_validos": int(len(pares)),
        "datos": [{"periodo": str(f.periodo), **{c: float(getattr(f, c)) for c in columnas}}
                  for f in pares.itertuples(index=False)],
    }
    if unidad_y is not None:
        resultado["unidad_x"] = unidad_x
        resultado["unidad_y"] = unidad_y
    if len(columnas) == 2 and len(pares) >= 2:
        x = pares[columnas[0]].to_numpy(dtype=float)
        y = pares[columnas[1]].to_numpy(dtype=float)
        if x.std() > 0 and y.std() > 0:
            resultado["correlaciones"] = {
                "pearson_r": float(pearsonr(x, y).statistic),
                "spearman_rho": float(spearmanr(x, y).statistic),
            }
        else:
            resultado["correlaciones"] = {"pearson_r": None, "spearman_rho": None}
    return resultado


def metricas_error_pi_pl(pares):
    """Calcula errores de IMERG respecto a PL, que se toma como referencia terrestre."""
    error = pares["PI"] - pares["PL"]
    return {
        "sesgo_medio_mm_mes": float(error.mean()),
        "mae_mm_mes": float(error.abs().mean()),
        "rmse_mm_mes": float((error.pow(2).mean()) ** 0.5),
    }


def metricas_prediccion(observado, estimado):
    error = estimado - observado
    return {"n": int(len(observado)), "sesgo": float(error.mean()),
            "mae": float(error.abs().mean()), "rmse": float(np.sqrt(np.mean(error ** 2)))}


def evaluar_prediccion(serie, prediccion, objetivo, nombre):
    comparacion = pd.concat([serie[objetivo].rename("observado"), prediccion.rename("estimado")], axis=1).dropna()
    if comparacion.empty:
        return None
    datos = [{"periodo": str(p), "mes": int(p.month), "observado": float(f.observado),
              "estimado": float(f.estimado), "residuo": float(f.observado - f.estimado),
              "prediccion_negativa": bool(f.estimado < 0)} for p, f in comparacion.iterrows()]
    return {"nombre": nombre, "metricas": metricas_prediccion(comparacion.observado, comparacion.estimado),
            "datos": datos, "predicciones_negativas": int((comparacion.estimado < 0).sum())}


def ajustar_ols(ajuste, variable_x, variable_y, rezago=0):
    """OLS con intercepto; el rezago opera sobre el calendario mensual completo."""
    muestra = pd.concat([ajuste[variable_x].shift(rezago).rename("x"),
                         ajuste[variable_y].rename("y")], axis=1).dropna()
    if len(muestra) < 3 or muestra.x.nunique() < 2:
        return None
    pendiente, intercepto = np.polyfit(muestra.x.to_numpy(float), muestra.y.to_numpy(float), 1)
    return {"intercepto": float(intercepto), "pendiente": float(pendiente), "n_ajuste": int(len(muestra))}


def evaluacion_fuera_muestra(datos):
    inicio, corte, fin = pd.Period("1998-01", "M"), pd.Period("2014-12", "M"), pd.Period("2022-12", "M")
    inicio_eval = pd.Period("2015-01", "M")
    serie = datos.copy()
    serie.index = pd.PeriodIndex(serie.index.astype(str), freq="M")
    serie = serie.reindex(pd.period_range(inicio, fin, freq="M"))
    ajuste, evaluacion = serie.loc[inicio:corte], serie.loc[inicio_eval:fin]
    salida = {"periodos": {"ajuste": {"inicio": str(inicio), "fin": str(corte)},
                           "evaluacion": {"inicio": str(inicio_eval), "fin": str(fin)}},
              "definiciones": {"sesgo": "estimado menos observado; positivo indica sobreestimación",
                               "residuo": "observado menos estimado",
                               "predicciones_negativas": "se conservan y se cuentan; no se recortan"},
              "lluvia_local": {}, "caudal": {"modelos": {}}}
    par = ajuste[["PI", "PL"]].dropna()
    if len(par) >= 3 and par.PI.nunique() >= 2:
        pendiente, intercepto = np.polyfit(par.PI.to_numpy(float), par.PL.to_numpy(float), 1)
        pred = pd.Series(intercepto + pendiente * serie.PI, index=serie.index)
        salida["lluvia_local"] = {
            "modelo": {"coeficientes": {"intercepto": float(intercepto), "pendiente": float(pendiente), "n_ajuste": int(len(par))},
                       "ajuste": evaluar_prediccion(ajuste, pred.loc[ajuste.index], "PL", "OLS PL ~ PI"),
                       "evaluacion": evaluar_prediccion(evaluacion, pred.loc[evaluacion.index], "PL", "OLS PL ~ PI")},
            "benchmark": {"ajuste": evaluar_prediccion(ajuste, ajuste.PI, "PL", "IMERG sin corrección"),
                          "evaluacion": evaluar_prediccion(evaluacion, evaluacion.PI, "PL", "IMERG sin corrección")}}
    climatologia = ajuste.groupby(ajuste.index.month).Q.mean()
    pred_clima = pd.Series([climatologia.get(p.month, np.nan) for p in serie.index], index=serie.index)
    salida["caudal"]["climatologia_mensual_ajuste"] = {str(int(m)): float(v) for m, v in climatologia.items()}
    salida["caudal"]["benchmark"] = {
        "ajuste": evaluar_prediccion(ajuste, pred_clima.loc[ajuste.index], "Q", "Climatología mensual de Q"),
        "evaluacion": evaluar_prediccion(evaluacion, pred_clima.loc[evaluacion.index], "Q", "Climatología mensual de Q")}
    for variable in ("PL", "PI"):
        for rezago in (0, 1):
            nombre = f"{variable}_t" if rezago == 0 else f"{variable}_t-1"
            coef = ajustar_ols(ajuste, variable, "Q", rezago)
            if coef is None:
                salida["caudal"]["modelos"][nombre] = None
                continue
            x = serie[variable].shift(rezago)
            pred = pd.Series(coef["intercepto"] + coef["pendiente"] * x, index=serie.index)
            salida["caudal"]["modelos"][nombre] = {
                "coeficientes": coef,
                "ajuste": evaluar_prediccion(ajuste, pred.loc[ajuste.index], "Q", f"OLS Q ~ {nombre}"),
                "evaluacion": evaluar_prediccion(evaluacion, pred.loc[evaluacion.index], "Q", f"OLS Q ~ {nombre}")}
    return salida


def main():
    datos = pd.read_csv(ENTRADA)
    # La columna de periodo en este CSV tiene encabezado vacío.
    columna_periodo = "periodo" if "periodo" in datos.columns else datos.columns[0]
    datos = datos.rename(columns={columna_periodo: "periodo"})
    requeridas = {"periodo", "PI", "PL", "Q"}
    faltantes = requeridas.difference(datos.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas en {ENTRADA.name}: {sorted(faltantes)}")
    datos["periodo"] = datos.periodo.astype(str)
    # El Q de variables_mensuales.csv es lámina de escorrentía (mm/mes).
    # El visor y esta evaluación requieren caudal medio (m³/s); se convierte usando
    # el área del polígono del proyecto y la duración real de cada mes.
    periodos = pd.PeriodIndex(datos.periodo, freq="M")
    area_km2 = pd.read_csv(RAIZ / "out" / "shp_fonce" / "areas_cuencas.csv").set_index("gauge_id").loc[24027010, "area_km2"]
    q_mm_mes = pd.to_numeric(datos["Q"], errors="coerce")
    datos["Q"] = pd.Series(
        q_mm_mes.to_numpy(dtype=float) * float(area_km2) * 1000
        / (periodos.days_in_month.to_numpy() * 86400), index=datos.index,
    )
    serie_evaluacion = datos.set_index("periodo")[["PI", "PL", "Q"]]
    serie_evaluacion.index = pd.PeriodIndex(serie_evaluacion.index, freq="M")

    pi_pl = preparar_pares(datos, ["PI", "PL"])
    pl_q = preparar_pares(datos, ["PL", "Q"])
    pi_q = preparar_pares(datos, ["PI", "Q"])
    if pi_pl.empty or pl_q.empty or pi_q.empty:
        raise ValueError("No hay meses coincidentes válidos para los pares requeridos.")

    resultado = {
        "titulo": "IMERG vs. lluvia local",
        "fuentes": {
            "PI": "IMERG, precipitación media sobre la cuenca",
            "PL": "Promedio de la red de pluviómetros IDEAM dentro de la cuenca",
        },
        "unidad": "mm/mes",
        **resumen(pi_pl, ["PI", "PL"], "mm/mes"),
        "metricas_pi_pl": metricas_error_pi_pl(pi_pl),
        "evaluacion_fuera_muestra": evaluacion_fuera_muestra(serie_evaluacion),
        "lluvia_vs_caudal": resumen(pl_q, ["PL", "Q"], "mm/mes", "m³/s"),
        "imerg_vs_caudal": resumen(pi_q, ["PI", "Q"], "mm/mes", "m³/s"),
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PI-PL: {len(pi_pl)} pares; PL-Q: {len(pl_q)} pares; "
          f"PI-Q: {len(pi_q)} pares. Salida: {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
