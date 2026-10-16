"""
core.glasses
==============

The glasses' app cards and their quick action menus (Zac, 2026-10-16;
Muse's H-0041 Phase 2). The glasses boot to MIA's orb; one swipe away,
the person flips through app cards; selecting one opens its quick action
menu. Assembled here, in code, so `web/glasses.js` holds no logic
(DEC-0013), from the same page assemblers every other screen uses.

- `glasses_apps(context)`: the person's apps as glasses cards, in the
  glasses' order (child-safe, respecting apps they've tucked away), each
  with a one-line status and its menu. Served as `/api/glasses`.
- `glasses_panel(context, app_id, item_id)`: what one menu item shows: a
  title and a few lines, each line optionally carrying the action it
  proposes. Served as `/api/glasses/{app_id}/{item_id}`.

A menu item is either a `panel` (a short readout, some lines of which
can be acted on) or an `ask` (a question handed to MIA, as if said
aloud). Every action still goes Propose → Approve → Execute → Record →
Undo through `/api/actions`; the glasses show the proposal's sentence
and a second gesture approves it (H-0008, H-0012).

**What the glasses may change** is `GLASSES_KINDS`: quick, everyday,
non-destructive things (ate it, a step done, a mission claimed, a chore
or upkeep done, a grocery item checked). Nothing that deletes, nothing
that needs a typed number, and no money (H-0041: money stays readouts on
the glasses in v1). A line whose action isn't in the list is shown as a
readout only.
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

# The action kinds a glasses line may carry. Never a delete, a money
# movement, or anything that needs a number typed in.
GLASSES_KINDS = frozenset({
    "fitness.food", "fitness.step", "fitness.training_done", "fitness.skill", "fitness.milestone",
    "mission.complete", "objective.tick", "maintenance.done", "grocery.check",
    "task.done", "meal.prep_done", "routine.log",
})

# Apps the glasses don't show as cards: the orb *is* Home and Talk; the
# Apps manager, Settings and Files are for a bigger screen.
NOT_ON_GLASSES = frozenset({"web_home", "assistant", "module_browser", "settings", "files"})

# The glasses' order: Today, then the apps used most on the move, then
# the rest of MIA in its usual order.
FIRST = ("dashboard", "missions", "kitchen", "workout", "budget", "garage", "maintenance", "greenhouse",
         "property", "real_estate", "skills", "character")

# Short names for a 600 px card, where the app's own name is long.
SHORT_NAMES = {"dashboard": "Today", "relationships": "People", "real_estate": "Rentals"}

MAX_LINES = 5


def _line(text: str, detail: str = "", tone: str = "", action: Optional[dict] = None) -> dict:
    out = {"text": text, "detail": detail, "tone": tone}
    if action and action.get("kind") in GLASSES_KINDS:
        out["action"] = {"kind": action["kind"], "label": action.get("label") or "Do it",
                         "params": dict(action.get("params") or {})}
    return out


def _panel(title: str, lines: list[dict], empty: str, more: int = 0) -> dict:
    return {"title": title, "lines": lines[:MAX_LINES], "more": max(0, more + len(lines) - MAX_LINES),
            "empty": empty}


# ---------------------------------------------------------------- panels


def _today_next(context, today):
    from core.web_surfaces import dashboard

    d = dashboard(context)
    lines = []
    for f in d.get("focus") or []:
        action = f.get("action")
        if action and action.get("kind") == "maintenance.done" and _asks_meter(context, (action.get("params") or {})):
            action = None
        lines.append(_line(f.get("title") or "", f.get("detail") or "",
                           "attention" if f.get("when") == "overdue" else "", action))
    return _panel("What's next", lines, "Nothing needs you. Enjoy it.")


def _today_coming(context, today):
    from core.web_surfaces import dashboard

    d = dashboard(context)
    return _panel("Coming up", [_line(u.get("title") or "", u.get("detail") or "") for u in d.get("upcoming") or []],
                  "Nothing coming up.")


def _today_wins(context, today):
    from core.web_surfaces import dashboard

    d = dashboard(context)
    wins = [w for w in d.get("wins") or [] if w.get("type") != "mission_missed"]
    return _panel("Recent wins", [_line(w.get("summary") or "") for w in wins], "No wins logged yet today.")


def _asks_meter(context, params: dict) -> bool:
    """A meter task's completion asks for the reading, which the glasses can't type."""
    try:
        task = context.maintenance.get_task(params.get("task_id"))
        return bool(task) and task.trigger_type != "calendar" and params.get("meter_value") is None
    except Exception:
        return False


def _fitness(context, today):
    from core.web_fitness import fitness_page

    return fitness_page(context, today)


def _kitchen_meals(context, today):
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
    return _panel("Today's meals", lines, "No meals planned today. Plan them in Kitchen → Week.")


def _kitchen_grocery(context, today):
    from core.web_screens import kitchen_page

    items = [g for g in kitchen_page(context, today).get("grocery") or [] if not g.get("checked")]
    lines = []
    for g in items:
        qty = g.get("quantity")
        amount = f"{qty:g} {g.get('unit') or ''}".strip() if qty else ""
        lines.append(_line(g.get("name") or "", " · ".join(x for x in (amount, g.get("for_recipe") or "") if x), "",
                           {"kind": "grocery.check", "label": "Got it",
                            "params": {"item_id": g["id"], "checked": True}}))
    return _panel("Grocery list", lines, "The grocery list is empty.")


def _kitchen_use_soon(context, today):
    from core.web_screens import kitchen_page

    items = sorted((p for p in kitchen_page(context, today).get("pantry") or [] if p.get("expiring")),
                   key=lambda p: p.get("expires_in") if p.get("expires_in") is not None else 99)
    lines = []
    for p in items:
        days = p.get("expires_in")
        when = "expired" if days is not None and days < 0 else "today" if days == 0 else f"in {days}d"
        lines.append(_line(p.get("name") or "", f"expires {when}" if days is not None else "",
                           "attention" if days is not None and days <= 0 else ""))
    return _panel("Use soon", lines, "Nothing in the pantry is about to expire.")


def _kitchen_make(context, today):
    from core.web_screens import kitchen_page

    page = kitchen_page(context, today)
    makeable = [r for r in page.get("recipes") or [] if r.get("makeable") and not r.get("locked")]
    lines = [_line(r.get("name") or "", f"{r['minutes']} min" if r.get("minutes") else "") for r in makeable]
    return _panel("You can make", lines, "Nothing has everything in the pantry. Check the grocery list.")


def _workout_training(context, today):
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
                                                       "params": {"step": s["index"]}}))
    if not training.get("done"):
        lines.append(_line("Finish today's training", training.get("name") or "", "",
                           {"kind": "fitness.training_done", "label": "Training done", "params": {}}))
    return _panel(f"Training: {training.get('name') or 'today'}", lines, "Nothing planned today.")


def _workout_practice(context, today):
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
    ms = _fitness(context, today).get("milestones") or []
    lines = [_line(m.get("name") or "", f"reached {m['done_on']}" if m.get("done_on") else "",
                   "ok" if m.get("done_on") else "",
                   None if m.get("done_on") else {"kind": "fitness.milestone", "label": "Reached it",
                                                  "params": {"milestone_id": m["id"]}})
             for m in ms]
    return _panel("Milestones", lines, "No milestones in your plan yet.")


def _missions(context, today):
    from core.web_progress import missions_page

    return missions_page(context, today)


def _mission_line(m: dict) -> dict:
    progress = f"{m.get('done', 0)} of {m.get('total', 0)}"
    if m.get("ready"):
        return _line(m.get("name") or "", f"ready · {m.get('reward_xp') or 0} XP", "ok",
                     {"kind": "mission.complete", "label": "Claim", "params": {"mission_id": m["id"]}})
    objectives = [o for o in m.get("objectives") or [] if not o.get("done")]
    action = None
    if len(objectives) == 1 and (objectives[0].get("target") or 1) == 1:
        action = {"kind": "objective.tick", "label": "Done",
                  "params": {"mission_id": m["id"], "index": objectives[0].get("index", 0), "amount": 1}}
    return _line(m.get("name") or "", progress, "", action)


def _missions_today(context, today):
    page = _missions(context, today)
    # Daily missions, and the ones the person's fitness plan makes for today.
    try:
        plan_daily = {m["mission_id"] for m in _fitness(context, today).get("missions") or []
                      if m.get("cadence") == "daily"}
    except Exception:
        log.exception("Glasses: the plan's missions failed")
        plan_daily = set()
    daily = [m for m in (page.get("daily") or []) + (page.get("active") or [])
             if m.get("status") == "active" and (m.get("daily") or m.get("id") in plan_daily)]
    return _panel("Today's missions", [_mission_line(m) for m in daily], "No daily missions today.")


def _missions_claim(context, today):
    page = _missions(context, today)
    ready = [m for m in (page.get("daily") or []) + (page.get("active") or []) if m.get("ready")]
    return _panel("Ready to claim", [_mission_line(m) for m in ready], "Nothing to claim yet. Keep going.")


def _missions_active(context, today):
    page = _missions(context, today)
    active = [m for m in page.get("active") or [] if not m.get("ready")]
    return _panel("Active missions", [_line(m.get("name") or "", f"{m.get('percent', 0)}%") for m in active],
                  "No active missions.")


def _skills_focus(context, today):
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
    from core.web_progress import skills_page

    growing = sorted((s for s in skills_page(context, today).get("skills") or [] if s.get("this_week")),
                     key=lambda s: -(s.get("this_week") or 0))
    return _panel("This week", [_line(s.get("name") or "", f"+{s['this_week']} XP · level {s.get('level')}")
                                for s in growing], "No skill XP yet this week.")


def _character_stats(context, today):
    from core.web_progress import character_page

    page = character_page(context, today)
    me = page.get("me") or {}
    lines = [_line(f"Level {me.get('level', 1)}", f"{me.get('total_xp', 0)} XP")]
    for s in page.get("stats") or []:
        if s.get("value"):
            lines.append(_line(s.get("name") or "", f"{s['value']:g} {s.get('unit') or ''}".strip()))
    return _panel("Your story", lines, "")


def _character_top(context, today):
    from core.web_progress import character_page

    top = character_page(context, today).get("top_skills") or []
    return _panel("Top skills", [_line(s.get("name") or "", f"level {s.get('level')}") for s in top],
                  "No skills levelled yet.")


def _money(context, today):
    from core.web_money import money_page

    return money_page(context, today)


def _money_month(context, today):
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


def _money_due(context, today):
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
    from core.region import money

    debts = ((_money(context, today).get("summary") or {}).get("debts") or {})
    lines = []
    if debts.get("total"):
        lines.append(_line(f"{money(debts['total'])} owed", f"{money(debts.get('minimum_payments') or 0)} minimums"))
    for d in debts.get("ranked") or []:
        rate = d.get("interest_rate")
        lines.append(_line(d.get("name") or "", (f"{rate:g}% · " if rate else "") + money(d.get("balance") or 0)))
    return _panel("Debts", lines, "No debts. 🎉" if not debts.get("total") else "")


def _equipment(scope: str):
    def attention(context, today):
        from core.web_equipment import equipment_page

        page = equipment_page(context, scope, today)
        lines = []
        for t in page.get("attention") or []:
            action = t.get("action")
            if action and action.get("asks_meter"):
                action = None
            lines.append(_line(f"{t.get('title')}: {t.get('asset')}", t.get("text") or "",
                               "attention" if t.get("urgency") == "overdue" else "", action))
        return _panel("Needs attention", lines, "Everything's cared for.")

    def next_up(context, today):
        from core.web_equipment import equipment_page

        page = equipment_page(context, scope, today)
        return _panel("Next up", [_line(f"{t.get('title')}: {t.get('asset')}", t.get("text") or "")
                                  for t in page.get("next_up") or []], "Nothing due in the next month.")

    return attention, next_up


def _rentals(context, today):
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


def _rental_upkeep(context, today):
    from core.web_screens import estate_page

    lines = []
    for p in estate_page(context, today).get("properties") or []:
        for t in p.get("tasks") or []:
            if t.get("needs_attention"):
                action = t.get("action")
                lines.append(_line(f"{t.get('title')}: {p.get('name')}", t.get("text") or "", "attention",
                                   None if not action or action.get("asks_meter") else action))
    return _panel("Upkeep", lines, "Every property is cared for.")


_GARAGE, _MAINT, _GREEN, _PROP = (_equipment(s) for s in ("garage", "maintenance", "greenhouse", "property"))

Panel = Callable[[object, date], dict]

# Each app's quick action menu: (item id, label, panel builder).
PANELS: dict[str, tuple[tuple[str, str, Panel], ...]] = {
    "dashboard": (("next", "What's next", _today_next), ("coming", "Coming up", _today_coming),
                  ("wins", "Recent wins", _today_wins)),
    "missions": (("today", "Today's missions", _missions_today), ("claim", "Ready to claim", _missions_claim),
                 ("active", "Active missions", _missions_active)),
    "kitchen": (("meals", "Today's meals", _kitchen_meals), ("grocery", "Grocery list", _kitchen_grocery),
                ("use_soon", "Use soon", _kitchen_use_soon), ("make", "What can I make", _kitchen_make)),
    "workout": (("training", "Today's training", _workout_training), ("practice", "Skill practice", _workout_practice),
                ("weight", "Weight", _workout_weight), ("milestones", "Milestones", _workout_milestones)),
    "budget": (("month", "This month", _money_month), ("due", "What's due", _money_due),
               ("debts", "Debts", _money_debts)),
    "garage": (("attention", "Needs attention", _GARAGE[0]), ("next", "Next up", _GARAGE[1])),
    "maintenance": (("attention", "Needs attention", _MAINT[0]), ("next", "Next up", _MAINT[1])),
    "greenhouse": (("attention", "Needs attention", _GREEN[0]), ("next", "Next up", _GREEN[1])),
    "property": (("attention", "Needs attention", _PROP[0]), ("next", "Next up", _PROP[1])),
    "real_estate": (("properties", "Properties", _rentals), ("upkeep", "Upkeep", _rental_upkeep)),
    "skills": (("focus", "Focus", _skills_focus), ("week", "This week", _skills_week)),
    "character": (("story", "Your story", _character_stats), ("top", "Top skills", _character_top)),
}

# Apps without a glasses readout yet: their menu asks MIA a question,
# as if said aloud (she answers with her tools). Questions only, never an
# example command: selecting one must not make a note or start a trip.
ASKS: dict[str, tuple[str, ...]] = {
    "household": ("What chores are due?", "What did I get done this week?"),
    "workshop": ("What jobs are open?", "Which parts are running low?"),
    "power": ("How's the battery?", "How much power did I use today?"),
    "observations": ("What have you noticed lately?",),
    "relationships": ("When is the next birthday?", "Who haven't I talked to in a while?"),
    "notes": ("What were my last notes?",),
    "classroom": ("What should I study next?",),
    "inbox": ("What's waiting in my inbox?", "Any emails I should answer?"),
    "expeditions": ("What's my next trip?", "What gear am I missing for it?"),
    "memories": ("What was my last trip like?",),
    "maps": ("Which trail maps do I have?",),
    "navigation": ("How far is my nearest waypoint?", "When is sunset today?"),
    "lab": ("What's my latest experiment reading?",),
    "field_kit": ("What devices are connected?",),
    "music": ("What's playing?",),
    "diagnostics": ("How is the computer doing?",),
}


EQUIPMENT_SCOPES = ("garage", "maintenance", "greenhouse", "property")


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


def _visible_apps(context) -> list:
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


def menu_for(app) -> list[dict]:
    """Pure logic. An app's quick action menu, at most four items."""
    if app.module_id in PANELS:
        return [{"id": item, "label": label, "type": "panel"} for item, label, _ in PANELS[app.module_id]][:4]
    asks = ASKS.get(app.module_id, ())
    return [{"id": f"ask{i}", "label": say.rstrip("?.!"), "type": "ask", "say": say}
            for i, say in enumerate(asks[:3])]


def glasses_apps(context, today: Optional[date] = None) -> dict:
    """The person's glasses app cards, each with a status line and its menu."""
    from core.web_surfaces import dashboard

    today = today or date.today()
    try:
        glance = {g["app"]: g for g in dashboard(context).get("glance") or []}
    except Exception:
        log.exception("Glasses: the at-a-glance lines failed")
        glance = {}
    cards = []
    for app in _visible_apps(context):
        g = glance.get(app.module_id) or {}
        if app.module_id in EQUIPMENT_SCOPES:
            g = _equipment_status(context, app.module_id, today)
        cards.append({
            "id": app.module_id, "name": SHORT_NAMES.get(app.module_id, app.name), "full_name": app.name,
            "tagline": app.tagline, "status": g.get("line") or "", "tone": g.get("tone") or "calm",
            "ask": app.ask, "menu": menu_for(app),
        })
    return {"as_of": today.isoformat(), "apps": cards, "kinds": sorted(GLASSES_KINDS)}


def glasses_panel(context, app_id: str, item_id: str, today: Optional[date] = None) -> Optional[dict]:
    """One menu item's readout, or None for an app or item the person doesn't have."""
    today = today or date.today()
    if app_id not in {a.module_id for a in _visible_apps(context)}:
        return None
    for item, label, build in PANELS.get(app_id, ()):
        if item == item_id:
            panel = build(context, today)
            return {"app": app_id, "item": item_id, "label": label, **panel}
    return None
