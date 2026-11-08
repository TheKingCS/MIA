"""
core.assistant_subscription_actions
=====================================

"Still using it?" by voice (DEC-0054, DEC-0125): "I still use Netflix" marks
that subscription in use today (the same `bill.still_using` as Money's
button), and "which subscriptions haven't I checked?" lists the ones not said
to be in use in three months (core/subscriptions.py).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _still(context, arguments: dict) -> str:
    """Tool still_using_subscription: marks the subscription named as in use today."""
    from core.actions import ACTION_TYPES, ActionError
    from core.assistant_cooking_actions import find_recipe
    from core.subscriptions import is_subscription

    budget = getattr(context, "budget", None)
    if budget is None:
        return "Money isn't on this MIA."
    subs = [b for b in budget.all_bills() if is_subscription(b)] or budget.all_bills()
    bill = find_recipe(subs, str(arguments.get("name") or ""))
    if bill is None:
        return "Which one? Your subscriptions: " + (", ".join(b.name for b in subs) or "none yet") + "."
    try:
        return ACTION_TYPES["bill.still_using"].execute(context, {"bill_id": bill.bill_id})
    except ActionError as problem:
        return str(problem)


def _unchecked(context, arguments: dict) -> str:
    """Tool list_unchecked_subscriptions: the subscriptions not said to be in use in three months, dearest first."""
    from datetime import date

    from core.region import money
    from core.subscriptions import CHECK_DAYS, unconfirmed

    bills = unconfirmed(context, date.today())
    if not bills:
        return "Every subscription has been checked in the last three months."
    return (f"Not checked in {CHECK_DAYS // 30} months: " + ", ".join(f"{b.name} ({money(b.amount)})" for b in bills)
            + ". Say \"I still use\" one, or cancel it.")


def register_subscription_actions(registry) -> None:
    """Registers still_using_subscription and list_unchecked_subscriptions (domain budget)."""
    s = {"type": "string"}
    registry.register(AssistantAction(
        name="still_using_subscription", domain="budget",
        description="The user says they still use one of their subscriptions; mark it in use today.",
        parameters={"type": "object", "properties": {"name": {**s, "description": "The subscription, e.g. 'Netflix'."}},
                    "required": ["name"]},
        handler=_still,
        trigger_phrases=("i still use", "still using", "i do use", "keep my subscription"),
    ))
    registry.register(AssistantAction(
        name="list_unchecked_subscriptions", domain="budget",
        description="Subscriptions the user hasn't said they still use in three months.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_unchecked,
        trigger_phrases=("my subscriptions", "which subscriptions", "unused subscriptions", "subscriptions i don't use"),
    ))
