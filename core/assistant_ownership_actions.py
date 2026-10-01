"""
core.assistant_ownership_actions
===================================

"Whose truck is it?" and "the mower is mine" (core/ownership.py,
2026-10-01): owner marks on maintenance items (vehicles, tools,
appliances).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_lookup import resolve_by_name
from core.ownership import owner_name, possessive, resolve_owner


def _find_item(context, name: str):
    maintenance = getattr(context, "maintenance", None)
    if maintenance is None:
        return None, "I don't have any vehicles, tools or appliances on this MIA."
    return resolve_by_name(maintenance.all_assets(), name, lambda a: a.name, "item")


def _action_set_item_owner(context, arguments: dict) -> str:
    asset, error = _find_item(context, str(arguments.get("item") or ""))
    if error:
        return error
    understood, owner_id = resolve_owner(context, str(arguments.get("owner") or ""))
    if not understood:
        return f"Whose is the {asset.name}? Say \"mine\", \"shared\", or the name of someone in your household."
    context.maintenance.update_asset(asset.asset_id, owner_profile_id=owner_id)
    if owner_id is None:
        return f"Okay, the {asset.name} is shared by the household."
    whose = possessive(context, owner_id)
    return f"Okay, the {asset.name} is {whose}." + (" Its maintenance shows on your Today list." if whose == "yours" else
                                                    f" Its maintenance shows on {owner_name(context, owner_id)}'s Today list.")


def _action_get_item_owner(context, arguments: dict) -> str:
    asset, error = _find_item(context, str(arguments.get("item") or ""))
    if error:
        return error
    whose = possessive(context, asset.owner_profile_id)
    if whose == "shared":
        return f"The {asset.name} is shared by the household (nobody's marked as its owner)."
    return f"The {asset.name} is {whose}."


def register_ownership_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="set_item_owner", domain="ownership",
        description="Say whose a vehicle, tool or appliance is: the user's, another household member's, or shared.",
        parameters={"type": "object", "properties": {
            "item": {"type": "string", "description": "The item, e.g. 'the truck'."},
            "owner": {"type": "string", "description": "'mine', 'shared', or a household member's name."},
        }, "required": ["item", "owner"]},
        handler=_action_set_item_owner,
        trigger_phrases=("is mine", "belongs to", "is shared", "is ours", "is my truck", "my own",
                         "is everyone's"),
    ))
    registry.register(AssistantAction(
        name="get_item_owner", domain="ownership",
        description="Whose a vehicle, tool or appliance is.",
        parameters={"type": "object", "properties": {
            "item": {"type": "string", "description": "The item, e.g. 'the truck'."},
        }, "required": ["item"]},
        handler=_action_get_item_owner,
        trigger_phrases=("whose", "who owns", "who does the", "who's is"),
    ))
