"""Fase 8 (punto 1): ¿se puede salvar la evaporación de tanque de Mogotes-AUT (24025090, DHIME)?

Es el único registro de tanque en la zona (parámetro «Evaporación total diaria», unidad «mm», nivel Preliminar,
2009-11-19 a 2022-12-31). Se revisa por tramos:
    - fracción de días en 0 (un tanque no evapora 0 mm en un día de 3 mm de ETo: un 0 se lee como dato ausente);
    - media de los días con dato > 0, frente a la ETo de la celda de ERA5-Land de Mogotes (script 20) los mismos días;
    - razón media tanque/ETo, que sería el factor de unidades si la serie fuera evaporación × constante;
    - coeficiente de tanque implícito Kp = ETo / (tanque / factor) con factor 100 (centésimas de mm) — FAO-56
      (cuadro 5) da Kp de 0.35 a 0.85 para tanque clase A;
    - correlación diaria y mensual con la ETo.
Escribe productos/punto1/tanque_mogotes_diagnostico.csv.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/33_tanque_mogotes.py
"""

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
ZIP_DHIME = RAIZ_ENTREGA / "datos" / "punto1" / "ideam_estaciones" / "dhime_hr_viento_tanque_parte2_1998_2022.zip"
ENTRADA_ETO = RAIZ_ENTREGA / "productos" / "punto1" / "eto_diaria_celdas_estaciones.csv"
SALIDA = RAIZ_ENTREGA / "productos" / "punto1" / "tanque_mogotes_diagnostico.csv"
ESTACION_CELDA = 24025040        # Mogotes-AUT (24025090) tiene las mismas coordenadas que 24025040
FACTOR_PRUEBA = 100              # hipótesis: centésimas de mm
TRAMOS = {"2009-11 a 2010": ("2009-11-01", "2010-12-31"), "2011": ("2011-01-01", "2011-12-31"),
          "2012 a 2018-08": ("2012-01-01", "2018-08-31"), "2018-09 a 2021": ("2018-09-01", "2021-12-31"),
          "2022": ("2022-01-01", "2022-12-31")}
# 2018-09: primer valor por encima del máximo de 2012–2017 (cambio de nivel visible en la serie).


def leer_tanque():
    with zipfile.ZipFile(ZIP_DHIME) as z, z.open("descargaDhime.csv") as f:
        d = pd.read_csv(f, sep=None, engine="python")
    t = d[d["Parametro"] == "Evaporación total diaria"].copy()
    assert set(t["CodigoEstacion"]) == {24025090} and set(t["Unidad"]) == {"mm"}
    t["Fecha"] = pd.to_datetime(t["Fecha"])
    return t.set_index("Fecha")["Valor"]


def main():
    tanque = leer_tanque()
    eto = pd.read_csv(ENTRADA_ETO, parse_dates=["fecha"])
    eto = eto[eto["estacion"] == ESTACION_CELDA].set_index("fecha")["eto_mm"]
    filas = []
    for nombre, (ini, fin) in TRAMOS.items():
        s = tanque[ini:fin]
        con_dato = s[s > 0]
        par = pd.DataFrame({"tanque": con_dato, "eto": eto}).dropna()
        fila = {"tramo": nombre, "dias": len(s), "fraccion_dias_en_0": float((s == 0).mean()),
                "dias_con_dato": len(con_dato), "maximo": float(s.max())}
        if len(par) > 10:
            mensual = par.resample("MS").mean().dropna()
            razon = par["tanque"].mean() / par["eto"].mean()
            fila.update(media_tanque=par["tanque"].mean(), media_eto_mm_d=par["eto"].mean(), razon_tanque_eto=razon,
                        kp_implicito_factor_100=FACTOR_PRUEBA / razon,
                        r_diaria=par.corr().iloc[0, 1], r_mensual=mensual.corr().iloc[0, 1], meses=len(mensual))
        filas.append(fila)
    tabla = pd.DataFrame(filas)
    tabla.round(3).to_csv(SALIDA, index=False)
    print(tabla.round(2).to_string())
    print(f"Listo: {SALIDA}")


if __name__ == "__main__":
    main()
