"""
core.classroom_actions
========================

The Classroom (core/classroom_manager.py, the person's own study) through
the action contract (core/actions.py), for its web screen: a subject, a
course and a lesson added, a lesson marked done (its skill XP credited once,
as on the desktop) or not done, and any of them taken out. The stores write
through atomic_write_text, so "undo that" takes each back. Children study
too: all child-safe.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _name(params, what: str) -> str:
    name = " ".join(str(params.get("name") or "").split())
    if not name:
        raise ActionError(f"What's the {what} called?")
    return name[:120]


def _subject(context, params):
    found = _need(context, "classroom").get_subject(str(params.get("subject_id") or ""))
    if found is None:
        raise ActionError("That subject isn't in your Classroom.")
    return found


def _course(context, params):
    found = _need(context, "classroom").get_course(str(params.get("course_id") or ""))
    if found is None:
        raise ActionError("That course isn't in your Classroom.")
    return found


def _lesson(context, params):
    found = _need(context, "classroom").get_lesson(str(params.get("lesson_id") or ""))
    if found is None:
        raise ActionError("That lesson isn't in your Classroom.")
    return found


def _subject_add(context, params) -> str:
    made = _need(context, "classroom").add_subject(_name(params, "subject"), str(params.get("category") or ""))
    return f"Added the subject {made.name}."


def _course_add(context, params) -> str:
    subject = _subject(context, params)
    made = _need(context, "classroom").add_course(subject.subject_id, _name(params, "course"))
    return f"Added {made.name} to {subject.name}."


def _lesson_add(context, params) -> str:
    course = _course(context, params)
    made = _need(context, "classroom").add_lesson(course.course_id, _name(params, "lesson"))
    return f"Added the lesson {made.name} to {course.name}."


def _lesson_done(context, params) -> str:
    lesson = _lesson(context, params)
    done = str(params.get("done", "yes")).lower() not in ("no", "false", "0")
    _need(context, "classroom").update_lesson(lesson.lesson_id, completed=done)
    return f"{lesson.name}: done." if done else f"{lesson.name}: not done yet."


def _delete(kind: str, finder, remover):
    def run(context, params) -> str:
        found = finder(context, params)
        getattr(_need(context, "classroom"), remover)(getattr(found, f"{kind}_id"))
        return f"Took {found.name} out."
    return run


CLASSROOM_ACTIONS = {a.kind: a for a in (
    ActionType("subject.add", "Add a subject", {"name": "what you're studying", "category": "a kind (optional)"},
               lambda c, p: f"Add the subject {_name(p, 'subject')}", _subject_add, child_ok=True),
    ActionType("subject.delete", "Take it out", {"subject_id": "the subject"},
               lambda c, p: f"Take {_subject(c, p).name} out, with its courses and lessons",
               _delete("subject", _subject, "delete_subject"), child_ok=True),
    ActionType("course.add", "Add a course", {"subject_id": "the subject", "name": "the course"},
               lambda c, p: f"Add {_name(p, 'course')} to {_subject(c, p).name}", _course_add, child_ok=True),
    ActionType("course.delete", "Take it out", {"course_id": "the course"},
               lambda c, p: f"Take {_course(c, p).name} out, with its lessons",
               _delete("course", _course, "delete_course"), child_ok=True),
    ActionType("lesson.add", "Add a lesson", {"course_id": "the course", "name": "the lesson"},
               lambda c, p: f"Add the lesson {_name(p, 'lesson')} to {_course(c, p).name}", _lesson_add, child_ok=True),
    ActionType("lesson.done", "Done", {"lesson_id": "the lesson", "done": "yes or no"},
               lambda c, p: f"Mark {_lesson(c, p).name} " + ("not done" if str(p.get("done", "yes")).lower() in
                                                             ("no", "false", "0") else "done"),
               _lesson_done, child_ok=True),
    ActionType("lesson.delete", "Take it out", {"lesson_id": "the lesson"},
               lambda c, p: f"Take the lesson {_lesson(c, p).name} out",
               _delete("lesson", _lesson, "delete_lesson"), child_ok=True),
)}
ACTION_TYPES.update(CLASSROOM_ACTIONS)
