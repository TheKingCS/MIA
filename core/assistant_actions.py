"""
core.assistant_actions
=========================

The Assistant's tool-use/action-execution registry — docs/ROADMAP.md
milestone 5.5. Lets the LLM actually DO things in MIA (open a
module, add an alarm, a note, an inventory item), not just answer
questions, via Ollama's structured tool-calling API
(core/llm_manager.py's `chat_with_tools()`).

This is a **different** capability from the Self-Modification / Dev
Mode staged plan in docs/ROADMAP.md, which is specifically about the
assistant editing MIA's own source code and is gated behind a
cautious multi-stage rollout (read & explain -> propose-not-apply ->
sandboxed testing -> scoped autonomy). Actions registered here are
just normal, everyday app operations any user could already do by
hand through the UI — there is no file-write/code-execution capability
anywhere in this module.

Same pluggable-registry shape as core/calculator_engine.py: register()
here, core/application.py wires the built-in actions in
(`_register_assistant_actions()`, mirroring `_register_calculators()`),
so this file doesn't need to know about ModuleManager or any specific
manager directly.

A handler receives the AppContext and the LLM's parsed arguments dict,
and returns a short human-readable confirmation string. There is
deliberately no second LLM round-trip to phrase that confirmation —
keeps this fast, fully deterministic, and unit-testable without a real
model. A handler that needs to touch the GUI (e.g. `open_module`) must
publish an event rather than reach into Qt directly, since handlers
can be invoked from contexts where that matters — see
modules/assistant/module.py's docstring for the threading reasoning.

**Domain-scoped tool attachment (added once the registry crossed 47
tools):** every prior round of tool-count growth in this project found
a real live-model-only bug (5.7-5.9's gating gaps, milestone 5.15's
`calculate_subnet` cross-schema interference — see docs/ROADMAP.md).
5.15's bug in particular was specifically about *unrelated* tool
schemas polluting the model's context on a totally unrelated prompt
(a security tool's presence broke an inventory question). Attaching
every registered tool to every action-request message, unconditionally,
doesn't just cost tokens — it's a structural interference risk that
gets worse every time the registry grows, with no ceiling. `domain`
groups related actions (e.g. "inventory", "security", "expeditions");
`AssistantActionRegistry.matching_actions()` attaches only the small
always-on `_ALWAYS_ON_DOMAIN` set (generic, cross-cutting actions like
`open_module`/`get_system_health` that existing collision-resolution
cases depend on being visible alongside whichever domain(s) actually
matched — see `_DOMAIN_ALWAYS_ON` below) plus whichever domain(s) the
prompt's own trigger phrases actually matched — typically ~10-13 tools
per request instead of the full registry, without discarding any
previously-solved collision case (each of those pairs — `open_module`/
`set_theme`, `list_profiles`/`get_device_profile` — lives in the same
domain specifically so they still get attached together, same as
before this change). Verified against the live model in
tests/live_model_check.py before/after — see docs/ROADMAP.md for the
verification writeup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable, Optional

from core.logger import get_logger
from core.main_thread import records_changed

if TYPE_CHECKING:
    from core.app_context import AppContext

log = get_logger(__name__)

# Always attached alongside whichever domain(s) a prompt's own trigger
# phrases matched — small and generic/cross-cutting enough that this
# doesn't reintroduce the interference risk this whole scheme exists to
# avoid, while keeping every collision-resolution case that predates
# this change working exactly as before (both members of each known
# collision pair — open_module/set_theme, list_profiles/
# get_device_profile — live in this one domain).
_ALWAYS_ON_DOMAIN = "system"


@dataclass
class AssistantAction:
    name: str
    description: str
    parameters: dict  # JSON schema "parameters" object (Ollama/OpenAI tool-call format)
    handler: Callable[[AppContext, dict], str]
    # Keyword phrases that make modules.assistant.module.looks_like_action_request()
    # offer this action's tool at all (see that function's docstring for
    # why tools aren't attached to every message unconditionally).
    # Co-located with the action's own definition rather than a separate
    # hand-maintained list elsewhere, so a new action's gating phrases
    # can't silently drift out of sync as the registry grows past a
    # handful of actions — milestone 5.9's fix for exactly that risk.
    trigger_phrases: tuple[str, ...] = ()
    # Groups related actions for scoped tool attachment — see this
    # module's docstring on domain-scoped attachment. Defaults to the
    # always-on domain so a new action registered without picking one
    # explicitly fails safe (visible everywhere) rather than silently
    # invisible everywhere.
    domain: str = _ALWAYS_ON_DOMAIN
    # Marks a mutating/deleting action — used by
    # modules/assistant/module.py's _on_reply() to refuse executing a
    # destructive call when it's bundled alongside other tool calls in
    # the same reply (see that module's docstring on why: the
    # 2026-07-14 qwen2.5:7b model-comparison experiment found a
    # stronger model can emit a spurious destructive call alongside a
    # correct read call for the same ordinary question — llama3.2 never
    # did this in this project's history, but nothing about this app's
    # design prevents a future/different model from doing it again).
    # Previously tracked only informally, by hand, in
    # tests/live_model_check.py's _DESTRUCTIVE_TOOLS — formalized here
    # so both that test script and production code share one source of
    # truth instead of two lists that can drift, same lesson as
    # trigger_phrases/gating_keywords in milestone 5.9.
    destructive: bool = False

    def to_ollama_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class AssistantActionRegistry:
    def __init__(self) -> None:
        # 2026-09-27 conversational audit: exact trigger phrases alone
        # missed how people actually talk ("I just put 120 hours on the
        # mower", "I watered the tomatoes"). Two more ways a domain
        # gets attached: its everyday vocabulary (whole words), and the
        # names of the user's own records in it (mention "the mower"
        # and Maintenance's tools come along).
        self._domain_keywords: dict[str, tuple[str, ...]] = {}
        self._entity_providers: dict[str, Callable[["AppContext"], Iterable[str]]] = {}
        self._entity_match_all: set[str] = set()
        self._actions: dict[str, AssistantAction] = {}

    def register(self, action: AssistantAction) -> None:
        self._actions[action.name] = action
        log.info("Registered assistant action: %s", action.name)

    def is_destructive(self, name: str) -> bool:
        """False for an unknown name — nothing to protect against executing something that doesn't exist."""
        action = self._actions.get(name)
        return action.destructive if action is not None else False

    def destructive_action_names(self) -> set[str]:
        return {action.name for action in self._actions.values() if action.destructive}

    def to_ollama_tools(self, actions: Optional[list[AssistantAction]] = None) -> list[dict]:
        """
        `actions` defaults to the full registry (used by nothing in
        production anymore, kept only so this method stays usable
        standalone/in tests without also calling matching_actions()
        first) — modules/assistant/module.py's build_chat_request()
        always passes matching_actions()'s result, per this module's
        domain-scoped-attachment docstring.
        """
        source = actions if actions is not None else list(self._actions.values())
        return [action.to_ollama_tool() for action in source]

    def gating_keywords(self) -> list[str]:
        """All registered actions' trigger_phrases, flattened — see AssistantAction.trigger_phrases."""
        keywords: list[str] = []
        for action in self._actions.values():
            keywords.extend(action.trigger_phrases)
        return keywords

    def register_domain_keywords(self, domain: str, keywords: Iterable[str]) -> None:
        """Whole-word vocabulary that attaches `domain` (e.g. "debt", "plywood")."""
        existing = self._domain_keywords.get(domain, ())
        self._domain_keywords[domain] = existing + tuple(k.lower() for k in keywords)

    def register_entity_names(
        self, domain: str, provider: Callable[["AppContext"], Iterable[str]], match_all_words: bool = False,
    ) -> None:
        """`provider(context)` returns the names of the user's records in
        `domain`; mentioning one of them attaches the domain. By default
        any significant word of a name counts ("the truck" -> "Pickup
        Truck"); `match_all_words` requires every one of them, for
        domains whose names share words with others ("Truck Loan" must
        not fire on "the truck")."""
        self._entity_providers[domain] = provider
        if match_all_words:
            self._entity_match_all.add(domain)

    def _keyword_domains(self, lowered: str) -> set[str]:
        return {
            domain for domain, keywords in self._domain_keywords.items()
            if any(re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", lowered) for k in keywords)
        }

    def _entity_domains(self, prompt: str, context: Optional["AppContext"]) -> set[str]:
        if context is None or not self._entity_providers:
            return set()
        from core.assistant_lookup import head_word, name_tokens

        prompt_tokens = name_tokens(prompt)
        lowered = prompt.lower()
        domains = set()
        for domain, provider in self._entity_providers.items():
            try:
                names = list(provider(context))
            except Exception:
                log.exception("Entity-name provider for domain '%s' failed", domain)
                continue
            for name in names:
                name_l = str(name).strip().lower()
                if not name_l:
                    continue
                if domain in self._entity_match_all:
                    significant = {t for t in name_tokens(name_l) if len(t) >= 4}
                    hit = bool(significant) and significant <= prompt_tokens
                else:
                    head = head_word(name_l)
                    hit = bool(head) and head in prompt_tokens
                if name_l in lowered or hit:
                    domains.add(domain)
                    break
        return domains

    def matching_actions(self, prompt: str, context: Optional["AppContext"] = None) -> list[AssistantAction]:
        """
        Actions to actually attach as tools for this specific prompt —
        see this module's docstring on domain-scoped attachment. Empty
        if no action's own trigger phrase matches (mirrors
        modules.assistant.module.looks_like_action_request()'s
        matching rule exactly, so "is this an action request at all"
        stays identical to before this change — only *which* tools get
        attached narrows, never *whether* any do).
        """
        lowered = f" {prompt.lower().strip()} "
        matched_domains: set[str] = set()
        for action in self._actions.values():
            if any(phrase in lowered for phrase in action.trigger_phrases):
                matched_domains.add(action.domain)
        matched_domains |= self._keyword_domains(lowered)
        matched_domains |= self._entity_domains(prompt, context)

        if not matched_domains:
            return []

        matched_domains.add(_ALWAYS_ON_DOMAIN)
        return [action for action in self._actions.values() if action.domain in matched_domains]

    def execute(self, context: AppContext, name: str, arguments: dict) -> str:
        """
        Run the named action's handler, or a clear message if the name
        is unknown or the handler raises — a malformed/hallucinated
        tool call from the LLM must never crash the app.
        """
        action = self._actions.get(name)
        if action is None:
            log.warning("Assistant tried to call unknown action '%s'", name)
            return f"(I tried to do something I don't know how to do: '{name}'.)"
        try:
            result = action.handler(context, arguments)
        except Exception:
            log.exception("Assistant action '%s' failed", name)
            return f"(Sorry, '{name}' didn't work.)"
        # Open screens re-read their data (core/main_thread.py), also when
        # the change came from the phone, on the server's thread.
        records_changed(context, name)
        return result
