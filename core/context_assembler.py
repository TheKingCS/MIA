"""
core.context_assembler
=========================

The "Life State" layer — a real service answering "what's going on in
this person's life right now," synthesized live from every domain
manager already in AppContext. This exact shape was discussed and
agreed on 2026-09-11 (see mia_system_vision's own dated entry: a
context_assembler.py query layer as the "world model" — a live view,
not a stored object) and then never actually built until now, at the
user's own explicit request after an external architecture review
named it the single most valuable missing piece.

Deliberately NOT a new database and NOT a second source of truth for
anything: every field on `LifeStateSnapshot` is computed fresh from
real, already-owned state each time `assemble_life_state()` runs —
Missions, recurring-mission streaks, Skill categories (reusing
core.skill_patterns' own momentum/decline/gap functions rather than
reimplementing them), open Insights, overdue Maintenance, and active
Projects. If any underlying manager's data changes, the next call
reflects it immediately — nothing here is cached or persisted.

GUI-only, same reason core.mission_patterns/core.skill_patterns' own
scans are GUI-only: context.insights/context.maintenance/
context.projects/context.recurring_missions are only ever constructed
in core/application.py, not core/core_runtime.py's headless boot path.
Every field gracefully degrades to empty/zero if its manager isn't
wired, rather than raising — same stance every other optional-service
check in this codebase takes.

The first real consumer is an Assistant action ("what's going on with
me?") so a user can get one synthesized answer instead of checking a
dozen screens. Future consumers (Discovery reasoning over the same
state, a Dashboard "System HUD" section, cross-tree Pattern Insights
correlation) should all read from this same function rather than each
re-deriving their own partial view — the whole reason this is worth
having as one shared layer instead of staying inline in one caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from core.maintenance_manager import is_overdue
from core.skill_patterns import declining_categories, momentum_categories, untouched_interests


@dataclass
class LifeStateSnapshot:
    """A live, synthesized read of one profile's current state — never
    persisted, rebuilt fresh on every call to assemble_life_state()."""

    profile_id: str
    active_mission_count: int = 0
    # (template display name, current streak) for every recurring
    # template with a real streak > 0 right now — a 0-streak template
    # isn't "going on" in the person's life, so it's left out rather
    # than padded with zeros.
    recurring_streaks: list[tuple[str, int]] = field(default_factory=list)
    skills_growing: list[str] = field(default_factory=list)
    skills_declining: list[str] = field(default_factory=list)
    skills_dormant: list[str] = field(default_factory=list)
    # Open Insight messages relevant to this profile — this profile's
    # own Pattern Insights (source_type="patterns", scoped by
    # source_id == profile_id) plus every other still-open Insight,
    # which today is all household-wide (Maintenance/Missions-stale
    # signals aren't profile-scoped in the data model at all).
    system_signals: list[str] = field(default_factory=list)
    overdue_maintenance_count: int = 0
    active_project_count: int = 0


def _find_profile(context, profile_id: str):
    if context.profiles is None:
        return None
    return next((p for p in context.profiles.list_profiles() if p.profile_id == profile_id), None)


def _missions_count_for_profile(context, profile_id: str) -> int:
    """A Mission counts toward this profile if it's unattributed
    (profile_id is None — shared/counts for everyone, the same
    convention core.gamification.grant_xp() and
    core.mission_manager.MissionManager._credit_mission_rewards()
    already establish), explicitly assigned to this profile, or this
    profile is one of its real group-quest participants."""
    return sum(
        1 for mission in context.missions.all_missions()
        if mission.status == "active"
        and (
            mission.profile_id is None
            or mission.profile_id == profile_id
            or profile_id in mission.participant_profile_ids
        )
    )


def assemble_life_state(context, profile_id: str, today: date) -> LifeStateSnapshot:
    """Real, deterministic synthesis — every section gracefully
    degrades to empty/zero if its manager isn't wired (GUI-only
    services, see module docstring), never raises."""
    snapshot = LifeStateSnapshot(profile_id=profile_id)

    if context.missions is not None:
        snapshot.active_mission_count = _missions_count_for_profile(context, profile_id)

    if context.recurring_missions is not None:
        for template in context.recurring_missions.all_templates():
            streak = context.recurring_missions.current_streak_for_template(template.template_id, today)
            if streak > 0:
                snapshot.recurring_streaks.append((template.name, streak))

    if context.skills is not None:
        snapshot.skills_growing = momentum_categories(context.skills, profile_id, today)
        snapshot.skills_declining = declining_categories(context.skills, profile_id, today)
        profile = _find_profile(context, profile_id)
        if profile is not None:
            snapshot.skills_dormant = untouched_interests(context.skills, profile)

    if context.insights is not None:
        for insight in context.insights.open_insights():
            if insight.source_type == "patterns" and insight.source_id != profile_id:
                continue  # a different profile's own pattern signal, not this one's
            snapshot.system_signals.append(insight.message)

    if context.maintenance is not None:
        snapshot.overdue_maintenance_count = sum(
            1 for task in context.maintenance.all_tasks() if is_overdue(task, today)
        )

    if context.projects is not None:
        snapshot.active_project_count = sum(
            1 for project in context.projects.all_projects() if project.status != "Complete"
        )

    return snapshot


def format_life_state_summary(snapshot: LifeStateSnapshot) -> str:
    """Pure formatting logic — testable without Qt. Turns the snapshot
    into a short plain-English status report. Always returns real
    text, even when everything is quiet (a pull-query response, unlike
    a notification message, must never come back empty)."""
    lines: list[str] = []

    if snapshot.active_mission_count:
        lines.append(f"{snapshot.active_mission_count} active mission(s).")

    if snapshot.recurring_streaks:
        streak_text = ", ".join(f"{name} ({streak})" for name, streak in snapshot.recurring_streaks)
        lines.append(f"Live streaks: {streak_text}.")

    if snapshot.skills_growing:
        lines.append(f"Skills gaining real momentum: {', '.join(snapshot.skills_growing)}.")

    if snapshot.skills_declining:
        lines.append(f"Skills that have gone quiet: {', '.join(snapshot.skills_declining)}.")

    if snapshot.skills_dormant:
        lines.append(f"Stated interests with nothing started yet: {', '.join(snapshot.skills_dormant)}.")

    if snapshot.overdue_maintenance_count:
        lines.append(f"{snapshot.overdue_maintenance_count} maintenance item(s) overdue.")

    if snapshot.active_project_count:
        lines.append(f"{snapshot.active_project_count} active project(s).")

    if snapshot.system_signals:
        lines.append("MIA has also noticed: " + " ".join(snapshot.system_signals))

    if not lines:
        return "Nothing notable right now — no active missions, no maintenance overdue, and no skill trends to report."

    return " ".join(lines)


def format_life_state_glance_line(snapshot: LifeStateSnapshot) -> str:
    """Pure formatting logic — testable without Qt. The dashboard-card
    "glance" form of format_life_state_summary() above — a short
    counts-only line, same "surface the summary before the detail"
    stance as gui/home_dashboard.py's other format_*_line() functions,
    just living here instead since it formats a core dataclass rather
    than reading a GUI-local structure."""
    parts = []
    if snapshot.active_mission_count:
        noun = "mission" if snapshot.active_mission_count == 1 else "missions"
        parts.append(f"{snapshot.active_mission_count} active {noun}")
    if snapshot.skills_growing:
        parts.append(f"{len(snapshot.skills_growing)} growing")
    if snapshot.skills_declining:
        parts.append(f"{len(snapshot.skills_declining)} declining")
    if snapshot.overdue_maintenance_count:
        noun = "item" if snapshot.overdue_maintenance_count == 1 else "items"
        parts.append(f"{snapshot.overdue_maintenance_count} overdue {noun}")
    if not parts:
        return "All quiet"
    return " · ".join(parts)


# ======================================================================
# Life State v2 (2026-10-05, Engine Phase 1 step 3,
# docs/ENGINE_PHASE1_PLAN.md)
# ======================================================================
#
# The same idea as v1, widened to the whole life and shaped as data:
# money, properties, vehicles/tools/appliances, kitchen, workouts
# (the last three added 2026-10-05 for Muse's H-0004), projects, what's
# due, missions and skills, recent
# wins (core/life_events.py), friction, goals and what waits on what
# (core/links.py). Every number comes from the function the rest of MIA
# already uses (finance_summary, today, rank_debts, v1 above); nothing
# here is a second calculation or hand-written prose.
#
# Each section says what it is (`status`: REAL, DERIVED, SIMULATED,
# STATIC or PLANNED) and where it comes from (`source`), so any surface
# reading it (the phone, a mock-up, glasses) can show it honestly. This
# is the read model behind `tools/export_state.py` and `/api/state`;
# its shape is published in docs/schema/life_state.schema.json.

LIFE_STATE_VERSION = 2
STATUSES = ("REAL", "DERIVED", "SIMULATED", "STATIC", "PLANNED")
_MONTHLY = {"monthly": 1.0, "weekly": 52 / 12, "biweekly": 26 / 12, "yearly": 1 / 12}
_RECENT_DAYS = 7


def monthly_equivalent(amount: float, recurrence) -> float:
    """Pure logic. A repeating amount per month; one-time ones count 0."""
    return round(float(amount or 0.0) * _MONTHLY.get(recurrence or "", 0.0), 2)


def _section(status: str, source: str, **data) -> dict:
    assert status in STATUSES
    return {"status": status, "source": source, **data}


def _person(context) -> dict:
    from core.child_accounts import is_child
    from core.person_settings import person_id

    pid = person_id(context)
    profiles = getattr(context, "profiles", None)
    profile = profiles.get_profile(pid) if profiles is not None and pid else None
    households = getattr(context, "households", None)
    household_id = households.household_of(pid) if households is not None and pid else None
    return {
        "profile_id": pid, "name": getattr(profile, "name", None),
        "household_id": household_id,
        "household_name": households.name(household_id) if households is not None and household_id else None,
        "child": bool(getattr(context, "config", None) is not None and pid and is_child(context, pid)),
    }


def _finances(context, today: date) -> dict:
    from core.finance_summary import build_finance_summary

    budget = getattr(context, "budget", None)
    if budget is None:
        return _section("PLANNED", "core/budget_manager.py", available=False)
    summary = build_finance_summary(context, today)
    summary.pop("generated_at", None)
    income = sum(monthly_equivalent(s.expected_amount, s.recurrence) for s in budget.all_income_sources())
    bills = sum(monthly_equivalent(b.amount, b.recurrence) for b in budget.all_bills())
    minimums = round(sum(d.minimum_payment for d in budget.all_debts()), 2)
    summary["monthly_plan"] = {
        "expected_income": round(income, 2), "bills": round(bills, 2), "debt_minimums": minimums,
        "gap": round(income - bills - minimums, 2),
        "note": "Repeating income sources and bills turned into a monthly amount, minus debt minimums.",
    }
    return _section("DERIVED", "core/finance_summary.py, core/budget_manager.py", **summary)


def _properties(context) -> dict:
    real_estate = getattr(context, "real_estate", None)
    if real_estate is None:
        return _section("PLANNED", "core/real_estate_manager.py", items=[])
    from core.real_estate_manager import equity

    items = []
    for prop in real_estate.all_properties():
        items.append({
            "ref": f"property:{prop.property_id}", "name": prop.name, "type": prop.property_type,
            "value": round(prop.current_value, 2), "mortgage_balance": round(prop.mortgage_balance, 2),
            "equity": round(equity(prop), 2),
        })
    return _section("REAL", "core/real_estate_manager.py", items=items)


def _assets(context, today: date) -> dict:
    """Vehicles, tools and appliances (Maintenance, Garage): who they
    belong to and what upkeep is overdue or coming (H-0004)."""
    maintenance = getattr(context, "maintenance", None)
    if maintenance is None:
        return _section("PLANNED", "core/maintenance_manager.py", items=[])
    from core.maintenance_manager import days_until_due, task_urgency
    from core.ownership import is_for_me

    profiles = getattr(context, "profiles", None)
    tasks = maintenance.all_tasks()
    items = []
    for asset in maintenance.all_assets():
        own = [t for t in tasks if t.asset_id == asset.asset_id]
        overdue = soon = 0
        upcoming = []
        for task in own:
            readings = [] if task.trigger_type == "calendar" else (maintenance.readings_for_task(task.task_id) or [])
            urgency = task_urgency(task, readings, today)
            overdue += urgency == "overdue"
            soon += urgency == "due_soon"
            left = days_until_due(task, today) if task.trigger_type == "calendar" else None
            if left is not None:
                upcoming.append((left, task.title))
        owner = getattr(asset, "owner_profile_id", None)
        owner_profile = profiles.get_profile(owner) if profiles is not None and owner else None
        nxt = min(upcoming) if upcoming else None
        items.append({
            "ref": f"asset:{asset.asset_id}", "name": asset.name, "category": asset.category,
            "owner": getattr(owner_profile, "name", None), "mine": bool(owner) and is_for_me(context, owner),
            "tasks_overdue": overdue, "tasks_due_soon": soon,
            "next_task": {"title": nxt[1], "days": nxt[0]} if nxt else None,
        })
    return _section("REAL", "core/maintenance_manager.py, core/ownership.py", items=items)


def _kitchen(context, today: date) -> dict:
    """Pantry, groceries and meals (Kitchen), H-0004."""
    kitchen = getattr(context, "kitchen", None)
    if kitchen is None:
        return _section("PLANNED", "core/kitchen_manager.py", available=False)
    from core.kitchen_manager import days_until_expiration

    pantry = kitchen.all_pantry_items()
    expiring = []
    for item in pantry:
        left = days_until_expiration(item, today)
        if left is not None and left <= 3:
            expiring.append({"name": item.name, "days": left})
    since = (today - timedelta(days=_RECENT_DAYS - 1)).isoformat()
    recipes = {r.recipe_id: r.name for r in kitchen.all_recipes()}
    meals = sorted((m for m in kitchen.all_meal_log_entries() if m.date >= since), key=lambda m: m.date, reverse=True)
    return _section(
        "REAL", "core/kitchen_manager.py",
        pantry_items=len(pantry), expiring_soon=sorted(expiring, key=lambda e: e["days"]),
        grocery_list=[{"name": g.name, "checked": g.checked} for g in kitchen.all_grocery_items()],
        recipes=len(recipes),
        recent_meals=[{"recipe": recipes.get(m.recipe_id, "a meal"), "date": m.date} for m in meals[:10]],
    )


def _workout(context, today: date) -> dict:
    """The person's own training (Workout), H-0004."""
    workout = getattr(context, "workout", None)
    if workout is None:
        return _section("PLANNED", "core/workout_manager.py", available=False)
    since = (today - timedelta(days=_RECENT_DAYS - 1)).isoformat()
    sessions = sorted(workout.all_sessions(), key=lambda s: s.date, reverse=True)
    recent = [s for s in sessions if since <= s.date <= today.isoformat()]
    templates = {t.template_id: t.name for t in workout.all_templates()}
    last = sessions[0] if sessions else None
    return _section(
        "REAL", "core/workout_manager.py",
        days=_RECENT_DAYS, sessions=len(recent), minutes=round(sum(s.duration_minutes for s in recent), 1),
        last_session={"date": last.date, "template": templates.get(last.template_id) if last.template_id else None,
                      "minutes": last.duration_minutes} if last else None,
        templates=sorted(templates.values()),
    )


def _waiting_on(context, ref: str, all_links: list) -> list[str]:
    from core import links

    return [links.name_of(context, l.target) for l in all_links
            if l.source == ref and l.relation in ("DEPENDS_ON", "BLOCKED_BY", "REQUIRES")]


def _projects(context, all_links: list) -> dict:
    projects = getattr(context, "projects", None)
    if projects is None:
        return _section("PLANNED", "core/project_manager.py", items=[])
    from core import links

    tasks = getattr(context, "tasks", None)
    items = []
    for project in projects.all_projects():
        if project.status == "Complete":
            continue
        ref = f"project:{project.project_id}"
        own = tasks.tasks_for_project(project.project_id) if tasks is not None else []
        items.append({
            "ref": ref, "name": project.name, "status": project.status, "due_date": project.due_date or None,
            "tasks_open": sum(1 for t in own if not t.done), "tasks_done": sum(1 for t in own if t.done),
            "supports": links.name_of(context, f"intent:{project.intent_id}") if project.intent_id else None,
            "waiting_on": _waiting_on(context, ref, all_links),
        })
    return _section("REAL", "core/project_manager.py, core/task_manager.py, core/links.py", items=items)


def _due(context, today: date) -> dict:
    from core.today import today_items

    return _section("DERIVED", "core/today.py", items=[i.as_dict() for i in today_items(context, today)])


def _missions_and_skills(context, profile_id, today: date) -> dict:
    if not profile_id:
        return _section("PLANNED", "core/context_assembler.py", available=False)
    snapshot = assemble_life_state(context, profile_id, today)
    return _section(
        "DERIVED", "core/context_assembler.py (v1), core/mission_manager.py, core/skill_manager.py",
        active_missions=snapshot.active_mission_count,
        streaks=[{"name": n, "days": d} for n, d in snapshot.recurring_streaks],
        skills_growing=snapshot.skills_growing, skills_declining=snapshot.skills_declining,
        skills_dormant=snapshot.skills_dormant, signals=snapshot.system_signals,
    )


def _recent_wins(context, today: date) -> dict:
    from core import life_events

    since = (today - timedelta(days=_RECENT_DAYS - 1)).isoformat()
    events = [e for e in life_events.events_for(context, since=since, until=today.isoformat())
              if e.type not in life_events.AUDIT_ONLY]
    wins = [e for e in events if e.type in life_events.WINS]
    return _section("DERIVED", "core/life_events.py", days=_RECENT_DAYS, counts=life_events.counts(wins),
                    latest=[{"at": e.at, "type": e.type, "summary": e.summary, "refs": e.refs, "source": e.source}
                            for e in events[:15]])


def _friction(due: dict, projects: dict, finances: dict) -> dict:
    """What's in the way right now, from the sections already built."""
    items = []
    for item in due.get("items", []):
        if item["when"] == "overdue":
            items.append({"kind": "overdue", "text": f"{item['title']} ({item['detail']})",
                          "module": item["module_id"]})
    for project in projects.get("items", []):
        if project["waiting_on"]:
            items.append({"kind": "waiting", "text": f"{project['name']} waits on {', '.join(project['waiting_on'])}",
                          "ref": project["ref"]})
    plan = finances.get("monthly_plan")
    if plan and plan["gap"] < 0:
        items.append({"kind": "money_gap", "text": "Planned monthly outflow is more than expected income",
                      "amount": plan["gap"]})
    for target in finances.get("budget_targets", []):
        if target["budget"] and target["spent"] > target["budget"]:
            items.append({"kind": "over_budget", "text": f"{target['category']} is over its monthly budget",
                          "amount": round(target["spent"] - target["budget"], 2)})
    return _section("DERIVED", "this file, from due, projects and finances", items=items)


def _goals(context, all_links: list) -> dict:
    """Active goals (intents) with what serves them, and every chain of
    things waiting on each other ("sell the lot → greenhouse → solar")."""
    from core import links

    intents = getattr(context, "intents", None)
    goals = []
    for intent in (intents.all_intents() if intents is not None else []):
        if intent.status != "Active":
            continue
        ref = f"intent:{intent.intent_id}"
        goals.append({
            "ref": ref, "name": intent.name, "primary": intent.primary,
            "serves": links.name_of(context, f"intent:{intent.serves_intent_id}") if intent.serves_intent_id else None,
            "supported_by": [links.name_of(context, l.source) for l in all_links
                             if l.target == ref and l.relation == "SUPPORTS"],
        })
    waits = [l for l in all_links if l.relation in ("DEPENDS_ON", "BLOCKED_BY", "REQUIRES")]
    waiting_sources = {l.source for l in waits}
    roots = list(dict.fromkeys(l.target for l in waits if l.target not in waiting_sources))
    chains = [[links.name_of(context, r)] + [links.name_of(context, x) for x in links.downstream(context, r)]
              for r in roots]
    return _section("DERIVED", "core/intent_manager.py, core/why_graph.py, core/links.py",
                    items=goals, chains=chains)


def assemble_life_state_v2(context, today: Optional[date] = None) -> dict:
    """The whole picture for the person this context is for (the
    signed-in person, or the phone user on their own view), as plain
    JSON-ready data. Never raises for a missing store: that section says
    PLANNED instead."""
    from core import links

    today = today or date.today()
    person = _person(context)
    all_links = links.all_links(context)
    due = _due(context, today)
    projects = _projects(context, all_links)
    if person["child"]:
        finances = _section("STATIC", "core/child_accounts.py", hidden=True,
                            note="Money isn't shown to a child account.")
        properties = _section("STATIC", "core/child_accounts.py", hidden=True, items=[])
        assets = _section("STATIC", "core/child_accounts.py", hidden=True, items=[])
    else:
        finances = _finances(context, today)
        properties = _properties(context)
        assets = _assets(context, today)
    stated = getattr(context, "links", None)
    return {
        "version": LIFE_STATE_VERSION,
        "schema": "docs/schema/life_state.schema.json",
        "as_of": today.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "person": person,
        "finances": finances,
        "properties": properties,
        "assets": assets,
        "kitchen": _kitchen(context, today),
        "workout": _workout(context, today),
        "projects": projects,
        "due": due,
        "missions_and_skills": _missions_and_skills(context, person["profile_id"], today),
        "recent_wins": _recent_wins(context, today),
        "friction": _friction(due, projects, finances),
        "goals": _goals(context, all_links),
        "links": _section("DERIVED", "core/links.py",
                          stated=len(stated.all_links()) if stated is not None else 0,
                          derived=sum(1 for l in all_links if l.derived)),
        "opportunities": _section("PLANNED", "Phase 2: MIA's reasoning over this state", items=[]),
    }


def describe_life_state_v2(state: dict) -> str:
    """Pure formatting. The v2 part of "what's going on with me?": wins,
    friction, what waits on what, the monthly plan. Empty when quiet;
    the caller adds v1's missions-and-skills line after it."""
    parts = []
    wins = state["recent_wins"]["counts"]
    if wins:
        from core.life_events import TYPES

        parts.append("This week: " + ", ".join(f"{n} {TYPES.get(t, t)}" for t, n in wins.items()) + ".")
    friction = state["friction"]["items"]
    if friction:
        parts.append("In the way: " + "; ".join(f["text"] for f in friction[:5]) + ".")
    chains = state["goals"].get("chains", [])
    if chains:
        parts.append("Waiting in order: " + "; ".join(" → ".join(c) for c in chains[:3]) + ".")
    plan = state["finances"].get("monthly_plan")
    if plan and (plan["expected_income"] or plan["bills"]):
        from core.region import money

        parts.append(f"Monthly plan: {money(plan['expected_income'])} in, "
                     f"{money(plan['bills'] + plan['debt_minimums'])} out ({money(plan['gap'])}).")
    return " ".join(parts)
