"""
tests.test_hatch_tracker
==========================

Eggs in the incubator as a mission (core/hatch_tracker.py): each bird's milestones dated from the day set (chicken:
candle days 7 and 14, lockdown 18, hatch 21), the mission made with a step for each, "how's the hatch going?" saying
the day and what's next (saved inside the change), a day set read looking back, muscovy and bobwhite with their
own days, and a future day, a long-over hatch, no eggs or an unknown bird refused.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from core import hatch_tracker as ht
from core.actions import ActionError

SET = date(2026, 11, 24)


def test_a_chicken_hatch_is_dated_from_the_day_set():
    """Candle 7 and 14, lockdown 18, hatch 21, then the brooder; ducks' brooder starts cooler."""
    steps = ht.plan("chicken", 12, SET)
    assert [s["day"] for s in steps] == [7, 14, 18, 21, 22]
    assert steps[-2]["on"] == "2026-12-15" and steps[2]["step"].startswith("Lockdown on day 18")
    assert [s["day"] for s in ht.plan("duck", 6, SET)] == [7, 14, 25, 28, 29]
    assert "about 95 F (35 C)" in steps[-1]["step"] and "about 90 F" in ht.plan("duck", 6, SET)[-1]["step"]


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
    """A context with the missions store and settings in a dict, counting its saves."""
    kept = {}
    config = SimpleNamespace(get=lambda k, d=None: kept.get(k, d), set=lambda k, v: kept.__setitem__(k, v),
                             save=lambda: kept.__setitem__("_saved", kept.get("_saved", 0) + 1))
    return SimpleNamespace(missions=_Missions(), config=config)


def test_the_mission_has_a_step_a_milestone_and_the_hatch_is_followed(monkeypatch):
    """Five dated steps (the brooder last), the hatch saved inside the change, and the day and what's next said."""
    import core.person_settings as ps

    monkeypatch.setattr(ps, "person_id", lambda context: None)
    ctx = _ctx()
    said = ht._make(ctx, {"bird": "chicken", "eggs": 12, "set": SET.isoformat()})
    assert "Hatch: 12 chicken eggs, due Dec 15" in said and len(ctx.missions.steps) == 5
    assert ctx.config.get("_saved") == 1  # saved inside the change: a restart keeps it
    assert ht.say(ctx, date(2026, 12, 10)).startswith("The 12 chicken eggs are on day 16; next, lockdown on day 18 in 2")


def test_a_future_day_no_eggs_or_an_unknown_bird_is_refused():
    """And a hatch so long ago it would be over."""
    with pytest.raises(ActionError):
        ht._params({"eggs": 12, "set": "2020-01-01"})  # long over
    with pytest.raises(ActionError):
        ht._params({"eggs": 12, "set": "2999-01-01"})
    with pytest.raises(ActionError):
        ht._params({"eggs": 0})
    with pytest.raises(ActionError):
        ht._params({"bird": "emu", "eggs": 4})


def test_the_day_set_is_read_looking_back():
    today = date(2026, 11, 24)  # a Tuesday
    assert ht.set_day("yesterday", today) == "2026-11-23" and ht.set_day("Sunday", today) == "2026-11-22"
    assert ht.set_day("last tuesday", today) == "2026-11-24" and ht.set_day("3 days ago", today) == "2026-11-21"
    assert ht.set_day("Nov 20", today) == "2026-11-20" and ht.set_day("someday", today) is None


def test_muscovy_and_bobwhite_have_their_own_days():
    """Their hatch day (the step before the brooder) is their own: 35 and 23 days."""
    assert ht.bird_of("muscovy duck") == "muscovy duck" and ht.plan("muscovy duck", 6, SET)[-2]["day"] == 35
    assert ht.bird_of("bobwhite quail eggs") == "bobwhite quail" and ht.plan("bobwhite quail", 6, SET)[-2]["day"] == 23
