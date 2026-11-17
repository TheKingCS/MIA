"""
tests.test_kind_grants
========================

Approve Once or Approve From Now On (DEC-0215 as amended by Zac, 2026-11-17; core/kind_grants.py): only kinds that
stay in his records and can be undone may be approved from now on, never paying, sending, plans or grants; Approve
From Now On keeps a standing yes once the change ran; MIA's own later proposal of that kind runs at once with an Undo
and is marked `auto`, while his own presses are unchanged; the standing yes is listed with his grants, taken back
there, and lapses after 90 days unused; and the card says whether it may offer the second button.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core import grants, kind_grants
from core.actions import ACTION_TYPES, ActionError
from tests.test_crafting import shop  # noqa: F401  (the fixture)


@pytest.fixture
def world(shop, monkeypatch):  # noqa: F811
    """The crafting world, with person settings kept in a plain dict."""
    from core import person_settings

    kept = {}
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: kept.get(key, default))
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: kept.__setitem__(key, value))
    shop.kept = kept
    return shop


def test_only_undoable_changes_to_his_own_records_may_be_approved_from_now_on():
    assert kind_grants.grantable("mission.add") and kind_grants.grantable("shelf.keep")
    for kind in ("bill.pay", "browser.commit", "grant.take_back", "steps.do", "history.undo", "no.such.kind"):
        assert not kind_grants.grantable(kind), kind
    for kind in ACTION_TYPES:
        if kind_grants.grantable(kind):
            assert grants.tier_of(kind) == grants.WITHIN_GRANT, kind


def test_approve_from_now_on_makes_mias_next_proposal_of_that_kind_run_at_once(world):
    center = world.actions
    first = center.propose(world, "mission.add", {"name": "Stake the tomatoes"}, proposed_by="mia")
    assert first.status == "proposed" and first.as_dict()["grantable"] is True
    center.approve(world, first.proposal_id, from_now_on=True)
    assert kind_grants.has(world, "mission.add")
    missions = len(world.missions.all_missions())
    second = center.propose(world, "mission.add", {"name": "Order seed"}, proposed_by="mia")
    assert second.status == "executed" and second.auto and len(world.missions.all_missions()) == missions + 1
    assert center.approve(world, second.proposal_id) is second  # a caller that approves after proposing gets it back
    center.undo(world, second.proposal_id)
    mine = center.propose(world, "mission.add", {"name": "My own"})  # his own press still shows a card
    assert mine.status == "proposed" and not mine.auto


def test_approve_once_keeps_no_standing_yes_and_a_kind_that_always_asks_refuses_from_now_on(world):
    center = world.actions
    once = center.propose(world, "mission.add", {"name": "Once"}, proposed_by="mia")
    center.approve(world, once.proposal_id)
    assert not kind_grants.has(world, "mission.add")
    assert center.propose(world, "mission.add", {"name": "Again"}, proposed_by="mia").status == "proposed"
    with pytest.raises(ValueError, match="always asks"):
        kind_grants.give(world, "bill.pay")


def test_a_standing_yes_is_listed_with_his_grants_taken_back_there_and_lapses_unused(world):
    center = world.actions
    p = center.propose(world, "mission.add", {"name": "Stake"}, proposed_by="mia")
    center.approve(world, p.proposal_id, from_now_on=True)
    listed = [g for g in grants.standing(world) if g.kind == "kind"]
    assert [g.grant_id for g in listed] == ["kind:mission.add"] and "Approve From Now On" in listed[0].how
    assert "ask again" in grants.take_back(world, "kind:mission.add")
    assert not kind_grants.has(world, "mission.add")
    kind_grants.give(world, "mission.add", now=datetime(2026, 1, 1))
    assert kind_grants.has(world, "mission.add", now=datetime(2026, 3, 1))
    assert not kind_grants.has(world, "mission.add", now=datetime(2026, 1, 1) + timedelta(days=91))


def test_a_failed_change_keeps_no_standing_yes(world, monkeypatch):
    center = world.actions
    p = center.propose(world, "mission.add", {"name": "Will fail"}, proposed_by="mia")
    action = ACTION_TYPES["mission.add"]
    monkeypatch.setitem(ACTION_TYPES, "mission.add", type(action)(action.kind, action.label, action.params,
                                                                  action.describe, lambda c, params: 1 / 0))
    done = center.approve(world, p.proposal_id, from_now_on=True)
    assert done.status == "failed" and not kind_grants.has(world, "mission.add")


def test_the_card_offers_from_now_on_only_where_it_may():
    from core.actions import Proposal

    assert Proposal("p", "mission.add", {}, "s", None).as_dict()["grantable"] is True
    assert Proposal("p", "bill.pay", {}, "s", None).as_dict()["grantable"] is False


def test_from_now_on_on_a_kind_that_always_asks_is_refused_before_anything_runs(world):
    center = world.actions
    p = center.propose(world, "mission.add", {"name": "x"})
    p.kind = "bill.pay"  # as if the card were for a kind that always asks
    with pytest.raises(ActionError, match="always asks first"):
        center.approve(world, p.proposal_id, from_now_on=True)
    assert p.status == "proposed"
