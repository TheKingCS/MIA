"""
gui.add_expense_dialog
=========================

Small dialog for recording an expense entry — used by
modules/workshop/module.py's Ledger tab. amount/category (a combo over
core.ledger_manager.EXPENSE_CATEGORIES)/description/notes; date
defaults to today inside core/ledger_manager.py's add_expense() itself,
so it isn't asked for here.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from core.ledger_manager import EXPENSE_CATEGORIES


class AddExpenseDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Expense")
        self.setFixedSize(340, 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Amount ($):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 1_000_000)
        self.amount_spin.setDecimals(2)
        layout.addWidget(self.amount_spin)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(EXPENSE_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g. Plywood restock")
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
        self._category: str = EXPENSE_CATEGORIES[0]
        self._description: str = ""
        self._notes: str = ""

    def _on_accept(self) -> None:
        self._amount = self.amount_spin.value()
        self._category = self.category_combo.currentText()
        self._description = self.description_edit.text().strip()
        self._notes = self.notes_edit.text().strip()
        self.accept()

    @property
    def entered_amount(self) -> float:
        return self._amount

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_notes(self) -> str:
        return self._notes
