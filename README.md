# Análisis de la cuenca del río Fonce hasta San Gil

Tarea 1 de Hidrología: análisis de la cuenca del río Fonce hasta la estación de aforo **San Gil (IDEAM
24027010)**, en Santander, Colombia. El análisis se hace en Python, en un notebook, y hay además un
informe en HTML generado por un script.

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

El notebook [`notebooks/02_precipitacion_vs_caudal.ipynb`](notebooks/02_precipitacion_vs_caudal.ipynb) se
organiza por punto del taller:

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

El **informe** [`reporte/reporte-fonce.html`](reporte/reporte-fonce.html) lo genera
`scripts/18_reporte_html.py`. Es un solo archivo que se abre en cualquier navegador, **sin internet**: las
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
- **Las cifras de los textos salen calculadas, no escritas a mano.**
  - En el notebook, las lecturas con números se generan con `display(Markdown(f"..."))`; el markdown fijo
    queda cualitativo.
  - En el informe, todo número sale de la f-string de `18_reporte_html.py`.
  - Así, cuando cambian los datos, no hay cifras viejas que perseguir.
- **Código revisable y reproducible.** El profesor ejecuta el notebook completo, que debe correr de
  principio a fin sin errores.
- **Todo en español**: textos, comentarios, variables y figuras.
- **El notebook se organiza por punto del taller** (1.x, 2.x, 3, 4.x). El informe **no** nombra los
  puntos: usa títulos de sección.
- **Imports y carga de datos en la primera celda de código** del notebook. Ninguna otra celda importa ni
  lee archivos.
- **Figuras del notebook con matplotlib** (nada de Plotly en el notebook). El informe HTML sí usa Plotly.
- **Período 1998–2022**, el de IMERG. **Sujeto: San Gil**; las subcuencas solo si aportan.
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

## 6. Estructura del repositorio

```
CLAUDE.md                 reglas del proyecto (obligatorias)
DATOS_FUENTES.md          procedencia de cada dato y decisiones sobre las fuentes
PLAN_CONTROL_CALIDAD.md   plan y estado de la sección 4 (control de calidad)
requirements.txt          paquetes de Python, con versión
notebooks/                el análisis (02_precipitacion_vs_caudal.ipynb es el principal)
scripts/                  la tubería, numerada en el orden en que se corre (ver scripts/README.md)
  historico/              scripts que ya no se usan (no correrlos)
data/                     datos crudos tal como se descargaron (no se editan)
out/                      productos intermedios (CSV, shapefiles) que leen el notebook y el informe
reporte/                  informe HTML y sus figuras
InfoPreliminar/           dos artículos de referencia sobre la cuenca (PDF y texto extraído)
```

## 7. Cómo correr

Desde la **raíz del repositorio**, con Python 3.13:

```
pip install -r requirements.txt
```

- **Solo el análisis:** abrir y ejecutar `notebooks/02_precipitacion_vs_caudal.ipynb` completo. Lee de
  `out/` y de `data/`. Desde la terminal:
  `jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 notebooks/02_precipitacion_vs_caudal.ipynb`
  (tarda unos 10 minutos).
- **Rehacer productos de `out/`:** correr los scripts que hagan falta, en orden, desde la raíz:
  `python scripts/NN_nombre.py`. Qué depende de qué está en `scripts/README.md`. Por ejemplo, si se cambia
  una exclusión de PL: 07, 07b, 07c, 09, 10, 11, 16 y 18, y después el notebook.
- **Rehacer el informe:** `python scripts/18_reporte_html.py` escribe `reporte/reporte-fonce.html`.

## 8. Cómo trabajar en paralelo sin pisarse

- **Una rama por punto del taller** (por ejemplo `punto-4.4`, `punto-5`) y un pull request a `main`, **con
  descripción** (qué, por qué, cómo se verificó). Nadie fusiona su propio PR, y **nada entra a `main` sin
  verificar antes que cumple las reglas** (reglas 18 a 21 de `CLAUDE.md`, sin excepciones).
- **El notebook es un solo archivo JSON grande**, así que dos personas editándolo a la vez chocan en el
  merge. Recomendaciones:
  - cada quien agrega **su propia sección al final**, con celdas nuevas, sin reescribir las de otros;
  - al terminar, antes del pull request, ejecutar el notebook completo y confirmar que no hay errores;
  - si el punto es grande, desarrollarlo en un notebook aparte (`notebooks/03_...ipynb`) que lea las mismas
    salidas de `out/`, y llevarlo al principal al final.
- **Scripts nuevos:** se numeran según dónde caen en la tubería (se usaron sufijos como `06b`, `07b` y `07c`
  para no renumerar). Se registran en `scripts/README.md`.
- **Un solo informe (regla 22):** todo lo que vaya al informe entra como sección de `scripts/18_reporte_html.py`; no se hacen informes ni visores HTML aparte.
- **Fuentes nuevas:** toda fuente descargada se registra en `DATOS_FUENTES.md`, con DOI o URL, licencia y
  SHA-256.
- **Decisiones que cambian datos compartidos**, como una exclusión, un umbral o la fuente de una variable,
  se consultan antes: mueven cifras en todo el notebook y el informe.
- **Antes de dar algo por terminado,** ejecutar el notebook completo y, si se tocó el informe,
  regenerarlo.

## 9. Cómo editar el informe (personas y agentes)

El informe `reporte/reporte-fonce.html` **no se edita a mano**: lo genera `scripts/18_reporte_html.py`, y
cualquier cambio hecho directamente en el HTML se pierde la próxima vez que alguien lo regenere. Tampoco se
publica en otro lado como fuente: la única fuente del informe es ese script, en este repositorio.

1. **Dónde está cada cosa en el script.**
   - Arriba, los **cálculos**: cada sección del informe tiene un bloque que lee de `out/` y calcula sus
     cifras (por ejemplo `# ---- régimen del ciclo anual`).
   - Después, la **página**: una f-string enorme, `pagina`, con el HTML, el CSS y el JavaScript. Dentro de
     ella, **las llaves de CSS y de JavaScript van dobladas** (`{{` y `}}`); las llaves sencillas son
     expresiones de Python, como `{n(AREA_SG_KM2)}`.
   - Al final, el **JavaScript de las gráficas** (Plotly), con una función `dibujar...()` por gráfica, que
     se llama desde `dibujar()`.
2. **Reglas al escribir** (detalle en `CLAUDE.md`):
   - toda cifra del texto sale de una variable calculada (regla 16); si el texto afirma algo sobre los datos
     («es mucho mayor que…»), se protege con un `assert` o se redacta de forma condicional;
   - el informe no nombra los puntos del taller (4.1, 4.3…), usa títulos de sección;
   - lo nuevo va dentro de `<div class="revision" data-etiqueta="Revisión · …">` hasta que se apruebe;
   - punto decimal, espacio para los miles, todo en español; PI y PL en paralelo.
3. **Verificar:**
   - `python scripts/18_reporte_html.py` (desde la raíz) tiene que terminar sin errores;
   - extraer los `<script>` sin `src` del HTML y pasarlos por `node --check`;
   - abrir `reporte/reporte-fonce.html` en el navegador y mirar la sección cambiada, en tema claro y oscuro.
4. **Entregar:** el script y el HTML regenerado en el mismo commit, en una rama, con un pull request con
   descripción (reglas 20 y 21).

Plotly está copiado en `reporte/vendor/plotly-2.32.0.min.js` y el script lo mete dentro del HTML; no hay
que tocarlo. Si se cambia de versión, se actualiza el SHA-256 en el script y en `DATOS_FUENTES.md`.
