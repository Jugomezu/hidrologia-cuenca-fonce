"""Segunda prueba de la ETo (punto 1, fase 3): nuestra ETo FAO-56 frente a la pet de TerraClimate v1.1.

«Nuestra ETo» = la ETo FAO-56 de este trabajo (scripts 01–04), calculada con forzantes de 6 puntos de ERA5-Land.
No es un producto de ERA5-Land; ERA5-Land solo aporta las entradas.

Lee:
    productos/punto1/eto_mensual_cuenca.csv           ETo mensual de la cuenca (04_eto_fao56.py), mm/mes
    productos/punto1/terraclimate_mensual_cuenca.csv  pet mensual de la cuenca (05_descarga_terraclimate.py), mm/mes

Escribe en productos/punto1/:
    eto_vs_terraclimate_pet_por_mes.csv     por mes calendario: medias, sesgo, MAE, RMSE y correlación
    eto_vs_terraclimate_pet_resumen.csv     lo mismo con los 300 meses, y la media anual de cada una
    eto_vs_terraclimate_pet.png             serie mensual y ciclo anual

Qué es la pet de TerraClimate (atributos del archivo y https://www.climatologylab.org/terraclimate.html, 2026-11-19):
    «Reference Evapotranspiration», ASCE Penman-Monteith corregida por CO2 (Yang et al., 2019). En v1.1 sus entradas
    salen de anomalías mensuales de ERA5 sobre climatologías CHELSA 2.1 (1981–2010), con la presión de vapor corregida
    con CRU TS. Dos diferencias con nuestra ETo, que se declaran y no se corrigen:
      - la corrección por CO2 cambia la resistencia de la superficie de la ec. de FAO-56;
      - sus anomalías vienen de ERA5, de donde salen también nuestros forzantes (ERA5-Land), así que no es independiente en las anomalías; sí en la
        climatología (CHELSA y CRU) y en la resolución (~4 km frente a 6 puntos de 0.1°).

Sesgo = media de (nuestra ETo − pet TerraClimate); positivo es nuestra ETo por encima. MAE = media de
|diferencia|. RMSE = raíz de la media de la diferencia al cuadrado. Todo en mm/mes, 1998-01 a 2022-12 (300 meses; los
dos productos no tienen huecos). El promedio de cuenca de los dos es el de cada script: Voronoi de 6 puntos en la ETo,
área de cada celda dentro del polígono en TerraClimate.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/16_eto_vs_terraclimate_pet.py
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (va después de fijar el backend sin pantalla)

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ETO = PRODUCTOS / "eto_mensual_cuenca.csv"
TERRACLIMATE = PRODUCTOS / "terraclimate_mensual_cuenca.csv"
SALIDA_POR_MES = PRODUCTOS / "eto_vs_terraclimate_pet_por_mes.csv"
SALIDA_RESUMEN = PRODUCTOS / "eto_vs_terraclimate_pet_resumen.csv"
SALIDA_FIGURA = PRODUCTOS / "eto_vs_terraclimate_pet.png"
MESES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


def metricas(grupo):
    diferencia = grupo["eto_fao56"] - grupo["pet_terraclimate"]
    return pd.Series({
        "meses": len(grupo),
        "eto_fao56_media": grupo["eto_fao56"].mean(),
        "pet_terraclimate_media": grupo["pet_terraclimate"].mean(),
        "sesgo_mm_mes": diferencia.mean(),
        "sesgo_pct": 100 * diferencia.mean() / grupo["pet_terraclimate"].mean(),
        "mae_mm_mes": diferencia.abs().mean(),
        "rmse_mm_mes": np.sqrt((diferencia ** 2).mean()),
        "correlacion": grupo["eto_fao56"].corr(grupo["pet_terraclimate"]),
    })


def main():
    eto = pd.read_csv(ETO)[["mes", "eto_mm_mes"]].rename(columns={"eto_mm_mes": "eto_fao56"})
    pet = pd.read_csv(TERRACLIMATE)[["mes", "pet_mm_mes", "pet_fraccion_area_valida"]]
    datos = eto.merge(pet.rename(columns={"pet_mm_mes": "pet_terraclimate"}), on="mes", how="inner")
    assert len(datos) == 300 and datos.notna().all().all()
    assert (datos["pet_fraccion_area_valida"] == 1).all()
    datos["mes_calendario"] = pd.to_datetime(datos["mes"]).dt.month

    por_mes = datos.groupby("mes_calendario").apply(metricas, include_groups=False)
    resumen = metricas(datos).to_frame("todos_los_meses").T
    resumen["eto_fao56_anual_mm"] = datos["eto_fao56"].sum() / 25
    resumen["pet_terraclimate_anual_mm"] = datos["pet_terraclimate"].sum() / 25
    por_mes.round(3).to_csv(SALIDA_POR_MES)
    resumen.round(3).to_csv(SALIDA_RESUMEN)

    # Solo el ciclo anual: la serie mensual se quitó del informe (Juan, 26 nov).
    figura, der = plt.subplots(figsize=(6.5, 3.6))
    x = range(1, 13)
    der.plot(x, por_mes["eto_fao56_media"], "o-", color="#1B6A80", label="ETo FAO-56 (este trabajo)")
    der.plot(x, por_mes["pet_terraclimate_media"], "s--", color="#CC79A7", label="pet TerraClimate")
    der.set_xticks(list(x), MESES)
    der.set_ylabel("mm/mes")
    der.set_title("Ciclo anual de la cuenca (media por mes, 1998–2022)", fontsize=10)
    der.grid(alpha=0.3)
    der.legend(fontsize=8, loc="lower left")
    figura.tight_layout()
    figura.savefig(SALIDA_FIGURA, dpi=150)

    pd.set_option("display.width", 200)
    print(resumen.round(2).T.to_string())
    print(por_mes[["sesgo_mm_mes", "sesgo_pct", "mae_mm_mes", "rmse_mm_mes"]].round(2).to_string())
    for ruta in (SALIDA_POR_MES, SALIDA_RESUMEN, SALIDA_FIGURA):
        print(f"Listo: {ruta.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
