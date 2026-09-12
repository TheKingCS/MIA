"""
gui.add_edit_classroom_lesson_dialog
========================================

Small dialog for creating or editing a Lesson within a Course
(modules/classroom/module.py) — name, freeform notes (content/
summary/materials), and an optional skill it trains. `completed` is
deliberately NOT editable here — it's flipped via the Lessons list's
own Mark Complete/Incomplete button (modules/classroom/module.py),
same "a real, deliberate action, not an incidental field on an edit
form" reasoning gui/add_edit_mission_dialog.py's status combo does NOT
follow for Missions (that one IS editable here) but Pathways/
Discovery-generated Missions already established for their own
completion — mirrored here since marking a lesson done is exactly that
kind of deliberate action. `course_id` is fixed at creation, same
reasoning as gui/add_edit_classroom_course_dialog.py's subject_id.

"Wire Classroom into Hero's Path" (2026-09-12): the skill picker is
deliberately a single (skill_id, xp) pair, not a full multi-weight list
editor — even core.mission_manager.Mission's own dialog doesn't expose
multi-skill-weight editing yet either, so this doesn't overbuild past
what Mission's own UI already offers.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.classroom_manager import Lesson
from core.gamification import SkillWeight


class AddEditLessonDialog(QDialog):
    def __init__(self, context, parent=None, lesson: Optional[Lesson] = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Edit Lesson" if lesson is not None else "New Lesson")
        self.setFixedSize(360, 420)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 'Ohm's Law and Series Circuits'")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Content, summary, or materials (optional)")
        layout.addWidget(self.notes_edit, stretch=1)

        layout.addWidget(QLabel("Trains skill (optional):"))
        self.skill_combo = QComboBox()
        self.skill_combo.addItem("(None)", None)
        if self.context is not None and self.context.skills is not None:
            for skill in self.context.skills.all_skills():
                self.skill_combo.addItem(skill.name, skill.skill_id)
        layout.addWidget(self.skill_combo)

        layout.addWidget(QLabel("XP:"))
        self.xp_spin = QSpinBox()
        self.xp_spin.setRange(1, 100)
        self.xp_spin.setValue(10)
        layout.addWidget(self.xp_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(lesson)

        self._name: str = ""
        self._notes: str = ""
        self._skill_rewards: list[SkillWeight] = []

    def _prefill(self, lesson: Optional[Lesson]) -> None:
        if lesson is None:
            return
        self.name_edit.setText(lesson.name)
        self.notes_edit.setPlainText(lesson.notes)
        if lesson.skill_rewards:
            weight = lesson.skill_rewards[0]
            skill_index = self.skill_combo.findData(weight.skill_id)
            self.skill_combo.setCurrentIndex(skill_index if skill_index != -1 else 0)
            self.xp_spin.setValue(weight.xp)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._notes = self.notes_edit.toPlainText()
        skill_id = self.skill_combo.currentData()
        self._skill_rewards = [SkillWeight(skill_id=skill_id, xp=self.xp_spin.value())] if skill_id else []
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_notes(self) -> str:
        return self._notes

    @property
    def entered_skill_rewards(self) -> list[SkillWeight]:
        return self._skill_rewards
