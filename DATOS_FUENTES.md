# Procedencia de los datos

Proyecto: **Analisis de cuenca — Hidrologia, Tarea 1**  

Generado automaticamente por `scripts/historico/11_metadatos_fuentes.py` el 2026-09-18.

Los DOI y versiones se verificaron contra la fuente autoritativa (API de Zenodo, NASA CMR, API de Socrata) en esa fecha.


## Resumen

| Fuente | DOI / ID | Licencia | Estado |
|---|---|---|---|
| CAMELS-COL: A Large-Sample Hydrometeorological Dataset for | `10.5281/zenodo.18794895` | CC-BY-4.0 | descargado |
| CAMELS-COL: A Large-Sample Hydrometeorological Dataset for | `10.5194/essd-2025-200` | CC-BY-4.0 | descargado |
| Catalogo Nacional de Estaciones del IDEAM | `(sin DOI) - identificador Socrata: hp9r-jxuu` | Datos Abiertos de Colombia ( | descargado |
| GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 de | `10.5067/GPM/IMERGDF/DAY/07` | Dominio publico (NASA Earth  | PENDIENTE |
| GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1  | `10.5067/GPM/IMERG/3B-MONTH/07` | Dominio publico (NASA Earth  | descargado |
| CHIRPS v2.0 - Climate Hazards Group InfraRed Precipitation | `10.15780/G2RP4Q` | Dominio publico (Creative Co | descargado |
| MSWX - Multi-Source Weather | `10.1175/BAMS-D-21-0145.1` | CC-BY-4.0 (requiere registro | descargado |
| ERA5-Land: temperatura 2 m, agregados diarios (0.1 grados; se prefirio sobre ERA5 por resolucion) | `10.24381/cds.e2161bac` | Licencia Copernicus para pro | 2026-09-24, via Google Earth Engine |
| DEM ALOS PALSAR 12.5 m (recorte de la zona) | sin DOI registrado (ver seccion) | sin registrar (ver seccion) | recorte en `data/dem/`, 2026-09-27 |
| Copernicus DEM GLO-90 (relieve del mapa de ubicacion) | no verificado (ver seccion) | no verificada (ver seccion) | 2026-10-09, copia publica en Amazon S3 |
| Natural Earth 1:10 m, limites de paises y departamentos (v5.1.1) | sin DOI | no verificada (ver seccion) | 2026-10-09, copia oficial en Amazon S3 |
| Mapa Geologico de Colombia 2023, escala 1:1 500 000 (SGC) | sin DOI | no verificada (ver seccion) | 2026-10-09, sitio del SGC |
| MapBiomas Colombia coleccion 3, cobertura 2022 | sin DOI | publica con cita de la fuente (ver seccion) | 2026-10-09, copia publica en Google Cloud Storage |

---


## CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia

- **Autores:** Jimenez, David A.; Meneses, Julian E.; Solha, Pedro H. Bernardes; Avila Diaz, Alvaro; Quesada, Benjamin; Brentan, Bruno Melo; Rodrigues, Andre Ferreira
- **DOI:** `10.5281/zenodo.18794895`
- **DOI de concepto:** `10.5281/zenodo.14947146  (siempre apunta a la version mas reciente)`
- **Version:** publicada 2026-02-26 (3a version del registro)
- **Editor / archivo:** Zenodo
- **Licencia:** CC-BY-4.0
- **Cobertura:** 346 cuencas de Colombia; series diarias 1981-01-01 a 2022-12-31; 71 atributos por cuenca
- **Fecha de acceso:** 2026-09-18
- **Destino local:** `data/camels_col/`

**Metodo de descarga**

```
API REST de Zenodo, descarga anonima (sin credenciales):
    curl -L 'https://zenodo.org/api/records/18794895/files/<ARCHIVO>/content' -o <ARCHIVO>
  Listado de versiones:  https://zenodo.org/api/records/15554735/versions
  NOTA: las versiones anteriores (15554735, 14947147) tienen los archivos
  restringidos; solo la de 2026-02-26 es de acceso abierto.
```

**Cita recomendada**

> Jimenez, D. A., Meneses, J. E., Solha, P. H. B., Avila Diaz, A., Quesada, B., Brentan, B. M., & Rodrigues, A. F. (2026). CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia [Data set]. Zenodo. https://doi.org/10.5281/zenodo.18794895


## CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia (preprint de discusion, Earth System Science Data)

- **Autores:** Jimenez, D. A., et al.
- **DOI:** `10.5194/essd-2025-200`
- **Version:** preprint, discusion abierta 2025-06-23
- **Editor / archivo:** Copernicus / Earth System Science Data Discussions
- **Licencia:** CC-BY-4.0
- **Cobertura:** Documento metodologico que acompania al dataset
- **Fecha de acceso:** 2026-09-18
- **Destino local:** `data/camels_col/essd-2025-200.pdf` (38 paginas, descargado el 2026-09-28, SHA-256 `01ce6cdab87516f31a5240c223a5aa972ddda1a5416435beb583d697688e5ece`)

**Metodo de descarga**

```
Descarga directa del PDF, anonima:
    https://essd.copernicus.org/preprints/essd-2025-200/essd-2025-200.pdf
```

**Cita recomendada**

> Jimenez, D. A., et al. (2025). CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia. Earth Syst. Sci. Data Discuss. https://doi.org/10.5194/essd-2025-200


## Catalogo Nacional de Estaciones del IDEAM

- **Autores:** Instituto de Hidrologia, Meteorologia y Estudios Ambientales (IDEAM)
- **DOI:** `(sin DOI) - identificador Socrata: hp9r-jxuu`
- **Version:** instantanea descargada el 2026-09-18
- **Editor / archivo:** datos.gov.co
- **Licencia:** Datos Abiertos de Colombia (uso libre con atribucion)
- **Cobertura:** 29.538 estaciones; nombre, corriente, categoria, estado, municipio, coordenadas, area/zona/subzona hidrografica
- **Fecha de acceso:** 2026-09-18
- **Destino local:** `data/ideam/cne_ideam.csv`

**Metodo de descarga**

```
API Socrata (SODA), descarga anonima:
    curl -L 'https://www.datos.gov.co/resource/hp9r-jxuu.csv?$limit=60000' \
         -o data/ideam/cne_ideam.csv
  Metadatos del recurso:  https://www.datos.gov.co/api/views/hp9r-jxuu.json
```

**Cita recomendada**

> IDEAM. Catalogo Nacional de Estaciones del IDEAM. Portal de Datos Abiertos de Colombia, conjunto hp9r-jxuu. Consultado el 2026-09-18.


## GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07 (GPM_3IMERGDF)

- **Autores:** Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., Tan, J.
- **DOI:** `10.5067/GPM/IMERGDF/DAY/07`
- **Version:** V07 (V07B en los granulos)
- **Editor / archivo:** NASA GES DISC (Goddard Earth Sciences Data and Information Services Center)
- **Licencia:** Dominio publico (NASA Earth Science Data); requiere registro Earthdata
- **Cobertura:** Global 90S-90N, 0.1 grados (~11 km, ~123 km2/pixel); diario; 1998-01-01 a 2025-09-30
- **Fecha de acceso:** 2026-09-18
- **Destino local:** `data/imerg/diario/  (pendiente)`

**Metodo de descarga**

```
OPeNDAP sobre HTTPS con autenticacion NASA Earthdata (URS OAuth).
  REQUIERE: (a) cuenta en https://urs.earthdata.nasa.gov
            (b) autorizar la aplicacion 'NASA GESDISC DATA ARCHIVE'
            (c) credenciales en un archivo netrc (NO versionar)
  En esta maquina el archivo es  C:/Users/juanp/_netrc.txt  y se pasa
  explicitamente porque curl solo busca '_netrc' sin extension:
    curl --netrc-file C:/Users/juanp/_netrc.txt -L -c ck -b ck \
      'https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.07/<AAAA>/<MM>/3B-DAY.MS.MRG.3IMERG.<AAAAMMDD>-S000000-E235959.V07B.nc4.ascii?precipitation[0:0][<i0>:<i1>][<j0>:<j1>]'
  Indexado de la grilla (verificado empiricamente):
    lon = -179.95 + 0.1*i   (i = 0..3599)
    lat =  -89.95 + 0.1*j   (j = 0..1799)
    orden de dimensiones: precipitation[time][lon][lat]
  NOTA: el servicio 'Data Rods for Hydrology' (hydro1.gesdisc) devuelve
  HTML en vez de datos con estas credenciales; se usa OPeNDAP.
```

**Cita recomendada**

> Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., & Tan, J. (2023). GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07. Greenbelt, MD: GES DISC. https://doi.org/10.5067/GPM/IMERGDF/DAY/07


## GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07 (GPM_3IMERGM)

- **Autores:** Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., Tan, J.
- **DOI:** `10.5067/GPM/IMERG/3B-MONTH/07`
- **Version:** V07 (V07B en los granulos)
- **Editor / archivo:** NASA GES DISC
- **Licencia:** Dominio publico (NASA Earth Science Data); requiere registro Earthdata
- **Cobertura:** Recorte Colombia: lon -79.55 a -66.35, lat -4.65 a 13.75 (0.1 grados); mensual 1998-01 a 2022-12 (300 meses). Unidades originales mm/h, convertidas a mm/mes multiplicando por las horas del mes
- **Fecha de acceso:** 2026-09-18
- **Destino local:** `data/imerg/  (crudo en mensual/AAAAMM.txt; empaquetado en imerg_mensual_col.npz)`

**Metodo de descarga**

```
OPeNDAP (ascii) sobre HTTPS con autenticacion NASA Earthdata:
    curl --netrc-file C:/Users/juanp/_netrc.txt -L -c ck -b ck \
      'https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07/<AAAA>/3B-MO.MS.MRG.3IMERG.<AAAA><MM>01-S000000-E235959.<MM>.V07B.HDF5.ascii?precipitation[0:0][1004:1136][853:1037]'
  Variable: /Grid/precipitation (mm/h), relleno -9999.9 -> NaN.
  6 descargas simultaneas, reanudable.
```

**Cita recomendada**

> Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., & Tan, J. (2023). GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07. Greenbelt, MD: GES DISC. https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07


## CHIRPS v2.0 - Climate Hazards Group InfraRed Precipitation with Station data

- **Autores:** Funk, C., et al.
- **DOI:** `10.15780/G2RP4Q`
- **Version:** v2.0
- **Editor / archivo:** Climate Hazards Center, UC Santa Barbara / USGS
- **Licencia:** Dominio publico (Creative Commons CC0)
- **Cobertura:** 50S-50N, 0.05 grados, diario, 1981-presente
- **Fecha de acceso:** 2026-09-18
- **Destino local:** `data/camels_col/hydromet/ (columna pr)`

**Metodo de descarga**

```
NO descargado directamente. Llega ya agregado por cuenca dentro de CAMELS-COL (columna 'pr' de 04_CAMELS_COL_Hydrometeorological_data).
  Fuente original: https://data.chc.ucsb.edu/products/CHIRPS-2.0/
```

> **Actualizacion 2026-09-24:** ademas de lo que llega dentro de CAMELS-COL, la grilla **mensual**
> de CHIRPS se descargo directamente de la fuente. Ver la seccion
> "CHIRPS v2.0 mensual (grilla de 0.05 grados) descargada directamente" mas abajo.

**Cita recomendada**

> Funk, C., et al. (2015). The climate hazards infrared precipitation with stations. Scientific Data, 2, 150066. https://doi.org/10.1038/sdata.2015.66


## MSWX - Multi-Source Weather (temperatura y variables meteorologicas)

- **Autores:** Beck, H. E., et al.
- **DOI:** `10.1175/BAMS-D-21-0145.1`
- **Version:** MSWX-Past
- **Editor / archivo:** GloH2O
- **Licencia:** CC-BY-4.0 (requiere registro en GloH2O)
- **Cobertura:** Global, 0.1 grados, 3-horario, 1979-presente
- **Fecha de acceso:** 2026-09-18
- **Destino local:** `data/camels_col/hydromet/ (columnas tmax, tmin, etp)`

**Metodo de descarga**

```
NO descargado directamente. Llega ya agregado por cuenca dentro de CAMELS-COL (columnas t_max, t_min y poten_evapo).
  Fuente original: https://www.gloh2o.org/mswx/
```

**Cita recomendada**

> Beck, H. E., et al. (2022). MSWX: Global 3-hourly 0.1 deg bias-corrected meteorological data. Bull. Amer. Meteor. Soc. https://doi.org/10.1175/BAMS-D-21-0145.1

### Decision vigente: la temperatura del proyecto es ERA5-Land (decidido el 2026-09-27)

Se cambio la decision del 2026-09-25 (abajo, conservada como historial). El proyecto usa **ERA5-Land**
como temperatura de la cuenca, por tres razones:

- **Trae la media diaria verdadera** (promedio de las 24 horas). CAMELS-COL solo publica la minima y la
  maxima de MSWX, y la media hay que aproximarla con el punto medio (min + max) / 2, que sobreestima la
  media real porque la temperatura pasa mas horas cerca de la minima. El tamano de ese sesgo se mide
  dentro de ERA5-Land (que trae las dos cosas) en `scripts/18_calculos_informe.py` (`t_sesgo_metodo`) y en
  la seccion 1.5 del notebook.
- **No tiene huecos:** 9 131 dias, los 300 meses del periodo. MSWX dentro de CAMELS-COL hereda los huecos
  del caudal (8 601 dias).
- **Se tiene la malla:** se promedia sobre la divisoria ponderando por area, igual que IMERG.

Lo que se pierde, y hay que declararlo: MSWX esta corregido de sesgo contra estaciones y ERA5-Land no, y
ERA5-Land suaviza el relieve (-4.23 C/km con las 29 celdas que tocan la cuenca ponderadas por area
dentro, frente a ~-6.5 esperable). Sin termometros en la cuenca no se
puede arbitrar cual acierta. MSWX se conserva para repetir calculos con la otra fuente.

### (Reemplazada) Por que se usaba MSWX y no ERA5-Land para la temperatura (decidido el 2026-09-25)

El proyecto tiene dos fuentes de temperatura y usa **MSWX**. El criterio es que **MSWX esta corregido de
sesgo contra observaciones de estaciones en superficie y ERA5-Land no**: ERA5-Land es el reanalisis
crudo. En una cuenca que **no tiene ni una sola estacion que mida temperatura** (las 7 del IDEAM dentro
de la divisoria son pluviometricas), conviene el producto que ya trae incorporado el contraste con
observaciones.

**El criterio NO es la resolucion espacial.** Los dos productos estan en malla de **0,1 grados**, asi que
por resolucion no se distinguen. (La resolucion si fue el criterio para preferir ERA5-Land sobre ERA5, que
esta a 0,25 grados; eso se documenta mas abajo y es una decision distinta.)

**Lo que se comparo** (8 601 dias con las dos fuentes, `scripts/18_calculos_informe.py`):

| | MSWX | ERA5-Land |
|---|---|---|
| Naturaleza | rean. corregido contra observaciones | reanalisis crudo |
| Resolucion | 0,1 grados | 0,1 grados |
| Dias con dato (1998-2022) | 8 601 | **9 131, sin un hueco** |
| Variables en el proyecto | minima y maxima | media, minima y maxima |
| T media del periodo | **16,87 C** | 14,68 C |
| Amplitud diaria media | 8,62 C | 9,78 C |
| Malla disponible | no (llega promediada por cuenca) | si, 29 celdas |

- MSWX es **2,19 C mas calido**. La separacion es casi constante en toda la distribucion: +1,92 C en el
  percentil 5 y +2,24 C en el percentil 95. Correlacion diaria r = 0,79.
- CAMELS-COL solo trae `t_min` y `t_max` de MSWX; la media diaria se calcula como (min + max) / 2.

**Comprobacion indirecta que apoya la eleccion:** cruzando las 21 celdas de ERA5-Land que caen dentro de
la cuenca contra la altitud del DEM (`scripts/12_gradiente_termico.py`), su temperatura baja
**-4,31 C por cada 1 000 m** (r2 = 0,96), cuando en aire humedo lo esperable ronda **-6,5 C/km**.
ERA5-Land **suaviza el relieve** y deja las partes altas mas templadas de lo que deberian estar. Es un
defecto conocido de los reanalisis en terreno quebrado, y es lo que el paso de correccion de MSWX busca
arreglar. **A MSWX no se le puede hacer esta prueba**, porque de el no tenemos la malla.

**Limitacion que hay que declarar:** sin ninguna observacion de temperatura dentro de la cuenca, **no hay
forma de saber cual de las dos acierta**. La eleccion se apoya en como esta construido cada producto, no
en una verificacion local. Los 2,19 C de diferencia se arrastran a todo lo que dependa de la temperatura,
empezando por la evapotranspiracion.

**ERA5-Land no se descarta:** se conserva descargado y procesado. Cubre 9 131 dias sin un solo hueco
frente a los 8 601 de MSWX (que hereda los huecos del caudal de CAMELS-COL), sirve para rellenar los
meses que CAMELS-COL pierde y para repetir cualquier calculo con la otra fuente.


## ERA5-Land: temperatura del aire a 2 m (agregados diarios)

- **Producto:** ERA5-Land Daily Aggregated - ECMWF Climate Reanalysis
  (identificador en el catalogo de Earth Engine: `ECMWF/ERA5_LAND/DAILY_AGGR`). Es el agregado diario
  de ERA5-Land horario.
- **Autores:** Munoz-Sabater, J., et al.
- **DOI (ERA5-Land horario, del que se deriva el diario):** `10.24381/cds.e2161bac`
  Verificado contra el registro del DOI el 2026-09-23. Los productos diarios derivados no tienen DOI
  propio que resuelva, asi que se cita el del dataset de origen.
- **Version:** ERA5-Land (reanalisis), agregado diario
- **Editor / archivo:** Copernicus Climate Change Service (C3S) / ECMWF; servido por Google Earth Engine
- **Licencia:** Licencia Copernicus para productos C3S (uso libre con atribucion)
- **Cobertura:** global terrestre, malla de 0.1 grados (resolucion nativa ~9 km, ~11 132 m)
- **Bandas usadas:** `temperature_2m` (media diaria), `temperature_2m_min` (minima diaria),
  `temperature_2m_max` (maxima diaria)
- **Periodo descargado:** 1998-01-01 a 2022-12-31, el periodo de estudio del proyecto (acceso
  2026-09-24); **ampliado a 1981-01-01 el 2026-10-07** para las tendencias de largo plazo (regla 6),
  con el mismo script, coleccion, bandas y poligono
- **Region:** el poligono de la cuenca de San Gil (24027010), no un recorte rectangular
- **Unidades:** la coleccion entrega kelvin; el script convierte a grados Celsius
- **Fecha de acceso:** 2026-09-24 (1998-2022) y 2026-10-07 (1981-1997)
- **Destino local:** `data/era5land_gee/t2m_<anio>.csv` (crudo, 42 archivos),
  `out/era5land_temperatura_diaria_fonce.csv` (serie de la cuenca, 1998-2022; la que lee el informe) y
  `out/era5land_temperatura_diaria_fonce_1981_2022.csv` (registro largo, solo para tendencias)
- **SHA-256 de `out/era5land_temperatura_diaria_fonce.csv`:**
  `99e9dd241a3cf14d089012f50d23f8971240c146b2a9b4dea642c8524238cb50` (sin cambios tras la ampliacion)
- **SHA-256 de `out/era5land_temperatura_diaria_fonce_1981_2022.csv`:**
  `538d364ecb832fd9e7030b1a4ac2511d0df8892a4a081ac383a0d3efbf6360f8`
- **Contenido verificado:** 9 131 dias, 1998-01-01 a 2022-12-31, **cero dias faltantes**, cero nulos;
  se cumple `t_min <= t_media <= t_max` en los 9 131 dias. El registro largo: 15 340 dias, 1981-01-01 a
  2022-12-31, cero faltantes, cero nulos, la misma desigualdad en todos los dias y ninguna racha de 5 o mas
  dias con el mismo valor.

**Por que ERA5-Land y no ERA5**

```
El criterio fue la RESOLUCION ESPACIAL.
  ERA5      : malla de 0.25 grados, unos 31 km de lado (~880 km2 por celda)
  ERA5-Land : malla de 0.10 grados, unos  9 km de lado  (~90 km2 por celda)
La cuenca de San Gil mide unos 2 100 km2: con ERA5 la cubririan dos o tres celdas y con
ERA5-Land unas veinte. En una cuenca de montana que va de 1 114 a 4 295 m eso importa,
porque la temperatura cambia con la altura y una malla gruesa mezcla el valle con el
paramo antes de que uno pueda separarlos.
```

**Por que por Earth Engine y no por el Climate Data Store**

```
Se intento primero por el CDS (scripts/historico/27_era5land_temperatura.py, producto
'derived-era5-land-daily-statistics') y no fue viable por congestion del servidor.
El 2026-09-24, la cola del CDS reportaba:
    peticiones "grandes" de ERA5 daily statistics : 40 corriendo, 2 907 en cola
    peticiones de ERA5 daily statistics           : 60 corriendo, 3 663 en cola
    acceso al archivo CDS-MARS                    : 460 corriendo, 8 488 en cola
Nuestra peticion pide un anio completo (12 meses), asi que cae en la primera categoria.
Una sola de las 75 peticiones necesarias llevaba 53 minutos en estado 'accepted' sin
arrancar. Earth Engine sirve la misma coleccion, ya agregada a diario, y ademas calcula
el promedio sobre el poligono en el servidor: las 25 peticiones se resolvieron en unos
tres minutos.
```

**Diferencia frente al producto del CDS que hay que tener presente**

```
Earth Engine agrega el dia en UTC. El producto del CDS permitia definir el dia en hora
local (se habia pedido UTC-05:00, hora de Colombia). El corte queda corrido cinco horas:
el "dia" de Earth Engine va de las 19:00 del dia anterior a las 19:00 del dia.
En la media diaria el efecto es minimo y en la agregacion mensual que usa el proyecto es
despreciable; en la minima y la maxima diarias puede desplazar algun extremo de un dia al
siguiente. Se documenta y no se corrige.
```

**Metodo de descarga**

```
Script: scripts/06_era5land_temperatura.py  (reanudable: no vuelve a pedir los anios ya bajados)
Cliente: paquete 'earthengine-api' (instalado: 1.7.45).

REQUISITOS, una sola vez:
  1. Cuenta de Earth Engine asociada a un proyecto de Google Cloud, gratis para uso
     academico: https://code.earthengine.google.com/register
  2. pip install earthengine-api
  3. earthengine authenticate   (abre el navegador; guarda el token en ~/.config/earthengine)
  4. truststore, porque en este equipo la verificacion TLS de Python falla si no usa el
     almacen de certificados de Windows.

NOTA sobre el entorno: en este equipo habia instalado un paquete llamado 'ee' (version
0.2, "a wrapper for dd", github.com/snarez/ee) que NO es Earth Engine y ocupa el mismo
nombre de import. Hubo que desinstalarlo para que 'import ee' resolviera al de Google.

Peticion (una por anio, 25 en total):
  coleccion = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
  bandas    = ['temperature_2m', 'temperature_2m_min', 'temperature_2m_max']
  reductor  = ee.Reducer.mean() sobre el poligono de la cuenca, scale = 11132 m

Procesamiento: la serie de la cuenca es el promedio de las celdas ponderado por la
fraccion del area de cada celda que cae dentro del poligono (asi opera ee.Reducer.mean()
sobre una geometria), el mismo criterio que se usa con IMERG en scripts/05_imerg_mensual_cuencas.py y scripts/historico/26_imerg_diario_fonce.py.
```

**Contraste con la temperatura de CAMELS-COL (MSWX), 8 601 dias comunes**

```
              ERA5-Land   CAMELS-COL   sesgo     r (diaria)
media          14.68 C      16.87 C    -2.19 C     0.791
minima         10.30 C      12.56 C    -2.26 C     0.784
maxima         20.08 C      21.18 C    -1.10 C     0.791
amplitud        9.78 C       8.62 C
Correlacion de la media a escala mensual: r = 0.863

ERA5-Land da la cuenca sistematicamente mas fria que MSWX, sobre todo en la minima, y con
mayor amplitud diaria. Las dos fuentes son reanalisis/interpolaciones de malla, no
observaciones, asi que la diferencia no resuelve cual es la correcta: queda anotada como
incertidumbre de la temperatura de entrada para el calculo de evapotranspiracion.
```

**Cita recomendada**

> Munoz-Sabater, J., et al. (2019). ERA5-Land hourly data from 1950 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). https://doi.org/10.24381/cds.e2161bac


---

## Inventario de archivos locales

676 archivos, 470.4 MB en total. Checksums completos en `out/datos_fuentes.csv`.

| Archivo | Tamanio | SHA-256 (12 primeros) |
|---|---|---|
| `data/camels_col/04_hydromet.zip` | 176.0 MB | `e204b898b6e5` |
| `data/camels_col/boundaries/03_CAMELS_COL_Basin_boundary/CAMELS_COL_catchments_boundaries.shp` | 40.9 MB | `32a3fdc06a7d` |
| `data/camels_col/03_boundaries.zip` | 13.2 MB | `ca4baafeb0c5` |
| `data/imerg/imerg_mensual_col.npz` | 11.4 MB | `67f27fea0959` |
| `data/ideam/cne_ideam.csv` | 3.3 MB | `fcc325062afc` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_29037020.txt` | 712.9 KB | `a1467bb05bd8` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_11077010.txt` | 708.8 KB | `3d5d934be622` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23097030.txt` | 707.3 KB | `29ef4dc54df3` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23037010.txt` | 704.5 KB | `2b5c61c6ad69` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_21237010.txt` | 702.6 KB | `b267546f07ea` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_26247020.txt` | 700.9 KB | `58a14df78532` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_35117010.txt` | 700.7 KB | `518357a935fe` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23057140.txt` | 699.9 KB | `70e473c488f5` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_21137010.txt` | 696.6 KB | `f1d589354296` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_26177030.txt` | 693.3 KB | `0d4aa9c7cf99` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_27037010.txt` | 691.0 KB | `19f55e46080e` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_26187110.txt` | 690.9 KB | `f61e9507c15a` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_13067020.txt` | 687.4 KB | `5badf80bc471` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_21027010.txt` | 682.8 KB | `9a16bd5ed9df` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_21017040.txt` | 682.4 KB | `13506dc7b8d1` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_32077080.txt` | 675.3 KB | `39be87372087` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_11057020.txt` | 675.0 KB | `b41f57743d88` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_26127040.txt` | 674.6 KB | `7d20f87b39bf` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_26057040.txt` | 674.0 KB | `9f2be7868c6b` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23107020.txt` | 673.5 KB | `c2987aa13572` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23147020.txt` | 671.7 KB | `231f64e919c6` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_51027060.txt` | 669.0 KB | `d73f7f73ec01` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23107030.txt` | 668.0 KB | `ccd52ef4747b` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_24027040.txt` | 667.1 KB | `29eb6438bc9e` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_12027050.txt` | 664.6 KB | `1f7aa7d088b7` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_35107030.txt` | 664.5 KB | `2905d17941aa` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_16047010.txt` | 663.1 KB | `3601acd85564` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_26207080.txt` | 662.7 KB | `81c5c8b7442a` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23127060.txt` | 662.1 KB | `b467ca5ea2e2` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_44037050.txt` | 661.7 KB | `bd13237abc36` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_16017020.txt` | 661.4 KB | `2b4976757032` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_24027060.txt` | 661.1 KB | `433f4552a313` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_21097070.txt` | 661.0 KB | `c95b5949680f` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_23127020.txt` | 658.6 KB | `864f81c876c2` |
| `data/camels_col/hydromet/3_Hydrometeorological_data/Hydromet_data_11037020.txt` | 658.4 KB | `403c2c31da4e` |

_(24 archivos menores de 100 KB omitidos de esta tabla; estan todos en el CSV.)_


---

## DHIME - IDEAM: precipitacion medida en pluviometros de la cuenca del Fonce

**Titulo:** Banco de datos hidrometeorologicos del IDEAM (DHIME), consulta y descarga de datos hidrometeorologicos
**Portal:** https://atencionciudadano.ideam.gov.co (antes dhime.ideam.gov.co)
**DOI:** no tiene
**Licencia / condiciones de uso:** acceso libre y gratuito, sin registro. Uso permitido solo con fines de
investigacion cientifica y estadistica; prohibida la comercializacion o venta de los datos; obligatorio citar
al IDEAM en cualquier publicacion, informe o tesis. Los terminos se aceptaron en el portal el 2026-09-23.
**Nivel de aprobacion de los datos descargados:** todos "Preliminar" (dato crudo, no validado por el IDEAM).

**Estaciones descargadas** (pluviometricas activas dentro de la cuenca de San Gil, elegidas por cubrir el
gradiente de altura y tener los registros mas largos):

| Codigo | Nombre | Altitud | Subcuenca |
|---|---|---|---|
| 24020040 | ENCINO | 1814 m | Pienta |
| 24020060 | VILLANUEVA | 1450 m | valle del Fonce (registro hasta 1994) |
| 24020220 | PAVAS LAS | 2625 m | Taquiza (la mas alta de la cuenca) |

**Metodo de descarga:** manual, a traves de la interfaz del portal (no hay API publica documentada).
Variable = PRECIPITACION; Departamento = Santander, Municipio = Todo, filtrando luego por codigo;
formato de salida CSV (el portal entrega un .zip con un unico `descargaDhime.csv`).

- Serie **diaria**: parametro "Dia pluviometrico (convencional)", periodo 1981-01-01 a 2000-12-31.
  El portal rechaza rangos diarios largos (aviso: limite de numero de anos para el tipo Diario) y con este
  parametro no devolvio ningun dato posterior al ano 2000 para estas estaciones.
- Serie **mensual**: parametro "Precipitacion total mensual", periodo 1981-01-01 a 2022-12-31.

**Advertencia sobre el dia pluviometrico:** el dia del IDEAM va de las 07:00 a las 07:00 del dia siguiente,
no de medianoche a medianoche como CHIRPS e IMERG. Hay que tenerlo en cuenta al comparar a escala diaria.

**Comprobacion hecha:** al sumar los dias de cada mes casi completo (>= 28 dias con dato) y compararlos con
el total mensual del portal, la diferencia mediana es 0.0 % y solo 1 de 360 meses difiere mas de 5 %.

| Archivo | Tamano | SHA-256 |
|---|---|---|
| `data/ideam/pluviometros/dhime/dhime_1981_2000.zip` | 58.8 KB | `b2fe0e910ba6f8e3d5a7c6b6a06d670c607d207df60ca0c9da4fec8e6b7049b6` |
| `data/ideam/pluviometros/dhime/dhime_mensual_1981_2022.zip` | 6.3 KB | `c91cd3865a290dc3678b977acdf0f25c2dd38d13b757633956c59396f3f86150` |

Procesados por `scripts/historico/23_pluviometros_dhime.py` a `out/pluviometros_fonce_diario.csv`,
`out/pluviometros_fonce_mensual.csv` y `out/pluviometros_fonce_resumen.csv`.

### Segunda descarga (2026-09-24): barrido completo de la cuenca, mensual 1998-2022

La primera descarga trajo solo tres estaciones. Esta segunda barrio **todas** las estaciones con serie
"Precipitacion total mensual" de los ocho municipios que componen la cuenca del Fonce (Charala, Coromoro,
Encino, Mogotes, Ocamonte, Paramo, San Gil y Valle de San Jose) y se quedo con las que cubren el periodo de
estudio.

**Criterio de seleccion:** la estacion se conserva si tiene dato en al menos el **70 % de los 300 meses**
de 1998-2022 (210 meses o mas). El porcentaje se calcula en `scripts/07_pluviometros_dhime.py`
sobre los datos efectivamente descargados, no sobre el conteo que anuncia el portal.

**Que quedo fuera y por que** (de las 22 estaciones de esos municipios con serie mensual):

- 14 terminan su registro en 1994 o antes, asi que no alcanzan el periodo: LAGUNA LA (24020190, hasta
  1994-12), LEJIA LA (24020200, 1994-09), MESON EL (24020140, 1994-12), VILLANUEVA (24020060, 1994-12),
  CHAPA (24010910, 1984-11), CARMEN EL HACIENDA (24020160, 1983-06), las CHARALA antiguas (24020030,
  24020210, 24025060), MOGOTES (24020050), PARAMO (24020090), INST AGRICOLA (24030890) y otras.
- Las estaciones **automaticas** de la zona (ENCINO-AUT 24025504, CHARALA-AUT 24025502,
  ESC AGR MOGOTES-AUT 24025505, MOGOTES-AUT 24025090, LA SIERRA-AUT 24025030) **no publican serie mensual
  totalizada**, solo registros sub-diarios, asi que no aparecen bajo este parametro.
- NOGAL EL (24020260) y SANTA RITA (2402500714), que si figuran en el catalogo de estaciones, no tienen
  ninguna serie de precipitacion total mensual publicada en DHIME.

**Resultado: las 8 candidatas pasaron el umbral**, la peor con 85.7 %:

| Codigo | Nombre | Altitud | Meses con dato (de 300) | Cobertura | Media | Dentro de la cuenca |
|---|---|---|---|---|---|---|
| 24020120 | COROMORO | 1520 m | 300 | 100.0 % | 209.3 mm/mes | si |
| 24025040 | ESCUELA AGRICOLA MOGOTES | 1673 m | 296 | 98.7 % | 236.6 mm/mes | si |
| 24020080 | VALLE DE SAN JOSE | 1300 m | 294 | 98.0 % | 181.1 mm/mes | si |
| 24020040 | ENCINO | 1814 m | 294 | 98.0 % | 287.2 mm/mes | si |
| 24025050 | CHARALA | 1350 m | 290 | 96.7 % | 224.7 mm/mes | si |
| 24020220 | PAVAS LAS | 2625 m | 276 | 92.0 % | 180.9 mm/mes | si |
| 24020230 | PUEBLO VIEJO | 2107 m | 267 | 89.0 % | 130.9 mm/mes | si |
| 24020150 | MAMONAL EL HACIENDA | 1408 m | 257 | 85.7 % | 96.1 mm/mes | **no** (aguas abajo de San Gil) |

La columna "dentro de la cuenca" se resuelve cruzando las coordenadas del Catalogo Nacional de Estaciones
contra el poligono de San Gil (`out/shp_fonce/cuencas_fonce.shp`). MAMONAL EL HACIENDA cae al norte del
cierre de la cuenca; se conserva en el archivo porque sirve de referencia externa, pero no debe entrar en
un promedio "sobre la cuenca" sin decirlo.

**Nivel de aprobacion:** mezcla de "Preliminar" y "Definitivo" segun el registro (la primera descarga era
toda preliminar).

**Metodo de descarga:** interfaz del portal, conducida con automatizacion de navegador. Variable =
Precipitacion; parametro = "Precipitacion total mensual"; Departamento = Santander, Municipio = Todo;
se marcaron las 8 estaciones en la lista, periodo 01/01/1998 a 31/12/2022, formato CSV. Los terminos de
uso se aceptaron de nuevo el 2026-09-24 (el portal los exige en cada sesion). Limites del portal para
este parametro: maximo 30 estaciones y 50 anos por descarga, asi que las 8 cupieron en una sola peticion.

**No se bajo serie diaria en esta ocasion** por decision del usuario.

| Archivo | Tamano | SHA-256 |
|---|---|---|
| `data/ideam/pluviometros/dhime/dhime_mensual_1998_2022_8est.zip` | 13.9 KB | `b2bdaa49053cf68c05016f1167a4e122e781928ee61a86b8065553ff4cb74ea4` |

Procesado por `scripts/07_pluviometros_dhime.py` a
`out/pluviometros_fonce_mensual_1998_2022.csv`, `out/pluviometros_fonce_1998_2022_resumen.csv` y
`out/pluviometros_fonce_catalogo.csv`.

**Nota sobre la codificacion:** el portal no es consistente. La descarga de 2026-09-23 vino en latin-1 y
la de 2026-09-24 en UTF-8; el script prueba las dos en vez de fijar una.

### Tercera descarga (2026-10-07): mensual 1981-1997

Para las tendencias de largo plazo (regla 6 de `CLAUDE.md`), se pidio el tramo anterior al periodo de
estudio para las mismas 8 estaciones de la segunda descarga, de modo que las dos descargas se puedan unir.
Estos datos aun no pasan por el control de calidad del proyecto ni los lee ningun script.

**Metodo de descarga:** interfaz del portal, conducida con automatizacion de navegador (Playwright sobre
Chrome visible). Variable = Precipitacion; parametro = "Precipitacion total mensual"; Departamento =
Santander, Municipio = Todo; se marcaron las 8 estaciones en la lista, periodo 01/01/1981 a 31/12/1997,
formato CSV. Los terminos de uso se aceptaron de nuevo el 2026-10-07. El portal entrega un .zip con un
unico `descargaDhime.csv` (UTF-8, mismas 8 columnas que la segunda descarga); se guarda sin modificar.
Detalle del portal: con Municipio = Todo la lista "Nombre o codigo" queda vacia y el boton Filtrar no
devuelve estaciones; se fijo ese filtro en "todas" (valor `-1`, el que el propio portal usa para "Todo").

**Estaciones pedidas:** 24020120 COROMORO, 24025040 ESCUELA AGRICOLA MOGOTES, 24020080 VALLE DE SAN JOSE,
24020040 ENCINO, 24025050 CHARALA, 24020220 PAVAS LAS, 24020230 PUEBLO VIEJO y 24020150 MAMONAL EL
HACIENDA (fuera de la cuenca; se pidio para que la descarga sea comparable con la segunda).

| Archivo | Tamano | SHA-256 |
|---|---|---|
| `data/ideam/pluviometros/dhime/dhime_mensual_1981_1997_8est.zip` | 8.9 KB | `42c0cb47748f000991e72f53ff80a7235f02b545f26e75b4156a1f587c65bc12` |

**Cobertura por estacion** (de 204 meses, 1981-01 a 1997-12; calculada leyendo el CSV del zip con Python):

| Codigo | Nombre | Meses con dato (de 204) | Primer mes | Ultimo mes | Nivel de aprobacion |
|---|---|---|---|---|---|
| 24020120 | COROMORO | 200 | 1981-01 | 1997-12 | Definitivo (200) |
| 24025040 | ESCUELA AGRICOLA MOGOTES | 203 | 1981-01 | 1997-12 | Preliminar (203) |
| 24020080 | VALLE DE SAN JOSE | 202 | 1981-01 | 1997-12 | Preliminar (202) |
| 24020040 | ENCINO | 196 | 1981-01 | 1997-12 | Preliminar (196) |
| 24025050 | CHARALA | 197 | 1981-01 | 1997-12 | Preliminar (197) |
| 24020220 | PAVAS LAS | 175 | 1983-05 | 1997-12 | Preliminar (175) |
| 24020230 | PUEBLO VIEJO | 167 | 1983-05 | 1997-12 | Preliminar (167) |
| 24020150 | MAMONAL EL HACIENDA | 130 | 1987-01 | 1997-12 | Preliminar (130) |

**Verificaciones hechas al recibir el archivo:** las columnas son las mismas del zip 1998-2022; todas las
fechas caen entre 1981-01 y 1997-12; no hay registros duplicados fecha-estacion ni valores vacios (1 470
filas). En los meses que comparte con la primera descarga (`dhime_mensual_1981_2022.zip`), ENCINO coincide
en sus 196 meses y PAVAS LAS en sus 175, sin ninguna diferencia.


---

### Tramo excluido: Encino 2016-2018 (decidido el 2026-09-28)

Los 36 meses de 2016 a 2018 de ENCINO (24020040) se excluyen de PL en todos los analisis. Sus totales
anuales (4 283, 6 695 y 4 833 mm) saltan muy por encima del resto de su serie (~3 143 mm) y vuelven a su
nivel en 2019, sin que IMERG ni el caudal acompanen el salto: con esos anos PL sale +23 % sobre su
promedio en 2017 y PI +3 %; sin ellos, PL coincide con PI. En junio de 2017 Encino marco 932 mm, 7.2
veces su mediana de junio. Se trata como un problema de registro.

- La exclusion se declara en `scripts/07_pluviometros_dhime.py` (tabla `EXCLUSIONES`) y queda documentada
  en `out/pluviometros_exclusiones.csv`.
- Todos los analisis leen `out/pluviometros_fonce_mensual_depurado.csv`. La serie cruda
  (`out/pluviometros_fonce_mensual_1998_2022.csv`) se conserva solo para documentar la decision.
- Efecto: PL baja de 208.9 a 204.3 mm/mes y la diferencia con IMERG pasa de -11.3 % a -9.3 %.
- Los datos descargados (`data/`) no se modifican.

### Tramos excluidos por las pruebas de anomalias (decidido el 2026-09-28)

`scripts/07c_anomalias.py` revisa la serie cruda (sin el tramo de Encino de arriba) con curvas de doble masa
y la prueba de Pettitt (1979; https://doi.org/10.2307/2346729), cada pluviometro contra el promedio de los
demas, por rondas. Resultados y decisiones (evidencia en la seccion 4.3 del notebook):

- **PUEBLO VIEJO (24020230), 1998-01 a 2004-11: excluido.** Hasta 2004-11 mide cerca de la cuarta parte que
  sus vecinos y desde 2004-12 unas tres cuartas partes (p < 0.001). El catalogo del IDEAM no registra
  ningun cambio de la estacion. Tratado como problema de registro.
- **7 meses en 0 mm: excluidos como no registrados.** PAVAS LAS 2000-08, 2009-07, 2013-07, 2018-05 y
  2019-07; VALLE DE SAN JOSE 2017-12 y 2021-12. En cada uno, todos los demas pluviometros midieron al menos
  20 mm. Otros dos ceros (PAVAS LAS 2001-08, PUEBLO VIEJO 2020-02) son plausibles y se conservan.
- **COROMORO (24020120): se conserva, marcado incierto.** Salto de -20 % desde 2003-03 (p = 0.006), sin
  escalon limpio ano a ano.
- **PUEBLO VIEJO (24020230), desde 2014-04: se conserva, marcado incierto (decidido el 2026-10-04).** La
  prueba de Pettitt encuentra un solo corte por serie. Repetida en el tramo que queda despues del primero
  (desde 2004-12, serie depurada, contra el promedio de los demas pluviometros sin Pueblo Viejo ni Coromoro),
  da un segundo salto: de 0.83 a 0.62 veces sus vecinos desde 2014-04 (-25 %, p < 0.001). No hay forma de
  saber cual tramo esta bien, asi que no se excluye. Coromoro no tiene segundo salto (p = 0.83). Salida:
  `out/anomalias_segundo_corte.csv` (`scripts/07c_anomalias.py`, paso 1b).
- **IMERG (PI) frente a PL: +11 % desde 2014-06 (p = 0.005), marcado incierto.** Cae en el cambio de
  calibracion de IMERG de TRMM a GPM el 1 de junio de 2014 (documento tecnico de IMERG V07, abajo), pero
  tambien dos meses despues del segundo salto de Pueblo Viejo. Contra una PL sin Pueblo Viejo, el salto
  baja a +6 % y deja de ser significativo (p = 0.26): buena parte viene de Pueblo Viejo. El cambio TRMM ->
  GPM puede aportar algo, pero no es la explicacion principal (lectura revisada el 2026-10-04).
- Todas las exclusiones estan en la tabla `EXCLUSIONES` de `scripts/07_pluviometros_dhime.py`, con la
  columna `evidencia` (seccion del notebook donde esta la prueba). Las cifras vigentes de PL y del sesgo
  PI-PL las calcula el notebook; no se copian aqui para que no se desactualicen.

## IMERG V07 Technical Documentation (documento tecnico del producto)

- **Autores:** Huffman, G. J., Bolvin, D. T., Joyce, R., Kelley, O. A., Nelkin, E. J., Tan, J., Watters, D. C., West, B. J.
- **Version:** 13 de julio de 2023 (V07)
- **Editor:** NASA Goddard Space Flight Center
- **URL:** https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation
- **Fecha de acceso:** 2026-09-28
- **Destino local:** `data/imerg/imerg_v07_technical_documentation.pdf` (97 paginas), SHA-256
  `2216edb07929f3163cf64b0425245d7e037dd67f4eeacb81b6bd7ab5474f99d7`
- **Uso:** fecha del cambio de calibracion TRMM -> GPM: "IMERG is processed using TRMM calibrations and
  TRMM-era constellation data from January 1998 [...] through May 2014. Commencing with 1 June 2014 IMERG
  processing uses GPM calibrations and GPM-era constellation data."

## POMCA del rio Fonce: buscado el 2026-09-24, NO disponible

Se busco el Plan de Ordenacion y Manejo de la Cuenca Hidrografica (POMCA) del rio Fonce para usarlo como
fuente de contexto. **No existe documento tecnico publico que se pueda descargar.** Queda registrado aqui
para no repetir la busqueda y para poder decirlo en el informe sin rodeos.

**Lo que si esta establecido:**

- La cuenca del rio Fonce es la **subzona hidrografica SZH 2402** del IDEAM.
- La autoridad competente es una **Comision Conjunta entre la CAS** (Corporacion Autonoma Regional de
  Santander) **y Corpoboyaca**, porque la cuenca cruza los dos departamentos.
- Hubo un **POMCA formulado en 2010-2011 por CorpoAire para la CAS** (citado como "Plan de ordenacion y
  manejo de la cuenca hidrografica del rio Fonce", CorpoAire, San Gil, 2011). Solo aparece como referencia
  bibliografica en literatura academica; **no esta publicado en ningun repositorio accesible**, ni fue
  adoptado por resolucion.
- Un **POMCA nuevo esta en formulacion desde abril de 2026**, todavia en fase de aprestamiento (reuniones
  municipales y conformacion del Consejo de Cuenca para el periodo 2026-2030). La meta anunciada es
  aprobarlo en diciembre de 2026. Reemplazara al de 2010 ajustandolo a la normativa vigente, con gestion
  del riesgo y cambio climatico.

**Donde se busco:**

- Repositorio de estudios POMCA de la CAS (`consultaambiental.cas.gov.co/pomcas/POMCAS/`): publica siete
  POMCAs con sus documentos tecnicos (Opon, Sogamoso, Carare Minero, Lebrija Medio, Medio y Bajo Suarez,
  Directos Magdalena, Afluentes Lebrija Medio). **El Fonce no esta.**
- Seccion POMCAS del sitio de la CAS (`cas.gov.co/gestion-corporativa/planes-y-programas/pomcas`): del
  Fonce solo hay la convocatoria del Consejo de Cuenca 2026-2030 (aviso y acta de evaluacion de
  candidatos), ningun documento tecnico.
- Busqueda abierta de PDF del documento de 2010-2011: sin resultados.

**Consecuencia para el analisis:** no hay area de cuenca, caudales ni precipitacion oficiales del POMCA
con que contrastar nuestros numeros. El area de San Gil que usa el proyecto (2 098.85 km2) es la del
poligono de CAMELS-COL medida por el propio proyecto (ver "Area de la cuenca"), no la del POMCA. **Nada del POMCA se cita como dato en el notebook ni en el informe**; solo se
menciona su estado (en formulacion) como contexto.

**Como se llama el documento que hay que conseguir.** La unica cita localizada del POMCA de 2011, tomada
literalmente de la bibliografia del articulo de Santana Ramon (2019), es:

> Corporacion Autonoma Regional de Santander (2011). *Plan de Ordenacion y Manejo de la Cuenca
> Hidrografica del Rio Fonce*. San Gil: CorpoAire.

En el original aparece con el autor invertido por el gestor bibliografico ("Santander, C. A. (2011). Plan
de Ordenacion y manejo de la cuenca hidrografica del rio Fonce, san gil: corpoaire"). Para pedirlo a la
CAS conviene nombrarlo por el titulo y el ano, y anadir el codigo de la subzona (SZH 2402).

**Referencias consultadas** (contexto, no datos):

- Santana Ramon, M. S. (2019). "Planes de Ordenacion y Manejo de Cuenca Hidrografica -POMCA- para la
  proteccion de la cuenca hidrografica del rio Fonce". *Ius Praxis*, 3(1). Universidad Libre.
  https://revistas.unilibre.edu.co/index.php/lux_praxis/article/view/7040
- Vanguardia (2026-04-17). "Iniciaron proceso de creacion del nuevo Pomca del rio Fonce".
- Corpoboyaca. "CAS y Corpoboyaca promueven la participacion en la formulacion del POMCA del rio Fonce".


---

## Bibliografia sobre la hidrologia del rio Fonce (San Gil)

Existe una linea de investigacion sostenida sobre **esta misma cuenca y esta misma estacion de aforo**,
desarrollada en conjunto por la Universidad Militar Nueva Granada y la Universidad de Pamplona (proyecto
UMNG INV IMP 2134, 2016-2018). Es el material de contraste mas cercano que hay al trabajo del proyecto.
Las citas siguientes estan transcritas de la bibliografia de Ochoa Acevedo et al. (2017), no reconstruidas
de memoria.

**Articulo de entrada, de acceso abierto y descargable:**

- Ochoa Acevedo, Y. P., Rivera, M. E. y Delgado Rodriguez, J. R. (2017). "Sistema de Pearson y modelos
  matematicos aplicados a la Hidrologia". *AVANCES Investigacion en Ingenieria*, 14(1), 95-108.
  ISSN 1794-4953. PDF libre en Dialnet: https://dialnet.unirioja.es/descarga/articulo/6684768.pdf
  Su introduccion resume toda la linea y de ahi salen las demas referencias.

**Trabajos sobre caudales del Fonce en San Gil:**

- Cardenas, J. C., Rivera, M. E. y Rivera, H. G. (2014). "Aplicacion del modelo Pearson-Wiener en la
  dinamica de los caudales maximos diarios en el rio Fonce en San Gil (Santander) con fines de proteccion
  contra la socavacion de puentes". V Congreso Internacional de Ingenieria Civil, Universidad Santo Tomas
  seccional Tunja.
- Correa, H. J., Castro, G. A. y Rivera, H. G. (2014). "Aplicacion del modelo Black-Sholes-Merton en el
  estudio del comportamiento erratico de los incrementos de caudales maximos (Rio Fonce, Santander)".
  V Congreso Internacional de Ingenieria Civil, Universidad Santo Tomas seccional Tunja.
- Rivera, M. E., Correa, H. J., Avendano, B. A. y Rivera, H. G. (2015). "Construccion de un proceso
  estocastico para simular el movimiento de caudales medios en el rio Fonce (San Gil-Santander)".
  *AVANCES Investigacion en Ingenieria*, vol. 12. ISSN 1794-4953.
- Torres, P. K., Rivera, H. G., Rivera, M. E., Fuentes, B. J. y Leon, A. M. (2015). "Identificacion de la
  incertidumbre en el proceso estocastico de caudales medios en el rio Fonce (San Gil-Santander)".
  *AVANCES Investigacion en Ingenieria*, vol. 12. ISSN 1794-4953.
- Fuentes, J., Palacio, G. D., Hoyos, O. L. y Rivera, H. G. (2015). "Oportunidades entre la tecnologia
  militar y la ingenieria civil. Caso de estudio: Aplicacion del Sistema Estadistico de Pearson en la
  modelacion de los caudales medios mensuales del rio Fonce-Santander". *Revista Ingenieros Militares*,
  vol. 10, 73-84.
- Martinez, L. F. (2016). "Pronostico hidrologico de caudales diarios en el rio Fonce (San Gil) mediante
  correlaciones de Pearson lluvia-escorrentia en epocas de aguas bajas". VI Congreso Internacional de
  Ingenieria Civil, Universidad Santo Tomas, Tunja.

**Trabajos sobre el balance hidrico y el clima de la cuenca** (los mas cercanos a lo que estamos haciendo):

- Fuentes, J. (2015). *Aplicacion del sistema de Pearson en el modelado estocastico de los procesos de
  precipitacion, evaporacion y escorrentia superficial (caudales medios) en el rio Fonce (Santander)*.
  Universidad Militar Nueva Granada, Facultad de Ingenieria Civil, Bogota D.C.
- Montanez, J. C. (2016). *Interpretacion estadistica de la variabilidad climatica en Santander y analisis
  de las proyecciones de cambio climatico en condiciones de proceso estocastico estacionario. Caso de
  estudio: Rio Fonce*. Universidad Militar Nueva Granada, Facultad de Ingenieria Civil, Bogota D.C.
- Ochoa Acevedo, Y. P., Rivera, M. E. y Delgado Rodriguez, J. R. (2018). "Analisis de los procesos
  relacionados a la hidrologia y a fenomenos de remocion en masa empleando herramientas de informacion
  geografica en la cuenca del rio Fonce-Santander". Poster, Universidad de Pamplona. Registro en
  ResearchGate 322940665 (la web bloquea la descarga automatica; requiere cuenta).

**Advertencia:** los trabajos no marcados abajo como leidos no se han leido todavia. Aqui solo estan
registrados como pistas bibliograficas verificadas. Nada de ellos se cita como dato en el notebook ni en
el informe mientras no se lea el documento y se compruebe la cifra en su fuente.

**Leidos el 2026-09-24** (el usuario los consiguio y estan en `InfoPreliminar/`):

- Fuentes Bacca, J. B. (2015). "Aplicacion del sistema de Pearson en el modelado estocastico de los
  procesos de precipitacion, evaporacion y escorrentia superficial (caudales medios) en el rio Fonce
  (Santander)". UMNG, proyecto ING 1770 de 2015.
  → Modela la **forma del histograma** de cada proceso del balance hidrico (tipos de Pearson), no sus
  valores. Usa precipitacion y evaporacion de **una sola estacion, Charala**, y caudales de San Gil,
  periodo 1983-2012. **No da cifras de balance hidrico ni trata la variacion espacial de la lluvia.**
- Montanez Benavides, J. C. (2016). "Interpretacion estadistica de la variabilidad climatica en Santander
  y analisis de las proyecciones de cambio climatico en condiciones de proceso estocastico estacionario.
  Caso de estudio: Rio Fonce". Trabajo de grado, UMNG. Tutor: Hebert Gonzalo Rivera.
  → Trata **El Nino y La Nina**, no el gradiente altitudinal. Su tabla 3 da Pmax y Pmin anuales de ~90
  estaciones de Santander pero **sin altitud**, asi que no sirve para cruzar lluvia contra altura.

Ninguno de los dos responde por que llueve menos en la parte alta de la cuenca; eso se resolvio con datos
propios (ver la seccion siguiente).


---

## DEM ALOS PALSAR 12.5 m (recorte de la zona de la cuenca)

- **Producto:** modelo digital de elevacion ALOS PALSAR, 12.5 m, en UTM 19N (EPSG:32619), int16, nodata
  -32768. Es lo unico que se sabe con certeza del archivo: el mosaico no trae metadatos de origen.
- **Origen:** mosaico nacional `Dem_Colombia-002.tif` (112 928 x 151 485 pixeles) de la carpeta compartida
  del equipo en Google Drive (`G:/Shared drives/DEM_Colombia/`). **Falta registrar de donde se bajo ese
  mosaico** (portal, producto exacto, fecha, licencia): pendiente de confirmar con quien lo armo.
- **Lo que usa el proyecto:** un recorte, `data/dem/dem_fonce_alos_12m.tif` (7 177 x 9 811 pixeles,
  x 1 216-90 881 m, y 631 358-753 958 m), hecho por `scripts/03_recorte_dem.py` el 2026-09-27. Cubre la
  cuenca de San Gil con 2 km de margen y todas las celdas de IMERG y ERA5-Land que la tocan. Se corta en
  pixeles enteros de la grilla original, sin remuestrear: cada pixel es identico al del mosaico
  (comprobado).
- **SHA-256 del recorte:** `d394fbcfb09157eaf7086f85e52ea0663d9ebc6dcde786ae6ed299742347231d`
- **Efecto sobre los resultados:** al leer el DEM remuestreado a 50 m, el mosaico original usaba sus
  piramides (`.ovr`) y el recorte no las tiene; la diferencia media es de 0.5 m sobre una altura media de
  2 261 m. Por eso las cifras de morfometria del 2026-09-27 difieren levemente de las anteriores.
- **Proyeccion y medidas:** la cuenca (73 grados O) cae en la zona UTM 18, no en la 19 del DEM. Medida en
  UTM 19N, el area sale 0.42 % mas grande y las longitudes 0.21 % mas largas. Por eso el DEM se usa solo
  para alturas, y las areas y longitudes se miden en el elipsoide o en MAGNA-SIRGAS / Colombia Bogota
  (EPSG:3116).


## Copernicus DEM GLO-90 (relieve de la region, para el mapa de ubicacion)

- **Producto:** Copernicus DEM GLO-90, modelo digital de superficie global de la Agencia Espacial Europea (ESA),
  programa Copernicus, con celdas de 3" (unos 90 m). Archivos de 1° x 1° en GeoTIFF optimizado para la nube (COG).
- **Fuente:** la copia publica en Amazon S3 (Registry of Open Data on AWS), sin cuenta:
  `https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_<norte>_<oeste>_DEM/<mismo nombre>.tif`.
  Segun su `readme.html`, la copia quita la fila y la columna que cada archivo original comparte con su vecino, asi
  que cada archivo tiene 1 200 x 1 200 celdas con su centro en los grados enteros.
- **Licencia y DOI:** **no verificados.** El `readme.html` de la copia remite a la pagina de licencias de Copernicus
  (https://spacedata.copernicus.eu/en/web/guest/collections/copernicus-digital-elevation-model/), que no se pudo
  abrir desde el entorno donde se descargo (la red la bloqueaba). Hay que comprobarlos ahi antes de entregar.
- **Descargado:** 2026-10-09, con `scripts/03b_relieve_regional.py` (se baja solo si no existe en `data/`).
- **Recuadro:** 75.5° O a 71.5° O y 4.5° N a 8° N (decision del usuario; primero se probo 73.5° O, recomendado
  por el agente, y el valle del Magdalena apenas asomaba): 20 archivos, de N04 a N07 y de W076 a W072.
- **Destino local:** `data/dem/copernicus_glo90/`, **fuera de git** (~100 MB); se vuelve a bajar con el script.
- **SHA-256 de cada archivo:**
  - `Copernicus_DSM_COG_30_N04_00_W072_00_DEM.tif`: `e0301928c97cdc4b7413c3917b278f7885677a84bcd620bd773339ce64ce7266`
  - `Copernicus_DSM_COG_30_N04_00_W073_00_DEM.tif`: `dd0a27d07d9b5fa90b2d560cdaf4d670b66f049072437380e37f3b567b5a365b`
  - `Copernicus_DSM_COG_30_N04_00_W074_00_DEM.tif`: `b27f06c1f2db31fc3a8e8317a4b05925a30022e1a089d1c508d14bd6b91eb39f`
  - `Copernicus_DSM_COG_30_N04_00_W075_00_DEM.tif`: `5d0338d7f675bb07deef9942c23ef7e5895330a4b09fcd1b3cf6fe01af7008ea`
  - `Copernicus_DSM_COG_30_N04_00_W076_00_DEM.tif`: `70a480b92be0a58da1a65d2c727ffed8a54f60940c3f0a3a5149a1f877e23f8e`
  - `Copernicus_DSM_COG_30_N05_00_W072_00_DEM.tif`: `3605d5147516cf8a8615abb5c7e650b3e81c644c026853a5d6a42898d7dadbd8`
  - `Copernicus_DSM_COG_30_N05_00_W073_00_DEM.tif`: `b162778727c30c1089e563c0ed8f6051e49a69931748664e665cec209094d191`
  - `Copernicus_DSM_COG_30_N05_00_W074_00_DEM.tif`: `7dc10127c2acac5b7ef8d6781e276cac4a97d26e37e927f71c1ca8475f9e493f`
  - `Copernicus_DSM_COG_30_N05_00_W075_00_DEM.tif`: `969bd0c8d69d031dbe052b60525be0d79f7818564323d67f64767fd516d745f9`
  - `Copernicus_DSM_COG_30_N05_00_W076_00_DEM.tif`: `447d1a3c079fcf78c77eb442a2571c24d22f481a4dcc123584ea20a53d558caf`
  - `Copernicus_DSM_COG_30_N06_00_W072_00_DEM.tif`: `eab54b28dceb8a8a01abc719fcec43a1bfa7f91784b0f2d4489e8a2afc12e883`
  - `Copernicus_DSM_COG_30_N06_00_W073_00_DEM.tif`: `208e2e8558d625c4c5c2b92ccfed0f36fb3a8066a29845e24407bafc0626c301`
  - `Copernicus_DSM_COG_30_N06_00_W074_00_DEM.tif`: `fbcb42a96b8eedec8fc05d152930819805c4e82c772148b37220b1ef9b1a82eb`
  - `Copernicus_DSM_COG_30_N06_00_W075_00_DEM.tif`: `c65169ebd73a6f41505cf3a4c53ca8efe53c99282882825965003e30b663ce5f`
  - `Copernicus_DSM_COG_30_N06_00_W076_00_DEM.tif`: `bea0bd2e5f41bac8560ef89ffa19411786396b4c1b6a8d993f1dce282d54945e`
  - `Copernicus_DSM_COG_30_N07_00_W072_00_DEM.tif`: `ce2e78778c97fcf3b1bb036c79aabc308d2416eec0182630ea0a504e2e8ac807`
  - `Copernicus_DSM_COG_30_N07_00_W073_00_DEM.tif`: `e54ce251a431f38f112cc479f91fc02c30c10f02e7eb4b0f51cafb7819c13b1d`
  - `Copernicus_DSM_COG_30_N07_00_W074_00_DEM.tif`: `90d38b41fc1c846f23993d8fe6d5c0d881a576c44b4edc7102639fcbf83e06aa`
  - `Copernicus_DSM_COG_30_N07_00_W075_00_DEM.tif`: `33d6cf95ddf87cbdd34a551a8cd715672aad03b6097732da78d21c33b48b3ff2`
  - `Copernicus_DSM_COG_30_N07_00_W076_00_DEM.tif`: `ea1b1719323992405c6f88a8eaf60d9a467627574f3eb3fdb434760a2c6acc01`
- **Transformaciones:** mosaico en la malla propia del DEM (sin remuestrear), recorte por indices al recuadro y
  promedio por bloques de 6 x 6 celdas (de 3" a 18", unos 550 m). Producto: `out/relieve_region_copernicus.tif`.
- **Uso:** solo la Figura 1 del informe (ubicacion). Ninguna cifra del analisis sale de este DEM; la elevacion de
  la cuenca sigue siendo la del ALOS PALSAR.


## Natural Earth 1:10 m: limites de paises y de departamentos (mapa de ubicacion)

- **Producto:** Natural Earth, escala 1:10 m, version 5.1.1 (archivo `*.VERSION.txt` de cada zip):
  `ne_10m_admin_0_countries` (paises) y `ne_10m_admin_1_states_provinces` (departamentos y estados).
- **Fuente:** la copia oficial de Natural Earth en Amazon S3: `https://naturalearth.s3.amazonaws.com/10m_cultural/`.
  El sitio `naturalearthdata.com` no se pudo abrir desde el entorno donde se descargo (la red lo bloqueaba).
- **Licencia:** **no verificada** desde el entorno: el README que trae cada zip no la menciona. Natural Earth
  declara sus datos de dominio publico en `https://www.naturalearthdata.com/about/terms-of-use/`; hay que
  comprobarlo ahi.
- **Descargado:** 2026-10-09, con `scripts/03b_relieve_regional.py`.
- **Destino local:** `data/natural_earth/`, **fuera de git** (~20 MB).
- **SHA-256:**
  - `ne_10m_admin_0_countries.zip`: `ce1ac7036499a0edd641fbc093cd209a98f96a49d2eca8480aaacad35138a7f6`
  - `ne_10m_admin_1_states_provinces.zip`: `efc59726337323058f9446210adc96673179cd344e053666ee3d28cb58ba2b05`
- **Transformaciones:** recorte al recuadro del mapa ampliado en 0.5°; columnas `nombre` y `codigo_pais`.
  Producto: `out/limites_region.gpkg` (capas `paises` y `departamentos`).
- **Uso:** solo la Figura 1 del informe. Los limites estan generalizados para la escala 1:10 m: sirven para ubicar,
  no para medir.



## Mapa Geologico de Colombia 2023, escala 1:1 500 000 (Servicio Geologico Colombiano)

- **Producto:** Mapa Geologico de Colombia 2023 del Servicio Geologico Colombiano (SGC), escala 1:1 500 000, en
  geodatabase de ArcGIS. CAMELS-COL lo cita como Gomez et al. (2023) y saca de el sus siete litologias.
- **Fuente:** https://www2.sgc.gov.co/MGC/Paginas/mgc_1_5M2023.aspx, archivo
  `https://www2.sgc.gov.co/MGC/Documents/MGC_2023/mgc2023.gdb.zip` (7.2 MB; el servidor lo marca como modificado
  el 2023-10-19).
- **Licencia:** **no verificada.** La pagina de descarga es publica y sin registro; hay que confirmar los terminos
  de uso del SGC antes de entregar.
- **Descargado:** 2026-10-09, con `scripts/03c_geologia_sgc.py` (se baja solo si no existe en `data/`; la descarga
  sigue desde el ultimo byte si la conexion se corta).
- **Destino local:** `data/sgc/mgc2023.gdb.zip` (en git). La geodatabase descomprimida, `data/sgc/mgc2023.gdb/`
  (~26 MB), queda fuera de git y la rehace el script.
- **SHA-256:** `mgc2023.gdb.zip`: `e7b0e9733dc92a72d33e1578d92717774e2a43d6bc67f23e9ad567931db39167`
- **Capas usadas:** `UC` (unidades cronoestratigraficas: simbolo, descripcion, edad) y `Fallas` (solo para el mapa).
  Sistema de referencia del archivo: EPSG:4686 (MAGNA-SIRGAS geograficas).
- **Transformaciones:** recorte de las unidades con el poligono de San Gil del proyecto; area de cada pedazo en
  EPSG:3116; cada unidad se asigna a un grupo litologico por la letra de su simbolo despues del guion (S, M, P, H,
  V, VC; minuscula = deposito cuaternario). Productos: `out/geologia_sgc_fonce_unidades.csv`,
  `out/geologia_sgc_fonce.csv` y `reporte/figuras/mapa_geologico.png`.
- **Por que no se usa la geologia de CAMELS-COL:** comparada con este recorte, sus columnas de rocas plutonicas,
  hipoabisales, metamorficas y sedimentarias traen el porcentaje de otro grupo (por ejemplo, su 63.72 % de
  "plutonic_rock_perc" es el area sedimentaria del SGC), y su columna volcanoclastica repite la volcanica en las
  346 cuencas del archivo. `scripts/18_calculos_informe.py` comprueba esa correspondencia con `assert`.
- **Uso:** la geologia del informe (tabla y Figura 5).


## MapBiomas Colombia, coleccion 3: cobertura y uso del suelo 2022

- **Producto:** mapa anual de cobertura y uso del suelo de MapBiomas Colombia, coleccion 3.0, ano 2022. GeoTIFF
  en EPSG:4326 con celdas de 0.000269° (unos 30 m), organizado en bloques de 512 x 512, valor 0 = sin dato.
- **Fuente:** copia publica en Google Cloud Storage, sin cuenta:
  `https://storage.googleapis.com/mapbiomas-public/initiatives/colombia/collection_3/coverage/colombia_coverage_2022.tif`
  (114 MB el pais entero; se lee solo la ventana de la cuenca).
- **Leyenda:** los codigos de las clases se copiaron de la hoja "LEYENDA" de
  `statistics_for_website_mb_colombia_transision_col3.xlsx` (misma copia publica,
  `.../collection_3/statistics/`). El encabezado de esa hoja dice "coleccion 2", pero el archivo es de la
  coleccion 3 e incluye las clases andinas (81 y 82) que aparecen en la cuenca. Algunos colores de la leyenda vienen
  con codigos hexadecimales incompletos; en el mapa se reemplazaron por colores parecidos.
- **Licencia y cita:** segun la hoja "READ_ME" del archivo de estadisticas, los datos son publicos y gratuitos con
  la cita: "Fundacion Gaia Amazonas (2025). Proyecto MapBiomas Colombia Coleccion 3.0 - Mapeo Anual de Cobertura y
  Uso del Suelo, recuperado en [FECHA] a traves del enlace [LINK]".
- **Descargado:** 2026-10-09, con `scripts/03d_coberturas_mapbiomas.py` (lee la ventana solo si no existe en `data/`).
- **Destino local:** `data/mapbiomas/colombia_coverage_2022_fonce.tif` (en git), la ventana tal como se lee.
- **SHA-256:** `colombia_coverage_2022_fonce.tif`: `22957c058c523283b40fbc14526b1758e5804dbb45e62ad00c4bd11e7508e58f`
- **Transformaciones:** una celda entra si su centro cae en el poligono de San Gil del proyecto; area de cada celda
  en el elipsoide WGS84. Productos: `out/coberturas_mapbiomas_fonce_2022.csv` y `reporte/figuras/mapa_coberturas.png`.
- **Uso:** las coberturas del informe (tabla y Figura 6). CAMELS-COL usa la coleccion 2 sobre su propio poligono;
  el informe compara las dos por grupo.

## Area de la cuenca (decidido el 2026-09-27)

El proyecto usa **el area del poligono**, medida por el propio proyecto, y no la que publica CAMELS-COL en
su tabla de atributos. Criterio del usuario: preferir los calculos propios a creer a ciegas los datos
publicados, siempre que se pueda.

| Cuenca | Area del poligono (geodesica), km2 | Area publicada por CAMELS-COL, km2 |
|---|---|---|
| San Gil (24027010) | 2 098.85 | 2 124.0 |

- El poligono es el mismo que distribuye CAMELS-COL; lo que cambia es que el area se mide sobre el, en el
  elipsoide WGS84 (`pyproj.Geod`), sin depender de ninguna proyeccion. La cifra publicada es 1.2 % mayor
  que su propio poligono.
- La calcula `scripts/02_shp_cuencas_estaciones.py` y la guarda en `out/shp_fonce/areas_cuencas.csv` (y en
  la columna `area_km2` del shapefile). Es **la unica fuente del area** en el proyecto: el paso de caudal a
  lamina (mm), la morfometria y el informe la leen de ahi.
- Efecto: Q expresado en mm/mes es 1.2 % mayor que con el area publicada.


## Gradiente altitudinal de la precipitacion en la cuenca (analisis propio, 2026-09-24)

Pregunta: los promedios de los pluviometros sugieren que llueve **menos** en la parte alta de la cuenca,
al reves de lo que uno esperaria. Se comprobo con dos fuentes independientes en
`scripts/09_gradiente_altitudinal.py`.

| Fuente | n | Pendiente | r | r2 |
|---|---|---|---|---|
| Pluviometros dentro de la divisoria | 7 | -394 mm/ano por 1 000 m | -0.31 | 0.10 |
| IMERG, las 30 celdas que tocan la cuenca, ponderadas por la fraccion de area dentro | 30 | -222 mm/ano por 1 000 m | **-0.91** | **0.83** |

(Hasta el 2026-09-27 el ajuste de IMERG usaba solo las 19 celdas con mas del 30 % de su area dentro y
daba -220 mm/ano por 1 000 m, r2 = 0.86. Se cambio a las 30 celdas ponderadas para no depender de un
umbral arbitrario; el resultado practicamente no cambia.)

La altitud de cada celda de IMERG sale de promediar el DEM ALOS PALSAR dentro de la celda (submuestreo
60 x 60). **El patron es real y no un artefacto de la red de pluviometros**: el satelite, que es
independiente de las estaciones, lo ve con r2 = 0.83.

**Explicacion (marco conceptual, no dato):** es el "optimo pluviometrico" de los valles interandinos
colombianos. La precipitacion crece con la altura solo hasta una franja optima y decrece por encima,
porque la humedad absoluta del aire y el agua precipitable de las nubes convectivas disminuyen con la
altura. La cuenca del Fonce va de 1 114 a 4 297 m, es decir **esta entera por encima de esa franja**, asi
que en su rango solo se observa la rama descendente.

- Poveda, G. (2004). "La hidroclimatologia de Colombia: una sintesis desde la escala inter-decadal hasta
  la escala diurna". *Revista de la Academia Colombiana de Ciencias Exactas, Fisicas y Naturales*,
  28(107), 201-221. DOI: 10.18257/raccefyn.28(107).2004.1991

Salidas: `out/gradiente_altitudinal_imerg.csv`, `out/gradiente_altitudinal_resumen.csv`,
`reporte/figuras/gradiente_altitudinal.png`.


---

## ETP de Hargreaves calculada por el proyecto (analisis propio, 2026-09-28)

La columna `poten_evapo` (ETP) de CAMELS-COL se calculo, segun el preprint (Jimenez et al., 2025, ec. 1,
pagina 11-12 de `data/camels_col/essd-2025-200.pdf`), con Hargreaves y Samani (1985) y la temperatura de MSWX:
ETo = 0.0023 * Ra * (T + 17.8) * (Tmax - Tmin)^0.5, con Ra en mm/dia segun FAO (2006) y T = (Tmax + Tmin) / 2.

`scripts/06b_etp_hargreaves.py` aplica esa misma formula (Ra con las ecuaciones 21-25 de FAO-56, por 0.408
para pasarla a mm/dia; latitud del centroide del poligono de San Gil, 6.26 N) con la temperatura de MSWX y
con la de ERA5-Land, y escribe `out/etp_hargreaves_fonce.csv`.

- La ETP publicada por CAMELS-COL es **2.75 veces** Hargreaves recalculado con las mismas temperaturas
  (cociente diario entre 2.65 y 2.85 en el 90 % de los dias; r = 0.996): la misma cuenta por una constante.
  Dejar Ra en MJ m-2 dia-1 explicaria un factor 2.45, no 2.75 (quedaria 1.12): la causa no se identifico.
- Recalculada: ~1 240 mm/ano con MSWX y ~1 257 con ERA5-Land, dentro del rango de 1 200-1 400 mm/ano que el
  mismo preprint reporta para Colombia segun el IDEAM. La publicada: ~3 420 mm/ano, por encima de la lluvia.
- Referencias: Hargreaves, G. H., y Samani, Z. A. (1985). Appl. Eng. Agric. 1(2), 96-99,
  https://doi.org/10.13031/2013.26773. Allen, R. G., et al. (1998). FAO Irrigation and Drainage Paper 56
  (edicion en espanol, 2006).
- **Decision (2026-09-28): todo el proyecto usa la ETP de Hargreaves con ERA5-Land** (`etp_era5land`).
  La ETP de CAMELS-COL no se usa en ningun calculo; solo aparece en la comparacion de la seccion 1.8.

## ONI - Indice Oceanico El Nino (NOAA Climate Prediction Center)

- **Producto:** Oceanic Nino Index (ONI): anomalia de la temperatura superficial del mar en la region
  Nino 3.4, en trimestres moviles (DJF, JFM, ..., NDJ). Es el indice con que la NOAA declara los episodios
  de El Nino y La Nina.
- **Fuente:** https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- **Licencia:** datos publicos del gobierno de EE. UU. (dominio publico).
- **Descargado:** 2026-09-28, con `scripts/17_oni_enso.py` (se baja solo si no existe en `data/`).
- **Destino local:** `data/noaa/oni.ascii.txt` (crudo; 919 trimestres, 1950-01 a 2026-07) y
  `out/oni_mensual.csv` (1998-2022, con la fase de cada mes).
- **SHA-256 de `data/noaa/oni.ascii.txt`:** `93f8c86c7a660f46318abe33b38c0479d184812d95a479a1fe869c0c2363a9e4`
- **Clasificacion usada (definicion operativa de la NOAA):** sobre el ONI redondeado a un decimal (como lo
  publica la NOAA en su tabla), trimestre calido si >= +0.5, frio si <= -0.5; hay episodio cuando se juntan al menos 5 trimestres consecutivos calidos (El Nino) o frios
  (La Nina). Cada trimestre se asigna a su mes central (DJF = enero).
- **Nota:** la NOAA revisa el ONI cuando actualiza su base de temperatura del mar (ERSST), asi que los
  valores de una descarga posterior pueden diferir ligeramente; la copia local con su SHA-256 es la
  referencia.


## ERSST v5 - temperatura superficial del mar (NOAA), campos mensuales del Punto 5

- **Producto:** NOAA Extended Reconstructed Sea Surface Temperature, version 5 (ERSST v5): temperatura
  superficial del mar mensual, global, en una malla de 2° x 2° (centros de 88° N a 88° S y de 0° a 358° E;
  89 x 180 puntos). Las celdas de tierra vienen vacias. Es la misma base con que la NOAA calcula el ONI.
- **Referencia:** Huang, B., Thorne, P. W., Banzon, V. F., et al. (2017). Extended Reconstructed Sea Surface
  Temperature, Version 5 (ERSSTv5): Upgrades, Validations, and Intercomparisons. *Journal of Climate*, 30(20),
  8179-8205. https://doi.org/10.1175/JCLI-D-16-0836.1 (verificado en Crossref el 2026-10-08).
- **Fuente:** NOAA PSL, https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc (NetCDF, °C).
- **Licencia:** datos publicos del gobierno de EE. UU.
- **Descargado:** 2026-10-08, con `scripts/19_campos_climaticos.py` (se baja solo si no existe en `data/`).
- **Periodo del archivo:** 1854-01 a 2026-09 (2 073 meses). El proyecto usa 1998-2022 (decision del usuario).
- **Destino local:** `data/noaa/ersst_v5/sst.mnmean.nc`, **fuera de git** porque pesa 160.8 MB (mas que el
  limite de GitHub); se vuelve a bajar con el script y se comprueba con su SHA-256.
- **SHA-256 de `data/noaa/ersst_v5/sst.mnmean.nc`:**
  `56659057862e8e064365d0c695570a4512937d5ebbf744f4af3f47699c267e81`
- **Transformaciones:** recorte a 1998-2022; ninguna mas (ya esta en la malla de 2° que usa el proyecto para
  los campos climaticos).
- **Control de calidad (2026-10-08):** con este archivo se calcula la temperatura media de la region Nino 3.4
  (5° S-5° N, 170° O-120° O; centros de 4° N a 4° S y de 190° a 240° E, ponderados por el coseno de la latitud)
  en trimestres moviles y se compara con la columna TOTAL del ONI (`data/noaa/oni.ascii.txt`) en 1998-2022:
  correlacion 0.997, diferencia media -0.05 °C y maxima 0.29 °C. Variantes de la caja no eliminan la
  diferencia residual; una posible razon es que el ONI local se bajo el 2026-09-28 y la NOAA lo recalcula
  cuando actualiza ERSST (ver la nota del ONI), pero no se comprobo. Resultado en
  `out/ersst_nino34_contra_oni.csv`.


## ERA5 mensual (viento, humedad y presion superficial), campos del Punto 5

- **Producto:** ERA5, reanalisis global de ECMWF, medias mensuales («monthly means of daily means»), malla de
  0.25° (721 x 1 440 puntos). Variables: componente zonal del viento `U` (m/s, positiva hacia el este),
  componente meridional `V` (m/s, positiva hacia el norte) y humedad especifica `Q` (kg/kg) en el nivel de
  **850 hPa**, y presion superficial `SP` (Pa).
- **Referencia del reanalisis:** Hersbach, H., Bell, B., Berrisford, P., et al. (2020). The ERA5 global
  reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999-2049.
  https://doi.org/10.1002/qj.3803 (verificado en Crossref el 2026-10-08).
- **Referencia del dataset usado:** European Centre for Medium-Range Weather Forecasts (2017). ERA5 Reanalysis
  Monthly Means. NSF National Center for Atmospheric Research, Geoscience Data Exchange (GDEX), dataset d633001.
  https://doi.org/10.5065/D63B5XW1 (verificado en DataCite el 2026-10-08).
- **Fuente:** https://data.gdex.ucar.edu/d633001/ , por HTTPS y sin cuenta. Un archivo por variable y por año:
  - niveles de presion: `e5.moda.an.pl/<año>/e5.moda.an.pl.128_131_u.ll025uv.<año>010100_<año>120100.nc`
    (y `128_132_v.ll025uv`, `128_133_q.ll025sc`), con los 37 niveles (~600 MB por archivo);
  - superficie: `e5.moda.an.sfc/<año>/e5.moda.an.sfc.128_134_sp.ll025sc.<año>010100_<año>120100.nc`.
- **Por que GDEX y no el Copernicus Climate Data Store:** es el mismo producto mensual de ECMWF. Primero se pidio
  al CDS, pero su cola tuvo los pedidos de niveles de presion mas de una hora sin empezar (2026-10-08). GDEX no
  tiene cola. Decision del usuario; ver `DECISIONES.md`.
- **Licencia:** ERA5 se distribuye bajo la licencia de Copernicus (uso libre con atribucion: «Contains modified
  Copernicus Climate Change Service information»); GDEX pide citar el DOI del dataset.
- **Descargado:** 2026-10-08, con `scripts/19_campos_climaticos.py`, que lee cada archivo anual por HTTPS y
  guarda solo el nivel de 850 hPa (o la presion superficial), sin otro cambio.
- **Periodo:** 1998-01 a 2022-12 (300 meses; decision del usuario).
- **Destino local:** `data/era5_campos/<variable>_<año>.nc` (100 archivos: u, v, q y sp por 25 años), **fuera de
  git** (suman ~2 GB). Se vuelven a obtener con el script. No se registra el SHA-256 de cada extracto porque los
  produce el propio script; los archivos de GDEX son la fuente y se identifican por su ruta.
- **Transformaciones** (`scripts/19_campos_climaticos.py`):
  1. **Celdas bajo tierra:** una celda de 0.25° esta bajo el terreno en un mes si su presion superficial media es
     menor que 850 hPa; sus valores de 850 hPa son extrapolados por el modelo y no se usan.
  2. **Remuestreo a 2°:** promedio por bloques ponderado por el coseno de la latitud, en cajas de 2° centradas en
     los puntos de ERSST v5 (las celdas que caen justo en el borde cuentan la mitad en cada caja).
  3. **Mascara a 2° (estricta):** una caja queda vacia en un mes si cualquiera de sus celdas de 0.25° esta bajo
     tierra ese mes. Ademas se guarda la fraccion de la caja bajo tierra.
  4. **Unidades:** q de kg/kg a g/kg.
  5. **Transporte de humedad a 850 hPa:** q·u y q·v con las medias mensuales, en (g/kg)·(m/s). Limitacion: la
     media del mes de q·u no es (media de q)·(media de u); se pierde el transporte de los eventos de dias.
- **Producto:** `out/campos_climaticos_2deg_1998_2022.nc` (SST, u850, v850, q850, qu850, qv850 y la fraccion bajo
  tierra, en la malla de 2° de ERSST).


## Plotly.js 2.32.0 (biblioteca de gráficas del informe)

- **Qué es:** la biblioteca de JavaScript con que se dibujan las gráficas interactivas del informe. No es un
  dato: se registra aquí porque es un archivo descargado que el proyecto guarda y usa.
- **URL:** https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.32.0/plotly.min.js
- **Licencia:** MIT (Plotly, Inc.; el aviso va en la cabecera del archivo).
- **Descargado:** 2026-10-06, con `curl`, a `reporte/vendor/plotly-2.32.0.min.js`.
- **SHA-256:** `0a17719a72751704861215da0e5c5cdb3f9a8d50eff5cb84cb6f8b80786682b0`
- **Uso:** `scripts/18b_reporte_html.py` lo incrusta en `reporte/reporte-fonce.html` para que el informe abra
  sin internet, y se detiene si el SHA-256 no coincide.

## Notas de reproducibilidad

- El archivo de credenciales de Earthdata (`_netrc.txt`) **no** forma parte del proyecto y no debe versionarse ni compartirse. Para volver a descargar IMERG (`scripts/04_imerg_descarga_mensual.py`) hay que proveer credenciales propias de NASA Earthdata; el aviso esta al comienzo del script.

- El orden de ejecucion de los scripts, y cuales necesitan acceso externo, esta en `scripts/README.md`.

- Zenodo sirve versiones inmutables: el DOI `10.5281/zenodo.18794895` seguira devolviendo exactamente estos archivos. El DOI de concepto `10.5281/zenodo.14947146` apunta siempre a la mas reciente y puede cambiar.

- El catalogo del IDEAM es una instantanea viva: `datos.gov.co` no versiona, asi que la copia local con su SHA-256 es la unica referencia estable.

- IMERG V07 se reprocesa ocasionalmente; los granulos llevan sufijo de version (`V07B`) que conviene registrar junto con la fecha de descarga.

- DHIME no versiona sus descargas ni expone una API publica: la copia local en `data/ideam/pluviometros/dhime/` con su SHA-256 es la unica referencia estable, y el nivel de aprobacion puede cambiar si el IDEAM valida los datos mas adelante.
