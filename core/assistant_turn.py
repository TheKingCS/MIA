"""
core.assistant_turn
=====================

One Assistant turn — user text in, the things MIA should say back out —
shared by every voice surface: the headless Core loop
(`core/voice_loop.py`) and the phone voice endpoint (`server/app.py`).
Pulled out of `VoiceLoopController._handle_turn()` unchanged in
behavior, so both surfaces answer, act, and skip destructive bundled
tool calls identically instead of drifting apart.

Memory extraction is deliberately returned as a follow-up
(`AssistantTurn.remember_from`) rather than run inline: it's a second
LLM call, and running it before the reply is spoken/sent would add its
full latency to every answer. Callers speak/send first, then call
`extract_memories()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.app_context import AppContext
from core.assistant_chat import (
    build_chat_request,
    build_memory_extraction_prompt,
    parse_extracted_memories,
    split_safe_tool_calls,
)
from core.conversation_manager import Conversation, ConversationMessage
from core.logger import get_logger

log = get_logger(__name__)


@dataclass
class AssistantTurn:
    replies: list[str] = field(default_factory=list)  # each thing MIA should say, in order
    remember_from: Optional[str] = None  # user text to run extract_memories() on, if any
    llm_available: bool = True


def add_message(conversation: Conversation, role: str, content: str) -> None:
    conversation.messages.append(
        ConversationMessage(role=role, content=content, timestamp=datetime.now(timezone.utc).isoformat())
    )


def run_assistant_turn(context: AppContext, conversation: Conversation, prompt: str) -> AssistantTurn:
    add_message(conversation, "user", prompt)

    if context.llm is None:
        return AssistantTurn(llm_available=False)
    messages, tools = build_chat_request(context, conversation, prompt)
    reply = context.llm.chat_with_tools(messages, tools)
    if reply is None:
        return AssistantTurn(llm_available=False)

    if reply.tool_calls:
        calls_to_execute, skipped_calls = split_safe_tool_calls(reply.tool_calls, context.assistant_actions)
        if skipped_calls:
            skipped_names = ", ".join(tc.name for tc in skipped_calls)
            log.warning("Skipped destructive tool call(s) bundled with other calls in one reply: %s", skipped_names)
        replies = []
        for tool_call in calls_to_execute:
            confirmation = context.assistant_actions.execute(context, tool_call.name, tool_call.arguments)
            add_message(conversation, "assistant", confirmation)
            replies.append(confirmation)
        return AssistantTurn(replies=replies)

    add_message(conversation, "assistant", reply.content)
    return AssistantTurn(replies=[reply.content], remember_from=prompt)


def extract_memories(context: AppContext, conversation_id: str, user_message: str) -> None:
    if context.user_memories is None or context.llm is None:
        return
    raw = context.llm.generate(build_memory_extraction_prompt(user_message))
    for category, fact in parse_extracted_memories(raw):
        context.user_memories.add_memory(fact, category=category, source_conversation_id=conversation_id)
