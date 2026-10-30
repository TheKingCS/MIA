"""
core.tool_loop
================

The tool loop (DEC-0052 step 2b; docs/REASONING_PLAN.md section 3b;
docs/TOOL_CALLING_RESEARCH.md R4). Before: a turn was one round; the
model picked lookups, MIA said each result as it was, and nothing was
combined or followed up. Now, when the model asks only to *look things
up*:

1. the lookups run and their results go back to the model, short
   (a long result is cut to its first `RESULT_CHARS` characters);
2. it may look up more, up to `MAX_STEPS` rounds, inside the time
   budget (`assistant.answer_budget_seconds`, 60 by Zac's call), never
   the same lookup twice;
3. it writes one answer from the results, and an answer that states a
   number the results don't hold is replaced by the results themselves
   (`core.question_plans.invented_numbers`).

A change (anything that writes records) is never run inside the loop:
the reply goes back to the caller as before, through the usual path. The
loop runs only against this computer's Ollama (the phone's small model
keeps one round). Pure orchestration: `run()` calls the model and the
lookups it's given; the desktop runs it on its ChatWorker thread, the
web and voice inside `run_assistant_turn`.
"""

from __future__ import annotations

import time
from typing import Optional

from core.llm_manager import ChatReply, ToolCall
from core.logger import get_logger

log = get_logger(__name__)

MAX_STEPS = 3
RESULT_CHARS = 1500
DEFAULT_BUDGET = 60.0

FOLLOW_UP = (
    "Those are the results of the lookups. If one more lookup would answer the person's question better, call it. "
    "Otherwise answer the question now, from these results: the answer first, in a few short sentences; only numbers "
    "and names the results contain; say what's missing if something needed isn't there; one next step only if it "
    "follows from the results. Talk like a person, not a report."
)
LAST_WORD = ("That's all the looking up there's time for. Answer the person's question now from the results above, "
             "the answer first; say plainly what you couldn't check.")


def loop_ok(context) -> bool:
    """Only against this computer's Ollama (the phone keeps one round)."""
    from core.llm_manager import OllamaBackend

    llm = getattr(context, "llm", None)
    return isinstance(getattr(llm, "_backend", None), OllamaBackend) and getattr(llm, "home", None) is None


def _lookups_only(context, calls: list[ToolCall]) -> bool:
    from core.assistant_actions import changes_records

    registry = getattr(context, "assistant_actions", None)
    known = getattr(registry, "_actions", {}) if registry is not None else {}
    return bool(calls) and all(c.name in known and not changes_records(c.name) for c in calls)


LOOK_FIRST = ("The person asked about their own records. Don't answer from memory: call the lookup that holds the "
              "answer first.")


def _look_first(context, llm, messages: list[dict], tools: list[dict], prompt: str, reply: ChatReply) -> ChatReply:
    """A question about their records answered without looking anything up
    (2026-10-30, live: "no overdue maintenance" when there was some): one
    more try, told to look first. Kept only if it does look something up."""
    from core.assistant_actions import changes_records, looks_like_question

    lookups = [t for t in tools if not changes_records(t.get("function", {}).get("name", ""))]
    if not lookups or not looks_like_question(prompt):
        return reply
    retry = llm.chat_with_tools(messages + [{"role": "system", "content": LOOK_FIRST}], lookups)
    if retry is not None and _lookups_only(context, retry.tool_calls):
        log.info("Tool loop: answered without looking; looked first on a second try.")
        return retry
    return reply


def _short(text: str) -> str:
    text = str(text or "").strip()
    return text if len(text) <= RESULT_CHARS else text[:RESULT_CHARS].rsplit(" ", 1)[0] + " …(cut short)"


def _plain(results: list[tuple[str, str]]) -> str:
    return " ".join(text for _name, text in results)


def run(context, llm, messages: list[dict], tools: list[dict], prompt: str, named: Optional[str] = None,
        budget: Optional[float] = None) -> Optional[ChatReply]:
    """One turn with the loop: the model's reply when it isn't only
    lookups (unchanged, for the caller's usual path); else one answer
    built from what it looked up."""
    from core.assistant_chat import settle_on_named_tool
    from core.question_plans import invented_numbers

    started = time.monotonic()
    if budget is None:
        config = getattr(context, "config", None)
        budget = float(config.get("assistant.answer_budget_seconds", DEFAULT_BUDGET) if config is not None
                       else DEFAULT_BUDGET)
    reply = llm.chat_with_tools(messages, tools)
    reply = settle_on_named_tool(named, messages, tools, reply, llm.chat_with_tools)
    if reply is not None and not reply.tool_calls and tools and loop_ok(context):
        reply = _look_first(context, llm, messages, tools, prompt, reply)
    if reply is None or not tools or not loop_ok(context) or not _lookups_only(context, reply.tool_calls):
        return reply

    registry = context.assistant_actions
    talk = list(messages)
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    step = 0
    while reply is not None and _lookups_only(context, reply.tool_calls):
        fresh = [c for c in reply.tool_calls if f"{c.name}:{sorted((c.arguments or {}).items())}" not in seen]
        if not fresh or step >= MAX_STEPS or (step and time.monotonic() - started > budget):
            break  # the first round always runs
        talk.append({"role": "assistant", "content": reply.content or "",
                     "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments or {}}} for c in fresh]})
        for call in fresh:
            seen.add(f"{call.name}:{sorted((call.arguments or {}).items())}")
            try:
                text = registry.execute(context, call.name, call.arguments or {})
            except Exception:
                log.exception("Lookup %s failed in the tool loop", call.name)
                text = f"(The {call.name} lookup failed.)"
            results.append((call.name, text))
            talk.append({"role": "tool", "content": _short(text), "tool_name": call.name})
        step += 1
        last = step >= MAX_STEPS or time.monotonic() - started > budget
        reply = llm.chat_with_tools(talk + [{"role": "system", "content": LAST_WORD if last else FOLLOW_UP}],
                                    [] if last else tools)
    log.info("Tool loop: %d round(s), %s, %.1fs", step, ", ".join(n for n, _ in results), time.monotonic() - started)
    if reply is not None and reply.tool_calls and not _lookups_only(context, reply.tool_calls):
        return reply  # it wants a change: the caller's usual path (approval), after looking things up
    if not results:
        return reply
    said = (reply.content if reply is not None else "") or ""
    sources ="\n".join(text for _n, text in results)
    if not said.strip() or invented_numbers(said, sources, prompt):
        if said.strip():
            log.warning("Tool loop answer had numbers the lookups didn't; saying the results instead.")
        return ChatReply(content=_plain(results), tool_calls=[])
    return ChatReply(content=said.strip(), tool_calls=[])
