"""
core.response_composer
========================

How much MIA says, and how, on the device she's speaking through
(DEC-0067; P2 of docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md). One identity,
three surfaces:

- **glasses**: one or two spoken sentences, about 20 words (5 to 8
  seconds), what matters first.
- **phone**: shown whole, only without a filler opening or a closing
  offer of more help, which the model adds however it's asked not to.
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

On every surface, a paragraph or sentence the model said twice is said once (`without_repeats`), and the model's
"the fact sheet" (her own working) is never said aloud (`without_sheet_words`, applied to the model's words only).
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

# never the word that carries the answer: "Absolutely not. That wire is live." keeps its "Absolutely not" (the Fable
# review, 2026-11-25)
FILLER = re.compile(r"^(certainly|sure thing|sure|of course|absolutely|great question|i'?d be happy to help)(?! not\b)"
                    r"[!,.:]*\s+", re.I)
# A last sentence that only invites more talk, which a model adds by habit. An offer to do something ("Want me
# to open it?") isn't one: a "yes" to that acts (core/conversation_state.py), so it's never in this list.
_INVITES = (r"let me know|anything else|feel free|is there anything|just ask|"
            r"(?:would you like|do you want|want|care) to (?:know|hear|learn) more|"
            r"would you like (?:more|further|additional) (?:details?|information|info)|"
            r"if you have (?:any |more |other |further |specific )*questions")
OFFER = re.compile(r"\s*(?:[^.?!]*\b(?:" + _INVITES + r")\b[^.?!]*[.?!]?)\s*$", re.I)
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
    """An answer fitted to a surface: what she says or shows there, and the whole answer kept in the conversation."""
    say: str  # what she says or shows on this surface
    full: str  # the whole answer, kept in the conversation


def words(text: str) -> int:
    """Pure logic. How many words a text has."""
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


OFFERING = re.compile(r"\b(?:" + _INVITES + r")\b", re.I)


def without_repeats(text: str) -> str:
    """Pure logic. The answer with a paragraph or sentence said again right after itself dropped (the live sweep,
    2026-11-25: the model said "The project you're planning: goats..." five times over). Short ones ("Yes."), list
    lines, a repeat later on (a refrain, a recipe's second heading) and anything with code stay."""
    if "```" in str(text or "") or re.search(r"^(?: {4}|\t)\S", str(text or ""), re.M):
        return text  # code is never touched: a line repeated in code is meant (the Fable review, 2026-11-25)

    def norm(said):
        """Its words and signs, lowercased, so "2 + 2 = 4" and "2 * 2 = 4" stay two."""
        return " ".join(str(said).lower().split())

    # only a repeat back to back, of something long enough to be a sentence: a refrain, a recipe's second
    # "Ingredients:", a step said again later and a short "Yes." are meant (the Fable review)
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text or ""):
        key = norm(paragraph)
        if paragraphs and len(key) >= 20 and key == norm(paragraphs[-1]):
            continue
        if "\n" in paragraph or re.match(r"\s*(?:[-*\u2022]|\d+[.)])\s", paragraph):
            paragraphs.append(paragraph)  # a list's lines stay as they are
            continue
        kept = []
        for sentence in SENTENCE.findall(paragraph) or [paragraph]:
            kept.append(sentence)
            for k in range(1, len(kept) // 2 + 1):  # a sentence or a run of them said again right after itself
                block = norm(" ".join(kept[-k:]))
                long_one = max(len(norm(s)) for s in kept[-k:]) >= 20  # never "One. One." or "Yes. Yes."
                if long_one and block == norm(" ".join(kept[-2 * k:-k])):
                    del kept[-k:]
                    break
        paragraphs.append("".join(kept).strip())
    return "\n\n".join(p for p in paragraphs if p.strip())


_LIST_MARK = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s")


def _sheet_rewrites(text: str) -> str:
    """Pure logic. "The fact sheet says/doesn't mention/...", "the sheet itself shows" said as his records ("your
    records show", its capital kept), outside quoted words; a sheet of plywood or a cookie sheet stays."""
    def fix(part: str) -> str:
        """One stretch outside quotes."""
        part = re.sub(r"\b(?:the |my )?fact sheet (?:says|shows|lists|suggests) (?:to |that )?(\w)",
                      lambda m: m.group(1).upper(), part, flags=re.I)  # the sentence starts where the words were
        part = re.sub(r"\b(?:the |my )?fact sheet (?:doesn'?t|does not) (?:mention|say|show|have|include|list)\b",
                      "I don't have", part, flags=re.I)
        part = re.sub(r"\b(?:on|in|from) the fact sheet\b", "in your records", part, flags=re.I)
        part = re.sub(r"\bthe fact sheet\b", "your records", part, flags=re.I)
        # "the sheet itself shows", "the sheet says" (the skills sweep, 2026-11-26), said with "your records" and its
        # verb made plural, the sentence's capital kept; a sheet of plywood, a cookie sheet or "on the sheet" stays
        plural = {"says": "say", "shows": "show", "lists": "list", "suggests": "suggest"}

        def records(m):
            """"The sheet itself shows" as "Your records show", its first letter's case kept."""
            lead = m.group(1)[:-3]  # "What " kept, or nothing
            said = lead + "your records " + plural[m.group(2).lower()]
            return said[:1].upper() + said[1:] if m.group(1)[:1].isupper() else said
        return re.sub(r"\b((?:what )?the) sheet(?: itself)? (says|shows|lists|suggests)\b", records, part, flags=re.I)

    pieces = re.split(r'("[^"\n]*"|\u201c[^\u201d\n]*\u201d)', text)
    return "".join(piece if i % 2 else fix(piece) for i, piece in enumerate(pieces))


def without_sheet_words(said: str) -> str:
    """Pure logic. The model's answer without her own working said aloud ("the fact sheet says", "the fact sheet
    doesn't mention": the live sweep, 2026-11-26): a sheet she was given is his records to him. Only "fact sheet"
    itself, so a balance sheet, a cookie sheet and the rest of the sentence stay as written (the Fable review). A
    sentence still saying one ("You mentioned a fact sheet, but ...": brainstorm round 19's live check) goes when the
    answer has anything else; never inside quotes, a code block or a list's item (the Fable review: "print the OSHA
    fact sheet" in his note stays). For the model's words only (core/assistant_turn, core/question_plans), never a
    code answer's."""
    out, fenced = [], False
    for line in (said or "").split("\n"):
        if line.strip().startswith("```"):
            fenced = not fenced
            out.append(line)
            continue
        if fenced:
            out.append(line)
            continue
        line = _sheet_rewrites(line)
        if re.search(r"\bfact sheets?\b", line, re.I) and not _LIST_MARK.match(line) and '"' not in line:
            kept = "".join(s for s in SENTENCE.findall(line) if not re.search(r"\bfact sheets?\b", s, re.I)).rstrip()
            if kept or len([x for x in said.split("\n") if x.strip()]) > 1:
                line = kept
        out.append(line)
    result = "\n".join(out).strip()
    return result or said


def polish(text: str, prompt: str = "") -> str:
    """Pure logic. The whole answer, for a screen: only the filler opening,
    a last sentence that offers more help, and a humor example's line copied
    word for word (core/personality.without_copied_example), or loosely when
    his words (`prompt`) are given, go. Lists, markdown and length stay.
    A paragraph or sentence said twice is said once (`without_repeats`), and his request said back as her opening
    ("I want to learn about tying a bowline.") goes.
    "I don't know what that means." before a real answer goes, and so does the model writing out its own lookup
    ('Tool call: "..." Response: "..."': only the answer stays). "The fact sheet" said aloud never stays
    (`without_sheet_words`, for the model's words: core/assistant_turn)."""
    from core.personality import without_copied_example

    text = without_copied_example((text or "").strip(), prompt)  # never a humor example's line said as hers
    text = without_repeats(text) or text  # never the same paragraph or sentence twice
    # 'Tool call: "What is the best goat for milk?"  Response: "The best..."' (the live sweep, 2026-11-26): the model
    # wrote out its own lookup; only the answer stays
    framed = re.match(r'^\s*(?:tool call|function call)\s*:\s*(?:"[^"\n]*"\s*|[^\n]*\n\s*)(?:\n\s*)*response\s*:\s*(.+)$',
                      text, re.I | re.S)
    if framed and framed.group(1).strip():
        text = framed.group(1).strip()
        if len(text) > 1 and text[0] == '"' and text.rstrip()[-1] == '"':
            text = text.strip()[1:-1].strip()
    # "Honestly, I don't know what that means. But ..." before a real answer (the live sweep): the answer stays
    text = re.sub(r"^\s*(?:honestly,?\s+)?i (?:don't|do not) (?:know|understand) what (?:that|you) means?\.\s*"
                  r"(?:but\s+)?(?=\S.{40,})", "", text, flags=re.I | re.S) or text
    text = text[:1].upper() + text[1:]
    if re.match(r"\s*(?:teach|tell|show|explain|help)\b", prompt or "", re.I):
        # "Teach me how to tie a bowline" answered "I want to learn about tying a bowline." first (the live sweep)
        text = re.sub(r"^\s*I(?:'d like| want| would like) to (?:learn|know|understand)\b[^.!?\n]*[.!?]\s*", "", text) \
            or text
    trimmed = FILLER.sub("", text).strip() or text
    trimmed = trimmed[:1].upper() + trimmed[1:]
    lines = trimmed.split("\n")
    sentences = SENTENCE.findall(lines[-1])
    if sentences and OFFERING.search(sentences[-1]):
        lines[-1] = "".join(sentences[:-1]).rstrip()
        if not lines[-1]:
            lines.pop()
    kept = "\n".join(lines).strip()
    return kept or trimmed


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
    if surface == PHONE:
        return Composed(say=polish(full), full=full)
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
