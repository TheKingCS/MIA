"""
core.lesson_answer
====================

A how-to answered from one of MIA's own courses (live sweep, 2026-11-25: "what's the best way to start a fire in the
rain?" went to the project plan, "how do I purify water from a creek?" was answered from memory with brand names, and
"how do I sharpen a chisel?" was told her library had no packs, while her Survival and Woodworking courses teach
exactly those, from their sources). A question that asks how to do one of a few lessons' own subjects gets that
lesson: its steps, why it matters and what to watch for, from the course's sources (core/bushcraft.py,
core/woodworking.py, core/carpentry.py, core/gardening_path.py), with the drill to practise it when there is one.

- **Which lesson** (`ASKS`, `find`): each lesson here has its own question pattern, matched only in a how-to
  ("how do I", "what's the best way to", "how should I"): never a loose overlap of words ("how do I water the
  tomatoes?" is no water-purifying lesson), and never a when ("when should I start tomato seeds?" is the planting
  dates'). A lesson not listed is never guessed at.
- **The answer** (`reply`): taken in code before the question plans (core/assistant_turn.py), like the first-aid
  how-to, the steps his question is about first (`steps_for`: the mites step for "have mites?"); None for anything
  else.

Read only: nothing is kept, and his path isn't touched (a lesson he hasn't started is said as the course's, and how
to start it).
"""

from __future__ import annotations

import re
from typing import Optional

# (course, lesson): the words that ask how to do the lesson's own subject
ASKS: dict[tuple, re.Pattern] = {
    ("bushcraft", "fire"): re.compile(r"\b(?:start|make|light|build|get)\w*\s+(?:a\s+)?fire\b|\bfire\s+(?:in|when)\s+"
                                      r"(?:the\s+)?(?:rain|wet|snow|woods)\b|\bferro\s?rod\b|\btinder\b"),
    ("bushcraft", "water"): re.compile(r"\b(?:purify|treat|disinfect|clean|filter|boil)\w*\s+(?:\w+\s+){0,3}water\b|"
                                       r"\bwater\s+(?:from\s+(?:a|the)\s+(?:creek|stream|river|pond|lake))\b|"
                                       r"\bwater\b.{0,25}\bsafe to drink\b"),
    ("bushcraft", "shelter"): re.compile(r"\b(?:build|make|set up|pitch)\w*\s+(?:a\s+)?(?:survival\s+|debris\s+|tarp\s+)?"
                                         r"(?:shelter|lean-to|debris hut)\b"),
    ("bushcraft", "navigation"): re.compile(r"\b(?:use|read)\w*\s+(?:a\s+)?(?:map and\s+)?compass\b|\btake\s+a\s+"
                                            r"bearing\b|\bdeclination\b"),
    ("bushcraft", "ten_essentials"): re.compile(r"\bten essentials\b|\b(?:carry|pack|bring)\b.{0,20}\b(?:day hike|"
                                                r"hike|hiking)\b"),
    ("woodworking", "sharpening"): re.compile(r"\bsharpen\w*\s+(?:a\s+|my\s+|the\s+)?(?:chisel|plane|plane iron|"
                                              r"blade|iron)s?\b|\bhone\s+(?:a\s+|my\s+)?(?:chisel|plane)\b"),
    ("woodworking", "first_piece"): re.compile(r"\b(?:beginner|beginners|first|starter|easy)\b.{0,20}\b(?:woodworking|"
                                               r"wood|woodshop)\s+(?:project|piece|build)s?\b"),
    # the business (live sweep, 2026-11-25: "what's the markup I should use for my woodworking?" reached the materials
    # calculator, "how do I write a quote for a deck job?" a cut list)
    ("business", "biz_price"): re.compile(r"\b(?:markup|mark-up|margin|mark (?:it|them|things) up)\b"),
    ("business", "biz_terms"): re.compile(r"\b(?:write|make|put together|do|draw up)\w*\s+(?:up\s+)?(?:a\s+|an\s+)?"
                                          r"(?:quote|estimate|bid)s?\b"),
    ("carpentry", "tape"): re.compile(r"\bread\w*\s+(?:a\s+)?tape(?:\s+measure)?\b"),
    ("carpentry", "square_level"): re.compile(r"\b(?:check|tell)\w*\s+(?:if\s+)?(?:\w+\s+){0,3}(?:is\s+)?"
                                              r"(?:plumb|level|square)\b|\b3-4-5\b|\bspeed square\b"),
    ("carpentry", "circular_saw"): re.compile(r"\buse\s+(?:a\s+)?circular saw\b|\bcircular saw\s+safely\b"),
    # the flock (live sweep, 2026-11-25: "how do I know if my chickens have mites?" went to the model)
    ("gardening", "flock_care"): re.compile(r"\b(?:mites?|lice)\b(?=.*\b(?:hens?|chickens?|flock|coop|birds?|"
                                            r"poultry|roosts?)\b)|\b(?:hens?|chickens?|flock|coop|birds?|poultry)\b.*"
                                            r"\b(?:mites?|lice)\b|\bfeed\w*\s+(?:my\s+|the\s+|laying\s+)*(?:hens|"
                                            r"chickens|flock|layers)\b|\b(?:protect|keep)\w*\s+(?:my\s+|the\s+)?"
                                            r"(?:hens|chickens|flock|coop)\b.{0,30}\b(?:predators?|raccoons?|foxes|"
                                            r"hawks|winter|cold|warm|safe)\b"),
    ("gardening", "seed_starting"): re.compile(r"\bstart\w*\s+(?:my\s+|the\s+)?(?:\w+\s+)?seeds?\b|\bseeds?\s+"
                                               r"(?:indoors|inside)\b"),
}
_HOWTO = re.compile(r"\b(?:how (?:do|should|would|can|could) (?:i|you|one|we)|how to|what'?s the (?:best|right|safest) "
                    r"way to|what is the (?:best|right|safest) way to|best way to|"
                    r"teach me (?:how )?to|show me how to|what(?:'s| is) a good|what should i (?:make|build) "
                    r"(?:as|for) (?:a|my)|what(?:'s| is) (?:the|a) (?:right |good |best |usual |typical |fair )?"
                    r"(?:markup|mark-up|margin)|how much (?:markup|margin)|what should i (?:feed|give|do about)|"
                    r"how (?:can|do) i tell if)\b")
# What a lesson's words also mean but it doesn't teach (the sixth review): a fire pit or fire insurance, the tank's or
# the aquaponics' water, a seed company
NOT_ASKS = {
    ("bushcraft", "fire"): re.compile(r"\bfire\s*(?:pit|place|insurance|extinguisher|alarm|department|ant)s?\b|"
                                      r"\bfireplace\b|\bfire\s+(?:the|an?)\s+\w+"),
    ("bushcraft", "water"): re.compile(r"\b(?:tank|cistern|aquaponics|pool|hot tub|aquarium|fish|pond|well|softener|"
                                       r"heater|bath|dishwasher|radiator)s?\b"),
    ("gardening", "seed_starting"): re.compile(r"\b(?:company|business|website|money|fund|funding|round|investor)s?\b"),
    # his own numbers are the plans' (the tenth review): "how much margin did the shop make", "the margin on my
    # cutting boards", another store's markup; and a tax estimate is no quote
    ("business", "biz_price"): re.compile(r"\b(?:markup|margin)\s+(?:on|did|does|this|last|was|is)\b|\bmade\b|"
                                          r"\b(?:home depot|lowe'?s|walmart|amazon|tractor supply)\b"),
    ("business", "biz_terms"): re.compile(r"\btax(?:es)?\b|\bcleared\b|\bbank\b"),
}
# A drill that practises the lesson (core/drills.py), said as the words that start it
DRILL_FOR = {("gardening", "flock_care"): "flock", ("bushcraft", "water"): "water", ("carpentry", "circular_saw"): "saw", ("carpentry", "tape"): "cut list",
             ("business", "biz_price"): "market day"}
# What to say to do it with MIA, after the lesson
THEN = {("business", "biz_terms"): "To start one, say \"make a quote for\" and what it's for, and the customer.",
        ("business", "biz_price"): "For one of your products, ask \"what should I charge for\" it and I'll work it "
                                   "out from your costs."}


def find(words: str) -> Optional[tuple]:
    """Pure logic. (course id, lesson id) for a how-to his words ask about one of `ASKS`'s lessons, else None.
    Never what a lesson's words also mean but it doesn't teach (`NOT_ASKS`)."""
    said = " ".join(str(words or "").lower().replace("’", "'").split())
    if not _HOWTO.search(said):
        return None
    return next((key for key, pattern in ASKS.items()
                 if pattern.search(said) and not (key in NOT_ASKS and NOT_ASKS[key].search(said))), None)


_PLAIN = {"what", "when", "where", "which", "should", "would", "could", "about", "with", "from", "that", "this", "have",
          "know", "tell", "best", "your", "mine", "they", "them", "there", "their", "into", "does", "want",
          # what a lesson is about, not which step of it: "chickens" ties the mites step with the coop's wire
          "chicken", "chickens", "hens", "flock", "birds", "coop", "layers", "laying", "plants", "garden", "wood",
          "water", "fire", "seeds"}


def steps_for(steps: tuple, words: str) -> list:
    """Pure logic. A lesson's steps, the ones his question is about first ("how do I know if my chickens have
    mites?" leads with the mites step, not the coop door), the rest after in their order; as they are when none
    stands out."""
    asked = {w[:5] for w in re.findall(r"[a-z]{4,}", str(words or "").lower()) if w not in _PLAIN}

    def score(step: str) -> int:
        """How many of his words (by their first five letters) the step uses."""
        return len(asked & {w[:5] for w in re.findall(r"[a-z]{4,}", step.lower())})

    best = max((score(s) for s in steps), default=0)
    if best == 0:
        return list(steps)
    return [s for s in steps if score(s) == best] + [s for s in steps if score(s) != best]


def reply(context, words: str) -> Optional[str]:
    """The lesson's answer for a how-to (`find`), from the course's own record: its steps (the ones asked about first,
    `steps_for`), why and what to watch for,
    the drill to practise it, and how to start the course when he hasn't. None when it isn't one.
    Then how to do it with MIA, where there's a way (`THEN`)."""
    from core import paths

    found = find(words)
    if found is None:
        return None
    course, lesson_id = found
    program = paths.program_of(context, course)
    lesson = next((l for s in program.stages for l in s.lessons if l.id == lesson_id), None) if program else None
    if lesson is None:
        return None
    out = f"From the {program.name} course, \"{lesson.title}\": " + " ".join(steps_for(lesson.steps, words))
    if lesson.why:
        out += f" Why it matters: {lesson.why}"
    if lesson.watch:
        out += " Watch for: " + " ".join(lesson.watch)
    drill = DRILL_FOR.get(found)
    if drill:
        out += f" To practise it, say \"give me a {drill} drill\"."
    if found in THEN:
        out += " " + THEN[found]
    book = getattr(context, "paths", None)
    if book is not None and book.path(course) is None:
        out += f" It's one lesson of the {program.name} course: say \"I want to learn {program.name.lower()}\" to start it."
    return out
