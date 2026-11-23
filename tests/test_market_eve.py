"""
tests.test_market_eve
=======================

The day before a market day (core/market_eve.py): what to bring from what usually sells, beside what's on hand, the
short ones and the goods without history named; once per market day, only for an open one tomorrow.
"""

from datetime import date, datetime
from types import SimpleNamespace

from core import market_eve as me

TODAY = date(2026, 11, 27)


def _ctx(markets, goods, monkeypatch):
    import core.web_craft as web_craft

    monkeypatch.setattr(web_craft, "goods_section", lambda context, today=None: {"goods": goods})
    return SimpleNamespace(business=SimpleNamespace(markets=markets))


def _market(day, status="open"):
    return SimpleNamespace(market_id="m1", place="Saturday market", date=day, status=status)


GOODS = [{"name": "Eggs", "on_hand": 8, "on_hand_text": "8 dozen", "usual": {"bring": 12, "avg_sold": 10}},
         {"name": "Jam", "on_hand": 20, "on_hand_text": "20 jars", "usual": {"bring": 6, "avg_sold": 5}},
         {"name": "Cutting boards", "on_hand": 3, "on_hand_text": "3", "usual": None}]


def test_the_day_before_she_says_what_to_bring_and_whats_short(monkeypatch):
    found = me.plan(_ctx([_market("2026-11-28")], GOODS, monkeypatch), TODAY)
    said = me.words(found)
    assert said.startswith("Tomorrow at Saturday market.")
    assert "12 Eggs (only 8 dozen on hand)" in said and "6 Jam" in said and "only 20" not in said
    assert "No market history yet for Cutting boards (3 on hand)" in said


def test_only_an_open_market_tomorrow_counts(monkeypatch):
    assert me.plan(_ctx([_market("2026-11-29")], GOODS, monkeypatch), TODAY) is None
    assert me.plan(_ctx([_market("2026-11-28", status="closed")], GOODS, monkeypatch), TODAY) is None


def test_it_is_said_once_per_market_day(monkeypatch):
    [said] = me.offer(_ctx([_market("2026-11-28")], GOODS, monkeypatch), datetime(2026, 11, 27, 9))
    assert said.topic == "market_eve" and said.urgency == "timely" and said.fingerprint == "market-eve-m1"
