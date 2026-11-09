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
"""

from __future__ import annotations

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
    still go to the help docs."""
    from core.assistant_chat import looks_like_how_to_question, looks_like_teaching_request

    registry = getattr(context, "assistant_actions", None)
    if registry is None or looks_like_how_to_question(prompt) or looks_like_teaching_request(prompt):
        return None
    action = registry.direct_lookup(prompt, context)
    return registry.execute(context, action.name, action.direct_arguments(prompt)) if action is not None else None


def instant_answer(context, conversation, prompt: str) -> Optional[str]:
    """For the desktop's chat panels, which build their own model request
    (2026-10-30: they never got these): a plain-word command done by code
    ("workout complete", "undo that"), a job being walked through ("next",
    "checked", core/trade_actions.py), the greenhouse and its hardware
    ("take over the greenhouse", "flash the safety MCU", DEC-0150), what they did ("I put away the
    dishes", core/did_it.py), or a question one lookup answers, run by
    code, no model; None when a question plan will answer (it comes
    first, as in run_assistant_turn) or it's for the model. Never in a
    personal mode or the journal."""
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
    from core.conversation_state import follow_up
    from core.question_plans import match

    if match(context, prompt) is not None or follow_up(conversation, prompt) is not None:
        return None
    return _direct_lookup(context, prompt)


def _greenhouse_reply(context, prompt: str):
    """The greenhouse node, in code: "take over the greenhouse", "how's the greenhouse?" (core/greenhouse_link.py),
    and setting up its hardware, "flash the safety MCU", "prepare the Pi", "push the greenhouse to ..."
    (core/greenhouse_provision.py); None when the words aren't for it."""
    from core import greenhouse_link, greenhouse_provision

    try:
        return greenhouse_link.reply(context, prompt) or greenhouse_provision.reply(context, prompt)
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
    (core/life_notes.py), else a way to track what they said they did (core/did_it.py)."""
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
    """One turn, in order: mode switches and the safety floor (before anything is stored or the model asked), then
    show-off, "look at this" (opens Look with the camera), "take me to the garage" (an area's hub, DEC-0130), "show my license" (the ID wallet), a job being walked through (core/trade_actions.py), the greenhouse and its hardware (DEC-0150), plain-word commands, what they did (core/did_it.py), question plans and direct lookups (none in a personal conversation), then the
    model with the tools offered for what was said.
    """
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
        from core.id_wallet import wants_card

        card = wants_card(context, prompt)  # "show my driver's license": the card opens on screen, its number never said
        if card is not None:
            said = f"Here's your {card[1]}."
            add_message(conversation, "assistant", said)
            return AssistantTurn(replies=[said], open=card[0], route="wallet")
        from core.trade_actions import reply as job_reply

        try:  # a job in progress ("next", "checked", "why?", a stop rule's words) or "walk me through ..." (DEC-0149)
            walked = job_reply(context, prompt)
        except Exception:
            log.exception("Couldn't follow the job")
            walked = None
        if walked is None:
            walked = _greenhouse_reply(context, prompt)  # "take over the greenhouse", "flash the safety MCU" (DEC-0150)
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

            planned = plan_answer(context, conversation, prompt)
            if planned is not None:
                said, _sheet = planned
                add_message(conversation, "assistant", said)
                return AssistantTurn(replies=([prepared.notice] if prepared.notice else []) + [said],
                                     route=f"plan: {_sheet.plan}")
            quick = _direct_lookup(context, prompt)
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
            confirmation = context.assistant_actions.execute(context, tool_call.name, tool_call.arguments)
            add_message(conversation, "assistant", confirmation)
            replies.append(confirmation)
        called = calls_to_execute[0].name if calls_to_execute else ""
        offer = _observe(context, conversation, prompt, offered, tool_called=called, reply=" ".join(replies),
                         seconds=time.monotonic() - started)
        if offer:
            replies.append(offer)
        return AssistantTurn(replies=replies, used=used, route="model, tools", tools_offered=offered,
                             tools_called=[c.name for c in calls_to_execute])

    content = with_offer(conversation, reply.content)
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
