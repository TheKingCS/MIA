"""
core.fitness_missions
=======================

A person's fitness plan as missions (DEC-0020, H-0026): made from the
plan (core/fitness_manager.py) each day and week, on the existing
mission path (Missions screen, XP, skills, complete, undo).

| Mission | When | Objectives |
|---|---|---|
| Training: <day> | training days | each exercise of today's strength day |
| <Skill> practice | daily, per skill with daily minutes | each practice item |
| Protein | daily, with a protein target | the grams |
| Packed lunch | daily, with packed_lunch on | taken to work |
| Meal prep | weekly, with a prep day | the prep session |
| Workouts this week | weekly, with workouts_per_week | days trained |

**The logs are the truth.** Each objective's progress is recomputed from
what was logged (`sync`), so logging a set on the Workout screen, saying
"step one done", or tapping +1 on the mission all land the same: a tap
(`tick`) writes the log first, then the mission follows. A mission
completes itself when every objective is done.

**Never punitive (DEC-0014).** A day that passes undone quietly drops
away (the logs keep whatever was done) with a gentle note in the
history; rest days aren't misses; no notices nag.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core import life_events
from core.gamification import SkillWeight
from core.logger import get_logger

log = get_logger(__name__)

PREFIX = "fitness:"
DAILY, WEEKLY = "fitness_daily", "fitness_weekly"


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _rep_text(exercise: dict) -> str:
    sets, reps, hold = exercise.get("sets"), exercise.get("reps"), exercise.get("hold_seconds")
    amount = f"{hold:g} s" if hold else (str(reps) if reps not in (None, "") else "")
    return f"{exercise.get('name', 'Exercise')}" + (f" {sets}×{amount}" if sets and amount else f" {amount}" if amount else "")


def specs(fit, today: date) -> list[dict]:
    """Pure logic over the plan. The missions today and this week should
    have: [{kind, key, name, icon, summary, objectives: [(text, target)],
    xp, skills: [(skill_id, xp)], cadence}]."""
    plan = fit.plan
    day, week = today.isoformat(), monday(today).isoformat()
    out = []
    training = fit.today_training(today)
    if training is not None:
        steps = training.get("exercises") or []
        out.append({"kind": "training", "key": f"{PREFIX}training:{day}", "cadence": DAILY,
                    "name": f"Training: {training.get('name') or 'today'}", "icon": "\U0001F4AA",
                    "summary": "Today's strength day from your rotation.",
                    "objectives": [(_rep_text(e), 1) for e in steps] or [("Train", 1)],
                    "xp": 30, "skills": [("calisthenics", 20), ("strength", 10)]})
    for skill in plan.get("skill_tree") or []:
        if not skill.get("daily_minutes") and not skill.get("practice"):
            continue
        name = skill.get("skill", "Skill")
        items = skill.get("practice") or [f"{skill.get('daily_minutes'):g} minutes"]
        out.append({"kind": f"skill:{name.lower()}", "key": f"{PREFIX}skill:{name.lower()}:{day}", "cadence": DAILY,
                    "name": f"{name} practice", "icon": "\U0001F938",
                    "summary": f"{skill.get('daily_minutes') or 10:g} minutes of {name.lower()} work.",
                    "objectives": [(item, 1) for item in items], "xp": 15, "skills": [("calisthenics", 10)]})
    protein = plan["targets"].get("protein_g")
    if protein:
        out.append({"kind": "protein", "key": f"{PREFIX}protein:{day}", "cadence": DAILY,
                    "name": f"Protein: {protein:g} g", "icon": "\U0001F357",
                    "summary": "Today's protein target.", "objectives": [(f"Eat {protein:g} g of protein", float(protein))],
                    "xp": 10, "skills": [("nutrition", 10)]})
    if plan["meals"].get("packed_lunch") and today.weekday() < 5:
        out.append({"kind": "lunch", "key": f"{PREFIX}lunch:{day}", "cadence": DAILY,
                    "name": "Packed lunch", "icon": "\U0001F96A", "summary": "Lunch packed and taken to work.",
                    "objectives": [("Take a packed lunch", 1)], "xp": 10, "skills": [("nutrition", 5)]})
    prep_day = plan["meals"].get("prep_day")
    if prep_day:
        out.append({"kind": "prep", "key": f"{PREFIX}prep:{week}", "cadence": WEEKLY,
                    "name": f"Meal prep ({prep_day})", "icon": "\U0001F372",
                    "summary": "This week's meal-prep session.", "objectives": [("Do the meal prep", 1)],
                    "xp": 40, "skills": [("cooking", 20), ("nutrition", 10)]})
    per_week = plan["targets"].get("workouts_per_week")
    if per_week:
        out.append({"kind": "week_workouts", "key": f"{PREFIX}week_workouts:{week}", "cadence": WEEKLY,
                    "name": f"Workouts this week: {per_week:g}", "icon": "\U0001F3CB",
                    "summary": "Days trained this week.", "objectives": [(f"Train {per_week:g} days", float(per_week))],
                    "xp": 50, "skills": [("strength", 20), ("endurance", 10)]})
    return out


def progress(fit, kind: str, key: str, objectives: list, today: date) -> list[float]:
    """Pure logic over the logs. Each objective's progress for a mission."""
    day = key.rsplit(":", 1)[1]
    if kind == "training":
        done = set(fit.steps_done(day))
        return [1.0 if i in done else 0.0 for i in range(len(objectives))]
    if kind.startswith("skill:"):
        skill = kind.split(":", 1)[1]
        practiced = {s["step"].lower() for s in fit.skill_sessions(skill) if s["date"] == day}
        if len(objectives) == 1 and objectives[0].description.endswith("minutes"):
            return [1.0 if fit.practice_minutes(skill, day) or practiced else 0.0]
        return [1.0 if o.description.lower() in practiced else 0.0 for o in objectives]
    if kind == "protein":
        target = objectives[0].target
        if fit.has_habit("protein", day):
            return [target]
        eaten = fit.day_totals(day)["totals"]["protein_g"] or 0.0
        return [min(target, eaten)]
    if kind == "lunch":
        return [1.0 if fit.has_habit("lunch", day) else 0.0]
    if kind == "prep":
        return [1.0 if fit.has_habit("prep", day) else 0.0]
    if kind == "week_workouts":
        return [float(min(objectives[0].target, len(fit.training_days_done(day))))]
    return [o.progress for o in objectives]


def _mine(context, pid) -> list:
    missions = getattr(context, "missions", None)
    if missions is None:
        return []
    return [m for m in missions.all_missions() if (m.occurrence_key or "").startswith(PREFIX) and m.profile_id == pid]


def _kind(mission) -> str:
    return mission.occurrence_key[len(PREFIX):].rsplit(":", 1)[0]


def ensure(context, today: Optional[date] = None) -> list:
    """Makes today's and this week's missions from the plan (once each),
    lets yesterday's undone ones go, and brings progress up to date.
    Returns the person's current fitness missions."""
    from core.person_settings import person_id

    fit, missions = getattr(context, "fitness", None), getattr(context, "missions", None)
    if fit is None or missions is None:
        return []
    today = today or date.today()
    pid = person_id(context)
    wanted = specs(fit, today)
    keys = {s["key"] for s in wanted}
    existing = {m.occurrence_key: m for m in _mine(context, pid)}
    for old_key, mission in existing.items():
        if old_key not in keys and mission.status == "active":
            stamp = old_key.rsplit(":", 1)[1]
            current = today.isoformat() if mission.recurring_kind == DAILY else monday(today).isoformat()
            if stamp < current:
                missions.delete_mission(mission.mission_id)  # the logs keep what was done
                life_events.record(fit, "mission_missed", f"{mission.name} passed. Nothing lost; it's there again next time.",
                                   [], {"kind": _kind(mission)})
    for spec in wanted:
        if spec["key"] in existing:
            continue
        mission = missions.add_mission(
            name=spec["name"], icon=spec["icon"], summary=spec["summary"], assigned_by="mia",
            mission_type="DAILY MISSION" if spec["cadence"] == DAILY else "WEEKLY MISSION",
            reward_xp=spec["xp"], skill_rewards=[SkillWeight(s, xp) for s, xp in spec["skills"]],
            recurring_kind=spec["cadence"], occurrence_key=spec["key"], profile_id=pid)
        for text, target in spec["objectives"]:
            missions.add_objective(mission.mission_id, text, "tally", float(target))
    sync(context, today)
    return [m for m in _mine(context, pid) if m.occurrence_key in keys]


def sync(context, today: Optional[date] = None) -> None:
    """Objective progress from the logs; a mission with everything done completes."""
    from core.person_settings import person_id

    fit, missions = getattr(context, "fitness", None), getattr(context, "missions", None)
    if fit is None or missions is None:
        return
    today = today or date.today()
    for mission in _mine(context, person_id(context)):
        if mission.status != "active":
            continue
        values = progress(fit, _kind(mission), mission.occurrence_key, mission.objectives, today)
        missions.set_objective_progress(mission.mission_id, values)
        if mission.objectives and all(missions.is_objective_complete(mission.mission_id, i)
                                      for i in range(len(mission.objectives))):
            missions.update_mission(mission.mission_id, status="completed")


def tick(context, mission, index: int, today: Optional[date] = None) -> str:
    """+1 on a fitness mission's objective: log it where it belongs, then sync."""
    fit = context.fitness
    today = today or date.today()
    kind, stamp = _kind(mission), mission.occurrence_key.rsplit(":", 1)[1]
    objective = mission.objectives[index]
    if kind == "training":
        fit.complete_step(index, date.fromisoformat(stamp))
        said = f"Done: {objective.description}."
    elif kind.startswith("skill:"):
        fit.log_skill(kind.split(":", 1)[1].title(), objective.description, on=stamp,
                      minutes=None if not objective.description.endswith("minutes") else float(objective.description.split()[0]))
        said = f"Logged {objective.description}."
    elif kind in ("protein", "lunch", "prep"):
        fit.mark_habit(kind, stamp)
        said = {"protein": "Protein target hit.", "lunch": "Packed lunch: done.", "prep": "Meal prep: done."}[kind]
    elif kind == "week_workouts":
        fit.complete_training(today)
        said = "Today's training is logged."
    else:
        said = "Done."
    sync(context, today)
    return said


def is_fitness(mission) -> bool:
    return (getattr(mission, "occurrence_key", None) or "").startswith(PREFIX)
