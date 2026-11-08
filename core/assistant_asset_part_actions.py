"""
core.assistant_asset_part_actions
===================================

Parts per asset by voice (DEC-0125; the screen is the asset page's Parts
tab, core/asset_parts.py): "the mower uses the 10W-30 oil", "what parts
does the truck take?", "the truck doesn't use that filter anymore". Names
are matched to real records in code; the add and remove are the same
actions the page uses, so undo takes them back.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _asset(context, name: str):
    """(asset, None) for the one asset the name means, or (None, what to say back)."""
    from core.assistant_lookup import resolve_by_name

    maintenance = getattr(context, "maintenance", None)
    if maintenance is None:
        return None, "The Garage isn't on this MIA."
    return resolve_by_name(maintenance.all_assets(), name, lambda a: a.name, "vehicle, tool or appliance")


def _part_ref(context, name: str):
    """(ref, None) for the one part, material or inventory item the name means, or (None, what to say back)."""
    from core.asset_parts import PART_KINDS
    from core.links import find

    return find(context, name, PART_KINDS)


def _run(context, kind: str, params: dict) -> str:
    """Runs asset.part_add or asset.part_remove and says what happened (or why not)."""
    from core.actions import ACTION_TYPES, ActionError

    try:
        return ACTION_TYPES[kind].execute(context, params)
    except ActionError as problem:
        return str(problem)


def _add(context, arguments: dict) -> str:
    """Tool add_asset_part: an asset uses a part, material or inventory item."""
    asset, problem = _asset(context, str(arguments.get("asset") or ""))
    if asset is None:
        return problem
    ref, problem = _part_ref(context, str(arguments.get("part") or ""))
    if ref is None:
        return problem + " Add it to your inventory or the Workshop's materials first if it isn't there."
    return _run(context, "asset.part_add", {"asset_id": asset.asset_id, "part": ref})


def _remove(context, arguments: dict) -> str:
    """Tool remove_asset_part: an asset no longer uses a part."""
    from core.asset_parts import parts_for
    from core.assistant_lookup import resolve_by_name

    asset, problem = _asset(context, str(arguments.get("asset") or ""))
    if asset is None:
        return problem
    part, problem = resolve_by_name(parts_for(context, asset.asset_id), str(arguments.get("part") or ""),
                                    lambda p: p["name"], "part")
    if part is None:
        return problem
    return _run(context, "asset.part_remove", {"asset_id": asset.asset_id, "part": part["ref"]})


def _list(context, arguments: dict) -> str:
    """Tool list_asset_parts: the parts an asset uses, with what's on hand and what's low or out."""
    from core.asset_parts import parts_for

    asset, problem = _asset(context, str(arguments.get("asset") or ""))
    if asset is None:
        return problem
    rows = parts_for(context, asset.asset_id)
    if not rows:
        return f"No parts listed for {asset.name} yet. Say which it uses, like \"the {asset.name} uses the air filter\"."

    def line(r) -> str:
        """One part in words: its name, how many, and out or low."""
        have = f"{r['have']:g}" + (f" {r['unit']}" if r["unit"] else "")
        return f"{r['name']} ({'none left' if r['state'] == 'out' else have + (', low' if r['state'] == 'low' else '')})"
    return f"{asset.name} uses: " + "; ".join(line(r) for r in rows) + "."


def register_asset_part_actions(registry) -> None:
    """Registers add_asset_part, remove_asset_part and list_asset_parts (domain maintenance)."""
    s = {"type": "string"}
    registry.register(AssistantAction(
        name="add_asset_part", domain="maintenance",
        description="A vehicle, tool or appliance uses one of the user's parts, materials or inventory items "
                    "(e.g. 'the mower uses the 10W-30 oil').",
        parameters={"type": "object", "properties": {"asset": {**s, "description": "The vehicle, tool or appliance."},
                                                     "part": {**s, "description": "The part, material or item."}},
                    "required": ["asset", "part"]},
        handler=_add,
        trigger_phrases=("uses the", "takes the", "part for the", "filter for the"),
    ))
    registry.register(AssistantAction(
        name="remove_asset_part", domain="maintenance",
        description="A vehicle, tool or appliance no longer uses one of its listed parts.",
        parameters={"type": "object", "properties": {"asset": {**s, "description": "The vehicle, tool or appliance."},
                                                     "part": {**s, "description": "The part to take off its list."}},
                    "required": ["asset", "part"]},
        handler=_remove,
        trigger_phrases=("doesn't use", "no longer uses", "take the part off"),
    ))
    registry.register(AssistantAction(
        name="list_asset_parts", domain="maintenance",
        description="The parts a vehicle, tool or appliance uses, with how many are on hand and which are low or out.",
        parameters={"type": "object", "properties": {"asset": {**s, "description": "The vehicle, tool or appliance."}},
                    "required": ["asset"]},
        handler=_list,
        trigger_phrases=("what parts", "parts for", "parts does", "what does the truck take"),
    ))
