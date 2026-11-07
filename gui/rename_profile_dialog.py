"""
gui.rename_profile_dialog
============================

A small, focused dialog for renaming the active profile from Settings —
same shape/size precedent as gui/add_profile_dialog.py, just a name
field instead of name+password.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class RenameProfileDialog(QDialog):
    """Renaming a profile."""
    def __init__(self, current_name: str, parent=None) -> None:
        """The new-name field (the current name to start) with OK and Cancel."""
        super().__init__(parent)
        self.setWindowTitle("Rename Profile")
        self.setFixedSize(340, 150)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("New name:"))

        self.name_edit = QLineEdit()
        self.name_edit.setText(current_name)
        layout.addWidget(self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._name: str = ""

    def _on_accept(self) -> None:
        """Keeps the name and closes; an empty name is pointed out in its box instead."""
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return
        self._name = name
        self.accept()

    @property
    def entered_name(self) -> str:
        """The name entered in the dialog (kept when OK is pressed)."""
        return self._name
