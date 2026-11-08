"""
core.answer_compare
=====================

"Do you prefer this response, or this one?" (DEC-0138): the surface over core/response_style.py. Now and then, after
a reply in Talk, MIA offers the same answer a second way that differs on one dimension of style (how long, how it's
laid out, its tone, what comes first), the one she's least sure about (`StyleBook.next_experiment`). The person picks;
`style.pick` records it, and the learned style feeds her phrasing from then on (`response_style.style_for`, already in
the chat prompt).

The facts never change, only the phrasing: the second way is the model rephrasing her own reply, and code checks it
before it's shown (`same_facts`: no number that wasn't in the reply, not empty, not the same text). One that fails is
never offered. Offers are rare: at most once a day, only on a reply long enough for style to matter, never when the
person turned it off ("stop asking which I prefer", `style.compare`), and never on a private turn (the caller says).

Also here: the How MIA Answers screen (web/answers.html, `screen`) and its actions: `style.pick` (one of the two),
`style.set` (say outright how a dimension should be; drops that dimension's earlier picks), `style.reset` (forget
every pick) and `style.compare` (offers on or off). All undoable.

Server flow (server/app.py `/api/talk/compare`): `plan` under the turn lock, `restyle` (the model, outside the lock),
then `keep` under the lock again.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Callable, Optional

from core import person_settings
from core.actions import ACTION_TYPES, ActionError, ActionType

MIN_CHARS = 140  # a reply shorter than this has too little style to compare
COMPARE_KEY, LAST_KEY, PENDING_KEY = "style.compare", "style.last_offer", "style.pending"

# The screen's words for each dimension and value (core/response_style.DIMENSIONS holds the values themselves).
NAMES = {"length": "How long", "format": "How it's laid out", "tone": "Tone", "lead": "What comes first"}
LABELS = {
    "standard": "Standard", "brief": "Brief", "detailed": "Detailed",
    "mixed": "A line, then bullets", "prose": "Prose", "bulleted": "Bullet points",
    "warm": "Warm", "neutral": "Neutral", "direct": "Direct",
    "answer_first": "The answer first", "context_first": "The context first",
}
# What the model is asked to do for each value (the rephrasing instruction).
ASK = {
    ("length", "brief"): "Make it much shorter: one or two sentences.",
    ("length", "standard"): "Keep it a normal, complete length.",
    ("length", "detailed"): "Make it more thorough, explaining a little more, without adding new facts.",
    ("format", "prose"): "Write it as flowing prose, no bullet points.",
    ("format", "bulleted"): "Lay it out as short bullet points.",
    ("format", "mixed"): "One line of prose, then bullet points where they help.",
    ("tone", "warm"): "Use a warm, friendly tone.",
    ("tone", "neutral"): "Use a plain, neutral tone.",
    ("tone", "direct"): "Be direct: no preamble, no pleasantries.",
    ("lead", "answer_first"): "Lead with the answer, then the why.",
    ("lead", "context_first"): "Give the context first, then the answer.",
}


def _book(context):
    """The person's StyleBook, or None on a MIA without one."""
    return getattr(context, "response_style", None)


def numbers(text: str) -> set:
    """Pure logic. The numbers written in a text (with commas and decimals, as written), to check facts didn't
    change."""
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")}


def same_facts(reply: str, other: str) -> bool:
    """Pure logic. Whether a rephrasing can be shown beside the reply: not empty, not the same words, and no number in
    it that the reply didn't have (a changed or invented figure is a changed fact)."""
    other = (other or "").strip()
    if not other or " ".join(other.split()) == " ".join((reply or "").split()):
        return False
    return numbers(other) <= numbers(reply)


def restyle_prompt(reply: str, dimension: str, value: str) -> str:
    """Pure logic. The instruction for the model: the same answer, one thing about its style changed, facts kept."""
    return ("Rewrite the assistant reply below. " + ASK[(dimension, value)] + " Keep every fact, name and number "
            "exactly as it is; add nothing new and leave nothing important out. Reply with the rewritten text only.\n\n"
            "Reply:\n" + (reply or "").strip())


def offers_on(context) -> bool:
    """Whether the person lets MIA offer two ways (on unless they turned it off)."""
    return bool(person_settings.get(context, COMPARE_KEY, True))


def plan(context, reply: str, today: Optional[date] = None, private: bool = False) -> Optional[dict]:
    """What to compare after this reply ({dimension, a, b}: a is the style the reply was made in, b the challenger), or
    None when no offer fits today: no style store, offers off, a private turn, a short reply, or one already offered
    today."""
    book = _book(context)
    today = today or date.today()
    if book is None or private or not offers_on(context) or len((reply or "").strip()) < MIN_CHARS:
        return None
    if person_settings.get(context, LAST_KEY, "") == today.isoformat():
        return None
    return book.next_experiment()


def restyle(generate: Callable, reply: str, dimension: str, value: str) -> str:
    """The model's second way of saying the reply (`generate(prompt) -> text`), or "" when it fails or changes a
    fact."""
    try:
        other = (generate(restyle_prompt(reply, dimension, value)) or "").strip()
    except Exception:  # noqa: BLE001 - no second way is fine; the reply stands
        return ""
    return other if same_facts(reply, other) else ""


def _offer_id(reply: str, other: str) -> str:
    """A short id for one offer, from its two texts."""
    return hashlib.sha256((reply + "\x00" + other).encode()).hexdigest()[:10]


def keep(context, experiment: dict, reply: str, other: str, today: Optional[date] = None) -> Optional[dict]:
    """Saves the offer for its pick and returns what the screen shows: the question and the two ways in a steady order
    (by the offer's id, so the reply isn't always first), or None when there's no second way."""
    if not experiment or not other:
        return None
    today = today or date.today()
    offer_id = _offer_id(reply, other)
    ways = [{"value": experiment["a"], "label": LABELS[experiment["a"]], "text": reply},
            {"value": experiment["b"], "label": LABELS[experiment["b"]], "text": other}]
    if int(offer_id[0], 16) % 2:
        ways.reverse()
    pending = {"id": offer_id, "dimension": experiment["dimension"], "values": [experiment["a"], experiment["b"]]}
    person_settings.put(context, PENDING_KEY, pending)
    person_settings.put(context, LAST_KEY, today.isoformat())
    return {"id": offer_id, "dimension": experiment["dimension"], "name": NAMES[experiment["dimension"]],
            "question": "Two ways to say it. Which do you prefer?", "ways": ways}


def screen(context) -> dict:
    """How MIA Answers (web/answers.html): each dimension with its options, the one she leans to and how settled it is,
    the picks so far, and whether she offers two ways."""
    from core.response_style import DIMENSIONS

    book = _book(context)
    if book is None:
        return {"available": False}
    dims = []
    for dim, options in DIMENSIONS.items():
        tally = book.tally(dim)
        picks = sum(tally.values())
        sure = book.confidence(dim)
        dims.append({"id": dim, "name": NAMES[dim], "preferred": book.preferred(dim), "picks": picks,
                     "settled": round(sure, 2),
                     "word": ("Not learned yet" if not picks else "Settled" if sure >= 0.6 and picks >= 3
                              else "Leaning" if sure > 0 else "Still learning"),
                     "options": [{"value": v, "label": LABELS[v], "count": tally.get(v, 0)} for v in options]})
    return {"available": True, "dimensions": dims, "picks": len(book.picks), "compare": offers_on(context),
            "instruction": book.style_instruction() if book.picks else "",
            "next": book.next_experiment()}


# ------------------------------------------------------------------ actions

def _need_book(context):
    """The style store, or ActionError on a MIA without one."""
    book = _book(context)
    if book is None:
        raise ActionError("Answer styles aren't set up on this MIA.")
    return book


def _check(dimension: str, value: str) -> None:
    """ActionError unless the value belongs to the dimension."""
    from core.response_style import DIMENSIONS

    if dimension not in DIMENSIONS or value not in DIMENSIONS[dimension]:
        raise ActionError("That isn't one of the ways MIA can answer.")


def _describe_pick(context, params) -> str:
    """The approval sentence for `style.pick` (one of the two ways offered)."""
    _need_book(context)
    pending = person_settings.get(context, PENDING_KEY, None) or {}
    dimension, chosen = str(params.get("dimension") or pending.get("dimension") or ""), str(params.get("chosen") or "")
    _check(dimension, chosen)
    if params.get("offer_id") and pending.get("id") != params.get("offer_id"):
        raise ActionError("That choice has already been made.")
    return f"Prefer {LABELS[chosen].lower()} ({NAMES[dimension].lower()})"


def _pick(context, params) -> str:
    """Does `style.pick`: records the chosen way over the other, and clears the offer."""
    _describe_pick(context, params)
    pending = person_settings.get(context, PENDING_KEY, None) or {}
    dimension, chosen = str(params.get("dimension") or pending.get("dimension")), str(params["chosen"])
    others = [v for v in pending.get("values", []) if v != chosen] if pending.get("dimension") == dimension else []
    rejected = str(params.get("rejected") or (others[0] if others else ""))
    _need_book(context).record_pick(dimension, chosen, rejected if rejected != chosen else "")
    person_settings.put(context, PENDING_KEY, None)
    return "Noted. I'll lean that way."


def _describe_set(context, params) -> str:
    """The approval sentence for `style.set`."""
    _need_book(context)
    dimension, value = str(params.get("dimension") or ""), str(params.get("value") or "")
    _check(dimension, value)
    return f"{NAMES[dimension]}: {LABELS[value].lower()}"


def _set(context, params) -> str:
    """Does `style.set`: the dimension becomes this value at once."""
    _describe_set(context, params)
    dimension, value = str(params["dimension"]), str(params["value"])
    _need_book(context).choose(dimension, value)
    return f"{NAMES[dimension]}: {LABELS[value].lower()} from now on."


def _describe_reset(context, params) -> str:
    """The approval sentence for `style.reset`."""
    if not _need_book(context).picks:
        raise ActionError("There's nothing learned to forget yet.")
    return "Forget how you like answers (MIA goes back to her normal style)"


def _reset(context, params) -> str:
    """Does `style.reset`."""
    _need_book(context).reset()
    person_settings.put(context, PENDING_KEY, None)
    return "Forgotten. I'll answer in my normal style and learn again."


def _describe_compare(context, params) -> str:
    """The approval sentence for `style.compare`."""
    on = str(params.get("on", "true")).lower() not in ("false", "no", "0", "off")
    return "Now and then, offer an answer two ways" if on else "Stop offering answers two ways"


def _compare(context, params) -> str:
    """Does `style.compare`: offers on or off."""
    on = str(params.get("on", "true")).lower() not in ("false", "no", "0", "off")
    person_settings.put(context, COMPARE_KEY, on)
    if not on:
        person_settings.put(context, PENDING_KEY, None)
    return "I'll offer two ways now and then." if on else "I won't ask which you prefer. Say so if you want it back."


STYLE_ACTIONS = {a.kind: a for a in (
    ActionType("style.pick", "This One", {"chosen": "the way picked", "dimension": "optional: which dimension",
                                          "rejected": "optional: the other way", "offer_id": "optional: the offer"},
               _describe_pick, _pick, child_ok=True),
    ActionType("style.set", "Choose", {"dimension": "length, format, tone or lead", "value": "the way"},
               _describe_set, _set, child_ok=True),
    ActionType("style.reset", "Forget", {}, _describe_reset, _reset, child_ok=True),
    ActionType("style.compare", "Two Ways", {"on": "true or false"}, _describe_compare, _compare, child_ok=True),
)}
ACTION_TYPES.update(STYLE_ACTIONS)
