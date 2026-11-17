"""
core.self_repair
==================

MIA puts her own services right when a check fails, and tells Zac after (DEC-0222; Zac, 2026-11-17, Q-77: yes to
"restart her own services, reload a model or re-run a failed job on her own when a check fails, no code or settings
change"). A background job every five minutes (core/background_jobs.py, `self_repair`).

**What she may do, and nothing else** (`check`):
- **Start Ollama** when her model is Ollama on this machine and isn't answering (the same quiet start a turn uses,
  `LLMManager._wake_local`), only when `llm.start_ollama` allows it and outside a turn's own cooldown, so she never
  reports a start that didn't happen; on its own thread, since it waits up to 15 seconds and the desktop's schedule
  runs on the window's thread;
- **reload her model** once Ollama is back: one empty request so the configured model is loaded before he asks,
  on a thread of its own so the schedule isn't held;
- **re-run a job that's backing off** (three failures in a row, core/scheduler.py): due now instead of later, at most
  once an hour each, and at once after Ollama came back.

Never code, never a setting, never a record: each repair is one of those three, at most `PER_HOUR` times an hour
each, and each is kept (`data/self_repairs.json`, this device only). **Telling him** (`offer`): what she did and
whether it worked, through the communication gate, once each.

This file is on the lab's protected list (core/dev_lab.py).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

RECORD = DATA_DIR / "self_repairs.json"
TOPIC = "self_repair"
PER_HOUR = 2  # times each repair may run in an hour
JOB_PER_HOUR = 1  # early re-runs of one job in an hour


def load(path: Optional[Path] = None) -> list[dict]:
    """Every repair kept, oldest first; a missing or unreadable record is none."""
    try:
        data = json.loads(Path(path or RECORD).read_text(encoding="utf-8"))
        return [e for e in data.get("repairs", []) if isinstance(e, dict)]
    except (OSError, ValueError, AttributeError):
        return []


def _save(entries: list[dict], path: Optional[Path] = None) -> None:
    """Writes the record atomically (its last 300 repairs)."""
    from core.atomic_write import atomic_write_text

    path = Path(path or RECORD)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps({"about": "What MIA put right in herself (core/self_repair.py)",
                                        "repairs": entries[-300:]}, indent=1, ensure_ascii=False) + "\n")


def allowed(entries: list[dict], what: str, now: datetime, most: int = PER_HOUR) -> bool:
    """Pure logic. Whether `what` ran fewer than `most` times in the last hour."""
    since = (now - timedelta(hours=1)).isoformat(timespec="seconds")
    return sum(1 for e in entries if e.get("what") == what and e.get("at", "") >= since) < most


def _local_ollama(context):
    """The LLM manager when her model is Ollama on this machine, else None."""
    from core.llm_manager import OllamaBackend, _is_this_machine

    llm = getattr(context, "llm", None)
    backend = getattr(llm, "_backend", None)
    if llm is None or not isinstance(backend, OllamaBackend):
        return None
    return llm if _is_this_machine(getattr(backend, "_base_url", "")) else None


def _warm(backend) -> None:
    """Loads the configured model with one empty request, on a thread of its own; a failure is only logged."""
    import urllib.request

    def run():
        """The request itself."""
        body = json.dumps({"model": backend._model, "keep_alive": backend._keep_alive}).encode("utf-8")
        request = urllib.request.Request(f"{backend._base_url}/api/generate", data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=180):
                pass
        except Exception as problem:  # noqa: BLE001 - the next turn loads it anyway
            log.info("Couldn't reload the model after starting Ollama: %s", problem)
    threading.Thread(target=run, name="mia-warm-model", daemon=True).start()


_LOCK = threading.Lock()  # the record is written from the schedule and from a repair's own thread
_running = threading.Event()  # a repair of Ollama is under way on its thread


def _keep(done: list[dict], path: Optional[Path] = None) -> None:
    """Adds repairs to the record, not yet told."""
    if not done:
        return
    with _LOCK:
        entries = load(path)
        for d in done:
            d["told"] = False
        _save(entries + done, path)


def _may_start(llm) -> bool:
    """Whether starting Ollama is hers to try now: allowed by `llm.start_ollama` and outside the cooldown a turn's own
    start keeps (core/llm_manager.WAKE_COOLDOWN), so she never reports a start that didn't happen."""
    import time

    from core.llm_manager import WAKE_COOLDOWN

    if not llm.context.config.get("llm.start_ollama", True):
        return False
    return time.monotonic() - getattr(llm, "_last_wake", float("-inf")) >= WAKE_COOLDOWN


def _repair_ollama(llm, jobs: dict, clock, at: str, warm, path: Optional[Path]) -> None:
    """Starts Ollama (it waits up to WAKE_WAIT seconds, so this runs on its own thread), reloads the model, makes jobs
    that were failing due again, and keeps what happened."""
    try:
        back = bool(llm._wake_local())
        done = [{"what": "ollama", "at": at, "ok": back,
                 "said": "Ollama had stopped, so I started it again; it's answering." if back else
                 "Ollama had stopped and didn't answer when I started it. Your model can't answer until it does."}]
        if back:
            (warm or _warm)(llm.backend)
            done.append({"what": "model", "at": at, "ok": True,
                         "said": f"I reloaded {getattr(llm.backend, '_model', 'the model')} so it's ready."})
            from core.homeostasis import BACKOFF_AFTER

            for name, job in jobs.items():
                if name != "self_repair" and job.failures_in_a_row >= BACKOFF_AFTER and clock is not None:
                    job.due = clock()  # it may have failed for want of the model
        _keep(done, path)
    except Exception:  # noqa: BLE001 - a repair that fails is only logged
        log.exception("Couldn't put Ollama right")
    finally:
        _running.clear()


def check(context, scheduler=None, now: Optional[datetime] = None, path: Optional[Path] = None,
          warm=None, start=None) -> list[dict]:
    """One round of checks and the repairs they call for (see the module's opening); returns what she did now (a
    start of Ollama runs on its own thread, `start`, and is kept when it's done, so the window never waits for it)."""
    from core.homeostasis import BACKOFF_AFTER

    now = now or datetime.now()
    at = now.isoformat(timespec="seconds")
    with _LOCK:
        entries = load(path)
    done: list[dict] = []
    jobs = getattr(scheduler, "_jobs", {}) if scheduler is not None else {}
    clock = getattr(scheduler, "_clock", None)
    llm = _local_ollama(context)
    if llm is not None and not _running.is_set() and allowed(entries, "ollama", now) and _may_start(llm) \
            and not llm.backend.is_available(timeout=2.0):
        _running.set()
        work = lambda: _repair_ollama(llm, jobs, clock, at, warm, path)  # noqa: E731
        if start is None:
            threading.Thread(target=work, name="mia-self-repair", daemon=True).start()
        else:
            start(work)
    for name, job in jobs.items():
        if name == "self_repair" or job.failures_in_a_row < BACKOFF_AFTER or clock is None:
            continue
        if not allowed(entries + done, f"job:{name}", now, JOB_PER_HOUR):
            continue
        job.due = clock()
        done.append({"what": f"job:{name}", "at": at, "ok": True,
                     "said": f"The {name.replace('_', ' ')} job had failed {job.failures_in_a_row} times in a row "
                             f"({job.last_error[:120]}); I ran it again."})
    _keep(done, path)
    return done


def offer(context, path: Optional[Path] = None, now: Optional[datetime] = None) -> list:
    """What she put right that he hasn't been told yet, as one timely Candidate for the gate (held for an opening,
    never dropped); marked told when offered."""
    from core.communication_gate import TIMELY, Candidate

    with _LOCK:
        entries = load(path)
        fresh = [e for e in entries if e.get("told") is False]
        if not fresh:
            return []
        for e in fresh:
            e["told"] = True
        _save(entries, path)
    when = (now or datetime.now()).isoformat(timespec="minutes")
    return [Candidate(topic=TOPIC, title="I put something right in myself",
                      message=" ".join(e.get("said", "") for e in fresh), source="system", urgency=TIMELY,
                      fingerprint=f"{TOPIC}:{when}")]


def recent(limit: int = 10, path: Optional[Path] = None) -> list[dict]:
    """The newest repairs, newest first, for Diagnostics: [{what, at, ok, said}]."""
    return [{k: e.get(k, "") for k in ("what", "at", "ok", "said")} for e in reversed(load(path)[-limit:])]


def said(limit: int = 5) -> str:
    """Her recent repairs in words, for voice."""
    found = recent(limit)
    if not found:
        return "I haven't had to put anything right in myself lately."
    return "Lately: " + " ".join(f"{e['at'][:16].replace('T', ' ')}: {e['said']}" for e in found)
