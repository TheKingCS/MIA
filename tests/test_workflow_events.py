"""
tests.test_workflow_events
============================

Workflows started by events in his history (core/workflows.py, DEC-0293; Zac, 2026-11-23: "Records and email, with
approval"): the trigger {"on": an event type} is checked, never runs on the calendar, runs once for each new event of
its type (each workflow from its own first look, none lost or run twice when events share a second), and an event
from something MIA read (an email, a page) runs with every change waiting for his yes.
"""

from datetime import datetime
from types import SimpleNamespace

from core import workflows as wf


def test_an_event_trigger_is_checked_and_never_runs_on_the_calendar():
    """An unknown type or a list is a problem, never a crash; it never runs on a date; its sentence says when it waits."""
    spec = {"trigger": {"on": "bill_paid"}}
    assert wf.due(spec, "", datetime(2026, 11, 23, 9)) is False
    problems = wf.check({"kind": "workflow", "title": "x", "owner": "personal", "trigger": {"on": "no_such_event"},
                         "steps": [{"step": "tell", "text": "hi"}]})
    assert any("event trigger" in p for p in problems)
    assert wf.check({"kind": "workflow", "title": "x", "owner": "personal", "trigger": {"on": ["bill_paid"]},
                     "steps": [{"step": "tell", "text": "hi"}]})  # a list is a problem, not a crash
    said = wf.describe({"trigger": {"on": "bill_paid"}, "steps": []})[0]
    assert "Whenever there are new bills paid" in said and "when one comes from something MIA read" in said


def test_what_she_read_is_told_apart_from_what_he_recorded():
    assert wf.from_reading(SimpleNamespace(source="inbox")) and wf.from_reading(SimpleNamespace(source="email:gmail"))
    assert not wf.from_reading(SimpleNamespace(source="manual")) and not wf.from_reading(SimpleNamespace(source="mia"))


class _Store:
    def __init__(self, trigger):
        self.spec = {"kind": "workflow", "trigger": trigger}

    def published(self):
        return [{"id": "C-1"}]

    def shown(self, cid):
        return {"spec": self.spec}

    def log_run(self, cid, entry):
        pass


def _ctx(trigger, seen=""):
    """A context with one published workflow and settings in a dict; `seen` is its mark from an earlier look."""
    settings = {wf.SEEN_KEY: {"C-1": {"at": seen, "ids": []}}} if seen else {}
    config = SimpleNamespace(get=lambda k, d=None: settings.get(k, d), set=lambda k, v: settings.__setitem__(k, v))
    return SimpleNamespace(creations=_Store(trigger), config=config), settings


def test_each_new_event_runs_once_and_an_emails_waits_for_his_yes(monkeypatch):
    """Two new events run it twice, the emailed one held; its mark moves to the newest; nothing new runs nothing."""
    import core.life_events as life_events

    events = [SimpleNamespace(type="bill_paid", at="2026-11-23T10:00:00", source="manual", event_id="a"),
              SimpleNamespace(type="bill_paid", at="2026-11-23T11:00:00", source="inbox", event_id="b"),
              SimpleNamespace(type="bill_paid", at="2026-11-22T08:00:00", source="manual", event_id="c")]  # before
    monkeypatch.setattr(life_events, "events_for", lambda context, since=None, types=None: events)
    runs = []
    monkeypatch.setattr(wf, "run", lambda context, cid, now=None, held=False: runs.append(held) or {"offers": []})
    ctx, settings = _ctx({"on": "bill_paid"}, seen="2026-11-23T09:00:00")
    wf.run_on_events(ctx, datetime(2026, 11, 23, 12))
    assert runs == [False, True] and settings[wf.SEEN_KEY]["C-1"] == {"at": "2026-11-23T11:00:00", "ids": ["b"]}
    wf.run_on_events(ctx, datetime(2026, 11, 23, 12, 5))
    assert runs == [False, True]  # nothing new: nothing runs again


def test_the_first_look_only_marks_where_it_starts(monkeypatch):
    """A workflow seen for the first time runs nothing from before; it only gets its own mark."""
    runs = []
    monkeypatch.setattr(wf, "run", lambda *a, **k: runs.append(1) or {"offers": []})
    ctx, settings = _ctx({"on": "bill_paid"})
    assert wf.run_on_events(ctx, datetime(2026, 11, 23, 12)) == [] and not runs
    assert settings[wf.SEEN_KEY]["C-1"]["at"]  # its mark, on the events' own clock


def test_events_in_the_same_second_are_none_lost_at_a_bursts_cut(monkeypatch):
    import core.life_events as life_events

    events = [SimpleNamespace(type="bill_paid", at="2026-11-23T10:00:00", source="import", event_id=f"e{i:02}")
              for i in range(12)]
    monkeypatch.setattr(life_events, "events_for", lambda context, since=None, types=None: events)
    runs = []
    monkeypatch.setattr(wf, "run", lambda context, cid, now=None, held=False: runs.append(1) or {"offers": []})
    ctx, settings = _ctx({"on": "bill_paid"}, seen="2026-11-23T09:00:00")
    wf.run_on_events(ctx, datetime(2026, 11, 23, 12))
    assert len(runs) == wf.MAX_EVENT_RUNS
    wf.run_on_events(ctx, datetime(2026, 11, 23, 12, 5))
    assert len(runs) == 12  # the two left over run next time, once each
    wf.run_on_events(ctx, datetime(2026, 11, 23, 12, 10))
    assert len(runs) == 12
