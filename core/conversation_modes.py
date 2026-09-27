"""
core.conversation_modes
==========================

How MIA should talk right now — slice A ("Talk it out") of
docs/COGNITIVE_EXTENSION_PROPOSAL.md. Pure logic: the mode vocabulary,
the explicit phrases that switch modes, and the one short tone line
each mode adds to the system prompt.

**Explicit, not inferred.** A mode changes only when the user says so
("just listen", "no bullshit", "hype me up", "help me figure out what
to do", "I want to journal"), exactly like teaching mode's trigger
phrases in core/assistant_chat.py. Guessing a mode from tone is a
later, separate step (see the proposal's question 9), and only if the
explicit version proves itself on the real model.

Six modes instead of the source document's twelve: a 3B model can't
reliably hold twelve subtly different personalities apart, and prompt
length has regressed this model before (docs/ROADMAP.md). Humor,
celebration and decompression are tone flavors inside these, not
modes of their own. Crisis is not a mode at all: it's
core/safety_floor.py, which runs before any mode.

Two flags sit beside the mode:
- **journal**: this conversation is being journaled into the
  encrypted private journal (core/private_journal.py). Starting a
  journal also switches to Listen, since journaling is talking, not
  being fixed.
- **off_record**: nothing from here on is saved: not to the journal,
  not to memories, not to conversations.json.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

COMPANION = "companion"
LISTEN = "listen"
DIRECT = "direct"
MOMENTUM = "momentum"
PLAN = "plan"
# Slice B, "Remember Why": answers only from core/why_graph.py's fact sheet.
PERSPECTIVE = "perspective"

MODES = (COMPANION, LISTEN, DIRECT, MOMENTUM, PLAN, PERSPECTIVE)
# Modes where MIA is there for the person, not the records: the reply
# skips help-doc grounding, and tools are offered only for a message
# that reads as a direct command (see looks_like_direct_command()).
PERSONAL_MODES = (LISTEN, DIRECT, MOMENTUM, PLAN, PERSPECTIVE)

MODE_LABELS = {
    COMPANION: "Normal",
    LISTEN: "Just listening",
    DIRECT: "Straight talk",
    MOMENTUM: "Hype",
    PLAN: "Figure it out",
    PERSPECTIVE: "Remember why",
}

# One sentence or two each, deliberately: every extra clause is prompt
# length a 3B model has to hold.
MODE_INSTRUCTIONS = {
    PERSPECTIVE: (
        "The user needs perspective on why they're doing what they're doing. Using ONLY the facts below, "
        "connect what they're doing today to what it's building toward, following their own reasons in order. "
        "Name one or two real numbers or wins from the facts. Never invent a number, a goal or a reason. If a "
        "reason is marked DONE, tell them honestly that it used to be a reason and it's complete now. It's fine "
        "that today is hard; don't tell them how to feel. Five sentences at most."
    ),
    LISTEN: (
        "Right now the user wants to be heard, not fixed. Reflect back what they said and how it seems to "
        "feel, in two or three sentences, and ask at most one gentle question. No advice, no lists, no to-dos "
        "unless they ask for them."
    ),
    DIRECT: (
        "The user asked for straight talk. Be direct and honest, skip the cushioning and the pep, and keep it "
        "short. Honest, not harsh."
    ),
    MOMENTUM: (
        "The user wants energy to get through the next stretch. Be upbeat and brief and focus on getting "
        "through the next hour, not the big picture. A little humor is welcome."
    ),
    PLAN: (
        "The user feels stuck or overwhelmed. Help make it smaller: name what matters most right now and "
        "suggest one concrete next step. Offer, don't order."
    ),
}

# Always added on the personal path: the human-agency principle
# (docs/COGNITIVE_EXTENSION.md section 14) in one line.
AGENCY_LINE = (
    "You help the user think; you never decide for them. Suggest, remind and reflect, and leave every "
    "decision to them."
)


def _phrases(*patterns: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(patterns) + r")\b")


# "just listen" but not "just listen to this song": allowed only when
# followed by nothing, punctuation, or "to me".
_LISTEN = _phrases(
    r"just listen(?!\s+to\s+(?!me\b))",
    r"(?:i\s+)?(?:just\s+)?need to vent",
    r"can i vent",
    r"let me vent",
    r"i just need someone to listen",
    r"don'?t (?:try to )?fix (?:it|this|anything)",
    r"just hear me out",
)
_DIRECT = _phrases(
    r"no bullshit",
    r"no bs",
    r"(?:the |a )?hard truth",
    r"be straight with me",
    r"give it to me straight",
    r"don'?t sugar ?coat(?: it)?",
    r"brutal(?:ly)? honest(?:y)?",
    r"be honest with me",
)
_MOMENTUM = _phrases(
    r"hype me up",
    r"pump me up",
    r"motivate me",
    r"(?:i need a |give me a )?pep talk",
    r"get me through (?:this|today|the day|the shift|this shift)",
)
_PLAN = _phrases(
    r"help me figure (?:out )?what to do",
    r"help me figure (?:this|it) out",
    r"i don'?t know what to do",
    r"i'?m (?:so )?overwhelmed",
    r"i am (?:so )?overwhelmed",
    r"make (?:this|it) smaller",
    r"where do i (?:even )?start",
)
_PERSPECTIVE = _phrases(
    r"remind me why",
    r"why am i (?:even )?doing (?:this|all this|any of this)",
    r"why do i (?:even )?bother",
    r"what'?s the point(?:\s+of (?:this|it|all this|any of this))?(?=\s*(?:[?.!,]|$))",
    r"what am i (?:even )?(?:working|doing (?:all )?this) (?:toward|towards|for)",
    r"i'?m (?:feeling |so )?(?:dragged|dragging) down",
    r"zoom (?:me )?out",
    r"what is all this for",
)
_JOURNAL = _phrases(
    r"i (?:want|need|'?d like) to journal",
    r"let'?s journal",
    r"journal (?:time|session)",
    r"start (?:a|my) journal entry",
    r"dear diary",
    r"journal this",
)
_OFF_RECORD = _phrases(
    r"off the record",
    r"don'?t (?:remember|save|journal|record) (?:this|that|any of this)",
    r"this stays between us",
    r"keep this between us",
)
_BACK_TO_NORMAL = _phrases(
    r"back to normal",
    r"normal mode",
    r"(?:we'?re |i'?m )?done journal(?:ing)?",
    r"end (?:the |my )?journal(?: entry| session)?",
    r"back on the record",
    r"on the record again",
)


@dataclass
class ModeChange:
    mode: Optional[str] = None  # new mode, or None to keep the current one
    journal: Optional[bool] = None  # True start, False stop, None unchanged
    off_record: Optional[bool] = None

    @property
    def is_empty(self) -> bool:
        return self.mode is None and self.journal is None and self.off_record is None


def detect_mode_change(prompt: str) -> ModeChange:
    """Pure logic. Which explicit mode/journal/record switches `prompt` contains.

    "Back to normal" wins over everything else in the same message
    (it's the way out, and must always work). Otherwise a journal start
    implies Listen unless another mode was also named ("I want to
    journal, no bullshit").
    """
    text = prompt.lower().replace("’", "'")
    change = ModeChange()

    if _BACK_TO_NORMAL.search(text):
        return ModeChange(mode=COMPANION, journal=False, off_record=False)

    # Perspective first: "no bullshit, remind me why" needs the facts more than a tone.
    for pattern, mode in ((_PERSPECTIVE, PERSPECTIVE), (_DIRECT, DIRECT), (_MOMENTUM, MOMENTUM), (_PLAN, PLAN), (_LISTEN, LISTEN)):
        if pattern.search(text):
            change.mode = mode
            break
    if _JOURNAL.search(text):
        change.journal = True
        if change.mode is None:
            change.mode = LISTEN
    if _OFF_RECORD.search(text):
        change.off_record = True
    return change


# Messages in a personal mode are mostly about feelings, and they
# mention the user's things constantly ("the truck broke down again and
# I'm done"). Offering record-editing tools for those would invite the
# model to "fix" a vent by logging maintenance. So in a personal mode,
# tools are only offered when the message starts like a command.
_COMMAND_START = re.compile(
    r"^(?:(?:hey |ok |okay )?mia[,:]?\s+)?(?:please\s+)?"
    r"(?:add|log|remind(?! me (?:why|what i))|set|mark|put|record|delete|remove|open|play|pause|stop|resume|check off|"
    r"start tracking|track|create|schedule|update|what'?s on|what is on|how much|list)\b"
)


def looks_like_direct_command(prompt: str) -> bool:
    return bool(_COMMAND_START.search(prompt.lower().strip()))
