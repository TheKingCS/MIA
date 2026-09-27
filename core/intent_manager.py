"""
core.intent_manager
======================

Intent — the "why" layer in the connective-infrastructure pass that
followed the "My Hero's Path" architecture review (see docs/ROADMAP.md's
dated entry for the full reasoning). An Intent is a long-running,
open-ended goal ("Homestead Independence," "Get really good at making
things") that a core.project_manager.Project can optionally declare it
serves, via `Project.intent_id`.

Deliberately structured almost identically to Project (same persisted-
JSON pattern: data/intents.json, a dataclass with to_dict/from_dict, a
manager class wrapping load/save) rather than reusing Project itself
with a flag — the two are semantically different even though they look
alike: a Project is bounded (has a due date, moves through Planning ->
Active -> Complete), an Intent is open-ended (no due date, gets revised
or retired over months/years rather than discretely "completed").

`primary` exists so the UI has an unambiguous answer to "what's the
current focus" when several Intents are open at once — set_primary()
flips one on and every other off, the same "exactly one active thing"
shape core.profile_manager's active-profile tracking already uses.

Linking a Project to an Intent is always optional (intent_id defaults
to None) — nothing in this codebase forces every Project to have one.
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
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_INTENTS_FILE = _DATA_DIR / "intents.json"

INTENT_STATUSES = ("Active", "Paused", "Achieved", "Archived")


@dataclass
class Intent:
    intent_id: str
    name: str
    description: str = ""
    status: str = "Active"
    primary: bool = False
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime
    # 2026-09-27, Cognitive Extension slice B ("Remember Why", see
    # core/why_graph.py): an Intent can serve a bigger one, so the
    # owner's reasons form a chain ("Factory work" -> "Pay off debt" ->
    # "Control over my time"), and `reason` keeps why in their own words.
    # Both optional; existing intents.json rows load unchanged.
    serves_intent_id: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "intent_id": self.intent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "primary": self.primary,
            "serves_intent_id": self.serves_intent_id,
            "reason": self.reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Intent":
        return Intent(
            intent_id=data.get("intent_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=data.get("status", "Active"),
            primary=bool(data.get("primary", False)),
            serves_intent_id=data.get("serves_intent_id"),
            reason=data.get("reason", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class IntentManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._intents: list[Intent] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _INTENTS_FILE.exists():
            self._intents = []
            return
        try:
            raw = json.loads(_INTENTS_FILE.read_text(encoding="utf-8"))
            self._intents = [Intent.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load intents.json — starting with an empty list.")
            notify_data_corruption(self.context, "intents.json")
            self._intents = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_INTENTS_FILE,
            json.dumps([i.to_dict() for i in self._intents], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_intent(
        self,
        name: str,
        description: str = "",
        status: str = "Active",
        primary: bool = False,
    ) -> Intent:
        now = datetime.now().isoformat(timespec="seconds")
        intent = Intent(
            intent_id=uuid.uuid4().hex[:10],
            name=name,
            description=description,
            status=status,
            primary=False,  # set below via set_primary() so "only one primary" stays enforced in one place
            created_at=now,
            updated_at=now,
        )
        self._intents.append(intent)
        self._save()
        log.info("Intent added: '%s'", name)
        if primary:
            self.set_primary(intent.intent_id)
        return intent

    def update_intent(self, intent_id: str, **fields) -> Intent:
        intent = self.get_intent(intent_id)
        if intent is None:
            raise ValueError(f"No intent with id '{intent_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_intent().")
            if key == "primary":
                raise ValueError("'primary' can't be set through update_intent() — use set_primary().")
            if not hasattr(intent, key):
                raise ValueError(f"Intent has no field '{key}'.")
            setattr(intent, key, value)
        intent.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return intent

    def set_primary(self, intent_id: str) -> Intent:
        """Marks `intent_id` as the primary (current-focus) Intent and
        unmarks every other one — same "exactly one active thing" shape
        as core.profile_manager's active-profile tracking."""
        intent = self.get_intent(intent_id)
        if intent is None:
            raise ValueError(f"No intent with id '{intent_id}'.")
        for other in self._intents:
            other.primary = other.intent_id == intent_id
        intent.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return intent

    def delete_intent(self, intent_id: str) -> None:
        self._intents = [i for i in self._intents if i.intent_id != intent_id]
        # Anything that served the deleted goal now serves nothing,
        # rather than pointing at an id that no longer exists.
        for intent in self._intents:
            if intent.serves_intent_id == intent_id:
                intent.serves_intent_id = None
        self._save()

    def would_create_cycle(self, intent_id: str, serves_intent_id: Optional[str]) -> bool:
        """True if making `intent_id` serve `serves_intent_id` would loop
        back to itself (A serves B serves A)."""
        seen = set()
        current = serves_intent_id
        while current is not None and current not in seen:
            if current == intent_id:
                return True
            seen.add(current)
            parent = self.get_intent(current)
            current = parent.serves_intent_id if parent is not None else None
        return False

    def set_serves(self, intent_id: str, serves_intent_id: Optional[str], reason: Optional[str] = None) -> Intent:
        """Link (or with None, unlink) `intent_id` to the bigger goal it serves."""
        if serves_intent_id is not None and self.get_intent(serves_intent_id) is None:
            raise ValueError(f"No intent with id '{serves_intent_id}'.")
        if self.would_create_cycle(intent_id, serves_intent_id):
            raise ValueError("That would make a goal serve itself.")
        fields = {"serves_intent_id": serves_intent_id}
        if reason is not None:
            fields["reason"] = reason
        return self.update_intent(intent_id, **fields)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_intent(self, intent_id: str) -> Optional[Intent]:
        for intent in self._intents:
            if intent.intent_id == intent_id:
                return intent
        return None

    def all_intents(self) -> list[Intent]:
        return list(self._intents)

    def primary_intent(self) -> Optional[Intent]:
        for intent in self._intents:
            if intent.primary:
                return intent
        return None
