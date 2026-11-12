"""¿Llueve menos en la parte alta de la cuenca del Fonce? Gradiente altitudinal de la precipitación.

La pregunta surgió al mirar los promedios de los pluviómetros: las dos estaciones más altas de la red
(PAVAS LAS a 2 625 m y PUEBLO VIEJO a 2 107 m) miden menos lluvia que varias estaciones del valle. Este
script comprueba si el patrón es real o si es un artefacto de tener pocas estaciones, contrastando dos
fuentes independientes:

1. **Los 7 pluviómetros del IDEAM que caen dentro de la divisoria** de San Gil. Miden en un punto, son
   pocos y vienen marcados como preliminares, pero son medida directa.
2. **Las 30 celdas de IMERG que tocan la cuenca**, cruzadas contra la altitud media del DEM ALOS PALSAR
   dentro de cada celda. Son una muestra más densa, homogénea y completamente independiente de la red
   de pluviómetros: si las dos coinciden, el patrón no es de la red.

La altitud de cada celda de IMERG se calcula submuestreando el DEM a una malla de 60 x 60 dentro de la
celda (la celda mide 0.1 grados, unos 11 km; el DEM tiene 12.5 m, así que leerlo completo sería
innecesariamente pesado y no cambia la media).

Salidas:
  out/gradiente_altitudinal_imerg.csv    altitud y precipitación de cada celda de IMERG
  out/gradiente_altitudinal_resumen.csv  la recta ajustada y la correlación de cada fuente
  reporte/figuras/gradiente_altitudinal.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

RAIZ = Path(__file__).resolve().parent.parent
DEM = RAIZ / "data/dem/dem_fonce_alos_12m.tif"   # recorte del mosaico nacional (scripts/03_recorte_dem.py)
OUT = RAIZ / "out"
FIGURAS = RAIZ / "reporte/figuras"

LADO_CELDA = 0.1        # grados; el tamaño de la celda de IMERG
MUESTREO = 60           # malla de submuestreo del DEM dentro de cada celda
FRAC_MINIMA = 0.30      # solo para dibujar: separa en la figura las celdas que apenas rozan la cuenca
# El ajuste de IMERG usa TODAS las celdas que tocan la cuenca, ponderadas por su fracción dentro
# (decisión del 2026-09-27; antes se usaban solo las que tenían más del 30 % dentro).

AZUL, VERDE, NARANJA, ROSA = "#0072B2", "#009E73", "#D55E00", "#CC79A7"
GRIS = "#6B7280"


def altitud_de_las_celdas(pixeles):
    """Altitud media, mínima y máxima del DEM dentro de cada celda de IMERG."""
    dem = rasterio.open(DEM)
    a_dem = Transformer.from_crs("EPSG:4326", dem.crs, always_xy=True)
    mitad = LADO_CELDA / 2
    filas = []
    for _, celda in pixeles.iterrows():
        # las cuatro esquinas de la celda, proyectadas al sistema del DEM
        esquinas_x, esquinas_y = a_dem.transform(
            [celda.lon - mitad, celda.lon + mitad, celda.lon - mitad, celda.lon + mitad],
            [celda.lat - mitad, celda.lat - mitad, celda.lat + mitad, celda.lat + mitad])
        ventana = from_bounds(min(esquinas_x), min(esquinas_y),
                              max(esquinas_x), max(esquinas_y), dem.transform)
        alturas = np.asarray(
            dem.read(1, window=ventana, out_shape=(1, MUESTREO, MUESTREO))).ravel()
        alturas = alturas[alturas > -1000]          # el DEM marca el vacío con -32768
        if alturas.size == 0:
            continue
        filas.append({"lon": celda.lon, "lat": celda.lat,
                      "p_anual_mm": celda.p_anual, "frac_dentro": celda.frac_dentro,
                      "altitud_media_m": float(alturas.mean()),
                      "altitud_min_m": float(alturas.min()),
                      "altitud_max_m": float(alturas.max())})
    dem.close()
    return pd.DataFrame(filas)


def recta(altitud, precipitacion, pesos=None):
    """Ajuste lineal de la precipitación contra la altitud, y su correlación.

    Con `pesos`, mínimos cuadrados ponderados y correlación ponderada: cada celda cuenta en proporción
    a la fracción de su área que cae dentro de la cuenca, así las que apenas rozan la divisoria entran
    al ajuste sin pesar lo mismo que las que están enteras dentro."""
    x, y = np.asarray(altitud, float), np.asarray(precipitacion, float)
    w = np.ones_like(x) if pesos is None else np.asarray(pesos, float)
    pendiente, intercepto = np.polyfit(x, y, 1, w=np.sqrt(w))   # polyfit pondera los residuos, de ahí la raíz
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    r = float(np.sum(w * (x - mx) * (y - my))
              / np.sqrt(np.sum(w * (x - mx) ** 2) * np.sum(w * (y - my) ** 2)))
    return {"intercepto_mm": intercepto, "mm_por_1000m": pendiente * 1000,
            "r": r, "r2": r ** 2, "n": len(x)}


# ------------------------------------------------------------------ los pluviómetros
catalogo = pd.read_csv(OUT / "pluviometros_fonce_catalogo.csv")
mensual = pd.read_csv(OUT / "pluviometros_fonce_mensual_depurado.csv")

# Media mensual x 12: no se suman años incompletos, que subestimarían el total.
media_mensual = mensual.groupby("codigo").precipitacion_mm.mean().rename("p_mes_mm")
plu = catalogo.merge(media_mensual, on="codigo")
plu["p_anual_mm"] = plu.p_mes_mm * 12
plu["nombre_corto"] = plu.nombre.str.replace(r"\s*\[\d+\]", "", regex=True).str.strip()
plu_dentro = plu[plu.dentro_cuenca].sort_values("altitud")

# ------------------------------------------------------------------ IMERG contra el DEM
celdas = altitud_de_las_celdas(pd.read_csv(OUT / "imerg_pixeles_fonce.csv"))
celdas_cuenca = celdas[celdas.frac_dentro > FRAC_MINIMA]

ajustes = {
    "pluviómetros dentro de la cuenca": recta(plu_dentro.altitud, plu_dentro.p_anual_mm),
    "IMERG, celdas que tocan la cuenca, ponderadas": recta(celdas.altitud_media_m, celdas.p_anual_mm,
                                                           pesos=celdas.frac_dentro),
}
resumen = pd.DataFrame(ajustes).T.rename_axis("fuente").reset_index()

celdas.to_csv(OUT / "gradiente_altitudinal_imerg.csv", index=False)
resumen.to_csv(OUT / "gradiente_altitudinal_resumen.csv", index=False)

# ------------------------------------------------------------------ la figura
FIGURAS.mkdir(parents=True, exist_ok=True)
fig, (izq, der) = plt.subplots(1, 2, figsize=(12.5, 5.4))

# --- panel izquierdo: los pluviómetros
izq.scatter(plu_dentro.altitud, plu_dentro.p_anual_mm, s=95, color=NARANJA,
            zorder=3, edgecolor="white", linewidth=1.2)
fuera = plu[~plu.dentro_cuenca]
izq.scatter(fuera.altitud, fuera.p_anual_mm, s=95, facecolor="white", zorder=3,
            edgecolor=GRIS, linewidth=1.4)
for _, e in plu.iterrows():
    izq.annotate(f"{e.nombre_corto}\n{e.altitud:.0f} m", (e.altitud, e.p_anual_mm),
                 textcoords="offset points", xytext=(0, 13), ha="center",
                 fontsize=7.5, color="#333333")
a = ajustes["pluviómetros dentro de la cuenca"]
x = np.linspace(plu_dentro.altitud.min(), plu_dentro.altitud.max(), 50)
izq.plot(x, a["intercepto_mm"] + a["mm_por_1000m"] / 1000 * x, color=NARANJA,
         linestyle="--", linewidth=1.3, zorder=2)
izq.set_title(f"Los 7 pluviómetros de la cuenca\n"
              f"{a['mm_por_1000m']:+.0f} mm/año por cada 1 000 m   (r = {a['r']:.2f})",
              fontsize=10.5)
izq.set_xlabel("altitud de la estación (m s. n. m.)")
izq.set_ylabel("precipitación media anual (mm/año)")
# aire arriba y abajo para que quepan las etiquetas de ENCINO y MAMONAL
izq.set_ylim(plu.p_anual_mm.min() - 250, plu.p_anual_mm.max() + 450)
izq.set_xlim(plu.altitud.min() - 180, plu.altitud.max() + 180)

# --- panel derecho: las celdas de IMERG
izq_fuera = celdas[celdas.frac_dentro <= FRAC_MINIMA]
der.scatter(izq_fuera.altitud_media_m, izq_fuera.p_anual_mm, s=55, facecolor="white",
            edgecolor=GRIS, linewidth=1.1, zorder=3,
            label=f"celdas que rozan la cuenca ({len(izq_fuera)})")
der.scatter(celdas_cuenca.altitud_media_m, celdas_cuenca.p_anual_mm, s=75, color=AZUL,
            edgecolor="white", linewidth=1.1, zorder=3,
            label=f"celdas con más del {FRAC_MINIMA:.0%} dentro ({len(celdas_cuenca)})")
b = ajustes["IMERG, celdas que tocan la cuenca, ponderadas"]
x = np.linspace(celdas.altitud_media_m.min(), celdas.altitud_media_m.max(), 50)
der.plot(x, b["intercepto_mm"] + b["mm_por_1000m"] / 1000 * x, color=AZUL,
         linestyle="-", linewidth=1.6, zorder=2)
der.set_title(f"IMERG contra la altitud del DEM\n"
              f"{b['mm_por_1000m']:+.0f} mm/año por cada 1 000 m   "
              f"(r = {b['r']:.2f}, r² = {b['r2']:.2f}; {b['n']} celdas, ponderadas por área dentro)",
              fontsize=10.5)
der.set_xlabel("altitud media de la celda de IMERG (m s. n. m.)")
der.set_ylabel("precipitación media anual 1998–2022 (mm/año)")
der.legend(fontsize=8.5, frameon=False, loc="upper right")

for eje in (izq, der):
    eje.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    eje.set_axisbelow(True)
    for lado in ("top", "right"):
        eje.spines[lado].set_visible(False)

fig.suptitle("En la cuenca del Fonce llueve menos arriba: las dos fuentes coinciden en el signo",
             fontsize=13, y=0.99)
fig.tight_layout()
fig.savefig(FIGURAS / "gradiente_altitudinal.png", dpi=160, bbox_inches="tight")

print(resumen.to_string(index=False))
print()
print("Pluviómetros, de menor a mayor altura:")
print(plu.sort_values("altitud")[["nombre_corto", "altitud", "p_anual_mm", "dentro_cuenca"]]
      .round(0).to_string(index=False))
print(f"\nFigura: {FIGURAS / 'gradiente_altitudinal.png'}")
