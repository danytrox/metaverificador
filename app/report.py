"""Exportación de resultados a CSV, JSON y HTML (todo local, sin CDN ni red)."""
from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from typing import Iterable

from .analyzer import Summary


def _summaries_to_list(items: Iterable[Summary]) -> list[Summary]:
    return list(items)


def export_csv(summaries: Iterable[Summary], path: str) -> None:
    summaries = _summaries_to_list(summaries)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            "Archivo", "Ruta", "Tipo", "Autor", "Autor_valores", "Titulo",
            "Fecha_creacion", "Software", "Advertencias",
        ])
        for s in summaries:
            w.writerow([
                s.filename,
                s.path,
                s.filetype,
                "SI" if s.author_found else "NO",
                "; ".join(s.author_values),
                s.title,
                s.creation_date,
                "; ".join(s.software),
                "; ".join(s.warnings),
            ])


def export_json(summaries: Iterable[Summary], path: str) -> None:
    summaries = _summaries_to_list(summaries)
    payload = []
    for s in summaries:
        rec = s.to_dict()
        rec["tags"] = s.tags
        payload.append(rec)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"generated": datetime.now().isoformat(timespec="seconds"),
             "backend": "local",
             "files": payload},
            f, ensure_ascii=False, indent=2,
        )


_HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MetaVerificador - Reporte</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#1a1a1a;}}
 h1{{font-size:20px;}}
 .meta{{color:#666;font-size:13px;margin-bottom:16px;}}
 table{{border-collapse:collapse;width:100%;font-size:13px;}}
 th,td{{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top;}}
 th{{background:#f2f2f2;}}
 tr.sin-autor td{{background:#fdecea;}}
 .pill{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:bold;}}
 .si{{background:#d4edda;color:#155724;}}
 .no{{background:#f8d7da;color:#721c24;}}
 details{{margin-top:4px;}}
 pre{{background:#f7f7f7;padding:8px;overflow:auto;font-size:11px;}}
</style>
</head>
<body>
<h1>MetaVerificador - Reporte de metadatos</h1>
<div class="meta">Generado {generated} · {n} archivo(s) · análisis 100% local</div>
<table>
<thead><tr><th>Archivo</th><th>Tipo</th><th>Autor</th><th>Autor (valores)</th><th>Título</th><th>Fecha</th><th>Software</th><th>Advertencias</th><th>Detalle</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>
"""


def export_html(summaries: Iterable[Summary], path: str) -> None:
    summaries = _summaries_to_list(summaries)
    rows = []
    for s in summaries:
        cls = "" if s.author_found else "sin-autor"
        pill = '<span class="pill si">SI</span>' if s.author_found else '<span class="pill no">NO</span>'
        tags_html = "<pre>" + html.escape(
            "\n".join(f"{k}: {v}" for k, v in sorted(s.tags.items()))
        ) + "</pre>"
        rows.append(
            f'<tr class="{cls}">'
            f'<td>{html.escape(s.filename)}</td>'
            f'<td>{html.escape(s.filetype)}</td>'
            f'<td>{pill}</td>'
            f'<td>{html.escape("; ".join(s.author_values))}</td>'
            f'<td>{html.escape(s.title)}</td>'
            f'<td>{html.escape(s.creation_date)}</td>'
            f'<td>{html.escape("; ".join(s.software))}</td>'
            f'<td>{html.escape("; ".join(s.warnings))}</td>'
            f'<td><details><summary>ver</summary>{tags_html}</details></td>'
            f'</tr>'
        )
    doc = _HTML_TEMPLATE.format(
        generated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        n=len(summaries),
        rows="\n".join(rows),
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
