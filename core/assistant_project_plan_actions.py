"""
core.assistant_project_plan_actions
=====================================

Plans made together, by voice (core/project_plans.py, T-0060): "let's plan a 4 by 8 raised bed", "plan my garden:
tomatoes and peppers in bed one", "make it 10 by 12", "leave out the materials stage", "confirm the plan". Drafting
and changing a draft write only the draft (undoable); confirming makes the project and its missions, so it's a card
for his yes, the same as the Planner page's Confirm (DEC-0125).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction

DOMAIN = "project_plans"


def _card(kind: str):
    """A handler that puts up a card for one of the plan actions with the arguments as its params."""
    def handler(context, arguments: dict) -> str:
        """Proposes it; says the card's sentence or why it can't be done."""
        from core.actions import ActionError

        actions = getattr(context, "actions", None)
        if actions is None:
            return "I can't put that to you from here: it's on the Planner page."
        try:
            card = actions.propose(context, kind, {k: v for k, v in (arguments or {}).items() if v not in ("", None)})
        except ActionError as problem:
            return str(problem)
        return f"{card.summary}. It's waiting for your yes: press Approve, or say \"approve it\"."
    return handler


def _do(kind: str, **fixed):
    """A handler that does a draft's action at once (drafts only; undoable), saying what happened; `fixed` params
    are added (a draft she starts says so: made_by)."""
    def handler(context, arguments: dict) -> str:
        """Runs it through the action contract, as the person."""
        from core.actions import ActionError

        actions = getattr(context, "actions", None)
        if actions is None:
            return "I can't do that from here: it's on the Planner page."
        params = {**{k: v for k, v in (arguments or {}).items() if v not in ("", None)}, **fixed}
        try:
            done = actions.approve(context, actions.propose(context, kind, params, proposed_by="mia").proposal_id)
        except ActionError as problem:
            return str(problem)
        if done.status != "executed":
            return done.result or "That didn't work; nothing was changed."
        return f"{done.result} (Say “undo that” to take it back.)"
    return handler


def _show(context, arguments: dict) -> str:
    """The plans in progress (or one), each with its stages and steps, for her to read out or talk through."""
    book = getattr(context, "project_plans", None)
    if book is None:
        return "Plans aren't here."
    plans = [book.get(arguments.get("plan_id"))] if arguments.get("plan_id") else book.listed()[:3]
    plans = [p for p in plans if p is not None]
    if not plans:
        return "No plans yet. Say \"let's plan\" and what: a build from the Library, or a garden."
    out = []
    for plan in plans:
        out.append(f"{plan.title} ({plan.kind}, {plan.status}, id {plan.plan_id}):")
        for stage in plan.stages:
            out.append(f"- {stage['name']}: " + "; ".join(s["do"] for s in stage["steps"][:6])
                       + (" ..." if len(stage["steps"]) > 6 else ""))
        out += [f"Note: {w}" for w in plan.warnings[:4]]
    return "\n".join(out)


_BED = {"type": "object", "properties": {"name": {"type": "string"}, "length_ft": {"type": "number"},
        "width_ft": {"type": "number"}, "depth_in": {"type": "number"}}}
_CROP = {"type": "object", "properties": {"crop": {"type": "string"}, "bed": {"type": "string"},
         "sqft": {"type": "number"}}}
_PLAN = {"type": "object", "properties": {
    "kind": {"type": "string", "description": "build or garden"},
    "shelf_plan": {"type": "string", "description": "a Library plan's id for a build (find_plans lists them)"},
    "sizes": {"type": "object", "description": "the plan's sizes, e.g. {\"length_ft\": 8, \"width_ft\": 4}"},
    "job": {"type": "string", "description": "a Trade Master job's id, instead of a plan"},
    "beds": {"type": "array", "items": _BED, "description": "a garden's beds"},
    "crops": {"type": "array", "items": _CROP, "description": "a garden's crops and their beds"},
    "last_frost": {"type": "string", "description": "his average last spring frost, e.g. 'April 20'"},
    "first_frost": {"type": "string", "description": "his average first fall frost"},
    "title": {"type": "string"}}}


def _garden_week(context, arguments: dict) -> str:
    """This week in the garden (core/garden_week.say)."""
    from core import garden_week

    return garden_week.say(context)


def _year(context, arguments: dict) -> str:
    """The homestead's year ahead (core/homestead_year.say)."""
    from core import homestead_year

    return homestead_year.say(context)


def _price(context, arguments: dict) -> str:
    """What a build costs and what to charge (core/plan_price.say)."""
    from core import plan_price

    try:
        hours = float(arguments.get("hours") or 0)
        margin = float(arguments["margin"]) if arguments.get("margin") not in (None, "") else None
    except (TypeError, ValueError):
        return "Hours and margin are numbers: like 12 hours and a 20% margin."
    return plan_price.say(context, str(arguments.get("plan") or ""), hours, margin)


def _seed_life(context, arguments: dict) -> str:
    """Tool seed_viability: how long that kind of seed keeps, and his dated packets of it (core/seed_life.say)."""
    from core import seed_life

    return seed_life.say(context, str(arguments.get("seeds") or ""))


def _what_to_plant(context, arguments: dict) -> str:
    """Tool what_to_plant: with a crop, when to plant it; without, what's due to plant now, from his last frost
    (core/planting_now.py)."""
    from core import planting_now

    crop = str(arguments.get("crop") or "").strip()
    return planting_now.say_crop(context, crop) if crop else planting_now.say_now(context)


def _picture(context, arguments: dict) -> str:
    """Tool project_picture: what a project he's planning touches (core/project_ripple.py, through the question
    plan "project picture"), in plain words; the model phrases the sheet when the plan reaches it first."""
    from core import question_plans as qp

    said = str(arguments.get("project") or "").strip()
    sheet = qp.gather(context, qp.PLAN_BY_NAME["project picture"], f"planning to build {said}" if said else "")
    return sheet.plain()


def _buildable(context, arguments: dict) -> str:
    """Tool what_can_i_build: the Library's builds closest to done from his workshop's stock (core/buildable.say)."""
    from core import buildable

    return buildable.say(context)


def _print_part(context, arguments: dict) -> str:
    """Tool design_print_part: an enclosure or a spacer as STL files from his sizes (core/print_parts.make).
    With mounting posts at a board's hole spacing and a cable hole when he asks for them."""
    from core import print_parts

    try:
        wall = float(arguments["wall_mm"]) if arguments.get("wall_mm") not in (None, "") else None
    except (TypeError, ValueError):
        wall = None
    return print_parts.make(context, str(arguments.get("kind") or "enclosure"), str(arguments.get("sizes") or ""),
                            str(arguments.get("name") or ""), wall, str(arguments.get("posts") or ""),
                            str(arguments.get("cable_hole") or "").lower() in ("1", "true", "yes"))


def _orchard_month(context, arguments: dict) -> str:
    """Tool orchard_this_month: the orchard's jobs in the next 30 days from his frost date (core/orchard.say_month)."""
    from core import orchard

    return orchard.say_month(context)


def _fruit_facts(context, arguments: dict) -> str:
    """Tool fruit_tree_facts: one fruit's chill hours, bearing, pollination, spacing, pruning and ripening
    (core/orchard.say_kind)."""
    from core import orchard

    return orchard.say_kind(str(arguments.get("fruit") or ""))


def _water_budget(context, arguments: dict) -> str:
    """Tool water_budget: the whole property's water a day and a month, what's stored and caught
    (core/water_budget.say)."""
    from core import water_budget

    return water_budget.say(context)


def _water_level(context, arguments: dict) -> str:
    """Tool log_water_level: a tank or cistern's level as he said it (core/water_budget.log_level)."""
    from core import water_budget

    return water_budget.log_level(context, str(arguments.get("tank") or ""), arguments.get("gallons"))


def _catchment(context, arguments: dict) -> str:
    """Tool rain_catchment: a roof's gallons from rain, his logged rain and his beds' needs (core/rain_catchment)."""
    from core import rain_catchment

    try:
        beds = float(arguments["beds_sqft"]) if arguments.get("beds_sqft") not in (None, "") else None
    except (TypeError, ValueError):
        beds = None
    return rain_catchment.say(context, str(arguments.get("roof") or ""), beds)


def _log_harvest(context, arguments: dict) -> str:
    """Tool log_harvest: a harvest kept on his grow lab batch of that crop, with when it was planted for a crop not
    there yet (core/harvest_log.log)."""
    from core import harvest_log

    return harvest_log.log(context, str(arguments.get("crop") or ""), arguments.get("amount"),
                           str(arguments.get("unit") or ""), str(arguments.get("where") or ""),
                           str(arguments.get("last") or "").lower() in ("1", "true", "yes"),
                           str(arguments.get("planted") or ""))


def _harvest_year(context, arguments: dict) -> str:
    """Tool harvest_this_year: this year's harvests and what they'd have cost (core/harvest_log.say_year)."""
    from core import harvest_log

    return harvest_log.say_year(context)


def register_project_plan_actions(registry) -> None:
    """Registers plan_with_me, change_plan (a draft's sizes, beds, crops, frosts, stages and notes; its build is
    chosen when drafted), design_print_part (an enclosure or spacer as STL files, core/print_parts.py), water_budget
    and log_water_level (the property's water, core/water_budget.py),
    orchard_this_month and fruit_tree_facts (the orchard, core/orchard.py), rain_catchment (a
    roof's gallons, core/rain_catchment.py), log_harvest and
    harvest_this_year (harvests by voice and what the garden produced,
    core/harvest_log.py; reached by "harvested" and the garden's words, never a bare "harvest" or "dug up"),
    what_can_i_build (the builds closest to done from his stock, core/buildable.py; reached by
    "build with what I have" or his lumber, never a bare "what could I build", which is often about something else),
    project_picture (what a project touches, core/project_ripple.py; reached by planning words,
    never by "want to build a", which is the material list's), price_build
    (core/plan_price.py), homestead_year (core/homestead_year.py), garden_this_week (core/garden_week.py),
    show_plans,
    confirm_plan and drop_plan, seed_viability (how long his seeds keep, core/seed_life.py) and what_to_plant (what's
    due to plant now, or one crop's dates, core/planting_now.py; for crops not in a confirmed plan). Their trigger
    phrases cover the everyday ways he'd ask ("what should I plant this
    week", "what needs doing in the garden", "how much should I charge for a picnic table":
    tests/test_everyday_phrasing_routing.py).
    The water tools are reached by water tanks and the cistern, never a bare "tank is at" (a propane tank) or
    "enough water" (a fish tank); the orchard's by its fruit, never "when should I prune" alone (roses) or "when
    will my" (a package).
    design_print_part takes a board's mounting-hole spacing for posts and a cable hole.
    design_print_part is never reached by "print me a" (an invoice) or a bare "a standoff"."""
    registry.register_domain_keywords(DOMAIN, ("plan my garden", "garden plan", "plan the build", "let's plan",
                                               "plan a", "the plan", "confirm the plan", "planting"))
    registry.register(AssistantAction(
        name="plan_with_me", domain=DOMAIN,
        description="Draft a plan with him: a build (a Library plan at his size, walked by Trade Master) or a "
                    "garden (beds, crops and his frost dates). Only a draft: he changes it, then confirms.",
        parameters=_PLAN, handler=_do("projectplan.draft", made_by="mia"),
        trigger_phrases=("let's plan", "plan my garden", "plan a garden", "plan the build", "help me plan"),
    ))
    changed = dict(_PLAN["properties"], plan_id={"type": "string"}, leave_out={"type": "string"},
                   put_back={"type": "string"}, notes={"type": "string"})
    for unused in ("kind", "shelf_plan", "job"):  # a draft's build is chosen when it's drafted
        changed.pop(unused)
    registry.register(AssistantAction(
        name="change_plan", domain=DOMAIN,
        description="Change a draft plan: its size, beds, crops, frost dates, a stage left out or put back, notes.",
        parameters={"type": "object", "properties": changed, "required": ["plan_id"]},
        handler=_do("projectplan.change"), trigger_phrases=("change the plan", "make it", "leave out the"),
    ))
    registry.register(AssistantAction(
        name="project_picture", domain=DOMAIN,
        description="Everything a project he's planning touches, from his records: the build's materials and cost "
                    "against what's on hand, his money and freedom date, garden plans, water, power, the flock, his "
                    "time, goals and research. Plans nothing.",
        parameters={"type": "object", "properties": {
            "project": {"type": "string", "description": "the project, e.g. 'a greenhouse'"}}, "required": ["project"]},
        handler=_picture, trigger_phrases=("planning to build", "thinking about building", "planning to put up",
                                           "thinking about putting up", "planning a greenhouse", "affect everything", "mean for everything",
                                           "what does it touch", "what would it take to build"),
    ))
    registry.register_domain_keywords("printing", ("3d print", "3d printer", "stl", "print a part"))
    registry.register(AssistantAction(
        name="design_print_part", domain="printing",
        description="Make a part to 3D print as STL files, from the inside size he gives: an enclosure (open box and "
                    "its lid, for a sensor board, relay or battery) or a spacer (round standoff). Says the outside size "
                    "and the most plastic; he slices and prints it himself.",
        parameters={"type": "object", "properties": {
            "kind": {"type": "string", "description": "enclosure or spacer"},
            "sizes": {"type": "string", "description": "the sizes as he said them, e.g. '80 by 50 by 30 mm'"},
            "name": {"type": "string", "description": "what it's for, e.g. 'soil sensor box' (optional)"},
            "wall_mm": {"type": "number", "description": "wall thickness in mm, if he said (2 by default)"},
            "posts": {"type": "string", "description": "a board's mounting-hole spacing, e.g. '58 by 23', if he said"},
            "cable_hole": {"type": "boolean", "description": "true for a hole for a cable or wires"}},
            "required": ["kind", "sizes"]},
        handler=_print_part,
        trigger_phrases=("3d print", "print an enclosure", "make me an enclosure", "design an enclosure",
                         "an enclosure for", "print a spacer", "make a spacer", "print a standoff",
                         "make a standoff"),
    ))
    registry.register_domain_keywords("water", ("cistern", "water tank", "rain barrels", "water budget", "well water"))
    registry.register(AssistantAction(
        name="water_budget", domain="water",
        description="The whole property's water: what the house, garden, orchard and flock use a day and a month, "
                    "what his tanks and cistern hold (their latest levels), what the roof caught, and how many days "
                    "the stored water lasts. Use this, never the offline library, for his own water: how much he "
                    "uses, has or how long it lasts.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_water_budget,
        trigger_phrases=("water budget", "how much water do i use", "how much water do we use", "water do i have",
                         "how long will my water last", "how long will the water last", "do i have enough water",
                         "enough water stored", "enough water for the", "my water usage", "our water usage",
                         "water use on the"),
        subjects=("water",),  # so "how long will my water last?" is answered in code (direct_lookup)
    ))
    registry.register(AssistantAction(
        name="log_water_level", domain="water",
        description="Log a tank, cistern or barrel's level in gallons, as he said it. Undoable.",
        parameters={"type": "object", "properties": {
            "tank": {"type": "string", "description": "which tank, e.g. 'cistern'"},
            "gallons": {"type": "number", "description": "how many gallons are in it"}}, "required": ["tank", "gallons"]},
        handler=_water_level, trigger_phrases=("cistern is at", "water tank is at", "barrel is at", "cistern has",
                                               "water tank has", "gallons in the cistern", "gallons in the water tank"),
    ))
    registry.register_domain_keywords("orchard", ("orchard", "fruit trees", "fruit tree"))
    registry.register(AssistantAction(
        name="orchard_this_month", domain="orchard",
        description="What his orchard needs in the next 30 days (pruning, dormant oil, bloom and frost watch, "
                    "thinning, harvest, fall cleanup), dated from his frost date for the fruit trees in his records, "
                    "and any that lack a pollination partner.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_orchard_month,
        trigger_phrases=("the orchard", "my orchard", "fruit trees need", "prune the apple", "prune my apple",
                         "prune the peach", "prune the pear", "prune the plum", "prune the cherry", "prune my fruit trees",
                         "prune the fruit trees", "spray the trees",
                         "dormant oil", "thin the fruit", "thin the apples", "thin the peaches"),
    ))
    registry.register(AssistantAction(
        name="fruit_tree_facts", domain="orchard",
        description="What one kind of fruit tree needs: chill hours, years to fruit, whether it needs a pollination "
                    "partner, spacing, when to prune and how long from bloom to ripe. Use this, before the offline "
                    "library, for any of those about apple, pear, peach, plum, cherry, apricot, fig and the like.",
        parameters={"type": "object", "properties": {"fruit": {"type": "string",
                    "description": "the fruit, e.g. 'peach'"}}, "required": ["fruit"]}, handler=_fruit_facts,
        trigger_phrases=("chill hours", "need a pollinator", "need two apple", "need another tree", "how far apart",
                         "years to fruit", "years to bear", "start bearing", "bear fruit", "self-fertile", "self fertile",
                         "self-pollinating"),
    ))
    registry.register(AssistantAction(
        name="rain_catchment", domain=DOMAIN,
        description="How much rainwater a roof would catch: gallons an inch for its footprint, what his logged rain "
                    "in the last 30 days would have given, and against his beds' watering when he gives their size.",
        parameters={"type": "object", "properties": {
            "roof": {"type": "string", "description": "the roof's footprint: '400 square feet' or '12 by 20'"},
            "beds_sqft": {"type": "number", "description": "square feet of beds it would water, if he said"}},
            "required": ["roof"]},
        handler=_catchment, trigger_phrases=("rain catchment", "catch off", "catch from the roof", "off the roof",
                                             "off a roof", "off my roof", "collect rain", "catch rain",
                                             "rainwater", "rain barrels", "how much rain could"),
    ))
    registry.register_domain_keywords("harvest", ("harvested",))
    registry.register(AssistantAction(
        name="log_harvest", domain="harvest",
        description="Log a garden crop he just harvested: the crop, how much and its unit, kept on his grow lab batch "
                    "of it (one is added, with when it was planted, when there isn't). Not eggs or honey. Undoable.",
        parameters={"type": "object", "properties": {
            "crop": {"type": "string", "description": "what was harvested, e.g. 'tomatoes'"},
            "amount": {"type": "number", "description": "how much"},
            "unit": {"type": "string", "description": "lb, oz, heads, bunches...; empty for a count"},
            "where": {"type": "string", "description": "which bed or tank, only if he said"},
            "last": {"type": "boolean", "description": "true when it's the last of that planting"},
            "planted": {"type": "string", "description": "roughly when it was planted, only if he said"}},
            "required": ["crop", "amount"]},
        handler=_log_harvest, trigger_phrases=("harvested", "log a harvest", "log the harvest", "log my harvest",
                                               "picked today", "out of the garden today",
                                               "from the garden today"),
    ))
    registry.register(AssistantAction(
        name="harvest_this_year", domain="harvest",
        description="What the garden has produced this year, crop by crop, and what it would have cost at the store "
                    "prices he's recorded.",
        parameters={"type": "object", "properties": {}},
        handler=_harvest_year, trigger_phrases=("garden produced", "garden has produced", "harvested this year",
                                                "how much have i harvested", "harvest so far", "garden saved",
                                                "garden save me", "garden worth", "this year's harvest"),
    ))
    registry.register(AssistantAction(
        name="what_can_i_build", domain=DOMAIN,
        description="Which of the Library's builds he's closest to having the materials for, from his workshop's "
                    "stock: how many of each plan's materials are on hand, what's left to buy and its cost.",
        parameters={"type": "object", "properties": {}},
        handler=_buildable, trigger_phrases=("build with what i have", "build with what i've got",
                                             "use up my lumber", "use up my scrap", "use up the lumber",
                                             "build with the lumber", "build with my lumber", "with the lumber i have",
                                             "build with my stock", "build from my stock"),
    ))
    registry.register(AssistantAction(
        name="price_build", domain=DOMAIN,
        description="What a Planner build would cost and what to charge for it: its materials priced from the "
                    "workshop, those with no price named, the hours he says at his labor rate, and his margin.",
        parameters={"type": "object", "properties": {
            "plan": {"type": "string", "description": "words from the build's name, e.g. 'shed'; empty for the newest"},
            "hours": {"type": "number", "description": "how many hours the job will take him"},
            "margin": {"type": "number", "description": "margin percent; 20 when not said"}}},
        handler=_price, trigger_phrases=("price the build", "what would it cost", "what should i charge",
                                         "quote for the", "how much to charge", "cost to build",
                                         "should i charge for"),
    ))
    registry.register(AssistantAction(
        name="garden_this_week", domain=DOMAIN,
        description="What his confirmed garden plans say is due in the next seven days: start indoors, transplant or "
                    "sow, ready to harvest, each with its day.",
        parameters={"type": "object", "properties": {}},
        handler=_garden_week, trigger_phrases=("garden this week", "what do i plant this week", "seeds this week",
                                               "what's due in the garden", "garden today",
                                               "plant this week", "seeds do i still need", "seeds i still need",
                                               "seeds do i need", "doing in the garden", "to do in the garden",
                                               "needs done in the garden"),
    ))
    registry.register(AssistantAction(
        name="what_to_plant", domain=DOMAIN,
        description="For crops not in a confirmed garden plan: what's due to plant now (start indoors, transplant or "
                    "sow) from his last frost, or, with a crop, when to plant that one.",
        parameters={"type": "object", "properties": {
            "crop": {"type": "string", "description": "one crop, if he named one"}}, "required": []},
        handler=_what_to_plant, trigger_phrases=("what can i plant", "what should i plant", "what should i be planting",
                                                 "when should i plant", "when do i plant", "too late to plant",
                                                 "time to plant", "when to plant", "plant now"),
    ))
    registry.register(AssistantAction(
        name="seed_viability", domain=DOMAIN,
        description="How long a kind of seed stays good, and whether his dated packets of it still are.",
        parameters={"type": "object", "properties": {
            "seeds": {"type": "string", "description": "the kind of seed, e.g. 'tomato'"}}, "required": ["seeds"]},
        handler=_seed_life, trigger_phrases=("seeds still good", "seeds last", "seed still good", "old seeds",
                                             "seeds expire", "seeds go bad", "seed viability", "germination test"),
    ))
    registry.register(AssistantAction(
        name="homestead_year", domain=DOMAIN,
        description="The homestead's next twelve months from his records: when each crop of his confirmed garden "
                    "plans starts indoors, goes out and is ready to harvest, and his recurring upkeep, month by month.",
        parameters={"type": "object", "properties": {}},
        handler=_year, trigger_phrases=("homestead year", "this year on the homestead", "what's coming this year",
                                        "when do i plant", "when do i start seeds", "year ahead",
                                        "on the homestead this"),
    ))
    registry.register(AssistantAction(
        name="show_plans", domain=DOMAIN,
        description="Read the plans in progress (or one by id): their stages and steps.",
        parameters={"type": "object", "properties": {"plan_id": {"type": "string"}}},
        handler=_show, trigger_phrases=("show the plan", "what's the plan", "my plans"),
    ))
    for name, kind, said in (
            ("confirm_plan", "projectplan.confirm", "Put up a card to confirm a draft plan: it becomes a project "
             "and one mission a stage."),
            ("drop_plan", "projectplan.drop", "Put up a card to let a draft plan go.")):
        registry.register(AssistantAction(
            name=name, domain=DOMAIN, description=said,
            parameters={"type": "object", "properties": {"plan_id": {"type": "string"}}, "required": ["plan_id"]},
            handler=_card(kind), trigger_phrases=("confirm the plan",) if kind.endswith("confirm") else ("drop the plan",),
        ))
