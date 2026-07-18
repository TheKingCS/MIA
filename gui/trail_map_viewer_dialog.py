"""
gui.trail_map_viewer_dialog
==============================

A simple embedded PDF viewer dialog for one core.trail_map_library.TrailMap
— uses QtPdf/QtPdfWidgets (confirmed importable in this dev sandbox,
unlike QtWebEngineWidgets, see gui/widgets/tile_map_view.py's docstring
for that finding), so trail map PDFs open right inside the app rather
than needing an external viewer.

**2026-07-18: `QPdfView` defaults to `PageMode.SinglePage`** (confirmed
directly, not assumed) — with no page-turning control anywhere in this
dialog, that silently showed only page 1 and nothing past it. Real bug
this caused, found via the user's own report ("the trail maps you
added for LBL are not maps at all"): every one of the seeded LBL/state
park PDFs is a multi-page trifold brochure whose actual cartographic
map sits on page 2, with page 1 being just a cover/title/text page —
so every one of them *looked* like it had no map at all, even though
6 of the 7 seeded entries (confirmed by rendering each page directly
and inspecting it) are genuine, detailed trail maps. Fixed by switching
to `PageMode.MultiPage` (continuous scroll through every page, same as
any normal PDF viewer) plus a page-count label, so the real map page
is actually reachable instead of hidden.
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

        page_count = self._document.pageCount()
        if page_count > 1:
            page_count_label = QLabel(f"{page_count} pages — scroll to see all of them")
            page_count_label.setObjectName("DashboardSectionBody")
            layout.addWidget(page_count_label)

        view = QPdfView(self)
        view.setDocument(self._document)
        view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        # MultiPage (continuous scroll) — the default SinglePage mode
        # with no page-turn control silently hid every page past the
        # first, which for a multi-page trifold brochure is exactly
        # where the real map usually is. See this file's 2026-07-18
        # docstring note.
        view.setPageMode(QPdfView.PageMode.MultiPage)
        layout.addWidget(view, stretch=1)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
