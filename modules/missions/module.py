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

**2026-07-16 redesign**: replaced the plain QListWidget rows (both
Missions and Objectives) with big "bubbly" cards
(gui/widgets/mission_card.py's MissionCard / gui/widgets/
objective_card.py's ObjectiveCard) — at the user's explicit request for
"bigger and more bubbly button-like choosing... and interacting."
Each card carries its own inline actions now (Mission: ✎ edit / ✕
delete; Objective: +1 tally / ✕ delete), so there's no more separate
"select from the list, then click a button below" two-step — the
screen-level button rows are now just "Add Mission"/"Add Objective".
Same QScrollArea + explicit hide()/setParent(None)/deleteLater()
rebuild-on-refresh pattern as gui/character_panel.py's chat log, for
the same reason: this app has hit real ghosted-widget bugs from
skipping that cleanup step before.

format_mission_row()/format_objective_row() are free functions (not
methods) — testable without Qt, see tests/test_missions_module.py.
format_objective_row() takes already-computed progress/is_complete
rather than a Mission/index pair, so it stays pure — the live
computation itself lives in core.mission_manager.MissionManager. Both
are now used for tooltips/logging rather than a literal list row, but
kept unchanged (and still tested) since MissionCard/ObjectiveCard build
their own richer display from the same underlying data.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.mission_manager import Mission, Objective
from gui.add_edit_mission_dialog import AddEditMissionDialog
from gui.add_edit_objective_dialog import AddEditObjectiveDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from gui.widgets.mission_card import MissionCard
from gui.widgets.objective_card import ObjectiveCard
from modules.module_base import ModuleBase


def format_mission_row(mission: Mission, trip_name: str = "") -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    trip_part = f"  [{trip_name}]" if trip_name else ""
    return f"{mission.name}{trip_part}  ({mission.status})"


def format_objective_row(objective: Objective, progress: float, is_complete: bool) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    mark = "[x]" if is_complete else "[ ]"
    return f"{mark} {objective.description}: {progress:g} of {objective.target:g}"


class MissionsModule(ModuleBase):
    module_id = "missions"
    display_name = "Missions"
    description = "Gamified goals and objectives, tied to a trip or general."
    icon = "\U0001F3C6"  # trophy

    def __init__(self, context) -> None:
        super().__init__(context)
        self._mission_scroll: Optional[QScrollArea] = None
        self._mission_cards_container: Optional[QWidget] = None
        self._mission_cards_layout: Optional[QVBoxLayout] = None
        self._objective_scroll: Optional[QScrollArea] = None
        self._objective_cards_container: Optional[QWidget] = None
        self._objective_cards_layout: Optional[QVBoxLayout] = None
        self._selected_mission_id: Optional[str] = None

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

        self._mission_scroll, self._mission_cards_container, self._mission_cards_layout = self._build_card_scroll()
        layout.addWidget(self._mission_scroll, stretch=1)

        add_mission_button = QPushButton("Add Mission")
        add_mission_button.clicked.connect(self._on_add_mission)
        layout.addWidget(add_mission_button)

        objective_title = QLabel("Objectives in selected Mission")
        objective_title.setObjectName("SubtitleLabel")
        layout.addWidget(objective_title)

        self._objective_scroll, self._objective_cards_container, self._objective_cards_layout = (
            self._build_card_scroll()
        )
        layout.addWidget(self._objective_scroll, stretch=1)

        add_objective_button = QPushButton("Add Objective")
        add_objective_button.clicked.connect(self._on_add_objective)
        layout.addWidget(add_objective_button)

        self._refresh_mission_cards()
        return widget

    @staticmethod
    def _build_card_scroll() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(2, 2, 2, 2)
        container_layout.setSpacing(10)
        container_layout.addStretch()
        scroll.setWidget(container)

        return scroll, container, container_layout

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_mission_cards(self) -> None:
        """Full rebuild on every call, same "clear and refill" shape as
        gui/character_panel.py's chat log — explicit hide() +
        setParent(None) before deleteLater(), same reasoning."""
        while self._mission_cards_layout.count():
            item = self._mission_cards_layout.takeAt(0)
            card = item.widget()
            if card is not None:
                card.hide()
                card.setParent(None)
                card.deleteLater()

        missions = self.context.missions.all_missions()
        if self._selected_mission_id is not None and not any(
            m.mission_id == self._selected_mission_id for m in missions
        ):
            self._selected_mission_id = None

        for mission in missions:
            trip_name = ""
            if mission.trip_id and self.context.trips is not None:
                trip = self.context.trips.get_trip(mission.trip_id)
                trip_name = trip.name if trip is not None else ""
            total_objectives = len(mission.objectives)
            completed_objectives = sum(
                1
                for index in range(total_objectives)
                if self.context.missions.is_objective_complete(mission.mission_id, index)
            )
            card = MissionCard(mission, trip_name, completed_objectives, total_objectives)
            card.set_selected(mission.mission_id == self._selected_mission_id)
            card.activated.connect(self._on_mission_selected)
            card.edit_requested.connect(self._on_edit_mission)
            card.delete_requested.connect(self._on_delete_mission)
            self._mission_cards_layout.addWidget(card)
            card.show()

        self._mission_cards_layout.addStretch()
        self._refresh_objective_cards()

    def _refresh_objective_cards(self) -> None:
        while self._objective_cards_layout.count():
            item = self._objective_cards_layout.takeAt(0)
            card = item.widget()
            if card is not None:
                card.hide()
                card.setParent(None)
                card.deleteLater()

        if self._selected_mission_id is None:
            self._objective_cards_layout.addStretch()
            return

        mission = self.context.missions.get_mission(self._selected_mission_id)
        if mission is None:
            self._objective_cards_layout.addStretch()
            return

        for index, objective in enumerate(mission.objectives):
            progress = self.context.missions.objective_progress(self._selected_mission_id, index) or 0.0
            is_complete = self.context.missions.is_objective_complete(self._selected_mission_id, index)
            card = ObjectiveCard(index, objective, progress, is_complete)
            card.increment_requested.connect(self._on_increment_objective)
            card.delete_requested.connect(self._on_delete_objective)
            self._objective_cards_layout.addWidget(card)
            card.show()

        self._objective_cards_layout.addStretch()

    def _on_mission_selected(self, mission_id: str) -> None:
        self._selected_mission_id = mission_id
        self._refresh_mission_cards()

    # ------------------------------------------------------------------
    # Mission actions
    # ------------------------------------------------------------------

    def _on_add_mission(self) -> None:
        dialog = AddEditMissionDialog(self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.add_mission(name=dialog.entered_name, trip_id=dialog.entered_trip_id)
        self._refresh_mission_cards()

    def _on_edit_mission(self, mission_id: str) -> None:
        mission = self.context.missions.get_mission(mission_id)
        if mission is None:
            return
        dialog = AddEditMissionDialog(self.context, mission=mission)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.update_mission(mission_id, name=dialog.entered_name, status=dialog.entered_status)
        self._refresh_mission_cards()

    def _on_delete_mission(self, mission_id: str) -> None:
        mission = self.context.missions.get_mission(mission_id)
        if mission is None:
            return
        dialog = DeleteConfirmDialog(mission.name, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.delete_mission(mission_id)
        if self._selected_mission_id == mission_id:
            self._selected_mission_id = None
        self._refresh_mission_cards()

    # ------------------------------------------------------------------
    # Objective actions
    # ------------------------------------------------------------------

    def _on_add_objective(self) -> None:
        if self._selected_mission_id is None:
            QMessageBox.information(None, "No Mission Selected", "Select a mission to add an objective to.")
            return

        dialog = AddEditObjectiveDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.add_objective(
            self._selected_mission_id, dialog.entered_description, dialog.entered_metric_type, dialog.entered_target
        )
        self._refresh_objective_cards()

    def _on_increment_objective(self, index: int) -> None:
        if self._selected_mission_id is None:
            return
        mission = self.context.missions.get_mission(self._selected_mission_id)
        if mission is None or not (0 <= index < len(mission.objectives)):
            return
        if mission.objectives[index].metric_type != "tally":
            QMessageBox.information(
                None, "Not a Tally Objective",
                "Only tally-type objectives can be incremented by hand — this one tracks trip time automatically.",
            )
            return

        self.context.missions.increment_tally(self._selected_mission_id, index)
        self._refresh_objective_cards()

    def _on_delete_objective(self, index: int) -> None:
        if self._selected_mission_id is None:
            return
        mission = self.context.missions.get_mission(self._selected_mission_id)
        if mission is None or not (0 <= index < len(mission.objectives)):
            return
        dialog = DeleteConfirmDialog(mission.objectives[index].description, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.delete_objective(self._selected_mission_id, index)
        self._refresh_objective_cards()
