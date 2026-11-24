"""
core.rain_catchment
=====================

Water off a roof (Jarvis brainstorm round 8, 2026-11-24): "how much rain could I catch off a 400 square foot roof?",
"is a 12 by 20 roof enough to water the greenhouse?". Worked out in code, never by the model.

**How.** An inch of rain on a square foot is 0.623 gallons; gutters, splash and the first flush lose some, so the
usual planning figure keeps 80% (`KEPT`). The roof's footprint (the ground it covers, not its slope) times that
gives gallons an inch. When his rain gauge has readings (core/weather_watch.py's series), the last 30 days' inches
say what that roof would have caught; without them it's said per inch only, never with a guessed rainfall. When he
names what it's for in square feet of beds, the beds' inch a week (core/project_ripple's garden guidance) is set
against it. Read-only.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

GALLONS_PER_SQFT_INCH = 0.623
KEPT = 0.8  # gutters, splash and the first flush: the usual planning share kept


def roof_sqft(said: str) -> Optional[float]:
    """Pure logic. A roof's square feet from words: "400 square feet", "400 sq ft", "12 by 20", "12x20 ft"; None."""
    text = str(said or "").lower().replace(",", "")
    by = re.search(r"(\d+(?:\.\d+)?)\s*(?:ft|foot|feet|')?\s*(?:by|x|×)\s*(\d+(?:\.\d+)?)", text)
    if by:
        return float(by.group(1)) * float(by.group(2))
    area = re.search(r"(\d+(?:\.\d+)?)\s*(?:square feet|square foot|sq\.? ?ft|sqft|sf)\b", text)
    if area:
        return float(area.group(1))
    bare = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", text)
    return float(bare.group(1)) if bare else None


def gallons(sqft: float, inches: float) -> float:
    """Pure logic. Gallons kept off a roof's footprint for this much rain (`KEPT` of the full 0.623 a square foot an
    inch)."""
    return round(max(0.0, sqft) * max(0.0, inches) * GALLONS_PER_SQFT_INCH * KEPT, 1)


def _rain_30(context, today: date) -> Optional[float]:
    """His gauge's inches over the last 30 days, or None with nothing logged then."""
    from core.weather_watch import RAIN_SERIES

    logger = getattr(context, "data_logger", None)
    if logger is None:
        return None
    since = (today - timedelta(days=29)).isoformat()
    found = [r.value for r in logger.readings_for(RAIN_SERIES) if str(r.timestamp)[:10] >= since]
    return round(sum(found), 2) if found else None


def say(context, roof: str, beds_sqft: Optional[float] = None, today: Optional[date] = None) -> str:
    """The roof's gallons an inch, what his logged rain would have given in 30 days, and against his beds' needs (an
    inch a week, 4.33 weeks a month)."""
    today = today or date.today()
    sqft = roof_sqft(roof)
    if not sqft:
        return "How big is the roof? Its footprint in square feet, or length by width, like \"12 by 20\"."
    per_inch = gallons(sqft, 1)
    out = [f"A {sqft:g} square foot roof keeps about {per_inch:g} gallons from each inch of rain (0.623 gallons a "
           f"square foot an inch, {round(KEPT * 100)}% kept after gutters and the first flush)."]
    rain = _rain_30(context, today)
    if rain is None:
        out.append("Your rain gauge has nothing logged in the last 30 days, so I can't say what it would have caught "
                   "here; log rain (\"we got half an inch\") and I'll count it.")
    else:
        caught = gallons(sqft, rain)
        out.append(f"Your gauge logged {rain:g} inches in the last 30 days: that roof would have caught about "
                   f"{caught:g} gallons.")
    if beds_sqft:
        need = gallons(beds_sqft, 1) / KEPT * 4.33  # an inch a week on the beds, a month's weeks, every drop used
        out.append(f"{beds_sqft:g} square feet of beds take about {round(need):g} gallons a month at an inch a week, "
                   f"so the roof covers that with {need / per_inch:.1f} inches of rain a month, with storage to hold "
                   "it between rains.")
    return " ".join(out)
