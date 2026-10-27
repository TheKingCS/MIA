"""
core.weekly_checkin
=====================

The Sunday check-in (DEC-0047 rule 5; Zac, 2026-10-27): Sunday morning,
a recap of the week just past and the layout of the week ahead.

**Last week** (the seven days ending yesterday): the Chronicle's story of
it (core/chronicle.py), the loop's honest score (runs and chores cleared,
missed days earning nothing; core/the_loop.py), the loot (earned, the
boss bonus, the paychecks that landed), quests finished, and what MIA
noticed (a hard-mode modifier that keeps coming back, overtime bosses,
missed days). **This week** (today and the six days after): each day's
runs with their projected loot, the rhythms and their times, what's on
the calendar (the things outside the loop: adventures), the quests in
progress, and how far along the next dungeon is.

Everything is assembled here from the stores; MIA only says it. It's a
rhythm of its own ("Sunday Check-In", Sundays at 9:00 until the person
moves it), so its reminder comes the loop's way. Marking it done is
`loop.checkin_done` (+15 XP once a week). Served as /api/checkin.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DONE_XP = 15


def _money(x) -> str:
    from core.region import money

    return money(x)


def _day_text(d: date) -> str:
    return f"{d:%a}, {d:%b} {d.day}"


def _span(a: date, b: date) -> str:
    return f"{a:%b} {a.day} – {b:%b} {b.day}" if a.month != b.month else f"{a:%b} {a.day} – {b.day}"


def _loot(context, since: date, until: date) -> dict:
    """Runs cleared in the range: loot, hours, overtime bosses, hard mode, paychecks landed."""
    from core.web_dungeon import banked
    from core.work_dungeon import AFFIX_BY_ID, boss_bonus, loot, split_hours

    book = getattr(context, "dungeon", None)
    out = {"loot": 0.0, "hours": 0.0, "runs": 0, "bosses": 0, "bonus": 0.0, "hard": {}, "banked": 0.0,
           "paychecks": 0, "hourly": False}
    if book is None:
        return out
    for d in book.dungeons:
        out["hourly"] = out["hourly"] or bool(d.hourly)
        split = split_hours(d, book.runs)
        for r in book.runs:
            if r.dungeon_id != d.dungeon_id or r.status != "cleared" or not (since.isoformat() <= r.date <= until.isoformat()):
                continue
            regular, overtime = split.get(r.run_id, (r.hours, 0.0))
            out["runs"] += 1
            out["hours"] += r.hours
            out["loot"] += loot(d, regular, overtime)
            if overtime or r.boss:
                out["bosses"] += 1
                out["bonus"] += boss_bonus(d, overtime)
            for a in r.affixes:
                name = AFFIX_BY_ID[a].name if a in AFFIX_BY_ID else a
                out["hard"][name] = out["hard"].get(name, 0) + 1
        paid = banked(context, d, since, until)
        out["banked"] += sum(p.amount for p in paid)
        out["paychecks"] += len(paid)
    out["loot"], out["bonus"], out["banked"] = round(out["loot"], 2), round(out["bonus"], 2), round(out["banked"], 2)
    return out


def _quests_done(context, since: date, until: date) -> list[str]:
    missions = getattr(context, "missions", None)
    if missions is None:
        return []
    return [m.name for m in missions.all_missions()
            if m.status == "completed" and not m.recurring_template_id
            and since.isoformat() <= (m.updated_at or "")[:10] <= until.isoformat()]


def noticed(loop_rows: list[dict], loot: dict) -> list[str]:
    """Pure logic. What MIA noticed about the week, in plain words."""
    out = []
    for name, n in sorted(loot["hard"].items(), key=lambda x: -x[1]):
        if n >= 2:
            out.append(f"{name} came up {n} times: the dates are in the hard-mode record if you want them.")
    if loot["bosses"]:
        out.append(f"{loot['bosses']} overtime boss{'es' if loot['bosses'] != 1 else ''}"
                   + (f": {_money(loot['bonus'])} of bonus loot." if loot["hourly"] else "."))
    for row in loop_rows:
        if row["missed"] and row["kind"] == "work":
            out.append(f"{row['name']}: {row['missed']} missed, nothing earned "
                       f"{'that day' if row['missed'] == 1 else 'those days'}.")
        elif row["missed"]:
            out.append(f"{row['name']}: {row['cleared']} of {row['scheduled']} days done.")
        elif row["scheduled"] and row["cleared"] == row["scheduled"]:
            out.append(f"{row['name']}: every one cleared. A full clear.")
    return out


def _ahead(context, today: date) -> tuple[list[dict], float]:
    """The next seven days, day by day, and their projected loot."""
    from core.the_loop import clock_text, span_hours
    from core.work_dungeon import loot, split_hours

    book = getattr(context, "loop", None)
    dungeons = getattr(context, "dungeon", None)
    calendar = getattr(context, "calendar", None)
    splits = {d.dungeon_id: split_hours(d, dungeons.runs, include_planned=True) for d in dungeons.dungeons} if dungeons else {}
    store = getattr(context, "recurring_missions", None)
    loop_names = tuple(t.name for t in store.all_templates()) if store is not None else ()
    days, projected = [], 0.0
    for i in range(7):
        day = today + timedelta(days=i)
        key = day.isoformat()
        items = []
        for r in (book.rhythms if book else []):
            if not r.active or r.kind == "checkin" or day.weekday() not in (r.days or []):
                continue
            if r.kind == "work":
                continue  # the run itself is listed below, with its loot
            items.append({"kind": r.kind, "icon": r.icon, "text": r.name, "time": clock_text(r.start)})
        for d in (dungeons.dungeons if dungeons else []):
            run = next((x for x in dungeons.runs if x.dungeon_id == d.dungeon_id and x.date == key), None)
            if run is None:
                continue
            regular, overtime = splits[d.dungeon_id].get(run.run_id, (run.hours, 0.0))
            worth = loot(d, regular, overtime) if d.hourly else None
            if worth is not None and run.status == "planned":
                projected += worth
            r = book.find("work", d.dungeon_id) if book else None
            items.append({"kind": "run", "icon": "⚔" , "boss": bool(overtime or run.boss),
                          "text": f"{d.name}: {run.hours:g} h" + (" (overtime boss)" if overtime or run.boss else ""),
                          "time": clock_text(r.start) if r and r.start else "",
                          "loot_text": _money(worth) if worth is not None else "", "status": run.status})
        for e in _events_on(calendar, day, loop_names):
            items.append({"kind": "event", "icon": "📅", "text": e.title, "time": clock_text(e.time) if e.time else ""})
        items.sort(key=lambda x: (x["time"] == "", x["time"]))
        days.append({"date": key, "label": _day_text(day), "today": i == 0, "items": items})
    return days, round(projected, 2)


def _events_on(calendar, day: date, loop_names: tuple) -> list:
    """The calendar's events on a day, leaving out the ones the loop already
    puts there (a recurring mission's "Feed the animals: 1 today")."""
    from core.calendar_manager import occurs_on

    if calendar is None:
        return []
    return [e for e in calendar.all_events() if occurs_on(e, day) and not (loop_names and e.title.startswith(loop_names))]


def _quests_open(context) -> list[dict]:
    missions = getattr(context, "missions", None)
    if missions is None:
        return []
    out = []
    for m in missions.all_missions():
        if m.status != "active" or m.recurring_template_id:
            continue
        total = sum(max(1.0, float(getattr(o, "target", 1) or 1)) for o in m.objectives) or 1.0
        done = sum(min(max(1.0, float(getattr(o, "target", 1) or 1)), float(getattr(o, "progress", 0) or 0)) for o in m.objectives)
        out.append({"id": m.mission_id, "name": m.name, "icon": m.icon or "⚔", "pct": round(100 * done / total)})
    return sorted(out, key=lambda q: -q["pct"])[:6]


def checkin(context, today: Optional[date] = None) -> dict:
    from core.chronicle import _gather, tell
    from core.child_accounts import is_child
    from core.the_loop import week

    today = today or date.today()
    since, until = today - timedelta(days=7), today - timedelta(days=1)
    child = is_child(context)
    try:
        story = tell(_gather(context, since, until))
    except Exception:
        log.exception("Check-in: the Chronicle couldn't be read")
        story = {"name": "Last Week", "story": [], "highlights": [], "total": 0}
    loop_rows = week(context, today, start=since)["rows"] if getattr(context, "loop", None) is not None else []
    for row in loop_rows:
        row.pop("cells", None)
    loot = _loot(context, since, until) if not child else _loot(None, since, until)
    days, projected = _ahead(context, today)
    nxt = None
    if not child and getattr(context, "dungeon", None) is not None:
        from core.web_dungeon import next_dungeon

        nxt = next_dungeon(context, None, today)
    book = getattr(context, "loop", None)
    runs_ahead = sum(1 for d in days for x in d["items"] if x["kind"] == "run")
    return {
        "available": True, "as_of": today.isoformat(),
        "title": "Sunday Check-In" if today.weekday() == 6 else "Weekly Check-In",
        "last": {"span": _span(since, until), "chapter": story["name"], "story": story["story"],
                 "highlights": story.get("highlights", [])[:5], "loop": loop_rows,
                 "loot": None if child or not loot["runs"] and not loot["paychecks"] else {
                     **loot, "loot_text": _money(loot["loot"]) if loot["hourly"] else "",
                     "bonus_text": _money(loot["bonus"]) if loot["bonus"] else "",
                     "banked_text": _money(loot["banked"]) if loot["paychecks"] else ""},
                 "quests": _quests_done(context, since, until)[:6],
                 "noticed": noticed(loop_rows, loot)},
        "ahead": {"span": _span(today, today + timedelta(days=6)), "days": days, "runs": runs_ahead,
                  "projected": projected, "projected_text": _money(projected) if projected and not child else "",
                  "quests": _quests_open(context), "next_dungeon": nxt},
        "done": bool(book and today.isoformat() in book.checkins), "xp": DONE_XP,
    }


def reminder_line(context, today: date) -> Optional[tuple[str, str]]:
    """The check-in's reminder: the week in one line, or nothing once it's done."""
    book = getattr(context, "loop", None)
    if book is not None and today.isoformat() in book.checkins:
        return None
    c = checkin(context, today)
    bits = []
    for row in c["last"]["loop"]:
        if row["scheduled"]:
            bits.append(f"{row['name']} {row['cleared']} of {row['scheduled']}")
    if c["last"]["loot"] and c["last"]["loot"]["loot_text"]:
        bits.append(f"{c['last']['loot']['loot_text']} loot")
    ahead = f"This week: {c['ahead']['runs']} run{'s' if c['ahead']['runs'] != 1 else ''} planned" + (
        f", {c['ahead']['projected_text']} projected" if c["ahead"]["projected_text"] else "") + "."
    return "📜 Your Sunday check-in", ("Last week: " + ", ".join(bits) + ". " if bits else "") + ahead + " Open it in MIA."
