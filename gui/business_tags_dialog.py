"""
gui.business_tags_dialog
===========================

Review Business Tags (2026-09-28, core/business_tagging.py): bank charges
nobody has sorted yet, each with a choice of Decide later / Personal / one
of the owner's businesses, MIA's guess preselected with its reason; and
below, what MIA tagged on her own, which can be changed the same way.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.business_tagging import PERSONAL, apply_choice, auto_tagged, pending_review
from core.region import money

LATER = "__later__"


def format_charge(expense) -> str:
    """Pure formatting logic."""
    return f"{expense.date}  {expense.payee or expense.description or 'Charge'}  {money(expense.amount, ',.2f')}"


class BusinessTagsDialog(QDialog):
    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Review Business Tags")
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Which business is each bank charge for? MIA learns from your answers: a store you've sorted the same "
            "way three times gets tagged automatically after future syncs."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        entities = self.context.budget.all_business_entities()
        self._rows: list[tuple[str, QComboBox, str]] = []  # (entry_id, combo, original choice)

        pending = pending_review(self.context)
        layout.addWidget(QLabel(f"Waiting for you ({len(pending)}):"))
        self._pending_table = self._table([(e, s.entity_id if s else LATER, s.reason if s else "") for e, s in pending],
                                          entities, allow_later=True)
        layout.addWidget(self._pending_table, stretch=2)

        auto = auto_tagged(self.context)
        layout.addWidget(QLabel(f"Tagged automatically ({len(auto)}), change any that are wrong:"))
        self._auto_table = self._table([(e, e.entity_id or PERSONAL, "tagged by MIA") for e in auto], entities,
                                       allow_later=False)
        layout.addWidget(self._auto_table, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _table(self, rows, entities, allow_later: bool) -> QTableWidget:
        table = QTableWidget(len(rows), 3)
        table.setHorizontalHeaderLabels(["Charge", "Business", "Why"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        for row, (expense, choice, reason) in enumerate(rows):
            table.setItem(row, 0, QTableWidgetItem(format_charge(expense)))
            combo = QComboBox()
            if allow_later:
                combo.addItem("Decide later", LATER)
            combo.addItem("Personal", PERSONAL)
            for entity in entities:
                combo.addItem(entity.name, entity.entity_id)
            combo.setCurrentIndex(max(0, combo.findData(choice)))
            table.setCellWidget(row, 1, combo)
            table.setItem(row, 2, QTableWidgetItem(reason))
            # The auto-tagged rows count as changed only if the owner changes them.
            self._rows.append((expense.entry_id, combo, choice if not allow_later else LATER))
        return table

    def _save(self) -> None:
        for entry_id, combo, original in self._rows:
            choice = combo.currentData()
            if choice == LATER:
                continue
            if original != LATER and choice == original:
                # An automatic tag left as it was: now the owner's too.
                self.context.budget.update_expense(entry_id, entity_auto=False)
                continue
            apply_choice(self.context, entry_id, choice)
        self.accept()
