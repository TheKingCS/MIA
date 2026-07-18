"""
gui.trail_map_viewer_dialog
==============================

A simple embedded PDF viewer dialog for one core.trail_map_library.TrailMap
— uses QtPdf/QtPdfWidgets (confirmed importable in this dev sandbox,
unlike QtWebEngineWidgets, see gui/widgets/tile_map_view.py's docstring
for that finding), so trail map PDFs open right inside the app rather
than needing an external viewer.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from core.trail_map_library import TrailMap


class TrailMapViewerDialog(QDialog):
    def __init__(self, trail_map: TrailMap, file_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{trail_map.park_name} — Trail Map")
        self.resize(720, 860)

        layout = QVBoxLayout(self)

        header = QLabel(f"{trail_map.park_name} ({trail_map.state})")
        header.setObjectName("SubtitleLabel")
        layout.addWidget(header)

        # Kept alive as an attribute — QPdfView doesn't take ownership
        # in a way that keeps a locally-scoped QPdfDocument alive.
        self._document = QPdfDocument(self)
        self._document.load(str(file_path))

        view = QPdfView(self)
        view.setDocument(self._document)
        view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        layout.addWidget(view, stretch=1)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
