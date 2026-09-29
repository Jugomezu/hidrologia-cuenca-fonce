"""PASO 1 de 2 — solo geometria (no toca las series diarias).

  (a) Grafo de anidamiento: B esta anidada en A  <=>  el aforo de B cae dentro
      del poligono de A y area(B) < area(A). Correcto hidrologicamente y barato.
  (b) Numero de pixeles IMERG (0.1 grados) cuyo centro cae dentro de la cuenca.

Salida: out/geometria.csv
"""
import geopandas as gpd, pandas as pd, numpy as np, shapely

bas = gpd.read_file("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/"
                    "CAMELS_COL_catchments_boundaries.shp")
bas["gauge_id"] = bas["IDEAM_CODE"].astype("int64")
bas = bas.to_crs(4326).reset_index(drop=True)
area_m2 = bas.to_crs(3395).geometry.area.values

m = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id")
gid = bas["gauge_id"].values
lon = m.loc[gid, "lon_wgs84"].to_numpy()
lat = m.loc[gid, "lat_wgs84"].to_numpy()
geoms = bas.geometry.values

# ---------- (a) anidamiento (sjoin: usa R-tree, no fuerza bruta) ---------
pts = gpd.GeoDataFrame(
    {"child": gid, "a_child": area_m2},
    geometry=gpd.points_from_xy(lon, lat), crs=4326)
polys = gpd.GeoDataFrame(
    {"parent": gid, "a_parent": area_m2}, geometry=bas.geometry, crs=4326)

j = gpd.sjoin(pts, polys, predicate="within")           # aforo dentro del poligono
j = j[(j["child"] != j["parent"]) & (j["a_child"] < j["a_parent"])]

contains = {int(g): set() for g in gid}
for par, ch in zip(j["parent"].to_numpy(), j["child"].to_numpy()):
    contains[int(par)].add(int(ch))

idx = {int(g): k for k, g in enumerate(gid)}
rows = []
for p, kids in contains.items():
    # hija DIRECTA = no esta contenida dentro de ninguna otra hija de la misma madre
    directas = {k for k in kids if not any(k in contains[c] for c in kids if c != k)}
    fr = {k: area_m2[idx[k]] / area_m2[idx[p]] for k in kids}
    # utiles para validacion interna: TODAS las anidadas (hijas y nietas)
    # entre 2% y 85% del area de la madre
    utiles = sorted([(k, fr[k]) for k in kids if 0.02 <= fr[k] <= 0.85],
                    key=lambda t: -t[1])
    rows.append(dict(
        gauge_id=p,
        area_km2_geom=area_m2[idx[p]] / 1e6,
        n_sub=len(utiles),
        n_sub_directas=sum(1 for k, _ in utiles if k in directas),
        n_sub_todas=len(kids),
        subs=";".join(str(k) for k, _ in utiles[:8]),
        sub_frac=";".join(f"{r:.3f}" for _, r in utiles[:8]),
    ))
nest = pd.DataFrame(rows).set_index("gauge_id")

# ---------- (b) pixeles IMERG --------------------------------------------
def imerg_px(geom):
    geom = shapely.simplify(geom, 0.002)      # ~200 m: irrelevante frente a pixeles de 11 km
    shapely.prepare(geom)                     # contains_xy repetido -> usa indice interno
    minx, miny, maxx, maxy = geom.bounds
    i0, i1 = int(np.floor((minx + 179.95) / 0.1)), int(np.ceil((maxx + 179.95) / 0.1))
    j0, j1 = int(np.floor((miny + 89.95) / 0.1)), int(np.ceil((maxy + 89.95) / 0.1))
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
    xs = (-179.95 + 0.1 * ii).ravel()
    ys = (-89.95 + 0.1 * jj).ravel()
    del ii, jj
    return int(shapely.contains_xy(geom, xs, ys).sum())

nest["imerg_px"] = [imerg_px(geoms[idx[g]]) for g in nest.index]
nest.to_csv("out/geometria.csv")

print(f"out/geometria.csv escrito: {len(nest)} cuencas")
print("\npixeles IMERG (centro dentro de la cuenca):")
print(nest.imerg_px.describe().round(1).to_string())
print(f"\ncuencas con >=1 subcuenca util: {int((nest.n_sub >= 1).sum())}"
      f" | >=2: {int((nest.n_sub >= 2).sum())}"
      f" | >=3: {int((nest.n_sub >= 3).sum())}")
top = nest[nest.n_sub >= 2].join(m[["area", "gauge_department"]]).sort_values(
    "n_sub", ascending=False)
print("\n--- cuencas con 2 o mas subcuencas anidadas ---")
print(top[["area", "gauge_department", "imerg_px", "n_sub", "subs", "sub_frac"]]
      .head(25).round(1).to_string())
