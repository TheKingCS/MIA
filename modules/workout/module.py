"""
modules.workout.module
=========================

Workout: an exercise library, named workout templates, a live guided
session (real elapsed time from a real stopwatch, not a guess), a
session history, and per-exercise progress (personal records + a
weight-over-time chart). All persistence/reporting logic lives in
core/workout_manager.py (self.context.workout) — this module is the
Qt-facing wrapper around it, same split as every other data-backed
module here.

Five tabs (Exercises/Templates/Log Session/History/Progress) — a
plain button row + QStackedWidget (the "Nature" re-skin's own tab
convention, ported from modules/garage/module.py; not QPushButton
QTabWidget's own unstyled default chrome), same "every tab refreshes
on every tab switch" fix modules/kitchen/module.py's own QTabWidget
still uses, applied proactively here from the start (History/Progress
both depend on whatever Log Session just saved).

**"Nature" re-skin rollout (2026-09-14)**: photo hero header + the
same tab-bar convention as Garage/Greenhouse's detail pages. Log
Session specifically also gained a real "Daily Mission" card — any
active Fitness-category core.recurring_mission_manager template
(e.g. the real Push-ups goal) shown alongside the session form,
matching the user's own reference mockup. Every other tab's own
internal content (lists/forms/combos) is unchanged this pass — only
the outer shell and Log Session were touched.

The Log Session tab is the one genuinely new interaction in this app:
a live, in-memory state machine (nothing written to core/workout_manager.py
until "Finish Session"). Real elapsed time comes from time.monotonic()
deltas — never datetime.now(), which can jump on a clock adjustment —
same precedent modules/toolbox/tools/stopwatch_tool.py already
established, including its own 100ms QTimer display-refresh interval.
format_elapsed() is deliberately its OWN small copy here rather than
an import from that file — modules never import each other directly
(CLAUDE.md's layering rule), and modules/real_estate/module.py's own
docstring already states the same call for its own near-identical
formatters ("independently-owned free functions here, not imported
from modules.budget.module").

The current exercise during a live session is a plain combo box the
user can change freely at any time (not a strict linear "Next
Exercise" queue) — real workouts revisit exercises, superset, and
don't always proceed in a fixed order.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Optional

from PySide6.QtCharts import QBarCategoryAxis, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.workout_manager import Exercise, WorkoutSession, WorkoutTemplate
from gui.add_edit_exercise_dialog import AddEditExerciseDialog
from gui.add_edit_workout_template_dialog import AddEditWorkoutTemplateDialog
from gui.add_template_exercise_dialog import AddTemplateExerciseDialog
from gui.list_widget_helpers import add_empty_state_item, selected_item_data
from gui.log_set_dialog import LogSetDialog
from gui.widgets.photo_background_frame import PhotoBackgroundFrame
from modules.module_base import ModuleBase

_DISPLAY_INTERVAL_MS = 100


def format_elapsed(total_ms: int) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_workout_module.py). "MM:SS" for under an hour,
    "HH:MM:SS" once it runs past one — same shape as
    modules.toolbox.tools.stopwatch_tool.format_elapsed(), minus the
    tenths-of-a-second digit (not meaningful for a workout session)."""
    if total_ms < 0:
        raise ValueError("total_ms must be non-negative.")
    total_seconds = total_ms // 1000
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_exercise_row(exercise: Exercise) -> str:
    """Pure formatting logic — testable without Qt."""
    equipment_part = f"  ({exercise.equipment})" if exercise.equipment else ""
    return f"{exercise.name}   [{exercise.category}]{equipment_part}"


def format_template_row(template: WorkoutTemplate) -> str:
    """Pure formatting logic — testable without Qt."""
    count = len(template.exercises)
    noun = "exercise" if count == 1 else "exercises"
    return f"{template.name}   ({count} {noun})"


def format_session_row(session: WorkoutSession, template_name: str) -> str:
    """Pure formatting logic — testable without Qt."""
    count = len(session.sets_logged)
    noun = "set" if count == 1 else "sets"
    return f"{session.date}   {template_name}   {session.duration_minutes:.0f} min   {count} {noun}"


class WorkoutModule(ModuleBase):
    module_id = "workout"
    display_name = "Workout"
    description = "Exercises, templates, guided sessions, and progress."
    icon = "\U0001F3CB"  # weightlifter

    def __init__(self, context) -> None:
        super().__init__(context)
        self._exercise_list: Optional[QListWidget] = None

        self._template_list: Optional[QListWidget] = None
        self._template_exercises_list: Optional[QListWidget] = None
        self._selected_template_id_for_detail: Optional[str] = None

        self._history_list: Optional[QListWidget] = None
        self._history_detail_list: Optional[QListWidget] = None

        self._progress_exercise_combo: Optional[QComboBox] = None
        self._progress_pr_label: Optional[QLabel] = None
        self._progress_chart_view: Optional[QChartView] = None

        # Live session state — nothing here is persisted until Finish
        # Session (see module docstring).
        self._session_active = False
        self._session_start_monotonic: Optional[float] = None
        self._session_sets_logged: list[dict] = []
        self._session_template_id: str = ""
        self._resting = False
        self._rest_start_monotonic: Optional[float] = None
        self._session_timer = QTimer()
        self._session_timer.setInterval(_DISPLAY_INTERVAL_MS)
        self._session_timer.timeout.connect(self._update_session_display)

        self._session_template_combo: Optional[QComboBox] = None
        self._start_session_button: Optional[QPushButton] = None
        self._finish_session_button: Optional[QPushButton] = None
        self._session_elapsed_label: Optional[QLabel] = None
        self._session_exercise_combo: Optional[QComboBox] = None
        self._log_set_button: Optional[QPushButton] = None
        self._rest_button: Optional[QPushButton] = None
        self._rest_elapsed_label: Optional[QLabel] = None
        self._session_sets_list: Optional[QListWidget] = None
        self._session_calories_spin: Optional[QDoubleSpinBox] = None

    def refresh(self) -> None:
        """Re-read every list (ModuleBase.refresh: records changed elsewhere, e.g. by voice)."""
        self._refresh_exercise_list()
        self._refresh_history_list()
        self._refresh_template_list()

    def get_widget(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background-color: #070f0d;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(150)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 20, 28, 16)
        hero_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        icon_badge = QLabel(self.icon)
        icon_badge.setObjectName("NatureIconBadge")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(icon_badge)
        title = QLabel(self.display_name)
        title.setObjectName("NatureHeaderTitle")
        header_row.addWidget(title)
        header_row.addStretch(1)
        hero_layout.addLayout(header_row)

        tagline = QLabel(self.description)
        tagline.setObjectName("NatureHeaderTagline")
        hero_layout.addWidget(tagline)
        hero_layout.addStretch(1)

        outer.addWidget(hero)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 0)
        body_layout.setSpacing(12)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(24)
        stack = QStackedWidget()
        tab_pages = {
            "Exercises": self._build_exercises_tab(),
            "Templates": self._build_templates_tab(),
            "Log Session": self._build_log_session_tab(),
            "History": self._build_history_tab(),
            "Progress": self._build_progress_tab(),
        }
        tab_buttons: dict[str, QPushButton] = {}

        def _select_tab(name: str) -> None:
            for key, button in tab_buttons.items():
                button.setProperty("active", key == name)
                button.style().unpolish(button)
                button.style().polish(button)
            stack.setCurrentWidget(tab_pages[name])
            self._on_tab_changed(0)

        for name, tab_widget in tab_pages.items():
            button = QPushButton(name)
            button.setObjectName("NatureTabButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, n=name: _select_tab(n))
            tab_buttons[name] = button
            tab_row.addWidget(button)
            stack.addWidget(tab_widget)
        tab_row.addStretch(1)
        body_layout.addLayout(tab_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(stack)
        body_layout.addWidget(scroll, stretch=1)

        outer.addWidget(body, stretch=1)
        _select_tab("Exercises")
        return page

    def _on_tab_changed(self, index: int) -> None:
        self._refresh_exercise_list()
        self._refresh_template_list()
        self._refresh_session_template_combo()
        self._refresh_session_exercise_combo()
        self._refresh_history_list()
        self._refresh_progress_exercise_combo()
        self._refresh_progress()

    # ------------------------------------------------------------------
    # Exercises tab
    # ------------------------------------------------------------------

    def _build_exercises_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._exercise_list = QListWidget()
        layout.addWidget(self._exercise_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Exercise")
        add_button.clicked.connect(self._on_add_exercise)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_exercise)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_exercise)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        self._refresh_exercise_list()
        return tab

    def _refresh_exercise_list(self) -> None:
        if self._exercise_list is None:
            return
        self._exercise_list.clear()
        for exercise in self.context.workout.all_exercises():
            item = QListWidgetItem(format_exercise_row(exercise))
            item.setData(Qt.ItemDataRole.UserRole, exercise.exercise_id)
            self._exercise_list.addItem(item)
        if self._exercise_list.count() == 0:
            add_empty_state_item(self._exercise_list, "No exercises yet — click Add Exercise to get started.")

    def _selected_exercise_id(self) -> Optional[str]:
        return selected_item_data(self._exercise_list)

    def _on_add_exercise(self) -> None:
        dialog = AddEditExerciseDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.workout.add_exercise(
            name=dialog.entered_name, category=dialog.entered_category,
            equipment=dialog.entered_equipment, notes=dialog.entered_notes,
        )
        self._refresh_exercise_list()

    def _on_edit_exercise(self) -> None:
        exercise_id = self._selected_exercise_id()
        if exercise_id is None:
            QMessageBox.information(None, "No Exercise Selected", "Select an exercise to edit.")
            return
        exercise = self.context.workout.get_exercise(exercise_id)
        dialog = AddEditExerciseDialog(exercise=exercise)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.workout.update_exercise(
            exercise_id, name=dialog.entered_name, category=dialog.entered_category,
            equipment=dialog.entered_equipment, notes=dialog.entered_notes,
        )
        self._refresh_exercise_list()

    def _on_delete_exercise(self) -> None:
        exercise_id = self._selected_exercise_id()
        if exercise_id is None:
            QMessageBox.information(None, "No Exercise Selected", "Select an exercise to delete.")
            return
        self.context.workout.delete_exercise(exercise_id)
        self._refresh_exercise_list()

    # ------------------------------------------------------------------
    # Templates tab
    # ------------------------------------------------------------------

    def _build_templates_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)

        left = QVBoxLayout()
        self._template_list = QListWidget()
        self._template_list.currentItemChanged.connect(lambda *_: self._refresh_template_exercises_list())
        left.addWidget(self._template_list, stretch=1)

        left_button_row = QHBoxLayout()
        add_button = QPushButton("Add Template")
        add_button.clicked.connect(self._on_add_template)
        left_button_row.addWidget(add_button)
        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_template)
        left_button_row.addWidget(edit_button)
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_template)
        left_button_row.addWidget(delete_button)
        left.addLayout(left_button_row)
        layout.addLayout(left, stretch=1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Exercises in this template:"))
        self._template_exercises_list = QListWidget()
        right.addWidget(self._template_exercises_list, stretch=1)

        right_button_row = QHBoxLayout()
        add_exercise_button = QPushButton("Add Exercise…")
        add_exercise_button.clicked.connect(self._on_add_template_exercise)
        right_button_row.addWidget(add_exercise_button)
        remove_exercise_button = QPushButton("Remove Selected")
        remove_exercise_button.clicked.connect(self._on_remove_template_exercise)
        right_button_row.addWidget(remove_exercise_button)
        right.addLayout(right_button_row)
        layout.addLayout(right, stretch=1)

        self._refresh_template_list()
        return tab

    def _refresh_template_list(self) -> None:
        if self._template_list is None:
            return
        previously_selected_id = selected_item_data(self._template_list)
        self._template_list.blockSignals(True)
        self._template_list.clear()
        templates = self.context.workout.all_templates()
        for template in templates:
            item = QListWidgetItem(format_template_row(template))
            item.setData(Qt.ItemDataRole.UserRole, template.template_id)
            self._template_list.addItem(item)
            if template.template_id == previously_selected_id:
                self._template_list.setCurrentItem(item)
        if not templates:
            add_empty_state_item(self._template_list, "No templates yet — click Add Template to get started.")
        self._template_list.blockSignals(False)
        self._refresh_template_exercises_list()

    def _selected_template_id(self) -> Optional[str]:
        return selected_item_data(self._template_list)

    def _refresh_template_exercises_list(self) -> None:
        if self._template_exercises_list is None:
            return
        self._template_exercises_list.clear()
        template_id = self._selected_template_id()
        if template_id is None:
            add_empty_state_item(self._template_exercises_list, "Select a template to see its exercises.")
            return
        template = self.context.workout.get_template(template_id)
        for entry in template.exercises:
            exercise = self.context.workout.get_exercise(entry.get("exercise_id", ""))
            name = exercise.name if exercise is not None else "(deleted exercise)"
            self._template_exercises_list.addItem(
                f"{name}   {entry.get('target_sets')}x{entry.get('target_reps')} @ {entry.get('target_weight'):g}"
            )
        if self._template_exercises_list.count() == 0:
            add_empty_state_item(self._template_exercises_list, "No exercises added to this template yet.")

    def _on_add_template(self) -> None:
        dialog = AddEditWorkoutTemplateDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.workout.add_template(name=dialog.entered_name, notes=dialog.entered_notes)
        self._refresh_template_list()

    def _on_edit_template(self) -> None:
        template_id = self._selected_template_id()
        if template_id is None:
            QMessageBox.information(None, "No Template Selected", "Select a template to edit.")
            return
        template = self.context.workout.get_template(template_id)
        dialog = AddEditWorkoutTemplateDialog(template=template)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.workout.update_template(template_id, name=dialog.entered_name, notes=dialog.entered_notes)
        self._refresh_template_list()

    def _on_delete_template(self) -> None:
        template_id = self._selected_template_id()
        if template_id is None:
            QMessageBox.information(None, "No Template Selected", "Select a template to delete.")
            return
        self.context.workout.delete_template(template_id)
        self._refresh_template_list()

    def _on_add_template_exercise(self) -> None:
        template_id = self._selected_template_id()
        if template_id is None:
            QMessageBox.information(None, "No Template Selected", "Select a template first.")
            return
        exercises = self.context.workout.all_exercises()
        if not exercises:
            QMessageBox.information(None, "No Exercises Yet", "Add an exercise in the Exercises tab first.")
            return
        dialog = AddTemplateExerciseDialog(exercises=exercises)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.workout.add_exercise_to_template(
            template_id, exercise_id=dialog.entered_exercise_id, target_sets=dialog.entered_target_sets,
            target_reps=dialog.entered_target_reps, target_weight=dialog.entered_target_weight,
        )
        self._refresh_template_list()

    def _on_remove_template_exercise(self) -> None:
        template_id = self._selected_template_id()
        if template_id is None:
            return
        item = self._template_exercises_list.currentItem()
        if item is None or not item.isSelected():
            QMessageBox.information(None, "No Exercise Selected", "Select an exercise to remove from this template.")
            return
        index = self._template_exercises_list.row(item)
        self.context.workout.remove_exercise_from_template(template_id, index)
        self._refresh_template_list()

    # ------------------------------------------------------------------
    # Log Session tab — a live, in-memory state machine
    # ------------------------------------------------------------------

    def _build_log_session_tab(self) -> QWidget:
        """Nature re-skin (2026-09-14) — a session card (the existing
        form/state machine, unchanged internally, just now contained in
        a rounded card) alongside a real "Daily Mission" card, matching
        the reference mockup's own two-panel Log Session layout."""
        tab = QWidget()
        outer = QHBoxLayout(tab)
        outer.setSpacing(16)

        session_card = QFrame()
        session_card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(session_card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        session_title = QLabel("Log Session")
        session_title.setObjectName("NatureSectionTitle")
        layout.addWidget(session_title)

        start_row = QHBoxLayout()
        start_row.addWidget(QLabel("Template:"))
        self._session_template_combo = QComboBox()
        start_row.addWidget(self._session_template_combo, stretch=1)
        self._start_session_button = QPushButton("Start Session")
        self._start_session_button.clicked.connect(self._on_start_session)
        start_row.addWidget(self._start_session_button)
        layout.addLayout(start_row)

        self._session_elapsed_label = QLabel("Session: 00:00")
        self._session_elapsed_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(self._session_elapsed_label)

        exercise_row = QHBoxLayout()
        exercise_row.addWidget(QLabel("Current Exercise:"))
        self._session_exercise_combo = QComboBox()
        exercise_row.addWidget(self._session_exercise_combo, stretch=1)
        self._log_set_button = QPushButton("Log Set")
        self._log_set_button.setEnabled(False)
        self._log_set_button.clicked.connect(self._on_log_set)
        exercise_row.addWidget(self._log_set_button)
        layout.addLayout(exercise_row)

        rest_row = QHBoxLayout()
        self._rest_elapsed_label = QLabel("Rest: 00:00")
        rest_row.addWidget(self._rest_elapsed_label)
        self._rest_button = QPushButton("Start Resting")
        self._rest_button.setEnabled(False)
        self._rest_button.clicked.connect(self._on_toggle_rest)
        rest_row.addWidget(self._rest_button)
        layout.addLayout(rest_row)

        self._session_sets_list = QListWidget()
        layout.addWidget(self._session_sets_list, stretch=1)

        finish_row = QHBoxLayout()
        finish_row.addWidget(QLabel("Calories (optional):"))
        self._session_calories_spin = QDoubleSpinBox()
        self._session_calories_spin.setRange(0.0, 5000.0)
        self._session_calories_spin.setDecimals(0)
        finish_row.addWidget(self._session_calories_spin)
        self._finish_session_button = QPushButton("Finish Session")
        self._finish_session_button.setEnabled(False)
        self._finish_session_button.clicked.connect(self._on_finish_session)
        finish_row.addWidget(self._finish_session_button)
        layout.addLayout(finish_row)

        outer.addWidget(session_card, stretch=2)

        side_column = QVBoxLayout()
        side_column.setSpacing(16)
        latest_entry_card = self._build_latest_entry_card()
        if latest_entry_card is not None:
            side_column.addWidget(latest_entry_card)
        daily_mission_card = self._build_daily_mission_card()
        if daily_mission_card is not None:
            side_column.addWidget(daily_mission_card)
        side_column.addStretch(1)
        outer.addLayout(side_column, stretch=1)

        self._refresh_session_template_combo()
        self._refresh_session_exercise_combo()
        return tab

    def _build_latest_entry_card(self) -> Optional[QFrame]:
        """"Latest Entry" card (Nature re-skin, 2026-09-14) — the most
        recently logged set: live from the in-progress session if one
        is active, else the last set from workout history, matching
        the reference mockup's own Log Session layout (a "Latest
        Entry" card above "Daily Mission" — the first pass only built
        the second one). Real data only — no fabricated clock time;
        WorkoutSession only stores a session-level date, not a per-set
        timestamp like the mockup's own "5:42 PM"."""
        if self._session_active and self._session_sets_logged:
            latest = self._session_sets_logged[-1]
            when = "Today"
        else:
            sessions = self.context.workout.all_sessions()
            if not sessions or not sessions[0].sets_logged:
                return None
            latest = sessions[0].sets_logged[-1]
            when = sessions[0].date

        exercise = self.context.workout.get_exercise(latest["exercise_id"])
        exercise_name = exercise.name if exercise is not None else "(deleted exercise)"

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title = QLabel("Latest Entry")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

        line = QLabel(f"{exercise_name} — Set {latest['set_number']}: {latest['reps']:g} reps @ {latest['weight']:g}")
        line.setObjectName("NatureAssetLine")
        line.setWordWrap(True)
        layout.addWidget(line)

        when_label = QLabel(when)
        when_label.setObjectName("NatureTileCaption")
        layout.addWidget(when_label)

        return card

    def _build_daily_mission_card(self) -> Optional[QFrame]:
        """"Daily Mission" card (Nature re-skin, 2026-09-14) — surfaces
        whatever active Fitness-category core.recurring_mission_manager
        template exists (e.g. the real Push-ups goal), matching the
        reference mockup's own Log Session "Daily Mission" card. No
        cross-module import (modules never import each other, CLAUDE.md's
        layering rule) — reads core.recurring_mission_manager directly,
        same as every other module that surfaces a recurring Mission's
        status. None if there's no active Fitness template yet."""
        if self.context.recurring_missions is None:
            return None
        templates = [
            t for t in self.context.recurring_missions.all_templates() if t.active and t.category == "Fitness"
        ]
        if not templates:
            return None
        template = templates[0]
        today = date.today()
        mission, _ = self.context.recurring_missions.ensure_current_missions(template, today)
        streak = self.context.recurring_missions.current_streak_for_template(template.template_id, today)

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title = QLabel("Daily Mission")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

        name_label = QLabel(template.name)
        name_label.setObjectName("NatureAssetLine")
        layout.addWidget(name_label)

        if mission is not None and mission.objectives:
            objective = mission.objectives[0]
            progress_label = QLabel(f"{objective.progress:g}/{objective.target:g}")
            progress_label.setObjectName("NatureTileValue")
            layout.addWidget(progress_label)

        streak_unit = "week" if template.recurrence == "weekly" else "day"
        streak_text = f"\U0001F525 {streak}-{streak_unit} streak" if streak > 0 else "New streak starting today"
        streak_label = QLabel(streak_text)
        streak_label.setObjectName("NatureTileCaption")
        layout.addWidget(streak_label)

        layout.addStretch(1)
        return card

    def _refresh_session_template_combo(self) -> None:
        if self._session_template_combo is None or self._session_active:
            return
        current = self._session_template_combo.currentData() if self._session_template_combo.count() else None
        self._session_template_combo.blockSignals(True)
        self._session_template_combo.clear()
        self._session_template_combo.addItem("Freeform (no template)", "")
        for template in self.context.workout.all_templates():
            self._session_template_combo.addItem(template.name, template.template_id)
        idx = self._session_template_combo.findData(current)
        self._session_template_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._session_template_combo.blockSignals(False)

    def _refresh_session_exercise_combo(self) -> None:
        if self._session_exercise_combo is None:
            return
        current = self._session_exercise_combo.currentData() if self._session_exercise_combo.count() else None
        self._session_exercise_combo.blockSignals(True)
        self._session_exercise_combo.clear()
        if self._session_active and self._session_template_id:
            template = self.context.workout.get_template(self._session_template_id)
            exercise_ids = [e.get("exercise_id") for e in (template.exercises if template else [])]
            exercises = [self.context.workout.get_exercise(eid) for eid in exercise_ids]
            exercises = [e for e in exercises if e is not None]
        else:
            exercises = self.context.workout.all_exercises()
        for exercise in exercises:
            self._session_exercise_combo.addItem(exercise.name, exercise.exercise_id)
        idx = self._session_exercise_combo.findData(current)
        self._session_exercise_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._session_exercise_combo.blockSignals(False)

    def _current_session_elapsed_ms(self) -> int:
        if not self._session_active or self._session_start_monotonic is None:
            return 0
        return int((time.monotonic() - self._session_start_monotonic) * 1000)

    def _current_rest_elapsed_ms(self) -> int:
        if not self._resting or self._rest_start_monotonic is None:
            return 0
        return int((time.monotonic() - self._rest_start_monotonic) * 1000)

    def _update_session_display(self) -> None:
        self._session_elapsed_label.setText(f"Session: {format_elapsed(self._current_session_elapsed_ms())}")
        self._rest_elapsed_label.setText(f"Rest: {format_elapsed(self._current_rest_elapsed_ms())}")

    def _on_start_session(self) -> None:
        if not self.context.workout.all_exercises():
            QMessageBox.information(None, "No Exercises Yet", "Add an exercise in the Exercises tab first.")
            return
        self._session_active = True
        self._session_template_id = self._session_template_combo.currentData() or ""
        self._session_start_monotonic = time.monotonic()
        self._session_sets_logged = []
        self._session_timer.start()

        self._start_session_button.setEnabled(False)
        self._session_template_combo.setEnabled(False)
        self._log_set_button.setEnabled(True)
        self._rest_button.setEnabled(True)
        self._finish_session_button.setEnabled(True)
        self._refresh_session_exercise_combo()
        self._refresh_session_sets_list()

    def _on_log_set(self) -> None:
        exercise_id = self._session_exercise_combo.currentData()
        if not exercise_id:
            QMessageBox.information(None, "No Exercise Selected", "Pick an exercise first.")
            return
        exercise = self.context.workout.get_exercise(exercise_id)
        dialog = LogSetDialog(exercise_name=exercise.name if exercise is not None else "")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        set_number = sum(1 for s in self._session_sets_logged if s["exercise_id"] == exercise_id) + 1
        self._session_sets_logged.append({
            "exercise_id": exercise_id, "set_number": set_number,
            "reps": dialog.entered_reps, "weight": dialog.entered_weight,
        })
        self._refresh_session_sets_list()

    def _refresh_session_sets_list(self) -> None:
        self._session_sets_list.clear()
        for entry in reversed(self._session_sets_logged):
            exercise = self.context.workout.get_exercise(entry["exercise_id"])
            name = exercise.name if exercise is not None else "(deleted exercise)"
            self._session_sets_list.addItem(f"{name}   Set {entry['set_number']}: {entry['reps']} reps @ {entry['weight']:g}")
        if not self._session_sets_logged:
            add_empty_state_item(self._session_sets_list, "No sets logged yet this session.")

    def _on_toggle_rest(self) -> None:
        if self._resting:
            self._resting = False
            self._rest_start_monotonic = None
            self._rest_button.setText("Start Resting")
            self._rest_elapsed_label.setText("Rest: 00:00")
        else:
            self._resting = True
            self._rest_start_monotonic = time.monotonic()
            self._rest_button.setText("Done Resting")

    def _on_finish_session(self) -> None:
        duration_minutes = self._current_session_elapsed_ms() / 1000 / 60
        calories = self._session_calories_spin.value() or None

        self._session_timer.stop()
        self.context.workout.add_session(
            template_id=self._session_template_id, date_str=date.today().isoformat(),
            duration_minutes=duration_minutes, calories_estimate=calories,
            sets_logged=self._session_sets_logged,
        )

        self._session_active = False
        self._session_start_monotonic = None
        self._session_sets_logged = []
        self._session_template_id = ""
        self._resting = False
        self._rest_start_monotonic = None
        self._session_calories_spin.setValue(0.0)

        self._start_session_button.setEnabled(True)
        self._session_template_combo.setEnabled(True)
        self._log_set_button.setEnabled(False)
        self._rest_button.setEnabled(False)
        self._rest_button.setText("Start Resting")
        self._finish_session_button.setEnabled(False)
        self._session_elapsed_label.setText("Session: 00:00")
        self._rest_elapsed_label.setText("Rest: 00:00")
        self._refresh_session_template_combo()
        self._refresh_session_exercise_combo()
        self._refresh_session_sets_list()
        QMessageBox.information(None, "Session Saved", "Workout session saved.")

    # ------------------------------------------------------------------
    # History tab
    # ------------------------------------------------------------------

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._history_list = QListWidget()
        self._history_list.currentItemChanged.connect(lambda *_: self._refresh_history_detail())
        layout.addWidget(self._history_list, stretch=1)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_session)
        layout.addWidget(delete_button, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(QLabel("Sets logged:"))
        self._history_detail_list = QListWidget()
        self._history_detail_list.setMaximumHeight(160)
        layout.addWidget(self._history_detail_list)

        self._refresh_history_list()
        return tab

    def _refresh_history_list(self) -> None:
        if self._history_list is None:
            return
        self._history_list.clear()
        sessions = self.context.workout.all_sessions()
        for session in sessions:
            template = self.context.workout.get_template(session.template_id) if session.template_id else None
            template_name = template.name if template is not None else "Freeform"
            item = QListWidgetItem(format_session_row(session, template_name))
            item.setData(Qt.ItemDataRole.UserRole, session.session_id)
            self._history_list.addItem(item)
        if self._history_list.count() == 0:
            add_empty_state_item(self._history_list, "No sessions logged yet — use the Log Session tab to get started.")
        self._refresh_history_detail()

    def _selected_session_id(self) -> Optional[str]:
        return selected_item_data(self._history_list)

    def _refresh_history_detail(self) -> None:
        if self._history_detail_list is None:
            return
        self._history_detail_list.clear()
        session_id = self._selected_session_id()
        if session_id is None:
            return
        session = self.context.workout.get_session(session_id)
        if session is None:
            return
        for entry in session.sets_logged:
            exercise = self.context.workout.get_exercise(entry.get("exercise_id", ""))
            name = exercise.name if exercise is not None else "(deleted exercise)"
            self._history_detail_list.addItem(f"{name}   Set {entry.get('set_number')}: {entry.get('reps')} reps @ {entry.get('weight'):g}")
        if self._history_detail_list.count() == 0:
            add_empty_state_item(self._history_detail_list, "No sets logged in this session.")

    def _on_delete_session(self) -> None:
        session_id = self._selected_session_id()
        if session_id is None:
            QMessageBox.information(None, "No Session Selected", "Select a session to delete.")
            return
        self.context.workout.delete_session(session_id)
        self._refresh_history_list()

    # ------------------------------------------------------------------
    # Progress tab
    # ------------------------------------------------------------------

    def _build_progress_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        exercise_row = QHBoxLayout()
        exercise_row.addWidget(QLabel("Exercise:"))
        self._progress_exercise_combo = QComboBox()
        self._progress_exercise_combo.currentIndexChanged.connect(lambda _idx: self._refresh_progress())
        exercise_row.addWidget(self._progress_exercise_combo, stretch=1)
        layout.addLayout(exercise_row)

        self._progress_pr_label = QLabel("")
        layout.addWidget(self._progress_pr_label)

        self._progress_chart_view = QChartView()
        self._progress_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._progress_chart_view.setMinimumHeight(280)
        layout.addWidget(self._progress_chart_view, stretch=1)

        self._refresh_progress_exercise_combo()
        self._refresh_progress()
        return tab

    def _refresh_progress_exercise_combo(self) -> None:
        if self._progress_exercise_combo is None:
            return
        current = self._progress_exercise_combo.currentData() if self._progress_exercise_combo.count() else None
        self._progress_exercise_combo.blockSignals(True)
        self._progress_exercise_combo.clear()
        for exercise in self.context.workout.all_exercises():
            self._progress_exercise_combo.addItem(exercise.name, exercise.exercise_id)
        idx = self._progress_exercise_combo.findData(current)
        self._progress_exercise_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._progress_exercise_combo.blockSignals(False)

    def _refresh_progress(self) -> None:
        if self._progress_pr_label is None:
            return
        exercise_id = self._progress_exercise_combo.currentData()
        if not exercise_id:
            self._progress_pr_label.setText("Add an exercise to see progress.")
            self._progress_chart_view.setChart(QChart())
            return

        pr = self.context.workout.personal_record_for(exercise_id)
        if pr is None:
            self._progress_pr_label.setText("No sets logged yet for this exercise.")
        else:
            self._progress_pr_label.setText(f"Personal Record: {pr['weight']:g} x {pr['reps']} reps ({pr['date']})")

        progression = self.context.workout.weight_progression_for(exercise_id)
        chart = QChart()
        chart.setTitle("Weight Over Time")
        chart.legend().hide()

        series = QLineSeries()
        # Visible point markers — a single logged session (a real, very
        # common early-usage case) is just one data point, and a bare
        # QLineSeries draws nothing at all for one point (a line needs
        # two to connect). Markers make that point visible on its own.
        series.setPointsVisible(True)
        categories = []
        max_weight = 0.0
        for i, (day, weight) in enumerate(progression):
            series.append(i, weight)
            categories.append(day)
            max_weight = max(max_weight, weight)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Weight")
        # Real, confirmed Qt Charts behavior (checked directly, not
        # assumed): auto-ranging a QValueAxis attached via addAxis()/
        # attachAxis() (not createDefaultAxes()) collapses to a
        # zero-height [weight, weight] range whenever every logged
        # weight is identical — including the single-point case every
        # new user hits first — which renders as a completely blank
        # chart with no visible axis scale at all. Setting an explicit
        # range with real headroom avoids that regardless of how many
        # points exist or whether they're all equal.
        axis_y.setRange(0.0, max(max_weight * 1.2, 10.0))
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self._progress_chart_view.setChart(chart)
