"""
tests.test_event_cancel
=========================

"Cancel the dentist" is that calendar event of his, cancelled through the action contract (core/reminders_view.cancel,
the calendar conversation check 2026-11-26: the model had said "That isn't available on this MIA"); never a word that
names another kind of thing.
"""

from types import SimpleNamespace

from core import assistant_turn, reminders_view


def test_the_words_reach_the_cancel(monkeypatch):
    seen = []
    monkeypatch.setattr(reminders_view, "cancel", lambda c, w, t=None: seen.append(w) or f"Cancelled {w}.")
    for words in ("cancel the dentist", "cancel my dentist appointment", "delete the vet visit on Friday"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words).startswith("Cancelled"), words
    assert seen == ["dentist", "dentist", "vet"]
    assert not str(assistant_turn._own_tool_reply(SimpleNamespace(), "cancel my netflix subscription") or "").startswith(
        "Cancelled netflix")
