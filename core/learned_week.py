"""
core.learned_week
===================

What she learned this week (brainstorm round 16, 2026-11-25): so he sees her getting better, the week in plain
words from her own records: what she kept about him (core/user_memory_manager), the skills he taught her
(core/taught_skills), and how often he had to fix what she did, area by area (core/corrections: the changes she made
and the ones he corrected), with the memories he corrected soon after she kept them. Counted in code; nothing is a
model's guess.

How: `facts(context, now)` gathers the counts (read only); `say(context, now)` words them. "What did you learn this
week?" reaches `say` in code (core/assistant_turn's `_own_tool_reply`), and the Sunday self-report ends with
`counts` (core/self_report.report): numbers only, never a memory's words, as that report keeps to.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DAYS = 7
SHOWN = 3


def _short(text: str, limit: int = 60) -> str:
    """A memory's text cut to a few words for a line."""
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def facts(context, now: Optional[datetime] = None) -> dict:
    """{memories: [texts kept this week], skills: [names taught this week], areas: {area: {changes, corrected}},
    memories_fixed: count}; a store that's missing or can't be read gives nothing for its part."""
    now = now or datetime.now()
    since = (now - timedelta(days=DAYS)).isoformat(timespec="seconds")
    out = {"memories": [], "skills": [], "areas": {}, "memories_fixed": 0}
    store = getattr(context, "user_memories", None)
    if store is not None:
        try:
            out["memories"] = [m.text for m in store.all_memories() if (m.created_at or "") >= since]
            out["memories_fixed"] = len(store.corrections(DAYS))
        except Exception:  # noqa: BLE001 - one part that can't be read never takes the rest
            log.exception("What she learned: the memories couldn't be read")
    book = getattr(context, "taught_skills", None)
    if book is not None:
        try:
            out["skills"] = [s.name for s in getattr(book, "skills", []) if (s.created_at or "") >= since]
        except Exception:  # noqa: BLE001
            log.exception("What she learned: the taught skills couldn't be read")
    try:
        from core import corrections

        out["areas"] = {a: r for a, r in corrections.summary(context, DAYS, now).items() if r.get("changes")}
    except Exception:  # noqa: BLE001
        log.exception("What she learned: the corrections couldn't be read")
    return out


def line(context, now: Optional[datetime] = None) -> str:
    """The week's learning in a line or two; "" with nothing to say."""
    f = facts(context, now)
    parts = []
    if f["memories"]:
        n = len(f["memories"])
        shown = "; ".join(_short(t) for t in f["memories"][:SHOWN]) + ("; and more" if n > SHOWN else "")
        parts.append(f"I kept {n} thing{'s' if n != 1 else ''} about you: {shown}.")
    if f["skills"]:
        parts.append("You taught me " + ", ".join(f["skills"][:SHOWN])
                     + (f" and {len(f['skills']) - SHOWN} more" if len(f["skills"]) > SHOWN else "") + ".")
    areas = f["areas"]
    if areas:
        made = sum(r["changes"] for r in areas.values())
        fixed = sorted(((a, r["corrected"]) for a, r in areas.items() if r.get("corrected")), key=lambda x: -x[1])
        if fixed:
            where = ", ".join(f"{n} in {a}" for a, n in fixed[:SHOWN])
            total = sum(n for _a, n in fixed)
            parts.append(f"You corrected {total} of the {made} changes I made ({where}).")
        else:
            parts.append(f"You didn't have to correct any of the {made} changes I made.")
    if f["memories_fixed"]:
        n = f["memories_fixed"]
        parts.append(f"You fixed {n} thing{'s' if n != 1 else ''} I'd remembered wrong.")
    return " ".join(parts)


def counts(context, now: Optional[datetime] = None) -> str:
    """The week's learning as numbers only, for the self-report ("From you this week: 3 memories kept, 1 skill taught,
    2 of my 14 changes corrected."); "" with nothing to count."""
    f = facts(context, now)
    made = sum(r["changes"] for r in f["areas"].values())
    fixed = sum(r.get("corrected", 0) for r in f["areas"].values())
    bits = []
    if f["memories"]:
        bits.append(f"{len(f['memories'])} memor{'ies' if len(f['memories']) != 1 else 'y'} kept")
    if f["skills"]:
        bits.append(f"{len(f['skills'])} skill{'s' if len(f['skills']) != 1 else ''} taught")
    if made:
        bits.append(f"{fixed} of my {made} changes corrected")
    return ("From you this week: " + ", ".join(bits) + ".") if bits else ""


def say(context, now: Optional[datetime] = None) -> str:
    """For "what did you learn this week?": the line, or that the week was quiet."""
    return line(context, now) or ("A quiet week: I didn't keep anything new about you, you didn't teach me a skill, "
                                  "and I made no changes for you to check.")
