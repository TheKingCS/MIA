"""
core.conversation_state
=========================

What a conversation is about (DEC-0052 step 4, first slice;
docs/REASONING_PLAN.md section 5). Before, every message started over:
"Which debt should I pay first?" then "what if I added $300 a month?"
or "why?" reached the model with no idea which records it was about.

Now each conversation remembers its last question plan (and the
question that started it) for a while. A short follow-up that leans on
it ("why?", "what about next month?", "and if I paid $300?", "tell me
more about that") goes back to the same plan, gathered again with both
questions, so the follow-up is answered from the same records, not a
guess. Kept in memory for the session: it's about the conversation
happening now, never stored as a fact about the person.

Not yet (the rest of section 5): which single record "it" means across
any turn, open questions MIA asked, and a running summary.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

FRESH_SECONDS = 15 * 60  # a follow-up after this long starts over
MAX_WORDS = 10

_LEADS = re.compile(r"^(and|but|so|ok|okay|also|then|why|how come|what about|how about|what if|tell me more|more|"
                    r"what else|anything else|is that|are those|does that|which one|how much is that|explain|"
                    r"go on|really|wait)\b", re.IGNORECASE)
_LEANS = re.compile(r"\b(it|that|this|those|these|them|they|there|the first one|the other one|same)\b", re.IGNORECASE)


@dataclass
class State:
    plan: str
    question: str
    at: float


_states: dict[str, State] = {}


def _key(conversation) -> Optional[str]:
    cid = getattr(conversation, "conversation_id", None)
    return str(cid) if cid else None


def remember_plan(conversation, plan: str, question: str) -> None:
    key = _key(conversation)
    if key:
        _states[key] = State(plan, question, time.monotonic())


def forget(conversation) -> None:
    _states.pop(_key(conversation) or "", None)


def looks_like_follow_up(text: str) -> bool:
    """Pure logic. A short message that leans on what came before."""
    said = (text or "").strip()
    words = said.split()
    if not words or len(words) > MAX_WORDS:
        return False
    return bool(_LEADS.match(said)) or bool(_LEANS.search(said))


def follow_up(conversation, text: str) -> Optional[State]:
    """The plan this message follows up on, when it's a fresh follow-up."""
    key = _key(conversation)
    state = _states.get(key) if key else None
    if state is None or time.monotonic() - state.at > FRESH_SECONDS or not looks_like_follow_up(text):
        return None
    return state
