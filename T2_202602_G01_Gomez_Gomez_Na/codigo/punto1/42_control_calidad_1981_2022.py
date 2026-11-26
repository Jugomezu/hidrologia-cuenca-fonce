"""Fase 8 (punto 1): control de calidad de la serie 1981–2022 antes de las tendencias, como en la Tarea 1.

Pedido de Juan (26 nov): usar 1981–2022 en la fase 8, pero primero limpiar la serie como en la Tarea 1. Allí
(Analisis_De_Cuenca/scripts/07b, 07c y el control del registro largo en 18_calculos_informe.py) la regla fue:
NADA SE BORRA AQUÍ; el script detecta y mide, y lo que se excluya lo decide la persona y se declara en el código.

Chequeos (los mismos de la Tarea 1, con los umbrales de allá):
1. Básicos, por punto y hora, solo sobre 1981–1997 (lo de 1998–2022 ya pasó la fase 0): horas faltantes o repetidas,
   valores fuera de rango físico (T −15 a 45 °C; punto de rocío no más de 0.5 °C sobre la T; presión 55–95 kPa;
   ssrd ≥ 0; viento < 30 m/s) y, por día, Rs > Ra.
2. Rachas: 5 días seguidos o más con el mismo valor diario exacto (Tmáx, Tmín, ea, Rs, viento). Umbral de 07c.
3. Atípicos mensuales de la cuenca (ETo, Thornthwaite, T, ea, u2, Rs): 1.5 rangos intercuartiles fuera del
   cuartil de su MISMO mes del calendario (criterio de los diagramas de caja de la Tarea 1). Se listan, no se borran.
4. Homogeneidad (saltos): Pettitt sobre la diferencia o razón anual entre ERA5-Land y una serie de otra fuente, como
   hizo la Tarea 1 con la T (ERA5-Land menos MSWX de CAMELS-COL):
   - T: T media de ERA5-Land (cuenca, Voronoi) menos (Tmín + Tmáx)/2 de MSWX (CAMELS-COL, San Gil).
   - Rs: razón Rs de ERA5-Land / Rs de Hargreaves–Samani con la Tmáx − Tmín de MSWX (FAO-56 ec. 50, kRs = 0.16,
     interior). MSWX no es del todo independiente de ERA5 (se construye a partir de él y se corrige con estaciones);
     es la única serie de temperatura que llega a 1981 en los datos del proyecto. Se declara.
   - Rs frente a la lluvia de CHIRPS (CAMELS-COL; satélite y estaciones, independiente de ERA5): residuo de la
     regresión de la anomalía mensual de Rs sobre la anomalía de P (meses nublados = lluviosos). Si la relación
     cambia de nivel, Pettitt lo encuentra en el residuo anual.
   Pettitt con la misma aproximación de p de la Tarea 1 (scripts 07c y 18).

Escribe productos/punto1/control_calidad_1981_2022.csv (un renglón por chequeo), control_calidad_atipicos_1981_2022.csv
y control_calidad_homogeneidad_1981_2022.png.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/punto1/42_control_calidad_1981_2022.py
"""

import importlib.util
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_DATOS = RAIZ_ENTREGA / "datos" / "punto1" / "era5land_puntos"
CARPETA_PRODUCTOS = RAIZ_ENTREGA / "productos" / "punto1"
ARCHIVO_CAMELS = (RAIZ_ENTREGA / "datos" / "punto1" / "camels_col" / "hydromet" / "3_Hydrometeorological_data"
                  / "Hydromet_data_24027010.txt")
SALIDA = CARPETA_PRODUCTOS / "control_calidad_1981_2022.csv"
SALIDA_ATIPICOS = CARPETA_PRODUCTOS / "control_calidad_atipicos_1981_2022.csv"
SALIDA_FIGURA = CARPETA_PRODUCTOS / "control_calidad_homogeneidad_1981_2022.png"
# Solo el panel de la Rs frente a CHIRPS, la evidencia del escalón que se corrige (va al anexo del informe; Juan, 26 nov)
SALIDA_FIGURA_RS = CARPETA_PRODUCTOS / "escalon_rs_chirps_1981_2022.png"
PANEL_RS = "residuo de Rs frente a la lluvia de CHIRPS"

# Umbrales (los de la Tarea 1 donde existen)
T_MIN, T_MAX = -15.0, 45.0           # °C, 07b: solo busca imposibles
TOLERANCIA_ROCIO = 0.5               # °C, Td puede pasar a T por redondeo, no más
P_MIN, P_MAX = 55.0, 95.0            # kPa, la cuenca va de ~1 100 a ~4 300 m
VIENTO_MAX = 30.0                    # m/s
SSRD_TOLERANCIA = 10.0               # J/m² por hora: ruido de redondeo, nada frente a ~2·10⁷ J/m² de un día
RACHA_DIAS = 5                       # 07c
FACTOR_ATIPICO = 1.5                 # 18_calculos_informe.py
ALFA = 0.05
KRS = 0.16                           # FAO-56 ec. 50, zonas interiores
LATITUD_CUENCA = 6.2                 # grados, centro aproximado de la cuenca (para Ra en Hargreaves–Samani)


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, Path(__file__).with_name(archivo))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


rn03 = cargar("series_diarias_rn", "03_series_diarias_rn.py")
t36 = cargar("tendencias_1981", "36_tendencias_demanda_1981_2022.py")
PESOS = t36.PESOS
filas = []


def registrar(chequeo, n_revisados, n_marcados, detalle):
    filas.append({"chequeo": chequeo, "revisados": n_revisados, "marcados": n_marcados,
                  "resultado": "sin problemas" if n_marcados == 0 else "revisar", "detalle": detalle})


def pettitt(x):
    """Prueba de Pettitt (1979): índice del último valor del primer tramo y p aproximada (igual que la Tarea 1)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    u = np.array([np.sign(x[: k + 1, None] - x[None, k + 1:]).sum() for k in range(n - 1)])
    k = int(np.argmax(np.abs(u)))
    return k, min(1.0, 2 * np.exp(-6 * float(abs(u[k])) ** 2 / (n ** 3 + n ** 2)))


# ---------------------------------------------------------------- 1. básicos sobre las horas de 1981–1997
def basicos():
    for n in t36.PUNTOS:
        h = pd.read_csv(CARPETA_DATOS / f"punto_{n}_1981_1997.csv", parse_dates=["valid_time"])
        esperadas = pd.date_range("1981-01-01 00:00", "1997-12-31 23:00", freq="h")
        faltan = len(esperadas.difference(h["valid_time"]))
        repetidas = int(h["valid_time"].duplicated().sum())
        nulos = int(h[["t2m", "d2m", "sp", "u10", "v10", "ssrd"]].isna().sum().sum())
        t, td = h["t2m"] - 273.15, h["d2m"] - 273.15
        fuera = {
            "T fuera de −15 a 45 °C": int(((t < T_MIN) | (t > T_MAX)).sum()),
            "punto de rocío > T + 0.5 °C": int((td > t + TOLERANCIA_ROCIO).sum()),
            "presión fuera de 55–95 kPa": int(((h["sp"] / 1000 < P_MIN) | (h["sp"] / 1000 > P_MAX)).sum()),
            # ERA5 deja valores de −1 a −4 J/m² a las 00 UTC (19 h local, de noche) por redondeo del pos-proceso; también
            # están en 1998–2022 y no pesan nada en la Rs diaria (MJ/m²). Solo cuenta como problema bajo −SSRD_TOLERANCIA.
            f"ssrd < −{SSRD_TOLERANCIA:.0f} J/m²": int((h["ssrd"] < -SSRD_TOLERANCIA).sum()),
            "viento ≥ 30 m/s": int((np.hypot(h["u10"], h["v10"]) >= VIENTO_MAX).sum()),
        }
        registrar(f"punto {n}: horas faltantes, repetidas o vacías", len(esperadas), faltan + repetidas + nulos,
                  f"faltan {faltan}, repetidas {repetidas}, celdas vacías {nulos}")
        pequenas = h["ssrd"][(h["ssrd"] < 0) & (h["ssrd"] >= -SSRD_TOLERANCIA)]
        registrar(f"punto {n}: ssrd entre −{SSRD_TOLERANCIA:.0f} y 0 J/m² (anotado, de noche)", len(h), 0,
                  f"{len(pequenas)} horas, mínimo {pequenas.min() if len(pequenas) else 0:.0f} J/m²; no se corrige")
        for chequeo, k in fuera.items():
            registrar(f"punto {n}: {chequeo}", len(h), k, "horas 1981–1997")


# ---------------------------------------------------------------- 2. rachas y Rs > Ra, sobre los diarios
def rachas_y_ra(diaria):
    vieja = diaria[diaria["fecha"] < "1998-01-01"]
    for n, d in vieja.groupby("punto"):
        registrar(f"punto {n}: Rs diaria > Ra", len(d), int((d["rs_MJm2"] > d["ra_MJm2"]).sum()), "días 1981–1997")
        registrar(f"punto {n}: Tmín ≤ Tmedia ≤ Tmáx", len(d),
                  int((~((d["tmin_C"] <= d["tmedia_C"]) & (d["tmedia_C"] <= d["tmax_C"]))).sum()), "días 1981–1997")
        for col in ("tmax_C", "tmin_C", "ea_kPa", "rs_MJm2", "viento10_ms"):
            v = d[col].round(4)
            largo = v.groupby((v != v.shift()).cumsum()).size()
            registrar(f"punto {n}: rachas de {RACHA_DIAS}+ días iguales en {col}", len(d),
                      int((largo >= RACHA_DIAS).sum()), "días 1981–1997")


# ---------------------------------------------------------------- 3. atípicos mensuales
def atipicos(tabla):
    marcas = []
    for v in ("eto", "thornthwaite", "t", "ea", "u2", "rs"):
        s = tabla[v]
        for m in range(1, 13):
            x = s[s.index.month == m]
            q1, q3 = x.quantile(0.25), x.quantile(0.75)
            ric = q3 - q1
            for p, val in x.items():
                if val > q3 + FACTOR_ATIPICO * ric or val < q1 - FACTOR_ATIPICO * ric:
                    marcas.append({"variable": v, "mes": str(p), "valor": val,
                                   "tipo": "alto" if val > q3 else "bajo",
                                   "z_ric": (val - x.median()) / ric, "tramo": "1981–1997" if p.year < 1998 else "1998–2022"})
    marcas = pd.DataFrame(marcas)
    for v in ("eto", "thornthwaite", "t", "ea", "u2", "rs"):
        m = marcas[marcas["variable"] == v] if len(marcas) else marcas
        antes = int((m["tramo"] == "1981–1997").sum()) if len(m) else 0
        despues = int((m["tramo"] == "1998–2022").sum()) if len(m) else 0
        registrar(f"atípicos mensuales de {v} (1.5 RIC por mes del calendario)", len(tabla), antes + despues,
                  f"1981–1997: {antes} de 204 meses; 1998–2022: {despues} de 300 meses (se listan, no se borran)")
    return marcas


# ---------------------------------------------------------------- 4. homogeneidad contra otras fuentes
def homogeneidad(diaria, tabla):
    cam = pd.read_csv(ARCHIVO_CAMELS, sep="\t", encoding="latin-1")
    cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
    cam["fecha"] = pd.to_datetime(cam["fecha"], format="%d/%m/%Y")
    cam = cam.set_index("fecha").loc["1981-01-01":"2022-12-31"]
    assert cam[["t_min", "t_max", "p_chirps"]].notna().all().all()

    # T: ERA5-Land (cuenca) menos MSWX, anual
    t_mswx = ((cam["t_min"] + cam["t_max"]) / 2).groupby(cam.index.year).mean()
    t_era = tabla["t"].groupby(tabla.index.year).mean()
    dif_t = (t_era - t_mswx).dropna()

    # Rs: ERA5-Land / Hargreaves–Samani con MSWX (FAO-56 ec. 50), anual
    ra = rn03.radiacion_extraterrestre(LATITUD_CUENCA, cam.index.day_of_year.to_numpy())
    rs_hs = pd.Series(KRS * np.sqrt((cam["t_max"] - cam["t_min"]).clip(lower=0)) * ra, index=cam.index)
    rs_hs_anual = rs_hs.groupby(rs_hs.index.year).mean()
    rs_era_anual = tabla["rs"].groupby(tabla.index.year).mean()
    razon_rs = (rs_era_anual / rs_hs_anual).dropna()

    # Rs frente a CHIRPS: residuo de anomalía de Rs ~ anomalía de P (mensual), promediado por año
    p_mes = cam["p_chirps"].resample("MS").sum()
    p_mes.index = p_mes.index.to_period("M")
    rs_mes = tabla["rs"]
    anom = lambda s: s - s.groupby(s.index.month).transform("mean")  # noqa: E731
    a_rs, a_p = anom(rs_mes), anom(p_mes.reindex(rs_mes.index))
    b = np.polyfit(a_p, a_rs, 1)
    residuo = (a_rs - np.polyval(b, a_p)).groupby(rs_mes.index.year).mean()

    resultados = {}
    for nombre, serie, unidad in (("T ERA5-Land − T MSWX", dif_t, "°C"),
                                  ("Rs ERA5-Land / Rs Hargreaves–Samani (MSWX)", razon_rs, "razón"),
                                  (PANEL_RS, residuo, "MJ/m²·d")):
        k, p = pettitt(serie.to_numpy())
        antes, despues = serie.iloc[: k + 1].mean(), serie.iloc[k + 1:].mean()
        resultados[nombre] = (serie, k, p)
        registrar(f"homogeneidad: {nombre} (Pettitt, anual)", len(serie), int(p < ALFA),
                  f"corte después de {serie.index[k]}, p = {p:.3f}; media antes {antes:.3f} y después {despues:.3f} {unidad}"
                  f" (salto {despues - antes:+.3f})")
    registrar("pendiente de Rs frente a P (CHIRPS), anomalías mensuales", len(a_rs), 0,
              f"{b[0] * 100:.3f} MJ/m²·d por cada 100 mm de lluvia de más en el mes")
    return resultados


def figura(resultados):
    fig, ejes = plt.subplots(3, 1, figsize=(6.5, 8), sharex=True)
    for ax, (nombre, (serie, k, p)) in zip(ejes, resultados.items()):
        ax.plot(serie.index, serie.to_numpy(), "o-", ms=3, color="#0072B2")
        antes, despues = serie.iloc[: k + 1].mean(), serie.iloc[k + 1:].mean()
        ax.hlines([antes, despues], [serie.index[0], serie.index[k] + 0.5], [serie.index[k] + 0.5, serie.index[-1]],
                  colors="#D55E00", lw=2, label=f"Pettitt: corte tras {serie.index[k]}, p = {p:.3f}")
        ax.axvline(1997.5, color="k", ls=":", lw=1)
        ax.set_title(nombre, fontsize=10)
        ax.legend(fontsize=8, loc="best")
    ejes[-1].set_xlabel("año")
    fig.tight_layout()
    fig.savefig(SALIDA_FIGURA, dpi=150)
    plt.close(fig)


def figura_escalon_rs(resultados):
    """El panel de la Rs frente a CHIRPS solo: el escalón que corrige el script 36."""
    serie, k, p = resultados[PANEL_RS]
    antes, despues = serie.iloc[: k + 1].mean(), serie.iloc[k + 1:].mean()
    fig, ax = plt.subplots(figsize=(6.5, 3.9))
    ax.plot(serie.index, serie.to_numpy(), "o-", ms=3, color="#0072B2", label="residuo anual")
    ax.hlines([antes, despues], [serie.index[0], serie.index[k] + 0.5], [serie.index[k] + 0.5, serie.index[-1]],
              colors="#D55E00", lw=2,
              label=f"Pettitt: corte tras {serie.index[k]}, p = {p:.3f}; salto {despues - antes:+.3f} MJ/m²·d")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("año")
    ax.set_ylabel("residuo de Rs (MJ/m²·d)")
    ax.set_title("Rs de ERA5-Land no explicada por la lluvia de CHIRPS, media anual", fontsize=10)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(SALIDA_FIGURA_RS, dpi=150)
    plt.close(fig)


def main():
    basicos()
    diaria = t36.diaria_completa()
    rachas_y_ra(diaria)
    tabla = t36.demanda_mensual(diaria)
    marcas = atipicos(tabla)
    resultados = homogeneidad(diaria, tabla)
    figura(resultados)
    figura_escalon_rs(resultados)
    salida = pd.DataFrame(filas)
    salida.to_csv(SALIDA, index=False)
    marcas.round(4).to_csv(SALIDA_ATIPICOS, index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 120)
    print(salida[salida["resultado"] == "revisar"].to_string())
    print(salida[salida["chequeo"].str.startswith(("homogeneidad", "pendiente", "atípicos"))][["chequeo", "detalle"]].to_string())
    print(f"Revisados {len(salida)} chequeos; marcados {int((salida['resultado'] == 'revisar').sum())}. "
          f"Listo: {SALIDA.name}, {SALIDA_ATIPICOS.name}, {SALIDA_FIGURA.name}, {SALIDA_FIGURA_RS.name}")


if __name__ == "__main__":
    main()
