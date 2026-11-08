"""
core.portal_pictures
=====================

The picture inside each area's portal in the Nexus, chosen by the person
(DEC-0140's "portal pictures painted by MIA", DEC-0130's Nexus).

What it does: every area's portal shows Muse's picture
(`web/img/portals/<area>.jpg`, H-0096) until the person puts one of their
own paintings there instead. `picture()` is what the Nexus draws (theirs,
else Muse's, else "" for the placeholder); `screen()` is the Portal Pictures
page; the action `portal.picture` puts one of their paintings on an area's
portal or takes it back to the original. A painting asked for "for the
Garage portal" goes up there by itself when it's done (`art_studio.settle`
calls `put_up`).

How: the choices are a personal setting, `nexus.portal_pictures`
({area id: art id}), so each person's Nexus is their own and "undo" puts it
back (the setting writes through atomic_write). A choice whose painting was
deleted is ignored, so the portal quietly goes back to Muse's picture.
"""

from __future__ import annotations

from typing import Optional

from core import person_settings
from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger

log = get_logger(__name__)

KEY = "nexus.portal_pictures"


def _store(context):
    """The person's paintings (core/art_studio's store), or None."""
    return getattr(context, "art", None)


def chosen(context) -> dict[str, str]:
    """{area id: art id} for the portals that show one of the person's own paintings (only paintings still there)."""
    raw = person_settings.get(context, KEY, {}) or {}
    store = _store(context)
    if not isinstance(raw, dict) or store is None:
        return {}
    out = {}
    for area, art_id in raw.items():
        try:
            if art_id and store.path(str(art_id)) is not None:
                out[str(area)] = str(art_id)
        except Exception:  # noqa: BLE001 - an unreadable picture is just not shown
            log.exception("Portal pictures: couldn't check %s", art_id)
    return out


def picture(context, area_id: str) -> str:
    """What an area's portal shows: the person's painting (its /api/art address, fetched with their sign-in), else
    Muse's picture (a page path), else "" (the room's placeholder in the area's colour)."""
    from core.web_nexus import portal_art

    own = chosen(context).get(area_id) if context is not None else None
    return f"/api/art/{own}/image" if own else portal_art(area_id)


def _area(area_id: str):
    """The area by its id, or ActionError."""
    from core.web_areas import AREAS

    for area in AREAS:
        if area.id == area_id:
            return area
    raise ActionError("There's no area like that.")


def put_up(context, area_id: str, art_id: str) -> None:
    """Puts one of the person's paintings on an area's portal ("" takes it back to the original). ValueError when the
    picture isn't theirs."""
    store = _store(context)
    if art_id and (store is None or store.path(art_id) is None):
        raise ValueError("That picture isn't one of yours.")
    picks = dict(person_settings.get(context, KEY, {}) or {})
    if art_id:
        picks[area_id] = art_id
    else:
        picks.pop(area_id, None)
    person_settings.put(context, KEY, picks)


def find_area(context, words: str) -> Optional[str]:
    """The area someone means by name ("the garage portal", "kitchen"), or None."""
    from core.web_areas import AREAS
    from core.web_nexus import _ALIASES

    text = " ".join(str(words or "").lower().replace("portal", " ").split())
    if not text:
        return None
    for area in AREAS:
        if area.id == text or area.name.lower() == text:
            return area.id
    for word, area_id in _ALIASES.items():
        if word in text.split():
            return area_id
    for area in AREAS:
        if area.name.lower() in text or text in area.name.lower():
            return area.id
    return None


def screen(context) -> dict:
    """The Portal Pictures page: each area the person sees with what its portal shows and where that came from, the
    paintings they could put on one (portal paintings first), the paintings still going, and the image engine."""
    from core.art_studio import status
    from core.web_areas import AREAS
    from core.web_areas import sidebar
    from core.web_nexus import portal_art

    art = status(context)
    picks = chosen(context)
    visible = {a["id"] for a in sidebar(context)}
    areas = []
    for a in AREAS:
        if a.id not in visible:
            continue
        own = picks.get(a.id, "")
        original = portal_art(a.id)
        areas.append({"id": a.id, "name": a.name, "hue": a.hue, "icon": a.icon,
                      "picture": f"/api/art/{own}/image" if own else original,
                      "source": "yours" if own else ("original" if original else "none"),
                      "art_id": own, "original": original})
    items = sorted(art["items"], key=lambda i: i.get("use") != "portal")  # newest first already; portal ones first
    return {"areas": areas, "paintings": items,
            "jobs": [j for j in art["jobs"] if j.get("use") == "portal"], "engine": art["engine"]}


def _describe(context, params) -> str:
    """The approval sentence for `portal.picture`."""
    area = _area(str(params.get("area") or ""))
    art_id = str(params.get("art") or "")
    if not art_id:
        if area.id not in chosen(context):
            raise ActionError(f"The {area.name} portal already shows its original picture.")
        return f"Put the {area.name} portal back to its original picture"
    store = _store(context)
    item = next((i for i in (store.all() if store is not None else []) if i["id"] == art_id), None)
    if item is None:
        raise ActionError("That picture isn't one of yours.")
    return f"Show the painting of {item['description'][:60]} in the {area.name} portal"


def _do(context, params) -> str:
    """Does `portal.picture`."""
    _describe(context, params)
    area = _area(str(params["area"]))
    art_id = str(params.get("art") or "")
    try:
        put_up(context, area.id, art_id)
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return (f"The {area.name} portal shows your painting now." if art_id
            else f"The {area.name} portal is back to its original picture.")


PORTAL_ACTIONS = {a.kind: a for a in (
    ActionType("portal.picture", "Use Here", {"area": "the area's id", "art": "one of your paintings' id, or empty for the original"},
               _describe, _do, child_ok=True),
)}
ACTION_TYPES.update(PORTAL_ACTIONS)
