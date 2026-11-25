"""
core.claim_check
==================

Never "I've added a reminder" when nothing was added (live sweep, 2026-11-25: "remind me to check the oil Saturday"
was offered only the alarms, called no tool, and the model answered "You've been reminded ... I'll send a
notification to your device at the scheduled time"). A reply of the model's that reaches the person with no tool run
that changes anything (core/assistant_turn.py: the tool loop only looks things up) and says it did something, or will
send something, isn't true; it's replaced with what is (`honest`): nothing was set up, and how to say it so it can be.
Each one is kept in the Fix-It Log (`claimed_done`), where it becomes a capability gap.

`claims_done(text)` (pure): first person, a change done ("I've added", "I set", "I've scheduled", "is set for
Saturday", "you've been reminded", "I'll send a notification"); never an offer ("I can add it", "want me to set
one?", "if you'd like, I'll add"), a question back, or someone else's doing ("you added").
"""

from __future__ import annotations

import re

_DONE = re.compile(
    r"\b(?:i(?:'ve| have)?|i just|i've just)\s+(?:gone ahead and\s+)?(?:added|set(?: up)?|scheduled|created|saved|logged|"
    r"recorded|deleted|removed|updated|booked|sent|put (?:it|that|this|them|a reminder|an? \w+) (?:on|in|into)|reminded|marked|cancell?ed|moved|changed|turned (?:on|off))\b"
    r"|\byou(?:'ve| have) been reminded\b"
    r"|\b(?:reminder|alarm|event|task|appointment|note)\s+(?:is|has been|was|'s)\s+(?:now\s+)?(?:set|added|scheduled|"
    r"created|saved|booked)\b"
    r"|\bi(?:'ll| will)\s+(?:send|remind|notify|ping|alert)\s+(?:you|a notification)\b", re.I)
# Offers and questions, which claim nothing: "I can add it", "want me to set one?", "if you'd like, I'll add it"
_OFFER = re.compile(r"\b(?:i can|i could|want me to|would you like|shall i|should i|if you(?:'d| would) like|"
                    r"just say|say the word|let me know if)\b", re.I)

HONEST = ("I didn't set that up: I couldn't do it from what you said, so nothing was added. Say it with what it is and "
          "when, like \"add check the oil to my calendar on Saturday\", and I'll put it there.")


_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
# He asked for something done: "remind me...", "add...", "can you put...", "please set..."
_ASKED = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+|can you\s+|could you\s+|would you\s+|i need you to\s+)?"
                    r"(?:remind|add|put|set|schedule|create|make|log|record|save|delete|remove|cancel|move|book|send|"
                    r"mark|note|write down|track|start|turn|change|update)\b", re.I)


def _claiming(sentence: str) -> bool:
    """Pure logic. Whether one sentence says it did something, and isn't an offer or a question."""
    return bool(_DONE.search(sentence)) and not _OFFER.search(sentence) and not sentence.strip().endswith("?")


def claims_done(text: str) -> bool:
    """Pure logic. Whether a reply says it did something (see the module's opening), in a sentence that isn't an
    offer or a question."""
    return any(_claiming(s) for s in _SENTENCES.split(str(text or "")))


def honest(context, prompt: str, text: str) -> str:
    """The reply as it should be said: the model's own when it claims nothing; when he asked for something done,
    HONEST; else the reply without its claiming sentences ("how are you?" answered, then "I'll remind you when
    they're due" with no reminder set), or HONEST when nothing would be left. The claim is kept in the Fix-It Log as
    `claimed_done` (never failing the turn)."""
    if not claims_done(text):
        return text
    kept = [s for s in _SENTENCES.split(str(text or "")) if s.strip() and not _claiming(s)]
    said = HONEST if _ASKED.search(prompt or "") or not kept else " ".join(kept)
    book = getattr(context, "failures", None)
    if book is not None:
        try:
            book.record("claimed_done", prompt=prompt, reply=text)
        except Exception:  # noqa: BLE001 - the log is a record of it, never a reason to fail the answer
            pass
    return said
