"""
core.web_nexus
================

The Nexus (DEC-0130; since DEC-0153, Zac 2026-11-11, only the gateway to
Living Worlds): a chamber of portals around MIA's orb, one per story you
can step into (each campaign in core/living_worlds.py, with its world),
and one to make a new world. It is no longer how MIA's apps are found:
those are the eight destinations (core/web_areas.py). On the PC and the
phone it opens from Living Worlds in Recreation; on the glasses it is the
third screen. This module is what the page shows; `web/nexus.html` and
`web/spatial.js` only draw it.

- `portal_status(items)` (pure): for each area, how many of today's items
  in its apps need you (overdue or today), counted in the area that owns
  the app and in its destination, for the glasses' menu and the rooms.
- `wants_area(prompt)` (pure): "take me to the garage", "open the
  homestead", "go to the Nexus" -> where to go (a destination's or
  subdashboard's hub, the Dashboard, or the Nexus), for the turn to open at
  once (core/assistant_turn.py), no model.
- `portal_art(portal_id)`: the picture made for a portal, once it is in
  web/img/portals/, else "".
- `worlds(context)`: the portals: each campaign (in play first, ended
  last) and "Make a world", with name, line, hue and page.
- `nexus(context, today)`: the portals with their pictures, the HUD (name,
  level, XP to the next level, active missions) and a line about the
  worlds, for the page.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import re

from core.logger import get_logger
from core.web_areas import AREAS, areas_of, top_of

log = get_logger(__name__)

# The worlds' hues: the areas' own (never amber or red, which mean "needs you" and "error"), one per world in turn.
WORLD_HUES = ("#9b6bff", "#35d4ff", "#c86bff", "#6a5cff", "#ff8ad8", "#7f95ff", "#6fc6ff", "#b9a8ff")
NEW_WORLD = "new_world"


def portal_status(items: list) -> dict[str, int]:
    """Pure logic. {area id: how many of today's overdue or today items belong to an app in it}; an item counts in
    the area that owns its app and in that area's destination."""
    out: dict[str, int] = {}
    for item in items:
        if item.get("when") not in ("overdue", "today"):
            continue
        for area in areas_of(item.get("module_id") or ""):
            for where in {area, top_of(area)}:
                out[where] = out.get(where, 0) + 1
    return out


PORTAL_ART = Path(__file__).resolve().parent.parent / "web" / "img" / "portals"


def portal_art(portal_id: str) -> str:
    """The picture made for a portal (web/nexus3d.js draws it), as a page path, or "" until one is in
    web/img/portals/<id>.jpg (H-0096): the room draws a placeholder in the portal's colour meanwhile."""
    return f"img/portals/{portal_id}.jpg" if (PORTAL_ART / f"{portal_id}.jpg").is_file() else ""


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


def worlds(context) -> list[dict]:
    """The Nexus's portals: each campaign as {id, name, icon, hue (its world's), line, page, status, world}, those in
    play first, then paused, then ended, each group by when it was last played; then "Make a world" (worlds.html).
    A MIA without Living Worlds has only that one."""
    book = getattr(context, "living_worlds", None) if context is not None else None
    out = []
    try:
        universes = list(book.universes) if book is not None else []
        hue = {u.universe_id: WORLD_HUES[i % len(WORLD_HUES)] for i, u in enumerate(universes)}
        name = {u.universe_id: u.name for u in universes}
        order = {"active": 0, "paused": 1}
        campaigns = sorted(book.campaigns if book is not None else [], key=lambda c: c.last_played or "", reverse=True)
        campaigns.sort(key=lambda c: order.get(c.status, 2))  # stable: in play first, each group latest played first
        for c in campaigns:
            world = name.get(c.universe_id, "")
            out.append({"id": c.campaign_id, "name": c.name, "icon": "character", "hue": hue.get(c.universe_id, WORLD_HUES[0]),
                        "line": " · ".join(x for x in (world, c.summary) if x) or "A story in your worlds.",
                        "page": f"worlds.html?campaign={c.campaign_id}", "status": c.status, "world": world})
    except Exception:
        log.exception("Nexus: the worlds couldn't be read")
        out = []
    out.append({"id": NEW_WORLD, "name": "Make a World", "icon": "plus", "hue": "#35d4ff",
                "line": "A new world, a campaign and your character in it.", "page": "worlds.html", "status": "",
                "world": ""})
    return out


def nexus(context, today: Optional[date] = None) -> dict:
    """The Nexus screen: the worlds' portals (worlds) with their pictures (the person's own painting if they put one
    there, core/portal_pictures, else one made for it), the HUD, the date, and a line about the stories in play."""
    from core.portal_pictures import picture
    from core.web_surfaces import _level, _profile, date_text

    today = today or date.today()
    portals = [{**p, "needs": 0, "art": picture(context, p["id"])} for p in worlds(context)]
    _pid, profile = _profile(context)
    playing = sum(1 for p in portals if p["status"] == "active")
    return {
        "date": date_text(today),
        "portals": portals,
        "hud": {"name": getattr(profile, "name", None), **_level(profile), "missions": _missions(context)},
        "day": (f"{playing} {'story' if playing == 1 else 'stories'} in play" if playing
                else "No story in play yet: make a world"),
    }


_GO = re.compile(r"^\s*(?:hey\s+mia[,\s]+)?(?:please\s+)?(?:take me (?:to|into)|go (?:to|into)|open(?: up)?|show me|bring up|"
                 r"jump to|head to)\s+(?:the\s+|my\s+)?(.+?)[\s.!?]*$", re.I)
# Everyday names, and DEC-0129's area names, for the area that holds them now.
_ALIASES = {"plants": "homestead", "animals": "homestead", "plants and animals": "homestead", "fitness": "health",
            "health": "health", "health and fitness": "health", "settings and diagnostics": "settings",
            "diagnostics": "system", "money": "finances", "finance": "finances", "comms": "ai_tools",
            "communications": "ai_tools", "messages": "ai_tools", "adventures": "recreation", "personal": "personal_tools",
            "business": "businesses", "devices": "smart_devices", "smart home": "smart_devices", "ai": "ai_tools"}
_DASHBOARD = ("dashboard", "home screen", "today", "overview")
_NEXUS = ("nexus", "the nexus", "living worlds", "worlds", "convergence", "the convergence")


def wants_area(prompt: str) -> Optional[tuple[str, str]]:
    """Pure logic. (where to open, its name) when the words ask to go to a destination, a subdashboard, the Dashboard
    or the Nexus, else None. Matches the area's whole name (and a few everyday or older names: "money", "fitness",
    "plants and animals"), never a word inside a longer request ("open the garage door" isn't the Garage: the name
    has to be all that's left)."""
    from core.web_areas import _page

    m = _GO.match(prompt or "")
    if not m:
        return None
    asked = re.sub(r"\s+(?:area|hub|portal|page|screen|section|dashboard)$", "", m.group(1).strip().lower())
    asked = asked.replace("&", "and").replace("+", "and")
    if asked in _NEXUS:
        return "nexus.html", "the Nexus"
    if asked in _DASHBOARD or m.group(1).strip().lower() in _DASHBOARD:
        return "index.html", "the Dashboard"
    for area in AREAS:
        if asked in (area.name.lower(), area.id.replace("_", " ")):
            return _page(area), area.name
    if asked in _ALIASES:
        area = next(a for a in AREAS if a.id == _ALIASES[asked])
        return _page(area), area.name
    return None
