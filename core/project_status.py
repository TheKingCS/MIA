"""
core.project_status
=====================

"How's the shed coming along?" (brainstorm round 19, 2026-11-26: the live check had "I'm not aware of any information
about a garage rewire" with the Garage Rewire in his projects): one project's picture from his own records, in code.
Its status and due date (days left, or how far past), its tasks (how many done, the next open one), the hours he's
logged on it (core/project_time) and when last, the money spent on it (core/homestead_costs, its tagged expenses
against its budget), and what it still needs (its own requirements). Read only; each part that can't be read is
left out.

`whole_cost(context, project)` is "what has the shed cost me?" (brainstorm round 19, a job's whole cost): the money
spent on it, and his hours on it, valued at his shop's labor rate (`workshop.labor_rate_per_hour`) when he set one.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def say(context, project, today: Optional[date] = None) -> str:
    """One project's picture in a few sentences: status and due date, tasks (the next one only while it isn't done),
    hours, the money spent on it once there is any, its own needs (by its id)."""
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
        if open_ and str(project.status or "").lower() not in ("done", "complete", "completed"):
            first = sorted(open_, key=lambda t: (not t.due_date, t.due_date or ""))[0]
            line += f"; next up, {first.title}"
        parts.append(line + ".")
    hours = project_time.total(project)
    if hours:
        last = max((str(e.get("date") or "") for e in (project.time_log or []) if isinstance(e, dict)), default="")
        on = _day(last)
        parts.append(f"You've put {hours:g} hour{'s' if hours != 1 else ''} into it" + (f", last on {on:%B} {on.day}" if on else "") + ".")
    else:
        parts.append("No hours logged on it yet.")
    try:  # the money on it (core/homestead_costs), only once something's been spent
        spent = _spent_line(context, project)
        if spent:
            parts.append(spent)
    except Exception:  # noqa: BLE001
        pass
    try:  # its own needs, by its id (never another project's whose name holds this one's)
        book = getattr(context, "requirements", None)
        lines = [r for r in (book.for_project(project.project_id) if book is not None else [])
                 if r.status in ("needed", "partial", "found")]
        if lines:
            said = [f"{r.quantity - r.have:g} {r.unit + ' ' if r.unit else ''}{r.item}"
                    + (" (some on hand)" if r.status == "partial" else "") for r in lines[:6]]
            more = f", and {len(lines) - 6} more" if len(lines) > 6 else ""
            parts.append(f"It still needs {', '.join(said)}{more}.")
    except Exception:  # noqa: BLE001
        pass
    return " ".join(parts)


def _spent_line(context, project) -> str:
    """The money spent on it in one sentence (core/homestead_costs.describe_build), or "" when nothing is."""
    if getattr(context, "budget", None) is None:
        return ""
    from core.homestead_costs import build_cost, describe_build

    cost = build_cost(context, project)
    return describe_build(cost) if cost.expense_count else ""


def whole_cost(context, project) -> str:
    """"What has the shed cost me?": the money spent on it (its tagged expenses, against its budget), then his hours on
    it, and those hours at his shop's labor rate when he set one (said as what his time is worth, never added to
    money spent); without the budget on this MIA, said as that."""
    from core import project_time
    from core.region import money

    parts = []
    if getattr(context, "budget", None) is not None:
        from core.homestead_costs import build_cost, describe_build

        parts.append(describe_build(build_cost(context, project)))
    else:
        parts.append(f"Money isn't kept on this MIA, so I can't say what {project.name} has cost.")
    hours = project_time.total(project)
    if hours:
        line = f"You've put {hours:g} hour{'s' if hours != 1 else ''} into it"
        rate = 0.0
        try:
            config = getattr(context, "config", None)
            rate = float(config.get("workshop.labor_rate_per_hour", 0) or 0) if config is not None else 0.0
        except (TypeError, ValueError):
            rate = 0.0
        if rate > 0:
            line += f", {money(hours * rate)} of your time at your {money(rate)} an hour"
        parts.append(line + ".")
    else:
        parts.append("No hours logged on it yet.")
    return " ".join(parts)


def _day(text: str) -> Optional[date]:
    """Pure logic. An ISO date, or None."""
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None
