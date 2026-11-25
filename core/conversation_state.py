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

**A tool's follow-up** (`followed_question`, 2026-11-24): "how long do I process quarts of green beans?" then "and
what about corn?" or "what if I'm at 3,000 feet?". The follow-up names no tool's words, so before, it got no tools and
the model answered alone (live check: it made up a curing-salt amount for "what about 8 pounds?"). Now a short
follow-up is routed with the person's last question that brought tools, so the same tools come along (with any of
its own), and the model is told to pass the tool `follow_up_question`: the new words first, then the question. A
follow-up that names no tool settles on the one its question named (`note_follow_up_tool`, `follow_up_tool`;
core/assistant_chat.named_tool, settle_on_named_tool), called by code when the model won't.

Not yet (the rest of section 5): which single record "it" means across
any turn, and open questions MIA asked.
A follow-up to a tool's answer outside a plan conversation is the model's, never a plan its words match
(`follows_a_tool`).
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
_LEANS = re.compile(r"\b(it|that|this|those|these|them|they|there|the first one|the other one|same)\b"
                    # "what should I do to get ready?" after a storm: getting ready for what was just said (never
                    # "get ready for work", which names its own)
                    r"|\b(get ready|be ready|prepare|be prepared)\W*$", re.IGNORECASE)


@dataclass
class State:
    """What a conversation is in the middle of: the question plan it last used, the question, and when."""
    plan: str
    question: str
    at: float


_states: dict[str, State] = {}


def _key(conversation) -> Optional[str]:
    """The conversation's id, as the key its state is kept under (None without one)."""
    cid = getattr(conversation, "conversation_id", None)
    return str(cid) if cid else None


def remember_plan(conversation, plan: str, question: str) -> None:
    """Remembers the plan a conversation just used, so a follow-up ("what about next month?") can lean on it."""
    key = _key(conversation)
    if key:
        _states[key] = State(plan, question, time.monotonic())


def forget(conversation) -> None:
    """Forgets what a conversation was in the middle of."""
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
FOLLOW_BACK = 4  # messages back a tool's follow-up may reach (the last exchange or two)


def followed_question(context, conversation, prompt: str) -> Optional[str]:
    """The person's last question in this conversation that brought tools, when `prompt` is a short follow-up
    (`looks_like_follow_up`, or a short "what about corn?"); else None. One that brings tools of its own still gets
    it ("what if I used 350 watt panels?" brings a power tool, and the sizing question's tools must come too: the
    caller routes on both). Only the last FOLLOW_BACK messages are searched, and only the person's own words."""
    registry = getattr(context, "assistant_actions", None)
    said = (prompt or "").strip()
    if registry is None or conversation is None or not said or len(said.split()) > MAX_WORDS:
        return None
    if not (_LEADS.match(said) or _LEANS.search(said)):
        return None
    before = [m for m in getattr(conversation, "messages", []) or []
              if not (getattr(m, "role", "") == "user" and str(getattr(m, "content", "")) == prompt)]
    for m in reversed(before[-FOLLOW_BACK:]):
        if getattr(m, "role", "") != "user":
            continue
        asked = str(getattr(m, "content", "") or "").strip()
        if asked and asked != said and registry.matching_actions(asked, context):
            return asked
    return None


TURN_SECONDS = 180  # a turn's follow-up words are good this long (the model's reply and its lookups)
_turn = {"prompt": "", "words": "", "follows": "", "named": "", "at": 0.0}


def set_turn_follow_up(prompt: str, words: str = "", follows: str = "") -> None:
    """Notes this turn's follow-up words and the question it follows (or that it isn't one) for the lookups it runs
    (`turn_follow_up`, `turn_follows`). One turn at a time: MIA answers one message at a time per device, and a stale
    note runs out after TURN_SECONDS."""
    _turn.update(prompt=str(prompt or "").strip() if words else "", words=words or "", follows=follows or "",
                 named="", at=time.monotonic())


def note_follow_up_tool(name: str) -> None:
    """Notes the tool a follow-up was settled on from the question it follows (core/assistant_chat.named_tool)."""
    _turn["named"] = name or ""


def follow_up_tool() -> str:
    """The tool this turn's follow-up was settled on from its question (`note_follow_up_tool`), or ""."""
    if not _turn["words"] or time.monotonic() - _turn["at"] > TURN_SECONDS:
        return ""
    return _turn["named"]


def turn_follows(prompt: str) -> str:
    """The question this turn's message follows, when `prompt` is the follow-up being answered now; else ""."""
    if not _turn["words"] or time.monotonic() - _turn["at"] > TURN_SECONDS:
        return ""
    return _turn["follows"] if _turn["prompt"] == str(prompt or "").strip() else ""


def turn_follow_up() -> Optional[tuple]:
    """(the follow-up's own words, the question a tool should be given) for the turn now running, or None."""
    if not _turn["words"] or time.monotonic() - _turn["at"] > TURN_SECONDS:
        return None
    return _turn["prompt"], _turn["words"]


def follows_a_tool(context, conversation, prompt: str) -> Optional[str]:
    """The tool question a short follow-up leans on, when no question plan is in progress in this conversation (a plan's
    own follow-ups go back to it: `follow_up`): then the follow-up is the model's, with that question's tools, never a
    plan its words happen to match ("what about today?" after "is it too cold to work outside tomorrow?" isn't the
    day's agenda; live check through run_assistant_turn, 2026-11-24). None otherwise."""
    if not looks_like_follow_up(prompt) or follow_up(conversation, prompt) is not None:
        return None
    return followed_question(context, conversation, prompt)


def follow_up_question(prompt: str, follows: str) -> str:
    """Pure logic. The question a tool is given for a follow-up: the new words first, then the question they follow
    ("And what about corn? (after: How long do I process quarts of green beans?)"), so a tool reading the first food
    or weight reads the new one (the live check, 2026-11-24: given only the turn, the model passed the tool's own
    description and the new detail was lost)."""
    return f"{prompt.strip()} (after: {follows.strip()})"


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
