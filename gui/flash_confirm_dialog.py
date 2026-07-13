"""
gui.flash_confirm_dialog
===========================

Confirmation dialog for Field Kit's OS + M.I.A. flashing/provisioning
action (docs/ROADMAP.md milestone 11.3) — writing an image to the
wrong device is unrecoverable (a bricked Pi, or a wiped real drive), so
this is deliberately the most cautious confirmation flow in the app,
one step beyond `gui/delete_confirm_dialog.py`'s already-established
"type to confirm" pattern (used for permanent file deletion):

- Every identifying detail of the target (model, size, raw device
  path, current filesystem/mountpoint) is shown up front, in plain
  language, so the user can visually cross-check it against the
  physical device in their hand before typing anything.
- The typed confirmation text is the device's own Linux name (e.g.
  "sdb") rather than a generic word like "yes" or "confirm" — the same
  reasoning `DeleteConfirmDialog` uses for the item's actual name:
  much harder to satisfy by habit/muscle memory than any fixed phrase.
- The match check itself (`core.device_framework.flash_confirmation_matches`)
  is a separate, unit-tested function rather than an inline string
  comparison — this is the more dangerous of this project's two
  "type to confirm" flows, so it gets an extra seam for testing.

This dialog only gates the *user's* confirmation (Rails 1-3 of the
milestone 11.3 design — boot-device exclusion already happened before
a device could even reach this dialog, via
`core.device_framework.list_block_devices()`). Rails 4/5 (re-validating
the device is still the same physical one, and still not the boot
device, immediately before writing) happen in the caller right before
the actual write starts, not here — this dialog is a point-in-time
snapshot of what the user saw and agreed to.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from core.device_framework import BlockDevice, flash_confirmation_matches
from gui.styles import DARK_FIELD_THEME


class FlashConfirmDialog(QDialog):
    def __init__(self, device: BlockDevice, image_path: str, image_size_display: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Confirm Flash — This Cannot Be Undone")
        self.setStyleSheet(DARK_FIELD_THEME)
        self.setMinimumSize(480, 320)

        self._device = device

        layout = QVBoxLayout(self)

        current_contents = (
            f"currently {device.fstype or 'unknown filesystem'}"
            + (f", mounted at {device.mountpoint}" if device.mountpoint else ", not mounted")
        )
        warning = QLabel(
            "This will ERASE ALL DATA on:\n\n"
            f"  {device.model or device.name}  ({device.size})\n"
            f"  /dev/{device.name}  —  {current_contents}\n\n"
            "Image to write:\n"
            f"  {image_path}  ({image_size_display})\n\n"
            "This cannot be undone. Double-check this is the exact drive "
            "you intend to overwrite — not any other device plugged in.\n\n"
            f"Type the device name to confirm:"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        self._confirm_edit = QLineEdit()
        self._confirm_edit.setPlaceholderText(device.name)
        self._confirm_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._confirm_edit)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Flash")
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _on_text_changed(self, text: str) -> None:
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            flash_confirmation_matches(text, self._device.name)
        )
