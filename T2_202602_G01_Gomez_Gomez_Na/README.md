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
- Procedencia de los datos y orden de ejecución.

Requisitos: `pip install -r codigo/requirements.txt`. Antes de armar el ZIP, `python codigo/verificar_entrega.py`
revisa nombre, estructura, nombres ASCII, rutas absolutas y credenciales. Cada archivo de `datos/` lleva su
`.meta.json` (fuente, versión, unidades, fecha de descarga, procesamiento); los que faltan los escribe
`python codigo/punto1/00_metadatos_datos.py`.

## `datos/punto1/`

Por ahora es una copia exacta de `../Analisis_De_Cuenca/data/`, los datos crudos de la Tarea 1 tal como se
descargaron (CAMELS-COL, DEM, ERA5-Land, pluviómetros del IDEAM, IMERG, MapBiomas, NOAA y SGC). Su procedencia,
licencias y SHA-256 están en `../Analisis_De_Cuenca/DATOS_FUENTES.md`. No se editan. Antes de entregar hay que
dejar solo lo que el punto 1 use de verdad, recortado a la cuenca y al período.

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
```

Toda la parte de diseño (05b, 05c, 05d, 05e) usa una sola cuenca: la del DEM (05a) con el C, el CN y el tc del Problema A.
