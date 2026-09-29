"""Descarga IMERG Final mensual V07 (GPM_3IMERGM, DOI 10.5067/GPM/IMERG/3B-MONTH/07)
recortado a Colombia, 1998-01 a 2022-12, y lo empaqueta en un solo .npz.

*** AVISO: ESTE SCRIPT NECESITA CREDENCIALES DE NASA EARTHDATA ***
Para volver a descargar hay que tener una cuenta gratuita en https://urs.earthdata.nasa.gov (con la
aplicacion "NASA GESDISC DATA ARCHIVE" autorizada) y un archivo netrc con esas credenciales:
    machine urs.earthdata.nasa.gov login <usuario> password <clave>
La ruta de ese archivo se fija abajo en NETRC; la que viene es la del equipo donde se descargo y hay que
cambiarla por la propia. Los datos ya descargados vienen en data/imerg/, asi que para reproducir el
analisis NO hace falta correr este script.

Metodo: OPeNDAP (ascii) sobre HTTPS con autenticacion NASA Earthdata.
  - credenciales en el archivo NETRC (no versionar)
  - reanudable: salta los meses ya descargados
  - 6 descargas simultaneas

Grilla (verificada): lon = -179.95 + 0.1*i ; lat = -89.95 + 0.1*j
Recorte: i = 1004..1136 (lon -79.55 .. -66.35), j = 853..1037 (lat -4.65 .. 13.75)
Unidades del archivo: mm/h (tasa media del mes) -> se convierte a mm/mes.

Salida: data/imerg/mensual/AAAAMM.txt (crudo) y data/imerg/imerg_mensual_col.npz
"""
import subprocess, calendar, numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

NETRC = "C:/Users/juanp/_netrc.txt"      # CAMBIAR por la ruta del netrc propio (ver el aviso arriba)
BASE = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07"
I0, I1, J0, J1 = 1004, 1136, 853, 1037
OUT = Path("data/imerg/mensual"); OUT.mkdir(parents=True, exist_ok=True)
import tempfile
# cookies de sesion Earthdata: fuera del proyecto (son tokens, no se comparten)
CK = Path(tempfile.gettempdir()) / "earthdata_cookies"; CK.mkdir(parents=True, exist_ok=True)
MESES = [(y, mo) for y in range(1998, 2023) for mo in range(1, 13)]

def url(y, mo):
    f = f"3B-MO.MS.MRG.3IMERG.{y}{mo:02d}01-S000000-E235959.{mo:02d}.V07B.HDF5"
    return (f"{BASE}/{y}/{f}.ascii?precipitation%5B0:0%5D"
            f"%5B{I0}:{I1}%5D%5B{J0}:{J1}%5D")

def bajar(ym, worker):
    y, mo = ym
    dst = OUT / f"{y}{mo:02d}.txt"
    if dst.exists() and dst.stat().st_size > 10000:
        return ym, "ya"
    ck = CK / f"ck{worker}.txt"
    for intento in range(3):
        r = subprocess.run(
            ["curl", "-s", "--netrc-file", NETRC, "-L", "-c", str(ck), "-b", str(ck),
             "--max-time", "180", "-o", str(dst), "-w", "%{http_code}", url(y, mo)],
            capture_output=True, text=True)
        if r.stdout.strip() == "200" and dst.exists() and dst.stat().st_size > 10000:
            return ym, "ok"
    return ym, f"FALLO http={r.stdout.strip()}"

fallos = []
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(bajar, ym, k % 6) for k, ym in enumerate(MESES)]
    for n, f in enumerate(as_completed(futs), 1):
        ym, st = f.result()
        if st.startswith("FALLO"):
            fallos.append((ym, st))
        if n % 50 == 0:
            print(f"  {n}/{len(MESES)} meses procesados", flush=True)
print("descarga terminada; fallos:", fallos if fallos else "ninguno")

# ---- empaquetar -------------------------------------------------------
nlon, nlat = I1 - I0 + 1, J1 - J0 + 1
arr = np.full((len(MESES), nlon, nlat), np.nan, dtype=np.float32)
for t, (y, mo) in enumerate(MESES):
    p = OUT / f"{y}{mo:02d}.txt"
    if not p.exists():
        continue
    for line in p.read_text().splitlines():
        if not line.startswith("precipitation["):
            continue
        head, vals = line.split(",", 1)
        k = int(head.split("][")[1].rstrip("]"))          # indice de lon relativo
        v = np.array([float(x) for x in vals.split(",")], dtype=np.float32)
        v[v < -9000] = np.nan
        horas = calendar.monthrange(y, mo)[1] * 24
        arr[t, k, :] = v * horas                           # mm/h -> mm/mes

lon = -179.95 + 0.1 * np.arange(I0, I1 + 1)
lat = -89.95 + 0.1 * np.arange(J0, J1 + 1)
fechas = np.array([f"{y}-{mo:02d}" for y, mo in MESES])
np.savez_compressed("data/imerg/imerg_mensual_col.npz",
                    precip_mm_mes=arr, lon=lon, lat=lat, fechas=fechas)
print(f"npz: {arr.shape} (meses, lon, lat); meses completos: "
      f"{int((~np.isnan(arr).all(axis=(1, 2))).sum())}/{len(MESES)}")
print(f"media nacional del recorte: {np.nanmean(arr) * 12:.0f} mm/anio")
