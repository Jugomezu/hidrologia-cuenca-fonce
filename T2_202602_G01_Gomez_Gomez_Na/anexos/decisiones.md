# Decisiones

Registro de las decisiones tomadas y su razonamiento, en orden. Va en la entrega como anexo.

## 2026-11-12 · Punto 1 · Puntos de ERA5-Land

**Decisión.** Seis centros de celda de ERA5-Land (0.1°). El promedio de la cuenca pondera cada punto por el
área de su región de Voronoi.

| Punto | lon, lat | Altura celda (m) | Altura región (m) | Peso |
|---|---|---|---|---|
| 1 | −73.1, 6.0 | 3 259 | 3 122 | 0.124 |
| 2 | −73.1, 6.2 | 1 776 | 1 859 | 0.173 |
| 3 | −73.1, 6.3 | 1 580 | 1 688 | 0.120 |
| 4 | −73.1, 6.4 | 1 715 | 1 598 | 0.146 |
| 5 | −73.0, 6.1 | 3 066 | 3 128 | 0.186 |
| 6 | −73.0, 6.4 | 2 085 | 2 145 | 0.252 |

**Razonamiento.**
1. Se descargaron datos de celdas con al menos el 90 % de su área dentro de la cuenca, para que no las
   influyeran zonas externas.
2. La altura varía mucho en la cuenca (1 118 a 4 284 m), y con ella la temperatura, una de las variables que
   intervienen en la ET. Se buscó que cada punto tenga una altura parecida a la de su región y que haya uno en
   cada franja de altura de igual área.
3. Entre las 12 376 combinaciones posibles se tomó la de menor diferencia de altura ponderada (88 m).
4. Descartadas: las opciones de áreas iguales, porque ubicaban peor los puntos en altura o usaban celdas con
   parte fuera de la cuenca; y la D, porque no tenía punto en el valle bajo.
5. Limitación: las celdas suavizan el relieve, así que ninguna representa los picos sobre unos 3 500 m.

## 2026-11-12 · Punto 1 · Variables y período de ERA5-Land

**Decisión.** Se descargaron de `reanalysis-era5-land-timeseries`, en los 6 puntos y para 1998–2022 (horario), las
variables que pide la ETo de FAO-56 (ec. 6): `2m_temperature`, `2m_dewpoint_temperature`, `surface_pressure`,
`10m_u_component_of_wind`, `10m_v_component_of_wind` y `surface_solar_radiation_downwards`.

**Razonamiento.**
1. Cada término de la ec. 6 sale de una de ellas: T, Δ y es de `t2m`; ea de `d2m`; γ de `sp`; u2 del viento a
   10 m (ec. 47); Rn de `ssrd`. G ≈ 0 a escala diaria.
2. `sp` en vez de la presión por altura (ec. 7): así γ corresponde a la misma topografía del modelo que las
   demás variables.

## 2026-11-12 · Punto 1 · Días en hora local

**Decisión.** Los días se arman en hora local (UTC−5): la hora local es `valid_time` − 5 h.

**Razonamiento.** T máxima y T mínima deben corresponder al día de Colombia. La suma diaria de `ssrd` no cambia,
porque toda la luz del día cae dentro del mismo día UTC.

## 2026-11-12 · Punto 1 · Diciembre de 2022 incompleto en hora local

**Decisión.** Se deja así, sin descargar más horas.

**Razonamiento.** La descarga termina el 2022-12-31 a las 23:00 UTC, que son las 18:00 hora local, así que a
diciembre de 2022 le faltan sus últimas 5 horas (noche). El efecto es despreciable y se menciona como limitación.
En el otro extremo, la primera hora descargada (1998-01-01 00:00 UTC) es el 1997-12-31 a las 19:00 hora local;
esas 5 horas (19:00–23:00 del 1997-12-31) se descartan para que la serie empiece el 1998-01-01 00:00 hora local.

## 2026-11-12 · Punto 1 · Agregación mensual de ERA5-Land

**Decisión.** Por punto y mes (hora local): la radiación solar (`ssrd`) se suma (MJ/m²·mes); temperatura, punto
de rocío, presión y rapidez del viento se promedian; Tmax y Tmin mensuales son el promedio de las máximas y
mínimas diarias. La rapidez del viento se calcula cada hora, √(u10² + v10²), antes de promediar.

**Razonamiento.** Solo la radiación es una cantidad que se acumula (energía); las demás son estados del aire y su
suma no tiene sentido físico. La suma mensual de radiación ya refleja el número de días de cada mes. Se suma Rs,
no Rn: Rn no se descargó y se calcula después con FAO-56, a escala diaria.

## 2026-11-12 · Punto 1 · Radiación neta Rn (FAO-56)

**Decisión.** Rn diaria por punto con FAO-56 (ec. 21–40), α = 0.23, G = 0; Rn mensual = suma de las diarias.
ea = promedio diario de e°(Td) horario. En Rso (ec. 37), z = altura de la superficie del modelo, despejada de la
presión media `sp` con la ec. 7.

**Razonamiento.** Rn depende de Tmax, Tmin y ea del mismo día, así que se calcula diaria y luego se suma al mes.
z del modelo para que Rso corresponda a la misma superficie que Rs y T; Rso cambia solo 2.7 % por cada 1 000 m.

## 2026-11-12 · Punto 1 · ETo con FAO-56 (ec. 6)

**Decisión.** ETo diaria por punto con la ec. 6 de FAO-56: T = (Tmax + Tmin)/2 (ec. 9), es = media de e°(Tmax) y
e°(Tmin) (ec. 12), γ con la presión `sp` (ec. 8), u2 = 0.748 × rapidez a 10 m (ec. 47), G = 0. ETo mensual = suma
de las diarias; ETo de la cuenca = promedio de los 6 puntos ponderado por el área de Voronoi.

**Razonamiento.** Es la forma estándar de FAO-56 a escala diaria. La suma mensual se hace después del cálculo
diario porque la ecuación no es lineal.

## 2026-11-12 · Punto 1 · Rnl en días muy nublados

**Decisión.** Se deja la ec. 39 de FAO-56 tal cual, sin el límite inferior Rs/Rso ≥ 0.3 de ASCE-EWRI (2005).

**Razonamiento.** Afecta 121 de 54 786 días-punto (0.2 %), donde Rnl sale levemente negativa; el efecto en la
ETo es despreciable y se mantiene el método de FAO-56 sin modificaciones.

## 2026-11-12 · Punto 1 · Radiación horaria de ERA5-Land (nota para la metodología)

**Decisión.** En la metodología se dirá: «Se usó el producto de series de tiempo de ERA5-Land, en el que `ssrd` se
entrega como energía por hora (J/m²); la radiación diaria es la suma de las 24 horas del día local».

**Razonamiento.** En el ERA5-Land por malla (`reanalysis-era5-land`), `ssrd` viene acumulada desde las 00 UTC y
hay que desacumularla; en el producto de series de tiempo no. Se verificó en los datos: el ciclo diario sube y
baja, y la suma diaria (18.6 MJ/m² en promedio) queda bajo la radiación de cielo despejado. Así nadie confunde
nuestra suma con una suma de acumulados.

## 2026-11-13 · Punto 1 · Presión real de vapor e_a

**Decisión.** e_a diaria = promedio de las 24 e°(Td) horarias del día, no e°(Td media) como en la ec. 14 de FAO-56.

**Razonamiento.** Con datos horarios, promediar e_a es más fiel al ciclo diario; e° no es lineal en Td.

## 2026-11-17 · Punto 1 · Brillo solar de estaciones del IDEAM

**Decisión.** Se descargó de DHIME el brillo solar total diario de 1998–2022 de tres estaciones dentro de la cuenca:
Escuela Agrícola Mogotes (24025040, 1673 m), La Sierra (24025030, 2850 m) y Charalá (24025050, 1350 m). Archivo:
`datos/punto1/ideam_brillo_solar/brillo_solar_diario_1998_2022_3est.zip` (SHA-256 `1b8c3665…f724d`).

**Razonamiento.** No hay radiación medida en la cuenca; el brillo solar es lo más cercano para revisar Rs de ERA5-Land.
Son las únicas estaciones de la cuenca con serie larga en DHIME y cubren tres alturas. Las tres pasan el criterio de la
Tarea 1 (dato en ≥ 70 % de los meses): 96.3, 96.3 y 93.0 %. Medias de 5.42, 3.32 y 5.33 h/día, cercanas a las normales
1991–2020 del IDEAM. Todo el registro es «Preliminar». Se descartó Mogotes-AUT (24025090): solo tiene 2020–2022.

## 2026-11-17 · Punto 1 · Periodo de la ETo

**Decisión.** La ETo se queda en 1998–2022; no se extiende a 1981. Las tendencias de ETo y Thornthwaite del
apartado 1.4 también usan 1998–2022 (25 años).

**Razonamiento.** Es el periodo ya descargado y procesado, y el mismo de IMERG. Las tendencias de la Tarea 1 empiezan
en 1981, así que cualquier comparación de tendencias con ellas debe decir que los periodos no coinciden.

## 2026-11-17 · Punto 1 · TerraClimate (aet y pet)

**Decisión.** Se descargaron de TerraClimate v1.1, por OPeNDAP, la evapotranspiración real (`aet`) y la de
referencia (`pet`), mensuales, 1998–2022, recortadas a la cuenca (script 05). El promedio de cuenca pondera cada celda
de ~4 km por el área de su intersección con el polígono de CAMELS-COL.

**Razonamiento.** `aet` es un producto de ET real de la familia de balance hídrico (apartado 1.2); `pet` es un producto
independiente de demanda, Penman-Monteith de pasto de referencia (apartado 1.1.b). No requiere registro. Pendiente:
citar cómo define TerraClimate cada variable en su documentación.

## 2026-11-17 · Punto 1 · ETo con medias mensuales (comprobación)

**Decisión.** Cálculo aparte (script 04b): ETo de un "día medio" con las medias del mes de Tmax, Tmin, ea, P, viento
y Rs, por los días del mes. Ra del día J = int(30.4 M − 15). G mensual con la ec. 43, G = 0.07 (T_i+1 − T_i−1), como
pide el plan; en 1998-01 y 2022-12 falta un vecino y se usa la ec. 44. Se guarda también la versión con G = 0 para
separar el efecto de agregar del de G.

**Resultado.** Diferencia con la suma de diarias muy pequeña: en la cuenca, entre −1.2 y +0.8 % mes a mes; en promedio por
mes del año, de −0.5 % (enero) a +0.3 % (mayo). G aporta como mucho ~1 mm/mes. La suma de diarias sigue siendo la ETo
mensual oficial; esto la respalda. Tabla: `anexos/punto1/eto_medias_mensuales_vs_suma_diarias.csv`.

## 2026-11-17 · Punto 1 · Altura de los 6 puntos frente al DEM

**Resultado.** (script 04b) La altura del modelo (despejada de `sp`) queda entre −318 m (punto 5) y +224 m (punto 4) de la
media del DEM en su región de Voronoi; en promedio ponderado, 2 200 m frente a 2 265 m (65 m más baja). Con el gradiente
del propio ERA5-Land entre los 6 puntos (T −5.2 °C/km, ea −0.50 kPa/km), eso es +0.3 °C y +0.03 kPa en la cuenca; en el
punto 5, +1.7 °C. No se corrige: queda como limitación. Las alturas de celda del DEM coinciden con la tabla del 2026-11-12.
Las regiones de Voronoi se copiaron a `datos/punto1/era5land_puntos/regiones_voronoi_puntos.geojson`.

## 2026-11-17 · Punto 1 · Día verificado a mano

**Resultado.** `anexos/punto1/dia_verificado_a_mano.xlsx` (script 04c): 2010-02-15, punto 6, desde las 24 horas crudas
hasta la ETo, con fórmulas vivas. ETo = 3.76 mm/día; todos los pasos coinciden con los productos a 4 decimales. Juan lo
revisó a mano contra FAO-56 el 2026-11-17.

## 2026-11-17 · Punto 1 · Torre de flujo (covarianza de remolinos)

**Resultado.** No hay torre de flujo en la cuenca ni cerca. Se revisaron los listados de sitios de AmeriFlux (858 sitios)
y de FLUXNET (267 sitios) el 2026-11-17. Las únicas torres en Colombia son CO-GV1 y CO-GV2, en Guatavita (Cundinamarca),
en un humedal a 3000 m. Están a unos 159 km de la cuenca y miden desde 2023, así que no cubren 1998–2022. Después vienen
Panamá (PA-SPs y PA-SPn, a unos 800 km) y la Amazonia.

**Decisión.** No se usa torre de flujo. La ET real se contrasta solo entre productos (TerraClimate, ERA5-Land, SSEBop y
MOD16) y con el balance hídrico. Esto queda como limitación.

## 2026-11-17 · Punto 1 · Rs de estaciones (brillo solar) frente a ERA5-Land

**Decisión.** Rs de estación con Angstrom, FAO-56 ec. 35, Rs = (0.25 + 0.50 n/N) Ra, con N de la ec. 34 y Ra de la ec. 21
en la latitud de la estación. a_s = 0.25 y b_s = 0.50 son los que FAO-56 recomienda sin calibración local (cap. 3,
ec. 35 en la p. 50 del PDF, verificada por Juan el 2026-11-19). Cada estación se compara con el más cercano de
los 6 puntos ya descargados, no con la celda que la contiene (no está descargada). Solo días con brillo solar; no se
rellena. Se descarta el día con n > N (no hubo ninguno). Script 12.

**Resultado.** Sesgo ERA5-Land − estación (todo el periodo) y RMSE diario, en MJ/m²·día:
Mogotes 24025040 (punto 6, 8.5 km, estación 412 m bajo la celda del DEM): +1.89 (+11.1 %), RMSE 3.44.
La Sierra 24025030 (punto 1, 7.8 km, 409 m bajo): +4.81 (+34.7 %), RMSE 5.65.
Charalá 24025050 (punto 3, 6.3 km, 230 m bajo): +2.33 (+13.8 %), RMSE 3.89.
ERA5-Land queda por encima en los 12 meses en las tres. Por mes: `productos/punto1/rs_estaciones_vs_era5land_por_mes.csv`.

## 2026-11-17 · Punto 1 · ETo de estación frente a ERA5-Land (prueba de estaciones)

**Decisión.** ETo FAO-56 de estación (script 13) en Mogotes, La Sierra y Charalá: Tmax y Tmin medidas, ea con la ec. 17
(HR máx. y mín.), Rs de Angstrom (script 12), P con la ec. 7 y la altura de la estación, G = 0. No hay viento en La Sierra
ni en Charalá: dos variantes, sin elegir todavía. (a) u2 = media mensual de Mogotes-AUT (24025090, mismas coordenadas
que 24025040), con anemómetro supuesto a 10 m (DHIME no da la altura) y ec. 47; u2 ≈ 0.70–0.83 m/s. (b) u2 = 2 m/s, valor de
FAO-56 sin datos de viento. Solo días con todas las entradas; no se rellena. Se comparan los mismos días contra el punto
más cercano. Andalucía (24035350) no entra: fuera de la cuenca y sin brillo solar. Tanque de Mogotes-AUT no se usa.

**Resultado.** Sesgo ERA5-Land − estación, mm/día (variante a / variante b):
Mogotes (4 591 días): −0.13 (−4.0 %) / −0.58 (−15.1 %). La Sierra (4 109): +0.56 (+23.1 %) / +0.53 (+21.8 %).
Charalá (4 462): −0.15 (−4.3 %) / −0.58 (−14.8 %). Medias de entradas en los mismos días: ERA5-Land más frío (Tmax
1.5–5.8 °C, Tmin 2.2–4.5 °C), más seco (ea 0.16–0.34 kPa) y con más Rs (1.8–5.1 MJ/m²·día) que las estaciones.

## 2026-11-17 · Punto 1 · Viento de la ETo de estación

**Decisión (Juan).** Variante final: (a), u2 = media mensual del viento de Mogotes-AUT (24025090), medido a 10 m y
llevado a 2 m con la ec. 47 de FAO-56. La variante (b), u2 = 2 m/s, queda solo como sensibilidad.

**Razonamiento.** Es viento medido en la cuenca. La altura de 10 m ya no es un supuesto: el Manual del Observador
Meteorológico del IDEAM (GDI-M003, versión 03, p. 37) dice que los sensores de viento en Colombia están a 10 m. Con (a), sesgo
ERA5-Land − estación: Mogotes −0.13 mm/día (−4.0 %), La Sierra +0.56 (+23.1 %), Charalá −0.15 (−4.3 %).

## 2026-11-17 · Punto 1 · Cómo se declara la ponderación espacial

**Decisión.** En el informe basta con «promedio ponderado por Voronoi», sin justificarlo más ni compararlo con la Tarea 1.

**Razonamiento.** La razón de los pesos ya está en la entrada del 2026-11-12. La Tarea 1 ponderó distinto (IMERG por
área de celda, pluviómetros sin pesos); no se presenta como equivalente.

## 2026-11-17 · Punto 1 · γ con la presión de cada punto

**Decisión.** γ (ec. 8) se calcula con la `sp` diaria de cada punto, no con la presión de la elevación media de la
cuenca como decía el plan. Se declara así en la metodología.

**Razonamiento.** Cada punto usa la presión de su propia altura, coherente con su T y su ea. La diferencia frente a la
presión media de la cuenca solo mueve γ en proporción a P y entra en la ETo por el denominador y el término
aerodinámico.

## 2026-11-17 · Punto 1 · Qué supone la ec. 47 (viento de 10 a 2 m)

**Nota para la metodología.** u2 = u10 · 4.87 / ln(67.8 · 10 − 5.42) = 0.748 u10. La ec. 47 supone un perfil
logarítmico del viento, en atmósfera neutra, sobre el pasto de referencia de 0.12 m (d = 0.08 m, z0m = 0.0148 m).
El viento de ERA5-Land a 10 m no viene de una superficie de pasto sino de la rugosidad del modelo en cada celda, y en
montaña la estabilidad cambia del día a la noche. Por eso u2 es el viento que tendría un pasto de referencia bajo ese
u10, no el viento real a 2 m. Pesa poco en la ETo: en el día verificado a mano, la parte aerodinámica es 0.37 de
3.76 mm/día.

## 2026-11-17 · Punto 1 · Error de ECMWF en ERA5-Land, sep-2022 a feb-2024

**Resultado.** ECMWF anunció el 2024-04-02 que en `reanalysis-era5-land-monthly-means` todas las variables acumuladas de
sep-2022 a feb-2024 están mal y no se reemplazarán; propone el tipo `monthly_averaged_reanalysis_by_hour_of_day` a las
00:00 ([foro de ECMWF](https://forum.ecmwf.int/t/issue-affecting-era5-land-monthly-averaged-reanalysis-for-the-period-september-2022-to-february-2024/2370)).
El script 04d lo revisa en nuestros datos (`anexos/punto1/era5land_sep_dic_2022_comprobacion.csv`):
- `era5land_mensual_balance` (script 07: ssr, str, e, pev) **sí está afectado**: sep–dic 2022 valen entre 0.29 y 0.48
  veces la media de 1998–2021, fuera del rango histórico los 4 meses.
- La Rs del producto de series de tiempo (6 puntos, base de la ETo) **no**: cociente 0.94–1.04, dentro del rango.

**Decisión (Juan, 2026-11-17).** Toda comparación que use `era5land_mensual_balance` (Rn y evaporación de ERA5-Land
mensual) se hace sobre 1998-01 a 2022-08 (296 meses). El archivo descargado no se toca. La ETo sigue en 1998–2022.

**Razonamiento.** Los 4 meses están claramente mal y ECMWF no los corrigió. Recortar es lo más simple de declarar y
no depende de una descarga nueva.

## 2026-11-18 · Punto 1 · ET real de cuenca de cada producto

**Decisión.** Script 14: cada producto en malla (GLEAM E y Ep, SSEBop v6.1 y v5, ERA5-Land e y pev) se promedia en la
cuenca pesando cada celda por el área de su intersección con el polígono (ESRI:54034), igual que TerraClimate (script
05). MOD16A2GF ya viene promediado en la cuenca; cada compuesto de 8 días se reparte por igual entre sus días. ERA5-Land
mensual se corta en 2022-08. Media anual en el periodo de cada producto y en el periodo común 2013–2021 (años en que
todos los productos de ET real tienen los 12 meses).

**Resultado.** Media anual 2013–2021, mm: ERA5-Land e 1281, GLEAM E 1192, MOD16A2GF 1136, TerraClimate 1032, SSEBop
v6.1 848, SSEBop v5 474. Potenciales: GLEAM Ep 1138, ERA5-Land pev 3204. Tabla: `productos/punto1/et_real_anual_productos.csv`.

## 2026-11-19 · Punto 1 · Balance hídrico: ET real = P − Q − ΔS

**Decisión (Juan).** Script 15. P con las dos fuentes en paralelo, como en la Tarea 1: PI (IMERG ponderado por área de
celda) y PL (7 pluviómetros dentro de la divisoria, con las exclusiones de la Tarea 1). Q observado de CAMELS-COL en
San Gil, en lámina sobre 2 098.85 km², con la regla de la Tarea 1 (mes vacío si faltan 5 o más días). El Q estimado
del modelo M5 de la Tarea 1 no se usa porque lleva Hargreaves adentro. Largo plazo: ciclo anual medio con los meses que
tienen Q (262 de 300); los 11 años completos de Q, como comprobación. ΔS: agua en las 4 capas de suelo de ERA5-Land
(0–289 cm), con los pesos de Voronoi de los 6 puntos. Se usan años calendario.

**Resultado.** ET real de largo plazo: 1 206 mm/año con PL y 884 con PI (Q = 1 345). Con los años completos da 1 220 y
865. ΔS del suelo: cambio neto de +0.2 mm/año entre 1998 y 2022 y variación de un año a otro con desviación estándar de
28 mm, así que ΔS ≈ 0 se sostiene. PI y PL reproducen las series de la Tarea 1 (diferencia máxima de 0.005 mm/mes).

**Razonamiento.** Q tiene 12.7 % de meses vacíos, concentrados en 2014–2015 y 2022. Exigir años completos deja solo 11
años; el ciclo anual medio aprovecha todos los meses con dato. El ΔS de ERA5-Land no incluye el agua subterránea
profunda.

## 2026-11-19 · Punto 1 · Segunda prueba de la ETo: TerraClimate pet

**Decisión (Juan).** La segunda prueba de la fase 3 es la pet de TerraClimate v1.1, porque es una ETo de referencia y
no una ETP: el archivo la describe como «Reference Evapotranspiration» y la página del producto como ASCE
Penman-Monteith corregida por CO2 (Yang et al., 2019). GLEAM Ep (Priestley-Taylor) y ERA5-Land pev son ETP y no
sirven como prueba de la ETo. El tanque de Mogotes-AUT no se usa (unidades erróneas). Script 16.

**Lo que se declara.** (1) La corrección por CO2 cambia la resistencia de superficie de FAO-56. (2) En v1.1 las
anomalías mensuales vienen solo de ERA5, así que la prueba no es independiente de ERA5 en la variabilidad; sí en la
climatología (CHELSA 2.1 y CRU TS) y en la resolución. No se verificó en el artículo de 2018 la superficie de
referencia ni el albedo (el artículo no cargó); queda pendiente.

**Resultado.** Sesgo de ERA5-Land (ETo − pet), 1998–2022: +10.3 mm/mes (+11.8 %); MAE 10.3, RMSE 10.4, r = 0.97.
ERA5-Land queda por encima en los 300 meses (+5.7 a +14.9 mm/mes). Por mes calendario, de +8.2 (junio) a +12.1 (marzo).
Anual: 1 166 frente a 1 043 mm.

## 2026-11-19 · Punto 1 · Nombre de la ETo en las pruebas

**Decisión (Juan).** La ETo que se pone a prueba se llama «nuestra ETo» o «ETo FAO-56 (este trabajo)», no «ETo de
ERA5-Land»: es la FAO-56 de los scripts 01–04, calculada con forzantes de ERA5-Land, y no un producto de ERA5-Land.
Sesgo = nuestra ETo − referencia (estación o pet de TerraClimate). En Rs sí se dice ERA5-Land: es su ssrd. Los nombres
de archivo (`*_vs_era5land_*`) se dejan como están.

## 2026-11-19 · Punto 1 · Viento de ERA5-Land en la ETo de estación (sensibilidad c)

Juan preguntó si el viento de ERA5-Land evita suponer viento en La Sierra y Charalá. Se agrega como variante (c) en el
script 13: u2 diario de ERA5-Land del punto más cercano. Sesgo de nuestra ETo (mm/día), (a) / (c): Mogotes −0.13 / −0.07,
La Sierra +0.56 / +0.56, Charalá −0.15 / −0.12. Con (c) los dos lados usan el mismo viento y la prueba no revisa el
viento. Por ahora (a) sigue como final; (c) es sensibilidad, hasta que Juan decida.

**Decisión (Juan, 2026-11-19).** (a) Mogotes-AUT sigue como final. La variante u2 = 2 m/s se quita. El viento de
ERA5-Land queda como única sensibilidad y pasa a llamarse (b).

## 2026-11-20 · Punto 1 · Cierre de la fase 3 (scripts 17 y 18)

**Pruebas en una tabla y dispersión (script 17).** Las dos pruebas se pasan a mm/día y a sesgo % (nuestra ETo −
referencia, sobre la referencia), que es lo único comparable: estaciones es diaria y TerraClimate mensual. Se calculan
tres dispersiones por mes: rango de las 4 series (media 28.6 pp), rango entre las 2 pruebas con las estaciones
promediadas (6.8 pp) y desviación estándar de las 4 series (13.5 pp). **Pendiente: Juan elige la definición.**

**ETo frente a P − Q (script 17).** Mismos meses o años que el script 15. Nuestra ETo 1 166 mm/año; P − Q 884 (PI) y
1 206 (PL). Con PL, P − Q supera la ETo en 39–50 mm/año y en 6 de 11 años. Solo cifras; la interpretación es de Juan.

**Mes a mano (script 18).** Marzo de 2001 en Mogotes (31 días completos), en anexos/punto1/mes_estacion_a_mano.xlsx,
con fórmulas vivas. Reproduce el script 13 con diferencia máxima de 0.0001 mm/día. Falta la revisión de Juan.

**Referencias.** Yang et al. es de 2019 (Nature Climate Change 9(1), 44–48; en línea en 2018). Abatzoglou et al. (2018)
solo dice Penman–Monteith sobre pasto de referencia: no da albedo, altura ni resistencia de superficie.
