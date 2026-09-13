"""
gui.manage_mission_skills_dialog
===================================

The Mission-side twin of gui.manage_project_skills_dialog — same
"live action" shape (each "Add" click calls add_skill_reward()
immediately and refreshes the list right there, no OK/Cancel/Accept
step), reused for both upfront declaration and retroactive tagging
since core.mission_manager.MissionManager.add_skill_reward() already
handles both cases correctly (see that method's own docstring).

No "remove" in this first pass — same deliberate deferral
gui.manage_project_skills_dialog.py already takes, matching this
codebase's existing non-destructive-reward bias.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.mission_manager import Mission


def format_skill_reward_row(context, skill_id: str, xp: int) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_manage_mission_skills_dialog.py). Falls back to the raw
    skill_id if the definition has since been removed from
    data/skill_definitions.json — never raises on a stale reference."""
    definition = context.skills.get_skill(skill_id) if context.skills is not None else None
    name = definition.name if definition is not None else skill_id
    return f"{name}: {xp} XP"


class ManageMissionSkillsDialog(QDialog):
    def __init__(self, context, mission: Mission, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.mission = mission
        self.setWindowTitle(f"Manage Skills — {mission.name}")
        self.setFixedSize(360, 420)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Skills this mission rewards:"))
        self.weight_list = QListWidget()
        layout.addWidget(self.weight_list, stretch=1)

        layout.addWidget(QLabel("Add a skill credit:"))
        self.skill_combo = QComboBox()
        skills = self.context.skills.all_skills() if self.context.skills is not None else []
        for definition in sorted(skills, key=lambda d: (d.category, d.name)):
            self.skill_combo.addItem(f"{definition.category} — {definition.name}", definition.skill_id)
        layout.addWidget(self.skill_combo)

        xp_row = QHBoxLayout()
        xp_row.addWidget(QLabel("XP:"))
        self.xp_spin = QSpinBox()
        self.xp_spin.setRange(1, 500)
        self.xp_spin.setValue(10)
        xp_row.addWidget(self.xp_spin)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._on_add)
        xp_row.addWidget(add_button)
        layout.addLayout(xp_row)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self._refresh_weight_list()

    def _refresh_weight_list(self) -> None:
        self.weight_list.clear()
        for weight in self.mission.skill_rewards:
            self.weight_list.addItem(QListWidgetItem(format_skill_reward_row(self.context, weight.skill_id, weight.xp)))

    def _on_add(self) -> None:
        skill_id = self.skill_combo.currentData()
        if skill_id is None:
            return
        xp = self.xp_spin.value()
        self.mission = self.context.missions.add_skill_reward(self.mission.mission_id, skill_id, xp)
        self._refresh_weight_list()
