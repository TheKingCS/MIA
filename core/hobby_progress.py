"""
core.hobby_progress
=====================

His hobbies' progress in one answer (brainstorm round 16, 2026-11-25): this month so far, across everything he does
for himself: each learning path's practice (core/paths: minutes, days and the stage he's on), the fish he caught
and his best (core/catch_log), his workouts (the workout store) and the hours on his projects
(core/project_time). Counted in code from his own records; read only.

How: `month(context, today)` gathers {paths, catches, best, workouts, projects}; `say(context, today)` words it in a
line or two. "How are my hobbies going?" and "my hobbies this month" reach `say` in code (core/assistant_turn's
`_own_tool_reply`). One course's detail stays the learning_progress tool's (core/assistant_path_actions).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

SHOWN = 3


def _hours(minutes: float) -> str:
    """Minutes said plainly: "40 minutes", "2 hours", "3 hours 20 minutes"."""
    minutes = int(round(minutes))
    h, m = divmod(minutes, 60)
    if not h:
        return f"{m} minute{'s' if m != 1 else ''}"
    said = f"{h} hour{'s' if h != 1 else ''}"
    return said + (f" {m} minute{'s' if m != 1 else ''}" if m else "")


def month(context, today: Optional[date] = None) -> dict:
    """This month so far: {paths: [{name, minutes, days, stage, stages}], catches: n, best: catch or None,
    workouts: n or None (no store), projects: [(name, hours)]}; a store that can't be read gives nothing for its
    part."""
    today = today or date.today()
    first = today.replace(day=1)
    since = first.isoformat()
    out = {"paths": [], "catches": 0, "best": None, "workouts": None, "projects": []}
    book = getattr(context, "paths", None)
    if book is not None:
        try:
            from core import paths

            for path_id in book.started():
                program = paths.program_of(context, path_id)
                record = book.path(path_id) or {}
                sessions = [s for s in record.get("sessions", []) if since <= str(s.get("date", "")) <= today.isoformat()]
                if program is None or not sessions:
                    continue
                stage = paths.stage_of(book, program)
                out["paths"].append({"name": program.name, "minutes": sum(float(s.get("minutes") or 0) for s in sessions),
                                     "days": len({s["date"] for s in sessions}), "stage": stage.number,
                                     "stages": len(program.stages)})
        except Exception:  # noqa: BLE001 - one part that can't be read never takes the rest
            log.exception("Hobbies' progress: the learning paths couldn't be read")
    try:
        from core import catch_log

        caught = [c for c in catch_log.catches(context) if str(c.get("at") or "")[:10] >= since]
        out["catches"] = len(caught)
        sized = [c for c in caught if c.get("length") or c.get("weight")]
        out["best"] = max(sized, key=catch_log._size) if sized else None
    except Exception:  # noqa: BLE001
        log.exception("Hobbies' progress: the catches couldn't be read")
    try:
        from core.paths import _workouts

        done = _workouts(context, since)
        out["workouts"] = None if done is None else len(done)
    except Exception:  # noqa: BLE001
        log.exception("Hobbies' progress: the workouts couldn't be read")
    try:
        from core import project_time

        out["projects"] = [(p.name, h) for p, h in project_time.totals(context, first, today)]
    except Exception:  # noqa: BLE001
        log.exception("Hobbies' progress: the project hours couldn't be read")
    return out


def say(context, today: Optional[date] = None) -> str:
    """For "how are my hobbies going?": this month so far in a line or two, or how to start it counting."""
    from core.catch_log import _measure

    f = month(context, today)
    parts = []
    for p in sorted(f["paths"], key=lambda p: -p["minutes"])[:SHOWN]:
        parts.append(f"{p['name']}: {_hours(p['minutes'])} over {p['days']} day{'s' if p['days'] != 1 else ''}, "
                     f"stage {p['stage']} of {p['stages']}")
    if f["catches"]:
        best = f["best"]
        parts.append(f"{f['catches']} fish caught" + (f", the best a {(best.get('species') or 'fish').lower()} "
                                                       f"({_measure(best)})" if best else ""))
    if f["workouts"]:
        parts.append(f"{f['workouts']} workout{'s' if f['workouts'] != 1 else ''}")
    for name, hours in f["projects"][:SHOWN]:
        parts.append(f"{hours:g} hour{'s' if hours != 1 else ''} on {name}")
    if not parts:
        return ("Nothing logged for your hobbies this month yet. Log practice on a course, a catch, a workout or "
                "hours on a project, and I'll keep the month's count.")
    return "This month so far: " + "; ".join(parts) + "."
