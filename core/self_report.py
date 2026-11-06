"""
core.self_report
==================

MIA's weekly self-report (build plan step 6, DEC-0094): once a week, to the
PC's owner, through the communication gate: what got better, what's
slipping, what she's working on, and how Night School went. Assembled in
code from her own records (the loops' history, Night School, the
benchmarks, the task queue); nothing in it is a model's guess.

Only on the PC with the development platform, only to the device's owner
(the first profile made on it), and only numbers and names of her own
loops and tasks: never anything from a person's records.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

TOPIC = "self_report"
DAY = 6  # Sunday (Monday is 0)


def _ago(days: int, now: Optional[datetime] = None) -> str:
    return ((now or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat(timespec="seconds")


def changes(history: dict[str, list[dict]], since: str) -> tuple[list[str], list[str]]:
    """Pure logic. Loops that recovered (below or sliding, now ok) and that fell (ok, now below or sliding)."""
    better, worse = [], []
    for loop_id, rows in history.items():
        judged = [r for r in rows if r.get("state") in ("ok", "below", "slid")]
        if not judged:
            continue
        before = [r for r in judged if r.get("at", "") < since]
        start, end = (before[-1] if before else None), judged[-1]
        if start is None:
            continue
        bad = ("below", "slid")
        if start["state"] in bad and end["state"] == "ok":
            better.append(loop_id)
        elif start["state"] == "ok" and end["state"] in bad:
            worse.append(loop_id)
    return sorted(better), sorted(worse)


def report(now: Optional[datetime] = None) -> Optional[str]:
    """This week, in a few plain lines. None when there's nothing to say."""
    from core import loops, night_school, work_tasks

    since = _ago(7, now)
    better, worse = changes(loops.history(None, "device"), since)
    tasks = work_tasks.load()
    mine = [t for t in tasks.values() if t.source.startswith(("loop:", "night:"))]
    done = [t for t in mine if t.status == "done" and t.updated >= since[:10]]
    working = [t for t in mine if t.status not in work_tasks.FINISHED]
    week = night_school.nights(7)
    lessons = [l for n in week for l in n.get("lessons", []) if l.get("outcome") in ("pass", "fail")]
    passed = sum(1 for l in lessons if l["outcome"] == "pass")
    lines = []
    if better:
        lines.append("Better: " + ", ".join(better) + ".")
    if worse:
        lines.append("Slipping: " + ", ".join(worse) + ".")
    if done:
        lines.append(f"Fixed {len(done)}: " + "; ".join(t.title for t in done[:3]) + ("..." if len(done) > 3 else "") + ".")
    if working:
        lines.append(f"Working on {len(working)}: " + "; ".join(f"{t.id} {t.title}" for t in working[:3])
                     + ("..." if len(working) > 3 else "") + ".")
    try:
        from core import chronicle_issue

        waiting = [i for i in chronicle_issue.issues() if i["status"] != "approved"]
    except (OSError, ValueError):
        waiting = []
    if waiting:
        lines.append(f"The Chronicles: issue #{waiting[-1]['number']:03d} waits for you "
                     f"(python -m tools.chronicle_issue show {waiting[-1]['id']}).")
    if week:
        lines.append(f"Night School: {len(week)} night{'s' if len(week) != 1 else ''}, {passed} of {len(lessons)} lessons passed.")
    return " ".join(lines) if lines else None


def _owner(context) -> Optional[str]:
    profiles = getattr(context, "profiles", None)
    listed = profiles.list_profiles() if profiles is not None else []
    return sorted(listed, key=lambda p: p.created_at or "")[0].profile_id if listed else None


def offer(context, now: Optional[datetime] = None) -> list:
    """On Sundays, for the PC's owner: the week's report as one Candidate for the gate."""
    from core import loops
    from core.communication_gate import Candidate
    from core.person_settings import person_id

    now = now or datetime.now()
    if now.weekday() != DAY or not loops._has_repo():
        return []
    if person_id(context) != _owner(context):
        return []
    said = report()
    if not said:
        return []
    week = now.date().isoformat()
    return [Candidate(topic=TOPIC, title="My week", message=said, source="loops", fingerprint=f"{TOPIC}:{week}")]
