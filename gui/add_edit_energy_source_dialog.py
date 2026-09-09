"""
gui.add_edit_energy_source_dialog
====================================

Small dialog for creating or editing a single energy source (solar
array, generator, propane tank, ...), used by modules/power/module.py's
Energy Sources tab. Same shape as gui/add_edit_asset_dialog.py —
including its "Latest Usage" read-only summary label pattern, re-pointed
at core.energy_manager.EnergyManager's own energy_source_meter_names()/
energy_source_readings() — but without the documents/receipts section,
out of scope for v1.
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

from core.energy_manager import ENERGY_SOURCE_TYPES, EnergyManager, EnergySource


class AddEditEnergySourceDialog(QDialog):
    def __init__(
        self,
        parent=None,
        source: Optional[EnergySource] = None,
        energy: Optional[EnergyManager] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Energy Source" if source is not None else "New Energy Source")
        self.setFixedSize(360, 400)
        self._source = source
        self._energy = energy

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Rooftop Solar Array, Backup Generator, Propane Tank")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(ENERGY_SOURCE_TYPES)
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        if source is not None:
            layout.addWidget(QLabel("Latest Usage:"))
            self._usage_label = QLabel("")
            self._usage_label.setWordWrap(True)
            self._usage_label.setObjectName("SubtitleLabel")
            layout.addWidget(self._usage_label)
        else:
            self._usage_label = None

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(source)
        if source is not None:
            self._refresh_usage_label()

        self._name: str = ""
        self._source_type: str = ENERGY_SOURCE_TYPES[0]
        self._notes: str = ""

    def _prefill(self, source: Optional[EnergySource]) -> None:
        if source is not None:
            self.name_edit.setText(source.name)
            if source.source_type in ENERGY_SOURCE_TYPES:
                self.type_combo.setCurrentText(source.source_type)
            self.notes_edit.setPlainText(source.notes)

    def _refresh_usage_label(self) -> None:
        """Read-only glance at every meter this source has logged
        readings under — not editable here, just a summary; logging
        happens on the Energy Sources tab, not inside this dialog."""
        if self._usage_label is None or self._source is None or self._energy is None:
            return
        names = self._energy.energy_source_meter_names(self._source.source_id)
        if not names:
            self._usage_label.setText("No readings logged yet.")
            return
        parts = []
        for name in names:
            readings = self._energy.energy_source_readings(self._source.source_id, name)
            if not readings:
                continue
            latest = readings[-1]
            unit = f" {latest.unit}" if latest.unit else ""
            parts.append(f"{name}: {latest.value:g}{unit} ({latest.timestamp[:10]})")
        self._usage_label.setText("  ·  ".join(parts) if parts else "No readings logged yet.")

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._source_type = self.type_combo.currentText()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_source_type(self) -> str:
        return self._source_type

    @property
    def entered_notes(self) -> str:
        return self._notes
