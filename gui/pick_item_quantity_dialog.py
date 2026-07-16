"""
gui.pick_item_quantity_dialog
================================

One reusable dialog for three actions that all share the same real
shape — "pick an existing item, enter a quantity (and optionally an
amount)": modules/workshop/module.py's Jobs tab "Consume Material" and
"Produce Product" actions (core/job_manager.py's consume_material()/
produce_product()), and its Ledger tab's "Record Sale" action
(core/ledger_manager.py's record_sale()). Building one parametrized
dialog here instead of three near-identical ones — the field shape is
genuinely the same, only the labels/whether an amount field is shown
differ.

Callers are responsible for checking `items` isn't empty first (and
showing their own "add a material/product first" message) — this
dialog doesn't special-case that, same as this project's existing
dialogs assuming the caller already validated there's something to
pick from.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QVBoxLayout,
)


class PickItemQuantityDialog(QDialog):
    def __init__(
        self,
        parent=None,
        title: str = "",
        item_label: str = "Item:",
        items: Optional[list[tuple[str, str]]] = None,
        quantity_label: str = "Quantity:",
        include_amount: bool = False,
        amount_label: str = "Amount ($):",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(340, 260 if include_amount else 200)
        self._include_amount = include_amount

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(item_label))
        self.item_combo = QComboBox()
        for item_id, display_text in items or []:
            self.item_combo.addItem(display_text, item_id)
        layout.addWidget(self.item_combo)

        layout.addWidget(QLabel(quantity_label))
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 1_000_000)
        self.quantity_spin.setDecimals(2)
        layout.addWidget(self.quantity_spin)

        if include_amount:
            layout.addWidget(QLabel(amount_label))
            self.amount_spin = QDoubleSpinBox()
            self.amount_spin.setRange(0, 1_000_000)
            self.amount_spin.setDecimals(2)
            layout.addWidget(self.amount_spin)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._item_id: str = ""
        self._quantity: float = 0.0
        self._amount: float = 0.0

    def _on_accept(self) -> None:
        self._item_id = self.item_combo.currentData()
        self._quantity = self.quantity_spin.value()
        if self._include_amount:
            self._amount = self.amount_spin.value()
        self.accept()

    @property
    def entered_item_id(self) -> str:
        return self._item_id

    @property
    def entered_quantity(self) -> float:
        return self._quantity

    @property
    def entered_amount(self) -> float:
        return self._amount
