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

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.app_context import AppContext
from core.assistant_chat import build_chat_request, named_tool, settle_on_named_tool, split_safe_tool_calls
from core.conversation_manager import Conversation, ConversationMessage
from core.logger import get_logger
from core.talk_it_out import Followup, after_fixed_reply, apply_followup, plan_followup, pre_turn, with_offer

log = get_logger(__name__)


@dataclass
class AssistantTurn:
    replies: list[str] = field(default_factory=list)  # each thing MIA should say, in order
    followup: Optional[Followup] = None  # background job for run_followup(), if any
    llm_available: bool = True
    # What I Used (DEC-0029): the memories this turn's answer was given,
    # so a surface can show them under the reply, each fixable or forgettable.
    used: list[dict] = field(default_factory=list)
    # A page for the surface to open (show-off mode's tour, DEC-0031).
    open: str = ""


def add_message(conversation: Conversation, role: str, content: str) -> None:
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


def _personal(conversation) -> bool:
    from core.conversation_modes import PERSONAL_MODES

    return getattr(conversation, "mode", None) in PERSONAL_MODES or bool(getattr(conversation, "journal", False))


def run_assistant_turn(context: AppContext, conversation: Conversation, prompt: str) -> AssistantTurn:
    # Mode switches and the safety floor first (core/talk_it_out.py),
    # before the message is stored, so it's stored with the privacy its
    # own words asked for, and before the model, which the safety floor
    # never waits on.
    prepared = pre_turn(context, conversation, prompt)
    add_message(conversation, "user", prompt)
    if prepared.fixed_reply is not None:
        add_message(conversation, "assistant", prepared.fixed_reply)
        after_fixed_reply(context, conversation)
        return AssistantTurn(replies=[prepared.fixed_reply])
    # Plain-word commands ("workout complete", "I weigh 182", "undo that"),
    # done by MIA's own code at once, no model (core/quick_commands.py).
    # Never in a private journal or talk-it-out mode.
    if not _personal(conversation):
        from core.show_off import INTRO, wants_show_off

        if wants_show_off(prompt):  # "show off for my friends" (DEC-0031)
            add_message(conversation, "assistant", INTRO)
            return AssistantTurn(replies=[INTRO], open="showoff.html")
        from core.quick_commands import handle

        quick = handle(context, prompt)
        if quick is None:
            quick = _direct_lookup(context, prompt)
        if quick is not None:
            add_message(conversation, "assistant", quick)
            return AssistantTurn(replies=([prepared.notice] if prepared.notice else []) + [quick])
    notices = []
    if prepared.notice:
        add_message(conversation, "assistant", prepared.notice)
        notices.append(prepared.notice)

    if context.llm is None:
        return AssistantTurn(replies=notices, llm_available=False)
    messages, tools = build_chat_request(context, conversation, prompt)
    used = memories_used(context, prompt, messages)
    reply = context.llm.chat_with_tools(messages, tools)
    reply = settle_on_named_tool(named_tool(context, prompt, tools), messages, tools, reply, context.llm.chat_with_tools)
    if reply is None:
        return AssistantTurn(replies=notices, llm_available=False)

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
        return AssistantTurn(replies=replies, used=used)

    content = with_offer(conversation, reply.content)
    add_message(conversation, "assistant", content)
    return AssistantTurn(replies=notices + [content], followup=plan_followup(context, conversation, prompt), used=used)


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
