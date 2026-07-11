"""
gui.notification_toast
========================

A brief, non-blocking pop-up shown when a new notification arrives
while the app is open. Implemented as a child widget of MainWindow
(positioned in its top-right corner) rather than a separate top-level
window, since a child widget avoids cross-platform window-manager
positioning quirks — it just needs to sit above its parent's other
widgets and auto-close after a few seconds.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.notification_manager import Notification

_LEVEL_COLORS = {
    "info": "#4fd1c5",
    "warning": "#e0af68",
    "critical": "#e06666",
}


class NotificationToast(QFrame):
    def __init__(self, parent, notification: Notification, duration_ms: int = 5000) -> None:
        super().__init__(parent)
        color = _LEVEL_COLORS.get(notification.level, _LEVEL_COLORS["info"])
        self.setStyleSheet(
            f"QFrame {{ background-color: #161b22; border-left: 4px solid {color}; "
            f"border-radius: 6px; }} QLabel {{ background: transparent; }}"
        )
        self.setFixedWidth(300)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 10, 8, 10)

        text_layout = QVBoxLayout()
        title_label = QLabel(notification.title)
        title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        title_label.setWordWrap(True)

        message_label = QLabel(notification.message)
        message_label.setStyleSheet("font-size: 12px; color: #a7b4c0;")
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
