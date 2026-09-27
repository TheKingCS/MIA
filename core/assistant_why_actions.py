"""
core.assistant_why_actions
=============================

Assistant tools for the owner's chain of reasons, slice B ("Remember
Why") of docs/COGNITIVE_EXTENSION_PROPOSAL.md. The chain lives on
Intents (core/intent_manager.py: `serves_intent_id`, `reason`); the
evidence is computed by core/why_graph.py.

The owner sets the chain up by talking: "the reason I'm working at the
factory is to pay off my debt", "paying off debt is so I can control my
own time". Each link is saved and the whole chain read straight back,
so a misheard link is caught right away and fixed by saying it again
or "unlink".

MIA never invents a reason: these tools only store what the owner said.
"""

from __future__ import annotations

from typing import Optional

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_lookup import name_tokens, resolve_by_name
from core.why_graph import build_why_sheet, chain_text_for

_S = {"type": "string"}


def _intent_named(context: AppContext, name: str) -> tuple[Optional[object], Optional[str]]:
    """(intent, None), or (None, question) when the name is ambiguous, or
    (None, None) when nothing like it exists yet."""
    intents = context.intents.all_intents()
    intent, message = resolve_by_name(intents, name, lambda i: i.name, "goal")
    if intent is not None:
        return intent, None
    wanted = name_tokens(name)
    if wanted and any(wanted & name_tokens(i.name) for i in intents):
        return None, message
    return None, None


def _find_or_create(context: AppContext, name: str) -> tuple[Optional[object], Optional[str], bool]:
    intent, question = _intent_named(context, name)
    if intent is not None or question is not None:
        return intent, question, False
    clean = name.strip().rstrip(".")
    clean = clean[:1].upper() + clean[1:]
    return context.intents.add_intent(clean), None, True


def _action_link_my_reason(context: AppContext, arguments: dict) -> str:
    if context.intents is None:
        return "Goals aren't available right now."
    goal_name = str(arguments.get("goal") or "").strip()
    serves_name = str(arguments.get("serves") or "").strip()
    reason = str(arguments.get("reason") or "").strip()
    if not goal_name or not serves_name:
        return "Tell me both parts: what you're doing, and what it's for."
    goal, question, _ = _find_or_create(context, goal_name)
    if goal is None:
        return question
    serves, question, _ = _find_or_create(context, serves_name)
    if serves is None:
        return question
    if goal.intent_id == serves.intent_id:
        return "Those sound like the same goal to me. What is it for?"
    try:
        context.intents.set_serves(goal.intent_id, serves.intent_id, reason or None)
    except ValueError:
        return f"'{serves.name}' already leads to '{goal.name}', so I can't link it the other way too."
    return f"Got it: {chain_text_for(context, goal.intent_id)}. If I got that wrong, just tell me again."


def _action_show_my_why(context: AppContext, arguments: dict) -> str:
    if context.intents is None:
        return "Goals aren't available right now."
    sheet = build_why_sheet(context)
    if sheet.is_empty:
        return (
            "You haven't told me your reasons yet. Try: 'the reason I'm working this job is to pay off my debt', "
            "then 'paying off debt is so I can control my own time.'"
        )
    parts = []
    for chain in sheet.chains:
        parts.append(" → ".join(link.name + (" (done)" if link.done else "") for link in chain) + ".")
        for link in chain:
            parts.extend(link.evidence)
    parts.extend(sheet.changes)
    return " ".join(parts)


def _action_unlink_my_reason(context: AppContext, arguments: dict) -> str:
    goal, question = _intent_named(context, str(arguments.get("goal") or ""))
    if goal is None:
        return question or f"I don't have a goal called '{arguments.get('goal')}'."
    if goal.serves_intent_id is None:
        return f"'{goal.name}' isn't linked to anything bigger."
    context.intents.set_serves(goal.intent_id, None)
    return f"Unlinked: '{goal.name}' no longer leads to anything bigger."


def _action_mark_goal_achieved(context: AppContext, arguments: dict) -> str:
    goal, question = _intent_named(context, str(arguments.get("goal") or ""))
    if goal is None:
        return question or f"I don't have a goal called '{arguments.get('goal')}'."
    context.intents.update_intent(goal.intent_id, status="Achieved")
    return f"Marked '{goal.name}' achieved. That's a real milestone. I'll stop treating it as something still ahead of you."


_WHY_TRIGGERS = (
    "the reason i", "reason i'm", "reason im", "my reason for", "reasons i'm", "my why", "show my why",
    "what are my reasons", "what am i working toward", "what am i working towards",
    "i'm doing this so", "is so i can", "is so that i can", "so that i can", "change my why", "unlink",
)


def register_why_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="link_my_reason", domain="why",
        description=(
            "Save one of the user's reasons: something they do (goal) serves a bigger goal (serves). Use the "
            "user's own words for both. E.g. 'the reason I work at the factory is to pay off debt' -> "
            "goal='Factory work', serves='Pay off debt'."
        ),
        parameters={"type": "object", "properties": {
            "goal": {**_S, "description": "What they're doing now, e.g. 'Factory work' or 'Pay off debt'."},
            "serves": {**_S, "description": "What it's for, e.g. 'Pay off debt' or 'Control over my time'."},
            "reason": {**_S, "description": "Their exact words, if they said more."},
        }, "required": ["goal", "serves"]},
        handler=_action_link_my_reason,
        trigger_phrases=_WHY_TRIGGERS,
    ))
    registry.register(AssistantAction(
        name="show_my_why", domain="why",
        description="Read back the user's chain of reasons with the facts behind each one.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_show_my_why,
        trigger_phrases=("show my why", "my why", "what are my reasons", "what am i working toward", "what am i working towards"),
    ))
    registry.register(AssistantAction(
        name="unlink_my_reason", domain="why",
        description="Remove the link from one of the user's goals to the bigger goal it served.",
        parameters={"type": "object", "properties": {"goal": {**_S, "description": "The goal to unlink."}}, "required": ["goal"]},
        handler=_action_unlink_my_reason,
        trigger_phrases=("unlink", "change my why", "that's not my reason", "thats not my reason"),
    ))
    registry.register(AssistantAction(
        name="mark_goal_achieved", domain="why",
        description="Mark one of the user's goals achieved (e.g. 'I paid off all my debt!').",
        parameters={"type": "object", "properties": {"goal": {**_S, "description": "The goal they achieved."}}, "required": ["goal"]},
        handler=_action_mark_goal_achieved,
        trigger_phrases=("achieved my goal", "i reached my goal", "goal achieved", "i did it, i paid off", "mark my goal"),
    ))
    # Deliberately no register_entity_names(): goal names are everyday
    # words ("Factory work", "Pay off debt"), and matching them would pull
    # these tools into ordinary sentences like "work was awful".
