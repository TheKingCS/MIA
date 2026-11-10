"""
core.trade_actions
==================

Trade Master's walkthroughs (core/trade_session.py, DEC-0149) as action kinds on the contract in core/actions.py, so the
screen and voice move the one session the same way: start a job or a diagnosis, next, back, "checked" (a hold point),
yes or no (a diagnosis), stop; and plan a job as a mission, its phases as objectives (`trade.plan`). Not offered to
child accounts (DEC-0119).

`reply()` is the voice, in code, no model: while a job is in progress, "next", "checked", "why?", "what should I
watch for?", "back", "where am I?", "stop the job", and yes or no in a diagnosis; any time, "walk me through building
the coop" or "my toilet keeps running, help me figure it out" starts one. Whatever is said, words that mean a stop
rule is happening ("I smell gas", "I'm bleeding") stop the session first.
"""

from __future__ import annotations

import re
from typing import Optional

from core import trade_session as js
from core import trades
from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _store(context):
    """The person's job store, or ActionError when it isn't here."""
    return _need(context, "trade_session")


def _live(context) -> js.Session:
    """The job in progress, or ActionError saying how to start one."""
    s = _store(context).live()
    if s is None:
        raise ActionError("No job in progress. Say “walk me through” and the job, like “walk me through building "
                          "the coop”.")
    return s


def _item(params):
    """The job or diagnosis the params name, or ActionError."""
    trades._loaded()
    item = trades.JOBS.get(str(params.get("item_id", ""))) or trades.DIAGNOSES.get(str(params.get("item_id", "")))
    if item is None:
        raise ActionError("I don't have that job written yet.")
    return item


def _mission_for(context, item) -> str:
    """The active mission planned for this job (`trade.plan`), so a session counts toward it; "" when there's none."""
    missions = getattr(context, "missions", None)
    name = _mission_name(item)
    found = next((m for m in (missions.all_missions() if missions is not None else [])
                  if m.status == "active" and m.name == name), None)
    return found.mission_id if found is not None else ""


def _mission_name(item) -> str:
    """Pure logic. The mission a job becomes: "Build: Chicken coop and run"."""
    verb = {"build": "Build", "install": "Install", "repair": "Fix"}.get(getattr(item, "kind", ""), "Do")
    return f"{verb}: {item.name}"


def _start(context, params) -> str:
    """Does `trade.start`: the job or diagnosis becomes the session, and it says what it is, its stop rules' reminder
    and the first step. A job is a mission from the start (Zac, 2026-11-09: in Missions, not on Today): its planned
    mission if there is one, else one made now, one objective a phase, each counted as its steps are done."""
    item = _item(params)
    store = _store(context)
    try:
        s = store.begin(item, mission_id=_mission_for(context, item))
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    made = ""
    if not s.mission_id and isinstance(item, trades.Job) and getattr(context, "missions", None) is not None:
        s.mission_id = _make_mission(context, item).mission_id  # made once the job has really started
        store.save()
        made = f"It's in your Missions as \u201c{_mission_name(item)}\u201d. "
    lead = trades.outline(item) if isinstance(item, trades.Diagnosis) else (
        f"{item.name}{'' if item.status == trades.CONFIRMED else ' (drafted from its sources, not yet confirmed by a person)'}. "
        f"{len(item.phases)} phases, {len(item.steps())} steps. Permit: {item.permit} Wear: {', '.join(item.ppe)}.")
    return f"{lead} {made}{js.say(s)}" if isinstance(item, trades.Job) else lead


def _save_and(context, s, said: str) -> str:
    """Saves the session and returns what to say (the store's save puts a session that just finished or stopped in
    the person's history)."""
    _store(context).save()
    return said


def _next(context, params) -> str:
    """Does `trade.next`: the next step (refused at an unchecked hold point), counting the step toward its phase on the
    planned mission."""
    s = _live(context)
    before = js.progress(s)
    moved, said = js.next_step(s)
    if moved and s.mission_id and before:
        missions = getattr(context, "missions", None)
        try:
            if missions is not None:
                missions.increment_tally(s.mission_id, before["phase_index"], 1)
        except (ValueError, IndexError):
            pass  # the mission was changed by hand: the session goes on without it
    return _save_and(context, s, said)


def _check(context, params) -> str:
    """Does `trade.check`: the hold point in focus is verified."""
    s = _live(context)
    return _save_and(context, s, js.confirm(s))


def _back(context, params) -> str:
    """Does `trade.back`: one step back."""
    s = _live(context)
    return _save_and(context, s, js.back(s))


def _answer(context, params) -> str:
    """Does `trade.answer`: a diagnosis's yes or no."""
    s = _live(context)
    said = str(params.get("answer", "")).strip().lower()
    if said not in ("yes", "no"):
        raise ActionError("Yes or no?")
    return _save_and(context, s, js.answer(s, said == "yes"))


def _stop(context, params) -> str:
    """Does `trade.stop`: stops the session (for a stop rule when its id is given)."""
    s = _live(context)
    rule = trades.STOP_RULES.get(str(params.get("rule", "")))
    return _save_and(context, s, js.stop(s, rule))


def _plan(context, params) -> str:
    """Does `trade.plan`: the job becomes a mission, one objective a phase (its steps to count), its scope as the
    summary; a session on it counts toward it."""
    item = _item(params)
    if not isinstance(item, trades.Job):
        raise ActionError("A diagnosis isn't a mission: say “help me figure it out” to start it.")
    _need(context, "missions")
    if _mission_for(context, item):
        raise ActionError(f"“{_mission_name(item)}” is already one of your missions.")
    mission = _make_mission(context, item)
    live = _store(context).live()
    if live is not None and live.item_id == item.id:
        live.mission_id = mission.mission_id
        _store(context).save()
    return f"Added the mission “{mission.name}”: {len(item.phases)} phases, each counted as you work its steps."


def _make_mission(context, item):
    """The job as a new mission: its scope as the summary, one tally objective a phase (its steps to count)."""
    missions = context.missions
    mission = missions.add_mission(_mission_name(item), summary=item.scope, icon="\U0001F6E0")
    for phase in item.phases:
        missions.add_objective(mission.mission_id, phase.name, "tally", len(phase.steps))
    return missions.get_mission(mission.mission_id)


def _describe_item(verb: str):
    """The approval card's sentence for an action on a named job."""
    return lambda c, p: f"{verb} {_item(p).name}"


for _kind, _label, _params, _describe, _execute in (
    ("trade.start", "Start", {"item_id": "the job or diagnosis"}, _describe_item("Start"), _start),
    ("trade.next", "Next Step", {}, lambda c, p: "Next step", _next),
    ("trade.check", "Checked", {}, lambda c, p: "The hold point is checked", _check),
    ("trade.back", "Back", {}, lambda c, p: "Back a step", _back),
    ("trade.answer", "Answer", {"answer": "yes or no"}, lambda c, p: f"Answer {p.get('answer', '')}", _answer),
    ("trade.stop", "Stop", {"rule": "optional: the stop rule"}, lambda c, p: "Stop the job", _stop),
    ("trade.plan", "Make It a Mission", {"item_id": "the job"}, _describe_item("Plan"), _plan),
):
    ACTION_TYPES[_kind] = ActionType(_kind, _label, _params, _describe, _execute)


# ------------------------------------------------------------------ the voice, in code

_START = re.compile(r"\b(?:walk me through|talk me through|help me (?:build|fix|figure out|diagnose|install|make)|"
                    r"teach me (?:to|how to) (?:build|fix|install|make)|how do i (?:build|fix|install|make)|"
                    r"start the .+ job|let'?s (?:build|fix|install|make)|help me figure it out|diagnose)\b")
_PHRASES = (
    (re.compile(r"^(?:ok(?:ay)?[, ]+)?(?:next|next step|what'?s next|done with (?:that|this)(?: one)?|go on|"
                r"continue|keep going)[.!]*$"), "trade.next", {}),
    (re.compile(r"^(?:checked|it'?s checked|verified|confirmed|done checking|all checked|check)[.!]*$"),
     "trade.check", {}),
    (re.compile(r"^(?:back|go back|previous(?: step)?|back a step|last step)[.!]*$"), "trade.back", {}),
    (re.compile(r"^(?:stop the job|stop (?:this|it)|end the job|i'?m done for (?:now|today)|pause the job)[.!]*$"),
     "trade.stop", {}),
    (re.compile(r"^(?:yes|yeah|yep|it does|it is|there is)[.!]*$"), "trade.answer", {"answer": "yes"}),
    (re.compile(r"^(?:no|nope|it doesn'?t|it isn'?t|there isn'?t)[.!]*$"), "trade.answer", {"answer": "no"}),
)
_WHY = re.compile(r"^(?:why|why\?|why (?:do|does|is|are) (?:we|i|that|this)\b.*|what'?s (?:that|this) for)")
_WATCH = re.compile(r"\b(?:watch (?:out )?for|what could go wrong|common mistakes?|careful about|look out for)\b")
_WHERE = re.compile(r"^(?:where am i|where was i|repeat|say (?:that|it) again|what step(?: am i on)?)[?.!]*$")


def _run(context, kind: str, params: dict) -> str:
    """Does an action as the person (proposed and approved in one step, as their own words asked)."""
    actions = getattr(context, "actions", None)
    if actions is None:
        return "I can't do that here."
    try:
        done = actions.approve(context, actions.propose(context, kind, params, proposed_by="person").proposal_id)
    except ActionError as problem:
        return str(problem)
    return done.result if done.status == "executed" else str(done.result or "That didn't go through.")


def reply(context, text: str) -> Optional[str]:
    """What MIA says, in code, to the words while a job is in progress (or to start one); None when the words aren't
    for a job. A stop rule's words stop a session in progress first, whatever else was said."""
    store = getattr(context, "trade_session", None)
    if store is None:
        return None
    said = " ".join((text or "").lower().replace("’", "'").split()).strip()
    live = store.live()
    if live is not None:
        rule = js.stop_for(said)
        if rule is not None:
            return _run(context, "trade.stop", {"rule": rule.id})
        for pattern, kind, params in _PHRASES:
            if pattern.match(said) and (kind != "trade.answer" or live.kind == "diagnosis"):
                return _run(context, kind, params)
        if _WHY.match(said):
            return js.why(live)
        if _WATCH.search(said):
            return js.watch(live)
        if _WHERE.match(said):
            return js.say(live)
        if re.search(r"\b(?:make (?:it|this) a mission|add (?:it|this) to (?:my )?missions)\b", said):
            return _run(context, "trade.plan", {"item_id": live.item_id})
    if _START.search(said):
        item = trades.find(said)
        if item is not None:
            if re.search(r"\b(?:mission|plan)\b", said) and isinstance(item, trades.Job):
                return _run(context, "trade.plan", {"item_id": item.id})
            return _run(context, "trade.start", {"item_id": item.id})
    return None
