"""
core.household_routines
=========================

The Household's web screen (web/household.html; the design canvas's
Household, DEC-0113): the household's routines (recurring-mission templates
in the "Household" category: laundry, dishes, the trash), each with its
current occurrence (today's, or this week's for a weekly one), how far
along it is and its streak in words, and the total done today; routines on
pause listed apart. Logging one is the `routine.log` action, as on the
glasses; adding, pausing and resuming one are `routine.add`,
`routine.pause` and `routine.resume` (core/routine_actions.py), the same
words by voice. Assembled here so the web never computes it (DEC-0017).

add_routine() is the one way a household routine is set up, used by the
action and the add_household_routine voice tool alike.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

CATEGORIES = ("Household",)


def streak_words(streak: int, every: str) -> str:
    """Pure logic. A streak in words: "21 days", "1 week", "a new streak" at zero."""
    if streak <= 0:
        return "a new streak"
    unit = "week" if every == "week" else "day"
    return f"{streak} {unit}{'' if streak == 1 else 's'}"


def add_routine(context, name: str, times=1, every: str = "day", today: Optional[date] = None):
    """Sets up a household routine (so many times a day or a week, tracked with a streak and a little XP), and returns
    it. ValueError without a name, for one already there by that name, or without the routines store."""
    from core.gamification import SkillWeight

    book = getattr(context, "recurring_missions", None)
    if book is None:
        raise ValueError("Household routines aren't available right now.")
    name = str(name or "").strip()
    if not name:
        raise ValueError("What's the routine called?")
    if any(t.category in CATEGORIES and t.active and t.name.lower() == name.lower() for t in book.all_templates()):
        raise ValueError(f"You already have a {name} routine.")
    recurrence = "weekly" if str(every or "").strip().lower().startswith("week") else "daily"
    try:
        target = max(1.0, float(times or 1))
    except (TypeError, ValueError):
        raise ValueError("How many times? Give a number.") from None
    return book.add_template(
        name=name, objective_description_template=f"{name} ({{target:g}}x)", base_target=target,
        target_increment_per_week=0.0, daily_reward_xp=10, weekly_bonus_reward_xp=25,
        start_date=(today or date.today()).isoformat(), daily_skill_rewards=[SkillWeight("household_management", 5)],
        icon="\U0001F9FA", recurrence=recurrence, category="Household",
    )


def screen(context, today: Optional[date] = None) -> dict:
    """Every active Household routine with its current occurrence (made if it's missing, as the desktop and the daily
    check do), whether it's done, its progress toward its target, its streak (and in words), still-to-do ones first;
    the paused ones; how many are done today; and the routine form.
    """
    from core.routine_actions import ROUTINE_FIELDS

    today = today or date.today()
    book = getattr(context, "recurring_missions", None)
    rows, paused = [], []
    for t in (book.all_templates() if book is not None else []):
        if t.category not in CATEGORIES:
            continue
        every = "week" if t.recurrence == "weekly" else "day"
        if not t.active:
            paused.append({"id": t.template_id, "name": t.name, "every": every,
                           "when": "Weekly" if every == "week" else "Daily"})
            continue
        mission, _bonus = book.ensure_current_missions(t, today)  # idempotent, as the desktop and the daily check do
        objective = mission.objectives[0] if mission is not None and mission.objectives else None
        streak = book.current_streak_for_template(t.template_id, today)
        rows.append({"id": t.template_id, "name": t.name, "every": every,
                     "when": "This week" if every == "week" else "Daily",
                     "done": mission is not None and mission.status == "completed",
                     "progress": objective.progress if objective else 0, "target": objective.target if objective else 0,
                     "streak": streak, "streak_text": streak_words(streak, every)})
    rows.sort(key=lambda r: r["done"])  # what's still to do first; stable, so the order they were added holds
    return {"routines": rows, "paused": paused, "done": sum(1 for r in rows if r["done"]), "total": len(rows),
            "pct": round(100 * sum(1 for r in rows if r["done"]) / len(rows)) if rows else 0,
            "forms": {"routine": {"fields": ROUTINE_FIELDS}}}
