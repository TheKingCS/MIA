"""
gui.widgets.skill_tree_canvas
================================

SkillTreeCanvas — a QWidget subclass that draws prerequisite connector
lines behind its own child widgets (design restyle Phase 4, 2026-09-12,
the "My Hero's Path" skill tree screen). Same "small QPainter-based
visual atom, reused across screens" shape as
gui/widgets/blueprint_frame.py/circular_gauge.py.

Drawing "behind the nodes" needs no manual raise()/overlay trick: Qt's
own paint order always renders a widget's paintEvent first, then its
child widgets on top, so simply *being* the grid container this canvas
already is (modules/skills/module.py sets its layout directly on one
of these) is enough. set_connections() stores live widget references,
not snapshotted coordinates, so a line stays correct across any
re-layout — paintEvent reads each widget's current .geometry() itself.

Deliberate simplification (see the Phase 4 plan/ROADMAP entry): every
connector draws as a straight line, even where the design's own mockup
shows a curved line for two prerequisites converging on one node
(irrigation). Real curve-fitting for one specific case wasn't worth it.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

_LINE_COLOR = QColor("#1f3538")
_LINE_WIDTH = 1.5


class SkillTreeCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._connections: list[tuple[QWidget, QWidget]] = []

    def set_connections(self, pairs: list[tuple[QWidget, QWidget]]) -> None:
        """`pairs` is (prerequisite_widget, dependent_widget) — call
        again after every grid rebuild (the previous widgets are gone
        by then anyway)."""
        self._connections = list(pairs)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(_LINE_COLOR)
        pen.setWidthF(_LINE_WIDTH)
        painter.setPen(pen)

        for prereq_widget, dependent_widget in self._connections:
            if prereq_widget.isHidden() or dependent_widget.isHidden():
                continue
            start = prereq_widget.geometry().center()
            start.setY(prereq_widget.geometry().bottom())
            end = dependent_widget.geometry().center()
            end.setY(dependent_widget.geometry().top())
            painter.drawLine(start, end)
        painter.end()
