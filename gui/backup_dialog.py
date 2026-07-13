"""
gui.backup_dialog
====================

Prompts for backup encryption options when creating a backup (see
modules/settings/module.py and core/backup_manager.py). Unlike profile
passwords (gui/add_profile_dialog.py), a backup passphrase has no
recovery path if mistyped — losing it means losing the backup — so
this dialog requires it to be entered twice and checks they match
before accepting.
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



class BackupPassphraseDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Backup Options")
        self.setFixedSize(380, 260)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Create a backup of your configuration and data."))

        self.encrypt_checkbox = QCheckBox("Encrypt this backup with a passphrase")
        self.encrypt_checkbox.toggled.connect(self._on_encrypt_toggle)
        layout.addWidget(self.encrypt_checkbox)

        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_edit.setPlaceholderText("Passphrase")
        self.passphrase_edit.setEnabled(False)
        layout.addWidget(self.passphrase_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setPlaceholderText("Confirm passphrase")
        self.confirm_edit.setEnabled(False)
        layout.addWidget(self.confirm_edit)

        self.warning_label = QLabel(
            "There is no way to recover a lost passphrase — the backup "
            "would be permanently unreadable."
        )
        self.warning_label.setObjectName("SubtitleLabel")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._passphrase: str = ""

    def _on_encrypt_toggle(self, checked: bool) -> None:
        self.passphrase_edit.setEnabled(checked)
        self.confirm_edit.setEnabled(checked)
        self.warning_label.setVisible(checked)
        if not checked:
            self.passphrase_edit.clear()
            self.confirm_edit.clear()

    def _on_accept(self) -> None:
        if not self.encrypt_checkbox.isChecked():
            self._passphrase = ""
            self.accept()
            return

        passphrase = self.passphrase_edit.text()
        confirm = self.confirm_edit.text()

        if not passphrase:
            self.passphrase_edit.setPlaceholderText("Passphrase can't be empty!")
            return
        if passphrase != confirm:
            self.confirm_edit.clear()
            self.confirm_edit.setPlaceholderText("Passphrases don't match!")
            return

        self._passphrase = passphrase
        self.accept()

    @property
    def entered_passphrase(self) -> str:
        """Empty string means "no encryption requested" — never None, safe to pass straight through."""
        return self._passphrase
