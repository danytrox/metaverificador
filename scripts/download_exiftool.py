"""Descarga el paquete Windows de ExifTool y lo deja en resources/exiftool/
para empaquetarlo dentro del .exe.

Fuente primaria: mirror de Oliver Betz (https://oliverbetz.de), el mismo
sistema de launcher + Perl portátil que exiftool.org usa para su paquete
oficial de Windows desde mediados de 2024. Es un enlace directo (sin el
challenge de Cloudflare que bloquea a SourceForge para descargas automáticas).

Estructura resultante en resources/exiftool/:
  exiftool.exe       (launcher, renombrado desde ExifTool.exe)
  exiftool_files/    (Perl portátil + biblioteca ExifTool)

Solo usa la biblioteca estándar; sin dependencias.
"""
from __future__ import annotations

import io
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile

VERSION = "13.59"
OB_BASE = "https://oliverbetz.de/cms/files/Artikel/ExifTool-for-Windows"
DEST = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "exiftool")
)

_LAUNCHER_NAMES = ("ExifTool.exe", "exiftool(-k).exe", "exiftool.exe")


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def _latest_version() -> str:
    try:
        txt = _fetch(f"{OB_BASE}/exiftool_latest_version.txt").decode("utf-8", errors="replace")
        v = txt.strip().splitlines()[0].strip()
        if re.fullmatch(r"\d+\.\d+", v):
            return v
    except OSError:
        pass
    return VERSION


def _extract(data: bytes) -> None:
    z = zipfile.ZipFile(io.BytesIO(data))
    z.extractall(DEST)
    # Normalizar el launcher a "exiftool.exe"
    for name in _LAUNCHER_NAMES:
        p = os.path.join(DEST, name)
        if os.path.isfile(p):
            target = os.path.join(DEST, "exiftool.exe")
            if os.path.normcase(name) != os.path.normcase("exiftool.exe"):
                if os.path.exists(target):
                    os.remove(target)
                os.rename(p, target)
            print(f"Launcher: {name!r} -> exiftool.exe")
            break
    else:
        print("ERROR: no se encontró el launcher de exiftool en el zip.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(os.path.join(DEST, "exiftool_files")):
        print("AVISO: el zip no trae exiftool_files/ (puede ser un exe PAR autónomo).")
    print(f"OK -> {os.path.join(DEST, 'exiftool.exe')}")


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    version = _latest_version()
    url = f"{OB_BASE}/exiftool-{version}_64.zip"
    try:
        print(f"Descargando {url}")
        data = _fetch(url)
    except OSError as exc:
        print(
            f"\nNo se pudo descargar ExifTool automáticamente ({exc}).\n"
            "Descárgalo manualmente desde https://exiftool.org (Windows Executable)\n"
            "o desde https://oliverbetz.de/pages/Artikel/ExifTool-for-Windows,\n"
            "descomprime el zip y deja su contenido en:\n"
            f"  {DEST}\n",
            file=sys.stderr,
        )
        return 1
    print(f"Descargado {len(data)} bytes (versión {version}).")
    _extract(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
