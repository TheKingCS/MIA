"""
gui.add_profile_dialog
========================

A small, focused dialog for creating an additional profile from the
profile-select screen. Deliberately not a full QWizard like first-run
setup — adding a second/third profile only needs a name and an
optional password, so a full multi-page wizard would be more ceremony
than the task warrants.

Accounts (2026-10-01): an email to sign in with (a password is then
needed too), and whether to share household things with an existing
household, approved by one of its members typing their password
(gui/account_dialogs.py's HouseholdChoice). Nothing is shared by default.
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

from core.profile_manager import looks_like_email


class AddProfileDialog(QDialog):
    def __init__(self, parent=None, context=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("New Profile")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Name for the new profile:"))

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Email to sign in with (optional)")
        layout.addWidget(self.email_edit)

        self.password_checkbox = QCheckBox("Protect this profile with a password")
        self.password_checkbox.toggled.connect(self._on_password_toggle)
        layout.addWidget(self.password_checkbox)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEnabled(False)
        layout.addWidget(self.password_edit)

        self.household_choice = None
        if context is not None and getattr(context, "households", None) is not None:
            from gui.account_dialogs import HouseholdChoice

            self.household_choice = HouseholdChoice(context, self)
            layout.addWidget(self.household_choice)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e06666;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._name: str = ""
        self._password: str = ""
        self._email: str = ""

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

        email = self.email_edit.text().strip()
        if email:
            if not looks_like_email(email):
                self.error_label.setText("That doesn't look like an email address.")
                return
            if self.context is not None and self.context.profiles.find_by_email(email) is not None:
                self.error_label.setText("Someone on this MIA already signs in with that email.")
                return
            if not (self.password_checkbox.isChecked() and self.password_edit.text()):
                self.error_label.setText("Signing in with an email needs a password too.")
                self.password_checkbox.setChecked(True)
                return
        if self.household_choice is not None and not self.household_choice.approval_ok():
            self.error_label.setText("That household member's password doesn't match.")
            return

        self._name = name
        self._email = email
        self._password = self.password_edit.text() if self.password_checkbox.isChecked() else ""
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_email(self) -> str:
        return self._email

    @property
    def entered_password(self) -> str:
        """Empty string means "no password requested" — never None, safe to pass straight through."""
        return self._password
