"""
core.assistant_turn
=====================

One Assistant turn — user text in, the things MIA should say back out —
shared by every voice surface: the headless Core loop
(`core/voice_loop.py`) and the phone voice endpoint (`server/app.py`).
Pulled out of `VoiceLoopController._handle_turn()` unchanged in
behavior, so both surfaces answer, act, and skip destructive bundled
tool calls identically instead of drifting apart.

Memory extraction (or, while journaling, organizing the journal
session: core/talk_it_out.py) is deliberately returned as a follow-up
(`AssistantTurn.followup`) rather than run inline: it's a second LLM
call, and running it before the reply is spoken/sent would add its
full latency to every answer. Callers speak/send first, then call
`run_followup()`.
A model reply that only says the person's words back (`echoes`) is replaced by a plain line asking again, and one
that claims a change no tool made is said honestly (core/claim_check.py). A tool's date the model fills is the day
his words name (`with_his_day`, `named_day`), and "remind me to X on a day" goes on his calendar in code
(`_reminder_reply`).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.app_context import AppContext
from core.assistant_chat import build_chat_request, named_tool, split_safe_tool_calls
from core.conversation_manager import Conversation, ConversationMessage
from core.logger import get_logger
from core.talk_it_out import Followup, after_fixed_reply, apply_followup, plan_followup, pre_turn, with_offer

log = get_logger(__name__)


@dataclass
class AssistantTurn:
    """What one turn produced: each thing MIA says in order, a follow-up job to run in the background, whether
    the model answered, the memories it used (What I Used), a page to open, and for the trace how it was answered
    and the tools offered and called.
    """
    replies: list[str] = field(default_factory=list)  # each thing MIA should say, in order
    followup: Optional[Followup] = None  # background job for run_followup(), if any
    llm_available: bool = True
    # What I Used (DEC-0029): the memories this turn's answer was given,
    # so a surface can show them under the reply, each fixable or forgettable.
    used: list[dict] = field(default_factory=list)
    # A page for the surface to open (show-off mode's tour, DEC-0031).
    open: str = ""
    # For the turn trace (core/turn_trace.py): which way it was answered.
    route: str = ""
    tools_offered: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)


def add_message(conversation: Conversation, role: str, content: str) -> None:
    """Adds a message to the conversation, stamped with the time and the conversation's privacy right now."""
    conversation.messages.append(
        ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            privacy=conversation.current_privacy(),
        )
    )


def _direct_lookup(context, prompt: str) -> Optional[str]:
    """A question that clearly asks for one lookup ("When is my next
    alarm?") is answered by running it, no model (2026-10-13,
    core/assistant_actions.direct_lookup). How-to and teach-me questions
    about using MIA (asked of her tool registry, `about_mia`) still go to the help docs."""
    from core.assistant_chat import looks_like_how_to_question, looks_like_teaching_request

    registry = getattr(context, "assistant_actions", None)
    if (registry is None or looks_like_how_to_question(prompt, context) or looks_like_teaching_request(prompt, context)
            or _about_her(prompt)):
        return None
    action = registry.direct_lookup(prompt, context)
    return registry.execute(context, action.name, action.direct_arguments(prompt)) if action is not None else None


def _about_her(prompt: str) -> bool:
    """Whether the message is a question only MIA's own records answer (her history, limits, design, what she's
    being built toward, how she learns: core/self_knowledge.py). The person's question plans and lookups stand
    aside for it, and the model answers with those records beside it."""
    from core.self_knowledge import asks_about_her

    try:
        return asks_about_her(prompt)
    except Exception:
        log.exception("Couldn't tell whether the question is about MIA herself")
        return False


def instant_answer(context, conversation, prompt: str) -> Optional[str]:
    """For the desktop's chat panels, which build their own model request
    (2026-10-30: they never got these): the lockdown phrase and the stop
    commands (core/lockdown.py, core/stop.py), a plain-word command done by code
    ("workout complete", "undo that"), a job being walked through ("next",
    "checked", core/trade_actions.py), the greenhouse and its hardware
    ("take over the greenhouse", "flash the safety MCU", DEC-0150), what MIA runs on ("what breaks if Ollama
    stops?", core/service_map.py), what they did ("I put away the
    dishes", core/did_it.py), or a question one lookup answers, run by
    code, no model; None when a question plan will answer (it comes
    first, as in run_assistant_turn), it follows up on a tool's answer
    (core/conversation_state.follows_a_tool), or it's for the model. Never in a
    personal mode or the journal, except "stop", "stop everything" and
    "carry on" (core/stop.py), asked first in every conversation, as in
    a turn.
    Building an ESP32 lab along with MIA (core/esp32_sim.reply) is answered there too, after the greenhouse and what
    MIA runs on.
    A scenario drill (core/drills.reply) is answered there too.
    A design of hers not built yet is answered there too, as a plan.
    A first-aid how-to too (`_first_aid_reply`).
    A how-to from a course lesson too (`_lesson_reply`).
    Days of water too (`_water_on_hand_reply`).
    A materials question too (`_materials_reply`).
    A reminder on a day too (`_reminder_reply`).
    A course's next lesson too (`_next_lesson_reply`).
    His upkeep (`_upkeep_reply`) and an LED's resistor (`_led_reply`) too.
    A short follow-up to a code answer, made whole, too (`_follow_through_reply`: "what about this month?"), and a
    go-ahead to her own offer runs its words (core/conversation_state.offered_phrase), and the sentence is put in
    the shape her routes read (`reshaped`), as in a turn.
    What he spent on a category (`_spent_on_reply`) too.
    A crop's dates and the 72-hour kit (`_garden_kit_reply`) too.
    The hours he puts into his projects (`_project_time_reply`) too, and an outlet's voltage (`_mains_reply`).
    A monthly reminder (`_monthly_reminder_reply`) too, a unit conversion (`_convert_reply`) and a holiday's date
    (`_holiday_reply`), and the house's trouble (`_home_trouble_reply`), and when to fish (`_fish_when_reply`), and the
    power out (`_outage_reply`), and the small everyday answers (`_everyday_reply`), and a load's watts
    (`_load_watts_reply`), and a bill paid, a product's stock or a debt's balance (`_records_reply`), and the
    homestead's own answers (`_own_tool_reply`).
    A weekly reminder too (`_weekly_reminder_reply`).
    What he spent too (`_spent_reply`).
    The morning briefing too (`_morning_briefing_reply`).
    A quote from a job's words too (`_job_quote_reply`).
    A daily reminder too (`_daily_reminder_reply`).
    Two logs in one sentence too (`_two_things_reply`: "$40 on screws and 2 hours on the shed")."""
    from core import stop  # "stop", "stop everything", "carry on": in code, before anything else (REQ-AUT-010)
    from core.conversation_state import set_turn_follow_up

    set_turn_follow_up(prompt)  # a new turn: the last one's follow-up words never reach this one's lookups
    try:
        from core import lockdown

        stopped = lockdown.handle(context, prompt) or stop.handle(context, prompt)
    except Exception:
        log.exception("Couldn't follow the stop")
        stopped = None
    if stopped is not None:
        return stopped
    if _personal(conversation):
        return None
    from core.conversation_state import offered_phrase

    prompt = offered_phrase(conversation, prompt) or prompt  # "ok, start it" to her offer, as in a turn
    prompt = reshaped(prompt)  # a greeting before a question, the weekday first, as in a turn
    from core.trade_actions import reply as job_reply

    try:  # a job in progress, or "walk me through ..." (DEC-0149), as in a turn
        walked = job_reply(context, prompt)
    except Exception:
        log.exception("Couldn't follow the job")
        walked = None
    if walked is None:
        walked = _greenhouse_reply(context, prompt)  # the greenhouse and its hardware (DEC-0150), as in a turn
    if walked is None:
        walked = _service_reply(context, prompt)  # "what breaks if Ollama stops?" (core/service_map.py, T-0007)
    if walked is None:
        walked = _lab_build_reply(context, conversation, prompt)  # building a lab along with MIA, as in a turn
    if walked is None:
        walked = _drill_reply(context, conversation, prompt)  # a scenario drill, as in a turn
    if walked is None:
        walked = _first_aid_reply(context, prompt)  # "how do you use a tourniquet?", as in a turn
    if walked is None:
        walked = _lesson_reply(context, prompt)  # "how do I sharpen a chisel?": her course's lesson, as in a turn
    if walked is None:
        walked = _water_on_hand_reply(context, prompt)  # "how many days of water do I have?", as in a turn
    if walked is None:
        walked = _job_quote_reply(context, prompt)  # "write a quote for Sarah's 12 by 16 deck", as in a turn
    if walked is None:
        walked = _materials_reply(context, prompt)  # "how many fence posts for 200 feet?", as in a turn
    if walked is None:
        walked = _next_lesson_reply(context, prompt)  # "what's my next guitar lesson?", as in a turn
    if walked is None:
        walked = _reminder_reply(context, prompt)  # "remind me to check the oil Saturday", as in a turn
    if walked is None:
        walked = _weekly_reminder_reply(context, prompt)  # "remind me every Monday to ...", as in a turn
    if walked is None:
        walked = _monthly_reminder_reply(context, prompt)  # "remind me to change the filter every month", as in a turn
    if walked is None:
        walked = _daily_reminder_reply(context, prompt)  # "remind me every morning to ...", as in a turn
    if walked is None:
        walked = _two_things_reply(context, prompt)  # "I spent $40 on screws and 2 hours on the shed", as in a turn
    if walked is None:
        walked = _spent_reply(context, prompt)  # "I spent $30 on groceries", as in a turn
    if walked is None:
        walked = _upkeep_reply(context, prompt)  # "when is my truck due for an oil change?", as in a turn
    if walked is None:
        walked = _led_reply(context, prompt)  # "what resistor for an LED on 5 volts?", as in a turn
    if walked is None:
        walked = _spent_on_reply(context, prompt)  # "how much did I spend on groceries this month?", as in a turn
    if walked is None:
        walked = _garden_kit_reply(context, prompt)  # a crop's dates, the 72-hour kit, as in a turn
    if walked is None:
        walked = _project_time_reply(context, prompt)  # "log 2 hours on the shed", as in a turn
    if walked is None:
        walked = _mains_reply(context, prompt)  # an outlet's voltage, in fixed safe words, as in a turn
    if walked is None:
        walked = _home_trouble_reply(context, prompt)  # a burst pipe, a flooded basement, as in a turn
    if walked is None:
        walked = _outage_reply(context, prompt)  # the power out, and his readiness, as in a turn
    if walked is None:
        walked = _follow_through_reply(context, conversation, prompt)  # "what about this month?", as in a turn
    if walked is None:
        walked = _records_reply(context, prompt)  # "did I pay the electric bill?", "how many cutting boards?", as in a turn
    if walked is None:
        walked = _own_tool_reply(context, prompt)  # the hens, the garden's water, the feed, canning, as in a turn
    if walked is None:
        walked = _load_watts_reply(context, prompt)  # "my freezer uses 150 watts", as in a turn
    if walked is None:
        walked = _everyday_reply(context, prompt)  # the time, days until, square feet, a walk logged, as in a turn
    if walked is None:
        walked = _fish_when_reply(context, prompt)  # "when's a good time to fish?", as in a turn
    if walked is None:
        walked = _convert_reply(context, prompt)  # "convert 5 gallons to liters", as in a turn
    if walked is None:
        walked = _holiday_reply(context, prompt)  # "when is Thanksgiving?", as in a turn
    if walked is None:
        walked = _morning_briefing_reply(context, prompt)  # "every morning, tell me the weather", as in a turn
    if walked is None:
        walked = _plan_reply(prompt)  # a design of hers not built yet, said as a plan
    if walked is not None:
        return walked
    from core.quick_commands import handle

    quick = handle(context, prompt)
    if quick is not None:
        return quick
    from core.did_it import reply as did_reply

    try:  # "I just put away the dishes" (DEC-0148), after the quick commands (a workout, a meal), as in a turn
        did = did_reply(context, conversation, prompt)
    except Exception:
        log.exception("Couldn't take in what the person did")
        did = None
    if did is not None:
        return did
    from core.conversation_state import follow_up, follows_a_tool
    from core.question_plans import match

    if _about_her(prompt):  # her own records answer it, in the model's turn
        return None
    if match(context, prompt) is not None or follow_up(conversation, prompt) is not None:
        return None
    if follows_a_tool(context, conversation, prompt):  # a follow-up to a tool's answer is the model's, with that tool
        return None
    return _direct_lookup(context, prompt)


def _lab_build_reply(context, conversation, prompt: str):
    """Building an ESP32 lab along with MIA, in code (core/esp32_sim.reply): a lab named to build, or "next step"
    right after a step; or one of My Bench's designs asked for ("build me a motion light", core/bench_designs.reply);
    None when the words aren't for it."""
    from core import bench_designs, esp32_sim

    try:
        return bench_designs.reply(context, conversation, prompt) or esp32_sim.reply(context, conversation, prompt)
    except Exception:
        log.exception("Couldn't follow the lab's build")
        return None


def _plan_reply(prompt: str):
    """A design of hers that nothing builds yet, said in code as a plan (core/self_knowledge.plan_reply); None
    otherwise."""
    from core.self_knowledge import plan_reply

    try:
        return plan_reply(prompt)
    except Exception:
        log.exception("Couldn't say what her plan is")
        return None


def _drill_reply(context, conversation, prompt: str):
    """A scenario drill, in code (core/drills.reply): "give me a survival drill", or an answer to the question MIA
    just asked; None when the words aren't for a drill."""
    from core import drills

    try:
        return drills.reply(context, conversation, prompt)
    except Exception:
        log.exception("Couldn't follow the drill")
        return None


def _first_aid_reply(context, prompt: str):
    """A first-aid how-to, in code (core/first_aid_floor.teach): the floor's own Red Cross and AHA words and the number
    for his country, then the drill to practise it when there is one (core/drills.FOR_KIND); None otherwise."""
    from core import drills, first_aid_floor
    from core.region import region_for

    try:
        taught = first_aid_floor.teach(prompt, region_for(context))
    except Exception:
        log.exception("Couldn't teach the first aid")
        return None
    if taught is None:
        return None
    kind = next((k for k, words in first_aid_floor._TOPIC if words.search(prompt.lower())), "")
    drill = drills.FOR_KIND.get(kind)
    return taught + (f" To practise it, say \"give me a {drill} drill\"." if drill else "")


_WATER_ON_HAND = re.compile(r"\b(?:days of (?:drinking )?water|how much (?:drinking )?water do (?:i|we) have|"
                            r"how long (?:will|would) (?:my|our|the) water last)\b")


def _water_on_hand_reply(context, prompt: str):
    """"How many days of water do I have?", in code, both ways it can mean (live check, 2026-11-25: three tools
    matched, and the model took the property's water budget and asked for the roof): the drinking water in the pantry
    against his target (core/preparedness.water_lines), then the property's stored water, its use and how long it
    lasts (core/water_budget.say). None for anything else.
    Only for a question, never a command or someone else's water (a car, the coop)."""
    from core.assistant_actions import looks_like_question

    said = prompt.lower().replace("’", "'")
    if not _WATER_ON_HAND.search(said) or not looks_like_question(prompt) \
            or re.match(r"\s*(?:remind|set|add|log|put|change|make)\b", said) \
            or re.search(r"\b(?:car|bottle|cooler|in the sun|coop|hens?|chickens?)\b", said):
        return None  # never a command or someone else's water ("remind me to buy 14 days of water": the sixth review)
    from core import preparedness, water_budget

    try:
        drinking = " ".join(preparedness.water_lines(context)).replace("Water: ", "Drinking water: ", 1)
        stored = water_budget.say(context)
    except Exception:
        log.exception("Couldn't answer the water on hand")
        return None
    return f"{drinking}\n\nFor the whole property: {stored}"


# Tools whose date the model fills, and his words may name a day for
_DATED = {"add_calendar_event": "date"}


def with_his_day(name: str, arguments, prompt: str, today=None) -> dict:
    """Pure logic. A call's arguments with the day his words name (`named_day`: "Friday", "tomorrow", "next
    Saturday") in place of the model's date, for a tool that takes one (`_DATED`; live sweep, 2026-11-25: "put the vet
    on the calendar for Friday at 2pm" went on 2024-03-15, made up and in the past). A date his words give themselves
    ("December 24", "12/04", "the 3rd"), or no day, leaves the model's as it is."""
    arguments = dict(arguments or {})
    field = _DATED.get(name)
    if not field:
        return arguments
    day = named_day(prompt, today)
    if day is not None:
        arguments[field] = day.isoformat()
    return arguments


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_EXPLICIT = re.compile(r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
                       r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+\d{1,2}\b|"
                       r"\b\d{1,2}/\d{1,2}\b|\b\d{4}-\d{2}-\d{2}\b|\bthe\s+\d{1,2}(?:st|nd|rd|th)\b", re.I)


def named_day(prompt: str, today=None):
    """Pure logic. The one day his words name, or None: none when they give a date themselves ("December 24",
    "12/04", "the 3rd": the seventh review, a stated date had been replaced by a weekday). "Today", "tonight",
    "tomorrow"; else a weekday, the one after "on", "for", "this", "next" or "by" before any other (a weekday in a
    title, "Tuesday trivia night ... for Thursday", is Thursday), and "next Friday" the one after the coming one.
    A weekday after "on", "by", "this" or "next" beats one after "for", and a weekday's own ("Tuesday's meeting") is
    never it."""
    from datetime import date as _date, timedelta

    said = " ".join(str(prompt or "").lower().replace("’", "'").split())
    today = today or _date.today()
    if _EXPLICIT.search(said):
        return None
    if re.search(r"\btomorrow\b", said):
        return today + timedelta(days=1)
    if re.search(r"\b(?:today|tonight|this (?:morning|afternoon|evening))\b", said):
        return today
    found = [(m.start(), m.group(2), m.group(1) or "") for m in
             re.finditer(r"\b(?:(on|for|this|next|by|coming)\s+)?(" + "|".join(_WEEKDAYS) + r")\b(?!'s)", said)]
    if not found:
        return None  # "Tuesday's meeting" is the meeting's day, never the reminder's (the eighth review)
    _at, weekday, before = next((f for f in found if f[2] in ("on", "by", "this", "next", "coming")),
                                next((f for f in found if f[2]), found[-1]))
    ahead = (_WEEKDAYS.index(weekday) - today.weekday()) % 7
    return today + timedelta(days=ahead + (7 if before == "next" else 0))


_REMIND_ON = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:can you\s+|could you\s+)?remind me to\s+(.+?)"
                        r"\s+(?:on\s+|this\s+|next\s+|this coming\s+)?(today|tonight|tomorrow|monday|tuesday|wednesday|"
                        r"thursday|friday|saturday|sunday)(?:\s+(?:morning|afternoon|evening|night))?"
                        r"(?:\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?\s*[.!]?\s*$", re.I)


# "remind me tomorrow at 9 to call the vet": the day and time first, said the other way round for _REMIND_ON
_REMIND_FIRST = re.compile(r"^(?P<lead>\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:can you\s+|could you\s+)?remind me)"
                           r"\s+(?P<when>(?:on\s+|this\s+|next\s+)?(?:today|tonight|tomorrow|monday|tuesday|wednesday|"
                           r"thursday|friday|saturday|sunday)(?:\s+(?:morning|afternoon|evening|night))?"
                           r"(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?)\s*,?\s+to\s+(?P<what>.+?)\s*[.!]?\s*$", re.I)


_EVERY = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_REMIND_EVERY = re.compile(
    r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?"
    r"(?:remind me (?:to\s+(?P<what1>.+?)\s+)?every\s+" + _EVERY + r"(?:\s+to\s+(?P<what2>.+?))?|"
    r"(?:automate|set up|add|make|create|schedule)\s+(?:a\s+)?(?:weekly\s+)?reminder\s+(?:for\s+)?every\s+"
    + _EVERY.replace("(", "(?P<day2>", 1) + r"\s+to\s+(?P<what3>.+?))"
    r"(?:\s+at\s+(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm)?)?\s*[.!?]?\s*$", re.I)


_REMIND_DAILY = re.compile(
    r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?remind me\s+"
    r"(?:(?:to\s+(?P<what1>.+?)\s+)?(?:every|each)\s+(?P<part>morning|day|night|evening|afternoon)|daily)"
    r"(?:\s+at\s+(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm)?)?(?:\s+to\s+(?P<what2>.+?))?"
    r"(?:\s+at\s+(?P<h2>\d{1,2})(?::(?P<m2>\d{2}))?\s*(?P<ap2>am|pm)?)?\s*[.!]?\s*$", re.I)


def _daily_reminder_reply(context, prompt: str):
    """"Remind me every morning to give the dog his meds", "remind me daily to check the water", in code (the
    eleventh review: it had no home, and the morning briefing took it): a daily event on his calendar from today,
    through add_calendar_event (undoable), at the time said ("at 7", in the evening for "night" or "evening"). None
    otherwise.
    "At 12" with no am or pm sets no time; two times, or a question in the title, are the model's.
    "At 12:30" keeps its time.
    "Every night at 12:30" is half past midnight; "every evening at 12:30" sets no time.
    "Every night at 2:30" is in the small hours; "every morning at 12:30" sets no time."""
    from datetime import date as _date

    found = _REMIND_DAILY.match(prompt.replace("’", "'"))
    if not found:
        return None
    what = (found.group("what1") or found.group("what2") or "").strip().rstrip(",")
    what = re.sub(r",?\s+(?:or|and|but)\s+(?:is|would|should|will|do|does|can)\b.*$", "", what, flags=re.I).strip()
    # an aside or a question is no part of it, nor a second time ("at 7 to take meds at 9": the twelfth review)
    if not what or "?" in what or re.search(r",\s*(?:is|was|do|does|should|would|can|could)\b", what, re.I) \
            or (found.group("h") and found.group("h2")) \
            or (re.search(r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", what, re.I) and (found.group("h") or found.group("h2"))):
        return None
    args = {"title": what[:1].upper() + what[1:], "date": _date.today().isoformat(), "recurrence": "daily"}
    hour_said, minute_said, ap = (found.group("h") or found.group("h2"), found.group("m") or found.group("m2"),
                                  (found.group("ap") or found.group("ap2") or "").lower())
    if hour_said and int(hour_said) == 12 and not ap and not minute_said:
        hour_said = None  # "every night at 12": noon or midnight? no time rather than a wrong one ("12:30" is kept)
    part = (found.group("part") or "").lower()
    if hour_said and int(hour_said) == 12 and not ap and part in ("evening", "morning"):
        hour_said = None  # "every evening at 12:30" isn't clear: no time rather than a wrong one
    if hour_said and int(hour_said) == 12 and not ap and part == "night":
        ap = "am"  # "every night at 12:30" is half past midnight (the fourteenth review: it had been noon)
    if hour_said and 1 <= int(hour_said) <= 4 and not ap and part == "night":
        ap = "am"  # "every night at 2:30" is in the small hours, never the afternoon (the fifteenth review)
    if hour_said:
        hour, minute = int(hour_said), int(minute_said or 0)
        later = ap == "pm" or (not ap and part in ("night", "evening", "afternoon"))
        hour += 12 if later and hour < 12 else 0
        hour = 0 if ap == "am" and hour == 12 else hour
        if hour < 24 and minute < 60:
            args["time"] = f"{hour:02d}:{minute:02d}"
    try:
        return context.assistant_actions.execute(context, "add_calendar_event", args)
    except Exception:
        log.exception("Couldn't put the daily reminder on the calendar")
        return None


_REMIND_MONTHLY = re.compile(
    r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?(?:"
    r"remind me (?:to|about)\s+(?P<what>.+?)\s+(?:every month|each month|monthly|once a month)|"
    r"remind me (?:every|each) month,?\s+to\s+(?P<what3>.+?)|"
    r"(?:every|each) month,?\s+remind me to\s+(?P<what2>.+?))"
    r"(?:\s+on the (?P<day>\d{1,2})(?:st|nd|rd|th)?)?\s*[.!]?\s*$", re.I)


def _monthly_reminder_reply(context, prompt: str):
    """"Remind me to change the furnace filter every month" (or "remind me every month to ..."), in code (the live
    sweep, 2026-11-25: the model called
    add_maintenance_task for a furnace he hasn't listed, and it was refused): a monthly event on his calendar, from
    today, or from the next day of the month he names ("on the 1st"), through add_calendar_event (undoable). None
    otherwise, and None for a bill (his bill tools remind him of those)."""
    from datetime import date as _date

    found = _REMIND_MONTHLY.match(prompt.replace("’", "'"))
    if not found:
        return None
    what = (found.group("what") or found.group("what2") or found.group("what3") or "").strip().rstrip(",")
    if not what or "?" in what or re.search(r"\b(?:pay|bills?|rent|mortgage|loan)\b", what, re.I) \
            or re.search(r"\b(?:every|each)\b", what, re.I):
        return None
    today = _date.today()
    start = today
    if found.group("day"):
        day = int(found.group("day"))
        if not 1 <= day <= 28:
            return None  # the 29th to the 31st aren't in every month: the model asks
        start = today.replace(day=day)
        if start < today:
            start = (start.replace(month=start.month % 12 + 1, year=start.year + (start.month == 12)))
    args = {"title": what[:1].upper() + what[1:], "date": start.isoformat(), "recurrence": "monthly"}
    try:
        return context.assistant_actions.execute(context, "add_calendar_event", args)
    except Exception:
        log.exception("Couldn't put the monthly reminder on the calendar")
        return None


def _weekly_reminder_reply(context, prompt: str):
    """"Remind me every Monday to check the water filter", "can you automate a reminder every Monday to ...", in code
    (live sweep, 2026-11-25: no tool was called, and the model promised a notification about the electric bill): a
    weekly event on his calendar from the next one of that weekday, through add_calendar_event (undoable). None
    otherwise.
    An aside (", or is that too much?") and a time said at its end ("at 9 tonight", "at noon") come out of the
    title."""
    from datetime import date as _date, timedelta

    found = _REMIND_EVERY.match(prompt.replace("’", "'"))
    if not found:
        return None
    what = (found.group("what1") or found.group("what2") or found.group("what3") or "").strip().rstrip(",")
    weekday = (found.group(2) or found.group("day2") or "").lower()
    # an aside or a question is no part of it (the tenth review: "..., or is that too much?" had been the title)
    what = re.sub(r",?\s+(?:or|and|but)\s+(?:is|would|should|will|do|does|can)\b.*$", "", what, flags=re.I).strip()
    if not what or not weekday or "?" in what:
        return None
    clock = re.search(r"\s+at\s+(noon|midnight|\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s+(tonight|in the (?:morning|"
                      r"afternoon|evening)|at night))?\s*$", what, re.I)
    if clock and not found.group("h"):  # "check the filter at 9 tonight", "at noon": the time, out of the title
        what = what[:clock.start()].strip()
        word, part = clock.group(1).lower(), (clock.group(4) or "").lower()
        hour = 12 if word == "noon" else 0 if word == "midnight" else int(word)
        if word.isdigit():
            ap = (clock.group(3) or "").lower()
            later = ap == "pm" or (not ap and any(w in part for w in ("tonight", "evening", "night", "afternoon")))
            hour += 12 if later and hour < 12 else 0
            hour = 0 if ap == "am" and hour == 12 else hour
        if hour < 24:
            found_time = f"{hour:02d}:{int(clock.group(2) or 0):02d}"
        else:
            found_time = ""
    else:
        found_time = ""
    today = _date.today()
    first = today + timedelta(days=(_WEEKDAYS.index(weekday) - today.weekday()) % 7)
    args = {"title": what[:1].upper() + what[1:], "date": first.isoformat(), "recurrence": "weekly"}
    if found_time:
        args["time"] = found_time
    if found.group("h"):
        hour, minute = int(found.group("h")), int(found.group("m") or 0)
        hour += 12 if (found.group("ap") or "").lower() == "pm" and hour < 12 else 0
        hour = 0 if (found.group("ap") or "").lower() == "am" and hour == 12 else hour
        if hour < 24 and minute < 60:
            args["time"] = f"{hour:02d}:{minute:02d}"
    try:
        return context.assistant_actions.execute(context, "add_calendar_event", args)
    except Exception:
        log.exception("Couldn't put the weekly reminder on the calendar")
        return None


def _reminder_reply(context, prompt: str):
    """"Remind me to check the oil Saturday", in code (live sweep, 2026-11-25: offered the alarms, the model called no
    tool and said "You've been reminded"): what and the day his words name (and a time, when said) go on his calendar
    through add_calendar_event, so it's undoable like any change of hers. A time with no day stays the alarms'; a
    repeating one ("every Saturday") the model's. None otherwise.
    "Tonight" or "evening" with an hour and no am or pm is the evening's.
    Evening only for "tonight" or a day's evening; "tonight at 12" sets no time.
    The day first is the same ("remind me tomorrow at 9 to call the vet", `_REMIND_FIRST`: the live sweep, where the
    model had written its alarm call out as text), its date from the day said first, never one in the task. An hour
    from 1 to 5 with no am, pm or morning is the afternoon ("tomorrow at 3").
    "Morning" counts only in the day and time, never in the task ("the morning glories"). Said the other way, the
    day is the one after the task, never one inside it ("remind me to send the invoice by Friday on Monday": the
    Fable review). A task ending on "before", "by", "and" or "or" is a deadline, the model's ("order feed before
    Friday": the cross-route review, 2026-11-26). A part of the day with no hour ("Saturday morning", "tonight") is
    that part's usual time: 8am, 2pm, 6pm, 8pm, never one already gone today ("tonight" said at 9pm sets no time)."""
    first = _REMIND_FIRST.match(prompt.replace("’", "'"))
    day_words = None
    if first:
        prompt = f"{first.group('lead')} to {first.group('what')} {first.group('when')}"
        day_words = first.group("when")  # the day he said first, never one in the task (the eighteenth review)
    found = _REMIND_ON.match(prompt.replace("’", "'"))
    if not found or re.search(r"\b(?:every|each)\b", found.group(1), re.I):
        return None
    if day_words is None:  # the day said after the task, never one inside it ("send the invoice by Friday on Monday")
        day_words = prompt.replace("’", "'")[found.end(1):]
    what = found.group(1).strip().rstrip(",")
    if re.search(r"\b(?:before|by|until|till|after|and|or|on|for)$", what, re.I):
        return None  # "order feed before Friday" is a deadline, not an event called "Order feed before" (cross-route review)
    args = with_his_day("add_calendar_event", {"title": what[:1].upper() + what[1:]}, day_words)
    evening = re.search(r"\btonight\b|\b(?:this|tomorrow|" + "|".join(_WEEKDAYS) + r")\s+(?:evening|night)\b", day_words,
                        re.I)  # never "night crawlers" or "game night saturday" (the eighth review)
    if "date" not in args:
        return None
    if found.group(3):
        hour, minute = int(found.group(3)), int(found.group(4) or 0)
        if evening and not found.group(5) and hour == 12:
            hour = 99  # "tonight at 12": noon or midnight? no time rather than a wrong one
        # "morning" in the day and time, never in the task ("check the morning glories saturday at 4", the nineteenth)
        morning = re.search(r"\bmorning\b", day_words, re.I)
        small = not found.group(5) and not morning and 1 <= hour <= 5  # "tomorrow at 3" is the afternoon (the eighteenth)
        hour += 12 if ((found.group(5) or "").lower() == "pm" or (evening and not found.group(5)) or small) \
            and hour < 12 else 0  # "tonight at 9" is 9 pm (the seventh review)
        hour = 0 if (found.group(5) or "").lower() == "am" and hour == 12 else hour
        if hour < 24 and minute < 60:
            args["time"] = f"{hour:02d}:{minute:02d}"
    else:  # "Saturday morning" with no hour: that part of the day's usual time (the fishing conversation check)
        part = re.search(r"\b(morning|afternoon|evening|night)\b", day_words, re.I)
        named = part.group(1).lower() if part else ("night" if re.search(r"\btonight\b", day_words, re.I) else "")
        from datetime import datetime as _now

        usual = {"morning": 8, "afternoon": 14, "evening": 18, "night": 20}.get(named)
        if usual is not None and str(args.get("date")) == _now.now().date().isoformat() and _now.now().hour >= usual:
            named = ""  # "tonight" at 9pm: never a time already gone (the Fable review)
        if named:
            args["time"] = {"morning": "08:00", "afternoon": "14:00", "evening": "18:00", "night": "20:00"}[named]
    try:
        return context.assistant_actions.execute(context, "add_calendar_event", args)
    except Exception:
        log.exception("Couldn't put the reminder on the calendar")
        return None


def _next_lesson_reply(context, prompt: str):
    """"What's my next guitar lesson?", read only, in code (core/assistant_path_actions.next_lesson_reply); None
    otherwise."""
    from core.assistant_path_actions import next_lesson_reply

    try:
        return next_lesson_reply(context, prompt)
    except Exception:
        log.exception("Couldn't say the next lesson")
        return None


# "...and 2 hours on the shed" inside what money was for: a second thing, never part of the first (_two_things_reply)
_AND_HOURS = re.compile(r"\band\s+(?:i\s+\w+(?:\s+in)?\s+)?(?:\d+(?:\.\d+)?|an?|one|two|three|four|five|six|seven|"
                        r"eight|nine|ten|eleven|twelve|half an?)(?: and a half)?\s*(?:hours?|hrs?|minutes?|mins?)\b",
                        re.I)
_AMOUNT = r"(?:\$\s?(?P<d>\d[\d,]*(?:\.\d{1,2})?)|(?P<n>\d[\d,]*(?:\.\d{1,2})?)\s*(?:dollars|bucks))"
_SPENT = re.compile(r"^\s*(?:i\s+)?(?:just\s+)?(?:spent|paid|dropped)\s+" + _AMOUNT + r"\s+(?:on|for)\s+(?P<what>.+?)"
                    r"\s*[.!]*\s*$", re.I)
_BOUGHT = re.compile(r"^\s*(?:i\s+)?(?:just\s+)?(?:bought|purchased)\s+(?P<what>.+?)\s+for\s+" + _AMOUNT +
                     r"\s*[.!]*\s*$", re.I)
# What it was for, by its words: the budget's categories (core/budget_manager.EXPENSE_CATEGORIES)
_SPENT_ON = (
    # the Fable review (2026-11-25): "chicken wire" and "the chicken coop" had been Groceries, "a board game" lumber
    ("Building Materials", r"\bchicken (?:coop|wire|run|tractor)\b|\bhardware cloth\b|\bfencing\b"),
    ("Entertainment", r"\b(?:board|video|card) games?\b"),
    ("Medical", r"\bhay fever\b|\ballerg\w*\b"),
    ("Groceries", r"\bchicken (?:breasts?|thighs?|wings?|legs?|drumsticks?|nuggets?|tenders?)\b|\bwhole chicken\b"),
    ("Animals & Feed", r"\b(?:feed|hay|straw|bedding|vet|chicks|scratch|oyster shell|dog food|cat food|kibble|goats?|"
                       r"(?:chicken|hen|goat|pig|pet|horse|rabbit) food|food for (?:the )?(?:dogs?|cats?|chickens|hens|"
                       r"goats|pigs|horses|rabbits|animals|pets)|pet supplies|"
                       r"horses?|pigs?|piglets?|livestock|lambs?|calf|calves)\b"),
    ("Groceries", r"\b(?:groceries|grocery|milk|bread|eggs|meat|produce|chicken|food|walmart|aldi|kroger|costco)\b"),
    ("Maintenance", r"\b(?:repairs?|fix(?:ing|ed)?|plumber|electrician|mechanic|parts)\b"),
    ("Transportation", r"\b(?:gas|fuel|diesel|gasoline|oil change|tires?|parking|toll)\b"),
    ("Building Materials", r"\b(?:lumber|2x\d+s?|plywood|screws|nails|concrete|fence|posts?|shingles|boards?)\b"),
    ("Tools & Equipment", r"\b(?:tools?|saw|drill|bits?|blade|clamps?|sander|router)\b"),
    ("Medical", r"\b(?:doctor|dentist|pharmacy|prescription|meds|medicine)\b"),
    ("Entertainment", r"\b(?:movie|movies|game|games|concert|streaming)\b"),
)
# A bill, rent, a loan, a card or a utility is a bill paid (mark_bill_paid and the debt tools), never a stray
# expense; money paid back isn't spending; a quote, an offer, a refund or a job is money that wasn't spent (the
# eleventh review: "I got a quote for $3,000" had been an expense)
_NOT_SPENDING = re.compile(r"\b(?:bills?|rent|loan|mortgage|card|insurance|invoice|deposit|back|internet|electricity|"
                           r"electric|phone bill|cable|utilit\w*|subscription|quote|offer|refund|raise|bonus)\b|"
                           r"\b(?:my|the) phone$|^(?:the|a|that) job$", re.I)  # his phone, or a job: his bill tools
# A person, not a thing: "I paid $100 for Sarah", "I spent $50 on him" (the twelfth review); a name counts only when
# it's someone he knows (`_known_person`), never Netflix, Costco or Uber (the thirteenth)
_A_PERSON = re.compile(r"(?:him|her|them|you|us|me|(?:my|the|our) (?:wife|husband|son|daughter|kid|kids|mom|dad|"
                       r"mother|father|brother|sister|friend|girlfriend|boyfriend|grandkids|grandson|granddaughter|"
                       r"parents|in-laws|nephew|niece|aunt|uncle|cousin|grandma|grandpa))", re.I)


def _known_person(context, words: str) -> bool:
    """Whether the words are only the name of someone in his people or his customers.
    A first name counts only written as a name (capitalized): "gas" is never Gas Station Co."""
    said = " ".join(str(words or "").split())
    full, first = set(), set()
    people = getattr(context, "relationships", None)
    named = [str(p.name) for p in (people.all_people() if people is not None and hasattr(people, "all_people") else [])]
    book = getattr(context, "business", None)
    named += [str(c.name) for c in (getattr(book, "customers", None) or [])]
    for name in named:
        full.add(name.lower())
        first.add(name.lower().split(" ")[0])
    # a first name only as he wrote a name, capitalized ("Sarah"): "gas" is never Gas Station Co (the fourteenth review)
    return bool(said) and (said.lower() in full or (said[:1].isupper() and said.lower() in first))
_SPENT_WHEN = re.compile(r"\s+(?:on\s+)?(yesterday|today|last week|(?:last\s+)?(?:monday|tuesday|wednesday|thursday|"
                         r"friday|saturday|sunday))$", re.I)


# What's left of "what it was for" that this route can't read whole (the Fable review, 2026-11-25): a day ("two days
# ago", "last night", "on the 20th", "November 20"), a debt or a payment ("my student loans", "the car payment",
# "the truck"), a retraction ("scratch that"), or money that fell ("on the floor")
_DAY_WORDS = (r"\b(?:ago|last|tonight|tomorrow|next|yesterday|on (?:monday|tuesday|wednesday|thursday|friday|"
              r"saturday|sunday)|january|february|march|april|june|july|august|september|october|november|december|"
              r"(?:on|in) (?:jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\b|the \d{1,2}(?:st|nd|rd|th)|"
              r"\d{1,2}/\d{1,2})\b")
# (Fable's check: "ground beef", "floor mats", "a week of groceries", "playing cards" are things bought)
_NOT_WHOLE = re.compile(_DAY_WORDS + r"|\b(?:loans?|(?:credit|debit|store|my|the) cards?|mortgages?|payments?|"
                        r"installments?|scratch that|never ?mind|actually|wait|post office|stamps)\b|"
                        r"^(?:the )?(?:floor|ground)$|^(?:the |my |our )?(?:truck|car|house|boat|van)$", re.I)
_DAY_LEFT = re.compile(_DAY_WORDS, re.I)


def _spent_reply(context, prompt: str):
    """"I spent $30 on groceries", "spent 12 dollars on gas", "bought 50 lb of layer feed for $22", in code (brainstorm
    round 14's sweep: the first went to the money month's plan and nothing was kept, the second got small talk, a
    third was only "Noted"): an expense through add_expense, in the budget's category its words name (feed, hay and
    the vet are Animals & Feed), undoable; feed with its weight goes to the flock's feed log (log_feed) when there's a
    flock. Never a question, a bill, rent, a loan, a card or money paid to a person (their own tools). None otherwise.
    Never a quote, an offer, a refund, "it" or two amounts at once; a repair is Maintenance, grocery chicken
    Groceries, goat feed never the hens', and "yesterday" dates it.
    Never money for a person ("for Sarah", "on him"); a weekday said after ("on Monday") is the one just gone.
    A name is a person only when he knows them (`_known_person`): Netflix and Costco are purchases; "last week" or a
    day alone is the model's to ask.
    The bill tools' words are checked again once a day said is cut off ("my phone yesterday"); family words (my
    mother, the kids) are people. Anything left it can't read whole (`_NOT_WHOLE`: another day, a debt, a
    retraction) is the model's (the Fable review). Money paid for one of his bills ("I paid $85 for propane") is that
    bill's to mark paid, never a stray expense (the cross-route review). A second thing after "and" ("...and 2 hours
    on the shed", `_AND_HOURS`) is never part of what it was for: the sentence is `_two_things_reply`'s."""
    said = prompt.replace("’", "'").strip()
    found = _SPENT.match(said) or _BOUGHT.match(said)
    if not found or "?" in said:
        return None
    what = found.group("what").strip().rstrip(",.")
    if _NOT_SPENDING.search(what) or re.search(r"\$\s?\d|\b\d+\s*(?:dollars|bucks)\b", what, re.I) \
            or re.fullmatch(r"(?:it|that|this|them|one)", what, re.I) or _AND_HOURS.search(what):
        return None  # two amounts in one ("$5 on a coffee and $10 on gas") are the model's to split
    when = _SPENT_WHEN.search(" " + what)
    day = ""
    if when:  # "spent $30 on groceries yesterday": its day, out of what it was for
        from core.budget_manager import read_date

        said_day = when.group(1).lower()
        if said_day == "last week":
            return None  # which day? the model asks, never today by default (the thirteenth review)
        if re.fullmatch(r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)", said_day):
            said_day = "last " + said_day  # "gas on Monday", said after: the Monday just gone
        day = read_date(said_day) or ""
        what = (" " + what)[:when.start()].strip()
        if _NOT_SPENDING.search(what):
            return None  # "my phone yesterday" is still his phone's bill (the fourteenth review)
    if not what or _A_PERSON.fullmatch(what) or _known_person(context, what):
        return None  # "spent $30 on Monday" names no thing; money for a person is a gift or a debt, not this
    if _NOT_WHOLE.search(what):
        return None  # a day it doesn't read, a debt, a retraction or a dropped bill: the model's (the Fable review)
    amount = float((found.group("d") or found.group("n")).replace(",", ""))
    if amount <= 0:
        return None
    category = next((c for c, words in _SPENT_ON if re.search(words, what, re.I)), "Other")
    weight = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds?)\b", what, re.I)
    flock = getattr(context, "flock", None)
    try:
        poultry = not re.search(r"\b(?:goats?|horses?|pigs?|hogs?|cattle|cows?|rabbits?|dogs?|cats?|sheep|llamas?|"
                                r"alpacas?)\b", what, re.I)
        if category == "Animals & Feed" and weight and re.search(r"\bfeed\b", what, re.I) and poultry \
                and flock is not None and getattr(flock, "flocks", None):  # goat feed never counts for the hens
            return context.assistant_actions.execute(context, "log_feed", {"pounds": float(weight.group(1)),
                                                                           "cost": amount})
        budget = getattr(context, "budget", None)
        bills = budget.all_bills() if budget is not None and hasattr(budget, "all_bills") else []
        thing = re.sub(r"^(?:the|my|our)\s+", "", what.lower()).strip()
        if any(thing and (thing == b.name.lower() or thing + " bill" == b.name.lower() or b.name.lower() in (thing,
                                                                                               thing.rstrip("s")))
               for b in bills):
            return None  # a bill of his: marking it paid is the bill tool's (the model's), never a stray expense
        args = {"amount": amount, "category": category, "description": what[:1].upper() + what[1:]}
        if day:
            args["date"] = day
        return context.assistant_actions.execute(context, "add_expense", args)
    except Exception:
        log.exception("Couldn't record what he spent")
        return None


def _morning_briefing_reply(context, prompt: str):
    """"Every morning at 7, tell me the weather and my day", "stop the morning briefing", in code
    (core/morning_briefing.reply); None otherwise."""
    from core import morning_briefing

    try:
        return morning_briefing.reply(context, prompt)
    except Exception:
        log.exception("Couldn't set the morning briefing")
        return None


def _job_quote_reply(context, prompt: str):
    """"Write a quote for Sarah's 12 by 16 deck", in code (core/job_quote.reply: the calculators' list, priced from
    the workshop, a draft quote for his yes); None otherwise, and None when a price, labor, a second job, his own
    build or a repair is said with it (the draft would drop them)."""
    from core import job_quote

    # a price, labor, two jobs, his own build or a repair said with it are the model's: the draft would drop them
    # (the Fable review, 2026-11-25)
    if re.search(r"\$\s?\d|\b\d+\s*(?:an|per|/)\s*(?:hour|hr)\b|\blabou?r\b|\bhours?\b|\band an? \d|\band (?:a|the) "
                 r"\d+\s*(?:by|x|foot|ft)|\bi (?:want|plan|need) to build\b|\bmy own\b|\bfor me\b|\brepairs?\b|"
                 r"\bfix\w*\b", prompt, re.I):
        return None
    try:
        return job_quote.reply(context, prompt)
    except Exception:
        log.exception("Couldn't draft the quote")
        return None


_DUE = re.compile(r"^\s*when(?:'s| is| are|s)?\s+(?:my|the|our)\s+(?P<asset>[\w' -]+?)\s+(?:due|next due)\s+for\s+"
                  r"(?:a\s+|an\s+|its\s+|the\s+|new\s+)?(?P<task>[\w' -]+?)\s*\??\s*$", re.I)
_NEEDS = re.compile(r"^\s*(?:my\s+|the\s+|our\s+)(?P<asset>[\w' -]+?)\s+needs\s+(?:a\s+|an\s+|new\s+|its\s+)?"
                    r"(?P<what>[\w' ,-]+?)\s*[.!]?\s*$", re.I)  # "its 30,000 mile service"
# what a need never is: a repeat, a day, a number, a question word, or no task at all (the fifteenth review)
_NOT_A_TASK = re.compile(r"^\s*(?:gas|fuel|gasoline|diesel|work)\s*$|\d+\s*(?:days?|weeks?|months?|years?|st|nd|rd|th)\b|"
                         r"\b(?:to|be|more|some|every|each|soon|today|tomorrow|tonight|next|this|week|month|year|"
                         r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|nothing|it|that|them|"
                         r"how|what|when|why|where|anything|something|help|"
                         # a time, a remark or a list (the seventeenth review: "tires in the spring", "wipers,
                         # badly", "an oil change, a new filter", "3 quarts of oil")
                         r"in|on|at|before|after|by|for|of|with|from|and|or|but|asap|badly|lot|really|again|"
                         r"quarts?|gallons?|liters?)\b|,\s|^(?:\S+\s+){5,}", re.I)
_FILLER = {"new", "the", "its", "his", "her", "our", "and", "replace", "replacement", "replaced"}
# What a need is added from: an upkeep job by name, never any noun after "needs" (the Fable review, 2026-11-25:
# "the truck needs no work", "my truck needs me", "the truck needs a name" had each become a task)
_UPKEEP_JOB = re.compile(r"\b(?:oil|filters?|brakes?|brake pads?|rotors?|tires?|tyres?|battery|batteries|wipers?|"
                         r"wiper blades?|tune-?up|belts?|spark plugs?|plugs?|rotation|alignment|inspection|service|"
                         r"servicing|coolant|antifreeze|transmission|fluid|grease|lube|bearings?|blades?|sharpen\w*|"
                         r"gutters?|caulk\w*|paint\w*|seal\w*|shingles?|roof|chimney|furnace|hoses?|chain|bar oil|"
                         r"air filter|fuel filter|shocks?|struts?|muffler|exhaust|headlights?|bulbs?|registration|"
                         r"tags?|emissions|smog|winteriz\w*|flush|gas cap|caps?|(?:body|brake|engine|paint) work|"
                         r"pump|gauge|fuel \w+|starter|alternator|radiator|thermostat|tune ?up|clutch|windshield|"
                         r"glass|wheel bearings?|u-?joints?|ball joints?|tie rods?|axle|cv joints?)\b", re.I)


def _assets(context) -> list:
    """His maintenance assets' names, lowercased."""
    book = getattr(context, "maintenance", None)
    return [str(a.name).lower() for a in (book.all_assets() if book is not None and hasattr(book, "all_assets") else [])]


def _task_line(context, asset: str, task: str, same: bool = False):
    """The line for that asset's task from his maintenance ("Oil Change (Truck): due in 3 days"), its own asset only
    (the fifteenth review: "truck" lists every vehicle, and the Car's oil change had been said for the truck); None
    when there's none.
    `same`: for a need, only the same task (whole words of the title, a plural as its one), never one sharing a
    word.
    Words are matched by their stems ("a tire rotation" is Rotate Tires), "replace" and "new" left out."""
    listed = context.assistant_actions.execute(context, "list_maintenance_tasks", {"query": asset})

    def words(text):
        """Its words' stems: a plural as its one, a long word by its first five letters ("rotation", "rotated"
        and "rotate" are one), "replace" and "new" left out ("new brake pads" is Replace Brake Pads)."""
        stems = set()
        for w in re.findall(r"[a-z]{3,}", text.lower()):
            if w in _FILLER:
                continue
            w = w[:-1] if len(w) > 3 and w.endswith("s") else w
            stems.add(w[:5])
        return stems

    said = words(task)
    for ln in str(listed).splitlines():
        line = ln.lstrip("- ").strip()
        title, _, rest = line.partition(" (")
        if not said or not rest.lower().startswith(f"{asset.lower()}):"):
            continue
        # asked when it's due, his words among the title's ("tags": Renew Tags); a need already listed only as the
        # same task ("a new battery" is never the Battery check, the sixteenth review)
        if (said == words(title)) if same else said <= words(title):
            return line
    return None


def _upkeep_reply(context, prompt: str):
    """His upkeep in code (the live sweep, 2026-11-25): "when is my truck due for an oil change?" is that task's line
    from his own maintenance (the model had asked for the truck's make and model, or added a task); "the truck needs
    new brakes" adds the task for that asset (it had tried to mark one complete), only when the asset is one of his.
    None otherwise.
    The line is that asset's own (`_task_line`); a need already listed is said, never added twice, and a remark, a
    repeat, a date or a non-task (`_NOT_A_TASK`) is the model's.
    A part or a mileage is a real need ("a new fuel filter", "its 30,000 mile service"); only a lone "gas" or "work"
    isn't.
    A need is added only for an upkeep job by name (`_UPKEEP_JOB`), never "needs me" or "needs a name" (the Fable
    review)."""
    assets = _assets(context)
    said = prompt.replace("’", "'")
    found = _DUE.match(said)
    if found and found.group("asset").lower() in assets:
        line = _task_line(context, found.group("asset"), found.group("task"))
        if line is None:
            return None
        tail = (" Log its reading (its miles or hours) and I'll say when it's due."
                if "no readings" in line.lower() else "")
        return f"{line}.{tail}"
    found = _NEEDS.match(said)
    if found and found.group("asset").lower() in assets and not _NOT_A_TASK.search(found.group("what")) \
            and _UPKEEP_JOB.search(found.group("what")) \
            and not re.search(r"\b(?:i think|maybe|probably|no|me|you|him|her|name|bigger|smaller)\b", found.group("what"),
                              re.I):
        title = found.group("what").strip()
        line = _task_line(context, found.group("asset"), title, same=True)
        if line is not None:
            return f"That's already on your list: {line}."  # never a second one (the fifteenth review)
        return context.assistant_actions.execute(context, "add_maintenance_task", {
            "asset_name": found.group("asset"), "title": title[:1].upper() + title[1:]})
    return None


_LED = re.compile(r"\bresistor\b.{0,40}\bleds?\b.{0,30}?\b(\d+(?:\.\d+)?)\s*(?:v|volts?)\b|"
                  r"\bleds?\b.{0,30}?\b(\d+(?:\.\d+)?)\s*(?:v|volts?)\b.{0,30}\bresistor\b", re.I)


def _led_reply(context, prompt: str):
    """"What resistor do I need for an LED on 5 volts?", worked out in code (core/eng_calcs led_resistor: the live
    sweep's model answer had its formula backwards): for a red LED (about 2 V) and a white or blue one (about 3.1 V),
    at 20 mA, rounded up to a stock value. None otherwise.
    Only the plain question: a forward voltage, two voltages, ohms, current, several LEDs or a strip are the
    model's; mains is a warning, and over a quarter watt of heat says to use a 1/2 W resistor.
    A current in mA or several LEDs in words are the model's; mains is over 50 V or said; the resistor is rated
    twice its heat.
    The note gives the rating only, never a heat figure that disagrees with the stock resistor's."""
    found = _LED.search(prompt)
    if not found:
        return None
    # only the plain question (the fifteenth review): a forward voltage or two voltages said, a resistor he has, the
    # current asked, several LEDs or a strip are the model's
    if (re.search(r"\b(?:forward|vf|ohms?|current|amps?|milliamps?|series|parallel|strips?|\d+\s*ma|"
                  r"(?:\d+|two|three|four|five|six|several|multiple|many)\s+leds)\b|\u03a9", prompt, re.I)
            or len(re.findall(r"\d+(?:\.\d+)?\s*(?:v|volts?)\b", prompt, re.I)) > 1):
        return None
    supply = float(found.group(1) or found.group(2))
    if supply > 50 or re.search(r"\bmains\b", prompt, re.I):  # a 5 V wall adapter is no mains (the sixteenth review)
        return ("Don't run an LED from mains through a resistor alone: the resistor would burn (watts of heat), the "
                "LED needs protecting from the reverse half of AC, and it's a shock hazard. Use a bulb or LED made for "
                "mains, or a low-voltage supply (5 or 12 V DC) with a resistor.")
    from core import eng_calcs

    said = []
    for color, forward in (("a red", 2.0), ("a white or blue", 3.1)):
        if supply <= forward:
            continue
        try:
            result = eng_calcs.calculate("led_resistor", {"supply": f"{supply:g} V", "forward": f"{forward:g} V",
                                                          "current": "20 mA"})
        except Exception:  # noqa: BLE001 - a calculation that can't be done is the model's
            return None
        said.append(f"for {color} LED (about {forward:g} V), {result['said'].rstrip('.')}")
        heat = (supply - forward) * 0.02
        rating = next(r for r in (0.25, 0.5, 1, 2, 3, 5) if r >= 2 * heat)  # rated twice its heat
        if rating > 0.25:
            said[-1] += f" (use a {'1/2' if rating == 0.5 else f'{rating:g}'} W resistor)"
    if not said:
        return None
    return ("At 20 mA, " + "; ".join(said) + ". R = (supply - the LED's forward voltage) / current: check your LED's "
            "own forward voltage and current on its datasheet.")


_SPENT_ON_ASK = re.compile(r"^\s*how much (?:money )?(?:did|have) (?:i|we) (?:spend|spent|spended) on (?P<what>[\w&' -]+?)"
                           r"(?:\s+(?P<when>(?:so far )?(?:this|last) (?:week|month|year)|today|yesterday|so far|"
                           r"(?:in|for|during) (?:january|february|march|april|may|june|july|august|september|october|"
                           r"november|december)(?:,? \d{4})?))?\s*\??\s*$", re.I)


_PLANT_WHEN = re.compile(r"^\s*when\s+(?:should|do|can|would)\s+(?:i|we)\s+(?:start|plant|sow|transplant|put out|set out)"
                         r"\b(?P<rest>.+?)\s*\??\s*$", re.I)
_PLANT_NOW = re.compile(r"^\s*what (?:should|can|could|do) (?:i|we) (?:plant|sow|grow|start (?:planting|seeds|in the "
                        r"garden|now|this month|indoors))(?: (?:now|in the spring|this "
                        r"spring|this month|this week|next|soon|in the garden|this time of year))?\s*\??\s*$", re.I)
_KIT_ASK = re.compile(r"^\s*(?:what\s+(?:should|would|do i|goes|do you)\s+(?:be\s+|go\s+|i\s+(?:put|pack|have|keep|need)\s+|"
                      r"need\s+|put\s+|pack\s+)?(?:in|into|for)\s+|check\s+|am i missing\s+(?:anything\s+)?(?:from|in|for)?\s*)"
                      r"(?:a|an|my|the|our)?\s*(?:72[- ]?hour|go[- ]?|bug[- ]?out|emergency|disaster|get[- ]home)\s*(?:bag|kit)s?"
                      r"\s*\??\s*$", re.I)


def _garden_kit_reply(context, prompt: str):
    """Two of hers the model passed over (the live sweep, 2026-11-25: it answered from what it knew, with a made-up
    frost date, and asked him to log a kit): "when should I start my tomato seeds?" is that crop's dates from his
    own last frost (core/planting_now.say_crop), and "what should be in a 72 hour bag?" the kit against his records
    (core/ready_kit.say). None otherwise, or for a crop she has no dates for.
    Never "when should I start selling tomatoes?" (a verb after start), and the kit only when what's in it is asked.
    Spring and string are crops' words, never a verb ("start spring peas").
    "What should I plant in the spring?" is what's due to plant from his frost (core/planting_now.say_now,
    `_PLANT_NOW`); "when should I plant garlic?" is fall's, from his first frost (planting_now.say_garlic); "my last
    frost is April 20" is kept as his frost date (planting_now.keep_frost)."""
    found = _PLANT_WHEN.match(prompt)
    try:
        from core import planting_now as _planting

        kept = _planting.keep_frost(context, prompt)  # "my last frost is April 20": kept, then what's due from it
        if kept is not None:
            return kept
        if _PLANT_NOW.match(prompt):  # "what should I plant in the spring?": what's due from his frost (the live sweep)
            from core import planting_now

            return planting_now.say_now(context)
        if found and re.match(r"\s*(?!spring\b|string\b)\w+ing\b", found.group("rest")) and not re.match(r"\s*(?:my|the|our)\b",
                                                                                     found.group("rest")):
            return None  # "when should I start selling tomatoes?" is no planting date (the eighteenth review)
        if found:
            from core import planting_now

            if re.search(r"\bgarlic\b(?!\s+(?:chives|mustard))", found.group("rest"), re.I):  # fall-planted: his first frost
                return planting_now.say_garlic(context)
            return planting_now.say_crop(context, found.group("rest")) if planting_now.crop_named(found.group("rest")) \
                else None
        if _KIT_ASK.match(prompt):
            from core import ready_kit

            return ready_kit.say(context)
    except Exception:
        log.exception("Couldn't answer the garden's dates or the kit")
    return None


_TIME_ON = (
    re.compile(r"^\s*(?:please\s+)?(?:log|put down|add|record|track)\s+" + r"(?P<h>(?:\d+(?:\.\d+)?|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half an?)(?: and a half)?\s*(?:hours?|hrs?|minutes?|mins?)(?: and a half)?)" + r"\s+(?:on|to|for|into)\s+(?P<p>.+?)"
               r"(?:\s+(?P<day>today|yesterday))?\s*[.!]?\s*$", re.I),
    re.compile(r"^\s*i\s+(?:just\s+)?(?:worked|spent|put in|put)\s+" + r"(?P<h>(?:\d+(?:\.\d+)?|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half an?)(?: and a half)?\s*(?:hours?|hrs?|minutes?|mins?)(?: and a half)?)" + r"\s+(?:on|into|at)\s+(?P<p>.+?)"
               r"(?:\s+(?P<day>today|yesterday))?\s*[.!]?\s*$", re.I),
    re.compile(r"^\s*i\s+worked\s+on\s+(?P<p>.+?)\s+for\s+" + r"(?P<h>(?:\d+(?:\.\d+)?|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half an?)(?: and a half)?\s*(?:hours?|hrs?|minutes?|mins?)(?: and a half)?)" + r"(?:\s+(?P<day>today|yesterday))?\s*[.!]?\s*$", re.I),
)
_HOURS_ASK = re.compile(r"^\s*how many hours (?:have|did) (?:i|we) (?:put|spent|spend|logged|log|worked)\s+(?:in\s+)?"
                        r"(?:into|on|in)\s+(?P<p>.+?)\s*\??\s*$", re.I)
_WORKED_ASK = re.compile(r"^\s*what (?:did|have) i (?:work|been working) on\s+(?P<when>today|yesterday|this week|last week)"
                         r"\s*\??\s*$", re.I)


def _project_time_reply(context, prompt: str):
    """The hours he puts into his projects, in code (the live sweep, 2026-11-25: "log 2 hours on the shed build" had
    been a maintenance reading, and "what did I work on yesterday?" read as his workouts): "log 2 hours on the shed",
    "I spent 3 hours on the deck yesterday" or "I worked on the coop for an hour" run log_project_time, only for a
    project of his (core/project_time.project_named); "how many hours have I put into the shed?" and "what did I work
    on this week?" run project_hours. "Log 2 hours on" something that's neither a project nor one of his machines is
    said as no such project, with his projects' names, only when the words say it's a project ("the shed build"); a
    machine's ("the mower") stays its engine hours, and an oven timer or guitar practice is never one. A day it
    doesn't read is the model's (the Fable review). Money in the project's words ("the shed and $40 on screws") is
    `_two_things_reply`'s, never one project's hours. None otherwise."""
    from core import project_time
    from core.budget_manager import read_date

    said = prompt.replace("’", "'")
    actions = getattr(context, "assistant_actions", None)
    if actions is None:
        return None
    try:
        for n, pattern in enumerate(_TIME_ON):
            found = pattern.match(said)
            if found and _DAY_LEFT.search(found.group("p")):
                return None  # "on the deck on Saturday", "two days ago": a day it doesn't read is the model's
            if found and re.search(r"\$\s?\d|\b\d+\s*(?:dollars|bucks)\b", found.group("p"), re.I):
                return None  # "2 hours on the shed and $40 on screws": both halves are _two_things_reply's
            if found and n == 0 and project_time.project_named(context, found.group("p")) is None \
                    and re.search(r"\b(?:build|project|job|remodel|rewire|renovation|reno|addition)\b", found.group("p"),
                                  re.I):
                named = project_time._words(found.group("p"))
                if not any(named & project_time._words(a) for a in _assets(context)):
                    # "log 2 hours on the shed build" with no such project: said so with his projects, never a
                    # machine's hours (the live check); "log 2 hours on the mower" stays its engine's reading
                    return actions.execute(context, "log_project_time", {"project": found.group("p"), "hours": 1})
            if found and project_time.project_named(context, found.group("p")) is not None:
                hours = project_time.hours_said(found.group("h"))
                if not hours or hours > 24:
                    return None
                args = {"project": found.group("p"), "hours": hours}
                if (found.group("day") or "").lower() == "yesterday":
                    args["date"] = read_date("yesterday") or ""
                return actions.execute(context, "log_project_time", args)
        found = _HOURS_ASK.match(said)
        if found and project_time.project_named(context, found.group("p")) is not None:
            return actions.execute(context, "project_hours", {"project": found.group("p")})
        found = _WORKED_ASK.match(said)
        if found:
            return actions.execute(context, "project_hours", {"period": found.group("when").lower()})
    except Exception:
        log.exception("Couldn't log or read his project hours")
    return None


_TWO_THINGS = re.compile(
    r"^\s*(?P<left>.+?)\s*,?\s+and\s+(?:then\s+)?(?P<right>(?:i\s+(?:also\s+)?(?:just\s+)?(?:spent|paid|dropped|bought|"
    r"purchased|worked|put in|put|logged)\s.+|(?:also\s+)?(?:\$\s?\d|\d[\d,.]*\s*(?:dollars|bucks|hours?|hrs?|minutes?|"
    r"mins?)\b|\d+(?:\.\d+)? and a half (?:hours?|hrs?)\b|(?:an?|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|half an?)(?: and a half)?\s+(?:hours?|hrs?|minutes?|mins?)\b).*))$", re.I)


def _one_thing(context, clause: str) -> str:
    """Pure logic. Which of her two logging routes a clause is whole for: "money" ("I spent $40 on screws"), "time"
    ("I spent 2 hours on the shed", a day it reads), or "" for neither."""
    found = _SPENT.match(clause) or _BOUGHT.match(clause)
    if found and "?" not in clause and not re.search(r"\$\s?\d|\b\d+\s*(?:dollars|bucks)\b", found.group("what"),
                                                     re.I) and not _AND_HOURS.search(found.group("what")):
        return "money"
    for pattern in _TIME_ON:
        found = pattern.match(clause)
        if found and not re.search(r"\$\s?\d", found.group("p")) and not _DAY_LEFT.search(found.group("p")):
            return "time"
    return ""


def _no_such_project(context, clause: str):
    """The hours half `_project_time_reply` turned down: log_project_time's own answer (no such project, and his
    projects' names; nothing kept) only when the words say it's a project ("the porch build") and it isn't one of his;
    a project of his it turned down (30 hours), "the phone", "hold" or one of his machines ("the mower") handed back
    as None (the Fable review, 2026-11-26)."""
    from core import project_time

    for pattern in _TIME_ON:
        found = pattern.match(clause)
        if found:
            if project_time.project_named(context, found.group("p")) is not None or not re.search(
                    r"\b(?:build|project|job|remodel|rewire|renovation|reno|addition)\b", found.group("p"), re.I):
                return None
            named = project_time._words(found.group("p"))
            if any(named & project_time._words(a) for a in _assets(context)):
                return None
            return context.assistant_actions.execute(context, "log_project_time",
                                                     {"project": found.group("p"), "hours": 1})
    return None


def _two_things_reply(context, prompt: str):
    """Two things in one sentence (brainstorm round 18): "I spent $40 on screws and 2 hours on the shed", "I paid $5
    for coffee and $10 for gas", each half through its own code (an expense by `_spent_reply`, a project's hours by
    `_project_time_reply`) and said back together. A half with no verb takes "I spent"; a day said at the end
    ("...yesterday", or one after the first half) is both halves', never added beside another day. Never a question.
    Only when both halves are whole for one of them; if one is then turned down (a
    bill of his, a person), the other's record is said and that half handed back in his words, never dropped; hours on
    no project of his are said as that, with his projects (`_no_such_project`). None otherwise."""
    said = (prompt or "").replace("’", "'").strip()
    found = _TWO_THINGS.match(said)
    if not found or "?" in said or getattr(context, "assistant_actions", None) is None:
        return None  # "...on the shed, right?" is a question, never two records
    left = found.group("left").strip().rstrip(",")
    right = re.sub(r"^also\s+", "", found.group("right").strip(), flags=re.I)
    right = re.sub(r"^i\s+also\s+", "I ", right, flags=re.I)
    if not re.match(r"^i\s", right, re.I):
        verb = re.match(r"^\s*(?:i\s+)?(?:just\s+)?(spent|paid|dropped)\b", left, re.I)
        money = re.match(r"^(?:\$|\d[\d,.]*\s*(?:dollars|bucks)\b)", right, re.I)
        right = f"I {verb.group(1).lower() if verb and money else 'spent'} {right}"  # "paid $85 ... and $40 ..."
    day = re.search(r"\s+(today|yesterday)\s*[.!]*\s*$", right, re.I)
    if day and not _DAY_LEFT.search(left) and not re.search(r"\btoday\b", left, re.I):
        left = f"{left} {day.group(1)}"  # "...and 2 hours on the shed yesterday": both were yesterday
    left_day = re.search(r"\s+(today|yesterday)\s*$", left, re.I)
    if left_day and not day and not _DAY_LEFT.search(right):
        right = f"{right.rstrip('.! ')} {left_day.group(1)}"  # "screws yesterday and 2 hours on the shed"
    kinds = [_one_thing(context, left), _one_thing(context, right)]
    if not all(kinds):
        return None
    replies = []
    for clause, kind in zip((left, right), kinds):
        reply = _spent_reply(context, clause) if kind == "money" else _project_time_reply(context, clause)
        if reply is None and kind == "time":
            reply = _no_such_project(context, clause)
        replies.append((clause, reply))
    kept = [r for _c, r in replies if r]
    if not kept:
        return None
    left_out = [c for c, r in replies if not r]
    return " ".join(kept) + "".join(f' I didn\'t keep "{c}": say it on its own and I\'ll sort it out.'
                                    for c in left_out)


_MAINS = re.compile(r"^(?!.*\b(?:power bill|outlet mall|outlet store|solar panels?|breaker list)\b)(?=.*\b(?:check|test|"
                    r"measure|read)\w*\b)(?=.*\b(?:voltage|volts|power|live|wired|wiring)\b)(?=.*\b(?:outlets?|sockets?|"
                    r"receptacles?|breakers?|breaker panel|electrical panel|panel|wall plugs?|mains)\b)|"
                    r"\b(?:outlets?|sockets?|receptacles?|breakers?|mains)\b.{0,40}\b(?:check|test|measure|read)\w*\b"
                    r".{0,40}\b(?:voltage|volts|power|live)\b|\bis (?:the|this|my|an?) (?:outlet|socket|wire) live\b|"
                    r"\b(?:check|test|tell)\w*\b.{0,20}\b(?:outlets?|sockets?|receptacles?)\b.{0,20}\b(?:live|hot|wired|"
                    r"working|has power|getting power)\b",
                    re.I)
MAINS_REPLY = ("The safe way to check an outlet: a plug-in outlet tester (its lights say whether it's live and wired "
               "right), or a non-contact voltage tester held near it, which beeps at a live wire without touching it. "
               "A multimeter on an outlet means touching live mains: only with a meter rated CAT II or higher, set to AC "
               "volts, probes with finger guards, one hand where you can. If anything reads wrong, or there's heat, "
               "buzzing or a burning smell, switch that breaker off and call an electrician.")


def _mains_reply(context, prompt: str):
    """"How do I check the voltage at an outlet?", in fixed words (the live sweep, 2026-11-25: the model walked him
    through a multimeter on a live outlet, setting it to "V or \u03a9"): a plug-in outlet tester or a non-contact
    tester first, a meter only rated for mains, and the breaker and an electrician when anything's off. None
    otherwise, and None for a vehicle's or a trailer's wiring (never the house's mains)."""
    if re.search(r"\b(?:truck|trailer|car|camper|rv|vehicle|boat|tractor)\b", prompt or "", re.I):
        return None  # a 12-volt outlet or trailer lights aren't the house's mains (cross-route review)
    return MAINS_REPLY if _MAINS.search(prompt or "") else None


_CONVERT = re.compile(r"^\s*(?:please\s+)?(?:convert|change|turn)\s+(?P<v>\d[\d,]*(?:\.\d+)?)\s*(?P<f>[a-z°][\w° .-]*?)\s+"
                      r"(?:to|into|in)\s+(?P<t>[a-z°][\w° .-]*?)\s*[.?!]?\s*$|"
                      r"^\s*how many\s+(?P<t2>[a-z°][\w° .-]*?)\s+(?:are |is )?in\s+(?:a\s+|an\s+)?(?P<v2>\d[\d,]*(?:\.\d+)?)?"
                      r"\s*(?P<f2>[a-z°][\w° .-]*?)\s*\??\s*$|"
                      r"^\s*what(?:'s| is)\s+(?P<v3>\d[\d,]*(?:\.\d+)?)\s*(?P<f3>[a-z°][\w° .-]*?)\s+in\s+"
                      r"(?P<t3>[a-z°][\w° .-]*?)\s*\??\s*$", re.I)


_FISH_WHEN = re.compile(r"\b(?:when(?:'s|s| is)?|what(?:'s| is))\s+(?:a\s+|the\s+)?(?:good|best|right)\s+time\s+(?:of\s+day\s+)?"
                        r"to\s+(?:go\s+)?fish(?:ing)?\b|\bbest time (?:of day )?to (?:go )?fish|\bwhen should i (?:go )?"
                        r"fish(?:ing)?\b|\bshould i (?:go )?fish(?:ing)? (?:today|tomorrow|this weekend|this morning|"
                        r"tonight)\b", re.I)


def _fish_when_reply(context, prompt: str):
    """"When's a good time to fish?", from his own catch log and today's weather (core/catch_log.best_time); None
    otherwise.
    Never a note to keep, "compliments", or a place that isn't his water ("in florida").
    A place is a capitalised name or a state, never "in the pond" or "in winter"."""
    said = str(prompt or "")
    if not _FISH_WHEN.search(said):
        return None
    # never a note to keep, a figure of speech, or a place that isn't his water (the Fable review: "in florida" is the
    # model's, never his own log's)
    if re.match(r"\s*(?:add|note|remind|log|save|write)\b", said, re.I) or re.search(r"\bcompliments?\b", said, re.I) \
            or re.search(r"\bin (?:[A-Z][a-z]+|alabama|alaska|arizona|arkansas|california|colorado|florida|georgia|"
                         r"idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|michigan|minnesota|"
                         r"mississippi|missouri|montana|nebraska|nevada|ohio|oklahoma|oregon|texas|utah|vermont|virginia|"
                         r"washington|wisconsin|wyoming|canada|mexico)\b", said):
        return None
    from core import catch_log

    try:
        return catch_log.best_time(context)
    except Exception:
        log.exception("Couldn't say when to fish")
        return None


_TIME_NOW = re.compile(r"^\s*(?:hey\s+mia[,:]?\s+)?(?:what(?:'s| is)? (?:the )?time(?: is it)?(?: (?:now|right now))?|what time "
                       r"is it(?: (?:now|right now))?|(?:do you know )?what time it is|what(?:'s| is) (?:the |today'?s )?"
                       r"date(?: today)?|what day is (?:it|today)|what(?:'s| is) today)\s*\??\s*$", re.I)
_DAYS_UNTIL = re.compile(r"^\s*how (?:many|much) (?P<unit>days|weeks|time)(?: is it| are there| left| do i have)? (?:until|"
                         r"till|til|to)\s+(?P<what>.+?)\s*\??\s*$", re.I)
_NUM = r"\d[\d,]*(?:\.\d+)?"
_AREA = re.compile(r"\b(?:square (?:footage|feet|foot)|sq\.? ?ft)\b.{0,25}?(?<![\d,.])(?P<a>" + _NUM + r")\s*(?:'|ft|feet|foot)?\s*"
                   r"(?:by|x)\s*(?P<b>" + _NUM + r")\b|(?<![\d,.])(?P<a2>" + _NUM + r")\s*(?:by|x)\s*(?P<b2>" + _NUM +
                   r")\b.{0,25}\b(?:in square feet|square (?:footage|feet)|sq\.? ?ft)\b", re.I)
# a measure that isn't feet, a quote, lumber or a rug's size is the model's (the Fable review)
_NOT_AREA = re.compile(r"\b(?:meters?|metres?|inch(?:es)?|cm|mm|tiles?|rugs?|area code|quote|dollars?|\$|lumber|boards?|"
                       r"2 by 4|2x4|long)\b|\b\d+\s*(?:ft|feet|')\s*\d", re.I)
_LOG_ACTIVITY = re.compile(r"^\s*(?:please\s+)?log (?:a |an |my )?(?P<n>\d+(?:\.\d+)?)[- ]?(?P<unit>minutes?|mins?|hours?|"
                           r"hrs?) (?P<what>walk|run|jog|hike|bike ride|ride|swim|workout|yoga|stretch(?:ing)?|"
                           r"lift(?:ing)?|row(?:ing)?)(?:\s+(?P<day>yesterday|today|this morning|last night))?\s*[.!]?\s*$",
                           re.I)
# what he should charge for his own eggs, never a store's price, a recipe or another thing by the dozen
_EGG_PRICE = re.compile(r"\b(?:how much|what) (?:should|could|do|can) (?:i|we) (?:charge|ask|sell|get)\b.{0,25}\b(?:eggs?\b|"
                        r"(?:a|per) dozen\b(?!\s+(?!eggs?\b)[a-z]))|\bprice (?:my|our) eggs\b|\bcharge (?:per|a|for a) dozen\b"
                        r"(?!\s+(?!eggs?\b)[a-z])", re.I)
_NOT_EGG_PRICE = re.compile(r"\b(?:walmart|store|costco|aldi|kroger|grocery|benedict|cupcakes?|donuts?|doughnuts?|cookies?|"
                            r"rolls|bagels?|last (?:week|month)|did i|legal|chickens)\b", re.I)


def _everyday_reply(context, prompt: str):
    """The small everyday answers, in code (the live sweep, 2026-11-25): the time and the date ("I'm not sure what
    time it is"), days until a holiday ("how many days until Christmas?" had said the library's instruction aloud),
    a floor's square footage ("12 by 16": the model had listed a shed's materials), "log a 30 minute walk" through
    log_workout (the model had only said "I'll log it"), and an egg price from his own feed cost per dozen
    (core/flock.figures). None otherwise.
    Only what's its own (the Fable review): today's date for "what's today", a holiday itself in days or weeks, feet
    only (never meters, a rug or a quote), a walk of up to a day (yesterday's too), and what he should charge for
    his own eggs, never a store's price."""
    from datetime import datetime as _dt

    said = prompt.replace("’", "'")
    if _TIME_NOW.match(said):
        now = _dt.now()
        if re.search(r"\b(?:date|day|today)\b", said, re.I):
            return f"It's {now:%A}, {now:%B} {now.day}, {now.year}."
        return f"It's {now.strftime('%I:%M %p').lstrip('0')}, {now:%A}."
    found = _DAYS_UNTIL.match(said)
    if found:
        from core import holidays

        what = found.group("what")
        name = holidays.named(what)
        if name is None:
            return None
        left = re.sub(rf"\b(?:{holidays.HOLIDAYS[name][0]})\b", " ", what.lower().replace("’", "'"))
        if re.sub(r"\b(?:the|this year|day)\b|[?.!,]", " ", left).strip():
            return None  # "the day after thanksgiving", "christmas break ends": not the holiday itself
        today = _dt.now().date()
        when = holidays.day_of(name, today.year)
        when = when if when >= today else holidays.day_of(name, today.year + 1)
        days = (when - today).days
        label = name.split(" (")[0]
        if not days:
            return f"{label} is today."
        if found.group("unit").lower() == "weeks":
            return f"About {days / 7:.1f} weeks ({days} days) until {label} ({when:%A}, {when:%B} {when.day})."
        return f"{days} day{'' if days == 1 else 's'} until {label} ({when:%A}, {when:%B} {when.day})."
    found = _AREA.search(said)
    if found and not re.search(r"\b(?:materials?|how many|cost|price|build)\b", said, re.I) and not _NOT_AREA.search(said):
        a = float((found.group("a") or found.group("a2")).replace(",", ""))
        b = float((found.group("b") or found.group("b2")).replace(",", ""))
        return f"{a:g} by {b:g} feet is {a * b:,.0f} square feet." if (a * b).is_integer() else \
            f"{a:g} by {b:g} feet is {a * b:,.2f} square feet."
    found = _LOG_ACTIVITY.match(said)
    if found:
        minutes = float(found.group("n")) * (60 if found.group("unit").lower().startswith("h") else 1)
        if not 0 < minutes <= 24 * 60:
            return None  # "a 0 minute walk", "90 hours": the model's to ask
        what = found.group("what").lower()
        args = {"exercises": [f"{minutes:g} minute {what}"], "duration_minutes": minutes}
        if (found.group("day") or "").lower() in ("yesterday", "last night"):
            from core.budget_manager import read_date

            args["date"] = read_date("yesterday")
        try:
            return context.assistant_actions.execute(context, "log_workout", args)
        except Exception:
            log.exception("Couldn't log the activity")
            return None
    if _EGG_PRICE.search(said) and not _NOT_EGG_PRICE.search(said):
        return _egg_price(context)
    return None


def _egg_price(context):
    """What a dozen of his eggs costs him in feed (core/flock.figures, the last 30 days) and how to price from it;
    the general rule when there's no flock or no feed logged."""
    from datetime import date as _date

    flock = getattr(context, "flock", None)
    rows = getattr(flock, "flocks", None) or []
    cost = None
    if rows:
        try:
            from core.flock import figures

            got = figures(rows[0], flock.entries_for(rows[0].flock_id), _date.today())
            cost = got.get("feed_per_dozen") or None
        except Exception:
            log.exception("Couldn't work out the feed cost per dozen")
    from core.region import money

    rule = ("Price from your costs up: feed per dozen, plus cartons (about 50 cents each new), plus something for your "
            "time, then check what farm eggs sell for near you (a farm stand, a feed store's board, local listings) and "
            "sit at or a little under that. Many places need a permit or labeling to sell eggs: check your state's rules.")
    if cost:
        return f"Your feed costs you about {money(cost)} a dozen (the last 30 days). {rule}"
    return "Log your feed and eggs and I'll work out what a dozen costs you. " + rule


_LOAD_WATTS = re.compile(r"^\s*(?:my|the|our)\s+(?P<load>[a-z][\w' -]{1,30}?)\s+(?:uses|draws|pulls|runs at|takes)\s+"
                         r"(?:about\s+|around\s+)?(?P<w>\d[\d,]*)\s*(?:w|watts)\b(?:\s+(?:for|and runs)\s+(?P<h>\d+(?:\.\d+)?)"
                         r"\s*hours?(?: a day)?)?\s*[.!]?\s*$", re.I)


def _load_watts_reply(context, prompt: str):
    """"My freezer uses 150 watts" (and "for 8 hours a day"), kept as one of his essential loads through
    set_power_load (the live sweep, 2026-11-25: the pantry's tools were offered and nothing was kept); a car, a
    phone or a light bulb's watts are the model's. None otherwise.
    Only what a load uses or draws: never a solar panel, a generator, a battery or a number like a total or a
    budget, and never 0 watts."""
    found = _LOAD_WATTS.match(prompt.replace("’", "'"))
    if not found or re.search(r"\b(?:bulbs?|phones?|laptops?|chargers?|car|truck|tv|solar|panels?|generator|inverter|"
                              r"batter(?:y|ies)|answer|budget|limit|total|capacity|max(?:imum)?)\b", found.group("load"),
                              re.I) or float(found.group("w").replace(",", "")) <= 0:
        return None  # a source of power, a number or a nothing is never a load (the Fable review)
    args = {"load": found.group("load").strip(), "watts": float(found.group("w").replace(",", "")), "question": prompt}
    if found.group("h"):
        args["hours"] = float(found.group("h"))
    try:
        return context.assistant_actions.execute(context, "set_power_load", args)
    except Exception:
        log.exception("Couldn't keep the load")
        return None


# his homestead's own answers, which the model passed over (the live sweep, 2026-11-25): each read-only tool by the
# words that are its whole question
_OWN_TOOLS = (
    # his own flock not laying (never "laying so much", a neighbour's hens or the sheep lying down: the Fable review)
    ("why_hens_not_laying", re.compile(r"^(?!.*\b(?:neighbou?r'?s?|book|video|sheep|cows?|goats?|so much|more)\b)(?:.*\b(?:why|"
                                       r"how come)\b.{0,40}\b(?:hens?|chickens?|flock|girls)\b.{0,30}\b(?:not|aren'?t|isn'?t|"
                                       r"stopped|stop|quit|haven'?t been) laying\b|.*\b(?:my|our|the) (?:hens?|chickens?|flock)\b"
                                       r".{0,15}\b(?:stopped|quit) laying\b|.*\bwhy (?:am|are) (?:i|we) not getting (?:any |"
                                       r"many )?eggs\b|.*\bwhy (?:aren'?t|isn'?t|haven'?t) (?:my|the|our) (?:hens?|chickens?|"
                                       r"flock|girls)\b.{0,20}\blaying\b)", re.I), False),
    # the garden's water only, never paint, the dog or the horses
    ("should_i_water", re.compile(r"^\s*(?:should|do) i (?:water|need to water) (?:the |my )?(?:garden|beds|plants|tomatoes|"
                                  r"vegetables|lawn|seedlings|peppers|squash|flowers)\b|^\s*should i water(?: today| this "
                                  r"week| tomorrow)?\s*\??\s*$|\b(?:does|do) (?:the |my )?(?:garden|beds|plants|tomatoes|"
                                  r"peppers|seedlings) need (?:water|watering)\b|^\s*is it time to water\b", re.I), False),
    # the flock's feed only: never the dog's or the pigs', a what-if, or last week's (the Fable review)
    ("get_eggs", re.compile(r"^(?!.*\b(?:dogs?|cats?|pigs?|goats?|horses?|cattle|cows?|rabbits?|if|last week|yesterday)\b)(?:.*"
                            r"\bhow (?:much|many)\b.{0,15}\b(?:chicken |layer )?feed\b.{0,10}\b(?:do (?:i|we) have|have (?:i|"
                            r"we) got)\b|.*\bhow long will (?:the |my |our )?(?:chicken |layer |hens'? )?feed last\b|"
                            r".*\bdo (?:i|we) have enough (?:chicken |layer )?feed\b)", re.I), True),
    # do the eggs pay for the feed: the flock's own numbers (get_eggs has the feed cost a dozen), never the spending
    # pace's "I need two months of your spending" (the egg conversation check, 2026-11-26)
    ("get_eggs", re.compile(r"^(?!.*\b(?:if|last week|this month|last month|yesterday)\b)\s*(?:hey mia,? )?(?:are|do|does|is) "
                            r"(?:the |my |our )?(?:eggs|hens|chickens|flock|girls) "
                            r"(?:paying|pay|covering|cover|earning|earn)(?: for)? (?:the |their |its )?(?:feed|"
                            r"themselves|keep)\b.{0,20}[?.!]*\s*$|^\s*(?:hey mia,? )?(?:what do|how much do) (?:the |my )?"
                            r"(?:eggs|hens|chickens) cost (?:me|us)(?: a dozen| per dozen)?\s*[?.!]*\s*$", re.I), True),
    # what she may do herself is her grants' (list_grants); the model had made up a browser and the Classroom
    # tools a question plan had answered instead, from a sheet without their records (the live sweep, 2026-11-26)
    ("best_customers", re.compile(r"^\s*(?:hey mia,? )?(?:who (?:are|is) (?:my|our) (?:best|top|biggest|repeat|regular) "
                                  r"(?:customers?|clients?|buyers?)|(?:show me |list )?(?:my|our) (?:best|top|biggest) "
                                  r"(?:customers?|clients?)|who (?:buys|spends|orders) the most(?: from me| with me| from "
                                  r"us| with us)?)\s*[?.!]*\s*$", re.I), False),
    ("suggest_recipes", re.compile(r"^\s*(?:hey mia,? )?(?:what (?:should|can|could) (?:i|we) (?:make|cook|have|eat) (?:for "
                                   r")?(?:dinner|supper|lunch|tonight)|what'?s for (?:dinner|supper)|(?:any )?(?:dinner|"
                                   r"supper) ideas|what can (?:i|we) make with what (?:i|we) have)\s*[?.!]*\s*$", re.I), False),
    # his own prices and hourly earnings (a question plan had answered from a sheet without them, 2026-11-26)
    ("check_my_prices", re.compile(r"^\s*(?:hey mia,? )?(?:should i (?:raise|up|increase) my prices|am i charging enough|"
                                   r"are my prices (?:too low|right|ok|okay)|check my prices)\s*[?.!]*\s*$", re.I), False),
    ("earnings_per_hour", re.compile(r"^\s*(?:hey mia,? )?(?:what(?:'s| is) my (?:hourly rate|hourly|rate per hour) on "
                                     r"(?:my )?(?:builds|jobs|the shop|the workshop)|how much do i (?:really )?make (?:an|per) "
                                     r"hour (?:on|from) (?:my )?(?:builds|jobs|the shop|the workshop))\s*[?.!]*\s*$", re.I),
     True),
    # "do I have enough firewood?": her own check's words, never rephrased into a question (brainstorm round 19)
    # firewood or the woodpile, or wood for the winter: never "how much wood do I have" (his lumber, the Fable review)
    ("firewood_check", re.compile(r"^(?!.*\b(?:if|neighbou?r'?s?)\b)\s*(?:hey mia,? )?(?:do (?:i|we) have enough (?:firewood|"
                                  r"wood(?= for (?:the |this )?winter))(?: for (?:the |this )?winter)?|how much firewood do "
                                  r"(?:i|we) have(?: left)?|is (?:my|our|the) (?:firewood|woodpile) enough|will (?:my|our|the) "
                                  r"(?:firewood|woodpile) last(?: the winter)?)\s*[?.!]*\s*$", re.I), False),
    # "is it a good day to work outside?": her forecast's own words (or her ask for his town, which a bare town answers:
    # core/her_asks), never the model's "can you tell me your city or zip code?"
    ("work_outside_wind_chill_heat_index", re.compile(
        r"^(?!.*\bif\b)\s*(?:hey mia,? )?(?:is (?:it|today|tomorrow) (?:a )?good (?:day|time|weather) (?:to|for) "
        r"(?:work(?:ing)? outside|outside work)|(?:can|should) i work outside|is it (?:too hot|too cold|safe) to work "
        r"outside|will (?:it|tomorrow) be (?:a )?good (?:day )?(?:to|for) work(?:ing)? outside)(?: today| tomorrow)?"
        r"\s*[?.!]*\s*$", re.I), True),
    ("list_grants", re.compile(r"^\s*what (?:can|may|do|will) you do (?:on your own|by yourself|without (?:asking(?: me)?|"
                               r"me asking))\s*\??\s*$|^\s*what are you allowed to do (?:on your own|by yourself)\s*\??\s*$",
                               re.I), False),
    # canning only with a food or a canning word: never "how do I can afford a truck" (the Fable review)
    ("canning_time", re.compile(r"^(?=.*\b(?:jars?|pints?|quarts?|pressure|water[- ]?bath|canner|beans|corn|tomatoes|peaches|"
                                r"pickles|salsa|jam|jelly|sauce|carrots|beets|peppers|meat|chicken|venison|soup|stock|broth|"
                                r"applesauce|pears|apples)\b)(?:\s*how (?:do|should|would) (?:i|you|we) (?:pressure |water[- ]bath"
                                r" )?can\b|\s*how long (?:do|should) (?:i|you) (?:pressure |water[- ]bath )?(?:can|process)\b)",
                                re.I), True),
)


_HOMESTEAD_HEALTH = re.compile(r"^\s*(?:how(?:'s| is) (?:the |my |our )?homestead(?: doing| holding up| looking| going)?|"
                               r"homestead (?:health|status|check)|how are we (?:doing|set) on supplies|"
                               r"how long (?:could|can|would|will) we (?:last|hold out|make it)(?: (?:here|at home|"
                               r"on what we have))?|how long (?:could|can|would|will) i (?:last|hold out|make it) "
                               r"(?:here|at home|on what (?:we|i) have)|how many days (?:could|can|will) we last)"
                               r"\s*[?.!]*\s*$", re.I)
_LEARNED_WEEK = re.compile(r"^\s*what(?: did you| have you|'ve you|'d you) learn(?:ed|t)? (?:(?:from|about) me )?"
                           r"(?:this|the) (?:past |last )?week(?: (?:from|about) me)?(?:,? mia)?\s*[?.!]*\s*$", re.I)
_HOBBIES = re.compile(r"^\s*(?:(?:how(?:'s| is| are)|hows) (?:my |the )?hobbies(?: and projects)?(?: going| coming along| "
                      r"doing)?(?: this month| lately| so far)?|how did my hobbies go this month|"
                      r"(?:my |the )?hobbies' progress|(?:my )?hobby progress|(?:my )?hobbies this month|"
                      r"what have i done for (?:fun|myself|my hobbies) this month)(?:,? mia)?\s*[?.!]*\s*$", re.I)
_MY_WEEK = re.compile(r"^\s*(?:(?:what(?:'s| is| does)|whats) (?:my|the) week (?:look(?:ing)? like|ahead(?: look like)?)|"
                      r"what(?:'s| is) (?:on|coming up|happening|due) (?:for )?this week|(?:my |the )?week ahead|"
                      r"what(?:'s| is) my week(?: (?:going to|gonna) look like)?)(?:,? mia)?\s*[?.!]*\s*$", re.I)
_WATCH_ASK = re.compile(r"^\s*(?:please |hey mia,? )?(?:(?:tell|let|warn|alert|ping) me(?: know)?|remind me) "
                        r"(?:(?:every|each) (?:morning|day|night|evening) )?(?:when(?:ever)?|if|once|every time|each time)"
                        r"\b", re.I)
_WATCHING = re.compile(r"^\s*what (?:are|r) you (?:watching|keeping an eye on)(?: for)?(?: for me)?\s*[?.!]*\s*$", re.I)
_TRIP_EVE = re.compile(r"^\s*(?:hey mia,? )?(?:what (?:do i need|should i (?:pack|bring)|do i (?:pack|bring))"
                       r"(?: (?:for|to pack for|to bring (?:on|for)|on) (?:my |the |tomorrow'?s |this )?(?:\w+ )?trip"
                       r"(?: tomorrow)?)?|am i (?:ready|packed) for (?:my |the |tomorrow'?s )?(?:\w+ )?trip(?: tomorrow)?|"
                       r"am i packed|before i go|what(?:'s| is) left to pack(?: for (?:my |the )?(?:\w+ )?trip)?)"
                       r"\s*[?.!]*\s*$", re.I)
_OUT_OF = re.compile(r"^\s*(?:hey mia,?\s+)?(?:(?:looks like|so|well|ugh),?\s+)?(?:we'?re|i'?m|we are|i am|we|i)\s+"
                     r"(?:all |completely |totally |almost |nearly )?(?:out of|ran out of|have run out of|are out of|"
                     r"are almost out of|almost ran out of)\s+([a-z][a-z' ,-]{1,40}?)\s*(?:again|now)?\s*[.!]*\s*$", re.I)
# The foods "we're out of ..." takes for the grocery list without asking (the Fable review: a deny-list let "out of
# the woods", "out of hope" and "out of diesel" through); anything else is the model's, unless it's already in his
# pantry or on his list.
_GROCERY_WORDS = frozenset(
    "milk eggs egg bread butter coffee tea sugar flour salt pepper rice pasta noodles cheese yogurt cereal oats oatmeal "
    "bacon sausage ham chicken beef pork turkey fish tuna beans lentils potatoes potato onions onion garlic carrots "
    "lettuce tomatoes tomato apples apple bananas banana oranges lemons limes berries grapes juice soda cream "
    "creamer honey syrup jam jelly peanut ketchup mustard mayo mayonnaise ranch dressing vinegar spices cinnamon "
    "vanilla yeast baking soda powder crackers cookies snacks popcorn tortillas buns bagels muffins broth "
    "soup sauce salsa pickles olives peas spinach broccoli cabbage celery peppers mushrooms avocados avocado "
    "toilet paper towels napkins dish soap detergent foil wrap trash diapers wipes shampoo toothpaste".split())
_NOT_GROCERIES = re.compile(r"^(?:the |a |an |my |our |here\b|this\b|that\b)|\b(?:feed|hope|reasons?|patience|time|"
                            r"options|ideas|energy|luck|money|cash|gas|fuel|diesel|propane|oil for|firewood|hay)\b", re.I)


def _groceries(context, said: str) -> bool:
    """Whether "out of" names groceries: every item a food or household word (`_GROCERY_WORDS`), or already in his
    pantry or on his grocery list; never an idiom or a supply that isn't bought at the store."""
    if _NOT_GROCERIES.search(said):
        return False
    items = [i.strip() for i in re.split(r",|\band\b", said) if i.strip()]
    kitchen = getattr(context, "kitchen", None)
    known = set()
    if kitchen is not None:
        try:
            known = {p.name.lower() for p in kitchen.all_pantry_items()} | \
                {g.name.lower() for g in kitchen.all_grocery_items()}
        except Exception:  # noqa: BLE001 - the food words alone then
            known = set()
    return bool(items) and all(i.lower() in known or set(i.lower().split()) <= _GROCERY_WORDS for i in items)
_REMEMBER_TALK = re.compile(r"^\s*(?:hey mia,? )?(?:do you |can you |did you )?remember what (?:i|we) (?:told you|said|"
                            r"talked about)(?: (?:yesterday|last night|last time|earlier|the other day))?\s*[?.!]*\s*$|"
                            r"^\s*what did (?:we talk about|i tell you)(?: (?:yesterday|last night|last time|earlier))?"
                            r"\s*[?.!]*\s*$", re.I)
_WORKOUT_TODAY = re.compile(r"^\s*(?:hey mia,? )?(?:what(?:'s| is) (?:a )?good workout(?: for)? today|what (?:should|do) i "
                             r"(?:work out|train|lift|hit|do at the gym)(?: today| tonight)?|what workout should i do"
                             r"(?: today| tonight)?|(?:give me |suggest )?a workout for today|what(?:'s| is) (?:my |the )?"
                             r"workout (?:for )?today)\s*[?.!]*\s*$", re.I)
_WOOD_NEXT = re.compile(r"^\s*(?:hey mia,? )?(?:what (?:woodworking )?project should i (?:do|build|make|try)(?: next)?"
                         r"(?: in the shop| in woodworking| with wood)?|what(?:'s| is) a good (?:first )?woodworking "
                         r"project|what should i build in (?:the|my) shop(?: next)?|(?:give me |any )?woodworking "
                         r"project ideas?|what woodworking project (?:should i|to) (?:do|build|make|try)(?: next)?)"
                         r"\s*[?.!]*\s*$", re.I)
_SPENT_PERIOD = re.compile(r"^\s*(?:hey mia,? )?(?:how much (?:did|have) (?:i|we) (?:spend|spent)|what did (?:i|we) spend|"
                           r"what(?:'s| is| was) (?:my|our) (?:total )?spending)(?! on\b)(?! for\b)\b(?P<rest>[^?]*)"
                           r"\s*[?.!]*\s*$", re.I)
_BIGGEST_CATEGORY = re.compile(r"^\s*(?:hey mia,? )?(?:what(?:'s| is| was| are| were) (?:my|our) (?:biggest|largest|top|"
                               r"main) (?:expense|spending)(?: categor(?:y|ies))?|where (?:does|did) (?:all )?(?:my|our) "
                               r"money go|what (?:do|did) (?:i|we) spend the most on)(?P<rest>[^?]*?)\s*[?.!]*\s*$", re.I)
_SHOP_MADE = re.compile(r"^\s*(?:hey mia,? )?(?:(?:what|how much) did (?:i|we) make (?:from|at|with|off) (?:the |my "
                        r")?(?:shop|workshop|woodshop|business)|how much did (?:the|my) (?:shop|workshop|woodshop|"
                        r"business) make|what(?:'s| are| were) (?:the|my) shop'?s? (?:sales|revenue|profit))"
                        r"(?P<rest>[^?]*?)\s*[?.!]*\s*$", re.I)
_DEBT_FIRST = re.compile(r"^\s*(?:hey mia,? )?(?:(?:should|do) i pay (?:off |down )?(?:the |my )?[\w ]{2,30}? or (?:the |my )?"
                         r"[\w ]{2,30}? first|which (?:debt|one|loan|card) (?:should|do) i pay (?:off |down )?first|what "
                         r"should i pay (?:off |down )?first|which debt first)\s*[?.!]*\s*$", re.I)
_REMINDERS_LIST = re.compile(r"^\s*(?:hey mia,? )?(?:what (?:reminders|alarms) do i have|what are my reminders|(?:list|show)"
                             r" (?:me )?my reminders|what am i being reminded (?:of|about)|my reminders)\s*[?.!]*\s*$", re.I)
_REMINDER_CANCEL = re.compile(r"^\s*(?:hey mia,? )?(?:please )?(?:cancel|delete|remove|stop|turn off|kill|drop)\s+(?P<what>"
                              r"(?:all (?:of )?(?:my |the )?reminders|every reminder|(?:the |my )?[\w' -]{2,40}? "
                              r"(?:reminder|alarm)s?))\s*[.!]*\s*$", re.I)
_GREETING = re.compile(r"^\s*(?:good (?:morning|afternoon|evening)|morning|hi|hello|hey|howdy|yo)(?:,? (?:mia|there))?"
                       r"\s*[.!]*\s*$", re.I)
_YESTERDAY = re.compile(r"^\s*(?:hey mia,? )?what did (?:i|we) (?:do|get done|accomplish) yesterday\s*[?.!]*\s*$", re.I)
_DUE_MONTH = re.compile(r"^\s*(?:hey mia,? )?what(?:'s| is| bills are| bills do i have| do i have) (?:due|coming due|"
                        r"coming up)(?: for)? (?:this month|the rest of the month|in the next (?:30|thirty) days|next "
                        r"month|this coming month)\s*[?.!]*\s*$|^\s*what bills are due (?:this month|the rest of the "
                        r"month)\s*[?.!]*\s*$|^\s*(?:hey mia,? )?(?:what bills (?:are|do i have) (?:still (?:due|left|"
                        r"unpaid)|left(?: to pay)?|unpaid)|what(?:'s| is) still (?:due|left to pay))(?: this month)?\s*[?.!]*\s*$",
                        re.I)  # "what bills are still due?" too (the money conversation check)
_NEED_FOR = re.compile(r"^\s*(?:hey mia,? )?what (?:do|would) (?:i|we) (?:still )?need (?:for|to make|to cook) (?:the |my |a "
                       r"|that )?(?P<dish>[\w' -]{2,40}?)\s*[?.!]*\s*$", re.I)
_THINKING_OF_BUILDING = re.compile(r"^\s*(?:hey mia,? )?(?:i'?m|i am|we'?re|we are) (?:thinking (?:about|of)|planning(?: on| to)?|"
                                   r"wanting to|going to|gonna) (?:build(?:ing)?|put(?:ting)? up) (?:a |an |some )?"
                                   r"(?P<what>[\w' -]{3,40}?)\s*[.!?]*\s*$", re.I)
_SAID_AS = {"stairs": "set of stairs", "steps": "set of steps", "shelving": "shelving unit", "shelves": "set of shelves",
            "compost": "compost bin", "stringer": "set of stair stringers"}
_AFFORD_ONCE = re.compile(r"^\s*(?:hey mia,? )?can (?:i|we) afford (?:to (?:spend|buy|get) )?(?:a |an )?\$\s?(?P<amount>\d[\d,]*"
                          r"(?:\.\d{1,2})?)(?!.*\b(?:(?:a|per|each|every) (?:week|month|year)|weekly|monthly|yearly|payments?|"
                          r"subscriptions?|rent)\b)(?:\s+(?!this month\b|right now\b|now\b|today\b|a month\b|monthly\b|"
                          r"per\b|each\b|every\b)(?:on (?:a |an )?)?[a-z][\w' -]{1,30}?)?(?:\s+(?:this month|right now|now|today))?\s*[?.!]*\s*$",
                          re.I)  # "a $300 chainsaw" too (the money conversation check); never a monthly cost
# "pay the electric bill", "I paid the electric bill", "mark the water bill paid": one of his bills marked paid
# (mark_bill_paid), only a bill of his by its whole name (the money conversation check: the model had once asked for
# the bill's amount to add it)
_BILL_PAID = re.compile(r"^\s*(?:hey mia,? )?(?:ok(?:ay)?,?\s+)?(?:please\s+)?(?:(?P<verb>(?:i\s+)?(?:just\s+)?paid|pay)\s+(?:the |my "
                        r"|our )?(?P<name>[\w&' -]{2,30}?)(?P<bill> bill)?|mark\s+(?:the |my |our )?(?P<name2>[\w&' -]{2,30}?)"
                        r"(?P<bill2> bill)?(?: as)? paid)(?: today| this month)?\s*[.!]*\s*$", re.I)


def _bill_said(bills, name: str, said_bill: bool):
    """Pure logic. The bill of his his words name: "the phone bill" is a bill named "Phone Bill" before one named
    "Phone"; the name alone otherwise (the Fable review)."""
    from core.assistant_tools import by_name

    if said_bill:
        return by_name(bills, name + " bill") or by_name(bills, name)
    return by_name(bills, name) or by_name(bills, name + " bill")


def _paid_this_time(bill, today):
    """Pure logic. The day it was paid when that payment is this time round's (within its period, or ever for a
    one-off), else None."""
    from datetime import date as _date

    period = {"weekly": 7, "biweekly": 14, "monthly": 31, "quarterly": 92, "yearly": 366}.get(
        str(getattr(bill, "recurrence", "") or "").lower())
    try:
        paid = _date.fromisoformat(str(getattr(bill, "last_paid_date", "") or "")[:10])
    except ValueError:
        return None
    return paid if period is None or 0 <= (today - paid).days < period else None
# "how much is left this month?": a money word or a money period said; a bare "how much is left?" is money only after
# her own money reply (core/her_asks), never after a feed or a loan question (the Fable review)
_MONEY_LEFT = re.compile(r"^\s*(?:hey mia,? )?(?:and\s+|so\s+|ok(?:ay)?,?\s+)?(?:how much money (?:is|do (?:i|we) have|have (?:i|we) "
                         r"got) left(?: over)?(?:\s+(?:this month|for the month|after (?:the |my |those )?bills|to spend))*|"
                         r"(?:how much (?:is|do (?:i|we) have|have (?:i|we) got) left(?: over)?|what(?:'s| is) left)(?:\s+(?:this "
                         r"month|for the month|after (?:the |my |those )?bills|to spend|in the budget))+)\s*[?.!]*\s*$", re.I)
_SIDE_HUSTLE = re.compile(r"^\s*(?:hey mia,? )?(?:what(?:'s| is| would be) a good side (?:hustle|business|gig|income)(?: for "
                          r"me)?|how (?:can|could) i (?:make|earn) (?:some )?(?:extra|side) (?:money|income|cash)|"
                          r"what (?:side hustle|side business) (?:should|could) i (?:do|start|try))\s*[?.!]*\s*$", re.I)
_STOP_REMINDING = re.compile(r"^\s*(?:hey mia,? )?(?:please )?(?:stop|quit|don'?t keep) reminding me (?:to|about|of) "
                             r"(?P<what>.+?)\s*[.!]*\s*$", re.I)
_TRACK_SPENDING = re.compile(r"^\s*(?:hey mia,? )?(?:can|could|will) you (?:track|log|watch|keep track of|record) (?:my |our )"
                             r"(?:spending|expenses|money|purchases)(?: automatically| for me| on your own)?\s*[?.!]*\s*$",
                             re.I)
_MORNING_ROUTINE = re.compile(r"^\s*(?:hey mia,? )?(?:can you )?(?:set up|make|build|create|start) (?:a |my )?(?:morning "
                              r"routine(?: for (?:my )?mornings?)?|routine for (?:my )?mornings?)\s*[?.!]*\s*$", re.I)
_WHEN_PAID = re.compile(r"^\s*(?:hey mia,? )?(?:when|whenever|every time) (?:i|we) get paid,? remind me to (?P<what>.+?)"
                        r"\s*[.!]*\s*$", re.I)
_MONTHLY_BILL = re.compile(r"^\s*(?:hey mia,? )?remind me (?:on the (?P<day1>first|1st|\d{1,2}(?:st|nd|rd|th)) of (?:every|"
                           r"each) month |every month |monthly )?to (?P<what>pay (?:the |my )?(?:rent|mortgage|[\w ]+? bill))"
                           r"(?: (?:every|each) month| monthly| on the (?P<day2>first|1st|\d{1,2}(?:st|nd|rd|th)))*"
                           r"\s*[.!]*\s*$", re.I)
_LAST_DONE = re.compile(r"^\s*(?:hey mia,? )?when (?:did|was) (?:i|we) last (?P<what>[\w' -]{3,50}?)\s*[?.!]*\s*$|"
                        r"^\s*(?:hey mia,? )?when was the last time (?:i|we) (?P<what2>[\w' -]{3,50}?)\s*[?.!]*\s*$", re.I)
_IN_A_WHILE = re.compile(r"^\s*(?:hey mia,? )?(?:please )?(?:can you |could you )?remind me in (?P<spec>[\w .-]{1,40}?"
                         r"(?:minutes?|mins?|hours?|hrs?|half an hour|a half hour|half hour|and a half)) to (?P<what>.+?)"
                         r"\s*[.!?]*\s*$", re.I)
_MOTIVATION = re.compile(r"^\s*(?:hey mia,? )?(?:i (?:really )?need (?:some )?motivation|motivate me|give me (?:some )?"
                         r"motivation|i'?m (?:feeling )?(?:so |really )?unmotivated|i can'?t get motivated|i have no "
                         r"motivation)(?: to (?P<task>(?:finish|work on|start|do|get to|tackle|build|clean) [\w' -]{2,40}?))?"
                         r"(?: today| right now)?\s*[.!?]*\s*$", re.I)
_VEHICLE_KIT = re.compile(r"\b(?:truck|car|vehicle|jeep|suv|van)(?:'s)? (?:emergency |winter |road(?:side)? |survival )?kit\b|"
                          r"\b(?:emergency|winter|road(?:side)?|survival) kit for (?:my |the |a )?(?:truck|car|vehicle|"
                          r"jeep|suv|van)\b|\bkeep in (?:my |the )?(?:truck|car|vehicle)\b", re.I)
_TEACH_SOMETHING = re.compile(r"^\s*(?:hey mia,? )?(?:teach me something(?: new| today| useful)?|(?:tell|show) me something "
                              r"(?:new|useful) to learn|what can i learn today|give me a lesson|teach me a skill)\s*[.!?]*\s*$",
                              re.I)
_MONTH_VS = re.compile(r"^\s*(?:hey mia,? )?(?=.*\b(?:spend|spent|spending)\b)(?!.*\b(?:income|earn\w*|made|make|saved?|"
                       r"save|time|hours?|minutes?|at|business|shop)\b)(?:did (?:i|we)|have (?:i|we) been|am i|"
                       r"are we|was i|were we|what did (?:i|we) spend|how does|how's|how is|compare|is|what's|my)\b"
                       r".{0,60}?(?:\bon (?P<cat>[\w&' -]{2,30}?)\s+)?(?:(?:so far )?this month\s+)?(?:than|vs\.?|"
                       r"versus|compared? (?:to|with)|against|and|to)\s+(?:i did\s+|what i spent\s+)?last month\s*[?.!]*\s*$|^\s*(?:hey mia,? )?"
                       r"(?:my )?(?P<cat2>[\w&' -]{2,30}?)(?: spending)? this month (?:vs\.?|versus|compared (?:to|with)) "
                       r"last month\s*[?.!]*\s*$", re.I)
_BEST_SELLER = re.compile(r"^\s*(?:hey mia,? )?(?:what(?:'s| is| are) (?:my )?(?:best[- ]sell(?:ing|er)s?|top[- ]sell(?:ing|er)s?)"
                          r"(?: products?| items?)?|what (?:sells|sold) (?:the )?best|which (?:of my )?products? (?:sells?|sold) "
                          r"(?:the )?(?:best|most))(?P<when> this (?:year|month|week)| last (?:year|month|week)| in (?:january|february|"
                          r"march|april|may|june|july|august|september|october|november|december)(?: \d{4})?)?"
                          r"\s*[?.!]*\s*$", re.I)
_HARDWARE_NEEDS = re.compile(r"^\s*(?:hey mia,? )?(?:what do (?:i|we) (?:need|have to get|need to (?:get|buy|pick up)) (?:from|at) "
                             r"(?:the )?(?:hardware store|lumber ?yard|lowe'?s|home depot|menards|tractor supply|farm store)|"
                             r"what (?:do|does) (?:i|we|my projects?) (?:still )?need (?:to buy )?for (?:my|our|the) projects?)"
                             r"\s*[?.!]*\s*$", re.I)
_OVERDUE = re.compile(r"^\s*(?:hey mia,? )?(?:what(?:'s| is| am i)|whats|is (?:there )?anything|anything|do i have anything) "
                      r"(?:overdue|past due|late|behind on)(?: (?:today|right now|now))?\s*[?.!]*\s*$|^\s*(?:show me |list )?"
                      r"(?:what'?s |everything )?overdue\s*[?.!]*\s*$", re.I)
# "I practiced for 30 minutes today", "practiced guitar for an hour": a session on his course (log_practice), before
# what-he-did's "Noted" took it (the guitar conversation check, 2026-11-26)
_PRACTICED = re.compile(r"^\s*(?:i\s+)?(?:just\s+)?(?:practiced|practised|played)(?:\s+(?:the\s+|my\s+)?(?P<what>(?!for\b)[a-z][\w' -]{1,25}?))?"
                        r"\s+(?:for\s+)?(?P<n>\d+(?:\.\d+)?|an?|half an?|one|two)\s*(?P<unit>minutes?|mins?|hours?|hrs?)"
                        r"(?:\s+on\s+(?P<on>[\w' -]{2,30}?))?(?:\s+(?:today|tonight|this morning|this evening))?\s*[.!]*\s*$",
                        re.I)
_DUE_TODAY = re.compile(r"^\s*(?:hey mia,? )?(?:what(?:'s| is)|whats|what do i have) due (?:today|for today)\s*[?.!]*\s*$|"
                        r"^\s*(?:hey mia,? )?what(?:'s| is) (?:on )?(?:my )?(?:list|plate) (?:for )?today\s*[?.!]*\s*$", re.I)
_REPORTS_LIST = re.compile(r"^\s*(?:hey mia,? )?(?:(?:what|which) (?:reports|updates) (?:do|will) you (?:send|give) me|what (?:are )?"
                           r"my (?:standing |scheduled )?reports|what do you (?:send|tell) me on a schedule|list my "
                           r"(?:standing |scheduled )?reports)\s*[?.!]*\s*$", re.I)
_REPORTS_STOP = re.compile(r"^\s*(?:hey mia,? )?(?:ok(?:ay)?,?\s+)?(?:please\s+)?(?:stop|cancel|drop|turn off) (?:the |my |that )?"
                           r"(?:(?:daily|morning|evening|weekly|monthly|monday|tuesday|wednesday|thursday|friday|saturday|"
                           r"sunday|money|due|spending|week)\s+)+(?:one|report|update)s?(?: you send me)?\s*[.!]*\s*$", re.I)
_PROJECT_COST = re.compile(r"^\s*(?:hey mia,? )?(?:what|how much) (?:has|have|did) (?:the |my |our )?(?P<p>[\w' -]{2,40}?) "
                           r"(?:project |build )?cost (?:me|us)(?: so far| in all| in total| altogether)?\s*[?.!]*\s*$|"
                           r"^\s*(?:hey mia,? )?(?:what(?:'s| is) the )?(?:whole|total|full|true) cost of (?:the |my |our )?"
                           r"(?P<q>[\w' -]{2,40}?)(?: project| build)?(?: so far)?\s*[?.!]*\s*$", re.I)
_PROJECT_COMING = re.compile(r"^\s*(?:hey mia,? )?(?:how(?:'s| is| are) (?:the |my |our )?(?P<a>[\w' -]{2,40}?) "
                             r"(?:coming(?: along)?|going|doing|looking|progressing)|how far along (?:is|am i (?:on|with)) "
                             r"(?:the |my |our )?(?P<b>[\w' -]{2,40}?)|where (?:am i|are we|do i stand) (?:on|with) (?:the |my "
                             r"|our )?(?P<c>[\w' -]{2,40}?)|(?:what's the |give me the )?status (?:of|on) (?:the |my |our )?"
                             r"(?P<d>[\w' -]{2,40}?))(?: project)?\s*[?.!]*\s*$", re.I)
_HOMESTEAD_MONTH = re.compile(r"^\s*(?:hey mia,? )?(?:what should (?:i|we) (?:be )?(?:doing|do|work on)|what(?:'s| is) there to "
                              r"do|what needs doing|what are the chores) (?:on|around) (?:the |my |our )?(?:homestead|farm|"
                              r"place|land|property)(?: this month| in (?P<month>january|february|march|april|may|june|july|"
                              r"august|september|october|november|december))?\s*[?.!]*\s*$|^\s*(?:hey mia,? )?(?:homestead|farm) "
                              r"(?:chores|jobs|tasks|work) (?:for )?this month\s*[?.!]*\s*$", re.I)
_MONEY_PULSE = re.compile(r"^\s*(?:(?:give me |what's |what is )?(?:my |the )?(?:money pulse|weekly money check)|"
                          r"how(?:'s| is) (?:my )?money (?:this week|(?:looking|doing)(?: this week)?)|"
                          r"how(?:'s| is) my money this week looking|how are my finances this week|how am i doing "
                          r"(?:on|with) money this week)\s*[?.!]*\s*$", re.I)


def _run_own(context, name: str, arguments: dict):
    """Runs one of her tools for a code route, or None when it isn't on this MIA or fails (the model then answers)."""
    actions = getattr(context, "assistant_actions", None)
    if actions is None or name not in getattr(actions, "_actions", {name: 1}):
        return None
    try:
        return actions.execute(context, name, arguments)
    except Exception:
        log.exception("Couldn't run %s", name)
        return None


_COMMAND_FIRST = re.compile(r"^\s*(?:hey mia,?\s+)?(?:please\s+)?(?:remind|add|log|put|note|write|save|keep track|record|"
                            r"schedule|make a note|i (?:put|added|bought|got|did|packed|need to)|we (?:put|added|bought))\b",
                            re.I)  # a command or a statement, never a question to answer (the cross-route review)


_DAYS_RE = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"
_PART_TIMES = {"morning": "8am", "afternoon": "2pm", "evening": "6pm", "night": "8pm"}


def reshaped(prompt: str) -> str:
    """Pure logic. A sentence put in the shape her routes read, its meaning kept (the cross-route review,
    2026-11-26): a greeting before a question set aside ("good morning, what's my week look like?" is the question);
    the weekday first ("every Monday remind me to ...") and a part of the day after it ("every Saturday morning")
    read as "remind me every Saturday to ... at 8am", a bare hour kept in its part of the day (`_with_part`)."""
    said = prompt or ""
    greeted = re.match(r"^\s*(?:good (?:morning|afternoon|evening)|hi|hello|hey|morning)(?:,? mia)?\s*[,!.]+\s*(?P<rest>\S.{5,})$",
                       said, re.I)
    if greeted:
        said = greeted.group("rest")
    first = re.match(rf"^\s*(?:hey mia,?\s+)?(?:every|each) ({_DAYS_RE})s?(?: (morning|afternoon|evening|night))?,?\s+"
                     r"remind me to\s+(.+?)\s*[.!]?\s*$", said, re.I)
    if first:
        return f"Remind me every {first.group(1)} to {_with_part(first.group(3), first.group(2))}"
    part = re.match(rf"^\s*(?:hey mia,?\s+)?(?:please\s+)?remind me every ({_DAYS_RE}) (morning|afternoon|evening|night)\s+to\s+"
                    r"(.+?)\s*[.!]?\s*$", said, re.I)
    if part:
        return f"Remind me every {part.group(1)} to {_with_part(part.group(3), part.group(2))}"
    return said


def _with_part(task: str, part: str) -> str:
    """Pure logic. A task with its part of the day as a time: its default ("at 8am") when it names no hour, or its
    bare hour made the afternoon's or the evening's ("at 7" on an evening is 7pm); a task with "at noon" or an hour with
    am or pm as it is (the Fable review, 2026-11-26)."""
    if not part:
        return task
    part = part.lower()
    if re.search(r"\bat (?:noon|midnight|\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))\b", task, re.I):
        return task
    bare = re.search(r"\bat (\d{1,2})(:\d{2})?\s*$", task)
    if bare:
        hour = int(bare.group(1))
        ampm = "am" if part == "morning" or (part == "night" and hour == 12) else "pm"
        return task[:bare.start()] + f"at {hour}{bare.group(2) or ''}{ampm}"
    return f"{task} at {_PART_TIMES[part]}"


def _own_tool_reply(context, prompt: str):
    """The homestead's own read-only answers by the words that are their question (the live sweep, 2026-11-25: "why
    aren't my hens laying?" was asked about stress, "how much feed do I have left?" asked what feed, "should I water
    the garden?" said there was no garden, and "how do I can tomatoes?" got back "How to can tomatoes."):
    why_hens_not_laying, should_i_water, get_eggs (its feed runway) and canning_time; and what she may do on her own,
    her grants (list_grants). "How's the homestead?" is its days in one line (core/homestead_health), "how's my
    money this week?" its pulse (core/money_pulse), "what did you learn this week?" the week's learning
    (core/learned_week), "how are my hobbies going?" this month across them (core/hobby_progress), "what does
    my week look like?" the week with its look-ahead (get_week); a sentence that opens as a command or a statement
    ("remind me to ...", "add ...", "I put ...": `_COMMAND_FIRST`) never gets her own tools' answers or the vehicle's
    kit, and "should I pay X or Y first?" only when X and Y are two of his debts (the cross-route review); "we're out of milk" the grocery list
    (add_grocery_item, never the pantry; only for groceries: food and household words, or what's in
    his pantry or on his list, never "out of the woods", "out of hope" or "out of diesel": `_groceries`), "do you remember what I told
    you yesterday?" her record of it (list_past_conversations), "what's a good workout for today?" his own next
    workout (core/workout_today), "what woodworking project should I do next?" his next piece
    (core/woodworking.next_project; "build next ... shop", the business's, stays make_next's), "how much did I
    spend last month?", "my biggest expense category this year" and "what did I make from the shop this month?"
    (core/money_periods; only when what follows is a period: "at Costco last month" is the model's), "can I afford a
    $500 purchase this month?" this month's records against it (core/money_periods.afford; a monthly cost is the
    afford plan's), "should I pay
    off the card or the truck first?" his own debts compared (get_debt_payoff_plan), his reminders listed and one
    cancelled by its words (never all on one sentence), "good morning" back in kind with the day, and "what did I do
    yesterday?" (core/reminders_view), "what's due this month?" to the month's end, overdue first
    (core/assistant_today_actions.due_through), and the automation asks she can't or mustn't claim (core/reminders_view:
    "stop reminding me to ..." only stops one that's there, "when did I last change the oil?" from his maintenance
    record (or his history: "when did I last work out?"), "remind me in 2 hours to ..." (or "an hour and a half") with the clock worked out, spending tracked automatically, a morning routine,
    "when I get paid remind me", rent reminded as a bill only when said monthly), a report on a schedule kept only
    when her code answers its question (core/standing_reports), "I'm thinking about building a chicken coop" what she can work
    out for it (core/build_calcs's structures, only one named on its own and with no size said), "I need motivation (to finish the shed)" his own reasons and one small step (core/motivation), "teach me
    something" a lesson from her own courses (core/teach_something), "did I spend more this month than last month?" the
    months side by side (core/money_periods.compare), "what's my best-selling product?" by units sold
    (core/money_periods.best_sellers), "what do I need from the hardware store?" his
    projects' open needs (never a guess from his expenses), "I caught a 3 pound bass at the pond" one catch, as said (core/catch_actions.parse), "how much is left this month?" the month's records after what's due (core/money_periods.afford), "I paid the
    electric bill" that bill of his marked paid (mark_bill_paid; never twice for one time round, and "pay the electric
    bill" is what's due and how to mark it, since she pays nothing),
    "I practiced for 30 minutes today" a session on his
    course (log_practice: the course named whole, never "guitar hero"; unnamed only as "practiced", never a day or a
    game), "what's due today?" today's things then the overdue (core/today.due_today_said), "what reports do you send
    me?" and "stop the Sunday one" her standing reports (core/standing_reports), "what's overdue?" everything
    overdue on his list
    (core/today.overdue_said), "what has the shed cost me?" its money and hours
    (core/project_status.whole_cost), "how's the shed coming along?" that project's picture
    (core/project_status, only for a project his words name whole), "what should I be doing on the homestead this
    month?" (or "in march") that month's items and the season's usual work (core/homestead_year.this_month), "what should be in my truck's
    emergency kit?" Ready.gov's car kit against his records (core/ready_kit.say_vehicle), "what's a good side
    hustle for me?" from what he already sells,
    keeps and owns (core/side_hustle), "what do I need for the chili?" a saved recipe's missing
    ingredients (core/assistant_domain_actions.needs_for; anything not a recipe of his is the model's), "tell me when..." a watch from his whole sentence
    when core/condition_watch can read it (watch_condition) and "what are you watching?" every watch (list_watches),
    "what do I need for my trip?" tomorrow's trip before he goes (core/trip_eve). None otherwise."""
    said = prompt.replace("’", "'")
    if _HOMESTEAD_HEALTH.match(said):  # "how's the homestead?": its days in one line (core/homestead_health)
        from core import homestead_health

        try:
            return homestead_health.line(context)
        except Exception:
            log.exception("Couldn't say the homestead's health")
            return None
    if _LEARNED_WEEK.match(said):  # "what did you learn this week?" (core/learned_week)
        from core import learned_week

        try:
            return learned_week.say(context)
        except Exception:
            log.exception("Couldn't say what she learned this week")
            return None
    if _HOBBIES.match(said):  # "how are my hobbies going?": this month across them (core/hobby_progress)
        from core import hobby_progress

        try:
            return hobby_progress.say(context)
        except Exception:
            log.exception("Couldn't say the hobbies' progress")
            return None
    from core import standing_reports

    report = standing_reports.parse(said)
    if report is not None and standing_reports.answer(context, report["question"]) is not None:
        # "every Sunday tell me what's due this week": kept from his words, only when her code answers it (never "every
        # morning tell me the weather and my day", the morning briefing's, nor "tell me a story every night")
        kept = _run_own(context, "keep_standing_report", {"question": said})
        if kept:
            return kept
    if _WATCH_ASK.match(said) or _WATCHING.match(said):  # "tell me when...": a watch read from his whole sentence
        from core import condition_watch                  # (core/condition_watch), never the model's few words
        from core.weather import unit_for

        actions = getattr(context, "assistant_actions", None)
        if _WATCHING.match(said):
            name = "list_watches"
        elif condition_watch.parse(said, celsius=unit_for(context) == "celsius") is not None:
            name = "watch_condition"
        else:
            name = ""
        if name and actions is not None and name in getattr(actions, "_actions", {name: 1}):
            try:
                return actions.execute(context, name, {"question": said} if name == "watch_condition" else {})
            except Exception:
                log.exception("Couldn't run %s", name)
                return None
    if _TRIP_EVE.match(said) and re.search(r"\btrip\b|\bpack|\bbefore i go\b", said, re.I):  # "what do I need for my trip?": tomorrow's trip, before he goes (core/trip_eve)
        from core import trip_eve

        try:
            return trip_eve.say(context)
        except Exception:
            log.exception("Couldn't say the trip's list")
            return None
    out = _OUT_OF.match(said)
    if out and _groceries(context, out.group(1).strip()):  # "we're out of milk": the grocery list, never the pantry
        return _run_own(context, "add_grocery_item", {"items": out.group(1).strip(), "question": said})
    if _REMEMBER_TALK.match(said):  # "do you remember what I told you yesterday?": her own record of it
        return _run_own(context, "list_past_conversations", {"question": said})
    low = said.lower()
    paid_bill = _BILL_PAID.match(said)
    budget = getattr(context, "budget", None)
    if paid_bill and budget is not None and hasattr(budget, "all_bills") and not re.search(r"\$|\d", said):
        from datetime import date as _date

        try:
            name = paid_bill.group("name") or paid_bill.group("name2")
            bill = _bill_said(budget.all_bills(), name, bool(paid_bill.group("bill") or paid_bill.group("bill2")))
            if bill is not None:
                already = _paid_this_time(bill, _date.today())
                if already is not None:  # never a second payment for the same time round (the Fable review)
                    return f"{bill.name} is already marked paid ({already:%B} {already.day})."
                if (paid_bill.group("verb") or "").lower().strip() == "pay":  # MIA pays nothing: say what's due
                    from core.region import money

                    amount = float(getattr(bill, "amount", 0) or 0)
                    return (f"I can't pay it for you, but I can keep track: {bill.name}"
                            + (f" is {money(amount)}" if amount else "") + ". Once it's paid, say \"I paid the "
                            f"{bill.name.lower().replace(' bill', '')} bill\" and I'll mark it.")
                return context.assistant_actions.execute(context, "mark_bill_paid", {"name": bill.name})
        except Exception:
            log.exception("Couldn't mark the bill paid")
    if _MONEY_LEFT.match(said):  # "how much is left this month?": the month's records (core/money_periods.afford)
        from core import money_periods

        try:
            return money_periods.afford(context, None)
        except Exception:
            log.exception("Couldn't say what's left this month")
            return None
    once = _AFFORD_ONCE.match(said)
    if once:  # "can I afford a $500 purchase this month?": this month's records against it (core/money_periods)
        from core import money_periods

        try:
            return money_periods.afford(context, float(once.group("amount").replace(",", "")))
        except Exception:
            log.exception("Couldn't say whether it's affordable")
            return None
    asked = _SHOP_MADE.match(said) or _BIGGEST_CATEGORY.match(said) or _SPENT_PERIOD.match(said)
    if asked:  # money over a period (core/money_periods), only when what follows is a period
        from core import money_periods

        try:
            if money_periods.only_period(asked.group("rest")):
                if asked.re is _SHOP_MADE:
                    return money_periods.shop_made(context, said)
                if asked.re is _BIGGEST_CATEGORY:
                    return money_periods.biggest(context, said)
                answer = money_periods.spent(context, asked.group("rest"))
                if answer:
                    return answer
        except Exception:
            log.exception("Couldn't say the money for that period")
            return None
    debt_or = _DEBT_FIRST.match(said) and re.search(r"\bor\b", said)
    if debt_or:  # "the electric bill or buy feed first?" names no two debts: the model's
        try:
            from core.assistant_domain_actions import _debts_named

            ranked = context.budget.debt_payoff_priority()
            if len(_debts_named(ranked, said)) != 2:
                debt_or = None
        except Exception:  # noqa: BLE001
            debt_or = None
        if debt_or is None:
            debt_or = False
    if _DEBT_FIRST.match(said) and debt_or is not False:  # "should I pay off the card or the truck first?"
        found = _run_own(context, "get_debt_payoff_plan", {"question": said})
        if found:
            return found
    stopping = _REMINDER_CANCEL.match(said)
    if stopping and re.match(r"\s*(?:hey mia,? )?(?:please )?(?:turn off|stop|kill)\b", said, re.I) and \
            re.search(r"\balarms?\b", stopping.group("what"), re.I):
        stopping = None  # "turn off the wake up alarm" while it rings is silencing it, never deleting it
    if _REMINDERS_LIST.match(said) or stopping or _GREETING.match(said) or _YESTERDAY.match(said):
        # his reminders, a greeting, yesterday (core/reminders_view)
        from core import reminders_view

        try:
            if _REMINDERS_LIST.match(said):
                return reminders_view.listing(context)
            if _GREETING.match(said):
                return reminders_view.greeting(context, said)
            if _YESTERDAY.match(said):
                return reminders_view.yesterday(context)
            found = reminders_view.cancel(context, stopping.group("what"))
            if found:
                return found
            return reminders_view.stop_reminding(context, stopping.group("what"))  # never a claim it stopped
        except Exception:
            log.exception("Couldn't answer about reminders")
            return None
    building = _THINKING_OF_BUILDING.match(said)
    if building and not re.search(r"\d", building.group("what")):  # a size said is the material tools' to take
        from core.assistant_plan_actions import STRUCTURES

        what = building.group("what").lower().strip()
        # only a structure on its own ("a chicken coop", "a new deck this spring"), never "a pitch deck", "a wall
        # between us" or "a shelter for the homeless" (the Fable review, 2026-11-26)
        named = next((n for names, _calc in STRUCTURES for n in names
                      if re.fullmatch(rf"(?:(?:new|small|big|little|simple|bigger|second|another|my|our)\s+)?"
                                      rf"{re.escape(n)}(?:\s+(?:this|next)\s+(?:weekend|week|spring|summer|fall|"
                                      rf"winter|month|year))?", what)), None)
        if named:
            kind = _SAID_AS.get(named, named)
            example = {"chicken coop": "a 4 by 8 chicken coop", "coop": "a 4 by 8 coop", "raised bed": "a 4 by 8 raised bed",
                       "deck": "a 12 by 16 deck", "fence": "100 feet of privacy fence"}.get(named, f"a {kind}")
            return (f"Good project. I can work out the materials and cuts for a {kind} at your size, what they'd cost from "
                    f"your prices, and what's already on hand. Say \"materials for {example}\" and I'll do it, or give "
                    f"me your size.")
    if _SIDE_HUSTLE.match(said):  # "what's a good side hustle for me?": from what he already has (core/side_hustle)
        from core import side_hustle

        try:
            return side_hustle.say(context)
        except Exception:
            log.exception("Couldn't say a side hustle")
            return None
    need = _NEED_FOR.match(said)
    if need:  # "what do I need for the chili?": a saved recipe's missing ingredients, never a cure or a build
        from core.assistant_domain_actions import needs_for

        try:
            found = needs_for(context, need.group("dish"))
        except Exception:
            log.exception("Couldn't say what a recipe needs")
            found = None
        if found:
            return found
    for pattern, name in ((_STOP_REMINDING, "stop"), (_TRACK_SPENDING, "track"), (_MORNING_ROUTINE, "routine"),
                          (_WHEN_PAID, "paid"), (_MONTHLY_BILL, "bill")):
        found = pattern.match(said)
        if not found:
            continue
        from core import reminders_view  # never a claim she did what she can't (the automation sweep, 2026-11-26)

        try:
            if name == "stop":
                return reminders_view.stop_reminding(context, found.group("what"))
            if name == "track":
                return reminders_view.TRACK_SPENDING
            if name == "routine":
                return reminders_view.MORNING_ROUTINE
            if name == "paid":
                return reminders_view.when_paid(context, found.group("what"))
            if not re.search(r"\b(?:every|each) month\b|\bmonthly\b", said, re.I):
                continue  # a one-off ("remind me to pay the vet bill") is the reminder's own route
            return reminders_view.bill_reminder(found.group("what"), found.group("day1") or found.group("day2") or "")
        except Exception:
            log.exception("Couldn't answer %s", name)
            return None
    done = _LAST_DONE.match(said)
    if done:  # "when did I last change the oil?": his maintenance record, never a guess (core/reminders_view)
        from core import reminders_view

        try:
            asked = done.group("what") or done.group("what2")
            found = reminders_view.last_done(context, asked) or reminders_view.last_in_history(context, asked)
        except Exception:
            log.exception("Couldn't say when it was last done")
            found = None
        if found:
            return found
    later = _IN_A_WHILE.match(said)
    if later:  # "remind me in 2 hours to check the oven": the clock worked out in code
        from core import reminders_view

        try:
            found = reminders_view.in_a_while(context, later.group("spec"), "", later.group("what"))
        except Exception:
            log.exception("Couldn't set the reminder")
            found = None
        if found:
            return found
    if _VEHICLE_KIT.search(said) and not _COMMAND_FIRST.match(said) and \
            re.match(r"\s*(?:hey mia,?\s+)?(?:what|which|check|do i|should i|how)\b", said, re.I):
        from core import ready_kit  # the vehicle's own kit, never the house's 72-hour bag

        try:
            return ready_kit.say_vehicle(context)
        except Exception:
            log.exception("Couldn't check the vehicle kit")
            return None
    versus = _MONTH_VS.match(said)
    if versus:  # "did I spend more this month than last month?" (core/money_periods.compare)
        from core import money_periods
        from core.budget_manager import EXPENSE_CATEGORIES

        category = ""
        if versus.group("cat") or versus.group("cat2"):
            what = (versus.group("cat") or versus.group("cat2")).strip()
            if re.search(r"\b(?:and|or)\b|,", what):
                return None  # "groceries and gas": two categories are the model's
            category = next((c for c in EXPENSE_CATEGORIES if c.lower() == what.lower()), None) or next(
                (c for c, words in _SPENT_ON if re.search(words, what, re.I)), None)
            if category is None and not (versus.group("cat2") and what.lower() in ("spending", "money")):
                return None  # a thing it can't put in a category: the model's
            category = category or ""
        try:
            return money_periods.compare(context, category)
        except Exception:
            log.exception("Couldn't compare the months")
            return None
    best = _BEST_SELLER.match(said)
    if best:  # "what's my best-selling product?": units sold from the ledger, never stock (core/money_periods)
        from core import money_periods

        try:
            return money_periods.best_sellers(context, best.group("when") or "")
        except Exception:
            log.exception("Couldn't say his best seller")
            return None
    if _HARDWARE_NEEDS.match(said):  # "what do I need from the hardware store?": his projects' open needs
        try:
            from core.assistant_requirement_actions import needs_sentence

            said_needs = needs_sentence(context, "")
            if said_needs in ("Nothing's still needed.",):
                return "Nothing's on your projects' needs lists right now, so nothing I know of to pick up."
            return said_needs
        except Exception:
            log.exception("Couldn't read his projects' needs")
            return None
    try:  # "I caught a 3 pound bass at the pond": the catch as said, in code (core/catch_actions.parse)
        from core import catch_actions

        caught = catch_actions.parse(said)
    except Exception:
        log.exception("Couldn't read the catch")
        caught = None
    if caught is not None:
        actions = getattr(context, "assistant_actions", None)
        if actions is not None:
            return actions.execute(context, "log_catch", caught)
    practiced = _PRACTICED.match(said)
    if practiced:  # a practice session on his course: the one named, else the only one started (core/paths)
        from core import paths

        book = getattr(context, "paths", None)
        try:
            started = [paths.program_of(context, p) for p in (book.started() if book is not None else [])]
            started = [p for p in started if p is not None]
            what = re.sub(r"^(?:the|my)\s+", "", (practiced.group("what") or "").strip().lower())
            named = paths.find_program(context, what) if what else None
            if named is not None and what not in {named.name.lower(), named.id.lower()} | set(
                    re.findall(r"[a-z]+", named.name.lower())) - {"and", "the", "basics", "with", "of"}:
                named = None  # "guitar hero", "go fish", "survival mode": never the course (the Fable review)
            on = (practiced.group("on") or "").lower()
            unnamed_ok = not what and practiced.group(0).lower().lstrip().lstrip("i ").startswith(("practiced", "practised",
                                                                                                    "just practi"))
            if re.search(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|weekend|xbox|"
                         r"playstation|phone|computer|switch)\b", on):
                named, unnamed_ok = None, False  # a day it doesn't read, or a game, is never a session today
            program = named if named is not None and named in started else (
                started[0] if len(started) == 1 and unnamed_ok else None)
            if program is not None:
                n = practiced.group("n").lower()
                amount = {"a": 1, "an": 1, "one": 1, "two": 2, "half a": 0.5, "half an": 0.5}.get(n) or float(n)
                minutes = amount * (60 if practiced.group("unit").lower().startswith("h") else 1)
                if 0 < minutes <= 600:
                    return _run_own(context, "log_practice", {"minutes": minutes, "path": program.id,
                                                              "worked_on": practiced.group("on") or ""})
        except Exception:
            log.exception("Couldn't log the practice")
    if _DUE_TODAY.match(said):  # "what's due today?": today's things, then what's overdue (core/today.due_today_said)
        from core import today as _today

        try:
            return _today.due_today_said(context)
        except Exception:
            log.exception("Couldn't say what's due today")
            return None
    if _REPORTS_LIST.match(said):  # "what reports do you send me?": her own list (core/standing_reports)
        return _run_own(context, "list_standing_reports", {})
    if _REPORTS_STOP.match(said):  # "stop the Sunday one": that report, or which one asked (core/standing_reports)
        from core import morning_briefing

        if not morning_briefing._OFF.search(said):  # "stop the morning report" is the briefing's own off switch
            return _run_own(context, "stop_standing_report", {"question": said})
    if _OVERDUE.match(said):  # "what's overdue?": his whole list's overdue (core/today.overdue_said)
        from core import today as _today

        try:
            return _today.overdue_said(context)
        except Exception:
            log.exception("Couldn't say what's overdue")
            return None
    costing = _PROJECT_COST.match(said)
    if costing:  # "what has the shed cost me?": its money and his hours (core/project_status.whole_cost)
        from core import project_status, project_time

        try:
            project = project_time.project_named(context, costing.group("p") or costing.group("q"), whole=True)
            if project is not None and project.name.lower() not in _assets(context):
                return project_status.whole_cost(context, project)  # a machine of the same name stays get_tool_costs'
        except Exception:
            log.exception("Couldn't say what the project cost")
    coming = _PROJECT_COMING.match(said)
    if coming:  # "how's the shed coming along?": the project's picture from his records (core/project_status)
        from core import project_status, project_time

        try:
            named = next(g for g in coming.groups() if g)
            project = project_time.project_named(context, named, whole=True)  # "the garden" is never Garden Fence
            if project is not None:
                return project_status.say(context, project)
        except Exception:
            log.exception("Couldn't say how the project is coming")
    month_asked = _HOMESTEAD_MONTH.match(said)
    if month_asked:  # "what should I be doing on the homestead this month?" (core/homestead_year)
        from core import homestead_year

        try:
            return homestead_year.this_month(context, month=month_asked.group("month") or "")
        except Exception:
            log.exception("Couldn't say the homestead's month")
            return None
    if _TEACH_SOMETHING.match(said):  # "teach me something": a lesson from her own courses (core/teach_something)
        from core import teach_something

        try:
            return teach_something.say(context)
        except Exception:
            log.exception("Couldn't teach something")
            return None
    motivated = _MOTIVATION.match(said)
    if motivated:  # "I need motivation (to finish the shed)": his own reasons and one small step (core/motivation)
        from core import motivation

        try:
            return motivation.say(context, task=motivated.group("task") or "")
        except Exception:
            log.exception("Couldn't give motivation")
            return None
    if _DUE_MONTH.match(said):  # "what's due this month?": the month to its end, overdue first (get_week's sources)
        from core.assistant_today_actions import due_through

        try:
            return due_through(context, said)
        except Exception:
            log.exception("Couldn't say what's due this month")
            return None
    if _WOOD_NEXT.match(said) and ("wood" in low or ("shop" in low and "next" not in low)):  # his next piece
        from core import woodworking

        try:
            return woodworking.next_project(context)
        except Exception:
            log.exception("Couldn't say the next woodworking project")
            return None
    if _WORKOUT_TODAY.match(said):  # "what's a good workout for today?": from his own training (core/workout_today)
        from core import workout_today

        try:
            return workout_today.say(context)
        except Exception:
            log.exception("Couldn't say today's workout")
            return None
    if _MY_WEEK.match(said):  # "what does my week look like?": the week and its look-ahead (get_week, core/week_ahead)
        actions = getattr(context, "assistant_actions", None)
        if actions is not None and "get_week" in getattr(actions, "_actions", {"get_week": 1}):
            try:
                return actions.execute(context, "get_week", {})
            except Exception:
                log.exception("Couldn't say the week")
                return None
    if _MONEY_PULSE.match(said):  # "how's my money this week?": its pulse in a line (core/money_pulse)
        from core import money_pulse

        try:
            return money_pulse.say(context)
        except Exception:
            log.exception("Couldn't say the money pulse")
            return None
    actions = getattr(context, "assistant_actions", None)
    if actions is None:
        return None
    if _COMMAND_FIRST.match(said):
        return None  # "remind me to ask the vet why the hens aren't laying" is the reminder's, not the diagnosis
    for name, pattern, words in _OWN_TOOLS:
        if pattern.search(said) and name in getattr(actions, "_actions", {name: 1}):
            try:
                return actions.execute(context, name, {"question": said} if words else {})
            except Exception:
                log.exception("Couldn't run %s", name)
                return None
    return None


_DEBT_ASK = re.compile(r"^\s*how much (?:is|do (?:i|we) (?:still )?owe on|is left on|do (?:i|we) have left on) (?:my|the|our) "
                       r"(?P<debt>[\w' -]+?)(?: balance)?\s*\??\s*$", re.I)


def _debt_line(context, prompt: str):
    """"How much is my truck loan?" from his debts (the live sweep, 2026-11-25: the word "truck" had offered the
    maintenance tools, and the model said the balance wasn't in them): the one debt his words name, its balance, rate
    and minimum. None otherwise.
    Only with a debt word said (loan, card, owe, balance): "how much is my truck?" is its value. "My card" alone is his
    one credit card (none when he has two)."""
    found = _DEBT_ASK.match(prompt.replace("’", "'"))
    budget = getattr(context, "budget", None)
    if not found or budget is None or not hasattr(budget, "all_debts") or not re.search(
            r"\b(?:loan|card|debt|balance|owe|left on)\b", prompt, re.I):
        return None  # "how much is my truck?" is its value (the Fable review)
    generic = {"loan", "card", "debt", "balance", "the", "my", "credit"}
    said = set(re.findall(r"[a-z0-9]+", found.group("debt").lower())) - generic
    named = [d for d in budget.all_debts() if said and said == set(re.findall(r"[a-z0-9]+", d.name.lower())) - generic]
    if not said and re.search(r"\bcard\b", found.group("debt"), re.I):  # "my card": his one credit card
        named = [d for d in budget.all_debts() if "card" in str(getattr(d, "debt_type", "") or "").lower()]
    if len(named) != 1:
        return None
    from core.region import money

    d = named[0]
    rate = f" at {float(d.interest_rate):g}%" if getattr(d, "interest_rate", None) else ""
    minimum = f", {money(float(d.minimum_payment))} a month minimum" if getattr(d, "minimum_payment", None) else ""
    return f"{d.name}: {money(float(d.balance))} left{rate}{minimum}."


_PAID_ASK = re.compile(r"^\s*(?:did|have) (?:i|we) (?:already )?pa(?:y|id) (?:the |my |our )?(?P<bill>[\w' -]+?)(?: bill)?"
                       r"(?: yet| already| this month)?\s*\??\s*$", re.I)  # the bill's own name, whole (by_name)
_HOW_MANY_HAVE = re.compile(r"^\s*how many (?!days\b|weeks\b|months\b|hours\b|years\b)(?P<what>[\w' -]+?) (?:do|have) (?:i|we) "
                            r"(?:have|got|got left|left)(?: in stock| on hand| left)?\s*\??\s*$", re.I)


def _follow_through_reply(context, conversation, prompt: str):
    """A short follow-up to one of her code answers, made whole (core/follow_through, the live sweep 2026-11-26:
    "what about this month?" after last month's spending, "and the card?" after the truck loan): his last question
    with the new words in place (the last one that wasn't itself a follow-up, each follow-up since folded in:
    core/follow_through.thread, so "and groceries?" after "what about this month?" is groceries this month), answered by the same code answers (`_records_reply`,
    `_own_tool_reply`, `_spent_on_reply`, `_water_on_hand_reply`, `_garden_kit_reply`: a crop's dates,
    `_everyday_reply`). His bare answer to her own
    last question ("about 4" after her firewood ask, "5 gallons" after "How much fuel?", his town, a build's size) is
    kept first (core/her_asks, given her last three replies so "add it to my projects" still finds the build). None when it isn't one, can't be joined, or no code answer takes the joined question (the
    model has it)."""
    from core import follow_through

    if conversation is not None:  # his bare answer to her own last question (core/her_asks)
        said = [str(getattr(m, "content", "") or "") for m in getattr(conversation, "messages", []) or []
                if getattr(m, "role", "") == "assistant"]
        if said:
            try:
                from core import her_asks

                kept = her_asks.reply(context, said[-1], prompt, tuple(said[-3:]))
                if kept:
                    return kept
            except Exception:
                log.exception("Couldn't keep his answer to her question")
    x = follow_through.follow_on(prompt)
    if x is None or conversation is None:
        return None
    asked = [str(getattr(m, "content", "") or "") for m in getattr(conversation, "messages", []) or []
             if getattr(m, "role", "") == "user"]
    if asked and asked[-1].strip() == prompt.strip():
        asked = asked[:-1]  # the new words, already stored
    # the thread: the question a chain of follow-ups leans on, each since folded in ("what about this month?", then
    # "and groceries?" is groceries this month)
    whole = follow_through.thread(asked, x)
    if not whole:
        return None
    return (_records_reply(context, whole) or _own_tool_reply(context, whole) or _spent_on_reply(context, whole)
            or _water_on_hand_reply(context, whole) or _garden_kit_reply(context, whole) or _everyday_reply(context, whole))


def _records_reply(context, prompt: str):
    """Two of his own records, in code (the live sweep, 2026-11-25: the model was unsure and asked where the cutting
    boards were): "did I pay the electric bill?" from his bills (paid, or when it's due), and "how many cutting
    boards do I have?" from his products' stock. None otherwise, or when no record of his is named.
    A recurring bill paid within its period is paid; a bill's and a product's names are matched whole (`by_name`),
    and the stock is the Product's quantity_in_stock.
    And "how much is my truck loan?" from his debts (`_debt_line`)."""
    said = prompt.replace("’", "'")
    line = _debt_line(context, said)
    if line is not None:
        return line
    found = _PAID_ASK.match(said)
    budget = getattr(context, "budget", None)
    if found and budget is not None and hasattr(budget, "all_bills"):
        from core.assistant_tools import by_name

        bill = by_name(budget.all_bills(), found.group("bill"))
        if bill is None:
            return None
        from datetime import date as _date

        from core.budget_manager import days_until_bill_due

        today = _date.today()
        period = {"weekly": 7, "biweekly": 14, "monthly": 31, "quarterly": 92, "yearly": 366}.get(
            str(bill.recurrence or "").lower())
        try:
            paid = _date.fromisoformat(str(bill.last_paid_date or "")[:10])
        except ValueError:
            paid = None
        if paid is not None and (period is None or 0 <= (today - paid).days < period):
            # paid this time round (a monthly one paid today is paid: the Fable review), never "not yet"
            return f"Yes: {bill.name} was paid {paid:%B} {paid.day}." + (
                "" if period is None else f" The next one is due in {days_until_bill_due(bill, today)} days.")
        left = days_until_bill_due(bill, today)
        if left is None:
            return f"I don't have a due date for {bill.name}, and no payment kept for it."
        if left < 0:
            return f"Not yet: {bill.name} is {-left} day{'' if left == -1 else 's'} overdue."
        return f"Not yet: {bill.name} is due {'today' if left == 0 else f'in {left} day' + ('' if left == 1 else 's')}."
    found = _HOW_MANY_HAVE.match(said)
    products = getattr(context, "products", None)
    if found and products is not None and hasattr(products, "all_products"):
        from core.assistant_tools import by_name

        product = by_name(products.all_products(), found.group("what"))
        if product is None:
            return None
        count = getattr(product, "quantity_in_stock", getattr(product, "quantity", None))  # the Product's own field
        if not isinstance(count, (int, float)) or count != count or count < 0:
            return None  # none kept, NaN or below zero: the model's to ask
        return f"{product.name}: {count:g} on hand."
    return None


def _outage_reply(context, prompt: str):
    """Ready for the power going out: the first things to do and his own readiness (core/outage_plan.reply); the
    power going out now is the outage clock's (core/outage.py). None otherwise."""
    from core import outage_plan

    try:
        return outage_plan.reply(context, prompt)
    except Exception:
        log.exception("Couldn't answer the outage")
        return None


def _home_trouble_reply(context, prompt: str):
    """A burst or frozen pipe or a flooded basement, in fixed words (core/home_trouble.reply); None otherwise."""
    from core import home_trouble

    return home_trouble.reply(prompt)


def _convert_reply(context, prompt: str):
    """"Convert 5 gallons to liters", "how many cups in a gallon?", "what's 70 degrees fahrenheit in celsius?", in code
    through convert_units (the live sweep, 2026-11-25: the model said only "The conversion is complete."). None when
    the words aren't a conversion or the units aren't ones it knows (the model's then)."""
    found = _CONVERT.match(prompt.replace("’", "'"))
    if not found:
        return None
    value = found.group("v") or found.group("v2") or found.group("v3") or "1"
    from_unit = (found.group("f") or found.group("f2") or found.group("f3") or "").strip()
    to_unit = (found.group("t") or found.group("t2") or found.group("t3") or "").strip()
    from_unit = re.sub(r"^degrees?\s+", "", from_unit, flags=re.I)
    to_unit = re.sub(r"^degrees?\s+", "", to_unit, flags=re.I)
    try:
        said = context.assistant_actions.execute(context, "convert_units", {
            "value": float(value.replace(",", "")), "from_unit": from_unit, "to_unit": to_unit})
    except Exception:
        log.exception("Couldn't convert")
        return None
    return said if said and not str(said).startswith(("I don't recognize", "I need")) else None


def _holiday_reply(context, prompt: str):
    """"When is Thanksgiving?", worked out in code (core/holidays.reply; the live sweep: "I don't have that
    information"). None otherwise."""
    from core import holidays

    try:
        return holidays.reply(context, prompt)
    except Exception:
        log.exception("Couldn't work out the holiday")
        return None


_OVER_BUDGET = re.compile(r"^\s*(?:am i|are we|is anything|anything)\s+(?:over|under)\s+(?:my\s+|our\s+|the\s+)?budgets?"
                          r"(?:\s+(?:anywhere|on anything|at all|this month|yet))?\s*\??\s*$", re.I)


def _spent_on_reply(context, prompt: str):
    """"How much did I spend on groceries this month?", in code from his own expenses (the live sweep, 2026-11-25:
    the money plan's model had said "the fact sheet only mentions..."): the category his words name (`_SPENT_ON`'s
    words, or a category's own name), this month unless he named another period (core/money_periods.period: last
    week, yesterday, last month, in October...). None when the
    words name no category, or there's no budget.
    "Am I over budget anywhere?" is his budgets, each spent against its target (budget_left, `_OVER_BUDGET`).
    A period it can't read ("last week") or two things are the model's; "so far" is all of it. A thing no category
    names ("fishing gear") is the expenses whose description names it (`_spent_by_words`), this year unless said."""
    if _OVER_BUDGET.match(prompt):  # "am I over budget anywhere?": his budgets, from budget_left (the live sweep)
        try:
            return context.assistant_actions.execute(context, "budget_left", {})
        except Exception:
            log.exception("Couldn't read his budgets")
            return None
    found = _SPENT_ON_ASK.match(prompt.replace("’", "'"))
    book = getattr(context, "budget", None)
    if not found or book is None or not hasattr(book, "total_expenses_by_category"):
        return None
    from datetime import date as _date, timedelta

    from core.budget_manager import EXPENSE_CATEGORIES
    from core.region import money

    what = found.group("what").strip()
    if re.search(r"\b(?:last|yesterday|today|week|weekend|year|month|ago|since|in (?:jan|feb|mar|apr|may|jun|jul|aug|"
                 r"sep|oct|nov|dec)\w*|\d{4}|and|or)\b|,", what, re.I):
        return None  # a period it doesn't read ("last week"), or two things: the model's (the eighteenth review)
    category = next((c for c in EXPENSE_CATEGORIES if c.lower() == what.lower()), None)
    category = category or next((c for c, words in _SPENT_ON if re.search(words, what, re.I)), None)
    today = _date.today()
    if category is None:  # "fishing gear": the expenses whose own description names it (the conversation check)
        return _spent_by_words(book, what, found.group("when") or "this year", today)
    when = (found.group("when") or "this month").lower()
    if when == "so far":
        start, end, said = None, today, "so far"
    else:  # any period core/money_periods reads ("last week", "yesterday", "in October")
        from core.money_periods import period

        start, end, said = period(when, today) or (today.replace(day=1), today, "this month")
    try:
        spent = book.total_expenses_by_category(start.isoformat() if start else None, end.isoformat()).get(category, 0.0)
    except Exception:
        log.exception("Couldn't total his spending")
        return None
    if not spent:
        return f"Nothing logged under {category} {said}."
    return f"{money(spent)} on {category} {said}, from what you've logged."


_GENERIC = {"gear", "stuff", "things", "supplies", "equipment", "items", "the", "my", "our", "a", "some", "new"}
# his hobbies' and the homestead's words, said as nothing logged when no expense names them; anything else is the model's
_HOBBY_WORDS = {"fishing", "hunting", "guitar", "woodworking", "camping", "garden", "gardening", "tool", "chicken",
                "fitness", "gym", "archery", "ammo", "bait", "tackle", "lumber", "seed", "soldering", "electronic",
                "arduino", "printer", "filament"}


def _spent_by_words(book, what: str, when: str, today):
    """His household's expenses in the period whose description names the thing ("fishing" for "fishing gear": the
    generic words left out, each a word's start, never inside another word), said with how many; None when the thing
    has no word to look for, or nothing names it and it isn't one of his hobbies' words (`_HOBBY_WORDS`)."""
    from core.money_periods import period
    from core.region import money

    words = [w for w in re.findall(r"[a-z]{3,}", what.lower()) if w not in _GENERIC]
    if not words or not hasattr(book, "all_expenses"):
        return None
    if when.lower() == "so far":
        start, end, said = None, today, "so far"
    else:
        start, end, said = period(when, today) or (today.replace(month=1, day=1), today, "this year")
    stems = [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words]
    hits = [e for e in book.all_expenses() if not getattr(e, "entity_id", "")
            and (start is None or start.isoformat() <= str(e.date)[:10]) and str(e.date)[:10] <= end.isoformat()
            and all(re.search(r"\b" + re.escape(s), str(e.description or ""), re.I) for s in stems)]
    when_said = said if said.split()[0].lower() in ("this", "last", "today", "yesterday", "so") else f"in {said}"
    if not hits:
        if not any(s in _HOBBY_WORDS for s in stems):
            return None  # "the shed", "Sarah", "everything": the model's, as before (the Fable review)
        return (f"Nothing logged {when_said} with \"{' '.join(words)}\" in what it was for, and no budget category "
                f"is {what}. Tell me as you buy (\"I spent $30 on a fishing reel\") and I'll keep count.")
    total = sum(e.amount for e in hits)
    one = len(hits) == 1
    return f"{money(total)} {when_said} on {what}, from {len(hits)} expense{'' if one else 's'} that name{'s' if one else ''} it."


def _materials_reply(context, prompt: str):
    """A materials question with its structure and size, in code (core/assistant_plan_actions.materials_reply: the
    calculators' list, never the model's); None otherwise."""
    from core.assistant_plan_actions import materials_reply

    try:
        return materials_reply(context, prompt)
    except Exception:
        log.exception("Couldn't work out the materials")
        return None


def _lesson_reply(context, prompt: str):
    """A how-to one of her courses teaches, in code (core/lesson_answer.reply: the lesson's steps, why and what to
    watch for, from the course's sources); None otherwise."""
    from core import lesson_answer

    try:
        return lesson_answer.reply(context, prompt)
    except Exception:
        log.exception("Couldn't answer from the lesson")
        return None


def _service_reply(context, prompt: str):
    """What MIA runs on, in code: "what breaks if <a service> stops?", "what does <it> need?", "what do you run on?"
    (core/service_map.py, T-0007); None when the words aren't for it."""
    from core import service_map

    try:
        return service_map.reply(context, prompt)
    except Exception:
        log.exception("Couldn't answer what MIA runs on")
        return None


def _greenhouse_reply(context, prompt: str):
    """The greenhouse node, in code: its setup in order ("let's set up the greenhouse", "what's next?",
    core/greenhouse_setup.py), "take over the greenhouse", "how's the greenhouse?" (core/greenhouse_link.py),
    and setting up its hardware, "flash the safety MCU", "prepare the Pi", "push the greenhouse to ..."
    (core/greenhouse_provision.py), and setting its targets, "set the greenhouse pH minimum to 6.4" then "yes, set it"
    (core/greenhouse_adjust.py); None when the words aren't for it."""
    from core import greenhouse_adjust, greenhouse_link, greenhouse_provision, greenhouse_setup

    try:
        return (greenhouse_adjust.reply(context, prompt) or greenhouse_setup.reply(context, prompt)
                or greenhouse_link.reply(context, prompt) or greenhouse_provision.reply(context, prompt))
    except Exception:
        log.exception("Couldn't follow the greenhouse words")
        return None


def _personal(conversation) -> bool:
    """Whether the conversation is a personal one (talk-it-out or another personal mode, or the private journal):
    no plain-word commands or lookups then.
    """
    from core.conversation_modes import PERSONAL_MODES

    return getattr(conversation, "mode", None) in PERSONAL_MODES or bool(getattr(conversation, "journal", False))


def run_assistant_turn(context: AppContext, conversation: Conversation, prompt: str, surface: str = "") -> AssistantTurn:
    """One turn, traced (core/turn_trace.py): how it was answered, how long it took, and on which device
    ("glasses", "phone"; "" for the PC), for the glasses.voice loop. After the reply, one offer: a note to keep
    (core/life_notes.py), else a way to track what they said they did (core/did_it.py). The whole turn runs under
    one trace id (core/trace.py, DEC-0280), so what it proposed, changed and recorded can be found from it.
    The turn's follow-up note is cleared when it ends, so it is never another turn's."""
    from core import trace
    from core.conversation_state import clear_turn_follow_up

    with trace.tracing():
        try:
            return _traced_turn(context, conversation, prompt, surface)
        finally:
            clear_turn_follow_up()  # the note is this turn's alone


def _traced_turn(context: AppContext, conversation: Conversation, prompt: str, surface: str) -> AssistantTurn:
    """run_assistant_turn's work, under its trace id."""
    from core.turn_trace import record

    started = time.monotonic()
    if conversation is not None:
        conversation.surface = surface  # for a rating said out loud (core/failure_log.py)
    turn = _turn(context, conversation, prompt)
    if turn.route != "fixed":  # never after the safety floor or a reply to the log itself
        from core.life_notes import offer_after

        try:
            offer = offer_after(context, conversation, prompt)
        except Exception:
            log.exception("Couldn't offer to keep a note")
            offer = None
        if offer:  # a promise, decision, idea or goal set aside, offered for a yes (DEC-0054)
            add_message(conversation, "assistant", offer)
            turn.replies.append(offer)
        else:  # what they said they did, kept, and one way to track it offered (DEC-0148)
            from core.did_it import offer_after as did_offer

            try:
                track = did_offer(context, conversation, prompt)
            except Exception:
                log.exception("Couldn't take in what the person did")
                track = None
            if track:
                add_message(conversation, "assistant", track)
                turn.replies.append(track)
    record(context, conversation, prompt, turn, time.monotonic() - started, surface)
    return turn


def _turn(context: AppContext, conversation: Conversation, prompt: str) -> AssistantTurn:
    # Mode switches and the safety floor first (core/talk_it_out.py),
    # before the message is stored, so it's stored with the privacy its
    # own words asked for, and before the model, which the safety floor
    # never waits on.
    """One turn, in order: the lockdown phrase (core/lockdown.py), "stop", "stop everything" and "carry on"
    (core/stop.py), in code, first, then mode switches and the safety floor (before anything is stored or the model asked), then
    show-off, "look at this" (opens Look with the camera), "take me to the garage" (an area's hub, DEC-0130), "show me where it says that" (the library article her last answer came from, core/show_source.py), "show my license" (the ID wallet), "summarize this conversation" and "export this chat" (core/conversation_export.py), a taught skill being shown, started or answered (core/taught_skills.take_turn), a job being walked through (core/trade_actions.py), the greenhouse and its hardware (DEC-0150), what MIA runs on (core/service_map.py), plain-word commands, what they did (core/did_it.py), question plans and direct lookups (none in a personal conversation), then the
    model with the tools offered for what was said; a tool the model calls that wasn't offered isn't run.
    Each turn starts by clearing the last one's follow-up note, and a follow-up to a tool's answer skips the
    question plans and code answers for the model with that tool (core/conversation_state.follows_a_tool).
    A reply that only echoes the question is never said as an answer (ECHO_REPLY).
    An echo of one of his messages from a moment ago is caught too.
    Building an ESP32 lab along with MIA is taken in code there too, before the plans ("walk me through building the
    pot lab", then "next step": core/esp32_sim.reply).
    A scenario drill is taken in code too, after the lab's build ("give me a survival drill", then "B":
    core/drills.reply).
    A design of hers nothing builds yet is said in code as a plan (core/self_knowledge.plan_reply).
    A first-aid how-to is answered in the floor's own words (`_first_aid_reply`).
    His upkeep ("when is my truck due for an oil change?", "the truck needs new brakes": `_upkeep_reply`) and an
    LED's resistor (`_led_reply`) are taken in code too.
    What he spent on a category this month is said from his expenses (`_spent_on_reply`).
    When to start a crop and what's in a 72-hour kit are said from his records (`_garden_kit_reply`).
    Hours on a project are logged and read back in code (`_project_time_reply`); an outlet's voltage is said in fixed
    safe words (`_mains_reply`); a monthly reminder goes on his calendar (`_monthly_reminder_reply`); a unit
    conversion (`_convert_reply`) and a holiday's date (`_holiday_reply`) are worked out in code; a burst pipe or a
    flooded basement is said in fixed words (`_home_trouble_reply`), and when to fish from his catches
    (`_fish_when_reply`), and the power out with his own readiness (`_outage_reply`); the time, days until a holiday,
    square feet, a walk logged and an egg price are worked out in code (`_everyday_reply`); a load's watts are kept
    (`_load_watts_reply`); a bill paid or a product's stock is read from his records (`_records_reply`); the hens,
    the garden's water, the feed and canning go to their own tools (`_own_tool_reply`). A turn the
    model answers ends a question plan's thread
    (core/conversation_state.forget), and a reply that is only a humor example is never said.
    A how-to one of her courses teaches, from its lesson (`_lesson_reply`).
    Days of water: the pantry's and the property's (`_water_on_hand_reply`).
    A materials question with its size, from the calculators (`_materials_reply`).
    A claim of a change no tool made is said honestly; a reminder on a day goes on the calendar.
    A personal or off-the-record turn's claim is never kept in the Fix-It Log.
    The model's reply is polished with his words, so a loosely copied humor example goes.
    A course's next lesson, named, in code (`_next_lesson_reply`).
    A reminder every week goes on the calendar repeating (`_weekly_reminder_reply`).
    What he says he spent is recorded (`_spent_reply`).
    The morning briefing he asks for, set or turned off (`_morning_briefing_reply`).
    A quote from a job's words, a draft for his yes (`_job_quote_reply`).
    A tool call written out as the answer is never said (GARBLED_REPLY).
    A reminder every day goes on the calendar daily (`_daily_reminder_reply`).
    A plain go-ahead ("ok, start it") to her own 'Say "..." and I'll ...' runs those words
    (core/conversation_state.offered_phrase); a short follow-up to a code answer is made whole
    (`_follow_through_reply`); the sentence is put in the shape her routes read (`reshaped`: a greeting before a
    question set aside, "every Saturday morning remind me to ..." as "remind me every Saturday to ... at 8am").
    A reply is taken for a tool call only when it names one of her tools. The model's "the fact sheet" is never said
    aloud (response_composer.without_sheet_words, on the model's words only).
    Two logs in one sentence ("I spent $40 on screws and 2 hours on the shed") are each kept by their own code
    (`_two_things_reply`), before a single expense could take the whole sentence.
    """
    from core import stop  # "stop", "stop everything", "carry on": in code, before anything else (REQ-AUT-010)

    from core import lockdown
    from core.conversation_state import follows_a_tool, set_turn_follow_up

    set_turn_follow_up(prompt)  # a new turn: the last one's follow-up words never reach this one's lookups
    tool_follow = follows_a_tool(context, conversation, prompt)
    stopped = lockdown.handle(context, prompt) or stop.handle(context, prompt)
    if stopped is not None:
        add_message(conversation, "user", prompt)
        add_message(conversation, "assistant", stopped)
        return AssistantTurn(replies=[stopped], route="fixed")
    prepared = pre_turn(context, conversation, prompt)
    from core.conversation_state import offered_phrase

    offered = offered_phrase(conversation, prompt)  # "ok, start it" to her 'Say "..." and I'll ...': those words
    add_message(conversation, "user", prompt)
    if offered and prepared.fixed_reply is None:
        prompt = offered
    if prepared.fixed_reply is None:  # the shape her routes read: a greeting before a question, the weekday first
        prompt = reshaped(prompt)
    if prepared.fixed_reply is not None:
        add_message(conversation, "assistant", prepared.fixed_reply)
        after_fixed_reply(context, conversation)
        return AssistantTurn(replies=[prepared.fixed_reply], route="fixed")
    # Plain-word commands ("workout complete", "I weigh 182", "undo that"),
    # done by MIA's own code at once, no model (core/quick_commands.py).
    # Never in a private journal or talk-it-out mode.
    if not _personal(conversation):
        from core.show_off import INTRO, wants_show_off

        if wants_show_off(prompt):  # "show off for my friends" (DEC-0031)
            add_message(conversation, "assistant", INTRO)
            return AssistantTurn(replies=[INTRO], open="showoff.html", route="show off")
        from core.sight import LOOK_REPLY, wants_look

        looking = wants_look(prompt)  # "look at this": Look opens with the camera (DEC-0125)
        if looking is not None:
            from urllib.parse import quote

            add_message(conversation, "assistant", LOOK_REPLY)
            return AssistantTurn(replies=[LOOK_REPLY], open=f"look.html?camera=1&ask={quote(looking)}", route="look")
        from core.web_nexus import wants_area

        going = wants_area(prompt)  # "take me to the garage" (DEC-0130): the area's hub opens at once
        if going is not None:
            said = f"Opening {going[1]}."
            add_message(conversation, "assistant", said)
            return AssistantTurn(replies=[said], open=going[0], route="area")
        from core import show_source
        from core.person_settings import person_id

        source = show_source.reply(person_id(context), prompt)  # "show me where it says that" (brainstorm 3.2)
        if source is not None:
            add_message(conversation, "assistant", source[0])
            return AssistantTurn(replies=[source[0]], open=source[1], route="source")
        from core.id_wallet import wants_card

        card = wants_card(context, prompt)  # "show my driver's license": the card opens on screen, its number never said
        if card is not None:
            said = f"Here's your {card[1]}."
            add_message(conversation, "assistant", said)
            return AssistantTurn(replies=[said], open=card[0], route="wallet")
        from core.conversation_export import reply as taken_out

        try:  # "summarize this conversation", "export this chat as JSON": the whole of it, not its last messages
            out = taken_out(context, conversation, prompt)
        except Exception:
            log.exception("Couldn't summarise or export the conversation")
            out = None
        if out is not None:
            add_message(conversation, "assistant", out[0])
            return AssistantTurn(replies=[out[0]], open=out[1], route="conversation")
        from core.taught_skills import take_turn

        try:  # "watch me: ...", "that's it", "run <a taught skill>", the answer a running skill asked for (DEC-0123)
            last = next((m.content for m in reversed(conversation.messages[:-1]) if m.role == "assistant"), "")
            taught = take_turn(context, last, prompt)
        except Exception:
            log.exception("Couldn't follow the taught skill")
            taught = None
        if taught is not None:
            add_message(conversation, "assistant", taught)
            return AssistantTurn(replies=[taught], route="taught skill")
        from core.trade_actions import reply as job_reply

        try:  # a job in progress ("next", "checked", "why?", a stop rule's words) or "walk me through ..." (DEC-0149)
            walked = job_reply(context, prompt)
        except Exception:
            log.exception("Couldn't follow the job")
            walked = None
        if walked is None:
            walked = _greenhouse_reply(context, prompt)  # "take over the greenhouse", "flash the safety MCU" (DEC-0150)
        if walked is None:
            walked = _service_reply(context, prompt)  # "what breaks if Ollama stops?" (core/service_map.py, T-0007)
        if walked is None:
            walked = _lab_build_reply(context, conversation, prompt)  # "walk me through building the pot lab", "next"
        if walked is None:
            walked = _drill_reply(context, conversation, prompt)  # "give me a survival drill", then "B"
        if walked is None:
            walked = _first_aid_reply(context, prompt)  # "how do you use a tourniquet?": the floor's own words
        if walked is None:
            walked = _lesson_reply(context, prompt)  # "how do I purify water from a creek?": her course's lesson
        if walked is None:
            walked = _water_on_hand_reply(context, prompt)  # days of water: the pantry's and the property's
        if walked is None:
            walked = _job_quote_reply(context, prompt)  # a quote from a job's words: a draft for his yes
        if walked is None:
            walked = _materials_reply(context, prompt)  # a structure and its size: the calculators' list
        if walked is None:
            walked = _next_lesson_reply(context, prompt)  # a course's next step, or that it isn't started
        if walked is None:
            walked = _reminder_reply(context, prompt)  # "remind me to X on Saturday": on his calendar
        if walked is None:
            walked = _weekly_reminder_reply(context, prompt)  # "every Monday": a weekly event on his calendar
        if walked is None:
            walked = _monthly_reminder_reply(context, prompt)  # "every month": a monthly event on his calendar
        if walked is None:
            walked = _daily_reminder_reply(context, prompt)  # "every morning": a daily event on his calendar
        if walked is None:
            walked = _two_things_reply(context, prompt)  # two logs in one sentence: each its own, said together
        if walked is None:
            walked = _spent_reply(context, prompt)  # "I spent $30 on groceries": an expense, undoable
        if walked is None:
            walked = _upkeep_reply(context, prompt)  # his upkeep: when a task is due, a need added as a task
        if walked is None:
            walked = _led_reply(context, prompt)  # an LED's resistor, worked out in code
        if walked is None:
            walked = _spent_on_reply(context, prompt)  # what he spent on a category, from his expenses
        if walked is None:
            walked = _garden_kit_reply(context, prompt)  # a crop's dates from his frost, the kit against his records
        if walked is None:
            walked = _project_time_reply(context, prompt)  # the hours he puts into his projects, logged and read
        if walked is None:
            walked = _mains_reply(context, prompt)  # an outlet's voltage: a tester first, an electrician if off
        if walked is None:
            walked = _home_trouble_reply(context, prompt)  # the house's trouble: the main shutoff, the power first
        if walked is None:
            walked = _outage_reply(context, prompt)  # the power out: the first things, then his own stores
        if walked is None:
            walked = _follow_through_reply(context, conversation, prompt)  # a follow-up to a code answer, made whole
        if walked is None:
            walked = _records_reply(context, prompt)  # a bill paid or not, a product's stock, from his records
        if walked is None:
            walked = _own_tool_reply(context, prompt)  # the homestead's own answers the model passed over
        if walked is None:
            walked = _load_watts_reply(context, prompt)  # a load's watts, kept for the power picture
        if walked is None:
            walked = _everyday_reply(context, prompt)  # the time, days until, square feet, a walk, an egg price
        if walked is None:
            walked = _fish_when_reply(context, prompt)  # when to fish, from his own catches and the weather
        if walked is None:
            walked = _convert_reply(context, prompt)  # a unit conversion, worked out by the converter
        if walked is None:
            walked = _holiday_reply(context, prompt)  # a holiday's date, worked out
        if walked is None:
            walked = _morning_briefing_reply(context, prompt)  # the morning briefing he asks for, set or off
        if walked is None:
            walked = _plan_reply(prompt)  # "what is the Life Enrichment Protocol?": a plan, said as one
        if walked is not None:
            add_message(conversation, "assistant", walked)
            return AssistantTurn(replies=([prepared.notice] if prepared.notice else []) + [walked], route="code")
        from core.quick_commands import handle

        quick = handle(context, prompt)
        if quick is None:
            from core.did_it import reply as did_reply

            try:  # "I just put away the dishes and started the laundry" (DEC-0148): kept, counted, one offer, by
                did = did_reply(context, conversation, prompt)  # code; after the quick commands (a workout, a meal)
            except Exception:
                log.exception("Couldn't take in what the person did")
                did = None
            if did is not None:
                add_message(conversation, "assistant", did)
                return AssistantTurn(replies=([prepared.notice] if prepared.notice else []) + [did], route="code")
        if quick is None:
            # A detailed question a plan answers: lookups by code, one answer (DEC-0052, core/question_plans.py).
            from core.question_plans import answer as plan_answer

            # A question about MIA herself isn't one about the person's records (core/self_knowledge.py).
            # A follow-up to a tool's answer is the model's, with that tool (core/conversation_state.follows_a_tool).
            planned = None if (_about_her(prompt) or tool_follow) else plan_answer(context, conversation, prompt)
            if planned is not None:
                said, _sheet = planned
                add_message(conversation, "assistant", said)
                return AssistantTurn(replies=([prepared.notice] if prepared.notice else []) + [said],
                                     route=f"plan: {_sheet.plan}")
            quick = None if tool_follow else _direct_lookup(context, prompt)
        if quick is not None:
            add_message(conversation, "assistant", quick)
            return AssistantTurn(replies=([prepared.notice] if prepared.notice else []) + [quick], route="code")
    from core import conversation_state

    # the model answers this one, so the plan's thread is over: "how much space do they need?" two turns after "I'm
    # thinking about getting goats" is no follow-up to the project picture (the live sweep, 2026-11-25)
    conversation_state.forget(conversation)
    notices = []
    if prepared.notice:
        add_message(conversation, "assistant", prepared.notice)
        notices.append(prepared.notice)

    if context.llm is None:
        _observe(context, conversation, prompt, [], llm_available=False)
        return AssistantTurn(replies=notices, llm_available=False, route="no model")
    started = time.monotonic()
    messages, tools = build_chat_request(context, conversation, prompt)
    used = memories_used(context, prompt, messages)
    from core.tool_loop import run as run_loop  # lookups combined into one answer (DEC-0052)

    reply = run_loop(context, context.llm, messages, tools, prompt, named_tool(context, prompt, tools))
    offered = [t.get("function", {}).get("name", "") for t in tools]
    if reply is None:
        _observe(context, conversation, prompt, offered, llm_available=False)
        return AssistantTurn(replies=notices, llm_available=False, route="model, no answer", tools_offered=offered)

    if reply.tool_calls:
        calls_to_execute, skipped_calls = split_safe_tool_calls(reply.tool_calls, context.assistant_actions)
        if skipped_calls:
            skipped_names = ", ".join(tc.name for tc in skipped_calls)
            log.warning("Skipped destructive tool call(s) bundled with other calls in one reply: %s", skipped_names)
        replies = list(notices)
        for tool_call in calls_to_execute:
            if tool_call.name not in offered:  # only a tool offered this turn runs (2026-11-10)
                log.warning("The model called %s, which wasn't offered this turn; not run.", tool_call.name)
                confirmation = "I got that mixed up on my end. Could you say it another way?"
            else:
                confirmation = context.assistant_actions.execute(context, tool_call.name,
                                                                 with_his_day(tool_call.name, tool_call.arguments, prompt))
            add_message(conversation, "assistant", confirmation)
            replies.append(confirmation)
        called = calls_to_execute[0].name if calls_to_execute else ""
        offer = _observe(context, conversation, prompt, offered, tool_called=called, reply=" ".join(replies),
                         seconds=time.monotonic() - started)
        if offer:
            replies.append(offer)
        return AssistantTurn(replies=replies, used=used, route="model, tools", tools_offered=offered,
                             tools_called=[c.name for c in calls_to_execute])

    from core.response_composer import polish, without_sheet_words

    # Her own words without the model's habitual "Sure!" first and "let me know" last, on every surface, not
    # only the phone (docs/CONVERSATION_REVIEW.md), and never "the fact sheet" (her working) said aloud. An offer of
    # hers to do something stays.
    content = with_offer(conversation, polish(without_sheet_words(reply.content), prompt))
    from core.claim_check import honest

    content = honest(context, prompt, content, keep=not _personal(conversation)
                     and not getattr(conversation, "off_record", False))  # never "I've added a reminder" (claim_check)
    earlier = [m.content for m in (getattr(conversation, "messages", None) or [])[-6:] if m.role == "user"]
    from core.offline_library import FROM_WHAT_YOU_KNOW
    from core.personality import only_example

    if FROM_WHAT_YOU_KNOW in content:  # the library's note to the model, said back (the live sweep): never to him
        content = content.replace(FROM_WHAT_YOU_KNOW, "").replace(
            "The offline library has no packs yet (they can be fetched on the Knowledge page).", "").strip() or ECHO_REPLY

    if echoes(content, prompt) or any(echoes(content, said) for said in earlier) or only_example(content):
        content = ECHO_REPLY  # never the person's own words, or a humor example alone, said back as if an answer
    if _garbled(content, context):
        content = GARBLED_REPLY  # never a tool call written out as the answer, even after the retry without tools
    add_message(conversation, "assistant", content)
    _observe(context, conversation, prompt, offered, reply=content, seconds=time.monotonic() - started,
             garbled=_garbled(reply.content))
    return AssistantTurn(replies=notices + [content], followup=plan_followup(context, conversation, prompt), used=used,
                         route="model", tools_offered=offered)


def _defines(text: str) -> bool:
    """Whether the JSON is a function definition: a "description" beside its name, never inside the arguments
    (the sixteenth review: a made-up call whose arguments had a description had leaked as raw JSON).
    Parameters that are a schema ("properties") make it a definition too."""
    import json

    try:
        whole = json.loads(text)
        schema = isinstance(whole, dict) and isinstance(whole.get("parameters"), dict) and "properties" in whole["parameters"]
        return isinstance(whole, dict) and ("description" in whole or schema)
    except ValueError:
        found = re.search(r'"(?:parameters|arguments|args|input)"\s*:', text)
        return bool(found) and ('"description"' in text[:found.start()]
                                or bool(re.match(r'\s*\{\s*"properties"', text[found.end():])))


def _garbled(content: str, context=None) -> bool:
    """Whether the model's reply is a tool call written as text instead of made (a malformed call); with a context, only
    when the name it gives is one of her tools (the twelfth review: a JSON example he asked for, {"name": "Zac"}, had
    been replaced).
    With a context: a call's shape (a name, then parameters, arguments, args or input), as the whole reply or one
    fenced block, naming one of her tools in any case or a made-up snake_case one; never {"name": "Zac", "age": 30}
    or a fenced example with words around it.
    The name may sit anywhere in the object; a fenced block counts only when it names one of her tools, a made-up
    snake_case name only unfenced with parameters or arguments.
    A function definition he asked for (a "description" beside its parameters) is an answer.
    A description inside the arguments is still a call (`_defines`).
    Inside qwen's <tool_call> tags too, and one of hers named with nothing else ({"name": "list_alarms"})."""
    from core.llm_manager import _looks_like_malformed_tool_call

    try:
        if not _looks_like_malformed_tool_call(content):
            return False
    except Exception:
        return False
    if context is None:
        return True
    from core.llm_manager import untagged

    text = untagged(content)  # inside qwen's <tool_call> tags too (the Fable review)
    fenced = re.fullmatch(r"```(?:json)?\s*(.+?)\s*```", text, re.S)
    if text.startswith("```") and not fenced:
        return False  # a fenced example with words around it is an explanation
    text = fenced.group(1) if fenced else text
    if not text.lstrip().startswith("{"):
        return False
    named = re.search(r'"(?:name|function|tool)"\s*:\s*"([\w.]+)"', text)  # wherever it sits (the fourteenth review)
    tools = {str(t).lower() for t in (getattr(getattr(context, "assistant_actions", None), "_actions", {}) or {})}
    if named and named.group(1).lower() in tools and re.fullmatch(r'\{\s*"(?:name|function|tool)"\s*:\s*"[\w.]+"\s*\}',
                                                                  text.strip()):
        return True  # {"name": "list_alarms"}: one of hers, called with nothing (the Fable review)
    if not named or not re.search(r'"(?:parameters|arguments|args|input)"\s*:', text):
        return False  # {"name": "Zac", "age": 30} is an answer
    name = named.group(1)
    if name.lower() in tools:
        return True  # one of hers, in any case
    # a made-up tool's snake_case name, only unfenced and with parameters or arguments: a fenced function-call example
    # he asked for ("get_current_weather") is an answer
    return (not fenced and "_" in name and bool(re.search(r'"(?:parameters|arguments)"\s*:', text))
            and not _defines(text))  # a function definition he asked for is an answer


def echoes(content: str, prompt: str) -> bool:
    """Pure logic. Whether the model's reply is only the person's own words back ("How's my training going this
    week?" answered with itself: the live check through the whole turn, 2026-11-24)."""
    def norm(text):
        return " ".join(re.findall(r"[a-z0-9']+", str(text or "").lower()))

    said = norm(content)
    return bool(said) and said == norm(prompt)


ECHO_REPLY = "I didn't get an answer together for that one. Ask me again, or in other words, and I'll try once more."
GARBLED_REPLY = ("I got that mixed up on my end and didn't do it. Say it again, maybe in other words, and I'll try "
                 "once more.")


def _observe(context, conversation, prompt: str, offered: list, **outcome) -> Optional[str]:
    """Where MIA stumbled this turn (core/failure_log.py); never in the way of the answer."""
    from core.failure_log import observe_turn

    try:
        return observe_turn(context, conversation, prompt, tools_offered=offered, **outcome)
    except Exception:
        log.exception("The failure log couldn't record this turn")
        return None


def memories_used(context, prompt: str, messages: list[dict]) -> list[dict]:
    """The memories the model was actually given this turn: the turn's
    memories that made it into the system message (an action request's
    lean prompt carries none)."""
    from core.assistant_chat import turn_memories

    system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
    return [{"id": m.memory_id, "text": m.text, "category": m.category}
            for m in turn_memories(context, prompt) if m.text and m.text in system]


def run_followup(context: AppContext, conversation: Conversation, followup: Optional[Followup]) -> None:
    """The after-reply background job: memory extraction, or organizing
    a journal session. Call after the reply is spoken/sent."""
    if followup is None or context.llm is None:
        return
    apply_followup(context, conversation, followup, context.llm.generate(followup.prompt))
