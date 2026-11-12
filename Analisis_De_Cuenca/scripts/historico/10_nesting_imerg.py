"""Criterios v2:
  (a) grafo de anidamiento entre las 346 cuencas, via PUNTO DE AFORO
      (B esta anidada en A  <=>  el aforo de B cae dentro del poligono de A
       y area(B) < area(A)).  Esto es hidrologicamente correcto y O(n*m)
       con operaciones baratas, en vez de intersecar poligonos complejos.
  (b) cobertura de pixeles IMERG (0.1 grados), vectorizada.
  (c) estadisticas del registro por variable y dentro de la ventana IMERG.
"""
import geopandas as gpd, pandas as pd, numpy as np, shapely
from pathlib import Path

TS = Path("data/camels_col/hydromet/3_Hydrometeorological_data")
IMERG_START = pd.Timestamp("1998-01-01")      # IMERG V07 arranca en 1998

bas = gpd.read_file("data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/"
                    "CAMELS_COL_catchments_boundaries.shp")
bas["gauge_id"] = bas["IDEAM_CODE"].astype("int64")
bas = bas.to_crs(4326).reset_index(drop=True)
bas["area_m2"] = bas.to_crs(3395).geometry.area.values

m = pd.read_csv("out/camels_col_master.csv").set_index("gauge_id")

# ---------- 1. anidamiento por punto de aforo ----------------------------
gid = bas["gauge_id"].values
lon = m.loc[gid, "lon_wgs84"].values
lat = m.loc[gid, "lat_wgs84"].values
area = bas["area_m2"].values
geoms = bas.geometry.values

kids_of = {int(g): [] for g in gid}
for i in range(len(bas)):
    inside = shapely.contains_xy(geoms[i], lon, lat)   # vectorizado sobre TODOS los aforos
    for j in np.flatnonzero(inside):
        if j == i:
            continue
        if area[j] < area[i]:                          # hija mas pequenia que la madre
            kids_of[int(gid[i])].append((int(gid[j]), area[j] / area[i]))

# hijas DIRECTAS: las que no estan contenidas en otra hija de la misma madre
direct = {}
for p, kk in kids_of.items():
    ids = {k for k, _ in kk}
    dd = []
    for k, r in kk:
        if not (ids & {c for c, _ in kids_of[k]}):      # k no contiene a otra hija
            dd.append((k, r))
    direct[p] = sorted(dd, key=lambda t: -t[1])

# ---------- 2. pixeles IMERG (0.1 grados) --------------------------------
def imerg_px(geom):
    minx, miny, maxx, maxy = geom.bounds
    i0, i1 = int(np.floor((minx + 179.95) / 0.1)), int(np.ceil((maxx + 179.95) / 0.1))
    j0, j1 = int(np.floor((miny + 89.95) / 0.1)), int(np.ceil((maxy + 89.95) / 0.1))
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
    xs = (-179.95 + 0.1 * ii).ravel()
    ys = (-89.95 + 0.1 * jj).ravel()
    return int(shapely.contains_xy(geom, xs, ys).sum())

# ---------- 3. registro por variable y ventana IMERG ---------------------
def load(g):
    d = pd.read_csv(TS / f"Hydromet_data_{g}.txt", sep="\t", encoding="latin-1")
    d.columns = ["date", "pr", "etp", "tmin", "tmax", "q"]
    d["date"] = pd.to_datetime(d["date"], format="%d/%m/%Y")
    d = d.set_index("date").sort_index()
    return d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"))

def maxrun(mask):
    v = np.asarray(mask, dtype=np.int8)
    if v.sum() == 0:
        return 0
    idx = np.flatnonzero(np.diff(np.r_[0, v, 0]))
    return int((idx[1::2] - idx[::2]).max())

rows = []
for n, g0 in enumerate(gid):
    g = int(g0)
    d = load(g); q = d["q"]; obs = q.dropna()
    w = d.loc[IMERG_START:]; wq = w["q"]
    ycnt = wq.resample("YE").count()
    kk = [(k, r) for k, r in direct[g] if 0.02 <= r <= 0.85]
    rows.append(dict(
        gauge_id=g,
        imerg_px=imerg_px(geoms[n]),
        yrs_full=len(obs) / 365.25,
        miss_q_full=100 * q.isna().mean(),
        gap_q_full=maxrun(q.isna()),
        miss_pr=100 * d["pr"].isna().mean(),
        miss_tmin=100 * d["tmin"].isna().mean(),
        miss_etp=100 * d["etp"].isna().mean(),
        yrs_imerg=wq.notna().sum() / 365.25,
        miss_q_imerg=100 * wq.isna().mean() if len(w) else np.nan,
        gap_q_imerg=maxrun(wq.isna()) if len(w) else np.nan,
        fullyrs_imerg=int((ycnt >= 350).sum()),
        start_obs=obs.index.min(), end_obs=obs.index.max(),
        n_sub=len(kk),
        subs=";".join(str(k) for k, _ in kk[:8]),
        sub_frac=";".join(f"{r:.3f}" for _, r in kk[:8]),
        n_sub_all=len(kids_of[g]),
    ))

res = pd.DataFrame(rows).set_index("gauge_id")
res.to_csv("out/nesting_imerg_raw.csv")
out = m.join(res, how="left")
out.to_csv("out/master_v2.csv")

print("master_v2:", out.shape)
print("\npixeles IMERG por cuenca:",
      {k: round(v, 1) for k, v in out.imerg_px.describe().to_dict().items()})
print("cuencas con >=1 subcuenca directa:", int((out.n_sub >= 1).sum()),
      "| >=2:", int((out.n_sub >= 2).sum()), "| >=3:", int((out.n_sub >= 3).sum()))
print("\nfaltantes por variable (mediana %):",
      {c: round(out[c].median(), 2) for c in
       ["miss_q_full", "miss_pr", "miss_tmin", "miss_etp"]})
print("anios de caudal en ventana IMERG (1998+):",
      {k: round(v, 2) for k, v in out.yrs_imerg.describe().to_dict().items()})
