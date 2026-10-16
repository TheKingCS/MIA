"""
core.calendar_view
====================

The Calendar (Zac, 2026-10-16): "I want the Calendar to be filled and I
want to be able to access it both in the app and on the glasses."

It is filled from everything in MIA that has a date, not only the events
someone typed in: calendar events (with their repeats), upkeep coming due
(maintenance), bills and expected pay, planned meals and meal prep,
training days, and birthdays. Nothing is copied: each item is read from
its own store every time, so finishing a task or paying a bill moves it
off the calendar by itself.

- `calendar_items(context, start, end, today)`: every dated thing in the range.
- `calendar_page(context, today, month)`: the screen: a month grid, and the
  agenda sorted the way Zac sorts everything with a date: **Past Due**
  (things to do whose day has gone by), **Today**, and **Due Soon** (the
  next two weeks, by day). Served as `/api/calendar`.

Adding and removing your own events are actions (`event.add`,
`event.delete` in core/actions.py).
"""

from __future__ import annotations

import calendar as _cal
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

SOON_DAYS = 14
PAST_DAYS = 31

# kind -> (label, the app it belongs to, for its icon and its screen)
KINDS = {
    "event": ("Event", "calendar"),
    "upkeep": ("Upkeep", "maintenance"),
    "bill": ("Bill", "budget"),
    "income": ("Pay", "budget"),
    "meal": ("Meal", "kitchen"),
    "prep": ("Meal Prep", "kitchen"),
    "training": ("Training", "workout"),
    "birthday": ("Birthday", "relationships"),
}


def _item(day: date, kind: str, title: str, detail: str = "", time: str = "", due: bool = False,
          action: Optional[dict] = None, **extra) -> dict:
    label, app = KINDS[kind]
    out = {"date": day.isoformat(), "time": time or "", "title": title, "detail": detail, "kind": kind,
           "kind_label": label, "app": app, "due": due}
    if action:
        out["action"] = action
    out.update(extra)
    return out


def _days(start: date, end: date):
    for i in range((end - start).days + 1):
        yield start + timedelta(days=i)


def _events(context, start: date, end: date) -> list[dict]:
    from core.calendar_manager import occurs_on

    store = getattr(context, "calendar", None)
    if store is None:
        return []
    out = []
    for event in store.all_events():
        for day in _days(start, end):
            if occurs_on(event, day):
                out.append(_item(day, "event", event.title, event.notes or "", event.time or "",
                                 event_id=event.event_id, repeats=event.recurrence or ""))
    return out


def _upkeep(context, start: date, end: date, today: date) -> list[dict]:
    from core.web_equipment import equipment_page

    if getattr(context, "maintenance", None) is None:
        return []
    out = []
    for c in equipment_page(context, "maintenance", today).get("calendar") or []:
        day = date.fromisoformat(c["date"])
        if c.get("overdue") or start <= day <= end:
            out.append(_item(day, "upkeep", f"{c['title']}: {c['asset']}", "past due" if c.get("overdue") else "",
                             due=True, action={"kind": "maintenance.done", "label": "Done",
                                               "params": {"task_id": c["task_id"]}}))
    return out


def _money(context, start: date, end: date, today: date) -> list[dict]:
    from core.budget_manager import (days_until_bill_due, days_until_income_due, next_bill_due_date,
                                     next_income_due_date)
    from core.child_accounts import is_child
    from core.region import money

    budget = getattr(context, "budget", None)
    if budget is None or is_child(context):
        return []
    out = []
    for bill in budget.all_bills():
        due = next_bill_due_date(bill)
        days = days_until_bill_due(bill, today)
        if due is None or days is None:
            continue
        if days < 0 or start <= due <= end:
            out.append(_item(due, "bill", f"{bill.name} {money(bill.amount)}", "past due" if days < 0 else "",
                             due=True, action={"kind": "bill.pay", "label": "Mark Paid", "params": {"bill_id": bill.bill_id}}))
    for source in budget.all_income_sources():
        nxt = next_income_due_date(source)
        days = days_until_income_due(source, today)
        if nxt is None or days is None:
            continue
        if days < 0 or start <= nxt <= end:
            out.append(_item(nxt, "income", f"{source.name} {money(source.expected_amount)}",
                             "expected, not marked received" if days < 0 else "expected", due=True,
                             action={"kind": "income.receive", "label": "Mark Received",
                                     "params": {"source_id": source.source_id}}))
    return out


def _fitness(context, start: date, end: date, today: date) -> list[dict]:
    from core.fitness_manager import WEEKDAYS

    fit = getattr(context, "fitness", None)
    if fit is None:
        return []
    kitchen = getattr(context, "kitchen", None)

    def recipe_name(recipe_id) -> str:
        recipe = kitchen.get_recipe(recipe_id) if kitchen is not None and recipe_id else None
        return recipe.name if recipe is not None else "a meal"

    out = []
    first = max(start, today)  # what's planned from today on
    for day in _days(first, end):
        for meal, slot in sorted(fit.planned(day.isoformat()).items(),
                                 key=lambda kv: ("breakfast", "lunch", "dinner", "snack").index(kv[0])
                                 if kv[0] in ("breakfast", "lunch", "dinner", "snack") else 9):
            rid = slot.get("recipe_id") if isinstance(slot, dict) else slot
            out.append(_item(day, "meal", f"{meal.capitalize()}: {recipe_name(rid)}"))
    for prep in fit.prep_sessions(first.isoformat(), end.isoformat()):
        out.append(_item(date.fromisoformat(prep["date"]), "prep", f"Meal prep: {recipe_name(prep.get('recipe_id'))}",
                         due=True))
    try:
        training = fit.plan.get("training") or {}
    except Exception:
        training = {}
    days = set(training.get("days") or [])
    if days and training.get("rotation"):
        for day in _days(first, end):
            if WEEKDAYS[day.weekday()] in days:
                out.append(_item(day, "training", "Training day"))
    return out


def _birthdays(context, start: date, end: date) -> list[dict]:
    store = getattr(context, "relationships", None)
    if store is None:
        return []
    out = []
    for who in list(store.all_people()) + list(store.all_pets()):
        raw = getattr(who, "birthday", "") or ""
        try:
            born = date.fromisoformat(raw)
        except ValueError:
            continue
        for year in range(start.year, end.year + 1):
            try:
                day = date(year, born.month, born.day)
            except ValueError:  # Feb 29 in a non-leap year: no made-up date
                continue
            if start <= day <= end:
                out.append(_item(day, "birthday", f"{who.name}'s birthday"))
    return out


def calendar_items(context, start: date, end: date, today: Optional[date] = None) -> list[dict]:
    """Every dated thing between `start` and `end` (and anything past due), sorted."""
    today = today or date.today()
    found: list[dict] = []
    for name, source in (("events", lambda: _events(context, start, end)),
                         ("upkeep", lambda: _upkeep(context, start, end, today)),
                         ("money", lambda: _money(context, start, end, today)),
                         ("fitness", lambda: _fitness(context, start, end, today)),
                         ("birthdays", lambda: _birthdays(context, start, end))):
        try:
            found.extend(source())
        except Exception:  # one store failing never empties the calendar
            log.exception("Calendar: the %s source failed", name)
    return sorted(found, key=lambda i: (i["date"], i["time"] or "99", i["title"].lower()))


def day_label(day: date, today: date) -> str:
    """Pure logic. "Today", "Tomorrow", "Sat, Oct 18"."""
    if day == today:
        return "Today"
    if day == today + timedelta(days=1):
        return "Tomorrow"
    return f"{day:%a}, {day:%b} {day.day}"


def calendar_page(context, today: Optional[date] = None, month: Optional[str] = None) -> dict:
    """The Calendar screen: a month grid and the Past Due / Today / Due Soon agenda."""
    today = today or date.today()
    try:
        year, mon = (int(x) for x in (month or "").split("-")[:2])
        first = date(year, mon, 1)
    except ValueError:
        first = today.replace(day=1)
    last = first.replace(day=_cal.monthrange(first.year, first.month)[1])
    soon_end = today + timedelta(days=SOON_DAYS)
    start = min(first, today)
    end = max(last, soon_end)
    items = calendar_items(context, start, end, today)

    iso_today = today.isoformat()
    past_due = [i for i in items if i["due"] and i["date"] < iso_today]
    todays = [i for i in items if i["date"] == iso_today]
    soon = []
    for day in _days(today + timedelta(days=1), soon_end):
        on = [i for i in items if i["date"] == day.isoformat()]
        if on:
            soon.append({"date": day.isoformat(), "label": day_label(day, today), "items": on})

    by_date: dict[str, list[dict]] = {}
    for i in items:
        if first.isoformat() <= i["date"] <= last.isoformat():
            by_date.setdefault(i["date"], []).append(i)
    grid = []
    lead = first.weekday()  # Monday-first weeks
    for i in range(lead):
        d = first - timedelta(days=lead - i)
        grid.append({"date": d.isoformat(), "day": d.day, "in_month": False, "today": d == today, "count": 0, "kinds": []})
    for d in _days(first, last):
        on = by_date.get(d.isoformat(), [])
        grid.append({"date": d.isoformat(), "day": d.day, "in_month": True, "today": d == today, "count": len(on),
                     "kinds": sorted({i["kind"] for i in on}),
                     "late": any(i["due"] and i["date"] < iso_today for i in on)})
    while len(grid) % 7:
        d = date.fromisoformat(grid[-1]["date"]) + timedelta(days=1)
        grid.append({"date": d.isoformat(), "day": d.day, "in_month": False, "today": d == today, "count": 0, "kinds": []})
    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = last + timedelta(days=1)
    return {
        "as_of": iso_today,
        "month": {"key": f"{first:%Y-%m}", "label": f"{first:%B %Y}", "prev": f"{prev_month:%Y-%m}",
                  "next": f"{next_month:%Y-%m}", "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                  "days": grid, "by_date": by_date},
        "past_due": past_due, "today": todays, "soon": soon,
        "kinds": [{"kind": k, "label": label, "app": app} for k, (label, app) in KINDS.items()],
        "forms": {"event": {"noun": "event", "id_param": "event_id", "fields": [
            {"name": "title", "label": "What", "type": "text", "required": True, "options": [], "default": None},
            {"name": "date", "label": "Date", "type": "date", "required": True, "options": [], "default": iso_today},
            {"name": "time", "label": "Time", "type": "text", "required": False, "options": [], "default": None},
            {"name": "recurrence", "label": "Repeats", "type": "choice", "required": False,
             "options": ["", "weekly", "biweekly", "monthly", "yearly"], "default": ""},
            {"name": "notes", "label": "Notes", "type": "text", "required": False, "options": [], "default": None},
        ]}},
    }
