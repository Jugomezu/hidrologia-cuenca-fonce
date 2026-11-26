#!/usr/bin/env python3
"""Hietogramas de bloques alternos e hidrogramas NRCS de la microcuenca del DEM.

Requiere numpy, pandas y matplotlib. Usa la misma cuenca y los mismos
parámetros que el Problema A: área, longitud y desnivel de 05a (DEM) y C, CN y
tc de 05b. Por eso se corre después de 05a y 05b. Antes era 04 y usaba una
cuenca representativa supuesta (1.85 km², tc 35 min, C 0.52), anterior al DEM.
Las rutas se resuelven relativas a este proyecto.
"""
from pathlib import Path
import json
import math
import warnings

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRODUCTS = ROOT / "productos" / "punto2"
META_DEM = ROOT / "datos" / "punto2" / "metadatos_microcuenca.json"
PROBLEM_A = PRODUCTS / "problemaA_alcantarilla.csv"
PARAMS_IDF = PRODUCTS / "parametros_idf.csv"
IDF_TABLE = PRODUCTS / "tabla_idf_completa.csv"
OUT_HIET = PRODUCTS / "hietogramas_bloques_alternos.csv"
OUT_RESULTS = PRODUCTS / "resultados_diseno_hidrologico.csv"
OUT_HYDRO = PRODUCTS / "hidrogramas_diseno.csv"
OUT_TC = PRODUCTS / "tiempos_concentracion.csv"
OUT_BASIN = PRODUCTS / "parametros_cuenca.csv"
FIG_HIET = PRODUCTS / "fig4_hietograma_lluvia_efectiva.png"
FIG_HYDRO = PRODUCTS / "fig4_hidrogramas_diseno.png"
FIG_QP = PRODUCTS / "fig4_caudales_pico_incertidumbre.png"


def _leer_cuenca():
    """Geometría del DEM (05a) y diseño nominal del Problema A (05b)."""
    for ruta in (META_DEM, PROBLEM_A):
        if not ruta.is_file():
            raise FileNotFoundError(f"Falta {ruta.relative_to(ROOT)}; corra antes 05a y 05b.")
    meta = json.loads(META_DEM.read_text(encoding="utf-8"))
    tabla = pd.read_csv(PROBLEM_A, encoding="utf-8-sig", low_memory=False)
    diseno = tabla[tabla["record_type"].eq("diseño_nominal")].iloc[0]
    return meta, diseno


_META, _DISENO_A = _leer_cuenca()
AREA_KM2 = float(_META["area_km2"])
L_M = float(_META["main_channel_length_m"])
DELTA_H_M = float(_META["elevation_max_m"]) - float(_META["outlet_elevation_m"])
SLOPE = float(_META["relief_slope_S0_m_per_m"])
CN_II = float(_DISENO_A["CN_II_reference"])
C_BASE = float(_DISENO_A["C_weighted"])
TC_DESIGN_MIN = float(_DISENO_A["tc_design_min"])
DELTA_T_MIN = 5.0
DESIGN_DURATION_H = 2.0
RETURN_PERIODS = (10, 25, 50, 100)
AMC_NAMES = ("AMC-I", "AMC-II", "AMC-III")
IA_FRACTIONS = (0.20, 0.05)
# Factor de frecuencia de C: 1 en todos los T (decisión de Juan, 26 nov). Así el racional de esta sección usa el
# mismo C = 0.495 del Problema A y no aparecen dos caudales de T = 50 para la misma cuenca.
CF_BY_T = {10: 1.00, 25: 1.00, 50: 1.00, 100: 1.00}


def tc_estimates():
    """Las mismas estimaciones de tc del Problema A (05b), sin recalcularlas aparte."""
    d = _DISENO_A
    return [
        {"metodo": "Kirpich (cauce completo)", "tc_min": float(d["Kirpich_min"]),
         "interpretacion": "Solo tránsito por el cauce; valor bajo frente a los demás."},
        {"metodo": "Témez", "tc_min": float(d["Temez_min"]),
         "interpretacion": "Estimación empírica con L en km y S en m/m."},
        {"metodo": "Kerby-Hathaway (lámina + cauce)", "tc_min": float(d["Kerby_Hathaway_combined_min"]),
         "interpretacion": "Suma el flujo laminar inicial (Kerby) y el cauce (Kirpich)."},
        {"metodo": "NRCS-SCS Lag", "tc_min": float(d["NRCS_SCS_Lag_min"]),
         "interpretacion": "Comprobación de lag de cuenca rural; la más lenta."},
    ]


def cn_by_amc():
    cn1 = CN_II / (2.281 - 0.01281 * CN_II)
    cn3 = CN_II / (0.427 + 0.00573 * CN_II)
    return {"AMC-I": cn1, "AMC-II": CN_II, "AMC-III": cn3}


def runoff_depth(cumulative_rain_mm, cn, ia_fraction):
    s = 25400.0 / cn - 254.0
    ia = ia_fraction * s
    p = np.asarray(cumulative_rain_mm, dtype=float)
    excess = np.zeros_like(p)
    mask = p > ia
    excess[mask] = (p[mask] - ia) ** 2 / (p[mask] - ia + s)
    return excess, s, ia


def idf_params():
    params = pd.read_csv(PARAMS_IDF, low_memory=False)
    if "formulacion" not in params or "Talbot-Wenzel" not in set(params.formulacion):
        raise ValueError(f"No existe fila Talbot-Wenzel en parametros_idf.csv; columnas: {list(params.columns)}")
    p = params.loc[params.formulacion.eq("Talbot-Wenzel")].iloc[0]
    a, m, b, c = (float(p[k]) for k in ("a", "m", "b_h", "c"))
    if b <= 0:
        raise ValueError("El modelo Talbot-Wenzel debe tener desplazamiento b_h > 0.")
    return a, m, b, c


def read_idf_table():
    table = pd.read_csv(IDF_TABLE, low_memory=False)
    needed = {"duration_min", "return_period_y", "intensity_mmh", "ci95_low_mmh", "ci95_high_mmh"}
    if not needed.issubset(table.columns):
        raise ValueError(f"Columnas inesperadas en tabla_idf_completa.csv: {list(table.columns)}")
    print("Columnas parámetros IDF:", list(pd.read_csv(PARAMS_IDF, nrows=0).columns))
    print("Columnas tabla IDF:", list(table.columns))
    return table


def intensity_from_params(duration_h, return_period, pars):
    a, m, b, c = pars
    return a * return_period ** m / (duration_h + b) ** c


def idf_row_at(table, minutes, T):
    rows = table[table.return_period_y.eq(T)].sort_values("duration_min")
    if rows.empty:
        raise ValueError(f"No hay banda IDF para T={T}.")
    x = rows.duration_min.to_numpy(float)
    def interpolate(col):
        vals = rows[col].to_numpy(float)
        # Log-log interpolation keeps intensities positive and smooth.
        return float(np.exp(np.interp(np.log(minutes), np.log(x), np.log(vals))))
    return {key: interpolate(key) for key in ("intensity_mmh", "ci95_low_mmh", "ci95_high_mmh")}


def storm_depth_curve(duration_h, T, pars, idf_table):
    n = int(round(duration_h * 60 / DELTA_T_MIN))
    elapsed_min = np.arange(1, n + 1, dtype=float) * DELTA_T_MIN
    # Use exact official table values where available; fill intervening 5-min
    # durations from the Talbot-Wenzel curve fitted to the same IDF table.
    cum_depth = []
    exact = idf_table[idf_table.return_period_y.eq(T)].set_index("duration_min")
    for dm in elapsed_min:
        if int(dm) in exact.index:
            i = float(exact.loc[int(dm), "intensity_mmh"])
        else:
            i = float(intensity_from_params(dm / 60, T, pars))
        cum_depth.append(i * dm / 60)
    cum_depth = np.maximum.accumulate(np.asarray(cum_depth, dtype=float))
    incremental = np.diff(np.r_[0.0, cum_depth])
    # Alternating-block placement: largest increment at the center, then
    # alternately immediately before/after it.
    order = np.argsort(incremental)[::-1]
    nblocks = len(incremental)
    center = nblocks // 2
    positions = [center]
    offset = 1
    while len(positions) < nblocks:
        if center - offset >= 0:
            positions.append(center - offset)
        if center + offset < nblocks:
            positions.append(center + offset)
        offset += 1
    rainfall = np.zeros(nblocks, dtype=float)
    for rank, pos in enumerate(positions):
        rainfall[pos] = incremental[order[rank]]
    return rainfall, cum_depth


def scs_unit_hydrograph(excess_mm, tp_h, duration_min=DELTA_T_MIN):
    # NRCS dimensionless UH ordinates (NEH-4 / NEH Part 630, Ch.16, PRF 484).
    t_ratio = np.array([0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1, 1.1, 1.2, 1.3,
                        1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.2, 2.4, 2.6, 2.8,
                        3, 3.2, 3.4, 3.6, 3.8, 4, 4.5, 5])
    q_ratio = np.array([0, .03, .10, .19, .31, .47, .66, .82, .93, .99, 1, .99, .93,
                        .86, .78, .68, .56, .46, .39, .33, .28, .207, .147, .107,
                        .077, .055, .04, .029, .021, .015, .011, .005, 0])
    tp_min = tp_h * 60
    qpeak_per_mm = 0.208 * AREA_KM2 / tp_h  # m3/s per mm of excess
    dt_h = duration_min / 60
    n_rain = len(excess_mm)
    end_h = n_rain * dt_h + 5 * tp_h
    time_h = np.arange(0, end_h + dt_h / 2, dt_h)
    centers_h = (np.arange(n_rain) + .5) * dt_h
    q = np.zeros_like(time_h)
    for j, depth in enumerate(excess_mm):
        if depth <= 0:
            continue
        lag = (time_h - centers_h[j]) / tp_h
        ordinates = np.interp(lag, t_ratio, q_ratio, left=0.0, right=0.0)
        q += float(depth) * qpeak_per_mm * ordinates
    return time_h, q, qpeak_per_mm, tp_min


def run_scenario(rainfall, T, duration_h, amc, ia_fraction, cn, scale=1.0):
    rain = np.asarray(rainfall, dtype=float) * scale
    cum_rain = np.cumsum(rain)
    cum_excess, s_mm, ia_mm = runoff_depth(cum_rain, cn, ia_fraction)
    d_excess = np.maximum(0, np.diff(np.r_[0, cum_excess]))
    tc_h = TC_DESIGN_MIN / 60
    tp_h = (DELTA_T_MIN / 2) / 60 + 0.6 * tc_h
    time_h, q, qpeak_unit, tp_min = scs_unit_hydrograph(d_excess, tp_h)
    dt_seconds = DELTA_T_MIN * 60
    volume = float(np.trapezoid(q, dx=dt_seconds))
    volume_cn = float(cum_excess[-1] * AREA_KM2 * 1000)
    qp = float(np.max(q))
    return {"T": T, "duration_h": duration_h, "AMC": amc, "Ia_fraction": ia_fraction,
            "CN": cn, "S_mm": s_mm, "Ia_mm": ia_mm, "rain_depth_mm": float(cum_rain[-1]),
            "effective_depth_mm": float(cum_excess[-1]), "effective_blocks": d_excess,
            "Qp_scs_m3s": qp, "Ve_scs_m3": volume, "Ve_CN_m3": volume_cn,
            "volume_error_pct": 100 * (volume - volume_cn) / volume_cn if volume_cn else 0.0,
            "time_h": time_h, "hydrograph": q, "tp_min": tp_min,
            "unit_hydrograph_qp_per_mm": qpeak_unit}


def make_figures(hyetogram_df, results_df, hydrographs, tc_df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 150, "axes.grid": True, "grid.alpha": .22,
                         "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    selected = hyetogram_df[(hyetogram_df["T"] == 50) & (hyetogram_df["duration_h"] == 2) &
                            (hyetogram_df.AMC == "AMC-II") & (hyetogram_df.Ia_fraction == .2)].sort_values("interval")
    fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    x = selected.interval_start_min + DELTA_T_MIN / 2
    ax.bar(x, selected.rainfall_increment_mm, width=4.5, color="#7aa6c2", label="Lluvia total")
    ax.bar(x, selected.loss_increment_mm, width=3.2, color="#dfaa58", label="Abstracción del intervalo")
    ax.bar(x, selected.effective_increment_mm, width=2.0, color="#16836b", label="Lluvia efectiva")
    ax.set(xlabel="Tiempo desde inicio (min)", ylabel="Lámina por intervalo (mm)",
           title="Bloques alternos y lluvia efectiva · T=50 años, D=2 h, AMC-II")
    ax.legend(frameon=False, ncol=3)
    fig.savefig(FIG_HIET, bbox_inches="tight"); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    colors = {10: "#5067a5", 25: "#16836b", 50: "#d27b30", 100: "#9a4d72"}
    for T in RETURN_PERIODS:
        key = (T, 2.0, "AMC-II", .2)
        item = hydrographs[key]
        axes[0].plot(item["time_h"] * 60, item["hydrograph"], label=f"T={T} años", color=colors[T])
    axes[0].set(title="Duración de tormenta 2 h · AMC-II", xlabel="Tiempo (min)", ylabel="Q (m³/s)")
    for amc, color in zip(AMC_NAMES, ("#7284ba", "#16836b", "#c04444")):
        item = hydrographs[(50, 2.0, amc, .2)]
        axes[1].plot(item["time_h"] * 60, item["hydrograph"], label=amc, color=color)
    axes[1].set(title="Sensibilidad AMC · T=50 años", xlabel="Tiempo (min)")
    axes[1].legend(frameon=False)
    fig.suptitle("Hidrogramas NRCS-UH por convolución de lluvia efectiva")
    fig.savefig(FIG_HYDRO, bbox_inches="tight"); plt.close(fig)

    base = results_df[(results_df.scenario_type == "diseño") & (results_df.duration_h == 2.0) &
                      (results_df.AMC == "AMC-II") & (results_df.Ia_fraction == .2)].sort_values("T")
    sens = results_df[(results_df["T"] == 50) &
                      (results_df["AMC"] == "AMC-II") &
                      np.isclose(results_df["Ia_fraction"], 0.2)].sort_values("duration_h")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    x = np.arange(len(base))
    axes[0].errorbar(x - .1, base.Qp_rational_m3s, yerr=[base.Qp_rational_m3s - base.Qp_rational_low95_m3s,
                                                          base.Qp_rational_high95_m3s - base.Qp_rational_m3s],
                     fmt="o", capsize=3, label="Racional")
    axes[0].errorbar(x + .1, base.Qp_scs_m3s, yerr=[base.Qp_scs_m3s - base.Qp_scs_low95_m3s,
                                                    base.Qp_scs_high95_m3s - base.Qp_scs_m3s],
                     fmt="s", capsize=3, label="NRCS-UH")
    axes[0].set(xticks=x, xticklabels=[str(t) for t in base.T], xlabel="T (años)", ylabel="Qp (m³/s)",
                title="Qp e incertidumbre IDF 95%")
    axes[0].legend(frameon=False)
    axes[1].plot(sens.duration_h, sens.Qp_scs_m3s, "o-", label="NRCS-UH, AMC-II")
    axes[1].fill_between(sens.duration_h.to_numpy(float), sens.Qp_scs_low95_m3s.to_numpy(float),
                         sens.Qp_scs_high95_m3s.to_numpy(float), alpha=.18)
    axes[1].set(xlabel="Duración D (h)", ylabel="Qp (m³/s)", title="Sensibilidad a D · T=50 años")
    fig.savefig(FIG_QP, bbox_inches="tight"); plt.close(fig)


def main():
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    pars = idf_params()
    idf_table = read_idf_table()
    print(f"Talbot-Wenzel: a={pars[0]:.6g}, m={pars[1]:.6g}, b={pars[2]:.6g} h, c={pars[3]:.6g}")

    estimates = tc_estimates()
    tc_df = pd.DataFrame(estimates)
    # tc adoptado = el del Problema A (05b), con su misma justificación.
    tc_df["adopted_design"] = False
    tc_design = TC_DESIGN_MIN
    dt_check = DELTA_T_MIN <= tc_design / 5
    tc_df = pd.concat([tc_df, pd.DataFrame([{"metodo": "Diseño adoptado", "tc_min": tc_design,
                                             "interpretacion": str(_DISENO_A["tc_selection_note"]),
                                             "adopted_design": True}])], ignore_index=True)
    tc_df.to_csv(OUT_TC, index=False, float_format="%.6f", encoding="utf-8")
    pd.DataFrame([
        {"parametro": "Área", "valor": AREA_KM2, "unidad": "km² (DEM, 05a)"},
        {"parametro": "Longitud del cauce principal", "valor": L_M, "unidad": "m"},
        {"parametro": "Diferencia de cotas", "valor": DELTA_H_M, "unidad": "m"},
        {"parametro": "Pendiente S0", "valor": SLOPE, "unidad": "m/m"},
        {"parametro": "Coeficiente racional base C", "valor": C_BASE, "unidad": "adimensional"},
        {"parametro": "Curve Number AMC-II", "valor": CN_II, "unidad": "adimensional"},
        {"parametro": "Paso de tiempo", "valor": DELTA_T_MIN, "unidad": "min"},
        {"parametro": "tc adoptado", "valor": TC_DESIGN_MIN, "unidad": "min"},
    ]).to_csv(OUT_BASIN, index=False, encoding="utf-8")
    print("Estimaciones de tc (min):", tc_df[["metodo", "tc_min"]].to_dict("records"))
    print(f"Paso Δt={DELTA_T_MIN:g} min; tc/5={tc_design/5:.2f} min; cumple: {dt_check}")
    if not dt_check:
        raise ValueError("Δt debe ser <= tc/5.")

    cn_amc = cn_by_amc()
    print("CN por condición antecedente:", cn_amc)
    tc_row = idf_row_at(idf_table, tc_design, 10)
    # tc intensity from Talbot-Wenzel central estimate; CI log-interpolated from
    # the fitted hourly/subhourly master table (at tc).
    i_tc = {T: intensity_from_params(tc_design / 60, T, pars) for T in RETURN_PERIODS}
    ci_tc = {T: idf_row_at(idf_table, tc_design, T) for T in RETURN_PERIODS}
    cf_note = "Sin factor de frecuencia (C_f = 1): mismo C del Problema A."

    storms = {(T, 2.0) for T in RETURN_PERIODS}
    storms.update((50, d) for d in (1.0, 3.0, 6.0))
    rainfall_by_storm = {}
    cumulative_by_storm = {}
    for T, duration in sorted(storms):
        rain, cum = storm_depth_curve(duration, T, pars, idf_table)
        rainfall_by_storm[(T, duration)] = rain
        cumulative_by_storm[(T, duration)] = cum

    hietogram_rows, result_rows = [], []
    hydrographs = {}
    for T, duration in sorted(storms):
        rain = rainfall_by_storm[(T, duration)]
        cum_rain = np.cumsum(rain)
        midpoints = (np.arange(len(rain)) + .5) * DELTA_T_MIN
        idf_depth = idf_row_at(idf_table, duration * 60, T)
        central_depth = float(intensity_from_params(duration, T, pars) * duration)
        # Scale the entire ABM pattern by the 95% IDF depth bounds for first-order
        # uncertainty propagation through the nonlinear CN loss and UH model.
        low_scale = min(idf_depth["ci95_low_mmh"] * duration / central_depth, 1.0)
        high_scale = max(idf_depth["ci95_high_mmh"] * duration / central_depth, 1.0)
        for amc in AMC_NAMES:
            cn = cn_amc[amc]
            for ia_fraction in IA_FRACTIONS:
                pe, s, ia = runoff_depth(cum_rain, cn, ia_fraction)
                dpe = np.maximum(0, np.diff(np.r_[0, pe]))
                losses = np.maximum(0, rain - dpe)
                for j in range(len(rain)):
                    hietogram_rows.append({"T": T, "duration_h": duration, "AMC": amc,
                        "Ia_fraction": ia_fraction, "CN": cn, "S_mm": s, "Ia_mm": ia,
                        "interval": j + 1, "interval_start_min": j * DELTA_T_MIN,
                        "interval_end_min": (j + 1) * DELTA_T_MIN,
                        "rainfall_increment_mm": rain[j], "cumulative_rain_mm": cum_rain[j],
                        "loss_increment_mm": losses[j], "effective_cumulative_mm": pe[j],
                        "effective_increment_mm": dpe[j]})
                nominal = run_scenario(rain, T, duration, amc, ia_fraction, cn)
                low_run = run_scenario(rain, T, duration, amc, ia_fraction, cn, scale=low_scale)
                high_run = run_scenario(rain, T, duration, amc, ia_fraction, cn, scale=high_scale)
                rational_c = min(C_BASE * CF_BY_T[T], 1.0)
                qrat = .278 * rational_c * i_tc[T] * AREA_KM2
                qrat_lo = .278 * rational_c * ci_tc[T]["ci95_low_mmh"] * AREA_KM2
                qrat_hi = .278 * rational_c * ci_tc[T]["ci95_high_mmh"] * AREA_KM2
                # Rational runoff volume is C_eff times total rainfall depth over D.
                pdepth = central_depth
                v_rat = rational_c * pdepth * AREA_KM2 * 1000
                p_low = idf_depth["ci95_low_mmh"] * duration
                p_high = idf_depth["ci95_high_mmh"] * duration
                v_rat_low = rational_c * p_low * AREA_KM2 * 1000
                v_rat_high = rational_c * p_high * AREA_KM2 * 1000
                scenario_type = "diseño" if duration == DESIGN_DURATION_H else "sensibilidad_D"
                result_rows.append({"scenario_type": scenario_type, "T": T, "duration_h": duration,
                    "AMC": amc, "Ia_fraction": ia_fraction, "CN": cn, "S_mm": nominal["S_mm"],
                    "Ia_mm": nominal["Ia_mm"], "rain_depth_mm": nominal["rain_depth_mm"],
                    "effective_depth_mm": nominal["effective_depth_mm"],
                    "Qp_rational_m3s": qrat, "Qp_rational_low95_m3s": qrat_lo,
                    "Qp_rational_high95_m3s": qrat_hi, "Ve_rational_m3": v_rat,
                    "Ve_rational_low95_m3": v_rat_low, "Ve_rational_high95_m3": v_rat_high,
                    "Qp_scs_m3s": nominal["Qp_scs_m3s"], "Qp_scs_low95_m3s": min(low_run["Qp_scs_m3s"], nominal["Qp_scs_m3s"]),
                    "Qp_scs_high95_m3s": max(high_run["Qp_scs_m3s"], nominal["Qp_scs_m3s"]),
                    "Ve_scs_m3": nominal["Ve_scs_m3"], "Ve_scs_low95_m3": low_run["Ve_scs_m3"],
                    "Ve_scs_high95_m3": high_run["Ve_scs_m3"], "Ve_CN_m3": nominal["Ve_CN_m3"],
                    "volume_error_pct": nominal["volume_error_pct"], "tc_design_min": TC_DESIGN_MIN,
                    "dt_min": DELTA_T_MIN, "tp_min": nominal["tp_min"], "Cf": CF_BY_T[T],
                    "Cf_assumption": cf_note, "idf_uncertainty": "bootstrap 95%; common storm scaling for SCS"})
                if ia_fraction == .2 and duration == DESIGN_DURATION_H:
                    hydrographs[(T, duration, amc, ia_fraction)] = nominal
                if T == 50 and amc == "AMC-II" and ia_fraction == .2:
                    hydrographs[(T, duration, amc, ia_fraction)] = nominal

    hdf = pd.DataFrame(hietogram_rows)
    rdf = pd.DataFrame(result_rows)
    hdf.to_csv(OUT_HIET, index=False, float_format="%.8g", encoding="utf-8")
    rdf.to_csv(OUT_RESULTS, index=False, float_format="%.8g", encoding="utf-8")
    # Keep only representative response hydrographs needed in the report/plots.
    hydro_rows = []
    for key, obj in hydrographs.items():
        T, duration, amc, ia_fraction = key
        for t, q in zip(obj["time_h"], obj["hydrograph"]):
            hydro_rows.append({"T": T, "duration_h": duration, "AMC": amc,
                               "Ia_fraction": ia_fraction, "time_min": t * 60, "Q_m3s": q})
    pd.DataFrame(hydro_rows).to_csv(OUT_HYDRO, index=False, float_format="%.8g", encoding="utf-8")
    make_figures(hdf, rdf, hydrographs, tc_df)

    # Diagnostic water balance and scenario summary.
    print(f"Cuenca DEM: A={AREA_KM2:.4f} km², L={L_M:.1f} m, ΔH={DELTA_H_M:.2f} m, S0={SLOPE:.5f} m/m; "
          f"C={C_BASE:.3f}; CNII={CN_II:g}; tc={TC_DESIGN_MIN:g} min (mismos del Problema A).")
    print(f"Δt={DELTA_T_MIN:g} min <= tc/5={TC_DESIGN_MIN/5:.1f} min.")
    print("Número de hietogramas de diseño y sensibilidad:", len(storms))
    print("Errores de balance volumétrico UH (%), rango:", float(rdf.volume_error_pct.min()), float(rdf.volume_error_pct.max()))
    print("Duración que maximiza Qp en T=50, AMC-II, Ia=0.2S:")
    sens = rdf[(rdf["T"] == 50) & (rdf["AMC"] == "AMC-II") &
               np.isclose(rdf["Ia_fraction"], 0.2)].sort_values("duration_h")
    print(sens[["duration_h", "Qp_scs_m3s", "Ve_scs_m3"]].to_string(index=False))
    print(f"Tablas: {OUT_HIET}, {OUT_RESULTS}, {OUT_HYDRO}, {OUT_TC}, {OUT_BASIN}")
    print(f"Figuras: {FIG_HIET}, {FIG_HYDRO}, {FIG_QP}")


if __name__ == "__main__":
    main()
