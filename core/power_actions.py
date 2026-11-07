"""
core.power_actions
====================

Power's changes on the web (DEC-0113 canvas, DEC-0125 parity: Power had no
phone screen). Energy sources (solar, a generator, propane, a battery bank)
are added, renamed and removed through the shared record kinds
(`energy_source.add` / `.edit` / `.delete`, core/record_actions.py), and a
reading is logged with `energy.reading` ("tank 62 %", "3.8 kWh today"),
written through core/energy_manager.py into the Data Logger like every
reading. Entered by hand: no sensors are connected yet.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.energy_manager import ENERGY_SOURCE_TYPES
from core.record_actions import Field, Record, record_form, record_kinds

ENERGY_SOURCE = Record(
    "energy_source", "energy source", "source_id", "get_energy_source", "add_energy_source", "update_energy_source",
    "delete_energy_source", store="energy",
    delete_note="Its readings are kept in the history.", fields=(
        Field("name", "Name", "text", True),
        Field("source_type", "Kind", "choice", options=tuple(ENERGY_SOURCE_TYPES), default="Other", say="kind",
              quiet_default=True),
        Field("notes", "Notes", "textarea"),
    ))


def _source(context, params):
    """The energy source named by source_id, or ActionError."""
    store = _need(context, "energy")
    found = store.get_energy_source(str(params.get("source_id") or ""))
    if found is None:
        raise ActionError("That energy source isn't here any more.")
    return found


def _value(params) -> float:
    """The reading's number, or ActionError."""
    try:
        return float(str(params.get("value") or "").replace(",", "").strip())
    except ValueError:
        raise ActionError("What does it read? Give a number.") from None


def _describe_reading(context, params) -> str:
    """The sentence the approval card shows for `energy.reading` (Propose); ActionError when it can't be done."""
    source = _source(context, params)
    meter = str(params.get("meter") or "").strip() or "Level"
    unit = str(params.get("unit") or "").strip()
    return f"Log {_value(params):g}{(' ' + unit) if unit else ''} for {source.name} ({meter})"


def _reading(context, params) -> str:
    """Does `energy.reading` once approved: one reading on the source's meter, kept in the Data Logger."""
    source = _source(context, params)
    meter = str(params.get("meter") or "").strip() or "Level"
    unit = str(params.get("unit") or "").strip()
    try:
        _need(context, "energy").log_energy_reading(source.source_id, meter, _value(params), unit,
                                                    str(params.get("note") or "").strip())
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"Logged {_value(params):g}{(' ' + unit) if unit else ''} for {source.name}."


READING_FIELDS = [
    {"name": "meter", "label": "What it measures (Level, kWh today, Fuel...)", "type": "text", "required": False,
     "options": [], "default": "Level"},
    {"name": "value", "label": "Reading", "type": "number", "required": True, "options": [], "default": None},
    {"name": "unit", "label": "Unit (%, kWh, gal...)", "type": "text", "required": False, "options": [], "default": "%"},
    {"name": "note", "label": "Note (optional)", "type": "text", "required": False, "options": [], "default": None},
]

_KINDS = record_kinds(ENERGY_SOURCE) + [
    ActionType("energy.reading", "Log Reading", {"source_id": "the source", "meter": "what it measures",
                                                 "value": "the reading", "unit": "optional", "note": "optional"},
               _describe_reading, _reading),
]
POWER_ACTIONS = {k.kind: k for k in _KINDS}
ACTION_TYPES.update(POWER_ACTIONS)


def forms() -> dict:
    """The forms Power's screen shows: an energy source, and a reading."""
    return {"energy_source": record_form(ENERGY_SOURCE), "reading": {"fields": READING_FIELDS}}
