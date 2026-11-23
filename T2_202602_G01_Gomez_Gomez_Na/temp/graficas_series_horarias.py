"""Documento de trabajo (temporal): series mensuales de ETo y series horarias de ERA5-Land, en un HTML con zoom.

Arriba, dos gráficas mensuales de la cuenca:
  - ETo de Penman–Monteith FAO-56 (productos/punto1/eto_mensual_cuenca.csv, de codigo/punto1/04_eto_fao56.py)
    contra la ETP de Hargreaves de la Tarea 1 (../Analisis_De_Cuenca/out/etp_hargreaves_fonce.csv, columna
    etp_era5land, diaria, sumada aquí por mes).
  - La ETo separada en su término radiativo y su término aerodinámico (suman la ETo).
Debajo, las series horarias de las 6 variables descargadas.

Lee datos/punto1/era5land_puntos/punto_N.csv (salida de codigo/punto1/01_descarga_era5land_puntos.py) y escribe
temp/series_horarias_era5land.html: una gráfica Plotly por variable, con los 6 puntos, a la que se le puede hacer
zoom (arrastrar un recuadro, rueda del ratón, doble clic para volver).

Hora local de Colombia = valid_time (UTC) − 5 h (decisión del 2026-11-12, anexos/decisiones.md).
Conversiones solo de unidades, para leer mejor: K → °C, Pa → kPa, ssrd J/m² en la hora → W/m² promedio de la hora
(÷ 3600). u10 y v10 se muestran tal cual (m/s).

Al final, la fase 3 (pruebas de la referencia): Rs de Angstrom con el brillo solar de 3 estaciones del IDEAM frente
a la ssrd de ERA5-Land, y ETo Penman–Monteith (FAO-56) de estación frente a la de ERA5-Land, con sus dos variantes de viento. Lee las
salidas de codigo/punto1/12_rs_brillo_solar_vs_era5land.py y 13_eto_estaciones_vs_era5land.py; no calcula nada nuevo.

También: la ETo de la fase 2 por mes calendario y su comprobación con medias mensuales (salidas de 04 y 04b, las
mismas que dibuja 04e), el estado de la auditoría de las fases 0 a 2 (cada casilla comprueba que su archivo exista), y
la ET real de cuenca de cada producto (salida de codigo/punto1/14_et_real_productos_cuenca.py) y el balance hídrico
P − Q − ΔS (salida de codigo/punto1/15_balance_hidrico.py).

Escribe también temp/documento_trabajo_ligero.html: lo mismo sin las series horarias (pesa menos de 1 MB), para
abrirlo con un enlace.

Las 219 144 horas × 6 puntos × 6 variables se guardan dentro del HTML como Float32 en base64, y el eje de tiempo
se reconstruye en el navegador a partir de la primera hora (las series son horarias y sin huecos; se verifica).
Por eso el archivo pesa unos 40 MB. Va en temp/, que se borra antes de armar el ZIP de la entrega.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python temp/graficas_series_horarias.py
"""

import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_ENTREGA = Path(__file__).resolve().parents[1]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"
SALIDA = RAIZ_ENTREGA / "temp" / "series_horarias_era5land.html"
SALIDA_LIGERA = RAIZ_ENTREGA / "temp" / "documento_trabajo_ligero.html"
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ANEXOS = RAIZ_ENTREGA / "anexos"
NOMBRES_PRODUCTO = {
    "era5land_e": "ERA5-Land e", "gleam_E": "GLEAM v4.3a E", "mod16a2gf": "MOD16A2GF v061",
    "terraclimate_aet": "TerraClimate aet", "ssebop_v61": "SSEBop v6.1", "ssebop_v5": "SSEBop v5",
    "gleam_Ep": "GLEAM v4.3a Ep (potencial)", "era5land_pev": "ERA5-Land pev (potencial)",
}

# Auditoría de las fases 0 a 2: (casilla, evidencia, archivos que deben existir). Todas cerradas el 2026-11-17.
AUDITORIA = [
    ("verificar_entrega.py y requirements.txt", "Existen; hoy solo reclama el informe, la presentación y temp/, que se hacen o borran al cerrar.",
     ["codigo/verificar_entrega.py", "codigo/requirements.txt"]),
    ("Inventario de la Tarea 1, con longitud y pendiente del cauce", "anexos/inventario_t1.md", ["anexos/inventario_t1.md"]),
    ("Ponderación espacial declarada [M05]", "Voronoi; en el informe se dice así, sin presentarlo como igual a la Tarea 1 (decisiones).",
     ["anexos/decisiones.md"]),
    ("Tmáx, Tmín horarias y es [M10]", "Scripts 03 y 04, ec. 12.", ["codigo/punto1/03_series_diarias_rn.py"]),
    ("ea con el punto de rocío [M11]", "Promedio diario de e°(Td) horario.", ["codigo/punto1/03_series_diarias_rn.py"]),
    ("Viento y ec. 47 [M12]", "Qué supone la ec. 47, escrito en decisiones: u2 = 0.748 u10, perfil logarítmico sobre pasto.",
     ["anexos/decisiones.md"]),
    ("Rn con α = 0.23; Rn de ERA5-Land aparte [M13]", "Rn neta de ERA5-Land descargada (script 07).",
     ["datos/punto1/era5land_mensual_balance/era5land_mensual_balance_1998_2022_fonce.nc"]),
    ("G = 0 y γ [M14]", "γ con la presión de cada punto, declarado como decisión.", ["anexos/decisiones.md"]),
    ("Elevación de los puntos frente al DEM [M15]", "Script 04b; tabla abajo.", ["anexos/punto1/elevacion_puntos_dem.csv"]),
    ("Medias mensuales frente a suma de diarias [K02, F02]", "Script 04b y figura 04e; gráfica abajo.",
     ["anexos/punto1/eto_medias_mensuales_vs_suma_diarias.csv", "anexos/punto1/eto_medias_mensuales_vs_suma_diarias.png"]),
    ("Un día a mano [K01]", "2010-02-15, punto 6: ETo = 3.76 mm/día, igual a los productos a 4 decimales. Juan lo revisó contra FAO-56.",
     ["anexos/punto1/dia_verificado_a_mano.xlsx"]),
    ("Convenciones de ERA5-Land y error de ECMWF [M07]", "Script 04d: el mensual está dañado en sep–dic 2022; se usa hasta 2022-08. Los 6 puntos horarios no.",
     ["anexos/punto1/era5land_sep_dic_2022_comprobacion.csv"]),
    ("Un .meta.json por archivo de datos [R08]", "Script 00.", ["codigo/punto1/00_metadatos_datos.py"]),
    ("Periodo de la ETo", "1998–2022.", ["anexos/decisiones.md"]),
    ("Decisiones en anexos/", "anexos/decisiones.md", ["anexos/decisiones.md"]),
    ("Bitácora de IA", "anexos/bitacora_ia.md", ["anexos/bitacora_ia.md"]),
]

NOMBRES_ESTACION = {"24025040": "Mogotes (1 673 m)", "24025030": "La Sierra (2 850 m)", "24025050": "Charalá (1 350 m)"}
ETO_CUENCA = RAIZ_ENTREGA / "productos" / "punto1" / "eto_mensual_cuenca.csv"
# La ETP de Hargreaves de la Tarea 1 (fuera de la carpeta de la entrega): solo para comparar en este documento.
HARGREAVES_TAREA1 = RAIZ_ENTREGA.parent / "Analisis_De_Cuenca" / "out" / "etp_hargreaves_fonce.csv"

DESFASE_HORA_LOCAL = pd.Timedelta(hours=-5)  # Colombia, UTC−5, sin horario de verano
PUNTOS = [1, 2, 3, 4, 5, 6]

# columna del CSV -> (nombre en la gráfica, unidades, función de conversión)
VARIABLES = {
    "t2m": ("Temperatura a 2 m · t2m", "°C", lambda x: x - 273.15),
    "d2m": ("Punto de rocío a 2 m · d2m", "°C", lambda x: x - 273.15),
    "sp": ("Presión en superficie · sp", "kPa", lambda x: x / 1000.0),
    "u10": ("Viento a 10 m hacia el este · u10", "m/s", lambda x: x),
    "v10": ("Viento a 10 m hacia el norte · v10", "m/s", lambda x: x),
    "ssrd": ("Radiación solar entrante · ssrd", "W/m²", lambda x: x / 3600.0),
}


def a_base64(valores):
    """Serie numérica -> texto base64 de sus bytes Float32 (little-endian)."""
    return base64.b64encode(np.asarray(valores, dtype="<f4").tobytes()).decode("ascii")


def leer_punto(n):
    """Lee la serie de un punto, ordenada por hora, y comprueba que sea horaria y sin huecos."""
    datos = pd.read_csv(CARPETA_DATOS / f"punto_{n}.csv", parse_dates=["valid_time"])
    datos = datos.sort_values("valid_time").reset_index(drop=True)
    pasos = datos["valid_time"].diff().dropna().unique()
    assert len(pasos) == 1 and pasos[0] == np.timedelta64(1, "h"), f"punto {n}: la serie no es horaria continua"
    return datos


def series_mensuales_eto():
    """ETo mensual de la cuenca con sus términos, y la ETP de Hargreaves mensual (mm/mes), mes a mes."""
    eto = pd.read_csv(ETO_CUENCA)
    hargreaves = pd.read_csv(HARGREAVES_TAREA1, parse_dates=["fecha"])
    hargreaves = hargreaves.set_index("fecha")["etp_era5land"].resample("MS").agg(["sum", "count"])
    hargreaves.index = hargreaves.index.strftime("%Y-%m")
    assert (hargreaves["count"] == hargreaves.index.map(lambda m: pd.Period(m).days_in_month)).all()
    juntas = eto.set_index("mes").join(hargreaves["sum"].rename("hargreaves_mm_mes"), how="left")
    assert juntas["hargreaves_mm_mes"].notna().all(), "faltan meses de Hargreaves"
    return {
        "meses": list(juntas.index),
        "eto": juntas["eto_mm_mes"].round(2).tolist(),
        "radiativa": juntas["eto_radiativa_mm_mes"].round(2).tolist(),
        "aerodinamica": juntas["eto_aerodinamica_mm_mes"].round(2).tolist(),
        "hargreaves": juntas["hargreaves_mm_mes"].round(2).tolist(),
    }


DIAS_MINIMOS_MES = 15   # series mensuales de estación: mínimo de días con dato


def datos_fase3():
    """Salidas de los scripts 12 y 13: ciclo anual, sesgo por mes, series diarias y resumen, por estación."""
    rs_mes = pd.read_csv(CARPETA_PRODUCTOS / "rs_estaciones_vs_era5land_por_mes.csv", dtype={"estacion": str})
    rs_res = pd.read_csv(CARPETA_PRODUCTOS / "rs_estaciones_vs_era5land_resumen.csv", dtype={"estacion": str})
    rs_dia = pd.read_csv(CARPETA_PRODUCTOS / "rs_estaciones_diaria.csv", dtype={"estacion": str})
    eto_mes = pd.read_csv(CARPETA_PRODUCTOS / "eto_estaciones_vs_era5land_por_mes.csv", dtype={"estacion": str})
    eto_res = pd.read_csv(CARPETA_PRODUCTOS / "eto_estaciones_vs_era5land_resumen.csv", dtype={"estacion": str})
    eto_dia = pd.read_csv(CARPETA_PRODUCTOS / "eto_estaciones_diaria.csv", dtype={"estacion": str})
    estaciones = []
    for codigo, nombre in NOMBRES_ESTACION.items():
        r = rs_mes[rs_mes["estacion"] == codigo].sort_values("mes")
        rr = rs_res[rs_res["estacion"] == codigo].iloc[0]
        e = {v: eto_mes[(eto_mes["estacion"] == codigo) & (eto_mes["variante_viento"] == v)].sort_values("mes")
             for v in ["mogotes_aut", "era5land"]}
        er = eto_res[eto_res["estacion"] == codigo].set_index("variante_viento")
        # Serie mensual: media de los días con dato; el mes queda vacío (null) si tiene menos de DIAS_MINIMOS_MES días.
        def mensual(tabla, columnas):
            t = tabla.assign(fecha=pd.to_datetime(tabla["fecha"])).set_index("fecha")[columnas]
            media = t.resample("MS").mean().reindex(pd.date_range("1998-01-01", "2022-12-01", freq="MS"))
            cuenta = t.resample("MS").count().reindex(media.index).fillna(0)
            media = media.where(cuenta >= DIAS_MINIMOS_MES)
            salida = {"fecha": media.index.strftime("%Y-%m-01").tolist()}
            for c in columnas:
                salida[c] = [None if pd.isna(v) else round(float(v), 2) for v in media[c]]
            return salida
        rd = mensual(rs_dia[rs_dia["estacion"] == codigo], ["rs_estacion_MJm2", "rs_era5_MJm2"])
        ed = mensual(eto_dia[eto_dia["estacion"] == codigo], ["eto_mogotes_aut_mm", "eto_era5land_mm", "eto_era5_mm"])
        estaciones.append({
            "codigo": codigo, "nombre": nombre, "punto": str(rr["celda_era5"]),
            "distancia_km": float(rr["distancia_km"]), "dz_celda_m": float(rr["estacion_menos_celda_dem_m"]),
            "rs": {"estacion": r["rs_estacion_media"].round(2).tolist(), "era5": r["rs_era5_media"].round(2).tolist(),
                   "sesgo": r["sesgo_MJm2"].round(2).tolist(),
                   "sesgo_total": round(float(rr["sesgo_MJm2"]), 2), "sesgo_pct": round(float(rr["sesgo_pct"]), 1),
                   "rmse": round(float(rr["rmse_MJm2"]), 2), "dias": int(rr["dias"])},
            "eto": {"a": e["mogotes_aut"]["eto_estacion_media_mm_dia"].round(3).tolist(),
                    "b": e["era5land"]["eto_estacion_media_mm_dia"].round(3).tolist(),
                    "era5": e["mogotes_aut"]["eto_era5_media_mm_dia"].round(3).tolist(),
                    "sesgo_a": e["mogotes_aut"]["sesgo_mm_dia"].round(3).tolist(),
                    "sesgo_b": e["era5land"]["sesgo_mm_dia"].round(3).tolist(),
                    "resumen": {v: {"sesgo": round(float(er.loc[v, "sesgo_mm_dia"]), 2),
                                    "pct": round(float(er.loc[v, "sesgo_pct"]), 1),
                                    "rmse": round(float(er.loc[v, "rmse_mm_dia"]), 2), "dias": int(er.loc[v, "dias"])}
                                for v in ["mogotes_aut", "era5land"]}},
            "diaria_rs": {"fecha": rd["fecha"], "estacion": rd["rs_estacion_MJm2"], "era5": rd["rs_era5_MJm2"]},
            "diaria_eto": {"fecha": ed["fecha"], "a": ed["eto_mogotes_aut_mm"], "b": ed["eto_era5land_mm"], "era5": ed["eto_era5_mm"]},
        })
    return estaciones


def datos_fase2_y_auditoria():
    """ETo por mes calendario (cuenca, términos y puntos), comprobación con medias mensuales, alturas y auditoría."""
    cuenca = pd.read_csv(ETO_CUENCA)
    mes = pd.to_datetime(cuenca["mes"]).dt.month
    ciclo = cuenca.groupby(mes)[["eto_mm_mes", "eto_radiativa_mm_mes", "eto_aerodinamica_mm_mes"]].mean()
    puntos = pd.read_csv(CARPETA_PRODUCTOS / "eto_mensual_puntos.csv")
    puntos["m"] = pd.to_datetime(puntos["mes"]).dt.month
    ciclo_puntos = puntos.groupby(["punto", "m"])["eto_mm_mes"].mean().unstack("m")
    alturas = pd.read_csv(ANEXOS / "punto1" / "elevacion_puntos_dem.csv")
    comprobacion = pd.read_csv(ANEXOS / "punto1" / "eto_medias_mensuales_vs_suma_diarias.csv", dtype={"punto": str})
    c = comprobacion[comprobacion["punto"] == "cuenca"].copy()
    assert len(c) == 300
    c["agregar_pct"] = 100 * c["parte_agregar_mm_mes"] / c["eto_suma_diarias_mm_mes"]
    c["g_pct"] = 100 * c["parte_g_mm_mes"] / c["eto_suma_diarias_mm_mes"]
    r = c.groupby(pd.to_datetime(c["mes"]).dt.month)[["diferencia_pct", "agregar_pct", "g_pct"]].agg(["mean", "min", "max"])
    auditoria = []
    for casilla, evidencia, archivos in AUDITORIA:
        faltan = [a for a in archivos if not (RAIZ_ENTREGA / a).exists()]
        auditoria.append({"casilla": casilla, "evidencia": evidencia, "cerrada": not faltan, "faltan": faltan})
    return {
        "ciclo": {"eto": ciclo["eto_mm_mes"].round(1).tolist(), "radiativa": ciclo["eto_radiativa_mm_mes"].round(1).tolist(),
                  "aerodinamica": ciclo["eto_aerodinamica_mm_mes"].round(1).tolist()},
        "ciclo_puntos": {str(n): ciclo_puntos.loc[n].round(1).tolist() for n in ciclo_puntos.index},
        "alturas": alturas[["punto", "z_celda_dem_m", "z_region_dem_m", "z_modelo_m", "modelo_menos_region_m",
                            "efecto_t_era5land_C", "efecto_ea_era5land_kPa"]].round(3).to_dict("records"),
        "comprobacion": {k: r[(col, est)].round(2).tolist() for k, (col, est) in {
            "media": ("diferencia_pct", "mean"), "min": ("diferencia_pct", "min"), "max": ("diferencia_pct", "max"),
            "agregar": ("agregar_pct", "mean"), "g": ("g_pct", "mean")}.items()},
        "auditoria": auditoria,
    }


def datos_prueba_terraclimate():
    """Segunda prueba de la ETo: nuestra ETo frente a TerraClimate pet (salidas de 16_eto_vs_terraclimate_pet.py)."""
    eto = pd.read_csv(ETO_CUENCA)
    pet = pd.read_csv(CARPETA_PRODUCTOS / "terraclimate_mensual_cuenca.csv")
    assert list(eto["mes"]) == list(pet["mes"])
    por_mes = pd.read_csv(CARPETA_PRODUCTOS / "eto_vs_terraclimate_pet_por_mes.csv")
    r = pd.read_csv(CARPETA_PRODUCTOS / "eto_vs_terraclimate_pet_resumen.csv").iloc[0]
    return {
        "meses": list(eto["mes"]), "eto": eto["eto_mm_mes"].round(1).tolist(), "pet": pet["pet_mm_mes"].round(1).tolist(),
        "ciclo_eto": por_mes["eto_fao56_media"].round(1).tolist(), "ciclo_pet": por_mes["pet_terraclimate_media"].round(1).tolist(),
        "sesgo": por_mes["sesgo_mm_mes"].round(2).tolist(), "mae": por_mes["mae_mm_mes"].round(2).tolist(),
        "rmse": por_mes["rmse_mm_mes"].round(2).tolist(),
        "resumen": {"sesgo": round(float(r["sesgo_mm_mes"]), 1), "pct": round(float(r["sesgo_pct"]), 1),
                    "mae": round(float(r["mae_mm_mes"]), 1), "rmse": round(float(r["rmse_mm_mes"]), 1),
                    "r": round(float(r["correlacion"]), 2), "anual_eto": round(float(r["eto_fao56_anual_mm"])),
                    "anual_pet": round(float(r["pet_terraclimate_anual_mm"]))},
    }


def datos_cierre_fase3():
    """Cierre de la fase 3: tabla de pruebas, dispersión y ETo frente a P − Q (salidas de 17)."""
    pruebas = pd.read_csv(CARPETA_PRODUCTOS / "pruebas_referencia.csv")
    disp = pd.read_csv(CARPETA_PRODUCTOS / "dispersion_pruebas.csv")
    bal = pd.read_csv(CARPETA_PRODUCTOS / "eto_vs_p_menos_q.csv")
    anual = pruebas[pruebas["mes"] == "anual"]
    return {
        "anual": anual[["serie", "base", "n", "eto_nuestra_mm_dia", "referencia_mm_dia", "sesgo_mm_dia", "sesgo_pct",
                        "mae_mm_dia", "rmse_mm_dia"]].round(2).to_dict("records"),
        "sesgo": {c.replace("sesgo_pct_", ""): disp[c].round(1).tolist() for c in disp.columns if c.startswith("sesgo_pct_")},
        "dispersion": {c: disp[c].round(1).tolist() for c in ["rango_4_series_pct", "rango_2_pruebas_pct", "desv_est_4_series_pct"]},
        "dispersion_media": {c: round(float(disp[c].mean()), 1) for c in ["rango_4_series_pct", "rango_2_pruebas_pct", "desv_est_4_series_pct"]},
        "balance": bal.round(1).to_dict("records"),
    }


def datos_et_real():
    """ET real mensual y anual de cada producto (salidas de 14_et_real_productos_cuenca.py)."""
    mensual = pd.read_csv(CARPETA_PRODUCTOS / "et_real_mensual_productos.csv")
    anual = pd.read_csv(CARPETA_PRODUCTOS / "et_real_anual_productos.csv")
    periodo = anual["periodo_comun"].iloc[0]
    primero, ultimo = (int(a) for a in periodo.split("–"))
    comunes = mensual[mensual["mes"].str[:4].astype(int).between(primero, ultimo)]
    ciclo = comunes.groupby(comunes["mes"].str[5:7].astype(int)).mean(numeric_only=True)
    columnas = list(NOMBRES_PRODUCTO)
    return {
        "periodo_comun": periodo,
        "meses": mensual["mes"].tolist(),
        "nombres": NOMBRES_PRODUCTO,
        "series": {c: [None if pd.isna(v) else round(float(v), 1) for v in mensual[c]] for c in columnas},
        "ciclo": {c: ciclo[c].round(1).tolist() for c in columnas},
        "anual": [{"producto": NOMBRES_PRODUCTO[f.producto], "clave": f.producto,
                   "anios": f"{int(f.primer_anio)}–{int(f.ultimo_anio)} ({int(f.anios_completos_propio)})",
                   "propio": round(float(f.media_anual_propio_mm)), "comun": round(float(f.media_anual_comun_mm))}
                  for f in anual.itertuples()],
    }


def datos_balance():
    """Balance hídrico P − Q − ΔS (salidas de codigo/punto1/15_balance_hidrico.py)."""
    resumen = pd.read_csv(CARPETA_PRODUCTOS / "balance_hidrico_resumen.csv")
    anual = pd.read_csv(CARPETA_PRODUCTOS / "balance_hidrico_anual.csv")
    return {
        "resumen": [{"camino": f.camino, "n": f"{int(f.n)} {f.unidad_n}", "PI": round(f.P_PI), "PL": round(f.P_PL),
                     "Q": round(f.Q), "ETR_PI": round(f.ETR_PI), "ETR_PL": round(f.ETR_PL)} for f in resumen.itertuples()],
        "ds_neto": round(float(resumen["dS_suelo_neto_mm_anio"].iloc[0]), 1),
        "ds_desv": round(float(resumen["dS_suelo_anual_desv_est_mm"].iloc[0])),
        "anios": anual["anio"].astype(str).tolist(),
        "etr_pi": anual["ETR_PI_con_dS"].round(0).tolist(),
        "etr_pl": anual["ETR_PL_con_dS"].round(0).tolist(),
    }


def datos_metodos():
    """Fase 4: métodos frente a la ETo Penman–Monteith (FAO-56) (salidas de 21_metodos_et.py)."""
    mensual = pd.read_csv(CARPETA_PRODUCTOS / "metodos_mensual.csv")
    ajuste = pd.read_csv(CARPETA_PRODUCTOS / "ajuste_por_mes.csv")
    ciclo_anual = pd.read_csv(CARPETA_PRODUCTOS / "ajuste_ciclo_anual.csv")
    columnas = [c for c in mensual.columns if c.endswith("_mm_mes")]
    ciclo = mensual.groupby(mensual["mes"].str[5:7].astype(int))[columnas].mean()
    resumen = ajuste.groupby(["metodo", "cantidad", "referencia"], sort=False).agg(
        sesgo=("sesgo_pct", "mean"), sesgo_min=("sesgo_pct", "min"), sesgo_max=("sesgo_pct", "max"),
        mae=("mae_mm_mes", "mean"), rmse=("rmse_mm_mes", "mean"), supera=("supera_dispersion", "sum")).reset_index()
    resumen = resumen.merge(ciclo_anual[["metodo", "error_amplitud_pct", "error_fase_maximo_meses",
                                         "error_fase_minimo_meses"]], on="metodo")
    nombres = {"thornthwaite": "Thornthwaite", "hargreaves": "Hargreaves–Samani", "priestley_taylor": "Priestley–Taylor",
               "makkink": "Makkink", "penman_fao24": "Penman (FAO-24, c = 0.8)", "cenicafe_2006": "Cenicafé 2006",
               "aa_brutsaert_stricker": "Brutsaert–Stricker (AA)", "eto_fao56_rs0": "Penman–Monteith (FAO-56) con rs = 0",
               "eto_fao56": "ETo Penman–Monteith (FAO-56)"}
    anual = {nombres[c.removesuffix("_mm_mes")]: round(float(mensual[c].mean() * 12)) for c in columnas}
    resumen["anual"] = resumen["metodo"].map(anual)
    partes = pd.read_csv(ETO_CUENCA)
    # Sesgo % de cada mes calendario y la dispersión elegida en la fase 3 (rango entre las 2 pruebas, Juan 20 nov).
    clave = {v: k for k, v in nombres.items()}
    sesgo = {clave[m]: g.sort_values("mes")["sesgo_pct"].round(1).tolist() for m, g in ajuste.groupby("metodo")}
    dispersion = pd.read_csv(CARPETA_PRODUCTOS / "dispersion_pruebas.csv").sort_values("mes")["dispersion_pct"]
    return {
        "sesgo": sesgo, "dispersion": dispersion.round(2).tolist(),
        "dispersion_media": round(float(dispersion.mean()), 1),
        "eto_partes": {"radiativa": round(float(partes["eto_radiativa_mm_mes"].mean() * 12)),
                       "aerodinamica": round(float(partes["eto_aerodinamica_mm_mes"].mean() * 12))},
        "eto_anual": anual["ETo Penman–Monteith (FAO-56)"],
        "anual": anual,
        "ciclo": {c.removesuffix("_mm_mes"): ciclo[c].round(1).tolist() for c in columnas},
        "resumen": resumen.round(1).to_dict(orient="records"),
    }


def datos_terminos():
    """Fase 5: términos radiativo y aerodinámico de la ETo por mes calendario (salida de 26_terminos_fao56.py)."""
    t = pd.read_csv(CARPETA_PRODUCTOS / "terminos_fao56_ciclo.csv")
    return {c: t[c].round(2).tolist() for c in t.columns if c != "mes_calendario"}


def datos_alfa():
    """Fase 5: α* = ETo/Eeq por mes calendario (salida de 27_alfa_implicito.py)."""
    t = pd.read_csv(CARPETA_PRODUCTOS / "alfa_implicito_ciclo.csv")
    return {c: t[c].round(4).tolist() for c in t.columns if c != "mes_calendario"}


def texto_fase4():
    """Fase 5: explicación de las diferencias escrita por Juan (temp/textos_informe/fase5_diferencias_eto.md)."""
    import html, re
    lineas = (Path(__file__).with_name("textos_informe") / "fase5_diferencias_eto.md").read_text(encoding="utf-8")
    parrafos = [b.strip() for b in lineas.split("\n\n")]
    parrafos = [b for b in parrafos if b and not b.startswith("#") and not b.startswith("Texto de Juan")]
    salida = []
    for b in parrafos:
        b = html.escape(b, quote=False)
        b = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", b)
        b = re.sub(r"\*(.+?)\*", r"<i>\1</i>", b)
        salida.append(b)
    return salida


def datos_hargreaves_tarea1():
    """Fase 4: Hargreaves de la Tarea 1 frente al de la Tarea 2 (salida de 23_hargreaves_tarea1.py)."""
    h = pd.read_csv(CARPETA_PRODUCTOS / "hargreaves_tarea1_mensual.csv")
    comunes = h.dropna()
    columnas = [c for c in h.columns if c.endswith("_mm_mes")]
    anual = comunes[columnas].mean() * 12
    ciclo = comunes.groupby(comunes["mes"].str[5:7].astype(int))[columnas].mean()
    return {
        "n_meses": len(comunes),
        "anual": {c.removesuffix("_mm_mes"): round(float(v)) for c, v in anual.items()},
        "sesgo": {c.removesuffix("_mm_mes"): round(float(100 * (v / anual["eto_penman_monteith_mm_mes"] - 1)), 1)
                  for c, v in anual.items()},
        "ciclo": {c.removesuffix("_mm_mes"): ciclo[c].round(1).tolist() for c in columnas},
    }


def datos_fase6():
    """Fase 6: ET real por varios caminos, incertidumbre y techo de energía (salidas de 24_et_real_fase6.py)."""
    frente = pd.read_csv(CARPETA_PRODUCTOS / "et_productos_vs_balance.csv")
    incert = pd.read_csv(CARPETA_PRODUCTOS / "et_incertidumbre.csv")
    anual = pd.read_csv(CARPETA_PRODUCTOS / "et_balance_anual.csv")
    ciclo = pd.read_csv(CARPETA_PRODUCTOS / "et_techo_energia.csv")
    techo = pd.read_csv(CARPETA_PRODUCTOS / "et_techo_energia_resumen.csv")
    claves = ["era5land_e", "gleam_E", "mod16a2gf", "terraclimate_aet", "ssebop_v61", "ssebop_v5", "aa_brutsaert_stricker"]
    redondear = lambda serie, d=0: [None if pd.isna(v) else round(float(v), d) for v in serie]
    por_tipo = {}
    for tipo, t in anual.groupby("tipo_de_anio"):
        por_tipo[tipo] = {
            "anios": t["anio"].astype(str).tolist(), "meses": t["meses"].iloc[0],
            "pi": redondear(t["P_menos_Q_PI"]), "pl": redondear(t["P_menos_Q_PL"]), "sigma": redondear(t["sigma_ET"]),
            "ds": redondear(t["dS_suelo"]), "eto": redondear(t["ETo"]), "rn": redondear(t["Rn_lambda"]),
            "mediana": redondear(t["mediana_productos"]), "minimo": redondear(t["min_productos"]),
            "maximo": redondear(t["max_productos"]),
            "marcas_pi": t["marcas_PI"].fillna("").tolist(), "marcas_pl": t["marcas_PL"].fillna("").tolist(),
            "ds_desv": round(float(t["dS_suelo"].std()), 0),
        }
    return {
        "frente": frente.round(3).to_dict(orient="records"),
        "incertidumbre": incert.round(1).to_dict(orient="records"),
        "anual": por_tipo,
        "techo": techo.round(3).to_dict(orient="records"),
        "ciclo": {c: redondear(ciclo[c], 1) for c in ["Rn_lambda", "ETo", "ETR_PI", "ETR_PL"] + claves},
        "claves": claves,
    }


def main():
    mensual = series_mensuales_eto()
    series = {n: leer_punto(n) for n in PUNTOS}

    # Todas las series deben empezar a la misma hora y tener el mismo largo, para compartir el eje de tiempo.
    inicio_utc = series[PUNTOS[0]]["valid_time"].iloc[0]
    largo = len(series[PUNTOS[0]])
    for n, datos in series.items():
        assert datos["valid_time"].iloc[0] == inicio_utc and len(datos) == largo, f"punto {n}: otro eje de tiempo"
    inicio_local = inicio_utc + DESFASE_HORA_LOCAL

    carga = {
        "inicio_local": inicio_local.strftime("%Y-%m-%dT%H:%M:%S"),
        "horas": largo,
        "mensual": mensual,
        "fase3": datos_fase3(),
        "fase2": datos_fase2_y_auditoria(),
        "et_real": datos_et_real(),
        "prueba_tc": datos_prueba_terraclimate(),
        "cierre_f3": datos_cierre_fase3(),
        "balance": datos_balance(),
        "metodos": datos_metodos(),
        "hargreaves_t1": datos_hargreaves_tarea1(),
        "texto_f4": texto_fase4(),
        "terminos": datos_terminos(),
        "alfa": datos_alfa(),
        "fase6": datos_fase6(),
        "puntos": PUNTOS,
        "variables": [
            {
                "columna": col,
                "titulo": titulo,
                "unidades": unidades,
                "series": {str(n): a_base64(convertir(series[n][col].to_numpy(dtype=float))) for n in PUNTOS},
            }
            for col, (titulo, unidades, convertir) in VARIABLES.items()
        ],
    }

    # Cifras del encabezado, calculadas de las series mensuales de la cuenca (25 años completos).
    anios = len(mensual["meses"]) / 12
    carga["cifras"] = [
        [f"{sum(mensual['eto']) / anios:,.0f}".replace(",", " ") + " mm/año", "ETo Penman–Monteith, cuenca"],
        [f"{sum(mensual['hargreaves']) / anios:,.0f}".replace(",", " ") + " mm/año", "ETP Hargreaves (Tarea 1), cuenca"],
        [f"{100 * sum(mensual['aerodinamica']) / sum(mensual['eto']):.1f} %", "de la ETo sale del término aerodinámico"],
        [f"{largo:,}".replace(",", " ") + " h", "horas por punto, 6 puntos"],
    ]
    html = PLANTILLA.replace("__CARGA__", json.dumps(carga, ensure_ascii=False))
    SALIDA.write_text(html, encoding="utf-8")
    print(f"Listo: {SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB), {largo} horas por punto")

    # Versión ligera: sin las series horarias.
    carga["variables"] = []
    carga["horas"] = 0
    carga["cifras"] = carga["cifras"][:3]
    SALIDA_LIGERA.write_text(PLANTILLA.replace("__CARGA__", json.dumps(carga, ensure_ascii=False)), encoding="utf-8")
    print(f"Listo: {SALIDA_LIGERA} ({SALIDA_LIGERA.stat().st_size / 1e6:.1f} MB)")


PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Documento de trabajo ETo</title>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Mismo estilo que el informe de la Tarea 1 (Analisis_De_Cuenca/scripts/18b_reporte_html.py). */
:root {
  --fondo: #F5F7F6; --superficie: #FFFFFF; --tinta: #17211E; --tenue: #56645F; --linea: #D5DDDA;
  --acento: #1B6A80; --acento-suave: #E2EFF2;
  --f-titulo: "Archivo", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --f-texto: "Source Serif 4", Georgia, "Times New Roman", serif;
  --f-dato: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
    --acento: #72B9CE; --acento-suave: #1C2D32;
  }
}
:root[data-theme="dark"] {
  --fondo: #111715; --superficie: #18201E; --tinta: #E3EAE7; --tenue: #9AA9A4; --linea: #2B3633;
  --acento: #72B9CE; --acento-suave: #1C2D32;
}
* { box-sizing: border-box; }
body { background: var(--fondo); color: var(--tinta); font: 400 17px/1.6 var(--f-texto); margin: 0; }
.envoltura { max-width: 1240px; margin: 0 auto; padding-inline: 20px; padding-block: 48px 72px; }
header { border-bottom: 1px solid var(--linea); padding-bottom: 28px; margin-bottom: 40px; }
.antetitulo { font: 600 12px/1 var(--f-dato); letter-spacing: .12em; text-transform: uppercase; color: var(--acento); margin: 0 0 14px; }
h1 { font: 800 clamp(32px, 5vw, 50px)/1.05 var(--f-titulo); font-stretch: 82%; letter-spacing: -.01em; margin: 0 0 16px; text-wrap: balance; }
h2 { font: 800 34px/1.15 var(--f-titulo); font-stretch: 88%; margin: 0 0 16px; text-wrap: balance;
     color: var(--acento); border-left: 6px solid var(--acento); padding-left: 14px; }
h3 { font: 600 13px/1.3 var(--f-dato); letter-spacing: .08em; text-transform: uppercase; color: var(--tenue); margin: 0 0 6px; }
p { margin: 0 0 14px; max-width: 66ch; }
.intro { font-size: 19px; color: var(--tenue); max-width: 64ch; margin: 0; }
.cifras { display: flex; flex-wrap: wrap; gap: 12px 36px; margin-top: 24px; }
.cifra { display: flex; flex-direction: column; gap: 2px; }
.cifra b { font: 500 24px/1.1 var(--f-dato); font-variant-numeric: tabular-nums; }
.cifra span { font: 400 12px/1.3 var(--f-dato); color: var(--tenue); letter-spacing: .04em; }
section { margin-bottom: 64px; }
.nota { font-size: 14px; color: var(--tenue); }
.tarjeta { background: var(--superficie); border: 1px solid var(--linea); border-radius: 6px; padding: 14px 12px 4px; }
.dos { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 12px; }
.rejilla { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 12px; }
.grafico { width: 100%; height: 380px; }
.rejilla .grafico { height: 300px; }
.controles { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 14px; }
.controles button { font: 500 13px/1 var(--f-dato); color: var(--tenue); background: var(--superficie); border: 1px solid var(--linea);
  border-radius: 6px; padding: 8px 12px; cursor: pointer; }
.controles button:hover { color: var(--tinta); }
.controles button[aria-pressed="true"] { color: var(--acento); border-color: var(--acento); background: var(--acento-suave); font-weight: 600; }
.tabla { overflow-x: auto; margin: 8px 0 4px; }
.tabla table { border-collapse: collapse; font: 400 13px/1.4 var(--f-dato); font-variant-numeric: tabular-nums; }
.tabla th, .tabla td { padding: 6px 12px; border-bottom: 1px solid var(--linea); text-align: right; white-space: nowrap; }
.tabla th:first-child, .tabla td:first-child { text-align: left; }
.tabla th { color: var(--tenue); font-weight: 500; }
.metodos { overflow-x: auto; }
.metodos table { border-collapse: collapse; font-size: 13.5px; line-height: 1.45; min-width: 760px; }
.metodos th, .metodos td { padding: 7px 10px; border-bottom: 1px solid var(--linea); text-align: left; vertical-align: top; }
.metodos th { color: var(--tenue); font-weight: 500; }
.metodos td.si { color: #1B7F4B; } .metodos td.no { color: #B3412E; }
footer { border-top: 1px solid var(--linea); padding-top: 24px; font-size: 14px; color: var(--tenue); }
code { font: 400 .86em var(--f-dato); }
@media (max-width: 1000px) { .rejilla { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 760px) { .dos, .rejilla { grid-template-columns: 1fr; } body { font-size: 16px; } }
</style>
</head>
<body>
<div class="envoltura">
<header>
  <p class="antetitulo">Tarea 2 · Punto 1 · Documento de trabajo (temporal)</p>
  <h1>Evapotranspiración de referencia en la cuenca del Fonce</h1>
  <p class="intro">ERA5-Land en 6 puntos de la cuenca, 1998–2022, en hora local (UTC−5). La cuenca es el promedio
  de los puntos ponderado por el área de su región de Voronoi.</p>
  <div class="cifras" id="cifras"></div>
</header>

<section>
  <h2>ETo mensual</h2>
  <p>Arrastra un recuadro o usa la rueda del ratón para hacer zoom; doble clic vuelve a la vista completa.</p>
  <div class="dos">
    <div class="tarjeta"><h3>Penman–Monteith contra Hargreaves</h3><div class="grafico" id="g-comparacion"></div></div>
    <div class="tarjeta"><h3>ETo por términos (apilados, suman la ETo)</h3><div class="grafico" id="g-terminos"></div></div>
  </div>
</section>

<section>
  <h2>ETo por mes del año</h2>
  <p>Media de 1998–2022 por mes calendario. Mismos datos que <code>productos/punto1/eto_ciclo_anual.png</code>
  (script 04e).</p>
  <div class="dos">
    <div class="tarjeta"><h3>Cuenca: términos radiativo y aerodinámico (suman la ETo)</h3><div class="grafico" id="g-f2-terminos"></div></div>
    <div class="tarjeta"><h3>ETo de cada punto y de la cuenca</h3><div class="grafico" id="g-f2-puntos"></div></div>
  </div>
</section>

<section>
  <h2>Comprobaciones de la ETo</h2>
  <p><b>Medias mensuales frente a suma de diarias.</b> ETo calculada con las medias del mes (G con la ec. 43) menos la
  suma de las ETo diarias, en % de la suma, para la cuenca. Línea: media de los 25 años; banda: mínimo a máximo.
  Script 04b; figura fija en <code>anexos/punto1/eto_medias_mensuales_vs_suma_diarias.png</code>.</p>
  <div class="tarjeta"><div class="grafico" id="g-f2-comprobacion"></div></div>
  <p style="margin-top:20px"><b>Altura de los 6 puntos frente al DEM</b> (script 04b). z del modelo despejada de la
  presión media; efecto en T y ea con el gradiente del propio ERA5-Land.</p>
  <div class="tabla" id="t-f2-alturas"></div>
  <p style="margin-top:20px"><b>Un día a mano.</b> 2010-02-15, punto 6, desde las 24 horas crudas hasta la ETo, en
  <code>anexos/punto1/dia_verificado_a_mano.xlsx</code> (script 04c): ETo = 3.76 mm/día, igual a los productos a 4
  decimales. Juan lo revisó contra FAO-56 el 2026-11-17.</p>
</section>

<section>
  <h2>Auditoría de las fases 0 a 2</h2>
  <p id="p-auditoria"></p>
  <div class="tabla" id="t-auditoria"></div>
</section>

<section id="s-horarias">
  <h2>Series horarias de las 6 variables</h2>
  <p>El zoom en el tiempo se sincroniza en las 6 gráficas. Clic en un punto de la leyenda lo oculta o lo muestra en todas.</p>
  <div class="controles" id="ventanas"></div>
  <div class="rejilla" id="rejilla"></div>
</section>

<section>
  <h2>Fase 3 · Resumen: qué se hizo, cómo y para qué</h2>
  <p><b>Para qué.</b> Nuestra ETo Penman–Monteith (FAO-56) es la referencia de todo el punto 1, pero sale de un reanálisis. La fase 3
  mide cuánto puede estar mal comparándola con fuentes que no salen de nuestro cálculo, y deja el margen (la
  dispersión entre pruebas) que usan la fase 4 como umbral y la fase 5 como banda.</p>
  <ol class="resumen">
    <li><b>Rs de ERA5-Land frente al brillo solar</b> (script 12). Rs de estación con Angstrom (FAO-56 ec. 35, a<sub>s</sub>
    0.25, b<sub>s</sub> 0.50) en Mogotes, La Sierra y Charalá, contra la celda de ERA5-Land que contiene a cada estación. ERA5-Land da
    +11 %, +34 % y +13 % más Rs (+1.8 a +4.7 MJ/m²·día). Valida la entrada de más peso; no cuenta como prueba.</li>
    <li><b>Prueba 1, estaciones</b> (script 13). ETo Penman–Monteith (FAO-56) completa con Tmáx, Tmín y HR de cada estación, su Rs de
    Angstrom, presión por altura y viento medido en Mogotes-AUT a 10 m. Nuestra ETo se toma en la celda de ERA5-Land de cada
    estación. Sesgo: Mogotes −0.08 mm/día (−2.3 %), La Sierra +0.66 (+27.2 %), Charalá −0.16 (−4.5 %). Con el viento de
    ERA5-Land (sensibilidad) cambia 0.09 mm/día o menos.</li>
    <li><b>Prueba 2, TerraClimate pet</b> (script 16). Otra ETo de referencia (Penman–Monteith sobre pasto, en v1.1
    corregida por CO<sub>2</sub>), promedio de cuenca, 300 meses. Sesgo de nuestra ETo: +0.34 mm/día (+11.8 %),
    r = 0.97; 1 166 frente a 1 043 mm/año.</li>
    <li><b>Dispersión entre pruebas</b> (script 17). Sesgo % de las 4 series por mes calendario y tres formas de medir
    cuánto discrepan. <b>Definición elegida por Juan: rango entre las 2 pruebas</b>, |TerraClimate − media de las 3
    estaciones|, media 5.0 pp (1.2 a 8.5 según el mes). Es el umbral de la fase 4 y la banda de la fase 5.</li>
    <li><b>ETo frente a P − Q</b> (script 17). Nuestra ETo 1 166 mm/año en los 262 meses con caudal. P − Q es 884 mm/año
    con IMERG (PI) y 1 206 con pluviómetros (PL). Con PI, P − Q queda por debajo de la ETo en los 11 años completos; con
    PL queda 39 a 50 mm/año por encima, y en 6 de los 11 años. El plan pide, si ETo &lt; P − Q, revisar en este orden:
    representatividad de la lluvia, pérdidas subterráneas, aportes externos y una cobertura que evapore más que el pasto.</li>
    <li><b>Mes para verificar a mano</b> (script 18). <code>anexos/punto1/mes_estacion_a_mano.xlsx</code>: marzo de 2001
    en Mogotes, cada paso de FAO-56 como fórmula de Excel. La hoja reproduce el script 13 con diferencia máxima de
    0.0001 mm/día (recalculada con LibreOffice). Revisada por Juan el 20 nov: está bien.</li>
  </ol>
  <p><b>Celda de cada estación (20 nov).</b> Hasta el 20 de noviembre las estaciones se comparaban con el más cercano de los
  6 puntos de la cuenca. Juan pidió bajar la celda que contiene a cada estación (scripts 19 y 20) y rehacer todo con ella:
  las cifras de esta página ya son con esa celda. Antes: Rs +1.9 a +4.8 MJ/m²·día; ETo Mogotes −0.13, La Sierra +0.56,
  Charalá −0.15 mm/día; dispersión 6.8 pp. Referencias completadas: Abatzoglou et al.
  (2018) y Yang et al. (2019) en <code>anexos/referencias.md</code>. El artículo de 2018 dice «Penman–Monteith» y «pasto de
  referencia», sin albedo ni resistencia de superficie.</p>
</section>

<section>
  <h2>Fase 3 · Cómo leer las comparaciones con estaciones</h2>
  <p><b>Qué se pone a prueba.</b> En Rs, la radiación de ERA5-Land (ssrd), que sí es un producto de ERA5-Land. En ETo,
  <b>nuestra ETo</b>: la FAO-56 de este trabajo (scripts 01–04), calculada con forzantes de ERA5-Land. No es un
  producto de ERA5-Land; ERA5-Land solo le da las entradas.</p>
  <p><b>Sesgo = promedio de (lo que se prueba − la referencia)</b>, en los mismos días o meses. Rs: ERA5-Land − estación.
  ETo con estaciones: nuestra ETo − ETo de estación. ETo con TerraClimate: nuestra ETo − pet de TerraClimate. Positivo:
  lo que se prueba da más que la referencia; negativo, menos. El sesgo en % se divide por la media de la referencia. El RMSE es el tamaño típico del error de un
  día, sin signo: un sesgo pequeño con RMSE grande quiere decir que los errores de días distintos se compensan.</p>
  <p><b>Rs de estación: ecuación de Angstrom</b> (FAO-56 ec. 35, p. 50):
  Rs = (a<sub>s</sub> + b<sub>s</sub>·n/N)·Ra, con n = horas de brillo solar medidas, N = (24/π)·ω<sub>s</sub> las horas
  de luz posibles (ec. 34) y Ra la radiación extraterrestre (ec. 21, con ec. 23–25), las dos calculadas cada día con la
  latitud de la estación. a<sub>s</sub> = 0.25 es la fracción de Ra que llega en un día cubierto (n = 0) y
  a<sub>s</sub> + b<sub>s</sub> = 0.75 la que llega en un día despejado (n = N). Son los valores que FAO-56 recomienda
  sin calibración local; en la cuenca no hay radiación medida para calibrarlos, así que ese error queda dentro del sesgo.</p>
  <p><b>Viento de la ETo de estación: variantes (a) y (b).</b> Solo Mogotes-AUT mide viento; La Sierra y Charalá no.
  (a) es la variante final: media mensual de Mogotes-AUT medida a 10 m (Manual del Observador Meteorológico del IDEAM,
  GDI-M003, p. 37) y llevada a 2 m con la ec. 47 (u2 ≈ 0.75 m/s), usada en las tres estaciones. (b) usa el u2 diario de
  ERA5-Land de la celda de la estación: sensibilidad que quita el supuesto de llevar el viento de Mogotes-AUT a las otras estaciones, pero con el
  mismo viento en los dos lados la prueba ya no revisa el viento.</p>
</section>

<section>
  <h2>Fase 3 · Radiación de estaciones frente a ERA5-Land</h2>
  <p>Rs de Angstrom con el brillo solar diario del IDEAM. Cada estación se compara con el punto de ERA5-Land más
  cercano, en los mismos días. Sesgo de ERA5-Land = ERA5-Land − estación.</p>
  <div class="tabla" id="t-rs"></div>
  <div class="rejilla" id="r-rs"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Sesgo de ERA5-Land en Rs, por mes (ERA5-Land − estación)</h3><div class="grafico" id="g-rs-sesgo"></div></div>
</section>

<section>
  <h2>Fase 3 · Nuestra ETo frente a la ETo de estación</h2>
  <p>ETo Penman–Monteith (FAO-56) con Tmáx, Tmín y HR de estación, la Rs de Angstrom y la presión por altura. Viento: (a), la
  variante final, es la media mensual de Mogotes-AUT medida a 10 m (altura de los anemómetros del IDEAM, Manual del
  Observador Meteorológico) y llevada a 2 m con la ec. 47; (b), con el viento de ERA5-Land, queda como sensibilidad. Solo días con todas
  las entradas. Nuestra ETo se toma en la celda de ERA5-Land de la estación. Sesgo = nuestra ETo − ETo de estación.</p>
  <div class="tabla" id="t-eto"></div>
  <div class="rejilla" id="r-eto"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Sesgo de nuestra ETo, por mes (nuestra ETo − estación)</h3><div class="grafico" id="g-eto-sesgo"></div></div>
</section>

<section>
  <h2>Fase 3 · Segunda prueba: TerraClimate pet</h2>
  <p>La pet de TerraClimate v1.1 es una ETo de referencia, no una ETP: ASCE Penman–Monteith corregida por CO<sub>2</sub>
  (Yang et al., 2019), según el archivo («Reference Evapotranspiration») y la página del producto. Por eso sirve para
  probar nuestra ETo; GLEAM Ep y ERA5-Land pev son ETP y no. Se declaran dos diferencias: la corrección por
  CO<sub>2</sub>, y que en v1.1 sus anomalías mensuales vienen de ERA5, de donde salen también nuestros forzantes
  (ERA5-Land); así que no es independiente en la variabilidad (sí en la climatología, CHELSA y CRU, y en la resolución, ~4 km). Promedio de cuenca, 1998–2022,
  300 meses. <b>Sesgo = nuestra ETo − pet TerraClimate.</b> Script 16.</p>
  <div class="tabla" id="t-tc"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Serie mensual (mm/mes)</h3><div class="grafico" id="g-tc-serie"></div></div>
  <div class="dos">
    <div class="tarjeta"><h3>Ciclo anual (mm/mes)</h3><div class="grafico" id="g-tc-ciclo"></div></div>
    <div class="tarjeta"><h3>Sesgo de nuestra ETo, MAE y RMSE por mes (mm/mes)</h3><div class="grafico" id="g-tc-sesgo"></div></div>
  </div>
</section>

<section>
  <h2>Fase 3 · Dispersión entre pruebas y ETo frente a P − Q</h2>
  <p>Script 17. Las dos pruebas en mm/día: estaciones día a día (viento de Mogotes-AUT), TerraClimate mes a mes
  (cuenca). MAE y RMSE no son comparables entre las dos pruebas porque una es diaria y otra mensual; el sesgo % sí.
  Sesgo % = (nuestra ETo − referencia) / referencia.</p>
  <div class="tabla" id="t-cierre-pruebas"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Sesgo % de nuestra ETo por mes, cada serie de referencia</h3><div class="grafico" id="g-cierre-sesgo"></div></div>
  <p style="margin-top:16px"><b>Tres definiciones de dispersión, por mes (puntos porcentuales).</b> Rango de las 4 series:
  máximo − mínimo del sesgo % de las 3 estaciones y TerraClimate. Rango de 2 pruebas: |TerraClimate − media de las 3
  estaciones|, cada prueba cuenta una vez. Desviación estándar de las 4 series.
  <b>Elegida (Juan, 20 nov): rango de 2 pruebas</b>, columna <code>dispersion_pct</code> de
  <code>dispersion_pruebas.csv</code> (script 17); media 5.0 pp, de 1.2 a 8.5 según el mes.</p>
  <div class="tarjeta"><h3>Dispersión por mes (pp)</h3><div class="grafico" id="g-cierre-disp"></div></div>
  <p style="margin-top:16px"><b>ETo multianual frente a P − Q multianual</b> (mm/año), en los mismos meses o años.</p>
  <div class="tabla" id="t-cierre-balance"></div>
</section>

<section>
  <h2>Fase 3 · Series mensuales por estación</h2>
  <p>Rs y ETo mensuales: media de los días con todas las entradas de estación, en los mismos días para los dos lados. Mes vacío si tiene menos de 15 días con dato. Elige la estación; el zoom en el tiempo se sincroniza entre las dos gráficas.</p>
  <div class="controles" id="c-estacion"></div>
  <div class="tarjeta"><h3>Rs, media mensual (MJ/m²·día)</h3><div class="grafico" id="g-rs-diaria"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3>ETo, media mensual (mm/día)</h3><div class="grafico" id="g-eto-diaria"></div></div>
</section>

<section>
  <h2>ET real de la cuenca por producto</h2>
  <p>Promedio de cuenca ponderado por el área de cada celda dentro del polígono (MOD16: media de los píxeles en Earth
  Engine; TerraClimate: script 05). ERA5-Land mensual (e y pev) se corta en 2022-08: sep–dic de 2022 están dañados por
  el error de ECMWF (decisión del 2026-11-17). GLEAM Ep y ERA5-Land pev son evaporación potencial, no ET real; se
  muestran solo como referencia y no entran al periodo común. Script 14.</p>
  <div class="tabla" id="t-et-anual"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>ET real mensual (mm/mes)</h3><div class="grafico" id="g-et-mensual"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3 id="h-et-ciclo">Ciclo anual (mm/mes)</h3><div class="grafico" id="g-et-ciclo"></div></div>
</section>

<section>
  <h2>Balance hídrico: ET real = P − Q − ΔS</h2>
  <p>ET real que no depende de ningún modelo de ET: lluvia (PI = IMERG, PL = pluviómetros del IDEAM depurados, en
  paralelo), caudal observado en San Gil (CAMELS-COL, lámina sobre 2 098.85 km²) y agua en el suelo de ERA5-Land (4
  capas, 0–289 cm, 6 puntos con pesos de Voronoi). Camino principal: ciclo anual medio con los meses que tienen Q;
  comprobación: los años con los 12 meses de Q. Decisiones del 2026-11-19. Script 15.</p>
  <div class="tabla" id="t-balance"></div>
  <p id="p-balance-ds"></p>
  <div class="tarjeta" style="margin-top:16px"><h3>ET real del balance frente a los productos (mm/año)</h3><div class="grafico" id="g-balance-productos"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3>ET real del balance por año completo de Q, con ΔS (mm/año)</h3><div class="grafico" id="g-balance-anual"></div></div>
</section>

<section>
  <h2>Fase 4 · Métodos frente a una referencia de la misma superficie</h2>
  <p>Elegidos por Juan: Thornthwaite (programado paso a paso, script 22), Hargreaves, Priestley–Taylor, Makkink,
  Brutsaert–Stricker (AA) y Cenicafé. Mismos forzantes y periodo que la ETo (1998–2022), paso diario, cuenca por
  Voronoi. Script 21; ecuaciones y un día a mano en <code>anexos/ecuaciones_metodos.md</code>. Misma superficie (Juan, 22 nov): cada
  método se compara con una referencia de su misma superficie, sin calibrar. Hargreaves, Makkink, Cenicafé y Penman
  (forma FAO-24, que es ETo del pasto y no E0; con c = 0.8, el que recomienda FAO-24, que solo vale con tiempo en calma) frente a la ETo Penman–Monteith (FAO-56); Thornthwaite también, porque no tiene
  conversión (se declara); Priestley–Taylor (superficie húmeda) frente a Penman–Monteith (FAO-56) con rs = 0, con los mismos datos. La AA
  es ET real: no entra aquí y va a la fase 6. Sesgo % = (método − referencia)/referencia, media de los 12 meses
  calendario. «Meses sobre la dispersión»: cuántos de los 12 tienen |sesgo %| mayor que la dispersión entre pruebas de
  la fase 3.</p>
  <div class="tabla" id="t-metodos"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Media anual 1998–2022 de cada método, tal como es (mm/año)</h3><p style="margin:4px 0 0;font-size:14px;color:var(--tenue)">Agrupados por lo que estima cada método; el color dice qué variables usa. Al lado de cada barra, la diferencia con la ETo Penman–Monteith (FAO-56), que es la línea punteada. Su barra se parte en término radiativo (lleno) y aerodinámico (rayado). Pasa el cursor (o toca) para ver la diferencia con la ETo: verde por encima, rojo por debajo.</p><div class="grafico" id="g-metodos-grupos" style="height:600px"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Sesgo de cada método frente a su referencia, mes a mes, con la dispersión de la fase 3 (%)</h3><p style="margin:4px 0 0;font-size:14px;color:var(--tenue)">Sesgo % = (método − referencia)/referencia, media 1998–2022 de cada mes calendario. Referencia: ETo Penman–Monteith (FAO-56); para Priestley–Taylor, Penman–Monteith (FAO-56) con rs = 0. La franja gris es ± la dispersión elegida en la fase 3. Para cada mes calendario: dispersión = |sesgo % de nuestra ETo frente a la pet de TerraClimate − media del sesgo % frente a las 3 estaciones (Mogotes, La Sierra, Charalá)|, es decir, cuánto difieren entre sí las dos pruebas de la ETo (cada prueba cuenta una vez; Juan, 20 nov; script 17). Cambia por mes, media <span id="disp-media"></span> pp: un punto fuera de la franja se aleja de la referencia más de lo que difieren entre sí las pruebas de la ETo. Doble clic en la leyenda para ver un solo método.</p><div class="grafico" id="g-metodos-sesgo" style="height:520px"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Comparación 1 · Métodos de ETo y Thornthwaite frente a la ETo Penman–Monteith (FAO-56): ciclo anual medio (mm/mes)</h3><div class="grafico" id="g-metodos-ciclo-eto"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Comparación 2 · Priestley–Taylor frente a Penman–Monteith (FAO-56) con rs = 0 (superficie húmeda): ciclo anual medio (mm/mes)</h3><div class="grafico" id="g-metodos-ciclo-pt"></div></div>
  <p>La AA (ET real) se compara en la fase 6, con el balance P − Q y los productos.</p>
  <h3>Fase 5 · Explicación de las diferencias de los métodos de ETo (texto de Juan, 23 nov; borrador)</h3>
  <div id="texto-f4"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Fase 5 · Términos de la ETo Penman–Monteith (FAO-56) por mes (mm/mes)</h3><p style="margin:4px 0 0;font-size:14px;color:var(--tenue)">FAO-56 ec. 6 partida en sus dos sumandos, que comparten el denominador Δ + γ(1 + 0.34 u2): radiativo = 0.408 Δ (Rn − G); aerodinámico = γ · 900/(T + 273) · u2 · (es − ea). Media 1998–2022 de cada mes calendario, cuenca por Voronoi. El número encima de cada barra es la fracción aerodinámica del mes; al pasar el cursor, su mínimo y máximo entre los 25 años. Script 26.</p><div class="grafico" id="g-terminos-f5"></div></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Fase 5 · α* = ETo/Eeq por mes, con el déficit de vapor y el viento</h3><p style="margin:4px 0 0;font-size:14px;color:var(--tenue)">Eeq = Δ/(Δ+γ) · Rn/λ (evaporación de equilibrio; G = 0, λ = 2.45 MJ/kg), con los mismos Δ, γ y Rn de la ETo; es Priestley–Taylor / 1.26. Suma mensual en cada punto, cuenca por Voronoi; α* = cociente de los totales del mes, media 1998–2022 por mes calendario. La franja es el mínimo y el máximo de α* entre los 25 años. Eje derecho: déficit es − ea (kPa) y u2 (m/s), media del mes. Script 27. Para verificar a mano: punto 6, febrero de 2010 (hoja <code>metodos_mes_a_mano.xlsx</code>): Eeq 100.321, ETo 105.091 mm/mes, α* 1.0475.</p><div class="grafico" id="g-alfa"></div></div>
  <h3>Hargreaves de la Tarea 1 frente al de la Tarea 2</h3>
  <p>Pedido de Juan (22 nov). Misma fórmula en todas (FAO-56 ec. 52). Tarea 2: los 6 puntos, día local, promedio
  Voronoi (script 21). Tarea 1: T promedio de la cuenca de Earth Engine (día UTC) o T de MSWX de CAMELS-COL, Ra en el
  centroide. CAMELS-COL: su ETP publicada, que la Tarea 1 ya halló unas 2.75 veces más alta que la misma fórmula con sus
  mismas temperaturas. Script 23; reproduce el CSV de la Tarea 1. Solo los meses sin días faltantes en CAMELS-COL.</p>
  <div class="tabla" id="t-hargreaves-t1"></div>
  <div class="tarjeta" style="margin-top:16px"><h3>Hargreaves de la Tarea 1 y de la Tarea 2 frente a la ETo Penman–Monteith (FAO-56): ciclo anual medio (mm/mes)</h3><div class="grafico" id="g-hargreaves-t1"></div></div>
</section>

<section>
  <h2>Fase 6 · ET real por varios caminos</h2>
  <p>Script 24 (22 nov, Juan ausente: las decisiones marcadas «para revisar» están en <code>anexos/decisiones.md</code>).
  Tres preguntas: cuánto vale la ET real según el balance y con qué incertidumbre; cuánto se aparta cada producto del
  balance en los mismos meses; y si alguna cifra rompe el techo de energía (Rn/λ, la radiación neta real de ERA5-Land,
  no la del pasto) o la demanda (ETo Penman–Monteith (FAO-56)).</p>
  <h3>Incertidumbre del balance de largo plazo</h3>
  <p class="nota">σ_P = |PL − PI|/√2 (las dos lluvias como dos medidas con el mismo error). σ_Q = 13.1 % de Q (1σ):
  el error medio de la curva de gasto al 95 %, 25.6 %, de Di Baldassarre y Montanari (2009,
  <a href="https://doi.org/10.5194/hess-13-913-2009">doi:10.5194/hess-13-913-2009</a>), tratado como sistemático.
  Sensibilidad: un aforo (5.3 % al 95 %) y el máximo del estudio (42.8 %).</p>
  <div class="tabla" id="t-f6-incert"></div>
  <div class="cifras" id="f6-cifras"></div>
  <div class="tarjeta" style="margin-top:20px"><h3>Cada producto frente al balance, en los mismos meses (mm/año)</h3>
    <p class="nota" style="margin:4px 0 0">Banda azul: P − Q con PL ± σ; banda naranja: con PI ± σ. Línea punteada:
    ETo Penman–Monteith (FAO-56); línea continua: Rn/λ de ERA5-Land. Cada barra se compara con el balance de sus mismos
    meses; las bandas son las del largo plazo (los meses cambian poco el balance, salvo SSEBop v6.1, que solo tiene 2012–2022).</p>
    <div class="grafico" id="g-f6-productos" style="height:460px"></div></div>
  <div class="tabla" id="t-f6-frente" style="margin-top:12px"></div>
  <div class="tarjeta" style="margin-top:20px"><h3>Ciclo anual medio: techo de energía, demanda, balance y productos (mm/mes)</h3>
    <p class="nota" style="margin:4px 0 0">P − Q mensual no es ET mensual: el agua que entra en un mes puede salir por
    el río en otro. Se muestra solo para ver la forma del ciclo.</p>
    <div class="grafico" id="g-f6-ciclo" style="height:440px"></div></div>
  <div class="tarjeta" style="margin-top:20px"><h3>P − Q por año (años con los 12 meses de Q), con ± σ_ET (mm/año)</h3>
    <div class="controles" id="c-f6-anio"></div>
    <div class="grafico" id="g-f6-anual" style="height:440px"></div></div>
  <h3 style="margin-top:20px">Años marcados (solo se señalan; no se explican)</h3>
  <p class="nota">Marcas: P − Q negativo; mayor que Rn/λ; mayor que la ETo; fuera del rango de los productos; a más de
  1σ de la mediana de los productos (ERA5-Land e, GLEAM, MOD16, TerraClimate, SSEBop y AA con los 12 meses ese año).</p>
  <div class="tabla" id="t-f6-marcas"></div>
</section>

<section>
  <h2>Fase 4 · Métodos disponibles en las notas del curso</h2>
  <p>Solo métodos de la sección «Caja de herramientas» y afines de las notas de C. D. Hoyos. Datos: ERA5-Land horario
  en 6 puntos (t2m, d2m, sp, u10, v10, ssrd), Rn FAO-56, estaciones DHIME, brillo solar. Quedan fuera las mediciones
  (lisímetro, covarianza de remolinos), los modelos satelitales (ya están como productos) y Budyko (fase 7).
  Pendiente: elección de Juan (4 de la tabla del enunciado + 2 de fuera).</p>
  <div class="metodos"><table>
    <tr><th>Familia</th><th>Método</th><th>Variables</th><th>¿Las tenemos?</th><th>Recomendación</th></tr>
    <tr><td>Tabla · temperatura</td><td>Thornthwaite (1948)</td><td>T media mensual, latitud (horas de sol N)</td><td class="si">Sí</td><td><b>Recomendado.</b> Mensual; hace falta en la fase 8.</td></tr>
    <tr><td>Tabla · temperatura</td><td>Hamon (1961)</td><td>T media, duración del día D</td><td class="si">Sí</td><td>Alternativa a Thornthwaite.</td></tr>
    <tr><td>Tabla · T + Ra</td><td>Hargreaves–Samani (1985)</td><td>Tmáx, Tmín, T media, Ra</td><td class="si">Sí (ya está en la Tarea 1)</td><td><b>Recomendado.</b> Recalcular con los 6 puntos y el mismo periodo que la ETo.</td></tr>
    <tr><td>Tabla · T + Ra</td><td>Oudin (2005)</td><td>T media, Ra</td><td class="si">Sí</td><td>Alternativa a Hargreaves.</td></tr>
    <tr><td>Tabla · radiación</td><td>Priestley–Taylor (1972)</td><td>Rn, G, T (Δ, γ con presión)</td><td class="si">Sí (Rn FAO-56 ya calculada)</td><td><b>Recomendado</b>, α = 1.26.</td></tr>
    <tr><td>Tabla · transferencia de masa</td><td>Meyer (1915)</td><td>es(Ts) − ea, viento a 9 m</td><td class="si">Sí, con T del aire en vez de la del agua (declararlo)</td><td><b>Recomendado</b>: la página da sus constantes; Dalton solo da f(u) genérica.</td></tr>
    <tr><td>Tabla · transferencia de masa</td><td>Dalton (1802)</td><td>f(u), es(Ts) − ea</td><td class="no">Falta la forma de f(u)</td><td>No: sin constantes en las notas.</td></tr>
    <tr><td>Fuera · radiación</td><td>Makkink (1957) / de Bruin</td><td>Rs, T</td><td class="si">Sí (ssrd)</td><td><b>Recomendado</b>: las notas lo sugieren para clima húmedo.</td></tr>
    <tr><td>Fuera · radiación</td><td>Turc (1961)</td><td>Rs, T, HR</td><td class="si">Sí</td><td>Alternativa a Makkink.</td></tr>
    <tr><td>Fuera · radiación</td><td>Jensen–Haise (1963), Abtew (1996)</td><td>Rs, T</td><td class="si">Sí</td><td>No: calibrados en zona árida y humedales de Florida.</td></tr>
    <tr><td>Fuera · combinación</td><td>Penman (1948), agua libre</td><td>Rn, T, ea, viento</td><td class="si">Sí</td><td>En la forma de FAO-24 (la que usamos) con la Rn del pasto da ETo, no E0 (corregido el 22 nov); se usa c = 0.8. Va dentro de la relación complementaria.</td></tr>
    <tr><td>Fuera · relación complementaria</td><td>Brutsaert–Stricker (1979), AA</td><td>Penman + Priestley–Taylor</td><td class="si">Sí</td><td><b>Recomendado</b>: estima ET real, comparable con GLEAM, MOD16 y SSEBop (fase 6).</td></tr>
    <tr><td>Fuera · temperatura</td><td>Blaney–Criddle (1950 / FAO-24)</td><td>T, % de horas de luz, K o c</td><td class="no">T sí; c sale de ábacos</td><td>No: c de ábaco no es reproducible.</td></tr>
    <tr><td>Fuera · temperatura</td><td>Linacre (1977)</td><td>T, Td, latitud, altitud</td><td class="si">Sí</td><td>Posible; es un Penman simplificado para agua libre.</td></tr>
    <tr><td>Fuera · tanque</td><td>Tanque clase A × Kp</td><td>Evaporación de tanque, viento, HR, fetch</td><td class="no">Tanque DHIME con unidades imposibles</td><td>No.</td></tr>
    <tr><td>Fuera · combinación</td><td>ASCE-EWRI (2005), FAO-56 horaria</td><td>Lo mismo que FAO-56</td><td class="si">Sí</td><td>No: es la misma familia que la referencia.</td></tr>
  </table></div>
</section>

<section>
  <h2>Auditoría de citas (2026-11-21)</h2>
  <p>Cada cita del punto 1 tiene DOI o enlace en <code>anexos/referencias.md</code>, con lo que se leyó. Los métodos de
  la fase 4 los revisó su propio hilo. Detalle en <code>anexos/decisiones.md</code>.</p>
  <div class="tabla"><table>
    <tr><th>Fuente</th><th>Lo que afirmamos</th><th>¿Lo dice?</th></tr>
    <tr><td>FAO-56 (Allen et al., 1998)</td><td>Números de ecuación; a_s = 0.25, b_s = 0.50; 2 m/s sin viento; ec. 47 sobre pasto corto</td><td class="si">Sí (Rs/Rso ≤ 1.0 en la ec. 39, ya aplicado)</td></tr>
    <tr><td>IDEAM GDI-M003 v03, p. 37</td><td>Sensores de viento a 10 m</td><td class="si">Sí: «en el territorio colombiano… a una altura de 10 m»</td></tr>
    <tr><td>ASCE-EWRI (2005), p. 20</td><td>Límite 0.3 &lt; Rs/Rso ≤ 1.0</td><td class="si">Sí (lectura parcial del PDF)</td></tr>
    <tr><td>Abatzoglou et al. (2018)</td><td>pet Penman-Monteith, pasto de referencia</td><td class="si">Sí; no da altura, albedo ni resistencia</td></tr>
    <tr><td>TerraClimate v1.1 (página)</td><td>pet ASCE corregida por CO2; anomalías de ERA5</td><td class="si">Sí. Pero el script 05 y el meta.json de la pet dicen FAO-56</td></tr>
    <tr><td>Yang et al. (2019)</td><td>rs depende del CO2</td><td class="si">Sí, en el resumen; texto de pago</td></tr>
    <tr><td>Aviso de ECMWF</td><td>ERA5-Land mensual dañado desde sep. 2022</td><td class="si">Sí (sep. 2022 a feb. 2024, variables acumuladas)</td></tr>
    <tr><td>SSEBop v6.1 y v5</td><td>DOI P9QJWQ6K y F72V2F1F; Senay et al. 2023</td><td class="no">Sin confirmar: las fichas no abrieron</td></tr>
    <tr><td>MOD16A2GF</td><td>Running et al. (2021)</td><td class="no">DOI sí; autores y año sin confirmar</td></tr>
    <tr><td>Jensen–Haise (1963)</td><td>Calibrado en zona árida</td><td class="no">Sin confirmar</td></tr>
  </table></div>
</section>

<footer>
  <p>Fase 6: <code>productos/punto1/et_*.csv</code> (script 24).</p>
  <p>Balance hídrico: <code>productos/punto1/balance_hidrico_*.csv</code> (script 15).</p>
  <p>ET real: <code>productos/punto1/et_real_mensual_productos.csv</code> y <code>et_real_anual_productos.csv</code>
  (script 14).</p>
  <p>Fase 3: salidas de <code>codigo/punto1/12_rs_brillo_solar_vs_era5land.py</code> y
  <code>13_eto_estaciones_vs_era5land.py</code> en <code>productos/punto1/</code>.</p>
  <p>Generado por <code>temp/graficas_series_horarias.py</code> a partir de <code>datos/punto1/era5land_puntos/</code>,
  <code>productos/punto1/eto_mensual_cuenca.csv</code> y la ETP de Hargreaves de la Tarea 1. Conversiones solo de
  unidades: K → °C, Pa → kPa, ssrd J/m² en la hora → W/m² (÷ 3600).</p>
</footer>
</div>
<script>
const CARGA = __CARGA__;
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const OPCIONES = {scrollZoom: true, displaylogo: false, responsive: true};
// Colores: Okabe–Ito para los 6 puntos; la ETP de Hargreaves con el color de la ETP en el informe de la Tarea 1.
const COLOR_PUNTO = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9'];
const COLOR = {eto: '#1B6A80', hargreaves: '#7C5BC7', radiativa: '#E69F00', aerodinamica: '#56B4E9'};

function base(unidad) {
  const tinta = css('--tinta'), tenue = css('--tenue'), linea = css('--linea');
  return {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: 'IBM Plex Mono, ui-monospace, monospace', size: 11, color: tinta},
    margin: {t: 36, r: 10, b: 36, l: 54}, hovermode: 'x unified', showlegend: true,
    legend: {orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'left', x: 0, font: {size: 10.5}},
    xaxis: {type: 'date', gridcolor: linea, zeroline: false, linecolor: linea, tickcolor: linea, tickfont: {color: tenue}},
    yaxis: {gridcolor: linea, zeroline: false, linecolor: linea, tickcolor: linea, tickfont: {color: tenue},
            title: {text: unidad, font: {size: 11, color: tenue}}}
  };
}

// Encabezado: cifras calculadas en Python.
for (const [valor, texto] of CARGA.cifras) {
  const d = document.createElement('div'); d.className = 'cifra';
  d.innerHTML = `<b>${valor}</b><span>${texto}</span>`;
  document.getElementById('cifras').appendChild(d);
}

// ETo mensual.
(() => {
  const M = CARGA.mensual, x = M.meses.map(m => m + '-01');
  const l1 = base('mm/mes'); l1.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-comparacion', [
    {type: 'scatter', mode: 'lines', name: 'ETo Penman–Monteith', x, y: M.eto, line: {color: COLOR.eto, width: 2}},
    {type: 'scatter', mode: 'lines', name: 'ETP Hargreaves', x, y: M.hargreaves, line: {color: COLOR.hargreaves, width: 1.6, dash: 'dot'}}],
    l1, OPCIONES);
  const l2 = base('mm/mes'); l2.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-terminos', [
    {type: 'scatter', mode: 'lines', stackgroup: 'eto', name: 'Radiativo', x, y: M.radiativa, line: {color: COLOR.radiativa, width: 1}},
    {type: 'scatter', mode: 'lines', stackgroup: 'eto', name: 'Aerodinámico', x, y: M.aerodinamica, line: {color: COLOR.aerodinamica, width: 1}}],
    l2, OPCIONES);
})();

// ---------- Fase 3 ----------
(() => {
  const F = CARGA.fase3, MESES = ['E','F','M','A','M','J','J','A','S','O','N','D'], xm = [1,2,3,4,5,6,7,8,9,10,11,12];
  const COLOR_EST = ['#0072B2', '#D55E00', '#009E73'];
  const C = {estacion: '#1B6A80', era5: '#C8553D', b: '#5A9E6F'};
  const fmt = (v, d = 2) => (v > 0 ? '+' : '') + v.toFixed(d);
  const ejeMes = l => { l.xaxis = Object.assign(l.xaxis, {type: 'linear', tickvals: xm, ticktext: MESES}); l.hovermode = 'x unified'; return l; };
  const tabla = (id, cab, filas) => { document.getElementById(id).innerHTML =
    `<table><thead><tr>${cab.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>` +
    filas.map(f => `<tr>${f.map(c => `<td>${c}</td>`).join('')}</tr>`).join('') + '</tbody></table>'; };
  const tarjeta = (cont, titulo) => { const t = document.createElement('div'); t.className = 'tarjeta';
    t.innerHTML = `<h3>${titulo}</h3>`; const g = document.createElement('div'); g.className = 'grafico';
    t.appendChild(g); document.getElementById(cont).appendChild(t); return g; };

  tabla('t-rs', ['Estación', 'Celda ERA5 (lat, lon)', 'Distancia', 'Estación − celda DEM', 'Días', 'Sesgo de ERA5-Land (MJ/m²·día)', 'Sesgo %', 'RMSE diario'],
    F.map(e => [e.nombre, e.punto, e.distancia_km.toFixed(1) + ' km', fmt(e.dz_celda_m, 0) + ' m', e.rs.dias,
                fmt(e.rs.sesgo_total), fmt(e.rs.sesgo_pct, 1), e.rs.rmse.toFixed(2)]));
  tabla('t-eto', ['Estación', 'Días', 'Sesgo de nuestra ETo (a), mm/día', 'Sesgo (a) %', 'RMSE (a)', 'Sesgo (b), mm/día', 'Sesgo (b) %', 'RMSE (b)'],
    F.map(e => { const a = e.eto.resumen.mogotes_aut, b = e.eto.resumen.era5land;
      return [e.nombre, a.dias, fmt(a.sesgo), fmt(a.pct, 1), a.rmse.toFixed(2), fmt(b.sesgo), fmt(b.pct, 1), b.rmse.toFixed(2)]; }));

  F.forEach(e => {
    Plotly.newPlot(tarjeta('r-rs', e.nombre), [
      {type: 'scatter', mode: 'lines+markers', name: 'Estación (Angstrom)', x: xm, y: e.rs.estacion, line: {color: C.estacion}},
      {type: 'scatter', mode: 'lines+markers', name: `ERA5-Land (celda ${e.punto})`, x: xm, y: e.rs.era5, line: {color: C.era5, dash: 'dash'}}],
      ejeMes(base('MJ/m²·día')), OPCIONES);
    Plotly.newPlot(tarjeta('r-eto', e.nombre), [
      {type: 'scatter', mode: 'lines+markers', name: 'Estación (a)', x: xm, y: e.eto.a, line: {color: C.estacion}},
      {type: 'scatter', mode: 'lines+markers', name: 'Estación (b)', x: xm, y: e.eto.b, line: {color: C.b, dash: 'dot'}},
      {type: 'scatter', mode: 'lines+markers', name: `Nuestra ETo (celda ${e.punto})`, x: xm, y: e.eto.era5, line: {color: C.era5, dash: 'dash'}}],
      ejeMes(base('mm/día')), OPCIONES);
  });
  Plotly.newPlot('g-rs-sesgo', F.map((e, k) => ({type: 'scatter', mode: 'lines+markers', name: e.nombre, x: xm, y: e.rs.sesgo,
    line: {color: COLOR_EST[k]}})), ejeMes(base('MJ/m²·día')), OPCIONES);
  Plotly.newPlot('g-eto-sesgo', F.flatMap((e, k) => [
    {type: 'scatter', mode: 'lines+markers', name: e.nombre + ' (a)', x: xm, y: e.eto.sesgo_a, line: {color: COLOR_EST[k]}},
    {type: 'scatter', mode: 'lines+markers', name: e.nombre + ' (b)', x: xm, y: e.eto.sesgo_b, line: {color: COLOR_EST[k], dash: 'dot'}}]),
    ejeMes(base('mm/día')), OPCIONES);

  // Series diarias con selector de estación y zoom sincronizado
  const dibujar = k => {
    const e = F[k];
    const l1 = base('MJ/m²·día'); l1.hovermode = 'closest';
    Plotly.react('g-rs-diaria', [
      {type: 'scatter', mode: 'lines', name: 'Estación (Angstrom)', x: e.diaria_rs.fecha, y: e.diaria_rs.estacion, line: {color: C.estacion, width: 1.5}},
      {type: 'scatter', mode: 'lines', name: `ERA5-Land (celda ${e.punto})`, x: e.diaria_rs.fecha, y: e.diaria_rs.era5, line: {color: C.era5, width: 1.5}}],
      l1, OPCIONES);
    const l2 = base('mm/día'); l2.hovermode = 'closest';
    Plotly.react('g-eto-diaria', [
      {type: 'scatter', mode: 'lines', name: 'Estación (a)', x: e.diaria_eto.fecha, y: e.diaria_eto.a, line: {color: C.estacion, width: 1.5}},
      {type: 'scatter', mode: 'lines', name: 'Estación (b)', x: e.diaria_eto.fecha, y: e.diaria_eto.b, line: {color: C.b, width: 1.5}, visible: 'legendonly'},
      {type: 'scatter', mode: 'lines', name: `Nuestra ETo (celda ${e.punto})`, x: e.diaria_eto.fecha, y: e.diaria_eto.era5, line: {color: C.era5, width: 1.5}}],
      l2, OPCIONES);
  };
  F.forEach((e, k) => { const b = document.createElement('button'); b.textContent = e.nombre; b.setAttribute('aria-pressed', String(k === 0));
    b.onclick = () => { document.querySelectorAll('#c-estacion button').forEach(o => o.setAttribute('aria-pressed', String(o === b))); dibujar(k); };
    document.getElementById('c-estacion').appendChild(b); });
  dibujar(0);
  let enSincronia = false;
  const pares = [['g-rs-diaria', 'g-eto-diaria'], ['g-eto-diaria', 'g-rs-diaria']];
  pares.forEach(([a, b]) => document.getElementById(a).on('plotly_relayout', ev => {
    if (enSincronia) return; const cambio = {};
    if (ev['xaxis.range[0]'] !== undefined) cambio['xaxis.range'] = [ev['xaxis.range[0]'], ev['xaxis.range[1]']];
    else if (ev['xaxis.autorange']) cambio['xaxis.autorange'] = true; else return;
    enSincronia = true; Plotly.relayout(b, cambio).then(() => { enSincronia = false; });
  }));
})();

// ---------- Fase 3, segunda prueba: TerraClimate pet ----------
(() => {
  const T = CARGA.prueba_tc, R = T.resumen, MESES = ['E','F','M','A','M','J','J','A','S','O','N','D'], xm = [1,2,3,4,5,6,7,8,9,10,11,12];
  const ejeMes = l => { l.xaxis = Object.assign(l.xaxis, {type: 'linear', tickvals: xm, ticktext: MESES}); l.hovermode = 'x unified'; return l; };
  const mas = v => (v > 0 ? '+' : '') + v;
  document.getElementById('t-tc').innerHTML = '<table><thead><tr><th>Nuestra ETo (mm/año)</th><th>pet TerraClimate (mm/año)</th>' +
    '<th>Sesgo de nuestra ETo (mm/mes)</th><th>Sesgo %</th><th>MAE</th><th>RMSE</th><th>r mensual</th></tr></thead><tbody><tr>' +
    [R.anual_eto, R.anual_pet, mas(R.sesgo), mas(R.pct), R.mae, R.rmse, R.r].map(v => `<td>${v}</td>`).join('') + '</tr></tbody></table>';
  const x = T.meses.map(m => m + '-01');
  Plotly.newPlot('g-tc-serie', [
    {type: 'scatter', mode: 'lines', name: 'ETo Penman–Monteith (FAO-56) (este trabajo)', x, y: T.eto, line: {color: COLOR.eto, width: 1.6}},
    {type: 'scatter', mode: 'lines', name: 'pet TerraClimate v1.1', x, y: T.pet, line: {color: '#CC79A7', width: 1.6, dash: 'dash'}}],
    base('mm/mes'), OPCIONES);
  const lc = ejeMes(base('mm/mes')); lc.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-tc-ciclo', [
    {type: 'scatter', mode: 'lines+markers', name: 'ETo Penman–Monteith (FAO-56) (este trabajo)', x: xm, y: T.ciclo_eto, line: {color: COLOR.eto}},
    {type: 'scatter', mode: 'lines+markers', name: 'pet TerraClimate', x: xm, y: T.ciclo_pet, line: {color: '#CC79A7', dash: 'dash'}}], lc, OPCIONES);
  const ls = ejeMes(base('mm/mes')); ls.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-tc-sesgo', [
    {type: 'bar', name: 'Sesgo de nuestra ETo', x: xm, y: T.sesgo, marker: {color: COLOR.eto}},
    {type: 'scatter', mode: 'lines+markers', name: 'MAE', x: xm, y: T.mae, line: {color: COLOR.radiativa}},
    {type: 'scatter', mode: 'lines+markers', name: 'RMSE', x: xm, y: T.rmse, line: {color: COLOR.hargreaves, dash: 'dot'}}], ls, OPCIONES);
})();

// ---------- Fase 3, cierre: dispersión y ETo frente a P − Q ----------
(() => {
  const K = CARGA.cierre_f3, MESES = ['E','F','M','A','M','J','J','A','S','O','N','D'], xm = [1,2,3,4,5,6,7,8,9,10,11,12];
  const ejeMes = l => { l.xaxis = Object.assign(l.xaxis, {type: 'linear', tickvals: xm, ticktext: MESES}); l.hovermode = 'x unified'; return l; };
  const mas = v => (v > 0 ? '+' : '') + v;
  const NOMBRE = {estacion_mogotes: 'Mogotes', estacion_la_sierra: 'La Sierra', estacion_charala: 'Charalá',
                  terraclimate_pet: 'TerraClimate pet', media_estaciones: 'Media de las 3 estaciones'};
  const tabla = (id, cab, filas) => { document.getElementById(id).innerHTML =
    `<table><thead><tr>${cab.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>` +
    filas.map(f => `<tr>${f.map(c => `<td>${c}</td>`).join('')}</tr>`).join('') + '</tbody></table>'; };
  tabla('t-cierre-pruebas', ['Referencia', 'Base', 'n', 'Nuestra ETo (mm/día)', 'Referencia (mm/día)', 'Sesgo (mm/día)', 'Sesgo %', 'MAE', 'RMSE'],
    K.anual.map(r => [NOMBRE[r.serie], r.base, r.n, r.eto_nuestra_mm_dia, r.referencia_mm_dia, mas(r.sesgo_mm_dia), mas(r.sesgo_pct), r.mae_mm_dia, r.rmse_mm_dia]));
  const colores = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#555'];
  Plotly.newPlot('g-cierre-sesgo', Object.entries(K.sesgo).map(([k, y], i) => ({type: 'scatter', mode: 'lines+markers',
    name: NOMBRE[k], x: xm, y, line: {color: colores[i % colores.length], dash: k === 'media_estaciones' ? 'dot' : 'solid'}})),
    ejeMes(base('%')), OPCIONES);
  const ND = {rango_4_series_pct: 'Rango de las 4 series', rango_2_pruebas_pct: 'Rango de 2 pruebas', desv_est_4_series_pct: 'Desv. estándar de las 4 series'};
  const ld = ejeMes(base('pp')); ld.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-cierre-disp', Object.entries(K.dispersion).map(([k, y], i) => ({type: 'scatter', mode: 'lines+markers',
    name: `${ND[k]} (media ${K.dispersion_media[k]})`, x: xm, y, line: {color: colores[i]}})), ld, OPCIONES);
  tabla('t-cierre-balance', ['Camino', 'n', 'Nuestra ETo', 'P − Q (PI)', 'P − Q (PL)', 'ETo − (P − Q), PI', 'ETo − (P − Q), PL', 'Años con P − Q &gt; ETo, PI', 'Ídem, PL'],
    K.balance.map(b => [b.camino, `${b.n} ${b.unidad_n}`, b.eto_mm_anio, b.p_menos_q_PI_mm_anio, b.p_menos_q_PL_mm_anio,
      mas(b.eto_menos_p_menos_q_PI_mm_anio), mas(b.eto_menos_p_menos_q_PL_mm_anio),
      `${b.anios_con_p_menos_q_mayor_que_eto_PI} de 11`, `${b.anios_con_p_menos_q_mayor_que_eto_PL} de 11`]));
})();

// ---------- Fase 2, auditoría y ET real ----------
(() => {
  const F = CARGA.fase2, MESES = ['E','F','M','A','M','J','J','A','S','O','N','D'], xm = [1,2,3,4,5,6,7,8,9,10,11,12];
  const ejeMes = l => { l.xaxis = Object.assign(l.xaxis, {type: 'linear', tickvals: xm, ticktext: MESES}); l.hovermode = 'x unified'; return l; };
  const tabla = (id, cab, filas) => { document.getElementById(id).innerHTML =
    `<table><thead><tr>${cab.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>` +
    filas.map(f => `<tr>${f.map(c => `<td>${c}</td>`).join('')}</tr>`).join('') + '</tbody></table>'; };
  const fmt = (v, d) => (v > 0 ? '+' : '') + v.toFixed(d);

  const l1 = ejeMes(base('mm/mes')); l1.barmode = 'stack'; l1.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-f2-terminos', [
    {type: 'bar', name: 'Radiativo', x: xm, y: F.ciclo.radiativa, marker: {color: COLOR.radiativa}},
    {type: 'bar', name: 'Aerodinámico', x: xm, y: F.ciclo.aerodinamica, marker: {color: COLOR.aerodinamica}}], l1, OPCIONES);
  const alt = Object.fromEntries(F.alturas.map(a => [String(a.punto), a.z_celda_dem_m]));
  const l2 = ejeMes(base('mm/mes')); l2.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-f2-puntos', [
    ...Object.entries(F.ciclo_puntos).map(([n, y], k) => ({type: 'scatter', mode: 'lines+markers', name: `P${n} (${Math.round(alt[n])} m)`,
      x: xm, y, line: {color: COLOR_PUNTO[k], width: 1.3}, marker: {size: 4}})),
    {type: 'scatter', mode: 'lines', name: 'Cuenca', x: xm, y: F.ciclo.eto, line: {color: css('--tinta'), width: 3}}], l2, OPCIONES);
  const C = F.comprobacion;
  Plotly.newPlot('g-f2-comprobacion', [
    {type: 'scatter', mode: 'lines', x: xm, y: C.max, line: {width: 0}, showlegend: false, hoverinfo: 'skip'},
    {type: 'scatter', mode: 'lines', name: 'Rango de los 25 años', x: xm, y: C.min, fill: 'tonexty', fillcolor: 'rgba(27,106,128,0.18)', line: {width: 0}},
    {type: 'scatter', mode: 'lines+markers', name: 'Diferencia total, media', x: xm, y: C.media, line: {color: COLOR.eto, width: 2.4}},
    {type: 'scatter', mode: 'lines+markers', name: 'Parte de agregar (G = 0)', x: xm, y: C.agregar, line: {color: COLOR.radiativa, dash: 'dash'}},
    {type: 'scatter', mode: 'lines+markers', name: 'Parte de G (ec. 43)', x: xm, y: C.g, line: {color: COLOR.hargreaves, dash: 'dot'}}],
    ejeMes(base('% de la suma de diarias')), OPCIONES);
  tabla('t-f2-alturas', ['Punto', 'z celda DEM (m)', 'z región DEM (m)', 'z modelo (m)', 'Modelo − región (m)', 'Efecto en T (°C)', 'Efecto en ea (kPa)'],
    F.alturas.map(a => [a.punto, Math.round(a.z_celda_dem_m), Math.round(a.z_region_dem_m), Math.round(a.z_modelo_m),
      fmt(a.modelo_menos_region_m, 0), fmt(a.efecto_t_era5land_C, 2), fmt(a.efecto_ea_era5land_kPa, 3)]));

  const cerradas = F.auditoria.filter(a => a.cerrada).length;
  document.getElementById('p-auditoria').textContent =
    `${cerradas} de ${F.auditoria.length} casillas cerradas. Cada casilla comprueba que su archivo exista al generar este documento.`;
  tabla('t-auditoria', ['#', 'Casilla', 'Estado', 'Evidencia'], F.auditoria.map((a, i) =>
    [i + 1, a.casilla, a.cerrada ? '✓ cerrada' : '✗ falta ' + a.faltan.join(', '), a.evidencia]));
  document.querySelectorAll('#t-auditoria td').forEach(td => { td.style.whiteSpace = 'normal'; td.style.textAlign = 'left'; });

  const E = CARGA.et_real, claves = Object.keys(E.nombres);
  const COLOR_PROD = {era5land_e: '#0072B2', gleam_E: '#009E73', mod16a2gf: '#D55E00', terraclimate_aet: '#CC79A7',
    ssebop_v61: '#E69F00', ssebop_v5: '#8C6D31', gleam_Ep: '#009E73', era5land_pev: '#0072B2'};
  const potencial = c => c === 'gleam_Ep' || c === 'era5land_pev';
  tabla('t-et-anual', ['Producto', 'Años completos', 'Media anual, su periodo (mm)', `Media anual, ${E.periodo_comun} (mm)`],
    E.anual.map(a => [a.producto, a.anios, a.propio, a.comun]));
  const xs = E.meses.map(m => m + '-01');
  const lm = base('mm/mes'); lm.hovermode = 'x unified';
  Plotly.newPlot('g-et-mensual', claves.map(c => ({type: 'scatter', mode: 'lines', name: E.nombres[c], x: xs, y: E.series[c],
    line: {color: COLOR_PROD[c], width: potencial(c) ? 1 : 1.5, dash: potencial(c) ? 'dot' : 'solid'},
    visible: c === 'era5land_pev' ? 'legendonly' : true})), lm, OPCIONES);
  document.getElementById('h-et-ciclo').textContent = `Ciclo anual, media ${E.periodo_comun} (mm/mes)`;
  const lc = ejeMes(base('mm/mes')); lc.yaxis.rangemode = 'tozero';
  Plotly.newPlot('g-et-ciclo', claves.map(c => ({type: 'scatter', mode: 'lines+markers', name: E.nombres[c], x: xm, y: E.ciclo[c],
    line: {color: COLOR_PROD[c], dash: potencial(c) ? 'dot' : 'solid'}, marker: {size: 4},
    visible: c === 'era5land_pev' ? 'legendonly' : true})), lc, OPCIONES);


  const MT = CARGA.metodos;
  tabla('t-metodos', ['Método', 'Estima', 'Se compara con', 'Media anual (mm)', 'Sesgo % (rango)', 'MAE (mm/mes)', 'RMSE (mm/mes)',
    'Meses sobre la dispersión', 'Error de amplitud %', 'Desfase del máx. / mín. (meses)'],
    [['ETo Penman–Monteith (FAO-56)', 'ETo', 'referencia', MT.eto_anual, '—', '—', '—', '—', '—', '—'],
     ['Penman–Monteith (FAO-56) con rs = 0', 'ETP superficie húmeda', 'referencia', MT.anual['Penman–Monteith (FAO-56) con rs = 0'], '—', '—', '—', '—', '—', '—'],
     ...MT.resumen.map(r => [r.metodo, r.cantidad, r.referencia, r.anual,
      `${fmt(r.sesgo, 1)} (${fmt(r.sesgo_min, 1)} a ${fmt(r.sesgo_max, 1)})`, r.mae.toFixed(1), r.rmse.toFixed(1),
      `${r.supera} de 12`, fmt(r.error_amplitud_pct, 1), `${r.error_fase_maximo_meses} / ${r.error_fase_minimo_meses}`]),
     ['Brutsaert–Stricker (AA)', 'ET real', 'fase 6 (balance, GLEAM)', MT.anual['Brutsaert–Stricker (AA)'], '—', '—', '—', '—', '—', '—']]);
  const NOMBRE_M = {eto_fao56: 'ETo Penman–Monteith (FAO-56)', thornthwaite: 'Thornthwaite', hargreaves: 'Hargreaves', priestley_taylor: 'Priestley–Taylor', makkink: 'Makkink',
    penman_fao24: 'Penman (FAO-24)', aa_brutsaert_stricker: 'AA (ET real)', cenicafe_2006: 'Cenicafé 2006', eto_fao56_rs0: 'Penman–Monteith (FAO-56) con rs = 0'};
  const COLOR_M = {eto_fao56: css('--tinta'), thornthwaite: '#A65E1A', hargreaves: '#7C5BC7', priestley_taylor: '#E69F00', makkink: '#009E73',
    penman_fao24: '#56B4E9', aa_brutsaert_stricker: '#D55E00', cenicafe_2006: '#CC79A7', eto_fao56_rs0: '#0072B2'};
  // Los métodos tal como son (Juan, 22 nov): agrupados en el eje por la cantidad que estiman (con un encabezado por
  // bloque); el color dice las variables que usan. La línea punteada es la ETo Penman–Monteith (FAO-56); la barra de
  // la ETo se parte en término radiativo (lleno) y aerodinámico (rayado).
  const PM = 'ETo Penman–Monteith (FAO-56)', P = MT.eto_partes;
  const miles = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const BLOQUES = [
    ['ETo · pasto de referencia', [PM, 'Penman (FAO-24, c = 0.8)', 'Makkink', 'Hargreaves–Samani', 'Cenicafé 2006']],
    ['ETP · superficie sin falta de agua', ['Priestley–Taylor', 'Thornthwaite']],
    ['ET real · la cuenca', ['Brutsaert–Stricker (AA)']],
  ];
  const filas = [], textoFila = [];
  BLOQUES.forEach(([titulo, metodos], k) => {
    if (k) { filas.push(`_esp${k}`); textoFila.push(''); }
    filas.push(`_tit${k}`); textoFila.push('');
    metodos.forEach(m => { filas.push(m); textoFila.push(m.replace(' (FAO-56)', '').replace('ETo ', '')); });
  });
  const VARIABLES = [
    ['Solo altitud', ['Cenicafé 2006'], '#CC79A7'],
    ['T (y latitud)', ['Thornthwaite'], '#A65E1A'],
    ['T + Ra', ['Hargreaves–Samani'], '#7C5BC7'],
    ['Rs + T', ['Makkink'], '#009E73'],
    ['Rn + T', ['Priestley–Taylor'], '#E69F00'],
    ['Rn + T + humedad + viento', ['Penman (FAO-24, c = 0.8)', 'Brutsaert–Stricker (AA)'], '#0072B2'],
  ];
  const frente = m => { const d = Math.round(100 * (MT.anual[m] / MT.eto_anual - 1)); return `${d > 0 ? '+' : d < 0 ? '−' : '±'}${Math.abs(d)} %`; };
  const conSigno = n => `${n > 0 ? '+' : n < 0 ? '−' : '±'}${miles(Math.abs(n))}`;
  const pct = Math.round(100 * P.radiativa / MT.eto_anual);
  // Dos vistas de la misma gráfica (Juan, 22 nov): normal = mm/año de cada método; al pasar el cursor (o tocar, en
  // pantallas táctiles) = diferencia con la ETo Penman–Monteith, verde hacia la derecha (más) y rojo a la izquierda.
  const VERDE = '#1A9850', ROJO = '#D73027', LIM = 560;
  const vistaMetodos = dif => {
    const trazas = VARIABLES.map(([grupo, metodos, color]) => {
      const d = metodos.map(m => MT.anual[m] - MT.eto_anual);
      return {type: 'bar', name: grupo, orientation: 'h', y: metodos, showlegend: !dif,
        x: dif ? d : metodos.map(m => MT.anual[m]),
        marker: {color: dif ? d.map(v => v >= 0 ? VERDE : ROJO) : color},
        text: metodos.map((m, k) => dif ? `<b>${conSigno(d[k])}</b>  ${frente(m)}` : `<b>${miles(MT.anual[m])}</b>  ${frente(m)}`),
        textposition: 'outside', cliponaxis: false, textfont: {color: css('--tinta')},
        hovertemplate: dif ? '%{y}<br>%{x:+} mm/año frente a la ETo Penman–Monteith<extra></extra>'
                           : '%{y}<br>%{x} mm/año · usa ' + grupo + '<extra></extra>'};
    });
    trazas.push(
      {type: 'bar', orientation: 'h', name: 'Rn + T + humedad + viento', showlegend: false, y: [PM], x: [dif ? 0 : P.radiativa],
        marker: {color: '#0072B2'}, text: [dif ? '' : `término radiativo ${miles(P.radiativa)} (${pct} %)`], textposition: 'inside',
        insidetextanchor: 'middle', textfont: {color: '#FFFFFF'},
        hovertemplate: 'Penman–Monteith, término radiativo: %{x} mm/año<extra></extra>'},
      {type: 'bar', orientation: 'h', name: 'rayado: término aerodinámico', y: [PM], x: [dif ? 0 : P.aerodinamica], showlegend: !dif,
        marker: {color: css('--superficie'), line: {color: '#0072B2', width: dif ? 0 : 1.5}, pattern: {shape: '/', fgcolor: '#0072B2', size: 6, solidity: 0.35}},
        text: [dif ? '<b>referencia</b>' : `<b>${miles(MT.eto_anual)}</b>  aerodinámico ${P.aerodinamica} (${100 - pct} %)`],
        textposition: 'outside', cliponaxis: false, textfont: {color: css('--tinta')},
        hovertemplate: 'Penman–Monteith, término aerodinámico: %{x} mm/año<extra></extra>'});
    const lg = base('mm/año'); lg.hovermode = 'closest'; lg.margin.l = 210; lg.margin.r = 40; lg.margin.t = 60;
    lg.barmode = 'stack'; lg.bargap = 0.32; lg.transition = {duration: 400, easing: 'cubic-in-out'};
    lg.legend = {orientation: 'h', x: 0, xanchor: 'left', y: 1.02, yanchor: 'bottom', traceorder: 'normal',
      title: {text: 'Variables que usa:  '}, font: {size: 12}};
    lg.yaxis = Object.assign(lg.yaxis || {}, {type: 'category', categoryorder: 'array', categoryarray: filas,
      tickmode: 'array', tickvals: filas, ticktext: textoFila, autorange: 'reversed', title: '', showgrid: false,
      ticks: '', tickfont: {size: 13}});
    lg.xaxis = Object.assign(lg.xaxis || {}, {type: 'linear', range: dif ? [-LIM, LIM] : [0, 1900], zeroline: false,
      title: dif ? 'Diferencia con la ETo Penman–Monteith (FAO-56), mm/año' : 'mm/año'});
    const xLinea = dif ? 0 : MT.eto_anual;
    lg.shapes = [{type: 'line', x0: xLinea, x1: xLinea, yref: 'paper', y0: 0, y1: 1,
      line: {color: css('--tenue'), dash: dif ? 'solid' : 'dot', width: 1.5}}];
    lg.annotations = [...BLOQUES.map(([titulo], k) => ({x: dif ? -LIM : 0, y: `_tit${k}`, xanchor: 'left', yanchor: 'middle',
      showarrow: false, text: `<b>${titulo}</b>`, font: {size: 14, color: css('--tinta')}})),
      {x: xLinea, yref: 'paper', y: 1, yanchor: 'bottom', showarrow: false,
       text: dif ? `<span style="color:${ROJO}">◀ por debajo</span>   ETo Penman–Monteith = 0   <span style="color:${VERDE}">por encima ▶</span>`
                 : `ETo Penman–Monteith ${miles(MT.eto_anual)}  ·  pasa el cursor para ver la diferencia`,
       font: {size: 11, color: css('--tenue')}}];
    return [trazas, lg];
  };
  Plotly.newPlot('g-metodos-grupos', ...vistaMetodos(false), OPCIONES);
  {
    const div = document.getElementById('g-metodos-grupos');
    let enDiferencia = false;
    const mostrar = dif => { if (dif !== enDiferencia) { enDiferencia = dif; Plotly.react(div, ...vistaMetodos(dif), OPCIONES); } };
    div.addEventListener('mouseenter', () => mostrar(true));
    div.addEventListener('mouseleave', () => mostrar(false));
    div.addEventListener('touchstart', () => mostrar(!enDiferencia), {passive: true});
  }

  // Comparaciones, cada una con su referencia de la misma superficie.
  const cicloDe = (id, claves, ref) => Plotly.newPlot(id, [...claves, ref].map(c => ({type: 'scatter', mode: 'lines+markers',
    name: NOMBRE_M[c], x: xm, y: MT.ciclo[c], marker: {size: 4},
    line: {color: COLOR_M[c], width: c === ref ? 3 : 1.6, dash: c === ref ? 'dot' : 'solid'}})), ejeMes(base('mm/mes')), OPCIONES);
  {
    // Sesgo mensual frente a la franja ± dispersión (Juan, 23 nov).
    const d = MT.dispersion;
    const franja = [{type: 'scatter', mode: 'lines', x: [...xm, ...xm.slice().reverse()], y: [...d, ...d.map(v => -v).reverse()],
      fill: 'toself', fillcolor: 'rgba(128,128,128,0.22)', line: {width: 0}, name: '± dispersión fase 3', hoverinfo: 'skip'},
      {type: 'scatter', mode: 'lines', x: xm, y: d, line: {color: 'rgba(128,128,128,0.6)', width: 1}, showlegend: false,
       hovertemplate: 'dispersión ±%{y:.1f} %<extra></extra>'}];
    const orden = ['makkink', 'penman_fao24', 'hargreaves', 'cenicafe_2006', 'priestley_taylor', 'thornthwaite'];
    const lineas = orden.filter(c => MT.sesgo[c]).map(c => {
      const y = MT.sesgo[c], fuera = y.filter((v, i) => Math.abs(v) > d[i]).length;
      return {type: 'scatter', mode: 'lines+markers', x: xm, y, line: {color: COLOR_M[c], width: 2},
        name: `${NOMBRE_M[c]}${c === 'priestley_taylor' ? ' (vs rs = 0)' : ''} · ${fuera}/12 fuera`,
        marker: {size: 7, symbol: y.map((v, i) => Math.abs(v) > d[i] ? 'circle' : 'circle-open')},
        hovertemplate: `${NOMBRE_M[c]}: %{y:+.1f} %<extra></extra>`};
    });
    const ls = ejeMes(base('sesgo %')); ls.hovermode = 'x unified';
    ls.shapes = [{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 0, line: {color: css('--tenue'), width: 1}}];
    Plotly.newPlot('g-metodos-sesgo', [...franja, ...lineas], ls, OPCIONES);
    document.getElementById('disp-media').textContent = MT.dispersion_media;
  }
  cicloDe('g-metodos-ciclo-eto', ['penman_fao24', 'makkink', 'hargreaves', 'cenicafe_2006', 'thornthwaite'], 'eto_fao56');
  cicloDe('g-metodos-ciclo-pt', ['priestley_taylor'], 'eto_fao56_rs0');

  {
    const TM = CARGA.terminos, fr = TM.fraccion_aerodinamica_pct;
    const rango = fr.map((v, i) => `${TM.fraccion_aerodinamica_min_pct[i].toFixed(1)} a ${TM.fraccion_aerodinamica_max_pct[i].toFixed(1)} %`);
    const lt = ejeMes(base('mm/mes')); lt.barmode = 'stack'; lt.hovermode = 'x unified';
    Plotly.newPlot('g-terminos-f5', [
      {type: 'bar', name: 'término radiativo', x: xm, y: TM.eto_radiativa_mm_mes, marker: {color: '#0072B2'},
       customdata: TM.fraccion_radiativa_pct, hovertemplate: 'radiativo: %{y:.1f} mm/mes (%{customdata:.1f} %)<extra></extra>'},
      {type: 'bar', name: 'término aerodinámico', x: xm, y: TM.eto_aerodinamica_mm_mes, marker: {color: '#E69F00'},
       text: fr.map(v => v.toFixed(1) + ' %'), textposition: 'outside', cliponaxis: false, customdata: rango,
       hovertemplate: 'aerodinámico: %{y:.1f} mm/mes (%{text}; entre años %{customdata})<extra></extra>'}], lt, OPCIONES);
  }
  {
    const A = CARGA.alfa;
    const la = ejeMes(base('razón con Eeq')); la.hovermode = 'x unified';
    la.yaxis2 = {title: 'kPa · m/s', overlaying: 'y', side: 'right', showgrid: false, rangemode: 'tozero'};
    la.legend = {orientation: 'h', y: 1.15}; la.margin = Object.assign({}, la.margin, {r: 70});
    Plotly.newPlot('g-alfa', [
      {type: 'scatter', mode: 'lines', x: [...xm, ...xm.slice().reverse()],
       y: [...A.alfa_estrella_max, ...A.alfa_estrella_min.slice().reverse()], fill: 'toself',
       fillcolor: 'rgba(0,114,178,0.15)', line: {width: 0}, name: 'α* mín.–máx. entre años', hoverinfo: 'skip'},
      {type: 'scatter', mode: 'lines+markers', x: xm, y: A.alfa_estrella, name: 'α* = ETo/Eeq', line: {color: '#0072B2', width: 2.5},
       hovertemplate: 'α*: %{y:.3f}<extra></extra>'},
      {type: 'scatter', mode: 'lines+markers', x: xm, y: A.alfa_rs0, name: 'ETo(rs = 0)/Eeq', line: {color: '#009E73', dash: 'dash'},
       hovertemplate: 'rs = 0: %{y:.3f}<extra></extra>'},
      {type: 'scatter', mode: 'lines', x: [1, 12], y: [1.26, 1.26], name: 'α de Priestley–Taylor (1.26)',
       line: {color: '#E69F00', dash: 'dot'}, hoverinfo: 'skip'},
      {type: 'scatter', mode: 'lines', x: xm, y: A.deficit_kPa, name: 'déficit es − ea (kPa)', yaxis: 'y2',
       line: {color: '#A65E1A', width: 1.3}, hovertemplate: 'déficit: %{y:.3f} kPa<extra></extra>'},
      {type: 'scatter', mode: 'lines', x: xm, y: A.u2_ms, name: 'u2 (m/s)', yaxis: 'y2',
       line: {color: '#7C5BC7', width: 1.3}, hovertemplate: 'u2: %{y:.2f} m/s<extra></extra>'}], la, OPCIONES);
  }
  document.getElementById('texto-f4').innerHTML = CARGA.texto_f4.map(t => `<p>${t}</p>`).join('');
  const H1 = CARGA.hargreaves_t1;
  const SERIES_H1 = [['tarea2_6_puntos', 'Tarea 2 · ERA5-Land, 6 puntos', '#7C5BC7'],
    ['tarea1_era5land', 'Tarea 1 · ERA5-Land, promedio de cuenca', '#56B4E9'],
    ['tarea1_mswx', 'Tarea 1 · MSWX (CAMELS-COL)', '#009E73'],
    ['camels_publicada', 'CAMELS-COL publicada', '#D55E00'],
    ['eto_penman_monteith', 'ETo Penman–Monteith (FAO-56)', css('--tinta')]];
  tabla('t-hargreaves-t1', ['Serie', `Media anual, ${H1.n_meses} meses (mm)`, 'Frente a la ETo Penman–Monteith (FAO-56)'],
    SERIES_H1.map(([c, n]) => [n, H1.anual[c], c === 'eto_penman_monteith' ? 'referencia' : `${fmt(H1.sesgo[c], 1)} %`]));
  Plotly.newPlot('g-hargreaves-t1', SERIES_H1.map(([c, n, color]) => ({type: 'scatter', mode: 'lines+markers', name: n,
    x: xm, y: H1.ciclo[c], marker: {size: 4}, visible: c === 'camels_publicada' ? 'legendonly' : true,
    line: {color, width: c === 'eto_penman_monteith' ? 3 : 1.6, dash: c === 'eto_penman_monteith' ? 'dot' : 'solid'}})),
    ejeMes(base('mm/mes')), OPCIONES);
  const B = CARGA.balance;
  tabla('t-balance', ['Camino', 'Datos', 'PI (mm/año)', 'PL (mm/año)', 'Q (mm/año)', 'ET real con PI', 'ET real con PL'],
    B.resumen.map(r => [r.camino, r.n, r.PI, r.PL, r.Q, r.ETR_PI, r.ETR_PL]));
  document.querySelectorAll('#t-balance td:first-child').forEach(td => { td.style.whiteSpace = 'normal'; td.style.textAlign = 'left'; });
  document.getElementById('p-balance-ds').textContent =
    `ΔS del suelo: cambio neto ${fmt(B.ds_neto, 1)} mm/año entre 1998 y 2022; de un año a otro varía con desviación estándar de ${B.ds_desv} mm.`;
  const reales = E.anual.filter(a => !potencial(a.clave));
  const etiquetas = ['Balance con PL', 'Balance con PI', ...reales.map(a => a.producto)];
  const valores = [B.resumen[0].ETR_PL, B.resumen[0].ETR_PI, ...reales.map(a => a.propio)];
  const lb = base('mm/año'); lb.yaxis.rangemode = 'tozero'; lb.showlegend = false; lb.xaxis = Object.assign(lb.xaxis || {}, {type: 'category'});
  Plotly.newPlot('g-balance-productos', [{type: 'bar', x: etiquetas, y: valores,
    marker: {color: etiquetas.map((_, i) => i < 2 ? css('--tinta') : COLOR_PROD[reales[i - 2].clave])},
    hovertemplate: '%{x}: %{y} mm/año<extra></extra>'}], lb, OPCIONES);
  const la = base('mm/año'); la.yaxis.rangemode = 'tozero'; la.barmode = 'group'; la.xaxis = Object.assign(la.xaxis || {}, {type: 'category'});
  Plotly.newPlot('g-balance-anual', [
    {type: 'bar', name: 'Con PL', x: B.anios, y: B.etr_pl, marker: {color: '#0072B2'}},
    {type: 'bar', name: 'Con PI', x: B.anios, y: B.etr_pi, marker: {color: '#E69F00'}}], la, OPCIONES);
})();

// Fase 6: ET real por varios caminos.
(() => {
  const F6 = CARGA.fase6, MESES = ['E','F','M','A','M','J','J','A','S','O','N','D'], xm = [1,2,3,4,5,6,7,8,9,10,11,12];
  const tabla = (id, cab, filas) => { document.getElementById(id).innerHTML =
    '<table><tr>' + cab.map(c => `<th>${c}</th>`).join('') + '</tr>' +
    filas.map(f => '<tr>' + f.map(v => `<td>${v}</td>`).join('') + '</tr>').join('') + '</table>'; };
  const miles = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const pct = v => (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(1) + ' %';
  const AZUL = '#0072B2', NARANJA = '#E69F00';
  const COLOR_P = {era5land_e: '#0072B2', gleam_E: '#009E73', mod16a2gf: '#D55E00', terraclimate_aet: '#CC79A7',
    ssebop_v61: '#E69F00', ssebop_v5: '#8C6D31', aa_brutsaert_stricker: '#7C5BC7'};
  const NOMBRE_P = {era5land_e: 'ERA5-Land e', gleam_E: 'GLEAM v4.3a E', mod16a2gf: 'MOD16A2GF v061', terraclimate_aet: 'TerraClimate aet',
    ssebop_v61: 'SSEBop v6.1', ssebop_v5: 'SSEBop v5', aa_brutsaert_stricker: 'AA (Brutsaert–Stricker)'};

  const I = F6.incertidumbre, C = I.find(r => r.caso_sigma_Q === 'central');
  tabla('t-f6-incert', ['Caso de σ_Q', 'σ_Q (% de Q)', 'σ_P (mm)', 'σ_Q (mm)', 'σ_ET (mm)', 'σ_ET / ET con PI', 'σ_ET / ET con PL', 'Parte de σ²_ET que viene de P'],
    I.map(r => [r.caso_sigma_Q, r.sigma_Q_pct_de_Q.toFixed(1), miles(r.sigma_P), miles(r.sigma_Q), miles(r.sigma_ET),
      Math.round(r.sigma_ET_pct_de_ETR_PI) + ' %', Math.round(r.sigma_ET_pct_de_ETR_PL) + ' %', Math.round(r.parte_de_P_en_varianza_pct) + ' %']));
  const T = Object.fromEntries(F6.techo.map(t => [t.camino, t]));
  const cifras = [
    [`${miles(C.ETR_PL)} ± ${miles(C.sigma_ET)}`, 'P − Q con PL (mm/año)'],
    [`${miles(C.ETR_PI)} ± ${miles(C.sigma_ET)}`, 'P − Q con PI (mm/año)'],
    [miles(T['balance con PL'].Rn_lambda_mm_anio), 'Rn/λ de ERA5-Land (mm/año)'],
    [`${T['balance con PI'].fraccion_evaporativa.toFixed(2)} – ${T['balance con PL'].fraccion_evaporativa.toFixed(2)}`, 'λET/Rn del balance (PI – PL)'],
    [`${T['balance con PI'].ET_sobre_ETo.toFixed(2)} – ${T['balance con PL'].ET_sobre_ETo.toFixed(2)}`, 'ET/ETo del balance (PI – PL)'],
  ];
  const caja = document.getElementById('f6-cifras');
  for (const [v, t] of cifras) { const d = document.createElement('div'); d.className = 'cifra'; d.innerHTML = `<b>${v}</b><span>${t}</span>`; caja.appendChild(d); }

  // Barras de productos con bandas del balance
  const FR = F6.frente, nombres = FR.map(f => f.producto);
  const lp = base('mm/año'); lp.hovermode = 'closest'; lp.showlegend = false; lp.yaxis.rangemode = 'tozero';
  lp.xaxis = {type: 'category', tickfont: {color: css('--tenue')}, linecolor: css('--linea')};
  const lim = [-0.5, nombres.length - 0.5];
  lp.shapes = [
    {type: 'rect', xref: 'x', x0: lim[0], x1: lim[1], y0: C.ETR_PL - C.sigma_ET, y1: C.ETR_PL + C.sigma_ET, fillcolor: AZUL, opacity: 0.10, line: {width: 0}, layer: 'below'},
    {type: 'rect', xref: 'x', x0: lim[0], x1: lim[1], y0: C.ETR_PI - C.sigma_ET, y1: C.ETR_PI + C.sigma_ET, fillcolor: NARANJA, opacity: 0.10, line: {width: 0}, layer: 'below'},
    {type: 'line', xref: 'x', x0: lim[0], x1: lim[1], y0: C.ETR_PL, y1: C.ETR_PL, line: {color: AZUL, width: 2}},
    {type: 'line', xref: 'x', x0: lim[0], x1: lim[1], y0: C.ETR_PI, y1: C.ETR_PI, line: {color: NARANJA, width: 2}},
    {type: 'line', xref: 'x', x0: lim[0], x1: lim[1], y0: T['balance con PL'].ETo_mm_anio, y1: T['balance con PL'].ETo_mm_anio, line: {color: css('--tinta'), width: 1.5, dash: 'dot'}},
    {type: 'line', xref: 'x', x0: lim[0], x1: lim[1], y0: T['balance con PL'].Rn_lambda_mm_anio, y1: T['balance con PL'].Rn_lambda_mm_anio, line: {color: '#C8553D', width: 1.5}},
  ];
  lp.annotations = [
    {xref: 'paper', x: 1, xanchor: 'right', y: C.ETR_PL, yshift: 9, text: 'P − Q con PL', showarrow: false, font: {color: AZUL, size: 11}},
    {xref: 'paper', x: 1, xanchor: 'right', y: C.ETR_PI, yshift: -9, text: 'P − Q con PI', showarrow: false, font: {color: NARANJA, size: 11}},
    {xref: 'paper', x: 0, xanchor: 'left', y: T['balance con PL'].ETo_mm_anio, yshift: 9, text: 'ETo Penman–Monteith (FAO-56)', showarrow: false, font: {size: 11}},
    {xref: 'paper', x: 0, xanchor: 'left', y: T['balance con PL'].Rn_lambda_mm_anio, yshift: 9, text: 'Rn/λ (ERA5-Land)', showarrow: false, font: {color: '#C8553D', size: 11}},
  ];
  const claveDe = n => Object.keys(NOMBRE_P).find(k => NOMBRE_P[k] === n);
  Plotly.newPlot('g-f6-productos', [{type: 'bar', x: nombres, y: FR.map(f => f.producto_mm_anio),
    marker: {color: nombres.map(n => COLOR_P[claveDe(n)] || '#888')},
    text: FR.map(f => miles(f.producto_mm_anio)), textposition: 'outside',
    customdata: FR.map(f => [miles(f.balance_PI_mm_anio), miles(f.balance_PL_mm_anio), pct(f.dif_vs_PI_pct), pct(f.dif_vs_PL_pct), f.meses_comunes_con_Q]),
    hovertemplate: '<b>%{x}</b>: %{y:.0f} mm/año<br>Balance en sus mismos %{customdata[4]} meses: PI %{customdata[0]} (%{customdata[2]}), PL %{customdata[1]} (%{customdata[3]})<extra></extra>'}],
    lp, OPCIONES);

  tabla('t-f6-frente', ['Producto', 'Principio de cálculo', 'Resolución', 'Meses con Q', 'Producto (mm/año)', 'Balance PI', 'Balance PL',
      'Frente a PI', 'Frente a PL', '¿Entre los dos balances?', 'λET/Rn', 'ET/ETo'],
    FR.map(f => [f.producto, f.principio, f.resolucion, f.meses_comunes_con_Q, miles(f.producto_mm_anio), miles(f.balance_PI_mm_anio),
      miles(f.balance_PL_mm_anio), pct(f.dif_vs_PI_pct), pct(f.dif_vs_PL_pct), f.entre_balances ? 'sí' : 'no',
      f.fraccion_evaporativa.toFixed(2), f.producto_sobre_ETo.toFixed(2)]));
  document.querySelectorAll('#t-f6-frente td:nth-child(2)').forEach(td => { td.style.whiteSpace = 'normal'; td.style.textAlign = 'left'; td.style.minWidth = '260px'; });

  // Ciclo anual
  const ejeMes = l => { l.xaxis = Object.assign(l.xaxis, {type: 'linear', tickvals: xm, ticktext: MESES}); l.hovermode = 'x unified'; return l; };
  const Ci = F6.ciclo, lc = ejeMes(base('mm/mes')); lc.yaxis.rangemode = 'tozero';
  const trazas = [
    {name: 'Rn/λ (ERA5-Land)', y: Ci.Rn_lambda, line: {color: '#C8553D', width: 2.5}},
    {name: 'ETo Penman–Monteith (FAO-56)', y: Ci.ETo, line: {color: css('--tinta'), width: 2.5, dash: 'dot'}},
    {name: 'P − Q con PL', y: Ci.ETR_PL, line: {color: AZUL, width: 2.5, dash: 'dash'}},
    {name: 'P − Q con PI', y: Ci.ETR_PI, line: {color: NARANJA, width: 2.5, dash: 'dash'}},
    ...F6.claves.map(k => ({name: NOMBRE_P[k], y: Ci[k], line: {color: COLOR_P[k], width: 1.5}, visible: k === 'ssebop_v5' ? 'legendonly' : true})),
  ].map(t => Object.assign({type: 'scatter', mode: 'lines+markers', x: xm, marker: {size: 4}}, t));
  Plotly.newPlot('g-f6-ciclo', trazas, lc, OPCIONES);

  // Por año, con selector de año hidrológico / calendario
  const dibujarAnual = tipo => {
    const A = F6.anual[tipo];
    const la = base('mm/año'); la.hovermode = 'x unified'; la.barmode = 'group'; la.yaxis.rangemode = 'tozero';
    la.xaxis = Object.assign(la.xaxis, {type: 'category'});
    Plotly.react('g-f6-anual', [
      {type: 'bar', name: 'P − Q con PL', x: A.anios, y: A.pl, marker: {color: AZUL}, error_y: {type: 'data', array: A.sigma, color: css('--tenue'), thickness: 1}},
      {type: 'bar', name: 'P − Q con PI', x: A.anios, y: A.pi, marker: {color: NARANJA}, error_y: {type: 'data', array: A.sigma, color: css('--tenue'), thickness: 1}},
      {type: 'scatter', mode: 'lines+markers', name: 'Mediana de los productos', x: A.anios, y: A.mediana, line: {color: '#009E73', width: 2}},
      {type: 'scatter', mode: 'lines', name: 'ETo Penman–Monteith (FAO-56)', x: A.anios, y: A.eto, line: {color: css('--tinta'), width: 1.5, dash: 'dot'}},
      {type: 'scatter', mode: 'lines', name: 'Rn/λ (ERA5-Land)', x: A.anios, y: A.rn, line: {color: '#C8553D', width: 1.5}},
      {type: 'scatter', mode: 'lines', name: 'ΔS del suelo', x: A.anios, y: A.ds, line: {color: css('--tenue'), width: 1}, visible: 'legendonly'},
    ], la, OPCIONES);
    const filas = [];
    A.anios.forEach((a, i) => { if (A.marcas_pi[i] || A.marcas_pl[i]) filas.push([a, miles(A.pi[i]), miles(A.pl[i]), miles(A.sigma[i]), miles(A.mediana[i]), A.marcas_pi[i] || '—', A.marcas_pl[i] || '—']); });
    tabla('t-f6-marcas', ['Año (' + (tipo === 'hidrologico' ? 'hidrológico, meses ' + A.meses : 'calendario') + ')', 'P − Q PI', 'P − Q PL', 'σ_ET', 'Mediana productos', 'Marcas con PI', 'Marcas con PL'], filas);
    document.querySelectorAll('#t-f6-marcas td:nth-child(n+6)').forEach(td => { td.style.whiteSpace = 'normal'; td.style.textAlign = 'left'; });
  };
  const caja2 = document.getElementById('c-f6-anio');
  [['hidrologico', `Año hidrológico (desde el mes de menos agua en el suelo, ${F6.anual.hidrologico.meses})`], ['calendario', 'Año calendario']].forEach(([tipo, texto], k) => {
    const b = document.createElement('button'); b.textContent = texto; b.setAttribute('aria-pressed', String(k === 0));
    b.onclick = () => { caja2.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', 'false')); b.setAttribute('aria-pressed', 'true'); dibujarAnual(tipo); };
    caja2.appendChild(b);
  });
  dibujarAnual('hidrologico');
})();

// Series horarias en rejilla, con el zoom en el tiempo sincronizado.
if (!CARGA.variables.length) document.getElementById('s-horarias').hidden = true;
const decodificar = b64 => { const s = atob(b64), b = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return new Float32Array(b.buffer); };
const t0 = new Date(CARGA.inicio_local + 'Z').getTime();
const pad = v => String(v).padStart(2, '0');
const tiempos = Array.from({length: CARGA.horas}, (_, i) => { const d = new Date(t0 + i * 3600000);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:00`; });
const nodos = [];
let sincronizando = false;
for (const v of CARGA.variables) {
  const tarjeta = document.createElement('div'); tarjeta.className = 'tarjeta';
  tarjeta.innerHTML = `<h3>${v.titulo}</h3>`;
  const nodo = document.createElement('div'); nodo.className = 'grafico';
  tarjeta.appendChild(nodo); document.getElementById('rejilla').appendChild(tarjeta);
  const trazas = CARGA.puntos.map((n, k) => ({
    type: 'scattergl', mode: 'lines', name: `P${n}`, legendgroup: `P${n}`, x: tiempos, y: decodificar(v.series[String(n)]),
    line: {width: 1, color: COLOR_PUNTO[k]}, hovertemplate: `P${n}: %{y:.2f} ${v.unidades}<extra></extra>`}));
  const disposicion = base(v.unidades); disposicion.hovermode = 'closest';
  Plotly.newPlot(nodo, trazas, disposicion, OPCIONES);
  nodos.push(nodo);
  // Zoom en el tiempo: se copia a las demás gráficas.
  nodo.on('plotly_relayout', ev => {
    if (sincronizando) return;
    const cambio = {};
    if (ev['xaxis.range[0]'] !== undefined) { cambio['xaxis.range'] = [ev['xaxis.range[0]'], ev['xaxis.range[1]']]; }
    else if (ev['xaxis.autorange']) { cambio['xaxis.autorange'] = true; }
    else return;
    sincronizando = true;
    Promise.all(nodos.filter(o => o !== nodo).map(o => Plotly.relayout(o, cambio))).then(() => { sincronizando = false; });
  });
  // Leyenda: ocultar o mostrar un punto en todas.
  nodo.on('plotly_legendclick', ev => {
    const k = ev.curveNumber, visible = ev.data[k].visible === 'legendonly' ? true : 'legendonly';
    nodos.forEach(o => Plotly.restyle(o, {visible}, [k]));
    return false;
  });
}

// Ventanas de tiempo para las series horarias.
const ventanas = [['Todo', null], ['1 año', 365], ['1 mes', 31], ['1 semana', 7]];
for (const [nombre, dias] of ventanas) {
  const b = document.createElement('button'); b.textContent = nombre; b.setAttribute('aria-pressed', String(dias === null));
  b.onclick = () => {
    document.querySelectorAll('#ventanas button').forEach(o => o.setAttribute('aria-pressed', String(o === b)));
    const fin = tiempos[tiempos.length - 1];
    const cambio = dias === null ? {'xaxis.autorange': true}
      : {'xaxis.range': [new Date(new Date(fin.replace(' ', 'T') + 'Z').getTime() - dias * 86400000).toISOString().slice(0, 16).replace('T', ' '), fin]};
    sincronizando = true;
    Promise.all(nodos.map(o => Plotly.relayout(o, cambio))).then(() => { sincronizando = false; });
  };
  document.getElementById('ventanas').appendChild(b);
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
