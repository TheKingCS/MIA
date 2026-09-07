"""
gui.add_edit_maintenance_task_dialog
=======================================

Small dialog for creating or editing a single maintenance task, used
by modules/maintenance/module.py. Same shape as
gui/add_edit_journal_entry_dialog.py (QDialog + shared app-level theme
+ QDialogButtonBox, validate-then-expose-via-properties on accept) —
asset/title/recurrence/notes instead of title/tags/body.

Named AddEditMaintenanceTaskDialog (not AddEditTaskDialog) deliberately
— gui/add_edit_task_dialog.py already exists for Project Manager's
unrelated core.task_manager.Task (a to-do item under a Project). Found
live: an early draft of this dialog reused that exact filename/class
name and silently overwrote the real Project Manager dialog before
this rename — a real, since-fixed mistake, not a naming style choice.

last_completed is deliberately NOT a field here — a new task starts
honestly as "never done yet" (None), same as a fresh MaintenanceTask's
default. "Mark Complete" on the Tasks tab is the one real place
last_completed gets set, which keeps this dialog simple and matches
how the action actually happens in practice (you did the work, then
you say so) rather than asking the user to backdate a first
completion during creation.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.maintenance_manager import MaintenanceAsset, MaintenanceTask

_DEFAULT_INTERVAL_DAYS = 30


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
        self.setFixedSize(360, 380)
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

        self.recurring_checkbox = QCheckBox("Recurring")
        self.recurring_checkbox.toggled.connect(self._on_recurring_toggle)
        layout.addWidget(self.recurring_checkbox)

        layout.addWidget(QLabel("Repeat every (days):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 3650)
        self.interval_spin.setValue(_DEFAULT_INTERVAL_DAYS)
        layout.addWidget(self.interval_spin)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(80)
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

    def _prefill(self, task: Optional[MaintenanceTask], default_asset_id: Optional[str]) -> None:
        if task is not None:
            index = self.asset_combo.findData(task.asset_id)
            if index >= 0:
                self.asset_combo.setCurrentIndex(index)
            self.title_edit.setText(task.title)
            self.notes_edit.setPlainText(task.notes)
            if task.interval_days is not None:
                self.recurring_checkbox.setChecked(True)
                self.interval_spin.setValue(task.interval_days)
            else:
                self.recurring_checkbox.setChecked(False)
        else:
            if default_asset_id is not None:
                index = self.asset_combo.findData(default_asset_id)
                if index >= 0:
                    self.asset_combo.setCurrentIndex(index)
            self.recurring_checkbox.setChecked(True)

        self._on_recurring_toggle(self.recurring_checkbox.isChecked())

    def _on_recurring_toggle(self, checked: bool) -> None:
        self.interval_spin.setEnabled(checked)

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
        self._interval_days = self.interval_spin.value() if self.recurring_checkbox.isChecked() else None
        self._notes = self.notes_edit.toPlainText().strip()
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
