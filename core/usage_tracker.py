"""
core.usage_tracker
=====================

Per-module usage tracking — "has the user ever actually opened X
through the app" — the real gap docs/VISION.md's modular tutorial
system names as still unbuilt: "proactively suggest a walkthrough for
never-used features... needs a real per-feature usage-tracking
subsystem that doesn't exist yet."

core.activity_log_manager.ActivityLogManager already subscribes to the
same "module.opened" event, but it's a capped (5000 entries, oldest
dropped), chronological narrative log built for "what have I been
doing" queries — free-text summaries, no module_id field, not meant as
a durable per-module index. This is deliberately a second, much
smaller, never-pruned one: one row per module_id
(first_opened/last_opened/open_count), so "has this module EVER been
opened" stays correct indefinitely, independent of how much unrelated
activity has scrolled past the capped log since.

Deliberately NOT backfilled from existing data (module content or the
activity log) when this shipped: real domain data existing for a
module (e.g. data/missions.json being full) proves work was done in
that domain, not that a real person actually clicked into the module
through the running app — much of it was created directly by manager
calls while building features, never through gui.main_window.
open_module(). Backfilling from that would fabricate a usage record
this subsystem has no real evidence for. Every module legitimately
starts "never opened" the day this shipped; core.smart_suggestions'
`build_walkthrough_suggestion()` only ever surfaces ONE candidate per
day and never repeats a module already suggested once
(`mark_suggested()`/`has_been_suggested()` below), so even a module
the user already knows well gets at most one harmless one-time nudge,
never a recurring nag.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_USAGE_FILE = _DATA_DIR / "module_usage.json"


@dataclass
class ModuleUsage:
    module_id: str
    first_opened: str = ""  # ISO datetime
    last_opened: str = ""  # ISO datetime
    open_count: int = 0

    def to_dict(self) -> dict:
        return {
            "module_id": self.module_id,
            "first_opened": self.first_opened,
            "last_opened": self.last_opened,
            "open_count": self.open_count,
        }

    @staticmethod
    def from_dict(data: dict) -> "ModuleUsage":
        return ModuleUsage(
            module_id=data.get("module_id", ""),
            first_opened=data.get("first_opened", ""),
            last_opened=data.get("last_opened", ""),
            open_count=data.get("open_count", 0),
        )


class UsageTracker:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._usage: dict[str, ModuleUsage] = {}
        self._suggested_module_ids: set[str] = set()
        self._load()
        self.context.events.subscribe("module.opened", self._on_module_opened)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _USAGE_FILE.exists():
            return
        try:
            raw = json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load module_usage.json — starting with no usage recorded.")
            return
        for entry in raw.get("usage", []):
            usage = ModuleUsage.from_dict(entry)
            if usage.module_id:
                self._usage[usage.module_id] = usage
        self._suggested_module_ids = set(raw.get("suggested_module_ids", []))

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "usage": [usage.to_dict() for usage in self._usage.values()],
            "suggested_module_ids": sorted(self._suggested_module_ids),
        }
        atomic_write_text(_USAGE_FILE, json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _on_module_opened(self, module_id: str) -> None:
        self.record_open(module_id)

    def record_open(self, module_id: str, when: Optional[str] = None) -> None:
        now = when or datetime.now().isoformat(timespec="seconds")
        usage = self._usage.get(module_id)
        if usage is None:
            usage = ModuleUsage(module_id=module_id, first_opened=now)
            self._usage[module_id] = usage
        usage.last_opened = now
        usage.open_count += 1
        self._save()

    def mark_suggested(self, module_id: str) -> None:
        self._suggested_module_ids.add(module_id)
        self._save()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def usage_for(self, module_id: str) -> Optional[ModuleUsage]:
        return self._usage.get(module_id)

    def all_usage(self) -> list[ModuleUsage]:
        return list(self._usage.values())

    def has_been_opened(self, module_id: str) -> bool:
        return module_id in self._usage

    def has_been_suggested(self, module_id: str) -> bool:
        return module_id in self._suggested_module_ids

    def never_opened_module_ids(self, all_module_ids: list[str]) -> list[str]:
        """Preserves `all_module_ids`' own order — callers control
        priority by the order they pass in (see
        core.application._check_daily_occasions, which passes
        module_manager.enabled_modules() in discovery order)."""
        return [module_id for module_id in all_module_ids if module_id not in self._usage]

    def unsuggested_never_opened_module_ids(self, all_module_ids: list[str]) -> list[str]:
        """never_opened_module_ids(), further narrowed to ones never
        already suggested a walkthrough for — the real "don't repeat
        the same nudge" guard."""
        return [
            module_id for module_id in self.never_opened_module_ids(all_module_ids)
            if module_id not in self._suggested_module_ids
        ]
