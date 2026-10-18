"""
core.chronicle
================

The Chronicle (DEC-0028, the game layer's eighth idea): the story of
your week, and of your year, told from what really happened.

Each week (Monday to Sunday) is a chapter: a name ("The Training Week"),
a few plain sentences, and the highlights. The chapter is ready on
Sunday; before then it's "so far". The yearly edition tells the year the
same way, with its biggest week and busiest month.

Facts are put together here, in code: the history (core/life_events.py,
undone changes left out), journal entries and finished expeditions. No
model writes it, so it's never made up. A quiet week is never a failure
(DEC-0014): it's "A Quiet Week", and rest counts too. Money is never in
a child's Chronicle (events_for already leaves it out).
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

WEEKS_SHOWN = 8

# (key, event types, chapter name, the lead sentence when it's the week's
# biggest thread, how to say the count)
THREADS = (
    ("quests", ("mission_completed", "questline_finished"), "The Questing Week", "Quests were the story.",
     lambda n: f"You finished {_n(n, 'mission')}."),
    ("training", ("workout_logged", "training_done"), "The Training Week", "This was a week of sweat.",
     lambda n: f"You trained {_times(n)}."),
    ("practice", ("skill_practice", "skill"), "The Practice Week", "You kept sharpening your skills.",
     lambda n: f"You practiced your skills {_times(n)}."),
    ("upkeep", ("maintenance_done",), "The Week You Kept Things Running", "You kept everything running.",
     lambda n: f"You kept your gear in shape with {_n(n, 'upkeep job')}."),
    ("money", ("bill_paid", "debt_payment"), "The Week Of Settling Accounts", "You took the fight to your money.",
     lambda n: f"You made {_n(n, 'payment')} on bills and debts."),
    ("kitchen", ("meal_logged", "prep_done"), "The Kitchen Week", "The kitchen was busy.",
     lambda n: f"You cooked {_n(n, 'time', 'times') if n > 2 else _times(n)}."),
    ("eating", ("food_logged",), "The Well-Fed Week", "You fed yourself well.",
     lambda n: f"You logged what you ate on {_n(n, 'day')}."),
    ("crafting", ("build_finished",), "The Maker's Week", "Sawdust everywhere: you built things.",
     lambda n: f"You finished {_n(n, 'build')} in the workshop."),
    ("growing", ("harvest", "batch_planted"), "The Harvest Week", "The garden came through.",
     lambda n: f"You planted or harvested {_times(n)}."),
    ("tasks", ("task_done", "project_completed"), "The Week Of Getting Things Done", "You got things done.",
     lambda n: f"You checked off {_n(n, 'task')}."),
    ("people", ("caught_up",), "A Week For People", "It was a week for people.",
     lambda n: f"You caught up with {_n(n, 'person', 'people')}."),
    ("journal", (), "The Thoughtful Week", "You made time to think.",
     lambda n: f"You wrote {_n(n, 'journal entry', 'journal entries')}."),
    ("trips", ("explored",), "The Week Of Adventure", "Adventure called, and you answered.",
     lambda n: f"You finished {_n(n, 'expedition')}."),
)
TYPE_THREAD = {t: key for key, types, *_ in THREADS for t in types}


def _n(n: int, one: str, many: str = "") -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _times(n: int) -> str:
    return "once" if n == 1 else "twice" if n == 2 else f"{n} times"


def week_bounds(day: date) -> tuple[date, date]:
    """Pure logic. The Monday and Sunday of the week `day` is in."""
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def _span(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start:%b} {start.day}–{end.day}"
    return f"{start:%b} {start.day} – {end:%b} {end.day}"


def _gather(context, since: date, until: date) -> list[tuple[str, str, str]]:
    """Everything in the range as (day, thread, highlight line)."""
    from core.life_events import AUDIT_ONLY, events_for, reversed_ids

    items: list[tuple[str, str, str]] = []
    events = events_for(context, since.isoformat(), until.isoformat())
    gone = reversed_ids(events)
    fed: set[str] = set()
    for e in events:
        thread = TYPE_THREAD.get(e.type)
        if not thread or e.event_id in gone or e.type in AUDIT_ONLY:
            continue
        if thread == "eating":  # counted once a day, never a highlight (it's every meal)
            if e.day not in fed:
                fed.add(e.day)
                items.append((e.day, thread, ""))
            continue
        items.append((e.day, thread, e.summary))
    journal = getattr(context, "journal", None)
    if journal is not None:
        for entry in journal.all_entries():
            day = (entry.created_at or "")[:10]
            if since.isoformat() <= day <= until.isoformat():
                items.append((day, "journal", ""))
    expeditions = getattr(context, "expeditions", None)
    if expeditions is not None:
        for x in expeditions.all_expeditions():
            if x.end_date and since.isoformat() <= x.end_date <= until.isoformat():
                items.append((x.end_date, "trips", f"Finished the expedition {x.name}"))
    return items


def tell(items: list[tuple[str, str, str]]) -> dict:
    """Pure logic. A chapter's name, story and highlights from its items."""
    tally = Counter(thread for _d, thread, _h in items)
    if not tally:
        return {"name": "A Quiet Week", "story": ["Nothing was recorded. Rest counts too: the next page is blank and waiting."],
                "highlights": [], "tally": [], "total": 0}
    order = [t for t in THREADS if tally.get(t[0])]
    order.sort(key=lambda t: -tally[t[0]])  # stable: ties keep THREADS order
    top = order[0]
    story = [top[3]] + [say(tally[key]) for key, _types, _name, _lead, say in order]
    if len(order) >= 4:
        story.append(f"{len(order)} parts of your life moved forward.")
    seen, highlights = set(), []
    for _d, _t, line in sorted(items, key=lambda i: i[0], reverse=True):
        if line and line not in seen:
            seen.add(line)
            highlights.append(line)
    return {"name": top[2], "story": story, "highlights": highlights[:6],
            "tally": [{"key": key, "count": tally[key]} for key, *_ in order], "total": sum(tally.values())}


def week_chapter(items: list, monday: date, today: date) -> dict:
    sunday = monday + timedelta(days=6)
    mine = [i for i in items if monday.isoformat() <= i[0] <= sunday.isoformat()]
    told = tell(mine)
    ready = today >= sunday
    week = monday.isocalendar()[1]
    return {"id": f"{monday.isocalendar()[0]}-W{week:02d}", "kind": "week", "title": f"Week {week}",
            "dates": _span(monday, sunday), "start": monday.isoformat(), "end": sunday.isoformat(),
            "ready": ready, "so_far": not ready, **told,
            "name": told["name"].replace("Week", "Week So Far", 1) if not ready and told["total"] and
            told["name"].endswith("Week") else told["name"]}


def year_edition(items: list, year: int, today: date) -> dict:
    start, end = date(year, 1, 1), date(year, 12, 31)
    mine = [i for i in items if start.isoformat() <= i[0] <= end.isoformat()]
    told = tell(mine)
    ready = today > end
    story = [told["story"][0].replace("week", "year")] + told["story"][1:]
    if mine:
        weeks = Counter(week_bounds(date.fromisoformat(d))[0] for d, _t, _h in mine)
        best, n = max(weeks.items(), key=lambda kv: (kv[1], kv[0]))
        months = Counter(d[:7] for d, _t, _h in mine)
        busiest = max(months.items(), key=lambda kv: (kv[1], kv[0]))[0]
        story.append(f"Your biggest week was Week {best.isocalendar()[1]} ({_span(best, best + timedelta(days=6))}), "
                     f"with {_n(n, 'thing', 'things')} done; your busiest month, "
                     f"{date.fromisoformat(busiest + '-01'):%B}.")
    name = told["name"].replace("Week", "Year") if told["total"] else "A Quiet Year"
    return {"id": str(year), "kind": "year", "title": str(year) if ready else f"{year} So Far",
            "dates": f"Jan 1 – {'Dec 31' if ready else f'{today:%b} {today.day}'}", "start": start.isoformat(),
            "end": end.isoformat(), "ready": ready, "so_far": not ready, **told, "name": name, "story": story}


def chronicle_page(context, today: Optional[date] = None) -> dict:
    """This week (or the one that just ended, on a Sunday), the weeks
    before it that have a story, and the yearly editions."""
    today = today or date.today()
    since = date(today.year - 1, 1, 1)
    try:
        items = _gather(context, since, today)
    except Exception:
        log.exception("Chronicle: gathering failed")
        items = []
    monday = week_bounds(today)[0]
    this_week = week_chapter(items, monday, today)
    weeks = [week_chapter(items, monday - timedelta(weeks=k), today) for k in range(1, WEEKS_SHOWN + 1)]
    first = min((d for d, _t, _h in items), default=None)
    weeks = [w for w in weeks if first is not None and w["end"] >= first]
    years = [year_edition(items, today.year, today)]
    if any(d < f"{today.year}-01-01" for d, _t, _h in items):
        years.append(year_edition(items, today.year - 1, today))
    from core.memory_vault import photos_between

    for chapter in [this_week, *weeks, *years]:
        chapter["photos"] = photos_between(context, chapter["start"], chapter["end"])  # the memory vault's
    return {"available": True, "as_of": today.isoformat(), "this_week": this_week, "weeks": weeks, "years": years}
