"""
core.trade_session
==================

Walking someone through a job or a diagnosis, one step at a time (DEC-0149; the third session beside cooking and
training, core/cooking_session.py, core/training_session.py), shared by every surface: the screen, voice, later the
glasses. The steps come from core/trades.py, never from a model.

- **Where you are**: the step in focus, its phase, and how far through the job.
- **Hold points**: a step with a hold (power proven dead, a layout checked square) can't be passed until the person
  says it's checked. Going on without it is refused, saying what to check.
- **Why and what to watch for**: each step's own, asked any time.
- **Stop rules** (core/trades.STOP_RULES): words that mean one is happening ("I smell gas", "I'm bleeding", "the
  tester beeps") stop the session at once and say what to do instead, whatever else was said.
- **A diagnosis** moves by yes and no from check to check, to a cause (with its fix job when one's written) or to a
  professional and what to tell them.
- **A mission**: a job's phases can become a mission's objectives (core/trade_actions.py, `trade.plan`); a session on that
  job counts each step done toward its phase.

Everything but `TradeStore` is pure logic. The store is personal (core/personal_data.py), sealed at rest (DEC-0126),
and writes through atomic_write_text, so "undo that" can put a session back.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import trades
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "trade_session.json"
WORKING, STOPPED, FINISHED = "working", "stopped", "finished"


@dataclass
class Session:
    """A job or diagnosis being worked: which, where (a step's place in the job, or the check in a diagnosis), the
    holds confirmed, its status and why it stopped, the mission it counts toward, and when it started."""
    item_id: str
    kind: str  # "job" | "diagnosis"
    title: str
    at: int = 0
    check: str = ""
    confirmed: list = field(default_factory=list)
    status: str = WORKING
    stopped: str = ""
    mission_id: str = ""
    result: str = ""
    started: str = ""


def item_of(s: Session):
    """The job or diagnosis a session works (None when it's gone)."""
    trades._loaded()
    return (trades.JOBS if s.kind == "job" else trades.DIAGNOSES).get(s.item_id)


def start(item, now: datetime, mission_id: str = "") -> Session:
    """A new session on a job or a diagnosis, at its first step or check."""
    kind = "diagnosis" if isinstance(item, trades.Diagnosis) else "job"
    return Session(item.id, kind, item.name, check=item.start if kind == "diagnosis" else "",
                   mission_id=mission_id, started=now.isoformat(timespec="seconds"))


def _step(s: Session, job) -> tuple[int, int, trades.Step]:
    """The step in focus: its phase's index, its own index in the phase, and the step."""
    return job.steps()[min(s.at, len(job.steps()) - 1)]


def say(s: Session) -> str:
    """The step or check in focus, said: where it is, what to do, and the hold to verify before going on."""
    item = item_of(s)
    if item is None:
        return "That job isn't there anymore."
    if s.status == STOPPED:
        return f"Stopped: {s.stopped}"
    if s.status == FINISHED:
        return s.result or f"That's {s.title} done."
    if s.kind == "diagnosis":
        return item.check(s.check).ask
    p, _i, step = _step(s, item)
    total = len(item.steps())
    line = f"{item.phases[p].name}, step {s.at + 1} of {total}: {step.do}"
    if step.hold and s.at not in s.confirmed:
        line += f" Before you go on: {step.hold} Say “checked” when it is."
    return line


def why(s: Session) -> str:
    """Why the step (or check) in focus matters."""
    item = item_of(s)
    if item is None or s.status != WORKING:
        return say(s)
    return item.check(s.check).why if s.kind == "diagnosis" else _step(s, item)[2].why


def watch(s: Session) -> str:
    """What to watch for on the step in focus (and its common mistakes)."""
    item = item_of(s)
    if item is None or s.status != WORKING or s.kind == "diagnosis":
        return say(s)
    found = _step(s, item)[2].watch
    return " ".join(found) if found else "Nothing special on this one beyond the usual care."


def confirm(s: Session) -> str:
    """The person says the hold point is checked; says what's next."""
    item = item_of(s)
    if item is None or s.kind != "job" or s.status != WORKING:
        return say(s)
    if not _step(s, item)[2].hold:
        return "There's nothing to check on this step. Say “next” when you're ready."
    if s.at not in s.confirmed:
        s.confirmed.append(s.at)
    return "Checked. Say “next” when you're ready."


def next_step(s: Session) -> tuple[bool, str]:
    """Moves to the next step, unless the one in focus has a hold not yet checked; (moved, what to say). Past the
    last step the job is finished."""
    item = item_of(s)
    if item is None or s.kind != "job" or s.status != WORKING:
        return False, say(s)
    step = _step(s, item)[2]
    if step.hold and s.at not in s.confirmed:
        return False, f"Not yet: {step.hold} Say “checked” once it is."
    if s.at + 1 >= len(item.steps()):
        s.status = FINISHED
        s.result = f"That's every step of {item.name}. Well done."
        return True, s.result
    s.at += 1
    return True, say(s)


def back(s: Session) -> str:
    """One step back (a job), and says it."""
    if s.kind == "job" and s.status == WORKING and s.at > 0:
        s.at -= 1
    return say(s)


def answer(s: Session, yes: bool) -> str:
    """A diagnosis's yes or no: the next check, or where it ends (a cause with its fix job, or a professional)."""
    item = item_of(s)
    if item is None or s.kind != "diagnosis" or s.status != WORKING:
        return say(s)
    target = item.check(s.check).yes if yes else item.check(s.check).no
    if item.check(target) is not None:
        s.check = target
        return say(s)
    s.status = FINISHED
    if target.startswith("cause:"):
        what, _, job = target[6:].partition("|")
        s.result = f"Found it: {what}." + (f" I can walk you through {trades.JOBS[job].name}: say “walk me through "
                                            f"it”." if job and job in trades.JOBS else "")
    else:
        s.result = f"This one's for {target[4:]}."
    return s.result


def stop_for(text: str) -> Optional[trades.StopRule]:
    """Pure logic. The stop rule the words say is happening ("I smell gas", "I'm bleeding"), or None."""
    said = (text or "").lower()
    return next((r for r in trades.STOP_RULES.values() if any(w in said for w in r.words)), None)


def stop(s: Session, rule: Optional[trades.StopRule] = None, why_text: str = "") -> str:
    """Stops the session: for a stop rule, what to do instead; or as the person asked."""
    s.status = STOPPED
    s.stopped = rule.instead if rule is not None else (why_text or "you stopped it. Say “walk me through "
                                                                   f"{s.title.lower()}” to start again.")
    return s.stopped if rule is not None else "Stopped. " + s.stopped


def progress(s: Session) -> dict:
    """Pure logic. How far through the job: {step, of, phase, phase_index}; {} for a diagnosis or a missing job."""
    item = item_of(s)
    if item is None or s.kind != "job":
        return {}
    p, _i, _step_ = _step(s, item)
    return {"step": s.at + 1, "of": len(item.steps()), "phase": item.phases[p].name, "phase_index": p}


class TradeStore:
    """The person's one job or diagnosis in progress (a personal store, core/personal_data.py)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Points at the person's session file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads the session in progress, keeping only the fields it knows; sealed at rest (DEC-0126): one that won't
        open is copied aside, logged, and means none."""
        self.session: Optional[Session] = None
        try:
            raw = json.loads(open_text(self._file)) if self._file.exists() else None
        except (OSError, ValueError):
            log.exception("%s unreadable; no job in progress.", _FILE)
            raw = None
        if raw:
            self.session = Session(**{k: v for k, v in raw.items() if k in Session.__dataclass_fields__})

    def reload(self) -> None:
        """Reads the file again (after undo restored it, or another surface changed it)."""
        self._load()

    def save(self) -> None:
        """Writes the session atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps(asdict(self.session) if self.session else None, indent=1))

    def live(self) -> Optional[Session]:
        """The job or diagnosis being worked now (not one finished or stopped)."""
        return self.session if self.session is not None and self.session.status == WORKING else None

    def begin(self, item, mission_id: str = "", now: Optional[datetime] = None) -> Session:
        """Starts a job or diagnosis (replacing one finished or stopped; ValueError when another is in progress)."""
        live = self.live()
        if live is not None and live.item_id != item.id:
            raise ValueError(f"You're in the middle of {live.title}. Finish it or say “stop the job” first.")
        self.session = start(item, now or datetime.now(), mission_id)
        self.save()
        return self.session
