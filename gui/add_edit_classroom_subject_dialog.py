"""
gui.add_edit_classroom_subject_dialog
=========================================

Small dialog for creating or editing a Subject (modules/classroom/module.py) —
name, an optional freeform category (e.g. "Mathematics", "Trade Skills",
not a fixed vocabulary — every subject the user studies is theirs to
name and categorize), and a description. Same minimal shape as
gui/add_edit_project_dialog.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QTextEdit, QVBoxLayout

from core.classroom_manager import Subject


class AddEditSubjectDialog(QDialog):
    def __init__(self, context, parent=None, subject: Optional[Subject] = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Edit Subject" if subject is not None else "New Subject")
        self.setFixedSize(360, 360)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 'Geometry' or 'Electrical'")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category (optional):"))
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("e.g. 'Mathematics', 'Trade Skills'")
        layout.addWidget(self.category_edit)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Description (optional)")
        layout.addWidget(self.description_edit, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(subject)

        self._name: str = ""
        self._category: str = ""
        self._description: str = ""

    def _prefill(self, subject: Optional[Subject]) -> None:
        if subject is None:
            return
        self.name_edit.setText(subject.name)
        self.category_edit.setText(subject.category)
        self.description_edit.setPlainText(subject.description)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._category = self.category_edit.text().strip()
        self._description = self.description_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_description(self) -> str:
        return self._description
