"""
tests.test_overdue_said
=========================

"What's overdue?" is his whole list's overdue (core/today.overdue_said, the live sweep 2026-11-26: it went to the
tax deadlines and said "That's for a grown-up." with no Compliance store), and a missing store is said as that;
and "what do I need from the hardware store?" is his projects' open needs, never a guess.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_goods_actions, assistant_turn, today


def test_the_overdue_things_or_that_nothing_is(monkeypatch):
    items = [today.TodayItem(when=today.OVERDUE, title="Pay Electric", detail="3 days late", module_id="budget",
                             record_id="b1"),
             today.TodayItem(when=today.TODAY, title="Water the beds", detail="", module_id="maintenance",
                             record_id="m1")]
    monkeypatch.setattr(today, "today_items", lambda c, t=None: items)
    assert today.overdue_said(SimpleNamespace(), date(2026, 11, 26)) == "Overdue (1): Pay Electric (3 days late)."
    monkeypatch.setattr(today, "today_items", lambda c, t=None: items[1:])
    assert today.overdue_said(SimpleNamespace(), date(2026, 11, 26)) == "Nothing's overdue. Due today: Water the beds."


def test_the_words_reach_it_and_a_missing_store_is_said(monkeypatch):
    monkeypatch.setattr(today, "overdue_said", lambda c, t=None: "late")
    for words in ("What's overdue?", "is anything overdue?", "what am I behind on?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "late", words
    from core import child_accounts

    monkeypatch.setattr(child_accounts, "is_child", lambda c, p=None: False)
    assert assistant_goods_actions._not_here(SimpleNamespace(), "Compliance") == "Compliance isn't kept on this MIA."


def test_the_hardware_store_is_his_projects_needs(monkeypatch):
    from core import assistant_requirement_actions as ara

    monkeypatch.setattr(ara, "needs_sentence", lambda c, w="": "Shed still needs 20 2x4s.")
    for words in ("What do I need from the hardware store?", "what do I need to get at Lowe's?",
                  "what do I still need for my projects?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "Shed still needs 20 2x4s.", words
    monkeypatch.setattr(ara, "needs_sentence", lambda c, w="": "Nothing's still needed.")
    assert "nothing I know of to pick up" in assistant_turn._own_tool_reply(SimpleNamespace(),
                                                                            "what do I need from the hardware store?")
