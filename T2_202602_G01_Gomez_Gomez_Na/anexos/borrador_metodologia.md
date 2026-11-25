# Borrador de metodología · Punto 1 (evapotranspiración, cuenca del río Fonce en San Gil)

Armado desde `anexos/decisiones.md` (solo las decisiones vigentes). Es un borrador para el informe: Juan lo revisa y lo
reescribe en su voz. Entre corchetes, el script de `codigo/punto1/` que hace cada paso.

## 1. Datos y periodo

- **Periodo:** 1998–2022 (25 años), el mismo de IMERG en la Tarea 1. Las tendencias de la Tarea 1 empiezan en 1981; las
  de este trabajo no, y se declara.
- **Cuenca:** polígono de CAMELS-COL hasta San Gil (IDEAM 24027010), 2 098.85 km² (área del polígono, Tarea 1).
- **Forzantes de la ETo:** ERA5-Land, producto de series de tiempo (`reanalysis-era5-land-timeseries`, CDS), horario,
  en 6 centros de celda de 0.1°: t2m, d2m, sp, u10, v10 y ssrd [01]. Celdas con ≥ 90 % de su área dentro de la cuenca,
  una por franja de altura de igual área (1 580 a 3 259 m). El valor de cuenca es el promedio ponderado por Voronoi.
- **Días en hora local** (UTC−5): T máxima y mínima corresponden al día de Colombia. A diciembre de 2022 le faltan sus
  últimas 5 horas (limitación despreciable).
- **Lluvia y caudal:** de la Tarea 1. PI (IMERG ponderado por área de celda) y PL (7 pluviómetros del IDEAM dentro de la
  divisoria, depurados). Lluvia principal: P̄ = (PI + PL)/2; PI y PL quedan como sensibilidad. Q observado de
  CAMELS-COL en San Gil, en lámina; mes vacío si faltan 5 o más días.
- **Estaciones del IDEAM (DHIME):** brillo solar, Tmáx, Tmín y HR de Mogotes (24025040), La Sierra (24025030) y
  Charalá (24025050); viento de Mogotes-AUT (24025090). Todo «Preliminar».
- **Productos de ET real:** GLEAM v4.3a, MOD16A2GF v061, SSEBop v6.1 y v5, TerraClimate v1.1 (aet) y la evaporación de
  ERA5-Land, promediados en la cuenca por área de intersección de cada celda [05–11, 14].
- **Error de ECMWF:** el ERA5-Land mensual (Rn y evaporación) está dañado en sep–dic 2022; todo lo que lo usa se corta
  en 2022-08. La ETo no está afectada (se comprobó, [04d]).
- **Sin datos:** no hay torre de flujo en la región (la más cercana, Guatavita, a 159 km y desde 2023). El tanque
  evaporímetro de Mogotes-AUT no se usa: no tiene un factor de unidades coherente [33].

## 2. ETo de referencia [02–04]

- Penman–Monteith (FAO-56), ec. 6, diaria por punto. T = (Tmáx + Tmín)/2; es = media de e°(Tmáx) y e°(Tmín); ea =
  promedio de las 24 e°(Td) horarias del día; γ con la presión `sp` de cada punto; u2 = 0.748·u10 (ec. 47); G = 0.
- Rn del pasto de referencia con FAO-56 (ec. 21–40), albedo 0.23. La ssrd del producto de series de tiempo viene por
  hora (no acumulada); Rs diaria = suma de las 24 horas.
- ETo mensual = suma de las diarias (la ecuación no es lineal). Comprobación con medias mensuales y G de la ec. 43:
  diferencia entre −1.2 y +0.8 % [04b].
- Supuestos declarados: la ec. 47 supone perfil logarítmico neutro sobre pasto de 0.12 m, así que u2 es el viento del
  pasto de referencia, no el real. La altura del modelo queda 65 m bajo la media del DEM (≈ +0.3 °C); no se corrige.
- Verificación: un día a mano (2010-02-15, punto 6) reproduce el script a 4 decimales [04c].

## 3. Pruebas de la referencia [12–20]

- **Radiación:** Rs de estación con Angstrom (FAO-56 ec. 35, a_s = 0.25, b_s = 0.50) contra la celda de ERA5-Land que
  contiene cada estación. Valida la entrada de más peso; no cuenta como prueba.
- **Prueba 1, estaciones:** ETo Penman–Monteith (FAO-56) con datos de estación (Tmáx, Tmín, HR, Rs de Angstrom, presión
  por altura) y viento de Mogotes-AUT medido a 10 m (IDEAM GDI-M003, p. 37); viento de ERA5-Land como sensibilidad.
  Solo días con todas las entradas; no se rellena.
- **Prueba 2, TerraClimate pet:** ETo de referencia ASCE Penman–Monteith con resistencia corregida por CO2; sus
  anomalías vienen de ERA5 (no es independiente en la variabilidad).
- **Dispersión entre pruebas:** por mes, |sesgo % frente a TerraClimate − media del sesgo % frente a las 3 estaciones|.
  Es el umbral para comparar métodos.
- Sesgo = nuestra ETo − referencia. Verificación: un mes a mano (Mogotes, marzo de 2001) [18].

## 4. Métodos de otras familias [21–23, 25]

- Thornthwaite (T del mes = media de (Tmáx + Tmín)/2; índice de calor I fijo con la climatología 1998–2022; L = promedio
  de las horas de luz del mes), Hargreaves, Priestley–Taylor (α = 1.26), Makkink (0.61 y −0.12, de las notas del curso),
  Cenicafé (Jaramillo, 2006: 4.37·exp(−0.0002 h)) y Brutsaert–Stricker (relación complementaria, ET real).
- Mismos forzantes, periodo y paso diario que la ETo.
- **Comparación con la misma superficie, sin calibrar:** Hargreaves, Makkink, Cenicafé, Penman (FAO-24, c = 0.8) y
  Thornthwaite frente a la ETo Penman–Monteith (FAO-56); Priestley–Taylor frente a Penman–Monteith (FAO-56) con rs = 0.
  La relación complementaria es ET real y va a la sección 6. Métricas por mes calendario: sesgo, MAE, RMSE, amplitud y
  fase.
- Meyer no se usa: necesita la temperatura del agua.

## 5. Explicación de las diferencias [26–28]

- Términos radiativo y aerodinámico de la ec. 6 por mes.
- α* = ETo/Eeq, con Eeq = Δ/(Δ + γ)·Rn/λ.
- Sensibilidad: Tmáx y Tmín +1 y +2 °C por igual (con ea constante y con HR constante), u2 +10 %, Rs −10 % y ea +10 %,
  sobre todos los métodos. Rnl se recalcula con las entradas nuevas; Thornthwaite conserva I.

## 6. ET real [15, 24]

- Balance: ET = P̄ − Q, años calendario. ΔS del suelo de ERA5-Land (0–289 cm) ≈ 0 en el largo plazo.
- Incertidumbre al 95 %: σ_P = 1.96·|PL − PI|/2 (error de la media de dos medidas), σ_Q = 25.6 % de Q (error de la curva
  de gasto; Di Baldassarre y Montanari, 2009), σ_ET = √(σ_P² + σ_Q²).
- Techo de energía: Rn/λ con la Rn real de ERA5-Land (ssr + str, hasta 2022-08), λ = 2.45 MJ/kg.
- Cada producto se compara con el balance en sus mismos meses; es consistente si cae dentro de ± σ_ET. La mediana de
  productos se hace sin SSEBop v5 ni la relación complementaria (fuera de ± σ_ET).

## 7. Régimen: energía o agua [29–31]

- Budyko con P̄: φ = ETo/P, ε = ET/P, curva de Fu (ω ajustado al punto multianual), elasticidad de Q a P teórica y
  empírica (Sankarasubramanian et al., 2001). Ejes completos. Sensibilidad de φ con Rn/λ y Priestley–Taylor.
- Meses: φ mensual = ETo/P̄; φ > 1 limitado por agua.
- Fracción evaporativa λET/Rn frente a la humedad del suelo de la zona de raíces de GLEAM (marco de Seneviratne et al.,
  2010), con la mediana de productos sin GLEAM (sería circular) ni SSEBop v5; ajuste con quiebre.

## 8. Cambios en la demanda [32]

- Tendencias 1998–2022 de la ETo Penman–Monteith (FAO-56), Thornthwaite, T, ea, u2 y Rs con los métodos de la Tarea 1:
  Mann-Kendall estacional con pendiente de Sen (p por permutación de años completos), OLS con una constante por mes y
  error de Newey-West (12 rezagos), Hamed–Rao, Pettitt y control de FDR (Benjamini–Hochberg). α = 0.05.
- Atribución (complementaria): sensibilidad de la sección 5 × tendencia de cada forzante, más residuo.
