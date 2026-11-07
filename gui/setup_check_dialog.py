"""
gui.setup_check_dialog
========================

Settings → Check My Setup (core/system_check.py): what works on this
device, what's missing, and the exact step for each.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from core.system_check import MISSING, OK, run_checks

_MARK = {OK: "✅", MISSING: "❌"}


class SetupCheckDialog(QDialog):
    """Check my setup: every check of this computer (model, voice, phone access...) with what's wrong and what to do, and Check again."""
    def __init__(self, context, parent=None, checks=None) -> None:
        """The list of checks (run now unless given) and Check again."""
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Check my setup")
        self.setMinimumSize(520, 460)
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        self.rows = QVBoxLayout(holder)
        self.rows.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(holder)
        layout.addWidget(scroll, stretch=1)
        rerun = QPushButton("Check again")
        rerun.clicked.connect(lambda: self._show(None))
        layout.addWidget(rerun)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._show(checks)

    def _show(self, checks) -> None:
        """Runs the checks (a wait cursor while they run) and lists each with its mark, detail and fix (old rows removed first)."""
        while self.rows.count():
            widget = self.rows.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            checks = checks if checks is not None else run_checks(self.context)
        finally:
            QGuiApplication.restoreOverrideCursor()
        self.checks = checks
        for check in checks:
            text = f"{_MARK.get(check.status, '➕')}  <b>{check.name}</b>: {check.detail}"
            if check.fix:
                text += f"<br><span style='color:#9fb3c8'>To do: {check.fix}</span>"
            label = QLabel(text)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.rows.addWidget(label)
