"""
core.conversation_manager
============================

Persistent Assistant conversations — 2026-07-14 aesthetic pass part 5
(docs/ROADMAP.md), at the user's explicit request for a ChatGPT-like
experience: named conversation threads you can review, continue, or
delete, rather than the stateless one-message-at-a-time exchanges the
Assistant used before this. Same persisted-JSON pattern as
core/mission_manager.py: data/conversations.json, dataclasses with
to_dict/from_dict, a manager class wrapping load/save.

A `Conversation`'s `title` starts as `_DEFAULT_TITLE` ("New
Conversation") and is filled in later by an LLM-generated summary once
there's been at least one real exchange — see
`core/assistant_chat.py`'s `build_title_generation_prompt()`/
`clean_generated_title()`, invoked from the GUI layer (`gui/character_panel.py`/
`modules/assistant/module.py`) since generating a title needs a live
LLM call, which this manager itself has no business making. `set_title()`
is generic (not title-generation-specific) so both that automatic path
and any future manual rename UI can use the same method.

Exactly one conversation is "active" at a time
(`get_active_conversation_id()`/`set_active_conversation_id()`,
persisted in config via `assistant.active_conversation_id` — not a
separate file, since it's a single small pointer, not a growing
dataset) — both the sidebar chat and the full-screen Assistant module
read and append to whichever conversation is active, so switching
between the two surfaces never shows a different, disconnected
conversation. Publishes `"conversation.updated"` on every mutation so
whichever surface *isn't* the one that just wrote to it can refresh
without the two widgets needing a direct reference to each other.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CONVERSATIONS_FILE = _DATA_DIR / "conversations.json"

DEFAULT_TITLE = "New Conversation"


@dataclass
class ConversationMessage:
    role: str  # "user" | "assistant"
    content: str
    timestamp: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @staticmethod
    def from_dict(data: dict) -> "ConversationMessage":
        return ConversationMessage(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class Conversation:
    conversation_id: str
    title: str = DEFAULT_TITLE
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Conversation":
        return Conversation(
            conversation_id=data.get("conversation_id", uuid.uuid4().hex[:10]),
            title=data.get("title", DEFAULT_TITLE),
            messages=[ConversationMessage.from_dict(d) for d in data.get("messages", [])],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ConversationManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._conversations: list[Conversation] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _CONVERSATIONS_FILE.exists():
            self._conversations = []
            return
        try:
            raw = json.loads(_CONVERSATIONS_FILE.read_text(encoding="utf-8"))
            self._conversations = [Conversation.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load conversations.json — starting with an empty list.")
            self._conversations = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_CONVERSATIONS_FILE,
            json.dumps([c.to_dict() for c in self._conversations], indent=2),
            encoding="utf-8",
        )

    def _bump_updated_at(self, conversation: Conversation) -> None:
        conversation.updated_at = datetime.now().isoformat(timespec="seconds")

    def _publish_updated(self, conversation_id: str) -> None:
        if self.context.events is not None:
            self.context.events.publish("conversation.updated", conversation_id=conversation_id)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_conversation(self) -> Conversation:
        now = datetime.now().isoformat(timespec="seconds")
        conversation = Conversation(conversation_id=uuid.uuid4().hex[:10], created_at=now, updated_at=now)
        self._conversations.append(conversation)
        self._save()
        log.info("Conversation created: '%s'", conversation.conversation_id)
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        for conversation in self._conversations:
            if conversation.conversation_id == conversation_id:
                return conversation
        return None

    def all_conversations(self) -> list[Conversation]:
        """Most-recently-updated first — matches a ChatGPT-style history list's own ordering."""
        return sorted(self._conversations, key=lambda c: c.updated_at, reverse=True)

    def delete_conversation(self, conversation_id: str) -> None:
        self._conversations = [c for c in self._conversations if c.conversation_id != conversation_id]
        self._save()
        self._publish_updated(conversation_id)
        if self.get_active_conversation_id() == conversation_id:
            self.set_active_conversation_id(None)

    def set_title(self, conversation_id: str, title: str) -> Optional[Conversation]:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        conversation.title = title
        self._save()
        self._publish_updated(conversation_id)
        return conversation

    def add_message(self, conversation_id: str, role: str, content: str) -> Optional[Conversation]:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        conversation.messages.append(
            ConversationMessage(role=role, content=content, timestamp=datetime.now().isoformat(timespec="seconds"))
        )
        self._bump_updated_at(conversation)
        self._save()
        self._publish_updated(conversation_id)
        return conversation

    # ------------------------------------------------------------------
    # Active conversation — the one both chat surfaces read/append to.
    # ------------------------------------------------------------------

    def get_active_conversation_id(self) -> Optional[str]:
        return self.context.config.get("assistant.active_conversation_id", None)

    def set_active_conversation_id(self, conversation_id: Optional[str]) -> None:
        self.context.config.set("assistant.active_conversation_id", conversation_id)
        self.context.config.save()
        # A distinct event from "conversation.updated" — that one means
        # "this specific conversation's content/title changed"; this one
        # means "the *pointer* changed, you're now looking at a
        # different conversation entirely" (switching, starting new, or
        # a delete_conversation() that happened to remove the active
        # one). Both chat surfaces need to tell these apart: the former
        # only matters if it's about whichever conversation they're
        # currently displaying, the latter always means "reload,
        # regardless of what you were just showing."
        if self.context.events is not None:
            self.context.events.publish("conversation.active_changed", conversation_id=conversation_id)

    def get_or_create_active_conversation(self) -> Conversation:
        """
        The conversation both chat surfaces should read/append to right
        now. Creates a fresh one the first time this is ever called (no
        active id yet) or if the previously-active conversation was
        since deleted — never returns None, so callers never need their
        own "what if there's nothing yet" branch.
        """
        active_id = self.get_active_conversation_id()
        if active_id is not None:
            conversation = self.get_conversation(active_id)
            if conversation is not None:
                return conversation
        conversation = self.create_conversation()
        self.set_active_conversation_id(conversation.conversation_id)
        return conversation

    def start_new_active_conversation(self) -> Conversation:
        """Explicit "New Conversation" action — always creates a fresh thread and makes it active."""
        conversation = self.create_conversation()
        self.set_active_conversation_id(conversation.conversation_id)
        return conversation
