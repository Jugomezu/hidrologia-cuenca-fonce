#!/usr/bin/env python3
"""Máximos anuales hidrológicos, distribuciones y figuras del Apartado 2.2.

Requisitos: numpy, pandas, scipy y matplotlib. Todas las rutas se resuelven
relativas a la raíz del proyecto. La serie limpia se carga con usecols y
low_memory=False; el PSV original no se utiliza en este análisis.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache
import math
import warnings

import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.special import gamma
from scipy.stats import genextreme, gumbel_r, pearson3

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datos" / "punto2"
PRODUCTS = ROOT / "productos" / "punto2"
CLEAN = DATA / "precip_horaria_limpia.csv"
SUMMARY = PRODUCTS / "resumen_completitud_anual.csv"
MAXIMA_CSV = PRODUCTS / "maximos_anuales_intensidad.csv"
PARAMS_CSV = PRODUCTS / "parametros_distribuciones.csv"
QUANTILES_CSV = PRODUCTS / "cuantiles_y_bootstrap.csv"
GOF_CSV = PRODUCTS / "bondad_y_estacionariedad.csv"
FIG_PROB = PRODUCTS / "fig2_papel_probabilidad.png"
FIG_LMOM = PRODUCTS / "fig2_diagrama_lmomentos.png"
FIG_BOOT = PRODUCTS / "fig2_incertidumbre_bootstrap.png"
DURATIONS = (1, 2, 3, 6, 12, 24)
RETURN_PERIODS = (2, 5, 10, 25, 50, 100)
BOOTSTRAPS = 1000
SEED = 42
GAMMA_EULER = 0.5772156649015329


def sample_lmoments(values):
    """Unbiased sample L-moments from Hosking & Wallis PWM equations.

    For ordered x_(i), b_r = n^-1 sum_{i=r+1}^n
    C(i-1,r)/C(n-1,r) x_(i); l1=b0, l2=2b1-b0,
    l3=6b2-6b1+b0, and l4=20b3-30b2+12b1-b0.
    """
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    if n < 4:
        raise ValueError("Se requieren al menos cuatro máximos para tau4.")
    b = []
    for r in range(4):
        weights = np.zeros(n, dtype=float)
        for i in range(r, n):
            weights[i] = math.comb(i, r) / math.comb(n - 1, r)
        b.append(float(np.dot(weights, x) / n))
    l1 = b[0]
    l2 = 2 * b[1] - b[0]
    l3 = 6 * b[2] - 6 * b[1] + b[0]
    l4 = 20 * b[3] - 30 * b[2] + 12 * b[1] - b[0]
    if not np.isfinite(l2) or l2 <= 0:
        raise ValueError("L-scale no positiva.")
    return l1, l2, l3, l4, l3 / l2, l4 / l2


def _gev_lmom_fit(x):
    l1, l2, _, _, tau3, _ = sample_lmoments(x)
    def tau3_from_xi(xi):
        if abs(xi) < 1e-7:
            return 2 * math.log(3) / math.log(2) - 3
        return 2 * (1 - 3 ** (-xi)) / (1 - 2 ** (-xi)) - 3
    lo, hi = -0.45, 0.32  # finite third L-moment domain, xi < 1/3
    f_lo, f_hi = tau3_from_xi(lo) - tau3, tau3_from_xi(hi) - tau3
    if f_lo * f_hi > 0:
        raise ValueError("Muestra fuera del dominio del ajuste GEV por L-momentos.")
    xi = optimize.brentq(lambda z: tau3_from_xi(z) - tau3, lo, hi)
    if abs(xi) < 1e-7:
        scale = l2 / math.log(2)
        loc = l1 - GAMMA_EULER * scale
    else:
        scale = l2 * xi / ((1 - 2 ** (-xi)) * gamma(1 + xi))
        loc = l1 - scale * (gamma(1 - xi) - 1) / xi
    return {"xi": float(xi), "c": float(-xi), "loc": float(loc), "scale": float(scale)}


def _pearson_theoretical_lmom(skew):
    # Midpoint quadrature of the population L-moment integrals for Pearson III.
    u = (np.arange(600, dtype=float) + 0.5) / 600
    q = pearson3.ppf(u, skew)
    p2 = 2 * u - 1
    p3 = 6 * u * u - 6 * u + 1
    p4 = 20 * u ** 3 - 30 * u * u + 12 * u - 1
    return np.array([q.mean(), np.mean(q * p2), np.mean(q * p3), np.mean(q * p4)])


@lru_cache(maxsize=1)
def _pearson_lmom_table():
    # Numerical population L-moments on a dense shape grid are cached once;
    # interpolation keeps the 1,000-replicate bootstrap tractable.
    skew_grid = np.linspace(-18, 18, 1441)
    lm = np.vstack([_pearson_theoretical_lmom(float(sk)) for sk in skew_grid])
    tau = lm[:, 2] / lm[:, 1]
    order = np.argsort(tau)
    return tau[order], skew_grid[order], lm[order]


def _pearson_lmom_skew(target_tau3):
    taus, skews, _ = _pearson_lmom_table()
    if target_tau3 < taus[0] or target_tau3 > taus[-1]:
        raise ValueError("L-skewness muestral fuera del dominio de Pearson III.")
    return float(np.interp(target_tau3, taus, skews))


def fit_distribution(x, distribution, method):
    x = np.asarray(x, dtype=float)
    if len(x) < 4 or np.any(~np.isfinite(x)):
        raise ValueError("Muestra incompleta o demasiado corta.")
    if distribution == "LP3":
        if np.any(x <= 0):
            raise ValueError("LP3 requiere máximos estrictamente positivos.")
        y = np.log10(x)
        if method == "MOM":
            return {"skew": float(stats.skew(y, bias=False)), "loc": float(np.mean(y)),
                    "scale": float(np.std(y, ddof=1)), "log_base": 10}
        if method == "LMOM":
            l1, l2, _, _, tau3, _ = sample_lmoments(y)
            skew = _pearson_lmom_skew(tau3)
            taus, skews, table = _pearson_lmom_table()
            idx = int(np.searchsorted(skews, skew).clip(0, len(skews) - 1))
            tlm = table[idx]
            scale = l2 / tlm[1]
            loc = l1 - scale * tlm[0]
            return {"skew": skew, "loc": float(loc), "scale": float(scale), "log_base": 10}
        if method == "MLE":
            skew, loc, scale = pearson3.fit(y)
            return {"skew": float(skew), "loc": float(loc), "scale": float(scale), "log_base": 10}
    elif distribution == "Gumbel":
        if method == "MOM":
            scale = np.std(x, ddof=1) * math.sqrt(6) / math.pi
            return {"loc": float(np.mean(x) - GAMMA_EULER * scale), "scale": float(scale)}
        if method == "LMOM":
            l1, l2, *_ = sample_lmoments(x)
            scale = l2 / math.log(2)
            return {"loc": float(l1 - GAMMA_EULER * scale), "scale": float(scale)}
        if method == "MLE":
            loc, scale = gumbel_r.fit(x)
            return {"loc": float(loc), "scale": float(scale)}
    elif distribution == "GEV":
        if method == "LMOM":
            return _gev_lmom_fit(x)
        if method == "MLE":
            c, loc, scale = genextreme.fit(x)
            return {"c": float(c), "xi": float(-c), "loc": float(loc), "scale": float(scale)}
        if method == "MOM":
            mean = float(np.mean(x)); sd = float(np.std(x, ddof=1))
            target = float(stats.skew(x, bias=False))
            def objective(c):
                sk = genextreme.stats(c, moments="s")
                return (float(sk) - target) ** 2 if np.isfinite(sk) else 1e100
            opt = optimize.minimize_scalar(objective, bounds=(-0.32, 0.95), method="bounded")
            c = float(opt.x)
            _, var0 = genextreme.stats(c, moments="mv")
            std0 = math.sqrt(float(var0))
            mean0 = genextreme.mean(c)
            scale = sd / float(std0)
            loc = mean - scale * float(mean0)
            return {"c": c, "xi": -c, "loc": float(loc), "scale": float(scale)}
    raise ValueError(f"Método/distribución no soportados: {distribution}/{method}")


def ppf(prob, distribution, params):
    if distribution == "Gumbel":
        return gumbel_r.ppf(prob, loc=params["loc"], scale=params["scale"])
    if distribution == "GEV":
        return genextreme.ppf(prob, params["c"], loc=params["loc"], scale=params["scale"])
    if distribution == "LP3":
        y = pearson3.ppf(prob, params["skew"], loc=params["loc"], scale=params["scale"])
        return np.power(10.0, y)
    raise ValueError(distribution)


def cdf(values, distribution, params):
    if distribution == "Gumbel":
        return gumbel_r.cdf(values, loc=params["loc"], scale=params["scale"])
    if distribution == "GEV":
        return genextreme.cdf(values, params["c"], loc=params["loc"], scale=params["scale"])
    if distribution == "LP3":
        return pearson3.cdf(np.log10(np.asarray(values)), params["skew"], loc=params["loc"], scale=params["scale"])
    raise ValueError(distribution)


def parameter_row(duration, distribution, method, params):
    return {"duration_h": duration, "distribution": distribution, "method": method,
            "loc": params.get("loc", np.nan), "scale": params.get("scale", np.nan),
            "shape": params.get("skew", params.get("xi", np.nan)),
            "gev_xi": params.get("xi", np.nan), "scipy_genextreme_c": params.get("c", np.nan),
            "pearson3_skew_log10": params.get("skew", np.nan),
            "parameter_location_scale": "log10(mm/h)" if distribution == "LP3" else "mm/h"}


def goodness(values, distribution, params):
    x = np.sort(np.asarray(values, dtype=float)); n = len(x)
    probs = np.clip(cdf(x, distribution, params), 1e-12, 1 - 1e-12)
    ks = float(np.max(np.maximum(np.arange(1, n + 1) / n - probs, probs - np.arange(n) / n)))
    i = np.arange(1, n + 1)
    ad = float(-n - np.sum((2 * i - 1) * (np.log(probs) + np.log(1 - probs[::-1]))) / n)
    plotting = (i - 0.375) / (n + 0.25)
    theoretical = np.asarray(ppf(plotting, distribution, params), dtype=float)
    ppcc = float(np.corrcoef(x, theoretical)[0, 1])
    return ks, ad, ppcc


def mann_kendall_sen(years, values):
    years = np.asarray(years, dtype=float); values = np.asarray(values, dtype=float)
    n = len(values)
    slopes = [(values[j] - values[i]) / (years[j] - years[i])
              for i in range(n - 1) for j in range(i + 1, n)]
    sen = float(np.median(slopes)) if slopes else np.nan
    s = 0
    for i in range(n - 1):
        s += int(np.sign(values[i + 1:] - values[i]).sum())
    _, ties = np.unique(values, return_counts=True)
    var_s = (n * (n - 1) * (2 * n + 5) - sum(t * (t - 1) * (2 * t + 5) for t in ties)) / 18
    if var_s <= 0:
        return int(s), 0.0, 1.0, sen
    z = (s - 1) / math.sqrt(var_s) if s > 0 else ((s + 1) / math.sqrt(var_s) if s < 0 else 0.0)
    p = float(2 * stats.norm.sf(abs(z)))
    return int(s), float(z), p, sen


def annual_maxima():
    if not CLEAN.is_file() or not SUMMARY.is_file():
        raise FileNotFoundError("Se requieren precip_horaria_limpia.csv y resumen_completitud_anual.csv.")
    accepted = set(pd.read_csv(SUMMARY).loc[lambda d: d.retained.astype(str).str.strip().str.lower().isin(["sí", "si"]), "year"].astype(int))
    frame = pd.read_csv(CLEAN, usecols=["timestamp", "precip_mm", "precip_state"], low_memory=False,
                        parse_dates=["timestamp"])
    valid = frame.precip_state.isin(["zero", "value", "trace"])
    frame["precip_mm"] = pd.to_numeric(frame.precip_mm, errors="coerce")
    frame = frame.loc[valid & frame.precip_mm.notna()].copy()
    # Año hidrológico nombrado por el año en que termina: octubre-septiembre.
    frame["hydro_year"] = frame.timestamp.dt.year + frame.timestamp.dt.month.ge(10).astype(int)
    frame = frame.loc[frame.hydro_year.isin(accepted)].copy()
    if frame.empty:
        raise ValueError("No hay observaciones válidas dentro de los años hidrológicos aceptados.")
    # Reindex each accepted hydro-year to every hour; rolling windows require
    # complete data, so a missing hour invalidates any window spanning it.
    maxima = []
    for year, group in frame.groupby("hydro_year", sort=True):
        start = pd.Timestamp(int(year) - 1, 10, 1, tz="UTC")
        end = pd.Timestamp(int(year), 10, 1, tz="UTC")
        index = pd.date_range(start, end, freq="h", inclusive="left")
        hourly = group.set_index("timestamp").precip_mm.reindex(index)
        record = {"hydro_year": int(year), "valid_hours": int(hourly.notna().sum())}
        for d in DURATIONS:
            depth = hourly.rolling(d, min_periods=d).sum().max()
            raw_depth = float(depth) if pd.notna(depth) else np.nan
            factor = 1.0 / (1.0 - 1.0 / (8.0 * d))
            corrected_depth = raw_depth * factor if np.isfinite(raw_depth) else np.nan
            record.update({f"max_depth_{d}h_mm": corrected_depth,
                           f"intensity_{d}h_mmh": corrected_depth / d if np.isfinite(corrected_depth) else np.nan,
                           f"weiss_factor_{d}h": factor})
        maxima.append(record)
    max_df = pd.DataFrame(maxima).sort_values("hydro_year")
    depths = np.column_stack([max_df[f"max_depth_{d}h_mm"].to_numpy(float) for d in DURATIONS])
    for row_i, yr in enumerate(max_df.hydro_year):
        vals = depths[row_i]
        finite = vals[np.isfinite(vals)]
        monotone = bool(np.all(np.diff(finite) >= -1e-10)) if len(finite) == len(DURATIONS) else False
        max_df.loc[max_df.hydro_year.eq(yr), "depth_monotone_after_weiss"] = monotone
    if not max_df.depth_monotone_after_weiss.all():
        warnings.warn("Hay años en que la corrección de Weiss rompe la monotonicidad de lámina con duración; revise la tabla.")
    max_df.to_csv(MAXIMA_CSV, index=False, float_format="%.6f", encoding="utf-8")
    return max_df


def main():
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    maxima = annual_maxima()
    samples = {}
    for duration in DURATIONS:
        col = f"intensity_{duration}h_mmh"
        series = maxima[["hydro_year", col]].dropna()
        samples[duration] = (series.hydro_year.to_numpy(int), series[col].to_numpy(float))
        if len(samples[duration][1]) < 20:
            warnings.warn(f"Duración {duration} h tiene solo {len(samples[duration][1])} máximos utilizables.")

    # L-moment ratios and trend are computed once per duration; fit diagnostics
    # and parameters are reported for every distribution/method combination.
    params_rows, quantile_rows, gof_rows = [], [], []
    fitted = {}
    rng = np.random.default_rng(SEED)
    for duration in DURATIONS:
        years, values = samples[duration]
        lm = sample_lmoments(values)
        trend_s, trend_z, trend_p, sen = mann_kendall_sen(years, values)
        for distribution in ("Gumbel", "GEV", "LP3"):
            for method in ("MOM", "LMOM", "MLE"):
                key = (duration, distribution, method)
                try:
                    params = fit_distribution(values, distribution, method)
                    fitted[key] = params
                    params_rows.append(parameter_row(duration, distribution, method, params))
                    ks, ad, ppcc = goodness(values, distribution, params)
                    gof_rows.append({"duration_h": duration, "distribution": distribution, "method": method,
                                     "n": len(values), "KS": ks, "AD": ad, "PPCC": ppcc,
                                     "sample_L1": lm[0], "sample_L2": lm[1], "tau3": lm[4], "tau4": lm[5],
                                     "MK_S": trend_s, "MK_Z": trend_z, "MK_pvalue": trend_p,
                                     "Sen_slope_mmh_per_hydroyear": sen})
                except Exception as exc:
                    warnings.warn(f"Ajuste fallido {key}: {exc}")
                    continue

                point_q = np.asarray(ppf(1 - 1 / np.asarray(RETURN_PERIODS), distribution, params), dtype=float)
                boot = np.full((BOOTSTRAPS, len(RETURN_PERIODS)), np.nan)
                for b in range(BOOTSTRAPS):
                    resample = rng.choice(values, size=len(values), replace=True)
                    try:
                        bp = fit_distribution(resample, distribution, method)
                        boot[b, :] = ppf(1 - 1 / np.asarray(RETURN_PERIODS), distribution, bp)
                    except Exception:
                        pass
                for j, period in enumerate(RETURN_PERIODS):
                    valid_boot = boot[:, j][np.isfinite(boot[:, j])]
                    low, median, high = np.percentile(valid_boot, [2.5, 50, 97.5]) if len(valid_boot) else (np.nan, np.nan, np.nan)
                    quantile_rows.append({"duration_h": duration, "distribution": distribution, "method": method,
                                          "return_period_y": period, "quantile_mmh": point_q[j],
                                          "ci95_low_mmh": low, "bootstrap_median_mmh": median, "ci95_high_mmh": high,
                                          "bootstrap_success": len(valid_boot), "bootstrap_replicates": BOOTSTRAPS,
                                          "seed": SEED})
                print(f"Duración {duration} h, {distribution}/{method}: bootstrap {BOOTSTRAPS} réplicas completado.")

    pd.DataFrame(params_rows).to_csv(PARAMS_CSV, index=False, float_format="%.8g", encoding="utf-8")
    qdf = pd.DataFrame(quantile_rows)
    qdf.to_csv(QUANTILES_CSV, index=False, float_format="%.8g", encoding="utf-8")
    pd.DataFrame(gof_rows).to_csv(GOF_CSV, index=False, float_format="%.8g", encoding="utf-8")
    make_figures(samples, fitted, qdf)
    print("Convención GEV: SciPy genextreme usa c = -xi; ambos parámetros están guardados explícitamente.")
    print(f"Resultados: {MAXIMA_CSV}, {PARAMS_CSV}, {QUANTILES_CSV}, {GOF_CSV}")
    print(f"Figuras: {FIG_PROB}, {FIG_LMOM}, {FIG_BOOT}")


def make_figures(samples, fitted, qdf):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": .2})
    # Gumbel probability paper with Gringorten plotting positions.
    # Paneles uno debajo de otro, a ~6.5 in (ancho de texto del informe), para que se lean (regla de Juan, 26 nov).
    fig, axes = plt.subplots(3, 1, figsize=(6.5, 10), constrained_layout=True)
    colors = {"Gumbel": "#087e78", "GEV": "#c45b38", "LP3": "#4267ac"}
    for ax, duration in zip(axes, (1, 6, 24)):
        values = np.sort(samples[duration][1]); n = len(values)
        ranks = np.arange(1, n + 1)
        F = (ranks - .44) / (n + 1 - 2 * .44)
        reduced = -np.log(-np.log(F))
        ax.scatter(reduced, values, s=17, color="#263b4a", alpha=.75, label="Observado")
        probs = np.linspace(.02, .995, 250)
        gumbel_x = -np.log(-np.log(probs))
        for dist in ("Gumbel", "GEV", "LP3"):
            p = fitted.get((duration, dist, "LMOM"))
            if p:
                ax.plot(gumbel_x, ppf(probs, dist, p), color=colors[dist], lw=1.8, label=f"{dist} LMOM")
        ax.set(title=f"{duration} h", xlabel="Variable reducida de Gumbel", ylabel="Intensidad máxima (mm/h)")
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle("Papel de probabilidad · posiciones de Gringorten (a = 0.44)")
    fig.savefig(FIG_PROB, bbox_inches="tight"); plt.close(fig)

    # Sample L-ratio plot and theoretical curves using population quantiles.
    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    for duration, (_, vals) in samples.items():
        lm = sample_lmoments(vals)
        ax.scatter(lm[4], lm[5], s=42, label=f"{duration} h", zorder=4)
    u = (np.arange(1000) + .5) / 1000
    for xi in np.linspace(-.35, .32, 80):
        c = -xi
        q = genextreme.ppf(u, c)
        if np.all(np.isfinite(q)):
            lm = sample_lmoments(q)
            ax.plot(lm[4], lm[5], color="#bf5a46", alpha=.35, lw=.8)
    gq = gumbel_r.ppf(u)
    glm = sample_lmoments(gq)
    ax.scatter([glm[4]], [glm[5]], marker="*", s=130, color="#087e78", label="Gumbel teórico")
    # Lognormal and Pearson-III reference curves, standardized by their shapes.
    for sigma in np.linspace(.1, 1.5, 45):
        q = stats.lognorm.ppf(u, s=sigma, scale=1)
        lm = sample_lmoments(q)
        ax.plot(lm[4], lm[5], color="#5b75b5", alpha=.45, lw=.8,
                label="Log-normal" if sigma == .1 else None)
    pearson_points = []
    for sk in np.linspace(-6, 6, 121):
        q = pearson3.ppf(u, sk)
        lm = sample_lmoments(q)
        pearson_points.append((lm[4], lm[5]))
    pearson_points.sort()
    ax.plot([p[0] for p in pearson_points], [p[1] for p in pearson_points], color="#4267ac", lw=1.4, label="Pearson III")
    ax.set(xlabel=r"L-skewness $\tau_3$", ylabel=r"L-kurtosis $\tau_4$", title="Diagrama de razones de L-momentos")
    ax.legend(frameon=False, ncol=2, fontsize=8)
    fig.savefig(FIG_LMOM, bbox_inches="tight"); plt.close(fig)

    # Relative percentile interval width versus T/N for Gumbel-LMOM bootstrap.
    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    for duration in DURATIONS:
        sub = qdf[(qdf.duration_h == duration) & (qdf.distribution == "Gumbel") & (qdf.method == "LMOM")].sort_values("return_period_y")
        if sub.empty:
            continue
        n = len(samples[duration][1])
        width = (sub.ci95_high_mmh - sub.ci95_low_mmh) / sub.bootstrap_median_mmh
        ax.plot(sub.return_period_y / n, width, marker="o", label=f"{duration} h")
    ax.set(xlabel=r"$T/N$", ylabel=r"$(Q_{97.5}-Q_{2.5})/Q_{50}$", title="Incertidumbre bootstrap 95%")
    ax.legend(title="Duración", frameon=False, ncol=3)
    fig.savefig(FIG_BOOT, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    main()
