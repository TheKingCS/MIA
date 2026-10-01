"""
gui.quick_capture_dialog
==========================

The quick capture box (core/quick_capture.py): type anything, press
Enter, MIA files it. It stays open for the next one; each result has
Undo. The Assistant runs off the screen's thread, so typing never
freezes.
"""

from __future__ import annotations

import threading

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from core.person_settings import person_id
from core.quick_capture import capture
from core.undo_log import undo_last

EXAMPLES = "e.g. \"milk and eggs\", \"oil change on the truck today\", \"dentist Tuesday at 2\""


class QuickCaptureDialog(QDialog):
    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Quick capture")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("What's on your mind? MIA files it where it belongs."))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(EXAMPLES)
        self.edit.returnPressed.connect(self._on_submit)
        layout.addWidget(self.edit)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        row = QHBoxLayout()
        self.undo_button = QPushButton("Undo")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self._on_undo)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(self.undo_button)
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
        self._busy = False

    def _on_submit(self) -> None:
        text = self.edit.text().strip()
        if not text or self._busy:
            return
        self._busy = True
        self.edit.setEnabled(False)
        self.undo_button.setEnabled(False)
        self.result_label.setText("Filing…")
        call = getattr(self.context, "main_thread_call", None) or (lambda fn: fn())

        def work() -> None:
            result = capture(self.context, text)
            call(lambda: self._show(result))

        threading.Thread(target=work, daemon=True, name="mia-quick-capture").start()

    def _show(self, result) -> None:
        self._busy = False
        self.edit.setEnabled(True)
        self.edit.clear()
        self.edit.setFocus()
        self.result_label.setText(result.reply)
        self.undo_button.setEnabled(result.filed)

    def _on_undo(self) -> None:
        change = undo_last(self.context, person_id(self.context))
        self.undo_button.setEnabled(False)
        self.result_label.setText("Undone." if change is not None else "Nothing to undo.")
