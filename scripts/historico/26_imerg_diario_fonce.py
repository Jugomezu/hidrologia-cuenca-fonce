"""Descarga IMERG Final diario V07 (GPM_3IMERGDF, DOI 10.5067/GPM/IMERGDF/DAY/07) recortado a la
cuenca del Fonce, 1998-01-01 a 2022-12-31, y calcula la serie diaria de precipitación promediada
sobre cada una de las seis (sub)cuencas, ponderando cada píxel por la fracción de su área que cae
dentro de la cuenca.

Es el mismo método de scripts/04_imerg_descarga_mensual.py (descarga) y scripts/05_imerg_mensual_cuencas.py
(promedio ponderado por área), pero con el producto diario y solo sobre el recorte del Fonce.

Método: OPeNDAP (ascii) sobre HTTPS con autenticación NASA Earthdata.
  - credenciales en C:/Users/juanp/_netrc.txt (no se versionan)
  - reanudable: salta los días ya descargados
  - 6 descargas simultáneas

Grilla (verificada): lon = -179.95 + 0.1*i ; lat = -89.95 + 0.1*j ; precipitation[time][lon][lat]
Unidades del archivo diario: mm/día (a diferencia del mensual, que viene en mm/h).

Salidas:
  data/imerg/diario/AAAAMMDD.txt    (crudo, tal como lo devuelve OPeNDAP)
  data/imerg/imerg_diario_fonce.npz (grilla empaquetada: precip_mm_dia, lon, lat, fechas)
  out/imerg_diario_fonce.csv        (fecha, id_estacion, p_imerg_mm)
"""
import subprocess, tempfile, sys
import numpy as np, pandas as pd, geopandas as gpd, shapely
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

NETRC = "C:/Users/juanp/_netrc.txt"
BASE = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.07"
I0, I1, J0, J1 = 1065, 1072, 957, 967          # recorte del Fonce con margen de 0.15°
LON = -179.95 + 0.1 * np.arange(I0, I1 + 1)
LAT = -89.95 + 0.1 * np.arange(J0, J1 + 1)
FECHAS = pd.date_range("1998-01-01", "2022-12-31", freq="D")
ESTACIONES = [24027010, 24027070, 24027030, 24027050, 24027040, 24027060]

CRUDO = Path("data/imerg/diario"); CRUDO.mkdir(parents=True, exist_ok=True)
CK = Path(tempfile.gettempdir()) / "earthdata_cookies"; CK.mkdir(parents=True, exist_ok=True)


def url(f):
    archivo = f"3B-DAY.MS.MRG.3IMERG.{f:%Y%m%d}-S000000-E235959.V07B.nc4"
    return (f"{BASE}/{f:%Y/%m}/{archivo}.ascii?precipitation%5B0:0%5D"
            f"%5B{I0}:{I1}%5D%5B{J0}:{J1}%5D")


def bajar(f, worker):
    dst = CRUDO / f"{f:%Y%m%d}.txt"
    if dst.exists() and dst.stat().st_size > 400:
        return f, "ya"
    ck = CK / f"ck{worker}.txt"
    for _ in range(3):
        r = subprocess.run(
            ["curl", "-s", "--netrc-file", NETRC, "-L", "-c", str(ck), "-b", str(ck),
             "--max-time", "120", "-o", str(dst), "-w", "%{http_code}", url(f)],
            capture_output=True, text=True)
        if r.stdout.strip() == "200" and dst.exists() and dst.stat().st_size > 400:
            return f, "ok"
    return f, f"FALLO http={r.stdout.strip()}"


fallos = []
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(bajar, f, k % 6) for k, f in enumerate(FECHAS)]
    for n, fut in enumerate(as_completed(futs), 1):
        f, st = fut.result()
        if st.startswith("FALLO"):
            fallos.append((f.strftime("%Y-%m-%d"), st))
        if n % 250 == 0:
            print(f"  {n}/{len(FECHAS)} días procesados", flush=True)
print(f"descarga terminada; días con fallo: {len(fallos)}", flush=True)
if fallos:
    print("  primeros fallos:", fallos[:10])

# ---- empaquetar la grilla -------------------------------------------------
P = np.full((len(FECHAS), len(LON), len(LAT)), np.nan, dtype=np.float32)
sin_archivo = []
for t, f in enumerate(FECHAS):
    p = CRUDO / f"{f:%Y%m%d}.txt"
    if not p.exists() or p.stat().st_size <= 400:
        sin_archivo.append(f)
        continue
    for linea in p.read_text().splitlines():
        if not linea.startswith("precipitation.precipitation["):
            continue
        cab, vals = linea.split(",", 1)
        lon_txt = cab.split("precipitation.lon=")[1].rstrip("]")
        k = int(round((float(lon_txt) - LON[0]) / 0.1))          # índice de lon dentro del recorte
        P[t, k, :] = np.fromstring(vals, sep=",")
P[P < 0] = np.nan                                                # -9999.9 = sin dato
np.savez_compressed("data/imerg/imerg_diario_fonce.npz",
                    precip_mm_dia=P, lon=LON, lat=LAT, fechas=FECHAS.strftime("%Y-%m-%d").values)
print(f"días sin archivo: {len(sin_archivo)} | celdas sin dato: {int(np.isnan(P).sum())} de {P.size}")

# ---- promedio ponderado por área sobre cada (sub)cuenca -------------------
SHP = "data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/CAMELS_COL_catchments_boundaries.shp"
lista = ",".join(f"'{i}'" for i in ESTACIONES)
g = gpd.read_file(SHP, where=f"IDEAM_CODE IN ({lista})")
g["id"] = g["IDEAM_CODE"].astype("int64")
g = g.to_crs(4326).set_index("id")

filas = []
for id_est in ESTACIONES:
    poly = shapely.simplify(g.loc[id_est, "geometry"], 0.002)     # ~200 m, irrelevante frente a 11 km
    I, J = np.meshgrid(np.arange(len(LON)), np.arange(len(LAT)), indexing="ij")
    celdas = shapely.box(LON[I] - .05, LAT[J] - .05, LON[I] + .05, LAT[J] + .05)
    shapely.prepare(poly)
    w = shapely.area(shapely.intersection(poly, celdas)); w = w / w.sum()
    serie = np.nansum(P * w[None], axis=(1, 2))
    serie[np.all(np.isnan(P), axis=(1, 2))] = np.nan              # día sin ningún píxel = sin dato
    print(f"{id_est}: {int((w > 0).sum())} píxeles | media anual 1998-2022 = "
          f"{np.nanmean(serie) * 365.25:.0f} mm | días sin dato = {int(np.isnan(serie).sum())}")
    filas.append(pd.DataFrame({"fecha": FECHAS.strftime("%Y-%m-%d"), "id_estacion": id_est,
                               "p_imerg_mm": np.round(serie, 3)}))

out = pd.concat(filas, ignore_index=True)
Path("out").mkdir(exist_ok=True)
out.to_csv("out/imerg_diario_fonce.csv", index=False)
print(f"\nout/imerg_diario_fonce.csv: {len(out)} filas "
      f"({out.id_estacion.nunique()} estaciones × {out.fecha.nunique()} días)")
