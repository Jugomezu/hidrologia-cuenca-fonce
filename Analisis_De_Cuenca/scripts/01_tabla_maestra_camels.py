"""Merge all CAMELS-COL attribute tables into one master table, add derived
record-quality fields and WGS84 coordinates."""
import pandas as pd, numpy as np
from pyproj import Transformer
from pathlib import Path

D = Path("data/camels_col")
OUT = Path("out"); OUT.mkdir(exist_ok=True)

def rd(name, sep=";"):
    df = pd.read_csv(D / name, sep=sep, decimal=".", encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    return df

info  = rd("02_CAMELS_COL_Catchment_information.csv")
geo   = rd("05_CAMELS_COL_Geologic_characteristics.csv")
land  = rd("06_CAMELS_COL_Land_cover_characteristics.csv")
soil  = rd("07_CAMELS_COL_Soil_characteristics.csv")
clim  = rd("08_CAMELS_COL_Climatic_indices.csv")
sign  = rd("09_CAMELS_COL_Hydrological_signatures.csv", sep=",")
phys  = rd("10_CAMELS_COL_Physiograpic_characteristics.csv")
luc   = rd("11_CAMELS_COL_Land_use_capability.csv")

m = info
for df, tag in [(phys,"phys"),(clim,"clim"),(sign,"sign"),(land,"land"),
                (geo,"geo"),(soil,"soil"),(luc,"luc")]:
    dup = [c for c in df.columns if c != "gauge_id" and c in m.columns]
    df = df.rename(columns={c: f"{c}_{tag}" for c in dup})
    m = m.merge(df, on="gauge_id", how="left")

# ---- record quality -------------------------------------------------------
m["start"] = pd.to_datetime(m["gauge_star"], format="mixed", dayfirst=True)
m["end"]   = pd.to_datetime(m["gauge_end"],  format="mixed", dayfirst=True)
m["span_yr"]     = (m["end"] - m["start"]).dt.days / 365.25
m["n_years_obs"] = m["gauge_n"] / 365.25          # actual observed days
m["missing_pct"] = m["gauge_missing"]
m["ends_2022"]   = m["end"] >= pd.Timestamp("2022-01-01")

# ---- WGS84 coords (source is EPSG:3395; lat col = northing, lon col = easting)
tr = Transformer.from_crs("EPSG:3395", "EPSG:4326", always_xy=True)
lon, lat = tr.transform(m["gauge_lon"].values, m["gauge_lat"].values)
m["lon_wgs84"], m["lat_wgs84"] = lon, lat

# ---- hydrological region from IDEAM gauge_id prefix ------------------------
# IDEAM "area hidrografica" = first digit of the 8-digit station code.
# Verified against gauge_department: 1=Caribe, 2=Magdalena-Cauca, 3=Orinoco,
# 4=Amazonas, 5=Pacifico (reproduces the region counts reported in the paper).
AREA_HIDRO = {"1": "Caribe", "2": "Magdalena-Cauca", "3": "Orinoco",
              "4": "Amazonas", "5": "Pacifico"}
m["region"] = m["gauge_id"].astype(str).str.zfill(8).str[0].map(AREA_HIDRO)
m["zona_hidro"] = m["gauge_id"].astype(str).str.zfill(8).str[:2]

m.to_csv(OUT / "camels_col_master.csv", index=False)
print("master table:", m.shape)
print("\nregions:\n", m["region"].value_counts())
print("\narea km2 describe:\n", m["area"].describe())
print("\nrecord length (obs years) describe:\n", m["n_years_obs"].describe())
print("\nmissing_pct describe:\n", m["missing_pct"].describe())
print("\nends in 2022:", int(m["ends_2022"].sum()), "of", len(m))
