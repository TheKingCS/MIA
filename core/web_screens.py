"""
core.web_screens
==================

Kitchen, Workout and Real Estate on the web (2026-10-06, DEC-0017/0018):
everything the PC app's screens show, assembled here so `web/` holds no
logic. Served as `/api/kitchen`, `/api/workout` and `/api/real-estate`;
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
    data = asdict(item)
    return {f.name: data.get(f.name) for f in record.fields}


def _r(value) -> float:
    return round(float(value or 0), 2)


# ------------------------------------------------------------------ Kitchen


def kitchen_page(context, today: Optional[date] = None) -> dict:
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
    return page


# ------------------------------------------------------------------ Workout


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
    page["templates"] = [{"id": t.template_id, "name": t.name, "notes": t.notes,
                          "exercises": [{"index": i, "name": getattr(exercises.get(x.get("exercise_id")), "name", "an exercise"),
                                         "sets": x.get("target_sets"), "reps": x.get("target_reps"),
                                         "weight": x.get("target_weight")} for i, x in enumerate(t.exercises)],
                          "values": _values(RECORDS["workout_template"], t)} for t in workout.all_templates()]
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


def estate_page(context, today: Optional[date] = None) -> dict:
    from core import links as links_module
    from core.estate_actions import RECORDS, form_spec
    from core.real_estate_manager import equity, has_loan_terms, monthly_payment
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
            "notes": p.notes, "values": _values(RECORDS["property"], p),
        })
    page["properties"] = properties
    page["totals"] = {"count": len(properties), "equity": _r(sum(p["equity"] for p in properties)),
                      "rent": _r(sum(p["rent"] for p in properties)),
                      "cash_flow": _r(sum(p["cash_flow"] or 0 for p in properties)),
                      "attention": sum(1 for p in properties for t in p["tasks"] if t["needs_attention"])}
    return page
