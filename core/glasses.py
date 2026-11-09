"""
core.glasses
==============

The glasses' app cards and their quick action menus (Zac, 2026-10-16;
Muse's H-0041 Phase 2). The glasses boot to MIA's orb; one swipe away,
the person flips through app cards; selecting one opens its quick action
menu. Assembled here, in code, so `web/glasses.js` holds no logic
(DEC-0013), from the same page assemblers every other screen uses.

- `glasses_apps(context)`: the person's apps as glasses cards (child-safe,
  respecting apps they've tucked away), each with a one-line status and
  its menu. **Pinned for the glasses = the person's favorite apps** (Zac,
  2026-10-16), in the order they starred them: those are the cards; the
  rest wait behind an "All apps" card. With no favorites, every app shows
  in the glasses' order. Served as `/api/glasses`, with Home's one line
  (`priority`) and its tone (`priority_tone`: amber orb when it needs you,
  the canvas's GlassesHome, DEC-0113), and `areas` for the Nexus's ring
  (`glasses_areas`: each area with its apps here, hue and what needs you;
  `short_name` fits its name on the ring; DEC-0130).
- Every app has a card but Passwords (no secrets on the display) and Look (the
  glasses' own camera, still to come): the apps that only had an ask got
  theirs in core/glasses_cards.py (2026-11-08), merged into PANELS below.
- `glasses_panel(context, app_id, item_id)`: what one menu item shows: a
  title and a few lines, each line optionally carrying the action it
  proposes. Served as `/api/glasses/{app_id}/{item_id}`.
  The live workout's panel also carries a `hero` (`training_hero`: the
  exercise, set and weight, one big number and what it is; the canvas's
  GlassesTraining); cook mode's panel ("Cooking Now") carries one from
  `cooking_hero`: the step large and each timer's time left.

A menu item is either a `panel` (a short readout, some lines of which
can be acted on) or an `ask` (a question handed to MIA, as if said
aloud). Every action still goes Propose → Approve → Execute → Record →
Undo through `/api/actions`; the glasses show the proposal's sentence
and a second gesture approves it (H-0008, H-0012).

**What the glasses may change** is `GLASSES_KINDS`: quick, everyday,
non-destructive things (ate it, a step done, a mission claimed, a chore
or upkeep done, a grocery item checked, a promise kept, a job's step
along or its hold checked). Nothing that deletes, nothing
that needs a typed number, and no money (H-0041: money stays readouts on
the glasses in v1). A line whose action isn't in the list is shown as a
readout only.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

# The action kinds a glasses line may carry. Never a delete, a money
# movement, or anything that needs a number typed in.
GLASSES_KINDS = frozenset({
    "fitness.food", "fitness.step", "fitness.training_done", "fitness.skill", "fitness.milestone",
    "mission.complete", "objective.tick", "maintenance.done", "grocery.check",
    "task.done", "meal.prep_done", "meal.cook", "routine.log", "app.favorite",
    # the live workout (DEC-0055): moving it along, never a number to type (counts come by voice)
    "training.start", "training.set", "training.skip_rest", "training.rest_more", "training.pause", "training.resume",
    "training.skip",
    "training.finish",
    # cook mode (DEC-0113): the step, a named timer the step offers, "I made this"; stopping without logging is by voice
    "cooking.next", "cooking.back", "cooking.timer", "cooking.timer_cancel", "cooking.made",
    # a trip underway (core/trip_route.py): "Arrived" at the next stop, logged now
    "trip.arrived",
    # the course to continue in the Classroom: a lesson ticked done (its skill XP credited once)
    "lesson.done",
    # Kept's open promises (core/glasses_cards.py, 2026-11-08): "Done", undoable
    "life_note.done",
    # Trade Master's walkthrough (DEC-0149, core/glasses_cards._trade_job): a job started, the step along, a hold
    # checked, a diagnosis's yes or no, and Stop; the holds are enforced in core/trade_session.py, never on the card
    "trade.start", "trade.next", "trade.check", "trade.back", "trade.answer", "trade.stop",
})

# Apps the glasses don't show as cards: the orb *is* Home and Talk; the
# Apps manager and Settings are for a bigger screen. Files has a card since
# 2026-11-07 (DEC-0125): asking what's there; the files open on the phone.
NOT_ON_GLASSES = frozenset({"web_home", "assistant", "module_browser", "settings", "dashboard",
                            "maintenance", "property"})

# The glasses' order: Today, then the apps used most on the move, then
# the rest of MIA in its usual order.
FIRST = ("missions", "calendar", "kitchen", "workout", "budget", "garage", "real_estate", "greenhouse",
         "skills", "character")

# Short names for a 600 px card, where the app's own name is long.
SHORT_NAMES = {"dashboard": "Today", "relationships": "People", "real_estate": "Rentals"}

MAX_LINES = 5


def _line(text: str, detail: str = "", tone: str = "", action: Optional[dict] = None) -> dict:
    """One panel line: text, a detail, a tone, and the action it proposes, kept only when its kind is in GLASSES_KINDS
    (anything else stays a readout).
    """
    out = {"text": text, "detail": detail, "tone": tone}
    if action and action.get("kind") in GLASSES_KINDS:
        out["action"] = {"kind": action["kind"], "label": action.get("label") or "Do it",
                         "params": dict(action.get("params") or {})}
    return out


def _panel(title: str, lines: list[dict], empty: str, more: int = 0, limit: int = MAX_LINES) -> dict:
    """A panel: its title, the first `limit` lines, how many more there are, and what to show when it's empty."""
    return {"title": title, "lines": lines[:limit], "more": max(0, more + len(lines) - limit),
            "empty": empty}


# ---------------------------------------------------------------- panels


def _asks_meter(context, params: dict) -> bool:
    """A meter task's completion asks for the reading, which the glasses can't type."""
    try:
        task = context.maintenance.get_task(params.get("task_id"))
        return bool(task) and task.trigger_type != "calendar" and params.get("meter_value") is None
    except Exception:
        return False


def _fitness(context, today):
    """The Fitness page's data (core/web_fitness.py), which several panels read from."""
    from core.web_fitness import fitness_page

    return fitness_page(context, today)


def _kitchen_meals(context, today):
    """Panel: today's planned meals with kcal and protein, each uneaten one offering "Ate it" (fitness.food), and
    protein against the target (a menu item's readout; lines with an allowed action can be approved from the glasses).
    """
    page = _fitness(context, today)
    meals = ((page.get("today") or {}).get("meals") or {})
    iso = meals.get("date") or today.isoformat()
    lines = []
    for m in meals.get("meals") or []:
        kcal = m.get("kcal")
        detail = m["meal"].capitalize() + (f" · {round(kcal)} kcal" if kcal else "") + \
            (f" · {round(m['protein_g'])} g protein" if m.get("protein_g") else "")
        action = None if m.get("eaten") else {
            "kind": "fitness.food", "label": "Ate it",
            "params": {"meal": m["meal"], "recipe_id": m.get("recipe_id"), "servings": m.get("servings"),
                       "date": iso, "planned_id": f"{iso}:{m['meal']}"}}
        lines.append(_line(m.get("name") or "", detail + (" · eaten" if m.get("eaten") else ""),
                           "ok" if m.get("eaten") else "", action))
    food = (page.get("today") or {}).get("food") or {}
    totals, targets = food.get("totals") or {}, food.get("targets") or {}
    if targets.get("protein_g"):
        lines.append(_line(f"Protein {round(totals.get('protein_g') or 0)} of {targets['protein_g']} g"))
    return _panel("Today's Meal Plan", lines, "No meals planned today. Plan them in Kitchen → Week.")


def _kitchen_grocery(context, today):
    """Panel: the unchecked grocery items with amount and recipe, each offering "Got it" (grocery.check) (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.web_screens import kitchen_page

    items = [g for g in kitchen_page(context, today).get("grocery") or [] if not g.get("checked")]
    lines = []
    for g in items:
        qty = g.get("quantity")
        amount = f"{qty:g} {g.get('unit') or ''}".strip() if qty else ""
        lines.append(_line(g.get("name") or "", " · ".join(x for x in (amount, g.get("for_recipe") or "") if x), "",
                           {"kind": "grocery.check", "label": "Got it",
                            "params": {"item_id": g["id"], "checked": True}}))
    return _panel("Grocery List", lines, "The grocery list is empty.", limit=60)


RECIPE_ITEM = "recipes-"
MUSIC_LIST = "list-"


def _slug(text: str) -> str:
    """A short id from text (lowercase, dashes, at most 20 characters), for menu items made from names."""
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:20]


def _open_recipes(context, today):
    """The recipes the person can open (not locked), from the Kitchen page."""
    from core.web_screens import kitchen_page

    return [r for r in kitchen_page(context, today).get("recipes") or [] if not r.get("locked")]


def _kitchen_recipes(context, today):
    """The recipe book's way in: favorites, each category, then all of them.
    Picking one opens those recipes to swipe through."""
    recipes = _open_recipes(context, today)
    lines = []

    def shelf(label: str, item: str, count: int) -> None:
        if count:
            line = _line(label, f"{count} recipe{'' if count == 1 else 's'}")
            line["open"] = {"item": f"{RECIPE_ITEM}{item}", "label": "Open"}
            lines.append(line)

    shelf("Favorites", "favorites", sum(1 for r in recipes if r.get("favorite")))
    for name in sorted({r.get("category") or "" for r in recipes} - {""}):
        shelf(name, _slug(name), sum(1 for r in recipes if r.get("category") == name))
    shelf("All Recipes", "all", len(recipes))
    return _panel("Recipes", lines, "No recipes yet. Add them on your phone.", limit=60)


def _recipe_shelf(context, today, which: str) -> Optional[dict]:
    """The recipes on one shelf: each with its picture, ingredients and steps."""
    from core.web_screens import recipe_steps

    recipes = _open_recipes(context, today)
    if which == "favorites":
        recipes = [r for r in recipes if r.get("favorite")]
    elif which != "all":
        recipes = [r for r in recipes if _slug(r.get("category") or "") == which]
    if not recipes:
        return None
    recipes.sort(key=lambda r: (not r.get("favorite"), -(r.get("times_made") or 0), (r.get("name") or "").lower()))
    lines = []
    for r in recipes:
        bits = [r.get("category") or "", f"{r['minutes']} min" if r.get("minutes") else "",
                f"{r['servings']:g} servings" if r.get("servings") else ""]
        line = _line(r.get("name") or "", " · ".join(b for b in bits if b))
        line["recipe"] = {
            "id": r["id"], "name": r.get("name") or "", "photo": r.get("photo") or "",
            "ingredients": [i for i in (r.get("ingredients_text") or "").splitlines() if i.strip()],
            "steps": recipe_steps(r.get("instructions") or ""), "rating": r.get("rating"),
            "action": {"kind": "meal.cook", "label": "I Made This", "params": {"recipe_id": r["id"]}},
        }
        lines.append(line)
    title = {"favorites": "Favorites", "all": "All Recipes"}.get(which) or recipes[0].get("category") or "Recipes"
    return _panel(title, lines, "No recipes here.", limit=60)


def _music(context):
    """The Music page's data (core/web_more.py)."""
    from core.web_more import music_page

    return music_page(context)


def _song_lines(tracks: list[dict]) -> list[dict]:
    """Each song says what plays from it: the list it's in, from here on."""
    ids = [t["id"] for t in tracks[:200]]
    lines = []
    for i, t in enumerate(tracks[:60]):
        line = _line(t["title"], " · ".join(b for b in (t.get("artist"), t.get("duration")) if b))
        line["play"] = {"label": "Play", "ids": ids, "at": i}
        lines.append(line)
    return lines


def _music_songs(context, today):
    """Panel: every song (the first 60), each playable (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    tracks = _music(context).get("tracks") or []
    return _panel("Songs", _song_lines(tracks), "No songs yet. Add them on your phone.", more=max(0, len(tracks) - 60), limit=60)


def _music_shelf(lines_of: list[tuple[str, str, int]]) -> list[dict]:
    """Lines for a shelf of song lists (playlists or artists): each names its count and opens that list."""
    lines = []
    for label, item, count in lines_of:
        line = _line(label, f"{count} song{'' if count == 1 else 's'}")
        line["open"] = {"item": f"{MUSIC_LIST}{item}", "label": "Open"}
        lines.append(line)
    return lines


def _music_playlists(context, today):
    """Panel: the playlists, each opening its songs (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    lists = _music(context).get("playlists") or []
    return _panel("Playlists", _music_shelf([(p["name"], f"p-{p['id']}"[:27], len(p["track_ids"])) for p in lists]),
                  "No playlists yet.", limit=60)


def _music_artists(context, today):
    """Panel: the artists, each opening their songs (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    artists = _music(context).get("artists") or []
    return _panel("Artists", _music_shelf([(a["name"], f"a-{i}", a["count"]) for i, a in enumerate(artists)]), "No artists yet.", limit=60)


def _music_list(context, which: str) -> Optional[dict]:
    """One playlist or artist's songs."""
    page = _music(context)
    tracks = page.get("tracks") or []
    if which.startswith("p-"):
        found = next((p for p in page.get("playlists") or [] if f"p-{p['id']}"[:27] == which), None)
        if found is None:
            return None
        by_id = {t["id"]: t for t in tracks}
        return _panel(found["name"], _song_lines([by_id[i] for i in found["track_ids"]]), "This playlist is empty.", limit=60)
    artists = page.get("artists") or []
    index = which[2:]
    if not index.isdigit() or int(index) >= len(artists):
        return None
    name = artists[int(index)]["name"]
    return _panel(name, _song_lines([t for t in tracks if (t.get("artist") or "Unknown artist") == name]), "No songs.", limit=60)


def _clock(seconds: int) -> str:
    """Pure logic. Seconds as m:ss ("17:42"), or h:mm:ss over an hour."""
    seconds = max(0, int(seconds))
    h, m, s = seconds // 3600, seconds % 3600 // 60, seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def cooking_hero(v: dict) -> dict:
    """Pure logic. Cook mode on the glasses (the canvas's cook mode, DEC-0113), from core/cooking_session.view: the
    recipe, which step of how many, the step itself, and each timer with its time left ("Done" once it has gone off)."""
    return {"kind": "cook", "name": v.get("title") or "", "set": f"Step {v.get('number')} of {v.get('steps_total')}",
            "step": v.get("step") or "",
            "timers": [{"name": t["name"], "left": "Done" if t["done"] else _clock(t["left"]), "done": t["done"]}
                       for t in v.get("timers") or []]}


def _kitchen_cooking(context, today):
    """Panel: the recipe being cooked (cook mode, core/cooking_session.py): its `hero` (cooking_hero), then Next Step
    (or I Made This on the last), Back, the timer the step offers and Stop for each running timer, all one press."""
    from datetime import datetime

    from core import cooking_session as cs

    store = getattr(context, "cooking", None)
    s = store.live() if store is not None else None
    if s is None:
        return _panel("Cooking Now", [], "Nothing's cooking. Open a recipe and Start Cooking, or say \"start cooking\".")
    v = cs.view(s, datetime.now())
    lines = []
    if v["last"]:
        lines.append(_line("I made this", "logs it and uses the pantry", "",
                           {"kind": "cooking.made", "label": "I Made This", "params": {"pantry": "yes"}}))
    else:
        lines.append(_line("Next step", v["next"] or "", "", {"kind": "cooking.next", "label": "Next Step", "params": {}}))
    offer = v.get("offer_timer")
    if offer and not any(t["name"].lower() == offer["name"].lower() for t in v["timers"]):
        minutes = max(1, round(offer["seconds"] / 60))
        lines.append(_line(f"{offer['name']} timer", f"{minutes} min", "",
                           {"kind": "cooking.timer", "label": "Start", "params": {"name": offer["name"], "minutes": minutes}}))
    for t in v["timers"]:
        lines.append(_line(f"Stop {t['name'].lower()} timer", "done" if t["done"] else _clock(t["left"]) + " left",
                           "attention" if t["done"] else "",
                           {"kind": "cooking.timer_cancel", "label": "Stop", "params": {"name": t["name"]}}))
    if v["number"] > 1:
        lines.append(_line("Back a step", v["previous"] or "", "", {"kind": "cooking.back", "label": "Back", "params": {}}))
    return {**_quick(_panel(f"Cooking: {v['title']}", lines, "")), "hero": cooking_hero(v)}


def _kitchen_pantry(context, today):
    """Panel: the pantry, soonest to expire first, flagging what expires within two days (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.web_screens import kitchen_page

    items = kitchen_page(context, today).get("pantry") or []
    items = sorted(items, key=lambda p: (p.get("expires_in") is None, p.get("expires_in") or 0, (p.get("name") or "").lower()))
    lines = []
    for p in items:
        qty = p.get("quantity")
        amount = f"{qty:g} {p.get('unit') or ''}".strip() if qty else ""
        days = p.get("expires_in")
        when = "" if days is None else "expired" if days < 0 else "expires today" if days == 0 else f"expires in {days}d"
        lines.append(_line(p.get("name") or "", " · ".join(b for b in (amount, when) if b),
                           "attention" if days is not None and days <= 2 else ""))
    return _panel("My Pantry", lines, "The pantry is empty.", limit=60)


QUICK = ("training.set", "training.skip_rest", "training.skip", "training.pause", "training.resume",
         "cooking.next", "cooking.back", "cooking.timer", "cooking.timer_cancel")


def _quick(panel: dict) -> dict:
    """A live workout moves on one press: each of these is small and undoable,
    and a second gesture per set would get in the way. The screen keeps itself
    current (`live`)."""
    for line in panel["lines"]:
        if (line.get("action") or {}).get("kind") in QUICK:
            line["action"]["quick"] = True
    return {**panel, "live": True}


def _workout_live(context, today):
    """The workout going right now (DEC-0055): where you are and the next move."""
    return _quick(_workout_live_lines(context, today))


HOW_COUNTED = {"said": "Said", "cadence": "MIA pace", "told": "Told", "tapped": "Tapped"}


def training_hero(s: dict) -> Optional[dict]:
    """Pure logic. The canvas's Active Training on the glasses (DEC-0113 GlassesTraining): the exercise, the set and
    weight, one big number and what it is, and what's next, from a live session's view (core/training_session.view).
    Resting: the rest left, then the set it leads to. Otherwise the last set's count against the goal, or the goal
    before the first set. MIA doesn't count reps live on the glasses, so the big number is never a guess. None when
    the session is done."""
    if s.get("status") == "complete":
        return None
    n = s.get("now") or {}
    goal = n.get("hold_seconds") or n.get("reps") or 0
    sets = f"Set {n.get('set')} / {n.get('sets')}" + (f" · {n['weight']}" if n.get("weight") else "")
    then = f"Then: {s['next']}" if s.get("next") else ""
    if s.get("status") == "resting":
        left = int(s.get("rest_left") or 0)
        return {"name": n.get("name") or "", "set": sets, "big": f"{left // 60}:{left % 60:02d}", "of": "",
                "how": "Rest", "next": f"Then: {n.get('name') or 'the next set'}", "resting": True}
    if n.get("last") is not None:
        return {"name": n.get("name") or "", "set": sets, "big": str(n["last"]), "of": f"/ {goal}" if goal else "",
                "how": "Last set · " + HOW_COUNTED.get(n.get("last_counted") or "told", "Told"), "next": then,
                "resting": False}
    return {"name": n.get("name") or "", "set": sets, "big": str(goal) if goal else "—", "of": "",
            "how": "Target · " + (n.get("target") or ""), "next": then, "resting": False}


def _workout_live_lines(context, today):
    """Panel: the live training session: the exercise and set now (and its `hero`, training_hero), the rest countdown
    (skip rest, +30 s), set done, pause or resume, skip, what's next and finish; with no session, a line to start today's workout (or a rest day) (a menu item's readout; lines with an allowed action can be approved from the glasses).
    """
    from core.web_fitness import live_session

    s = live_session(context)
    if s is None:
        t = (_fitness(context, today).get("today") or {})
        if not t.get("training"):
            return _panel("Active Training", [], "Rest day. Recovery counts too.")
        return _panel("Active Training", [_line("Start today's workout", t["training"].get("name") or "", "",
                                                 {"kind": "training.start", "label": "Start", "params": {}})], "")
    n, lines = s.get("now") or {}, []
    if s["status"] == "complete":
        lines.append(_line("All done", s["title"], "ok", {"kind": "training.finish", "label": "Finish", "params": {}}))
    else:
        lines.append(_line(n.get("name") or "", f"Set {n.get('set')}/{n.get('sets')} · {n.get('target')}"
                           + (f" · last {n['last']}" if n.get("last") is not None else ""), "attention"))
        if s["status"] == "resting":
            lines.append(_line(f"Rest {s['rest_left']} s", "then " + (n.get("name") or ""), "",
                               {"kind": "training.skip_rest", "label": "Skip rest", "params": {}}))
            lines.append(_line("+30 s", "thirty more seconds", "",
                               {"kind": "training.rest_more", "label": "+30 s", "params": {}}))
        else:
            lines.append(_line("Set done", "say the count, or tap", "",
                               {"kind": "training.set", "label": "Next set", "params": {"counted": "tapped"}}))
        lines.append(_line("Paused" if s["status"] == "paused" else "Pause", "", "",
                           {"kind": "training.resume" if s["status"] == "paused" else "training.pause",
                            "label": "Resume" if s["status"] == "paused" else "Pause", "params": {}}))
        if s["status"] != "paused":
            lines.append(_line("Skip this exercise", n.get("name") or "", "",
                               {"kind": "training.skip", "label": "Skip", "params": {}}))
        if s.get("next"):
            lines.append(_line("Next", s["next"], ""))
        lines.append(_line("Finish", f"{s['done_exercises']}/{s['exercises']} exercises", "",
                           {"kind": "training.finish", "label": "Finish", "params": {}}))
    return {**_panel(f"Training: {s['title']}", lines, ""), "hero": training_hero(s)}


def _workout_training(context, today):
    """Panel: today's training steps (sets and reps or holds), each undone one offering Done (fitness.step), then
    "Training done" (a menu item's readout; lines with an allowed action can be approved from the glasses).
    """
    t = (_fitness(context, today).get("today") or {})
    training = t.get("training")
    if t.get("rest_day") or not training:
        return _panel("Today's training", [], "Rest day. Recovery counts too.")
    lines = []
    for s in training.get("steps") or []:
        amount = f"{s['sets']}×{s['reps']}" if s.get("reps") else f"{s['sets']}×{s['hold_seconds']} s" \
            if s.get("hold_seconds") and s.get("sets") else f"{s['hold_seconds']} s" if s.get("hold_seconds") else ""
        lines.append(_line(s.get("name") or "", amount + (" · done" if s.get("done") else ""),
                           "ok" if s.get("done") else "",
                           None if s.get("done") else {"kind": "fitness.step", "label": "Done",
                                                       "params": {"step": s["index"] + 1}}))
    if not training.get("done"):
        lines.append(_line("Finish today's training", training.get("name") or "", "",
                           {"kind": "fitness.training_done", "label": "Training done", "params": {}}))
    return _panel(f"Training: {training.get('name') or 'today'}", lines, "Nothing planned today.")


def _workout_practice(context, today):
    """Panel: today's skill practice, best against target per step, offering "Practiced N min" until the day's
    minutes are in (a menu item's readout; lines with an allowed action can be approved from the glasses).
    """
    skills = (_fitness(context, today).get("today") or {}).get("skills") or []
    lines = []
    for s in skills:
        minutes = s.get("daily_minutes") or 0
        done = (s.get("minutes_today") or 0) >= minutes > 0
        best = []
        for step in s.get("steps") or []:
            if step.get("target_seconds"):
                best.append(f"{step['name']} {round(step.get('best_seconds') or 0)}/{step['target_seconds']} s")
            elif step.get("target_reps"):
                best.append(f"{step['name']} {step.get('best_reps') or 0}/{step['target_reps']} reps")
        action = None if done or not minutes else {
            "kind": "fitness.skill", "label": f"Practiced {minutes} min",
            "params": {"skill": s["skill"], "minutes": minutes}}
        lines.append(_line(s.get("skill") or "", " · ".join(best[:2]) or f"{minutes} min a day",
                           "ok" if done else "", action))
    return _panel("Skill practice", lines, "No skills in your plan yet. Add them in My plan.")


def _workout_weight(context, today):
    """Panel: the latest weigh-in, the weekly trend and the goal (and when it's on track for) (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    w = _fitness(context, today).get("weight") or {}
    if not w.get("latest"):
        return _panel("Weight", [], "No weigh-ins yet.")
    units = w.get("units") or ""
    lines = [_line(f"{w['latest']:g} {units}", f"on {w.get('latest_on')}")]
    if w.get("weekly_change") is not None:
        lines.append(_line(f"{w['weekly_change']:+.1f} {units} a week", "7-day trend"))
    if w.get("target"):
        lines.append(_line(f"Goal {w['target']:g} {units}",
                           f"on track for {w['on_track_for']}" if w.get("on_track_for") else ""))
    return _panel("Weight", lines, "No weigh-ins yet.")


def _workout_milestones(context, today):
    """Panel: the plan's milestones, each unreached one offering "Reached it" (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    ms = _fitness(context, today).get("milestones") or []
    lines = [_line(m.get("name") or "", f"reached {m['done_on']}" if m.get("done_on") else "",
                   "ok" if m.get("done_on") else "",
                   None if m.get("done_on") else {"kind": "fitness.milestone", "label": "Reached it",
                                                  "params": {"milestone_id": m["id"]}})
             for m in ms]
    return _panel("Milestones", lines, "No milestones in your plan yet.")


# Past Due / Due Today / Due Soon (Zac, 2026-10-16): the one way the
# glasses sort everything with a date, in Missions, equipment and the calendar.
BUCKETS = (("past_due", "Past Due"), ("due_today", "Due Today"), ("due_soon", "Due Soon"))


def bucket_of(days: Optional[int], urgency: str = "") -> Optional[str]:
    """Which due bucket a task falls in (past_due, due_today, due_soon); the same rule as Equipment's page."""
    from core.web_equipment import bucket_of as shared

    return shared(days, urgency)


def _bucketed(lines: list[dict], bucket: Optional[str]) -> list[dict]:
    """The lines in one bucket (all of them when bucket is None)."""
    return [line for line in lines if bucket is None or line.get("bucket") == bucket]


def _missions(context, today):
    """The Missions page's data (core/web_progress.py)."""
    from core.web_progress import missions_page

    return missions_page(context, today)


def _mission_line(m: dict) -> dict:
    """One mission as a line: "Claim" when it's ready; "Done" when one single-step objective is left (one that doesn't
    count itself); otherwise its progress only.
    """
    progress = f"{m.get('done', 0)} of {m.get('total', 0)}"
    if m.get("ready"):
        return _line(m.get("name") or "", f"ready · {m.get('reward_xp') or 0} XP", "ok",
                     {"kind": "mission.complete", "label": "Claim", "params": {"mission_id": m["id"]}})
    objectives = [o for o in m.get("objectives") or [] if not o.get("done")]
    action = None
    if len(objectives) == 1 and (objectives[0].get("target") or 1) == 1 and not objectives[0].get("counts_itself"):
        action = {"kind": "objective.tick", "label": "Done",
                  "params": {"mission_id": m["id"], "index": objectives[0].get("index", 0), "amount": 1}}
    return _line(m.get("name") or "", progress, "", action)


def _missions_claim(context, today):
    """Panel: the missions ready to claim, daily and active (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    page = _missions(context, today)
    ready = [m for m in (page.get("daily") or []) + (page.get("active") or []) if m.get("ready")]
    return _panel("Ready to claim", [_mission_line(m) for m in ready], "Nothing to claim yet. Keep going.")


def _active_missions(page: dict) -> list[dict]:
    """Every active mission: the long-running ones first, then today's."""
    return [m for m in (page.get("active") or []) + (page.get("daily") or []) if m.get("status") == "active"]


def mission_focus(context, today: date, mission_id: Optional[str] = None) -> Optional[dict]:
    """The mission the Missions card shows (Zac, 2026-10-16): the one the
    person selected on the glasses, else their first active mission."""
    missions = _active_missions(_missions(context, today))
    if not missions:
        return None
    m = next((x for x in missions if x.get("id") == mission_id), None) or missions[0]
    return {"id": m["id"], "name": m.get("name") or "", "icon": m.get("icon") or "", "ready": bool(m.get("ready")),
            "done": m.get("done", 0), "total": m.get("total", 0), "reward_xp": m.get("reward_xp") or 0,
            "objectives": [{"text": o.get("description") or o.get("text") or "", "done": bool(o.get("done")),
                            "progress": o.get("progress"), "target": o.get("target")}
                           for o in m.get("objectives") or []]}


def _missions_progress(context, today, mission_id: Optional[str] = None):
    """The selected mission's objectives, each one done or +1 from the glasses."""
    page = _missions(context, today)
    missions = _active_missions(page)
    m = next((x for x in missions if x.get("id") == mission_id), None) or (missions[0] if missions else None)
    if m is None:
        return _panel("Log progress", [], "No active missions.")
    lines = []
    if m.get("ready"):
        lines.append(_line("Claim the reward", f"{m.get('reward_xp') or 0} XP", "ok",
                           {"kind": "mission.complete", "label": "Claim", "params": {"mission_id": m["id"]}}))
    for o in m.get("objectives") or []:
        target = o.get("target") or 1
        if o.get("done"):
            lines.append(_line(o.get("description") or o.get("text") or "", "done", "ok"))
            continue
        tally = target != 1
        if o.get("counts_itself"):  # a trip or task objective: it counts itself, nothing to tick
            lines.append(_line(o.get("description") or "", f"{(o.get('progress') or 0):g} of {target:g}"))
            continue
        lines.append(_line(o.get("description") or o.get("text") or "", f"{(o.get('progress') or 0):g} of {target:g}" if tally else "", "",
                           {"kind": "objective.tick", "label": "+1" if tally else "Done",
                            "params": {"mission_id": m["id"], "index": o.get("index", 0), "amount": 1}}))
    return _panel(m.get("name") or "Log progress", lines, "Nothing left to do on this one.")


def _missions_pick(context, today, mission_id: Optional[str] = None):
    """Every active mission (pick one for the Missions card) and everything
    that's due (Today's old list: maintenance, bills, chores...), each in
    its bucket so the glasses can sort by Past Due / Due Today / Due Soon."""
    from core.today import today_items

    page = _missions(context, today)
    missions = _active_missions(page)
    current = (mission_focus(context, today, mission_id) or {}).get("id")
    plan_daily = set()
    try:
        plan_daily = {m["mission_id"] for m in _fitness(context, today).get("missions") or []
                      if m.get("cadence") == "daily"}
    except Exception:
        log.debug("Glasses: no fitness plan missions", exc_info=True)
    lines = []
    when_bucket = {"overdue": "past_due", "today": "due_today", "waiting": "due_today", "soon": "due_soon"}
    try:
        due = [i.as_dict() for i in today_items(context, today)]
    except Exception:
        log.exception("Glasses: the due list failed")
        due = []
    for d in due:
        action = d.get("action")
        if action and action.get("kind") == "maintenance.done" and _asks_meter(context, action.get("params") or {}):
            action = None
        line = _line(d.get("title") or "", d.get("detail") or "",
                     "attention" if d.get("when") == "overdue" else "", action)
        line["bucket"] = when_bucket.get(d.get("when"))
        lines.append(line)
    for m in missions:
        daily = m.get("daily") or m.get("id") in plan_daily
        line = _line(m.get("name") or "", ("showing · " if m["id"] == current else "") +
                     (f"ready · {m.get('reward_xp') or 0} XP" if m.get("ready") else f"{m.get('done', 0)} of {m.get('total', 0)}"),
                     "ok" if m["id"] == current else "")
        line["pick"] = {"mission": m["id"], "label": "Show"}
        line["bucket"] = "due_today" if daily and not m.get("ready") else None
        lines.append(line)
    order = {"past_due": 0, "due_today": 1, "due_soon": 2, None: 3}
    lines.sort(key=lambda line: order[line.get("bucket")])
    panel = _panel("Select Mission", lines, "No active missions and nothing due.", limit=60)
    panel["filters"] = [{"id": None, "label": "All", "count": len(lines)}] + [
        {"id": b, "label": label, "count": sum(1 for line in lines if line.get("bucket") == b)} for b, label in BUCKETS]
    return panel


def _skills_focus(context, today):
    """Panel: the focus skill and XP to its next level, and how many skills are growing (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.web_progress import skills_page

    page = skills_page(context, today)
    focus = page.get("focus")
    counts = page.get("counts") or {}
    lines = []
    if focus:
        lines.append(_line(focus.get("name") or "", f"{focus.get('to_next')} XP to the next level"
                           if focus.get("to_next") is not None else "focus skill", "ok"))
    if counts:
        lines.append(_line(f"{counts.get('touched', 0)} skills growing", f"of {counts.get('skills', 0)}"))
    return _panel("Focus", lines, "Pick a focus skill in Skills.")


def _skills_week(context, today):
    """Panel: the skills that gained XP this week, most first (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.web_progress import skills_page

    growing = sorted((s for s in skills_page(context, today).get("skills") or [] if s.get("this_week")),
                     key=lambda s: -(s.get("this_week") or 0))
    return _panel("This week", [_line(s.get("name") or "", f"+{s['this_week']} XP · level {s.get('level')}")
                                for s in growing], "No skill XP yet this week.")


def _character_stats(context, today):
    """Panel: the person's level and XP and their non-zero character stats (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.web_progress import character_page

    page = character_page(context, today)
    me = page.get("me") or {}
    lines = [_line(f"Level {me.get('level', 1)}", f"{me.get('total_xp', 0)} XP")]
    for s in page.get("stats") or []:
        if s.get("value"):
            lines.append(_line(s.get("name") or "", f"{s['value']:g} {s.get('unit') or ''}".strip()))
    return _panel("Your story", lines, "")


def _character_buffs(context, today):
    """Panel: the buffs active today (core/buffs.py) (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.buffs import buffs

    return _panel("Buffs", [_line(f"{b['icon']} {b['name']}", f"+{b['bonus']} {b['stat'].capitalize()} · {b['lasts']}", "ok")
                            for b in buffs(context, today)], "No buffs right now.")


def _character_chronicle(context, today):
    """Panel: this week's chronicle story (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.chronicle import chronicle_page

    week = chronicle_page(context, today)["this_week"]
    return _panel(f"{week['title']}: {week['name']}", [_line(line) for line in week["story"]], "")


def _character_top(context, today):
    """Panel: the top skills by level (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.web_progress import character_page

    top = character_page(context, today).get("top_skills") or []
    return _panel("Top skills", [_line(s.get("name") or "", f"level {s.get('level')}") for s in top],
                  "No skills levelled yet.")


def _money(context, today):
    """The Money page's data (core/web_money.py)."""
    from core.web_money import money_page

    return money_page(context, today)


def _money_month(context, today):
    """Panel: this month's in, out and net, and what's left a month after bills and minimums (readouts only: no
    money actions on the glasses) (a menu item's readout; lines with an allowed action can be approved from the glasses).
    """
    from core.region import money

    page = _money(context, today)
    if not page.get("available", True):
        return _panel("This month", [], "Money isn't available here.")
    s = (page.get("summary") or {})
    month = s.get("month") or {}
    plan = s.get("monthly_plan") or {}
    lines = [_line(f"In {money(month.get('income') or 0)}", month.get("label") or "", "ok"),
             _line(f"Out {money(month.get('expenses') or 0)}", "", "bad"),
             _line(f"Net {money(month.get('net') or 0)}", "")]
    if plan.get("gap") is not None:
        lines.append(_line(f"{money(plan['gap'])} a month", "left after bills and minimums"))
    return _panel("This month", lines, "")


def _freedom(context, today):
    """The Freedom page's data (core/freedom.py)."""
    from core.freedom import freedom_page

    return freedom_page(context, today)


def _freedom_glance(context, today):
    """The work-night glance (H-0067): the fund, this week, the streak, what tonight's shift buys. Read-only."""
    page = _freedom(context, today)
    if not page.get("available"):
        return _panel("Freedom", [], "Freedom is a grown-up's plan.")
    p, t = page["plan"], page["plan"]["text"]
    if not p["goal"]:
        return _panel("Freedom", [], "Set up your plan on the phone: Freedom → Your Plan.")
    week = next((x for x in page["periods"] if x["id"] == "week"), {})
    lines = [_line(f"{t['saved']} of {t['goal']}", f"{p['progress_pct']:g}% of the fund" if p["progress_pct"] is not None else ""),
             _line(f"This week {week.get('total_text', '—')}", (f"{page['streak']} green weeks in a row"
                                                                 if page["streak"] else ""),
                   "ok" if (week.get("total") or 0) > 0 else "")]
    if page["range"]["earliest"]:
        latest = page["range"]["latest"]
        lines.append(_line("Free between " + page["range"]["earliest"][:7] + (" and " + latest[:7] if latest else " and later"),
                           "an estimate at your pace"))
    if page.get("shift"):
        sh = page["shift"]
        lines.append(_line(f"Tonight buys {sh['days_of_living']:g} days" if sh.get("days_of_living") else f"Tonight: {sh['pay_text']}",
                           sh["pay_text"]))
    return _panel("Freedom", lines, "")


def _freedom_next(context, today):
    """Panel: the next build in the Freedom plan: percent done, what's left, spent of budget (adults only) (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    page = _freedom(context, today)
    if not page.get("available"):
        return _panel("Next Build", [], "Freedom is a grown-up's plan.")
    b = page.get("next_build")
    if not b:
        return _panel("Next Build", [], "No builds in the plan yet.")
    return _panel("Next Build", [_line(b["name"], f"{b['pct']}% · {b['left_text']} to go"),
                                 _line(f"{b['spent_text']} of {b['budget_text']}", "")], "")


def _money_due(context, today):
    """Panel: bills due in the next two weeks (overdue flagged), then income expected in that time (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.region import money

    page = _money(context, today)
    lines = []
    for b in sorted(page.get("bills") or [], key=lambda b: b.get("days") if b.get("days") is not None else 999):
        if b.get("days") is not None and b["days"] <= 14:
            lines.append(_line(f"{b['name']} {money(b.get('amount') or 0)}", b.get("when") or "",
                               "bad" if b["days"] < 0 else "attention" if b["days"] <= 3 else ""))
    for i in page.get("income_sources") or []:
        if i.get("days") is not None and i["days"] <= 14:
            lines.append(_line(f"{i['name']} {money(i.get('amount') or 0)}", "expected " + (i.get("when") or ""),
                               "ok"))
    return _panel("What's due", lines, "Nothing due in the next two weeks.")


def _money_debts(context, today):
    """Panel: what's owed and the minimum payments, then each debt with its rate and balance (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.region import money

    debts = ((_money(context, today).get("summary") or {}).get("debts") or {})
    lines = []
    if debts.get("total"):
        lines.append(_line(f"{money(debts['total'])} owed", f"{money(debts.get('minimum_payments') or 0)} minimums"))
    for d in debts.get("ranked") or []:
        rate = d.get("interest_rate")
        lines.append(_line(d.get("name") or "", (f"{rate:g}% · " if rate else "") + money(d.get("balance") or 0)))
    return _panel("Debts", lines, "No debts. 🎉" if not debts.get("total") else "")


def _task_lines(context, rows: list[dict], with_asset: bool = True) -> list[dict]:
    """Equipment tasks as lines, each with its due bucket; an action that needs a typed meter reading is dropped (the
    glasses take no typed numbers).
    """
    lines = []
    for t in rows:
        action = t.get("action")
        if action and action.get("asks_meter"):
            action = None
        line = _line(f"{t.get('title')}: {t.get('asset')}" if with_asset else t.get("title") or "", t.get("text") or "",
                     "attention" if t.get("urgency") == "overdue" else "", action)
        line["bucket"] = bucket_of(t.get("days"), t.get("urgency") or "")
        lines.append(line)
    return lines


def _equipment_rows(context, scope: str, today) -> tuple[list[dict], list[dict]]:
    """An equipment scope's assets and its tasks (needing attention first, then next up, without repeats)."""
    from core.web_equipment import equipment_page

    page = equipment_page(context, scope, today)
    seen, rows = set(), []
    for t in (page.get("attention") or []) + (page.get("next_up") or []):
        if t["id"] not in seen:
            seen.add(t["id"])
            rows.append(t)
    return page.get("assets") or [], rows


ASSET_ITEM = "asset-"


def _asset_panel(context, scope: str, asset_id: str, today) -> Optional[dict]:
    """One thing you own: its condition, then everything due on it."""
    found, rows = _equipment_rows(context, scope, today)
    asset = next((a for a in found if a["id"] == asset_id), None)
    if asset is None:
        return None
    lines = _task_lines(context, [r for r in rows if r["asset_id"] == asset_id], with_asset=False)
    c = asset.get("condition")
    if c:
        lines.insert(0, _line("Condition", f"{c['percent']}% {c['label']}"))
    return _panel(asset.get("name") or "", lines, "Nothing due on this one.", limit=60)


def _equipment(scope: str):
    """Builds the four panels for an equipment scope (vehicles, home...): the assets (condition, past-due count, next
    task, each opening its asset) and the Past Due, Due Today and Due Soon task lists.
    """
    def assets(context, today):
        found, rows = _equipment_rows(context, scope, today)
        lines = []
        for a in found:
            late = sum(1 for r in rows if r["asset_id"] == a["id"] and bucket_of(r.get("days"), r.get("urgency") or "") == "past_due")
            nxt = next((r for r in rows if r["asset_id"] == a["id"]), None)
            c = a.get("condition")  # gear condition (DEC-0028)
            bits = [f"{c['percent']}% {c['label']}" if c else "", f"{late} past due" if late else "",
                    f"next: {nxt['title']} ({nxt['text']})" if nxt else ""]
            lines.append(_line(a.get("name") or "", " · ".join(b for b in bits if b) or (a.get("make_model") or ""),
                               "attention" if late else ""))
            lines[-1]["open"] = {"item": f"{ASSET_ITEM}{a['id']}", "label": "Open"}
        return _panel("Assets", lines, "Nothing tracked here yet.", limit=60)

    def in_bucket(bucket: str, label: str, empty: str):
        def build(context, today):
            _found, rows = _equipment_rows(context, scope, today)
            return _panel(label, _bucketed(_task_lines(context, rows), bucket), empty, limit=60)
        return build

    return (assets, in_bucket("past_due", "Past Due", "Nothing past due. Everything's cared for."),
            in_bucket("due_today", "Due Today", "Nothing due today."),
            in_bucket("due_soon", "Due Soon", "Nothing due in the next month."))


def _rentals(context, today):
    """Panel: the rental properties with status and monthly cash flow, flagging ones with tasks that need attention (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.region import money
    from core.web_screens import estate_page

    page = estate_page(context, today)
    lines = []
    for p in page.get("properties") or []:
        bits = [p.get("status") or ""]
        if p.get("cash_flow") is not None:
            bits.append(f"{money(p['cash_flow'])}/mo cash flow")
        lines.append(_line(p.get("name") or "", " · ".join(b for b in bits if b),
                           "attention" if any(t.get("needs_attention") for t in p.get("tasks") or []) else ""))
    return _panel("Properties", lines, "No properties yet.")


def _calendar(bucket: str, label: str, empty: str):
    """The Calendar on the glasses: Past Due, Due Today, Due Soon (core/calendar_view.py)."""
    def build(context, today):
        from core.calendar_view import calendar_page, day_label

        page = calendar_page(context, today)
        if bucket == "soon":
            found = [(d, i) for group in page["soon"] for i in group["items"] for d in (date.fromisoformat(group["date"]),)]
        else:
            found = [(date.fromisoformat(i["date"]), i) for i in page[bucket]]
        lines = []
        for day, i in found:
            when = [day_label(day, today) if bucket != "today" else "", i.get("time") or "", i.get("kind_label") or ""]
            action = i.get("action")
            if action and action.get("kind") == "maintenance.done" and _asks_meter(context, action.get("params") or {}):
                action = None
            lines.append(_line(i["title"], " · ".join(w for w in when if w),
                               "attention" if bucket == "past_due" else "", action))
        return _panel(label, lines, empty, limit=60)
    return build


def calendar_status(context, today: date) -> dict:
    """The Calendar card's one-line status: how many today, how many past due, or the next thing coming; {} when the
    calendar fails (logged, never breaks the cards).
    """
    from core.calendar_view import calendar_page

    try:
        page = calendar_page(context, today)
    except Exception:
        log.exception("Glasses: the calendar line failed")
        return {}
    late, now = len(page["past_due"]), len(page["today"])
    nxt = page["soon"][0] if page["soon"] else None
    bits = [f"{now} today" if now else "Nothing today", f"{late} past due" if late else "",
            f"next: {nxt['items'][0]['title']} ({nxt['label']})" if nxt and not now else ""]
    return {"line": " · ".join(b for b in bits if b), "tone": "attention" if late else "calm"}


def _trail(context, today):
    """Panel: the trip underway's route (core/trip_route.route_card): the next stop first, offering Arrived
    (trip.arrived, logged now), then the stops after it, the last leg walked and the distance so far. One trip at a
    time; with none underway it says how to start one."""
    from core.trip_route import route_card

    trips = getattr(context, "trips", None)
    underway = [t for t in trips.all_trips() if t.status == "active"] if trips is not None else []
    if not underway:
        return _panel("On The Trail", [], "No trip underway. Start one in Expeditions.")
    trip = underway[0]
    card = route_card(context, trip)
    lines = []
    if card["next"]:
        lines.append(_line(card["next"]["name"], "next stop", "", {"kind": "trip.arrived", "label": "Arrived",
                                                                  "params": {"trip_id": trip.trip_id,
                                                                             "waypoint_id": card["next"]["id"]}}))
    if card["legs"]:
        leg = card["legs"][-1]
        lines.append(_line(f"{leg['from']} to {leg['to']}", " · ".join(x for x in (f"{leg['km']} km", leg["took"], leg["pace"]) if x), "ok"))
    if card["walked_km"]:
        lines.append(_line("So far", f"{card['walked_km']} km" + (f" of {card['planned_km']}" if card["planned_km"] else "")))
    nxt = next((i for i, s in enumerate(card["stops"]) if card["next"] and s["id"] == card["next"]["id"] and not s["reached"]), None)
    later = card["stops"][nxt + 1:] if nxt is not None else []
    lines += [_line(s["name"], "later") for s in later]
    empty = "Every stop is reached." if card["stops"] else f"{trip.name} has no route. Add stops in Expeditions."
    return _panel("On The Trail · " + trip.name, lines, empty)


def _classroom_continue(context, today):
    """Panel: the course to continue (core/classroom_manager.continue_course): the lessons left in it, each with Done
    (lesson.done), and how far along the course is."""
    from core.classroom_manager import screen

    page = screen(context)
    course = page.get("continue")
    if not page.get("available"):
        return _panel("Continue", [], "The Classroom isn't available here.")
    if course is None:
        return _panel("Continue", [], "Nothing left to learn right now. Add a course in the Classroom.")
    left = next((c["lessons"] for s in page["subjects"] for c in s["courses"] if c["id"] == course["course_id"]), [])
    lines = [_line(l["name"], f"+{l['xp']} XP" if l["xp"] else "", "",
                   {"kind": "lesson.done", "label": "Done", "params": {"lesson_id": l["id"], "done": "yes"}})
             for l in left if not l["done"]]
    return _panel(f"{course['course']} · {course['done']} of {course['total']}", lines, "Every lesson is done.")


def _noticed(context, today):
    """Panel: what MIA noticed (core/observations_web.py), Needs You first in amber, each with its next step; a
    readout (settling one happens where it lives)."""
    from core.observations_web import screen

    page = screen(context, today)
    found = sorted(page.get("findings") or [], key=lambda f: f.get("kind") != "Needs You")
    lines = [_line(f["title"], f.get("next") or "", "attention" if f.get("kind") == "Needs You" else "") for f in found]
    lines += [_line(i["title"], i.get("next") or g["source"]) for g in page.get("insights") or [] for i in g["items"]]
    return _panel("What MIA Noticed", lines, "Nothing noticed lately. All quiet.")


def _lab_latest(context, today):
    """Panel: each series' latest reading in the Lab (its own and other apps'), newest first; a readout."""
    from core.web_lab import lab_page

    page = lab_page(context)
    if not page.get("available"):
        return _panel("Latest Readings", [], "The Lab isn't available here.")
    rows = sorted((page.get("series") or []) + (page.get("other_series") or []), key=lambda r: r.get("at") or "", reverse=True)
    return _panel("Latest Readings", [_line(r["name"], f"{r['latest']} · {r['when']}") for r in rows],
                  "No readings yet. Log one in the Lab.")


def _power_levels(context, today):
    """Panel: the battery, then each energy source's meters (amber when low), from core/web_power.py; a readout."""
    from core.web_power import power_page

    page = power_page(context)
    lines = []
    battery = page.get("battery") or {}
    if battery.get("available"):
        left = battery.get("minutes_left")
        detail = f"{battery['percent']}%" + (" · plugged in" if battery.get("plugged_in") else
                                             f" · {left // 60} h {left % 60} min left" if left else "")
        lines.append(_line("Battery", detail, "attention" if (battery.get("meter") or {}).get("tone") == "attention" else ""))
    for source in page.get("sources") or []:
        for m in source.get("meters") or []:
            lines.append(_line(f"{source['name']} · {m['name']}", f"{m['text']} · {m['when']}",
                               "attention" if (m.get("meter") or {}).get("tone") == "attention" else ""))
    return _panel("Power", lines, "No battery or energy sources here yet.")


def _journal_latest(context, today):
    """Panel: the newest journal notes (the plain journal, never the private one), each with its day and tags."""
    journal = getattr(context, "journal", None)
    entries = journal.all_entries() if journal is not None else []
    return _panel("Latest Notes", [_line(e.title, " · ".join(x for x in ((e.updated_at or e.created_at or "")[:10],
                                                                       ", ".join(e.tags[:2])) if x)) for e in entries],
                  "No notes yet. Say \"make a note\" and what to keep.")


def _memories_glance(context, today):
    """Panel: on this day in an earlier year first, then the latest trips, each with its distance and days."""
    from core.memories_web import screen

    page = screen(context, today)
    lines = [_line("On this day: " + r["name"], f"{r['start'][:4]} · {r['km']} km" if r["km"] else r["start"][:4], "ok")
             for r in page["on_this_day"]]
    lines += [_line(r["name"], " · ".join(x for x in (f"{r['km']} km" if r["km"] else "",
                                                     f"{r['days']} days" if r["days"] else "") if x)) for r in page["recaps"]]
    return _panel("Memories", lines, "No trips remembered yet.")


def _field_devices(context, today):
    """Panel: what's plugged in now (core/web_field_kit.py): storage with its size and where it's mounted, then boards
    on serial ports; a readout (ejecting stays on the PC)."""
    from core.web_field_kit import _devices

    found = _devices(context)
    if not found["available"]:
        return _panel("Plugged In", [], "This MIA can't look at its devices.")
    lines = [_line(d["name"], " · ".join(x for x in (d["size"], d["mounted"] or "not mounted", d["via"]) if x))
             for d in found["storage"]]
    lines += [_line(d["name"], " · ".join(x for x in (d["port"], d["board"]) if x)) for d in found["serial"]]
    return _panel("Plugged In", lines, "Nothing plugged in.")


def _waypoint_list(context, today):
    """Panel: the saved waypoints by name, with their kind and notes' first words; a readout (distances need a
    position: ask "how far is" one)."""
    book = getattr(context, "waypoints", None)
    points = book.all_waypoints() if book is not None else []
    return _panel("Waypoints", [_line(w.name, " · ".join(x for x in (w.category, (w.notes or "")[:40]) if x))
                                for w in points], "No waypoints saved yet.")


def _trail_maps(context, today):
    """Panel: the trail maps on this MIA, by park and state; a readout (they open on the phone or PC)."""
    library = getattr(context, "trail_maps", None)
    maps = library.all_trail_maps() if library is not None else []
    return _panel("Trail Maps", [_line(m.park_name, m.state) for m in sorted(maps, key=lambda m: m.park_name.lower())],
                  "No trail maps saved yet.")


def _project_tasks(context, today):
    """Panel: the open tasks of the projects underway (core/web_projects.py), soonest due first, each with Done
    (task.done) and its project and due day; up to five, the rest counted."""
    projects, tasks = getattr(context, "projects", None), getattr(context, "tasks", None)
    if projects is None or tasks is None:
        return _panel("Project Tasks", [], "Projects aren't available here.")
    lines = []
    for p in projects.all_projects():
        if p.status == "Complete":
            continue
        for t in tasks.tasks_for_project(p.project_id):
            if t.done:
                continue
            late = bool(t.due_date) and t.due_date < today.isoformat()
            lines.append((t.due_date or "9999", _line(t.title, p.name + (f" · by {t.due_date[5:]}" if t.due_date else ""),
                                                     "attention" if late else "",
                                                     {"kind": "task.done", "label": "Done", "params": {"task_id": t.task_id}})))
    lines.sort(key=lambda pair: pair[0])
    return _panel("Project Tasks", [line for _, line in lines], "No open tasks. Add some on the Projects page.")


def _household_chores(context, today):
    """Panel: the active household routines with this period's progress, each undone one offering Done
    (routine.log), those still to do first (a menu item's readout; lines with an allowed action can be approved from the glasses).
    """
    store = getattr(context, "recurring_missions", None)
    if store is None:
        return _panel("Chores", [], "Chores aren't available here.")
    lines = []
    for t in store.all_templates():
        if t.category != "Household" or not t.active:
            continue
        mission, _ = store.ensure_current_missions(t, today)
        objective = mission.objectives[0] if mission and mission.objectives else None
        if objective is None:
            continue
        done = objective.progress >= objective.target
        period = "today" if t.recurrence == "daily" else "this week"
        lines.append(_line(t.name, "done " + period if done else f"{objective.progress:g} of {objective.target:g} {period}",
                           "ok" if done else "",
                           None if done else {"kind": "routine.log", "label": "Done",
                                              "params": {"template_id": t.template_id}}))
    lines.sort(key=lambda line: "action" not in line)
    return _panel("Chores", lines, "No household routines yet. Ask MIA to set one up.")


def _people_birthdays(context, today):
    """Panel: the birthdays of the people and pets kept, soonest first, flagging the coming week (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    from core.relationships_manager import days_until_birthday

    store = getattr(context, "relationships", None)
    if store is None:
        return _panel("Birthdays", [], "People & Pets isn't available here.")
    found = []
    for who in list(store.all_people()) + list(store.all_pets()):
        days = days_until_birthday(getattr(who, "birthday", ""), today)
        if days is not None:
            found.append((days, who.name))
    found.sort()
    lines = []
    for days, name in found:
        when = today + timedelta(days=days)
        text = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
        lines.append(_line(name, f"birthday {text} · {when:%b} {when.day}", "attention" if days <= 7 else ""))
    return _panel("Birthdays", lines, "No birthdays saved yet.")


def _inbox_waiting(context, today):
    """Panel: the inbox documents waiting to be filed, newest first, with kind and date (a menu item's readout; lines with an allowed action can be approved from the glasses)."""
    store = getattr(context, "inbox", None)
    if store is None:
        return _panel("Waiting", [], "The inbox isn't available here.")
    lines = []
    for item in reversed(store.pending()):
        title = item.subject or item.vendor or (item.files[0] if item.files else "") or "A document"
        kind = (item.doc_type or "").replace("_", " ")
        bits = [b for b in (kind if kind != "other" else "", "reading…" if item.reading else "",
                            (item.received_at or "")[:10]) if b]
        lines.append(_line(title, " · ".join(bits)))
    return _panel("Waiting to file", lines, "Nothing waiting. All filed.")


_GARAGE, _GREEN, _HOME = (_equipment(s) for s in ("garage", "greenhouse", "real_estate"))


def _equipment_menu(builders) -> tuple:
    """The menu entries (id, label, builder) for an equipment scope's four panels."""
    return tuple(zip(("assets", "past_due", "due_today", "due_soon"),
                     ("Assets", "Past Due", "Due Today", "Due Soon"), builders))

Panel = Callable[[object, date], dict]

# Each app's quick action menu: (item id, label, panel builder).
PANELS: dict[str, tuple[tuple[str, str, Panel], ...]] = {
    "missions": (("pick", "Select Mission", _missions_pick), ("progress", "Log Progress", _missions_progress),
                 ("claim", "Ready To Claim", _missions_claim)),
    "music": (("songs", "Songs", _music_songs), ("playlists", "Playlists", _music_playlists), ("artists", "Artists", _music_artists)),
    "kitchen": (("cooking", "Cooking Now", _kitchen_cooking), ("recipes", "Recipes", _kitchen_recipes), ("meals", "Today's Meal Plan", _kitchen_meals),
                ("pantry", "My Pantry", _kitchen_pantry), ("grocery", "Grocery List", _kitchen_grocery)),
    "workout": (("live", "Active Training", _workout_live), ("training", "Today's Training", _workout_training), ("practice", "Skill Practice", _workout_practice),
                ("weight", "Weight", _workout_weight), ("milestones", "Milestones", _workout_milestones)),
    "freedom": (("tonight", "Tonight", _freedom_glance), ("next", "Next Build", _freedom_next)),
    "budget": (("month", "This Month", _money_month), ("due", "What's Due", _money_due),
               ("debts", "Debts", _money_debts)),
    "garage": _equipment_menu(_GARAGE),
    "greenhouse": _equipment_menu(_GREEN),
    # Every building you own and its appliances (Zac, 2026-10-16): the money
    # side, then the house and appliances, then their upkeep by bucket.
    "real_estate": (("properties", "Properties", _rentals), ("assets", "Home & Appliances", _HOME[0]),
                    ("past_due", "Past Due", _HOME[1]), ("due_today", "Due Today", _HOME[2]),
                    ("due_soon", "Due Soon", _HOME[3])),
    "calendar": (("past_due", "Past Due", _calendar("past_due", "Past Due", "Nothing past due. You're caught up.")),
                 ("today", "Due Today", _calendar("today", "Due Today", "Nothing on today.")),
                 ("soon", "Due Soon", _calendar("soon", "Due Soon", "Nothing in the next two weeks."))),
    "skills": (("focus", "Focus", _skills_focus), ("week", "This Week", _skills_week)),
    "character": (("story", "Your Story", _character_stats), ("buffs", "Buffs", _character_buffs),
                  ("chronicle", "This Week's Story", _character_chronicle),
                  ("top", "Top Skills", _character_top)),
    "household": (("chores", "Chores Due", _household_chores),),
    "relationships": (("birthdays", "Next Birthdays", _people_birthdays),),
    "inbox": (("waiting", "Waiting To File", _inbox_waiting),),
    "expeditions": (("trail", "On The Trail", _trail),),
    "workshop": (("tasks", "Project Tasks", _project_tasks),),
    "classroom": (("continue", "Continue", _classroom_continue),),
    "observations": (("noticed", "What MIA Noticed", _noticed),),
    "lab": (("latest", "Latest Readings", _lab_latest),),
    "power": (("levels", "Levels", _power_levels),),
    "notes": (("latest", "Latest Notes", _journal_latest),),
    "field_kit": (("devices", "Plugged In", _field_devices),),
    "navigation": (("waypoints", "Waypoints", _waypoint_list),),
    "maps": (("trail_maps", "Trail Maps", _trail_maps),),
    "memories": (("trips", "Memories", _memories_glance),),
}

# Questions an app's menu hands MIA, as if said aloud (she answers with
# her tools), after its panels; for apps without a panel yet, the whole
# menu. Questions only, never an example command: selecting one must not
# make a note or start a trip.
ASKS: dict[str, tuple[str, ...]] = {
    "household": ("Which chores are due?",),
    "workshop": ("What jobs are open?", "Which parts are running low?"),
    "power": ("How's the battery?", "How much power did I use today?"),
    "observations": ("What have you noticed lately?",),
    "notes": ("What were my last notes?",),
    "classroom": ("How is my learning progress?",),
    "inbox": ("What is waiting in my inbox?",),
    "expeditions": ("What's left on my route?", "What's my next trip?", "What gear do I need for my next trip?"),
    "memories": ("What was my last trip like?",),
    "maps": ("Which trail maps do I have?",),
    "navigation": ("How far is my nearest waypoint?", "When is sunset today?"),
    "lab": ("What are my latest lab readings?",),
    "field_kit": ("What devices are connected?",),
    "diagnostics": ("How is my system health?",),
    # Full use on the glasses too (DEC-0125, 2026-11-07): each answered by the app's own voice tool (a test checks
    # every ask reaches one), until a card of its own is drawn.
    "dungeon": ("How much loot did I make this week?",),
    "security": ("Are the cameras working?",),
    "issues": ("What is in the Fix-It Log?",),
    "compliance": ("What deadlines are coming up?",),
    "flock": ("How many eggs did the hens lay today?", "How many eggs this week?"),
    "business": ("How much profit did I make this month?",),
    "insurance": ("When does my insurance renew?",),
    "reward_shop": ("What can I buy with my credits?",),
    "vault": ("Do I have photos of the garden?",),
    "knowledge": ("Which woodworking plans do you have?",),
    "toolbox": ("Can you convert 5 gallons to liters?", "How many board feet in a 2x6 that is 8 feet long?"),
    "operating_journal": ("Am I living how I said I want to?",),
    "life_notes": ("What did I promise?", "What ideas have I had?"),
    "play": ("How much have I played this week?",),
    "good_news": ("What's the good news?",),
    "browser": ("Which browser tasks have you learned?",),
    "files": ("Which files are in my MIA folder?",),
}

# The cards for the apps that only had an ask (core/glasses_cards.py, Zac, 2026-11-08): each app's readout panels,
# from its own page assembler; its asks above stay after them in the menu.
from core.glasses_cards import PANELS as _MORE_PANELS  # noqa: E402  (it builds on _line and _panel above)
from core.glasses_cards import STATUS_FROM as _MORE_STATUS  # noqa: E402
from core.glasses_cards import status as _more_status  # noqa: E402

PANELS.update(_MORE_PANELS)
from core.glasses_cards import EXTRA as _MORE_ITEMS  # noqa: E402  (What's Next, Your Campaign, My Directions, Good Runs, Connections, The Job, Tracks, Practice)

for _app, _items in _MORE_ITEMS.items():
    PANELS[_app] = PANELS.get(_app, ()) + _items


EQUIPMENT_SCOPES = ("garage", "greenhouse")


def _equipment_status(context, scope: str, today: date) -> dict:
    """One equipment screen's line: how many need attention, and what's next."""
    from core.web_equipment import equipment_page

    try:
        page = equipment_page(context, scope, today)
    except Exception:
        log.exception("Glasses: the %s line failed", scope)
        return {}
    late = page.get("attention") or []
    nxt = (page.get("next_up") or [None])[0]
    bits = [f"{len(page.get('assets') or [])} tracked"]
    if late:
        bits.append(f"{len(late)} need{'s' if len(late) == 1 else ''} attention")
    if nxt:
        bits.append(f"next: {nxt.get('title')} ({nxt.get('asset')})")
    return {"line": " · ".join(bits), "tone": "attention" if late else "calm"}


def _tile(label: str, value, tone: str = "") -> dict:
    """One status tile on a card (label, value, tone)."""
    return {"label": label, "value": str(value), "tone": tone}


def _kitchen_tiles(context, today) -> list[dict]:
    """Kitchen's card tiles: meals eaten of planned, grocery items left, pantry expiring, recipes."""
    from core.web_screens import kitchen_page

    page = kitchen_page(context, today)
    meals = (((_fitness(context, today).get("today") or {}).get("meals") or {}).get("meals")) or []
    expiring = [p for p in page.get("pantry") or [] if p.get("expires_in") is not None and p["expires_in"] <= 2]
    return [_tile("Meals", f"{sum(1 for m in meals if m.get('eaten'))}/{len(meals)}"),
            _tile("Grocery", sum(1 for g in page.get("grocery") or [] if not g.get("checked"))),
            _tile("Expiring", len(expiring), "attention" if expiring else ""),
            _tile("Recipes", sum(1 for r in page.get("recipes") or [] if not r.get("locked")))]


def _workout_tiles(context, today) -> list[dict]:
    """Workout's card tiles: today's training (or Rest), steps done, protein against target."""
    page = _fitness(context, today)
    t = page.get("today") or {}
    training = t.get("training") if not t.get("rest_day") else None
    steps = (training or {}).get("steps") or []
    food = t.get("food") or {}
    target = (food.get("targets") or {}).get("protein_g")
    tiles = [_tile("Today", (training or {}).get("name") or "Rest"),
             _tile("Steps", f"{sum(1 for s in steps if s.get('done'))}/{len(steps)}")]
    if target:
        tiles.append(_tile("Protein", f"{round((food.get('totals') or {}).get('protein_g') or 0)}/{target} g"))
    return tiles


def _equipment_tiles(scope: str):
    """Builds an equipment scope's card tiles: tracked, past due, due today, due soon."""
    def build(context, today) -> list[dict]:
        found, rows = _equipment_rows(context, scope, today)
        buckets = [bucket_of(r.get("days"), r.get("urgency") or "") for r in rows]
        late = buckets.count("past_due")
        return [_tile("Tracked", len(found)), _tile("Past Due", late, "attention" if late else ""),
                _tile("Today", buckets.count("due_today")), _tile("Soon", buckets.count("due_soon"))]
    return build


def _music_tiles(context, today) -> list[dict]:
    """Music's card tiles: songs, playlists, artists."""
    page = _music(context)
    return [_tile("Songs", len(page.get("tracks") or [])), _tile("Playlists", len(page.get("playlists") or [])),
            _tile("Artists", len(page.get("artists") or []))]


def _calendar_tiles(context, today) -> list[dict]:
    """Calendar's card tiles: past due, today, soon."""
    from core.calendar_view import calendar_page

    page = calendar_page(context, today)
    late = len(page["past_due"])
    return [_tile("Past Due", late, "attention" if late else ""), _tile("Today", len(page["today"])), _tile("Soon", len(page["soon"]))]


# The numbers at the top of an app's screen. No money here (H-0041).
TILES = {"kitchen": _kitchen_tiles, "workout": _workout_tiles, "garage": _equipment_tiles("garage"),
         "greenhouse": _equipment_tiles("greenhouse"), "calendar": _calendar_tiles, "music": _music_tiles}
# The new cards' tiles (core/glasses_cards.py, 2026-11-08): Chickens, the Dungeon, Compliance, Reward Shop, Orders.
from core.glasses_cards import TILES as _MORE_TILES  # noqa: E402

TILES.update(_MORE_TILES)


def _tiles(context, module_id: str, today: date) -> list[dict]:
    """A card's tiles, or [] for an app without them or when building them fails (logged)."""
    if module_id not in TILES:
        return []
    try:
        return TILES[module_id](context, today)
    except Exception:
        log.exception("Glasses: the tiles for %s failed", module_id)
        return []


def _visible_apps(context) -> list:
    """The apps the glasses show, in the glasses' order (FIRST, then the rest): visible to this person (child-safe,
    not tucked away), not kept off the glasses, and with a panel or an ask to open.
    """
    from core.web_surfaces import APPS, APPS_BY_ID, _visible

    order = list(FIRST) + [a.module_id for a in APPS if a.module_id not in FIRST]
    out = []
    for module_id in order:
        app = APPS_BY_ID.get(module_id)
        if app is None or module_id in NOT_ON_GLASSES or not _visible(context, app):
            continue
        if module_id not in PANELS and module_id not in ASKS:
            continue
        out.append(app)
    return out


def menu_for(app, pinned: Optional[bool] = None) -> list[dict]:
    """Pure logic. An app's quick action menu: its panels, then questions
    for MIA, at most five; then pin or unpin it for the glasses (its
    favorite star) when `pinned` is known."""
    items = [{"id": item, "label": label, "type": "panel"} for item, label, _ in PANELS.get(app.module_id, ())]
    if app.module_id == "music":
        items.insert(0, {"id": "now", "label": "Now Playing", "type": "player"})
    items += [{"id": f"ask{i}", "label": say.rstrip("?.!"), "type": "ask", "say": say}
              for i, say in enumerate(ASKS.get(app.module_id, ()))]
    items = items[:5]
    if pinned is not None:
        items.append({"id": "pin", "label": "Unpin From Glasses" if pinned else "Pin To Glasses", "type": "action",
                      "action": {"kind": "app.favorite", "label": "Unpin" if pinned else "Pin",
                                 "params": {"module_id": app.module_id, "favorite": not pinned}}})
    return items


def priority_now(apps: list[dict]) -> str:
    """Pure logic. The one line on Home: what needs attention, else the
    mission's next step, else nothing."""
    late = next((a for a in apps if a.get("tone") == "attention" and a.get("status")), None)
    if late:
        return f"{late['name']}: {late['status']}"
    mission = next((a.get("mission") for a in apps if a.get("mission")), None)
    step = next((o["text"] for o in (mission or {}).get("objectives", []) if not o["done"]), "")
    return step or ""


def priority_tone(apps: list[dict]) -> str:
    """Pure logic. How Home's line reads (the canvas's orb, DEC-0113): "attention" when an app needs the person (her
    orb turns amber), "" for a mission step or nothing."""
    return "attention" if any(a.get("tone") == "attention" and a.get("status") for a in apps) else ""


def glasses_apps(context, today: Optional[date] = None, mission_id: Optional[str] = None) -> dict:
    """The person's glasses cards: their pinned apps (favorites), then the
    rest behind "All apps". Each card has a status line (its at-a-glance line, or for the cards drawn 2026-11-08 their
    first panel's first line: core/glasses_cards.status) and its menu; Home's
    line is `priority`, with `priority_tone` for her orb; `areas` is the Nexus's ring (glasses_areas)."""
    from core.focus_presets import favorite_apps
    from core.web_surfaces import dashboard

    today = today or date.today()
    try:
        glance = {g["app"]: g for g in dashboard(context).get("glance") or []}
    except Exception:
        log.exception("Glasses: the at-a-glance lines failed")
        glance = {}
    apps = _visible_apps(context)
    try:
        favorites = favorite_apps(context)
    except Exception:  # a headless context without settings
        favorites = []
    by_id = {a.module_id: a for a in apps}
    # Missions always comes right after the orb (Zac, 2026-10-16), then the pins.
    pinned_ids = [f for f in dict.fromkeys(favorites) if f in by_id and f != "missions"]
    if pinned_ids and "missions" in by_id:
        pinned_ids.insert(0, "missions")

    def card(app) -> dict:
        g = glance.get(app.module_id) or {}
        if app.module_id in EQUIPMENT_SCOPES:
            g = _equipment_status(context, app.module_id, today)
        elif app.module_id == "calendar":
            g = calendar_status(context, today)
        elif not g.get("line") and app.module_id in _MORE_STATUS:
            g = _more_status(context, app.module_id, today)
        return {
            "id": app.module_id, "name": SHORT_NAMES.get(app.module_id, app.name), "full_name": app.name,
            "tagline": app.tagline, "status": g.get("line") or "", "tone": g.get("tone") or "calm",
            "ask": app.ask, "pinned": app.module_id in pinned_ids, "tiles": _tiles(context, app.module_id, today),
            "menu": menu_for(app, None if app.module_id == "missions" else app.module_id in pinned_ids),
            **({"mission": mission_focus(context, today, mission_id)} if app.module_id == "missions" else {}),
        }

    pinned = [card(by_id[i]) for i in pinned_ids]
    others = [card(a) for a in apps if a.module_id not in pinned_ids]
    return {"as_of": today.isoformat(), "pinned": bool(pinned), "priority": priority_now(pinned + others),
            "priority_tone": priority_tone(pinned + others),
            "apps": pinned or others, "others": others if pinned else [],
            "hint": "" if pinned else "Star your favorite apps to pin them here.",
            "kinds": sorted(GLASSES_KINDS),
            # DEC-0130 (NEXUS_PLAN M4): the Nexus on the glasses, a flat ring of areas, each with its apps here
            "areas": glasses_areas(context, [c["id"] for c in pinned + others], today),
            # DEC-0136: only a theme's accent travels to the lens (black is see-through), lifted to read on it
            "accent": _accent(context)}


def _accent(context) -> dict:
    """The person's theme accent for the lens (core/themes.glasses_accent); Stark's cyan when it can't be read."""
    try:
        from core.themes import glasses_accent

        return glasses_accent(context)
    except Exception:  # noqa: BLE001 - the glasses keep their own cyan
        return {}


def short_name(name: str) -> str:
    """Pure logic. An area's name short enough for the glasses' ring: "and" becomes "&", and Settings and Diagnostics
    is Settings."""
    return "Settings" if name.startswith("Settings") else name.replace(" and ", " & ")


def glasses_areas(context, app_ids: list[str], today: date) -> list[dict]:
    """The Nexus on the glasses (DEC-0130): each area (in order) that has an app on the glasses, with its hue, those
    apps' ids, and how many of today's items in it need you. No particles or depth here: the display shows light and
    black is see-through, so it's names on black."""
    from core.web_areas import AREAS
    from core.web_nexus import _today, portal_status

    have = set(app_ids)
    status = portal_status(_today(context, today))
    out = []
    for area in AREAS:
        ids = [m for m in area.members if isinstance(m, str) and m in have]
        if ids:
            out.append({"id": area.id, "name": area.name, "short": short_name(area.name), "hue": area.hue, "apps": ids,
                        "needs": status.get(area.id, 0)})
    return out


def glasses_panel(context, app_id: str, item_id: str, today: Optional[date] = None,
                  mission_id: Optional[str] = None) -> Optional[dict]:
    """One menu item's readout, or None for an app or item the person doesn't have.
    `mission_id`: the mission the glasses' Missions card is showing."""
    today = today or date.today()
    if app_id not in {a.module_id for a in _visible_apps(context)}:
        return None
    for item, label, build in PANELS.get(app_id, ()):
        if item == item_id:
            panel = build(context, today, mission_id) if build in (_missions_progress, _missions_pick) \
                else build(context, today)
            return {"app": app_id, "item": item_id, "label": label, **panel}
    if item_id.startswith(RECIPE_ITEM) and app_id == "kitchen":
        panel = _recipe_shelf(context, today, item_id[len(RECIPE_ITEM):])
        return {"app": app_id, "item": item_id, "label": panel["title"], **panel} if panel else None
    if item_id.startswith(MUSIC_LIST) and app_id == "music":
        panel = _music_list(context, item_id[len(MUSIC_LIST):])
        return {"app": app_id, "item": item_id, "label": panel["title"], **panel} if panel else None
    if item_id.startswith(ASSET_ITEM) and app_id in EQUIPMENT_SCOPES:
        panel = _asset_panel(context, app_id, item_id[len(ASSET_ITEM):], today)
        return {"app": app_id, "item": item_id, "label": panel["title"], **panel} if panel else None
    return None
