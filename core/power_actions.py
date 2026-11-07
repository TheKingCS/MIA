"""
core.power_actions
====================

Every change the Power screen makes (2026-11-07, DEC-0125: Power on the
phone), as action kinds on the contract in core/actions.py: an energy
source (solar, a generator, propane...) added, edited or deleted, from one
table (core/record_actions.py), and `energy.reading`, a reading logged by
hand on one of its meters (no sensors yet: core/energy_manager.py). The
sources write through atomic_write_text and the readings go through the
Data Logger, so "undo that" takes either back.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionType, _need
from core.energy_manager import ENERGY_SOURCE_TYPES
from core.record_actions import Field, Record, field_dict, get, parse, record_form, record_kinds

SOURCE = Record("energy_source", "energy source", "source_id", "get_energy_source", "add_energy_source",
                "update_energy_source", "delete_energy_source", store="energy",
                delete_note="Its readings stay in the Data Logger.", fields=(
                    Field("name", "Name", "text", True),
                    Field("source_type", "Kind", "choice", options=tuple(ENERGY_SOURCE_TYPES), default="Other",
                          say="kind", quiet_default=True),
                    Field("notes", "Notes", "textarea"),
                ))

_METER = Field("meter_name", "Meter", "text", True, say="meter")
_VALUE = Field("value", "Reading", "number", True)
_UNIT = Field("unit", "Unit (%, kWh, gal...)", "text")
_NOTE = Field("note", "Note", "textarea")


def _describe_reading(context, params) -> str:
    """The sentence the approval card shows for `energy.reading` (Propose); raises ActionError when it can't be done."""
    source = get(context, SOURCE, params)
    meter, value, unit = parse(_METER, params.get("meter_name")), parse(_VALUE, params.get("value")), parse(_UNIT, params.get("unit"))
    return f"Log {meter} {value:g}{(' ' + unit) if unit else ''} on {source.name}"


def _log_reading(context, params) -> str:
    """Does `energy.reading` once approved, and says what happened. The reading goes on the source's own meter."""
    source = get(context, SOURCE, params)
    meter, value = parse(_METER, params.get("meter_name")), parse(_VALUE, params.get("value"))
    _need(context, "data_logger")
    context.energy.log_energy_reading(source.source_id, meter, value, unit=parse(_UNIT, params.get("unit")),
                                      note=parse(_NOTE, params.get("note")))
    return f"Logged {meter} on {source.name}."


POWER_ACTIONS: dict[str, ActionType] = {k.kind: k for k in record_kinds(SOURCE) + [
    ActionType("energy.reading", "Log reading", {"source_id": "the energy source", "meter_name": "e.g. Fuel",
                                                 "value": "the reading", "unit": "optional", "note": "optional"},
               _describe_reading, _log_reading),
]}
ACTION_TYPES.update(POWER_ACTIONS)


def form_spec() -> dict:
    """The Power screen's forms: an energy source, and a reading."""
    return {"source": record_form(SOURCE), "reading": [field_dict(f) for f in (_METER, _VALUE, _UNIT, _NOTE)]}
