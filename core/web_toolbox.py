"""
core.web_toolbox
==================

The Toolbox's web screen (DEC-0113 canvas Toolbox, DEC-0125: the Toolbox had
no phone screen). Three parts:

- **Calculators**: Ohm's law, the unit converter, board feet and concrete
  volume, each with the fields its form shows. calc() works one out from the
  form's values (core/toolbox_calcs.py, core/unit_conversion.py), so the web
  never does the math, and its answer reads like the voice tool's.
- **Alarms**: each alarm with its time, repeat and whether it's on; setting,
  switching and deleting one are actions (core/toolbox_actions.py).
- **Tools**: the Toolbox's other tools and where each one is on the web
  (the calendar has its own page; the stopwatch runs on the page itself;
  inventory stays on the PC).
"""

from __future__ import annotations

from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)


def _f(name, label, kind="number", default=None, options=(), required=False):
    """One form field, in the shape the web's forms take."""
    return {"name": name, "label": label, "type": kind, "required": required, "options": list(options),
            "default": default}


def _unit_fields() -> list:
    """The unit converter's fields: the category and each category's units (the page narrows the lists)."""
    from core.unit_conversion import UNIT_CATEGORIES

    return [_f("category", "Kind", "choice", "Length", list(UNIT_CATEGORIES)), _f("value", "Amount", default=1),
            _f("from_unit", "From", "choice", "Feet (ft)"), _f("to_unit", "To", "choice", "Meters (m)")]


def calculators() -> list:
    """Every calculator the screen offers: id, name, what it does, its fields, and a worked example."""
    from core.unit_conversion import UNIT_CATEGORIES

    return [
        {"id": "ohms_law", "name": "Ohm's Law", "category": "Electronics",
         "about": "Any two of voltage, current and resistance give the third, and the power.",
         "fields": [_f("volts", "Volts (V)", default=12), _f("ohms", "Ohms (Ω)", default=220), _f("amps", "Amps (A)")],
         "example": {"volts": 12, "ohms": 220}},
        {"id": "unit_converter", "name": "Unit Converter", "category": "General",
         "about": "Length, area, volume, weight, temperature, speed, pressure, energy, power, time, data, angle and "
                  "fuel economy.",
         "fields": _unit_fields(), "units": {c: list(u) for c, u in UNIT_CATEGORIES.items()},
         "example": {"category": "Volume", "value": 5, "from_unit": "US Gallons (gal)", "to_unit": "Liters (L)"}},
        {"id": "board_feet", "name": "Board Feet", "category": "Woodworking",
         "about": "Nominal thickness × width in inches × length in feet ÷ 12, times how many.",
         "fields": [_f("thickness_in", "Thickness (in)", default=2), _f("width_in", "Width (in)", default=4),
                    _f("length_ft", "Length (ft)", default=8), _f("count", "How many", default=1)],
         "example": {"thickness_in": 2, "width_in": 6, "length_ft": 8, "count": 10}},
        {"id": "concrete", "name": "Concrete Volume", "category": "Building",
         "about": "A slab or pad in cubic yards with 10% extra, and the bags of premix.",
         "fields": [_f("length_ft", "Length (ft)", default=10), _f("width_ft", "Width (ft)", default=10),
                    _f("thickness_in", "Thickness (in)", default=4)],
         "example": {"length_ft": 10, "width_ft": 10, "thickness_in": 4}},
    ]


def _num(params: dict, name: str, required: bool = True) -> Optional[float]:
    """A number from the form, None when left blank and allowed; ValueError otherwise."""
    raw = params.get(name)
    if raw is None or str(raw).strip() == "":
        if required:
            raise ValueError("Fill in every box.")
        return None
    try:
        return float(str(raw).replace(",", "").strip())
    except ValueError:
        raise ValueError(f"{raw} isn't a number.") from None


def calc(calc_id: str, params: dict) -> dict:
    """Pure logic. One calculator worked out from the form's values: {answer (the main line), lines (label, value)
    pairs, note}; {error} in plain words when the values don't work (never raises)."""
    from core.toolbox_calcs import board_feet, concrete_volume, ohms_law
    from core.unit_conversion import UNIT_CATEGORIES, convert

    try:
        if calc_id == "ohms_law":
            r = ohms_law(_num(params, "volts", False), _num(params, "amps", False), _num(params, "ohms", False))
            names = {"volts": "Voltage", "amps": "Current", "ohms": "Resistance"}
            return {"answer": f"{names[r['solved']]}: {r['text'][r['solved']]}", "solved": r["solved"],
                    "lines": [[names[k], r["text"][k]] for k in ("volts", "amps", "ohms")] + [["Power", r["text"]["watts"]]],
                    "note": ""}
        if calc_id == "unit_converter":
            category = str(params.get("category") or "")
            units = UNIT_CATEGORIES.get(category)
            a, b = str(params.get("from_unit") or ""), str(params.get("to_unit") or "")
            if units is None or a not in units or b not in units:
                return {"error": "Pick a kind and two of its units."}
            value = _num(params, "value")
            out = convert(category, a, b, value)
            return {"answer": f"{value:g} {_short(a)} = {out:.6g} {_short(b)}", "lines": [], "note": ""}
        if calc_id == "board_feet":
            r = board_feet(_num(params, "thickness_in"), _num(params, "width_in"), _num(params, "length_ft"),
                           _num(params, "count", False) or 1)
            return {"answer": r["text"], "lines": [["Each", f"{r['each']:g} bd ft"], ["Total", f"{r['total']:g} bd ft"]],
                    "note": "Priced by the board foot? Multiply the total by the price."}
        if calc_id == "concrete":
            r = concrete_volume(_num(params, "length_ft"), _num(params, "width_ft"), _num(params, "thickness_in"))
            return {"answer": f"{r['cubic_yd']:g} cu yd", "lines": [["Cubic feet", f"{r['cubic_ft']:g}"],
                    ["80 lb bags", str(r["bags_80"])], ["60 lb bags", str(r["bags_60"])]], "note": r["note"]}
    except ValueError as problem:
        return {"error": str(problem)}
    return {"error": "There's no calculator by that name."}


def _short(unit_key: str) -> str:
    """Pure logic. A unit's short name from its display key: "Feet (ft)" -> "ft"; the key itself without one."""
    if "(" in unit_key and unit_key.endswith(")"):
        return unit_key[unit_key.index("(") + 1:-1]
    return unit_key


def _alarms(context) -> list:
    """Every alarm for the screen: id, label, time, repeat in a word, on or off; earliest first."""
    from core.toolbox_actions import repeat_word

    store = getattr(context, "alarms", None)
    if store is None:
        return []
    try:
        alarms = store.all_alarms()
    except Exception:
        log.exception("Toolbox: alarms read failed")
        return []
    return [{"id": a.alarm_id, "label": a.label, "time": a.time, "repeat": repeat_word(a.days), "on": bool(a.enabled)}
            for a in sorted(alarms, key=lambda a: a.time)]


def _tools(context) -> list:
    """The Toolbox's other tools and where each is on the web: a page, this page, or the PC."""
    inventory = getattr(context, "inventory", None)
    try:
        items = len(inventory.all_items()) if inventory is not None else 0
    except Exception:
        items = 0
    return [
        {"id": "stopwatch", "name": "Stopwatch", "note": "Start, lap and reset, right here.", "where": "here"},
        {"id": "calendar", "name": "Calendar", "note": "Everything with a date.", "where": "calendar.html"},
        {"id": "inventory", "name": "Inventory", "note": (f"{items} items. " if items else "") + "On the PC, or ask MIA.",
         "where": "pc", "ask": "What's in my inventory?"},
    ]


def toolbox_page(context) -> dict:
    """The Toolbox screen's data: the calculators, the alarms and their form, and the other tools."""
    from core.toolbox_actions import ALARM_FIELDS

    alarms = _alarms(context)
    return {"available": True, "calculators": calculators(), "alarms": alarms,
            "alarms_on": sum(1 for a in alarms if a["on"]), "can_alarm": getattr(context, "alarms", None) is not None,
            "forms": {"alarm": {"fields": ALARM_FIELDS}}, "tools": _tools(context)}
