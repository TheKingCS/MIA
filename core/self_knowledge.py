"""
core.self_knowledge
=====================

What MIA can honestly say about herself — grounded in real data, never guessed. When the person asks "what are you?",
"what can you do?", "what are you working on?" or "what do you know about me?", her answer should come from the facts
(the system map, her Night School focus, the person's own stored directions and preferences), not from the model
improvising — the same "facts in code, the model only phrases" rule the rest of MIA follows, and the fix for the
self-description drift the capabilities doc warns about.

Each function returns a plain, first-person line or two MIA can speak or build on. `grounding_block()` puts them
into the system message of a how-to question about herself (`about_herself()`, core/assistant_chat.py), so her
spoken answers about herself come from these facts too. Everything is read defensively, so a
missing source is simply left out rather than crashing the answer.
"""

from __future__ import annotations

import re
import time
from typing import Optional

_ABOUT_ME_TTL = 600  # seconds: her scale doesn't change mid-conversation, and reading it takes about half a second
_about_me_cache: dict = {"at": 0.0, "text": ""}

# A question about MIA herself, not about using one of her apps: how she works, learns, remembers, is built, what
# she's working on. "How do you add a bill?" is a how-to about an app, so it's left out.
_ABOUT_HER = re.compile(
    r"\b(?:how (?:do|does|did|can|will) (?:you|mia) (?:work|learn|think|remember|improve|grow|know|decide|get better)"
    r"|what (?:are|is) (?:you|mia) (?:working on|learning|studying|focused on|made of|built (?:on|from|with))"
    r"|how (?:are|is) (?:you|mia) (?:built|made|trained|learning|improving)"
    r"|(?:your|mia's) (?:memory|brain|model|training|focus|night school|loops|code|architecture|own code)"
    r"|(?:do|can|does) (?:you|mia) (?:learn|remember|think|improve|grow|train|get smarter))\b",
    re.IGNORECASE)


def _safe(fn, default=""):
    """Run a reader; on any failure return the default so a self-answer never crashes."""
    try:
        return fn()
    except Exception:  # noqa: BLE001 - a missing source is a quiet gap, not an error
        return default


def about_me() -> str:
    """A grounded, first-person description of what MIA is — the real scale, from the system map (DEC-0139)."""
    from core import system_map

    d = system_map.assemble()
    arch = d.get("architecture", {})
    files = sum(arch.values()) if arch else 0
    tools = d.get("capabilities", {}).get("tools")
    loops = d.get("loops", {}).get("active")
    decisions = len(d.get("decisions", []))
    sealed = d.get("stores", {}).get("sealed")
    parts = ["I'm MIA — a local-first personal assistant that runs on your own devices, so what I keep about you stays "
             "with you."]
    if files:
        detail = f"Under the hood I'm about {files} files of code"
        if tools:
            detail += f", roughly {tools} tools"
        if loops:
            detail += f", and {loops} improvement loops that watch how I work and push me to get better"
        parts.append(detail + ".")
    if decisions:
        parts.append(f"There are {decisions} decisions on record for why I'm built the way I am"
                     + (f", and {sealed} of the things I keep about you are encrypted on disk" if sealed else "") + ".")
    return " ".join(parts)


def my_focus() -> str:
    """What MIA is working on right now — her Night School directive (DEC-0100), or her build plan."""
    from core import night_school

    directive = _safe(lambda: night_school.settings().get("directive"), "")
    if directive:
        return "What I'm working on right now, every night: " + directive
    return "Right now I work through my build plan step by step each night, with a teacher setting my exercises."


def what_i_know_about_you(context) -> str:
    """A grounded sketch of what MIA understands about the person — from their stored directions, memories and the
    answer-style she's learned. Honest about how much (or little) she knows."""
    bits = []
    book = getattr(context, "direction", None)
    live = _safe(lambda: book.active(), []) if book is not None else []
    if live:
        bits.append("You're steering your life by: " + "; ".join(d.title for d in live) + ".")
    memories = getattr(context, "user_memories", None)
    count = _safe(lambda: len(memories.all_memories()), 0) if memories is not None else 0
    if count:
        bits.append(f"I'm holding {count} thing{'s' if count != 1 else ''} I remember about you.")
    style = getattr(context, "response_style", None)
    if style is not None and _safe(lambda: bool(style.picks), False):
        bits.append("And I'm learning how you like me to answer.")
    return " ".join(bits) or "Honestly, I'm still getting to know you — tell me what matters, and I'll remember."


def self_summary(context) -> str:
    """The three together: what she is, what she's working on, and what she knows about the person."""
    return "\n\n".join([about_me(), my_focus(), what_i_know_about_you(context)])


def about_herself(prompt: str) -> bool:
    """Pure logic. Whether a question is about MIA herself (how she works, learns, remembers, is built, what she's
    working on), as opposed to how to use one of her apps."""
    return bool(_ABOUT_HER.search(prompt or ""))


def _about_me_kept() -> str:
    """`about_me()` kept for _ABOUT_ME_TTL, for answers inside a turn (reading it takes about half a second); a
    failure isn't kept, so the next question tries again. The About page reads `about_me()` live."""
    if _about_me_cache["text"] and time.monotonic() - _about_me_cache["at"] < _ABOUT_ME_TTL:
        return _about_me_cache["text"]
    text = _safe(about_me)
    if text:
        _about_me_cache.update(at=time.monotonic(), text=text)
    return text


def grounding_block(context) -> str:
    """Her own facts for a how-to question about herself (DEC-0142), so the answer comes from the records rather than
    the model improvising about itself: what she is, what she's working on, and what she knows about the person. ""
    when nothing can be read."""
    facts = [x for x in (_about_me_kept(), _safe(my_focus), _safe(lambda: what_i_know_about_you(context))) if x]
    if not facts:
        return ""
    return ("What's true about you, from your own records. Answer about yourself from these, never from a guess:\n"
            + "\n".join(f"- {x}" for x in facts))
