"""Fase 9, tema f (punto 1): la rs efectiva frente al esquema de Jarvis, con el LAI de MODIS.

Esquema de Jarvis como lo usa ECMWF (HTESSEL; tabla de Gehrke, Sühring y Maronga, 2021, GMD 14:5307,
doi:10.5194/gmd-14-5307-2021):
    rs = rc,min / LAI · f(radiación) · f(humedad del suelo) · f(déficit),      cada f ≥ 1 (1 = sin estrés).
Con la rs que despeja el script 37 (ra por cobertura) y el LAI de MODIS, el producto de los factores es
    f_total = rs · LAI / rc,min.
Solo se puede separar el factor del déficit: la cuenca está limitada por energía y el suelo casi siempre está húmedo, y la
radiación varía junto con el déficit. Se ajusta, por punto y producto,
    ln f_total = a + g · D        (D = déficit de presión de vapor en hPa; forma exp(g·D) de ECMWF)
y se compara g con el gD de la tabla (0.03 hPa⁻¹ para los árboles; 0 para cultivos y arbustos).

Decisiones:
    - LAI: «lai_todos» del script 38 (todos los píxeles válidos, también los del algoritmo de respaldo; decisión de Juan,
      25 nov). LAI mensual = media de los compuestos de 4 días que empiezan en el mes.
    - rc,min de la celda: el de cada cobertura (Tabla 1 de Gehrke et al., con los tipos que eligió Juan: bosque =
      evergreen broadleaf trees 175 s/m; herbazal andino = evergreen shrubs 225; agropecuario = crops, mixed farming
      180), combinado en paralelo con la fracción de MapBiomas: 1/rc,min = Σ fracción / rc,min. Las «otras» coberturas
      (≤ 2 %) cuentan como agropecuario, igual que en el script 37.
    - Solo los meses con solución (rs > 0); los meses de GLEAM «sin solución» quedan fuera.
Advertencias: el déficit también entra en la inversión del script 37, así que una parte de la relación entre f_total y D
puede salir del propio método; y la rs efectiva mezcla dosel, suelo e intercepción.

Entradas: productos/punto1/resistencia_superficie_mensual.csv y _resumen.csv (script 37);
datos/punto1/mcd15a3h/mcd15a3h_lai_puntos_2002_2022.csv (script 38).
Salidas: productos/punto1/jarvis_lai_mensual.csv, jarvis_lai_resumen.csv y jarvis_lai.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/39_jarvis_lai.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_RS = CARPETA_PRODUCTOS / "resistencia_superficie_mensual.csv"
ENTRADA_RESUMEN_RS = CARPETA_PRODUCTOS / "resistencia_superficie_resumen.csv"
ENTRADA_LAI = RAIZ_ENTREGA / "datos" / "punto1" / "mcd15a3h" / "mcd15a3h_lai_puntos_2002_2022.csv"
SALIDA_MENSUAL = CARPETA_PRODUCTOS / "jarvis_lai_mensual.csv"
SALIDA_RESUMEN = CARPETA_PRODUCTOS / "jarvis_lai_resumen.csv"
SALIDA_FIGURA = CARPETA_PRODUCTOS / "jarvis_lai.png"

# rc,min (s/m) y gD (1/hPa) de la Tabla 1 de Gehrke et al. (2021), con los tipos elegidos por Juan
RC_MIN = {"bosque": 175.0, "herbazal_andino": 225.0, "agropecuario": 180.0}
GD_TABLA_ARBOLES = 0.03
COLUMNA_LAI = "lai_todos"


def lai_mensual():
    lai = pd.read_csv(ENTRADA_LAI, parse_dates=["fecha_inicio"])
    lai["mes"] = lai["fecha_inicio"].dt.to_period("M").astype(str)
    return (lai.groupby(["punto", "mes"])[COLUMNA_LAI].agg(["mean", "count"])
            .rename(columns={"mean": "lai", "count": "compuestos_lai"}).reset_index())


def rc_min_celda(resumen_rs):
    """rc,min de la celda de cada punto, en paralelo con la fracción de cada cobertura."""
    f = resumen_rs.drop_duplicates("punto").set_index("punto")
    agro = f["frac_agropecuario"] + f["frac_otras"]
    conductancia = (f["frac_bosque"] / RC_MIN["bosque"] + f["frac_herbazal_andino"] / RC_MIN["herbazal_andino"]
                    + agro / RC_MIN["agropecuario"])
    return 1 / conductancia


def ajuste_deficit(g):
    """OLS de ln f_total contra D (hPa): pendiente g, su error estándar, R² y n."""
    x, y = g["deficit_hPa"].to_numpy(), np.log(g["f_total"].to_numpy())
    n = len(x)
    pend, corte = np.polyfit(x, y, 1)
    residuo = y - (corte + pend * x)
    error = np.sqrt(residuo @ residuo / (n - 2) / ((x - x.mean()) @ (x - x.mean())))
    r2 = 1 - (residuo @ residuo) / ((y - y.mean()) @ (y - y.mean()))
    return pend, error, r2, n


def main():
    rs = pd.read_csv(ENTRADA_RS)
    resumen_rs = pd.read_csv(ENTRADA_RESUMEN_RS)
    rc_min = rc_min_celda(resumen_rs)

    tabla = rs[["producto", "punto", "mes", "z_modelo_m", "rs_sm", "sin_solucion", "deficit_kPa", "t_C"]].merge(
        lai_mensual(), on=["punto", "mes"], how="inner")
    tabla = tabla[~tabla["sin_solucion"] & tabla["lai"].notna()].copy()
    tabla["deficit_hPa"] = 10 * tabla["deficit_kPa"]
    tabla["rc_min_celda_sm"] = tabla["punto"].map(rc_min)
    tabla["rs_por_lai_sm"] = tabla["rs_sm"] * tabla["lai"]
    tabla["f_total"] = tabla["rs_por_lai_sm"] / tabla["rc_min_celda_sm"]
    assert (tabla["f_total"] > 0).all()

    filas = []
    for (prod, n), g in tabla.groupby(["producto", "punto"]):
        pend, error, r2, meses = ajuste_deficit(g)
        filas.append({
            "producto": prod, "punto": n, "z_modelo_m": g["z_modelo_m"].iloc[0], "meses": meses,
            "lai_mediana": g["lai"].median(), "rs_mediana_sm": g["rs_sm"].median(),
            "rs_por_lai_mediana_sm": g["rs_por_lai_sm"].median(), "rc_min_celda_sm": rc_min[n],
            "f_total_mediana": g["f_total"].median(), "deficit_medio_hPa": g["deficit_hPa"].mean(),
            "g_deficit_por_hPa": pend, "g_ic95_inferior": pend - 1.96 * error, "g_ic95_superior": pend + 1.96 * error,
            "r2_ln_f_vs_deficit": r2,
        })
    resumen = pd.DataFrame(filas)
    # pendiente con la altura (n = 6, descriptiva) de rs y de rs·LAI
    for prod, r in resumen.groupby("producto"):
        for col in ("rs_mediana_sm", "rs_por_lai_mediana_sm", "lai_mediana"):
            resumen.loc[r.index, f"{col}_por_km"] = np.polyfit(r["z_modelo_m"] / 1000, r[col], 1)[0]
    resumen["g_tabla_arboles_por_hPa"] = GD_TABLA_ARBOLES

    salida = tabla.drop(columns="sin_solucion")
    salida.round(4).to_csv(SALIDA_MENSUAL, index=False)
    resumen.round(4).to_csv(SALIDA_RESUMEN, index=False)
    figura(tabla, resumen)

    pd.set_option("display.width", 220)
    print(resumen.drop(columns=["g_tabla_arboles_por_hPa"]).round(3).to_string())
    print(f"Listo: {SALIDA_MENSUAL.name}, {SALIDA_RESUMEN.name}, {SALIDA_FIGURA.name}")


def figura(tabla, resumen):
    colores = {"GLEAM v4.3a": "#CC79A7", "SSEBop v6.1": "#E69F00"}
    fig, ejes = plt.subplots(1, 3, figsize=(16, 4.8))
    for prod, r in resumen.groupby("producto"):
        r = r.sort_values("z_modelo_m")
        ejes[0].plot(r["rs_mediana_sm"], r["z_modelo_m"], "o--", color=colores[prod], alpha=0.5, label=f"{prod}: rs")
        ejes[0].plot(r["rs_por_lai_mediana_sm"], r["z_modelo_m"], "o-", color=colores[prod], label=f"{prod}: rs · LAI")
    tabla_puntos = resumen.drop_duplicates("punto").sort_values("z_modelo_m")
    ejes[0].plot(tabla_puntos["rc_min_celda_sm"], tabla_puntos["z_modelo_m"], "k:", label="rc,min de la tabla (celda)")
    ejes[0].set_xlim(0, None)
    ejes[0].set_xlabel("s/m (medianas)")
    ejes[0].set_ylabel("altura del modelo (m)")
    ejes[0].set_title("rs y rs · LAI frente a la altura")
    ejes[0].legend(fontsize=7)
    ejes[1].plot(tabla_puntos["lai_mediana"], tabla_puntos["z_modelo_m"], "o-", color="#009E73")
    ejes[1].set_xlim(0, None)
    ejes[1].set_xlabel("LAI de MODIS, mediana mensual (m²/m²)")
    ejes[1].set_ylabel("altura del modelo (m)")
    ejes[1].set_title("Índice de área foliar (MCD15A3H)")
    s = tabla[tabla["producto"] == "SSEBop v6.1"]
    z = s.groupby("punto")["z_modelo_m"].first()
    for n, g in s.groupby("punto"):
        color = plt.cm.viridis((z[n] - 1600) / 1500)
        ejes[2].scatter(g["deficit_hPa"], g["f_total"], s=8, color=color, alpha=0.6, label=f"punto {n} ({z[n]:.0f} m)")
        fila = resumen[(resumen["producto"] == "SSEBop v6.1") & (resumen["punto"] == n)].iloc[0]
        x = np.linspace(g["deficit_hPa"].min(), g["deficit_hPa"].max(), 20)
        corte = np.log(g["f_total"]).mean() - fila["g_deficit_por_hPa"] * g["deficit_hPa"].mean()
        ejes[2].plot(x, np.exp(corte + fila["g_deficit_por_hPa"] * x), color=color)
    ejes[2].set_yscale("log")
    ejes[2].set_xlabel("déficit de presión de vapor D (hPa)")
    ejes[2].set_ylabel("f_total = rs · LAI / rc,min")
    ejes[2].set_title("SSEBop v6.1: castigo total frente al déficit")
    ejes[2].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(SALIDA_FIGURA, dpi=150)


if __name__ == "__main__":
    main()
