"""
tests.test_hatch_tracker
==========================

Eggs in the incubator as a mission (core/hatch_tracker.py): each bird's milestones dated from the day set (chicken:
candle days 7 and 14, lockdown 18, hatch 21), the mission made with a step for each, "how's the hatch going?" saying
the day and what's next, and a future day, no eggs or an unknown bird refused.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from core import hatch_tracker as ht
from core.actions import ActionError

SET = date(2026, 11, 24)


def test_a_chicken_hatch_is_dated_from_the_day_set():
    steps = ht.plan("chicken", 12, SET)
    assert [s["day"] for s in steps] == [7, 14, 18, 21]
    assert steps[-1]["on"] == "2026-12-15" and steps[2]["step"].startswith("Lockdown on day 18")
    assert [s["day"] for s in ht.plan("duck", 6, SET)] == [7, 14, 25, 28]


def test_birds_are_read_from_how_hes_say_them():
    assert ht.bird_of("geese") == "goose" and ht.bird_of("coturnix") == "quail" and ht.bird_of("emu") == ""


class _Missions:
    """The missions store, as much as the hatch tracker uses of it."""

    def __init__(self):
        """No missions yet."""
        self.made, self.steps = [], []

    def add_mission(self, name, **kw):
        """A new active mission."""
        self.made.append(SimpleNamespace(mission_id="M1", name=name, status="active"))
        return self.made[-1]

    def add_objective(self, mission_id, description, metric_type, target):
        """One step, kept in order."""
        self.steps.append(description)

    def get_mission(self, mission_id):
        """A mission by id, or None."""
        return next((m for m in self.made if m.mission_id == mission_id), None)


def _ctx():
    """A context with the missions store and settings in a dict."""
    kept = {}
    config = SimpleNamespace(get=lambda k, d=None: kept.get(k, d), set=lambda k, v: kept.__setitem__(k, v))
    return SimpleNamespace(missions=_Missions(), config=config)


def test_the_mission_has_a_step_a_milestone_and_the_hatch_is_followed(monkeypatch):
    import core.person_settings as ps

    monkeypatch.setattr(ps, "person_id", lambda context: None)
    ctx = _ctx()
    said = ht._make(ctx, {"bird": "chicken", "eggs": 12, "set": SET.isoformat()})
    assert "Hatch: 12 chicken eggs, due Dec 15" in said and len(ctx.missions.steps) == 4
    assert ht.say(ctx, date(2026, 12, 10)).startswith("The 12 chicken eggs are on day 16; next, lockdown on day 18 in 2")


def test_a_future_day_no_eggs_or_an_unknown_bird_is_refused():
    with pytest.raises(ActionError):
        ht._params({"eggs": 12, "set": "2999-01-01"})
    with pytest.raises(ActionError):
        ht._params({"eggs": 0})
    with pytest.raises(ActionError):
        ht._params({"bird": "emu", "eggs": 4})
