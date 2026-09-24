"""Motor de extracción de metadatos. 100% local.

Backend primario: ExifTool (el mismo motor que usan los sitios web de
metadatos), invocado como subproceso local. Ningún archivo sale del equipo.

Backend de respaldo: pypdf + Pillow, para que la aplicación no quede inútil
si ExifTool no está disponible (o como verificación cruzada).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

# Archivos por invocación de exiftool (evita superar el límite de longitud de
# la línea de comandos en Windows).
_BATCH_SIZE = 200

# En Windows, oculta la ventana de consola que ExifTool abriría al ejecutarse
# desde la app empaquetada (sin consola propia). En otros SO el valor es 0.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


@dataclass
class FileResult:
    path: str
    tags: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def find_exiftool() -> Optional[str]:
    """Localiza el ejecutable de exiftool (empaquetado o del sistema)."""
    names = ("exiftool.exe", "ExifTool.exe", "exiftool")
    # 1) Empaquetado con PyInstaller (onefile extrae a sys._MEIPASS)
    base = getattr(sys, "_MEIPASS", None)
    if base:
        for name in names:
            p = os.path.join(base, "exiftool", name)
            if os.path.isfile(p):
                return p
    # 2) Junto al ejecutable (distribución onedir)
    exe_dir = os.path.dirname(sys.executable)
    for name in names:
        p = os.path.join(exe_dir, "exiftool", name)
        if os.path.isfile(p):
            return p
    # 3) En el árbol de fuentes (desarrollo)
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "exiftool")
    for name in names:
        p = os.path.normpath(os.path.join(src, name))
        if os.path.isfile(p):
            return p
    # 4) Del sistema (PATH)
    return shutil.which("exiftool")


class ExifToolBackend:
    """Extrae metadatos completos con ExifTool (formato JSON, grupos incluidos)."""

    def __init__(self):
        self.exe = find_exiftool()

    @property
    def available(self) -> bool:
        return self.exe is not None

    def extract_many(
        self,
        paths: Iterable[str],
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_cb: Optional[Callable[[], bool]] = None,
    ) -> list[FileResult]:
        paths = [os.path.abspath(p) for p in paths]
        results: list[FileResult] = []
        total = len(paths)
        done = 0
        for i in range(0, total, _BATCH_SIZE):
            if cancel_cb and cancel_cb():
                break
            chunk = paths[i : i + _BATCH_SIZE]
            cmd = [
                self.exe, "-json", "-G", "-a", "-s",
                "-charset", "filename=UTF8", *chunk,
            ]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8",
                errors="replace", creationflags=_NO_WINDOW,
            )
            parsed = None
            if proc.returncode == 0:
                try:
                    parsed = json.loads(proc.stdout)
                except json.JSONDecodeError:
                    parsed = None
            if parsed is not None:
                for item in parsed:
                    src = item.get("SourceFile") or ""
                    tags = {k: v for k, v in item.items() if k != "SourceFile"}
                    err = tags.get("Error") or None
                    results.append(FileResult(path=src, tags=tags, error=err))
            else:
                # Reintentar archivo por archivo (algún archivo rompió el lote)
                for p in chunk:
                    if cancel_cb and cancel_cb():
                        break
                    results.append(self._extract_one(p))
            done += len(chunk)
            if progress_cb:
                progress_cb(done, total)
        return results

    def _extract_one(self, path: str) -> FileResult:
        cmd = [self.exe, "-json", "-G", "-a", "-s", "-charset", "filename=UTF8", path]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", creationflags=_NO_WINDOW,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                if data:
                    item = data[0]
                    tags = {k: v for k, v in item.items() if k != "SourceFile"}
                    err = tags.get("Error") or None
                    return FileResult(path=os.path.abspath(path), tags=tags, error=err)
            except json.JSONDecodeError:
                pass
        msg = (proc.stderr or "").strip() or "exiftool: error desconocido"
        return FileResult(path=os.path.abspath(path), error=msg)


class PurePythonBackend:
    """Respaldo sin exiftool: PDF (pypdf), imágenes (Pillow) y datos de archivo."""

    def extract_many(
        self,
        paths: Iterable[str],
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_cb: Optional[Callable[[], bool]] = None,
    ) -> list[FileResult]:
        paths = list(paths)
        results = []
        total = len(paths)
        for i, p in enumerate(paths):
            if cancel_cb and cancel_cb():
                break
            results.append(self._extract_one(os.path.abspath(p)))
            if progress_cb:
                progress_cb(i + 1, total)
        return results

    def _extract_one(self, path: str) -> FileResult:
        tags: dict = {}
        try:
            st = os.stat(path)
            import datetime

            tags["File:FileName"] = os.path.basename(path)
            tags["File:FileSize"] = str(st.st_size)
            tags["File:FileModifyDate"] = datetime.datetime.fromtimestamp(
                st.st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S")
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                self._extract_pdf(path, tags)
            elif ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif", ".bmp", ".webp"):
                self._extract_image(path, tags)
            tags["App:Backend"] = "python (respaldo)"
            return FileResult(path=path, tags=tags)
        except Exception as exc:  # noqa: BLE001
            return FileResult(path=path, error=str(exc))

    @staticmethod
    def _extract_pdf(path: str, tags: dict) -> None:
        from pypdf import PdfReader

        reader = PdfReader(path)
        meta = reader.metadata or {}
        for k, v in meta.items():
            if v not in (None, "", " "):
                tags[f"PDF:{str(k).strip('/')}"] = str(v)
        tags["File:FileType"] = "PDF"
        tags["File:PageCount"] = str(len(reader.pages))

    @staticmethod
    def _extract_image(path: str, tags: dict) -> None:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(path) as im:
            tags["File:ImageWidth"] = str(im.width)
            tags["File:ImageHeight"] = str(im.height)
            tags["File:FileType"] = (im.format or "").upper()
            exif = im.getexif()
            if exif:
                for tag_id, val in exif.items():
                    name = TAGS.get(tag_id, str(tag_id))
                    tags[f"EXIF:{name}"] = str(val)


def get_backend():
    """Devuelve el mejor backend disponible (ExifTool primero)."""
    ex = ExifToolBackend()
    if ex.available:
        return ex
    return PurePythonBackend()
