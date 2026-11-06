"""
core.household_routines
=========================

The Household's web screen (web/household.html): the household's routines
(recurring-mission templates in the "Household" category: laundry, dishes,
hygiene), each with its current occurrence (today's, or this week's for a
weekly one), how far along it is and its streak, and the total for the
day. Logging one is the `routine.log` action, as on the glasses. The same
reading as the desktop's Household module (modules/household), assembled
here so the web never computes it (DEC-0017).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

CATEGORIES = ("Household",)


def screen(context, today: Optional[date] = None) -> dict:
    today = today or date.today()
    book = getattr(context, "recurring_missions", None)
    rows = []
    for t in (book.all_templates() if book is not None else []):
        if t.category not in CATEGORIES or not t.active:
            continue
        mission, _bonus = book.ensure_current_missions(t, today)  # idempotent, as the desktop and the daily check do
        objective = mission.objectives[0] if mission is not None and mission.objectives else None
        rows.append({"id": t.template_id, "name": t.name, "every": "week" if t.recurrence == "weekly" else "day",
                     "done": mission is not None and mission.status == "completed",
                     "progress": objective.progress if objective else 0, "target": objective.target if objective else 0,
                     "streak": book.current_streak_for_template(t.template_id, today)})
    return {"routines": rows, "done": sum(1 for r in rows if r["done"]), "total": len(rows)}
