"""Mapas de correlación de la cuenca con los campos climáticos (Punto 5.2), figuras fijas del informe.

Lee out/correlaciones_campos.nc (lo escribe scripts/18_calculos_informe.py) y dibuja, para cada combinación de
variable de la cuenca, campo y rezago, doce paneles comparables, uno por mes del calendario de la cuenca, con:
  - escala divergente común de -1 a 1 centrada en cero (la misma en todos los mapas);
  - en gris: la tierra en la SST, 850 hPa bajo el terreno y las cajas con menos pares que el mínimo;
  - la cuenca marcada; dominio de 60° S a 60° N (decisión del usuario);
  - en los mapas del viento, flechas con la dirección del viento medio de ese mes a 850 hPa;
  - en cada panel, el rango de pares (n) de las cajas dibujadas, y el rezago en el título;
  - puntos negros en las cajas que sobreviven a la corrección por pruebas múltiples (FDR de Benjamini-Hochberg por
    panel, con el q que guarda out/correlaciones_campos.nc; el color no se oculta en las demás). El mapa de todos
    los meses juntos no lleva puntos: sus meses seguidos no son independientes y la prueba t no vale ahí.
Además, un mapa por combinación con todos los meses juntos (anomalías).

Uso:  python scripts/21_mapas_correlacion.py            (todas las figuras)
      python scripts/21_mapas_correlacion.py PL sst 0   (una sola combinación)
"""
import importlib.util
import sys
from pathlib import Path

import matplotlib
import numpy as np
import xarray as xr
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def texto_n(n, dentro):
    """Rango de pares de las cajas dibujadas («n = 23» si todas tienen el mismo)."""
    if not dentro.any():
        return "n insuficiente"
    a, b = int(n[dentro].min()), int(n[dentro].max())
    return f"n = {a}" if a == b else f"n = {a}–{b}"

RAIZ = Path(__file__).resolve().parents[1]
CORRELACIONES = RAIZ / "out/correlaciones_campos.nc"
CAMPOS = RAIZ / "out/campos_climaticos_2deg_1998_2022.nc"
FIGURAS = RAIZ / "reporte/figuras"
DPI = 150
DOMINIO = (0, 360, -60, 60)
PASO_FLECHAS = 4                  # una flecha cada 4 cajas (8°)

# las funciones de mapa comunes están en scripts/20_mapas_campos.py
_spec = importlib.util.spec_from_file_location("mapas_campos", RAIZ / "scripts/20_mapas_campos.py")
mapas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mapas)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
NOMBRE_CAMPO = {"sst": "SST (ERSST v5)", "viento850": "rapidez del viento a 850 hPa (ERA5)",
                "q850": "humedad específica a 850 hPa (ERA5)"}
NOMBRE_CORTO = {"sst": "SST", "viento850": "viento a 850 hPa", "q850": "humedad a 850 hPa"}
NOMBRE_CUENCA = {"PL": "PL (pluviómetros)", "PI": "PI (IMERG)", "Q": "Q (caudal)"}
NOMBRE_METODO = {"r_p": "Pearson", "r_s": "Spearman"}
# combinaciones que se dibujan (decisiones del usuario del 2026-10-09)
COMBINACIONES = [(v, c, 0, "r_p") for v in ("PL", "Q") for c in ("sst", "viento850", "q850")]
COMBINACIONES += [("PI", c, 0, "r_p") for c in ("sst", "q850")]
COMBINACIONES += [(v, "sst", 1, "r_p") for v in ("PL", "Q", "PI")]
COMBINACIONES += [("Q", "sst", 0, "r_s")]


def puntear(ax, lat, lon, q, q_fdr):
    """Un punto en el centro de cada caja que sobrevive al FDR (q < q_fdr)."""
    LON, LAT = np.meshgrid(lon, lat)
    sobrevive = np.isfinite(q) & (q < q_fdr)
    ax.scatter(LON[sobrevive], LAT[sobrevive], s=0.6, c="black", marker=".", linewidths=0)


def guardar(fig, nombre):
    """Guarda la figura y la reduce a 256 colores (paleta indexada): las figuras van incrustadas en el informe y, a
    todo color, cada una pesa cerca de 1 MB; con la escala continua de los mapas la diferencia no se ve."""
    ruta = FIGURAS / nombre
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    Image.open(ruta).convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(ruta, optimize=True)


def nombre_figura(v, campo, l, metodo):
    sufijo = "" if metodo == "r_p" else "_spearman"
    return f"corr_{v}_{campo}_l{l}{sufijo}.png"


def figura(v, campo, l, metodo, corr, campos, tierra, n_minimo):
    lat, lon = corr.lat.values, corr.lon.values
    r = corr[f"{metodo}__{v}__{campo}__l{l}"].values
    n = corr[f"n__{v}__{campo}__l{l}"].values
    q = corr[f"q_{metodo[-1]}__{v}__{campo}__l{l}"].values          # r_p -> q_p, r_s -> q_s
    q_fdr = float(corr.attrs["q_fdr"])
    fig, ejes = plt.subplots(4, 3, figsize=(16, 10.5), constrained_layout=True)
    if campo == "viento850":
        LON, LAT = np.meshgrid(lon, lat)
        sel = (slice(None, None, PASO_FLECHAS), slice(None, None, PASO_FLECHAS))
        u_mes = campos.u850.groupby("tiempo.month").mean("tiempo").values
        v_mes = campos.v850.groupby("tiempo.month").mean("tiempo").values
    for k, ax in enumerate(ejes.flat):
        dentro = n[k] >= n_minimo
        n_txt = texto_n(n[k], dentro)
        m = mapas.dibujar_correlacion(ax, lat, lon, r[k], n[k], n_minimo, tierra, f"{MESES[k]}  ({n_txt})",
                                      extension=DOMINIO, pasos=(60, 30), tam_titulo=10)
        puntear(ax, lat, lon, q[k], q_fdr)
        if campo == "viento850":
            # dirección del viento medio del mes (flechas de largo fijo: solo indican hacia dónde sopla)
            uu, vv = u_mes[k][sel], v_mes[k][sel]
            rapidez = np.hypot(uu, vv)
            with np.errstate(invalid="ignore", divide="ignore"):
                ax.quiver(LON[sel], LAT[sel], uu / rapidez, vv / rapidez, color="#333333", scale=55, width=0.0022,
                          headwidth=4, alpha=0.8)
    barra = fig.colorbar(m, ax=ejes, orientation="horizontal", fraction=0.03, pad=0.01, aspect=60,
                         ticks=np.linspace(-1, 1, 9))
    barra.set_label(f"correlación de {NOMBRE_METODO[metodo]} entre las anomalías (escala común de −1 a 1)", fontsize=10)
    rez = "sin rezago (ℓ = 0)" if l == 0 else f"rezago ℓ = {l}: el campo, {l} mes{'es' if l > 1 else ''} antes"
    extra = "; flechas: dirección del viento medio del mes" if campo == "viento850" else ""
    fig.suptitle(f"{NOMBRE_CUENCA[v]} contra {NOMBRE_CAMPO[campo]}, cada mes del calendario de la cuenca, 1998–2022, "
                 f"{rez}. Gris: sin dato o menos de {n_minimo} pares; puntos: sobreviven al FDR (q < {q_fdr:.2f})"
                 f"{extra}", fontsize=11.5, x=0.01, ha="left")
    guardar(fig, nombre_figura(v, campo, l, metodo))


def figura_todos(corr, tierra, n_minimo):
    """Un panel por combinación base (ℓ = 0, Pearson) con todos los meses juntos (anomalías)."""
    base = [(v, c) for v in ("PL", "Q", "PI") for c in ("sst", "viento850", "q850")]
    lat, lon = corr.lat.values, corr.lon.values
    fig, ejes = plt.subplots(3, 3, figsize=(16, 8.2), constrained_layout=True)
    for (v, c), ax in zip(base, ejes.flat):
        r = corr[f"r_p__{v}__{c}__l0"].values[12]
        n = corr[f"n__{v}__{c}__l0"].values[12]
        dentro = n >= n_minimo
        m = mapas.dibujar_correlacion(ax, lat, lon, r, n, n_minimo, tierra,
                                      f"{v} contra {NOMBRE_CORTO[c]}  "
                                      f"({texto_n(n, dentro)})",
                                      extension=DOMINIO, pasos=(60, 30), tam_titulo=10)
    barra = fig.colorbar(m, ax=ejes, orientation="horizontal", fraction=0.04, pad=0.01, aspect=60,
                         ticks=np.linspace(-1, 1, 9))
    barra.set_label("correlación de Pearson entre las anomalías (escala común de −1 a 1)", fontsize=10)
    fig.suptitle("Todos los meses juntos (anomalías respecto a cada mes del calendario), 1998–2022, sin rezago. "
                 f"Gris: sin dato o menos de {n_minimo} pares. Sin puntos de significancia: los meses seguidos no son "
                 "independientes", fontsize=11.5, x=0.01, ha="left")
    guardar(fig, "corr_todos_los_meses.png")


def main():
    FIGURAS.mkdir(parents=True, exist_ok=True)
    corr = xr.open_dataset(CORRELACIONES)
    campos = xr.open_dataset(CAMPOS)
    tierra = mapas.mascara_tierra(campos.sst)
    n_minimo = int(corr.attrs["n_minimo"])
    pedidas = COMBINACIONES
    if len(sys.argv) == 4:
        v, c, l = sys.argv[1], sys.argv[2], int(sys.argv[3])
        pedidas = [(v, c, l, "r_p")]
    for v, c, l, metodo in pedidas:
        figura(v, c, l, metodo, corr, campos, tierra, n_minimo)
        print("listo", nombre_figura(v, c, l, metodo), flush=True)
    if len(sys.argv) != 4:
        figura_todos(corr, tierra, n_minimo)
        print("listo corr_todos_los_meses.png")


if __name__ == "__main__":
    main()
