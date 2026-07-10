"""
gui.widgets.placeholder_widget
================================

A generic "coming soon" screen used by v0.1 stub modules.

Centralizing this means every placeholder module looks consistent, and
when a module gets real functionality, it simply stops calling this and
builds its own widget in get_widget() instead — no other file changes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def build_placeholder_widget(title: str, description: str, icon: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(12)

    icon_label = QLabel(icon)
    icon_label.setStyleSheet("font-size: 56px;")
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    title_label = QLabel(title)
    title_label.setObjectName("TitleLabel")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    status_label = QLabel("Coming soon")
    status_label.setObjectName("SubtitleLabel")
    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    desc_label = QLabel(description)
    desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_label.setWordWrap(True)

    layout.addWidget(icon_label)
    layout.addWidget(title_label)
    layout.addWidget(status_label)
    layout.addWidget(desc_label)
    return widget
