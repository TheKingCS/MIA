"""
gui.add_profile_dialog
========================

A small, focused dialog for creating an additional profile from the
profile-select screen. Deliberately not a full QWizard like first-run
setup — adding a second/third profile only needs a name and an
optional password, so a full multi-page wizard would be more ceremony
than the task warrants.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from gui.styles import DARK_FIELD_THEME


class AddProfileDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Profile")
        self.setStyleSheet(DARK_FIELD_THEME)
        self.setFixedSize(340, 220)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Name for the new profile:"))

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        self.password_checkbox = QCheckBox("Protect this profile with a password")
        self.password_checkbox.toggled.connect(self._on_password_toggle)
        layout.addWidget(self.password_checkbox)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEnabled(False)
        layout.addWidget(self.password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._name: str = ""
        self._password: str = ""

    def _on_password_toggle(self, checked: bool) -> None:
        self.password_edit.setEnabled(checked)
        if not checked:
            self.password_edit.clear()

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        if self.password_checkbox.isChecked() and not self.password_edit.text():
            self.password_edit.setPlaceholderText("Password can't be empty!")
            return

        self._name = name
        self._password = self.password_edit.text() if self.password_checkbox.isChecked() else ""
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_password(self) -> str:
        """Empty string means "no password requested" — never None, safe to pass straight through."""
        return self._password
