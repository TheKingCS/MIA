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

**What came earlier** (`earlier_topics`): the model only sees the last
few messages, so in a long conversation the start was simply gone. The
questions asked before that window go into the system message, in the
person's own words, built by code (no summary written by the model, so
nothing in it can be made up).

Not yet (the rest of section 5): which single record "it" means across
any turn, and open questions MIA asked.
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


EARLIER_SHOWN = 6
EARLIER_CHARS = 90


def earlier_topics(messages: list, kept: int) -> str:
    """Pure logic. The person's questions from before the last `kept`
    messages (the ones the model sees), most recent last; "" when nothing
    was cut."""
    before = messages[:-kept] if kept > 0 else list(messages)
    asked = [str(getattr(m, "content", "") or "").strip() for m in before if getattr(m, "role", "") == "user"]
    asked = [a if len(a) <= EARLIER_CHARS else a[:EARLIER_CHARS].rsplit(" ", 1)[0] + "…" for a in asked if a]
    if not asked:
        return ""
    return ("Earlier in this conversation (older than the messages below) they asked: "
            + "; ".join(f"“{a}”" for a in asked[-EARLIER_SHOWN:]) + ".")


_YES = re.compile(r"^(yes|yeah|yep|yup|sure|ok|okay|please|please do|do it|go ahead|sounds good|that works|"
                  r"yes please|sure thing|let's do it|absolutely|definitely)\b[\s!.,]*(please|thanks|thank you)?[\s!.]*$",
                  re.IGNORECASE)


def agreed_to(conversation, prompt: str) -> Optional[str]:
    """Pure logic. When `prompt` is a plain yes to the question MIA just
    asked ("Want me to add it to your calendar?" -> "yes please"), that
    question; else None. Before, "yes" matched no tool, so the model had
    nothing to do it with and could only say it had (2026-10-30)."""
    if not _YES.match((prompt or "").strip()):
        return None
    before = [m for m in getattr(conversation, "messages", []) or []
              if not (getattr(m, "role", "") == "user" and str(getattr(m, "content", "")) == prompt)]
    last = before[-1] if before else None
    said = str(getattr(last, "content", "") or "").strip() if last is not None else ""
    if getattr(last, "role", "") != "assistant" or not said.endswith("?"):
        return None
    sentences = re.split(r"(?<=[.!])\s+", said)
    return sentences[-1]


LOOK_BACK = 8  # messages searched for the last thing named


def what_it_means(context, conversation, prompt: str) -> Optional[str]:
    """What "it" / "that" in `prompt` most likely means: the last of the
    person's own records named in the conversation (by them or by MIA),
    when the message leans on a pronoun and names nothing itself."""
    from core.assistant_actions import looks_like_question
    from core.question_plans import CHANGE_VERBS

    registry = getattr(context, "assistant_actions", None)
    if registry is None or conversation is None or not _LEANS.search(prompt or ""):
        return None
    first = (prompt or "").strip().lower().split(" ", 1)[0].strip(",.!?")
    if not (looks_like_question(prompt) or first in CHANGE_VERBS):
        return None  # "That's cool." leans on "that" but asks nothing about a record
    if registry.named_things(prompt, context):
        return None  # it names its own subject
    before = [m for m in getattr(conversation, "messages", []) if str(getattr(m, "content", "")) != prompt]
    for m in reversed(before[-LOOK_BACK:]):
        named = registry.named_things(str(getattr(m, "content", "") or ""), context)
        if len(named) == 1:  # two things named in one message: too unsure to pick
            return named[0]
        if named:
            return None
    return None


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
