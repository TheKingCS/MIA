"""
core.web_environments
=======================

An area's own environment (DEC-0130, NEXUS_PLAN M3): going through a portal
lands in a space laid out for that part of life, not a grid of app tiles.
The hub (core/web_areas.hub) carries `environment` for areas that have one;
the others keep their tiles until their turn. Garage is first.

- `garage(context, today)`: the Garage as a workshop. Its bays (each
  vehicle, tool or appliance: photo, make, meter, what's overdue and what's
  next; from core/web_equipment.equipment_page), what needs you, the parts
  running low or out across every asset (core/asset_parts.py), and the
  bench's tools (Toolbox, Look, Workshop, Projects, the parts inventory).
- `room(context, area_id, today)`: every other area, as a room of its apps
  round MIA's orb (doors with what waits in each, and what needs you).
- `ENVIRONMENTS`: area id -> its own builder; the rest get `room`.

Where the graphics card allows, the page draws the Garage as a 3D room on the
Nexus's engine (web/hub.js garageRoom, web/nexus3d.js): the bays round MIA's
orb. Read-only: every change is made on the screens these link to, through
their own actions.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

BENCH = (
    {"id": "toolbox", "name": "Toolbox", "icon": "toolbox", "page": "toolbox.html", "line": "Quick tools and timers"},
    {"id": "inventory", "name": "Parts and Inventory", "icon": "toolbox", "page": "toolbox.html#inventory",
     "line": "What's on the shelves"},
    {"id": "sight", "name": "Look", "icon": "sight", "page": "look.html", "line": "Show MIA a part or a problem"},
    {"id": "workshop", "name": "Workshop", "icon": "workshop", "page": "workshop.html", "line": "Jobs, materials, products"},
    {"id": "projects", "name": "Projects", "icon": "workshop", "page": "projects.html", "line": "Builds and their tasks"},
)


def low_parts(context, asset_ids: list[str]) -> list[dict]:
    """The parts running low or out across these assets, each once with the assets that use it ([{name, have, unit,
    state, used_by}]), out first."""
    from core.asset_parts import parts_for

    maintenance = getattr(context, "maintenance", None)
    names = {a.asset_id: a.name for a in maintenance.all_assets()} if maintenance is not None else {}
    found: dict[str, dict] = {}
    for asset_id in asset_ids:
        for part in parts_for(context, asset_id):
            if part["state"] == "ok":
                continue
            row = found.setdefault(part["ref"], {**part, "used_by": []})
            row["used_by"].append(names.get(asset_id, ""))
    return sorted(found.values(), key=lambda r: (r["state"] != "out", r["name"].lower()))


def garage(context, today: Optional[date] = None) -> dict:
    """The Garage environment: bays, what needs you, low parts, and the bench (see the module's docstring)."""
    from core.web_equipment import equipment_page

    today = today or date.today()
    page = equipment_page(context, "garage", today)
    if not page.get("available"):
        return {"kind": "garage", "available": False, "bench": list(BENCH)}
    bays = []
    for a in page.get("assets") or []:  # the Garage's own (all_assets is everything, the house's too)
        upcoming = [t for t in a.get("tasks", []) if t.get("text")]
        bays.append({"id": a["id"], "name": a["name"], "category": a.get("category", ""), "make_model": a.get("make_model", ""),
                     "photo": a.get("photo", ""), "meter": a.get("meter"), "overdue": a.get("overdue", 0),
                     "next": upcoming[0] if upcoming else None, "page": f"asset.html?id={a['id']}"})
    bays.sort(key=lambda b: (-int(b["overdue"] or 0), b["name"].lower()))
    return {"kind": "garage", "available": True, "bays": bays,
            "needs": [{"title": t["title"], "asset": t.get("asset", ""), "text": t.get("text", ""),
                       "page": f"asset.html?id={t['asset_id']}" if t.get("asset_id") else "garage.html"}
                      for t in (page.get("attention") or [])[:6]],
            "parts": low_parts(context, [b["id"] for b in bays]), "bench": list(BENCH)}


def room(context, area_id: str, today: Optional[date] = None) -> Optional[dict]:
    """Any other area as a room (DEC-0130 M5's first pass, 2026-11-08): its apps and pages stand round MIA's orb as
    doors, each with how many of today's overdue or due items wait in it, and the area's list of what needs you (today's
    overdue and due items whose app is in the area, at most six). A destination's subdashboards are doors too
    (DEC-0153), each counting the items of the apps inside it. The page draws it only in the Spatial look where the
    graphics card allows; the Cards look and every other device keep the area's tiles. None for an unknown area."""
    from core.web_areas import _entries, _sub_entry, children, resolve

    area = resolve(area_id)
    if area is None:
        return None
    from core.web_nexus import _today

    today = today or date.today()
    items = [i for i in _today(context, today) if i.get("when") in ("overdue", "today")]
    doors, page_of = [], {}
    for sub_area in children(area.id):
        inside = _entries(context, sub_area.members)
        if not inside:
            continue
        ids = {e["id"] for e in inside}
        page_of.update({e["id"]: e["page"] for e in inside})
        doors.append({**_sub_entry(sub_area), "needs": sum(1 for i in items if i.get("module_id") in ids)})
    for entry in _entries(context, area.members):
        page_of[entry["id"]] = entry["page"]
        doors.append({**entry, "needs": sum(1 for i in items if i.get("module_id") == entry["id"])})
    needs = [{"title": i.get("title", ""), "text": i.get("detail") or ("overdue" if i["when"] == "overdue" else "today"),
              "app": i.get("module_id", ""), "page": page_of[i.get("module_id")]}
             for i in items if i.get("module_id") in page_of][:6]
    return {"kind": "room", "available": bool(doors), "doors": doors, "needs": needs}


ENVIRONMENTS = {"garage": garage}


def environment(context, area_id: str, today: Optional[date] = None) -> Optional[dict]:
    """An area's environment: its own (the Garage's workshop), else the room of its apps (`room`); None when building it
    fails, so the hub's tiles show."""
    build = ENVIRONMENTS.get(area_id)
    try:
        return build(context, today) if build is not None else room(context, area_id, today)
    except Exception:
        log.exception("Environment %s failed; the hub's tiles show instead", area_id)
        return None
