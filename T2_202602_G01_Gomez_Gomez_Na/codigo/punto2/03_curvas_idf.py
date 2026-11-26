#!/usr/bin/env python3
"""Consistencia de cuantiles y ajuste de curvas IDF del Apartado 2.3.

Requiere numpy, pandas, scipy y matplotlib. Lee únicamente los productos CSV
de 2.2; todas las rutas se resuelven desde la raíz del proyecto.
"""
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[2]
PRODUCTS = ROOT / "productos" / "punto2"
QUANTILES = PRODUCTS / "cuantiles_y_bootstrap.csv"
GOODNESS = PRODUCTS / "bondad_y_estacionariedad.csv"
OUT_PARAMS = PRODUCTS / "parametros_idf.csv"
OUT_TABLE = PRODUCTS / "tabla_idf_completa.csv"
FIG_IDF = PRODUCTS / "fig3_curvas_idf_loglog.png"
FIG_RESID = PRODUCTS / "fig3_comparacion_modelos_idf.png"
DUR_H = np.array([1., 2., 3., 6., 12., 24.])
DUR_MIN = np.array([5, 10, 15, 30, 60, 120, 180, 360, 720, 1440], dtype=int)
RETURNS = np.array([2, 5, 10, 25, 50, 100], dtype=int)
DIST = "LP3"
METHOD = "LMOM"


def pava(values, increasing=True):
    """Unweighted pool-adjacent-violators algorithm."""
    y = np.asarray(values, dtype=float).copy()
    if not increasing:
        return -pava(-y, increasing=True)
    means, weights, starts = [], [], []
    for i, val in enumerate(y):
        means.append(float(val)); weights.append(1.0); starts.append(i)
        while len(means) > 1 and means[-2] > means[-1]:
            w = weights[-2] + weights[-1]
            m = (means[-2] * weights[-2] + means[-1] * weights[-1]) / w
            means[-2:] = [m]; weights[-2:] = [w]; starts.pop()
    out = np.empty_like(y)
    ends = starts[1:] + [len(y)]
    for start, end, mean in zip(starts, ends, means):
        out[start:end] = mean
    return out


def monotone_surface(intensity, durations=DUR_H, max_iter=500, tol=1e-10):
    """Project to increasing depth vs duration and intensity vs return period."""
    x = np.asarray(intensity, dtype=float).copy()
    for _ in range(max_iter):
        old = x.copy()
        # P = i*d is nondecreasing with duration, independently by T.
        for j in range(x.shape[1]):
            x[:, j] = pava(x[:, j] * durations) / durations
        # Larger return periods cannot have lower intensities.
        for i in range(x.shape[0]):
            x[i, :] = pava(x[i, :])
        if np.nanmax(np.abs(x - old)) < tol:
            break
    return x


def n_metrics(observed, predicted):
    obs = np.asarray(observed, float).ravel()
    pred = np.asarray(predicted, float).ravel()
    err = pred - obs
    mape = float(np.mean(np.abs(err / obs)) * 100)
    rmse = float(np.sqrt(np.mean(err ** 2)))
    ss_tot = float(np.sum((obs - obs.mean()) ** 2))
    r2 = float(1 - np.sum(err ** 2) / ss_tot) if ss_tot else np.nan
    return mape, rmse, r2


def _positive_exp(z):
    return np.exp(np.clip(z, -30, 30))


def fit_sherman(d, t, y):
    # i = a*T^m/d^c; positive m ensures no return-period curve crossings.
    ld, lt, ly = np.log(d), np.log(t), np.log(y)
    x0 = np.array([np.median(ly), .35, .65])
    fit = least_squares(lambda z: z[0] + z[1] * lt - z[2] * ld - ly,
                        x0, bounds=([-30, .001, .001], [30, 5, 1.0]))
    a, m, c = np.exp(fit.x[0]), fit.x[1], fit.x[2]
    return {"a": a, "m": m, "b_h": 0.0, "c": c}, lambda dd, tt: a * tt ** m / dd ** c


def fit_talbot(d, t, y):
    # i = a*T^m/(d+b)^c; b is constrained positive.
    ld_t = np.log(t)
    ly = np.log(y)
    def residual(z):
        loga, m, logb, logc = z
        b, c = _positive_exp(logb), _positive_exp(logc)
        return loga + m * ld_t - c * np.log(d + b) - ly
    x0 = [float(np.median(ly)), .35, np.log(.25), np.log(.65)]
    # c<=1 ensures P=i*d is nondecreasing for all d when b>0.
    fit = least_squares(residual, x0, bounds=([-30, .001, -9, -4], [30, 5, 5, 0]))
    loga, m, logb, logc = fit.x
    a, b, c = float(np.exp(loga)), float(np.exp(logb)), float(np.exp(logc))
    return {"a": a, "m": float(m), "b_h": b, "c": c}, lambda dd, tt: a * tt ** m / (dd + b) ** c


def fit_koutsoyiannis(d, t, y):
    """Fit w(T)/(d+b)^c first, then fit w(T)=a*T^m."""
    unique_t = np.unique(t)
    logt = np.log(unique_t)
    def stage(logb, logc):
        b, c = float(np.exp(logb)), float(np.exp(logc))
        logw = np.array([np.mean(np.log(y[t == tv]) + c * np.log(d[t == tv] + b)) for tv in unique_t])
        m, intercept = np.polyfit(logt, logw, 1)
        # Constrain the return-period relation to increase, so fitted curves do not cross.
        if m <= .001:
            m = .001
            intercept = float(np.mean(logw - m * logt))
        return b, c, np.exp(intercept), float(m), logw
    def residual(z):
        b, c, a, m, _ = stage(z[0], z[1])
        return np.log(a) + m * np.log(t) - c * np.log(d + b) - np.log(y)
    # c<=1 ensures P=i*d is nondecreasing for all d when b>0.
    fit = least_squares(residual, [np.log(.25), np.log(.65)], bounds=([-9, -4], [5, 0]))
    b, c, a, m, logw = stage(*fit.x)
    w_by_t = {str(int(tv)): float(np.exp(v)) for tv, v in zip(unique_t, logw)}
    return {"a": a, "m": m, "b_h": b, "c": c,
            "w_by_return_period": ";".join(f"T{key}={value:.8g}" for key, value in w_by_t.items())}, \
        lambda dd, tt: a * tt ** m / (dd + b) ** c


def fit_model(name, d, t, y):
    if name == "Bernard-Sherman":
        return fit_sherman(d, t, y)
    if name == "Talbot-Wenzel":
        return fit_talbot(d, t, y)
    if name == "Koutsoyiannis-1998":
        return fit_koutsoyiannis(d, t, y)
    raise ValueError(name)


def make_figures(base, lo, hi, predictions, residuals, winner, winner_params):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 150, "axes.grid": True, "grid.alpha": .22,
                         "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    dense = np.geomspace(5 / 60, 24, 240)
    colors = dict(zip(RETURNS, ("#5c6bc0", "#00897b", "#e67e22", "#8e44ad", "#c0392b", "#34495e")))
    fig, ax = plt.subplots(figsize=(9, 6), constrained_layout=True)
    ax.axvspan(5 / 60, 1, color="#f4c95d", alpha=.14, label="Extrapolación < 1 h")
    for T in RETURNS:
        ax.plot(dense, predictions[winner][int(T)](dense, np.full_like(dense, T)),
                color=colors[int(T)], label=f"T={T} años")
        if T in (10, 50):
            band_lo = lo[:, list(RETURNS).index(T)]
            band_hi = hi[:, list(RETURNS).index(T)]
            # Propagate the bootstrap bounds with the selected common duration
            # shape (b,c); estimate only the amplitude for this fixed T/bound.
            b, c = winner_params["b_h"], winner_params["c"]
            amp_lo = float(np.exp(np.mean(np.log(band_lo) + c * np.log(DUR_H + b))))
            amp_hi = float(np.exp(np.mean(np.log(band_hi) + c * np.log(DUR_H + b))))
            low_line = np.minimum(amp_lo, amp_hi) / (dense + b) ** c
            high_line = np.maximum(amp_lo, amp_hi) / (dense + b) ** c
            center_line = predictions[winner][int(T)](dense, np.full_like(dense, T))
            low_line = np.minimum(low_line, center_line)
            high_line = np.maximum(high_line, center_line)
            ax.fill_between(dense, low_line, high_line, color=colors[int(T)], alpha=.12)
        j = list(RETURNS).index(T)
        ax.scatter(DUR_H, base[:, j], color=colors[int(T)], edgecolor="white", s=30, zorder=3)
    ax.set(xscale="log", yscale="log", xlim=(5 / 60, 24), xlabel="Duración (h; escala log)",
           ylabel="Intensidad (mm/h; escala log)", title=f"Curvas IDF de Denver Stapleton · modelo {winner}")
    ax.legend(ncol=2, frameon=False)
    fig.savefig(FIG_IDF, bbox_inches="tight"); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True, constrained_layout=True)
    model_names = list(residuals)
    palette = dict(zip(model_names, ("#16836b", "#d99a38", "#5267a8")))
    for ax, T in zip(axes, (2, 10, 50)):
        for name in model_names:
            vals = residuals[name][int(T)]
            ax.plot(DUR_H, vals, marker="o", lw=1.2, label=name, color=palette[name])
        ax.axhline(0, color="#666", lw=.8)
        ax.set(xscale="log", title=f"T={T} años", xlabel="Duración (h)")
    axes[0].set_ylabel("Residuo relativo (%)")
    axes[-1].legend(frameon=False, fontsize=8)
    fig.suptitle("Comparación de residuales de las formulaciones IDF")
    fig.savefig(FIG_RESID, bbox_inches="tight"); plt.close(fig)


def main():
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    qdf = pd.read_csv(QUANTILES, low_memory=False)
    gdf = pd.read_csv(GOODNESS, low_memory=False)
    required_q = {"duration_h", "distribution", "method", "return_period_y", "quantile_mmh", "ci95_low_mmh", "ci95_high_mmh"}
    required_g = {"duration_h", "distribution", "method", "KS", "AD", "MK_S", "MK_pvalue", "Sen_slope_mmh_per_hydroyear"}
    if not required_q.issubset(qdf.columns):
        raise ValueError(f"Columnas inesperadas en cuantiles_y_bootstrap.csv. Encontradas: {list(qdf.columns)}")
    if not required_g.issubset(gdf.columns):
        raise ValueError(f"Columnas inesperadas en bondad_y_estacionariedad.csv. Encontradas: {list(gdf.columns)}")
    print("Columnas de cuantiles:", list(qdf.columns))
    print("Columnas de bondad/estacionariedad:", list(gdf.columns))

    selected = qdf[(qdf.distribution == "LP3") & (qdf.method == "LMOM") & qdf.duration_h.isin(DUR_H) & qdf.return_period_y.isin(RETURNS)].copy()
    if selected.empty:
        raise ValueError("No se encontraron cuantiles LP3 / LMOM para las duraciones y periodos solicitados.")
    def pivot(column):
        return selected.pivot(index="duration_h", columns="return_period_y", values=column).reindex(index=DUR_H, columns=RETURNS).to_numpy(float)
    raw = pivot("quantile_mmh")
    raw_lo, raw_hi = pivot("ci95_low_mmh"), pivot("ci95_high_mmh")
    if np.any(~np.isfinite(raw)):
        raise ValueError("Faltan cuantiles LP3/LMOM para alguna combinación duración/retorno.")
    base = monotone_surface(raw)
    lo, hi = monotone_surface(raw_lo), monotone_surface(raw_hi)
    # Keep bands ordered around the adjusted point estimates.
    lo = np.minimum(lo, base); hi = np.maximum(hi, base)
    before_depth = raw * DUR_H[:, None]
    after_depth = base * DUR_H[:, None]
    input_depth_violations = int(np.sum(np.diff(before_depth, axis=0) < -1e-9))
    adjusted_depth_violations = int(np.sum(np.diff(after_depth, axis=0) < -1e-9))
    print(f"Máxima modificación isotónica de intensidad: {np.max(np.abs(base - raw)):.6g} mm/h")
    print("Monotonicidad de P(d,T) tras ajuste:", bool(np.all(np.diff(after_depth, axis=0) >= -1e-9)))
    print("Monotonicidad de i(d,T) con T tras ajuste:", bool(np.all(np.diff(base, axis=1) >= -1e-9)))

    # Selection justification is checked within the like-for-like LMOM family.
    gof = gdf[gdf.method == "LMOM"].copy()
    wins = []
    for duration in DUR_H:
        rows = gof[gof.duration_h == duration].set_index("distribution")
        if not {"LP3", "GEV", "Gumbel"}.issubset(rows.index):
            wins.append({"duration_h": duration, "LP3_lower_KS": False, "LP3_lower_AD": False})
        else:
            wins.append({"duration_h": duration,
                         "LP3_lower_KS": bool(rows.loc["LP3", "KS"] <= rows.loc[["GEV", "Gumbel"], "KS"].min()),
                         "LP3_lower_AD": bool(rows.loc["LP3", "AD"] <= rows.loc[["GEV", "Gumbel"], "AD"].min())})
    selection = pd.DataFrame(wins)
    if not selection[["LP3_lower_KS", "LP3_lower_AD"]].all().all():
        warnings.warn("LP3/LMOM no supera KS y AD en todas las duraciones frente a GEV/Gumbel LMOM; se conserva como principal por instrucción, con comparación transparente.")
    print("LP3/LMOM gana o empata KS/AD contra GEV/Gumbel LMOM en todas las duraciones:",
          bool(selection[["LP3_lower_KS", "LP3_lower_AD"]].all().all()))

    dflat = np.repeat(DUR_H, len(RETURNS))
    tflat = np.tile(RETURNS.astype(float), len(DUR_H))
    yflat = base.ravel()
    model_names = ["Bernard-Sherman", "Talbot-Wenzel", "Koutsoyiannis-1998"]
    params_rows, predictions, residuals, model_params = [], {}, {}, {}
    fit_scores = {}
    for name in model_names:
        params, fn = fit_model(name, dflat, tflat, yflat)
        pred = fn(DUR_H[:, None], RETURNS[None, :].astype(float))
        mape, rmse, r2 = n_metrics(base, pred)
        crossings = int(np.sum(np.diff(pred, axis=1) < -1e-9))
        curves_non_crossing = crossings == 0
        fit_scores[name] = (mape, rmse)
        model_params[name] = params
        predictions[name] = {int(T): (lambda dd, tt, _fn=fn: _fn(dd, tt)) for T in RETURNS}
        residuals[name] = {int(T): 100 * (pred[:, j] - base[:, j]) / base[:, j] for j, T in enumerate(RETURNS)}
        params_rows.append({"formulacion": name, **params, "MAPE_pct": mape, "RMSE_mmh": rmse,
                            "R2": r2, "T_curve_crossings": crossings,
                            "curvas_no_cruzan": curves_non_crossing,
                            "P_no_decrece_por_restriccion_c_le_1": bool(params["c"] <= 1 + 1e-10),
                            "violaciones_P_antes": input_depth_violations,
                            "violaciones_P_despues": adjusted_depth_violations,
                            "isotonic_max_adjustment_mmh": float(np.max(np.abs(base - raw))),
                            "selection_LP3_LMOM_lower_KS_all": bool(selection.LP3_lower_KS.all()),
                            "selection_LP3_LMOM_lower_AD_all": bool(selection.LP3_lower_AD.all())})
    winner_overall = min(model_names, key=lambda n: fit_scores[n][0])
    offset_models = ["Talbot-Wenzel", "Koutsoyiannis-1998"]
    winner = min(offset_models, key=lambda n: fit_scores[n][0])
    for row in params_rows:
        row["ganador_global"] = row["formulacion"] == winner_overall
        row["modelo_maestro_b_positivo"] = row["formulacion"] == winner
    print("Métricas por formulación (MAPE, RMSE):", fit_scores)
    print(f"Ganador global por MAPE: {winner_overall}; modelo ganador con b>0 usado para tabla/figura: {winner}.")

    # Fit lower/upper empirical bootstrap bounds by duration to propagate them
    # through the selected positive-offset IDF model, including sub-hour hours.
    band_fits = {}
    for j, T in enumerate(RETURNS):
        band_fits[int(T)] = []
        for band in (lo[:, j], hi[:, j]):
            p, f = fit_model(winner, DUR_H, np.full(len(DUR_H), float(T)), band)
            band_fits[int(T)].append((p, f))

    master = []
    for minutes in DUR_MIN:
        dh = minutes / 60.0
        for j, T in enumerate(RETURNS):
            intensity = float(predictions[winner][int(T)](np.array([dh]), np.array([float(T)]))[0])
            band_preds = [float(f(np.array([dh]), np.array([float(T)]))[0]) for _, f in band_fits[int(T)]]
            low_i, high_i = min(band_preds), max(band_preds)
            low_i, high_i = min(low_i, intensity), max(high_i, intensity)
            master.append({"duration_min": int(minutes), "duration_h": dh, "return_period_y": int(T),
                           "intensity_mmh": intensity, "depth_mm": intensity * dh,
                           "ci95_low_mmh": low_i, "ci95_high_mmh": high_i,
                           "ci95_low_depth_mm": low_i * dh, "ci95_high_depth_mm": high_i * dh,
                           "extrapolated_subhour": bool(minutes < 60), "model": winner})
    master_df = pd.DataFrame(master)
    master_df.to_csv(OUT_TABLE, index=False, float_format="%.8g", encoding="utf-8")
    pd.DataFrame(params_rows).to_csv(OUT_PARAMS, index=False, float_format="%.8g", encoding="utf-8")
    make_figures(base, lo, hi, predictions, residuals, winner, model_params[winner])

    trend = gdf[(gdf.distribution == "LP3") & (gdf.method == "LMOM")].drop_duplicates("duration_h")
    if (trend.MK_S < 0).all():
        print("Aviso de interpretación: Mann-Kendall es negativo en las seis duraciones. El cambio en frecuencia de muestreo/reportes después de 1973 puede contribuir a una inhomogeneidad; no debe atribuirse causalidad sin una prueba de homogeneidad independiente.")
    print(f"Tabla IDF: {OUT_TABLE}\nParámetros y métricas: {OUT_PARAMS}")
    print(f"Figuras: {FIG_IDF}, {FIG_RESID}")


if __name__ == "__main__":
    main()
