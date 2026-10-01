"""
core.classroom_manager
==========================

Classroom (2026-09-11) — the user's own self-education content model:
Subjects (K-12-level academic subjects and trades) contain Courses,
Courses contain Lessons. v1 is deliberately just this content/lesson
structure — no Skills/Missions/Discovery wiring yet, see this module's
own ROADMAP entry for why. Starts empty, like every other personal-
content module in this codebase (Kitchen, Workout, Projects) — no
pre-seeded universal curriculum ships with it, unlike Mission
Pathways/Skill definitions (hand-authored content files); this is the
user's own real courses/lessons, not a fixed taxonomy.

One manager, three related record types, same shape as
core.workout_manager.py (Exercise/Template/Session, one file per type).

Cascading delete, not unlink: a Lesson doesn't independently make sense
without its Course, same reasoning core.mission_manager.Mission's own
Objectives are deleted along with their parent Mission (not the
Project/Task unlink precedent, where a standalone Task is still
meaningful on its own).

Completion is derived, never stored twice: course_completion()/
subject_completion() compute (done, total) fresh from real Lesson
records every time, same "derive it, don't persist a second copy that
can drift" philosophy as every level/unlock computation elsewhere in
this codebase.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.gamification import SkillWeight, grant_xp
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SUBJECTS_FILE = _DATA_DIR / "classroom_subjects.json"
_COURSES_FILE = _DATA_DIR / "classroom_courses.json"
_LESSONS_FILE = _DATA_DIR / "classroom_lessons.json"


@dataclass
class Subject:
    subject_id: str
    name: str
    category: str = ""  # freeform, e.g. "Mathematics", "Trade Skills"
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Subject":
        return Subject(
            subject_id=data.get("subject_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class Course:
    course_id: str
    subject_id: str
    name: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id,
            "subject_id": self.subject_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Course":
        return Course(
            course_id=data.get("course_id", uuid.uuid4().hex[:10]),
            subject_id=data.get("subject_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class Lesson:
    lesson_id: str
    course_id: str
    name: str
    notes: str = ""  # freeform content/summary/materials
    completed: bool = False
    completed_at: str = ""  # set once, on the real False -> True transition
    # "Wire Classroom into Hero's Path" (2026-09-12) — optional Skill XP
    # a completed Lesson also grants, credited via the shared
    # core.gamification.grant_xp() helper (same path Kitchen/Workout/
    # Maintenance/Budget already use for "a completed real action, not
    # a Mission"). skill_rewards_credited guards against re-granting on
    # a later Complete->Incomplete->Complete cycle — same exploit class,
    # same fix shape, as core.project_manager.Project.skill_weights_credited.
    skill_rewards: list[SkillWeight] = field(default_factory=list)
    skill_rewards_credited: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "lesson_id": self.lesson_id,
            "course_id": self.course_id,
            "name": self.name,
            "notes": self.notes,
            "completed": self.completed,
            "completed_at": self.completed_at,
            "skill_rewards": [{"skill_id": w.skill_id, "xp": w.xp} for w in self.skill_rewards],
            "skill_rewards_credited": self.skill_rewards_credited,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Lesson":
        return Lesson(
            lesson_id=data.get("lesson_id", uuid.uuid4().hex[:10]),
            course_id=data.get("course_id", ""),
            name=data.get("name", ""),
            notes=data.get("notes", ""),
            completed=bool(data.get("completed", False)),
            completed_at=data.get("completed_at", ""),
            skill_rewards=[
                SkillWeight(skill_id=d["skill_id"], xp=d["xp"]) for d in data.get("skill_rewards", [])
            ],
            skill_rewards_credited=bool(data.get("skill_rewards_credited", False)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ClassroomManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._subjects_file = self.data_dir / "classroom_subjects.json" if data_dir is not None else _SUBJECTS_FILE
        self._courses_file = self.data_dir / "classroom_courses.json" if data_dir is not None else _COURSES_FILE
        self._lessons_file = self.data_dir / "classroom_lessons.json" if data_dir is not None else _LESSONS_FILE
        self.context = context
        self._subjects: list[Subject] = []
        self._courses: list[Course] = []
        self._lessons: list[Lesson] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._subjects = self._load_file(self._subjects_file, Subject.from_dict)
        self._courses = self._load_file(self._courses_file, Course.from_dict)
        self._lessons = self._load_file(self._lessons_file, Lesson.from_dict)

    def _load_file(self, path: Path, from_dict) -> list:
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            notify_data_corruption(self.context, path.name)
            return []

    def _save_subjects(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._subjects_file, json.dumps([s.to_dict() for s in self._subjects], indent=2), encoding="utf-8")

    def _save_courses(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._courses_file, json.dumps([c.to_dict() for c in self._courses], indent=2), encoding="utf-8")

    def _save_lessons(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._lessons_file, json.dumps([l.to_dict() for l in self._lessons], indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Subjects
    # ------------------------------------------------------------------

    def add_subject(self, name: str, category: str = "", description: str = "") -> Subject:
        now = datetime.now().isoformat(timespec="seconds")
        subject = Subject(
            subject_id=uuid.uuid4().hex[:10], name=name, category=category,
            description=description, created_at=now, updated_at=now,
        )
        self._subjects.append(subject)
        self._save_subjects()
        return subject

    def update_subject(self, subject_id: str, **fields) -> Subject:
        subject = self.get_subject(subject_id)
        if subject is None:
            raise ValueError(f"No subject with id '{subject_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_subject().")
            if not hasattr(subject, key):
                raise ValueError(f"Subject has no field '{key}'.")
            setattr(subject, key, value)
        subject.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save_subjects()
        return subject

    def delete_subject(self, subject_id: str) -> None:
        """Cascades: removes every Course under this Subject, and every
        Lesson under each of those Courses — see module docstring for
        why this is a cascade, not an unlink."""
        course_ids = [c.course_id for c in self._courses if c.subject_id == subject_id]
        self._lessons = [l for l in self._lessons if l.course_id not in course_ids]
        self._courses = [c for c in self._courses if c.subject_id != subject_id]
        self._subjects = [s for s in self._subjects if s.subject_id != subject_id]
        self._save_lessons()
        self._save_courses()
        self._save_subjects()

    def get_subject(self, subject_id: str) -> Optional[Subject]:
        for subject in self._subjects:
            if subject.subject_id == subject_id:
                return subject
        return None

    def all_subjects(self) -> list[Subject]:
        return sorted(self._subjects, key=lambda s: s.name.lower())

    # ------------------------------------------------------------------
    # Courses
    # ------------------------------------------------------------------

    def add_course(self, subject_id: str, name: str, description: str = "") -> Course:
        now = datetime.now().isoformat(timespec="seconds")
        course = Course(
            course_id=uuid.uuid4().hex[:10], subject_id=subject_id, name=name,
            description=description, created_at=now, updated_at=now,
        )
        self._courses.append(course)
        self._save_courses()
        return course

    def update_course(self, course_id: str, **fields) -> Course:
        course = self.get_course(course_id)
        if course is None:
            raise ValueError(f"No course with id '{course_id}'.")
        for key, value in fields.items():
            if key in ("created_at", "subject_id"):
                raise ValueError(f"'{key}' can't be set through update_course().")
            if not hasattr(course, key):
                raise ValueError(f"Course has no field '{key}'.")
            setattr(course, key, value)
        course.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save_courses()
        return course

    def delete_course(self, course_id: str) -> None:
        """Cascades: removes every Lesson under this Course."""
        self._lessons = [l for l in self._lessons if l.course_id != course_id]
        self._courses = [c for c in self._courses if c.course_id != course_id]
        self._save_lessons()
        self._save_courses()

    def get_course(self, course_id: str) -> Optional[Course]:
        for course in self._courses:
            if course.course_id == course_id:
                return course
        return None

    def courses_for_subject(self, subject_id: str) -> list[Course]:
        return sorted(
            (c for c in self._courses if c.subject_id == subject_id),
            key=lambda c: c.name.lower(),
        )

    # ------------------------------------------------------------------
    # Lessons
    # ------------------------------------------------------------------

    def add_lesson(
        self, course_id: str, name: str, notes: str = "", skill_rewards: Optional[list[SkillWeight]] = None,
    ) -> Lesson:
        now = datetime.now().isoformat(timespec="seconds")
        lesson = Lesson(
            lesson_id=uuid.uuid4().hex[:10], course_id=course_id, name=name,
            notes=notes, skill_rewards=list(skill_rewards) if skill_rewards else [],
            created_at=now, updated_at=now,
        )
        self._lessons.append(lesson)
        self._save_lessons()
        return lesson

    def update_lesson(self, lesson_id: str, **fields) -> Lesson:
        lesson = self.get_lesson(lesson_id)
        if lesson is None:
            raise ValueError(f"No lesson with id '{lesson_id}'.")
        was_completed = lesson.completed
        for key, value in fields.items():
            if key in ("created_at", "course_id", "completed_at", "skill_rewards_credited"):
                raise ValueError(f"'{key}' can't be set through update_lesson().")
            if not hasattr(lesson, key):
                raise ValueError(f"Lesson has no field '{key}'.")
            setattr(lesson, key, value)
        lesson.updated_at = datetime.now().isoformat(timespec="seconds")
        if not was_completed and lesson.completed:
            lesson.completed_at = lesson.updated_at
            # "Wire Classroom into Hero's Path" (2026-09-12) — credits
            # only on this real transition, guarded by
            # skill_rewards_credited so a later Complete->Incomplete->
            # Complete cycle can never re-grant the same XP (same
            # exploit class core.project_manager.Project.skill_weights_credited
            # was added to close). 0 flat profile XP — that stays
            # Mission-exclusive, same boundary
            # Project._credit_project_skill_weights() already draws.
            if lesson.skill_rewards and not lesson.skill_rewards_credited:
                grant_xp(
                    self.context, 0, "\U0001F393 Lesson complete!",
                    f"'{lesson.name}' is complete!", skill_weights=lesson.skill_rewards,
                )
                lesson.skill_rewards_credited = True
        self._save_lessons()
        return lesson

    def delete_lesson(self, lesson_id: str) -> None:
        self._lessons = [l for l in self._lessons if l.lesson_id != lesson_id]
        self._save_lessons()

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        for lesson in self._lessons:
            if lesson.lesson_id == lesson_id:
                return lesson
        return None

    def lessons_for_course(self, course_id: str) -> list[Lesson]:
        return sorted(
            (l for l in self._lessons if l.course_id == course_id),
            key=lambda l: l.created_at,
        )

    # ------------------------------------------------------------------
    # Derived completion — never stored, always computed fresh
    # ------------------------------------------------------------------

    def course_completion(self, course_id: str) -> tuple[int, int]:
        lessons = self.lessons_for_course(course_id)
        return sum(1 for l in lessons if l.completed), len(lessons)

    def subject_completion(self, subject_id: str) -> tuple[int, int]:
        done = 0
        total = 0
        for course in self.courses_for_subject(subject_id):
            course_done, course_total = self.course_completion(course.course_id)
            done += course_done
            total += course_total
        return done, total
