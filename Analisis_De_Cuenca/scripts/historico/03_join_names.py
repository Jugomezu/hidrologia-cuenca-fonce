"""Attach IDEAM catalogue metadata (station name, river, sub-zone, status)
to the ranked candidates."""
import pandas as pd
from pathlib import Path

cne = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str)
cne["gauge_id"] = cne["codigo"].str.lstrip("0").astype("int64")
keep = ["gauge_id","nombre","categoria","estado","tecnologia","municipio","corriente",
        "area_hidrografica","zona_hidrografica","subzona_hidrografica",
        "fecha_instalacion","fecha_suspension","altitud","latitud","longitud"]
cne = cne[keep].drop_duplicates("gauge_id")

cand = pd.read_csv("out/candidates_ranked.csv")
j = cand.merge(cne, on="gauge_id", how="left")
j["nombre"] = j["nombre"].str.replace(r"\s*\[\d+\]$", "", regex=True).str.strip()
j.to_csv("out/candidates_named.csv", index=False)

print("matched to IDEAM catalogue:", j["nombre"].notna().sum(), "/", len(j))
print("station category:", j["categoria"].value_counts().to_dict())
print("station status  :", j["estado"].value_counts().to_dict())

pd.set_option("display.width", 260, "display.max_colwidth", 34)
cols = ["gauge_id","nombre","corriente","subzona_hidrografica","gauge_department",
        "area","mean_ele","n_years_obs","missing_pct","runoff_ratio","estado","score"]
print("\n=== TOP 20 CANDIDATES ===")
print(j[cols].head(20).round(2).to_string(index=False))
