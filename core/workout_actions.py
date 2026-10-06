"""
core.workout_actions
======================

Every change the Workout screen makes (2026-10-06, DEC-0017/0018), as
action kinds on the contract in core/actions.py: exercises and templates
(add, edit, delete), a template's exercises (add one, remove one), and
logging a session the way the concept's form does (an exercise, reps,
sets, weight, how long, notes; or a whole template). Workouts are each
person's own and in CHILD_APPS, so these are child-safe.
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
    Record("workout_template", "template", "template_id", "get_template", "add_template", "update_template",
           "delete_template", store="workout", fields=(
               Field("name", "Name", "text", True),
               Field("notes", "Notes", "textarea"),
           )),
)}

_EXERCISE = Field("exercise_id", "Exercise", "pick", options=("exercises",))
_TEMPLATE = Field("template_id", "Template", "pick", options=("templates",))
_SETS = Field("sets", "Sets", "int", default=1)
_REPS = Field("reps", "Reps", "int", default=0)
_WEIGHT = Field("weight", "Weight", "amount", default=0.0)
_MINUTES = Field("duration_minutes", "Minutes", "amount", default=0.0, say="minutes")
_DATE = Field("date", "Date", "date")
_NOTES = Field("notes", "Notes", "textarea")
_TARGET_SETS = Field("target_sets", "Sets", "int", default=3)
_TARGET_REPS = Field("target_reps", "Reps", "int", default=10)
_TARGET_WEIGHT = Field("target_weight", "Weight", "amount", default=0.0)


def _exercise(context, exercise_id: str):
    exercise = _need(context, "workout").get_exercise(str(exercise_id or ""))
    if exercise is None:
        raise ActionError("Pick an exercise.")
    return exercise


def _template(context, template_id: str, needed: bool = False):
    if not template_id:
        if needed:
            raise ActionError("That template isn't there anymore.")
        return None
    template = _need(context, "workout").get_template(str(template_id))
    if template is None:
        raise ActionError("That template isn't there anymore.")
    return template


# ------------------------------------------------------------------ logging a session


def _session(context, params) -> dict:
    template = _template(context, params.get("template_id"))
    exercise = _exercise(context, params.get("exercise_id")) if params.get("exercise_id") else None
    if exercise is None and template is None:
        raise ActionError("Pick an exercise or a template.")
    sets, reps, weight = parse(_SETS, params.get("sets")), parse(_REPS, params.get("reps")), parse(_WEIGHT, params.get("weight"))
    logged = []
    if exercise is not None:
        logged = [{"exercise_id": exercise.exercise_id, "set_number": n + 1, "reps": reps, "weight": weight}
                  for n in range(max(1, sets))]
    elif template is not None:
        for item in template.exercises:
            for n in range(int(item.get("target_sets") or 1)):
                logged.append({"exercise_id": item.get("exercise_id"), "set_number": n + 1,
                               "reps": item.get("target_reps") or 0, "weight": item.get("target_weight") or 0})
    return {"template": template, "exercise": exercise, "sets": sets, "reps": reps, "weight": weight, "logged": logged,
            "minutes": parse(_MINUTES, params.get("duration_minutes")), "date": parse(_DATE, params.get("date")),
            "notes": parse(_NOTES, params.get("notes"))}


def _describe_log(context, params) -> str:
    s = _session(context, params)
    if s["exercise"] is not None:
        what = f"{s['exercise'].name}: {max(1, s['sets'])} × {s['reps']}" + (f" at {s['weight']:g}" if s["weight"] else "")
    else:
        what = f"{s['template'].name} ({len(s['logged'])} sets)"
    extra = (f", {s['minutes']:g} min" if s["minutes"] else "") + (f" on {s['date']}" if s["date"] else "")
    return f"Log a workout: {what}{extra}"


def _log(context, params) -> str:
    s = _session(context, params)
    context.workout.add_session(template_id=s["template"].template_id if s["template"] else "", date_str=s["date"],
                                duration_minutes=s["minutes"], notes=s["notes"], sets_logged=s["logged"])
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


# ------------------------------------------------------------------ a template's exercises


def _describe_template_add(context, params) -> str:
    template = _template(context, params.get("template_id"), needed=True)
    exercise = _exercise(context, params.get("exercise_id"))
    sets, reps = parse(_TARGET_SETS, params.get("target_sets")), parse(_TARGET_REPS, params.get("target_reps"))
    weight = parse(_TARGET_WEIGHT, params.get("target_weight"))
    return f"Add {exercise.name} to {template.name}: {sets} × {reps}" + (f" at {weight:g}" if weight else "")


def _template_add(context, params) -> str:
    template = _template(context, params.get("template_id"), needed=True)
    exercise = _exercise(context, params.get("exercise_id"))
    context.workout.add_exercise_to_template(template.template_id, exercise.exercise_id,
                                             parse(_TARGET_SETS, params.get("target_sets")),
                                             parse(_TARGET_REPS, params.get("target_reps")),
                                             parse(_TARGET_WEIGHT, params.get("target_weight")))
    return f"{exercise.name} is in {template.name}."


def _template_item(context, params):
    template = _template(context, params.get("template_id"), needed=True)
    try:
        index = int(params.get("index"))
        item = template.exercises[index]
    except (TypeError, ValueError, IndexError):
        raise ActionError("That exercise isn't in the template anymore.") from None
    exercise = context.workout.get_exercise(item.get("exercise_id"))
    return template, index, exercise.name if exercise else "that exercise"


def _describe_template_remove(context, params) -> str:
    template, _index, name = _template_item(context, params)
    return f"Take {name} out of {template.name}"


def _template_remove(context, params) -> str:
    template, index, name = _template_item(context, params)
    context.workout.remove_exercise_from_template(template.template_id, index)
    return f"{name} is out of {template.name}."


# ------------------------------------------------------------------ the kinds


def _kinds() -> list[ActionType]:
    kinds = []
    for record in RECORDS.values():
        kinds += record_kinds(record, child_ok=True)
    kinds += [
        ActionType("workout.log", "Save session", {"exercise_id": "an exercise, or", "template_id": "a template",
                                                   "sets": "", "reps": "", "weight": "", "duration_minutes": "",
                                                   "date": "", "notes": ""}, _describe_log, _log, True),
        ActionType("workout.delete", "Remove", {"session_id": "the session"}, _describe_session_delete, _session_delete, True),
        ActionType("workout_template.exercise_add", "Add exercise", {"template_id": "", "exercise_id": "", "target_sets": "",
                                                                     "target_reps": "", "target_weight": ""},
                   _describe_template_add, _template_add, True),
        ActionType("workout_template.exercise_remove", "Remove", {"template_id": "", "index": ""},
                   _describe_template_remove, _template_remove, True),
    ]
    return kinds


WORKOUT_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(WORKOUT_ACTIONS)


def form_spec() -> dict:
    forms = {key: record_form(r) for key, r in RECORDS.items()}
    forms["log"] = {"noun": "session", "id_param": None,
                    "fields": [field_dict(f) for f in (_EXERCISE, _REPS, _SETS, _WEIGHT, _MINUTES, _DATE, _NOTES)]}
    forms["log_template"] = {"noun": "session", "id_param": None,
                             "fields": [field_dict(f) for f in (_TEMPLATE, _MINUTES, _DATE, _NOTES)]}
    forms["template_exercise"] = {"noun": "exercise", "id_param": "template_id",
                                  "fields": [field_dict(f) for f in (_EXERCISE, _TARGET_SETS, _TARGET_REPS, _TARGET_WEIGHT)]}
    return forms
