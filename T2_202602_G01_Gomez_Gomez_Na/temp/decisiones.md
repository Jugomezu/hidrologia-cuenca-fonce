# Decisiones (temporal)

Registro de las decisiones tomadas y su razonamiento. Archivo temporal: la carpeta `temp/` se borra antes de
armar el ZIP de la entrega.

## 2026-11-12 · Punto 1 · Puntos de ERA5-Land

**Decisión.** Seis centros de celda de ERA5-Land (0.1°). El promedio de la cuenca pondera cada punto por el
área de su región de Voronoi.

| Punto | lon, lat | Altura celda (m) | Altura región (m) | Peso |
|---|---|---|---|---|
| 1 | −73.1, 6.0 | 3 259 | 3 122 | 0.124 |
| 2 | −73.1, 6.2 | 1 776 | 1 859 | 0.173 |
| 3 | −73.1, 6.3 | 1 580 | 1 688 | 0.120 |
| 4 | −73.1, 6.4 | 1 715 | 1 598 | 0.146 |
| 5 | −73.0, 6.1 | 3 066 | 3 128 | 0.186 |
| 6 | −73.0, 6.4 | 2 085 | 2 145 | 0.252 |

**Razonamiento.**
1. Se descargaron datos de celdas con al menos el 90 % de su área dentro de la cuenca, para que no las
   influyeran zonas externas.
2. La altura varía mucho en la cuenca (1 118 a 4 284 m), y con ella la temperatura, una de las variables que
   intervienen en la ET. Se buscó que cada punto tenga una altura parecida a la de su región y que haya uno en
   cada franja de altura de igual área.
3. Entre las 12 376 combinaciones posibles se tomó la de menor diferencia de altura ponderada (88 m).
4. Descartadas: las opciones de áreas iguales, porque ubicaban peor los puntos en altura o usaban celdas con
   parte fuera de la cuenca; y la D, porque no tenía punto en el valle bajo.
5. Limitación: las celdas suavizan el relieve, así que ninguna representa los picos sobre unos 3 500 m.

## 2026-11-12 · Punto 1 · Variables y período de ERA5-Land

**Decisión.** Se descargaron de `reanalysis-era5-land-timeseries`, en los 6 puntos y para 1998–2022 (horario), las
variables que pide la ETo de FAO-56 (ec. 6): `2m_temperature`, `2m_dewpoint_temperature`, `surface_pressure`,
`10m_u_component_of_wind`, `10m_v_component_of_wind` y `surface_solar_radiation_downwards`.

**Razonamiento.**
1. Cada término de la ec. 6 sale de una de ellas: T, Δ y es de `t2m`; ea de `d2m`; γ de `sp`; u2 del viento a
   10 m (ec. 47); Rn de `ssrd`. G ≈ 0 a escala diaria.
2. `sp` en vez de la presión por altura (ec. 7): así γ corresponde a la misma topografía del modelo que las
   demás variables.

## 2026-11-12 · Punto 1 · Días en hora local

**Decisión.** Los días se arman en hora local (UTC−5): la hora local es `valid_time` − 5 h.

**Razonamiento.** T máxima y T mínima deben corresponder al día de Colombia. La suma diaria de `ssrd` no cambia,
porque toda la luz del día cae dentro del mismo día UTC.

## 2026-11-12 · Punto 1 · Diciembre de 2022 incompleto en hora local

**Decisión.** Se deja así, sin descargar más horas.

**Razonamiento.** La descarga termina el 2022-12-31 a las 23:00 UTC, que son las 18:00 hora local, así que a
diciembre de 2022 le faltan sus últimas 5 horas (noche). El efecto es despreciable y se menciona como limitación.
En el otro extremo, la primera hora descargada (1998-01-01 00:00 UTC) es el 1997-12-31 a las 19:00 hora local;
esas 5 horas (19:00–23:00 del 1997-12-31) se descartan para que la serie empiece el 1998-01-01 00:00 hora local.

## 2026-11-12 · Punto 1 · Agregación mensual de ERA5-Land

**Decisión.** Por punto y mes (hora local): la radiación solar (`ssrd`) se suma (MJ/m²·mes); temperatura, punto
de rocío, presión y rapidez del viento se promedian; Tmax y Tmin mensuales son el promedio de las máximas y
mínimas diarias. La rapidez del viento se calcula cada hora, √(u10² + v10²), antes de promediar.

**Razonamiento.** Solo la radiación es una cantidad que se acumula (energía); las demás son estados del aire y su
suma no tiene sentido físico. La suma mensual de radiación ya refleja el número de días de cada mes. Se suma Rs,
no Rn: Rn no se descargó y se calcula después con FAO-56, a escala diaria.

## 2026-11-12 · Punto 1 · Radiación neta Rn (FAO-56)

**Decisión.** Rn diaria por punto con FAO-56 (ec. 21–40), α = 0.23, G = 0; Rn mensual = suma de las diarias.
ea = promedio diario de e°(Td) horario. En Rso (ec. 37), z = altura de la superficie del modelo, despejada de la
presión media `sp` con la ec. 7.

**Razonamiento.** Rn depende de Tmax, Tmin y ea del mismo día, así que se calcula diaria y luego se suma al mes.
z del modelo para que Rso corresponda a la misma superficie que Rs y T; Rso cambia solo 2.7 % por cada 1 000 m.

## 2026-11-12 · Punto 1 · ETo con FAO-56 (ec. 6)

**Decisión.** ETo diaria por punto con la ec. 6 de FAO-56: T = (Tmax + Tmin)/2 (ec. 9), es = media de e°(Tmax) y
e°(Tmin) (ec. 12), γ con la presión `sp` (ec. 8), u2 = 0.748 × rapidez a 10 m (ec. 47), G = 0. ETo mensual = suma
de las diarias; ETo de la cuenca = promedio de los 6 puntos ponderado por el área de Voronoi.

**Razonamiento.** Es la forma estándar de FAO-56 a escala diaria. La suma mensual se hace después del cálculo
diario porque la ecuación no es lineal.
