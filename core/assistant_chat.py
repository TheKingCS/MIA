"""
core.assistant_chat
======================

The pure, non-Qt logic for one Assistant chat turn — moved here from
`modules/assistant/module.py` (2026-07-14 aesthetic pass part 4,
docs/ROADMAP.md) once the sidebar chat in `gui/character_panel.py`
needed the exact same request-building and tool-call-safety logic as
the full-screen Assistant module. `gui/` may import `core/` directly
but must never import `modules/` (CLAUDE.md's one-directional
layering), so anything both surfaces need had to live here, not in
`modules/assistant/module.py` — these functions already touched only
`context`/plain data, never Qt, so the move is a pure relocation, not a
rewrite.
"""

from __future__ import annotations

from typing import Iterable, Optional

from core.llm_manager import ToolCall

# Curated example prompts per AssistantAction domain (core/assistant_actions.py's
# own `domain` field) — shown as clickable suggestions in
# gui/character_panel.py's sidebar chat, added 2026-07-14 aesthetic pass
# part 4 at the user's request ("the assistant should recommend
# questions that it has a good ability to help with"). Deliberately a
# small, curated, hand-written dict (same shape as this file's sibling
# MODULE_REACTIONS in gui/character_panel.py) rather than generated from
# each action's own `trigger_phrases` — trigger phrases are gating
# fragments tuned for substring matching ("battery level", "distance
# to"), not always a complete, natural-reading question a user would
# want to see written out as a suggestion chip.
DOMAIN_EXAMPLE_PROMPTS: dict[str, list[str]] = {
    "system": ["What's my system health?", "What have I been doing recently?"],
    "alarms": ["Set an alarm called Wake Up for 6:30", "List my alarms"],
    "notes": ["Add a note that says buy more filters", "List my notes"],
    "inventory": ["Add to inventory: 10 M3 bolts", "How many M3 bolts do I have?"],
    "waypoints": ["Add a waypoint called Trailhead", "What's the distance from Home to Trailhead?"],
    "expeditions": ["Start an expedition called Weekend Trip", "List my trips"],
    "calendar": ["Add a calendar event called Vet Appointment", "What's on my calendar?"],
    "power": ["What's my battery level?"],
    "components": ["List my components", "Add a component to my workshop inventory"],
    "field_kit": ["What devices are connected?", "List my scripts"],
    "security": ["Check the strength of this password", "Calculate this subnet: 192.168.1.0/24"],
    "projects": ["Start a project called Garage Rewire", "List my tasks"],
    "missions": ["What's my current mission?", "Log progress on my mission"],
}

# A mix of prompts shown on screens with no specific domain to suggest
# from (Home, Apps, or any module not in MODULE_ID_TO_DOMAINS below) —
# deliberately spans several different domains rather than repeating
# one, so it doubles as a quick "here's the range of things I can do"
# sampler.
_GENERIC_EXAMPLE_PROMPTS = [
    "What can you help me with?",
    "What's my battery level?",
    "What's my current mission?",
    "Add a waypoint",
]

# module_id -> the AssistantAction domain(s) most relevant to that
# screen — a list, not a single domain, since some modules (Toolbox
# especially) house several distinct domains as separate tabs. Any
# module_id not listed here falls back to _GENERIC_EXAMPLE_PROMPTS.
MODULE_ID_TO_DOMAINS: dict[str, list[str]] = {
    "missions": ["missions"],
    "expeditions": ["expeditions"],
    "navigation": ["waypoints"],
    "notes": ["notes"],
    "toolbox": ["alarms", "calendar", "inventory", "projects"],
    "workshop": ["components"],
    "field_kit": ["field_kit", "security"],
    "power": ["power"],
    "settings": ["system"],
    "diagnostics": ["system"],
}

_SUGGESTED_PROMPT_LIMIT = 4


def suggested_prompts_for_module(module_id: Optional[str]) -> list[str]:
    """
    Pure lookup logic — testable without Qt (see tests/test_assistant_chat.py).
    `module_id` is None for the Home screen. Pulls one prompt per
    matched domain first (for variety across domains) before filling
    any remaining slots with a second prompt from the same domains, so
    a single wordy domain can't crowd out the others.
    """
    domains = MODULE_ID_TO_DOMAINS.get(module_id or "", [])
    if not domains:
        return list(_GENERIC_EXAMPLE_PROMPTS[:_SUGGESTED_PROMPT_LIMIT])

    prompts: list[str] = []
    for round_index in range(2):
        for domain in domains:
            candidates = DOMAIN_EXAMPLE_PROMPTS.get(domain, [])
            if round_index < len(candidates):
                prompts.append(candidates[round_index])
            if len(prompts) >= _SUGGESTED_PROMPT_LIMIT:
                return prompts
    return prompts

# Fallback keyword phrases, used only when looks_like_action_request()
# is called without an explicit `keywords` argument (e.g. exercising
# the pure classifier directly in tests). Production code
# (modules/assistant/module.py's _on_send(), gui/character_panel.py's
# sidebar chat) instead passes `AppContext.assistant_actions.gating_keywords()`
# — the live union of every registered action's own `trigger_phrases`
# (core/assistant_actions.py), not this static list. Milestone 5.9
# moved gating phrases onto each action's own registration for exactly
# this reason: a hand-maintained central tuple like this one silently
# drifts out of sync once the registry grows past a handful of
# actions — this fallback exists purely so the classifier stays
# testable in isolation, not as the real source of truth.
_ACTION_REQUEST_KEYWORDS = (
    "open ", "launch ", "go to ", "switch to ", "take me to ",
    "set an alarm", "set a timer", "add an alarm", "remind me", "wake me up",
    "add a note", "take a note", "make a note", "write down", "jot down",
    "add to inventory", "add an inventory item", "inventory item",
    "recent activity", "activity log", "what have i done", "what have i been doing", "what did i do",
)


def format_chat_line(speaker: str, text: str) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_assistant_chat.py)."""
    return f"{speaker}: {text}"


def split_safe_tool_calls(tool_calls: list[ToolCall], assistant_actions) -> tuple[list[ToolCall], list[ToolCall]]:
    """
    Returns (calls_to_execute, calls_skipped). Pure logic (no Qt) —
    testable directly, see tests/test_assistant_chat.py.

    A single tool call executes regardless of whether it's destructive
    — that's the normal, already-extensively-tested case (every
    delete_*/adjust_* golden-set case is exactly one call). Only when
    the model returns **more than one** tool call in the same reply are
    destructive ones skipped rather than executed.

    Why: found via the 2026-07-14 qwen2.5:7b model-comparison
    experiment (docs/ROADMAP.md) — asked "How many M3 bolts do I have?"
    (a pure read question), qwen2.5:7b returned BOTH `list_inventory`
    AND a spurious `adjust_inventory_quantity` call in the same reply.
    llama3.2 never did this across this project's entire history of
    live-model verification, but nothing about this app's design
    prevents a future/different model from doing it again, and this
    app was never designed or tested for genuine multi-intent-per-
    message use (every registered action assumes one atomic operation
    per user turn). Bundling a destructive call alongside anything else
    is treated as a sign of model confusion, not a feature request —
    fail closed on the destructive part, same conservative bias as
    every delete/adjust handler's own exact-match-or-refuse design.
    """
    if len(tool_calls) <= 1:
        return list(tool_calls), []
    kept = [tc for tc in tool_calls if not assistant_actions.is_destructive(tc.name)]
    skipped = [tc for tc in tool_calls if assistant_actions.is_destructive(tc.name)]
    return kept, skipped


def looks_like_action_request(text: str, keywords: Iterable[str] = _ACTION_REQUEST_KEYWORDS) -> bool:
    """
    Drives both halves of the grounding/tool-calling split — see
    modules/assistant/module.py's docstring for the two real-usage
    regressions (hallucinated `open_module` call on an info question;
    grounding noise blocking a real `add_alarm` call) this classifier
    fixes. Pure keyword matching, same simplicity level as
    core/device_help_manager.py's retrieval scoring. `keywords` defaults
    to this module's own fallback list only for standalone testing —
    see `_ACTION_REQUEST_KEYWORDS`'s docstring for why production code
    always passes the registry's live keyword set instead.
    """
    lowered = f" {text.lower().strip()} "
    return any(keyword in lowered for keyword in keywords)


def build_chat_request(context, prompt: str) -> tuple[list[dict], list[dict]]:
    """
    Decides whether `prompt` looks like an action request and builds
    the (messages, tools) pair a caller hands to `core.chat_worker.ChatWorker`
    — pulled out as its own function (touches only `context`, no Qt) so
    `tests/live_model_check.py` (the golden-set live-model regression
    script, milestone 5.11) exercises this exact decision logic
    against the real Ollama server, not a hand-copied reimplementation
    that could quietly drift from what production actually does.
    """
    matched_actions = (
        context.assistant_actions.matching_actions(prompt)
        if context.assistant_actions is not None
        else []
    )
    is_action_request = bool(matched_actions)

    llm_prompt = prompt
    if not is_action_request and context.device_help is not None:
        llm_prompt = context.device_help.build_grounded_prompt(prompt)

    messages = [{"role": "user", "content": llm_prompt}]
    tools = []
    if is_action_request and context.assistant_actions is not None:
        # Domain-scoped, not the full registry — see
        # core/assistant_actions.py's docstring on why (tool-count
        # scaling has caused real live-model-only interference bugs;
        # matching_actions() attaches only the small always-on set plus
        # whichever domain(s) this prompt's own triggers matched).
        tools = context.assistant_actions.to_ollama_tools(matched_actions)

    return messages, tools
