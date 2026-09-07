"""
gui.add_edit_asset_dialog
============================

Small dialog for creating or editing a single maintenance asset
(vehicle, mower, appliance, ...), used by modules/maintenance/module.py.
Same shape as gui/add_edit_journal_entry_dialog.py (QDialog + shared
app-level theme + QDialogButtonBox, validate-then-expose-via-properties
on accept) — name/category/notes instead of title/tags/body.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.maintenance_manager import ASSET_CATEGORIES, MaintenanceAsset


class AddEditAssetDialog(QDialog):
    def __init__(self, parent=None, asset: Optional[MaintenanceAsset] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Asset" if asset is not None else "New Asset")
        self.setFixedSize(360, 340)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 2019 Ford F-150, Lawn Mower, Trek E-Bike")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(ASSET_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional) — model, serial number, purchase date, etc.")
        self.notes_edit.setFixedHeight(90)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(asset)

        self._name: str = ""
        self._category: str = ASSET_CATEGORIES[0]
        self._notes: str = ""

    def _prefill(self, asset: Optional[MaintenanceAsset]) -> None:
        if asset is not None:
            self.name_edit.setText(asset.name)
            if asset.category in ASSET_CATEGORIES:
                self.category_combo.setCurrentText(asset.category)
            self.notes_edit.setPlainText(asset.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._category = self.category_combo.currentText()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_notes(self) -> str:
        return self._notes
