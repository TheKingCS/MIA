"""
core.loop_actions
===================

The Loop's actions (DEC-0047, core/the_loop.py) on the action contract:
what the person says about when things happen, in plain words, undoable.

- `loop.set`: a rhythm's days, start, end (a night shift ends the next
  morning), reminder lead, reminder on or off. What's set is theirs:
  learning never overwrites it. Names a rhythm by "work", "chores", its
  name, or a new name (a rhythm of their own).
- `loop.forget`: let MIA learn the days or the times again.
- `loop.delete`: remove a rhythm of their own (work and chores come back
  by themselves; turn their reminder off instead).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.the_loop import clock_text, days_text, parse_clock, parse_days, span_hours

_WORK_WORDS = ("work", "workday", "work day", "shift", "my shift", "job", "the dungeon", "dungeon", "factory", "the plant")
_CHORE_WORDS = ("chores", "chore", "housework", "routines", "household")


def _book(context):
    return _need(context, "loop")


def _find(context, params, create: bool = False):
    from core.the_loop import ensure_rhythms

    book = _book(context)
    ensure_rhythms(context)
    wanted = str(params.get("rhythm_id") or "")
    if wanted:
        r = book.get(wanted)
        if r is None:
            raise ActionError("That rhythm isn't there anymore.")
        return r, None
    name = str(params.get("name") or "").strip()
    low = name.lower()
    if not low:
        raise ActionError("Which part of your week? (work, chores, or a name)")
    if low in _WORK_WORDS:
        r = next((x for x in book.rhythms if x.kind == "work"), None)
        if r is None:
            raise ActionError("Set up your dungeon first (Apps → The Dungeon), then its schedule.")
        return r, None
    if low in _CHORE_WORDS:
        r = book.find("routine", "Household")
        if r is None and create:
            return None, ("Chores", "routine", "Household", "🧹")
        if r is None:
            raise ActionError("No chores rhythm yet.")
        return r, None
    r = next((x for x in book.rhythms if x.name.lower() == low), None)
    if r is None and create:
        return None, (name[:40], "custom", "", "🔁")
    if r is None:
        raise ActionError(f"No “{name}” in your loop.")
    return r, None


def _values(params) -> dict:
    out = {}
    try:
        if params.get("days") not in (None, ""):
            out["days"] = parse_days(params["days"])
        for f in ("start", "end"):
            if params.get(f) not in (None, ""):
                out[f] = parse_clock(params[f])
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    if params.get("lead_minutes") not in (None, ""):
        try:
            lead = int(float(params["lead_minutes"]))
        except (TypeError, ValueError):
            raise ActionError("The reminder lead is minutes, a number.") from None
        if not 0 <= lead <= 240:
            raise ActionError("Remind between 0 and 240 minutes before.")
        out["lead_minutes"] = lead
    if params.get("remind") not in (None, ""):
        out["remind"] = str(params["remind"]).strip().lower() in ("1", "true", "yes", "on")
    if not out:
        raise ActionError("What about it? (days, when it starts and ends, the reminder)")
    return out


def _set_describe(context, params) -> str:
    r, new = _find(context, params, create=True)
    v = _values(params)
    name = r.name if r else new[0]
    bits = []
    if "days" in v:
        bits.append(days_text(v["days"]))
    if "start" in v or "end" in v:
        start, end = v.get("start", r.start if r else ""), v.get("end", r.end if r else "")
        hours = span_hours(start, end)
        bits.append((clock_text(start) or "?") + (f" – {clock_text(end)}" if end else "")
                    + (f" ({hours:g} h)" if hours else ""))
    if "lead_minutes" in v:
        bits.append(f"remind {v['lead_minutes']} min before")
    if "remind" in v:
        bits.append("reminder on" if v["remind"] else "reminder off")
    return f"{'Your loop: ' if r else 'New in your loop: '}{name}: " + ", ".join(bits)


def _set_execute(context, params) -> str:
    r, new = _find(context, params, create=True)
    v = _values(params)
    book = _book(context)
    if r is None:
        name, kind, ref, icon = new
        r = book.add(name, kind, ref, icon)
    book.set(r.rhythm_id, **v)
    if r.kind == "work":
        from core.the_loop import plan_week

        plan_week(context)
    return f"Got it. MIA will remind you {r.lead_minutes} min before." if r.remind and r.start else "Got it."


def _forget_describe(context, params) -> str:
    r, _ = _find(context, params)
    what = "times" if str(params.get("what") or "times").lower().startswith("t") else "days"
    return f"Let MIA learn {r.name}'s {what} again from what you actually do"


def _forget_execute(context, params) -> str:
    r, _ = _find(context, params)
    what = "times" if str(params.get("what") or "times").lower().startswith("t") else "days"
    _book(context).forget(r.rhythm_id, what)
    return "She'll learn it again."


def _delete_describe(context, params) -> str:
    r, _ = _find(context, params)
    if r.kind != "custom":
        raise ActionError(f"{r.name} comes back by itself; turn its reminder off instead.")
    return f"Remove {r.name} from your loop"


def _delete_execute(context, params) -> str:
    r, _ = _find(context, params)
    _book(context).delete(r.rhythm_id)
    return "Removed."


def _register() -> None:
    names = {"rhythm_id": "the rhythm", "name": "work, chores, or a name"}
    for kind in (
        ActionType("loop.set", "Set", {**names, "days": "mon-fri, sun-thu, every day…", "start": "9:30 pm",
                                       "end": "6 am", "lead_minutes": "remind this many minutes before",
                                       "remind": "yes / no"}, _set_describe, _set_execute),
        ActionType("loop.forget", "Learn Again", {**names, "what": "times or days"}, _forget_describe, _forget_execute),
        ActionType("loop.delete", "Remove", names, _delete_describe, _delete_execute),
    ):
        ACTION_TYPES[kind.kind] = kind


_register()
