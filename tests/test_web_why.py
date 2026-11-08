"""My Why on the web (core/web_why.py): the chains of reasons with their facts, and linking, unlinking and achieving
goals as why.* actions, the same goals the voice tools keep (DEC-0125)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core import actions
from core.actions import ActionCenter, ActionError
from core.intent_manager import IntentManager
from core.web_why import why_page


@pytest.fixture
def me(tmp_path, monkeypatch):
    """A stand-in person with intents in a temporary folder and an action center, and none of the other stores."""
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    ctx = SimpleNamespace(config=None, undo=None, events=None, actions=ActionCenter(), budget=None, real_estate=None,
                          projects=None, missions=None, user_memories=None, finance=None)
    ctx.intents = IntentManager(ctx, data_dir=tmp_path)
    return ctx


def act(ctx, kind, **params):
    """Proposes an action as the person and approves it; returns both."""
    proposal = ctx.actions.propose(ctx, kind, params, proposed_by="person")
    return proposal, ctx.actions.approve(ctx, proposal.proposal_id)


def test_goals_are_linked_into_a_chain_unlinked_and_achieved(me):
    assert why_page(SimpleNamespace(intents=None)) == {"available": False}
    assert why_page(me)["chains"] == []
    proposal, done = act(me, "why.link", goal="factory work", serves="Pay off debt", reason="It pays the most")
    assert proposal.summary == "Factory work → Pay off debt: It pays the most"
    assert done.result == "Linked: Factory work → Pay off debt."
    debt = next(g for g in why_page(me)["goals"] if g["name"] == "Pay off debt")
    act(me, "why.link", goal_id=debt["id"], serves="Control over my time")
    page = why_page(me)
    [chain] = page["chains"]
    assert [l["name"] for l in chain] == ["Factory work", "Pay off debt", "Control over my time"]
    assert chain[0]["reason"] == "It pays the most"
    with pytest.raises(ActionError, match="can't go the other way"):
        me.actions.propose(me, "why.link", {"goal": "Control over my time", "serves": "Factory work"})
    with pytest.raises(ActionError, match="same goal"):
        me.actions.propose(me, "why.link", {"goal": "Pay off debt", "serves": "pay off debt"})
    act(me, "why.achieve", goal_id=debt["id"])
    assert next(l for l in why_page(me)["chains"][0] if l["name"] == "Pay off debt")["done"]
    with pytest.raises(ActionError, match="already marked achieved"):
        me.actions.propose(me, "why.achieve", {"goal_id": debt["id"]})
    factory = next(g for g in why_page(me)["goals"] if g["name"] == "Factory work")
    act(me, "why.unlink", goal_id=factory["id"])
    assert len(why_page(me)["chains"]) == 2
    with pytest.raises(ActionError, match="isn't linked"):
        me.actions.propose(me, "why.unlink", {"goal_id": factory["id"]})
