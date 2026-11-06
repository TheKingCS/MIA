"""
core.tak
==========

MIA's places in the open, civilian standards a TAK app speaks (build plan
step 14, DEC-0099): Cursor on Target events and KML, packed as a TAK data
package (a zip with a `MANIFEST/manifest.xml`) that ATAK-CIV, iTAK and
WinTAK import, so the person's waypoints show on their TAK map with MIA's
names, notes and MGRS grid references (core/geo_grid.py).

Nothing is sent anywhere: the package is a file the person carries to their
TAK app. (Sharing on the local network, Cursor on Target over UDP multicast,
waits for its own approval: a person's places are theirs.)

Also the quick phrases for grid references: "add a waypoint called Spring at
18S UJ 23478 06483", "what's the grid for Spring?".
"""

from __future__ import annotations

import io
import re
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Optional
from xml.sax.saxutils import escape, quoteattr

from core import geo_grid

MARKER = "b-m-p-s-m"  # a spot map marker, the plain point every TAK app shows
STALE = timedelta(days=365)


def _when(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def cot_event(waypoint, now: Optional[datetime] = None) -> str:
    """Pure logic. One waypoint as a Cursor on Target event (XML)."""
    now = now or datetime.now(timezone.utc)
    grid = geo_grid.to_mgrs(waypoint.latitude, waypoint.longitude)
    remarks = " ".join(x for x in (grid, waypoint.category, waypoint.notes) if x)
    return (f'<event version="2.0" uid={quoteattr("MIA-" + waypoint.waypoint_id)} type="{MARKER}" how="h-g-i-g-o" '
            f'time="{_when(now)}" start="{_when(now)}" stale="{_when(now + STALE)}">'
            f'<point lat="{waypoint.latitude:.7f}" lon="{waypoint.longitude:.7f}" hae="9999999.0" ce="9999999.0" '
            f'le="9999999.0"/><detail><contact callsign={quoteattr(waypoint.name)}/>'
            f'<remarks>{escape(remarks)}</remarks><precisionlocation altsrc="???" geopointsrc="USER"/></detail></event>')


def kml(waypoints, title: str = "MIA's places", tracks=()) -> str:
    """Pure logic. The waypoints as KML placemarks, each with its grid reference; tracks as lines."""
    marks = "".join(
        f"<Placemark><name>{escape(w.name)}</name><description>"
        f"{escape(' · '.join(x for x in (geo_grid.to_mgrs(w.latitude, w.longitude), w.category, w.notes) if x))}"
        f"</description><Point><coordinates>{w.longitude:.7f},{w.latitude:.7f},0</coordinates></Point></Placemark>"
        for w in waypoints)
    lines = "".join(
        f"<Placemark><name>{escape(t['name'])}</name><description>{escape(_track_line(t))}</description>"
        f"<LineString><coordinates>{_coordinates(t['points'])}</coordinates>"
        f"</LineString></Placemark>" for t in tracks)
    return (f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"<name>{escape(title)}</name>{marks}{lines}</Document></kml>")


def _coordinates(points: list) -> str:
    return " ".join("%.6f,%.6f,0" % (p["lon"], p["lat"]) for p in points)


def _track_line(track: dict) -> str:
    from core.gps_tracks import describe

    return describe(track)


def data_package(waypoints, name: str = "MIA places", now: Optional[datetime] = None, tracks=()) -> bytes:
    """Pure logic. A TAK data package (zip): one .cot per waypoint, the KML (with tracks as lines), and the
    manifest that lists them."""
    entries = {f"{w.waypoint_id}/{w.waypoint_id}.cot": cot_event(w, now) for w in waypoints}
    entries["MIA_places.kml"] = kml(waypoints, name, tracks)
    contents = "".join(f'<Content ignore="false" zipEntry={quoteattr(path)}/>' for path in entries)
    manifest = (f'<MissionPackageManifest version="2"><Configuration>'
                f'<Parameter name="uid" value="{uuid.uuid4()}"/><Parameter name="name" value={quoteattr(name)}/>'
                f'<Parameter name="onReceiveDelete" value="false"/></Configuration>'
                f"<Contents>{contents}</Contents></MissionPackageManifest>")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("MANIFEST/manifest.xml", manifest)
        for path, text in entries.items():
            z.writestr(path, text)
    return out.getvalue()


# ------------------------------------------------------------------ talking to it

_GRID = r"(\d{1,2}\s*[C-HJ-NP-X]\s*[A-HJ-NP-Z][A-HJ-NP-V]\s*\d{0,5}\s*\d{0,5})"
_ADD = re.compile(rf"^(?:add|save|mark)\s+(?:a\s+)?waypoint\s+(?:called\s+|named\s+)?(.+?)\s+at\s+{_GRID}[.!]*$",
                  re.IGNORECASE)
_ASK = re.compile(r"^(?:what'?s|what is|give me)\s+the\s+grid(?:\s+reference)?\s+(?:for|of)\s+(.+?)[?.!]*$",
                  re.IGNORECASE)


def reply(context, text: str) -> Optional[str]:
    """"add a waypoint called Spring at 18S UJ 23478 06483", "what's the grid for Spring?". None otherwise."""
    store = getattr(context, "waypoints", None)
    if store is None:
        return None
    said = " ".join(str(text or "").split())
    added, asked = _ADD.match(said), _ASK.match(said)
    if added:
        try:
            lat, lon = geo_grid.from_mgrs(added.group(2))
        except geo_grid.GridError as problem:
            return str(problem)
        w = store.add_waypoint(name=added.group(1).strip(), latitude=lat, longitude=lon)
        return f"Waypoint '{w.name}' saved at {geo_grid.to_mgrs(lat, lon)} ({lat:.5f}, {lon:.5f})."
    if asked:
        want = asked.group(1).strip().lower()
        found = next((w for w in store.all_waypoints() if w.name.lower() == want), None) or \
            next((w for w in store.all_waypoints() if want in w.name.lower()), None)
        if found is None:
            return None
        return f"{found.name} is at {geo_grid.to_mgrs(found.latitude, found.longitude)}."
    return None
