"""
core.assistant_requirement_actions
====================================

What each project needs, by voice (Procurement P1, DEC-0172, DEC-0125):
- "What do I still need for the greenhouse?" (`project_needs`).
- "The greenhouse needs four ventilation fans" (`add_need`).
- "I got the fans for the greenhouse" (`got_need`), "the greenhouse doesn't need the fans" (`drop_need`).

Each change runs the same action the World page's Needs tab uses (core/requirement_actions.py), with the same checks
and undo.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run


def needs_sentence(context, project_words: str = "") -> str:
    """What's still needed: for the project named, or for every project with something open; from the store."""
    book, projects = getattr(context, "requirements", None), getattr(context, "projects", None)
    if book is None or projects is None:
        return "Project needs aren't kept on this MIA."
    words = " ".join(str(project_words or "").lower().split())
    chosen = [p for p in projects.all_projects() if not words or words in p.name.lower()]
    if words and not chosen:
        return "Which project? I don't have one by that name."
    said = []
    for p in chosen:
        lines = [r for r in book.for_project(p.project_id) if r.status in ("needed", "partial", "found")]
        if not lines:
            continue
        parts = [f"{r.quantity - r.have:g} {r.unit + ' ' if r.unit else ''}{r.item}" + (" (some on hand)" if r.status == "partial" else "")
                 for r in lines[:8]]
        more = f", and {len(lines) - 8} more" if len(lines) > 8 else ""
        said.append(f"{p.name} still needs {', '.join(parts)}{more}")
    if not said:
        return "Nothing's still needed." if not words else f"{chosen[0].name} has everything it needs on the list."
    return ". ".join(said) + "."


def _needs(context, arguments: dict) -> str:
    """Tool project_needs: what's still needed, for one project or all."""
    return needs_sentence(context, arguments.get("project") or "")


def _add(context, arguments: dict) -> str:
    """Tool add_need: proposes `requirement.add`."""
    keys = ("project", "item", "quantity", "unit", "specs", "max_price", "condition", "priority", "needed_by")
    return _run(context, "requirement.add", {k: arguments.get(k) or "" for k in keys})


def _got(context, arguments: dict) -> str:
    """Tool got_need: proposes `requirement.got`."""
    return _run(context, "requirement.got", {"project": arguments.get("project") or "", "item": arguments.get("item") or ""})


def _drop(context, arguments: dict) -> str:
    """Tool drop_need: proposes `requirement.remove`."""
    return _run(context, "requirement.remove", {"project": arguments.get("project") or "",
                                                "item": arguments.get("item") or ""})


def _opportunities(context, arguments: dict) -> str:
    """Tool what_is_worth_buying: finds that meet a project's need, best first, each with its recommendation and why
    (core/opportunity.py, Procurement P3). Read only."""
    from core import opportunity

    return opportunity.sentence(opportunity.opportunities(context))


def register_requirement_actions(registry: AssistantActionRegistry) -> None:
    """Registers the project-needs tools: project_needs, add_need, got_need and drop_need; and what_is_worth_buying,
    the finds that meet them with a recommendation each (Procurement P3)."""
    named = {"type": "object", "properties": {"project": {"type": "string", "description": "the project's name"},
                                              "item": {"type": "string", "description": "the item"}},
             "required": ["item"]}
    registry.register(AssistantAction(
        name="what_is_worth_buying", domain="requirements",
        description="Finds that meet one of the person's project needs, best first, each with buy when ready, "
                    "investigate, wait or skip and why. Read only: it never buys anything.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_opportunities,
        trigger_phrases=("worth buying", "any good deals for", "deals for my projects", "should i buy",
                         "what have you found for my projects", "opportunities"),
        subjects=("deal", "deals", "buy", "opportunities")))
    registry.register(AssistantAction(
        name="project_needs", domain="requirements", description="What a project (or every project) still needs.",
        parameters={"type": "object", "properties": {"project": {"type": "string", "description": "optional"}},
                    "required": []},
        handler=_needs,
        trigger_phrases=("what do i still need", "what does the project need", "what do i need for", "shopping list for the"),
        subjects=("need", "project"),
    ))
    registry.register(AssistantAction(
        name="add_need", domain="requirements", description="Add something a project needs.",
        parameters={"type": "object", "properties": {
            "project": {"type": "string", "description": "the project's name"},
            "item": {"type": "string", "description": "what it needs, in the person's words"},
            "quantity": {"type": "string", "description": "how many (default 1)"},
            "unit": {"type": "string", "description": "optional"},
            "specs": {"type": "string", "description": "what it has to be (optional)"},
            "max_price": {"type": "string", "description": "the most it should cost (optional)"},
            "condition": {"type": "string", "description": "any, new or used (optional)"},
            "priority": {"type": "string", "description": "first, later or nice to have (optional)"},
            "needed_by": {"type": "string", "description": "date (optional)"}},
            "required": ["project", "item"]},
        handler=_add,
        trigger_phrases=("add a need", "add to the needs for", "project needs a", "for the project i need"),
        subjects=("need", "project"),
    ))
    registry.register(AssistantAction(
        name="got_need", domain="requirements", description="Mark something a project needed as in hand.",
        parameters=named, handler=_got,
        trigger_phrases=("got it for the project", "have it now for the", "mark the need in hand"),
        subjects=("need",),
    ))
    registry.register(AssistantAction(
        name="drop_need", domain="requirements", description="Take something off a project's needs.",
        parameters=named, handler=_drop,
        trigger_phrases=("doesn't need", "don't need the", "take off the list"),
        subjects=("need",),
    ))
