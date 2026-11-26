"""
core.follow_through
=====================

A short follow-up to one of her code answers, made whole (the live sweep, 2026-11-26: "What about this month?"
after "How much did I spend last month?" got "check your bank statements", and "And the card?" after the truck
loan's balance got a made-up balance). His last question and the new words are joined in code (`merged`), and the
joined question goes to the same code answers that took the first one:

- a period for a period: "what about this month?" after a spending question asks it for this month;
- a thing for a thing: "and the card?" after "how much is my truck loan?" asks "how much is my card?"; "and the
  kitchen?" after "how many cutting boards do I have?" never (only the question's own shapes are swapped).

`follow_on(text)` is the new words of a follow-up ("what about X", "how about X", "and X"), or None; `merged(prev,
x)` the whole question, or None when it can't be joined (then the model has it, as before).
"""

from __future__ import annotations

import re
from typing import Optional

_LEAD = re.compile(r"^\s*(?:ok(?:ay)?,?\s+|so,?\s+|and\s+|but\s+)?(?:what about|how about|and what about|and how about|"
                   r"and)\s+(?P<x>[^?]{1,40}?)\s*[?.!]*\s*$", re.I)
_THING_ASKS = (
    re.compile(r"^(?P<ask>\s*how much (?:is|do (?:i|we) (?:still )?owe on|is left on) (?:my|the|our) )(?P<thing>[\w' -]+?)"
               r"(?P<end>\s*\??\s*)$", re.I),
    re.compile(r"^(?P<ask>\s*did (?:i|we) (?:already )?pay (?:the |my |our )?)(?P<thing>[\w' -]+?)(?P<end>(?: bill)?"
               r"(?: yet| already| this month)?\s*\??\s*)$", re.I),
    re.compile(r"^(?P<ask>\s*how many )(?P<thing>[\w' -]+?)(?P<end> (?:do|have) (?:i|we) (?:have|got|got left|left)"
               r"(?: in stock| on hand| left)?\s*\??\s*)$", re.I),
)


def follow_on(text: str) -> Optional[str]:
    """Pure logic. The new words of a short follow-up ("what about this month?" -> "this month"), or None."""
    found = _LEAD.match(text or "")
    return found.group("x").strip() if found else None


def merged(prev: str, x: str) -> Optional[str]:
    """Pure logic. His last question with the follow-up's words in place: a period for its period, or a thing for
    its thing; None when they can't be joined."""
    from core.money_periods import _PERIOD_WORDS, only_period

    prev, x = (prev or "").strip(), (x or "").strip()
    if not prev or not x:
        return None
    if only_period(" " + x) and _PERIOD_WORDS.search(x):
        if _PERIOD_WORDS.search(prev):
            return _PERIOD_WORDS.sub(x, prev, count=1)
        return prev.rstrip(" ?.!") + f" {x}?"
    thing = re.sub(r"^(?:the|my|our)\s+", "", x, flags=re.I)
    for shape in _THING_ASKS:
        found = shape.match(prev)
        if found:
            return f"{found.group('ask')}{thing}{found.group('end')}"
    return None
