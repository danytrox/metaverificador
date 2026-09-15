"""Modo línea de comandos (útil para automatización y pruebas sin GUI)."""
from __future__ import annotations

import argparse

from .analyzer import summarize
from .extractor import get_backend
from .report import export_csv, export_html, export_json


def run_cli(args: argparse.Namespace) -> int:
    backend = get_backend()
    engine = type(backend).__name__
    results = backend.extract_many(args.paths, progress_cb=None)
    summaries = [summarize(r) for r in results]

    print(f"Backend: {engine}")
    print(f"{'ARCHIVO':<40} {'AUTOR':<4} {'TIPO':<22} TITULO")
    print("-" * 100)
    for s in summaries:
        autor = "SI" if s.author_found else "NO"
        print(f"{s.filename:<40} {autor:<4} {s.filetype:<22} {s.title}")
    print("-" * 100)
    missing = sum(1 for s in summaries if not s.author_found)
    print(f"Total: {len(summaries)} | Sin autor: {missing}")

    if args.csv:
        export_csv(summaries, args.csv)
        print(f"CSV  -> {args.csv}")
    if args.json:
        export_json(summaries, args.json)
        print(f"JSON -> {args.json}")
    if args.html:
        export_html(summaries, args.html)
        print(f"HTML -> {args.html}")
    return 0
