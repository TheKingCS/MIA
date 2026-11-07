"""
tools.tracks
==============

Tracks from GPX files (core/gps_tracks.py, DEC-0099), into the signed-in person's own folder.

    python -m tools.tracks                    every track, newest first
    python -m tools.tracks add walk.gpx ["A name"]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    """The GPS tracks' command line: add a GPX file (with a name), or list the tracks in a line each. Returns the exit code."""
    from core.gps_tracks import TrackError, describe
    from tools.intelligence_check import build_context

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.disable(logging.INFO)
    store = getattr(build_context(), "gps_tracks", None)
    if store is None:
        print("No tracks store here.")
        return 1
    if argv[:1] == ["add"] and len(argv) > 1:
        try:
            track = store.add_gpx(Path(argv[1]).read_text(encoding="utf-8", errors="replace"), " ".join(argv[2:]))
        except (OSError, TrackError) as problem:
            print(problem)
            return 1
        print(describe(track))
        return 0
    for track in sorted(store.tracks, key=lambda t: t["stats"].get("date") or t["added"], reverse=True):
        print(describe(track))
    if not store.tracks:
        print("No tracks yet: python -m tools.tracks add walk.gpx")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
