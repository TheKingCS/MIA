"""
core.workout_actions
======================

Every change the Workout screen makes (2026-10-06, DEC-0017/0018), as
action kinds on the contract in core/actions.py: exercises (add, edit,
delete) and logging a session the way the concept's form does (an
exercise, reps, sets, weight, how long, notes). Workout templates are gone
(Zac, 2026-10-16): the plan's training days are the routines you repeat
(core/fitness_manager.py). Workouts are each person's own and in
CHILD_APPS, so these are child-safe.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, field_dict, get, parse, record_form, record_kinds


def _categories():
    from core.workout_manager import EXERCISE_CATEGORIES

    return tuple(EXERCISE_CATEGORIES)


RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("exercise", "exercise", "exercise_id", "get_exercise", "add_exercise", "update_exercise", "delete_exercise",
           store="workout", delete_note="Sessions you logged with it stay in your history.", fields=(
               Field("name", "Name", "text", True),
               Field("category", "Works", "choice", options=_categories(), default="Full Body", say="works"),
               Field("equipment", "Equipment", "text"),
               Field("notes", "Notes", "textarea"),
           )),
)}

_EXERCISE = Field("exercise_id", "Exercise", "pick", options=("exercises",))
_SETS = Field("sets", "Sets", "int", default=1)
_REPS = Field("reps", "Reps", "int", default=0)
_WEIGHT = Field("weight", "Weight", "amount", default=0.0)
_MINUTES = Field("duration_minutes", "Minutes", "amount", default=0.0, say="minutes")
_DATE = Field("date", "Date", "date")
_NOTES = Field("notes", "Notes", "textarea")


def _exercise(context, exercise_id: str):
    exercise = _need(context, "workout").get_exercise(str(exercise_id or ""))
    if exercise is None:
        raise ActionError("Pick an exercise.")
    return exercise


# ------------------------------------------------------------------ logging a session


def _session(context, params) -> dict:
    exercise = _exercise(context, params.get("exercise_id"))
    sets, reps, weight = parse(_SETS, params.get("sets")), parse(_REPS, params.get("reps")), parse(_WEIGHT, params.get("weight"))
    logged = [{"exercise_id": exercise.exercise_id, "set_number": n + 1, "reps": reps, "weight": weight}
              for n in range(max(1, sets))]
    return {"exercise": exercise, "sets": sets, "reps": reps, "weight": weight, "logged": logged,
            "minutes": parse(_MINUTES, params.get("duration_minutes")), "date": parse(_DATE, params.get("date")),
            "notes": parse(_NOTES, params.get("notes"))}


def _describe_log(context, params) -> str:
    s = _session(context, params)
    what = f"{s['exercise'].name}: {max(1, s['sets'])} × {s['reps']}" + (f" at {s['weight']:g}" if s["weight"] else "")
    extra = (f", {s['minutes']:g} min" if s["minutes"] else "") + (f" on {s['date']}" if s["date"] else "")
    return f"Log a workout: {what}{extra}"


def _log(context, params) -> str:
    s = _session(context, params)
    context.workout.add_session(template_id="", date_str=s["date"], duration_minutes=s["minutes"], notes=s["notes"],
                                sets_logged=s["logged"])
    return "Workout logged. Nice work."


def _session_record(context, params):
    session = _need(context, "workout").get_session(str(params.get("session_id", "")))
    if session is None:
        raise ActionError("That session isn't there anymore.")
    return session


def _describe_session_delete(context, params) -> str:
    session = _session_record(context, params)
    return f"Remove the workout on {session.date} ({len(session.sets_logged)} sets) from your history"


def _session_delete(context, params) -> str:
    session = _session_record(context, params)
    context.workout.delete_session(session.session_id)
    return f"The workout on {session.date} is removed."


# ------------------------------------------------------------------ the kinds


def _kinds() -> list[ActionType]:
    kinds = []
    for record in RECORDS.values():
        kinds += record_kinds(record, child_ok=True)
    kinds += [
        ActionType("workout.log", "Save session", {"exercise_id": "the exercise", "sets": "", "reps": "", "weight": "",
                                                   "duration_minutes": "", "date": "", "notes": ""}, _describe_log, _log, True),
        ActionType("workout.delete", "Remove", {"session_id": "the session"}, _describe_session_delete, _session_delete, True),
    ]
    return kinds


WORKOUT_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(WORKOUT_ACTIONS)


def form_spec() -> dict:
    forms = {key: record_form(r) for key, r in RECORDS.items()}
    forms["log"] = {"noun": "session", "id_param": None,
                    "fields": [field_dict(f) for f in (_EXERCISE, _REPS, _SETS, _WEIGHT, _MINUTES, _DATE, _NOTES)]}
    return forms
