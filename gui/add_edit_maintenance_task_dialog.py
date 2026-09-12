"""
gui.add_edit_maintenance_task_dialog
=======================================

Small dialog for creating or editing a single maintenance task, used
by modules/maintenance/module.py. Same shape as
gui/add_edit_journal_entry_dialog.py (QDialog + shared app-level theme
+ QDialogButtonBox, validate-then-expose-via-properties on accept) —
asset/title/trigger/notes instead of title/tags/body.

Named AddEditMaintenanceTaskDialog (not AddEditTaskDialog) deliberately
— gui/add_edit_task_dialog.py already exists for Project Manager's
unrelated core.task_manager.Task (a to-do item under a Project). Found
live: an early draft of this dialog reused that exact filename/class
name and silently overwrote the real Project Manager dialog before
this rename — a real, since-fixed mistake, not a naming style choice.

v2 adds a trigger-type combo that swaps a QStackedWidget page: Calendar
(the original recurring-checkbox + day-interval spin, unchanged),
Meter (Runtime/Mileage/Cycles/Condition — one unit line edit + an
interval spin, since all four share core.maintenance_manager's
"cumulative reading vs. an interval" mechanism and differ only in
label/unit), and Sensor (unit + threshold value + above/below combo,
the "reading crosses a line" mechanism). Values for the meter/sensor
mechanisms come later via "Log Reading…" on the Tasks tab, not here —
this dialog only defines the rule, not a first reading.

last_completed/last_completed_meter_value are deliberately NOT fields
here — a new task starts honestly as "never done yet", same as a fresh
MaintenanceTask's defaults. "Mark Complete" on the Tasks tab is the one
real place those get set.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.maintenance_manager import DEFAULT_METER_UNITS, PRIORITY_LEVELS, MaintenanceAsset, MaintenanceTask

_DEFAULT_INTERVAL_DAYS = 30

# Display label -> stored trigger_type value, in combo order.
_TRIGGER_TYPE_LABELS = [
    ("Calendar", "calendar"),
    ("Runtime", "runtime"),
    ("Mileage", "mileage"),
    ("Cycles", "cycles"),
    ("Condition", "condition"),
    ("Sensor", "sensor"),
]
_CALENDAR_PAGE, _METER_PAGE, _SENSOR_PAGE = 0, 1, 2


class AddEditMaintenanceTaskDialog(QDialog):
    def __init__(
        self,
        parent=None,
        assets: Optional[list[MaintenanceAsset]] = None,
        task: Optional[MaintenanceTask] = None,
        default_asset_id: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Task" if task is not None else "New Task")
        self.setFixedSize(380, 570)
        self._assets = assets or []

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Asset:"))
        self.asset_combo = QComboBox()
        for asset in self._assets:
            self.asset_combo.addItem(f"{asset.name} ({asset.category})", asset.asset_id)
        layout.addWidget(self.asset_combo)

        layout.addWidget(QLabel("Task:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Oil change, Mow lawn, Replace HVAC filter")
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel("Trigger:"))
        self.trigger_combo = QComboBox()
        for label, _value in _TRIGGER_TYPE_LABELS:
            self.trigger_combo.addItem(label)
        self.trigger_combo.currentIndexChanged.connect(self._on_trigger_changed)
        layout.addWidget(self.trigger_combo)

        self.trigger_stack = QStackedWidget()
        self.trigger_stack.addWidget(self._build_calendar_page())
        self.trigger_stack.addWidget(self._build_meter_page())
        self.trigger_stack.addWidget(self._build_sensor_page())
        layout.addWidget(self.trigger_stack)

        self.auto_schedule_checkbox = QCheckBox("Auto-schedule a calendar event once due")
        layout.addWidget(self.auto_schedule_checkbox)

        layout.addWidget(QLabel("Priority:"))
        self.priority_combo = QComboBox()
        for level in PRIORITY_LEVELS:
            self.priority_combo.addItem(level.capitalize(), level)
        self.priority_combo.setCurrentIndex(PRIORITY_LEVELS.index("normal"))
        layout.addWidget(self.priority_combo)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(task, default_asset_id)

        self._asset_id: str = ""
        self._title: str = ""
        self._interval_days: Optional[int] = None
        self._notes: str = ""
        self._trigger_type: str = "calendar"
        self._meter_unit: str = ""
        self._meter_interval: Optional[float] = None
        self._threshold_value: Optional[float] = None
        self._threshold_direction: str = "below"
        self._auto_schedule: bool = False
        self._priority: str = "normal"

    # ------------------------------------------------------------------
    # Trigger-type pages
    # ------------------------------------------------------------------

    def _build_calendar_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.recurring_checkbox = QCheckBox("Recurring")
        self.recurring_checkbox.toggled.connect(self._on_recurring_toggle)
        layout.addWidget(self.recurring_checkbox)

        layout.addWidget(QLabel("Repeat every (days):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 3650)
        self.interval_spin.setValue(_DEFAULT_INTERVAL_DAYS)
        layout.addWidget(self.interval_spin)

        return page

    def _build_meter_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Unit:"))
        self.meter_unit_edit = QLineEdit()
        self.meter_unit_edit.setPlaceholderText("e.g. engine hours, miles, starts")
        layout.addWidget(self.meter_unit_edit)

        layout.addWidget(QLabel("Due every:"))
        self.meter_interval_spin = QDoubleSpinBox()
        self.meter_interval_spin.setRange(0.1, 1_000_000.0)
        self.meter_interval_spin.setDecimals(1)
        self.meter_interval_spin.setValue(50.0)
        layout.addWidget(self.meter_interval_spin)

        return page

    def _build_sensor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Unit:"))
        self.sensor_unit_edit = QLineEdit()
        self.sensor_unit_edit.setPlaceholderText("e.g. V, PSI, ppm")
        layout.addWidget(self.sensor_unit_edit)

        layout.addWidget(QLabel("Due when reading is:"))
        self.threshold_direction_combo = QComboBox()
        self.threshold_direction_combo.addItems(["below", "above"])
        layout.addWidget(self.threshold_direction_combo)

        layout.addWidget(QLabel("Threshold value:"))
        self.threshold_value_spin = QDoubleSpinBox()
        self.threshold_value_spin.setRange(-1_000_000.0, 1_000_000.0)
        self.threshold_value_spin.setDecimals(1)
        layout.addWidget(self.threshold_value_spin)

        return page

    def _on_trigger_changed(self, index: int) -> None:
        trigger_type = _TRIGGER_TYPE_LABELS[index][1]
        if trigger_type == "calendar":
            self.trigger_stack.setCurrentIndex(_CALENDAR_PAGE)
        elif trigger_type == "sensor":
            self.trigger_stack.setCurrentIndex(_SENSOR_PAGE)
        else:
            self.trigger_stack.setCurrentIndex(_METER_PAGE)
            if not self.meter_unit_edit.text().strip():
                self.meter_unit_edit.setText(DEFAULT_METER_UNITS.get(trigger_type, ""))

    def _on_recurring_toggle(self, checked: bool) -> None:
        self.interval_spin.setEnabled(checked)

    # ------------------------------------------------------------------

    def _prefill(self, task: Optional[MaintenanceTask], default_asset_id: Optional[str]) -> None:
        if task is not None:
            index = self.asset_combo.findData(task.asset_id)
            if index >= 0:
                self.asset_combo.setCurrentIndex(index)
            self.title_edit.setText(task.title)
            self.notes_edit.setPlainText(task.notes)
            self.auto_schedule_checkbox.setChecked(task.auto_schedule)
            priority_index = self.priority_combo.findData(task.priority)
            self.priority_combo.setCurrentIndex(priority_index if priority_index != -1 else PRIORITY_LEVELS.index("normal"))

            trigger_index = next(
                (i for i, (_label, value) in enumerate(_TRIGGER_TYPE_LABELS) if value == task.trigger_type), 0
            )
            self.trigger_combo.setCurrentIndex(trigger_index)

            if task.interval_days is not None:
                self.recurring_checkbox.setChecked(True)
                self.interval_spin.setValue(task.interval_days)
            else:
                self.recurring_checkbox.setChecked(False)

            self.meter_unit_edit.setText(task.meter_unit)
            self.sensor_unit_edit.setText(task.meter_unit)
            if task.meter_interval is not None:
                self.meter_interval_spin.setValue(task.meter_interval)
            if task.threshold_value is not None:
                self.threshold_value_spin.setValue(task.threshold_value)
            self.threshold_direction_combo.setCurrentText(task.threshold_direction)
        else:
            if default_asset_id is not None:
                index = self.asset_combo.findData(default_asset_id)
                if index >= 0:
                    self.asset_combo.setCurrentIndex(index)
            self.recurring_checkbox.setChecked(True)

        self._on_recurring_toggle(self.recurring_checkbox.isChecked())
        self._on_trigger_changed(self.trigger_combo.currentIndex())

    def _on_accept(self) -> None:
        # Zero assets is a precondition the module checks BEFORE opening
        # this dialog (see modules/maintenance/module.py's _on_add_task),
        # not something this dialog needs to guard against itself.
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setPlaceholderText("Task can't be empty!")
            return

        self._asset_id = self.asset_combo.currentData()
        self._title = title
        self._notes = self.notes_edit.toPlainText().strip()
        self._auto_schedule = self.auto_schedule_checkbox.isChecked()
        self._priority = self.priority_combo.currentData()
        self._trigger_type = _TRIGGER_TYPE_LABELS[self.trigger_combo.currentIndex()][1]

        self._interval_days = None
        self._meter_unit = ""
        self._meter_interval = None
        self._threshold_value = None
        self._threshold_direction = "below"

        if self._trigger_type == "calendar":
            self._interval_days = self.interval_spin.value() if self.recurring_checkbox.isChecked() else None
        elif self._trigger_type == "sensor":
            self._meter_unit = self.sensor_unit_edit.text().strip()
            self._threshold_value = self.threshold_value_spin.value()
            self._threshold_direction = self.threshold_direction_combo.currentText()
        else:
            self._meter_unit = self.meter_unit_edit.text().strip()
            self._meter_interval = self.meter_interval_spin.value()

        self.accept()

    @property
    def entered_asset_id(self) -> str:
        return self._asset_id

    @property
    def entered_title(self) -> str:
        return self._title

    @property
    def entered_interval_days(self) -> Optional[int]:
        return self._interval_days

    @property
    def entered_notes(self) -> str:
        return self._notes

    @property
    def entered_trigger_type(self) -> str:
        return self._trigger_type

    @property
    def entered_meter_unit(self) -> str:
        return self._meter_unit

    @property
    def entered_meter_interval(self) -> Optional[float]:
        return self._meter_interval

    @property
    def entered_threshold_value(self) -> Optional[float]:
        return self._threshold_value

    @property
    def entered_threshold_direction(self) -> str:
        return self._threshold_direction

    @property
    def entered_auto_schedule(self) -> bool:
        return self._auto_schedule

    @property
    def entered_priority(self) -> str:
        return self._priority
