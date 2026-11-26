"""
core.workout_today
====================

"What's a good workout for today?" (the live sweep, 2026-11-26: it had said it couldn't suggest one), answered in
code from his own training: the muscle group he's rested longest over the last LOOKBACK_DAYS (by his exercises'
categories, grouped PUSH, PULL, LEGS and CORE), his own exercises for it with what he did last time and a small step
up (one more rep, or 5 lb once he's done 12: progressive overload, as his Fitness course teaches), and a saved
workout of his that covers it. Trained hard both of the last two days: a lighter day is said first. With no history,
a short full-body starter he can log.

`suggest(context, today)` gives {group, rested_days, exercises: [{name, last}], template, rest_first} or {} with no
history; `say(context, today)` the words. Read only.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

LOOKBACK_DAYS = 14
GROUPS = {"Push": ("Chest", "Shoulders"), "Pull": ("Back", "Arms"), "Legs": ("Legs",), "Core": ("Core",)}
STARTER = ("a full-body starter: 3 rounds of 10 squats, 10 push-ups (on your knees is fine), 10 rows with whatever you "
           "have (a dumbbell, a backpack), and a 30-second plank, resting a minute between rounds. Tell me what you "
           "did (\"I did 3 sets of 10 squats\") and I'll keep count and build from it.")
SHOWN = 4


def _group_of(category: str) -> str:
    """Pure logic. The group an exercise's category is in ("" for cardio, full body and other)."""
    return next((g for g, cats in GROUPS.items() if category in cats), "")


def _step_up(reps: int, weight: float) -> str:
    """Pure logic. The next small step from his last top set: 5 lb more once he's done 12, else one more rep."""
    if weight and reps >= 12:
        return f"try {weight + 5:g} lb for {max(reps - 4, 6)}"
    return f"try {reps + 1} reps" + (f" at {weight:g} lb" if weight else "")


def suggest(context, today: Optional[date] = None) -> dict:
    """What to train today from his last LOOKBACK_DAYS (see the module's opening), or {} with no workout store or no
    sessions with known exercises."""
    from core.paths import _workouts

    today = today or date.today()
    store = getattr(context, "workout", None)
    sessions = _workouts(context, (today - timedelta(days=LOOKBACK_DAYS)).isoformat()) if store is not None else None
    if not sessions:
        return {}
    exercises = {e.exercise_id: e for e in store.all_exercises()}
    last_day: dict = {}
    last_set: dict = {}  # exercise_id -> (date, reps, weight), the heaviest set of its latest session
    for s in sorted(sessions, key=lambda s: s.date):
        for logged in s.sets_logged:
            ex = exercises.get(logged.get("exercise_id"))
            if ex is None:
                continue
            group = _group_of(ex.category)
            if group:
                last_day[group] = max(last_day.get(group, ""), s.date)
            reps, weight = int(logged.get("reps") or 0), float(logged.get("weight") or 0)
            before = last_set.get(ex.exercise_id)
            if before is None or before[0] < s.date or (before[0] == s.date and (weight, reps) > before[2:0:-1]):
                last_set[ex.exercise_id] = (s.date, reps, weight)
    if not last_day:
        return {}
    days = {s.date for s in sessions}
    rest_first = today.isoformat() in days and (today - timedelta(days=1)).isoformat() in days

    def rested(g: str) -> int:
        """Days since that group was trained (LOOKBACK_DAYS + 1 when not in the window)."""
        when = last_day.get(g)
        return (today - date.fromisoformat(when[:10])).days if when else LOOKBACK_DAYS + 1

    group = max(GROUPS, key=lambda g: (rested(g), g == "Legs"))
    mine = [e for e in exercises.values() if _group_of(e.category) == group]
    mine.sort(key=lambda e: last_set.get(e.exercise_id, ("",))[0], reverse=True)
    picked = []
    for e in mine[:SHOWN]:
        got = last_set.get(e.exercise_id)
        last = (f"last time {got[1]} reps" + (f" at {got[2]:g} lb" if got[2] else "") + f"; {_step_up(got[1], got[2])}"
                if got else "not logged yet")
        picked.append({"name": e.name, "last": last})
    template = next((t.name for t in store.all_templates()
                     if any(_group_of(getattr(exercises.get(x.get("exercise_id")), "category", "")) == group
                            for x in t.exercises)), "")
    return {"group": group, "rested_days": rested(group), "exercises": picked, "template": template,
            "rest_first": rest_first}


def say(context, today: Optional[date] = None) -> str:
    """For "what's a good workout for today?": his own next workout, or a starter with no history."""
    if getattr(context, "workout", None) is None:
        return "Workouts aren't on this MIA."
    found = suggest(context, today)
    if not found:
        return "With nothing logged in the last two weeks, " + STARTER
    rested = found["rested_days"]
    since = ("not in the last two weeks" if rested > LOOKBACK_DAYS else
             "yesterday" if rested == 1 else "today already" if rested == 0 else f"{rested} days ago")
    parts = []
    if found["rest_first"]:
        parts.append("You've trained today and yesterday: a light day or a walk is a fine choice too.")
    parts.append(f"{found['group']} is the one rested longest (last trained {since}).")
    if found["exercises"]:
        parts.append("Your own: " + "; ".join(f"{e['name']} ({e['last']})" for e in found["exercises"]) + ".")
    else:
        parts.append(f"You don't have {found['group'].lower()} exercises in your library yet: add one in Workout.")
    if found["template"]:
        parts.append(f"Your saved workout \"{found['template']}\" covers it.")
    return " ".join(parts)
