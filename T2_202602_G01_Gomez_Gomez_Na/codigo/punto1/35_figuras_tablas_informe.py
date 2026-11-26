"""Figuras fijas y tablas del informe (punto 1) que todavía solo existían en el documento de trabajo.

No calcula nada nuevo: lee productos que ya escriben otros scripts y los dibuja o los pone en tablas de LaTeX, para que
ninguna cifra del informe se copie a mano.

Entradas (productos/punto1/):
    metodos_mensual.csv          script 21/22: cada método, mm/mes, 1998–2022
    eto_mensual_cuenca.csv       script 04: ETo y sus términos radiativo y aerodinámico
    ajuste_por_mes.csv           script 21: sesgo de cada método frente a su referencia, por mes calendario
    sensibilidad.csv             script 28: cambio % de cada método al perturbar una entrada
    et_productos_vs_balance.csv  script 24: cada producto de ET real frente al balance en sus mismos meses
    et_incertidumbre.csv         script 24: P̄ − Q y σ_ET (95 %)
    et_techo_energia_resumen.csv script 24: Rn/λ y ETo del periodo
    budyko_resumen.csv           script 29: punto multianual, ω de Fu y elasticidades

Escribe:
    productos/punto1/metodos_frente_eto.png       métodos tal cual, en mm/año (diseño de Juan, 22 nov)
    productos/punto1/sensibilidad_metodos.png     cambio anual % de cada método en cada escenario
    productos/punto1/et_real_productos.png        productos de ET real frente a P̄ − Q ± σ_ET
    productos/punto1/tablas_informe/*.tex         tablas que el informe incluye con \\input

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/35_figuras_tablas_informe.py
"""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
CARPETA_TABLAS = CARPETA_PRODUCTOS / "tablas_informe"

PM = "ETo Penman–Monteith (FAO-56)"

# Nombre de cada columna de metodos_mensual.csv tal como aparece en el informe.
NOMBRES_METODOS = {
    "eto_fao56": PM,
    "eto_fao56_rs0": "Penman–Monteith (FAO-56) con rs = 0",
    "penman_fao24": "Penman (FAO-24, c = 0.8)",
    "makkink": "Makkink",
    "hargreaves": "Hargreaves–Samani",
    "cenicafe_2006": "Cenicafé 2006",
    "priestley_taylor": "Priestley–Taylor",
    "thornthwaite": "Thornthwaite",
    "aa_brutsaert_stricker": "Brutsaert–Stricker (AA)",
}

# Diseño de Juan (22 nov): los métodos tal como son, agrupados por la cantidad que estiman; el color dice qué
# variables usa cada uno; línea vertical en la ETo Penman–Monteith (FAO-56).
BLOQUES = [
    ("ETo · pasto de referencia", [PM, "Penman (FAO-24, c = 0.8)", "Makkink", "Hargreaves–Samani", "Cenicafé 2006"]),
    ("ETP · superficie sin falta de agua", ["Priestley–Taylor", "Thornthwaite"]),
    ("ET real · la cuenca", ["Brutsaert–Stricker (AA)"]),
]
COLOR_VARIABLES = {
    "Solo altitud": ("#CC79A7", ["Cenicafé 2006"]),
    "T (y latitud)": ("#A65E1A", ["Thornthwaite"]),
    "T + Ra": ("#7C5BC7", ["Hargreaves–Samani"]),
    "Rs + T": ("#009E73", ["Makkink"]),
    "Rn + T": ("#E69F00", ["Priestley–Taylor"]),
    "Rn + T + humedad + viento": ("#0072B2", [PM, "Penman (FAO-24, c = 0.8)", "Brutsaert–Stricker (AA)"]),
}

ESCENARIOS = {"t+1_ea": "T +1 °C\nea cte", "t+2_ea": "T +2 °C\nea cte", "t+1_hr": "T +1 °C\nHR cte",
              "t+2_hr": "T +2 °C\nHR cte", "u2+10": "u2\n+10 %", "rs-10": "Rs\n−10 %", "ea+10": "ea\n+10 %"}


def miles(valor):
    """Entero con espacio fino para los miles (2 098), como pide el informe."""
    return f"{round(valor):,}".replace(",", " ")


def miles_tex(valor):
    return f"{round(valor):,}".replace(",", "\\,")


def signo(valor, decimales=1):
    texto = f"{abs(valor):.{decimales}f}"
    return ("+" if valor > 0 else "−" if valor < 0 else "±") + texto


def signo_tex(valor, decimales=1):
    texto = f"{abs(valor):.{decimales}f}"
    return ("$+$" if valor > 0 else "$-$" if valor < 0 else "$\\pm$") + texto


def anual_por_metodo():
    """Media anual 1998–2022 de cada método: media de los 300 meses × 12."""
    mensual = pd.read_csv(CARPETA_PRODUCTOS / "metodos_mensual.csv")
    return {NOMBRES_METODOS[c.removesuffix("_mm_mes")]: mensual[c].mean() * 12
            for c in mensual.columns if c.endswith("_mm_mes")}


def figura_metodos(anual):
    terminos = pd.read_csv(CARPETA_PRODUCTOS / "eto_mensual_cuenca.csv")
    radiativo = terminos["eto_radiativa_mm_mes"].mean() * 12
    aerodinamico = terminos["eto_aerodinamica_mm_mes"].mean() * 12
    # La barra de la ETo es la suma de sus dos términos: se comprueba que cuadre con la ETo del script 21.
    assert abs(radiativo + aerodinamico - anual[PM]) < 1, "los términos de la ETo no suman la ETo"
    color_de = {m: c for c, ms in COLOR_VARIABLES.values() for m in ms}

    filas, y, cabeceras = [], 0, []
    for titulo, metodos in BLOQUES:
        cabeceras.append((y, titulo))
        y += 1
        for m in metodos:
            filas.append((y, m))
            y += 1
        y += 0.5

    fig, eje = plt.subplots(figsize=(6.5, 5.6))
    for posicion, m in filas:
        valor = anual[m]
        if m == PM:
            eje.barh(posicion, radiativo, color=color_de[m], height=0.65)
            eje.barh(posicion, aerodinamico, left=radiativo, color="white", edgecolor=color_de[m], hatch="///",
                     height=0.65)
        else:
            eje.barh(posicion, valor, color=color_de[m], height=0.65)
        diferencia = 100 * (valor / anual[PM] - 1)
        texto = f"{miles(valor)}" + ("" if m == PM else f"   {signo(diferencia, 0)} %")
        eje.text(valor + 20, posicion, texto, va="center", fontsize=8,
                 bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.9))
    eje.axvline(anual[PM], color="black", ls="--", lw=1)
    for posicion, titulo in cabeceras:
        eje.text(0, posicion, titulo, va="center", fontsize=8.5, fontweight="bold")
    eje.set_yticks([p for p, _ in filas], [m.replace("ETo ", "") for _, m in filas], fontsize=8)
    eje.invert_yaxis()
    eje.set_xlim(0, max(anual.values()) * 1.22)
    eje.set_xlabel("mm/año (media 1998–2022)")
    eje.spines[["top", "right"]].set_visible(False)
    leyenda = [Patch(color=c, label=g) for g, (c, _) in COLOR_VARIABLES.items()]
    leyenda.append(Patch(facecolor="white", edgecolor="#0072B2", hatch="///", label="término aerodinámico de la ETo"))
    fig.legend(handles=leyenda, title="Variables que usa", fontsize=7, title_fontsize=7.5, loc="lower center", ncol=4,
               frameon=False)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    salida = CARPETA_PRODUCTOS / "metodos_frente_eto.png"
    fig.savefig(salida, dpi=200)
    plt.close(fig)
    print(f"Listo: {salida}")
    return radiativo, aerodinamico


def tabla_metodos(anual):
    """Sesgo de cada método frente a la referencia de su misma superficie, y meses en que supera la dispersión."""
    ajuste = pd.read_csv(CARPETA_PRODUCTOS / "ajuste_por_mes.csv")
    resumen = ajuste.groupby(["metodo", "cantidad", "referencia"], sort=False).agg(
        sesgo=("sesgo_pct", "mean"), minimo=("sesgo_pct", "min"), maximo=("sesgo_pct", "max"),
        rmse=("rmse_mm_mes", "mean"), dentro=("supera_dispersion", lambda s: int((~s.astype(bool)).sum()))).reset_index()
    lineas = [
        "% Generado por codigo/punto1/35_figuras_tablas_informe.py; no se edita a mano.",
        "\\begin{tabular}{llrrrr}", "\\toprule",
        "Método & Se compara con & mm/año & Sesgo \\% (rango mensual) & RMSE (mm/mes) & Meses dentro \\\\",
        " & & & & & de la dispersión \\\\", "\\midrule",
    ]
    for _, r in resumen.iterrows():
        referencia = "\\PM{}" if r["referencia"] == PM else "\\PM{} con $r_s = 0$"
        lineas.append(f"{r['metodo']} & {referencia} & {miles_tex(anual[r['metodo']])} & "
                      f"{signo_tex(r['sesgo'])} ({signo_tex(r['minimo'])} a {signo_tex(r['maximo'])}) & "
                      f"{r['rmse']:.1f} & {r['dentro']} de 12 \\\\")
    lineas += ["\\midrule",
               f"\\ETo{{}} \\PM{{}} & referencia & {miles_tex(anual[PM])} & & & \\\\",
               f"\\PM{{}} con $r_s = 0$ & referencia & {miles_tex(anual['Penman–Monteith (FAO-56) con rs = 0'])} & & & \\\\",
               "\\bottomrule", "\\end{tabular}"]
    escribir_tabla("tabla_metodos.tex", lineas)


def figura_sensibilidad():
    t = pd.read_csv(CARPETA_PRODUCTOS / "sensibilidad.csv", dtype={"mes": str})
    anual = t[t["mes"] == "anual"].pivot(index="metodo", columns="escenario", values="cambio_pct")
    metodos = list(dict.fromkeys(t["metodo"]))
    anual = anual.loc[metodos, list(ESCENARIOS)]
    fig, eje = plt.subplots(figsize=(6.5, 4.8))
    limite = 21  # mismo rango de color que el documento de trabajo; Thornthwaite con +2 °C llega a ~21 %
    assert anual.abs().max().max() <= limite + 0.5, "un cambio sale del rango de color"
    imagen = eje.imshow(anual.values, cmap="RdBu_r", vmin=-limite, vmax=limite, aspect="auto")
    for i in range(anual.shape[0]):
        for j in range(anual.shape[1]):
            valor = anual.values[i, j]
            eje.text(j, i, signo(valor), ha="center", va="center", fontsize=7.5,
                     color="white" if abs(valor) > 12 else "black")
    eje.set_xticks(range(len(ESCENARIOS)), list(ESCENARIOS.values()), fontsize=7.5)
    eje.set_yticks(range(len(metodos)), metodos, fontsize=8)
    eje.xaxis.tick_top()
    fig.colorbar(imagen, ax=eje, label="cambio anual (%)", shrink=0.85)
    fig.tight_layout()
    salida = CARPETA_PRODUCTOS / "sensibilidad_metodos.png"
    fig.savefig(salida, dpi=200)
    plt.close(fig)
    print(f"Listo: {salida}")


def figura_et_real():
    frente = pd.read_csv(CARPETA_PRODUCTOS / "et_productos_vs_balance.csv")
    central = pd.read_csv(CARPETA_PRODUCTOS / "et_incertidumbre.csv").query("caso_sigma_Q == 'central'").iloc[0]
    techo = pd.read_csv(CARPETA_PRODUCTOS / "et_techo_energia_resumen.csv").set_index("camino")
    et, sigma = central["ETR_Pm"], central["sigma_ET"]
    fig, eje = plt.subplots(figsize=(6.5, 5.4))
    x = range(len(frente))
    eje.axhspan(et - sigma, et + sigma, color="0.85", label="P̄ − Q ± σ_ET (95 %)")
    eje.axhline(et, color="black", lw=2, label=f"P̄ − Q = {miles(et)} mm/año")
    eje.axhline(central["ETR_PL"], color="#0072B2", ls="--", lw=1, label="P − Q con PL")
    eje.axhline(central["ETR_PI"], color="#E69F00", ls="--", lw=1, label="P − Q con PI")
    eje.axhline(techo.loc["balance con Pm", "ETo_mm_anio"], color="black", ls=":", lw=1.5, label="ETo Penman–Monteith (FAO-56)")
    eje.axhline(techo.loc["balance con Pm", "Rn_lambda_mm_anio"], color="#C8553D", lw=1.5, label="Rn/λ (ERA5-Land)")
    colores = ["#0072B2" if d else "#999999" for d in frente["dentro_de_sigma_ET_de_Pm"]]
    eje.bar(x, frente["producto_mm_anio"], color=colores, width=0.6, zorder=3)
    for i, v in enumerate(frente["producto_mm_anio"]):
        eje.text(i, v + 25, miles(v), ha="center", fontsize=8, zorder=4,
                 bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.9))
    eje.set_xticks(list(x), [" ".join(p.split(" ")[:-1]) + "\n" + p.split(" ")[-1] if " (" not in p
                            else p.replace(" (", "\n(") for p in frente["producto"]], fontsize=7.5)
    eje.set_ylabel("mm/año (meses comunes con Q)")
    eje.set_ylim(0, techo.loc["balance con Pm", "Rn_lambda_mm_anio"] * 1.12)
    eje.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False)
    eje.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    salida = CARPETA_PRODUCTOS / "et_real_productos.png"
    fig.savefig(salida, dpi=200)
    plt.close(fig)
    print(f"Listo: {salida}")


def tabla_et_real():
    frente = pd.read_csv(CARPETA_PRODUCTOS / "et_productos_vs_balance.csv")
    lineas = [
        "% Generado por codigo/punto1/35_figuras_tablas_informe.py; no se edita a mano.",
        "\\begin{tabular}{llrrrr}", "\\toprule",
        "Producto & Resolución & Meses & Producto & Balance $\\bar{P} - Q$ & ¿Dentro de \\\\",
        " & & con Q & (mm/año) & mismos meses (mm/año) & $\\pm\\sigma_\\mathrm{ET}$? \\\\", "\\midrule",
    ]
    for _, r in frente.iterrows():
        lineas.append(f"{r['producto']} & {r['resolucion'].replace('~', '$\\sim$')} & {r['meses_comunes_con_Q']} & "
                      f"{miles_tex(r['producto_mm_anio'])} & {miles_tex(r['balance_Pm_mm_anio'])} "
                      f"({signo_tex(r['dif_vs_Pm_pct'], 0)}~\\%) & {'sí' if r['dentro_de_sigma_ET_de_Pm'] else 'no'} \\\\")
    lineas += ["\\bottomrule", "\\end{tabular}"]
    escribir_tabla("tabla_et_productos.tex", lineas)


def tabla_budyko():
    b = pd.read_csv(CARPETA_PRODUCTOS / "budyko_resumen.csv")
    etiquetas = {
        "P − Q (P̄)": "$\\bar{P} - Q$ & \\ETo{} \\PM{}",
        "P − Q (P̄), ETP = Rn/λ": "$\\bar{P} - Q$ & $R_n/\\lambda$",
        "P − Q (P̄), ETP = Priestley–Taylor": "$\\bar{P} - Q$ & Priestley--Taylor",
        "mediana de productos, P = P̄": "mediana de productos & \\ETo{} \\PM{}",
    }
    assert set(b["serie"]) == set(etiquetas), "budyko_resumen.csv cambió de series"
    lineas = [
        "% Generado por codigo/punto1/35_figuras_tablas_informe.py; no se edita a mano.",
        "\\begin{tabular}{llrrrrr}", "\\toprule",
        "ET & ETP & $\\varphi$ & $\\varepsilon$ & $\\omega$ de Fu & \\multicolumn{2}{c}{Elasticidad de Q a P} \\\\",
        "\\cmidrule(lr){6-7}", " & & & & & teórica & empírica \\\\", "\\midrule",
    ]
    for _, r in b.iterrows():
        lineas.append(f"{etiquetas[r['serie']]} & {r['phi']:.2f} & {r['epsilon']:.2f} & {r['omega_fu']:.2f} & "
                      f"{r['elasticidad_teorica']:.2f} & {r['elasticidad_empirica_sankarasubramanian']:.2f} \\\\")
    lineas += ["\\bottomrule", "\\end{tabular}"]
    escribir_tabla("tabla_budyko.tex", lineas)


def cifras_texto(anual):
    """Cifras que usan los textos del informe redactados con IA (introducción y metodología), como macros de LaTeX.

    Los textos de Juan conservan sus propias cifras; estas macros evitan copiar números a mano en lo demás.
    """
    central = pd.read_csv(CARPETA_PRODUCTOS / "et_incertidumbre.csv").query("caso_sigma_Q == 'central'").iloc[0]
    techo = pd.read_csv(CARPETA_PRODUCTOS / "et_techo_energia_resumen.csv").set_index("camino")
    budyko = pd.read_csv(CARPETA_PRODUCTOS / "budyko_resumen.csv").set_index("serie").loc["P − Q (P̄)"]
    regimen = pd.read_csv(CARPETA_PRODUCTOS / "regimen_mensual.csv")
    meses_agua = regimen.loc[regimen["phi_Pm"] > 1, "mes"].tolist()
    assert meses_agua == [1], "el texto dice que solo enero tiene φ > 1 en el ciclo medio"
    cifras = {
        "cifraPm": miles_tex(central["P_media"]), "cifraPI": miles_tex(central["P_PI"]),
        "cifraPL": miles_tex(central["P_PL"]), "cifraQ": miles_tex(central["Q"]),
        "cifraETbalance": miles_tex(central["ETR_Pm"]), "cifraSigmaET": miles_tex(central["sigma_ET"]),
        "cifraETo": miles_tex(anual[PM]), "cifraRnLambda": miles_tex(techo.loc["balance con Pm", "Rn_lambda_mm_anio"]),
        "cifraPhi": f"{budyko['phi']:.2f}", "cifraEpsilon": f"{budyko['epsilon']:.2f}",
        "cifraQsobreP": f"{central['Q'] / central['P_media']:.2f}",
    }
    lineas = ["% Generado por codigo/punto1/35_figuras_tablas_informe.py; no se edita a mano.",
              "% Medias anuales 1998–2022 (mm/año) de la cuenca del Fonce en San Gil; P, Q y ET en los 262 meses con Q."]
    lineas += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in cifras.items()]
    escribir_tabla("cifras.tex", lineas)


def escribir_tabla(nombre, lineas):
    CARPETA_TABLAS.mkdir(exist_ok=True)
    salida = CARPETA_TABLAS / nombre
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Listo: {salida}")


def main():
    anual = anual_por_metodo()
    figura_metodos(anual)
    tabla_metodos(anual)
    figura_sensibilidad()
    figura_et_real()
    tabla_et_real()
    tabla_budyko()
    cifras_texto(anual)


if __name__ == "__main__":
    main()
