"""
core.taught_skill_actions
===========================

Taught skills' actions (DEC-0123, core/taught_skills.py) on the action
contract: proposed in plain words, approved, run, undoable.

- `taught_skill.add`: a new skill from its name and its steps written as
  lines (teaching by telling).
- `taught_skill.steps`: change a skill's steps (it goes back to
  practising).
- `taught_skill.delete`: forget a skill.
- `taught_skill.watch`: start watching ("watch me: the Friday reset").
- `taught_skill.keep`: keep what was shown as a skill.
- `taught_skill.cancel`: drop what was being shown.

Running a skill isn't one action: it's a run that can stop for the person
several times (`taught_skills.start` / `answer` / `stop`), and each step
in it goes through its own gate.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.taught_skills import CLEAN_RUNS, SkillError, parse_steps, say_step, step_problems


def _book(context):
    """The person's taught skills, or ActionError when this MIA doesn't have them."""
    return _need(context, "taught_skills")


def _skill(context, params):
    """The skill the params name, or ActionError."""
    skill = _book(context).get(str(params.get("skill_id") or ""))
    if skill is None:
        raise ActionError("That skill isn't here anymore.")
    return skill


def _steps(context, params) -> list:
    """The steps written in the params, read and checked; ActionError in the engine's own words."""
    try:
        steps = parse_steps(params.get("steps"))
    except SkillError as problem:
        raise ActionError(str(problem)) from None
    wrong = step_problems(context, steps)
    if wrong:
        raise ActionError(" ".join(wrong))
    return steps


def _said(context, steps: list) -> str:
    """Steps as one numbered sentence."""
    return " ".join(f"{n}. {say_step(context, s)}." for n, s in enumerate(steps, 1))


def _name(context, params) -> str:
    """The new skill's name from the params, or ActionError when it's missing or taken."""
    name = " ".join(str(params.get("name") or "").split())
    if not name:
        raise ActionError("What should the skill be called?")
    if any(s.name.lower() == name.lower() for s in _book(context).skills):
        raise ActionError(f"There's already a skill called {name}.")
    return name


def _add_describe(context, params) -> str:
    """The approval sentence for `taught_skill.add`."""
    return f"Teach me \"{_name(context, params)}\": {_said(context, _steps(context, params))}"


def _add_execute(context, params) -> str:
    """Does `taught_skill.add`."""
    try:
        skill = _book(context).add(_name(context, params), _steps(context, params), about=params.get("about") or "",
                                   source=params.get("source") or "told in steps")
    except SkillError as problem:
        raise ActionError(str(problem)) from None
    return f"Got it. \"{skill.name}\" is practising: {CLEAN_RUNS} clean runs with you and I'll have learned it."


def _steps_describe(context, params) -> str:
    """The approval sentence for `taught_skill.steps`."""
    skill = _skill(context, params)
    back = " It goes back to practising." if skill.state == "learned" else ""
    return f"Change \"{skill.name}\" to: {_said(context, _steps(context, params))}{back}"


def _steps_execute(context, params) -> str:
    """Does `taught_skill.steps`."""
    skill = _skill(context, params)
    try:
        _book(context).set_steps(skill.skill_id, _steps(context, params))
    except SkillError as problem:
        raise ActionError(str(problem)) from None
    return f"Changed \"{skill.name}\". It's practising again."


def _delete_describe(context, params) -> str:
    """The approval sentence for `taught_skill.delete`."""
    return f"Forget the skill \"{_skill(context, params).name}\""


def _delete_execute(context, params) -> str:
    """Does `taught_skill.delete`."""
    skill = _skill(context, params)
    _book(context).delete(skill.skill_id)
    return f"Forgot \"{skill.name}\"."


def _watch_describe(context, params) -> str:
    """The approval sentence for `taught_skill.watch`."""
    book = _book(context)
    if book.recording is not None:
        raise ActionError(f"I'm already watching for \"{book.recording['name']}\".")
    return f"Watch what you do next and keep it as the skill \"{_name(context, params)}\""


def _watch_execute(context, params) -> str:
    """Does `taught_skill.watch`."""
    try:
        _book(context).start_watching(_name(context, params))
    except SkillError as problem:
        raise ActionError(str(problem)) from None
    return "Watching. Do it with me, one thing at a time, then press Keep (or say \"that's it\")."


def _shown(context) -> dict:
    """What's being shown right now, or ActionError when she isn't watching."""
    recording = _book(context).recording
    if recording is None:
        raise ActionError("I'm not watching anything right now.")
    return recording


def _keep_describe(context, params) -> str:
    """The approval sentence for `taught_skill.keep`."""
    shown = _shown(context)
    if not shown["steps"]:
        raise ActionError("I haven't seen you do anything yet.")
    return f"Keep \"{shown['name']}\": {_said(context, shown['steps'])}"


def _keep_execute(context, params) -> str:
    """Does `taught_skill.keep`."""
    try:
        skill = _book(context).keep_watched()
    except SkillError as problem:
        raise ActionError(str(problem)) from None
    return f"Kept \"{skill.name}\". Run it with me {CLEAN_RUNS} times cleanly and I'll have learned it."


def _cancel_describe(context, params) -> str:
    """The approval sentence for `taught_skill.cancel`."""
    return f"Stop watching and drop \"{_shown(context)['name']}\""


def _cancel_execute(context, params) -> str:
    """Does `taught_skill.cancel`."""
    name = _shown(context)["name"]
    _book(context).stop_watching()
    return f"Dropped \"{name}\"."


def _register() -> None:
    """Adds the taught-skill kinds to ACTION_TYPES. Runs once, when this module is imported."""
    for kind in (
        ActionType("taught_skill.add", "Teach a Skill", {"name": "its name", "steps": "the steps, one a line",
                                                         "about": "what it's for (optional)",
                                                         "source": "where it came from (optional)"},
                   _add_describe, _add_execute, child_ok=False),
        ActionType("taught_skill.steps", "Change Steps", {"skill_id": "the skill", "steps": "the steps, one a line"},
                   _steps_describe, _steps_execute, child_ok=False),
        ActionType("taught_skill.delete", "Forget Skill", {"skill_id": "the skill"},
                   _delete_describe, _delete_execute, child_ok=False),
        ActionType("taught_skill.watch", "Watch Me", {"name": "what to call it"},
                   _watch_describe, _watch_execute, child_ok=False),
        ActionType("taught_skill.keep", "Keep It", {}, _keep_describe, _keep_execute, child_ok=False),
        ActionType("taught_skill.cancel", "Never Mind", {}, _cancel_describe, _cancel_execute, child_ok=False),
    ):
        ACTION_TYPES[kind.kind] = kind


_register()
