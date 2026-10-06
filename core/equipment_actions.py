"""
core.equipment_actions
========================

Every change the Garage, Property, Greenhouse and Maintenance screens can
make (2026-10-06, DEC-0017), as action kinds on the contract in
core/actions.py, from one table (core/record_actions.py): assets
(add, edit, delete), maintenance tasks (add, edit, delete), and logging a
reading, on a task's meter (engine hours toward the next oil change) or
on the asset's own meter (fuel, mileage). Marking a task done is
`maintenance.done` (core/actions.py), which also takes a meter value.
Removing a document from an asset keeps the stored file, so undo brings
it back whole; deleting an asset keeps its documents for the same reason.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, field_dict, get, parse, record_form, record_kinds, show


def _lists():
    from core.maintenance_manager import ASSET_CATEGORIES, PRIORITY_LEVELS, TRIGGER_TYPES

    return tuple(ASSET_CATEGORIES), tuple(TRIGGER_TYPES), tuple(PRIORITY_LEVELS)


_CATEGORIES, _TRIGGERS, _PRIORITIES = _lists()

RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("asset", "asset", "asset_id", "get_asset", "add_asset", "update_asset", "delete_asset", store="maintenance",
           delete_note="Its maintenance tasks go with it; its documents are kept.", fields=(
               Field("name", "Name", "text", True),
               Field("category", "Kind", "choice", options=_CATEGORIES, default="Other", say="kind", quiet_default=True),
               Field("manufacturer", "Make", "text", say="make"),
               Field("model", "Model", "text"),
               Field("serial_number", "Serial number", "text", say="serial"),
               Field("purchase_date", "Bought on", "date", say="bought"),
               Field("purchase_price", "Price paid", "money", default=0.0, say="price"),
               Field("warranty_until", "Warranty until", "date", say="warranty until"),
               Field("notes", "Notes", "textarea"),
           )),
    Record("maintenance_task", "maintenance task", "task_id", "get_task", "add_task", "update_task", "delete_task",
           store="maintenance", title_attrs=("title",), fields=(
               Field("asset_id", "For", "asset", True, say="for"),
               Field("title", "What to do", "text", True),
               Field("trigger_type", "Goes by", "choice", options=_TRIGGERS, default="calendar", say="goes by",
                     quiet_default=True),
               Field("interval_days", "Every (days)", "int", say="every (days)"),
               Field("meter_unit", "Meter unit", "text", say="unit"),
               Field("meter_interval", "Every (meter units)", "amount", say="every"),
               Field("threshold_value", "Due at reading", "number", say="due at"),
               Field("threshold_direction", "Due when the reading is", "choice", options=("below", "above"),
                     default="below", say="due when", quiet_default=True),
               Field("priority", "Priority", "choice", options=_PRIORITIES, default="normal", quiet_default=True),
               Field("last_completed", "Last done", "date", say="last done"),
               Field("notes", "Notes", "textarea"),
           )),
)}


# ------------------------------------------------------------------ deleting an asset (documents kept)


def _delete_asset(context, params) -> str:
    asset = get(context, RECORDS["asset"], params)
    _need(context, "maintenance").delete_asset(asset.asset_id, keep_documents=True)
    return f"Deleted {asset.name} and its tasks. Undo brings them back."


# ------------------------------------------------------------------ readings


_VALUE = Field("value", "Reading", "number", True)
_NOTE = Field("note", "Note", "textarea")
_METER = Field("meter_name", "Meter", "text", True, say="meter")
_UNIT = Field("unit", "Unit", "text")


def _task_and_asset(context, params):
    task = _need(context, "maintenance").get_task(str(params.get("task_id", "")))
    if task is None:
        raise ActionError("That maintenance task isn't there anymore.")
    return task, context.maintenance.get_asset(task.asset_id)


def _describe_task_reading(context, params) -> str:
    task, asset = _task_and_asset(context, params)
    value = parse(_VALUE, params.get("value"))
    unit = f" {task.meter_unit}" if task.meter_unit else ""
    return f"Log {value:g}{unit} for {task.title}" + (f" on {asset.name}" if asset else "")


def _log_task_reading(context, params) -> str:
    task, asset = _task_and_asset(context, params)
    value = parse(_VALUE, params.get("value"))
    _need(context, "data_logger")
    context.maintenance.log_reading(task.task_id, value, note=parse(_NOTE, params.get("note")))
    return f"Logged {value:g} {task.meter_unit}".rstrip() + f" for {task.title}."


def _describe_asset_reading(context, params) -> str:
    asset = get(context, RECORDS["asset"], params)
    meter, value = parse(_METER, params.get("meter_name")), parse(_VALUE, params.get("value"))
    unit = parse(_UNIT, params.get("unit"))
    return f"Log {meter} {value:g}{(' ' + unit) if unit else ''} on {asset.name}"


def _log_asset_reading(context, params) -> str:
    asset = get(context, RECORDS["asset"], params)
    meter, value = parse(_METER, params.get("meter_name")), parse(_VALUE, params.get("value"))
    _need(context, "data_logger")
    context.maintenance.log_asset_reading(asset.asset_id, meter, value, unit=parse(_UNIT, params.get("unit")),
                                          note=parse(_NOTE, params.get("note")))
    return f"Logged {meter} on {asset.name}."


# ------------------------------------------------------------------ documents


def _document(context, params):
    asset = get(context, RECORDS["asset"], params)
    name = str(params.get("filename", ""))
    if name not in asset.documents:
        raise ActionError("That document isn't on it anymore.")
    return asset, name


def _describe_document_remove(context, params) -> str:
    asset, name = _document(context, params)
    return f"Remove {name} from {asset.name}"


def _remove_document(context, params) -> str:
    asset, name = _document(context, params)
    # Only the list changes; the stored copy stays so undo restores it.
    context.maintenance.update_asset(asset.asset_id, documents=[d for d in asset.documents if d != name])
    return f"{name} is removed from {asset.name}."


# ------------------------------------------------------------------ the kinds


def _kinds() -> list[ActionType]:
    kinds = []
    for record in RECORDS.values():
        kinds += record_kinds(record)
    kinds = [k for k in kinds if k.kind != "asset.delete"]
    kinds += [
        ActionType("asset.delete", "Delete", {"asset_id": "the asset"},
                   lambda c, p: f"Delete the asset {get(c, RECORDS['asset'], p).name}. "
                                f"{RECORDS['asset'].delete_note}", _delete_asset),
        ActionType("maintenance.reading", "Log reading", {"task_id": "the task", "value": "the reading",
                                                          "note": "optional"},
                   _describe_task_reading, _log_task_reading),
        ActionType("asset.reading", "Log reading", {"asset_id": "the asset", "meter_name": "e.g. Fuel",
                                                    "value": "the reading", "unit": "optional", "note": "optional"},
                   _describe_asset_reading, _log_asset_reading),
        ActionType("asset.document_remove", "Remove", {"asset_id": "the asset", "filename": "the document"},
                   _describe_document_remove, _remove_document),
    ]
    return kinds


EQUIPMENT_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(EQUIPMENT_ACTIONS)


def form_spec() -> dict:
    forms = {key: record_form(r) for key, r in RECORDS.items()}
    forms["task_reading"] = {"noun": "reading", "id_param": "task_id", "fields": [field_dict(_VALUE), field_dict(_NOTE)]}
    forms["asset_reading"] = {"noun": "reading", "id_param": "asset_id",
                              "fields": [field_dict(_METER), field_dict(_VALUE), field_dict(_UNIT), field_dict(_NOTE)]}
    forms["done"] = {"noun": "completion", "id_param": "task_id",
                     "fields": [field_dict(Field("meter_value", "Meter reading now (optional)", "number"))]}
    return forms


__all__ = ["RECORDS", "EQUIPMENT_ACTIONS", "form_spec", "show"]
