"""
modules.power.module
======================

Power — docs/ROADMAP.md milestone 7.2, plus manual energy/utility
tracking added 2026-09-09 (the last of four "Field Manual" brainstorm
items this session). Two tabs: Battery (the original, unchanged
`AppContext.power`/core/power_manager.py battery/UPS view) and Energy
Sources (`AppContext.energy`/core/energy_manager.py — user-named
sources like solar arrays, generators, propane tanks, each with
manually-logged readings). Same `QTabWidget` multi-feature-in-one-module
shape as modules/maintenance/module.py/modules/budget/module.py.

Energy Sources is manual-entry only, same "no real hardware yet"
stance core/energy_manager.py's own docstring states — the user
confirmed this directly when asked. No chart here (unlike modules/lab
/module.py, which already proves QtCharts works in this codebase) —
the user's own ask was "tracking," not trend visualization; a plain
readings list is the honest v1 scope, see core/energy_manager.py's
docstring for the full reasoning.

format_power_status()/format_energy_source_row()/
format_energy_reading_row() are free functions (not methods), same
pure-formatting-logic shape as modules/diagnostics/module.py's
format_system_health() — testable without Qt, see
tests/test_power_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.data_logger_manager import Reading
from core.energy_manager import EnergySource
from core.power_manager import PowerStatus
from gui.add_edit_energy_source_dialog import AddEditEnergySourceDialog
from gui.log_asset_reading_dialog import LogAssetReadingDialog
from modules.module_base import ModuleBase

_REFRESH_MS = 5000


def format_power_status(status: Optional[PowerStatus]) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_power_module.py)."""
    if status is None:
        return "No battery or UPS detected on this system."

    lines = [
        f"Battery: {status.percent:.0f}%",
        "Power: Plugged in" if status.plugged_in else "Power: On battery",
    ]
    if not status.plugged_in and status.seconds_left is not None:
        minutes_left = status.seconds_left // 60
        lines.append(f"Estimated time remaining: {minutes_left} min")
    return "\n".join(lines)


def format_energy_source_row(source: EnergySource) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_power_module.py)."""
    return f"{source.name}   [{source.source_type}]"


def format_energy_reading_row(reading: Reading) -> str:
    """Pure formatting logic — testable without Qt. Same shape as
    modules/lab/module.py's format_reading_row()."""
    value_part = f"{reading.value:g}{' ' + reading.unit if reading.unit else ''}"
    time_part = reading.timestamp.replace("T", " ") if reading.timestamp else ""
    note_part = f"  — {reading.note}" if reading.note else ""
    return f"{time_part}   {value_part}{note_part}"


class PowerModule(ModuleBase):
    module_id = "power"
    display_name = "Power"
    description = "Battery status and manual energy/utility tracking."
    icon = "\U0001F50B"  # battery

    def __init__(self, context) -> None:
        super().__init__(context)
        self._status_label: Optional[QLabel] = None
        self._timer: Optional[QTimer] = None

        self._source_list: Optional[QListWidget] = None
        self._meter_combo: Optional[QComboBox] = None
        self._readings_list: Optional[QListWidget] = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        tabs.addTab(self._build_battery_tab(), "Battery")
        tabs.addTab(self._build_energy_sources_tab(), "Energy Sources")
        layout.addWidget(tabs, stretch=1)

        return widget

    # ------------------------------------------------------------------
    # Battery tab — unchanged from the original single-view module
    # ------------------------------------------------------------------

    def _build_battery_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._status_label = QLabel("")
        self._status_label.setObjectName("ReadoutLabel")
        layout.addWidget(self._status_label)
        layout.addStretch()

        self._refresh_battery()

        self._timer = QTimer(tab)
        self._timer.timeout.connect(self._refresh_battery)
        self._timer.start(_REFRESH_MS)

        return tab

    def _refresh_battery(self) -> None:
        if self._status_label is None:
            return
        status = self.context.power.read() if self.context.power is not None else None
        self._status_label.setText(format_power_status(status))

    # ------------------------------------------------------------------
    # Energy Sources tab
    # ------------------------------------------------------------------

    def _build_energy_sources_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._source_list = QListWidget()
        self._source_list.currentItemChanged.connect(lambda *_: self._refresh_meter_combo())
        layout.addWidget(self._source_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Source")
        add_button.clicked.connect(self._on_add_energy_source)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_energy_source)
        button_row.addWidget(edit_button)

        log_button = QPushButton("Log Reading…")
        log_button.clicked.connect(self._on_log_energy_reading)
        button_row.addWidget(log_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_energy_source)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        meter_row = QHBoxLayout()
        meter_row.addWidget(QLabel("Meter:"))
        self._meter_combo = QComboBox()
        self._meter_combo.currentTextChanged.connect(lambda _text: self._refresh_readings_list())
        meter_row.addWidget(self._meter_combo, stretch=1)
        layout.addLayout(meter_row)

        self._readings_list = QListWidget()
        layout.addWidget(self._readings_list, stretch=1)

        self._refresh_energy_source_list()
        return tab

    def _refresh_energy_source_list(self) -> None:
        self._source_list.clear()
        for source in self.context.energy.all_energy_sources():
            item = QListWidgetItem(format_energy_source_row(source))
            item.setData(Qt.ItemDataRole.UserRole, source.source_id)
            self._source_list.addItem(item)
        self._refresh_meter_combo()

    def _selected_energy_source_id(self) -> Optional[str]:
        item = self._source_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _refresh_meter_combo(self) -> None:
        source_id = self._selected_energy_source_id()
        self._meter_combo.blockSignals(True)
        self._meter_combo.clear()
        if source_id is not None:
            self._meter_combo.addItems(self.context.energy.energy_source_meter_names(source_id))
        self._meter_combo.blockSignals(False)
        self._refresh_readings_list()

    def _refresh_readings_list(self) -> None:
        self._readings_list.clear()
        source_id = self._selected_energy_source_id()
        meter_name = self._meter_combo.currentText()
        if source_id is None or not meter_name:
            return
        for reading in self.context.energy.energy_source_readings(source_id, meter_name):
            self._readings_list.addItem(QListWidgetItem(format_energy_reading_row(reading)))

    def _on_add_energy_source(self) -> None:
        dialog = AddEditEnergySourceDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.energy.add_energy_source(
            name=dialog.entered_name,
            source_type=dialog.entered_source_type,
            notes=dialog.entered_notes,
        )
        self._refresh_energy_source_list()

    def _on_edit_energy_source(self) -> None:
        source_id = self._selected_energy_source_id()
        if source_id is None:
            QMessageBox.information(None, "No Source Selected", "Select an energy source to edit.")
            return

        source = self.context.energy.get_energy_source(source_id)
        dialog = AddEditEnergySourceDialog(source=source, energy=self.context.energy)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.energy.update_energy_source(
            source_id,
            name=dialog.entered_name,
            source_type=dialog.entered_source_type,
            notes=dialog.entered_notes,
        )
        self._refresh_energy_source_list()

    def _on_delete_energy_source(self) -> None:
        source_id = self._selected_energy_source_id()
        if source_id is None:
            QMessageBox.information(None, "No Source Selected", "Select an energy source to delete.")
            return

        source = self.context.energy.get_energy_source(source_id)
        confirm = QMessageBox.question(
            None,
            "Delete Energy Source",
            f"Delete '{source.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.energy.delete_energy_source(source_id)
        self._refresh_energy_source_list()

    def _on_log_energy_reading(self) -> None:
        source_id = self._selected_energy_source_id()
        if source_id is None:
            QMessageBox.information(None, "No Source Selected", "Select an energy source to log a reading for.")
            return

        known_names = self.context.energy.energy_source_meter_names(source_id)
        dialog = LogAssetReadingDialog(known_meter_names=known_names)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.energy.log_energy_reading(
            source_id, dialog.entered_meter_name, dialog.entered_value, unit=dialog.entered_unit, note=dialog.entered_note
        )
        self._refresh_meter_combo()
