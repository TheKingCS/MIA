"""
core.personality
==================

MIA's voice in code (DEC-0029, ALICE pick 7; the guide is
docs/design/MIA_VOICE.md). The words MIA writes on her own (the
Chronicle, buffs, MIA Remembers, the crafting results, notes through the
communication gate) are checked against the one rule code can check:
never guilt (DEC-0014).
"""

from __future__ import annotations

import re

GUILT_WORDS = ("failed", "failure", "you missed", "behind", "lazy", "should have", "shame", "disappointing",
               "broke your streak", "lost your streak", "wasted")
_GUILT = re.compile(r"\b(" + "|".join(re.escape(w) for w in GUILT_WORDS) + r")\b", re.IGNORECASE)


def guilt_in(text: str) -> list[str]:
    """Pure logic. The guilt words in `text` (empty when it's kind)."""
    return [m.group(1).lower() for m in _GUILT.finditer(text or "")]
