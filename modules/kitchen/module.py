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

Five tabs (Recipes, Pantry, Grocery List, Meal Log, Suggestions) — a
plain button row + QStackedWidget (the "Nature" re-skin's own tab
convention, ported from modules/garage/module.py; not QTabWidget's own
unstyled default chrome). The Recipes tab is itself a second, nested
`QStackedWidget` list↔detail page (mirrors modules/real_estate/module.py's
exact pattern) — reopening a recipe shouldn't feel like leaving and
re-entering the module. Ingredient editing on the detail page opens
gui/add_edit_ingredient_dialog.py one ingredient at a time (the real
gui/pick_item_quantity_dialog.py precedent — see that dialog's own
docstring — not an embedded multi-row table editor).

**"Nature" re-skin rollout (2026-09-14)**: photo hero header + the
Garage/Greenhouse/Workout tab-bar convention. Every tab's own internal
content (recipe cards, pantry/grocery/meal-log lists) is unchanged
this pass — only the outer shell.

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
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
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
from gui.widgets.photo_background_frame import PhotoBackgroundFrame
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


def format_made_count_line(times_made: int) -> str:
    """Pure formatting logic — testable without Qt. Consolidates what
    used to be duplicated inline in two places (the recipe card and
    the detail page) — now a third real call site (multi-user pass,
    2026-09-14) for the per-profile "YOUR STATS" card justified
    actually extracting it."""
    return "Never made yet" if times_made == 0 else f"Made {times_made}x"


def format_last_made_line(last_made: Optional[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"Last made: {last_made}" if last_made else "Never logged as made"


def format_rating_line(rating: Optional[float]) -> str:
    """Pure formatting logic — testable without Qt. Multi-user pass
    (2026-09-14) — a real per-profile opinion, never a fabricated
    default rating."""
    return f"Your rating: {rating:g}/5" if rating is not None else "Not rated yet"


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
        self._recipe_list_layout: Optional[QVBoxLayout] = None
        self._detail_recipe_id: Optional[str] = None
        self._detail_ingredients_list: Optional[QListWidget] = None

        self._pantry_list: Optional[QListWidget] = None
        self._grocery_list_widget: Optional[QListWidget] = None
        self._meal_log_list: Optional[QListWidget] = None
        self._suggestions_list: Optional[QListWidget] = None

    def get_widget(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background-color: #070f0d;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(150)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 20, 28, 16)
        hero_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        icon_badge = QLabel(self.icon)
        icon_badge.setObjectName("NatureIconBadge")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(icon_badge)
        title = QLabel(self.display_name)
        title.setObjectName("NatureHeaderTitle")
        header_row.addWidget(title)
        header_row.addStretch(1)
        hero_layout.addLayout(header_row)

        tagline = QLabel(self.description)
        tagline.setObjectName("NatureHeaderTagline")
        hero_layout.addWidget(tagline)
        hero_layout.addStretch(1)

        outer.addWidget(hero)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 0)
        body_layout.setSpacing(12)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(24)
        stack = QStackedWidget()
        tab_pages = {
            "Recipes": self._build_recipes_tab(),
            "Pantry": self._build_pantry_tab(),
            "Grocery List": self._build_grocery_tab(),
            "Meal Log": self._build_meal_log_tab(),
            "Suggestions": self._build_suggestions_tab(),
        }
        tab_buttons: dict[str, QPushButton] = {}

        def _select_tab(name: str) -> None:
            for key, button in tab_buttons.items():
                button.setProperty("active", key == name)
                button.style().unpolish(button)
                button.style().polish(button)
            stack.setCurrentWidget(tab_pages[name])
            self._on_tab_changed(0)

        for name, tab_widget in tab_pages.items():
            button = QPushButton(name)
            button.setObjectName("NatureTabButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, n=name: _select_tab(n))
            tab_buttons[name] = button
            tab_row.addWidget(button)
            stack.addWidget(tab_widget)
        tab_row.addStretch(1)
        body_layout.addLayout(tab_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(stack)
        body_layout.addWidget(scroll, stretch=1)

        outer.addWidget(body, stretch=1)
        _select_tab("Recipes")
        return page

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
        """Nature re-skin, real reorganization (2026-09-14) — recipe
        cards (icon/lock-state thumbnail + name/category/servings/time,
        reusing format_recipe_row() verbatim) replacing the old
        QListWidget rows, matching the reference mockup's own recipe-
        card layout and Garage/Real Estate's established clickable-card
        pattern. Edit/Delete moved onto the recipe's own detail page —
        same reasoning as Real Estate's property cards."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        add_button = QPushButton("Add Recipe")
        add_button.clicked.connect(self._on_add_recipe)
        layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignLeft)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._recipe_list_layout = QVBoxLayout(content)
        self._recipe_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._recipe_list_layout.setSpacing(12)
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        self._refresh_recipe_list()
        return page

    def _refresh_recipe_list(self) -> None:
        if self._recipe_list_layout is None:
            return
        while self._recipe_list_layout.count():
            item = self._recipe_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        recipes = self.context.kitchen.all_recipes()
        if not recipes:
            empty = QLabel("No recipes yet — click Add Recipe to get started.")
            empty.setObjectName("NatureTileCaption")
            self._recipe_list_layout.addWidget(empty)
            return
        for recipe in recipes:
            self._recipe_list_layout.addWidget(self._build_recipe_row(recipe))

    def _build_recipe_row(self, recipe: Recipe) -> QWidget:
        """A recipe's clickable card plus a separate quick-log button
        (2026-09-14) — "a way to easily log meals like logging
        workouts": one click from the list, no need to open the
        detail page first. Kept as a sibling widget rather than nested
        inside the card's own QPushButton (a real click-handling risk
        — a button inside a button), matching how every other Nature
        list keeps its card a single, whole clickable region."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        row_layout.addWidget(self._build_recipe_card(recipe), stretch=1)

        if not recipe.locked:
            log_button = QPushButton("\U0001F373 Log")
            log_button.setToolTip(f"Log that you made {recipe.name} today")
            log_button.clicked.connect(lambda checked=False, rid=recipe.recipe_id: self._on_quick_log_meal(rid))
            row_layout.addWidget(log_button)

        return row

    def _build_recipe_card(self, recipe: Recipe) -> QPushButton:
        card = QPushButton()
        card.setObjectName("NatureAssetCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setToolTip(f"Open {recipe.name}")
        card.setMinimumHeight(80)
        card.clicked.connect(lambda checked=False, rid=recipe.recipe_id: self._show_recipe_detail_page(rid))
        outer = QHBoxLayout(card)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(14)

        thumb = QLabel("\U0001F512" if recipe.locked else "\U0001F37D")
        thumb.setObjectName("NatureIconBadge")
        if recipe.locked:
            thumb.setProperty("tone", "danger")
        thumb.setFixedSize(48, 48)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(thumb)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_label = QLabel(f"{format_recipe_row(recipe)}  ›")
        title_label.setObjectName("NatureAssetTitle")
        title_label.setWordWrap(True)
        text_col.addWidget(title_label)

        if not recipe.locked:
            # "Stat tracking how many times I've made each meal"
            # (2026-09-14) — real data, core.kitchen_manager.times_made()
            # already existed but was never surfaced anywhere in the UI.
            times_made = self.context.kitchen.times_made(recipe.recipe_id)
            made_label = QLabel(format_made_count_line(times_made))
            made_label.setObjectName("NatureTileCaption")
            text_col.addWidget(made_label)

        outer.addLayout(text_col, stretch=1)

        return card

    def _on_quick_log_meal(self, recipe_id: str) -> None:
        """Low-friction by design — no confirmation dialog; the
        card's own "Made Nx" count updating immediately is the
        feedback, same spirit as Workout's live counters."""
        self.context.kitchen.log_meal(recipe_id, date.today().isoformat())
        self._refresh_recipe_list()

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

    def _on_edit_recipe(self, recipe_id: str) -> None:
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
        self._show_recipe_detail_page(recipe_id)

    def _on_delete_recipe(self, recipe_id: str) -> None:
        self.context.kitchen.delete_recipe(recipe_id)
        self._show_recipe_list_page()

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
        """Nature re-skin, real reorganization (2026-09-14) — photo hero
        (Edit/Delete moved here, same reasoning as Real Estate's
        property detail page) + each section as its own #NatureAssetCard."""
        recipe = self.context.kitchen.get_recipe(recipe_id)

        page = QWidget()
        page.setStyleSheet("background-color: #070f0d;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(150)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 16, 28, 16)
        hero_layout.setSpacing(6)

        top_row = QHBoxLayout()
        back_button = QPushButton("← Back to Recipes")
        back_button.clicked.connect(self._show_recipe_list_page)
        top_row.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        top_row.addStretch(1)
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: self._on_edit_recipe(recipe_id))
        top_row.addWidget(edit_button)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self._on_delete_recipe(recipe_id))
        top_row.addWidget(delete_button)
        hero_layout.addLayout(top_row)

        title = QLabel(recipe.name)
        title.setObjectName("NatureHeaderTitle")
        hero_layout.addWidget(title)

        if not recipe.locked:
            time_total = recipe.prep_time_minutes + recipe.cook_time_minutes
            tagline_text = f"{recipe.category}   —   {recipe.servings} servings"
            if time_total:
                tagline_text += f"   —   {recipe.prep_time_minutes} min prep + {recipe.cook_time_minutes} min cook"
            tagline = QLabel(tagline_text)
            tagline.setObjectName("NatureHeaderTagline")
            hero_layout.addWidget(tagline)
        hero_layout.addStretch(1)

        outer.addWidget(hero)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # "Recipe Unlocked" (2026-09-12) — the actual reward-withholding
        # this feature exists to provide: a locked recipe shows nothing
        # but its name and what unlocks it, real ingredients/
        # instructions/nutrition stay hidden until it's genuinely
        # unlocked. Derived live via _unlocking_mission_name() — nothing
        # new persisted for this lookup.
        if recipe.locked:
            locked_card = QFrame()
            locked_card.setObjectName("NatureAttentionPanel")
            locked_layout = QVBoxLayout(locked_card)
            locked_layout.setContentsMargins(18, 16, 18, 16)
            locked_title = QLabel("\U0001F512 Locked")
            locked_title.setObjectName("NatureAttentionTitle")
            locked_layout.addWidget(locked_title)
            mission_name = self._unlocking_mission_name(recipe_id)
            hint_text = (
                f"Complete the mission \"{mission_name}\" to unlock this recipe."
                if mission_name is not None
                else "Complete a mission to unlock this recipe."
            )
            hint_label = QLabel(hint_text)
            hint_label.setObjectName("NatureAttentionLine")
            hint_label.setWordWrap(True)
            locked_layout.addWidget(hint_label)
            layout.addWidget(locked_card)
            layout.addStretch(1)
            scroll.setWidget(content)
            outer.addWidget(scroll, stretch=1)
            return page

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
            nutrition_card = QFrame()
            nutrition_card.setObjectName("NatureAssetCard")
            nutrition_layout = QVBoxLayout(nutrition_card)
            nutrition_layout.setContentsMargins(18, 16, 18, 16)
            nutrition = QLabel("Per serving: " + ", ".join(parts))
            nutrition.setObjectName("NatureAssetLine")
            nutrition_layout.addWidget(nutrition)
            layout.addWidget(nutrition_card)

        ingredients_card = QFrame()
        ingredients_card.setObjectName("NatureAssetCard")
        ingredients_layout = QVBoxLayout(ingredients_card)
        ingredients_layout.setContentsMargins(18, 16, 18, 16)
        ingredients_layout.setSpacing(6)
        ingredients_title = QLabel("Ingredients")
        ingredients_title.setObjectName("NatureSectionTitle")
        ingredients_layout.addWidget(ingredients_title)

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
        ingredients_layout.addWidget(self._detail_ingredients_list)

        ingredient_button_row = QHBoxLayout()
        add_ingredient_button = QPushButton("Add Ingredient…")
        add_ingredient_button.clicked.connect(lambda: self._on_add_ingredient(recipe_id))
        ingredient_button_row.addWidget(add_ingredient_button)
        remove_ingredient_button = QPushButton("Remove Selected")
        remove_ingredient_button.clicked.connect(lambda: self._on_remove_ingredient(recipe_id))
        ingredient_button_row.addWidget(remove_ingredient_button)
        ingredients_layout.addLayout(ingredient_button_row)
        layout.addWidget(ingredients_card)

        if recipe.instructions:
            instructions_card = QFrame()
            instructions_card.setObjectName("NatureAssetCard")
            instructions_layout = QVBoxLayout(instructions_card)
            instructions_layout.setContentsMargins(18, 16, 18, 16)
            instructions_layout.setSpacing(6)
            instructions_title = QLabel("Instructions")
            instructions_title.setObjectName("NatureSectionTitle")
            instructions_layout.addWidget(instructions_title)
            instructions_view = QTextEdit()
            instructions_view.setPlainText(recipe.instructions)
            instructions_view.setReadOnly(True)
            instructions_view.setMaximumHeight(140)
            instructions_layout.addWidget(instructions_view)
            layout.addWidget(instructions_card)

        last_made_card = QFrame()
        last_made_card.setObjectName("NatureAssetCard")
        last_made_layout = QVBoxLayout(last_made_card)
        last_made_layout.setContentsMargins(18, 16, 18, 16)
        last_made_layout.setSpacing(8)
        # Multi-user pass (2026-09-14) — this card is the HOUSEHOLD
        # total (every profile's meals, unfiltered); see the new "YOUR
        # STATS" card below for the active profile's own relationship
        # to this recipe (the [[project_mia_multiuser_vision]] handoff's
        # own "shared object + user relationship" pattern).
        household_title = QLabel("HOUSEHOLD")
        household_title.setObjectName("NatureSectionTitle")
        last_made_layout.addWidget(household_title)
        times_made = self.context.kitchen.times_made(recipe_id)
        made_count_label = QLabel(format_made_count_line(times_made))
        made_count_label.setObjectName("NatureAssetLine")
        last_made_layout.addWidget(made_count_label)
        last_made = self.context.kitchen.last_made_date(recipe_id)
        last_made_label = QLabel(format_last_made_line(last_made))
        last_made_label.setObjectName("NatureTileCaption")
        last_made_layout.addWidget(last_made_label)

        log_meal_button = QPushButton("Log that I made this today")
        log_meal_button.clicked.connect(lambda: self._on_log_meal_today(recipe_id))
        last_made_layout.addWidget(log_meal_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(last_made_card)

        your_stats_card = self._build_your_recipe_stats_card(recipe_id)
        if your_stats_card is not None:
            layout.addWidget(your_stats_card)

        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)
        return page

    def _build_your_recipe_stats_card(self, recipe_id: str) -> Optional[QFrame]:
        """The active profile's own relationship to this shared recipe
        (2026-09-14 multi-user pass) — times made, last made, rating,
        favorite, personal notes, all editable and scoped to whoever's
        actually logged in. None with no active profile (same "degrade
        gracefully" stance every other profile-aware card in this app
        takes) — there's no "you" to show stats for."""
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        if active_profile is None:
            return None

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(8)
        title = QLabel("YOUR STATS")
        title.setObjectName("NatureSectionTitle")
        card_layout.addWidget(title)

        your_times_made = self.context.kitchen.times_made(recipe_id, profile_id=active_profile.profile_id)
        made_label = QLabel(format_made_count_line(your_times_made))
        made_label.setObjectName("NatureAssetLine")
        card_layout.addWidget(made_label)

        your_last_made = self.context.kitchen.last_made_date(recipe_id, profile_id=active_profile.profile_id)
        last_made_label = QLabel(format_last_made_line(your_last_made))
        last_made_label.setObjectName("NatureTileCaption")
        card_layout.addWidget(last_made_label)

        user_stats = self.context.kitchen.get_recipe_user_stats(active_profile.profile_id, recipe_id)

        rating_row = QHBoxLayout()
        rating_label = QLabel("Your rating:")
        rating_row.addWidget(rating_label)
        rating_combo = QComboBox()
        rating_combo.addItem("Not rated", None)
        for value in (1.0, 2.0, 3.0, 4.0, 5.0):
            rating_combo.addItem(f"{value:g}/5", value)
        if user_stats.rating is not None:
            index = rating_combo.findData(user_stats.rating)
            if index >= 0:
                rating_combo.setCurrentIndex(index)
        rating_row.addWidget(rating_combo)
        rating_row.addStretch(1)
        card_layout.addLayout(rating_row)

        favorite_checkbox = QCheckBox("Favorite")
        favorite_checkbox.setChecked(user_stats.favorite)
        card_layout.addWidget(favorite_checkbox)

        notes_field = QLineEdit(user_stats.personal_notes)
        notes_field.setPlaceholderText("Your personal notes (e.g. \"add more carrots\")")
        card_layout.addWidget(notes_field)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self._on_save_recipe_user_stats(
            recipe_id, active_profile.profile_id, rating_combo, favorite_checkbox, notes_field,
        ))
        card_layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignLeft)

        return card

    def _on_save_recipe_user_stats(
        self, recipe_id: str, profile_id: str, rating_combo: QComboBox, favorite_checkbox: QCheckBox, notes_field: QLineEdit,
    ) -> None:
        self.context.kitchen.set_recipe_rating(profile_id, recipe_id, rating_combo.currentData())
        self.context.kitchen.set_recipe_favorite(profile_id, recipe_id, favorite_checkbox.isChecked())
        self.context.kitchen.set_recipe_personal_notes(profile_id, recipe_id, notes_field.text())
        self._show_recipe_detail_page(recipe_id)

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
        """Nature re-skin (2026-09-14) — a bordered #NatureAssetCard
        titled "Pantry" around the existing QListWidget, matching how
        the reference mockup shows Pantry as its own boxed section.
        The list/selection/Edit/Delete interaction is unchanged — a
        pantry item has no detail page to click into, unlike Recipes."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 12, 0, 12)

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Pantry")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

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

        page_layout.addWidget(card, stretch=1)
        self._refresh_pantry_list()
        return page

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
        """Nature re-skin (2026-09-14) — boxed #NatureAssetCard titled
        "Grocery List", matching the reference mockup; the checkable-
        item interaction underneath is unchanged."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 12, 0, 12)

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Grocery List")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

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

        page_layout.addWidget(card, stretch=1)
        self._refresh_grocery_list()
        return page

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
        """Nature re-skin (2026-09-14) — boxed #NatureAssetCard titled
        "Meal Log", same treatment as Pantry/Grocery."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 12, 0, 12)

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Meal Log")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

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

        page_layout.addWidget(card, stretch=1)
        self._refresh_meal_log_list()
        return page

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
        """Nature re-skin (2026-09-14) — boxed #NatureAssetCard titled
        "Suggestions", same treatment as Pantry/Grocery/Meal Log."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 12, 0, 12)

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Suggestions")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

        intro = QLabel("Recipes you can make right now, based on your pantry — fully makeable ones come first.")
        intro.setObjectName("NatureTileCaption")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._suggestions_list = QListWidget()
        layout.addWidget(self._suggestions_list, stretch=1)

        add_missing_button = QPushButton("Add Missing Ingredients to Grocery List")
        add_missing_button.clicked.connect(self._on_add_missing_to_grocery_list)
        layout.addWidget(add_missing_button, alignment=Qt.AlignmentFlag.AlignLeft)

        page_layout.addWidget(card, stretch=1)
        self._refresh_suggestions_list()
        return page

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
