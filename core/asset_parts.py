"""
core.asset_parts
==================

Parts per asset (2026-11-07; the asset page's "parts aren't tracked per
asset yet", PLANNED since 2026-10-06): the oil filters, blades, belts and
fluids a vehicle, tool or appliance uses, from the household's own
inventory, workshop materials and parts bins.

No new store: "the truck uses this filter" is a stated link in
core/links.py, `asset:<id> REQUIRES <kind>:<id>`, so it shows up in the
link graph and "what's connected to the truck?" too, and undo takes it
back like any link.

- `parts_for(context, asset_id)`: each part the asset uses, how many are
  on hand, and whether it's low (a material at or under its reorder level)
  or out (none left), low ones first.
- `choices(context)`: every part, material and inventory item, for the
  picker.
- Actions `asset.part_add` / `asset.part_remove` (the asset page's Add A
  Part and Remove; by voice, add_asset_part, remove_asset_part and
  list_asset_parts in core/assistant_asset_part_actions.py).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

PART_KINDS = ("inventory_item", "material", "component")
RELATION = "REQUIRES"


def stock_state(kind: str, record) -> tuple[float, str, str]:
    """Pure logic. (how many on hand, its unit, "out" / "low" / "ok") for one part: a material is low at or under its
    reorder level, anything is out at zero."""
    if kind == "material":
        have = float(getattr(record, "quantity_on_hand", 0) or 0)
        threshold = float(getattr(record, "reorder_threshold", 0) or 0)
        state = "out" if have <= 0 else "low" if threshold and have <= threshold else "ok"
        return have, getattr(record, "unit", "") or "", state
    have = float(getattr(record, "quantity", 0) or 0)
    return have, "", "out" if have <= 0 else "ok"


def _record(context, ref: str):
    """(kind, record) for a part's ref, or (kind, None) when it's gone."""
    from core.links import KINDS, _records

    kind_name, _, record_id = ref.partition(":")
    kind = KINDS.get(kind_name)
    if kind is None or kind_name not in PART_KINDS:
        return kind_name, None
    return kind_name, next((r for r in _records(context, kind) if str(getattr(r, kind.id_attr, "")) == record_id), None)


def parts_for(context, asset_id: str) -> list[dict]:
    """The parts an asset uses: [{ref, name, kind, have, unit, state, where}], out and low ones first, then by name.
    A part since deleted is left out."""
    store = getattr(context, "links", None)
    if store is None:
        return []
    rows = []
    order = {"out": 0, "low": 1, "ok": 2}
    for link in store.all_links():
        if link.relation != RELATION or link.source != f"asset:{asset_id}":
            continue
        kind, record = _record(context, link.target)
        if record is None:
            continue
        have, unit, state = stock_state(kind, record)
        rows.append({"ref": link.target, "name": record.name, "kind": kind, "have": round(have, 2), "unit": unit,
                     "state": state, "where": getattr(record, "location", "") or ""})
    return sorted(rows, key=lambda r: (order[r["state"]], r["name"].lower()))


def choices(context) -> list[dict]:
    """Every part, material and inventory item, for the Add A Part picker: [{id: ref, name}], by name."""
    from core.links import KINDS, _records, ref_of

    out = []
    for kind_name in PART_KINDS:
        label = {"inventory_item": "Inventory", "material": "Material", "component": "Part"}[kind_name]
        for record in _records(context, KINDS[kind_name]):
            out.append({"id": ref_of(kind_name, record), "name": f"{record.name} ({label})"})
    return sorted(out, key=lambda c: c["name"].lower())


def _asset(context, params):
    """The asset the params name; ActionError when it's gone."""
    asset = _need(context, "maintenance").get_asset(str(params.get("asset_id") or ""))
    if asset is None:
        raise ActionError("That isn't in the Garage anymore.")
    return asset


def _part(context, params):
    """The part the params name (a ref like material:ab12); ActionError when it isn't a part or is gone."""
    ref = str(params.get("part") or "")
    kind, record = _record(context, ref)
    if record is None:
        raise ActionError("That part isn't in your inventory, materials or parts anymore.")
    return ref, record


def _add(context, params) -> str:
    """Does asset.part_add: the asset uses this part (a stated link)."""
    asset, (ref, record) = _asset(context, params), _part(context, params)
    from core.person_settings import person_id

    _need(context, "links").add(f"asset:{asset.asset_id}", RELATION, ref, "", person_id(context))
    return f"{asset.name} uses {record.name}."


def _remove(context, params) -> str:
    """Does asset.part_remove: the asset no longer lists this part."""
    asset = _asset(context, params)
    ref = str(params.get("part") or "")
    if not _need(context, "links").remove(f"asset:{asset.asset_id}", ref, RELATION):
        raise ActionError("That part isn't listed for it.")
    kind, record = _record(context, ref)
    return f"Took {record.name if record is not None else 'that part'} off {asset.name}'s parts."


def _describe_remove(context, params) -> str:
    """The approval sentence for asset.part_remove (the part may be gone already; then it says "that part")."""
    record = _record(context, str(params.get("part") or ""))[1]
    return f"Take {record.name if record is not None else 'that part'} off {_asset(context, params).name}'s parts"


PART_ACTIONS = {a.kind: a for a in (
    ActionType("asset.part_add", "Add A Part", {"asset_id": "the asset", "part": "the part, material or item"},
               lambda c, p: f"{_asset(c, p).name} uses {_part(c, p)[1].name}", _add),
    ActionType("asset.part_remove", "Remove", {"asset_id": "the asset", "part": "the part"}, _describe_remove, _remove),
)}
ACTION_TYPES.update(PART_ACTIONS)
