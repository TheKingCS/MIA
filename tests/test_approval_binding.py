"""Tests for approvals bound to the card (WP-02, REQ-SEC-016, core/actions.py): an approval holds only for the card
exactly as it was shown; a changed card, another card's binding, or a second approval does nothing."""
from types import SimpleNamespace

import pytest

from core import actions
from core.actions import ACTION_TYPES, ActionCenter, ActionError, ActionType, Refused, binding_of

RAN = []


@pytest.fixture
def center(monkeypatch):
    """An action center with one test kind whose execute records what it ran with (and changes its own copy)."""
    def execute(context, params):
        """Runs, records the params it got, and scribbles on them (its copy)."""
        RAN.append(dict(params))
        params["amount"] = 999
        return "done"

    RAN.clear()
    monkeypatch.setitem(ACTION_TYPES, "test.pay", ActionType("test.pay", "Pay", {"amount": "how much"},
                                                             lambda c, p: f"Pay {p['amount']}", execute))
    monkeypatch.setattr(actions, "_read_back", lambda context, proposal, change: None)
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    return ActionCenter()


CONTEXT = SimpleNamespace(config=None, undo=None)


def test_a_card_approved_as_shown_runs_once_with_what_was_shown(center):
    """The binding the screen saw approves it; execute gets a copy, so the card stays as approved; a second approval
    is refused."""
    card = center.propose(CONTEXT, "test.pay", {"amount": 5})
    assert card.binding == binding_of("test.pay", {"amount": 5}, "Pay 5")
    done = center.approve(CONTEXT, card.proposal_id, binding=card.binding)
    assert done.status == actions.EXECUTED and RAN == [{"amount": 5}] and done.params == {"amount": 5}
    with pytest.raises(ActionError):
        center.approve(CONTEXT, card.proposal_id, binding=card.binding)
    assert len(RAN) == 1


def test_a_card_changed_after_it_was_shown_is_refused(center):
    """Its parameters edited in place after it was made: nothing runs, and it's refused, not invalid."""
    card = center.propose(CONTEXT, "test.pay", {"amount": 5})
    card.params["amount"] = 500
    with pytest.raises(Refused):
        center.approve(CONTEXT, card.proposal_id)
    assert RAN == [] and card.status == actions.PROPOSED


def test_another_cards_binding_doesnt_approve_this_one(center):
    """The screen saw card A; an approval of B with A's binding is refused."""
    a = center.propose(CONTEXT, "test.pay", {"amount": 5})
    b = center.propose(CONTEXT, "test.pay", {"amount": 50})
    with pytest.raises(Refused):
        center.approve(CONTEXT, b.proposal_id, binding=a.binding)
    assert RAN == []
    assert center.approve(CONTEXT, b.proposal_id).status == actions.EXECUTED  # with no binding: as it was made
