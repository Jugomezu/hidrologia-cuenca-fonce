# Tarea 1 — Análisis de cuenca (Hidrología)

Análisis de la cuenca del río Fonce (San Gil, IDEAM 24027010) y su informe. El análisis se hace en
Python, en notebooks; el informe se arma aparte en HTML.

## Reglas del proyecto

1. **Nada inventado.** Todo número, tabla o afirmación del notebook y del informe sale de los datasets
   descargados o del procesamiento de esos datasets dentro del notebook. Si un dato no se consiguió, se
   dice que falta; no se rellena, no se estima "a ojo" ni se escribe de memoria. Los umbrales y
   supuestos se declaran explícitamente en el código.
2. **Código revisable.** El profesor ejecuta y revisa el código. Debe correr de principio a fin sin
   errores, ser legible, con nombres claros, pasos explícitos y comentarios donde la decisión no sea
   obvia. Nada de resultados pegados a mano ni de celdas que dependan de haber corrido otra cosa antes
   en otro orden.
3. **Todo en español**: texto, comentarios, nombres de variables y funciones, etiquetas de las figuras.
   Lo que venga de una fuente externa en inglés (nombres de columnas de CAMELS-COL, DOI, títulos de
   papers) se conserva tal cual y se explica en español.
4. **El notebook se organiza por punto del taller.** Cada sección lleva el número y el nombre del punto,
   por ejemplo `1. Series mensuales: exploración y validación`. Se avanza de a un punto: el usuario
   avisa cuándo pasar al siguiente. No adelantarse a puntos que no se han pedido.
5. **De diario a mensual, siempre con la misma regla.** Al agregar una serie diaria a mensual, un mes
   al que le falten **cinco o más días** de registro queda **vacío** (NaN); hasta cuatro días faltantes
   el mes se calcula. (El umbral empezó en un día y se amplió a cuatro el 2026-09-24, porque con el
   umbral estricto se perdía el 28 % de los meses de caudal de San Gil por faltantes dispersos.) Esta regla vale para toda serie diaria del proyecto (precipitación, caudal, lo que
   sea) y se aplica con una única función compartida en el notebook, no reescribiéndola cada vez.
6. **El período de estudio es 1998–2022**, unos 25 años. Es el período en que existe IMERG, que es la
   fuente de precipitación principal. Toda serie se recorta a esa ventana antes de analizarla, y los
   datos que existan fuera de ella (CAMELS-COL y los pluviómetros llegan hasta 1981) solo se usan si el
   usuario lo pide explícitamente.
7. **El sujeto de estudio es San Gil (24027010).** Salvo que el usuario pida lo contrario, todo el
   procesamiento y toda figura se hacen **solo para San Gil**. Las cinco subcuencas anidadas (Mérida,
   Nemizaque, Puente Llano, Puente Cabra, Puente Arco) son herramientas para entender a San Gil y se
   usan únicamente cuando aportan a esa lectura; ampliarles el análisis es un extra que se hace solo si
   sobra tiempo, nunca por defecto.
8. **Las figuras se hacen con matplotlib o seaborn.** Nada de Plotly: VS Code no renderiza sus figuras
   en el notebook.
9. **Todos los `import` van en la primera celda** del notebook, junto con la carga de datos. Ninguna
   celda posterior importa nada.
10. **Los datos se cargan en una sola celda** al comienzo del notebook, antes de la primera sección.
11. **Todo análisis que dependa de la precipitación se hace dos veces**, una con cada fuente, y se
    reportan los dos resultados en paralelo:
    - **IMERG**, satélite, promediado sobre el polígono de la cuenca ponderando cada celda por su área
      dentro de ella. Serie completa: los 300 meses de 1998–2022, sin huecos.
    - **El promedio de la red de pluviómetros** del IDEAM: las estaciones que caen **dentro de la
      divisoria** de San Gil (hoy 7 de las 8 descargadas; Mamonal El Hacienda queda fuera, en la
      vertiente del Chicamocha, y no entra). Cada mes se promedia con los pluviómetros que tengan dato
      ese mes; no se rellena ninguno.

    La razón es que las dos fuentes no coinciden: IMERG queda un 12.0 % por debajo de la red
    (185.3 contra 210.7 mm/mes al 2026-09-28, con todas las exclusiones de abajo; la cifra vigente la
    calcula el notebook, sección 4.3). No hay forma de arbitrar cuál tiene la razón —el satélite estima
    indirectamente sobre celdas de 122 km², los pluviómetros miden en puntos, vienen marcados como
    preliminares y ninguno está por encima de 2 625 m—, así que en vez de elegir una y esconder la
    incertidumbre, se arrastra explícitamente hasta el resultado final. Esto **reemplaza** la
    "decisión pendiente" de corregir IMERG por el sesgo: no se corrige, se hacen las dos.

    **Cuando haya que escoger una, manda PL** (decidido el 2026-09-28): son medidas reales de lluvia en
    la cuenca, no una estimación indirecta. PI se sigue calculando en paralelo como contraste.

    **Tramos excluidos de PL en todos los análisis** (decididos el 2026-09-28): Encino (24020040) 2016-2018,
    Pueblo Viejo (24020230) 1998-01 a 2004-11, y 7 meses en 0 mm de Pavas Las y Valle de San José que sus
    vecinos no acompañan. Son problemas de registro. Las exclusiones se declaran en la tabla `EXCLUSIONES`
    de `scripts/07_pluviometros_dhime.py`, que escribe `out/pluviometros_fonce_mensual_depurado.csv`; todo
    análisis lee esa serie. La cruda (`..._1998_2022.csv`) solo se usa para documentar las decisiones.

12. **Notación de las tres variables principales.** A partir del 2026-09-25 se nombran así en el
    notebook, en el informe y en las figuras:
    - **PI** — precipitación de IMERG (satélite), promediada sobre la cuenca ponderando por área.
    - **PL** — precipitación de los pluviómetros del IDEAM (la red, el promedio de las estaciones que
      caen dentro de la divisoria).
    - **Q** — caudal.

    La primera vez que aparece cada sigla en un documento se explica qué es; después se usa suelta. En
    el código los nombres de variable pueden seguir siendo descriptivos (`p_imerg`, `red`, `caudal`),
    pero las etiquetas de figuras, los encabezados de tabla y el texto usan PI, PL y Q.

13. **El área de cada cuenca es la de su polígono, medida por el proyecto** (decidido el 2026-09-27):
    San Gil = 2 098.85 km², geodésica, calculada en `scripts/02_shp_cuencas_estaciones.py` y guardada en
    `out/shp_fonce/areas_cuencas.csv`, que es la única fuente del área. No se usa la columna `area` de
    CAMELS-COL (2 124 km², 1.2 % mayor que su propio polígono). En general, se prefieren los cálculos
    propios a los valores publicados siempre que se puedan hacer. Áreas y longitudes se miden en el
    elipsoide o en EPSG:3116, nunca en UTM 19N (la cuenca está en la zona 18).

14. **Punto decimal** en el notebook, el informe y las figuras (14.68, no 14,68). Los miles se separan
    con espacio (2 098.85).

15. **La ETP es la de Hargreaves calculada por el proyecto con ERA5-Land** (decidido el 2026-09-28):
    `scripts/06b_etp_hargreaves.py` → `out/etp_hargreaves_fonce.csv`, columna `etp_era5land`. La ETP que
    publica CAMELS-COL (`poten_evapo`) sale unas 2.75 veces más alta que su propia fórmula y no se usa en
    ningún cálculo; solo aparece en la comparación de la sección 1.8 del notebook.

16. **Las cifras de los textos salen calculadas, no escritas a mano** (decidido el 2026-09-29). En el
    notebook, una lectura con números se genera desde código (`display(Markdown(f"..."))` con los valores
    calculados) y el markdown fijo queda cualitativo; en el informe, todo número sale de la f-string de
    `scripts/18_reporte_html.py`. El informe no nombra los puntos del taller (4.1, 4.3…): usa los títulos
    de sus secciones.

## Estructura

- `README.md` — punto de entrada para personas y agentes: estado del trabajo, decisiones y cómo trabajar en paralelo.
- `notebooks/` — el análisis.
- `scripts/` — descargas, preparación de datos y generación de figuras e informes, numerados en el orden
  en que se corren; `scripts/README.md` explica la tubería y `scripts/historico/` guarda lo que ya no se usa.
- `data/` — datos crudos tal como se descargaron; no se editan.
- `out/` — productos intermedios (CSV, shapefiles).
- `reporte/` — informe HTML y sus figuras.
- `DATOS_FUENTES.md` — procedencia de cada fuente: título, DOI, licencia, cómo se descargó y SHA-256.
  Toda fuente nueva se registra ahí.
