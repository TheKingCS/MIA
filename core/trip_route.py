"""
core.trip_route
=================

A trip's route and checkpoints on every device (DEC-0125; docs/WEB_PARITY.md
Expeditions "not yet: route, splits"). The desktop's trip dialog plans a
route from saved waypoints and logs "arrived here" at each one
(core/trip_manager.py: `waypoint_ids`, `record_split`, `leg_summaries`);
the web and voice had neither.

- `route_card(context, trip)`: what the Expeditions screen shows for a trip:
  the planned stops in order (each marked reached once logged), the planned
  distance, the next stop to arrive at, and each leg walked so far (from,
  to, distance, time, pace), all worked out here.
- Three action kinds, so the page and voice agree and "undo that" takes
  each back (the trips store writes through atomic_write_text):
  `trip.route_add` (a waypoint onto the end of the route),
  `trip.route_remove` (one off it) and `trip.arrived` (a checkpoint logged
  now).
- `duration_words` and `pace_words`: pure helpers for the legs.

Distances stay in kilometres, as every other Expeditions figure does.
"""

from __future__ import annotations

from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def duration_words(hours: float) -> str:
    """Pure logic. How long a leg took, in words: "45 min", "1 h 05 min", "3 h"."""
    minutes = max(0, round(hours * 60))
    if minutes < 60:
        return f"{minutes} min"
    whole, rest = divmod(minutes, 60)
    return f"{whole} h" if not rest else f"{whole} h {rest:02d} min"


def pace_words(speed_kmh: Optional[float]) -> str:
    """Pure logic. A leg's speed in words ("3.2 km/h"); "" when there was no time to divide by."""
    return f"{speed_kmh:.1f} km/h" if speed_kmh else ""


def reached_in_order(route: list[str], logged: list[str]) -> list[bool]:
    """Pure logic. Which stops of a route are reached, going through the checkpoints in the order they were logged:
    a stop counts once a checkpoint there comes after the one that reached the stop before it, so an out-and-back
    route (the trailhead first and last) isn't finished by the first checkpoint. A stop never logged is skipped, not
    a block: the next stops can still be reached."""
    out, after = [], 0
    for stop in route:
        try:
            at = logged.index(stop, after)
        except ValueError:
            out.append(False)
            continue
        out.append(True)
        after = at + 1
    return out


def _names(context) -> dict:
    """Each saved waypoint's name, by id ({} without waypoints on this MIA)."""
    book = getattr(context, "waypoints", None)
    return {w.waypoint_id: w.name for w in book.all_waypoints()} if book is not None else {}


def route_card(context, trip) -> dict:
    """A trip's route for its screen: the stops in order ({id, name, reached}), the planned km, the next stop not yet
    reached (None when every stop is reached or there's no route), the legs logged ({from, to, km, took, pace}) with
    their total, and when each checkpoint was logged. A stop whose waypoint was deleted is left out."""
    trips = context.trips
    names = _names(context)
    stops = [{"id": w, "name": names[w], "reached": done}
             for w, done in zip(trip.waypoint_ids, reached_in_order(trip.waypoint_ids, [s.waypoint_id for s in trip.splits]))
             if w in names]
    try:
        planned = trips.planned_route_distance_km(trip.trip_id)
    except Exception:
        planned = None
    legs = [{"from": names.get(leg.from_waypoint_id, "?"), "to": names.get(leg.to_waypoint_id, "?"),
             "km": round(leg.distance_km, 2), "took": duration_words(leg.elapsed_hours), "pace": pace_words(leg.speed_kmh)}
            for leg in trips.leg_summaries(trip.trip_id)]
    checkpoints = [{"name": names.get(s.waypoint_id, "?"), "at": s.logged_at} for s in trip.splits]
    return {"stops": stops, "planned_km": round(planned, 1) if planned else None,
            "next": next(({"id": s["id"], "name": s["name"]} for s in stops if not s["reached"]), None),
            "legs": legs, "walked_km": round(sum(leg["km"] for leg in legs), 1) if legs else None,
            "checkpoints": checkpoints}


def waypoint_choices(context) -> list[dict]:
    """Every saved waypoint as {id, name}, for the screen's "Add a stop" picker."""
    return [{"id": i, "name": n} for i, n in _names(context).items()]


# ------------------------------------------------------------------ actions


def _trip(context, params):
    """The trip the params name; ActionError when it isn't there."""
    trip = _need(context, "trips").get_trip(str(params.get("trip_id") or ""))
    if trip is None:
        raise ActionError("That trip isn't here any more.")
    return trip


def _waypoint(context, params) -> tuple[str, str]:
    """The waypoint the params name, as (id, name); ActionError when it isn't saved."""
    found = _need(context, "waypoints").get_waypoint(str(params.get("waypoint_id") or ""))
    if found is None:
        raise ActionError("That waypoint isn't saved. Add it in Navigation first.")
    return found.waypoint_id, found.name


def _describe_route_add(context, params) -> str:
    """The approval sentence for trip.route_add. A stop already on the route can go on again (out and back)."""
    trip, (wid, name) = _trip(context, params), _waypoint(context, params)
    return f"Add {name} to the {trip.name} route" + (" again (on the way back)" if wid in trip.waypoint_ids else "")


def _route_add(context, params) -> str:
    """Does trip.route_add: the waypoint goes on the end of the route."""
    trip, (wid, name) = _trip(context, params), _waypoint(context, params)
    context.trips.add_waypoint_to_route(trip.trip_id, wid)
    return f"{name} is stop {len(context.trips.get_trip(trip.trip_id).waypoint_ids)} on the {trip.name} route."


def _describe_route_remove(context, params) -> str:
    """The approval sentence for trip.route_remove; a waypoint not on the route is refused."""
    trip = _trip(context, params)
    wid = str(params.get("waypoint_id") or "")
    if wid not in trip.waypoint_ids:
        raise ActionError("That stop isn't on the route.")
    return f"Take {_names(context).get(wid, 'that stop')} off the {trip.name} route"


def _route_remove(context, params) -> str:
    """Does trip.route_remove: the stop comes off the route, its first time on it (checkpoints logged there stay)."""
    trip = _trip(context, params)
    wid = str(params.get("waypoint_id") or "")
    name = _names(context).get(wid, "That stop")
    context.trips.remove_waypoint_from_route(trip.trip_id, wid)
    return f"{name} is off the {trip.name} route."


def _describe_arrived(context, params) -> str:
    """The approval sentence for trip.arrived."""
    trip, (_, name) = _trip(context, params), _waypoint(context, params)
    return f"Log arriving at {name} on {trip.name} now"


def _arrived(context, params) -> str:
    """Does trip.arrived: a checkpoint logged now, and the leg it ends in words when there's one before it."""
    trip, (wid, name) = _trip(context, params), _waypoint(context, params)
    context.trips.record_split(trip.trip_id, wid)
    legs = context.trips.leg_summaries(trip.trip_id)
    if legs and legs[-1].to_waypoint_id == wid:
        leg = legs[-1]
        pace = pace_words(leg.speed_kmh)
        return (f"Arrived at {name}: {leg.distance_km:.1f} km from {_names(context).get(leg.from_waypoint_id, 'the last')} "
                f"in {duration_words(leg.elapsed_hours)}" + (f", {pace}." if pace else "."))
    return f"Arrived at {name}. The clock's running from here."


ROUTE_ACTIONS = {a.kind: a for a in (
    ActionType("trip.route_add", "Add a stop", {"trip_id": "the trip", "waypoint_id": "a saved waypoint"},
               _describe_route_add, _route_add),
    ActionType("trip.route_remove", "Take off the route", {"trip_id": "the trip", "waypoint_id": "the stop"},
               _describe_route_remove, _route_remove),
    ActionType("trip.arrived", "Arrived", {"trip_id": "the trip", "waypoint_id": "where you are"},
               _describe_arrived, _arrived),
)}
ACTION_TYPES.update(ROUTE_ACTIONS)
