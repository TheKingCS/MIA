"""
core.assistant_life_actions
=============================

Assistant actions for the personal side of MIA (2026-09-27, following
docs/ASSISTANT_AUDIT.md): workouts, people and pets, household
routines, and Classroom learning. Same contract as
core/assistant_domain_actions.py: handlers are pure functions of
(context, arguments), find records from the user's own words via
core.assistant_lookup, never delete, and return one sentence to speak.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_domain_actions import _as_list, _list, _n, _num, _obj, _s
from core.assistant_lookup import resolve_by_name

_NO_PARAMS = {"type": "object", "properties": {}, "required": []}
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
# Birthdays are used by month/day only (reminders, "days until"); a
# spoken birthday usually has no year, so a leap year stands in and is
# never read back.
_NO_YEAR = 2000


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def parse_birthday(text: str) -> Optional[str]:
    """Pure logic. "1990-03-03", "March 3", "march 3rd 1990", "3/3",
    "3/3/1990" -> ISO date (year 2000 when none given); None if unparseable."""
    t = str(text or "").strip().lower().replace(",", " ")
    if not t:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", t)
        if m:
            mo, d = int(m.group(1)), int(m.group(2))
            y = int(m.group(3)) if m.group(3) else _NO_YEAR
            if y < 100:
                y += 1900 if y > 30 else 2000
        else:
            m = re.fullmatch(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?", t)
            if not m or m.group(1) not in _MONTHS:
                return None
            mo, d = _MONTHS[m.group(1)], int(m.group(2))
            y = int(m.group(3)) if m.group(3) else _NO_YEAR
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def speak_birthday(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d.strftime('%B')} {d.day}" + ("" if d.year == _NO_YEAR else f", {d.year}")


def days_until(iso: str, today: date) -> Optional[int]:
    try:
        b = date.fromisoformat(iso)
    except ValueError:
        return None
    for year in (today.year, today.year + 1):
        try:
            nxt = b.replace(year=year)
        except ValueError:  # Feb 29 in a non-leap year
            nxt = date(year, 3, 1)
        if nxt >= today:
            return (nxt - today).days
    return None


_SETS_REPS = re.compile(r"(\d+)\s*(?:x|sets? of)\s*(\d+)(?:\s*reps?)?", re.I)
_WEIGHT = re.compile(r"(?:at|@|with)\s*(\d+(?:\.\d+)?)\s*(lbs?|pounds?|kg|kgs)?", re.I)
_REPS_ONLY = re.compile(r"^(\d+)\s+(?!x\b)", re.I)


def parse_exercise_line(line: str) -> dict:
    """Pure logic. "3x10 squats at 185" / "squats 3 sets of 10 @ 185 lbs"
    -> {"name": "squats", "sets": 3, "reps": 10, "weight": 185.0};
    "20 push-ups" -> 1 set of 20; anything without sets or reps (e.g.
    "ran 3 miles") -> {"name": line, "sets": 0, ...}, kept as a note."""
    text = str(line).strip()
    sets = reps = 0
    weight = 0.0
    m = _SETS_REPS.search(text)
    if m:
        sets, reps = int(m.group(1)), int(m.group(2))
        text = (text[: m.start()] + " " + text[m.end():]).strip()
    w = _WEIGHT.search(text)
    if w:
        weight = float(w.group(1))
        text = (text[: w.start()] + " " + text[w.end():]).strip()
    if not sets:
        r = _REPS_ONLY.match(text)
        if r:
            sets, reps = 1, int(r.group(1))
            text = text[r.end():].strip()
    name = re.sub(r"\s+", " ", text).strip(" ,.-")
    return {"name": name or str(line).strip(), "sets": sets, "reps": reps, "weight": weight}


def _append_line(existing: str, text: str, dated: bool = False) -> str:
    line = f"{date.today().isoformat()}: {text}" if dated else text
    return f"{existing.rstrip()}\n{line}" if existing.strip() else line


# ---------------------------------------------------------------------------
# Workout
# ---------------------------------------------------------------------------


def _find_or_create_exercise(context: AppContext, name: str):
    exercises = context.workout.all_exercises()
    exercise, _ = resolve_by_name(exercises, name, lambda e: e.name, "exercise")
    if exercise is not None:
        return exercise, False
    return context.workout.add_exercise(name=name.strip().title()), True


def _action_log_workout(context: AppContext, arguments: dict) -> str:
    lines = _as_list(arguments.get("exercises"))
    duration = _num(arguments.get("duration_minutes"), 0.0) or 0.0
    notes = [str(arguments.get("notes", "") or "").strip()]
    if not lines and not duration and not notes[0]:
        return "What did you do? Tell me the exercises, like '3 sets of 10 squats at 185'."
    sets_logged, created, done = [], [], []
    for line in lines:
        parsed = parse_exercise_line(line)
        if not parsed["sets"]:
            notes.append(line)
            done.append(line)
            continue
        exercise, is_new = _find_or_create_exercise(context, parsed["name"])
        if is_new:
            created.append(exercise.name)
        for number in range(1, parsed["sets"] + 1):
            sets_logged.append({
                "exercise_id": exercise.exercise_id, "set_number": number,
                "reps": parsed["reps"], "weight": parsed["weight"],
            })
        weight = f" at {parsed['weight']:g}" if parsed["weight"] else ""
        done.append(f"{parsed['sets']}x{parsed['reps']} {exercise.name}{weight}")
    context.workout.add_session(
        duration_minutes=duration, notes="\n".join(n for n in notes if n), sets_logged=sets_logged,
        date_str=str(arguments.get("date", "") or "").strip() or None,
    )
    reply = "Logged your workout" + (f": {'; '.join(done)}" if done else "") + "."
    if created:
        reply += f" (New exercise{'s' if len(created) > 1 else ''}: {', '.join(created)}.)"
    return reply


def _action_get_workout_summary(context: AppContext, arguments: dict) -> str:
    today = date.today()
    week_start = (today.toordinal() - today.weekday())
    sessions = context.workout.all_sessions()
    if not sessions:
        return "No workouts logged yet. Tell me what you did and I'll start tracking."
    this_week = [s for s in sessions if date.fromisoformat(s.date).toordinal() >= week_start]
    last = sessions[0]
    names = {e.exercise_id: e.name for e in context.workout.all_exercises()}
    last_exercises = sorted({names.get(x.get("exercise_id"), "exercise") for x in last.sets_logged})
    days_ago = (today - date.fromisoformat(last.date)).days
    when = "today" if days_ago == 0 else ("yesterday" if days_ago == 1 else f"{days_ago} days ago")
    what = f" ({', '.join(last_exercises)})" if last_exercises else ""
    return f"{len(this_week)} workout(s) this week. Your last one was {when}{what}."


def _action_get_personal_record(context: AppContext, arguments: dict) -> str:
    exercise, error = resolve_by_name(context.workout.all_exercises(), str(arguments.get("exercise", "")), lambda e: e.name, "exercise")
    if error:
        return error
    pr = context.workout.personal_record_for(exercise.exercise_id)
    if pr is None:
        return f"You haven't logged any sets of {exercise.name} yet."
    weight = f"{pr['weight']:g} for " if pr["weight"] else ""
    return f"Your {exercise.name} record is {weight}{pr['reps']} reps, on {pr['date']}."


# ---------------------------------------------------------------------------
# People & pets
# ---------------------------------------------------------------------------


def _find_person(context: AppContext, name: str):
    return resolve_by_name(context.relationships.all_people(), name, lambda p: p.name, "person")


def _find_pet(context: AppContext, name: str):
    return resolve_by_name(context.relationships.all_pets(), name, lambda p: p.name, "pet")


def _action_add_person(context: AppContext, arguments: dict) -> str:
    name = str(arguments.get("name", "") or "").strip()
    if not name:
        return "Who should I add?"
    if any(p.name.lower() == name.lower() for p in context.relationships.all_people()):
        return f"{name} is already in People. Tell me what to add about them."
    birthday = parse_birthday(arguments.get("birthday", "")) or ""
    person = context.relationships.add_person(
        name=name, relationship=str(arguments.get("relationship", "") or "").strip(), birthday=birthday,
        notes=str(arguments.get("note", "") or "").strip(),
    )
    extra = f", birthday {speak_birthday(birthday)}" if birthday else ""
    rel = f" ({person.relationship})" if person.relationship else ""
    return f"Added {person.name}{rel} to People{extra}."


def _action_update_person(context: AppContext, arguments: dict) -> str:
    person, error = _find_person(context, str(arguments.get("name", "")))
    if error:
        return error
    fields, said = {}, []
    relationship = str(arguments.get("relationship", "") or "").strip()
    if relationship:
        fields["relationship"] = relationship
        said.append(f"relationship {relationship}")
    if arguments.get("birthday"):
        birthday = parse_birthday(arguments["birthday"])
        if birthday is None:
            return f"I couldn't read '{arguments['birthday']}' as a date. Try something like 'March 3'."
        fields["birthday"] = birthday
        said.append(f"birthday {speak_birthday(birthday)}")
    for key, field, label, dated in (
        ("favorite_thing", "favorite_things", "likes", False),
        ("gift_idea", "gift_ideas", "gift idea", False),
        ("note", "notes", "note", True),
    ):
        text = str(arguments.get(key, "") or "").strip()
        if text:
            fields[field] = _append_line(getattr(person, field), text, dated=dated)
            said.append(f"{label}: {text}")
    if not fields:
        return f"What should I remember about {person.name}?"
    context.relationships.update_person(person.person_id, **fields)
    return f"Got it, {person.name}: {'; '.join(said)}."


def _action_get_person(context: AppContext, arguments: dict) -> str:
    person, error = _find_person(context, str(arguments.get("name", "")))
    if error:
        return error
    parts = [person.name + (f", your {person.relationship.lower()}" if person.relationship else "")]
    if person.birthday:
        days = days_until(person.birthday, date.today())
        soon = "" if days is None else (" (today!)" if days == 0 else f" ({days} days away)")
        parts.append(f"birthday {speak_birthday(person.birthday)}{soon}")
    reply = ", ".join(parts) + "."
    if person.favorite_things.strip():
        reply += f" Likes: {'; '.join(person.favorite_things.strip().splitlines())}."
    if person.gift_ideas.strip():
        reply += f" Gift ideas: {'; '.join(person.gift_ideas.strip().splitlines())}."
    if person.notes.strip():
        reply += f" Notes: {' / '.join(person.notes.strip().splitlines()[-3:])}"
    return reply


def _action_list_upcoming_birthdays(context: AppContext, arguments: dict) -> str:
    today = date.today()
    within = int(_num(arguments.get("within_days"), 60) or 60)
    upcoming = sorted(
        (days_until(p.birthday, today), p) for p in context.relationships.all_people() if p.birthday
    )
    upcoming = [(d, p) for d, p in upcoming if d is not None and d <= within]
    if not upcoming:
        return f"No birthdays in the next {within} days."
    return "Coming up: " + "; ".join(
        f"{p.name} {'today' if d == 0 else f'in {d} days'} ({speak_birthday(p.birthday)})" for d, p in upcoming
    ) + "."


def _action_add_pet(context: AppContext, arguments: dict) -> str:
    name = str(arguments.get("name", "") or "").strip()
    if not name:
        return "What's your pet's name?"
    birthday = parse_birthday(arguments.get("birthday", "")) or ""
    pet = context.relationships.add_pet(name=name, species=str(arguments.get("species", "") or "").strip(), birthday=birthday)
    kind = f" the {pet.species.lower()}" if pet.species else ""
    return f"Added {pet.name}{kind} to Pets."


def _action_update_pet(context: AppContext, arguments: dict) -> str:
    pet, error = _find_pet(context, str(arguments.get("name", "")))
    if error:
        return error
    fields, said = {}, []
    species = str(arguments.get("species", "") or "").strip()
    if species:
        fields["species"] = species
        said.append(species)
    if arguments.get("birthday"):
        birthday = parse_birthday(arguments["birthday"])
        if birthday:
            fields["birthday"] = birthday
            said.append(f"birthday {speak_birthday(birthday)}")
    medical = str(arguments.get("medical_note", "") or "").strip()
    if medical:
        fields["medical_notes"] = _append_line(pet.medical_notes, medical, dated=True)
        said.append(f"medical: {medical}")
    note = str(arguments.get("note", "") or "").strip()
    if note:
        fields["notes"] = _append_line(pet.notes, note, dated=True)
        said.append(f"note: {note}")
    if not fields:
        return f"What should I record for {pet.name}?"
    context.relationships.update_pet(pet.pet_id, **fields)
    return f"Updated {pet.name}: {'; '.join(said)}."


def _action_get_pet(context: AppContext, arguments: dict) -> str:
    pet, error = _find_pet(context, str(arguments.get("name", "")))
    if error:
        return error
    reply = pet.name + (f" ({pet.species})" if pet.species else "")
    if pet.birthday:
        reply += f", birthday {speak_birthday(pet.birthday)}"
    reply += "."
    if pet.medical_notes.strip():
        reply += f" Medical: {' / '.join(pet.medical_notes.strip().splitlines()[-3:])}."
    if pet.notes.strip():
        reply += f" Notes: {' / '.join(pet.notes.strip().splitlines()[-3:])}"
    return reply


# ---------------------------------------------------------------------------
# Household routines (recurring missions in the "Household" category)
# ---------------------------------------------------------------------------


def _household_templates(context: AppContext) -> list:
    if context.recurring_missions is None:
        return []
    return [t for t in context.recurring_missions.all_templates() if t.category == "Household" and t.active]


def _action_list_household_routines(context: AppContext, arguments: dict) -> str:
    templates = _household_templates(context)
    if not templates:
        return "You don't have any household routines yet. Want me to set one up, like laundry twice a week?"
    today = date.today()
    lines, done = [], 0
    for t in templates:
        mission, _ = context.recurring_missions.ensure_current_missions(t, today)
        streak = context.recurring_missions.current_streak_for_template(t.template_id, today)
        period = "this week" if t.recurrence == "weekly" else "today"
        if mission.objectives:
            o = mission.objectives[0]
            complete = o.progress >= o.target
            done += complete
            status = "done" if complete else f"{o.progress:g} of {o.target:g}"
        else:
            status = "no goal"
        streak_text = f", {streak}-{'week' if t.recurrence == 'weekly' else 'day'} streak" if streak else ""
        lines.append(f"{t.name} {period}: {status}{streak_text}")
    return f"{done} of {len(templates)} routines done. " + "; ".join(lines) + "."


def _action_log_household_routine(context: AppContext, arguments: dict) -> str:
    template, error = resolve_by_name(_household_templates(context), str(arguments.get("routine", "")), lambda t: t.name, "household routine")
    if error:
        return error
    amount = _num(arguments.get("amount"), 1.0) or 1.0
    mission, _ = context.recurring_missions.ensure_current_missions(template, date.today())
    if not mission.objectives:
        return f"{template.name} doesn't have a goal to count toward."
    context.missions.increment_tally(mission.mission_id, 0, delta=amount)
    objective = context.missions.get_mission(mission.mission_id).objectives[0]
    if objective.progress >= objective.target:
        return f"{template.name}: {objective.progress:g} of {objective.target:g}. That's done for {'the week' if template.recurrence == 'weekly' else 'today'}!"
    return f"{template.name}: {objective.progress:g} of {objective.target:g}."


def _action_add_household_routine(context: AppContext, arguments: dict) -> str:
    from core.gamification import SkillWeight

    if context.recurring_missions is None:
        return "Household routines aren't available right now."
    name = str(arguments.get("name", "") or "").strip()
    if not name:
        return "What's the routine called?"
    if any(t.name.lower() == name.lower() for t in _household_templates(context)):
        return f"You already have a {name} routine."
    recurrence = "weekly" if str(arguments.get("recurrence", "")).strip().lower().startswith("week") else "daily"
    target = max(1.0, _num(arguments.get("times"), 1.0) or 1.0)
    context.recurring_missions.add_template(
        name=name, objective_description_template=f"{name} ({{target:g}}x)", base_target=target,
        target_increment_per_week=0.0, daily_reward_xp=10, weekly_bonus_reward_xp=25,
        start_date=date.today().isoformat(), daily_skill_rewards=[SkillWeight("household_management", 5)],
        icon="\U0001F9FA", recurrence=recurrence, category="Household",
    )
    per = "a week" if recurrence == "weekly" else "a day"
    return f"Added {name}: {target:g} time{'s' if target != 1 else ''} {per}. I'll track your streak."


# ---------------------------------------------------------------------------
# Classroom
# ---------------------------------------------------------------------------


def _all_courses(context: AppContext) -> list:
    return [c for s in context.classroom.all_subjects() for c in context.classroom.courses_for_subject(s.subject_id)]


def _all_lessons(context: AppContext) -> list:
    return [l for c in _all_courses(context) for l in context.classroom.lessons_for_course(c.course_id)]


def _action_add_course(context: AppContext, arguments: dict) -> str:
    subject_name = str(arguments.get("subject", "") or "").strip()
    course_name = str(arguments.get("course", "") or "").strip()
    if not subject_name or not course_name:
        return "What subject is it under, and what's the course called?"
    subject = next((s for s in context.classroom.all_subjects() if s.name.lower() == subject_name.lower()), None)
    new_subject = subject is None
    if new_subject:
        subject = context.classroom.add_subject(subject_name)
    course = context.classroom.add_course(subject.subject_id, course_name, description=str(arguments.get("description", "") or ""))
    lessons = _as_list(arguments.get("lessons"))
    for lesson in lessons:
        context.classroom.add_lesson(course.course_id, lesson)
    tail = f" with {len(lessons)} lessons" if lessons else ""
    return f"Added the course {course.name}{tail} under {'new subject ' if new_subject else ''}{subject.name}."


def _action_add_lesson(context: AppContext, arguments: dict) -> str:
    course, error = resolve_by_name(_all_courses(context), str(arguments.get("course", "")), lambda c: c.name, "course")
    if error:
        return error
    names = _as_list(arguments.get("lessons")) or _as_list(arguments.get("lesson"))
    if not names:
        return f"What lesson should I add to {course.name}?"
    for name in names:
        context.classroom.add_lesson(course.course_id, name, notes=str(arguments.get("notes", "") or ""))
    return f"Added {', '.join(names)} to {course.name}."


def _action_complete_lesson(context: AppContext, arguments: dict) -> str:
    lessons = [l for l in _all_lessons(context) if not l.completed]
    lesson, error = resolve_by_name(lessons, str(arguments.get("lesson", "")), lambda l: l.name, "unfinished lesson")
    if error:
        return error
    context.classroom.update_lesson(lesson.lesson_id, completed=True)
    done, total = context.classroom.course_completion(lesson.course_id)
    course = context.classroom.get_course(lesson.course_id)
    return f"Nice, {lesson.name} is done. {course.name}: {done} of {total} lessons complete."


def _action_add_lesson_notes(context: AppContext, arguments: dict) -> str:
    lesson, error = resolve_by_name(_all_lessons(context), str(arguments.get("lesson", "")), lambda l: l.name, "lesson")
    if error:
        return error
    text = str(arguments.get("notes", "") or "").strip()
    if not text:
        return f"What should I add to your notes for {lesson.name}?"
    context.classroom.update_lesson(lesson.lesson_id, notes=_append_line(lesson.notes, text))
    return f"Added to your {lesson.name} notes."


def _action_get_learning_progress(context: AppContext, arguments: dict) -> str:
    subjects = context.classroom.all_subjects()
    if not subjects:
        return "You haven't set up any subjects yet. Tell me what you want to learn and I'll add a course."
    query = str(arguments.get("subject", "") or "").strip()
    if query:
        subject, error = resolve_by_name(subjects, query, lambda s: s.name, "subject")
        if error:
            return error
        subjects = [subject]
    parts = []
    for s in subjects:
        done, total = context.classroom.subject_completion(s.subject_id)
        courses = context.classroom.courses_for_subject(s.subject_id)
        nxt = next((l.name for c in courses for l in context.classroom.lessons_for_course(c.course_id) if not l.completed), None)
        parts.append(f"{s.name}: {done} of {total} lessons" + (f", next up {nxt}" if nxt else ""))
    return "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_life_actions(registry: AssistantActionRegistry) -> None:
    # -- workout -------------------------------------------------------------
    registry.register(AssistantAction(
        name="log_workout", domain="workout",
        description="Log a workout the user did. Each exercise as a line like '3x10 squats at 185' or '20 push-ups'; cardio like 'ran 3 miles' is kept as a note.",
        parameters=_obj({
            "exercises": _list("Exercise lines, e.g. ['3x10 squats at 185', '3x8 bench at 155']."),
            "duration_minutes": _n("Total minutes, if mentioned."), "notes": _s("Anything else they said about it."),
            "date": _s("YYYY-MM-DD if not today."),
        }, ["exercises"]),
        handler=_action_log_workout,
        trigger_phrases=("log my workout", "log a workout", "i worked out", "just worked out", "did my workout", "i lifted"),
    ))
    registry.register(AssistantAction(
        name="get_workout_summary", domain="workout",
        description="How many workouts this week and what the last one was.",
        parameters=_NO_PARAMS, handler=_action_get_workout_summary,
        trigger_phrases=("my workouts", "workouts this week", "when did i last work out", "last workout"),
    ))
    registry.register(AssistantAction(
        name="get_personal_record", domain="workout",
        description="The user's personal record (heaviest set) for one exercise.",
        parameters=_obj({"exercise": _s("The exercise, e.g. 'squat'.")}, ["exercise"]),
        handler=_action_get_personal_record,
        trigger_phrases=("personal record", "my pr ", "my pr?", "my pr.", "my best", "max on"),
    ))
    registry.register_domain_keywords("workout", (
        "workout", "workouts", "worked out", "reps", "squats", "squat", "bench press", "deadlift", "deadlifts",
        "push-ups", "pushups", "pull-ups", "pullups", "curls", "gym",
    ))
    registry.register_entity_names("workout", lambda ctx: [e.name for e in ctx.workout.all_exercises()] if ctx.workout else [])

    # -- people & pets -------------------------------------------------------
    registry.register(AssistantAction(
        name="add_person", domain="relationships",
        description="Add someone the user knows to People (family, friends, coworkers).",
        parameters=_obj({
            "name": _s("Their name."), "relationship": _s("e.g. Sister, Best friend, Coworker."),
            "birthday": _s("e.g. 'March 3' or YYYY-MM-DD."), "note": _s("Anything else the user said about them."),
        }, ["name"]),
        handler=_action_add_person,
        trigger_phrases=("add a person", "add someone", "add my sister", "add my brother", "add my friend", "add my mom", "add my dad"),
    ))
    registry.register(AssistantAction(
        name="update_person", domain="relationships",
        description="Remember something about a person: their birthday, relationship, something they like, a gift idea, or a dated note (e.g. 'Sarah got a new job').",
        parameters=_obj({
            "name": _s("The person."), "relationship": _s("Relationship, if stated."), "birthday": _s("Birthday, if stated."),
            "favorite_thing": _s("Something they like."), "gift_idea": _s("A gift idea for them."), "note": _s("Any other news or memory."),
        }, ["name"]),
        handler=_action_update_person,
        trigger_phrases=("'s birthday is", "birthday is on", "gift idea", "would love"),
    ))
    registry.register(AssistantAction(
        name="get_person", domain="relationships",
        description="Everything MIA knows about a person: relationship, birthday, likes, gift ideas, notes.",
        parameters=_obj({"name": _s("The person.")}, ["name"]),
        handler=_action_get_person,
        trigger_phrases=("gift ideas for", "what does she like", "what does he like"),
    ))
    registry.register(AssistantAction(
        name="list_upcoming_birthdays", domain="relationships",
        description="Birthdays coming up soon among the people the user knows.",
        parameters=_obj({"within_days": _n("How far ahead to look (default 60).")}, []),
        handler=_action_list_upcoming_birthdays,
        trigger_phrases=("upcoming birthdays", "birthdays coming up", "whose birthday", "any birthdays"),
    ))
    registry.register(AssistantAction(
        name="add_pet", domain="relationships", description="Add a pet.",
        parameters=_obj({"name": _s("Pet's name."), "species": _s("Dog, cat, etc."), "birthday": _s("Birthday or adoption date.")}, ["name"]),
        handler=_action_add_pet,
        trigger_phrases=("add a pet", "new pet", "we got a puppy", "we got a kitten", "adopted a"),
    ))
    registry.register(AssistantAction(
        name="update_pet", domain="relationships",
        description="Record something about a pet: a vet visit or medical note (dated), species, birthday, or another note.",
        parameters=_obj({
            "name": _s("The pet."), "medical_note": _s("Vet visit, medication, vaccine, symptom."),
            "note": _s("Other news."), "species": _s("Species."), "birthday": _s("Birthday."),
        }, ["name"]),
        handler=_action_update_pet,
        trigger_phrases=("to the vet", "vet visit", "vaccin", "medication"),
    ))
    registry.register(AssistantAction(
        name="get_pet", domain="relationships", description="Everything MIA knows about a pet, including medical history.",
        parameters=_obj({"name": _s("The pet.")}, ["name"]), handler=_action_get_pet,
        trigger_phrases=("last vet", "medical history",),
    ))
    # Not "dog"/"cat"/"pet": "what's a good name for a dog?" is small talk. Pets are matched by name.
    registry.register_domain_keywords("relationships", ("birthday", "birthdays", "vet", "pets"))
    registry.register_entity_names("relationships", lambda ctx: (
        [p.name for p in ctx.relationships.all_people()] + [p.name for p in ctx.relationships.all_pets()]
    ) if ctx.relationships else [])

    # -- household routines --------------------------------------------------
    registry.register(AssistantAction(
        name="list_household_routines", domain="household",
        description="Today's/this week's household routines (laundry, dishes, chores): progress and streaks.",
        parameters=_NO_PARAMS, handler=_action_list_household_routines,
        trigger_phrases=("my chores", "household routines", "chores today", "what chores", "routines today"),
    ))
    registry.register(AssistantAction(
        name="log_household_routine", domain="household",
        description="Count progress on a household routine the user did (e.g. did a load of laundry, did the dishes).",
        parameters=_obj({"routine": _s("The routine, in the user's words, e.g. 'laundry'."), "amount": _n("How many times (default 1).")}, ["routine"]),
        handler=_action_log_household_routine,
        trigger_phrases=("did the dishes", "did a load", "did laundry", "did the laundry", "finished the chores", "did my chores"),
    ))
    registry.register(AssistantAction(
        name="add_household_routine", domain="household",
        description="Set up a new recurring household routine with a daily or weekly goal and a streak (e.g. laundry twice a week).",
        parameters=_obj({
            "name": _s("Routine name, e.g. 'Laundry'."), "times": _n("How many times per period."),
            "recurrence": _s("daily or weekly."),
        }, ["name"]),
        handler=_action_add_household_routine,
        trigger_phrases=("add a chore", "add a routine", "new routine", "new chore", "track my chores"),
    ))
    registry.register_domain_keywords("household", ("chore", "chores", "laundry", "dishes", "vacuum", "vacuumed"))
    registry.register_entity_names("household", lambda ctx: [t.name for t in _household_templates(ctx)])

    # -- classroom -----------------------------------------------------------
    registry.register(AssistantAction(
        name="add_course", domain="classroom",
        description="Add a course to Classroom under a subject (creating the subject if new), optionally with its lessons.",
        parameters=_obj({
            "subject": _s("e.g. 'Electrical'."), "course": _s("e.g. 'Residential Wiring Basics'."),
            "description": _s("Optional."), "lessons": _list("Optional lesson names in order."),
        }, ["subject", "course"]),
        handler=_action_add_course,
        trigger_phrases=("add a course", "new course", "start a course", "i want to learn", "learn about"),
    ))
    registry.register(AssistantAction(
        name="add_lesson", domain="classroom", description="Add lesson(s) to an existing Classroom course.",
        parameters=_obj({"course": _s("The course."), "lessons": _list("Lesson names."), "notes": _s("Optional notes.")}, ["course", "lessons"]),
        handler=_action_add_lesson,
        trigger_phrases=("add a lesson", "new lesson"),
    ))
    registry.register(AssistantAction(
        name="complete_lesson", domain="classroom", description="Mark a Classroom lesson finished.",
        parameters=_obj({"lesson": _s("The lesson, in the user's words.")}, ["lesson"]),
        handler=_action_complete_lesson,
        trigger_phrases=("finished the lesson", "finished lesson", "done with the lesson", "completed the lesson", "finished my lesson"),
    ))
    registry.register(AssistantAction(
        name="add_lesson_notes", domain="classroom", description="Add what the user learned to a lesson's notes.",
        parameters=_obj({"lesson": _s("The lesson."), "notes": _s("What to add.")}, ["lesson", "notes"]),
        handler=_action_add_lesson_notes,
        trigger_phrases=("add to my notes for", "lesson notes", "i learned that"),
    ))
    registry.register(AssistantAction(
        name="get_learning_progress", domain="classroom", description="Progress through Classroom subjects and what's next.",
        parameters=_obj({"subject": _s("Optional subject.")}, []),
        handler=_action_get_learning_progress,
        trigger_phrases=("learning progress", "what am i learning", "my courses", "next lesson", "how far am i in"),
    ))
    # Not "course": "of course" is everywhere.
    registry.register_domain_keywords("classroom", ("classroom", "courses", "lesson", "lessons", "studying"))
    registry.register_entity_names("classroom", lambda ctx: (
        [s.name for s in ctx.classroom.all_subjects()] + [c.name for c in _all_courses(ctx)] + [l.name for l in _all_lessons(ctx)]
    ) if ctx.classroom else [])
