"""
core.council_floor
====================

Who has the floor in the council, and how little it costs (DEC-0080/0081;
Zac, 2026-11-04: "the AI need to be able to communicate to each other but
in some smart restricted manor as to not needlessly have them eat up the
usage. They wont be much of a council if they cant communicate";
`docs/COUNCIL_AND_CHRONICLES_REVIEW.md` section 3).

No member can call another. Everything passes through `run()`, which MIA
moderates:

- **Each of Zac's messages opens a turn with a budget** (`plan()`): asking
  members by name costs one call each, plus one for a question they pass
  on; "debate" is two rounds among those named; "discuss", "work it out"
  or `@all` is up to `DISCUSS_BUDGET`; "budget 4" says it outright (up to
  `MAX_BUDGET`). MIA's own answers and summaries cost no one's usage.
- **A member asks another with one line**, `ASK codex: <question>`, at the
  end of its answer. `gate()` passes it on only if the budget has room, the
  member is here and not resting at a usage limit (core/dev_usage.py), it
  isn't the asker, the question isn't a repeat of one in the thread, and it
  isn't one MIA answers from what's decided (those go to her, free). A
  question that's held says why, in the thread.
- **Members read a short context, not the chat** (`context_for()`): a
  short thread as it is; a long one as MIA's summary (her local model,
  cached) plus the last two messages.
- **It stops by itself**: when the budget is spent, when everyone in a
  debate says AGREE, when a member only repeats itself, when nobody's left
  who's here, or when Zac says stop in the thread.
- **Then MIA sums up** when two or more members spoke: where they agree,
  where they don't, what's open.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from core import council
from core.failure_log import similar

DISCUSS_BUDGET = 6
MAX_BUDGET = 12
REPEAT = 0.6  # a question this alike to one already asked in the thread is a repeat
SAME_POINT = 0.7  # an answer this alike to the member's last one adds nothing new
SHORT_THREAD = 3  # messages a member reads as they are; past this, a summary

ASK_LINE = re.compile(r"^\s*ASK\s+@?(\w+)\s*:\s*(.+?)\s*$", re.I | re.M)
AGREE = re.compile(r"^\s*AGREE\b", re.I | re.M)
DEBATE = re.compile(r"\b(debate|argue|challenge|push back|disagree)\b", re.I)
DISCUSS = re.compile(r"\b(discuss|work (it|this) out|figure (it|this) out|talk (it|this) (over|through))\b|@all\b", re.I)
SAID_BUDGET = re.compile(r"\bbudget\s*(?:of\s*)?(\d+)\b", re.I)
STOP = re.compile(r"^\s*(stop|hold on|that's enough|enough|end( the)? council)\b", re.I)
# Questions about what's already decided or recorded: MIA's, from her documents, free.
DECIDED = re.compile(r"\b(what did we decide|did we decide|was it decided|is there a decision|what's the "
                     r"decision|DEC-\d{4}|which task|what task|T-\d{4})\b", re.I)

SUMMARY_PROMPT = (
    "Summarize this part of a development discussion in at most 120 words, as notes for someone joining: "
    "what was asked, each member's position, where they agree, where they don't, and anything still open. "
    "Name who said what. No advice of your own.\n\n{text}"
)
WRAP_PROMPT = (
    "The discussion:\n{text}\n\n"
    "You're MIA, moderating your development council. Write only your summary of the discussion above, in at "
    "most 90 words: where the members agree, where they disagree (who and on what), and what's still open or "
    "should become a task. Plain sentences, no headings, no quotes from the discussion. Name each member. "
    "Don't add opinions of your own."
)


def tidy(text: str, names: list[str]) -> str:
    """Pure logic. A model's reply without what it echoed: transcript lines ("[qwen] ...") and its own
    name as a prefix ("Coder: ...")."""
    lines = [ln for ln in (text or "").splitlines()
             if not re.match(r"^\s*\[(" + "|".join(map(re.escape, names)) + r")\]", ln, re.I)]
    out = "\n".join(lines).strip()
    return re.sub(r"^\s*(" + "|".join(map(re.escape, names)) + r")\s*:\s*", "", out, flags=re.I).strip()


def plan(text: str, here: list[str]) -> dict:
    """Pure logic. What one of Zac's messages asks for: who, in what order, how many rounds, what budget."""
    roster = list(council.members())
    named = council.mentions(text, roster)
    everyone = "@all" in (text or "").lower()
    if everyone:
        named = [n for n in roster if n in here and n != "mia"]
    asked = [n for n in named if n != "mia"]
    if DEBATE.search(text or "") and len(asked) >= 2:
        mode, rounds, budget = "debate", 2, 2 * len(asked)
    elif DISCUSS.search(text or "") or everyone:
        mode, rounds, budget = "discuss", 1, DISCUSS_BUDGET
        if not asked:  # "council, work it out": everyone who's here
            named = [n for n in roster if n in here and n != "mia"]
    else:
        mode, rounds, budget = "ask", 1, len(asked) + (1 if asked else 0)
    said = SAID_BUDGET.search(text or "")
    if said:
        budget = int(said.group(1))
    return {"mode": mode, "order": named, "rounds": rounds, "budget": max(0, min(budget, MAX_BUDGET))}


FAILED = "(I couldn't answer"


def spoke(m: dict) -> bool:
    """A member's real answer: not MIA's, and not a call that failed (a limit or an error costs no answer)."""
    return m.get("kind") == "answer" and m.get("who") != "mia" and not str(m.get("text", "")).startswith(FAILED)


def spent(turn: str, messages: list[dict]) -> int:
    """Calls a turn has used: members' answers, never MIA's."""
    return sum(1 for m in messages if m.get("turn") == turn and spoke(m))


def ask_line(answer_text: str) -> Optional[tuple[str, str]]:
    """Pure logic. The one member and question an answer passes on, if it ends with an ASK line."""
    found = ASK_LINE.findall(answer_text or "")
    return (found[-1][0].lower(), found[-1][1]) if found else None


def gate(asker: str, target: str, question: str, messages: list[dict], budget_left: int,
         ready: set) -> tuple[str, str]:
    """Pure logic. ("pass" | "mia" | "hold", why) for a question one member puts to another."""
    roster = council.members()
    if target not in roster:
        return "hold", f"there's no member called {target}"
    if target == asker:
        return "hold", "a member can't ask itself"
    if target == "mia" or DECIDED.search(question):
        return "mia", "it's about what's decided, which MIA answers from her documents"
    for m in messages:
        earlier = m.get("question") or ""
        if earlier and similar(earlier, question) >= REPEAT:
            return "hold", "it was already asked in this thread"
    if budget_left <= 0:
        return "hold", "this turn's budget is spent"
    if target not in ready:
        return "hold", f"{roster[target]['name']} isn't available right now"
    return "pass", ""


def _plain(messages: list[dict]) -> str:
    return "\n".join(f"[{m['who']}] {m['text'][:600]}" for m in messages)


_SUMMARIES: dict[tuple[str, int], str] = {}


def context_for(messages: list[dict], summarize: Optional[Callable[[str], str]]) -> str:
    """What a member reads of the thread: as it is when short; else MIA's summary and the last two."""
    said = [m for m in messages if m.get("kind") != "note"]
    if len(said) <= SHORT_THREAD:
        return _plain(said) or "(nothing yet)"
    earlier, last = said[:-2], said[-2:]
    key = (earlier[0].get("thread", ""), len(earlier))
    if key not in _SUMMARIES:
        text = ""
        if summarize:
            try:
                text = summarize(SUMMARY_PROMPT.format(text=_plain(earlier)))
            except Exception:  # no local model: a plain cut instead
                text = ""
        _SUMMARIES[key] = text.strip() or "\n".join(f"[{m['who']}] {m['text'][:160]}" for m in earlier)
    return f"Summary of the thread so far (by MIA):\n{_SUMMARIES[key]}\n\nThe latest:\n{_plain(last)}"


def ready_members() -> set:
    """Members here and not resting at a usage limit (DEC-0079)."""
    from core import dev_usage

    roster = council.members()
    out = set()
    for name in council.here():
        try:
            if dev_usage.state(roster[name]["provider"])["state"] == "cooling":
                continue
        except OSError:
            pass
        out.add(name)
    return out | {"mia"}


def _local_model(prompt: str) -> str:
    from core.work_review import ask_provider

    return ask_provider("ollama", prompt, purpose="summary")


def run(root: dict, *, ask: Optional[Callable[[str, str], str]] = None,
        summarize: Optional[Callable[[str], str]] = _local_model, ready: Optional[set] = None,
        on_turn: Optional[Callable[[str, bool], None]] = None, repo=None, store=None) -> list[dict]:
    """Work one of Zac's messages through the council within its budget. Returns what was posted."""
    store = store or council._store()
    ready = set(ready) if ready is not None else ready_members()
    p = root.get("plan") or plan(root["text"], sorted(ready))
    thread_id, turn = root.get("thread") or root["id"], root.get("turn") or root["id"]
    posted: list[dict] = []
    last_said: dict[str, str] = {}
    out_of_it: set = set()

    def note(text: str, **extra) -> None:
        posted.append(council.post("mia", text, reply_to=root["id"], repo=repo, store=store, kind="note",
                                   thread=thread_id, turn=turn, **extra))

    def stopped() -> bool:
        messages = council.thread(thread_id, store)
        ids = [m.get("id") for m in messages]
        after = messages[ids.index(root["id"]) + 1:] if root["id"] in ids else []
        return any(m.get("who") == "zac" and STOP.match(m.get("text", "")) for m in after)

    def speak(name: str, prompt_message: dict) -> Optional[dict]:
        if on_turn:
            on_turn(name, True)
        try:
            messages = council.thread(thread_id, store)
            context = context_for([m for m in messages if m.get("id") != prompt_message.get("id")], summarize)
            said = council.answer(name, prompt_message, ask=ask, repo=repo, store=store, context=context)
        finally:
            if on_turn:
                on_turn(name, False)
        posted.append(said)
        if said["text"].startswith(FAILED):
            ready.discard(name)
        return said

    queue: list[tuple[str, dict]] = []
    for _ in range(p["rounds"]):
        queue.extend((n, root) for n in p["order"])
    if not queue:
        return posted
    rounds_seen: dict[str, int] = {}
    while queue:
        name, prompt_message = queue.pop(0)
        if stopped():
            note("Stopped, as you asked.")
            break
        if name in out_of_it:
            if prompt_message is not root:
                note(f"Held the question for {council.members()[name]['name']}: they've only been repeating "
                     "themselves.")
            continue
        if name == "mia":
            speak("mia", prompt_message)
            continue
        if spent(turn, council.thread(thread_id, store)) >= p["budget"]:
            note(f"That's this turn's budget ({p['budget']} calls). Ask for more with \"budget\" and a number.")
            break
        if name not in ready:
            note(f"{council.members()[name]['name']} isn't available right now, so they're skipped.")
            continue
        rounds_seen[name] = rounds_seen.get(name, 0) + 1
        if p["mode"] == "debate" and rounds_seen[name] > 1:
            prompt_message = {**root, "text": root["text"] + "\n\n(Second round: answer the others' points "
                              "directly. If you agree with where it's landed, end with AGREE.)"}
        said = speak(name, prompt_message)
        if said is None or name not in ready:
            continue
        if name in last_said and similar(last_said[name], said["text"]) >= SAME_POINT:
            out_of_it.add(name)  # nothing new from them: no more rounds
        last_said[name] = said["text"]
        if p["mode"] == "debate" and all(AGREE.search(last_said.get(n, "")) for n in p["order"] if n != "mia"):
            note("They agree.")
            queue = [q for q in queue if q[0] == "mia"]
        passed = ask_line(said["text"])
        if passed:
            target, question = passed
            messages = council.thread(thread_id, store)
            left = p["budget"] - spent(turn, messages)
            verdict, why = gate(name, target, question, messages, left, ready)
            asker = council.members()[name]["name"]
            if verdict == "hold":
                note(f"Held {asker}'s question for {target}: {why}.", question=question)
            else:
                who = "mia" if verdict == "mia" else target
                passing = council.post("mia", f"{asker} asks {council.members()[who]['name']}: {question}",
                                       reply_to=said["id"], repo=repo, store=store, kind="note",
                                       thread=thread_id, turn=turn, question=question)
                posted.append(passing)
                if who != "mia":  # the question takes their turn this round: one call, not two
                    pending = next((i for i, q in enumerate(queue) if q == (who, root)), None)
                    if pending is not None:
                        queue.pop(pending)
                queue.insert(0, (who, passing))
    speakers = {m["who"] for m in posted if spoke(m)}
    if len(speakers) >= 2 and summarize:
        try:
            wrap = summarize(WRAP_PROMPT.format(text=_plain([m for m in council.thread(thread_id, store)
                                                            if m.get("kind") != "note"])))
        except Exception:
            wrap = ""
        wrap = tidy(wrap, ["zac", *council.members()])
        if wrap:
            posted.append(council.post("mia", wrap, reply_to=root["id"], repo=repo, store=store,
                                       kind="summary", thread=thread_id, turn=turn))
    return posted
