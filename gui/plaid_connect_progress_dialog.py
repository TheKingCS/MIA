"""
gui.plaid_connect_progress_dialog
====================================

Shown while waiting for the user to finish connecting a bank in their
system browser (Plaid's Hosted Link, opened via webbrowser.open() —
see core/plaid_manager.py's module docstring for why there's no
embedded Link widget). Polls
core.plaid_manager.PlaidManager.check_public_token_once() on a QTimer
rather than calling the manager's blocking poll_for_public_token() —
that method has its own real sleep loop, which would freeze this
dialog's event loop (and the whole app) between checks; a QTimer tick
only ever runs one quick network call at a time, same "don't block the
UI thread" reasoning as every other polling/background-check pattern
in this app (core/device_framework.py's periodic scan,
core/finance_manager.py's watched-folder poll).

No hard timeout here — Cancel is the user's own "give up" action,
simpler than picking an arbitrary GUI-side deadline on top of however
long a real bank login actually takes.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

_POLL_INTERVAL_MS = 3000


class PlaidConnectProgressDialog(QDialog):
    def __init__(self, plaid_manager, link_token: str, parent=None) -> None:
        super().__init__(parent)
        self._plaid_manager = plaid_manager
        self._link_token = link_token
        self._public_token: Optional[str] = None

        self.setWindowTitle("Connecting a Bank")
        self.setFixedSize(360, 150)

        layout = QVBoxLayout(self)
        self.status_label = QLabel(
            "Finish connecting your bank in the browser window that just opened.\n\n"
            "Waiting for it to complete…"
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._check_once)
        self._timer.start()

    def _check_once(self) -> None:
        try:
            token = self._plaid_manager.check_public_token_once(self._link_token)
        except Exception as exc:  # noqa: BLE001 — surface any real API error rather than hang forever
            self._timer.stop()
            self.status_label.setText(f"Something went wrong checking connection status:\n{exc}")
            return

        if token is not None:
            self._timer.stop()
            self._public_token = token
            self.accept()

    def reject(self) -> None:
        self._timer.stop()
        super().reject()

    @property
    def entered_public_token(self) -> Optional[str]:
        return self._public_token
