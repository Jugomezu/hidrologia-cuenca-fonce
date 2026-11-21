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
