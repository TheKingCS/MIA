"""
gui.add_edit_asset_dialog
============================

Small dialog for creating or editing a single maintenance asset
(vehicle, mower, appliance, ...), used by modules/maintenance/module.py.
Same shape as gui/add_edit_journal_entry_dialog.py (QDialog + shared
app-level theme + QDialogButtonBox, validate-then-expose-via-properties
on accept) — name/category/notes plus purchase-date/serial/manufacturer/
model instead of title/tags/body.

The documents (receipts/warranties/manuals) list is only shown/enabled
in edit mode (asset is not None) — a brand-new asset has no asset_id yet
to copy files into, same precondition as gui/trip_detail_dialog.py's
Photos section, which this mirrors exactly (Add/Remove/Open buttons over
a QListWidget, QFileDialog.getOpenFileNames to import, immediate effect
via context.maintenance.add_document()/remove_document() rather than
batched until OK — same as Trip's photo add/remove).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QDate, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.maintenance_manager import ASSET_CATEGORIES, MaintenanceAsset, MaintenanceManager

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditAssetDialog(QDialog):
    def __init__(
        self,
        parent=None,
        asset: Optional[MaintenanceAsset] = None,
        maintenance: Optional[MaintenanceManager] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Asset" if asset is not None else "New Asset")
        self.setFixedSize(380, 600)
        self._asset = asset
        self._maintenance = maintenance

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 2019 Ford F-150, Lawn Mower, Trek E-Bike")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(ASSET_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Manufacturer:"))
        self.manufacturer_edit = QLineEdit()
        self.manufacturer_edit.setPlaceholderText("optional")
        layout.addWidget(self.manufacturer_edit)

        layout.addWidget(QLabel("Model:"))
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("optional")
        layout.addWidget(self.model_edit)

        layout.addWidget(QLabel("Serial Number:"))
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText("optional")
        layout.addWidget(self.serial_edit)

        self._purchase_date_cleared = True  # set before the widget below so its first dateChanged fire is safe

        layout.addWidget(QLabel("Purchase Date:"))
        purchase_row = QHBoxLayout()
        self.purchase_date_edit = QDateEdit()
        self.purchase_date_edit.setCalendarPopup(True)
        self.purchase_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.purchase_date_edit.setDate(QDate.currentDate())
        self.purchase_date_edit.dateChanged.connect(self._on_purchase_date_changed)
        purchase_row.addWidget(self.purchase_date_edit)
        self.purchase_date_clear_button = QPushButton("Clear")
        self.purchase_date_clear_button.clicked.connect(self._on_clear_purchase_date)
        purchase_row.addWidget(self.purchase_date_clear_button)
        layout.addLayout(purchase_row)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        if asset is not None:
            layout.addWidget(QLabel("Latest Usage:"))
            self._usage_label = QLabel("")
            self._usage_label.setWordWrap(True)
            self._usage_label.setObjectName("SubtitleLabel")
            layout.addWidget(self._usage_label)
        else:
            self._usage_label = None

        if asset is not None:
            documents_title = QLabel("Documents (receipts, warranties, manuals):")
            layout.addWidget(documents_title)

            self._document_list = QListWidget()
            layout.addWidget(self._document_list, stretch=1)

            document_buttons = QHBoxLayout()
            add_doc_button = QPushButton("Add…")
            add_doc_button.clicked.connect(self._on_add_documents)
            document_buttons.addWidget(add_doc_button)

            open_doc_button = QPushButton("Open Selected")
            open_doc_button.clicked.connect(self._on_open_document)
            document_buttons.addWidget(open_doc_button)

            remove_doc_button = QPushButton("Remove Selected")
            remove_doc_button.clicked.connect(self._on_remove_document)
            document_buttons.addWidget(remove_doc_button)
            layout.addLayout(document_buttons)
        else:
            self._document_list = None

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(asset)
        if asset is not None:
            self._refresh_document_list()
            self._refresh_usage_label()

        self._name: str = ""
        self._category: str = ASSET_CATEGORIES[0]
        self._notes: str = ""
        self._purchase_date: str = ""
        self._serial_number: str = ""
        self._manufacturer: str = ""
        self._model: str = ""

    def _prefill(self, asset: Optional[MaintenanceAsset]) -> None:
        if asset is not None:
            self.name_edit.setText(asset.name)
            if asset.category in ASSET_CATEGORIES:
                self.category_combo.setCurrentText(asset.category)
            self.notes_edit.setPlainText(asset.notes)
            self.manufacturer_edit.setText(asset.manufacturer)
            self.model_edit.setText(asset.model)
            self.serial_edit.setText(asset.serial_number)
            if asset.purchase_date:
                self.purchase_date_edit.setDate(QDate.fromString(asset.purchase_date, _ISO_DATE_FORMAT))
                self._purchase_date_cleared = False

    def _on_purchase_date_changed(self, _new_date: QDate) -> None:
        self._purchase_date_cleared = False

    def _on_clear_purchase_date(self) -> None:
        self.purchase_date_edit.blockSignals(True)
        self.purchase_date_edit.setDate(QDate.currentDate())
        self.purchase_date_edit.blockSignals(False)
        self._purchase_date_cleared = True

    def _refresh_usage_label(self) -> None:
        """Read-only glance at every meter this asset has logged usage
        under (via modules/maintenance/module.py's "Log Usage…" action) —
        not editable here, just a summary; logging happens on the Assets
        tab, not inside this dialog."""
        if self._usage_label is None or self._asset is None or self._maintenance is None:
            return
        names = self._maintenance.asset_meter_names(self._asset.asset_id)
        if not names:
            self._usage_label.setText("No usage logged yet.")
            return
        parts = []
        for name in names:
            readings = self._maintenance.asset_readings(self._asset.asset_id, name)
            if not readings:
                continue
            latest = readings[-1]
            unit = f" {latest.unit}" if latest.unit else ""
            parts.append(f"{name}: {latest.value:g}{unit} ({latest.timestamp[:10]})")
        self._usage_label.setText("  ·  ".join(parts) if parts else "No usage logged yet.")

    def _refresh_document_list(self) -> None:
        self._document_list.clear()
        if self._asset is None:
            return
        for filename in self._asset.documents:
            self._document_list.addItem(QListWidgetItem(filename))

    def _on_add_documents(self) -> None:
        if self._asset is None or self._maintenance is None:
            return
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Document(s)", "", "Documents (*.pdf *.png *.jpg *.jpeg);;All Files (*)"
        )
        for file_path in file_paths:
            self._maintenance.add_document(self._asset.asset_id, Path(file_path))
        self._refresh_document_list()

    def _on_open_document(self) -> None:
        if self._asset is None or self._maintenance is None:
            return
        item = self._document_list.currentItem()
        if item is None:
            return
        path = self._maintenance.document_path(self._asset.asset_id, item.text())
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_remove_document(self) -> None:
        if self._asset is None or self._maintenance is None:
            return
        item = self._document_list.currentItem()
        if item is None:
            return
        self._maintenance.remove_document(self._asset.asset_id, item.text())
        self._refresh_document_list()

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._category = self.category_combo.currentText()
        self._notes = self.notes_edit.toPlainText().strip()
        self._manufacturer = self.manufacturer_edit.text().strip()
        self._model = self.model_edit.text().strip()
        self._serial_number = self.serial_edit.text().strip()
        self._purchase_date = "" if self._purchase_date_cleared else self.purchase_date_edit.date().toString(_ISO_DATE_FORMAT)
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

    @property
    def entered_purchase_date(self) -> str:
        return self._purchase_date

    @property
    def entered_serial_number(self) -> str:
        return self._serial_number

    @property
    def entered_manufacturer(self) -> str:
        return self._manufacturer

    @property
    def entered_model(self) -> str:
        return self._model
