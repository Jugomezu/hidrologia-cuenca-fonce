"""Figuras del análisis morfométrico de la cuenca del Fonce (scripts/13_morfometria.py).

Este script NO recalcula nada: solo lee los CSV que ya produjo scripts/13_morfometria.py en
out/ y los dibuja. Cuatro figuras, cada una en su propio archivo:

  1. reporte/figuras/perfil_cauce.png          — perfil topográfico del cauce principal.
  2. reporte/figuras/curva_hipsometrica.png    — curva hipsométrica normalizada.
  3. reporte/figuras/pendientes_orientacion.png — histograma de pendientes + rosa de orientaciones.
  4. reporte/figuras/tiempos_concentracion.png  — tc publicado por CAMELS-COL contra el recalculado
                                                   con la pendiente real del cauce.
"""
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"
FIGURAS = RAIZ / "reporte/figuras"
FIGURAS.mkdir(parents=True, exist_ok=True)

# paleta Okabe-Ito del proyecto (colorblind-safe)
AZUL, VERDE, NARANJA, ROSA = "#0072B2", "#009E73", "#D55E00", "#CC79A7"
GRIS = "#6B7280"


def estilo_cartesiano(eje):
    """Rejilla horizontal tenue y sin bordes arriba/derecha, como el resto de figuras del proyecto."""
    eje.grid(axis="y", color="#E5E7EB", linewidth=0.8, zorder=0)
    eje.set_axisbelow(True)
    for lado in ("top", "right"):
        eje.spines[lado].set_visible(False)


resumen = pd.read_csv(OUT / "morfometria_fonce.csv")


def valor_resumen(magnitud, columna="valor"):
    """Lee un renglón de morfometria_fonce.csv por su nombre. Evita repetir números a mano."""
    return resumen.loc[resumen.magnitud == magnitud, columna].iloc[0]


# =============================================================== 1. perfil del cauce
perfil = pd.read_csv(OUT / "perfil_cauce_fonce.csv")

desnivel_m = perfil.altura_suavizada_m.iloc[0] - perfil.altura_suavizada_m.iloc[-1]
distancia_total_km = perfil.distancia_km.iloc[-1]
pendiente_media = desnivel_m / (distancia_total_km * 1000)
altura_san_gil = perfil.altura_suavizada_m.iloc[-1]

fig, ax = plt.subplots(figsize=(11, 5.6), constrained_layout=True)

base = perfil.altura_m.min() - 150
ax.fill_between(perfil.distancia_km, perfil.altura_suavizada_m, base, color=AZUL, alpha=0.15, zorder=1)
ax.plot(perfil.distancia_km, perfil.altura_m, color=GRIS, linewidth=0.8, alpha=0.6, zorder=2,
        label="perfil crudo (DEM sobre el cauce)")
ax.plot(perfil.distancia_km, perfil.altura_suavizada_m, color=AZUL, linewidth=2.0, zorder=3,
        label="perfil suavizado (monótono, sin repechos)")

ax.scatter([distancia_total_km], [altura_san_gil], color="k", zorder=4, s=55)
ax.annotate(f"San Gil\n{altura_san_gil:.0f} m s. n. m.", (distancia_total_km, altura_san_gil),
            xytext=(-14, 45), textcoords="offset points", ha="right", fontsize=9.5,
            arrowprops=dict(arrowstyle="-", color="k", lw=0.8))
ax.scatter([perfil.distancia_km.iloc[0]], [perfil.altura_suavizada_m.iloc[0]], color=GRIS, zorder=4, s=40)
ax.annotate(f"cabecera del cauce\n{perfil.altura_suavizada_m.iloc[0]:.0f} m s. n. m.",
            (perfil.distancia_km.iloc[0], perfil.altura_suavizada_m.iloc[0]),
            xytext=(14, -8), textcoords="offset points", ha="left", va="top", fontsize=9, color=GRIS)

ax.text(0.02, 0.06,
        f"desnivel total: {desnivel_m:,.0f} m\npendiente media: {pendiente_media:.4f} m/m ({pendiente_media*100:.1f} %)"
        .replace(",", " "),
        transform=ax.transAxes, fontsize=10, va="bottom", ha="left",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#D1D5DB"))

ax.set_xlim(0, distancia_total_km)
ax.set_ylim(base, perfil.altura_m.max() + 150)
ax.set_xlabel("distancia desde la cabecera del cauce (km)")
ax.set_ylabel("altura (m s. n. m.)")
ax.legend(loc="upper right", fontsize=9, frameon=False)
estilo_cartesiano(ax)
ax.set_title(f"El cauce principal del Fonce cae {desnivel_m:,.0f} m en {distancia_total_km:.0f} km hasta San Gil"
             .replace(",", " "), fontsize=12.5, weight="semibold")

fig.savefig(FIGURAS / "perfil_cauce.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print(f"perfil_cauce.png: desnivel {desnivel_m:.0f} m, pendiente media {pendiente_media:.4f} m/m, "
      f"{len(perfil)} puntos")


# =============================================================== 2. curva hipsométrica
hips = pd.read_csv(OUT / "curva_hipsometrica_fonce.csv")
altura_min, altura_max = hips.altura_m.min(), hips.altura_m.max()
hips["altura_relativa"] = (hips.altura_m - altura_min) / (altura_max - altura_min)
integral_hips = valor_resumen("integral hipsométrica")

fig, ax = plt.subplots(figsize=(7.4, 6.6), constrained_layout=True)
ax.fill_between(hips.fraccion_area_encima, hips.altura_relativa, 0, color=VERDE, alpha=0.25, zorder=1)
ax.plot(hips.fraccion_area_encima, hips.altura_relativa, color=VERDE, linewidth=2.2, zorder=2)
ax.plot([0, 1], [1, 0], color=GRIS, linewidth=1, linestyle="--", zorder=1,
        label="diagonal (integral = 0,5)")

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_xlabel("fracción del área de la cuenca por encima de la altura (—)")
ax.set_ylabel("altura relativa,  (h − h_mín) / (h_máx − h_mín)  (—)")
ax.legend(loc="upper right", fontsize=8.5, frameon=False)
estilo_cartesiano(ax)

eje_alturas = ax.twinx()
eje_alturas.set_ylim(altura_min, altura_max)
eje_alturas.set_ylabel("altura real (m s. n. m.)")
eje_alturas.spines["top"].set_visible(False)

ax.text(0.58, 0.62,
        f"integral hipsométrica = {integral_hips:.2f}\n\n"
        "por debajo de ~0,35–0,40:\ncuenca madura, en fase de\nequilibrio, ya erosionada\n(no juvenil)",
        transform=ax.transAxes, fontsize=9.5, va="top", ha="left",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="#D1D5DB"))

ax.set_title(f"Curva hipsométrica: integral = {integral_hips:.2f}, cuenca madura y ya erosionada",
             fontsize=12.5, weight="semibold")

fig.savefig(FIGURAS / "curva_hipsometrica.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print(f"curva_hipsometrica.png: integral hipsométrica = {integral_hips:.3f}, "
      f"altura {altura_min:.0f}-{altura_max:.0f} m")


# =============================================================== 3. pendientes + orientación
pend = pd.read_csv(OUT / "pendientes_fonce.csv")
orient = pd.read_csv(OUT / "orientaciones_fonce.csv")

frac_mayor_20 = pend.loc[pend.desde_grados >= 20, "fraccion_area"].sum()
frac_mayor_30 = pend.loc[pend.desde_grados >= 30, "fraccion_area"].sum()
mediana_pend = valor_resumen("pendiente mediana del terreno")

fig = plt.figure(figsize=(13, 6.2), constrained_layout=True)
izq = fig.add_subplot(1, 2, 1)
der = fig.add_subplot(1, 2, 2, projection="polar")

# --- panel izquierdo: histograma de pendientes
ancho = pend.hasta_grados - pend.desde_grados
izq.bar(pend.desde_grados, pend.fraccion_area * 100, width=ancho, align="edge",
        color=AZUL, edgecolor="white", linewidth=0.6, zorder=2)
izq.axvline(mediana_pend, color=NARANJA, linewidth=1.8, linestyle="--", zorder=3)
izq.annotate(f"mediana = {mediana_pend:.1f}°", (mediana_pend, izq.get_ylim()[1]),
             xytext=(6, -4), textcoords="offset points", fontsize=9.5, color=NARANJA, va="top")

izq.text(0.97, 0.93,
          f"{frac_mayor_20*100:.0f} % del área supera los 20°\n{frac_mayor_30*100:.0f} % del área supera los 30°",
          transform=izq.transAxes, fontsize=9.5, va="top", ha="right",
          bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#D1D5DB"))

izq.set_xlim(0, pend.hasta_grados.max())
izq.set_xlabel("pendiente del terreno (°)")
izq.set_ylabel("fracción del área de la cuenca (%)")
izq.set_title("Ladera predominantemente empinada: mediana de "
              f"{mediana_pend:.1f}°", fontsize=11.5, weight="semibold")
estilo_cartesiano(izq)

# --- panel derecho: rosa de orientaciones
# el rumbo ya viene en orden horario empezando en N, cada uno a 22.5° del anterior (ver 13_morfometria.py)
angulos = np.radians(np.arange(len(orient)) * 22.5)
ancho_barra = np.radians(22.5)
dominante = orient.loc[orient.fraccion_area.idxmax()]
colores = [ROSA if r == dominante.rumbo else NARANJA for r in orient.rumbo]

der.bar(angulos, orient.fraccion_area * 100, width=ancho_barra, color=colores,
        edgecolor="white", linewidth=0.7, zorder=2, align="center")
der.set_theta_zero_location("N")
der.set_theta_direction(-1)          # sentido horario
der.set_xticks(angulos)
der.set_xticklabels(orient.rumbo, fontsize=8.5)
der.set_ylabel("")
# las etiquetas radiales de un gráfico polar quedan SIEMPRE detrás de las barras (no respetan zorder);
# como todos los rumbos tienen más del 4.8 % de área, cualquier marca por debajo de eso quedaría tapada
# sin remedio. Se etiqueta solo por encima del mínimo (rumbo SSE, el de menos área) y se pone esa marca
# sobre el propio rumbo SSE, donde la barra es más corta y deja hueco libre hasta el borde.
der.set_rlabel_position(157.5)
der.set_yticks([6, 8])
der.set_yticklabels(["6 %", "8 %"], fontsize=8)
for etiqueta in der.get_yticklabels():
    etiqueta.set_path_effects([pe.withStroke(linewidth=2.5, foreground="white")])
der.set_title(f"Laderas orientadas sobre todo al {dominante.rumbo} "
              f"({dominante.fraccion_area*100:.1f} % del área)", fontsize=11.5, weight="semibold", pad=8)

fig.suptitle("Relieve de la cuenca del Fonce: pendientes fuertes, laderas orientadas al occidente",
             fontsize=13.5, y=1.08)

fig.savefig(FIGURAS / "pendientes_orientacion.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print(f"pendientes_orientacion.png: {frac_mayor_20*100:.1f}% > 20°, {frac_mayor_30*100:.1f}% > 30°, "
      f"mediana {mediana_pend:.1f}°; rumbo dominante {dominante.rumbo} ({dominante.fraccion_area*100:.1f}%)")


# =============================================================== 4. tiempos de concentración
tc = pd.read_csv(OUT / "tiempos_concentracion.csv")
pendiente_taylor = valor_resumen("pendiente del cauce (Taylor-Schwarz)")
equi_slope_camels = valor_resumen("pendiente del cauce (Taylor-Schwarz)", "publicado_camels")
factor = pendiente_taylor / equi_slope_camels

x = np.arange(len(tc))
ancho = 0.36

fig, ax = plt.subplots(figsize=(9.5, 6.2), constrained_layout=True)
barras_pub = ax.bar(x - ancho / 2, tc.publicado_camels_h, ancho, color=NARANJA, zorder=2,
                     label="publicado por CAMELS-COL (con su equi_slope)")
barras_med = ax.bar(x + ancho / 2, tc.con_pendiente_medida_h, ancho, color=AZUL, zorder=2,
                     label="recalculado con la pendiente real del cauce (Taylor-Schwarz)")

for barras in (barras_pub, barras_med):
    for b in barras:
        ax.annotate(f"{b.get_height():.1f}", (b.get_x() + b.get_width() / 2, b.get_height()),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8.5)

ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels(tc.formula)
ax.set_ylabel("tiempo de concentración (horas, escala log)")
ax.legend(loc="upper right", fontsize=9, frameon=False)
estilo_cartesiano(ax)
ax.grid(axis="y", which="minor", color="#E5E7EB", linewidth=0.4, zorder=0)

ax.set_title(
    f"CAMELS-COL publica hasta {tc.publicado_camels_h.max():.0f} h porque su equi_slope "
    f"es {factor:.0f} veces menor que la pendiente real;\ncon la pendiente medida, Kirpich da "
    f"{tc.loc[tc.formula == 'Kirpich', 'con_pendiente_medida_h'].iloc[0]:.0f} h",
    fontsize=12, weight="semibold")

fig.savefig(FIGURAS / "tiempos_concentracion.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print(f"tiempos_concentracion.png: equi_slope CAMELS = {equi_slope_camels:.2e} m/m, "
      f"pendiente real (Taylor-Schwarz) = {pendiente_taylor:.4f} m/m, factor = {factor:.0f}x")
