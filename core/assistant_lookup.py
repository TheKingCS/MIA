"""
core.assistant_lookup
=======================

How Assistant actions find the user's own records from the words they
actually say. People say "the truck" and "did the oil", not "Pickup
Truck" and "Oil change", and the model can only pass on their words.

`resolve_by_name()` tries, in order: an exact (case-insensitive) name,
then a name containing the words or contained in them, then
shared-word overlap (with light stemming: "watered" matches "Water
tomatoes"). It only accepts a match when exactly one record is best;
a tie asks the user which one, and no match lists what does exist so
the conversation can recover. Destructive actions pass
`allow_fuzzy=False` and keep the old exact-name-only rule, since guessing
wrong there loses data.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, Optional, TypeVar

T = TypeVar("T")

# Words that carry no signal about which record is meant.
_FILLER = {
    "the", "a", "an", "my", "our", "his", "her", "their", "of", "on", "in", "for", "to", "and",
    "with", "at", "from", "some", "this", "that", "these", "those", "it",
}
_MAX_LISTED = 8


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"  # groceries -> grocery, batteries -> battery
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


# Generic trailing words that don't identify a record by themselves
# ("Pepper Plants" is about peppers; "Cutting Board" about cutting boards).
_GENERIC_HEADS = {"plant", "bed", "bush", "tree", "row", "box", "pot", "board", "garden", "set", "kit"}


def head_word(name: str) -> str:
    """Pure logic. The word that identifies a record when mentioned alone:
    the last meaningful word, skipping generic ones and very short ones.
    "Riding Mower" -> "mower"; "Pepper Plants" -> "pepper"; "Garden
    Omelette" -> "omelette"; "" when there's nothing usable."""
    words = [_stem(w) for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in _FILLER]
    words = [w for w in words if len(w) >= 4]
    for word in reversed(words):
        if word not in _GENERIC_HEADS:
            return word
    return words[-1] if words else ""


def name_tokens(text: str) -> set[str]:
    """Pure logic. Meaningful, lightly-stemmed words in `text`."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if w not in _FILLER}


def resolve_by_name(
    items: Iterable[T],
    name: str,
    get_name: Callable[[T], str],
    kind: str,
    allow_fuzzy: bool = True,
) -> tuple[Optional[T], Optional[str]]:
    """Returns (item, None) for one confident match, else (None, a short
    message to say back to the user)."""
    items = list(items)
    wanted = (name or "").strip()
    if not wanted:
        return None, f"Which {kind}?{_available(items, get_name, kind)}"
    lowered = wanted.lower()

    exact = [i for i in items if get_name(i).strip().lower() == lowered]
    if len(exact) == 1:
        return exact[0], None
    if len(exact) > 1:
        return None, _ambiguous(exact, get_name, kind, wanted)
    if not allow_fuzzy:
        return None, f"I don't have {_a(kind)} called '{wanted}'.{_available(items, get_name, kind)}"

    wanted_tokens = name_tokens(wanted)
    contains = [
        i for i in items
        if lowered in get_name(i).lower() or (get_name(i).lower() in lowered and get_name(i).strip())
    ]
    if len(contains) == 1:
        return contains[0], None

    pool = contains or items
    scored = [(len(wanted_tokens & name_tokens(get_name(i))), i) for i in pool]
    best = max((s for s, _ in scored), default=0)
    if best > 0:
        top = [i for s, i in scored if s == best]
        if len(top) == 1:
            return top[0], None
        return None, _ambiguous(top, get_name, kind, wanted)
    if len(contains) > 1:
        return None, _ambiguous(contains, get_name, kind, wanted)
    return None, f"I don't have {_a(kind)} called '{wanted}'.{_available(items, get_name, kind)}"


def _a(kind: str) -> str:
    return f"an {kind}" if kind[:1].lower() in "aeiou" else f"a {kind}"


def _ambiguous(items: list, get_name: Callable, kind: str, wanted: str) -> str:
    names = ", ".join(sorted(get_name(i) for i in items)[:_MAX_LISTED])
    return f"More than one {kind} matches '{wanted}' ({names}). Which one did you mean?"


def _available(items: list, get_name: Callable, kind: str) -> str:
    if not items:
        return f" You don't have any {kind}s yet."
    names = sorted(get_name(i) for i in items)
    more = f", and {len(names) - _MAX_LISTED} more" if len(names) > _MAX_LISTED else ""
    return f" You have: {', '.join(names[:_MAX_LISTED])}{more}."
