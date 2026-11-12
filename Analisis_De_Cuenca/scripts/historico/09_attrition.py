"""Order-independent attrition: for each criterion, how many catchments does it
fail on its own, and how many would survive if ONLY that criterion were dropped."""
import pandas as pd, numpy as np
pd.set_option("display.width", 200)

m = pd.read_csv("out/camels_col_master.csv")

A = {
 "area 100-5000 km2":   m["area"].between(100,5000),
 "ends >= 2018":        pd.to_datetime(m["end"]) >= pd.Timestamp("2018-01-01"),
 "obs >= 25 yr":        m["n_years_obs"] >= 25,
 "missing <= 8%":       m["missing_pct"] <= 8,
 "runoff ratio .2-.95": m["runoff_ratio"].between(0.20,0.95),
 "urban < 2%":          m["urban_perc"] < 2.0,
 "water bodies < 1.5%": m["water_bodies_perc"] < 1.5,
}
A = {k: v.fillna(False) for k,v in A.items()}

def report(D, pool, label):
    print(f"\n=== {label}  (pool = {int(pool.sum())}) ===")
    allpass = pool.copy()
    for v in D.values(): allpass &= v
    print(f"pass all: {int(allpass.sum())}")
    rows=[]
    for k,v in D.items():
        fails = pool & ~v
        # unique: fails this one, passes every other
        others = pool.copy()
        for k2,v2 in D.items():
            if k2!=k: others &= v2
        uniq = others & ~v
        # survivors if this criterion were removed
        without = pool.copy()
        for k2,v2 in D.items():
            if k2!=k: without &= v2
        rows.append([k, int(fails.sum()), int(uniq.sum()), int(without.sum())])
    df=pd.DataFrame(rows, columns=["criterion","fails_it","ONLY_it_fails","survivors_without_it"])
    df["cost"] = df["survivors_without_it"] - int(allpass.sum())
    print(df.to_string(index=False))
    return allpass

pool = pd.Series(True, index=m.index)
passA = report(A, pool, "STAGE 2-3 : metadata screen, from 346")

q = pd.read_csv("out/candidates_qc.csv")
B = {
 "max gap <= 150 d":  q["max_gap_days"] <= 150,
 "flatline < 5%":     q["flatline_pct"] < 5,
 "r(P,Q) mon >= .60": q["r_pq_monthly"] >= 0.60,
 "seasonal r >= .70": q["r_seasonal"] >= 0.70,
 "annual RR cv <=.30":q["rr_cv"] <= 0.30,
 "|step| <= 20%":     q["step_pct"].abs() <= 20,
 ">= 30 full years":  q["n_full_years"] >= 30,
}
B = {k: v.fillna(False) for k,v in B.items()}
report(B, pd.Series(True, index=q.index), "STAGE 4 : daily-series QC, from 95")

# how many fail 1, 2, 3+ gates
nf = sum((~v).astype(int) for v in B.values())
print("\nStage-4 gates failed per catchment:")
print(nf.value_counts().sort_index().rename_axis("n_gates_failed").to_string())

print("\nThreshold context (all 346):")
for c,lab in [("missing_pct","missing %"),("n_years_obs","obs years"),
              ("runoff_ratio","runoff ratio"),("area","area km2")]:
    s=m[c].describe(percentiles=[.1,.25,.5,.75,.9])
    print(f"  {lab:<14s} p10={s['10%']:.2f} p25={s['25%']:.2f} med={s['50%']:.2f} p75={s['75%']:.2f} p90={s['90%']:.2f}")
