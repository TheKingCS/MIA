"""
core.portal_pictures
=====================

The picture inside each portal in the Nexus, chosen by the person
(DEC-0140's "portal pictures painted by MIA"; since DEC-0153 the Nexus's
portals are the person's Living Worlds stories, core/web_nexus.worlds, and
the word "area" in the setting and the action means a portal's id).

What it does: every portal shows the picture made for it
(`web/img/portals/<id>.jpg`, H-0096) until the person puts one of their
own paintings there instead. `picture()` is what the Nexus draws (theirs,
else Muse's, else "" for the placeholder); `screen()` is the Portal Pictures
page; the action `portal.picture` puts one of their paintings on a
portal or takes it back to the original. A painting asked for "for the
Dragon Coast portal" goes up there by itself when it's done (`art_studio.settle`
calls `put_up`).

How: the choices are a personal setting, `nexus.portal_pictures`
({portal id: art id}), so each person's Nexus is their own and "undo" puts it
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


class _Portal:
    """A Nexus portal's id and name, for the sentences."""

    def __init__(self, portal: dict) -> None:
        """Keeps the portal's id and name."""
        self.id, self.name = portal["id"], portal["name"]


def _portals(context) -> list[dict]:
    """The Nexus's portals the person has (core/web_nexus.worlds)."""
    from core.web_nexus import worlds

    return worlds(context)


def _area(context, area_id: str) -> _Portal:
    """The portal by its id, or ActionError."""
    for portal in _portals(context):
        if portal["id"] == area_id:
            return _Portal(portal)
    raise ActionError("There's no portal like that in the Nexus.")


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
    """The portal someone means by its story's or world's name ("the Dragon Coast portal"), or None."""
    text = " ".join(str(words or "").lower().replace("portal", " ").split())
    text = text[4:] if text.startswith("the ") and text[4:] else text
    if not text:
        return None
    portals = _portals(context)
    for p in portals:
        if p["id"] == text or p["name"].lower() == text or (p.get("world") or "").lower() == text:
            return p["id"]
    for p in portals:
        for name in (p["name"].lower(), (p.get("world") or "").lower()):
            if name and (name in text or text in name):
                return p["id"]
    return None


def screen(context) -> dict:
    """The Portal Pictures page: each portal in the person's Nexus (their stories, under `areas` for the page) with
    what it shows and where that came from, the paintings they could put on one (portal paintings first), the
    paintings still going, and the image engine."""
    from core.art_studio import status
    from core.web_nexus import portal_art

    art = status(context)
    picks = chosen(context)
    areas = []
    for p in _portals(context):
        own = picks.get(p["id"], "")
        original = portal_art(p["id"])
        areas.append({"id": p["id"], "name": p["name"], "hue": p["hue"], "icon": p["icon"],
                      "picture": f"/api/art/{own}/image" if own else original,
                      "source": "yours" if own else ("original" if original else "none"),
                      "art_id": own, "original": original})
    items = sorted(art["items"], key=lambda i: i.get("use") != "portal")  # newest first already; portal ones first
    return {"areas": areas, "paintings": items,
            "jobs": [j for j in art["jobs"] if j.get("use") == "portal"], "engine": art["engine"]}


def _describe(context, params) -> str:
    """The approval sentence for `portal.picture`."""
    area = _area(context, str(params.get("area") or ""))
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
    area = _area(context, str(params["area"]))
    art_id = str(params.get("art") or "")
    try:
        put_up(context, area.id, art_id)
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return (f"The {area.name} portal shows your painting now." if art_id
            else f"The {area.name} portal is back to its original picture.")


PORTAL_ACTIONS = {a.kind: a for a in (
    ActionType("portal.picture", "Use Here", {"area": "the portal's id (a story's)", "art": "one of your paintings' id, or empty for the original"},
               _describe, _do, child_ok=True),
)}
ACTION_TYPES.update(PORTAL_ACTIONS)
