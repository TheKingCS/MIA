"""
modules.budget.module
========================

Budget: household bills, income, expenses, expected/recurring income,
and debt payoff tracking. Eight tabs (Bills, Income Sources, Income,
Expenses, Debts, Summary, Trends, Bank Sync) — same `QTabWidget`
multi-feature-in-one-module shape as modules/maintenance/module.py and
modules/workshop/module.py, since these are closely-related views over
one connected data set rather than separate top-level modules.

The Debts tab is the GUI half of core/budget_manager.py's Debt/
rank_debts() (2026-09-27) — a strategy combo (Avalanche/Snowball/
Hybrid) drives which order debts are listed in, with each row's own
computed reason (highest current APR, or an expiring promo warning)
shown inline. "Record Payment" mirrors the Bills tab's "Mark Paid"
shape exactly: one click, two real effects (a real Expense entry + a
real balance reduction) via BudgetManager.record_debt_payment().

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

The Trends tab charts Income vs. Expenses for the last 12 calendar
months via QtCharts (QChart/QChartView/QBarSeries/QBarSet/
QBarCategoryAxis — the same native-charting precedent already
established in modules/lab/module.py, extended here to a grouped bar
chart with real month labels instead of a bare index-based line). Each
month bucket is computed on demand from BudgetManager.total_income()/
total_expenses() — no new historical-snapshot storage, since real
Income/Expense entries already carry real dates.

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

import calendar
import webbrowser
from datetime import date, datetime
from typing import Optional

from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import QColor, QPageLayout, QPageSize, QPainter, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.business_report import build_business_report_html, build_consolidated_business_report_html
from core.homestead_costs import BuildCost, ToolCost, all_build_costs, all_tool_costs, record_tool_purchase
from core.business_tagging import auto_tag_new, pending_review
from core.business_use import build_worksheet, build_worksheet_html, equipment_report_rows, set_mileage_rate
from core.budget_manager import (
    Bill,
    DEBT_PAYOFF_STRATEGIES,
    Debt,
    DebtPriority,
    EXPENSE_CATEGORIES,
    ExpenseEntry,
    IncomeEntry,
    IncomeSource,
    days_until_bill_due,
    days_until_income_due,
    effective_apr,
)
from core.real_estate_manager import (
    SCHEDULE_E_ELIGIBLE_PROPERTY_TYPES,
    annual_depreciation,
    equity as property_equity,
    has_loan_terms,
    interest_paid_in_range,
)
from core.search_manager import SearchResult
from core.secrets_manager import SecretsError
from gui.add_edit_bill_dialog import AddEditBillDialog
from gui.add_edit_debt_dialog import AddEditDebtDialog
from gui.add_edit_expense_dialog import AddEditExpenseDialog
from gui.add_edit_income_dialog import AddEditIncomeDialog
from gui.add_edit_income_source_dialog import AddEditIncomeSourceDialog
from gui.list_widget_helpers import add_empty_state_item, selected_item_data
from gui.manage_business_entities_dialog import ManageBusinessEntitiesDialog
from gui.mark_bill_paid_dialog import MarkBillPaidDialog
from gui.mark_income_received_dialog import MarkIncomeReceivedDialog
from gui.record_debt_payment_dialog import RecordDebtPaymentDialog
from gui.reset_plaid_dialog import ResetPlaidDialog
from gui.password_dialog import PasswordPromptDialog
from gui.plaid_connect_progress_dialog import PlaidConnectProgressDialog
from gui.plaid_setup_dialog import PlaidSetupDialog
from modules.module_base import ModuleBase
from core.region import money


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
    return f"{status}  {bill.name}   {money(bill.amount, '.2f')}  [{bill.category}]"


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
    return f"{status}  {source.name}   {money(source.expected_amount, '.2f')}  [{source.category}]"


def format_income_row(entry: IncomeEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description_part = f"  {entry.description}" if entry.description else ""
    return f"{entry.date}   {money(entry.amount, '.2f')}  [{entry.category}]{description_part}"


def format_expense_row(entry: ExpenseEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description_part = f"  {entry.description}" if entry.description else ""
    return f"{entry.date}   {money(entry.amount, '.2f')}  [{entry.category}]{description_part}"


def format_debt_row(debt: Debt, today: date, priority: Optional[DebtPriority] = None) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_budget_module.py). `priority` is this debt's own entry
    from core.budget_manager.rank_debts() for the currently-selected
    strategy, when one was computed — carries the real "why this rank"
    reason (a plain APR comparison, or a soon-to-expire promo warning)
    straight into the row rather than requiring a second lookup."""
    rate = effective_apr(debt, today)
    rank_part = f"#{priority.rank}  " if priority is not None else ""
    synced_part = "  (bank-synced)" if debt.plaid_account_id else ""
    row = f"{rank_part}{debt.name}   {money(debt.balance, ',.2f')} @ {rate:.2f}% APR  [{debt.debt_type}]{synced_part}"
    if priority is not None:
        row += f"  — {priority.reason}"
    return row


def format_build_row(cost: BuildCost) -> str:
    """Pure formatting logic — Builds & Tools tab (Finance #2)."""
    text = f"{cost.name}  —  {money(cost.spent, ',.2f')} spent"
    if cost.budget > 0:
        if cost.remaining >= 0:
            text += f" of {money(cost.budget, ',.2f')} ({cost.percent_used:g}%), {money(cost.remaining, ',.2f')} left"
        else:
            text += f" of {money(cost.budget, ',.2f')}, {money(-cost.remaining, ',.2f')} OVER"
    return text + f"   [{cost.status}]"


def format_tool_row(cost: ToolCost) -> str:
    """Pure formatting logic — Builds & Tools tab (Finance #2)."""
    text = f"{cost.name}  —  {money(cost.total, ',.2f')} total ({money(cost.purchase_price, ',.2f')} to buy + {money(cost.upkeep, ',.2f')} since)"
    if cost.cost_per_hour is not None:
        text += f", {money(cost.cost_per_hour, ',.2f')}/hr over {cost.hours:g} hrs"
    return text


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
    value_part = f"{money(value, ',.2f')}" if value is not None else "value unknown"
    return f"{label}   {qty_part}{value_part}"


def month_buckets(today: date, count: int = 12) -> list[tuple[str, str, str]]:
    """Pure logic — testable without Qt (see tests/test_budget_module.py).
    Last `count` calendar months ending at today's month, oldest first —
    e.g. [("Oct 2025", "2025-10-01", "2025-10-31"), ..., ("Sep 2026",
    "2026-09-01", "2026-09-30")] for today=2026-09-09. Each (start, end)
    pair is ready to pass straight into BudgetManager.total_income()/
    total_expenses()."""
    buckets = []
    year, month = today.year, today.month
    for _ in range(count):
        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)
        buckets.append((start.strftime("%b %Y"), start.isoformat(), end.isoformat()))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    buckets.reverse()
    return buckets


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
        self._debt_list: Optional[QListWidget] = None
        self._debt_strategy_combo: Optional[QComboBox] = None
        self._debt_tab_summary_label: Optional[QLabel] = None
        self._summary_range_label: Optional[QLabel] = None
        self._summary_entity_combo: Optional[QComboBox] = None
        self._summary_income_label: Optional[QLabel] = None
        self._summary_expenses_label: Optional[QLabel] = None
        self._summary_net_label: Optional[QLabel] = None
        self._summary_tax_income_label: Optional[QLabel] = None
        self._summary_tax_expenses_label: Optional[QLabel] = None
        self._summary_debt_label: Optional[QLabel] = None
        self._summary_start_date: Optional[str] = None
        self._summary_end_date: Optional[str] = None
        self._budget_target_spins: dict[str, QDoubleSpinBox] = {}
        self._budget_target_actual_labels: dict[str, QLabel] = {}

        self._trends_entity_combo: Optional[QComboBox] = None
        self._trends_chart_view: Optional[QChartView] = None
        self._trends_net_label: Optional[QLabel] = None

        self._plaid_status_label: Optional[QLabel] = None
        self._plaid_accounts_list: Optional[QListWidget] = None
        self._plaid_setup_button: Optional[QPushButton] = None
        self._plaid_unlock_button: Optional[QPushButton] = None
        self._plaid_connect_button: Optional[QPushButton] = None
        self._plaid_add_transactions_button: Optional[QPushButton] = None
        self._plaid_add_investments_button: Optional[QPushButton] = None
        self._plaid_add_liabilities_button: Optional[QPushButton] = None
        self._plaid_disconnect_button: Optional[QPushButton] = None
        self._plaid_reset_button: Optional[QPushButton] = None
        self._plaid_sync_button: Optional[QPushButton] = None
        self._plaid_holdings_list: Optional[QListWidget] = None

    def on_load(self) -> None:
        super().on_load()
        self.context.search.register_provider("budget", self._search)

    def refresh(self) -> None:
        """Re-read every list (ModuleBase.refresh: records changed elsewhere, e.g. by voice)."""
        self._refresh_bill_list()
        self._refresh_expense_list()
        self._refresh_income_list()
        self._refresh_income_source_list()
        self._refresh_debt_list()
        self._refresh_budget_targets()
        self._refresh_summary()
        self._refresh_homestead()

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
        tabs.addTab(self._build_debts_tab(), "Debts")
        tabs.addTab(self._build_homestead_tab(), "Builds & Tools")
        tabs.addTab(self._build_summary_tab(), "Summary")
        tabs.addTab(self._build_trends_tab(), "Trends")
        tabs.addTab(self._build_bank_sync_tab(), "Bank Sync")
        # 2026-09-10: Bills/Income Sources/Income/Expenses' own add/
        # edit/delete/mark-paid/mark-received handlers only ever
        # refresh their own tab's list — Summary/Trends/Budget Targets
        # would otherwise show stale figures (even $0/an empty chart)
        # until the user happened to re-click a Summary range button
        # or change the entity filter themselves. All three refreshes
        # are cheap in-memory recomputations over already-loaded data,
        # so redoing them on every tab switch (regardless of which tab)
        # is simpler and safer than tracking which tab needs it.
        tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(tabs, stretch=1)

        return widget

    def _on_tab_changed(self, index: int) -> None:
        self._refresh_summary()
        self._refresh_budget_targets()
        self._refresh_trends_chart()
        self._refresh_debt_list()
        self._refresh_homestead()

    # ------------------------------------------------------------------
    # Builds & Tools tab (Finance #2, core/homestead_costs.py)
    # ------------------------------------------------------------------

    def _expense_link_choices(self) -> dict:
        """The build and tool pickers for the expense dialog."""
        return {
            "projects": self.context.projects.all_projects() if self.context.projects is not None else [],
            "assets": self.context.maintenance.all_assets() if self.context.maintenance is not None else [],
        }

    def _build_homestead_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        hint = QLabel(
            "What your builds and tools really cost. Tag an expense with its build or tool (Expenses → Add/Edit), "
            "or tell MIA: \"I spent $240 on lumber for the greenhouse\", \"I bought a chainsaw for $329\"."
        )
        hint.setObjectName("SubtitleLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(QLabel("Builds"))
        self._builds_list = QListWidget()
        layout.addWidget(self._builds_list, stretch=1)
        build_buttons = QHBoxLayout()
        budget_button = QPushButton("Set Build Budget…")
        budget_button.clicked.connect(self._on_set_build_budget)
        build_buttons.addWidget(budget_button)
        build_buttons.addStretch(1)
        layout.addLayout(build_buttons)

        layout.addWidget(QLabel("Tools & equipment"))
        self._tools_list = QListWidget()
        layout.addWidget(self._tools_list, stretch=1)
        tool_buttons = QHBoxLayout()
        purchase_button = QPushButton("Record Tool Purchase…")
        purchase_button.clicked.connect(self._on_record_tool_purchase)
        tool_buttons.addWidget(purchase_button)
        # Finance #3 (core/business_use.py): business use of equipment.
        use_button = QPushButton("Log Business Use…")
        use_button.clicked.connect(self._on_log_business_use)
        tool_buttons.addWidget(use_button)
        worksheet_button = QPushButton("Business Use Worksheet…")
        worksheet_button.clicked.connect(self._on_business_use_worksheet)
        tool_buttons.addWidget(worksheet_button)
        tool_buttons.addStretch(1)
        layout.addLayout(tool_buttons)

        self._refresh_homestead()
        return tab

    def _refresh_homestead(self) -> None:
        if not hasattr(self, "_builds_list"):
            return
        self._builds_list.clear()
        self._tools_list.clear()
        if self.context.projects is not None:
            builds = all_build_costs(self.context)
            for cost in builds:
                self._builds_list.addItem(format_build_row(cost))
            if not builds:
                self._builds_list.addItem("No build costs yet.")
        if self.context.maintenance is not None:
            tools = all_tool_costs(self.context)
            for cost in tools:
                self._tools_list.addItem(format_tool_row(cost))
            if not tools:
                self._tools_list.addItem("No tool costs yet.")

    def _on_set_build_budget(self) -> None:
        projects = self.context.projects.all_projects() if self.context.projects is not None else []
        if not projects:
            QMessageBox.information(None, "No Builds", "Add a build first (Toolbox → Projects), or tell MIA about one.")
            return
        names = [p.name for p in projects]
        name, ok = QInputDialog.getItem(None, "Set Build Budget", "Build:", names, 0, False)
        if not ok:
            return
        project = projects[names.index(name)]
        amount, ok = QInputDialog.getDouble(None, "Set Build Budget", f"Budget for {name} ($):", project.budget, 0, 10_000_000, 2)
        if ok:
            self.context.projects.update_project(project.project_id, budget=amount)
            self._refresh_homestead()

    def _pick_tool(self, title: str):
        assets = self.context.maintenance.all_assets() if self.context.maintenance is not None else []
        if not assets:
            QMessageBox.information(None, title, "Add the equipment in Maintenance first.")
            return None
        names = [a.name for a in assets]
        name, ok = QInputDialog.getItem(None, title, "Tool or equipment:", names, 0, False)
        return assets[names.index(name)] if ok else None

    def _on_log_business_use(self) -> None:
        if self.context.business_use is None:
            return
        asset = self._pick_tool("Log Business Use")
        if asset is None:
            return
        # Vehicles are measured in miles (core/business_use.py), everything else in hours.
        in_miles = asset.category == "Vehicle"
        unit = "miles" if in_miles else "hours"
        amount, ok = QInputDialog.getDouble(None, "Log Business Use", f"Business {unit} on the {asset.name}:", 1, 0.1, 100_000, 1)
        if not ok:
            return
        hours, miles = (0.0, amount) if in_miles else (amount, 0.0)
        client, ok = QInputDialog.getText(None, "Log Business Use", "Who or what was it for? (e.g. 'Johnson lawn', 'Maple duplex')")
        if not ok:
            return
        entity_id = ""
        entities = self.context.budget.all_business_entities()
        if entities:
            names = ["(No specific business)"] + [e.name for e in entities]
            choice, ok = QInputDialog.getItem(None, "Log Business Use", "Which business?", names, 0, False)
            if ok and choice != names[0]:
                entity_id = entities[names.index(choice) - 1].entity_id
        self.context.business_use.log_use(asset.asset_id, hours, client=client.strip(), entity_id=entity_id, miles=miles)
        QMessageBox.information(None, "Log Business Use", f"Logged {amount:g} business {unit} on the {asset.name}.")

    def _on_business_use_worksheet(self) -> None:
        if self.context.business_use is None:
            return
        asset = self._pick_tool("Business Use Worksheet")
        if asset is None:
            return
        this_year = date.today().year
        year, ok = QInputDialog.getInt(None, "Business Use Worksheet", "Tax year:", this_year, 2000, this_year + 1)
        if not ok:
            return
        sheet = build_worksheet(self.context, asset, year)
        state = {"html": build_worksheet_html(sheet, datetime.now().strftime("%Y-%m-%d %H:%M"))}
        dialog = QDialog()
        dialog.setWindowTitle(f"Business Use: {asset.name}, {year}")
        dialog.resize(720, 640)
        dialog_layout = QVBoxLayout(dialog)
        viewer = QTextBrowser()
        viewer.setHtml(state["html"])
        dialog_layout.addWidget(viewer, stretch=1)
        buttons = QHBoxLayout()
        export_button = QPushButton("Export PDF…")
        export_button.clicked.connect(
            lambda: self._export_report_html_to_pdf(state["html"], "Export Business Use Worksheet", f"Business_Use_{asset.name.replace(' ', '_')}_{year}")
        )
        buttons.addWidget(export_button)
        if sheet.unit == "miles":
            def set_rate() -> None:
                current = sheet.mileage_rate or 0.0
                rate, ok = QInputDialog.getDouble(
                    None, "Standard Mileage Rate", f"IRS standard mileage rate for {year}, in dollars per mile (from irs.gov):",
                    current, 0.0, 5.0, 3,
                )
                if ok and rate > 0:
                    set_mileage_rate(self.context, year, rate)
                    state["html"] = build_worksheet_html(build_worksheet(self.context, asset, year),
                                                         datetime.now().strftime("%Y-%m-%d %H:%M"))
                    viewer.setHtml(state["html"])
            rate_button = QPushButton("Set Mileage Rate…")
            rate_button.clicked.connect(set_rate)
            buttons.addWidget(rate_button)
        buttons.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        buttons.addWidget(close_button)
        dialog_layout.addLayout(buttons)
        dialog.exec()

    def _on_record_tool_purchase(self) -> None:
        if self.context.maintenance is None:
            return
        name, ok = QInputDialog.getText(None, "Record Tool Purchase", "Tool (e.g. 'DeWalt drill'):")
        if not ok or not name.strip():
            return
        price, ok = QInputDialog.getDouble(None, "Record Tool Purchase", f"What did the {name.strip()} cost ($)?", 0, 0, 10_000_000, 2)
        if not ok or price <= 0:
            return
        project_id = ""
        projects = self.context.projects.all_projects() if self.context.projects is not None else []
        if projects:
            names = ["(Not for a build)"] + [p.name for p in projects]
            choice, ok = QInputDialog.getItem(None, "Record Tool Purchase", "Bought for a build?", names, 0, False)
            if ok and choice != names[0]:
                project_id = projects[names.index(choice) - 1].project_id
        record_tool_purchase(self.context, name.strip(), price, project_id=project_id)
        self._refresh_homestead()
        self._refresh_expense_list()

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
        if self._bill_list.count() == 0:
            message = "No bills match your filter." if bills else "No bills tracked yet — click Add Bill to get started."
            add_empty_state_item(self._bill_list, message)

    def _selected_bill_id(self) -> Optional[str]:
        return selected_item_data(self._bill_list)

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
        if self._income_source_list.count() == 0:
            message = "No income sources match your filter." if sources else "No income sources tracked yet — click Add Income Source to get started."
            add_empty_state_item(self._income_source_list, message)

    def _selected_income_source_id(self) -> Optional[str]:
        return selected_item_data(self._income_source_list)

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
        if self._income_list.count() == 0:
            add_empty_state_item(self._income_list, "No income recorded yet — click Add Income to get started.")

    def _selected_income_id(self) -> Optional[str]:
        return selected_item_data(self._income_list)

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
        if self._expense_list.count() == 0:
            add_empty_state_item(self._expense_list, "No expenses recorded yet — click Add Expense to get started.")

    def _selected_expense_id(self) -> Optional[str]:
        return selected_item_data(self._expense_list)

    def _on_add_expense(self) -> None:
        dialog = AddEditExpenseDialog(entities=self.context.budget.all_business_entities(), **self._expense_link_choices())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_expense(
            amount=dialog.entered_amount,
            category=dialog.entered_category,
            description=dialog.entered_description,
            date=dialog.entered_date,
            entity_id=dialog.entered_entity_id,
            tax_relevant=dialog.entered_tax_relevant,
            payee=dialog.entered_payee,
            notes=dialog.entered_notes,
            project_id=dialog.entered_project_id,
            asset_id=dialog.entered_asset_id,
        )
        self._refresh_expense_list()

    def _on_edit_expense(self) -> None:
        entry_id = self._selected_expense_id()
        if entry_id is None:
            QMessageBox.information(None, "No Expense Selected", "Select an expense entry to edit.")
            return

        entry = self.context.budget.get_expense(entry_id)
        dialog = AddEditExpenseDialog(entry=entry, entities=self.context.budget.all_business_entities(), **self._expense_link_choices())
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
            payee=dialog.entered_payee,
            notes=dialog.entered_notes,
            project_id=dialog.entered_project_id,
            asset_id=dialog.entered_asset_id,
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
    # Debts tab — payoff-tracked liabilities, ranked by real priority
    # (core.budget_manager.rank_debts()) under a chosen strategy. "Record
    # Payment" mirrors the Bills tab's "Mark Paid" shape: one click,
    # two real effects (a real Expense entry + a real balance
    # reduction) via BudgetManager.record_debt_payment().
    # ------------------------------------------------------------------

    def _build_debts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._debt_tab_summary_label = QLabel("")
        self._debt_tab_summary_label.setObjectName("SubtitleLabel")
        layout.addWidget(self._debt_tab_summary_label)

        strategy_row = QHBoxLayout()
        strategy_row.addWidget(QLabel("Payoff strategy:"))
        self._debt_strategy_combo = QComboBox()
        for strategy in DEBT_PAYOFF_STRATEGIES:
            self._debt_strategy_combo.addItem(strategy.capitalize(), strategy)
        # Hybrid (avalanche order, but an expiring promo jumps the
        # queue) is the real default — see core.budget_manager.rank_debts()'s
        # own docstring for why pure avalanche alone can miss a
        # time-boxed promo emergency.
        self._debt_strategy_combo.setCurrentIndex(DEBT_PAYOFF_STRATEGIES.index("hybrid"))
        self._debt_strategy_combo.currentIndexChanged.connect(lambda _idx: self._refresh_debt_list())
        strategy_row.addWidget(self._debt_strategy_combo, stretch=1)
        layout.addLayout(strategy_row)

        self._debt_list = QListWidget()
        layout.addWidget(self._debt_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Debt")
        add_button.clicked.connect(self._on_add_debt)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_debt)
        button_row.addWidget(edit_button)

        payment_button = QPushButton("Record Payment")
        payment_button.clicked.connect(self._on_record_debt_payment)
        button_row.addWidget(payment_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_debt)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_debt_list()
        return tab

    def _refresh_debt_list(self) -> None:
        if self._debt_list is None or self._debt_strategy_combo is None:
            return  # not built yet — _on_tab_changed can fire before the Debts tab exists
        today = date.today()
        strategy = self._debt_strategy_combo.currentData()
        debts = self.context.budget.all_debts()
        priorities = {p.debt.debt_id: p for p in self.context.budget.debt_payoff_priority(strategy, today=today)}

        self._debt_list.clear()
        for debt in debts:
            item = QListWidgetItem(format_debt_row(debt, today, priorities.get(debt.debt_id)))
            item.setData(Qt.ItemDataRole.UserRole, debt.debt_id)
            self._debt_list.addItem(item)
        if self._debt_list.count() == 0:
            add_empty_state_item(self._debt_list, "No debts tracked yet — click Add Debt to get started.")

        total_balance = self.context.budget.total_debt_balance()
        avg_apr = self.context.budget.weighted_average_debt_apr(today=today)
        min_payments = self.context.budget.total_minimum_debt_payments()
        self._debt_tab_summary_label.setText(
            f"Total Debt: {money(total_balance, ',.2f')}   ·   Weighted Avg APR: {avg_apr:.2f}%   ·   Min Payments/mo: {money(min_payments, ',.2f')}"
        )

    def _selected_debt_id(self) -> Optional[str]:
        return selected_item_data(self._debt_list)

    def _on_add_debt(self) -> None:
        dialog = AddEditDebtDialog(entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.add_debt(
            name=dialog.entered_name,
            balance=dialog.entered_balance,
            interest_rate=dialog.entered_interest_rate,
            minimum_payment=dialog.entered_minimum_payment,
            debt_type=dialog.entered_debt_type,
            promo_apr=dialog.entered_promo_apr,
            promo_expires_date=dialog.entered_promo_expires_date,
            entity_id=dialog.entered_entity_id,
            notes=dialog.entered_notes,
        )
        self._refresh_debt_list()

    def _on_edit_debt(self) -> None:
        debt_id = self._selected_debt_id()
        if debt_id is None:
            QMessageBox.information(None, "No Debt Selected", "Select a debt to edit.")
            return

        debt = self.context.budget.get_debt(debt_id)
        dialog = AddEditDebtDialog(debt=debt, entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.update_debt(
            debt_id,
            name=dialog.entered_name,
            balance=dialog.entered_balance,
            interest_rate=dialog.entered_interest_rate,
            minimum_payment=dialog.entered_minimum_payment,
            debt_type=dialog.entered_debt_type,
            promo_apr=dialog.entered_promo_apr,
            promo_expires_date=dialog.entered_promo_expires_date,
            entity_id=dialog.entered_entity_id,
            notes=dialog.entered_notes,
        )
        self._refresh_debt_list()

    def _on_record_debt_payment(self) -> None:
        debt_id = self._selected_debt_id()
        if debt_id is None:
            QMessageBox.information(None, "No Debt Selected", "Select a debt to record a payment against.")
            return

        debt = self.context.budget.get_debt(debt_id)
        dialog = RecordDebtPaymentDialog(default_amount=debt.minimum_payment)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.budget.record_debt_payment(debt_id, dialog.entered_amount, date=dialog.entered_paid_date)
        self._refresh_debt_list()
        self._refresh_expense_list()

    def _on_delete_debt(self) -> None:
        debt_id = self._selected_debt_id()
        if debt_id is None:
            QMessageBox.information(None, "No Debt Selected", "Select a debt to delete.")
            return

        debt = self.context.budget.get_debt(debt_id)
        confirm = QMessageBox.question(
            None,
            "Delete Debt",
            f"Delete '{debt.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.budget.delete_debt(debt_id)
        self._refresh_debt_list()

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
        self._summary_debt_label = QLabel()
        layout.addWidget(self._summary_debt_label)

        layout.addWidget(self._build_budget_targets_group())

        export_button = QPushButton("Export Business Report (PDF)…")
        export_button.clicked.connect(self._on_export_business_report)
        layout.addWidget(export_button)

        consolidated_export_button = QPushButton("Export Consolidated Report (All Entities)…")
        consolidated_export_button.clicked.connect(self._on_export_consolidated_report)
        layout.addWidget(consolidated_export_button)

        layout.addStretch(1)

        self._on_summary_this_month()
        return tab

    # ------------------------------------------------------------------
    # Trends tab
    # ------------------------------------------------------------------

    def _build_trends_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        entity_row = QHBoxLayout()
        entity_row.addWidget(QLabel("Entity:"))
        self._trends_entity_combo = QComboBox()
        self._populate_entity_combo(self._trends_entity_combo)
        self._trends_entity_combo.currentIndexChanged.connect(lambda _idx: self._refresh_trends_chart())
        entity_row.addWidget(self._trends_entity_combo, stretch=1)
        layout.addLayout(entity_row)

        self._trends_chart_view = QChartView()
        self._trends_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._trends_chart_view.setMinimumHeight(320)
        layout.addWidget(self._trends_chart_view, stretch=1)

        self._trends_net_label = QLabel()
        layout.addWidget(self._trends_net_label)

        self._refresh_trends_chart()
        return tab

    def _refresh_trends_chart(self) -> None:
        entity_id = self._trends_entity_combo.currentData()
        buckets = month_buckets(date.today(), count=12)

        income_set = QBarSet("Income")
        expenses_set = QBarSet("Expenses")
        income_set.setColor(QColor("#4A90D9"))  # deliberate, fixed pair — not Qt's auto-cycled series colors
        expenses_set.setColor(QColor("#E8934A"))
        categories = []
        net_total = 0.0
        for label, start, end in buckets:
            income = self.context.budget.total_income(start, end, entity_id=entity_id)
            expenses = self.context.budget.total_expenses(start, end, entity_id=entity_id)
            income_set.append(income)
            expenses_set.append(expenses)
            categories.append(label)
            net_total += income - expenses

        series = QBarSeries()
        series.append(income_set)
        series.append(expenses_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Income vs. Expenses — Last 12 Months")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Amount ($)")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self._trends_chart_view.setChart(chart)
        self._trends_net_label.setText(f"Net cash flow (last 12 months): {money(net_total, ',.2f')}")

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
            self._budget_target_actual_labels[category].setText(f"actual: {money(actual_by_category.get(category, 0.0), ',.2f')}")

    def _on_budget_target_changed(self, category: str) -> None:
        entity_id = self._budget_target_entity_id()
        amount = self._budget_target_spins[category].value()
        if amount <= 0.0:
            self.context.budget.delete_budget_target(category, entity_id=entity_id)
        else:
            self.context.budget.set_budget_target(category, amount, entity_id=entity_id)

    def _populate_entity_combo(self, combo: QComboBox) -> None:
        """None ("All Entities") is the default/off state matching
        total_income()'s own entity_id=None contract; "" filters to
        unassigned entries. Shared by every entity-filter combo this
        module owns (Summary, Trends) so they all stay in sync."""
        current = combo.currentData() if combo.count() else None
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("All Entities", None)
        combo.addItem("(Unassigned)", "")
        for ent in self.context.budget.all_business_entities():
            combo.addItem(ent.name, ent.entity_id)
        idx = combo.findData(current)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def _refresh_entity_combo(self) -> None:
        """Re-populates every entity-filter combo this module owns."""
        self._populate_entity_combo(self._summary_entity_combo)
        if self._trends_entity_combo is not None:
            self._populate_entity_combo(self._trends_entity_combo)

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

        self._summary_income_label.setText(f"Income: {money(income, ',.2f')}")
        self._summary_expenses_label.setText(f"Expenses: {money(expenses, ',.2f')}")
        self._summary_net_label.setText(f"Net: {money(income - expenses, ',.2f')}")
        self._summary_tax_income_label.setText(f"Tax-relevant income: {money(tax_income, ',.2f')}")
        self._summary_tax_expenses_label.setText(f"Tax-relevant (deductible) expenses: {money(tax_expenses, ',.2f')}")

        total_debt = budget.total_debt_balance(entity_id=entity_id)
        avg_apr = budget.weighted_average_debt_apr(entity_id=entity_id)
        self._summary_debt_label.setText(f"Total Debt: {money(total_debt, ',.2f')}  (weighted avg {avg_apr:.2f}% APR)")

    def _gather_equipment_use(self, entity_id: Optional[str], year: int) -> list[dict]:
        if self.context.business_use is None or self.context.maintenance is None:
            return []
        budget = self.context.budget
        sheets = []
        for asset_id in self.context.business_use.assets_with_business_use():
            asset = self.context.maintenance.get_asset(asset_id)
            if asset is not None:
                sheets.append(build_worksheet(self.context, asset, year))
        entity_names = {e.name for e in budget.all_business_entities()}
        if entity_id is None:
            scope = None
        elif entity_id == "":
            scope = ""
        else:
            entity = budget.get_business_entity(entity_id)
            scope = entity.name if entity is not None else ""
        return equipment_report_rows(sheets, scope, entity_names)

    def _gather_entity_report_kwargs(
        self, entity_id: Optional[str], start: Optional[str], end: Optional[str], range_label: str,
    ) -> dict:
        """Every build_business_report_html() kwarg that depends on one
        entity/household scope — shared between a standalone single-
        entity export and each per-entity section of the consolidated
        (all-entities) export, so the real gathering logic (budget
        targets, properties, Schedule E, 1099) lives in exactly one
        place. entity_id follows the Summary tab's own convention: None
        ("All Entities", single-entity export only — never passed by
        the consolidated export, which always loops concrete buckets),
        "" (Unassigned), or a real BusinessEntity id."""
        budget = self.context.budget
        real_estate = self.context.real_estate

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

        # Schedule E and 1099 tracking are both inherently annual — only
        # populate them for "This Year", same "caller decides, not the
        # report module" gating budget_targets already uses for its own
        # "This Month only" restriction. None (not []/{}) means "not
        # this range, omit the section" — see build_business_report_html()'s
        # own docstring for why that's distinct from a real empty result.
        schedule_e_properties = None
        payees_over_threshold = None
        equipment_use = None
        if range_label == "This Year":
            # 2026-09-28: the business share of equipment and vehicles.
            equipment_use = self._gather_equipment_use(entity_id, int((start or date.today().isoformat())[:4]))
            schedule_e_properties = []
            for prop in real_estate.all_properties():
                if entity_id is not None and prop.entity_id != entity_id:
                    continue
                if prop.property_type not in SCHEDULE_E_ELIGIBLE_PROPERTY_TYPES:
                    continue
                expenses_by_category: dict[str, float] = {}
                for expense in real_estate.expenses_for_property(prop.property_id, start, end):
                    expenses_by_category[expense.category] = expenses_by_category.get(expense.category, 0.0) + expense.amount
                # Real fix (2026-09-09): the logged "Mortgage/Rent"
                # total is a full P&I payment, but only the interest
                # portion is ever deductible on Schedule E — principal
                # repayment is a balance-sheet reduction, never an
                # expense line. Once this property has real loan terms
                # entered, substitute the actual interest-only portion;
                # otherwise keep the old full-amount behavior (with its
                # existing overstatement caveat in _schedule_e_table()).
                if "Mortgage/Rent" in expenses_by_category and has_loan_terms(prop):
                    expenses_by_category["Mortgage/Rent"] = interest_paid_in_range(prop, start, end)
                rents_received = sum(
                    i.amount for i in real_estate.income_for_property(prop.property_id, start, end)
                )
                schedule_e_properties.append({
                    "name": prop.name,
                    "rents_received": rents_received,
                    "expenses_by_category": expenses_by_category,
                    "depreciation": annual_depreciation(prop),
                })
            payees_over_threshold = budget.payees_over_1099_threshold(start, end, entity_id=entity_id or "")

        return dict(
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
            schedule_e_properties=schedule_e_properties,
            payees_over_threshold=payees_over_threshold,
            equipment_use=equipment_use,
        )

    def _gather_net_worth_by_source(self) -> dict[str, float]:
        """Household-wide, never scoped to the Summary tab's entity
        filter — Plaid/Kraken snapshots and native Real Estate equity
        have no entity concept in this app at all (a real fact, not a
        simplification: FinancialSnapshot carries no entity_id). Same
        "missing means excluded, not a fabricated zero" convention
        gui/home_dashboard.py's format_net_worth_line() already
        established — reimplemented here (not imported) since core/
        cannot depend on gui/."""
        finance = self.context.finance
        real_estate = self.context.real_estate
        contributions: dict[str, float] = {}
        if finance is not None:
            for snapshot in finance.all_latest_snapshots():
                total_value = snapshot.data.get("summary", {}).get("total_value")
                if total_value is None:
                    continue
                label = snapshot.data.get("institution_name") or snapshot.source
                contributions[label] = contributions.get(label, 0.0) + total_value
        properties = real_estate.all_properties()
        if properties:
            contributions["Property Portfolio"] = sum(property_equity(p) for p in properties)
        return contributions

    def _gather_investment_holdings(self) -> list[dict]:
        """Household-wide, same reasoning as _gather_net_worth_by_source()
        above. Flattens every connected Plaid item's real holdings
        snapshot (core/plaid_manager.py's "plaid_investments_<item_id>"
        source) into the shape core.business_report._investments_table()
        expects."""
        finance = self.context.finance
        holdings: list[dict] = []
        if finance is None:
            return holdings
        for snapshot in finance.all_latest_snapshots():
            if not snapshot.source.startswith("plaid_investments_"):
                continue
            institution_name = snapshot.data.get("institution_name") or "Unknown institution"
            for holding in snapshot.data.get("holdings", []):
                holdings.append({
                    "institution_name": institution_name,
                    "security_name": holding.get("security_name") or "Unknown security",
                    "ticker_symbol": holding.get("ticker_symbol"),
                    "quantity": holding.get("quantity"),
                    "value": holding.get("institution_value"),
                })
        return holdings

    def _export_report_html_to_pdf(self, html: str, dialog_title: str, filename_prefix: str) -> None:
        """Shared QTextDocument/QPrinter export flow for both the
        single-entity and consolidated Business Report buttons."""
        suggested_name = f"{filename_prefix}_{datetime.now():%Y-%m-%d}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(None, dialog_title, suggested_name, "PDF files (*.pdf)")
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

        entity_label = None
        if entity_id is not None:
            entity_label = "(Unassigned)" if entity_id == "" else budget.get_business_entity(entity_id).name

        html = build_business_report_html(
            range_label=range_label,
            start_date=start,
            end_date=end,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            entity_label=entity_label,
            net_worth_by_source=self._gather_net_worth_by_source(),
            investment_holdings=self._gather_investment_holdings(),
            **self._gather_entity_report_kwargs(entity_id, start, end, range_label),
        )
        self._export_report_html_to_pdf(html, "Export Business Report", "Business_Report")

    def _on_export_consolidated_report(self) -> None:
        """One document covering every entity/household bucket at once
        — a household running multiple LLCs otherwise has no way to
        compare them side-by-side (the single-entity export above is
        always scoped to whatever the Summary tab's entity combo
        currently selects). Reuses the Summary tab's own already-
        selected range, same as the single-entity export. Every bucket
        is always included, even with zero activity — this report's
        own consistent "never silently drop, show the honest empty
        state" convention, same as an individual bucket's own empty
        income/properties tables would already show in a standalone
        export."""
        start, end = self._summary_start_date, self._summary_end_date
        range_label = self._summary_range_label.text()
        budget = self.context.budget
        real_estate = self.context.real_estate

        buckets = [("(Unassigned)", "")] + [(ent.name, ent.entity_id) for ent in budget.all_business_entities()]

        entity_comparisons = []
        entity_report_bodies = []
        for label, bucket_entity_id in buckets:
            kwargs = self._gather_entity_report_kwargs(bucket_entity_id, start, end, range_label)
            properties = [p for p in real_estate.all_properties() if p.entity_id == bucket_entity_id]
            entity_comparisons.append({
                "label": label,
                "income_total": kwargs["income_total"],
                "expenses_total": kwargs["expenses_total"],
                "property_equity_total": sum(property_equity(p) for p in properties),
            })
            entity_report_bodies.append(build_business_report_html(
                range_label=range_label,
                start_date=start,
                end_date=end,
                generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                entity_label=label,
                include_net_worth_section=False,
                **kwargs,
            ))

        html = build_consolidated_business_report_html(
            range_label=range_label,
            start_date=start,
            end_date=end,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            net_worth_by_source=self._gather_net_worth_by_source(),
            investment_holdings=self._gather_investment_holdings(),
            entity_comparisons=entity_comparisons,
            entity_report_bodies=entity_report_bodies,
        )
        self._export_report_html_to_pdf(
            html, "Export Consolidated Report", "Consolidated_Business_Report",
        )

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

        self._plaid_add_liabilities_button = QPushButton("Add Card/Loan Access…")
        self._plaid_add_liabilities_button.clicked.connect(self._on_plaid_add_liabilities)
        button_row.addWidget(self._plaid_add_liabilities_button)

        self._plaid_sync_button = QPushButton("Sync Now")
        self._plaid_sync_button.clicked.connect(self._on_plaid_sync)
        button_row.addWidget(self._plaid_sync_button)

        layout.addLayout(button_row)

        manage_row = QHBoxLayout()
        self._plaid_disconnect_button = QPushButton("Disconnect Selected…")
        self._plaid_disconnect_button.clicked.connect(self._on_plaid_disconnect)
        manage_row.addWidget(self._plaid_disconnect_button)

        self._plaid_reset_button = QPushButton("Reset Plaid Setup…")
        self._plaid_reset_button.clicked.connect(self._on_plaid_reset)
        manage_row.addWidget(self._plaid_reset_button)
        # Which business each bank charge is for (core/business_tagging.py).
        self._business_tags_button = QPushButton("Review Business Tags")
        self._business_tags_button.clicked.connect(self._on_review_business_tags)
        manage_row.addWidget(self._business_tags_button)
        manage_row.addStretch(1)
        layout.addLayout(manage_row)

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
        self._plaid_add_liabilities_button.setEnabled(unlocked and self._selected_plaid_item_needs_liabilities_upgrade())
        self._plaid_disconnect_button.setEnabled(unlocked and self._selected_plaid_item_id() is not None)
        self._plaid_reset_button.setEnabled(unlocked)
        waiting = len(pending_review(self.context))
        has_businesses = bool(self.context.budget.all_business_entities())
        self._business_tags_button.setEnabled(has_businesses)
        self._business_tags_button.setText(f"Review Business Tags ({waiting})" if waiting else "Review Business Tags")
        self._business_tags_button.setToolTip(
            "Which business each bank charge is for." if has_businesses else "Add a business first (Summary tab → Manage Entities…)."
        )

        if not configured:
            self._plaid_status_label.setText("Not set up yet.")
        elif not unlocked:
            self._plaid_status_label.setText("Set up, locked — unlock to connect or sync.")
        else:
            count = len(plaid.connected_items())
            noun = "account" if count == 1 else "accounts"
            environment = (plaid.environment or "").upper()
            self._plaid_status_label.setText(f"Unlocked — {environment} — {count} connected {noun}.")

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
                if item.liabilities_enabled:
                    suffix_parts.append("cards/loans enabled")
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
                    self._plaid_holdings_list.addItem(f"Total holdings value: {money(total, ',.2f')}")
        else:
            self._plaid_holdings_list.addItem("Select a connected account to see its holdings.")

    def _selected_plaid_item_id(self) -> Optional[str]:
        return selected_item_data(self._plaid_accounts_list)

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

    def _selected_plaid_item_needs_liabilities_upgrade(self) -> bool:
        item_id = self._selected_plaid_item_id()
        if item_id is None or not self.context.plaid.is_unlocked():
            return False
        return any(i.item_id == item_id and not i.liabilities_enabled for i in self.context.plaid.connected_items())

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

    def _on_plaid_add_liabilities(self) -> None:
        """Update-mode counterpart to _on_plaid_connect() for
        Liabilities (credit cards/student loans -> the Debts tab) —
        same shape as _on_plaid_add_investments() above."""
        item_id = self._selected_plaid_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Account Selected", "Select a connected account to add card/loan access to.")
            return

        try:
            link_token, hosted_link_url = self.context.plaid.create_liabilities_upgrade_session(item_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Start", str(exc))
            return

        webbrowser.open(hosted_link_url)

        progress = PlaidConnectProgressDialog(self.context.plaid, link_token)
        if progress.exec() != QDialog.DialogCode.Accepted or not progress.entered_public_token:
            return

        try:
            self.context.plaid.finish_liabilities_upgrade(item_id, progress.entered_public_token)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Finish", str(exc))
            return

        save_dialog = PasswordPromptDialog("your Plaid vault", prompt="Re-enter the passphrase for")
        if save_dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.context.plaid.save_current_vault(save_dialog.entered_password)
            except SecretsError as exc:
                QMessageBox.warning(None, "Couldn't Save", f"Card/loan access granted for this session, but saving failed: {exc}")
        self._refresh_plaid_tab()

    def _on_plaid_disconnect(self) -> None:
        item_id = self._selected_plaid_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Account Selected", "Select a connected account to disconnect.")
            return
        item = next((i for i in self.context.plaid.connected_items() if i.item_id == item_id), None)
        if item is None:
            return
        confirm = QMessageBox.question(
            None,
            "Disconnect Bank",
            f"Disconnect '{item.institution_name}'?\n\n"
            "Plaid removes the connection (freeing its slot). Its balances leave your net worth, "
            "and its synced debts become manual debts. Imported transactions are kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        pw_dialog = PasswordPromptDialog("your Plaid vault", prompt="Enter the passphrase for")
        if pw_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.context.plaid.disconnect_item(item_id, pw_dialog.entered_password)
        except SecretsError as exc:
            QMessageBox.warning(None, "Couldn't Disconnect", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — surface a real Plaid API error; the item is kept for retry
            QMessageBox.warning(None, "Couldn't Disconnect", f"Plaid didn't remove the connection, so it was kept: {exc}")
            return
        QMessageBox.information(None, "Disconnected", f"'{item.institution_name}' was disconnected.")
        self._refresh_plaid_tab()
        self._refresh_debt_list()

    def _on_plaid_reset(self) -> None:
        plaid = self.context.plaid
        dialog = ResetPlaidDialog(plaid.environment or "", len(plaid.connected_items()))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            result = plaid.reset(dialog.entered_passphrase, purge_imported_data=dialog.purge_imported_data)
        except SecretsError as exc:
            QMessageBox.warning(None, "Couldn't Reset", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(None, "Couldn't Reset", str(exc))
            return

        if not result.completed:
            QMessageBox.warning(
                None, "Reset Stopped",
                "These connections couldn't be removed, so your Plaid setup was kept:\n\n"
                + "\n".join(result.failed)
                + "\n\nAny others were disconnected. Try Reset again later.",
            )
        else:
            message = f"Disconnected {len(result.removed)} bank(s) and removed your saved Plaid keys."
            if dialog.purge_imported_data:
                message += (
                    f" Deleted {result.income_purged + result.expenses_purged} imported transaction(s)"
                    f" and {result.debts_purged} synced debt(s)."
                )
            message += " You can now run Set Up Plaid again."
            QMessageBox.information(None, "Plaid Reset", message)
        self._refresh_plaid_tab()
        self._refresh_debt_list()
        self._refresh_income_list()
        self._refresh_expense_list()

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
        if result.debts_added or result.debts_updated:
            message += f" Debts: {result.debts_added} new, {result.debts_updated} updated (see the Debts tab)."
        tagging = auto_tag_new(self.context).describe()
        if tagging:
            message += f" {tagging}"
        QMessageBox.information(None, "Synced", message)
        self._refresh_plaid_tab()
        self._refresh_debt_list()
        self._refresh_expense_list()
        self._refresh_income_list()

    def _on_review_business_tags(self) -> None:
        from gui.business_tags_dialog import BusinessTagsDialog

        if BusinessTagsDialog(self.context).exec() == QDialog.DialogCode.Accepted:
            self._refresh_expense_list()
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
                    description=f"Bill — {money(bill.amount, '.2f')} [{bill.category}]",
                    source=self.display_name,
                    action_type="open_module",
                    action_target=self.module_id,
                ))
        return results
