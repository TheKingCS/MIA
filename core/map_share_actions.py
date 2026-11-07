"""
core.map_share_actions
========================

Showing MIA's places on TAK apps on the local network (build plan step 14,
DEC-0099; `docs/MAPS_AND_COMMS.md`), through the action contract
(core/actions.py): `map.tak_share` sends each waypoint once as a Cursor on
Target event over UDP multicast with a one-hop limit, so it never leaves the
network the PC is on. A person's places are where they go: it's never a
child's action, and it happens only when approved, each time.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _places(context) -> list:
    """Every waypoint to share; ActionError when there are none."""
    store = getattr(context, "waypoints", None)
    places = store.all_waypoints() if store is not None else []
    if not places:
        raise ActionError("There are no places to share yet.")
    return places


def _describe(context, params) -> str:
    """What sharing will do, said before it's approved: how many places, shown on TAK apps on this network, once, never beyond it."""
    places = _places(context)
    return (f"Show your {len(places)} place{'s' if len(places) != 1 else ''} on TAK apps on this network, once "
            "(never beyond it)")


def _share(context, params) -> str:
    """Sends every waypoint as a CoT event to TAK apps on the local network (core.tak); ActionError when the network refuses it. Says how many were sent."""
    from core import tak

    places = _places(context)
    try:
        sent = tak.send([tak.cot_event(w) for w in places])
    except OSError as problem:
        raise ActionError(f"The network wouldn't take it: {problem}") from problem
    return f"Sent {sent} place{'s' if sent != 1 else ''} to TAK apps on this network. They stay for a year in the app."


MAP_SHARE_ACTIONS = {a.kind: a for a in (
    ActionType("map.tak_share", "Show on TAK", {}, _describe, _share),
)}
ACTION_TYPES.update(MAP_SHARE_ACTIONS)
