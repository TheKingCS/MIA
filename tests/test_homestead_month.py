"""
tests.test_homestead_month
============================

"What should I be doing on the homestead this month?" (core/homestead_year.this_month, brainstorm round 18): his own
month first, then the season's usual work, the flock's only with hens.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, homestead_year


def test_his_month_then_the_seasons_work(monkeypatch):
    monkeypatch.setattr(homestead_year, "year", lambda c, t=None: [
        {"month": "2026-12", "label": "December 2026", "items": [("2026-12-05", "Sharpen blades (Riding Mower)")]}])
    with_hens = SimpleNamespace(flock=SimpleNamespace(flocks=[SimpleNamespace(hens=6)]))
    said = homestead_year.this_month(with_hens, date(2026, 12, 2))
    assert said.startswith("From your records this December: Sharpen blades (Riding Mower).")
    assert "keep the hens' water from freezing" in said and "order seeds" in said
    without = homestead_year.this_month(SimpleNamespace(), date(2026, 12, 2))
    assert "hens' water" not in without


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(homestead_year, "this_month", lambda c, t=None: "the month")
    for words in ("What should I be doing on the homestead this month?", "homestead chores this month",
                  "what needs doing around the place?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the month", words
