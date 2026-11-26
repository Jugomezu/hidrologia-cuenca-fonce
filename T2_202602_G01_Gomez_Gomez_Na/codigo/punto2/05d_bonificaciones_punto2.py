#!/usr/bin/env python3
"""Cálculos reproducibles de las bonificaciones 2.5.1–2.5.4.

Solo consume archivos locales del proyecto y guarda los cuatro CSV solicitados.
Los costos se expresan en unidades de C0 porque el enunciado no proporciona
un costo monetario de referencia.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import genextreme, genpareto

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datos" / "punto2"
PRODUCTS = ROOT / "productos" / "punto2"

HOURLY_PATH = DATA / "precip_horaria_limpia.csv"
ANNUAL_PATH = PRODUCTS / "resumen_completitud_anual.csv"
MAXIMA_PATH = PRODUCTS / "maximos_anuales_intensidad.csv"
IDF_PARAMS_PATH = PRODUCTS / "parametros_idf.csv"
IDF_QUANTILES_PATH = PRODUCTS / "cuantiles_y_bootstrap.csv"
PROBLEM_A_MC_PATH = PRODUCTS / "problemaA_montecarlo.csv"
PROBLEM_A_PATH = PRODUCTS / "problemaA_alcantarilla.csv"

OUT_251 = PRODUCTS / "bono_251_costo_esperado.csv"
OUT_251_SENS = PRODUCTS / "bono_251_sensibilidad.csv"
OUT_252 = PRODUCTS / "bono_252_pot_langbein.csv"
OUT_253 = PRODUCTS / "bono_253_cambio_climatico.csv"
OUT_254 = PRODUCTS / "bono_254_hashimoto_crv.csv"

# Parámetros de la cuenca y de la obra: se leen del diseño nominal del
# Problema A (05b), que a su vez toma área, longitud y pendiente del DEM (05a).
# Así las bonificaciones usan exactamente la misma cuenca, tc, C e intensidad.
def _diseno_problema_a() -> pd.Series:
    if not PROBLEM_A_PATH.is_file():
        raise FileNotFoundError(f"Falta {PROBLEM_A_PATH.relative_to(ROOT)}; corra antes 05b.")
    tabla = pd.read_csv(PROBLEM_A_PATH, encoding="utf-8-sig", low_memory=False)
    return tabla[tabla["record_type"].eq("diseño_nominal")].iloc[0]


_DISENO_A = _diseno_problema_a()
AREA_KM2 = float(_DISENO_A["area_km2"])
TC_MIN = float(_DISENO_A["tc_design_min"])
C_RUNOFF = float(_DISENO_A["C_weighted"])
S0 = float(_DISENO_A["slope_S0"])
MANNING_N = float(_DISENO_A["manning_n"])
D_COM_CURRENT_M = float(_DISENO_A["D_commercial_mm"]) / 1000.0
QC_CURRENT_M3S = float(_DISENO_A["Qc_full_m3s"])
I_DISENO_A_MMH = float(_DISENO_A["idf_intensity_point_mmh"])
DESIGN_RETURN_Y = float(_DISENO_A["T_design_y"])
LIFE_Y = int(_DISENO_A["life_years"])
WEISS_1H = 1.14
COMMERCIAL_MM = np.array([600, 750, 900, 1050, 1200, 1350, 1500, 1800], dtype=float)
C0_NORMALIZED = 1.0
SEED = 42


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Falta {path.relative_to(ROOT)}")
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def idf_parameters() -> dict[str, float]:
    params = read_csv(IDF_PARAMS_PATH)
    rows = params[params["formulacion"].astype(str).str.casefold() == "talbot-wenzel"]
    if rows.empty:
        raise ValueError("No se encontró Talbot-Wenzel en parametros_idf.csv")
    row = rows.iloc[0]
    return {key: float(row[key]) for key in ("a", "m", "b_h", "c")}


def idf_i(duration_min: float, return_y: float, params: dict[str, float]) -> float:
    """Intensidad Talbot–Wenzel (mm/h) de parametros_idf.csv, sin reescalar.

    La duración se convierte explícitamente de minutos a horas. Es la misma
    curva que usa el Problema A (05b).
    """
    d_h = duration_min / 60.0
    return params["a"] * return_y**params["m"] / (d_h + params["b_h"])**params["c"]


def rational_q(intensity_mmh: float, C: float = C_RUNOFF) -> float:
    return C * intensity_mmh * AREA_KM2 / 3.6


def pipe_capacity(diameter_m: float) -> float:
    return 0.312 / MANNING_N * diameter_m ** (8.0 / 3.0) * math.sqrt(S0)


def required_diameter(q_m3s: float) -> float:
    return (MANNING_N * q_m3s / (0.312 * math.sqrt(S0))) ** (3.0 / 8.0)


def commercial_diameter(d_m: float) -> tuple[float, str]:
    choices = COMMERCIAL_MM[COMMERCIAL_MM >= d_m * 1000.0]
    if not len(choices):
        return float(COMMERCIAL_MM[-1]), ">1800 mm; usar diámetro especial" 
    return float(choices[0]), f"{choices[0]:.0f} mm"


def annual_valid_years() -> list[int]:
    annual = read_csv(ANNUAL_PATH)
    retained = annual["retained"].astype(str).str.strip().str.casefold().isin(
        {"si", "sí", "true", "1", "yes"}
    )
    years = pd.to_numeric(annual.loc[retained, "year"], errors="coerce").dropna().astype(int)
    if len(years):
        return years.tolist()
    return []


def part_251(params: dict[str, float]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    r0, n, c0 = 0.06, 25, C0_NORMALIZED
    q2 = rational_q(idf_i(TC_MIN, 2.0, params))
    grid_t = np.arange(2.0, 501.0, 1.0)
    rows = []

    def calc_for(td: float, dmax_multiplier: float, rate: float) -> dict:
        frc = rate * (1 + rate)**n / ((1 + rate)**n - 1)
        qd = rational_q(idf_i(TC_MIN, td, params))
        c_obra = c0 * (qd / q2)**0.6
        annual_cost = frc * c_obra
        dmax = dmax_multiplier * c0
        # Midpoint quadrature over annual exceedance probability p in [0,1/Td].
        count = 5000
        pmax = 1.0 / td
        p = (np.arange(count, dtype=float) + 0.5) * pmax / count
        q = np.array([rational_q(idf_i(TC_MIN, 1.0 / pi, params)) for pi in p])
        damage = np.where(q > qd, dmax * (1.0 - np.exp(-(q - qd) / (0.5 * qd))), 0.0)
        dae = float(damage.mean() * pmax)
        return {"T_d_y": td, "Q2_m3s": q2, "Q_d_m3s": qd, "C0_normalized": c0,
                "Cobra_C0_units": c_obra, "FRC_per_year": frc,
                "Canual_C0_per_year": annual_cost, "Dmax_C0_units": dmax,
                "DAE_C0_per_year": dae, "CTAE_C0_per_year": annual_cost + dae,
                "discount_rate": rate, "life_years": n, "DAE_quadrature_midpoints": count}

    for td in grid_t:
        rows.append(calc_for(float(td), 20.0, r0))
    base = pd.DataFrame(rows)
    base.to_csv(OUT_251, index=False, encoding="utf-8-sig")
    optimum = base.loc[base["CTAE_C0_per_year"].idxmin()].to_dict()

    sensitivity = []
    for dmult in (10.0, 20.0, 40.0):
        for rate in (0.03, 0.06, 0.10):
            candidates = pd.DataFrame([calc_for(float(td), dmult, rate) for td in grid_t])
            best = candidates.loc[candidates["CTAE_C0_per_year"].idxmin()].to_dict()
            best.update({"Dmax_multiplier_C0": dmult, "rate_sensitivity": rate,
                         "sensitivity_scope": "factorial: todas las combinaciones Dmax x r"})
            sensitivity.append(best)
    sens = pd.DataFrame(sensitivity)
    sens.to_csv(OUT_251_SENS, index=False, encoding="utf-8-sig")
    return base, sens, optimum


def choose_pot_threshold(hourly: pd.DataFrame, valid_years: list[int]) -> tuple[float, np.ndarray, float]:
    subset = hourly[hourly["timestamp"].dt.year.isin(valid_years)].copy()
    values = pd.to_numeric(subset["precip_mm"], errors="coerce").to_numpy(dtype=float)
    times = subset["timestamp"].to_numpy(dtype="datetime64[ns]")
    valid = np.isfinite(values) & (values >= 0)
    positive = np.unique(values[valid & (values > 0)])
    if len(positive) < 5:
        raise ValueError("No hay suficientes horas húmedas para declusterizar eventos POT.")

    valid_year_count = max(len(valid_years), 1)

    def event_peaks(threshold: float) -> np.ndarray:
        idx = np.flatnonzero(valid & (values >= threshold))
        if not len(idx):
            return np.array([], dtype=float)
        # Una nueva tormenta comienza tras al menos seis horas sin superar u.
        gaps_h = np.diff(times[idx]).astype("timedelta64[m]").astype(float) / 60.0
        starts = np.r_[0, np.flatnonzero(gaps_h > 6.0) + 1]
        ends = np.r_[starts[1:], len(idx)]
        return np.asarray([np.max(values[idx[a:b]]) for a, b in zip(starts, ends)])

    # Búsqueda monotónica del nivel que deja aproximadamente 2 eventos/año.
    low, high = 0, len(positive) - 1
    for _ in range(50):
        mid = (low + high) // 2
        rate = len(event_peaks(float(positive[mid]))) / valid_year_count
        if rate > 2.0:
            low = mid + 1
        else:
            high = mid
        if low >= high:
            break
    candidate_ids = range(max(0, low - 8), min(len(positive), high + 9))
    candidates = []
    for index in candidate_ids:
        threshold = float(positive[index])
        peaks = event_peaks(threshold)
        rate = len(peaks) / valid_year_count
        candidates.append((abs(rate - 2.0), threshold, peaks, rate))
    if not candidates:
        raise ValueError("No se pudo seleccionar el umbral POT.")
    feasible = [item for item in candidates if 1.5 <= item[3] <= 2.5]
    best = min(feasible or candidates, key=lambda item: item[0])
    return best[1], best[2], best[3]


def part_252(hourly: pd.DataFrame, valid_years: list[int], params: dict[str, float]) -> pd.DataFrame:
    threshold_raw, raw_peaks, lambda_y = choose_pot_threshold(hourly, valid_years)
    u = threshold_raw * WEISS_1H
    peaks = raw_peaks * WEISS_1H
    excess = peaks - u
    excess = excess[excess > 1e-10]
    if len(excess) < 10:
        raise ValueError(f"Solo hay {len(excess)} excedencias POT sobre u; ajuste inestable.")
    shape_xi, loc, scale = genpareto.fit(excess, floc=0.0)
    annual_max = read_csv(MAXIMA_PATH)
    annual_max["hydro_year"] = pd.to_numeric(annual_max["hydro_year"], errors="coerce")
    annual_max["intensity_1h_mmh"] = pd.to_numeric(annual_max["intensity_1h_mmh"], errors="coerce")
    annual_max = annual_max[annual_max["hydro_year"].isin(valid_years)]
    lp3 = read_csv(IDF_QUANTILES_PATH)
    lp3["duration_h"] = pd.to_numeric(lp3["duration_h"], errors="coerce")
    lp3["return_period_y"] = pd.to_numeric(lp3["return_period_y"], errors="coerce")
    lp3_rows = lp3[(lp3["distribution"].astype(str).str.upper() == "LP3") &
                   (lp3["method"].astype(str).str.upper() == "LMOM") &
                   np.isclose(lp3["duration_h"], 1.0)]
    rows = []
    for t_ams in (2, 5, 10, 25, 50, 100):
        t_event = -1.0 / math.log(1.0 - 1.0 / t_ams)
        conditional_sf = min(1.0, max(1e-12, 1.0 / (lambda_y * t_event)))
        qpot = u + float(genpareto.isf(conditional_sf, shape_xi, loc=0.0, scale=scale))
        q_ams_row = lp3_rows[np.isclose(lp3_rows["return_period_y"], t_ams)]
        q_ams = float(q_ams_row.iloc[0]["quantile_mmh"]) if not q_ams_row.empty else np.nan
        empirical = float(annual_max["intensity_1h_mmh"].quantile(1 - 1 / t_ams)) if len(annual_max) else np.nan
        rows.append({"record_type": "cuantil_POT_Langbein", "return_period_AMS_y": t_ams,
                     "return_period_event_T_E_y": t_event, "threshold_raw_mm_h": threshold_raw,
                     "threshold_Weiss_mm_h": u, "Weiss_1h_factor": WEISS_1H,
                     "valid_years": len(valid_years), "events": len(raw_peaks),
                     "lambda_events_per_year": lambda_y, "GPD_shape_c_plus_xi": shape_xi,
                     "GPD_scale_mm_h": scale, "GPD_loc_excess_mm_h": loc,
                     "POT_quantile_mm_h": qpot, "AMS_LP3_LMOM_quantile_mm_h": q_ams,
                     "AMS_empirical_quantile_mm_h": empirical,
                     "POT_minus_AMS_LP3_mm_h": qpot - q_ams})
    rows.append({"record_type": "diagnostico_POT", "return_period_AMS_y": np.nan,
                 "return_period_event_T_E_y": np.nan, "threshold_raw_mm_h": threshold_raw,
                 "threshold_Weiss_mm_h": u, "Weiss_1h_factor": WEISS_1H,
                 "valid_years": len(valid_years), "events": len(raw_peaks),
                 "lambda_events_per_year": lambda_y, "GPD_shape_c_plus_xi": shape_xi,
                 "GPD_scale_mm_h": scale, "GPD_loc_excess_mm_h": loc,
                 "POT_quantile_mm_h": np.nan, "AMS_LP3_LMOM_quantile_mm_h": np.nan,
                 "AMS_empirical_quantile_mm_h": np.nan,
                 "POT_minus_AMS_LP3_mm_h": np.nan})
    result = pd.DataFrame(rows)
    result.to_csv(OUT_252, index=False, encoding="utf-8-sig")
    return result


def fit_nonstationary_gev(annual_max: pd.DataFrame) -> dict[str, float]:
    x = annual_max["intensity_1h_mmh"].to_numpy(dtype=float)
    years = annual_max["hydro_year"].to_numpy(dtype=float)
    keep = np.isfinite(x) & np.isfinite(years)
    x, years = x[keep], years[keep]
    t = years - float(np.mean(years))
    c0, loc0, scale0 = genextreme.fit(x)

    def objective(theta):
        c, mu0, mu1, log_scale = theta
        scale = math.exp(log_scale)
        loc = mu0 + mu1 * t
        logpdf = genextreme.logpdf(x, c, loc=loc, scale=scale)
        return float(-np.sum(logpdf)) if np.all(np.isfinite(logpdf)) else 1e100

    init = np.array([c0, loc0, 0.0, math.log(scale0)])
    fit = minimize(objective, init, method="L-BFGS-B",
                   bounds=[(-0.8, 0.8), (None, None), (-1.0, 1.0), (-5.0, 5.0)])
    if not fit.success and not np.isfinite(fit.fun):
        raise RuntimeError(f"No convergió GEV no estacionaria: {fit.message}")
    c, mu0, mu1, log_scale = fit.x
    return {"scipy_c_minus_xi": float(c), "mu0_mmh": float(mu0),
            "mu1_mmh_per_year": float(mu1), "scale_mmh": float(math.exp(log_scale)),
            "time_center_year": float(np.mean(years)), "n_ams": int(len(x)),
            "fit_converged": bool(fit.success), "negative_loglikelihood": float(fit.fun),
            "shape_xi_opposite_scipy_c": float(-c)}


def part_253(params: dict[str, float], valid_years: list[int]) -> pd.DataFrame:
    maxima = read_csv(MAXIMA_PATH)
    maxima["hydro_year"] = pd.to_numeric(maxima["hydro_year"], errors="coerce")
    maxima["intensity_1h_mmh"] = pd.to_numeric(maxima["intensity_1h_mmh"], errors="coerce")
    maxima = maxima[maxima["hydro_year"].isin(valid_years)].dropna(subset=["intensity_1h_mmh"])
    gev = fit_nonstationary_gev(maxima)
    deltas = (0.0, 1.0, 1.5, 2.0, 3.0)
    duration = TC_MIN
    i_base_tc = idf_i(duration, DESIGN_RETURN_Y, params)
    i_base_1h = idf_i(60.0, DESIGN_RETURN_Y, params)
    i_critical = 3.6 * QC_CURRENT_M3S / (C_RUNOFF * AREA_KM2)
    future_year = float(maxima["hydro_year"].max()) + LIFE_Y
    mc_summary = read_csv(PROBLEM_A_MC_PATH)
    mc_summary = mc_summary[mc_summary.get("record_type", pd.Series(dtype=str))
                            .astype(str).eq("resumen_montecarlo")]
    mc_p = float(pd.to_numeric(mc_summary.iloc[0]["annual_effective_failure_probability"], errors="coerce")) \
        if not mc_summary.empty else np.nan
    mc_t = 1.0 / mc_p if np.isfinite(mc_p) and mc_p > 0 else np.nan
    mc_risk = 1.0 - (1.0 - mc_p)**LIFE_Y if np.isfinite(mc_p) else np.nan
    # Comprobación de consistencia: la intensidad base debe ser la del Problema A.
    if not np.isclose(i_base_tc, I_DISENO_A_MMH, rtol=1e-4):
        raise ArithmeticError(f"i(tc, T={DESIGN_RETURN_Y:g}) = {i_base_tc:.3f} mm/h no coincide con el "
                              f"Problema A ({I_DISENO_A_MMH:.3f} mm/h).")
    q50_check = rational_q(i_base_tc)
    rows = []
    for delta in deltas:
        factor = 1.0 + 0.07 * delta
        ip_tc, ip_1h = factor * i_base_tc, factor * i_base_1h
        qp = rational_q(ip_tc)
        dreq = required_diameter(qp)
        dcom_mm, dcom_label = commercial_diameter(dreq)
        # Inversa de la misma curva IDF usada arriba: i(T)=i50*(T/50)^m.
        tef_idf = DESIGN_RETURN_Y * (i_critical / ip_tc) ** (1.0 / params["m"])
        p_idf = min(1.0, max(0.0, 1.0 / tef_idf))
        risk_idf = 1 - (1 - p_idf)**LIFE_Y
        # Proyecta la GEV hasta t_final+25 y aplica el factor climático a la
        # distribución. El umbral de la obra i* se mantiene fijo.
        mu_future = (gev["mu0_mmh"] + gev["mu1_mmh_per_year"] *
                     (future_year - gev["time_center_year"])) * factor
        scale_future = gev["scale_mmh"] * factor
        p_gev = float(genextreme.sf(i_critical, gev["scipy_c_minus_xi"],
                                    loc=mu_future, scale=scale_future))
        p_gev = min(1.0, max(0.0, p_gev))
        rows.append({"delta_temperature_C": delta, "Westra_scaling_pct_per_C": 7.0,
                     "intensity_factor": factor, "tc_design_min": duration,
                     "i_tc_base_T50_mmh": i_base_tc, "i_tc_future_mmh": ip_tc,
                     "i_1h_base_T50_mmh": i_base_1h, "i_1h_future_mmh": ip_1h,
                     "Qp_future_m3s": qp, "D_required_m": dreq,
                     "D_required_mm": dreq * 1000, "D_commercial_mm": dcom_mm,
                     "D_commercial_recommendation": dcom_label,
                     "Qc_current_1500mm_m3s": QC_CURRENT_M3S,
                     "i_critical_current_pipe_mmh": i_critical,
                     "baseline_Q50_m3s_at_deltaT0": q50_check,
                     "T_effective_IDF_y": tef_idf, "annual_exceedance_IDF": p_idf,
                     "risk_25y_IDF": risk_idf,
                     "GEV_scipy_c_minus_xi": gev["scipy_c_minus_xi"],
                     "GEV_shape_xi": gev["shape_xi_opposite_scipy_c"],
                     "GEV_mu0_mmh": gev["mu0_mmh"],
                     "GEV_mu1_mmh_per_year": gev["mu1_mmh_per_year"],
                     "GEV_time_center_year": gev["time_center_year"],
                     "GEV_future_evaluation_year_t_final_plus_25": future_year,
                     "GEV_mu_end_future_scaled_mmh": mu_future,
                     "GEV_scale_future_scaled_mmh": scale_future,
                     "T_effective_GEV_nonstationary_y": (1 / p_gev if p_gev > 0 else np.inf),
                     "annual_exceedance_GEV": p_gev,
                     "risk_25y_GEV": 1 - (1 - p_gev)**LIFE_Y,
                     "MC_annual_effective_failure_probability_from_ProblemaA": mc_p,
                     "MC_T_effective_y_from_ProblemaA": mc_t,
                     "MC_risk_25y_from_ProblemaA": mc_risk,
                     "GEV_n_ams": gev["n_ams"], "GEV_fit_converged": gev["fit_converged"]})
    result = pd.DataFrame(rows)
    result.to_csv(OUT_253, index=False, encoding="utf-8-sig")
    return result


def part_254(hourly: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    data = hourly[["timestamp", "precip_mm", "precip_state"]].copy()
    data["precip_mm"] = pd.to_numeric(data["precip_mm"], errors="coerce")
    data = data.sort_values("timestamp").reset_index(drop=True)
    # La ventana es tc redondeado hacia arriba a horas enteras (la serie es
    # horaria); con tc = 60 min es una hora. Se aplica el factor de Weiss.
    window_hours = max(1, int(math.ceil(TC_MIN / 60.0)))
    valid_rain = data["precip_mm"].where(np.isfinite(data["precip_mm"]) & (data["precip_mm"] >= 0))
    intensity = valid_rain.rolling(window_hours, min_periods=window_hours).mean() * WEISS_1H
    q = C_RUNOFF * AREA_KM2 / 3.6 * intensity
    times = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    valid = np.isfinite(q.to_numpy(dtype=float)) & times.notna().to_numpy()
    qv = q.to_numpy(dtype=float)[valid]
    tv = times.to_numpy()[valid]
    rows, events_for_print = [], []
    for diameter_mm in (1200.0, 1500.0, 1800.0):
        diameter_m = diameter_mm / 1000.0
        qc = QC_CURRENT_M3S if np.isclose(diameter_mm, D_COM_CURRENT_M * 1000) else pipe_capacity(diameter_m)
        failed = qv > qc
        alpha = float(1.0 - failed.mean()) if len(failed) else np.nan
        if len(failed) > 1:
            consecutive = np.diff(tv).astype("timedelta64[m]").astype(float) == 60.0
            starts_fail = failed[:-1] & consecutive
            denominator = int(starts_fail.sum())
            recovery = int((failed[:-1] & (~failed[1:]) & consecutive).sum())
            gamma = recovery / denominator if denominator else np.nan
        else:
            gamma = np.nan
        gamma_duration = 1.0 / gamma if gamma and np.isfinite(gamma) else np.inf
        fail_idx = np.flatnonzero(failed)
        event_rows = []
        if len(fail_idx):
            breaks = np.r_[0, np.flatnonzero((np.diff(fail_idx) > 1) |
                          (np.diff(tv[fail_idx]).astype("timedelta64[m]").astype(float) > 60)) + 1]
            ends = np.r_[breaks[1:], len(fail_idx)]
            for event_id, (begin, end) in enumerate(zip(breaks, ends), 1):
                ix = fail_idx[begin:end]
                peak_i = int(ix[np.argmax(qv[ix])])
                event = {"record_type": "evento_superacion", "diameter_mm": diameter_mm,
                         "Qc_m3s": qc, "event_id": event_id,
                         "start_utc": pd.Timestamp(tv[ix[0]]).isoformat(),
                         "end_utc": pd.Timestamp(tv[ix[-1]]).isoformat(),
                         "duration_hours": int(len(ix)), "peak_time_utc": pd.Timestamp(tv[peak_i]).isoformat(),
                         "peak_Q_m3s": float(qv[peak_i]),
                         "peak_excess_m3s": float(qv[peak_i] - qc),
                         "peak_excess_relative_Qc": float((qv[peak_i] - qc) / qc)}
                event_rows.append(event)
        excess = qv[failed] - qc
        summary = {"record_type": "metricas_Hashimoto_1982", "diameter_mm": diameter_mm,
                   "Qc_m3s": qc, "tc_min": TC_MIN, "hourly_resolution_used_min": 60,
                   "Weiss_1h_factor": WEISS_1H, "C": C_RUNOFF, "A_km2": AREA_KM2,
                   "S0_m_per_m": S0, "Manning_n": MANNING_N,
                   "valid_hours_evaluated": int(len(qv)), "failed_hours": int(failed.sum()),
                   "reliability_alpha": alpha, "resilience_gamma_per_hour": gamma,
                   "mean_failure_duration_1_over_gamma_hours": gamma_duration,
                   "mean_contiguous_failure_event_hours": float(np.mean([e["duration_hours"] for e in event_rows])) if event_rows else 0.0,
                   "vulnerability_mean_excess_m3s": float(np.mean(excess)) if len(excess) else 0.0,
                   "vulnerability_max_excess_m3s": float(np.max(excess)) if len(excess) else 0.0,
                   "vulnerability_mean_relative_Qc": float(np.mean(excess) / qc) if len(excess) else 0.0,
                   "vulnerability_max_relative_Qc": float(np.max(excess) / qc) if len(excess) else 0.0,
                   "historical_exceedance_events": len(event_rows),
                   "resilience_definition": "transiciones falló→cumplió / horas fallidas con siguiente hora observada"}
        rows.append(summary)
        rows.extend(event_rows)
        if diameter_mm == 1500:
            events_for_print = event_rows
    result = pd.DataFrame(rows)
    result.to_csv(OUT_254, index=False, encoding="utf-8-sig")
    return result, events_for_print


def create_bonus_figure(base: pd.DataFrame, pot: pd.DataFrame,
                        climate: pd.DataFrame, hashimoto: pd.DataFrame) -> Path:
    """Genera el resumen gráfico 2x2 de las cuatro bonificaciones."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.titleweight": "bold", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.22})
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    ax_a, ax_b, ax_c, ax_d = axes.flat

    # Panel A: costos esperados y retornos de referencia.
    base = base.sort_values("T_d_y")
    ax_a.plot(base.T_d_y, base.Canual_C0_per_year, label="Costo anualizado de obra", color="#4267ac")
    ax_a.plot(base.T_d_y, base.DAE_C0_per_year, label="DAE", color="#da8a2b")
    ax_a.plot(base.T_d_y, base.CTAE_C0_per_year, label="CTAE", color="#16836b", linewidth=2.2)
    optimum = base.loc[base.CTAE_C0_per_year.idxmin()]
    ax_a.axvline(float(optimum.T_d_y), color="#16836b", linestyle="--", label=f"Óptimo: T={optimum.T_d_y:.0f} años")
    ax_a.axvline(50, color="#ad4c4c", linestyle=":", label="Diseño: T=50 años")
    ax_a.set(xlabel="Periodo de retorno T (años)", ylabel="Costo normalizado (C₀/año)",
             title="A · 2.5.1 Costo esperado", xlim=(2, 500))
    ax_a.legend(frameon=False, fontsize=8)

    # Panel B: POT contra AMS, con Langbein expresado en años de evento.
    pot_rows = pot[pot.record_type.eq("cuantil_POT_Langbein")].sort_values("return_period_AMS_y")
    ax_b.plot(pot_rows.return_period_AMS_y, pot_rows.POT_quantile_mm_h, "o-",
              color="#16836b", label="POT-GPD + Langbein")
    ax_b.plot(pot_rows.return_period_AMS_y, pot_rows.AMS_LP3_LMOM_quantile_mm_h, "s--",
              color="#bd5b50", label="AMS LP3/L-momentos")
    ax_b.plot(pot_rows.return_period_AMS_y, pot_rows.AMS_empirical_quantile_mm_h, "^:",
              color="#5267a8", label="AMS empírico")
    ax_b.set(xscale="log", xlabel="Periodo de retorno AMS (años)", ylabel="Intensidad 1 h (mm/h)",
             title="B · 2.5.2 POT-GPD frente a AMS")
    ax_b.legend(frameon=False, fontsize=8)

    # Panel C: caudal, capacidad y degradación de los retornos efectivos.
    climate = climate.sort_values("delta_temperature_C")
    ax_c.plot(climate.delta_temperature_C, climate.Qp_future_m3s, "o-", color="#bd5b50",
              label="Caudal pico Qₚ")
    ax_c.axhline(QC_CURRENT_M3S, color="#172b3a", linestyle="--", label="Capacidad D=1500 mm")
    ax_c.set(xlabel="Calentamiento ΔT (°C)", ylabel="Caudal (m³/s)", title="C · 2.5.3 Cambio climático")
    ax_c2 = ax_c.twinx()
    ax_c2.plot(climate.delta_temperature_C, climate.T_effective_IDF_y, "s-", color="#d99a38",
               label="T efectivo IDF")
    ax_c2.plot(climate.delta_temperature_C, climate.T_effective_GEV_nonstationary_y, "^--",
               color="#5267a8", label="T efectivo GEV futura")
    ax_c2.set_ylabel("Retorno efectivo (años, escala log)")
    ax_c2.set_yscale("log")
    handles, labels = ax_c.get_legend_handles_labels()
    handles2, labels2 = ax_c2.get_legend_handles_labels()
    ax_c.legend(handles + handles2, labels + labels2, frameon=False, fontsize=7, loc="center left")

    # Panel D: hidrograma histórico cercano al 26-jul-1965 a partir del CSV
    # horario, manteniendo solo la pequeña ventana temporal necesaria.
    event_time = pd.Timestamp("1965-07-26T00:00:00Z")
    start, end = event_time - pd.Timedelta(hours=36), event_time + pd.Timedelta(hours=60)
    chunks = []
    for chunk in pd.read_csv(HOURLY_PATH, usecols=["timestamp", "precip_mm"],
                             chunksize=200_000, low_memory=False):
        ts = pd.to_datetime(chunk.timestamp, utc=True, errors="coerce")
        keep = ts.between(start, end)
        if keep.any():
            selected = chunk.loc[keep, ["precip_mm"]].copy()
            selected["timestamp"] = ts.loc[keep].to_numpy()
            chunks.append(selected)
    hydro = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["timestamp", "precip_mm"])
    if not hydro.empty:
        hydro["precip_mm"] = pd.to_numeric(hydro.precip_mm, errors="coerce")
        hydro["Q_m3s"] = hydro.precip_mm * WEISS_1H * C_RUNOFF * AREA_KM2 / 3.6
        hydro = hydro.sort_values("timestamp")
        ax_d.plot(hydro.timestamp, hydro.Q_m3s, color="#177e89", linewidth=1.6,
                  label="Hidrograma observado (1 h, Weiss=1.14)")
        peak_idx = hydro.Q_m3s.idxmax()
        peak = hydro.loc[peak_idx]
        ax_d.scatter([peak.timestamp], [peak.Q_m3s], color="#bd5b50", zorder=4)
        ax_d.annotate(f"Pico {peak.Q_m3s:.3f} m³/s\n26-jul-1965",
                      (peak.timestamp, peak.Q_m3s), xytext=(9, 10), textcoords="offset points", fontsize=8)
        ax_d.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H h", tz=mdates.UTC))
    summaries = hashimoto[hashimoto.record_type.eq("metricas_Hashimoto_1982")]
    colors = {1200.0: "#8b5aa5", 1500.0: "#d99a38", 1800.0: "#536b78"}
    for _, row in summaries.iterrows():
        ax_d.axhline(float(row.Qc_m3s), color=colors[float(row.diameter_mm)], linestyle="--",
                     label=f"Qc {row.diameter_mm:.0f} mm = {row.Qc_m3s:.2f} m³/s")
    ax_d.set(xlabel="Fecha (UTC)", ylabel="Caudal equivalente (m³/s)",
             title="D · 2.5.4 Hashimoto y evento crítico")
    ax_d.legend(frameon=False, fontsize=7, loc="upper left")
    metrics = []
    for _, row in summaries.iterrows():
        gamma = float(row.resilience_gamma_per_hour) if pd.notna(row.resilience_gamma_per_hour) else 0
        metrics.append(f"{row.diameter_mm:.0f} mm: α={float(row.reliability_alpha):.5f}, "
                       f"γ={gamma:.2f}/h, ν̄={float(row.vulnerability_mean_excess_m3s):.2f} m³/s")
    ax_d.text(0.99, 0.97, "\n".join(metrics), transform=ax_d.transAxes, ha="right", va="top",
              fontsize=7, bbox={"boxstyle": "round,pad=.35", "facecolor": "white", "alpha": .88, "edgecolor": "#ccd6dc"})

    fig.suptitle("Bonificaciones de diseño y riesgo · Denver Stapleton", fontsize=15, fontweight="bold")
    output = PRODUCTS / "fig_25_bonificaciones.png"
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


def main() -> None:
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    hourly = read_csv(HOURLY_PATH)
    hourly["timestamp"] = pd.to_datetime(hourly["timestamp"], utc=True, errors="coerce")
    hourly["precip_mm"] = pd.to_numeric(hourly["precip_mm"], errors="coerce")
    valid_years = annual_valid_years()
    if not valid_years:
        valid = hourly[np.isfinite(hourly["precip_mm"])].copy()
        valid_years = sorted(valid["timestamp"].dt.year.unique().tolist())
    params = idf_parameters()

    print("=== Bonificaciones Punto 2 · 2.5.1–2.5.4 ===")
    print(f"Serie horaria: {len(hourly):,} filas; años aceptados usados: {len(valid_years)}")
    print(f"IDF Talbot-Wenzel: a={params['a']:.6g}, m={params['m']:.6g}, b={params['b_h']:.6g} h, c={params['c']:.6g}")

    base, sensitivity, optimum = part_251(params)
    print("\n2.5.1 · Costo esperado")
    q50_anchor = rational_q(idf_i(TC_MIN, DESIGN_RETURN_Y, params))
    print(f"  Diseño del Problema A: A={AREA_KM2:.4f} km², tc={TC_MIN:.1f} min, C={C_RUNOFF:.3f}; "
          f"i(tc, T={DESIGN_RETURN_Y:g})={idf_i(TC_MIN, DESIGN_RETURN_Y, params):.2f} mm/h; "
          f"Q50={q50_anchor:.3f} m³/s.")
    print(f"  Q2={optimum['Q2_m3s']:.4f} m³/s; T óptimo={optimum['T_d_y']:.0f} años")
    print(f"  C_obra={optimum['Cobra_C0_units']:.4f} C0; C_anual={optimum['Canual_C0_per_year']:.4f} C0/año; "
          f"DAE={optimum['DAE_C0_per_year']:.4f} C0/año; CTAE={optimum['CTAE_C0_per_year']:.4f} C0/año")
    print("  Sensibilidad factorial Dmax={10,20,40} C0 × r={3%,6%,10%}:")
    print(sensitivity[["Dmax_multiplier_C0", "rate_sensitivity", "T_d_y", "CTAE_C0_per_year"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    pot = part_252(hourly, valid_years, params)
    pot_diag = pot[pot["record_type"] == "diagnostico_POT"].iloc[0]
    print("\n2.5.2 · POT/GPD y relación de Langbein")
    print(f"  Umbral u={pot_diag['threshold_Weiss_mm_h']:.3f} mm/h (Weiss 1.14); "
          f"eventos={pot_diag['events']} en {pot_diag['valid_years']} años; λ={pot_diag['lambda_events_per_year']:.3f}/año")
    print(f"  GPD scipy c=+ξ={pot_diag['GPD_shape_c_plus_xi']:.4f}, escala={pot_diag['GPD_scale_mm_h']:.3f} mm/h")
    print(pot[pot["record_type"] == "cuantil_POT_Langbein"][
        ["return_period_AMS_y", "return_period_event_T_E_y", "POT_quantile_mm_h", "AMS_LP3_LMOM_quantile_mm_h", "AMS_empirical_quantile_mm_h"]
    ].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    climate = part_253(params, valid_years)
    print("\n2.5.3 · Cambio climático +7%/°C y GEV no estacionaria")
    first = climate.iloc[0]
    print(f"  ΔT=0: Q50={first['Qp_future_m3s']:.3f} m³/s; "
          f"Dcom={first['D_commercial_recommendation']}; i*={first['i_critical_current_pipe_mmh']:.2f} mm/h; "
          f"Tef IDF={first['T_effective_IDF_y']:.2f} años.")
    print(f"  GEV evaluada en t_final+25={first['GEV_future_evaluation_year_t_final_plus_25']:.0f}; "
          f"Tef GEV={first['T_effective_GEV_nonstationary_y']:.2f} años. "
          f"Referencia MC Problema A: p={first['MC_annual_effective_failure_probability_from_ProblemaA']:.5f}, "
          f"Tef={first['MC_T_effective_y_from_ProblemaA']:.2f} años, "
          f"R25={first['MC_risk_25y_from_ProblemaA']:.2%}.")
    print(climate[["delta_temperature_C", "i_tc_future_mmh", "Qp_future_m3s", "D_required_mm",
                   "D_commercial_recommendation", "T_effective_IDF_y", "risk_25y_IDF",
                   "GEV_future_evaluation_year_t_final_plus_25",
                   "T_effective_GEV_nonstationary_y", "risk_25y_GEV"]].to_string(
                       index=False, float_format=lambda x: f"{x:.4f}"))

    hashimoto, events = part_254(hourly)
    summaries = hashimoto[hashimoto["record_type"] == "metricas_Hashimoto_1982"]
    print("\n2.5.4 · Confiabilidad, resiliencia y vulnerabilidad Hashimoto")
    print(summaries[["diameter_mm", "Qc_m3s", "valid_hours_evaluated", "failed_hours",
                     "reliability_alpha", "resilience_gamma_per_hour",
                     "mean_failure_duration_1_over_gamma_hours", "vulnerability_mean_excess_m3s",
                     "vulnerability_max_excess_m3s", "historical_exceedance_events"]].to_string(
                         index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"  Eventos históricos que superan Qc de 1500 mm: {len(events)}")
    if events:
        print(pd.DataFrame(events)[["start_utc", "end_utc", "duration_hours", "peak_Q_m3s", "peak_excess_m3s"]].to_string(
            index=False, float_format=lambda x: f"{x:.3f}"))

    figure_path = create_bonus_figure(base, pot, climate, hashimoto)
    print(f"Figura 2.5 creada: {figure_path.relative_to(ROOT)} (300 dpi)")

    for path in (OUT_251, OUT_251_SENS, OUT_252, OUT_253, OUT_254):
        print(f"CSV: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
