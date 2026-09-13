"""
modules.household.module
===========================

Household — Garage/Property/Greenhouse's fourth sibling, but over
core.recurring_mission_manager.RecurringMissionTemplate (filtered to
category == "Household") instead of core.maintenance_manager.
MaintenanceAsset. Home for domestic routines that aren't asset
maintenance — laundry, dishes, hygiene — the same kind of thing
Workouts already gets its own module for.

Added 2026-09-14 at the user's own request, after asking where a
laundry mission would even live ("it wouldn't really have a page like
real estate or garage... how should I categorize and organize laundry
and hygiene and dishes"). They confirmed building this now rather than
folding it into an existing module.

Display shape (the user's own spec, 2026-09-14): a little daily
checklist plus one big total progress bar for completing the day's/
week's household templates — not a per-asset detail page like Garage's,
since a template's own past occurrences are already the Mission Log's
job, and there's no "asset" here to drill into, just the routine
itself. Each checklist row opens its current real occurrence Mission
directly in the Missions module (the same `assistant.open_module_
requested` + record_id mechanism every other area already uses).

is_household_template()/format_checklist_line()/household_progress are
free functions (not methods), independently owned rather than imported
from another module (CLAUDE.md's one-directional layering rule).

**"Nature" re-skin (2026-09-14, closing a real parity gap)**: ported
to the same photo-hero + `#NatureAssetCard` treatment every other
active module got — Household had been left behind on the old teal
system (it wasn't one of the 8 pictured reference pages, and Property
was the first parity gap closed; this is the second and last one).
The "Total Progress" card keeps its own prominence (a `#NatureAssetCard`
with the big `#NatureTileValue` count, not the coral attention-panel
styling — this is a celebratory highlight, not a warning).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.mission_manager import Mission
from core.recurring_mission_manager import RecurringMissionTemplate
from gui.widgets.photo_background_frame import PhotoBackgroundFrame
from modules.module_base import ModuleBase

HOUSEHOLD_CATEGORIES = ["Household"]


def is_household_template(template: RecurringMissionTemplate) -> bool:
    """Pure filter — testable without Qt (see tests/test_household_module.py)."""
    return template.category in HOUSEHOLD_CATEGORIES


def format_checklist_line(template: RecurringMissionTemplate, mission: Optional[Mission], streak: int) -> str:
    """Pure formatting logic — testable without Qt. `mission` is the
    template's current real occurrence (today's for "daily" recurrence,
    this week's for "weekly") — never None in practice since the module
    calls ensure_current_missions() before formatting, but handled
    plainly here anyway."""
    unit = "week" if template.recurrence == "weekly" else "day"
    streak_text = f"{streak}-{unit} streak" if streak > 0 else "new streak starting"

    if mission is None or not mission.objectives:
        return f"{template.name} — {streak_text}"

    objective = mission.objectives[0]
    check = "✓" if mission.status == "completed" else "•"
    return f"{check} {template.name} — {objective.progress:g}/{objective.target:g} — {streak_text}"


def household_progress(missions: list[Optional[Mission]]) -> tuple[int, int]:
    """Pure aggregation — (completed_count, total_count) across every
    household template's current occurrence Mission, for the one big
    "total progress" bar. A None (shouldn't happen once the module has
    called ensure_current_missions(), but handled anyway) just doesn't
    count as complete."""
    total = len(missions)
    completed = sum(1 for m in missions if m is not None and m.status == "completed")
    return completed, total


class HouseholdModule(ModuleBase):
    module_id = "household"
    display_name = "Household"
    description = "Daily and weekly household routines — laundry, dishes, chores."
    icon = "\U0001F9FA"  # basket

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list_layout: Optional[QVBoxLayout] = None
        self._progress_bar: Optional[QProgressBar] = None
        self._progress_label: Optional[QLabel] = None

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
        body_layout.setContentsMargins(24, 20, 24, 24)
        body_layout.setSpacing(16)

        progress_card = QFrame()
        progress_card.setObjectName("NatureAssetCard")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(18, 16, 18, 16)
        progress_layout.setSpacing(8)

        progress_eyebrow = QLabel("TOTAL PROGRESS")
        progress_eyebrow.setObjectName("NatureSectionTitle")
        progress_layout.addWidget(progress_eyebrow)

        self._progress_label = QLabel("—")
        self._progress_label.setObjectName("NatureTileValue")
        progress_layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        progress_layout.addWidget(self._progress_bar)

        body_layout.addWidget(progress_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._list_layout = QVBoxLayout(content)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(10)
        scroll.setWidget(content)
        body_layout.addWidget(scroll, stretch=1)

        outer.addWidget(body, stretch=1)

        self._refresh()
        return page

    def _refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        today = date.today()
        templates = [t for t in self.context.recurring_missions.all_templates() if is_household_template(t) and t.active]

        if not templates:
            empty = QLabel("Nothing tracked yet — add a Household recurring mission template.")
            empty.setObjectName("NatureTileCaption")
            self._list_layout.addWidget(empty)
            self._progress_label.setText("—")
            self._progress_bar.setRange(0, 1)
            self._progress_bar.setValue(0)
            return

        occurrence_missions: list[Optional[Mission]] = []
        for template in templates:
            mission, _ = self.context.recurring_missions.ensure_current_missions(template, today)
            occurrence_missions.append(mission)
            streak = self.context.recurring_missions.current_streak_for_template(template.template_id, today)

            row = QPushButton()
            row.setObjectName("NatureAssetCard")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.setToolTip(f"Open {template.name}")
            row.setMinimumHeight(64)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(18, 12, 18, 12)
            row_layout.setSpacing(2)
            line_label = QLabel(format_checklist_line(template, mission, streak))
            line_label.setObjectName("NatureAssetTitle")
            row_layout.addWidget(line_label)
            if mission is not None:
                row.clicked.connect(
                    lambda checked=False, mid=mission.mission_id: self.context.events.publish(
                        "assistant.open_module_requested", module_id="missions", record_id=mid,
                    )
                )
            self._list_layout.addWidget(row)

        completed, total = household_progress(occurrence_missions)
        self._progress_label.setText(f"{completed}/{total} complete")
        self._progress_bar.setRange(0, max(total, 1))
        self._progress_bar.setValue(completed)
