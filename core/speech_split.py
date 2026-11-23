"""
core.speech_split
===================

Her first words sooner (Jarvis brainstorm 1.1(c); Zac, 2026-11-23: "smooth conversation"). Her answer can't be spoken
while the model is still writing it: every answer is checked whole first (invented figures, the canning floor, the
emergency floor, the response composer), and those checks stay. What can be quicker is the voice: instead of making
the whole answer's audio before any plays, the server makes only the first part's (`first_part`), and the page voices
the rest a part at a time while the first plays (web/shell.js `playReply`, through /api/heavy/speak).

`first_part(text)` is the opening sentence, or the first two when the first is very short ("Sure." would be a blip),
never cut mid-sentence; the rest is everything after it, "" when the whole answer is short enough to say at once.
Only a page that asks for it gets the split (`/api/voice/turn?split=1`); the phone app and the glasses get the whole
audio as before.
"""

from __future__ import annotations

import re

SHORT_ENOUGH = 220  # an answer this long or less is said in one go
FIRST_AT_LEAST = 40  # a first sentence shorter than this takes the next one with it
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def sentences(text: str) -> list[str]:
    """Pure logic. The text's sentences, in order (a decimal or "e.g." mid-sentence isn't an end: an end is followed by
    a space and a capital, digit or quote)."""
    return [s.strip() for s in _SENTENCE_END.split(" ".join(str(text or "").split())) if s.strip()]


def first_part(text: str) -> tuple[str, str]:
    """Pure logic. (what to say first, the rest): the whole text and "" when it's SHORT_ENOUGH or one sentence."""
    text = " ".join(str(text or "").split())
    parts = sentences(text)
    if len(text) <= SHORT_ENOUGH or len(parts) < 2:
        return text, ""
    first = parts[0]
    taken = 1
    while len(first) < FIRST_AT_LEAST and taken < len(parts) - 1:
        first = f"{first} {parts[taken]}"
        taken += 1
    return first, " ".join(parts[taken:])
