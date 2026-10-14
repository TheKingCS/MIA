"""
core.plan_import
==================

"Paste a plan" (2026-10-14, Zac: "work with Muse to fill out my workouts,
goals, meals, nutrition"). A whole fitness plan and its recipes as one
block of plain text, the kind Muse (or anyone) writes in a chat and the
person pastes into My plan on their phone. The person's details go from
that chat straight into MIA on their device, never through the repo
(DEC-0002).

The format (docs/PLAN_TEXT_FORMAT.md has a full placeholder example):

    GOALS
    Protein: 170 g
    Calories: 2300
    Goal weight: 175 lb by 2027-03-01
    Workouts a week: 3
    Weigh-in days: Mon, Thu

    TRAINING
    Days: Mon, Wed, Fri
    Day: Push
    Dips 3x8
    Day: Pull
    Pull-ups 5x5

    SKILL: Handstand
    Minutes a day: 12
    Drills: Wrist prep, Wall walks
    Wall hold 60s

    MILESTONES
    60 s wall handstand

    MEALS
    Packed lunch: yes
    Prep day: Sun
    Allergies: peanuts
    Lunch rotation: Turkey chili

    RECIPE: Turkey chili
    Category: Lunch
    Servings: 6
    Prep: 15 min
    Cook: 60 min
    Ingredients:
    2 lb ground turkey
    Steps:
    Brown the turkey.

Headings are case-blind and the colons optional. Only the parts in the
text change: no TRAINING section leaves the training as it was; a
TRAINING section with days replaces the rotation. A recipe with the
same name as one in the Kitchen is updated, not duplicated. Lines MIA
can't place are listed back, never silently dropped. Applying it is one
action, `plan.import`, so one "undo" takes it all back.
"""

from __future__ import annotations

import re
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

_HEADING = re.compile(r"^\s*#*\s*(goals?|targets?|training day|training|workouts?|skills?|milestones?|meals?|recipes?|day)\b"
                      r"\s*:?\s*(.*?)\s*$", re.IGNORECASE)
_KEY = re.compile(r"^\s*([A-Za-z][A-Za-z '\-/]*?)\s*:\s*(.*?)\s*$")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


_BULLET = re.compile(r"^\s*(?:(?:[-•*]|\[[ xX]?\]|\d+[.)])\s+)+")


def _item(line: str) -> str:
    """Pure logic. A list line without its bullet or number ("1. Dips 3x8" -> "Dips 3x8")."""
    return _BULLET.sub("", line).strip()


def _number(text: str) -> Optional[str]:
    found = _NUMBER.search(text.replace(",", ""))
    return found.group(0) if found else None


def _minutes(text: str) -> Optional[str]:
    """ "1 hr 15 min" -> "75"; "45 min" -> "45"."""
    hours = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b", text, re.IGNORECASE)
    mins = re.search(r"(\d+)\s*(?:m|min|mins|minutes)\b", text, re.IGNORECASE)
    if hours or mins:
        return str(round(float(hours.group(1) if hours else 0) * 60 + int(mins.group(1) if mins else 0)))
    return _number(text)


def parse(text: str) -> dict:
    """Pure logic. The text as {plan: changes for fitness.plan, recipes:
    [...], lunch_rotation: [recipe names], problems: [lines not understood]}."""
    plan: dict = {}
    recipes: list[dict] = []
    lunches: list[str] = []
    problems: list[str] = []
    section, day, skill, recipe, part = "", None, None, None, ""
    gap, listed = False, False  # a blank line before this one; the recipe's steps were a numbered/bulleted list
    for raw in (text or "").splitlines():
        line = re.sub(r"^#+\s*", "", raw.strip().strip("*").strip())
        if not line or set(line) <= set("-=_#*"):
            gap = True
            continue
        bulleted = bool(_BULLET.match(line))
        line = _item(line)
        if not line:
            continue
        if section == "recipe" and part == "steps" and gap and listed and not bulleted and not _HEADING.match(line):
            section = ""  # after a numbered list and a blank line, plain text is the chat talking, not a step
        gap = False
        heading = _HEADING.match(line)
        word = heading.group(1).lower() if heading else ""
        rest = heading.group(2) if heading else ""
        if heading and (not rest or word in ("day", "training day", "skill", "skills", "recipe", "recipes")
                        or rest.startswith(":") or line.rstrip().endswith(":")):
            if word in ("goal", "goals", "target", "targets"):
                section = "goals"
                continue
            if word in ("training", "workout", "workouts"):
                section, day = "training", None
                continue
            if word in ("milestone", "milestones"):
                section = "milestones"
                continue
            if word in ("meal", "meals"):
                section = "meals"
                continue
            if word in ("day", "training day") and rest:
                section = "training"
                day = {"name": rest.lstrip(": "), "exercises": []}
                plan.setdefault("training", {}).setdefault("rotation", []).append(day)
                continue
            if word in ("skill", "skills") and rest:
                section, part = "skill", ""
                name = rest.lstrip(": ")
                per_day = re.search(r"\(?\s*(\d+)\s*(?:min|minutes)[^)]*\)?", name, re.IGNORECASE)
                skill = {"skill": re.sub(r"[,(]?\s*\d+\s*(?:min|minutes).*$", "", name, flags=re.IGNORECASE).strip(" ,("),
                         "daily_minutes": per_day.group(1) if per_day else "", "practice": [], "steps": []}
                plan.setdefault("skill_tree", []).append(skill)
                continue
            if word in ("skill", "skills"):
                section = "skills_heading"
                continue
            if word in ("recipe", "recipes") and rest:
                section, part, listed = "recipe", "", False
                recipe = {"name": rest.lstrip(": "), "ingredients": [], "steps": []}
                recipes.append(recipe)
                continue
            if word in ("recipe", "recipes"):
                section = "recipes_heading"
                continue
        key = _KEY.match(line)
        name, value = (key.group(1).lower().strip(), key.group(2)) if key else ("", "")
        if section == "goals" and key:
            targets = plan.setdefault("targets", {})
            if re.search(r"\bper\b|/\s*(lb|kg)", value, re.IGNORECASE):
                problems.append(raw.strip() + " (MIA needs a daily number, like 170 g)")
            elif "protein" in name:
                targets["protein_g"] = _number(value) or ""
            elif "calor" in name or name in ("kcal", "energy"):
                targets["calories"] = _number(value) or ""
            elif "weigh" in name and ("day" in name or "in" in name.split()):
                targets["weigh_in_days"] = value
            elif "weight" in name or name == "goal":
                targets["target_weight"] = _number(value) or ""
                unit = re.search(r"\b(lb|lbs|pounds?|kg|kilos?)\b", value, re.IGNORECASE)
                if unit:
                    plan["units"] = "kg" if unit.group(1).lower().startswith("k") else "lb"
                by = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", value)
                if by:
                    targets["target_date"] = by.group(1)
            elif "workout" in name or "session" in name:
                targets["workouts_per_week"] = _number(value) or ""
            elif "unit" in name:
                plan["units"] = "kg" if value.lower().startswith("k") else "lb"
            elif "date" in name or name in ("by", "goal date"):
                targets["target_date"] = value
            elif "approach" in name or "method" in name:
                targets["calorie_approach"] = value
            else:
                problems.append(raw.strip())
        elif section == "training":
            if key and "day" in name and day is None:
                plan.setdefault("training", {})["days"] = value
            elif day is not None:
                day["exercises"].append(_item(line))
            else:
                problems.append(raw.strip())
        elif section == "skill" and skill is not None:
            if key and ("minute" in name or "per day" in name or name == "daily"):
                skill["daily_minutes"] = _number(value) or ""
            elif key and name in ("drills", "practice", "drill"):
                skill["practice"] = [d.strip() for d in value.split(",") if d.strip()]
            elif key and name in ("steps", "progression", "progressions"):
                if value:
                    skill["steps"].append(value)
            else:
                skill["steps"].append(_item(line))
        elif section == "milestones":
            plan.setdefault("milestones", []).append({"name": _item(line)})
        elif section == "meals" and key:
            meals = plan.setdefault("meals", {})
            if "lunch" in name and ("pack" in name or "work" in name):
                meals["packed_lunch"] = value.lower().startswith(("y", "t", "1"))
            elif "prep" in name:
                meals["prep_day"] = value
            elif "rotation" in name or ("lunch" in name and "," in value) or name == "lunches":
                lunches.extend(n.strip() for n in value.split(",") if n.strip())
            elif name in ("diet", "style"):
                meals.setdefault("preferences", {})["diet"] = value
            elif "allerg" in name:
                meals.setdefault("preferences", {})["allergies"] = "" if value.lower() in ("none", "no", "-") else value
            elif "dislike" in name or "don't eat" in name or "dont eat" in name or "avoid" in name:
                meals.setdefault("preferences", {})["dislikes"] = "" if value.lower() in ("none", "no", "-") else value
            else:
                problems.append(raw.strip())
        elif section == "recipe" and recipe is not None:
            if key and name in ("ingredients", "ingredient"):
                part = "ingredients"
                if value:
                    recipe["ingredients"].append(value)
            elif key and name in ("steps", "instructions", "method", "directions"):
                part = "steps"
                if value:
                    recipe["steps"].append(value)
            elif key and part == "" and name in ("category", "meal", "type"):
                recipe["category"] = value.capitalize()
            elif key and part == "" and name in ("servings", "serves", "makes"):
                recipe["servings"] = _number(value) or ""
            elif key and part == "" and name in ("prep", "prep time"):
                recipe["prep_time_minutes"] = _minutes(value) or ""
            elif key and part == "" and name in ("cook", "cook time"):
                recipe["cook_time_minutes"] = _minutes(value) or ""
            elif key and part == "" and ("calor" in name or name == "kcal"):
                recipe["calories_per_serving"] = _number(value) or ""
            elif key and part == "" and name in ("protein", "carbs", "fat"):
                recipe[{"protein": "protein_g", "carbs": "carbs_g", "fat": "fat_g"}[name]] = _number(value) or ""
            elif key and part == "" and name in ("source", "notes", "note"):
                recipe["source" if name == "source" else "notes"] = value
            elif part == "ingredients":
                recipe["ingredients"].append(_item(line))
            elif part == "steps":
                listed = listed or bulleted
                recipe["steps"].append(line)
            else:
                problems.append(raw.strip())
        else:
            problems.append(raw.strip())
    return {"plan": plan, "recipes": recipes, "lunch_rotation": lunches, "problems": problems}


# ------------------------------------------------------------------ the action


def _read(context, params) -> dict:
    if getattr(context, "fitness", None) is None:
        raise ActionError("Plans aren't set up on this MIA.")
    found = parse(str(params.get("text") or ""))
    if not found["plan"] and not found["recipes"] and not found["lunch_rotation"]:
        raise ActionError("MIA couldn't find a plan in that text. It needs headings like GOALS, TRAINING, "
                          "SKILL: Handstand, MILESTONES, MEALS or RECIPE: Turkey chili.")
    if found["recipes"] and getattr(context, "kitchen", None) is None:
        raise ActionError("Recipes need the Kitchen, which isn't set up on this MIA.")
    known = {r.name.strip().lower() for r in context.kitchen.all_recipes()} if getattr(context, "kitchen", None) else set()
    pasted = {r["name"].strip().lower() for r in found["recipes"]}
    missing = [n for n in found["lunch_rotation"] if n.strip().lower() not in known | pasted]
    if missing:
        raise ActionError("The lunch rotation names recipes MIA doesn't have: " + ", ".join(missing)
                          + ". Add them as RECIPE: sections in the same text.")
    from core.fitness_actions import _clean_plan

    if found["plan"]:
        _clean_plan(context, found["plan"])  # checks it now, so the summary never promises what can't be saved
    return found


def _describe(context, params) -> str:
    found = _read(context, params)
    plan, parts = found["plan"], []
    t = plan.get("targets") or {}
    goals = [f"protein {t['protein_g']} g" if t.get("protein_g") else "",
             f"{t['calories']} kcal" if t.get("calories") else "",
             f"goal weight {t['target_weight']}" if t.get("target_weight") else "",
             f"{t['workouts_per_week']} workouts a week" if t.get("workouts_per_week") else ""]
    if any(goals):
        parts.append("goals (" + ", ".join(g for g in goals if g) + ")")
    training = plan.get("training") or {}
    if training.get("rotation"):
        count = len(training["rotation"])
        parts.append(f"{count} training day{'s' if count != 1 else ''} ({', '.join(d['name'] for d in training['rotation'])})")
    elif training.get("days"):
        parts.append("training days")
    if plan.get("skill_tree"):
        parts.append("skills: " + ", ".join(s["skill"] for s in plan["skill_tree"]))
    if plan.get("milestones"):
        parts.append(f"{len(plan['milestones'])} milestone{'s' if len(plan['milestones']) != 1 else ''}")
    if plan.get("meals") or found["lunch_rotation"]:
        parts.append("meals")
    if found["recipes"]:
        known = {r.name.strip().lower() for r in context.kitchen.all_recipes()}
        new = [r["name"] for r in found["recipes"] if r["name"].strip().lower() not in known]
        updated = [r["name"] for r in found["recipes"] if r["name"].strip().lower() in known]
        if new:
            parts.append(f"add {len(new)} recipe{'s' if len(new) != 1 else ''} ({', '.join(new)})")
        if updated:
            parts.append(f"update {', '.join(updated)}")
    summary = "Set from the pasted plan: " + "; ".join(parts) + "."
    if found["problems"]:
        shown = found["problems"][:3]
        summary += f" MIA skipped {len(found['problems'])} line{'s' if len(found['problems']) != 1 else ''} it didn't understand: " \
                   + "; ".join(f"“{p}”" for p in shown) + ("…" if len(found["problems"]) > 3 else "")
    return summary


def _apply(context, params) -> str:
    from core.fitness_actions import _clean_plan
    from core.fitness_missions import ensure
    from core.kitchen_actions import parse_ingredients

    found = _read(context, params)
    kitchen = getattr(context, "kitchen", None)
    ids = {r.name.strip().lower(): r.recipe_id for r in kitchen.all_recipes()} if kitchen is not None else {}
    for r in found["recipes"]:
        fields = {k: r[k] for k in ("category", "source", "notes") if r.get(k)}
        for k in ("servings", "prep_time_minutes", "cook_time_minutes"):
            if r.get(k):
                fields[k] = int(float(r[k]))
        for k in ("calories_per_serving", "protein_g", "carbs_g", "fat_g"):
            if r.get(k):
                fields[k] = float(r[k])
        if r["steps"]:
            fields["instructions"] = "\n".join(r["steps"])
        existing = ids.get(r["name"].strip().lower())
        if existing is None:
            existing = kitchen.add_recipe(r["name"].strip(), **{k: v for k, v in fields.items()
                                                                 if k not in ("ingredients",)}).recipe_id
            ids[r["name"].strip().lower()] = existing
        elif fields:
            kitchen.update_recipe(existing, **fields)
        if r["ingredients"]:
            kitchen.update_recipe(existing, ingredients=parse_ingredients("\n".join(r["ingredients"])))
    plan = dict(found["plan"])
    if found["lunch_rotation"]:
        plan.setdefault("meals", {})["lunch_rotation"] = [ids[n.strip().lower()] for n in found["lunch_rotation"]]
    if plan.get("milestones"):  # keep the ones already reached
        before = {m.get("name", "").strip().lower(): m for m in context.fitness.plan.get("milestones") or []}
        plan["milestones"] = [{**before.get(m["name"].strip().lower(), {}), **m} for m in plan["milestones"]]
    if plan:
        context.fitness.update_plan(_clean_plan(context, plan))
    ensure(context)
    recipes = len(found["recipes"])
    return "Your plan is in." + (f" {recipes} recipe{'s' if recipes != 1 else ''} in the Kitchen." if recipes else "") \
        + " Say “undo that” to take it all back."


PLAN_IMPORT = ActionType("plan.import", "Use this plan", {"text": "the plan as text (GOALS, TRAINING, SKILL:, MEALS, RECIPE:)"},
                         _describe, _apply, True)
ACTION_TYPES[PLAN_IMPORT.kind] = PLAN_IMPORT
