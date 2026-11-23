"""
core.market_eve
=================

The day before a market day (Jarvis brainstorm round 2; Zac, 2026-11-23: "my businesses skills ... automation"): when
he has a market day set for tomorrow (core/business_book.py MarketDay, still open), one message through the gate with
what to bring: for each good, how many usually sell and so how many to take (core/goods.demand, from his own closed
market days), beside how many he has on hand, and any that's short. All of it from his records (the Workshop's Goods,
core/web_craft.goods_section); nothing is guessed, and a good with no market history yet is named as on hand only.

`plan(context, today)` is the market and its list; `offer(context, now)` the daily check's message (TIMELY: it matters
by tonight), once per market day.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)


def plan(context, today: Optional[date] = None) -> Optional[dict]:
    """{market: {place, date}, goods: [{name, bring, on_hand, short}]} for an open market day tomorrow, or None."""
    from core.web_craft import goods_section

    today = today or date.today()
    business = getattr(context, "business", None)
    tomorrow = (today + timedelta(days=1)).isoformat()
    market = next((m for m in (getattr(business, "markets", []) or [])
                   if m.date == tomorrow and m.status == "open"), None)
    if market is None:
        return None
    goods = []
    for g in goods_section(context, today).get("goods", []):
        usual = g.get("usual") or {}
        bring = usual.get("bring")
        goods.append({"name": g["name"], "bring": bring, "on_hand": g.get("on_hand", 0),
                      "on_hand_text": g.get("on_hand_text", ""),
                      "short": bring is not None and g.get("on_hand", 0) < bring})
    return {"market": {"place": market.place or "the market", "date": market.date, "id": market.market_id},
            "goods": goods}


def words(found: dict) -> str:
    """Pure logic. The list in sentences: what to bring, what's short, what has no history yet."""
    place = found["market"]["place"]
    with_history = [g for g in found["goods"] if g["bring"] is not None]
    without = [g for g in found["goods"] if g["bring"] is None and g["on_hand"]]
    parts = [f"Tomorrow at {place}."]
    if with_history:
        parts.append("Bring " + "; ".join(f"{g['bring']:g} {g['name']}" + (f" (only {g['on_hand_text'] or g['on_hand']} on hand)"
                                                                          if g["short"] else "")
                                         for g in with_history[:8]) + ", from what usually sells.")
    if without:
        parts.append("No market history yet for " + ", ".join(f"{g['name']} ({g['on_hand_text'] or g['on_hand']} on "
                                                              "hand)" for g in without[:5]) + ".")
    if len(parts) == 1:
        parts.append("Nothing made and on hand in the Workshop's Goods to take yet.")
    return " ".join(parts)


def offer(context, now: datetime) -> list:
    """The daily check's message the day before a market day: TIMELY, once per market day."""
    from core.communication_gate import TIMELY, Candidate

    try:
        found = plan(context, now.date())
    except Exception:  # noqa: BLE001 - the goods that can't be read never break the check
        log.exception("Market eve: the goods couldn't be read")
        return []
    if found is None:
        return []
    return [Candidate(topic="market_eve", title=f"Market tomorrow: {found['market']['place']}",
                      message=words(found), urgency=TIMELY, source="system",
                      fingerprint=f"market-eve-{found['market']['id']}")]
