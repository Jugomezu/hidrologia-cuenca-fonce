# Tarea 2 — Evapotranspiración y diseño (Hidrología, 202602)

Esta carpeta sigue la estructura obligatoria de la entrega y ya lleva el nombre que exige: el ZIP de la
entrega es esta carpeta comprimida entera, `T2_202602_G01_Gomez_Gomez_Na.zip`.

Integrantes: Juan Pablo Gómez y Andrea Gómez. El grupo tiene solo dos integrantes. «Na» en el nombre de la carpeta
y del ZIP no es una persona, sino un relleno: la expresión regular del enunciado,
`^T2_202602_G[0-9]{2}(_[A-Z][A-Za-z]+){3}\.zip$`, exige exactamente tres apellidos.

```
README.md
T2_202602_G01_informe.pdf        (pendiente)
T2_202602_G01_presentacion.pdf
codigo/     punto1/  punto2/
datos/      punto1/  punto2/
productos/  punto1/  punto2/
anexos/
```

| Carpeta | Contenido |
|---|---|
| `codigo/` | Scripts que reproducen el procesamiento, las tablas y las figuras de cada punto. |
| `datos/` | Archivos de entrada efectivamente usados, recortados a la cuenca y al período. |
| `productos/` | Series mensuales y anuales procesadas, tablas y figuras del informe. |
| `anexos/` | Resultados complementarios, comprobaciones y evidencia del uso de IA. `anexos/presentacion/` arma la presentación: `python anexos/presentacion/construir_presentacion.py` y luego `node anexos/presentacion/exportar_pdf.js` (Playwright) escriben el HTML y el PDF de la raíz. |

Requisitos: `pip install -r codigo/requirements.txt`. Antes de armar el ZIP, `python codigo/verificar_entrega.py`
revisa nombre, estructura, nombres ASCII, rutas absolutas y credenciales. Cada archivo de `datos/` lleva su
`.meta.json` (fuente, versión, unidades, fecha de descarga, procesamiento); los que faltan los escribe
`python codigo/punto1/00_metadatos_datos.py`.

## Orden de ejecución (punto 1)

Todo se corre desde esta carpeta (la raíz de la entrega), por ejemplo `python codigo/punto1/04_eto_fao56.py`.
Cada script lee de `datos/punto1/` y de lo que escribieron los anteriores en `productos/punto1/` y `anexos/punto1/`.

**Descargas (no hace falta correrlas).** 01 (también con `--extension_1981`), 05, 06, 07, 08, 09, 10, 11, 19 y 38 bajan los datos y piden cuenta y clave
propias (CDS, Earth Engine, SFTP de GLEAM). Sus resultados ya vienen en `datos/punto1/`. El 05 además deja
`productos/punto1/terraclimate_mensual_cuenca.csv`, que leen los scripts 14, 16 y 17: ese archivo va en la entrega.
`00_metadatos_datos.py` solo escribe los `.meta.json` que falten; `00b_recorte_datos_tarea1.py` recorta a la cuenca las divisorias de CAMELS-COL y el IMERG de Colombia (ya está hecho).

**Cálculo, en este orden:**

| Paso | Scripts | Qué hace |
|---|---|---|
| ETo de referencia | 02, 03, 04 | Series mensuales y diarias de los 6 puntos, Rn y ETo Penman–Monteith (FAO-56) |
| Comprobaciones de la ETo | 04b, 04c, 04d, 04e | Medias mensuales y alturas, día a mano, error de ECMWF de 2022, figuras |
| Productos de ET real y balance | 14, 15 | ET real de cada producto y balance P − Q |
| Pruebas de la referencia | 16, 20, 12, 13, 17, 18 | TerraClimate, celdas de las estaciones, Rs y ETo de estación, dispersión, mes a mano |
| Otros métodos | 22, 21, 23, 25 | Thornthwaite, los demás métodos, Hargreaves de la Tarea 1, mes a mano |
| Diferencias entre métodos | 26, 27, 28 | Términos de la ETo, α* y sensibilidad |
| ET real y Budyko | 24, 29 | ET real por varios caminos y espacio de Budyko |
| Energía o agua, por mes | 30, 31 | Régimen mensual y fracción evaporativa |
| HR de las estaciones | 41 | HR media de 5 estaciones del IDEAM (cifra del texto de Hargreaves) |
| Cambios en la demanda | 32, 33 | Tendencias 1998–2022 y atribución; diagnóstico del tanque de Mogotes-AUT |
| Cambios en la demanda, 1981–2022 | 42, 36 | Control de calidad del registro largo; tendencias con la Rs corregida antes de 2001 |
| Paisaje de la cuenca | 34, 37, 39 | Gradiente altitudinal y reparto de energía; resistencia de superficie; Jarvis con LAI |
| Mapa de la cuenca | 43 | DEM con sombreado, estaciones del IDEAM, puntos de ERA5-Land y aforo (figura 1 del informe) |
| Déficit climático y frecuencia (no va en el informe) | 40 | Usa las funciones de `codigo/punto2/02_extremos_y_distribuciones.py` |
| Figuras y tablas del informe | 35 | Figuras fijas de métodos, sensibilidad y ET real; tablas y cifras en LaTeX (`productos/punto1/tablas_informe/`). Va después de 21–32 |

Probado el 2026-11-23 en una copia limpia, con `productos/punto1/` vacío salvo `terraclimate_mensual_cuenca.csv`:
los 24 scripts (del 02 al 29) corren en este orden y reproducen los productos guardados (solo cambian cifras en el 4.º decimal).
El script 23 compara además con la Tarea 1 si encuentra `../Analisis_De_Cuenca/`; sin esa carpeta corre igual.

## Informe

`anexos/informe_latex/informe.tex` (con `referencias.bib`). Después del script 35 del punto 1 y del 06 del punto 2,
desde esa carpeta:
`latexmk -pdf informe.tex`, y se copia `informe.pdf` a la raíz como `T2_202602_G01_informe.pdf`.

## `datos/punto1/`

Solo los archivos que lee el código del punto 1, recortados a la cuenca del Fonce en San Gil (IDEAM 24027010) y al
periodo analizado. Cada archivo lleva su `.meta.json` (fuente, versión, unidades, fecha de descarga y procesamiento).

| Carpeta | Fuente |
|---|---|
| `camels_col/` | CAMELS-COL (Jimenez et al., 2026), doi:10.5281/zenodo.18794895: Q diario de San Gil y su divisoria |
| `dem/` | DEM ALOS PALSAR 12.5 m (Alaska Satellite Facility), recortado a la cuenca |
| `era5land_puntos/`, `era5land_puntos_balance/`, `era5land_celdas_estaciones/` | ERA5-Land horario (CDS, reanalysis-era5-land-timeseries) en los 6 puntos y en las celdas de 3 estaciones |
| `era5land_mensual_balance/`, `era5land_gee/` | ERA5-Land mensual (CDS) y diario de temperatura (Google Earth Engine) |
| `imerg/` | NASA GPM IMERG V07 mensual, doi:10.5067/GPM/IMERG/3B-MONTH/07 |
| `ideam/`, `ideam_estaciones/`, `ideam_brillo_solar/` | IDEAM: catálogo de estaciones y descargas de DHIME (pluviómetros, T, HR, viento, tanque, brillo solar) |
| `gleam_v4/`, `mod16a2gf/`, `ssebop/`, `ssebop_v5/`, `terraclimate/`, `mcd15a3h/` | Productos de ET real, demanda y LAI (ver `anexos/referencias.md`) |
| `mapbiomas/` | MapBiomas Colombia, colección 3, coberturas 2022 |

El 2026-11-27 se quitó lo que ningún script lee: el resto de CAMELS-COL (todas las cuencas del país), las series de
IMERG por mes, el mapa geológico del SGC, los índices ONI y TNA de NOAA, ERA5-Land de GEE de 1981–1997 y los
pluviómetros de 1981. Las dos bases nacionales que sí se leen (divisorias de CAMELS-COL e IMERG de Colombia) las
recorta `codigo/punto1/00b_recorte_datos_tarea1.py`.

`temp/` es la carpeta de trabajo (documento de trabajo, plan, textos de Juan). Se queda en el repositorio, pero no va
en el ZIP.

## Punto 2: orden de ejecución

Desde esta carpeta (`T2_202602_G01_Gomez_Gomez_Na/`):

```bash
python codigo/punto2/01_descarga_y_calidad.py        # control de calidad de la lluvia horaria (GHCNh, Denver Stapleton)
python codigo/punto2/02_extremos_y_distribuciones.py # máximos anuales, distribuciones, bootstrap (~5 min)
python codigo/punto2/03_curvas_idf.py                # curvas IDF
python codigo/punto2/05a_dem_y_validacion_idf.py     # microcuenca con el DEM y comparación con NOAA Atlas 14 (requiere internet)
python codigo/punto2/05b_problemaA_alcantarilla.py   # Problema A: área/L/S0 del DEM, C, CN y tc adoptados
python codigo/punto2/05c_problemaB_tanque_detencion.py
python codigo/punto2/05d_bonificaciones_punto2.py    # lee la cuenca y la obra del Problema A
python codigo/punto2/05e_hidrogramas_nrcs.py         # antes 04; misma cuenca y parámetros del Problema A
python codigo/punto2/00_generar_html.py              # informe HTML del punto 2
python codigo/punto2/06_cifras_informe.py             # cifras del punto 2 que cita el informe LaTeX
```

Toda la parte de diseño (05b, 05c, 05d, 05e) usa una sola cuenca: la del DEM (05a) con el C, el CN y el tc del Problema A.
