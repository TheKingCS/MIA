"""
gui.add_edit_waypoint_dialog
===============================

Small dialog for creating or editing a single waypoint, used by
modules/navigation/module.py. Same shape as
gui/add_edit_component_dialog.py (QDialog + the shared app-level theme +
QDialogButtonBox, validate-then-expose-via-properties on accept) —
name/latitude/longitude/notes/category instead of name/category/value/
package/quantity/location/notes. Latitude/longitude use QDoubleSpinBox
(range-limited to valid coordinates, 6 decimal places — enough for
~0.1m precision, more than any manual entry needs) rather than a plain
QLineEdit, so an out-of-range or non-numeric value can't be entered at
all instead of being caught after the fact.

`category` (docs/ROADMAP.md milestone 12.2, Trip Log) uses a QComboBox
over `WAYPOINT_CATEGORIES` plus a blank "Uncategorized" option — a fixed
suggested vocabulary, not free text, so campsite pins stay consistently
labeled across a trip's route/map.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.waypoint_manager import WAYPOINT_CATEGORIES, Waypoint


class AddEditWaypointDialog(QDialog):
    def __init__(self, parent=None, waypoint: Optional[Waypoint] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Waypoint" if waypoint is not None else "New Waypoint")
        self.setFixedSize(360, 460)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Latitude:"))
        self.latitude_spin = QDoubleSpinBox()
        self.latitude_spin.setRange(-90.0, 90.0)
        self.latitude_spin.setDecimals(6)
        layout.addWidget(self.latitude_spin)

        layout.addWidget(QLabel("Longitude:"))
        self.longitude_spin = QDoubleSpinBox()
        self.longitude_spin.setRange(-180.0, 180.0)
        self.longitude_spin.setDecimals(6)
        layout.addWidget(self.longitude_spin)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("Uncategorized", "")
        for category in WAYPOINT_CATEGORIES:
            self.category_combo.addItem(category, category)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        layout.addWidget(self.notes_edit, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(waypoint)

        self._name: str = ""
        self._latitude: float = 0.0
        self._longitude: float = 0.0
        self._notes: str = ""
        self._category: str = ""

    def _prefill(self, waypoint: Optional[Waypoint]) -> None:
        if waypoint is not None:
            self.name_edit.setText(waypoint.name)
            self.latitude_spin.setValue(waypoint.latitude)
            self.longitude_spin.setValue(waypoint.longitude)
            self.notes_edit.setPlainText(waypoint.notes)
            index = self.category_combo.findData(waypoint.category)
            self.category_combo.setCurrentIndex(index if index != -1 else 0)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._latitude = self.latitude_spin.value()
        self._longitude = self.longitude_spin.value()
        self._notes = self.notes_edit.toPlainText()
        self._category = self.category_combo.currentData()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_latitude(self) -> float:
        return self._latitude

    @property
    def entered_longitude(self) -> float:
        return self._longitude

    @property
    def entered_notes(self) -> str:
        return self._notes

    @property
    def entered_category(self) -> str:
        return self._category
