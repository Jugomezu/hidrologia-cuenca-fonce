"""Descarga GLEAM v4 mensual (E, Ep y SMrz) por SFTP y la recorta a la caja de la cuenca del Fonce.

Fuente: GLEAM4 (Miralles et al., 2025; Global Land Evaporation Amsterdam Model), Universidad de Gante. Se usa la
versión 4.x «a» más reciente que haya en el servidor (la «a» se fuerza con reanálisis y cubre 1980 en adelante;
la «b» es satelital y más corta). Variables mensuales:
    E     evaporación real (mm/mes)
    Ep    evaporación potencial (mm/mes)
    SMrz  humedad del suelo en la zona de raíces (m³/m³)
Las unidades exactas se leen de los atributos del archivo y se copian al .meta.json.

Acceso: SFTP en aether.ugent.be, puerto 2225, usuario gleamuser. La clave la entrega GLEAM al registrarse y
NO está en este repositorio: el script la lee SOLO de la variable de entorno GLEAM_SFTP_PASS y se detiene si
no existe. No la imprime ni la guarda.

Período: 1998-01 a 2022-12. Caja: N 6.7, O −73.4, S 5.8, E −72.7 (la de la cuenca más una celda de margen).

Cómo se baja: se abre cada NetCDF mensual directamente en el servidor (lectura remota con h5netcdf) y se leen solo
las celdas de la caja; si eso falla, se baja el archivo a una carpeta temporal, se recorta y se borra. No queda
ningún archivo global.

Uso, desde la carpeta de la entrega (T2_202602_G01_Gomez_Gomez_Na/), en PowerShell:
    $env:GLEAM_SFTP_PASS = "<clave>"      # solo en esa terminal; no la escribas en ningún archivo
    python codigo/punto1/11_descarga_gleam_v4.py
    Remove-Item Env:GLEAM_SFTP_PASS

Salidas, en datos/punto1/gleam_v4/:
    gleam_v4_<VAR>_mensual_1998_2022_fonce.nc            recorte sin transformar, con sus atributos
    gleam_v4_<VAR>_mensual_1998_2022_fonce.nc.meta.json  fuente, versión, unidades, período, recorte, SHA-256
Si falta la clave, la conexión falla o no aparecen los archivos mensuales, el script se detiene con el error.
"""

import datetime
import hashlib
import json
import os
import posixpath
import re
import stat
import sys
import tempfile
from pathlib import Path

import paramiko
import xarray as xr

# --- Rutas (relativas a la carpeta de la entrega) ---------------------------------------------------
RAIZ_ENTREGA = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_ENTREGA / "datos" / "punto1" / "gleam_v4"

# --- Petición ---------------------------------------------------------------------------------------
SERVIDOR = "aether.ugent.be"
PUERTO = 2225
USUARIO = "gleamuser"
VARIABLE_CLAVE = "GLEAM_SFTP_PASS"
VARIABLES = ["E", "Ep", "SMrz"]
FECHA_INICIO, FECHA_FIN = "1998-01-01", "2022-12-31"
MESES_ESPERADOS = 300
CAJA = {"norte": 6.7, "oeste": -73.4, "sur": 5.8, "este": -72.7}
PROFUNDIDAD_MAXIMA = 6
PATRON_VERSION = re.compile(r"v?4\.(\d+)a", re.IGNORECASE)


def sha256_de(archivo):
    resumen = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def conectar():
    clave = os.environ.get(VARIABLE_CLAVE)
    if not clave:
        sys.exit(f"Falta la variable de entorno {VARIABLE_CLAVE} con la clave del SFTP de GLEAM. "
                 f"Defínela en la terminal antes de correr el script (ver el docstring).")
    if clave.startswith("<") and clave.endswith(">"):
        sys.exit(f"{VARIABLE_CLAVE} contiene el texto de ejemplo entre < >, no la clave real del correo de GLEAM.")
    transporte = paramiko.Transport((SERVIDOR, PUERTO))
    transporte.start_client(timeout=60)
    try:
        transporte.auth_password(USUARIO, clave)
    except (paramiko.BadAuthenticationType, paramiko.AuthenticationException):
        # Algunos servidores solo aceptan la clave por el método «keyboard-interactive».
        transporte.auth_interactive(USUARIO, lambda titulo, instrucciones, preguntas: [clave] * len(preguntas))
    del clave
    if not transporte.is_authenticated():
        sys.exit("El servidor de GLEAM rechazó la clave: revisa que sea la del correo, copiada sin espacios.")
    return transporte, paramiko.SFTPClient.from_transport(transporte)


def listar_ncs(sftp, carpeta="/", profundidad=0):
    """Rutas de todos los .nc bajo `carpeta` (recorrido limitado en profundidad)."""
    rutas = []
    if profundidad > PROFUNDIDAD_MAXIMA:
        return rutas
    for entrada in sftp.listdir_attr(carpeta):
        ruta = posixpath.join(carpeta, entrada.filename)
        if stat.S_ISDIR(entrada.st_mode):
            rutas += listar_ncs(sftp, ruta, profundidad + 1)
        elif entrada.filename.endswith(".nc"):
            rutas.append(ruta)
    return rutas


def escoger_archivos(rutas, variable):
    """Archivos mensuales de la variable en la versión 4.xa más reciente, ordenados."""
    candidatos = []
    for ruta in rutas:
        nombre = posixpath.basename(ruta)
        version = PATRON_VERSION.search(ruta)
        mensual = re.search(r"(_MO\b|_MO\.nc|/monthly/)", ruta, re.IGNORECASE)
        # Exactamente «VAR_AAAA_...»: así «Ep» no toma sus componentes «Ep_aero_...» ni «Ep_rad_...».
        if version and mensual and re.match(rf"{re.escape(variable)}_\d{{4}}_", nombre):
            candidatos.append((int(version.group(1)), ruta))
    if not candidatos:
        raise RuntimeError(f"No se encontraron archivos mensuales de {variable} en una versión 4.xa del servidor")
    ultima = max(v for v, _ in candidatos)
    archivos = sorted(r for v, r in candidatos if v == ultima)
    anios = {int(re.search(r"_(\d{4})_", posixpath.basename(r)).group(1)) for r in archivos}
    faltan = sorted(set(range(1998, 2023)) - anios)
    if faltan:
        raise RuntimeError(f"{variable}: faltan los archivos anuales de {faltan} en la versión 4.{ultima}a")
    print(f"  {variable}: {len(archivos)} archivos anuales, de {min(anios)} a {max(anios)}", flush=True)
    return f"4.{ultima}a", archivos


def recortar(ds, variable):
    nombres_lat = [n for n in ("lat", "latitude") if n in ds.coords]
    nombres_lon = [n for n in ("lon", "longitude") if n in ds.coords]
    lat, lon = nombres_lat[0], nombres_lon[0]
    descendente = float(ds[lat][0]) > float(ds[lat][-1])
    corte_lat = slice(CAJA["norte"], CAJA["sur"]) if descendente else slice(CAJA["sur"], CAJA["norte"])
    sub = ds[[variable]].sel({lat: corte_lat, lon: slice(CAJA["oeste"], CAJA["este"])})
    return sub.sel(time=slice(FECHA_INICIO, FECHA_FIN)).load()


def abrir_y_recortar(sftp, ruta, variable):
    """Lectura remota de la caja; si no se puede, descarga temporal, recorte y borrado."""
    try:
        with sftp.open(ruta, "rb") as remoto:
            remoto.set_pipelined(True)
            with xr.open_dataset(remoto, engine="h5netcdf") as ds:
                return recortar(ds, variable), "lectura remota de la caja (h5netcdf sobre SFTP)"
    except Exception as error:  # noqa: BLE001
        print(f"  lectura remota no disponible ({type(error).__name__}); se descarga {posixpath.basename(ruta)}",
              flush=True)
    with tempfile.TemporaryDirectory() as carpeta:
        local = Path(carpeta) / posixpath.basename(ruta)
        sftp.get(ruta, str(local))
        with xr.open_dataset(local) as ds:
            sub = recortar(ds, variable)
        local.unlink()
    return sub, "descarga temporal del archivo global, recorte y borrado"


def main():
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    transporte, sftp = conectar()
    try:
        rutas = listar_ncs(sftp)
        print(f"{len(rutas)} archivos .nc en el servidor", flush=True)
        for variable in VARIABLES:
            destino = CARPETA_SALIDA / f"gleam_v4_{variable}_mensual_1998_2022_fonce.nc"
            if destino.exists() and Path(f"{destino}.meta.json").exists():
                print(f"{variable}: ya existe {destino.name}, no se descarga de nuevo.", flush=True)
                continue
            version, archivos = escoger_archivos(rutas, variable)
            print(f"{variable}: GLEAM v{version}, {len(archivos)} archivo(s)", flush=True)
            partes, modo = [], None
            for ruta in archivos:
                sub, modo = abrir_y_recortar(sftp, ruta, variable)
                if sub.sizes.get("time", 0):
                    partes.append(sub)
            datos = xr.concat(partes, dim="time").sortby("time") if len(partes) > 1 else partes[0]
            if datos.sizes["time"] != MESES_ESPERADOS:
                raise RuntimeError(f"{variable}: {datos.sizes['time']} meses en 1998–2022; se esperaban "
                                   f"{MESES_ESPERADOS}")
            destino = CARPETA_SALIDA / f"gleam_v4_{variable}_mensual_1998_2022_fonce.nc"
            datos.to_netcdf(destino)
            da = datos[variable]
            lat = [n for n in ("lat", "latitude") if n in datos.coords][0]
            lon = [n for n in ("lon", "longitude") if n in datos.coords][0]
            meta = {
                "archivo": destino.name,
                "fuente": "GLEAM4 (Miralles et al., 2025), Universidad de Gante, SFTP aether.ugent.be:2225",
                "version": f"v{version}",
                "variable": f"{variable}: {da.attrs.get('long_name', '')}",
                "unidades": da.attrs.get("units"),
                "periodo": f"{str(datos.time.values[0])[:7]} a {str(datos.time.values[-1])[:7]} "
                           f"({datos.sizes['time']} meses)",
                "recorte_espacial": (f"{datos.sizes[lat]} x {datos.sizes[lon]} celdas (lat x lon); centros lat "
                                     f"{float(datos[lat].min()):.3f} a {float(datos[lat].max()):.3f}, lon "
                                     f"{float(datos[lon].min()):.3f} a {float(datos[lon].max()):.3f}; caja {CAJA}"),
                "nan": int(da.isnull().sum()),
                "archivos_fuente": [posixpath.basename(r) for r in archivos],
                "url": f"sftp://{SERVIDOR}:{PUERTO} (usuario {USUARIO}; clave entregada por GLEAM al registrarse)",
                "fecha_descarga": datetime.date.today().isoformat(),
                "procesamiento": f"solo recorte espacial y temporal ({modo}); valores y atributos sin transformar",
                "script": "codigo/punto1/11_descarga_gleam_v4.py",
                "sha256": sha256_de(destino),
            }
            Path(f"{destino}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8", newline="\n")
            print(json.dumps(meta, ensure_ascii=False, indent=2), flush=True)
    finally:
        sftp.close()
        transporte.close()


if __name__ == "__main__":
    main()
