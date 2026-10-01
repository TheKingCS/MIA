"""
gui.add_edit_person_dialog
=============================

Small dialog for creating or editing a single Relationship Profile
(a person MIA knows), used by modules/relationships/module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.relationships_manager import Person

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditPersonDialog(QDialog):
    def __init__(self, parent=None, person: Optional[Person] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Person" if person is not None else "New Person")
        self.setFixedSize(360, 560)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Jamie")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Relationship:"))
        self.relationship_edit = QLineEdit()
        self.relationship_edit.setPlaceholderText("e.g. Sister, Best friend, Coworker (optional)")
        layout.addWidget(self.relationship_edit)

        layout.addWidget(QLabel("Email:"))
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("So MIA can address emails to them (optional)")
        layout.addWidget(self.email_edit)

        self.birthday_checkbox = QCheckBox("Track birthday")
        self.birthday_checkbox.toggled.connect(self._on_birthday_toggle)
        layout.addWidget(self.birthday_checkbox)

        self.birthday_edit = QDateEdit()
        self.birthday_edit.setCalendarPopup(True)
        self.birthday_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.birthday_edit.setDate(QDate.currentDate())
        self.birthday_edit.setEnabled(False)
        layout.addWidget(self.birthday_edit)

        layout.addWidget(QLabel("Favorite Things:"))
        self.favorite_things_edit = QTextEdit()
        self.favorite_things_edit.setPlaceholderText("Notes on what they love (optional)")
        self.favorite_things_edit.setFixedHeight(70)
        layout.addWidget(self.favorite_things_edit)

        layout.addWidget(QLabel("Gift Ideas:"))
        self.gift_ideas_edit = QTextEdit()
        self.gift_ideas_edit.setPlaceholderText("Running list of gift ideas (optional)")
        self.gift_ideas_edit.setFixedHeight(70)
        layout.addWidget(self.gift_ideas_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Shared memories, anything else (optional)")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(person)

        self._name: str = ""
        self._relationship: str = ""
        self._birthday: str = ""
        self._favorite_things: str = ""
        self._gift_ideas: str = ""
        self._notes: str = ""
        self._email: str = ""

    def _on_birthday_toggle(self, checked: bool) -> None:
        self.birthday_edit.setEnabled(checked)

    def _prefill(self, person: Optional[Person]) -> None:
        if person is None:
            return
        self.name_edit.setText(person.name)
        self.relationship_edit.setText(person.relationship)
        self.email_edit.setText(person.email)
        if person.birthday:
            self.birthday_checkbox.setChecked(True)
            self.birthday_edit.setDate(QDate.fromString(person.birthday, _ISO_DATE_FORMAT))
        self.favorite_things_edit.setPlainText(person.favorite_things)
        self.gift_ideas_edit.setPlainText(person.gift_ideas)
        self.notes_edit.setPlainText(person.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._relationship = self.relationship_edit.text().strip()
        self._birthday = (
            self.birthday_edit.date().toString(_ISO_DATE_FORMAT) if self.birthday_checkbox.isChecked() else ""
        )
        self._favorite_things = self.favorite_things_edit.toPlainText().strip()
        self._gift_ideas = self.gift_ideas_edit.toPlainText().strip()
        self._notes = self.notes_edit.toPlainText().strip()
        self._email = self.email_edit.text().strip().lower()
        self.accept()

    @property
    def entered_email(self) -> str:
        return self._email

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_relationship(self) -> str:
        return self._relationship

    @property
    def entered_birthday(self) -> str:
        return self._birthday

    @property
    def entered_favorite_things(self) -> str:
        return self._favorite_things

    @property
    def entered_gift_ideas(self) -> str:
        return self._gift_ideas

    @property
    def entered_notes(self) -> str:
        return self._notes
