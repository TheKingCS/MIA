"""
tests.test_event_cancel
=========================

"Cancel the dentist appointment" is that calendar event of his, cancelled through the action contract
(core/reminders_view.cancel_event, the calendar conversation check 2026-11-26: the model had said "That isn't
available on this MIA"); careful because it deletes: a word shared with another kind of event, a repeating series or
the wrong day is asked about first, never deleted.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, reminders_view

TODAY = date(2026, 11, 26)  # a Thursday


def _event(title, day="2026-11-27", recurrence=None, time="14:00"):
    """A calendar event."""
    return SimpleNamespace(event_id=title, title=title, date=day, recurrence=recurrence, time=time)


def test_only_a_clear_one_is_cancelled(monkeypatch):
    events = [_event("Dentist appointment"), _event("Oil change"), _event("Gym", recurrence="weekly"),
              _event("Dinner"), _event("Dinner with Sarah")]
    context = SimpleNamespace(calendar=SimpleNamespace(all_events=lambda: events))
    cancelled = []
    monkeypatch.setattr(reminders_view, "_delete", lambda c, k, p, n, w: cancelled.append(n) or f"Cancelled {n}.")
    assert reminders_view.cancel_event(context, "dentist", True, "", TODAY, kind="appointment") == \
        "Cancelled Dentist appointment."
    assert reminders_view.cancel_event(context, "oil change", False, "", TODAY) == "Cancelled Oil change."
    assert reminders_view.cancel_event(context, "oil", False, "", TODAY).startswith("Cancel Oil change")
    assert "whole series" in reminders_view.cancel_event(context, "gym", False, "friday", TODAY)
    assert reminders_view.cancel_event(context, "dentist", True, "monday", TODAY, kind="appointment").startswith(
        "I don't have")
    assert reminders_view.cancel_event(context, "dinner", False, "", TODAY) == "Cancelled Dinner."
    assert reminders_view.cancel_event(context, "all my notes", False, "", TODAY) is None
    assert cancelled == ["Dentist appointment", "Oil change", "Dinner"]
    events.append(_event("Team lunch"))
    assert reminders_view.cancel_event(context, "team", True, "", TODAY, kind="meeting").startswith("Cancel Team lunch")
    assert cancelled == ["Dentist appointment", "Oil change", "Dinner"]


def test_the_words_reach_it(monkeypatch):
    seen = []
    monkeypatch.setattr(reminders_view, "cancel_event", lambda c, w, k, d="", t=None, kind="": seen.append((w, k, d)) or "ok")
    for words in ("cancel the dentist", "cancel my dentist appointment", "delete the vet visit on Friday"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "ok", words
    assert seen == [("dentist", False, ""), ("dentist", True, ""), ("vet", True, "Friday")]
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "cancel my netflix subscription") != "ok"
