"""Análisis de metadatos: localiza autor, título, fecha y software."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

# Etiquetas que representan a una PERSONA (autor/creador/fotógrafo)
_AUTHOR_TAGS = {"author", "artist", "by-line", "byline", "owner", "credit", "lastmodifiedby"}
# Grupos en los que "Creator" es una persona, no software
_CREATOR_IS_PERSON_GROUPS = {
    "xmp-dc", "dc", "exif", "iptc", "xmp-iptc", "photoshop", "openxml",
    "office", "microsoft", "xmp", "icc",
}
_SOFTWARE_TAGS = {
    "creatortool", "producer", "software", "historysoftwareagent",
    "application", "generator", "encodedby",
}
_TITLE_TAGS = {"title", "objectname", "headline"}
_DATE_TAGS = {"createdate", "creationdate", "datetimeoriginal", "datetimecreated", "contentcreated"}


def _split_key(key: str) -> tuple[str, str]:
    if ":" in key:
        group, _, tag = key.partition(":")
        return group.strip().lower(), tag.strip().lower()
    return "", key.strip().lower()


def _is_author_key(key: str) -> bool:
    group, tag = _split_key(key)
    if tag in _AUTHOR_TAGS:
        return True
    if tag == "creator":
        # En PDF "Creator" es el software; en XMP-dc/EXIF/IPTC es el autor.
        return group in _CREATOR_IS_PERSON_GROUPS
    return False


def _is_software_key(key: str) -> bool:
    group, tag = _split_key(key)
    if tag in _SOFTWARE_TAGS:
        return True
    if tag == "creator" and group == "pdf":
        return True  # PDF:Creator = software que generó el archivo
    return False


def _first(tags: dict, wanted: set) -> str:
    for key, value in tags.items():
        _, tag = _split_key(key)
        if tag in wanted and value not in (None, "", " "):
            return str(value)
    return ""


def _collect(tags: dict, pred) -> list[str]:
    out = []
    for key, value in tags.items():
        if pred(key) and value not in (None, "", " "):
            out.append(f"{key}: {value}")
    return out


@dataclass
class Summary:
    path: str
    filename: str
    filetype: str = ""
    author_found: bool = False
    author_values: list = field(default_factory=list)
    author_tags: list = field(default_factory=list)
    title: str = ""
    creation_date: str = ""
    software: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    tags: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "filename": self.filename,
            "filetype": self.filetype,
            "author_found": self.author_found,
            "author_values": list(self.author_values),
            "author_tags": list(self.author_tags),
            "title": self.title,
            "creation_date": self.creation_date,
            "software": list(self.software),
            "warnings": list(self.warnings),
        }


def summarize(result) -> Summary:
    tags = result.tags or {}
    s = Summary(
        path=os.path.abspath(result.path),
        filename=os.path.basename(result.path),
        tags=dict(tags),
    )

    s.filetype = tags.get("File:FileType", tags.get("File:MIMEType", ""))
    if result.error:
        s.warnings.append(f"Error: {result.error}")

    # Advertencias nativas de exiftool
    for key in ("Warning",):
        if key in tags and tags[key] not in (None, "", " "):
            s.warnings.append(f"{key}: {tags[key]}")

    # Autor
    s.author_tags = [k for k in tags if _is_author_key(k) and tags[k] not in (None, "", " ")]
    s.author_values = [f"{k}: {tags[k]}" for k in s.author_tags]
    s.author_found = bool(s.author_values)

    # Título / fecha / software
    s.title = _first(tags, _TITLE_TAGS)
    s.creation_date = _first(tags, _DATE_TAGS)
    s.software = _collect(tags, _is_software_key)

    # Avisos específicos
    if not s.author_found:
        s.warnings.append("Sin autor identificado (campo de autor vacío o inexistente).")
    if not s.author_found and s.filetype.lower() == "pdf" and any(
        "indesign" in v.lower() for v in s.software
    ):
        s.warnings.append(
            "PDF exportado desde InDesign sin autor: probablemente el campo /Author "
            "y dc:creator nunca se completaron."
        )
    if tags.get("App:Backend"):
        s.warnings.append("Extracción limitada (backend de respaldo Python, sin ExifTool).")

    return s
