"""Fase 5 (punto 1): α* = ETo/Eeq por mes, junto al déficit de vapor y al viento.

Evaporación de equilibrio (notas del curso, sección 6: https://carlosdhoyos.github.io/cursos/hidrologia/evapotranspiracion.html;
Priestley y Taylor 1972, doi:10.1175/1520-0493(1972)100<0081:OTAOSH>2.3.CO;2):

    Eeq = Δ/(Δ + γ) · (Rn − G)/λ          mm/día, G = 0 en paso diario (FAO-56 ec. 42), λ = 2.45 MJ/kg

con los mismos Δ, γ y Rn de la ETo. Es igual a Priestley–Taylor / 1.26, así que se toma de metodos_diaria_puntos.csv
(script 21) dividiendo por α = 1.26.

Pasos:
    1. Eeq, ETo Penman–Monteith (FAO-56) y Penman–Monteith con rs = 0 diarios en cada punto.
    2. Suma por mes en cada punto; déficit (es − ea) y u2 como media del mes.
    3. Cuenca = promedio ponderado por el área de Voronoi (pesos de 04_eto_fao56.py).
    4. α* = ETo/Eeq y α(rs = 0) = ETo(rs = 0)/Eeq de cada mes, con los totales mensuales (no el promedio de cocientes
       diarios). Ciclo anual: cociente de las medias de los 25 años por mes calendario.

Escribe:
    productos/punto1/alfa_implicito_mensual.csv   cada mes 1998–2022: Eeq, ETo, ETo rs = 0, α*, α(rs = 0), déficit, u2
    productos/punto1/alfa_implicito_ciclo.csv     por mes calendario, lo mismo, más el mínimo y el máximo de α* entre años
    productos/punto1/alfa_implicito.png
Además imprime α* de febrero de 2010 en el punto 6, el mes de anexos/punto1/metodos_mes_a_mano.xlsx, para verificarlo
a mano.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/27_alfa_implicito.py
"""

import importlib.util
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_METODOS = CARPETA_PRODUCTOS / "metodos_diaria_puntos.csv"
ENTRADA_ETO = CARPETA_PRODUCTOS / "eto_diaria_puntos.csv"
ENTRADA_ETO_CUENCA = CARPETA_PRODUCTOS / "eto_mensual_cuenca.csv"
SALIDA_MENSUAL = CARPETA_PRODUCTOS / "alfa_implicito_mensual.csv"
SALIDA_CICLO = CARPETA_PRODUCTOS / "alfa_implicito_ciclo.csv"
SALIDA_PNG = CARPETA_PRODUCTOS / "alfa_implicito.png"
ALFA_PT = 1.26
MESES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
PUNTO_MANO, MES_MANO = 6, "2010-02"

_spec = importlib.util.spec_from_file_location("eto_fao56", Path(__file__).with_name("04_eto_fao56.py"))
eto_fao56 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eto_fao56)
PESOS = eto_fao56.PESOS


def main():
    metodos = pd.read_csv(ENTRADA_METODOS, parse_dates=["fecha"])
    eto = pd.read_csv(ENTRADA_ETO, parse_dates=["fecha"])
    diaria = metodos[["fecha", "punto", "priestley_taylor", "eto_fao56_rs0"]].merge(
        eto[["fecha", "punto", "eto_mm", "deficit_kPa", "u2_ms"]], on=["fecha", "punto"], validate="one_to_one")
    diaria["eeq"] = diaria["priestley_taylor"] / ALFA_PT
    diaria["mes"] = diaria["fecha"].dt.strftime("%Y-%m")

    por_punto = diaria.groupby(["punto", "mes"]).agg(
        eeq=("eeq", "sum"), eto=("eto_mm", "sum"), eto_rs0=("eto_fao56_rs0", "sum"),
        deficit=("deficit_kPa", "mean"), u2=("u2_ms", "mean")).reset_index()
    peso = por_punto["punto"].map(PESOS)
    columnas = ["eeq", "eto", "eto_rs0", "deficit", "u2"]
    cuenca = (por_punto[columnas].mul(peso, axis=0).groupby(por_punto["mes"]).sum()
              .div(peso.groupby(por_punto["mes"]).sum(), axis=0))
    assert len(cuenca) == 300

    # La ETo de cuenca debe coincidir con la del script 04.
    ref = pd.read_csv(ENTRADA_ETO_CUENCA).set_index("mes")["eto_mm_mes"]
    error = (cuenca["eto"] - ref.reindex(cuenca.index)).abs().max()
    assert error < 0.01, f"la ETo de cuenca no coincide con el script 04 (máx. {error:.4f} mm/mes)"

    cuenca["alfa_estrella"] = cuenca["eto"] / cuenca["eeq"]
    cuenca["alfa_rs0"] = cuenca["eto_rs0"] / cuenca["eeq"]
    salida = cuenca.rename(columns={"eeq": "eeq_mm_mes", "eto": "eto_mm_mes", "eto_rs0": "eto_rs0_mm_mes",
                                    "deficit": "deficit_kPa", "u2": "u2_ms"})
    salida.round(4).to_csv(SALIDA_MENSUAL)
    print(f"Listo: {SALIDA_MENSUAL}")

    cuenca["mes_calendario"] = cuenca.index.str[5:7].astype(int)
    g = cuenca.groupby("mes_calendario")
    ciclo = g[["eeq", "eto", "eto_rs0", "deficit", "u2"]].mean()
    ciclo["alfa_estrella"] = ciclo["eto"] / ciclo["eeq"]
    ciclo["alfa_rs0"] = ciclo["eto_rs0"] / ciclo["eeq"]
    ciclo["alfa_estrella_min"] = g["alfa_estrella"].min()
    ciclo["alfa_estrella_max"] = g["alfa_estrella"].max()
    ciclo = ciclo.rename(columns={"eeq": "eeq_mm_mes", "eto": "eto_mm_mes", "eto_rs0": "eto_rs0_mm_mes",
                                  "deficit": "deficit_kPa", "u2": "u2_ms"})
    ciclo.round(4).to_csv(SALIDA_CICLO)
    print(f"Listo: {SALIDA_CICLO}")
    print(ciclo[["eeq_mm_mes", "eto_mm_mes", "alfa_estrella", "alfa_rs0", "alfa_estrella_min", "alfa_estrella_max",
                 "deficit_kPa", "u2_ms"]].round(3).to_string())
    anual = cuenca[["eeq", "eto", "eto_rs0"]].mean() * 12
    print(f"Anual: Eeq {anual['eeq']:.0f}, ETo {anual['eto']:.0f}, ETo rs = 0 {anual['eto_rs0']:.0f} mm/año; "
          f"α* {anual['eto'] / anual['eeq']:.3f}, α(rs = 0) {anual['eto_rs0'] / anual['eeq']:.3f}")

    mano = por_punto[(por_punto["punto"] == PUNTO_MANO) & (por_punto["mes"] == MES_MANO)].iloc[0]
    print(f"Para verificar a mano (punto {PUNTO_MANO}, {MES_MANO}, hoja metodos_mes_a_mano.xlsx): "
          f"Eeq {mano['eeq']:.3f}, ETo {mano['eto']:.3f} mm/mes, α* {mano['eto'] / mano['eeq']:.4f}")

    fig, eje = plt.subplots(figsize=(6.5, 4.6))
    x = list(range(1, 13))
    eje.fill_between(x, ciclo["alfa_estrella_min"], ciclo["alfa_estrella_max"], color="#0072B2", alpha=0.15,
                     label="α* mín.–máx. entre años")
    eje.plot(x, ciclo["alfa_estrella"], "o-", color="#0072B2", label="α* = ETo/Eeq")
    eje.plot(x, ciclo["alfa_rs0"], "s--", color="#009E73", label="ETo(rs = 0)/Eeq")
    eje.axhline(ALFA_PT, color="#E69F00", ls=":", label="α de Priestley–Taylor (1.26)")
    eje.set_xticks(x, MESES)
    eje.set_ylabel("razón con Eeq")
    eje2 = eje.twinx()
    eje2.plot(x, ciclo["deficit_kPa"], color="#A65E1A", lw=1, label="déficit es − ea (kPa)")
    eje2.plot(x, ciclo["u2_ms"], color="#7C5BC7", lw=1, label="u2 (m/s)")
    eje2.set_ylabel("kPa  ·  m/s")
    lineas = eje.get_legend_handles_labels()
    lineas2 = eje2.get_legend_handles_labels()
    eje.legend(lineas[0] + lineas2[0], lineas[1] + lineas2[1], fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    eje.set_title("α* por mes, cuenca, media 1998–2022", fontsize=10)
    fig.tight_layout()
    fig.savefig(SALIDA_PNG, dpi=150)
    print(f"Listo: {SALIDA_PNG}")


if __name__ == "__main__":
    main()
