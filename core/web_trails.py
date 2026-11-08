"""
core.web_trails
=================

Trail Maps on the web (web/trails.html, DEC-0017 parity with the Qt Maps module's Trail Maps tab): the official park
and trail map PDFs kept on this MIA (core/trail_map_library.py), by state, each opening in the browser's own PDF
viewer. Added by sending a PDF from the device (`/api/trail-maps/upload`) or from a direct link
(`/api/trail-maps/fetch`, the same download the Qt tab and the add_trail_map_from_url tool make); a file that isn't
really a PDF is refused. Taking one out is the action `trail_map.delete`: its PDF is set aside (not erased), so Undo
brings it back whole.

`screen(context)` is what `/api/trail-maps` serves. The catalog is the device's (data/trail_maps.json), like the
offline map tiles: places, not personal records.
"""

from __future__ import annotations

from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

MAX_MB = 60  # a park map PDF is a few MB; this keeps an upload from filling the disk by mistake


def _library(context):
    """The trail map library, or None on a MIA without one."""
    return getattr(context, "trail_maps", None)


def screen(context) -> dict:
    """Trail Maps: every map grouped by state (A to Z, parks A to Z), with whether its PDF is here and its size."""
    lib = _library(context)
    if lib is None:
        return {"available": False}
    groups: dict[str, list] = {}
    for t in lib.all_trail_maps():
        path = lib.file_path(t.trail_map_id)
        groups.setdefault(t.state or "Somewhere", []).append({
            "id": t.trail_map_id, "park": t.park_name, "state": t.state, "notes": t.notes,
            "added": (t.added_at or "")[:10], "from_link": bool(t.source_url),
            "here": path is not None, "size_kb": round(path.stat().st_size / 1024) if path is not None else 0})
    return {"available": True, "count": sum(len(v) for v in groups.values()),
            "states": [{"state": state, "maps": maps} for state, maps in sorted(groups.items(), key=lambda g: g[0].lower())],
            "max_mb": MAX_MB}


def add_upload(context, park: str, state: str, data: bytes, notes: str = "") -> dict:
    """A PDF sent from the device, catalogued. ValueError (with the sentence to show) for a missing park or state, a
    file too big, or one that isn't a PDF."""
    from core.trail_map_library import NotAPdfError

    lib = _library(context)
    park, state = " ".join(str(park or "").split())[:80], " ".join(str(state or "").split())[:40]
    if lib is None:
        raise ValueError("Trail maps aren't set up on this MIA.")
    if not park or not state:
        raise ValueError("Which park, and which state?")
    if len(data) > MAX_MB * 1024 * 1024:
        raise ValueError(f"That file is over {MAX_MB} MB.")
    try:
        t = lib.add_from_bytes(park, state, data, str(notes or "")[:300])
    except NotAPdfError:
        raise ValueError("That file isn't a PDF. Trail maps are PDFs from the park's own site.") from None
    return {"id": t.trail_map_id, "message": f"{t.park_name} ({t.state}) is in your trail maps."}


def add_link(context, park: str, state: str, url: str, notes: str = "") -> dict:
    """A PDF downloaded from a direct link the person gave (http or https only), catalogued. ValueError with the
    sentence to show when it can't be."""
    import urllib.error

    from core.trail_map_library import NotAPdfError

    lib = _library(context)
    park, state, url = " ".join(str(park or "").split())[:80], " ".join(str(state or "").split())[:40], str(url or "").strip()
    if lib is None:
        raise ValueError("Trail maps aren't set up on this MIA.")
    if not park or not state:
        raise ValueError("Which park, and which state?")
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("Give the link to the PDF itself (starting with https://).")
    try:
        t = lib.add_from_url(park, state, url, str(notes or "")[:300])
    except NotAPdfError:
        raise ValueError("That link isn't a PDF. Open the park's map page and copy the link to the PDF itself.") from None
    except (urllib.error.URLError, OSError, ValueError) as problem:
        raise ValueError(f"Couldn't download it: {problem}") from None
    return {"id": t.trail_map_id, "message": f"{t.park_name} ({t.state}) is in your trail maps."}


def _need(context, params):
    """The map the params name; ActionError when it isn't there."""
    lib = _library(context)
    found = lib.get_trail_map(str(params.get("trail_map_id") or "")) if lib is not None else None
    if found is None:
        raise ActionError("That trail map isn't here.")
    return found


def _describe_delete(context, params) -> str:
    """The approval sentence for `trail_map.delete`."""
    t = _need(context, params)
    return f"Take the trail map for {t.park_name} ({t.state}) out"


def _delete(context, params) -> str:
    """Does `trail_map.delete`: out of the catalog, its PDF set aside so Undo brings it back."""
    t = _need(context, params)
    _library(context).delete_trail_map(t.trail_map_id)
    return f"Took out {t.park_name}. Undo brings it back."


def find(context, words: str) -> Optional[object]:
    """The trail map whose park (or park and state) the words name, or None."""
    lib = _library(context)
    said = " ".join(str(words or "").lower().split())
    if lib is None or not said:
        return None
    return next((t for t in lib.all_trail_maps() if said in t.park_name.lower() or t.park_name.lower() in said), None)


TRAIL_ACTIONS = {a.kind: a for a in (
    ActionType("trail_map.delete", "Take Out", {"trail_map_id": "the trail map"}, _describe_delete, _delete),
)}
ACTION_TYPES.update(TRAIL_ACTIONS)
