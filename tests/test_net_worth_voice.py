"""
tests.test_net_worth_voice
============================

"What's my net worth?" by voice (get_net_worth): the Money page's figure (linked accounts and property equity), each
part named, his other debts taken off too since that figure leaves them out, and nothing to add up said plainly,
never a made-up zero.
"""

from types import SimpleNamespace

import core.finance_summary as fs
from core.assistant_domain_actions import _action_get_net_worth as worth


def _ctx(debts):
    """A context whose budget holds debts of these balances."""
    return SimpleNamespace(budget=SimpleNamespace(all_debts=lambda: [SimpleNamespace(balance=b) for b in debts]),
                           config=None)


def test_the_figure_names_its_parts_and_takes_off_his_other_debts(monkeypatch):
    monkeypatch.setattr(fs, "_net_worth", lambda context: {"total": 80000.0, "sources": [
        {"label": "Property equity", "value": 80000.0}]})
    said = worth(_ctx([5000, 2000, 0]), {})
    assert "net worth is $80,000.00 (Property equity $80,000.00)" in said
    assert "$7,000.00 across 2 (cards and loans); with them it's $73,000.00" in said


def test_nothing_to_add_up_is_said_plainly(monkeypatch):
    monkeypatch.setattr(fs, "_net_worth", lambda context: {"total": None, "sources": []})
    assert worth(_ctx([]), {}).startswith("I can't work out a net worth yet")
