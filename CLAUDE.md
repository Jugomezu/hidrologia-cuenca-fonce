# Tarea 1 — Análisis de cuenca (Hidrología)

Análisis de la cuenca del río Fonce (San Gil, IDEAM 24027010) y su informe. El análisis se hace en
scripts de Python (`scripts/`) y se presenta en un informe HTML. **El notebook
`notebooks/02_precipitacion_vs_caudal.ipynb` quedó congelado el 2026-10-07**: se conserva, corre y se puede
entregar, pero ya no se modifica; todo lo nuevo va a los scripts y al informe.

## Reglas del proyecto

1. **Nada inventado.** Todo número, tabla o afirmación del notebook y del informe sale de los datasets
   descargados o del procesamiento de esos datasets dentro de los scripts del proyecto. Si un dato no se consiguió, se
   dice que falta; no se rellena, no se estima "a ojo" ni se escribe de memoria. Los umbrales y
   supuestos se declaran explícitamente en el código.
2. **Código revisable.** El profesor ejecuta y revisa el código; el análisis está en `scripts/18_calculos_informe.py`.
   Debe correr de principio a fin sin errores, ser legible, con nombres claros, pasos explícitos y comentarios donde la decisión no sea
   obvia. Nada de resultados pegados a mano ni de pasos que dependan de haber corrido otra cosa antes
   en otro orden.
3. **Todo en español**: texto, comentarios, nombres de variables y funciones, etiquetas de las figuras.
   Lo que venga de una fuente externa en inglés (nombres de columnas de CAMELS-COL, DOI, títulos de
   papers) se conserva tal cual y se explica en español.
4. **Se avanza de a un punto del taller**: el usuario avisa cuándo pasar al siguiente. No adelantarse a
   puntos que no se han pedido. El notebook congelado está organizado por punto del taller; el informe se
   organiza por temas y no nombra los puntos.
5. **De diario a mensual, siempre con la misma regla.** Al agregar una serie diaria a mensual, un mes
   al que le falten **cinco o más días** de registro queda **vacío** (NaN); hasta cuatro días faltantes
   el mes se calcula. (El umbral empezó en un día y se amplió a cuatro el 2026-09-24, porque con el
   umbral estricto se perdía el 28 % de los meses de caudal de San Gil por faltantes dispersos.) Esta regla vale para toda serie diaria del proyecto (precipitación, caudal, lo que
   sea) y se aplica con la función `a_mensual` de los scripts, no reescribiéndola cada vez.
6. **Dos períodos, según la pregunta** (1998–2022 decidido al comienzo; el registro largo, el 2026-10-07).
   - **Para comparar variables y productos, 1998–2022**, unos 25 años: el período común, en que existe
     IMERG. Toda comparación entre PI, PL, Q y temperatura, y todo lo que ya está en el informe, se hace en
     esa ventana.
   - **Para cambios de largo plazo (tendencias), el registro completo de cada variable desde 1981, cuando
     exista.** Q de CAMELS-COL y los pluviómetros llegan hasta 1981; IMERG empieza en 1998 y no se extiende;
     ERA5-Land hoy solo está descargado para 1998–2022. La menor duración de IMERG no recorta los otros
     registros.
   - En el registro largo se reportan las fechas, los meses válidos, los vacíos y los cambios de fuente de
     cada serie; «serie completa» no significa rellenar faltantes. Los datos anteriores a 1998 no han pasado
     por el control de calidad del proyecto (las exclusiones de la regla 11 cubren 1998–2022): antes de usarlos
     se revisan, y lo que se decida se declara en el código.
   - Las dos preguntas se distinguen en el informe: no se mezclan resultados de una ventana con los de la otra.
7. **El sujeto de estudio es San Gil (24027010).** Salvo que el usuario pida lo contrario, todo el
   procesamiento y toda figura se hacen **solo para San Gil**. Las cinco subcuencas anidadas (Mérida,
   Nemizaque, Puente Llano, Puente Cabra, Puente Arco) son herramientas para entender a San Gil y se
   usan únicamente cuando aportan a esa lectura; ampliarles el análisis es un extra que se hace solo si
   sobra tiempo, nunca por defecto.
8. **Figuras.** Las imágenes fijas (`reporte/figuras/`) se hacen con matplotlib o seaborn; las gráficas
   interactivas del informe, con Plotly, que va incrustado en el HTML.
9. **Los `import` van al comienzo de cada script.**
10. **Los datos se leen de `data/` y `out/`**, con rutas relativas a la raíz del repositorio. Ningún script
    depende de haber corrido el notebook.
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
    calcula `scripts/18_calculos_informe.py`). No hay forma de arbitrar cuál tiene la razón —el satélite estima
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
    ningún cálculo; solo aparece en la comparación de la sección de la ETP del informe.

16. **Las cifras de los textos salen calculadas, no escritas a mano** (decidido el 2026-09-29). En el
    informe, todo número se calcula en `scripts/18_calculos_informe.py` y se inserta en la página desde `scripts/18b_reporte_html.py`;
    si un texto afirma algo sobre los datos («es mucho mayor que…»), se protege con un `assert` o se
    redacta de forma condicional. El informe no nombra los puntos del taller (4.1, 4.3…): usa los títulos de
    sus secciones.

17. **La persona debe entender cada cambio que hace el agente.** Quien trabaja en este proyecto tiene que
    poder explicar de memoria cada cambio que entrega: el profesor revisa el trabajo y lo pregunta. Por
    eso el agente **no trabaja en piloto automático**:
    - **Si la instrucción es demasiado amplia** para que la persona entienda lo que va a pasar («haz el
      punto 5», «arregla todo», «termina el análisis», «mejora el informe»), el agente **se detiene y no
      empieza**. Explica qué implicaría, lo parte en pasos pequeños y pide que la persona elija o apruebe
      el primero.
    - **Antes de cada paso,** dice qué va a cambiar, en qué archivos y por qué, y espera confirmación. Nada
      de lotes grandes de cambios de una sola vez.
    - **Después de cada paso,** explica en palabras simples qué hizo, qué decisión se tomó y qué resultado
      salió. Luego verifica que la persona lo entendió, por ejemplo pidiéndole que lo resuma o
      preguntándole por qué se hizo así, antes de seguir.
    - **Las decisiones de método** (umbrales, exclusiones de datos, qué fuente usar, cómo tratar un hueco)
      las toma la persona, no el agente. El agente presenta las opciones con su evidencia y recomienda
      una, pero no decide solo.
    - **Si la persona pide «hazlo tú» o «no me expliques»,** el agente recuerda esta regla y sigue
      explicando: el objetivo es que la persona aprenda y pueda defender el trabajo, no solo que el trabajo
      quede hecho.

18. **El notebook está congelado** (decidido el 2026-10-07). No se le agregan secciones ni se cambia su
    contenido. Si alguna vez hubiera que corregirlo, cada elemento de `source` termina en `"\n"` salvo el
    último, toda celda lleva su `id` y después se ejecuta completo con
    `jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 …`.
    **Lo que un texto anuncia, existe**, en el informe igual que en el notebook: si un texto dice que viene
    una figura o una tabla, está.

19. **Cada archivo va en su lugar.**
    - Los scripts van en `scripts/`, numerados según su lugar en la tubería (con sufijo, como `16b`, para no
      renumerar), y se registran en `scripts/README.md`.
    - Las páginas HTML van en `reporte/`. **Nada suelto en la raíz** del repositorio.
    - Todo archivo de `out/` lo produce un script del repositorio, al correrlo: no se hace a mano ni con otra
      herramienta. Sus textos van en español.

20. **Todo pull request lleva descripción**: qué cambia, por qué, qué decisiones de método se tomaron y cómo
    se verificó. Quien lo abre tiene que poder explicarlo (regla 17). Desde el 2026-10-08 el proyecto es
    individual y el dueño puede fusionar sus propios PR (antes, nadie fusionaba el suyo).

21. **Nada entra a `main` sin verificar antes que cumple las reglas, sin excepciones** (decidido el
    2026-10-03; aplica también al dueño del repositorio y a su agente). Antes de fusionar un PR o de
    hacer push a `main` se comprueba, y se deja constancia en el PR o en el mensaje de commit:
    - los scripts que cambiaron corren sin errores desde la raíz;
    - si cambió algo que lee el informe, se regenera con `python scripts/18b_reporte_html.py`, su JavaScript pasa
      `node --check` y el HTML abre en el navegador sin errores;
    - el notebook congelado no cambió (regla 18);
    - las reglas 1 a 20: nada inventado; todo en español; PI y PL en paralelo, con la PL depurada; cifras de
      los textos calculadas; punto decimal y espacio para los miles; archivos en su lugar; PR con
      descripción.

    Si algo no cumple, no se fusiona: se pide la corrección en el mismo PR.

22. **Hay un solo informe** (decidido el 2026-10-04): `reporte/reporte-fonce.html`, generado por
    `scripts/18b_reporte_html.py` con los cálculos de `scripts/18_calculos_informe.py`. Todo lo que vaya al informe, de cualquier
    punto y de cualquier persona, entra como una sección de esos dos scripts. El HTML no se edita a mano. **No se hacen informes, visores ni páginas HTML aparte.** El visor
    `reporte/punto2_i.html` del Punto 2, anterior a esta regla, se integró al informe y se borró el 2026-10-04.

## Estructura

- `README.md` — punto de entrada para personas y agentes: estado del trabajo, decisiones y cómo trabajar en paralelo.
- `notebooks/` — el notebook del análisis inicial, congelado el 2026-10-07.
- `scripts/` — descargas, preparación de datos y generación de figuras e informes, numerados en el orden
  en que se corren; `scripts/README.md` explica la tubería y `scripts/historico/` guarda lo que ya no se usa.
- `data/` — datos crudos tal como se descargaron; no se editan.
- `out/` — productos intermedios (CSV, shapefiles).
- `reporte/` — informe HTML y sus figuras.
- `DATOS_FUENTES.md` — procedencia de cada fuente: título, DOI, licencia, cómo se descargó y SHA-256.
  Toda fuente nueva se registra ahí.
