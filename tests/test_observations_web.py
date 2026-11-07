"""Observations' web screen (core/observations_web.py): findings across apps, and the open insights by source, each
with its card (kind, the apps it used, where to settle it: DEC-0113)."""

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
                                               "next": "Mark it done, or reschedule.", "since": "2026-11-01",
                                               "kind": "Noticed", "tone": "accent", "used": "Maintenance",
                                               "open": {"label": "Open in Maintenance", "href": "maintenance.html"}}
    assert data["insights"][1]["items"][0]["kind"] == "Pattern"


def test_nothing_yet(monkeypatch):
    monkeypatch.setattr(findings_module, "findings", lambda context, today=None: [])
    assert screen(SimpleNamespace(insights=None)) == {"findings": [], "insights": []}


def test_each_observation_says_its_kind_the_apps_it_used_and_where_to_settle_it():
    from core.observations_web import card

    apps = {"budget": ("Money", "money.html"), "expeditions": ("Expeditions", "expeditions.html"),
            "maintenance": ("Maintenance", "maintenance.html"), "missions": ("Missions", None)}
    got = card("maintenance", ["asset:a1", "trip:t1", "asset:a2"], True, apps)
    assert got == {"kind": "Needs You", "tone": "attention", "used": "Maintenance · Expeditions",
                   "open": {"label": "Open in Maintenance", "href": "maintenance.html"}}
    calm = card("missions", ["mission:m1"], False, apps)
    assert (calm["kind"], calm["used"], calm["open"]) == ("Noticed", "Missions", None)  # no web page, no link
