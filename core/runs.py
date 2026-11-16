"""
core.runs
===========

One record for anything MIA runs in steps (prompt 23's review, UI-1; DEC-0188;
`docs/mia_os/MIA_OS_UNIVERSAL_INTELLIGENCE_REVIEW.md` sections 3, 6 and 14): a browser routine, a taught skill, a
workflow, later a plan across apps. Three engines already ran steps, each keeping its own state its own way; a
browser routine waiting for his OK kept its place only in the browser's memory, so a restart lost it. This store is
the one place that says what's running, where each run is, what it's waiting for, what it did, and why it stopped,
so "what's running?", the stop (REQ-AUT-010) and recovery read one thing.

**A run** (`RunRecord`): its id, the engine that runs it (`source`: browser_routines, taught_skills, workflows), the
kind and the record it runs (`ref`, like `browser_routine:ab12`), a title, when it started and last changed, its
`status`, the step it's at as a path (`"3"`, or `"2.then.0"` for a workflow's nested step), what it waits for
(`{"kind": commit / signin / ask / you / confirm, "text"}`), each finished step with what she said and the
actions it caused, why it ended, and the engine's own private state (a skill's answers stay in the skill).

**Statuses:** `running` (a step in progress), `waiting` (on the person), `done`, `stopped` (ended early, with why),
`failed` (an error). Only the first two are open.

**After a restart** (`recover`, called the first time the store loads in a process, never on a later reload): a run that was `running` was cut off
mid-step, so it becomes `stopped` with that said, never left looking alive and never called done. A `waiting` run
stays waiting only if its engine keeps the wait across a restart (taught skills do); the others (a browser routine's
held commit lives in the browser) become `stopped` with "run it again from step N".

Each person's own (PERSONAL_STORES), written atomically so "undo" sees it; the finished runs kept are the last
`KEEP_DONE`. Nothing here decides anything: engines write to it, screens and tools read it.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "runs.json"
KEEP_DONE = 200
OPEN = ("running", "waiting")
STATUSES = OPEN + ("done", "stopped", "failed")
SOURCES = ("browser_routines", "taught_skills", "workflows", "plans")
# Engines whose waiting survives a restart of MIA (their own store keeps the wait); others' waits end with it.
WAITS_SURVIVE = frozenset({"taught_skills"})
WAITING_KINDS = ("commit", "signin", "ask", "you", "confirm")
_RECOVERED: set = set()  # run files already recovered in this process


def _now() -> str:
    """Pure logic. Now, to the second."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class RunRecord:
    """One run (see the module's opening)."""
    run_id: str
    source: str  # the engine: browser_routines, taught_skills, workflows, plans
    ref: str  # what it runs, by kind:id
    title: str
    started: str
    updated: str
    status: str = "running"
    at: str = ""  # the step it's at, as a path
    waiting: Optional[dict] = None
    steps: list = field(default_factory=list)  # [{"at", "said", "actions", "when"}]
    why: str = ""  # why it ended, for stopped and failed
    state: dict = field(default_factory=dict)  # the engine's own
    how: str = "observed"  # the engine wrote what it did (DEC-0173)

    @property
    def is_open(self) -> bool:
        """Whether it's still going (running or waiting on the person)."""
        return self.status in OPEN


class RunBook:
    """A person's runs: open ones and the last KEEP_DONE finished, in `runs.json`."""

    # The epistemic contract (DEC-0173, G3): which engine wrote each run, when it started, and that it was observed.
    EPISTEMIC = {"record": RunRecord, "source": "source", "at": "started", "how": "how"}

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the person's runs (or data/'s) and, the first time this file is loaded in a process, recovers any a
        restart cut off (a later rebuild of the store holds runs that are really going)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self._lock = threading.RLock()  # the browser's worker, the scheduler and requests write from their own threads
        self._load()
        key = str(self._file.resolve())
        if key not in _RECOVERED:  # once per file per process: a store rebuilt later (a reload after undo or sync)
            _RECOVERED.add(key)    # holds runs that are really going, not ones a restart cut off
            self.recover()

    def _load(self) -> None:
        """Reads the file; a missing or unreadable one is no runs (sealed at rest: open_text opens it)."""
        self.runs: dict[str, RunRecord] = {}
        try:
            raw = json.loads(open_text(self._file)).get("runs", [])
        except (OSError, ValueError):
            return
        names = {f for f in RunRecord.__dataclass_fields__}
        for item in raw:
            if isinstance(item, dict) and item.get("run_id"):
                try:
                    self.runs[item["run_id"]] = RunRecord(**{k: v for k, v in item.items() if k in names})
                except TypeError:
                    continue

    def _save(self) -> None:
        """Writes atomically, keeping every open run and the newest KEEP_DONE finished ones. Outside "undo that": a
        run is a log of what happened, so undoing the step she just did never erases that the run happened (as
        taught skills' own run log does)."""
        from core.undo_log import outside_undo

        done = sorted((r for r in self.runs.values() if not r.is_open), key=lambda r: r.updated, reverse=True)
        for old in done[KEEP_DONE:]:
            self.runs.pop(old.run_id, None)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with outside_undo():
            atomic_write_text(self._file, json.dumps({"version": 1, "runs": [asdict(r) for r in self.runs.values()]},
                                                     indent=1, ensure_ascii=False))

    # ------------------------------------------------------------------ what engines write

    def start(self, source: str, ref: str, title: str, at: str = "1", state: Optional[dict] = None) -> RunRecord:
        """A new run, running from its first step (or `at`). ValueError for an engine it doesn't know."""
        if source not in SOURCES:
            raise ValueError(f"{source} isn't an engine that runs steps.")
        with self._lock:
            now = _now()
            run = RunRecord(uuid.uuid4().hex[:12], source, ref, " ".join(str(title).split())[:120] or ref, now, now,
                            at=str(at), state=dict(state or {}))
            self.runs[run.run_id] = run
            self._save()
            return run

    def _open(self, run_id: str) -> Optional[RunRecord]:
        """An open run by id, or None (a finished or unknown one is left alone)."""
        run = self.runs.get(run_id or "")
        return run if run is not None and run.is_open else None

    def step(self, run_id: str, at: str, said: str = "", actions=(), next_at: str = "") -> None:
        """A step finished: what she said and the actions it caused; the run moves on (to `next_at` if given)."""
        with self._lock:
            run = self._open(run_id)
            if run is None:
                return
            run.steps.append({"at": str(at), "said": str(said)[:300], "actions": [str(a) for a in actions][:10],
                              "when": _now()})
            run.status, run.waiting, run.updated = "running", None, _now()
            run.at = str(next_at) if next_at else run.at
            self._save()

    def wait(self, run_id: str, at: str, kind: str, text: str, state: Optional[dict] = None) -> None:
        """The run waits on the person at a step (a commit to approve, a sign-in, a question, their own part)."""
        with self._lock:
            run = self._open(run_id)
            if run is None:
                return
            run.status, run.at, run.updated = "waiting", str(at), _now()
            run.waiting = {"kind": kind if kind in WAITING_KINDS else "confirm", "text": str(text)[:300]}
            if state:
                run.state.update(state)
            self._save()

    def finish(self, run_id: str, status: str = "done", why: str = "") -> None:
        """The run ended: done, stopped (with why) or failed (with the error in words)."""
        with self._lock:
            run = self._open(run_id)
            if run is None:
                return
            run.status = status if status in ("done", "stopped", "failed") else "stopped"
            run.why, run.waiting, run.updated = str(why)[:300], None, _now()
            self._save()

    def recover(self) -> list[RunRecord]:
        """After a restart: runs cut off mid-step become stopped, and waits their engine can't keep end too, each
        saying so. Returns the runs it changed."""
        changed = []
        with self._lock:
            for run in self.runs.values():
                if run.status == "running":
                    run.status, run.why = "stopped", f"MIA stopped while step {run.at} was in progress; it may not have finished"
                elif run.status == "waiting" and run.source not in WAITS_SURVIVE:
                    run.status, run.waiting = "stopped", None
                    run.why = f"MIA restarted while waiting for you at step {run.at}; run it again from step {run.at}"
                else:
                    continue
                run.updated = _now()
                changed.append(run)
            if changed:
                self._save()
                log.info("Runs: %d cut off by a restart are marked stopped.", len(changed))
        return changed

    # ------------------------------------------------------------------ what screens and tools read

    def get(self, run_id: str) -> Optional[RunRecord]:
        """A run by id, open or not."""
        return self.runs.get(run_id or "")

    def open_runs(self) -> list[RunRecord]:
        """Everything running or waiting, oldest first."""
        return sorted((r for r in self.runs.values() if r.is_open), key=lambda r: r.started)

    def recent(self, limit: int = 20) -> list[RunRecord]:
        """The latest runs, open or finished, newest first."""
        return sorted(self.runs.values(), key=lambda r: r.updated, reverse=True)[:limit]

    def for_ref(self, ref: str) -> list[RunRecord]:
        """The runs of one thing (a routine, a skill), newest first."""
        return sorted((r for r in self.runs.values() if r.ref == ref), key=lambda r: r.updated, reverse=True)


def book(context) -> Optional[RunBook]:
    """The context's run book, or None (a context without one: old tests, the phone's small MIA)."""
    return getattr(context, "runs", None)


def describe(run: RunRecord) -> str:
    """Pure logic. One run in her words: what, where it is, and what it waits for or why it ended."""
    where = {"running": f"at step {run.at}", "waiting": f"waiting for you at step {run.at}",
             "done": "finished", "stopped": "stopped", "failed": "failed"}[run.status]
    line = f"{run.title}: {where}"
    if run.status == "waiting" and run.waiting:
        line += f" ({run.waiting['text']})"
    elif run.why:
        line += f" ({run.why})"
    return line + "."


def summary(context) -> str:
    """What's running now, and what ended lately, in a few sentences (the list_runs tool)."""
    runs = book(context)
    if runs is None:
        return "I can't see my runs on this device."
    now = runs.open_runs()
    ended = [r for r in runs.recent(5) if not r.is_open]
    if not now and not ended:
        return "Nothing's running, and nothing has run lately."
    parts = []
    if now:
        parts.append("Running now: " + " ".join(describe(r) for r in now))
    else:
        parts.append("Nothing's running now.")
    if ended:
        parts.append("Lately: " + " ".join(describe(r) for r in ended[:3]))
    return " ".join(parts)
