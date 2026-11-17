"""
core.quantities
=================

Numbers with their units, for MIA's engineering calculators (the local
specialists plan, S0a; DEC-0197).

What it is: a `Quantity` is a value and what it measures. Arithmetic keeps
track of the units, so adding metres to feet converts, adding metres to
volts is an error, and volts times amps comes out as watts. A specialist's
numbers go wrong most often at the units, and here that is a refusal, not
a wrong answer.

How it works: every unit is a factor times a product of five base
dimensions (length, mass, time, current, temperature). `q(12, "V")` makes a
quantity; `.to("mV")` converts; `+ - * /` combine; `parse("12 V")` reads
one from text ("1,500 W" is fifteen hundred; "2,5 mm" is two and a half). Temperatures in °C and °F are differences in arithmetic and
are converted as points only by `temperature()`.

Pure logic: no I/O. The everyday unit converter stays
`core/unit_conversion.py`; this is for calculations.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# Dimensions as exponents of (length m, mass kg, time s, current A, temperature K).
_NONE = (0, 0, 0, 0, 0)
_L, _M, _T, _I, _K = (1, 0, 0, 0, 0), (0, 1, 0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 1, 0), (0, 0, 0, 0, 1)
_VOLT, _WATT, _OHM = (2, 1, -3, -1, 0), (2, 1, -3, 0, 0), (2, 1, -3, -2, 0)
_JOULE, _COULOMB, _FARAD = (2, 1, -2, 0, 0), (0, 0, 1, 1, 0), (-2, -1, 4, 2, 0)

# unit -> (factor to SI, dimension)
UNITS: dict[str, tuple[float, tuple]] = {
    "": (1.0, _NONE), "%": (0.01, _NONE),
    "m": (1.0, _L), "mm": (1e-3, _L), "cm": (1e-2, _L), "km": (1e3, _L), "in": (0.0254, _L), "ft": (0.3048, _L),
    "yd": (0.9144, _L), "mi": (1609.344, _L),
    "kg": (1.0, _M), "g": (1e-3, _M), "lb": (0.45359237, _M), "oz": (0.028349523125, _M),
    "s": (1.0, _T), "ms": (1e-3, _T), "min": (60.0, _T), "h": (3600.0, _T), "day": (86400.0, _T),
    "A": (1.0, _I), "mA": (1e-3, _I), "uA": (1e-6, _I),
    "V": (1.0, _VOLT), "mV": (1e-3, _VOLT), "kV": (1e3, _VOLT),
    "W": (1.0, _WATT), "mW": (1e-3, _WATT), "kW": (1e3, _WATT),
    "ohm": (1.0, _OHM), "kohm": (1e3, _OHM), "Mohm": (1e6, _OHM),
    "J": (1.0, _JOULE), "Wh": (3600.0, _JOULE), "kWh": (3.6e6, _JOULE),
    "Ah": (3600.0, _COULOMB), "mAh": (3.6, _COULOMB),
    "F": (1.0, _FARAD), "uF": (1e-6, _FARAD), "nF": (1e-9, _FARAD),
    "Hz": (1.0, (0, 0, -1, 0, 0)), "kHz": (1e3, (0, 0, -1, 0, 0)), "MHz": (1e6, (0, 0, -1, 0, 0)),
    "K": (1.0, _K), "degC": (1.0, _K), "degF": (5.0 / 9.0, _K),  # as differences
    "m2": (1.0, (2, 0, 0, 0, 0)), "ft2": (0.09290304, (2, 0, 0, 0, 0)),
    "m3": (1.0, (3, 0, 0, 0, 0)), "L": (1e-3, (3, 0, 0, 0, 0)), "mL": (1e-6, (3, 0, 0, 0, 0)),
    "gal": (3.785411784e-3, (3, 0, 0, 0, 0)), "ft3": (0.028316846592, (3, 0, 0, 0, 0)),
    # Flows and the greenhouse's heat (the greenhouse specialist, S4): BTU per hour is a power; a U-value is a power
    # per area per degree.
    "BTU/h": (0.29307107, _WATT), "m3/s": (1.0, (3, 0, -1, 0, 0)), "cfm": (4.719474432e-4, (3, 0, -1, 0, 0)),
    "gpm": (6.30901964e-5, (3, 0, -1, 0, 0)), "gph": (1.051503273e-6, (3, 0, -1, 0, 0)),
    "W/m2K": (1.0, (0, 1, -3, 0, -1)), "BTU/h/ft2/degF": (5.678263337, (0, 1, -3, 0, -1)),
    "N": (1.0, (1, 1, -2, 0, 0)), "Pa": (1.0, (-1, 1, -2, 0, 0)), "psi": (6894.757293168, (-1, 1, -2, 0, 0)),
    "degC/W": (1.0, (-2, -1, 3, 0, 1)),
}
_ALIASES = {"Ω": "ohm", "ohms": "ohm", "kΩ": "kohm", "MΩ": "Mohm", "µA": "uA", "µF": "uF", "°C": "degC", "°F": "degF",
            "volt": "V", "volts": "V", "amp": "A", "amps": "A", "watt": "W", "watts": "W", "feet": "ft", "foot": "ft",
            "inch": "in", "inches": "in", "hr": "h", "hours": "h", "hour": "h", "sec": "s", "percent": "%",
            "ml": "mL", "millilitre": "mL", "millilitres": "mL", "milliliter": "mL", "milliliters": "mL",
            "litre": "L", "litres": "L", "liter": "L", "liters": "L", "l": "L", "Btu/h": "BTU/h", "btu/h": "BTU/h",
            "BTU/hr": "BTU/h", "Btu/hr": "BTU/h", "btuh": "BTU/h", "CFM": "cfm", "GPM": "gpm", "GPH": "gph",
            "cu ft": "ft3", "sq ft": "ft2", "ft²": "ft2", "m²": "m2", "ft³": "ft3"}
_TEXT = re.compile(r"^\s*(-?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")
_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")


class UnitError(ValueError):
    """Units that don't go together, or a unit MIA doesn't know; its message is a plain sentence."""


def unit_of(name: str) -> str:
    """Pure logic. A unit's own name from how it was written (Ω, volts, °C...). UnitError for one MIA doesn't
    know."""
    name = str(name or "").strip()
    name = _ALIASES.get(name, _ALIASES.get(name.lower(), name))
    if name not in UNITS:
        raise UnitError(f"I don't know the unit \"{name}\".")
    return name


@dataclass(frozen=True)
class Quantity:
    """A value in SI base units with its dimension, and the unit it's shown in. Made with `q()`."""
    si: float
    dim: tuple
    unit: str = ""

    @property
    def value(self) -> float:
        """The value in the unit it's shown in."""
        return self.si / UNITS[self.unit][0] if self.unit in UNITS and UNITS[self.unit][1] == self.dim else self.si

    def to(self, unit: str) -> "Quantity":
        """The same quantity shown in another unit. UnitError when that unit measures something else."""
        unit = unit_of(unit)
        if UNITS[unit][1] != self.dim:
            raise UnitError(f"{self.unit or 'a plain number'} can't be given in {unit}: they measure different things.")
        return Quantity(self.si, self.dim, unit)

    def number(self, unit: str) -> float:
        """The value as a plain number in a unit."""
        return self.to(unit).value

    def _same(self, other: "Quantity", doing: str) -> None:
        """UnitError unless the other measures the same thing."""
        if not isinstance(other, Quantity) or other.dim != self.dim:
            theirs = other.unit if isinstance(other, Quantity) else "a plain number"
            raise UnitError(f"Can't {doing} {self.unit or 'a plain number'} and {theirs or 'a plain number'}.")

    def __add__(self, other):
        """Adds two of the same kind, in this one's unit."""
        self._same(other, "add")
        return Quantity(self.si + other.si, self.dim, self.unit)

    def __sub__(self, other):
        """Subtracts one of the same kind, in this one's unit."""
        self._same(other, "subtract")
        return Quantity(self.si - other.si, self.dim, self.unit)

    def __mul__(self, other):
        """Times a number or another quantity; the units multiply (volts times amps is watts)."""
        if isinstance(other, Quantity):
            return _named(self.si * other.si, tuple(a + b for a, b in zip(self.dim, other.dim)))
        return Quantity(self.si * float(other), self.dim, self.unit)

    __rmul__ = __mul__

    def __truediv__(self, other):
        """Divided by a number or another quantity; the units divide."""
        if isinstance(other, Quantity):
            if other.si == 0:
                raise UnitError("That would divide by zero.")
            return _named(self.si / other.si, tuple(a - b for a, b in zip(self.dim, other.dim)))
        if float(other) == 0:
            raise UnitError("That would divide by zero.")
        return Quantity(self.si / float(other), self.dim, self.unit)

    def __lt__(self, other):
        """Smaller than another of the same kind."""
        self._same(other, "compare")
        return self.si < other.si

    def __le__(self, other):
        """Smaller than or equal to another of the same kind."""
        self._same(other, "compare")
        return self.si <= other.si

    def close_to(self, other: "Quantity", within: float = 0.02) -> bool:
        """Whether another of the same kind is within a fraction of this one (2% by default)."""
        if not isinstance(other, Quantity) or other.dim != self.dim:
            return False
        return math.isclose(self.si, other.si, rel_tol=within, abs_tol=1e-12)

    def __str__(self) -> str:
        """The value and unit, to four significant figures: "13.5 A"."""
        shown = float(f"{self.value:.4g}")  # four significant figures, written out plainly (10000, not 1e+04)
        text = f"{shown:,.12g}" if 1e-4 <= abs(shown) < 1e9 or shown == 0 else f"{shown:.4g}"
        return f"{text} {self.unit}".strip()


# The unit a result is shown in when multiplying or dividing gives this dimension.
_SHOW = {_NONE: "", _L: "m", _M: "kg", _T: "s", _I: "A", _K: "K", _VOLT: "V", _WATT: "W", _OHM: "ohm", _JOULE: "J",
         _COULOMB: "Ah", _FARAD: "F", (2, 0, 0, 0, 0): "m2", (3, 0, 0, 0, 0): "m3", (0, 0, -1, 0, 0): "Hz",
         (-2, -1, 3, 0, 1): "degC/W"}


def _named(si: float, dim: tuple) -> Quantity:
    """A result with the usual unit for its dimension (none known: shown in SI with no unit name)."""
    return Quantity(si, dim, _SHOW.get(dim, ""))


def q(value: float, unit: str = "") -> Quantity:
    """A quantity from a number and a unit. UnitError for a unit MIA doesn't know or a value that isn't a number."""
    unit = unit_of(unit)
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise UnitError(f"\"{value}\" isn't a number.") from None
    if not math.isfinite(value):
        raise UnitError("That isn't a finite number.")
    factor, dim = UNITS[unit]
    return Quantity(value * factor, dim, unit)


def parse(text: str) -> Quantity:
    """A quantity from text like "12 V", "2.5mm" or "40": UnitError when it doesn't read."""
    found = _TEXT.match(str(text or ""))
    if not found:
        raise UnitError(f"I can't read \"{text}\" as a number with a unit.")
    number = found.group(1)
    if _THOUSANDS.match(number):
        number = number.replace(",", "")  # 1,500 is fifteen hundred
    elif number.count(",") == 1 and "." not in number:
        number = number.replace(",", ".")  # 2,5 is two and a half
    elif "," in number:
        raise UnitError(f"I can't read \"{text}\" as a number with a unit.")
    return q(float(number), found.group(2))


def temperature(value: float, unit: str, to: str) -> float:
    """A temperature as a point on one scale given on another (degC, degF, K), unlike a difference."""
    unit, to = unit_of(unit), unit_of(to)
    if "K" != unit and not unit.startswith("deg") or "K" != to and not to.startswith("deg"):
        raise UnitError("Temperatures are in degC, degF or K.")
    kelvin = {"K": value, "degC": value + 273.15, "degF": (value - 32) * 5 / 9 + 273.15}[unit]
    return {"K": kelvin, "degC": kelvin - 273.15, "degF": (kelvin - 273.15) * 9 / 5 + 32}[to]
