"""
core.guitar
=============

MIA teaches guitar (DEC-0111; Zac, 2026-11-07: "I want to learn guitar and would
like for MIA to be able to help teach me as well as track my progress and assign
missions like homework ... being able to verify and test a user's skills just like
it would do for itself"). She learns the way she makes the person learn: a
curriculum in stages, practice that's logged, homework as missions, and skill
checks that have to be passed, not claimed.

**The program** (`STAGES`): five stages, from holding the guitar to lead basics.
Each has lessons (what to do, step by step, why, and the mistakes to watch for;
chord shapes in `CHORDS`) and **skill checks** (`Check`): each one measurable,
with what passes. A check is passed one of three ways, and the record says
which:
- **heard**: MIA listens to a recording (core/guitar_ear.py) and the right notes
  rang (a chord), or the string is in tune;
- **counted**: a number the person measured against the clock or a metronome
  (one-minute chord changes, a tempo held for a minute), at or over the mark;
- **said**: the person says they did it, for what can't be measured yet; it
  counts, and says it was said.
A stage is done when all its checks are passed; the next opens.

**The coach** (`GuitarCoach`, each person's own store, `guitar.json`): their
goal in their own words, how much they mean to practise (minutes a day, days
a week), every practice session (minutes, what they worked on, a tempo), every
check attempt (passed or not, the value, how it was verified), and the stage
they're on. Practice and passed checks are life events; a passed check and a
finished stage earn XP in the Music skill (core/gamification.py).

**Homework** (`ensure_homework()`): each week a mission, assigned by MIA, from
the plan and the current stage: practise on N days, M minutes in all, and one
objective for each check still open. Its progress comes from the log, and it
completes itself when everything's done, the way her fitness missions do
(core/fitness_missions.py).

**Stats** (`stats()`): this week's days and minutes against the plan, the
streak, total hours, checks passed, the bests (chord changes a minute, tempo),
and the stage. `next_step()` says what to work on now and why.

MIA has missions, skills and checks of her own; this is the same machinery
turned toward a person (Zac: "she is essentially using herself the same way
the user is").
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core import life_events
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "guitar.json"
SKILL = "music"  # her skill tree's Music skill (data/skill_definitions.json)
PREFIX = "guitar:"  # the occurrence key of the homework missions
CHECK_XP = 25
STAGE_XP = 100


# ------------------------------------------------------------------ the program

@dataclass(frozen=True)
class Chord:
    """One chord shape: its name, the fret on each string from the low E (6) to the high E (1), x for muted and 0
    for open, the finger on each (1 index to 4 little), and the notes in it."""
    name: str
    frets: str
    fingers: str
    notes: tuple[str, ...]


CHORDS: dict[str, Chord] = {c.name: c for c in (
    Chord("Em", "022000", "023000", ("E", "G", "B")),
    Chord("Am", "x02210", "x02310", ("A", "C", "E")),
    Chord("C", "x32010", "x32010", ("C", "E", "G")),
    Chord("G", "320003", "210003", ("G", "B", "D")),
    Chord("D", "xx0232", "xx0132", ("D", "F#", "A")),
    Chord("E", "022100", "023100", ("E", "G#", "B")),
    Chord("A", "x02220", "x01230", ("A", "C#", "E")),
    Chord("Dm", "xx0231", "xx0231", ("D", "F", "A")),
    Chord("F", "133211", "134211", ("F", "A", "C")),
    Chord("Bm", "x24432", "x13421", ("B", "D", "F#")),
)}


@dataclass(frozen=True)
class Lesson:
    """One lesson: its id and title, the steps to do in order, why it matters, the mistakes to watch for, and the
    chords it teaches."""
    id: str
    title: str
    steps: tuple[str, ...]
    why: str
    watch: tuple[str, ...] = ()
    chords: tuple[str, ...] = ()


@dataclass(frozen=True)
class Check:
    """One skill check: its id, what to do, how it's verified (heard_chord, heard_tuning, counted, said), the chord
    it's about, the mark that passes (for counted ones) and its unit."""
    id: str
    what: str
    how: str
    chord: str = ""
    passes_at: float = 0.0
    unit: str = ""


@dataclass(frozen=True)
class Stage:
    """One stage of the program: its number, name, what it builds, its lessons and the checks that finish it."""
    number: int
    name: str
    builds: str
    lessons: tuple[Lesson, ...]
    checks: tuple[Check, ...]


STAGES: tuple[Stage, ...] = (
    Stage(1, "First sounds", "holding the guitar, tuning it, two chords and steady strumming", (
        Lesson("hold_tune", "Holding it and tuning it", (
            "Sit with the guitar's waist on your right leg (left if you play left-handed), the neck pointing a little "
            "up, your back straight.",
            "The strings, thickest to thinnest, are E A D G B E: 6 is the low E, 1 the high E. Remember them as "
            "\"Eddie Ate Dynamite, Good Bye Eddie\".",
            "Tune every string before you play, every time: pluck it, let MIA hear it (or use any tuner), and turn "
            "its peg until it's in tune. Tune up to the note, not down to it: it holds better.",
            "Press a string just behind a fret (on the side nearer the body), with your fingertip, not the pad."),
            "Practising out of tune teaches your ear the wrong sounds; a guitar in tune makes every chord sound right "
            "the moment your fingers are right.",
            ("Pressing in the middle between frets (buzz) or on top of the fret (dead note).",
             "Squeezing with the thumb: it should rest behind the neck, relaxed.")),
        Lesson("em_am", "Your first chords: E minor and A minor", (
            "E minor: second finger on the 2nd fret of the A string (5), third finger on the 2nd fret of the D "
            "string (4); strum all six strings.",
            "A minor: the same two fingers move down one string each (2nd fret of D and G), and your first finger "
            "goes on the 1st fret of the B string (2); strum from the A string down, not the low E.",
            "Play each one string at a time, slowly: every string should ring. Fix any that doesn't before you strum.",
            "Then switch between them: look at where the fingers go next before you lift them."),
            "These two share a shape: moving between them is the first chord change, and the same move comes back "
            "in dozens of songs.",
            ("A finger leaning on the string below it and muting it: arch your fingers, tips straight down.",
             "Strumming the low E in A minor: it isn't part of the chord."), ("Em", "Am")),
        Lesson("strum_down", "Strumming down, in time", (
            "Set a metronome to 60 beats a minute (MIA can count it, or any metronome app).",
            "Strum down once on every beat: four strums, then four more, without stopping.",
            "Move from the wrist and elbow, loosely; brush the strings, don't dig in.",
            "Keep going when a chord sounds wrong: the beat matters more than the chord right now."),
            "Rhythm is what makes chords into music. A steady down strum is what every pattern later is built on.",
            ("Speeding up or stopping when a change is hard: slow the change, never the beat.",), ()),
    ), (
        Check("tuned", "Tune all six strings; let MIA hear each one", "heard_tuning"),
        Check("em_clean", "Play E minor so every note rings", "heard_chord", chord="Em"),
        Check("am_clean", "Play A minor so every note rings", "heard_chord", chord="Am"),
        Check("changes_em_am", "One-minute changes: E minor to A minor and back, as many as you can in a minute",
              "counted", passes_at=20, unit="changes a minute"),
        Check("strum_60", "Strum down on every beat at 60 bpm for one minute without stopping", "said"),
    )),
    Stage(2, "The open chords", "the five open chords most songs use", (
        Lesson("c_g", "C and G", (
            "C: third finger 3rd fret of the A string, second finger 2nd fret of the D string, first finger 1st fret "
            "of the B string; strum from the A string.",
            "G: second finger 3rd fret of the low E, first finger 2nd fret of the A string, third (or fourth) finger "
            "3rd fret of the high E; strum all six.",
            "Play each string by string until all ring; then one-minute changes between them."),
            "G and C are the two chords you'll play most: together with D they make thousands of songs.",
            ("In C, the first finger touching the high E and muting it.",), ("C", "G")),
        Lesson("d_e_a", "D, E and A", (
            "D: first finger 2nd fret of the G string, third finger 3rd fret of the B string, second finger 2nd fret "
            "of the high E; strum only the top four strings.",
            "E: like E minor, with your first finger added on the 1st fret of the G string.",
            "A: three fingers side by side on the 2nd fret of the D, G and B strings; strum from the A string.",
            "Practise the changes that share fingers first: E minor to E, then A to D."),
            "With these, the open chords are complete: every song in the next stage uses only them.",
            ("Strumming the low strings in D: it muddies the chord.",
             "In A, three fingers crowding one fret: angle them, or try 2-3-4 instead of 1-2-3."), ("D", "E", "A")),
        Lesson("strum_pattern", "The strumming pattern: down, down-up, up-down-up", (
            "Count eight to a bar: 1 and 2 and 3 and 4 and. Down strums land on the numbers, up strums on the ands.",
            "The pattern: down (1), down (2), up (and), up (and of 3), down (4), up (and). Miss the strum on 3 but "
            "keep your hand moving.",
            "Keep your hand moving down and up all the time, like a pendulum; strum or miss the strings, never stop.",
            "Start at 60 bpm on one chord, then two."),
            "This one pattern fits most pop and folk songs, and keeping the hand moving is what keeps time.",
            ("Stopping the hand on the missed strum: it's what throws the rhythm off.",)),
    ), (
        Check("c_clean", "Play C so every note rings", "heard_chord", chord="C"),
        Check("g_clean", "Play G so every note rings", "heard_chord", chord="G"),
        Check("d_clean", "Play D so every note rings", "heard_chord", chord="D"),
        Check("changes_g_c", "One-minute changes: G to C and back", "counted", passes_at=30, unit="changes a minute"),
        Check("changes_d_a", "One-minute changes: D to A and back", "counted", passes_at=30, unit="changes a minute"),
        Check("pattern_70", "The strumming pattern on one chord at 70 bpm for one minute", "counted", passes_at=70,
              unit="bpm"),
    )),
    Stage(3, "Rhythm and first songs", "changing on the beat and playing songs through", (
        Lesson("progression", "G, E minor, C, D: the four-chord song", (
            "Four beats on each: G, E minor, C, D, round and round.",
            "Change on beat 1, every time: if you're late, let the last strum before the change go (strum open "
            "strings) and keep the beat.",
            "Use the pattern from stage 2 once the changes land on time with down strums."),
            "This progression is the backbone of a huge number of songs: when it flows, you can play them.",
            ("Waiting for the fingers before strumming: the beat goes on without them.",), ("G", "Em", "C", "D")),
        Lesson("song", "A whole song, start to finish", (
            "Pick a song you like that uses only open chords (search its name with \"chords\").",
            "Learn it a section at a time: verse, then chorus.",
            "Play it through at a slow tempo, without stopping, even through mistakes.",
            "Record yourself once a week: you'll hear what to fix, and how far you've come."),
            "Finishing songs is what keeps people playing; a song played through badly teaches more than a perfect "
            "verse played alone.", ()),
    ), (
        Check("changes_g_d", "One-minute changes: G to D and back", "counted", passes_at=40, unit="changes a minute"),
        Check("progression_80", "G, Em, C, D at 80 bpm for two minutes, changing on the beat", "counted", passes_at=80,
              unit="bpm"),
        Check("song_through", "Play one whole song through without stopping", "said"),
    )),
    Stage(4, "Barre chords and power chords", "chords that move up the neck", (
        Lesson("power", "Power chords", (
            "Root on the low E string with your first finger, then your third finger two frets up on the A string "
            "(and the fourth on the D string the same fret, if you like). Play only those strings.",
            "Slide the same shape anywhere: the note under your first finger names the chord (3rd fret is G5).",
            "Mute the other strings by letting your fingers touch them lightly."),
            "Power chords are rock and punk's backbone, and the first chord you can move anywhere.", ()),
        Lesson("barre_f", "The F barre chord", (
            "Lay your first finger flat across all six strings at the 1st fret, close to the fret, the bony side "
            "rolled a little toward the headstock.",
            "Make an E shape with the other three fingers in front of it (3rd fret A and D strings, 2nd fret G).",
            "Pull back with your arm rather than squeezing with the thumb; check every string one by one.",
            "It takes weeks for most people: practise it a few minutes a day, never until it hurts."),
            "Barre chords let you play any chord anywhere: one shape, every key.",
            ("Pressing with the soft middle of the first finger: the strings under its creases go dead.",), ("F",)),
    ), (
        Check("f_clean", "Play the F barre chord so every note rings", "heard_chord", chord="F"),
        Check("changes_c_f", "One-minute changes: C to F and back", "counted", passes_at=20, unit="changes a minute"),
    )),
    Stage(5, "Lead basics", "the minor pentatonic scale, picking and bends", (
        Lesson("pentatonic", "The A minor pentatonic, box one", (
            "First finger at the 5th fret; on every string play the 5th fret and one more note: 8th on the two E "
            "strings and the B string, 7th on the A, D and G strings.",
            "Up and down, slowly, alternating down and up picks.",
            "Then with a metronome: two notes a beat (eighth notes), starting at 60 bpm."),
            "This one shape is where most rock and blues solos live.",
            ("Lifting fingers far off the strings: keep them close, ready.",)),
        Lesson("bends", "Bending a string", (
            "Third finger at the 7th fret of the G string, with the first and second fingers behind it on the same "
            "string to help.",
            "Push the string up toward the ceiling until it sounds like the 9th fret (a whole step): play the 9th fret "
            "first to hear the target.",
            "Turn the wrist, like turning a door knob; don't push with the finger alone."),
            "A bend in tune is what makes a solo sing; out of tune is the most common thing that makes it sour.", ()),
    ), (
        Check("pentatonic_80", "A minor pentatonic up and down in eighth notes at 80 bpm, clean", "counted",
              passes_at=80, unit="bpm"),
        Check("bend_in_tune", "Bend the G string at the 7th fret up to the note of the 9th fret, in tune", "said"),
    )),
)

CHECKS: dict[str, tuple[Stage, Check]] = {c.id: (s, c) for s in STAGES for c in s.checks}
LESSONS: dict[str, tuple[Stage, Lesson]] = {l.id: (s, l) for s in STAGES for l in s.lessons}


def shape_text(chord: Chord) -> str:
    """Pure logic. A chord shape said plainly, string by string from the low E: \"E minor: low E open, A 2nd fret
    (finger 2), ...\"."""
    strings = ("low E", "A", "D", "G", "B", "high E")
    parts = []
    for name, fret, finger in zip(strings, chord.frets, chord.fingers):
        if fret == "x":
            parts.append(f"{name} not played")
        elif fret == "0":
            parts.append(f"{name} open")
        else:
            parts.append(f"{name} fret {fret} (finger {finger})")
    return f"{chord.name} ({', '.join(chord.notes)}): " + ", ".join(parts)


def teach(lesson: Lesson) -> str:
    """Pure logic. A lesson as MIA says it: the title, each step, the chord shapes, why, and what to watch for."""
    text = f"{lesson.title}. " + " ".join(f"{i}. {s}" for i, s in enumerate(lesson.steps, 1))
    if lesson.chords:
        text += " Shapes: " + "; ".join(shape_text(CHORDS[c]) for c in lesson.chords if c in CHORDS) + "."
    text += f" Why: {lesson.why}"
    if lesson.watch:
        text += " Watch for: " + " ".join(lesson.watch)
    return text


# ------------------------------------------------------------------ the coach (each person's own)

class GuitarCoach:
    """A person's guitar learning (guitar.json in their own folder, written through atomic_write_text): their goal,
    their practice plan, every practice session and check attempt, and the stage they're on."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads it from the person's folder (or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self._load()

    def _load(self) -> None:
        """Reads it; missing or unreadable is a fresh start (not started)."""
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.goal: str = str(data.get("goal") or "")
        self.started: str = str(data.get("started") or "")
        self.plan: dict = dict(data.get("plan") or {"minutes_a_day": 15, "days_a_week": 5})
        self.sessions: list[dict] = list(data.get("sessions") or [])
        self.attempts: list[dict] = list(data.get("attempts") or [])
        self.stage: int = int(data.get("stage") or 1)

    def _save(self) -> None:
        """Writes it atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"goal": self.goal, "started": self.started, "plan": self.plan,
                                                  "sessions": self.sessions[-3000:], "attempts": self.attempts[-3000:],
                                                  "stage": self.stage}, indent=1, ensure_ascii=False))

    @property
    def is_started(self) -> bool:
        """Whether they've started learning."""
        return bool(self.started)

    def start(self, goal: str = "", minutes_a_day: int = 15, days_a_week: int = 5, today: Optional[date] = None) -> None:
        """Starts (or restarts the plan of) learning: their goal in their own words and how much they mean to
        practise (5 to 120 minutes, 1 to 7 days); a life event the first time."""
        first = not self.started
        self.goal = " ".join(str(goal or self.goal).split())[:300]
        self.plan = {"minutes_a_day": max(5, min(120, int(minutes_a_day or 15))),
                     "days_a_week": max(1, min(7, int(days_a_week or 5)))}
        if first:
            self.started = (today or date.today()).isoformat()
        self._save()
        if first:
            life_events.record(self, "guitar_started", "Started learning guitar" + (f": {self.goal}" if self.goal else ""),
                               [], {"plan": self.plan})

    def log_practice(self, minutes: float, worked_on: str = "", bpm: Optional[float] = None,
                     day: Optional[str] = None) -> dict:
        """Keeps one practice session (minutes over 0, what they worked on, a tempo if they used one); a life event.
        ValueError for no time."""
        minutes = float(minutes or 0)
        if minutes <= 0:
            raise ValueError("How long did you practise?")
        entry = {"id": uuid.uuid4().hex[:8], "date": day or date.today().isoformat(), "minutes": round(minutes, 1),
                 "worked_on": " ".join(str(worked_on or "").split())[:200],
                 "bpm": round(float(bpm), 1) if bpm not in (None, "") else None}
        self.sessions.append(entry)
        self._save()
        life_events.record(self, "guitar_practice", f"Practised guitar {minutes:g} min"
                           + (f": {entry['worked_on']}" if entry["worked_on"] else ""), [],
                           {"minutes": entry["minutes"], "bpm": entry["bpm"]})
        return entry

    def passed(self, check_id: str) -> bool:
        """Whether a check has been passed."""
        return any(a["check"] == check_id and a["passed"] for a in self.attempts)

    def attempt(self, check_id: str, passed: bool, value: Optional[float] = None, how: str = "said",
                detail: str = "", day: Optional[str] = None) -> dict:
        """Keeps one attempt at a check: passed or not, its value, how it was verified (heard, counted, said) and what
        was heard. A first pass is a life event and earns XP; the stage moves on when all its checks are passed
        (another life event, more XP). ValueError for a check that isn't in the program."""
        if check_id not in CHECKS:
            raise ValueError("There's no such check.")
        first_pass = passed and not self.passed(check_id)
        entry = {"id": uuid.uuid4().hex[:8], "check": check_id, "date": day or date.today().isoformat(),
                 "passed": bool(passed), "value": value, "how": how, "detail": str(detail or "")[:300]}
        self.attempts.append(entry)
        stage, check = CHECKS[check_id]
        moved = False
        if first_pass and stage.number == self.stage and all(self.passed(c.id) for c in stage.checks) \
                and self.stage < len(STAGES):
            self.stage += 1
            moved = True
        self._save()
        if first_pass:
            life_events.record(self, "guitar_check_passed", f"Passed a guitar check ({how}): {check.what}",
                               [], {"check": check_id, "value": value, "how": how})
            self._xp(CHECK_XP, "🎸 Check passed", check.what)
        if moved:
            done = STAGES[self.stage - 2]
            life_events.record(self, "guitar_stage_done", f"Finished guitar stage {done.number}: {done.name}", [],
                               {"stage": done.number})
            self._xp(STAGE_XP, f"🎸 Stage {done.number} done", f"{done.name}. Next: {STAGES[self.stage - 1].name}.")
        entry["stage_done"] = moved
        return entry

    def _xp(self, xp: int, title: str, message: str) -> None:
        """XP in the Music skill for the person (nothing without profiles, as in tests)."""
        if self.context is None or getattr(self.context, "profiles", None) is None:
            return
        from core.gamification import SkillWeight, grant_xp

        try:
            grant_xp(self.context, xp, title, message, skill_weights=[SkillWeight(SKILL, xp)])
        except Exception:
            log.exception("Guitar: XP couldn't be granted")

    def best(self, check_id: str) -> Optional[float]:
        """The best value counted for a check (most changes, fastest tempo), or None."""
        values = [a["value"] for a in self.attempts if a["check"] == check_id and a["value"] is not None]
        return max(values) if values else None


# ------------------------------------------------------------------ what's next, and how it's going

def current_stage(coach: GuitarCoach) -> Stage:
    """The stage they're on."""
    return STAGES[max(1, min(coach.stage, len(STAGES))) - 1]


def open_checks(coach: GuitarCoach) -> list[Check]:
    """The current stage's checks not passed yet, in order."""
    return [c for c in current_stage(coach).checks if not coach.passed(c.id)]


def next_step(coach: GuitarCoach) -> str:
    """Pure logic. What to work on now, and why: start, the first open check and the lesson behind it, or that the
    program is done."""
    if not coach.is_started:
        return "Say \"I want to learn guitar\" and how much time you have, and I'll set up your plan."
    stage = current_stage(coach)
    left = open_checks(coach)
    if not left:
        return "You've passed every check in the program. Pick songs you love and keep playing; I'll keep the log."
    check = left[0]
    lesson = next((l for l in stage.lessons if check.chord and check.chord in l.chords), stage.lessons[0])
    how = {"heard_chord": "play it to me and I'll listen", "heard_tuning": "play each string to me",
           "counted": f"time yourself and tell me the number (passes at {check.passes_at:g} {check.unit})",
           "said": "tell me when you've done it"}[check.how]
    return (f"Stage {stage.number}, {stage.name}: next is \"{check.what}\" ({how}). The lesson for it: "
            f"{lesson.title}. {len(left)} check{'s' if len(left) != 1 else ''} left in this stage.")


def _week(today: date) -> tuple[str, str]:
    """Pure logic. This week, Monday to Sunday, as ISO dates."""
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat(), (monday + timedelta(days=6)).isoformat()


def stats(coach: GuitarCoach, today: Optional[date] = None) -> dict:
    """How it's going: this week's practice days and minutes against the plan, the streak of days practised (today
    or yesterday counts as current), total hours, sessions, checks passed (of all), the stage, and the bests."""
    today = today or date.today()
    first, last = _week(today)
    week = [s for s in coach.sessions if first <= s["date"] <= last]
    days = sorted({s["date"] for s in coach.sessions}, reverse=True)
    streak, cursor = 0, today
    if days and days[0] < (today - timedelta(days=1)).isoformat():
        cursor = None
    elif days and days[0] != today.isoformat():
        cursor = today - timedelta(days=1)
    while cursor is not None and cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    bests = {c.id: coach.best(c.id) for s in STAGES for c in s.checks if c.how == "counted" and coach.best(c.id)}
    return {"started": coach.started, "goal": coach.goal, "plan": coach.plan, "stage": current_stage(coach).number,
            "stage_name": current_stage(coach).name, "week_days": len({s["date"] for s in week}),
            "week_minutes": round(sum(s["minutes"] for s in week), 1), "streak": streak,
            "hours": round(sum(s["minutes"] for s in coach.sessions) / 60, 1), "sessions": len(coach.sessions),
            "checks_passed": sum(1 for c in CHECKS if coach.passed(c)), "checks": len(CHECKS), "bests": bests}


def describe_stats(coach: GuitarCoach, today: Optional[date] = None) -> str:
    """Pure logic. How it's going, said plainly."""
    if not coach.is_started:
        return next_step(coach)
    s = stats(coach, today)
    text = (f"Stage {s['stage']} of {len(STAGES)} ({s['stage_name']}). This week: {s['week_days']} of "
            f"{s['plan']['days_a_week']} days, {s['week_minutes']:g} minutes. Streak: {s['streak']} "
            f"day{'s' if s['streak'] != 1 else ''}. {s['hours']:g} hours in all; {s['checks_passed']} of "
            f"{s['checks']} checks passed.")
    if s["bests"]:
        text += " Bests: " + "; ".join(f"{CHECKS[k][1].what.split(':')[0]} {v:g} {CHECKS[k][1].unit}"
                                       for k, v in s["bests"].items()) + "."
    return text + " " + next_step(coach)


# ------------------------------------------------------------------ homework (missions)

def _homework_spec(coach: GuitarCoach, today: date) -> dict:
    """This week's homework: its occurrence key, name and objectives (practice days, minutes, each open check)."""
    first, _last = _week(today)
    stage = current_stage(coach)
    plan = coach.plan
    objectives = [(f"Practise on {plan['days_a_week']} days", float(plan["days_a_week"])),
                  (f"Practise {plan['minutes_a_day'] * plan['days_a_week']} minutes in all",
                   float(plan["minutes_a_day"] * plan["days_a_week"]))]
    objectives += [(f"Pass: {c.what}", 1.0) for c in open_checks(coach)[:3]]
    return {"key": f"{PREFIX}week:{first}", "name": f"Guitar homework: {stage.name}",
            "summary": f"This week's practice for stage {stage.number} ({stage.builds}).", "objectives": objectives}


def _progress(coach: GuitarCoach, spec: dict, today: date) -> list[float]:
    """Each homework objective's progress from the log: days and minutes this week, and 1 for a check passed."""
    first, last = _week(today)
    week = [s for s in coach.sessions if first <= s["date"] <= last]
    out = []
    for text, _target in spec["objectives"]:
        if text.startswith("Practise on"):
            out.append(float(len({s["date"] for s in week})))
        elif text.startswith("Practise"):
            out.append(float(sum(s["minutes"] for s in week)))
        else:
            check = next((c for c in CHECKS.values() if f"Pass: {c[1].what}" == text), None)
            out.append(1.0 if check is not None and coach.passed(check[1].id) else 0.0)
    return out


def ensure_homework(context, today: Optional[date] = None):
    """This week's homework mission for the signed-in person, made once (by MIA) when they've started, its progress
    brought up to date from the log, completed when all of it's done. Returns the mission, or None."""
    from core.gamification import SkillWeight
    from core.person_settings import person_id

    coach, missions = getattr(context, "guitar", None), getattr(context, "missions", None)
    if coach is None or missions is None or not coach.is_started:
        return None
    today = today or date.today()
    pid = person_id(context)
    spec = _homework_spec(coach, today)
    mission = next((m for m in missions.all_missions() if m.occurrence_key == spec["key"] and m.profile_id == pid), None)
    if mission is None:
        mission = missions.add_mission(name=spec["name"], icon="🎸", summary=spec["summary"], assigned_by="mia",
                                       mission_type="WEEKLY MISSION", reward_xp=40,
                                       skill_rewards=[SkillWeight(SKILL, 40)], recurring_kind="weekly",
                                       occurrence_key=spec["key"], profile_id=pid)
        for text, target in spec["objectives"]:
            missions.add_objective(mission.mission_id, text, "tally", target)
        mission = missions.get_mission(mission.mission_id)
    if mission.status == "active":
        texts = [o.description for o in mission.objectives]
        values = _progress(coach, {"objectives": [(t, 0) for t in texts]}, today)
        missions.set_objective_progress(mission.mission_id, values)
        if mission.objectives and all(missions.is_objective_complete(mission.mission_id, i)
                                      for i in range(len(mission.objectives))):
            missions.update_mission(mission.mission_id, status="completed")
    return missions.get_mission(mission.mission_id)


# ------------------------------------------------------------------ listening (a check passed by playing it)

MAX_RECORDING = 8 * 1024 * 1024  # bytes: a few seconds of WAV is plenty


def listen(context, check_id: str, wav: bytes, string: Optional[int] = None) -> dict:
    """A check heard from a recording (core/guitar_ear.py): a chord check passes when every note of the chord rang
    and nothing stray did; the tuning check takes one string at a time (6 is the low E) and passes when all six
    have been heard in tune on the same day. The attempt is kept either way. Returns what was heard and said;
    ValueError for a check that isn't heard, a missing string number, or a recording that can't be heard."""
    import io

    from core import guitar_ear as ear

    coach = getattr(context, "guitar", None)
    if coach is None:
        raise ValueError("Guitar lessons aren't on this MIA.")
    if check_id not in CHECKS:
        raise ValueError("There's no such check.")
    _stage, check = CHECKS[check_id]
    if not check.how.startswith("heard"):
        raise ValueError("That check is counted or said, not heard: tell me how it went.")
    if not wav or len(wav) > MAX_RECORDING:
        raise ValueError("Send a short WAV recording (a few seconds).")
    if check.how == "heard_tuning" and string not in (1, 2, 3, 4, 5, 6):
        raise ValueError("Which string? 6 is the low E, 1 the high E.")
    try:
        samples, rate = ear.read_wav(io.BytesIO(wav))
        if check.how == "heard_chord":
            chord = CHORDS[check.chord]
            heard = ear.hear_chord(ear.chroma(samples, rate), chord.notes)
            done = coach.attempt(check_id, heard["passed"], how="heard",
                                 detail=f"rang {heard['rang']}, missing {heard['missing']}, stray {heard['stray']}")
            return {"check": check_id, "passed": heard["passed"], "heard": heard,
                    "said": ear.describe_chord(chord.name, heard), "stage_done": done["stage_done"]}
        result = ear.tuning(ear.pitch(samples, rate), string)
    except ear.EarError as problem:
        raise ValueError(str(problem)) from None
    today = date.today().isoformat()
    tuned = {int(a["detail"].split(":")[1]) for a in coach.attempts
             if a["check"] == check_id and a["date"] == today and str(a["detail"]).startswith("string:")
             and a["value"] is not None and abs(a["value"]) <= 10}
    if result["in_tune"]:
        tuned.add(string)
    all_six = tuned == {1, 2, 3, 4, 5, 6}
    done = coach.attempt(check_id, all_six, value=result["cents"], how="heard", detail=f"string:{string}")
    if result["in_tune"]:
        said = f"String {string} is in tune ({result['target']})."
    else:
        fix = "loosen it a little" if result["cents"] > 0 else "tighten it a little"
        said = (f"String {string} should be {result['target']}; I hear {result['heard']}, "
                f"{abs(result['cents']):g} cents {'sharp' if result['cents'] > 0 else 'flat'}: {fix}.")
    said += " All six are in tune." if all_six else f" In tune so far today: {len(tuned)} of 6."
    return {"check": check_id, "passed": all_six, "tuning": result, "said": said, "stage_done": done["stage_done"]}


# ------------------------------------------------------------------ by voice

def _coach(context) -> Optional[GuitarCoach]:
    """The person's guitar coach, or None on a MIA without it."""
    return getattr(context, "guitar", None)


def _find_check(words: str, coach: GuitarCoach) -> Optional[Check]:
    """The check the words mean: by id, by the chords named ("G to C"), else the first open one."""
    text = (words or "").lower().replace("e minor", "em").replace("a minor", "am")
    if text in CHECKS:
        return CHECKS[text][1]
    padded = f" {text.replace(',', ' ')} "
    named = [c.lower() for c in CHORDS if f" {c.lower()} " in padded]
    if named:
        for _stage, check in CHECKS.values():
            what = check.what.lower().replace("e minor", "em").replace("a minor", "am")
            if check.how == "counted" and all(f" {n} " in f" {what} " for n in named):
                return check
    if "pentatonic" in text or "scale" in text:
        return CHECKS["pentatonic_80"][1]
    if "song" in text:
        return CHECKS["song_through"][1]
    left = open_checks(coach)
    return left[0] if left else None


def _action_start(context, arguments: dict) -> str:
    """Tool start_guitar: starts learning (their goal in their words, minutes a day, days a week), and the first
    homework."""
    coach = _coach(context)
    if coach is None:
        return "Guitar lessons aren't on this MIA."
    coach.start(str(arguments.get("goal") or ""), int(arguments.get("minutes_a_day") or 15),
                int(arguments.get("days_a_week") or 5))
    ensure_homework(context)
    plan = coach.plan
    return (f"You're set: {plan['minutes_a_day']} minutes a day, {plan['days_a_week']} days a week. Your homework "
            "for this week is in Missions. " + next_step(coach) + " Want the first lesson now?")


def _action_lesson(context, arguments: dict) -> str:
    """Tool guitar_lesson: teaches a lesson (the one named, a chord's shape, or the next one for where they are)."""
    coach = _coach(context)
    if coach is None:
        return "Guitar lessons aren't on this MIA."
    words = str(arguments.get("topic") or "").strip().lower()
    short = words.replace(" chord", "").replace(" minor", "m").replace(" major", "").strip()
    chord = next((c for name, c in CHORDS.items() if short == name.lower()), None) if words else None
    if chord is not None:
        lesson = next((l for _s, l in LESSONS.values() if chord.name in l.chords), None)
        return shape_text(chord) + "." + (f" It's in the lesson \"{lesson.title}\"." if lesson else "")
    lesson = next((l for _s, l in LESSONS.values() if words and words in l.title.lower()), None)
    if lesson is None:
        stage = current_stage(coach)
        left = open_checks(coach)
        lesson = next((l for l in stage.lessons if left and left[0].chord and left[0].chord in l.chords),
                      stage.lessons[0])
    return teach(lesson)


def _action_practice(context, arguments: dict) -> str:
    """Tool log_guitar_practice: keeps a practice session, and says how the week's homework stands."""
    coach = _coach(context)
    if coach is None:
        return "Guitar lessons aren't on this MIA."
    if not coach.is_started:
        return next_step(coach)
    try:
        coach.log_practice(arguments.get("minutes") or 0, str(arguments.get("worked_on") or ""), arguments.get("bpm"))
    except (TypeError, ValueError) as problem:
        return str(problem)
    mission = ensure_homework(context)
    s = stats(coach)
    text = f"Logged. This week: {s['week_days']} of {s['plan']['days_a_week']} days, {s['week_minutes']:g} minutes."
    if mission is not None and mission.status == "completed":
        text += " That finishes this week's homework."
    return text


def _action_check(context, arguments: dict) -> str:
    """Tool guitar_check: a counted or said check ("I did 24 changes G to C"): passed when the number reaches the
    mark (or when said); a heard one asks for a recording."""
    coach = _coach(context)
    if coach is None:
        return "Guitar lessons aren't on this MIA."
    if not coach.is_started:
        return next_step(coach)
    check = _find_check(str(arguments.get("check") or ""), coach)
    if check is None:
        return "Which check? " + next_step(coach)
    if check.how.startswith("heard"):
        return (f"\"{check.what}\" is one I listen to: open the Guitar page (web/guitar.html, on the phone or the web) "
                "and play it, and I'll tell you what I hear.")
    value = arguments.get("value")
    if check.how == "counted":
        try:
            value = float(value)
        except (TypeError, ValueError):
            return f"What number did you get? It passes at {check.passes_at:g} {check.unit}."
        passed = value >= check.passes_at
    else:
        value, passed = None, True
    done = coach.attempt(check.id, passed, value=value, how="counted" if check.how == "counted" else "said")
    ensure_homework(context)
    if not passed:
        return (f"{value:g} {check.unit}: not there yet (it passes at {check.passes_at:g}). Your best is "
                f"{coach.best(check.id):g}. Slow the change down and keep your fingers close; try again tomorrow.")
    text = f"Passed: {check.what}." + (f" {value:g} {check.unit}." if value is not None else "")
    if done["stage_done"]:
        text += f" That finishes the stage. Next: stage {coach.stage}, {current_stage(coach).name}."
    return text + " " + next_step(coach)


def _action_progress(context, arguments: dict) -> str:
    """Tool get_guitar_progress: how it's going (the week against the plan, streak, hours, checks, bests) and what's
    next."""
    coach = _coach(context)
    if coach is None:
        return "Guitar lessons aren't on this MIA."
    ensure_homework(context)
    return describe_stats(coach)


def register_guitar_actions(registry) -> None:
    """Registers the guitar tools: start_guitar, guitar_lesson, log_guitar_practice, guitar_check and
    get_guitar_progress."""
    from core.assistant_actions import AssistantAction

    s = {"type": "string"}
    registry.register(AssistantAction(
        name="start_guitar", domain="guitar",
        description="Start learning guitar: their goal in their own words and how much they can practise; MIA makes "
                    "the plan and the first homework.",
        parameters={"type": "object", "properties": {
            "goal": {**s, "description": "Why they want to play, in their words."},
            "minutes_a_day": {"type": "integer", "description": "Minutes a day, only if they said."},
            "days_a_week": {"type": "integer", "description": "Days a week, only if they said."}}, "required": []},
        handler=_action_start,
        trigger_phrases=("learn guitar", "learn the guitar", "learn to play guitar", "teach me guitar",
                         "start guitar lessons"),
        subjects=("guitar",),
    ))
    registry.register(AssistantAction(
        name="guitar_lesson", domain="guitar",
        description="Teach a guitar lesson or a chord shape: the one named, or the next one for where they are.",
        parameters={"type": "object", "properties": {
            "topic": {**s, "description": "A chord (G, E minor) or lesson, only if they named one."}}, "required": []},
        handler=_action_lesson,
        trigger_phrases=("guitar lesson", "how do i play the", "show me the chord", "next guitar lesson",
                         "chord shape", "how do you play a", "teach me the chord"),
        subjects=("guitar", "chord"),
    ))
    registry.register(AssistantAction(
        name="log_guitar_practice", domain="guitar",
        description="Log a guitar practice session: minutes, what they worked on, a tempo if they used one.",
        parameters={"type": "object", "properties": {
            "minutes": {"type": "number", "description": "How long."},
            "worked_on": {**s, "description": "What they practised."},
            "bpm": {"type": "number", "description": "The metronome tempo, only if they said."}},
            "required": ["minutes"]},
        handler=_action_practice,
        trigger_phrases=("practiced guitar", "practised guitar", "played guitar for", "guitar practice",
                         "minutes of guitar", "practiced my chords", "practised my chords"),
        subjects=("guitar",),
    ))
    registry.register(AssistantAction(
        name="guitar_check", domain="guitar",
        description="Record a guitar skill check they measured or did: one-minute chord changes, a tempo held, a song "
                    "played through.",
        parameters={"type": "object", "properties": {
            "check": {**s, "description": "Which check, e.g. 'G to C changes'."},
            "value": {"type": "number", "description": "The number they got (changes a minute, bpm)."}},
            "required": []},
        handler=_action_check,
        trigger_phrases=("changes in a minute", "chord changes", "one minute changes", "one-minute changes",
                         "guitar check", "played the whole song"),
        subjects=("guitar", "changes"),
    ))
    registry.register(AssistantAction(
        name="get_guitar_progress", domain="guitar",
        description="How their guitar learning is going: the week against the plan, streak, hours, checks passed, "
                    "bests, and what to work on next.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_progress,
        trigger_phrases=("guitar progress", "how's my guitar", "how is my guitar", "my guitar stats",
                         "guitar homework", "how am i doing on guitar"),
        subjects=("guitar",),
    ))
