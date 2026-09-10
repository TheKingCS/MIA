"""
core.user_memory_manager
===========================

Persistent facts MIA has learned about the user over the course of
conversations — 2026-07-14 aesthetic pass part 5 (docs/ROADMAP.md), at
the user's explicit request: "an ability to review and delete... see
the AI's stored memories about the user and keep or delete them." Same
persisted-JSON pattern as core/mission_manager.py: data/user_memories.json,
a dataclass with to_dict/from_dict, a manager class wrapping load/save.

Memories are extracted from a conversation by the LLM itself (see
core/assistant_chat.py's `build_memory_extraction_prompt()`/
`parse_extracted_memories()`) — this manager only stores/serves them,
it never talks to the LLM directly, same separation as
core/device_help_manager.py not owning retrieval-vs-generation itself.

`add_memory()` silently no-ops (returns None) on a near-duplicate of an
existing memory — deliberately simple, case-insensitive exact-text
matching (not fuzzy/semantic dedup, which would need embeddings this
project has already decided against building for a much bigger corpus
in core/device_help_manager.py's own docstring) rather than letting the
same fact accumulate a new row every time it comes up again in
conversation.

**2026-09-10 "Memory Palace"**: categorization, not a rename — VISION.md
asks for "categorized, interconnected memory... replacing today's flat
UserMemory list," but a full rename would touch 10 real call sites
across the live GUI and headless Core conversation flows for zero
functional gain. The real substance (flat -> categorized) is delivered
by adding a real `category` field instead: `core.assistant_chat`'s
memory-extraction prompt now asks the LLM for a category per fact
(`Category: Fact` per line), and `add_memory()` stores it, falling back
to "Other" for anything unrecognized so a formatting slip never loses
a real fact. "Interconnected" (cross-linking related memories) is a
real, separate, bigger feature deferred for now — this data model has
no "related to" concept yet.
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

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_USER_MEMORIES_FILE = _DATA_DIR / "user_memories.json"

MEMORY_CATEGORIES = [
    "Family", "Programming", "Fitness", "Fishing", "Projects", "Travel",
    "Cooking", "Finance", "Pets", "Education", "Work", "Other",
]


@dataclass
class UserMemory:
    memory_id: str
    text: str
    created_at: str = ""
    source_conversation_id: Optional[str] = None
    category: str = "Other"  # one of MEMORY_CATEGORIES — "Other" for pre-Memory-Palace records too

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "text": self.text,
            "created_at": self.created_at,
            "source_conversation_id": self.source_conversation_id,
            "category": self.category,
        }

    @staticmethod
    def from_dict(data: dict) -> "UserMemory":
        return UserMemory(
            memory_id=data.get("memory_id", uuid.uuid4().hex[:10]),
            text=data.get("text", ""),
            created_at=data.get("created_at", ""),
            source_conversation_id=data.get("source_conversation_id"),
            category=data.get("category", "Other"),
        )


def is_duplicate_memory(text: str, existing_texts: list[str]) -> bool:
    """Pure logic — testable without touching the filesystem. Case/whitespace-insensitive exact match."""
    normalized = text.strip().lower()
    return any(normalized == existing.strip().lower() for existing in existing_texts)


class UserMemoryManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._memories: list[UserMemory] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _USER_MEMORIES_FILE.exists():
            self._memories = []
            return
        try:
            raw = json.loads(_USER_MEMORIES_FILE.read_text(encoding="utf-8"))
            self._memories = [UserMemory.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load user_memories.json — starting with an empty list.")
            self._memories = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _USER_MEMORIES_FILE.write_text(
            json.dumps([m.to_dict() for m in self._memories], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def all_memories(self) -> list[UserMemory]:
        """Newest first — matches the conversation list's own ordering convention."""
        return sorted(self._memories, key=lambda m: m.created_at, reverse=True)

    def add_memory(
        self, text: str, category: str = "Other", source_conversation_id: Optional[str] = None,
    ) -> Optional[UserMemory]:
        text = text.strip()
        if not text:
            return None
        if is_duplicate_memory(text, [m.text for m in self._memories]):
            return None
        memory = UserMemory(
            memory_id=uuid.uuid4().hex[:10],
            text=text,
            created_at=datetime.now().isoformat(timespec="seconds"),
            source_conversation_id=source_conversation_id,
            category=category if category in MEMORY_CATEGORIES else "Other",
        )
        self._memories.append(memory)
        self._save()
        log.info("User memory added: '%s'", text)
        return memory

    def delete_memory(self, memory_id: str) -> None:
        self._memories = [m for m in self._memories if m.memory_id != memory_id]
        self._save()

    def clear_all(self) -> None:
        self._memories = []
        self._save()
