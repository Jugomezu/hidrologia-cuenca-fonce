"""Figuras de la ETo FAO-56 (punto 1, fase 2): ciclo anual y comprobación con medias mensuales.

Lee las salidas de 04_eto_fao56.py y 04b_comprobaciones_eto.py; no calcula la ETo de nuevo.
    productos/punto1/eto_mensual_cuenca.csv                     ETo mensual de la cuenca y sus dos términos
    productos/punto1/eto_mensual_puntos.csv                     ETo mensual de cada uno de los 6 puntos
    anexos/punto1/eto_medias_mensuales_vs_suma_diarias.csv      ETo con medias mensuales frente a la suma de diarias

Escribe:
    productos/punto1/eto_ciclo_anual.png
        Izquierda: ciclo anual de la ETo de la cuenca (media de 1998–2022 por mes calendario, mm/mes), apilada en su
        término radiativo y su término aerodinámico (suman la ETo).
        Derecha: ciclo anual de la ETo de cada punto, con su altura del DEM, y la de la cuenca.
    anexos/punto1/eto_medias_mensuales_vs_suma_diarias.png
        Diferencia (ETo con medias mensuales − suma de las ETo diarias) en % de la suma de diarias, por mes calendario,
        en la cuenca: la media de los 25 años y el rango (mínimo a máximo) de los 25 valores de cada mes. Se separan
        las dos partes de la diferencia que calcula 04b: la de agregar antes de calcular (con G = 0) y la de G (ec. 43).

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/04e_figuras_eto.py
"""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (va después de fijar el backend sin pantalla)

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
ETO_CUENCA = RAIZ_ENTREGA / "productos" / "punto1" / "eto_mensual_cuenca.csv"
ETO_PUNTOS = RAIZ_ENTREGA / "productos" / "punto1" / "eto_mensual_puntos.csv"
COMPROBACION = RAIZ_ENTREGA / "anexos" / "punto1" / "eto_medias_mensuales_vs_suma_diarias.csv"
ALTURAS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"
FIGURA_CICLO = RAIZ_ENTREGA / "productos" / "punto1" / "eto_ciclo_anual.png"
FIGURA_COMPROBACION = RAIZ_ENTREGA / "anexos" / "punto1" / "eto_medias_mensuales_vs_suma_diarias.png"

MESES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
X = list(range(1, 13))
COLOR_PUNTO = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]   # Okabe–Ito, como el documento de trabajo


def ciclo(tabla, columnas):
    """Media por mes calendario de las columnas dadas (tabla con columna 'mes' AAAA-MM)."""
    mes = pd.to_datetime(tabla["mes"]).dt.month
    return tabla.groupby(mes)[columnas].mean()


def figura_ciclo_anual():
    cuenca = pd.read_csv(ETO_CUENCA)
    assert len(cuenca) == 300
    c = ciclo(cuenca, ["eto_mm_mes", "eto_radiativa_mm_mes", "eto_aerodinamica_mm_mes"])
    puntos = pd.read_csv(ETO_PUNTOS)
    alturas = pd.read_csv(ALTURAS).set_index("punto")["z_celda_dem_m"]

    figura, (izq, der) = plt.subplots(2, 1, figsize=(6.5, 8))
    izq.bar(X, c["eto_radiativa_mm_mes"], color="#E69F00", label="Término radiativo")
    izq.bar(X, c["eto_aerodinamica_mm_mes"], bottom=c["eto_radiativa_mm_mes"], color="#56B4E9",
            label="Término aerodinámico")
    for x, total in zip(X, c["eto_mm_mes"]):
        izq.text(x, total + 1, f"{total:.0f}", ha="center", fontsize=8)
    izq.set_title("Cuenca: ETo por términos (suman la ETo)", fontsize=10)
    izq.set_ylabel("ETo media (mm/mes)")
    izq.legend(fontsize=8, loc="lower center", ncol=2)

    for k, (n, grupo) in enumerate(puntos.groupby("punto")):
        p = ciclo(grupo, ["eto_mm_mes"])["eto_mm_mes"]
        der.plot(X, p, "o-", ms=3, lw=1.2, color=COLOR_PUNTO[k], label=f"Punto {n} ({alturas.loc[n]:.0f} m)")
    der.plot(X, c["eto_mm_mes"], "k-", lw=2.4, label="Cuenca (Voronoi)")
    der.set_title("ETo por punto (altura de la celda en el DEM)", fontsize=10)
    der.legend(fontsize=7.5, ncol=2, loc="lower center")
    for eje in (izq, der):
        eje.set_xticks(X, MESES)
        eje.grid(alpha=0.3, axis="y")
    der.set_ylim(bottom=0)
    izq.set_ylim(bottom=0)
    figura.suptitle("Ciclo anual de la ETo FAO-56 con ERA5-Land, media 1998–2022", fontsize=11)
    figura.tight_layout()
    figura.savefig(FIGURA_CICLO, dpi=150)
    print(f"Listo: {FIGURA_CICLO.relative_to(RAIZ_ENTREGA)}")


def figura_comprobacion():
    tabla = pd.read_csv(COMPROBACION, dtype={"punto": str})
    cuenca = tabla[tabla["punto"] == "cuenca"].copy()
    assert len(cuenca) == 300
    base = cuenca["eto_suma_diarias_mm_mes"]
    cuenca["agregar_pct"] = 100 * cuenca["parte_agregar_mm_mes"] / base
    cuenca["g_pct"] = 100 * cuenca["parte_g_mm_mes"] / base
    mes = pd.to_datetime(cuenca["mes"]).dt.month
    resumen = cuenca.groupby(mes)[["diferencia_pct", "agregar_pct", "g_pct"]].agg(["mean", "min", "max"])

    figura, eje = plt.subplots(figsize=(8, 4.9))
    eje.fill_between(X, resumen[("diferencia_pct", "min")], resumen[("diferencia_pct", "max")], color="#1B6A80",
                     alpha=0.18, label="Diferencia total, rango de los 25 años")
    eje.plot(X, resumen[("diferencia_pct", "mean")], "o-", color="#1B6A80", label="Diferencia total, media")
    eje.plot(X, resumen[("agregar_pct", "mean")], "s--", color="#E69F00", ms=4, label="Parte de agregar (G = 0), media")
    eje.plot(X, resumen[("g_pct", "mean")], "^:", color="#7C5BC7", ms=4, label="Parte de G (ec. 43), media")
    eje.axhline(0, color="0.4", lw=0.8)
    eje.set_xticks(X, MESES)
    eje.set_ylabel("% de la suma de las ETo diarias")
    eje.grid(alpha=0.3, axis="y")
    eje.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)
    eje.set_title("Cuenca: ETo con medias mensuales menos suma de las ETo diarias, 1998–2022", fontsize=10)
    figura.tight_layout()
    figura.savefig(FIGURA_COMPROBACION, dpi=150)
    print(f"Listo: {FIGURA_COMPROBACION.relative_to(RAIZ_ENTREGA)}")
    print(resumen.round(2).to_string())


def main():
    figura_ciclo_anual()
    figura_comprobacion()


if __name__ == "__main__":
    main()
