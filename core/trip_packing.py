"""
core.trip_packing
===================

A trip's packing list from the last one (brainstorm round 17, 2026-11-25): when he adds a trip, the last trip of
the same kind (core/trip_manager.py, by start date, else when it was made) that had a packing list is named with its
list, and "copy the packing list" puts its items on the new trip, unpacked, leaving out what's already there. Copied
only on his words, never on her own: the tool copy_packing_list (act_within_grant: he asked; each item through
TripManager.add_gear_item, written atomically so "undo that" takes it back).

`last_like(context, trip)` finds the trip to copy from; `offer_line(context, trip)` is the sentence added to
add_trip's reply; `copy(context, to_trip, from_trip)` does it, through the action `gear.copy_last` (the trip page's
"Copy from" button, core/web_more's `copy_from`, and the tool alike: DEC-0125, both ways).
"""

from __future__ import annotations

from typing import Optional

SHOWN = 6


def _when(trip) -> str:
    """A trip's date for ordering: its start, else when it was made."""
    return str(trip.start_date or trip.created_at or "")


def _kind(trip) -> str:
    """Pure logic. "fishing trip", or "trip" for one with no activity."""
    return f"{trip.activity_type.lower()} trip" if trip.activity_type else "trip"


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
    if not labels:
        return ""
    shown = ", ".join(labels[:SHOWN]) + (f" and {len(labels) - SHOWN} more" if len(labels) > SHOWN else "")
    return (f" Your last {_kind(trip)}, {found.name}, packed: {shown}. Say \"copy the packing list to {trip.name}\" "
            f"and I'll put those on it.")


def copy(context, to_trip, from_trip) -> list[str]:
    """Puts from_trip's items on to_trip, unpacked, leaving out any already there (by name, `missing`); the labels
    added."""
    labels = set(missing(to_trip, from_trip))
    added = []
    for g in from_trip.gear:
        if g.label in labels and g.label not in added:
            context.trips.add_gear_item(to_trip.trip_id, label=g.label, item_id=g.item_id)
            added.append(g.label)
    return added


def missing(to_trip, from_trip) -> list[str]:
    """Pure logic. The labels on from_trip's list that to_trip doesn't have yet."""
    have = {(g.label or "").lower() for g in to_trip.gear}
    out = []
    for g in from_trip.gear:
        if g.label and g.label.lower() not in have:
            have.add(g.label.lower())
            out.append(g.label)
    return out


def copy_from(context, trip) -> dict:
    """For the trip page: {name, trip_id, count} of the last like trip whose list has items this planned one lacks,
    or {} (a trip under way or done copies nothing)."""
    if trip.status != "planned":
        return {}
    found = last_like(context, trip)
    count = len(missing(trip, found)) if found is not None else 0
    return {"name": found.name, "trip_id": found.trip_id, "count": count} if count else {}


def _pair(context, params):
    """(to_trip, from_trip) for gear.copy_last: from_trip_id, else the last like trip; ActionError when either's gone."""
    from core.actions import ActionError

    trips = getattr(context, "trips", None)
    if trips is None:
        raise ActionError("Expeditions isn't on this MIA.")
    to_trip = trips.get_trip(str(params.get("trip_id") or ""))
    if to_trip is None:
        raise ActionError("That trip isn't there anymore.")
    source = str(params.get("from_trip_id") or "")
    from_trip = trips.get_trip(source) if source else last_like(context, to_trip)
    if from_trip is None or from_trip.trip_id == to_trip.trip_id:
        raise ActionError(f"There's no earlier {_kind(to_trip)} with a packing list to copy.")
    return to_trip, from_trip


def _copy_describe(context, params) -> str:
    """The sentence the card shows for gear.copy_last."""
    from core.actions import ActionError

    to_trip, from_trip = _pair(context, params)
    labels = missing(to_trip, from_trip)
    if not labels:
        raise ActionError(f"{to_trip.name} already has everything from {from_trip.name}'s packing list.")
    return (f"Copy {len(labels)} item{'s' if len(labels) != 1 else ''} from {from_trip.name}'s packing list to "
            f"{to_trip.name}: " + ", ".join(labels[:SHOWN]) + (" and more" if len(labels) > SHOWN else ""))


def _copy_execute(context, params) -> str:
    """Does gear.copy_last."""
    to_trip, from_trip = _pair(context, params)
    added = copy(context, to_trip, from_trip)
    if not added:
        return f"{to_trip.name} already has everything from {from_trip.name}'s packing list."
    return (f"Copied {len(added)} item{'s' if len(added) != 1 else ''} from {from_trip.name} to {to_trip.name}: "
            + ", ".join(added[:SHOWN]) + (" and more" if len(added) > SHOWN else "") + ".")


def _register_action() -> None:
    """Puts gear.copy_last on the action contract."""
    from core.actions import ACTION_TYPES, ActionType

    ACTION_TYPES["gear.copy_last"] = ActionType(
        "gear.copy_last", "Copy the list", {"trip_id": "the trip", "from_trip_id": "optional: the trip to copy from"},
        _copy_describe, _copy_execute)


_register_action()


def _newest_planned(context):
    """The trip most recently made that's still planned."""
    trips = [t for t in context.trips.all_trips() if t.status == "planned"]
    return max(trips, key=lambda t: str(t.created_at or "")) if trips else None


def _named(context, name: str, planned_first: bool):
    """The trip with that name: a planned one first when copying onto it, the latest one when copying from it."""
    found = [t for t in context.trips.all_trips() if t.name.lower() == name]
    if not found:
        return None
    if planned_first and any(t.status == "planned" for t in found):
        found = [t for t in found if t.status == "planned"]
    return max(found, key=_when)


def _copy_tool(context, arguments: dict) -> str:
    """Tool copy_packing_list: copies the last like trip's list (or the one he names as `from_trip`) onto the trip
    he names (`trip_name`), else onto the trip he made most recently that's still planned, through the action
    gear.copy_last (core/actions.run_as_tool). A trip named alone that
    isn't planned is the one to copy from ("copy the packing list from Lake day"), never one to add to (the Fable
    review, 2026-11-25)."""
    if getattr(context, "trips", None) is None:
        return "Expeditions isn't on this MIA."
    name = str(arguments.get("trip_name") or "").strip().lower()
    source = str(arguments.get("from_trip") or "").strip().lower()
    to_trip = _named(context, name, True) if name else _newest_planned(context)
    if name and not source and to_trip is not None and to_trip.status != "planned":
        source, to_trip = name, _newest_planned(context)
        name = ""
    if to_trip is None:
        return f"I don't have a trip called '{arguments.get('trip_name')}'." if name else "You don't have a trip planned."
    from_trip = _named(context, source, False) if source else last_like(context, to_trip)
    if from_trip is None:
        return (f"I don't have a trip called '{source}'." if source else
                f"There's no earlier {_kind(to_trip)} with a packing list to copy.")
    if from_trip.trip_id == to_trip.trip_id:
        return f"That's {to_trip.name}'s own list: tell me which trip to copy it to."
    from core.actions import run_as_tool

    return run_as_tool(context, "gear.copy_last", {"trip_id": to_trip.trip_id, "from_trip_id": from_trip.trip_id})


def register_trip_packing_actions(registry) -> None:
    """Registers copy_packing_list."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="copy_packing_list", domain="expeditions",
        description="Copy a packing list from his last trip of the same kind (or one he names) onto a trip.",
        parameters={"type": "object", "properties": {
            "trip_name": {"type": "string", "description": "the trip to copy onto; leave empty unless he names it"},
            "from_trip": {"type": "string", "description": "the trip to copy from; leave empty unless he names it"}},
            "required": []},
        handler=_copy_tool,
        trigger_phrases=("copy the packing list", "the same packing list", "copy my gear list",
                         "use the last packing list"),
        subjects=("packing", "gear"),
    ))
