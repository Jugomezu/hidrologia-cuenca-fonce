# Inventario de lo que se reusa de la Tarea 1

Cuenca del río Fonce hasta la estación San Gil (IDEAM 24027010). La Tarea 1 está en `../Analisis_De_Cuenca/` del
repositorio; aquí se dice qué se toma de ella y de qué archivo sale cada cifra. No se copia nada a mano: las cifras
están tal como las escribió su script.

## Cuenca y relieve

| Magnitud | Valor | Archivo de la Tarea 1 | Script |
|---|---|---|---|
| Área (polígono de CAMELS-COL, geodésica) | 2 098.85 km² | `out/shp_fonce/areas_cuencas.csv` | `02_shp_cuencas_estaciones.py` |
| Perímetro | 338.5 km | `out/morfometria_fonce.csv` | `13_morfometria.py` |
| Altura mínima, media y máxima (DEM ALOS 12 m) | 1 114, 2 265 y 4 297 m | `out/morfometria_fonce.csv` | `13_morfometria.py` |

CAMELS-COL publica 2 124 km² (1.2 % más que su propio polígono). La Tarea 1 decidió usar 2 098.85 km²; la Tarea 2
usa la misma área para pasar caudal a lámina.

## Cauce principal (lo usa el punto 2)

La Tarea 1 midió el cauce de dos formas. La oficial de su informe es la red de CAMELS-COL; la otra es un trazado
propio desde el DEM (D8 a 50 m), hecho para comprobar la primera.

| Magnitud | Red de CAMELS-COL (oficial) | Trazado desde el DEM | CAMELS-COL publica |
|---|---|---|---|
| Longitud del cauce principal | 90.76 km | 95.03 km | 99.12 km |
| Desnivel del cauce | 2 046 m | 2 776 m | — |
| Pendiente media (desnivel / longitud) | 0.0225 m/m | 0.0292 m/m | — |
| Pendiente de Taylor-Schwarz | 0.0192 m/m | 0.0450 m/m | 4.45e-05 (no es m/m: unidad sin aclarar) |

Fuentes: `out/morfometria_fonce.csv` (`13_morfometria.py`) y `out/comparacion_cauces.csv`
(`15_cauce_desde_dem.py`). Trazados: `out/shp_fonce/cauce_principal.shp` y `out/shp_fonce/cauce_dem.shp`.
Las dos versiones difieren poco en longitud (4.7 %) y mucho en desnivel, porque el trazado del DEM nace a 3 894 m y el
de CAMELS-COL a 3 165 m (`out/perfil_cauce_dem.csv`, `out/perfil_cauce_fonce.csv`). Quien use la pendiente en el punto 2 debe decir cuál toma.

## Series mensuales 1998–2022

`out/variables_mensuales.csv` (`16_correlaciones_variables.py`): 262 meses con todas las variables a la vez.

| Columna | Qué es | Unidades |
|---|---|---|
| `PI` | Precipitación de IMERG, promedio sobre la cuenca ponderado por área de celda | mm/mes |
| `PL` | Precipitación de la red de pluviómetros del IDEAM dentro de la divisoria (7), serie depurada | mm/mes |
| `Q` | Caudal en San Gil como lámina sobre 2 098.85 km² | mm/mes |
| `ETP` | Hargreaves con ERA5-Land, calculada en la Tarea 1 | mm/mes |
| `T ERA5`, `T MSWX` | Temperatura media de la cuenca | °C |

De diario a mensual la Tarea 1 dejó vacío todo mes con 5 o más días faltantes. La Tarea 2 la usa para el balance
P − Q y para comparar la ETo de FAO-56 con la ETP de Hargreaves.

## Datos crudos

`datos/punto1/` es hoy una copia de `../Analisis_De_Cuenca/data/` (CAMELS-COL, DEM ALOS, ERA5-Land de GEE,
pluviómetros del IDEAM, IMERG, MapBiomas, NOAA, SGC). Procedencia, licencias y SHA-256 en
`../Analisis_De_Cuenca/DATOS_FUENTES.md`. Antes de entregar se deja solo lo que el punto 1 use, recortado a la
cuenca y al período.

## Lo que no se reusa

Las tendencias de la Tarea 1 empiezan en 1981; la ETo de la Tarea 2 cubre 1998–2022 (decisión del 2026-11-17), así
que sus tendencias no se comparan directamente.
