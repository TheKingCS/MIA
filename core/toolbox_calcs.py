"""
core.toolbox_calcs
====================

The Toolbox's calculators as pure math (DEC-0113 canvas Toolbox, DEC-0125:
the same answer by voice, on the PC and on the phone). Ohm's law (solve()
moved here from modules/toolbox/calculators/ohms_law.py, which re-exports
it), Ohm's law from any two of the three, board feet and concrete volume.
Unit conversion lives in core/unit_conversion.py.

Every result comes back with a reading in words in sensible units ("54.5
mA", "1.2 kΩ"), so the web, the Qt calculator and the voice tool say the
same thing. Pure logic: no I/O.
"""

from __future__ import annotations

import math
from typing import Optional

from core.build_calcs import BAG_80LB_CUFT, WASTE

BAG_60LB_CUFT = 0.45  # premixed concrete yield of a 60 lb bag
_PREFIXES = ((1e9, "G"), (1e6, "M"), (1e3, "k"), (1.0, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"))


def solve(solve_for: str, voltage: float | None, current: float | None, resistance: float | None) -> float:
    """Pure logic. Solves V = I × R for whichever of the three `solve_for` names; the other two must be given."""
    if solve_for == "voltage":
        return current * resistance
    if solve_for == "current":
        return voltage / resistance
    if solve_for == "resistance":
        return voltage / current
    raise ValueError(f"Unknown solve_for: {solve_for!r}")


def si(value: float, unit: str) -> str:
    """Pure logic. A value with a metric prefix that keeps it between 1 and 1000: 0.0545 A -> "54.5 mA",
    1200 Ω -> "1.2 kΩ", 0 -> "0 V"."""
    if value == 0 or not math.isfinite(value):
        return f"{value:g} {unit}"
    size = abs(value)
    for factor, prefix in _PREFIXES:
        if size >= factor * 0.9995:
            return f"{value / factor:.3g} {prefix}{unit}"
    factor, prefix = _PREFIXES[-1]
    return f"{value / factor:.3g} {prefix}{unit}"


def ohms_law(volts: Optional[float] = None, amps: Optional[float] = None, ohms: Optional[float] = None) -> dict:
    """Pure logic. Ohm's law from any two of volts, amps and ohms: all three and the power, each as a number and in
    words, and which one was worked out. ValueError without exactly two, or when it would divide by zero."""
    given = {k: v for k, v in (("volts", volts), ("amps", amps), ("ohms", ohms)) if v is not None}
    if len(given) != 2:
        raise ValueError("Give any two of volts, current and resistance.")
    try:
        if volts is None:
            volts, solved = amps * ohms, "volts"
        elif amps is None:
            amps, solved = volts / ohms, "amps"
        else:
            ohms, solved = volts / amps, "ohms"
    except ZeroDivisionError:
        raise ValueError("That would divide by zero: resistance or current can't be 0.") from None
    watts = volts * amps
    return {"volts": volts, "amps": amps, "ohms": ohms, "watts": watts, "solved": solved,
            "text": {"volts": si(volts, "V"), "amps": si(amps, "A"), "ohms": si(ohms, "Ω"), "watts": si(watts, "W")}}


def board_feet(thickness_in: float, width_in: float, length_ft: float, count: float = 1) -> dict:
    """Pure logic. Board feet of lumber (nominal inches × inches × feet ÷ 12, times how many): the total and per
    board. ValueError for a size of 0 or less."""
    if min(thickness_in, width_in, length_ft, count) <= 0:
        raise ValueError("Every size and the count must be more than 0.")
    each = thickness_in * width_in * length_ft / 12
    total = each * count
    return {"each": round(each, 2), "total": round(total, 2),
            "text": f"{total:.4g} board feet" + (f" ({each:.3g} each)" if count != 1 else "")}


def concrete_volume(length_ft: float, width_ft: float, thickness_in: float) -> dict:
    """Pure logic. Concrete for a slab or pad: cubic feet and yards with 10% extra (build_calcs.WASTE), and how many
    80 lb or 60 lb bags of premix that is. ValueError for a size of 0 or less."""
    if min(length_ft, width_ft, thickness_in) <= 0:
        raise ValueError("Length, width and thickness must be more than 0.")
    cubic_ft = length_ft * width_ft * thickness_in / 12 * (1 + WASTE)
    yards = cubic_ft / 27
    bags_80, bags_60 = math.ceil(cubic_ft / BAG_80LB_CUFT), math.ceil(cubic_ft / BAG_60LB_CUFT)
    return {"cubic_ft": round(cubic_ft, 2), "cubic_yd": round(yards, 2), "bags_80": bags_80, "bags_60": bags_60,
            "text": f"{yards:.2f} cu yd ({cubic_ft:.1f} cu ft), or {bags_80} bags of 80 lb mix",
            "note": "Includes 10% extra. Over about a cubic yard, ready-mix delivery is usually easier than bags."
            if yards > 1 else "Includes 10% extra."}
