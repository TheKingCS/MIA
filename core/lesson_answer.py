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

# the fish his courses name, and what those words mean that isn't a fish ("bass guitar", "perch business")
_FISH = (r"bass|trout|catfish|crappie|bluegill|panfish|sunfish|perch|walleye|pike|carp|salmon|muskie|musky|"
         r"striper|redfish|snook|cats|bream|gills")
_NOT_FISH = r"(?!\s+(?:guitar|amp|pickup|drum|tank|pond|fryer|finder|recipe|business|track|song|album|boat|filter|line\b))"
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
    # soldering and the meter (core/soldering_path.py: the live sweeps found it a gap); the Fable check of the courses
    # (2026-11-25): each needs its own subject's words, never a hook for hanging, a bass guitar or an outlet
    ("soldering", "fixing"): re.compile(r"\bsolder(?:ing)? bridges?\b|\bbridged? (?:two |the )?pins\b|\bdesolder\w*|"
                                        r"\bsolder (?:wick|sucker)\b|\btoo much solder\b|\bremov\w* (?:the )?solder\b|"
                                        r"\bcold (?:solder )?joints?\b"),
    ("soldering", "joints"): re.compile(r"\bsolder\w*\b"),
    ("soldering", "meter"): re.compile(r"\bmulti-?meter\b|\bcontinuity\b(?=.*\b(?:wires?|joints?|circuits?|meter|boards?|"
                                       r"fuses?|cables?|traces?)\b)|\b(?:measure|check|test|read)\w*\s+(?:the\s+|a\s+)?"
                                       r"(?:dc\s+)?(?:voltage|volts|resistance|ohms|amps|current)\b|\btest (?:a|the) "
                                       r"(?:resistor|fuse|diode)\b|\bcheck (?:a|the) (?:9 ?v|aa|aaa) battery\b"),
    # fishing (the live sweeps: hook sizes had been guessed)
    ("fishing", "hooks"): re.compile(r"\b(?:hook sizes?|size (?:of )?hooks?|(?:what|which) (?:size )?hooks?|hooks?)\b"
                                     r".{0,30}\b(?:" + _FISH + r"|fish|fishing|worms?|minnows?|plastics?|bait|crickets?|"
                                     r"nightcrawlers?)\b" + _NOT_FISH + r"|\bcircle hooks?\b|\bfish(?:ing)? hooks?\b|"
                                     r"\bhook sizes? (?:mean|work|go)\b"),
    ("fishing", "knots"): re.compile(r"\b(?:tie|tying)\b.{0,25}\b(?:hooks?|lures?|swivels?|fishing line|jigs?)\b"
                                     r"(?!.{0,25}\b(?:trailer|tarp|workbench|bench|truck|wall|fence)\b)|"
                                     r"\b(?:improved )?clinch knot\b|\bpalomar\b|\bfishing knots?\b|\bknot\b.{0,20}\b(?:braid|"
                                     r"fluoro\w*|mono\w*|hooks?|lures?|fishing line)\b"),
    ("fishing", "rigs"): re.compile(r"\b(?:texas|carolina|drop shot|slip bobber|bobber)\s+rigs?\b|\bbottom rigs?\b.{0,25}"
                                    r"\b(?:fish|catfish|carp)\b|\bset up (?:a |my )?(?:bobber|float)\b|"
                                    r"\brig\w*\b.{0,25}\b(?:bass|catfish|crappie|bluegill|worms?|bobber)\b" + _NOT_FISH),
    ("fishing", "release"): re.compile(r"\bcatch and release\b|\brelease\w*\s+(?:a\s+|the\s+)?(?:" + _FISH + r"|fish)\b"
                                       + _NOT_FISH + r"|\b(?:unhook|take the hook out of|get the hook out of|remove (?:a |"
                                       r"the )?hook from)\s+(?:a\s+|the\s+|my\s+|this\s+)?(?:" + _FISH + r"|fish)\b"),
    ("fishing", "cleaning"): re.compile(r"\b(?:clean|fillet|gut|scale|skin)\w*\s+(?:a\s+|the\s+|my\s+|these\s+)?(?:" + _FISH
                                        + r"|fish)\b" + _NOT_FISH + r"|\bcook\w*\b.{0,20}\bfish\b.{0,20}\b(?:to|temp\w*)\b"),
    ("fishing", "rules"): re.compile(r"\bfishing licen[cs]es?\b|\blicen[cs]e to fish\b|\b(?:bag|creel|size|daily) "
                                     r"limits?\b.{0,25}\b(?:" + _FISH + r"|fish)\b"),
    ("fishing", "reading_water"): re.compile(r"\bwhere (?:do|should|can|would) (?:i|you) (?:find|catch|fish for|look for)\b"
                                             r".{0,20}\b(?:" + _FISH + r"|fish)\b" + _NOT_FISH),
    ("gardening", "seed_starting"): re.compile(r"\bstart\w*\s+(?:my\s+|the\s+)?(?:\w+\s+)?seeds?\b|\bseeds?\s+"
                                               r"(?:indoors|inside)\b"),
}
_HOWTO = re.compile(r"\b(?:what size|which size|what hook|which hook|what knot|which knot|what(?:'s| is) the best knot|"
                    r"how hot|what temp\w*|where (?:do|should|can|would) (?:i|you)|do i need a|"
                    r"how (?:do|should|would|can|could) (?:i|you|one|we)|how to|what'?s the (?:best|right|safest) "
                    r"way to|what is the (?:best|right|safest) way to|best way to|"
                    r"teach me (?:how )?to|show me how to|what(?:'s| is) a good|what should i (?:make|build) "
                    r"(?:as|for) (?:a|my)|what(?:'s| is) (?:the|a) (?:right |good |best |usual |typical |fair )?"
                    r"(?:markup|mark-up|margin)|how much (?:markup|margin)|what should i (?:feed|give|do about)|"
                    r"how (?:can|do) i tell if)\b")
_NOT_BENCH_SOLDER = (r"\b(?:pipes?|copper|plumbing|sweat\w*|fittings?|stained glass|jewel\w*|water lines?|"
                     r"valves?|sink|gas lines?|junction box|mains|18650|battery tabs|battery packs?|cells|radiators?|"
                     r"gutters?|rings?|silver|flashing|roof)\b")
# What a lesson's words also mean but it doesn't teach (the sixth review): a fire pit or fire insurance, the tank's or
# the aquaponics' water, a seed company
NOT_ASKS = {
    ("bushcraft", "fire"): re.compile(r"\bfire\s*(?:pit|place|insurance|extinguisher|alarm|department|ant)s?\b|"
                                      r"\bfireplace\b|\bfire\s+(?:the|an?)\s+\w+"),
    ("bushcraft", "water"): re.compile(r"\b(?:tank|cistern|aquaponics|pool|hot tub|aquarium|fish|pond|well|softener|"
                                       r"heater|bath|dishwasher|radiator)s?\b|"
                                       # the kitchen and the house (the Fable review, 2026-11-25)
                                       r"\b(?:pasta|noodles|rice|eggs?|coffee|tea|basement|flood\w*|leak\w*|carpet|"
                                       r"floor|trough|bucket|hard water|dishes)\b"),
    ("bushcraft", "shelter"): re.compile(r"\bfor (?:the |my |our )?(?:goats?|chickens?|hens|animals?|dogs?|horses?|"
                                         r"pigs?|livestock|cows?|sheep|ducks?|rabbits?|cats?)\b"),
    ("gardening", "seed_starting"): re.compile(r"\b(?:company|business|website|money|fund|funding|round|investor)s?\b"),
    # his own numbers are the plans' (the tenth review): "how much margin did the shop make", "the margin on my
    # cutting boards", another store's markup; and a tax estimate is no quote
    ("business", "biz_price"): re.compile(r"\b(?:markup|margin)\s+(?:on|did|does|this|last|was|is)\b|\bmade\b|"
                                          r"\bmargin of (?:safety|error)\b|"
                                          r"\b(?:home depot|lowe'?s|walmart|amazon|tractor supply)\b"),
    ("fishing", "hooks"): re.compile(r"\bhooks? (?:for|on) (?:the |my |a )?(?:wall|garage|tools?|towels?|coats?|"
                                     r"pictures?|hanging|ceiling|shed|keys|hats?|bags?|trailer|chains?)\b|\bhook up\b|"
                                     r"\b(?:crochet|mirror|curtain|shower|towing|tow|latch|gate|eye|picture|wall)\b|"
                                     r"\b(?:take|get|remove)\b.{0,10}\bhook out\b|\bunhook\w*\b|\bremov\w* (?:a |the )?"
                                     r"hook\b"),  # taking one out is the release lesson
    ("fishing", "cleaning"): re.compile(r"\bfish ?tank\b|\baquarium\b|\baquaponics\b|\bpond\b|\bfryer\b"),
    # a hook in a person or a pet is first aid or the vet's, never a fish's release (the Fable check)
    ("fishing", "release"): re.compile(r"\b(?:hand|finger|thumb|skin|arm|leg|ear|eye|lip|face|foot|dog|cat|puppy|horse|"
                                       r"trailer|washing machine|bra)\b"),
    ("fishing", "rigs"): re.compile(r"\b(?:guitar|amp|pickup|worm bin|drain|drill press|truck|antenna)\b"),
    ("fishing", "knots"): re.compile(r"\bclinch (?:the|a) (?:deal|nail|win)\b"),
    # a pipe's, a gas line's, a battery pack's or a ring's solder is never a circuit board's (the Fable check)
    ("soldering", "joints"): re.compile(_NOT_BENCH_SOLDER),
    ("soldering", "fixing"): re.compile(_NOT_BENCH_SOLDER),
    # mains and high-energy sources are an electrician's, never the bench meter lesson (the Fable check)
    ("soldering", "meter"): re.compile(r"\b(?:outlets?|sockets?|receptacles?|mains|wall|breakers?|panel|live wire|hot wire|"
                                       r"is (?:a|the) wire live|120 ?v?|240 ?v?|\bac\b|appliances?|microwave|capacitors?|"
                                       r"electric fence|fence|solar|car|truck|alternator|dryer|oven|stove|well pump|"
                                       r"furnace|story|business continuity)\b"),
    ("business", "biz_terms"): re.compile(r"\btax(?:es)?\b|\bcleared\b|\bbank\b|\btweets?\b|\bquote (?:a |the )?"
                                          r"(?:verse|passage|text|line|source)\b"),
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
          "water", "fire", "seeds",
          # the fishing and soldering lessons' own subjects: "what size hook for catfish?" leads with catfish's step
          "hook", "hooks", "size", "sizes", "fish", "fishing", "knot", "knots", "solder", "soldering", "meter"}


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
