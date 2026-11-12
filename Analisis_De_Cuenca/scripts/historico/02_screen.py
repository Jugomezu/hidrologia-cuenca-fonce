"""Screen the 346 CAMELS-COL catchments down to candidates suitable for an
in-depth single-basin study: moderate size, long+complete record, physically
consistent water balance, low human intervention."""
import pandas as pd, numpy as np
from pathlib import Path

m = pd.read_csv("out/camels_col_master.csv")
n0 = len(m)

# ---------------- hard filters -------------------------------------------
f = {}
f["area 100-5000 km2"]      = m["area"].between(100, 5000)
f["record ends >= 2018"]    = pd.to_datetime(m["end"]) >= pd.Timestamp("2018-01-01")
f["obs record >= 25 yr"]    = m["n_years_obs"] >= 25
f["missing <= 8%"]          = m["missing_pct"] <= 8
# water balance must be closable: Q/P outside this range means the satellite P
# and the gauge Q are mutually inconsistent -> unusable for modelling
f["runoff_ratio 0.2-0.95"]  = m["runoff_ratio"].between(0.20, 0.95)
f["urban < 2%"]             = m["urban_perc"] < 2.0
f["water bodies < 1.5%"]    = m["water_bodies_perc"] < 1.5   # reservoir proxy

print(f"start: {n0} catchments")
keep = pd.Series(True, index=m.index)
for name, mask in f.items():
    keep &= mask.fillna(False)
    print(f"  after {name:<24s}: {int(keep.sum()):>3d}   (this filter alone: {int(mask.fillna(False).sum())})")

c = m[keep].copy()

# ---------------- scoring -------------------------------------------------
def norm(s, lo, hi, invert=False):
    v = ((s - lo) / (hi - lo)).clip(0, 1)
    return 1 - v if invert else v

# size: prefer ~200-2000 km2, penalise both tails
ideal_lo, ideal_hi = 200, 2000
la = np.log10(c["area"])
size = np.where(la < np.log10(ideal_lo), norm(la, np.log10(100), np.log10(ideal_lo)),
        np.where(la > np.log10(ideal_hi), norm(la, np.log10(ideal_hi), np.log10(5000), invert=True), 1.0))

c["s_size"]      = size
c["s_complete"]  = norm(c["missing_pct"], 0, 8, invert=True)
c["s_length"]    = norm(c["n_years_obs"], 25, 41)
c["s_recent"]    = (pd.to_datetime(c["end"]) >= pd.Timestamp("2022-01-01")).astype(float)
c["s_natural"]   = norm(c["forest_perc"] + c["nat_non_forest_form_perc"], 20, 90)
c["s_lowurban"]  = norm(c["urban_perc"], 0, 2, invert=True)
# balanced runoff ratio: closest to ~0.55 is most "textbook"
c["s_balance"]   = 1 - (c["runoff_ratio"] - 0.55).abs() / 0.4
c["s_balance"]   = c["s_balance"].clip(0, 1)

W = {"s_complete":0.22,"s_length":0.16,"s_recent":0.10,"s_size":0.18,
     "s_balance":0.16,"s_natural":0.10,"s_lowurban":0.08}
c["score"] = sum(c[k]*w for k, w in W.items())
c = c.sort_values("score", ascending=False)

cols = ["gauge_id","gauge_department","region","area","mean_ele","n_years_obs",
        "missing_pct","end","runoff_ratio","baseflow_index","aridity","q_mean",
        "forest_perc","agricul_livestock_perc","urban_perc","cn_catchment",
        "tc_representative","score","lat_wgs84","lon_wgs84"]
c[cols].to_csv("out/candidates_ranked.csv", index=False)

pd.set_option("display.width", 250, "display.max_columns", 40)
print(f"\n{len(c)} catchments passed all filters. Top 25:\n")
show = c[["gauge_id","gauge_department","region","area","mean_ele","n_years_obs",
          "missing_pct","runoff_ratio","baseflow_index","aridity","forest_perc",
          "urban_perc","score"]].head(25).round(2)
print(show.to_string(index=False))
print("\nregion mix of candidates:\n", c["region"].value_counts().to_string())
