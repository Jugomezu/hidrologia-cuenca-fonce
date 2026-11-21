# Referencias del punto 1

Lista de trabajo: cada fuente citada en scripts, decisiones o informe. Formato APA 7. Se completa a medida que se cita.

- Allen, R. G., Pereira, L. S., Raes, D. y Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop
  water requirements* (FAO Irrigation and Drainage Paper 56). FAO. https://www.fao.org/3/x0490e/x0490e00.htm. Usado: cap. 3, ec. 7, 8, 11–14, 17, 21–25, 34, 35,
  37–40, 42–44 y 47. La ec. 35 (Angstrom) está en la p. 50.
- Instituto de Hidrología, Meteorología y Estudios Ambientales [IDEAM]. (2024). *Manual del observador meteorológico*
  (Código GDI-M003, versión 03, fecha del documento 07/07/2025). Subdirección de Meteorología. Usado: altura de 10 m de
  los sensores de viento, p. 37 (viento de Mogotes-AUT, script 13).
- Abatzoglou, J. T., Hegewisch, K. C., Yin, C. y Kalashnikov, D. A. (2026). TerraClimate v1.1, an updated global
  climate and climatic water balance dataset with climate scenarios. *Scientific Data*. Datos: Zenodo,
  https://doi.org/10.5281/zenodo.23961197 (referencia tal como la trae el archivo; volumen y páginas pendientes).
  Usado: pet (ETo de referencia) y aet, scripts 05, 14 y 16.
- Abatzoglou, J. T., Dobrowski, S. Z., Parks, S. A. y Hegewisch, K. C. (2018). TerraClimate, a high-resolution global
  dataset of monthly climate and climatic water balance from 1958–2015. *Scientific Data, 5*, 170191.
  https://doi.org/10.1038/sdata.2017.191. Usado: definición de la pet (versión original): «Monthly reference
  evapotranspiration (ET0) was calculated using the Penman Montieth approach» y «ET0 assumes a reference grass surface».
  El texto no dice si es FAO-56 o ASCE, ni da altura del pasto, albedo ni resistencia de superficie (leído en PMC,
  PMC5759372, 2026-11-20).
- Yang, Y., Roderick, M. L., Zhang, S., McVicar, T. R. y Donohue, R. J. (2019). Hydrologic implications of vegetation
  response to elevated CO2 in climate projections. *Nature Climate Change, 9*(1), 44–48.
  https://doi.org/10.1038/s41558-018-0361-0. Publicado en línea en 2018 (por eso la página de TerraClimate dice 2018).
  Usado: corrección por CO2 de la resistencia de superficie en la pet de TerraClimate v1.1. Datos tomados de la ficha
  RePEc/IDEAS; el texto completo no se leyó.

## Fase 4 · Métodos (script 21)

Cada DOI se comprobó en Crossref el 2026-11-20 (título, revista, volumen y páginas) y los enlaces sin DOI abrieron ese
día. «Leído» dice qué parte del contenido se comprobó contra lo que afirmamos.

- Brutsaert, W. y Stricker, H. (1979). An advection-aridity approach to estimate actual regional evapotranspiration.
  *Water Resources Research, 15*(2), 443–450. https://doi.org/10.1029/WR015i002p00443. Usado: relación complementaria
  AA. Leído: no (la página de la revista no abrió); la ecuación ET = 2 ETw − ETp, con ETw de Priestley–Taylor y ETp de
  Penman, se toma de las notas del curso (Hoyos), Parte 7.
- Doorenbos, J. y Pruitt, W. O. (1977). *Guidelines for predicting crop water requirements* (FAO Irrigation and
  Drainage Paper 24, ed. revisada). FAO. https://www.fao.org/4/f2430e/f2430e.pdf. Usado: forma FAO-24 de la función de
  viento de Penman, f(u) = 0.27 (1 + U2/100), con U2 el recorrido del viento a 2 m en km/día y el déficit en mbar. Leído:
  sí, p. 16–17 (lo dicen también las notas del curso). El título se leyó de un PDF con OCR dañado: confirmarlo a mano.
- Hargreaves, G. H. y Samani, Z. A. (1985). Reference crop evapotranspiration from temperature. *Applied Engineering in
  Agriculture, 1*(2), 96–99. https://doi.org/10.13031/2013.26773. Leído: el artículo no; la ecuación coincide con FAO-56
  ec. 52, ETo = 0.0023 (Tmedia + 17.8)(Tmáx − Tmín)^0.5 Ra, con Ra en mm/día (p. web del cap. 3, x0490e07): por eso el
  script multiplica Ra en MJ/m²·día por 0.408.
- Hoyos, C. D. (s. f.). *Evapotranspiración* [notas del curso de Hidrología]. Universidad Nacional de Colombia.
  https://carlosdhoyos.github.io/cursos/hidrologia/evapotranspiracion.html. Usado: ecuaciones de Hargreaves,
  Priestley–Taylor, Makkink, Penman (forma FAO-24) y AA tal como se dan en el curso (Partes 2, 6 y 7). Leído: sí.
- Jaramillo Robledo, A. (2006). Evapotranspiración de referencia en la región Andina de Colombia. *Cenicafé, 57*(4),
  288–298. Leído: sí, completo. https://cenicafe.org/es/publications/arc057(04)288-298.pdf (también en
  https://www.scribd.com/document/519656789/arc057-04-288-298). Usado: ETo = 4.37·exp(−0.0002 h), ec. 1, p. 292.
  No tiene DOI.
- Makkink, G. F. (1957). Testing the Penman formula by means of lysimeters. *Journal of the Institution of Water
  Engineers, 11*, 277–288. Sin DOI ni enlace en línea encontrado: la ecuación se toma de las notas del curso (Hoyos),
  Parte 7. FAO-24 (Doorenbos y Pruitt, 1977) dice que su método de radiación es una adaptación de la fórmula de
  Makkink (1957). Leído: no.
- Penman, H. L. (1948). Natural evaporation from open water, bare soil and grass. *Proceedings of the Royal Society of
  London. Series A, 193*(1032), 120–145. https://doi.org/10.1098/rspa.1948.0037. Leído: no; se usa la forma de
  FAO-24 (arriba).
- Priestley, C. H. B. y Taylor, R. J. (1972). On the assessment of surface heat flux and evaporation using large-scale
  parameters. *Monthly Weather Review, 100*(2), 81–92.
  https://doi.org/10.1175/1520-0493(1972)100<0081:OTAOSH>2.3.CO;2. Leído: solo el resumen, que no da α = 1.26; el valor
  se toma de las notas del curso (Partes 2 y 7). Falta verlo en el texto del artículo.
