"""
core.quick_capture
====================

Quick capture (2026-10-01): one box, reachable from anywhere (the "+"
in the header, or Ctrl+Shift+Space), for whatever is on your mind: "milk
and eggs", "changed the truck's oil today", "dentist Tuesday at 2",
"Pat's email is pat@example.com", "idea: a rain barrel by the shed". MIA
files it where it belongs.

How:
- The Assistant handles it as a normal turn (the same tools and routing
  as chat), in a conversation of its own, "Quick capture", in History.
- If a tool changed something, that's the filing: MIA says what she did,
  and "undo that" (core/undo_log.py) takes it back.
- If nothing was filed (the model was unsure, asked a question, or isn't
  running), the text is saved as a note tagged "capture", so nothing you
  jot down is ever lost. You can file it properly later.

The model only ever proposes where things go through the existing tools;
the fallback note needs no model at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

TITLE = "✚ Quick capture"
NOTE_TAG = "capture"


@dataclass
class CaptureResult:
    reply: str
    filed: bool  # a tool put it somewhere (undoable); False = kept as a note
    note_id: Optional[str] = None


def _conversation(context):
    conversations = getattr(context, "conversations", None)
    if conversations is None:
        return None
    for conversation in conversations.all_conversations():
        if conversation.title == TITLE:
            return conversation
    conversation = conversations.create_conversation()
    conversation.title = TITLE
    conversations.save()
    return conversation


def _latest_change(context):
    from core.person_settings import person_id

    undo = getattr(context, "undo", None)
    recent = undo.recent(person_id(context)) if undo is not None else []
    return recent[0] if recent else None


def save_as_note(context, text: str):
    journal = getattr(context, "journal", None)
    if journal is None:
        return None
    first_line = text.strip().splitlines()[0]
    title = first_line if len(first_line) <= 60 else first_line[:57].rstrip() + "…"
    return journal.add_entry(title=title, body=text.strip(), tags=[NOTE_TAG])


def capture(context, text: str, turn_runner=None) -> CaptureResult:
    """File `text`. Runs the Assistant (slow-ish), so call it off the
    screen's thread. `turn_runner` is for tests."""
    text = (text or "").strip()
    if not text:
        return CaptureResult("Nothing to capture.", False)
    if turn_runner is None:
        from core.assistant_turn import run_assistant_turn as turn_runner
    before = _latest_change(context)
    replies: list[str] = []
    conversation = _conversation(context)
    if conversation is not None and getattr(context, "llm", None) is not None:
        try:
            turn = turn_runner(context, conversation, text)
            replies = list(turn.replies) if turn.llm_available else []
            conversations = getattr(context, "conversations", None)
            if conversations is not None:
                conversations.save()
        except Exception:
            log.exception("Quick capture: the Assistant turn failed; keeping it as a note.")
    after = _latest_change(context)
    if after is not None and after is not before:
        return CaptureResult(" ".join(replies) or "Done.", True)
    note = save_as_note(context, text)
    if note is None:
        return CaptureResult("I couldn't save that anywhere.", False)
    return CaptureResult("Saved as a note (Notes, tagged \"capture\"). You can file it later.", False,
                         getattr(note, "entry_id", None))
