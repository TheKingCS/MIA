"""
core.product_specs
====================

Products compared by their real specifications, not their titles (Procurement P2, DEC-0172; the proposal's section
5). Everything here is pure code: a model never decides whether two things are the same.

**Categories** (`CATEGORIES`): each kind of product has the few specifications that decide whether it does the job,
each with how it's compared: `min` (at least what's needed: a pump's flow), `max` (at most: a fan's noise), or `eq`
(must match: volts, a board's nominal size). A category is found from the words (`category_of`).

**Reading** (`read`): numbers with their units from a listing's or a need's text, normalised: gallons per hour,
feet of head, watts, volts, CFM, inches, feet, millimetres (a "mil" is 0.0254 mm), a board's nominal size (2x4),
pipe schedule, and yes/no words (treated, submersible, UV). A value that isn't in the text is unknown, never guessed.

**The verdict** (`verdict`), for a product against what's needed:
- `identical`: the same model number (a token of letters and digits both name);
- `equivalent`: every specification the need states is met;
- `similar`: same category, but a stated specification is unknown in the product;
- `not suitable`: a stated specification fails (two pumps with the same watts and less flow at the head needed).
Each comes with its reasons, one per specification, and what's unknown.
"""

from __future__ import annotations

import re
from typing import Optional

# category -> (words that mark it, {field: comparison})
CATEGORIES: dict[str, tuple[tuple[str, ...], dict[str, str]]] = {
    "pump": (("pump",), {"flow_gph": "min", "head_ft": "min", "volts": "eq", "submersible": "eq"}),
    "fan": (("fan", "ventilator", "exhaust"), {"cfm": "min", "size_in": "eq", "volts": "eq"}),
    "lumber": (("lumber", "stud", "board", "2x", "4x4", "plank", "joist"), {"nominal": "eq", "length_ft": "min",
                                                                          "treated": "eq"}),
    "pipe": (("pipe", "pvc", "conduit", "tubing"), {"diameter_in": "eq", "schedule": "eq", "length_ft": "min"}),
    "panel": (("polycarbonate", "panel", "film", "glazing", "sheet", "poly"), {"thickness_mm": "min",
                                                                             "width_ft": "min", "uv": "eq"}),
    "sensor": (("sensor", "probe", "thermometer", "hygrometer"), {"measures": "eq", "interface": "eq",
                                                                  "volts": "eq"}),
    "solar": (("solar", "photovoltaic", "pv module"), {"watts": "min", "volts": "eq"}),
}
NAMES = {"flow_gph": "flow", "head_ft": "head", "volts": "volts", "submersible": "submersible", "cfm": "airflow",
         "size_in": "size", "nominal": "size", "length_ft": "length", "treated": "treated", "diameter_in": "diameter",
         "schedule": "schedule", "thickness_mm": "thickness", "width_ft": "width", "uv": "UV rated",
         "measures": "measures", "interface": "interface", "watts": "watts"}

_NUM = r"(\d+(?:\.\d+)?)"
_PATTERNS = (
    ("flow_gph", re.compile(_NUM + r"\s*(?:gph|gal(?:lons?)?\s*(?:per|/)\s*h(?:ou)?r)", re.I), 1.0),
    ("flow_gph", re.compile(_NUM + r"\s*(?:gpm|gal(?:lons?)?\s*(?:per|/)\s*min(?:ute)?)", re.I), 60.0),
    ("head_ft", re.compile(r"(?:head|lift)\D{0,12}?" + _NUM + r"\s*(?:ft|feet|')", re.I), 1.0),
    ("head_ft", re.compile(_NUM + r"\s*(?:ft|feet|')\s*(?:of\s*)?(?:head|lift)", re.I), 1.0),
    ("watts", re.compile(_NUM + r"\s*(?:w|watts?)\b", re.I), 1.0),
    ("volts", re.compile(_NUM + r"\s*(?:v|volts?|vac|vdc)\b", re.I), 1.0),
    ("cfm", re.compile(_NUM + r"\s*cfm\b", re.I), 1.0),
    ("thickness_mm", re.compile(_NUM + r"\s*mm\b", re.I), 1.0),
    ("thickness_mm", re.compile(_NUM + r"\s*mils?\b", re.I), 0.0254),
    ("schedule", re.compile(r"(?:sch(?:edule)?\.?)\s*(40|80)\b", re.I), 1.0),
    ("diameter_in", re.compile(_NUM + r"\s*(?:in(?:ch(?:es)?)?\b|\")\s*(?:pvc|pipe|diameter|dia)", re.I), 1.0),
    ("size_in", re.compile(_NUM + r"\s*(?:in(?:ch(?:es)?)?\b|\")\s*(?:fan|blade|shutter|exhaust)", re.I), 1.0),
    ("length_ft", re.compile(r"\bx\s*" + _NUM + r"\s*(?:ft|feet|foot|')", re.I), 1.0),  # "2x4 x 8 ft"
    ("length_ft", re.compile(_NUM + r"\s*(?:ft|feet|foot|')\s*(?:long|lengths?)\b", re.I), 1.0),
    ("length_ft", re.compile(_NUM + r"\s*(?:ft|feet|foot|')\s*(?:stud|board|pipe|plank|joist)", re.I), 1.0),
    ("width_ft", re.compile(_NUM + r"\s*(?:ft|feet|')\s*wide", re.I), 1.0),
)
_FLAGS = (
    ("treated", re.compile(r"\b(?:pressure[- ]?treated|treated|ground contact)\b", re.I),
     re.compile(r"\buntreated\b", re.I)),
    ("submersible", re.compile(r"\bsubmersible\b", re.I), re.compile(r"\binline|in-line|external\b", re.I)),
    ("uv", re.compile(r"\buv(?:[- ](?:rated|stabili[sz]ed|coated|protect\w*|resistant))\b", re.I),
     re.compile(r"\bnot uv\b", re.I)),
)
_NOMINAL = re.compile(r"\b(\d)\s*[x×]\s*(\d{1,2})\b")
_MEASURES = re.compile(r"\b(temperature|humidity|moisture|ph|ec|light|co2|water level|pressure)\b", re.I)
_INTERFACE = re.compile(r"\b(i2c|1-wire|onewire|analog|spi|uart|rs485|modbus|zigbee|wi-?fi|bluetooth)\b", re.I)
_MODEL = re.compile(r"\b(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z0-9][A-Z0-9-]{4,}\b")
# Letters-and-digits tokens that are measurements, sizes or counts, never a model: "120VAC", "500GPH", "2X4X8",
# "SCH40", "10-PACK", "AWG12".
_UNITS = ("V|VAC|VDC|W|KW|KWH|WH|A|AH|MAH|AMP|AMPS|HZ|HP|GPH|GPM|CFM|PSI|RPM|MM|CM|M|IN|INCH|FT|YD|MIL|MILS|GA|AWG|"
          "LB|LBS|OZ|KG|G|GAL|QT|L|ML|PK|PC|PCS|PACK|CT|COUNT|PAIR|SET|K|LM|LUMENS?|DEG|F|C")
_MEASURE = re.compile(rf"^(?:\d+(?:-\d+)?-?(?:{_UNITS})|(?:SCH|SCHEDULE|AWG|GA|GAUGE|SIZE|TYPE|GRADE|IP|R|T)-?\d+|"
                      r"\d+(?:X\d+)+(?:-?(?:FT|IN|MM))?)$")


def category_of(text: str) -> Optional[str]:
    """Pure logic. The product category the words name (the first in CATEGORIES whose words appear), or None."""
    low = f" {str(text or '').lower()} "
    for name, (words, _fields) in CATEGORIES.items():
        if any(w in low for w in words):
            return name
    return None


def read(text: str) -> dict:
    """Pure logic. The specifications in some text, normalised (see the module's opening); a field not found is
    left out."""
    text = str(text or "")
    out: dict = {}
    for field, pattern, factor in _PATTERNS:
        if field in out:
            continue
        m = pattern.search(text)
        if m:
            out[field] = round(float(m.group(1)) * factor, 3) if field != "schedule" else int(m.group(1))
    for field, yes, no in _FLAGS:
        if no.search(text):
            out[field] = False
        elif yes.search(text):
            out[field] = True
    m = _NOMINAL.search(text)
    if m:
        out["nominal"] = f"{m.group(1)}x{m.group(2)}"
    m = _MEASURES.search(text)
    if m and category_of(text) == "sensor":  # "pressure treated" isn't a sensor that measures pressure
        out["measures"] = m.group(1).lower()
    m = _INTERFACE.search(text)
    if m:
        out["interface"] = m.group(1).lower().replace("onewire", "1-wire").replace("wi-fi", "wifi")
    return out


def models(text: str) -> set[str]:
    """Pure logic. The model-number-like tokens in some text (letters and digits, five or more characters), leaving
    out measurements, sizes and counts ("120VAC", "2X4X8", "SCH40"): two products that share a voltage aren't the
    same model."""
    return {m.group(0) for m in _MODEL.finditer(str(text or "").upper()) if not _MEASURE.match(m.group(0))}


def verdict(needed_text: str, product_text: str, category: Optional[str] = None) -> dict:
    """Pure logic. {verdict, category, reasons, unknown} for a product against a need (see the module's opening).
    `needed_text` is the need's item and specs; `product_text` the listing's title and details."""
    cat = category or category_of(needed_text) or category_of(product_text)
    shared = models(needed_text) & models(product_text)
    if shared:
        return {"verdict": "identical", "category": cat, "reasons": [f"same model ({sorted(shared)[0]})"], "unknown": []}
    if cat is None:
        return {"verdict": "similar", "category": None, "reasons": ["not a kind of product I compare by specs yet"],
                "unknown": []}
    fields = CATEGORIES[cat][1]
    need, have = read(needed_text), read(product_text)
    reasons, unknown, failed = [], [], False
    for field, how in fields.items():
        if field not in need:
            continue
        label = NAMES.get(field, field)
        if field not in have:
            unknown.append(label)
            continue
        want, got = need[field], have[field]
        ok = (got >= want) if how == "min" and isinstance(got, (int, float)) and not isinstance(got, bool) else \
            (got <= want) if how == "max" and isinstance(got, (int, float)) and not isinstance(got, bool) else got == want
        reasons.append(f"{label}: {_shown(got)} {'meets' if ok else 'fails'} {_shown(want)}"
                       + (" needed" if how != "eq" else ""))
        failed = failed or not ok
    if failed:
        result = "not suitable"
    elif unknown:
        result = "similar"
    else:
        result = "equivalent" if reasons else "similar"
    if not reasons and not unknown:
        reasons = ["the need states no specifications to check"]
    return {"verdict": result, "category": cat, "reasons": reasons, "unknown": unknown}


def _shown(value) -> str:
    """A specification's value in words."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
