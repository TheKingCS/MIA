"""The "still using it?" mark on subscriptions (core/subscriptions.py, DEC-0054): which bills are subscriptions, the
quiet finding for ones not checked in three months (never unprompted), Money's Still Using as bill.still_using, and the
same by voice."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from core.actions import ActionCenter
from core.findings import still_using_subscription
from core.subscriptions import CHECK_DAYS, is_subscription, unconfirmed
from core.web_money import money_page
from tests.engine_world import build_world


def bill(**kw):
    """A monthly utility bill, changed by any fields given."""
    base = dict(name="Electric", category="Utilities", recurrence="monthly", notes="", still_using_on="")
    return SimpleNamespace(**{**base, **kw})


def test_which_bills_are_subscriptions():
    assert not is_subscription(bill())
    assert is_subscription(bill(name="Streaming plus", category="Other"))
    assert is_subscription(bill(name="Gym", notes="membership"))
    assert is_subscription(bill(name="Netflix", category="Entertainment"))
    assert not is_subscription(bill(name="Netflix", category="Entertainment", recurrence=None))
    assert is_subscription(bill(name="Anything", still_using_on="2026-10-01"))


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The test household with an action center."""
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def test_an_unchecked_subscription_is_noticed_quietly_until_marked_in_use(world):
    from core.assistant_subscription_actions import _still, _unchecked

    old = (date.today() - timedelta(days=CHECK_DAYS + 5)).isoformat()
    tv = world.budget.add_bill("Netflix", 15.49, old, recurrence="monthly", category="Entertainment")
    world.budget.update_bill(tv.bill_id, created_at=old)
    world.budget.add_bill("Electric", 120.0, old, recurrence="monthly")
    [found] = still_using_subscription(world, date.today())
    assert "Netflix ($15.49)" in found.claim and not found.unprompted and found.app == "budget"
    assert _unchecked(world, {}).startswith("Not checked in 3 months: Netflix ($15.49)")
    row = next(b for b in money_page(world, date.today())["bills"] if b["name"] == "Netflix")
    assert row["subscription"] and row["still_using_on"] == ""
    proposal = world.actions.propose(world, "bill.still_using", {"bill_id": tv.bill_id})
    assert proposal.summary == "Mark Netflix as still in use"
    world.actions.approve(world, proposal.proposal_id)
    assert unconfirmed(world, date.today()) == [] and still_using_subscription(world, date.today()) == []
    world.actions.undo(world, proposal.proposal_id)
    assert _still(world, {"name": "netflix"}) == "Noted: you still use Netflix. I'll ask again in 3 months."
    assert _unchecked(world, {}) == "Every subscription has been checked in the last three months."
