"""
core.presence
===============

Presence (DEC-0044, docs/UX_SYSTEM_AUDIT.md): what matters now, across
everything MIA keeps, in one ranked list, so nobody has to visit eight
screens to find out. Each item says **why** it's there, what **kind** of
thing it is (a deadline, a fact, a suggestion, progress), where it came
from, where to go for detail, and the next useful action when there's
one to propose.

Nothing is stored or worked out twice: every source is the code its own
screen uses.
- **Today** (`core/today.py`): overdue, today, waiting, soon: bills,
  upkeep, tasks, calendar, birthdays, the inbox, drafts.
- **Compliance** (`core/obligations.py`): overdue, the next 30 days,
  unverified ones (a suggestion to check).
- **Homestead goods** (`core/goods.py`): batches to sell first or past
  their sell-by; an open market day.
- **Chickens** (`core/flock.py`): a dozen or more loose eggs (a carton's
  worth).
- **Freedom** (`core/freedom.py`) and the **active mission's** next
  objective: progress, never urgent.

Ranked by urgency (overdue deadlines first, progress last). Facts come
from the stores; "suggestion" items say they're suggestions. A child sees
only what's theirs (no money, no compliance).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

NOW_LIMIT = 7


@dataclass
class Item:
    key: str  # stable, for a surface to remember what it showed
    title: str
    why: str
    kind: str  # deadline | fact | suggestion | progress
    urgency: int  # 0-100
    app: str  # the app it belongs to (module id)
    detail: str = ""
    action: Optional[dict] = None  # an action kind to propose (core/actions.py)
    href: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _safe(name: str, gather) -> list[Item]:
    try:
        return gather()
    except Exception:  # one store failing never empties Presence
        log.exception("Presence: the %s source failed", name)
        return []


def _today(context, today: date) -> list[Item]:
    from core.today import OVERDUE, SOON, TODAY, WAITING, today_items

    weight = {OVERDUE: 90, TODAY: 72, WAITING: 50, SOON: 30}
    kind = {OVERDUE: "deadline", TODAY: "deadline", WAITING: "fact", SOON: "deadline"}
    why = {OVERDUE: "It's past due.", TODAY: "It's due today.", WAITING: "It's waiting on you.",
           SOON: "Coming up in the next few days."}
    out = []
    for i, t in enumerate(today_items(context, today)):
        out.append(Item(key=f"today:{t.module_id}:{t.record_id or i}:{t.title}", title=t.title, why=why[t.when],
                        detail=t.detail, kind=kind[t.when], urgency=weight[t.when] - min(i, 5), app=t.module_id or "",
                        action=t.action))
    return out


def _compliance(context, today: date) -> list[Item]:
    from core.child_accounts import is_child
    from core.obligations import CLOSED, state

    book = getattr(context, "obligations", None)
    if book is None or is_child(context):
        return []
    out, unverified = [], 0
    for o in book.obligations:
        if o.status in CLOSED:
            continue
        st = state(o, today)
        if not st["verified"]:
            unverified += 1
        if st["where"] == "overdue":
            out.append(Item(f"obligation:{o.obligation_id}", o.title, f"It was due {st['due']}." +
                            ("" if st["verified"] else " Not verified yet."), "deadline", 95, "compliance",
                            detail=o.authority))
        elif st["where"] == "upcoming":
            days = st["days"]
            out.append(Item(f"obligation:{o.obligation_id}", o.title,
                            ("Due today." if days == 0 else f"Due in {days} days ({st['due']}).") +
                            ("" if st["verified"] else " Not verified yet: check the source."), "deadline",
                            85 if days <= 7 else 60, "compliance", detail=o.authority))
    if unverified:
        out.append(Item("obligations:unverified", f"{unverified} {'obligation' if unverified == 1 else 'obligations'} to verify",
                        "A deadline isn't one until you've checked its official source.", "suggestion", 25,
                        "compliance"))
    return out


def _goods(context, today: date) -> list[Item]:
    from core.child_accounts import is_child
    from core.web_craft import goods_section

    if is_child(context) or getattr(context, "craft_recipes", None) is None:
        return []
    section = goods_section(context, today)
    out = []
    if section.get("market"):
        m = section["market"]
        out.append(Item(f"market:{m['id']}", f"Market day open{' at ' + m['place'] if m['place'] else ''}",
                        f"{m['sold']:g} sold so far, {m['revenue_text']} taken in. Close it when you're done.",
                        "fact", 65, "workshop", href="workshop.html#goods"))
    for g in section["goods"]:
        past = [lot for lot in g["lots"] if lot["state"] == "past"]
        first = [lot for lot in g["lots"] if lot["state"] == "sell first"]
        if past:
            out.append(Item(f"goods:past:{g['recipe_id']}", f"{g['name']}: past its sell-by",
                            f"{sum(lot['left'] for lot in past):g} left from batches past their sell-by: sell or toss.",
                            "suggestion", 58, "workshop", href="workshop.html#goods"))
        elif first:
            out.append(Item(f"goods:first:{g['recipe_id']}", f"Sell the oldest {g['name']} first",
                            f"{sum(lot['left'] for lot in first):g} near their sell-by.", "suggestion", 40, "workshop",
                            href="workshop.html#goods"))
    return out


def _flock(context, today: date) -> list[Item]:
    from core.flock import figures

    book = getattr(context, "flock", None)
    if book is None:
        return []
    out = []
    for f in book.flocks:
        loose = figures(f, book.entries, today)["loose"]
        if loose >= 12:
            out.append(Item(f"flock:{f.flock_id}:loose", f"{loose:g} loose eggs from {f.name}",
                            "That's at least a carton: into cartons for the stand, or into the bakery.", "suggestion",
                            33, "flock", href="flock.html"))
    return out


def _freedom(context, today: date) -> list[Item]:
    from core.child_accounts import is_child
    from core.freedom import freedom_page

    if is_child(context):
        return []
    page = freedom_page(context, today)
    if not page.get("available"):
        return []
    p = page["plan"]
    if not p["goal"]:
        return [Item("freedom:setup", "Set up your freedom plan",
                     "What a month takes and what you've saved: then MIA can estimate the day.", "suggestion", 15,
                     "freedom", href="freedom.html")]
    week = next((x for x in page["periods"] if x["id"] == "week"), {})
    lead = ("The fund is full." if p["ready"] else f"About {p['days']:,} days to go." if p["days"] is not None
            else p["why_no_date"])
    return [Item("freedom:progress", f"Freedom: {p['progress_pct']:g}% of the fund" if p["progress_pct"] is not None
                 else "Freedom", f"{lead} This week: {week.get('total_text', '—')}.", "progress", 20, "freedom",
                 href="freedom.html")]


def _missions(context, today: date) -> list[Item]:
    missions = getattr(context, "missions", None)
    if missions is None:
        return []
    active = [m for m in missions.all_missions() if m.status == "active"]
    out = []
    for m in sorted(active, key=lambda m: m.updated_at or m.created_at, reverse=True)[:2]:
        left = [o for o in m.objectives if not (o.target and o.progress >= o.target)]
        if not left:
            continue
        o = left[0]
        progress = f" ({o.progress:g} of {o.target:g})" if o.target and o.target != 1 else ""
        out.append(Item(f"mission:{m.mission_id}", f"{m.name}: {o.description}",
                        f"The next step on an active mission{progress}.", "progress", 22, "missions",
                        href="missions.html"))
    return out


def presence(context, today: Optional[date] = None) -> dict:
    """What matters now ("now", ranked), progress ("path"), and the next
    useful action (the top item that has something to do)."""
    from core.web_surfaces import APPS

    today = today or date.today()
    items: list[Item] = []
    for name, source in (("today", _today), ("compliance", _compliance), ("goods", _goods), ("flock", _flock),
                         ("freedom", _freedom), ("missions", _missions)):
        items.extend(_safe(name, lambda source=source: source(context, today)))
    page_of = {a.module_id: a.page for a in APPS if a.page}
    page_of["maintenance"] = "calendar.html"
    seen, unique = set(), []
    for item in sorted(items, key=lambda i: -i.urgency):
        if item.key in seen:
            continue
        seen.add(item.key)
        item.href = item.href or page_of.get(item.app, "")
        unique.append(item)
    now = [i for i in unique if i.kind != "progress"]
    path = [i for i in unique if i.kind == "progress"]
    nxt = next((i for i in now if i.action or i.href), None)
    quiet = not now
    return {"as_of": today.isoformat(), "now": [i.as_dict() for i in now[:NOW_LIMIT]],
            "more": max(0, len(now) - NOW_LIMIT), "path": [i.as_dict() for i in path],
            "next": nxt.as_dict() if nxt else None, "quiet": quiet,
            "line": ("Nothing needs you right now." if quiet else
                     f"{len(now)} {'thing needs' if len(now) == 1 else 'things need'} you; "
                     f"start with: {now[0].title}.")}


def context_lines(context, today: Optional[date] = None, limit: int = 3) -> str:
    """A few lines for MIA's system message (DEC-0044, context in every
    turn): what the person is working toward (their primary goal and
    why, in their words), their active missions, and the top of Presence.
    Short on purpose: a small model reads all of it every turn. "" when
    there's nothing to say."""
    lines = []
    intents = getattr(context, "intents", None)
    goal = _safe_value(lambda: intents.primary_intent()) if intents is not None else None
    if goal is not None:
        lines.append(f"Working toward: {goal.name}" + (f" (why, in their words: {goal.reason})" if goal.reason else ""))
    missions = getattr(context, "missions", None)
    if missions is not None:
        active = [m.name for m in _safe_value(lambda: missions.all_missions()) or [] if m.status == "active"][:3]
        if active:
            lines.append("Active missions: " + "; ".join(active))
    now = (_safe_value(lambda: presence(context, today)) or {}).get("now") or []
    if now:
        lines.append("Needs them now: " + "; ".join(f"{i['title']} ({i['why'].rstrip('.')})" for i in now[:limit]))
    if not lines:
        return ""
    return "Their world right now (from MIA's records; use it when it's relevant, never invent beyond it):\n" + \
        "\n".join(f"- {line}" for line in lines)


def _safe_value(get):
    try:
        return get()
    except Exception:
        log.exception("Presence context failed")
        return None
