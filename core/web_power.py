"""
core.web_power
================

The Power screen's data (web/power.html; 2026-11-07, DEC-0125: Power was
the PC app's only). Two parts, as the design canvas draws them: this
computer's battery (core/power_manager.py; a desktop usually has none) and
the energy sources tracked by hand (core/energy_manager.py), each with the
latest reading on each of its meters, a fill for a meter read in percent,
and how long ago it was logged. Changes go through core/power_actions.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def _ago(stamp: str, now: datetime) -> str:
    """Pure logic. When a reading was logged, in words: "today, 4 pm", "Mon", "2 weeks ago"."""
    try:
        when = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return ""
    days = (now.date() - when.date()).days
    if days <= 0:
        return "today, " + when.strftime("%I %p").lstrip("0").lower()
    if days < 7:
        return when.strftime("%a")
    weeks = days // 7
    return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def _battery(context) -> dict:
    """This computer's battery: percent, plugged in, time left; {"present": False} without one."""
    power = getattr(context, "power", None)
    status = power.read() if power is not None and power.is_available() else None
    if status is None:
        return {"present": False}
    left = status.seconds_left
    return {"present": True, "percent": round(status.percent), "plugged_in": status.plugged_in,
            "minutes_left": round(left / 60) if left else None}


def power_page(context, now: Optional[datetime] = None) -> dict:
    """The Power screen: the battery, each energy source with its meters' latest readings (a percent fill when read
    in %), the kinds of source, and the forms; {"available": False} without the energy store."""
    from core.energy_manager import ENERGY_SOURCE_TYPES
    from core.power_actions import form_spec

    energy = getattr(context, "energy", None)
    if energy is None:
        return {"available": False}
    now = now or datetime.now()
    sources = []
    for source in energy.all_energy_sources():
        meters = []
        if getattr(context, "data_logger", None) is not None:
            for meter in energy.energy_source_meter_names(source.source_id):
                readings = energy.energy_source_readings(source.source_id, meter)
                if not readings:
                    continue
                last = max(readings, key=lambda r: r.timestamp or "")
                percent = round(max(0.0, min(100.0, last.value))) if last.unit.strip() == "%" else None
                meters.append({"meter": meter, "value": last.value, "unit": last.unit, "note": last.note,
                               "percent": percent, "when": _ago(last.timestamp, now), "at": last.timestamp})
        sources.append({"id": source.source_id, "name": source.name, "kind": source.source_type, "notes": source.notes,
                        "meters": meters, "values": {"name": source.name, "source_type": source.source_type,
                                                     "notes": source.notes}})
    return {"available": True, "battery": _battery(context), "sources": sources, "kinds": list(ENERGY_SOURCE_TYPES),
            "forms": form_spec()}
