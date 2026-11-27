# Crítica de tus textos de resultados (punto 1)

Hecha con el prompt de la fase 11: no reescribe nada, solo señala. Las letras son las del plan:
(a) afirmación sin cifra, figura o cita; (b) proceso sin contraste con tus datos; (c) sin incertidumbre o limitación;
(d) falta explicación alternativa; (e) mezcla de ETo, ETP, E0 y ET; (f) figura no citada.
Entre corchetes va la evidencia que ya existe en `productos/punto1/` por si la quieres usar.

En el informe tus textos están tal cual (solo pasados a LaTeX). La única cifra cambiada es la HR de Hargreaves, que ya
es 79.3 % (script 30, tu decisión del 24 nov).

## Fase 4 (respuestas del punto de control)

- (a) «nuestra cuenca es húmeda y tiene poco viento»: falta la cifra. [HR 79.3 %; u2 medio 0.62 m/s, `tendencias_demanda.csv`]
- Ojo con la redacción de la respuesta 3. Que el sesgo de Makkink quede dentro de la dispersión significa que no se
  distingue de la incertidumbre de la referencia. No significa que el error venga «de problemas con los datos».
- Usé las respuestas 1 y 3. La 2 no la puse porque es general y no habla de la cuenca.

## Fase 5 (diferencias entre métodos)

- **Penman.**
  - (a) El R² de 0.991 no sale de ningún script. Tampoco hay cifra para «calibrando c ambas series se vuelven similares».
  - (b) Atribuir la diferencia al viento no lo apoyan tus datos. Con u2 +10 %, Penman sube 0.5 % y la ETo 0.1 %.
    Donde más se separan es en la respuesta al déficit de vapor: con T +1 °C y ea constante, Penman sube 4.7 % y la
    ETo 3.2 %; con ea +10 %, Penman baja 3.8 % y la ETo 1.3 % (Fig. 6).
  - (d) Explicación alternativa: FAO-24 no tiene resistencia de superficie y su función de viento es empírica.
- **Makkink.**
  - (a) «muy bueno cuando el limitante es la radiación» no tiene cita.
  - (b) Tu argumento se puede cerrar con números. El término aerodinámico pesa 7.6 % de la ETo y Makkink queda a −3.1 %.
    Además, Makkink es el método más sensible a Rs (−10.4 % con Rs −10 %, frente a −7.6 % de la ETo; Fig. 6).
- **Hargreaves.** (d) Falta una alternativa a la HR alta. Por ejemplo: la amplitud térmica de ERA5-Land en celdas de
  9 km puede no ser la de la estación. También puedes comparar con el Hargreaves de la Tarea 1 (script 23).
- **Cenicafé.**
  - (c) «aproximación decente»: el sesgo va de −18.5 % a −3.5 % según el mes y solo 2 de 12 meses caen dentro de la
    dispersión (Tabla 1).
  - (a) Las «dos estaciones en Santander» necesitan cita con página (Jaramillo 2006).
- **Priestley–Taylor.**
  - (b) Falta decir por qué queda +16.5 %. Tus datos lo explican: el α que pediría esta cuenca con rs = 0 es
    α* = 1.08 (1.07 a 1.10 según el mes), no 1.26 [`alfa_implicito_ciclo.csv`, columna alfa_rs0].
  - (a) «se podría calibrar fácilmente»: dale el número, α ≈ 1.08.
- **Thornthwaite.**
  - Bien planteado. Puedes amarrarlo a la fase 8: Thornthwaite cambia 10.3 % por cada °C y la ETo 3.2 % (Fig. 6).
    Por eso detecta una tendencia que la ETo no tiene.
  - (e) Si lo comparas con la ETo, dilo en una frase: se trata como ETo porque no tiene conversión.
- **α\*.** (a) Las correlaciones 0.95 y 0.78 no salen de ningún script (ya estaba en la auditoría de fases 0–5).
- (f) No citas ninguna figura ni tabla: Fig. 4 (métodos), Tabla 1, Fig. 5 (términos y α*) ni Fig. 6 (sensibilidad).

## Fase 7 (índice de aridez y fracción evaporativa)

- **Índice de aridez.**
  - Contradicción: dices que febrero «está sobre el límite», pero su φ medio es 0.76. Lo que lo acerca al límite es
    que tiene φ > 1 en el 44 % de los años. Conviene decirlo así.
  - (c) Falta el matiz que acordamos: φ > 1 en un mes dice que la lluvia no cubre la demanda, no que la ET esté
    frenada. En enero ET/ETo sigue en ≈ 0.90.
- **Fracción evaporativa.**
  - (c) Faltan la R² de 0.16 y el rango de EF (0.57 a 0.64).
  - (c) θ* = 0.452 es el borde de la búsqueda, no un quiebre encontrado.
  - (d) Alternativa: no ves el quiebre porque SMrz de GLEAM casi no pasa de 0.45, es decir, el producto no explora
    suelos secos. Otra posibilidad: los productos de ET ya traen su propio modelo de estrés.
  - (a) «La cuenca no está limitada por agua» debería apoyarse explícitamente en Budyko (φ = 0.49, Tabla 3) y en
    ET/ETo ≈ 0.90.
- (f) No citas las Figs. 8 y 9 ni la Tabla 3.

## Fase 8 (tendencias)

- (c) «no tiene tendencia» está mejor como «no se detecta tendencia». Dale el intervalo de Sen: de −11 a +18 mm/año
  por década (IC 95 %) [`tendencias_demanda.csv`].
- (b) y (d) Falta el mecanismo. La T sube +0.21 °C por década (MK p 0.012). La ETo responde poco a T (3 %/°C) y
  Thornthwaite mucho (10 %/°C). En la atribución, T aporta +6.1 mm/año por década y la compensan en parte Rs (−1.6) y
  ea (−0.9). Tú dejaste la atribución «en veremos»; basta con una frase.
- Thornthwaite sí pasa el control de FDR con MK (q 0.045) y no con OLS. Dilo, porque es lo que justifica «detectable
  pero pequeña».
- (f) Cita la Fig. 10.

## Lo que todavía no tiene texto tuyo

La ETo y lo que la controla (Fig. 1), las pruebas de la referencia (Figs. 2 y 3), la ET real con su incertidumbre
(Fig. 7, Tabla 2), la fase 9, las conclusiones y la contribución de cada integrante.
