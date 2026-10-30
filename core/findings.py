"""
core.findings
===============

Findings (DEC-0052 step 3; docs/REASONING_PLAN.md section 4): what MIA
notices by putting two apps together, worked out in code, never by the
model. Each one says what it noticed, the records it came from (`refs`,
"kind:id"), why it matters, one suggested next step, how sure it is
(REAL from records, or DERIVED by calculation), and whether it may reach
the person unprompted.

Unprompted (Zac, 2026-10-30, "go with that"): a bill due before payday
with money short, upkeep due on a vehicle before a trip, a deadline in a
packed week, a cheaper insurance quote near renewal. These go through
the communication gate (merged, rate-limited, repeats dropped). The
rest show only when asked ("what have you noticed?", the "noticed"
question plan) and on Home, quietly.

Not built yet, for want of data (docs/INTELLIGENCE_BENCHMARK.md section
5): goods passing their best-by before market day (lots have no best-by
date) and a subscription nobody uses (nothing records use).

Each rule is small and fails alone: one store failing never hides the
others.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

REAL, DERIVED = "REAL", "DERIVED"
TRIP_AHEAD_DAYS = 14
PACKED_WEEK = 8  # calendar items in a week that make it packed
STALE_DAYS = 14
RENEWAL_DAYS = 45


@dataclass
class Finding:
    key: str  # stable: the same situation keeps the same key
    title: str
    claim: str
    why: str
    refs: list = field(default_factory=list)  # "kind:id"
    next_step: str = ""
    sureness: str = REAL
    unprompted: bool = False
    app: str = ""


def _money(amount: float) -> str:
    from core.region import money

    return money(amount)


def _day(iso: str) -> Optional[date]:
    try:
        return date.fromisoformat(str(iso or "")[:10])
    except ValueError:
        return None


def _say_day(day: date, today: date) -> str:
    if day == today:
        return "today"
    if day == today + timedelta(days=1):
        return "tomorrow"
    # A weekday only for the week ahead: a past "Thursday, October 15" was read as "last Thursday" (live).
    return f"{day:%A}, {day:%B} {day.day}" if 0 < (day - today).days < 7 else f"{day:%B} {day.day}"


def _next_on(anchor: str, recurrence, today: date, ahead: int = 45) -> Optional[date]:
    from core.calendar_manager import occurs_on

    if not anchor:
        return None
    event = SimpleNamespace(date=anchor, recurrence=recurrence)
    for i in range(ahead + 1):
        day = today + timedelta(days=i)
        if occurs_on(event, day):
            return day
    return None


# ---------------------------------------------------------------- the rules


def bill_before_pay(context, today: date) -> list[Finding]:
    """A bill falls due before the next pay lands; unprompted when the
    bank says there isn't enough for it."""
    budget = getattr(context, "budget", None)
    if budget is None:
        return []
    pays = [d for d in (_next_on(s.next_date, getattr(s, "recurrence", None), today)
                        for s in budget.all_income_sources()) if d is not None]
    if not pays:
        return []
    payday = min(pays)
    due = [(b, d) for b in budget.all_bills() if (d := _next_on(b.due_date, b.recurrence, today)) and d < payday]
    if not due:
        return []
    total = sum(float(b.amount or 0) for b, _ in due)
    try:
        from core.freedom import bank_cash

        cash = bank_cash(context)
    except Exception:
        cash = None
    short = cash is not None and cash < total
    names = ", ".join(f"{b.name} ({_money(b.amount)}, {_say_day(d, today)})" for b, d in due[:4])
    claim = f"Before your next pay lands {_say_day(payday, today)}: {names}."
    if cash is not None:
        claim += f" The bank shows {_money(cash)} in checking and savings" + (", less than they add up to." if short else ".")
    return [Finding(f"bill_before_pay:{payday}", "Bills before payday", claim,
                    "Paying late can cost a fee; knowing now leaves time to move money or call ahead.",
                    [f"bill:{b.bill_id}" for b, _ in due], "Move money in or set a reminder before the first one.",
                    DERIVED, unprompted=short, app="budget")]


def upkeep_before_trip(context, today: date) -> list[Finding]:
    """A trip starts soon and a vehicle has upkeep due before it."""
    from core.maintenance_manager import days_until_due as maintenance_days_until_due

    trips = getattr(context, "trips", None)
    upkeep = getattr(context, "maintenance", None)
    if trips is None or upkeep is None:
        return []
    soon = sorted((d, t) for t in trips.all_trips()
                  if (d := _day(t.start_date)) and 0 <= (d - today).days <= TRIP_AHEAD_DAYS)
    if not soon:
        return []
    start, trip = soon[0]
    due = []
    for task in upkeep.all_tasks():
        asset = upkeep.get_asset(task.asset_id)
        if asset is None or asset.category != "Vehicle" or getattr(task, "trigger_type", "calendar") != "calendar":
            continue
        left = maintenance_days_until_due(task, today)
        if (left is None and task.interval_days) or (left is not None and left <= (start - today).days):
            due.append((task, asset))
    if not due:
        return []
    names = ", ".join(f"{t.title} on the {a.name}" for t, a in due[:3])
    return [Finding(f"upkeep_before_trip:{getattr(trip, 'trip_id', trip.name)}:{start}", "Upkeep before your trip",
                    f"{trip.name} starts {_say_day(start, today)}, and {names} is due before then.",
                    "A breakdown on the road costs more than the upkeep.",
                    [f"maintenance_task:{t.task_id}" for t, _ in due], "Book it or do it before you leave.",
                    REAL, unprompted=True, app="maintenance")]


def meal_missing_ingredient(context, today: date) -> list[Finding]:
    """A meal planned in the next three days needs something that isn't in
    the pantry or on the grocery list."""
    from core.kitchen_manager import recipe_missing_ingredients

    fitness, kitchen = getattr(context, "fitness", None), getattr(context, "kitchen", None)
    if fitness is None or kitchen is None:
        return []
    listed = {g.name.strip().lower() for g in kitchen.all_grocery_items() if not getattr(g, "checked", False)}
    out = []
    for i in range(3):
        day = today + timedelta(days=i)
        for slot in fitness.planned(day.isoformat()).values():
            recipe = kitchen.get_recipe(slot.get("recipe_id") if isinstance(slot, dict) else slot)
            if recipe is None:
                continue
            need = [n for n in recipe_missing_ingredients(recipe, kitchen.all_pantry_items()) if n.strip().lower() not in listed]
            if need:
                out.append(Finding(f"meal_missing:{day}:{recipe.recipe_id}", "A meal is missing something",
                                   f"{recipe.name} ({_say_day(day, today)}) needs {', '.join(need[:4])}, which isn't in "
                                   "the pantry or on the grocery list.",
                                   "Caught now, it's one trip to the store instead of a change of plans.",
                                   [f"recipe:{recipe.recipe_id}"], f"Add {need[0]} to the grocery list.", REAL, app="kitchen"))
    return out


def overtime_and_training(context, today: date) -> list[Finding]:
    """Overtime this pay week, and training days missed this week (said
    without guilt: rest counts, DEC-0014)."""
    book = getattr(context, "dungeon", None)
    if book is None or not book.dungeons:
        return []
    from core.the_loop import week
    from core.web_dungeon import dungeon_view

    overtime = sum(dungeon_view(context, d, book.runs, today)["week"]["overtime"] for d in book.dungeons)
    rows = [r for r in week(context, today).get("rows", []) if r.get("kind") == "training"]
    missed = sum(1 for r in rows for c in r["cells"] if c["status"] == "missed")
    if overtime <= 0 or not missed:
        return []
    return [Finding(f"overtime_training:{today - timedelta(days=today.weekday())}", "A heavy work week",
                    f"{overtime:g} hours of overtime this week, and {missed} training day{'s' if missed != 1 else ''} "
                    "didn't happen.", "Long weeks take it out of you; the plan can bend to fit them.",
                    [], "Move a training day to your day off, or call this a rest week.", DERIVED, app="workout")]


def deadline_in_packed_week(context, today: date) -> list[Finding]:
    """A deadline lands in a week the calendar is already full."""
    from core.calendar_view import calendar_items
    from core.obligations import CLOSED, next_due

    book = getattr(context, "obligations", None)
    if book is None:
        return []
    out = []
    for o in book.obligations:
        due = next_due(o)
        if o.status in CLOSED or due is None or not 0 <= (due - today).days <= 21:
            continue
        monday = due - timedelta(days=due.weekday())
        items = [i for i in calendar_items(context, monday, monday + timedelta(days=6), today)
                 if i["kind"] != "obligation"]
        if len(items) >= PACKED_WEEK:
            out.append(Finding(f"deadline_packed:{o.obligation_id}:{due}", "A deadline in a full week",
                               f"{o.title} is due {_say_day(due, today)}, in a week with {len(items)} other things on "
                               "the calendar.", "Done early, it won't compete with everything else that week.",
                               [f"obligation:{o.obligation_id}"], f"Do {o.title} the week before.", DERIVED,
                               unprompted=True, app="compliance"))
    return out


def goal_not_moving(context, today: date) -> list[Finding]:
    """An active mission that hasn't moved in two weeks."""
    missions = getattr(context, "missions", None)
    if missions is None:
        return []
    out = []
    for m in missions.all_missions():
        if m.status != "active" or getattr(m, "recurring_kind", None):
            continue
        moved = _day(m.updated_at or m.created_at)
        if moved is None or (today - moved).days < STALE_DAYS:
            continue
        left = [o for o in m.objectives if not (o.target and o.progress >= o.target)]
        step = left[0].description if left else ""
        out.append(Finding(f"goal_stale:{m.mission_id}", "A mission that hasn't moved",
                           f"{m.name} hasn't moved since {_say_day(moved, today)}" + (f"; next is {step}." if step else "."),
                           "Sometimes a mission is stuck on one step; sometimes it's not the priority anymore.",
                           [f"mission:{m.mission_id}"], f"Take the next step ({step}), or put it on hold." if step else
                           "Decide whether it's still the priority.", REAL, app="missions"))
    return out[:3]


def build_over_budget(context, today: date) -> list[Finding]:
    """A build's budget is used up and it isn't done."""
    from core.homestead_costs import all_build_costs

    out = []
    for c in all_build_costs(context):
        if c.budget > 0 and c.spent >= c.budget and str(c.status).lower() not in ("complete", "completed", "done"):
            out.append(Finding(f"build_budget:{c.project_id}", "A build past its budget",
                               f"{c.name} has used {_money(c.spent)} of its {_money(c.budget)} budget and isn't done.",
                               "Knowing what's left to buy keeps the rest of the plan honest.",
                               [f"project:{c.project_id}"], "Raise the budget or list what's still needed.", REAL,
                               app="business"))
    return out


def cheaper_quote(context, today: date) -> list[Finding]:
    """A policy renews within 45 days and a quote with the same coverage costs less."""
    from core.insurance import compare

    book = getattr(context, "insurance", None)
    if book is None:
        return []
    out = []
    for p in book.policies:
        renews = _day(p.renews)
        if renews is None or not 0 <= (renews - today).days <= RENEWAL_DAYS:
            continue
        best = max((q for q in compare(p, book.quotes_for(p.policy_id)).get("quotes", [])
                    if q["same_coverage"] and q["saves"] > 0), key=lambda q: q["saves"], default=None)
        if best is not None:
            out.append(Finding(f"cheaper_quote:{p.policy_id}:{p.renews}", "A cheaper quote before renewal",
                               f"Your {p.name.lower()} renews {_say_day(renews, today)}; {best['insurer']} quoted the same "
                               f"coverage for {_money(best['saves'])} a year less.",
                               "Switching before the renewal avoids paying another term at the old price.",
                               [f"policy:{p.policy_id}", f"quote:{best['id']}"], "Look at the quote in Insurance.", REAL,
                               unprompted=True, app="insurance"))
    return out


RULES: tuple[Callable, ...] = (bill_before_pay, upkeep_before_trip, deadline_in_packed_week, cheaper_quote,
                               meal_missing_ingredient, overtime_and_training, goal_not_moving, build_over_budget)


def findings(context, today: Optional[date] = None) -> list[Finding]:
    """Everything MIA notices now; never a child's money or work."""
    from core.child_accounts import is_child

    today = today or date.today()
    child = is_child(context)
    out: list[Finding] = []
    for rule in RULES:
        if child and rule in (bill_before_pay, cheaper_quote, overtime_and_training, build_over_budget):
            continue
        try:
            out.extend(rule(context, today))
        except Exception:
            log.exception("Finding rule %s failed", rule.__name__)
    return out


def as_line(f: Finding) -> str:
    """One finding in plain words, with why and the next step."""
    return f"{f.claim} {f.why}" + (f" Next: {f.next_step}" if f.next_step else "")
