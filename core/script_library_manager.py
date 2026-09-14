"""
core.script_library_manager
==============================

Backs Field Kit's "Useful Scripts" tab (docs/ROADMAP.md milestone
11.4) — a categorized library of user-authored shell/Python scripts.
Same persisted-JSON pattern as core.journal_manager.JournalManager:
data/scripts.json, a dataclass with to_dict/from_dict, a manager class
wrapping load/save/CRUD/search. Script *content* is stored inline
(like a Journal entry's body), not as a path to an external file — one
JSON blob to back up/restore, no separate scripts/ directory to keep in
sync, and it matches how every other "user's own data" manager in this
app already works.

No sandboxing when a script is actually run (core/script_runner.py) —
these are the user's own trusted scripts on their own offline device,
same stance this project already takes for third-party module
installation (see CLAUDE.md's "known intentional simplifications").
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SCRIPTS_FILE = _DATA_DIR / "scripts.json"

INTERPRETERS = ("shell", "python")


@dataclass
class Script:
    script_id: str
    name: str
    interpreter: str = "shell"
    category: str = ""
    content: str = ""
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "script_id": self.script_id,
            "name": self.name,
            "interpreter": self.interpreter,
            "category": self.category,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Script":
        return Script(
            script_id=data.get("script_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            interpreter=data.get("interpreter", "shell"),
            category=data.get("category", ""),
            content=data.get("content", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ScriptLibraryManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._scripts: list[Script] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _SCRIPTS_FILE.exists():
            self._scripts = []
            return
        try:
            raw = json.loads(_SCRIPTS_FILE.read_text(encoding="utf-8"))
            self._scripts = [Script.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load scripts.json — starting with an empty list.")
            self._scripts = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_SCRIPTS_FILE,
            json.dumps([s.to_dict() for s in self._scripts], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_script(self, name: str, interpreter: str = "shell", content: str = "", category: str = "") -> Script:
        now = datetime.now().isoformat(timespec="seconds")
        script = Script(
            script_id=uuid.uuid4().hex[:10],
            name=name,
            interpreter=interpreter if interpreter in INTERPRETERS else "shell",
            category=category,
            content=content,
            created_at=now,
            updated_at=now,
        )
        self._scripts.append(script)
        self._save()
        log.info("Script added: '%s' (%s)", name, script.interpreter)
        return script

    def update_script(self, script_id: str, **fields) -> Script:
        script = self.get_script(script_id)
        if script is None:
            raise ValueError(f"No script with id '{script_id}'.")
        for key, value in fields.items():
            if key in ("created_at", "updated_at"):
                raise ValueError(f"'{key}' can't be set through update_script().")
            if not hasattr(script, key):
                raise ValueError(f"Script has no field '{key}'.")
            setattr(script, key, value)
        script.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return script

    def delete_script(self, script_id: str) -> None:
        self._scripts = [s for s in self._scripts if s.script_id != script_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_script(self, script_id: str) -> Optional[Script]:
        for script in self._scripts:
            if script.script_id == script_id:
                return script
        return None

    def all_scripts(self) -> list[Script]:
        """Alphabetical by category, then name — a library browses better sorted than "most recent first"."""
        return sorted(self._scripts, key=lambda s: (s.category.lower(), s.name.lower()))

    def search(self, query: str) -> list[Script]:
        """Case-insensitive substring match over name, category, and content."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []
        matches = [
            s for s in self._scripts
            if query_lower in f"{s.name} {s.category} {s.content}".lower()
        ]
        return sorted(matches, key=lambda s: (s.category.lower(), s.name.lower()))

    def categories(self) -> list[str]:
        return sorted({s.category for s in self._scripts if s.category})
