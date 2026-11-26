#!/usr/bin/env python3
"""Problema B: tanque de detención y comparación de hidrogramas en Denver.

Las entradas son productos locales del Problema A e IDF Talbot-Wenzel. Las
rutas se derivan de la raíz del proyecto a partir de este archivo.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRODUCTS = ROOT / "productos" / "punto2"
PROBLEM_A = PRODUCTS / "problemaA_alcantarilla.csv"
IDF_PARAMS = PRODUCTS / "parametros_idf.csv"
IDF_TABLE = PRODUCTS / "tabla_idf_completa.csv"
OUT_CSV = PRODUCTS / "problemaB_tanque_detencion.csv"
FIG_PATH = PRODUCTS / "fig_24_problemaB_tanque.png"

T_Y = 50
C_URB = 0.78
TC_URB_MIN = 30.0
STORM_MIN = 180.0
RAIN_DT_MIN = 5.0
ROUTE_DT_S = 60.0
TANK_AREA_M2 = 18000.0
TANK_MAX_H_M = 3.5
CD = 0.61
G = 9.80665
DURATIONS_MIN = (30, 45, 60, 75, 90, 120, 150, 180, 240, 360)


def inputs():
    for path in (PROBLEM_A, IDF_PARAMS, IDF_TABLE):
        if not path.is_file():
            raise FileNotFoundError(f"Falta insumo local: {path.relative_to(ROOT)}")
    a = pd.read_csv(PROBLEM_A, low_memory=False).iloc[0]
    parameters = pd.read_csv(IDF_PARAMS, low_memory=False)
    idf = pd.read_csv(IDF_TABLE, low_memory=False)
    row = parameters[parameters.formulacion.astype(str).str.casefold().eq("talbot-wenzel")]
    if row.empty:
        raise ValueError("parametros_idf.csv no contiene Talbot-Wenzel.")
    p = row.iloc[0]
    tw = {key: float(p[key]) for key in ("a", "m", "b_h", "c")}
    return a, idf, tw


def intensity_mmh(duration_min: float, T: int, tw: dict) -> float:
    duration_h = duration_min / 60.0
    return tw["a"] * T**tw["m"] / (duration_h + tw["b_h"]) ** tw["c"]


def qpeak_rational(duration_min: float, area_km2: float, C: float, tw: dict) -> tuple[float, float]:
    intensity = intensity_mmh(duration_min, T_Y, tw)
    return C * intensity * area_km2 / 3.6, intensity


def trapezoid_hydrograph(duration_min: float, tc_min: float, area_km2: float,
                         coefficient: float, tw: dict) -> dict:
    q_peak, i_peak = qpeak_rational(duration_min, area_km2, coefficient, tw)
    total_end = duration_min + tc_min
    time_min = np.arange(0.0, total_end + ROUTE_DT_S / 60.0, ROUTE_DT_S / 60.0)
    q = np.zeros_like(time_min)
    rising = (time_min >= 0) & (time_min < tc_min)
    q[rising] = q_peak * time_min[rising] / tc_min
    plateau = (time_min >= tc_min) & (time_min <= duration_min)
    q[plateau] = q_peak
    recession = (time_min > duration_min) & (time_min <= total_end)
    q[recession] = q_peak * (total_end - time_min[recession]) / tc_min
    return {"time_min": time_min, "qin_m3s": q, "duration_min": duration_min,
            "qpeak_m3s": q_peak, "intensity_mmh": i_peak}


def block_depths(duration_min: float, dt_min: float, T: int, tw: dict) -> np.ndarray:
    count = int(round(duration_min / dt_min))
    edges = np.arange(0, count + 1, dtype=float) * dt_min
    cumulative = np.zeros(count + 1, dtype=float)
    positive = edges[1:] > 0
    for idx in np.flatnonzero(positive) + 1:
        dmin = edges[idx]
        cumulative[idx] = intensity_mmh(dmin, T, tw) * dmin / 60.0
    increments = np.diff(cumulative)
    if np.any(increments < -1e-9):
        raise ValueError("La curva IDF produce láminas incrementales negativas.")
    return np.maximum(increments, 0)


def arrange_blocks(depths: np.ndarray, pattern: str) -> np.ndarray:
    ordered = np.sort(depths)[::-1]
    n = len(depths)
    result = np.zeros(n, dtype=float)
    if pattern == "pico_al_inicio_decreciente":
        result[:] = ordered
    elif pattern == "pico_al_final_creciente":
        result[:] = ordered[::-1]
    elif pattern == "pico_al_centro_bloques_alternos":
        center_left = (n - 1) // 2
        positions = [center_left]
        distance = 1
        while len(positions) < n:
            for pos in (center_left - distance, center_left + distance):
                if 0 <= pos < n:
                    positions.append(pos)
            distance += 1
        result[np.asarray(positions[:n], dtype=int)] = ordered
    else:
        raise ValueError(f"Patrón desconocido: {pattern}")
    return result


def time_area_hydrograph(pattern: str, area_km2: float, coefficient: float,
                         tw: dict) -> dict:
    # Todos los patrones se forman con los mismos incrementos de lluvia
    # derivados de la curva DDF y, por tanto, conservan lámina total idéntica.
    depths = block_depths(STORM_MIN, RAIN_DT_MIN, T_Y, tw)
    arranged = arrange_blocks(depths, pattern)
    block_intensity = arranged / (RAIN_DT_MIN / 60.0)
    nstorm = len(arranged)
    n_tail = int(round(TC_URB_MIN / RAIN_DT_MIN))
    # Cada valor representa la intensidad durante el intervalo anterior; las
    # últimas tc/Δt celdas vacías permiten completar la respuesta temporal.
    series = np.r_[block_intensity, np.zeros(n_tail + 1)]
    rolling = np.convolve(series, np.ones(n_tail) / n_tail, mode="full")[:len(series)]
    time_min = np.arange(len(series) + 1, dtype=float) * RAIN_DT_MIN
    q = np.zeros_like(time_min)
    q[1:] = coefficient * area_km2 / 3.6 * rolling
    return {
        "time_min": time_min, "qin_m3s": q, "duration_min": STORM_MIN,
        "qpeak_m3s": float(np.max(q)),
        "intensity_mmh": float(np.max(rolling)),
        "rain_depth_mm": float(np.sum(arranged)),
        "rain_depth_blocks_mm": arranged,
        "block_intensity_mmh": block_intensity,
        "pattern": pattern,
    }


def orifice_discharge(head_m: float, diameter_m: float) -> float:
    area = math.pi * diameter_m**2 / 4
    effective_head = max(head_m - diameter_m / 2, 0.0)
    return CD * area * math.sqrt(2 * G * effective_head)


def route_level_pool(profile: dict, orifice_diameter_m: float) -> dict:
    times_min = np.asarray(profile["time_min"], dtype=float)
    qin = np.asarray(profile["qin_m3s"], dtype=float)
    end_sec = max(times_min) * 60
    time_sec = np.arange(0, end_sec + ROUTE_DT_S, ROUTE_DT_S)
    q_in_route = np.interp(time_sec / 60, times_min, qin, left=0.0, right=0.0)
    storage = np.zeros(len(time_sec), dtype=float)

    def inflow(t_sec: float) -> float:
        return float(np.interp(t_sec, time_sec, q_in_route, left=0.0, right=0.0))

    def derivative(t_sec: float, volume: float) -> float:
        head = max(volume, 0.0) / TANK_AREA_M2
        return inflow(t_sec) - orifice_discharge(head, orifice_diameter_m)

    for index in range(len(time_sec) - 1):
        t = time_sec[index]
        v = storage[index]
        dt = ROUTE_DT_S
        k1 = derivative(t, v)
        k2 = derivative(t + dt / 2, v + dt * k1 / 2)
        k3 = derivative(t + dt / 2, v + dt * k2 / 2)
        k4 = derivative(t + dt, v + dt * k3)
        storage[index + 1] = max(0.0, v + dt * (k1 + 2*k2 + 2*k3 + k4) / 6)

    head = storage / TANK_AREA_M2
    outflow = np.array([orifice_discharge(h, orifice_diameter_m) for h in head])
    return {
        "time_min": time_sec / 60, "qin_m3s": q_in_route, "qout_m3s": outflow,
        "storage_m3": storage, "head_m": head,
        "orifice_diameter_m": orifice_diameter_m,
        "q_in_max_m3s": float(np.max(q_in_route)),
        "q_out_max_m3s": float(np.max(outflow)),
        "storage_max_m3": float(np.max(storage)),
        "head_max_m": float(np.max(head)),
        "overflow_m3": float(max(0.0, np.max(storage) - TANK_AREA_M2 * TANK_MAX_H_M)),
    }


def route_all(profiles: dict[str, dict], diameter_m: float) -> dict[str, dict]:
    return {name: route_level_pool(profile, diameter_m) for name, profile in profiles.items()}


def size_orifice(profiles: dict[str, dict], q_limit: float) -> tuple[float, dict[str, dict]]:
    # Busca el mayor diámetro que conserva Omax<=Qlim en todos los eventos,
    # entre los que también caben en la altura útil. Un diámetro mayor reduce
    # el almacenamiento, pero eleva las descargas máximas.
    feasible = []
    infeasible = []
    for diameter in np.linspace(0.03, 1.50, 61):
        routed = route_all(profiles, float(diameter))
        max_out = max(r["q_out_max_m3s"] for r in routed.values())
        max_head = max(r["head_max_m"] for r in routed.values())
        if max_out <= q_limit + 1e-6 and max_head <= TANK_MAX_H_M:
            feasible.append(float(diameter))
        else:
            infeasible.append(float(diameter))
    if not feasible:
        raise RuntimeError("No hay diámetro de orificio que cumpla Qlim y altura útil; aumente volumen del tanque o revise IDF.")
    low = max(feasible)
    if low >= 1.5:
        return low, route_all(profiles, low)
    # Refinamiento hacia el límite Qlim, manteniendo factibilidad hidráulica.
    high = min((value for value in infeasible if value > low), default=min(1.5, low + 0.025))
    for _ in range(24):
        mid = (low + high) / 2
        routed = route_all(profiles, mid)
        max_out = max(r["q_out_max_m3s"] for r in routed.values())
        max_head = max(r["head_max_m"] for r in routed.values())
        if max_out <= q_limit and max_head <= TANK_MAX_H_M:
            low = mid
        else:
            high = mid
    final = route_all(profiles, low)
    return low, final


def summarize(profile: dict, routed: dict, scenario_type: str,
              pattern: str, duration_min: float, q_limit: float,
              orifice_diameter_m: float, area_km2: float,
              dcrit: float = np.nan) -> dict:
    return {
        "scenario_type": scenario_type, "pattern": pattern,
        "duration_min": duration_min, "d_crit_min": dcrit,
        "T_y": T_Y, "C_urban": C_URB, "tc_urban_min": TC_URB_MIN,
        "rain_depth_mm": profile.get("rain_depth_mm", np.nan),
        "Imax_m3s": routed["q_in_max_m3s"],
        "Omax_m3s": routed["q_out_max_m3s"], "Qlim_m3s": q_limit,
        "Vreq_m3": routed["storage_max_m3"], "hmax_m": routed["head_max_m"],
        "tank_area_m2": TANK_AREA_M2, "tank_hmax_m": TANK_MAX_H_M,
        "tank_footprint_ha": TANK_AREA_M2 / 10000.0,
        "tank_fraction_basin_pct": TANK_AREA_M2 / (area_km2 * 1e6) * 100,
        "tank_capacity_m3": TANK_AREA_M2 * TANK_MAX_H_M,
        "orifice_diameter_m": orifice_diameter_m,
        "orifice_Cd": CD, "route_dt_min": ROUTE_DT_S / 60,
        "exceeds_Qlim": bool(routed["q_out_max_m3s"] > q_limit + 1e-6),
        "exceeds_tank_height": bool(routed["head_max_m"] > TANK_MAX_H_M),
        "overflow_volume_m3": routed["overflow_m3"],
    }


def make_figure(trapezoids: dict[str, dict], time_area_profiles: dict[str, dict],
                routed: dict[str, dict], rows: pd.DataFrame, dcrit: float,
                q_limit: float, output: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.7), constrained_layout=True)
    trap_rows = rows[rows.scenario_type.eq("racional_modificado")].sort_values("duration_min")
    ax1.plot(trap_rows.duration_min, trap_rows.Vreq_m3, marker="o", lw=2.2, color="#197b70")
    critical_row = trap_rows.loc[trap_rows.Vreq_m3.idxmax()]
    ax1.scatter([dcrit], [critical_row.Vreq_m3], s=90, zorder=4, color="#d14a3a",
                label=f"Crítica: {dcrit:.0f} min")
    ax1.axhline(TANK_AREA_M2 * TANK_MAX_H_M, color="#697985", ls="--", label="Volumen útil del tanque")
    ax1.set_xlabel("Duración de tormenta d (min)"); ax1.set_ylabel("Almacenamiento máximo Vreq (m³)")
    ax1.set_title("Racional modificado · duración crítica")
    ax1.grid(alpha=0.25); ax1.legend(fontsize=8)

    critical_name = f"trap_{int(dcrit)}"
    plot_profiles = [(critical_name, trapezoids[critical_name], "Trapezoidal crítico", "#a64137")]
    pattern_labels = {
        "pico_al_inicio_decreciente": ("Pico inicial", "#3678a8"),
        "pico_al_centro_bloques_alternos": ("Pico central", "#76549a"),
        "pico_al_final_creciente": ("Pico final", "#d28a27"),
    }
    for key, profile in time_area_profiles.items():
        plot_profiles.append((key, profile, pattern_labels[profile["pattern"]][0],
                              pattern_labels[profile["pattern"]][1]))

    ax2b = ax2.twinx()
    for key, profile, label, color in plot_profiles:
        routed_event = routed[key]
        xh = routed_event["time_min"] / 60
        ax2.plot(xh, routed_event["qin_m3s"], color=color, lw=1.5, alpha=0.8,
                 label=f"Entrada · {label}")
        ax2.plot(xh, routed_event["qout_m3s"], color=color, lw=2, ls="--",
                 label=f"Salida · {label}")
        ax2b.plot(xh, routed_event["storage_m3"], color=color, lw=1.15, ls=":", alpha=0.75,
                  label="S(t), colores por patrón" if key == plot_profiles[0][0] else "_nolegend_")
    ax2.axhline(q_limit, color="#222222", lw=1.2, ls="-.", label="$Q_{lim}$")
    ax2.set_xlabel("Tiempo (h)"); ax2.set_ylabel("Caudal I(t), O(t) (m³/s)")
    ax2b.set_ylabel("Almacenamiento S(t) (m³)")
    ax2.set_title("Hidrogramas y tránsito por piscina nivelada")
    ax2.grid(alpha=0.2)
    h1, l1 = ax2.get_legend_handles_labels(); h2, l2 = ax2b.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right", ncol=2)
    fig.suptitle(f"Tanque de detención · T={T_Y} años · Do={next(iter(routed.values()))['orifice_diameter_m']*1000:.0f} mm",
                 fontsize=14, weight="bold")
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    a, idf, tw = inputs()
    area = float(a["area_km2"])
    q_limit = float(a["Qp_rational_m3s"])
    c_previous = float(a["C_weighted"])
    tc_previous = float(a["tc_design_min"])
    if not np.isclose(area, 1.0269, atol=5e-4):
        print(f"Nota: el área local leída es {area:.4f} km², distinta del ejemplo redondeado 1.0269 km².")
    # Recalcula Qp previo desde los insumos IDF como control de consistencia.
    q_previous_check, _ = qpeak_rational(tc_previous, area, c_previous, tw)
    profiles: dict[str, dict] = {}
    trapezoids: dict[str, dict] = {}
    for duration in DURATIONS_MIN:
        key = f"trap_{duration}"
        profile = trapezoid_hydrograph(duration, TC_URB_MIN, area, C_URB, tw)
        trapezoids[key] = profile; profiles[key] = profile
    patterns = (
        "pico_al_inicio_decreciente",
        "pico_al_centro_bloques_alternos",
        "pico_al_final_creciente",
    )
    time_area_profiles = {}
    for pattern in patterns:
        key = f"area_{pattern}"
        profile = time_area_hydrograph(pattern, area, C_URB, tw)
        time_area_profiles[key] = profile; profiles[key] = profile

    orifice_diameter, routed = size_orifice(profiles, q_limit)
    trap_rows = []
    for duration in DURATIONS_MIN:
        key = f"trap_{duration}"
        trap_rows.append(summarize(trapezoids[key], routed[key], "racional_modificado",
                                   "trapezoidal", duration, q_limit, orifice_diameter, area))
    critical = max(trap_rows, key=lambda row: row["Vreq_m3"])
    dcrit = float(critical["duration_min"])
    rows = []
    for row in trap_rows:
        row["d_crit_min"] = dcrit
        rows.append(row)
    for key, profile in time_area_profiles.items():
        rows.append(summarize(profile, routed[key], "tiempo_area", profile["pattern"],
                              STORM_MIN, q_limit, orifice_diameter, area, dcrit))
    result = pd.DataFrame(rows)
    result["Qp_previo_m3s"] = q_limit
    result["Qp_previo_recalculo_m3s"] = q_previous_check
    result["tc_previo_min"] = tc_previous
    result["rainfall_depth_note"] = "Bloques derivados de IDF Talbot-Wenzel; los tres patrones tiempo-área conservan la misma lámina acumulada."
    result["routing_note"] = "RK4, Δt=1 min; S=A_tanque h; orificio Cd=0.61 y cabeza disponible max(h−Do/2,0)."
    result.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    make_figure(trapezoids, time_area_profiles, routed, result, dcrit, q_limit, FIG_PATH)

    print("=== Problema B · tanque de detención ===")
    print(f"Cuenca A={area:.4f} km²; escenario previo C={c_previous:.3f}, tc={tc_previous:.1f} min; urbanizado C={C_URB:.2f}, tc={TC_URB_MIN:.0f} min.")
    print(f"T={T_Y} años; Qlim={q_limit:.3f} m³/s; verificación Qprev(IDF)={q_previous_check:.3f} m³/s.")
    print(f"Tanque {TANK_AREA_M2:.0f} m² ({TANK_AREA_M2/10000:.2f} ha; {TANK_AREA_M2/(area*1e6):.2%} de la cuenca) × {TANK_MAX_H_M:.1f} m = {TANK_AREA_M2*TANK_MAX_H_M:.0f} m³; orificio dimensionado Do={orifice_diameter*1000:.0f} mm; Cd={CD}; RK4 Δt={ROUTE_DT_S/60:.0f} min.")
    print(f"Duración crítica trapezoidal dcrit={dcrit:.0f} min; Vreq={critical['Vreq_m3']:.1f} m³; hmax={critical['hmax_m']:.3f} m; Omax={critical['Omax_m3s']:.3f} m³/s.")
    for row in rows:
        print(f"{row['scenario_type']:22s} {row['pattern']:39s} d={row['duration_min']:>3.0f} min: Imax={row['Imax_m3s']:.3f}; Omax={row['Omax_m3s']:.3f}; Vreq={row['Vreq_m3']:.1f} m³; hmax={row['hmax_m']:.3f} m.")
    if result.exceeds_Qlim.any() or result.exceeds_tank_height.any():
        print("ADVERTENCIA: al menos un escenario excede Qlim o la altura útil; el prediseño de tanque/orificio no satisface la condición.")
    print(f"Archivos: {OUT_CSV.relative_to(ROOT)} y {FIG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
