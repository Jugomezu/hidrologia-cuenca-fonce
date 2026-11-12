"""Find CAMELS-COL gauges nested inside / containing each finalist basin.
Nested gauges let you validate a model internally -- a big plus for a deep study."""
import geopandas as gpd, pandas as pd

bas = gpd.read_file("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/"
                    "CAMELS_COL_catchments_boundaries.shp")
bas["gauge_id"] = bas["IDEAM_CODE"].astype("int64")
bas["area_m2"] = bas.area

master = pd.read_csv("out/camels_col_master.csv")
names  = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str)
names["gauge_id"] = names["codigo"].str.lstrip("0").astype("int64")
names["nombre"] = names["nombre"].str.replace(r"\s*\[\d+\]$","",regex=True)
nm = names.drop_duplicates("gauge_id").set_index("gauge_id")[["nombre","corriente"]]

fin = pd.read_csv("out/finalists_with_stations.csv")
info = master.set_index("gauge_id")

for _, r in fin.head(6).iterrows():
    gid = int(r["gauge_id"])
    me = bas[bas.gauge_id == gid]
    if me.empty: continue
    geom = me.geometry.iloc[0]
    rel = []
    for _, o in bas[bas.gauge_id != gid].iterrows():
        if not o.geometry.intersects(geom): continue
        inter = o.geometry.intersection(geom).area
        if inter / o["area_m2"] > 0.95:  rel.append(("nested inside", o.gauge_id))
        elif inter / geom.area > 0.95:   rel.append(("contains this", o.gauge_id))
    print(f"\n=== {r['nombre']} / Rio {r['corriente']} ({gid}) — {r['area']:.0f} km2")
    if not rel:
        print("    no nested CAMELS-COL gauges")
    for kind, oid in rel:
        o = info.loc[oid]
        n = nm.loc[oid] if oid in nm.index else {"nombre":"?","corriente":"?"}
        print(f"    {kind:<14s} {oid}  {str(n['nombre'])[:26]:<26s} "
              f"{o['area']:>8.0f} km2  miss={o['gauge_missing']:.1f}%  yrs={o['n_years_obs']:.0f}")
