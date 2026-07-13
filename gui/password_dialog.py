"""
gui.password_dialog
=====================

A small reusable dialog for prompting a profile's password — used both
when selecting a password-protected profile and when deleting one.

Kept as a single reusable component (rather than duplicating a password
field inline in profile_select.py) so the look and behavior of "enter
this profile's password" stays consistent everywhere it's needed,
including the eventual Settings module's "change password" flow.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)



class PasswordPromptDialog(QDialog):
    def __init__(self, profile_name: str, prompt: str = "Enter password for", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.setFixedSize(340, 150)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{prompt} {profile_name}:"))

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Password")
        layout.addWidget(self.password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def entered_password(self) -> str:
        return self.password_edit.text()


def prompt_for_password(profile, parent=None, prompt: str = "Enter password for") -> tuple[bool, str]:
    """
    Show a password dialog for `profile`. Returns (cancelled, password) —
    where cancelled is True if the user hit Cancel/closed the dialog.
    Does not verify the password itself; callers check it against
    ProfileManager.verify_password.
    """
    dialog = PasswordPromptDialog(profile.name, prompt=prompt, parent=parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return True, ""
    return False, dialog.entered_password
