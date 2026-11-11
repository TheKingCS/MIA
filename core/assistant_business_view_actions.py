"""
core.assistant_business_view_actions
======================================

The Businesses subdashboard by voice (DEC-0153, 2026-11-11): "how are my
businesses doing?" (each business's month and year, from
core/web_businesses.businesses_page) and "how is the rental business
doing?" (one business's dashboard: its money, open orders and quotes,
properties and what it owes). Facts are put together in code; the model
only phrases them. Orders and quotes are added for a business through
the quote and order actions (core/business_actions.py, `entity_id`).
"""

from __future__ import annotations

from datetime import date

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def describe_businesses(page: dict) -> str:
    """Pure logic. Every business's month and year in a few sentences."""
    if not page.get("available"):
        return "Businesses come from Money, which isn't set up here."
    if not page["businesses"]:
        return "You don't have a business set up in Money yet."
    parts = [f"{b['name']}: {b['month']['net']} this month ({b['month']['income']} in, {b['month']['expenses']} out), "
             f"{b['year']['net']} this year"
             + (f", {b['open_orders']} open order{'s' if b['open_orders'] != 1 else ''}" if b["open_orders"] else "")
             + "." for b in page["businesses"]]
    if page.get("unsorted"):
        parts.append(f"{page['unsorted']['count']} orders or quotes have no business yet.")
    return " ".join(parts)


def describe_business(found: dict) -> str:
    """Pure logic. One business's dashboard in a few sentences."""
    open_orders = [o for o in found["orders"] if o["open"]]
    open_quotes = [q for q in found["quotes"] if q["open"]]
    line = (f"{found['name']}: {found['month']['net']} this month ({found['month']['income']} in, "
            f"{found['month']['expenses']} out), {found['year']['net']} this year.")
    if found["spending"]:
        line += " Most of this year's spending went to " + ", ".join(
            f"{s['category']} ({s['amount']})" for s in found["spending"][:3]) + "."
    if open_orders or open_quotes:
        line += f" {len(open_orders)} open order{'s' if len(open_orders) != 1 else ''} and {len(open_quotes)} open quote" \
                f"{'s' if len(open_quotes) != 1 else ''}."
    if found["properties"]:
        line += f" It owns {len(found['properties'])} propert{'ies' if len(found['properties']) != 1 else 'y'}."
    if found["debts"]:
        line += " It owes " + ", ".join(f"{d['name']} {d['balance']}" for d in found["debts"]) + "."
    return line


def _action_get_businesses(context, arguments: dict) -> str:
    """Tool get_businesses: how each business is doing this month and this year."""
    from core.web_businesses import businesses_page

    return describe_businesses(businesses_page(context, date.today()))


def _action_get_business(context, arguments: dict) -> str:
    """Tool get_business: one business's own dashboard, by (part of) its name."""
    from core.web_businesses import business_dashboard, businesses_page

    words = " ".join(str(arguments.get("business") or "").lower().replace("business", " ").split())
    page = businesses_page(context, date.today())
    if not page.get("available") or not page["businesses"]:
        return describe_businesses(page)
    asked = [w for w in words.split() if w not in ("the", "my", "our", "a") and len(w) > 2]

    def means(name: str) -> bool:
        """Whether the words name this business: all of them in its name ("the woodshop"), or its whole name."""
        name = name.lower()
        return bool(asked) and (all(w in name for w in asked) or name in words)

    match = next((b for b in page["businesses"] if means(b["name"])), None)
    if match is None:
        return "Which business? You have " + ", ".join(b["name"] for b in page["businesses"]) + "."
    return describe_business(business_dashboard(context, match["id"], date.today()))


def register_business_view_actions(registry: AssistantActionRegistry) -> None:
    """Registers get_businesses and get_business (domain ledger: Orders & Quotes' and the businesses')."""
    registry.register(AssistantAction(
        name="get_businesses", domain="ledger",
        description="How each of the user's businesses is doing: this month's and this year's income, expenses and net, "
                    "and open orders.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_get_businesses,
        trigger_phrases=("my businesses", "how are the businesses", "how's business", "hows business",
                         "business doing", "businesses doing"),
    ))
    registry.register(AssistantAction(
        name="get_business", domain="ledger",
        description="One business's own dashboard by name: its money this month and year, where it went, open orders and "
                    "quotes, properties and debts.",
        parameters={"type": "object", "properties": {
            "business": {"type": "string", "description": "the business's name, or part of it."}}, "required": ["business"]},
        handler=_action_get_business,
        trigger_phrases=("how is the business", "how's the business", "how is my business", "dashboard for the business"),
    ))
