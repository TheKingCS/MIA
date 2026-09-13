"""
gui.widgets.photo_background_frame
=====================================

PhotoBackgroundFrame — a QFrame that paints a full-bleed background
photo (scaled + center-cropped to cover the frame, the same "cover"
crop CSS's background-size:cover does) with a dark gradient scrim over
it (near-transparent at the top, opaque toward the bottom) so real
content sitting in a child layout on top stays legible regardless of
what the photo looks like underneath. Same "small QPainter-based
visual atom, reused across screens" shape as
gui/widgets/blueprint_frame.py.

Introduced 2026-09-14 for the "Nature" re-skin pilot (Garage first, per
the user's own reference mockup) — every other module still uses the
teal HUD system (BlueprintFrame/#DashboardCard/#MonitorTile); nothing
here touches those, and this class doesn't replace BlueprintFrame,
it's a new sibling for a different visual direction.

When no `pixmap_path` is given — true for every module so far, since
the reference mockup's own asset photography was too low-resolution
to extract and ship (see modules/garage/module.py's own docstring) —
a vertical dark-green-to-black gradient placeholder is painted
instead, so the layout/scrim composition can be judged before real
photography exists. Swap in a real path later with no other code
changes needed.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QWidget

_SCRIM_TOP = QColor(7, 15, 13, 40)
_SCRIM_BOTTOM = QColor(7, 15, 13, 235)
_PLACEHOLDER_TOP = QColor(20, 46, 36)
_PLACEHOLDER_BOTTOM = QColor(7, 15, 13)


class PhotoBackgroundFrame(QFrame):
    def __init__(self, parent: Optional[QWidget] = None, pixmap_path: Optional[str] = None) -> None:
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = QPixmap(pixmap_path) if pixmap_path else None
        if self._pixmap is not None and self._pixmap.isNull():
            self._pixmap = None

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        if self._pixmap is not None:
            scaled = self._pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - rect.width()) // 2
            y = (scaled.height() - rect.height()) // 2
            painter.drawPixmap(rect, scaled, QRectF(x, y, rect.width(), rect.height()))
        else:
            placeholder = QLinearGradient(0, 0, 0, rect.height())
            placeholder.setColorAt(0.0, _PLACEHOLDER_TOP)
            placeholder.setColorAt(1.0, _PLACEHOLDER_BOTTOM)
            painter.fillRect(rect, placeholder)

        scrim = QLinearGradient(0, 0, 0, rect.height())
        scrim.setColorAt(0.0, _SCRIM_TOP)
        scrim.setColorAt(1.0, _SCRIM_BOTTOM)
        painter.fillRect(rect, scrim)
        painter.end()
