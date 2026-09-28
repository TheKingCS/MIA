"""
core.talk_it_out
===================

Slice A of docs/COGNITIVE_EXTENSION_PROPOSAL.md, "Talk it out": the
glue every chat surface (Home's chat bar, the character panel, the
Assistant module, the phone, the headless voice loop) calls around one
turn, so they all behave the same way.

Before the model (`pre_turn()`):
1. Explicit mode switches are applied to the conversation
   (core/conversation_modes.py): "just listen", "I want to journal",
   "off the record", "back to normal"...
2. A turn that reads the private journal back is marked private, so
   neither the question nor MIA's answer is written to
   conversations.json.
3. The safety floor (core/safety_floor.py) runs. If it fires, the
   caller says its fixed reply and does NOT call the model.

After the reply (`plan_followup()` / `apply_followup()`), exactly one
background LLM job, replacing the old always-extract-memories step:
- journaling: the session is saved to the encrypted private journal
  right away (no model needed), then organized (title, mood, themes,
  summary) and saved again;
- normal conversation: memories are extracted as before;
- off the record, or a private turn: nothing.

Journaled text never becomes an ordinary memory: memories are plain
JSON, and the owner chose an encrypted journal. MIA uses the journal
to support the user through `journal_context_block()` instead, which
only has anything to say while the journal is unlocked.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_chat import build_memory_extraction_prompt, parse_extracted_memories
from core.conversation_manager import DEFAULT_TITLE, PRIVACY_JOURNAL, Conversation
from core.conversation_modes import COMPANION, DIRECT, LISTEN, MOMENTUM, PLAN, detect_mode_change
from core.logger import get_logger
from core.passing_mentions import carry_out, detect_offer, is_yes
from core.private_journal import JournalExchange, JournalLockedError, PrivateJournalEntry
from core.safety_floor import detect_danger, safety_reply, trusted_contact_from
from core.textbook_study import is_study_mode, update_study_target

log = get_logger(__name__)

JOURNAL_TITLE = "Journal session"
OFF_RECORD_TITLE = "Off the record"

NOT_SET_UP_NOTICE = (
    "I'm listening. One thing first: your private journal isn't set up yet, so I can't save this "
    "session. You can set it up in Notes under Private Journal, and I'll save from then on."
)

# Phrases that read the private journal back. Shared by pre_turn()
# (to keep the turn out of conversations.json) and the journal tools'
# trigger phrases, so the two can't drift apart.
JOURNAL_READ_PHRASES = (
    "my journal", "journal entries", "journal entry about", "i've been journaling", "ive been journaling",
    "i've been writing about", "have i been writing about", "what have i been writing",
    "what did i journal", "what have i journaled", "when did i last feel", "last time i felt",
    "what's been on my mind", "whats been on my mind", "journal themes",
)


def _looks_like_journal_read(prompt: str) -> bool:
    text = f" {prompt.lower().replace('’', chr(39))} "
    return any(phrase in text for phrase in JOURNAL_READ_PHRASES)


@dataclass
class PreTurn:
    # Say this and skip the model: the safety floor fired, or the owner
    # said yes to MIA's offer to record something (core/passing_mentions.py).
    fixed_reply: Optional[str] = None
    notice: Optional[str] = None  # say this first, then continue to the model as usual


def _persist(context: AppContext, conversation: Conversation) -> None:
    manager = getattr(context, "conversations", None)
    if manager is not None and manager.get_conversation(conversation.conversation_id) is conversation:
        manager.save()


def _journal_ready(context: AppContext) -> bool:
    journal = getattr(context, "private_journal", None)
    return journal is not None and journal.is_set_up()


def pre_turn(context: AppContext, conversation: Conversation, prompt: str) -> PreTurn:
    """Call BEFORE adding the user's message to the conversation, so the
    message itself is stored with the privacy its own words asked for."""
    result = PreTurn()
    conversation.private_turn = _looks_like_journal_read(prompt)

    # "Propose, you confirm": a yes to the offer MIA just made records it;
    # anything else lets the offer go.
    offer, conversation.pending_offer = conversation.pending_offer, None
    if offer is not None and getattr(offer, "shown", False) and not offer.expired() and is_yes(prompt):
        result.fixed_reply = carry_out(context, offer)
        return result

    change = detect_mode_change(prompt)
    if not change.is_empty:
        if change.mode is not None:
            conversation.mode = change.mode
        if change.journal is True and not conversation.journal:
            conversation.journal = True
            conversation.journal_session_id = None  # a fresh entry on the first save
            conversation.journal_start_index = len(conversation.messages)
            conversation.journal_organization = None
            if not _journal_ready(context):
                result.notice = NOT_SET_UP_NOTICE
        elif change.journal is False:
            conversation.journal = False
            conversation.journal_session_id = None
        if change.off_record is not None:
            conversation.off_record = change.off_record
        # A default title would be generated from the first exchange and
        # stored in plain text; a private conversation gets a neutral one.
        if conversation.title == DEFAULT_TITLE and (conversation.journal or conversation.off_record):
            conversation.title = JOURNAL_TITLE if conversation.journal else OFF_RECORD_TITLE
        _persist(context, conversation)

    # Textbook tutor: which book/chapter this study or quiz turn is on.
    if is_study_mode(conversation.mode):
        before = (conversation.study_book_id, conversation.study_chapter)
        notice = update_study_target(context, conversation, prompt)
        if notice and not result.notice:
            result.notice = notice
        if (conversation.study_book_id, conversation.study_chapter) != before:
            _persist(context, conversation)

    if detect_danger(prompt):
        conversation.mode = LISTEN
        _persist(context, conversation)
        result.fixed_reply = safety_reply(trusted_contact_from(context))
        return result

    if _offers_allowed(conversation) and getattr(context, "assistant_actions", None) is not None:
        conversation.pending_offer = detect_offer(prompt, context)
    return result


_OFFER_MODES = (COMPANION, DIRECT, MOMENTUM, PLAN)


def _offers_allowed(conversation: Conversation) -> bool:
    """Not while MIA is just listening, journaling, off the record,
    tutoring or reading the private journal back."""
    return (conversation.mode in _OFFER_MODES and not conversation.journal and not conversation.off_record
            and not conversation.private_turn)


def with_offer(conversation: Conversation, reply: str) -> str:
    """Call on MIA's plain reply (not when she ran a tool): adds her offer
    to record what the owner just mentioned, if there is one. The offer
    counts for the next turn only if it was actually said."""
    offer = conversation.pending_offer
    if offer is None:
        return reply
    offer.shown = True
    return f"{reply.rstrip()} {offer.question}" if reply.strip() else offer.question


# ---------------------------------------------------------------------------
# Journal sessions
# ---------------------------------------------------------------------------

_MAX_EXCHANGES_FOR_ORGANIZING = 24
_MAX_CHARS_PER_EXCHANGE = 600

_ORGANIZE_PROMPT = (
    "Below is a journal conversation between the user and MIA, their assistant. Organize it for the "
    "user's private journal. Reply in exactly this form, four lines:\n"
    "Title: <3 to 6 words>\n"
    "Mood: <one or two words for how the user seems to feel, in their own terms>\n"
    "Themes: <2 to 4 short themes, comma separated>\n"
    "Summary: <two or three sentences to the user, starting with 'You talked about'>\n"
    "Use only what the user actually said. Don't add advice.\n\n"
    "Conversation:\n{transcript}"
)


def journal_exchanges(conversation: Conversation) -> list[JournalExchange]:
    return [
        JournalExchange(m.role, m.content, m.timestamp)
        for m in conversation.messages[conversation.journal_start_index:]
        if m.privacy == PRIVACY_JOURNAL
    ]


def build_journal_organize_prompt(exchanges: list[JournalExchange]) -> str:
    """Pure logic."""
    lines = []
    for exchange in exchanges[-_MAX_EXCHANGES_FOR_ORGANIZING:]:
        speaker = "User" if exchange.role == "user" else "MIA"
        lines.append(f"{speaker}: {exchange.content[:_MAX_CHARS_PER_EXCHANGE]}")
    return _ORGANIZE_PROMPT.format(transcript="\n".join(lines))


_FIELD = re.compile(r"^\W*(title|mood|themes?|summary)\W*:\s*(.+)$", re.IGNORECASE)


def parse_journal_organization(raw: Optional[str]) -> Optional[dict]:
    """Pure logic. Lenient: the small model adds bullets, bold, quotes.
    None unless at least a title or a summary came back."""
    if not raw:
        return None
    found: dict[str, str] = {}
    for line in raw.splitlines():
        match = _FIELD.match(line.strip())
        if match:
            key = match.group(1).lower().rstrip("s") if match.group(1).lower().startswith("theme") else match.group(1).lower()
            found.setdefault(key, match.group(2).strip().strip("*\"' "))
    if not found.get("title") and not found.get("summary"):
        return None
    themes = [t.strip().strip("*\"' .").lower() for t in found.get("theme", "").split(",")]
    return {
        "title": found.get("title", "")[:60],
        "mood": found.get("mood", "")[:40],
        "themes": [t[:30] for t in themes if t][:5],
        "summary": found.get("summary", "")[:600],
    }


def record_journal_turn(context: AppContext, conversation: Conversation) -> bool:
    """Save the open journal session (encrypted). No model needed, works
    while the journal is locked. False when there's nothing to save or
    no journal to save into."""
    journal = getattr(context, "private_journal", None)
    if journal is None or not journal.is_set_up() or not conversation.journal:
        return False
    exchanges = journal_exchanges(conversation)
    if not exchanges:
        return False
    if conversation.journal_session_id is None:
        conversation.journal_session_id = uuid.uuid4().hex[:12]
    organization = conversation.journal_organization or {}
    entry = PrivateJournalEntry(
        entry_id=conversation.journal_session_id,
        title=organization.get("title") or f"Journal, {date.today().strftime('%B')} {date.today().day}",
        summary=organization.get("summary", ""),
        mood=organization.get("mood", ""),
        themes=list(organization.get("themes", [])),
        exchanges=exchanges,
        conversation_id=conversation.conversation_id,
        created_at=exchanges[0].timestamp[:19] if exchanges[0].timestamp else "",
    )
    try:
        journal.save_entry(entry)
    except Exception:
        log.exception("Couldn't save the journal session.")
        return False
    return True


# ---------------------------------------------------------------------------
# After the reply
# ---------------------------------------------------------------------------

@dataclass
class Followup:
    kind: str  # "memories" | "journal"
    prompt: str
    conversation_id: str


def plan_followup(context: AppContext, conversation: Conversation, user_message: str) -> Optional[Followup]:
    """What background LLM job (if any) to run after a normal reply.
    Journaling also saves the session right here, before the model
    organizes it, so nothing is lost if the model never answers."""
    if conversation.off_record or conversation.private_turn:
        return None
    if conversation.journal:
        if not record_journal_turn(context, conversation):
            return None
        return Followup("journal", build_journal_organize_prompt(journal_exchanges(conversation)), conversation.conversation_id)
    if getattr(context, "user_memories", None) is None:
        return None
    return Followup("memories", build_memory_extraction_prompt(user_message), conversation.conversation_id)


def apply_followup(context: AppContext, conversation: Conversation, followup: Followup, raw: Optional[str]) -> None:
    if followup.kind == "memories":
        if context.user_memories is None:
            return
        for category, fact in parse_extracted_memories(raw):
            context.user_memories.add_memory(fact, category=category, source_conversation_id=followup.conversation_id)
        return
    organization = parse_journal_organization(raw)
    if organization is not None and conversation.journal:
        conversation.journal_organization = organization
        record_journal_turn(context, conversation)


def after_fixed_reply(context: AppContext, conversation: Conversation) -> None:
    """After the safety floor's fixed reply: keep an open journal session
    current. Never extracts memories from a message like that."""
    if conversation.journal and not conversation.off_record:
        record_journal_turn(context, conversation)


# ---------------------------------------------------------------------------
# Using the journal to support the user
# ---------------------------------------------------------------------------

_CONTEXT_ENTRIES = 3


def _entry_date(entry: PrivateJournalEntry) -> str:
    try:
        parsed = datetime.fromisoformat(entry.created_at)
    except ValueError:
        return entry.created_at[:10]
    return f"{parsed.strftime('%B')} {parsed.day}"


def journal_context_block(context: AppContext) -> str:
    """Recent journal sessions for the personal-mode system prompt.
    Empty unless the journal is unlocked: locked means unreadable, MIA
    included."""
    journal = getattr(context, "private_journal", None)
    if journal is None or not journal.is_unlocked():
        return ""
    try:
        entries = journal.all_entries()[:_CONTEXT_ENTRIES]
    except JournalLockedError:
        return ""
    if not entries:
        return ""
    lines = []
    for entry in entries:
        detail = "; ".join(part for part in (
            f"mood: {entry.mood}" if entry.mood else "",
            f"themes: {', '.join(entry.themes)}" if entry.themes else "",
        ) if part)
        lines.append(f"- {_entry_date(entry)}, {entry.title}" + (f" ({detail})" if detail else ""))
    return (
        "Recent sessions from the user's private journal (for context; mention them only if it helps):\n"
        + "\n".join(lines)
    )


# ---------------------------------------------------------------------------
# Assistant tools: reading the journal back
# ---------------------------------------------------------------------------

def _journal_unavailable(context: AppContext) -> Optional[str]:
    journal = getattr(context, "private_journal", None)
    if journal is None or not journal.is_set_up():
        return "You haven't set up a private journal yet. You can do that in Notes under Private Journal."
    if not journal.is_unlocked():
        return "Your private journal is locked. Unlock it in Notes under Private Journal, then ask me again."
    return None


def _describe(entry: PrivateJournalEntry) -> str:
    body = entry.summary or (entry.user_text[:160] + ("…" if len(entry.user_text) > 160 else ""))
    return f"On {_entry_date(entry)} ({entry.title}): {body}"


def _action_read_private_journal(context: AppContext, arguments: dict) -> str:
    problem = _journal_unavailable(context)
    if problem:
        return problem
    query = str(arguments.get("query") or "").strip()
    entries = context.private_journal.search(query) if query else context.private_journal.all_entries()
    if not entries:
        return f"I didn't find anything in your journal about {query}." if query else "Your private journal is empty so far."
    shown = entries[:3]
    more = f" There are {len(entries) - 3} more." if len(entries) > 3 else ""
    return " ".join(_describe(e) for e in shown) + more


def _action_get_journal_themes(context: AppContext, arguments: dict) -> str:
    problem = _journal_unavailable(context)
    if problem:
        return problem
    days = int(arguments.get("days") or 30)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    entries = [e for e in context.private_journal.all_entries() if e.created_at >= cutoff]
    if not entries:
        return f"You haven't journaled in the last {days} days."
    themes = Counter(t for e in entries for t in e.themes).most_common(4)
    moods = [e.mood for e in entries if e.mood][:4]
    parts = [f"In the last {days} days you journaled {len(entries)} time{'s' if len(entries) != 1 else ''}."]
    if themes:
        parts.append("What came up most: " + ", ".join(f"{t} ({n})" for t, n in themes) + ".")
    if moods:
        parts.append("How you described feeling: " + ", ".join(moods) + ".")
    return " ".join(parts)


def register_journal_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="read_private_journal", domain="private_journal",
        description=(
            "Read back the user's private journal (sessions they journaled by talking with MIA), newest first, "
            "optionally only entries about a topic."
        ),
        parameters={"type": "object", "properties": {
            "query": {"type": "string", "description": "Topic to look for, e.g. 'work' or 'debt'. Leave out for the latest."},
        }, "required": []},
        handler=_action_read_private_journal,
        trigger_phrases=JOURNAL_READ_PHRASES,
    ))
    registry.register(AssistantAction(
        name="get_journal_themes", domain="private_journal",
        description="What the user has been journaling about lately: how often, the most common themes, and moods.",
        parameters={"type": "object", "properties": {
            "days": {"type": "integer", "description": "How many days back. Default 30."},
        }, "required": []},
        handler=_action_get_journal_themes,
        trigger_phrases=("what have i been writing", "what's been on my mind", "whats been on my mind", "journal themes",
                         "what have i been journaling", "what have i journaled"),
    ))


__all__ = [
    "COMPANION", "PreTurn", "Followup", "pre_turn", "plan_followup", "apply_followup", "after_fixed_reply",
    "record_journal_turn", "journal_context_block", "register_journal_actions",
    "build_journal_organize_prompt", "parse_journal_organization", "JOURNAL_READ_PHRASES",
]
