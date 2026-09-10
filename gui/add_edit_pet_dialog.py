"""
gui.add_edit_pet_dialog
==========================

Small dialog for creating or editing a single Pet Profile, used by
modules/relationships/module.py. No photo field yet — see
core/relationships_manager.py's own module docstring for why.
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

from core.relationships_manager import Pet

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditPetDialog(QDialog):
    def __init__(self, parent=None, pet: Optional[Pet] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Pet" if pet is not None else "New Pet")
        self.setFixedSize(360, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Rex")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Species:"))
        self.species_edit = QLineEdit()
        self.species_edit.setPlaceholderText("e.g. Dog, Cat, Bird (optional)")
        layout.addWidget(self.species_edit)

        self.birthday_checkbox = QCheckBox("Track birthday / adoption date")
        self.birthday_checkbox.toggled.connect(self._on_birthday_toggle)
        layout.addWidget(self.birthday_checkbox)

        self.birthday_edit = QDateEdit()
        self.birthday_edit.setCalendarPopup(True)
        self.birthday_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.birthday_edit.setDate(QDate.currentDate())
        self.birthday_edit.setEnabled(False)
        layout.addWidget(self.birthday_edit)

        layout.addWidget(QLabel("Medical Notes:"))
        self.medical_notes_edit = QTextEdit()
        self.medical_notes_edit.setPlaceholderText("Medical history, vet visits (optional)")
        self.medical_notes_edit.setFixedHeight(90)
        layout.addWidget(self.medical_notes_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Anything else (optional)")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(pet)

        self._name: str = ""
        self._species: str = ""
        self._birthday: str = ""
        self._medical_notes: str = ""
        self._notes: str = ""

    def _on_birthday_toggle(self, checked: bool) -> None:
        self.birthday_edit.setEnabled(checked)

    def _prefill(self, pet: Optional[Pet]) -> None:
        if pet is None:
            return
        self.name_edit.setText(pet.name)
        self.species_edit.setText(pet.species)
        if pet.birthday:
            self.birthday_checkbox.setChecked(True)
            self.birthday_edit.setDate(QDate.fromString(pet.birthday, _ISO_DATE_FORMAT))
        self.medical_notes_edit.setPlainText(pet.medical_notes)
        self.notes_edit.setPlainText(pet.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._species = self.species_edit.text().strip()
        self._birthday = (
            self.birthday_edit.date().toString(_ISO_DATE_FORMAT) if self.birthday_checkbox.isChecked() else ""
        )
        self._medical_notes = self.medical_notes_edit.toPlainText().strip()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_species(self) -> str:
        return self._species

    @property
    def entered_birthday(self) -> str:
        return self._birthday

    @property
    def entered_medical_notes(self) -> str:
        return self._medical_notes

    @property
    def entered_notes(self) -> str:
        return self._notes
