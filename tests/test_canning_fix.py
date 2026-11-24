"""
tests.test_canning_fix
========================

A batch put up with the wrong count, fixed (core/canning_fix.py): the history gains the difference, so the jars he
has ever canned are right again, and the jars on hand move by it; a bought can or a count that's already right is
refused.
"""

import pytest

from core import canning_shelf, life_milestones
from core.actions import ACTION_TYPES, ActionError
from core.canning_fix import _fix, recorded
from tests.engine_world import build_world


def test_seventy_said_for_seven_is_fixed_in_the_count_and_on_the_shelf(tmp_path, monkeypatch):
    """70 put up, 3 eaten (67 on hand), fixed to 7: canned counts 7, and 4 are on hand."""
    world = build_world(tmp_path, monkeypatch)
    item = canning_shelf.put_up(world.kitchen, "tomatoes", 70, "quarts")
    world.kitchen.update_pantry_item(item.item_id, quantity=67)
    params = {"item_id": item.item_id, "jars": 7}
    assert "recorded as 70" in ACTION_TYPES["jars.correct"].describe(world, params)
    ACTION_TYPES["jars.correct"].execute(world, params)
    assert life_milestones.jars_canned(world) == 7 and recorded(world, item.item_id) == 7
    assert world.kitchen.get_pantry_item(item.item_id).quantity == 4
    with pytest.raises(ActionError):
        ACTION_TYPES["jars.correct"].describe(world, params)


def test_a_bought_can_is_not_a_batch_and_a_count_is_needed(tmp_path, monkeypatch):
    """A pantry item without the canning shelf's mark is refused, as is no count."""
    world = build_world(tmp_path, monkeypatch)
    bought = world.kitchen.add_pantry_item("Canned beans", quantity=4, unit="cans")
    with pytest.raises(ActionError):
        ACTION_TYPES["jars.correct"].describe(world, {"item_id": bought.item_id, "jars": 2})
    item = canning_shelf.put_up(world.kitchen, "peaches", 6, "pints")
    with pytest.raises(ActionError):
        ACTION_TYPES["jars.correct"].describe(world, {"item_id": item.item_id, "jars": ""})


def test_by_voice_the_newest_batch_of_that_food_is_fixed(tmp_path, monkeypatch):
    """"I put up 12 jars of salsa, not 21": the salsa batch, not the tomatoes."""
    world = build_world(tmp_path, monkeypatch)
    canning_shelf.put_up(world.kitchen, "tomatoes", 7, "quarts")
    salsa = canning_shelf.put_up(world.kitchen, "salsa", 21, "pints")
    assert "now 12 jars" in _fix(world, {"food": "salsa", "jars": 12})
    assert recorded(world, salsa.item_id) == 12 and life_milestones.jars_canned(world) == 19
    assert "no batch of pickles" in _fix(world, {"food": "pickles", "jars": 3})
