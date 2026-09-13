"""
modules.real_estate.module
=============================

Real Estate: a property portfolio — values, equity, rental income, and
linked Maintenance history per property. List page (all properties,
glance tiles) + a detail page per property (info, linked maintenance
task list, income/expense history, a NOI/cap-rate/equity summary) —
same `QStackedWidget` "← Back" pattern as modules/knowledge/module.py,
not a second top-level module, since reopening a property shouldn't
feel like leaving and re-entering the app.

All persistence/reporting logic lives in core/real_estate_manager.py
(self.context.real_estate) — this module is the Qt-facing wrapper
around it. Rental income/expenses are real core.budget_manager entries
(reused, not duplicated — see that manager's own docstring); Maintenance
history is a real core.maintenance_manager.MaintenanceAsset's real task
list, read directly via self.context.maintenance (any module can use a
core service directly — only cross-*module* imports are restricted).
format_property_glance_line()/format_linked_task_line() are
independently-owned free functions here, not imported from
modules.budget.module/modules.property.module, matching the same
"no cross-module import" stance already established for
Garage/Property's near-identical formatters.

The detail page is rebuilt fresh every time it's opened (not cached)
— unlike Knowledge's reader pages (static PDF content, worth caching
scroll position), a property's linked financial/maintenance data
changes often enough that showing stale data would be a real, confusing
bug, not just a missed optimization.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.budget_manager import ExpenseEntry, IncomeEntry
from gui.widgets.asset_missions_panel import build_asset_missions_panel
from core.maintenance_manager import MaintenanceTask, days_until_due, is_meter_task_due, is_sensor_task_due, meter_used_since_last
from core.real_estate_manager import (
    Property,
    accumulated_depreciation,
    annual_depreciation,
    equity,
    has_loan_terms,
    monthly_payment,
    payoff_date,
    remaining_balance_as_of,
)
from gui.add_edit_income_dialog import AddEditIncomeDialog
from gui.add_edit_expense_dialog import AddEditExpenseDialog
from gui.add_edit_property_dialog import AddEditPropertyDialog
from gui.list_widget_helpers import add_empty_state_item, selected_item_data
from modules.module_base import ModuleBase


def format_property_glance_line(prop: Property, equity_value: float) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_real_estate_module.py)."""
    return f"{prop.name}   [{prop.property_type}]   Equity: ${equity_value:,.2f}"


def format_linked_task_line(task: MaintenanceTask, today: date, readings: Optional[list] = None) -> str:
    """Pure formatting logic — testable without Qt. Same status
    vocabulary as modules.property.module.format_task_status_line,
    independently owned (see module docstring)."""
    readings = readings or []

    if task.trigger_type == "calendar":
        remaining = days_until_due(task, today)
        if remaining is None:
            status = "one-time" if not task.last_completed else "done"
        elif remaining < 0:
            status = f"overdue {-remaining}d"
        elif remaining == 0:
            status = "due today"
        else:
            status = f"due in {remaining}d"
        return f"{task.title} — {status}"

    if task.is_meter_task:
        unit = task.meter_unit or "units"
        if task.last_completed_meter_value is None:
            status = "never done"
        elif not readings:
            status = "no readings logged"
        else:
            used = meter_used_since_last(task, readings) or 0.0
            interval = task.meter_interval or 0.0
            remaining_units = interval - used
            status = f"overdue {-remaining_units:.0f} {unit}" if remaining_units <= 0 else f"{used:.0f}/{interval:.0f} {unit}"
        return f"{task.title} — {status}"

    if not readings:
        status = "no readings logged"
    else:
        latest = readings[-1].value
        unit = task.meter_unit or ""
        status = f"due — {latest:g}{unit}" if is_sensor_task_due(task, readings) else f"ok — {latest:g}{unit}"
    return f"{task.title} — {status}"


def format_income_row(entry: IncomeEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description_part = f"  {entry.description}" if entry.description else ""
    return f"{entry.date}   ${entry.amount:.2f}{description_part}"


def format_expense_row(entry: ExpenseEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description_part = f"  {entry.description}" if entry.description else ""
    return f"{entry.date}   ${entry.amount:.2f}  [{entry.category}]{description_part}"


class RealEstateModule(ModuleBase):
    module_id = "real_estate"
    display_name = "Real Estate"
    description = "Property values, equity, rental income, and linked maintenance."
    icon = "\U0001F3D8"  # houses

    def __init__(self, context) -> None:
        super().__init__(context)
        self._stack: Optional[QStackedWidget] = None
        self._list_page: Optional[QWidget] = None
        self._detail_page: Optional[QWidget] = None
        self._detail_property_id: Optional[str] = None

        self._property_list: Optional[QListWidget] = None
        self._entity_filter_combo: Optional[QComboBox] = None
        self._tracked_label: Optional[QLabel] = None
        self._equity_label: Optional[QLabel] = None
        self._rental_label: Optional[QLabel] = None

        # Detail-page widget refs, rebuilt each time _build_detail_page runs.
        self._detail_income_list: Optional[QListWidget] = None
        self._detail_expense_list: Optional[QListWidget] = None
        self._detail_maintenance_list: Optional[QListWidget] = None
        self._detail_noi_label: Optional[QLabel] = None
        self._detail_cap_rate_label: Optional[QLabel] = None
        self._detail_annual_depreciation_label: Optional[QLabel] = None
        self._detail_accumulated_depreciation_label: Optional[QLabel] = None
        self._detail_monthly_payment_label: Optional[QLabel] = None
        self._detail_loan_balance_label: Optional[QLabel] = None
        self._detail_payoff_date_label: Optional[QLabel] = None
        self._detail_range_label: Optional[QLabel] = None
        self._detail_start_date: Optional[str] = None
        self._detail_end_date: Optional[str] = None

    def get_widget(self) -> QWidget:
        self._stack = QStackedWidget()
        self._list_page = self._build_list_page()
        self._stack.addWidget(self._list_page)
        self._stack.setCurrentWidget(self._list_page)
        return self._stack

    # ------------------------------------------------------------------
    # List page
    # ------------------------------------------------------------------

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        entity_row = QHBoxLayout()
        entity_row.addWidget(QLabel("Entity:"))
        self._entity_filter_combo = QComboBox()
        self._refresh_entity_filter_combo()
        self._entity_filter_combo.currentIndexChanged.connect(lambda _idx: self._refresh_list())
        entity_row.addWidget(self._entity_filter_combo, stretch=1)
        layout.addLayout(entity_row)

        glance_row = QHBoxLayout()
        glance_row.setSpacing(24)
        self._tracked_label = self._build_glance_tile(glance_row, "Properties")
        self._equity_label = self._build_glance_tile(glance_row, "Total Equity")
        self._rental_label = self._build_glance_tile(glance_row, "Rental Income This Month")
        layout.addLayout(glance_row)

        self._property_list = QListWidget()
        layout.addWidget(self._property_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Property")
        add_button.clicked.connect(self._on_add_property)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_property)
        button_row.addWidget(edit_button)

        details_button = QPushButton("View Details")
        details_button.clicked.connect(self._on_view_details)
        button_row.addWidget(details_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_property)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_list()
        return page

    def _build_glance_tile(self, row_layout: QHBoxLayout, caption: str) -> QLabel:
        tile = QVBoxLayout()
        value_label = QLabel("—")
        value_label.setObjectName("TitleLabel")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption_label = QLabel(caption)
        caption_label.setObjectName("SubtitleLabel")
        caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.addWidget(value_label)
        tile.addWidget(caption_label)
        row_layout.addLayout(tile)
        return value_label

    def _refresh_entity_filter_combo(self) -> None:
        """Read-only consumer of core.budget_manager's BusinessEntity
        list — this module never manages entities itself, only Budget's
        Summary tab does ("Manage Entities…"), to avoid two management
        entry points for the same list."""
        current = self._entity_filter_combo.currentData() if self._entity_filter_combo.count() else None
        self._entity_filter_combo.blockSignals(True)
        self._entity_filter_combo.clear()
        self._entity_filter_combo.addItem("All Entities", None)
        self._entity_filter_combo.addItem("(Unassigned)", "")
        for ent in self.context.budget.all_business_entities():
            self._entity_filter_combo.addItem(ent.name, ent.entity_id)
        idx = self._entity_filter_combo.findData(current)
        self._entity_filter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._entity_filter_combo.blockSignals(False)

    def _refresh_list(self) -> None:
        selected_entity = self._entity_filter_combo.currentData()
        properties = [
            p for p in self.context.real_estate.all_properties()
            if selected_entity is None or p.entity_id == selected_entity
        ]

        self._tracked_label.setText(str(len(properties)))
        total_equity = sum(equity(p) for p in properties)
        self._equity_label.setText(f"${total_equity:,.2f}")

        today = date.today()
        month_start = today.replace(day=1).isoformat()
        total_rental = sum(
            sum(e.amount for e in self.context.real_estate.income_for_property(p.property_id, month_start))
            for p in properties
        )
        self._rental_label.setText(f"${total_rental:,.2f}")

        self._property_list.clear()
        for prop in properties:
            item = QListWidgetItem(format_property_glance_line(prop, equity(prop)))
            item.setData(Qt.ItemDataRole.UserRole, prop.property_id)
            self._property_list.addItem(item)
        if self._property_list.count() == 0:
            if selected_entity is not None:
                add_empty_state_item(self._property_list, "No properties for this entity.")
            else:
                add_empty_state_item(self._property_list, "No properties tracked yet — click Add Property to get started.")

    def _selected_property_id(self) -> Optional[str]:
        return selected_item_data(self._property_list)

    def _on_add_property(self) -> None:
        dialog = AddEditPropertyDialog(entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.real_estate.add_property(
            name=dialog.entered_name,
            property_type=dialog.entered_property_type,
            purchase_date=dialog.entered_purchase_date,
            purchase_price=dialog.entered_purchase_price,
            current_value=dialog.entered_current_value,
            mortgage_balance=dialog.entered_mortgage_balance,
            entity_id=dialog.entered_entity_id,
            land_value=dialog.entered_land_value,
            placed_in_service_date=dialog.entered_placed_in_service_date,
            original_loan_amount=dialog.entered_original_loan_amount,
            interest_rate_pct=dialog.entered_interest_rate_pct,
            loan_term_months=dialog.entered_loan_term_months,
            loan_start_date=dialog.entered_loan_start_date,
            notes=dialog.entered_notes,
        )
        self._refresh_list()

    def _on_edit_property(self) -> None:
        property_id = self._selected_property_id()
        if property_id is None:
            QMessageBox.information(None, "No Property Selected", "Select a property to edit.")
            return

        prop = self.context.real_estate.get_property(property_id)
        dialog = AddEditPropertyDialog(property_=prop, entities=self.context.budget.all_business_entities())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.real_estate.update_property(
            property_id,
            name=dialog.entered_name,
            property_type=dialog.entered_property_type,
            purchase_date=dialog.entered_purchase_date,
            purchase_price=dialog.entered_purchase_price,
            current_value=dialog.entered_current_value,
            mortgage_balance=dialog.entered_mortgage_balance,
            entity_id=dialog.entered_entity_id,
            land_value=dialog.entered_land_value,
            placed_in_service_date=dialog.entered_placed_in_service_date,
            original_loan_amount=dialog.entered_original_loan_amount,
            interest_rate_pct=dialog.entered_interest_rate_pct,
            loan_term_months=dialog.entered_loan_term_months,
            loan_start_date=dialog.entered_loan_start_date,
            notes=dialog.entered_notes,
        )
        self._refresh_list()

    def _on_view_details(self) -> None:
        property_id = self._selected_property_id()
        if property_id is None:
            QMessageBox.information(None, "No Property Selected", "Select a property to view.")
            return
        self._show_detail_page(property_id)

    def _on_delete_property(self) -> None:
        property_id = self._selected_property_id()
        if property_id is None:
            QMessageBox.information(None, "No Property Selected", "Select a property to delete.")
            return

        prop = self.context.real_estate.get_property(property_id)
        confirm = QMessageBox.question(
            None,
            "Delete Property",
            f"Delete '{prop.name}'? Its recorded income/expenses and any linked Maintenance asset are kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.real_estate.delete_property(property_id)
        self._refresh_list()

    # ------------------------------------------------------------------
    # Detail page
    # ------------------------------------------------------------------

    def _show_list_page(self) -> None:
        self._stack.setCurrentWidget(self._list_page)
        if self._detail_page is not None:
            self._stack.removeWidget(self._detail_page)
            self._detail_page = None
            self._detail_property_id = None
        self._refresh_list()

    def _show_detail_page(self, property_id: str) -> None:
        if self._detail_page is not None:
            self._stack.removeWidget(self._detail_page)
            self._detail_page = None

        self._detail_property_id = property_id
        self._detail_start_date = None
        self._detail_end_date = None
        self._detail_page = self._build_detail_page(property_id)
        self._stack.addWidget(self._detail_page)
        self._stack.setCurrentWidget(self._detail_page)

    def _build_detail_page(self, property_id: str) -> QWidget:
        prop = self.context.real_estate.get_property(property_id)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        back_button = QPushButton("← Back to Properties")
        back_button.clicked.connect(self._show_list_page)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        header = QLabel(prop.name)
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        entity = self.context.budget.get_business_entity(prop.entity_id) if prop.entity_id else None
        entity_name = entity.name if entity is not None else "(Unassigned)"
        info = QLabel(
            f"{prop.property_type}   —   Purchased {prop.purchase_date or 'unknown'} for ${prop.purchase_price:,.2f}\n"
            f"Current value: ${prop.current_value:,.2f}   Mortgage balance: ${prop.mortgage_balance:,.2f}   "
            f"Equity: ${equity(prop):,.2f}\n"
            f"Entity: {entity_name}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addWidget(self._build_maintenance_section(prop))
        layout.addWidget(self._build_missions_section(prop))
        layout.addWidget(self._build_income_expense_section(prop), stretch=1)
        layout.addWidget(self._build_summary_section(prop))

        return page

    def _build_missions_section(self, prop: Property) -> QWidget:
        """Mission-to-asset tagging (2026-09-13) — real parity across
        areas: this is the same shared panel Garage/Property/Greenhouse
        embed on their own asset detail pages, at the user's own
        explicit request. An unlinked property (no maintenance_asset_id
        yet) gets an honest note rather than a panel with nothing to
        show — same "prefer the model" stance the rest of this app's
        Maintenance integration already takes."""
        if not prop.maintenance_asset_id:
            section = QWidget()
            layout = QVBoxLayout(section)
            layout.setContentsMargins(0, 0, 0, 0)
            note = QLabel("Link a Maintenance asset above to see related Missions.")
            note.setObjectName("SubtitleLabel")
            layout.addWidget(note)
            return section
        return build_asset_missions_panel(self.context, prop.maintenance_asset_id)

    def focus_record(self, record_id: str) -> None:
        """Cross-module deep-linking (2026-09-13) — opens straight to
        this property's own detail page, same mechanism
        Garage/Property/Greenhouse's own focus_record() implementations
        use."""
        self._show_detail_page(record_id)

    def _build_maintenance_section(self, prop: Property) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Maintenance")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        self._detail_maintenance_list = QListWidget()
        self._detail_maintenance_list.setMaximumHeight(120)
        layout.addWidget(self._detail_maintenance_list)

        if prop.maintenance_asset_id and self.context.maintenance.get_asset(prop.maintenance_asset_id) is not None:
            today = date.today()
            for task in self.context.maintenance.tasks_for_asset(prop.maintenance_asset_id):
                readings = (
                    self.context.maintenance.readings_for_task(task.task_id) if task.trigger_type != "calendar" else []
                )
                self._detail_maintenance_list.addItem(format_linked_task_line(task, today, readings))
            if self._detail_maintenance_list.count() == 0:
                self._detail_maintenance_list.addItem("No maintenance tasks tracked for this property yet.")
            unlink_button = QPushButton("Unlink Maintenance Asset")
            unlink_button.clicked.connect(lambda: self._on_unlink_maintenance(prop.property_id))
            layout.addWidget(unlink_button, alignment=Qt.AlignmentFlag.AlignLeft)
        else:
            self._detail_maintenance_list.addItem("No Maintenance asset linked yet.")
            link_button = QPushButton("Link Maintenance Asset…")
            link_button.clicked.connect(lambda: self._on_link_maintenance(prop.property_id))
            layout.addWidget(link_button, alignment=Qt.AlignmentFlag.AlignLeft)

        return section

    def _on_link_maintenance(self, property_id: str) -> None:
        candidates = [a for a in self.context.maintenance.all_assets() if a.category == "Property"]
        if not candidates:
            QMessageBox.information(
                None, "No Property Assets Yet",
                "Add a Maintenance asset with category 'Property' first (in the Maintenance or Property module), then link it here.",
            )
            return

        labels = [f"{a.name}" for a in candidates]
        label, ok = QInputDialog.getItem(None, "Link Maintenance Asset", "Asset:", labels, editable=False)
        if not ok or not label:
            return

        chosen = candidates[labels.index(label)]
        self.context.real_estate.update_property(property_id, maintenance_asset_id=chosen.asset_id)
        self._show_detail_page(property_id)

    def _on_unlink_maintenance(self, property_id: str) -> None:
        self.context.real_estate.update_property(property_id, maintenance_asset_id="")
        self._show_detail_page(property_id)

    def _build_income_expense_section(self, prop: Property) -> QWidget:
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)

        income_column = QVBoxLayout()
        income_title = QLabel("Rental Income")
        income_title.setStyleSheet("font-weight: 600;")
        income_column.addWidget(income_title)
        self._detail_income_list = QListWidget()
        income_column.addWidget(self._detail_income_list, stretch=1)
        record_income_button = QPushButton("Record Rental Income")
        record_income_button.clicked.connect(lambda: self._on_record_income(prop.property_id))
        income_column.addWidget(record_income_button)
        layout.addLayout(income_column)

        expense_column = QVBoxLayout()
        expense_title = QLabel("Expenses")
        expense_title.setStyleSheet("font-weight: 600;")
        expense_column.addWidget(expense_title)
        self._detail_expense_list = QListWidget()
        expense_column.addWidget(self._detail_expense_list, stretch=1)
        record_expense_button = QPushButton("Record Expense")
        record_expense_button.clicked.connect(lambda: self._on_record_expense(prop.property_id))
        expense_column.addWidget(record_expense_button)
        layout.addLayout(expense_column)

        for entry in self.context.real_estate.income_for_property(prop.property_id):
            self._detail_income_list.addItem(format_income_row(entry))
        if self._detail_income_list.count() == 0:
            add_empty_state_item(self._detail_income_list, "No rental income recorded yet.")
        for entry in self.context.real_estate.expenses_for_property(prop.property_id):
            self._detail_expense_list.addItem(format_expense_row(entry))
        if self._detail_expense_list.count() == 0:
            add_empty_state_item(self._detail_expense_list, "No expenses recorded yet.")

        return section

    def _on_record_income(self, property_id: str) -> None:
        dialog = AddEditIncomeDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.real_estate.record_rental_income(
            property_id, amount=dialog.entered_amount, date_str=dialog.entered_date,
            description=dialog.entered_description, notes=dialog.entered_notes,
        )
        self._show_detail_page(property_id)

    def _on_record_expense(self, property_id: str) -> None:
        dialog = AddEditExpenseDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.real_estate.record_property_expense(
            property_id, amount=dialog.entered_amount, category=dialog.entered_category,
            date_str=dialog.entered_date, description=dialog.entered_description, notes=dialog.entered_notes,
        )
        self._show_detail_page(property_id)

    def _build_summary_section(self, prop: Property) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Summary")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        self._detail_range_label = QLabel("")
        self._detail_range_label.setObjectName("SubtitleLabel")
        layout.addWidget(self._detail_range_label)

        range_row = QHBoxLayout()
        month_button = QPushButton("This Month")
        month_button.clicked.connect(lambda: self._on_summary_this_month(prop.property_id))
        range_row.addWidget(month_button)

        year_button = QPushButton("This Year")
        year_button.clicked.connect(lambda: self._on_summary_this_year(prop.property_id))
        range_row.addWidget(year_button)

        all_time_button = QPushButton("All Time")
        all_time_button.clicked.connect(lambda: self._on_summary_all_time(prop.property_id))
        range_row.addWidget(all_time_button)
        layout.addLayout(range_row)

        self._detail_noi_label = QLabel()
        layout.addWidget(self._detail_noi_label)
        self._detail_cap_rate_label = QLabel()
        layout.addWidget(self._detail_cap_rate_label)
        self._detail_annual_depreciation_label = QLabel()
        layout.addWidget(self._detail_annual_depreciation_label)
        self._detail_accumulated_depreciation_label = QLabel()
        layout.addWidget(self._detail_accumulated_depreciation_label)
        self._detail_monthly_payment_label = QLabel()
        layout.addWidget(self._detail_monthly_payment_label)
        self._detail_loan_balance_label = QLabel()
        layout.addWidget(self._detail_loan_balance_label)
        self._detail_payoff_date_label = QLabel()
        layout.addWidget(self._detail_payoff_date_label)

        self._refresh_summary(prop.property_id, "This Month", self._month_start(), None)
        return section

    @staticmethod
    def _month_start() -> str:
        return date.today().replace(day=1).isoformat()

    def _on_summary_this_month(self, property_id: str) -> None:
        self._refresh_summary(property_id, "This Month", self._month_start(), None)

    def _on_summary_this_year(self, property_id: str) -> None:
        self._refresh_summary(property_id, "This Year", date.today().replace(month=1, day=1).isoformat(), None)

    def _on_summary_all_time(self, property_id: str) -> None:
        self._refresh_summary(property_id, "All Time", None, None)

    def _refresh_summary(self, property_id: str, label: str, start_date: Optional[str], end_date: Optional[str]) -> None:
        self._detail_range_label.setText(label)
        noi = self.context.real_estate.net_operating_income(property_id, start_date, end_date)
        cap_rate = self.context.real_estate.cap_rate(property_id, start_date, end_date)
        self._detail_noi_label.setText(f"Net Operating Income: ${noi:,.2f}")
        cap_rate_text = f"{cap_rate * 100:.2f}%" if cap_rate is not None else "n/a (set a current value)"
        self._detail_cap_rate_label.setText(f"Cap Rate: {cap_rate_text}")

        # Depreciation is a property-level figure, not date-range scoped
        # like NOI/cap rate — recomputed here anyway (harmless) so it
        # stays in one refresh path rather than needing separate wiring.
        prop = self.context.real_estate.get_property(property_id)
        if prop is not None:
            annual = annual_depreciation(prop)
            # Real, honest caveat: an unset Land Value (0.0, the field's
            # own default) means depreciable_basis() treats the FULL
            # purchase price as depreciable, inflating this real-looking
            # number — same "flag a real-but-possibly-misleading figure"
            # convention Cap Rate's own "n/a (set a current value)" text
            # already uses on this exact view.
            land_value_caveat = " (land value not set — this may overstate depreciation)" if annual > 0 and prop.land_value <= 0 else ""
            self._detail_annual_depreciation_label.setText(f"Annual Depreciation: ${annual:,.2f}{land_value_caveat}")
            accumulated = accumulated_depreciation(prop, date.today())
            self._detail_accumulated_depreciation_label.setText(f"Accumulated Depreciation: ${accumulated:,.2f}{land_value_caveat}")

            # Loan terms are a separate, optional concept from the
            # manually-tracked mortgage_balance shown elsewhere — this
            # is a PROJECTION from the entered loan terms, so the
            # labels say so explicitly rather than implying they're the
            # same authoritative figure (see remaining_balance_as_of()'s
            # own docstring in core/real_estate_manager.py).
            if has_loan_terms(prop):
                self._detail_monthly_payment_label.setText(f"Monthly Payment (P&I): ${monthly_payment(prop):,.2f}")
                balance = remaining_balance_as_of(prop, date.today())
                self._detail_loan_balance_label.setText(f"Est. Remaining Loan Balance (per loan terms): ${balance:,.2f}")
                self._detail_payoff_date_label.setText(f"Est. Payoff Date: {payoff_date(prop)}")
            else:
                self._detail_monthly_payment_label.setText("Monthly Payment: enter loan terms to calculate")
                self._detail_loan_balance_label.setText("")
                self._detail_payoff_date_label.setText("")
