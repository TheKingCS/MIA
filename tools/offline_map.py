"""
tools.offline_map
===================

Cut an area of OpenStreetMap into a vector offline map (core/offline_maps.py), kept in data/maps/ and drawn on
the web's Maps page.

    .venv\\Scripts\\python -m tools.offline_map list
    .venv\\Scripts\\python -m tools.offline_map cut home --around-waypoints 10      every waypoint, 10 km around
    .venv\\Scripts\\python -m tools.offline_map cut trip --bbox -105.1,39.9,-104.9,40.1 --maxzoom 14
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str]) -> int:
    """The command line: `list` the areas kept, or `cut <name>` with --bbox or --around-waypoints (and --maxzoom).
    Returns 0 when it worked, 1 with the reason printed when it didn't.
    """
    from core import offline_maps as om

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="tools.offline_map")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    cut = sub.add_parser("cut")
    cut.add_argument("name")
    cut.add_argument("--bbox", help="west,south,east,north in degrees")
    cut.add_argument("--around-waypoints", type=float, metavar="KM")
    cut.add_argument("--maxzoom", type=int, default=om.MAX_ZOOM)
    args = parser.parse_args(argv)
    if args.command == "list":
        for m in om.maps():
            print(f"{m['name']}: {m['size_mb']} MB, zoom {m['min_zoom']}-{m['max_zoom']}, bounds {m['bounds']}")
        return 0
    if args.bbox:
        box = tuple(float(v) for v in args.bbox.split(","))
    elif args.around_waypoints:
        from core.waypoint_manager import WaypointManager

        points = [(w.latitude, w.longitude) for w in WaypointManager(None).all_waypoints()]
        box = om.around(points, args.around_waypoints)
        if box is None:
            print("No waypoints to cut around.")
            return 1
    else:
        print("Give --bbox or --around-waypoints.")
        return 1
    try:
        path = om.extract(args.name, box, args.maxzoom)
    except ValueError as problem:
        print(problem)
        return 1
    print(f"{path}: {path.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
