#!/usr/bin/env python3
"""Cifras del punto 2 que cita el informe LaTeX (recomendación de diseño).

Lee los CSV de productos/punto2/ que escriben 05b y 05c y escribe macros de LaTeX en
productos/punto2/tablas_informe/cifras_punto2.tex, para que ningún número del texto se escriba a mano.
Los assert protegen lo que el texto afirma con palabras (por ejemplo, que el tubo nominal no cubre la sensibilidad).

Correr desde la carpeta de la entrega, después de 05b y 05c:
    python codigo/punto2/06_cifras_informe.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PRODUCTOS = RAIZ / "productos" / "punto2"
SALIDA = PRODUCTOS / "tablas_informe" / "cifras_punto2.tex"


def numero(valor: float, decimales: int) -> str:
    """Punto decimal y espacio fino de LaTeX para los miles (2\\,098.85)."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "\\,")


def main() -> None:
    diseno = pd.read_csv(PRODUCTOS / "problemaA_alcantarilla.csv").iloc[0]
    sensibilidad = pd.read_csv(PRODUCTOS / "problemaA_sensibilidad.csv")
    tanque = pd.read_csv(PRODUCTOS / "problemaB_tanque_detencion.csv")
    montecarlo = pd.read_csv(PRODUCTOS / "problemaA_montecarlo.csv")

    escenarios = sensibilidad[sensibilidad.record_type.eq("escenario") & sensibilidad.factor.ne("Referencia")]
    # Diámetro requerido más alto de cada factor: el texto nombra los que pasan del tubo nominal.
    maximo_por_factor = escenarios.groupby("factor").D_required_mm.max()
    d_nominal = float(diseno.D_commercial_mm)
    factores_que_exceden = maximo_por_factor[maximo_por_factor > d_nominal]

    # Lo que el texto afirma con palabras.
    assert float(diseno.D_recommended_mm) > d_nominal, "el recomendado debe ser mayor que el nominal"
    assert float(diseno.D_recommended_mm) >= float(diseno.D_required_max_sensitivity_mm)
    assert set(factores_que_exceden.index) == {"Tiempo de concentración", "IC95% IDF", "Coeficiente C"}, \
        f"cambió qué factores pasan de {d_nominal:.0f} mm: {list(factores_que_exceden.index)}"
    caso_tc = escenarios[escenarios.factor.eq("Tiempo de concentración")].sort_values("D_required_mm").iloc[-1]
    assert caso_tc.scenario.startswith("Kirpich"), "el t_c que más pide es Kirpich"

    # Riesgo efectivo del Monte Carlo (tubo nominal): la fila de resumen que escribe 05b, la misma que cita el texto.
    resumen = montecarlo[montecarlo.record_type.eq("resumen_montecarlo")].iloc[0]
    p_efectivo = float(resumen.annual_effective_failure_probability)
    riesgo_efectivo = float(resumen.effective_risk_life_25y)

    tanque_util = float(tanque.tank_area_m2.iloc[0] * tanque.tank_hmax_m.iloc[0])
    v_peor = float(tanque.Vreq_m3.max())
    assert v_peor < tanque_util, "el tanque debe cubrir el peor patrón"

    macros = {
        "pdosQ": numero(float(diseno.Qp_rational_m3s), 2),
        "pdosDreq": numero(float(diseno.D_required_mm), 0),
        "pdosDnom": numero(d_nominal, 0),
        "pdosQcnom": numero(float(diseno.Qc_full_m3s), 2),
        "pdosFSnom": numero(float(diseno.FS_nominal), 2),
        "pdosDmaxSens": numero(float(diseno.D_required_max_sensitivity_mm), 0),
        "pdosTcKirpich": numero(float(caso_tc.tc_min), 1),
        "pdosDidfAlta": numero(float(maximo_por_factor["IC95% IDF"]), 0),
        "pdosDcAlto": numero(float(maximo_por_factor["Coeficiente C"]), 0),
        "pdosDrec": numero(float(diseno.D_recommended_mm), 0),
        "pdosQcrec": numero(float(diseno.Qc_full_recommended_m3s), 2),
        "pdosFSrec": numero(float(diseno.FS_recommended), 2),
        "pdosRiesgoNom": numero(float(diseno.risk_at_T50_pct), 1),
        "pdosVida": numero(float(diseno.life_years), 0),
        "pdosPef": numero(100 * p_efectivo, 2),
        "pdosRiesgoEf": numero(100 * riesgo_efectivo, 1),
        "pdosVtanque": numero(tanque_util, 0),
        "pdosVpeor": numero(v_peor, 0),
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    lineas = ["% Escrito por codigo/punto2/06_cifras_informe.py; no editar a mano."]
    lineas += [f"\\newcommand{{\\{nombre}}}{{{valor}}}" for nombre, valor in macros.items()]
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Cifras del punto 2: {SALIDA.relative_to(RAIZ)}")
    for nombre, valor in macros.items():
        print(f"  {nombre} = {valor}")


if __name__ == "__main__":
    main()
