"""
modules.budget.module
========================

Budget: household bills, income, expenses, and expected/recurring
income. Six tabs (Bills, Income Sources, Income, Expenses, Summary,
Bank Sync) — same `QTabWidget` multi-feature-in-one-module shape as
modules/maintenance/module.py and modules/workshop/module.py, since
these are closely-related views over one connected data set rather
than separate top-level modules.

All persistence/recurrence/reporting logic lives in
core/budget_manager.py (self.context.budget) — this module is the
Qt-facing wrapper around it, same split as every other data-backed
module here.

The Bills tab's "Mark Paid" action is the real integration point: it
opens gui/mark_bill_paid_dialog.py, then calls
self.context.budget.mark_bill_paid(...), which both records a real
Expense entry AND advances the bill's own due date — one click, two
real effects, same shape as Maintenance's "Mark Complete" for a meter
task. The Income Sources tab's "Mark Received" action mirrors this
exactly via mark_income_received().

The Summary tab's Budget Targets section is the GUI half of the
proactive nudges feature (core/budget_nudges.py) — it's the same
planned-vs-actual comparison the daily nudge checks, made visible and
editable on demand rather than only surfaced as a notification.

The Bank Sync tab is the GUI half of core/plaid_manager.py — see that
module's own docstring for the full "why Hosted Link + browser +
polling, why an encrypted passphrase-locked vault" reasoning. "Connect
a Bank" is deliberately never exposed as an Assistant action: a real
credential/consent flow needs the user physically watching their own
browser, not something a stray chat phrase could trigger.
"""

from __future__ import annotations

import webbrowser
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
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

from core.budget_manager import (
    Bill,
    EXPENSE_CATEGORIES,
    ExpenseEntry,
    IncomeEntry,
    IncomeSource,
    days_until_bill_due,
    days_until_income_due,
)
from core.search_manager import SearchResult
from core.secrets_manager import SecretsError
from gui.add_edit_bill_dialog import AddEditBillDialog
from gui.add_edit_expense_dialog import AddEditExpenseDialog
from gui.add_edit_income_dialog import AddEditIncomeDialog
from gui.add_edit_income_source_dialog import AddEditIncomeSourceDialog
from gui.mark_bill_paid_dialog import MarkBillPaidDialog
from gui.mark_income_received_dialog import MarkIncomeReceivedDialog
from gui.password_dialog import PasswordPromptDialog
from gui.plaid_connect_progress_dialog import PlaidConnectProgressDialog
from gui.plaid_setup_dialog import PlaidSetupDialog
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


def format_income_source_row(source: IncomeSource, today: date) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_budget_module.py)."""
    remaining = days_until_income_due(source, today)
    if remaining is None:
        status = "[NO SCHEDULE]"
    elif remaining < 0:
        status = f"[OVERDUE {-remaining}d]"
    elif remaining == 0:
        status = "[DUE TODAY]"
    else:
        status = f"[DUE IN {remaining}d]"
    return f"{status}  {source.name}   ${source.expected_amount:.2f}  [{source.category}]"


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
        self._income_source_filter_edit: Optional[QLineEdit] = None
        self._income_source_list: Optional[QListWidget] = None
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
        self._budget_target_spins: dict[str, QDoubleSpinBox] = {}
        self._budget_target_actual_labels: dict[str, QLabel] = {}

        self._plaid_status_label: Optional[QLabel] = None
        self._plaid_accounts_list: Optional[QListWidget] = None
        self._plaid_setup_button: Optional[QPushButton] = None
        self._plaid_unlock_button: Optional[QPushButton] = None
        self._plaid_connect_button: Optional[QPushButton] = None
        self._plaid_sync_button: Optional[QPushButton] = None

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
        tabs.addTab(self._build_income_sources_tab(), "Income Sources")
        tabs.addTab(self._build_income_tab(), "Income")
        tabs.addTab(self._build_expenses_tab(), "Expenses")
        tabs.addTab(self._build_summary_tab(), "Summary")
        tabs.addTab(self._build_bank_sync_tab(), "Bank Sync")
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
    # Income Sources tab — expected/recurring income (paychecks, rental
    # income), same shape as the Bills tab above. Distinct from the
    # Income tab below, which is real received income entries.
    # ------------------------------------------------------------------

    def _build_income_sources_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._income_source_filter_edit = QLineEdit()
        self._income_source_filter_edit.setPlaceholderText("Filter by name or category…")
        self._income_source_filter_edit.textChanged.connect(lambda _text: self._refresh_income_source_list())
        layout.addWidget(self._income_source_filter_edit)

        self._income_source_list = QListWidget()
        layout.addWidget(self._income_source_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Income Source")
        add_button.clicked.connect(self._on_add_income_source)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_income_source)
        button_row.addWidget(edit_button)

        received_button = QPushButton("Mark Received")
        received_button.clicked.connect(self._on_mark_income_received)
        button_row.addWidget(received_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_income_source)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_income_source_list()
        return tab

    def _refresh_income_source_list(self) -> None:
        query = self._income_source_filter_edit.text().strip().lower()
        today = date.today()
        sources = self.context.budget.all_income_sources()

        self._income_source_list.clear()
        for source in sources:
            if query and query not in source.name.lower() and query not in source.category.lower():
                continue
            row_text = format_income_source_row(source, today)
            item = QListWidgetItem(row_text)
            item.setData(Qt.ItemDataRole.UserRole, source.source_id)
            self._income_source_list.addItem(item)

    def _selected_income_source_id(self) -> Optional[str]:
        item = self._income_source_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_income_source(self) -> None:
        dialog = AddEditIncomeSourceDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_income_source(
            name=dialog.entered_name,
            expected_amount=dialog.entered_amount,
            next_date=dialog.entered_next_date,
            category=dialog.entered_category,
            recurrence=dialog.entered_recurrence,
            notes=dialog.entered_notes,
        )
        self._refresh_income_source_list()

    def _on_edit_income_source(self) -> None:
        source_id = self._selected_income_source_id()
        if source_id is None:
            QMessageBox.information(None, "No Income Source Selected", "Select an income source to edit.")
            return

        source = self.context.budget.get_income_source(source_id)
        dialog = AddEditIncomeSourceDialog(income_source=source)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_income_source(
            source_id,
            name=dialog.entered_name,
            expected_amount=dialog.entered_amount,
            next_date=dialog.entered_next_date,
            category=dialog.entered_category,
            recurrence=dialog.entered_recurrence,
            notes=dialog.entered_notes,
        )
        self._refresh_income_source_list()

    def _on_mark_income_received(self) -> None:
        source_id = self._selected_income_source_id()
        if source_id is None:
            QMessageBox.information(None, "No Income Source Selected", "Select an income source to mark received.")
            return

        source = self.context.budget.get_income_source(source_id)
        dialog = MarkIncomeReceivedDialog(default_amount=source.expected_amount)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.mark_income_received(
            source_id, received_date=dialog.entered_received_date, amount=dialog.entered_amount
        )
        self._refresh_income_source_list()
        self._refresh_income_list()

    def _on_delete_income_source(self) -> None:
        source_id = self._selected_income_source_id()
        if source_id is None:
            QMessageBox.information(None, "No Income Source Selected", "Select an income source to delete.")
            return

        source = self.context.budget.get_income_source(source_id)
        confirm = QMessageBox.question(
            None,
            "Delete Income Source",
            f"Delete '{source.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.budget.delete_income_source(source_id)
        self._refresh_income_source_list()

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

        layout.addWidget(self._build_budget_targets_group())
        layout.addStretch(1)

        self._on_summary_this_month()
        return tab

    def _build_budget_targets_group(self) -> QGroupBox:
        """One row per EXPENSE_CATEGORIES entry: an editable planned
        monthly amount alongside this month's actual spend, reusing
        total_expenses_by_category() for the "actual" side. Same
        planned-vs-actual comparison core/budget_nudges.py's daily
        check makes — this is the on-demand, editable view of it."""
        group = QGroupBox("Budget Targets (this month)")
        form = QFormLayout(group)

        targets_by_category = {t.category: t.monthly_amount for t in self.context.budget.all_budget_targets()}
        today = date.today()
        actual_by_category = self.context.budget.total_expenses_by_category(today.replace(day=1).isoformat(), None)

        self._budget_target_spins = {}
        self._budget_target_actual_labels = {}
        for category in EXPENSE_CATEGORIES:
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1_000_000.0)
            spin.setDecimals(2)
            spin.setValue(targets_by_category.get(category, 0.0))
            spin.editingFinished.connect(lambda cat=category: self._on_budget_target_changed(cat))
            self._budget_target_spins[category] = spin

            actual_label = QLabel(f"actual: ${actual_by_category.get(category, 0.0):,.2f}")
            actual_label.setObjectName("SubtitleLabel")
            self._budget_target_actual_labels[category] = actual_label

            row = QHBoxLayout()
            row.addWidget(spin)
            row.addWidget(actual_label)
            form.addRow(f"{category}:", row)

        return group

    def _on_budget_target_changed(self, category: str) -> None:
        amount = self._budget_target_spins[category].value()
        if amount <= 0.0:
            self.context.budget.delete_budget_target(category)
        else:
            self.context.budget.set_budget_target(category, amount)

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
    # Bank Sync tab — GUI half of core/plaid_manager.py, see that
    # module's docstring for the full design reasoning.
    # ------------------------------------------------------------------

    def _build_bank_sync_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        intro = QLabel(
            "Connect a real bank or brokerage account via Plaid to pull balances into MIA. "
            "This is a real third-party service — see Settings for the offline-first tradeoff this accepts."
        )
        intro.setWordWrap(True)
        intro.setObjectName("SubtitleLabel")
        layout.addWidget(intro)

        self._plaid_status_label = QLabel("")
        layout.addWidget(self._plaid_status_label)

        self._plaid_accounts_list = QListWidget()
        layout.addWidget(self._plaid_accounts_list, stretch=1)

        button_row = QHBoxLayout()
        self._plaid_setup_button = QPushButton("Set Up Plaid…")
        self._plaid_setup_button.clicked.connect(self._on_plaid_setup)
        button_row.addWidget(self._plaid_setup_button)

        self._plaid_unlock_button = QPushButton("Unlock…")
        self._plaid_unlock_button.clicked.connect(self._on_plaid_unlock)
        button_row.addWidget(self._plaid_unlock_button)

        self._plaid_connect_button = QPushButton("Connect a Bank…")
        self._plaid_connect_button.clicked.connect(self._on_plaid_connect)
        button_row.addWidget(self._plaid_connect_button)

        self._plaid_sync_button = QPushButton("Sync Now")
        self._plaid_sync_button.clicked.connect(self._on_plaid_sync)
        button_row.addWidget(self._plaid_sync_button)

        layout.addLayout(button_row)

        self._refresh_plaid_tab()
        return tab

    def _refresh_plaid_tab(self) -> None:
        plaid = self.context.plaid
        configured = plaid.is_configured()
        unlocked = plaid.is_unlocked()

        self._plaid_setup_button.setEnabled(not configured)
        self._plaid_unlock_button.setEnabled(configured and not unlocked)
        self._plaid_connect_button.setEnabled(unlocked)
        self._plaid_sync_button.setEnabled(unlocked)

        if not configured:
            self._plaid_status_label.setText("Not set up yet.")
        elif not unlocked:
            self._plaid_status_label.setText("Set up, locked — unlock to connect or sync.")
        else:
            count = len(plaid.connected_items())
            noun = "account" if count == 1 else "accounts"
            self._plaid_status_label.setText(f"Unlocked — {count} connected {noun}.")

        self._plaid_accounts_list.clear()
        if unlocked:
            for item in plaid.connected_items():
                self._plaid_accounts_list.addItem(f"{item.institution_name}  —  connected {item.connected_at}")
        else:
            self._plaid_accounts_list.addItem("Unlock to see connected accounts.")

    def _on_plaid_setup(self) -> None:
        dialog = PlaidSetupDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.plaid.setup(
            client_id=dialog.entered_client_id,
            secret=dialog.entered_secret,
            environment=dialog.entered_environment,
            passphrase=dialog.entered_passphrase,
        )
        QMessageBox.information(None, "Plaid Set Up", "Plaid is set up and unlocked for this session.")
        self._refresh_plaid_tab()

    def _on_plaid_unlock(self) -> None:
        dialog = PasswordPromptDialog("your Plaid vault", prompt="Enter the passphrase for")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self.context.plaid.unlock(dialog.entered_password)
        except SecretsError as exc:
            QMessageBox.warning(None, "Couldn't Unlock", str(exc))
            return
        self._refresh_plaid_tab()

    def _on_plaid_connect(self) -> None:
        try:
            link_token, hosted_link_url = self.context.plaid.create_hosted_link_session()
        except Exception as exc:  # noqa: BLE001 — surface any real Plaid API error to the user
            QMessageBox.warning(None, "Couldn't Start Connection", str(exc))
            return

        webbrowser.open(hosted_link_url)

        progress = PlaidConnectProgressDialog(self.context.plaid, link_token)
        if progress.exec() != QDialog.DialogCode.Accepted or not progress.entered_public_token:
            return

        try:
            self.context.plaid.finish_connection(progress.entered_public_token)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Finish Connecting", str(exc))
            return

        save_dialog = PasswordPromptDialog("your Plaid vault", prompt="Re-enter the passphrase for")
        if save_dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.context.plaid.save_current_vault(save_dialog.entered_password)
            except SecretsError as exc:
                QMessageBox.warning(None, "Couldn't Save", f"Bank connected for this session, but saving failed: {exc}")
        self._refresh_plaid_tab()

    def _on_plaid_sync(self) -> None:
        try:
            snapshots = self.context.plaid.sync()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Sync Failed", str(exc))
            return

        if not snapshots:
            QMessageBox.information(None, "Nothing to Sync", "No connected accounts to sync yet.")
            return
        QMessageBox.information(None, "Synced", f"Synced {len(snapshots)} connected account(s).")

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
