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
   number the results don't hold is asked again once without it, then
   replaced by the results themselves (`core.question_plans.invented_numbers`).
   Her offline library's results (`LIBRARY_TOOLS`) are cut much longer and
   held to their figures strictly, small ones included; said plainly, a
   library result is its first passage and where it's from. A question only
   the library's look-up was offered for, answered without it, is read from
   the library first (`_read_first`). A safety lookup whose answer is worded in code (`SAID_AS_IS`: canning
   times, a meat cure, bleach for water, heat and wind chill, solar sizing, taxes, the outage clock), or one of his
   records' answers in whole sentences (spending against his usual, what to make next, who owes him, his songbook,
   what's biting, the hens, the year's harvest, a high bill, when to fish), is said as it is, never re-worded.

While a round of lookups runs and the model reads what they found, her orb says what it's for, from the tools'
domains (`DOING`, `round_doing`, through core/orb_state.doing: "Thinking · Reading your library"), so the wait is never
a blank (brainstorm 1.1); each lookup itself shows as working.

The sources a library lookup names are kept for the person (core/show_source.py), so "show me where it says that"
opens the very article.

A change (anything that writes records) is never run inside the loop:
the reply goes back to the caller as before, through the usual path.
Two checks (2026-11-10): a lookup the model names that wasn't offered
this turn isn't run; and when a lookup brought in outside text (a web
page or search framed by `untrusted()`, or the inbox's mail), a change
the model then asks for is not handed on: MIA says what she would do
and the person says it again (`held_after_outside_text`), so words on
a page can't steer her into acting. Browser steps keep their own gate. The
loop runs only against this computer's Ollama (the phone's small model
keeps one round). Pure orchestration: `run()` calls the model and the
lookups it's given; the desktop runs it on its ChatWorker thread, the
web and voice inside `run_assistant_turn`.
A SAID_AS_IS answer drops a failed lookup to the usual path, a repeat, and a sibling's refusal (NOT_AN_ANSWER), and
keeps the model's words for a two-part question's other part (`two_part`).
A tool whose one detail is his question (its `prompt_arg`) is given his own words, never the model's (`his_words`).
"""

from __future__ import annotations

import re
import time
from typing import Optional

from core.llm_manager import ChatReply, ToolCall
from core.logger import get_logger

log = get_logger(__name__)

MAX_STEPS = 3
RESULT_CHARS = 1500
# Her offline library's reading (core/reference_reader.py): several passages and how to talk about them, which a
# 1,500-character cut would lose; and their figures are held to the text exactly, small ones too (2 drops, 4 cups).
LIBRARY_TOOLS = {"look_up_offline": 7000, "read_reference": 7000}
# Lookups whose answer is safety numbers worked out and worded in code: said as they are, never re-worded by the
# model, which squeezed "the wind chill gets down to about 18°F around 7 am..." into "18°F, 7 am, 3 pm." and could
# drop a pressure, a nitrite level or a warning (live check through run_assistant_turn, 2026-11-24).
# And his records' answers, already whole sentences: re-worded, "am I spending more than usual?" became "check the
# Money app", his songbook "I learned Yesterday", and once "$X ... $Y" (the same live check).
SAID_AS_IS = frozenset({"canning_time", "meat_cure", "bleach_for_water", "work_outside_wind_chill_heat_index",
                        "size_solar", "tax_set_aside", "power_outage",
                        "spending_vs_usual", "what_to_make_next", "who_owes_me", "songs_i_can_play", "whats_biting",
                        "why_hens_not_laying", "harvest_this_year", "why_bill_high", "best_time_to_fish",
                        "practice_today",
                        # the calculators: their figures are worked out in code (live sweep 2026-11-25: the model
                        # wrapped 62 bags in "The user is looking for...")
                        "calculate_concrete", "calculate_board_feet", "material_list", "cut_list", "feed_mix"})

# What her orb says while a lookup runs (brainstorm 1.1), by the tool's domain; the rest say "Looking it up".
DOING = {"library": "Reading your library", "budget": "Checking your money", "debts": "Checking your money",
         "ledger": "Checking your money", "today": "Checking your day", "calendar": "Checking your calendar",
         "missions": "Checking your missions", "maintenance": "Checking your upkeep", "kitchen": "Checking the kitchen",
         "groceries": "Checking the groceries", "flock": "Checking the flock", "health": "Checking your health log",
         "memory": "Remembering", "browser": "Looking online", "maps": "Checking the map", "music": "Checking music",
         "inventory": "Checking what's on hand", "materials": "Checking materials", "jobs": "Checking jobs",
         "learning": "Checking your learning", "journal": "Reading your journal"}


def _remember_sources(context, text: str) -> None:
    """Keeps the sources a library lookup named, for "show me where it says that" (core/show_source.py)."""
    from core import show_source
    from core.person_settings import person_id

    try:
        show_source.remember(person_id(context), show_source.sources_in(text))
    except Exception:  # noqa: BLE001 - remembering never breaks a turn
        log.exception("Couldn't keep the library's sources")


def round_doing(registry, names: list) -> str:
    """Pure logic. What a round of lookups is for, in her orb's few words: the library's when it reads the library,
    else the first lookup's (`doing_words`)."""
    if any(n in LIBRARY_TOOLS for n in names):
        return DOING["library"]
    return doing_words(registry, names[0]) if names else "Looking it up"


def doing_words(registry, name: str) -> str:
    """Pure logic. The few words her orb shows while this tool runs: by its domain (`DOING`), else "Looking it up"."""
    action = getattr(registry, "_actions", {}).get(name)
    return DOING.get(getattr(action, "domain", ""), "Looking it up")
DEFAULT_BUDGET = 60.0

FOLLOW_UP = (
    "Those are the results of the lookups. If one more lookup would answer the person's question better, call it. "
    "Otherwise answer the question now, from these results: the answer first, in a few short sentences; only numbers "
    "and names the results contain; say what's missing if something needed isn't there; one next step only if it "
    "follows from the results. Talk like a person, not a report, in plain text: no headings, bold or symbols."
)
LAST_WORD = ("That's all the looking up there's time for. Answer the person's question now from the results above, "
             "the answer first; say plainly what you couldn't check.")


def loop_ok(context) -> bool:
    """Only against this computer's Ollama (the phone keeps one round)."""
    from core.llm_manager import OllamaBackend

    llm = getattr(context, "llm", None)
    return isinstance(getattr(llm, "_backend", None), OllamaBackend) and getattr(llm, "home", None) is None


def _lookups_only(context, calls: list[ToolCall]) -> bool:
    """Whether every tool call in a reply only reads (a lookup), so the results can be answered from directly."""
    from core.assistant_actions import changes_records

    registry = getattr(context, "assistant_actions", None)
    known = getattr(registry, "_actions", {}) if registry is not None else {}
    return bool(calls) and all(c.name in known and not changes_records(c.name) for c in calls)


# Lookups whose results carry outside text, and what that text is (WP-03): mail senders and subjects, World
# Intelligence's finds (titles as feeds and search results gave them), a receipt's lines as read from a scan, and a
# team's workspace (notes written from what they read). Their results are framed before the model sees them.
OUTSIDE_WHAT = {"list_inbox": "Mail and letters in the inbox", "world_finds": "Finds from feeds and searches",
                "get_receipt": "A receipt read from a scan", "whats_in_the_workspace": "A project's workspace notes",
                "find_on_youtube": "Song titles and channels from YouTube"}
OUTSIDE_TOOLS = frozenset(OUTSIDE_WHAT)


def _brought_outside_text(results: list[tuple[str, str]]) -> bool:
    """Whether any lookup this turn returned outside text: framed by untrusted(), or from an OUTSIDE_TOOLS lookup."""
    from core.browser_safety import carries_outside_text

    return any(name in OUTSIDE_TOOLS or carries_outside_text(text) for name, text in results)


def held_after_outside_text(context, reply: ChatReply) -> ChatReply:
    """The reply to give instead of a change asked for right after outside text: what MIA would do, to be said again.
    Browser steps (their own gate, DEC-0117) are never held here."""
    registry = getattr(context, "assistant_actions", None)
    known = getattr(registry, "_actions", {}) if registry is not None else {}
    from core.assistant_browser_actions import DOMAIN as BROWSER

    if all(getattr(known.get(c.name), "domain", "") == BROWSER for c in reply.tool_calls):
        return reply
    names = ", ".join(c.name.replace("_", " ") for c in reply.tool_calls)
    log.info("Tool loop: held a change after outside text (%s).", names)
    return ChatReply(content=(f"I just read something from outside MIA, so I won't act on it in the same breath. "
                              f"I'd {names}. Say so and I'll do it."), tool_calls=[])


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


def _read_first(context, tools: list[dict], prompt: str, reply: ChatReply) -> ChatReply:
    """A how-to or factual question her offline library can answer, answered from memory (2026-11-22, live:
    qwen2.5:14b gave bleach figures of its own, or said "let me look that up" without looking): when the library's
    look-up is the only lookup offered and the message is a question (or asked the way a how-to is, without a
    question mark: ASKING) with something to look up, the look-up runs in code, so the answer is read from the
    library (facts found in code, the model only phrases them)."""
    from core.assistant_actions import changes_records, looks_like_question

    from core.assistant_library_actions import ASKING
    from core.reference_reader import terms

    names = [t.get("function", {}).get("name", "") for t in tools]
    lookups = [n for n in names if not changes_records(n)]
    library = getattr(context, "reference_library", None)
    lowered = f" {prompt.lower()} "
    asked = looks_like_question(prompt) or any(re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", lowered) for a in ASKING)
    if ("look_up_offline" not in lookups or any(n not in LIBRARY_TOOLS for n in lookups) or not asked
            or len(terms(prompt)) < 2 or library is None or not library.list_packs()):
        return reply  # spoken how-tos count ("how do I purify water"); "tell me more?" has nothing to look up
    log.info("Tool loop: a question for the library answered without reading it; reading it first.")
    return ChatReply(content="", tool_calls=[ToolCall(name="look_up_offline", arguments={"question": prompt})])


_REQUEST_STARTS = ("can you", "could you", "would you", "will you", "can u", "please", "i want you to",
                   "i need you to", "go ahead", "let's", "lets")
ANSWER_ONLY = ("They asked a question, not for a change: answer it, using lookups if you need them. Don't add, "
               "change or delete anything; if a change would help, offer it in one short question at the end.")


def asks_not_tells(prompt: str) -> bool:
    """Pure logic. A question that isn't a request ("What lessons have I
    learned?", not "can you add milk?" or "add milk")."""
    from core.assistant_actions import looks_like_question
    from core.question_plans import CHANGE_VERBS

    said = (prompt or "").strip().lower()
    first = said.split(" ", 1)[0].strip(",.!?") if said else ""
    return looks_like_question(prompt) and not said.startswith(_REQUEST_STARTS) and first not in CHANGE_VERBS


def _wants_change(context, reply: ChatReply) -> bool:
    """Whether a reply asks for any tool call that changes a record (core/main_thread.call_changes: material_list
    without keep only works a size out)."""
    from core.main_thread import call_changes

    return any(call_changes(c.name, c.arguments) for c in reply.tool_calls)


def _answer_instead(context, llm, messages: list[dict], tools: list[dict], reply: ChatReply) -> ChatReply:
    """A change nobody asked for (2026-10-30, the benchmark: "What lessons
    have I learned?" reached for add_course, "make to order or keep
    inventory?" for add_inventory_item): one more try, lookups only, told
    to answer. Its answer (or its lookups) replaces the change; never the
    change itself."""
    from core.assistant_actions import changes_records

    lookups = [t for t in tools if not changes_records(t.get("function", {}).get("name", ""))]
    retry = llm.chat_with_tools(messages + [{"role": "system", "content": ANSWER_ONLY}], lookups)
    log.info("Tool loop: a question reached for a change (%s); answered instead.",
             ", ".join(c.name for c in reply.tool_calls))
    if retry is not None and not _wants_change(context, retry) and (retry.content.strip() or retry.tool_calls):
        return retry
    return ChatReply(content="I can answer that, but I'd need to change something to do it. What would you like me to do?",
                     tool_calls=[])


def his_words(registry, call: ToolCall, prompt: str) -> dict:
    """A call's arguments, with a tool's `prompt_arg` (the one detail that is his question: canning_time, feed_mix...)
    given his own words, or on a follow-up the question it makes (core/conversation_state.turn_follow_up), never the
    model's (live check, 2026-11-25: "how long do I pressure can quart jars of green beans?" reached canning_time with
    the tool's own description as the question, and was refused)."""
    arguments = dict(call.arguments or {})
    action = getattr(registry, "_actions", {}).get(call.name)
    field = getattr(action, "prompt_arg", "") if action is not None else ""
    if not field or not str(prompt or "").strip():
        return arguments
    from core.conversation_state import turn_follow_up

    follow = turn_follow_up()
    own = follow is not None and follow[1] and follow[0] == str(prompt).strip()  # this turn's follow-up, not another's
    arguments[field] = follow[1] if own else str(prompt).strip()
    return arguments


def _short(text: str, name: str = "") -> str:
    """A tool's result cut to RESULT_CHARS (1,500; LIBRARY_TOOLS their own) at a word, marked as cut short."""
    text = str(text or "").strip()
    limit = LIBRARY_TOOLS.get(name, RESULT_CHARS)
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …(cut short)"


def _library_said(text: str) -> str:
    """Pure logic. A library result as it can be said plainly: its first passage with where it's from, without the
    frame and the note on how to talk."""
    lines = [ln for ln in str(text or "").splitlines()
             if not ln.startswith(("[From her offline library", "[End of", "ref: ", "Answer from these"))]
    body = "\n".join(lines).strip()
    first = body.split("\n\n")[0].strip()
    return (first.replace("\n", ": ", 1) if first.startswith("From ") else first) or body


def without_figures(answer: str, wrong: set[str], keep_share: float = 0.6) -> str:
    """Pure logic. A library answer with the sentences (or list lines) that state a figure the text doesn't hold taken
    out, when most of it stays; "" when too little would (then the passage itself is said)."""
    from core.question_plans import numbers_in

    text = re.sub(r"(?m)^\s*(\d{1,2}[.)]|[-*•])\s+", "", str(answer or "").strip())  # a list's own markers
    parts = [p for p in re.split(r"(?<=[.!?])\s+|\n+", text) if p.strip()]
    kept = [p for p in parts if not (numbers_in(p) & wrong)]
    if not parts or len(kept) < keep_share * len(parts) or len(kept) < 2:
        return ""
    return " ".join(p.strip() for p in kept)


def _plain(results: list[tuple[str, str]]) -> str:
    """Every tool result's text, one after another (a library result as its first passage, said plainly)."""
    return " ".join(_library_said(text) if name in LIBRARY_TOOLS else text for name, text in results)


def run(context, llm, messages: list[dict], tools: list[dict], prompt: str, named: Optional[str] = None,
        budget: Optional[float] = None) -> Optional[ChatReply]:
    """One turn with the loop: the model's reply when it isn't only
    lookups (unchanged, for the caller's usual path); else one answer
    built from what it looked up (the library's sources kept for "show me
    where it says that", core/show_source.py), her orb saying what each round is for
    until the model's follow-up is back (`round_doing`). A lookup that brings outside text
    (OUTSIDE_WHAT) is framed as information before the model reads it
    (WP-03). Only lookups offered in `tools` run,
    and a change asked for after a lookup that brought in outside text
    is held and said back (held_after_outside_text). A question only her
    library's look-up was offered for is read from it first
    (`_read_first`); a library answer's figures are held to its text
    strictly (when every result is the library's), and one still
    stating its own after the retry loses just those sentences
    (`without_figures`); every library answer passes her safety floor
    (`_finish`, core/reference_reader.floor), with what the library was
    asked beside the question (a follow-up names its food there), and
    the guide's page looked up in code when the turn's reading missed it.
    Lookups that are all SAID_AS_IS (safety numbers worded in code) are the answer as they are.
    SAID_AS_IS answers skip failures and repeats, and keep the model's words (never figures) for a two-part
    question's other part.
    A tool's `prompt_arg` is given his words (`his_words`)."""
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
        reply = _read_first(context, tools, prompt, reply)
    if reply is not None and not reply.tool_calls and tools and loop_ok(context):
        reply = _look_first(context, llm, messages, tools, prompt, reply)
    if reply is not None and tools and loop_ok(context) and _wants_change(context, reply) and asks_not_tells(prompt):
        reply = _answer_instead(context, llm, messages, tools, reply)
    if reply is None or not tools or not loop_ok(context) or not _lookups_only(context, reply.tool_calls):
        return reply

    registry = context.assistant_actions
    offered = {t.get("function", {}).get("name", "") for t in tools}
    talk = list(messages)
    results: list[tuple[str, str]] = []
    asked = ""  # what the library was asked: a follow-up names its food there
    seen: set[str] = set()
    step = 0
    while reply is not None and _lookups_only(context, reply.tool_calls):
        fresh = [c for c in reply.tool_calls if f"{c.name}:{sorted((c.arguments or {}).items())}" not in seen]
        if not fresh or step >= MAX_STEPS or (step and time.monotonic() - started > budget):
            break  # the first round always runs
        talk.append({"role": "assistant", "content": reply.content or "",
                     "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments or {}}} for c in fresh]})
        from core import orb_state

        # Her orb says what this round is for (1.1) from its first lookup until the model's follow-up is back: the
        # lookups take milliseconds, the wait is the model reading what they found (review 2026-11-23).
        round_words = orb_state.doing(round_doing(registry, [c.name for c in fresh]))
        round_words.__enter__()
        try:
            for call in fresh:
                seen.add(f"{call.name}:{sorted((call.arguments or {}).items())}")
                if call.name not in offered:
                    log.warning("Tool loop: the model named %s, which wasn't offered this turn; not run.", call.name)
                    results.append((call.name, f"(The {call.name} lookup isn't available for this question.)"))
                    talk.append({"role": "tool", "content": results[-1][1], "tool_name": call.name})
                    continue
                try:
                    with orb_state.active("working"):  # the lookup itself
                        text = registry.execute(context, call.name, his_words(registry, call, prompt))
                except Exception:
                    log.exception("Lookup %s failed in the tool loop", call.name)
                    text = f"(The {call.name} lookup failed.)"
                results.append((call.name, text))
                if call.name in LIBRARY_TOOLS:
                    asked += " " + " ".join(str(v) for v in (call.arguments or {}).values())
                    _remember_sources(context, text)  # "show me where it says that" (core/show_source.py)
                shown = _short(text, call.name)
                if call.name in OUTSIDE_WHAT:  # outside text, marked as information before the model reads it (WP-03)
                    from core.browser_safety import outside

                    shown = outside(shown, OUTSIDE_WHAT[call.name])
                talk.append({"role": "tool", "content": shown, "tool_name": call.name})
            step += 1
            last = step >= MAX_STEPS or time.monotonic() - started > budget
            reply = llm.chat_with_tools(talk + [{"role": "system", "content": LAST_WORD if last else FOLLOW_UP}],
                                        [] if last else tools)
        finally:
            round_words.__exit__(None, None, None)
    log.info("Tool loop: %d round(s), %s, %.1fs", step, ", ".join(n for n, _ in results), time.monotonic() - started)
    if reply is not None and reply.tool_calls and not _lookups_only(context, reply.tool_calls):
        if _brought_outside_text(results):
            return held_after_outside_text(context, reply)  # words from a page or a mail never steer a change
        if not asks_not_tells(prompt):
            return reply  # a change they asked for: the caller's usual path (approval), after looking things up
        reply = llm.chat_with_tools(talk + [{"role": "system", "content": ANSWER_ONLY}], [])  # never unasked
    if not results:
        return reply
    if (all(name in SAID_AS_IS for name, _t in results) and not (reply is not None and reply.tool_calls)
            and not any(text.startswith("(The ") for _n, text in results)):  # a failed lookup goes the usual way
        texts = list(dict.fromkeys(t for _n, t in results))  # the same answer twice is said once
        answered = [t for t in texts if not t.startswith(NOT_AN_ANSWER)]
        text = "\n\n".join(answered or texts)  # a sibling lookup's "I can't" never stands beside an answer
        extra = ((reply.content if reply is not None else "") or "").strip()
        # the model's own words for the question's other part: never figures (those are a squeezed copy of the
        # tool's, "20 minutes, 10 lb, 1,000 ft": the live check)
        if extra and two_part(prompt) and not re.search(r"\d", extra):
            from core.plain_words import strip_markdown

            text += "\n\n" + strip_markdown(extra)  # the model's answer to the question's other part
        return _finish(context, prompt, asked, results, text)
    said = (reply.content if reply is not None else "") or ""
    sources = "\n".join(text for _n, text in results)
    strict = all(name in LIBRARY_TOOLS for name, _t in results)  # a reference's figures, small ones too
    wrong = invented_numbers(said, sources, prompt, strict) if said.strip() else set()
    if wrong:
        # Often general knowledge ("every 5,000 miles"), not a misread record: one more try without those
        # numbers before falling back to the bare results (2026-10-30, live).
        where = "the library's text" if strict else "their records"
        retry = llm.chat_with_tools(talk + [{"role": "assistant", "content": said}, {"role": "system", "content": (
            f"Your answer used numbers that aren't in {where}: {', '.join(sorted(wrong))}. Write the same answer "
            f"again, keeping everything else in it: only those numbers change, to the ones {where} gives, exactly, "
            "or to words where it gives none.")}], [])
        again = (retry.content if retry is not None else "") or ""
        if strict and len(again.strip()) < 0.5 * len(said.strip()):
            again = ""  # a retry that lost most of the answer: the answer itself is trimmed instead
        if again.strip() and not invented_numbers(again, sources, prompt, strict):
            return _finish(context, prompt, asked, results, again.strip())
        trimmed = without_figures(again or said, invented_numbers(again or said, sources, prompt, strict)) \
            if strict else ""
        if trimmed:  # a library answer: only the sentences with a figure of its own go (2026-11-22, live)
            log.warning("Tool loop: a library answer stated figures the text didn't; those sentences left out.")
            from core.plain_words import strip_markdown

            return _finish(context, prompt, asked, results, strip_markdown(trimmed))
        log.warning("Tool loop answer had numbers the lookups didn't (%s); saying the results instead.",
                    ", ".join(sorted(wrong)))
        failures = getattr(context, "failures", None)
        if failures is not None:  # for the answers.numbers loop: the tools, never the words
            try:
                failures.record("invented_number", tool=",".join(n for n, _t in results)[:200])
            except Exception:
                log.exception("Couldn't note the invented number.")
    if not said.strip() or wrong:
        return _finish(context, prompt, asked, results, _plain(results))
    from core.plain_words import strip_markdown

    return _finish(context, prompt, asked, results, strip_markdown(said))


# How a SAID_AS_IS lookup says it couldn't answer (asks for a detail, or has no tested figure)
NOT_AN_ANSWER = ("I only give", "How much meat", "How much water", "How much power", "I don't know your town",
                 "The forecast I have doesn't")


def two_part(prompt: str) -> bool:
    """Pure logic. Whether a question asks two things ("how long for green beans, and can I reuse the lids?"): then a
    SAID_AS_IS answer keeps the model's reply after the tool's (review 2026-11-24: the lids part was lost)."""
    said = str(prompt or "").lower()
    return said.count("?") >= 2 or bool(re.search(
        r"\b(and|also|plus)\s+(can|could|should|do|does|is|are|will|how|what|why|when|where|which)\b", said))


def _finish(context, prompt: str, asked: str, results: list, text: str) -> ChatReply:
    """The answer, with her library's safety floor under it when it was read from the library
    (core/reference_reader.floor: canning a low-acid food is never told as a water bath), what the library was asked
    beside the question (a follow-up names its food there). When the floor must replace the answer and this turn's
    reading holds no guide page to give instead (the model asked in its own words and missed it), the person's own
    question is looked up in code for it. A first-aid answer from the library ends with when to call for help
    (core/first_aid_floor.library_floor)."""
    if any(name in LIBRARY_TOOLS for name, _t in results):
        from core.reference_reader import NO_PAGE, floor

        sources = "\n\n".join(t for name, t in results if name in LIBRARY_TOOLS)
        said = floor(prompt + asked, text, sources)
        library = getattr(context, "reference_library", None)
        if said.endswith(NO_PAGE) and library is not None:
            from core.offline_library import look_up

            try:
                said = floor(prompt + asked, text, look_up(library, prompt))
            except Exception:  # noqa: BLE001 - the rule alone stands
                log.exception("The floor's own look-up failed.")
        text = said
        from core.first_aid_floor import library_floor  # a first-aid answer says when to call for help (4.2)
        from core.region import region_for

        text = library_floor(prompt, text, region_for(context))
    return ChatReply(content=text, tool_calls=[])
