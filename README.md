# Análisis de la cuenca del río Fonce hasta San Gil

Tarea 1 de Hidrología: análisis de la cuenca del río Fonce hasta la estación de aforo **San Gil (IDEAM
24027010)**, en Santander, Colombia. El análisis se hace en scripts de Python y se presenta en un informe
HTML. El notebook del análisis inicial quedó congelado el 2026-10-07 (sección 2).

Este README está escrito para que **cualquier persona o agente** que llegue al repositorio entienda el
proyecto y pueda trabajar en un punto del taller en paralelo con otros, sin romper lo que ya está hecho.

---

## 1. Lo primero que hay que leer

1. **[`CLAUDE.md`](CLAUDE.md)** tiene las **reglas del proyecto**, y son obligatorias. Resumen en la
   sección 4 de este README.

   > **Agentes: agreguen una copia de `CLAUDE.md` a sus instrucciones principales** antes de empezar, y
   > síganla durante toda la sesión.
   > - **Claude Code** la carga solo desde la raíz del repositorio.
   > - **Otros agentes** deben copiarla a su archivo de instrucciones de base (`AGENTS.md`, `.cursorrules`,
   >   `.github/copilot-instructions.md`, las «custom instructions» o el prompt de sistema, según la
   >   herramienta).
   >
   > Si `CLAUDE.md` cambia en `main`, hay que volver a copiarla.
2. **[`DATOS_FUENTES.md`](DATOS_FUENTES.md)** registra la procedencia de cada dato: título, DOI, licencia,
   cómo se descargó, SHA-256 y las decisiones tomadas sobre cada fuente.
3. **[`scripts/README.md`](scripts/README.md)** describe la tubería de scripts, en orden, con lo que lee
   y lo que produce cada uno.
4. **[`PLAN_CONTROL_CALIDAD.md`](PLAN_CONTROL_CALIDAD.md)** es el plan de la sección de control de
   calidad (punto 4 del notebook), con su estado.

## 2. Estado del trabajo

El análisis vive en `scripts/` y se presenta en el informe. El notebook
[`notebooks/02_precipitacion_vs_caudal.ipynb`](notebooks/02_precipitacion_vs_caudal.ipynb) quedó **congelado
el 2026-10-07**: se conserva, corre de principio a fin y se puede entregar, pero ya no se le agrega nada;
todo lo nuevo va a los scripts y al informe. Lo que tiene, por punto del taller:

| Sección | Contenido | Estado |
|---|---|---|
| 1.0–1.8 | Series mensuales: exploración y validación (estadísticos, cajas, IMERG, comparación PI–PL, lluvia contra caudal, completitud, temperatura, gradiente altitudinal, Encino, ETP) | hecho |
| 1.9 | Ciclo anual: estadísticos por mes y régimen (mediana por mes, temporadas, concentración, armónicos de Fourier, Kruskal-Wallis; PL, PI y Q bimodales) | hecho |
| 1.10 | Desfase estacional entre la lluvia y el caudal (fase del armónico de 6 meses, PL y PI) | hecho |
| 1.11 | Variabilidad (DE y CV, con su inestabilidad), asimetría e influencia de cada año, mes a mes | hecho |
| 2.1–2.5 | Morfometría (forma, perfil del cauce, curva hipsométrica, pendientes, problemas de CAMELS-COL) | hecho |
| 3 | Cómo se relacionan las variables (correlaciones, anomalías) | hecho |
| 4.1 | Completitud: días válidos, criterio de los 4 días | hecho |
| 4.2 | Control de calidad básico sobre los archivos crudos | hecho |
| 4.3 | Anomalías: saltos (doble masa, Pettitt), secuencias constantes, extremos, cobertura | hecho |
| 4.4 | Trazabilidad: registro de anomalías, comprobaciones, decisiones y efecto | hecho |
| 4.5 | Coherencia hidrológica (residuo P − Q, meses con Q > P) | hecho |

El **índice de flujo base** de CAMELS-COL se quitó del informe, y se decidió no calcular uno propio
(2026-10-04).

Después de congelar el notebook, **todo el análisis nuevo está solo en los scripts y el informe** (el notebook no hace
falta para reproducirlo): años contrastantes y anomalías respecto al ciclo anual; **anomalías y anomalías
estandarizadas** (a = X − µ, z = a / s, referencia fija 1998–2022, las seis variables); **tendencias de largo plazo**
(registro completo desde 1981 cuando existe: Q, temperatura y PL*, la red fija de pluviómetros; OLS con Newey-West,
Mann-Kendall/Sen, LOESS, Pettitt, FDR, significancia contra relevancia); y **frecuencias** (Fourier: Lomb-Scargle y
FFT, bandas, ruido rojo AR(1)), que viene de la rama `punto-4` de angomezma-cyber, integrada a los scripts el 2026-10-08.
La ampliación del Punto 2 de esa rama no se integró: lo que ya estaba en `main` se consideró suficiente (decisión del
usuario, 2026-10-08).

El **informe** [`reporte/reporte-fonce.html`](reporte/reporte-fonce.html) lo genera
`scripts/18b_reporte_html.py`, con los cálculos de `scripts/18_calculos_informe.py`. Es un solo archivo que se abre en cualquier navegador, **sin internet**: las
figuras y Plotly van dentro (sin conexión, solo cambian las tipografías por otras de reemplazo). Cómo
editarlo: sección 9.

## 3. Los datos ya están descargados: no hace falta correr las descargas

Todo lo que se descargó está en `data/`, y todos los productos intermedios en `out/`. **No hace falta
correr los scripts de descarga**; ese trabajo ya se hizo. Las instrucciones de cómo se descargó cada cosa
se conservan en `DATOS_FUENTES.md` y en el encabezado de cada script, por si alguna vez hay que rehacerlo.

Scripts que necesitan acceso externo (**no correrlos** salvo que se quiera rehacer la descarga):

| Script | Qué necesita |
|---|---|
| `03_recorte_dem.py` | el mosaico nacional del DEM en una carpeta compartida (`G:`), fuera del repositorio |
| `04_imerg_descarga_mensual.py` | credenciales de NASA Earthdata (archivo netrc) y `curl` |
| `06_era5land_temperatura.py` | una cuenta de Google Earth Engine autenticada |
| `07_pluviometros_dhime.py` | internet, para consultar el catálogo público de estaciones del IDEAM (sin credenciales). Aquí se declaran las exclusiones de PL: **sí se corre si se cambia una exclusión** |

Un archivo quedó fuera del repositorio: `data/camels_col/04_hydromet.zip` (184 MB, más que el límite de
GitHub). Es redundante, porque sus 346 archivos ya están descomprimidos en `data/camels_col/hydromet/`.
Cómo bajarlo de Zenodo está en `DATOS_FUENTES.md`.

## 4. Reglas del proyecto (resumen; manda `CLAUDE.md`)

- **La persona debe entender cada cambio (regla 17).** El agente no trabaja en piloto automático.
  - Si la instrucción es demasiado amplia para que la persona sepa lo que va a pasar, el agente se detiene
    y la parte en pasos pequeños.
  - Antes de cada paso dice qué va a cambiar y espera confirmación; después explica lo que hizo y verifica
    que se entendió.
  - Las decisiones de método las toma la persona.
  - Cada quien tiene que poder explicar de memoria lo que entrega.
- **Nada inventado.** Todo número sale de los datos o de su procesamiento. Si falta un dato se dice; no
  se rellena ni se estima «a ojo».
- **Las cifras de los textos salen calculadas, no escritas a mano**: se calculan en `scripts/18_calculos_informe.py` y
  la página las inserta. Así, cuando cambian los datos, no hay cifras viejas que perseguir.
- **Código revisable y reproducible.** El profesor ejecuta y revisa los scripts; corren de principio a fin
  sin errores desde la raíz.
- **Todo en español**: textos, comentarios, variables y figuras.
- **El notebook está congelado** (2026-10-07): no se modifica. El informe **no** nombra los puntos del
  taller: usa títulos de sección.
- **Figuras:** las fijas con matplotlib; las interactivas del informe con Plotly, incrustado en el HTML.
- **Período 1998–2022**, el de IMERG, para comparar variables y productos; **desde 1981, cuando exista**, para tendencias de largo plazo (regla 6). **Sujeto: San Gil**; las subcuencas solo si aportan.
- **Punto decimal y espacio para los miles** (2 098.85).

## 5. Notación y decisiones vigentes

- **PI**: precipitación de IMERG Final V07, promediada sobre la cuenca ponderando cada celda por su área
  dentro de ella.
- **PL**: precipitación de los pluviómetros del IDEAM: el promedio, cada mes, de los **7 pluviómetros
  dentro de la divisoria** que tengan dato.
- **Q**: caudal en San Gil (IDEAM, vía CAMELS-COL).

Decisiones que ya están tomadas y no se reabren sin consultar (detalle y fecha en `CLAUDE.md` y en
`DATOS_FUENTES.md`):

- **Área:** la del polígono, medida por el proyecto (`out/shp_fonce/areas_cuencas.csv`), no la de
  CAMELS-COL. Áreas y longitudes en el elipsoide o en EPSG:3116.
- **De diario a mensual:**
  - una única función, `a_mensual`: un mes con **5 o más días faltantes** queda vacío;
  - los **acumulados** de meses incompletos son el promedio de los días con dato por los días del mes,
    nunca una suma parcial.
- **PI y PL:** todo análisis de lluvia se hace con **PI y PL en paralelo**. **Cuando hay que escoger,
  manda PL.**
- **Tramos excluidos de PL** (tabla `EXCLUSIONES` en `scripts/07_pluviometros_dhime.py`, evidencia en las
  secciones 1.7 y 4.3):
  - Encino 2016–2018;
  - Pueblo Viejo de 1998-01 a 2004-11;
  - 7 meses en 0 mm de Pavas Las y Valle de San José.

  Todo análisis lee `out/pluviometros_fonce_mensual_depurado.csv`.
- **Marcados como inciertos, pero conservados:**
  - Coromoro: salto de −20 % desde 2003;
  - Pueblo Viejo desde abril de 2014: un segundo salto, de −25 %, en el tramo que queda después del
    excluido (`out/anomalias_segundo_corte.csv`);
  - PI: salto de +11 % desde junio de 2014. Cae en el cambio de calibración de IMERG de TRMM a GPM, pero
    con PL sin Pueblo Viejo baja a +6 % y deja de ser significativo: buena parte viene de Pueblo Viejo, y
    el cambio TRMM → GPM no es la explicación principal.
- **Registro de anomalías** (sección 4.4): `out/registro_anomalias.csv`, de `scripts/07d_trazabilidad.py`,
  con lo comprobado, lo decidido, el efecto y el estado (corregido, incierto o descartado) de cada una.
- **Temperatura:** la de **ERA5-Land**. MSWX, que viene en CAMELS-COL, solo sirve para comparar.
- **ETP:** la de **Hargreaves calculada por el proyecto con ERA5-Land** (`scripts/06b_etp_hargreaves.py`).
  La ETP que publica CAMELS-COL sale unas 2.75 veces más alta que su propia fórmula y no se usa.
- **Frecuencias (Fourier), estabilidad de Q frente a la ventana** (2026-10-08): el tramo continuo más largo de Q
  tiene 69 meses, menos que un segmento de Welch (120), así que Welch se reduciría a Hann. En su lugar se promedia
  Lomb-Scargle sobre tramos de 120 meses con traslape de la mitad, sobre toda la serie con sus vacíos. Lo decidió el
  usuario, con la recomendación del agente; se descartaron Welch con segmentos de 36 meses (solo 2 segmentos) y no
  probarlo.
- **Frecuencias (Fourier), ancho de las bandas anual y semianual** (2026-10-08): ±Δf (Δf = 1/N) alrededor de 1/12 y
  1/6 ciclos/mes, el lóbulo principal del pico; la banda alta empieza donde termina la semianual. Con ±Δf/2, la versión
  original, la semianual de PL daba 32 % cuando el ciclo medio predice ~50 %; con ±Δf da 49 %. Lo decidió el usuario,
  con la recomendación del agente; se descartaron ±2Δf y dejar ±Δf/2 declarándolo.
- **Frecuencias (Fourier), meses extremos en la prueba de sensibilidad** (2026-10-08): se quitan los mismos atípicos de
  «Revisión de outliers» (1.5 RIC por fuera de los cuartiles de su mes del calendario), para que el informe tenga un
  solo criterio de extremos. Lo decidió el usuario, **distinto de lo que recomendó el agente**: el agente proponía
  quitar el 2 % más extremo de cada variable (6 meses en todas, para que la prueba fuera comparable entre variables);
  el usuario prefirió la consistencia con el resto del informe. Se descartó también el criterio del PR original (3 RIC
  desde la mediana de todas las anomalías), que no aparece en otra parte y en PL y PI no quitaba ningún mes. Con los
  atípicos del proyecto, ningún pico de las anomalías se mueve.

## 6. Estructura del repositorio

```
CLAUDE.md                 reglas del proyecto (obligatorias)
DATOS_FUENTES.md          procedencia de cada dato y decisiones sobre las fuentes
PLAN_CONTROL_CALIDAD.md   plan y estado de la sección 4 (control de calidad)
requirements.txt          paquetes de Python, con versión
notebooks/                el notebook del análisis inicial, congelado el 2026-10-07
scripts/                  la tubería, numerada en el orden en que se corre (ver scripts/README.md)
  historico/              scripts que ya no se usan (no correrlos)
data/                     datos crudos tal como se descargaron (no se editan)
out/                      productos intermedios (CSV, shapefiles) que leen los scripts y el informe
reporte/                  informe HTML y sus figuras
InfoPreliminar/           dos artículos de referencia sobre la cuenca (PDF y texto extraído)
```

## 7. Cómo correr

Desde la **raíz del repositorio**, con Python 3.13:

```
pip install -r requirements.txt
```

- **Rehacer productos de `out/`:** correr los scripts que hagan falta, en orden, desde la raíz:
  `python scripts/NN_nombre.py`. Qué depende de qué está en `scripts/README.md`. Por ejemplo, si se cambia
  una exclusión de PL: 07, 07b, 07c, 07d, 09, 10, 11, 16 y 18b.
- **Rehacer el informe:** `python scripts/18b_reporte_html.py` corre los cálculos de `scripts/18_calculos_informe.py` y escribe
  `reporte/reporte-fonce.html` (unos segundos).
- **El notebook congelado,** si se quiere ver: `jupyter nbconvert --to notebook --execute --inplace
  --ExecutePreprocessor.timeout=1200 notebooks/02_precipitacion_vs_caudal.ipynb` (unos 10 minutos).

## 8. Cómo trabajar en paralelo sin pisarse

- **Una rama por punto del taller** (por ejemplo `punto-4.4`, `punto-5`) y un pull request a `main`, **con
  descripción** (qué, por qué, cómo se verificó), y **nada entra a `main` sin verificar antes que cumple las
  reglas** (reglas 20 y 21 de `CLAUDE.md`, sin excepciones). Desde el 2026-10-08 el proyecto es individual:
  el dueño fusiona sus propios PR.
- **El notebook no se toca** (regla 18): está congelado.
- **Scripts nuevos:** se numeran según dónde caen en la tubería (se usaron sufijos como `06b`, `07b` y `07c`
  para no renumerar). Se registran en `scripts/README.md`.
- **Un solo informe (regla 22):** todo lo que vaya al informe entra como sección de `scripts/18_calculos_informe.py` (el
  cálculo) y de `scripts/18b_reporte_html.py` (la página); no se hacen informes ni visores HTML aparte.
- **Fuentes nuevas:** toda fuente descargada se registra en `DATOS_FUENTES.md`, con DOI o URL, licencia y
  SHA-256.
- **Decisiones que cambian datos compartidos**, como una exclusión, un umbral o la fuente de una variable,
  se consultan antes: mueven cifras en todo el informe.
- **Antes de dar algo por terminado,** correr los scripts que cambiaron y, si se tocó el informe,
  regenerarlo y abrirlo en el navegador.

## 9. Cómo editar el informe (personas y agentes)

El informe `reporte/reporte-fonce.html` **no se edita a mano**: lo generan dos scripts, y cualquier cambio
hecho directamente en el HTML se pierde la próxima vez que alguien lo regenere. Tampoco se publica en otro
lado como fuente: la única fuente del informe son esos scripts, en este repositorio.

1. **Dónde está cada cosa.**
   - **`scripts/18_calculos_informe.py`: el análisis.** Lee de `out/` y `data/` y calcula todo lo que el informe muestra, en
     bloques por tema (por ejemplo `# ---- régimen del ciclo anual`). Solo cálculos: deja resultados en
     variables (números, tablas de pandas, series para las gráficas), sin HTML.
   - **`scripts/18b_reporte_html.py`: la página.** Corre los cálculos, arma las filas de las tablas y escribe el HTML con
     una f-string enorme, `pagina`, que contiene el texto, el CSS y el JavaScript. Dentro de ella, **las
     llaves de CSS y de JavaScript van dobladas** (`{{` y `}}`); las llaves sencillas son expresiones de
     Python, como `{n(AREA_SG_KM2)}`. Al final van las funciones `dibujar...()` de las gráficas (Plotly),
     que se llaman desde `dibujar()`.
   - Un tema nuevo lleva su bloque de cálculo en el primero y su texto en el segundo.
2. **Reglas al escribir** (detalle en `CLAUDE.md`):
   - toda cifra del texto sale de una variable calculada (regla 16); si el texto afirma algo sobre los datos
     («es mucho mayor que…»), se protege con un `assert` o se redacta de forma condicional;
   - el informe no nombra los puntos del taller (4.1, 4.3…), usa títulos de sección;
   - lo nuevo va dentro de `<div class="revision" data-etiqueta="Revisión · …">` hasta que se apruebe;
   - punto decimal, espacio para los miles, todo en español; PI y PL en paralelo.
3. **Verificar:**
   - `python scripts/18b_reporte_html.py` (desde la raíz) tiene que terminar sin errores;
   - extraer los `<script>` sin `src` del HTML y pasarlos por `node --check`;
   - abrir `reporte/reporte-fonce.html` en el navegador y mirar la sección cambiada, en tema claro y oscuro.
4. **Entregar:** los scripts y el HTML regenerado en el mismo commit, en una rama, con un pull request con
   descripción (reglas 20 y 21).

Plotly está copiado en `reporte/vendor/plotly-2.32.0.min.js` y el script lo mete dentro del HTML; no hay
que tocarlo. Si se cambia de versión, se actualiza el SHA-256 en `scripts/18b_reporte_html.py` y en `DATOS_FUENTES.md`.
