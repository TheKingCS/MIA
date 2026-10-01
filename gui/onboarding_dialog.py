"""
gui.onboarding_dialog
=======================

"Getting to know you" (2026-10-01, accounts stage 2): right after a new
account is made, MIA asks a few questions, one at a time, as a
conversation: what she should help with most, how often to speak up,
and anything else she should know. Then she says what she'll put first
on the Apps screen (core/focus_presets.py) and does it when you agree.

Replaces the older checkbox interview at account creation: the goals
fill in the Skills interests too, and the last answer is the interview
notes (memories are pulled from it later, gui/home_dashboard.py). Every
answer is optional; Skip keeps every app showing as before.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import focus_presets, person_settings
from core.focus_presets import GOALS, SPEAK_UP
from core.logger import get_logger
from core.personal_data import ScopedView

log = get_logger(__name__)


def _bubble(text: str, mine: bool = False) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(
        "padding: 8px 12px; border-radius: 10px; color: #e6edf3; "
        + ("background-color: #1f3a5f; margin-left: 60px;" if mine else "background-color: #23302b; margin-right: 60px;")
    )
    return label


class OnboardingDialog(QDialog):
    def __init__(self, context, profile, module_names: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.profile = profile
        self.module_names = module_names
        # Answers are saved for this person, whoever is signed in at the desktop.
        personal = getattr(context, "personal_data", None)
        self.person = (personal.view(profile.profile_id) if personal is not None
                       else ScopedView(context, (), profile_id=profile.profile_id))
        self.goals: list[str] = []
        self.speak_up: int = 5
        self.notes = ""
        self.recommendation = None
        self._handler = None
        self.setWindowTitle("Getting to know you")
        self.setMinimumSize(520, 560)

        layout = QVBoxLayout(self)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        self._conversation = QVBoxLayout(holder)
        self._conversation.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(holder)
        layout.addWidget(self._scroll, stretch=1)
        self._answer_area = QVBoxLayout()
        layout.addLayout(self._answer_area)
        row = QHBoxLayout()
        self.skip_button = QPushButton("Skip")
        self.skip_button.clicked.connect(self.reject)
        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("ModuleButton")
        row.addWidget(self.skip_button)
        row.addStretch(1)
        row.addWidget(self.next_button)
        layout.addLayout(row)

        self._say(f"Hi {profile.name}! I'm MIA. A few quick questions so I can put the right things in front of you.")
        self._ask_goals()

    # ------------------------------------------------------------------

    def _say(self, text: str, mine: bool = False) -> None:
        self._conversation.addWidget(_bubble(text, mine))
        bar = self._scroll.verticalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def _clear_answers(self) -> None:
        while self._answer_area.count():
            item = self._answer_area.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _next(self, handler) -> None:
        if self._handler is not None:
            self.next_button.clicked.disconnect(self._handler)
        self._handler = handler
        self.next_button.clicked.connect(handler)

    def _ask_goals(self) -> None:
        self._say("What should I help you with most? Pick as many as you like.")
        chips = QWidget()
        grid = QVBoxLayout(chips)
        grid.setContentsMargins(0, 0, 0, 0)
        self._goal_buttons = {}
        for goal_id, label in GOALS:
            button = QPushButton(label)
            button.setCheckable(True)
            self._goal_buttons[goal_id] = button
            grid.addWidget(button)
        self._answer_area.addWidget(chips)
        self._next(self._on_goals)

    def _on_goals(self) -> None:
        self.goals = [g for g, b in self._goal_buttons.items() if b.isChecked()]
        names = dict(GOALS)
        self._say(", ".join(names[g] for g in self.goals) if self.goals else "Not sure yet.", mine=True)
        self._clear_answers()
        self._say("How often should I speak up on my own (reminders, check-ins, ideas)? "
                  "Urgent things and alarms always come through.")
        box = QWidget()
        column = QVBoxLayout(box)
        column.setContentsMargins(0, 0, 0, 0)
        self._speak_group = QButtonGroup(self)
        for index, (_key, label, count) in enumerate(SPEAK_UP):
            radio = QRadioButton(label)
            radio.setChecked(count == 5)
            self._speak_group.addButton(radio, index)
            column.addWidget(radio)
        self._answer_area.addWidget(box)
        self._next(self._on_speak_up)

    def _on_speak_up(self) -> None:
        _key, label, self.speak_up = SPEAK_UP[max(0, self._speak_group.checkedId())]
        self._say(label, mine=True)
        self._clear_answers()
        self._say("Anything else I should know? Your goals, what you take care of, what you're working toward. "
                  "(Optional.)")
        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText('e.g. "I run a mowing business and I\'m saving for a tractor"')
        self._notes_edit.setMaximumHeight(90)
        self._answer_area.addWidget(self._notes_edit)
        self._next(self._on_notes)

    def _on_notes(self) -> None:
        self.notes = self._notes_edit.toPlainText().strip()
        if self.notes:
            self._say(self.notes, mine=True)
        self._clear_answers()
        self.recommendation = focus_presets.recommend(self.goals)
        self._say(focus_presets.describe(self.recommendation, self.module_names))
        # Starter sets (core/starter_templates.py) the goals suggest, so
        # there's something to check off on day one. Ticked by default;
        # "Show me everything" adds none.
        from core.starter_templates import STARTERS, for_goals

        self.starter_checks = {}
        suggested = for_goals(self.goals)
        if suggested:
            self._say("I can also fill in the usual things to start with (rename or delete anything later):")
            for starter_id in suggested:
                starter = STARTERS[starter_id]
                check = QCheckBox(f"{starter.name}: {starter.description}")
                check.setChecked(True)
                self.starter_checks[starter_id] = check
                self._answer_area.addWidget(check)
        self.next_button.setText("Sounds good")
        self.skip_button.setText("Show me everything")
        self._next(self._on_agree)

    def _on_agree(self) -> None:
        self.save(apply_focus=True)
        from core import starter_templates

        for starter_id, check in getattr(self, "starter_checks", {}).items():
            if check.isChecked():
                try:
                    starter_templates.apply(self.person, starter_id)
                except Exception:  # a starter set never stops setup from finishing
                    log.exception("Couldn't add the %s starter set.", starter_id)
        self.accept()

    def reject(self) -> None:
        # Skipping still keeps what was answered, just not the app focus.
        self.save(apply_focus=False)
        super().reject()

    def save(self, apply_focus: bool) -> None:
        person_settings.put(self.person, "setup.questions_done", True)
        if self.recommendation is None and not self.goals:
            return
        person_settings.put(self.person, "communication.daily_budget", int(self.speak_up))
        profiles = self.context.profiles
        skills = getattr(self.context, "skills", None)
        categories = skills.categories() if skills is not None else []
        profiles.set_interview_answers(self.profile.profile_id, focus_presets.interests_for(self.goals, categories),
                                       self.notes)
        if apply_focus and self.recommendation is not None:
            focus_presets.apply(self.person, self.recommendation)


def module_names(module_manager) -> dict[str, str]:
    return {m.module_id: m.display_name for m in module_manager.all()} if module_manager is not None else {}
