"""
gui.log_meal_dialog
======================

Small dialog for logging that a recipe was made on a given date, used
by modules/kitchen/module.py's Meal Log tab "Log a Meal" button. The
Recipes detail page's own "Log that I made this today" quick action
skips this dialog entirely and calls KitchenManager.log_meal() directly
with today's date — a real one-click action, not a prefilled form.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class LogMealDialog(QDialog):
    def __init__(self, parent=None, recipes: Optional[list] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Log a Meal")
        self.setFixedSize(340, 260)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Recipe:"))
        self.recipe_combo = QComboBox()
        for recipe in recipes or []:
            self.recipe_combo.addItem(recipe.name, recipe.recipe_id)
        layout.addWidget(self.recipe_combo)

        layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.date_edit.setDate(QDate.currentDate())
        layout.addWidget(self.date_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._recipe_id: str = ""
        self._date: str = ""
        self._notes: str = ""

    def _on_accept(self) -> None:
        recipe_id = self.recipe_combo.currentData()
        if not recipe_id:
            return
        self._recipe_id = recipe_id
        self._date = self.date_edit.date().toString(_ISO_DATE_FORMAT)
        self._notes = self.notes_edit.text().strip()
        self.accept()

    @property
    def entered_recipe_id(self) -> str:
        return self._recipe_id

    @property
    def entered_date(self) -> str:
        return self._date

    @property
    def entered_notes(self) -> str:
        return self._notes
