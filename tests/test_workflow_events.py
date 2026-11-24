"""
tests.test_workflow_events
============================

Workflows started by events in his history (core/workflows.py, DEC-0293; Zac, 2026-11-23: "Records and email, with
approval"): the trigger {"on": an event type} is checked, never runs on the calendar, runs once for each new event of
its type, and an event from something MIA read (an email, a page) runs with every change waiting for his yes.
"""

from datetime import datetime
from types import SimpleNamespace

from core import workflows as wf


def test_an_event_trigger_is_checked_and_never_runs_on_the_calendar():
    spec = {"trigger": {"on": "bill_paid"}}
    assert wf.due(spec, "", datetime(2026, 11, 23, 9)) is False
    problems = wf.check({"kind": "workflow", "title": "x", "owner": "personal", "trigger": {"on": "no_such_event"},
                         "steps": [{"step": "tell", "text": "hi"}]})
    assert any("event trigger" in p for p in problems)
    assert "Whenever there are new bills paid" in wf.describe({"trigger": {"on": "bill_paid"}, "steps": []})[0]


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
    settings = {wf.SEEN_KEY: seen} if seen else {}
    config = SimpleNamespace(get=lambda k, d=None: settings.get(k, d), set=lambda k, v: settings.__setitem__(k, v))
    return SimpleNamespace(creations=_Store(trigger), config=config), settings


def test_each_new_event_runs_once_and_an_emails_waits_for_his_yes(monkeypatch):
    import core.life_events as life_events

    events = [SimpleNamespace(type="bill_paid", at="2026-11-23T10:00:00", source="manual"),
              SimpleNamespace(type="bill_paid", at="2026-11-23T11:00:00", source="inbox"),
              SimpleNamespace(type="bill_paid", at="2026-11-22T08:00:00", source="manual")]  # before the last look
    monkeypatch.setattr(life_events, "events_for", lambda context, since=None, types=None: events)
    runs = []
    monkeypatch.setattr(wf, "run", lambda context, cid, now=None, held=False: runs.append(held) or {"offers": []})
    ctx, settings = _ctx({"on": "bill_paid"}, seen="2026-11-23T09:00:00")
    wf.run_on_events(ctx, datetime(2026, 11, 23, 12))
    assert runs == [False, True] and settings[wf.SEEN_KEY] == "2026-11-23T11:00:00"
    wf.run_on_events(ctx, datetime(2026, 11, 23, 12, 5))
    assert runs == [False, True]  # nothing new: nothing runs again


def test_the_first_look_only_marks_where_it_starts(monkeypatch):
    runs = []
    monkeypatch.setattr(wf, "run", lambda *a, **k: runs.append(1) or {"offers": []})
    ctx, settings = _ctx({"on": "bill_paid"})
    assert wf.run_on_events(ctx, datetime(2026, 11, 23, 12)) == [] and not runs
    assert settings[wf.SEEN_KEY] == "2026-11-23T12:00:00"
