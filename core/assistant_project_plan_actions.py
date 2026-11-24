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


def register_project_plan_actions(registry) -> None:
    """Registers plan_with_me, change_plan (a draft's sizes, beds, crops, frosts, stages and notes; its build is
    chosen when drafted), price_build (core/plan_price.py), homestead_year (core/homestead_year.py), garden_this_week (core/garden_week.py),
    show_plans,
    confirm_plan and drop_plan, and seed_viability (how long his seeds keep, core/seed_life.py). Their trigger
    phrases cover the everyday ways he'd ask ("what should I plant this
    week", "what needs doing in the garden", "how much should I charge for a picnic table":
    tests/test_everyday_phrasing_routing.py)."""
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
