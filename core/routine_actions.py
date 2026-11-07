"""
core.routine_actions
======================

The Household's routines changed from the screen (DEC-0113 canvas
Household, DEC-0125: routines could only be added by voice). `routine.add`
sets one up (core/household_routines.add_routine, the same as the
add_household_routine voice tool); `routine.pause` stops it making new
missions while keeping its history; `routine.resume` picks it back up.
Logging one stays `routine.log` (core/actions.py). Each is undoable: the
routines store writes through atomic_write.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

ROUTINE_FIELDS = [
    {"name": "name", "label": "What it is (Dishes, Trash to the road...)", "type": "text", "required": True,
     "options": [], "default": None},
    {"name": "times", "label": "How many times", "type": "number", "required": False, "options": [], "default": 1},
    {"name": "every", "label": "Every", "type": "choice", "required": False, "options": ["day", "week"], "default": "day"},
]


def _times(params) -> float:
    """How many times, 1 when left blank; ActionError for anything that isn't a number of at least one."""
    raw = str(params.get("times") or "1").strip()
    try:
        times = float(raw)
    except ValueError:
        raise ActionError("How many times? Give a number.") from None
    if times < 1:
        raise ActionError("At least once.")
    return times


def _every(params) -> str:
    """"week" or "day"."""
    return "week" if str(params.get("every") or "").lower().startswith("week") else "day"


def _describe_add(context, params) -> str:
    """The sentence the approval card shows for `routine.add`; ActionError when it can't be done."""
    book = _need(context, "recurring_missions")
    name = str(params.get("name") or "").strip()
    if not name:
        raise ActionError("What's the routine called?")
    if any(t.category == "Household" and t.active and t.name.lower() == name.lower() for t in book.all_templates()):
        raise ActionError(f"You already have a {name} routine.")
    times = _times(params)
    return f"Add {name}: {times:g} time{'s' if times != 1 else ''} a {_every(params)}"


def _add(context, params) -> str:
    """Does `routine.add` once approved."""
    from core.household_routines import add_routine

    try:
        t = add_routine(context, params.get("name"), _times(params), _every(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"Added {t.name}. I'll track your streak."


def _routine(context, params):
    """The household routine named by template_id, or ActionError."""
    t = _need(context, "recurring_missions").get_template(str(params.get("template_id") or ""))
    if t is None or t.category != "Household":
        raise ActionError("That routine isn't here any more.")
    return t


def _switch(active: bool):
    """The execute for pause (False) or resume (True)."""
    def run(context, params) -> str:
        """Pauses or resumes the routine."""
        t = _routine(context, params)
        context.recurring_missions.set_active(t.template_id, active)
        return f"{t.name} is {'back on' if active else 'paused'}."
    return run


_KINDS = [
    ActionType("routine.add", "Add Routine", {"name": "what it is", "times": "how many times", "every": "day or week"},
               _describe_add, _add),
    ActionType("routine.pause", "Pause", {"template_id": "the routine"},
               lambda c, p: f"Pause {_routine(c, p).name} (its streak and history are kept)", _switch(False)),
    ActionType("routine.resume", "Resume", {"template_id": "the routine"},
               lambda c, p: f"Start {_routine(c, p).name} again", _switch(True)),
]
ROUTINE_ACTIONS = {k.kind: k for k in _KINDS}
ACTION_TYPES.update(ROUTINE_ACTIONS)
