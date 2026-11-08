"""
tests.test_voice_more_twins
=============================

More voice twins (DEC-0125, core/assistant_more_twins_actions.py): remember
that, an order paid (the rest owed when no amount is said), the last weigh-in
deleted, a mission renamed, an operating journal line removed, each through
its screen's own action.
"""

from types import SimpleNamespace

from core import assistant_more_twins_actions as more


class _Actions:
    """Keeps each proposal and runs it."""

    def __init__(self):
        """Nothing yet."""
        self.proposed = []

    def propose(self, context, kind, params, proposed_by):
        """Keeps it."""
        self.proposed.append((kind, params))
        return SimpleNamespace(proposal_id="p")

    def approve(self, context, proposal_id):
        """Done."""
        return SimpleNamespace(status="executed", result="Done.")


def _context():
    """A business with one open order, weigh-ins, missions and journal lines."""
    order = SimpleNamespace(order_id="o1", title="Custom PCB, 10 boards", customer_id="c1", price=180.0,
                            status="Building", payment_ids=["r1"])
    business = SimpleNamespace(orders=[order], customers=[SimpleNamespace(customer_id="c1", name="Customer A")])
    ledger = SimpleNamespace(all_revenue=lambda: [SimpleNamespace(entry_id="r1", amount=90.0)])
    return SimpleNamespace(
        actions=_Actions(), business=business, ledger=ledger,
        fitness=SimpleNamespace(weigh_ins=lambda: [{"id": "w1"}, {"id": "w2"}]),
        missions=SimpleNamespace(all_missions=lambda: [SimpleNamespace(mission_id="m1", name="Read the Tractor Manual")]),
        operating_journal=SimpleNamespace(lines=[{"id": "l1", "text": "Early mornings, three days a week"}]))


def test_each_twin_runs_its_screen_s_own_action():
    """The kinds and params each tool proposes; an order with no amount said is paid what's still owed."""
    cases = [
        (more._action_remember_this, {"fact": "My truck takes 5W-30 oil."}, ("memory.add", {"text": "My truck takes 5W-30 oil."})),
        (more._action_order_paid, {"order": "customer a"}, ("order.pay", {"order_id": "o1", "amount": 90.0})),
        (more._action_order_paid, {"order": "pcb", "amount": "50"}, ("order.pay", {"order_id": "o1", "amount": "50"})),
        (more._action_delete_last_weigh_in, {}, ("fitness.weigh_in_delete", {"entry_id": "w2"})),
        (more._action_rename_mission, {"mission": "tractor manual", "name": "Learn Hydraulics"},
         ("mission.edit", {"mission_id": "m1", "name": "Learn Hydraulics"})),
        (more._action_remove_operating_line, {"line": "early mornings"}, ("operating.remove", {"line_id": "l1"})),
    ]
    for handler, args, expected in cases:
        c = _context()
        handler(c, args)
        assert c.actions.proposed == [expected], handler.__name__


def test_nothing_to_remember_or_rename_is_asked_about():
    """No fact, no new name: a question and no change."""
    c = _context()
    assert more._action_remember_this(c, {"fact": ""}) == "What should I remember?"
    assert more._action_rename_mission(c, {"mission": "tractor"}) == "What should Read the Tractor Manual be called?"
    assert not c.actions.proposed


def test_a_secret_is_never_remembered_by_voice():
    """Passwords, PINs, codes and card numbers stay screen-only (Zac, 2026-11-07): refused, nothing kept."""
    c = _context()
    for said in ("My gate code is 4421", "Remember my bank password is hunter2", "my PIN is 1234",
                 "the card number ends 4421 and the CVV is 123"):
        assert more._action_remember_this(c, {"fact": said}) == more.SECRET_REPLY
    assert not c.actions.proposed
