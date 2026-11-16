"""
core.step_plan_actions
========================

Plans across apps (UI-7, core/step_plans.py) on the action contract in core/actions.py:

- `steps.plan_week`: line up this week's steps from today's list (nothing in the plan runs).
- `steps.do`: do one waiting step. The approval card shows the step's own sentence, and the step's action runs as
  the person; undoing it puts back what the step changed and the step waits again.
- `steps.change`: give a waiting step new details, checked by its own action.
- `steps.drop`: leave one step out. `steps.drop_plan`: leave out everything still waiting.

A plan's steps are only ever kinds that reach the person's own records and can be undone (core/step_plans._allowed),
so `steps.do` never reaches further than that either.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _plans(context):
    """The person's plans."""
    from core.step_plans import book

    return book(context)


def _step(context, params):
    """The plan and step the parameters name (the newest open plan when none is named); ActionError otherwise."""
    from core.step_plans import PlanError

    try:
        plan = _plans(context).find(str(params.get("plan_id") or ""))
        return plan, _plans(context).step(plan, params.get("step_id") or params.get("step"))
    except PlanError as problem:
        raise ActionError(str(problem)) from None


def _run(call):
    """Runs a plan operation, turning its refusal into the action contract's."""
    from core.step_plans import PlanError

    try:
        return call()
    except PlanError as problem:
        raise ActionError(str(problem)) from None


def _describe_week(context, params) -> str:
    """The sentence for `steps.plan_week`: how many steps today's list offers."""
    from core.step_plans import week_items

    count = len(week_items(context))
    if not count:
        raise ActionError("Nothing due has a step I can take for you.")
    return f"Line up {count} step{'s' if count != 1 else ''} from what's due, for you to do one at a time"


def _plan_week(context, params) -> str:
    """Does `steps.plan_week` and says what's in the plan."""
    from core.step_plans import plan_week

    plan = _run(lambda: plan_week(context))
    waiting, cant = len(plan.waiting()), sum(1 for s in plan.steps if s.status == "cant")
    return (f"\"{plan.title}\" has {waiting} step{'s' if waiting != 1 else ''} waiting for you"
            + (f", and {cant} I can't do from here" if cant else "") + ". Nothing has been changed.")


def _describe_do(context, params) -> str:
    """The sentence for `steps.do`: the step's own, checked as things are now, and where it sits in its plan."""
    from core.step_plans import WAITING, _allowed, _said

    plan, step = _step(context, params)
    if step.status != WAITING:
        raise ActionError(f"Step {plan.number(step)} is already {_said(step.status)}.")
    if _allowed(step.kind):
        raise ActionError(f"Step {plan.number(step)} can't be done here: {_allowed(step.kind)}.")
    try:
        summary = ACTION_TYPES[step.kind].describe(context, step.params)
    except ValueError as problem:
        raise ActionError(f"Step {plan.number(step)} can't be done as it is: {problem}") from None
    return f"{summary} (step {plan.number(step)} of {len(plan.steps)} in \"{plan.title}\")"


def _do(context, params) -> str:
    """Does `steps.do` and says what happened and what's next."""
    plan, step = _step(context, params)
    done = _run(lambda: _plans(context).do(context, plan.plan_id, step.step_id))
    if done.status != "done":
        raise ActionError(f"Step {plan.number(done)} didn't work: {done.why}")
    left = plan.waiting()
    return done.result + (f" Next: step {plan.number(left[0])}, {left[0].summary}." if left
                          else f" That was the last step of \"{plan.title}\".")


def _describe_change(context, params) -> str:
    """The sentence for `steps.change`; the new details are checked when it runs."""
    plan, step = _step(context, params)
    if not isinstance(params.get("params"), dict) or not params["params"]:
        raise ActionError("Say what to change about the step.")
    return f"Change step {plan.number(step)} of \"{plan.title}\""


def _change(context, params) -> str:
    """Does `steps.change` and says the step as it now reads."""
    plan, step = _step(context, params)
    changed = _run(lambda: _plans(context).change(context, plan.plan_id, step.step_id, params.get("params") or {}))
    return f"Step {plan.number(changed)} now reads: {changed.summary}."


def _describe_drop(context, params) -> str:
    """The sentence for `steps.drop`."""
    plan, step = _step(context, params)
    if step.status != "waiting":
        raise ActionError(f"Step {plan.number(step)} isn't waiting.")
    return f"Leave step {plan.number(step)} out of \"{plan.title}\" ({step.summary})"


def _drop(context, params) -> str:
    """Does `steps.drop`."""
    plan, step = _step(context, params)
    _run(lambda: _plans(context).drop(context, plan.plan_id, step.step_id))
    left = len(plan.waiting())
    return f"Left out. {left} step{'s' if left != 1 else ''} still waiting." if left else "Left out. The plan is finished."


def _describe_drop_plan(context, params) -> str:
    """The sentence for `steps.drop_plan`."""
    plan = _run(lambda: _plans(context).find(str(params.get("plan_id") or "")))
    waiting = len(plan.waiting())
    return f"Leave out the {waiting} step{'s' if waiting != 1 else ''} still waiting in \"{plan.title}\""


def _drop_plan(context, params) -> str:
    """Does `steps.drop_plan`."""
    plan = _run(lambda: _plans(context).find(str(params.get("plan_id") or "")))
    _run(lambda: _plans(context).drop_plan(context, plan.plan_id))
    return f"\"{plan.title}\" is closed. What was already done stays done."


_WHICH = {"plan_id": "optional: the plan (the newest open one)", "step_id": "the step, or its number"}

for _a in (
    ActionType("steps.plan_week", "Plan My Week", {}, _describe_week, _plan_week),
    ActionType("steps.do", "Do It", dict(_WHICH), _describe_do, _do),
    ActionType("steps.change", "Change", {**_WHICH, "params": "the details to change"}, _describe_change, _change),
    ActionType("steps.drop", "Leave Out", dict(_WHICH), _describe_drop, _drop),
    ActionType("steps.drop_plan", "Drop The Rest", {"plan_id": "optional: the plan"}, _describe_drop_plan, _drop_plan),
):
    ACTION_TYPES[_a.kind] = _a
