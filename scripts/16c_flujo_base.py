"""Flujo base e índice de flujo base (BFI) de San Gil con el filtro de Lyne-Hollick en la versión de Ladson et al. (2013).

El caudal diario Q se separa en dos partes: el flujo rápido, que sube y baja con cada tormenta, y el flujo base, la parte
lenta que sostiene al río entre tormentas (agua subterránea y subsuperficial). El BFI es la fracción del caudal que es
flujo base: BFI = suma del flujo base / suma de Q.

El método (elegido por el usuario el 2026-10-11, frente a Eckhardt, porque es el que usa CAMELS-COL para su
`baseflow_index` y todos sus parámetros son fijos):
  1. Filtro de Lyne y Hollick (1979). Día a día, el flujo rápido es
         qf(t) = ALFA * qf(t-1) + (1 + ALFA) / 2 * [Q(t) - Q(t-1)],
     acotado entre 0 y Q(t), y el flujo base es b(t) = Q(t) - qf(t).
  2. Receta de Ladson et al. (2013): ALFA = 0.925; tres pasadas (hacia adelante, hacia atrás sobre el flujo base de la
     primera y otra vez hacia adelante); y antes de filtrar se reflejan REFLEJO días al comienzo y al final de la serie
     para que el filtro "arranque" antes de los datos reales. Esos días reflejados se quitan al terminar.

Los días faltantes no se rellenan (regla 1). Al archivo de CAMELS-COL le faltan días como filas ausentes, así que la
serie se lleva al calendario completo y el filtro se corre por separado en cada tramo continuo con dato; los tramos de
menos de TRAMO_MINIMO días se descartan, porque no alcanzan para el reflejo. El BFI se calcula solo con los días que
pasaron por el filtro.

Dos períodos (regla 6): 1998-2022, el período del informe, y 1981-2022, el registro completo, que es el que usa
CAMELS-COL y sirve para comparar con su valor publicado. Los días anteriores a 1998 no han pasado por el control de
calidad del proyecto; aquí se usan tal como vienen.

Referencias:
  Lyne, V. y Hollick, M. (1979). Stochastic time-variable rainfall-runoff modelling. Institution of Engineers
    Australia National Conference, 89-93.
  Ladson, A. R., Brown, R., Neal, B. y Nathan, R. (2013). A standard approach to baseflow separation using the Lyne and
    Hollick filter. Australasian Journal of Water Resources, 17(1), 25-34. https://doi.org/10.7158/W12-028.2013.17.1

Salidas:
  out/flujo_base_diario.csv    fecha, caudal, flujo_base (m³/s); 1981-2022 en el calendario completo, vacío donde no
                               hay dato o el tramo es demasiado corto
  out/flujo_base_bfi.csv       un renglón por período: días, tramos, BFI de Ladson y el baseflow_index de CAMELS-COL
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ID_PRINCIPAL = "24027010"            # San Gil
ALFA = 0.925                         # parámetro del filtro (Ladson et al., 2013)
PASADAS = 3                          # adelante, atrás, adelante (Ladson et al., 2013)
REFLEJO = 30                         # días reflejados en cada extremo (Ladson et al., 2013)
TRAMO_MINIMO = REFLEJO + 1           # un tramo más corto no alcanza para reflejar REFLEJO días
PERIODOS = {"1998-2022": ("1998-01-01", "2022-12-31"),
            "1981-2022": ("1981-01-01", "2022-12-31")}

# --- caudal diario de CAMELS-COL, llevado al calendario completo (los días ausentes quedan vacíos)
cam = pd.read_csv(RAIZ / f"data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_{ID_PRINCIPAL}.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam["fecha"], format="%d/%m/%Y")
inicio, fin = min(p[0] for p in PERIODOS.values()), max(p[1] for p in PERIODOS.values())
caudal = cam.set_index("fecha").sort_index()["caudal"].reindex(pd.date_range(inicio, fin, freq="D"))

# --- el baseflow_index que publica CAMELS-COL para San Gil, para comparar
firmas = pd.read_csv(RAIZ / "data/camels_col/09_CAMELS_COL_Hydrological_signatures.csv", dtype={"gauge_id": str})
bfi_camels = float(firmas.set_index("gauge_id").loc[ID_PRINCIPAL, "baseflow_index"])


def pasada_lyne_hollick(q, alfa):
    """Una pasada del filtro hacia adelante: devuelve el flujo base. El flujo rápido arranca en 0 y en cada día se
    acota entre 0 y el caudal de ese día, así que el flujo base nunca es negativo ni mayor que el caudal."""
    rapido = np.zeros_like(q)
    for t in range(1, len(q)):
        rapido[t] = alfa * rapido[t - 1] + (1 + alfa) / 2 * (q[t] - q[t - 1])
        rapido[t] = min(max(rapido[t], 0.0), q[t])
    return q - rapido


def flujo_base_ladson(q, alfa=ALFA, pasadas=PASADAS, reflejo=REFLEJO):
    """Flujo base de un tramo continuo de caudal con la receta de Ladson et al. (2013)."""
    # Reflejo: los días 2 a reflejo+1 en espejo antes del comienzo, y los penúltimos en espejo después del final
    extendido = np.concatenate([q[reflejo:0:-1], q, q[-2:-reflejo - 2:-1]])
    base = extendido
    for i in range(pasadas):
        if i % 2 == 0:                                       # pasadas 1 y 3: hacia adelante
            base = pasada_lyne_hollick(base, alfa)
        else:                                                # pasada 2: hacia atrás
            base = pasada_lyne_hollick(base[::-1], alfa)[::-1]
    return base[reflejo:-reflejo]


def tramos_continuos(serie):
    """Lista de (inicio, fin) en posiciones de la serie, de los tramos sin días vacíos."""
    con_dato = serie.notna().to_numpy().astype(int)
    cambios = np.flatnonzero(np.diff(np.concatenate([[0], con_dato, [0]])))
    return list(zip(cambios[::2], cambios[1::2]))


# --- filtro sobre el registro completo, tramo por tramo
flujo_base = pd.Series(np.nan, index=caudal.index)
for i, j in tramos_continuos(caudal):
    if j - i >= TRAMO_MINIMO:
        flujo_base.iloc[i:j] = flujo_base_ladson(caudal.iloc[i:j].to_numpy())

assert (flujo_base.dropna() >= 0).all(), "el flujo base no puede ser negativo"
assert (flujo_base.dropna() <= caudal[flujo_base.notna()] + 1e-9).all(), "el flujo base no puede superar el caudal"

# --- BFI por período. El filtro se corre una vez sobre todo el registro; el período 1998-2022 es un recorte, así
# que un tramo que cruza el 1 de enero de 1998 se filtra completo (no se corta en esa fecha).
filas = []
for nombre, (desde, hasta) in PERIODOS.items():
    q, b = caudal[desde:hasta], flujo_base[desde:hasta]
    usados = b.notna()
    filas.append({
        "periodo": nombre,
        "dias_calendario": len(q),
        "dias_con_dato": int(q.notna().sum()),
        "dias_usados": int(usados.sum()),
        "tramos": sum(1 for i, j in tramos_continuos(b) if j > i),
        "bfi_ladson": round(b[usados].sum() / q[usados].sum(), 3),
        "bfi_camels_col": bfi_camels,
    })
resumen = pd.DataFrame(filas)

(RAIZ / "out").mkdir(exist_ok=True)
pd.DataFrame({"fecha": caudal.index.date, "caudal": caudal.round(3).to_numpy(),
              "flujo_base": flujo_base.round(3).to_numpy()}).to_csv(RAIZ / "out/flujo_base_diario.csv", index=False)
resumen.to_csv(RAIZ / "out/flujo_base_bfi.csv", index=False)

print(f"Flujo base de San Gil ({ID_PRINCIPAL}) con Lyne-Hollick, receta de Ladson et al. (2013): "
      f"ALFA = {ALFA}, {PASADAS} pasadas, {REFLEJO} días reflejados; tramos de al menos {TRAMO_MINIMO} días")
print(resumen.to_string(index=False))
