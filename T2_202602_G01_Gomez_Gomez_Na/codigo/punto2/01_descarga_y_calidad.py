#!/usr/bin/env python3
"""Limpieza y diagnóstico de precipitación GHCNh, con lectura acotada en RAM."""
from collections import defaultdict
from pathlib import Path
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datos" / "punto2"
PRODUCT_DIR = ROOT / "productos" / "punto2"
SOURCE = DATA_DIR / "GHCNh_USW00023062_por.psv"
CLEAN = DATA_DIR / "precip_horaria_limpia.csv"
SUMMARY = PRODUCT_DIR / "resumen_completitud_anual.csv"
EXTREMES = PRODUCT_DIR / "eventos_extremos_verificados.csv"
SENSITIVITY = PRODUCT_DIR / "sensibilidad_completitud.csv"
USECOLS = [
    "STATION", "Station_name", "DATE", "Year", "Month", "Day", "Hour",
    "Minute", "LATITUDE", "LONGITUDE", "ELEVATION", "precipitation",
    "precipitation_Measurement_Code", "precipitation_Quality_Code",
    "precipitation_Report_Type",
]
CHUNK_SIZE = 200_000
VALID_STATES = {"zero", "value", "trace"}


def _dates(frame):
    dates = pd.to_datetime(frame["DATE"], errors="coerce", utc=True)
    bad = dates.isna()
    if bad.any():
        parts = pd.to_datetime({
            "year": pd.to_numeric(frame.loc[bad, "Year"], errors="coerce"),
            "month": pd.to_numeric(frame.loc[bad, "Month"], errors="coerce"),
            "day": pd.to_numeric(frame.loc[bad, "Day"], errors="coerce"),
            "hour": pd.to_numeric(frame.loc[bad, "Hour"], errors="coerce"),
            "minute": pd.to_numeric(frame.loc[bad, "Minute"], errors="coerce").fillna(0),
        }, errors="coerce", utc=True)
        dates.loc[bad] = parts
    return dates


def _prepare(frame, code_sets=None):
    """Reduce an input chunk to timestamped precipitation observations."""
    if code_sets is not None:
        for col, key in (("precipitation_Measurement_Code", "measurement"),
                         ("precipitation_Quality_Code", "quality")):
            code_sets[key].update(frame[col].dropna().astype(str).str.strip().unique())
    dates = _dates(frame)
    frame = frame.loc[dates.notna()].copy()
    frame["timestamp"] = dates.loc[dates.notna()].dt.floor("min")
    raw = frame["precipitation"].astype("string").str.strip()
    mcode = frame["precipitation_Measurement_Code"].astype("string").str.strip().str.upper()
    qcode = frame["precipitation_Quality_Code"].astype("string").str.strip().str.upper()
    trace = raw.str.upper().eq("T") | mcode.isin(["T", "TRACE", "TRAZA"])
    amount = pd.to_numeric(raw.mask(raw.str.upper().eq("T")), errors="coerce")
    qc_ok = qcode.isna() | qcode.isin(["", "0"])
    numeric_ok = amount.notna() & amount.ge(0) & qc_ok
    trace_ok = trace & qc_ok
    state = pd.Series("missing", index=frame.index, dtype="string")
    state.loc[numeric_ok & amount.eq(0)] = "zero"
    state.loc[numeric_ok & amount.gt(0)] = "value"
    state.loc[trace_ok] = "trace"
    values = amount.where(numeric_ok)
    values.loc[trace_ok] = 0.0
    out = pd.DataFrame({
        "timestamp": frame["timestamp"], "precip_mm": values,
        "precip_state": state,
        "quality_flag": frame["precipitation_Quality_Code"].fillna("").astype(str).str.strip(),
        "measurement_flag": frame["precipitation_Measurement_Code"].fillna("").astype(str).str.strip(),
    })
    out["hour"] = out.timestamp.dt.floor("h")
    out.sort_values("timestamp", kind="stable", inplace=True)
    return out


def _write_hour(writer, row, previous_hour, annual_counts):
    hour = row["hour"]
    if previous_hour is not None:
        next_hour = previous_hour + pd.Timedelta(hours=1)
        while next_hour < hour:
            writer.writerow([next_hour.strftime("%Y-%m-%dT%H:%M:%SZ"), "NaN", "missing", "", ""])
            annual_counts[next_hour.year] += 0
            next_hour += pd.Timedelta(hours=1)
    state = str(row["precip_state"])
    amount = row["precip_mm"]
    writer.writerow([hour.strftime("%Y-%m-%dT%H:%M:%SZ"), "NaN" if pd.isna(amount) else amount,
                     state, row["quality_flag"], row["measurement_flag"]])
    if state in VALID_STATES:
        annual_counts[hour.year] += 1
    return hour


def build_clean_from_psv():
    """Stream the large source file in chunks and write the regular series."""
    if not SOURCE.is_file():
        raise FileNotFoundError(f"No existe la serie limpia ni el PSV local: {SOURCE}")
    import csv
    import tempfile

    print(f"No existe la serie limpia; lectura del PSV en bloques de {CHUNK_SIZE:,} filas.")
    code_sets = {"measurement": set(), "quality": set()}
    annual_counts = defaultdict(int)
    previous_hour = None
    pending = None
    first_hour = last_hour = None
    exact_duplicate_rows = multi_stamp_hours = 0
    # Escribir a temporal evita dejar una serie parcial si el procesamiento falla.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=DATA_DIR,
                                     prefix="precip_limpia_", suffix=".tmp", delete=False) as temp:
        temp_path = Path(temp.name)
        writer = csv.writer(temp)
        writer.writerow(["timestamp", "precip_mm", "precip_state", "quality_flag", "measurement_flag"])
        for chunk_no, chunk in enumerate(pd.read_csv(SOURCE, sep="|", usecols=USECOLS,
                                                       chunksize=CHUNK_SIZE, low_memory=False), start=1):
            reduced = _prepare(chunk, code_sets)
            if reduced.empty:
                continue
            exact_duplicate_rows += int(reduced.duplicated("timestamp", keep=False).sum())
            hour_counts = reduced.groupby("hour").timestamp.nunique()
            multi_stamp_hours += int((hour_counts > 1).sum())
            grouped = reduced.groupby("hour", sort=True).tail(1)
            for record in grouped.to_dict("records"):
                if pending is None:
                    pending = record
                    continue
                if record["hour"] < pending["hour"]:
                    raise ValueError("Los bloques del PSV no están en orden cronológico; no es seguro consolidarlos en streaming.")
                if record["hour"] == pending["hour"]:
                    if record["timestamp"] >= pending["timestamp"]:
                        pending = record
                    continue
                previous_hour = _write_hour(writer, pending, previous_hour, annual_counts)
                first_hour = first_hour or pending["hour"]
                last_hour = pending["hour"]
                pending = record
            if chunk_no % 5 == 0:
                print(f"  Bloque {chunk_no:,} procesado")
        if pending is not None:
            previous_hour = _write_hour(writer, pending, previous_hour, annual_counts)
            first_hour = first_hour or pending["hour"]
            last_hour = pending["hour"]
    temp_path.replace(CLEAN)
    if first_hour is None:
        raise ValueError("No se encontraron fechas válidas en el PSV.")

    years = range(first_hour.year, last_hour.year + 1)
    rows = []
    for year in years:
        expected = 8784 if pd.Timestamp(year, 12, 31).is_leap_year else 8760
        wet_expected = 4392
        wet_valid = 0
        # El conteo de temporada se reconstruye con lectura por bloques de la salida,
        # que es ligera y ya está regularizada.
        rows.append({"year": year, "valid_hours": annual_counts[year], "expected_hours": expected,
                     "annual_completeness": annual_counts[year] / expected,
                     "valid_wet_season_hours": wet_valid, "expected_wet_season_hours": wet_expected,
                     "wet_season_completeness": 0.0, "retained": "no", "reason": "pendiente de temporada"})
    # Recalcular conteos anuales y abril-septiembre de la serie en bloques.
    wet_counts = defaultdict(int)
    for chunk in pd.read_csv(CLEAN, chunksize=CHUNK_SIZE, parse_dates=["timestamp"]):
        valid = chunk.precip_state.isin(VALID_STATES)
        wet = chunk.timestamp.dt.month.isin([4, 5, 6, 7, 8, 9])
        for year, count in chunk.loc[valid & wet].groupby(chunk.timestamp.dt.year).size().items():
            wet_counts[int(year)] += int(count)
    for row in rows:
        year = row["year"]
        wet_expected = 4392
        wet_valid = wet_counts[year]
        wet_pct = wet_valid / wet_expected
        annual_pct = row["annual_completeness"]
        keep = annual_pct >= .80 and wet_pct >= .90
        reasons = []
        if annual_pct < .80:
            reasons.append("completitud anual < 80%")
        if wet_pct < .90:
            reasons.append("completitud abril-septiembre < 90%")
        row.update(valid_wet_season_hours=wet_valid, wet_season_completeness=wet_pct,
                   retained="sí" if keep else "no",
                   reason="cumple ambos umbrales" if keep else "; ".join(reasons))
    pd.DataFrame(rows).to_csv(SUMMARY, index=False, float_format="%.6f", encoding="utf-8")
    print(f"Códigos de medición observados: {sorted(code_sets['measurement'])}")
    print(f"Códigos de calidad observados: {sorted(code_sets['quality'])}")
    print(f"Duplicados exactos involucrados detectados dentro de bloques: {exact_duplicate_rows:,}")
    print(f"Horas con marcas subhorarias detectadas dentro de bloques: {multi_stamp_hours:,}")


def summarize_clean_series():
    """Analyze an existing clean CSV with bounded memory (two streaming passes)."""
    import csv

    if not SUMMARY.exists():
        raise FileNotFoundError(f"Falta el resumen anual esperado: {SUMMARY}")
    summary = pd.read_csv(SUMMARY)
    annual_lookup = summary.set_index("year")
    peaks = []
    maxima = {}
    states = set()
    qualities = set()
    measurements = set()
    first_ts = last_ts = None
    counts_by_year = defaultdict(int)
    for chunk in pd.read_csv(CLEAN, chunksize=CHUNK_SIZE, parse_dates=["timestamp"]):
        chunk.sort_values("timestamp", inplace=True)
        first_ts = first_ts or chunk.timestamp.min()
        last_ts = chunk.timestamp.max()
        states.update(chunk.precip_state.dropna().astype(str).unique())
        qualities.update(chunk.quality_flag.dropna().astype(str).unique())
        measurements.update(chunk.measurement_flag.dropna().astype(str).unique())
        valid = chunk.precip_state.isin(VALID_STATES) & pd.to_numeric(chunk.precip_mm, errors="coerce").notna()
        amounts = pd.to_numeric(chunk.loc[valid, "precip_mm"], errors="coerce")
        years = chunk.loc[valid, "timestamp"].dt.year
        for year, val in zip(years, amounts):
            counts_by_year[int(year)] += 1
            maxima[int(year)] = max(maxima.get(int(year), -math.inf), float(val))
        candidate = chunk.loc[valid & chunk.precip_state.isin(["zero", "value"])].copy()
        candidate["precip_mm"] = pd.to_numeric(candidate.precip_mm, errors="coerce")
        peaks.extend(candidate.nlargest(10, "precip_mm")[["timestamp", "precip_mm", "quality_flag", "measurement_flag"]].to_dict("records"))
        peaks = sorted(peaks, key=lambda x: x["precip_mm"], reverse=True)[:10]

    print(f"Serie existente reutilizada: {CLEAN}; no se abrió el PSV de 901 MB.")
    print(f"Rango: {first_ts} a {last_ts}; estados: {sorted(states)}")
    print(f"Códigos de calidad en la serie: {sorted(qualities)}")
    print(f"Códigos de medición en la serie: {sorted(measurements)}")
    print("Resolución de salida: horaria regular; años y horas válidas según resumen anual.")

    # Segunda pasada, ahora buscando únicamente las ventanas de ±24 h de los
    # diez máximos retenidos. No se mantiene la serie completa en memoria.
    window = {r["timestamp"]: {"prev": 0.0, "prev_n": 0, "next": 0.0, "next_n": 0}
              for r in peaks}
    for chunk in pd.read_csv(CLEAN, chunksize=CHUNK_SIZE, parse_dates=["timestamp"]):
        valid = chunk.precip_state.isin(VALID_STATES) & pd.to_numeric(chunk.precip_mm, errors="coerce").notna()
        chunk = chunk.loc[valid, ["timestamp", "precip_mm"]].copy()
        chunk["precip_mm"] = pd.to_numeric(chunk.precip_mm, errors="coerce")
        for event_ts, accum in window.items():
            before = chunk[(chunk.timestamp >= event_ts - pd.Timedelta(hours=24)) & (chunk.timestamp < event_ts)]
            after = chunk[(chunk.timestamp > event_ts) & (chunk.timestamp <= event_ts + pd.Timedelta(hours=24))]
            accum["prev"] += float(before.precip_mm.sum())
            accum["prev_n"] += len(before)
            accum["next"] += float(after.precip_mm.sum())
            accum["next_n"] += len(after)
    extreme_rows = []
    for event in peaks:
        w = window[event["timestamp"]]
        extreme_rows.append({
            "timestamp": event["timestamp"], "precip_mm": event["precip_mm"],
            "rain_prev_24h_mm": w["prev"], "valid_prev_24h_hours": w["prev_n"],
            "rain_next_24h_mm": w["next"], "valid_next_24h_hours": w["next_n"],
            "quality_code": event["quality_flag"], "measurement_code": event["measurement_flag"],
        })
    pd.DataFrame(extreme_rows).to_csv(EXTREMES, index=False, na_rep="NaN", encoding="utf-8")
    print("Diez máximos horarios y lluvia en ventanas previas/posteriores de 24 h:")
    if extreme_rows:
        print(pd.DataFrame(extreme_rows).to_string(index=False))

    selections = {
        "filtrados_80_90": [int(y) for y in maxima if y in annual_lookup.index and str(annual_lookup.loc[y, "retained"]).strip().lower() in ("sí", "si")],
        "todos_completitud_50": [int(y) for y in maxima if y in annual_lookup.index and float(annual_lookup.loc[y, "annual_completeness"]) >= .50],
    }
    sensitivity_rows = []
    for criterion, years in selections.items():
        values = [maxima[y] for y in years]
        mean = sum(values) / len(values) if values else math.nan
        if len(values) > 1:
            sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
            beta = sd * math.sqrt(6) / math.pi
            location = mean - 0.5772156649015329 * beta
            q10 = location - beta * math.log(-math.log(1 - 1 / 10))
            q50 = location - beta * math.log(-math.log(1 - 1 / 50))
        else:
            q10 = q50 = math.nan
        sensitivity_rows.append({
            "criterio": criterion, "numero_anios": len(values),
            "media_maximos_anuales_mm": mean, "cuantil_1h_T10_mm": q10,
            "cuantil_1h_T50_mm": q50,
            "metodo": "Gumbel por momentos sobre máximos anuales horarios (preliminar)",
        })
    pd.DataFrame(sensitivity_rows).to_csv(SENSITIVITY, index=False, na_rep="NaN", float_format="%.4f", encoding="utf-8")
    print("Sensibilidad de máximos anuales horarios (Gumbel por momentos, preliminar):")
    print(pd.DataFrame(sensitivity_rows).to_string(index=False))
    print("Resolución: 1 h no captura máximos de 10, 15 o 30 min relevantes para microcuencas. "
          "Weiss (1964) ajusta máximos de reloj fijo respecto de máximos móviles para la duración observada; "
          "no reconstruye datos subhorarios. Para duraciones <1 h se necesita una ley de escala regional "
          "validada y documentar su incertidumbre.")
    print(f"Tabla de eventos: {EXTREMES}\nTabla de sensibilidad: {SENSITIVITY}")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    if CLEAN.exists():
        if not SUMMARY.exists():
            raise FileNotFoundError(f"Existe {CLEAN}, pero falta {SUMMARY}; regenere el resumen antes del análisis.")
        summarize_clean_series()
    else:
        build_clean_from_psv()
        summarize_clean_series()
    print("Años aceptados:", pd.read_csv(SUMMARY).loc[lambda x: x.retained.astype(str).str.lower().isin(["sí", "si"]), "year"].tolist())


if __name__ == "__main__":
    main()
