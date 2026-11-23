"""
core.homestead_year
=====================

The homestead's year at a glance (Jarvis brainstorm 4.4; Zac, 2026-11-23: "homestead skills"): the next twelve months,
month by month, from his own records, never a generic calendar:

- **The garden** (core/garden_plans.schedule, from his confirmed garden plans' frost dates): when each crop starts
  indoors, goes out (transplanted or sown) and comes ready to harvest; the harvest is when the canning and storing come.
- **Upkeep** (core/maintenance_manager.next_due_date): each recurring calendar task's due dates in the year (a task
  every 30 days shows each month it falls in).

`year(context, today)` is the months, each {month: "2027-04", label: "April 2027", items: [...]} with the empty ones left
out; `say` reads the next few months out ("what's coming on the homestead this year?"). Everything here is already a
record of his: this only puts it in order.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

MONTHS = 12
SAID_MONTHS = 3


def _key(day: date) -> str:
    """Pure logic. A day's month as "2027-04"."""
    return f"{day.year:04d}-{day.month:02d}"


def garden_items(plans: list, today: date, end: date) -> list[tuple[date, str]]:
    """Pure logic. Each confirmed garden plan's crop dates between today and end: (day, "Start tomatoes indoors")."""
    from core.garden_plans import CROPS, parse_day, schedule

    out = []
    for plan in plans:
        if getattr(plan, "kind", "") != "garden" or getattr(plan, "status", "") != "confirmed":
            continue
        for year in (today.year, today.year + 1):
            last = parse_day(plan.last_frost, year)
            if last is None:
                continue
            first = parse_day(getattr(plan, "first_frost", ""), year)
            for item in plan.crops:
                crop = CROPS.get(str(item.get("crop") if isinstance(item, dict) else item))
                if crop is None:
                    continue
                when = schedule(crop, last, first)
                name = crop.name.lower()
                for day, what in ((when["start_indoors"], f"Start {name} indoors"),
                                  (when["out"], f"{'Transplant' if when['how'] == 'transplant' else 'Sow'} {name}"),
                                  (when["harvest"], f"{crop.name} ready to harvest (time to can or store)")):
                    if day is not None and today <= day <= end:
                        out.append((day, what))
    return sorted(set(out))


def upkeep_items(tasks: list, today: date, end: date) -> list[tuple[date, str]]:
    """Pure logic. Each recurring calendar task's due dates between today and end: (day, title)."""
    from core.maintenance_manager import next_due_date

    out = []
    for task in tasks:
        if getattr(task, "trigger_type", "calendar") != "calendar" or not task.interval_days:
            continue
        due = next_due_date(task)
        if due is None:
            continue
        while due < today:
            due += timedelta(days=task.interval_days)
        while due <= end:
            out.append((due, task.title))
            due += timedelta(days=task.interval_days)
    return sorted(out)


def year(context, today: Optional[date] = None) -> list[dict]:
    """The next MONTHS months with something in them: each {month, label, items: [(day ISO, what)]}."""
    today = today or date.today()
    end = date(today.year + 1, today.month, 1) - timedelta(days=1)
    found: list[tuple[date, str]] = []
    plans = getattr(context, "project_plans", None)
    upkeep = getattr(context, "maintenance", None)
    for read in ((lambda: garden_items(plans.listed(), today, end)) if plans is not None else None,
                 (lambda: upkeep_items(upkeep.all_tasks(), today, end)) if upkeep is not None else None):
        if read is None:
            continue
        try:
            found += read()
        except Exception:  # noqa: BLE001 - one record that can't be read never stops the rest
            log.exception("Homestead year: a source couldn't be read")
    months: dict[str, dict] = {}
    for day, what in sorted(found):
        m = months.setdefault(_key(day), {"month": _key(day), "label": day.strftime("%B %Y"), "items": []})
        m["items"].append((day.isoformat(), what))
    return [months[k] for k in sorted(months)]


def say(context, today: Optional[date] = None) -> str:
    """For "what's coming on the homestead this year?": the next few months with something in them."""
    months = year(context, today)
    if not months:
        return ("Nothing on the homestead's year yet: confirm a garden plan in the Planner (with your frost dates) or "
                "add upkeep with how often it's due, and the months fill in.")
    parts = []
    for m in months[:SAID_MONTHS]:
        items = m["items"]
        shown = "; ".join(what for _day, what in items[:5]) + (f"; and {len(items) - 5} more" if len(items) > 5 else "")
        parts.append(f"{m['label']}: {shown}.")
    more = len(months) - SAID_MONTHS
    return " ".join(parts) + (f" Then {more} more month{'s' if more != 1 else ''} with something in them." if more > 0
                              else "")
