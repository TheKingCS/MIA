"""
tests.test_next_cut
=====================

A plan's cut list read one cut at a time in the shop (next_cut): the plan he names, then "next cut" walking on from
where he is, the last one said, "start the cuts over", and a plan with no cuts or none named answered plainly.
"""

from types import SimpleNamespace

from core.assistant_plan_actions import _action_next_cut as next_cut

PLAN = {"id": "P1", "title": "Potting bench", "materials": {"cuts": [
    {"part": "legs", "qty": 4, "length_in": 34.0, "stock": "2x4"},
    {"part": "top slats", "qty": 6, "length_in": 48.0, "stock": "1x6"}]}}


class _Library:
    """The plans shelf, as much as next_cut uses of it."""

    def best(self, name):
        """The plan a name means."""
        return PLAN if "bench" in name.lower() else None

    def get(self, plan_id):
        """A plan by id."""
        return PLAN if plan_id == "P1" else None


def _ctx():
    """A context with the shelf and settings in a dict."""
    kept = {}
    return SimpleNamespace(plans=_Library(), config=SimpleNamespace(get=lambda k, d=None: kept.get(k, d),
                                                                    set=lambda k, v: kept.__setitem__(k, v)))


def test_the_cuts_are_read_one_at_a_time_and_start_over():
    ctx = _ctx()
    assert next_cut(ctx, {"plan": "the potting bench"}).startswith("Cut 1 of 2 for Potting bench: 4 x legs at")
    second = next_cut(ctx, {})
    assert "Cut 2 of 2" in second and "That's the last one." in second
    assert next_cut(ctx, {}).startswith("That's every cut for Potting bench")
    assert next_cut(ctx, {"start_over": "yes"}).startswith("Cut 1 of 2")


def test_no_plan_named_or_no_cuts_is_said_plainly():
    assert next_cut(_ctx(), {}).startswith("Which plan's cuts?")
