"""Fase 4 (punto 1): un mes de cada método resuelto con fórmulas en una hoja de cálculo, para verificarlo a mano.

El plan de la fase 4 pide verificar a mano un mes de cada método. Este script prepara la hoja; la verificación la hace
Juan.

Escribe anexos/punto1/metodos_mes_a_mano.xlsx con tres hojas:
    constantes     latitud y altura del punto, λ, α, c, constantes de Cenicafé y la altura del viento
    dias           un día por fila: las entradas de ERA5-Land del punto (Tmáx, Tmín, ea, presión, viento a 10 m,
                   Rs, Ra, Rn, salidas del script 03) y, como fórmulas de Excel, los pasos intermedios y cada método
                   en mm/día. Abajo, la suma del mes en la hoja, la del script 21 (o 04 para la ETo) y la diferencia.
    thornthwaite   el índice de calor I con los 12 meses de la climatología del punto, el exponente a, la T del mes,
                   la duración media del día (de la hoja dias) y la ETP del mes, frente al script 22.

Mes elegido: febrero de 2010 en el punto 6 (el mismo punto y mes del día resuelto en anexos/ecuaciones_metodos.md,
15 feb 2010). Se cambia con PUNTO y MES. Las sumas son del punto, no de la cuenca (la cuenca es el promedio Voronoi de
los 6 puntos, como la ETo).

El script repite cada fórmula en pandas y se detiene si no reproduce los scripts 04, 21 y 22.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/25_metodos_mes_a_mano.py
"""

import math
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
PUNTOS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"
SALIDA = RAIZ_ENTREGA / "anexos" / "punto1" / "metodos_mes_a_mano.xlsx"

PUNTO = 6
MES = "2010-02"
LAMBDA, ALFA_PT, C_PENMAN, CENICAFE, CENICAFE_EXP, Z_VIENTO = 2.45, 1.26, 0.8, 4.37, -0.0002, 10.0

# Hoja «constantes»: (nombre, valor o None si se llena con datos del punto, fuente). Fila = posición + 2.
CONSTANTES = [
    ("latitud del punto (°)", None, "anexos/punto1/elevacion_puntos_dem.csv"),
    ("h, altura del punto para Cenicafé (m)", None, "z_region_dem_m, misma tabla (script 21)"),
    ("λ (MJ/kg)", LAMBDA, "FAO-56 (0.408 = 1/2.45)"),
    ("α de Priestley–Taylor", ALFA_PT, "Priestley y Taylor (1972)"),
    ("c de Penman (FAO-24)", C_PENMAN, "FAO-24, p. 15; solo con tiempo en calma (Juan, 22 nov)"),
    ("Cenicafé, coeficiente (mm/día)", CENICAFE, "Jaramillo (2006), p. 292"),
    ("Cenicafé, exponente (1/m)", CENICAFE_EXP, "Jaramillo (2006), p. 292"),
    ("z del viento de ERA5-Land (m)", Z_VIENTO, "u10 de ERA5-Land"),
]
K = {n: f"constantes!$B${i + 2}" for i, (n, _, _) in enumerate(CONSTANTES)}
LAT, ALT, LAM, ALF, CPEN, CEN, CENX, ZV = K.values()

# Hoja «dias»: columna -> (encabezado, fórmula con {r} = fila; None si es dato). G = 0 en paso diario (FAO-56 ec. 42).
COLUMNAS = [
    ("A", "fecha", None), ("B", "J (día del año)", None),
    ("C", "Tmáx (°C)", None), ("D", "Tmín (°C)", None), ("E", "ea (kPa)", None), ("F", "presión (kPa)", None),
    ("G", "viento a 10 m (m/s)", None), ("H", "Rs (MJ/m²·día)", None), ("I", "Ra (MJ/m²·día)", None),
    ("J", "Rn (MJ/m²·día)", None),
    ("K", "T = (Tmáx+Tmín)/2, ec. 9", "=(C{r}+D{r})/2"),
    ("L", "e°(Tmáx), ec. 11", "=0.6108*EXP(17.27*C{r}/(C{r}+237.3))"),
    ("M", "e°(Tmín), ec. 11", "=0.6108*EXP(17.27*D{r}/(D{r}+237.3))"),
    ("N", "es, ec. 12 (kPa)", "=(L{r}+M{r})/2"),
    ("O", "es − ea (kPa, ≥ 0)", "=MAX(N{r}-E{r},0)"),
    ("P", "Δ, ec. 13 (kPa/°C)", "=4098*(0.6108*EXP(17.27*K{r}/(K{r}+237.3)))/(K{r}+237.3)^2"),
    ("Q", "γ, ec. 8 (kPa/°C)", "=0.000665*F{r}"),
    ("R", "u2, ec. 47 (m/s)", f"=G{{r}}*4.87/LN(67.8*{ZV}-5.42)"),
    ("S", "W = Δ/(Δ+γ)", "=P{r}/(P{r}+Q{r})"),
    ("T", "Hargreaves (mm/día)", "=0.0023*0.408*I{r}*(K{r}+17.8)*SQRT(MAX(C{r}-D{r},0))"),
    ("U", "Priestley–Taylor (mm/día)", f"={ALF}*S{{r}}*J{{r}}/{LAM}"),
    ("V", "Makkink (mm/día)", f"=0.61*S{{r}}*H{{r}}/{LAM}-0.12"),
    ("W", "f(u) FAO-24, U2 en km/día", "=0.27*(1+R{r}*86.4/100)"),
    ("X", "Penman con c = 1 (mm/día)", f"=S{{r}}*J{{r}}/{LAM}+(1-S{{r}})*W{{r}}*O{{r}}*10"),
    ("Y", "Penman FAO-24, c = 0.8 (mm/día)", f"={CPEN}*X{{r}}"),
    ("Z", "AA = 2·PT − Penman c = 1 (mm/día)", "=2*U{r}-X{r}"),
    ("AA", "Cenicafé 2006 (mm/día)", f"={CEN}*EXP({CENX}*{ALT})"),
    ("AB", "Penman–Monteith rs = 0 (mm/día)", "=(0.408*P{r}*J{r}+Q{r}*900/(K{r}+273)*R{r}*O{r})/(P{r}+Q{r})"),
    ("AC", "ETo Penman–Monteith FAO-56, ec. 6 (mm/día)",
     "=(0.408*P{r}*J{r}+Q{r}*900/(K{r}+273)*R{r}*O{r})/(P{r}+Q{r}*(1+0.34*R{r}))"),
    ("AD", "φ (rad)", f"=RADIANS({LAT})"),
    ("AE", "δ, ec. 24", "=0.409*SIN(2*PI()/365*B{r}-1.39)"),
    ("AF", "ωs, ec. 25", "=ACOS(-TAN(AD{r})*TAN(AE{r}))"),
    ("AG", "N, horas de luz, ec. 34 (para Thornthwaite)", "=24/PI()*AF{r}"),
]
# Método -> (columna de la hoja, columna del script, archivo del script)
METODOS = {
    "Hargreaves": ("T", "hargreaves", "21"), "Priestley–Taylor": ("U", "priestley_taylor", "21"),
    "Makkink": ("V", "makkink", "21"), "Penman FAO-24 (c = 0.8)": ("Y", "penman_fao24", "21"),
    "AA (Brutsaert–Stricker)": ("Z", "aa_brutsaert_stricker", "21"), "Cenicafé 2006": ("AA", "cenicafe_2006", "21"),
    "Penman–Monteith rs = 0": ("AB", "eto_fao56_rs0", "21"), "ETo Penman–Monteith (FAO-56)": ("AC", "eto_mm", "04"),
}


def metodos_pandas(d, lat, h):
    """Las mismas fórmulas de la hoja, en pandas, para comprobar la hoja contra los scripts."""
    t = (d["tmax_C"] + d["tmin_C"]) / 2
    e0 = lambda x: 0.6108 * (17.27 * x / (x + 237.3)).map(math.exp)  # noqa: E731
    deficit = ((e0(d["tmax_C"]) + e0(d["tmin_C"])) / 2 - d["ea_kPa"]).clip(lower=0)
    dlt = 4098 * e0(t) / (t + 237.3) ** 2
    gam = 0.000665 * d["sp_kPa"]
    u2 = d["viento10_ms"] * 4.87 / math.log(67.8 * Z_VIENTO - 5.42)
    w = dlt / (dlt + gam)
    rn = d["rn_MJm2"]
    pt = ALFA_PT * w * rn / LAMBDA
    pen1 = w * rn / LAMBDA + (1 - w) * 0.27 * (1 + u2 * 86.4 / 100) * deficit * 10
    num = 0.408 * dlt * rn + gam * 900 / (t + 273) * u2 * deficit
    return pd.DataFrame({
        "hargreaves": 0.0023 * 0.408 * d["ra_MJm2"] * (t + 17.8) * (d["tmax_C"] - d["tmin_C"]).clip(lower=0) ** 0.5,
        "priestley_taylor": pt, "makkink": 0.61 * w * d["rs_MJm2"] / LAMBDA - 0.12,
        "penman_fao24": C_PENMAN * pen1, "aa_brutsaert_stricker": 2 * pt - pen1,
        "cenicafe_2006": CENICAFE * math.exp(CENICAFE_EXP * h) + 0 * t,
        "eto_fao56_rs0": num / (dlt + gam), "eto_mm": num / (dlt + gam * (1 + 0.34 * u2)),
    })


def main():
    puntos = pd.read_csv(PUNTOS).set_index("punto")
    lat, h = float(puntos.loc[PUNTO, "lat"]), float(puntos.loc[PUNTO, "z_region_dem_m"])
    diaria = pd.read_csv(PRODUCTOS / "era5land_diario_puntos.csv", parse_dates=["fecha"])
    del_punto = diaria[diaria["punto"] == PUNTO]
    d = del_punto[del_punto["fecha"].dt.strftime("%Y-%m") == MES].reset_index(drop=True)
    script = (pd.read_csv(PRODUCTOS / "metodos_diaria_puntos.csv", parse_dates=["fecha"])
              .merge(pd.read_csv(PRODUCTOS / "eto_diaria_puntos.csv", parse_dates=["fecha"])[["fecha", "punto", "eto_mm"]],
                     on=["fecha", "punto"]))
    script = script[(script["punto"] == PUNTO) & (script["fecha"].dt.strftime("%Y-%m") == MES)].reset_index(drop=True)
    assert len(d) == len(script) > 0

    nuestra = metodos_pandas(d, lat, h)
    for _, (_, col, _) in METODOS.items():
        error = (nuestra[col] - script[col]).abs().max()
        assert error < 1e-3, f"{col}: la hoja no reproduce el script (máx. {error:.5f} mm/día)"

    # Thornthwaite: climatología de T del punto (25 años), I, a y el mes.
    tm = del_punto.assign(t=(del_punto["tmax_C"] + del_punto["tmin_C"]) / 2).set_index("fecha")["t"].resample("MS").mean()
    clima = tm.groupby(tm.index.month).mean()
    th = pd.read_csv(PRODUCTOS / "thornthwaite_mensual_puntos.csv")
    th = th[(th["punto"] == PUNTO) & (th["mes"] == MES)].iloc[0]

    libro = Workbook()
    negrita, resaltado = Font(bold=True), PatternFill("solid", fgColor="FFF2CC")
    hoja_c = libro.active
    hoja_c.title = "constantes"
    hoja_c.append(("constante", "valor", "fuente"))
    for nombre, valor, fuente in CONSTANTES:
        valor = {"latitud del punto (°)": lat, "h, altura del punto para Cenicafé (m)": h}.get(nombre, valor)
        hoja_c.append((nombre, valor, fuente))
    hoja_c.append(())
    hoja_c.append((f"Punto {PUNTO}, {MES}. Entradas: productos/punto1/era5land_diario_puntos.csv (script 03).",))
    for celda in hoja_c[1]:
        celda.font = negrita

    hoja = libro.create_sheet("dias")
    hoja.append([encabezado for _, encabezado, _ in COLUMNAS])
    for i, f in d.iterrows():
        r = i + 2
        datos = {"A": f["fecha"].strftime("%Y-%m-%d"), "B": int(f["fecha"].dayofyear), "C": f["tmax_C"],
                 "D": f["tmin_C"], "E": f["ea_kPa"], "F": f["sp_kPa"], "G": f["viento10_ms"], "H": f["rs_MJm2"],
                 "I": f["ra_MJm2"], "J": f["rn_MJm2"]}
        for col, _, formula in COLUMNAS:
            hoja[f"{col}{r}"] = formula.format(r=r) if formula else datos[col]
    ultima = len(d) + 1
    for celda in hoja[1]:
        celda.font = negrita

    # Resumen del mes debajo de los días.
    base = ultima + 2
    hoja[f"A{base}"] = "Suma del mes (mm/mes)"
    hoja[f"A{base}"].font = negrita
    for j, encabezado in enumerate(["método", "hoja", "script", "diferencia"]):
        hoja.cell(row=base + 1, column=1 + j, value=encabezado).font = negrita
    for k, (nombre, (col, col_script, num)) in enumerate(METODOS.items()):
        r = base + 2 + k
        hoja[f"A{r}"] = nombre
        hoja[f"B{r}"] = f"=SUM({col}2:{col}{ultima})"
        hoja[f"C{r}"] = round(float(script[col_script].sum()), 3)
        hoja[f"D{r}"] = f"=B{r}-C{r}"
        hoja[f"E{r}"] = f"script {num}"
        hoja[f"B{r}"].fill = resaltado
    hoja.freeze_panes = "C2"

    # Thornthwaite
    ht = libro.create_sheet("thornthwaite")
    ht.append(("mes calendario", f"T media 1998–2022 del punto {PUNTO} (°C)", "(T/5)^1.514"))
    for mes, t in clima.items():
        r = ht.max_row + 1
        ht.append((int(mes), round(float(t), 4), f"=(MAX(B{r},0)/5)^1.514"))
    filas = [
        ("I, índice de calor", "=SUM(C2:C13)", round(float(th["I"]), 3)),
        ("a = 6.75e-7 I³ − 7.71e-5 I² + 0.01792 I + 0.49239", "=6.75E-7*B15^3-7.71E-5*B15^2+0.01792*B15+0.49239",
         round(float(th["a"]), 4)),
        (f"T del mes {MES} (°C)", f"=AVERAGE(dias!K2:K{ultima})", round(float(th["t_C"]), 4)),
        ("ETP sin corregir = 16·(10·T/I)^a (mm/mes)", "=16*(10*B17/B15)^B16", round(float(th["etp_sin_corregir_mm"]), 3)),
        ("L, horas de luz media del mes", f"=AVERAGE(dias!AG2:AG{ultima})", round(float(th["L_h"]), 4)),
        ("N, días del mes", f"=COUNT(dias!B2:B{ultima})", int(th["N_dias"])),
        ("ETP Thornthwaite = sin corregir·(L/12)·(N/30) (mm/mes)", "=B18*(B19/12)*(B20/30)",
         round(float(th["etp_thornthwaite_mm"]), 3)),
    ]
    # Cabecera en la fila 14 y pasos en las filas 15 a 21 (las fórmulas usan esas filas).
    ht.cell(row=14, column=1, value="paso").font = negrita
    ht.cell(row=14, column=2, value="hoja").font = negrita
    ht.cell(row=14, column=3, value="script 22").font = negrita
    ht.cell(row=14, column=4, value="diferencia").font = negrita
    for k, (nombre, formula, valor) in enumerate(filas):
        r = 15 + k
        ht.cell(row=r, column=1, value=nombre)
        ht.cell(row=r, column=2, value=formula).fill = resaltado
        ht.cell(row=r, column=3, value=valor)
        ht.cell(row=r, column=4, value=f"=B{r}-C{r}")
    for celda in ht[1]:
        celda.font = negrita

    for h_ in libro.worksheets:
        for col in h_.columns:
            h_.column_dimensions[col[0].column_letter].width = 16
    hoja_c.column_dimensions["A"].width = 38
    hoja_c.column_dimensions["C"].width = 55
    ht.column_dimensions["A"].width = 55
    hoja.column_dimensions["A"].width = 30
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    libro.save(SALIDA)
    print(f"Listo: {SALIDA} (punto {PUNTO}, {MES}, {len(d)} días)")
    print("Suma del mes en pandas (mm/mes):")
    print(nuestra.sum().round(2).to_string())


if __name__ == "__main__":
    main()
