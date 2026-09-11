"""
tests.test_insight_manager
=============================

Unit tests for core.insight_manager. Isolates _DATA_DIR/_INSIGHTS_FILE/
_RECOMMENDATIONS_FILE into a tmp_path scratch area, same monkeypatch
pattern as every other manager test file.
"""

from __future__ import annotations

import pytest

import core.insight_manager as insight_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.insight_manager import InsightManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(insight_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(insight_manager_module, "_INSIGHTS_FILE", data_dir / "insights.json")
    monkeypatch.setattr(insight_manager_module, "_RECOMMENDATIONS_FILE", data_dir / "recommendations.json")
    return data_dir


def _make_manager() -> InsightManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return InsightManager(context)


# ------------------------------------------------------------------
# create_insight_if_new / idempotency
# ------------------------------------------------------------------

def test_starts_empty_when_no_files_exist(isolated_paths):
    manager = _make_manager()
    assert manager.all_insights() == []
    assert manager.all_recommendations() == []


def test_create_insight_if_new_creates_a_real_insight(isolated_paths):
    manager = _make_manager()
    insight = manager.create_insight_if_new("maintenance", "task1", "overdue", "Title", "Message")
    assert insight is not None
    assert insight.source_type == "maintenance"
    assert insight.source_id == "task1"
    assert insight.kind == "overdue"
    assert insight.status == "open"
    assert insight.created_at


def test_create_insight_if_new_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.create_insight_if_new("maintenance", "task1", "overdue", "Title", "Message")

    reloaded = InsightManager(manager.context)
    assert len(reloaded.all_insights()) == 1
    assert reloaded.all_insights()[0].source_id == "task1"


def test_create_insight_if_new_returns_none_when_an_open_one_already_exists(isolated_paths):
    manager = _make_manager()
    first = manager.create_insight_if_new("maintenance", "task1", "overdue", "Title", "Message")
    second = manager.create_insight_if_new("maintenance", "task1", "overdue", "Title 2", "Message 2")

    assert first is not None
    assert second is None
    assert len(manager.all_insights()) == 1


def test_create_insight_if_new_allows_a_different_kind_for_the_same_source(isolated_paths):
    manager = _make_manager()
    manager.create_insight_if_new("maintenance", "task1", "due_soon", "Title", "Message")
    second = manager.create_insight_if_new("maintenance", "task1", "overdue", "Title 2", "Message 2")

    assert second is not None
    assert len(manager.all_insights()) == 2


def test_create_insight_if_new_allows_recreating_after_resolution(isolated_paths):
    manager = _make_manager()
    first = manager.create_insight_if_new("maintenance", "task1", "overdue", "Title", "Message")
    manager.resolve_insight(first.insight_id)

    second = manager.create_insight_if_new("maintenance", "task1", "overdue", "Title 2", "Message 2")

    assert second is not None
    assert second.insight_id != first.insight_id


# ------------------------------------------------------------------
# open_insight_for / open_insights_for_source / open_insights
# ------------------------------------------------------------------

def test_open_insight_for_returns_none_when_nothing_matches(isolated_paths):
    manager = _make_manager()
    assert manager.open_insight_for("maintenance", "task1", "overdue") is None


def test_open_insights_for_source_only_includes_open_ones(isolated_paths):
    manager = _make_manager()
    a = manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")
    manager.create_insight_if_new("maintenance", "task1", "due_soon", "T", "M")
    manager.resolve_insight(a.insight_id)

    open_ones = manager.open_insights_for_source("maintenance", "task1")
    assert len(open_ones) == 1
    assert open_ones[0].kind == "due_soon"


def test_open_insights_for_source_ignores_other_sources(isolated_paths):
    manager = _make_manager()
    manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")
    manager.create_insight_if_new("maintenance", "task2", "overdue", "T", "M")

    assert len(manager.open_insights_for_source("maintenance", "task1")) == 1


def test_open_insights_returns_all_open_across_sources(isolated_paths):
    manager = _make_manager()
    manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")
    b = manager.create_insight_if_new("maintenance", "task2", "overdue", "T", "M")
    manager.resolve_insight(b.insight_id)

    assert len(manager.open_insights()) == 1


# ------------------------------------------------------------------
# resolve_insight — also resolves linked pending Recommendations
# ------------------------------------------------------------------

def test_resolve_insight_marks_it_resolved(isolated_paths):
    manager = _make_manager()
    insight = manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")

    resolved = manager.resolve_insight(insight.insight_id)

    assert resolved.status == "resolved"
    assert resolved.resolved_at
    assert manager.get_insight(insight.insight_id).status == "resolved"


def test_resolve_insight_also_resolves_a_pending_recommendation(isolated_paths):
    manager = _make_manager()
    insight = manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")
    recommendation = manager.add_recommendation(insight.insight_id, "Do the thing.")

    manager.resolve_insight(insight.insight_id)

    reloaded = manager.recommendations_for_insight(insight.insight_id)
    assert reloaded[0].status == "resolved"
    assert reloaded[0].resolved_at
    assert recommendation.recommendation_id == reloaded[0].recommendation_id


def test_resolve_insight_unknown_id_returns_none(isolated_paths):
    manager = _make_manager()
    assert manager.resolve_insight("does-not-exist") is None


def test_resolve_insight_twice_is_safe(isolated_paths):
    manager = _make_manager()
    insight = manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")
    manager.resolve_insight(insight.insight_id)
    resolved_again = manager.resolve_insight(insight.insight_id)
    assert resolved_again.status == "resolved"


def test_get_insight_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_insight("does-not-exist") is None


# ------------------------------------------------------------------
# Recommendations
# ------------------------------------------------------------------

def test_add_recommendation_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    insight = manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")
    manager.add_recommendation(insight.insight_id, "Do the thing.")

    reloaded = InsightManager(manager.context)
    recs = reloaded.all_recommendations()
    assert len(recs) == 1
    assert recs[0].insight_id == insight.insight_id
    assert recs[0].message == "Do the thing."
    assert recs[0].status == "pending"


def test_recommendations_for_insight_filters_correctly(isolated_paths):
    manager = _make_manager()
    a = manager.create_insight_if_new("maintenance", "task1", "overdue", "T", "M")
    b = manager.create_insight_if_new("maintenance", "task2", "overdue", "T", "M")
    manager.add_recommendation(a.insight_id, "For A")
    manager.add_recommendation(b.insight_id, "For B")

    recs_for_a = manager.recommendations_for_insight(a.insight_id)
    assert len(recs_for_a) == 1
    assert recs_for_a[0].message == "For A"


def test_load_handles_corrupt_insights_json_gracefully(isolated_paths):
    data_dir = isolated_paths
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "insights.json").write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_insights() == []
