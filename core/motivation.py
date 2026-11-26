"""
core.motivation
=================

"I need motivation" (the full sweep, 2026-11-26: the model made up "you're running low on cash" and asked a
question): his own reasons said back (core/why_graph's chains, the ones he gave: "working this job to pay off debt,
to control my own time"), and one small thing he can do now from today's list (core/today), never a guess about how
he feels. With no reasons kept yet, how to tell her one.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)


def say(context, today: Optional[date] = None, task: str = "") -> str:
    """His reasons, then one thing to start on now: for a task he named ("to finish the shed", "to work on the shed"),
    its smallest piece and the hours logged on that project (found by the thing, never its verb); else a task or upkeep due today or overdue (never a bill, a birthday or
    something coming soon), else the smallest step toward it."""
    today = today or date.today()
    parts = []
    try:
        from core.why_graph import build_why_sheet

        sheet = build_why_sheet(context, record_checkpoint=False) if getattr(context, "intents", None) is not None else None
        chains = [] if sheet is None or sheet.is_empty else sheet.chains
    except Exception:  # noqa: BLE001
        log.exception("Motivation: the reasons couldn't be read")
        chains = []
    if chains:
        said = " → ".join(link.name for link in chains[0])
        parts.append(f"Here's what you told me you're working toward: {said}.")
        done = [link.name for chain in chains for link in chain if link.done]
        if done:
            parts.append(f"You've already done {done[0]}.")
    else:
        parts.append("Tell me what you're working toward and why (\"the reason I'm working this job is to pay off my "
                     "debt\"), and I'll keep it to remind you on days like this.")
    try:
        from core.today import is_alarm, today_items

        # a task or upkeep due now, never a bill, a birthday, an event or something coming soon (the Fable review)
        items = [i for i in today_items(context, today) if not is_alarm(i.as_dict())
                 and getattr(i, "module_id", "") in ("toolbox", "maintenance") and getattr(i, "when", "") in
                 ("overdue", "today")]
    except Exception:  # noqa: BLE001
        items = []
    if task:  # "motivation to finish the shed": the smallest piece of that, and what's logged on it
        import re

        thing = re.sub(r"^(?:finish|work on|start|do|get to|tackle|build|clean(?: up)?)\s+", "", task.strip(), flags=re.I)
        project = None
        try:
            from core import project_time

            project = project_time.project_named(context, thing)
        except Exception:  # noqa: BLE001
            project = None
        logged = ""
        if project is not None:
            hours = project_time.total(project)
            logged = f" You've put {hours:g} hours into {project.name} so far." if hours else ""
        parts.append(f"For {thing or task}: pick the smallest piece you can finish in twenty minutes and do just "
                     f"that.{logged}")
    elif items:
        parts.append(f"One small thing to start with: {items[0].title}. Do that one, then see how you feel.")
    else:
        parts.append("Nothing's due today, so pick the smallest step toward it and do just that.")
    return " ".join(parts)
