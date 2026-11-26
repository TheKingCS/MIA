"""
core.trip_packing
===================

A trip's packing list from the last one (brainstorm round 17, 2026-11-25): when he adds a trip, the last trip of
the same kind (core/trip_manager.py, by start date, else when it was made) that had a packing list is named with its
list, and "copy the packing list" puts its items on the new trip, unpacked, leaving out what's already there. Copied
only on his words, never on her own: the tool copy_packing_list (act_within_grant: he asked; each item through
TripManager.add_gear_item, written atomically so "undo that" takes it back).

`last_like(context, trip)` finds the trip to copy from; `offer_line(context, trip)` is the sentence added to
add_trip's reply; `copy(context, to_trip, from_trip)` does it.
"""

from __future__ import annotations

from typing import Optional

SHOWN = 6


def _when(trip) -> str:
    """A trip's date for ordering: its start, else when it was made."""
    return str(trip.start_date or trip.created_at or "")


def last_like(context, trip) -> Optional[object]:
    """The latest other trip of the same activity with a packing list, or None (no activity: any kind)."""
    trips = getattr(context, "trips", None)
    if trips is None:
        return None
    like = [t for t in trips.all_trips() if t.trip_id != trip.trip_id and t.gear
            and (not trip.activity_type or t.activity_type == trip.activity_type)]
    return max(like, key=_when) if like else None


def offer_line(context, trip) -> str:
    """The sentence for add_trip's reply: the last like trip's list and how to copy it, or ""."""
    found = last_like(context, trip)
    if found is None:
        return ""
    labels = [g.label for g in found.gear if g.label]
    shown = ", ".join(labels[:SHOWN]) + (f" and {len(labels) - SHOWN} more" if len(labels) > SHOWN else "")
    return (f" Your last {(trip.activity_type or 'trip').lower()} trip, {found.name}, packed: {shown}. Say \"copy the "
            f"packing list\" and I'll put those on this one.")


def copy(context, to_trip, from_trip) -> list[str]:
    """Puts from_trip's items on to_trip, unpacked, leaving out any already there (by name); the labels added."""
    have = {g.label.lower() for g in to_trip.gear}
    added = []
    for g in from_trip.gear:
        if g.label and g.label.lower() not in have:
            context.trips.add_gear_item(to_trip.trip_id, label=g.label, item_id=g.item_id)
            have.add(g.label.lower())
            added.append(g.label)
    return added


def _newest_planned(context):
    """The trip most recently made that's still planned."""
    trips = [t for t in context.trips.all_trips() if t.status == "planned"]
    return max(trips, key=lambda t: str(t.created_at or "")) if trips else None


def _copy_tool(context, arguments: dict) -> str:
    """Tool copy_packing_list: copies the last like trip's list (or the one he names as `from_trip`) onto the trip
    he names (`trip_name`), else onto the trip he made most recently that's still planned."""
    if getattr(context, "trips", None) is None:
        return "Expeditions isn't on this MIA."
    name = str(arguments.get("trip_name") or "").strip().lower()
    to_trip = next((t for t in context.trips.all_trips() if t.name.lower() == name), None) if name else \
        _newest_planned(context)
    if to_trip is None:
        return f"I don't have a trip called '{arguments.get('trip_name')}'." if name else "You don't have a trip planned."
    source = str(arguments.get("from_trip") or "").strip().lower()
    from_trip = next((t for t in context.trips.all_trips() if t.name.lower() == source), None) if source else \
        last_like(context, to_trip)
    if from_trip is None:
        return (f"I don't have a trip called '{arguments.get('from_trip')}'." if source else
                f"There's no earlier {(to_trip.activity_type or 'trip').lower()} trip with a packing list to copy.")
    added = copy(context, to_trip, from_trip)
    if not added:
        return f"{to_trip.name} already has everything from {from_trip.name}'s packing list."
    return (f"Copied {len(added)} item{'s' if len(added) != 1 else ''} from {from_trip.name} to {to_trip.name}: "
            + ", ".join(added[:SHOWN]) + (" and more" if len(added) > SHOWN else "") + ".")


def register_trip_packing_actions(registry) -> None:
    """Registers copy_packing_list."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="copy_packing_list", domain="expeditions",
        description="Copy a packing list from his last trip of the same kind (or one he names) onto a trip.",
        parameters={"type": "object", "properties": {
            "trip_name": {"type": "string", "description": "the trip to copy onto (optional: the newest planned one)"},
            "from_trip": {"type": "string", "description": "the trip to copy from (optional: the last of the same kind)"}},
            "required": []},
        handler=_copy_tool,
        trigger_phrases=("copy the packing list", "same packing list", "copy my gear list", "use the last packing list"),
        subjects=("packing", "gear"),
    ))
