"""Fase 5 (punto 1): términos radiativo y aerodinámico de la ETo Penman–Monteith (FAO-56) por mes calendario.

La ETo de FAO-56 (ec. 6) se separa en dos sumandos con el mismo denominador Δ + γ(1 + 0.34 u2):
    radiativo     0.408 Δ (Rn − G)
    aerodinámico  γ · 900/(T + 273) · u2 · (es − ea)
El script 04 ya guarda los dos en productos/punto1/eto_mensual_cuenca.csv (mm/mes, cuenca por Voronoi). Aquí se
promedian por mes calendario (1998–2022) y se calcula la fracción de cada término.

Fracción del mes calendario = media de los 25 años del término / media de la ETo (cociente de medias). Además, el
mínimo y el máximo de la fracción aerodinámica entre los 25 años de ese mes.

Escribe productos/punto1/terminos_fao56_ciclo.csv y productos/punto1/terminos_fao56.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/26_terminos_fao56.py
"""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA = CARPETA_PRODUCTOS / "eto_mensual_cuenca.csv"
SALIDA_CSV = CARPETA_PRODUCTOS / "terminos_fao56_ciclo.csv"
SALIDA_PNG = CARPETA_PRODUCTOS / "terminos_fao56.png"
MESES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


def main():
    eto = pd.read_csv(ENTRADA)
    eto["mes_calendario"] = eto["mes"].str[5:7].astype(int)
    suma = (eto["eto_radiativa_mm_mes"] + eto["eto_aerodinamica_mm_mes"] - eto["eto_mm_mes"]).abs().max()
    assert suma < 0.01, f"radiativo + aerodinámico no da la ETo (máx. {suma:.4f} mm/mes)"
    eto["fraccion_aero"] = eto["eto_aerodinamica_mm_mes"] / eto["eto_mm_mes"]

    por_mes = eto.groupby("mes_calendario")
    ciclo = por_mes[["eto_mm_mes", "eto_radiativa_mm_mes", "eto_aerodinamica_mm_mes"]].mean()
    ciclo["fraccion_radiativa_pct"] = 100 * ciclo["eto_radiativa_mm_mes"] / ciclo["eto_mm_mes"]
    ciclo["fraccion_aerodinamica_pct"] = 100 * ciclo["eto_aerodinamica_mm_mes"] / ciclo["eto_mm_mes"]
    ciclo["fraccion_aerodinamica_min_pct"] = 100 * por_mes["fraccion_aero"].min()
    ciclo["fraccion_aerodinamica_max_pct"] = 100 * por_mes["fraccion_aero"].max()
    ciclo.round(3).to_csv(SALIDA_CSV)
    print(f"Listo: {SALIDA_CSV}")
    print(ciclo[["eto_mm_mes", "fraccion_aerodinamica_pct", "fraccion_aerodinamica_min_pct",
                 "fraccion_aerodinamica_max_pct"]].round(1).to_string())
    anual = eto[["eto_radiativa_mm_mes", "eto_aerodinamica_mm_mes"]].mean() * 12
    print(f"Anual: radiativo {anual.iloc[0]:.0f}, aerodinámico {anual.iloc[1]:.0f} mm/año "
          f"({100 * anual.iloc[1] / anual.sum():.1f} %)")

    fig, eje = plt.subplots(figsize=(8, 4))
    x = range(1, 13)
    eje.bar(x, ciclo["eto_radiativa_mm_mes"], color="#0072B2", label="término radiativo")
    eje.bar(x, ciclo["eto_aerodinamica_mm_mes"], bottom=ciclo["eto_radiativa_mm_mes"], color="#E69F00",
            label="término aerodinámico")
    for m, fila in ciclo.iterrows():
        eje.text(m, fila["eto_mm_mes"] + 1, f"{fila['fraccion_aerodinamica_pct']:.1f} %", ha="center", fontsize=8)
    eje.set_xticks(list(x), MESES)
    eje.set_ylabel("mm/mes")
    eje.set_title("ETo Penman–Monteith (FAO-56), cuenca, media 1998–2022\n(número = fracción aerodinámica)",
                  fontsize=10)
    eje.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(SALIDA_PNG, dpi=150)
    print(f"Listo: {SALIDA_PNG}")


if __name__ == "__main__":
    main()
