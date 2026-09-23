"""Modo línea de comandos (útil para automatización y pruebas sin GUI)."""
from __future__ import annotations

import argparse
import sys

from .analyzer import summarize
from .extractor import get_backend
from .llm import enhance_template_columns, is_available as llm_is_available
from .report import export_csv, export_html, export_json, export_xlsx
from .template import load_template


def run_cli(args: argparse.Namespace) -> int:
    backend = get_backend()
    engine = type(backend).__name__
    results = backend.extract_many(args.paths, progress_cb=None)
    summaries = [summarize(r) for r in results]

    template = None
    if getattr(args, "template", None):
        try:
            template = load_template(args.template)
        except Exception as exc:  # noqa: BLE001
            print(f"Error al cargar la plantilla: {exc}", file=sys.stderr)
            return 1
        if llm_is_available():
            template.columns = enhance_template_columns(template.columns)
        print(f"Plantilla: {template.name} ({len(template.columns)} columnas)")

    print(f"Backend: {engine}")
    print(f"{'ARCHIVO':<40} {'AUTOR':<4} {'TIPO':<22} TITULO")
    print("-" * 100)
    for s in summaries:
        autor = "SÍ" if s.author_found else "NO"
        print(f"{s.filename:<40} {autor:<4} {s.filetype:<22} {s.title}")
    print("-" * 100)
    missing = sum(1 for s in summaries if not s.author_found)
    print(f"Total: {len(summaries)} | Sin autor: {missing}")

    if args.csv:
        export_csv(summaries, args.csv, template=template)
        print(f"CSV  -> {args.csv}")
    if args.json:
        export_json(summaries, args.json)
        print(f"JSON -> {args.json}")
    if args.html:
        export_html(summaries, args.html, template=template)
        print(f"HTML -> {args.html}")
    if args.xlsx:
        export_xlsx(summaries, args.xlsx, template=template)
        print(f"XLSX -> {args.xlsx}")
    return 0
