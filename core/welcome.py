"""
core.welcome
==============

What comes after User Sync (slice 5 of docs/GLASSES_FIRST_BOOT_PLAN.md):
the first mission, the tour of Home, the app menu with its optional
tours, and the moment MIA hands over.

- **Know your system** is a real mission with real objectives: "let's go"
  adds it through core/actions.py, each objective ticks itself as it
  happens, and finishing it pays its XP the way any mission does.
- **Tours** are the real thing's own labels: a tour's steps name items in
  the app's glasses menu (core/glasses.py PANELS), and a test fails if one
  doesn't exist. A paused tour picks up at its step.
- "Say Hey MIA" became "Talk to MIA on your own": a tap makes her listen
  (DEC-0063), there's no wake word.

- `state(context)`: what the glasses show. Served as `/api/welcome`.
- `choose(context, choice, app)`: begin, next, skip, tour, open, later,
  resume, finish.
- `hear(context, text)`: words during it, or None when they aren't for it.
- `talked(context)`: she was spoken to on the glasses.

Each person's own, on their profile. Moving through it isn't a change to
their life, so only the mission goes through the action contract.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from core import first_boot, life_events, person_settings, user_sync
from core.app_intro import app_intro
from core.logger import get_logger

log = get_logger(__name__)

KEY = "welcome.progress"

MISSION = "Know your system"
SUMMARY = "Learn MIA by using her. Finishing this tour is your first completed mission."
MISSION_XP = 100
MEET, HOME, EXPLORE, TALK = range(4)
OBJECTIVES = ("Meet MIA", "Tour your Home", "Explore the app menu", "Talk to MIA on your own")

# Home's steps: (which of Home's first cards lights up, or None; the words).
HOME_TOUR = (
    (0, "Your missions live here: real goals broken into steps, each worth XP. Your first one is already running."),
    (1, "Move from my orb to flip through your apps. The ones you pin come first."),
    (None, "Tap and talk to me any time, wherever you are."),
    (None, "One move back from my orb is everything we've said."),
)
# An app's steps: (its menu item in core/glasses.py, the words).
APP_TOURS = {
    "missions": (("pick", "Pick the mission your card shows here."),
                 ("progress", "Tick off a step as you do it. The XP comes when it's finished."),
                 ("claim", "Anything finished and waiting for you shows up here.")),
    "budget": (("month", "How this month is going, in one look."),
               ("due", "What's coming due, so nothing surprises you."),
               ("debts", "Your debts, and what's left on each.")),
    "workout": (("training", "What's on today, from your plan."),
                ("live", "Start a session here and I'll count it with you."),
                ("milestones", "The big ones you're working toward.")),
    "kitchen": (("recipes", "Your recipe book."),
                ("meals", "What's planned to eat today."),
                ("pantry", "What you've got on hand."),
                ("grocery", "The list for the store.")),
}
IDEAS = ({"label": "Plan my week", "say": "Help me plan my week."},
         {"label": "Set a goal", "say": "Help me set a goal."},
         {"label": "Just talk", "say": ""})

LATER = re.compile(r"(let'?s )?(finish|do (this|it)|continue) later|later|not now", re.I)
NEXT = re.compile(r"next|ok(ay)?|got it|continue|keep going|go on", re.I)
SKIP = re.compile(r"skip( the| this)?( tour| one)?", re.I)
BEGIN = re.compile(r"(ok(ay)?,? )?(let'?s go|begin|let'?s begin|start|let'?s start|yes|sure)", re.I)
RESUME = re.compile(r"(let'?s )?(start|continue|keep going with)( the)? tours?|know (my|your) system", re.I)


# ------------------------------------------------------------------ progress


def _progress(context) -> dict:
    """This person's welcome progress (person_settings), or a fresh one."""
    saved = person_settings.get(context, KEY) or {}
    return saved if isinstance(saved, dict) else {}


def _save(context, progress: dict) -> None:
    """Saves this person's welcome progress."""
    person_settings.put(context, KEY, progress)


def _mission(context, progress: dict):
    """The "Know your system" mission once it's been added, or None."""
    missions = getattr(context, "missions", None)
    found = progress.get("mission_id")
    return missions.get_mission(found) if missions is not None and found else None


def _act(context, kind: str, **params):
    """Proposes an action as MIA and approves it at once (the person chose "let's go"), so the mission is made through
    the action contract like any other.
    """
    actions = context.actions
    return actions.approve(context, actions.propose(context, kind, params, proposed_by="mia").proposal_id)


def _tick(context, progress: dict, index: int) -> None:
    """An objective happened. Once is enough, and a mission they removed stays removed."""
    mission = _mission(context, progress)
    if mission is None or mission.status != "active" or context.missions.is_objective_complete(mission.mission_id, index):
        return
    try:
        _act(context, "objective.tick", mission_id=mission.mission_id, index=index)
        if all(context.missions.is_objective_complete(mission.mission_id, i) for i in range(len(OBJECTIVES))):
            _act(context, "mission.complete", mission_id=mission.mission_id)
            progress["complete"] = True
            progress.pop("paused", None)
    except Exception:
        log.exception("Couldn't tick %s.", OBJECTIVES[index])


def _record(context, what: str) -> None:
    """Records a finished tour in the person's life-event history."""
    life_events.record(getattr(context, "personal_life_events", None) or getattr(context, "life_events", None),
                       "tour_done", what, payload={}, profile_id=person_settings.person_id(context))


# ------------------------------------------------------------------ what's shown


def _tour_apps(context) -> list:
    """The apps on this person's glasses that have a tour, with their short names."""
    from core.glasses import SHORT_NAMES, _visible_apps

    return [(a.module_id, SHORT_NAMES.get(a.module_id, a.name)) for a in _visible_apps(context) if a.module_id in APP_TOURS]


def _app_rows(context, progress: dict) -> list[dict]:
    """The app menu's rows: each app with a tour, its status (ready, paused at a step, or done) and its intro."""
    tours = progress.get("tours") or {}
    rows = []
    for module_id, name in _tour_apps(context):
        own = tours.get(module_id) or {}
        status = "Tour done" if own.get("done") else f"Paused · step {own['step'] + 1}" if own.get("step") else "Tour ready"
        rows.append({"id": module_id, "name": name, "status": status, "intro": app_intro(context, module_id)})
    return rows


def _mission_card(context, progress: dict) -> dict:
    """The first mission's card: its objectives and which are done, and the percent done (meeting MIA counts as done
    before the mission is even added).
    """
    mission = _mission(context, progress)
    done = [False] * len(OBJECTIVES)
    if mission is not None:
        done = [context.missions.is_objective_complete(mission.mission_id, i) for i in range(len(OBJECTIVES))]
    else:
        done[MEET] = True  # she's met MIA by now, whether or not the mission's been added
    return {"name": MISSION, "summary": SUMMARY, "xp": MISSION_XP, "percent": round(100 * sum(done) / len(done)),
            "objectives": [{"text": t, "done": d} for t, d in zip(OBJECTIVES, done)]}


def _home_tiles(context) -> list[str]:
    """The first four Home tiles' names, for the Home tour to light up."""
    from core.glasses import glasses_apps

    return [a["name"] for a in glasses_apps(context)["apps"][:4]]


def _tour(context, progress: dict) -> Optional[dict]:
    """The tour step being shown, or None: on Home, the step and which tile is lit; in an app's tour, the step and
    which of its menu items is lit (the tour names real items from core/glasses.py PANELS).
    """
    if progress.get("stage") == "home":
        at = progress.get("home_step", 0)
        lit, text = HOME_TOUR[at]
        return {"app": "home", "name": "Home", "number": at + 1, "of": len(HOME_TOUR), "text": text,
                "tiles": [{"label": n, "on": i == lit} for i, n in enumerate(_home_tiles(context))]}
    from core.glasses import PANELS

    app = progress.get("touring")
    if progress.get("stage") != "tour" or app not in APP_TOURS:
        return None
    at = (progress.get("tours") or {}).get(app, {}).get("step", 0)
    item, text = APP_TOURS[app][at]
    labels = PANELS[app]
    return {"app": app, "name": dict(_tour_apps(context)).get(app, app), "number": at + 1, "of": len(APP_TOURS[app]), "text": text,
            "tiles": [{"label": label, "on": key == item} for key, label, _build in labels]}


def state(context) -> dict:
    """What the glasses show now: nothing until the introduction and User Sync are done; then the stage (mission,
    home, tour, apps, explore, done), whether it's paused, the mission card, the tour step, the app rows, and ideas
    once it's complete.
    """
    progress = _progress(context)
    out = {"stage": "none", "paused": False, "left": False, "ready": False, "mission": None, "tour": None, "apps": [], "ideas": []}
    if progress.get("finished_at"):
        return {**out, "stage": "done"}
    if not first_boot.state(context)["done"] or not user_sync.state(context)["done"]:
        return out  # her introduction and User Sync come first
    stage = progress.get("stage") or "mission"
    if progress.get("complete") and stage in ("apps", "mission"):
        stage = "explore"
    out.update(stage=stage, paused=bool(progress.get("paused")), left=True, ready=not progress.get("stage"),
               mission=_mission_card(context, progress), tour=_tour(context, progress))
    if stage == "apps":
        out["apps"] = _app_rows(context, progress)
    if stage == "explore":
        out["ideas"] = list(IDEAS)
    return out


def _result(context, say: str = "") -> dict:
    """The state plus what MIA says, as the endpoint returns it."""
    return {**state(context), "say": say}


# ------------------------------------------------------------------ the steps


def _begin(context, progress: dict) -> dict:
    """"Let's go": adds the first mission and its objectives (once), ticks meeting MIA, and starts the Home tour."""
    if getattr(context, "actions", None) is None or getattr(context, "missions", None) is None:
        return _result(context, "I can't set that up here.")
    name = next((m for m in context.missions.all_missions() if m.name == MISSION), None)
    if name is None:
        _act(context, "mission.add", name=MISSION, summary=SUMMARY, reward_xp=MISSION_XP)
        name = next(m for m in context.missions.all_missions() if m.name == MISSION)
        for what in OBJECTIVES:
            _act(context, "objective.add", mission_id=name.mission_id, description=what, target=1)
    progress.update(mission_id=name.mission_id, stage="home", home_step=0)
    _tick(context, progress, MEET)
    _save(context, progress)
    return _result(context, HOME_TOUR[0][1])


def _to_apps(context, progress: dict, ticked: bool) -> dict:
    """Moves to the app menu, ticking the Home objective and recording it when the tour was finished, not skipped."""
    progress["stage"] = "apps"
    if ticked:
        _tick(context, progress, HOME)
        _record(context, "Finished the tour of Home")
    _save(context, progress)
    return _result(context, "Here are your apps. Every tour is optional.")


def _next(context, progress: dict) -> dict:
    """The next tour step; at the end of Home it moves to the apps, at the end of an app's tour it marks the tour done,
    ticks exploring and records it.
    """
    if progress.get("stage") == "home":
        at = progress.get("home_step", 0) + 1
        if at >= len(HOME_TOUR):
            return _to_apps(context, progress, True)
        progress["home_step"] = at
        _save(context, progress)
        return _result(context, HOME_TOUR[at][1])
    app = progress.get("touring")
    own = progress.setdefault("tours", {}).setdefault(app, {})
    own["step"] = own.get("step", 0) + 1
    if own["step"] < len(APP_TOURS[app]):
        _save(context, progress)
        return _result(context, APP_TOURS[app][own["step"]][1])
    own.update(step=0, done=True)
    progress["stage"] = "apps"
    progress.pop("touring", None)
    _tick(context, progress, EXPLORE)
    _record(context, f"Finished the {app} tour")
    _save(context, progress)
    return _result(context, "That's the tour.")


def _skip(context, progress: dict) -> dict:
    """Skips out of a tour to the app menu; an app tour keeps its step, so it picks up there."""
    if progress.get("stage") == "home":
        return _to_apps(context, progress, False)
    progress["stage"] = "apps"  # its step stays: a paused tour picks up there
    progress.pop("touring", None)
    _save(context, progress)
    return _result(context)


def _start_tour(context, progress: dict, app: str) -> dict:
    """Starts (or resumes) an app's tour at its step."""
    if app not in dict(_tour_apps(context)):
        return _result(context)
    own = progress.setdefault("tours", {}).setdefault(app, {})
    progress.update(stage="tour", touring=app)
    _save(context, progress)
    return _result(context, APP_TOURS[app][own.get("step", 0)][1])


def _open(context, progress: dict, app: str) -> dict:
    """"Just open it" counts: they went and looked."""
    _tick(context, progress, EXPLORE)
    _save(context, progress)
    return {**_result(context), "open": app}


def choose(context, choice: str, app: str = "") -> dict:
    """What the person chose (begin, next, skip, tour, open, later, resume, finish), acted on only when it fits the
    stage; returns the new state and what MIA says.
    """
    progress = _progress(context)
    now = state(context)
    if now["stage"] in ("none", "done"):
        return _result(context)
    if choice == "later":
        progress["paused"] = True
        _save(context, progress)
        return _result(context, "Of course. It'll be here whenever you like.")
    if choice == "resume":
        progress.pop("paused", None)
        _save(context, progress)
        return _result(context)
    if now["stage"] == "mission" and choice == "begin":
        return _begin(context, progress)
    if now["stage"] in ("home", "tour") and choice == "next":
        return _next(context, progress)
    if now["stage"] in ("home", "tour") and choice == "skip":
        return _skip(context, progress)
    if now["stage"] == "apps" and choice == "tour":
        return _start_tour(context, progress, app)
    if now["stage"] == "apps" and choice == "open":
        return _open(context, progress, app)
    if now["stage"] == "explore" and choice == "finish":
        progress["finished_at"] = datetime.now().isoformat(timespec="seconds")
        _save(context, progress)
    return _result(context)


def hear(context, text: str) -> Optional[dict]:
    """Words from the glasses, if they're for what's on screen."""
    words = " ".join(str(text or "").split()).strip(" .!?")
    now = state(context)
    if not now["left"]:
        return None
    if now["paused"]:
        return choose(context, "resume") if RESUME.fullmatch(words) else None
    if LATER.fullmatch(words):
        return choose(context, "later")
    if now["stage"] == "mission" and BEGIN.fullmatch(words):
        return choose(context, "begin")
    if now["stage"] in ("home", "tour"):
        if SKIP.fullmatch(words):
            return choose(context, "skip")
        if NEXT.fullmatch(words):
            return choose(context, "next")
    return None


def talked(context) -> None:
    """A turn on the glasses that wasn't an answer to anything of hers."""
    progress = _progress(context)
    if progress.get("mission_id") and not progress.get("complete"):
        _tick(context, progress, TALK)
        _save(context, progress)
