"""Starter sets from the web's Settings (core/starter_actions.py, DEC-0125): each set with its parts on the page, and
starter.add adding a set, or the parts ticked, as one action whose Undo takes it all back."""

from __future__ import annotations

import pytest

from core.actions import ActionCenter, ActionError
from core.starter_actions import starters
from core.web_account import settings_page
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The test household with an action center."""
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def test_a_starter_set_is_added_from_settings_part_by_part_and_undone(world):
    sets = {s["id"]: s for s in settings_page(world)["starters"]}
    assert "home_family" in sets and sets["home_family"]["parts"] and starters(None)
    part = sets["personal"]["parts"][0]["id"]
    proposal = world.actions.propose(world, "starter.add", {"starter_id": "personal", "parts": part})
    assert proposal.summary.startswith("Add the Personal starter set: ")
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed" and done.result.startswith("Personal: Added")
    before = len(world.recurring_missions.all_templates())
    assert before >= 1
    world.actions.undo(world, proposal.proposal_id)  # the action's own Undo takes the whole set back
    assert len(world.recurring_missions.all_templates()) < before
    with pytest.raises(ActionError, match="isn't in this set"):
        world.actions.propose(world, "starter.add", {"starter_id": "personal", "parts": "nope"})
    with pytest.raises(ActionError, match="Pick a starter set"):
        world.actions.propose(world, "starter.add", {"starter_id": "nope"})
