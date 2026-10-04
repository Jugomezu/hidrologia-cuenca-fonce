"""Trazabilidad (sección 4.4 del notebook): registro de las anomalías encontradas en los datos, con lo que
se comprobó, lo que se decidió, el efecto en el análisis y el estado en que quedó cada una.

Este script no detecta ni decide nada nuevo: reúne en una tabla lo que ya hicieron 07 (exclusiones de PL),
07b (control básico), 07c (anomalías), 06b (ETP), 13 (morfometría) y 16 (series mensuales), y las cifras
de cada fila las lee de sus salidas. Así, si cambia un dato, el registro cambia con él.

Estados:
  corregido   el problema se resolvió (se excluyó el tramo, se cambió la fuente o el cálculo);
  incierto    se conserva el dato, pero no hay forma de saber si está bien; se arrastra y se advierte;
  descartado  se revisó y no resultó ser un problema.

Ejecutar desde la raíz del proyecto: python scripts/07d_trazabilidad.py
Salida: out/registro_anomalias.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")   # la consola de Windows no imprime signos como − o ·

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
DIAS = pd.date_range("1998-01-01", "2022-12-31", freq="D")
MAX_DIAS_FALTANTES = 4      # la regla del proyecto: un mes con 5 o más días faltantes queda vacío


def miles(x, dec=0):
    """Número con punto decimal y espacio para los miles (regla 14)."""
    return f"{x:,.{dec}f}".replace(",", " ")


# ---------------------------------------------------------------- lectura de lo que ya produjo la tubería
exclusiones = pd.read_csv(OUT / "pluviometros_exclusiones.csv")
homog = pd.read_csv(OUT / "anomalias_homogeneidad.csv").set_index("serie")
segundo = pd.read_csv(OUT / "anomalias_segundo_corte.csv").set_index("serie")
ceros = pd.read_csv(OUT / "anomalias_ceros_pl.csv")
cobertura = pd.read_csv(OUT / "anomalias_cobertura_pl.csv")
rachas = pd.read_csv(OUT / "anomalias_rachas.csv")
picos = pd.read_csv(OUT / "anomalias_picos_q.csv")
plu_crudo = pd.read_csv(OUT / "pluviometros_fonce_mensual_1998_2022.csv")
catalogo = pd.read_csv(OUT / "pluviometros_fonce_catalogo.csv")
variables = pd.read_csv(OUT / "variables_mensuales.csv", index_col=0)
morfometria = pd.read_csv(OUT / "morfometria_fonce.csv").set_index("magnitud")
etp = pd.read_csv(OUT / "etp_hargreaves_fonce.csv", parse_dates=["fecha"]).set_index("fecha").loc["1998":"2022"]
cam = pd.read_csv(RAIZ / f"data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_{ID_PRINCIPAL}.txt",
                  sep="\t", encoding="latin-1")
cam.columns = ["fecha", "p_chirps", "etp", "t_min", "t_max", "caudal"]
cam["fecha"] = pd.to_datetime(cam.fecha, format="%d/%m/%Y")
q_dia = cam.set_index("fecha").caudal.reindex(DIAS)

# ---------------------------------------------------------------- cifras de cada fila
excl = exclusiones.set_index(["codigo", "desde"]).meses_excluidos
meses_encino = int(excl[(24020040, "2016-01")])
meses_pueblo_viejo = int(excl[(24020230, "1998-01")])
meses_en_cero = int(exclusiones[exclusiones.solo_si_cero].meses_excluidos.sum())
pv, co, pi_h = homog.loc["PL · Pueblo Viejo"], homog.loc["PL · Coromoro"], homog.loc["PI (IMERG)"]
# segundo corte (07c, paso 1b): en el tramo que queda después del primer salto
pv2, co2, pi_sin_pv = segundo.loc["PL · Pueblo Viejo"], segundo.loc["PL · Coromoro"], segundo.loc["PI (IMERG)"]
# los textos de las filas de Pueblo Viejo, Coromoro y PI dan por hecho lo que sigue; si los datos cambian y deja
# de cumplirse, el script se detiene en vez de escribir un registro equivocado
assert pv2.significativo and not co2.significativo
assert pi_sin_pv.referencia == "PL sin Pueblo Viejo"
assert pi_h.significativo and not pi_sin_pv.significativo and abs(pi_sin_pv.cambio_pct) < abs(pi_h.cambio_pct)

ceros_creibles = ceros[~ceros.dificil_de_creer]
ceros_creibles_txt = "; ".join(f"{f.pluviometro} {f.periodo} (el vecino más seco midió {f.otros_minimo_mm:.1f} mm)"
                               for f in ceros_creibles.itertuples())

# sesgo PI frente a PL en los 300 meses (como en la sección 4.3): PL es el promedio de los pluviómetros
# dentro de la divisoria que tienen dato, en la serie depurada
dentro = catalogo[catalogo.dentro_cuenca].codigo
plu = pd.read_csv(OUT / "pluviometros_fonce_mensual_depurado.csv", parse_dates=["fecha"])
pl = plu[plu.codigo.isin(dentro)].pivot_table(index="fecha", columns="codigo", values="precipitacion_mm").mean(axis=1)
pl.index = pl.index.to_period("M").astype(str)
imerg = pd.read_csv(OUT / "imerg_mensual_fonce.csv")
pi = imerg[imerg.id_estacion == ID_PRINCIPAL].set_index("periodo").p_imerg_mm
par = pd.concat([pi.rename("PI"), pl.rename("PL")], axis=1).loc["1998-01":"2022-12"].dropna()
sesgo_pi_pl = (par.PI.mean() / par.PL.mean() - 1) * 100

sesgo_cob = cobertura.sesgo_estimado_pct.abs()

aprob = plu_crudo[plu_crudo.codigo.isin(dentro)].nivel_aprobacion.value_counts()
pct_preliminar = aprob.get("Preliminar", 0) / aprob.sum() * 100

dias_sin_fila = int(q_dia.isna().sum())
faltan_por_mes = q_dia.isna().groupby(q_dia.index.to_period("M")).sum()
meses_incompletos = faltan_por_mes[(faltan_por_mes > 0) & (faltan_por_mes <= MAX_DIAS_FALTANTES)]
# si solo se sumaran los días con dato, el mes quedaría corto en la fracción de días que faltan
falta_suma_pct = meses_incompletos / meses_incompletos.index.days_in_month * 100

area = morfometria.loc["área"]
dif_area_pct = (area.publicado_camels / area.valor - 1) * 100
pend = morfometria.loc["pendiente del cauce (Taylor-Schwarz)"]
razon_etp = etp.etp_camels.sum() / etp.etp_mswx.sum()

# P − Q anual contra la ETP, con PL, en los años con los 12 meses de Q (mismo criterio que la sección 4.5)
anual = variables.assign(anio=variables.index.str[:4])
meses_q = anual.groupby("anio").Q.count()
anual = anual.groupby("anio")[["PL", "Q", "ETP"]].sum(min_count=12).loc[meses_q.index[meses_q == 12]]
anios_sobre_etp = list(anual.index[(anual.PL - anual.Q) > anual.ETP])

n_rachas_q_t = int((~rachas.variable.str.startswith("PL")).sum())
rachas_pl = rachas[rachas.variable.str.startswith("PL")]
rachas_pl_txt = "; ".join(f"{f.variable.split(' · ')[1].split(' (')[0]}, {miles(f.valor)} mm, {f.desde} a {f.hasta}"
                          for f in rachas_pl.itertuples())

# ---------------------------------------------------------------- el registro
registro = [
    dict(anomalia="Encino 2016–2018: totales anuales muy por encima del resto de su serie", serie="PL",
         comprobacion="se comparó contra PI y contra Q: ninguno de los dos acompaña esos años",
         decision=f"se excluye el tramo ({meses_encino} meses)",
         efecto="PL se calcula sin Encino esos años", estado="corregido", evidencia="1.7"),
    dict(anomalia=f"Pueblo Viejo hasta {pv.ultimo_mes_antes}: mide {pv.razon_antes:.2f} veces lo de sus vecinos; "
                  f"desde {pv.primer_mes_despues}, {pv.razon_despues:.2f}", serie="PL",
         comprobacion=f"doble masa y prueba de Pettitt (p = {pv.p:.0e}); el catálogo del IDEAM no registra el cambio",
         decision=f"se excluye el tramo ({meses_pueblo_viejo} meses)",
         efecto="PL se calcula sin Pueblo Viejo en ese tramo", estado="corregido", evidencia="4.3"),
    dict(anomalia=f"Pueblo Viejo desde {pv2.primer_mes_despues}: pasa de {pv2.razon_antes:.2f} a "
                  f"{pv2.razon_despues:.2f} veces sus vecinos ({pv2.cambio_pct:+.1f} %)", serie="PL",
         comprobacion=f"prueba de Pettitt sobre el tramo desde {pv2.tramo_desde}, contra los demás pluviómetros "
                      f"sin Pueblo Viejo ni Coromoro (p = {pv2.p:.0e}); es un segundo salto, que la prueba sobre la "
                      "serie completa no ve porque solo encuentra un corte por serie",
         decision="se conserva", efecto="PL puede estar algo baja desde ese mes", estado="incierto",
         evidencia="4.3"),
    dict(anomalia=f"{meses_en_cero} meses en 0 mm difíciles de creer (Pavas Las y Valle de San José)", serie="PL",
         comprobacion="todos los demás pluviómetros midieron más de 20 mm ese mes",
         decision="se excluyen como meses no registrados", efecto="esos meses PL se promedia sin ese pluviómetro",
         estado="corregido", evidencia="4.3"),
    dict(anomalia=f"{len(ceros_creibles)} meses en 0 mm creíbles", serie="PL",
         comprobacion=ceros_creibles_txt, decision="se conservan",
         efecto="ninguno", estado="descartado", evidencia="4.3"),
    dict(anomalia=f"Coromoro: de {co.razon_antes:.2f} a {co.razon_despues:.2f} veces sus vecinos desde "
                  f"{co.primer_mes_despues} ({co.cambio_pct:+.1f} %)", serie="PL",
         comprobacion=f"doble masa y prueba de Pettitt (p = {co.p:.3f}); el cambio es gradual y no se sabe cuál "
                      f"tramo está bien; en el tramo posterior no hay un segundo salto (p = {co2.p:.2f})",
         decision="se conserva", efecto="PL puede estar algo baja desde ese mes", estado="incierto",
         evidencia="4.3"),
    dict(anomalia=f"PI sube {pi_h.cambio_pct:+.1f} % frente a PL desde {pi_h.primer_mes_despues}", serie="PI",
         comprobacion=f"prueba de Pettitt (p = {pi_h.p:.3f}); con PL sin Pueblo Viejo el salto baja a "
                      f"{pi_sin_pv.cambio_pct:+.1f} % y deja de ser significativo (p = {pi_sin_pv.p:.2f}): buena "
                      "parte viene del segundo salto de Pueblo Viejo; el cambio de calibración de IMERG de TRMM a "
                      "GPM el 1 de junio de 2014 (documentación técnica de IMERG V07) puede aportar algo, pero no "
                      "es la explicación principal",
         decision="se conserva", efecto="la razón PI / PL no es homogénea antes y después de 2014", estado="incierto",
         evidencia="4.3"),
    dict(anomalia=f"PI queda {abs(sesgo_pi_pl):.1f} % por debajo de PL", serie="PI y PL",
         comprobacion=f"promedio de los {len(par)} meses: {par.PI.mean():.1f} mm/mes con PI y {par.PL.mean():.1f} con PL",
         decision="no se corrige ninguna: todo análisis de lluvia se hace con PI y con PL; si hay que escoger, "
                  "manda PL",
         efecto="los resultados se reportan con las dos fuentes", estado="incierto", evidencia="1.2"),
    dict(anomalia=f"En {len(cobertura)} meses faltan pluviómetros en PL", serie="PL",
         comprobacion=f"sesgo estimado frente al promedio de los 7: mediana {sesgo_cob.median():.1f} %, "
                      f"máximo {sesgo_cob.max():.1f} %",
         decision="no se rellena: cada mes se promedia con los pluviómetros que tienen dato",
         efecto="PL de esos meses puede quedar algo alta o baja", estado="incierto", evidencia="4.3"),
    dict(anomalia=f"{pct_preliminar:.0f} % de los registros de PL son preliminares", serie="PL",
         comprobacion="nivel de aprobación del IDEAM en cada registro; preliminar quiere decir aún no validado, "
                      "no que tenga error",
         decision="se usan", efecto="ninguno directo", estado="incierto", evidencia="4.2"),
    dict(anomalia=f"{miles(dias_sin_fila)} días de 1998–2022 sin fila en el caudal de CAMELS-COL", serie="Q",
         comprobacion="conteo de días ausentes por mes",
         decision=f"un mes con {MAX_DIAS_FALTANTES + 1} o más días faltantes queda vacío",
         efecto=f"quedan {variables.Q.notna().sum()} meses de Q", estado="corregido", evidencia="4.1"),
    dict(anomalia="Acumulados de meses incompletos calculados como suma parcial", serie="Q",
         comprobacion=f"{len(meses_incompletos)} meses con 1 a {MAX_DIAS_FALTANTES} días faltantes quedarían en "
                      f"promedio {falta_suma_pct.mean():.1f} % por debajo (hasta {falta_suma_pct.max():.1f} %)",
         decision="el acumulado es el promedio de los días con dato por los días del mes",
         efecto="esos meses ya no quedan cortos", estado="corregido", evidencia="4.1"),
    dict(anomalia=f"El área que publica CAMELS-COL es {dif_area_pct:.1f} % mayor que su propio polígono",
         serie="área", comprobacion=f"área geodésica del polígono: {miles(area.valor, 2)} km², contra "
                                    f"{miles(area.publicado_camels, 2)} km² publicados",
         decision="se usa el área del polígono", efecto="Q en mm y todo lo que depende del área",
         estado="corregido", evidencia="2.5"),
    dict(anomalia="La pendiente del cauce que publica CAMELS-COL (equi_slope) es demasiado baja",
         serie="pendiente", comprobacion=f"Taylor-Schwarz con el DEM: {pend.valor:.4f} m/m, contra "
                                         f"{pend.publicado_camels:.2e} m/m publicados",
         decision="se usa la pendiente calculada por el proyecto", efecto="tiempos de concentración y morfometría",
         estado="corregido", evidencia="2.5"),
    dict(anomalia=f"La ETP de CAMELS-COL es {razon_etp:.2f} veces la de su propia fórmula", serie="ETP",
         comprobacion="se repitió la fórmula de Hargreaves con los mismos datos (MSWX)",
         decision="se usa la ETP de Hargreaves calculada por el proyecto con ERA5-Land",
         efecto="toda comparación con la ETP", estado="corregido", evidencia="1.8"),
    dict(anomalia="La temperatura media de MSWX en CAMELS-COL es el punto medio entre mínima y máxima, y "
                  "hereda los huecos del caudal", serie="temperatura",
         comprobacion="se comparó con ERA5-Land, que trae la media diaria verdadera y no tiene huecos",
         decision="se usa ERA5-Land; MSWX queda solo para comparar", efecto="temperatura y ETP",
         estado="corregido", evidencia="1.5"),
    dict(anomalia="Meses atípicos (fuera de 1.5 rangos intercuartiles de su mes del calendario), entre ellos "
                  "febrero de 1999, el más lluvioso del período", serie="PI, PL, Q y temperatura",
         comprobacion="se cruzaron entre variables y con el ONI (El Niño y La Niña)",
         decision="no se elimina ninguno", efecto="ninguno", estado="incierto", evidencia="1.0"),
    dict(anomalia=f"Años en que P − Q supera a la ETP con PL: {', '.join(anios_sobre_etp) or 'ninguno'}",
         serie="PL y Q", comprobacion=f"se probaron cuatro explicaciones; la recarga del suelo no explica "
                                      f"{anios_sobre_etp[0]}, y apunta a PL sobrestimada en los años sin Pueblo Viejo",
         decision="se conservan y se anotan", efecto="el balance de esos años es dudoso", estado="incierto",
         evidencia="4.5"),
    dict(anomalia="Secuencias constantes y picos aislados", serie="PL, Q y temperatura",
         comprobacion=f"{n_rachas_q_t} rachas de 5 o más días iguales en Q y temperatura; {len(rachas_pl)} de "
                      f"2 meses iguales en PL ({rachas_pl_txt}); {len(picos)} picos aislados en Q",
         decision="sin acción: dos meses iguales pueden coincidir por azar", efecto="ninguno",
         estado="descartado", evidencia="4.3"),
]
tabla = pd.DataFrame(registro)
tabla.insert(0, "n", range(1, len(tabla) + 1))
assert tabla.estado.isin(["corregido", "incierto", "descartado"]).all()
tabla.to_csv(OUT / "registro_anomalias.csv", index=False)

pd.set_option("display.max_colwidth", 90, "display.width", 200)
print(tabla[["n", "serie", "anomalia", "estado"]].to_string(index=False))
print("\n" + tabla.estado.value_counts().to_string())
print("\nGuardado: out/registro_anomalias.csv")
