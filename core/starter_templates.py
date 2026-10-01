"""
core.starter_templates
========================

Starter sets (2026-10-01): a new MIA is empty, and an empty app is hard
to start with. A starter set fills in the usual things for a kind of
life, so there's something to check off on day one:

- **Home & Family**: daily and weekly chores, and the house's upkeep
  (smoke alarms, the furnace filter, the dryer vent...).
- **Homestead**: animal and garden chores, well, generator and fences.
- **Student**: study and reading streaks, planning the week.
- **Personal**: a daily walk, planning tomorrow, a weekly journal.
- **Business**: filing receipts, the books, following up.
- **Fitness**: a beginner bodyweight workout and a daily movement goal.

Each set is split into parts the person can leave out ("we don't have a
well"). Adding one is safe to repeat (nothing already there by name is
added twice), undoable in one step ("undo that", core/undo_log.py), and
upkeep schedules count from today, so nothing shows up overdue. A child
(core/child_accounts.py) gets the routines and workouts, not the house
upkeep.

The contents are general on purpose: no names, places or amounts. Money
targets are left out because they're personal. Offered in the setup
questions (gui/onboarding_dialog.py), Settings and the Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional

from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Routine:
    """A recurring Mission (core/recurring_mission_manager.py)."""
    name: str
    objective: str  # "{target:g}" is filled with the day's or week's target
    target: float = 1.0
    recurrence: str = "daily"  # daily | weekly
    category: str = "Household"  # Household shows in Household, Fitness in Workouts
    skill: str = "household_management"
    icon: str = "\U0001F9FA"


@dataclass(frozen=True)
class Upkeep:
    """A maintenance asset with calendar tasks (title, every N days)."""
    asset: str
    category: str
    tasks: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Workout:
    """A workout template: (exercise, category, sets, reps)."""
    name: str
    exercises: tuple[tuple[str, str, int, int], ...]


@dataclass(frozen=True)
class Part:
    part_id: str
    label: str
    items: tuple


@dataclass(frozen=True)
class Starter:
    starter_id: str
    name: str
    description: str
    parts: tuple[Part, ...]


_HOUSE = Upkeep("Home", "Property", (
    ("Test the smoke and carbon monoxide alarms", 180),
    ("Replace the heating and cooling filter", 90),
    ("Clean the dryer vent", 365),
    ("Clean the fridge coils", 365),
    ("Check the fire extinguisher", 365),
    ("Clean the gutters", 180),
))

STARTERS: dict[str, Starter] = {s.starter_id: s for s in (
    Starter("home_family", "Home & Family", "Everyday chores and the house's upkeep.", (
        Part("chores", "Daily and weekly chores", (
            Routine("Dishes", "Do the dishes ({target:g}x)"),
            Routine("Tidy up", "Tidy up for {target:g} minutes", 10),
            Routine("Laundry", "Do {target:g} loads of laundry", 2, "weekly"),
            Routine("Trash and recycling", "Take out the trash and recycling ({target:g}x)", 1, "weekly"),
        )),
        Part("house", "House upkeep (alarms, filters, dryer vent...)", (_HOUSE,)),
    )),
    Starter("homestead", "Homestead", "Animals, garden, water, power and fences.", (
        Part("chores", "Animal and garden chores", (
            Routine("Animal chores", "Feed and water the animals ({target:g}x)", 1, skill="animal_care", icon="\U0001F404"),
            Routine("Garden check", "Check and water the garden ({target:g}x)", 1, skill="gardening", icon="\U0001F331"),
            Routine("Walk the property", "Walk the property ({target:g}x)", 1, "weekly", skill="landscaping",
                    icon="\U0001F333"),
        )),
        Part("house", "House upkeep (alarms, filters, dryer vent...)", (_HOUSE,)),
        Part("water", "Well and water", (
            Upkeep("Well and water", "Property", (("Test the well water", 365), ("Check the pressure tank", 180))),
        )),
        Part("power", "Generator", (
            Upkeep("Generator", "Power Equipment", (("Run the generator under load", 30),
                                                    ("Change the generator oil", 180))),
        )),
        Part("fences", "Fences", (Upkeep("Fences", "Property", (("Walk and fix the fences", 90),)),)),
    )),
    Starter("student", "Student", "Study and reading streaks, and a weekly plan.", (
        Part("study", "Study and reading", (
            Routine("Study", "Study for {target:g} minutes", 25, category="Learning", skill="learning", icon="\U0001F4DA"),
            Routine("Read", "Read {target:g} pages", 10, category="Learning", skill="learning", icon="\U0001F4D6"),
        )),
        Part("plan", "Plan the week", (
            Routine("Plan the week", "Plan the week ahead ({target:g}x)", 1, "weekly", "Personal", "organization",
                    "\U0001F5D3"),
        )),
    )),
    Starter("personal", "Personal", "A daily walk, planning tomorrow and a weekly journal.", (
        Part("daily", "Daily habits", (
            Routine("Walk", "Walk for {target:g} minutes", 15, category="Fitness", skill="endurance", icon="\U0001F6B6"),
            Routine("Plan tomorrow", "Plan tomorrow ({target:g}x)", 1, category="Personal", skill="organization",
                    icon="\U0001F4DD"),
        )),
        Part("journal", "Weekly journal", (
            Routine("Journal", "Write in your journal ({target:g}x)", 1, "weekly", "Personal", "focus", "\U0001F4D3"),
        )),
    )),
    Starter("business", "Business", "Receipts, the books and following up, every week.", (
        Part("weekly", "Weekly business routines", (
            Routine("File receipts", "File this week's receipts ({target:g}x)", 1, "weekly", "Business",
                    "organization", "\U0001F9FE"),
            Routine("Review the books", "Review income and expenses ({target:g}x)", 1, "weekly", "Business",
                    "organization", "\U0001F4CA"),
            Routine("Follow up", "Follow up with customers and leads ({target:g}x)", 1, "weekly", "Business",
                    "communication", "\U0001F4DE"),
        )),
    )),
    Starter("fitness", "Fitness", "A beginner bodyweight workout and a daily movement goal.", (
        Part("workout", "Beginner full-body workout (no equipment)", (
            Workout("Beginner full body", (
                ("Push-ups", "Chest", 3, 8), ("Bodyweight squats", "Legs", 3, 12), ("Lunges", "Legs", 3, 10),
                ("Glute bridges", "Legs", 3, 12), ("Plank (seconds)", "Core", 3, 30),
            )),
        )),
        Part("move", "Move every day", (
            Routine("Move", "Exercise for {target:g} minutes", 20, category="Fitness", skill="endurance",
                    icon="\U0001F3C3"),
        )),
    )),
)}

# The setup questions' goals (core/focus_presets.py GOALS) -> the starter sets they suggest.
GOAL_STARTERS = {"home": "home_family", "land": "homestead", "school": "student", "business": "business",
                 "health": "fitness", "thinking": "personal"}


def for_goals(goals: Iterable[str]) -> list[str]:
    """Pure logic. The starter sets the chosen goals suggest, in order, once each."""
    return list(dict.fromkeys(GOAL_STARTERS[g] for g in goals if g in GOAL_STARTERS))


def find(text: str) -> Optional[Starter]:
    """Pure logic. A starter set by id or name ("homestead", "home and family")."""
    wanted = "".join(c for c in (text or "").lower() if c.isalnum())
    if not wanted:
        return None
    for starter in STARTERS.values():
        keys = {starter.starter_id.replace("_", ""), "".join(c for c in starter.name.lower() if c.isalnum())}
        if wanted in keys or any(k.startswith(wanted) for k in keys):
            return starter
    return None


def describe(starter: Starter) -> str:
    """Pure logic. What's in a set, for the Assistant and the Settings window."""
    lines = []
    for part in starter.parts:
        names = []
        for item in part.items:
            if isinstance(item, Upkeep):
                names += [title.lower() for title, _days in item.tasks]
            else:
                names.append(item.name)
        lines.append(f"{part.label}: {', '.join(names)}")
    return f"{starter.name}: " + "; ".join(lines) + "."


@dataclass
class StarterResult:
    added: list[str] = field(default_factory=list)
    already: list[str] = field(default_factory=list)
    unavailable: list[str] = field(default_factory=list)  # parts this MIA (or a child) can't take

    def describe(self) -> str:
        if not self.added:
            text = "Everything in that set is already here." if self.already else "Nothing was added."
        else:
            text = f"Added {len(self.added)}: {', '.join(self.added)}."
            if self.already:
                text += f" Already had {len(self.already)}."
        if self.unavailable:
            text += f" Left out: {', '.join(self.unavailable)}."
        return text


def _same(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def _add_routine(context, routine: Routine, today: date, result: StarterResult) -> None:
    from core.gamification import SkillWeight

    store = context.recurring_missions
    if any(_same(t.name, routine.name) for t in store.all_templates()):
        result.already.append(routine.name)
        return
    store.add_template(
        name=routine.name, objective_description_template=routine.objective, base_target=routine.target,
        target_increment_per_week=0.0, daily_reward_xp=10, weekly_bonus_reward_xp=25,
        start_date=today.isoformat(), daily_skill_rewards=[SkillWeight(routine.skill, 5)], icon=routine.icon,
        recurrence=routine.recurrence, category=routine.category,
    )
    result.added.append(routine.name)


def _add_upkeep(context, upkeep: Upkeep, today: date, result: StarterResult) -> None:
    store = context.maintenance
    asset = next((a for a in store.all_assets() if _same(a.name, upkeep.asset)), None)
    if asset is None:
        asset = store.add_asset(upkeep.asset, upkeep.category, notes="From a starter set. Rename or delete freely.")
    have = {t.title.strip().lower() for t in store.all_tasks() if t.asset_id == asset.asset_id}
    for title, days in upkeep.tasks:
        if title.lower() in have:
            result.already.append(title)
            continue
        # Counted from today: nothing starts out overdue. Mark it done
        # with the real date if you know when it was last done.
        store.add_task(asset.asset_id, title, interval_days=days, last_completed=today.isoformat())
        result.added.append(title)


def _add_workout(context, workout: Workout, result: StarterResult) -> None:
    store = context.workout
    if any(_same(t.name, workout.name) for t in store.all_templates()):
        result.already.append(workout.name)
        return
    template = store.add_template(workout.name, notes="From a starter set.")
    for name, category, sets, reps in workout.exercises:
        exercise = next((e for e in store.all_exercises() if _same(e.name, name)), None)
        if exercise is None:
            exercise = store.add_exercise(name, category)
        store.add_exercise_to_template(template.template_id, exercise.exercise_id, sets, reps)
    result.added.append(workout.name)


_STORE_FOR = {Routine: "recurring_missions", Upkeep: "maintenance", Workout: "workout"}


def apply(context, starter_id: str, part_ids: Optional[Iterable[str]] = None,
          today: Optional[date] = None) -> StarterResult:
    """Add a starter set (all of it, or just `part_ids`). One undoable change."""
    from core.child_accounts import is_child
    from core.person_settings import person_id
    from core.undo_log import recording

    starter = STARTERS.get(starter_id)
    if starter is None:
        raise ValueError(f"No starter set '{starter_id}'.")
    today = today or date.today()
    wanted = set(part_ids) if part_ids is not None else {p.part_id for p in starter.parts}
    child = getattr(context, "config", None) is not None and is_child(context)
    result = StarterResult()
    with recording(f"starter_{starter_id}", person_id(context)) as change:
        for part in starter.parts:
            if part.part_id not in wanted:
                continue
            kinds = {type(item) for item in part.items}
            if (child and Upkeep in kinds) or any(getattr(context, _STORE_FOR[k], None) is None for k in kinds):
                result.unavailable.append(part.label)
                continue
            for item in part.items:
                if isinstance(item, Routine):
                    _add_routine(context, item, today, result)
                elif isinstance(item, Upkeep):
                    _add_upkeep(context, item, today, result)
                else:
                    _add_workout(context, item, result)
    undo = getattr(context, "undo", None)
    if undo is not None:
        undo.add(change)
    if result.added:
        from core.main_thread import publish

        publish(context, "records.changed", action=f"starter_{starter_id}")
    log.info("Starter set %s: %s", starter_id, result.describe())
    return result
