"""Shapefile con las estaciones IDEAM dentro de la cuenca del Fonce (San Gil, 24027010)
y shapefile con los polígonos de las 6 (sub)cuencas, para verlas juntas en un SIG.

Reutiliza el mismo criterio espacial de scripts/historico/20_inventario_fonce.py (estación dentro
del polígono de San Gil), pero esta vez conserva lat/lon y también marca en qué
subcuenca del Fonce cae cada estación (una estación puede caer en varias, por el
anidamiento).

Salidas:
  out/shp_fonce/estaciones_fonce.shp   (puntos, EPSG:4326)
  out/shp_fonce/cuencas_fonce.shp      (polígonos, EPSG:4326)
"""
import geopandas as gpd, pandas as pd
from pyproj import Geod
from pathlib import Path

ESTACIONES_FONCE = {
    24027010: "San Gil (Fonce, salida)",
    24027070: "Merida (Fonce)",
    24027030: "Nemizaque (Pienta)",
    24027050: "Puente Llano (Taquiza)",
    24027040: "Puente Cabra (Mogoticos)",
    24027060: "Puente Arco (Monchia)",
}
SHP = ("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/"
       "CAMELS_COL_catchments_boundaries.shp")
OUT = Path("out/shp_fonce"); OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- cuencas
lista = ",".join(f"'{i}'" for i in ESTACIONES_FONCE)
cuencas = gpd.read_file(SHP, where=f"IDEAM_CODE IN ({lista})")
cuencas["gauge_id"] = cuencas["IDEAM_CODE"].astype("int64")
cuencas = cuencas.to_crs(4326)
cuencas["nombre"] = cuencas["gauge_id"].map(ESTACIONES_FONCE)
# El área se mide sobre el propio polígono, en el elipsoide (geodésica, sin depender de ninguna
# proyección), en vez de copiar la que publica CAMELS-COL en su tabla de atributos: esa cifra (2 124 km²
# para San Gil) es 1,2 % mayor que el polígono que la misma CAMELS-COL distribuye, y el proyecto prefiere
# medir lo que usa. Esta columna es la única fuente del área en todo el proyecto.
GEOD = Geod(ellps="WGS84")
cuencas["area_km2"] = [abs(GEOD.geometry_area_perimeter(g)[0]) / 1e6 for g in cuencas.geometry]
cuencas["area_km2"] = cuencas["area_km2"].round(2)
cuencas = cuencas[["gauge_id", "nombre", "area_km2", "geometry"]]
cuencas.to_file(OUT / "cuencas_fonce.shp")
# el área también en un CSV, con todos sus decimales (el .dbf del shapefile los recorta)
cuencas[["gauge_id", "nombre", "area_km2"]].to_csv(OUT / "areas_cuencas.csv", index=False)

# ---------------------------------------------------------------- estaciones IDEAM
cne = pd.read_csv("data/ideam/cne_ideam.csv", dtype=str)
cne["lat"] = pd.to_numeric(cne["latitud"], errors="coerce")
cne["lon"] = pd.to_numeric(cne["longitud"], errors="coerce")
cne = cne.dropna(subset=["lat", "lon"])
cne["nombre"] = cne["nombre"].str.replace(r"\s*\[\d+\]$", "", regex=True).str.strip()
pts = gpd.GeoDataFrame(cne, geometry=gpd.points_from_xy(cne["lon"], cne["lat"]), crs=4326)

madre = cuencas.loc[cuencas.gauge_id == 24027010, "geometry"].iloc[0]
dentro = pts[pts.within(madre)].copy()

# marcar en que subcuenca(s) cae cada estacion (nombres separados por ;)
def subcuencas_de(pt):
    hits = cuencas.loc[cuencas.geometry.contains(pt), "nombre"]
    return ";".join(hits)
dentro["subcuencas"] = dentro.geometry.apply(subcuencas_de)

cols = ["codigo", "nombre", "categoria", "tecnologia", "estado", "municipio",
        "corriente", "altitud", "fecha_instalacion", "fecha_suspension",
        "lat", "lon", "subcuencas", "geometry"]
dentro = dentro[cols].rename(columns={
    "codigo": "codigo", "categoria": "categoria", "tecnologia": "tecnolog",
    "fecha_instalacion": "f_instal", "fecha_suspension": "f_suspen",
})
# shapefile: nombres de columna a max 10 caracteres
dentro = dentro.rename(columns={"tecnolog": "tecnolog", "subcuencas": "subcuenca"})
dentro.to_file(OUT / "estaciones_fonce.shp")

print(f"cuencas_fonce.shp: {len(cuencas)} poligonos -> {OUT/'cuencas_fonce.shp'}")
print(f"estaciones_fonce.shp: {len(dentro)} estaciones -> {OUT/'estaciones_fonce.shp'}")
print("\npor categoria:")
print(dentro["categoria"].value_counts().to_string())
print("\npluviometricas activas:", int(((dentro.categoria.str.contains("Pluvio")) & (dentro.estado == "Activa")).sum()))
