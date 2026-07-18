"""
modules.maps.trail_map_fetch_worker
======================================

Runs core.trail_map_library.TrailMapLibrary.add_from_url() off the GUI
thread — a real network download, same one-shot QThread-per-run
pattern as modules/field_kit/script_worker.py's ScriptWorker.
add_from_local_file() needs no worker (no network I/O, just a local
file copy — fast enough for a direct call).
"""

from __future__ import annotations

import urllib.error
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.trail_map_library import NotAPdfError, TrailMap, TrailMapLibrary


class TrailMapFetchWorker(QThread):
    finished_fetch = Signal(object, str)  # (TrailMap or None, error message or "")

    def __init__(self, library: TrailMapLibrary, park_name: str, state: str, url: str, notes: str = "") -> None:
        super().__init__()
        self._library = library
        self._park_name = park_name
        self._state = state
        self._url = url
        self._notes = notes

    def run(self) -> None:
        try:
            trail_map: Optional[TrailMap] = self._library.add_from_url(
                self._park_name, self._state, self._url, self._notes
            )
            self.finished_fetch.emit(trail_map, "")
        except NotAPdfError as exc:
            self.finished_fetch.emit(None, str(exc))
        except (urllib.error.URLError, OSError) as exc:
            self.finished_fetch.emit(None, f"Couldn't download that URL: {exc}")
