"""
modules.missions.module
==========================

Mission Log — docs/ROADMAP.md milestone v0.18, module #20. Rebuilt
2026-07-18 against a design handoff (CCH.zip's Missions.dc.html) as a
two-panel "Mission Log": a detail panel (icon/title/region, summary,
an objectives checklist, difficulty/level tags, a rewards footer) on
the left, and a mission list (ACTIVE/COMPLETED, sticky Level+XP footer)
on the right — replacing the previous single-column "Missions list
above Objectives list" layout entirely, not just restyling it.

The list's sticky footer reads the active profile's real level/XP
(`core.leveling.compute_level_progress()`, driven by
`core.mission_manager.MissionManager`'s reward-crediting on mission
completion — see that module's docstring) — this is real gamification
state now, not the design mockup's static placeholder numbers.

format_mission_row()/format_objective_row() are kept, still tested
(tests/test_missions_module.py) — they were never actually rendered as
literal list rows even before this rewrite (MissionCard/ObjectiveCard
built their own richer display), so nothing here depends on changing
them.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.leveling import compute_level_progress
from core.mission_manager import Mission, Objective
from gui.add_edit_mission_dialog import AddEditMissionDialog
from gui.add_edit_objective_dialog import AddEditObjectiveDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from gui.widgets.mission_list_row import MissionListRow
from gui.widgets.objective_checklist_row import ObjectiveChecklistRow
from modules.module_base import ModuleBase


def format_mission_row(mission: Mission, trip_name: str = "") -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    trip_part = f"  [{trip_name}]" if trip_name else ""
    return f"{mission.name}{trip_part}  ({mission.status})"


def format_objective_row(objective: Objective, progress: float, is_complete: bool) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    mark = "[x]" if is_complete else "[ ]"
    return f"{mark} {objective.description}: {progress:g} of {objective.target:g}"


def format_rewards_line(reward_credits: int, reward_xp: int) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    return f"${reward_credits:,}    {reward_xp:,} XP"


def format_level_footer_line(level: int, xp_into_level: int, xp_needed: int) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py)."""
    return f"Level {level}    {xp_into_level:,} / {xp_needed:,}"


def format_objectives_heading(completed: int, total: int) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py).
    Preserves the pre-redesign MissionCard's aggregate progress bar as plain text
    in the new checklist-style detail panel — a real, previously-shipped feature,
    not something to silently drop just because the design mockup didn't have it."""
    if total == 0:
        return "OBJECTIVES"
    return f"OBJECTIVES — {completed} of {total} complete"


def format_checklist_label(description: str, progress: float, target: float, is_complete: bool) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_missions_module.py).
    Appends a "(2 of 3)" fraction for any not-yet-complete objective whose target
    is more than a single step — a checkbox alone can't show partial tally/hours
    progress the way the pre-redesign ObjectiveCard's QProgressBar did."""
    if is_complete or target <= 1:
        return description
    return f"{description} ({progress:g} of {target:g})"


class MissionsModule(ModuleBase):
    module_id = "missions"
    display_name = "Missions"
    description = "Gamified goals and objectives, tied to a trip or general."
    icon = "\U0001F3C6"  # trophy

    def __init__(self, context) -> None:
        super().__init__(context)
        self._detail_container: Optional[QWidget] = None
        self._detail_layout: Optional[QVBoxLayout] = None
        self._list_active_layout: Optional[QVBoxLayout] = None
        self._list_completed_layout: Optional[QVBoxLayout] = None
        self._active_count_label: Optional[QLabel] = None
        self._level_footer_label: Optional[QLabel] = None
        self._level_footer_bar: Optional[QWidget] = None
        self._selected_mission_id: Optional[str] = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        title_row = QHBoxLayout()
        title_label = QLabel(f"{self.icon}  Mission Log")
        title_label.setObjectName("TitleLabel")
        title_row.addWidget(title_label)
        title_row.addStretch()
        self._active_count_label = QLabel("")
        self._active_count_label.setObjectName("MissionActiveCountPill")
        title_row.addWidget(self._active_count_label)
        outer.addLayout(title_row)

        add_row = QHBoxLayout()
        add_mission_button = QPushButton("+ Add Mission")
        add_mission_button.clicked.connect(self._on_add_mission)
        add_row.addWidget(add_mission_button)
        add_row.addStretch()
        outer.addLayout(add_row)

        body = QHBoxLayout()
        body.setSpacing(18)
        body.addWidget(self._build_detail_panel(), stretch=10)
        body.addWidget(self._build_list_panel(), stretch=7)
        outer.addLayout(body, stretch=1)

        self._refresh()
        return widget

    # ------------------------------------------------------------------
    # Panel construction
    # ------------------------------------------------------------------

    def _build_detail_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("MissionDetailPanel")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._detail_container = QWidget()
        self._detail_container.setObjectName("DashboardCard")
        self._detail_layout = QVBoxLayout(self._detail_container)
        self._detail_layout.setContentsMargins(22, 20, 22, 20)
        self._detail_layout.setSpacing(10)

        scroll.setWidget(self._detail_container)
        return scroll

    def _build_list_panel(self) -> QWidget:
        container = QWidget()
        container.setObjectName("DashboardCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 18, 20, 0)
        layout.setSpacing(4)

        world_label = QLabel("WORLD MISSIONS")
        world_label.setObjectName("DashboardSectionTitle")
        layout.addWidget(world_label)

        active_label = QLabel("ACTIVE")
        active_label.setObjectName("MissionListSectionActive")
        layout.addWidget(active_label)

        active_scroll = QScrollArea()
        active_scroll.setWidgetResizable(True)
        active_scroll.setFrameShape(QFrame.Shape.NoFrame)
        active_container = QWidget()
        self._list_active_layout = QVBoxLayout(active_container)
        self._list_active_layout.setContentsMargins(0, 0, 0, 0)
        self._list_active_layout.setSpacing(2)
        active_scroll.setWidget(active_container)
        layout.addWidget(active_scroll, stretch=1)

        completed_label = QLabel("COMPLETED")
        completed_label.setObjectName("MissionListSectionCompleted")
        layout.addWidget(completed_label)

        completed_scroll = QScrollArea()
        completed_scroll.setWidgetResizable(True)
        completed_scroll.setFrameShape(QFrame.Shape.NoFrame)
        completed_container = QWidget()
        self._list_completed_layout = QVBoxLayout(completed_container)
        self._list_completed_layout.setContentsMargins(0, 0, 0, 0)
        self._list_completed_layout.setSpacing(2)
        completed_scroll.setWidget(completed_container)
        layout.addWidget(completed_scroll, stretch=1)

        footer = QWidget()
        footer.setObjectName("MissionLevelFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 10)
        self._level_footer_label = QLabel("")
        self._level_footer_label.setObjectName("MissionLevelFooterText")
        footer_layout.addWidget(self._level_footer_label)
        layout.addWidget(footer)

        return container

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        missions = self.context.missions.all_missions()
        if self._selected_mission_id is None or not any(
            m.mission_id == self._selected_mission_id for m in missions
        ):
            active_missions = [m for m in missions if m.status == "active"]
            first = active_missions[0] if active_missions else (missions[0] if missions else None)
            self._selected_mission_id = first.mission_id if first is not None else None

        active_count = sum(1 for m in missions if m.status == "active")
        self._active_count_label.setText(f"● {active_count} ACTIVE")

        self._refresh_list(missions)
        self._refresh_detail()
        self._refresh_level_footer()

    def _refresh_list(self, missions: list[Mission]) -> None:
        for layout in (self._list_active_layout, self._list_completed_layout):
            while layout.count():
                item = layout.takeAt(0)
                row = item.widget()
                if row is not None:
                    row.hide()
                    row.setParent(None)
                    row.deleteLater()

        for mission in missions:
            if mission.status != "active":
                continue
            row = MissionListRow(mission.mission_id, mission.icon, mission.name)
            row.set_selected(mission.mission_id == self._selected_mission_id)
            row.activated.connect(self._on_mission_selected)
            self._list_active_layout.addWidget(row)
        self._list_active_layout.addStretch()

        for mission in missions:
            if mission.status != "completed":
                continue
            row = MissionListRow(mission.mission_id, mission.icon, mission.name, completed=True)
            row.set_selected(mission.mission_id == self._selected_mission_id)
            row.activated.connect(self._on_mission_selected)
            self._list_completed_layout.addWidget(row)
        self._list_completed_layout.addStretch()

    def _refresh_detail(self) -> None:
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.hide()
                child.setParent(None)
                child.deleteLater()

        mission = (
            self.context.missions.get_mission(self._selected_mission_id)
            if self._selected_mission_id is not None
            else None
        )
        if mission is None:
            empty_label = QLabel("No missions yet — add one to get started.")
            empty_label.setObjectName("SubtitleLabel")
            self._detail_layout.addWidget(empty_label)
            return

        # Wrapped in a real QWidget (not a bare addLayout()) so
        # _refresh_detail()'s cleanup loop above can actually reach and
        # remove these child widgets next time — a nested layout handed
        # to addLayout() has no QWidget of its own for takeAt() to hide/
        # reparent/delete, so its children silently stayed on screen,
        # ghosting on top of the next mission's render. Found via a real
        # screenshot (overlapping title/region/tag text), not assumed —
        # same class of bug this project has hit before (see
        # gui/character_panel.py's _refresh_suggestions() docstring).
        header_widget = QWidget()
        header_row = QHBoxLayout(header_widget)
        header_row.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(mission.icon)
        icon_label.setObjectName("MissionDetailIcon")
        header_row.addWidget(icon_label)
        name_row = QVBoxLayout()
        title_line = QHBoxLayout()
        name_label = QLabel(mission.name)
        name_label.setObjectName("MissionDetailTitle")
        name_label.setWordWrap(True)
        title_line.addWidget(name_label, stretch=1)
        # 2026-07-16 gamification pass's "quest giver" badge — a real,
        # pre-existing feature ("MIA should assign me missions
        # sometimes") this rebuild must keep, not silently drop just
        # because the design mockup's own placeholder data never
        # exercised it.
        if mission.assigned_by == "mia":
            badge = QLabel("MIA ASSIGNED")
            badge.setObjectName("MissionCardBadge")
            title_line.addWidget(badge)
        name_row.addLayout(title_line)
        if mission.region:
            region_label = QLabel(mission.region)
            region_label.setObjectName("MissionDetailRegion")
            name_row.addWidget(region_label)
        header_row.addLayout(name_row, stretch=1)
        edit_button = QPushButton("✎")
        edit_button.setObjectName("HeaderButton")
        edit_button.setFixedWidth(32)
        edit_button.setToolTip("Edit this mission")
        edit_button.clicked.connect(lambda: self._on_edit_mission(mission.mission_id))
        header_row.addWidget(edit_button)
        delete_button = QPushButton("✕")
        delete_button.setObjectName("HeaderButton")
        delete_button.setFixedWidth(32)
        delete_button.setToolTip("Delete this mission")
        delete_button.clicked.connect(lambda: self._on_delete_mission(mission.mission_id))
        header_row.addWidget(delete_button)
        self._detail_layout.addWidget(header_widget)

        if mission.summary:
            summary_label = QLabel(mission.summary)
            summary_label.setObjectName("MissionDetailSummary")
            summary_label.setWordWrap(True)
            self._detail_layout.addWidget(summary_label)

        completed_objectives = sum(
            1 for index in range(len(mission.objectives)) if self.context.missions.is_objective_complete(mission.mission_id, index)
        )
        objectives_title = QLabel(format_objectives_heading(completed_objectives, len(mission.objectives)))
        objectives_title.setObjectName("DashboardSectionTitle")
        self._detail_layout.addWidget(objectives_title)

        for index, objective in enumerate(mission.objectives):
            progress = self.context.missions.objective_progress(mission.mission_id, index) or 0.0
            is_complete = self.context.missions.is_objective_complete(mission.mission_id, index)
            label_text = format_checklist_label(objective.description, progress, objective.target, is_complete)
            row = ObjectiveChecklistRow(
                index, label_text, is_complete, objective.metric_type == "tally", is_multi_step=objective.target > 1
            )
            row.increment_requested.connect(self._on_increment_objective)
            row.delete_requested.connect(self._on_delete_objective)
            self._detail_layout.addWidget(row)

        add_objective_button = QPushButton("+ Add Objective")
        add_objective_button.setObjectName("HeaderButton")
        add_objective_button.clicked.connect(self._on_add_objective)
        self._detail_layout.addWidget(add_objective_button)

        tag_widget = QWidget()
        tag_row = QHBoxLayout(tag_widget)
        tag_row.setContentsMargins(0, 0, 0, 0)
        level_tag = QLabel(f"{mission.difficulty}")
        level_tag.setObjectName("MissionDifficultyTag")
        tag_row.addWidget(level_tag)
        tag_row.addStretch()
        self._detail_layout.addWidget(tag_widget)

        self._detail_layout.addStretch()

        rewards_footer = QWidget()
        rewards_footer.setObjectName("MissionRewardsFooter")
        rewards_layout = QHBoxLayout(rewards_footer)
        rewards_layout.setContentsMargins(16, 12, 16, 12)
        rewards_text = QLabel(format_rewards_line(mission.reward_credits, mission.reward_xp))
        rewards_text.setObjectName("MissionRewardsText")
        rewards_layout.addWidget(rewards_text)
        rewards_layout.addStretch()
        mission_type_label = QLabel(mission.mission_type)
        mission_type_label.setObjectName("MissionTypeLabel")
        rewards_layout.addWidget(mission_type_label)
        self._detail_layout.addWidget(rewards_footer)

    def _refresh_level_footer(self) -> None:
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        total_xp = active_profile.total_xp if active_profile is not None else 0
        level, xp_into_level, xp_needed = compute_level_progress(total_xp)
        self._level_footer_label.setText(format_level_footer_line(level, xp_into_level, xp_needed))

    def _on_mission_selected(self, mission_id: str) -> None:
        self._selected_mission_id = mission_id
        self._refresh()

    # ------------------------------------------------------------------
    # Mission actions
    # ------------------------------------------------------------------

    def _on_add_mission(self) -> None:
        dialog = AddEditMissionDialog(self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        mission = self.context.missions.add_mission(
            name=dialog.entered_name,
            trip_id=dialog.entered_trip_id,
            project_id=dialog.entered_project_id,
            icon=dialog.entered_icon,
            region=dialog.entered_region,
            summary=dialog.entered_summary,
            difficulty=dialog.entered_difficulty,
            mission_type=dialog.entered_mission_type,
            reward_xp=dialog.entered_reward_xp,
            reward_credits=dialog.entered_reward_credits,
        )
        self._selected_mission_id = mission.mission_id
        self._refresh()

    def _on_edit_mission(self, mission_id: str) -> None:
        mission = self.context.missions.get_mission(mission_id)
        if mission is None:
            return
        dialog = AddEditMissionDialog(self.context, mission=mission)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.missions.update_mission(
            mission_id,
            name=dialog.entered_name,
            status=dialog.entered_status,
            icon=dialog.entered_icon,
            region=dialog.entered_region,
            summary=dialog.entered_summary,
            difficulty=dialog.entered_difficulty,
            mission_type=dialog.entered_mission_type,
            reward_xp=dialog.entered_reward_xp,
            reward_credits=dialog.entered_reward_credits,
        )
        self._refresh()

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
        self._refresh()

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
        self._refresh()

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
        self._refresh()

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
        self._refresh()
