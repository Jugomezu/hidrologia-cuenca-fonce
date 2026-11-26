# Tarea 2 — Evapotranspiración y diseño (Hidrología, 202602)

Esta carpeta sigue la estructura obligatoria de la entrega y ya lleva el nombre que exige: el ZIP de la
entrega es esta carpeta comprimida entera, `T2_202602_G01_Gomez_Gomez_Na.zip`.

```
README.md
T2_202602_G01_informe.pdf        (pendiente)
T2_202602_G01_presentacion.pdf   (pendiente)
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
| `anexos/` | Resultados complementarios, comprobaciones y evidencia del uso de IA. |

## Pendiente para la entrega

- Integrantes con su nombre completo.
- Procedencia de los datos.

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
`00_metadatos_datos.py` solo escribe los `.meta.json` que falten.

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

Probado el 2026-11-23 en una copia limpia, con `productos/punto1/` vacío salvo `terraclimate_mensual_cuenca.csv`:
los 24 scripts (del 02 al 29) corren en este orden y reproducen los productos guardados (solo cambian cifras en el 4.º decimal).
El script 23 compara además con la Tarea 1 si encuentra `../Analisis_De_Cuenca/`; sin esa carpeta corre igual.

## `datos/punto1/`

Por ahora es una copia exacta de `../Analisis_De_Cuenca/data/`, los datos crudos de la Tarea 1 tal como se
descargaron (CAMELS-COL, DEM, ERA5-Land, pluviómetros del IDEAM, IMERG, MapBiomas, NOAA y SGC). Su procedencia,
licencias y SHA-256 están en `../Analisis_De_Cuenca/DATOS_FUENTES.md`. No se editan. Antes de entregar hay que
dejar solo lo que el punto 1 use de verdad, recortado a la cuenca y al período.
