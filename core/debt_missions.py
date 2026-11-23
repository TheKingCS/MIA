"""
core.debt_missions
====================

His debt payoff plan as a mission (Jarvis brainstorm 6.2; Zac, 2026-11-23: "finance skills"): the order to pay them
off and the month each is gone, worked out in code (core/budget_manager.rank_debts for the order, his strategy;
core/debt_math.simulate for the months, with any extra he names), made into one mission with an objective for each
debt in that order, on his press (`debts.missions`, act_with_approval; one running at a time). Each objective is
ticked when that debt's balance reaches zero (`tick`, in the daily missions check), matched by the debt's id
(`MAP_KEY`: a rename or two debts with one name never tick the wrong step), and the mission is completed when every
step is; from the budget's own record, never by the model.

`plan(context, strategy, extra)` is the plan in data; `say` reads it out; `MISSION_PREFIX` marks the mission so the
tick finds its own.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger

log = get_logger(__name__)

MISSION_PREFIX = "Debt-free"
MAP_KEY = "modules.budget.debt_missions"  # mission id -> the debt ids of its steps, in order (config)
OBJECTIVE = "Pay off {name}"
STRATEGIES = ("hybrid", "avalanche", "snowball")


def plan(context, strategy: str = "hybrid", extra: float = 0.0, today: Optional[date] = None) -> dict:
    """{steps: [{name, balance, by, debt_id}], debt_free, months, extra, strategy, never: [names a minimum never
    pays]}, or {} without open debts. Two debts with one name keep their own ids, in payoff order."""
    from core.budget_manager import rank_debts
    from core.debt_math import simulate

    today = today or date.today()
    budget = getattr(context, "budget", None)
    debts = [d for d in (budget.all_debts() if budget is not None else []) if float(d.balance or 0) > 0]
    if not debts:
        return {}
    strategy = strategy if strategy in STRATEGIES else "hybrid"
    ordered = [p.debt for p in rank_debts(debts, today, strategy)]
    result = simulate(ordered, max(0.0, float(extra or 0)), today)
    by_name = {}
    for d in ordered:
        by_name.setdefault(d.name, []).append(d.debt_id)
    steps = [{"name": r.name, "balance": r.balance, "by": r.paid_off,
              "debt_id": (by_name.get(r.name) or [""]).pop(0)} for r in result.debts]
    paid = [s["by"] for s in steps if s["by"]]
    return {"steps": steps, "debt_free": max(paid) if result.months and paid else None,
            "months": result.months, "extra": max(0.0, float(extra or 0)), "strategy": strategy,
            "never": [s["name"] for s in steps if s["by"] is None]}


def _month(ym: Optional[str]) -> str:
    """Pure logic. "2027-08" as "August 2027"."""
    if not ym:
        return "not at these payments"
    try:
        return date.fromisoformat(f"{ym}-01").strftime("%B %Y")
    except ValueError:
        return ym


def say(found: dict) -> str:
    """Pure logic. The plan in words."""
    from core.region import money

    if not found:
        return "No open debts in your budget to plan a payoff for."
    order = "; ".join(f"{s['name']} ({money(s['balance'])}) by {_month(s['by'])}" for s in found["steps"])
    extra = f", with {money(found['extra'])} extra a month" if found["extra"] else ""
    end = f"Debt-free by {_month(found['debt_free'])}" if found["debt_free"] else "Not debt-free at these payments"
    never = (" " + ", ".join(found["never"]) + ": the minimum doesn't cover the interest, so it needs more."
             if found["never"] else "")
    return f"In order ({found['strategy']}{extra}): {order}. {end}.{never}"


def _describe(context, params) -> str:
    """The card's sentence for `debts.missions`: the mission it makes; ActionError with no open debts, or while a
    payoff mission is already running."""
    found = plan(context, str(params.get("strategy") or "hybrid"), _extra(params))
    if not found:
        raise ActionError("No open debts in your budget to plan a payoff for.")
    missions = getattr(context, "missions", None)
    if missions is not None and any(m.status == "active" and m.name.startswith(MISSION_PREFIX)
                                    for m in missions.all_missions()):
        raise ActionError("There's already a payoff mission running: finish or give it up in Missions first.")
    return f"Make your payoff plan a mission. {say(found)}"


def _extra(params) -> float:
    """The extra a month the params name (0 when none or not a number)."""
    try:
        return max(0.0, float(params.get("extra") or 0))
    except (TypeError, ValueError):
        return 0.0


def _make(context, params) -> str:
    """Does `debts.missions`: one mission, an objective for each debt in payoff order, each step's debt id kept in
    the settings (`MAP_KEY`) for the tick."""
    from core.person_settings import person_id

    found = plan(context, str(params.get("strategy") or "hybrid"), _extra(params))
    if not found:
        raise ActionError("No open debts in your budget to plan a payoff for.")
    missions = getattr(context, "missions", None)
    if missions is None:
        raise ActionError("Missions aren't on this MIA.")
    title = f"{MISSION_PREFIX} by {_month(found['debt_free'])}" if found["debt_free"] else f"{MISSION_PREFIX}: the plan"
    mission = missions.add_mission(title, assigned_by="mia", icon="\U0001F4B3", summary=say(found),
                                   profile_id=person_id(context))
    for step in found["steps"]:
        missions.add_objective(mission.mission_id, OBJECTIVE.format(name=step["name"])
                               + (f" (by {_month(step['by'])})" if step["by"] else ""), "tally", 1)
    config = getattr(context, "config", None)
    if config is not None:  # each step's debt by id, so a rename or a twin name never ticks the wrong one
        kept = dict(config.get(MAP_KEY, {}) or {})
        kept[mission.mission_id] = [s["debt_id"] for s in found["steps"]]
        config.set(MAP_KEY, kept)
    return f"Made the mission “{title}” with {len(found['steps'])} steps, one for each debt in order."


def tick(context) -> int:
    """Ticks each payoff step whose debt (by its id) is paid off, its balance at zero; a deleted debt is left as it
    is (deleting isn't paying). A mission whose every step is done is completed. How many steps changed."""
    missions, budget, config = (getattr(context, n, None) for n in ("missions", "budget", "config"))
    if missions is None or budget is None or config is None:
        return 0
    kept = dict(config.get(MAP_KEY, {}) or {})
    balances = {d.debt_id: float(d.balance or 0) for d in budget.all_debts()}
    changed = 0
    for m in missions.all_missions():
        ids = kept.get(m.mission_id)
        if m.status != "active" or not ids:
            continue
        progress = []
        for o, debt_id in zip(m.objectives, ids):
            done = debt_id in balances and balances[debt_id] <= 0
            progress.append(1.0 if done else None)
            changed += int(done and o.progress < 1)
        if any(p is not None for p in progress):
            missions.set_objective_progress(m.mission_id, progress)
        if m.objectives and all(o.progress >= 1 for o in m.objectives):
            missions.update_mission(m.mission_id, status="completed")
    return changed


ACTION_TYPES["debts.missions"] = ActionType(
    "debts.missions", "Make It A Mission", {"strategy": "/".join(STRATEGIES), "extra": "extra a month (optional)"},
    _describe, _make)
