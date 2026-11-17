# Auditoría de las fases 0 a 2 del punto 1 (2026-11-17)

Recorrido de las 16 casillas de `temp/PLAN_PUNTO1_evapotranspiracion.md`. ✓ cumple · ◐ a medias · ✗ falta.

| # | Casilla | Estado | Evidencia o lo que falta |
|---|---|---|---|
| 1 | `verificar_entrega.py` pasa | ✗ | No existe `codigo/verificar_entrega.py`. Tampoco `codigo/requirements.txt`. |
| 2 | Inventario de la Tarea 1, con longitud y pendiente del cauce | ✗ | No existe `anexos/inventario_t1.md`. |
| 3 | Misma ponderación espacial que la Tarea 1 [M05] | ◐ | Se pondera por Voronoi (decisiones, 2026-11-12). La Tarea 1 ponderó IMERG por área de celda y promedió los pluviómetros sin pesos. Falta decidir si se declara como equivalente o como distinta, y escribirlo. El código que eligió los puntos no está en el repo. |
| 4 | Tmáx y Tmín horarias; es = media de e°(Tmáx) y e°(Tmín) [M10] | ✓ | `03_series_diarias_rn.py`, `04_eto_fao56.py` (ec. 12). |
| 5 | ea con el punto de rocío [M11] | ✓ | Promedio diario de e°(Td) horario (decisiones, 2026-11-13). |
| 6 | Viento: magnitud horaria, ec. 47 y qué supone [M12] | ◐ | Cálculo bien. Falta escribir qué supone la ec. 47 (perfil logarítmico sobre pasto de 0.12 m). |
| 7 | Rn con α = 0.23; Rn de ERA5-Land guardada aparte [M13] | ◐ | Rn del pasto bien. La radiación neta de ERA5-Land no se descargó; la fase 6 la necesita (descarga en el PC). |
| 8 | G = 0 diario; γ con la presión de la elevación media [M14] | ◐ | G = 0 bien. γ usa la `sp` de cada punto, no la de la elevación media de la cuenca: es una decisión (2026-11-12) que difiere del plan y hay que declararla así. |
| 9 | Elevación de los puntos frente al DEM, efecto en T y ea [M15] | ✓ | Hecho hoy: `04b_comprobaciones_eto.py` → `anexos/punto1/elevacion_puntos_dem.csv`. |
| 10 | Cálculo con medias mensuales y G ec. 43, diferencia por mes [K02, F02] | ✓ | Hecho hoy: `04b` → `anexos/punto1/eto_medias_mensuales_vs_suma_diarias.csv`. Falta la figura. |
| 11 | Un día a mano en hoja de cálculo [K01] | ◐ | Hoja hecha hoy: `anexos/punto1/dia_verificado_a_mano.xlsx`. Falta que el grupo la revise. |
| 12 | Convenciones de ERA5-Land: acumulación y advertencia de ECMWF sep-2022–feb-2024 [M07] | ◐ | Acumulación revisada (decisiones, nota de radiación horaria). La advertencia de ECMWF no está revisada ni escrita. |
| 13 | Cada archivo de datos con su `.meta.json` [R08] | ✗ | Solo hay `metadatos_descarga.json` por carpeta en ERA5-Land y TerraClimate; ningún `.meta.json` por archivo; nada en el brillo solar ni en la copia de la Tarea 1. |
| 14 | Periodo de la ETo | ✓ | 1998–2022 (decisiones, 2026-11-17). |
| 15 | Decisiones en `anexos/decisiones.md` | ✗ | Sigue en `temp/decisiones.md`. |
| 16 | Bitácora de IA | ✗ | No existe `anexos/bitacora_ia.md`. |

Numeración: 01 descarga, 02 mensuales y 03–04 Rn y ETo son de las fases 1 y 2; 04b y 04c son comprobaciones de la fase 2;
05 es TerraClimate (fases 3 y 6).
