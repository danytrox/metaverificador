"""MetaVerificador — punto de entrada.

Sin argumentos: abre la interfaz gráfica (PySide6).
Con `--cli`: ejecuta el análisis por terminal y exporta informes.
"""
from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="MetaVerificador",
        description="Analiza metadatos de archivos de forma 100% local.",
    )
    p.add_argument("paths", nargs="*", help="Archivos o carpetas a analizar (modo CLI).")
    p.add_argument("--cli", action="store_true", help="Forzar modo línea de comandos.")
    p.add_argument("--csv", metavar="ARCHIVO.csv", help="Exportar resultados a CSV.")
    p.add_argument("--json", metavar="ARCHIVO.json", help="Exportar resultados a JSON.")
    p.add_argument("--html", metavar="ARCHIVO.html", help="Exportar resultados a HTML.")
    p.add_argument("--xlsx", metavar="ARCHIVO.xlsx", help="Exportar resultados a Excel (.xlsx).")
    p.add_argument("--template", metavar="PLANTILLA", help="Plantilla (.xlsx o .html) que define las columnas del informe.")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.cli or (args.paths and (args.csv or args.json or args.html or args.xlsx or not sys.stdout.isatty())):
        from app.cli import run_cli

        return run_cli(args)
    from app.ui import run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
