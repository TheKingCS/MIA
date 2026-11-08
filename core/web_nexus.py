"""
core.web_nexus
================

The Nexus (DEC-0130, Zac 2026-11-08): MIA's spatial home. A chamber of
portals, one per area (core/web_areas.AREAS), around MIA's orb, with the HUD
across the top. This module is what the page shows; `web/nexus.html` and
`web/spatial.js` only draw it.

- `portal_status(items)` (pure): for each area, how many of today's items
  in its apps need you (overdue or today), from core/today.py, so a portal
  can glow when something inside it wants attention.
- `wants_area(prompt)` (pure): "take me to the garage", "open finances",
  "go to the Nexus" -> where to go (the area's hub, or the Nexus), for the
  turn to open at once (core/assistant_turn.py), no model.
- `portal_art(area_id)`: the picture inside a portal in the room, once
  Muse's is in web/img/portals/ (H-0096), else "".
- `nexus(context, today)`: the portals (id, name, icon, hue, hub page,
  line, what needs you, art), the HUD (name, level, XP to the next level, active
  missions) and the day in one line, for the page.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import re

from core.logger import get_logger
from core.web_areas import AREAS, areas_of

log = get_logger(__name__)


def portal_status(items: list) -> dict[str, int]:
    """Pure logic. {area id: how many of today's overdue or today items belong to an app in it}; an item counts in
    every area its app is in."""
    out: dict[str, int] = {}
    for item in items:
        if item.get("when") not in ("overdue", "today"):
            continue
        for area in areas_of(item.get("module_id") or ""):
            out[area] = out.get(area, 0) + 1
    return out


PORTAL_ART = Path(__file__).resolve().parent.parent / "web" / "img" / "portals"


def portal_art(area_id: str) -> str:
    """The picture inside an area's portal in the room (web/nexus3d.js), as a page path, or "" until Muse's picture
    for it is in web/img/portals/<area id>.jpg (H-0096): the room draws a placeholder in the area's colour meanwhile."""
    return f"img/portals/{area_id}.jpg" if (PORTAL_ART / f"{area_id}.jpg").is_file() else ""


def _today(context, today: date) -> list[dict]:
    """Today's items as dicts ([] if they can't be read)."""
    try:
        from core.today import today_items

        return [i.as_dict() for i in today_items(context, today)]
    except Exception:
        log.exception("Nexus: today failed")
        return []


def _missions(context) -> int:
    """How many missions are active ([] store: 0)."""
    missions = getattr(context, "missions", None)
    try:
        return sum(1 for m in missions.all_missions() if m.status == "active") if missions is not None else 0
    except Exception:
        log.exception("Nexus: missions failed")
        return 0


def nexus(context, today: Optional[date] = None) -> dict:
    """The Nexus screen: portals in sidebar order with what needs you in each and its picture (the person's own
    painting if they put one there, core/portal_pictures, else Muse's once it's in), the HUD, and the day in one line."""
    from core.portal_pictures import picture
    from core.web_areas import sidebar
    from core.web_surfaces import _level, _profile, date_text

    today = today or date.today()
    items = _today(context, today)
    status = portal_status(items)
    visible = {a["id"] for a in sidebar(context)}
    portals = [{"id": a.id, "name": a.name, "icon": a.icon, "hue": a.hue, "line": a.tagline,
                "page": f"hub.html?area={a.id}", "needs": status.get(a.id, 0), "art": picture(context, a.id)}
               for a in AREAS if a.id in visible]
    _pid, profile = _profile(context)
    due = sum(1 for i in items if i.get("when") in ("overdue", "today"))
    return {
        "date": date_text(today),
        "portals": portals,
        "hud": {"name": getattr(profile, "name", None), **_level(profile), "missions": _missions(context)},
        "day": (f"{due} thing{'s' if due != 1 else ''} need{'s' if due == 1 else ''} you today" if due
                else "Nothing needs you today"),
    }


_GO = re.compile(r"^\s*(?:hey\s+mia[,\s]+)?(?:please\s+)?(?:take me (?:to|into)|go (?:to|into)|open(?: up)?|show me|bring up|"
                 r"jump to|head to)\s+(?:the\s+|my\s+)?(.+?)[\s.!?]*$", re.I)
_ALIASES = {"plants": "plants_animals", "animals": "plants_animals", "fitness": "health", "health": "health",
            "settings": "system", "diagnostics": "system", "money": "finances", "finance": "finances",
            "comms": "communications", "messages": "communications", "adventures": "recreation"}


def wants_area(prompt: str) -> Optional[tuple[str, str]]:
    """Pure logic. (where to open, its name) when the words ask to go to an area or the Nexus, else None. Matches the
    area's whole name (and a few everyday names: "money", "fitness", "settings"), never a word inside a longer request
    ("open the garage door" isn't the Garage: the name has to be all that's left)."""
    m = _GO.match(prompt or "")
    if not m:
        return None
    asked = re.sub(r"\s+(?:area|hub|portal|page|screen|section)$", "", m.group(1).strip().lower())
    asked = asked.replace("&", "and")
    if asked in ("nexus", "the nexus", "home screen"):
        return "nexus.html", "the Nexus"
    for area in AREAS:
        if asked in (area.name.lower(), area.id.replace("_", " ")):
            return f"hub.html?area={area.id}", area.name
    if asked in _ALIASES:
        area = next(a for a in AREAS if a.id == _ALIASES[asked])
        return f"hub.html?area={area.id}", area.name
    return None
