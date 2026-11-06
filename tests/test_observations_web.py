"""Observations' web screen (core/observations_web.py): findings across apps, and the open insights by source."""

from types import SimpleNamespace

import core.findings as findings_module
from core.findings import Finding
from core.observations_web import screen


def test_what_she_noticed(monkeypatch):
    monkeypatch.setattr(findings_module, "findings", lambda context, today=None: [
        Finding("k1", "A bill before payday", "Rent is due Friday; pay comes Monday.", "So it isn't late.",
                next_step="Move it to Monday.", app="money")])
    insights = [SimpleNamespace(insight_id="i1", source_type="maintenance", title="Oil change", message="Overdue.",
                                created_at="2026-11-01T09:00:00"),
                SimpleNamespace(insight_id="i2", source_type="patterns", title="Mondays", message="Workouts slip.",
                                created_at="")]
    recs = {"i1": [SimpleNamespace(message="Mark it done, or reschedule.", status="pending")], "i2": []}
    store = SimpleNamespace(open_insights=lambda: insights, recommendations_for_insight=lambda iid: recs[iid])
    data = screen(SimpleNamespace(insights=store))
    assert data["findings"][0]["next"] == "Move it to Monday."
    assert [g["source"] for g in data["insights"]] == ["Upkeep", "Patterns"]
    assert data["insights"][0]["items"][0] == {"title": "Oil change", "message": "Overdue.",
                                               "next": "Mark it done, or reschedule.", "since": "2026-11-01"}


def test_nothing_yet(monkeypatch):
    monkeypatch.setattr(findings_module, "findings", lambda context, today=None: [])
    assert screen(SimpleNamespace(insights=None)) == {"findings": [], "insights": []}
