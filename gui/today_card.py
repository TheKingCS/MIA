"""
gui.today_card
================

The "Today" card at the top of Home (core/today.py, 2026-10-01): what
needs you today across every app, overdue first. Each row opens the app
it belongs to. Rebuilt only when the list actually changes, so the
dashboard's regular refresh doesn't make it flicker.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from core.today import OVERDUE, SOON, TODAY, WAITING, today_items

_GROUPS = {OVERDUE: "OVERDUE", TODAY: "TODAY", WAITING: "WAITING ON YOU", SOON: "COMING UP"}
MAX_ROWS = 10


class TodayCard(QFrame):
    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setObjectName("DashboardCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 14, 20, 14)
        self._layout.setSpacing(4)
        self._shown: list = []
        self.refresh()

    def refresh(self) -> None:
        items = today_items(self.context)
        signature = [i.as_dict() for i in items]
        if signature == self._shown:
            return
        self._shown = signature
        while self._layout.count():
            widget = self._layout.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        title = QLabel("TODAY")
        title.setObjectName("DashboardOverlineLabel")
        self._layout.addWidget(title)
        if not items:
            self._layout.addWidget(QLabel("Nothing needs you today. Enjoy it."))
            return
        group = None
        for item in items[:MAX_ROWS]:
            # A heading for each group; today's own needs none when it comes first.
            if item.when != group and not (group is None and item.when == TODAY):
                heading = QLabel(_GROUPS.get(item.when, item.when))
                heading.setObjectName("SubtitleLabel")
                self._layout.addWidget(heading)
            group = item.when
            lead = item.time or item.icon
            text = f"{lead}   {item.title}" + (f"  ·  {item.detail}" if item.detail else "")
            row = QPushButton(text)
            row.setFlat(True)
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.setStyleSheet("text-align: left; padding: 4px 2px;"
                              + (" color: #e06666;" if item.when == OVERDUE else ""))
            if item.module_id:
                row.clicked.connect(lambda checked=False, i=item: self._open(i))
            self._layout.addWidget(row)
        if len(items) > MAX_ROWS:
            more = QLabel(f"and {len(items) - MAX_ROWS} more. Ask MIA \"what's on today?\"")
            more.setObjectName("SubtitleLabel")
            self._layout.addWidget(more)

    def _open(self, item) -> None:
        self.context.events.publish("assistant.open_module_requested", module_id=item.module_id,
                                    record_id=item.record_id)
