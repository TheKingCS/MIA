"""
core.show_off
===============

Show-off mode (DEC-0031): "MIA, show off for my friends" starts a short
narrated tour of what MIA can do, on the person's **real** profile, in
front of other people. So the tour is built here, in code, from a
filtered copy of the person's data, and the screens it shows are its own
cards, never the real screens:

- **Never shown:** money (debts, prices, profit, bills), the journal,
  memories, health (weight, food, sleep), and other people's details
  (names, birthdays). Debt bosses are left out; Chronicle lines about
  money, the journal, people and food are left out; buffs that would say
  either are left out; recipes show what they need and their steps, never
  a price.
- **Shown:** level and XP, skills, the six attributes, buffs, missions and
  mission bosses, gear condition, crafting recipes and finished builds
  (with their photos), the Reward Shop's credits (game currency, not
  money), and this week's Chronicle chapter, filtered.
- **No live Talk during the tour:** an answer could say anything, so the
  tour page hides it; the last card says what to ask afterwards.

The words are scripted (docs/design/MIA_VOICE.md), never written by a
model on the spot, so there's no waiting and nothing made up in front
of an audience. `wants_show_off()` is the spoken trigger.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

TRIGGER = re.compile(r"\b(show ?off|demo mode|show (my |our )?friends what you can do|show them what you can do)\b",
                     re.IGNORECASE)
INTRO = "Let's show them what I can do. Opening the tour."
HIDDEN_THREADS = {"money", "journal", "people", "eating"}  # the Chronicle's threads that stay private
HIDDEN_BUFFS = {"debt_slayer", "good_company", "well_fed", "clear_mind"}  # money, people, health, the journal


def wants_show_off(text: str) -> bool:
    """Pure logic. "MIA, show off for my friends" → True."""
    return bool(TRIGGER.search(text or ""))


def _step(key: str, title: str, say: str, **data) -> dict:
    return {"key": key, "title": title, "say": say, **data}


def _safely(fn, *args):
    try:
        return fn(*args)
    except Exception:
        log.debug("Show-off: %s failed", getattr(fn, "__name__", fn), exc_info=True)
        return None


def _level(context, today):
    from core.web_progress import character_page

    page = character_page(context, today)
    me = page.get("me") or {}
    first = (me.get("name") or "").split(" ")[0]
    level = me.get("level", 1)
    pct = round(100 * me.get("xp_into_level", 0) / me["xp_for_level"]) if me.get("xp_for_level") else 0
    hello = _step("hello", "Hi, I'm MIA",
                  "I'm a personal assistant that turns real life into a game. Everything you're about to see "
                  "comes from things that really happened, and none of it ever leaves this house.",
                  name=first)
    level_card = _step("level", f"Level {level}",
                       f"Every real thing done earns experience: workouts, missions, builds, upkeep. "
                       f"That's level {level}, {pct}% of the way to the next.",
                       level=level, percent=pct, total_xp=me.get("total_xp", 0),
                       top_skills=[{"name": s["name"], "icon": s["icon"], "level": s["level"]}
                                   for s in (page.get("top_skills") or [])[:3]])
    stats = [{"name": a["name"], "icon": a["icon"], "value": a["value"], "max": a["max"]}
             for a in page.get("attributes") or []]
    attrs = _step("stats", "Real Character Stats",
                  "Six stats, like a character sheet, made from what's really done. Training only goes up; "
                  "a quiet month never takes anything away.", stats=stats) if stats else None
    return [hello, level_card, attrs]


def _buffs(context, today):
    from core.buffs import buffs

    shown = [{"name": b["name"], "icon": b["icon"], "stat": b["stat"].capitalize()}
             for b in buffs(context, today) if b["key"] not in HIDDEN_BUFFS]
    if not shown:
        return None
    return _step("buffs", "Buffs", "Good streaks earn buffs, and each one lifts a stat. There are no debuffs, ever.",
                 buffs=shown)


def _missions(context, today):
    from core.boss_battles import bosses

    missions = getattr(context, "missions", None)
    active = []
    if missions is not None:
        for m in missions.all_missions():
            if m.status != "active" or not m.objectives:
                continue
            total = sum(max(1.0, float(o.target or 1)) for o in m.objectives)
            done = sum(min(max(1.0, float(o.target or 1)), float(o.progress or 0)) for o in m.objectives)
            active.append({"name": m.name, "icon": m.icon or "🎯", "percent": round(100 * done / total) if total else 0})
    boss = [b for b in bosses(context, today)["active"] if b["kind"] == "mission"][:1]  # never a debt
    if not active and not boss:
        return None
    return _step("missions", "Missions And Boss Fights",
                 "Goals become missions with objectives, and the big ones become boss fights with an HP bar.",
                 missions=sorted(active, key=lambda m: -m["percent"])[:3],
                 boss={"name": boss[0]["name"], "icon": boss[0]["icon"], "percent": boss[0]["percent"],
                       "phase": boss[0]["phase"]} if boss else None)


def _gear(context, today):
    from core.web_equipment import _task_row, condition

    maintenance = getattr(context, "maintenance", None)
    if maintenance is None:
        return None
    gear = []
    for asset in maintenance.all_assets():
        bar = condition([_task_row(context, t, asset, today) for t in maintenance.tasks_for_asset(asset.asset_id)])
        if bar is not None:
            gear.append({"name": asset.name, "percent": bar["percent"], "label": bar["label"], "tone": bar["tone"]})
    if not gear:
        return None
    return _step("gear", "Gear Like Equipment",
                 "The mower, the truck, the house: each has a condition bar that wears down as upkeep comes due "
                 "and fills back up when it's done.", gear=sorted(gear, key=lambda g: -g["percent"])[:4])


def _crafting(context, today):
    from core.web_craft import craft_section

    craft = craft_section(context)
    if not craft["recipes"] and not craft["builds"]:
        return None
    recipe = max(craft["recipes"], key=lambda r: r["built"], default=None)
    finished = [b for b in craft["builds"] if b["finished"]]
    photo = next(((b["id"], m["name"]) for b in finished for m in b["photos"] if m["kind"] == "image" and m["tag"] == "after"),
                 next(((b["id"], m["name"]) for b in finished for m in b["photos"] if m["kind"] == "image"), None))
    return _step("crafting", "Crafting Recipes",
                 "Things built in the workshop are saved like crafting recipes: what they need, the cuts, the steps. "
                 "I check what's on the shelf and make the shopping list for what's missing.",
                 recipe={"name": recipe["name"], "materials": len(recipe["rows"]), "steps": len(recipe["steps"]),
                         "ready": recipe["ready"]} if recipe else None,
                 recipes=len(craft["recipes"]), built=len(finished),
                 photo={"job_id": photo[0], "name": photo[1]} if photo else None)


def _shop(context, today):
    from core.game_layer import shop_page

    page = shop_page(context)
    if not page.get("available") or not page.get("rewards"):
        return None
    return _step("shop", "The Reward Shop",
                 "Credits earned from missions buy real rewards picked ahead of time. Spending never lowers the level.",
                 credits=page["credits"]["left"], rewards=[{"name": r["name"], "icon": r["icon"], "cost": r["cost"]}
                                                           for r in page["rewards"][:3]])


def _chronicle(context, today):
    from core.chronicle import _gather, tell, week_bounds

    monday, sunday = week_bounds(today)
    items = [i for i in _gather(context, monday, sunday) if i[1] not in HIDDEN_THREADS]
    told = tell(items)
    if not told["total"]:
        return None
    return _step("chronicle", "The Chronicle", "Every week I write the story of it, from what really happened.",
                 name=told["name"], story=told["story"][:4])


def tour(context, today: Optional[date] = None) -> dict:
    """The tour's cards, in order (empty ones left out)."""
    today = today or date.today()
    steps = list(_safely(_level, context, today) or [])
    for source in (_buffs, _missions, _gear, _crafting, _shop, _chronicle):
        steps.append(_safely(source, context, today))
    steps.append(_step("glasses", "On The Glasses",
                       "The same MIA shows up on smart glasses: missions, upkeep and recipes in the corner of your eye, "
                       "and the XP when something's done."))
    steps.append(_step("finale", "Ask Me Anything Later",
                       "That's the tour. Afterwards, try asking me what's next on a mission, how a build is going, "
                       "or to start a recipe. Thanks for watching!"))
    steps = [s for s in steps if s]
    return {"steps": steps, "count": len(steps)}
