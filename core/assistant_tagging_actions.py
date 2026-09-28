"""
core.assistant_tagging_actions
=================================

Assistant tools for sorting bank charges to businesses
(core/business_tagging.py): "which charges need a business?" and "the
Shell charge was for lawn care" / "the Walmart one was personal".
"""

from __future__ import annotations

import re

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.business_tagging import PERSONAL, apply_choice, merchant_key, pending_review

_S = {"type": "string"}


def _names(context) -> dict:
    return {e.entity_id: e.name for e in context.budget.all_business_entities()}


def _action_list_untagged(context: AppContext, arguments: dict) -> str:
    if getattr(context, "budget", None) is None or not context.budget.all_business_entities():
        return "You haven't set up any businesses yet (Budget → Summary → Manage Entities)."
    pending = pending_review(context)
    if not pending:
        return "Every bank charge is sorted."
    names = _names(context)
    parts = []
    for expense, suggestion in pending[:5]:
        text = f"{expense.payee or expense.description} ${expense.amount:,.2f} on {expense.date}"
        if suggestion is not None:
            text += " (probably personal)" if suggestion.entity_id == PERSONAL else f" (probably {names[suggestion.entity_id]})"
        parts.append(text)
    more = f", and {len(pending) - 5} more" if len(pending) > 5 else ""
    return (f"{len(pending)} charge{'s' if len(pending) != 1 else ''} need a business: " + "; ".join(parts) + more +
            ". Tell me like \"the Shell charge was for lawn care\", or use Budget → Bank Sync → Review Business Tags.")


def _find_business(context, words: str):
    lowered = words.lower().strip()
    if re.search(r"\b(personal|mine|household|home)\b", lowered):
        return PERSONAL
    for entity in context.budget.all_business_entities():
        name = entity.name.lower()
        significant = [w for w in re.findall(r"[a-z]+", name) if w not in ("llc", "inc", "co", "the", "and")]
        if name in lowered or lowered in name or any(w in lowered for w in significant if len(w) >= 4):
            return entity.entity_id
    return None


def _action_tag_charge(context: AppContext, arguments: dict) -> str:
    if getattr(context, "budget", None) is None or not context.budget.all_business_entities():
        return "You haven't set up any businesses yet (Budget → Summary → Manage Entities)."
    store = merchant_key(str(arguments.get("charge") or ""))
    business_words = str(arguments.get("business") or "")
    choice = _find_business(context, business_words)
    if choice is None:
        return f"I don't have a business called {business_words}. Yours: " + ", ".join(_names(context).values()) + "."
    pending = pending_review(context)
    matches = [e for e, _ in pending if store and merchant_key(e.payee or e.description) == store]
    if not matches:
        return f"I don't see an unsorted charge from {arguments.get('charge') or 'there'}."
    expense = matches[0]  # the newest
    apply_choice(context, expense.entry_id, choice)
    where = "personal" if choice == PERSONAL else _names(context)[choice]
    others = len(matches) - 1
    tail = f" {others} more from there are still waiting." if others else ""
    return f"Marked the {expense.payee or expense.description} charge (${expense.amount:,.2f}, {expense.date}) as {where}. I'll remember that.{tail}"


def register_tagging_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="list_untagged_charges", domain="business_tags",
        description="List bank charges that haven't been sorted to one of the user's businesses (or personal) yet.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_list_untagged,
        trigger_phrases=("need a business", "untagged", "business tags", "which charges", "unsorted charges", "sort my charges"),
    ))
    registry.register(AssistantAction(
        name="tag_charge", domain="business_tags",
        description="Say which business a bank charge was for, or that it was personal. MIA learns it for that store.",
        parameters={"type": "object", "properties": {
            "charge": {**_S, "description": "The store or charge, e.g. 'Shell'."},
            "business": {**_S, "description": "The business, e.g. 'lawn care', or 'personal'."},
        }, "required": ["charge", "business"]},
        handler=_action_tag_charge,
        trigger_phrases=("charge was for", "charge was personal", "charge is for", "one was personal", "one was for",
                         "was a business expense", "tag the"),
    ))
