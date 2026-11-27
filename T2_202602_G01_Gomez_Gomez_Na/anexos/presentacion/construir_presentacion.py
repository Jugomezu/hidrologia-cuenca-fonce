"""Arma la presentación oral de la Tarea 2 (12 minutos) como un HTML autocontenido.

Uso, desde la carpeta de la entrega:
    python anexos/presentacion/construir_presentacion.py
    node anexos/presentacion/exportar_pdf.js

El primero escribe anexos/presentacion/presentacion.html con las figuras de productos/
incrustadas; el segundo imprime ese HTML a T2_202602_G01_presentacion.pdf en la raíz.

Las cifras son las del informe (anexos/informe_latex/, tablas y macros de productos/*/tablas_informe/):
la presentación no calcula ni agrega resultados. Las figuras son las mismas del informe; a las
que están apiladas en vertical se les muestra solo el panel que se comenta (recorte por CSS,
la imagen no se modifica).
"""

import base64
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]  # carpeta T2_202602_G01_Gomez_Gomez_Na
SALIDA = Path(__file__).resolve().parent / "presentacion.html"


def figura(ruta, alto_px=None, desde=0.0, hasta=1.0, alt=""):
    """Incrusta una figura de productos/. desde/hasta: fracción vertical que se muestra."""
    archivo = RAIZ / "productos" / ruta
    datos = base64.b64encode(archivo.read_bytes()).decode("ascii")
    from PIL import Image  # solo para leer el tamaño

    ancho, alto = Image.open(archivo).size
    alto_visible = alto * (hasta - desde)
    proporcion = ancho / alto_visible
    estilo_caja = f"aspect-ratio:{ancho}/{alto_visible:.0f};"
    if alto_px:
        estilo_caja += f"height:{alto_px}px;width:{alto_px * proporcion:.0f}px;"
    # margin-top en % se mide contra el ancho de la caja: desplaza la imagen al panel pedido
    margen = -desde * alto / ancho * 100
    return (
        f'<div class="fig" style="{estilo_caja}">'
        f'<img alt="{alt}" style="margin-top:{margen:.3f}%" '
        f'src="data:image/png;base64,{datos}"></div>'
    )


# Cada diapositiva: (minutos aproximados, sección, html, notas para quien expone)
DIAPOSITIVAS = []


def diapositiva(minutos, seccion, html, notas):
    DIAPOSITIVAS.append((minutos, seccion, html, notas))


# 1 · Portada ---------------------------------------------------------------------------
diapositiva(0.3, "inicio", f"""
<div class="portada">
  <div class="portada-texto">
    <p class="ceja">Hidrología · Tarea 2 · Semestre 202602 · Grupo G01</p>
    <h1>Evapotranspiración en la cuenca del río Fonce y diseño hidrológico</h1>
    <p class="sub">Cuánta agua devuelve una cuenca andina a la atmósfera, y cómo dimensionar una obra
    de drenaje con lluvia horaria</p>
    <div class="autores"><span>Juan Pablo Gómez</span><span>Andrea Gómez Mahecha</span></div>
  </div>
  <div class="portada-fig">{figura("punto1/mapa_cuenca_estaciones.png", alto_px=930, alt="Mapa de la cuenca del río Fonce")}</div>
</div>
""", "Presentarnos. Dos puntos: la ET de la cuenca del Fonce (Juan) y el diseño de drenaje en Denver (Andrea).")

# 2 · Dos escalas ---------------------------------------------------------------------
diapositiva(0.6, "intro", """
<h2>Dos problemas, dos escalas</h2>
<div class="dos">
  <div class="bloque p1">
    <p class="ceja">Punto 1 · Fonce hasta San Gil (IDEAM 24027010)</p>
    <p class="grande">2 098.85 <small>km²</small></p>
    <p>Lluvia y caudal mensuales, forzantes diarios · 1998–2022 (tendencias 1981–2022)</p>
    <ol class="preguntas">
      <li>¿Cuál es la demanda atmosférica y qué la controla?</li>
      <li>¿Cuánta agua devuelve la cuenca a la atmósfera, y con qué incertidumbre?</li>
      <li>¿En qué meses manda la energía y en cuáles el agua?</li>
      <li>¿Ha cambiado la demanda, y por qué?</li>
      <li>¿Qué proceso distingue a la cuenca?</li>
    </ol>
  </div>
  <div class="bloque p2">
    <p class="ceja">Punto 2 · Microcuenca junto a Denver Stapleton</p>
    <p class="grande">1.0269 <small>km²</small></p>
    <p>Lluvia horaria de una estación · piedemonte semiárido, tormentas convectivas de verano</p>
    <ol class="preguntas">
      <li>¿Qué intensidad tiene cada periodo de retorno, y cómo se compara con NOAA Atlas 14?</li>
      <li>¿Qué alcantarilla pide la microcuenca para T = 50 años, y qué tan sensible es?</li>
      <li>¿Cuánto tanque de detención hace falta tras urbanizar, según el patrón de la tormenta?</li>
      <li>¿Cómo cambian diseño y confiabilidad con costo, excedencias, calentamiento e historia?</li>
    </ol>
  </div>
</div>
""", "El punto 1 es balance de largo plazo en una cuenca grande; el punto 2 es diseño con extremos de minutos en una cuenca de 1 km². Leer las preguntas de cada punto (5 y 4): estructuran lo que sigue.")

# 3 · La cuenca -----------------------------------------------------------------------
diapositiva(0.8, "p1", f"""
<h2>Una cuenca húmeda con 3 000 m de desnivel</h2>
<div class="fig-texto">
  {figura("punto1/mapa_cuenca_estaciones.png", alto_px=860, alt="Cuenca, estaciones y puntos de ERA5-Land")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">1 121–4 299 <small>m</small></span><span>de San Gil al páramo; media 2 264 m</span></div>
      <div><span class="num">2 390 <small>mm/año</small></span><span>lluvia P̄ = (PI + PL)/2: IMERG 2 229, pluviómetros 2 551</span></div>
      <div><span class="num">1 345 <small>mm/año</small></span><span>caudal en San Gil: 56 % de la lluvia</span></div>
      <div><span class="num">1 045 <small>mm/año</small></span><span>el resto se evapotranspira: P̄ − Q</span></div>
    </div>
    <p class="nota">Dos temporadas de lluvia (abril y octubre) por el paso de la ZCIT. Ningún pluviómetro
    está por encima de 2 625 m, donde queda el 30 % de la cuenca.</p>
  </div>
</div>
""", "Lluvia que duplica la demanda (P/ETP = 2.01). Usamos 6 puntos de ERA5-Land (uno por franja de altura de igual área), 7 pluviómetros y 3 estaciones climatológicas. La pregunta de fondo: con tanta lluvia, ¿qué limita la ET?")

# 4 · La demanda ----------------------------------------------------------------------
diapositiva(0.9, "p1", f"""
<h2>La demanda la pone la radiación</h2>
<div class="fig-texto">
  {figura("punto1/terminos_fao56.png", alto_px=560, alt="Términos radiativo y aerodinámico de la ETo por mes")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">1 166 <small>mm/año</small></span><span>ETo Penman–Monteith (FAO-56), ERA5-Land horario, 6 puntos</span></div>
      <div><span class="num">92 %</span><span>de la ETo es término radiativo (91–94 % según el mes)</span></div>
    </div>
    <p class="rotulo">¿Qué tan buena es la referencia?</p>
    <table class="tabla">
      <tr><th></th><th>Mogotes</th><th>La Sierra</th><th>Charalá</th></tr>
      <tr><td>Rs ERA5-Land − Angstrom</td><td>+1.8</td><td>+4.7</td><td>+2.3</td><td class="u">MJ/m²·d</td></tr>
      <tr><td>ETo ERA5-Land − estación</td><td>−0.08</td><td>+0.66</td><td>−0.16</td><td class="u">mm/d</td></tr>
    </table>
    <p class="nota">Frente a la pet de TerraClimate: +11.8 % (1 166 contra 1 043), r = 0.97.
    La diferencia entre las dos pruebas, <b>5.0 puntos porcentuales</b>, es la incertidumbre de la referencia.</p>
  </div>
</div>
""", "El término aerodinámico es solo 6 a 9 % de la ETo según el mes. ERA5-Land da más Rs que el brillo solar, pero la ETo casi coincide con la de estación. Esa banda de 5.0 pp es con la que juzgamos los otros métodos.")

# 5 · Métodos -------------------------------------------------------------------------
diapositiva(0.9, "p1", f"""
<h2>Seis métodos, cada uno frente a su misma superficie</h2>
<div class="fig-texto">
  {figura("punto1/metodos_frente_eto.png", alto_px=860, alt="Media anual de cada método")}
  <div class="columna">
    <table class="tabla sesgos">
      <tr><th>Método</th><th>Sesgo</th><th>Meses en la banda</th></tr>
      <tr class="mejor"><td>Makkink</td><td>−3.1 %</td><td>7 de 12</td></tr>
      <tr><td>Penman (FAO-24, c = 0.8)</td><td>−7.4 %</td><td>4 de 12</td></tr>
      <tr><td>Hargreaves–Samani</td><td>+10.0 %</td><td>4 de 12</td></tr>
      <tr><td>Cenicafé 2006</td><td>−12.1 %</td><td>2 de 12</td></tr>
      <tr><td>Priestley–Taylor*</td><td>+16.5 %</td><td>0 de 12</td></tr>
      <tr><td>Thornthwaite</td><td>−38.2 %</td><td>0 de 12</td></tr>
    </table>
    <p class="nota">* Frente a Penman–Monteith (FAO-56) con rs = 0; los demás, frente a la ETo.</p>
    <ul class="claves">
      <li><b>Makkink</b> acierta porque la cuenca es húmeda y de poco viento.</li>
      <li><b>Thornthwaite</b> ve frío por la altura y lo lee como poca energía.</li>
      <li><b>α* = ETo/Eeq</b> va de 1.004 a 1.028: casi todo es energía.</li>
    </ul>
  </div>
</div>
""", "Hargreaves sobreestima con humedad alta (HR media 79.3 %). Cenicafé solo usa la altitud y aun así queda a −12 %. La AA (Brutsaert–Stricker) se descarta porque cae por encima del rango de la ET real.")

# 6 · ET real -------------------------------------------------------------------------
diapositiva(0.9, "p1", f"""
<h2>La cuenca evapora 1 045 ± 467 mm al año</h2>
<div class="fig-texto">
  {figura("punto1/et_real_productos.png", alto_px=860, alt="Productos de ET real frente al balance")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">± 467 <small>mm/año</small></span><span>95 %: lluvia σP = 315 (|PL − PI|) y caudal σQ = 344 (25.6 % de Q)</span></div>
      <div><span class="num">0.90</span><span>ET/ETo: evapora casi lo que pide la atmósfera</span></div>
      <div><span class="num">60 %</span><span>de la energía disponible; techo Rn/λ = 1 754 mm/año</span></div>
    </div>
    <p class="nota">Cinco productos caen dentro de la franja. SSEBop v5 (475) y la AA (1 551) quedan fuera
    y no se usan. El balance descarta productos, pero no dice cuál de los cinco es el mejor.</p>
  </div>
</div>
""", "La incertidumbre es casi la mitad del valor y viene por partes iguales de la lluvia (IMERG contra pluviómetros) y del caudal (Di Baldassarre y Montanari, 2009).")

# 7 · Budyko --------------------------------------------------------------------------
diapositiva(0.9, "p1", f"""
<h2>Manda la energía, salvo en enero</h2>
<div class="fig-texto">
  {figura("punto1/budyko.png", alto_px=820, alt="Espacio de Budyko")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">φ 0.49 · ε 0.43</span><span>lejos del límite de agua, cerca del de energía; Fu ω = 2.66</span></div>
      <div><span class="num">1.62</span><span>elasticidad de Q a P (empírica 1.63)</span></div>
      <div><span class="num">φ = 1.15</span><span>en enero: el único mes en que la demanda supera a la lluvia</span></div>
    </div>
    <p class="nota">La fracción evaporativa casi no cambia con la humedad del suelo (0.57 a 0.64) y no muestra
    quiebre. Sola no es concluyente, porque el suelo casi nunca se seca; junto con Budyko y ET/ETo = 0.90,
    apunta a la energía.</p>
  </div>
</div>
""", "En enero la diferencia la pone el agua que el suelo guardó. Alternativa: los productos traen su propio modelo de estrés hídrico. Ejes sin cortar: φ hasta 1.2, ε hasta 1.1.")

# 8 · Tendencias ----------------------------------------------------------------------
diapositiva(0.85, "p1", f"""
<h2>La demanda no ha cambiado de forma significativa</h2>
<div class="fig-texto">
  {figura("punto1/tendencias_demanda_1981_2022.png", alto_px=860, alt="Tendencias de la demanda 1981–2022")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">+4.2 <small>mm/año/década</small></span><span>ETo 1981–2022, p = 0.15: no significativa</span></div>
      <div><span class="num">+0.14 <small>°C/década</small></span><span>la temperatura sí sube; Thornthwaite +10.6, significativa</span></div>
      <div><span class="num">10.3 % vs 3.2 %</span><span>por °C: cuánto responden Thornthwaite y la ETo</span></div>
    </div>
    <p class="nota">Antes, el control de calidad encontró un escalón de +0.317 MJ/m²·d en la Rs de ERA5-Land
    después de 2000 (Pettitt p = 0.013, frente a CHIRPS). Sin corregirlo, la ETo subiría +9.5 y saldría
    significativa.</p>
  </div>
</div>
""", "Atribución: la temperatura aporta +5.5 y ea, u2 y Rs restan un poco. El escalón es un defecto del reanálisis (cambian las observaciones asimiladas), no un cambio real.")

# 9 · Altura --------------------------------------------------------------------------
diapositiva(0.85, "p1", f"""
<h2>Lo que distingue a la cuenca: la altura</h2>
<div class="fig-texto">
  {figura("punto1/gradiente_altitudinal.png", alto_px=860, hasta=0.645, alt="Demanda y ET real frente a la altura")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">−9 % <small>por km</small></span><span>baja la ETo con la altura</span></div>
      <div><span class="num">−30 % <small>por km</small></span><span>baja la ET real (GLEAM; SSEBop v6.1 −26, TerraClimate −11)</span></div>
      <div><span class="num">0.84 → 0.43</span><span>λET/Rn de GLEAM; una superficie mojada solo bajaría de 0.70 a 0.65</span></div>
    </div>
    <p class="nota">La resistencia de superficie sube +113 a +140 s/m por km, pero rs·LAI no sube: el LAI pasa de
    cerca de 3 a 1.2–1.7. Arriba frena la evaporación el páramo, con menos hojas, no el cierre de estomas.</p>
  </div>
</div>
""", "El frío explica una parte pequeña; el resto es la superficie. Cuidado: la ET por altura sale de productos, no de medidas, y podrían subestimar arriba por niebla y nubes.")

# 10 · Punto 2: sitio y datos ---------------------------------------------------------
diapositiva(0.75, "p2", f"""
<h2>Denver: una microcuenca y 45 años de lluvia horaria</h2>
<div class="fig-texto">
  {figura("punto2/fig_24_microcuenca_dem.png", alto_px=600, desde=0.645, hasta=0.99, alt="Microcuenca sobre el DEM Copernicus")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">1.0269 <small>km²</small></span><span>cauce de 2 312.5 m, del DEM Copernicus GLO-30, a 1.08 km de la estación</span></div>
      <div><span class="num">USW00023062</span><span>Denver Stapleton, NOAA GHCNh, precipitación horaria</span></div>
      <div><span class="num">22.30 → 13.28 <small>mm/h</small></span><span>media del máximo de 1 h, 1949–1972 frente a 1973–1994 (p ≈ 0.0008)</span></div>
    </div>
    <p class="nota">Un año entra con ≥ 80 % de horas válidas y ≥ 90 % entre abril y septiembre. El salto de 1973
    sugiere un cambio de registro.</p>
  </div>
</div>
""", "El DEM es un modelo de superficie: incluye edificios y no ve cunetas ni sumideros, así que la cuenca es una candidata topográfica que hay que validar con el drenaje urbano.")

# 11 · IDF ----------------------------------------------------------------------------
diapositiva(0.8, "p2", f"""
<h2>Curvas IDF, frente a NOAA Atlas 14</h2>
<div class="fig-texto">
  {figura("punto2/fig3_curvas_idf_loglog.png", alto_px=780, alt="Curvas IDF de Denver Stapleton")}
  <div class="columna">
    <ul class="claves">
      <li>Máximos anuales con la corrección de Weiss; <b>LP3 por L-momentos</b> (asimetría positiva, mejor KS y AD en las seis duraciones) y modelo Talbot–Wenzel.</li>
      <li>Por debajo de 1 h la curva es extrapolación, no medida.</li>
    </ul>
    <div class="cifras">
      <div><span class="num">18 de 36</span><span>casos dentro de la banda del 90 % de NOAA: todos los de T ≥ 25 años</span></div>
      <div><span class="num">−17 a −28 %</span><span>por debajo de NOAA para T ≤ 10 años (1 a 24 h); T = 50 y 1 h: 45.51 frente a 53 mm/h</span></div>
      <div><span class="num">T ≥ 137.3 <small>años</small></span><span>tormenta del 7 de agosto de 2022 (cota inferior); la del 26 de julio de 1965, T ≈ 75.7</span></div>
    </div>
  </div>
</div>
""", "Las duraciones cortas son las que controlan una microcuenca, y son justo las que no medimos. Eso es la principal incertidumbre del diseño. NOAA usa series de duración parcial de muchas estaciones y registros subhorarios; nosotros, máximos anuales de una sola estación horaria.")

# 12 · Problema A ---------------------------------------------------------------------
diapositiva(0.9, "p2", f"""
<h2>Problema A: una alcantarilla de 1 650 mm</h2>
<div class="fig-texto">
  {figura("punto2/fig_24_problemaA_sensibilidad_mc.png", alto_px=800, desde=0.035, hasta=0.515, alt="Sensibilidad del diámetro")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">6.43 <small>m³/s</small></span><span>caudal T = 50 años: i = 45.51 mm/h con tc = 60 min, C = 0.495</span></div>
      <div><span class="num">1 460 → 1 500 <small>mm</small></span><span>diámetro requerido y comercial inmediato, FS 1.08</span></div>
      <div><span class="num rec">1 650 <small>mm</small></span><span>recomendado: cubre IDF alta (1 558), C +20 % (1 563) y tc de Kirpich (1 576); FS 1.39</span></div>
    </div>
    <p class="nota">En 25 años, el riesgo nominal de T = 50 es 39.7 %; el efectivo del Monte Carlo para el tubo de
    1 500 mm es 15.2 %. Lo que más mueve el diámetro es el tc.</p>
  </div>
</div>
""", "El tubo de 1 500 solo cubre el caso central. Con 1 650 la capacidad es 8.91 m³/s. Es un predimensionamiento: no reemplaza el modelo hidráulico de detalle.")

# 13 · Problema B ---------------------------------------------------------------------
diapositiva(0.75, "p2", f"""
<h2>Problema B: el patrón de la tormenta fija el tanque</h2>
<div class="fig-texto">
  {figura("punto2/fig_24_problemaB_tanque.png", alto_px=860, desde=0.468, alt="Hidrogramas y tránsito del tanque")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">C 0.495 → 0.78</span><span>al urbanizar, y tc de 60 a 30 min</span></div>
      <div><span class="num">6.426 <small>m³/s</small></span><span>descarga máxima permitida: el pico antes de urbanizar</span></div>
      <div><span class="num">25 642 → 36 597 <small>m³</small></span><span>pico al inicio y pico al final (180 min): +43 % con la misma lámina</span></div>
      <div><span class="num rec">63 000 <small>m³</small></span><span>tanque de 18 000 m² × 3.5 m con orificio: cubre el peor caso</span></div>
    </div>
    <p class="nota">Con el pico al final el vaso se llena antes de que el orificio evacúe; aun así el tanque no rebosa y la
    salida queda bajo 6.426 m³/s. El racional modificado da una duración crítica de 75 min.</p>
  </div>
</div>
""", "Tránsito por piscina nivelada con RK4 de 1 minuto y Cd = 0.61. El orden de la lluvia dentro de la tormenta importa tanto como su total.")

# 14 · Análisis complementarios ------------------------------------------------------
diapositiva(0.75, "p2", f"""
<h2>Con +2 °C, el tubo de 1 500 mm ya no alcanza</h2>
<div class="fig-texto">
  {figura("punto2/fig_25b_bonificaciones.png", alto_px=680, desde=0.035, hasta=0.5, alt="Caudal pico y retorno efectivo con el calentamiento")}
  <div class="columna">
    <div class="cifras">
      <div><span class="num">7.33 <small>m³/s</small></span><span>pico T = 50 años con +2 °C (+14 % de intensidad, 7 %/°C), contra 6.91 del tubo de 1 500 mm</span></div>
      <div><span class="num">α = 1.000</span><span>con 1 500 mm o más, ninguna hora del registro supera la capacidad; con 1 200 mm fallan 8</span></div>
      <div><span class="num">T = 227 <small>años</small></span><span>mínimo del costo esperado (costos normalizados, no un presupuesto)</span></div>
    </div>
    <p class="nota">POT-GPD con Langbein coincide con los máximos anuales en T bajos y medios; en T altos LP3 da algo más:
    es la opción conservadora.</p>
  </div>
</div>
""", "Estos análisis responden la cuarta pregunta y refuerzan el tubo de 1 650 mm (8.91 m³/s).")

# 15 · Conclusiones -------------------------------------------------------------------
diapositiva(0.8, "fin", """
<h2>Conclusiones</h2>
<div class="dos concl">
  <div class="bloque p1">
    <p class="ceja">Punto 1 · Fonce</p>
    <ol>
      <li>La demanda la controla casi toda la energía; el término aerodinámico pesa poco.</li>
      <li>La cuenca devuelve menos de la mitad de la lluvia, con una incertidumbre del orden de la propia ET.</li>
      <li>Está limitada por energía casi todo el año; solo enero pasa al límite de agua.</li>
      <li>La demanda no tiene tendencia significativa una vez corregido el salto de la radiación.</li>
      <li>Con la altura, la menor cobertura vegetal frena la ET, no la falta de agua.</li>
    </ol>
  </div>
  <div class="bloque p2">
    <p class="ceja">Punto 2 · Denver</p>
    <ol>
      <li>La IDF cae en la banda de NOAA Atlas 14 para T ≥ 25 años y por debajo para T ≤ 10; el cambio de registro de 1973 pide cautela.</li>
      <li>El tc y la IDF subhoraria controlan el diseño: se recomienda el tubo de 1 650 mm.</li>
      <li>El patrón temporal de la tormenta fija el volumen del tanque.</li>
      <li>LP3 es algo más conservador que POT; con +2 °C el tubo de 1 500 mm se supera.</li>
      <li>Es un predimensionamiento: falta validar la cuenca con el drenaje urbano.</li>
    </ol>
  </div>
</div>
<p class="pie-ia">Uso de IA: Claude (Claude Code) en el punto 1 y la integración; Codex (OpenAI) en la programación del punto 2.
Las decisiones de método son del grupo. Detalle en el informe y en anexos/bitacora_ia.md.</p>
""", "Cerrar respondiendo las preguntas del inicio sin repetir cifras. Abrir a preguntas.")


ESTILO = """
:root{
  /* Lámina de 1920×1080 escalada a la ventana; figura grande a la izquierda, cifras a la derecha. */
  --papel:#F5F7F6; --tinta:#13212C; --suave:#4F5F6B; --linea:#D5DDE0;
  --fonce:#0B5F8A; --fonce-claro:#E3EEF4; --denver:#9A5B13; --denver-claro:#F4EBDF;
  --display:"Archivo", "Inter", system-ui, sans-serif;
  --texto:"Inter", system-ui, sans-serif;
  --datos:"IBM Plex Mono", ui-monospace, monospace;
  color-scheme:light;
}
html,body{height:100%;margin:0;background:#0E1A22;}
body{font-family:var(--texto);color:var(--tinta);overflow:hidden;}
#escenario{position:absolute;left:50%;top:50%;width:1920px;height:1080px;transform-origin:0 0;}
.lamina{position:absolute;inset:0;background:var(--papel);padding:72px 96px 88px;box-sizing:border-box;
  display:none;flex-direction:column;gap:36px;--acento:var(--fonce);--acento-claro:var(--fonce-claro);}
.lamina.activa{display:flex;}
.lamina.p2{--acento:var(--denver);--acento-claro:var(--denver-claro);}
.lamina::before{content:"";position:absolute;left:0;top:0;bottom:0;width:14px;background:var(--acento);}
.lamina.inicio::before,.lamina.intro::before,.lamina.fin::before{background:linear-gradient(var(--fonce) 0 50%,var(--denver) 50% 100%);}
h1,h2{font-family:var(--display);font-weight:800;letter-spacing:-0.015em;margin:0;text-wrap:balance;}
h2{font-size:60px;line-height:1.05;}
.ceja{font-family:var(--datos);font-size:22px;letter-spacing:0.06em;text-transform:uppercase;color:var(--acento);margin:0;}
.fig{overflow:hidden;max-width:100%;flex:none;background:#fff;border-radius:6px;box-shadow:0 1px 0 var(--linea),0 10px 30px rgba(19,33,44,.08);}
.fig img{display:block;width:100%;max-width:none;}
.fig-texto{display:flex;gap:64px;align-items:center;flex:1;min-height:0;}
.columna{display:flex;flex-direction:column;gap:30px;flex:1;min-width:0;}
.cifras{display:flex;flex-direction:column;gap:22px;}
.cifras div{display:flex;flex-direction:column;gap:4px;border-left:4px solid var(--acento);padding-left:22px;}
.num{font-family:var(--datos);font-weight:600;font-size:44px;color:var(--acento);font-variant-numeric:tabular-nums;line-height:1.1;}
.num small{font-size:24px;font-weight:500;color:var(--suave);}
.num.rec{background:var(--acento-claro);padding:2px 12px;border-radius:4px;align-self:flex-start;}
.cifras span:last-child{font-size:25px;line-height:1.35;color:var(--suave);}
.nota{font-size:24px;line-height:1.45;color:var(--tinta);margin:0;max-width:62ch;}
.rotulo{font-family:var(--display);font-weight:700;font-size:30px;margin:0;}
.tabla{border-collapse:collapse;font-size:24px;font-variant-numeric:tabular-nums;}
.tabla th{font-family:var(--datos);font-weight:500;font-size:19px;letter-spacing:.04em;text-transform:uppercase;color:var(--suave);text-align:left;padding:6px 18px 10px 0;border-bottom:2px solid var(--tinta);}
.tabla td{padding:10px 18px 10px 0;border-bottom:1px solid var(--linea);}
.tabla td:not(:first-child){font-family:var(--datos);white-space:nowrap;}
.tabla td.u{color:var(--suave);font-size:19px;}
.tabla.sesgos{font-size:27px;}
.tabla tr.mejor td{color:var(--acento);font-weight:700;}
.claves{margin:0;padding-left:28px;display:flex;flex-direction:column;gap:12px;font-size:25px;line-height:1.4;}
.claves b{color:var(--acento);}
/* portada */
.portada{display:flex;gap:80px;align-items:center;height:100%;}
.portada-texto{flex:1;display:flex;flex-direction:column;gap:34px;}
.portada h1{font-size:92px;line-height:1.0;}
.portada .sub{font-size:32px;line-height:1.4;color:var(--suave);margin:0;max-width:30ch;}
.autores{display:flex;gap:40px;font-family:var(--display);font-weight:600;font-size:34px;}
.autores span+span{color:var(--denver);}
.autores span:first-child{color:var(--fonce);}
.portada-fig .fig{border-radius:0;}
/* dos columnas */
.dos{display:grid;grid-template-columns:1fr 1fr;gap:56px;flex:1;min-height:0;}
.bloque{background:#fff;border-top:8px solid var(--acento);padding:36px 44px;display:flex;flex-direction:column;gap:18px;border-radius:0 0 6px 6px;}
.bloque.p1{--acento:var(--fonce);}
.bloque.p2{--acento:var(--denver);}
.bloque p{margin:0;font-size:26px;color:var(--suave);}
.bloque .grande{font-family:var(--datos);font-size:64px;font-weight:600;color:var(--acento);}
.bloque .grande small{font-size:30px;color:var(--suave);}
.preguntas,.concl ol{margin:6px 0 0;padding-left:36px;display:flex;flex-direction:column;gap:14px;font-size:28px;line-height:1.35;}
.concl ol{font-size:34px;gap:26px;}
.preguntas li::marker,.concl li::marker{font-family:var(--datos);color:var(--acento);font-weight:600;}
.pie-ia{margin:0;font-size:20px;color:var(--suave);}
/* pie de lámina */
.pie{position:absolute;left:96px;right:96px;bottom:30px;display:flex;justify-content:space-between;align-items:center;font-family:var(--datos);font-size:18px;color:var(--suave);letter-spacing:.04em;}
.barra{flex:1;height:4px;background:var(--linea);margin:0 28px;position:relative;border-radius:2px;}
.barra i{position:absolute;left:0;top:0;bottom:0;background:var(--acento);border-radius:2px;}
/* notas de quien expone (tecla N) */
#notas{position:fixed;left:0;right:0;bottom:0;background:#13212CEE;color:#F5F7F6;font:18px/1.5 var(--texto);padding:14px max(16px,env(safe-area-inset-left,0px)) calc(14px + env(safe-area-inset-bottom,0px));}
#ayuda{position:fixed;right:max(12px,env(safe-area-inset-right,0px));top:calc(10px + env(safe-area-inset-top,0px));color:#9FB0BA;font:13px var(--texto);}
@media print{
  @page{size:1920px 1080px;margin:0;}
  html,body{background:var(--papel);overflow:visible;height:auto;}
  #escenario{position:static;transform:none!important;width:auto;height:auto;}
  .lamina{display:flex!important;position:relative;width:1920px;height:1080px;break-after:page;}
  #notas,#ayuda{display:none!important;}
}
@media (prefers-reduced-motion:no-preference){.lamina.activa{animation:entra .25s ease-out;}}
@keyframes entra{from{opacity:.4}to{opacity:1}}
"""

GUION = """
const laminas=[...document.querySelectorAll('.lamina')];
const escenario=document.getElementById('escenario');
const notas=document.getElementById('notas');
let i=0;
function ajustar(){const s=Math.min(innerWidth/1920,innerHeight/1080);
  escenario.style.transform=`scale(${s}) translate(-50%,-50%)`;}
function mostrar(n){i=Math.max(0,Math.min(laminas.length-1,n));
  laminas.forEach((l,k)=>l.classList.toggle('activa',k===i));
  notas.textContent=laminas[i].dataset.notas;
  if(location.hash!=='#d'+(i+1))history.replaceState(null,'','#d'+(i+1));}
addEventListener('resize',ajustar);
addEventListener('keydown',e=>{
  if(['ArrowRight','PageDown',' ','Enter'].includes(e.key)){e.preventDefault();mostrar(i+1);}
  else if(['ArrowLeft','PageUp','Backspace'].includes(e.key)){e.preventDefault();mostrar(i-1);}
  else if(e.key==='Home')mostrar(0);
  else if(e.key==='End')mostrar(laminas.length-1);
  else if(e.key==='n'||e.key==='N')notas.hidden=!notas.hidden;
  else if(e.key==='f'||e.key==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen?.().catch(()=>{});}
});
addEventListener('click',e=>{if(e.target.closest('#notas'))return;mostrar(e.clientX>innerWidth/3?i+1:i-1);});
let x0=null;addEventListener('touchstart',e=>x0=e.touches[0].clientX,{passive:true});
addEventListener('touchend',e=>{if(x0===null)return;const dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>40)mostrar(dx<0?i+1:i-1);x0=null;});
ajustar();
const m=/^#d(\\d+)$/.exec(location.hash);mostrar(m?Number(m[1])-1:0);
"""


def construir():
    total = sum(d[0] for d in DIAPOSITIVAS)
    acumulado = 0.0
    laminas = []
    for numero, (minutos, seccion, html, notas) in enumerate(DIAPOSITIVAS, start=1):
        inicio = acumulado
        reloj = f"{int(inicio)}:{round((inicio % 1) * 60):02d}"
        acumulado += minutos
        etiqueta = {"p1": "Punto 1 · Fonce", "p2": "Punto 2 · Denver"}.get(seccion, "Tarea 2 · G01")
        progreso = acumulado / total * 100
        pie = (
            f'<div class="pie"><span>{etiqueta}</span>'
            f'<span class="barra"><i style="width:{progreso:.1f}%"></i></span>'
            f"<span>desde {reloj} · {numero}/{len(DIAPOSITIVAS)}</span></div>"
        )
        notas_attr = notas.replace('"', "&quot;")
        laminas.append(
            f'<section class="lamina {seccion}" data-notas="{notas_attr}">{html}{pie}</section>'
        )
    pagina = f"""<title>Fonce y Denver · Tarea 2</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=IBM+Plex+Mono:wght@500;600&family=Inter:wght@400;500;600;700&display=swap">
<style>{ESTILO}</style>
<div id="escenario">
{chr(10).join(laminas)}
</div>
<div id="notas" hidden></div>
<div id="ayuda">← → para pasar · N notas · F pantalla completa</div>
<script>{GUION}</script>
"""
    SALIDA.write_text(pagina, encoding="utf-8")
    print(f"{SALIDA.relative_to(RAIZ)}: {len(DIAPOSITIVAS)} diapositivas, {total:.1f} min de guion, "
          f"{SALIDA.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    construir()
