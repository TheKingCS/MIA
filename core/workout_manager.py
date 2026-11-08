"""
core.workout_manager
=======================

MIA's Workout Module — an exercise library, named workout templates,
logged sessions (sets/reps/weight, real elapsed time from a live
session's own stopwatch), personal records, and per-exercise progress.

One manager, several related record types — same shape as
core.budget_manager.py/core.kitchen_manager.py. Template exercises and
a session's logged sets are plain dicts on their parent record
(Template.exercises / WorkoutSession.sets_logged), not separate CRUD
entities or nested dataclasses — same precedent
core.kitchen_manager.Recipe.ingredients just established.

Personal records use the single most honest, universally-meaningful
metric — the heaviest weight ever logged for an exercise (ties broken
by higher reps) — never a fabricated 1RM-estimate formula (Epley/
Brzycki/etc.), same "real correct-shaped number, not fabricated
precision" boundary core.real_estate_manager.annual_depreciation()'s
own docstring draws. calories_estimate is manual entry only — no MET-
based formula exists here to compute one honestly, same "manual now,
real integration later" precedent as core.kitchen_manager.Recipe's own
nutrition fields.

A live session's set-by-set logging happens entirely in the GUI
module's own in-memory state (modules/workout/module.py) — this
manager only ever sees a session once, complete, via add_session() on
Finish. Real elapsed duration comes from the live session's own
time.monotonic()-based stopwatch, never a guess.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.gamification import SkillWeight, grant_xp
from core import life_events
from core.logger import get_logger
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_EXERCISES_FILE = _DATA_DIR / "workout_exercises.json"
_TEMPLATES_FILE = _DATA_DIR / "workout_templates.json"
_SESSIONS_FILE = _DATA_DIR / "workout_sessions.json"

EXERCISE_CATEGORIES = ["Chest", "Back", "Shoulders", "Arms", "Legs", "Core", "Cardio", "Full Body", "Other"]


@dataclass
class Exercise:
    """One exercise in the person's library: name, category (EXERCISE_CATEGORIES), equipment (free text) and notes."""
    exercise_id: str
    name: str
    category: str = "Full Body"  # one of EXERCISE_CATEGORIES
    equipment: str = ""  # freeform: "Barbell", "Dumbbell", "Bodyweight", "Machine", ...
    notes: str = ""

    def to_dict(self) -> dict:
        """The record as the plain dict saved in its JSON file."""
        return {
            "exercise_id": self.exercise_id, "name": self.name, "category": self.category,
            "equipment": self.equipment, "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict) -> "Exercise":
        """A record from its saved dict; a missing field takes its default (a missing id gets a new one), so older files load."""
        return Exercise(
            exercise_id=data.get("exercise_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            category=data.get("category", "Full Body"),
            equipment=data.get("equipment", ""),
            notes=data.get("notes", ""),
        )


@dataclass
class WorkoutTemplate:
    """A saved workout: its exercises in order, each with target sets, reps and weight."""
    template_id: str
    name: str
    notes: str = ""
    exercises: list = field(default_factory=list)  # [{"exercise_id","target_sets","target_reps","target_weight"}]

    def to_dict(self) -> dict:
        """The record as the plain dict saved in its JSON file."""
        return {
            "template_id": self.template_id, "name": self.name, "notes": self.notes,
            "exercises": self.exercises,
        }

    @staticmethod
    def from_dict(data: dict) -> "WorkoutTemplate":
        """A record from its saved dict; a missing field takes its default (a missing id gets a new one), so older files load."""
        return WorkoutTemplate(
            template_id=data.get("template_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            notes=data.get("notes", ""),
            exercises=data.get("exercises", []),
        )


@dataclass
class WorkoutSession:
    """One finished workout: the template it followed ("" for freeform), date, minutes, a calorie estimate (None when
    not entered), notes, every set logged (exercise, set number, reps, weight) and who did it (the signed-in profile;
    None counts for everyone).
    """
    session_id: str
    template_id: str = ""  # "" = freeform, no template
    date: str = ""
    duration_minutes: float = 0.0
    calories_estimate: Optional[float] = None  # None = not entered, never a fabricated zero
    notes: str = ""
    sets_logged: list = field(default_factory=list)  # [{"exercise_id","set_number","reps","weight"}]
    # Per-profile rewards (2026-09-14) — stamped automatically with
    # whoever was the active profile at add_session() time (see that
    # method below), same "credit whoever's actually active" precedent
    # core.gamification.grant_xp() already follows for XP. None only
    # for a session logged with no active profile at all (or from
    # before this field existed) — core.rewards_manager treats that as
    # shared, counting toward every profile, same as before this field
    # existed.
    profile_id: Optional[str] = None

    def to_dict(self) -> dict:
        """The record as the plain dict saved in its JSON file."""
        return {
            "session_id": self.session_id, "template_id": self.template_id, "date": self.date,
            "duration_minutes": self.duration_minutes, "calories_estimate": self.calories_estimate,
            "notes": self.notes, "sets_logged": self.sets_logged, "profile_id": self.profile_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "WorkoutSession":
        """A record from its saved dict; a missing field takes its default (a missing id gets a new one), so older files load."""
        return WorkoutSession(
            session_id=data.get("session_id", uuid.uuid4().hex[:10]),
            template_id=data.get("template_id", ""),
            date=data.get("date", ""),
            duration_minutes=data.get("duration_minutes", 0.0),
            calories_estimate=data.get("calories_estimate"),
            notes=data.get("notes", ""),
            sets_logged=data.get("sets_logged", []),
            profile_id=data.get("profile_id"),
        )


def _in_range(entry_date: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """Pure logic — testable without I/O. Same ISO-date-string-compare
    shape as every other manager's own _in_range()."""
    if start_date and entry_date < start_date:
        return False
    if end_date and entry_date > end_date:
        return False
    return True


def personal_record(exercise_id: str, sessions: list[WorkoutSession]) -> Optional[dict]:
    """Pure logic — testable without Qt. The heaviest weight ever
    logged for this exercise across all sessions (ties broken by
    higher reps) — the single most honest, universally-meaningful PR
    metric, not a fabricated 1RM-estimate formula. None when never
    logged."""
    best: Optional[dict] = None
    for session in sessions:
        for entry in session.sets_logged:
            if entry.get("exercise_id") != exercise_id:
                continue
            weight = entry.get("weight") or 0.0
            reps = entry.get("reps") or 0
            if best is None or (weight, reps) > (best["weight"], best["reps"]):
                best = {"weight": weight, "reps": reps, "date": session.date}
    return best


def weight_progression(exercise_id: str, sessions: list[WorkoutSession]) -> list[tuple[str, float]]:
    """Pure logic — testable without Qt. (date, max_weight_that_day)
    pairs across all sessions, sorted by date — Progress tab's chart
    data. A day with multiple sessions/sets for this exercise
    contributes its single heaviest set, not every set."""
    max_by_date: dict[str, float] = {}
    for session in sessions:
        for entry in session.sets_logged:
            if entry.get("exercise_id") != exercise_id:
                continue
            weight = entry.get("weight") or 0.0
            max_by_date[session.date] = max(max_by_date.get(session.date, 0.0), weight)
    return sorted(max_by_date.items())


class WorkoutManager:
    """The person's workout store: exercises, templates and finished sessions, one JSON file each in their own folder
    (data/ by default), written through atomic_write_text so undo can restore it. Finishing a session grants XP and
    records a life event; personal records and progressions are derived from the sessions, never stored.
    """
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or data/ by default.
        """Points at the person's files (data_dir, or data/ by default) and loads them."""
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._exercises_file = self.data_dir / "workout_exercises.json" if data_dir is not None else _EXERCISES_FILE
        self._templates_file = self.data_dir / "workout_templates.json" if data_dir is not None else _TEMPLATES_FILE
        self._sessions_file = self.data_dir / "workout_sessions.json" if data_dir is not None else _SESSIONS_FILE
        self.context = context
        self._exercises: list[Exercise] = []
        self._templates: list[WorkoutTemplate] = []
        self._sessions: list[WorkoutSession] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Reads all three files (undo calls this to reload)."""
        self._exercises = self._load_file(self._exercises_file, Exercise)
        self._templates = self._load_file(self._templates_file, WorkoutTemplate)
        self._sessions = self._load_file(self._sessions_file, WorkoutSession)

    def _load_file(self, path: Path, cls) -> list:
        """One file's records; missing is empty, a damaged file is logged, reported (notify_data_corruption) and starts
        empty. Sealed at rest (DEC-0126): a sealed file is opened, one that won't open is copied aside and starts empty.
        """
        if not path.exists():
            return []
        try:
            raw = json.loads(open_text(path))
            return [cls.from_dict(d) for d in raw]
        except (ValueError, OSError):  # ValueError: bad JSON or a sealed file that won't open
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            notify_data_corruption(self.context, path.name)
            return []

    def _save_file(self, path: Path, records: list) -> None:
        """Writes one file's records atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps([r.to_dict() for r in records], indent=2), encoding="utf-8")

    def _save_exercises(self) -> None:
        """Saves the exercises."""
        self._save_file(self._exercises_file, self._exercises)

    def _save_templates(self) -> None:
        """Saves the templates."""
        self._save_file(self._templates_file, self._templates)

    def _save_sessions(self) -> None:
        """Saves the sessions."""
        self._save_file(self._sessions_file, self._sessions)

    # ------------------------------------------------------------------
    # Exercise CRUD
    # ------------------------------------------------------------------

    def add_exercise(self, name: str, category: str = "Full Body", equipment: str = "", notes: str = "") -> Exercise:
        """Adds an exercise (an unknown category becomes Other)."""
        exercise = Exercise(
            exercise_id=uuid.uuid4().hex[:10],
            name=name,
            category=category if category in EXERCISE_CATEGORIES else "Other",
            equipment=equipment,
            notes=notes,
        )
        self._exercises.append(exercise)
        self._save_exercises()
        log.info("Exercise added: '%s' (%s)", exercise.name, exercise.category)
        return exercise

    def update_exercise(self, exercise_id: str, **fields) -> Exercise:
        """Changes an exercise's fields (ValueError for an unknown exercise or field)."""
        exercise = self.get_exercise(exercise_id)
        if exercise is None:
            raise ValueError(f"No exercise with id '{exercise_id}'.")
        for key, value in fields.items():
            if not hasattr(exercise, key):
                raise ValueError(f"Exercise has no field '{key}'.")
            setattr(exercise, key, value)
        if exercise.category not in EXERCISE_CATEGORIES:
            exercise.category = "Other"
        self._save_exercises()
        return exercise

    def delete_exercise(self, exercise_id: str) -> None:
        """Deletes an exercise."""
        self._exercises = [e for e in self._exercises if e.exercise_id != exercise_id]
        self._save_exercises()

    def get_exercise(self, exercise_id: str) -> Optional[Exercise]:
        """The exercise with this id, or None."""
        for exercise in self._exercises:
            if exercise.exercise_id == exercise_id:
                return exercise
        return None

    def all_exercises(self) -> list[Exercise]:
        """Every exercise, by name."""
        return sorted(self._exercises, key=lambda e: e.name.lower())

    # ------------------------------------------------------------------
    # Template CRUD
    # ------------------------------------------------------------------

    def add_template(self, name: str, notes: str = "") -> WorkoutTemplate:
        """Adds an empty workout template."""
        template = WorkoutTemplate(template_id=uuid.uuid4().hex[:10], name=name, notes=notes)
        self._templates.append(template)
        self._save_templates()
        log.info("Workout template added: '%s'", template.name)
        return template

    def update_template(self, template_id: str, **fields) -> WorkoutTemplate:
        """Changes a template's fields (ValueError for an unknown template or field)."""
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"No template with id '{template_id}'.")
        for key, value in fields.items():
            if not hasattr(template, key):
                raise ValueError(f"WorkoutTemplate has no field '{key}'.")
            setattr(template, key, value)
        self._save_templates()
        return template

    def delete_template(self, template_id: str) -> None:
        """Deletes a template."""
        self._templates = [t for t in self._templates if t.template_id != template_id]
        self._save_templates()

    def get_template(self, template_id: str) -> Optional[WorkoutTemplate]:
        """The template with this id, or None."""
        for template in self._templates:
            if template.template_id == template_id:
                return template
        return None

    def all_templates(self) -> list[WorkoutTemplate]:
        """Every template, by name."""
        return sorted(self._templates, key=lambda t: t.name.lower())

    def add_exercise_to_template(
        self, template_id: str, exercise_id: str, target_sets: int = 3, target_reps: int = 10, target_weight: float = 0.0,
    ) -> WorkoutTemplate:
        """Adds an exercise to a template with its targets (at least 1 set and 1 rep, weight never negative)."""
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"No template with id '{template_id}'.")
        template.exercises.append({
            "exercise_id": exercise_id, "target_sets": max(1, target_sets),
            "target_reps": max(1, target_reps), "target_weight": max(0.0, target_weight),
        })
        self._save_templates()
        return template

    def remove_exercise_from_template(self, template_id: str, index: int) -> WorkoutTemplate:
        """Removes a template's exercise by position (out of range changes nothing)."""
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"No template with id '{template_id}'.")
        if 0 <= index < len(template.exercises):
            template.exercises.pop(index)
            self._save_templates()
        return template

    # ------------------------------------------------------------------
    # Sessions — saved whole, once, on Finish (see module docstring)
    # ------------------------------------------------------------------

    def add_session(
        self, template_id: str = "", date_str: Optional[str] = None, duration_minutes: float = 0.0,
        calories_estimate: Optional[float] = None, notes: str = "", sets_logged: Optional[list] = None,
    ) -> WorkoutSession:
        """Records a finished workout for whoever is signed in. It's only called once, at Finish Session (the live
        session lives in memory until then), so the 10 XP toward Strength it grants can't be granted twice; it also
        records a workout_logged life event.
        """
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        session = WorkoutSession(
            session_id=uuid.uuid4().hex[:10],
            template_id=template_id,
            date=date_str or date.today().isoformat(),
            duration_minutes=max(0.0, duration_minutes),
            calories_estimate=calories_estimate,
            notes=notes,
            sets_logged=sets_logged or [],
            profile_id=active_profile.profile_id if active_profile is not None else None,
        )
        self._sessions.append(session)
        self._save_sessions()
        log.info("Workout session logged: %s (%d sets)", session.date, len(session.sets_logged))
        # 2026-09-11 gamification pass — a session is only ever added
        # once, at "Finish Session" (see this file's own docstring on
        # the live in-memory state machine), so this is a real, one-time
        # completion moment, not something that could double-grant.
        set_count = len(session.sets_logged)
        set_note = f"{set_count} set{'s' if set_count != 1 else ''} in the books." if set_count else "Session logged."
        # "My Hero's Path" (2026-09-11) — the first real proof a single
        # activity can train a Skill alongside the flat profile XP
        # above. Strength (core/skill_manager.py, data/skill_definitions
        # .json) is a broad first cut; a finer split (Calisthenics vs.
        # Endurance by session type) is real future scope, not done here.
        grant_xp(
            self.context,
            10,
            "\U0001F4AA Workout logged!",
            f"Nice work — {set_note}",
            skill_weights=[SkillWeight("strength", 10)],
        )
        template = self.get_template(template_id) if template_id else None
        life_events.record(self, "workout_logged", f"Worked out: {template.name if template else 'a session'}"
                           + (f", {session.duration_minutes:g} min" if session.duration_minutes else ""),
                           [f"workout:{session.session_id}"] + ([f"workout_template:{template_id}"] if template_id else []),
                           {"date": session.date, "minutes": session.duration_minutes, "sets": set_count})
        # Event-sourced groundwork (2026-09-14) — see
        # core/rewards_manager.py's own docstring for the full design.
        self.context.events.publish(
            "activity.logged", source="workout", category="workout_session",
            timestamp=datetime.now().isoformat(timespec="seconds"),
            duration=session.duration_minutes / 60.0, quantity=None,
            metadata={"session_id": session.session_id},
        )
        return session

    def delete_session(self, session_id: str) -> None:
        """Deletes a session."""
        self._sessions = [s for s in self._sessions if s.session_id != session_id]
        self._save_sessions()

    def get_session(self, session_id: str) -> Optional[WorkoutSession]:
        """The session with this id, or None."""
        for session in self._sessions:
            if session.session_id == session_id:
                return session
        return None

    def all_sessions(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> list[WorkoutSession]:
        """The sessions in a date range (both ends optional), newest first."""
        return sorted(
            (s for s in self._sessions if _in_range(s.date, start_date, end_date)),
            key=lambda s: s.date, reverse=True,
        )

    def last_session_date(self) -> Optional[str]:
        """The date of the latest workout, or None."""
        dates = [s.date for s in self._sessions]
        return max(dates) if dates else None

    # ------------------------------------------------------------------
    # Personal records + progress
    # ------------------------------------------------------------------

    def personal_record_for(self, exercise_id: str) -> Optional[dict]:
        """The heaviest set ever logged for an exercise (ties broken by more reps), derived from the sessions; None when
        never logged.
        """
        return personal_record(exercise_id, self._sessions)

    def weight_progression_for(self, exercise_id: str) -> list[tuple[str, float]]:
        """An exercise's heaviest weight per day, as (date, weight) by date, for the progress chart."""
        return weight_progression(exercise_id, self._sessions)
