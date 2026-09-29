"""Morfometría básica de la cuenca del Fonce hasta San Gil.

Responde tres cosas y revisa una cuarta:

  1. **Qué forma tiene la cuenca** — índice de Gravelius, factor de forma y razón de elongación, que
     miden lo alargada que es. Se comparan contra lo que publica CAMELS-COL.
  2. **Cómo es el perfil del cauce principal** — se extrae de la red de drenaje de CAMELS-COL buscando
     el camino más largo desde una cabecera hasta el punto de salida, y se lo perfila contra el DEM.
  3. **Cómo se reparten la altura, la pendiente y la orientación de las laderas** — curva hipsométrica,
     histograma de pendientes y rosa de orientaciones, todo desde el DEM.
  4. **Si los tiempos de concentración de CAMELS-COL son creíbles** — porque su `equi_slope` parece estar
     en otra unidad, y de ahí salen tiempos de concentración de más de cuatro días para una cuenca de
     2 100 km². Se recalculan con la pendiente medida sobre el cauce real.

Salidas (todas en out/, para que las figuras las dibuje otro script):
  morfometria_fonce.csv          los índices de forma y las cifras de resumen, con su fuente
  perfil_cauce_fonce.csv         distancia acumulada y altura a lo largo del cauce principal
  curva_hipsometrica_fonce.csv   fracción de área por encima de cada altura
  pendientes_fonce.csv           histograma de pendientes del terreno
  orientaciones_fonce.csv        histograma de orientación de laderas (16 rumbos)
  tiempos_concentracion.csv      tc por cada fórmula, con la pendiente de CAMELS y con la medida
"""
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry import LineString

RAIZ = Path(__file__).resolve().parent.parent
DEM = RAIZ / "data/dem/dem_fonce_alos_12m.tif"   # recorte del mosaico nacional (scripts/03_recorte_dem.py)
OUT = RAIZ / "out"
ID_PRINCIPAL = 24027010
UTM = "EPSG:32619"
# Las longitudes y áreas se miden en MAGNA-SIRGAS / Colombia Bogotá (EPSG:3116), la proyección oficial
# para esta zona. El DEM viene en UTM 19N, pero la cuenca (73° O) cae en la zona 18: medida en UTM 19N
# el área sale 0,42 % más grande y las longitudes 0,21 % más largas. El DEM se sigue leyendo en su grilla
# nativa (las alturas no cambian); solo las medidas de distancia y superficie se hacen en EPSG:3116.
MEDICION = "EPSG:3116"
FACTOR = 4                      # 12,5 m -> 50 m; suficiente para estadística de terreno
PASO_PERFIL = 250               # m entre puntos del perfil del cauce


# ------------------------------------------------------------------ la cuenca
cuencas = gpd.read_file(OUT / "shp_fonce/cuencas_fonce.shp")
cuencas["gauge_id"] = cuencas.gauge_id.astype(int)
cuenca = cuencas[cuencas.gauge_id == ID_PRINCIPAL].to_crs(UTM)
poligono = cuenca.geometry.iloc[0]
poligono_medido = cuenca.to_crs(MEDICION).geometry.iloc[0]
# el área es la única del proyecto, la geodésica que mide 02_shp_cuencas_estaciones.py
area_km2 = float(pd.read_csv(OUT / "shp_fonce/areas_cuencas.csv").set_index("gauge_id").loc[ID_PRINCIPAL, "area_km2"])
perimetro_km = poligono_medido.length / 1000

# el archivo viene separado por punto y coma y con espacios sobrantes en algunos encabezados
fisio = pd.read_csv(RAIZ / "data/camels_col/signatures/10_CAMELS_COL_Physiograpic_characteristics.csv",
                    sep=";")
fisio.columns = [c.strip() for c in fisio.columns]
fisio_sg = fisio.set_index("gauge_id").loc[ID_PRINCIPAL]


# ------------------------------------------------------------------ el DEM, recortado a la cuenca
with rasterio.open(DEM) as src:
    xmin, ymin, xmax, ymax = cuenca.total_bounds
    ventana = from_bounds(xmin, ymin, xmax, ymax, src.transform).round_offsets().round_lengths()
    alto, ancho = int(ventana.height // FACTOR), int(ventana.width // FACTOR)
    z = src.read(1, window=ventana, out_shape=(1, alto, ancho),
                 masked=True).astype("float32").filled(np.nan)
    transform = src.window_transform(ventana) * rasterio.Affine.scale(
        ventana.width / ancho, ventana.height / alto)

fuera = geometry_mask(cuenca.geometry, out_shape=z.shape, transform=transform)
z_cuenca = np.where(fuera, np.nan, z)
paso_m = abs(transform.a)
celdas_validas = int(np.isfinite(z_cuenca).sum())


# ------------------------------------------------------------------ 1. forma de la cuenca
def indices_de_forma(area_km2, perimetro_km, longitud_cauce_km):
    """Los tres índices clásicos. Todos valen 1 (o cerca) en una cuenca circular y crecen o decrecen
    a medida que se alarga."""
    a_m2, p_m, l_m = area_km2 * 1e6, perimetro_km * 1000, longitud_cauce_km * 1000
    return {
        # Gravelius: perímetro frente al de un círculo de la misma área. 1 = circular, >1 = alargada.
        "gravelius": p_m / (2 * np.sqrt(np.pi * a_m2)),
        # Horton: área sobre el cuadrado de la longitud del cauce. Cuanto menor, más alargada.
        "factor_forma": a_m2 / l_m ** 2,
        # Schumm: diámetro del círculo de igual área frente a la longitud del cauce.
        "razon_elongacion": (2 / l_m) * np.sqrt(a_m2 / np.pi),
        # cuánto más largo es el perímetro que el del círculo equivalente
        "exceso_perimetro_pct": (p_m / (2 * np.sqrt(np.pi * a_m2)) - 1) * 100,
    }


# ------------------------------------------------------------------ 2. el cauce principal
# La red de CAMELS-COL trae, para cada cuenca, todos sus tramos juntos en un MultiLineString. El cauce
# principal es el camino más largo del grafo: desde la cabecera más lejana hasta el punto de salida.
red = gpd.read_file(RAIZ / "data/camels_col/drainage/12_CAMELS_COL_Drainage_network/Drainage_network.shp")
red_sg = red[red.IDEAM_CODE == ID_PRINCIPAL].to_crs(UTM)
tramos = list(red_sg.geometry.iloc[0].geoms)
longitud_red_km = sum(t.length for t in red_sg.to_crs(MEDICION).geometry.iloc[0].geoms) / 1000


def redondear(punto, tolerancia=1.0):
    """Los extremos de dos tramos que se tocan no siempre coinciden al milímetro; se redondean a 1 m
    para que el grafo los reconozca como el mismo nodo."""
    return (round(punto[0] / tolerancia) * tolerancia, round(punto[1] / tolerancia) * tolerancia)


grafo = nx.Graph()
for tramo in tramos:
    coords = list(tramo.coords)
    a, b = redondear(coords[0]), redondear(coords[-1])
    if grafo.has_edge(a, b) and grafo[a][b]["peso"] >= tramo.length:
        continue
    grafo.add_edge(a, b, peso=tramo.length, geom=tramo)

# El punto de salida es el nodo más bajo de la red: se busca su altura en el DEM.
def altura_en(punto):
    columna, fila = ~transform * punto
    fila, columna = int(fila), int(columna)
    if 0 <= fila < z.shape[0] and 0 <= columna < z.shape[1]:
        return float(z[fila, columna])
    return np.nan


nodos = list(grafo.nodes)
alturas_nodos = {n: altura_en(n) for n in nodos}
salida = min((n for n in nodos if np.isfinite(alturas_nodos[n])), key=lambda n: alturas_nodos[n])

# camino más largo hasta la salida = el cauce principal
distancias = nx.single_source_dijkstra_path_length(grafo, salida, weight="peso")
cabecera = max(distancias, key=distancias.get)
camino = nx.shortest_path(grafo, salida, cabecera, weight="peso")

# se encadenan las geometrías del camino, ordenadas desde la cabecera hacia la salida
piezas = []
for a, b in zip(camino[:-1], camino[1:]):
    linea = grafo[a][b]["geom"]
    coords = list(linea.coords)
    if redondear(coords[0]) != a:
        coords = coords[::-1]
    piezas.extend(coords)
cauce = LineString(piezas[::-1])          # de la cabecera a la salida
longitud_cauce_km = gpd.GeoSeries([cauce], crs=UTM).to_crs(MEDICION).length.iloc[0] / 1000
# el perfil se muestrea sobre el trazado en UTM (donde está el DEM); sus distancias se pasan a la escala
# de EPSG:3116 para que el perfil y la longitud del cauce midan lo mismo
ESCALA_UTM = longitud_cauce_km * 1000 / cauce.length

# perfil: se muestrea el DEM cada PASO_PERFIL metros a lo largo del cauce
distancias_perfil = np.arange(0, cauce.length, PASO_PERFIL)
perfil = pd.DataFrame({
    "distancia_km": distancias_perfil * ESCALA_UTM / 1000,
    "altura_m": [altura_en((cauce.interpolate(d).x, cauce.interpolate(d).y)) for d in distancias_perfil],
})
perfil["altura_m"] = perfil.altura_m.replace(-32768, np.nan).interpolate()
# el cauce se recorre desde la cabecera, así que la altura debe ir bajando; se fuerza monotonía para
# la pendiente (el DEM tiene ruido y a veces "sube" unos metros dentro del cauce)
perfil["altura_suavizada_m"] = perfil.altura_m[::-1].cummax()[::-1]

desnivel_cauce_m = perfil.altura_suavizada_m.iloc[0] - perfil.altura_suavizada_m.iloc[-1]
pendiente_cauce = desnivel_cauce_m / (longitud_cauce_km * 1000)

# pendiente por el método de Taylor-Schwarz, que es el que corresponde usar en tiempo de concentración
tramos_perfil = perfil.dropna(subset=["altura_suavizada_m"])
dl = np.diff(tramos_perfil.distancia_km.values) * 1000
dz = -np.diff(tramos_perfil.altura_suavizada_m.values)
validos = (dl > 0) & (dz > 0)
pendiente_taylor = (dl[validos].sum() / np.sum(dl[validos] / np.sqrt(dz[validos] / dl[validos]))) ** 2


# ------------------------------------------------------------------ 3. altura, pendiente, orientación
alturas = z_cuenca[np.isfinite(z_cuenca)]
niveles = np.linspace(alturas.min(), alturas.max(), 100)
hipsometrica = pd.DataFrame({
    "altura_m": niveles,
    "fraccion_area_encima": [(alturas >= h).mean() for h in niveles],
})
# integral hipsométrica: área bajo la curva normalizada. ~0,6 cuencas jóvenes, ~0,3 seniles.
h_rel = (niveles - alturas.min()) / (alturas.max() - alturas.min())
integral_hipsometrica = float(np.trapezoid(hipsometrica.fraccion_area_encima.values, h_rel))

dzdy, dzdx = np.gradient(z_cuenca, paso_m, paso_m)
pendiente_grados = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
pendiente_pct = np.hypot(dzdx, dzdy) * 100
pend = pendiente_grados[np.isfinite(pendiente_grados)]

bordes_pend = np.arange(0, 75, 5)
conteo_pend, _ = np.histogram(pend, bins=bordes_pend)
pendientes = pd.DataFrame({"desde_grados": bordes_pend[:-1], "hasta_grados": bordes_pend[1:],
                           "fraccion_area": conteo_pend / conteo_pend.sum()})

# orientación: 0° = norte, creciendo en sentido horario
orientacion = (np.degrees(np.arctan2(-dzdx, dzdy)) + 360) % 360
llano = np.hypot(dzdx, dzdy) < 0.01        # casi plano: la orientación no significa nada
orient = orientacion[np.isfinite(orientacion) & ~llano]
RUMBOS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
          "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
bordes_orient = np.arange(-11.25, 360, 22.5)
conteo_orient, _ = np.histogram((orient + 11.25) % 360 - 11.25, bins=bordes_orient)
orientaciones = pd.DataFrame({"rumbo": RUMBOS, "fraccion_area": conteo_orient / conteo_orient.sum()})


# ------------------------------------------------------------------ 4. tiempos de concentración
def tiempos_de_concentracion(longitud_km, desnivel_m, pendiente, area_km2):
    """Las cuatro fórmulas que usa CAMELS-COL, en horas."""
    L_m, L_km = longitud_km * 1000, longitud_km
    return {
        "Kirpich": 0.0195 * L_m ** 0.77 * pendiente ** -0.385 / 60,
        "Chow": 0.1602 * (L_km / np.sqrt(pendiente)) ** 0.64,
        "Johnstone": 0.4623 * L_km ** 0.5 * (pendiente * 100) ** -0.25,
        "Engi_Corps": 0.3 * (L_km / pendiente ** 0.25) ** 0.76,
    }


tc_camels_slope = tiempos_de_concentracion(longitud_cauce_km, desnivel_cauce_m,
                                           float(fisio_sg["equi_slope"]), area_km2)
tc_medida = tiempos_de_concentracion(longitud_cauce_km, desnivel_cauce_m, pendiente_taylor, area_km2)
tc_publicado = {"Kirpich": float(fisio_sg["tc_kirpich"]), "Chow": float(fisio_sg["tc_chow"]),
                "Johnstone": float(fisio_sg["tc_Johnstone"]), "Engi_Corps": float(fisio_sg["tc_Engi_Corps"])}
tc = pd.DataFrame({"publicado_camels_h": tc_publicado,
                   "con_equi_slope_camels_h": tc_camels_slope,
                   "con_pendiente_medida_h": tc_medida}).rename_axis("formula").reset_index()


# ------------------------------------------------------------------ salidas
forma = indices_de_forma(area_km2, perimetro_km, longitud_cauce_km)
resumen = pd.DataFrame([
    ("área", area_km2, "km²", "polígono del proyecto", float(fisio_sg["area"])),
    ("perímetro", perimetro_km, "km", "polígono del proyecto", float(fisio_sg["perimeter"])),
    ("longitud del cauce principal", longitud_cauce_km, "km", "red de drenaje de CAMELS-COL",
     float(fisio_sg["streng_chanel"])),
    ("longitud de la red que publica CAMELS-COL", longitud_red_km, "km",
     "red de drenaje de CAMELS-COL", np.nan),
    # Ojo: esto NO es la densidad de drenaje real. La red de CAMELS-COL trae solo los cauces de cierto
    # orden, no cada quebrada, así que sale muy por debajo del rango habitual (0,5 a 3 km/km²). Se deja
    # anotada para que quede claro que no se puede usar como tal.
    ("longitud de red por km² (NO es la densidad de drenaje real)", longitud_red_km / area_km2,
     "km/km²", "red de CAMELS-COL, incompleta", np.nan),
    ("índice de Gravelius", forma["gravelius"], "—", "calculado", float(fisio_sg["gravelius_index"])),
    ("factor de forma de Horton", forma["factor_forma"], "—", "calculado", float(fisio_sg["factor_form"])),
    ("razón de elongación", forma["razon_elongacion"], "—", "calculada", np.nan),
    ("altura mínima", float(np.nanmin(z_cuenca)), "m", "DEM", float(fisio_sg["minimum_ele"])),
    ("altura media", float(np.nanmean(z_cuenca)), "m", "DEM", float(fisio_sg["mean_ele"])),
    ("altura máxima", float(np.nanmax(z_cuenca)), "m", "DEM", float(fisio_sg["maximum_ele"])),
    ("desnivel del cauce", desnivel_cauce_m, "m", "DEM sobre el cauce", np.nan),
    ("pendiente media del cauce", pendiente_cauce, "m/m", "DEM sobre el cauce", np.nan),
    ("pendiente del cauce (Taylor-Schwarz)", pendiente_taylor, "m/m", "DEM sobre el cauce",
     float(fisio_sg["equi_slope"])),
    ("pendiente media del terreno", float(np.nanmean(pendiente_grados)), "grados", "DEM", np.nan),
    ("pendiente mediana del terreno", float(np.nanmedian(pend)), "grados", "DEM", np.nan),
    ("integral hipsométrica", integral_hipsometrica, "—", "DEM", np.nan),
], columns=["magnitud", "valor", "unidad", "origen", "publicado_camels"])

resumen.to_csv(OUT / "morfometria_fonce.csv", index=False)
perfil.to_csv(OUT / "perfil_cauce_fonce.csv", index=False)
hipsometrica.to_csv(OUT / "curva_hipsometrica_fonce.csv", index=False)
pendientes.to_csv(OUT / "pendientes_fonce.csv", index=False)
orientaciones.to_csv(OUT / "orientaciones_fonce.csv", index=False)
tc.to_csv(OUT / "tiempos_concentracion.csv", index=False)
gpd.GeoDataFrame(geometry=[cauce], crs=UTM).to_file(OUT / "shp_fonce/cauce_principal.shp")

pd.set_option("display.width", 130)
print(f"DEM: {celdas_validas:,} celdas de {paso_m:.0f} m dentro de la cuenca\n".replace(",", " "))
print(resumen.to_string(index=False, float_format=lambda v: f"{v:,.4g}".replace(",", " ")))
print(f"\nTiempos de concentración (horas):")
print(tc.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
print(f"\nPerfil del cauce: {len(perfil)} puntos cada {PASO_PERFIL} m")
