# Referencias del punto 1

Lista de trabajo: cada fuente citada en scripts, decisiones o informe. Formato APA 7. Se completa a medida que se cita.
Auditoría de citas del 2026-11-21: cada entrada dice qué se leyó y si dice lo que afirmamos. «No leído» = solo se
comprobó que la referencia existe.

## Fuentes de método (fases 0–3)

- Allen, R. G., Pereira, L. S., Raes, D. y Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop
  water requirements* (FAO Irrigation and Drainage Paper 56). FAO. ISBN 92-5-104219-5.
  https://www.fao.org/3/x0490e/x0490e00.htm. Usado: cap. 3, ec. 7, 8, 11–14, 17, 21–25, 34, 35, 37–40, 42–44, 47 y 52;
  cap. 2, ec. 6 y recuadro 4. La ec. 35 (Angstrom) está en la p. 50 del PDF (verificada por Juan). Leído (versión web,
  cap. 2 y 3, 2026-11-21): cada número de ecuación corresponde a lo que decimos; a_s = 0.25 y b_s = 0.50 sin
  calibración (ec. 35); 2 m/s como estimación temporal sin datos de viento; ec. 39 con Rs/Rso ≤ 1.0 (el script 03 lo
  aplica); ec. 47 «above a short grassed surface». d = 0.08 m y z0m = 0.0148 m no están impresos: salen del recuadro 4
  (d = 2/3 h, z0m = 0.123 h) con h = 0.12 m.
- Instituto de Hidrología, Meteorología y Estudios Ambientales [IDEAM]. (2024). *Manual del observador meteorológico*
  (Código GDI-M003, versión 03, fecha del documento 07/07/2025). Subdirección de Meteorología.
  https://www.ideam.gov.co/sites/default/files/mapa-de-procesos/gdi-m003_manual_del_observador_meteorologico_0.pdf.
  Usado: altura de 10 m de los sensores de viento (viento de Mogotes-AUT, script 13). Leído: p. 37, sección 4.6.2, «En
  el territorio colombiano los sensores de viento se encuentran emplazados sobre un mástil a una altura de 10 m». La
  portada dice julio de 2024 y la versión 03 es del 07/07/2025; antes el código era M-GDI-M-M003 (la versión 1, de
  2019, lo dice en la p. 63).
- ASCE-EWRI. (2005). *The ASCE standardized reference evapotranspiration equation* (R. G. Allen, I. A. Walter, R.
  Elliott, T. Howell, D. Itenfisu y M. Jensen, eds.). American Society of Civil Engineers.
  ISBN 978-0-7844-0805-6 (copia del informe final: https://epic2-clone.awi.de/42362/1/ascestzdetmain2005.pdf).
  Usado: límite 0.3 < Rs/Rso ≤ 1.0 de fcd (ec. 18, p. 20), que no se aplica (decisión del 2026-11-12). Leído: portada
  y editores; la frase de la p. 20 se leyó en una extracción parcial del PDF, no en el texto completo.
- Abatzoglou, J. T., Hegewisch, K. C., Yin, C. y Kalashnikov, D. A. (2026). TerraClimate v1.1, an updated global
  climate and climatic water balance dataset with climate scenarios. *Scientific Data* (en prensa). Datos: Zenodo,
  https://doi.org/10.5281/zenodo.23961197; página del producto: https://www.climatologylab.org/terraclimate.html.
  Referencia y DOI tal como los trae el archivo; la página de Zenodo no abrió desde aquí. Usado: pet y aet, scripts 05,
  14 y 16. Leído (página del producto, 2026-11-21): pet = «ASCE Penman-Monteith corrected for CO2, Yang et al., 2018»;
  anomalías mensuales «solely from ERA5» sobre la climatología CHELSA. No da superficie, altura, albedo ni resistencia.
- Abatzoglou, J. T., Dobrowski, S. Z., Parks, S. A. y Hegewisch, K. C. (2018). TerraClimate, a high-resolution global
  dataset of monthly climate and climatic water balance from 1958–2015. *Scientific Data, 5*, 170191.
  https://doi.org/10.1038/sdata.2017.191 (texto libre: https://escholarship.org/content/qt9zs322sc/qt9zs322sc_noSplash_5ba59c16956e8db158ab51c507c7785e.pdf).
  Usado: definición de la pet (versión original). Leído (p. 3): «Monthly reference evapotranspiration (ET0) was
  calculated using the Penman Montieth approach» y «ET0 assumes a reference grass surface». No dice FAO-56 ni ASCE, ni
  altura del pasto, albedo o resistencia de superficie.
- Yang, Y., Roderick, M. L., Zhang, S., McVicar, T. R. y Donohue, R. J. (2019). Hydrologic implications of vegetation
  response to elevated CO2 in climate projections. *Nature Climate Change, 9*(1), 44–48.
  https://doi.org/10.1038/s41558-018-0361-0. En línea el 17 de diciembre de 2018 (por eso TerraClimate dice 2018).
  Usado: corrección por CO2 de la resistencia de superficie en la pet de TerraClimate v1.1. Leído: solo el resumen
  (el texto es de pago): relaciona rs con el CO2 y lo incorpora al cálculo de la ETP. La fórmula exacta no se leyó.

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
  sí, p. 16–17 (lo dicen también las notas del curso). c = 0.8 con tiempo en calma: p. 15 (leído por Juan, 22 nov). El título se leyó de un PDF con OCR dañado: confirmarlo a mano.
- Hargreaves, G. H. y Samani, Z. A. (1985). Reference crop evapotranspiration from temperature. *Applied Engineering in
  Agriculture, 1*(2), 96–99. https://doi.org/10.13031/2013.26773. Leído: el artículo no; la ecuación coincide con FAO-56
  ec. 52, ETo = 0.0023 (Tmedia + 17.8)(Tmáx − Tmín)^0.5 Ra, con Ra en mm/día (p. web del cap. 3, x0490e07): por eso el
  script multiplica Ra en MJ/m²·día por 0.408. Que Hargreaves tiende a sobrestimar la ETo con HR alta: FAO-56, p. 64
  (leído por Juan, 23 nov).
- Hoyos, C. D. (s. f.). *Evapotranspiración* [notas del curso de Hidrología]. Universidad Nacional de Colombia.
  https://carlosdhoyos.github.io/cursos/hidrologia/evapotranspiracion.html. Usado: ecuaciones de Hargreaves,
  Priestley–Taylor, Makkink, Penman (forma FAO-24) y AA tal como se dan en el curso (Partes 2, 6 y 7). Leído: sí.
- Jaramillo Robledo, A. (2006). Evapotranspiración de referencia en la región Andina de Colombia. *Cenicafé, 57*(4),
  288–298. Leído: sí, completo. https://cenicafe.org/es/publications/arc057(04)288-298.pdf (también en
  https://www.scribd.com/document/519656789/arc057-04-288-298). Usado: ETo = 4.37·exp(−0.0002 h), ec. 1, p. 292.
  No tiene DOI.
- Makkink, G. F. (1957). Testing the Penman formula by means of lysimeters. *Journal of the Institution of Water
  Engineers, 11*, 277–288. Sin DOI ni enlace en línea encontrado: la ecuación se toma de las notas del curso (Hoyos),
  Parte 7. Leído: no (el original no está en línea). Lo que sí se leyó: FAO-24 (Doorenbos y Pruitt, 1977), p. 8,
  dice «The Radiation Method is essentially an adaptation of the Makkink formula (1957)» y su método de radiación,
  ETo = c (W · Rs), estima la ETo del pasto de referencia (8 a 15 cm, bien regado). W es el factor de peso que depende
  de la temperatura y la altura (el mismo papel que Δ/(Δ + γ)); c se lee en la figura 2 según HR media y viento diurno.
  FAO-24 no da las constantes 0.61 y −0.12: esas salen de las notas del curso.
- Penman, H. L. (1948). Natural evaporation from open water, bare soil and grass. *Proceedings of the Royal Society of
  London. Series A, 193*(1032), 120–145. https://doi.org/10.1098/rspa.1948.0037. Leído: no; se usa la forma de
  FAO-24 (arriba).
- Priestley, C. H. B. y Taylor, R. J. (1972). On the assessment of surface heat flux and evaporation using large-scale
  parameters. *Monthly Weather Review, 100*(2), 81–92.
  https://doi.org/10.1175/1520-0493(1972)100<0081:OTAOSH>2.3.CO;2. Leído: solo el resumen, que no da α = 1.26; el valor
  se toma de las notas del curso (Partes 2 y 7). Falta verlo en el texto del artículo.

## Datos (citados en los scripts y en los metadatos)

Comprobado el 2026-11-21 en la página de cada producto, salvo donde se dice.

- Muñoz-Sabater, J., Dutra, E., Agustí-Panareda, A., et al. (2021). ERA5-Land: a state-of-the-art global reanalysis
  dataset for land applications. *Earth System Science Data, 13*(9), 4349–4383. https://doi.org/10.5194/essd-13-4349-2021.
- ECMWF. (2024). *Issue affecting ERA5-Land monthly averaged reanalysis for the period September 2022 to February 2024*
  [foro]. https://forum.ecmwf.int/t/issue-affecting-era5-land-monthly-averaged-reanalysis-for-the-period-september-2022-to-february-2024/2370.
  Leído: afecta todas las variables acumuladas del producto mensual, sep. 2022 a feb. 2024. Respalda el recorte a
  2022-08 del script 07.
- Jimenez, D. A., Meneses, J. E., Bernardes Solha, P. H., Avila Diaz, A., Quesada, B., Brentan, B. M. y Rodrigues,
  A. F. (2026). *CAMELS-COL: A large-sample hydrometeorological dataset for Colombia* (v3) [conjunto de datos]. Zenodo.
  https://doi.org/10.5281/zenodo.18794895. Licencia CC BY 4.0. Artículo en discusión: https://doi.org/10.5194/essd-2025-200.
- Miralles, D. G., Bonte, O., Koppa, A., et al. (2025). GLEAM4: global land evaporation and soil moisture dataset at
  0.1° resolution from 1980 to near present. *Scientific Data, 12*. https://doi.org/10.1038/s41597-025-04610-y.
  Número de artículo sin confirmar.
- Running, S., Mu, Q., Zhao, M. y Moreno, A. (2021). *MODIS/Terra Net Evapotranspiration Gap-Filled 8-Day L4 Global
  500m SIN Grid V061* [conjunto de datos]. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD16A2GF.061. El DOI está en
  la ficha de Earth Engine; autores y año no aparecen ahí (salen de la forma de cita de LP DAAC, no leída).
- Senay, G. B. et al. SSEBop v6.1 (VIIRS, desde 2012), USGS FEWS NET. https://doi.org/10.5066/P9QJWQ6K. La búsqueda
  asocia este DOI a «SSEBop Evapotranspiration Data from 2012 to Present» (USGS), pero la página no abrió: autores y
  año (2023) sin confirmar.
- Senay, G. B. et al. SSEBop v5 (MODIS), USGS FEWS NET. https://doi.org/10.5066/F72V2F1F. El DOI resuelve al portal
  general de FEWS NET, no a una ficha del producto: autores, año y título sin confirmar. La ficha USGS del SSEBop
  operativo global es otra: Senay, Kagone y Velpuri (2020), https://doi.org/10.5066/P9OUVUUI.
- Huffman, G. J. et al. *GPM IMERG Final Precipitation L3 1 month 0.1° V07 (GPM_3IMERGM)*. NASA GES DISC.
  https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07. Heredado de la Tarea 1; solo se comprobó que la ficha existe.
- Servicio Geológico Colombiano. (2023). *Mapa Geológico de Colombia 2023*, escala 1:1 500 000.
  https://www2.sgc.gov.co/MGC/Paginas/mgc_1_5M2023.aspx. Heredado de la Tarea 1.

## Métodos descartados (documento de trabajo) y lecturas del plan

Solo se comprobó que existen y dónde leerlos; no se citan en el informe por ahora.

- Hamon, W. R. (1961). Estimating potential evapotranspiration. *Journal of the Hydraulics Division, 87*(3), 107–120.
  https://doi.org/10.1061/JYCEAJ.0000599.
- Oudin, L., Hervieu, F., Michel, C., et al. (2005). Which potential evapotranspiration input for a lumped
  rainfall–runoff model? Part 2. *Journal of Hydrology, 303*, 290–306.
  https://ludovicoudin.github.io/publications/2005_Journal_of_Hydrology_Oudin_Hervieu.html. Es la parte 2 la que
  propone la fórmula con T media y Ra; datos de la parte 2 sin abrir (la parte 1 sí: 303, 275–289,
  https://doi.org/10.1016/j.jhydrol.2004.08.025).
- Jensen, M. E. y Haise, H. R. (1963). Estimating evapotranspiration from solar radiation. *Journal of the Irrigation
  and Drainage Division, 89*(4), 15–41. https://doi.org/10.1061/JRCEA4.0000287. «Calibrado en zona árida» no se
  confirmó en lo leído.
- Abtew, W. (1996). Evapotranspiration measurements and modeling for three wetland systems in South Florida. *JAWRA,
  32*(3), 465–473. https://doi.org/10.1111/j.1752-1688.1996.tb04044.x. Humedales del sur de Florida: confirmado.
- Blaney, H. F. y Criddle, W. D. (1950). *Determining water requirements in irrigated areas from climatological and
  irrigation data* (SCS-TP-96). USDA Soil Conservation Service.
  https://ia800300.us.archive.org/4/items/determiningwater96blan/determiningwater96blan.pdf.
- Linacre, E. T. (1977). A simple formula for estimating evaporation rates in various climates, using temperature
  data alone. *Agricultural Meteorology, 18*, 409–424. Sin enlace al texto; entradas (Tmáx, Tmín, Td, altitud,
  latitud) según https://www.rdocumentation.org/packages/Evapotranspiration/versions/1.10/topics/ET.Linacre.
- Turc, L. (1961). Évaluation des besoins en eau d'irrigation, évapotranspiration potentielle. *Annales Agronomiques,
  12*, 13–49. Sin enlace al texto encontrado; volumen y páginas sin confirmar.
- Lecturas del plan (temp/PLAN): Milly y Dunne (2016), https://doi.org/10.1038/nclimate3046; Brutsaert y Parlange
  (1998), https://www.nature.com/articles/23845; Wilson et al. (2002), https://ahg.nature.berkeley.edu/wp-content/pubs/Energy.pdf;
  Sankarasubramanian et al. (2001), https://ccee.ncsu.edu/chwr/wp-content/uploads/sites/493/2017/01/2001WRR_elasticity.pdf;
  Roderick y Farquhar (2002), https://researchportalplus.anu.edu.au/en/publications/the-cause-of-decreased-pan-evaporation-over-the-past-50-years/;
  McVicar et al. (2012), https://researchportalplus.anu.edu.au/en/publications/global-review-and-synthesis-of-trends-in-observed-terrestrial-nea/.
  Dingman (2015, *Physical Hydrology*, 3.ª ed.) y Shaw et al. (2010, *Hydrology in Practice*, 4.ª ed.) son libros sin
  enlace libre; las secciones citadas (tabla 6.2, sec. 6.7, 6.8 y 10.3) no se comprobaron.
- Thornthwaite, C. W. (1948). An approach toward a rational classification of climate. *Geographical Review, 38*(1),
  55–. https://doi.org/10.2307/210739 (Crossref solo da la página inicial). Leído: no; la ecuación (I, a y la
  corrección (L/12)(N/30)) se toma de las notas del curso (Hoyos), Parte 7. Script 22.
