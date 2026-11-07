"""
core.waypoint_actions
=======================

Waypoints (core/waypoint_manager.py) through the action contract
(core/actions.py), for the web's Maps and Navigation pages: `waypoint.add`
(a name and where: from a tap on the map, or typed) and `waypoint.delete`.
The store writes through atomic_write_text, so "undo that" takes either
back. Maps are a child's too: both are child-safe.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _where(params) -> tuple[float, float]:
    """The latitude and longitude in the params as numbers; ActionError when they're missing or not on Earth."""
    try:
        lat, lon = float(params.get("lat")), float(params.get("lon"))
    except (TypeError, ValueError):
        raise ActionError("Where is it? A latitude and a longitude.") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ActionError("That isn't a place on Earth.")
    return lat, lon


def _name(params) -> str:
    """The waypoint's name, spaces tidied, at most 80 characters; ActionError when it's empty."""
    name = " ".join(str(params.get("name") or "").split())
    if not name:
        raise ActionError("What's the waypoint called?")
    return name[:80]


def _describe_add(context, params) -> str:
    """waypoint.add's sentence to approve: the name and where, to five decimal places."""
    lat, lon = _where(params)
    return f"Add the waypoint {_name(params)} at {lat:.5f}, {lon:.5f}"


def _add(context, params) -> str:
    """waypoint.add: a new waypoint in the household's list; a category not in WAYPOINT_CATEGORIES is left blank."""
    from core.waypoint_manager import WAYPOINT_CATEGORIES

    lat, lon = _where(params)
    category = str(params.get("category") or "")
    made = _need(context, "waypoints").add_waypoint(_name(params), lat, lon,
                                                    category=category if category in WAYPOINT_CATEGORIES else "")
    return f"Added {made.name}."


def _waypoint(context, params):
    """The waypoint the params name; ActionError when it's gone."""
    found = _need(context, "waypoints").get_waypoint(str(params.get("waypoint_id") or ""))
    if found is None:
        raise ActionError("That waypoint isn't there any more.")
    return found


def _delete(context, params) -> str:
    """waypoint.delete: take the waypoint out of the household's list."""
    found = _waypoint(context, params)
    _need(context, "waypoints").delete_waypoint(found.waypoint_id)
    return f"Took {found.name} out."


WAYPOINT_ACTIONS = {a.kind: a for a in (
    ActionType("waypoint.add", "Add", {"name": "what to call it", "lat": "latitude", "lon": "longitude",
                                       "category": "a kind (optional)"}, _describe_add, _add, child_ok=True),
    ActionType("waypoint.delete", "Take it out", {"waypoint_id": "the waypoint"},
               lambda c, p: f"Take the waypoint {_waypoint(c, p).name} out", _delete, child_ok=True),
)}
ACTION_TYPES.update(WAYPOINT_ACTIONS)
