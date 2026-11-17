"""Un día de la ETo de FAO-56 resuelto paso a paso en una hoja de cálculo, para verificarlo a mano (punto 1).

Escribe anexos/punto1/dia_verificado_a_mano.xlsx con dos hojas:
    horas     las 24 horas del día local tal como vienen en datos/punto1/era5land_puntos/punto_N.csv (K, Pa, m/s, J/m²)
              y, con fórmulas de Excel, su paso a °C, kPa, rapidez del viento y e°(Td)
    calculo   cada paso de Rn (ec. 21–40) y de la ETo (ec. 6) como fórmula de Excel que apunta a las celdas
              anteriores, con su ecuación de FAO-56, el valor que dio el script (productos/punto1/) y la diferencia

Las fórmulas quedan vivas: quien revise puede cambiar una entrada y ver cómo se mueve la ETo. Ninguna cifra de la
hoja se escribe a mano: las entradas son los datos crudos y las comparaciones salen de los productos.

Además, el script repite aquí el cálculo con la librería math (sin pandas ni las funciones de 03 y 04) y comprueba
que coincide con los productos; si no coincide, se detiene. Así la hoja y el cálculo independiente se respaldan.

Día y punto elegidos: 2010-02-15 en el punto 6 (el de mayor peso, 0.252). Es un día de temporada seca;
cualquier otro sirve cambiando DIA y PUNTO.

La única entrada que no sale del día es la altura del modelo z (ec. 37), que 03_series_diarias_rn.py despeja de la
presión media de los 25 años; aquí se recalcula con la misma fórmula y se escribe como entrada.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/04c_dia_verificado_a_mano.py
"""

import math
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"
DIARIA_SCRIPT = RAIZ_ENTREGA / "productos" / "punto1" / "era5land_diario_puntos.csv"
ETO_SCRIPT = RAIZ_ENTREGA / "productos" / "punto1" / "eto_diaria_puntos.csv"
SALIDA = RAIZ_ENTREGA / "anexos" / "punto1" / "dia_verificado_a_mano.xlsx"

DIA = "2010-02-15"
PUNTO = 6
DESFASE_HORA_LOCAL = pd.Timedelta(hours=-5)  # Colombia, UTC−5
TOLERANCIA_RELATIVA = 1e-3                   # los productos se guardan con 4 decimales


def leer_dia():
    """Las 24 horas del día local en el punto, sin transformar, y la presión media de todo el período."""
    horaria = pd.read_csv(CARPETA_DATOS / f"punto_{PUNTO}.csv", parse_dates=["valid_time"])
    horaria["hora_local"] = horaria["valid_time"] + DESFASE_HORA_LOCAL
    inicio = pd.Timestamp(DIA)
    del_dia = horaria[(horaria["hora_local"] >= inicio) & (horaria["hora_local"] < inicio + pd.Timedelta(days=1))]
    if len(del_dia) != 24:
        raise ValueError(f"El {DIA} tiene {len(del_dia)} horas en el punto {PUNTO}; se necesitan 24.")
    # Presión media del período 1998-01-01 00:00 a 2022-12-31 23:00 local, como en 03_series_diarias_rn.py.
    periodo = horaria[(horaria["hora_local"] >= "1998-01-01") & (horaria["hora_local"] <= "2022-12-31 23:00")]
    return del_dia.reset_index(drop=True), periodo["sp"].mean() / 1000


def calculo_independiente(del_dia, p_media_kpa):
    """El mismo día con math, paso a paso; devuelve los valores intermedios con el nombre de los productos."""
    e_sat = lambda t: 0.6108 * math.exp(17.27 * t / (t + 237.3))         # ec. 11
    t = [k - 273.15 for k in del_dia["t2m"]]
    tmax, tmin = max(t), min(t)
    ea = sum(e_sat(k - 273.15) for k in del_dia["d2m"]) / 24
    p = sum(del_dia["sp"]) / 24 / 1000
    viento10 = sum(math.hypot(u, v) for u, v in zip(del_dia["u10"], del_dia["v10"])) / 24
    rs = sum(del_dia["ssrd"]) / 1e6

    latitud = math.radians(float(del_dia["latitude"].iloc[0]))
    j = pd.Timestamp(DIA).day_of_year
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * j)                       # ec. 23
    decl = 0.409 * math.sin(2 * math.pi / 365 * j - 1.39)                   # ec. 24
    ws = math.acos(-math.tan(latitud) * math.tan(decl))                     # ec. 25
    ra = 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(latitud) * math.sin(decl)
                                            + math.cos(latitud) * math.cos(decl) * math.sin(ws))  # ec. 21
    z = (293 - 293 * (p_media_kpa / 101.3) ** (1 / 5.26)) / 0.0065          # ec. 7 despejada
    rso = (0.75 + 2e-5 * z) * ra                                            # ec. 37
    rns = 0.77 * rs                                                         # ec. 38
    rnl = (4.903e-9 * ((tmax + 273.15) ** 4 + (tmin + 273.15) ** 4) / 2
           * (0.34 - 0.14 * math.sqrt(ea)) * (1.35 * min(rs / rso, 1) - 0.35))  # ec. 39
    rn = rns - rnl                                                          # ec. 40

    tm = (tmax + tmin) / 2                                                  # ec. 9
    delta = 4098 * e_sat(tm) / (tm + 237.3) ** 2                            # ec. 13
    es = (e_sat(tmax) + e_sat(tmin)) / 2                                    # ec. 12
    gamma = 0.665e-3 * p                                                    # ec. 8
    u2 = viento10 * 4.87 / math.log(67.8 * 10 - 5.42)                       # ec. 47
    eto = (0.408 * delta * rn + gamma * 900 / (tm + 273) * u2 * max(es - ea, 0)) / (delta + gamma * (1 + 0.34 * u2))
    return {"tmax_C": tmax, "tmin_C": tmin, "ea_kPa": ea, "sp_kPa": p, "viento10_ms": viento10, "rs_MJm2": rs,
            "ra_MJm2": ra, "rso_MJm2": rso, "rns_MJm2": rns, "rnl_MJm2": rnl, "rn_MJm2": rn,
            "t_C": tm, "es_kPa": es, "u2_ms": u2, "eto_mm": eto}


def valores_del_script():
    diaria = pd.read_csv(DIARIA_SCRIPT)
    eto = pd.read_csv(ETO_SCRIPT)
    fila_diaria = diaria[(diaria["fecha"] == DIA) & (diaria["punto"] == PUNTO)].iloc[0]
    fila_eto = eto[(eto["fecha"] == DIA) & (eto["punto"] == PUNTO)].iloc[0]
    return {**fila_diaria.to_dict(), **fila_eto.to_dict()}


def hoja_horas(libro, del_dia):
    hoja = libro.active
    hoja.title = "horas"
    encabezado = ["hora local", "valid_time (UTC)", "t2m (K)", "d2m (K)", "sp (Pa)", "u10 (m/s)", "v10 (m/s)",
                  "ssrd (J/m²)", "T (°C)", "Td (°C)", "e°(Td) (kPa) ec. 11", "P (kPa)", "rapidez 10 m (m/s)"]
    hoja.append(encabezado)
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for i, fila in del_dia.iterrows():
        r = i + 2
        hoja.append([fila["hora_local"].strftime("%Y-%m-%d %H:%M"), fila["valid_time"].strftime("%Y-%m-%d %H:%M"),
                     float(fila["t2m"]), float(fila["d2m"]), float(fila["sp"]), float(fila["u10"]),
                     float(fila["v10"]), float(fila["ssrd"]),
                     f"=C{r}-273.15", f"=D{r}-273.15", f"=0.6108*EXP(17.27*J{r}/(J{r}+237.3))", f"=E{r}/1000",
                     f"=SQRT(F{r}^2+G{r}^2)"])
    for columna, ancho in zip("ABCDEFGHIJKLM", [17, 17, 11, 11, 11, 11, 11, 13, 9, 9, 18, 10, 18]):
        hoja.column_dimensions[columna].width = ancho


def hoja_calculo(libro, del_dia, p_media_kpa, script):
    hoja = libro.create_sheet("calculo")
    hoja.append(["Paso", "Símbolo", "Valor (fórmula)", "Unidades", "FAO-56", "Valor del script", "Diferencia",
                 "Fuente del valor del script"])
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    pasos = [
        # (paso, símbolo, fórmula, unidades, ecuación, columna del producto)
        ("Día local y punto", "día", f"{DIA} · punto {PUNTO}", "", "", None),
        ("Latitud de la celda", "lat", float(del_dia["latitude"].iloc[0]), "°", "", None),
        ("Día juliano", "J", pd.Timestamp(DIA).day_of_year, "", "", None),
        ("Presión media 1998–2022 en el punto", "P media", p_media_kpa, "kPa", "dato (03_series_diarias_rn.py)", None),
        ("Altura del modelo", "z", "=(293-293*(C5/101.3)^(1/5.26))/0.0065", "m", "ec. 7 despejada", None),
        ("Temperatura máxima", "Tmax", "=MAX(horas!I2:I25)", "°C", "", "tmax_C"),
        ("Temperatura mínima", "Tmin", "=MIN(horas!I2:I25)", "°C", "", "tmin_C"),
        ("Presión real de vapor", "ea", "=AVERAGE(horas!K2:K25)", "kPa", "ec. 14 con Td horaria", "ea_kPa"),
        ("Presión del día", "P", "=AVERAGE(horas!L2:L25)", "kPa", "", "sp_kPa"),
        ("Rapidez del viento a 10 m", "u10", "=AVERAGE(horas!M2:M25)", "m/s", "", "viento10_ms"),
        ("Radiación solar", "Rs", "=SUM(horas!H2:H25)/1000000", "MJ/m²·día", "", "rs_MJm2"),
        ("Latitud en radianes", "φ", "=RADIANS(C3)", "rad", "ec. 22", None),
        ("Distancia inversa Tierra–Sol", "dr", "=1+0.033*COS(2*PI()/365*C4)", "", "ec. 23", None),
        ("Declinación solar", "δ", "=0.409*SIN(2*PI()/365*C4-1.39)", "rad", "ec. 24", None),
        ("Ángulo horario de la puesta del sol", "ωs", "=ACOS(-TAN(C13)*TAN(C15))", "rad", "ec. 25", None),
        ("Radiación extraterrestre", "Ra",
         "=24*60/PI()*0.082*C14*(C16*SIN(C13)*SIN(C15)+COS(C13)*COS(C15)*SIN(C16))", "MJ/m²·día", "ec. 21",
         "ra_MJm2"),
        ("Radiación de cielo despejado", "Rso", "=(0.75+0.00002*C6)*C17", "MJ/m²·día", "ec. 37", "rso_MJm2"),
        ("Onda corta neta (α = 0.23)", "Rns", "=(1-0.23)*C12", "MJ/m²·día", "ec. 38", "rns_MJm2"),
        ("Cociente Rs/Rso (máximo 1)", "Rs/Rso", "=MIN(C12/C18,1)", "", "nota de la ec. 39", None),
        ("Onda larga neta", "Rnl",
         "=0.000000004903*((C7+273.15)^4+(C8+273.15)^4)/2*(0.34-0.14*SQRT(C9))*(1.35*C20-0.35)", "MJ/m²·día",
         "ec. 39", "rnl_MJm2"),
        ("Radiación neta", "Rn", "=C19-C21", "MJ/m²·día", "ec. 40", "rn_MJm2"),
        ("Temperatura media", "T", "=(C7+C8)/2", "°C", "ec. 9", "t_C"),
        ("Pendiente de la curva de saturación", "Δ",
         "=4098*0.6108*EXP(17.27*C23/(C23+237.3))/(C23+237.3)^2", "kPa/°C", "ec. 13", None),
        ("Presión de saturación media", "es",
         "=(0.6108*EXP(17.27*C7/(C7+237.3))+0.6108*EXP(17.27*C8/(C8+237.3)))/2", "kPa", "ec. 11 y 12", "es_kPa"),
        ("Déficit de presión de vapor", "es − ea", "=MAX(C25-C9,0)", "kPa", "", "deficit_kPa"),
        ("Constante psicrométrica", "γ", "=0.000665*C10", "kPa/°C", "ec. 8", None),
        ("Factor de 10 a 2 m (control: 0.748)", "4.87/ln(67.8·10 − 5.42)", "=4.87/LN(67.8*10-5.42)", "",
         "ec. 47", None),
        ("Viento a 2 m", "u2", "=C11*C28", "m/s", "ec. 47", "u2_ms"),
        ("Término radiativo", "0.408 Δ (Rn − G), G = 0", "=0.408*C24*(C22-0)", "", "ec. 6, ec. 42", None),
        ("Término aerodinámico", "γ 900/(T+273) u2 (es − ea)", "=C27*900/(C23+273)*C29*C26", "", "ec. 6", None),
        ("Denominador", "Δ + γ (1 + 0.34 u2)", "=C24+C27*(1+0.34*C29)", "", "ec. 6", None),
        ("ETo, parte radiativa", "", "=C30/C32", "mm/día", "ec. 6", "eto_radiativa_mm"),
        ("ETo, parte aerodinámica", "", "=C31/C32", "mm/día", "ec. 6", "eto_aerodinamica_mm"),
        ("ETo (control: entre 1 y 9 mm/día)", "ETo", "=C33+C34", "mm/día", "ec. 6", "eto_mm"),
    ]
    for i, (paso, simbolo, formula, unidades, ecuacion, producto) in enumerate(pasos):
        r = i + 2
        if producto is None:
            hoja.append([paso, simbolo, formula, unidades, ecuacion])
        else:
            fuente = "eto_diaria_puntos.csv" if producto.startswith(("eto", "t_C", "es_", "deficit", "u2")) \
                else "era5land_diario_puntos.csv"
            hoja.append([paso, simbolo, formula, unidades, ecuacion, float(script[producto]), f"=C{r}-F{r}",
                         f"productos/punto1/{fuente}, columna {producto}"])
    for columna, ancho in zip("ABCDEFGH", [38, 26, 16, 11, 26, 16, 12, 58]):
        hoja.column_dimensions[columna].width = ancho
    hoja["C35"].font = Font(bold=True)


def main():
    del_dia, p_media_kpa = leer_dia()
    independiente = calculo_independiente(del_dia, p_media_kpa)
    script = valores_del_script()

    print(f"Día {DIA}, punto {PUNTO}: cálculo independiente frente a los productos")
    for nombre, valor in independiente.items():
        referencia = float(script[nombre])
        print(f"  {nombre:12s} independiente {valor:10.4f}   script {referencia:10.4f}")
        if not math.isclose(valor, referencia, rel_tol=TOLERANCIA_RELATIVA, abs_tol=1e-4):
            raise AssertionError(f"{nombre} no coincide: {valor} frente a {referencia}")
    assert 1 <= independiente["eto_mm"] <= 9, "ETo fuera del rango de control de 1 a 9 mm/día"

    libro = Workbook()
    hoja_horas(libro, del_dia)
    hoja_calculo(libro, del_dia, p_media_kpa, script)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    libro.save(SALIDA)
    print(f"Listo: {SALIDA}")


if __name__ == "__main__":
    main()
