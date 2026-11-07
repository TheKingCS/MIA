"""
core.web_lab
==============

The Lab's web screen (DEC-0113 canvas Lab, DEC-0125: the Lab had no phone
screen). The Lab is the home of the Data Logger (core/data_logger_manager.py):
readings kept in named series ("Soil moisture", "Tank pH", "Shop temp"), one
value each with a unit, a note and when.

lab_page() gives the series as chips (each with its latest reading, how
long ago and how many), and the chosen one in full: its readings newest
first, a few plain numbers (latest, lowest, highest, average, the change
since the first) and the points for its chart. Series written by other
apps (Power's energy sources, Garage's asset meters) are listed apart
under the name they have there, read only, with a link to that app.

Logging and deleting readings are the actions `lab_reading.add` and
`lab_reading.delete` (core/lab_reading_actions.py). Entered by hand: no
sensors are connected yet. The web only draws.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.logger import get_logger
from core.web_power import ago

log = get_logger(__name__)

CHART_POINTS = 60  # the chart shows the newest readings, up to this many
_OTHER_APPS = (("energy_source_", "Power", "power.html"), ("maintenance_asset_", "Garage", "garage.html"))


def resolve_series(series_ids: list, requested: str) -> str:
    """Pure logic. The stored series id that matches `requested` ignoring case (so "soil moisture" joins "Soil
    Moisture"), else `requested` as typed, trimmed: a new series starts with its first reading."""
    requested = (requested or "").strip()
    return next((s for s in series_ids if s.lower() == requested.lower()), requested)


def owner_of(series_id: str) -> Optional[tuple]:
    """Pure logic. The app that writes a series, (prefix, app name, page), or None for the Lab's own."""
    return next((o for o in _OTHER_APPS if series_id.startswith(o[0])), None)


def _when(reading) -> Optional[datetime]:
    """A reading's time, or None when it can't be read."""
    try:
        return datetime.fromisoformat(str(reading.timestamp)[:19])
    except ValueError:
        return None


def _text(value: float, unit: str) -> str:
    """Pure logic. A value with its unit: "21.5 °C", "62%", "7.1"."""
    unit = (unit or "").strip()
    return f"{value:g}%" if unit == "%" else f"{value:g} {unit}".strip()


def stats(readings: list) -> dict:
    """Pure logic. Plain numbers for a series (oldest first): latest, lowest, highest, average and the change since
    the first, each in words with the latest reading's unit; {} without readings."""
    if not readings:
        return {}
    values = [r.value for r in readings]
    unit = readings[-1].unit or ""
    change = values[-1] - values[0]
    return {"latest": _text(values[-1], unit), "low": _text(min(values), unit), "high": _text(max(values), unit),
            "average": _text(round(sum(values) / len(values), 2), unit),
            "change": ("+" if change > 0 else "") + _text(round(change, 2), unit) if len(values) > 1 else "",
            "count": len(values)}


def chart(readings: list) -> dict:
    """Pure logic. The chart's points for a series (oldest first): the newest CHART_POINTS readings as {x 0..1
    across, y 0..1 up, label}, with the low and high it spans; empty points with fewer than two readings."""
    shown = readings[-CHART_POINTS:]
    if len(shown) < 2:
        return {"points": [], "low": None, "high": None}
    values = [r.value for r in shown]
    low, high = min(values), max(values)
    span = (high - low) or 1.0
    unit = shown[-1].unit or ""
    return {"points": [{"x": round(i / (len(shown) - 1), 4), "y": round((r.value - low) / span, 4),
                        "label": _text(r.value, r.unit or unit)} for i, r in enumerate(shown)],
            "low": _text(low, unit), "high": _text(high, unit)}


def _name(context, series_id: str) -> str:
    """A series' name for the screen: the Lab's own as stored; another app's as "Propane tank · Level"."""
    owner = owner_of(series_id)
    if owner is None:
        return series_id
    rest = series_id[len(owner[0]):]
    record_id, _, meter = rest.partition("_")
    try:
        if owner[1] == "Power":
            record = context.energy.get_energy_source(record_id) if getattr(context, "energy", None) else None
        else:
            record = context.maintenance.get_asset(record_id) if getattr(context, "maintenance", None) else None
    except Exception:
        record = None
    return f"{getattr(record, 'name', None) or 'Removed'} · {meter or 'Reading'}"


def lab_page(context, series: str = "", now: Optional[datetime] = None) -> dict:
    """The Lab screen's data: the Lab's own series and other apps' (each with its latest reading, how long ago, how
    many), and the chosen series in full (readings newest first, plain numbers, chart points): the one asked for,
    else the one with the newest reading."""
    from core.lab_reading_actions import READING_FIELDS

    now = now or datetime.now()
    logger = getattr(context, "data_logger", None)
    if logger is None:
        return {"available": False}
    own, others = [], []
    for sid in logger.list_series():
        readings = logger.readings_for(sid)
        if not readings:
            continue
        last = readings[-1]
        owner = owner_of(sid)
        row = {"id": sid, "name": _name(context, sid), "latest": _text(last.value, last.unit), "count": len(readings),
               "when": ago(_when(last), now), "at": str(last.timestamp)[:19]}
        if owner:
            row.update({"app": owner[1], "page": owner[2]})
            others.append(row)
        else:
            own.append(row)
    own.sort(key=lambda r: r["at"], reverse=True)
    others.sort(key=lambda r: r["name"].lower())
    every = {r["id"] for r in own + others}
    chosen = series if series in every else (own[0]["id"] if own else "")
    detail = None
    if chosen:
        readings = logger.readings_for(chosen)
        owner = owner_of(chosen)
        detail = {"id": chosen, "name": _name(context, chosen), "own": owner is None,
                  "app": owner[1] if owner else None, "page": owner[2] if owner else None,
                  "unit": readings[-1].unit if readings else "", "stats": stats(readings), "chart": chart(readings),
                  "readings": [{"id": r.reading_id, "text": _text(r.value, r.unit), "note": r.note,
                                "when": ago(_when(r), now), "at": str(r.timestamp)[:16].replace("T", " ")}
                               for r in reversed(readings)]}
    return {"available": True, "series": own, "other_series": others, "chosen": detail,
            "forms": {"reading": {"fields": READING_FIELDS}}}
