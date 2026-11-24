"""
core.broiler_batch
====================

A batch of meat birds, as a mission (Jarvis brainstorm, round 5: homestead). "I got 25 Cornish cross chicks today"
makes one mission whose steps are dated from the day they came: off the brooder heat once feathered, out to pasture
or a tractor, and processing day for that breed, with about how much feed the batch will eat to get there, worked
out in code from the common figures, never by the model. Guided steps live in Missions (Zac, 2026-11-09).

How: `BREEDS` holds each meat breed's weeks to processing and feed per bird (Cornish cross about 8 weeks and 15 lb
of feed a bird; red rangers and Freedom Rangers about 11 weeks and 20 lb; heritage breeds 16 weeks and more);
`plan(breed, birds, started)` is the dated steps (pure); `broilers.start` (act_within_grant, undoable like any
mission) makes the mission, the batch kept in the settings (`MAP_KEY`, saved inside the change so a restart keeps
it and "undo that" takes it back), the day read looking back (core/hatch_tracker.set_day).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

MISSION_PREFIX = "Meat birds"
MAP_KEY = "modules.flock.broilers"  # mission id -> {"breed", "birds", "started"}
# breed: (weeks to processing, pounds of feed a bird to get there, the weeks off brooder heat)
BREEDS = {"cornish cross": (8, 15, 3), "red ranger": (11, 20, 4), "freedom ranger": (11, 20, 4),
          "heritage": (16, 30, 5)}
SAID_AS = {"cornish": "cornish cross", "cornish x": "cornish cross", "cornish rock": "cornish cross",
           "cornish rocks": "cornish cross", "cx": "cornish cross", "broiler": "cornish cross", "broilers": "cornish cross",
           "red rangers": "red ranger", "rangers": "freedom ranger", "freedom rangers": "freedom ranger",
           "dual purpose": "heritage", "heritage breed": "heritage"}


def breed_of(said: str) -> str:
    """Pure logic. The meat breed he named ("cornish rocks", "freedom rangers"), or "" when it isn't one of `BREEDS`."""
    text = " ".join(str(said or "").lower().split())
    for word in sorted((*BREEDS, *SAID_AS), key=len, reverse=True):
        if word in text:
            return SAID_AS.get(word, word)
    return ""


def plan(breed: str, birds: int, started: date) -> dict:
    """Pure logic. {"steps": [{week, on, step}], "feed_lb", "processing"}: the batch's dated steps, each led by a short
    name before its colon ("Off the heat", "Feed 12 hours on, 12 off"), and the feed it'll eat, from the day the chicks
    came; water is always kept in, even the night before processing."""
    weeks, feed, heat_off = BREEDS[breed]
    on = lambda w: started + timedelta(weeks=w)  # noqa: E731
    steps = [
        {"week": 0, "on": started.isoformat(), "step": "Brooder: about 95 F the first week, 5 F cooler each week; "
                                                       "starter feed (about 20 to 22% protein) and water always"},
        {"week": heat_off, "on": on(heat_off).isoformat(),
         "step": f"Off the heat: by about week {heat_off}, once they're feathered and the nights allow"},
        {"week": heat_off + 1, "on": on(heat_off + 1).isoformat(),
         "step": "Out to pasture or a tractor: move it daily, shade and water every day"},
        {"week": weeks, "on": on(weeks).isoformat(),
         "step": f"Processing day, about week {weeks}: take their feed away the night before, but keep water in"},
    ]
    if breed == "cornish cross":
        steps.insert(2, {"week": 2, "on": on(2).isoformat(),
                         "step": "Feed 12 hours on, 12 off: Cornish cross grow so fast that from about week 2 a "
                                 "schedule keeps their legs and hearts up with them"})
    steps.sort(key=lambda s: s["week"])  # in the order they come
    return {"steps": steps, "feed_lb": round(birds * feed), "processing": on(weeks)}


def _params(params) -> tuple[str, int, date]:
    """The breed (Cornish cross unless he names another), the count and the day they came; ActionError for what's
    missing or wrong."""
    breed = breed_of(str(params.get("breed") or "cornish cross"))
    if not breed:
        raise ActionError(f"Which breed? I know {', '.join(BREEDS)}.")
    try:
        birds = int(float(params.get("birds") or 0))
    except (TypeError, ValueError):
        raise ActionError("How many birds?") from None
    if not 1 <= birds <= 2000:
        raise ActionError("How many birds?")
    try:
        started = date.fromisoformat(str(params.get("started") or date.today().isoformat())[:10])
    except ValueError:
        raise ActionError("Which day did they come?") from None
    if started > date.today():
        raise ActionError("They can't have come in the future.")
    if (date.today() - started).days > BREEDS[breed][0] * 7 + 14:
        raise ActionError("That batch would be processed by now. Which day did they come?")
    return breed, birds, started


def _title(breed: str, birds: int, processing: date) -> str:
    """Pure logic. The mission's title."""
    return f"{MISSION_PREFIX}: {birds} {breed}, processing about {processing:%b} {processing.day}"


def _describe(context, params) -> str:
    """The card's sentence for `broilers.start`: the mission, its processing day and the feed."""
    breed, birds, started = _params(params)
    found = plan(breed, birds, started)
    return (f"Make the mission “{_title(breed, birds, found['processing'])}”: {len(found['steps'])} dated steps; "
            f"about {found['feed_lb']:,} lb of feed to get there.")


def _active(missions, mission_id: str) -> bool:
    """Whether a batch's mission is still under way."""
    mission = missions.get_mission(mission_id) if missions is not None else None
    return mission is not None and getattr(mission, "status", "active") == "active"


def _make(context, params) -> str:
    """Does `broilers.start`: one mission, a step for each dated milestone, the batch kept in `MAP_KEY` (saved inside
    the change; entries of batches no longer under way dropped)."""
    from core.person_settings import person_id

    breed, birds, started = _params(params)
    missions = getattr(context, "missions", None)
    if missions is None:
        raise ActionError("Missions aren't on this MIA.")
    found = plan(breed, birds, started)
    title = _title(breed, birds, found["processing"])
    mission = missions.add_mission(title, assigned_by="mia", icon="\U0001F414",
                                   summary=f"About {found['feed_lb']:,} lb of feed for the batch.",
                                   profile_id=person_id(context))
    for step in found["steps"]:
        on = date.fromisoformat(step["on"])
        missions.add_objective(mission.mission_id, f"{step['step']} ({on:%a %b} {on.day})", "tally", 1)
    config = getattr(context, "config", None)
    if config is not None:
        kept = {k: v for k, v in dict(config.get(MAP_KEY, {}) or {}).items() if _active(missions, k)}
        kept[mission.mission_id] = {"breed": breed, "birds": birds, "started": started.isoformat()}
        config.set(MAP_KEY, kept)
        if hasattr(config, "save"):
            config.save()  # inside the change: a restart keeps it, and "undo that" takes it back with the mission
    return (f"Made the mission “{title}” with {len(found['steps'])} steps. Plan on about {found['feed_lb']:,} lb of "
            f"feed for the batch.")


def say(context, today: Optional[date] = None) -> str:
    """For "how are the meat birds coming?": each batch under way, its week (their first seven days are week 1), what's
    next and the processing day; a kept batch that can't be read is skipped."""
    today = today or date.today()
    config = getattr(context, "config", None)
    missions = getattr(context, "missions", None)
    lines = []
    for mission_id, batch in dict(config.get(MAP_KEY, {}) or {}).items() if config is not None else []:
        if not _active(missions, mission_id):
            continue
        try:
            started = date.fromisoformat(batch["started"])
            found = plan(batch["breed"], batch["birds"], started)
        except (KeyError, ValueError, TypeError):  # a kept batch that can't be read never breaks the rest
            continue
        week = (today - started).days // 7 + 1  # their first seven days are week 1
        coming = [s for s in found["steps"] if date.fromisoformat(s["on"]) >= today]
        nxt = f"; next: {coming[0]['step'].split(':')[0].lower()} ({date.fromisoformat(coming[0]['on']):%b} " \
              f"{date.fromisoformat(coming[0]['on']).day})" if coming else ""
        lines.append(f"The {batch['birds']} {batch['breed']} are in week {week}{nxt}; processing about "
                     f"{found['processing']:%b} {found['processing'].day}.")
    return " ".join(lines) if lines else ("No meat birds that I know of. Tell me when you get some (\"I got 25 "
                                          "Cornish cross chicks today\") and I'll keep the dates.")


ACTION_TYPES["broilers.start"] = ActionType(
    "broilers.start", "Start The Batch", {"breed": "/".join(BREEDS), "birds": "how many", "started": "the day they came"},
    _describe, _make)
