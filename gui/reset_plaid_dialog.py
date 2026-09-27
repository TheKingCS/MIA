"""
gui.reset_plaid_dialog
=========================

Confirmation for core.plaid_manager.PlaidManager.reset() — removes
every bank connection on Plaid's side and deletes the local vault so
Plaid can be set up again (e.g. switching Sandbox -> Production).
Requires typing "reset" plus the vault passphrase, same "typed
confirmation is harder to click through by habit" reasoning as
gui/delete_confirm_dialog.py. The purge checkbox defaults ON in
Sandbox (fake test data shouldn't linger in a real budget) and OFF in
Production (real imported history is worth keeping).
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

_CONFIRM_WORD = "reset"


class ResetPlaidDialog(QDialog):
    def __init__(self, environment: str, connected_count: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reset Plaid Setup")
        self.setFixedSize(460, 400)

        layout = QVBoxLayout(self)

        warning = QLabel(
            f"Current environment: {environment.upper()}\n\n"
            f"This disconnects all {connected_count} connected bank(s) on Plaid's side "
            "(freeing those connection slots), then deletes MIA's saved Plaid keys so you can "
            "run Set Up Plaid again — for example with Production keys.\n\n"
            "If any bank can't be disconnected, the reset stops and nothing else is deleted."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        self.purge_checkbox = QCheckBox("Also delete data imported from Plaid")
        self.purge_checkbox.setChecked(environment == "sandbox")
        layout.addWidget(self.purge_checkbox)
        purge_detail = QLabel(
            "Imported transactions and bank-synced debts. Manual entries are never touched. "
            "(Bank balances always leave your net worth on reset.)"
        )
        purge_detail.setWordWrap(True)
        purge_detail.setObjectName("SubtitleLabel")
        layout.addWidget(purge_detail)

        layout.addWidget(QLabel("Vault passphrase:"))
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.passphrase_edit)

        layout.addWidget(QLabel(f'Type "{_CONFIRM_WORD}" to confirm:'))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.textChanged.connect(self._update_ok_enabled)
        self.passphrase_edit.textChanged.connect(self._update_ok_enabled)
        layout.addWidget(self.confirm_edit)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Reset")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)
        self._update_ok_enabled()

    def _update_ok_enabled(self, *_args) -> None:
        ready = self.confirm_edit.text().strip().lower() == _CONFIRM_WORD and bool(self.passphrase_edit.text())
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ready)

    @property
    def entered_passphrase(self) -> str:
        return self.passphrase_edit.text()

    @property
    def purge_imported_data(self) -> bool:
        return self.purge_checkbox.isChecked()
