"""
core.lab_reading_actions
==========================

The Lab's changes on the web (DEC-0113 canvas Lab, DEC-0125: the Lab had no
phone screen). `lab_reading.add` logs a reading to a series in the Data
Logger (core/data_logger_manager.py), joining an existing series whatever its
case and starting a new one with its first reading; `lab_reading.delete`
takes one out. A reading on a series another app writes (Power's sources,
Garage's meters) is changed there, not here. ("lab.*" is the development
lab's, core/lab_actions.py.)
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _value(params) -> float:
    """The reading's number, or ActionError."""
    try:
        return float(str(params.get("value") or "").replace(",", "").strip())
    except ValueError:
        raise ActionError("What does it read? Give a number.") from None


def _series(context, params) -> str:
    """The series to log to (an existing one whatever its case), or ActionError; never another app's."""
    from core.web_lab import owner_of, resolve_series

    logger = _need(context, "data_logger")
    wanted = str(params.get("series") or "").strip()
    if not wanted:
        raise ActionError("Which series? Give it a name, like Soil moisture.")
    series = resolve_series(logger.list_series(), wanted)
    if owner_of(series):
        raise ActionError(f"That series is {owner_of(series)[1]}'s; log it there.")
    return series


def _unit(params) -> str:
    """The unit typed, trimmed."""
    return str(params.get("unit") or "").strip()


def _describe_add(context, params) -> str:
    """The sentence the approval card shows for `lab_reading.add`; ActionError when it can't be done."""
    unit = _unit(params)
    return f"Log {_value(params):g}{(' ' + unit) if unit else ''} to {_series(context, params)}"


def _add(context, params) -> str:
    """Does `lab_reading.add` once approved."""
    series, unit = _series(context, params), _unit(params)
    value = _value(params)
    _need(context, "data_logger").add_reading(series, value, unit=unit, note=str(params.get("note") or "").strip())
    return f"Logged {value:g}{(' ' + unit) if unit else ''} to {series}."


def _reading(context, params):
    """The reading named by reading_id, or ActionError; another app's readings are changed there."""
    from core.web_lab import owner_of

    logger = _need(context, "data_logger")
    rid = str(params.get("reading_id") or "")
    for sid in logger.list_series():
        for r in logger.readings_for(sid):
            if r.reading_id == rid:
                if owner_of(sid):
                    raise ActionError(f"That reading is {owner_of(sid)[1]}'s; change it there.")
                return r
    raise ActionError("That reading isn't here any more.")


def _describe_delete(context, params) -> str:
    """The sentence for `lab_reading.delete`."""
    r = _reading(context, params)
    return f"Delete the reading {r.value:g}{(' ' + r.unit) if r.unit else ''} from {r.series_id} ({str(r.timestamp)[:16].replace('T', ' ')})"


def _delete(context, params) -> str:
    """Does `lab_reading.delete`."""
    r = _reading(context, params)
    _need(context, "data_logger").delete_reading(r.reading_id)
    return f"Deleted the reading from {r.series_id}."


READING_FIELDS = [
    {"name": "series", "label": "Series (Soil moisture, Tank pH...)", "type": "text", "required": True, "options": [],
     "default": None},
    {"name": "value", "label": "Reading", "type": "number", "required": True, "options": [], "default": None},
    {"name": "unit", "label": "Unit (°C, %, pH...)", "type": "text", "required": False, "options": [], "default": None},
    {"name": "note", "label": "Note (optional)", "type": "text", "required": False, "options": [], "default": None},
]

_KINDS = [
    ActionType("lab_reading.add", "Log Reading", {"series": "the series", "value": "the reading", "unit": "optional",
                                                  "note": "optional"}, _describe_add, _add),
    ActionType("lab_reading.delete", "Delete Reading", {"reading_id": "the reading"}, _describe_delete, _delete),
]
LAB_READING_ACTIONS = {k.kind: k for k in _KINDS}
ACTION_TYPES.update(LAB_READING_ACTIONS)
