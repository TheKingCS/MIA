"""
gui.add_revenue_dialog
=========================

Small dialog for manually recording a revenue entry not tied to a
specific product sale (a commission, a flat fee) — used by
modules/workshop/module.py's Ledger tab. amount/description/notes;
date defaults to today inside core/ledger_manager.py's add_revenue()
itself, so it isn't asked for here. For revenue tied to an actual
product sale, the Ledger tab's "Record Sale" action
(gui/pick_item_quantity_dialog.py + core.ledger_manager.record_sale())
is the real path — this dialog is deliberately the simpler, no-product
case.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class AddRevenueDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Revenue")
        self.setFixedSize(340, 260)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Amount ($):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 1_000_000)
        self.amount_spin.setDecimals(2)
        layout.addWidget(self.amount_spin)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g. Custom commission")
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        layout.addWidget(self.notes_edit)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._amount: float = 0.0
        self._description: str = ""
        self._notes: str = ""

    def _on_accept(self) -> None:
        self._amount = self.amount_spin.value()
        self._description = self.description_edit.text().strip()
        self._notes = self.notes_edit.text().strip()
        self.accept()

    @property
    def entered_amount(self) -> float:
        return self._amount

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_notes(self) -> str:
        return self._notes
