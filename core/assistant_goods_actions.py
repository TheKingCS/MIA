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
Eggs over last week, this month or last month are counted from the flock's log (`eggs_between`).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _run(context, kind: str, params: dict) -> str:
    """An action kind, checked then run, as the screens do; its own
    words when it can't."""
    from core.actions import run_as_tool

    return run_as_tool(context, kind, params)


# ---------------------------------------------------------------- chickens


def _get_eggs(context, arguments: dict) -> str:
    """Tool get_eggs: for each flock, eggs today and this week, the lay rate from its hens, loose eggs, cartons on
    hand and feed cost a dozen, read from the Chickens page, and when they're laying far below their own normal, that
    with what to check (core/unusual.py), and how long the feed will last (core/feed_runway.py). Asked about last
    week or this month (his words, a follow-up's own first): those eggs from the log (`eggs_between`).
    """
    from core.web_flock import flock_page

    page = flock_page(context)
    if not page.get("available") or not page["flocks"]:
        return "No flock in MIA yet: add it under Apps → Chickens."
    own = str(arguments.get("question", "") or "").lower().split(" (after:")[0]
    span = _egg_span(own)
    if span is not None:
        return _eggs_in_span(context, span)
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
        parts.append(line + "." + (" " + f["unusual"] if f.get("unusual") else "")
                     + (" " + f["feed_runway"] if f.get("feed_runway") else ""))
    return " ".join(parts)


def _egg_span(words: str):
    """Pure logic. (label, first day back, last day back) for "last week" (7 to 13 days ago), "this month" or "last
    month" (by the calendar), else None."""
    from datetime import date, timedelta

    today = date.today()
    if "last week" in words:
        return "last week", today - timedelta(days=13), today - timedelta(days=7)
    if "this month" in words:
        return "so far this month", today.replace(day=1), today
    if "last month" in words:
        end = today.replace(day=1) - timedelta(days=1)
        return f"in {end:%B}", end.replace(day=1), end
    return None


def eggs_between(entries: list, flock_id: str, first, last) -> float:
    """Pure logic. Eggs one flock's log has collected between two dates, both counted."""
    return sum(float(e.count or 0) for e in entries if e.flock_id == flock_id and e.kind == "eggs"
               and first.isoformat() <= str(e.date)[:10] <= last.isoformat())


def _eggs_in_span(context, span) -> str:
    """Each flock's eggs over that span, from its log, with this week beside it for last week."""
    from datetime import date, timedelta

    label, first, last = span
    book = context.flock
    parts = []
    for f in book.flocks:
        entries = book.entries_for(f.flock_id)
        got = eggs_between(entries, f.flock_id, first, last)
        line = f"{f.name}: {got:g} eggs {label}"
        if label == "last week":
            week = eggs_between(entries, f.flock_id, date.today() - timedelta(days=6), date.today())
            line += f", against {week:g} this week"
        parts.append(line + ".")
    return " ".join(parts)


def _log_eggs(context, arguments: dict) -> str:
    """Tool log_eggs: proposes `flock.eggs` for the flock named (or the only one), asking which when it can't tell."""
    book = getattr(context, "flock", None)
    if book is None or not book.flocks:
        return "No flock in MIA yet: add it under Apps → Chickens."
    name = str(arguments.get("flock") or "").strip().lower()
    flock = next((f for f in book.flocks if name and name in f.name.lower()), book.flocks[0] if len(book.flocks) == 1 else None)
    if flock is None:
        return "Which flock? " + ", ".join(f.name for f in book.flocks)
    return _run(context, "flock.eggs", {"flock_id": flock.flock_id, "count": arguments.get("count")})


def _log_feed(context, arguments: dict) -> str:
    """Tool log_feed: proposes `flock.feed` (the pounds and what it cost, for the flock named or the only one), so
    feed bought counts toward the flock's feed runway and goes in the business's books (brainstorm round 14: "I spent
    $45 on feed" had been a Groceries expense the flock never knew of); asks which flock when it can't tell."""
    book = getattr(context, "flock", None)
    if book is None or not book.flocks:
        return "No flock in MIA yet: add it under Apps → Chickens. (Or say it as an expense, and I'll log the cost.)"
    name = str(arguments.get("flock") or "").strip().lower()
    flock = next((f for f in book.flocks if name and name in f.name.lower()), book.flocks[0] if len(book.flocks) == 1 else None)
    if flock is None:
        return "Which flock? " + ", ".join(f.name for f in book.flocks)
    params = {"flock_id": flock.flock_id, "pounds": arguments.get("pounds"), "cost": arguments.get("cost")}
    if arguments.get("date"):
        params["date"] = arguments.get("date")
    return _run(context, "flock.feed", params)


# ---------------------------------------------------------------- goods


def _recipe_named(context, name: str):
    """The Workshop recipe a spoken name means: an exact match first, else the one recipe whose name contains it
    (or is contained in it); None when there's no single answer.
    """
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
    """Tool list_goods_on_hand: each homestead good on hand, noting the ones to sell oldest first."""
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
    """Tool sell_goods: proposes `goods.sell` for the recipe named, with the quantity (1 by default) and a price only
    when they said one.
    """
    recipe = _recipe_named(context, str(arguments.get("item") or ""))
    if recipe is None:
        return "Which of your goods? Say it the way the recipe is named in the Workshop."
    params = {"recipe_id": recipe.recipe_id, "quantity": arguments.get("quantity") or 1}
    if arguments.get("amount"):
        params["amount"] = arguments.get("amount")
    return _run(context, "goods.sell", params)


# ---------------------------------------------------------------- freedom and deadlines


def _not_here(context, app: str) -> str:
    """Why a grown-up's page isn't there: a child's account, or the app's store missing on this MIA (the live sweep,
    2026-11-26: "what's overdue?" had "That's for a grown-up." for a missing store)."""
    from core.child_accounts import is_child

    try:
        if is_child(context):
            return "That's for a grown-up."
    except Exception:  # noqa: BLE001
        pass
    return f"{app} isn't kept on this MIA."


def _get_freedom(context, arguments: dict) -> str:
    """Tool get_freedom_progress: days to go and the date at their pace (or why there's no date yet, or that the
    fund is full), how much is saved of the goal, this week's total, and how much of a month the homestead covers.
    Grown-ups only; a missing store is said as that (`_not_here`).
    """
    from core.freedom import freedom_page

    page = freedom_page(context)
    if not page.get("available"):
        return _not_here(context, "Freedom")
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
    """Tool get_deadlines: overdue obligations, then the ones due soon (noting the unverified), or the next two
    when nothing is due in 30 days, and how many are still to verify. Grown-ups only; a missing store is said as that
    (`_not_here`).
    """
    from core.web_compliance import compliance_page

    page = compliance_page(context)
    if not page.get("available"):
        return _not_here(context, "Compliance")
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


def _action_start_hatch(context, arguments: dict) -> str:
    """Tool start_hatch: eggs set in the incubator (hatch.start, core/hatch_tracker.py): a mission with the bird's
    dated candling, lockdown and hatch-day steps; the day set read looking back ("yesterday", "Sunday"), and always
    named, so a card approved later keeps it."""
    from core import hatch_tracker
    from core.assistant_correction_actions import _run

    when = hatch_tracker.set_day(str(arguments.get("set") or "today"))
    if when is None:
        return "Which day were they set?"
    params = {"bird": str(arguments.get("bird") or "chicken"), "eggs": arguments.get("eggs"), "set": when}
    return _run(context, "hatch.start", params)


def _action_feed_mix(context, arguments: dict) -> str:
    """Tool feed_mix: two feeds mixed to a target protein, the Pearson square (core/feed_mix.say), worked out in code."""
    from core import feed_mix

    return feed_mix.say(str(arguments.get("question") or ""))


def _action_start_broilers(context, arguments: dict) -> str:
    """Tool start_broilers: a batch of meat birds (broilers.start, core/broiler_batch.py): a mission dated from the
    day they came to processing day, with the feed they'll eat; the day read looking back."""
    from core import hatch_tracker
    from core.assistant_correction_actions import _run

    when = hatch_tracker.set_day(str(arguments.get("started") or "today"))
    if when is None:
        return "Which day did they come?"
    return _run(context, "broilers.start", {"breed": str(arguments.get("breed") or "cornish cross"),
                                            "birds": arguments.get("birds"), "started": when})


def _action_broilers_status(context, arguments: dict) -> str:
    """Tool broilers_status: each batch's week, what's next and the processing day (core/broiler_batch.say)."""
    from core import broiler_batch

    return broiler_batch.say(context)


def _action_hatch_status(context, arguments: dict) -> str:
    """Tool hatch_status: what day each hatch is on and what's next (core/hatch_tracker.say)."""
    from core import hatch_tracker

    return hatch_tracker.say(context)


def register_goods_actions(registry: AssistantActionRegistry) -> None:
    """Registers the flock, goods, freedom and compliance tools: get_eggs, log_eggs, list_goods_on_hand,
    sell_goods, get_freedom_progress (never by "how far along", a project's) and get_deadlines (never "what's overdue?"
    alone, his whole list's: core/today.overdue_said); get_eggs is also reached by asking about the feed ("how long
    will the feed last?": its answer says how long the feed lasts, core/feed_runway.py) and what the eggs cost ("do the
    eggs pay for themselves?": its answer has the feed cost a dozen). Also start_hatch and hatch_status: eggs in the incubator as a
    mission with dated steps (core/hatch_tracker.py), start_broilers and broilers_status (a batch of meat birds to
    processing day, core/broiler_batch.py; the start tool hears only a batch that came, "got 25 broiler chicks"), and feed_mix (two feeds to a target protein, core/feed_mix.py, reached by "16% layer", "32% supplement" and the
    like), hatch_status heard only of eggs ("how's the hatch going?",
    never "the business incubator" or "the lockdown drill").
    get_eggs takes his words (its prompt_arg, still answered in code) for last week, this month or last month.
    feed_mix takes his own words (`prompt_arg`).
    And log_feed: feed bought, to the flock's log and the books.
    """
    none = {"type": "object", "properties": {}, "required": []}
    registry.register(AssistantAction(
        name="start_hatch", domain="flock",
        description="Eggs set in the incubator: a mission with the dated candling, lockdown and hatch-day steps "
                    "for that bird (chicken 21 days, duck and turkey 28, goose 30, guinea 27, quail 17).",
        parameters={"type": "object", "properties": {
            "bird": {"type": "string", "description": "chicken, duck, turkey, goose, guinea or quail"},
            "eggs": {"type": "number", "description": "how many eggs"},
            "set": {"type": "string", "description": "the day set, if not today"}}, "required": ["eggs"]},
        handler=_action_start_hatch,
        trigger_phrases=("in the incubator", "set some eggs", "set eggs", "eggs to hatch", "started incubating",
                         "start a hatch"),
    ))
    registry.register(AssistantAction(
        name="start_broilers", domain="flock",
        description="A batch of meat birds came: a mission dated to processing day (Cornish cross about 8 weeks, "
                    "rangers about 11, heritage 16), with the feed the batch will eat.",
        parameters={"type": "object", "properties": {
            "breed": {"type": "string", "description": "cornish cross, red ranger, freedom ranger or heritage"},
            "birds": {"type": "number", "description": "how many"},
            "started": {"type": "string", "description": "the day they came, if not today"}}, "required": ["birds"]},
        handler=_action_start_broilers,
        trigger_phrases=("got meat birds", "meat bird chicks", "cornish cross chicks", "cornish rock chicks",
                         "broiler chicks", "got broilers", "freedom ranger chicks", "red ranger chicks"),
    ))
    registry.register(AssistantAction(
        name="broilers_status", domain="flock",
        description="How each batch of meat birds is coming: its week, what's next and the processing day.",
        parameters=none, handler=_action_broilers_status,
        trigger_phrases=("meat birds coming", "how are the broilers", "processing day", "when do i process",
                         "when to butcher", "butcher the chickens"),
    ))
    registry.register(AssistantAction(
        name="feed_mix", domain="knowledge",  # a calculator, not a record she keeps: "how do I mix..." is the world's
        description="How to mix two feeds to reach a target protein (the Pearson square): parts, shares and a batch's "
                    "pounds of each, worked out in code.",
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "Their words, with both feeds' percent and the target."}},
            "required": ["question"]},
        handler=_action_feed_mix, prompt_arg="question",  # his own words, never the model's (live check 2026-11-25: it sent the tool's description)
        trigger_phrases=("mix feed", "mix the feed", "feed mix", "pearson square", "protein feed", "% protein",
                         "percent protein", "mix two feeds", "% feed", "% layer", "% grower", "% starter",
                         "% supplement", "% pellet", "% crumble", "% ration", "percent feed", "percent layer",
                         "percent supplement", "percent grower"),
    ))
    registry.register(AssistantAction(
        name="hatch_status", domain="flock",
        description="How each hatch in the incubator is going: what day it is and what's next.",
        parameters=none, handler=_action_hatch_status,
        trigger_phrases=(" the hatch ", " the hatch?", "hatch going", "hatch status", "eggs in the incubator",
                         "incubator eggs", "lockdown day", "candle the eggs", "when do they hatch", "when will they hatch"),
    ))
    registry.register(AssistantAction(
        name="get_eggs", domain="flock",
        description="The chickens: eggs today and this week (or last week, this month, last month), lay rate, loose "
                    "eggs, cartons on hand, feed cost per dozen.",
        parameters={"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                    "required": []},
        handler=_get_eggs, prompt_arg="question",  # still answered in code, his words as the question
        trigger_phrases=("how many eggs", "eggs this week", "eggs today", "lay rate", "are the hens laying",
                         "how are the chickens", "how are the hens", "egg count", "feed last", "chicken feed",
                         "more feed", "out of feed", "eggs pay for", "eggs cost me", "cost per dozen", "cost a dozen",
                         "chickens cost me", "hens cost me", "feed cost"),
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
        name="log_feed", domain="flock",
        description="Log feed bought for the flock (pounds and what it cost): it counts toward how long the feed "
                    "lasts and goes in the business's books. Use this, not add_expense, for chicken or layer feed.",
        parameters={"type": "object", "properties": {
            "pounds": {"type": "number", "description": "How many pounds (a 50 lb bag is 50)."},
            "cost": {"type": "number", "description": "What it cost, if he said."},
            "flock": {"type": "string", "description": "Which flock, only if there are several."}},
            "required": []},
        handler=_log_feed,
        trigger_phrases=("bought feed", "bought layer feed", "bought chicken feed", "lb of feed", "pounds of feed",
                         "bag of feed", "bags of feed", "lb of layer feed", "lbs of feed", "spent on feed",
                         "on chicken feed", "on layer feed", "picked up feed"),
        subjects=("feed",),
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
                         "out of this job"),
        subjects=("freedom", "quit", "leave", "saved", "progress", "home", "job", "factory"),
    ))
    registry.register(AssistantAction(
        name="get_deadlines", domain="compliance",
        description="Tax and compliance deadlines: overdue, the next 30 days, what's still to verify.",
        parameters=none, handler=_get_deadlines,
        # never "what's overdue?" alone: that's his whole day's (core/today.overdue_said, the live sweep 2026-11-26)
        trigger_phrases=("due for taxes", "tax deadline", "deadlines", "permit", "licence", "license", "estimated tax",
                         "compliance", "taxes due"),
        subjects=("tax", "deadline", "permit", "licence", "license", "compliance"),
    ))
