"""Sistema de plantillas opcional.

Permite reordenar y seleccionar las columnas del informe a partir de una
plantilla (Excel .xlsx o tabla .html). Si no se carga ninguna plantilla, los
exportadores siguen usando su salida por defecto (columnas fijas actuales).

La plantilla se interpreta de forma determinística:

- Un encabezado que coincide con una etiqueta ExifTool (``Grupo:Etiqueta``,
  p. ej. ``EXIF:Model`` o ``File:FileSize``) se resuelve directamente contra
  los metadatos extraídos.
- Cualquier otro encabezado se clasifica por palabras clave (autor, título,
  fecha, software, tipo, ruta, etc.) y se resuelve contra el ``Summary``.

``app.llm.py`` añade un mapeo semántico opcional con IA local para encabezados
ambiguos, manteniendo esta resolución determinística como respaldo.
"""
from __future__ import annotations

import html.parser
import os
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class ColumnSpec:
    """Una columna del informe: su encabezado y cómo resolver su valor."""
    header: str
    kind: str = "tag"                 # filename|path|filetype|author_bool|author_values|title|date|software|warnings|tags|tag
    source: Optional[str] = None      # etiqueta ExifTool (kind="tag") o atributo (kind="raw")


@dataclass
class TemplateSpec:
    """Plantilla resuelta: lista ordenada de columnas."""
    name: str = "plantilla"
    columns: list[ColumnSpec] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Normalización y clasificación
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    """Minúsculas, sin tildes, espacios colapsados (para comparar encabezados)."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


# Orden de prioridad: los más específicos primero.
_KIND_KEYWORDS: dict[str, list[str]] = {
    "author_values": ["autor valores", "autor detalle", "autor (valores)", "autor (detalle)",
                      "valor autor", "valores autor", "detalle autor", "author values",
                      "author detail", "campo autor"],
    "author_bool": ["autor", "author", "tiene autor", "autor?", "creador", "creator",
                    "artista", "artist", "fotografo", "fotografa", "by-line", "byline"],
    "filename": ["archivo", "nombre", "nombre de archivo", "filename", "file name", "fichero"],
    "path": ["ruta", "ubicacion", "carpeta", "path", "ruta completa", "directorio"],
    "filetype": ["tipo", "formato", "type", "format", "mime", "mimetype",
                 "tipo de archivo", "extension", "ext"],
    "title": ["titulo", "title", "objectname", "headline"],
    "date": ["fecha", "date", "fecha de creacion", "fecha creacion", "fecha de modificacion",
             "creation date", "created", "creado", "creacion", "datetime", "modificado"],
    "software": ["software", "programa", "aplicacion", "application", "producer",
                 "creatortool", "creator tool", "generador", "generator", "herramienta"],
    "warnings": ["advertencia", "advertencias", "aviso", "avisos", "warning", "warnings", "notas"],
    "tags": ["metadatos", "detalle", "detail", "tags", "todos los campos", "campos"],
}

_KIND_PRIORITY = [
    "author_values", "author_bool", "filetype", "filename", "path",
    "date", "title", "software", "warnings", "tags",
]

_TAG_RE_HEADER = r"^[A-Za-z][A-Za-z0-9_-]*:[A-Za-z][A-Za-z0-9_ /.-]*$"


def _looks_like_tag(header: str) -> bool:
    import re

    return bool(re.match(_TAG_RE_HEADER, header.strip()))


def classify_header(header: str) -> ColumnSpec:
    """Convierte un encabezado de plantilla en un ``ColumnSpec``."""
    raw = str(header).strip()
    if not raw:
        return ColumnSpec(header="", kind="tag")
    if _looks_like_tag(raw):
        return ColumnSpec(header=raw, kind="tag", source=raw)
    norm = _norm(raw)
    best_kind = None
    best_score = 0
    for kind in _KIND_PRIORITY:
        for kw in _KIND_KEYWORDS[kind]:
            score = 0
            if norm == kw:
                score = 3
            elif norm.startswith(kw) or kw in norm:
                score = 2
            if score > best_score:
                best_score = score
                best_kind = kind
    if best_kind is None:
        # Sin coincidencia: encabezado desconocido (la IA local puede resolverlo).
        return ColumnSpec(header=raw, kind="unknown", source=None)
    return ColumnSpec(header=raw, kind=best_kind)


# ---------------------------------------------------------------------------
# Parseo de plantillas
# ---------------------------------------------------------------------------

def _find_header_row(values: list[list[object]], max_scan: int = 10) -> int:
    """Devuelve el índice (0-based) de la fila con más celdas no vacías."""
    best = -1
    best_count = -1
    for i, row in enumerate(values[:max_scan]):
        count = sum(1 for v in row if v is not None and str(v).strip() != "")
        if count > best_count:
            best_count = count
            best = i
    return best if best >= 0 else 0


def parse_xlsx(path: str) -> TemplateSpec:
    """Lee los encabezados de la primera hoja de un .xlsx como plantilla."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    if not rows:
        return TemplateSpec(name=os.path.basename(path))

    header_idx = _find_header_row(rows)
    headers = [str(v).strip() for v in rows[header_idx] if v is not None and str(v).strip() != ""]
    columns = [classify_header(h) for h in headers]
    return TemplateSpec(name=os.path.basename(path), columns=columns)


class _TableHeaderParser(html.parser.HTMLParser):
    """Extrae el texto de los <th> (o <td> de la primera fila) en orden."""

    def __init__(self):
        super().__init__()
        self._in_cell = False
        self._buf: list[str] = []
        self.headers: list[str] = []
        self._fallback: list[str] = []
        self._in_first_row = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr" and not self.headers and not self._fallback:
            self._in_first_row = True
        if tag in ("th", "td"):
            self._in_cell = True
            self._buf = []

    def handle_data(self, data):
        if self._in_cell:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self._in_cell:
            text = " ".join("".join(self._buf).split()).strip()
            if text:
                if tag == "th":
                    self.headers.append(text)
                elif self._in_first_row:
                    self._fallback.append(text)
            self._in_cell = False
        if tag == "tr":
            self._in_first_row = False


def parse_html(path: str) -> TemplateSpec:
    """Lee los encabezados de la primera tabla de un .html como plantilla."""
    with open(path, encoding="utf-8", errors="replace") as f:
        data = f.read()
    parser = _TableHeaderParser()
    parser.feed(data)
    headers = parser.headers or parser._fallback
    columns = [classify_header(h) for h in headers]
    return TemplateSpec(name=os.path.basename(path), columns=columns)


def load_template(path: str) -> TemplateSpec:
    """Carga una plantilla según su extensión (.xlsx o .html)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        spec = parse_xlsx(path)
    elif ext in (".html", ".htm"):
        spec = parse_html(path)
    else:
        raise ValueError(f"Formato de plantilla no soportado: {ext or path}")
    if not spec.columns:
        raise ValueError("La plantilla no tiene encabezados de columna.")
    return spec


# ---------------------------------------------------------------------------
# Resolución de valores
# ---------------------------------------------------------------------------

def _as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple, set)):
        return " | ".join(_as_text(x) for x in v)
    return str(v)


def _get_tag(tags: dict, key: str):
    """Búsqueda insensible a mayúsculas de una etiqueta ``Grupo:Tag``."""
    k = key.strip().lower()
    for tk, tv in tags.items():
        if str(tk).strip().lower() == k:
            return tv
    return None


def format_tags(tags: dict) -> str:
    return "\n".join(f"{k}: {_as_text(v)}" for k, v in sorted(tags.items()))


def resolve_cell(column: ColumnSpec, summary) -> str:
    """Resuelve el valor de una columna para un archivo ya analizado (Summary)."""
    kind = column.kind
    if kind == "filename":
        return summary.filename
    if kind == "path":
        return summary.path
    if kind == "filetype":
        return summary.filetype
    if kind == "author_bool":
        return "SÍ" if summary.author_found else "NO"
    if kind == "author_values":
        return "; ".join(summary.author_values)
    if kind == "title":
        return summary.title or ""
    if kind == "date":
        return summary.creation_date or ""
    if kind == "software":
        return "; ".join(summary.software)
    if kind == "warnings":
        return "; ".join(summary.warnings)
    if kind == "tags":
        return format_tags(summary.tags)
    if kind == "tag":
        if column.source:
            v = _get_tag(summary.tags, column.source)
            if v is not None:
                return _as_text(v)
        return ""
    if kind == "unknown":
        return ""
    return ""


def is_author_column(column: ColumnSpec) -> bool:
    """Indica si la columna marca el estado de autor (para resaltar filas)."""
    return column.kind == "author_bool"
