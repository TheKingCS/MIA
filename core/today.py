"""
core.today
============

"Today" (2026-10-01): one list of what needs you today, from every app,
so nobody has to open eight screens to find out. Shown at the top of
Home (gui/home_dashboard.py), on the phone (`/api/today`), and by the
Assistant ("what's on today?").

What it gathers, for the signed-in person (their household's things and
their own):
- **Overdue** first: bills past due, maintenance overdue, tasks past
  their date.
- **Today**: calendar events (in time order), alarms, bills and
  maintenance due today, tasks due today, paydays, birthdays (People &
  Pets), pantry items expiring.
- **Waiting on you**: documents in the inbox to file, email drafts not
  sent yet.
- **Soon** (the next 3 days): bills, maintenance, birthdays.

Maintenance on something that belongs to someone else in the household
(core/ownership.py) is theirs, so it's left off your list.

Facts only, assembled in code; the Assistant only phrases them. Every
source is optional, so a store this MIA doesn't have is just left out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

OVERDUE, TODAY, WAITING, SOON = "overdue", "today", "waiting", "soon"
_ORDER = {OVERDUE: 0, TODAY: 1, WAITING: 2, SOON: 3}
SOON_DAYS = 3


@dataclass
class TodayItem:
    when: str  # overdue | today | waiting | soon
    title: str
    detail: str = ""
    time: str = ""  # "HH:MM" for timed things today
    module_id: str = ""  # where to go to act on it
    record_id: Optional[str] = None
    icon: str = "•"

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def _days(n: int) -> str:
    return "tomorrow" if n == 1 else f"in {n} days"


def _late(n: int) -> str:
    return "1 day late" if n == 1 else f"{n} days late"


def _safe(source: str, gather) -> list[TodayItem]:
    try:
        return list(gather())
    except Exception:  # one broken source never hides the rest of the day
        log.exception("Today: couldn't read %s.", source)
        return []


# ------------------------------------------------------------------ sources


def _calendar(context, today: date):
    from core.daily_occasions import calendar_events_today

    calendar = getattr(context, "calendar", None)
    if calendar is None:
        return
    for event in calendar_events_today(calendar.all_events(), today.isoformat()):
        yield TodayItem(TODAY, event.title, event.notes.splitlines()[0] if event.notes else "", event.time or "",
                        "calendar", event.event_id, "\U0001F4C5")


def _alarms(context, today: date):
    alarms = getattr(context, "alarms", None)
    if alarms is None:
        return
    for alarm in alarms.all_alarms():
        if alarm.enabled and (not alarm.days or today.weekday() in alarm.days):
            yield TodayItem(TODAY, alarm.label or "Alarm", "alarm", alarm.time, "toolbox", None, "⏰")


def _bills(context, today: date):
    from core.budget_manager import days_until_bill_due, days_until_income_due
    from core.region import money

    budget = getattr(context, "budget", None)
    if budget is None:
        return
    for bill in budget.all_bills():
        left = days_until_bill_due(bill, today)
        if left is None:
            continue
        amount = money(bill.amount)
        if left < 0:
            yield TodayItem(OVERDUE, f"Pay {bill.name}", f"{amount}, {_late(-left)}", "", "budget", bill.bill_id, "\U0001F4B8")
        elif left == 0:
            yield TodayItem(TODAY, f"Pay {bill.name}", f"{amount}, due today", "", "budget", bill.bill_id, "\U0001F4B8")
        elif left <= SOON_DAYS:
            yield TodayItem(SOON, f"{bill.name} is due {_days(left)}", amount, "", "budget", bill.bill_id, "\U0001F4B8")
    for source in budget.all_income_sources():
        if days_until_income_due(source, today) == 0:
            yield TodayItem(TODAY, f"Payday: {source.name}", money(source.expected_amount), "", "budget", None,
                            "\U0001F4B0")


def _maintenance(context, today: date):
    from core.maintenance_manager import days_until_due, task_urgency

    maintenance = getattr(context, "maintenance", None)
    if maintenance is None:
        return
    from core.ownership import is_for_me

    assets = {a.asset_id: a for a in maintenance.all_assets()}
    names = {a.asset_id: a.name for a in assets.values()}
    for task in maintenance.all_tasks():
        asset = assets.get(task.asset_id)
        if asset is not None and not is_for_me(context, asset.owner_profile_id):
            continue  # someone else's truck (core/ownership.py)
        readings = [] if task.trigger_type == "calendar" else (maintenance.readings_for_task(task.task_id) or [])
        urgency = task_urgency(task, readings, today)
        title = f"{task.title}: {names.get(task.asset_id, 'maintenance')}"
        if urgency == "overdue":
            left = days_until_due(task, today) if task.trigger_type == "calendar" else None
            yield TodayItem(OVERDUE, title, _late(-left) if left is not None and left < 0 else "due now",
                            "", "maintenance", task.task_id, "\U0001F527")
        elif urgency == "due_soon":
            left = days_until_due(task, today) if task.trigger_type == "calendar" else None
            if left == 0:
                yield TodayItem(TODAY, title, "due today", "", "maintenance", task.task_id, "\U0001F527")
            else:
                yield TodayItem(SOON, title, f"due {_days(left)}" if left else "due soon", "", "maintenance",
                                task.task_id, "\U0001F527")


def _tasks(context, today: date):
    tasks = getattr(context, "tasks", None)
    if tasks is None:
        return
    for task in tasks.all_tasks():
        if task.done or not task.due_date:
            continue
        try:
            due = date.fromisoformat(task.due_date[:10])
        except ValueError:
            continue
        if due < today:
            yield TodayItem(OVERDUE, task.title, _late((today - due).days), "", "toolbox", task.task_id, "✅")
        elif due == today:
            yield TodayItem(TODAY, task.title, "due today", "", "toolbox", task.task_id, "✅")


def _birthdays(context, today: date):
    relationships = getattr(context, "relationships", None)
    if relationships is None:
        return
    for person in relationships.all_people():
        if not person.birthday:
            continue
        try:
            born = date.fromisoformat(person.birthday)
        except ValueError:
            continue
        for ahead in range(SOON_DAYS + 1):
            day = today + timedelta(days=ahead)
            if (born.month, born.day) == (day.month, day.day):
                if ahead == 0:
                    yield TodayItem(TODAY, f"{person.name}'s birthday", "today", "", "relationships", person.person_id,
                                    "\U0001F382")
                else:
                    yield TodayItem(SOON, f"{person.name}'s birthday", _days(ahead), "", "relationships",
                                    person.person_id, "\U0001F382")
                break


def _pantry(context, today: date):
    from core.kitchen_manager import days_until_expiration

    kitchen = getattr(context, "kitchen", None)
    if kitchen is None:
        return
    expiring = []
    for item in kitchen.all_pantry_items():
        left = days_until_expiration(item, today)
        if left is not None and left <= 1:
            expiring.append(item)
    if expiring:
        names = ", ".join(i.name for i in expiring[:4]) + (" and more" if len(expiring) > 4 else "")
        yield TodayItem(TODAY, "Use up soon", names, "", "kitchen", None, "\U0001F96C")


def _waiting(context, today: date):
    inbox = getattr(context, "inbox", None)
    pending = inbox.pending() if inbox is not None else []
    if pending:
        yield TodayItem(WAITING, f"{len(pending)} document{'s' if len(pending) != 1 else ''} to file",
                        "in your inbox", "", "inbox", None, "\U0001F4E5")
    drafts = getattr(context, "email_drafts", None)
    waiting = drafts.open_drafts() if drafts is not None else []
    if waiting:
        yield TodayItem(WAITING, f"{len(waiting)} email draft{'s' if len(waiting) != 1 else ''} not sent",
                        waiting[0].subject or "", "", "", waiting[0].draft_id, "✉")


_SOURCES = (("calendar", _calendar), ("alarms", _alarms), ("bills", _bills), ("maintenance", _maintenance),
            ("tasks", _tasks), ("birthdays", _birthdays), ("pantry", _pantry), ("waiting", _waiting))


def today_items(context, today: Optional[date] = None) -> list[TodayItem]:
    today = today or date.today()
    items: list[TodayItem] = []
    from core.child_accounts import is_child

    child = getattr(context, "config", None) is not None and is_child(context)
    for name, gather in _SOURCES:
        if child and name in ("bills", "maintenance", "waiting"):
            continue  # grown-up things (core/child_accounts.py)
        items += _safe(name, lambda g=gather: g(context, today))
    # Overdue, then today (timed things in time order first), waiting, soon.
    return sorted(items, key=lambda i: (_ORDER[i.when], i.time == "" if i.when == TODAY else 0, i.time))


def describe(items: list[TodayItem], limit: int = 8) -> str:
    """Pure logic. What MIA says for "what's on today?"."""
    if not items:
        return "Nothing needs you today. Enjoy it."
    parts = []
    overdue = [i for i in items if i.when == OVERDUE]
    if overdue:
        parts.append("Overdue: " + "; ".join(f"{i.title} ({i.detail})" for i in overdue[:limit]) + ".")
    today = [i for i in items if i.when == TODAY]
    if today:
        parts.append("Today: " + "; ".join((f"{i.time} " if i.time else "") + i.title + (f" ({i.detail})" if i.detail and i.when == TODAY and not i.time else "")
                                           for i in today[:limit]) + ".")
    waiting = [i for i in items if i.when == WAITING]
    if waiting:
        parts.append("Waiting on you: " + "; ".join(i.title for i in waiting) + ".")
    soon = [i for i in items if i.when == SOON]
    if soon:
        parts.append("Coming up: " + "; ".join(f"{i.title} ({i.detail})" for i in soon[:limit]) + ".")
    return " ".join(parts)
