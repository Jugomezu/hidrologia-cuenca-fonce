"""Final ranking: combine metadata screening with measured time-series quality."""
import pandas as pd, numpy as np
pd.set_option("display.width", 300, "display.max_columns", 50)

d = pd.read_csv("out/candidates_qc.csv")

# ---- hard QC gates -------------------------------------------------------
g = {}
g["max gap <= 150 d"]     = d["max_gap_days"] <= 150
g["flatline < 5%"]        = d["flatline_pct"] < 5
g["monthly r(P,Q) >= .60" ]= d["r_pq_monthly"] >= 0.60
g["seasonal r >= .70"]    = d["r_seasonal"] >= 0.70
g["annual RR cv <= .30"]  = d["rr_cv"] <= 0.30
g["|step| <= 20%"]        = d["step_pct"].abs() <= 20
g[">= 30 full years"]     = d["n_full_years"] >= 30

keep = pd.Series(True, index=d.index)
print(f"start: {len(d)} screened candidates")
for k, v in g.items():
    keep &= v.fillna(False)
    print(f"  after {k:<24s}: {int(keep.sum()):>3d}   (alone: {int(v.fillna(False).sum())})")
f = d[keep].copy()

def nz(s, lo, hi, invert=False):
    v = ((s - lo) / (hi - lo)).clip(0, 1)
    return 1 - v if invert else v

f["q_gap"]    = nz(f["max_gap_days"], 7, 150, invert=True)
f["q_flat"]   = nz(f["flatline_pct"], 0, 5, invert=True)
f["q_signal"] = nz(f["r_pq_monthly"], 0.60, 0.88)
f["q_seas"]   = nz(f["r_seasonal"], 0.70, 0.95)
f["q_stable"] = nz(f["rr_cv"], 0.09, 0.30, invert=True)
f["q_step"]   = nz(f["step_pct"].abs(), 0, 20, invert=True)
f["q_len"]    = nz(f["n_full_years"], 30, 42)

W = {"q_gap":.16,"q_flat":.12,"q_signal":.18,"q_seas":.12,
     "q_stable":.14,"q_step":.10,"q_len":.08}
f["qc_score"] = sum(f[k]*w for k, w in W.items()) / sum(W.values())
f["final"] = 0.45*f["score"] + 0.55*f["qc_score"]
f = f.sort_values("final", ascending=False)
f.to_csv("out/finalists.csv", index=False)

cols = ["gauge_id","nombre","corriente","gauge_department","area","mean_ele",
        "n_full_years","q_missing_pct","max_gap_days","flatline_pct",
        "r_pq_monthly","r_seasonal","rr_cv","step_pct","runoff_ratio",
        "baseflow_index","aridity","estado","final"]
print(f"\n=== {len(f)} FINALISTS (all gates passed) ===\n")
print(f[cols].head(20).round(2).to_string(index=False))
