"""Export the shortlist + supporting series used in the comparison report.
Includes two REJECTED basins so the report can show *why* they were cut."""
import pandas as pd, numpy as np, json
from pathlib import Path

TS = Path("data/camels_col/hydromet/3_Hydrometeorological_data")
qc = pd.read_csv("out/candidates_qc.csv").set_index("gauge_id")
fin = pd.read_csv("out/finalists_with_stations.csv").set_index("gauge_id")
m   = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id")

SEL = [(21017050,"shortlist"),(26057040,"shortlist"),(24027040,"shortlist"),
       (23067060,"shortlist"),(23107020,"shortlist"),
       (26027100,"rejected"),(22027020,"rejected")]

def load(g):
    d = pd.read_csv(TS / f"Hydromet_data_{g}.txt", sep="\t", encoding="latin-1")
    d.columns = ["date","pr","etp","tmin","tmax","q"]
    d["date"] = pd.to_datetime(d["date"], format="%d/%m/%Y")
    d = d.set_index("date").sort_index()
    return d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"))

payload = {}
for gid, verdict in SEL:
    a = m.loc[gid]; r = qc.loc[gid]
    st = fin.loc[gid] if gid in fin.index else None
    d = load(gid); w = d[d.q.notna()]; area = a["area"]
    tomm = lambda s: s*86400/(area*1e6)*1000          # m3/s -> mm/day

    c = d.assign(mo=d.index.month).groupby("mo").agg(P=("pr","mean"), E=("etp","mean"), Q=("q","mean"))
    c["Pm"] = c.P*30.4; c["Qmm"] = tomm(c.Q)*30.4; c["Em"] = c.E*30.4
    Pidx = (c.Pm/c.Pm.mean()).round(3); Qidx = (c.Qmm/c.Qmm.mean()).round(3)

    yr = d.resample("YE").agg(q=("q","mean"), n=("q","count"), p=("pr","sum"))
    yr = yr[yr.n >= 350]
    yr["qmm"] = tomm(yr["q"])*365.25; yr["rr"] = yr.qmm/yr.p

    qs = tomm(w["q"]).sort_values(ascending=False).values
    exc = [0.1,1,5,10,20,30,40,50,60,70,80,90,95,99]
    idx = np.clip(np.searchsorted(np.arange(1,len(qs)+1)/(len(qs)+1)*100, exc), 0, len(qs)-1)

    payload[str(gid)] = dict(
        verdict=verdict, name=a.get("gauge_department"),
        station=(st["nombre"] if st is not None else qc.loc[gid,"nombre"]),
        river=(st["corriente"] if st is not None else qc.loc[gid,"corriente"]),
        dept=a["gauge_department"],
        muni=(st["municipio"] if st is not None else ""),
        subzona=(st["subzona_hidrografica"] if st is not None else ""),
        categoria=(st["categoria"] if st is not None else ""),
        estado=(st["estado"] if st is not None else ""),
        area=round(area,1), elev_min=int(a.minimum_ele), elev_mean=int(a.mean_ele),
        elev_max=int(a.maximum_ele), channel_km=round(a["streng_chanel"],1),
        gravelius=round(a["gravelius_index"],2), form=round(a.factor_form,2),
        cn=round(a.cn_catchment,1), lat=round(a.lat_wgs84,4), lon=round(a.lon_wgs84,4),
        start=str(a.start)[:10], end=str(a.end)[:10],
        years=round(a.n_years_obs,1), missing=round(a.missing_pct,2),
        maxgap=int(r.max_gap_days), flat=round(r.flatline_pct,2),
        rpq=round(r.r_pq_monthly,2), rseas=round(r.r_seasonal,2),
        rrcv=round(r.rr_cv,2), step=round(r.step_pct,1), nyr=int(r.n_full_years),
        qmean=round(a.q_mean,2), rr=round(a.runoff_ratio,2), bfi=round(a.baseflow_index,2),
        fdc_slope=round(a.slope_fdc,2), elas=round(a.stream_elas,2), aridity=round(a.aridity,2),
        forest=round(a.forest_perc,1), agri=round(a.agricul_livestock_perc,1),
        urban=round(a.urban_perc,2),
        st_in=int(st.in_total) if st is not None else None,
        st_p=int(st.in_precip) if st is not None else None,
        st_c=int(st.in_climate) if st is not None else None,
        st_active=int(st.in_active) if st is not None else None,
        st_buf_p=int(st.buf_precip) if st is not None else None,
        clim=dict(P=[round(v,1) for v in c.Pm], Q=[round(v,1) for v in c.Qmm],
                  E=[round(v,1) for v in c.Em],
                  Pidx=list(Pidx), Qidx=list(Qidx)),
        annual=dict(year=[int(y.year) for y in yr.index], rr=[round(v,3) for v in yr.rr]),
        fdc=dict(exc=exc, q=[round(float(qs[i]),4) for i in idx]),
    )

Path("out/report_data.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
print("wrote", len(payload), "basins")
for k,v in payload.items():
    ph = np.corrcoef(v['clim']['Pidx'], v['clim']['Qidx'])[0,1]
    print(f"  {k} {v['river']:<12s} {v['verdict']:<9s} {v['area']:>6.0f}km2  phase r={ph:+.2f}  Qidx range {min(v['clim']['Qidx']):.2f}-{max(v['clim']['Qidx']):.2f}")
