"""Approving a waiting card by voice, "approve it from now on" included (core/spoken_approval.py, DEC-0215)."""

from types import SimpleNamespace

import pytest

from core import spoken_approval as sa
from core.actions import ActionError


@pytest.mark.parametrize("text,expected", [
    ("What's waiting for me?", ("list", None, False)),
    ("anything to approve", ("list", None, False)),
    ("Approve it", ("approve", None, False)),
    ("approve that.", ("approve", None, False)),
    ("approve 2", ("approve", 2, False)),
    ("Approve it from now on", ("approve", None, True)),
    ("yes, approve it, and from now on", ("approve", None, True)),
    ("approve that going forward", ("approve", None, True)),
    ("approve number 3 going forward", ("approve", 3, True)),
    ("reject it", ("reject", None, False)),
    ("no, decline 2", ("reject", 2, False)),
])
def test_his_words_for_a_waiting_card_are_understood(text, expected):
    assert sa.parse(text) == expected


@pytest.mark.parametrize("text", ["yes", "do it", "approve the budget plan for next year and email Sam",
                                  "from now on call me Z", "always", "I approve of that movie",
                                  # these name no card, and answer too many of her other questions (the review)
                                  "Yes, and from now on", "okay, going forward", "yes going forward",
                                  "Always do that"])
def test_words_that_answer_something_else_are_left_alone(text):
    assert sa.parse(text) is None


class _Actions:
    """A stand-in action manager with waiting cards; approve refuses from_now_on for a kind that always asks."""

    def __init__(self, cards):
        """The waiting cards."""
        self.cards, self.calls = cards, []

    def pending(self, _who):
        """The waiting cards."""
        return list(self.cards)

    def approve(self, _context, pid, from_now_on=False):
        """Records the approval; refuses from_now_on for the money kind."""
        card = next(c for c in self.cards if c.proposal_id == pid)
        if from_now_on and card.kind == "bill.pay":
            raise ActionError("That kind of change always asks first, so it can't be approved from now on.")
        self.calls.append(("approve", pid, from_now_on))
        return SimpleNamespace(result=f"Done: {card.summary}.")

    def reject(self, _context, pid):
        """Records the rejection."""
        self.calls.append(("reject", pid))


def _card(pid, summary, kind="task.add", at="2026-11-17T10:00"):
    """A stand-in waiting card."""
    return SimpleNamespace(proposal_id=pid, summary=summary, kind=kind, created_at=at)


def _context(monkeypatch, cards):
    """A context whose action manager holds these cards."""
    monkeypatch.setattr("core.actions._who", lambda _c: "me")
    return SimpleNamespace(actions=_Actions(cards))


def test_one_waiting_card_is_approved_from_now_on_and_he_is_told_how_to_take_it_back(monkeypatch):
    ctx = _context(monkeypatch, [_card("p1", "Add milk to the list")])
    said = sa.reply(ctx, "approve it from now on")
    assert ctx.actions.calls == [("approve", "p1", True)] and "take that back in your grants" in said


def test_a_kind_that_always_asks_is_not_approved_from_now_on(monkeypatch):
    ctx = _context(monkeypatch, [_card("p1", "Pay the power bill", kind="bill.pay")])
    said = sa.reply(ctx, "approve it from now on")
    assert ctx.actions.calls == [] and "always asks first" in said


def test_with_several_waiting_she_lists_them_instead_of_guessing(monkeypatch):
    ctx = _context(monkeypatch, [_card("p1", "A", at="1"), _card("p2", "B", at="2")])
    said = sa.reply(ctx, "approve it")
    assert ctx.actions.calls == [] and "1. A" in said and "2. B" in said


def test_a_number_picks_the_card_in_the_order_listed(monkeypatch):
    ctx = _context(monkeypatch, [_card("p2", "B", at="2"), _card("p1", "A", at="1")])
    sa.reply(ctx, "approve 2")
    assert ctx.actions.calls == [("approve", "p2", False)]


def test_a_number_past_the_list_approves_nothing(monkeypatch):
    ctx = _context(monkeypatch, [_card("p1", "A")])
    assert "only 1" in sa.reply(ctx, "approve 3") and ctx.actions.calls == []


def test_rejecting_runs_nothing(monkeypatch):
    ctx = _context(monkeypatch, [_card("p1", "A")])
    assert "Nothing was changed" in sa.reply(ctx, "reject it") and ctx.actions.calls == [("reject", "p1")]


def test_with_nothing_waiting_she_says_so(monkeypatch):
    ctx = _context(monkeypatch, [])
    assert "Nothing" in sa.reply(ctx, "approve it") and "Nothing" in sa.reply(ctx, "what's waiting for me?")


def test_the_quick_commands_hear_it_first(monkeypatch):
    from core import quick_commands

    ctx = _context(monkeypatch, [_card("p1", "Add milk")])
    assert "Done" in quick_commands.handle(ctx, "approve it")
