"""Procesa las descargas del portal DHIME del IDEAM (pluviómetros de la cuenca del Fonce).

Los datos NO se descargan automáticamente: el portal (https://atencionciudadano.ideam.gov.co)
exige aceptar sus términos de uso e interactuar con la interfaz, así que los archivos se bajaron
a mano y se guardaron sin modificar en `data/ideam/pluviometros/dhime/`. Este script solo los lee.

Cómo se bajaron (para repetirlo):
  Variable = PRECIPITACION
  Parámetro = "Día pluviométrico (convencional)"  ->  serie diaria
              "Precipitación total mensual"       ->  serie mensual
  Departamento = Santander, Municipio = Todo, y luego se filtró por código de estación.
  Formato = CSV (el portal entrega un .zip con un único archivo `descargaDhime.csv`).

Dos límites del portal que explican por qué hay dos archivos:
  1. La consulta diaria no acepta más de ~20 años por descarga.
  2. El parámetro diario "Día pluviométrico (convencional)" no devolvió nada después del año 2000
     para estas estaciones; la serie mensual sí llega hasta 2022. Por eso el diario va de 1981 a 2000
     y el mensual de 1981 a 2022. No se rellenó ni se estimó nada para cubrir el faltante.

Estaciones (las tres del Fonce que cubren el gradiente de altura):
  24020040 ENCINO      (1814 m, subcuenca del Pienta)
  24020060 VILLANUEVA  (1450 m, valle del Fonce; su registro termina en 1994)
  24020220 PAVAS LAS   (2625 m, subcuenca del Taquiza; la más alta de la cuenca)

Salidas:
  out/pluviometros_fonce_diario.csv   (fecha, codigo, nombre, precipitacion_mm, nivel_aprobacion)
  out/pluviometros_fonce_mensual.csv  (mismas columnas, un registro por mes)
  out/pluviometros_fonce_resumen.csv  (cobertura y % de datos faltantes por estación)
"""
import zipfile, hashlib
from pathlib import Path
import pandas as pd

DHIME = Path("data/ideam/pluviometros/dhime")
OUT = Path("out")
ARCHIVOS = {
    "diario": DHIME / "dhime_1981_2000.zip",
    "mensual": DHIME / "dhime_mensual_1981_2022.zip",
}
ESTACIONES = {24020040: "ENCINO", 24020060: "VILLANUEVA", 24020220: "PAVAS LAS"}


def leer_zip(ruta):
    """Lee el CSV que viene dentro del zip de DHIME. El archivo está codificado en latin-1."""
    with zipfile.ZipFile(ruta) as z:
        nombre = z.namelist()[0]
        with z.open(nombre) as f:
            d = pd.read_csv(f, encoding="latin-1")
    d = d.rename(columns={
        "CodigoEstacion": "codigo", "NombreEstacion": "nombre_completo", "Fecha": "fecha",
        "Valor": "precipitacion_mm", "NivelAprobacion": "nivel_aprobacion",
    })
    d["fecha"] = pd.to_datetime(d["fecha"])
    d["nombre"] = d["codigo"].map(ESTACIONES)
    return d[["fecha", "codigo", "nombre", "precipitacion_mm", "nivel_aprobacion"]].sort_values(
        ["codigo", "fecha"]).reset_index(drop=True)


def resumen(d, frecuencia):
    """Cobertura de cada estación: período, número de registros y % de faltantes frente al período."""
    filas = []
    for codigo, g in d.groupby("codigo"):
        inicio, fin = g.fecha.min(), g.fecha.max()
        esperados = len(pd.date_range(inicio, fin, freq="D" if frecuencia == "diario" else "MS"))
        con_dato = g.precipitacion_mm.notna().sum()
        filas.append({
            "codigo": codigo, "nombre": ESTACIONES[codigo], "frecuencia": frecuencia,
            "desde": inicio.date(), "hasta": fin.date(),
            "registros": len(g), "con_dato": int(con_dato),
            "faltantes_pct": round((esperados - con_dato) / esperados * 100, 1),
            "media_mm": round(g.precipitacion_mm.mean(), 1),
        })
    return pd.DataFrame(filas)


series, resumenes = {}, []
for frecuencia, ruta in ARCHIVOS.items():
    d = leer_zip(ruta)
    d.to_csv(OUT / f"pluviometros_fonce_{frecuencia}.csv", index=False)
    series[frecuencia] = d
    resumenes.append(resumen(d, frecuencia))
    sha = hashlib.sha256(ruta.read_bytes()).hexdigest()
    print(f"{ruta.name}: {len(d)} registros -> out/pluviometros_fonce_{frecuencia}.csv")
    print(f"  sha256: {sha}")

tabla = pd.concat(resumenes, ignore_index=True)
tabla.to_csv(OUT / "pluviometros_fonce_resumen.csv", index=False)
print("\nCobertura por estación:")
print(tabla.to_string(index=False))

# Comprobación: la suma de los días de un mes completo debe parecerse al total mensual del portal.
diario, mensual = series["diario"], series["mensual"]
dm = diario.copy()
dm["mes"] = dm.fecha.dt.to_period("M")
g = dm.groupby(["codigo", "mes"])["precipitacion_mm"].agg(["sum", "count"])
g = g[g["count"] >= 28].reset_index()                       # solo meses casi completos
m = mensual.copy()
m["mes"] = m.fecha.dt.to_period("M")
comp = g.merge(m[["codigo", "mes", "precipitacion_mm"]], on=["codigo", "mes"])
comp["dif_pct"] = (comp["sum"] - comp.precipitacion_mm) / comp.precipitacion_mm * 100
print(f"\nComprobación diario vs. mensual ({len(comp)} meses casi completos en común):")
print(f"  diferencia mediana: {comp.dif_pct.median():.1f} %  |  "
      f"meses que difieren más de 5 %: {(comp.dif_pct.abs() > 5).sum()}")
