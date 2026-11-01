"""
core.first_boot
=================

The first time a person meets MIA (slice 2 of
docs/GLASSES_FIRST_BOOT_PLAN.md, Zac's brief of 2026-10-29): she doesn't
launch, she awakens. This keeps how far each person has got, so the
sequence can be left and picked up again on any device, and writes the
words she says, so a screen only plays them (DEC-0013).

- `state(context)`: {"done", "phase", "phases": [...], "beats": [...]}:
  what's left, one beat per look. Served as `/api/first-boot`.
- `firstboot.advance` / `firstboot.skip` (core/actions.py's contract):
  a phase finished; the rest skipped. The screen proposes and approves
  them itself as they happen: the person is watching it. Skipped phases
  are remembered, so they can come back later.

Each person's own, on their profile (core/person_settings.py). Phases
run in PHASES order; a phase left halfway starts again from its first
beat. Later slices add User Sync and the tutorial to PHASES; someone
who finished before then is asked about those separately.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core import person_settings
from core.actions import ACTION_TYPES, ActionError, ActionType, _need

KEY = "first_boot.progress"

# id -> what the beat looks like, what she says (with {name}), how long at least (seconds).
PHASES = {
    "awakening": [
        {"look": "swarm", "say": "A new connection is forming…", "seconds": 7},
        {"look": "flare", "say": "", "seconds": 5},
    ],
    "connecting": [
        {"look": "core", "say": "", "seconds": 6},
    ],
    "introduction": [
        {"look": "voice", "say": "Hello, {name}.", "seconds": 4, "speak": True},
        {"look": "voice", "say": "I'm MIA, your Multifunctional Intelligent Assistant.", "seconds": 6, "speak": True},
        {"look": "voice", "say": "I'm here to help you organize your life, reach your goals, and make the most of every day.",
         "seconds": 9, "speak": True},
        {"look": "voice", "say": "Whenever you want me, just tap and talk.", "seconds": 6, "speak": True},
    ],
}


def _progress(context) -> dict:
    saved = person_settings.get(context, KEY) or {}
    return saved if isinstance(saved, dict) else {}


def _first_name(context) -> str:
    who = person_settings.person_id(context)
    profiles = getattr(context, "profiles", None)
    found = next((p for p in profiles.list_profiles() if p.profile_id == who), None) if profiles is not None else None
    name = str(getattr(found, "name", "") or "").strip()
    return name.split()[0] if name else ""


def _beats(context, phase: str) -> list[dict]:
    name = _first_name(context)
    out = []
    for beat in PHASES[phase]:
        say = beat["say"].format(name=name) if name else beat["say"].replace(", {name}", "")
        out.append({**beat, "say": say, "phase": phase})
    return out


def state(context) -> dict:
    """What's left of the first boot for this person."""
    progress = _progress(context)
    finished = [p for p in PHASES if p in (progress.get("phases") or [])]
    left = [p for p in PHASES if p not in finished]
    done = bool(progress.get("finished_at")) or not left
    if done:
        left = []
    return {"done": done, "phase": left[0] if left else None, "phases": list(PHASES), "finished": finished,
            "skipped": list(progress.get("skipped") or []),
            "beats": [b for p in left for b in _beats(context, p)]}


def _finish(context, progress: dict, skipped: bool) -> None:
    from core import life_events

    progress["finished_at"] = datetime.now().isoformat(timespec="seconds")
    person_settings.put(context, KEY, progress)
    life_events.record(getattr(context, "personal_life_events", None) or getattr(context, "life_events", None), "first_boot_finished",
                       "Skipped the rest of meeting MIA" if skipped else "Met MIA for the first time",
                       payload={"skipped": list(progress.get("skipped") or [])},
                       profile_id=person_settings.person_id(context))


def advance(context, phase: str) -> dict:
    """A phase finished. Repeating one changes nothing."""
    if phase not in PHASES:
        raise ActionError("There's no such part of the first boot.")
    progress = _progress(context)
    done = list(progress.get("phases") or [])
    if phase not in done and not progress.get("finished_at"):
        progress["phases"] = done + [phase]
        if all(p in progress["phases"] for p in PHASES):
            _finish(context, progress, skipped=False)
        else:
            person_settings.put(context, KEY, progress)
    return state(context)


def skip(context) -> dict:
    """Skip what's left; it's remembered, so it can come back."""
    progress = _progress(context)
    if not progress.get("finished_at"):
        done = progress.get("phases") or []
        progress["skipped"] = [p for p in PHASES if p not in done]
        _finish(context, progress, skipped=True)
    return state(context)


# ------------------------------------------------------------------ the action contract


def _describe_advance(context, params) -> str:
    return f"Finish this part of meeting MIA ({str(params.get('phase') or '').strip()})"


def _do_advance(context, params) -> str:
    _need(context, "config")
    advance(context, str(params.get("phase") or "").strip())
    return "Noted."


def _describe_skip(context, params) -> str:
    return "Skip the rest of meeting MIA"


def _do_skip(context, params) -> str:
    _need(context, "config")
    skip(context)
    return "Skipped. You can come back to it any time."


ACTION_TYPES["firstboot.advance"] = ActionType(
    "firstboot.advance", "Continue", {"phase": "the part just finished"}, _describe_advance, _do_advance, child_ok=True)
ACTION_TYPES["firstboot.skip"] = ActionType(
    "firstboot.skip", "Skip", {}, _describe_skip, _do_skip, child_ok=True)


def summary(context) -> Optional[dict]:
    """For Life State: how far this person has got."""
    now = state(context)
    return {"done": now["done"], "phase": now["phase"], "finished": now["finished"], "skipped": now["skipped"]}
