"""
core.claim_check
==================

Never "I've added a reminder" when nothing was added (live sweep, 2026-11-25: "remind me to check the oil Saturday"
was offered only the alarms, called no tool, and the model answered "You've been reminded ... I'll send a
notification to your device at the scheduled time"). A reply of the model's that reaches the person with no tool run
that changes anything (core/assistant_turn.py: the tool loop only looks things up) and says it did something, or will
send something, isn't true; it's replaced with what is (`honest`): nothing was set up, and how to say it so it can be.
Each one is kept in the Fix-It Log (`claimed_done`), where it becomes a capability gap.

`claims_done(text)` (pure): first person, a change done to one of his records ("I've added a reminder", "I set an
alarm", "I'll send a notification"), or, when he asked for a change, "it's set" ("your reminder is set for Saturday",
"you've been reminded"); never an offer ("I can add it", "want me to set one?"), a question back, someone else's
doing ("you added"), or a sentence about anything but his records ("in my example, I set the temperature").
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
# A first-person claim counts only when it names one of his records (the seventh review: "in my example, I set the
# temperature to 350", "I set sail at dawn", "I changed my mind" claim nothing of his)
_RECORD = re.compile(r"\b(?:reminders?|alarms?|timers?|events?|calendar|appointments?|tasks?|to-?dos?|lists?|notes?|"
                     r"notifications?|missions?|entr(?:y|ies)|logs?|budget|routines?|orders?|invoices?|"
                     r"schedule|recurring)\b", re.I)
# The "it's set" forms ("your alarm is set for 6:30") also say what a lookup found, so they count only when he asked
# for a change (a lookup's "Your alarm is set for 6:30 tomorrow" stays)
_PASSIVE = re.compile(r"\byou(?:'ve| have) been reminded\b|\b(?:reminder|alarm|event|task|appointment|note)\s+(?:is|has "
                      r"been|was|'s)\s+(?:now\s+)?(?:set|added|scheduled|created|saved|booked)\b", re.I)
# A promise to remind or notify him is a claim by itself (nothing would remind him): "I'll remind you when it's due"
_PROMISE = re.compile(r"\bi(?:'ll| will)\s+(?:send|remind|notify|ping|alert)\s+(?:you|a notification)\b", re.I)
# Offers and questions, which claim nothing: "I can add it", "want me to set one?", "if you'd like, I'll add it"
_OFFER = re.compile(r"\b(?:i can|i could|want me to|would you like|shall i|should i|if you(?:'d| would) like|"
                    r"just say|say the word|let me know if)\b", re.I)

HONEST = ("I didn't set that up: I couldn't do it from what you said, so nothing was added. Say it with what it is and "
          "when, like \"add check the oil to my calendar on Saturday\", and I'll put it there.")


_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
# He asked for something done: "remind me...", "add...", "can you put...", "please set..."
_ASKED = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+|can you\s+|could you\s+|would you\s+|i need you to\s+)?"
                    r"(?:remind|add|put|schedule|log|record|delete|remove|cancel|move|book|mark|"
                    r"set (?:an? |the |my )?(?:alarm|timer|reminder))\b", re.I)  # a record asked for, not a story


def _claiming(sentence: str, asked: bool = True) -> bool:
    """Pure logic. Whether one sentence says it did something to one of his records (`_RECORD`), and isn't an offer
    or a question, or promises to remind or notify him (`_PROMISE`); the "it's set" forms only when he asked for a
    change (`asked`)."""
    if _OFFER.search(sentence) or sentence.strip().endswith("?"):
        return False
    first_person = bool(_DONE.search(sentence)) and not _PASSIVE.search(sentence) and bool(_RECORD.search(sentence))
    return first_person or bool(_PROMISE.search(sentence)) or (asked and bool(_PASSIVE.search(sentence)))


def claims_done(text: str, asked: bool = True) -> bool:
    """Pure logic. Whether a reply says it did something (see the module's opening), in a sentence that isn't an
    offer or a question (`_claiming`)."""
    return any(_claiming(s, asked) for s in _SENTENCES.split(str(text or "")))


def honest(context, prompt: str, text: str, keep: bool = True) -> str:
    """The reply as it should be said: the model's own when it claims nothing; when he asked for something done,
    HONEST; else the reply without its claiming sentences ("how are you?" answered, then "I'll remind you when
    they're due" with no reminder set), or HONEST when nothing would be left. The claim is kept in the Fix-It Log as
    `claimed_done` (never failing the turn), unless `keep` is False (a personal, journal or off-the-record turn: the
    seventh review)."""
    asked = bool(_ASKED.search(prompt or ""))
    if not claims_done(text, asked):
        return text
    kept = [s for s in _SENTENCES.split(str(text or "")) if s.strip() and not _claiming(s, asked)]
    said = HONEST if asked or not kept else " ".join(kept)
    book = getattr(context, "failures", None) if keep else None
    if book is not None:
        try:
            book.record("claimed_done", prompt=prompt, reply=text)
        except Exception:  # noqa: BLE001 - the log is a record of it, never a reason to fail the answer
            pass
    return said
