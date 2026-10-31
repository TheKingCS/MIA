"""
core.training_session
=======================

The live workout session (DEC-0055, docs/ACTIVE_TRAINING_PLAN.md): one
per person, shared by every surface (the PC, the phone, the glasses,
voice), moving set by set through today's training.

- **Prescribed** comes from the fitness plan (`today_training()`: each
  exercise's sets, reps or hold); **performed** is recorded here, set by
  set: the reps (or seconds) actually done, the weight if any, and **how
  the count was made**: `said` (counted aloud, MIA followed), `cadence`
  (MIA counted the pace, the person confirmed the total), `told` (the
  total, said after), `tapped`. None of these is verification, and the
  record never pretends otherwise.
- **Rest starts by itself** after each set (Zac, DEC-0055: yes), the
  exercise's own `rest_seconds` or REST_SECONDS; "skip rest" moves on.
- **MIA counts the pace** (Zac: "count the pace"): `cadence_seconds` per
  rep (the exercise's own, else CADENCE_SECONDS); the phone speaks the
  count locally (no lag), and the confirmed total comes back as a set.
- **Finishing** writes one ordinary `workout_manager` session (sets,
  actual reps, target reps, weights, how counted, real minutes), so XP,
  skills, stats, rewards, personal records and the fitness missions
  follow on their existing paths (DEC-0052: what was performed is the
  workout log's).
- A short set is a set, a skipped exercise is skipped, a pause is a
  pause: nothing is lost or scolded (DEC-0014).

The transitions are pure functions over a `Session` and a `now`; the
`TrainingStore` keeps the one current session in the person's folder
(written through atomic_write_text, so a restart keeps a workout and
"undo that" works).
"""

from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "training_session.json"
REST_SECONDS = 60
CADENCE_SECONDS = 2.0
COUNTED = ("said", "cadence", "told", "tapped")
ACTIVE, RESTING, PAUSED, COMPLETE, FINISHED = "active", "resting", "paused", "complete", "finished"


@dataclass
class Step:
    """One exercise in the session: what's prescribed and what was done."""

    name: str
    sets: int = 1
    reps: Optional[int] = None  # target reps a set
    hold_seconds: Optional[int] = None  # or a hold
    rest_seconds: int = REST_SECONDS
    cadence_seconds: float = CADENCE_SECONDS
    done: list = field(default_factory=list)  # [{reps, seconds, weight, counted, at, rested}]
    skipped: bool = False

    @property
    def complete(self) -> bool:
        return self.skipped or len(self.done) >= max(1, self.sets)


@dataclass
class Session:
    session_id: str
    title: str
    started_at: str
    steps: list = field(default_factory=list)  # Step
    index: int = 0
    status: str = ACTIVE
    rest_until: str = ""
    paused_at: str = ""
    paused_from: str = ""  # the status to go back to on resume
    paused_seconds: float = 0.0
    finished_at: str = ""
    workout_session_id: str = ""  # the workout log it became


def _iso(now: datetime) -> str:
    return now.isoformat(timespec="seconds")


def _at(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(text) if text else None
    except ValueError:
        return None


# ---------------------------------------------------------------- the transitions (pure)


def start(training: dict, now: datetime) -> Session:
    """A session from today's training (`FitnessManager.today_training()`)."""
    steps = []
    for e in training.get("exercises") or []:
        steps.append(Step(
            name=str(e.get("name") or "Exercise"), sets=int(e.get("sets") or 1),
            reps=int(e["reps"]) if e.get("reps") else None,
            hold_seconds=int(e["hold_seconds"]) if e.get("hold_seconds") else None,
            rest_seconds=int(e.get("rest_seconds") or REST_SECONDS),
            cadence_seconds=float(e.get("cadence_seconds") or CADENCE_SECONDS)))
    if not steps:
        raise ValueError("Today's training has no exercises in it yet. Add them in My Plan.")
    return Session(uuid.uuid4().hex[:10], str(training.get("name") or "Today's training"), _iso(now), steps)


def current(s: Session) -> Optional[Step]:
    return s.steps[s.index] if 0 <= s.index < len(s.steps) else None


def _advance(s: Session) -> None:
    """Past finished exercises to the next one with sets left, or complete."""
    while current(s) is not None and current(s).complete:
        s.index += 1
    s.status = COMPLETE if current(s) is None else ACTIVE
    s.rest_until = ""


def settle(s: Session, now: datetime) -> Session:
    """Rest that has run out ends by itself."""
    until = _at(s.rest_until)
    if s.status == RESTING and until is not None and now >= until:
        _record_rest(s, until)  # the whole rest was taken
        _advance(s)
    return s


def log_set(s: Session, now: datetime, reps: Optional[int] = None, seconds: Optional[float] = None,
            weight: Optional[float] = None, counted: str = "told") -> Session:
    """A set done: recorded as performed, then the rest starts by itself
    (none after the session's last set)."""
    settle(s, now)
    if s.status in (FINISHED, COMPLETE):
        raise ValueError("That's the whole workout already. Say \"I'm done\" to wrap it up.")
    if s.status == PAUSED:
        resume(s, now)
    if s.status == RESTING:  # a set done before the rest ran out: the rest ended there
        _record_rest(s, now)
        _advance(s)
    step = current(s)
    if step is not None and step.hold_seconds and reps is not None and seconds is None:
        reps, seconds = None, float(reps)  # "45" on a plank is 45 seconds
    if reps is not None and reps < 0 or seconds is not None and seconds < 0:
        raise ValueError("That count doesn't look right.")
    step.done.append({"reps": reps, "seconds": seconds, "weight": weight,
                      "counted": counted if counted in COUNTED else "told", "at": _iso(now), "rested": None})
    if step.complete and all(st.complete for st in s.steps[s.index + 1:]):
        s.index = len(s.steps)
        s.status, s.rest_until = COMPLETE, ""
        return s
    s.status, s.rest_until = RESTING, _iso(now + timedelta(seconds=step.rest_seconds))
    return s


def skip_rest(s: Session, now: datetime) -> Session:
    if s.status == RESTING:
        _record_rest(s, now)
        _advance(s)
    return s


def _record_rest(s: Session, now: datetime) -> None:
    """How long they actually rested, on the set before it (a 'keep your rest' objective is then real)."""
    step = current(s)
    if step is not None and step.done:
        began = _at(step.done[-1]["at"])
        if began is not None:
            step.done[-1]["rested"] = round((now - began).total_seconds())


def skip_exercise(s: Session, now: datetime) -> Session:
    settle(s, now)
    step = current(s)
    if step is not None:
        step.skipped = True  # any sets already done stay done
    _advance(s)
    return s


def pause(s: Session, now: datetime) -> Session:
    if s.status in (ACTIVE, RESTING):
        s.paused_from, s.paused_at, s.status = s.status, _iso(now), PAUSED
    return s


def resume(s: Session, now: datetime) -> Session:
    began = _at(s.paused_at)
    if s.status == PAUSED and began is not None:
        gap = (now - began).total_seconds()
        s.paused_seconds += gap
        until = _at(s.rest_until)
        if until is not None:  # the rest waits while paused
            s.rest_until = _iso(until + timedelta(seconds=gap))
        s.status, s.paused_at = s.paused_from or ACTIVE, ""
    return s


def correct(s: Session, reps: Optional[int] = None, seconds: Optional[float] = None) -> Session:
    """"Make that 10": the last set logged, wherever it is."""
    for step in reversed(s.steps[: min(s.index, len(s.steps) - 1) + 1]):
        if step.done:
            if reps is not None:
                step.done[-1]["reps"] = reps
            if seconds is not None:
                step.done[-1]["seconds"] = seconds
            return s
    raise ValueError("There's no set to correct yet.")


def elapsed(s: Session, now: datetime) -> float:
    """Seconds of workout, pauses left out."""
    end = _at(s.finished_at) or now
    paused = s.paused_seconds + ((now - _at(s.paused_at)).total_seconds() if s.status == PAUSED and s.paused_at else 0)
    return max(0.0, (end - _at(s.started_at)).total_seconds() - paused)


def rest_left(s: Session, now: datetime) -> Optional[int]:
    until = _at(s.rest_until)
    if s.status != RESTING or until is None:
        return None
    return max(0, math.ceil((until - now).total_seconds() - 1e-6))  # a countdown rounds up: it starts at the full rest


def target_text(step: Step) -> str:
    if step.hold_seconds:
        return f"{step.hold_seconds} seconds"
    return f"{step.reps} reps" if step.reps else "your best"


def view(s: Session, now: datetime) -> dict:
    """What every surface shows: plain values, the words ready."""
    settle(s, now)
    step = current(s)
    if step is not None and step.complete:  # resting after an exercise's last set: what's coming is the next one
        step = next((st for st in s.steps[s.index + 1:] if not st.complete), None)
    later = s.steps[s.steps.index(step) + 1:] if step is not None else []
    upcoming = next((st for st in later if not st.complete), None)
    out = {"id": s.session_id, "title": s.title, "status": s.status, "elapsed": int(elapsed(s, now)),
           "rest_left": rest_left(s, now), "exercises": len(s.steps),
           "done_exercises": sum(1 for st in s.steps if st.complete), "steps": [
               {"name": st.name, "target": target_text(st), "sets": st.sets, "done": len(st.done), "skipped": st.skipped,
                "counts": [d["reps"] if d["reps"] is not None else d["seconds"] for d in st.done]} for st in s.steps]}
    if step is not None:
        last = step.done[-1] if step.done else None
        out["now"] = {"name": step.name, "set": min(len(step.done) + 1, step.sets),  # the set being done, or next
                      "sets": step.sets, "target": target_text(step), "reps": step.reps, "hold_seconds": step.hold_seconds,
                      "cadence_seconds": step.cadence_seconds,
                      "last": (last["reps"] if last["reps"] is not None else last["seconds"]) if last else None}
    out["next"] = upcoming.name if upcoming is not None else None
    return out


def say(s: Session, now: datetime) -> str:
    """One sentence for the voice: where they are."""
    v = view(s, now)
    if s.status == COMPLETE:
        return "That's the whole workout. Say \"I'm done\" to wrap it up."
    if s.status == FINISHED:
        return "The workout's finished."
    n = v.get("now") or {}
    where = f"{n.get('name')}, set {n.get('set')} of {n.get('sets')}, {n.get('target')}."
    if s.status == RESTING:
        return f"Resting: {v['rest_left']} seconds. Then {where}"
    if s.status == PAUSED:
        return f"Paused. Next is {where} Say \"resume\" when you're ready."
    return where


# ---------------------------------------------------------------- counting by voice (pure)

_UNITS = {"zero": 0, "one": 1, "won": 1, "two": 2, "to": 2, "too": 2, "three": 3, "four": 4, "for": 4, "five": 5,
          "six": 6, "seven": 7, "eight": 8, "ate": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
          "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
          "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}


def numbers_heard(text: str) -> list[int]:
    """Pure logic. The numbers in what was heard, in order ("one two
    three", "21", "twenty one"). Sound-alikes count ("to", "for", "ate"):
    the sequence rule in `follow_count` keeps them honest."""
    out: list[int] = []
    words = re.findall(r"\d+|[a-z]+", (text or "").lower())
    i = 0
    while i < len(words):
        w = words[i]
        if w.isdigit():
            out.append(int(w))
        elif w in _TENS:
            n = _TENS[w]
            if i + 1 < len(words) and words[i + 1] in _UNITS and 0 < _UNITS[words[i + 1]] < 10:
                n += _UNITS[words[i + 1]]
                i += 1
            out.append(n)
        elif w in _UNITS:
            out.append(_UNITS[w])
        i += 1
    return out


def follow_count(heard: list[int], start: int = 0) -> int:
    """Pure logic. The count when someone counts aloud: the highest number
    reached *in sequence* from `start`. The next number, or one past it
    (a word missed in the noise), moves it on; a repeat is ignored (no
    double counting); anything else (a misheard "six" after "two", a
    "to" that meant nothing) is ignored."""
    count = start
    for n in heard:
        if n in (count + 1, count + 2):
            count = n
    return count


# ---------------------------------------------------------------- what's said during a workout (pure)

_LEAD = re.compile(r"^(?:hey |ok |okay )?mia[, ]+|^(?:please |ok |okay |alright )+")
_START = re.compile(r"^(?:start|begin|let'?s (?:do|start|begin)|time for)(?: my| today'?s| the)? "
                    r"(?:workout(?: routine)?|training|routine|session|lift)(?: now)?$")
_PAUSE = re.compile(r"^(?:pause|hold on|wait|hang on|take a break)(?: the workout| it| a (?:sec|second|minute))?$")
_RESUME = re.compile(r"^(?:resume|continue|keep going|i'?m back|unpause|back to it)(?: the workout)?$")
_NEXT = re.compile(r"^(?:next(?: set)?|skip (?:the )?rest|i'?m ready|ready|go|let'?s go)$")
_SKIP = re.compile(r"^skip(?: this| that| the)?(?: exercise| one| move)?$")
_FINISH = re.compile(r"^(?:i'?m done|i am done|(?:i'?m )?done for (?:today|the day|now)|finish(?:ed)?(?: my| the)?"
                     r"(?: workout| training| session)?|end(?: the)? workout|that'?s it(?: for today)?|"
                     r"workout (?:done|complete|finished|over)|stop(?: the)? workout)$")
_SAY = re.compile(r"^(?:repeat(?: that)?|say that again|what'?s next|where am i|how am i doing|what set is (?:this|it))$")
_ASK = re.compile(r"^(?:done|set done|that'?s a set|finished(?: that| the)? set|got it)$")
_CORRECT = re.compile(r"^(?:make (?:that|it)|actually|no,? (?:it was|that was|i got)|correction,?) (.+)$")
_COUNT = re.compile(r"^(?:i )?(?:got|did|made|hit|managed|that was|done at|finished at)? ?(.+?)(?: reps?| times)?$")


def parse_training(text: str, status: Optional[str]) -> Optional[tuple[str, dict]]:
    """Pure logic. What a short spoken line means for the workout, given
    the live session's status (None: no workout going): an action kind
    and its params, ("say", {}) to tell them where they are, ("ask", {})
    to ask how many, or None (not about the workout)."""
    said = re.sub(r"[.!?]+$", "", (text or "").lower().replace("’", "'").strip())
    said = _LEAD.sub("", said).strip(" ,")
    if not said or len(said.split()) > 9:
        return None
    if status is None:
        return ("training.start", {}) if _START.match(said) else None
    if _FINISH.match(said):
        return ("training.finish", {})
    if _PAUSE.match(said):
        return ("training.pause", {})
    if _RESUME.match(said):
        return ("training.resume", {})
    if _SAY.match(said):
        return ("say", {})
    if _SKIP.match(said):
        return ("training.skip", {})
    if _NEXT.match(said):
        return ("training.skip_rest", {}) if status == RESTING else ("training.set", {"counted": "tapped"})
    if _ASK.match(said):
        return ("ask", {})
    m = _CORRECT.match(said)
    if m:
        heard = numbers_heard(m.group(1))
        if heard:
            return ("training.correct", {"seconds": heard[-1]} if "second" in m.group(1) else {"reps": heard[-1]})
    m = _COUNT.match(said)
    if m and status in (ACTIVE, RESTING, PAUSED):
        heard = numbers_heard(m.group(1))
        rest = re.sub(r"\d+|\b(?:" + "|".join(list(_UNITS) + list(_TENS)) + r")\b|seconds?|secs?|reps?|and|of them|"
                      r"all|times|[ ,-]", "", m.group(1))
        if heard and not rest and len(heard) <= 2:  # "twelve", "got 12", "45 seconds": nothing else in it
            n = heard[-1]
            return ("training.set", {"seconds": n, "counted": "told"} if "sec" in m.group(1)
                    else {"reps": n, "counted": "told"})
    return None


# ---------------------------------------------------------------- the store


class TrainingStore:
    """The person's one current session (a personal store)."""

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        self.session: Optional[Session] = None
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8")) if self._file.exists() else None
        except (OSError, ValueError):
            log.exception("%s unreadable; no session in progress.", _FILE)
            raw = None
        if raw:
            steps = [Step(**{k: v for k, v in st.items() if k in Step.__dataclass_fields__}) for st in raw.get("steps", [])]
            self.session = Session(**{**{k: v for k, v in raw.items() if k in Session.__dataclass_fields__},
                                      "steps": steps})

    def reload(self) -> None:
        self._load()

    def save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps(asdict(self.session) if self.session else None, indent=1),
                          encoding="utf-8")

    def live(self) -> Optional[Session]:
        """The session in progress (not a finished one)."""
        return self.session if self.session is not None and self.session.status != FINISHED else None

    def begin(self, training: dict, now: Optional[datetime] = None) -> Session:
        if self.live() is not None:
            raise ValueError("A workout is already going. Say \"I'm done\" to finish it first.")
        self.session = start(training, now or datetime.now())
        self.save()
        return self.session

    def finish(self, now: Optional[datetime] = None) -> Optional[str]:
        """The session becomes one workout log; returns its id (None when
        nothing was done, which is simply dropped)."""
        s = self.live()
        if s is None:
            raise ValueError("There's no workout going.")
        now = now or datetime.now()
        if s.status == PAUSED:
            resume(s, now)
        if s.status == RESTING:
            _record_rest(s, now)
        s.finished_at, s.status = _iso(now), FINISHED
        logged = self._sets_logged(s)
        if logged:
            workout = getattr(self.context, "workout", None)
            if workout is not None:
                session = workout.add_session(duration_minutes=round(elapsed(s, now) / 60, 1),
                                              notes=f"{s.title} (live session)", sets_logged=logged)
                s.workout_session_id = session.session_id
        self.save()
        return s.workout_session_id or None

    def _sets_logged(self, s: Session) -> list[dict]:
        workout = getattr(self.context, "workout", None)
        out = []
        for st in s.steps:
            if not st.done:
                continue
            exercise_id = _exercise_id(workout, st.name) if workout is not None else ""
            for n, d in enumerate(st.done, 1):
                out.append({"exercise_id": exercise_id, "set_number": n, "reps": d["reps"] or 0,
                            "weight": d["weight"] or 0.0, "seconds": d["seconds"], "target_reps": st.reps,
                            "target_seconds": st.hold_seconds, "counted": d["counted"], "rested": d["rested"],
                            "name": st.name})
        return out


def _exercise_id(workout, name: str) -> str:
    """The library's exercise with this name, added the first time it's done."""
    wanted = name.strip().lower()
    found = next((e for e in workout.all_exercises() if e.name.strip().lower() == wanted), None)
    return (found or workout.add_exercise(name.strip())).exercise_id
