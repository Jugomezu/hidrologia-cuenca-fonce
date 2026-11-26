# Punto 2 · Análisis hidrológico de Denver

Proyecto para control de calidad de precipitación, análisis de extremos, curvas IDF y diseño hidrológico preliminar.

## Estructura

- `codigo/punto2/`: scripts del flujo de análisis.
- `datos/punto2/`: archivo fuente y series limpias.
- `productos/punto2/`: tablas, figuras y reporte HTML.

Los scripts resuelven sus rutas desde la raíz del proyecto. La estación usada es NOAA GHCNh `USW00023062` (Denver Stapleton).

## Requisitos

Python 3 con `pandas`, `numpy`, `scipy` y `matplotlib`. Instala los paquetes desde la raíz:

```bash
python -m pip install -r requirements.txt
```

## Orden de ejecución

Ejecuta desde la raíz del proyecto:

```bash
python codigo/punto2/01_descarga_y_calidad.py
python codigo/punto2/02_extremos_y_distribuciones.py
python codigo/punto2/03_curvas_idf.py
python codigo/punto2/04_diseno_hidrologico.py
python codigo/punto2/00_generar_html.py
```

El flujo lee el PSV local de NOAA si ya está en `datos/punto2/`; los productos intermedios y finales se escriben en `productos/punto2/`.
