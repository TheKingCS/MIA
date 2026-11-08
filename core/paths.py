"""
core.paths
============

Learning paths: how MIA turns a desire into a skill (DEC-0112; Zac, 2026-11-07,
after the guitar path: "That whole principle ... should be a principle she uses
repeatedly when understanding a desire or interest, planning steps for
implementing or improvement, tracking progress, monitoring statistics,
completing missions as progress is made and being able to verify and test").

**The loop**, the same for a person learning guitar and for MIA learning to
build herself (her Night School curriculum, DEC-0107):

1. **Understand the desire**: what they want, in their own words (`goal`),
   and how much time they have (`plan`).
2. **Plan the steps**: a program (`Program`) of stages, each with lessons
   (steps, why, what to watch for) and the skill checks that finish it.
3. **Teach**: the next lesson for where they are (`teach()`).
4. **Practise and log**: every session (`PathBook.log_practice()`).
5. **Homework as missions**: each week a mission for each path, from the
   plan and the open checks; its progress comes from the log and it
   completes itself (`ensure_homework()`).
6. **Statistics**: the week against the plan, the streak, hours, checks
   passed, bests (`stats()`); a started path's screen is `path_card()`,
   with each check of the stage and who verifies it (`check_state()`).
7. **Verify by evidence**: a check is passed by showing it, and the record
   says how: **heard** or otherwise measured by a verifier in code (guitar's
   ear, `core/guitar_ear.py`), **recorded** (read from what MIA already
   keeps for them since the path started: workouts, GPS tracks, meals
   cooked; `SOURCES`, and `sweep()` passes these by itself), **counted** (a
   number at or over the mark), or **said** (what can't be measured yet,
   and it says so).
8. **Next stage** when every check of this one is passed; XP in the
   program's skill along the way.

**Programs** come from two places. **Built in** (`register()`): written and
checked in code, like guitar (`core/guitar.py`). **Drafted** for an interest
no program covers (`draft()`): MIA's local model writes one from the
interest, grounded in what her specialists know (core/specialists.py), and
code checks its shape (stages, lessons, checks counted or said with a mark
and a unit). A draft is a proposal: it starts only when the person says so,
and says it was drafted.

**The store** (`PathBook`, each person's own, `paths.json`): every path they've
started (goal, plan, sessions, attempts, stage) and their drafts. Practice,
passed checks and finished stages are life events.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from core import life_events
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "paths.json"
PREFIX = "path:"  # homework missions' occurrence key: path:<id>:week:<monday>
CHECK_XP = 25
STAGE_XP = 100
HOMEWORK_XP = 40
PLAIN_HOWS = ("said", "counted")
RECORDED = "recorded"


# ------------------------------------------------------------------ programs

@dataclass(frozen=True)
class Lesson:
    """One lesson: its id and title, the steps in order, why it matters, the mistakes to watch for, and what it's
    about (for a program's own extras: guitar's chord shapes)."""
    id: str
    title: str
    steps: tuple[str, ...]
    why: str
    watch: tuple[str, ...] = ()
    about: tuple[str, ...] = ()


@dataclass(frozen=True)
class Check:
    """One skill check: its id, what to do, how it's verified (said, counted, recorded, or a verifier the program
    has), what it's about (a chord for guitar), the mark that passes a counted or recorded one, its unit, and for a
    recorded one the record that measures it (a key of `SOURCES`)."""
    id: str
    what: str
    how: str
    about: str = ""
    passes_at: float = 0.0
    unit: str = ""
    source: str = ""


@dataclass(frozen=True)
class Stage:
    """One stage: its number, name, what it builds, its lessons and the checks that finish it."""
    number: int
    name: str
    builds: str
    lessons: tuple[Lesson, ...]
    checks: tuple[Check, ...]


@dataclass(frozen=True)
class Program:
    """A learning program: its id, name, the skill its XP goes to, icon, what it's for, the words that mean someone
    wants it, its stages, its verifiers (how -> verify(context, path_id, check, payload) -> dict), a teacher's extra
    for a lesson (guitar adds the chord shapes), whether it was drafted, and the plan it suggests."""
    id: str
    name: str
    skill: str
    icon: str
    about: str
    words: tuple[str, ...]
    stages: tuple[Stage, ...]
    verifiers: dict = field(default_factory=dict)
    extra: Optional[Callable[[Lesson], str]] = None
    drafted: bool = False
    plan: tuple[int, int] = (15, 5)  # minutes a day, days a week

    def check(self, check_id: str) -> Optional[tuple[Stage, Check]]:
        """A check by id, with its stage, or None."""
        return next(((s, c) for s in self.stages for c in s.checks if c.id == check_id), None)


PROGRAMS: dict[str, Program] = {}


def register(program: Program) -> Program:
    """Adds a built-in program (its module registers it on import)."""
    PROGRAMS[program.id] = program
    return program


def _builtins() -> None:
    """Imports the modules that register built-in programs."""
    import core.guitar  # noqa: F401


def program_of(context, path_id: str) -> Optional[Program]:
    """A program by id: built in, or one of this person's drafts."""
    _builtins()
    if path_id in PROGRAMS:
        return PROGRAMS[path_id]
    book = getattr(context, "paths", None)
    raw = book.drafts.get(path_id) if book is not None else None
    return from_dict(raw) if raw else None


def from_dict(raw: dict) -> Program:
    """A drafted program from its saved form (no verifiers: drafted checks are counted, recorded or said)."""
    stages = tuple(Stage(int(s["number"]), s["name"], s.get("builds", ""),
                         tuple(Lesson(l["id"], l["title"], tuple(l["steps"]), l["why"], tuple(l.get("watch") or ()))
                               for l in s["lessons"]),
                         tuple(Check(c["id"], c["what"], c["how"], "", float(c.get("passes_at") or 0), c.get("unit", ""),
                                     c.get("source", ""))
                               for c in s["checks"]))
                   for s in raw["stages"])
    return Program(raw["id"], raw["name"], raw.get("skill", ""), raw.get("icon", "🎯"), raw.get("about", ""),
                   tuple(raw.get("words") or ()), stages, drafted=True,
                   plan=tuple(raw.get("plan") or (15, 5)))


def to_dict(program: Program) -> dict:
    """A program's saved form (its verifiers and extras aren't data and aren't kept)."""
    return {"id": program.id, "name": program.name, "skill": program.skill, "icon": program.icon,
            "about": program.about, "words": list(program.words), "plan": list(program.plan),
            "stages": [{"number": s.number, "name": s.name, "builds": s.builds,
                        "lessons": [asdict(l) for l in s.lessons], "checks": [asdict(c) for c in s.checks]}
                       for s in program.stages]}


def problems(program: Program) -> list[str]:
    """What's wrong with a program's shape: no stages; a stage without lessons or checks; a lesson without steps or
    why; a check verified a way the program can't; a counted check without a mark and a unit; a recorded one without
    a mark or a record MIA keeps; ids used twice."""
    out = []
    if not program.stages:
        out.append("it has no stages")
    ids = [c.id for s in program.stages for c in s.checks] + [l.id for s in program.stages for l in s.lessons]
    if len(ids) != len(set(ids)):
        out.append("an id is used twice")
    for s in program.stages:
        if not s.lessons or not s.checks:
            out.append(f"stage {s.number} needs lessons and checks")
        for l in s.lessons:
            if not l.steps or not l.why:
                out.append(f"lesson {l.id} needs steps and why")
        for c in s.checks:
            if c.how not in PLAIN_HOWS and c.how != RECORDED and c.how not in program.verifiers:
                out.append(f"check {c.id} is verified {c.how!r}, which this program can't")
            if c.how == "counted" and not (c.passes_at > 0 and c.unit):
                out.append(f"check {c.id} is counted but has no mark or unit")
            if c.how == RECORDED and not (c.passes_at > 0 and c.source in SOURCES):
                out.append(f"check {c.id} is recorded but has no mark or no record MIA keeps")
    return out


def find_program(context, interest: str) -> Optional[Program]:
    """The program an interest means: by name or id, else the one whose words it uses most; a person's drafts
    count too."""
    _builtins()
    text = f" {(interest or '').lower()} "
    candidates = list(PROGRAMS.values())
    book = getattr(context, "paths", None)
    if book is not None:
        candidates += [from_dict(d) for d in book.drafts.values()]
    for p in candidates:
        if f" {p.id} " in text or p.name.lower() in text:
            return p
    scored = [(sum(1 for w in p.words if w in text), p) for p in candidates]
    best = max(scored, key=lambda x: x[0], default=(0, None))
    return best[1] if best[0] else None


# ------------------------------------------------------------------ the store (each person's own)

class PathBook:
    """A person's learning paths (paths.json in their own folder, written through atomic_write_text): for each path
    started, their goal, plan, practice sessions, check attempts and stage; and the programs drafted for them."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads it from the person's folder (or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self._load()

    def _load(self) -> None:
        """Reads it; missing or unreadable is nothing started. Sealed on disk (DEC-0126): open_text reads it sealed or plain, and one that won't open is copied aside and counts as damaged."""
        try:
            data = json.loads(open_text(self._file))
        except (OSError, ValueError):
            data = {}
        self.paths: dict[str, dict] = dict(data.get("paths") or {})
        self.drafts: dict[str, dict] = dict(data.get("drafts") or {})

    def _save(self) -> None:
        """Writes it atomically (the latest 3,000 sessions and attempts of each path)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for p in self.paths.values():
            p["sessions"], p["attempts"] = p["sessions"][-3000:], p["attempts"][-3000:]
        atomic_write_text(self._file, json.dumps({"paths": self.paths, "drafts": self.drafts}, indent=1,
                                                 ensure_ascii=False))

    def path(self, path_id: str) -> Optional[dict]:
        """A started path's record, or None."""
        return self.paths.get(path_id)

    def started(self) -> list[str]:
        """The paths started, in the order they were."""
        return sorted(self.paths, key=lambda k: self.paths[k]["started"])

    def keep_draft(self, program: Program) -> None:
        """Keeps a drafted program for this person (replacing one with the same id)."""
        self.drafts[program.id] = to_dict(program)
        self._save()

    def start(self, program: Program, goal: str = "", minutes_a_day: Optional[int] = None,
              days_a_week: Optional[int] = None, today: Optional[date] = None) -> dict:
        """Starts a path (or updates the goal and plan of one started): their goal in their own words and how much
        they mean to practise (5 to 240 minutes, 1 to 7 days); a life event the first time."""
        first = program.id not in self.paths
        record = self.paths.setdefault(program.id, {"goal": "", "started": (today or date.today()).isoformat(),
                                                    "plan": {}, "sessions": [], "attempts": [], "stage": 1})
        record["goal"] = " ".join(str(goal or record["goal"]).split())[:300]
        minutes = int(minutes_a_day or record["plan"].get("minutes_a_day") or program.plan[0])
        days = int(days_a_week or record["plan"].get("days_a_week") or program.plan[1])
        record["plan"] = {"minutes_a_day": max(5, min(240, minutes)), "days_a_week": max(1, min(7, days))}
        self._save()
        if first:
            life_events.record(self, "path_started", f"Started learning {program.name}"
                               + (f": {record['goal']}" if record["goal"] else ""), [f"path:{program.id}"],
                               {"path": program.id, "plan": record["plan"]})
        return record

    def log_practice(self, program: Program, minutes: float, worked_on: str = "", value: Optional[float] = None,
                     day: Optional[str] = None) -> dict:
        """Keeps one practice session on a started path (minutes over 0, what they worked on, a number such as a
        tempo); a life event. ValueError for no time or a path not started."""
        record = self.paths.get(program.id)
        if record is None:
            raise ValueError(f"Start {program.name} first.")
        minutes = float(minutes or 0)
        if minutes <= 0:
            raise ValueError("How long did you practise?")
        entry = {"id": uuid.uuid4().hex[:8], "date": day or date.today().isoformat(), "minutes": round(minutes, 1),
                 "worked_on": " ".join(str(worked_on or "").split())[:200],
                 "value": round(float(value), 1) if value not in (None, "") else None}
        record["sessions"].append(entry)
        self._save()
        life_events.record(self, "path_practice", f"Practised {program.name} {minutes:g} min"
                           + (f": {entry['worked_on']}" if entry["worked_on"] else ""), [f"path:{program.id}"],
                           {"path": program.id, "minutes": entry["minutes"]})
        return entry

    def passed(self, path_id: str, check_id: str) -> bool:
        """Whether a check on a path has been passed."""
        record = self.paths.get(path_id) or {}
        return any(a["check"] == check_id and a["passed"] for a in record.get("attempts", []))

    def best(self, path_id: str, check_id: str) -> Optional[float]:
        """The best value counted for a check, or None."""
        record = self.paths.get(path_id) or {}
        values = [a["value"] for a in record.get("attempts", []) if a["check"] == check_id and a["value"] is not None]
        return max(values) if values else None

    def attempt(self, program: Program, check_id: str, passed: bool, value: Optional[float] = None,
                how: str = "said", detail: str = "", day: Optional[str] = None) -> dict:
        """Keeps one attempt at a check: passed or not, its value, how it was verified, what was found. A first pass
        is a life event and earns XP; when every check of the current stage is passed the next opens (another life
        event, more XP). ValueError for a check the program hasn't or a path not started."""
        record = self.paths.get(program.id)
        if record is None:
            raise ValueError(f"Start {program.name} first.")
        found = program.check(check_id)
        if found is None:
            raise ValueError("There's no such check.")
        stage, check = found
        first_pass = passed and not self.passed(program.id, check_id)
        entry = {"id": uuid.uuid4().hex[:8], "check": check_id, "date": day or date.today().isoformat(),
                 "passed": bool(passed), "value": value, "how": how, "detail": str(detail or "")[:300]}
        record["attempts"].append(entry)
        moved = False
        if first_pass and stage.number == record["stage"] and record["stage"] < len(program.stages) \
                and all(self.passed(program.id, c.id) for c in stage.checks):
            record["stage"] += 1
            moved = True
        self._save()
        if first_pass:
            life_events.record(self, "path_check_passed", f"Passed a {program.name} check ({how}): {check.what}",
                               [f"path:{program.id}"], {"path": program.id, "check": check_id, "value": value,
                                                        "how": how})
            self._xp(program, CHECK_XP, f"{program.icon} Check passed", check.what)
        if moved:
            done = program.stages[record["stage"] - 2]
            life_events.record(self, "path_stage_done", f"Finished {program.name} stage {done.number}: {done.name}",
                               [f"path:{program.id}"], {"path": program.id, "stage": done.number})
            self._xp(program, STAGE_XP, f"{program.icon} Stage {done.number} done",
                     f"{done.name}. Next: {program.stages[record['stage'] - 1].name}.")
        entry["stage_done"] = moved
        return entry

    def _xp(self, program: Program, xp: int, title: str, message: str) -> None:
        """XP in the program's skill for the person (nothing without profiles, as in tests)."""
        if self.context is None or getattr(self.context, "profiles", None) is None:
            return
        from core.gamification import SkillWeight, grant_xp

        try:
            grant_xp(self.context, xp, title, message,
                     skill_weights=[SkillWeight(program.skill, xp)] if program.skill else None)
        except Exception:
            log.exception("Paths: XP couldn't be granted")


# ------------------------------------------------------------------ where they are, what's next, how it's going

def stage_of(book: PathBook, program: Program) -> Stage:
    """The stage they're on in a program."""
    record = book.path(program.id) or {"stage": 1}
    return program.stages[max(1, min(record["stage"], len(program.stages))) - 1]


def open_checks(book: PathBook, program: Program) -> list[Check]:
    """The current stage's checks not passed yet, in order."""
    return [c for c in stage_of(book, program).checks if not book.passed(program.id, c.id)]


HOW_TO = {"counted": "time or measure it and tell me the number", "said": "tell me when you've done it"}


def next_step(book: PathBook, program: Program) -> str:
    """Pure logic. What to work on now, and why: start, the first open check and the lesson behind it, or that the
    program is done."""
    if book.path(program.id) is None:
        return f"Say \"start {program.name}\" and how much time you have, and I'll set up your plan."
    stage = stage_of(book, program)
    left = open_checks(book, program)
    if not left:
        return f"You've passed every check in {program.name}. Keep practising what you love; I'll keep the log."
    check = left[0]
    lesson = next((l for l in stage.lessons if check.about and check.about in l.about), stage.lessons[0])
    how = HOW_TO.get(check.how, "show me, and I'll check it")
    if check.how == "counted":
        how += f" (passes at {check.passes_at:g} {check.unit})"
    return (f"{program.name}, stage {stage.number} ({stage.name}): next is \"{check.what}\" ({how}). The lesson for "
            f"it: {lesson.title}. {len(left)} check{'s' if len(left) != 1 else ''} left in this stage.")


def teach(program: Program, lesson: Lesson) -> str:
    """Pure logic. A lesson as MIA says it: the title, each step, the program's extra (guitar's shapes), why, and
    what to watch for."""
    text = f"{lesson.title}. " + " ".join(f"{i}. {s}" for i, s in enumerate(lesson.steps, 1))
    extra = program.extra(lesson) if program.extra else ""
    if extra:
        text += " " + extra
    text += f" Why: {lesson.why}"
    if lesson.watch:
        text += " Watch for: " + " ".join(lesson.watch)
    return text


def _week(today: date) -> tuple[str, str]:
    """Pure logic. This week, Monday to Sunday, as ISO dates."""
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat(), (monday + timedelta(days=6)).isoformat()


def stats(book: PathBook, program: Program, today: Optional[date] = None) -> dict:
    """How a path is going: this week's practice days and minutes against the plan, the streak of days practised
    (today or yesterday keeps it current), total hours, sessions, checks passed (of all), the stage, and the bests
    of the counted checks."""
    today = today or date.today()
    record = book.path(program.id) or {"goal": "", "started": "", "plan": {}, "sessions": [], "attempts": []}
    first, last = _week(today)
    sessions = record["sessions"]
    week = [s for s in sessions if first <= s["date"] <= last]
    days = {s["date"] for s in sessions}
    cursor = today if today.isoformat() in days else today - timedelta(days=1)
    streak = 0
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    every = [c for s in program.stages for c in s.checks]
    bests = {c.id: book.best(program.id, c.id) for c in every
             if c.how == "counted" and book.best(program.id, c.id) is not None}
    stage = stage_of(book, program)
    return {"path": program.id, "name": program.name, "drafted": program.drafted, "started": record["started"],
            "goal": record["goal"], "plan": record["plan"], "stage": stage.number, "stage_name": stage.name,
            "stages": len(program.stages), "week_days": len({s["date"] for s in week}),
            "week_minutes": round(sum(s["minutes"] for s in week), 1), "streak": streak,
            "hours": round(sum(s["minutes"] for s in sessions) / 60, 1), "sessions": len(sessions),
            "checks_passed": sum(1 for c in every if book.passed(program.id, c.id)), "checks": len(every),
            "bests": bests}


def describe_stats(book: PathBook, program: Program, today: Optional[date] = None) -> str:
    """Pure logic. How a path is going, said plainly, and what's next."""
    if book.path(program.id) is None:
        return next_step(book, program)
    s = stats(book, program, today)
    text = (f"{program.name}: stage {s['stage']} of {s['stages']} ({s['stage_name']}). This week: {s['week_days']} "
            f"of {s['plan']['days_a_week']} days, {s['week_minutes']:g} minutes. Streak: {s['streak']} "
            f"day{'s' if s['streak'] != 1 else ''}. {s['hours']:g} hours in all; {s['checks_passed']} of "
            f"{s['checks']} checks passed.")
    if s["bests"]:
        text += " Bests: " + "; ".join(f"{program.check(k)[1].what.split(':')[0]} {v:g} {program.check(k)[1].unit}"
                                       for k, v in s["bests"].items()) + "."
    return text + " " + next_step(book, program)


def check_state(passed: bool, how: str) -> str:
    """Pure logic. A check's state in a few words, for the path's screen (the design canvas, DEC-0113): passed or
    open, and who verifies it: "Passed · MIA heard it", "Open · counted by you", "Open · MIA listens",
    "Open · from your records", "Open · you say when"."""
    if passed:
        return "Passed · " + ("MIA heard it" if how.startswith("heard") else "counted" if how == "counted"
                              else "from your records" if how == "recorded" else "you said so")
    return "Open · " + ("MIA listens" if how.startswith("heard") else "counted by you" if how == "counted"
                        else "from your records" if how == "recorded" else "you say when")


def path_card(book: PathBook, program: Program, today: Optional[date] = None) -> dict:
    """One started path for its screen (web/guitar.html and any path): the stats, what's next, the open checks (how
    each is verified), and for the design canvas (DEC-0113) every check of the current stage with its state, and
    this week's homework in a line."""
    stage = stage_of(book, program)
    homework = _homework(book, program, today or date.today())
    return {"id": program.id, "name": program.name, "icon": program.icon, "stats": stats(book, program, today),
            "next": next_step(book, program),
            "open": [{"id": c.id, "what": c.what, "how": c.how, "about": c.about} for c in open_checks(book, program)],
            "stage_checks": [{"id": c.id, "what": c.what, "how": c.how, "about": c.about,
                              "passed": book.passed(program.id, c.id),
                              "state": check_state(book.passed(program.id, c.id), c.how)} for c in stage.checks],
            "homework": "; ".join(t for t, _n in homework["objectives"][:2]) + " this week."}


# ------------------------------------------------------------------ homework (missions)

def _homework(book: PathBook, program: Program, today: date) -> dict:
    """This week's homework for a path: its occurrence key, name, summary and objectives (practice days, minutes,
    up to three open checks)."""
    first, _last = _week(today)
    stage = stage_of(book, program)
    plan = book.path(program.id)["plan"]
    objectives = [(f"Practise on {plan['days_a_week']} days", float(plan["days_a_week"])),
                  (f"Practise {plan['minutes_a_day'] * plan['days_a_week']} minutes in all",
                   float(plan["minutes_a_day"] * plan["days_a_week"]))]
    objectives += [(f"Pass: {c.what}", 1.0) for c in open_checks(book, program)[:3]]
    return {"key": f"{PREFIX}{program.id}:week:{first}", "name": f"{program.name} homework: {stage.name}",
            "summary": f"This week's practice for stage {stage.number} ({stage.builds}).", "objectives": objectives}


def _progress(book: PathBook, program: Program, texts: list[str], today: date) -> list[float]:
    """Each homework objective's progress from the log: days and minutes this week, and 1 for a check passed."""
    first, last = _week(today)
    week = [s for s in book.path(program.id)["sessions"] if first <= s["date"] <= last]
    checks = {f"Pass: {c.what}": c.id for s in program.stages for c in s.checks}
    out = []
    for text in texts:
        if text.startswith("Practise on"):
            out.append(float(len({s["date"] for s in week})))
        elif text.startswith("Practise"):
            out.append(float(sum(s["minutes"] for s in week)))
        else:
            out.append(1.0 if text in checks and book.passed(program.id, checks[text]) else 0.0)
    return out


def ensure_homework(context, today: Optional[date] = None) -> list:
    """This week's homework mission for each path the signed-in person has started, made once (by MIA), its
    progress brought up to date from the log, completed when all of it's done; recorded checks that reached their
    mark pass first (`sweep()`). Returns the missions."""
    from core.gamification import SkillWeight
    from core.person_settings import person_id

    book, missions = getattr(context, "paths", None), getattr(context, "missions", None)
    if book is None or missions is None:
        return []
    today = today or date.today()
    pid = person_id(context)
    sweep(context)
    out = []
    for path_id in book.started():
        program = program_of(context, path_id)
        if program is None:
            continue
        spec = _homework(book, program, today)
        mission = next((m for m in missions.all_missions() if m.occurrence_key == spec["key"] and m.profile_id == pid),
                       None)
        if mission is None:
            mission = missions.add_mission(
                name=spec["name"], icon=program.icon, summary=spec["summary"], assigned_by="mia",
                mission_type="WEEKLY MISSION", reward_xp=HOMEWORK_XP,
                skill_rewards=[SkillWeight(program.skill, HOMEWORK_XP)] if program.skill else None,
                recurring_kind="weekly", occurrence_key=spec["key"], profile_id=pid)
            for text, target in spec["objectives"]:
                missions.add_objective(mission.mission_id, text, "tally", target)
            mission = missions.get_mission(mission.mission_id)
        if mission.status == "active":
            missions.set_objective_progress(mission.mission_id, _progress(
                book, program, [o.description for o in mission.objectives], today))
            if mission.objectives and all(missions.is_objective_complete(mission.mission_id, i)
                                          for i in range(len(mission.objectives))):
                missions.update_mission(mission.mission_id, status="completed")
        out.append(missions.get_mission(mission.mission_id))
    return out


# ------------------------------------------------------------------ verifying (a verifier, or counted, or said)

def verify(context, program: Program, check_id: str, payload) -> dict:
    """A check verified by its program's verifier from what was sent (a recording, for guitar): the verifier decides
    and the attempt is kept. ValueError for a check that isn't verified that way, or what can't be checked."""
    book = getattr(context, "paths", None)
    if book is None:
        raise ValueError("Learning paths aren't on this MIA.")
    found = program.check(check_id)
    if found is None:
        raise ValueError("There's no such check.")
    _stage, check = found
    if check.how == RECORDED:
        return check_records(context, program, check)
    verifier = program.verifiers.get(check.how)
    if verifier is None:
        raise ValueError("That check is counted or said: tell me how it went.")
    return verifier(context, program, check, payload)


# ------------------------------------------------------------------ recorded: passed from what MIA already keeps

@dataclass(frozen=True)
class Source:
    """A record MIA keeps that can pass a check: what it measures (said back), its unit, and how it's read:
    read(context, since) -> a number from the person's own records since that ISO date, or None when MIA doesn't keep
    that record here."""
    what: str
    unit: str
    read: Callable


def _theirs(entry_profile, context) -> bool:
    """Whether a record is the signed-in person's: stamped with them, or with nobody (records from before people
    were recorded count for everyone, as the stores themselves count them)."""
    from core.person_settings import person_id

    return entry_profile in (None, person_id(context))


def _workouts(context, since: str) -> Optional[list]:
    """The person's workouts since a date, or None without a workout store."""
    store = getattr(context, "workout", None)
    if store is None:
        return None
    return [s for s in store.all_sessions(start_date=since) if _theirs(s.profile_id, context)]


def _tracks(context, since: str) -> Optional[list]:
    """The person's GPS tracks since a date (by the track's own date, else when it was added), or None without
    the store."""
    store = getattr(context, "gps_tracks", None)
    if store is None:
        return None
    return [t for t in store.tracks if (t["stats"].get("date") or t["added"][:10]) >= since]


def _meals(context, since: str) -> Optional[list]:
    """The meals this person has logged as made since a date, or None without a kitchen."""
    store = getattr(context, "kitchen", None)
    if store is None:
        return None
    return [m for m in store.all_meal_log_entries() if m.date >= since and _theirs(m.profile_id, context)]


def _count(rows) -> Optional[float]:
    """Pure logic. How many, or None for no store."""
    return None if rows is None else float(len(rows))


SOURCES: dict[str, Source] = {
    "workouts": Source("workouts logged", "workouts", lambda c, since: _count(_workouts(c, since))),
    "workout_minutes": Source("minutes of workouts logged", "minutes", lambda c, since: (
        None if (w := _workouts(c, since)) is None else float(sum(s.duration_minutes for s in w)))),
    "track_km": Source("kilometres in your GPS tracks", "km", lambda c, since: (
        None if (t := _tracks(c, since)) is None else round(sum(x["stats"]["km"] for x in t), 2))),
    "longest_track_km": Source("your longest GPS track", "km", lambda c, since: (
        None if (t := _tracks(c, since)) is None else max((x["stats"]["km"] for x in t), default=0.0))),
    "meals_cooked": Source("meals you logged as made", "meals", lambda c, since: _count(_meals(c, since))),
    "recipes_cooked": Source("different recipes you've made", "recipes", lambda c, since: (
        None if (m := _meals(c, since)) is None else float(len({x.recipe_id for x in m})))),
}


def measure(context, path_id: str, check: Check) -> Optional[float]:
    """What a recorded check's record says now, counting only since the path started (what came before isn't this
    path's work), or None when MIA doesn't keep that record here."""
    source = SOURCES.get(check.source)
    record = context.paths.path(path_id) if getattr(context, "paths", None) is not None else None
    if source is None or record is None:
        return None
    return source.read(context, record["started"])


def check_records(context, program: Program, check: Check, quiet: bool = False) -> dict:
    """A recorded check read from the person's own records: it passes at the mark, and the attempt says it was
    recorded and from what. Quiet (the sweep): only a pass is kept, so reading the records every day doesn't fill
    the history with misses. Returns {passed, said, stage_done, value}. ValueError when MIA doesn't keep that record
    here."""
    book = context.paths
    source = SOURCES.get(check.source)
    value = measure(context, program.id, check)
    if source is None or value is None:
        raise ValueError(f"I don't keep the record that checks \"{check.what}\" on this MIA.")
    unit = check.unit or source.unit
    passed = value >= check.passes_at
    if not passed:
        if not quiet:
            book.attempt(program, check.id, False, value=value, how=RECORDED, detail=check.source)
        return {"passed": False, "stage_done": False, "value": value,
                "said": (f"Your records show {value:g} {unit} ({source.what}) since you started; it passes at "
                         f"{check.passes_at:g}. I'll pass it myself when they get there.")}
    done = book.attempt(program, check.id, True, value=value, how=RECORDED, detail=check.source)
    said = f"Passed from your records: {check.what} ({value:g} {unit}, {source.what})."
    if done["stage_done"]:
        said += f" That finishes the stage. Next: {stage_of(book, program).name}."
    return {"passed": True, "stage_done": done["stage_done"], "value": value, "said": said}


def sweep(context) -> list[dict]:
    """Every open recorded check on the signed-in person's paths, read from their records; the ones that reached
    their mark pass by themselves (a life event and XP, like any pass). Runs before homework is brought up to date.
    Returns what passed: {path, check, said}."""
    book = getattr(context, "paths", None)
    if book is None:
        return []
    out = []
    for path_id in book.started():
        program = program_of(context, path_id)
        if program is None:
            continue
        for check in open_checks(book, program):
            if check.how != RECORDED:
                continue
            try:
                result = check_records(context, program, check, quiet=True)
            except ValueError:
                continue
            if result["passed"]:
                out.append({"path": path_id, "check": check.id, "said": result["said"]})
    return out


def record_plain(context, program: Program, check: Check, value=None) -> dict:
    """A counted or said check: counted passes when the value reaches the mark; said passes. Returns {passed, said,
    stage_done}. ValueError for a counted one with no number."""
    book = context.paths
    if check.how == "counted":
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"What number did you get? It passes at {check.passes_at:g} {check.unit}.") from None
        passed = value >= check.passes_at
    else:
        value, passed = None, True
    done = book.attempt(program, check.id, passed, value=value, how=check.how)
    if not passed:
        return {"passed": False, "stage_done": False,
                "said": (f"{value:g} {check.unit}: not there yet (it passes at {check.passes_at:g}). Your best is "
                         f"{book.best(program.id, check.id):g}. Slower and cleaner first; try again tomorrow.")}
    said = f"Passed: {check.what}." + (f" {value:g} {check.unit}." if value is not None else "")
    if done["stage_done"]:
        said += f" That finishes the stage. Next: {stage_of(book, program).name}."
    return {"passed": True, "stage_done": done["stage_done"], "said": said}


# ------------------------------------------------------------------ drafting a program for a new interest

DRAFT_PROMPT = """Someone wants to learn or improve at: {interest}
Their goal, in their words: {goal}

Write a learning program for them, the way a good teacher would: stages from where a beginner starts, each with
lessons (clear steps, why it matters, the common mistakes) and skill checks that prove the stage is learned.
A check is either "counted" (a number they measure against a mark, like repetitions in a minute, a time, a distance,
a score; give passes_at and unit), "recorded" (MIA reads it from what she already keeps for them, counted from the
day they start; give passes_at and a source, one of: {sources}), or "said" (they tell you they did it, for what can't
be measured). Prefer recorded when a source fits, then counted.
Be safe and correct; say when something needs a professional or a teacher in person.

What MIA's specialists already know about it (use it, don't contradict it):
{grounding}

Reply with only a JSON object:
{{"name": "short name", "skill": "one of: {skills}", "about": "one sentence",
  "words": ["words someone would use about it"],
  "stages": [3 to 5 of {{"name": "...", "builds": "what it builds",
     "lessons": [1 to 3 of {{"title": "...", "steps": ["..."], "why": "...", "watch": ["..."]}}],
     "checks": [1 to 4 of {{"what": "...", "how": "counted", "recorded" or "said", "passes_at": number,
                            "unit": "...", "source": "..."}}]}}]}}"""


def _slug(text: str, n: int = 24) -> str:
    """Pure logic. Text as an id: lowercase letters, digits and underscores."""
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:n] or "item"


def _ollama(prompt: str) -> str:
    """Asks the local model for a JSON reply (qwen2.5:14b, temperature 0.3); ValueError when it isn't answering."""
    import urllib.request

    body = json.dumps({"model": "qwen2.5:14b", "prompt": prompt, "stream": False, "format": "json",
                       "options": {"temperature": 0.3}}).encode("utf-8")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=600) as answer:
            return json.loads(answer.read()).get("response", "")
    except (OSError, ValueError) as problem:
        raise ValueError(f"My local model isn't answering ({problem}), so I can't plan it right now.") from None


def _drafted_check(check_id: str, c: dict) -> Check:
    """Pure logic. A check from a model's draft: counted and recorded keep their mark (a recorded one its source and
    the source's unit); anything else is said, with no mark."""
    how = c.get("how") if c.get("how") in ("counted", RECORDED) else "said"
    what = str(c.get("what", ""))[:200]
    if how == "said":
        return Check(check_id, what, how)
    mark = float(c.get("passes_at") or 0)
    if how == RECORDED:
        source = str(c.get("source", ""))
        return Check(check_id, what, how, "", mark, SOURCES[source].unit if source in SOURCES else "", source)
    return Check(check_id, what, how, "", mark, str(c.get("unit", ""))[:30])


def program_from_draft(raw: dict, interest: str) -> Program:
    """A program from a model's draft, its ids made in code; ValueError for one whose shape won't do (problems())."""
    name = " ".join(str(raw.get("name") or interest).split())[:40] or "My path"
    pid = _slug(name)
    stages = []
    for n, s in enumerate(raw.get("stages") or [], 1):
        lessons = tuple(Lesson(f"{pid}_{n}_{i}", str(l.get("title", ""))[:80],
                               tuple(str(x)[:400] for x in l.get("steps") or [])[:8], str(l.get("why", ""))[:300],
                               tuple(str(x)[:200] for x in l.get("watch") or [])[:4])
                        for i, l in enumerate(s.get("lessons") or [], 1) if isinstance(l, dict))
        checks = tuple(_drafted_check(f"{pid}_{n}_c{i}", c)
                       for i, c in enumerate(s.get("checks") or [], 1) if isinstance(c, dict))
        stages.append(Stage(n, str(s.get("name", f"Stage {n}"))[:60], str(s.get("builds", ""))[:200], lessons, checks))
    program = Program(pid, name, _slug(str(raw.get("skill") or ""), 40), "🎯", str(raw.get("about", ""))[:200],
                      tuple(str(w).lower()[:30] for w in raw.get("words") or [])[:12] or tuple(interest.lower().split()),
                      tuple(stages[:5]), drafted=True)
    wrong = problems(program)
    if wrong:
        raise ValueError("The plan I drafted didn't hold together (" + "; ".join(wrong[:3]) + "). Ask me again.")
    return program


def draft(context, interest: str, goal: str = "", ask: Optional[Callable[[str], str]] = None) -> Program:
    """Drafts a program for an interest no program covers: the local model writes it from the interest and the
    goal, grounded in her specialists' notes; code checks its shape; it's kept as this person's draft until they
    start it. ValueError when it can't be drafted."""
    from core import specialists

    book = getattr(context, "paths", None)
    if book is None:
        raise ValueError("Learning paths aren't on this MIA.")
    notes = specialists.search(interest, limit=4)
    grounding = "\n".join(f"- {n['title']}: {n['body'][:300]} (sources: {'; '.join(n['sources'])})"
                          for _s, _sid, n in notes) or "(nothing yet)"
    skills = getattr(context, "skills", None)
    names = ", ".join(sorted(s.skill_id for s in skills.all_skills())[:80]) if skills is not None else "music"
    sources = "; ".join(f"{key} ({s.what}, in {s.unit})" for key, s in SOURCES.items())
    reply = (ask or _ollama)(DRAFT_PROMPT.format(interest=interest, goal=goal or "(not said)", grounding=grounding,
                                                 skills=names, sources=sources))
    try:
        raw = json.loads(reply[reply.find("{"): reply.rfind("}") + 1])
    except ValueError:
        raise ValueError("The plan I drafted didn't come through. Ask me again.") from None
    program = program_from_draft(raw, interest)
    if skills is not None and program.skill not in {s.skill_id for s in skills.all_skills()}:
        program = Program(program.id, program.name, "", program.icon, program.about, program.words, program.stages,
                          drafted=True)
    book.keep_draft(program)
    return program


def describe_program(program: Program) -> str:
    """Pure logic. A program in a few lines: its stages and how each is checked."""
    parts = [f"{program.name}" + (" (a plan I drafted for you)" if program.drafted else "") + ":"]
    for s in program.stages:
        parts.append(f"stage {s.number}, {s.name} ({len(s.lessons)} lesson{'s' if len(s.lessons) != 1 else ''}; "
                     f"checks: {'; '.join(c.what for c in s.checks)})")
    return " ".join(parts)
