"""Versión del informe ordenada por los puntos del taller: escribe reporte/reporte-fonce-por-puntos.html.

Excepción a la regla 22 (un solo informe) y a la regla 16 (el informe no nombra los puntos), decidida por el
usuario el 2026-10-11. Esta página no es un informe nuevo: toma el informe ya generado por
scripts/18b_reporte_html.py, lo parte en sus secciones y las reordena según la tabla ORDEN. El texto de cada
sección no cambia; solo se agregan encabezados de punto y recuadros «Pendiente» donde el informe todavía no
tiene lo que pide el taller. Para cambiar el contenido se edita 18 o 18b, se regenera el informe y se corre
este script. Desde la raíz:

    python scripts/18c_reporte_por_puntos.py
"""
import re
from pathlib import Path

ENTRADA = Path("reporte/reporte-fonce.html")
SALIDA = Path("reporte/reporte-fonce-por-puntos.html")

# Cuántas secciones tiene hoy el informe. Si 18b gana o pierde una, el script se detiene, para que alguien
# decida en qué punto va y la ponga en ORDEN, en vez de que la sección se pierda o quede en un lugar cualquiera.
SECCIONES_ESPERADAS = 30

# El bloque de la hipótesis H sale de «Explicaciones físicas» y va a «Revisión de la hipótesis», al final.
TITULO_HIPOTESIS = "<h3>Una hipótesis para las relaciones y las tendencias</h3>"


def partir_en_secciones(html):
    """Devuelve (lo de antes de la primera sección, {título h2: sección}, lo de entre secciones, lo del final).

    Lo que hay entre secciones son scripts de la página (por ejemplo, el de las pestañas); se conservan y se
    ponen todos después de la última sección, donde siguen encontrando los elementos que usan.
    """
    inicios = [m.start() for m in re.finditer(r"<section>", html)]
    finales = [m.end() for m in re.finditer(r"</section>", html)]
    assert len(inicios) == len(finales) == SECCIONES_ESPERADAS, (
        f"el informe tiene {len(inicios)} secciones y se esperaban {SECCIONES_ESPERADAS}: revisar ORDEN")
    antes = html[: inicios[0]]
    despues = html[finales[-1]:]
    entre = [html[a:b] for a, b in zip(finales[:-1], inicios[1:]) if html[a:b].strip()]
    secciones = {}
    for a, b in zip(inicios, finales):
        bloque = html[a:b]
        titulo = re.search(r"<h2[^>]*>(.*?)</h2>", bloque, re.S).group(1).strip()
        secciones[titulo] = bloque
    return antes, secciones, entre, despues


def extraer_div(texto, marca):
    """Devuelve (texto sin el <div> que contiene `marca`, ese <div>), contando los <div> anidados."""
    i = texto.index(marca)
    inicio = texto.rindex("<div>", 0, i)
    nivel = 0
    for m in re.finditer(r"<div\b|</div>", texto[inicio:]):
        nivel += 1 if m.group(0) == "<div" else -1
        if nivel == 0:
            fin = inicio + m.end()
            return texto[:inicio] + texto[fin:], texto[inicio:fin]
    raise ValueError(f"no se cerró el <div> de {marca}")


def punto(titulo):
    """Encabezado de un punto del taller (los títulos son cortos y propios, no el texto del enunciado)."""
    return f'<section class="punto"><h2>{titulo}</h2></section>'


def pendiente(titulo, que_falta):
    """Recuadro para lo que pide el taller y el informe todavía no tiene. No se rellena: se dice que falta."""
    return f'<section class="pendiente"><h2>{titulo}</h2><p><b>Pendiente.</b> {que_falta}</p></section>'


html = ENTRADA.read_text(encoding="utf-8")
antes, secciones, entre, despues = partir_en_secciones(html)
secciones["Explicaciones físicas"], bloque_hipotesis = extraer_div(secciones["Explicaciones físicas"],
                                                                   TITULO_HIPOTESIS)

# El orden de la página. Un texto que es título de una sección del informe se reemplaza por esa sección;
# lo demás (encabezados de punto y recuadros) se escribe tal cual.
ORDEN = [
    punto("Contexto físico de la cuenca"),
    "Contexto geográfico", "Mapas de la cuenca", "Forma y relieve de la cuenca", "Coberturas, suelos y geología",

    punto("Punto 1. Series mensuales"),
    "Comparando PI con PL", "En esta cuenca llueve menos arriba",
    "Dos fuentes de temperatura, y por qué se usa ERA5-Land",
    "Las cuatro variables, en números", "Revisión de outliers",
    "Qué meses tienen dato y cuáles no", "Control de calidad básico", "Saltos y errores de registro",
    "Registro de problemas de los datos", "La evapotranspiración potencial (ETP)",
    "Lo que le cae a la cuenca y lo que sale por el río",
    pendiente("Hipótesis inicial", "Espacio reservado para la primera interpretación del régimen."),
    "El ciclo anual", "Años que se salen de lo normal", "Explicaciones físicas",

    punto("Punto 2. Relaciones y modelos"),
    "Cómo se relacionan las variables entre sí", "¿Sirve la lluvia para estimar el caudal?",

    punto("Punto 3. Tendencias"),
    "Anomalías y anomalías estandarizadas", "Tendencias de largo plazo",

    punto("Punto 4. Frecuencias"),
    "Frecuencias: análisis de Fourier",

    punto("Punto 5. Clima global"),
    "Campos climáticos globales", "La cuenca frente a los campos climáticos", "Interpretación física de los patrones",

    "Síntesis física y conclusiones",
    pendiente("Esquema conceptual", "Falta el esquema que conecta circulación regional, lluvia, almacenamiento, "
                                    "pérdidas y caudal, con sus escalas de tiempo."),
    '<section class="punto"><h2>Revisión de la hipótesis</h2>'
    '<p>El informe revisa la hipótesis en «Conclusiones», dentro de «Síntesis física y conclusiones». '
    f'Abajo, H tal como se formuló.</p>{bloque_hipotesis}</section>',

    "Bibliografía", "Contribuciones de los autores", "Uso de inteligencia artificial",
]

# Cada sección del informe aparece exactamente una vez: ni se pierde ni se repite.
usadas = [x for x in ORDEN if x in secciones]
assert sorted(usadas) == sorted(secciones), f"secciones sin ubicar o repetidas: {set(secciones) ^ set(usadas)}"

cuerpo = "\n".join(secciones.get(x, x) for x in ORDEN)

# Estilo de las piezas nuevas, con las variables de color del informe (sirven en tema claro y oscuro).
ESTILO = """<style>
section.punto { border-top: 3px solid var(--acento); padding-top: 18px; }
section.pendiente { border: 1px dashed var(--tenue); padding: 14px 18px; }
</style>
"""
assert antes.count('<div class="envoltura">') == 1
antes = antes.replace('<div class="envoltura">', ESTILO + '<div class="envoltura">', 1)
antes, n = re.subn(r"<title>[^<]*</title>", "<title>Reporte cuenca del Fonce (por puntos del taller)</title>",
                   antes, count=1)
assert n == 1

SALIDA.write_text(antes + cuerpo + "\n" + "\n".join(entre) + despues, encoding="utf-8")
print(f"escrito {SALIDA}: {len(usadas)} secciones del informe, reordenadas por punto")
