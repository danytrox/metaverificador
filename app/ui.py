"""Interfaz gráfica (PySide6). Arrastrar y soltar, tabla de resultados,
detalle de metadatos y exportación CSV/JSON/HTML/Excel. Todo local.

Los colores de resaltado se adaptan al tema (claro/oscuro) del sistema para
que el texto siempre sea legible.
"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .analyzer import summarize
from .extractor import ExifToolBackend, get_backend
from .report import export_csv, export_html, export_json, export_xlsx

_COLUMNS = ["Archivo", "Tipo", "Autor", "Autor (valores)", "Título", "Fecha", "Software"]


class Worker(QThread):
    progress = Signal(int, int)
    file_done = Signal(object)
    finished_all = Signal()

    def __init__(self, paths, backend):
        super().__init__()
        self.paths = list(paths)
        self.backend = backend
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        def _cb(done, total):
            if self._cancel:
                return
            self.progress.emit(done, total)

        try:
            results = self.backend.extract_many(self.paths, progress_cb=_cb)
            for r in results:
                if self._cancel:
                    break
                self.file_done.emit(summarize(r))
        finally:
            self.finished_all.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MetaVerificador — Análisis local de metadatos")
        self.resize(1100, 700)
        self.setAcceptDrops(True)

        self.backend = get_backend()
        self._summaries = {}  # path -> Summary
        self._worker = None

        self._build_ui()
        self._refresh_engine_label()

    # ---------- Tema ----------
    def _is_dark(self) -> bool:
        return self.palette().color(QPalette.Window).lightness() < 128

    def _row_colors(self) -> dict:
        """Colores de resaltado según el tema (claro u oscuro)."""
        if self._is_dark():
            return {
                "no_bg": "#4a2530",   # rojo oscuro (fondo fila sin autor)
                "no_fg": "#f5c6cb",   # rosa claro (texto legible sobre el fondo)
                "yes": "#7ee2a8",     # verde claro
                "no": "#ff8a8a",      # rojo claro
            }
        return {
            "no_bg": "#fdecea",       # rosa claro (fondo fila sin autor)
            "no_fg": None,            # texto por defecto (oscuro) es legible
            "yes": "#1e7b34",         # verde oscuro
            "no": "#c00000",          # rojo oscuro
        }

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Barra superior de acciones
        bar = QHBoxLayout()
        self.btn_add_files = QPushButton("Agregar archivos")
        self.btn_add_folder = QPushButton("Agregar carpeta")
        self.btn_remove = QPushButton("Quitar seleccionados")
        self.btn_clear = QPushButton("Limpiar")
        self.btn_add_files.setToolTip("Selecciona uno o más archivos para analizar")
        self.btn_add_folder.setToolTip("Analiza todos los archivos de una carpeta (recursivo)")
        self.btn_remove.setToolTip("Quita de la lista los archivos seleccionados")
        self.btn_clear.setToolTip("Vacía la lista y los resultados")

        # Botón único de exportación con menú desplegable
        self.btn_export = QToolButton()
        self.btn_export.setText("Exportar")
        self.btn_export.setToolTip("Guarda los resultados en el formato que elijas")
        self.btn_export.setPopupMode(QToolButton.InstantPopup)
        self.btn_export.setEnabled(False)
        export_menu = QMenu(self.btn_export)
        a = export_menu.addAction("Excel (.xlsx) — resumen + todos los metadatos")
        a.triggered.connect(lambda: self._export("xlsx"))
        a = export_menu.addAction("CSV (.csv) — tabla simple")
        a.triggered.connect(lambda: self._export("csv"))
        a = export_menu.addAction("JSON (.json) — datos completos")
        a.triggered.connect(lambda: self._export("json"))
        a = export_menu.addAction("HTML (.html) — informe para navegador")
        a.triggered.connect(lambda: self._export("html"))
        self.btn_export.setMenu(export_menu)

        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_add_folder.clicked.connect(self._add_folder)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear.clicked.connect(self._clear)

        for b in (self.btn_add_files, self.btn_add_folder, self.btn_remove, self.btn_clear):
            bar.addWidget(b)
        bar.addStretch(1)
        self.engine_label = QLabel("")
        bar.addWidget(self.engine_label)
        bar.addSpacing(16)
        bar.addWidget(self.btn_export)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)

        # Lista de archivos (izquierda)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.itemSelectionChanged.connect(self._on_selection)
        splitter.addWidget(self.file_list)

        # Panel derecho: tabla + detalle
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(_COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_row_select)
        rl.addWidget(self.table, 3)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText(
            "Detalle de metadatos del archivo seleccionado (todos los campos)."
        )
        rl.addWidget(self.detail, 2)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 820])
        root.addWidget(splitter, 1)

        # Barra inferior
        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.status = QLabel("Arrastra archivos o carpetas aquí, o usa los botones.")
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.progress, 0)
        root.addLayout(bottom)

    def _refresh_engine_label(self):
        dark = self._is_dark()
        if isinstance(self.backend, ExifToolBackend) and self.backend.available:
            self.engine_label.setText("Motor: ExifTool (local)")
            color = "#7ee2a8" if dark else "#155724"
        else:
            self.engine_label.setText("Motor: Python (respaldo)")
            color = "#f0c674" if dark else "#856404"
            self.status.setText(
                "ExifTool no encontrado; usando backend de respaldo (menos completo)."
            )
        self.engine_label.setStyleSheet(f"color:{color};font-weight:bold;")

    # ---------- Archivos ----------
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar archivos")
        self._queue(files)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if not folder:
            return
        found = []
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                found.append(os.path.join(dirpath, name))
        self._queue(found)

    def _queue(self, paths):
        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if not os.path.isfile(p) or p in self._summaries:
                continue
            item = QListWidgetItem(os.path.basename(p))
            item.setToolTip(p)
            item.setData(Qt.UserRole, p)
            self.file_list.addItem(item)
            self._summaries[p] = None  # pendiente
            added += 1
        if added:
            self._start_analysis()

    def _remove_selected(self):
        for item in self.file_list.selectedItems():
            self._summaries.pop(item.data(Qt.UserRole), None)
            self.file_list.takeItem(self.file_list.row(item))
        self._rebuild_table()

    def _clear(self):
        self.file_list.clear()
        self._summaries.clear()
        self.detail.clear()
        self.table.setRowCount(0)
        self._update_status()

    # ---------- Análisis ----------
    def _start_analysis(self):
        if self._worker and self._worker.isRunning():
            return
        pending = [p for p, s in self._summaries.items() if s is None]
        if not pending:
            return
        self.progress.setVisible(True)
        self.progress.setRange(0, len(pending))
        self.progress.setValue(0)
        self._worker = Worker(pending, self.backend)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.finished_all.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, done, total):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    @Slot(object)
    def _on_file_done(self, summary):
        self._summaries[summary.path] = summary
        self._upsert_table_row(summary)

    @Slot()
    def _on_finished(self):
        self.progress.setVisible(False)
        self._update_status()

    def _update_status(self):
        total = len(self._summaries)
        done = sum(1 for s in self._summaries.values() if s is not None)
        if not total:
            self.status.setText("Arrastra archivos o carpetas aquí, o usa los botones.")
            self.btn_export.setEnabled(False)
            return
        missing = sum(1 for s in self._summaries.values() if s is not None and not s.author_found)
        self.btn_export.setEnabled(done > 0)
        self.status.setText(
            f"{done}/{total} analizados · {missing} sin autor · "
            "los archivos nunca salen de este equipo"
        )

    # ---------- Tabla ----------
    def _upsert_table_row(self, summary):
        # Reemplazar fila existente o agregar
        row = -1
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).data(Qt.UserRole) == summary.path:
                row = i
                break
        if row == -1:
            row = self.table.rowCount()
            self.table.insertRow(row)
        colors = self._row_colors()
        values = [
            summary.filename,
            summary.filetype,
            "SI" if summary.author_found else "NO",
            " | ".join(summary.author_values),
            summary.title,
            summary.creation_date,
            " | ".join(summary.software),
        ]
        for col, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setData(Qt.UserRole, summary.path)
            if not summary.author_found:
                item.setBackground(QColor(colors["no_bg"]))
                if colors["no_fg"]:
                    item.setForeground(QColor(colors["no_fg"]))
            if col == 2:  # columna "Autor"
                f = QFont()
                f.setBold(True)
                item.setFont(f)
                item.setForeground(QColor(colors["yes"] if summary.author_found else colors["no"]))
                item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)

    def _rebuild_table(self):
        self.table.setRowCount(0)
        for summary in self._summaries.values():
            if summary is not None:
                self._upsert_table_row(summary)

    def _on_selection(self):
        items = self.file_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        self._select_path(path)

    def _on_row_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        path = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        self._select_path(path)

    def _select_path(self, path):
        summary = self._summaries.get(path)
        if summary is None:
            self.detail.setPlainText("Aún no analizado.")
            return
        self.detail.setPlainText(self._format_detail(summary))

    @staticmethod
    def _format_detail(summary) -> str:
        lines = [f"Archivo : {summary.filename}", f"Ruta    : {summary.path}",
                 f"Tipo    : {summary.filetype}", f"Autor   : {'SI' if summary.author_found else 'NO'}"]
        if summary.title:
            lines.append(f"Título  : {summary.title}")
        if summary.creation_date:
            lines.append(f"Fecha   : {summary.creation_date}")
        if summary.software:
            lines.append(f"Software: {' | '.join(summary.software)}")
        if summary.warnings:
            lines.append("")
            lines.append("Advertencias:")
            for w in summary.warnings:
                lines.append(f"  - {w}")
        lines.append("")
        lines.append("Todos los campos:")
        for k in sorted(summary.tags):
            lines.append(f"  {k}: {summary.tags[k]}")
        return "\n".join(lines)

    # ---------- Exportación ----------
    def _export(self, fmt):
        done = [s for s in self._summaries.values() if s is not None]
        if not done:
            QMessageBox.information(self, "MetaVerificador", "No hay resultados que exportar.")
            return
        filters = {"csv": "CSV (*.csv)", "json": "JSON (*.json)", "html": "HTML (*.html)", "xlsx": "Excel (*.xlsx)"}
        path, _ = QFileDialog.getSaveFileName(self, "Guardar reporte", f"reporte.{fmt}", filters[fmt])
        if not path:
            return
        try:
            if fmt == "csv":
                export_csv(done, path)
            elif fmt == "json":
                export_json(done, path)
            elif fmt == "xlsx":
                export_xlsx(done, path)
            else:
                export_html(done, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "MetaVerificador", f"Error al exportar: {exc}")
            return
        QMessageBox.information(self, "MetaVerificador", f"Reporte guardado en:\n{path}")

    # ---------- Drag & drop ----------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p:
                if os.path.isdir(p):
                    for dirpath, dirnames, filenames in os.walk(p):
                        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                        for name in filenames:
                            paths.append(os.path.join(dirpath, name))
                else:
                    paths.append(p)
        self._queue(paths)
        event.acceptProposedAction()


def run_gui() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MetaVerificador")
    win = MainWindow()
    win.show()
    return app.exec()
