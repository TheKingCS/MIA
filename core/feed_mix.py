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

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_BATCH = re.compile(r"(\d+(?:\.\d+)?)\s*(lbs?|pounds?|kg|kilos?|kilograms?)\b", re.I)


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
    """Pure logic. (feed one %, feed two %, the target %, batch, unit) from what he said: the target is the
    percentage after "to", "get", "make" or "for", else the last one; None without three percentages."""
    text = str(said or "")
    found = [float(x) for x in _PCT.findall(text)]
    if len(found) < 3:
        return None
    m = re.search(r"\b(?:to|get|make|for|at|reach)\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*%", text, re.I)
    target = float(m.group(1)) if m else found[-1]
    feeds = [x for x in found if x != target][:2]
    if len(feeds) < 2:
        return None
    batch = _BATCH.search(text)
    return feeds[0], feeds[1], target, (float(batch.group(1)) if batch else None), (batch.group(2) if batch else "")


def say(said: str) -> str:
    """For "how do I mix 16% and 32% feed to get 20%?": the parts, the shares and any batch's amounts."""
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
    said_ = (f"For {found['target']:g}%: {p_low:g} parts of the {found['low']:g}% feed to {p_high:g} parts of the "
             f"{found['high']:g}% ({s_low:g}% and {s_high:g}% of the mix)")
    if found["amounts"]:
        u = "lb" if unit.lower().startswith(("lb", "pound")) else "kg"
        said_ += (f"; in {batch:g} {u}: {found['amounts'][0]:g} {u} of the {found['low']:g}% and "
                  f"{found['amounts'][1]:g} {u} of the {found['high']:g}%")
    return said_ + ". The same square works for any one nutrient, calcium or fat."
