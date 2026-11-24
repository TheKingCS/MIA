"""
core.hatch_tracker
====================

Eggs in the incubator, as a mission (Jarvis brainstorm, round 4: homestead). "I set 12 chicken eggs in the incubator
today" makes one mission whose steps are the dated milestones of that bird's incubation: candling, lockdown (stop
turning, raise the humidity) and hatch day, each with its date worked out in code from the day they were set, never by
the model, then the brooder's heat once they're out (about 95 F the first week for chicks, 90 F for waterfowl, 5 F
cooler each week until feathered). "How's the hatch going?" says what day it is and what's next. His guided steps live in Missions, never on
Today (Zac, 2026-11-09).

How: `BIRDS` holds each bird's days (the common extension figures: chicken 21, duck and turkey 28, goose 30, guinea
27, coturnix quail 17, muscovy duck 35, bobwhite quail 23; lockdown three days before hatch); `plan(bird, eggs, set_on)` is the dated milestones (pure);
the action `hatch.start` (act_within_grant, undoable like any mission) makes the mission, its steps ticked by him as
he does them, and keeps the bird and the day set in the settings (`MAP_KEY`, saved inside the change, so "undo that"
takes both back; a finished hatch's entry is dropped) so `say` can count the days. A day set is read looking back
(`set_day`: "yesterday", "Sunday" is the last one, "3 days ago"); a hatch that would be long over is refused.
`MISSION_PREFIX` marks the mission.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

MISSION_PREFIX = "Hatch"
MAP_KEY = "modules.flock.hatches"  # mission id -> {"bird", "eggs", "set"}
# bird: (days to hatch, the days to candle); lockdown is three days before hatch
BIRDS = {
    "chicken": (21, (7, 14)), "duck": (28, (7, 14)), "turkey": (28, (7, 14)), "goose": (30, (7, 14)),
    "guinea": (27, (7, 14)), "quail": (17, (5, 10)),
    "muscovy duck": (35, (7, 14)), "bobwhite quail": (23, (7, 14)),
}
SAID_AS = {"chickens": "chicken", "hen": "chicken", "hens": "chicken", "ducks": "duck", "turkeys": "turkey",
           "geese": "goose", "guineas": "guinea", "guinea fowl": "guinea", "coturnix": "quail",
           "muscovy": "muscovy duck", "muscovies": "muscovy duck", "bobwhite": "bobwhite quail",
           "bobwhites": "bobwhite quail"}
LOCKDOWN_BEFORE = 3
# The brooder's first-week heat (the common extension figures): chicks, turkey poults, keets and quail start near
# 95 F, waterfowl near 90 F; then about 5 F cooler each week until they're feathered (about six weeks).
BROODER_START_F = {"duck": 90, "goose": 90, "muscovy duck": 90}
BROODER_WEEKS = 6


def bird_of(said: str) -> str:
    """Pure logic. The bird he named ("chickens", "geese", "coturnix"), or "" when it isn't one of `BIRDS`."""
    said = " ".join(str(said or "").lower().split())
    for word in sorted((*BIRDS, *SAID_AS), key=len, reverse=True):
        if word in said:
            return SAID_AS.get(word, word)
    return ""


def plan(bird: str, eggs: int, set_on: date) -> list[dict]:
    """Pure logic. The milestones for eggs of `bird` set on `set_on`: [{day, on (ISO), step}], in order: candling,
    lockdown, hatch day, then the brooder's heat once they're out (`BROODER_START_F`, waterfowl a little cooler)."""
    days, candles = BIRDS[bird]
    lockdown = days - LOCKDOWN_BEFORE
    out = [{"day": d, "on": (set_on + timedelta(days=d)).isoformat(),
            "step": f"Candle the eggs on day {d}: take out any that are clear or have stopped growing"}
           for d in candles]
    out.append({"day": lockdown, "on": (set_on + timedelta(days=lockdown)).isoformat(),
                "step": f"Lockdown on day {lockdown}: stop turning, raise the humidity, keep the lid shut"})
    out.append({"day": days, "on": (set_on + timedelta(days=days)).isoformat(),
                "step": f"Hatch day {days}: leave them in until they're dry and fluffy"})
    start = BROODER_START_F.get(bird, 95)
    out.append({"day": days + 1, "on": (set_on + timedelta(days=days + 1)).isoformat(),
                "step": f"Brooder: about {start} F ({round((start - 32) * 5 / 9)} C) under the heat the first week, "
                        f"5 F cooler each week until they're feathered (about {BROODER_WEEKS} weeks); watch them: "
                        f"huddled means too cold, spread to the edges means too hot"})
    return out


def _title(bird: str, eggs: int, set_on: date) -> str:
    """Pure logic. The mission's title."""
    hatch = set_on + timedelta(days=BIRDS[bird][0])
    return f"{MISSION_PREFIX}: {eggs} {bird} egg{'s' if eggs != 1 else ''}, due {hatch:%b} {hatch.day}"


def _params(params) -> tuple[str, int, date]:
    """The bird (chickens unless he names another), the count and the day set, from the action's params;
    ActionError for what's missing or wrong: no eggs, a bird it doesn't know, a day in the future, or one so long
    ago the hatch would be over."""
    bird = bird_of(str(params.get("bird") or "chicken"))  # chickens unless he names another bird
    if not bird:
        raise ActionError(f"Which bird? I know {', '.join(BIRDS)}.")
    try:
        eggs = int(float(params.get("eggs") or 0))
    except (TypeError, ValueError):
        raise ActionError("How many eggs?") from None
    if not 1 <= eggs <= 500:
        raise ActionError("How many eggs?")
    try:
        set_on = date.fromisoformat(str(params.get("set") or date.today().isoformat())[:10])
    except ValueError:
        raise ActionError("Which day were they set?") from None
    if set_on > date.today():
        raise ActionError("They can't have been set in the future.")
    if (date.today() - set_on).days > BIRDS[bird][0] + 7:
        raise ActionError("That hatch would be over by now. Which day were they set?")
    return bird, eggs, set_on


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                         "dec"), start=1)}


def set_day(said: str, today: Optional[date] = None) -> Optional[str]:
    """Pure logic. The day eggs were set, looking back: "today", "yesterday", "N days ago", a weekday (the most recent
    one, today counting; "last" allowed), an ISO date, or a month and day ("Nov 20", "11/20") this year or last;
    None when it isn't a day."""
    today = today or date.today()
    text = " ".join(str(said or "").lower().replace(",", " ").split()).removeprefix("on ")
    if text in ("", "today", "this morning", "tonight"):
        return today.isoformat()
    if text in ("yesterday", "last night"):
        return (today - timedelta(days=1)).isoformat()
    ago = re.fullmatch(r"(\d{1,2}) days? ago", text)
    if ago:
        return (today - timedelta(days=int(ago.group(1)))).isoformat()
    weekday = text.removeprefix("last ").removeprefix("this past ")
    if weekday in _WEEKDAYS:
        back = (today.weekday() - _WEEKDAYS.index(weekday)) % 7
        return (today - timedelta(days=back)).isoformat()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        pass
    m = re.fullmatch(r"([a-z]{3})[a-z]*\.? (\d{1,2})(?:st|nd|rd|th)?", text)
    n = re.fullmatch(r"(\d{1,2})/(\d{1,2})", text)
    month, day = (_MONTHS.get(m.group(1)), int(m.group(2))) if m else (int(n.group(1)), int(n.group(2))) if n else (0, 0)
    if not month:
        return None
    for year in (today.year, today.year - 1):
        try:
            when = date(year, month, day)
        except ValueError:
            return None
        if when <= today:
            return when.isoformat()
    return None


def _describe(context, params) -> str:
    """The card's sentence for `hatch.start`: the mission it makes and its dates."""
    bird, eggs, set_on = _params(params)
    steps = plan(bird, eggs, set_on)
    return (f"Make the mission “{_title(bird, eggs, set_on)}”: "
            + "; ".join(f"day {s['day']} ({date.fromisoformat(s['on']):%b} {date.fromisoformat(s['on']).day})"
                        for s in steps) + ".")


def _active(missions, mission_id: str) -> bool:
    """Whether a hatch's mission is still under way."""
    mission = missions.get_mission(mission_id) if missions is not None else None
    return mission is not None and getattr(mission, "status", "active") == "active"


def _make(context, params) -> str:
    """Does `hatch.start`: one mission, a step for each milestone with its date, the hatch kept in `MAP_KEY` (saved
    inside the change; entries of hatches no longer under way dropped)."""
    from core.person_settings import person_id

    bird, eggs, set_on = _params(params)
    missions = getattr(context, "missions", None)
    if missions is None:
        raise ActionError("Missions aren't on this MIA.")
    steps = plan(bird, eggs, set_on)
    title = _title(bird, eggs, set_on)
    mission = missions.add_mission(title, assigned_by="mia", icon="\U0001F95A", summary=say_plan(bird, eggs, set_on),
                                   profile_id=person_id(context))
    for step in steps:
        on = date.fromisoformat(step["on"])
        missions.add_objective(mission.mission_id, f"{step['step']} ({on:%a %b} {on.day})", "tally", 1)
    config = getattr(context, "config", None)
    if config is not None:
        kept = dict(config.get(MAP_KEY, {}) or {})
        kept = {k: v for k, v in kept.items() if _active(missions, k)}  # a finished or deleted hatch's entry goes
        kept[mission.mission_id] = {"bird": bird, "eggs": eggs, "set": set_on.isoformat()}
        config.set(MAP_KEY, kept)
        if hasattr(config, "save"):
            config.save()  # inside the change: a restart keeps it, and "undo that" puts it back with the mission
    return f"Made the mission “{title}” with {len(steps)} steps. Next: {steps[0]['step'].split(':')[0].lower()}."


def say_plan(bird: str, eggs: int, set_on: date) -> str:
    """Pure logic. The milestones in one sentence."""
    return "; ".join(f"{s['step'].split(':')[0]} ({date.fromisoformat(s['on']):%b} {date.fromisoformat(s['on']).day})"
                     for s in plan(bird, eggs, set_on)) + "."


def say(context, today: Optional[date] = None) -> str:
    """For "how's the hatch going?": each hatch under way (its mission not done), what day it is and what's next;
    said plainly when there's none."""
    today = today or date.today()
    config = getattr(context, "config", None)
    missions = getattr(context, "missions", None)
    kept = dict(config.get(MAP_KEY, {}) or {}) if config is not None else {}
    lines = []
    for mission_id, hatch in kept.items():
        mission = missions.get_mission(mission_id) if missions is not None else None
        if mission is None or getattr(mission, "status", "active") != "active":
            continue
        set_on = date.fromisoformat(hatch["set"])
        day = (today - set_on).days
        coming = [s for s in plan(hatch["bird"], hatch["eggs"], set_on) if s["day"] >= day]
        if coming:
            nxt = coming[0]
            when = "today" if nxt["day"] == day else f"in {nxt['day'] - day} day{'s' if nxt['day'] - day != 1 else ''}"
            lines.append(f"The {hatch['eggs']} {hatch['bird']} eggs are on day {day}; next, "
                         f"{nxt['step'].split(':')[0].lower()} {when}.")
        else:
            lines.append(f"The {hatch['eggs']} {hatch['bird']} eggs are past hatch day (day {day}): tick the "
                         f"mission done when they're out.")
    return " ".join(lines) if lines else ("No eggs in the incubator that I know of. Tell me when you set some (\"I set "
                                          "12 chicken eggs today\") and I'll keep the dates.")


ACTION_TYPES["hatch.start"] = ActionType(
    "hatch.start", "Start The Hatch", {"bird": "/".join(BIRDS), "eggs": "how many", "set": "the day set (YYYY-MM-DD)"},
    _describe, _make)
