"""
core.web_screens
==================

Kitchen, Workout and Real Estate on the web (2026-10-06, DEC-0017/0018):
everything the PC app's screens show, assembled here so `web/` holds no
logic. Served as `/api/kitchen` (and one recipe, `/api/kitchen/recipe/{id}`,
its amounts scaled to `?servings=` by scale_factor and scaled_amount),
`/api/workout` (with `weeks`, workouts and volume a week: weekly_training)
and `/api/real-estate` (a property's photo: `property_photo_url`);
changes are the action kinds in core/kitchen_actions.py,
core/workout_actions.py and core/estate_actions.py.

Figures come from the stores' own functions (what can I make, personal
records, equity, the mortgage payment), never a second calculation.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

RECENT_DAYS = 60
EXPIRING_DAYS = 3


def _values(record, item) -> dict:
    """A record's form values: each of its fields from the item."""
    data = asdict(item)
    return {f.name: data.get(f.name) for f in record.fields}


def _r(value) -> float:
    """A number rounded to cents (0 for nothing)."""
    return round(float(value or 0), 2)


# ------------------------------------------------------------------ Kitchen


def kitchen_page(context, today: Optional[date] = None) -> dict:
    """The data the Kitchen screen shows, assembled here (the web only draws it): recipes (what's missing for each, whether it can be made, times
    made, favourites, ratings, photos; locked ones with the mission that unlocks them), the pantry with what expires,
    the grocery list, meals logged, the forms, and the recipe being cooked in cook mode (`cooking`).
    """
    from core.kitchen_actions import RECORDS, form_spec, ingredients_text
    from core.kitchen_manager import days_until_expiration, recipe_missing_ingredients
    from core.person_settings import person_id

    today = today or date.today()
    kitchen = getattr(context, "kitchen", None)
    page = {"available": kitchen is not None, "forms": form_spec(), "as_of": today.isoformat()}
    if kitchen is None:
        return page
    pid = person_id(context)
    pantry = kitchen.all_pantry_items()
    favorites = set(kitchen.favorite_recipe_ids(pid)) if pid else set()
    unlockers: dict[str, str] = {}
    missions = getattr(context, "missions", None)
    if missions is not None:
        for m in missions.all_missions():
            if m.status != "completed":
                for recipe_id in m.recipe_unlocks:
                    unlockers.setdefault(recipe_id, m.name)

    recipes = []
    for r in kitchen.all_recipes():
        missing = recipe_missing_ingredients(r, pantry)
        stats = kitchen.get_recipe_user_stats(pid, r.recipe_id) if pid else None
        recipes.append({
            "id": r.recipe_id, "name": r.name, "category": r.category, "servings": r.servings,
            "minutes": (r.prep_time_minutes or 0) + (r.cook_time_minutes or 0),
            "calories": r.calories_per_serving, "ingredients": [i.get("name", "") for i in r.ingredients],
            "ingredients_text": ingredients_text(r.ingredients), "instructions": r.instructions, "source": r.source,
            "notes": r.notes, "locked": r.locked, "unlocked_by_mission": unlockers.get(r.recipe_id) if r.locked else None,
            "missing": missing, "makeable": not missing and bool(r.ingredients),
            "times_made": kitchen.times_made(r.recipe_id), "last_made": kitchen.last_made_date(r.recipe_id),
            "favorite": r.recipe_id in favorites, "rating": getattr(stats, "rating", None),
            "photo": recipe_photo_url(kitchen, r),
            "values": _values(RECORDS["recipe"], r),
        })
    page["recipes"] = sorted(recipes, key=lambda x: (x["locked"], not x["favorite"], x["name"].lower()))

    items = []
    for p in pantry:
        days = days_until_expiration(p, today)
        items.append({"id": p.item_id, "name": p.name, "quantity": p.quantity, "unit": p.unit, "category": p.category,
                      "expires_in": days, "expiring": days is not None and days <= EXPIRING_DAYS,
                      "values": _values(RECORDS["pantry"], p)})
    page["pantry"] = sorted(items, key=lambda x: (not x["expiring"], x["category"], x["name"].lower()))

    names = {r.recipe_id: r.name for r in kitchen.all_recipes()}
    page["grocery"] = [{"id": g.item_id, "name": g.name, "quantity": g.quantity, "unit": g.unit, "checked": g.checked,
                        "for_recipe": names.get(g.source_recipe_id)} for g in kitchen.all_grocery_items()]
    since = (today - timedelta(days=RECENT_DAYS)).isoformat()
    meals = sorted((m for m in kitchen.all_meal_log_entries() if (m.date or "") >= since),
                   key=lambda m: m.date or "", reverse=True)
    page["meals"] = [{"id": m.entry_id, "date": m.date, "recipe": names.get(m.recipe_id, "a meal"),
                      "recipe_id": m.recipe_id, "notes": m.notes} for m in meals]
    page["suggestions"] = [x for x in page["recipes"] if not x["locked"] and x["ingredients"]
                           and len(x["missing"]) <= 2][:8]
    page["suggestions"].sort(key=lambda x: len(x["missing"]))
    page["counts"] = {"recipes": len(recipes), "pantry": len(items), "expiring": sum(i["expiring"] for i in items),
                      "grocery": sum(not g["checked"] for g in page["grocery"])}
    page["cooking"] = _cooking(context)  # the recipe being cooked in cook mode, or None (DEC-0113)
    return page


def _cooking(context):
    """Cook mode's session for the Kitchen and recipe screens (core/cooking_actions.screen), or None; a failure
    there never hides the page."""
    try:
        from core.cooking_actions import screen

        return screen(context)
    except Exception:
        log.exception("Kitchen: cook mode unavailable")
        return None


def recipe_steps(instructions: str) -> list[str]:
    """Pure logic. A recipe's instructions as numbered steps: one a line,
    or split at "1." / "2)" numbers when written as one paragraph; the
    numbers themselves are dropped (the screen numbers them)."""
    import re

    text = (instructions or "").strip()
    if not text:
        return []
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) == 1:
        lines = re.split(r"\s+(?=(?:step\s*)?\d+[.):]\s)", text, flags=re.IGNORECASE)
    return [re.sub(r"^\s*(?:step\s*)?\d+[.):]\s*|^\s*[-*•]\s*", "", l, flags=re.IGNORECASE).strip() for l in lines
            if l.strip()]


def scale_factor(recipe_servings, servings) -> tuple[int, float]:
    """Pure logic. The servings a recipe is shown for and the factor its amounts scale by: the asked-for servings
    (1 to 100) over the recipe's own; the recipe's own and 1 when none is asked or it can't be read."""
    own = max(1, int(recipe_servings or 1))
    try:
        want = int(servings) if servings not in (None, "") else own
    except (TypeError, ValueError):
        want = own
    want = max(1, min(100, want))
    return want, want / own


def scaled_amount(quantity, unit: str, factor: float) -> str:
    """Pure logic. An ingredient's amount for the servings shown, as a cook reads it (core/units.kitchen_amount:
    "1 ½ cups"); "" when it has no number."""
    from core.units import kitchen_amount

    try:
        q = float(quantity)
    except (TypeError, ValueError):
        return ""
    return kitchen_amount(q * factor, unit) if q > 0 else ""


def recipe_page(context, recipe_id: str, today: Optional[date] = None, servings=None) -> dict:
    """One recipe, opened from a meal card (Zac, 2026-10-14): what it is,
    its nutrition per serving, each ingredient with whether the house has
    it (in the pantry, already on the grocery list, or to buy), the steps,
    and when it's planned next. "Schedule meal" is meal.plan; "Add to
    grocery list" is grocery.from_recipe, adding exactly `to_buy`. Also the
    recipe being cooked in cook mode (`cooking`, DEC-0113), if any. With
    `servings`, each ingredient's `amount` is scaled to that many (the
    canvas's servings stepper, scale_factor); `shown_servings` says how many."""
    from core.fitness_manager import MEALS
    from core.kitchen_actions import RECORDS, form_spec
    from core.kitchen_manager import ingredient_key, recipe_missing_ingredients
    from core.nutrition import recipe_facts
    from core.person_settings import person_id

    today = today or date.today()
    kitchen = getattr(context, "kitchen", None)
    recipe = kitchen.get_recipe(recipe_id) if kitchen is not None else None
    if recipe is None:
        return {"available": False}
    pid = person_id(context)
    shown_servings, factor = scale_factor(recipe.servings, servings)
    missing = {ingredient_key(n) for n in recipe_missing_ingredients(recipe, kitchen.all_pantry_items())}
    listed = {ingredient_key(g.name) for g in kitchen.all_grocery_items()}
    from core.kitchen_blueprint import check

    have_of = {r["name"]: r["have"] for r in check(recipe, kitchen.all_pantry_items())}
    ingredients = []
    for ingredient in recipe.ingredients:
        name = str(ingredient.get("name", "")).strip()
        if not name:
            continue
        key = ingredient_key(name)
        status = "have" if key not in missing else "on_list" if key in listed else "to_buy"
        have = have_of.get(name)
        ingredients.append({"name": name, "quantity": ingredient.get("quantity") or None,
                            "unit": ingredient.get("unit", ""), "status": status,
                            "amount": scaled_amount(ingredient.get("quantity"), ingredient.get("unit", ""), factor),
                            "have": f"{have:g} {ingredient.get('unit', '')}".strip() if have is not None else None})
    facts = recipe_facts(recipe)
    unlocker = None
    if recipe.locked and getattr(context, "missions", None) is not None:
        unlocker = next((m.name for m in context.missions.all_missions()
                         if m.status != "completed" and recipe.recipe_id in m.recipe_unlocks), None)
    scheduled = []
    fit = getattr(context, "fitness", None)
    if fit is not None:
        for offset in range(14):
            day = (today + timedelta(days=offset)).isoformat()
            for meal, slot in fit.planned(day).items():
                if slot.get("recipe_id") == recipe.recipe_id:
                    scheduled.append({"date": day, "meal": meal, "servings": slot.get("servings", 1),
                                      "eaten": meal in fit.eaten_planned(day)})
        scheduled.sort(key=lambda x: (x["date"], MEALS.index(x["meal"])))
    category = (recipe.category or "").lower()
    stats = kitchen.get_recipe_user_stats(pid, recipe.recipe_id) if pid else None
    made = sorted(m.date for m in kitchen.all_meal_log_entries() if m.recipe_id == recipe.recipe_id and m.date)
    others = [v for who, v in kitchen.recipe_ratings(recipe.recipe_id).items() if who != pid]
    eaten = fit.food_for_recipe(recipe.recipe_id) if fit is not None else []
    return {
        "available": True, "as_of": today.isoformat(), "id": recipe.recipe_id, "name": recipe.name,
        "category": recipe.category, "servings": recipe.servings, "shown_servings": shown_servings,
        "prep_minutes": recipe.prep_time_minutes or 0,
        "cook_minutes": recipe.cook_time_minutes or 0, "source": recipe.source, "notes": recipe.notes,
        "steps": recipe_steps(recipe.instructions), "ingredients": ingredients, "cooking": _cooking(context),
        "to_buy": [i["name"] for i in ingredients if i["status"] == "to_buy"],
        "nutrition": {**{k: facts.get(k) for k in ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")},
                      "source": facts["source"], "not_found": facts["not_found"], "no_amount": facts["no_amount"],
                      "to_taste": facts["to_taste"]},
        "locked": recipe.locked, "unlocked_by_mission": unlocker,
        "favorite": pid is not None and recipe.recipe_id in set(kitchen.favorite_recipe_ids(pid)),
        "rating": getattr(stats, "rating", None), "times_made": kitchen.times_made(recipe.recipe_id),
        "last_made": kitchen.last_made_date(recipe.recipe_id),
        "stats": {  # the household's cooking and this person's own rating and eating (Zac, 2026-10-14)
            "rating": getattr(stats, "rating", None), "can_rate": bool(pid),
            "others_rated": len(others), "others_average": round(sum(others) / len(others), 1) if others else None,
            "times_made": len(made), "first_made": made[0] if made else None, "last_made": made[-1] if made else None,
            "made_last_30_days": sum(1 for d in made if d > (today - timedelta(days=30)).isoformat()),
            "times_eaten": len(eaten), "servings_eaten": round(sum(float(f.get("servings") or 1) for f in eaten), 1)},
        "can_schedule": fit is not None and not recipe.locked, "scheduled": scheduled,
        "meals": list(MEALS), "default_meal": category if category in MEALS else "dinner",
        "values": _values(RECORDS["recipe"], recipe), "ingredients_text": _ingredients_text(recipe), "forms": form_spec(),
        "photo": recipe_photo_url(kitchen, recipe),
    }


def recipe_photo_url(kitchen, recipe) -> str:
    """Where a screen fetches the recipe's photo ("" for none); the version
    changes when the photo does, so a new picture is never shown stale."""
    path = kitchen.recipe_photo_path(recipe.recipe_id) if kitchen is not None else None
    return f"/api/kitchen/recipe/{recipe.recipe_id}/photo?v={int(path.stat().st_mtime)}" if path else ""


def _ingredients_text(recipe) -> str:
    """A recipe's ingredients as the text its form edits."""
    from core.kitchen_actions import ingredients_text

    return ingredients_text(recipe.ingredients)


# ------------------------------------------------------------------ Workout


def weekly_training(sessions, today: date, weeks: int = 8) -> list[dict]:
    """Pure logic (given sessions). The canvas's Workout progress: each of the last `weeks` weeks (Monday first, oldest
    first) with its workouts, minutes, sets and volume (reps × weight, for sets with both), and each figure's share of
    the busiest week (0 to 100) for its bar."""
    this_monday = today - timedelta(days=today.weekday())
    rows = []
    for i in range(weeks - 1, -1, -1):
        start = this_monday - timedelta(days=7 * i)
        end = (start + timedelta(days=6)).isoformat()
        in_week = [s for s in sessions if start.isoformat() <= (s.date or "") <= end]
        volume = 0.0
        sets = 0
        for s in in_week:
            for st in s.sets_logged:
                sets += 1
                try:
                    volume += float(st.get("reps") or 0) * float(st.get("weight") or 0)
                except (TypeError, ValueError):
                    pass
        rows.append({"week": start.isoformat(), "label": f"{start.strftime('%b')} {start.day}", "workouts": len(in_week),
                     "minutes": _r(sum(s.duration_minutes or 0 for s in in_week)), "sets": sets, "volume": round(volume)})
    for key in ("workouts", "volume"):
        top = max((r[key] for r in rows), default=0)
        for r in rows:
            r[key + "_pct"] = round(r[key] / top * 100) if top else 0
    return rows


def _streak_days(sessions, today: date) -> int:
    """Pure logic (given sessions). Days in a row, ending today or yesterday, with a workout."""
    days = {s.date for s in sessions if s.date}
    day = today if today.isoformat() in days else today - timedelta(days=1)
    count = 0
    while day.isoformat() in days:
        count += 1
        day -= timedelta(days=1)
    return count


def workout_page(context, today: Optional[date] = None) -> dict:
    """The data the Workout screen shows, assembled here (the web only draws it): exercises with their records and progress, sessions newest first (each
    summarised by exercise, reps and sets), this week's count and minutes, the streak, the last eight weeks' workouts
    and volume (`weeks`, for Progress's bars), today's daily missions, and the forms.
    """
    from core.workout_actions import RECORDS, form_spec

    today = today or date.today()
    workout = getattr(context, "workout", None)
    page = {"available": workout is not None, "forms": form_spec(), "as_of": today.isoformat()}
    if workout is None:
        return page
    exercises = {e.exercise_id: e for e in workout.all_exercises()}
    page["exercises"] = [{"id": e.exercise_id, "name": e.name, "category": e.category, "equipment": e.equipment,
                          "notes": e.notes, "pr": workout.personal_record_for(e.exercise_id),
                          "progress": workout.weight_progression_for(e.exercise_id)[-8:],
                          "values": _values(RECORDS["exercise"], e)}
                         for e in sorted(exercises.values(), key=lambda e: e.name.lower())]
    # Workout templates are gone (Zac, 2026-10-16); a session logged with one long ago keeps its name in History.
    templates = {t.template_id: t.name for t in workout.all_templates()}

    def summary(session) -> str:
        by_exercise: dict[str, list] = {}
        for s in session.sets_logged:
            by_exercise.setdefault(s.get("exercise_id"), []).append(s)
        parts = []
        for exercise_id, sets in by_exercise.items():
            name = getattr(exercises.get(exercise_id), "name", "an exercise")
            reps = sum(int(s.get("reps") or 0) for s in sets)
            parts.append(f"{name} {reps} reps · {len(sets)} set{'s' if len(sets) != 1 else ''}")
        return "; ".join(parts) or (templates.get(session.template_id) or "A session")

    # newest first; on the same day, the one logged last
    sessions = [s for _, s in sorted(enumerate(workout.all_sessions()), key=lambda x: (x[1].date or "", x[0]), reverse=True)]
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    page["sessions"] = [{"id": s.session_id, "date": s.date, "template": templates.get(s.template_id),
                         "minutes": s.duration_minutes, "sets": len(s.sets_logged), "summary": summary(s), "notes": s.notes}
                        for s in sessions[:60]]
    page["latest"] = page["sessions"][0] if page["sessions"] else None
    this_week = [s for s in sessions if (s.date or "") >= week_start]
    page["stats"] = {"this_week": len(this_week), "minutes_this_week": _r(sum(s.duration_minutes for s in this_week)),
                     "streak": _streak_days(sessions, today), "total": len(sessions)}
    page["weeks"] = weekly_training(sessions, today)  # Progress: workouts and volume a week (the canvas, DEC-0113)

    page["daily_missions"] = []
    missions, recurring = getattr(context, "missions", None), getattr(context, "recurring_missions", None)
    if missions is not None:
        for m in missions.all_missions():
            if m.recurring_kind != "daily" or m.status == "abandoned" or m.occurrence_key != today.isoformat():
                continue
            target = sum(o.target for o in m.objectives) or 1
            progress = sum(min(missions.objective_progress(m.mission_id, i) or 0, o.target) for i, o in enumerate(m.objectives))
            streak = recurring.current_streak_for_template(m.recurring_template_id, today) \
                if recurring is not None and m.recurring_template_id else 0
            page["daily_missions"].append({"id": m.mission_id, "name": m.name, "progress": progress, "target": target,
                                           "done": m.status == "completed", "streak": streak,
                                           "template_id": m.recurring_template_id})
    return page


# ------------------------------------------------------------------ Real Estate


def property_badge(status: str, rent: float, income_month: float) -> dict:
    """Pure logic. The word on a property's card and its tone (the design canvas's Real Estate, DEC-0113): a rented
    property with its rent set and no rent recorded yet this month says "Rent Due" (amber: it needs you);
    otherwise its status, green when it's rented or lived in, amber when it's waiting on something (for rent, for
    sale, being renovated, vacant), plain for the rest. A vacancy is never shown as an error."""
    if status == "Rented" and rent and income_month <= 0:
        return {"text": "Rent Due", "tone": "attention"}
    tone = ("ok" if status in ("Rented", "Owner Occupied") else
            "attention" if status in ("Vacant", "For Rent", "For Sale", "Under Renovation") else "")
    return {"text": status or "", "tone": tone}


def property_photo_url(real_estate, prop) -> str:
    """Where a screen fetches the property's photo ("" for none); the link changes with the file, so a new photo is
    never shown stale."""
    path = real_estate.property_photo_path(prop.property_id) if real_estate is not None else None
    return f"/api/real-estate/property/{prop.property_id}/photo?v={path.name}" if path else ""


def estate_page(context, today: Optional[date] = None) -> dict:
    """The data the Real Estate screen shows, assembled here (the web only draws it): each property with its value, loan and payment, this month's income and
    expenses and the year's net operating income (with a budget), its upkeep tasks, the missions linked to it, and
    the word on its card (`property_badge`: Rent Due, Rented...), its photo (`property_photo_url`), and for a rental or investment its straight-line
    depreciation a year and so far (an estimate, not a tax figure), and once sold, what the sale came to (`sale`).
    """
    from core import links as links_module
    from core.estate_actions import RECORDS, form_spec
    from core.real_estate_manager import (accumulated_depreciation, annual_depreciation, equity, has_loan_terms,
                                          monthly_payment, sale_summary)
    from core.region import currency_symbol_for

    today = today or date.today()
    real_estate = getattr(context, "real_estate", None)
    page = {"available": real_estate is not None, "forms": form_spec(), "as_of": today.isoformat(),
            "currency_symbol": currency_symbol_for(context)}
    if real_estate is None:
        return page
    month_start = today.replace(day=1).isoformat()
    year_start = today.replace(month=1, day=1).isoformat()
    maintenance = getattr(context, "maintenance", None)
    missions = getattr(context, "missions", None)
    properties = []
    for p in real_estate.all_properties():
        payment = monthly_payment(p) if has_loan_terms(p) else 0.0
        income_month = expenses_month = noi_year = 0.0
        if getattr(context, "budget", None) is not None:
            income_month = sum(e.amount for e in real_estate.income_for_property(p.property_id, month_start, today.isoformat()))
            expenses_month = sum(e.amount for e in real_estate.expenses_for_property(p.property_id, month_start, today.isoformat()))
            noi_year = real_estate.net_operating_income(p.property_id, year_start, today.isoformat())
        tasks = []
        asset = maintenance.get_asset(p.maintenance_asset_id) if maintenance is not None and p.maintenance_asset_id else None
        if asset is not None:
            from core.web_equipment import _order, _task_row

            tasks = sorted((_task_row(context, t, asset, today) for t in maintenance.tasks_for_asset(asset.asset_id)
                            if not (t.is_meter_task and t.meter_interval is None)), key=_order)
        related = []
        if missions is not None:
            ref = f"property:{p.property_id}"
            for link in links_module.links_for(context, ref):
                other = link.target if link.source == ref else link.source
                if other.startswith("mission:"):
                    mission = missions.get_mission(other.split(":", 1)[1])
                    if mission is not None:
                        related.append({"id": mission.mission_id, "name": mission.name, "status": mission.status})
        properties.append({
            "id": p.property_id, "name": p.name, "type": p.property_type, "status": p.status, "location": p.location,
            "rent": _r(p.monthly_rent), "value": _r(p.current_value), "owed": _r(p.mortgage_balance), "equity": _r(equity(p)),
            "payment": _r(payment), "cash_flow": _r(p.monthly_rent - payment) if p.monthly_rent else None,
            "income_month": _r(income_month), "expenses_month": _r(expenses_month), "noi_year": _r(noi_year),
            "asset_id": asset.asset_id if asset is not None else None, "tasks": tasks, "missions": related,
            "notes": p.notes, "values": _values(RECORDS["property"], p), "photo": property_photo_url(real_estate, p),
            "badge": property_badge(p.status, p.monthly_rent, income_month),
            # straight-line, rentals and investments only (core/real_estate_manager.py): an estimate, not a tax figure
            "depreciation": {"year": _r(annual_depreciation(p)), "so_far": _r(accumulated_depreciation(p, today))}
            if annual_depreciation(p) > 0 and not p.sale_date else None,
            # once sold: what it came to (core/real_estate_manager.sale_summary; the gain an estimate, not a tax figure)
            "sale": {k: (_r(v) if isinstance(v, float) else v) for k, v in sale_summary(p).items()} if p.sale_date else None,
        })
    page["properties"] = properties
    page["totals"] = {"count": len(properties), "equity": _r(sum(p["equity"] for p in properties)),
                      "rent": _r(sum(p["rent"] for p in properties)),
                      "cash_flow": _r(sum(p["cash_flow"] or 0 for p in properties)),
                      "attention": sum(1 for p in properties for t in p["tasks"] if t["needs_attention"])}
    return page
