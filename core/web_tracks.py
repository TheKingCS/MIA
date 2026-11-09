"""
core.web_tracks
=================

Tracks on the web (web/tracks.html; core/gps_tracks.py, DEC-0099; claude, 2026-11-09: GPX tracks had no screen, only
`python -m tools.tracks` and "how far was my last hike?"). Every walk, ride or drive the person has added, newest
first: its name and date, distance, climb and descent, time taken and time moving, where it started and ended (MGRS),
its shape drawn from its own points, and the totals for the last 30 days and all time.

Changes are actions: `track.add` keeps a GPX file the person chose (its text, worked out in core/gps_tracks.stats,
never by a model) and `track.delete` takes one off; both write through atomic_write_text, so "undo that" puts it back.
Where a person went is theirs: a personal store, and nothing here leaves the device.

Formatting only: the numbers come from core/gps_tracks.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.logger import get_logger

log = get_logger(__name__)

SHAPE_POINTS = 160  # a track's outline is drawn from at most this many of its points
MAX_GPX = 4 * 1024 * 1024  # characters


def shape(points: list[dict], size: int = 100) -> str:
    """Pure logic. A track's outline as an SVG path in a `size` square (north up, the longer side filling it, the
    shorter centred, longitude scaled by the latitude so the shape isn't stretched); "" for fewer than two points."""
    import math

    pts = [p for p in points if p.get("lat") is not None and p.get("lon") is not None]
    if len(pts) < 2:
        return ""
    step = max(1, len(pts) // SHAPE_POINTS)
    pts = pts[::step] + ([pts[-1]] if (len(pts) - 1) % step else [])
    k = math.cos(math.radians(sum(p["lat"] for p in pts) / len(pts)))
    xs, ys = [p["lon"] * k for p in pts], [p["lat"] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    scale = (size - 8) / max(w, h, 1e-9)
    ox, oy = (size - w * scale) / 2, (size - h * scale) / 2
    xy = [(ox + (x - min(xs)) * scale, size - (oy + (y - min(ys)) * scale)) for x, y in zip(xs, ys)]
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in xy)


def _time_words(hours: Optional[float]) -> str:
    """Pure logic. Hours as "1 h 05 min" or "42 min"; "" when not known."""
    if not hours:
        return ""
    h, m = divmod(round(hours * 60), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def _card(track: dict) -> dict:
    """One track for the screen: name, date, the numbers in words, start and end, the line it's said in, its shape."""
    from core.gps_tracks import describe

    s = track.get("stats") or {}
    return {"id": track["id"], "name": track.get("name", "A track"), "date": s.get("date") or track.get("added", "")[:10],
            "km": s.get("km", 0), "climb_m": s.get("climb_m", 0), "descent_m": s.get("descent_m", 0),
            "time": _time_words(s.get("hours")), "moving": _time_words(s.get("moving_hours")),
            "start": s.get("start", ""), "end": s.get("end", ""), "points": s.get("points", 0),
            "line": describe(track), "shape": shape(track.get("points") or [])}


def screen(context, today: Optional[date] = None) -> dict:
    """Tracks: every one newest first, and the totals (count and km) for the last 30 days and all time. `available` is
    False when this MIA has no track store."""
    today = today or date.today()
    store = getattr(context, "gps_tracks", None)
    if store is None:
        return {"available": False, "tracks": [], "totals": {}}
    cards = sorted((_card(t) for t in store.tracks), key=lambda c: c["date"], reverse=True)
    since = (today - timedelta(days=30)).isoformat()
    recent = [c for c in cards if c["date"] >= since]
    return {"available": True, "tracks": cards,
            "totals": {"count": len(cards), "km": round(sum(c["km"] for c in cards), 1),
                       "count_30": len(recent), "km_30": round(sum(c["km"] for c in recent), 1)}}


# ------------------------------------------------------------------ actions

def _gpx(params) -> str:
    """The GPX text the params carry, or ActionError."""
    text = str(params.get("gpx") or "")
    if not text.strip():
        raise ActionError("Choose a GPX file from your phone, watch or GPS.")
    if len(text) > MAX_GPX:
        raise ActionError("That file is too large for one track.")
    return text


def _describe_add(context, params) -> str:
    """The sentence for `track.add`: the track as it will be kept (read from the file now, so a bad file is refused
    before anything is approved)."""
    from core.gps_tracks import TrackError, parse_gpx, stats

    _need(context, "gps_tracks")
    try:
        found, points = parse_gpx(_gpx(params))
    except TrackError as problem:
        raise ActionError(str(problem)) from None
    name = (str(params.get("name") or "").strip() or found or "A track")[:80]
    return f"Keep {name}: {stats(points)['km']:g} km"


def _add(context, params) -> str:
    """Does `track.add`: keeps the track and says it in a line."""
    from core.gps_tracks import TrackError, describe

    try:
        track = _need(context, "gps_tracks").add_gpx(_gpx(params), str(params.get("name") or ""))
    except TrackError as problem:
        raise ActionError(str(problem)) from None
    return "Kept. " + describe(track)


def _one(context, params) -> dict:
    """The track `track_id` names, or ActionError."""
    found = next((t for t in _need(context, "gps_tracks").tracks if t["id"] == str(params.get("track_id") or "")), None)
    if found is None:
        raise ActionError("That track isn't here any more.")
    return found


def _delete(context, params) -> str:
    """Does `track.delete`."""
    track = _one(context, params)
    _need(context, "gps_tracks").delete(track["id"])
    return f"Took {track['name']} off your tracks."


TRACK_ACTIONS = {k.kind: k for k in (
    ActionType("track.add", "Add a Track", {"gpx": "the GPX file's text", "name": "a name (optional)"},
               _describe_add, _add),
    ActionType("track.delete", "Delete Track", {"track_id": "the track"},
               lambda c, p: f"Delete {_one(c, p)['name']}", _delete),
)}
ACTION_TYPES.update(TRACK_ACTIONS)
