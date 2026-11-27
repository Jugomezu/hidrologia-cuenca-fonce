"""Fase 7 (punto 1): clasificación de cada mes como limitado por energía o por agua.

Criterio (Juan, 2026-11-24): el del espacio de Budyko, con el índice de aridez φ = ETP/P, aquí φ = ETo/P (ETo
Penman–Monteith (FAO-56) de la cuenca, script 04):
    φ < 1   limitado por energía (la lluvia del mes cubre la demanda)
    φ > 1   limitado por agua    (la demanda supera la lluvia; la ET depende del agua guardada)
Lluvia: P̄ = (PI + PL)/2 (Juan, 2026-11-23); solo P̄, sin PI ni PL (Juan, 2026-11-24).

Dos lecturas:
    ciclo medio      φ del mes calendario con las medias 1998–2022 de ETo y P
    mes a mes        fracción de los meses de cada mes calendario con φ > 1 (cuántos años ese mes fue limitado por agua)

Entrada: productos/punto1/et_productos_mensual.csv (script 24).
Escribe productos/punto1/regimen_mensual.csv y productos/punto1/regimen_mensual.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/30_regimen_mensual.py
"""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA = CARPETA_PRODUCTOS / "et_productos_mensual.csv"
SALIDA_CSV = CARPETA_PRODUCTOS / "regimen_mensual.csv"
SALIDA_PNG = CARPETA_PRODUCTOS / "regimen_mensual.png"
LLUVIAS = {"Pm": "P̄"}   # solo P̄ (Juan, 24 nov)


def clase(phi):
    return "limitado por agua" if phi > 1 else "limitado por energía"


def main():
    d = pd.read_csv(ENTRADA)
    d["mes_calendario"] = d["mes"].str[5:7].astype(int)
    ciclo = d.groupby("mes_calendario")[["ETo", *LLUVIAS]].mean()
    filas = []
    for m, fila in ciclo.iterrows():
        meses = d[d["mes_calendario"] == m]
        salida = {"mes": m, "ETo_mm": fila["ETo"]}
        for p in LLUVIAS:
            phi = fila["ETo"] / fila[p]
            validos = meses[p].notna() & meses["ETo"].notna()
            salida |= {f"{p}_mm": fila[p], f"phi_{p}": phi, f"clase_{p}": clase(phi),
                       f"fraccion_meses_agua_{p}": float((meses.loc[validos, "ETo"] / meses.loc[validos, p] > 1).mean()),
                       f"n_meses_{p}": int(validos.sum())}
        filas.append(salida)
    tabla = pd.DataFrame(filas)
    tabla.round(4).to_csv(SALIDA_CSV, index=False)
    print(f"Listo: {SALIDA_CSV}")
    print(tabla[["mes", "phi_Pm", "clase_Pm", "fraccion_meses_agua_Pm"]].round(2).to_string(index=False))

    fig, eje = plt.subplots(figsize=(6.5, 3.6))
    eje.axhspan(1, 2, color="#E69F00", alpha=0.15, label="limitado por agua (φ > 1)")
    eje.axhspan(0, 1, color="#0072B2", alpha=0.08, label="limitado por energía (φ < 1)")
    eje.plot(tabla["mes"], tabla["phi_Pm"], "k-o", lw=2, label="φ con P̄")
    eje.set_xticks(range(1, 13), ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    eje.set_xlim(0.5, 12.5)
    eje.set_ylim(0, 1.6)
    eje.set_xlabel("mes")
    eje.set_ylabel("φ = ETo/P")
    eje.legend(fontsize=7, loc="upper right")
    eje.set_title("Índice de aridez mensual, ciclo medio 1998–2022", fontsize=9)
    fig.tight_layout()
    fig.savefig(SALIDA_PNG, dpi=150)
    print(f"Listo: {SALIDA_PNG}")


if __name__ == "__main__":
    main()
