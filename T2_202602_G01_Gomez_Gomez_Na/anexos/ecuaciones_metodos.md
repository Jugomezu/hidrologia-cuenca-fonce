# Ecuaciones de los métodos de la fase 4 (punto 1)

Script: `codigo/punto1/21_metodos_et.py`. Paso diario, en cada uno de los 6 puntos; el mensual es la suma de los días
y la cuenca es el promedio ponderado por Voronoi, igual que la ETo FAO-56. Unidades: mm/día; Rn, Rs y Ra en
MJ/m²·día; T en °C; presiones en kPa. Mismos forzantes que la ETo (ERA5-Land, 1998–2022). λ = 2.45 MJ/kg (el de
FAO-56). G = 0 diario. Δ, γ, es, ea y u2 como en FAO-56 (ec. 8, 12, 13, 47), con la presión de cada punto.

Elegidos por Juan el 2026-11-20. Thornthwaite se programó paso a paso con Juan (script 22). De Cenicafé se usa solo la versión de 2006 (Juan). Referencias completas, con DOI o enlace, en `anexos/referencias.md`. 
| Método | Estima | Ecuación | Fuente |
|---|---|---|---|
| Thornthwaite (1948) | ETP | 16 (L/12)(N/30)(10 T/I)^a; I = Σ(Tᵢ/5)^1.514; a = 6.75·10⁻⁷ I³ − 7.71·10⁻⁵ I² + 0.01792 I + 0.49239 | Notas del curso, Parte 7. Mensual. T = media de (Tmáx + Tmín)/2; I fijo por punto (1998–2022); L = media de las horas de luz del mes (FAO-56 ec. 24, 25, 34); N = días del mes |
| Hargreaves–Samani (1985) | ETo | 0.0023 · 0.408 · Ra · (T + 17.8) · √(Tmáx − Tmín) | Notas del curso, Parte 7; FAO-56 ec. 52 |
| Priestley–Taylor (1972) | ETP | 1.26 · Δ/(Δ+γ) · (Rn − G)/λ | Notas del curso, Partes 2 y 7 |
| Makkink (1957) | ETo | 0.61 · Δ/(Δ+γ) · Rs/λ − 0.12 | Notas del curso, Parte 7 |
| Penman (1948), forma FAO-24 | E0 | Δ/(Δ+γ) · Rn/λ + γ/(Δ+γ) · 0.27 (1 + U2/100) · (es − ea) | Notas del curso, Parte 6 (U2 en km/día, déficit en mbar) |
| Brutsaert y Stricker (1979), AA | ET real | 2 · ETw − ETp, con ETw = Priestley–Taylor y ETp = Penman | Notas del curso, Parte 7 |
| Cenicafé, Jaramillo (2006) | ETo | 4.37 · exp(−0.0002 h) | Cenicafé 57(4):288–298, p. 292; ajustada a Penman–Monteith, 34 estaciones, 170–3 700 m, R² = 0.80 |

Supuestos que se declaran:

- Rn es la del pasto de referencia (albedo 0.23), también en Penman y en la AA. No es la Rn de agua libre.
- Cenicafé: h = altura media del DEM en la región de Voronoi de cada punto (`anexos/punto1/elevacion_puntos_dem.csv`).
  Da un valor diario fijo por punto: el método no tiene ciclo anual, solo cambia con los días del mes.
- La AA da ET real, no ETo: en la tabla de ajuste lleva la columna `cantidad` para no mezclarla sin decirlo.

## Un día a mano

2010-02-15, punto 6 (el mismo día de `anexos/punto1/dia_verificado_a_mano.xlsx`). Entradas: Tmáx 22.9976, Tmín
11.1917 °C, ea 1.4241 kPa, P 78.1166 kPa, viento a 10 m 0.8977 m/s, Rs 21.7396, Ra 35.6843, Rn 12.5958 MJ/m²·día,
h 2 144.948 m. Intermedios: T 17.0947 °C, Δ 0.12344, γ 0.05195 kPa/°C, Δ/(Δ+γ) 0.7038, es 2.0693 kPa, u2 0.6714 m/s.

| Método | mm/día |
|---|---|
| Hargreaves | 4.0149 |
| Priestley–Taylor | 4.5592 |
| Makkink | 3.6895 |
| Penman 1948 | 4.4337 |
| AA | 4.6847 |
| Cenicafé 2006 | 2.8456 |
| ETo FAO-56 (referencia) | 3.76 |

Calculado aparte, sin las funciones del script, y coincide a 4 decimales con `productos/punto1/metodos_diaria_puntos.csv`.

### Un mes a mano, Thornthwaite

2010-02, punto 6 (lat 6.4°). T = 17.6923 °C, I = 67.9572, a = 1.5660, L = 11.798 h, N = 28.
ETP = 16 · (10 · 17.6923/67.9572)^1.566 · (11.798/12) · (28/30) = 65.6928 mm/mes. Calculado aparte y coincide con
`productos/punto1/thornthwaite_mensual_puntos.csv`.

## Qué cantidad estima cada método

| Método | Estima | Superficie | De dónde sale |
|---|---|---|---|
| Penman–Monteith FAO-56 | ETo | Pasto de referencia: 0.12 m, rs = 70 s/m, albedo 0.23, bien regado | FAO-56 |
| Hargreaves–Samani | ETo | El mismo pasto (calibrado para reproducirlo) | FAO-56 ec. 52 la llama ETo |
| Cenicafé 2006 | ETo | El mismo pasto: regresión sobre valores de Penman–Monteith | Jaramillo (2006), p. 290–292 |
| Makkink | ETo | Pasto bien regado | FAO-24, p. 8: su método de radiación, «adaptation of the Makkink formula», estima ETo |
| Thornthwaite | ETP | Superficie vegetal extensa sin falta de agua; sin cultivo definido | Notas del curso |
| Priestley–Taylor | ETP (ambiente húmedo) | Superficie saturada sin advección; no es el pasto de referencia | Notas del curso |
| Penman 1948 | E0 | Agua libre. Aquí se calcula con la Rn del pasto, así que queda como una potencial | Notas del curso |
| Brutsaert–Stricker (AA) | ET real | La cuenca, con el agua que tiene | Notas del curso |

Consecuencia: frente a la ETo FAO-56 solo se comparan directamente las ETo (Hargreaves, Cenicafé, Makkink). Thornthwaite
y Priestley–Taylor son potenciales sin superficie fija y se leen con cuidado. La AA se compara con la ET real (balance
P − Q y productos, fase 6), no con la ETo.

## Ficha de los métodos de fuera de la tabla

### Makkink (1957)

- **Publicación original.** Makkink, G. F. (1957). Testing the Penman formula by means of lysimeters. *Journal of the
  Institution of Water Engineers, 11*, 277–288. No está en línea y no se leyó.
- **Proceso.** Evaporación controlada por la energía solar que llega al suelo: ET ∝ Δ/(Δ + γ) · Rs/λ. Δ/(Δ + γ) es la
  fracción de la energía que va a evaporar a una temperatura dada.
- **Qué simplifica.** Deja fuera el término aerodinámico (viento y déficit de vapor) y la radiación de onda larga: usa
  Rs en vez de Rn, con dos constantes empíricas (0.61 y −0.12) que absorben esas diferencias.
- **Clima de calibración.** Con lisímetros (lo dice el título). El lugar y el cultivo no se verificaron en el original.
- **Por qué sirve aquí.** La cuenca es húmeda y de viento débil: el término aerodinámico es solo el 7.6 % de la ETo
  FAO-56 (1998–2022, `eto_mensual_cuenca.csv`), así que lo que Makkink deja fuera pesa poco. Las notas del curso lo
  recomiendan, junto con Priestley–Taylor, para climas húmedos con datos de radiación y temperatura. Resultado: −3 %.

### Brutsaert y Stricker (1979), advección-aridez (AA)

- **Publicación original.** Brutsaert, W. y Stricker, H. (1979). *Water Resources Research, 15*(2), 443–450.
  https://doi.org/10.1029/WR015i002p00443. No se leyó el texto (la página de la revista no abrió).
- **Proceso.** Relación complementaria (Bouchet, 1963): cuando la superficie se seca, la ET real baja y la energía que
  sobra calienta y seca el aire, lo que sube la ET potencial. ET + ETp = 2 · ETw.
- **Qué simplifica.** Supone que la relación es simétrica; ETw con Priestley–Taylor (α = 1.26) y ETp con Penman. No
  usa datos de suelo ni de vegetación. Las notas lo dan para escala regional, mensual a anual.
- **Clima de calibración.** No verificado en el original.
- **Por qué sirve aquí.** Da ET real solo con datos meteorológicos, independiente del balance P − Q y de los productos
  satelitales. Limitación encontrada: aquí Priestley–Taylor supera a Penman en el 96 % de los días (viento débil), y
  por eso la AA da una ET real mayor que la potencial (1 550 mm/año), lo que no es físico. Se explica en la fase 5.

### Cenicafé, Jaramillo (2006)

- **Publicación original.** Jaramillo Robledo, A. (2006). Evapotranspiración de referencia en la región Andina de
  Colombia. *Cenicafé, 57*(4), 288–298. Leída completa.
- **Proceso.** Ninguno directo: es una regresión de la ETo de Penman–Monteith contra la altitud. La forma exponencial se
  justifica porque la presión y la densidad del aire bajan exponencialmente con la altura (p. 291).
- **Qué simplifica.** Todo menos la altitud: no tiene ciclo anual ni cambia de un año a otro; un valor fijo por punto.
- **Clima de calibración.** 34 estaciones de los valles interandinos del Cauca y el Magdalena, de 170 a 3 700 m
  (R² = 0.80), dos de ellas en Santander (p. 291–292).
- **Por qué sirve aquí.** Es una ecuación regional para los Andes colombianos y cubre la altura de los 6 puntos (1 598 a
  3 128 m de altura media de sus regiones). Sirve como referencia de orden de magnitud. Resultado: −12 %.
