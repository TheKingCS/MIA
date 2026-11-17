"""
core.message_kind
===================

Intent before action, first step (T-0009; `docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md` A7 P3): sorting what someone
said into the kind of message it is, in code, before any path is chosen: a command, a question, chat, humor,
frustration, a feeling, a plan, a follow-up, a request for advice, a hypothetical, or an observation.

**Watching only, for now.** `sort` is recorded with each turn (`core/turn_trace.py`, `kind`), so the traces and the
golden conversation corpus (`data/conversation_cases.json`, each case labelled with its kind) can measure it
(`accuracy`) before it's allowed to steer anything. The routing (the action path, the info path, the personal modes)
doesn't change. When it's measured good enough, it feeds that split instead of keyword lists alone.

**How:** ordered rules over the words (`RULES`): the first that matches wins, so the narrow kinds (a follow-up, a
hypothetical, a command's opening verb) come before the broad ones (any question, chat). Pure logic.
"""

from __future__ import annotations

import re
from typing import Optional

KINDS = ("command", "follow-up", "hypothetical", "feeling", "frustration", "humor", "advice", "plan", "question",
         "observation", "chat")

_COMMAND_VERBS = ("add", "remind", "open", "set", "turn", "start", "stop", "log", "create", "delete", "remove", "show",
                  "play", "pause", "put", "mark", "schedule", "move", "rename", "save", "record", "note", "track",
                  "cancel", "undo", "write down", "text", "email", "draft", "find", "search", "look up", "check off")
_FEELINGS = ("i feel", "i'm feeling", "im feeling", "i am feeling", "i miss", "i'm struggling", "i've been struggling",
             "i'm scared", "i'm worried", "i'm anxious", "i'm sad", "i'm lonely", "i'm happy", "i'm excited",
             "i'm proud", "messed up", "good news", "bad news", "overwhelmed", "you're the only one",
             "not smart enough", "i'm tired of", "i feel guilty", "heartbroken", "i'm grateful")
_FRUSTRATION = ("ugh", "nothing is working", "nothing works", "jammed again", "broke again", "keeps breaking",
                "so annoying", "i'm sick of", "fed up", "i keep starting", "why won't", "won't work", "doesn't work",
                "again.")
_HUMOR = ("tell me something funny", "tell me a joke", "make me laugh", "joke", "lol", "haha", "one more",
          "better schedule than", "turn into a")
_ADVICE = ("any ideas", "what's one thing", "what is one thing", "any tips", "suggest", "recommend", "what would you do",
           "any advice", "what could i do")
_PLAN = ("help me think through", "help me plan", "where do i start", "what should i focus on", "i'm going to",
         "i am going to", "i'll just", "i want to", "i'm planning", "i plan to", "should i go all in", "could be bigger",
         "my plan is", "next step")
_HYPOTHETICAL = ("what if", "imagine", "suppose", "hypothetically", "let's say")
_FOLLOW = ("and ", "why", "how long", "what about", "then what", "and then", "how so", "really", "like what")
_GREETINGS = ("morning", "good morning", "hey", "hi", "hello", "i'm back", "you there", "evening", "good night", "night")
_QUESTION_STARTS = ("what", "how", "why", "when", "where", "who", "which", "is ", "are ", "do ", "does ", "did ",
                    "can ", "could ", "should ", "would ", "will ", "tell me about")


def _norm(text: str) -> str:
    """Pure logic. Lower case, curly quotes straightened, spaces collapsed."""
    return " ".join((text or "").lower().replace("’", "'").split())


def _has(said: str, phrases) -> bool:
    """Pure logic. Whether any phrase is in the words as whole words ("ugh" isn't in "through")."""
    for p in phrases:
        tail = "(?![a-z0-9])" if p[-1].isalnum() else ""
        if re.search(r"(?<![a-z0-9])" + re.escape(p) + tail, said):
            return True
    return False


def _starts_with_verb(said: str) -> bool:
    """Pure logic. Whether it opens with a command verb ("add eggs...", "please remind me...")."""
    said = re.sub(r"^(please|can you|could you|mia,?|hey mia,?)\s+", "", said)
    return any(said == v or said.startswith(v + " ") for v in _COMMAND_VERBS)


def sort(text: str, previous: Optional[str] = None) -> str:
    """Pure logic. The kind of message (one of KINDS). `previous` is her last reply, when there was one: a short
    question after it is a follow-up."""
    said = _norm(text)
    if not said:
        return "chat"
    words = said.rstrip("?!.").split()
    is_question = said.endswith("?") or said.startswith(_QUESTION_STARTS)
    if previous is not None and len(words) <= 6 and said.startswith(_FOLLOW):
        return "follow-up"
    if len(words) <= 6 and said.startswith(("and ", "why", "how long", "then what", "and then", "how so")):
        return "follow-up"
    if said.startswith(_HYPOTHETICAL):
        return "hypothetical"
    if not is_question and _starts_with_verb(said):
        return "command"
    if len(words) <= 4 and (said.rstrip("!.?") in _GREETINGS or said.startswith(_GREETINGS)):
        return "chat"
    if _has(said, _FEELINGS):
        return "feeling"
    if _has(said, _FRUSTRATION):
        return "frustration"
    if _has(said, _HUMOR):
        return "humor"
    if _has(said, _ADVICE):
        return "advice"
    if _has(said, _PLAN):
        return "plan"
    if is_question:
        return "question"
    if said.startswith(("it's been", "it is", "it was", "there's", "the weather")):
        return "observation"
    return "chat"


def accuracy(cases: list[dict]) -> dict:
    """Pure logic. How `sort` does on labelled cases ({say, kind}): {right, total, share, misses: [(say, kind,
    sorted)]}; a follow-up counts as agreeing with "question"."""
    def agrees(got: str, label: str) -> bool:
        """A follow-up is a kind of question."""
        return got == label or (got == "follow-up" and label == "question")

    misses = [(c["say"], c["kind"], sort(c["say"])) for c in cases if not agrees(sort(c["say"]), c["kind"])]
    total = len(cases)
    return {"right": total - len(misses), "total": total, "share": round((total - len(misses)) / total, 2) if total else 0.0,
            "misses": misses}
