"""
modules.workshop.module
=========================

Workshop & Electronics — docs/ROADMAP.md milestone 8.3 (Component DB)
plus MIA Home's production pipeline (2026-07-16, see
docs/VISION.md's "MIA Home's expanded scope" section):
Materials/Jobs/Products/Ledger. Five tabs in one module
(docs/MODULE_SPEC.md allows exactly one `ModuleBase` subclass per
module folder, so multiple sub-features share tabs rather than
becoming separate modules — same reasoning modules/field_kit/module.py
gives for being the first module to need a `QTabWidget`).

**Components** (original, unchanged) — a dedicated electronics-parts
inventory backed by core/component_manager.py.

**Materials/Jobs/Products/Ledger** — this module was the natural home
for the production-pipeline GUI: its own docstring had already flagged
"3D printer/CNC/laser... waits for that hardware/tooling to exist," and
Materials/Jobs/Products/Ledger are exactly the shared data layer real
fab-hardware modules would eventually read/write against, per
`core/material_manager.py`'s docstring. Placed here (new tabs) rather
than a separate top-level module, at the user's explicit call.

Each tab follows the same list+filter+Add/Edit/Delete shape as
Components. Jobs additionally has "Consume Material"/"Produce Product"
(core/job_manager.py's real cross-manager integration points); Products
additionally has "Add Listing"/"Remove Listing"; Ledger additionally
has "Record Sale" (core/ledger_manager.py's real integration point) and
shows a live Net Profit summary.

format_component_row()/format_material_row()/format_job_row()/
format_product_row()/format_revenue_row()/format_expense_row() are free
functions (not methods), same pure-formatting-logic shape as
modules/notes/module.py's format_entry_row() — testable without Qt, see
tests/test_workshop_module.py.
"""

from __future__ import annotations

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

from core.component_manager import Component
from core.job_manager import Job
from core.ledger_manager import ExpenseEntry, RevenueEntry
from core.material_manager import Material
from core.product_manager import Product
from gui.add_edit_component_dialog import AddEditComponentDialog
from gui.add_edit_job_dialog import AddEditJobDialog
from gui.add_edit_listing_dialog import AddListingDialog
from gui.add_edit_material_dialog import AddEditMaterialDialog
from gui.add_edit_product_dialog import AddEditProductDialog
from gui.add_expense_dialog import AddExpenseDialog
from gui.add_revenue_dialog import AddRevenueDialog
from gui.pick_item_quantity_dialog import PickItemQuantityDialog
from modules.module_base import ModuleBase


def format_component_row(component: Component) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_workshop_module.py)."""
    detail_parts = [part for part in (component.category, component.value, component.package) if part]
    detail = f"  [{', '.join(detail_parts)}]" if detail_parts else ""
    location = f"  ({component.location})" if component.location else ""
    return f"{component.name}{detail}  qty {component.quantity}{location}"


def format_component_detail_line(
    added_by_name: Optional[str], times_used: int, last_used_by_name: Optional[str], last_used_date: Optional[str]
) -> str:
    """Pure formatting logic — testable without Qt. Multi-user pass
    (2026-09-14) — same shape as
    modules.toolbox.tools.inventory_tool.format_item_detail_line(),
    the second real application of this exact "shared object + user
    relationship" surfacing (Components is the third domain, after
    Recipes and Inventory)."""
    added_part = f"Added by {added_by_name}" if added_by_name else "Added by: unknown"
    if times_used:
        used_part = f"Used {times_used}x"
        if last_used_by_name and last_used_date:
            used_part += f" (last: {last_used_by_name} on {last_used_date})"
        elif last_used_date:
            used_part += f" (last: {last_used_date})"
    else:
        used_part = "Never used yet"
    return f"{added_part}  ·  {used_part}"


def format_material_row(material: Material) -> str:
    """Pure formatting logic — testable without Qt."""
    unit = f" {material.unit}" if material.unit else ""
    line = f"{material.name}  —  {material.quantity_on_hand:g}{unit} on hand  —  ${material.unit_cost:.2f}/{material.unit or 'unit'}"
    if material.quantity_on_hand <= material.reorder_threshold:
        line += "  ⚠ LOW STOCK"
    return line


def format_material_detail_line(
    added_by_name: Optional[str], times_used: int, last_used_by_name: Optional[str], last_used_date: Optional[str]
) -> str:
    """Pure formatting logic — testable without Qt. Same shape as
    format_component_detail_line() above — Materials is the fourth real
    application of this "shared object + user relationship" surfacing
    (Recipes, Inventory, Component DB, now Materials). No quick-adjust
    buttons here unlike Components/Inventory: a material's real usage
    event is "Consume Material" on a Job (see JobManager.
    consume_material()), not a manual per-item tally — this label
    reflects both that and any direct manual adjustment."""
    added_part = f"Added by {added_by_name}" if added_by_name else "Added by: unknown"
    if times_used:
        used_part = f"Used {times_used}x"
        if last_used_by_name and last_used_date:
            used_part += f" (last: {last_used_by_name} on {last_used_date})"
        elif last_used_date:
            used_part += f" (last: {last_used_date})"
    else:
        used_part = "Never used yet"
    return f"{added_part}  ·  {used_part}"


def format_job_row(job: Job) -> str:
    """Pure formatting logic — testable without Qt. Cost isn't included
    here — it needs live Material prices/the labor rate (see
    core/job_manager.py's total_cost()), which this pure function has
    no access to; the module appends it separately when refreshing."""
    return f"{job.name}  [{job.status}]  —  {job.labor_hours:g} labor hrs"


def format_product_row(product: Product) -> str:
    """Pure formatting logic — testable without Qt."""
    listing_count = len(product.listings)
    listing_note = f"  —  {listing_count} listing{'s' if listing_count != 1 else ''}" if listing_count else ""
    return f"{product.name}  —  {product.quantity_in_stock:g} in stock  —  ${product.base_price:.2f} base{listing_note}"


def format_product_detail_line(
    added_by_name: Optional[str], times_sold: int, last_sold_by_name: Optional[str], last_sold_date: Optional[str]
) -> str:
    """Pure formatting logic — testable without Qt. Same shape as
    format_material_detail_line() above — Products is the fifth real
    application of this "shared object + user relationship" surfacing.
    "Sold" not "used": a product's real usage event is production
    (Jobs) crediting stock and a sale (Ledger) debiting it, not a
    manual per-item tally, same reasoning Materials' own detail line
    already established for its two real event sources."""
    added_part = f"Added by {added_by_name}" if added_by_name else "Added by: unknown"
    if times_sold:
        sold_part = f"Sold {times_sold}x"
        if last_sold_by_name and last_sold_date:
            sold_part += f" (last: {last_sold_by_name} on {last_sold_date})"
        elif last_sold_date:
            sold_part += f" (last: {last_sold_date})"
    else:
        sold_part = "Never sold yet"
    return f"{added_part}  ·  {sold_part}"


def format_revenue_row(entry: RevenueEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description = f"  —  {entry.description}" if entry.description else ""
    return f"{entry.date}  —  ${entry.amount:.2f}{description}"


def format_expense_row(entry: ExpenseEntry) -> str:
    """Pure formatting logic — testable without Qt."""
    description = f"  —  {entry.description}" if entry.description else ""
    return f"{entry.date}  —  ${entry.amount:.2f}  [{entry.category}]{description}"


class WorkshopModule(ModuleBase):
    module_id = "workshop"
    display_name = "Workshop & Electronics"
    description = "Component inventory, fabrication materials/jobs/products, and a sales ledger."
    icon = "\U0001F529"  # nut and bolt

    def __init__(self, context) -> None:
        super().__init__(context)
        self._component_list: Optional[QListWidget] = None
        self._component_filter_edit: Optional[QLineEdit] = None
        self._component_detail_label: Optional[QLabel] = None
        self._material_list: Optional[QListWidget] = None
        self._material_filter_edit: Optional[QLineEdit] = None
        self._material_detail_label: Optional[QLabel] = None
        self._job_list: Optional[QListWidget] = None
        self._job_filter_edit: Optional[QLineEdit] = None
        self._product_list: Optional[QListWidget] = None
        self._product_filter_edit: Optional[QLineEdit] = None
        self._product_detail_label: Optional[QLabel] = None
        self._revenue_list: Optional[QListWidget] = None
        self._expense_list: Optional[QListWidget] = None
        self._net_profit_label: Optional[QLabel] = None

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
        tabs.addTab(self._build_components_tab(), "Components")
        tabs.addTab(self._build_materials_tab(), "Materials")
        tabs.addTab(self._build_jobs_tab(), "Jobs")
        tabs.addTab(self._build_products_tab(), "Products")
        tabs.addTab(self._build_ledger_tab(), "Ledger")
        layout.addWidget(tabs, stretch=1)

        return widget

    # ------------------------------------------------------------------
    # Components tab
    # ------------------------------------------------------------------

    def _build_components_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._component_filter_edit = QLineEdit()
        self._component_filter_edit.setPlaceholderText("Filter by name, category, value, package, or location…")
        self._component_filter_edit.textChanged.connect(lambda _text: self._refresh_components_list())
        layout.addWidget(self._component_filter_edit)

        self._component_list = QListWidget()
        self._component_list.currentItemChanged.connect(lambda *_: self._update_component_detail_label())
        layout.addWidget(self._component_list, stretch=1)

        # Multi-user pass (2026-09-14) — who added this component + real
        # usage history for the selected one, same "shared object + user
        # relationship" surfacing as
        # modules/toolbox/tools/inventory_tool.py's own detail label.
        self._component_detail_label = QLabel("")
        self._component_detail_label.setObjectName("SubtitleLabel")
        self._component_detail_label.setWordWrap(True)
        layout.addWidget(self._component_detail_label)

        adjust_row = QHBoxLayout()
        adjust_row.addWidget(QLabel("Quantity:"))

        minus_button = QPushButton("−1")
        minus_button.clicked.connect(lambda: self._on_adjust_component(-1))
        adjust_row.addWidget(minus_button)

        plus_button = QPushButton("+1")
        plus_button.clicked.connect(lambda: self._on_adjust_component(1))
        adjust_row.addWidget(plus_button)

        adjust_row.addStretch()
        layout.addLayout(adjust_row)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Component")
        add_button.clicked.connect(self._on_add_component)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_component)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_component)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_components_list()
        return tab

    def _refresh_components_list(self, select_component_id: Optional[str] = None) -> None:
        query = self._component_filter_edit.text().strip()
        components = (
            self.context.components.search(query) if query else self.context.components.all_components()
        )

        self._component_list.clear()
        for component in components:
            item = QListWidgetItem(format_component_row(component))
            item.setData(Qt.ItemDataRole.UserRole, component.component_id)
            self._component_list.addItem(item)
            if component.component_id == select_component_id:
                self._component_list.setCurrentItem(item)
        self._update_component_detail_label()

    def _selected_component_id(self) -> Optional[str]:
        item = self._component_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _profile_name(self, profile_id: Optional[str]) -> Optional[str]:
        if profile_id is None or self.context.profiles is None:
            return None
        match = next((p for p in self.context.profiles.list_profiles() if p.profile_id == profile_id), None)
        return match.name if match is not None else None

    def _update_component_detail_label(self) -> None:
        component_id = self._selected_component_id()
        if component_id is None:
            self._component_detail_label.setText("")
            return

        component = self.context.components.get_component(component_id)
        if component is None:
            self._component_detail_label.setText("")
            return

        added_by_name = self._profile_name(component.added_by_profile_id)
        times_used = self.context.components.times_used(component_id)
        last_used_entry = self.context.components.last_used(component_id)
        last_used_by_name = self._profile_name(last_used_entry.profile_id) if last_used_entry else None
        last_used_date = last_used_entry.timestamp[:10] if last_used_entry else None

        self._component_detail_label.setText(
            format_component_detail_line(added_by_name, times_used, last_used_by_name, last_used_date)
        )

    def _on_adjust_component(self, delta: int) -> None:
        component_id = self._selected_component_id()
        if component_id is None:
            QMessageBox.information(None, "No Component Selected", "Select a component to adjust.")
            return
        self.context.components.adjust_quantity(component_id, delta)
        self._refresh_components_list(select_component_id=component_id)

    def _on_add_component(self) -> None:
        dialog = AddEditComponentDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        added = self.context.components.add_component(
            name=dialog.entered_name, category=dialog.entered_category, value=dialog.entered_value,
            package=dialog.entered_package, quantity=dialog.entered_quantity,
            location=dialog.entered_location, notes=dialog.entered_notes,
        )
        self._refresh_components_list(select_component_id=added.component_id)

    def _on_edit_component(self) -> None:
        component_id = self._selected_component_id()
        if component_id is None:
            QMessageBox.information(None, "No Component Selected", "Select a component to edit.")
            return
        component = self.context.components.get_component(component_id)
        dialog = AddEditComponentDialog(component=component)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.components.update_component(
            component_id, name=dialog.entered_name, category=dialog.entered_category,
            value=dialog.entered_value, package=dialog.entered_package, quantity=dialog.entered_quantity,
            location=dialog.entered_location, notes=dialog.entered_notes,
        )
        self._refresh_components_list(select_component_id=component_id)

    def _on_delete_component(self) -> None:
        component_id = self._selected_component_id()
        if component_id is None:
            QMessageBox.information(None, "No Component Selected", "Select a component to delete.")
            return
        component = self.context.components.get_component(component_id)
        confirm = QMessageBox.question(
            None, "Delete Component", f"Delete '{component.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.components.delete_component(component_id)
        self._refresh_components_list()

    # ------------------------------------------------------------------
    # Materials tab
    # ------------------------------------------------------------------

    def _build_materials_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._material_filter_edit = QLineEdit()
        self._material_filter_edit.setPlaceholderText("Filter by name, supplier, or location…")
        self._material_filter_edit.textChanged.connect(lambda _text: self._refresh_materials_list())
        layout.addWidget(self._material_filter_edit)

        self._material_list = QListWidget()
        self._material_list.currentItemChanged.connect(lambda *_: self._update_material_detail_label())
        layout.addWidget(self._material_list, stretch=1)

        # Multi-user pass (2026-09-14) — same "shared object + user
        # relationship" surfacing as the Components tab's own detail
        # label above; no quick-adjust buttons here, see
        # format_material_detail_line()'s own docstring for why.
        self._material_detail_label = QLabel("")
        self._material_detail_label.setObjectName("SubtitleLabel")
        self._material_detail_label.setWordWrap(True)
        layout.addWidget(self._material_detail_label)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Material")
        add_button.clicked.connect(self._on_add_material)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_material)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_material)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_materials_list()
        return tab

    def _refresh_materials_list(self, select_material_id: Optional[str] = None) -> None:
        query = self._material_filter_edit.text().strip()
        materials = self.context.materials.search(query) if query else self.context.materials.all_materials()

        self._material_list.clear()
        for material in materials:
            item = QListWidgetItem(format_material_row(material))
            item.setData(Qt.ItemDataRole.UserRole, material.material_id)
            self._material_list.addItem(item)
            if material.material_id == select_material_id:
                self._material_list.setCurrentItem(item)
        self._update_material_detail_label()

    def _selected_material_id(self) -> Optional[str]:
        item = self._material_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _update_material_detail_label(self) -> None:
        material_id = self._selected_material_id()
        if material_id is None:
            self._material_detail_label.setText("")
            return

        material = self.context.materials.get_material(material_id)
        if material is None:
            self._material_detail_label.setText("")
            return

        added_by_name = self._profile_name(material.added_by_profile_id)
        times_used = self.context.materials.times_used(material_id)
        last_used_entry = self.context.materials.last_used(material_id)
        last_used_by_name = self._profile_name(last_used_entry.profile_id) if last_used_entry else None
        last_used_date = last_used_entry.timestamp[:10] if last_used_entry else None

        self._material_detail_label.setText(
            format_material_detail_line(added_by_name, times_used, last_used_by_name, last_used_date)
        )

    def _on_add_material(self) -> None:
        dialog = AddEditMaterialDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        added = self.context.materials.add_material(
            name=dialog.entered_name, unit=dialog.entered_unit, unit_cost=dialog.entered_unit_cost,
            quantity_on_hand=dialog.entered_quantity_on_hand, reorder_threshold=dialog.entered_reorder_threshold,
            supplier=dialog.entered_supplier, location=dialog.entered_location, notes=dialog.entered_notes,
        )
        self._refresh_materials_list(select_material_id=added.material_id)

    def _on_edit_material(self) -> None:
        material_id = self._selected_material_id()
        if material_id is None:
            QMessageBox.information(None, "No Material Selected", "Select a material to edit.")
            return
        material = self.context.materials.get_material(material_id)
        dialog = AddEditMaterialDialog(material=material)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.materials.update_material(
            material_id, name=dialog.entered_name, unit=dialog.entered_unit, unit_cost=dialog.entered_unit_cost,
            quantity_on_hand=dialog.entered_quantity_on_hand, reorder_threshold=dialog.entered_reorder_threshold,
            supplier=dialog.entered_supplier, location=dialog.entered_location, notes=dialog.entered_notes,
        )
        self._refresh_materials_list(select_material_id=material_id)

    def _on_delete_material(self) -> None:
        material_id = self._selected_material_id()
        if material_id is None:
            QMessageBox.information(None, "No Material Selected", "Select a material to delete.")
            return
        material = self.context.materials.get_material(material_id)
        confirm = QMessageBox.question(
            None, "Delete Material", f"Delete '{material.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.materials.delete_material(material_id)
        self._refresh_materials_list()

    # ------------------------------------------------------------------
    # Jobs tab
    # ------------------------------------------------------------------

    def _build_jobs_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._job_filter_edit = QLineEdit()
        self._job_filter_edit.setPlaceholderText("Filter by name, description, or notes…")
        self._job_filter_edit.textChanged.connect(lambda _text: self._refresh_jobs_list())
        layout.addWidget(self._job_filter_edit)

        self._job_list = QListWidget()
        layout.addWidget(self._job_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Job")
        add_button.clicked.connect(self._on_add_job)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_job)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_job)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        action_row = QHBoxLayout()
        consume_button = QPushButton("Consume Material…")
        consume_button.clicked.connect(self._on_consume_material)
        action_row.addWidget(consume_button)

        produce_button = QPushButton("Produce Product…")
        produce_button.clicked.connect(self._on_produce_product)
        action_row.addWidget(produce_button)

        layout.addLayout(action_row)

        self._refresh_jobs_list()
        return tab

    def _refresh_jobs_list(self) -> None:
        query = self._job_filter_edit.text().strip()
        jobs = self.context.jobs.search(query) if query else self.context.jobs.all_jobs()

        self._job_list.clear()
        for job in jobs:
            cost = self.context.jobs.total_cost(job.job_id)
            line = format_job_row(job)
            if cost is not None:
                line += f"  —  cost: ${cost:.2f}"
            item = QListWidgetItem(line)
            item.setData(Qt.ItemDataRole.UserRole, job.job_id)
            self._job_list.addItem(item)

    def _selected_job_id(self) -> Optional[str]:
        item = self._job_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_add_job(self) -> None:
        dialog = AddEditJobDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.jobs.add_job(
            name=dialog.entered_name, description=dialog.entered_description, status=dialog.entered_status,
            labor_hours=dialog.entered_labor_hours, notes=dialog.entered_notes,
        )
        self._refresh_jobs_list()

    def _on_edit_job(self) -> None:
        job_id = self._selected_job_id()
        if job_id is None:
            QMessageBox.information(None, "No Job Selected", "Select a job to edit.")
            return
        job = self.context.jobs.get_job(job_id)
        dialog = AddEditJobDialog(job=job)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.jobs.update_job(
            job_id, name=dialog.entered_name, description=dialog.entered_description,
            status=dialog.entered_status, labor_hours=dialog.entered_labor_hours, notes=dialog.entered_notes,
        )
        self._refresh_jobs_list()

    def _on_delete_job(self) -> None:
        job_id = self._selected_job_id()
        if job_id is None:
            QMessageBox.information(None, "No Job Selected", "Select a job to delete.")
            return
        job = self.context.jobs.get_job(job_id)
        confirm = QMessageBox.question(
            None, "Delete Job", f"Delete '{job.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.jobs.delete_job(job_id)
        self._refresh_jobs_list()

    def _on_consume_material(self) -> None:
        job_id = self._selected_job_id()
        if job_id is None:
            QMessageBox.information(None, "No Job Selected", "Select a job first.")
            return
        materials = self.context.materials.all_materials()
        if not materials:
            QMessageBox.information(None, "No Materials", "Add a material first.")
            return
        items = [(m.material_id, f"{m.name} ({m.quantity_on_hand:g} {m.unit or 'on hand'})") for m in materials]
        dialog = PickItemQuantityDialog(
            title="Consume Material", item_label="Material:", items=items, quantity_label="Quantity Used:",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.jobs.consume_material(job_id, dialog.entered_item_id, dialog.entered_quantity)
        self._refresh_jobs_list()
        self._refresh_materials_list()

    def _on_produce_product(self) -> None:
        job_id = self._selected_job_id()
        if job_id is None:
            QMessageBox.information(None, "No Job Selected", "Select a job first.")
            return
        products = self.context.products.all_products()
        if not products:
            QMessageBox.information(None, "No Products", "Add a product first.")
            return
        items = [(p.product_id, f"{p.name} ({p.quantity_in_stock:g} in stock)") for p in products]
        dialog = PickItemQuantityDialog(
            title="Produce Product", item_label="Product:", items=items, quantity_label="Quantity Produced:",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.jobs.produce_product(job_id, dialog.entered_item_id, dialog.entered_quantity)
        self._refresh_jobs_list()
        self._refresh_products_list()

    # ------------------------------------------------------------------
    # Products tab
    # ------------------------------------------------------------------

    def _build_products_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._product_filter_edit = QLineEdit()
        self._product_filter_edit.setPlaceholderText("Filter by name, description, or notes…")
        self._product_filter_edit.textChanged.connect(lambda _text: self._refresh_products_list())
        layout.addWidget(self._product_filter_edit)

        self._product_list = QListWidget()
        self._product_list.currentItemChanged.connect(lambda *_: self._update_product_detail_label())
        layout.addWidget(self._product_list, stretch=1)

        # Multi-user pass (2026-09-14) — same "shared object + user
        # relationship" surfacing as the Components/Materials tabs' own
        # detail labels; no quick-adjust buttons here either, see
        # format_product_detail_line()'s own docstring for why.
        self._product_detail_label = QLabel("")
        self._product_detail_label.setObjectName("SubtitleLabel")
        self._product_detail_label.setWordWrap(True)
        layout.addWidget(self._product_detail_label)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Product")
        add_button.clicked.connect(self._on_add_product)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_product)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_product)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        listing_row = QHBoxLayout()
        add_listing_button = QPushButton("Add Listing…")
        add_listing_button.clicked.connect(self._on_add_listing)
        listing_row.addWidget(add_listing_button)

        remove_listing_button = QPushButton("Remove Last Listing")
        remove_listing_button.clicked.connect(self._on_remove_listing)
        listing_row.addWidget(remove_listing_button)

        layout.addLayout(listing_row)

        self._refresh_products_list()
        return tab

    def _refresh_products_list(self, select_product_id: Optional[str] = None) -> None:
        query = self._product_filter_edit.text().strip()
        products = self.context.products.search(query) if query else self.context.products.all_products()

        self._product_list.clear()
        for product in products:
            item = QListWidgetItem(format_product_row(product))
            item.setData(Qt.ItemDataRole.UserRole, product.product_id)
            self._product_list.addItem(item)
            if product.product_id == select_product_id:
                self._product_list.setCurrentItem(item)
        self._update_product_detail_label()

    def _selected_product_id(self) -> Optional[str]:
        item = self._product_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _update_product_detail_label(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            self._product_detail_label.setText("")
            return

        product = self.context.products.get_product(product_id)
        if product is None:
            self._product_detail_label.setText("")
            return

        added_by_name = self._profile_name(product.added_by_profile_id)
        times_sold = self.context.products.times_sold(product_id)
        last_sold_entry = self.context.products.last_sold(product_id)
        last_sold_by_name = self._profile_name(last_sold_entry.profile_id) if last_sold_entry else None
        last_sold_date = last_sold_entry.timestamp[:10] if last_sold_entry else None

        self._product_detail_label.setText(
            format_product_detail_line(added_by_name, times_sold, last_sold_by_name, last_sold_date)
        )

    def _on_add_product(self) -> None:
        dialog = AddEditProductDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        added = self.context.products.add_product(
            name=dialog.entered_name, description=dialog.entered_description,
            quantity_in_stock=dialog.entered_quantity_in_stock, base_price=dialog.entered_base_price,
            notes=dialog.entered_notes,
        )
        self._refresh_products_list(select_product_id=added.product_id)

    def _on_edit_product(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            QMessageBox.information(None, "No Product Selected", "Select a product to edit.")
            return
        product = self.context.products.get_product(product_id)
        dialog = AddEditProductDialog(product=product)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.products.update_product(
            product_id, name=dialog.entered_name, description=dialog.entered_description,
            quantity_in_stock=dialog.entered_quantity_in_stock, base_price=dialog.entered_base_price,
            notes=dialog.entered_notes,
        )
        self._refresh_products_list(select_product_id=product_id)

    def _on_delete_product(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            QMessageBox.information(None, "No Product Selected", "Select a product to delete.")
            return
        product = self.context.products.get_product(product_id)
        confirm = QMessageBox.question(
            None, "Delete Product", f"Delete '{product.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.products.delete_product(product_id)
        self._refresh_products_list()

    def _on_add_listing(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            QMessageBox.information(None, "No Product Selected", "Select a product first.")
            return
        dialog = AddListingDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.products.add_listing(
            product_id, platform=dialog.entered_platform, price=dialog.entered_price,
            status=dialog.entered_status, url=dialog.entered_url,
        )
        self._refresh_products_list()

    def _on_remove_listing(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            QMessageBox.information(None, "No Product Selected", "Select a product first.")
            return
        product = self.context.products.get_product(product_id)
        if not product.listings:
            QMessageBox.information(None, "No Listings", f"'{product.name}' has no listings to remove.")
            return
        last_listing = product.listings[-1]
        confirm = QMessageBox.question(
            None, "Remove Listing", f"Remove the '{last_listing.platform}' listing from '{product.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.products.remove_listing(product_id, last_listing.listing_id)
        self._refresh_products_list()

    # ------------------------------------------------------------------
    # Ledger tab
    # ------------------------------------------------------------------

    def _build_ledger_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._net_profit_label = QLabel("")
        self._net_profit_label.setObjectName("SubtitleLabel")
        layout.addWidget(self._net_profit_label)

        layout.addWidget(QLabel("Revenue"))
        self._revenue_list = QListWidget()
        layout.addWidget(self._revenue_list, stretch=1)

        revenue_button_row = QHBoxLayout()
        add_revenue_button = QPushButton("Add Revenue…")
        add_revenue_button.clicked.connect(self._on_add_revenue)
        revenue_button_row.addWidget(add_revenue_button)

        record_sale_button = QPushButton("Record Sale…")
        record_sale_button.clicked.connect(self._on_record_sale)
        revenue_button_row.addWidget(record_sale_button)

        delete_revenue_button = QPushButton("Delete Selected Revenue")
        delete_revenue_button.clicked.connect(self._on_delete_revenue)
        revenue_button_row.addWidget(delete_revenue_button)

        layout.addLayout(revenue_button_row)

        layout.addWidget(QLabel("Expenses"))
        self._expense_list = QListWidget()
        layout.addWidget(self._expense_list, stretch=1)

        expense_button_row = QHBoxLayout()
        add_expense_button = QPushButton("Add Expense…")
        add_expense_button.clicked.connect(self._on_add_expense)
        expense_button_row.addWidget(add_expense_button)

        delete_expense_button = QPushButton("Delete Selected Expense")
        delete_expense_button.clicked.connect(self._on_delete_expense)
        expense_button_row.addWidget(delete_expense_button)

        layout.addLayout(expense_button_row)

        self._refresh_ledger()
        return tab

    def _refresh_ledger(self) -> None:
        self._net_profit_label.setText(
            f"Net Profit: ${self.context.ledger.net_profit():.2f}  "
            f"(Revenue ${self.context.ledger.total_revenue():.2f}  —  "
            f"Expenses ${self.context.ledger.total_expenses():.2f})"
        )

        self._revenue_list.clear()
        for entry in self.context.ledger.all_revenue():
            item = QListWidgetItem(format_revenue_row(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            self._revenue_list.addItem(item)

        self._expense_list.clear()
        for entry in self.context.ledger.all_expenses():
            item = QListWidgetItem(format_expense_row(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            self._expense_list.addItem(item)

    def _selected_revenue_id(self) -> Optional[str]:
        item = self._revenue_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _selected_expense_id(self) -> Optional[str]:
        item = self._expense_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_add_revenue(self) -> None:
        dialog = AddRevenueDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.ledger.add_revenue(
            amount=dialog.entered_amount, description=dialog.entered_description, notes=dialog.entered_notes,
        )
        self._refresh_ledger()

    def _on_record_sale(self) -> None:
        products = self.context.products.all_products()
        if not products:
            QMessageBox.information(None, "No Products", "Add a product first.")
            return
        items = [(p.product_id, f"{p.name} (${p.base_price:.2f} base)") for p in products]
        dialog = PickItemQuantityDialog(
            title="Record Sale", item_label="Product:", items=items, quantity_label="Quantity Sold:",
            include_amount=True, amount_label="Sale Amount ($):",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.ledger.record_sale(
            dialog.entered_item_id, quantity_sold=dialog.entered_quantity, amount=dialog.entered_amount,
        )
        self._refresh_ledger()
        self._refresh_products_list()

    def _on_delete_revenue(self) -> None:
        entry_id = self._selected_revenue_id()
        if entry_id is None:
            QMessageBox.information(None, "No Entry Selected", "Select a revenue entry to delete.")
            return
        self.context.ledger.delete_revenue(entry_id)
        self._refresh_ledger()

    def _on_add_expense(self) -> None:
        dialog = AddExpenseDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.ledger.add_expense(
            amount=dialog.entered_amount, category=dialog.entered_category,
            description=dialog.entered_description, notes=dialog.entered_notes,
        )
        self._refresh_ledger()

    def _on_delete_expense(self) -> None:
        entry_id = self._selected_expense_id()
        if entry_id is None:
            QMessageBox.information(None, "No Entry Selected", "Select an expense entry to delete.")
            return
        self.context.ledger.delete_expense(entry_id)
        self._refresh_ledger()
