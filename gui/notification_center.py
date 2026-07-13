"""
gui.notification_center
=========================

The full notification list, opened from the bell button in the main
window header. Shows every notification (read and unread), newest
first, color-coded by level, with per-item dismiss and a "Clear All"
action.

Opening this dialog marks everything as read (matching how most
phone/desktop notification centers behave — "seen" as soon as you look
at the list) but does NOT delete anything; entries stay visible until
individually dismissed or cleared, so nothing disappears without the
user choosing to remove it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext

_LEVEL_COLORS = {
    "info": "#4fd1c5",
    "warning": "#e0af68",
    "critical": "#e06666",
}


class NotificationCenterDialog(QDialog):
    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Notifications")
        self.resize(420, 480)

        self._build_ui()
        # Seeing the list counts as "reading" it — clears the unread
        # badge, but nothing is deleted until the user dismisses it.
        self.context.notifications.mark_all_read()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Notifications")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(8)
        self._populate()

        scroll.setWidget(self._list_container)
        layout.addWidget(scroll)

        clear_all_button = QPushButton("Clear All")
        clear_all_button.setObjectName("ModuleButton")
        clear_all_button.clicked.connect(self._on_clear_all)
        layout.addWidget(clear_all_button)

    def _populate(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        notifications = self.context.notifications.list_all()
        if not notifications:
            empty_label = QLabel("No notifications.")
            empty_label.setObjectName("SubtitleLabel")
            self._list_layout.addWidget(empty_label)
            return

        for notification in notifications:
            self._list_layout.addWidget(self._build_row(notification))

    def _build_row(self, notification) -> QFrame:
        color = _LEVEL_COLORS.get(notification.level, _LEVEL_COLORS["info"])
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background-color: #161b22; border-left: 4px solid {color}; border-radius: 6px; }}"
        )

        outer = QHBoxLayout(row)
        text_layout = QVBoxLayout()

        title_label = QLabel(notification.title)
        title_label.setStyleSheet("font-weight: 600;")
        title_label.setWordWrap(True)

        message_label = QLabel(notification.message)
        message_label.setObjectName("SubtitleLabel")
        message_label.setWordWrap(True)

        meta_label = QLabel(f"{notification.source} \u2022 {notification.created_at}")
        meta_label.setStyleSheet("color: #5a6773; font-size: 11px;")

        text_layout.addWidget(title_label)
        text_layout.addWidget(message_label)
        text_layout.addWidget(meta_label)
        outer.addLayout(text_layout, stretch=1)

        dismiss_button = QPushButton("\u00D7")
        dismiss_button.setFixedSize(28, 28)
        dismiss_button.clicked.connect(lambda checked=False, nid=notification.notification_id: self._on_dismiss(nid))
        outer.addWidget(dismiss_button)

        return row

    def _on_dismiss(self, notification_id: str) -> None:
        self.context.notifications.dismiss(notification_id)
        self._populate()

    def _on_clear_all(self) -> None:
        self.context.notifications.clear_all()
        self._populate()
