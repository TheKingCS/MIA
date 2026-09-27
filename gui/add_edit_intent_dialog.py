"""
gui.add_edit_intent_dialog
=============================

Small dialog for creating or editing a single Intent (the top-level
container in modules/toolbox/tools/intent_tool.py) — same shape as
gui/add_edit_project_dialog.py: name/description/status, with `status`
as a QComboBox over core.intent_manager.INTENT_STATUSES, plus a
"Current Focus" checkbox that goes through IntentManager.set_primary()
after the dialog closes (not a plain field — see
IntentTool._on_add_intent()/_on_edit_intent(), same "primary is special,
not just another setattr" reasoning as core.intent_manager.IntentManager
itself keeping set_primary() a separate method from update_intent()).
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.intent_manager import INTENT_STATUSES, Intent


class AddEditIntentDialog(QDialog):
    def __init__(self, parent=None, intent: Optional[Intent] = None, intents: Sequence[Intent] = ()) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Intent" if intent is not None else "New Intent")
        self.setFixedSize(380, 560)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 'Homestead Independence'")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        for status in INTENT_STATUSES:
            self.status_combo.addItem(status, status)
        layout.addWidget(self.status_combo)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("What this goal actually means (optional)")
        layout.addWidget(self.description_edit, stretch=1)

        # Cognitive Extension slice B: the owner's chain of reasons
        # (core/why_graph.py). Any other goal can be the bigger one.
        layout.addWidget(QLabel("This serves (a bigger goal):"))
        self.serves_combo = QComboBox()
        self.serves_combo.addItem("(nothing bigger)", None)
        own_id = intent.intent_id if intent is not None else None
        for other in intents:
            if other.intent_id != own_id:
                self.serves_combo.addItem(other.name, other.intent_id)
        layout.addWidget(self.serves_combo)

        layout.addWidget(QLabel("Why, in your own words:"))
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("e.g. 'so I can quit on my own terms'")
        layout.addWidget(self.reason_edit)

        self.primary_checkbox = QCheckBox("Make this my Current Focus")
        layout.addWidget(self.primary_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(intent)

        self._name: str = ""
        self._status: str = ""
        self._description: str = ""
        self._primary: bool = False
        self._serves_intent_id: Optional[str] = None
        self._reason: str = ""

    def _prefill(self, intent: Optional[Intent]) -> None:
        if intent is not None:
            self.name_edit.setText(intent.name)
            index = self.status_combo.findData(intent.status)
            self.status_combo.setCurrentIndex(index if index != -1 else 0)
            self.description_edit.setPlainText(intent.description)
            self.primary_checkbox.setChecked(intent.primary)
            serves_index = self.serves_combo.findData(intent.serves_intent_id)
            self.serves_combo.setCurrentIndex(serves_index if serves_index != -1 else 0)
            self.reason_edit.setText(intent.reason)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._status = self.status_combo.currentData()
        self._description = self.description_edit.toPlainText()
        self._primary = self.primary_checkbox.isChecked()
        self._serves_intent_id = self.serves_combo.currentData()
        self._reason = self.reason_edit.text().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_status(self) -> str:
        return self._status

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_primary(self) -> bool:
        return self._primary

    @property
    def entered_serves_intent_id(self) -> Optional[str]:
        return self._serves_intent_id

    @property
    def entered_reason(self) -> str:
        return self._reason
