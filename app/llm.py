"""Capa de IA opcional (Fase 2).

Usa un modelo local pequeño (Qwen2.5-1.5B en GGUF, vía llama-cpp-python) para
mapear encabezados de plantilla *ambiguos* a campos de metadatos reales.

Es totalmente opcional:

- Si el modelo no está descargado o `llama-cpp-python` no está instalado, la
  aplicación sigue funcionando con el mapeo determinístico de ``template.py``.
- El modelo corre **una vez por plantilla** (no por archivo); el relleno de
  cada archivo se hace de forma determinística con el spec resultante.

El modelo se descarga aparte con ``scripts/download_model.py`` o se apunta con
la variable de entorno ``METAVERIFICADOR_MODEL``.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

from .template import ColumnSpec, classify_header

MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"

# Etiquetas ExifTool habituales que se dan como "vocabulario" al modelo.
_TAG_VOCABULARY = [
    "File:FileName", "File:FileSize", "File:FileType", "File:MIMEType",
    "File:FileModifyDate", "File:Directory",
    "EXIF:Make", "EXIF:Model", "EXIF:Software", "EXIF:Artist", "EXIF:DateTimeOriginal",
    "EXIF:CreateDate", "EXIF:GPSLatitude", "EXIF:GPSLongitude", "EXIF:ImageWidth",
    "EXIF:ImageHeight", "EXIF:ExposureTime", "EXIF:FNumber", "EXIF:ISO",
    "EXIF:LensModel", "EXIF:Copyright",
    "IPTC:By-line", "IPTC:ObjectName", "IPTC:Keywords", "IPTC:CopyrightNotice",
    "XMP:Creator", "XMP:Title", "XMP:Description", "XMP:CreateDate",
    "XMP-dc:Creator", "XMP-dc:Title", "XMP-dc:Subject", "XMP-dc:Rights",
    "PDF:Author", "PDF:Title", "PDF:Creator", "PDF:Producer", "PDF:CreateDate",
    "PDF:Subject", "PDF:Keywords",
    "Composite:ImageSize", "Composite:Megapixels", "Composite:GPSPosition",
]

_VOCAB_LOWER = {t.lower() for t in _TAG_VOCABULARY}

_VALID_KINDS = {
    "filename", "path", "filetype", "author_bool", "author_values",
    "title", "date", "software", "warnings", "tags", "tag",
}


def model_dir() -> str:
    """Carpeta donde se guarda/descargan los modelos GGUF."""
    if os.environ.get("METAVERIFICADOR_MODELS_DIR"):
        return os.environ["METAVERIFICADOR_MODELS_DIR"]
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates = [os.path.join(exe_dir, "models")]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidates.append(os.path.join(base, "models"))
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, ".metaverificador", "models"))
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            if os.access(d, os.W_OK):
                return d
        except OSError:
            continue
    return candidates[-1]


def find_model() -> Optional[str]:
    """Localiza un GGUF disponible (env var, carpeta models, o exe dir)."""
    env = os.environ.get("METAVERIFICADOR_MODEL")
    if env and os.path.isfile(env):
        return env
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    locations = [model_dir(), exe_dir]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        locations.append(base)
    for d in locations:
        for name in (MODEL_FILE,):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        for name in os.listdir(d) if os.path.isdir(d) else []:
            if name.lower().endswith(".gguf"):
                return os.path.join(d, name)
    return None


def is_available() -> bool:
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    return find_model() is not None


def llama_cpp_installed() -> bool:
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    return True


def download_model(progress_cb=None, force: bool = False) -> str:
    """Descarga el GGUF (una sola vez) y devuelve su ruta local.

    ``progress_cb`` recibe ``(bytes_descargados, total)``; ``total`` puede ser 0
    si el servidor no informa el tamaño.
    """
    import urllib.request

    dest = os.path.join(model_dir(), MODEL_FILE)
    if os.path.isfile(dest) and not force:
        return dest

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "MetaVerificador"})
        with urllib.request.urlopen(req) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb:
                        progress_cb(done, total)
        os.replace(tmp, dest)
    except Exception:
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
    return dest


def ensure_model(progress_cb=None) -> Optional[str]:
    """Devuelve la ruta del modelo, descargándolo en primer uso si hace falta.

    Devuelve ``None`` si no se puede obtener (sin red o sin llama-cpp).
    """
    existing = find_model()
    if existing:
        return existing
    if not llama_cpp_installed():
        return None
    try:
        return download_model(progress_cb=progress_cb)
    except Exception:  # noqa: BLE001
        return None


class LLMMapper:
    """Mapea encabezados ambiguos a campos de metadatos con un modelo local."""

    def __init__(self, model_path: Optional[str] = None):
        self._model_path = model_path or find_model()
        self._llm = None

    @property
    def available(self) -> bool:
        return self._model_path is not None

    def _ensure_loaded(self):
        if self._llm is not None:
            return
        if not self._model_path:
            raise RuntimeError("No hay modelo local disponible.")
        from llama_cpp import Llama

        self._llm = Llama(
            model_path=self._model_path,
            n_ctx=4096,
            n_gpu_layers=0,
            verbose=False,
        )

    def _map_batch(self, headers: list[str]) -> dict[str, ColumnSpec]:
        """Pide al modelo el mapeo de una lista de encabezados."""
        self._ensure_loaded()
        vocab = ", ".join(_TAG_VOCABULARY)
        prompt = (
            "Mapea cada encabezado de plantilla a un campo de metadatos. "
            "Para cada encabezado elige un 'kind' de esta lista: "
            "filename, path, filetype, author_bool, author_values, title, date, "
            "software, warnings, tags, tag. "
            "Usa 'tag' solo si el encabezado corresponde a una etiqueta real; "
            "entonces pon en 'source' la etiqueta exacta de la lista de etiquetas. "
            "Si no corresponde a una etiqueta real, usa el 'kind' lógico apropiado "
            "y 'source' null. Etiquetas disponibles: "
            f"{vocab}.\n\n"
            "Responde SOLO con JSON, sin texto adicional, con esta forma:\n"
            '{"mappings": [{"header": "<encabezado>", "kind": "<kind>", "source": "<etiqueta o null>"}]}'
        )
        user = "Encabezados: " + json.dumps(headers, ensure_ascii=False)
        resp = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        text = resp["choices"][0]["message"]["content"]
        return self._parse_response(text, headers)

    @staticmethod
    def _parse_response(text: str, headers: list[str]) -> dict[str, ColumnSpec]:
        result: dict[str, ColumnSpec] = {}
        try:
            start = text.find("{")
            end = text.rfind("}")
            data = json.loads(text[start : end + 1])
            for m in data.get("mappings", []):
                h = str(m.get("header", "")).strip()
                if h not in headers:
                    continue
                kind = str(m.get("kind", "")).strip().lower()
                if kind not in _VALID_KINDS:
                    continue
                src = m.get("source")
                source = str(src).strip() if src else None
                if source is not None and source.lower() not in _VOCAB_LOWER:
                    source = None
                result[h] = ColumnSpec(header=h, kind=kind, source=source)
        except (json.JSONDecodeError, AttributeError, ValueError):
            pass
        return result

    def map_columns(self, columns: list[ColumnSpec]) -> list[ColumnSpec]:
        """Mejora el mapeo de las columnas ambiguas usando el modelo local.

        Solo se consulta al modelo para encabezados que el clasificador
        determinístico no supo resolver (kind == 'tag' sin coincidencia real).
        """
        if not self.available:
            return columns
        ambiguous = [c for c in columns if c.kind == "unknown"]
        if not ambiguous:
            return columns
        headers = [c.header for c in ambiguous]
        try:
            mapped = self._map_batch(headers)
        except Exception:  # noqa: BLE001
            return columns
        out = []
        for c in columns:
            if c.kind == "unknown" and c.header in mapped:
                out.append(mapped[c.header])
            else:
                out.append(c)
        return out


_mapper_cache: Optional[LLMMapper] = None


def get_mapper() -> Optional[LLMMapper]:
    """Devuelve un mapeador IA (cacheado) si hay modelo local y llama-cpp instalado."""
    global _mapper_cache
    if _mapper_cache is not None:
        return _mapper_cache
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return None
    path = find_model()
    if not path:
        return None
    _mapper_cache = LLMMapper(path)
    return _mapper_cache


def enhance_template_columns(columns: list[ColumnSpec]) -> list[ColumnSpec]:
    mapper = get_mapper()
    if mapper is None:
        return columns
    return mapper.map_columns(columns)
