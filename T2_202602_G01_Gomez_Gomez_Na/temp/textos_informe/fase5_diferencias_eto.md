# Fase 5 · Explicación de las diferencias entre métodos de ETo

Texto de Juan (23 nov 2026), con correcciones de ortografía y forma. Para el informe.

En esta sección se compararán los métodos de ETo (evapotranspiración de referencia) anual de los métodos elegidos.

**Penman:** Para la actividad se calculó la ETo con este método usando c = 0.8, como sugiere FAO-24 (p. 15). Este método es muy similar al Penman–Monteith de FAO-56 con el que estamos comparando, tanto que tienen una correlación anual R² de 0.991, con Penman sistemáticamente por debajo, posiblemente porque el coeficiente *c* que propone FAO-24 puede ser muy bajo para esta cuenca. Ambos métodos son tan similares porque son ambos modificaciones o adaptaciones del método original de Penman.

La diferencia más importante en los valores de estos dos métodos se debe a diferencias en el viento y en la elección de c, pues calibrando con este factor ambas series se vuelven similares, y sus comportamientos diferentes se podrían entonces atribuir al viento.

**Makkink:** Este método utiliza solo T y Rs, por lo que no tiene en cuenta el componente de viento o la humedad. Esto hace que el método de Makkink sea muy bueno cuando la humedad no es un factor limitante y el viento es más bien bajo, pero lo más importante es que el limitante sea la radiación.

En nuestro caso el componente aerodinámico de Penman–Monteith es una parte pequeña del total, pero podría explicar la pequeña diferencia que hay entre estos dos métodos, pues Makkink ignora el componente aerodinámico. El método intenta compensar eso con sus coeficientes, que lo ajustan a las condiciones aerodinámicas de la zona donde fue calibrado, y por eso la diferencia entre FAO-56 y Makkink no es tan grande como todo el término aerodinámico de FAO-56, pero igual hay diferencias porque la cuenca está en una zona que no es donde se calibró el método.

**Hargreaves:** Este método utiliza Tmáx, Tmín y Ra para calcular la ETo. Es muy útil para los casos en los que no se tiene mucha información climática de la zona, como por ejemplo en la Tarea 1, en la que solo contábamos con datos de temperatura y la ubicación de la cuenca. El valor de este método da por encima del valor obtenido con Penman–Monteith (+10 %); esto se puede deber a que Hargreaves tiende a sobreestimar la ETo en condiciones de HR alta (FAO-56, p. 64), y en nuestra cuenca la humedad relativa promedio es de 79.4 % (promedio simple de 5 estaciones del IDEAM).

**Cenicafé:** Este método usa solo la altitud, entonces da un valor diario fijo de ETo que no tiene en cuenta fluctuaciones. En la gráfica mensual se ven fluctuaciones porque cambia la cantidad de días en el mes. Este método es especialmente útil en los Andes colombianos, pues fue calibrado con estaciones en esta zona, incluyendo dos en Santander, y tiene la ventaja de que no necesita ningún dato más allá de la altitud y da una aproximación decente con muy pocos datos (−12 % respecto a Penman–Monteith). La desventaja es que ignora las fluctuaciones porque es un valor constante diario.

**Priestley–Taylor:** Priestley–Taylor no es la ET de un pasto de referencia (ETo), sino la de una superficie húmeda sin rs. Para compararla con Penman–Monteith, hacemos el ajuste calculándolo con rs = 0, en vez del que se calcula según FAO-56. Al hacer esta comparación vemos que tienen formas muy similares, con una diferencia estable entre ambos métodos. Esto sugiere que se podría calibrar fácilmente para dar resultados muy similares a los de Penman–Monteith sin rs.

Pendiente: el promedio de HR de las 5 estaciones (79.4 %) aún no está en un script.
