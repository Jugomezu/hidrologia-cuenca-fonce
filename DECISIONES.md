# Registro de decisiones

Las decisiones de método y de organización que toma el dueño del proyecto (Jugomezu), en orden. En cada una se anota
qué recomendó el agente y, cuando no coincide, **«contradice al agente»**, con la razón que dio el usuario si la dio. Las
reglas permanentes están en `CLAUDE.md`; aquí queda el rastro de cómo se llegó a ellas. Las más recientes van al final.

| Fecha | Tema | Decisión del usuario | Recomendación del agente | ¿Coinciden? |
|---|---|---|---|---|
| 2026-10-04 | Registro de anomalías (4.4) | Tercer estado «descartado» (revisado y sin problema); las banderas de calidad quedan como nota, no como fila | Lo mismo | Sí |
| 2026-10-04 | Referencia ponderada (distancia y altura) para las pruebas de saltos | No se adopta: «solo es complicarnos» | Neutral; propuso 1/d² con altura si se adoptaba | Sí |
| 2026-10-04 | Pueblo Viejo | Primero: excluirlo completo. Después, al ver el efecto (PL sube, más años con P − Q > ETP), se deja como estaba: excluido 1998-01 a 2004-11 y el salto de 2014 marcado como incierto | Conservarlo marcado como incierto | Al final sí; el usuario cambió de decisión |
| 2026-10-04 | Ciclo anual: climatología y concentración | Mediana; concentración con el PCI y forma con armónicos; temporadas sobre o bajo el mes típico | Mediana; PCI y SI; armónicos y picos con prominencia; umbral de la media mensual | En lo esencial |
| 2026-10-04 | Ciclo anual: estacionalidad débil | El PCI no se usa en ningún lado; Kruskal-Wallis decide si hay estacionalidad | Kruskal-Wallis (el PCI no distinguía bimodal de débil) | Sí |
| 2026-10-04 | Q en el régimen | Todo el régimen de Q en mm/mes | mm/mes | Sí |
| 2026-10-04 | Desfase estacional | Fase del armónico de 6 meses, con PL y PI, y *bootstrap*; la correlación cruzada se mueve al ciclo anual | Lo mismo | Sí |
| 2026-10-05 | Integración del Punto 2 al informe | Integrar lo que no existía y borrar el visor `punto2_i.html` | Lo mismo | Sí |
| 2026-10-05 | Informe | HTML autocontenido que los agentes de los compañeros puedan editar; deja de publicarse como artifact | Lo mismo, editando siempre el script | Sí |
| 2026-10-05 | Párrafos del informe | Acortarlos | Recorte de 30 a 40 % en los largos | Sí |
| 2026-10-07 | Variabilidad mes a mes | Solo DE y CV, con la inestabilidad del CV; CV de la temperatura en K; después se agregan asimetría e influencia con una o dos figuras | DE, RIC, CV y RIC/mediana; asimetría clásica y de Bowley | **Contradice al agente** (menos medidas) |
| 2026-10-07 | Notebook | Se congela; todo lo nuevo va solo a los scripts y al informe; el script del informe se parte en cálculos y página | Congelarlo solo si el taller no exige notebook | Sí, con la condición dicha |
| 2026-10-07 | Picos del ciclo y estabilidad | Picos por armónicos; tolerancia de ±1 mes; Q solo con años completos; mitades iguales | Lo mismo | Sí |
| 2026-10-07 | Explicación de la diferencia de PI entre mitades | Solo el ENSO; no mencionar TRMM → GPM ni el salto de Pueblo Viejo | Mencionar las tres causas | **Contradice al agente** |
| 2026-10-07 | Anomalías y años contrastantes | Anomalía en RIC respecto a la mediana; 2 húmedos y 2 secos; Q solo con años completos; dos figuras, la del ciclo solo con PL | Lo mismo | Sí |
| 2026-10-07 | Años contrastantes, después de ver julio de 2010 | Elegirlos con PL y PI juntas | Lo mismo | Sí |
| 2026-10-07 | Gráficas repetidas lluvia–caudal | Juntarlas en una sola sección | Quedarse solo con la prueba fuera del período | **Contradice al agente** |
| 2026-10-07 | Registro largo (regla 6) | Primero: mantener solo 1998–2022. Después: dos períodos, 1998–2022 para comparar y desde 1981 para tendencias | Dos períodos | Al final sí; el usuario cambió de decisión |
| 2026-10-07 | Anomalías estandarizadas | Referencia 1998–2022; las anomalías robustas se usan tal como están; las tres temperaturas siempre juntas en las gráficas | Lo mismo | Sí |
| 2026-10-08 | PL para tendencias (PL*) | Red fija de estaciones desde 1981, sin Pueblo Viejo en ningún año, sin rachas de valores repetidos (se quitan todos sus meses) y sin picos extremos | Red fija de las 5 estaciones; conservar las rachas | **Contradice al agente** en las rachas: se quitan |
| 2026-10-08 | Criterio de picos extremos de PL* | Primero: más de 3 veces la mediana y más de 300 mm, sin mirar los vecinos. Después se vuelve al criterio con la condición de los vecinos (3 veces su promedio) | Con la condición de los vecinos | Al final sí; el usuario cambió de decisión |
| 2026-10-08 | Salto de Valle de San José en 1998 | No agregarlo al registro de anomalías | Agregarlo como incierto | **Contradice al agente** |
| 2026-10-08 | Explicación de Mann-Kendall en el informe | Eliminarla (parecía no usarse) | Conservarla: se usa en tablas y textos y el taller la exige | **Contradice al agente**; pendiente |
| 2026-10-08 | Punto 3.5 | Hacer FDR, el gráfico de pendientes por mes, significancia contra relevancia y la banda OLS; no la tabla de consistencia ni la sensibilidad a años y fechas | FDR, pendientes por mes y relevancia primero | En lo esencial |
| 2026-10-08 | Tendencias: Pettitt | Pettitt anual y mensual con permutación, Pettitt sin la recta y BIC con empate a menos de 2 | Lo mismo | Sí |
| 2026-10-08 | Trabajo de angomezma-cyber (rama `punto-4`) | Lo integra el agente; PL* y ERA5-Land en el registro extendido; el notebook sigue congelado; ella no revisa el PR, lo revisan el usuario y el agente con las reglas y luego contra la rúbrica | Lo mismo; sugirió que ella revisara | **Contradice al agente** en quién revisa |
| 2026-10-08 | Fusiones | Los PR #2 a #18 se fusionan como excepción a la regla 20, autorizada por el usuario en cada uno | Pedir la revisión de otra persona | **Contradice al agente** (regla 20) |
| 2026-10-08 | Punto 5.1: SST | ERSST v5 | ERSST v5 | Sí |
| 2026-10-08 | Punto 5.1: variables atmosféricas | Viento a 850 hPa (u y v) y humedad específica a 850 hPa, para el transporte de humedad; ni presión al nivel del mar ni altura geopotencial | Presión al nivel del mar y viento a 850 hPa | **Contradice al agente** |
| 2026-10-08 | Punto 5.1: malla | Remuestreo a 2° | 2° (la malla de ERSST) | Sí |
| 2026-10-08 | Punto 5.1: período | 1998–2022, «por simplicidad» | 1981–2022 (y 1998–2022 aparte) | **Contradice al agente** |
| 2026-10-08 | Registro de decisiones | Llevar este archivo desde ahora, marcando cuando el usuario contradice al agente | — | — |
| 2026-10-08 | Punto 5.1: transporte de humedad | q × V a 850 hPa con las medias mensuales (se declara que pierde el transporte de los eventos de días) | Lo mismo; el flujo integrado en la columna solo como contraste si hiciera falta | Sí |
| 2026-10-08 | Punto 5.1: celdas bajo tierra a 850 hPa | Una caja de 2° queda vacía si **cualquiera** de sus celdas de 0.25° tiene presión superficial menor que 850 hPa ese mes | Vacía solo si más de la mitad de sus celdas está bajo tierra | **Contradice al agente** (más estricto: se pierde casi toda la cordillera) |
| 2026-10-08 | Punto 5.1: remuestreo | Promedio por bloques ponderado por área (cos de la latitud) en las cajas de 2° de ERSST | Lo mismo | Sí |
| 2026-10-08 | Punto 5.1: archivos crudos | Los crudos (ERSST ~160 MB y ERA5 a 0.25°, varios GB) quedan fuera de git, con su SHA-256 y el script para volver a bajarlos; el producto a 2° sí se versiona | Lo mismo (el usuario no objetó) | Sí |
| 2026-10-08 | Punto 5.1: fuente de ERA5 | Primero: pedir ERA5 ya interpolado a 2° al CDS, para no esperar la cola (contradecía al agente, que recomendaba esperar los datos de 0.25° y promediar por bloques). Después, al ver que la cola seguía horas sin atender los pedidos de 850 hPa: bajar el mismo ERA5 mensual de la copia del NSF NCAR GDEX (d633001), sin cola, a 0.25°, y **volver al método original**: promedio por bloques ponderado por área y máscara estricta | GDEX a 0.25° con el método original | Al final sí; el usuario cambió de decisión |
