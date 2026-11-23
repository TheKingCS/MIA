"""
core.left_off
===============

Where he left off (Jarvis brainstorm 1.2; Zac, 2026-11-23: "smooth conversation ... aware"): "where were we?" or
"what was I working on?" answered from what his records hold, never from the model's guess, so a conversation picks
up where the last one stopped, on any device.

- **Missions in motion** (`missions_in_motion`): active missions changed in the last LOOKBACK_DAYS days, newest first,
  each with its next objective not yet done (core/mission_manager.py's own `is_objective_complete`).
- **Plans not confirmed** (`drafts`): Planner drafts (core/project_plans.py) worked on in that time and not yet
  confirmed or dropped: "the coop floor plan is still a draft".
- **Promises open** and **decisions lately** (core/life_notes.py): what he said he'd do, still open, and what he
  decided in that time (only notes he chose to keep).

`gather(context, now)` puts them together (each source that can't be read left out); `describe` says them, at most
SHOWN of each; "" when there's nothing, so "catch me up" (core/needs_now.py) can add it without a word on a clean
slate.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

LOOKBACK_DAYS = 14
SHOWN = 3


def _recent(stamp: str, since: datetime) -> bool:
    """Pure logic. Whether an ISO time is at or after `since` (a blank or bad one isn't)."""
    try:
        return datetime.fromisoformat(str(stamp)[:19]) >= since
    except ValueError:
        return False


def missions_in_motion(context, since: datetime) -> list[dict]:
    """Active missions changed since then, newest first: each {name, next, steps} (next "" when every objective is
    done, or there are none)."""
    manager = getattr(context, "missions", None)
    if manager is None:
        return []
    out = []
    for m in manager.all_missions():
        if m.status != "active" or not _recent(m.updated_at or m.created_at, since):
            continue
        nxt = ""
        for i, objective in enumerate(m.objectives):
            if not manager.is_objective_complete(m.mission_id, i):
                nxt = objective.description
                break
        out.append({"name": m.name, "next": nxt, "steps": len(m.objectives), "at": m.updated_at or m.created_at})
    return sorted(out, key=lambda x: x["at"], reverse=True)


def drafts(context, since: datetime) -> list[str]:
    """The Planner's drafts worked on since then and not confirmed, newest first, by title."""
    book = getattr(context, "project_plans", None)
    if book is None:
        return []
    return [p.title for p in book.listed() if p.status == "draft" and _recent(p.updated_at, since)]


def notes(context, since: datetime) -> dict:
    """{"promises": [open promises], "decisions": [decisions kept since then]}, newest first, each said in a line."""
    store = getattr(context, "life_notes", None)
    if store is None:
        return {"promises": [], "decisions": []}
    newest = lambda notes: sorted(notes, key=lambda n: n.get("at", ""), reverse=True)  # noqa: E731
    return {"promises": [_promise(n) for n in newest(store.of_kind("commitment", open_only=True))],
            "decisions": [_decision(n) for n in newest(store.of_kind("decision"))
                          if _recent(n.get("at", ""), since)]}


def _promise(note: dict) -> str:
    """Pure logic. An open promise in a line, without a label: "fix the gate, for Sam, by Saturday"."""
    return note.get("what", "") + (f", for {note['who']}" if note.get("who") else "") + \
        (f", by {note['by']}" if note.get("by") else "")


def _decision(note: dict) -> str:
    """Pure logic. A decision in a line, without a label: "2x8 joists, because the span is 12 feet"."""
    return note.get("what", "") + (f", because {note['why']}" if note.get("why") else "")


def gather(context, now: Optional[datetime] = None) -> dict:
    """{"missions", "drafts", "promises", "decisions"}: each source that can't be read left empty."""
    now = now or datetime.now()
    since = now - timedelta(days=LOOKBACK_DAYS)
    out = {"missions": [], "drafts": [], "promises": [], "decisions": []}
    for read in (lambda: {"missions": missions_in_motion(context, since)}, lambda: {"drafts": drafts(context, since)},
                 lambda: notes(context, since)):
        try:
            out.update(read())
        except Exception:  # noqa: BLE001 - one record that can't be read never stops the rest
            log.exception("Left off: a source couldn't be read")
    return out


def describe(found: dict) -> str:
    """Pure logic. Where he left off in words ("" with nothing to pick up): each mission with its next step (or
    ready to finish when every step of one that has steps is done), drafts, then promises and decisions, newest
    first, each without its label said twice."""
    parts = []
    missions = found.get("missions") or []
    if missions:
        lines = [m["name"] + (f" (next: {m['next']})" if m["next"] else
                              " (every step done: ready to finish)" if m.get("steps") else "")
                 for m in missions[:SHOWN]]
        parts.append("Lately you've been on " + "; ".join(lines) + ".")
    plans = found.get("drafts") or []
    if plans:
        parts.append("Still a draft in the Planner: " + ", ".join(plans[:SHOWN]) + ". Confirm it when it's right and "
                     "I'll make the missions.")
    promises = found.get("promises") or []
    if promises:
        parts.append("Open promises: " + "; ".join(promises[:SHOWN]) + ".")
    decisions = found.get("decisions") or []
    if decisions:
        parts.append("You decided lately: " + "; ".join(decisions[:SHOWN]) + ".")
    return " ".join(parts)


def say(context) -> str:
    """For "where were we?": where he left off, or that the slate is clean."""
    said = describe(gather(context))
    return said or ("Nothing's mid-way that I can see: no mission touched in the last two weeks, no plan waiting to be "
                    "confirmed, and no open promises.")
