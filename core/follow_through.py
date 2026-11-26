"""
core.follow_through
=====================

A short follow-up to one of her code answers, made whole (the live sweep, 2026-11-26: "What about this month?"
after "How much did I spend last month?" got "check your bank statements", and "And the card?" after the truck
loan's balance got a made-up balance). His last question and the new words are joined in code (`merged`), and the
joined question goes to the same code answers that took the first one:

- a period for a period: "what about this month?" after a spending question asks it for this month;
- a thing for a thing: "and the card?" after "how much is my truck loan?" asks "how much is my card?", "how about
  water?" after "how much feed do I have left?", "and until New Year's?" after the days until Christmas;
- a size for a size: "and a 10 by 12?" after "the square footage of a 12 by 16 shed?" (only the question's own
  shapes are swapped).

`follow_on(text)` is the new words of a follow-up ("what about X", "how about X", "and X"), or None; `merged(prev,
x)` the whole question, or None when it can't be joined (then the model has it, as before). Only a question is
joined, never a command (the Fable review: "cancel the dentist reminder" then "what about today?"), and a debt
follow-up stays a debt question ("and the mortgage?" is what he owes on it).
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
    # "how much feed do I have left?" then "how about water?" (the live sweep, 2026-11-26)
    re.compile(r"^(?P<ask>\s*how much )(?P<thing>[\w' -]+?)(?P<end> (?:do|have) (?:i|we) (?:have|got)(?: left)?\s*\??\s*)$",
               re.I),
    # "how many days until Christmas?" then "and until New Year's?"
    re.compile(r"^(?P<ask>\s*how (?:many|much) (?:days|weeks|time)(?: is it| are there| left| do i have)? (?:until|till|"
               r"til|to|before) )(?P<thing>[\w' -]+?)(?P<end>\s*\??\s*)$", re.I),
)
_SIZE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:by|x)\s*\d+(?:\.\d+)?\b", re.I)


def follow_on(text: str) -> Optional[str]:
    """Pure logic. The new words of a short follow-up ("what about this month?" -> "this month"), or None."""
    found = _LEAD.match(text or "")
    return found.group("x").strip() if found else None


def merged(prev: str, x: str) -> Optional[str]:
    """Pure logic. His last question with the follow-up's words in place: a period for its period, or a thing for
    its thing (a debt follow-up kept a debt question; never a "before ..." or "that"), or a size for the thing's
    own (the last) size; None when they can't be joined or his last words weren't a
    question."""
    from core.money_periods import _PERIOD_WORDS, only_period

    prev, x = (prev or "").strip(), (x or "").strip()
    if not prev or not x:
        return None
    if not re.match(r"^\s*(?:hey mia,?\s+)?(?:what|how|did|do|does|is|are|was|were|when|where|who|which|have|has)\b",
                    prev, re.I):
        return None  # only a question is asked again: never a command re-run ("cancel the dentist reminder today?")
    if only_period(" " + x) and _PERIOD_WORDS.search(x):
        if _PERIOD_WORDS.search(prev):
            return _PERIOD_WORDS.sub(x, prev, count=1)
        return prev.rstrip(" ?.!") + f" {x}?"
    size = re.fullmatch(r"(?:an? |the )?(\d+(?:\.\d+)?\s*(?:by|x)\s*\d+(?:\.\d+)?)(?: one)?", x, re.I)
    if size and _SIZE.search(prev):  # "and a 10 by 12?" after "the square footage of a 12 by 16 shed?"
        last = list(_SIZE.finditer(prev))[-1]  # the thing's size, never a lumber size before it ("2 by 4 studs")
        return prev[:last.start()] + size.group(1) + prev[last.end():]
    for shape in _THING_ASKS:
        found = shape.match(prev)
        if found:
            days = shape is _THING_ASKS[-1]
            if not days and re.match(r"(?:before|after|with|without|for|in|on|at|by|until|till|that|then|it)\b", x,
                                     re.I):
                return None  # "and before interest?", "and before that?": not a thing to swap in
            words = r"(?:the|my|our|until|till|til|to|before)" if days else r"(?:the|my|our)"
            thing = re.sub(rf"^{words}\s+", "", x, flags=re.I)  # "until" only for the days-until question
            if shape is _THING_ASKS[0] and re.search(r"\b(?:loan|card|debt|balance|owe|left on)\b", prev, re.I) and \
                    not re.search(r"\b(?:loan|card|debt|balance)\b", thing, re.I):
                return f"How much do I owe on my {thing}?"  # "and the mortgage?" after a loan: still a debt question
            return f"{found.group('ask')}{thing}{found.group('end')}"
    return None
