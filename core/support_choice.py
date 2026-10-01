"""
core.support_choice
======================

"When it's ambiguous, MIA asks instead of guessing" (2026-09-28), the
part of slice B that was deferred (docs/COGNITIVE_EXTENSION_PROPOSAL.md,
sections 8 and 9).

When the owner says something heavy ("rough day", "I'm so tired of
this", "work sucks") without asking for a kind of support, MIA asks one
question before answering: just listen, help figure it out, or remember
why. Short answers work ("listen", "the second one", "just talk"), and
the ordinary mode phrases do too. She remembers the choices; after the
same one three times running she stops asking, uses it, and says so.

Pure logic here; core/talk_it_out.pre_turn() wires it in (so every chat
surface and the phone behave the same), after the safety floor, which
always comes first. At most one question per conversation every
`ASK_EVERY` hours; `assistant.ask_support_kind` turns it off. Both it and
the remembered choices are each person's own (core/person_settings.py).
"""

from __future__ import annotations

import re
from typing import Optional

from core import person_settings
from core.conversation_modes import COMPANION, LISTEN, PERSPECTIVE, PLAN

ASK_EVERY_HOURS = 3
HABIT_COUNT = 3
_MAX_REMEMBERED = 6

QUESTION = ("That sounds like a lot. Do you want me to just listen, help you figure out what to do, "
            "or remind you why you're doing all this?")

HABIT_NOTICE = {
    LISTEN: "I'm listening. (Say \"help me figure it out\" if you want more than that.)",
    PLAN: "Okay, let's make it smaller. (Say \"just listen\" if you'd rather vent.)",
    PERSPECTIVE: "Let's zoom out for a second. (Say \"just listen\" if you'd rather vent.)",
}

_HEAVY = re.compile(
    r"\b(?:(?:rough|terrible|awful|horrible|bad|long|shitty|crappy|hard) (?:day|night|week|shift)|"
    r"(?:so |really |just )?(?:exhausted|drained|burn(?:ed|t) out|worn out|fed up|stressed(?: out)?|frustrated|"
    r"miserable|defeated|discouraged)|"
    r"(?:sick|tired) of (?:this|it|everything|work|my job|doing)|hate (?:my job|this job|work|this)|"
    r"(?:work|today|everything|this) sucks|falling apart|can'?t (?:do this|take (?:it|this))|"
    r"want to quit|same thing every (?:single )?day|what a day)\b",
    re.IGNORECASE,
)
_QUESTION_WORDS = re.compile(r"^\s*(?:what|how|when|where|who|which|can you|could you|should i|do i|is|are|will)\b", re.IGNORECASE)

_ANSWERS = (
    (LISTEN, re.compile(r"\b(?:listen|listening|vent|venting|hear me|the first(?: one)?|first one)\b")),
    (PLAN, re.compile(r"\b(?:figure|plan|help|fix|advice|next step|the second(?: one)?|second one)\b")),
    (PERSPECTIVE, re.compile(r"\b(?:why|remind|perspective|zoom out|the (?:third|last)(?: one)?|third one|last one)\b")),
    (COMPANION, re.compile(r"\b(?:just talk|neither|none|nah|no thanks|normal|whatever|nothing)\b")),
)


def sounds_heavy(text: str) -> bool:
    """Pure logic. Strain without a request for anything specific."""
    lowered = text.lower().replace("’", "'")
    if "?" in lowered and _QUESTION_WORDS.search(lowered):
        return False  # a question gets answered, not a menu
    return bool(_HEAVY.search(lowered))


def interpret_answer(text: str) -> Optional[str]:
    """Pure logic. Which choice a short answer picked, or None."""
    lowered = text.lower().replace("’", "'").strip()
    if len(lowered.split()) > 12:
        return None  # a long reply is them talking, not choosing
    for mode, pattern in _ANSWERS:
        if pattern.search(lowered):
            return mode
    return None


def habit(choices: list[str]) -> Optional[str]:
    """Pure logic. The owner's usual choice: the same one HABIT_COUNT times running."""
    recent = choices[-HABIT_COUNT:]
    if len(recent) == HABIT_COUNT and len(set(recent)) == 1 and recent[0] in HABIT_NOTICE:
        return recent[0]
    return None


def remember(context, mode: str) -> None:
    """Each person's own choices (core/person_settings.py)."""
    choices = remembered(context)
    person_settings.put(context, "assistant.support_choices", (choices + [mode])[-_MAX_REMEMBERED:])


def remembered(context) -> list[str]:
    if context is None or getattr(context, "config", None) is None:
        return []
    return list(person_settings.get(context, "assistant.support_choices", []) or [])
