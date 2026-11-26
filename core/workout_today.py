"""
core.workout_today
====================

"What's a good workout for today?" (the live sweep, 2026-11-26: it had said it couldn't suggest one), answered in
code from his own training:

1. **His plan first**: with a training rotation in Fitness (core/fitness_manager.today_training), today's day in it
   (its saved workout's exercises), or that today is a rest day in it.
2. **Else the group rested longest**: of the groups he has exercises for (PUSH, PULL, LEGS, CORE, from each
   exercise's category, or its name when it's "Full Body", as spoken and live logs make them: `group_of`), the one
   least recently trained over LOOKBACK_DAYS; his own exercises for it with his last top set (from all his history)
   and a small step up: about 5% more weight once he's done 12 reps, else one more rep; a hold, 5 more seconds;
   in his units (kg or lb, core/fitness_manager.default_units).
3. Trained both of the last two days: a lighter day is said first. No history: a short full-body starter.

The Fable review (2026-11-26) found spoken logs unread (their "Full Body" category), an empty group always chosen,
the plan ignored, holds said as "0 reps" and a flat 5 lb on every lift; all fixed here.

`suggest(context, today)` gives the parts; `say(context, today)` the words. Read only.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

LOOKBACK_DAYS = 14
GROUPS = {"Push": ("Chest", "Shoulders"), "Pull": ("Back",), "Legs": ("Legs",), "Core": ("Core",)}
_BY_NAME = (("Legs", r"squat|lunge|deadlift|leg press|calf|step[- ]?up|hip thrust|glute|hamstring|quad"),
            ("Push", r"bench|press|push[- ]?up|dip|fly|flye|tricep|skull|overhead|lateral raise|shoulder"),
            ("Pull", r"row|pull[- ]?up|chin[- ]?up|curl|lat |pulldown|face pull|shrug"),
            ("Core", r"plank|crunch|sit[- ]?up|ab |abs|russian twist|leg raise|hollow|dead bug|core"))
STARTER = ("a full-body starter: 3 rounds of 10 squats, 10 push-ups (on your knees is fine), 10 rows with whatever you "
           "have (a dumbbell, a backpack), and a 30-second plank, resting a minute between rounds. Tell me what you "
           "did (\"I did 3 sets of 10 squats\") and I'll keep count and build from it.")
SHOWN = 4


def group_of(exercise) -> str:
    """Pure logic. An exercise's group: by its category, else by its name (a "Full Body" one from a spoken or live
    log); "" for cardio and what can't be told. Arms go by name (a curl pulls, a triceps press pushes)."""
    category = getattr(exercise, "category", "") or ""
    found = next((g for g, cats in GROUPS.items() if category in cats), "")
    if found:
        return found
    if category in ("Cardio",):
        return ""
    name = f" {getattr(exercise, 'name', '') or ''} ".lower()
    return next((g for g, pattern in _BY_NAME if re.search(pattern, name)), "")


def _units(context) -> str:
    """kg or lb by his country (core/fitness_manager.default_units); lb without it."""
    fitness = getattr(context, "fitness", None)
    try:
        return fitness.default_units() if fitness is not None else "lb"
    except Exception:  # noqa: BLE001
        return "lb"


def _plural(n: float, word: str) -> str:
    """Pure logic. "1 rep", "11 reps"."""
    return f"{n:g} {word}{'' if n == 1 else 's'}"


def _step_up(reps: int, weight: float, seconds: float, unit: str) -> str:
    """Pure logic. The next small step from his last top set: a hold 5 seconds longer; about 5% more weight (rounded
    to 2.5, or 5 over 100) once he's done 12, with fewer reps; else one more rep."""
    if not reps and seconds:
        return f"try {seconds + 5:g} seconds"
    if weight and reps >= 12:
        step = 5.0 if weight >= 100 else 2.5
        more = max(step, round(weight * 0.05 / step) * step)
        return f"try {weight + more:g} {unit} for {max(reps - 4, 6)}"
    return f"try {_plural(reps + 1, 'rep')}" + (f" at {weight:g} {unit}" if weight else "")


def _last(reps: int, weight: float, seconds: float, unit: str) -> str:
    """Pure logic. His last top set in words."""
    if not reps and seconds:
        return f"last time {seconds:g} seconds"
    return f"last time {_plural(reps, 'rep')}" + (f" at {weight:g} {unit}" if weight else "")


def _plan_day(context, today: date) -> Optional[dict]:
    """His Fitness plan's day: {name, template_id, done} today, {"rest": True} on its rest day, None with no plan."""
    fitness = getattr(context, "fitness", None)
    if fitness is None:
        return None
    try:
        rotation = (fitness.plan.get("training") or {}).get("rotation") or []
        if not rotation:
            return None
        return fitness.today_training(today) or {"rest": True}
    except Exception:  # noqa: BLE001 - the history then
        return None


def suggest(context, today: Optional[date] = None) -> dict:
    """{plan, group, rested_days, exercises: [{name, last}], template, rest_first, any} (see the module's opening);
    {} with no workout store."""
    from core.paths import _workouts

    today = today or date.today()
    store = getattr(context, "workout", None)
    if store is None:
        return {}
    unit = _units(context)
    every = _workouts(context, "") or []
    recent = [s for s in every if s.date >= (today - timedelta(days=LOOKBACK_DAYS)).isoformat()]
    in_window = {id(s) for s in recent}
    exercises = {e.exercise_id: e for e in store.all_exercises()}
    last_day: dict = {}
    last_set: dict = {}  # exercise_id -> (date, reps, weight, seconds), the top set of its latest session
    for s in sorted(every, key=lambda s: s.date):
        for logged in s.sets_logged:
            ex = exercises.get(logged.get("exercise_id"))
            if ex is None:
                continue
            group = group_of(ex)
            if group and id(s) in in_window:
                last_day[group] = max(last_day.get(group, ""), s.date)
            reps, weight = int(logged.get("reps") or 0), float(logged.get("weight") or 0)
            seconds = float(logged.get("seconds") or 0)
            before = last_set.get(ex.exercise_id)
            if before is None or before[0] < s.date or (before[0] == s.date and (weight, reps, seconds) >
                                                        (before[2], before[1], before[3])):
                last_set[ex.exercise_id] = (s.date, reps, weight, seconds)
    days = {s.date for s in every}
    rest_first = (today - timedelta(days=1)).isoformat() in days and (today - timedelta(days=2)).isoformat() in days \
        and today.isoformat() not in days

    def lines(chosen: list) -> list:
        """His exercises with their last top set and the next step."""
        out = []
        for e in chosen[:SHOWN]:
            got = last_set.get(e.exercise_id)
            out.append({"name": e.name, "last": f"{_last(got[1], got[2], got[3], unit)}; {_step_up(got[1], got[2], got[3], unit)}"
                        if got else "not logged yet"})
        return out

    found = {"plan": None, "group": "", "rested_days": 0, "exercises": [], "template": "", "rest_first": rest_first,
             "any": bool(every)}
    plan = _plan_day(context, today)
    if plan is not None:
        found["plan"] = plan
        template = store.get_template(plan.get("template_id", "")) if plan.get("template_id") else None
        if template is not None:
            found["exercises"] = lines([exercises[x["exercise_id"]] for x in template.exercises
                                        if x.get("exercise_id") in exercises])
        return found
    have = {group_of(e) for e in exercises.values()} - {""}
    if not have or not recent:
        return found

    def rested(g: str) -> int:
        """Days since that group was trained (LOOKBACK_DAYS + 1 when not in the window)."""
        when = last_day.get(g)
        return (today - date.fromisoformat(when[:10])).days if when else LOOKBACK_DAYS + 1

    group = max(sorted(have), key=lambda g: (rested(g), g == "Legs"))
    mine = sorted((e for e in exercises.values() if group_of(e) == group),
                  key=lambda e: last_set.get(e.exercise_id, ("",))[0], reverse=True)
    found.update(group=group, rested_days=rested(group), exercises=lines(mine),
                 template=next((t.name for t in store.all_templates()
                                if any(group_of(exercises.get(x.get("exercise_id"))) == group
                                       for x in t.exercises if x.get("exercise_id") in exercises)), ""))
    return found


def say(context, today: Optional[date] = None) -> str:
    """For "what's a good workout for today?": his plan's day, or his own next workout, or a starter."""
    if getattr(context, "workout", None) is None:
        return "Workouts aren't on this MIA."
    found = suggest(context, today)
    parts = []
    if found.get("rest_first"):
        parts.append("You trained the last two days: a light day or a walk is a fine choice too.")
    plan = found.get("plan")
    if plan is not None:
        if plan.get("rest"):
            return " ".join(parts + ["Today's a rest day in your plan: a walk or a stretch, and back at it next time."])
        said = f"Today in your plan: {plan.get('name') or 'your training day'}" + (" (done already)." if plan.get("done") else ".")
        parts.append(said)
        if found["exercises"]:
            parts.append("; ".join(f"{e['name']} ({e['last']})" for e in found["exercises"]) + ".")
        return " ".join(parts)
    if not found.get("group"):
        if found.get("any"):
            return " ".join(parts + ["Nothing in the last two weeks I can sort into push, pull, legs or core, so: "
                                     + STARTER])
        return "With nothing logged yet, " + STARTER
    rested = found["rested_days"]
    since = ("not in the last two weeks" if rested > LOOKBACK_DAYS else
             "yesterday" if rested == 1 else "today already" if rested == 0 else f"{rested} days ago")
    parts.append(f"{found['group']} is the one rested longest (last trained {since}).")
    parts.append("Your own: " + "; ".join(f"{e['name']} ({e['last']})" for e in found["exercises"]) + ".")
    if found["template"]:
        parts.append(f"Your saved workout \"{found['template']}\" covers it.")
    return " ".join(parts)
