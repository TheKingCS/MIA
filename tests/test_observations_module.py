"""
tests.test_observations_module
=================================

Unit tests for modules.observations.module's pure functions, same
style as tests/test_memories_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.insight_manager import Insight
from modules.observations.module import (
    format_insight_recommendation_line,
    format_source_section_label,
    group_open_insights_by_source,
)


def _insight(insight_id, source_type, created_at, status="open") -> Insight:
    return Insight(
        insight_id=insight_id, source_type=source_type, source_id="s1", kind="overdue",
        title="Title", message="Message", status=status, created_at=created_at,
    )


def test_format_source_section_label_maintenance():
    assert format_source_section_label("maintenance") == "MAINTENANCE"


def test_format_source_section_label_missions():
    assert format_source_section_label("missions") == "MISSIONS"


def test_format_source_section_label_unknown_falls_back_to_uppercased():
    assert format_source_section_label("garden") == "GARDEN"


def test_format_insight_recommendation_line_with_message():
    assert format_insight_recommendation_line("Mark it complete.") == "→ Mark it complete."


def test_format_insight_recommendation_line_none():
    assert format_insight_recommendation_line(None) == ""


def test_format_insight_recommendation_line_empty_string():
    assert format_insight_recommendation_line("") == ""


def test_group_open_insights_by_source_excludes_resolved():
    open_one = _insight("i1", "maintenance", "2026-09-01T10:00:00")
    resolved_one = _insight("i2", "maintenance", "2026-09-02T10:00:00", status="resolved")

    groups = group_open_insights_by_source([open_one, resolved_one])
    assert groups == [("maintenance", [open_one])]


def test_group_open_insights_by_source_groups_by_source_type():
    maint = _insight("i1", "maintenance", "2026-09-01T10:00:00")
    mission = _insight("i2", "missions", "2026-09-01T10:00:00")

    groups = group_open_insights_by_source([maint, mission])
    assert [source for source, _ in groups] == ["maintenance", "missions"]


def test_group_open_insights_by_source_sorts_oldest_first_within_a_group():
    newer = _insight("i1", "maintenance", "2026-09-10T10:00:00")
    older = _insight("i2", "maintenance", "2026-09-01T10:00:00")

    groups = group_open_insights_by_source([newer, older])
    assert groups[0][1] == [older, newer]


def test_group_open_insights_by_source_empty_when_nothing_open():
    assert group_open_insights_by_source([]) == []
