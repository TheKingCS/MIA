"""
core.assistant_trip_route_actions
====================================

A trip's route and checkpoints by voice (DEC-0125), the same three action
kinds the Expeditions page uses (core/trip_route.py), so "undo that" takes
each back:

- add_route_stop: "add the summit to the ridge trip's route".
- log_arrival: "arrived at the spring", "I made it to the trailhead": a checkpoint
  on the trip underway (or the trip named), with the leg it ends.
- get_trip_route: "what's left on my route?": the stops reached, the next
  one, and the legs so far.

A trip is found by the words said; with none said, the one underway.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _find(items, words: str):
    """The record whose name the words name, or None (the shared finder for anything with a name)."""
    from core.assistant_cooking_actions import find_recipe

    return find_recipe(items, words) if words.strip() else None


def _trip(context, words: str):
    """(the trip the words name, else the one underway; a reply when there's no such trip)."""
    trips = getattr(context, "trips", None)
    if trips is None:
        return None, "Expeditions aren't on this MIA."
    words = str(words or "").replace("trip", "").strip()
    if words:
        found = _find(trips.all_trips(), words)
        return (found, None) if found else (None, f"I don't have a trip called '{words}'.")
    underway = [t for t in trips.all_trips() if t.status == "active"]
    if len(underway) == 1:
        return underway[0], None
    return None, "Which trip?" if underway else "No trip is underway. Which trip is it?"


def _run(context, kind: str, params: dict) -> str:
    """Runs the action kind as the page would (its describe checks it first) and returns what happened."""
    from core.actions import run_as_tool

    return run_as_tool(context, kind, params)


def _waypoint(context, words: str):
    """(the saved waypoint the words name; a reply when there's none)."""
    book = getattr(context, "waypoints", None)
    if book is None:
        return None, "Waypoints aren't on this MIA."
    found = _find(book.all_waypoints(), str(words or "").replace("waypoint", ""))
    return (found, None) if found else (None, f"I don't have a waypoint called '{words}'. Save it in Navigation first.")


def _add_stop(context, arguments: dict) -> str:
    """Tool add_route_stop: a saved waypoint onto the end of a trip's route."""
    trip, problem = _trip(context, arguments.get("trip"))
    if problem:
        return problem
    point, problem = _waypoint(context, arguments.get("waypoint"))
    if problem:
        return problem
    return _run(context, "trip.route_add", {"trip_id": trip.trip_id, "waypoint_id": point.waypoint_id})


def _arrived(context, arguments: dict) -> str:
    """Tool log_arrival: a checkpoint at the waypoint named, on the trip underway (or the one named)."""
    trip, problem = _trip(context, arguments.get("trip"))
    if problem:
        return problem
    point, problem = _waypoint(context, arguments.get("waypoint"))
    if problem:
        return problem
    return _run(context, "trip.arrived", {"trip_id": trip.trip_id, "waypoint_id": point.waypoint_id})


def _route(context, arguments: dict) -> str:
    """Tool get_trip_route: the stops (reached or not), the next one, and the legs walked, in words."""
    from core.trip_route import route_card

    trip, problem = _trip(context, arguments.get("trip"))
    if problem:
        return problem
    card = route_card(context, trip)
    if not card["stops"] and not card["legs"]:
        return f"{trip.name} has no route yet. Say \"add the trailhead to the {trip.name} route\"."
    parts = []
    if card["stops"]:
        parts.append(f"{trip.name}: " + ", ".join(s["name"] + (" (reached)" if s["reached"] else "") for s in card["stops"]) +
                     (f", {card['planned_km']} km planned." if card["planned_km"] else "."))
    parts.append(f"Next: {card['next']['name']}." if card["next"] else "Every stop is reached." if card["stops"] else "")
    if card["legs"]:
        parts.append(f"So far {card['walked_km']} km: " + "; ".join(
            f"{leg['from']} to {leg['to']} {leg['km']} km in {leg['took']}" for leg in card["legs"]) + ".")
    return " ".join(p for p in parts if p)


def register_trip_route_actions(registry) -> None:
    """Registers add_route_stop, log_arrival and get_trip_route."""
    s = {"type": "string"}
    trip = {**s, "description": "The trip as they said it; leave out for the trip underway."}
    registry.register(AssistantAction(
        name="add_route_stop", domain="expeditions",
        description="Add a saved waypoint to the end of a trip's planned route.",
        parameters={"type": "object", "properties": {"waypoint": {**s, "description": "The waypoint as they said it."},
                                                     "trip": trip}, "required": ["waypoint"]},
        handler=_add_stop,
        trigger_phrases=("to the route", "to my route", "add a stop", "route stop"),
        subjects=("route",),
    ))
    registry.register(AssistantAction(
        name="log_arrival", domain="expeditions",
        description="Log arriving at a waypoint now on a trip (a checkpoint), with the leg's distance and time.",
        parameters={"type": "object", "properties": {"waypoint": {**s, "description": "Where they are now."},
                                                     "trip": trip}, "required": ["waypoint"]},
        handler=_arrived,
        trigger_phrases=("arrived at", "i made it to", "reached the", "checkpoint"),
        subjects=("checkpoint",),
    ))
    registry.register(AssistantAction(
        name="get_trip_route", domain="expeditions",
        description="A trip's route: the stops reached, the next one, and the legs walked so far.",
        parameters={"type": "object", "properties": {"trip": trip}, "required": []},
        handler=_route,
        trigger_phrases=("my route", "next stop", "left on the route", "my splits"),
        subjects=("route",),
    ))
