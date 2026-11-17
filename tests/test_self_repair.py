"""MIA putting her own services right and telling Zac after (core/self_repair.py, DEC-0222)."""

from datetime import datetime
from types import SimpleNamespace

from core import self_repair
from core.homeostasis import BACKOFF_AFTER

NOW = datetime(2026, 11, 18, 9, 0)
AT_ONCE = staticmethod(lambda work: work())  # runs the repair's thread work right away, for the tests


class _Backend:
    """A stand-in Ollama backend that is or isn't answering."""

    def __init__(self, up):
        """Whether it answers."""
        self.up, self._model = up, "qwen2.5:14b"

    def is_available(self, timeout):
        """Whether it answers."""
        return self.up


class _LLM:
    """A stand-in LLM manager whose wake starts the backend (or doesn't), with its settings and cooldown."""

    def __init__(self, up, wakes=True, start_ollama=True, last_wake=float("-inf")):
        """Its backend's state, whether a wake works, the start_ollama setting and when a turn last woke it."""
        self.backend, self.wakes, self.woken = _Backend(up), wakes, 0
        self._last_wake = last_wake
        self.context = SimpleNamespace(config=SimpleNamespace(
            get=lambda k, d=None: start_ollama if k == "llm.start_ollama" else d))

    def _wake_local(self):
        """Counts the wake and says whether it worked."""
        self.woken += 1
        return self.wakes


def _context(monkeypatch, llm):
    """A context whose model is the stand-in, treated as Ollama on this machine."""
    monkeypatch.setattr(self_repair, "_local_ollama", lambda c: c.llm)
    self_repair._running.clear()
    return SimpleNamespace(llm=llm)


def _check(ctx, path, scheduler=None, warm=None):
    """One round, with the Ollama repair run at once instead of on its thread."""
    return self_repair.check(ctx, scheduler, now=NOW, path=path, warm=warm or (lambda b: None),
                             start=lambda work: work())


def test_a_stopped_ollama_is_started_and_the_model_reloaded(monkeypatch, tmp_path):
    llm, warmed, path = _LLM(up=False), [], tmp_path / "r.json"
    self_repair.check(_context(monkeypatch, llm), now=NOW, path=path, warm=warmed.append, start=lambda w: w())
    assert llm.woken == 1 and [e["what"] for e in self_repair.load(path)] == ["ollama", "model"]
    assert warmed == [llm.backend]


def test_a_running_ollama_is_left_alone(monkeypatch, tmp_path):
    llm = _LLM(up=True)
    assert _check(_context(monkeypatch, llm), tmp_path / "r.json") == [] and llm.woken == 0


def test_a_failed_start_is_said_plainly_and_nothing_is_reloaded(monkeypatch, tmp_path):
    path = tmp_path / "r.json"
    _check(_context(monkeypatch, _LLM(up=False, wakes=False)), path)
    kept = self_repair.load(path)
    assert [e["what"] for e in kept] == ["ollama"] and not kept[0]["ok"] and "didn't answer" in kept[0]["said"]


def test_she_never_reports_a_start_she_was_not_allowed_to_try(monkeypatch, tmp_path):
    import time

    off = _LLM(up=False, start_ollama=False)
    _check(_context(monkeypatch, off), tmp_path / "a.json")
    cooling = _LLM(up=False, last_wake=time.monotonic())  # a turn just tried
    _check(_context(monkeypatch, cooling), tmp_path / "b.json")
    assert off.woken == cooling.woken == 0
    assert self_repair.load(tmp_path / "a.json") == [] and self_repair.load(tmp_path / "b.json") == []


def test_the_start_runs_on_its_own_thread_and_not_twice_at_once(monkeypatch, tmp_path):
    started = []
    ctx = _context(monkeypatch, _LLM(up=False))
    self_repair.check(ctx, now=NOW, path=tmp_path / "r.json", start=started.append)
    self_repair.check(ctx, now=NOW, path=tmp_path / "r.json", start=started.append)
    assert len(started) == 1  # the first is still "running"
    self_repair._running.clear()


def test_each_repair_runs_at_most_twice_an_hour(monkeypatch, tmp_path):
    path, llm = tmp_path / "r.json", _LLM(up=False, wakes=False)
    for _ in range(4):
        _check(_context(monkeypatch, llm), path)
    assert llm.woken == self_repair.PER_HOUR


def _scheduler(failures):
    """A stand-in scheduler with one job that has failed `failures` times in a row."""
    job = SimpleNamespace(failures_in_a_row=failures, last_error="LLMUnavailableError: down", due=999.0)
    return SimpleNamespace(_jobs={"world_intel": job}, _clock=lambda: 5.0), job


def test_a_job_that_keeps_failing_is_run_again_once_an_hour(monkeypatch, tmp_path):
    path = tmp_path / "r.json"
    sched, job = _scheduler(BACKOFF_AFTER)
    ctx = _context(monkeypatch, _LLM(up=True))
    done = _check(ctx, path, sched)
    assert job.due == 5.0 and [d["what"] for d in done] == ["job:world_intel"]
    job.due = 999.0
    assert _check(ctx, path, sched) == [] and job.due == 999.0


def test_a_job_that_failed_less_than_backoff_is_left_to_its_schedule(monkeypatch, tmp_path):
    sched, _job = _scheduler(BACKOFF_AFTER - 1)
    assert _check(_context(monkeypatch, _LLM(up=True)), tmp_path / "r.json", sched) == []


def test_what_she_did_is_told_once_through_the_gate_and_waits_for_an_opening(monkeypatch, tmp_path):
    from core.communication_gate import TIMELY

    path = tmp_path / "r.json"
    _check(_context(monkeypatch, _LLM(up=False)), path)
    told = self_repair.offer(None, path=path, now=NOW)
    assert len(told) == 1 and told[0].urgency == TIMELY and "started it again" in told[0].message
    assert self_repair.offer(None, path=path, now=NOW) == []


def test_the_self_repair_job_runs_every_five_minutes_even_while_stopped():
    from core.background_jobs import JOBS
    from core.stop import JOBS_THAT_RUN

    assert ("self_repair", 300, "_check_self_repair") in JOBS and "self_repair" in JOBS_THAT_RUN
