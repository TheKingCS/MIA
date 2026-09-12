"""
modules.kitchen.module
=========================

Kitchen: recipes, a pantry/inventory list, a grocery list, a meal log,
and suggestions — which recipes are makeable right now from what's in
the pantry, and adding a recipe's missing ingredients to the grocery
list in one action. All persistence/reporting logic lives in
core/kitchen_manager.py (self.context.kitchen) — this module is the
Qt-facing wrapper around it, same split as every other data-backed
module here.

Five tabs (Recipes, Pantry, Grocery List, Meal Log, Suggestions),
QTabWidget, same shape as modules/budget/module.py. The Recipes tab is
itself a `QStackedWidget` list↔detail page (mirrors
modules/real_estate/module.py's exact pattern) — reopening a recipe
shouldn't feel like leaving and re-entering the module. Ingredient
editing on the detail page opens gui/add_edit_ingredient_dialog.py one
ingredient at a time (the real gui/pick_item_quantity_dialog.py
precedent — see that dialog's own docstring — not an embedded
multi-row table editor).

Since Pantry/Grocery List/Meal Log changes affect what the Suggestions
tab (and the Recipes detail page's own "missing ingredients" list)
shows, every tab is refreshed on every tab switch
(`tabs.currentChanged`) — same fix, and same reasoning, as the
Summary/Trends staleness fix just shipped in modules/budget/module.py
this session: all of these are cheap in-memory recomputations over
already-loaded data, so there's no real cost to always refreshing
rather than trying to track which tab needs it.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.kitchen_manager import (
    GroceryListItem,
    MealLogEntry,
    PantryItem,
    Recipe,
    days_until_expiration,
)
from gui.add_edit_grocery_item_dialog import AddEditGroceryItemDialog
from gui.add_edit_ingredient_dialog import AddEditIngredientDialog
from gui.add_edit_pantry_item_dialog import AddEditPantryItemDialog
from gui.add_edit_recipe_dialog import AddEditRecipeDialog
from gui.list_widget_helpers import add_empty_state_item, selected_item_data
from gui.log_meal_dialog import LogMealDialog
from modules.module_base import ModuleBase


def format_recipe_row(recipe: Recipe) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_kitchen_module.py).
    A locked recipe uses a plain-ASCII "(Locked)" prefix, same
    modules/skills/module.py.format_locked_skill_name() convention —
    that function's own docstring explains why: a real, reproduced
    font-fallback bug with the lock emoji, not a style choice."""
    prefix = "(Locked) " if recipe.locked else ""
    time_part = f"  {recipe.prep_time_minutes + recipe.cook_time_minutes} min" if recipe.prep_time_minutes or recipe.cook_time_minutes else ""
    return f"{prefix}{recipe.name}   [{recipe.category}]   {recipe.servings} servings{time_part}"


def format_pantry_row(item: PantryItem, today: date) -> str:
    """Pure formatting logic — testable without Qt. Same [OVERDUE Nd]/
    [DUE TODAY]/[DUE IN Nd] shape modules.budget.module.format_bill_row()
    already established, retargeted to expiration."""
    remaining = days_until_expiration(item, today)
    if remaining is None:
        status = ""
    elif remaining < 0:
        status = f"[EXPIRED {-remaining}d]  "
    elif remaining == 0:
        status = "[EXPIRES TODAY]  "
    else:
        status = f"[EXPIRES IN {remaining}d]  "
    quantity_part = f"{item.quantity:g} {item.unit}".strip() if item.quantity else ""
    return f"{status}{item.name}   {quantity_part}  [{item.category}]"


def format_grocery_row(item: GroceryListItem) -> str:
    """Pure formatting logic — testable without Qt."""
    quantity_part = f"{item.quantity:g} {item.unit}".strip() if item.quantity else ""
    source_part = "  (from recipe)" if item.source_recipe_id else ""
    return f"{item.name}   {quantity_part}{source_part}"


def format_meal_log_row(entry: MealLogEntry, recipe_name: str) -> str:
    """Pure formatting logic — testable without Qt."""
    notes_part = f"  {entry.notes}" if entry.notes else ""
    return f"{entry.date}   {recipe_name}{notes_part}"


def format_suggestion_row(recipe: Recipe, missing: list[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    if not missing:
        return f"✓ {recipe.name} — ready to make"
    return f"{recipe.name} — missing: {', '.join(missing)}"


class KitchenModule(ModuleBase):
    module_id = "kitchen"
    display_name = "Kitchen"
    description = "Recipes, pantry, grocery list, and meal tracking."
    icon = "\U0001F373"  # cooking

    def __init__(self, context) -> None:
        super().__init__(context)
        # Recipes tab — list<->detail QStackedWidget, mirrors
        # modules/real_estate/module.py exactly.
        self._recipes_stack: Optional[QStackedWidget] = None
        self._recipe_list_page: Optional[QWidget] = None
        self._recipe_detail_page: Optional[QWidget] = None
        self._recipe_list: Optional[QListWidget] = None
        self._detail_recipe_id: Optional[str] = None
        self._detail_ingredients_list: Optional[QListWidget] = None

        self._pantry_list: Optional[QListWidget] = None
        self._grocery_list_widget: Optional[QListWidget] = None
        self._meal_log_list: Optional[QListWidget] = None
        self._suggestions_list: Optional[QListWidget] = None

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
        tabs.addTab(self._build_recipes_tab(), "Recipes")
        tabs.addTab(self._build_pantry_tab(), "Pantry")
        tabs.addTab(self._build_grocery_tab(), "Grocery List")
        tabs.addTab(self._build_meal_log_tab(), "Meal Log")
        tabs.addTab(self._build_suggestions_tab(), "Suggestions")
        tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(tabs, stretch=1)

        return widget

    def _on_tab_changed(self, index: int) -> None:
        self._refresh_recipe_list()
        self._refresh_pantry_list()
        self._refresh_grocery_list()
        self._refresh_meal_log_list()
        self._refresh_suggestions_list()

    # ------------------------------------------------------------------
    # Recipes tab — list page
    # ------------------------------------------------------------------

    def _build_recipes_tab(self) -> QWidget:
        self._recipes_stack = QStackedWidget()
        self._recipe_list_page = self._build_recipe_list_page()
        self._recipes_stack.addWidget(self._recipe_list_page)
        self._recipes_stack.setCurrentWidget(self._recipe_list_page)
        return self._recipes_stack

    def _build_recipe_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._recipe_list = QListWidget()
        layout.addWidget(self._recipe_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Recipe")
        add_button.clicked.connect(self._on_add_recipe)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_recipe)
        button_row.addWidget(edit_button)

        details_button = QPushButton("View Details")
        details_button.clicked.connect(self._on_view_recipe_details)
        button_row.addWidget(details_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_recipe)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        self._refresh_recipe_list()
        return page

    def _refresh_recipe_list(self) -> None:
        if self._recipe_list is None:
            return
        self._recipe_list.clear()
        recipes = self.context.kitchen.all_recipes()
        for recipe in recipes:
            item = QListWidgetItem(format_recipe_row(recipe))
            item.setData(Qt.ItemDataRole.UserRole, recipe.recipe_id)
            self._recipe_list.addItem(item)
        if self._recipe_list.count() == 0:
            add_empty_state_item(self._recipe_list, "No recipes yet — click Add Recipe to get started.")

    def _selected_recipe_id(self) -> Optional[str]:
        return selected_item_data(self._recipe_list)

    def _on_add_recipe(self) -> None:
        dialog = AddEditRecipeDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.kitchen.add_recipe(
            name=dialog.entered_name,
            category=dialog.entered_category,
            servings=dialog.entered_servings,
            prep_time_minutes=dialog.entered_prep_time_minutes,
            cook_time_minutes=dialog.entered_cook_time_minutes,
            instructions=dialog.entered_instructions,
            calories_per_serving=dialog.entered_calories_per_serving,
            protein_g=dialog.entered_protein_g,
            carbs_g=dialog.entered_carbs_g,
            fat_g=dialog.entered_fat_g,
            source=dialog.entered_source,
            notes=dialog.entered_notes,
            locked=dialog.entered_locked,
        )
        self._refresh_recipe_list()

    def _on_edit_recipe(self) -> None:
        recipe_id = self._selected_recipe_id()
        if recipe_id is None:
            QMessageBox.information(None, "No Recipe Selected", "Select a recipe to edit.")
            return
        recipe = self.context.kitchen.get_recipe(recipe_id)
        dialog = AddEditRecipeDialog(recipe=recipe)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.kitchen.update_recipe(
            recipe_id,
            name=dialog.entered_name,
            category=dialog.entered_category,
            servings=dialog.entered_servings,
            prep_time_minutes=dialog.entered_prep_time_minutes,
            cook_time_minutes=dialog.entered_cook_time_minutes,
            instructions=dialog.entered_instructions,
            calories_per_serving=dialog.entered_calories_per_serving,
            protein_g=dialog.entered_protein_g,
            carbs_g=dialog.entered_carbs_g,
            fat_g=dialog.entered_fat_g,
            source=dialog.entered_source,
            notes=dialog.entered_notes,
            locked=dialog.entered_locked,
        )
        self._refresh_recipe_list()

    def _on_delete_recipe(self) -> None:
        recipe_id = self._selected_recipe_id()
        if recipe_id is None:
            QMessageBox.information(None, "No Recipe Selected", "Select a recipe to delete.")
            return
        self.context.kitchen.delete_recipe(recipe_id)
        self._refresh_recipe_list()

    def _on_view_recipe_details(self) -> None:
        recipe_id = self._selected_recipe_id()
        if recipe_id is None:
            QMessageBox.information(None, "No Recipe Selected", "Select a recipe to view.")
            return
        self._show_recipe_detail_page(recipe_id)

    # ------------------------------------------------------------------
    # Recipes tab — detail page
    # ------------------------------------------------------------------

    def _show_recipe_list_page(self) -> None:
        self._recipes_stack.setCurrentWidget(self._recipe_list_page)
        if self._recipe_detail_page is not None:
            self._recipes_stack.removeWidget(self._recipe_detail_page)
            self._recipe_detail_page = None
            self._detail_recipe_id = None
        self._refresh_recipe_list()

    def _show_recipe_detail_page(self, recipe_id: str) -> None:
        if self._recipe_detail_page is not None:
            self._recipes_stack.removeWidget(self._recipe_detail_page)
            self._recipe_detail_page = None

        self._detail_recipe_id = recipe_id
        self._recipe_detail_page = self._build_recipe_detail_page(recipe_id)
        self._recipes_stack.addWidget(self._recipe_detail_page)
        self._recipes_stack.setCurrentWidget(self._recipe_detail_page)

    def _build_recipe_detail_page(self, recipe_id: str) -> QWidget:
        recipe = self.context.kitchen.get_recipe(recipe_id)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        back_button = QPushButton("← Back to Recipes")
        back_button.clicked.connect(self._show_recipe_list_page)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        header = QLabel(recipe.name)
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        # "Recipe Unlocked" (2026-09-12) — the actual reward-withholding
        # this feature exists to provide: a locked recipe shows nothing
        # but its name and what unlocks it, real ingredients/
        # instructions/nutrition stay hidden until it's genuinely
        # unlocked. Derived live via _unlocking_mission_name() — nothing
        # new persisted for this lookup.
        if recipe.locked:
            locked_label = QLabel("\U0001F512 Locked")
            locked_label.setObjectName("SubtitleLabel")
            layout.addWidget(locked_label)
            mission_name = self._unlocking_mission_name(recipe_id)
            hint_text = (
                f"Complete the mission \"{mission_name}\" to unlock this recipe."
                if mission_name is not None
                else "Complete a mission to unlock this recipe."
            )
            hint_label = QLabel(hint_text)
            hint_label.setWordWrap(True)
            layout.addWidget(hint_label)
            layout.addStretch(1)
            return page

        time_total = recipe.prep_time_minutes + recipe.cook_time_minutes
        info_text = f"{recipe.category}   —   {recipe.servings} servings"
        if time_total:
            info_text += f"   —   {recipe.prep_time_minutes} min prep + {recipe.cook_time_minutes} min cook"
        info = QLabel(info_text)
        info.setWordWrap(True)
        layout.addWidget(info)

        if any(v is not None for v in (recipe.calories_per_serving, recipe.protein_g, recipe.carbs_g, recipe.fat_g)):
            parts = []
            if recipe.calories_per_serving is not None:
                parts.append(f"{recipe.calories_per_serving:g} cal")
            if recipe.protein_g is not None:
                parts.append(f"{recipe.protein_g:g}g protein")
            if recipe.carbs_g is not None:
                parts.append(f"{recipe.carbs_g:g}g carbs")
            if recipe.fat_g is not None:
                parts.append(f"{recipe.fat_g:g}g fat")
            nutrition = QLabel("Per serving: " + ", ".join(parts))
            nutrition.setObjectName("SubtitleLabel")
            layout.addWidget(nutrition)

        ingredients_title = QLabel("Ingredients")
        ingredients_title.setStyleSheet("font-weight: 600;")
        layout.addWidget(ingredients_title)

        self._detail_ingredients_list = QListWidget()
        self._detail_ingredients_list.setMaximumHeight(160)
        for ingredient in recipe.ingredients:
            quantity = ingredient.get("quantity") or 0.0
            unit = ingredient.get("unit", "")
            quantity_part = f"{quantity:g} {unit}".strip() if quantity else ""
            notes_part = f"  ({ingredient.get('notes')})" if ingredient.get("notes") else ""
            self._detail_ingredients_list.addItem(f"{ingredient.get('name', '')}   {quantity_part}{notes_part}")
        if self._detail_ingredients_list.count() == 0:
            add_empty_state_item(self._detail_ingredients_list, "No ingredients added yet.")
        layout.addWidget(self._detail_ingredients_list)

        ingredient_button_row = QHBoxLayout()
        add_ingredient_button = QPushButton("Add Ingredient…")
        add_ingredient_button.clicked.connect(lambda: self._on_add_ingredient(recipe_id))
        ingredient_button_row.addWidget(add_ingredient_button)
        remove_ingredient_button = QPushButton("Remove Selected")
        remove_ingredient_button.clicked.connect(lambda: self._on_remove_ingredient(recipe_id))
        ingredient_button_row.addWidget(remove_ingredient_button)
        layout.addLayout(ingredient_button_row)

        if recipe.instructions:
            instructions_title = QLabel("Instructions")
            instructions_title.setStyleSheet("font-weight: 600;")
            layout.addWidget(instructions_title)
            instructions_view = QTextEdit()
            instructions_view.setPlainText(recipe.instructions)
            instructions_view.setReadOnly(True)
            instructions_view.setMaximumHeight(140)
            layout.addWidget(instructions_view)

        last_made = self.context.kitchen.last_made_date(recipe_id)
        last_made_text = f"Last made: {last_made}" if last_made else "Never logged as made"
        last_made_label = QLabel(last_made_text)
        last_made_label.setObjectName("SubtitleLabel")
        layout.addWidget(last_made_label)

        log_meal_button = QPushButton("Log that I made this today")
        log_meal_button.clicked.connect(lambda: self._on_log_meal_today(recipe_id))
        layout.addWidget(log_meal_button, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch(1)
        return page

    def _unlocking_mission_name(self, recipe_id: str) -> Optional[str]:
        """Live reverse-lookup — the real, currently-active Mission (if
        any) whose recipe_unlocks names this recipe. Never a stale or
        fabricated name: None if no such Mission exists right now
        (already-completed/abandoned missions don't count — there's
        nothing left for the user to go do)."""
        if self.context.missions is None:
            return None
        for mission in self.context.missions.all_missions():
            if mission.status == "active" and recipe_id in mission.recipe_unlocks:
                return mission.name
        return None

    def _selected_ingredient_index(self) -> Optional[int]:
        item = self._detail_ingredients_list.currentItem()
        if item is None or not item.isSelected():
            return None
        return self._detail_ingredients_list.row(item)

    def _on_add_ingredient(self, recipe_id: str) -> None:
        dialog = AddEditIngredientDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.kitchen.add_ingredient(
            recipe_id, name=dialog.entered_name, quantity=dialog.entered_quantity,
            unit=dialog.entered_unit, notes=dialog.entered_notes,
        )
        self._show_recipe_detail_page(recipe_id)

    def _on_remove_ingredient(self, recipe_id: str) -> None:
        index = self._selected_ingredient_index()
        if index is None:
            QMessageBox.information(None, "No Ingredient Selected", "Select an ingredient to remove.")
            return
        self.context.kitchen.remove_ingredient(recipe_id, index)
        self._show_recipe_detail_page(recipe_id)

    def _on_log_meal_today(self, recipe_id: str) -> None:
        self.context.kitchen.log_meal(recipe_id, date.today().isoformat())
        self._show_recipe_detail_page(recipe_id)

    # ------------------------------------------------------------------
    # Pantry tab
    # ------------------------------------------------------------------

    def _build_pantry_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._pantry_list = QListWidget()
        layout.addWidget(self._pantry_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Pantry Item")
        add_button.clicked.connect(self._on_add_pantry_item)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_pantry_item)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_pantry_item)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        self._refresh_pantry_list()
        return tab

    def _refresh_pantry_list(self) -> None:
        if self._pantry_list is None:
            return
        self._pantry_list.clear()
        today = date.today()
        items = self.context.kitchen.all_pantry_items()
        for item in items:
            list_item = QListWidgetItem(format_pantry_row(item, today))
            list_item.setData(Qt.ItemDataRole.UserRole, item.item_id)
            self._pantry_list.addItem(list_item)
        if self._pantry_list.count() == 0:
            add_empty_state_item(self._pantry_list, "No pantry items tracked yet — click Add Pantry Item to get started.")

    def _selected_pantry_item_id(self) -> Optional[str]:
        return selected_item_data(self._pantry_list)

    def _on_add_pantry_item(self) -> None:
        dialog = AddEditPantryItemDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.kitchen.add_pantry_item(
            name=dialog.entered_name, quantity=dialog.entered_quantity, unit=dialog.entered_unit,
            category=dialog.entered_category, expiration_date=dialog.entered_expiration_date,
            notes=dialog.entered_notes,
        )
        self._refresh_pantry_list()

    def _on_edit_pantry_item(self) -> None:
        item_id = self._selected_pantry_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Item Selected", "Select a pantry item to edit.")
            return
        item = self.context.kitchen.get_pantry_item(item_id)
        dialog = AddEditPantryItemDialog(item=item)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.kitchen.update_pantry_item(
            item_id, name=dialog.entered_name, quantity=dialog.entered_quantity, unit=dialog.entered_unit,
            category=dialog.entered_category, expiration_date=dialog.entered_expiration_date,
            notes=dialog.entered_notes,
        )
        self._refresh_pantry_list()

    def _on_delete_pantry_item(self) -> None:
        item_id = self._selected_pantry_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Item Selected", "Select a pantry item to delete.")
            return
        self.context.kitchen.delete_pantry_item(item_id)
        self._refresh_pantry_list()

    # ------------------------------------------------------------------
    # Grocery List tab
    # ------------------------------------------------------------------

    def _build_grocery_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._grocery_list_widget = QListWidget()
        self._grocery_list_widget.itemChanged.connect(self._on_grocery_item_changed)
        layout.addWidget(self._grocery_list_widget, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Item")
        add_button.clicked.connect(self._on_add_grocery_item)
        button_row.addWidget(add_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_grocery_item)
        button_row.addWidget(delete_button)

        clear_button = QPushButton("Clear Checked Items")
        clear_button.clicked.connect(self._on_clear_checked_grocery_items)
        button_row.addWidget(clear_button)
        layout.addLayout(button_row)

        self._refresh_grocery_list()
        return tab

    def _refresh_grocery_list(self) -> None:
        if self._grocery_list_widget is None:
            return
        self._grocery_list_widget.blockSignals(True)
        self._grocery_list_widget.clear()
        items = self.context.kitchen.all_grocery_items()
        for item in items:
            list_item = QListWidgetItem(format_grocery_row(item))
            list_item.setData(Qt.ItemDataRole.UserRole, item.item_id)
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            list_item.setCheckState(Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked)
            self._grocery_list_widget.addItem(list_item)
        if self._grocery_list_widget.count() == 0:
            add_empty_state_item(self._grocery_list_widget, "Grocery list is empty.")
        self._grocery_list_widget.blockSignals(False)

    def _selected_grocery_item_id(self) -> Optional[str]:
        return selected_item_data(self._grocery_list_widget)

    def _on_grocery_item_changed(self, item: QListWidgetItem) -> None:
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            return
        self.context.kitchen.set_grocery_item_checked(item_id, item.checkState() == Qt.CheckState.Checked)

    def _on_add_grocery_item(self) -> None:
        dialog = AddEditGroceryItemDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.kitchen.add_grocery_item(
            name=dialog.entered_name, quantity=dialog.entered_quantity, unit=dialog.entered_unit,
        )
        self._refresh_grocery_list()

    def _on_delete_grocery_item(self) -> None:
        item_id = self._selected_grocery_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Item Selected", "Select a grocery item to delete.")
            return
        self.context.kitchen.delete_grocery_item(item_id)
        self._refresh_grocery_list()

    def _on_clear_checked_grocery_items(self) -> None:
        self.context.kitchen.clear_checked_grocery_items()
        self._refresh_grocery_list()

    # ------------------------------------------------------------------
    # Meal Log tab
    # ------------------------------------------------------------------

    def _build_meal_log_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._meal_log_list = QListWidget()
        layout.addWidget(self._meal_log_list, stretch=1)

        button_row = QHBoxLayout()
        log_button = QPushButton("Log a Meal")
        log_button.clicked.connect(self._on_log_meal)
        button_row.addWidget(log_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_meal_log_entry)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        self._refresh_meal_log_list()
        return tab

    def _refresh_meal_log_list(self) -> None:
        if self._meal_log_list is None:
            return
        self._meal_log_list.clear()
        entries = self.context.kitchen.all_meal_log_entries()
        for entry in entries:
            recipe = self.context.kitchen.get_recipe(entry.recipe_id)
            recipe_name = recipe.name if recipe is not None else "(deleted recipe)"
            item = QListWidgetItem(format_meal_log_row(entry, recipe_name))
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            self._meal_log_list.addItem(item)
        if self._meal_log_list.count() == 0:
            add_empty_state_item(self._meal_log_list, "No meals logged yet — click Log a Meal to get started.")

    def _selected_meal_log_entry_id(self) -> Optional[str]:
        return selected_item_data(self._meal_log_list)

    def _on_log_meal(self) -> None:
        recipes = self.context.kitchen.all_recipes()
        if not recipes:
            QMessageBox.information(None, "No Recipes Yet", "Add a recipe first, then log a meal against it.")
            return
        dialog = LogMealDialog(recipes=recipes)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.kitchen.log_meal(dialog.entered_recipe_id, dialog.entered_date, dialog.entered_notes)
        self._refresh_meal_log_list()

    def _on_delete_meal_log_entry(self) -> None:
        entry_id = self._selected_meal_log_entry_id()
        if entry_id is None:
            QMessageBox.information(None, "No Entry Selected", "Select a meal log entry to delete.")
            return
        self.context.kitchen.delete_meal_log_entry(entry_id)
        self._refresh_meal_log_list()

    # ------------------------------------------------------------------
    # Suggestions tab
    # ------------------------------------------------------------------

    def _build_suggestions_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        intro = QLabel("Recipes you can make right now, based on your pantry — fully makeable ones come first.")
        intro.setObjectName("SubtitleLabel")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._suggestions_list = QListWidget()
        layout.addWidget(self._suggestions_list, stretch=1)

        add_missing_button = QPushButton("Add Missing Ingredients to Grocery List")
        add_missing_button.clicked.connect(self._on_add_missing_to_grocery_list)
        layout.addWidget(add_missing_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self._refresh_suggestions_list()
        return tab

    def _refresh_suggestions_list(self) -> None:
        if self._suggestions_list is None:
            return
        self._suggestions_list.clear()
        results = self.context.kitchen.recipes_makeable_now()
        for recipe, missing in results:
            item = QListWidgetItem(format_suggestion_row(recipe, missing))
            item.setData(Qt.ItemDataRole.UserRole, recipe.recipe_id)
            self._suggestions_list.addItem(item)
        if self._suggestions_list.count() == 0:
            add_empty_state_item(self._suggestions_list, "No recipes tracked yet — add one in the Recipes tab.")

    def _on_add_missing_to_grocery_list(self) -> None:
        recipe_id = selected_item_data(self._suggestions_list)
        if recipe_id is None:
            QMessageBox.information(None, "No Recipe Selected", "Select a recipe to add its missing ingredients.")
            return
        added = self.context.kitchen.add_missing_ingredients_to_grocery_list(recipe_id)
        if added:
            QMessageBox.information(None, "Added to Grocery List", f"Added {len(added)} item(s) to the grocery list.")
        else:
            QMessageBox.information(None, "Nothing to Add", "Every missing ingredient is already on the grocery list.")
        self._refresh_grocery_list()
