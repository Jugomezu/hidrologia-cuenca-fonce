# Plan de trabajo — Punto 1: Evapotranspiración

Tarea 2 de Hidrología 202602 · entrega martes 24 de noviembre de 2026

> Copia del plan que Juan pegó en el proyecto el 2026-11-17. Texto sin cambios; solo se le dio formato de Markdown.

Este plan sirve para dos cosas a la vez: que el punto 1 quede completo y que el grupo lo entienda lo suficiente para defenderlo en una exposición sin IA. Por eso cada fase separa tres cosas: lo que se estudia y decide sin ayuda, lo que se le pide a Opus (código, explicación, caso de comprobación, examen) y lo que se verifica a mano.

Los códigos entre corchetes ([K01], [F03]) son los ítems de RUBRICA_T2_evaluador.md que cubre cada fase.

## Estado al 17 de noviembre

Cuenca: río Fonce hasta la estación San Gil (IDEAM 24027010), Santander. El polígono mide 2 099 km² y CAMELS-COL reporta 2 124 km². Elijan una de las dos áreas para convertir caudal a lámina, úsenla en todo el trabajo y declárenla.

Disponible de la Tarea 1:

- variables_mensuales.csv, 1998–2022: precipitación de IMERG y de 8 pluviómetros DHIME, caudal en San Gil, temperatura de ERA5-Land (con MSWX para comparar) y ETP de Hargreaves.
- Delimitación de CAMELS-COL y DEM ALOS de 12 m.
- Tendencias desde 1981 en Q, T y P con Mann-Kendall y pendiente de Sen, OLS con errores Newey-West, Pettitt y control de FDR.
- Ficha física: morfometría, geología, coberturas y suelos.

Hecho en la Tarea 2: ETo FAO-56 diaria y mensual con 6 puntos de ERA5-Land, scripts 01–04 y registro de decisiones. Brillo solar de 3 estaciones en el repositorio. Las fases 0 a 2 están hechas pero por auditar.

Pendiente: comparar la Rs de ERA5-Land con el brillo solar (fase 3), las fases 3 a 11, las figuras, recortar datos/punto1 (hoy es una copia completa de la Tarea 1), README, informe, presentación y todo el punto 2.

## Auditoría de las fases 0 a 2 (hoy, 1–2 h)

- [ ] verificar_entrega.py (fase 0) pasa sobre el repositorio: nombre, estructura, rutas relativas, credenciales, nombres ASCII [G1–G7, R03, R10, R11]
- [ ] Inventario de la Tarea 1 llenado, con longitud y pendiente del cauce principal tomadas de la morfometría (las usa el punto 2)
- [ ] Los 6 puntos se promedian con la misma ponderación espacial de la Tarea 1, y eso queda escrito [M05]
- [ ] Tmáx y Tmín salen de datos horarios o diarios; es = promedio de e°(Tmáx) y e°(Tmín) [M10]
- [ ] ea con la temperatura de rocío [M11]
- [ ] Viento: magnitud con datos horarios antes de promediar; reducción de 10 a 2 m con la ec. 47 y discusión de qué supone [M12]
- [ ] Rn del pasto con albedo 0.23 para la ETo; la radiación neta de ERA5-Land guardada aparte para la fase 6 [M13]
- [ ] G = 0 en el cálculo diario; γ con la presión de la elevación media de la cuenca [M14]
- [ ] Comparación entre la elevación de los puntos de ERA5-Land y el DEM, con su efecto sobre T y ea [M15]
- [ ] Cálculo aparte con medias mensuales (G = 0.07·(T₍ᵢ₊₁₎ − T₍ᵢ₋₁₎)) y su diferencia con la suma de los diarios, por mes. "Mensual" no puede ser solo la suma de los diarios [K02, F02]
- [ ] Un día verificado a mano en una hoja de cálculo [K01]
- [ ] Convenciones de ERA5-Land revisadas: acumulación de la radiación y advertencia de ECMWF sobre los promedios de sep-2022 a feb-2024, que toca los últimos meses de 2022 [M07]
- [ ] Cada archivo de datos con su .meta.json [R08]
- [ ] Periodo de la ETo: las tendencias de la Tarea 1 empiezan en 1981, pero las series mensuales en 1998. Si la descarga de los 6 puntos empieza en 1998, decidir hoy si se extiende a 1981 o si las tendencias de la fase 8 se hacen sobre 1998–2022 y se declara la diferencia. La descarga es lenta, por eso la decisión es hoy
- [ ] El registro de decisiones existente pasa a ser anexos/decisiones.md
- [ ] La bitácora de IA recoge lo hecho hasta ahora, incluido lo trabajado en el proyecto de Claude

Numeración de los scripts: los scripts 01–04 del grupo ya existen y no hay que renombrarlos. Anoten a qué fase corresponde cada uno. Los nombres de script que aparecen en los prompts de este plan son indicativos: cada script nuevo toma el siguiente número libre, en orden de ejecución, empezando en 05.

## Cómo usar este plan

### Reparto del trabajo entre el grupo y Opus

| Lo hace el grupo | Lo puede hacer Opus |
|---|---|
| Elegir métodos, umbrales, año hidrológico, tema del paisaje | Programar lo que el grupo especificó |
| Interpretar físicamente cada resultado | Explicar un concepto o una ecuación paso a paso |
| Verificar cifras con un caso a mano | Preparar el caso a mano y revisar el resultado del grupo |
| Leer las fuentes que se citan | Decir qué sección leer y hacer preguntas sobre ella |
| Redactar la discusión | Criticar un borrador: huecos, afirmaciones sin respaldo, alternativas que faltan |

El enunciado permite usar IA para programar, depurar, explorar métodos, construir figuras y redactar, pero no delegar las decisiones, la interpretación ni la verificación. La exposición oral vale lo mismo que el trabajo escrito y la mitad de su nota es comprensión física.

### Rutina de cada fase

1. Estudiar la lectura indicada y responder a mano las preguntas.
2. Decidir lo que la fase marca como decisión del grupo y anotarlo en anexos/decisiones.md con su razón.
3. Pedir a Opus el trabajo con el prompt de la fase, en una sesión que empiece con el contexto base.
4. Verificar a mano el caso indicado. Si no coincide, no se avanza.
5. Anotar en la bitácora de IA.
6. Redactar el párrafo de metodología de la fase a partir de anexos/decisiones.md, en anexos/borrador_metodologia.md. Así la metodología del informe no queda toda para el último día.
7. Punto de control sin IA: cada integrante responde las tres preguntas de la fase sin mirar notas.

Cada fase tiene un responsable que la ejecuta; los otros dos integrantes hacen el punto de control con él. Los tres deben poder responder por ambos puntos.

### Contexto base (pegar al inicio de cada sesión de Opus)

```
Trabajo en una tarea universitaria de hidrología con mi grupo. Tu papel es de
tutor y programador, no de autor. Reglas para toda la sesión:

1. Antes de escribir código, explica la ecuación o el método en 5-10 líneas,
   con unidades, y dime qué supone.
2. No tomes decisiones metodológicas por mí. Si hay que elegir (método, umbral,
   periodo, parámetro), dame las opciones con sus consecuencias y espera.
3. No escribas la interpretación física de los resultados. Cuando haya un
   resultado, hazme 3 preguntas que me obliguen a interpretarlo yo.
4. Estructura fija del proyecto, con rutas SIEMPRE relativas a la carpeta raíz:
   codigo/punto1/  datos/punto1/  productos/punto1/  anexos/
   Nombres de archivo solo ASCII, sin espacios.
5. Cada archivo de datos lleva al lado un .meta.json con: fuente, versión,
   variable, unidades, periodo, recorte espacial, fecha de descarga y
   procesamiento aplicado.
6. Si una descarga o lectura falla, el script se detiene con un error claro.
   Nunca generes datos sintéticos ni valores de relleno.
7. Ninguna credencial, clave o token dentro del proyecto ni en el código.
8. Columnas con unidades en el nombre (eto_mm_d, rn_mj_m2_d). Fija semillas
   aleatorias. Registra versiones en codigo/requirements.txt.
9. Antes de usar un identificador de conjunto de datos, una función de librería
   o una constante de un método publicado, confírmalo en la documentación o en
   la publicación original y dime dónde lo confirmaste. Si no puedes
   confirmarlo, dilo.
10. Con cada script entrégame un caso de comprobación a mano: entradas, pasos
    y resultado esperado.
```

### Prompt de examen (usar al cerrar cada fase)

```
Actúa como el profesor en la exposición oral. Sobre la fase que acabo de
terminar, hazme 5 preguntas, una por una, esperando mi respuesta: una de
rastreo (de una cifra hasta los datos y el código), dos de decisión
metodológica, una de mecanismo físico y una de limitación. No me des la
respuesta: califica cada respuesta de 0 a 5 y dime qué le faltó.
```

### Bitácora de IA (anexos/bitacora_ia.md)

Una fila por uso. Con esto la declaración de IA del informe sale casi sola [I04, I05].

| Fecha | Herramienta y versión | Tarea concreta | Cómo se verificó | Qué se rechazó o corrigió | Integrante |
|---|---|---|---|---|---|

Las primeras filas ya existen y hay que escribirlas: la rúbrica de evaluación y estos dos planes se hicieron con IA a partir del enunciado.

## Ruta crítica (hoy es martes 17; quedan siete días)

Esta tabla es la misma en los dos planes. Con la ETo ya calculada, el cuello de botella es el punto 2, que no ha empezado: la búsqueda del sitio arranca hoy. En el punto 1, lo urgente es lanzar las descargas de productos de ET real y de demanda, y decidir el periodo de la ETo.

| Día | Punto 1 | Punto 2 | Hito |
|---|---|---|---|
| Mar 17 | Auditoría de fases 0–2; lanzar descargas de productos (fases 3 y 6) | Fase 1, con hora límite | Sitio decidido; descargas en cola |
| Mié 18 | Fases 3 y 4 | Fases 1 (cierre) y 2 | Rs frente a brillo solar; dos pruebas de la referencia; serie depurada |
| Jue 19 | Fase 5 | Fases 3 y 4 | Diferencias explicadas; nueve ajustes por duración |
| Vie 20 | Fases 6 y 7 | Fases 5 y 6 | ET real y Budyko; IDF con bandas |
| Sáb 21 | Fases 8 y 9 | Fases 7 y 8 | Tendencias y paisaje; problema A |
| Dom 22 | Fase 11; congelar código y recortar datos | Fases 9 y 11 | Borrador completo; auditoría en modo INFORME (cierre A) |
| Lun 23 | Cierre B | Cierre B | Correcciones, presentación, ZIP probado desde cero, auditoría en modo ZIP |
| Mar 24 | — | — | Entrega |

Lo que falta suma unas 85 a 105 horas antes del cierre (40–50 del punto 1 y 45–55 del punto 2), más 10 a 14 horas de cierre. Son entre 5 y 7 horas diarias por integrante. Un reparto posible: un responsable por punto y un tercero en datos, verificación y redacción. Ese reparto lo decide el grupo.

Orden de recorte si falta tiempo (nunca se recorta lo obligatorio):

1. Bonos 1.6 y 1.4. El 1.6 es el primero en caer si el sitio del punto 2 queda fuera del Fonce.
2. En la fase 9, un solo tema.
3. En la fase 3, las dos pruebas más baratas en datos.
4. En la fase 6, torres de flujo solo si hay una en la región.

## Fase 0 — Preparación común a los dos puntos (2–3 h)

Estado: hecha en buena parte. Solo se completa lo que marque la auditoría del inicio.

Cubre: estructura y nombre de la entrega, continuidad con la Tarea 1. [G1–G7, R01, R02, R10, M03]

Estudia primero: la sección de entrega del enunciado. Preguntas a mano:

- ¿Cuál es el nombre exacto del ZIP del grupo? Comprobarlo contra `^T2_202602_G[0-9]{2}(_[A-Z][A-Za-z]+){3}\.zip$`, con los apellidos en orden alfabético y sin tildes.
- ¿Qué archivos y carpetas van en la raíz, y cuáles no pueden ir?

Decisiones del grupo: quién responde por cada fase; lenguaje y entorno; repositorio compartido.

Inventario de la Tarea 1 (llenar en anexos/inventario_t1.md; todo el punto 1 depende de él):

| Insumo | Archivo | Periodo | Unidades | ¿Listo? |
|---|---|---|---|---|
| Delimitación de la cuenca y DEM | | | | |
| Área, longitud y pendiente del cauce principal (las usa el punto 2 para el argumento de escala) | | | | |
| Precipitación mensual de pluviómetros | | | | |
| Precipitación mensual satelital | | | | |
| Caudal medio mensual y escorrentía | | | | |
| Temperatura mensual | | | | |
| Climatología, temporadas húmeda y seca | | | | |
| Resultados y métodos de tendencias | | | | |
| Ficha física de la cuenca | | | | |
| Hipótesis sobre el retorno de agua a la atmósfera | | | | |
| Esquema conceptual | | | | |
| Método de ponderación espacial | | | | |

Si el grupo cambió de cuenca o de integrantes, hay que justificarlo y verificar de nuevo área, registro y faltantes.

Prompt para Opus:

```
Crea la estructura de carpetas de la entrega: una carpeta raíz llamada
<NOMBRE_DEL_ZIP_SIN_EXTENSION> con README.md, codigo/punto1, codigo/punto2,
datos/punto1, datos/punto2, productos/punto1, productos/punto2 y anexos.
Añade codigo/requirements.txt con versiones fijas, una plantilla de README con
cinco apartados (integrantes con nombre completo, descripción de carpetas,
procedencia de los datos, requisitos, orden de ejecución) y un script
codigo/verificar_entrega.py que compruebe: nombre contra la expresión regular
<REGEX>, estructura exacta de la raíz, ausencia de rutas absolutas, de
credenciales y de nombres con caracteres no ASCII o espacios.
```

Verifica a mano: ejecutar verificar_entrega.py sobre la carpeta vacía y sobre una copia con un error a propósito (un archivo con tilde).

Punto de control sin IA: ¿qué pasa con la nota si el ZIP tiene otro nombre? ¿Dónde va el archivo de dependencias? ¿Qué no puede ir en la carpeta de datos?

## Fase 1 — Credenciales y datos de reanálisis (3–4 h de trabajo; la cola de descarga corre aparte)

Estado: hecha con 6 puntos de ERA5-Land. Se audita con la lista del inicio. El prompt de abajo solo hace falta si se extiende el periodo a 1981 o si falta alguna variable para la fase 6 (radiación neta real, evaporación, humedad del suelo).

Cubre: fuentes y convenciones de datos. [M01, M02, M04, M05, M07, M08, M09, R06, R07, R08, R12]

Estudia primero: el recuadro de datos del enunciado y la documentación de ERA5-Land sobre variables acumuladas. Preguntas a mano:

- ¿Por qué no se pueden sacar Tmáx y Tmín de las medias mensuales?
- ¿En qué unidades y con qué acumulación vienen la radiación y la evaporación? ¿Qué signo tiene la evaporación?
- ¿Qué advierte ECMWF sobre los promedios mensuales entre septiembre de 2022 y febrero de 2024?

Decisiones del grupo:

- Ruta de descarga. El enunciado nombra tres: series horarias por punto (reanalysis-era5-land-timeseries, una solicitud por punto, varios puntos dentro de la cuenca), la colección diaria de Earth Engine (ECMWF/ERA5_LAND/DAILY_AGGR, con Tmáx, Tmín, radiación y evaporación) y reanalysis-era5-land-monthly-means para radiación neta, evaporación y humedad del suelo mensuales. No descargar ERA5-Land horario por área. derived-era5-land-daily-statistics no trae radiación ni evaporación.
- Periodo de análisis y cómo se alinea con las series de la Tarea 1.
- Número y ubicación de los puntos dentro de la cuenca, y cómo se ponderan igual que en la Tarea 1.
- Fuentes locales: si existen estaciones completas, tanques o estudios, se usan además de las globales.

Prompt para Opus:

```
Necesito descargar de ERA5-Land, para la cuenca <NOMBRE> (delimitación en
datos/punto1/<archivo>), periodo <AAAA-AAAA>, por la ruta <RUTA ELEGIDA>:
temperatura a 2 m, temperatura de rocío a 2 m, componentes del viento a 10 m,
radiación solar descendente, radiación neta de onda corta y de onda larga en
superficie, presión, evaporación total y humedad del suelo por capas.

Antes del script: (a) confirma en la documentación el nombre exacto de cada
variable, sus unidades, cómo se acumula y su convención de signo, y muéstrame
una tabla; (b) dime qué advierte ECMWF sobre los promedios mensuales entre
sep-2022 y feb-2024 y qué opciones tengo.

Luego escribe codigo/punto1/01_descarga_era5land.py: lee las credenciales del
entorno del usuario (nunca del proyecto), recorta a la cuenca y al periodo,
guarda en datos/punto1/ con su .meta.json y falla de forma visible si algo no
descarga. Escribe también 02_agregar_cuenca.py, que promedia sobre la cuenca
con la ponderación <MÉTODO DE LA TAREA 1> y deja series diarias y mensuales.
```

Verifica a mano: tomar un día cualquiera y comprobar que la radiación solar convertida a MJ/m²/d está en un rango plausible para la latitud; que la evaporación, tras cambiarle el signo, es positiva y de pocos mm/d; que 1 mm/d ≈ 28.4 W/m².

Salidas: datos/punto1/era5land_*.nc|csv con metadatos; productos/punto1/forzantes_diarios.csv, forzantes_mensuales.csv.

Punto de control sin IA: ¿cuánto mide una celda de ERA5-Land y qué implica en la cuenca? ¿Por qué pev no es ETo? ¿Qué se hizo con los meses afectados por la advertencia de ECMWF?

## Fase 2 — ETo de referencia con Penman–Monteith FAO-56 (4–5 h)

Estado: ETo diaria y mensual calculada. Faltan, si la auditoría lo confirma, el cálculo aparte con medias mensuales, la comparación de elevaciones, el día verificado a mano y las figuras. Las preguntas a mano y el punto de control se hacen igual: son lo que se pregunta en la exposición.

Cubre: apartado 1.1.a. [M10, M11, M12, M13, M14, M15, K01, K02, F02]

Estudia primero: FAO-56 capítulos 2 y 3 (ecuaciones 6, 7, 39, 42, 43 y 47); sección 6 de las notas del curso; Dingman (2015), tabla 6.2. Preguntas a mano:

- ¿Qué representa cada uno de los dos sumandos del numerador de la ecuación 6?
- ¿Por qué e°(Tmedia) subestima la presión de saturación?
- ¿Por qué promediar las componentes del viento antes de calcular la magnitud subestima la velocidad?

Decisiones del grupo: elevación con la que se calcula γ; cómo tratar la diferencia entre la elevación del modelo y la del DEM; cómo se define el día (hora local frente a UTC).

Prompt para Opus:

```
Explícame la ecuación 6 de FAO-56 término por término y luego escribe
codigo/punto1/03_eto_fao56.py con estas reglas, que no son negociables:
- es = promedio de e°(Tmax) y e°(Tmin); ea = e°(Td).
- Viento: magnitud sqrt(u²+v²) con datos horarios, luego promedio diario, y
  reducción de 10 m a 2 m con la ecuación 47.
- Rn del pasto de referencia: Rns = (1-0.23)·Rs y Rnl con la ecuación 39. La
  radiación neta propia de ERA5-Land se guarda aparte, sin usarla aquí.
- G = 0 en el cálculo diario. Gamma con la presión de la elevación <Z> m.
- Salida diaria en mm/d y acumulados mensuales en mm/mes.
Añade un segundo cálculo con medias mensuales de todas las variables y
G = 0.07·(T_{i+1} - T_{i-1}), y una tabla por mes calendario con la diferencia
frente a la suma de los diarios. Añade una comparación entre la elevación del
modelo y la media del DEM de la cuenca.
Dame un día real de mis datos resuelto paso a paso para comprobarlo a mano.
```

Verifica a mano: el día de comprobación, en una hoja de cálculo. Controles: factor de viento 4.87/ln(67.8·10 − 5.42) = 0.748; P = 101.3·((293 − 0.0065z)/293)^5.26; γ = 0.000665·P; ETo entre 1 y 9 mm/d.

Salidas: productos/punto1/eto_fao56_diaria.csv, eto_fao56_mensual.csv, eto_error_promediado.csv, figura del ciclo anual.

Punto de control sin IA: ¿en qué meses es mayor el error por promediar y por qué? ¿Qué supone la reducción del viento sobre la rugosidad de la superficie? ¿Por qué se usa el albedo 0.23 y no el de la cuenca?

## Fase 3 — Poner a prueba la referencia (3–4 h)

Cubre: apartado 1.1.b. [M19, K03, K04, F03]

Estudia primero: FAO-56 capítulo 4 (tanques) y ecuación 50; sección 8 de las notas del curso. Preguntas a mano:

- ¿Por qué la ETo es "la referencia por definición" y aun así puede estar mal?
- ¿Por qué P − Q no sirve como referencia de la demanda?

Decisiones del grupo: cuáles dos pruebas (mínimo) de estas tres:

| Prueba | Qué separa | Qué exige |
|---|---|---|
| Estaciones meteorológicas | El error de los datos de reanálisis del error del método | Estación completa cercana. Sin radiación, estimarla con la ecuación 50; presión por elevación con la ecuación 7 |
| Tanque evaporímetro | Mide demanda, no evapotranspiración real | Coeficiente de tanque justificado |
| Producto independiente de demanda | Otra definición y otros datos | Documentar cómo define la demanda (la base de la Tarea 1, TerraClimate, GLEAM) |

El brillo solar de las tres estaciones sirve para validar la Rs de ERA5-Land, que es la entrada de mayor peso en la ETo. Esa comparación valida una entrada; no cuenta como una de las dos pruebas. La prueba de estaciones exige recalcular la ETo completa con datos de estación. Si esas estaciones también miden temperatura, humedad y viento, la Rs estimada desde el brillo solar permite hacer la prueba completa.

Prompt para Opus (brillo solar):

```
Tengo horas de brillo solar diario de 3 estaciones: <ARCHIVOS, CÓDIGOS Y
COORDENADAS>. Confirma en FAO-56, capítulo 3, la ecuación que convierte la
duración de insolación en Rs (n/N, Ra y los coeficientes a_s y b_s) y qué
valores recomienda cuando no hay calibración local; dime número de ecuación y
página. Luego escribe el script que estime Rs diaria en cada estación y la
compare con la Rs de ERA5-Land en el punto o la celda más cercana: sesgo y
RMSE por mes calendario, y ciclo anual. Reporta la diferencia de elevación
entre cada estación y su celda. Si las estaciones tienen temperatura, humedad
y viento, recalcula la ETo FAO-56 de estación y compárala con la mía. No
interpretes: dame las cifras.
```

Pregunta para el punto de control: si la Rs de ERA5-Land tiene un sesgo en ciertos meses, ¿cuánto se traslada a la ETo y en qué meses? Respóndanla con el experimento de sensibilidad de la fase 5.

Prompt para Opus:

```
Voy a contrastar mi ETo FAO-56 con <PRUEBA 1> y <PRUEBA 2>. Para cada una:
(a) dime qué cantidad mide o calcula exactamente y en qué se diferencia de la
ETo de FAO-56; (b) escribe codigo/punto1/04_pruebas_referencia.py que la
descargue o lea, la recorte a la cuenca y al periodo común, y calcule por mes
calendario sesgo, MAE y RMSE frente a mi ETo; (c) calcula la dispersión entre
las pruebas mes a mes, que usaré después como umbral.
Compara además la ETo multianual con P - Q multianual de mis series y
muéstrame solo los números.
```

Verifica a mano: un mes de la estación recalculado con FAO-56. Si ETo multianual < P − Q, revisar en este orden: representatividad de la precipitación, pérdidas subterráneas, aportes externos y, al final, una cobertura que evapore más que el pasto.

Salidas: productos/punto1/pruebas_referencia.csv, dispersion_pruebas.csv.

Punto de control sin IA: ¿qué error aísla la comparación con la estación? ¿Qué mide un tanque? ¿Qué harían si la ETo resulta menor que P − Q?

## Fase 4 — Métodos de otras familias (5–6 h)

Cubre: apartado 1.1.c. [M06, M16, M17, M18, K05, K06, K07, F04, F05]

Estudia primero: Dingman (2015), sección 6.7; sección 7 de las notas del curso; el recuadro de notación del enunciado. Preguntas a mano:

- ¿En qué se diferencian ETo, ETp, E0, Epan y ET? ¿Cuál calcula cada método?
- ¿Para qué clima y qué superficie se calibró cada método de la tabla?

Decisiones del grupo:

- Cuatro métodos de la tabla, uno por familia: temperatura (Thornthwaite o Hamon), temperatura con radiación extraterrestre (Hargreaves u Oudin), radiación (Priestley–Taylor, con α = 1.26 inicial), transferencia de masa (Dalton o Meyer). Hargreaves ya está calculado en la Tarea 1. Verifiquen que usa Tmáx y Tmín, Ra en mm/d equivalentes y la versión que se va a declarar, y que se recalcula con los mismos datos y periodo que la ETo. Thornthwaite hace falta de todos modos para la fase 8.
- Dos métodos fuera de la tabla, de naturaleza física distinta entre sí. Menú para explorar, no una elección: fórmulas de radiación y temperatura (Makkink, Turc), fórmulas de déficit de vapor o humedad, combinación de agua libre de Penman (calcula E0, hay que declararlo), relación complementaria (estima ET real, hay que declararlo). Para cada uno: publicación original, proceso que representa, qué simplifica, clima de calibración y por qué sirve para esta cuenca.

Prompt para Opus:

```
Elegí estos métodos: <4 DE LA TABLA> y <2 ADICIONALES>. Para cada uno:
1. Escribe la ecuación con unidades y la versión exacta, citando la
   publicación original. Si hay variantes con constantes distintas, muéstralas
   y dime cuál usa la librería. Confirma cada constante; no la des de memoria.
2. Dime qué cantidad estima (ETo, ETp, E0 o ET).
3. Impleméntalo en codigo/punto1/05_metodos.py. Thornthwaite lo programo yo
   contigo, paso a paso, sin librería. Hargreaves con Ra en mm/d equivalentes.
4. Dame un caso a mano para cada método.
Luego calcula, frente a FAO-56 y POR MES CALENDARIO: sesgo, MAE, RMSE, error
de amplitud y error de fase del ciclo anual. Entrega la tabla, sin
interpretarla.
```

Verifica a mano: un mes de cada método. Comprobar que la tabla de ajuste no mezcla cantidades distintas sin decirlo.

Salidas: productos/punto1/metodos_mensual.csv, ajuste_por_mes.csv, anexos/ecuaciones_metodos.md.

Punto de control sin IA: ¿cuál se ajusta mejor y era esperable? ¿Puede un método empírico ajustarse bien por compensación de errores? ¿Qué alejamientos superan la dispersión de las pruebas?

## Fase 5 — Explicar las diferencias (5–6 h)

Cubre: apartado 1.1.d y verificación de unidades. [K08, K09, K10, K11, F01, F06, F07, F08]

Estudia primero: sección 6 de las notas (Penman, evaporación de equilibrio, Priestley–Taylor); Shaw et al. (2010), sección 10.3; Milly y Dunne (2016). Preguntas a mano:

- Convertir 146 W/m² de calor latente a mm/h con λ = 2.45×10⁶ J/kg. ¿Coincide con los 3.52 mm/h del texto?
- ¿Por qué α* de FAO-56 no se compara directamente con 1.26?

Decisiones del grupo: cómo se define la dispersión de las pruebas; cómo se perturba la temperatura (¿también Tmáx, Tmín y rocío?); qué método simple elegirían con solo temperatura, usando el árbol de decisión de las notas.

Prompt para Opus:

```
Con mis series, escribe codigo/punto1/06_diferencias.py:
1. Ciclo anual de todos los métodos con una banda que muestre la dispersión
   de las pruebas de la fase 3.
2. Separa FAO-56 en término radiativo y término aerodinámico; fracción de cada
   uno por mes. Calcula alfa* = ETo/Eeq con Eeq = [Delta/(Delta+gamma)]·
   (Rn-G)/lambda, y grafícalo por mes junto al déficit de vapor y al viento.
3. Experimento de sensibilidad, recalculando TODOS los métodos: T +1 y +2 °C
   con ea constante; T +1 y +2 °C con humedad relativa constante; u2 +10 %;
   Rs -10 %; ea +10 %. Tabla del cambio porcentual por mes y por método.
Explícame antes qué diferencia física hay entre calentar con ea constante y
con humedad relativa constante. No interpretes los resultados: hazme
preguntas.
```

Verifica a mano: 146 W/m² → 0.21 mm/h (≈ 5.1 mm/d); un mes de α*; un caso de sensibilidad con la hoja de cálculo de la fase 2.

Salidas: figuras ciclo_anual_metodos, terminos_fao56, alfa_implicito; sensibilidad.csv.

Punto de control sin IA: ¿qué forzante mueve más la demanda y en qué meses? ¿Qué métodos responden a un forzante que no incluyen? Para cada método, ¿por qué se aparta: viento, déficit de vapor, radiación o calibración para otro clima?

## Fase 6 — Evapotranspiración real por varios caminos (5–6 h)

Cubre: apartado 1.2. [M20, M21, M24, K12, K13, K14, K15, K16, F09, F10, F11, F12]

Estudia primero: secciones 8 y 9 de las notas del curso; Wilson et al. (2002) sobre el cierre del balance de energía. Preguntas a mano:

- ¿Por qué P − Q mensual no es evapotranspiración mensual?
- ¿Qué principio de cálculo usa cada producto: balance de energía con temperatura superficial, Penman–Monteith con datos satelitales, Priestley–Taylor con estrés, modelo de superficie o balance hídrico?

Decisiones del grupo:

- Año hidrológico, iniciando en la época de menor almacenamiento.
- Área de la cuenca para convertir caudal a lámina: 2 099 km² del polígono o 2 124 km² de CAMELS-COL. La misma en todo el trabajo, declarada.
- Productos: al menos dos de familias distintas (GLEAM, MOD16, SSEBop, evaporación de ERA5-Land, TerraClimate, la base de la cuenca). MOD16 y SSEBop solo en el periodo común, no para tendencias.
- Incertidumbre del caudal: valor documentado y su fuente.
- GRACE: solo como contexto regional o con el error de escala cuantificado.
- Torres de flujo: buscar si hay una torre de covarianza de remolinos en la región (FLUXNET y redes regionales). Si la hay, se usa para contrastar el ciclo anual de los productos y se discuten el cierre del balance de energía y la diferencia de escala. Si no la hay, el informe lo dice en una frase con dónde se buscó.

Prompt para Opus:

```
Escribe codigo/punto1/07_et_real.py:
1. Balance de largo plazo ET = P - Q con P de los 8 pluviómetros DHIME y con
   P de IMERG, en mm/año (área de la cuenca: <ÁREA DECLARADA> km²);
   y P - Q año a año con año hidrológico iniciando en <MES>.
2. Propagación del error: sigma_ET² = sigma_P² + sigma_Q², con sigma_P a
   partir de la diferencia entre mis dos precipitaciones y sigma_Q = <VALOR Y
   FUENTE>. Reporta qué fracción de ET representa.
3. Techo energético: radiación neta REAL de la superficie (la de ERA5-Land,
   no la del pasto) convertida a lámina Rn/lambda; fracción evaporativa anual.
4. Productos <LISTA>: para cada uno confirma en su documentación principio de
   cálculo, resolución, periodo, unidades y convención de signo; recorta a la
   cuenca; ciclo anual y total anual en el periodo común.
5. Tabla de cuánto se aparta cada producto del balance multianual.
Marca los años con P - Q negativo, mayor que Rn/lambda o muy distinto de los
productos, sin explicarlos.
```

Verifica a mano: el balance de un año con las series mensuales; σ_ET; que λET/Rn ≤ 1 y ET ≤ ETo en el largo plazo.

Salidas: productos/punto1/et_balance_anual.csv, et_productos_mensual.csv, et_incertidumbre.csv.

Punto de control sin IA: ¿qué almacenamientos podrían violar ΔS ≈ 0 en la cuenca? ¿Hay trasvases o extracciones? ¿Qué producto queda más cerca del balance y por qué, según su principio de cálculo?

## Fase 7 — ¿Manda la energía o el agua? (5–6 h)

Cubre: apartado 1.3. [M23, K17, K18, K19, K20, K21, F13, F14, F15, F16, F17, F18]

Estudia primero: Dingman (2015), sección 6.8; Budyko y la curva de Fu en las notas; Sankarasubramanian et al. (2001); Brutsaert y Parlange (1998). Preguntas a mano:

- En el espacio de Budyko, ¿qué significan los dos límites?
- ¿Qué diferencia hay entre el índice de aridez con ETo y con evapotranspiración potencial?

Decisiones del grupo: criterios numéricos para clasificar un mes como limitado por energía, por agua o de transición; qué ET anual se usa en los puntos de Budyko (productos, o P − Q si la fase 6 mostró que ΔS anual es pequeño).

Prompt para Opus:

```
Escribe codigo/punto1/08_regimen.py:
1. ET/ETo y ET/P por mes calendario con mis productos. Aplica estos criterios
   de clasificación que definí: <CRITERIOS>.
2. Fracción evaporativa mensual frente a la humedad del suelo de la zona de
   raíces; busca un umbral con un método que me expliques antes.
3. Budyko: punto multianual en ETo/P frente a ET/P; ajuste de omega de la
   curva de Fu, ET/P = 1 + phi - (1 + phi^omega)^(1/omega); trayectoria año a
   año con ET = <FUENTE ELEGIDA>.
4. Elasticidad teórica del caudal a la precipitación con la curva ajustada
   (deriva la fórmula conmigo) y la empírica con el estimador de mediana de
   Sankarasubramanian sobre anomalías anuales.
5. ET frente a la demanda en años secos y húmedos.
Entrega cifras y figuras; las preguntas de interpretación me las haces tú.
```

Verifica a mano: el punto multianual de Budyko; que el ω ajustado reproduce el ET/P observado; la elasticidad con F′(φ) = 1 − φ^(ω−1)·(1 + φ^ω)^(1/ω − 1).

Salidas: regimen_mensual.csv, figuras budyko, fraccion_evaporativa_humedad, elasticidad.csv.

Punto de control sin IA: ¿coincide la clasificación mensual con las temporadas de la Tarea 1? ¿Hay meses con ET > P, y de qué almacenamiento sale esa agua? ¿Qué atributos de la cuenca explican su distancia a la curva de Budyko? ¿Cambia la hipótesis de la Tarea 1?

## Fase 8 — Cambios en la demanda (4–5 h)

Cubre: apartado 1.4. [M22, K22, K23, K24, F19, F20, F21] · Bono +0.1 [B1.4]

Estudia primero: Roderick y Farquhar (2002); McVicar et al. (2012); los métodos de tendencia de la Tarea 1. Preguntas a mano:

- ¿Qué es la paradoja del tanque y qué forzantes la explican?
- ¿Por qué una tendencia estadística no identifica una causa?

Decisiones del grupo: periodo de tendencias, que depende de lo decidido en la auditoría (1981–2022 si se extendió la descarga, o 1998–2022 declarando la diferencia con la Tarea 1); cómo tratar la autocorrelación; sensibilidades analíticas o numéricas. Buscar si hay datos de tanque evaporímetro en la zona: si existen, su tendencia entra en la comparación; si no, se declara.

Prompt para Opus:

```
Escribe codigo/punto1/09_cambios.py:
1. Tendencias de ETo FAO-56 y de Thornthwaite con los métodos de la Tarea 1
   (Mann-Kendall con pendiente de Sen, OLS con errores Newey-West, Pettitt y
   control de FDR), periodo <PERIODO DECIDIDO>,
   revisando estacionariedad, dependencia temporal y sensibilidad a los
   extremos del registro (quitando los primeros y los últimos años).
2. Atribución: sensibilidad de ETo a T, ea, u2 y Rs (derivadas numéricas),
   multiplicada por la tendencia observada de cada forzante; suma frente a la
   tendencia directa y residuo.
3. Tabla comparando la tendencia de ETo con la de Thornthwaite.
Solo cifras con su significancia.
[Opcional, bono] Con la curva de Fu de la fase 7, descompón el cambio de
caudal entre los subperiodos <A> y <B> en la parte debida a P, a ETo y a
omega, y compárala con la tendencia de caudal de la Tarea 1.
```

Verifica a mano: la contribución de un forzante; que la suma de contribuciones más el residuo da la tendencia directa.

Salidas: tendencias_demanda.csv, atribucion_eto.csv.

Punto de control sin IA: si Thornthwaite sube y FAO-56 no, ¿qué forzante compensa la temperatura? ¿Cómo distinguen un cambio de clima de uno de cobertura, de operación hidráulica o de un artefacto del reanálisis?

## Fase 9 — El paisaje de la cuenca (4–6 h)

Cubre: apartado 1.5. [K25, F22]

Estudia primero: la ficha física de la Tarea 1 y la referencia del tema elegido.

Decisión del grupo: al menos un tema, justificado con la ficha, y explicando por qué se descartan los otros cinco.

| Tema | Tiene sentido si la cuenca… | Qué se calcula |
|---|---|---|
| a. Gradiente altitudinal | Tiene relieve fuerte | ETo y ET por bandas de elevación del DEM |
| b. Intercepción y cobertura | Tiene bosque y otra cobertura relevante | Gash o regresión por evento para dos coberturas; escenario de cambio |
| c. Niebla y nubosidad | Es bosque nublado, páramo o costa con niebla | Entrada oculta si P − Q < ET de los productos |
| d. Nieve, hielo y sublimación | Tiene nieve o glaciares | Sublimación, fracción de la ablación, ciclo anual |
| e. Agua libre y riego | Tiene lagos, embalses, humedales o riego | Evaporación de esas superficies y su peso en el balance |
| f. Resistencia del dosel | Tiene coberturas con estrés estacional | Penman–Monteith con resistencia tipo Jarvis e índice de área foliar |

Prompt para Opus:

```
Elegí el tema <LETRA> por estas razones: <RAZONES DE LA FICHA>. Explícame el
método (<MÉTODO>) con sus supuestos y datos necesarios, dime qué datos
globales existen para mi cuenca confirmándolo en su documentación, y escribe
codigo/punto1/10_paisaje.py. Antes de programar, dime qué resultado haría
falsa mi razón para elegir este tema.
```

Verifica a mano: un caso del método con números redondos.

Punto de control sin IA: ¿por qué este tema y no los otros? ¿Qué resuelve y qué no resuelve un producto de 9 km en la cuenca?

## Fase 10 — Opcional con bono +0.2: de la evapotranspiración al diseño

Cubre: apartado 1.6. [B1.6]

Solo si el punto 2 usa la misma cuenca o una con información equivalente, y después de que el punto 2 tenga sus métodos de frecuencia listos (fases 4 y 5 de ese plan). Una serie sin análisis de frecuencia no suma.

Decisión del grupo: una serie anual entre déficit climático de la temporada seca, evaporación neta de un embalse hipotético, demanda de riego de un cultivo o déficit máximo de humedad del suelo.

Prompt para Opus:

```
Construye la serie anual de <SERIE> con los criterios de mi punto 1:
<CRITERIOS>. Guárdala en productos/punto1/ con metadatos. Luego aplícale el
análisis de frecuencia de codigo/punto2/ (mismas funciones) y dame el valor
que se supera en promedio una vez cada <T> años con su intervalo de confianza.
```

## Fase 11 — Síntesis y redacción del punto 1 (5–6 h)

Cubre: síntesis del punto 1 y esquema conceptual. [K26, K48, F23, F24, F25, F26]

Lo escribe el grupo, sin IA en el primer borrador:

- Las cinco respuestas de la síntesis: cuál es la demanda y qué la controla; cuánta agua devuelve la cuenca y con qué incertidumbre; en qué meses manda la energía y en cuáles el agua; qué ha cambiado y por qué; qué proceso distingue a la cuenca.
- Una tabla de tres columnas: observado, estimado con modelos o productos, hipótesis de interpretación.
- Para cada resultado principal: mecanismo, evidencia propia, cita con sección y al menos una explicación alternativa.
- El esquema conceptual de la Tarea 1 actualizado con los flujos y almacenamientos estimados.

Prompt para Opus (crítica, no redacción):

```
Este es mi borrador de resultados y discusión del punto 1: <TEXTO>. No lo
reescribas. Señala: (a) afirmaciones sin cifra, figura o cita que las
respalde; (b) procesos nombrados sin contraste con mis datos; (c) resultados
sin incertidumbre o sin limitación; (d) lugares donde falta una explicación
alternativa; (e) mezclas de ETo, ETp, E0 y ET; (f) figuras no citadas o que no
sostienen ningún argumento.
```

Punto de control sin IA: cada integrante explica una figura distinta en dos minutos: qué muestra, qué proceso hay detrás y qué la debilitaría.

## Cierre común a los dos puntos

Cubre: [I01–I09, K49, R01–R14, G1–G7]

### Cierre A — domingo 22: el informe

Primero, con el código congelado: recortar datos/punto1 y datos/punto2. Listar los archivos que los scripts leen de verdad, conservar solo esos (recortados a la cuenca y al periodo) con sus metadatos y quitar el resto de la copia de la Tarea 1. Luego ejecutar todo desde cero para confirmar que no falta nada [R06, R07].

- Informe integrado, con las cinco secciones en orden: Introducción, Metodología, Resultados y discusión física, Conclusiones, Uso de inteligencia artificial. La introducción presenta la cuenca del punto 1 y el sitio del punto 2, su contexto hidroclimático, la motivación, los objetivos y las preguntas o hipótesis, con bibliografía. La metodología se arma con anexos/borrador_metodologia.md. Las conclusiones responden las preguntas iniciales sin repetir cifras ni traer resultados nuevos.
- Referencias: cada cita del texto en la lista y cada entrada de la lista citada; libros con sección o capítulo.
- Declaración de IA desde la bitácora: herramientas y versión, tareas concretas, qué se verificó y cómo, qué se rechazó o corrigió, contribución de cada integrante.
- Auditoría del informe: en una sesión nueva de Opus, pasar RUBRICA_T2_evaluador.md y el PDF del informe (modo INFORME). Queda la noche y el lunes para corregir, empezando por los faltantes con más puntos recuperables.

### Cierre B — lunes 23: la entrega

- Correcciones de la auditoría del domingo.
- Presentación en PDF, con el nombre T2_202602_GNN_presentacion.pdf. Sin ese archivo la entrega incumple la estructura. Diez minutos para los dos puntos: una historia que permita entender la cuenca y la obra, con pocas figuras legibles y cada una conectada con un proceso o un riesgo. Ensayarla una vez con cronómetro y con el prompt de examen; la exposición es sin IA y cualquier integrante debe poder responder.
- README con sus cinco apartados: integrantes con nombre completo, descripción de carpetas, procedencia de los datos, requisitos y orden de ejecución.
- Prueba desde cero: descomprimir el ZIP en otra carpeta, crear un entorno nuevo y ejecutar todo en el orden del README. Ejecutar codigo/verificar_entrega.py.
- Auditoría de la entrega: pasar la rúbrica y el ZIP en modo ZIP a una sesión nueva de Opus. Anotar ambas auditorías en la bitácora.
