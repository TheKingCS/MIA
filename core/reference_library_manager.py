"""
core.reference_library_manager
================================

The ZIM engine behind the Reference Library — docs/ROADMAP.md milestone
4.1, the "Reference Library" row of the shared core services table
(indexed/searchable document + PDF + Kiwix ZIM viewer). This milestone
is the engine only: pack discovery, reading, and search. The
`knowledge` module's UI (milestone 4.2), Global Search integration
(4.3), and install-a-pack-from-the-UI flow (4.4, `install_pack_from_file`)
build on top of this.

Wraps the `libzim` package (Kiwix's own Python bindings for the ZIM
file format — see docs/ROADMAP.md's "don't reinvent the wheel"
integration decisions). One `.zim` file is one "pack" (e.g. a Wikipedia
slice, WikiHow, iFixit, a first-aid guide); packs live in a configurable
library folder (`reference_library.root_path`, defaulting to
`reference_library/` at the repo root) rather than under `data/` — see
that config key's comment in config/default_config.json and
docs/HARDWARE.md's storage-split reasoning for why: content packs can
be multi-gigabyte, and `data/` is what core/backup_manager.py backs up
wholesale.

Same defensive-discovery pattern as core/module_manager.py: a
missing/corrupt `.zim` file is logged and skipped rather than crashing
the app, since content packs are user-supplied files on a removable
drive that can be absent, still copying, or damaged.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from libzim.reader import Archive
from libzim.search import Query, Searcher

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = _PROJECT_ROOT / "reference_library"

# A multi-gigabyte pack being copied into root_path keeps growing for
# minutes; opening it mid-copy via libzim can hang rather than raise
# (it's a truncated/still-changing file, not a cleanly corrupt one).
# Skip anything touched more recently than this and let a later
# list_packs() call (the next keystroke in search, or the next time the
# library screen is shown) pick it up once it's gone quiet.
_MIN_QUIET_SECONDS = 5.0


@dataclass
class ReferencePack:
    """One installed .zim file, with just enough metadata to list/browse it."""

    pack_id: str  # filename stem; unique within root_path by construction
    file_path: str
    title: str
    description: str
    language: str
    article_count: int


@dataclass
class ReferenceSearchHit:
    path: str
    title: str


@dataclass
class PackInstallResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    pack_id: Optional[str] = None
    title: Optional[str] = None


@dataclass
class ReferenceSnippet:
    """One search_all_packs() result — a short plain-text excerpt, not the full article."""

    pack_id: str
    pack_title: str
    article_title: str
    snippet: str


_SNIPPET_MAX_CHARS = 500


class _HTMLTextExtractor(HTMLParser):
    """
    Minimal HTML-to-plain-text extractor for building a short
    Assistant-grounding snippet (core/device_help_manager.py) — stdlib
    only, no new dependency for what's just "strip tags, skip
    script/style content, collapse whitespace."  Not a general-purpose
    HTML-to-text tool; good enough for a short excerpt, not for
    rendering (that's modules/knowledge/zim_text_browser.py's job).
    """

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(" ".join(self._parts).split())


def _html_to_snippet(html_bytes: bytes, max_chars: int = _SNIPPET_MAX_CHARS) -> str:
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html_bytes.decode("utf-8", errors="replace"))
    except Exception:
        return ""
    text = extractor.get_text()
    if len(text) > max_chars:
        return text[:max_chars] + "…"
    return text


class ReferenceLibraryManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._root_path = self._resolve_root_path()
        self._archives: dict[str, Archive] = {}
        # (size, mtime) at the moment a pack failed to open, so a genuinely
        # broken file isn't retried every keystroke, but a since-replaced
        # or since-finished-copying file is.
        self._failed_stat: dict[str, tuple[int, float]] = {}

        try:
            self._root_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Most likely cause: root_path points at a removable drive
            # (per docs/HARDWARE.md) that isn't mounted right now. Don't
            # crash the app over a missing content drive — list_packs()
            # below already returns an empty list when the folder
            # doesn't exist, so the app just shows an empty library.
            log.warning("Could not create/access reference library folder: %s", self._root_path)

    def _resolve_root_path(self) -> Path:
        configured = self.context.config.get("reference_library.root_path", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_ROOT

    @property
    def root_path(self) -> Path:
        """Where to point a user at when telling them where to copy .zim files — used by the 4.2 UI's empty state."""
        return self._root_path

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_packs(self) -> list[ReferencePack]:
        """
        Rescan root_path for .zim files and return the packs that open
        successfully, sorted by title. Cheap enough to call whenever
        the library screen is shown — there's no persisted index to
        keep in sync (libzim's own on-disk index is the source of truth).
        """
        if not self._root_path.exists():
            return []

        packs = []
        for zim_path in sorted(self._root_path.glob("*.zim")):
            archive = self._get_archive(zim_path.stem, zim_path)
            if archive is None:
                continue
            packs.append(self._build_pack(zim_path.stem, zim_path, archive))
        return sorted(packs, key=lambda p: p.title.lower())

    def get_pack(self, pack_id: str) -> Optional[ReferencePack]:
        for pack in self.list_packs():
            if pack.pack_id == pack_id:
                return pack
        return None

    def install_pack_from_file(self, source_path: Path) -> PackInstallResult:
        """
        Validate and copy an external .zim file into root_path — the
        same validate-before-copy shape as
        core/module_validator.py's module installs (docs/ROADMAP.md
        milestone 4.4). On success the new pack is cached immediately
        (bypassing the mid-copy quiet-period guard in _get_archive,
        which doesn't apply here since we just wrote this file
        ourselves and know it's complete) so it shows up in the very
        next list_packs() call without waiting out that window.
        """
        source_path = Path(source_path)

        if not source_path.is_file():
            return PackInstallResult(passed=False, errors=[f"'{source_path}' is not a file."])
        if source_path.suffix.lower() != ".zim":
            return PackInstallResult(passed=False, errors=["Not a .zim file — pick a file with a .zim extension."])

        destination_path = self._root_path / source_path.name
        if destination_path.exists():
            return PackInstallResult(
                passed=False, errors=[f"A pack named '{source_path.name}' is already installed."]
            )

        try:
            Archive(str(source_path))  # cheap open, just to validate before copying a possibly-huge file
        except Exception as exc:
            return PackInstallResult(passed=False, errors=[f"Not a valid ZIM file: {exc}"])

        try:
            self._root_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
        except OSError as exc:
            return PackInstallResult(passed=False, errors=[f"Validation passed, but copying the file failed: {exc}"])

        pack_id = destination_path.stem
        archive = Archive(str(destination_path))
        self._archives[pack_id] = archive
        self._failed_stat.pop(pack_id, None)

        log.info("Installed new content pack '%s' from %s", pack_id, source_path)
        return PackInstallResult(
            passed=True, pack_id=pack_id, title=self._get_metadata(archive, "Title", default=pack_id)
        )

    def _get_archive(self, pack_id: str, file_path: Path) -> Optional[Archive]:
        if pack_id in self._archives:
            return self._archives[pack_id]

        try:
            stat = file_path.stat()
        except OSError:
            return None

        if time.time() - stat.st_mtime < _MIN_QUIET_SECONDS:
            log.debug("Skipping recently-modified ZIM file (likely still copying): %s", file_path)
            return None

        state = (stat.st_size, stat.st_mtime)
        if self._failed_stat.get(pack_id) == state:
            return None

        try:
            archive = Archive(str(file_path))
        except Exception:
            log.warning("Skipping unreadable ZIM file: %s", file_path)
            self._failed_stat[pack_id] = state
            return None

        self._archives[pack_id] = archive
        self._failed_stat.pop(pack_id, None)
        return archive

    @staticmethod
    def _get_metadata(archive: Archive, key: str, default: str = "") -> str:
        try:
            return archive.get_metadata(key).decode("utf-8", errors="replace")
        except (KeyError, RuntimeError):
            return default

    def _build_pack(self, pack_id: str, file_path: Path, archive: Archive) -> ReferencePack:
        return ReferencePack(
            pack_id=pack_id,
            file_path=str(file_path),
            title=self._get_metadata(archive, "Title", default=pack_id),
            description=self._get_metadata(archive, "Description"),
            language=self._get_metadata(archive, "Language"),
            article_count=archive.article_count,
        )

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def get_main_page(self, pack_id: str) -> Optional[str]:
        """
        The entry path a pack's viewer should land on by default, or
        None. `archive.main_entry` is a synthetic redirect entry whose
        own `.path` ("mainPage") isn't independently fetchable via
        get_entry_by_path/get_entry_content — resolve through the
        redirect to the real, fetchable target path.
        """
        archive = self._archive_for_pack(pack_id)
        if archive is None or not archive.has_main_entry:
            return None
        entry = archive.main_entry
        if entry.is_redirect:
            entry = entry.get_redirect_entry()
        return entry.path

    def get_entry_content(self, pack_id: str, entry_path: str) -> Optional[tuple[bytes, str]]:
        """
        Returns (content_bytes, mimetype) for `entry_path` within `pack_id`
        — used for both the article HTML itself and any inline resource
        (image, CSS, ...) it references by a ZIM-internal relative path.
        Returns None if the pack or entry doesn't exist.
        """
        archive = self._archive_for_pack(pack_id)
        if archive is None:
            return None
        try:
            item = archive.get_entry_by_path(entry_path).get_item()
        except KeyError:
            return None
        return bytes(item.content), item.mimetype

    def _archive_for_pack(self, pack_id: str) -> Optional[Archive]:
        if pack_id in self._archives:
            return self._archives[pack_id]
        zim_path = self._root_path / f"{pack_id}.zim"
        if not zim_path.exists():
            return None
        return self._get_archive(pack_id, zim_path)

    # ------------------------------------------------------------------
    # Search (within a single pack — fanning a query out across every
    # installed pack is Global Search integration's job, milestone 4.3)
    # ------------------------------------------------------------------

    def search(self, pack_id: str, query: str, limit: int = 20) -> list[ReferenceSearchHit]:
        query = query.strip()
        archive = self._archive_for_pack(pack_id)
        if archive is None or not query or not archive.has_fulltext_index:
            return []

        searcher = Searcher(archive)
        search = searcher.search(Query().set_query(query))
        hits = []
        for path in search.getResults(0, limit):
            try:
                title = archive.get_entry_by_path(path).title
            except KeyError:
                continue
            hits.append(ReferenceSearchHit(path=path, title=title))
        return hits

    def search_all_packs(self, query: str, limit: int = 5) -> list[ReferenceSnippet]:
        """
        Fan `query` out across every installed pack's full-text search
        and return up to `limit` short plain-text snippets total —
        used by core/device_help_manager.py to ground Assistant answers
        in the actual installed reference content (Wikipedia/iFixit/
        etc.), not just M.I.A.'s own docs/*.md. Similar cross-pack
        fan-out shape to modules/knowledge/module.py's Global Search
        provider, but returns grounding snippets, not SearchResult UI
        objects, and doesn't re-rank hits — libzim's own full-text
        search relevance ordering is used as-is *within* a pack.

        Takes at most one hit per pack, and tries every installed pack
        before capping the total at `limit` — NOT "stop as soon as
        `limit` hits are found." Found via a real query
        ("hypothermia symptoms" against 8 real installed packs): a
        general cold-weather Appropedia article alphabetically before
        the medicine pack supplied several hits that exhausted a
        break-early total cap, so the medicine pack's much more
        directly relevant "Hypothermia" Wikipedia article never even
        got searched. One-hit-per-pack across every pack, capped only
        at the end, means `limit` should comfortably cover however many
        packs are installed (a handful in practice) rather than being
        tuned as a performance knob — letting the LLM itself weigh
        several candidate packs' evidence, which it's better suited for
        than any cross-pack scoring this class could cheaply build.

        Deliberately not the full article: each hit's content is
        fetched and reduced to a short plain-text excerpt
        (_html_to_snippet) so a handful of matches across several packs
        stays cheap to include in an LLM prompt.
        """
        query = query.strip()
        if not query:
            return []

        snippets: list[ReferenceSnippet] = []
        for pack in self.list_packs():
            hits = self.search(pack.pack_id, query, limit=1)
            for hit in hits:
                content = self.get_entry_content(pack.pack_id, hit.path)
                if content is None:
                    continue
                content_bytes, mimetype = content
                if not mimetype.startswith("text/html"):
                    continue
                snippet_text = _html_to_snippet(content_bytes)
                if not snippet_text:
                    continue
                snippets.append(ReferenceSnippet(
                    pack_id=pack.pack_id,
                    pack_title=pack.title,
                    article_title=hit.title,
                    snippet=snippet_text,
                ))
        return snippets[:limit]
