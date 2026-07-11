"""
core.search_manager
=====================

A system-wide search service — the "don't make me know where to look
for each thing" feature. Any module or core service can register a
search provider; SearchManager just fans a query out to all of them
and collects the results.

Design:
- Results are plain data (SearchResult: title, description, source,
  action_type, action_target) — never a raw callback. This keeps
  SearchManager (core/) from needing to know anything about the GUI,
  the same separation every other core service in this project follows.
  The GUI layer (gui/search_dialog.py + MainWindow) is the only thing
  that interprets action_type and actually does something with it.
- A provider is just `Callable[[str], list[SearchResult]]`. A broken
  provider is caught and logged, not allowed to break search for every
  other provider — same defensive pattern as core/event_bus.py.
- Currently registered providers (see core/application.py):
  "modules" (searches module display name/description/id) and
  "profiles" (searches profile names). As real content-bearing modules
  are built (Notes, Files, Reference Library, etc.), each one should
  register its own provider — see docs/ADDING_MODULES.md for the
  pattern once documented there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)


@dataclass
class SearchResult:
    """
    A single search result. action_type/action_target describe what
    should happen if the user selects this result — interpreted by the
    GUI layer, never executed here.
    """

    title: str
    description: str
    source: str
    action_type: str  # e.g. "open_module", "switch_profile"
    action_target: str  # e.g. a module_id or profile_id


class SearchManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._providers: dict[str, Callable[[str], list[SearchResult]]] = {}

    def register_provider(self, name: str, provider: Callable[[str], list[SearchResult]]) -> None:
        """Register a search provider under `name` (used only for logging/debugging)."""
        self._providers[name] = provider
        log.info("Registered search provider: %s", name)

    def search(self, query: str) -> list[SearchResult]:
        """
        Run `query` against every registered provider and return the
        combined results. Returns an empty list for a blank query
        rather than every provider's "everything" — search should
        require actual input.
        """
        query = query.strip()
        if not query:
            return []

        results: list[SearchResult] = []
        for name, provider in self._providers.items():
            try:
                results.extend(provider(query))
            except Exception:
                log.exception("Search provider '%s' raised an error — skipping its results.", name)
        return results
