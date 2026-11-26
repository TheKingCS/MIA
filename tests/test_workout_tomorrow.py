"""
tests.test_workout_tomorrow
=============================

"What should I work out tomorrow?" from his own training (core/workout_today.say with tomorrow, the fitness
conversation check 2026-11-26: it had gone to the model), "last trained" still said from today.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, workout_today


def test_tomorrow_is_worked_out_for_tomorrow(monkeypatch):
    seen = []

    def suggest(c, day=None):
        """Legs trained today: rested 1 day by tomorrow."""
        seen.append(day)
        return {"group": "Push", "rested_days": 3, "exercises": [{"name": "Bench", "last": "3x8 at 135"}],
                "template": ""}
    monkeypatch.setattr(workout_today, "suggest", suggest)
    said = workout_today.say(SimpleNamespace(workout=object()), date(2026, 11, 26), tomorrow=True)
    assert seen == [date(2026, 11, 27)] and "last trained 2 days ago" in said
    monkeypatch.setattr(workout_today, "say", lambda c, t=None, tomorrow=False: f"tomorrow={tomorrow}")
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what should I work out tomorrow?") == "tomorrow=True"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what should I work out today?") == "tomorrow=False"
