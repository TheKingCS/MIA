"""
core.fitness_manager
======================

A person's fitness plan and what they log against it (DEC-0020,
docs/KITCHEN_FITNESS_PLAN.md, Muse's H-0026): weigh-ins and their trend,
what they ate and its nutrition, timed skill practice (handstand holds in
seconds), and milestones. Personal (core/personal_data.py
PERSONAL_STORES): each person's own file, `fitness.json`, never shared.

**The plan** is Muse's schema (H-0026), with every value the person's:

    targets:    protein_g, calories, calorie_approach ("maintenance" /
                "deficit" / "surplus"), weigh_in_days ["Mon", "Thu"],
                target_weight, target_date, workouts_per_week
    training:   days ["Mon", "Wed", "Fri"], rotation [{name, template_id,
                exercises: [{name, sets, reps, hold_seconds}]}]
    skill_tree: [{skill, daily_minutes, practice: [names], steps:
                [{name, target_seconds | target_reps}]}]
    milestones: [{id, name, done_on}]
    meals:      packed_lunch, lunch_rotation [recipe ids], prep_day "Sun",
                preferences {dislikes, allergies, diet}
    units:      "lb" or "kg" (from the person's country until they choose)

The repo holds this shape and the logic; the numbers live on the device
(DEC-0002). Missions made from the plan: core/fitness_missions.py.

Never punitive (DEC-0014): a missed weigh-in or a heavier day is just a
point on a line; the trend is a 7-day average and a weekly rate, worded
plainly.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core import life_events
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEALS = ("breakfast", "lunch", "dinner", "snack")
NUTRIENTS = ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
KG_PER_LB = 0.45359237


def empty_plan() -> dict:
    return {"targets": {"protein_g": None, "calories": None, "calorie_approach": "", "weigh_in_days": [],
                        "target_weight": None, "target_date": None, "workouts_per_week": None},
            "training": {"days": [], "rotation": []},
            "skill_tree": [], "milestones": [],
            "meals": {"packed_lunch": False, "lunch_rotation": [], "prep_day": "",
                      "preferences": {"dislikes": [], "allergies": [], "diet": ""}},
            "units": ""}


def _merge(base: dict, extra: dict) -> dict:
    """Pure logic. `extra` over `base`, key by key, nested dicts merged."""
    out = dict(base)
    for key, value in (extra or {}).items():
        out[key] = _merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def convert(weight: float, unit: str, to: str) -> float:
    """Pure logic. A weight in `unit` ("lb"/"kg") as `to`."""
    if unit == to:
        return weight
    return weight * KG_PER_LB if to == "kg" else weight / KG_PER_LB


def trend(points: list[tuple[date, float]], today: date) -> dict:
    """Pure logic. The weight picture from (day, weight) points, oldest
    first: latest, the 7-day average, the weekly rate over the last 4
    weeks (least squares, needs 3 weigh-ins spread over a week), and the
    change since the first weigh-in."""
    if not points:
        return {"latest": None, "average_7d": None, "weekly_change": None, "since_start": None, "count": 0}
    recent = [w for d, w in points if d > today - timedelta(days=7)]
    window = [(d, w) for d, w in points if d > today - timedelta(days=28)]
    weekly = None
    if len(window) >= 3 and (window[-1][0] - window[0][0]).days >= 7:
        xs = [(d - window[0][0]).days for d, _ in window]
        ys = [w for _, w in window]
        mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
        spread = sum((x - mean_x) ** 2 for x in xs)
        if spread:
            weekly = round(7 * sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / spread, 2)
    return {"latest": points[-1][1], "latest_on": points[-1][0].isoformat(),
            "average_7d": round(sum(recent) / len(recent), 1) if recent else None,
            "weekly_change": weekly, "since_start": round(points[-1][1] - points[0][1], 1), "count": len(points)}


def eta(latest: Optional[float], weekly: Optional[float], target: Optional[float], today: date) -> Optional[str]:
    """Pure logic. When the trend reaches the target weight, or None
    (no target, no trend, or heading the other way)."""
    if latest is None or weekly in (None, 0) or target is None:
        return None
    gap = target - latest
    if gap == 0:
        return today.isoformat()
    if (gap > 0) != (weekly > 0):
        return None
    weeks = gap / weekly
    return (today + timedelta(days=round(weeks * 7))).isoformat() if weeks < 520 else None


def add_up(entries: list[dict]) -> dict:
    """Pure logic. Nutrient totals; a nutrient no entry knows stays None
    (unknown is not zero)."""
    totals: dict = {}
    for n in NUTRIENTS:
        known = [e[n] for e in entries if e.get(n) is not None]
        totals[n] = round(sum(known), 1) if known else None
    return totals


class FitnessManager:
    """`context.fitness`: one person's plan, weigh-ins, food and practice."""

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self.path = self.data_dir / "fitness.json"
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------ storage

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except (OSError, ValueError):
            log.exception("Couldn't read %s; starting fresh.", self.path)
            raw = {}
        self._data = {"plan": _merge(empty_plan(), raw.get("plan") or {}),
                      "weigh_ins": list(raw.get("weigh_ins") or []),
                      "food": list(raw.get("food") or []),
                      "skill_sessions": list(raw.get("skill_sessions") or []),
                      "training_done": list(raw.get("training_done") or []),
                      "training_steps": dict(raw.get("training_steps") or {}),  # date -> [step indexes done]
                      "habits": dict(raw.get("habits") or {}),
                      # date -> meal -> {recipe_id, servings, prep_id}: what's planned (core/meal_plan.py)
                      "meal_plan": dict(raw.get("meal_plan") or {}),
                      # [{id, date, recipe_id, servings, covers: ["2026-10-13:lunch", ...]}]
                      "prep": list(raw.get("prep") or [])}  # date (or week's Monday) -> ["lunch", "prep", ...]

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.path, json.dumps(self._data, indent=1, ensure_ascii=False), encoding="utf-8")

    def _record(self, type_: str, summary: str, payload: dict) -> None:
        life_events.record(self, type_, summary, [], payload)

    # ------------------------------------------------------------------ the plan

    @property
    def plan(self) -> dict:
        plan = json.loads(json.dumps(self._data["plan"]))
        plan["units"] = plan.get("units") or self.default_units()
        return plan

    def default_units(self) -> str:
        from core.region import country_of

        try:
            return "lb" if country_of(self.context) in ("US", "LR", "MM") else "kg"
        except Exception:
            return "lb"

    def update_plan(self, changes: dict) -> dict:
        """Merges `changes` into the plan (nested parts merge; lists replace)."""
        self._data["plan"] = _merge(self._data["plan"], changes or {})
        for milestone in self._data["plan"].get("milestones", []):
            milestone.setdefault("id", uuid.uuid4().hex[:8])
            milestone.setdefault("done_on", None)
        self._save()
        self._record("plan_changed", "Updated the fitness plan", {"parts": sorted((changes or {}).keys())})
        return self.plan

    # ------------------------------------------------------------------ weigh-ins

    def log_weight(self, weight: float, on: Optional[str] = None, unit: Optional[str] = None, note: str = "") -> dict:
        if not 20 <= float(weight) <= 1500:
            raise ValueError("That doesn't look like a body weight.")
        day = on or date.today().isoformat()
        entry = {"id": uuid.uuid4().hex[:10], "date": day, "weight": round(float(weight), 1),
                 "unit": unit or self.plan["units"], "note": note}
        self._data["weigh_ins"] = [w for w in self._data["weigh_ins"] if w["date"] != day] + [entry]
        self._data["weigh_ins"].sort(key=lambda w: w["date"])
        self._save()
        self._record("weigh_in", f"Weighed in at {entry['weight']:g} {entry['unit']}",
                     {"weight": entry["weight"], "unit": entry["unit"], "date": day})
        return entry

    def delete_weight(self, entry_id: str) -> None:
        self._data["weigh_ins"] = [w for w in self._data["weigh_ins"] if w["id"] != entry_id]
        self._save()

    def weigh_ins(self) -> list[dict]:
        return list(self._data["weigh_ins"])

    def weight_trend(self, today: Optional[date] = None) -> dict:
        today = today or date.today()
        units = self.plan["units"]
        points = [(date.fromisoformat(w["date"]), convert(w["weight"], w.get("unit", units), units))
                  for w in self._data["weigh_ins"] if w["date"] <= today.isoformat()]
        picture = trend(points, today)
        picture["units"] = units
        target = self.plan["targets"].get("target_weight")
        picture["target"] = target
        picture["on_track_for"] = eta(picture["latest"], picture["weekly_change"], target, today)
        return picture

    # ------------------------------------------------------------------ food

    def log_food(self, meal: str, name: str, nutrients: Optional[dict] = None, on: Optional[str] = None,
                 recipe_id: str = "", servings: float = 1.0, source: str = "quick", planned_id: str = "") -> dict:
        meal = meal if meal in MEALS else "snack"
        entry = {"id": uuid.uuid4().hex[:10], "date": on or date.today().isoformat(), "meal": meal, "name": name,
                 "recipe_id": recipe_id, "servings": servings, "source": source, "planned_id": planned_id}
        for n in NUTRIENTS:
            value = (nutrients or {}).get(n)
            entry[n] = round(float(value), 1) if value is not None else None
        self._data["food"].append(entry)
        self._save()
        protein = f", {entry['protein_g']:g} g protein" if entry["protein_g"] is not None else ""
        self._record("food_logged", f"Ate {name} ({meal}){protein}", {"meal": meal, "date": entry["date"],
                                                                        "recipe_id": recipe_id})
        return entry

    def delete_food(self, entry_id: str) -> None:
        self._data["food"] = [f for f in self._data["food"] if f["id"] != entry_id]
        self._save()

    def food_on(self, day: str) -> list[dict]:
        return [f for f in self._data["food"] if f["date"] == day]

    def day_totals(self, day: Optional[str] = None) -> dict:
        """What was eaten on a day, its totals, and the targets beside them."""
        day = day or date.today().isoformat()
        eaten = self.food_on(day)
        targets = self.plan["targets"]
        return {"date": day, "entries": eaten, "totals": add_up(eaten),
                "targets": {"kcal": targets.get("calories"), "protein_g": targets.get("protein_g")},
                "meals_logged": sorted({e["meal"] for e in eaten}, key=MEALS.index)}

    def daily_history(self, days: int = 28, today: Optional[date] = None) -> list[dict]:
        today = today or date.today()
        return [{"date": d, **self.day_totals(d)["totals"]}
                for d in ((today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1))]

    # ------------------------------------------------------------------ skill practice

    def log_skill(self, skill: str, step: str = "", seconds: Optional[float] = None, reps: Optional[int] = None,
                  minutes: Optional[float] = None, on: Optional[str] = None, note: str = "") -> dict:
        entry = {"id": uuid.uuid4().hex[:10], "date": on or date.today().isoformat(), "skill": skill, "step": step,
                 "seconds": seconds, "reps": reps, "minutes": minutes, "note": note}
        self._data["skill_sessions"].append(entry)
        self._save()
        what = f"{seconds:g} s" if seconds else f"{reps} reps" if reps else f"{minutes:g} min" if minutes else "practice"
        self._record("skill_practice", f"{skill}: {step or 'practice'}, {what}", {"skill": skill, "step": step})
        return entry

    def skill_sessions(self, skill: Optional[str] = None) -> list[dict]:
        return [s for s in self._data["skill_sessions"] if skill is None or s["skill"].lower() == skill.lower()]

    def best_hold(self, skill: str, step: str = "") -> Optional[float]:
        holds = [s["seconds"] for s in self.skill_sessions(skill) if s.get("seconds") and (not step or s["step"] == step)]
        return max(holds) if holds else None

    def practice_minutes(self, skill: str, day: Optional[str] = None) -> float:
        day = day or date.today().isoformat()
        return sum(s.get("minutes") or 0 for s in self.skill_sessions(skill) if s["date"] == day)

    # ------------------------------------------------------------------ training rotation

    def today_training(self, today: Optional[date] = None) -> Optional[dict]:
        """Today's strength day: the next one in the rotation, on a
        training day; None on a rest day (or with no rotation)."""
        today = today or date.today()
        training = self.plan["training"]
        rotation = training.get("rotation") or []
        if not rotation or WEEKDAYS[today.weekday()] not in (training.get("days") or WEEKDAYS):
            return None
        done_before = [t for t in self._data["training_done"] if t["date"] < today.isoformat()]
        done_today = next((t for t in self._data["training_done"] if t["date"] == today.isoformat()), None)
        index = done_today["index"] if done_today else len(done_before) % len(rotation)
        return {**rotation[index], "index": index, "done": done_today is not None}

    def complete_training(self, today: Optional[date] = None) -> Optional[dict]:
        day = (today or date.today()).isoformat()
        todays = self.today_training(today)
        if todays is None or todays["done"]:
            return todays
        self._data["training_done"].append({"date": day, "index": todays["index"], "name": todays.get("name", "")})
        self._save()
        self._record("training_done", f"Finished {todays.get('name') or 'training'}", {"date": day})
        return {**todays, "done": True}

    def complete_step(self, index: int, today: Optional[date] = None) -> Optional[dict]:
        """One step (exercise) of today's training; the last one finishes the day."""
        day = (today or date.today()).isoformat()
        todays = self.today_training(today)
        if todays is None:
            return None
        steps = todays.get("exercises") or []
        if steps and not 0 <= index < len(steps):
            raise ValueError(f"Today's training has {len(steps)} steps.")
        done = sorted(set(self._data["training_steps"].get(day, [])) | {index})
        self._data["training_steps"][day] = done
        self._save()
        name = (steps[index].get("name") if steps else todays.get("name")) or f"step {index + 1}"
        self._record("training_step", f"Done: {name}", {"date": day, "step": index})
        if not steps or len(done) >= len(steps):
            return self.complete_training(today)
        return {**todays, "steps_done": done}

    def steps_done(self, day: Optional[str] = None) -> list[int]:
        day = day or date.today().isoformat()
        if any(t["date"] == day for t in self._data["training_done"]):
            todays = self.today_training(date.fromisoformat(day))
            return list(range(len((todays or {}).get("exercises") or []))) or [0]
        return list(self._data["training_steps"].get(day, []))

    def mark_habit(self, name: str, day: Optional[str] = None, done: bool = True) -> None:
        """A yes/no for a day (or a week, keyed by its Monday): "lunch", "prep", "protein"."""
        day = day or date.today().isoformat()
        have = set(self._data["habits"].get(day, []))
        have = have | {name} if done else have - {name}
        self._data["habits"][day] = sorted(have)
        self._save()
        if done:
            self._record("habit", f"Done: {name}", {"habit": name, "date": day})

    def has_habit(self, name: str, day: Optional[str] = None) -> bool:
        return name in self._data["habits"].get(day or date.today().isoformat(), [])

    def training_days_done(self, since: str) -> list[dict]:
        return [t for t in self._data["training_done"] if t["date"] >= since]

    # ------------------------------------------------------------------ meal plan (core/meal_plan.py has the logic)

    def planned(self, day: str) -> dict:
        return dict(self._data["meal_plan"].get(day, {}))

    def plan_meal(self, day: str, meal: str, recipe_id: Optional[str], servings: float = 1.0, prep_id: str = "") -> None:
        """Sets (or, with no recipe, clears) one meal of one day."""
        meal = meal if meal in MEALS else "snack"
        slots = self._data["meal_plan"].setdefault(day, {})
        if recipe_id:
            slots[meal] = {"recipe_id": recipe_id, "servings": servings, "prep_id": prep_id}
        else:
            slots.pop(meal, None)
        if not slots:
            self._data["meal_plan"].pop(day, None)
        self._save()

    def prep_sessions(self, since: str = "", until: str = "9999") -> list[dict]:
        return [p for p in self._data["prep"] if since <= p["date"] <= until]

    def add_prep(self, day: str, recipe_id: str, servings: float, covers: list[str]) -> dict:
        session = {"id": uuid.uuid4().hex[:8], "date": day, "recipe_id": recipe_id, "servings": servings,
                   "covers": list(covers), "done": False}
        self._data["prep"].append(session)
        for slot in covers:
            covered_day, meal = slot.split(":")
            slots = self._data["meal_plan"].setdefault(covered_day, {})
            slots[meal] = {"recipe_id": recipe_id, "servings": 1.0, "prep_id": session["id"]}
        self._save()
        self._record("prep_planned", f"Planned meal prep for {day}", {"date": day, "covers": len(covers)})
        return session

    def finish_prep(self, prep_id: str) -> dict:
        session = next((p for p in self._data["prep"] if p["id"] == prep_id), None)
        if session is None:
            raise ValueError("There's no prep session like that.")
        session["done"] = True
        self._save()
        self._record("prep_done", "Meal prep done", {"prep": prep_id})
        return dict(session)

    def delete_prep(self, prep_id: str) -> None:
        self._data["prep"] = [p for p in self._data["prep"] if p["id"] != prep_id]
        for slots in self._data["meal_plan"].values():
            for meal in [m for m, v in slots.items() if v.get("prep_id") == prep_id]:
                slots.pop(meal)
        self._save()

    def eaten_planned(self, day: str) -> set:
        """The planned meals of a day already logged as eaten."""
        return {f["meal"] for f in self.food_on(day) if f.get("planned_id") == f"{day}:{f['meal']}"}

    # ------------------------------------------------------------------ milestones

    def complete_milestone(self, milestone_id: str, on: Optional[str] = None) -> dict:
        plan = self._data["plan"]
        milestone = next((m for m in plan.get("milestones", []) if m.get("id") == milestone_id), None)
        if milestone is None:
            raise ValueError("There's no milestone like that in your plan.")
        if not milestone.get("done_on"):
            milestone["done_on"] = on or date.today().isoformat()
            self._save()
            self._record("milestone", f"Milestone: {milestone['name']}", {"milestone": milestone["name"]})
        return dict(milestone)
