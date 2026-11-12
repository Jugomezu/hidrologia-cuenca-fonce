"""Data-quality / 'noisiness' diagnostics computed on the raw daily series
for every screened candidate. Metadata says how much data exists; this says
whether the data is any good."""
import pandas as pd, numpy as np
from pathlib import Path

TS = Path("data/camels_col/hydromet/3_Hydrometeorological_data")
cand = pd.read_csv("out/candidates_named.csv")

def load(gid):
    df = pd.read_csv(TS / f"Hydromet_data_{gid}.txt", sep="\t", encoding="latin-1")
    df.columns = ["date","pr","etp","tmin","tmax","q"]
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    df = df.set_index("date").sort_index()
    # missing days are ABSENT rows in these files, not NaN -> restore the
    # full daily calendar so gaps are visible to the diagnostics
    full = pd.date_range(df.index.min(), df.index.max(), freq="D")
    return df.reindex(full)

def max_run(mask):
    """length of the longest True run"""
    if not mask.any(): return 0
    v = mask.values.astype(int)
    best = cur = 0
    for x in v:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best

def flatline_days(q, minlen=7):
    """days sitting inside a run of >=minlen identical, non-zero values --
    the classic fingerprint of infilled / eyeballed stage readings."""
    s = q.dropna()
    if len(s) < minlen: return np.nan
    grp = (s != s.shift()).cumsum()
    sz = s.groupby(grp).transform("size")
    flat = (sz >= minlen) & (s > 0)
    return 100 * flat.sum() / len(s)

rows = []
for _, r in cand.iterrows():
    gid = int(r["gauge_id"])
    d = load(gid)
    q = d["q"]
    obs = q.dropna()
    if len(obs) == 0: continue
    lo, hi = obs.index.min(), obs.index.max()
    w = d.loc[lo:hi]                      # within-record window only

    # --- annual water balance stability (complete years only) -------------
    yr = w.resample("YE").agg(q=("q","mean"), qn=("q","count"),
                              p=("pr","sum"), e=("etp","sum"))
    yr = yr[yr["qn"] >= 350]
    # convert mean m3/s -> mm/yr using catchment area
    area_km2 = r["area"]
    yr["q_mm"] = yr["q"] * 86400 * 365.25 / (area_km2 * 1e6) * 1000
    yr["rr"] = yr["q_mm"] / yr["p"]
    rr_cv = yr["rr"].std() / yr["rr"].mean() if len(yr) > 5 else np.nan

    # --- monthly P->Q coherence (how modellable is this basin?) -----------
    mo = w.resample("ME").agg(q=("q","mean"), qn=("q","count"), p=("pr","sum"))
    mo = mo[mo["qn"] >= 25].dropna()
    r_pq = mo["q"].corr(mo["p"], method="spearman") if len(mo) > 24 else np.nan
    # seasonal-cycle coherence: mean monthly climatology correlation
    clim = mo.assign(m=mo.index.month).groupby("m")[["q","p"]].mean()
    r_seas = clim["q"].corr(clim["p"]) if len(clim) == 12 else np.nan

    # --- step change between record halves --------------------------------
    mid = lo + (hi - lo) / 2
    q1, q2 = obs.loc[:mid], obs.loc[mid:]
    step = (q2.mean() - q1.mean()) / q1.mean() * 100 if len(q1) > 365 and len(q2) > 365 else np.nan

    rows.append(dict(
        gauge_id=gid,
        q_missing_pct = 100 * w["q"].isna().sum() / len(w),
        max_gap_days  = max_run(w["q"].isna()),
        flatline_pct  = flatline_days(w["q"]),
        zero_pct      = 100 * (obs == 0).sum() / len(obs),
        n_full_years  = len(yr),
        rr_cv         = rr_cv,
        rr_med        = yr["rr"].median(),
        r_pq_monthly  = r_pq,
        r_seasonal    = r_seas,
        step_pct      = step,
        q_p99_over_med= obs.quantile(0.99) / obs.median() if obs.median() > 0 else np.nan,
    ))

qc = pd.DataFrame(rows)
out = cand.merge(qc, on="gauge_id", how="left")
out.to_csv("out/candidates_qc.csv", index=False)

pd.set_option("display.width", 260)
print("QC computed for", len(qc), "candidates\n")
print(qc[["q_missing_pct","max_gap_days","flatline_pct","zero_pct","n_full_years",
          "rr_cv","r_pq_monthly","r_seasonal","step_pct"]].describe().round(2).to_string())
