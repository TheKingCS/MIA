"""
gui.add_edit_mission_dialog
==============================

Small dialog for creating or editing a single Mission
(modules/missions/module.py) — name, an optional linked Trip (picked
from a QComboBox of all existing trips, "None" for a general goal not
tied to any outing), and status (edit only). The trip link can't be
changed after creation (mirrors `update_mission()`'s own rejection of a
`trip_id` field change, same reasoning as Trip's fixed `expedition_id`)
— editing an existing Mission shows name/status only, no trip picker.

Connective-infrastructure pass (2026-09-11): gained an optional linked
Project picker, same shape/scoping as the trip picker above — a
Mission can be the gamified "face" of a Project rather than the two
staying unrelated containers for structured work
(core.mission_manager.Mission.project_id). Creation-only, same
reasoning as the trip link.

**2026-07-18 design handoff** (CCH.zip's Mission Log screen): gained
fields for the redesigned detail card/rewards footer — icon (single
emoji glyph, matches this project's icon convention), region (a short
mono "eyebrow" label, free text), summary (the descriptive paragraph),
difficulty, mission type, and reward XP/credits. All optional/defaulted
so existing missions with none of this set still render sensibly (the
module's own formatting functions handle blank/zero gracefully).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.mission_manager import ABANDON_REASONS, DIFFICULTY_LEVELS, Mission

_STATUSES = ("active", "completed", "abandoned")
_MISSION_TYPES = ("OPTIONAL MISSION", "DAILY MISSION", "MAIN MISSION")
_NO_ABANDON_REASON = "(none)"


class AddEditMissionDialog(QDialog):
    def __init__(self, context, parent=None, mission: Optional[Mission] = None) -> None:
        super().__init__(parent)
        self.context = context
        self._editing = mission is not None
        self.setWindowTitle("Edit Mission" if self._editing else "New Mission")
        self.setMinimumWidth(380)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name, e.g. 'Master Angler'")
        layout.addRow("Name:", self.name_edit)

        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("An emoji, e.g. \U0001F3A3")
        self.icon_edit.setMaxLength(4)
        layout.addRow("Icon:", self.icon_edit)

        self.region_edit = QLineEdit()
        self.region_edit.setPlaceholderText("e.g. 'FIELD SEASON · FISHING'")
        layout.addRow("Region/category:", self.region_edit)

        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setFixedHeight(70)
        self.summary_edit.setPlaceholderText("A sentence or two describing this mission.")
        layout.addRow("Summary:", self.summary_edit)

        self.difficulty_combo = QComboBox()
        for level in DIFFICULTY_LEVELS:
            self.difficulty_combo.addItem(level.capitalize(), level)
        layout.addRow("Difficulty:", self.difficulty_combo)

        self.mission_type_combo = QComboBox()
        self.mission_type_combo.setEditable(True)
        for mission_type in _MISSION_TYPES:
            self.mission_type_combo.addItem(mission_type)
        layout.addRow("Mission type:", self.mission_type_combo)

        self.reward_xp_spin = QSpinBox()
        self.reward_xp_spin.setRange(0, 100_000)
        self.reward_xp_spin.setSuffix(" XP")
        layout.addRow("Reward:", self.reward_xp_spin)

        self.reward_credits_spin = QSpinBox()
        self.reward_credits_spin.setRange(0, 100_000)
        self.reward_credits_spin.setPrefix("$")
        layout.addRow("Reward credits:", self.reward_credits_spin)

        self.trip_combo: Optional[QComboBox] = None
        if not self._editing:
            self.trip_combo = QComboBox()
            self.trip_combo.addItem("(None — general goal)", None)
            for trip in context.trips.all_trips():
                self.trip_combo.addItem(trip.name, trip.trip_id)
            layout.addRow("Linked Trip (optional):", self.trip_combo)

        self.project_combo: Optional[QComboBox] = None
        if not self._editing:
            self.project_combo = QComboBox()
            self.project_combo.addItem("(None — general goal)", None)
            if context is not None and context.projects is not None:
                for project in context.projects.all_projects():
                    self.project_combo.addItem(project.name, project.project_id)
            layout.addRow("Linked Project (optional):", self.project_combo)

        # Group quests (2026-09-14) — real party members, creation-only
        # (same "picked once, not reassignable via edit" rule the
        # trip/project links above already follow). Empty by default —
        # a Mission with no boxes checked is a normal solo/unattributed
        # Mission, unchanged.
        self.participant_checkboxes: dict[str, QCheckBox] = {}
        if not self._editing:
            party_widget = QWidget()
            party_layout = QVBoxLayout(party_widget)
            party_layout.setContentsMargins(0, 0, 0, 0)
            if context is not None and context.profiles is not None:
                for profile in context.profiles.list_profiles():
                    checkbox = QCheckBox(profile.name)
                    self.participant_checkboxes[profile.profile_id] = checkbox
                    party_layout.addWidget(checkbox)
            layout.addRow("Party (optional):", party_widget)

        self.status_combo: Optional[QComboBox] = None
        self.abandon_reason_combo: Optional[QComboBox] = None
        if self._editing:
            self.status_combo = QComboBox()
            for status in _STATUSES:
                self.status_combo.addItem(status.capitalize(), status)
            layout.addRow("Status:", self.status_combo)

            # "Mission failure/struggle signal" (2026-09-11) — only
            # meaningful when Status is "Abandoned"; _on_accept() below
            # forces this back to "" whenever the chosen status isn't
            # abandoned, so a stray selection here never sticks to a
            # mission that isn't actually abandoned.
            self.abandon_reason_combo = QComboBox()
            self.abandon_reason_combo.addItem(_NO_ABANDON_REASON, "")
            for reason in ABANDON_REASONS:
                self.abandon_reason_combo.addItem(reason.replace("_", " ").capitalize(), reason)
            layout.addRow("Abandon reason:", self.abandon_reason_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self._prefill(mission)

        self._name: str = ""
        self._trip_id = None
        self._project_id = None
        self._status: str = "active"
        self._icon: str = "\U0001F4CB"
        self._region: str = ""
        self._summary: str = ""
        self._difficulty: str = "NORMAL"
        self._mission_type: str = "OPTIONAL MISSION"
        self._reward_xp: int = 0
        self._reward_credits: int = 0
        self._abandon_reason: str = ""
        self._participant_profile_ids: list[str] = []

    def _prefill(self, mission: Optional[Mission]) -> None:
        if mission is None:
            self.icon_edit.setText("\U0001F4CB")
            return
        self.name_edit.setText(mission.name)
        self.icon_edit.setText(mission.icon)
        self.region_edit.setText(mission.region)
        self.summary_edit.setPlainText(mission.summary)
        difficulty_index = self.difficulty_combo.findData(mission.difficulty)
        self.difficulty_combo.setCurrentIndex(difficulty_index if difficulty_index != -1 else 1)
        self.mission_type_combo.setCurrentText(mission.mission_type)
        self.reward_xp_spin.setValue(mission.reward_xp)
        self.reward_credits_spin.setValue(mission.reward_credits)
        if self.status_combo is not None:
            status_index = self.status_combo.findData(mission.status)
            self.status_combo.setCurrentIndex(status_index if status_index != -1 else 0)
        if self.abandon_reason_combo is not None:
            reason_index = self.abandon_reason_combo.findData(mission.abandon_reason)
            self.abandon_reason_combo.setCurrentIndex(reason_index if reason_index != -1 else 0)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._icon = self.icon_edit.text().strip() or "\U0001F4CB"
        self._region = self.region_edit.text().strip()
        self._summary = self.summary_edit.toPlainText().strip()
        self._difficulty = self.difficulty_combo.currentData()
        self._mission_type = self.mission_type_combo.currentText().strip() or "OPTIONAL MISSION"
        self._reward_xp = self.reward_xp_spin.value()
        self._reward_credits = self.reward_credits_spin.value()
        if self.trip_combo is not None:
            self._trip_id = self.trip_combo.currentData()
        if self.project_combo is not None:
            self._project_id = self.project_combo.currentData()
        self._participant_profile_ids = [
            profile_id for profile_id, checkbox in self.participant_checkboxes.items() if checkbox.isChecked()
        ]
        if self.status_combo is not None:
            self._status = self.status_combo.currentData()
        self._abandon_reason = (
            self.abandon_reason_combo.currentData()
            if self.abandon_reason_combo is not None and self._status == "abandoned"
            else ""
        )
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_trip_id(self):
        return self._trip_id

    @property
    def entered_project_id(self):
        return self._project_id

    @property
    def entered_status(self) -> str:
        return self._status

    @property
    def entered_icon(self) -> str:
        return self._icon

    @property
    def entered_region(self) -> str:
        return self._region

    @property
    def entered_summary(self) -> str:
        return self._summary

    @property
    def entered_difficulty(self) -> str:
        return self._difficulty

    @property
    def entered_mission_type(self) -> str:
        return self._mission_type

    @property
    def entered_reward_xp(self) -> int:
        return self._reward_xp

    @property
    def entered_reward_credits(self) -> int:
        return self._reward_credits

    @property
    def entered_abandon_reason(self) -> str:
        return self._abandon_reason

    @property
    def entered_participant_profile_ids(self) -> list[str]:
        return self._participant_profile_ids
