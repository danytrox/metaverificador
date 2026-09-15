"""Descarga el binario oficial de ExifTool para Windows y lo deja como
resources/exiftool/exiftool.exe (para empaquetarlo dentro del .exe).

- Solo usa la biblioteca estándar (sin dependencias).
- Descarga directa desde exiftool.org / SourceForge (canales oficiales).
- El archivo del zip se llama "exiftool(-k).exe"; se renombra a exiftool.exe
  para uso en línea de comandos (tal como indica la documentación oficial).
"""
from __future__ import annotations

import io
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
import zipfile

VERSION = "13.59"  # versión conocida; si da 404, se busca la última automáticamente
DEST = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "exiftool")
)

_DOWNLOAD_URLS = [
    "https://downloads.sourceforge.net/project/exiftool/exiftool-{ver}_64.zip",
    "https://sourceforge.net/projects/exiftool/files/exiftool-{ver}_64.zip/download",
]
_HOMEPAGE = "https://exiftool.org/"


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _latest_version() -> str:
    """Descubre la última versión de Windows desde la portada de exiftool.org."""
    html = _fetch(_HOMEPAGE).decode("utf-8", errors="replace")
    versions = re.findall(r"exiftool-(\d+\.\d+)_64\.zip", html)
    if not versions:
        return VERSION
    return max(versions, key=lambda v: [int(x) for x in v.split(".")])


def _download(version: str) -> bytes:
    last_err: Exception | None = None
    for tmpl in _DOWNLOAD_URLS:
        url = tmpl.format(ver=version)
        try:
            print(f"Descargando {url}")
            return _fetch(url)
        except urllib.error.HTTPError as exc:
            last_err = exc
            print(f"  HTTP {exc.code} en {url}")
        except OSError as exc:
            last_err = exc
            print(f"  Error de red en {url}: {exc}")
    raise last_err or RuntimeError("descarga fallida")


def _extract_exe(data: bytes) -> str:
    z = zipfile.ZipFile(io.BytesIO(data))
    candidates = [
        n for n in z.namelist()
        if n.lower().endswith(".exe") and "exiftool" in os.path.basename(n).lower()
    ]
    if not candidates:
        print("ERROR: no se encontró ningún exiftool*.exe dentro del zip.", file=sys.stderr)
        print("Contenido del zip:", file=sys.stderr)
        for n in z.namelist():
            print(f"  {n}", file=sys.stderr)
        sys.exit(1)
    src = candidates[0]
    target = os.path.join(DEST, "exiftool.exe")
    with z.open(src) as fsrc, open(target, "wb") as fdst:
        shutil.copyfileobj(fsrc, fdst)
    print(f"Extraído {src!r} -> {target}")
    return target


def _print_manual_help() -> None:
    print(
        "\nNo se pudo descargar ExifTool automáticamente (bloqueo de red, proxy o IP restringida).\n"
        "Descárgalo manualmente desde https://exiftool.org (sección 'Windows Executable'),\n"
        "descomprime el zip y coloca el ejecutable renombrado como:\n"
        f"  {os.path.join(DEST, 'exiftool.exe')}\n",
        file=sys.stderr,
    )


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    version = VERSION
    try:
        data = _download(version)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            _print_manual_help()
            return 1
        version = _latest_version()
        print(f"Versión {VERSION} no disponible; usando la última: {version}")
        try:
            data = _download(version)
        except OSError:
            _print_manual_help()
            return 1
    except OSError:
        _print_manual_help()
        return 1
    print(f"Descargado {len(data)} bytes.")
    _extract_exe(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
