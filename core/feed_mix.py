"""
core.feed_mix
===============

Mixing two feeds to a target protein, the Pearson square (Jarvis brainstorm, round 5: homestead). "How do I mix 16%
layer feed and a 32% supplement to get 20%?" says how many parts of each, the share of each, and, given a batch
size, the pounds of each; worked out in code, the model only says it.

How: `mix(low, high, target, batch)` is pure: parts of the low feed are (high - target), parts of the high feed are
(target - low); the target must lie between the two, or there's no mix that reaches it (said, never forced). A batch
in pounds or kilograms splits by those shares. `read(said)` picks the three percentages and any batch out of what he
said. Protein is the usual target, but the arithmetic is the same for any one nutrient (calcium, fat).
"""

from __future__ import annotations

import re
from typing import Optional

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent\b|per cent\b)(?!\s*(?:\w+\s+)?(?:calcium|fat|fib(?:er|re)|"
                  r"moisture|salt|phosphorus|off)\b)", re.I)  # a protein figure, never "5% calcium" or "10% off"
_BATCH = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(lbs?|pounds?|kg|kilos?|kilograms?)\b", re.I)
_TARGET = re.compile(r"\b(?:get|make|reach|want|need|end up (?:with|at))\s+(?:a\s+|to\s+)?(\d+(?:\.\d+)?)\s*"
                     r"(?:%|percent\b|per cent\b)", re.I)


class MixError(ValueError):
    """A mix that can't be made: said in words."""


def mix(low: float, high: float, target: float, batch: Optional[float] = None) -> dict:
    """Pure logic. The Pearson square: {"parts": (low feed, high feed), "shares": (percent, percent), "amounts":
    (batch of low, batch of high) or None}. MixError when the target isn't between the two feeds."""
    low, high = sorted((float(low), float(high)))
    target = float(target)
    if low == high:
        raise MixError("The two feeds have the same protein, so mixing them can't change it.")
    if not low < target < high:
        raise MixError(f"{target:g}% isn't between {low:g}% and {high:g}%, so no mix of these two reaches it.")
    parts = (round(high - target, 2), round(target - low, 2))
    total = parts[0] + parts[1]
    shares = (round(parts[0] / total * 100, 1), round(parts[1] / total * 100, 1))
    amounts = (round(batch * parts[0] / total, 1), round(batch * parts[1] / total, 1)) if batch else None
    return {"low": low, "high": high, "target": target, "parts": parts, "shares": shares, "amounts": amounts}


def read(said: str) -> Optional[tuple]:
    """Pure logic. (feed one %, feed two %, the target %, batch, unit) from what he said ("%" or "percent"; a
    calcium, fat or fibre figure, or "10% off", is never a feed): the target is the one after get, make, reach, want
    or need when it lies between the others, else the middle one (the only one a mix can reach); one figure removed
    for the target by its place, never every copy of its value. None without three percentages."""
    text = str(said or "")
    marks = list(_PCT.finditer(text))
    if len(marks) < 3:
        return None
    values = [float(m.group(1)) for m in marks[:3]]
    keyed = list(_TARGET.finditer(text))
    pick = None
    if keyed:  # the last get/make/want...; one before a figure he said as a feed is still that figure
        start = keyed[-1].start(1)
        pick = next((i for i, m in enumerate(marks[:3]) if m.start(1) == start), None)
    if pick is None or not min(values) <= values[pick] <= max(values):
        pick = sorted(range(3), key=lambda i: values[i])[1]  # the middle one: the only one a mix can reach
    target = values[pick]
    feeds = [v for i, v in enumerate(values) if i != pick]
    batch = _BATCH.search(text)
    return feeds[0], feeds[1], target, (float(batch.group(1)) if batch else None), (batch.group(2) if batch else "")


def say(said: str) -> str:
    """For "how do I mix 16% and 32% feed to get 20%?": the parts (one part said as one), the shares and any batch's
    amounts."""
    got = read(said)
    if got is None:
        return ("Give me the two feeds' protein and the protein you want, like \"mix 16% layer and 32% supplement "
                "to 20%\", and the batch size if you like (\"100 lb\").")
    a, b, target, batch, unit = got
    try:
        found = mix(a, b, target, batch)
    except MixError as problem:
        return str(problem)
    p_low, p_high = found["parts"]
    s_low, s_high = found["shares"]
    said_ = (f"For {found['target']:g}%: {p_low:g} part{'s' if p_low != 1 else ''} of the {found['low']:g}% feed to "
             f"{p_high:g} part{'s' if p_high != 1 else ''} of the {found['high']:g}% ({s_low:g}% and {s_high:g}% of "
             f"the mix)")
    if found["amounts"]:
        u = "lb" if unit.lower().startswith(("lb", "pound")) else "kg"
        said_ += (f"; in {batch:g} {u}: {found['amounts'][0]:g} {u} of the {found['low']:g}% and "
                  f"{found['amounts'][1]:g} {u} of the {found['high']:g}%")
    return said_ + ". The same square works for any one nutrient, calcium or fat."
