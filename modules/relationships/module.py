"""
modules.relationships.module
===============================

Relationship Profiles and Pet Profiles — docs/VISION.md's own
"structured extensions" of Memory Palace. All persistence lives in
core/relationships_manager.py (self.context.relationships) — this
module is the Qt-facing wrapper around it, same split as every other
data-backed module here.

Two tabs (People/Pets), QTabWidget, same shape as Kitchen's own Pantry
tab (filterable list + Add/Edit/Delete, gui/list_widget_helpers.py
reused throughout) — no nested list<->detail page needed, since
neither record has its own sub-entities requiring extra screen space
beyond what the Add/Edit dialogs already cover.
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.corrections import screen_edit
from core.relationships_manager import Pet, Person, days_until_birthday
from gui.add_edit_pet_dialog import AddEditPetDialog
from gui.add_edit_person_dialog import AddEditPersonDialog
from gui.list_widget_helpers import add_empty_state_item, selected_item_data
from modules.module_base import ModuleBase


def _birthday_tag(birthday: str, today: date) -> str:
    """Pure logic — testable without Qt. Same [DUE IN Nd]-style
    convention format_bill_row()/format_pantry_row() already
    established, retargeted to an upcoming birthday."""
    if not birthday:
        return ""
    days = days_until_birthday(birthday, today)
    if days is None:
        return ""
    if days == 0:
        return "[BIRTHDAY TODAY]  "
    return f"[BIRTHDAY IN {days}d]  "


def format_person_row(person: Person, today: date) -> str:
    """Pure formatting logic — testable without Qt."""
    relationship_part = f"  [{person.relationship}]" if person.relationship else ""
    return f"{_birthday_tag(person.birthday, today)}{person.name}{relationship_part}"


def format_pet_row(pet: Pet, today: date) -> str:
    """Pure formatting logic — testable without Qt."""
    species_part = f"  [{pet.species}]" if pet.species else ""
    return f"{_birthday_tag(pet.birthday, today)}{pet.name}{species_part}"


class RelationshipsModule(ModuleBase):
    """The People & Pets app (desktop): the people in someone's life (relationship, birthday, favourite things, gift ideas, email) and their pets (species, birthday, medical notes), in two tabs."""
    module_id = "relationships"
    display_name = "People & Pets"
    description = "Relationship profiles and pet profiles."
    icon = "\U0001F465"  # people silhouette

    def __init__(self, context) -> None:
        """Nothing built yet: the tabs are made in get_widget()."""
        super().__init__(context)
        self._person_list: Optional[QListWidget] = None
        self._pet_list: Optional[QListWidget] = None

    def refresh(self) -> None:
        """Re-read every list (ModuleBase.refresh: records changed elsewhere, e.g. by voice)."""
        self._refresh_person_list()
        self._refresh_pet_list()

    def get_widget(self) -> QWidget:
        """The page: People and Pets tabs."""
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
        tabs.addTab(self._build_people_tab(), "People")
        tabs.addTab(self._build_pets_tab(), "Pets")
        tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(tabs, stretch=1)

        return widget

    def _on_tab_changed(self, index: int) -> None:
        """Refreshes both lists when the tab changes, so an edit made elsewhere shows."""
        self._refresh_person_list()
        self._refresh_pet_list()

    # ------------------------------------------------------------------
    # People tab
    # ------------------------------------------------------------------

    def _build_people_tab(self) -> QWidget:
        """The People tab: the list with Add, Edit and Delete."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._person_list = QListWidget()
        layout.addWidget(self._person_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Person")
        add_button.clicked.connect(self._on_add_person)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_person)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_person)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        self._refresh_person_list()
        return tab

    def _refresh_person_list(self) -> None:
        """Lists every person (with how soon their birthday is)."""
        if self._person_list is None:
            return
        self._person_list.clear()
        today = date.today()
        for person in self.context.relationships.all_people():
            item = QListWidgetItem(format_person_row(person, today))
            item.setData(Qt.ItemDataRole.UserRole, person.person_id)
            self._person_list.addItem(item)
        if self._person_list.count() == 0:
            add_empty_state_item(self._person_list, "No people tracked yet — click Add Person to get started.")

    def _selected_person_id(self) -> Optional[str]:
        """The selected person's id, or None."""
        return selected_item_data(self._person_list)

    def _on_add_person(self) -> None:
        """Adds a person from the dialog and refreshes."""
        dialog = AddEditPersonDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.relationships.add_person(
            name=dialog.entered_name, relationship=dialog.entered_relationship,
            birthday=dialog.entered_birthday, favorite_things=dialog.entered_favorite_things,
            gift_ideas=dialog.entered_gift_ideas, notes=dialog.entered_notes, email=dialog.entered_email,
        )
        self._refresh_person_list()

    def _on_edit_person(self) -> None:
        """Edits the selected person in the dialog (asks for a selection first)."""
        person_id = self._selected_person_id()
        if person_id is None:
            QMessageBox.information(None, "No Person Selected", "Select a person to edit.")
            return
        person = self.context.relationships.get_person(person_id)
        dialog = AddEditPersonDialog(person=person)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.relationships.update_person(
            person_id, name=dialog.entered_name, relationship=dialog.entered_relationship,
            birthday=dialog.entered_birthday, favorite_things=dialog.entered_favorite_things,
            gift_ideas=dialog.entered_gift_ideas, notes=dialog.entered_notes, email=dialog.entered_email,
        )
        screen_edit(self.context, "person.edit", person_id)  # someone she added, fixed by hand (step 4)
        self._refresh_person_list()

    def _on_delete_person(self) -> None:
        """Deletes the selected person (recorded as a screen edit, so a person fixing MIA's work counts) and refreshes."""
        person_id = self._selected_person_id()
        if person_id is None:
            QMessageBox.information(None, "No Person Selected", "Select a person to delete.")
            return
        self.context.relationships.delete_person(person_id)
        screen_edit(self.context, "person.delete", person_id)
        self._refresh_person_list()

    # ------------------------------------------------------------------
    # Pets tab
    # ------------------------------------------------------------------

    def _build_pets_tab(self) -> QWidget:
        """The Pets tab: the list with Add, Edit and Delete."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._pet_list = QListWidget()
        layout.addWidget(self._pet_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Pet")
        add_button.clicked.connect(self._on_add_pet)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_pet)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_pet)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        self._refresh_pet_list()
        return tab

    def _refresh_pet_list(self) -> None:
        """Lists every pet (with how soon its birthday is)."""
        if self._pet_list is None:
            return
        self._pet_list.clear()
        today = date.today()
        for pet in self.context.relationships.all_pets():
            item = QListWidgetItem(format_pet_row(pet, today))
            item.setData(Qt.ItemDataRole.UserRole, pet.pet_id)
            self._pet_list.addItem(item)
        if self._pet_list.count() == 0:
            add_empty_state_item(self._pet_list, "No pets tracked yet — click Add Pet to get started.")

    def _selected_pet_id(self) -> Optional[str]:
        """The selected pet's id, or None."""
        return selected_item_data(self._pet_list)

    def _on_add_pet(self) -> None:
        """Adds a pet from the dialog and refreshes."""
        dialog = AddEditPetDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.relationships.add_pet(
            name=dialog.entered_name, species=dialog.entered_species,
            birthday=dialog.entered_birthday, medical_notes=dialog.entered_medical_notes,
            notes=dialog.entered_notes,
        )
        self._refresh_pet_list()

    def _on_edit_pet(self) -> None:
        """Edits the selected pet in the dialog (asks for a selection first)."""
        pet_id = self._selected_pet_id()
        if pet_id is None:
            QMessageBox.information(None, "No Pet Selected", "Select a pet to edit.")
            return
        pet = self.context.relationships.get_pet(pet_id)
        dialog = AddEditPetDialog(pet=pet)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.relationships.update_pet(
            pet_id, name=dialog.entered_name, species=dialog.entered_species,
            birthday=dialog.entered_birthday, medical_notes=dialog.entered_medical_notes,
            notes=dialog.entered_notes,
        )
        self._refresh_pet_list()

    def _on_delete_pet(self) -> None:
        """Deletes the selected pet and refreshes."""
        pet_id = self._selected_pet_id()
        if pet_id is None:
            QMessageBox.information(None, "No Pet Selected", "Select a pet to delete.")
            return
        self.context.relationships.delete_pet(pet_id)
        self._refresh_pet_list()
