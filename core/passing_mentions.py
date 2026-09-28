"""
core.passing_mentions
========================

"Propose, you confirm" (2026-09-28): when the owner mentions in passing
something MIA keeps a record of, she answers as usual and then offers to
record it, and does so only on a yes:

    "Ugh, the mower got a new battery today, $120."
    MIA: "... Want me to note that on the Riding Mower's page and log the $120?"
    "Yeah."   ->  noted, expense logged.

What counts (deliberately narrow; a wrong offer is noise, a missed one
is just a normal chat):
- **work done on a tracked item**: the item named ("the mower", "the
  truck") plus a done-verb ("got a new", "replaced", "changed",
  "sharpened"...). If it matches one of that item's maintenance tasks
  ("changed the oil" ~ "Change engine oil"), the offer is to mark the
  task done; otherwise to note it on the item's page. A dollar amount
  rides along as the cost.
- **a bill paid**: "paid" plus the name of a tracked bill.
- **a payment on a debt**: "paid $200 on the Chase card".
- **running out of something**: "we're out of milk and eggs" (not
  already on the grocery list).

Never for questions, plans or wishes ("need to", "should", "going to",
"didn't"), and never while MIA is just listening, journaling, off the
record, or tutoring (core/talk_it_out.py decides when to look).

Detection is code, not the model, and so is the offer's wording; the
yes runs the same tools the owner could have asked for directly, so the
result reads the same.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

OFFER_LIFETIME_SECONDS = 30 * 60

_DONE_VERBS = re.compile(
    r"\b(got (?:a |some )?new|put (?:a |some )?new|put on (?:a |some )?new|installed|replaced|changed|swapped|fixed|"
    r"repaired|serviced|sharpened|rotated|cleaned|greased|flushed|topped off|tuned up|patched|welded|"
    r"rebuilt|adjusted|tightened|aired up|inspected|renewed|watered|fertilized|pruned|sprayed)\b",
    re.IGNORECASE,
)
_NOT_DONE = re.compile(
    r"\b(need(?:s)? to|needs|should|going to|gonna|have to|has to|want to|wanna|will|won't|didn't|did not|"
    r"hasn't|haven't|can't|cannot|couldn't|if|maybe|might|thinking about|plan(?:ning)? to|when should|how do)\b",
    re.IGNORECASE,
)
_MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{2}))?")
_OUT_OF = re.compile(r"\b(?:we're|we are|i'm|i am|we|i)\s+(?:all\s+|almost\s+|about\s+|nearly\s+)?(?:out of|low on|running low on|running out of)\s+([a-z][a-z ,'&-]{1,60})",
                     re.IGNORECASE)
_PAID = re.compile(r"\b(?:paid|payed|made (?:a|the) payment)\b", re.IGNORECASE)
_YES = re.compile(r"^\s*(?:yes|yeah|yep|yup|ya|yes please|sure|ok|okay|please|please do|do it|go ahead|sounds good|"
                  r"that'd be great|that would be great|perfect|absolutely|definitely|yes ma'am|mhm|uh huh)\b[\s!.,]*"
                  r"(?:please|thanks|thank you|mia)?[\s!.]*$", re.IGNORECASE)
_STOP = {"the", "a", "an", "my", "our", "on", "in", "of", "to", "and", "for", "it", "its", "his", "her", "some", "new",
         "with", "at", "today", "yesterday", "this", "that", "just", "got", "put", "i", "we", "was", "is"}


@dataclass
class Offer:
    kind: str  # "task" | "note" | "bill" | "debt" | "grocery"
    question: str  # what MIA asks, after her reply
    calls: list[tuple[str, dict]] = field(default_factory=list)  # tools to run on a yes, in order
    expense: Optional[dict] = None  # a cost to log with a note: {"amount", "asset_id", "description"}
    created: float = field(default_factory=time.time)
    shown: bool = False  # set once MIA has actually asked (core/talk_it_out.with_offer)

    def expired(self, now: Optional[float] = None) -> bool:
        return (now or time.time()) - self.created > OFFER_LIFETIME_SECONDS


def is_yes(text: str) -> bool:
    """Pure logic. A short, plain yes to an offer."""
    return bool(_YES.match(text.strip().lower().replace("’", "'")))


def _stem(word: str) -> str:
    word = word.lower().strip("'")
    for suffix in ("ened", "ed", "ing", "en", "es", "s", "e"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _tokens(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z']+", text.lower()) if w not in _STOP and len(w) > 2}


def _money(text: str) -> Optional[float]:
    match = _MONEY.search(text)
    if not match:
        return None
    return float(match.group(1).replace(",", "") + "." + (match.group(2) or "00"))


def _names_in(text: str, names: list[str]) -> list[str]:
    """Which of `names` the text mentions, by full name or by its last
    word ("Riding Mower" -> "the mower") when that word is unique."""
    lowered = f" {text.lower()} "
    last_words: dict[str, list[str]] = {}
    for name in names:
        last_words.setdefault(name.lower().split()[-1], []).append(name)
    hits = []
    for name in names:
        full = re.search(rf"(?<![a-z0-9]){re.escape(name.lower())}(?![a-z0-9])", lowered)
        last = name.lower().split()[-1]
        short = len(last) >= 4 and len(last_words[last]) == 1 and re.search(
            rf"(?<![a-z0-9]){re.escape(last)}s?(?![a-z0-9])", lowered)
        if full or short:
            hits.append(name)
    return hits


def _clause(text: str, verb: re.Match) -> str:
    """The sentence the done-verb is in, tidied for a note."""
    start = max(text.rfind(ch, 0, verb.start()) for ch in ".!?\n") + 1
    ends = [i for i in (text.find(ch, verb.end()) for ch in ".!?\n") if i != -1]
    sentence = text[start:min(ends) if ends else None].strip(" ,;")
    sentence = re.sub(r"^(?:ugh|well|so|oh|hey|man|welp|finally|anyway)[,!]?\s+", "", sentence, flags=re.IGNORECASE)
    return sentence[:1].upper() + sentence[1:] if sentence else ""


def _and_list(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def detect_offer(text: str, context) -> Optional[Offer]:
    """The one offer worth making for this message, or None."""
    if "?" in text or _NOT_DONE.search(text):
        return None
    amount = _money(text)
    budget = getattr(context, "budget", None)

    # A bill paid, or a payment on a debt.
    if _PAID.search(text) and budget is not None:
        bills = [b.name for b in budget.all_bills()]
        named = _names_in(text, bills)
        if len(named) == 1:
            args = {"name": named[0], **({"amount": amount} if amount else {})}
            return Offer("bill", f"Want me to mark the {named[0]} bill paid" + (f" (${amount:,.2f})" if amount else "") + "?",
                         [("mark_bill_paid", args)])
        debts = [d.name for d in budget.all_debts()]
        named = _names_in(text, debts)
        if len(named) == 1 and amount:
            return Offer("debt", f"Want me to record the ${amount:,.2f} payment on {named[0]}?",
                         [("record_debt_payment", {"debt_name": named[0], "amount": amount})])

    # Work done on a tracked item.
    maintenance = getattr(context, "maintenance", None)
    verb = _DONE_VERBS.search(text)
    if verb and maintenance is not None:
        assets = maintenance.all_assets()
        named = _names_in(text, [a.name for a in assets])
        if len(named) == 1:
            asset = next(a for a in assets if a.name == named[0])
            said = _tokens(text)
            best, best_overlap = None, 0
            for task in maintenance.tasks_for_asset(asset.asset_id):
                wanted = _tokens(task.title)
                overlap = len(wanted & said)
                if wanted and overlap >= min(2, len(wanted)) and overlap > best_overlap:
                    best, best_overlap = task, overlap
            cost = f" and log the ${amount:,.2f}" if amount else ""
            if best is not None:
                args = {"title": best.title, "asset_name": asset.name, **({"cost": amount} if amount else {})}
                return Offer("task", f"Want me to mark “{best.title}” done on the {asset.name}{cost}?",
                             [("complete_maintenance_task", args)])
            note = _clause(text, verb)
            if note:
                expense = {"amount": amount, "asset_id": asset.asset_id, "description": f"{asset.name}: {note}"[:120]} if amount else None
                return Offer("note", f"Want me to note that on the {asset.name}'s page{cost}?",
                             [("add_asset_note", {"asset_name": asset.name, "note": note})], expense=expense)

    # Running out of something.
    kitchen = getattr(context, "kitchen", None)
    out = _OUT_OF.search(text)
    if out and kitchen is not None:
        phrase = re.split(r"\b(?:so|but|because|again|already|today|now|and i|and we)\b|[.!;]", out.group(1), maxsplit=1)[0]
        items = [i.strip(" ,'-") for i in re.split(r",|\band\b|&", phrase) if i.strip(" ,'-")]
        items = [re.sub(r"^(?:the|some|any)\s+", "", i) for i in items if len(i.split()) <= 3][:4]
        on_list = {g.name.lower() for g in kitchen.all_grocery_items() if not getattr(g, "checked", False)}
        items = [i for i in items if i.lower() not in on_list]
        if items:
            return Offer("grocery", f"Want me to add {_and_list(items)} to the grocery list?",
                         [("add_grocery_item", {"items": items})])
    return None


def carry_out(context, offer: Offer) -> str:
    """The owner said yes: run the offer's tools and say what happened."""
    registry = context.assistant_actions
    replies = [registry.execute(context, name, args) for name, args in offer.calls]
    if offer.expense and getattr(context, "budget", None) is not None:
        context.budget.add_expense(
            amount=offer.expense["amount"], category="Maintenance", description=offer.expense["description"],
            asset_id=offer.expense["asset_id"], notes="From something you mentioned to MIA.",
        )
        replies.append(f"Logged ${offer.expense['amount']:,.2f} as a Maintenance expense.")
    return " ".join(r for r in replies if r)
