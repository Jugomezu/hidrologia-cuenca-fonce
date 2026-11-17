"""Revisa que la carpeta de la entrega cumpla lo que pide el enunciado de la Tarea 2, antes de armar el ZIP.

Comprueba:
    1. El nombre de la carpeta (+ ".zip") cumple ^T2_202602_G[0-9]{2}(_[A-Z][A-Za-z]+){3}\\.zip$.
    2. Están los elementos obligatorios: README.md, T2_202602_GNN_informe.pdf, T2_202602_GNN_presentacion.pdf,
       codigo/{punto1,punto2}, datos/{punto1,punto2}, productos/{punto1,punto2}, anexos/.
    3. No hay nada más en la raíz de la carpeta (por ejemplo temp/, que se borra antes de entregar).
    4. Todo nombre de archivo y carpeta usa solo ASCII y no tiene espacios.
    5. El código no tiene rutas absolutas (C:\\..., /home/..., /Users/..., /mnt/...).
    6. No hay credenciales: archivos como .cdsapirc o .netrc, ni claves escritas en el código.
    7. Opcional, con --zip: el ZIP tiene el nombre correcto y una sola carpeta raíz con ese mismo nombre.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/):
    python codigo/verificar_entrega.py
    python codigo/verificar_entrega.py --zip ../T2_202602_G01_Gomez_Gomez_Na.zip

Termina con código 0 si todo cumple y 1 si algo falla; imprime cada problema.
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path

RAIZ_ENTREGA = Path(__file__).resolve().parents[1]

PATRON_ZIP = re.compile(r"^T2_202602_G[0-9]{2}(_[A-Z][A-Za-z]+){3}\.zip$")  # tal cual el enunciado
SUBCARPETAS_OBLIGATORIAS = ["codigo/punto1", "codigo/punto2", "datos/punto1", "datos/punto2",
                            "productos/punto1", "productos/punto2", "anexos"]
EXTENSIONES_CODIGO = {".py", ".ipynb", ".r", ".R", ".m", ".sh", ".bat", ".txt", ".yml", ".yaml", ".md", ".json"}

# Rutas absolutas: unidad de Windows (C:\ o C:/) o carpetas personales de Linux/macOS.
PATRON_RUTA_ABSOLUTA = re.compile(r"[A-Za-z]:[\\/](Users|Documents|Escritorio|OneDrive)|/home/|/Users/|/mnt/")
ARCHIVOS_CREDENCIALES = {".cdsapirc", ".netrc", ".env", "id_rsa", "id_ed25519", "credentials.json"}
# Una clave escrita en el código: key/token/password = "texto largo" (16 caracteres o más).
PATRON_CLAVE = re.compile(r"""(key|token|password|contrasena|secret)\s*[:=]\s*['"][^'"\s]{16,}['"]""", re.IGNORECASE)


def revisar_nombre(problemas):
    nombre_zip = RAIZ_ENTREGA.name + ".zip"
    if not PATRON_ZIP.match(nombre_zip):
        problemas.append(f"Nombre: '{nombre_zip}' no cumple la expresión regular del enunciado.")
    return RAIZ_ENTREGA.name.split("_")[2]  # GNN


def revisar_estructura(grupo, problemas):
    archivos = ["README.md", f"T2_202602_{grupo}_informe.pdf", f"T2_202602_{grupo}_presentacion.pdf"]
    for archivo in archivos:
        if not (RAIZ_ENTREGA / archivo).is_file():
            problemas.append(f"Estructura: falta el archivo {archivo}.")
    for carpeta in SUBCARPETAS_OBLIGATORIAS:
        if not (RAIZ_ENTREGA / carpeta).is_dir():
            problemas.append(f"Estructura: falta la carpeta {carpeta}/.")
    permitidos = set(archivos) | {"codigo", "datos", "productos", "anexos"}
    for elemento in RAIZ_ENTREGA.iterdir():
        if elemento.name not in permitidos and elemento.name != ".gitkeep":
            problemas.append(f"Estructura: '{elemento.name}' no está permitido en la raíz (borrarlo antes de entregar).")


def revisar_nombres_ascii(problemas):
    for ruta in RAIZ_ENTREGA.rglob("*"):
        nombre = ruta.name
        if not nombre.isascii() or " " in nombre:
            problemas.append(f"Nombre no ASCII o con espacios: {ruta.relative_to(RAIZ_ENTREGA)}")


def revisar_codigo(problemas):
    for ruta in (RAIZ_ENTREGA / "codigo").rglob("*"):
        if ruta.name in ARCHIVOS_CREDENCIALES:
            problemas.append(f"Credenciales: {ruta.relative_to(RAIZ_ENTREGA)} no puede ir en la entrega.")
        if not ruta.is_file() or ruta.suffix not in EXTENSIONES_CODIGO or ruta.name == Path(__file__).name:
            continue
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        for numero, linea in enumerate(texto.splitlines(), start=1):
            if PATRON_RUTA_ABSOLUTA.search(linea):
                problemas.append(f"Ruta absoluta: {ruta.relative_to(RAIZ_ENTREGA)}:{numero}: {linea.strip()[:90]}")
            if PATRON_CLAVE.search(linea):
                problemas.append(f"Posible clave: {ruta.relative_to(RAIZ_ENTREGA)}:{numero}")
    for ruta in RAIZ_ENTREGA.rglob("*"):
        if ruta.name in ARCHIVOS_CREDENCIALES and "codigo" not in ruta.parts:
            problemas.append(f"Credenciales: {ruta.relative_to(RAIZ_ENTREGA)} no puede ir en la entrega.")


def revisar_zip(ruta_zip, problemas):
    ruta_zip = Path(ruta_zip)
    if not PATRON_ZIP.match(ruta_zip.name):
        problemas.append(f"ZIP: el nombre '{ruta_zip.name}' no cumple la expresión regular.")
    with zipfile.ZipFile(ruta_zip) as z:
        raices = {nombre.split("/")[0] for nombre in z.namelist()}
    if raices != {ruta_zip.stem}:
        problemas.append(f"ZIP: debe tener una sola carpeta raíz '{ruta_zip.stem}'; tiene {sorted(raices)}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zip", help="ruta del ZIP ya armado, para revisarlo también")
    argumentos = parser.parse_args()

    problemas = []
    grupo = revisar_nombre(problemas)
    revisar_estructura(grupo, problemas)
    revisar_nombres_ascii(problemas)
    revisar_codigo(problemas)
    if argumentos.zip:
        revisar_zip(argumentos.zip, problemas)

    if problemas:
        print(f"{len(problemas)} problema(s):")
        for problema in problemas:
            print("  -", problema)
        sys.exit(1)
    print("La entrega cumple todas las comprobaciones.")


if __name__ == "__main__":
    main()
