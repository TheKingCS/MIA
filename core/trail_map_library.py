"""
core.trail_map_library
=========================

A catalog of official state park / trail map PDFs — the "state park
maps and trail maps" half of the Maps module's offline-maps upgrade,
alongside core.map_tile_cache's real basemap tiles.

**Deliberately not pre-seeded with a hardcoded list of park PDF URLs.**
Investigated this directly first rather than guessing: state park
agency sites (Kentucky, Tennessee, and presumably most others) sit
behind anti-bot protection that blocks non-browser HTTP requests (both
`WebFetch` and a browser-UA'd `curl` got blocked/404s trying to
enumerate real per-park PDF links programmatically), and the parks
themselves don't publish a unified API — official trail maps just live
as individual PDFs on each state's own site, found by a person browsing
it. Hardcoding a list of scraped URLs here would mean shipping links
with no way to confirm they're still live. Same shape as
`core/reference_library_manager.py`'s own design: this is a real,
working *catalog engine* (add/list/delete, files stored outside `data/`
in their own root, same reasoning content packs get their own root
rather than living under `data/`) — the user (or a future scraping
pass, done carefully and rate-limit-respectfully once specific target
sites are confirmed scrapable) supplies the actual park/URL/file.

Same persisted-JSON-metadata-plus-files-on-disk split as
ReferenceLibraryManager: `data/trail_maps.json` holds the catalog
metadata, the actual PDF bytes live under a configurable root
(`maps.trail_map_root_path`, defaulting to `trail_maps/` at the repo
root) — not under `data/`, since PDFs can be several MB each and
`data/` is what `core/backup_manager.py` backs up wholesale.

Uses stdlib `urllib.request` for `add_from_url()`, not the `requests`
package — same "keep requirements.txt minimal" reasoning as
core/map_tile_cache.py.
"""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = _PROJECT_ROOT / "trail_maps"
_DATA_DIR = _PROJECT_ROOT / "data"
_TRAIL_MAPS_FILE = _DATA_DIR / "trail_maps.json"

_REQUEST_TIMEOUT_SECONDS = 15
_PDF_MAGIC_BYTES = b"%PDF"


class NotAPdfError(ValueError):
    """Raised when a fetched/imported file doesn't look like a real PDF."""


@dataclass
class TrailMap:
    trail_map_id: str
    park_name: str
    state: str
    filename: str  # this trail map's own file, relative to root_path
    source_url: str = ""  # "" if added from a local file rather than a URL
    notes: str = ""
    added_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "trail_map_id": self.trail_map_id,
            "park_name": self.park_name,
            "state": self.state,
            "filename": self.filename,
            "source_url": self.source_url,
            "notes": self.notes,
            "added_at": self.added_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "TrailMap":
        return TrailMap(
            trail_map_id=data.get("trail_map_id", uuid.uuid4().hex[:10]),
            park_name=data.get("park_name", ""),
            state=data.get("state", ""),
            filename=data.get("filename", ""),
            source_url=data.get("source_url", ""),
            notes=data.get("notes", ""),
            added_at=data.get("added_at", ""),
        )


class TrailMapLibrary:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._root_path = self._resolve_root_path()
        self._trail_maps: list[TrailMap] = []
        self._load()

        try:
            self._root_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Same graceful-degradation stance as ReferenceLibraryManager
            # — don't crash the app if root_path points somewhere
            # unavailable right now.
            log.warning("Could not create/access trail map folder: %s", self._root_path)

    def _resolve_root_path(self) -> Path:
        configured = self.context.config.get("maps.trail_map_root_path", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_ROOT

    @property
    def root_path(self) -> Path:
        return self._root_path

    # ------------------------------------------------------------------
    # Persistence (metadata only — the PDFs themselves live on disk under root_path)
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _TRAIL_MAPS_FILE.exists():
            self._trail_maps = []
            return
        try:
            raw = json.loads(_TRAIL_MAPS_FILE.read_text(encoding="utf-8"))
            self._trail_maps = [TrailMap.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load trail_maps.json — starting with an empty catalog.")
            notify_data_corruption(self.context, "trail_maps.json")
            self._trail_maps = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_TRAIL_MAPS_FILE,
            json.dumps([t.to_dict() for t in self._trail_maps], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Adding
    # ------------------------------------------------------------------

    def add_from_url(self, park_name: str, state: str, url: str, notes: str = "") -> TrailMap:
        """Downloads the PDF at `url` and catalogs it. Raises
        NotAPdfError if the response doesn't start with a real PDF
        magic-number header — a 404/error page returned with a 200
        status (common on some sites) would otherwise silently get
        cataloged as a broken "trail map"."""
        request = urllib.request.Request(url, headers={"User-Agent": "MIA-Home/0.2"})
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            data = response.read()

        if not data.startswith(_PDF_MAGIC_BYTES):
            raise NotAPdfError(f"The file at '{url}' doesn't look like a real PDF.")

        trail_map_id = uuid.uuid4().hex[:10]
        filename = f"{trail_map_id}.pdf"
        self._root_path.mkdir(parents=True, exist_ok=True)
        (self._root_path / filename).write_bytes(data)

        return self._catalog(trail_map_id, park_name, state, filename, source_url=url, notes=notes)

    def add_from_local_file(self, park_name: str, state: str, source_path: Path, notes: str = "") -> TrailMap:
        """Copies an existing local PDF file into the library. Raises
        NotAPdfError the same way add_from_url() does."""
        header = source_path.open("rb").read(len(_PDF_MAGIC_BYTES))
        if not header.startswith(_PDF_MAGIC_BYTES):
            raise NotAPdfError(f"'{source_path}' doesn't look like a real PDF.")

        trail_map_id = uuid.uuid4().hex[:10]
        filename = f"{trail_map_id}.pdf"
        self._root_path.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, self._root_path / filename)

        return self._catalog(trail_map_id, park_name, state, filename, source_url="", notes=notes)

    def _catalog(
        self, trail_map_id: str, park_name: str, state: str, filename: str, source_url: str, notes: str
    ) -> TrailMap:
        trail_map = TrailMap(
            trail_map_id=trail_map_id,
            park_name=park_name,
            state=state,
            filename=filename,
            source_url=source_url,
            notes=notes,
            added_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._trail_maps.append(trail_map)
        self._save()
        log.info("Trail map added: '%s' (%s)", park_name, state)
        return trail_map

    # ------------------------------------------------------------------
    # Reading / deleting
    # ------------------------------------------------------------------

    def get_trail_map(self, trail_map_id: str) -> Optional[TrailMap]:
        for trail_map in self._trail_maps:
            if trail_map.trail_map_id == trail_map_id:
                return trail_map
        return None

    def all_trail_maps(self) -> list[TrailMap]:
        return sorted(self._trail_maps, key=lambda t: (t.state.lower(), t.park_name.lower()))

    def trail_maps_for_state(self, state: str) -> list[TrailMap]:
        return [t for t in self.all_trail_maps() if t.state.lower() == state.lower()]

    def file_path(self, trail_map_id: str) -> Optional[Path]:
        trail_map = self.get_trail_map(trail_map_id)
        if trail_map is None:
            return None
        path = self._root_path / trail_map.filename
        return path if path.exists() else None

    def delete_trail_map(self, trail_map_id: str) -> None:
        trail_map = self.get_trail_map(trail_map_id)
        if trail_map is None:
            return
        path = self._root_path / trail_map.filename
        if path.exists():
            path.unlink()
        self._trail_maps = [t for t in self._trail_maps if t.trail_map_id != trail_map_id]
        self._save()
