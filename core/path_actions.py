"""
core.path_actions
===================

Learning paths on the action contract (DEC-0112, core/paths.py): proposed in
plain words, approved, run, undoable.

- `path.draft`: draft a learning path for an interest (the Universal Action
  Layer's "Learn This Myself", DEC-0165 U3). An interest a program already
  covers is named, not drafted again. A draft is only a plan: nothing starts
  until the person says "start it" (core/assistant_path_actions.py) or starts
  it on the Learning page.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _interest(params) -> str:
    """The interest in the params, in a few words, or ActionError."""
    interest = " ".join(str(params.get("interest") or "").split())[:120]
    if not interest:
        raise ActionError("What would you like to learn?")
    return interest


def _draft_describe(context, params) -> str:
    """The approval sentence for `path.draft`: the plan already there, or that one will be drafted."""
    from core import paths

    _need(context, "paths")
    interest = _interest(params)
    found = paths.find_program(context, interest)
    if found is not None:
        return f"Show the learning path for {found.name} (it's already here; nothing starts until you say so)"
    return f"Draft a learning path for “{interest}” (a plan MIA writes; nothing starts until you say so)"


def _draft_execute(context, params) -> str:
    """Does `path.draft`: names the program already there, or drafts and keeps one; says how to start it."""
    from core import paths

    interest = _interest(params)
    program = paths.find_program(context, interest)
    if program is None:
        try:
            program = paths.draft(context, interest, str(params.get("goal") or ""))
        except ValueError as problem:
            raise ActionError(str(problem)) from None
    return paths.describe_program(program) + " Say \"start it\" to begin, or open it in Learning."


def _register() -> None:
    """Adds the path kinds to ACTION_TYPES. Runs once, when this module is imported."""
    ACTION_TYPES["path.draft"] = ActionType("path.draft", "Draft A Learning Path",
                                            {"interest": "what to learn", "goal": "why, in their words (optional)"},
                                            _draft_describe, _draft_execute)


_register()
