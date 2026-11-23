"""
tests.test_needs_now
======================

The front of "catch me up" (core/needs_now.py, brainstorm 2.1): the greenhouse's open alerts, tonight's weather
against his plans and an update waiting; what the gate is holding; what she did on her own in the last day.
"""

from datetime import datetime
from types import SimpleNamespace

from core import needs_now


def _entry(at, by="mia", what="Added the electric bill to the budget"):
    from core.change_history import Entry

    return Entry(change_id=at, label="add_expense", summary=what, profile_id=None, at=at, by=by)


def test_a_quiet_day_says_nothing_so_the_report_starts_as_before():
    assert needs_now.describe({"now": [], "held": [], "own": []}) == ""


def test_each_part_is_said_in_order_with_how_to_undo():
    said = needs_now.describe({"now": ["Frost is possible tonight: cover the tomatoes."],
                               "held": ["Your budget this week", "A skill gone quiet"],
                               "own": [_entry("2026-11-23T07:02:00")]})
    assert said.index("Needs you now") < said.index("holding 2 messages") < said.index("On my own")
    assert "Added the electric bill" in said and "undo that" in said


def test_long_lists_are_cut_with_how_many_more():
    said = needs_now.describe({"now": [f"Thing {i}" for i in range(7)], "held": [], "own": []})
    assert "Thing 4." in said and "Thing 5" not in said and "And 2 more." in said


def test_greenhouse_alerts_count_only_once_she_has_taken_the_node_over():
    state = {"alerts": [{"severity": "warning", "message": "Water temperature high"},
                        {"severity": "critical", "message": "Pump stopped"},
                        {"severity": "info", "message": "ok"},
                        {"severity": "critical", "message": "old", "resolved": True}]}
    ctx = SimpleNamespace(greenhouse_link=SimpleNamespace(taken_over=True, state=state))
    assert needs_now._alerts(ctx) == ["Greenhouse (critical): Pump stopped",
                                      "Greenhouse (warning): Water temperature high"]
    ctx.greenhouse_link.taken_over = False
    assert needs_now._alerts(ctx) == []


def test_only_her_own_changes_not_undone_from_the_last_day(monkeypatch):
    from core import change_history

    def find(pid, start, end, about=""):
        assert (end - start).total_seconds() == 24 * 3600
        return [_entry("2026-11-23T07:00:00"), _entry("2026-11-23T06:00:00", by="person")]

    monkeypatch.setattr(change_history, "find", find)
    monkeypatch.setattr("core.person_settings.person_id", lambda context: None)
    own = needs_now._on_her_own(SimpleNamespace(), datetime(2026, 11, 23, 9))
    assert [e.by for e in own] == ["mia"]


def test_a_source_that_fails_never_stops_the_rest(monkeypatch):
    monkeypatch.setattr(needs_now, "_alerts", lambda context: 1 / 0)
    monkeypatch.setattr(needs_now, "_weather", lambda context, now: ["Frost tonight."])
    monkeypatch.setattr(needs_now, "_update", lambda: [])
    monkeypatch.setattr(needs_now, "_on_her_own", lambda context, now: [])
    gate = SimpleNamespace(pending=lambda: [{"title": "Your budget"}, {"topic": "checkin"}])
    found = needs_now.gather(SimpleNamespace(communication=gate), datetime(2026, 11, 23, 9))
    assert found == {"now": ["Frost tonight."], "held": ["Your budget", "checkin"], "own": []}


def test_catch_me_up_starts_with_what_needs_him(monkeypatch):
    """What needs him first, then where he left off (core/left_off.py), then the life state."""
    from core import assistant_tools

    monkeypatch.setattr(needs_now, "gather", lambda context, now=None: {"now": ["Pump stopped."], "held": [], "own": []})
    monkeypatch.setattr("core.left_off.gather", lambda context, now=None: {"missions": [], "drafts": ["Coop floor"],
                                                                          "promises": [], "decisions": []})
    monkeypatch.setattr("core.person_settings.person_id", lambda context: "p1")
    monkeypatch.setattr(assistant_tools, "assemble_life_state_v2", lambda context, today: {})
    monkeypatch.setattr(assistant_tools, "describe_life_state_v2", lambda state: "This week: 3 missions done.")
    monkeypatch.setattr(assistant_tools, "assemble_life_state", lambda context, pid, today: None)
    monkeypatch.setattr(assistant_tools, "format_life_state_summary", lambda snap: "2 active missions.")
    tools = getattr(assistant_tools, "AssistantTools", None) or next(
        v for v in vars(assistant_tools).values() if isinstance(v, type) and hasattr(v, "_action_get_life_state"))
    said = tools._action_get_life_state(SimpleNamespace(profiles=object()), {})
    assert said.startswith("Needs you now: Pump stopped. Still a draft in the Planner: Coop floor.")
    assert said.endswith("This week: 3 missions done. 2 active missions.")
