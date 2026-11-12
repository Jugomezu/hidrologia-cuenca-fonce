"""Genera el registro de procedencia de TODOS los datos descargados:
titulo, DOI, version, licencia, metodo de descarga exacto e inventario de
archivos locales con tamanio y SHA-256.

Salidas:  DATOS_FUENTES.md   (lectura humana)
          out/datos_fuentes.csv  (inventario de archivos, uso programatico)
"""
import hashlib, json, csv
from pathlib import Path
from datetime import date

ROOT = Path(".")
HOY = date.today().isoformat()

# --------------------------------------------------------------------------
# Metadatos curados a mano, verificados contra la fuente autoritativa
# (Zenodo API, NASA CMR, Socrata API) el 2026-09-18.
# --------------------------------------------------------------------------
FUENTES = [
 dict(
  clave="camels_col",
  titulo="CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia",
  autores="Jimenez, David A.; Meneses, Julian E.; Solha, Pedro H. Bernardes; "
          "Avila Diaz, Alvaro; Quesada, Benjamin; Brentan, Bruno Melo; "
          "Rodrigues, Andre Ferreira",
  doi="10.5281/zenodo.18794895",
  doi_concepto="10.5281/zenodo.14947146  (siempre apunta a la version mas reciente)",
  version="publicada 2026-02-26 (3a version del registro)",
  licencia="CC-BY-4.0",
  editor="Zenodo",
  cobertura="346 cuencas de Colombia; series diarias 1981-01-01 a 2022-12-31; "
            "71 atributos por cuenca",
  acceso=HOY,
  metodo="API REST de Zenodo, descarga anonima (sin credenciales):\n"
         "    curl -L 'https://zenodo.org/api/records/18794895/files/<ARCHIVO>/content' -o <ARCHIVO>\n"
         "  Listado de versiones:  https://zenodo.org/api/records/15554735/versions\n"
         "  NOTA: las versiones anteriores (15554735, 14947147) tienen los archivos\n"
         "  restringidos; solo la de 2026-02-26 es de acceso abierto.",
  script="descarga manual via curl (ver seccion 'Comandos' abajo)",
  destino="data/camels_col/",
  cita="Jimenez, D. A., Meneses, J. E., Solha, P. H. B., Avila Diaz, A., Quesada, B., "
       "Brentan, B. M., & Rodrigues, A. F. (2026). CAMELS-COL: A Large-Sample "
       "Hydrometeorological Dataset for Colombia [Data set]. Zenodo. "
       "https://doi.org/10.5281/zenodo.18794895",
 ),
 dict(
  clave="camels_col_paper",
  titulo="CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia "
         "(preprint de discusion, Earth System Science Data)",
  autores="Jimenez, D. A., et al.",
  doi="10.5194/essd-2025-200",
  doi_concepto="",
  version="preprint, discusion abierta 2025-06-23",
  licencia="CC-BY-4.0",
  editor="Copernicus / Earth System Science Data Discussions",
  cobertura="Documento metodologico que acompania al dataset",
  acceso=HOY,
  metodo="Descarga directa del PDF, anonima:\n"
         "    https://essd.copernicus.org/preprints/essd-2025-200/essd-2025-200.pdf",
  script="consultado en linea; no almacenado en el proyecto",
  destino="(no almacenado)",
  cita="Jimenez, D. A., et al. (2025). CAMELS-COL: A Large-Sample Hydrometeorological "
       "Dataset for Colombia. Earth Syst. Sci. Data Discuss. "
       "https://doi.org/10.5194/essd-2025-200",
 ),
 dict(
  clave="ideam_cne",
  titulo="Catalogo Nacional de Estaciones del IDEAM",
  autores="Instituto de Hidrologia, Meteorologia y Estudios Ambientales (IDEAM)",
  doi="(sin DOI) - identificador Socrata: hp9r-jxuu",
  doi_concepto="",
  version="instantanea descargada el " + HOY,
  licencia="Datos Abiertos de Colombia (uso libre con atribucion)",
  editor="datos.gov.co",
  cobertura="29.538 estaciones; nombre, corriente, categoria, estado, municipio, "
            "coordenadas, area/zona/subzona hidrografica",
  acceso=HOY,
  metodo="API Socrata (SODA), descarga anonima:\n"
         "    curl -L 'https://www.datos.gov.co/resource/hp9r-jxuu.csv?$limit=60000' \\\n"
         "         -o data/ideam/cne_ideam.csv\n"
         "  Metadatos del recurso:  https://www.datos.gov.co/api/views/hp9r-jxuu.json",
  script="descarga manual via curl",
  destino="data/ideam/cne_ideam.csv",
  cita="IDEAM. Catalogo Nacional de Estaciones del IDEAM. Portal de Datos Abiertos "
       "de Colombia, conjunto hp9r-jxuu. Consultado el " + HOY + ".",
 ),
 dict(
  clave="imerg",
  titulo="GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07 "
         "(GPM_3IMERGDF)",
  autores="Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., Tan, J.",
  doi="10.5067/GPM/IMERGDF/DAY/07",
  doi_concepto="",
  version="V07 (V07B en los granulos)",
  licencia="Dominio publico (NASA Earth Science Data); requiere registro Earthdata",
  editor="NASA GES DISC (Goddard Earth Sciences Data and Information Services Center)",
  cobertura="Global 90S-90N, 0.1 grados (~11 km, ~123 km2/pixel); "
            "diario; 1998-01-01 a 2025-09-30",
  acceso=HOY,
  metodo="OPeNDAP sobre HTTPS con autenticacion NASA Earthdata (URS OAuth).\n"
         "  REQUIERE: (a) cuenta en https://urs.earthdata.nasa.gov\n"
         "            (b) autorizar la aplicacion 'NASA GESDISC DATA ARCHIVE'\n"
         "            (c) credenciales en un archivo netrc (NO versionar)\n"
         "  En esta maquina el archivo es  C:/Users/juanp/_netrc.txt  y se pasa\n"
         "  explicitamente porque curl solo busca '_netrc' sin extension:\n"
         "    curl --netrc-file C:/Users/juanp/_netrc.txt -L -c ck -b ck \\\n"
         "      'https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.07/"
         "<AAAA>/<MM>/3B-DAY.MS.MRG.3IMERG.<AAAAMMDD>-S000000-E235959.V07B.nc4.ascii"
         "?precipitation[0:0][<i0>:<i1>][<j0>:<j1>]'\n"
         "  Indexado de la grilla (verificado empiricamente):\n"
         "    lon = -179.95 + 0.1*i   (i = 0..3599)\n"
         "    lat =  -89.95 + 0.1*j   (j = 0..1799)\n"
         "    orden de dimensiones: precipitation[time][lon][lat]\n"
         "  NOTA: el servicio 'Data Rods for Hydrology' (hydro1.gesdisc) devuelve\n"
         "  HTML en vez de datos con estas credenciales; se usa OPeNDAP.",
  script="(pendiente: solo para la cuenca elegida)",
  destino="data/imerg/diario/  (pendiente)",
  cita="Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., & Tan, J. "
       "(2023). GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07. "
       "Greenbelt, MD: GES DISC. https://doi.org/10.5067/GPM/IMERGDF/DAY/07",
 ),
 dict(
  clave="imerg_mensual",
  titulo="GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07 "
         "(GPM_3IMERGM)",
  autores="Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., Tan, J.",
  doi="10.5067/GPM/IMERG/3B-MONTH/07",
  doi_concepto="",
  version="V07 (V07B en los granulos)",
  licencia="Dominio publico (NASA Earth Science Data); requiere registro Earthdata",
  editor="NASA GES DISC",
  cobertura="Recorte Colombia: lon -79.55 a -66.35, lat -4.65 a 13.75 (0.1 grados); "
            "mensual 1998-01 a 2022-12 (300 meses). Unidades originales mm/h, "
            "convertidas a mm/mes multiplicando por las horas del mes",
  acceso=HOY,
  metodo="OPeNDAP (ascii) sobre HTTPS con autenticacion NASA Earthdata:\n"
         "    curl --netrc-file C:/Users/juanp/_netrc.txt -L -c ck -b ck \\\n"
         "      'https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07/"
         "<AAAA>/3B-MO.MS.MRG.3IMERG.<AAAA><MM>01-S000000-E235959.<MM>.V07B.HDF5"
         ".ascii?precipitation[0:0][1004:1136][853:1037]'\n"
         "  Variable: /Grid/precipitation (mm/h), relleno -9999.9 -> NaN.\n"
         "  6 descargas simultaneas, reanudable.",
  script="scripts/04_imerg_descarga_mensual.py",
  destino="data/imerg/  (crudo en mensual/AAAAMM.txt; empaquetado en imerg_mensual_col.npz)",
  cita="Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., & Tan, J. "
       "(2023). GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07. "
       "Greenbelt, MD: GES DISC. https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07",
 ),
 dict(
  clave="chirps",
  titulo="CHIRPS v2.0 - Climate Hazards Group InfraRed Precipitation with Station data",
  autores="Funk, C., et al.",
  doi="10.15780/G2RP4Q",
  doi_concepto="",
  version="v2.0",
  licencia="Dominio publico (Creative Commons CC0)",
  editor="Climate Hazards Center, UC Santa Barbara / USGS",
  cobertura="50S-50N, 0.05 grados, diario, 1981-presente",
  acceso=HOY,
  metodo="NO descargado directamente. Llega ya agregado por cuenca dentro de "
         "CAMELS-COL (columna 'pr' de 04_CAMELS_COL_Hydrometeorological_data).\n"
         "  Fuente original: https://data.chc.ucsb.edu/products/CHIRPS-2.0/",
  script="(incluido en CAMELS-COL)",
  destino="data/camels_col/hydromet/ (columna pr)",
  cita="Funk, C., et al. (2015). The climate hazards infrared precipitation with "
       "stations. Scientific Data, 2, 150066. https://doi.org/10.1038/sdata.2015.66",
 ),
 dict(
  clave="mswx",
  titulo="MSWX - Multi-Source Weather (temperatura y variables meteorologicas)",
  autores="Beck, H. E., et al.",
  doi="10.1175/BAMS-D-21-0145.1",
  doi_concepto="",
  version="MSWX-Past",
  licencia="CC-BY-4.0 (requiere registro en GloH2O)",
  editor="GloH2O",
  cobertura="Global, 0.1 grados, 3-horario, 1979-presente",
  acceso=HOY,
  metodo="NO descargado directamente. Llega ya agregado por cuenca dentro de "
         "CAMELS-COL (columnas t_max, t_min y poten_evapo).\n"
         "  Fuente original: https://www.gloh2o.org/mswx/",
  script="(incluido en CAMELS-COL)",
  destino="data/camels_col/hydromet/ (columnas tmax, tmin, etp)",
  cita="Beck, H. E., et al. (2022). MSWX: Global 3-hourly 0.1 deg bias-corrected "
       "meteorological data. Bull. Amer. Meteor. Soc. "
       "https://doi.org/10.1175/BAMS-D-21-0145.1",
 ),
 dict(
  clave="era5",
  titulo="ERA5 daily statistics / ERA5-Land hourly data (temperatura)",
  autores="Hersbach, H., et al. / Munoz-Sabater, J., et al.",
  doi="10.24381/cds.adbb2d47  (ERA5 single levels) | "
      "10.24381/cds.e2161bac  (ERA5-Land hourly)",
  doi_concepto="",
  version="por definir (ERA5 o ERA5-Land segun resolucion requerida)",
  licencia="Licencia Copernicus para productos C3S (uso libre con atribucion)",
  editor="Copernicus Climate Change Service (C3S) / ECMWF",
  cobertura="ERA5: global 0.25 deg, 1940-presente. ERA5-Land: 0.1 deg, 1950-presente",
  acceso="PENDIENTE - aun no descargado",
  metodo="PLANEADO. Requiere cuenta en el Climate Data Store y clave de API en\n"
         "  ~/.cdsapirc; descarga con el paquete 'cdsapi'. Solo se usara si se\n"
         "  necesita temperatura fuera de lo que ya trae CAMELS-COL (MSWX).",
  script="(pendiente)",
  destino="data/era5/  (pendiente)",
  cita="Hersbach, H., et al. (2023). ERA5 hourly data on single levels from 1940 to "
       "present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). "
       "https://doi.org/10.24381/cds.adbb2d47",
 ),
]

# --------------------------------------------------------------------------
def inventario(base: Path):
    filas = []
    if not base.exists():
        return filas
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        h = hashlib.sha256()
        with p.open("rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                h.update(blk)
        filas.append(dict(ruta=p.as_posix(), bytes=p.stat().st_size,
                          sha256=h.hexdigest()))
    return filas

filas = inventario(ROOT / "data")
Path("out").mkdir(exist_ok=True)
with open("out/datos_fuentes.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["ruta", "bytes", "sha256"])
    w.writeheader(); w.writerows(filas)

def humano(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024: return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

L = []
L.append("# Procedencia de los datos\n")
L.append(f"Proyecto: **Analisis de cuenca — Hidrologia, Tarea 1**  \n")
L.append(f"Generado automaticamente por `scripts/historico/11_metadatos_fuentes.py` el {HOY}.\n")
L.append("Los DOI y versiones se verificaron contra la fuente autoritativa "
         "(API de Zenodo, NASA CMR, API de Socrata) en esa fecha.\n")
L.append("\n## Resumen\n")
L.append("| Fuente | DOI / ID | Licencia | Estado |")
L.append("|---|---|---|---|")
for f in FUENTES:
    est = "descargado" if Path(f["destino"].split()[0]).exists() else (
          "PENDIENTE" if "PENDIENTE" in f["acceso"] or "pendiente" in f["destino"]
          else "no almacenado")
    L.append(f"| {f['titulo'].split('(')[0].strip()[:58]} | `{f['doi']}` | "
             f"{f['licencia'][:28]} | {est} |")

L.append("\n---\n")
for f in FUENTES:
    L.append(f"\n## {f['titulo']}\n")
    L.append(f"- **Autores:** {f['autores']}")
    L.append(f"- **DOI:** `{f['doi']}`")
    if f["doi_concepto"]:
        L.append(f"- **DOI de concepto:** `{f['doi_concepto']}`")
    L.append(f"- **Version:** {f['version']}")
    L.append(f"- **Editor / archivo:** {f['editor']}")
    L.append(f"- **Licencia:** {f['licencia']}")
    L.append(f"- **Cobertura:** {f['cobertura']}")
    L.append(f"- **Fecha de acceso:** {f['acceso']}")
    L.append(f"- **Destino local:** `{f['destino']}`")
    L.append(f"\n**Metodo de descarga**\n")
    L.append("```\n" + f["metodo"] + "\n```")
    L.append(f"\n**Cita recomendada**\n\n> {f['cita']}\n")

L.append("\n---\n\n## Inventario de archivos locales\n")
L.append(f"{len(filas)} archivos, {humano(sum(x['bytes'] for x in filas))} en total. "
         "Checksums completos en `out/datos_fuentes.csv`.\n")
L.append("| Archivo | Tamanio | SHA-256 (12 primeros) |")
L.append("|---|---|---|")
grandes = [x for x in filas if x["bytes"] > 100_000]
for x in sorted(grandes, key=lambda r: -r["bytes"])[:40]:
    L.append(f"| `{x['ruta']}` | {humano(x['bytes'])} | `{x['sha256'][:12]}` |")
peq = len(filas) - len(grandes)
if peq:
    L.append(f"\n_({peq} archivos menores de 100 KB omitidos de esta tabla; "
             "estan todos en el CSV.)_\n")

L.append("\n---\n\n## Notas de reproducibilidad\n")
L.append("- El archivo de credenciales de Earthdata (`_netrc.txt`) **no** forma parte "
         "del proyecto y no debe versionarse ni compartirse.\n")
L.append("- Zenodo sirve versiones inmutables: el DOI `10.5281/zenodo.18794895` "
         "seguira devolviendo exactamente estos archivos. El DOI de concepto "
         "`10.5281/zenodo.14947146` apunta siempre a la mas reciente y puede cambiar.\n")
L.append("- El catalogo del IDEAM es una instantanea viva: `datos.gov.co` no versiona, "
         "asi que la copia local con su SHA-256 es la unica referencia estable.\n")
L.append("- IMERG V07 se reprocesa ocasionalmente; los granulos llevan sufijo de "
         "version (`V07B`) que conviene registrar junto con la fecha de descarga.\n")

Path("DATOS_FUENTES.md").write_text("\n".join(L), encoding="utf-8")
print(f"DATOS_FUENTES.md escrito ({len(FUENTES)} fuentes)")
print(f"out/datos_fuentes.csv: {len(filas)} archivos, "
      f"{humano(sum(x['bytes'] for x in filas))}")
