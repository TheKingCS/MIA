"""
core.web_power
================

Power's web screen (DEC-0113 canvas, DEC-0125: Power had no phone screen).
Two parts:

- **Battery**: this device's battery from core/power_manager.py (percent,
  plugged in, time left), or that it has none (a desktop on mains);
- **Energy sources**: each source the person tracks by hand
  (core/energy_manager.py) with its latest reading on each meter, how long
  ago that was, and, for a reading in percent, a meter to fill and its tone
  (amber under LOW_PERCENT: it needs you soon).

Readings are entered by hand; no sensors are connected yet. Changes are the
actions in core/power_actions.py. The web only draws.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

LOW_PERCENT = 25


def ago(when: Optional[datetime], now: datetime) -> str:
    """Pure logic. How long ago a reading was, in a few words: "just now", "3 h ago", "today", "yesterday",
    "4 days ago", "2 weeks ago"; "" without a time."""
    if when is None:
        return ""
    seconds = (now - when).total_seconds()
    if seconds < 3600:
        return "just now" if seconds < 120 else f"{int(seconds // 60)} min ago"
    if when.date() == now.date():
        return f"{int(seconds // 3600)} h ago"
    days = (now.date() - when.date()).days
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    return f"{days // 7} weeks ago"


def meter_of(value: float, unit: str) -> Optional[dict]:
    """Pure logic. A reading in percent as a meter: its fill and tone (attention under LOW_PERCENT); None for any
    other unit (a kWh count has no full)."""
    if (unit or "").strip() != "%":
        return None
    pct = max(0.0, min(100.0, float(value)))
    return {"pct": round(pct), "tone": "attention" if pct < LOW_PERCENT else "ok"}


def reading_text(value: float, unit: str) -> str:
    """Pure logic. A reading in words: "62%", "3.8 kWh", "40"."""
    unit = (unit or "").strip()
    return f"{value:g}%" if unit == "%" else f"{value:g} {unit}".strip()


def _battery(context) -> dict:
    """This device's battery: {available, percent, plugged_in, minutes_left}; available False when it has none."""
    power = getattr(context, "power", None)
    try:
        status = power.read() if power is not None and power.is_available() else None
    except Exception:
        log.exception("Power: battery read failed")
        status = None
    if status is None:
        return {"available": False}
    return {"available": True, "percent": round(status.percent), "plugged_in": bool(status.plugged_in),
            "minutes_left": round(status.seconds_left / 60) if status.seconds_left else None,
            "meter": meter_of(status.percent, "%")}


def power_page(context, now: Optional[datetime] = None) -> dict:
    """The Power screen's data: the battery, and each energy source with its latest reading per meter (value, unit,
    when, a meter for percent readings), most needing attention first; the forms."""
    from core.power_actions import forms

    now = now or datetime.now()
    energy = getattr(context, "energy", None)
    sources = []
    for s in (energy.all_energy_sources() if energy is not None else []):
        meters = []
        for name in energy.energy_source_meter_names(s.source_id):
            readings = energy.energy_source_readings(s.source_id, name)
            if not readings:
                continue
            last = max(readings, key=lambda r: r.timestamp)
            try:
                at = datetime.fromisoformat(str(last.timestamp)[:19])
            except ValueError:
                at = None
            meters.append({"name": name, "value": last.value, "unit": last.unit or "",
                           "text": reading_text(last.value, last.unit or ""),
                           "when": ago(at, now), "at": str(last.timestamp)[:19], "meter": meter_of(last.value, last.unit or ""),
                           "count": len(readings)})
        low = min((m["meter"]["pct"] for m in meters if m["meter"]), default=101)
        sources.append({"id": s.source_id, "name": s.name, "type": s.source_type, "notes": s.notes, "meters": meters,
                        "needs_you": low < LOW_PERCENT,
                        "values": {"name": s.name, "source_type": s.source_type, "notes": s.notes}})
    sources.sort(key=lambda x: (not x["needs_you"], x["name"].lower()))
    return {"available": energy is not None, "battery": _battery(context), "sources": sources, "forms": forms(),
            "low_percent": LOW_PERCENT}
