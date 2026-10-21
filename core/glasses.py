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
  in the glasses' order. Served as `/api/glasses`.
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

from datetime import date, timedelta
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

# The action kinds a glasses line may carry. Never a delete, a money
# movement, or anything that needs a number typed in.
GLASSES_KINDS = frozenset({
    "fitness.food", "fitness.step", "fitness.training_done", "fitness.skill", "fitness.milestone",
    "mission.complete", "objective.tick", "maintenance.done", "grocery.check",
    "task.done", "meal.prep_done", "routine.log", "app.favorite",
})

# Apps the glasses don't show as cards: the orb *is* Home and Talk; the
# Apps manager, Settings and Files are for a bigger screen.
NOT_ON_GLASSES = frozenset({"web_home", "assistant", "module_browser", "settings", "files", "dashboard",
                            "maintenance", "property"})

# The glasses' order: Today, then the apps used most on the move, then
# the rest of MIA in its usual order.
FIRST = ("missions", "calendar", "kitchen", "workout", "budget", "garage", "real_estate", "greenhouse",
         "skills", "character")

# Short names for a 600 px card, where the app's own name is long.
SHORT_NAMES = {"dashboard": "Today", "relationships": "People", "real_estate": "Rentals"}

MAX_LINES = 5


def _line(text: str, detail: str = "", tone: str = "", action: Optional[dict] = None) -> dict:
    out = {"text": text, "detail": detail, "tone": tone}
    if action and action.get("kind") in GLASSES_KINDS:
        out["action"] = {"kind": action["kind"], "label": action.get("label") or "Do it",
                         "params": dict(action.get("params") or {})}
    return out


def _panel(title: str, lines: list[dict], empty: str, more: int = 0, limit: int = MAX_LINES) -> dict:
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
    return _panel("Today's Meal Plan", lines, "No meals planned today. Plan them in Kitchen → Week.")


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
    return _panel("Grocery List", lines, "The grocery list is empty.", limit=60)


def _kitchen_recipes(context, today):
    """Every recipe, to swipe through on the glasses: its picture, and its
    ingredients and steps once selected."""
    from core.web_screens import kitchen_page, recipe_steps

    recipes = [r for r in kitchen_page(context, today).get("recipes") or [] if not r.get("locked")]
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
        }
        lines.append(line)
    return _panel("Recipes", lines, "No recipes yet. Add them on your phone.", limit=60)


def _kitchen_pantry(context, today):
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
                                                       "params": {"step": s["index"] + 1}}))
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


# Past Due / Due Today / Due Soon (Zac, 2026-10-16): the one way the
# glasses sort everything with a date, in Missions, equipment and the calendar.
BUCKETS = (("past_due", "Past Due"), ("due_today", "Due Today"), ("due_soon", "Due Soon"))


def bucket_of(days: Optional[int], urgency: str = "") -> Optional[str]:
    from core.web_equipment import bucket_of as shared

    return shared(days, urgency)


def _bucketed(lines: list[dict], bucket: Optional[str]) -> list[dict]:
    return [line for line in lines if bucket is None or line.get("bucket") == bucket]


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
    if len(objectives) == 1 and (objectives[0].get("target") or 1) == 1 and not objectives[0].get("counts_itself"):
        action = {"kind": "objective.tick", "label": "Done",
                  "params": {"mission_id": m["id"], "index": objectives[0].get("index", 0), "amount": 1}}
    return _line(m.get("name") or "", progress, "", action)


def _missions_claim(context, today):
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


def _character_buffs(context, today):
    from core.buffs import buffs

    return _panel("Buffs", [_line(f"{b['icon']} {b['name']}", f"+{b['bonus']} {b['stat'].capitalize()} · {b['lasts']}", "ok")
                            for b in buffs(context, today)], "No buffs right now.")


def _character_chronicle(context, today):
    from core.chronicle import chronicle_page

    week = chronicle_page(context, today)["this_week"]
    return _panel(f"{week['title']}: {week['name']}", [_line(line) for line in week["story"]], "")


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


def _freedom(context, today):
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
    page = _freedom(context, today)
    if not page.get("available"):
        return _panel("Next Build", [], "Freedom is a grown-up's plan.")
    b = page.get("next_build")
    if not b:
        return _panel("Next Build", [], "No builds in the plan yet.")
    return _panel("Next Build", [_line(b["name"], f"{b['pct']}% · {b['left_text']} to go"),
                                 _line(f"{b['spent_text']} of {b['budget_text']}", "")], "")


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


def _task_lines(context, rows: list[dict], with_asset: bool = True) -> list[dict]:
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
    from core.web_equipment import equipment_page

    page = equipment_page(context, scope, today)
    seen, rows = set(), []
    for t in (page.get("attention") or []) + (page.get("next_up") or []):
        if t["id"] not in seen:
            seen.add(t["id"])
            rows.append(t)
    return page.get("assets") or [], rows


def _equipment(scope: str):
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


def _household_chores(context, today):
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
    return tuple(zip(("assets", "past_due", "due_today", "due_soon"),
                     ("Assets", "Past Due", "Due Today", "Due Soon"), builders))

Panel = Callable[[object, date], dict]

# Each app's quick action menu: (item id, label, panel builder).
PANELS: dict[str, tuple[tuple[str, str, Panel], ...]] = {
    "missions": (("pick", "Select Mission", _missions_pick), ("progress", "Log Progress", _missions_progress),
                 ("claim", "Ready To Claim", _missions_claim)),
    "kitchen": (("recipes", "Recipes", _kitchen_recipes), ("meals", "Today's Meal Plan", _kitchen_meals),
                ("pantry", "My Pantry", _kitchen_pantry), ("grocery", "Grocery List", _kitchen_grocery)),
    "workout": (("training", "Today's Training", _workout_training), ("practice", "Skill Practice", _workout_practice),
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
}

# Questions an app's menu hands MIA, as if said aloud (she answers with
# her tools), after its panels; for apps without a panel yet, the whole
# menu. Questions only, never an example command: selecting one must not
# make a note or start a trip.
ASKS: dict[str, tuple[str, ...]] = {
    "household": ("What did I get done this week?",),
    "workshop": ("What jobs are open?", "Which parts are running low?"),
    "power": ("How's the battery?", "How much power did I use today?"),
    "observations": ("What have you noticed lately?",),
    "notes": ("What were my last notes?",),
    "classroom": ("What should I study next?",),
    "inbox": ("Any emails I should answer?",),
    "expeditions": ("What's my next trip?", "What gear am I missing for it?"),
    "memories": ("What was my last trip like?",),
    "maps": ("Which trail maps do I have?",),
    "navigation": ("How far is my nearest waypoint?", "When is sunset today?"),
    "lab": ("What's my latest experiment reading?",),
    "field_kit": ("What devices are connected?",),
    "music": ("What's playing?",),
    "diagnostics": ("How is the computer doing?",),
}


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


def menu_for(app, pinned: Optional[bool] = None) -> list[dict]:
    """Pure logic. An app's quick action menu: its panels, then questions
    for MIA, at most five; then pin or unpin it for the glasses (its
    favorite star) when `pinned` is known."""
    items = [{"id": item, "label": label, "type": "panel"} for item, label, _ in PANELS.get(app.module_id, ())]
    items += [{"id": f"ask{i}", "label": say.rstrip("?.!"), "type": "ask", "say": say}
              for i, say in enumerate(ASKS.get(app.module_id, ()))]
    items = items[:5]
    if pinned is not None:
        items.append({"id": "pin", "label": "Unpin From Glasses" if pinned else "Pin To Glasses", "type": "action",
                      "action": {"kind": "app.favorite", "label": "Unpin" if pinned else "Pin",
                                 "params": {"module_id": app.module_id, "favorite": not pinned}}})
    return items


def glasses_apps(context, today: Optional[date] = None, mission_id: Optional[str] = None) -> dict:
    """The person's glasses cards: their pinned apps (favorites), then the
    rest behind "All apps". Each card has a status line and its menu."""
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
        return {
            "id": app.module_id, "name": SHORT_NAMES.get(app.module_id, app.name), "full_name": app.name,
            "tagline": app.tagline, "status": g.get("line") or "", "tone": g.get("tone") or "calm",
            "ask": app.ask, "pinned": app.module_id in pinned_ids,
            "menu": menu_for(app, None if app.module_id == "missions" else app.module_id in pinned_ids),
            **({"mission": mission_focus(context, today, mission_id)} if app.module_id == "missions" else {}),
        }

    pinned = [card(by_id[i]) for i in pinned_ids]
    others = [card(a) for a in apps if a.module_id not in pinned_ids]
    return {"as_of": today.isoformat(), "pinned": bool(pinned),
            "apps": pinned or others, "others": others if pinned else [],
            "hint": "" if pinned else "Star your favorite apps to pin them here.",
            "kinds": sorted(GLASSES_KINDS)}


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
    return None
