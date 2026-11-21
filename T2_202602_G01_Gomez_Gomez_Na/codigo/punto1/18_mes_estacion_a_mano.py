"""Un mes de la ETo de estación (prueba de la fase 3) resuelto con fórmulas en una hoja de cálculo, para verificarlo a mano.

El plan de la fase 3 pide verificar a mano un mes de la estación recalculado con FAO-56. Este script prepara la hoja;
la verificación la hace el grupo.

Escribe anexos/punto1/mes_estacion_a_mano.xlsx con dos hojas:
    constantes   latitud y altura de la estación, a_s, b_s, albedo, σ, Gsc y el u2 del mes (variante (a), Mogotes-AUT)
    dias         un día por fila: las entradas medidas (Tmáx, Tmín, HRmáx, HRmín, horas de brillo solar) y, como
                 fórmulas de Excel, cada paso de FAO-56 hasta la ETo (ec. 6), con la ETo del script 13 y la diferencia.
                 Abajo, la media del mes en la hoja, en el script y nuestra ETo del mismo mes en la celda de ERA5-Land de la estación (script 20).

Las entradas salen de productos/punto1/eto_estaciones_diaria.csv y rs_estaciones_diaria.csv (salidas de 12 y 13), y
la latitud y la altura del catálogo del IDEAM. El script repite el cálculo con la librería math y se detiene si no
coincide con el script 13.

Mes elegido: marzo de 2001 en Escuela Agrícola Mogotes (24025040), uno de los meses con los 31 días completos. Se
cambia con ESTACION y MES.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/18_mes_estacion_a_mano.py
"""

import math
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
CATALOGO_IDEAM = RAIZ_ENTREGA / "datos" / "punto1" / "ideam" / "cne_ideam.csv"
SALIDA = RAIZ_ENTREGA / "anexos" / "punto1" / "mes_estacion_a_mano.xlsx"

ESTACION = "24025040"
MES = "2001-03"
A_S, B_S, ALBEDO, SIGMA, GSC = 0.25, 0.50, 0.23, 4.903e-9, 0.0820

# columna -> (encabezado, fórmula con {r} = fila; None si es dato)
COLUMNAS = [
    ("A", "fecha", None), ("B", "J (día del año)", None), ("C", "Tmáx (°C)", None), ("D", "Tmín (°C)", None),
    ("E", "HRmáx (%)", None), ("F", "HRmín (%)", None), ("G", "n, brillo solar (h)", None),
    ("H", "u2 (m/s)", "=constantes!$B$8"),
    ("I", "φ (rad)", "=RADIANS(constantes!$B$2)"),
    ("J", "dr, ec. 23", "=1+0.033*COS(2*PI()/365*B{r})"),
    ("K", "δ, ec. 24", "=0.409*SIN(2*PI()/365*B{r}-1.39)"),
    ("L", "ωs, ec. 25", "=ACOS(-TAN(I{r})*TAN(K{r}))"),
    ("M", "Ra, ec. 21 (MJ/m²·día)", "=24*60/PI()*constantes!$B$7*J{r}*(L{r}*SIN(I{r})*SIN(K{r})+COS(I{r})*COS(K{r})*SIN(L{r}))"),
    ("N", "N, ec. 34 (h)", "=24/PI()*L{r}"),
    ("O", "Rs, ec. 35 (MJ/m²·día)", "=(constantes!$B$4+constantes!$B$5*G{r}/N{r})*M{r}"),
    ("P", "Rso, ec. 37", "=(0.75+2E-5*constantes!$B$3)*M{r}"),
    ("Q", "e°(Tmáx), ec. 11 (kPa)", "=0.6108*EXP(17.27*C{r}/(C{r}+237.3))"),
    ("R", "e°(Tmín), ec. 11 (kPa)", "=0.6108*EXP(17.27*D{r}/(D{r}+237.3))"),
    ("S", "es, ec. 12 (kPa)", "=(Q{r}+R{r})/2"),
    ("T", "ea, ec. 17 (kPa)", "=(R{r}*E{r}/100+Q{r}*F{r}/100)/2"),
    ("U", "Rnl, ec. 39", "=constantes!$B$6*((C{r}+273.15)^4+(D{r}+273.15)^4)/2*(0.34-0.14*SQRT(T{r}))*(1.35*MIN(O{r}/P{r},1)-0.35)"),
    ("V", "Rn, ec. 38 y 40", "=(1-constantes!$B$9)*O{r}-U{r}"),
    ("W", "Tmedia, ec. 9 (°C)", "=(C{r}+D{r})/2"),
    ("X", "Δ, ec. 13 (kPa/°C)", "=4098*(0.6108*EXP(17.27*W{r}/(W{r}+237.3)))/(W{r}+237.3)^2"),
    ("Y", "P, ec. 7 (kPa)", "=101.3*((293-0.0065*constantes!$B$3)/293)^5.26"),
    ("Z", "γ, ec. 8 (kPa/°C)", "=0.000665*Y{r}"),
    ("AA", "ETo hoja, ec. 6 (mm/día)", "=(0.408*X{r}*V{r}+Z{r}*900/(W{r}+273)*H{r}*MAX(S{r}-T{r},0))/(X{r}+Z{r}*(1+0.34*H{r}))"),
    ("AB", "ETo script 13 (mm/día)", None),
    ("AC", "diferencia hoja − script", "=AA{r}-AB{r}"),
    ("AD", "nuestra ETo, celda de la estación (mm/día)", None),
]


def eto_math(fila, lat, z, u2):
    """El mismo cálculo de la hoja, con math, para comprobar que la hoja reproduce el script 13."""
    phi = math.radians(lat)
    j = fila["fecha"].dayofyear
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * j)
    delta = 0.409 * math.sin(2 * math.pi / 365 * j - 1.39)
    ws = math.acos(-math.tan(phi) * math.tan(delta))
    ra = 24 * 60 / math.pi * GSC * dr * (ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    n_luz = 24 / math.pi * ws
    rs = (A_S + B_S * fila["brillo_h"] / n_luz) * ra
    rso = (0.75 + 2e-5 * z) * ra
    e = lambda t: 0.6108 * math.exp(17.27 * t / (t + 237.3))  # noqa: E731
    es = (e(fila["tmax_C"]) + e(fila["tmin_C"])) / 2
    ea = (e(fila["tmin_C"]) * fila["hrmax_pct"] / 100 + e(fila["tmax_C"]) * fila["hrmin_pct"] / 100) / 2
    rnl = SIGMA * ((fila["tmax_C"] + 273.15) ** 4 + (fila["tmin_C"] + 273.15) ** 4) / 2 \
        * (0.34 - 0.14 * math.sqrt(ea)) * (1.35 * min(rs / rso, 1) - 0.35)
    rn = (1 - ALBEDO) * rs - rnl
    t = (fila["tmax_C"] + fila["tmin_C"]) / 2
    dlt = 4098 * e(t) / (t + 237.3) ** 2
    gamma = 0.000665 * 101.3 * ((293 - 0.0065 * z) / 293) ** 5.26
    return (0.408 * dlt * rn + gamma * 900 / (t + 273) * u2 * max(es - ea, 0)) / (dlt + gamma * (1 + 0.34 * u2))


def main():
    catalogo = pd.read_csv(CATALOGO_IDEAM, dtype=str)
    est = catalogo[catalogo["codigo"].str.lstrip("0") == ESTACION].iloc[0]
    lat, z = float(est["latitud"]), float(est["altitud"])
    diaria = pd.read_csv(PRODUCTOS / "eto_estaciones_diaria.csv", dtype={"estacion": str}, parse_dates=["fecha"])
    rs = pd.read_csv(PRODUCTOS / "rs_estaciones_diaria.csv", dtype={"estacion": str}, parse_dates=["fecha"])
    d = diaria[(diaria["estacion"] == ESTACION) & (diaria["fecha"].dt.strftime("%Y-%m") == MES)]
    d = d.merge(rs[rs["estacion"] == ESTACION][["fecha", "brillo_h"]], on="fecha").reset_index(drop=True)
    assert len(d) > 0
    u2 = float(d["u2_mogotes_aut_ms"].iloc[0])
    assert (d["u2_mogotes_aut_ms"] == u2).all()

    # Comprobación independiente: math frente al script 13
    otra = d.apply(lambda f: eto_math(f, lat, z, u2), axis=1)
    error = (otra - d["eto_mogotes_aut_mm"]).abs().max()
    assert error < 1e-3, f"el cálculo con math no reproduce el script 13 (máx. {error})"

    libro = Workbook()
    hoja_c = libro.active
    hoja_c.title = "constantes"
    for fila in [("constante", "valor", "fuente"),
                 ("latitud (°)", lat, "catálogo IDEAM (cne_ideam.csv)"),
                 ("z, altura de la estación (m)", z, "catálogo IDEAM (cne_ideam.csv)"),
                 ("a_s", A_S, "FAO-56 ec. 35, sin calibración local"),
                 ("b_s", B_S, "FAO-56 ec. 35, sin calibración local"),
                 ("σ (MJ/K⁴·m²·día)", SIGMA, "FAO-56 ec. 39"),
                 ("Gsc (MJ/m²·min)", GSC, "FAO-56 ec. 21"),
                 ("u2 del mes (m/s)", u2, "Mogotes-AUT a 10 m llevado a 2 m con la ec. 47 (script 13)"),
                 ("albedo", ALBEDO, "FAO-56, pasto de referencia")]:
        hoja_c.append(fila)
    hoja = libro.create_sheet("dias")
    hoja.append([encabezado for _, encabezado, _ in COLUMNAS])
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for i, f in d.iterrows():
        r = i + 2
        datos = {"A": f["fecha"].strftime("%Y-%m-%d"), "B": int(f["fecha"].dayofyear), "C": f["tmax_C"],
                 "D": f["tmin_C"], "E": f["hrmax_pct"], "F": f["hrmin_pct"], "G": f["brillo_h"],
                 "AB": round(float(f["eto_mogotes_aut_mm"]), 4), "AD": round(float(f["eto_era5_mm"]), 4)}
        for col, _, formula in COLUMNAS:
            hoja[f"{col}{r}"] = formula.format(r=r) if formula else datos[col]
    ultima = len(d) + 1
    base = ultima + 2
    hoja[f"Z{base}"] = "media del mes"
    hoja[f"Z{base}"].font = Font(bold=True)
    for col in ["AA", "AB", "AC", "AD"]:
        hoja[f"{col}{base}"] = f"=AVERAGE({col}2:{col}{ultima})"
    hoja[f"Z{base + 1}"] = "sesgo de nuestra ETo este mes (AD − AA)"
    hoja[f"AA{base + 1}"] = f"=AD{base}-AA{base}"
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    libro.save(SALIDA)
    print(f"{ESTACION} {MES}: {len(d)} días, ETo media {d['eto_mogotes_aut_mm'].mean():.3f} mm/día (script 13), "
          f"nuestra ETo {d['eto_era5_mm'].mean():.3f}; math frente al script: máx. {error:.1e}")
    print(f"Listo: {SALIDA.relative_to(RAIZ_ENTREGA)}")


if __name__ == "__main__":
    main()
