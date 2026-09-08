"""
gui.plaid_setup_dialog
=========================

One-time setup dialog for Plaid connectivity — collects the app's own
client_id/secret (obtained by the user from their own Plaid Dashboard
signup at plaid.com; MIA never creates that account on their behalf),
which environment to use, and a new vault passphrase to encrypt them
with (core.plaid_manager.PlaidManager.setup()). Same QDialog + shared
app-level theme + QDialogButtonBox shape as every other dialog here.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from core.plaid_manager import ENVIRONMENTS


class PlaidSetupDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Up Plaid")
        self.setFixedSize(380, 380)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Get a client_id and secret from your own Plaid Dashboard "
            "(plaid.com) first — MIA doesn't create that account for you."
        )
        intro.setWordWrap(True)
        intro.setObjectName("SubtitleLabel")
        layout.addWidget(intro)

        layout.addWidget(QLabel("Client ID:"))
        self.client_id_edit = QLineEdit()
        layout.addWidget(self.client_id_edit)

        layout.addWidget(QLabel("Secret:"))
        self.secret_edit = QLineEdit()
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.secret_edit)

        layout.addWidget(QLabel("Environment:"))
        self.environment_combo = QComboBox()
        self.environment_combo.addItems(ENVIRONMENTS)
        layout.addWidget(self.environment_combo)

        layout.addWidget(QLabel("New vault passphrase (protects the above at rest):"))
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.passphrase_edit)

        layout.addWidget(QLabel("Confirm passphrase:"))
        self.passphrase_confirm_edit = QLineEdit()
        self.passphrase_confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.passphrase_confirm_edit)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e05c5c;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._client_id: str = ""
        self._secret: str = ""
        self._environment: str = ENVIRONMENTS[0]
        self._passphrase: str = ""

    def _on_accept(self) -> None:
        client_id = self.client_id_edit.text().strip()
        secret = self.secret_edit.text().strip()
        passphrase = self.passphrase_edit.text()
        confirm = self.passphrase_confirm_edit.text()

        if not client_id or not secret:
            self.error_label.setText("Client ID and Secret are both required.")
            return
        if not passphrase:
            self.error_label.setText("A vault passphrase is required.")
            return
        if passphrase != confirm:
            self.error_label.setText("Passphrases don't match.")
            return

        self._client_id = client_id
        self._secret = secret
        self._environment = self.environment_combo.currentText()
        self._passphrase = passphrase
        self.accept()

    @property
    def entered_client_id(self) -> str:
        return self._client_id

    @property
    def entered_secret(self) -> str:
        return self._secret

    @property
    def entered_environment(self) -> str:
        return self._environment

    @property
    def entered_passphrase(self) -> str:
        return self._passphrase
