"""Descarga el modelo GGUF ligero para el mapeo de plantillas (opcional).

Se descarga una sola vez. Si ya existe, se omite.
Uso:  python scripts/download_model.py [--force]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm import MODEL_FILE, download_model, model_dir  # noqa: E402


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> int:
    p = argparse.ArgumentParser(description="Descarga el modelo GGUF local (opcional).")
    p.add_argument("--force", action="store_true", help="Redescargar aunque ya exista.")
    args = p.parse_args()

    dest = os.path.join(model_dir(), MODEL_FILE)
    if os.path.isfile(dest) and not args.force:
        print(f"El modelo ya existe ({_human(os.path.getsize(dest))}): {dest}")
        return 0

    print(f"Descargando {MODEL_FILE} …")
    print(f"  destino: {dest}")

    def _progress(done: int, total: int):
        if total:
            print(f"\r  {_human(done)} / {_human(total)} ({done * 100 / total:.1f}%)", end="")

    try:
        download_model(progress_cb=_progress, force=args.force)
    except Exception as exc:  # noqa: BLE001
        print()
        print(f"Error al descargar: {exc}", file=sys.stderr)
        return 1
    print()
    print(f"Listo: {_human(os.path.getsize(dest))} en {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
