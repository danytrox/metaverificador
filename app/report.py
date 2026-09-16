"""Exportación de resultados a CSV, JSON, HTML y Excel (todo local, sin CDN ni red)."""
from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from typing import Iterable

from .analyzer import Summary


def _summaries_to_list(items: Iterable[Summary]) -> list[Summary]:
    return list(items)


def _as_text(v) -> str:
    """Convierte cualquier valor de metadato a texto legible."""
    if v is None:
        return ""
    if isinstance(v, (list, tuple, set)):
        return " | ".join(_as_text(x) for x in v)
    return str(v)


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
                " | ".join(s.author_values),
                s.title,
                s.creation_date,
                " | ".join(s.software),
                " | ".join(s.warnings),
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


def export_xlsx(summaries: Iterable[Summary], path: str) -> None:
    """Exporta a Excel (.xlsx) con dos hojas: Resumen y Metadatos completos.

    Hoja "Resumen": una fila por archivo con título, encabezado, autofiltro y
    filas congeladas. El autor se marca SÍ (verde) / NO (rojo) y las filas sin
    autor van sombreadas en rojo.
    Hoja "Metadatos": volcado completo campo por campo (Archivo, Grupo, Campo,
    Valor) para inspeccionar todos los metadatos extraídos.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    summaries = _summaries_to_list(summaries)

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, color="FFFFFF", size=14)
    sub_font = Font(italic=True, color="595959", size=10)
    legend_font = Font(italic=True, color="595959", size=9)
    no_fill = PatternFill("solid", fgColor="FDE7E9")
    yes_font = Font(bold=True, color="1E7B34")
    no_font = Font(bold=True, color="C00000")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center")
    top_wrap = Alignment(vertical="top", wrap_text=True)

    wb = Workbook()

    # ---------- Hoja 1: Resumen ----------
    ws = wb.active
    ws.title = "Resumen"
    cols = ["Archivo", "Ruta", "Tipo", "Autor", "Autor (detalle)",
            "Título", "Fecha de creación", "Software", "Advertencias"]
    last_col = get_column_letter(len(cols))

    ws.merge_cells(f"A1:{last_col}1")
    c = ws["A1"]
    c.value = "MetaVerificador — Reporte de metadatos"
    c.font = title_font
    c.fill = header_fill
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 26

    ws.merge_cells(f"A2:{last_col}2")
    c = ws["A2"]
    c.value = (
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}   ·   "
        f"{len(summaries)} archivo(s)   ·   análisis 100% local"
    )
    c.font = sub_font
    ws.row_dimensions[2].height = 16

    ws.merge_cells(f"A3:{last_col}3")
    c = ws["A3"]
    c.value = (
        "Leyenda:  SÍ = registra autor en metadatos  ·  NO = sin autor (fila en rojo)  ·  "
        "\"Autor (detalle)\" indica el campo exacto y el valor encontrado."
    )
    c.font = legend_font

    header_row = 4
    for i, name in enumerate(cols, start=1):
        cell = ws.cell(row=header_row, column=i, value=name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    for r, s in enumerate(summaries, start=header_row + 1):
        vals = [
            s.filename,
            s.path,
            s.filetype,
            "SÍ" if s.author_found else "NO",
            "; ".join(s.author_values),
            s.title,
            s.creation_date,
            "; ".join(s.software),
            "; ".join(s.warnings),
        ]
        for i, val in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=i, value=val)
            cell.border = border
            cell.alignment = top_wrap
            if not s.author_found:
                cell.fill = no_fill
        autor_cell = ws.cell(row=r, column=4)
        autor_cell.font = yes_font if s.author_found else no_font
        autor_cell.alignment = center

    for i, w in enumerate([38, 40, 14, 9, 45, 30, 20, 38, 45], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B5"
    last_row = header_row + len(summaries)
    if summaries:
        ws.auto_filter.ref = f"A{header_row}:{last_col}{last_row}"

    # ---------- Hoja 2: Metadatos completos ----------
    ws2 = wb.create_sheet("Metadatos")
    cols2 = ["Archivo", "Grupo", "Campo", "Valor"]
    for i, name in enumerate(cols2, start=1):
        cell = ws2.cell(row=1, column=i, value=name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    r = 2
    for s in summaries:
        for k in sorted(s.tags):
            grupo, _, campo = k.partition(":")
            vals2 = [s.filename, grupo, campo, _as_text(s.tags[k])]
            for i, val in enumerate(vals2, start=1):
                cell = ws2.cell(row=r, column=i, value=val)
                cell.border = border
                cell.alignment = top_wrap
            r += 1

    for i, w in enumerate([38, 16, 30, 70], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w
    ws2.freeze_panes = "B2"
    if r > 2:
        ws2.auto_filter.ref = f"A1:D{r - 1}"

    wb.save(path)
