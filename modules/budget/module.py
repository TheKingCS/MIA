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

The Summary tab's "Export Business Report" button composes a real PDF
via core/business_report.py (pure HTML composition) + Qt's own
QTextDocument/QPrinter (no new dependency) — combines this tab's
household finance figures with the Real Estate portfolio (both are
plain sibling AppContext fields) into one document, reusing whichever
date range is currently selected here rather than a second picker.

The Bank Sync tab is the GUI half of core/plaid_manager.py — see that
module's own docstring for the full "why Hosted Link + browser +
polling, why an encrypted passphrase-locked vault" reasoning. "Connect
a Bank" is deliberately never exposed as an Assistant action: a real
credential/consent flow needs the user physically watching their own
browser, not something a stray chat phrase could trigger. "Add
Transaction Access…" is the same real browser-consent flow for an
already-connected account (Plaid's "update mode" Link) — same
reasoning, also never an Assistant action. Real bank transactions
imported this way land as genuine Income/Expense entries via
context.plaid.sync(), not a separate read-only list — they show up in
the Income/Expenses tabs, the Summary tab, proactive nudges, and the
Business Report exactly like a manually-entered one.
"""

from __future__ import annotations

import webbrowser
from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
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

from core.business_report import build_business_report_html
from core.budget_manager import (
    Bill,
    EXPENSE_CATEGORIES,
    ExpenseEntry,
    IncomeEntry,
    IncomeSource,
    days_until_bill_due,
    days_until_income_due,
)
from core.real_estate_manager import annual_depreciation, equity as property_equity
from core.search_manager import SearchResult
from core.secrets_manager import SecretsError
from gui.add_edit_bill_dialog import AddEditBillDialog
from gui.add_edit_expense_dialog import AddEditExpenseDialog
from gui.add_edit_income_dialog import AddEditIncomeDialog
from gui.add_edit_income_source_dialog import AddEditIncomeSourceDialog
from gui.manage_business_entities_dialog import ManageBusinessEntitiesDialog
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


def format_holding_row(holding: dict) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_budget_module.py). holding is one entry from a
    core.plaid_manager plaid_investments_* snapshot's "holdings" list."""
    name = holding.get("security_name") or "Unknown security"
    ticker = holding.get("ticker_symbol")
    label = f"{name} ({ticker})" if ticker else name
    quantity = holding.get("quantity")
    value = holding.get("institution_value")
    qty_part = f"{quantity:,.4g} sh  —  " if quantity is not None else ""
    value_part = f"${value:,.2f}" if value is not None else "value unknown"
    return f"{label}   {qty_part}{value_part}"


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
        self._summary_entity_combo: Optional[QComboBox] = None
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
        self._plaid_add_transactions_button: Optional[QPushButton] = None
        self._plaid_add_investments_button: Optional[QPushButton] = None
        self._plaid_sync_button: Optional[QPushButton] = None
        self._plaid_holdings_list: Optional[QListWidget] = None

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
        dialog = AddEditBillDialog(entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_bill(
            name=dialog.entered_name,
            amount=dialog.entered_amount,
            due_date=dialog.entered_due_date,
            category=dialog.entered_category,
            recurrence=dialog.entered_recurrence,
            tax_relevant=dialog.entered_tax_relevant,
            entity_id=dialog.entered_entity_id,
            notes=dialog.entered_notes,
        )
        self._refresh_bill_list()

    def _on_edit_bill(self) -> None:
        bill_id = self._selected_bill_id()
        if bill_id is None:
            QMessageBox.information(None, "No Bill Selected", "Select a bill to edit.")
            return

        bill = self.context.budget.get_bill(bill_id)
        dialog = AddEditBillDialog(bill=bill, entities=self.context.budget.all_business_entities())
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
            entity_id=dialog.entered_entity_id,
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
        dialog = AddEditIncomeSourceDialog(entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_income_source(
            name=dialog.entered_name,
            expected_amount=dialog.entered_amount,
            next_date=dialog.entered_next_date,
            category=dialog.entered_category,
            recurrence=dialog.entered_recurrence,
            entity_id=dialog.entered_entity_id,
            notes=dialog.entered_notes,
        )
        self._refresh_income_source_list()

    def _on_edit_income_source(self) -> None:
        source_id = self._selected_income_source_id()
        if source_id is None:
            QMessageBox.information(None, "No Income Source Selected", "Select an income source to edit.")
            return

        source = self.context.budget.get_income_source(source_id)
        dialog = AddEditIncomeSourceDialog(income_source=source, entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_income_source(
            source_id,
            name=dialog.entered_name,
            expected_amount=dialog.entered_amount,
            next_date=dialog.entered_next_date,
            category=dialog.entered_category,
            recurrence=dialog.entered_recurrence,
            entity_id=dialog.entered_entity_id,
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
        dialog = AddEditIncomeDialog(entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_income(
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            entity_id=dialog.entered_entity_id,
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
        dialog = AddEditIncomeDialog(entry=entry, entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_income(
            entry_id,
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            entity_id=dialog.entered_entity_id,
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
        dialog = AddEditExpenseDialog(entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_expense(
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            entity_id=dialog.entered_entity_id,
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
        dialog = AddEditExpenseDialog(entry=entry, entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_expense(
            entry_id,
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            entity_id=dialog.entered_entity_id,
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

        entity_row = QHBoxLayout()
        entity_row.addWidget(QLabel("Entity:"))
        self._summary_entity_combo = QComboBox()
        self._refresh_entity_combo()
        self._summary_entity_combo.currentIndexChanged.connect(lambda _idx: self._refresh_summary())
        self._summary_entity_combo.currentIndexChanged.connect(lambda _idx: self._refresh_budget_targets())
        entity_row.addWidget(self._summary_entity_combo, stretch=1)

        manage_entities_button = QPushButton("Manage Entities…")
        manage_entities_button.clicked.connect(self._on_manage_entities)
        entity_row.addWidget(manage_entities_button)
        layout.addLayout(entity_row)

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

        export_button = QPushButton("Export Business Report (PDF)…")
        export_button.clicked.connect(self._on_export_business_report)
        layout.addWidget(export_button)

        layout.addStretch(1)

        self._on_summary_this_month()
        return tab

    def _budget_target_entity_id(self) -> str:
        """Budget Targets are always edited for one specific entity
        context — "All Entities" (None) has no single sensible planned
        amount to show per category (more than one entity could have
        its own target for the same category name), so it collapses to
        the household/unassigned bucket, same as explicitly picking
        "(Unassigned)"."""
        return self._summary_entity_combo.currentData() or ""

    def _build_budget_targets_group(self) -> QGroupBox:
        """One row per EXPENSE_CATEGORIES entry: an editable planned
        monthly amount alongside this month's actual spend, reusing
        total_expenses_by_category() for the "actual" side. Same
        planned-vs-actual comparison core/budget_nudges.py's daily
        check makes — this is the on-demand, editable view of it.
        Scoped to whatever entity the Summary tab's own filter currently
        selects (see _budget_target_entity_id()) — refreshed in place
        by _refresh_budget_targets() rather than rebuilt, so the entity
        combo's change handler doesn't need to tear down/recreate this
        whole group."""
        self._budget_targets_group = QGroupBox()
        form = QFormLayout(self._budget_targets_group)

        self._budget_target_spins = {}
        self._budget_target_actual_labels = {}
        for category in EXPENSE_CATEGORIES:
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1_000_000.0)
            spin.setDecimals(2)
            spin.editingFinished.connect(lambda cat=category: self._on_budget_target_changed(cat))
            self._budget_target_spins[category] = spin

            actual_label = QLabel("")
            actual_label.setObjectName("SubtitleLabel")
            self._budget_target_actual_labels[category] = actual_label

            row = QHBoxLayout()
            row.addWidget(spin)
            row.addWidget(actual_label)
            form.addRow(f"{category}:", row)

        self._refresh_budget_targets()
        return self._budget_targets_group

    def _refresh_budget_targets(self) -> None:
        entity_id = self._budget_target_entity_id()
        title = "Budget Targets (this month)"
        if entity_id:
            entity = self.context.budget.get_business_entity(entity_id)
            if entity is not None:
                title += f" — {entity.name}"
        self._budget_targets_group.setTitle(title)

        targets_by_category = {
            t.category: t.monthly_amount for t in self.context.budget.all_budget_targets(entity_id=entity_id)
        }
        today = date.today()
        actual_by_category = self.context.budget.total_expenses_by_category(
            today.replace(day=1).isoformat(), None, entity_id=entity_id,
        )
        for category, spin in self._budget_target_spins.items():
            spin.blockSignals(True)
            spin.setValue(targets_by_category.get(category, 0.0))
            spin.blockSignals(False)
            self._budget_target_actual_labels[category].setText(f"actual: ${actual_by_category.get(category, 0.0):,.2f}")

    def _on_budget_target_changed(self, category: str) -> None:
        entity_id = self._budget_target_entity_id()
        amount = self._budget_target_spins[category].value()
        if amount <= 0.0:
            self.context.budget.delete_budget_target(category, entity_id=entity_id)
        else:
            self.context.budget.set_budget_target(category, amount, entity_id=entity_id)

    def _refresh_entity_combo(self) -> None:
        """Re-populates the Summary tab's entity filter — None ("All
        Entities") is the default/off state matching total_income()'s
        own entity_id=None contract; "" filters to unassigned entries."""
        current = self._summary_entity_combo.currentData() if self._summary_entity_combo.count() else None
        self._summary_entity_combo.blockSignals(True)
        self._summary_entity_combo.clear()
        self._summary_entity_combo.addItem("All Entities", None)
        self._summary_entity_combo.addItem("(Unassigned)", "")
        for ent in self.context.budget.all_business_entities():
            self._summary_entity_combo.addItem(ent.name, ent.entity_id)
        idx = self._summary_entity_combo.findData(current)
        self._summary_entity_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._summary_entity_combo.blockSignals(False)

    def _on_manage_entities(self) -> None:
        dialog = ManageBusinessEntitiesDialog(self.context)
        dialog.exec()
        self._refresh_entity_combo()

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
        entity_id = self._summary_entity_combo.currentData()
        budget = self.context.budget
        income = budget.total_income(start, end, entity_id=entity_id)
        expenses = budget.total_expenses(start, end, entity_id=entity_id)
        tax_income = budget.total_income(start, end, tax_relevant_only=True, entity_id=entity_id)
        tax_expenses = budget.total_expenses(start, end, tax_relevant_only=True, entity_id=entity_id)

        self._summary_income_label.setText(f"Income: ${income:,.2f}")
        self._summary_expenses_label.setText(f"Expenses: ${expenses:,.2f}")
        self._summary_net_label.setText(f"Net: ${income - expenses:,.2f}")
        self._summary_tax_income_label.setText(f"Tax-relevant income: ${tax_income:,.2f}")
        self._summary_tax_expenses_label.setText(f"Tax-relevant (deductible) expenses: ${tax_expenses:,.2f}")

    def _on_export_business_report(self) -> None:
        """Composes a real PDF from core.business_report.build_business_
        report_html() — fetches plain data from context.budget/
        context.real_estate here, keeping the composition function
        itself pure and Qt-free. Reuses the Summary tab's own already-
        selected range rather than a second, redundant date picker."""
        start, end = self._summary_start_date, self._summary_end_date
        range_label = self._summary_range_label.text()
        entity_id = self._summary_entity_combo.currentData()
        budget = self.context.budget
        real_estate = self.context.real_estate

        entity_label = None
        if entity_id is not None:
            entity_label = "(Unassigned)" if entity_id == "" else budget.get_business_entity(entity_id).name

        # Budget Targets vs. Actual only makes honest sense for "This
        # Month" — BudgetTarget.monthly_amount has no yearly-aggregation
        # concept (see its own docstring in core/budget_manager.py).
        # "All Entities" (entity_id is None) collapses to the household/
        # unassigned bucket, same as the Summary tab's own Budget
        # Targets section — an unfiltered mix could have more than one
        # target for the same category name.
        budget_targets = budget.all_budget_targets(entity_id=entity_id or "") if range_label == "This Month" else []

        properties = []
        for prop in real_estate.all_properties():
            if entity_id is not None and prop.entity_id != entity_id:
                continue
            properties.append({
                "name": prop.name,
                "type": prop.property_type,
                "current_value": prop.current_value,
                "mortgage_balance": prop.mortgage_balance,
                "equity": property_equity(prop),
                "noi": real_estate.net_operating_income(prop.property_id, start, end),
                "cap_rate": real_estate.cap_rate(prop.property_id, start, end),
                "annual_depreciation": annual_depreciation(prop),
            })

        html = build_business_report_html(
            range_label=range_label,
            start_date=start,
            end_date=end,
            income_total=budget.total_income(start, end, entity_id=entity_id),
            expenses_total=budget.total_expenses(start, end, entity_id=entity_id),
            tax_income_total=budget.total_income(start, end, tax_relevant_only=True, entity_id=entity_id),
            tax_expenses_total=budget.total_expenses(start, end, tax_relevant_only=True, entity_id=entity_id),
            income_by_category=budget.total_income_by_category(start, end, entity_id=entity_id),
            expenses_by_category=budget.total_expenses_by_category(start, end, entity_id=entity_id),
            budget_targets=budget_targets,
            # Matches budget_targets' own entity resolution above (not
            # the raw entity_id the other totals/breakdowns use) — the
            # Budget Targets vs. Actual comparison needs both sides
            # computed against the same filter to mean anything.
            actual_by_category=budget.total_expenses_by_category(start, end, entity_id=entity_id or ""),
            properties=properties,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            entity_label=entity_label,
        )

        suggested_name = f"Business_Report_{datetime.now():%Y-%m-%d}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(None, "Export Business Report", suggested_name, "PDF files (*.pdf)")
        if not file_path:
            return
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        try:
            document = QTextDocument()
            document.setHtml(html)

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
            printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
            document.print_(printer)
        except Exception as exc:  # noqa: BLE001 — surface any real rendering/write error to the user
            QMessageBox.warning(None, "Export Failed", f"Could not export the report: {exc}")
            return

        QMessageBox.information(None, "Business Report Exported", f"Saved to {file_path}")

    # ------------------------------------------------------------------
    # Bank Sync tab — GUI half of core/plaid_manager.py, see that
    # module's docstring for the full design reasoning.
    # ------------------------------------------------------------------

    def _build_bank_sync_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        intro = QLabel(
            "Connect a real bank or brokerage account via Plaid to pull balances into MIA. "
            "This is a real third-party service — see Settings for the offline-first tradeoff this accepts. "
            "Fidelity is supported, but on Plaid's free/Pay-as-you-go tier, seeing Fidelity holdings here "
            "requires filing a support ticket with Plaid requesting Investments access for your account first."
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

        self._plaid_add_transactions_button = QPushButton("Add Transaction Access…")
        self._plaid_add_transactions_button.clicked.connect(self._on_plaid_add_transactions)
        button_row.addWidget(self._plaid_add_transactions_button)

        self._plaid_add_investments_button = QPushButton("Add Investments Access…")
        self._plaid_add_investments_button.clicked.connect(self._on_plaid_add_investments)
        button_row.addWidget(self._plaid_add_investments_button)

        self._plaid_sync_button = QPushButton("Sync Now")
        self._plaid_sync_button.clicked.connect(self._on_plaid_sync)
        button_row.addWidget(self._plaid_sync_button)

        layout.addLayout(button_row)

        holdings_label = QLabel("Holdings:")
        holdings_label.setObjectName("SubtitleLabel")
        layout.addWidget(holdings_label)
        self._plaid_holdings_list = QListWidget()
        layout.addWidget(self._plaid_holdings_list, stretch=1)

        self._plaid_accounts_list.currentItemChanged.connect(lambda *_: self._refresh_plaid_tab())

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
        self._plaid_add_transactions_button.setEnabled(unlocked and self._selected_plaid_item_needs_upgrade())
        self._plaid_add_investments_button.setEnabled(unlocked and self._selected_plaid_item_needs_investments_upgrade())

        if not configured:
            self._plaid_status_label.setText("Not set up yet.")
        elif not unlocked:
            self._plaid_status_label.setText("Set up, locked — unlock to connect or sync.")
        else:
            count = len(plaid.connected_items())
            noun = "account" if count == 1 else "accounts"
            self._plaid_status_label.setText(f"Unlocked — {count} connected {noun}.")

        # Rebuilding the list below (clear() + re-add) would otherwise wipe
        # the current selection right back out on every call — including
        # the very currentItemChanged-triggered call a user's own click
        # causes — so the previously-selected item_id is captured first and
        # restored after repopulating, still under blockSignals to avoid a
        # second, redundant currentItemChanged firing from that restore.
        previously_selected_item_id = self._selected_plaid_item_id()
        self._plaid_accounts_list.blockSignals(True)
        self._plaid_accounts_list.clear()
        if unlocked:
            for item in plaid.connected_items():
                suffix_parts = []
                if item.transactions_enabled:
                    suffix_parts.append("transactions enabled")
                if item.investments_enabled:
                    suffix_parts.append("investments enabled")
                suffix = f"  ·  {', '.join(suffix_parts)}" if suffix_parts else ""
                list_item = QListWidgetItem(f"{item.institution_name}  —  connected {item.connected_at}{suffix}")
                list_item.setData(Qt.ItemDataRole.UserRole, item.item_id)
                self._plaid_accounts_list.addItem(list_item)
                if item.item_id == previously_selected_item_id:
                    self._plaid_accounts_list.setCurrentItem(list_item)
        else:
            self._plaid_accounts_list.addItem("Unlock to see connected accounts.")
        self._plaid_accounts_list.blockSignals(False)

        self._plaid_holdings_list.clear()
        item_id = self._selected_plaid_item_id()
        if item_id and self.context.finance is not None:
            snapshot = self.context.finance.latest_snapshot(f"plaid_investments_{item_id}")
            if snapshot is None:
                self._plaid_holdings_list.addItem("No holdings synced for this account yet.")
            else:
                for holding in snapshot.data.get("holdings", []):
                    self._plaid_holdings_list.addItem(format_holding_row(holding))
                total = snapshot.data.get("holdings_total_value")
                if total is not None:
                    self._plaid_holdings_list.addItem(f"Total holdings value: ${total:,.2f}")
        else:
            self._plaid_holdings_list.addItem("Select a connected account to see its holdings.")

    def _selected_plaid_item_id(self) -> Optional[str]:
        item = self._plaid_accounts_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _selected_plaid_item_needs_upgrade(self) -> bool:
        item_id = self._selected_plaid_item_id()
        if item_id is None or not self.context.plaid.is_unlocked():
            return False
        return any(i.item_id == item_id and not i.transactions_enabled for i in self.context.plaid.connected_items())

    def _selected_plaid_item_needs_investments_upgrade(self) -> bool:
        item_id = self._selected_plaid_item_id()
        if item_id is None or not self.context.plaid.is_unlocked():
            return False
        return any(i.item_id == item_id and not i.investments_enabled for i in self.context.plaid.connected_items())

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

    def _on_plaid_add_transactions(self) -> None:
        """Update-mode counterpart to _on_plaid_connect() — adds
        Transactions consent to an item that was connected before this
        feature existed, without a full disconnect/reconnect. Reuses
        PlaidConnectProgressDialog unchanged; it only depends on
        check_public_token_once(link_token), which works identically
        for an update-mode token."""
        item_id = self._selected_plaid_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Account Selected", "Select a connected account to add transaction access to.")
            return

        try:
            link_token, hosted_link_url = self.context.plaid.create_update_mode_session(item_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Start", str(exc))
            return

        webbrowser.open(hosted_link_url)

        progress = PlaidConnectProgressDialog(self.context.plaid, link_token)
        if progress.exec() != QDialog.DialogCode.Accepted or not progress.entered_public_token:
            return

        try:
            self.context.plaid.finish_transactions_upgrade(item_id, progress.entered_public_token)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Finish", str(exc))
            return

        save_dialog = PasswordPromptDialog("your Plaid vault", prompt="Re-enter the passphrase for")
        if save_dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.context.plaid.save_current_vault(save_dialog.entered_password)
            except SecretsError as exc:
                QMessageBox.warning(None, "Couldn't Save", f"Transaction access granted for this session, but saving failed: {exc}")
        self._refresh_plaid_tab()

    def _on_plaid_add_investments(self) -> None:
        """Update-mode counterpart to _on_plaid_connect() for
        Investments — same shape as _on_plaid_add_transactions() above."""
        item_id = self._selected_plaid_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Account Selected", "Select a connected account to add investments access to.")
            return

        try:
            link_token, hosted_link_url = self.context.plaid.create_investments_upgrade_session(item_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Start", str(exc))
            return

        webbrowser.open(hosted_link_url)

        progress = PlaidConnectProgressDialog(self.context.plaid, link_token)
        if progress.exec() != QDialog.DialogCode.Accepted or not progress.entered_public_token:
            return

        try:
            self.context.plaid.finish_investments_upgrade(item_id, progress.entered_public_token)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Finish", str(exc))
            return

        save_dialog = PasswordPromptDialog("your Plaid vault", prompt="Re-enter the passphrase for")
        if save_dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.context.plaid.save_current_vault(save_dialog.entered_password)
            except SecretsError as exc:
                QMessageBox.warning(None, "Couldn't Save", f"Investments access granted for this session, but saving failed: {exc}")
        self._refresh_plaid_tab()

    def _on_plaid_sync(self) -> None:
        passphrase = None
        if any(i.transactions_enabled for i in self.context.plaid.connected_items()):
            pw_dialog = PasswordPromptDialog("your Plaid vault", prompt="Re-enter the passphrase for")
            if pw_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            passphrase = pw_dialog.entered_password

        try:
            result = self.context.plaid.sync(passphrase=passphrase)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Sync Failed", str(exc))
            return

        if not result.snapshots:
            QMessageBox.information(None, "Nothing to Sync", "No connected accounts to sync yet.")
            return

        message = f"Synced {len(result.snapshots)} connected account(s)."
        if result.transactions_added or result.transactions_updated:
            message += f" Imported {result.transactions_added} new transaction(s)"
            if result.transactions_updated:
                message += f", updated {result.transactions_updated}"
            message += "."
        if result.investment_accounts_synced:
            message += f" Synced holdings for {result.investment_accounts_synced} investment account(s)."
        QMessageBox.information(None, "Synced", message)
        self._refresh_plaid_tab()

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
