"""
core.training_actions
=======================

The live workout session's changes (DEC-0055, core/training_session.py)
as action kinds on the contract in core/actions.py, so the Workout
screen, the glasses and voice all move the one session the same way:
start today's training, a set done (with how it was counted), skip the
rest, skip an exercise, pause, resume, correct the last count, finish.
Each person's own, and child-safe (workouts are in CHILD_APPS; no
weights are asked of a child).
"""

from __future__ import annotations

from datetime import datetime

from core import training_session as ts
from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _store(context):
    return _need(context, "training")


def _live(context):
    s = _store(context).live()
    if s is None:
        raise ActionError("There's no workout going. Say \"start my workout\".")
    return s


def _number(value, what: str):
    if value in (None, ""):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ActionError(f"The {what} should be a number.") from None
    if n < 0 or n > 10000:
        raise ActionError(f"That {what} doesn't look right.")
    return n


def _run(context, change) -> str:
    """Apply one transition to the live session, save, and say where they are."""
    store, now = _store(context), datetime.now()
    s = _live(context)
    try:
        change(s, now)
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    store.save()
    return ts.say(s, now)


# ---------------------------------------------------------------- start / finish


def _describe_start(context, params) -> str:
    fit = _need(context, "fitness")
    todays = fit.today_training()
    if not todays:
        raise ActionError("Today's a rest day in your plan. Rest counts too.")
    if _store(context).live() is not None:
        raise ActionError("A workout is already going.")
    return f"Start today's training: {todays.get('name') or 'your workout'}"


def _start(context, params) -> str:
    todays = _need(context, "fitness").today_training()
    if not todays:
        raise ActionError("Today's a rest day in your plan.")
    try:
        s = _store(context).begin(todays)
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    first = s.steps[0]
    return (f"{s.title}: {len(s.steps)} exercise{'s' if len(s.steps) != 1 else ''}. First up, {first.name}, "
            f"{first.sets} set{'s' if first.sets != 1 else ''} of {ts.target_text(first)}. Let's go.")


def _finish(context, params) -> str:
    store = _store(context)
    s = _live(context)
    done = sum(len(st.done) for st in s.steps)
    try:
        store.finish()
    except ValueError as exc:
        raise ActionError(str(exc)) from None
    if not done:
        return "Workout closed. Nothing was logged, and that's fine."
    return f"Workout done: {done} set{'s' if done != 1 else ''} in the books. Nice work."


# ---------------------------------------------------------------- during


def _describe_set(context, params) -> str:
    name = (ts.view(_live(context), datetime.now()).get("now") or {}).get("name") or "this exercise"
    reps, seconds = _number(params.get("reps"), "reps"), _number(params.get("seconds"), "time")
    what = f"{int(reps)} reps" if reps is not None else f"{seconds:g} seconds" if seconds is not None else "a set"
    return f"Log {what} for {name}"


def _set(context, params) -> str:
    reps, seconds = _number(params.get("reps"), "reps"), _number(params.get("seconds"), "time")
    from core.child_accounts import is_child

    weight = None if is_child(context) else _number(params.get("weight"), "weight")
    counted = str(params.get("counted") or "told")
    return _run(context, lambda s, now: ts.log_set(s, now, reps=int(reps) if reps is not None else None,
                                                  seconds=seconds, weight=weight, counted=counted))


def _correct(context, params) -> str:
    reps, seconds = _number(params.get("reps"), "reps"), _number(params.get("seconds"), "time")
    _run(context, lambda s, now: ts.correct(s, reps=int(reps) if reps is not None else None, seconds=seconds))
    return f"Changed to {int(reps)} reps." if reps is not None else f"Changed to {seconds:g} seconds."


def _simple(change, what: str):
    return (lambda context, params: f"{what}"), (lambda context, params: _run(context, change))


_KINDS = [
    ActionType("training.start", "Start workout", {}, _describe_start, _start, True),
    ActionType("training.set", "Set done", {"reps": "", "seconds": "", "weight": "", "counted": "said|cadence|told|tapped"},
               _describe_set, _set, True),
    ActionType("training.correct", "Correct", {"reps": "", "seconds": ""},
               lambda c, p: "Correct the last set's count", _correct, True),
    ActionType("training.skip_rest", "Skip rest", {}, *_simple(ts.skip_rest, "Skip the rest"), True),
    ActionType("training.skip", "Skip exercise", {}, *_simple(ts.skip_exercise, "Skip this exercise"), True),
    ActionType("training.pause", "Pause", {}, *_simple(ts.pause, "Pause the workout"), True),
    ActionType("training.resume", "Resume", {}, *_simple(ts.resume, "Resume the workout"), True),
    ActionType("training.finish", "Finish", {}, lambda c, p: "Finish the workout", _finish, True),
]
TRAINING_ACTIONS = {k.kind: k for k in _KINDS}
ACTION_TYPES.update(TRAINING_ACTIONS)
