"""
modules.observations.module
==============================

"Observations" — the real UI core.insight_manager.py's own docstring
flagged as deferred: "Deliberately no dedicated browsing UI this
phase — Insights surface through the existing NotificationToast/
NotificationCenter... available for a later phase (a 'System
Observation' view...) to query." That later phase is now: three real
scan domains (core.maintenance_insights, core.mission_insights,
core.mission_patterns) all feed the same Insight/Recommendation store,
so there's real content to browse instead of an empty shell.

Read-only, same stance as modules/memories/module.py (Expedition
recaps) — an Insight is discovered automatically by a domain scan,
never hand-authored, and resolving one happens through the existing
domain UI (marking a Maintenance task complete, touching a stale or
repeatedly-abandoned Mission) exactly as it already does for the
Notification toast this adds a persistent view alongside. No new "mark
resolved" interaction here, matching all three scan modules' own
docstrings.

format_source_section_label()/group_open_insights_by_source() are free
functions (not methods) — testable without Qt, see
tests/test_observations_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.insight_manager import Insight
from modules.module_base import ModuleBase

_SOURCE_LABELS = {
    "maintenance": "MAINTENANCE",
    "missions": "MISSIONS",
    "patterns": "PATTERNS",
}


def format_source_section_label(source_type: str) -> str:
    """Pure formatting logic — testable without Qt."""
    return _SOURCE_LABELS.get(source_type, source_type.upper())


def format_insight_recommendation_line(recommendation_message: Optional[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    if not recommendation_message:
        return ""
    return f"→ {recommendation_message}"


def group_open_insights_by_source(insights: list[Insight]) -> list[tuple[str, list[Insight]]]:
    """Pure logic — testable without Qt. Groups OPEN insights by
    source_type, oldest-first within each group (the longest-
    outstanding observation surfaces first) — groups themselves keep
    first-appearance order from `insights`, not alphabetical, since
    callers already pass all_insights() in a sensible order."""
    groups: dict[str, list[Insight]] = {}
    for insight in insights:
        if insight.status != "open":
            continue
        groups.setdefault(insight.source_type, []).append(insight)
    for group in groups.values():
        group.sort(key=lambda i: i.created_at)
    return list(groups.items())


class ObservationsModule(ModuleBase):
    module_id = "observations"
    display_name = "Observations"
    description = "What MIA has noticed across your maintenance and missions."
    icon = "\U0001F50D"  # magnifying glass

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
        self._list_layout.setSpacing(12)
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

        all_insights = self.context.insights.all_insights() if self.context.insights is not None else []
        groups = group_open_insights_by_source(all_insights)

        if not groups:
            message = (
                "Nothing open right now — MIA will flag things here as it notices them."
                if self.context.insights is not None else
                "Observations aren't available."
            )
            empty_label = QLabel(message)
            empty_label.setObjectName("SubtitleLabel")
            empty_label.setWordWrap(True)
            self._list_layout.addWidget(empty_label)
            return

        for source_type, insights in groups:
            section_label = QLabel(format_source_section_label(source_type))
            section_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
            self._list_layout.addWidget(section_label)
            for insight in insights:
                self._list_layout.addWidget(self._build_insight_card(insight))

    def _build_insight_card(self, insight: Insight) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        title_label = QLabel(insight.title)
        title_label.setStyleSheet("font-weight: 600;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        message_label = QLabel(insight.message)
        message_label.setObjectName("DashboardSectionBody")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        recommendations = (
            self.context.insights.recommendations_for_insight(insight.insight_id)
            if self.context.insights is not None else []
        )
        pending = next((r for r in recommendations if r.status == "pending"), None)
        recommendation_line = format_insight_recommendation_line(pending.message if pending else None)
        if recommendation_line:
            recommendation_label = QLabel(recommendation_line)
            recommendation_label.setObjectName("SubtitleLabel")
            recommendation_label.setWordWrap(True)
            layout.addWidget(recommendation_label)

        return card
