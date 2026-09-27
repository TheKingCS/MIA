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

**2026-07-14 aesthetic pass part 5** (docs/ROADMAP.md), at the user's
explicit request for a ChatGPT-like, "always growing with the user"
companion rather than a stateless Q&A tool: `build_chat_request()` now
takes a real `core.conversation_manager.Conversation` and sends bounded
history (`trim_history()`) plus a proper system-role message
(`build_system_message()`) instead of a single bare user message —
verified this doesn't need a backend change at all, since
`core.llm_manager.OllamaBackend.chat()` already forwards whatever
`messages` list it's given straight to Ollama's `/api/chat`, which
already understands multi-turn `system`/`user`/`assistant` roles; only
the caller-side assembly needed to change.

The identity/personality text is deliberately short — this project has
hit real, live-model-verified regressions from a *longer* preamble
before (core/device_help_manager.py's own `GROUNDING_INSTRUCTION`
docstring: a longer version made llama3.2:3b MORE likely to falsely
say "I don't know" even on confident matches) — and is only added to
the **information-question** system message, not the action-request
one. Action requests keep the shortest possible system framing
(just the identity line, no warmth/personality elaboration) since
that path's 67-case golden set (`tests/live_model_check.py`) is the
most fragile, most-tested surface in this codebase and personality
fluff sitting next to tool schemas is a real, avoidable regression
risk for zero user-visible benefit — the user never sees this system
message, only the tool's own (separately-worded) confirmation text.
Re-verify against the full golden set after any further wording change
here, not just a subjective read of the prompt.
"""

from __future__ import annotations

import re

from datetime import date
from typing import TYPE_CHECKING, Iterable, Optional

from core.connectivity import connectivity_prompt_block
from core.conversation_modes import (
    AGENCY_LINE,
    COMPANION,
    LISTEN,
    MODE_INSTRUCTIONS,
    PERSONAL_MODES,
    PERSPECTIVE,
    looks_like_direct_command,
)
from core.why_graph import build_why_sheet

# Perspective asked for before the owner has told MIA any reasons:
# say so plainly and invite them, instead of generic motivation.
NO_WHY_YET_INSTRUCTION = (
    "The user asked to be reminded why they're doing what they're doing, but they haven't told you their "
    "reasons yet, so you don't know them. Say so kindly, don't guess or give generic motivation, and invite "
    "them to tell you, for example: 'the reason I'm working this job is so I can pay off my debt, and paying "
    "off debt is so I can control my own time.'"
)
from core.device_help_manager import GROUNDING_INSTRUCTION
from core.llm_manager import ToolCall
from core.user_memory_manager import MEMORY_CATEGORIES

if TYPE_CHECKING:
    from core.conversation_manager import Conversation, ConversationMessage

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


# Short, deliberately — see this module's docstring on why length is a
# real, previously-measured regression risk for llama3.2:3b, and why
# the warmer clauses are only added to the info-question path.
_IDENTITY_LINE = (
    "You are MIA (Multifunctional Intelligent Assistant), the user's personal offline survival companion."
)
_IDENTITY_WARMTH = (
    " You're warm, encouraging, and genuinely curious about the user as a person — like a lifelong friend, "
    "not a cold Q&A tool. Celebrate their wins, comfort them when things are hard, and look for real "
    "opportunities to get to know them better over time. You can speak your replies aloud through "
    "text-to-speech — if asked whether you can talk, speak, or have a voice, say yes."
)
# 2026-07-18, at the user's explicit request ("I want it to be as if
# this program is an extension of the assistant and it should know it
# like the back of its hand"): info-question-only, same regression-
# safety reasoning as _IDENTITY_WARMTH above (the action-request path's
# bare _IDENTITY_LINE stays untouched — it's the fragile, already-tuned
# surface, per this module's own docstring and docs/ROADMAP.md's
# tool-count-interference history). Deliberately worded as confidence
# *conditional on* the grounded material ("when it covers something"),
# not a blanket license to sound sure of everything — GROUNDING_INSTRUCTION
# right after this in build_system_message() is still the harder
# "only use the material below, say you don't know otherwise" rule;
# this just stops correct, grounded answers from reading like a
# stranger's guess.
_IDENTITY_APP_FLUENCY = (
    " This program is your own home, not a separate tool bolted onto you — you know its modules and "
    "features intimately. When the reference material below covers something, answer with the confident, "
    "specific familiarity of someone describing their own house, not a stranger guessing from the outside."
)

# 2026-09-10 "Interactive onboarding + modular tutorial system"
# (docs/VISION.md) — a third conversation path alongside action-request/
# info-question, for when the user explicitly wants a slower, step-by-
# step walkthrough rather than a quick fact. Deliberately narrow/
# explicit trigger phrases (VISION's own example: "Teach me how quests
# work") — NOT a broad reclassification of every "how do I" question,
# which core.device_help_manager's existing grounded-answer path
# already handles well; teaching mode only fires when the user
# unambiguously asks to be taught.
_TEACHING_TRIGGER_PHRASES = (
    "teach me how",
    "teach me about",
    "walk me through",
    "give me a walkthrough",
    "give me a tutorial",
    "show me how to use",
)


def looks_like_teaching_request(prompt: str) -> bool:
    """Pure logic — testable without an LLM (see tests/test_assistant_chat.py)."""
    prompt_lower = prompt.lower()
    return any(phrase in prompt_lower for phrase in _TEACHING_TRIGGER_PHRASES)


# 2026-09-27: "how do I add a bill?" contains the add_bill trigger
# "add a bill", so it used to be routed as a command: tools attached,
# no help-doc grounding, and a real risk of the model adding a bill
# instead of explaining. Questions about *how to use* MIA skip tool
# matching and get the normal grounded answer. Kept to phrasings that
# ask about using the app, not "how much…"/"how far…" data questions,
# which are real tool requests.
_HOW_TO_PREFIXES = (
    "how do i", "how do you", "how can i", "how would i", "how should i",
    "where do i", "where can i", "is there a way to", "can you explain how",
)
# "how does my budget look" / "what does the mower need" are data
# questions, so these two shapes only count when they're about how
# something works or what a part of the app does.
_HOW_TO_PATTERNS = (
    re.compile(r"^how does .+ work"),
    re.compile(r"^what does (the |my )?[\w' ]+ (module|tab|screen|page|button|feature|app) do"),
)


def looks_like_how_to_question(prompt: str) -> bool:
    """Pure logic. True for questions about how to use MIA itself."""
    lowered = prompt.lower().strip()
    return lowered.startswith(_HOW_TO_PREFIXES) or any(p.search(lowered) for p in _HOW_TO_PATTERNS)


# Swapped in for GROUNDING_INSTRUCTION (never both at once — one
# system message, one job) when looks_like_teaching_request() fires.
# Same "keep it short, don't over-qualify" discipline GROUNDING_
# INSTRUCTION's own comment already established for this exact model
# (a longer, more-qualifying preamble measurably made llama3.2:3b MORE
# likely to falsely say "I don't know") — any future wording edit here
# should be re-verified against the live model the same way, not
# assumed safe.
_TEACHING_INSTRUCTION = (
    "The user explicitly asked to be taught how something in MIA works, step by step — not just a quick "
    "fact. Using ONLY the reference material below, walk them through it like a patient guide: a short "
    "intro, concrete steps in order, then one real thing they could try right now. If the material doesn't "
    "actually cover this, say so honestly rather than inventing steps — do not use outside knowledge."
)

_MAX_HISTORY_MESSAGES = 12  # 6 exchanges — bounds prompt growth/latency on CPU-only Pi-class hardware

_MAX_INJECTED_MEMORIES = 20  # most recent — bounds prompt growth as the memory store grows over months of use

# Deliberately built from ONLY the user's own message, not the
# assistant's reply too — measured directly against the live model
# (docs/ROADMAP.md) that including the assistant's turn made this
# consistently WORSE, not better: a 100%-reproducible failure (not
# sampling noise — see core/device_help_manager.py's own docstring on
# telling those apart) where the model concluded "no new facts" even
# when the user's message plainly stated a name and a hobby in the same
# breath. Also required an explicit anti-hallucination + anti-pronoun-
# guessing instruction after live testing surfaced the small model
# inventing biographical details (a birth date, a relationship status,
# a "daily routine") that were never actually said, and guessing the
# user's gender inconsistently across otherwise-identical prompts.
# Biased deliberately toward missing a real fact (a false negative)
# over fabricating one (a false positive) — for a feature whose whole
# point is trustworthy long-term memory, a wrong invented "fact" is far
# worse than an occasional missed one.
# 2026-09-10 "Memory Palace": each fact now also gets a category, in
# the same message, rather than a second LLM call — a category is a
# simple classification of text the model already has to read anyway,
# not a separate reasoning task, so this doesn't add real fragility on
# top of the existing NONE-detection risk documented above.
# parse_extracted_memories() is still forgiving of a malformed/missing
# category (falls back to "Other" and keeps the whole line as the
# fact) — never lets a formatting slip cost a real fact.
_MEMORY_CATEGORY_LIST = ", ".join(c for c in MEMORY_CATEGORIES if c != "Other")
_MEMORY_EXTRACTION_PROMPT_TEMPLATE = (
    "The user just sent this message to their personal assistant:\n\n"
    "\"{user_message}\"\n\n"
    "List every fact it EXPLICITLY states about the user themselves (name, birthday, a relationship, a "
    "stated preference, a stated ongoing interest/hobby, something they value, a goal and why they want it, "
    "something they keep struggling with, or something they accomplished). One fact per line, in the exact form "
    "\"Category: Fact\", using the words \"the user\" instead of he/she/his/her, e.g. "
    "\"Pets: The user has a dog named Rex.\" Category must be exactly one of: "
    f"{_MEMORY_CATEGORY_LIST}, Other — pick Other if nothing else fits. Never add "
    "a detail that wasn't actually said, and never guess at anything (gender, age, routine, schedule) "
    "that wasn't stated. If it's a question, a one-time request/command, or states no personal fact, "
    "reply with exactly: NONE"
)

_TITLE_GENERATION_PROMPT_TEMPLATE = (
    "Write a short title (3-6 words, no punctuation, no quotes) summarizing what this conversation is "
    "about so far, based on this first exchange.\n\n"
    "User: {user_message}\n"
    "You: {assistant_message}"
)


def trim_history(messages: list["ConversationMessage"], max_messages: int = _MAX_HISTORY_MESSAGES) -> list["ConversationMessage"]:
    """Pure logic — testable without Qt or a real Conversation. Keeps the most recent `max_messages`."""
    if max_messages <= 0:
        return []
    return messages[-max_messages:]


def build_user_context_block(context) -> str:
    """
    Pure-ish (touches `context.profiles`/`context.user_memories`, no
    LLM call) — assembles "what MIA knows about this user so far"
    from the active Profile's structured fields (name, birthday) plus
    free-text UserMemory entries, for injection into the info-question
    system message. Returns an empty-knowledge line rather than an
    empty string when nothing is known yet, framed as an invitation to
    learn more — matches this pass's "researcher" framing rather than
    just silently omitting the section.
    """
    facts: list[str] = []

    active_profile = context.profiles.get_active_profile() if context.profiles is not None else None
    if active_profile is not None:
        facts.append(f"Name: {active_profile.name}")
        birthday = getattr(active_profile, "birthday", None)
        if birthday:
            facts.append(f"Birthday: {format_birthday(birthday)}")

    if context.user_memories is not None:
        for memory in context.user_memories.all_memories()[:_MAX_INJECTED_MEMORIES]:
            facts.append(memory.text)

    if not facts:
        return "You don't know much about this user yet — a great opportunity to ask and learn."
    bullet_list = "\n".join(f"- {fact}" for fact in facts)
    return f"What you know about this user so far:\n{bullet_list}"


def format_birthday(iso_date: str) -> str:
    """Pure formatting logic — "March 3" (no year, this is a casual reference, not a form field)."""
    try:
        parsed = date.fromisoformat(iso_date)
    except ValueError:
        return iso_date
    return f"{parsed.strftime('%B')} {parsed.day}"


def build_system_message(context, is_action_request: bool, is_teaching_request: bool = False) -> str:
    """
    The system-role message for one chat turn — pulled out as its own
    function so `build_chat_request()` stays readable and this is
    independently testable. Action requests get the bare identity line
    only; information questions additionally get the warmth framing,
    the user-context block, and a closing instruction — see this
    module's docstring for why the split. That closing instruction is
    `_TEACHING_INSTRUCTION` when `is_teaching_request` (2026-09-10,
    "teach me how X works"), otherwise
    `core.device_help_manager.GROUNDING_INSTRUCTION` — never both;
    `is_action_request` always wins over `is_teaching_request` if
    somehow both were true (callers shouldn't produce that combination
    — see `build_chat_request()`, which checks teaching status first
    and skips action-matching entirely when it fires).
    """
    if is_action_request:
        return _IDENTITY_LINE

    closing_instruction = _TEACHING_INSTRUCTION if is_teaching_request else GROUNDING_INSTRUCTION
    parts = [_IDENTITY_LINE + _IDENTITY_WARMTH + _IDENTITY_APP_FLUENCY, build_user_context_block(context)]
    # 2026-09-27: online/offline awareness. Info questions only — every
    # Assistant action runs offline, so the action path stays lean.
    connectivity = getattr(context, "connectivity", None)
    if connectivity is not None:
        block = connectivity_prompt_block(connectivity.status)
        if block:
            parts.append(block)
    parts.append(closing_instruction)
    return "\n\n".join(parts)


def build_chat_request(context, conversation: "Conversation", prompt: str) -> tuple[list[dict], list[dict]]:
    """
    Decides whether `prompt` looks like an action request and builds
    the (messages, tools) pair a caller hands to `core.chat_worker.ChatWorker`
    — pulled out as its own function (touches only `context`, no Qt) so
    `tests/live_model_check.py` (the golden-set live-model regression
    script, milestone 5.11) exercises this exact decision logic
    against the real Ollama server, not a hand-copied reimplementation
    that could quietly drift from what production actually does.

    `conversation` supplies the bounded history sent alongside `prompt`
    (2026-07-14 aesthetic pass part 5) — pass a conversation with no
    prior messages (a fresh one) for a "no history yet" first turn, same
    as before this pass. `messages` still ends with the current turn's
    `prompt` (raw for an action request, grounded-with-reference-material
    for an information question) as the final user message — history
    entries are the plain, human-readable text as actually
    displayed/stored, never a past turn's grounded/augmented version, so
    old retrieval material doesn't pile up turn after turn.

    `looks_like_teaching_request()` (2026-09-10) is checked BEFORE
    action-matching and, if it fires, action-matching is skipped
    entirely — an explicit "teach me how to add a mission" must never
    be treated as a literal request to execute `add_mission`. Teaching
    requests still get grounded material from `context.device_help`
    (reusing self-knowledge's existing retrieval), just with
    `_TEACHING_INSTRUCTION` framing instead of `GROUNDING_INSTRUCTION`,
    and — like any other info question — never get tools attached.
    """
    mode = getattr(conversation, "mode", COMPANION) if conversation is not None else COMPANION
    if mode in PERSONAL_MODES or getattr(conversation, "journal", False):
        return _build_personal_request(context, conversation, prompt, mode)

    is_teaching_request = looks_like_teaching_request(prompt)
    matched_actions = (
        context.assistant_actions.matching_actions(prompt, context)
        if context.assistant_actions is not None and not is_teaching_request and not looks_like_how_to_question(prompt)
        else []
    )
    is_action_request = bool(matched_actions)

    llm_prompt = prompt
    if not is_action_request and context.device_help is not None:
        llm_prompt = context.device_help.build_grounded_prompt(prompt)

    history = trim_history(conversation.messages) if conversation is not None else []
    messages = [{"role": "system", "content": build_system_message(context, is_action_request, is_teaching_request)}]
    messages.extend({"role": m.role, "content": m.content} for m in history)
    messages.append({"role": "user", "content": llm_prompt})

    tools = []
    if is_action_request and context.assistant_actions is not None:
        # Domain-scoped, not the full registry — see
        # core/assistant_actions.py's docstring on why (tool-count
        # scaling has caused real live-model-only interference bugs;
        # matching_actions() attaches only the small always-on set plus
        # whichever domain(s) this prompt's own triggers matched).
        tools = context.assistant_actions.to_ollama_tools(matched_actions)

    return messages, tools


def build_personal_system_message(context, mode: str) -> str:
    """The personal path's system message (Cognitive Extension slice A):
    who MIA is, the human-agency line, what she knows about the user,
    recent private-journal sessions when unlocked, and the one tone line
    for the current mode. No help-doc grounding: "only answer from the
    reference material" is the wrong instruction for someone venting."""
    from core.talk_it_out import journal_context_block  # local: talk_it_out imports this module

    parts = [_IDENTITY_LINE + _IDENTITY_WARMTH + " " + AGENCY_LINE, build_user_context_block(context)]
    journal_block = journal_context_block(context)
    if journal_block:
        parts.append(journal_block)
    if mode == PERSPECTIVE:
        # Slice B: the facts come from code (core/why_graph.py); the model only phrases them.
        sheet = build_why_sheet(context)
        if sheet.is_empty:
            parts.append(NO_WHY_YET_INSTRUCTION + " Answer in plain conversational text.")
            return "\n\n".join(parts)
        parts.append("The user's reasons and the facts behind them:\n" + sheet.to_text())
    instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS[LISTEN])
    parts.append(instruction + " Answer in plain conversational text.")
    return "\n\n".join(parts)


def _build_personal_request(context, conversation, prompt: str, mode: str) -> tuple[list[dict], list[dict]]:
    """A personal-mode turn (listen / direct / momentum / plan, or any
    journaling). Tools only for a message that starts like a command
    ("add milk to the list" still works mid-journal); a vent that
    mentions the truck must not become a maintenance log."""
    matched_actions = []
    if context.assistant_actions is not None and looks_like_direct_command(prompt):
        matched_actions = context.assistant_actions.matching_actions(prompt, context)

    history = trim_history(conversation.messages) if conversation is not None else []
    if matched_actions:
        system = _IDENTITY_LINE
    else:
        system = build_personal_system_message(context, mode if mode in PERSONAL_MODES else LISTEN)
    messages = [{"role": "system", "content": system}]
    messages.extend({"role": m.role, "content": m.content} for m in history)
    messages.append({"role": "user", "content": prompt})
    tools = context.assistant_actions.to_ollama_tools(matched_actions) if matched_actions else []
    return messages, tools


def build_memory_extraction_prompt(user_message: str) -> str:
    """Pure logic — testable without Qt or a real LLM (see tests/test_assistant_chat.py)."""
    return _MEMORY_EXTRACTION_PROMPT_TEMPLATE.format(user_message=user_message)


# Live-model testing found the small model doesn't reliably reply with
# the literal word "NONE" as instructed — it sometimes paraphrases the
# same "nothing to extract" conclusion in a full sentence instead (e.g.
# "There is no new information provided about the user."). Rejecting
# only an exact "NONE" match would let that paraphrase through and get
# stored as if it were a real memory (this happened in testing). This
# is a belt-and-suspenders safety net on top of the prompt's own
# instruction, not a replacement for it — same "don't trust the model
# to follow instructions perfectly" caution as
# core/llm_manager.py's `_looks_like_malformed_tool_call()`.
_NO_FACT_HEDGE_PHRASES = (
    "no new", "nothing new", "no information", "not stated", "not explicitly",
    "does not state", "doesn't state", "no fact", "not mentioned", "is mentioned",
)


def _split_category_and_fact(line: str) -> tuple[str, str]:
    """Pure logic. "Category: Fact" -> (category, fact) once the text
    before the first colon exactly matches a real category
    (case-insensitive, normalized to the real casing); anything else
    -> ("Other", line) with the WHOLE original line preserved as the
    fact — a formatting slip must never cost a real fact, same
    belt-and-suspenders caution as the NONE/hedge detection below."""
    if ":" in line:
        prefix, rest = line.split(":", 1)
        prefix = prefix.strip()
        for category in MEMORY_CATEGORIES:
            if prefix.lower() == category.lower() and rest.strip():
                return category, rest.strip()
    return "Other", line


def parse_extracted_memories(raw_text: Optional[str]) -> list[tuple[str, str]]:
    """
    Pure parsing logic — one (category, fact) pair per non-empty line,
    stripping common bullet/numbering prefixes, dropping a bare "NONE"
    (case-insensitive) line and any line that reads as a hedge/
    explanation rather than a stated fact (see `_NO_FACT_HEDGE_PHRASES`).
    See `_split_category_and_fact()` for how the "Category: Fact" line
    shape is parsed (and how a malformed one degrades safely). Returns
    [] for None/empty input rather than raising, since the LLM backend
    being unreachable is an expected, non-fatal case for a background
    enhancement like this — memory extraction failing should never
    disrupt the actual chat reply already shown to the user.
    """
    if not raw_text:
        return []
    facts = []
    for line in raw_text.splitlines():
        line = line.strip().lstrip("-*•").strip()
        # Strip a leading "1. "/"2) " numbering prefix, if present.
        for index, char in enumerate(line):
            if char.isdigit():
                continue
            if char in ".)" and index > 0:
                line = line[index + 1:].strip()
            break
        if not line or line.strip(".").upper() == "NONE":
            continue
        lowered = line.lower()
        if any(phrase in lowered for phrase in _NO_FACT_HEDGE_PHRASES):
            continue
        facts.append(_split_category_and_fact(line))
    return facts


def build_title_generation_prompt(user_message: str, assistant_message: str) -> str:
    """Pure logic — testable without Qt or a real LLM (see tests/test_assistant_chat.py)."""
    return _TITLE_GENERATION_PROMPT_TEMPLATE.format(user_message=user_message, assistant_message=assistant_message)


_MAX_TITLE_LENGTH = 60


def clean_generated_title(raw_title: Optional[str]) -> Optional[str]:
    """
    Pure cleanup logic — strips surrounding quotes/whitespace and caps
    length (a small model occasionally ignores the "3-6 words"
    instruction and free-associates a whole sentence). Returns None
    (not the default title, not an empty string) for blank/missing
    input, so callers can tell "nothing usable came back" apart from
    "the model deliberately produced a short-but-valid title" without
    re-checking against `core.conversation_manager.DEFAULT_TITLE`
    themselves.
    """
    if not raw_title:
        return None
    cleaned = raw_title.strip().strip("\"'“”").strip()
    if not cleaned:
        return None
    if len(cleaned) > _MAX_TITLE_LENGTH:
        cleaned = cleaned[:_MAX_TITLE_LENGTH].rsplit(" ", 1)[0].rstrip(",.;:")
    return cleaned or None
