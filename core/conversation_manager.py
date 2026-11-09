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
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CONVERSATIONS_FILE = _DATA_DIR / "conversations.json"

DEFAULT_TITLE = "New Conversation"


# Message privacy (2026-09-27, Cognitive Extension slice A — see
# core/conversation_modes.py). A private message stays in memory for
# the rest of this run (so the model keeps its context mid-conversation)
# but is never written to conversations.json: journaled text belongs in
# the encrypted core/private_journal.py, and off-the-record text
# belongs nowhere.
PRIVACY_NONE = ""
PRIVACY_JOURNAL = "journal"  # saved to the encrypted private journal only
PRIVACY_OFF_RECORD = "off_record"  # saved nowhere
PRIVACY_PRIVATE = "private"  # e.g. a turn that read the private journal back


@dataclass
class ConversationMessage:
    """One message in a conversation: who (the person or MIA), what, when, and its privacy (journal, off the record,
    or a private turn), which is never saved: a private message isn't written at all.
    """
    role: str  # "user" | "assistant"
    content: str
    timestamp: str = ""  # ISO datetime
    privacy: str = PRIVACY_NONE  # never persisted: private messages aren't written at all

    def to_dict(self) -> dict:
        """The message as saved (its privacy isn't)."""
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @staticmethod
    def from_dict(data: dict) -> "ConversationMessage":
        """A message from its saved dict."""
        return ConversationMessage(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class Conversation:
    """One conversation: its messages, title, mode (companion, journal...), whether it's journaling or off the record,
    the textbook chapter it's studying, and this run's transient state (a private turn, the open journal session, an
    offer waiting for a yes, a support choice asked), none of which is saved.
    """
    conversation_id: str
    title: str = DEFAULT_TITLE
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    # Conversation mode state (core/conversation_modes.py). Persisted so
    # a restart mid-journal stays in journal mode; none of it is content.
    mode: str = "companion"
    journal: bool = False
    off_record: bool = False
    # Textbook tutor (core/textbook_study.py): which book and chapter a
    # study or quiz conversation is on. Persisted, like the mode.
    study_book_id: Optional[str] = None
    study_chapter: Optional[int] = None
    # Transient, this run only: the current turn reads private data
    # (the private journal), so its messages must not be persisted.
    private_turn: bool = field(default=False, repr=False, compare=False)
    # Transient: the latest organization (title/mood/themes/summary) for
    # the open journal session, so re-saving it doesn't need to read the
    # encrypted entry back (which would need the passphrase).
    journal_organization: Optional[dict] = field(default=None, repr=False, compare=False)
    # Transient: MIA's offer to record something the owner mentioned in
    # passing (core/passing_mentions.py), waiting for a yes on the next turn.
    pending_offer: Optional[object] = field(default=None, repr=False, compare=False)
    # Transient: MIA's offer to track something the person said they did (core/did_it.py, DEC-0148), waiting for a
    # yes on the next turn, and the message already answered by that code this turn (so it isn't offered twice).
    pending_track: Optional[dict] = field(default=None, repr=False, compare=False)
    did_handled: Optional[str] = field(default=None, repr=False, compare=False)
    # Transient: MIA just asked which kind of support the user wants
    # (core/support_choice.py), and when she last asked.
    awaiting_support: bool = field(default=False, repr=False, compare=False)
    support_asked_at: Optional[float] = field(default=None, repr=False, compare=False)
    # Transient: the open journal session's entry id and where it starts
    # in `messages`. Not persisted on purpose: after a restart the
    # earlier session's messages are gone from memory (they were never
    # written here), so continuing must start a new entry rather than
    # overwrite the saved one with only the newer half.
    journal_session_id: Optional[str] = field(default=None, repr=False, compare=False)
    journal_start_index: int = field(default=0, repr=False, compare=False)

    def current_privacy(self) -> str:
        """What the next message is: off the record, journal, private (this turn read the private journal), or none."""
        if self.off_record:
            return PRIVACY_OFF_RECORD
        if self.journal:
            return PRIVACY_JOURNAL
        if self.private_turn:
            return PRIVACY_PRIVATE
        return PRIVACY_NONE

    def to_dict(self) -> dict:
        """The conversation as saved: only messages with no privacy are written."""
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages if not m.privacy],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "mode": self.mode,
            "journal": self.journal,
            "off_record": self.off_record,
            "study_book_id": self.study_book_id,
            "study_chapter": self.study_chapter,
        }

    @staticmethod
    def from_dict(data: dict) -> "Conversation":
        """A conversation from its saved dict."""
        return Conversation(
            conversation_id=data.get("conversation_id", uuid.uuid4().hex[:10]),
            title=data.get("title", DEFAULT_TITLE),
            messages=[ConversationMessage.from_dict(d) for d in data.get("messages", [])],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            mode=data.get("mode", "companion"),
            journal=bool(data.get("journal", False)),
            off_record=bool(data.get("off_record", False)),
            study_book_id=data.get("study_book_id"),
            study_chapter=data.get("study_chapter"),
        )


class ConversationManager:
    """The person's conversations with MIA (conversations.json in their folder, written through atomic_write_text),
    and which one is active: the thread both chat surfaces read and add to.
    """
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or the
        # shared data/ folder by default.
        """Points at the person's file (data/ by default) and loads it."""
        self.data_dir = Path(data_dir) if data_dir is not None else _CONVERSATIONS_FILE.parent
        self._conversations_file = self.data_dir / _CONVERSATIONS_FILE.name if data_dir is not None else _CONVERSATIONS_FILE
        self.context = context
        self._conversations: list[Conversation] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Reads the conversations; a damaged file is logged, reported (notify_data_corruption) and starts empty. The file is sealed on disk (DEC-0126); open_text reads it sealed or plain, and one that won't open is
        copied aside first and counts as damaged (never stopping MIA from starting)."""
        if not self._conversations_file.exists():
            self._conversations = []
            return
        try:
            raw = json.loads(open_text(self._conversations_file))
            self._conversations = [Conversation.from_dict(d) for d in raw]
        except (ValueError, OSError):  # ValueError: bad JSON, or a sealed file that won't open (copied aside)
            log.exception("Failed to load conversations.json — starting with an empty list.")
            notify_data_corruption(self.context, "conversations.json")
            self._conversations = []

    def _save(self) -> None:
        """Writes every conversation atomically (private messages left out by to_dict)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._conversations_file,
            json.dumps([c.to_dict() for c in self._conversations], indent=2),
            encoding="utf-8",
        )

    def save(self) -> None:
        """Persist after a caller changed a conversation's mode flags directly."""
        self._save()

    def _bump_updated_at(self, conversation: Conversation) -> None:
        """Stamps a conversation as changed now."""
        conversation.updated_at = datetime.now().isoformat(timespec="seconds")

    def _publish_updated(self, conversation_id: str) -> None:
        """Publishes conversation.updated, so a screen showing it refreshes."""
        if self.context.events is not None:
            self.context.events.publish("conversation.updated", conversation_id=conversation_id)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_conversation(self) -> Conversation:
        """Starts an empty conversation and saves it."""
        now = datetime.now().isoformat(timespec="seconds")
        conversation = Conversation(conversation_id=uuid.uuid4().hex[:10], created_at=now, updated_at=now)
        self._conversations.append(conversation)
        self._save()
        log.info("Conversation created: '%s'", conversation.conversation_id)
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """The conversation with this id, or None."""
        for conversation in self._conversations:
            if conversation.conversation_id == conversation_id:
                return conversation
        return None

    def all_conversations(self) -> list[Conversation]:
        """Most-recently-updated first — matches a ChatGPT-style history list's own ordering."""
        return sorted(self._conversations, key=lambda c: c.updated_at, reverse=True)

    def delete_conversation(self, conversation_id: str) -> None:
        """Deletes a conversation (and clears the active one if it was that)."""
        self._conversations = [c for c in self._conversations if c.conversation_id != conversation_id]
        self._save()
        self._publish_updated(conversation_id)
        if self.get_active_conversation_id() == conversation_id:
            self.set_active_conversation_id(None)

    def set_title(self, conversation_id: str, title: str) -> Optional[Conversation]:
        """Renames a conversation (None when it's gone)."""
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        conversation.title = title
        self._save()
        self._publish_updated(conversation_id)
        return conversation

    def add_message(self, conversation_id: str, role: str, content: str) -> Optional[Conversation]:
        """Adds a message, stamped now and marked with the conversation's current privacy (so a private one is never
        saved), then saves and publishes conversation.updated. None when the conversation is gone.
        """
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        conversation.messages.append(
            ConversationMessage(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                privacy=conversation.current_privacy(),
            )
        )
        self._bump_updated_at(conversation)
        self._save()
        self._publish_updated(conversation_id)
        return conversation

    # ------------------------------------------------------------------
    # Active conversation — the one both chat surfaces read/append to.
    # ------------------------------------------------------------------

    def get_active_conversation_id(self) -> Optional[str]:
        """The active conversation's id (assistant.active_conversation_id in the config), or None."""
        return self.context.config.get("assistant.active_conversation_id", None)

    def set_active_conversation_id(self, conversation_id: Optional[str]) -> None:
        """Makes a conversation the active one (saved in the config) and publishes that the pointer changed (a
        different event from a conversation's content changing, so both chat surfaces reload).
        """
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
