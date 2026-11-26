"""
core.her_asks
===============

His bare answer to her own last question, finished in code (brainstorm round 19; the live check 2026-11-26: "5
gallons" after "How much fuel?" got the question echoed back, "Springfield, Illinois" after "I don't know your town
yet" a made-up forecast). Each ask is known by its own words in her last message, and each answer is read strictly:

- the firewood a winter takes him ("about 4 cords": core/firewood.answer_to_ask);
- the fuel for the generator ("5 gallons", "20 lb of propane", "a half gallon": core/homestead_sums.generator_runtime);
- the generator's burn rate ("half a gallon an hour": kept as prepared.generator_gph, then the runtime for the fuel
  he'd already given);
- his town ("Springfield, Illinois", or one or two capitalised words): set only when the weather service finds it,
  never a command or a sentence of his (the Fable review: "remind me to call mom" or "undo that" after her ask had
  become a town).

- a build she offered to work out ("I'm thinking about building a shed" got "Good project. I can work out the
  materials ... at your size"): its size ("a 10 by 12", "what about 10x12?") is its materials, "how much would it
  cost?" asks the size, and "add it to my projects" adds it (the conversation check, 2026-11-26: the size had gone to
  a running-costs plan's guess, and "add it" nowhere).

- after a catch she logged ("... fish logged in all"), "when's the best time to go back?" is the fishing times
  (best_time_to_fish).

- after her ask for his last spring frost, a bare date ("April 20") is kept as it (core/planting_now.keep_frost);
- after one of her course replies, "what should I work on next?" is that course's next step;
- after her own money reply (a bill marked paid, income or an expense recorded), "how much is left (after that)?"
  is the month's money after what's due.

Anything else is None, and the turn goes on as if she hadn't asked. `reply(context, last_reply, prompt)` is the one
call (core/assistant_turn._follow_through_reply).
"""

from __future__ import annotations

import re
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

FUEL_ASK = "How much fuel? Say it in gallons"
RATE_ASK = 'like "my generator burns half a gallon an hour"'
TOWN_ASK = "I don't know your town yet"
# the build she offered to work out, in her own words (core/assistant_turn's "thinking of building" reply, or her size ask)
_BUILD = re.compile(r"materials and cuts for an? (?P<kind>[\w' -]+?) at your size|For the (?P<kind2>[\w' -]+?), what size\?")
_SIZE = re.compile(r"^\s*(?:(?:ok(?:ay)?|so|and|hmm|well),?\s+)?(?:what about|how about|make it|let'?s (?:do|say)|maybe|say|about|"
                   r"go with)?\s*(?:an?\s+)?(?P<size>\d+(?:\.\d+)?\s*(?:'|ft|feet|foot)?\s*(?:by|x)\s*\d+(?:\.\d+)?)\s*"
                   r"(?:'|ft|feet|foot)?(?:\s+(?:one|size|feet))?\s*[?.!]*\s*$", re.I)
_BUILD_COST = re.compile(r"^\s*(?:and\s+|so\s+)?(?:how much\s+(?:would|will|does|do)\s+(?:the\s+)?(?:it|that|one|lumber|"
                         r"materials|wood)\s+(?:cost|run(?: me)?)|what\s+(?:would|will)\s+(?:the\s+)?(?:it|that|one|"
                         r"lumber|materials|wood)\s+cost)(?:\s+(?:me|us))?\s*[?.!]*\s*$", re.I)
_BUILD_ADD = re.compile(r"^\s*(?:ok(?:ay)?,?\s+|great,?\s+|yes,?\s+)?(?:please\s+)?(?:(?:add|put)\s+(?:it|that|this)\s+"
                        r"(?:to|in|on)\s+(?:my|the)\s+(?:projects?|project list)|make\s+(?:it|that|this)\s+(?:a|into a)\s+"
                        r"project)(?:\s+please)?\s*[.!]*\s*$", re.I)
# her own money reply (a payment marked, income or an expense recorded, what's left): a bare "how much is left?" after
# it is the month's money (core/money_periods.afford)
_AFTER_MONEY = re.compile(r"\bMarked '[^']+' paid\b|\bRecorded \$[\d,.]+ (?:of income|expense)\b|\bFrom what's logged\b")
_BARE_LEFT = re.compile(r"^\s*(?:and\s+|so\s+|ok(?:ay)?,?\s+)?(?:how much (?:is|do (?:i|we) have|have (?:i|we) got) left(?: over)?|"
                        r"what(?:'s| is) left)(?:\s+(?:now|after that))?\s*[?.!]*\s*$", re.I)
# her own course replies ("Guitar, stage 1 ...", "From Guitar, stage 1", "Logged. Guitar this week:"): "what should I
# work on next?" is that course's next step (core/paths.next_step), never a project's (the guitar conversation check)
_COURSE_SAID = re.compile(r"(?:^|\. |\n)(?:From )?(?P<prog>[A-Z][\w' ]{1,40}?)(?: \([^)]*\))?, stage \d+|\bLogged\. (?P<prog2>[A-Z][\w' ]{1,40}?) "
                          r"this week:")
_NEXT = re.compile(r"^\s*(?:so\s+|ok(?:ay)?,?\s+|and\s+)?(?:what(?:'s| is) next|what next|what (?:should|do) i (?:work on|do|practi[cs]e)"
                   r" next|what(?:'s| is) my next step)\s*[?.!]*\s*$", re.I)
_AFTER_CATCH = re.compile(r"\b\d+ fish logged in all\b", re.I)  # her catch replies' own words, never hours or eggs
_GO_BACK = re.compile(r"^\s*(?:so\s+|and\s+)?(?:when(?:'s| is) (?:the )?best (?:time|day) to go (?:back|again|fishing)|when "
                      r"should (?:i|we) go (?:back|again|fishing)|when (?:can|could) (?:i|we) go back)(?: out)?(?: there)?\s*"
                      r"[?.!]*\s*$", re.I)
_LUMBER = {(2, 2), (2, 3), (2, 4), (2, 6), (2, 8), (2, 10), (2, 12), (4, 4), (4, 6), (6, 6), (1, 2), (1, 4), (1, 6),
           (1, 8)}  # nominal lumber, never a build's size ("what about a 2 by 4?")
_FEET = re.compile(r"^\s*(?:(?:ok(?:ay)?|so|and|maybe|about|say|make it|what about|how about),?\s+)*(?P<n>\d+(?:\.\d+)?)\s*"
                   r"(?:'|ft|feet|foot)(?:\s+(?:long|of (?:it|fence)))?\s*[?.!]*\s*$", re.I)
# her replies that are still the build's own thread: her size ask, or a materials list (core/plan_library's lines)
_BUILD_THREAD = re.compile(r"^For the [\w' -]+, what size\?|^\d+(?:\.\d+)? x \d+(?:\.\d+)? ft |^\d+ ft (?:of )?\w*\s*fence", re.I)

_FUEL_ONLY = re.compile(r"^\s*(?:about |around |maybe |probably |like |i have |we have |i'?ve got |we'?ve got )?(?:\d+(?:\.\d+)?|"
                        r"a couple(?: of)?|half an?|a half|an?|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
                        r"(?:gallons?|gal|lbs?|pounds?|liters?|litres?)(?: of (?:gas|gasoline|diesel|propane|lp|fuel))?"
                        r"\s*[.!]?\s*$", re.I)
_RATE_ONLY = re.compile(r"^\s*(?:about |around |maybe |probably |it'?s |it burns )?(?P<n>\d*\.?\d+|half an?|a half|a quarter "
                        r"(?:of )?an?|an?|one)\s*(?:gallons?|gal)\s*(?:an|per|a|each) hour\s*[.!]?\s*$", re.I)
_RATE_WORDS = {"half a": 0.5, "half an": 0.5, "a half": 0.5, "a quarter of a": 0.25, "a quarter a": 0.25, "a": 1.0,
               "an": 1.0, "one": 1.0}
# a town: "Name, Region" or one or two capitalised words, never a word that's his answer to something else
_TOWN = re.compile(r"^\s*(?:(?i:it'?s |i'?m in |i live in |we'?re in |we live in ))?(?P<x>[A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+)?"
                   r"(?:,\s*[A-Za-z][A-Za-z .]{1,30})?)\s*[.!]?\s*$")
_NOT_A_TOWN = re.compile(r"^(?:home|here|there|work|the farm|same|idk|skip|cancel|maybe|yes|yeah|yep|no|nope|ok|okay|"
                         r"thanks|hello|hi|hey|later|never mind|nevermind|undo|stop)\b", re.I)


def reply(context, last_reply: str, prompt: str, recent: tuple = ()) -> Optional[str]:
    """His answer to her last question, kept or worked out in code; None when she didn't ask, or his words aren't
    that answer. `recent` is her last few replies, newest last: the build she offered is found there too, so "add it
    to my projects" after its materials list still means the shed, but only when every reply since was the build's
    own thread; a board's size ("a 2 by 4") is never the build's, a fence takes its feet, and a project of that name
    already kept is said so, never added twice (the Fable review). After a catch she logged, "when's the best time to
    go back?" is the fishing times; after her money reply, "how much is left?" is the month's money; after her frost ask, a bare
    date is his last frost; after her course reply, "what should I work on next?" is that course's next step."""
    asked, said = str(last_reply or ""), str(prompt or "").strip()
    if not asked or not said or len(said) > 60:
        return None
    from core import firewood

    kept = firewood.answer_to_ask(context, asked, said)
    if kept:
        return kept
    if FUEL_ASK in asked and _FUEL_ONLY.match(said):
        from core.homestead_sums import generator_runtime

        words = re.sub(r"\ba half\b", "half a", said, flags=re.I)
        answer = generator_runtime(context, words)
        return None if answer.startswith("How much fuel?") else answer
    rate = _RATE_ONLY.match(said) if RATE_ASK in asked else None
    if rate:
        n = rate.group("n").lower()
        gph = _RATE_WORDS.get(n) if n in _RATE_WORDS else float(n)
        if not gph or not 0.05 <= gph <= 5:
            return None
        from core.assistant_today_actions import _action_set_preparedness

        kept = _action_set_preparedness(context, {"generator_gph": gph})
        fuel = re.search(r"to work out (.+?):", asked)  # the fuel he'd given before her ask: its runtime now
        if fuel and str(kept).startswith("Set:"):
            from core.homestead_sums import generator_runtime

            kept = f"{kept} {generator_runtime(context, fuel.group(1))}"
        return kept
    if any(m in asked for m in ("When's your last spring frost?", "I need your last spring frost",
                                "When is your last spring frost")):  # the garden plan's own ask too
        from core import planting_now

        kept = planting_now.keep_frost(context, said, "last")  # "April 20" after her frost ask
        if kept is not None:
            return kept
    course = _COURSE_SAID.search(asked) if _NEXT.match(said) else None
    if course:
        from core import paths

        book = getattr(context, "paths", None)
        program = paths.find_program(context, course.group("prog") or course.group("prog2"))
        if book is not None and program is not None and book.path(program.id) is not None:
            return paths.next_step(book, program)
    if _AFTER_MONEY.search(asked) and _BARE_LEFT.match(said):
        from core import money_periods

        return money_periods.afford(context, None)
    if _AFTER_CATCH.search(asked) and _GO_BACK.match(said):
        actions = getattr(context, "assistant_actions", None)
        return actions.execute(context, "best_time_to_fish", {"when": "this week"}) if actions is not None else None
    build = _BUILD.search(asked)
    if build is None and _BUILD_ADD.match(said):  # "add it" after its list: an older offer, only along its own thread
        for i in range(len(recent) - 1, max(-1, len(recent) - 4), -1):
            found = _BUILD.search(recent[i])
            if found:
                if all(_BUILD.search(r) or _BUILD_THREAD.search(r.strip()) for r in recent[i + 1:]):
                    build = found
                break
    if build:
        kind = (build.group("kind") or build.group("kind2")).strip()
        from core.assistant_plan_actions import materials_reply

        fence = "fence" in kind.lower()
        feet = _FEET.match(said) if fence else None
        if feet:  # "100 feet": a fence's length
            return materials_reply(context, f"materials for {feet.group('n')} feet of {kind}")
        sized = None if fence else _SIZE.match(said)
        if sized:  # "a 10 by 12": the calculators' list for it (core/assistant_plan_actions.materials_reply)
            size = re.sub(r"\s*(?:'|ft|feet|foot)\s*", " ", sized.group("size")).strip()
            size = re.sub(r"\s*(?:by|x)\s*", " by ", size, flags=re.I)
            a, b = (float(n) for n in size.split(" by "))
            if (int(min(a, b)), int(max(a, b))) in _LUMBER or min(a, b) < 3:
                return None  # "a 2 by 4" is a board, never the build's footprint
            return materials_reply(context, f"materials for a {size} {kind}")
        if _BUILD_COST.match(said):
            example = "100 feet" if fence else "a 10 by 12"
            return (f"For the {kind}, what size? Say it like \"{example}\" and I'll work out the materials and price "
                    f"them from your records.")
        if _BUILD_ADD.match(said):
            actions = getattr(context, "assistant_actions", None)
            if actions is None:
                return None
            name = kind[:1].upper() + kind[1:]
            from core import project_time

            if project_time.project_named(context, name, whole=True) is not None:
                return f"{name} is already one of your projects."  # never a second Shed (the Fable review)
            return actions.execute(context, "add_project", {"name": name})
    town = _TOWN.match(said) if TOWN_ASK in asked else None
    if town and not _NOT_A_TOWN.match(said) and not said.lower().startswith(("my town is", "set my town")):
        actions = getattr(context, "assistant_actions", None)
        if actions is None:
            return None
        try:
            answer = actions.execute(context, "set_weather_place", {"place": town.group("x").strip()})
        except Exception:
            log.exception("Couldn't set his town")
            return None
        found = str(answer or "").startswith("The weather is for")
        return answer if found or "," in town.group("x") else None  # a word that isn't a town is the model's
    return None
