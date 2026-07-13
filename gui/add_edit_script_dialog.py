"""
gui.add_edit_script_dialog
=============================

Small dialog for creating or editing a single Field Kit script, used by
modules/field_kit/module.py. Same shape as
gui/add_edit_journal_entry_dialog.py (QDialog + the shared app-level theme +
QDialogButtonBox, validate-then-expose-via-properties on accept) —
name/category/interpreter/content instead of title/tags/body.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.script_library_manager import INTERPRETERS, Script


class AddEditScriptDialog(QDialog):
    def __init__(self, parent=None, script: Optional[Script] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Script" if script is not None else "New Script")
        self.setFixedSize(480, 520)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category:"))
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("e.g. Network, Automation (optional)")
        layout.addWidget(self.category_edit)

        layout.addWidget(QLabel("Interpreter:"))
        self.interpreter_combo = QComboBox()
        self.interpreter_combo.addItems(INTERPRETERS)
        layout.addWidget(self.interpreter_combo)

        layout.addWidget(QLabel("Script:"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Write your script here...")
        self.content_edit.setFontFamily("monospace")
        layout.addWidget(self.content_edit, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(script)

        self._name: str = ""
        self._category: str = ""
        self._interpreter: str = "shell"
        self._content: str = ""

    def _prefill(self, script: Optional[Script]) -> None:
        if script is not None:
            self.name_edit.setText(script.name)
            self.category_edit.setText(script.category)
            index = self.interpreter_combo.findText(script.interpreter)
            if index >= 0:
                self.interpreter_combo.setCurrentIndex(index)
            self.content_edit.setPlainText(script.content)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._category = self.category_edit.text().strip()
        self._interpreter = self.interpreter_combo.currentText()
        self._content = self.content_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_interpreter(self) -> str:
        return self._interpreter

    @property
    def entered_content(self) -> str:
        return self._content
