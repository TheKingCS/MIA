"""
core.fitness_actions
======================

What the fitness screens and plain-word commands change (DEC-0020,
H-0026), as action kinds: proposed, approved, recorded, undoable, and
credited to the person (core/actions.py). Each logs into the person's
fitness store (core/fitness_manager.py) and then brings the fitness
missions up to date (core/fitness_missions.py), since the logs are the
truth.

| Kind | Does |
|---|---|
| fitness.weigh_in | logs a weight (today, or a date) |
| fitness.food | logs something eaten: a recipe's servings, or numbers |
| fitness.protein | logs grams of protein (a shake, a snack) |
| fitness.training_done | today's training, all of it |
| fitness.step | one step (exercise) of today's training |
| fitness.skill | timed skill practice (a 45 s handstand hold) |
| fitness.habit | a yes for the day: packed lunch, meal prep, protein hit |
| fitness.plan | changes the plan (targets, rotation, skills, meals) |
| fitness.milestone | a milestone reached |
| meal.plan | one day's meal: a recipe and servings (or cleared) |
| meal.prep | a prep session: cook a recipe ahead for the meals it covers |
| meal.prep_done | a prep session cooked |
| meal.prep_delete | a prep session removed, with the meals it covered |
| fitness.food_delete | something logged as eaten, removed |
| fitness.weigh_in_delete | a weigh-in removed |
| meal.suggest | fill the week's empty lunches and dinners from your recipes |
| meal.shop | the week's shopping list onto the Kitchen's grocery list |
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType


def _fit(context):
    fit = getattr(context, "fitness", None)
    if fit is None:
        raise ActionError("Fitness isn't set up on this MIA.")
    return fit


def _number(value, what: str, low: float = 0.0) -> float:
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ActionError(f"{what} needs a number.") from None
    if number <= low:
        raise ActionError(f"{what} has to be more than {low:g}.")
    return number


def _day(params) -> str:
    raw = str(params.get("date") or "").strip()
    if not raw:
        return date.today().isoformat()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        raise ActionError("Dates look like 2026-10-12.") from None


def _after(context) -> None:
    from core.fitness_missions import sync

    sync(context)


# ------------------------------------------------------------------ weight


def _describe_weigh_in(context, params) -> str:
    fit = _fit(context)
    weight = _number(params.get("weight"), "A weight")
    unit = params.get("unit") or fit.plan["units"]
    if unit not in ("lb", "kg"):
        raise ActionError("Weights are in lb or kg.")
    return f"Log your weight: {weight:g} {unit}" + (f" on {params['date']}" if params.get("date") else "")


def _weigh_in(context, params) -> str:
    fit = _fit(context)
    try:
        entry = fit.log_weight(_number(params.get("weight"), "A weight"), _day(params), params.get("unit") or None)
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    picture = fit.weight_trend()
    trend = ""
    if picture.get("weekly_change") is not None:
        rate = picture["weekly_change"]
        trend = f" Your trend: {'down' if rate < 0 else 'up'} {abs(rate):g} {picture['units']} a week." if rate else " Your trend: steady."
    return f"Logged {entry['weight']:g} {entry['unit']}.{trend}"


# ------------------------------------------------------------------ food


def _food_entry(context, params) -> tuple[str, str, dict, str, float]:
    """(meal, name, nutrients, recipe_id, servings) for a food log."""
    from core.fitness_manager import MEALS
    from core.nutrition import recipe_facts, scaled

    meal = str(params.get("meal") or "snack").lower()
    if meal not in MEALS:
        raise ActionError("Meals are breakfast, lunch, dinner or snack.")
    servings = _number(params.get("servings") or 1, "Servings")
    recipe_id = str(params.get("recipe_id") or "")
    if recipe_id:
        kitchen = getattr(context, "kitchen", None)
        recipe = kitchen.get_recipe(recipe_id) if kitchen is not None else None
        if recipe is None:
            raise ActionError("There's no recipe like that.")
        return meal, recipe.name, scaled(recipe_facts(recipe), servings), recipe_id, servings
    name = str(params.get("name") or "").strip()
    if not name:
        raise ActionError("What did you eat?")
    nutrients = {}
    for key in ("kcal", "protein_g", "carbs_g", "fat_g"):
        if params.get(key) not in (None, ""):
            nutrients[key] = _number(params[key], key.replace("_g", "").replace("kcal", "Calories"), low=-0.1)
    return meal, name, nutrients, "", servings


def _describe_food(context, params) -> str:
    meal, name, nutrients, _, servings = _food_entry(context, params)
    amount = f"{servings:g} × " if servings != 1 else ""
    facts = ", ".join(f"{round(nutrients[k]):g} {'kcal' if k == 'kcal' else 'g protein'}" for k in ("kcal", "protein_g")
                      if nutrients.get(k) is not None)
    return f"Log {meal}: {amount}{name}" + (f" ({facts})" if facts else "")


def _food(context, params) -> str:
    meal, name, nutrients, recipe_id, servings = _food_entry(context, params)
    fit = _fit(context)
    day = _day(params)
    fit.log_food(meal, name, nutrients, on=day, recipe_id=recipe_id, servings=servings,
                 source="recipe" if recipe_id else "quick", planned_id=str(params.get("planned_id") or ""))
    slot = fit.planned(day).get(meal) if params.get("planned_id") else None
    prepped = bool(slot and slot.get("prep_id") and slot.get("recipe_id") == recipe_id)
    if recipe_id and not prepped and getattr(context, "kitchen", None) is not None:
        context.kitchen.log_meal(recipe_id, day)  # the Kitchen's own "times made" (a prepped meal counted when cooked)
    if meal == "lunch" and params.get("planned_id") and fit.plan["meals"].get("packed_lunch"):
        fit.mark_habit("lunch", day)  # the planned lunch, eaten: it was packed
    _after(context)
    totals = fit.day_totals(day)
    protein, target = totals["totals"]["protein_g"], totals["targets"]["protein_g"]
    so_far = f" Protein today: {protein:g} of {target:g} g." if protein is not None and target else ""
    return f"Logged {name} for {meal}.{so_far}"


def _describe_protein(context, params) -> str:
    return f"Log {_number(params.get('grams'), 'Grams'):g} g of protein" + (f" ({params['name']})" if params.get("name") else "")


def _protein(context, params) -> str:
    grams = _number(params.get("grams"), "Grams")
    return _food(context, {"meal": params.get("meal") or "snack", "name": params.get("name") or "Protein",
                           "protein_g": grams, "date": params.get("date")})


# ------------------------------------------------------------------ training


def _today(context):
    todays = _fit(context).today_training()
    if todays is None:
        raise ActionError("No training is planned today. Rest counts too.")
    return todays


def _describe_training(context, params) -> str:
    todays = _today(context)
    if todays["done"]:
        raise ActionError(f"{todays.get('name') or 'Today’s training'} is already done.")
    return f"Mark today's training done: {todays.get('name') or 'training'}"


def _training(context, params) -> str:
    todays = _fit(context).complete_training()
    _after(context)
    return f"{todays.get('name') or 'Training'} done. Nice work."


def _step_index(context, params) -> tuple[int, dict]:
    todays = _today(context)
    steps = todays.get("exercises") or []
    raw = params.get("step")
    if isinstance(raw, str) and not raw.strip().lstrip("-").isdigit():
        wanted = raw.strip().lower()
        for index, step in enumerate(steps):
            if wanted in step.get("name", "").lower() or step.get("name", "").lower() in wanted:
                return index, todays
        raise ActionError(f"Today's {todays.get('name') or 'training'} has no step like “{raw}”.")
    index = int(_number(raw, "A step")) - 1
    if not 0 <= index < max(1, len(steps)):
        raise ActionError(f"Today's training has {len(steps)} steps.")
    return index, todays


def _describe_step(context, params) -> str:
    index, todays = _step_index(context, params)
    steps = todays.get("exercises") or []
    name = steps[index].get("name") if steps else todays.get("name")
    return f"Mark step {index + 1} done: {name}"


def _step(context, params) -> str:
    index, todays = _step_index(context, params)
    result = _fit(context).complete_step(index)
    _after(context)
    steps = todays.get("exercises") or []
    if result and result.get("done"):
        return f"That's all of {todays.get('name') or 'today’s training'}. Done."
    left = len(steps) - len(result.get("steps_done", [])) if result else 0
    return f"Step {index + 1} done. {left} to go."


def _describe_skill(context, params) -> str:
    skill = str(params.get("skill") or "").strip() or "Skill"
    seconds = params.get("seconds")
    what = f"{_number(seconds, 'Seconds'):g} s" if seconds not in (None, "") else "practice"
    return f"Log {skill}: {params.get('step') or ''} {what}".replace("  ", " ")


def _skill(context, params) -> str:
    fit = _fit(context)
    skill = str(params.get("skill") or "").strip()
    if not skill:
        raise ActionError("Which skill?")
    seconds = _number(params["seconds"], "Seconds") if params.get("seconds") not in (None, "") else None
    minutes = _number(params["minutes"], "Minutes") if params.get("minutes") not in (None, "") else None
    best_before = fit.best_hold(skill, params.get("step") or "")
    fit.log_skill(skill, str(params.get("step") or ""), seconds=seconds, minutes=minutes, on=_day(params))
    _after(context)
    if seconds and (best_before is None or seconds > best_before):
        return f"{skill}: {seconds:g} s. That's your best hold yet."
    return f"{skill} logged."


HABITS = {"lunch": "packed lunch", "prep": "meal prep", "protein": "protein target"}


def _describe_habit(context, params) -> str:
    habit = str(params.get("habit") or "")
    if habit not in HABITS:
        raise ActionError("That isn't one of your daily yeses.")
    return f"Mark done: {HABITS[habit]}"


def _habit(context, params) -> str:
    from core.fitness_missions import monday

    habit = str(params.get("habit") or "")
    day = _day(params)
    key = monday(date.fromisoformat(day)).isoformat() if habit == "prep" else day
    _fit(context).mark_habit(habit, key)
    _after(context)
    return f"{HABITS[habit].capitalize()}: done."


# ------------------------------------------------------------------ plan


def _words(value) -> list[str]:
    """A list, or "a, b, c" typed on a phone, as a clean list."""
    items = value if isinstance(value, list) else str(value or "").replace("\n", ",").split(",")
    return [str(i).strip() for i in items if str(i).strip()]


def _lines(value) -> list[str]:
    return value if isinstance(value, list) else [l for l in str(value or "").splitlines() if l.strip()]


def _optional_number(value, what: str, whole: bool = False):
    if value in (None, ""):
        return None
    number = _number(value, what)
    return int(round(number)) if whole else number


def _clean_plan(context, changes) -> dict:
    """The plan's parts as typed on a screen, checked and shaped like the
    plan (H-0026): numbers as numbers, "Mon, Wed" as a list, exercises
    from lines like "Dips 3x8" (core/fitness_manager.parse_exercise)."""
    from core.fitness_manager import WEEKDAYS, parse_exercise, parse_skill_step

    if not isinstance(changes, dict) or not changes:
        raise ActionError("Nothing to change.")
    unknown = set(changes) - {"targets", "training", "skill_tree", "milestones", "meals", "units"}
    if unknown:
        raise ActionError(f"Plans don't have {', '.join(sorted(unknown))}.")
    out = dict(changes)

    def days(value):
        picked = [d[:3].capitalize() for d in _words(value)]
        wrong = [d for d in picked if d not in WEEKDAYS]
        if wrong:
            raise ActionError(f"Days are Mon, Tue, Wed, Thu, Fri, Sat, Sun (not {', '.join(wrong)}).")
        return [d for d in WEEKDAYS if d in picked]

    if isinstance(changes.get("targets"), dict):
        t = dict(changes["targets"])
        for key, what, whole in (("protein_g", "Protein", True), ("calories", "Calories", True),
                                 ("target_weight", "Goal weight", False), ("workouts_per_week", "Workouts a week", True)):
            if key in t:
                t[key] = _optional_number(t[key], what, whole)
        if t.get("target_weight") is not None and _is_child(context):
            raise ActionError("Goal weights aren't part of a child's plan.")
        if "target_date" in t:
            t["target_date"] = str(t["target_date"] or "").strip() or None
            if t["target_date"]:
                try:
                    date.fromisoformat(t["target_date"])
                except ValueError:
                    raise ActionError("Dates look like 2027-03-01.") from None
        if "weigh_in_days" in t:
            t["weigh_in_days"] = days(t["weigh_in_days"])
        out["targets"] = t
    if isinstance(changes.get("training"), dict):
        tr = dict(changes["training"])
        if "days" in tr:
            tr["days"] = days(tr["days"])
        if "rotation" in tr:
            rotation = []
            for entry in tr["rotation"] or []:
                name = str(entry.get("name") or "").strip()
                if not name:
                    continue
                exercises = entry.get("exercises")
                if not isinstance(exercises, list) or any(isinstance(e, str) for e in exercises):
                    exercises = [e for e in (parse_exercise(l) for l in _lines(exercises)) if e]
                rotation.append({**entry, "name": name, "exercises": exercises})
            tr["rotation"] = rotation
        out["training"] = tr
    if "skill_tree" in changes:
        skills = []
        for entry in changes["skill_tree"] or []:
            name = str(entry.get("skill") or "").strip()
            if not name:
                continue
            steps = entry.get("steps")
            if not isinstance(steps, list) or any(isinstance(x, str) for x in steps):
                steps = [x for x in (parse_skill_step(l) for l in _lines(steps)) if x]
            skills.append({**entry, "skill": name, "steps": steps, "practice": _words(entry.get("practice")),
                           "daily_minutes": _optional_number(entry.get("daily_minutes"), "Minutes a day", True)})
        out["skill_tree"] = skills
    if isinstance(changes.get("meals"), dict):
        m = dict(changes["meals"])
        if "packed_lunch" in m:
            m["packed_lunch"] = str(m["packed_lunch"]).lower() in ("true", "1", "yes", "on")
        if "prep_day" in m:
            m["prep_day"] = (days(m["prep_day"]) or [""])[0]
        if "lunch_rotation" in m:
            m["lunch_rotation"] = _words(m["lunch_rotation"])
        if isinstance(m.get("preferences"), dict):
            prefs = dict(m["preferences"])
            for key in ("dislikes", "allergies"):
                if key in prefs:
                    prefs[key] = _words(prefs[key])
            m["preferences"] = prefs
        out["meals"] = m
    if "milestones" in changes:
        out["milestones"] = [{**x, "name": str(x.get("name") or "").strip()} for x in changes["milestones"] or []
                             if str(x.get("name") or "").strip()]
    if "units" in changes:
        if changes["units"] not in ("lb", "kg"):
            raise ActionError("Units are lb or kg.")
    return out


def _is_child(context) -> bool:
    from core.child_accounts import is_child

    try:
        return bool(is_child(context))
    except Exception:
        return False


PLAN_PARTS = {"targets": "targets", "training": "training", "skill_tree": "skills", "milestones": "milestones",
              "meals": "meals", "units": "units"}


def _describe_plan(context, params) -> str:
    changes = _clean_plan(context, params.get("changes"))
    return "Update your plan: " + ", ".join(PLAN_PARTS[k] for k in sorted(changes))


def _plan(context, params) -> str:
    _fit(context).update_plan(_clean_plan(context, params["changes"]))
    from core.fitness_missions import ensure

    ensure(context)
    return "Your plan is updated."


def _describe_milestone(context, params) -> str:
    milestone = next((m for m in _fit(context).plan.get("milestones", []) if m.get("id") == params.get("milestone_id")), None)
    if milestone is None:
        raise ActionError("There's no milestone like that in your plan.")
    if milestone.get("done_on"):
        raise ActionError(f"{milestone['name']} was reached on {milestone['done_on']}.")
    return f"Mark reached: {milestone['name']}"


def _milestone(context, params) -> str:
    from core.gamification import SkillWeight, grant_xp

    milestone = _fit(context).complete_milestone(str(params["milestone_id"]))
    grant_xp(context, 100, "🏆 Milestone reached", milestone["name"], skill_weights=[SkillWeight("calisthenics", 50)])
    return f"🏆 {milestone['name']}! That's a big one."


# ------------------------------------------------------------------ meal plans (core/meal_plan.py)


def _meal_slot(context, params) -> tuple[str, str, str, float]:
    from core.fitness_manager import MEALS

    day = _day(params)
    meal = str(params.get("meal") or "").lower()
    if meal not in MEALS:
        raise ActionError("Meals are breakfast, lunch, dinner or snack.")
    recipe_id = str(params.get("recipe_id") or "")
    if recipe_id and (getattr(context, "kitchen", None) is None or context.kitchen.get_recipe(recipe_id) is None):
        raise ActionError("There's no recipe like that.")
    return day, meal, recipe_id, _number(params.get("servings") or 1, "Servings")


def _on_day(day: str) -> str:
    """ "today", or "on Fri Oct 16"."""
    said = _say_day(day)
    return said if said == "today" else f"on {said}"


def _say_day(day: str) -> str:
    d = date.fromisoformat(day)
    return "today" if d == date.today() else f"{d:%a} {d:%b} {d.day}"  # %-d isn't on Windows


def _describe_plan_meal(context, params) -> str:
    day, meal, recipe_id, servings = _meal_slot(context, params)
    if not recipe_id:
        return f"Clear {meal} {_on_day(day)}"
    now = _fit(context).planned(day).get(meal)
    replacing = ""
    if now and now["recipe_id"] != recipe_id:
        old = context.kitchen.get_recipe(now["recipe_id"])
        replacing = f" (instead of {old.name})" if old is not None else ""
    return (f"Plan {meal} {_on_day(day)}: {context.kitchen.get_recipe(recipe_id).name}"
            + (f" × {servings:g}" if servings != 1 else "") + replacing)


def _plan_meal(context, params) -> str:
    from core.fitness_missions import ensure

    day, meal, recipe_id, servings = _meal_slot(context, params)
    _fit(context).plan_meal(day, meal, recipe_id or None, servings)
    ensure(context)
    return "Planned." if recipe_id else "Cleared."


def _covers(params) -> list[str]:
    raw = params.get("covers") or []
    covers = raw if isinstance(raw, list) else [c.strip() for c in str(raw).split(",") if c.strip()]
    from core.fitness_manager import MEALS

    for slot in covers:
        day, _, meal = slot.partition(":")
        try:
            date.fromisoformat(day)
        except ValueError:
            raise ActionError(f"“{slot}” isn't a day and meal like 2026-10-13:lunch.") from None
        if meal not in MEALS:
            raise ActionError(f"“{slot}” isn't a day and meal like 2026-10-13:lunch.")
    return covers


def _describe_prep(context, params) -> str:
    recipe_id = str(params.get("recipe_id") or "")
    recipe = context.kitchen.get_recipe(recipe_id) if getattr(context, "kitchen", None) is not None else None
    if recipe is None:
        raise ActionError("There's no recipe like that.")
    servings = _number(params.get("servings") or recipe.servings, "Servings")
    covers = _covers(params)
    return f"Prep {_on_day(_day(params))}: {recipe.name} × {servings:g}" + (f", covering {len(covers)} meals" if covers else "")


def _prep(context, params) -> str:
    from core.fitness_missions import ensure

    recipe = context.kitchen.get_recipe(str(params["recipe_id"]))
    _fit(context).add_prep(_day(params), recipe.recipe_id, _number(params.get("servings") or recipe.servings, "Servings"),
                           _covers(params))
    ensure(context)
    return "Meal prep planned."


def _describe_prep_done(context, params) -> str:
    session = next((p for p in _fit(context).prep_sessions() if p["id"] == params.get("prep_id")), None)
    if session is None:
        raise ActionError("There's no prep session like that.")
    return "Mark this meal prep done"


def _prep_done(context, params) -> str:
    session = _fit(context).finish_prep(str(params["prep_id"]))
    if getattr(context, "kitchen", None) is not None and context.kitchen.get_recipe(session["recipe_id"]) is not None:
        context.kitchen.log_meal(session["recipe_id"], date.today().isoformat(),
                                 notes=f"Meal prep, {session['servings']:g} servings")  # made once, eaten over the week
    _after(context)
    return "Meal prep: done."


def _prep_session(context, params) -> dict:
    session = next((p for p in _fit(context).prep_sessions() if p["id"] == params.get("prep_id")), None)
    if session is None:
        raise ActionError("There's no prep session like that.")
    return session


def _describe_prep_delete(context, params) -> str:
    session = _prep_session(context, params)
    recipe = context.kitchen.get_recipe(session["recipe_id"]) if getattr(context, "kitchen", None) is not None else None
    covered = f" and the {len(session['covers'])} meals it covers" if session["covers"] else ""
    return f"Remove the prep session {_on_day(session['date'])}" + (f" ({recipe.name})" if recipe else "") + covered


def _prep_delete(context, params) -> str:
    from core.fitness_missions import ensure

    _fit(context).delete_prep(_prep_session(context, params)["id"])
    ensure(context)
    return "Prep session removed."


def _entry(entries: list, entry_id, what: str) -> dict:
    entry = next((e for e in entries if e["id"] == entry_id), None)
    if entry is None:
        raise ActionError(f"There's no {what} like that.")
    return entry


def _describe_food_delete(context, params) -> str:
    entry = _entry(_fit(context)._data["food"], params.get("entry_id"), "food entry")
    return f"Remove {entry['name']} ({entry['meal']}, {_say_day(entry['date'])}) from what you ate"


def _food_delete(context, params) -> str:
    fit = _fit(context)
    fit.delete_food(_entry(fit._data["food"], params.get("entry_id"), "food entry")["id"])
    _after(context)
    return "Removed."


def _describe_weigh_in_delete(context, params) -> str:
    entry = _entry(_fit(context).weigh_ins(), params.get("entry_id"), "weigh-in")
    return f"Remove the weigh-in of {entry['weight']:g} {entry['unit']} {_on_day(entry['date'])}"


def _weigh_in_delete(context, params) -> str:
    fit = _fit(context)
    fit.delete_weight(_entry(fit.weigh_ins(), params.get("entry_id"), "weigh-in")["id"])
    _after(context)
    return "Removed."


def _suggestions(context, params) -> list[dict]:
    from core.meal_plan import suggest_week

    picks = suggest_week(context, date.fromisoformat(_day(params)))
    if not picks:
        raise ActionError("There are no empty lunches or dinners this week, or no recipes to fill them.")
    return picks


def _describe_suggest(context, params) -> str:
    picks = _suggestions(context, params)
    names = sorted({p["name"] for p in picks})
    return f"Fill {len(picks)} meals this week from your recipes: " + ", ".join(names)


def _suggest(context, params) -> str:
    from core.fitness_missions import ensure

    fit = _fit(context)
    for pick in _suggestions(context, params):
        fit.plan_meal(pick["date"], pick["meal"], pick["recipe_id"], pick["servings"])
    ensure(context)
    return "Your week is planned."


def _describe_shop(context, params) -> str:
    from core.meal_plan import shopping_list

    items = shopping_list(context, date.fromisoformat(_day(params)))["items"]
    if not items:
        raise ActionError("The week's plan needs nothing the house doesn't already have.")
    flagged = [i["name"] for i in items if i["allergy"]]
    warning = f" ⚠ {', '.join(flagged)} matches an allergy." if flagged else ""
    return f"Add {len(items)} things to the grocery list for this week's meals.{warning}"


def _shop(context, params) -> str:
    from core.meal_plan import shopping_list

    items = shopping_list(context, date.fromisoformat(_day(params)))["items"]
    for item in items:
        context.kitchen.add_grocery_item(item["name"], item["quantity"], item["unit"])
    return f"Added {len(items)} things to the grocery list."


FITNESS_ACTIONS: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("fitness.weigh_in", "Log weight", {"weight": "the number", "unit": "lb or kg (optional)", "date": "optional"},
               _describe_weigh_in, _weigh_in),  # not for children: body weight isn't a kid's number to track
    ActionType("fitness.food", "Log food", {"meal": "breakfast/lunch/dinner/snack", "recipe_id": "a recipe, or",
                                            "name": "what it was", "servings": "default 1", "kcal": "optional",
                                            "protein_g": "optional", "carbs_g": "optional", "fat_g": "optional",
                                            "date": "optional"}, _describe_food, _food, True),
    ActionType("fitness.protein", "Log protein", {"grams": "how much", "name": "optional", "meal": "optional"},
               _describe_protein, _protein, True),
    ActionType("fitness.training_done", "Training done", {}, _describe_training, _training, True),
    ActionType("fitness.step", "Step done", {"step": "its number (1 first) or name"}, _describe_step, _step, True),
    ActionType("fitness.skill", "Log practice", {"skill": "e.g. Handstand", "step": "optional", "seconds": "a hold",
                                                 "minutes": "practice time", "date": "optional"},
               _describe_skill, _skill, True),
    ActionType("fitness.habit", "Done", {"habit": "/".join(HABITS), "date": "optional"}, _describe_habit, _habit, True),
    ActionType("fitness.plan", "Save plan", {"changes": "the parts of the plan to change"}, _describe_plan, _plan, True),
    ActionType("meal.plan", "Plan", {"date": "the day", "meal": "breakfast/lunch/dinner/snack",
                                     "recipe_id": "the recipe (none clears it)", "servings": "default 1"},
               _describe_plan_meal, _plan_meal, True),
    ActionType("meal.prep", "Plan prep", {"date": "the prep day", "recipe_id": "what to cook", "servings": "how many",
                                          "covers": "the meals it feeds: 2026-10-13:lunch, ..."},
               _describe_prep, _prep, True),
    ActionType("meal.prep_done", "Prep done", {"prep_id": "the prep session"}, _describe_prep_done, _prep_done, True),
    ActionType("meal.prep_delete", "Remove", {"prep_id": "the prep session"}, _describe_prep_delete, _prep_delete, True),
    ActionType("fitness.food_delete", "Remove", {"entry_id": "the food entry"}, _describe_food_delete, _food_delete, True),
    ActionType("fitness.weigh_in_delete", "Remove", {"entry_id": "the weigh-in"}, _describe_weigh_in_delete,
               _weigh_in_delete),
    ActionType("meal.suggest", "Plan my week", {"date": "any day of the week"}, _describe_suggest, _suggest, True),
    ActionType("meal.shop", "Add to grocery list", {"date": "any day of the week"}, _describe_shop, _shop),
    ActionType("fitness.milestone", "Reached it", {"milestone_id": "the milestone"}, _describe_milestone, _milestone, True),
)}
ACTION_TYPES.update(FITNESS_ACTIONS)
