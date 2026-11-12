"""Geología de la cuenca de San Gil con el Mapa Geológico de Colombia 2023 del Servicio Geológico Colombiano (SGC).

CAMELS-COL publica, para cada cuenca, el porcentaje de área de siete litologías sacadas de este mismo mapa. Al
recortar el mapa del SGC con el polígono del proyecto, los porcentajes de CAMELS-COL aparecen con las etiquetas
corridas (por ejemplo, el 63.7 % que CAMELS-COL llama «rocas plutónicas» es lo que el SGC marca como rocas
sedimentarias). Por eso la geología del informe se calcula aquí, con el mapa original y el polígono del proyecto
(decisión del usuario del 2026-10-09; regla 13: se prefieren los cálculos propios).

FUENTE
  Servicio Geológico Colombiano, 2023. Mapa Geológico de Colombia 2023, escala 1:1 500 000 (CAMELS-COL lo cita
  como Gómez et al., 2023).
  Página de descarga: https://www2.sgc.gov.co/MGC/Paginas/mgc_1_5M2023.aspx
  Archivo: la geodatabase de ArcGIS (mgc2023.gdb.zip). Se usan dos capas:
    - «UC»: las unidades cronoestratigráficas (polígonos), con su símbolo, descripción y edad;
    - «Fallas»: las fallas (líneas), solo para el mapa.

TRANSFORMACIONES
  1. Se recortan las unidades con el polígono de San Gil (out/shp_fonce/cuencas_fonce.shp). El mapa viene en
     EPSG:4686 (MAGNA-SIRGAS geográficas); el área de cada pedazo se mide en EPSG:3116 (regla 13).
  2. Cada unidad se asigna a un grupo litológico según la letra de su símbolo después del guion, que es como el
     SGC codifica la litología (b2b6-Sm: S, sedimentaria; T3J-Pi: P, plutónica). Los símbolos de los depósitos
     cuaternarios van en minúscula (Q-ca). La tabla LITOLOGIA_POR_LETRA declara la regla; la descripción de cada
     unidad queda en la salida para poder comprobarla.
  3. El porcentaje de cada grupo es su área dividida por el área total recortada.

SALIDAS
  data/sgc/mgc2023.gdb.zip                    la geodatabase tal como se descarga (7.2 MB)
  out/geologia_sgc_fonce_unidades.csv          cada unidad dentro de la cuenca: símbolo, descripción, edad, grupo, área
  out/geologia_sgc_fonce.csv                   el área y el porcentaje de cada grupo litológico
  reporte/figuras/mapa_geologico.png           mapa de los grupos litológicos, las unidades y las fallas

El archivo se baja solo si no existe; su SHA-256 se imprime y está en DATOS_FUENTES.md.
"""
import hashlib
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import truststore
from matplotlib.patches import Patch

truststore.inject_into_ssl()      # usa los certificados del sistema operativo para verificar las descargas

RAIZ = Path(__file__).resolve().parents[1]
URL = "https://www2.sgc.gov.co/MGC/Documents/MGC_2023/mgc2023.gdb.zip"
ZIP = RAIZ / "data/sgc/mgc2023.gdb.zip"
GDB = RAIZ / "data/sgc/mgc2023.gdb"
POLIGONOS = RAIZ / "out/shp_fonce/cuencas_fonce.shp"
SALIDA_UNIDADES = RAIZ / "out/geologia_sgc_fonce_unidades.csv"
SALIDA_GRUPOS = RAIZ / "out/geologia_sgc_fonce.csv"
FIGURA = RAIZ / "reporte/figuras/mapa_geologico.png"
ID_SAN_GIL = 24027010
CRS_AREAS = 3116                  # MAGNA-SIRGAS / Colombia Bogotá, en metros (regla 13)

# Letra del símbolo del SGC (lo que va después del guion) -> grupo litológico. «VC» va antes que «V» porque
# las dos empiezan por V. Los mismos siete grupos que usa CAMELS-COL, en español.
LITOLOGIA_POR_LETRA = [
    ("VC", "Volcanoclástica"),
    ("V", "Volcánica"),
    ("H", "Hipoabisal"),
    ("P", "Plutónica"),
    ("M", "Metamórfica"),
    ("S", "Sedimentaria"),
]
DEPOSITO = "Depósito no consolidado"     # símbolos en minúscula: depósitos cuaternarios
COLOR_GRUPO = {                          # colores para el mapa (solo visuales)
    "Sedimentaria": "#E8C872", "Metamórfica": "#8FB98B", "Plutónica": "#E07A6F", "Hipoabisal": "#C77DB5",
    "Volcánica": "#7FA7D9", "Volcanoclástica": "#B7A3D6", DEPOSITO: "#F3EBD3",
}


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def bajar(url, ruta, intentos=50):
    """Baja el archivo por partes: si la conexión se corta, sigue desde el último byte recibido."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        return ruta
    parcial = ruta.with_suffix(ruta.suffix + ".parcial")
    total = int(requests.head(url, timeout=60).headers["Content-Length"])
    for _ in range(intentos):
        ya = parcial.stat().st_size if parcial.exists() else 0
        if ya >= total:
            break
        try:
            with requests.get(url, headers={"Range": f"bytes={ya}-"}, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(parcial, "ab") as f:
                    for bloque in r.iter_content(1 << 16):
                        f.write(bloque)
        except requests.RequestException as error:
            print(f"  conexión cortada en {ya} de {total} bytes ({error}); se sigue")
    assert parcial.stat().st_size == total, "la descarga no se completó"
    parcial.rename(ruta)
    return ruta


def grupo_litologico(simbolo):
    letra = simbolo.split("-", 1)[1]
    if letra[0].islower():
        return DEPOSITO
    for prefijo, grupo in LITOLOGIA_POR_LETRA:
        if letra.startswith(prefijo):
            return grupo
    raise ValueError(f"símbolo sin grupo litológico: {simbolo}")


# ---------------------------------------------------------------- descarga y lectura
bajar(URL, ZIP)
print(f"{ZIP.relative_to(RAIZ)}: {ZIP.stat().st_size / 1e6:.1f} MB, SHA-256 {sha256(ZIP)}")
if not GDB.exists():
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(GDB.parent)

cuenca = gpd.read_file(POLIGONOS).query("gauge_id == @ID_SAN_GIL")
uc = gpd.read_file(GDB, layer="UC")
cuenca = cuenca.to_crs(uc.crs)
uc = uc[uc.intersects(cuenca.geometry.iloc[0])]

# ---------------------------------------------------------------- recorte y áreas
recorte = gpd.overlay(uc[["SimboloUC", "Descripcion", "Edad", "geometry"]], cuenca[["geometry"]],
                      how="intersection")
recorte["grupo"] = recorte.SimboloUC.map(grupo_litologico)
recorte["area_km2"] = recorte.to_crs(CRS_AREAS).area / 1e6

unidades = (recorte.groupby(["SimboloUC", "Descripcion", "Edad", "grupo"], as_index=False)["area_km2"].sum()
            .sort_values("area_km2", ascending=False))
area_total = unidades.area_km2.sum()
unidades["porcentaje"] = unidades.area_km2 / area_total * 100
unidades = unidades.rename(columns={"SimboloUC": "simbolo", "Descripcion": "descripcion", "Edad": "edad"})

grupos = (unidades.groupby("grupo", as_index=False)[["area_km2", "porcentaje"]].sum()
          .sort_values("porcentaje", ascending=False))

# El recorte tiene que cubrir la cuenca: su área debe coincidir con la del polígono medida en el mismo sistema.
area_poligono = float(cuenca.to_crs(CRS_AREAS).area.iloc[0] / 1e6)
assert abs(area_total - area_poligono) / area_poligono < 0.001, (area_total, area_poligono)

unidades.to_csv(SALIDA_UNIDADES, index=False, float_format="%.4f")
grupos.to_csv(SALIDA_GRUPOS, index=False, float_format="%.4f")
print(f"{len(unidades)} unidades del SGC dentro de la cuenca, {area_total:.2f} km² (EPSG:{CRS_AREAS})")
print(grupos.to_string(index=False, float_format="%.2f"))

# ---------------------------------------------------------------- mapa
fallas = gpd.read_file(GDB, layer="Fallas", bbox=tuple(cuenca.total_bounds))
fallas = gpd.clip(fallas, cuenca)

fig, ax = plt.subplots(figsize=(9.0, 7.6), dpi=200)
recorte.plot(ax=ax, color=recorte.grupo.map(COLOR_GRUPO), edgecolor="white", linewidth=0.4)
recorte.dissolve("SimboloUC").reset_index().plot(ax=ax, facecolor="none", edgecolor="#5a5a5a", linewidth=0.3)
if len(fallas):
    fallas.plot(ax=ax, color="#3b2a1a", linewidth=0.9)
cuenca.boundary.plot(ax=ax, color="black", linewidth=1.2)

# rótulo de cada unidad grande (más del 2 % de la cuenca), en su punto representativo
for simbolo, pedazo in recorte.dissolve("SimboloUC").iterrows():
    if pedazo.geometry.area / cuenca.geometry.iloc[0].area > 0.02:
        punto = pedazo.geometry.representative_point()
        ax.annotate(simbolo, (punto.x, punto.y), ha="center", va="center", fontsize=6.5, color="#222222")

leyenda = [Patch(facecolor=COLOR_GRUPO[g], edgecolor="#5a5a5a", label=f"{g} ({p:.1f} %)" if p >= 0.1 else f"{g} ({p:.2f} %)")
           for g, p in zip(grupos.grupo, grupos.porcentaje)]
if len(fallas):
    leyenda.append(plt.Line2D([], [], color="#3b2a1a", linewidth=0.9, label="Fallas"))
ax.legend(handles=leyenda, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=7.5, frameon=True, title="Grupo litológico",
          title_fontsize=8)
ax.set_xlabel("Longitud (°)")
ax.set_ylabel("Latitud (°)")
# un kilómetro mide lo mismo en las dos direcciones a la latitud de la cuenca
ax.set_aspect(1 / np.cos(np.radians(cuenca.geometry.iloc[0].centroid.y)))
ax.tick_params(labelsize=7)
ax.set_title("Geología de la cuenca del Fonce hasta San Gil\nMapa Geológico de Colombia 2023 (SGC), 1:1 500 000",
             fontsize=9)
fig.tight_layout()
FIGURA.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGURA)
print(f"figura: {FIGURA.relative_to(RAIZ)}")
