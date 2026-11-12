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
