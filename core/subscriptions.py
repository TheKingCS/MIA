"""
core.subscriptions
====================

DEC-0054's "still using it?" mark on subscriptions (2026-11-07; the
unused-subscription finding core/findings.py listed as not built "for want of
data": nothing recorded use). Now the person records it: "I still use
Netflix", or Still Using on the bill in Money, stamps the bill's
`still_using_on` with today.

- `is_subscription(bill)`: a repeating bill that reads like one (its category
  is Entertainment, or its name or notes say subscription, membership,
  streaming, a plan or premium), or one already marked.
- `unconfirmed(context, today)`: subscriptions not confirmed in
  CHECK_DAYS (or ever, once they've been around that long), dearest first.
- `still_using_subscription` (core/findings.py): the quiet finding, never
  unprompted (show, don't judge: what's unneeded is the person's call).
- `bill.still_using`: the mark, as an action (Money's button; by voice,
  still_using_subscription).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

CHECK_DAYS = 90
_WORDS = re.compile(r"\b(subscriptions?|membership|member|streaming|premium|plus|pro plan|monthly plan|annual plan)\b")


def is_subscription(bill) -> bool:
    """Pure logic. Whether a bill is a subscription: it repeats, and it's been marked, is filed as Entertainment, or
    its name or notes say so."""
    if not bill.recurrence:
        return False
    if bill.still_using_on or bill.category == "Entertainment":
        return True
    return bool(_WORDS.search(f"{bill.name} {bill.notes}".lower()))


def _since(iso: str) -> Optional[date]:
    """A stored ISO date or datetime as a date, None when blank or unreadable."""
    try:
        return date.fromisoformat((iso or "")[:10])
    except ValueError:
        return None


def unconfirmed(context, today: date) -> list:
    """Subscriptions not said to be in use within CHECK_DAYS (one never marked counts once it's been on the books that
    long), dearest first."""
    budget = getattr(context, "budget", None)
    out = []
    for bill in budget.all_bills() if budget is not None else []:
        if not is_subscription(bill):
            continue
        last = _since(bill.still_using_on) or _since(bill.created_at)
        if last is not None and (today - last).days < CHECK_DAYS:
            continue
        out.append(bill)
    return sorted(out, key=lambda b: -float(b.amount or 0))


def _bill(context, params):
    """The bill the params name; ActionError when it's gone."""
    bill = _need(context, "budget").get_bill(str(params.get("bill_id") or ""))
    if bill is None:
        raise ActionError("That bill isn't there anymore.")
    return bill


def _still_using(context, params) -> str:
    """Does bill.still_using: today's date on the bill's mark."""
    bill = _bill(context, params)
    context.budget.update_bill(bill.bill_id, still_using_on=date.today().isoformat())
    return f"Noted: you still use {bill.name}. I'll ask again in {CHECK_DAYS // 30} months."


SUBSCRIPTION_ACTIONS = {"bill.still_using": ActionType(
    "bill.still_using", "Still Using", {"bill_id": "the subscription"},
    lambda c, p: f"Mark {_bill(c, p).name} as still in use", _still_using)}
ACTION_TYPES.update(SUBSCRIPTION_ACTIONS)
