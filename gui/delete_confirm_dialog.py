"""
gui.delete_confirm_dialog
============================

Requires typing the exact item name before Delete is enabled — used
for permanent, unrecoverable deletions (modules/files_mod/module.py).
Chosen over a plain Yes/No confirmation because a real file manager's
delete is genuinely irreversible (no trash/recycle bin — see
modules/files_mod/file_operations.py's module docstring for why), and
a typed confirmation is much harder to click through by habit than a
Yes/No dialog is.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)



class DeleteConfirmDialog(QDialog):
    def __init__(self, item_name: str, is_directory: bool, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Confirm Delete")
        self.setFixedSize(420, 220)

        self._item_name = item_name

        layout = QVBoxLayout(self)

        kind = "folder and everything inside it" if is_directory else "file"
        warning = QLabel(
            f"This will permanently delete this {kind}:\n\n{item_name}\n\n"
            "There is no trash/recycle bin — this cannot be undone.\n\n"
            "Type the name to confirm:"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        self._confirm_edit = QLineEdit()
        self._confirm_edit.setPlaceholderText(item_name)
        self._confirm_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._confirm_edit)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _on_text_changed(self, text: str) -> None:
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(text == self._item_name)
