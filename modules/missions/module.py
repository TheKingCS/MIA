"""
modules.missions.module
==========================

Missions — docs/ROADMAP.md milestone v0.18, module #20 in that doc's
"Top-level module sections" list. Two-level CRUD, same shape as
modules/expeditions/module.py: Missions at the top, the selected
Mission's Objectives below it. A Mission optionally links to an
existing Trip (picked at creation only — see
gui/add_edit_mission_dialog.py); objectives track progress toward a
target, either a manually-incremented tally or time computed live from
the linked Trip's logged splits (core/mission_manager.py).

format_mission_row()/format_objective_row() are free functions (not
methods) — testable without Qt, see tests/test_missions_module.py.
format_objective_row() takes already-computed progress/is_complete
rather than a Mission/index pair, so it stays pure or here — the live
computation itself lives in core.mission_manager.MissionManager.
"""

from __future__ import annotations

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
    QVBoxLayout,
    QWidget,
)

from core.mission_manager import Mission, Objective
from gui.add_edit_mission_dialog import AddEditMissionDialog
from gui.add_edit_objective_dialog import AddEditObjectiveDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from modules.module_base import ModuleBase


def format_mission_row(mission: Mission, trip_name: str = "") -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    trip_part = f"  [{trip_name}]" if trip_name else ""
    return f"{mission.name}{trip_part}  ({mission.status})"


def format_objective_row(objective: Objective, progress: float, is_complete: bool) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    mark = "[x]" if is_complete else "[ ]"
    return f"{mark} {objective.description}: {progress:g}/{objective.target:g}"


class MissionsModule(ModuleBase):
    module_id = "missions"
    display_name = "Missions"
    description = "Gamified goals and objectives, tied to a trip or general."
    icon = "\U0001F3C6"  # trophy

    def __init__(self, context) -> None:
        super().__init__(context)
        self._mission_list: Optional[QListWidget] = None
        self._objective_list: Optional[QListWidget] = None

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

        mission_title = QLabel("Missions")
        mission_title.setObjectName("SubtitleLabel")
        layout.addWidget(mission_title)

        self._mission_list = QListWidget()
        self._mission_list.currentItemChanged.connect(self._on_mission_selected)
        layout.addWidget(self._mission_list, stretch=1)

        mission_buttons = QHBoxLayout()
        add_mission_button = QPushButton("Add Mission")
        add_mission_button.clicked.connect(self._on_add_mission)
        mission_buttons.addWidget(add_mission_button)

        edit_mission_button = QPushButton("Edit Selected")
        edit_mission_button.clicked.connect(self._on_edit_mission)
        mission_buttons.addWidget(edit_mission_button)

        delete_mission_button = QPushButton("Delete Selected")
        delete_mission_button.clicked.connect(self._on_delete_mission)
        mission_buttons.addWidget(delete_mission_button)
        layout.addLayout(mission_buttons)

        objective_title = QLabel("Objectives in selected Mission")
        objective_title.setObjectName("SubtitleLabel")
        layout.addWidget(objective_title)

        self._objective_list = QListWidget()
        layout.addWidget(self._objective_list, stretch=1)

        objective_buttons = QHBoxLayout()
        add_objective_button = QPushButton("Add Objective")
        add_objective_button.clicked.connect(self._on_add_objective)
        objective_buttons.addWidget(add_objective_button)

        increment_button = QPushButton("+1 Tally")
        increment_button.clicked.connect(self._on_increment_objective)
        objective_buttons.addWidget(increment_button)

        delete_objective_button = QPushButton("Delete Selected")
        delete_objective_button.clicked.connect(self._on_delete_objective)
        objective_buttons.addWidget(delete_objective_button)
        layout.addLayout(objective_buttons)

        self._refresh_mission_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_mission_list(self) -> None:
        previously_selected = self._selected_mission_id()

        self._mission_list.clear()
        for mission in self.context.missions.all_missions():
            trip_name = ""
            if mission.trip_id:
                trip = self.context.trips.get_trip(mission.trip_id)
                trip_name = trip.name if trip is not None else ""
            item = QListWidgetItem(format_mission_row(mission, trip_name))
            item.setData(Qt.ItemDataRole.UserRole, mission.mission_id)
            self._mission_list.addItem(item)

        if previously_selected is not None:
            for row in range(self._mission_list.count()):
                item = self._mission_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == previously_selected:
                    self._mission_list.setCurrentItem(item)
                    break
        self._refresh_objective_list()

    def _refresh_objective_list(self) -> None:
        self._objective_list.clear()
        mission_id = self._selected_mission_id()
        if mission_id is None:
            return
        mission = self.context.missions.get_mission(mission_id)
        if mission is None:
            return
        for index, objective in enumerate(mission.objectives):
            progress = self.context.missions.objective_progress(mission_id, index) or 0.0
            is_complete = self.context.missions.is_objective_complete(mission_id, index)
            item = QListWidgetItem(format_objective_row(objective, progress, is_complete))
            item.setData(Qt.ItemDataRole.UserRole, index)
            self._objective_list.addItem(item)

    def _on_mission_selected(self) -> None:
        self._refresh_objective_list()

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _selected_mission_id(self) -> Optional[str]:
        item = self._mission_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _selected_objective_index(self) -> Optional[int]:
        item = self._objective_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Mission actions
    # ------------------------------------------------------------------

    def _on_add_mission(self) -> None:
        dialog = AddEditMissionDialog(self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.add_mission(name=dialog.entered_name, trip_id=dialog.entered_trip_id)
        self._refresh_mission_list()

    def _on_edit_mission(self) -> None:
        mission_id = self._selected_mission_id()
        if mission_id is None:
            QMessageBox.information(None, "No Mission Selected", "Select a mission to edit.")
            return

        mission = self.context.missions.get_mission(mission_id)
        dialog = AddEditMissionDialog(self.context, mission=mission)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.update_mission(mission_id, name=dialog.entered_name, status=dialog.entered_status)
        self._refresh_mission_list()

    def _on_delete_mission(self) -> None:
        mission_id = self._selected_mission_id()
        if mission_id is None:
            QMessageBox.information(None, "No Mission Selected", "Select a mission to delete.")
            return

        mission = self.context.missions.get_mission(mission_id)
        dialog = DeleteConfirmDialog(mission.name, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.delete_mission(mission_id)
        self._refresh_mission_list()

    # ------------------------------------------------------------------
    # Objective actions
    # ------------------------------------------------------------------

    def _on_add_objective(self) -> None:
        mission_id = self._selected_mission_id()
        if mission_id is None:
            QMessageBox.information(None, "No Mission Selected", "Select a mission to add an objective to.")
            return

        dialog = AddEditObjectiveDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.add_objective(
            mission_id, dialog.entered_description, dialog.entered_metric_type, dialog.entered_target
        )
        self._refresh_objective_list()

    def _on_increment_objective(self) -> None:
        mission_id = self._selected_mission_id()
        index = self._selected_objective_index()
        if mission_id is None or index is None:
            QMessageBox.information(None, "No Objective Selected", "Select an objective to increment.")
            return

        mission = self.context.missions.get_mission(mission_id)
        if mission.objectives[index].metric_type != "tally":
            QMessageBox.information(
                None, "Not a Tally Objective",
                "Only tally-type objectives can be incremented by hand — this one tracks trip time automatically.",
            )
            return

        self.context.missions.increment_tally(mission_id, index)
        self._refresh_objective_list()

    def _on_delete_objective(self) -> None:
        mission_id = self._selected_mission_id()
        index = self._selected_objective_index()
        if mission_id is None or index is None:
            QMessageBox.information(None, "No Objective Selected", "Select an objective to delete.")
            return

        mission = self.context.missions.get_mission(mission_id)
        dialog = DeleteConfirmDialog(mission.objectives[index].description, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.delete_objective(mission_id, index)
        self._refresh_objective_list()
