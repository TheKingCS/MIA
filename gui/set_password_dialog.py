"""
gui.set_password_dialog
==========================

A small, focused dialog for setting/changing/removing the active
profile's password from Settings — same checkbox+field shape as
gui/add_profile_dialog.py's password section, adapted for editing
rather than creation.

Deliberately never sees or checks the profile's CURRENT password —
that verification is the caller's job, done before this dialog is ever
opened (modules/settings/module.py reuses gui/password_dialog.py's
prompt_for_password()/verify_password(), the same two-call pattern
gui/profile_select.py's own profile-switch flow already uses), so a
wrong current password is rejected before the user ever sees a "set a
new one" field.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QVBoxLayout,
)


class SetPasswordDialog(QDialog):
    def __init__(self, has_password: bool, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Change Password")
        self.setFixedSize(340, 150)
        self._has_password = has_password

        layout = QVBoxLayout(self)

        self.password_checkbox = QCheckBox("Protect this profile with a password")
        self.password_checkbox.setChecked(has_password)
        self.password_checkbox.toggled.connect(self._on_password_toggle)
        layout.addWidget(self.password_checkbox)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText(
            "Leave blank to keep the current password" if has_password else "Password"
        )
        self.password_edit.setEnabled(has_password)
        layout.addWidget(self.password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._wants_password: bool = has_password
        self._new_password: str = ""

    def _on_password_toggle(self, checked: bool) -> None:
        self.password_edit.setEnabled(checked)
        if not checked:
            self.password_edit.clear()

    def _on_accept(self) -> None:
        wants_password = self.password_checkbox.isChecked()
        if wants_password and not self._has_password and not self.password_edit.text():
            self.password_edit.setPlaceholderText("Password can't be empty!")
            return
        self._wants_password = wants_password
        self._new_password = self.password_edit.text()
        self.accept()

    @property
    def entered_wants_password(self) -> bool:
        return self._wants_password

    @property
    def entered_new_password(self) -> str:
        """Blank means "no change" when the profile already had a
        password (see the dialog's own placeholder text) — the caller
        is responsible for falling back to the just-verified current
        password in that case, never treating blank as "set an empty
        password.\""""
        return self._new_password
