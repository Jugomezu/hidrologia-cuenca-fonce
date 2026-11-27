"""Fase 9, tema f (punto 1): resistencia de superficie efectiva por inversión de Penman–Monteith, sin LAI.

Idea: la ec. 3 de FAO-56 con resistencia de superficie rs, escrita en las unidades de la ec. 6, es
    ET = (A + B) / (C + D + E·rs)        con   A = 0.408·Δ·Rn,  B = γ·900/(T+273)·(es − ea)·208/ra,
                                               C = Δ,  D = γ,  E = γ/ra.
Con la ra del pasto (ra = 208/u2) y rs = 70 s/m queda la ec. 6 (ETo). Si se pone la ET REAL de un producto, se despeja
la rs que la reproduce:
    rs = ((A + B)/ET − C − D) / E.
Es una rs «efectiva»: mezcla dosel, suelo e intercepción, y hereda los errores del producto.

ra por cobertura (decisión de Juan, 25 nov). Ec. 4 de FAO-56, ra = ln((zm − d)/zom)·ln((zh − d)/zoh) / (k²·u_z), con
    - zom = z0 de la Tabla 1 de Gehrke, Sühring y Maronga (2021, GMD 14:5307, doi:10.5194/gmd-14-5307-2021), tipos de
      vegetación «al estilo de ECMWF»: bosque = evergreen broadleaf trees (2.00 m); mosaico agropecuario = crops, mixed
      farming (0.10 m); herbazal o arbustal andino = evergreen shrubs (0.10 m). Sensibilidad: herbazal = tall grass
      (0.47 m).
    - zoh = 0.1·zom (FAO-56), no el z0,h de esa tabla.
    - Viento: el de 10 m de ERA5-Land, tomado como medido 10 m por encima del plano de desplazamiento d (zm − d = zh − d
      = 10 m). Así d no hace falta y la ra no se indefine en el bosque, cuyo dosel pasaría de los 10 m.
    - En cada celda la conductancia 1/ra es el promedio de las de cada cobertura ponderado por su fracción de MapBiomas
      2022 (superficies en paralelo); el resto de las coberturas (≤ 2 %) se trata como agropecuario.
La rs con la ra del pasto (208/u2) queda como sensibilidad.

Datos, en cada uno de los 6 puntos de ERA5-Land (centros de celda de 0.1°):
    - T, ea, sp, viento: diarios del script 03 (era5land_diario_puntos.csv); u2 con la ec. 47; Δ y es como el script 04.
    - Rn REAL de la superficie: ssr + str de ERA5-Land mensual (script 07) en la celda del punto. Se corta en 2022-08
      (error de ECMWF de sep–dic 2022). Sensibilidad: Rn del pasto de referencia (FAO-56, albedo 0.23, script 03).
    - ET real: GLEAM v4.3a (malla desplazada 0.05°: media de las 4 celdas que tocan la celda del punto) y SSEBop v6.1
      (media de los píxeles dentro de la celda del punto; 2012–2022).
Los términos A–E se promedian por mes (media de los días) antes de despejar. G = 0.

Luego: rs mediana por punto frente a la altura del modelo, y, dentro de cada punto, la correlación mensual de rs con la T
y el déficit (las variables de dos funciones de Jarvis, 1976). Entre puntos, T y altura van juntas (y la cobertura), así
que no se separan las funciones de Jarvis; solo se ve si la rs sube con la altura y cómo varía en el año.

Para leer la rs se agrega, por punto: la cobertura de MapBiomas 2022 en la celda (fracción de bosque, de herbazal o
arbustal andino y de mosaico agropecuario) y el techo de Penman–Monteith con rs = 0 (la ET máxima
que el despeje admite), calculado con la ra por cobertura. Si la ET del producto lo supera, el mes queda «sin solución» y la rs se acota en 0.

Escribe productos/punto1/resistencia_superficie_mensual.csv, resistencia_superficie_resumen.csv y
resistencia_superficie.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/37_resistencia_superficie.py
"""

import importlib.util
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.transform import rowcol

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
DATOS = RAIZ_ENTREGA / "datos" / "punto1"
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ENTRADA_DIARIA = CARPETA_PRODUCTOS / "era5land_diario_puntos.csv"
ENTRADA_PUNTOS = RAIZ_ENTREGA / "anexos" / "punto1" / "elevacion_puntos_dem.csv"
ARCHIVO_RN = DATOS / "era5land_mensual_balance" / "era5land_mensual_balance_1998_2022_fonce.nc"
ARCHIVO_GLEAM = DATOS / "gleam_v4" / "gleam_v4_E_mensual_1998_2022_fonce.nc"
ARCHIVO_COBERTURA = DATOS / "mapbiomas" / "colombia_coverage_2022_fonce.tif"
ARCHIVO_SSEBOP = DATOS / "ssebop" / "ssebop_v61_eta_mensual_2012_2022_fonce.nc"
SALIDA_MENSUAL = CARPETA_PRODUCTOS / "resistencia_superficie_mensual.csv"
SALIDA_RESUMEN = CARPETA_PRODUCTOS / "resistencia_superficie_resumen.csv"
SALIDA_FIGURA = CARPETA_PRODUCTOS / "resistencia_superficie.png"

ULTIMO_MES = "2022-08"            # ERA5-Land mensual dañado después (ECMWF)
RS_REFERENCIA = 70.0              # s/m, pasto de referencia de FAO-56
MEDIA_CELDA = 0.05                # medio ancho de la celda de ERA5-Land (grados)
# Códigos de MapBiomas Colombia (colección 3; leyenda copiada en ../Analisis_De_Cuenca/scripts/03d_coberturas_mapbiomas.py)
GRUPOS_COBERTURA = {"bosque": [3], "herbazal_andino": [81], "agropecuario": [21]}
# Longitud de rugosidad para el momento z0 (m), Tabla 1 de Gehrke et al. (2021); el tipo elegido lo decidió Juan
Z0_COBERTURA = {"bosque": 2.00,             # evergreen broadleaf trees
                "herbazal_andino": 0.10,    # evergreen shrubs
                "agropecuario": 0.10}       # crops, mixed farming
Z0_HERBAZAL_TALL_GRASS = 0.47              # sensibilidad: herbazal andino como tall grass
K_VON_KARMAN = 0.41
ALTURA_VIENTO_SOBRE_D = 10.0               # m: el viento de 10 m se toma 10 m por encima del plano de desplazamiento


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, Path(__file__).with_name(archivo))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


eto04 = cargar("eto_fao56", "04_eto_fao56.py")


def ra_fao56(z0m, viento10):
    """Resistencia aerodinámica (s/m), ec. 4 de FAO-56 con zoh = 0.1·zom y zm − d = zh − d = 10 m."""
    return (np.log(ALTURA_VIENTO_SOBRE_D / z0m) * np.log(ALTURA_VIENTO_SOBRE_D / (0.1 * z0m))
            / (K_VON_KARMAN ** 2 * viento10))


def ra_celda(fracciones, viento10, z0):
    """ra de la celda: inverso de la conductancia media ponderada por la fracción de cada cobertura."""
    conductancia = sum(fracciones[f"frac_{c}"] / ra_fao56(z0[c], viento10) for c in z0)
    return 1 / conductancia


def terminos_mensuales(diaria, coberturas):
    """Medias mensuales de A (con Rn de referencia), B, C, D y E por punto, y forzantes.

    B y E dependen de la ra; se calculan con tres ra: la del pasto (sufijo _pasto), la de la cobertura (_cob, la
    principal) y la de la cobertura con el herbazal como tall grass (_tg, sensibilidad).
    """
    t = (diaria["tmax_C"] + diaria["tmin_C"]) / 2
    delta = eto04.pendiente_saturacion(t)
    es = (eto04.presion_saturacion(diaria["tmax_C"]) + eto04.presion_saturacion(diaria["tmin_C"])) / 2
    gamma = 0.665e-3 * diaria["sp_kPa"]
    u2 = eto04.viento_a_2m(diaria["viento10_ms"])
    deficit = (es - diaria["ea_kPa"]).clip(lower=0)
    # fracciones de cobertura de la celda de cada día; las «otras» (≤ 2 %) se suman al agropecuario
    frac = coberturas.loc[diaria["punto"]].reset_index(drop=True)
    frac["frac_agropecuario"] = frac["frac_agropecuario"] + frac["frac_otras"]
    viento10 = diaria["viento10_ms"].reset_index(drop=True)
    z0_tg = dict(Z0_COBERTURA, herbazal_andino=Z0_HERBAZAL_TALL_GRASS)
    ras = {"pasto": 208 / u2.reset_index(drop=True), "cob": ra_celda(frac, viento10, Z0_COBERTURA),
           "tg": ra_celda(frac, viento10, z0_tg)}
    d = pd.DataFrame({
        "punto": diaria["punto"], "mes": diaria["fecha"].dt.to_period("M"),
        "A_ref": 0.408 * delta * diaria["rn_MJm2"], "C": delta, "D": gamma, "delta_0408": 0.408 * delta,
        "t_C": t, "deficit_kPa": deficit, "u2_ms": u2, "rn_ref_MJm2": diaria["rn_MJm2"],
    }).reset_index(drop=True)
    for sufijo, ra in ras.items():
        d[f"ra_{sufijo}_sm"] = ra
        d[f"B_{sufijo}"] = (gamma * 900 / (t + 273) * deficit).reset_index(drop=True) * 208 / ra
        d[f"E_{sufijo}"] = gamma.reset_index(drop=True) / ra
    return d.groupby(["punto", "mes"]).mean().reset_index()


def rn_real(puntos):
    """Rn real (ssr + str de ERA5-Land, MJ/m²·día) en la celda de cada punto."""
    ds = xr.open_dataset(ARCHIVO_RN)
    filas = []
    for n, p in puntos.iterrows():
        celda = ds.sel(latitude=p["lat"], longitude=p["lon"], method="nearest")
        assert abs(float(celda.latitude) - p["lat"]) < 1e-6 and abs(float(celda.longitude) - p["lon"]) < 1e-6
        rn = (celda["ssr"] + celda["str"]).to_series() / 1e6          # media mensual de la acumulación diaria, J/m²
        filas.append(pd.DataFrame({"punto": n, "mes": rn.index.to_period("M"), "rn_real_MJm2": rn.to_numpy()}))
    return pd.concat(filas)


def et_en_celda(archivo, variable, puntos):
    """ET mensual (mm/mes) del producto promediada dentro de la celda de 0.1° de cada punto.

    GLEAM (0.1°, desplazada 0.05°): las celdas cuyo centro está a ≤ 0.05° en lat y lon (4 celdas, cada una cubre un
    cuarto). SSEBop (~1 km): los píxeles con centro dentro de la celda.
    """
    ds = xr.open_dataset(archivo)[variable]
    lat, lon = ("lat", "lon") if "lat" in ds.dims else ("latitude", "longitude")
    filas = []
    for n, p in puntos.iterrows():
        sel = ds.where((abs(ds[lat] - p["lat"]) <= MEDIA_CELDA + 1e-6) & (abs(ds[lon] - p["lon"]) <= MEDIA_CELDA + 1e-6),
                       drop=True)
        serie = sel.mean([lat, lon]).to_series()
        assert sel.sizes[lat] * sel.sizes[lon] >= 4, f"{archivo.name}: pocas celdas en el punto {n}"
        filas.append(pd.DataFrame({"punto": n, "mes": pd.to_datetime(serie.index).to_period("M"),
                                   "et_mm_mes": serie.to_numpy(), "celdas": sel.sizes[lat] * sel.sizes[lon]}))
    return pd.concat(filas)


def coberturas_celda(puntos):
    """Fracción de cada grupo de cobertura de MapBiomas 2022 entre los píxeles con dato de la celda de 0.1° del punto.

    Píxeles de ~30 m en EPSG:4326 sin ponderar por área: dentro de una celda de 0.1° la diferencia de área entre filas
    es despreciable (< 0.1 %).
    """
    with rasterio.open(ARCHIVO_COBERTURA) as r:
        clases, transformacion = r.read(1), r.transform
    filas = []
    for n, p in puntos.iterrows():
        f0, c0 = rowcol(transformacion, p["lon"] - MEDIA_CELDA, p["lat"] + MEDIA_CELDA)
        f1, c1 = rowcol(transformacion, p["lon"] + MEDIA_CELDA, p["lat"] - MEDIA_CELDA)
        celda = clases[max(f0, 0):f1, max(c0, 0):c1].ravel()
        celda = celda[celda > 0]                           # 0 = sin dato del archivo nacional
        fila = {"punto": n}
        for grupo, codigos in GRUPOS_COBERTURA.items():
            fila[f"frac_{grupo}"] = np.isin(celda, codigos).mean()
        fila["frac_otras"] = 1 - sum(fila[f"frac_{g}"] for g in GRUPOS_COBERTURA)
        filas.append(fila)
    return pd.DataFrame(filas).set_index("punto")


def despejar_rs(tabla, a_col, ra="cob"):
    """rs (s/m) que hace que Penman–Monteith dé la ET del producto con la ra indicada (pasto, cob o tg). Negativa si la
    ET supera lo que permite rs = 0: entonces se toma rs = 0 (cota inferior) y el mes cuenta como «sin solución»."""
    et_dia = tabla["et_mm_mes"] / tabla["mes"].dt.days_in_month
    return ((tabla[a_col] + tabla[f"B_{ra}"]) / et_dia - tabla["C"] - tabla["D"]) / tabla[f"E_{ra}"]


def main():
    puntos = pd.read_csv(ENTRADA_PUNTOS).set_index("punto")
    diaria = pd.read_csv(ENTRADA_DIARIA, parse_dates=["fecha"])
    coberturas = coberturas_celda(puntos)
    term = terminos_mensuales(diaria, coberturas).merge(rn_real(puntos), on=["punto", "mes"], how="left")
    term = term[term["mes"] <= pd.Period(ULTIMO_MES, "M")]
    # A con la Rn real: 0.408·Δ·Rn con la Δ media del mes (la Rn real solo es mensual)
    term["A_real"] = term["delta_0408"] * term["rn_real_MJm2"]

    tablas = []
    for nombre, (archivo, var) in {"GLEAM v4.3a": (ARCHIVO_GLEAM, "E"),
                                   "SSEBop v6.1": (ARCHIVO_SSEBOP, "eta")}.items():
        et = et_en_celda(archivo, var, puntos)
        t = term.merge(et, on=["punto", "mes"], how="inner")
        t["producto"] = nombre
        crudo = despejar_rs(t, "A_real")
        t["sin_solucion"] = crudo <= 0
        t["rs_sm"] = crudo.clip(lower=0)
        t["rs_sm_rn_referencia"] = despejar_rs(t, "A_ref").clip(lower=0)
        pasto = despejar_rs(t, "A_real", ra="pasto")
        t["sin_solucion_ra_pasto"] = pasto <= 0
        t["rs_sm_ra_pasto"] = pasto.clip(lower=0)
        t["rs_sm_herbazal_tall_grass"] = despejar_rs(t, "A_real", ra="tg").clip(lower=0)
        t["et_techo_rs0_mm_dia"] = (t["A_real"] + t["B_cob"]) / (t["C"] + t["D"])   # Penman–Monteith con rs = 0
        tablas.append(t)
    tabla = pd.concat(tablas, ignore_index=True)
    tabla["z_modelo_m"] = tabla["punto"].map(puntos["z_modelo_m"])

    # Comprobación: con la ETo de FAO-56, la Rn de referencia y la ra del pasto, el despeje devuelve rs = 70 s/m
    prueba = term.assign(et_mm_mes=(term["A_ref"] + term["B_pasto"])
                         / (term["C"] + term["D"] + term["E_pasto"] * RS_REFERENCIA) * term["mes"].dt.days_in_month)
    assert np.allclose(despejar_rs(prueba, "A_ref", ra="pasto"), RS_REFERENCIA)

    resumen = []
    for (prod, n), g in tabla.groupby(["producto", "punto"]):
        resumen.append({"producto": prod, "punto": n, "z_modelo_m": puntos.loc[n, "z_modelo_m"], "meses": len(g),
                        "meses_sin_solucion": int(g["sin_solucion"].sum()),
                        "corr_rs_deficit_mensual": g[~g["sin_solucion"]][["rs_sm", "deficit_kPa"]].corr().iloc[0, 1],
                        "corr_rs_t_mensual": g[~g["sin_solucion"]][["rs_sm", "t_C"]].corr().iloc[0, 1],
                        "rs_mediana_sm": g["rs_sm"].median(), "rs_p25_sm": g["rs_sm"].quantile(0.25),
                        "rs_p75_sm": g["rs_sm"].quantile(0.75),
                        "rs_mediana_rn_referencia_sm": g["rs_sm_rn_referencia"].median(),
                        "ra_cobertura_mediana_sm": g["ra_cob_sm"].median(),
                        "ra_pasto_mediana_sm": g["ra_pasto_sm"].median(),
                        "rs_mediana_ra_pasto_sm": g["rs_sm_ra_pasto"].median(),
                        "meses_sin_solucion_ra_pasto": int(g["sin_solucion_ra_pasto"].sum()),
                        "rs_mediana_herbazal_tall_grass_sm": g["rs_sm_herbazal_tall_grass"].median(),
                        "et_techo_rs0_mm_anio": (g["et_techo_rs0_mm_dia"] * g["mes"].dt.days_in_month).mean() * 12,
                        "et_mm_anio": g["et_mm_mes"].mean() * 12, "t_C": g["t_C"].mean(),
                        "deficit_kPa": g["deficit_kPa"].mean()})
    resumen = pd.DataFrame(resumen).merge(coberturas, left_on="punto", right_index=True)
    ajustes = []
    for prod, g in tabla.groupby("producto"):
        r = resumen[resumen["producto"] == prod]
        pend = np.polyfit(r["z_modelo_m"] / 1000, r["rs_mediana_sm"], 1)
        pend_pasto = np.polyfit(r["z_modelo_m"] / 1000, r["rs_mediana_ra_pasto_sm"], 1)
        ajustes.append({"producto": prod, "rs_por_km_sm": pend[0],
                        "r2_rs_altura": np.corrcoef(r["z_modelo_m"], r["rs_mediana_sm"])[0, 1] ** 2,
                        "rs_por_km_ra_pasto_sm": pend_pasto[0]})
    ajustes = pd.DataFrame(ajustes)

    salida = tabla.copy()
    salida["mes"] = salida["mes"].astype(str)
    salida.round(4).to_csv(SALIDA_MENSUAL, index=False)
    resumen.merge(ajustes, on="producto").round(4).to_csv(SALIDA_RESUMEN, index=False)
    figura(tabla, resumen)

    pd.set_option("display.width", 200)
    print(resumen.round(2).to_string())
    print(ajustes.round(4).to_string())
    print(f"Listo: {SALIDA_MENSUAL.name}, {SALIDA_RESUMEN.name}, {SALIDA_FIGURA.name}")


def figura(tabla, resumen):
    colores = {"GLEAM v4.3a": "#CC79A7", "SSEBop v6.1": "#E69F00"}
    fig, ejes = plt.subplots(2, 1, figsize=(6.5, 8.8))
    for prod, r in resumen.groupby("producto"):
        r = r.sort_values("z_modelo_m")
        ejes[0].errorbar(r["rs_mediana_sm"], r["z_modelo_m"],
                         xerr=[r["rs_mediana_sm"] - r["rs_p25_sm"], r["rs_p75_sm"] - r["rs_mediana_sm"]],
                         fmt="o", color=colores[prod], capsize=3, label=f"{prod}, ra por cobertura")
        ejes[0].plot(r["rs_mediana_ra_pasto_sm"], r["z_modelo_m"], "o", color=colores[prod], alpha=0.45,
                     label=f"{prod}, ra del pasto (sensibilidad)")
        # rectas rs = corte + pendiente·z (mínimos cuadrados con las 6 medianas; descriptivas, n = 6)
        z = np.linspace(r["z_modelo_m"].min(), r["z_modelo_m"].max(), 2)
        for col, estilo, alfa, texto in (("rs_mediana_sm", "-", 1.0, "ra por cobertura"),
                                         ("rs_mediana_ra_pasto_sm", "--", 0.45, "ra del pasto")):
            pendiente, corte = np.polyfit(r["z_modelo_m"] / 1000, r[col], 1)
            ejes[0].plot(corte + pendiente * z / 1000, z, estilo, color=colores[prod], alpha=alfa, lw=1,
                         label=f"recta {prod}, {texto}: {pendiente:+.0f} s/m por km")
    ejes[0].axvline(RS_REFERENCIA, color="k", ls=":", lw=1, label="pasto de referencia (70 s/m)")
    ejes[0].set_xlim(0, None)
    ejes[0].set_xlabel("rs efectiva, mediana y cuartiles (s/m)")
    ejes[0].set_ylabel("altura del modelo (m)")
    ejes[0].set_title("Resistencia de superficie frente a la altura")
    ejes[0].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
    # ciclo anual de la rs de SSEBop por punto (mediana por mes del calendario)
    s = tabla[tabla["producto"] == "SSEBop v6.1"]
    ciclo = s.groupby(["punto", s["mes"].dt.month])["rs_sm"].median().unstack(0)
    z = s.groupby("punto")["z_modelo_m"].first()
    for n in ciclo.columns:
        ejes[1].plot(ciclo.index, ciclo[n], "o-", ms=3, color=plt.cm.viridis((z[n] - 1600) / 1500),
                     label=f"punto {n} ({z[n]:.0f} m)")
    ejes[1].set_ylim(0, None)
    ejes[1].set_xticks(range(1, 13))
    ejes[1].set_xlabel("mes")
    ejes[1].set_ylabel("rs efectiva (s/m)")
    ejes[1].set_title("Ciclo anual de la rs con SSEBop v6.1 (2012–2022), ra por cobertura", fontsize=10)
    ejes[1].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(SALIDA_FIGURA, dpi=150)


if __name__ == "__main__":
    main()
