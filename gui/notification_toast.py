"""
gui.notification_toast
========================

A brief, non-blocking pop-up shown when a new notification arrives
while the app is open. Implemented as a child widget of MainWindow
(positioned in its top-right corner) rather than a separate top-level
window, since a child widget avoids cross-platform window-manager
positioning quirks — it just needs to sit above its parent's other
widgets and auto-close after a few seconds.

**2026-07-15 fix**: this widget (and `gui/notification_center.py`'s row
widget) predate the 4-theme system (milestone 13.2) and were never
migrated — they called their own `setStyleSheet()` with a hardcoded
dark-theme-only background (`#161b22`), so a toast/notification card
looked identical (and wrong) regardless of the selected theme. Fixed
the same way every other themed card in this app works: an object name
(`#NotificationCard`, reusing `#DashboardCard`'s per-theme background)
plus a `level` dynamic property so `gui/styles.py`/`gui/theme_manager.py`
can style the level-accent border per theme
(`QFrame#NotificationCard[level="..."]`) — no inline `setStyleSheet()`
left on this widget at all now, same pattern as the header bell's
`hasUnread` property.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.notification_manager import Notification


class NotificationToast(QFrame):
    def __init__(self, parent, notification: Notification, duration_ms: int = 5000) -> None:
        super().__init__(parent)
        self.setObjectName("NotificationCard")
        self.setProperty("level", notification.level)
        self.setFixedWidth(300)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 10, 8, 10)

        text_layout = QVBoxLayout()
        title_label = QLabel(notification.title)
        title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        title_label.setWordWrap(True)

        message_label = QLabel(notification.message)
        message_label.setObjectName("SubtitleLabel")
        message_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(message_label)
        outer.addLayout(text_layout, stretch=1)

        close_button = QPushButton("\u00D7")
        close_button.setFixedSize(22, 22)
        close_button.setStyleSheet("font-size: 14px;")
        close_button.clicked.connect(self.close)
        outer.addWidget(close_button)

        self.adjustSize()
        QTimer.singleShot(duration_ms, self.close)

    def show_in_corner(self) -> None:
        """Position this toast in the parent's top-right corner and show it."""
        parent = self.parentWidget()
        if parent is not None:
            self.move(parent.width() - self.width() - 24, 76)
        self.show()
        self.raise_()
