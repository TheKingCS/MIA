"""
modules.budget.module
========================

Budget: household bills, income, and expenses. Four tabs (Bills,
Income, Expenses, Summary) — same `QTabWidget` multi-feature-in-one-
module shape as modules/maintenance/module.py and
modules/workshop/module.py, since these are four closely-related views
over one connected data set rather than separate top-level modules.

All persistence/recurrence/reporting logic lives in
core/budget_manager.py (self.context.budget) — this module is the
Qt-facing wrapper around it, same split as every other data-backed
module here.

The Bills tab's "Mark Paid" action is the real integration point: it
opens gui/mark_bill_paid_dialog.py, then calls
self.context.budget.mark_bill_paid(...), which both records a real
Expense entry AND advances the bill's own due date — one click, two
real effects, same shape as Maintenance's "Mark Complete" for a meter
task.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.budget_manager import Bill, ExpenseEntry, IncomeEntry, days_until_bill_due
from core.search_manager import SearchResult
from gui.add_edit_bill_dialog import AddEditBillDialog
from gui.add_edit_expense_dialog import AddEditExpenseDialog
from gui.add_edit_income_dialog import AddEditIncomeDialog
from gui.mark_bill_paid_dialog import MarkBillPaidDialog
from modules.module_base import ModuleBase


def format_bill_row(bill: Bill, today: date) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_budget_module.py)."""
    remaining = days_until_bill_due(bill, today)
    if remaining is None:
        status = "[PAID]"
    elif remaining < 0:
        status = f"[OVERDUE {-remaining}d]"
    elif remaining == 0:
        status = "[DUE TODAY]"
    else:
        status = f"[DUE IN {remaining}d]"
    return f"{status}  {bill.name}   ${bill.amount:.2f}  [{bill.category}]"


def format_income_row(entry: IncomeEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description_part = f"  {entry.description}" if entry.description else ""
    return f"{entry.date}   ${entry.amount:.2f}  [{entry.category}]{description_part}"


def format_expense_row(entry: ExpenseEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description_part = f"  {entry.description}" if entry.description else ""
    return f"{entry.date}   ${entry.amount:.2f}  [{entry.category}]{description_part}"


class BudgetModule(ModuleBase):
    module_id = "budget"
    display_name = "Budget"
    description = "Household bills, income, expenses, and tax-relevant totals."
    icon = "\U0001F4B0"  # money bag

    def __init__(self, context) -> None:
        super().__init__(context)
        self._bill_filter_edit: Optional[QLineEdit] = None
        self._bill_list: Optional[QListWidget] = None
        self._income_list: Optional[QListWidget] = None
        self._expense_list: Optional[QListWidget] = None
        self._summary_range_label: Optional[QLabel] = None
        self._summary_income_label: Optional[QLabel] = None
        self._summary_expenses_label: Optional[QLabel] = None
        self._summary_net_label: Optional[QLabel] = None
        self._summary_tax_income_label: Optional[QLabel] = None
        self._summary_tax_expenses_label: Optional[QLabel] = None
        self._summary_start_date: Optional[str] = None
        self._summary_end_date: Optional[str] = None

    def on_load(self) -> None:
        super().on_load()
        self.context.search.register_provider("budget", self._search)

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
        tabs.addTab(self._build_bills_tab(), "Bills")
        tabs.addTab(self._build_income_tab(), "Income")
        tabs.addTab(self._build_expenses_tab(), "Expenses")
        tabs.addTab(self._build_summary_tab(), "Summary")
        layout.addWidget(tabs, stretch=1)

        return widget

    # ------------------------------------------------------------------
    # Bills tab
    # ------------------------------------------------------------------

    def _build_bills_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._bill_filter_edit = QLineEdit()
        self._bill_filter_edit.setPlaceholderText("Filter by name or category…")
        self._bill_filter_edit.textChanged.connect(lambda _text: self._refresh_bill_list())
        layout.addWidget(self._bill_filter_edit)

        self._bill_list = QListWidget()
        layout.addWidget(self._bill_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Bill")
        add_button.clicked.connect(self._on_add_bill)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_bill)
        button_row.addWidget(edit_button)

        paid_button = QPushButton("Mark Paid")
        paid_button.clicked.connect(self._on_mark_bill_paid)
        button_row.addWidget(paid_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_bill)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_bill_list()
        return tab

    def _refresh_bill_list(self) -> None:
        query = self._bill_filter_edit.text().strip().lower()
        today = date.today()
        bills = self.context.budget.all_bills()

        self._bill_list.clear()
        for bill in bills:
            row_text = format_bill_row(bill, today)
            if query and query not in bill.name.lower() and query not in bill.category.lower():
                continue
            item = QListWidgetItem(row_text)
            item.setData(Qt.ItemDataRole.UserRole, bill.bill_id)
            self._bill_list.addItem(item)

    def _selected_bill_id(self) -> Optional[str]:
        item = self._bill_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_bill(self) -> None:
        dialog = AddEditBillDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_bill(
            name=dialog.entered_name,
            amount=dialog.entered_amount,
            due_date=dialog.entered_due_date,
            category=dialog.entered_category,
            recurrence=dialog.entered_recurrence,
            tax_relevant=dialog.entered_tax_relevant,
            notes=dialog.entered_notes,
        )
        self._refresh_bill_list()

    def _on_edit_bill(self) -> None:
        bill_id = self._selected_bill_id()
        if bill_id is None:
            QMessageBox.information(None, "No Bill Selected", "Select a bill to edit.")
            return

        bill = self.context.budget.get_bill(bill_id)
        dialog = AddEditBillDialog(bill=bill)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_bill(
            bill_id,
            name=dialog.entered_name,
            amount=dialog.entered_amount,
            due_date=dialog.entered_due_date,
            category=dialog.entered_category,
            recurrence=dialog.entered_recurrence,
            tax_relevant=dialog.entered_tax_relevant,
            notes=dialog.entered_notes,
        )
        self._refresh_bill_list()

    def _on_mark_bill_paid(self) -> None:
        bill_id = self._selected_bill_id()
        if bill_id is None:
            QMessageBox.information(None, "No Bill Selected", "Select a bill to mark paid.")
            return

        bill = self.context.budget.get_bill(bill_id)
        dialog = MarkBillPaidDialog(default_amount=bill.amount)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.mark_bill_paid(bill_id, paid_date=dialog.entered_paid_date, amount=dialog.entered_amount)
        self._refresh_bill_list()
        self._refresh_expense_list()

    def _on_delete_bill(self) -> None:
        bill_id = self._selected_bill_id()
        if bill_id is None:
            QMessageBox.information(None, "No Bill Selected", "Select a bill to delete.")
            return

        bill = self.context.budget.get_bill(bill_id)
        confirm = QMessageBox.question(
            None,
            "Delete Bill",
            f"Delete '{bill.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.budget.delete_bill(bill_id)
        self._refresh_bill_list()

    # ------------------------------------------------------------------
    # Income tab
    # ------------------------------------------------------------------

    def _build_income_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._income_list = QListWidget()
        layout.addWidget(self._income_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Income")
        add_button.clicked.connect(self._on_add_income)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_income)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_income)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_income_list()
        return tab

    def _refresh_income_list(self) -> None:
        self._income_list.clear()
        for entry in self.context.budget.all_income():
            item = QListWidgetItem(format_income_row(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            self._income_list.addItem(item)

    def _selected_income_id(self) -> Optional[str]:
        item = self._income_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_income(self) -> None:
        dialog = AddEditIncomeDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_income(
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            tax_relevant=dialog.entered_tax_relevant,
            notes=dialog.entered_notes,
        )
        self._refresh_income_list()

    def _on_edit_income(self) -> None:
        entry_id = self._selected_income_id()
        if entry_id is None:
            QMessageBox.information(None, "No Income Selected", "Select an income entry to edit.")
            return

        entry = self.context.budget.get_income(entry_id)
        dialog = AddEditIncomeDialog(entry=entry)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_income(
            entry_id,
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            tax_relevant=dialog.entered_tax_relevant,
            notes=dialog.entered_notes,
        )
        self._refresh_income_list()

    def _on_delete_income(self) -> None:
        entry_id = self._selected_income_id()
        if entry_id is None:
            QMessageBox.information(None, "No Income Selected", "Select an income entry to delete.")
            return

        confirm = QMessageBox.question(
            None,
            "Delete Income Entry",
            "Delete this income entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.budget.delete_income(entry_id)
        self._refresh_income_list()

    # ------------------------------------------------------------------
    # Expenses tab
    # ------------------------------------------------------------------

    def _build_expenses_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._expense_list = QListWidget()
        layout.addWidget(self._expense_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Expense")
        add_button.clicked.connect(self._on_add_expense)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_expense)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_expense)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_expense_list()
        return tab

    def _refresh_expense_list(self) -> None:
        self._expense_list.clear()
        for entry in self.context.budget.all_expenses():
            item = QListWidgetItem(format_expense_row(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            self._expense_list.addItem(item)

    def _selected_expense_id(self) -> Optional[str]:
        item = self._expense_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_expense(self) -> None:
        dialog = AddEditExpenseDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_expense(
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            tax_relevant=dialog.entered_tax_relevant,
            notes=dialog.entered_notes,
        )
        self._refresh_expense_list()

    def _on_edit_expense(self) -> None:
        entry_id = self._selected_expense_id()
        if entry_id is None:
            QMessageBox.information(None, "No Expense Selected", "Select an expense entry to edit.")
            return

        entry = self.context.budget.get_expense(entry_id)
        dialog = AddEditExpenseDialog(entry=entry)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_expense(
            entry_id,
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            tax_relevant=dialog.entered_tax_relevant,
            notes=dialog.entered_notes,
        )
        self._refresh_expense_list()

    def _on_delete_expense(self) -> None:
        entry_id = self._selected_expense_id()
        if entry_id is None:
            QMessageBox.information(None, "No Expense Selected", "Select an expense entry to delete.")
            return

        confirm = QMessageBox.question(
            None,
            "Delete Expense Entry",
            "Delete this expense entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.budget.delete_expense(entry_id)
        self._refresh_expense_list()

    # ------------------------------------------------------------------
    # Summary tab — computed on demand from core/budget_manager.py's
    # reporting functions, never a separately-stored figure that could
    # drift (same stance core.ledger_manager.LedgerManager.net_profit()
    # already takes).
    # ------------------------------------------------------------------

    def _build_summary_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._summary_range_label = QLabel("")
        self._summary_range_label.setObjectName("SubtitleLabel")
        layout.addWidget(self._summary_range_label)

        range_row = QHBoxLayout()
        month_button = QPushButton("This Month")
        month_button.clicked.connect(self._on_summary_this_month)
        range_row.addWidget(month_button)

        year_button = QPushButton("This Year")
        year_button.clicked.connect(self._on_summary_this_year)
        range_row.addWidget(year_button)

        all_time_button = QPushButton("All Time")
        all_time_button.clicked.connect(self._on_summary_all_time)
        range_row.addWidget(all_time_button)
        layout.addLayout(range_row)

        self._summary_income_label = QLabel()
        layout.addWidget(self._summary_income_label)
        self._summary_expenses_label = QLabel()
        layout.addWidget(self._summary_expenses_label)
        self._summary_net_label = QLabel()
        layout.addWidget(self._summary_net_label)
        self._summary_tax_income_label = QLabel()
        layout.addWidget(self._summary_tax_income_label)
        self._summary_tax_expenses_label = QLabel()
        layout.addWidget(self._summary_tax_expenses_label)

        layout.addStretch(1)

        self._on_summary_this_month()
        return tab

    def _on_summary_this_month(self) -> None:
        today = date.today()
        start = today.replace(day=1).isoformat()
        self._set_summary_range("This Month", start, None)

    def _on_summary_this_year(self) -> None:
        today = date.today()
        start = today.replace(month=1, day=1).isoformat()
        self._set_summary_range("This Year", start, None)

    def _on_summary_all_time(self) -> None:
        self._set_summary_range("All Time", None, None)

    def _set_summary_range(self, label: str, start_date: Optional[str], end_date: Optional[str]) -> None:
        self._summary_start_date = start_date
        self._summary_end_date = end_date
        self._summary_range_label.setText(label)
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        start, end = self._summary_start_date, self._summary_end_date
        budget = self.context.budget
        income = budget.total_income(start, end)
        expenses = budget.total_expenses(start, end)
        tax_income = budget.total_income(start, end, tax_relevant_only=True)
        tax_expenses = budget.total_expenses(start, end, tax_relevant_only=True)

        self._summary_income_label.setText(f"Income: ${income:,.2f}")
        self._summary_expenses_label.setText(f"Expenses: ${expenses:,.2f}")
        self._summary_net_label.setText(f"Net: ${income - expenses:,.2f}")
        self._summary_tax_income_label.setText(f"Tax-relevant income: ${tax_income:,.2f}")
        self._summary_tax_expenses_label.setText(f"Tax-relevant (deductible) expenses: ${tax_expenses:,.2f}")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search(self, query: str) -> list[SearchResult]:
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        results = []
        for bill in self.context.budget.all_bills():
            if query_lower in bill.name.lower() or query_lower in bill.category.lower():
                results.append(SearchResult(
                    title=bill.name,
                    description=f"Bill — ${bill.amount:.2f} [{bill.category}]",
                    source=self.display_name,
                    action_type="open_module",
                    action_target=self.module_id,
                ))
        return results
