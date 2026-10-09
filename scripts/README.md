# Scripts del proyecto

Los scripts preparan todo lo que el informe (`reporte/reporte-fonce.html`) lee de `out/`, y el análisis del
informe vive en `18_calculos_informe.py`. El notebook `notebooks/02_precipitacion_vs_caudal.ipynb` quedó
congelado el 2026-10-07 y ya no se modifica. Están numerados **en el orden en que hay que correrlos**:
cada uno solo necesita lo que producen los anteriores.

**Para reproducir el análisis no hace falta correr ninguno.** Los productos de `out/` ya vienen en el
proyecto, y el informe se regenera directamente sobre ellos con `python scripts/18b_reporte_html.py`. Los scripts sirven para rehacer esos productos
desde los datos crudos de `data/` y para revisar cómo se obtuvo cada uno.

## Cómo se corren

Desde la **carpeta raíz del proyecto** (la que contiene `data/`, `out/` y `scripts/`):

```
python scripts/01_tabla_maestra_camels.py
python scripts/02_shp_cuencas_estaciones.py
...
```

Hay que correrlos desde la raíz porque algunos (01, 02, 04, 05, 08 y 17) usan rutas relativas como
`out/...` o `data/...`. Los demás calculan la raíz a partir de su propia ubicación y funcionan desde
cualquier carpeta, pero lo más seguro es correrlos todos desde la raíz.

Los paquetes están en `requirements.txt`, en la raíz.

## La tubería, en orden

| # | Script | Qué hace | Lee | Produce |
|---|---|---|---|---|
| 01 | `01_tabla_maestra_camels.py` | Une las tablas de atributos de CAMELS-COL en una sola | `data/camels_col/` | `out/camels_col_master.csv` |
| 02 | `02_shp_cuencas_estaciones.py` | Polígonos de San Gil y sus 5 subcuencas, su **área** (geodésica, la única del proyecto) y las estaciones del IDEAM dentro | `data/camels_col/`, `data/ideam/cne_ideam.csv` | `out/shp_fonce/` (incluye `areas_cuencas.csv`) |
| 03 | `03_recorte_dem.py` | Recorta el DEM ALOS PALSAR nacional a la zona de la cuenca ⚠️ | mosaico nacional (carpeta compartida) | `data/dem/dem_fonce_alos_12m.tif` |
| 04 | `04_imerg_descarga_mensual.py` | Descarga IMERG Final mensual sobre Colombia ⚠️ | internet (NASA GES DISC) | `data/imerg/` |
| 05 | `05_imerg_mensual_cuencas.py` | PI: IMERG mensual promediado sobre cada cuenca, ponderado por área | `data/imerg/`, polígonos de `data/camels_col/` | `out/imerg_mensual_fonce.csv` |
| 06 | `06_era5land_temperatura.py` | Temperatura diaria de ERA5-Land sobre la cuenca, y sus celdas; 1998-2022 para el informe y 1981-2022 aparte para tendencias ⚠️ | Google Earth Engine, `out/shp_fonce/` | `out/era5land_*.csv`, `data/era5land_gee/` |
| 06b | `06b_etp_hargreaves.py` | ETP diaria de Hargreaves con ERA5-Land y con MSWX (la fórmula que declara CAMELS-COL), junto a la ETP publicada | `out/` de 02 y 06, `data/camels_col/` | `out/etp_hargreaves_fonce.csv` |
| 07 | `07_pluviometros_dhime.py` | Pluviómetros del IDEAM (DHIME), serie mensual 1998-2022 y catálogo con quién cae dentro de la divisoria; además PL* (red fija desde 1981, solo para tendencias: `out/pluviometros_pl_larga_*.csv`, y la serie cruda `out/pluviometros_fonce_mensual_1981_2022.csv`) | `data/ideam/pluviometros/dhime/`, catálogo de estaciones del IDEAM en línea (público) | `out/pluviometros_fonce_*.csv`; la serie **depurada** (sin Encino 2016-2018) es la que usan todos los análisis |
| 07b | `07b_control_calidad_basico.py` | Control de calidad básico sobre los archivos crudos: fechas, duplicados, unidades, códigos de faltante, valores imposibles, banderas; qué es cada dato; los píxeles de IMERG del mes revisado a mano | `data/` (CAMELS-COL, DHIME, IMERG, ERA5-Land), `out/` de 01, 02, 05, 06b, 07 | `out/control_calidad_basico.csv`, `out/naturaleza_fuentes.csv`, `out/control_calidad_pi_mes_revisado.csv` |
| 07c | `07c_anomalias.py` | Anomalías: saltos (doble masa y Pettitt, por rondas), segundo corte de los pluviómetros marcados y PI contra PL sin los que lo tienen, secuencias constantes, picos aislados de Q, cobertura de PL, meses en 0 mm. De aquí salen las exclusiones con evidencia "4.3" de 07 | `out/` de 05, 06, 07, 16 | `out/anomalias_*.csv` (incluye `anomalias_segundo_corte.csv`) |
| 07d | `07d_trazabilidad.py` | Trazabilidad: el registro de anomalías, con lo que se comprobó, lo que se decidió, el efecto y el estado (corregido, incierto o descartado). No decide nada: reúne lo de los demás scripts y lee de sus salidas cada cifra | `out/` de 06b, 07, 07c, 13 y 16; Q diario de `data/camels_col/` | `out/registro_anomalias.csv` |
| 08 | `08_mapas_y_pixeles.py` | Mapas del DEM y de las celdas de IMERG y ERA5-Land; fracción de cada celda dentro de la cuenca | DEM, `out/` de 02, 06, 07 | `out/imerg_pixeles_fonce.csv`, `reporte/figuras/` |
| 09 | `09_gradiente_altitudinal.py` | ¿Llueve menos arriba? IMERG y pluviómetros contra la altitud | DEM, `out/` de 07, 08 | `out/gradiente_altitudinal_*.csv`, figura |
| 10 | `10_estaciones_subcuencas.py` | En qué subcuenca cae cada pluviómetro; mapa de las dos estaciones extremas | DEM, `out/` de 02, 05, 07 | `out/estaciones_subcuencas.csv`, figura |
| 11 | `11_correlacion_pluviometros_imerg.py` | Correlación mes a mes de cada pluviómetro contra su celda de IMERG | `out/` de 07, 10 | `out/correlacion_pluviometros_imerg.csv` |
| 12 | `12_gradiente_termico.py` | ¿Baja la temperatura de ERA5-Land con la altura como debería? | DEM, `out/` de 06 | `out/gradiente_termico_era5land.csv` |
| 13 | `13_morfometria.py` | Forma de la cuenca, cauce principal, perfil, hipsometría, pendientes, orientaciones, tiempos de concentración | DEM, `data/camels_col/`, `out/shp_fonce/` | `out/morfometria_fonce.csv` y otros de morfometría |
| 14 | `14_figuras_morfometria.py` | Figuras de la morfometría | `out/` de 13 | `reporte/figuras/` |
| 15 | `15_cauce_desde_dem.py` | Cauce principal derivado del DEM con pysheds, comparado con el de CAMELS-COL | DEM, `out/` de 13 | `out/comparacion_cauces.csv`, `out/perfil_cauce_dem.csv` |
| 16 | `16_correlaciones_variables.py` | Correlaciones entre PI, PL, Q, ETP y las dos temperaturas | `out/` de 02, 05, 06, 06b, 07 | `out/correlaciones_*.csv`, `out/variables_mensuales.csv` |
| 16b | `16b_modelos_lluvia_caudal.py` | Modelos para estimar Q a partir de la lluvia (PL y PI en paralelo), en mm/mes. Diagnóstico (forma, dispersión, residuos por mes, memoria y normalidad, en escala lineal y logarítmica) y cinco modelos: climatología, recta, recta con la lluvia del mes anterior y sus versiones en logaritmos; parámetros con Newey-West, BIC, partición 1998-2014 / 2015-2022 y validación cruzada con 5 bloques de 5 años; ficha del modelo elegido, M4 (ecuación, parámetros, rango de aplicación, supuestos y por qué se eligió) | `out/` de 02, 05, 07 y 16 | `out/modelos_diagnostico.csv`, `out/modelos_parametros.csv`, `out/modelos_ajuste.csv`, `out/modelos_evaluacion.csv`, `out/modelos_ficha.csv`, `out/modelos_estimados.csv` (los lee 18) |
| 17 | `17_oni_enso.py` | Descarga el Índice Oceánico El Niño (ONI) de la NOAA y marca cada mes como El Niño, La Niña o neutro (1998-2022 y, aparte, 1981-2022 para el registro largo) | internet (NOAA CPC), una sola vez; luego `data/noaa/` | `out/oni_mensual.csv` |
| 18 | `18_calculos_informe.py` | **El análisis del informe**: lee `out/` y `data/` y calcula todas las cifras, tablas y series que muestra el informe, por tema. Sin HTML. No se corre solo: lo corre 18b | casi todo `out/` | variables en memoria para 18b; `out/correlaciones_campos.nc` (con r, n, p-valores, q del FDR y la marca de robustez; lo dibuja 21), `out/correlaciones_campos_significancia.csv`, `out/correlaciones_campos_jackknife.csv` y `out/correlacion_nino34_indice.csv` (21 va después de 18 y antes de la versión final de 18b) |
| 18b | `18b_reporte_html.py` | **La página del informe**: corre 18, arma el HTML (texto, tablas, CSS y JavaScript de las gráficas) e incrusta las figuras y Plotly; el informe se edita en 18 y 18b, nunca en el HTML | lo que calcula 18, `reporte/figuras/`, `reporte/vendor/plotly-2.32.0.min.js` | `reporte/reporte-fonce.html` |
| 19 | `19_campos_climaticos.py` | **Campos climáticos del Punto 5**: baja ERSST v5 (SST) y ERA5 mensual (viento u y v, humedad específica y presión superficial a 850 hPa), enmascara 850 hPa bajo el terreno, remuestrea ERA5 a la malla de 2° de ERSST (promedio por bloques ponderado por área) y calcula el transporte de humedad q·u y q·v; 1998-2022 | internet (NOAA PSL y NCAR GDEX, sin cuenta), una sola vez; luego `data/noaa/ersst_v5/` y `data/era5_campos/` (fuera de git) | `out/campos_climaticos_2deg_1998_2022.nc` |
| 20 | `20_mapas_campos.py` | Mapas globales de los campos del Punto 5: SST media, humedad y transporte de humedad a 850 hPa, y el transporte de humedad de cada mes del calendario en la región de la cuenca. Tiene las funciones de mapa comunes (escala divergente de −1 a 1, cuenca marcada, máscaras en gris) para los mapas de correlación | `out/campos_climaticos_2deg_1998_2022.nc`, `out/shp_fonce/cuencas_fonce.shp` | `reporte/figuras/campos_*.png` |
| 21 | `21_mapas_correlacion.py` | Mapas de correlación de la cuenca (PL, Q y PI) con la SST, la rapidez del viento y la humedad a 850 hPa: 12 paneles por mes del calendario, escala común de −1 a 1, gris para lo inválido y para menos de 20 pares, n en cada panel, puntos en las cajas que sobreviven al FDR; ℓ = 0 y ℓ = 1 (SST), Spearman de Q contra la SST y un mapa con todos los meses juntos | `out/correlaciones_campos.nc` (lo escribe 18), `out/campos_climaticos_2deg_1998_2022.nc` | `reporte/figuras/corr_*.png` |

El informe (18 y 18b) no depende del notebook congelado, que también lee las salidas de 16.

## ⚠️ Los tres pasos que no se pueden rehacer sin acceso externo

Sus resultados ya vienen en `data/`, así que **no hace falta correrlos**. Para volver a hacerlos:

- **03 — recorte del DEM.** Necesita el mosaico nacional `Dem_Colombia-002.tif` (varios GB), que está en
  la carpeta compartida del equipo en Google Drive y no viaja con el proyecto. Es el único script que
  apunta fuera del proyecto (`G:/Shared drives/DEM_Colombia/`).
- **04 — descarga de IMERG.** Necesita **credenciales de NASA Earthdata** (cuenta gratuita) en un archivo
  netrc, y `curl` instalado. El aviso con los pasos está al comienzo del script; la ruta del netrc
  (`NETRC`) hay que cambiarla por la propia.
- **06 — ERA5-Land.** Necesita una cuenta de **Google Earth Engine** autenticada (`earthengine authenticate`)
  con un proyecto de Cloud habilitado.

La descarga de los pluviómetros (07) fue manual, desde el portal DHIME del IDEAM; el script procesa el
archivo descargado, que está en `data/ideam/pluviometros/dhime/`, y consulta la ubicación y altitud de
cada estación en el catálogo en línea del IDEAM (público, sin credenciales, pero necesita internet). Cómo se bajó cada fuente, con su
DOI, licencia y SHA-256, está en `DATOS_FUENTES.md`.

## `historico/`

Scripts que ya no forman parte de la tubería. Se conservan como registro de cómo se llegó hasta aquí;
**no hay que correrlos** y ninguno produce algo que use el notebook o el informe.

- **01–19 de la etapa de selección** (`02_screen.py` a `19_construir_informes.py`, más `10a_geometria.py`
  y `20_inventario_fonce.py`): tamizaje de las 346 cuencas de CAMELS-COL hasta elegir el Fonce, y los
  informes de esa etapa (`reporte/informe-fonce.html`, `reporte/criterios.html`). Algunos están en inglés
  porque son anteriores a la regla de "todo en español". `plantillas/` es de `19_construir_informes.py`.
- **`23_pluviometros_dhime.py`**: la primera descarga de pluviómetros (3 estaciones, 1981-2022),
  reemplazada por `07_pluviometros_dhime.py`.
- **`26_imerg_diario_fonce.py`**: IMERG diario sobre la cuenca. Se descargó pero ningún análisis lo usa.
- **`16b_punto2_json.py`**: exportaba los pares PI–PL, PL–Q y PI–Q y la evaluación fuera del período de
  ajuste para el visor del Punto 2 (`reporte/punto2_i.html`). El visor se integró al informe y se borró el
  2026-10-04 (regla 22); el informe calcula lo mismo en `18_calculos_informe.py`.
- **`27_era5land_temperatura.py`**: primer intento de bajar ERA5-Land por el Climate Data Store,
  abandonado porque la cola del servicio no avanzaba; se reemplazó por Earth Engine (06). **No correrlo**:
  escribe el mismo archivo de temperatura que usa el análisis.
