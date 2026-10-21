"""
core.assistant_goods_actions
==============================

Saying it to MIA (2026-10-21): the homestead's newest screens by voice.
"How many eggs this week?", "I collected 9 eggs", "What goods do I have
on hand?", "Sold 3 loaves of banana bread", "How close am I to freedom?",
"What's due for taxes?". Each one runs the same code its screen does
(the action kinds in core/flock_actions.py, core/goods_actions.py; the
pages in core/web_flock.py, core/freedom.py, core/web_compliance.py), so
the numbers match and "undo that" takes a change back.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _run(context, kind: str, params: dict) -> str:
    """An action kind, checked then run, as the screens do; its own
    words when it can't."""
    from core.actions import ACTION_TYPES, ActionError

    action = ACTION_TYPES[kind]
    try:
        action.describe(context, params)
        return action.execute(context, params)
    except (ActionError, ValueError) as problem:
        return str(problem)


# ---------------------------------------------------------------- chickens


def _get_eggs(context, arguments: dict) -> str:
    from core.web_flock import flock_page

    page = flock_page(context)
    if not page.get("available") or not page["flocks"]:
        return "No flock in MIA yet: add it under Apps → Chickens."
    parts = []
    for f in page["flocks"]:
        x = f["figures"]
        line = f"{f['name']}: {x['today']:g} eggs today, {x['week']:g} this week"
        if x["lay_rate_text"]:
            line += f" ({x['lay_rate_text']} lay rate from {f['hens']} hens)"
        line += f", {x['loose']:g} loose"
        if f["good"]:
            line += f", {f['good']['on_hand_text']} of {f['good']['name']} in cartons"
        if x["feed_per_dozen_text"]:
            line += f"; feed costs {x['feed_per_dozen_text']} a dozen"
        parts.append(line + ".")
    return " ".join(parts)


def _log_eggs(context, arguments: dict) -> str:
    book = getattr(context, "flock", None)
    if book is None or not book.flocks:
        return "No flock in MIA yet: add it under Apps → Chickens."
    name = str(arguments.get("flock") or "").strip().lower()
    flock = next((f for f in book.flocks if name and name in f.name.lower()), book.flocks[0] if len(book.flocks) == 1 else None)
    if flock is None:
        return "Which flock? " + ", ".join(f.name for f in book.flocks)
    return _run(context, "flock.eggs", {"flock_id": flock.flock_id, "count": arguments.get("count")})


# ---------------------------------------------------------------- goods


def _recipe_named(context, name: str):
    from core.craft_recipes import key

    book = getattr(context, "craft_recipes", None)
    if book is None:
        return None
    wanted = key(name)
    recipes = book.all_recipes()
    exact = next((r for r in recipes if key(r.name) == wanted), None)
    if exact is not None:
        return exact
    close = [r for r in recipes if wanted and (wanted in key(r.name) or key(r.name) in wanted)]
    return close[0] if len(close) == 1 else None


def _get_goods(context, arguments: dict) -> str:
    from core.web_craft import goods_section

    goods = [g for g in goods_section(context)["goods"] if g["on_hand"]]
    if not goods:
        return "No homestead goods on hand right now."
    parts = []
    for g in goods:
        line = f"{g['on_hand_text']} of {g['name']}"
        if g["sell_first"]:
            line += " (sell the oldest first)"
        parts.append(line)
    return "On hand: " + "; ".join(parts) + "."


def _sell_goods(context, arguments: dict) -> str:
    recipe = _recipe_named(context, str(arguments.get("item") or ""))
    if recipe is None:
        return "Which of your goods? Say it the way the recipe is named in the Workshop."
    params = {"recipe_id": recipe.recipe_id, "quantity": arguments.get("quantity") or 1}
    if arguments.get("amount"):
        params["amount"] = arguments.get("amount")
    return _run(context, "goods.sell", params)


# ---------------------------------------------------------------- freedom and deadlines


def _get_freedom(context, arguments: dict) -> str:
    from core.freedom import freedom_page

    page = freedom_page(context)
    if not page.get("available"):
        return "That's for a grown-up."
    p, t = page["plan"], page["plan"]["text"]
    if p["ready"]:
        lead = "The freedom fund is full: you're there."
    elif p["days"] is not None:
        lead = f"About {p['days']:,} days to go, around {p['date'][:7]}, at your pace of {t['pace']} a month."
    else:
        lead = p["why_no_date"]
    week = next((x for x in page["periods"] if x["id"] == "week"), None)
    progress = (f" You've saved {t['saved']} of {t['goal']}" + (f" ({p['progress_pct']:g}%)" if p["progress_pct"] is not None
                                                                 else "") + ".") if p["goal"] else ""
    tail = f" This week: {week['total_text']}." if week else ""
    cover = f" The homestead covers {p['covered_pct']}% of a month." if p["covered_pct"] is not None else ""
    return lead + progress + tail + cover


def _get_deadlines(context, arguments: dict) -> str:
    from core.web_compliance import compliance_page

    page = compliance_page(context)
    if not page.get("available"):
        return "That's for a grown-up."
    g = page["groups"]
    if not page["counts"]["open"]:
        return "Nothing on your Compliance list yet. Apps → Compliance → Things To Check offers the usual ones to verify."
    said = []
    for c in g["overdue"]:
        said.append(f"OVERDUE: {c['title']} (due {c['due']})")
    for c in g["soon"]:
        said.append(f"{c['title']} in {c['days']} days ({c['due']})" + ("" if c["verified"] else ", not verified yet"))
    if not said:
        nxt = (g["later"] or g["check"])[:2]
        said = [f"{c['title']}" + (f" on {c['due']}" if c["due"] else "") for c in nxt]
        lead = "Nothing due in the next 30 days. Next: "
    else:
        lead = ""
    unverified = page["counts"]["unverified"]
    tail = f" {unverified} still to verify." if unverified else ""
    return lead + "; ".join(said) + "." + tail


def register_goods_actions(registry: AssistantActionRegistry) -> None:
    none = {"type": "object", "properties": {}, "required": []}
    registry.register(AssistantAction(
        name="get_eggs", domain="flock",
        description="The chickens: eggs today and this week, lay rate, loose eggs, cartons on hand, feed cost per dozen.",
        parameters=none, handler=_get_eggs,
        trigger_phrases=("how many eggs", "eggs this week", "eggs today", "lay rate", "are the hens laying",
                         "how are the chickens", "how are the hens", "egg count"),
        subjects=("egg", "hen", "chicken", "flock"),
    ))
    registry.register(AssistantAction(
        name="log_eggs", domain="flock",
        description="Log eggs collected today from the flock.",
        parameters={"type": "object", "properties": {
            "count": {"type": "integer", "description": "How many eggs."},
            "flock": {"type": "string", "description": "Which flock, only if there are several."}},
            "required": ["count"]},
        handler=_log_eggs,
        trigger_phrases=("collected", "gathered", "got eggs", "log eggs", "eggs from the coop", "picked up eggs"),
        subjects=("egg",),
    ))
    registry.register(AssistantAction(
        name="list_goods_on_hand", domain="goods",
        description="Homestead goods made and not sold yet (bread, honey, eggs in cartons, jars), and what to sell first.",
        parameters=none, handler=_get_goods,
        trigger_phrases=("goods on hand", "what goods", "what do i have to sell", "what's left to sell",
                         "whats left to sell", "what should i sell first", "how much banana bread",
                         "how many jars", "how many loaves"),
        subjects=("good", "sell", "bread", "honey", "jar", "loave", "loaf"),
    ))
    registry.register(AssistantAction(
        name="sell_goods", domain="goods",
        description=("Record a sale of homestead goods made in batches (a Workshop recipe like banana bread, honey, "
                     "eggs, cookies): the oldest batch first, during the open market day if there is one."),
        parameters={"type": "object", "properties": {
            "item": {"type": "string", "description": "The good, as its recipe is named (\"banana bread\")."},
            "quantity": {"type": "number", "description": "How many (in the recipe's unit: loaves, jars, dozen)."},
            "amount": {"type": "number", "description": "What they sold for in all, only if not the usual price."}},
            "required": ["item"]},
        handler=_sell_goods,
        trigger_phrases=("sold", "i sold", "sold some", "sale of"),
        subjects=("bread", "honey", "egg", "jar", "loaf", "loave", "cookie", "dozen"),
    ))
    registry.register(AssistantAction(
        name="get_freedom_progress", domain="freedom",
        description="The freedom plan: days to go, the estimated month, saved of the fund, this week, how much of a month the homestead covers.",
        parameters=none, handler=_get_freedom,
        trigger_phrases=("how close am i", "freedom fund", "freedom plan", "when can i quit", "when can i leave",
                         "work from home", "how much have i saved", "freedom progress", "out of the factory",
                         "out of this job", "how far along"),
        subjects=("freedom", "quit", "leave", "saved", "progress", "home", "job", "factory"),
    ))
    registry.register(AssistantAction(
        name="get_deadlines", domain="compliance",
        description="Tax and compliance deadlines: overdue, the next 30 days, what's still to verify.",
        parameters=none, handler=_get_deadlines,
        trigger_phrases=("due for taxes", "tax deadline", "deadlines", "what's overdue", "whats overdue",
                         "permit", "licence", "license", "estimated tax", "compliance", "taxes due"),
        subjects=("tax", "deadline", "overdue", "permit", "licence", "license", "compliance", "due"),
    ))
