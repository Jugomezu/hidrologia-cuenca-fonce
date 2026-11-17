# Bitácora del uso de IA

Herramienta: Claude (Anthropic), usado con Claude Code dentro de un proyecto de claude.ai conectado al repositorio.
Cada tarea se pidió en un hilo aparte. La IA escribió código, bajó datos y redactó borradores; las decisiones de método
las tomó el grupo (ver `decisiones.md`). La verificación a mano de la ETo
está en `punto1/dia_verificado_a_mano.xlsx`.

Formato de cada fila: qué se pidió, qué hizo la IA, qué decidió o revisó el grupo.

## Punto 1

| Fecha | Pedido | Qué hizo la IA | Qué decidió o revisó el grupo |
|---|---|---|---|
| 2026-11-12 | Elegir puntos de ERA5-Land para la ET | Propuso opciones de puntos y pesos (Voronoi de áreas iguales A–C, por franjas de altura D–E) con mapas | Juan eligió la opción E y descartó la igualdad de áreas |
| 2026-11-12 | Descargar ERA5-Land en los 6 puntos | Escribió el script 01; la descarga corrió en el PC de Juan con su clave del CDS | Variables y período 1998–2022; días en hora local (UTC−5) |
| 2026-11-12 | Rn y ETo de FAO-56 | Scripts 02–04: series mensuales, Rn diaria (ec. 21–40), ETo (ec. 6) y promedio de cuenca | α = 0.23, G = 0, Rnl sin el límite de ASCE-EWRI |
| 2026-11-13 | Presión real de vapor | Explicó la diferencia entre promediar e°(Td) horaria y la ec. 14 literal | Juan eligió el promedio horario |
| 2026-11-17 | Plan del punto 1 y tablero | Copió el plan a `temp/` y armó un tablero de avance | — |
| 2026-11-17 | Auditar las fases 0 a 2 | Revisó las 16 casillas del plan; hizo el script 04b (ETo con medias mensuales, alturas frente al DEM) y el 04c (día a mano) | Revisar la hoja del día a mano queda a cargo del grupo |
| 2026-11-17 | Bajar productos de ET y estaciones | Scripts 05–11: TerraClimate, ERA5-Land suelo y balance mensual, SSEBop v6.1 y v5, MOD16A2GF, GLEAM v4.3a; brillo solar, T, HR y viento de DHIME | ETo en 1998–2022; no hay torre de flujo útil |
| 2026-11-17 | Cerrar los pendientes de la auditoría | Movió este registro de decisiones a `anexos/`; escribió `verificar_entrega.py`, `requirements.txt`, el inventario de la Tarea 1, los .meta.json (script 00) y la comprobación del error de ECMWF (script 04d) | Juan: Voronoi en 3–4 palabras; γ con la presión de cada punto; recortar el ERA5-Land mensual a 2022-08 |

## Punto 2

Lo trabaja la compañera de Juan; su parte de la bitácora se agrega aparte.

## Lo que la IA no hizo

- No eligió métodos, umbrales ni períodos: los propuso con su evidencia y el grupo decidió.
- No sustituye la verificación: el día a mano y la lectura de las fuentes citadas los hace el grupo.
