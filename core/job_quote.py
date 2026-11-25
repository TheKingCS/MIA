"""
core.job_quote
================

A quote from a job's words (brainstorm round 14; Zac's vision: "my businesses skills ... automation of as much as
possible"): "write a quote for Sarah's 12 by 16 deck" works the job out in code and drafts the quote for his yes.

- **The job** (`ASK`, `job_of`): a quote asked for, for a customer and a structure with its size; the structure and
  size are read the way the materials route reads them (core/assistant_plan_actions.structure_for, sizes_for), so
  the list is the calculators' (core/build_calcs.py), never the model's.
- **The materials' cost** (`priced`): each item at its unit cost from the workshop's materials (core/plan_library._match),
  the whole quantity (what's on hand is used up too); an item with no price known is named, never guessed.
- **The quote** (`reply`): a Draft (quote.add, undoable) for the customer named when he has them, the known materials
  as its extras, his usual margin, the list and what isn't priced in its notes; labor isn't in it until he says the
  hours (MIA has no hours for a deck), and it's sent only when he sends it.
"""

from __future__ import annotations

import re
from typing import Optional

ASK = re.compile(r"^\s*(?:can you\s+|could you\s+|please\s+)?(?:write|make|draft|put together|draw up|do)\s+(?:up\s+)?"
                 r"(?:an?\s+)?(?:quote|estimate|bid)\s+for\s+(?P<rest>.+?)\s*[.!?]*\s*$", re.I)
_WHOSE = re.compile(r"^(?:(?P<who>[a-z][\w-]*)(?:'s|’s)\s+(?P<job1>.+)|(?:a\s+|an\s+|the\s+)?(?P<job2>.+?)\s+for\s+"
                    r"(?P<who2>[a-z][\w-]*))$", re.I)


def job_of(words: str) -> Optional[tuple]:
    """Pure logic. (customer's name or "", the job's words) for "write a quote for Sarah's 12 by 16 deck" or "make a
    quote for a 12 by 16 deck for Sarah", else None."""
    found = ASK.match(str(words or ""))
    if not found:
        return None
    rest = found.group("rest").strip()
    whose = _WHOSE.match(rest)
    if whose:
        who = whose.group("who") or whose.group("who2") or ""
        job = whose.group("job1") or whose.group("job2") or ""
        if who.lower() not in ("a", "an", "the", "my", "his", "her", "their", "our"):
            return who, job
    return "", rest


def priced(context, items: list) -> tuple:
    """(known cost, [items with no price]) for a materials list's items at the workshop's unit costs."""
    from core.plan_library import _match

    stock = list(getattr(getattr(context, "materials", None), "all_materials", lambda: [])())
    cost, unpriced = 0.0, []
    for item in items:
        match = _match(item["name"], stock)
        if match is not None and getattr(match, "unit_cost", 0):
            cost += float(item["qty"]) * float(match.unit_cost)
        else:
            unpriced.append(item["name"])
    return round(cost, 2), unpriced


def reply(context, words: str) -> Optional[str]:
    """The draft quote for the job his words name, or None when they aren't a quote for a structure with its size
    (then "make a quote for ..." goes to make_quote as before)."""
    from core.assistant_plan_actions import calculate, size_words, sizes_for, structure_for

    found = job_of(words)
    if found is None:
        return None
    who, job = found
    calc = structure_for(job)
    if not calc or not size_words(job):
        return None
    try:
        result = calculate(calc, **sizes_for(calc, {"size": job}))
    except (TypeError, ValueError):
        return None
    listed = result.as_dict()
    cost, unpriced = priced(context, listed["items"])
    from core.assistant_correction_actions import _one, _run
    from core.region import money

    params = {"title": result.title[:1].upper() + result.title[1:], "extras": cost,
              "notes": ("Materials (worked out by MIA): " + "; ".join(
                  f"{i['qty']:g} {i.get('unit', '') + ' ' if i.get('unit') else ''}{i['name']}" for i in listed["items"])
                        + (f". Not priced yet: {', '.join(unpriced)}." if unpriced else ".")
                        + " Labor not included: add your hours.")}
    book = getattr(context, "business", None)
    named = ""
    if who and book is not None:
        person = _one(list(book.customers), who.lower(), lambda c: c.name, "customer")
        if isinstance(person, str):
            named = f" I don't have {who} as a customer yet, so it's for no one: say \"add a customer named {who}\"."
        else:
            params["customer_id"] = person.customer_id
    done = _run(context, "quote.add", params)
    if "undo that" not in done:  # it wasn't made: say why, and nothing about a draft that isn't there
        return done
    priced_words = (f"the materials I have prices for come to {money(cost)}" if cost else
                    "none of the materials have prices in the workshop yet")
    gaps = f"; not priced: {', '.join(unpriced[:4])}{' and more' if len(unpriced) > 4 else ''}" if unpriced else ""
    return (f"{done} A draft for {result.title}: {priced_words}{gaps}, plus your margin. Labor isn't in it: tell me "
            f"the hours, and check it before you send it.{named}")
