"""
core.web_fitness
==================

What the fitness screens show (DEC-0020, H-0026), assembled in core so
the screens (Muse's) only draw it: today (training and its steps, skill
practice, food and nutrition against the targets, planned meals, the
day's fitness missions), the weight line, the week's meal plan with its
prep and shopping list, and "Is it working?" (docs/KITCHEN_FITNESS_PLAN.md
phase 7): four weeks of training, meals on plan, calories and protein
against the goals, and the weight's direction, in one plain sentence
computed here, never by a model.

Children's pages leave out weight (core/fitness_actions.py doesn't offer
weigh-ins to them either).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.fitness_manager import WEEKDAYS


def _child(context) -> bool:
    from core.child_accounts import is_child

    try:
        return bool(is_child(context))
    except Exception:
        return False


def _missions(context, today: date) -> list[dict]:
    from core.fitness_missions import _kind, ensure

    out = []
    for mission in ensure(context, today):
        objectives = [{"index": i, "text": o.description, "progress": o.progress, "target": o.target,
                       "done": o.progress >= o.target} for i, o in enumerate(mission.objectives)]
        out.append({"mission_id": mission.mission_id, "kind": _kind(mission), "name": mission.name, "icon": mission.icon,
                    "cadence": "daily" if mission.recurring_kind == "fitness_daily" else "weekly",
                    "status": mission.status, "xp": mission.reward_xp, "objectives": objectives,
                    "done": sum(o["done"] for o in objectives), "total": len(objectives)})
    return out


def weight_series(fit, today: date, days: int = 90) -> list[dict]:
    """Each weigh-in in the window with the 7-day average at that point (the line to draw)."""
    from core.fitness_manager import convert

    units = fit.plan["units"]
    points = [(date.fromisoformat(w["date"]), convert(w["weight"], w.get("unit", units), units), w["id"])
              for w in fit.weigh_ins() if today - timedelta(days=days) < date.fromisoformat(w["date"]) <= today]
    out = []
    for day, weight, entry_id in points:
        window = [w for d, w, _ in points if day - timedelta(days=7) < d <= day]
        out.append({"id": entry_id, "date": day.isoformat(), "weight": round(weight, 1),
                    "average": round(sum(window) / len(window), 1)})
    return out


def fitness_page(context, today: Optional[date] = None) -> dict:
    from core.meal_plan import day_plan

    fit = getattr(context, "fitness", None)
    if fit is None:
        return {"available": False}
    today = today or date.today()
    plan = fit.plan
    child = _child(context)
    training = fit.today_training(today)
    if training is not None:
        done = set(fit.steps_done(today.isoformat()))
        training = {**training, "steps": [{"index": i, "name": e.get("name", ""), "sets": e.get("sets"),
                                           "reps": e.get("reps"), "hold_seconds": e.get("hold_seconds"),
                                           "done": i in done} for i, e in enumerate(training.get("exercises") or [])]}
    skills = []
    for skill in plan.get("skill_tree") or []:
        name = skill.get("skill", "")
        steps = [{**step, "best_seconds": fit.best_hold(name, step.get("name", ""))} for step in skill.get("steps") or []]
        skills.append({"skill": name, "daily_minutes": skill.get("daily_minutes"), "practice": skill.get("practice") or [],
                       "minutes_today": fit.practice_minutes(name, today.isoformat()), "steps": steps,
                       "best_seconds": fit.best_hold(name)})
    page = {
        "available": True, "as_of": today.isoformat(), "child": child, "plan": plan,
        "today": {"training": training, "rest_day": training is None and bool((plan["training"].get("rotation"))),
                  "skills": skills, "food": fit.day_totals(today.isoformat()), "meals": day_plan(context, today)},
        "missions": _missions(context, today),
        "milestones": plan.get("milestones") or [],
        "progress": progress(context, today),
    }
    page["plan_text"] = plan_text(plan)
    if not child:
        page["weight"] = {**fit.weight_trend(today), "series": weight_series(fit, today)}
    return page


def plan_text(plan: dict) -> dict:
    """The plan's lists as the lines My plan's editor shows (and
    fitness.plan reads back: core/fitness_manager.parse_exercise)."""
    from core.fitness_manager import exercise_text, skill_step_text

    return {"rotation": [{"name": d.get("name", ""), "exercises": "\n".join(exercise_text(e) for e in d.get("exercises") or [])}
                         for d in plan["training"].get("rotation") or []],
            "skills": [{"skill": k.get("skill", ""), "daily_minutes": k.get("daily_minutes"),
                        "practice": ", ".join(k.get("practice") or []),
                        "steps": "\n".join(skill_step_text(x) for x in k.get("steps") or [])}
                       for k in plan.get("skill_tree") or []]}


def week_page(context, day: Optional[date] = None) -> dict:
    """The meal-plan week: each day's meals and totals, prep sessions, shopping list, and a suggestion."""
    from core.meal_plan import shopping_list, suggest_week, week_plan

    if getattr(context, "fitness", None) is None:
        return {"available": False}
    day = day or date.today()
    kitchen = getattr(context, "kitchen", None)
    recipes = [{"recipe_id": r.recipe_id, "name": r.name, "category": r.category, "servings": r.servings}
               for r in (kitchen.all_recipes() if kitchen is not None else []) if not getattr(r, "locked", False)]
    return {"available": True, **week_plan(context, day), "shopping": shopping_list(context, day),
            "suggestion": suggest_week(context, day), "recipes": recipes}


# ------------------------------------------------------------------ is it working?


def _plural(n: float, word: str) -> str:
    return f"{n:g} {word}{'' if n == 1 else 's'}"


def progress(context, today: Optional[date] = None, weeks: int = 4) -> dict:
    """The last `weeks` weeks against the plan, and one plain sentence."""
    fit = context.fitness
    today = today or date.today()
    start = today - timedelta(days=7 * weeks - 1)
    data = fit._data
    first = min([e["date"] for key in ("weigh_ins", "food", "skill_sessions", "training_done") for e in data[key]]
                + [d for d in data["habits"]], default=None)
    if first is None:
        return {"weeks": 0, "since": None, "planned_workouts": 0, "workouts": 0, "planned_meals": 0, "meals_eaten": 0,
                "average_kcal": None, "average_protein_g": None, "weekly_weight_change": None, "days": [],
                "sentence": "Nothing logged yet. Log a weigh-in, a workout or a meal and this fills in."}
    start = max(start, date.fromisoformat(first))  # never count days from before you started
    plan = fit.plan
    days = [start + timedelta(days=i) for i in range((today - start).days + 1)]
    training_days = set(plan["training"].get("days") or [])
    planned_sessions = sum(1 for d in days if WEEKDAYS[d.weekday()] in training_days) if plan["training"].get("rotation") else 0
    trained = len(fit.training_days_done(start.isoformat()))
    planned_meals = sum(len(fit.planned(d.isoformat())) for d in days)
    eaten_meals = sum(len(fit.eaten_planned(d.isoformat())) for d in days)
    logged = [fit.day_totals(d.isoformat())["totals"] for d in days]
    with_kcal = [t["kcal"] for t in logged if t["kcal"] is not None]
    with_protein = [t["protein_g"] for t in logged if t["protein_g"] is not None]
    average_kcal = round(sum(with_kcal) / len(with_kcal)) if with_kcal else None
    average_protein = round(sum(with_protein) / len(with_protein)) if with_protein else None
    weight = fit.weight_trend(today) if not _child(context) else {}
    targets = plan["targets"]

    parts = []
    if planned_sessions:
        parts.append(f"{trained} of {planned_sessions} workouts")
    elif trained:
        parts.append(_plural(trained, "workout"))
    if planned_meals:
        parts.append(f"{eaten_meals} of {planned_meals} planned meals")
    if average_kcal is not None:
        goal = f" (goal {targets['calories']:,})" if targets.get("calories") else ""
        parts.append(f"{average_kcal:,} kcal a day{goal}")
    if average_protein is not None:
        goal = f" (goal {targets['protein_g']:g})" if targets.get("protein_g") else ""
        parts.append(f"{average_protein} g protein{goal}")
    rate = weight.get("weekly_change")
    if rate is not None:
        units = weight.get("units", "")
        parts.append("weight steady" if abs(rate) < 0.1 else f"weight {'down' if rate < 0 else 'up'} {abs(rate):g} {units} a week")
    span = (today - start).days + 1
    period = _plural(round(span / 7), "week") if span >= 14 else ("Today" if span == 1 else _plural(span, "day"))
    sentence = f"{period}: " + ", ".join(parts) + "." if parts else \
        "Nothing logged yet. Log a weigh-in, a workout or a meal and this fills in."
    if weight.get("on_track_for"):
        when = date.fromisoformat(weight["on_track_for"])
        sentence = sentence[:-1] + f", on track for your goal by {when.strftime('%B')} {when.day}."  # %-d isn't on Windows
    return {"weeks": round(span / 7, 1), "since": start.isoformat(), "planned_workouts": planned_sessions, "workouts": trained,
            "planned_meals": planned_meals, "meals_eaten": eaten_meals, "average_kcal": average_kcal,
            "average_protein_g": average_protein, "weekly_weight_change": rate, "sentence": sentence,
            "days": fit.daily_history(span, today)}
