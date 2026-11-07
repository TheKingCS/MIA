"""
tools.tak_export
==================

MIA's waypoints as a TAK data package (core/tak.py, DEC-0099): open it in
ATAK-CIV, iTAK or WinTAK (Import, then the file) and the places show on the
TAK map with their names, notes and MGRS grid references. Nothing is sent: it's
a file you carry to the TAK app.

    python -m tools.tak_export                       (writes MIA_places.zip in your Documents folder)
    python -m tools.tak_export C:\\path\\to\\file.zip
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    """Exports every waypoint and GPS track as a TAK data package (a zip, to Documents/MIA_places.zip unless a path is given) for ATAK or iTAK. Returns 1 when there's nothing to export."""
    from core import tak
    from tools.intelligence_check import build_context

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.disable(logging.INFO)
    context = build_context()
    waypoints = context.waypoints.all_waypoints() if getattr(context, "waypoints", None) is not None else []
    tracks = context.gps_tracks.tracks if getattr(context, "gps_tracks", None) is not None else []
    if not waypoints and not tracks:
        print("No waypoints yet: add one (\"add a waypoint called Spring at 18S UJ 23478 06483\").")
        return 1
    target = Path(argv[0]) if argv else Path.home() / "Documents" / "MIA_places.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(tak.data_package(waypoints, tracks=tracks))
    print(f"{len(waypoints)} waypoint{'s' if len(waypoints) != 1 else ''} and {len(tracks)} "
          f"track{'s' if len(tracks) != 1 else ''} in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
