# Fase 8: conclusión de Juan (24 nov)

La ETo Penman–Monteith (FAO-56) no tiene tendencia en 1998–2022 (Sen +3 mm/año por década, p 0.68).
En Thornthwaite la tendencia es estadísticamente detectable con Mann-Kendall (p 0.015), pero pequeña en magnitud:
+16 mm/año por década, cerca de 2 % por década; OLS con Newey-West no la confirma (p 0.086).

Cifras: productos/punto1/tendencias_demanda.csv (script 32).

## Con 1981–2022 (Juan, 24 nov, 9:31 p. m.)

Se reporta 1981–2022. La ETo sube +9.5 mm/año por década (0.8 %/década), significativa con todas las pruebas. Para la
Rs, su tendencia puede venir solo de defectos de los datos del reanálisis (escalón hacia 1999–2001), más que de una
tendencia real.

## Con 1981–2022 y la Rs corregida (Juan, 26 nov, 1:09 p. m.)

El control de calidad (script 42, como la Tarea 1) halló un escalón de Rs de +0.317 MJ/m²·d después de 2000 frente a
la lluvia de CHIRPS (Pettitt p 0.013). Juan decidió corregirlo: se suma a la Rs de antes de 2001 y se recalculan Rn y la
ETo (script 36, solo fase 8). Resultado: ETo +4.2 mm/año por década (+0.37 %), no significativa (OLS Newey-West p 0.15,
Mann-Kendall p 0.15). Thornthwaite +10.6 mm/año por década y T +0.14 °C/década, significativas. Atribución: T +5.5,
ea −0.6, u2 −0.1, Rs −0.6 mm/año por década. Sin corregir (sensibilidad): ETo +9.5, significativa.
