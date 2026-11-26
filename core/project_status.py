"""
core.project_status
=====================

"How's the shed coming along?" (brainstorm round 19, 2026-11-26: the live check had "I'm not aware of any information
about a garage rewire" with the Garage Rewire in his projects): one project's picture from his own records, in code.
Its status and due date (days left, or how far past), its tasks (how many done, the next open one), the hours he's
logged on it (core/project_time) and when last, and what it still needs (core/assistant_requirement_actions). Read
only; each part that can't be read is left out.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def say(context, project, today: Optional[date] = None) -> str:
    """One project's picture in a few sentences: status and due date, tasks, hours, needs."""
    from core import project_time

    today = today or date.today()
    parts = [f"{project.name} is {str(project.status or 'in progress').lower()}"]
    due = _day(project.due_date)
    if due and str(project.status or "").lower() not in ("done", "complete", "completed"):
        days = (due - today).days
        parts[0] += (f", due {due:%B} {due.day} ({days} day{'s' if days != 1 else ''} left)" if days > 0 else
                     ", due today" if days == 0 else
                     f", {-days} day{'s' if days != -1 else ''} past its due date ({due:%B} {due.day})")
    parts[0] += "."
    tasks_book = getattr(context, "tasks", None)
    try:
        tasks = tasks_book.tasks_for_project(project.project_id) if tasks_book is not None else []
    except Exception:  # noqa: BLE001
        tasks = []
    if tasks:
        done = sum(1 for t in tasks if t.done)
        open_ = [t for t in tasks if not t.done]
        line = f"Tasks: {done} of {len(tasks)} done"
        if open_:
            first = sorted(open_, key=lambda t: (not t.due_date, t.due_date or ""))[0]
            line += f"; next up, {first.title}"
        parts.append(line + ".")
    hours = project_time.total(project)
    if hours:
        last = max((str(e.get("date") or "") for e in (project.time_log or []) if isinstance(e, dict)), default="")
        on = _day(last)
        parts.append(f"You've put {hours:g} hours into it" + (f", last on {on:%B} {on.day}" if on else "") + ".")
    else:
        parts.append("No hours logged on it yet.")
    try:
        from core.assistant_requirement_actions import needs_sentence

        if getattr(context, "requirements", None) is not None:
            needs = needs_sentence(context, project.name)
            if "still needs" in needs:
                parts.append(needs)
    except Exception:  # noqa: BLE001
        pass
    return " ".join(parts)


def _day(text: str) -> Optional[date]:
    """Pure logic. An ISO date, or None."""
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None
