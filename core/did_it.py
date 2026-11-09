"""
core.did_it
=============

"I did X" (DEC-0148; Zac, 2026-11-08: "anything I talk about or say I did X today should be evaluated for how MIA
can incorporate it into missions or track it"). When the person says what they did ("I just put away the dishes
and started a load of laundry"), MIA's own code, no model:

- **keeps it**: each activity is a line in their own history (a `did` life event, sealed a line at a time), so
  Natural Momentum (core/momentum.py) can see what got done, in what order, and when;
- **counts it** toward a household routine it names ("laundry" counts toward the Laundry routine), through the
  same `routine.log` action the Household screen uses, so "undo that" takes it back;
- **offers once** what else it could count toward, one question, kept only on a yes: an open task with that name
  (`task.done`), a mission objective it matches (`objective.tick`), or, when it's something they keep doing that
  nothing tracks yet (said on another day in the last two weeks, or "I've been ..."), a new routine (`routine.add`).

A message that's only what they did is answered here (`reply`). One that also asks something goes to the model as
usual, and afterwards the activities are kept and the one offer made (`offer_after`), never counting a routine
there (the model may already have). The answer to an offer is read before the next turn (`answer_offer`). Never in a
private, journal or personal conversation; never "I did something stupid" (no vague or self-critical objects) and
never "I didn't".
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

EVENT = "did"
REPEAT_DAYS = 14  # an untracked activity said on another day this recently is offered as a routine
_VERBS = ("did", "finished", "made", "cleaned", "washed", "started", "put away", "picked up", "cooked", "fed",
          "watered", "mowed", "fixed", "took out", "folded", "vacuumed", "swept", "mopped", "prepped", "prepared",
          "set out", "built", "planted", "harvested", "organized", "organised", "repaired", "changed", "emptied",
          "loaded", "unloaded", "ran", "walked", "practiced", "practised", "worked on", "painted", "sanded", "stained",
          "baked", "canned", "ordered", "paid", "scrubbed", "tidied", "dusted", "hung", "repotted", "weeded", "split",
          "stacked", "hauled", "collected", "delegated", "wrote", "read", "studied", "brewed", "packed", "charged",
          "cleared", "trimmed", "pruned", "replaced", "installed", "sorted", "filed", "got", "put")
_VERB = "|".join(sorted((re.escape(v) for v in _VERBS), key=len, reverse=True))
_LEAD = re.compile(r"^(?:and\s+|then\s+|also\s+|so\s+)*(?:i\s+(?:just\s+|already\s+|finally\s+|also\s+|then\s+)*"
                   r"|just\s+|already\s+|finally\s+)?(" + _VERB + r")\b\s*(.*)$")
_HABIT = re.compile(r"^i'?(?:ve| have)\s+been\s+([a-z]+ing)\b\s*(.*)$")
_SPLIT = re.compile(r"\s*(?:,\s*(?:and\s+|then\s+)?|;\s*|\s+and then\s+|\s+then\s+|\s+and\s+(?=(?:i\s+)?(?:"
                    + _VERB + r")\b))\s*")
_VAGUE = re.compile(r"^(?:it|that|this|something|nothing|anything|everything|my best|wrong|so|a mistake|mistakes|"
                    r"a mess|a fool|an error|it all)\b")
_NEGATIVE = re.compile(r"\b(?:didn'?t|did not|never|haven'?t|wasn'?t|couldn'?t|can'?t)\b")
_YES = re.compile(r"^\s*(?:yes|yeah|yep|yup|sure|ok(?:ay)?|please|do it|go ahead|track it|count it|make it one|"
                  r"yes please)[.!\s]*$", re.I)
_COUNTING = frozenset({"times", "time", "days", "day", "week", "weeks", "minutes", "hours"})
_NAME_STOP = frozenset({"the", "a", "an", "my", "our", "some", "just", "been", "today", "this"})
_STOP = frozenset({"the", "a", "an", "my", "our", "some", "of", "up", "away", "out", "load", "loads", "all", "today",
                   "this", "morning", "just", "for", "to", "and", "in", "on", "at", "with", "it", "them", "off"})


def _clean(text: str) -> str:
    """Pure logic. Lowercase, curly quotes straightened, spaces tidied, the closing punctuation off."""
    text = (text or "").replace("’", "'").lower()
    return " ".join(text.split()).strip(" .!")


def activities(text: str) -> tuple[list[str], bool]:
    """Pure logic. The activities a person says they did, each as said ("put away the dishes"), and whether that's
    all the message is (nothing else in it, no question). "I've been running" is a habit: ("been running"). None for
    a negative, a question, or a vague or self-critical object."""
    said = _clean(text)
    if not said or _NEGATIVE.search(said):
        return [], False
    habit = _HABIT.match(said.rstrip("?"))
    if habit:
        what = f"{habit.group(1)} {habit.group(2)}".strip()
        return ([f"been {what}"], "?" not in said) if not _VAGUE.match(habit.group(2) or "x") else ([], False)
    parts = [p for p in _SPLIT.split(said.rstrip("?")) if p]
    found, whole = [], "?" not in said
    for part in parts:
        m = _LEAD.match(part)
        if not m or not m.group(2) or _VAGUE.match(m.group(2)):
            whole = False
            continue
        found.append(f"{m.group(1)} {m.group(2)}".strip())
    if found and not _LEAD.match(parts[0]):
        whole = False
    return found, whole and bool(found)


def key(what: str) -> str:
    """Pure logic. What an activity is, for counting repeats: its words without the little ones, each singular
    ("put away the dishes" and "put the dishes away" are both "put dish")."""
    words = (re.sub(r"'s$|'$", "", w) for w in re.findall(r"[a-z']+", (what or "").lower()))  # tomorrow's -> tomorrow
    return " ".join(_singular(w) for w in words if w and w not in _STOP)


def _singular(word: str) -> str:
    """Pure logic. A word without a plural ending, roughly (dishes -> dish, plants -> plant)."""
    if len(word) > 4 and word.endswith("es") and word[-3] in "sxhz":
        return word[:-2]
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _words(text: str) -> set:
    """Pure logic. An activity's or a name's meaningful words, singular."""
    return set(key(text).split())


def _routines(context) -> list:
    """The active household routines (recurring-mission templates in the Household category)."""
    book = getattr(context, "recurring_missions", None)
    if book is None:
        return []
    return [t for t in book.all_templates() if t.category == "Household" and t.active]


def routine_for(context, what: str):
    """The household routine an activity names (every word of the routine's name is in it: "a load of laundry"
    counts toward Laundry), or None."""
    words = _words(what)
    matches = [t for t in _routines(context) if _words(t.name) and _words(t.name) <= words]
    return max(matches, key=lambda t: len(_words(t.name)), default=None)


def _stem(word: str) -> str:
    """Pure logic. A word without its verb ending, roughly, so "fixed" meets "fix" and "walking" meets "walk"."""
    for end in ("ing", "ed", "e"):
        if word.endswith(end) and len(word) - len(end) >= 3:
            return word[: -len(end)]
    return word


def _close(what: str, name: str) -> bool:
    """Pure logic. Whether an activity and a task's or objective's name are about the same thing: all of a short
    name's words (one or two), or two of a longer one's, by their stems ("fixed the gate" is "Fix the gate"); numbers
    don't count ("Walk the dog 10 times")."""
    words = {_stem(w) for w in _words(what)}
    wanted = {_stem(w) for w in _words(name) if len(w) >= 3 and not w.isdigit() and w not in _COUNTING}
    shared = words & wanted
    return bool(wanted) and (shared == wanted if len(wanted) <= 2 else len(shared) >= 2)


def evaluate(context, what: str, today: Optional[date] = None, habit: bool = False) -> Optional[dict]:
    """How MIA could count an activity that no routine counts: {kind (the action), params, line (the question)}, or
    None. In order: an open task with that name, an objective of an active mission it matches (a tally not yet
    reached), then something done again and nothing tracks, as a new routine."""
    tasks = getattr(context, "tasks", None)
    for t in (tasks.all_tasks() if tasks is not None else []):
        if not t.done and _close(what, t.title):
            return {"kind": "task.done", "params": {"task_id": t.task_id},
                    "line": f"Is that your task “{t.title}”? Want me to mark it done?"}
    missions = getattr(context, "missions", None)
    for m in (missions.all_missions() if missions is not None else []):
        if m.status != "active" or m.recurring_template_id:
            continue
        for i, o in enumerate(m.objectives):
            if o.metric_type == "tally" and o.progress < o.target and _close(what, o.description):
                return {"kind": "objective.tick", "params": {"mission_id": m.mission_id, "index": i, "amount": 1},
                        "line": f"That counts toward “{o.description}” on your mission {m.name}. Want me to count it?"}
    name = _routine_name(what)
    if habit:
        return {"kind": "routine.add", "params": {"name": name, "times": 1, "every": "day"},
                "line": f"Want me to track {name.lower()} as a routine, with a streak?"}
    days = _days_done(context, key(what), today or date.today())
    if days:
        return {"kind": "routine.add", "params": {"name": name, "times": 1, "every": "day" if len(days) >= 2 else "week"},
                "line": f"You did that on {len(days) + 1} days lately. Want me to make {name.lower()} a routine, "
                        "with a streak?"}
    return None


def _routine_name(what: str) -> str:
    """Pure logic. A routine's name from an activity: its words without the articles and "been", the first
    capitalised ("put away the dishes" -> "Put away dishes"; "been running every morning" -> "Running every
    morning")."""
    words = [w for w in re.findall(r"[a-z']+", what.lower()) if w not in _NAME_STOP]
    text = " ".join(words) or what
    return text[:1].upper() + text[1:60]


def _days_done(context, wanted: str, today: date) -> set:
    """The other days in the last REPEAT_DAYS the person said they did this (by its key), today left out."""
    from core.life_events import events_for

    since = (today - timedelta(days=REPEAT_DAYS)).isoformat()
    try:
        found = events_for(context, since=since, types=[EVENT])
    except Exception:
        log.exception("Couldn't read the history for repeats")
        return set()
    return {e.at[:10] for e in found if (e.payload or {}).get("key") == wanted and e.at[:10] != today.isoformat()}


def _keep(context, what: str) -> None:
    """One activity as a line in the person's own history (their personal log, else the household's)."""
    from core import life_events

    where = getattr(context, "personal_life_events", None) or getattr(context, "life_events", None)
    life_events.record(where, EVENT, f"Did: {what}", payload={"key": key(what)}, source="said")


def _private(conversation) -> bool:
    """Whether this conversation is one MIA never takes from (core/life_notes.py's rule: off the record, the journal,
    a private turn, a personal mode)."""
    from core.life_notes import _private as private

    return private(conversation)


def _run(context, kind: str, params: dict) -> str:
    """Does an action as the person (proposed and approved in one step, as their own words asked), and says what
    happened; ActionError's words when it's refused."""
    from core.actions import ActionError

    actions = getattr(context, "actions", None)
    if actions is None:
        return "I can't do that here."
    try:
        done = actions.approve(context, actions.propose(context, kind, params, proposed_by="person").proposal_id)
    except ActionError as problem:
        return str(problem)
    return done.result if done.status == "executed" else str(done.result or "That didn't go through.")


def _offer_for(context, conversation, found: list, habit: bool) -> Optional[str]:
    """The one question for the first activity a routine doesn't name (a routine's is counted, by this code or the
    model), kept on the conversation for its answer."""
    for what in found:
        if routine_for(context, what) is not None:
            continue
        offer = evaluate(context, what, habit=habit)
        if offer is not None:
            conversation.pending_track = {**offer, "what": what, "at": datetime.now().isoformat(timespec="seconds")}
            return offer["line"]
    return None


def _passing(context, prompt: str) -> bool:
    """Whether a passing mention (core/passing_mentions.py) is about a record MIA keeps ("paid the electric bill",
    "changed the mower's oil"): that offer is the better one, so this steps aside."""
    from core.passing_mentions import detect_offer

    try:
        return detect_offer(prompt, context) is not None
    except Exception:
        log.exception("Couldn't check for a passing mention")
        return False


def reply(context, conversation, prompt: str) -> Optional[str]:
    """A message that's only what they did: each activity kept, routines counted, one offer for the rest, and the
    reply in words; None when it isn't one, a passing mention is about a kept record, or it's private."""
    if conversation is None or _private(conversation) or _passing(context, prompt):
        return None
    found, whole = activities(prompt)
    if not found or not whole:
        return None
    habit = found[0].startswith("been ")
    counted, noted = [], []
    for what in found:
        _keep(context, what)
        template = None if habit else routine_for(context, what)
        if template is not None:
            counted.append(_run(context, "routine.log", {"template_id": template.template_id}))
        else:
            noted.append(what)
    lines = counted + ([f"Noted: {', '.join(noted)}."] if noted and not habit else [])
    if habit:
        lines.append(f"Good to know you've {found[0]}.")
    if counted:
        lines.append("(Say “undo that” to take it back.)")
    from core import momentum

    following = None if momentum.in_flow(context) else momentum.next_in_chain(context, key(found[-1]))
    offer = _offer_for(context, conversation, found, habit)
    if offer:
        lines.append(offer)
    elif following:
        lines.append(f"Often after that you {following}.")
    conversation.did_handled = prompt
    return " ".join(lines)


def offer_after(context, conversation, prompt: str) -> Optional[str]:
    """After MIA's reply to a message that also said what they did: the activities kept, and one offer for one a
    routine doesn't name. None when the turn was handled here already, it's private, or there's nothing to offer."""
    if conversation is None or _private(conversation) or getattr(conversation, "did_handled", None) == prompt:
        return None
    if getattr(conversation, "pending_note", None) or getattr(getattr(conversation, "pending_offer", None), "shown",
                                                              False):
        return None  # she already asked something this turn (life notes, a passing mention): one question at a time
    found, _whole = activities(prompt)
    if not found:
        return None
    for what in found:
        _keep(context, what)
    return _offer_for(context, conversation, found, found[0].startswith("been "))


def answer_offer(context, conversation, prompt: str) -> Optional[str]:
    """Before a turn: a yes to MIA's offer does it (as the person, undoable); anything else lets it go."""
    pending = getattr(conversation, "pending_track", None) if conversation is not None else None
    if not pending:
        return None
    conversation.pending_track = None
    if not _YES.match(prompt or ""):
        return None
    params = dict(pending["params"])
    if pending["kind"] == "routine.add":
        params["times"] = str(params.get("times", 1))
    said = _run(context, pending["kind"], params)
    return f"{said} (Say “undo that” to take it back.)"
