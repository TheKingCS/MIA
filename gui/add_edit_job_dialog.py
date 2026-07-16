"""
gui.add_edit_job_dialog
==========================

Small dialog for creating or editing a single fabrication job, used by
modules/workshop/module.py's Jobs tab. Same shape as
gui/add_edit_component_dialog.py — name/description/status (a combo
over core.job_manager.JOB_STATUSES, same "fixed vocabulary" pattern
gui/... project dialogs use for Project's status combo)/labor_hours/
notes. material_consumption/products_produced aren't editable here —
those are recorded via the Jobs tab's own "Consume Material"/"Produce
Product" actions (gui/pick_item_quantity_dialog.py), not free-typed.
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

from core.job_manager import JOB_STATUSES, Job


class AddEditJobDialog(QDialog):
    def __init__(self, parent=None, job: Optional[Job] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Job" if job is not None else "New Job")
        self.setFixedSize(360, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Engrave 20 coasters")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Description (optional)")
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(JOB_STATUSES)
        layout.addWidget(self.status_combo)

        layout.addWidget(QLabel("Labor Hours:"))
        self.labor_hours_spin = QDoubleSpinBox()
        self.labor_hours_spin.setRange(0, 10_000)
        self.labor_hours_spin.setDecimals(2)
        layout.addWidget(self.labor_hours_spin)

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

        self._prefill(job)

        self._name: str = ""
        self._description: str = ""
        self._status: str = JOB_STATUSES[0]
        self._labor_hours: float = 0.0
        self._notes: str = ""

    def _prefill(self, job: Optional[Job]) -> None:
        if job is not None:
            self.name_edit.setText(job.name)
            self.description_edit.setText(job.description)
            index = self.status_combo.findText(job.status)
            if index != -1:
                self.status_combo.setCurrentIndex(index)
            self.labor_hours_spin.setValue(job.labor_hours)
            self.notes_edit.setPlainText(job.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._description = self.description_edit.text().strip()
        self._status = self.status_combo.currentText()
        self._labor_hours = self.labor_hours_spin.value()
        self._notes = self.notes_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_status(self) -> str:
        return self._status

    @property
    def entered_labor_hours(self) -> float:
        return self._labor_hours

    @property
    def entered_notes(self) -> str:
        return self._notes
