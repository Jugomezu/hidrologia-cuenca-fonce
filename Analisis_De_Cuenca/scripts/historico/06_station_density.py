"""How much *ground* met data exists inside each candidate basin?
CHIRPS/MSWX are satellite products; a basin with real IDEAM rain gauges inside
it can be validated and analysed at much higher confidence."""
import geopandas as gpd, pandas as pd, numpy as np

bas = gpd.read_file("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/"
                    "CAMELS_COL_catchments_boundaries.shp").to_crs(4326)
bas["gauge_id"] = bas["IDEAM_CODE"].astype("int64")

cne = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str)
cne["lat"] = pd.to_numeric(cne["latitud"], errors="coerce")
cne["lon"] = pd.to_numeric(cne["longitud"], errors="coerce")
cne = cne.dropna(subset=["lat","lon"])
pts = gpd.GeoDataFrame(cne, geometry=gpd.points_from_xy(cne["lon"], cne["lat"]), crs=4326)

fin = pd.read_csv("out/finalists.csv")
sub = bas[bas["gauge_id"].isin(fin["gauge_id"])].copy()

# buffer ~10 km to also catch gauges just outside the divide (usable for interpolation)
buf = sub.copy()
buf["geometry"] = buf.to_crs(3395).buffer(10000).to_crs(4326)

def tally(poly_gdf, label):
    j = gpd.sjoin(pts, poly_gdf[["gauge_id","geometry"]], predicate="within")
    def cat(g):
        c = g["categoria"].fillna("")
        return pd.Series({
            f"{label}_total": len(g),
            f"{label}_precip": c.str.contains("Pluvio", case=False).sum(),
            f"{label}_climate": c.str.contains("Clim|Agromet|Sinóptica|Meteor", case=False, regex=True).sum(),
            f"{label}_flow": c.str.contains("Limni", case=False).sum(),
            f"{label}_active": (g["estado"].fillna("").str.strip() == "Activa").sum(),
        })
    return j.groupby("gauge_id").apply(cat, include_groups=False)

t_in  = tally(sub, "in")
t_buf = tally(buf, "buf")

res = fin.merge(t_in, on="gauge_id", how="left").merge(t_buf, on="gauge_id", how="left")
for c in res.columns:
    if c.startswith(("in_","buf_")): res[c] = res[c].fillna(0).astype(int)
res["precip_per_1000km2"] = (res["in_precip"] / res["area"] * 1000).round(1)
res.to_csv("out/finalists_with_stations.csv", index=False)

pd.set_option("display.width", 300)
cols = ["gauge_id","nombre","corriente","gauge_department","area",
        "in_total","in_precip","in_climate","in_active",
        "buf_precip","buf_climate","precip_per_1000km2","final"]
print("=== IDEAM ground stations inside basin / within 10 km buffer ===\n")
print(res[cols].round(2).to_string(index=False))
