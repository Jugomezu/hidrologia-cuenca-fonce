# Control de calidad de los datos — plan por pasos

## Contexto
El taller pide una sección de control de calidad con cuatro puntos: completitud, control básico,
anomalías y trazabilidad. Cierra con una sección de coherencia hidrológica. Buena parte ya está hecha
y repartida en el notebook y en el informe. La idea es no rehacer nada: lo que existe se cita o se
reutiliza, y solo se agrega lo que falta.

Cada paso se hace en dos lugares:
- en el notebook, como un punto nuevo, **«4. Control de calidad de los datos»**, con subsecciones
  4.1 a 4.5; el número se cambia si el taller usa otro;
- en el informe (`scripts/18_reporte_html.py`), como resumen.

Después de cada paso se republica el informe. Se espera la aprobación del usuario antes de pasar al
siguiente.

**Resaltado para revisión (pedido del usuario):** todo lo que se agregue o cambie en el informe durante
esta sección va dentro de `<div class="revision" data-etiqueta="Revisión 4.x · …">`, un bloque de fondo
amarillo con etiqueta. Cuando el usuario lo apruebe, se quita el resaltado.

**Estado:** 4.1 hecho y revisado (2026-09-28), resaltado quitado; además, ETP propia (Hargreaves con ERA5-Land,
sección 1.8) adoptada en todo el proyecto. 4.2 hecho y revisado (2026-09-28), resaltado quitado. En el informe no se nombran los puntos (4.x): se nombran las secciones. 4.3 hecho (2026-09-29), resaltado pendiente de revisión. Siguen 4.4 y 4.5.

## Lo que ya está hecho (se cita, no se repite)
- **Mapa de días válidos por mes, para todas las variables:** en el informe, «Qué meses tienen dato y
  cuáles no», con el porcentaje de días, los días consecutivos y una tabla de meses utilizables,
  incompletos y perdidos. En el notebook, la 1.4 lo cubre solo para PI y Q.
- **Regla de completitud:** la función única `a_mensual`, con 5 o más días faltantes, se aplica en todo
  el proyecto.
- **Atípicos:** la sección «Revisión de outliers», con Tukey 1.5 por mes del calendario, sin eliminar
  nada, cruzada con Q, las temperaturas y el ONI.
- **Anomalías ya resueltas:**
  - Encino 2016–2018, excluido;
  - sesgo de PI frente a PL, que se arrastra;
  - MSWX, reemplazada por ERA5-Land;
  - área de CAMELS-COL un 1.2 % mayor;
  - `equi_slope` de CAMELS-COL.

## Hallazgo antes de empezar (entra en el paso 1)
Dos series se **suman** con `a_mensual(..., "sum")` aunque la regla permita hasta 4 días faltantes:
- Q en mm: notebook 1.3 y `18_reporte_html.py:207`;
- ETP: `16_correlaciones_variables.py:76`.

Un mes al que le faltan días queda entonces como una suma parcial presentada como acumulado completo,
justo lo que el punto 1 prohíbe. Q en m³/s y las temperaturas se promedian, así que no tienen el
problema. PI y PL llegan ya mensuales.

---

## Paso 1 — Completitud (4.1)
1. Corregir las sumas parciales: el acumulado del mes pasa a ser la **media de los días con dato por
   los días del mes**. Se usa la misma función `a_mensual`, con una opción nueva o con un cálculo
   explícito. Se cambia en el notebook, en el script 16 y en el script 18.
2. Contar cuántos meses cambian y cuánto se mueven las cifras que dependen de ellos, por ejemplo el
   «59 % de la lluvia sale como caudal» de la 1.3.
3. En el notebook, ampliar la tabla de la 1.4 a todas las variables: días válidos por año y mes, meses
   conservados y meses excluidos.
4. Justificar el criterio de forma explícita: por qué 4 días, cuántos meses se recuperan (215 → 262) y
   por qué, con el escalado, un mes incompleto ya no es una suma parcial.
5. En el informe: agregar a «Qué meses tienen dato» la justificación y la nota sobre las sumas.

## Paso 2 — Control de calidad básico (4.2)
Una celda o un script que, para cada serie cruda (CAMELS-COL diario, DHIME, IMERG, ERA5-Land), revise:
- **Fechas:** rango, días ausentes, **fechas duplicadas** y orden.
- **Códigos de faltante:** buscar −999, −9999, 9999 y similares en los crudos.
- **Negativos y rangos según la física de cada variable:**
  - P, Q y ETP ≥ 0;
  - T puede ser negativa, pero con un rango plausible para la altura de la cuenca;
  - T máx ≥ T mín.
- **Unidades:** confirmar m³/s, mm y °C. En ERA5-Land, la conversión de K a °C.
- **Banderas:**
  - `nivel_aprobacion` de DHIME: cuántos meses son preliminares;
  - qué trae IMERG y qué trae CAMELS-COL; si una fuente no trae banderas, se dice.
- **Tabla de naturaleza de cada fuente:** medido, estimado por satélite, reanálisis o modelado, y si hay
  valores rellenados. Se usa lo que dicen la documentación de CAMELS-COL
  (`00_CAMELS-COL Description.docx`) y `DATOS_FUENTES.md`. Lo que no se pueda confirmar queda como «no
  documentado».
- **Revisión a mano de un mes completo:** Q de San Gil en un mes, con sus días listados, la suma, la
  conversión de m³/s a mm con el área y la comparación con el valor que usa el análisis. Además, un mes
  de PI desde el archivo de IMERG y uno de temperatura desde ERA5-Land.

## Paso 3 — Anomalías (4.3)
- **Saltos bruscos:** curva de **doble masa** de cada pluviómetro contra el resto de la red, y de Q
  contra PL, más una prueba de cambio de nivel (Pettitt).
- **Secuencias constantes:** rachas de días con el mismo valor exacto en Q y en las temperaturas
  diarias, y rachas largas de ceros en la lluvia.
- **Extremos aislados:** remitir a «Revisión de outliers», dejando explícito que no se eliminó ningún
  valor por salirse de los bigotes.
- **Cambios de cobertura:** cuántos pluviómetros aportan a PL cada mes a lo largo del tiempo, y si un
  cambio en la red mueve el promedio.
- **Metadatos:** para cada salto sospechoso, consultar el catálogo del IDEAM (instalación, estado,
  categoría) y las versiones de los productos (IMERG V07, ERA5-Land).

## Paso 4 — Trazabilidad (4.4)
Una tabla de registro, definida en el código, con las columnas anomalía, comprobación hecha, decisión,
efecto en el análisis y estado (**corregido** o **incierto**).
- Empieza con lo que ya se decidió: Encino, sesgo PI–PL, MSWX, área, `equi_slope`, las sumas parciales
  del paso 1, jul 1998 y jul 2001 en PI, feb 1999, etc.
- Se completa con lo que salga de los pasos 2 y 3.
- En el informe va como una sección retraíble.

## Paso 5 — Coherencia hidrológica (4.5)
- Residuo mensual y anual Pm − Rm, con PL y con PI, junto a la ETP. Se hace sin afirmar que el residuo
  sea evapotranspiración y se explica por qué: almacenamiento y otros intercambios.
- Los meses con Rm > Pm: cuántos hay, en qué época del año y si siguen a meses lluviosos (liberación de
  almacenamiento). No se tratan como error.
- Se reutiliza «Lo que le cae a la cuenca y lo que sale por el río» del informe en lugar de duplicarla.

## Verificación en cada paso
- El notebook corre completo sin errores.
- `python scripts/16_correlaciones_variables.py` y `python scripts/18_reporte_html.py` corren sin
  errores.
- `node --check` sobre los `<script>` extraídos del informe.
- Capturas con Playwright de la sección nueva, en tema claro y oscuro.
- Las cifras del texto salen del cálculo, nunca escritas a mano, y se revisan con una lectura directa
  del CSV.
- Republicar el informe en el mismo artifact.

## Pendiente para más adelante (fuera de esta sección)
- **Índice de flujo base (BFI).** Se quitó del informe el 2026-09-28: el 0.70 venía de CAMELS-COL
  (filtro de Ladson et al., 2013, período y manejo de huecos no documentados) y el texto lo
  sobreinterpretaba como «agua del almacenamiento». Se retoma con el análisis de Fourier, calculando un BFI
  propio sobre 1998-2022 y citando a Ladson et al. (2013).
