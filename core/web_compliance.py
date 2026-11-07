"""
core.web_compliance
=====================

The Compliance screen (DEC-0040): every obligation, sorted the way
deadlines are read: **Overdue**, **Next 30 days**, **Later**, **To
check** (unverified, or undated), and **Done**. Each says when it's
really due (moved off a weekend or holiday, an extension to file kept
apart from the money's date), the fee, the documents, the next step, the
official link, whether it's verified, and the one step its row offers
(`next_step`: Verify, Where It Stands, Mark Filed, Mark Paid, Mark Done).
Served as /api/compliance; the web only formats.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def _money(x) -> str:
    """An amount in the person's currency (core.region.money)."""
    from core.region import money

    return money(x)


def _text(d: Optional[date]) -> str:
    """Pure logic. A date as ISO text, or "" for none."""
    return d.isoformat() if d else ""


def next_step(card: dict) -> dict:
    """Pure logic. The one thing a Compliance row offers (the design canvas's groups, DEC-0113): Verify (or Check
    Again) while it isn't verified, since only the person can; Where It Stands when it's overdue, to say what
    happened; otherwise the step its status points to: Mark Filed for a filing not yet in, Mark Paid once money is
    what's left, Mark Done for the rest. `opens` names the form the web shows; `action` is a ready action."""
    oid = card["id"]
    if not card["verified"] or card["stale"]:
        return {"label": "Check Again" if card["verified"] else "Verify", "opens": "verify"}
    if card["where"] == "overdue":
        return {"label": "Where It Stands", "opens": "status"}
    filing = "filing" in (card.get("kind") or "") or "return" in (card.get("title") or "").lower()
    if filing and card["status"] in ("applies", "ready to file", "extended"):
        step = ("Mark Filed", "submitted")
    elif card["status"] in ("submitted", "payment due") and (card.get("pay_on") or card.get("fee_text")
                                                             or card.get("estimate_text")):
        step = ("Mark Paid", "paid")
    else:
        step = ("Mark Done", "done")
    return {"label": step[0], "action": {"kind": "obligation.status", "label": step[0],
                                         "params": {"obligation_id": oid, "status": step[1]}}}


def compliance_page(context, today: Optional[date] = None) -> dict:
    """The Compliance screen's data: a card per obligation (licences, filings, taxes) with where it stands, its due, filing and payment dates (and whether a weekend or holiday moved them), fees, documents, next step, its source and when it was verified, its form values, and (while open) the one step its row offers; overdue first. Not available without the store or for a child."""
    from core.child_accounts import is_child
    from core.obligation_actions import OBLIGATION
    from core.obligations import STATUSES, effective_dates, starter_list, state
    from core.record_actions import record_form

    today = today or date.today()
    book = getattr(context, "obligations", None)
    if book is None or is_child(context):
        return {"available": False}
    cards = []
    for o in book.obligations:
        st = state(o, today)
        dates = effective_dates(o)
        cards.append({
            "id": o.obligation_id, "title": o.title, "kind": o.kind, "authority": o.authority,
            "jurisdiction": o.jurisdiction, "applies_to": o.applies_to, "period": o.period, "status": o.status,
            "where": st["where"], "due": st["due"], "days": st["days"], "verified": st["verified"], "stale": st["stale"],
            "file_on": _text(dates["file"]), "pay_on": _text(dates["pay"]),
            "moved": [w for w, m in (("filing", dates["file_moved"]), ("payment", dates["pay_moved"])) if m],
            "stated_due": o.due_date, "extended_to": o.extended_to,
            "fee_text": _money(o.fee) if o.fee else "", "estimate_text": _money(o.estimate) if o.estimate else "",
            "documents": o.documents, "next_action": o.next_action, "source_url": o.source_url,
            "source_title": o.source_title, "rule": o.rule, "verified_on": o.verified_on, "proof": o.proof,
            "recurrence": o.recurrence, "notes": o.notes,
            "values": {f.name: (" ".join(str(x) for x in o.reminders) if f.name == "reminders" else getattr(o, f.name))
                       for f in OBLIGATION.fields},
        })
    for c in cards:
        if c["where"] != "closed":
            c["next"] = next_step(c)
    order = {"overdue": 0, "upcoming": 1, "later": 2, "undated": 3, "closed": 4}
    cards.sort(key=lambda c: (order[c["where"]], c["due"] or "9999", c["title"].lower()))
    groups = {
        "overdue": [c for c in cards if c["where"] == "overdue"],
        "soon": [c for c in cards if c["where"] == "upcoming"],
        "later": [c for c in cards if c["where"] == "later" and c["verified"]],
        "check": [c for c in cards if c["where"] in ("later", "undated") and not c["verified"]
                  or c["where"] == "undated" and c["verified"]],
        "done": [c for c in cards if c["where"] == "closed"][:30],
    }
    open_ = [c for c in cards if c["where"] != "closed"]
    fees = sum(o.fee for o in book.obligations if o.status not in ("done", "paid", "not applicable")
               and state(o, today)["where"] in ("overdue", "upcoming"))
    region = getattr(context, "config", None)
    code = (region.get("region.state", "") if region is not None else "") or ""
    return {
        "available": True, "as_of": today.isoformat(), "groups": groups,
        "counts": {"overdue": len(groups["overdue"]), "soon": len(groups["soon"]),
                   "unverified": sum(1 for c in open_ if not c["verified"]), "open": len(open_)},
        "fees_soon_text": _money(fees) if fees else "",
        "forms": {"obligation": record_form(OBLIGATION)},
        "statuses": [s for s in STATUSES if s != "to verify"],
        "starters": [s for s in starter_list(code) if not any(o.starter_id == s["id"] and o.status not in
                                                              ("done", "paid", "not applicable")
                                                              for o in book.obligations)],
    }
