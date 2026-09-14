"""
core.kitchen_manager
=======================

MIA's Kitchen Module — recipes, a pantry/inventory list, a grocery
list, and a meal log, plus the logic that connects them: which recipes
are makeable right now from what's in the pantry, and adding a
recipe's missing ingredients to the grocery list in one action.

Deliberately its own manager, not a reuse of core.inventory_manager.py
(the generic Toolbox Inventory tool) — same real reasoning
docs/ROADMAP.md's milestone 8.3 already gave for Workshop's own
component DB: "mixing kitchen supplies and resistor stock into one
list serves neither well." One manager, several related record types,
same shape as core.budget_manager.py (Bills/Income/Expenses/
IncomeSources/BudgetTargets all live in one file there too, rather
than one manager per concept).

Ingredients are plain dicts on Recipe.ingredients
({"name", "quantity", "unit", "notes"}), not a separate CRUD entity or
a nested dataclass — same "plain dict sub-structure" precedent
core.business_report.py's own composition functions already use.

Units are freeform strings ("cups", "lbs", "each", ...) — there is no
unit-conversion system. recipe_missing_ingredients() only compares
quantities when a pantry item's unit matches an ingredient's unit
exactly (case-insensitive); otherwise it falls back to a presence-only
check. Comparing quantities across mismatched units would be
fabricated precision, not a real answer — same honest boundary
core.real_estate_manager.annual_depreciation()'s own docstring draws
around its own real-but-approximate figure.

Nutrition facts (calories/protein/carbs/fat) are optional, manually
entered fields on Recipe — no USDA/nutrition-API lookup exists here,
same "manual entry now, real integration later" precedent as Energy
tracking and Real Estate's own manually-updated current_value.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.gamification import SkillWeight, grant_xp
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_RECIPES_FILE = _DATA_DIR / "kitchen_recipes.json"
_PANTRY_FILE = _DATA_DIR / "kitchen_pantry.json"
_GROCERY_LIST_FILE = _DATA_DIR / "kitchen_grocery_list.json"
_MEAL_LOG_FILE = _DATA_DIR / "kitchen_meal_log.json"
# Multi-user pass (2026-09-14) — the "shared object + user relationship"
# pattern's first real application (see the
# [[project_mia_multiuser_vision]] memory). Recipe/MealLogEntry stay
# shared/household; this file holds one RecipeUserStats row per real
# (profile_id, recipe_id) pair that's ever been rated/favorited/noted.
_RECIPE_USER_STATS_FILE = _DATA_DIR / "kitchen_recipe_user_stats.json"

RECIPE_CATEGORIES = ["Breakfast", "Lunch", "Dinner", "Dessert", "Snack", "Side", "Drink", "Other"]
PANTRY_CATEGORIES = [
    "Produce", "Dairy", "Meat", "Frozen", "Pantry/Dry Goods", "Spices", "Condiments", "Beverages", "Other",
]


@dataclass
class Recipe:
    recipe_id: str
    name: str
    category: str = "Dinner"  # one of RECIPE_CATEGORIES
    servings: int = 4
    prep_time_minutes: int = 0
    cook_time_minutes: int = 0
    instructions: str = ""
    ingredients: list = field(default_factory=list)  # [{"name","quantity","unit","notes"}]
    # None (not 0.0) means "not entered" — a real, honest absence, not a fabricated zero.
    calories_per_serving: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    source: str = ""
    notes: str = ""
    created_at: str = ""
    # "Recipe Unlocked" (2026-09-12) — a reward Mission.recipe_unlocks
    # can grant. Defaults False so every existing recipe stays exactly
    # as visible/usable as it is today; only a recipe the user
    # deliberately checks "Locked" for starts hidden. See
    # KitchenManager.unlock_recipe() and core.mission_manager's own
    # crediting of it on Mission completion. "Cook it to unlock it"
    # (2026-09-14) — log_meal()'s own real completion trigger: the
    # Mission naming this recipe completes the moment the user logs
    # having actually made it, not just via a manual mark-complete.
    locked: bool = False
    # Multi-user pass (2026-09-14) — who unlocked this shared recipe
    # and when, per the [[project_mia_multiuser_vision]] handoff's own
    # "Unlocked by: Faith" example. Recipe itself stays one shared
    # object (never duplicated per user) — this is just real metadata
    # about a real one-time event, same "record what happened, not a
    # duplicate" stance as everything else here. None/None for every
    # recipe that started unlocked (locked was never True) or was
    # unlocked before this field existed.
    unlocked_by_profile_id: Optional[str] = None
    unlocked_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "recipe_id": self.recipe_id, "name": self.name, "category": self.category,
            "servings": self.servings, "prep_time_minutes": self.prep_time_minutes,
            "cook_time_minutes": self.cook_time_minutes, "instructions": self.instructions,
            "ingredients": self.ingredients,
            "calories_per_serving": self.calories_per_serving, "protein_g": self.protein_g,
            "carbs_g": self.carbs_g, "fat_g": self.fat_g,
            "source": self.source, "notes": self.notes, "created_at": self.created_at,
            "locked": self.locked,
            "unlocked_by_profile_id": self.unlocked_by_profile_id,
            "unlocked_at": self.unlocked_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Recipe":
        return Recipe(
            recipe_id=data.get("recipe_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            category=data.get("category", "Dinner"),
            servings=data.get("servings", 4),
            prep_time_minutes=data.get("prep_time_minutes", 0),
            cook_time_minutes=data.get("cook_time_minutes", 0),
            instructions=data.get("instructions", ""),
            ingredients=data.get("ingredients", []),
            calories_per_serving=data.get("calories_per_serving"),
            protein_g=data.get("protein_g"),
            carbs_g=data.get("carbs_g"),
            fat_g=data.get("fat_g"),
            source=data.get("source", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            locked=bool(data.get("locked", False)),
            unlocked_by_profile_id=data.get("unlocked_by_profile_id"),
            unlocked_at=data.get("unlocked_at"),
        )


@dataclass
class PantryItem:
    item_id: str
    name: str
    quantity: float = 0.0
    unit: str = ""
    category: str = "Pantry/Dry Goods"  # one of PANTRY_CATEGORIES
    expiration_date: str = ""  # "" = not tracked
    notes: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id, "name": self.name, "quantity": self.quantity, "unit": self.unit,
            "category": self.category, "expiration_date": self.expiration_date,
            "notes": self.notes, "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PantryItem":
        return PantryItem(
            item_id=data.get("item_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            quantity=data.get("quantity", 0.0),
            unit=data.get("unit", ""),
            category=data.get("category", "Pantry/Dry Goods"),
            expiration_date=data.get("expiration_date", ""),
            notes=data.get("notes", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class GroceryListItem:
    item_id: str
    name: str
    quantity: float = 0.0
    unit: str = ""
    checked: bool = False
    source_recipe_id: str = ""  # "" = manually added
    added_at: str = ""

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id, "name": self.name, "quantity": self.quantity, "unit": self.unit,
            "checked": self.checked, "source_recipe_id": self.source_recipe_id, "added_at": self.added_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "GroceryListItem":
        return GroceryListItem(
            item_id=data.get("item_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            quantity=data.get("quantity", 0.0),
            unit=data.get("unit", ""),
            checked=data.get("checked", False),
            source_recipe_id=data.get("source_recipe_id", ""),
            added_at=data.get("added_at", ""),
        )


@dataclass
class MealLogEntry:
    entry_id: str
    recipe_id: str
    date: str
    notes: str = ""
    # Multi-user pass (2026-09-14) — stamped with whoever's active at
    # log_meal() time, same auto-attribution precedent
    # core.workout_manager.WorkoutSession.profile_id already
    # established. None (shared/unattributed — every entry logged
    # before this field existed, or with no active profile) counts
    # toward every profile's own times_made()/last_made_date(), same
    # "derive it, don't persist a duplicate" default every other
    # per-profile field in this codebase already uses.
    profile_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id, "recipe_id": self.recipe_id, "date": self.date,
            "notes": self.notes, "profile_id": self.profile_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "MealLogEntry":
        return MealLogEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            recipe_id=data.get("recipe_id", ""),
            date=data.get("date", ""),
            notes=data.get("notes", ""),
            profile_id=data.get("profile_id"),
        )


@dataclass
class RecipeUserStats:
    """One real (profile_id, recipe_id) pair's own relationship to a
    shared Recipe — the [[project_mia_multiuser_vision]] handoff's own
    flagship "shared object + user relationship" pattern. Recipe
    itself never gets duplicated per user; this is the per-user side
    of it. `times_made`/`last_made` are deliberately NOT fields here —
    both derive live from MealLogEntry.profile_id (see
    KitchenManager.times_made()/last_made_date()), same "derive it,
    don't persist a second copy that can drift" stance as everything
    else in this codebase. Only real per-user OPINIONS/notes that
    nothing else could derive live here: rating, favorite, personal
    notes."""

    profile_id: str
    recipe_id: str
    rating: Optional[float] = None  # None = not rated, never a fabricated 0
    favorite: bool = False
    personal_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id, "recipe_id": self.recipe_id,
            "rating": self.rating, "favorite": self.favorite, "personal_notes": self.personal_notes,
        }

    @staticmethod
    def from_dict(data: dict) -> "RecipeUserStats":
        return RecipeUserStats(
            profile_id=data.get("profile_id", ""),
            recipe_id=data.get("recipe_id", ""),
            rating=data.get("rating"),
            favorite=bool(data.get("favorite", False)),
            personal_notes=data.get("personal_notes", ""),
        )


def _in_range(entry_date: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """Pure logic — testable without I/O. Same ISO-date-string-compare
    shape as core.budget_manager/core.real_estate_manager's own
    _in_range()."""
    if start_date and entry_date < start_date:
        return False
    if end_date and entry_date > end_date:
        return False
    return True


def days_until_expiration(item: PantryItem, today: date) -> Optional[int]:
    """Pure logic — testable without Qt. None when expiration isn't
    tracked (item.expiration_date == "") — never a fabricated number."""
    if not item.expiration_date:
        return None
    try:
        expiration = date.fromisoformat(item.expiration_date)
    except ValueError:
        return None
    return (expiration - today).days


def recipe_missing_ingredients(recipe: Recipe, pantry_items: list[PantryItem]) -> list[str]:
    """Pure logic — testable without Qt. Case-insensitive name match
    against the pantry; when a matching pantry item's unit equals the
    ingredient's unit (case-insensitive), also requires enough
    quantity — otherwise this falls back to presence-only (comparing
    quantities across mismatched units would be fabricated precision,
    not a real answer). Returns the missing ingredient names in
    recipe order; an empty list means fully makeable."""
    pantry_by_name: dict[str, list[PantryItem]] = {}
    for item in pantry_items:
        pantry_by_name.setdefault(item.name.strip().lower(), []).append(item)

    missing = []
    for ingredient in recipe.ingredients:
        name = str(ingredient.get("name", "")).strip()
        if not name:
            continue
        matches = pantry_by_name.get(name.lower())
        if not matches:
            missing.append(name)
            continue
        unit = str(ingredient.get("unit", "")).strip().lower()
        needed = ingredient.get("quantity") or 0.0
        unit_matched_total = sum(m.quantity for m in matches if m.unit.strip().lower() == unit)
        if unit and any(m.unit.strip().lower() == unit for m in matches):
            if unit_matched_total < needed:
                missing.append(name)
        # else: presence-only — the ingredient name exists in the pantry
        # in some unit, treated as available without a quantity check.
    return missing


def recipes_makeable_from_pantry(
    recipes: list[Recipe], pantry_items: list[PantryItem],
) -> list[tuple[Recipe, list[str]]]:
    """Pure logic — testable without Qt. One (recipe, missing_ingredients)
    pair per recipe, sorted fewest-missing-first — the most actionable
    suggestions come first, a fully-makeable recipe ([] missing) always
    sorts to the very front."""
    results = [(recipe, recipe_missing_ingredients(recipe, pantry_items)) for recipe in recipes]
    return sorted(results, key=lambda pair: len(pair[1]))


class KitchenManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._recipes: list[Recipe] = []
        self._pantry: list[PantryItem] = []
        self._grocery_list: list[GroceryListItem] = []
        self._meal_log: list[MealLogEntry] = []
        self._recipe_user_stats: list[RecipeUserStats] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._recipes = self._load_file(_RECIPES_FILE, Recipe)
        self._pantry = self._load_file(_PANTRY_FILE, PantryItem)
        self._grocery_list = self._load_file(_GROCERY_LIST_FILE, GroceryListItem)
        self._meal_log = self._load_file(_MEAL_LOG_FILE, MealLogEntry)
        self._recipe_user_stats = self._load_file(_RECIPE_USER_STATS_FILE, RecipeUserStats)

    @staticmethod
    def _load_file(path: Path, cls) -> list:
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [cls.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            return []

    @staticmethod
    def _save_file(path: Path, records: list) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([r.to_dict() for r in records], indent=2), encoding="utf-8")

    def _save_recipes(self) -> None:
        self._save_file(_RECIPES_FILE, self._recipes)

    def _save_pantry(self) -> None:
        self._save_file(_PANTRY_FILE, self._pantry)

    def _save_grocery_list(self) -> None:
        self._save_file(_GROCERY_LIST_FILE, self._grocery_list)

    def _save_meal_log(self) -> None:
        self._save_file(_MEAL_LOG_FILE, self._meal_log)

    def _save_recipe_user_stats(self) -> None:
        self._save_file(_RECIPE_USER_STATS_FILE, self._recipe_user_stats)

    # ------------------------------------------------------------------
    # Recipe CRUD
    # ------------------------------------------------------------------

    def add_recipe(
        self,
        name: str,
        category: str = "Dinner",
        servings: int = 4,
        prep_time_minutes: int = 0,
        cook_time_minutes: int = 0,
        instructions: str = "",
        calories_per_serving: Optional[float] = None,
        protein_g: Optional[float] = None,
        carbs_g: Optional[float] = None,
        fat_g: Optional[float] = None,
        source: str = "",
        notes: str = "",
        locked: bool = False,
    ) -> Recipe:
        recipe = Recipe(
            recipe_id=uuid.uuid4().hex[:10],
            name=name,
            category=category if category in RECIPE_CATEGORIES else "Other",
            servings=max(1, servings),
            prep_time_minutes=max(0, prep_time_minutes),
            cook_time_minutes=max(0, cook_time_minutes),
            instructions=instructions,
            calories_per_serving=calories_per_serving,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            source=source,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
            locked=locked,
        )
        self._recipes.append(recipe)
        self._save_recipes()
        log.info("Recipe added: '%s' (%s)", recipe.name, recipe.category)
        return recipe

    def update_recipe(self, recipe_id: str, **fields) -> Recipe:
        recipe = self.get_recipe(recipe_id)
        if recipe is None:
            raise ValueError(f"No recipe with id '{recipe_id}'.")
        for key, value in fields.items():
            if not hasattr(recipe, key):
                raise ValueError(f"Recipe has no field '{key}'.")
            setattr(recipe, key, value)
        if recipe.category not in RECIPE_CATEGORIES:
            recipe.category = "Other"
        recipe.servings = max(1, recipe.servings)
        recipe.prep_time_minutes = max(0, recipe.prep_time_minutes)
        recipe.cook_time_minutes = max(0, recipe.cook_time_minutes)
        self._save_recipes()
        return recipe

    def delete_recipe(self, recipe_id: str) -> None:
        self._recipes = [r for r in self._recipes if r.recipe_id != recipe_id]
        self._save_recipes()

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        for recipe in self._recipes:
            if recipe.recipe_id == recipe_id:
                return recipe
        return None

    def all_recipes(self) -> list[Recipe]:
        return sorted(self._recipes, key=lambda r: r.name.lower())

    def unlock_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """
        "Recipe Unlocked" (2026-09-12) — called by
        core.mission_manager.MissionManager on a real Mission
        completion (mission.recipe_unlocks). No-ops (returns the recipe
        unchanged) if the recipe is already unlocked or the id is
        unknown — never fires a duplicate notification for a state that
        was already true, same idempotency stance
        core.insight_manager.InsightManager.resolve_insight() already
        takes. The unlock itself stays household-wide (the Recipe
        object is shared, not duplicated per profile — see
        [[project_mia_multiuser_vision]]), but records WHO unlocked it
        (whoever's active, if any) and when — real attribution
        metadata on the one shared object, same pattern
        core.mission_manager.Mission.profile_id already established.
        """
        recipe = self.get_recipe(recipe_id)
        if recipe is None or not recipe.locked:
            return recipe
        recipe.locked = False
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        recipe.unlocked_by_profile_id = active_profile.profile_id if active_profile is not None else None
        recipe.unlocked_at = datetime.now().isoformat(timespec="seconds")
        self._save_recipes()
        log.info("Recipe unlocked: '%s'", recipe.name)
        if self.context.notifications is not None:
            self.context.notifications.notify(
                title="\U0001F513 Recipe Unlocked!",
                message=f"'{recipe.name}' is now available.",
                level="info",
                source="kitchen",
            )
        return recipe

    # ------------------------------------------------------------------
    # Ingredients — mutate a Recipe's own ingredients list, not a
    # separate CRUD entity (see module docstring)
    # ------------------------------------------------------------------

    def add_ingredient(self, recipe_id: str, name: str, quantity: float = 0.0, unit: str = "", notes: str = "") -> Recipe:
        recipe = self.get_recipe(recipe_id)
        if recipe is None:
            raise ValueError(f"No recipe with id '{recipe_id}'.")
        recipe.ingredients.append({"name": name, "quantity": max(0.0, quantity), "unit": unit, "notes": notes})
        self._save_recipes()
        return recipe

    def remove_ingredient(self, recipe_id: str, index: int) -> Recipe:
        recipe = self.get_recipe(recipe_id)
        if recipe is None:
            raise ValueError(f"No recipe with id '{recipe_id}'.")
        if 0 <= index < len(recipe.ingredients):
            recipe.ingredients.pop(index)
            self._save_recipes()
        return recipe

    # ------------------------------------------------------------------
    # Pantry CRUD
    # ------------------------------------------------------------------

    def add_pantry_item(
        self, name: str, quantity: float = 0.0, unit: str = "", category: str = "Pantry/Dry Goods",
        expiration_date: str = "", notes: str = "",
    ) -> PantryItem:
        item = PantryItem(
            item_id=uuid.uuid4().hex[:10],
            name=name,
            quantity=max(0.0, quantity),
            unit=unit,
            category=category if category in PANTRY_CATEGORIES else "Other",
            expiration_date=expiration_date,
            notes=notes,
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._pantry.append(item)
        self._save_pantry()
        log.info("Pantry item added: '%s'", item.name)
        return item

    def update_pantry_item(self, item_id: str, **fields) -> PantryItem:
        item = self.get_pantry_item(item_id)
        if item is None:
            raise ValueError(f"No pantry item with id '{item_id}'.")
        for key, value in fields.items():
            if not hasattr(item, key):
                raise ValueError(f"PantryItem has no field '{key}'.")
            setattr(item, key, value)
        if item.category not in PANTRY_CATEGORIES:
            item.category = "Other"
        if item.quantity < 0:
            item.quantity = 0.0
        item.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save_pantry()
        return item

    def delete_pantry_item(self, item_id: str) -> None:
        self._pantry = [p for p in self._pantry if p.item_id != item_id]
        self._save_pantry()

    def get_pantry_item(self, item_id: str) -> Optional[PantryItem]:
        for item in self._pantry:
            if item.item_id == item_id:
                return item
        return None

    def all_pantry_items(self) -> list[PantryItem]:
        return sorted(self._pantry, key=lambda p: p.name.lower())

    # ------------------------------------------------------------------
    # Grocery list CRUD
    # ------------------------------------------------------------------

    def add_grocery_item(
        self, name: str, quantity: float = 0.0, unit: str = "", source_recipe_id: str = "",
    ) -> GroceryListItem:
        item = GroceryListItem(
            item_id=uuid.uuid4().hex[:10],
            name=name,
            quantity=max(0.0, quantity),
            unit=unit,
            source_recipe_id=source_recipe_id,
            added_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._grocery_list.append(item)
        self._save_grocery_list()
        return item

    def set_grocery_item_checked(self, item_id: str, checked: bool) -> None:
        item = self.get_grocery_item(item_id)
        if item is not None:
            item.checked = checked
            self._save_grocery_list()

    def delete_grocery_item(self, item_id: str) -> None:
        self._grocery_list = [g for g in self._grocery_list if g.item_id != item_id]
        self._save_grocery_list()

    def clear_checked_grocery_items(self) -> None:
        self._grocery_list = [g for g in self._grocery_list if not g.checked]
        self._save_grocery_list()

    def get_grocery_item(self, item_id: str) -> Optional[GroceryListItem]:
        for item in self._grocery_list:
            if item.item_id == item_id:
                return item
        return None

    def all_grocery_items(self) -> list[GroceryListItem]:
        return list(self._grocery_list)

    def add_missing_ingredients_to_grocery_list(self, recipe_id: str) -> list[GroceryListItem]:
        """The real suggestions-to-action link: adds each of the
        recipe's currently-missing ingredients (recipe_missing_ingredients())
        to the grocery list, skipping any name already present on it
        (case-insensitive) so repeated use never piles up duplicates.
        Returns the newly-added items only."""
        recipe = self.get_recipe(recipe_id)
        if recipe is None:
            raise ValueError(f"No recipe with id '{recipe_id}'.")
        missing_names = {n.lower() for n in recipe_missing_ingredients(recipe, self._pantry)}
        existing_names = {g.name.strip().lower() for g in self._grocery_list}

        added = []
        for ingredient in recipe.ingredients:
            name = str(ingredient.get("name", "")).strip()
            if name.lower() not in missing_names or name.lower() in existing_names:
                continue
            item = self.add_grocery_item(
                name=name, quantity=ingredient.get("quantity") or 0.0,
                unit=ingredient.get("unit", ""), source_recipe_id=recipe_id,
            )
            added.append(item)
            existing_names.add(name.lower())
        return added

    # ------------------------------------------------------------------
    # Meal log CRUD + meal-frequency queries
    # ------------------------------------------------------------------

    def log_meal(self, recipe_id: str, date_str: Optional[str] = None, notes: str = "") -> MealLogEntry:
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        entry = MealLogEntry(
            entry_id=uuid.uuid4().hex[:10],
            recipe_id=recipe_id,
            date=date_str or date.today().isoformat(),
            notes=notes,
            profile_id=active_profile.profile_id if active_profile is not None else None,
        )
        self._meal_log.append(entry)
        self._save_meal_log()
        # 2026-09-11 gamification pass — a fresh log entry every call,
        # never an idempotency risk (unlike, say, re-marking something
        # already complete).
        recipe = self.get_recipe(recipe_id)
        recipe_note = f"'{recipe.name}' logged for today." if recipe is not None else "Logged for today."
        # "My Hero's Path" (2026-09-11) — Nutrition (Body category) is
        # the natural skill for a logged meal.
        grant_xp(
            self.context,
            5,
            "\U0001F373 Meal logged!",
            recipe_note,
            skill_weights=[SkillWeight("nutrition", 5)],
        )
        # "Cook it to unlock it" (2026-09-14) — the real, direct
        # completion trigger the user asked for: any active Mission
        # whose recipe_unlocks names this recipe completes the moment
        # you actually log having made it, rather than needing a
        # separate manual "mark complete" click or an unrelated tally.
        # Reuses update_mission()'s own existing reward-crediting/
        # recipe-unlocking pipeline verbatim — this is the only new
        # code, not a second unlock mechanism.
        if self.context.missions is not None:
            for mission in self.context.missions.all_missions():
                if mission.status == "active" and recipe_id in mission.recipe_unlocks:
                    self.context.missions.update_mission(mission.mission_id, status="completed")
        # Event-sourced groundwork (2026-09-14) — see
        # core/rewards_manager.py's own docstring for the full design.
        self.context.events.publish(
            "activity.logged", source="kitchen", category="meal_cooked",
            timestamp=datetime.now().isoformat(timespec="seconds"),
            duration=None, quantity=1,
            metadata={"entry_id": entry.entry_id, "recipe_id": recipe_id},
        )
        return entry

    def delete_meal_log_entry(self, entry_id: str) -> None:
        self._meal_log = [m for m in self._meal_log if m.entry_id != entry_id]
        self._save_meal_log()

    def all_meal_log_entries(self) -> list[MealLogEntry]:
        return sorted(self._meal_log, key=lambda m: m.date, reverse=True)

    def times_made(
        self, recipe_id: str, profile_id: Optional[str] = None,
        start_date: Optional[str] = None, end_date: Optional[str] = None,
    ) -> int:
        """`profile_id=None` (the default) is the real household total —
        unchanged from before per-profile attribution existed. Given a
        real profile_id, counts only entries attributed to that
        profile OR unattributed (`MealLogEntry.profile_id is None` —
        shared/legacy, counts toward everyone, same convention
        core.rewards_manager.is_attributed_to() already established)."""
        return sum(
            1 for m in self._meal_log
            if m.recipe_id == recipe_id and _in_range(m.date, start_date, end_date)
            and (profile_id is None or m.profile_id is None or m.profile_id == profile_id)
        )

    def last_made_date(self, recipe_id: str, profile_id: Optional[str] = None) -> Optional[str]:
        """Same `profile_id` semantics as times_made() above."""
        dates = [
            m.date for m in self._meal_log
            if m.recipe_id == recipe_id and (profile_id is None or m.profile_id is None or m.profile_id == profile_id)
        ]
        return max(dates) if dates else None

    # ------------------------------------------------------------------
    # Recipe <-> profile relationship (2026-09-14) — the "shared object
    # + user relationship" pattern's first real application, see
    # RecipeUserStats' own docstring and [[project_mia_multiuser_vision]].
    # ------------------------------------------------------------------

    def get_recipe_user_stats(self, profile_id: str, recipe_id: str) -> RecipeUserStats:
        """Never returns None — a profile/recipe pair with no real
        rating/favorite/notes yet just gets a fresh, unsaved default
        (nothing is persisted until one of the setters below is
        actually called), so callers never need a null-check."""
        for stats in self._recipe_user_stats:
            if stats.profile_id == profile_id and stats.recipe_id == recipe_id:
                return stats
        return RecipeUserStats(profile_id=profile_id, recipe_id=recipe_id)

    def _get_or_create_recipe_user_stats(self, profile_id: str, recipe_id: str) -> RecipeUserStats:
        for stats in self._recipe_user_stats:
            if stats.profile_id == profile_id and stats.recipe_id == recipe_id:
                return stats
        stats = RecipeUserStats(profile_id=profile_id, recipe_id=recipe_id)
        self._recipe_user_stats.append(stats)
        return stats

    def set_recipe_rating(self, profile_id: str, recipe_id: str, rating: Optional[float]) -> RecipeUserStats:
        stats = self._get_or_create_recipe_user_stats(profile_id, recipe_id)
        stats.rating = rating
        self._save_recipe_user_stats()
        return stats

    def set_recipe_favorite(self, profile_id: str, recipe_id: str, favorite: bool) -> RecipeUserStats:
        stats = self._get_or_create_recipe_user_stats(profile_id, recipe_id)
        stats.favorite = favorite
        self._save_recipe_user_stats()
        return stats

    def set_recipe_personal_notes(self, profile_id: str, recipe_id: str, personal_notes: str) -> RecipeUserStats:
        stats = self._get_or_create_recipe_user_stats(profile_id, recipe_id)
        stats.personal_notes = personal_notes
        self._save_recipe_user_stats()
        return stats

    def favorite_recipe_ids(self, profile_id: str) -> list[str]:
        return [s.recipe_id for s in self._recipe_user_stats if s.profile_id == profile_id and s.favorite]

    # ------------------------------------------------------------------
    # Suggestions
    # ------------------------------------------------------------------

    def recipes_makeable_now(self) -> list[tuple[Recipe, list[str]]]:
        return recipes_makeable_from_pantry(self.all_recipes(), self._pantry)
