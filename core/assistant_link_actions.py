"""
core.assistant_link_actions
==============================

"The land loan funds the rental", "the greenhouse depends on selling
the lot", "what depends on selling the lot?", "what's connected to the
truck?" (core/links.py, 2026-10-05). Names are matched to real records
in code; a link is only saved between things that exist. Undoable.
"""

from __future__ import annotations

from core import links
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.person_settings import person_id


def _action_link_things(context, arguments: dict) -> str:
    store = getattr(context, "links", None)
    if store is None:
        return "Links aren't available right now."
    relation = links.relation_from(str(arguments.get("relation") or ""))
    if relation is None:
        return "How are they related? For example: funds, depends on, part of, supports, blocked by, related to."
    source, problem = links.find(context, str(arguments.get("thing") or ""))
    if source is None:
        return problem
    target, problem = links.find(context, str(arguments.get("other") or ""))
    if target is None:
        return problem
    if source == target:
        return "That's the same thing twice."
    link = store.add(source, relation, target, str(arguments.get("note") or ""), person_id(context))
    return f"Noted: {links.describe_link(context, link)}."


def _action_unlink_things(context, arguments: dict) -> str:
    store = getattr(context, "links", None)
    if store is None:
        return "Links aren't available right now."
    source, problem = links.find(context, str(arguments.get("thing") or ""))
    if source is None:
        return problem
    target, problem = links.find(context, str(arguments.get("other") or ""))
    if target is None:
        return problem
    removed = store.remove(source, target)
    if not removed:
        return (f"I don't have a link between {links.name_of(context, source)} and {links.name_of(context, target)} "
                "that you told me about (links that come from the records themselves change with the records).")
    return f"Removed the link between {links.name_of(context, source)} and {links.name_of(context, target)}."


def _action_get_links(context, arguments: dict) -> str:
    ref, problem = links.find(context, str(arguments.get("thing") or ""))
    if ref is None:
        return problem
    name = links.name_of(context, ref)
    found = links.links_for(context, ref)
    waiting = links.downstream(context, ref)
    if not found and not waiting:
        return f"Nothing is linked to {name} yet."
    parts = []
    if found:
        parts.append("; ".join(links.describe_link(context, l) for l in found[:12]) + ".")
    if waiting:
        parts.append(f"Waiting on {name}: " + ", ".join(links.name_of(context, r) for r in waiting) + ".")
    return " ".join(parts)


def register_link_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="link_things", domain="links",
        description="Remember how two of the user's things relate: a loan FUNDS a property, a project DEPENDS_ON a "
                    "sale, a task is BLOCKED_BY something, a project SUPPORTS a goal, something is PART_OF another.",
        parameters={"type": "object", "properties": {
            "thing": {"type": "string", "description": "The first thing, by its name."},
            "relation": {"type": "string", "description": "funds, depends on, blocked by, requires, part of, "
                                                         "supports, located at, brings in income for, related to."},
            "other": {"type": "string", "description": "The second thing, by its name."},
            "note": {"type": "string", "description": "Optional note."},
        }, "required": ["thing", "relation", "other"]},
        handler=_action_link_things,
        trigger_phrases=("depends on", "is blocked by", "blocked by", " funds ", "pays for the", "is part of",
                         "is for the", "goes toward", "link the", "connect the", "waits on", "can't start until",
                         "cant start until", "has to happen before"),
    ))
    registry.register(AssistantAction(
        name="unlink_things", domain="links", destructive=True,
        description="Forget a link the user stated between two things.",
        parameters={"type": "object", "properties": {
            "thing": {"type": "string", "description": "The first thing."},
            "other": {"type": "string", "description": "The second thing."},
        }, "required": ["thing", "other"]},
        handler=_action_unlink_things,
        trigger_phrases=("unlink", "no longer depends", "doesn't depend", "isn't connected", "not related anymore"),
    ))
    registry.register(AssistantAction(
        name="get_links", domain="links",
        description="What's connected to one of the user's things, and what is waiting on it (depends on it, "
                    "blocked by it), directly or down a chain.",
        parameters={"type": "object", "properties": {
            "thing": {"type": "string", "description": "The thing, by its name."},
        }, "required": ["thing"]},
        handler=_action_get_links,
        trigger_phrases=("what depends on", "what's waiting on", "whats waiting on", "connected to", "linked to",
                         "what's tied to", "what is tied to", "what does it affect", "what does that affect",
                         "what's blocked by", "whats blocked by"),
    ))
