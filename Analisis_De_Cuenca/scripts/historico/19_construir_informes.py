"""Arma reporte/informe-fonce.html y reporte/criterios.html.

Orden completo (cada paso alimenta al siguiente):
    python scripts/historico/18_extraer_reglas.py      # lee las reglas del CODIGO y las verifica
    python scripts/historico/17_datos_informe.py       # junta valores, embudo, sensibilidad
    python scripts/historico/19_construir_informes.py  # este script

Los enlaces entre las dos paginas se leen de reporte/urls.json si existe
({"informe": "...", "criterios": "..."}), que se llena despues de publicar.
"""
import json, re
from pathlib import Path

P = Path("scripts/plantillas")
OUT = Path("reporte"); OUT.mkdir(exist_ok=True)

datos = Path("out/informe_datos.json").read_text(encoding="utf-8")
json.loads(datos)                                          # JSON valido
assert "</script" not in datos.lower(), "el JSON contiene </script"
assert " " not in datos and " " not in datos

css = (P / "comun.css").read_text(encoding="utf-8")
js = (P / "comun.js").read_text(encoding="utf-8")
urls = json.loads(Path("reporte/urls.json").read_text(encoding="utf-8")) if Path("reporte/urls.json").exists() else {}

for tpl, salida in [("tpl_informe.html", "informe-fonce.html"), ("tpl_criterios.html", "criterios.html")]:
    h = (P / tpl).read_text(encoding="utf-8")
    h = h.replace("__COMUN_CSS__", css).replace("__COMUN_JS__", js).replace("__DATA__", datos)
    h = h.replace("__CRITERIOS_URL__", urls.get("criterios", "")).replace("__INFORME_URL__", urls.get("informe", ""))
    sobran = re.findall(r"__[A-Z_]{4,}__", h)
    assert not sobran, f"{salida}: quedaron marcadores sin reemplazar: {sobran}"
    (OUT / salida).write_text(h, encoding="utf-8")
    print(f"{salida}: {len(h) / 1024:.0f} KB  (enlaces: {'si' if urls else 'aun no'})")
