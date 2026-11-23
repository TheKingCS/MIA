"""
core.unusual
==============

Noticing what's unusual (Jarvis brainstorm 2.3; Zac, 2026-11-23: "aware"): a change from his own normal is worth a
word, with what it may mean and what to check first. Each check here is pure logic over his own records, its normal
learned from his history, never a fixed number from somewhere else; the daily check `unusual` offers what it finds
through the communication gate, once per finding.

**Eggs** (`egg_drop`): the hens laying far less than they were. Judged only on days he logged eggs (a day without
an entry isn't a day of zero eggs, and today's count isn't finished): the last three logged days before today, all
within the last five, against the logged days of
the two weeks before (at least five of them). A fall of 40% or more is said, with the causes worth checking in the
order they're most often the answer (the shorter days of fall and winter, a molt, heat, a scare from a predator or a
change, eggs laid somewhere new, short on water, feed or protein, an illness) and, when he logged a bird lost or
added in those weeks, that first.

**Spending** (`spending_over`): a category whose spending this month so far is already half again past its usual
whole month (the average of the last three full months it had spending in, at least two of them), and at least
SPEND_MARGIN over in money; so a month half gone is never compared with a whole one. Said with the amounts.

More checks belong here as their records allow (a bill that didn't come): each its own pure function, its own
fingerprint.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DROP = 0.4  # a fall this large from his own normal is worth a word
RECENT_DAYS = 3
RECENT_WITHIN = 5
BASELINE_DAYS = 14
BASELINE_MIN = 5
CAUSES = ("the shorter days of fall and winter (hens slow down under about 14 hours of light)",
          "a molt (feathers dropping, usually late summer or fall)",
          "heat", "a scare: a predator, a new bird, a move or a change in the coop",
          "eggs laid somewhere new (check under bushes and corners)",
          "too little water, feed or protein (layer feed about 16% protein; treats under a tenth of what they eat)",
          "an illness or mites (look for a pale comb, a dirty vent, lethargy)")


def egg_drop(entries: list, flock_id: str, today: date) -> Optional[dict]:
    """Pure logic. {recent, usual, fall, birds_changed} when this flock's laying fell by DROP or more from its own
    normal over the logged days before today (see the module docstring), else None. `entries` are core/flock.py Entry records."""
    days: dict[date, float] = {}
    birds_changed = False
    for e in entries:
        if e.flock_id != flock_id:
            continue
        try:
            day = date.fromisoformat(str(e.date)[:10])
        except ValueError:
            continue
        if e.kind == "eggs":
            days[day] = days.get(day, 0.0) + float(e.count or 0)
        elif e.kind == "birds" and today - timedelta(days=RECENT_WITHIN + BASELINE_DAYS) <= day <= today:
            birds_changed = True
    logged = sorted((d for d in days if d < today), reverse=True)  # today's count is still coming in
    recent = logged[:RECENT_DAYS]
    if len(recent) < RECENT_DAYS or (today - recent[-1]).days >= RECENT_WITHIN:
        return None
    start = recent[-1] - timedelta(days=BASELINE_DAYS)
    base = [d for d in logged[RECENT_DAYS:] if d >= start]
    if len(base) < BASELINE_MIN:
        return None
    usual = sum(days[d] for d in base) / len(base)
    now = sum(days[d] for d in recent) / len(recent)
    if usual <= 0 or now > usual * (1 - DROP):
        return None
    return {"recent": round(now, 1), "usual": round(usual, 1), "fall": round(1 - now / usual, 2),
            "birds_changed": birds_changed}


SPEND_OVER = 1.5
SPEND_MARGIN = 50.0
SPEND_MONTHS = 3


def _month_bounds(day: date, back: int) -> tuple[date, date]:
    """Pure logic. The first and last day of the month `back` months before the one `day` is in."""
    year, month = day.year, day.month - back
    while month < 1:
        year, month = year - 1, month + 12
    start = date(year, month, 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return start, nxt - timedelta(days=1)


def spending_over(by_month: list, this_month: dict) -> list[dict]:
    """Pure logic. The categories already far past their usual month: each {category, so_far, usual}, the largest
    overrun first. `by_month` holds the last full months' {category: total}, newest first; `this_month` the month so
    far's."""
    out = []
    for category, so_far in this_month.items():
        past = [m[category] for m in by_month[:SPEND_MONTHS] if m.get(category, 0) > 0]
        if len(past) < 2:
            continue
        usual = sum(past) / len(past)
        if so_far >= usual * SPEND_OVER and so_far - usual >= SPEND_MARGIN:
            out.append({"category": category, "so_far": round(so_far, 2), "usual": round(usual, 2)})
    return sorted(out, key=lambda f: f["usual"] - f["so_far"])


def _spending(context, today: date) -> list[dict]:
    """His budget's categories already far past their usual month, from his own expenses."""
    budget = getattr(context, "budget", None)
    if budget is None:
        return []
    months = []
    for back in range(1, SPEND_MONTHS + 1):
        start, end = _month_bounds(today, back)
        months.append(budget.total_expenses_by_category(start.isoformat(), end.isoformat()))
    start, _end = _month_bounds(today, 0)
    return spending_over(months, budget.total_expenses_by_category(start.isoformat(), today.isoformat()))


def _egg_words(name: str, found: dict) -> str:
    """Pure logic. The egg drop in her words, with what to check."""
    first = "You logged birds lost or added lately: that alone can do it. Otherwise, " if found["birds_changed"] else ""
    return (f"{name} have been laying about {found['recent']:g} eggs a day lately, down from their usual "
            f"{found['usual']:g} ({round(found['fall'] * 100)}% fewer). {first}the usual reasons, most likely first: "
            + "; ".join(CAUSES) + ".")


def findings(context, today: date) -> list[dict]:
    """Every unusual thing found in his records today, spending first, then each flock's eggs: each {kind, title,
    text, key}; a record that can't be read leaves its check out."""
    from core.region import money

    out = []
    try:
        for f in _spending(context, today):
            out.append({"kind": "spending", "title": f"{f['category']}: more than usual",
                        "text": (f"You've spent {money(f['so_far'])} on {f['category']} so far this month; a usual "
                                 f"whole month is about {money(f['usual'])}. Worth a look at what's different."),
                        "key": f"spend-{f['category'].lower()}"})
    except Exception:  # noqa: BLE001 - the budget that can't be read never stops the rest
        log.exception("Unusual: the budget couldn't be read")
    book = getattr(context, "flock", None)
    for flock in getattr(book, "flocks", []) or []:
        if max(0, flock.hens) == 0:
            continue
        try:
            found = egg_drop(book.entries, flock.flock_id, today)
        except Exception:  # noqa: BLE001 - one flock that can't be read never stops the rest
            log.exception("Unusual: the flock log couldn't be read")
            continue
        if found:
            out.append({"kind": "eggs", "title": f"{flock.name}: fewer eggs", "text": _egg_words(flock.name, found),
                        "key": f"eggs-{flock.flock_id}"})
    return out


def offer(context, now: datetime) -> list:
    """The daily check's messages through the gate: AMBIENT (worth knowing, never urgent), once per finding per
    week (its fingerprint names the week), so a drop that lasts isn't said every day."""
    from core.communication_gate import AMBIENT, Candidate

    year, week, _ = now.date().isocalendar()
    return [Candidate(topic="unusual", title=f["title"], message=f["text"], urgency=AMBIENT, source="system",
                      fingerprint=f"{f['key']}-{year}-W{week:02d}")
            for f in findings(context, now.date())]


def say(context) -> str:
    """For "anything unusual?": what she found, or that nothing in his records looks off."""
    found = findings(context, date.today())
    if not found:
        return "Nothing in your records looks off from your usual right now."
    return " ".join(f["text"] for f in found)
