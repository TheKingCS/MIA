"""
gui.file_preview_dialog
==========================

A read-only preview dialog for the Files module (modules/files_mod/
module.py) — text content in a monospace view, or an image scaled to
fit, depending on which classmethod constructs it. Kept as one dialog
class with two display modes rather than two separate classes since
the surrounding chrome (title, sizing, close button) is identical
either way.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QVBoxLayout

from gui.styles import DARK_FIELD_THEME


class FilePreviewDialog(QDialog):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(DARK_FIELD_THEME)
        self.resize(600, 500)
        self._layout = QVBoxLayout(self)

    @classmethod
    def for_text(cls, title: str, text: str, parent=None) -> "FilePreviewDialog":
        dialog = cls(title, parent)
        view = QPlainTextEdit()
        view.setObjectName("LogView")
        view.setReadOnly(True)
        view.setPlainText(text)
        dialog._layout.addWidget(view)
        return dialog

    @classmethod
    def for_image(cls, title: str, pixmap: QPixmap, parent=None) -> "FilePreviewDialog":
        dialog = cls(title, parent)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scaled = pixmap.scaled(
            560, 460, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(scaled)
        dialog._layout.addWidget(label)
        return dialog
