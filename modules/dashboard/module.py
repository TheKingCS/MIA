"""
modules.dashboard.module
===========================

Dashboard — docs/ROADMAP.md milestone v0.19, the last of the three new
subsystems from the 2026-07-14 wearable-companion vision update. A
read-only, at-a-glance summary: recent activity, active Missions and
their objective progress, recent Memories (Expedition recaps), upcoming
Calendar events, and active Projects/open Tasks. Purely an aggregation
view over data every other module already owns and manages — same
"no add/edit/delete of its own" stance as modules/memories/module.py.

Auto-navigated to when Field Kit detects a docked Core and auto-imports
its Expedition data (`modules/field_kit/module.py`'s
`_check_for_docked_core()`), via the existing `"assistant.open_module_requested"`
event — but this module is also a normal, always-accessible menu entry,
not something that only exists behind a dock event.

**"Recently played music" from the original vision is deliberately not
here** — Media/Music isn't a built module yet (confirmed blocked in
this dev sandbox on missing `libpulse`; see docs/ROADMAP.md's v1.0+
bucket notes), so there's no real data source for it. Add a section
once Media actually exists, not before.

format_activity_line()/format_mission_summary_line()/
format_recap_summary_line()/format_upcoming_event_line()/
format_project_line()/format_open_task_line() are free functions (not
methods) — testable without Qt, see tests/test_dashboard_module.py.
Dashboard writes its own small recap/objective summary lines rather
than importing modules.missions.module/modules.memories.module's
formatting helpers — modules never import another module directly
(CLAUDE.md's one-directional layering rule).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from core.activity_log_manager import ActivityLogEntry
from core.calendar_manager import CalendarEvent
from core.memory_manager import ExpeditionRecap
from core.mission_manager import Mission
from core.project_manager import Project
from core.task_manager import Task
from modules.module_base import ModuleBase

_SECTION_ITEM_LIMIT = 5


def format_activity_line(entry: ActivityLogEntry) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_dashboard_module.py)."""
    return f"{entry.timestamp}  —  {entry.summary}"


def format_mission_summary_line(mission: Mission, completed_objectives: int, total_objectives: int) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_dashboard_module.py)."""
    if total_objectives == 0:
        return f"{mission.name}  (no objectives yet)"
    return f"{mission.name}  ({completed_objectives} of {total_objectives} objectives complete)"


def format_recap_summary_line(recap: ExpeditionRecap) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_dashboard_module.py)."""
    parts = [recap.expedition.name]
    if recap.duration_days:
        parts.append(f"{recap.duration_days}d")
    if recap.total_distance_km:
        parts.append(f"{recap.total_distance_km:.1f} km")
    if recap.photo_count:
        parts.append(f"{recap.photo_count} photo{'s' if recap.photo_count != 1 else ''}")
    return "  —  ".join(parts)


def format_upcoming_event_line(event: CalendarEvent) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_dashboard_module.py)."""
    time_part = f" {event.time}" if event.time else ""
    return f"{event.date}{time_part}  —  {event.title}"


def format_project_line(project: Project) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_dashboard_module.py)."""
    due_part = f"  (due {project.due_date})" if project.due_date else ""
    return f"{project.name}  [{project.status}]{due_part}"


def format_open_task_line(task: Task) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_dashboard_module.py)."""
    due_part = f"  (due {task.due_date})" if task.due_date else ""
    return f"{task.title}{due_part}"


class DashboardModule(ModuleBase):
    module_id = "dashboard"
    display_name = "Dashboard"
    description = "Recent activity, active missions, memories, and upcoming items at a glance."
    icon = "\U0001F4CA"  # bar chart

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list_layout: Optional[QVBoxLayout] = None

    def get_widget(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._list_layout = QVBoxLayout(content)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        self._refresh()
        return page

    def _refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        recent_activity = self.context.activity_log.recent(limit=_SECTION_ITEM_LIMIT)
        self._add_section("Recent Activity", [format_activity_line(e) for e in recent_activity])

        active_missions = [m for m in self.context.missions.all_missions() if m.status == "active"]
        mission_lines = []
        for mission in active_missions[:_SECTION_ITEM_LIMIT]:
            total = len(mission.objectives)
            completed = sum(
                1 for index in range(total) if self.context.missions.is_objective_complete(mission.mission_id, index)
            )
            mission_lines.append(format_mission_summary_line(mission, completed, total))
        self._add_section("Active Missions", mission_lines)

        recaps = self.context.memories.all_recaps()[:_SECTION_ITEM_LIMIT]
        self._add_section("Recent Memories", [format_recap_summary_line(r) for r in recaps])

        today = date.today().isoformat()
        upcoming_events = sorted(
            (e for e in self.context.calendar.all_events() if e.date >= today),
            key=lambda e: (e.date, e.time or ""),
        )[:_SECTION_ITEM_LIMIT]
        self._add_section("Upcoming Events", [format_upcoming_event_line(e) for e in upcoming_events])

        active_projects = [p for p in self.context.projects.all_projects() if p.status != "Complete"]
        self._add_section("Active Projects", [format_project_line(p) for p in active_projects[:_SECTION_ITEM_LIMIT]])

        open_tasks = [t for t in self.context.tasks.all_tasks() if not t.done]
        self._add_section("Open Tasks", [format_open_task_line(t) for t in open_tasks[:_SECTION_ITEM_LIMIT]])

    def _add_section(self, title: str, lines: list[str]) -> None:
        section_label = QLabel(title)
        section_label.setStyleSheet("font-weight: 600;")
        self._list_layout.addWidget(section_label)

        if not lines:
            empty_label = QLabel("Nothing here yet.")
            empty_label.setObjectName("SubtitleLabel")
            self._list_layout.addWidget(empty_label)
            return

        for line in lines:
            item_label = QLabel(f"- {line}")
            item_label.setWordWrap(True)
            self._list_layout.addWidget(item_label)
