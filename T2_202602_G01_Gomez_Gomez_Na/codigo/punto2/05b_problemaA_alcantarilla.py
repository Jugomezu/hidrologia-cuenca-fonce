#!/usr/bin/env python3
"""Problema A: diseño preliminar de una alcantarilla circular en Denver.

Consume solamente los metadatos y productos IDF locales del proyecto. Todas
las rutas se resuelven desde la raíz del repositorio, relativa a este archivo.
Los resultados son un ejercicio de prediseño; las fuentes y limitaciones de
cada ecuación/supuesto se guardan en los CSV y se imprimen en el diagnóstico.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearson3, truncnorm

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datos" / "punto2"
PRODUCTS = ROOT / "productos" / "punto2"
META_PATH = DATA / "metadatos_microcuenca.json"
PARAMS_PATH = PRODUCTS / "parametros_idf.csv"
IDF_PATH = PRODUCTS / "tabla_idf_completa.csv"
QUANTILES_PATH = PRODUCTS / "cuantiles_y_bootstrap.csv"
MAXIMA_PATH = PRODUCTS / "maximos_anuales_intensidad.csv"
COMPLETENESS_PATH = PRODUCTS / "resumen_completitud_anual.csv"
OUT_DESIGN = PRODUCTS / "problemaA_alcantarilla.csv"
OUT_SENS = PRODUCTS / "problemaA_sensibilidad.csv"
OUT_MC = PRODUCTS / "problemaA_montecarlo.csv"
FIG_PATH = PRODUCTS / "fig_24_problemaA_sensibilidad_mc.png"

SEED = 42
N_MC = 5000
T_DESIGN = 50
LIFE_YEARS = 25
RISK_TARGET = 0.40
CN_II = 78.0
SHEET_LENGTH_M = 300.0  # Kerby se limita al tramo corto de flujo laminar/superficial.
KERBY_RETARDANCE_N = 0.20  # valor compuesto representativo de parques y lotes.
MANNING_N_NOMINAL = 0.013
COMMERCIAL_MM = np.array([600, 750, 900, 1050, 1200, 1350, 1500], dtype=float)


def read_inputs():
    for path in (META_PATH, PARAMS_PATH, IDF_PATH, QUANTILES_PATH,
                 MAXIMA_PATH, COMPLETENESS_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Falta insumo requerido: {path.relative_to(ROOT)}")
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    params_all = pd.read_csv(PARAMS_PATH, low_memory=False)
    idf = pd.read_csv(IDF_PATH, low_memory=False)
    quantiles = pd.read_csv(QUANTILES_PATH, low_memory=False)
    maxima = pd.read_csv(MAXIMA_PATH, low_memory=False)
    completeness = pd.read_csv(COMPLETENESS_PATH, low_memory=False)
    return meta, params_all, idf, quantiles, maxima, completeness


def tc_methods(meta: dict, cn: float) -> tuple[dict[str, float], dict]:
    length = float(meta["main_channel_length_m"])
    slope = float(meta["relief_slope_S0_m_per_m"])
    # Kirpich 1940, SI form (m, m/m, min); adecuado como screening de cauce.
    kirpich = 0.01947 * length**0.77 * slope**-0.385
    # Témez 1978: L en km y S en m/m, resultado en horas.
    temez = 60 * 0.30 * ((length / 1000) / slope**0.25) ** 0.76
    # Kerby-Hathaway: Kerby estima escorrentía laminar sobre un tramo corto.
    # Se suma el tiempo de ese tramo (L<=366 m) y Kirpich para el cauce restante.
    channel_length = max(length - SHEET_LENGTH_M, 1.0)
    kerby_sheet = 0.828 * (
        SHEET_LENGTH_M * 3.280839895 * KERBY_RETARDANCE_N / math.sqrt(slope)
    ) ** 0.467
    kirpich_channel = 0.01947 * channel_length**0.77 * slope**-0.385
    kerby_hathaway = kerby_sheet + kirpich_channel
    # NRCS/SCS watershed lag (Mockus); S_ret in inches, length in feet,
    # slope in percent. Lag=0.6 Tc, fórmula de NRCS NEH 630, cap. 15.
    retention_mm = 25400 / cn - 254
    retention_in = retention_mm / 25.4
    length_ft = length * 3.280839895
    lag_h = length_ft**0.8 * (retention_in + 1) ** 0.7 / (
        1900 * math.sqrt(slope * 100)
    )
    nrcs_tc = lag_h / 0.6 * 60
    methods = {
        "Kirpich (cauce completo)": kirpich,
        "Témez": temez,
        "Kerby-Hathaway (lámina + cauce)": kerby_hathaway,
        "NRCS-SCS Lag": nrcs_tc,
    }
    # 60 min es una adopción redondeada dentro del rango urbano rápido
    # (Kirpich/Kerby compuesto), conservadora respecto a Kirpich solo.
    adopted = 60.0
    context = {
        "Kirpich_min": kirpich, "Temez_min": temez,
        "Kerby_sheet_length_m_assumed": SHEET_LENGTH_M,
        "Kerby_retardance_N_assumed": KERBY_RETARDANCE_N,
        "Kerby_sheet_min": kerby_sheet,
        "Kerby_channel_Kirpich_min": kirpich_channel,
        "Kerby_Hathaway_combined_min": kerby_hathaway,
        "NRCS_SCS_Lag_min": nrcs_tc,
        "tc_design_min": adopted,
        "tc_selection_note": "60 min: redondeo de diseño urbano entre estimaciones rápidas; NRCS Lag es un control de cuenca rural más lento.",
    }
    return methods, context


def runoff_coefficient() -> tuple[float, pd.DataFrame]:
    # Composición hipotética explícita de baja/media densidad periurbana;
    # C de referencia por superficies en Chow et al. (1988), Applied Hydrology,
    # tabla 15.1.1. El reparto de áreas requiere verificación GIS/catastro.
    parts = pd.DataFrame([
        {"cover": "Residencial y vías impermeables", "area_fraction": 0.45,
         "C_k": 0.75, "basis": "Rango residencial/impermeable, Chow et al. 1988, Tabla 15.1.1"},
        {"cover": "Parques y zonas verdes", "area_fraction": 0.35,
         "C_k": 0.25, "basis": "Áreas verdes/permeables, Chow et al. 1988, Tabla 15.1.1"},
        {"cover": "Suelo descubierto/pradera semiárida", "area_fraction": 0.20,
         "C_k": 0.35, "basis": "Suelo abierto, Chow et al. 1988, Tabla 15.1.1"},
    ])
    parts["weighted_C"] = parts.area_fraction * parts.C_k
    if not np.isclose(parts.area_fraction.sum(), 1):
        raise ValueError("Las fracciones de cobertura deben sumar 1.")
    return float(parts.weighted_C.sum()), parts


def get_tw(params: pd.DataFrame) -> dict:
    found = params[params.formulacion.astype(str).str.casefold().eq("talbot-wenzel")]
    if found.empty:
        raise ValueError("parametros_idf.csv no contiene Talbot-Wenzel.")
    row = found.iloc[0]
    return {key: float(row[key]) for key in ("a", "m", "b_h", "c")}


def tw_intensity(t_hours: float, T: float, tw: dict) -> float:
    return tw["a"] * T**tw["m"] / (t_hours + tw["b_h"]) ** tw["c"]


def idf_point_ci(quantiles: pd.DataFrame, duration_h: float, T: int,
                 distribution: str = "LP3") -> tuple[float, float, float]:
    rows = quantiles[
        np.isclose(pd.to_numeric(quantiles.duration_h, errors="coerce"), duration_h)
        & quantiles.distribution.astype(str).str.casefold().eq(distribution.casefold())
        & quantiles.method.astype(str).str.upper().eq("LMOM")
        & np.isclose(pd.to_numeric(quantiles.return_period_y, errors="coerce"), T)
    ]
    if rows.empty:
        raise ValueError(f"Sin cuantiles {distribution}/LMOM para {duration_h:g} h, T={T}.")
    row = rows.iloc[0]
    return tuple(float(row[c]) for c in ("quantile_mmh", "ci95_low_mmh", "ci95_high_mmh"))


def idf_table_intensity(idf: pd.DataFrame, duration_min: float, T: int) -> float:
    required = {"duration_min", "return_period_y", "intensity_mmh", "model"}
    if not required.issubset(idf.columns):
        raise ValueError(f"tabla_idf_completa.csv requiere columnas {sorted(required)}.")
    rows = idf[
        np.isclose(pd.to_numeric(idf.duration_min, errors="coerce"), duration_min)
        & np.isclose(pd.to_numeric(idf.return_period_y, errors="coerce"), T)
        & idf.model.astype(str).str.casefold().eq("talbot-wenzel")
    ]
    if rows.empty:
        raise ValueError(f"No hay IDF Talbot-Wenzel en tabla maestra para {duration_min:g} min, T={T}.")
    return float(rows.iloc[0].intensity_mmh)


def pipe_capacity(diameter_m: float, roughness: float, slope: float) -> float:
    return 0.312 / roughness * diameter_m ** (8 / 3) * math.sqrt(slope)


def required_diameter(q_m3s: float, roughness: float, slope: float) -> float:
    return (roughness * q_m3s / (0.312 * math.sqrt(slope))) ** (3 / 8)


def commercial_diameter(d_m: float) -> float:
    fitting = COMMERCIAL_MM[COMMERCIAL_MM / 1000 >= d_m]
    return float(fitting[0]) if len(fitting) else np.nan


def area_reduction_factor(area_km2: float, duration_h: float, T: float) -> tuple[float, str]:
    # En cuencas <20 km² se adopta FRA=1: una reducción areal no se recomienda
    # en la guía ARR/WRC citada abajo. Para 250 km² se usa un cálculo ilustrativo
    # regional, explícitamente no calibrado para Colorado, de Carey-Smith et al.
    if area_km2 < 20:
        return 1.0, "Sin reducción areal para A<20 km²; criterio de aplicación de ARR/WRC."
    raw = 1 - 0.023 * area_km2**0.43 * max(duration_h, 0.1)**-0.52 * math.log(T)**0.23
    return float(np.clip(raw, 0.05, 1.0)), (
        "Ilustración Carey-Smith et al. (2018), ARF=1−0.023 A^0.43 D^-0.52 (lnT)^0.23; "
        "no calibrada regionalmente para Denver, no usar como factor de diseño local."
    )


def load_lmom_module():
    path = ROOT / "codigo" / "punto2" / "02_extremos_y_distribuciones.py"
    spec = importlib.util.spec_from_file_location("punto2_extremos_lmom", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_maxima(maxima: pd.DataFrame, completeness: pd.DataFrame) -> np.ndarray:
    year_col = "hydro_year" if "hydro_year" in maxima else "year"
    retained_col = next((c for c in ("retained", "conservar", "aceptado") if c in completeness), None)
    year_summary_col = "year" if "year" in completeness else "hydro_year"
    if retained_col:
        accepted = completeness.loc[
            completeness[retained_col].astype(str).str.casefold().isin({"sí", "si", "true", "1", "yes"}),
            year_summary_col,
        ].astype(int)
        maxima = maxima[maxima[year_col].astype(int).isin(set(accepted))]
    values = pd.to_numeric(maxima.intensity_1h_mmh, errors="coerce").dropna()
    values = values[np.isfinite(values) & (values > 0)].to_numpy(float)
    if len(values) < 20:
        raise ValueError(f"Solo {len(values)} máximos anuales aceptados; se requieren al menos 20.")
    return values


def monte_carlo(values: np.ndarray, lmom, tc_methods_min: dict, tc_design: float,
                C_mean: float, area: float, slope_design: float, design_intensity: float,
                pipe_d_m: float, tw: dict, T: int = T_DESIGN) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(SEED)
    tc_min, tc_max = min(tc_methods_min.values()), max(tc_methods_min.values())
    c_dist = truncnorm((0.15 - C_mean) / (0.12 * C_mean),
                       (0.95 - C_mean) / (0.12 * C_mean), loc=C_mean, scale=0.12 * C_mean)
    n_dist = truncnorm((0.011 - 0.013) / 0.001, (0.016 - 0.013) / 0.001,
                       loc=0.013, scale=0.001)
    tc_samples = rng.triangular(tc_min, tc_design, tc_max, N_MC)
    C_samples = c_dist.rvs(size=N_MC, random_state=rng)
    n_samples = n_dist.rvs(size=N_MC, random_state=rng)
    slope_samples = np.maximum(1e-6, rng.normal(slope_design, 0.10 * slope_design, N_MC))
    anchor_1h = design_intensity / (
        ((1 + tw["b_h"]) / (tc_design / 60 + tw["b_h"])) ** tw["c"]
    )
    duration_ratio = np.array([
        ((1 + tw["b_h"]) / (t / 60 + tw["b_h"])) ** tw["c"] for t in tc_samples
    ])
    rows = []
    attempts = 0
    # Nonparametric bootstrap over accepted annual maxima. Each replicate
    # refits LP3/LMOM; this supplies the parameter uncertainty rather than a
    # normal approximation to the published CI.
    while len(rows) < N_MC and attempts < N_MC * 5:
        idx = len(rows)
        attempts += 1
        sample = rng.choice(values, size=len(values), replace=True)
        try:
            fit = lmom.fit_distribution(sample, "LP3", "LMOM")
        except (ValueError, FloatingPointError, OverflowError):
            continue
        probability = 1 - 1 / T
        # En parametros_distribuciones.csv, LP3/LMOM tiene loc/scale/skew
        # ajustados sobre log10(mm/h). El bootstrap puede mover su T50; se
        # calibra la réplica en intensidad para que su PPF(T=50, 1 h) ancle
        # exactamente la IDF maestra. La misma transformación se aplica al
        # sorteo anual y al umbral antes de evaluar la supervivencia.
        raw_i50 = float(lmom.ppf(np.array([probability]), "LP3", fit)[0])
        if not np.isfinite(raw_i50) or raw_i50 <= 0:
            continue
        bootstrap_calibration = anchor_1h / raw_i50
        fit_calibrated = dict(fit)
        fit_calibrated["loc"] += np.log10(bootstrap_calibration)
        calibrated_i50 = float(lmom.ppf(np.array([probability]), "LP3", fit_calibrated)[0])
        if not np.isclose(calibrated_i50, anchor_1h, rtol=1e-9, atol=1e-9):
            continue
        i_design = calibrated_i50 * duration_ratio[idx]
        annual_i = float(lmom.ppf(
            np.array([rng.uniform(1e-5, 1 - 1e-5)]), "LP3", fit_calibrated
        )[0]) * duration_ratio[idx]
        if not (np.isfinite(i_design) and np.isfinite(annual_i) and i_design > 0 and annual_i > 0):
            continue
        q_load = C_samples[idx] * i_design * area / 3.6
        q_annual = C_samples[idx] * annual_i * area / 3.6
        q_cap = pipe_capacity(pipe_d_m, n_samples[idx], slope_samples[idx])
        i_crit = 3.6 * q_cap / (C_samples[idx] * area)
        # El loc lleva el mismo desplazamiento log10(calibración) que el PPF;
        # se transforma i* a la duración base de 1 h antes de usar la SF.
        threshold_1h_log10 = np.log10(max(i_crit / duration_ratio[idx], np.finfo(float).tiny))
        p_fail = float(pearson3.sf(
            threshold_1h_log10, fit_calibrated["skew"],
            loc=fit_calibrated["loc"], scale=fit_calibrated["scale"]
        ))
        p_fail = float(np.clip(p_fail, 0.0, 1.0))
        rows.append({
            "iteration": idx + 1, "bootstrap_intensity_1h_uncalibrated_mmh": raw_i50,
            "bootstrap_calibration_to_idf": bootstrap_calibration,
            "bootstrap_intensity_1h_mmh": calibrated_i50,
            "bootstrap_loc_log10_uncalibrated": fit["loc"],
            "bootstrap_loc_log10_calibrated": fit_calibrated["loc"],
            "C_sample": C_samples[idx], "tc_sample_min": tc_samples[idx],
            "manning_n_sample": n_samples[idx], "slope_sample": slope_samples[idx],
            "i_design_sample_mmh": i_design, "Q_load_T50_m3s": q_load,
            "Q_annual_random_m3s": q_annual, "Q_capacity_m3s": q_cap,
            "i_critical_mmh": i_crit, "annual_exceedance_probability": p_fail,
            "risk_life_25y": 1 - (1 - p_fail) ** LIFE_YEARS,
            "failure_direct_indicator": bool(q_annual > q_cap),
            "FS_design_sample": q_cap / q_load if q_load > 0 else np.nan,
        })
    mc = pd.DataFrame(rows)
    if len(mc) != N_MC:
        raise RuntimeError(f"Bootstrap LP3/LMOM obtuvo {len(mc)} réplicas válidas en {attempts} intentos; se exigían {N_MC}.")
    p_effective = float(mc.annual_exceedance_probability.mean())
    direct_rate = float(mc.failure_direct_indicator.mean())
    direct_se = math.sqrt(max(direct_rate * (1 - direct_rate), 0) / N_MC)
    summary = {
        "record_type": "resumen_montecarlo", "iterations": N_MC, "seed": SEED,
        "annual_effective_failure_probability": p_effective,
        "effective_risk_life_25y": 1 - (1 - p_effective) ** LIFE_YEARS,
        "direct_rate_Pr_QL_gt_Qc": direct_rate,
        "direct_rate_minus_annual_probability": direct_rate - p_effective,
        "direct_rate_mc_standard_error": direct_se,
        "direct_rate_matches_probability_within_4SE": abs(direct_rate - p_effective) <= 4 * direct_se + 1e-9,
        "FS_nominal": float(pipe_capacity(pipe_d_m, MANNING_N_NOMINAL, slope_design)
                            / (C_mean * design_intensity * area / 3.6)),
        "Q_load_T50_mean_m3s": float(mc.Q_load_T50_m3s.mean()),
        "Q_capacity_mean_m3s": float(mc.Q_capacity_m3s.mean()),
        "i_critical_mean_mmh": float(mc.i_critical_mmh.mean()),
        "design_intensity_reference_mmh": design_intensity,
        "pipe_diameter_m": pipe_d_m,
        "note": "LP3 ajustada en log10(mm/h); cada bootstrap desplaza loc por log10(calibración) para que PPF(T=50,1h) ancle la IDF maestra. p_anual=pearson3.sf(log10(i*/factor_duración), skew, loc_calibrado, scale); tasa directa usa el mismo ajuste.",
        "lp3_calibration_anchor_1h_mmh": anchor_1h,
    }
    return mc, summary


def make_figure(sensitivity: pd.DataFrame, mc: pd.DataFrame, dcom_mm: float,
                nominal_fs: float, nominal_d_mm: float) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.2), constrained_layout=True)
    ordered = sensitivity[sensitivity.record_type.eq("sensibilidad")].sort_values(
        "impact_D_mm", ascending=True
    )
    y = np.arange(len(ordered))
    left = np.maximum(0, nominal_d_mm - ordered.min_D_mm.to_numpy(float))
    right = np.maximum(0, ordered.max_D_mm.to_numpy(float) - nominal_d_mm)
    ax1.errorbar(np.zeros(len(ordered)), y, xerr=np.vstack([left, right]),
                 fmt="o", color="#2c8b78", ecolor="#2c8b78", capsize=4,
                 elinewidth=5, markersize=4)
    ax1.set_yticks(y, ordered.factor)
    ax1.set_xlabel("Cambio en D requerido respecto al nominal (mm)")
    ax1.set_title("Sensibilidad ordenada del diámetro")
    ax1.grid(axis="x", alpha=0.25)
    ax1.axvline(0, color="#3d4b54", lw=0.7)
    commercial_offsets = COMMERCIAL_MM - nominal_d_mm
    for index, offset in enumerate(commercial_offsets):
        ax1.axvline(offset, color="#83929a", lw=0.65, ls=":" if index % 2 else "--", alpha=0.55)
    ax1.text(0.98, 0.02, "Líneas verticales: diámetros comerciales 600–1500 mm",
             transform=ax1.transAxes, ha="right", va="bottom", fontsize=8,
             bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#cccccc"})
    ax1.text(0.98, 0.12, f"D nominal = {nominal_d_mm:.0f} mm; Dcom = {dcom_mm:.0f} mm", transform=ax1.transAxes,
             ha="right", fontsize=9, color="#145c50")

    load = mc.Q_annual_random_m3s.to_numpy()
    capacity = mc.Q_capacity_m3s.to_numpy()
    bins = np.linspace(0, max(np.percentile(load, 99.5), np.percentile(capacity, 99.5)), 45)
    ax2.hist(load, bins=bins, density=True, alpha=0.55, color="#d8844a", label="Carga anual aleatoria $Q_L$")
    ax2.hist(capacity, bins=bins, density=True, alpha=0.55, color="#3976a8", label="$Q_c$ con incertidumbre n, S")
    fail_rate = np.mean(load > capacity)
    ax2.axvline(np.median(load), color="#a85625", ls="--", lw=1.4, label="Mediana carga")
    ax2.axvline(np.median(capacity), color="#245b84", ls="--", lw=1.4, label="Mediana capacidad")
    ax2.set_xlabel("Caudal (m³/s)"); ax2.set_ylabel("Densidad")
    ax2.set_title("Monte Carlo: carga y capacidad")
    ax2.text(0.98, 0.97, f"Dcom={dcom_mm:.0f} mm · FS nominal={nominal_fs:.2f}\nPr(QL>Qc)={fail_rate:.3f}",
             transform=ax2.transAxes, ha="right", va="top", fontsize=9,
             bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#cccccc"})
    ax2.legend(fontsize=8, loc="upper left")
    ax2.grid(alpha=0.2)
    fig.suptitle("Problema A · Prediseño de alcantarilla circular", fontsize=15, weight="bold")
    fig.savefig(FIG_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    meta, params, idf, quantiles, maxima, completeness = read_inputs()
    area = float(meta["area_km2"])
    length = float(meta["main_channel_length_m"])
    slope = float(meta["relief_slope_S0_m_per_m"])
    relief = float(meta["elevation_max_m"]) - float(meta["outlet_elevation_m"])
    C, covers = runoff_coefficient()
    methods, tc_context = tc_methods(meta, CN_II)
    tc_design_min = tc_context["tc_design_min"]
    tc_h = tc_design_min / 60
    tw = get_tw(params)
    arf, arf_note = area_reduction_factor(area, tc_h, T_DESIGN)
    # Para el caso adoptado tc=60 min, usa directamente el punto de la tabla
    # maestra y contrástalo con los parámetros Talbot-Wenzel para la continuidad.
    point_i = idf_table_intensity(idf, tc_design_min, T_DESIGN)
    # Verifica el convenio de distribución guardado: LP3 vive en log10(mm/h),
    # por eso la inversa de Pearson III se transforma con 10**y.
    dist_params_path = PRODUCTS / "parametros_distribuciones.csv"
    if not dist_params_path.is_file():
        raise FileNotFoundError(f"Falta {dist_params_path.relative_to(ROOT)} para validar LP3/LMOM.")
    dist_params = pd.read_csv(dist_params_path, low_memory=False)
    saved = dist_params[
        np.isclose(pd.to_numeric(dist_params.duration_h, errors="coerce"), 1.0)
        & dist_params.distribution.astype(str).eq("LP3")
        & dist_params.method.astype(str).str.upper().eq("LMOM")
    ]
    if saved.empty:
        raise ValueError("No hay parámetros LP3/LMOM para 1 h en parametros_distribuciones.csv.")
    saved = saved.iloc[0]
    raw_1h_q50 = float(10 ** pearson3.ppf(
        1 - 1 / T_DESIGN, float(saved["pearson3_skew_log10"]),
        loc=float(saved["loc"]), scale=float(saved["scale"])
    ))
    anchor_1h = point_i / (((1 + tw["b_h"]) / (tc_h + tw["b_h"])) ** tw["c"])
    calibrated_loc = float(saved["loc"]) + np.log10(anchor_1h / raw_1h_q50)
    calibrated_1h_q50 = float(10 ** pearson3.ppf(
        1 - 1 / T_DESIGN, float(saved["pearson3_skew_log10"]),
        loc=calibrated_loc, scale=float(saved["scale"])
    ))
    if not np.isclose(calibrated_1h_q50, anchor_1h, rtol=1e-10, atol=1e-10):
        raise ArithmeticError("La inversa LP3 calibrada no reproduce el ancla IDF de 1 h, T=50.")
    print(f"LP3/LMOM 1 h: PPF guardada sin calibrar={raw_1h_q50:.4f} mm/h; "
          f"factor multiplicativo={anchor_1h/raw_1h_q50:.6f}; "
          f"ancla IDF={anchor_1h:.4f}; PPF tras calibración={calibrated_1h_q50:.4f} mm/h.")
    area_i = point_i * arf
    q_design = C * area_i * area / 3.6
    d_required_m = required_diameter(q_design, MANNING_N_NOMINAL, slope)
    dcom_mm = commercial_diameter(d_required_m)
    if not np.isfinite(dcom_mm):
        raise ValueError(f"Diámetro requerido {1000*d_required_m:.1f} mm excede la serie comercial disponible.")
    q_capacity = pipe_capacity(dcom_mm / 1000, MANNING_N_NOMINAL, slope)
    fs_nominal = q_capacity / q_design
    risk_50_25 = 1 - (1 - 1 / 50) ** LIFE_YEARS
    T_from_risk = 1 / (1 - (1 - RISK_TARGET) ** (1 / LIFE_YEARS))

    # Sensibilidad un factor a la vez respecto del caso nominal T=50 años.
    scenarios = []
    def add_scenario(factor: str, scenario: str, duration_min: float,
                     Cval: float = C, intensity: float | None = None,
                     nval: float = MANNING_N_NOMINAL, slopeval: float = slope,
                     distribution: str = "LP3/LMOM", note: str = ""):
        if intensity is None:
            intensity = tw_intensity(duration_min / 60, T_DESIGN, tw)
        q = Cval * intensity * arf * area / 3.6
        d = required_diameter(q, nval, slopeval)
        scenarios.append({
            "record_type": "escenario", "factor": factor, "scenario": scenario,
            "T_y": T_DESIGN, "tc_min": duration_min, "C": Cval,
            "intensity_mmh": intensity, "distribution": distribution,
            "FRA": arf, "Qp_m3s": q, "D_required_mm": 1000 * d,
            "D_commercial_mm": commercial_diameter(d), "note": note,
        })
    add_scenario("Referencia", "adoptado", tc_design_min)
    for name, tc_value in methods.items():
        add_scenario("Tiempo de concentración", name, tc_value, note="Método alternativo; demás supuestos base.")
    add_scenario("Coeficiente C", "C -20%", tc_design_min, Cval=max(0.15, 0.8 * C))
    add_scenario("Coeficiente C", "C +20%", tc_design_min, Cval=min(0.95, 1.2 * C))

    scale = ((1 + tw["b_h"]) / (tc_h + tw["b_h"])) ** tw["c"]
    lp3_q, lp3_lo, lp3_hi = idf_point_ci(quantiles, 1.0, T_DESIGN, "LP3")
    for label, i1 in (("LP3/LMOM límite inferior IC95%", lp3_lo),
                      ("LP3/LMOM mediana bootstrap", lp3_q),
                      ("LP3/LMOM límite superior IC95%", lp3_hi)):
        add_scenario("IC95% IDF", label, tc_design_min, intensity=i1 * scale,
                     distribution="LP3/LMOM", note="Cuantil a 1 h reescalado con la forma de duración Talbot-Wenzel.")
    for dist in ("GEV", "Gumbel"):
        q, lo, hi = idf_point_ci(quantiles, 1.0, T_DESIGN, dist)
        add_scenario("Distribución", f"{dist}/LMOM", tc_design_min,
                     intensity=q * scale, distribution=f"{dist}/LMOM",
                     note="Cuantil LMOM a 1 h; reescalado con duración Talbot-Wenzel.")

    sens = pd.DataFrame(scenarios)
    group_ranges = sens[sens.factor.ne("Referencia")].groupby("factor").D_required_mm.agg(
        min_D_mm="min", max_D_mm="max"
    ).reset_index()
    group_ranges["impact_D_mm"] = group_ranges.max_D_mm - group_ranges.min_D_mm
    group_ranges["impact_rank"] = group_ranges.impact_D_mm.rank(method="min", ascending=False).astype(int)
    sens = sens.merge(group_ranges, on="factor", how="left")
    sensitivity_summary = group_ranges.assign(
        record_type="sensibilidad", scenario="rango", T_y=T_DESIGN,
        tc_min=np.nan, C=np.nan, intensity_mmh=np.nan, distribution="",
        FRA=arf, Qp_m3s=np.nan, D_required_mm=np.nan, D_commercial_mm=np.nan,
        note="Impacto como rango máximo-mínimo de diámetro requerido entre escenarios del factor."
    )
    sensitivity_out = pd.concat([sens, sensitivity_summary[sens.columns]], ignore_index=True)
    sensitivity_out.sort_values(["record_type", "impact_rank", "factor"], na_position="last").to_csv(
        OUT_SENS, index=False, encoding="utf-8-sig"
    )

    # Datos de detalle del diseño adoptado y trazabilidad del riesgo.
    cover_payload = "; ".join(
        f"{r.cover}={r.area_fraction:.0%} (C={r.C_k:.2f})" for r in covers.itertuples()
    )
    design = pd.DataFrame([{
        "record_type": "diseño_nominal", "station": meta.get("station", "USW00023062"),
        "area_km2": area, "area_ha": area * 100, "length_m": length,
        "relief_m": relief, "slope_S0": slope, "cover_mix": cover_payload,
        "C_weighted": C, "CN_II_reference": CN_II,
        **tc_context, "tc_methods_min": "; ".join(f"{k}={v:.2f}" for k, v in methods.items()),
        "T_design_y": T_DESIGN, "life_years": LIFE_YEARS,
        "risk_at_T50_pct": 100 * risk_50_25, "T_for_target_risk_y": T_from_risk,
        "risk_target_pct": 100 * RISK_TARGET,
        "return_period_practice_reference": "Chow et al. (1988), Tabla 13.1.1: colectores pluviales ciudades pequeñas 2-25 años; ciudades grandes 25-50; alcantarillas viales 5-10 (tráfico bajo), 10-25 (intermedio), 50-100 (alto). T=50 está en el límite superior urbano y el inferior para tráfico alto.",
        "duration_h": tc_h, "idf_model": "Talbot-Wenzel; cuantil base LP3/LMOM",
        "LP3_raw_PPF_T50_1h_mmh": raw_1h_q50,
        "LP3_calibration_factor_to_IDF": anchor_1h / raw_1h_q50,
        "LP3_calibrated_PPF_T50_1h_mmh": calibrated_1h_q50,
        "LP3_calibrated_loc_log10": calibrated_loc,
        "idf_a": tw["a"], "idf_m": tw["m"], "idf_b_h": tw["b_h"], "idf_c": tw["c"],
        "idf_intensity_point_mmh": point_i, "FRA": arf, "intensity_areal_mmh": area_i,
        "FRA_note": arf_note, "Qp_rational_m3s": q_design,
        "manning_n": MANNING_N_NOMINAL, "D_required_m": d_required_m,
        "D_required_mm": 1000 * d_required_m, "D_commercial_mm": dcom_mm,
        "Qc_full_m3s": q_capacity, "FS_nominal": fs_nominal,
        "design_note": "Manning a tubo lleno; diseño preliminar sin pérdidas locales, remanso, entrada, sedimentos ni verificación estructural.",
    }])
    design.to_csv(OUT_DESIGN, index=False, encoding="utf-8-sig")

    values = valid_maxima(maxima, completeness)
    lmom = load_lmom_module()
    mc, mc_summary = monte_carlo(values, lmom, methods, tc_design_min, C, area,
                                 slope, point_i, dcom_mm / 1000, tw)
    mc_out = pd.concat([mc, pd.DataFrame([mc_summary])], ignore_index=True, sort=False)
    mc_out.to_csv(OUT_MC, index=False, encoding="utf-8-sig")
    make_figure(sensitivity_out, mc, dcom_mm, fs_nominal, 1000 * d_required_m)

    # Ilustración de escala: ARF regional genérico a 250 km², mismas tc/T.
    arf_large, large_note = area_reduction_factor(250.0, tc_h, T_DESIGN)
    q_large_uniform = C * point_i * 250 / 3.6
    q_large_reduced = q_large_uniform * arf_large
    print("=== Problema A · prediseño de alcantarilla ===")
    print(f"Metadatos reales: A={area:.4f} km²; L={length:.1f} m; ΔH={relief:.2f} m; S0={slope:.5f} m/m.")
    print("Cobertura asumida: " + cover_payload + f"; C ponderado={C:.3f}.")
    print("tc (min): " + "; ".join(f"{k} {v:.1f}" for k, v in methods.items()))
    print(f"tc adoptado={tc_design_min:.1f} min; la variación refleja longitud hidráulica, retardancia y dominios empíricos distintos.")
    print(f"R(T=50,n=25)={risk_50_25:.1%}; T para R=40% en 25 años={T_from_risk:.1f} años; se adopta T=50 años.")
    print(f"FRA microcuenca={arf:.3f}; i={point_i:.2f} mm/h; Qp={q_design:.3f} m³/s.")
    print(f"D requerido={1000*d_required_m:.1f} mm; D comercial={dcom_mm:.0f} mm; Qc={q_capacity:.3f} m³/s; FS={fs_nominal:.2f}.")
    print("Práctica Chow et al. (1988), Tabla 13.1.1: colectores de ciudad pequeña 2–25 años, ciudad grande 25–50; alcantarilla vial 5–10 (tráfico bajo), 10–25 (intermedio), 50–100 (alto). T=50 coincide con límite superior urbano y límite inferior de tráfico alto; la clase y consecuencias locales deben confirmarse.")
    print("Sensibilidad (mayor impacto primero):")
    for row in group_ranges.sort_values("impact_rank").itertuples():
        print(f"  {row.impact_rank}. {row.factor}: ΔD={row.impact_D_mm:.1f} mm (D={row.min_D_mm:.1f}–{row.max_D_mm:.1f} mm).")
    print(f"Monte Carlo N={N_MC}, seed={SEED}: p_anual efectiva={mc_summary['annual_effective_failure_probability']:.4f}; R_ef(25a)={mc_summary['effective_risk_life_25y']:.1%}; Pr(QL>Qc)={mc_summary['direct_rate_Pr_QL_gt_Qc']:.4f}.")
    print("Chequeo de excedencia: p_anual=pearson3.sf(log10(i*/escala_duración), skew, loc_calibrado, scale); "
          f"directa y analítica coinciden dentro de 4 errores estándar: "
          f"{mc_summary['direct_rate_matches_probability_within_4SE']} "
          f"(diferencia={mc_summary['direct_rate_minus_annual_probability']:.4f}).")
    print(f"Escala 250 km²: FRA ilustrativo={arf_large:.3f}; Q racional puntual uniforme={q_large_uniform:.1f} m³/s vs reducido={q_large_reduced:.1f} m³/s. {large_note}")
    print("La lluvia convectiva de Denver no es uniforme en espacio/tiempo sobre 250 km²; el método racional y su tc único dejan de ser representativos; usar lluvia areal/radar y modelación distribuida.")
    print(f"Guardado: {OUT_DESIGN.relative_to(ROOT)}, {OUT_SENS.relative_to(ROOT)}, {OUT_MC.relative_to(ROOT)}, {FIG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
