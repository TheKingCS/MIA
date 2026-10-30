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
from core.main_thread import changes_records, records_changed

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
    # Words that say what the action is about, beyond its own name ("chore"
    # for list_household_routines): see _names_its_subject().
    subjects: tuple[str, ...] = ()
    # 2026-10-21 (DEC-0041): a lookup whose one detail is the question
    # itself ("can you track my chickens?", "what did we decide about
    # eggs?") can still be answered in code: direct_lookup() passes the
    # person's words as this parameter.
    prompt_arg: str = ""

    def direct_arguments(self, prompt: str) -> dict:
        """The arguments a direct lookup runs with: none, or the person's words."""
        return {self.prompt_arg: prompt} if self.prompt_arg else {}

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

    def named_things(self, text: str, context: Optional["AppContext"]) -> list[str]:
        """The person's own records `text` names, by their full names
        ("the truck" -> "Pickup Truck"), with the same matching as
        _entity_domains. For what "it" means in a conversation
        (core/conversation_state.py)."""
        if context is None or not self._entity_providers or not text:
            return []
        from core.assistant_lookup import head_word, name_tokens

        tokens, lowered, found = name_tokens(text), text.lower(), []
        for domain, provider in self._entity_providers.items():
            try:
                names = list(provider(context))
            except Exception:
                continue
            for name in names:
                name_l = str(name).strip().lower()
                if not name_l:
                    continue
                if domain in self._entity_match_all:
                    significant = {t for t in name_tokens(name_l) if len(t) >= 4}
                    hit = bool(significant) and significant <= tokens
                else:
                    hit = bool(head_word(name_l)) and head_word(name_l) in tokens
                if (name_l in lowered or hit) and str(name).strip() not in found:
                    found.append(str(name).strip())
        return found

    def _learned_domains(self, prompt: str, context: Optional["AppContext"]) -> set[str]:
        """What this person taught MIA they mean (core/failure_log.py, tier 1):
        a remembered phrase brings its tool's domain along."""
        book = getattr(context, "failures", None) if context is not None else None
        if book is None:
            return set()
        return {self._actions[p["tool"]].domain for p in book.phrases_in(prompt) if p["tool"] in self._actions}

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
        matched_domains |= self._learned_domains(prompt, context)

        if not matched_domains:
            return []

        # 2026-10-13 (the phone's model, docs/PHONE_MODEL_TEST.md): the
        # general "system" tools used to ride along on every request: 13
        # tools, two-thirds of what a small model has to read, needed by
        # 11 of 187 golden cases. They come only when the words point at
        # one of them (its own trigger phrases or keywords matched the
        # "system" domain above), and then all together, so the old
        # collision pairs (open_module/set_theme, ...) still travel as one.
        # A child is never offered grown-up tools (core/child_accounts.py).
        from core.child_accounts import tool_allowed

        return [action for action in self._actions.values()
                if action.domain in matched_domains and tool_allowed(context, action.domain)]

    def direct_lookup(self, prompt: str, context: Optional["AppContext"] = None) -> Optional[AssistantAction]:
        """The one lookup a question clearly asks for, to run without the
        model (2026-10-13: instant on the phone, and the small model's
        commonest miss was answering such questions from memory). Only
        when the message is a question, exactly one read-only action's own
        trigger phrase matches, it needs no arguments, and nothing that
        changes records matches too; otherwise None and the model decides."""
        from core.child_accounts import tool_allowed

        lowered = f" {prompt.lower().strip()} "
        if not looks_like_question(prompt):
            return None
        matched = [a for a in self._actions.values() if any(p in lowered for p in a.trigger_phrases)
                   and tool_allowed(context, a.domain)]
        if not matched or any(changes_records(a.name) for a in matched):
            return None
        # No details at all (a search word, a date, a filter needs the model to
        # pick it out), and never the journals: their answers stay out of the
        # chat history, which only the model's path handles.
        lookups = [a for a in matched if (not ((a.parameters or {}).get("properties"))
                                          or set((a.parameters or {}).get("properties")) == {a.prompt_arg})
                   and "journal" not in a.name and "journal" not in a.domain and _names_its_subject(a, prompt)]
        return lookups[0] if len(lookups) == 1 and len(matched) == 1 else None

    def named_action(self, prompt: str, offered: Iterable[str]) -> Optional[str]:
        """The one tool the message names in its own words, for when the
        model doesn't use it (2026-10-19, the PC model's misses: "Add a note
        that says buy milk" answered with "what title?"). Exactly one offered
        action's trigger phrase matches and it isn't destructive; a lookup
        only for a question, one that changes records only when the message
        starts with that phrase ("Add a recipe for...", never "do I have a
        recipe for chili?"). And the message says what it's about ("do I
        have" alone never names list_inventory). Else None."""
        lowered = f" {prompt.lower().strip()} "
        offered = set(offered)
        matched = [a for a in self._actions.values() if a.name in offered and any(p in lowered for p in a.trigger_phrases)]
        if len(matched) != 1 or matched[0].destructive or not _names_its_subject(matched[0], prompt):
            return None
        action = matched[0]
        if not changes_records(action.name):
            return action.name if looks_like_question(prompt) else None
        request = _POLITE_START.sub("", prompt.lower().strip())
        return action.name if any(request.startswith(p.strip()) for p in action.trigger_phrases) else None

    def execute(self, context: AppContext, name: str, arguments: dict) -> str:
        """
        Run the named action's handler, or a clear message if the name
        is unknown or the handler raises — a malformed/hallucinated
        tool call from the LLM must never crash the app.
        """
        action = self._actions.get(name)
        if action is None:
            log.warning("Assistant tried to call unknown action '%s'", name)
            from core.failure_log import observe_tool_error

            try:
                observe_tool_error(context, name, "unknown tool", arguments)
            except Exception:
                log.exception("The failure log couldn't record '%s'", name)
            # Like a person who misheard: say so and ask, never "I don't know what to do".
            return "I got that mixed up on my end. Could you say it another way? I've noted it so it gets fixed."
        from core.child_accounts import ASK_A_PARENT, tool_allowed

        if not tool_allowed(context, action.domain):
            log.info("Refused '%s' for a child account.", name)
            return ASK_A_PARENT
        # "Undo that" (core/undo_log.py): what this tool changes can be put back.
        undo = getattr(context, "undo", None)
        recording = undo is not None and changes_records(name) and name != "undo_last_change"
        from core.life_events import acting
        from core.person_settings import person_id

        try:
            # What it changes is recorded as MIA's doing, for this person (core/life_events.py).
            with acting("assistant", person_id(context)):
                if recording:
                    from core.undo_log import recording as record_change

                    with record_change(name, person_id(context)) as change:
                        result = action.handler(context, arguments)
                    undo.add(change)
                else:
                    result = action.handler(context, arguments)
        except Exception as exc:
            log.exception("Assistant action '%s' failed", name)
            from core.failure_log import observe_tool_error

            try:
                observe_tool_error(context, name, f"{type(exc).__name__}: {exc}", arguments)
            except Exception:
                log.exception("The failure log couldn't record '%s'", name)
            return ("Something on my side broke while I was doing that, sorry. I've logged it so it gets fixed. "
                    "You can try again, or do it from its page for now.")
        # Open screens re-read their data (core/main_thread.py), also when
        # the change came from the phone, on the server's thread.
        records_changed(context, name)
        return result


_POLITE_START = re.compile(r"^((hey |ok |okay )?mia[,:]?\s+|please\s+|(can|could|would|will) you\s+(please\s+)?)+")

_QUESTION_STARTS = ("what", "when", "which", "who", "where", "how many", "how much", "how's", "how is", "do i", "did i",
                    "have i", "am i", "is there", "are there", "any ", "show me", "list ")


def _singular(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _names_its_subject(action: AssistantAction, prompt: str) -> bool:
    """Pure logic. The question says what the lookup is about: "alarm" for
    list_alarms, "bill" for list_bills, or one of the action's own
    `subjects` ("chore" for list_household_routines). A generic phrase like
    "do I have" alone never decides."""
    lowered = prompt.lower()
    said = {_singular(w) for w in re.findall(r"[a-z]+", lowered)}
    subject = [_singular(w) for w in action.name.split("_")[1:] if len(w) > 2 and w not in ("my", "the", "all")]
    return any(w in said for w in subject) or any(s in lowered for s in action.subjects)


def looks_like_question(prompt: str) -> bool:
    """Pure logic. A question asking for something MIA knows (not a request to change it)."""
    said = prompt.strip().lower()
    return said.endswith("?") or said.startswith(_QUESTION_STARTS)
