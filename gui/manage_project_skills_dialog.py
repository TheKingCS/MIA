"""
gui.manage_project_skills_dialog
===================================

The one small dialog "My Hero's Path" Phase 2 needs for tagging which
skills a Project trains — reused for BOTH upfront declaration and
retroactive tagging after the fact, since
core.project_manager.ProjectManager.add_skill_weight() already handles
both cases correctly on its own (see that method's own docstring).

Deliberately a "live action" dialog, not a form: each "Add" click
calls add_skill_weight() immediately and refreshes the list right
there — there's no OK/Cancel/Accept step, because by the time a click
lands the credit has already genuinely happened (or is queued for
this Project's next real completion). This is the same shape as
gui/widgets/volume_quick_control.py's live-action pattern, not
gui/add_edit_project_dialog.py's collect-then-submit form pattern —
those are different UI jobs and shouldn't share one convention.

No "remove" in this first pass — deliberately deferred (see
docs/ROADMAP.md's dated entry), matches this codebase's existing
non-destructive-reward bias (a Mission's own reward fields can be
edited, but nothing anywhere retroactively revokes already-granted XP).
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

from core.project_manager import Project


def format_skill_weight_row(context, skill_id: str, xp: int) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_manage_project_skills_dialog.py). Falls back to the raw
    skill_id if the definition has since been removed from
    data/skill_definitions.json — never raises on a stale reference."""
    definition = context.skills.get_skill(skill_id) if context.skills is not None else None
    name = definition.name if definition is not None else skill_id
    return f"{name}: {xp} XP"


class ManageProjectSkillsDialog(QDialog):
    def __init__(self, context, project: Project, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.project = project
        self.setWindowTitle(f"Manage Skills — {project.name}")
        self.setFixedSize(360, 420)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Skills this project trains:"))
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
        for weight in self.project.skill_weights:
            self.weight_list.addItem(QListWidgetItem(format_skill_weight_row(self.context, weight.skill_id, weight.xp)))

    def _on_add(self) -> None:
        skill_id = self.skill_combo.currentData()
        if skill_id is None:
            return
        xp = self.xp_spin.value()
        self.project = self.context.projects.add_skill_weight(self.project.project_id, skill_id, xp)
        self._refresh_weight_list()
