"""
gui.add_edit_recipe_dialog
=============================

Small dialog for creating or editing a recipe's own header fields
(name, category, servings, timing, instructions, optional nutrition
facts), used by modules/kitchen/module.py. Deliberately does NOT edit
ingredients — those are added/removed one at a time from the recipe's
own detail page via gui/add_edit_ingredient_dialog.py, same real
"outer list + single-item dialog, immediate commit" precedent
gui/add_edit_job_dialog.py's own docstring already establishes for the
directly analogous Job -> materials-consumed relationship.

Nutrition fields follow core/real_estate_manager.py's own
has_loan_terms() precedent: a 0.0 value means "not entered" (there's
no real recipe with 0 calories), converted to/from None on save/
prefill rather than adding a new "optional field" checkbox convention.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.kitchen_manager import RECIPE_CATEGORIES, Recipe


class AddEditRecipeDialog(QDialog):
    def __init__(self, parent=None, recipe: Optional[Recipe] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Recipe" if recipe is not None else "New Recipe")
        self.setFixedSize(380, 790)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Weeknight Chili")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(RECIPE_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Servings:"))
        self.servings_spin = QSpinBox()
        self.servings_spin.setRange(1, 100)
        self.servings_spin.setValue(4)
        layout.addWidget(self.servings_spin)

        layout.addWidget(QLabel("Prep Time (minutes):"))
        self.prep_time_spin = QSpinBox()
        self.prep_time_spin.setRange(0, 1440)
        layout.addWidget(self.prep_time_spin)

        layout.addWidget(QLabel("Cook Time (minutes):"))
        self.cook_time_spin = QSpinBox()
        self.cook_time_spin.setRange(0, 1440)
        layout.addWidget(self.cook_time_spin)

        layout.addWidget(QLabel("Instructions:"))
        self.instructions_edit = QTextEdit()
        self.instructions_edit.setPlaceholderText("Steps, one per line (optional)")
        self.instructions_edit.setFixedHeight(120)
        layout.addWidget(self.instructions_edit)

        layout.addWidget(QLabel("Nutrition (per serving, optional — leave at 0 to skip):"))
        self.calories_spin = QDoubleSpinBox()
        self.calories_spin.setRange(0.0, 10_000.0)
        self.calories_spin.setDecimals(0)
        self.calories_spin.setPrefix("Calories: ")
        layout.addWidget(self.calories_spin)

        self.protein_spin = QDoubleSpinBox()
        self.protein_spin.setRange(0.0, 1_000.0)
        self.protein_spin.setDecimals(1)
        self.protein_spin.setPrefix("Protein (g): ")
        layout.addWidget(self.protein_spin)

        self.carbs_spin = QDoubleSpinBox()
        self.carbs_spin.setRange(0.0, 1_000.0)
        self.carbs_spin.setDecimals(1)
        self.carbs_spin.setPrefix("Carbs (g): ")
        layout.addWidget(self.carbs_spin)

        self.fat_spin = QDoubleSpinBox()
        self.fat_spin.setRange(0.0, 1_000.0)
        self.fat_spin.setDecimals(1)
        self.fat_spin.setPrefix("Fat (g): ")
        layout.addWidget(self.fat_spin)

        layout.addWidget(QLabel("Source:"))
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("e.g. a URL, cookbook, or 'Grandma's recipe box' (optional)")
        layout.addWidget(self.source_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(60)
        layout.addWidget(self.notes_edit)

        # "Recipe Unlocked" (2026-09-12) — unchecked by default so a
        # new recipe is always immediately usable; only a deliberately-
        # authored "reward" recipe starts hidden.
        self.locked_checkbox = QCheckBox("Locked (unlocked by completing a mission)")
        layout.addWidget(self.locked_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(recipe)

        self._name: str = ""
        self._category: str = RECIPE_CATEGORIES[0]
        self._servings: int = 4
        self._prep_time_minutes: int = 0
        self._cook_time_minutes: int = 0
        self._instructions: str = ""
        self._calories_per_serving: Optional[float] = None
        self._protein_g: Optional[float] = None
        self._carbs_g: Optional[float] = None
        self._fat_g: Optional[float] = None
        self._source: str = ""
        self._notes: str = ""
        self._locked: bool = False

    def _prefill(self, recipe: Optional[Recipe]) -> None:
        if recipe is None:
            return
        self.name_edit.setText(recipe.name)
        if recipe.category in RECIPE_CATEGORIES:
            self.category_combo.setCurrentText(recipe.category)
        self.servings_spin.setValue(recipe.servings)
        self.prep_time_spin.setValue(recipe.prep_time_minutes)
        self.cook_time_spin.setValue(recipe.cook_time_minutes)
        self.instructions_edit.setPlainText(recipe.instructions)
        self.calories_spin.setValue(recipe.calories_per_serving or 0.0)
        self.protein_spin.setValue(recipe.protein_g or 0.0)
        self.carbs_spin.setValue(recipe.carbs_g or 0.0)
        self.fat_spin.setValue(recipe.fat_g or 0.0)
        self.source_edit.setText(recipe.source)
        self.notes_edit.setPlainText(recipe.notes)
        self.locked_checkbox.setChecked(recipe.locked)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._category = self.category_combo.currentText()
        self._servings = self.servings_spin.value()
        self._prep_time_minutes = self.prep_time_spin.value()
        self._cook_time_minutes = self.cook_time_spin.value()
        self._instructions = self.instructions_edit.toPlainText().strip()
        self._calories_per_serving = self.calories_spin.value() or None
        self._protein_g = self.protein_spin.value() or None
        self._carbs_g = self.carbs_spin.value() or None
        self._fat_g = self.fat_spin.value() or None
        self._source = self.source_edit.text().strip()
        self._notes = self.notes_edit.toPlainText().strip()
        self._locked = self.locked_checkbox.isChecked()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_servings(self) -> int:
        return self._servings

    @property
    def entered_prep_time_minutes(self) -> int:
        return self._prep_time_minutes

    @property
    def entered_cook_time_minutes(self) -> int:
        return self._cook_time_minutes

    @property
    def entered_instructions(self) -> str:
        return self._instructions

    @property
    def entered_calories_per_serving(self) -> Optional[float]:
        return self._calories_per_serving

    @property
    def entered_protein_g(self) -> Optional[float]:
        return self._protein_g

    @property
    def entered_carbs_g(self) -> Optional[float]:
        return self._carbs_g

    @property
    def entered_fat_g(self) -> Optional[float]:
        return self._fat_g

    @property
    def entered_source(self) -> str:
        return self._source

    @property
    def entered_notes(self) -> str:
        return self._notes

    @property
    def entered_locked(self) -> bool:
        return self._locked
