"""Fase 7 (punto 1): fracción evaporativa frente a la humedad del suelo de la zona de raíces, y su umbral θ*.

Marco (Seneviratne et al., 2010, doi:10.1016/j.earscirev.2010.02.004): con el suelo húmedo, EF = λET/Rn no depende
de la humedad (limitado por energía); por debajo de una humedad crítica θ*, EF cae con la humedad (limitado por agua).

    EF(θ) = EF_max                      si θ ≥ θ*
    EF(θ) = EF_max − b·(θ* − θ)          si θ < θ*

θ* se busca en una malla (percentiles 5 a 95 de θ); para cada θ*, EF_max y b salen por mínimos cuadrados; se queda el
θ* de menor suma de cuadrados.

Datos mensuales 1998–2022:
    θ     SMrz de GLEAM v4.3a, media de la cuenca (m³/m³)
    Rn/λ  de ERA5-Land (script 24, mm/mes)
    ET    (a) mediana de MOD16, TerraClimate, ERA5-Land e y SSEBop v6.1, la que no depende de GLEAM; sin SSEBop v5
              (fuera de ± σ_ET del balance; Juan, 24 nov)
          (b) GLEAM E: circular, porque GLEAM reduce su ET según SMrz; solo para comparar

Escribe productos/punto1/fraccion_evaporativa.csv (mes a mes), fraccion_evaporativa_umbral.csv y
fraccion_evaporativa.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/31_fraccion_evaporativa.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import xarray as xr

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_SM = RAIZ_ENTREGA / "datos" / "punto1" / "gleam_v4" / "gleam_v4_SMrz_mensual_1998_2022_fonce.nc"
ENTRADA_ET = CARPETA_PRODUCTOS / "et_productos_mensual.csv"
SALIDA_MES = CARPETA_PRODUCTOS / "fraccion_evaporativa.csv"
SALIDA_UMBRAL = CARPETA_PRODUCTOS / "fraccion_evaporativa_umbral.csv"
SALIDA_PNG = CARPETA_PRODUCTOS / "fraccion_evaporativa.png"
SIN_GLEAM = ["mod16a2gf", "terraclimate_aet", "era5land_e", "ssebop_v61"]   # sin SSEBop v5 (Juan, 24 nov)


def ajustar_quiebre(theta, ef):
    """θ*, EF_max y b del modelo plano-inclinado por mínimos cuadrados en una malla de θ*."""
    mejor = None
    for t in np.linspace(*np.percentile(theta, [5, 95]), 400):
        x = np.minimum(theta - t, 0)          # 0 arriba de θ*, θ − θ* (negativo) abajo
        a = np.column_stack([np.ones_like(x), x])
        coef, *_ = np.linalg.lstsq(a, ef, rcond=None)
        sse = float(((a @ coef - ef) ** 2).sum())
        if mejor is None or sse < mejor[0]:
            mejor = (sse, t, coef[0], coef[1])
    sse, t, ef_max, b = mejor
    sse_plano = float(((ef - ef.mean()) ** 2).sum())
    return {"theta_critica": t, "EF_max": ef_max, "pendiente_b": b, "r2_frente_a_plano": 1 - sse / sse_plano,
            "meses_bajo_theta": int((theta < t).sum()), "meses": len(theta)}


def main():
    sm = xr.open_dataset(ENTRADA_SM)["SMrz"]
    theta = sm.mean(["lat", "lon"]).to_series()
    theta.index = theta.index.strftime("%Y-%m")
    et = pd.read_csv(ENTRADA_ET).set_index("mes")
    d = pd.DataFrame({"theta": theta, "Rn_lambda": et["Rn_lambda"],
                      "ET_sin_gleam": et[SIN_GLEAM].median(axis=1), "ET_gleam": et["gleam_E"]})
    d["EF_sin_gleam"] = d["ET_sin_gleam"] / d["Rn_lambda"]
    d["EF_gleam"] = d["ET_gleam"] / d["Rn_lambda"]
    d = d.dropna()
    d["mes_calendario"] = d.index.str[5:7].astype(int)

    filas = []
    for nombre in ["sin_gleam", "gleam"]:
        r = ajustar_quiebre(d["theta"].values, d[f"EF_{nombre}"].values)
        bajo = d[d["theta"] < r["theta_critica"]]
        r |= {"ET": nombre, "meses_bajo_theta_por_mes_calendario":
              " ".join(f"{m}:{n}" for m, n in bajo["mes_calendario"].value_counts().sort_index().items())}
        d[f"bajo_theta_{nombre}"] = d["theta"] < r["theta_critica"]
        filas.append(r)
    umbral = pd.DataFrame(filas)[["ET", "theta_critica", "EF_max", "pendiente_b", "r2_frente_a_plano",
                                   "meses_bajo_theta", "meses", "meses_bajo_theta_por_mes_calendario"]]
    d.round(4).to_csv(SALIDA_MES, index_label="mes")
    umbral.round(4).to_csv(SALIDA_UMBRAL, index=False)
    print(f"Listo: {SALIDA_MES}\nListo: {SALIDA_UMBRAL}")
    print(umbral.round(3).to_string(index=False))

    fig, ejes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for eje, fila in zip(ejes, filas):
        n = fila["ET"]
        eje.scatter(d["theta"], d[f"EF_{n}"], s=10, c=d["mes_calendario"], cmap="twilight", alpha=0.8)
        x = np.linspace(d["theta"].min(), d["theta"].max(), 100)
        eje.plot(x, fila["EF_max"] + fila["pendiente_b"] * np.minimum(x - fila["theta_critica"], 0), "k-")
        eje.axvline(fila["theta_critica"], color="k", ls=":", lw=1)
        eje.set_xlabel("SMrz de GLEAM (m³/m³)")
        eje.set_title(f"ET: {'mediana sin GLEAM' if n == 'sin_gleam' else 'GLEAM E (circular)'}; "
                      f"θ* = {fila['theta_critica']:.3f}", fontsize=9)
    ejes[0].set_ylabel("EF = λET/Rn")
    fig.tight_layout()
    fig.savefig(SALIDA_PNG, dpi=150)
    print(f"Listo: {SALIDA_PNG}")


if __name__ == "__main__":
    main()
