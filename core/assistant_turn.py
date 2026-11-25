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
    A weekly reminder too (`_weekly_reminder_reply`)."""
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
        walked = _materials_reply(context, prompt)  # "how many fence posts for 200 feet?", as in a turn
    if walked is None:
        walked = _next_lesson_reply(context, prompt)  # "what's my next guitar lesson?", as in a turn
    if walked is None:
        walked = _reminder_reply(context, prompt)  # "remind me to check the oil Saturday", as in a turn
    if walked is None:
        walked = _weekly_reminder_reply(context, prompt)  # "remind me every Monday to ...", as in a turn
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


_EVERY = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_REMIND_EVERY = re.compile(
    r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?"
    r"(?:remind me (?:to\s+(?P<what1>.+?)\s+)?every\s+" + _EVERY + r"(?:\s+to\s+(?P<what2>.+?))?|"
    r"(?:automate|set up|add|make|create|schedule)\s+(?:a\s+)?(?:weekly\s+)?reminder\s+(?:for\s+)?every\s+"
    + _EVERY.replace("(", "(?P<day2>", 1) + r"\s+to\s+(?P<what3>.+?))"
    r"(?:\s+at\s+(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm)?)?\s*[.!?]?\s*$", re.I)


def _weekly_reminder_reply(context, prompt: str):
    """"Remind me every Monday to check the water filter", "can you automate a reminder every Monday to ...", in code
    (live sweep, 2026-11-25: no tool was called, and the model promised a notification about the electric bill): a
    weekly event on his calendar from the next one of that weekday, through add_calendar_event (undoable). None
    otherwise."""
    from datetime import date as _date, timedelta

    found = _REMIND_EVERY.match(prompt.replace("’", "'"))
    if not found:
        return None
    what = (found.group("what1") or found.group("what2") or found.group("what3") or "").strip().rstrip(",")
    weekday = (found.group(2) or found.group("day2") or "").lower()
    if not what or not weekday:
        return None
    today = _date.today()
    first = today + timedelta(days=(_WEEKDAYS.index(weekday) - today.weekday()) % 7)
    args = {"title": what[:1].upper() + what[1:], "date": first.isoformat(), "recurrence": "weekly"}
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
    Evening only for "tonight" or a day's evening; "tonight at 12" sets no time."""
    found = _REMIND_ON.match(prompt.replace("’", "'"))
    if not found or re.search(r"\b(?:every|each)\b", found.group(1), re.I):
        return None
    what = found.group(1).strip().rstrip(",")
    args = with_his_day("add_calendar_event", {"title": what[:1].upper() + what[1:]}, prompt)
    evening = re.search(r"\btonight\b|\b(?:this|tomorrow|" + "|".join(_WEEKDAYS) + r")\s+(?:evening|night)\b", prompt,
                        re.I)  # never "night crawlers" or "game night saturday" (the eighth review)
    if "date" not in args:
        return None
    if found.group(3):
        hour, minute = int(found.group(3)), int(found.group(4) or 0)
        if evening and not found.group(5) and hour == 12:
            hour = 99  # "tonight at 12": noon or midnight? no time rather than a wrong one
        hour += 12 if ((found.group(5) or "").lower() == "pm" or (evening and not found.group(5))) and hour < 12 \
            else 0  # "tonight at 9" is 9 pm (the seventh review)
        hour = 0 if (found.group(5) or "").lower() == "am" and hour == 12 else hour
        if hour < 24 and minute < 60:
            args["time"] = f"{hour:02d}:{minute:02d}"
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
    A how-to one of her courses teaches, from its lesson (`_lesson_reply`).
    Days of water: the pantry's and the property's (`_water_on_hand_reply`).
    A materials question with its size, from the calculators (`_materials_reply`).
    A claim of a change no tool made is said honestly; a reminder on a day goes on the calendar.
    A personal or off-the-record turn's claim is never kept in the Fix-It Log.
    The model's reply is polished with his words, so a loosely copied humor example goes.
    A course's next lesson, named, in code (`_next_lesson_reply`).
    A reminder every week goes on the calendar repeating (`_weekly_reminder_reply`).
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
    add_message(conversation, "user", prompt)
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
            walked = _materials_reply(context, prompt)  # a structure and its size: the calculators' list
        if walked is None:
            walked = _next_lesson_reply(context, prompt)  # a course's next step, or that it isn't started
        if walked is None:
            walked = _reminder_reply(context, prompt)  # "remind me to X on Saturday": on his calendar
        if walked is None:
            walked = _weekly_reminder_reply(context, prompt)  # "every Monday": a weekly event on his calendar
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

    from core.response_composer import polish

    # Her own words without the model's habitual "Sure!" first and "let me know" last, on every surface, not
    # only the phone (docs/CONVERSATION_REVIEW.md). An offer of hers to do something stays.
    content = with_offer(conversation, polish(reply.content, prompt))
    from core.claim_check import honest

    content = honest(context, prompt, content, keep=not _personal(conversation)
                     and not getattr(conversation, "off_record", False))  # never "I've added a reminder" (claim_check)
    earlier = [m.content for m in (getattr(conversation, "messages", None) or [])[-6:] if m.role == "user"]
    if echoes(content, prompt) or any(echoes(content, said) for said in earlier):
        content = ECHO_REPLY  # never the person's own words (now or a moment ago) said back as if an answer
    add_message(conversation, "assistant", content)
    _observe(context, conversation, prompt, offered, reply=content, seconds=time.monotonic() - started,
             garbled=_garbled(reply.content))
    return AssistantTurn(replies=notices + [content], followup=plan_followup(context, conversation, prompt), used=used,
                         route="model", tools_offered=offered)


def _garbled(content: str) -> bool:
    """Whether the model's reply is a tool call written as text instead of made (a malformed call)."""
    from core.llm_manager import _looks_like_malformed_tool_call

    try:
        return bool(_looks_like_malformed_tool_call(content))
    except Exception:
        return False


def echoes(content: str, prompt: str) -> bool:
    """Pure logic. Whether the model's reply is only the person's own words back ("How's my training going this
    week?" answered with itself: the live check through the whole turn, 2026-11-24)."""
    def norm(text):
        return " ".join(re.findall(r"[a-z0-9']+", str(text or "").lower()))

    said = norm(content)
    return bool(said) and said == norm(prompt)


ECHO_REPLY = "I didn't get an answer together for that one. Ask me again, or in other words, and I'll try once more."


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
