"""
core.classroom_actions
========================

The Classroom (core/classroom_manager.py, the person's own study) through
the action contract (core/actions.py), for its web screen: a subject, a
course and a lesson added, a lesson's notes written (lesson.notes, as "add
to my notes for..." does by voice), the skill a lesson trains and its XP
(lesson.skill), a lesson marked done (its skill XP credited once,
as on the desktop) or not done, and any of them taken out. The stores write
through atomic_write_text, so "undo that" takes each back. Children study
too: all child-safe.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _name(params, what: str) -> str:
    """The name in the params, its spaces tidied; raises ActionError naming what's missing ("What's the course called?")."""
    name = " ".join(str(params.get("name") or "").split())
    if not name:
        raise ActionError(f"What's the {what} called?")
    return name[:120]


def _subject(context, params):
    """The subject the params name, from this person's Classroom; ActionError when it isn't there."""
    found = _need(context, "classroom").get_subject(str(params.get("subject_id") or ""))
    if found is None:
        raise ActionError("That subject isn't in your Classroom.")
    return found


def _course(context, params):
    """The course the params name; ActionError when it isn't there."""
    found = _need(context, "classroom").get_course(str(params.get("course_id") or ""))
    if found is None:
        raise ActionError("That course isn't in your Classroom.")
    return found


def _lesson(context, params):
    """The lesson the params name; ActionError when it isn't there."""
    found = _need(context, "classroom").get_lesson(str(params.get("lesson_id") or ""))
    if found is None:
        raise ActionError("That lesson isn't in your Classroom.")
    return found


def _subject_add(context, params) -> str:
    """subject.add: a new subject, with an optional category."""
    made = _need(context, "classroom").add_subject(_name(params, "subject"), str(params.get("category") or ""))
    return f"Added the subject {made.name}."


def _course_add(context, params) -> str:
    """course.add: a new course in a subject."""
    subject = _subject(context, params)
    made = _need(context, "classroom").add_course(subject.subject_id, _name(params, "course"))
    return f"Added {made.name} to {subject.name}."


def _lesson_add(context, params) -> str:
    """lesson.add: a new lesson in a course."""
    course = _course(context, params)
    made = _need(context, "classroom").add_lesson(course.course_id, _name(params, "lesson"))
    return f"Added the lesson {made.name} to {course.name}."


def _lesson_done(context, params) -> str:
    """lesson.done: tick a lesson done ("done": yes) or not done (no). Going to done credits its skill XP once,
    in ClassroomManager.update_lesson, exactly as the desktop does.
    """
    lesson = _lesson(context, params)
    done = str(params.get("done", "yes")).lower() not in ("no", "false", "0")
    _need(context, "classroom").update_lesson(lesson.lesson_id, completed=done)
    return f"{lesson.name}: done." if done else f"{lesson.name}: not done yet."


def _lesson_notes(context, params) -> str:
    """lesson.notes: a lesson's notes replaced with the text given (the screen edits the whole note; empty clears it)."""
    lesson = _lesson(context, params)
    text = str(params.get("notes") or "").strip()
    _need(context, "classroom").update_lesson(lesson.lesson_id, notes=text)
    return f"Saved your notes for {lesson.name}." if text else f"Cleared your notes for {lesson.name}."


def _skill_choice(context, params):
    """(the lesson, the skill it will train or None, the XP) from the params; ActionError for a skill that isn't one,
    or XP outside 1 to 100 (the desktop's lesson dialog has the same range)."""
    lesson = _lesson(context, params)
    skill_id = str(params.get("skill_id") or "").strip()
    if not skill_id:
        return lesson, None, 0
    skills = getattr(context, "skills", None)
    skill = skills.get_skill(skill_id) if skills is not None else None
    if skill is None:
        raise ActionError("That skill isn't one of yours.")
    try:
        xp = int(str(params.get("xp") or "10").strip())
    except ValueError:
        raise ActionError("XP has to be a whole number.") from None
    if not 1 <= xp <= 100:
        raise ActionError("XP: pick from 1 to 100.")
    return lesson, skill, xp


def _describe_lesson_skill(context, params) -> str:
    """The approval sentence for lesson.skill."""
    lesson, skill, xp = _skill_choice(context, params)
    return f"{lesson.name} trains {skill.name}, {xp} XP when it's done" if skill else f"{lesson.name} trains no skill"


def _lesson_skill(context, params) -> str:
    """lesson.skill: the one skill a lesson trains and its XP (credited once, when the lesson is first done), or
    none. A lesson already credited keeps what it gave."""
    from core.gamification import SkillWeight

    lesson, skill, xp = _skill_choice(context, params)
    rewards = [SkillWeight(skill.skill_id, xp)] if skill else []
    _need(context, "classroom").update_lesson(lesson.lesson_id, skill_rewards=rewards)
    return f"{lesson.name} trains {skill.name} now." if skill else f"{lesson.name} trains no skill now."


def _delete(kind: str, finder, remover):
    """Make the execute function for subject.delete, course.delete or lesson.delete: find the record with `finder`
    and remove it with the manager's `remover` method (deleting a subject or course takes what's under it too).
    """
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
    ActionType("lesson.notes", "Save the notes", {"lesson_id": "the lesson", "notes": "what you learned"},
               lambda c, p: f"Save your notes for {_lesson(c, p).name}", _lesson_notes, child_ok=True),
    ActionType("lesson.skill", "Trains", {"lesson_id": "the lesson", "skill_id": "a skill (blank for none)",
                                          "xp": "1 to 100"}, _describe_lesson_skill, _lesson_skill, child_ok=True),
    ActionType("lesson.delete", "Take it out", {"lesson_id": "the lesson"},
               lambda c, p: f"Take the lesson {_lesson(c, p).name} out",
               _delete("lesson", _lesson, "delete_lesson"), child_ok=True),
)}
ACTION_TYPES.update(CLASSROOM_ACTIONS)
