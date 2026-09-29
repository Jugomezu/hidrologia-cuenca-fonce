# Descarga manual de los pluviómetros del IDEAM (cuenca del Fonce)

Portal: **https://atencionciudadano.ideam.gov.co** (antes dhime.ideam.gov.co). Es de acceso libre,
no pide registro. Uso investigativo no comercial, citando al IDEAM. Cada archivo que entrega pesa
máximo 5 MB, así que conviene pedir pocas estaciones a la vez.

## Qué pedir

- Parámetro: **PRECIPITACIÓN**
- Etiqueta / cálculo: **Precipitación total diaria** (no la mensual ni la horaria)
- Período: **1981-01-01 a 2022-12-31** (es el período de CAMELS-COL; si el portal deja más, pide todo)
- Formato de salida: **CSV** (llega dentro de un .zip)

## Dónde guardar

Deja los archivos tal como lleguen (sin abrirlos ni editarlos en Excel) en esta misma carpeta:

    data/ideam/pluviometros/

## Estaciones, en orden de prioridad

El portal a veces muestra el código sin los ceros de la izquierda (24020060 en vez de 0024020060).
Las dos formas son la misma estación.

### 1. Convencionales activas con registro largo (las más valiosas: son las que no están en datos.gov.co)

| Código | Nombre | Desde | Altitud |
|---|---|---|---|
| 0024020060 | VILLANUEVA | 1956 | 1450 m |
| 0024020080 | VALLE DE SAN JOSE | 1958 | 1300 m |
| 0024020040 | ENCINO | 1954 | 1814 m |
| 0024020190 | LAGUNA LA | 1967 | 1550 m |
| 0024020200 | LEJIA LA | 1967 | 1500 m |
| 0024010910 | CHAPA | 1970 | 1600 m |
| 0024020120 | COROMORO | 1973 | 1520 m |
| 0024025050 | CHARALA | 1973 | 1350 m |
| 0024020260 | NOGAL EL | 1977 | 1560 m |
| 0024020140 | MESON EL | 1979 | 1200 m |
| 2402500714 | SANTA RITA | 1979 | 1527 m |

### 2. Las más altas (cubren la parte alta de la cuenca, donde no hay casi nada)

| Código | Nombre | Desde | Altitud |
|---|---|---|---|
| 0024020220 | PAVAS LAS | 1983 | 2625 m |
| 0024020230 | PUEBLO VIEJO | 1983 | 2107 m |
| 0024025030 | LA SIERRA - AUT | 1967 | 2850 m |

### 3. Climatológicas y agrometeorológica activas (también miden precipitación)

| Código | Nombre | Desde | Altitud |
|---|---|---|---|
| 0024025040 | ESCUELA AGRICOLA MOGOTES | 1973 | 1673 m |
| 0024025090 | MOGOTES - AUT | 2004 | 1673 m |
| 0024025502 | CHARALA-24025502 - AUT | — | 1328 m |
| 0024025504 | ENCINO-24025504 - AUT | — | 1898 m |
| 0024025505 | ESC AGR MOGOTES - AUT | — | 1708 m |

### 4. Suspendidas con registro histórico (opcionales, sirven para rellenar años viejos)

| Código | Nombre | Período | Altitud |
|---|---|---|---|
| 0024020030 | CHARALA | 1954-1973 | 1350 m |
| 0024020050 | MOGOTES | 1958-1974 | 1673 m |
| 0024020090 | PARAMO | 1958-1971 | 1353 m |
| 0024020210 | CHARALA (pluviográfica) | 1968-1971 | 1350 m |
| 0024025060 | CHARALA (climatológica) | 1956-1970 | 1450 m |
| 0024020160 | CARMEN EL HACIENDA | 1979-1983 | 1400 m |
| 0024020100 | QUINTA LA | 1959-1960 | 1700 m |

Fuente de la lista: `out/fonce_inventario_estaciones.csv` (estaciones del Catálogo Nacional de
Estaciones del IDEAM que caen dentro del polígono de la cuenca de San Gil).
