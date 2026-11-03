"""
core.response_composer
========================

How much MIA says, and how, on the device she's speaking through
(DEC-0067; P2 of docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md). One identity,
three surfaces:

- **glasses**: one or two spoken sentences, about 20 words (5 to 8
  seconds), what matters first.
- **phone**: shown whole, like the PC; its length comes from the prompt.
- **pc**: the full answer.

The whole answer always stays in the conversation, where the phone and the
PC show it. The glasses get a version *composed* for speaking, not a cut-off
one: tidied first (no markdown, lists, filler openings or "let me know"
closings), and when it's still too long, rewritten for speech by the model
in one short call. That rewrite must keep only numbers the answer had, so
being short never costs her grounding; when the model can't, the answer's
own first sentences are used, never a sentence cut in half. Her own opening
sentences come first whenever they fit: the model only rewrites an opening
too long to speak (tried the other way round, the rewrites lost her warmth
and once added a fact; pc-check, 2026-11-03).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

GLASSES, PHONE, PC = "glasses", "phone", "pc"
SURFACES = (GLASSES, PHONE, PC)

# Words, roughly: 2.5 a second spoken. None: no limit.
BUDGET = {GLASSES: 25, PHONE: None, PC: None}  # the phone and PC show it whole; their length comes from the prompt
REWRITE_SECONDS = 6.0  # a glasses answer can't wait longer than this for its spoken version
REWRITE_LIMIT = 40  # a rewrite longer than this missed the point; use the answer's own sentences

FILLER = re.compile(r"^(certainly|sure thing|sure|of course|absolutely|great question|i'?d be happy to help)[!,.:]*\s+", re.I)
OFFER = re.compile(r"\s*(?:[^.?!]*\b(?:let me know|anything else|feel free|is there anything)\b[^.?!]*[.?!]?)\s*$", re.I)
LIST_MARK = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.M)
SENTENCE = re.compile(r".+?(?:[.!?](?=\s|$)|$)\s*", re.S)
NUMBER = re.compile(r"\d[\d,.:]*")

REWRITE_PROMPT = (
    "You're MIA, speaking through someone's glasses. Say the answer below out loud to them in one or two short "
    "sentences, at most {budget} words, the most important thing first. Use only what the answer says: add no "
    "fact, reason or number of your own, and leave the details for their phone. Keep its warmth and any joke. "
    "No filler, no 'let me know', no announcing what you're doing. Reply with only what you'd say.\n\nThe answer:\n{answer}"
)


@dataclass
class Composed:
    say: str  # what she says or shows on this surface
    full: str  # the whole answer, kept in the conversation


def words(text: str) -> int:
    return len((text or "").split())


def tidy(text: str) -> str:
    """Pure logic. The answer as speech: no markdown, list marks or line
    breaks, no filler opening, no closing offer of more help."""
    text = re.sub(r"\*\*|__|`", "", text or "")
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = LIST_MARK.sub("", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = " ".join(line if line[-1] in ".!?:" else line + "." for line in lines)
    text = FILLER.sub("", text).strip()
    kept = OFFER.sub("", text).strip()
    return kept or text


def first_sentences(text: str, budget: int) -> str:
    """Pure logic. The answer's own opening sentences, whole, within `budget`
    words. At least one sentence, even a long one: never half of one."""
    kept = []
    for sentence in SENTENCE.findall(text):
        if kept and words(" ".join(kept + [sentence])) > budget:
            break
        kept.append(sentence.strip())
    return " ".join(kept).strip()


def grounded(said: str, answer: str) -> bool:
    """Pure logic. Every number in `said` is one the answer had."""
    have = {n.strip(".,:") for n in NUMBER.findall(answer)}
    return all(n.strip(".,:") in have for n in NUMBER.findall(said))


def compose(context, answer: str, surface: str = PC) -> Composed:
    """`answer` for `surface`. Never raises: at worst the tidied answer."""
    full = answer or ""
    budget = BUDGET.get(surface)
    if budget is None:
        return Composed(say=full, full=full)
    spoken = tidy(full)
    if words(spoken) <= budget:
        return Composed(say=spoken, full=full)
    # Her own opening, when it fits: her words, her warmth, her joke, and no
    # risk of a fact she didn't say. The model rewrites only an opening too
    # long to speak.
    opening = first_sentences(spoken, budget)
    if words(opening) <= budget or surface != GLASSES:
        return Composed(say=opening, full=full)
    rewritten = _rewrite(context, spoken, budget)
    return Composed(say=rewritten or opening, full=full)


def _rewrite(context, spoken: str, budget: int) -> Optional[str]:
    """The model's spoken version, or None when it's slow, long or adds a number."""
    llm = getattr(context, "llm", None)
    if llm is None:
        return None
    try:
        said = llm.generate(REWRITE_PROMPT.format(budget=budget, answer=spoken), timeout=REWRITE_SECONDS)
    except Exception:  # never let composing break an answer
        log.exception("Composing a spoken answer failed")
        return None
    said = tidy((said or "").strip().strip('"'))
    if not said or words(said) > REWRITE_LIMIT or not grounded(said, spoken):
        return None
    return said
