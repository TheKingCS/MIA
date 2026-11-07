"""
core.offline_maps
===================

Vector offline maps (build plan step 14; Zac's OK for the outside code,
2026-11-06): an area of OpenStreetMap cut from the Protomaps daily world
build into one small file (PMTiles), kept on this PC in `data/maps/`, and
drawn by MapLibre on the web's Maps page (`web/vendor/`). Unlike the topo
tiles (US only), it covers anywhere, and stays sharp at every zoom.

- **Cutting an area** (`extract()`, `python -m tools.offline_map`): the
  `pmtiles` tool fetches only the bytes of the area asked for (an 8 km
  square to street level is about 2.5 MB, a few seconds). The map server
  sees which area is asked for (as USGS does for the topo tiles); nothing
  else about the person is sent.
- **Which areas**: a box given, or around the waypoints (`around()`).
- **Reading one** (`header()`): its bounds, zoom range and centre come
  from the file's own 127-byte header, so the page can open on it.
"""

from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR = ROOT / "data" / "maps"
TOOL = Path.home() / "DevTools" / "pmtiles" / "pmtiles.exe"
BUILDS = "https://build-metadata.protomaps.dev/builds.json"
BUILD_URL = "https://build.protomaps.com/{key}"
MAX_ZOOM = 15
_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


def valid_name(name: str) -> bool:
    """Pure logic. A map's name: lowercase letters, digits, - and _ (it's a file name)."""
    return bool(_NAME.match(name or ""))


def around(points: list[tuple[float, float]], km: float = 5.0) -> Optional[tuple[float, float, float, float]]:
    """Pure logic. The box (min lon, min lat, max lon, max lat) around (lat, lon) points, `km` beyond them."""
    if not points:
        return None
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    dlat = km / 111.0
    dlon = km / (111.0 * max(0.1, math.cos(math.radians(sum(lats) / len(lats)))))
    return (round(max(-180.0, min(lons) - dlon), 5), round(max(-85.0, min(lats) - dlat), 5),
            round(min(180.0, max(lons) + dlon), 5), round(min(85.0, max(lats) + dlat), 5))


def header(path: Path) -> Optional[dict]:
    """A PMTiles v3 file's header: {min_zoom, max_zoom, bounds [w, s, e, n], center [lon, lat], center_zoom}."""
    try:
        with open(path, "rb") as f:
            head = f.read(127)
    except OSError:
        return None
    if len(head) < 127 or head[:7] != b"PMTiles" or head[7] != 3:
        return None
    min_zoom, max_zoom = head[100], head[101]
    w, s, e, n = (v / 1e7 for v in struct.unpack_from("<iiii", head, 102))
    center_zoom = head[118]
    clon, clat = (v / 1e7 for v in struct.unpack_from("<ii", head, 119))
    return {"min_zoom": min_zoom, "max_zoom": max_zoom, "bounds": [w, s, e, n], "center": [clon, clat],
            "center_zoom": center_zoom}


def maps(folder: Optional[Path] = None) -> list[dict]:
    """The areas kept on this PC: [{name, size_mb, bounds, center, max_zoom}]."""
    folder = folder or MAPS_DIR
    out = []
    for path in sorted(folder.glob("*.pmtiles")) if folder.exists() else []:
        found = header(path)
        if found is not None and valid_name(path.stem):
            out.append({"name": path.stem, "size_mb": round(path.stat().st_size / 1e6, 1), **found})
    return out


def path_of(name: str, folder: Optional[Path] = None) -> Optional[Path]:
    if not valid_name(name):
        return None
    folder = folder or MAPS_DIR
    path = folder / f"{name}.pmtiles"
    return path if path.exists() else None


def _get(url: str) -> bytes:
    # A plain Python User-Agent is refused (403); the same name the topo tiles use (core/map_tile_cache.py)
    request = urllib.request.Request(url, headers={"User-Agent": "MIA-Home/0.2"})
    with urllib.request.urlopen(request, timeout=30) as answer:
        return answer.read()


def latest_build(get: Callable[[str], bytes] = _get) -> str:
    """The newest Protomaps world build's URL."""
    builds = json.loads(get(BUILDS))
    return BUILD_URL.format(key=sorted(b["key"] for b in builds if b["key"].endswith(".pmtiles"))[-1])


def extract(name: str, box: tuple[float, float, float, float], max_zoom: int = MAX_ZOOM, source: str = "",
            run: Callable = subprocess.run, folder: Optional[Path] = None) -> Path:
    """Cut the box out of the world build into data/maps/<name>.pmtiles. Raises ValueError with why it can't."""
    if not valid_name(name):
        raise ValueError("A map's name is lowercase letters, digits, - and _.")
    w, s, e, n = box
    if not (-180 <= w < e <= 180 and -85 <= s < n <= 85):
        raise ValueError("That box isn't on the map.")
    if not TOOL.exists():
        raise ValueError(f"The pmtiles tool isn't at {TOOL}.")
    folder = folder or MAPS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{name}.pmtiles"
    done = run([str(TOOL), "extract", source or latest_build(), str(out), f"--bbox={w},{s},{e},{n}",
                f"--maxzoom={max(0, min(MAX_ZOOM, int(max_zoom)))}"], capture_output=True, text=True,
               encoding="utf-8", errors="replace", timeout=3600,
               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if done.returncode != 0 or header(out) is None:
        raise ValueError(f"The cut didn't finish: {(done.stderr or done.stdout or '')[-300:]}")
    return out


# ------------------------------------------------------------------ from the Maps page (the action contract)

MAX_AREA_DEG = 2.0  # a box this many degrees a side at most (about 200 km): a county, not a country, from a tap


def _box(params) -> tuple[float, float, float, float]:
    from core.actions import ActionError

    try:
        box = tuple(float(params.get(k)) for k in ("west", "south", "east", "north"))
    except (TypeError, ValueError):
        raise ActionError("Which area? Its west, south, east and north edges.") from None
    w, s, e, n = box
    if not (-180 <= w < e <= 180 and -85 <= s < n <= 85):
        raise ActionError("That area isn't on the map.")
    if e - w > MAX_AREA_DEG or n - s > MAX_AREA_DEG:
        raise ActionError("That's a big area: zoom in to a county or smaller, or cut it at the PC with "
                          "`python -m tools.offline_map`.")
    return box


def _area_name(params) -> str:
    from core.actions import ActionError

    name = re.sub(r"[^a-z0-9_-]+", "-", str(params.get("name") or "").strip().lower()).strip("-")[:40]
    if not valid_name(name):
        raise ActionError("What should the area be called?")
    return name


def _describe_cut(context, params) -> str:
    w, s, e, n = _box(params)
    return f"Keep the map of this area offline as \"{_area_name(params)}\" (about {(e - w) * 85:.0f} × {(n - s) * 111:.0f} km)"


def _cut(context, params) -> str:
    import threading

    from core import live

    name, box = _area_name(params), _box(params)

    def run():
        notifications = getattr(context, "notifications", None)
        try:
            path = extract(name, box)
            said = f"The map of {name} is on this PC ({path.stat().st_size / 1e6:.1f} MB): it works with no signal."
        except Exception as problem:
            said = f"The map of {name} couldn't be cut: {str(problem)[:200]}"
        live.bump()  # the Maps page reads again
        if notifications is not None:
            try:
                notifications.notify("🗺 Offline map", said, source="maps")
            except Exception:
                pass
    threading.Thread(target=run, name="mia-map-cut", daemon=True).start()
    return f"Cutting {name}: it'll be on the map in a minute (you'll get a note)."


def _describe_remove(context, params) -> str:
    from core.actions import ActionError

    name = str(params.get("name") or "")
    if path_of(name) is None:
        raise ActionError("That map area isn't on this PC.")
    return f"Take the offline map {name} off this PC"


def _remove(context, params) -> str:
    from core import live

    found = path_of(str(params.get("name") or ""))
    if found is not None:
        found.unlink()
        live.bump()
    return "Taken off."


def _register() -> None:
    from core.actions import ACTION_TYPES, ActionType

    ACTION_TYPES.update({a.kind: a for a in (
        ActionType("map.area_keep", "Keep offline", {"name": "what to call it", "west": "degrees", "south": "degrees",
                                                      "east": "degrees", "north": "degrees"}, _describe_cut, _cut),
        ActionType("map.area_remove", "Take it off", {"name": "the area"}, _describe_remove, _remove),
    )})
