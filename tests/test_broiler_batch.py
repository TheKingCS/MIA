"""
tests.test_broiler_batch
==========================

A batch of meat birds as a mission (core/broiler_batch.py): each breed's steps dated from the day they came (Cornish
cross: off the heat week 3, a feeding schedule from week 2, pasture week 4, processing week 8), the feed the batch
eats, the batch saved inside the change, and a breed it doesn't know, no birds, a future day or a long-done batch
refused.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from core import broiler_batch as bb
from core.actions import ActionError

CAME = date(2026, 11, 24)


def test_a_cornish_cross_batch_is_dated_to_processing_day():
    found = bb.plan("cornish cross", 25, CAME)
    assert [s["week"] for s in found["steps"]] == [0, 2, 3, 4, 8]
    assert found["processing"] == date(2027, 1, 19) and found["feed_lb"] == 375
    assert bb.plan("freedom ranger", 10, CAME)["processing"] == date(2027, 2, 9)


def test_breeds_are_read_from_how_he_says_them():
    assert bb.breed_of("cornish rocks") == "cornish cross" and bb.breed_of("freedom rangers") == "freedom ranger"
    assert bb.breed_of("emus") == ""


class _Missions:
    """The missions store, as much as the batch uses of it."""

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


def test_the_mission_is_made_and_saved_inside_the_change(monkeypatch):
    import core.person_settings as ps

    monkeypatch.setattr(ps, "person_id", lambda context: None)
    kept = {}
    config = SimpleNamespace(get=lambda k, d=None: kept.get(k, d), set=lambda k, v: kept.__setitem__(k, v),
                             save=lambda: kept.__setitem__("_saved", 1))
    ctx = SimpleNamespace(missions=_Missions(), config=config)
    said = bb._make(ctx, {"breed": "cornish cross", "birds": 25, "started": CAME.isoformat()})
    assert "25 cornish cross, processing about Jan 19" in said and "375 lb of feed" in said
    assert len(ctx.missions.steps) == 5 and kept["_saved"] == 1
    assert "week 0" in bb.say(ctx, CAME)


def test_whats_wrong_is_refused():
    for params in ({"breed": "emu", "birds": 4}, {"birds": 0}, {"birds": 5, "started": "2999-01-01"},
                   {"birds": 5, "started": "2020-01-01"}):
        with pytest.raises(ActionError):
            bb._params(params)
