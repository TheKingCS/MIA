"""MIA putting her own services right and telling Zac after (core/self_repair.py, DEC-0222)."""

from datetime import datetime
from types import SimpleNamespace

from core import self_repair
from core.homeostasis import BACKOFF_AFTER

NOW = datetime(2026, 11, 18, 9, 0)


class _Backend:
    """A stand-in Ollama backend that is or isn't answering."""

    def __init__(self, up):
        """Whether it answers."""
        self.up, self._model = up, "qwen2.5:14b"

    def is_available(self, timeout):
        """Whether it answers."""
        return self.up


class _LLM:
    """A stand-in LLM manager whose wake starts the backend (or doesn't)."""

    def __init__(self, up, wakes=True):
        """Its backend's state and whether a wake works."""
        self.backend, self.wakes, self.woken = _Backend(up), wakes, 0

    def _wake_local(self):
        """Counts the wake and says whether it worked."""
        self.woken += 1
        return self.wakes


def _context(monkeypatch, llm):
    """A context whose model is the stand-in, treated as Ollama on this machine."""
    monkeypatch.setattr(self_repair, "_local_ollama", lambda c: c.llm)
    return SimpleNamespace(llm=llm)


def test_a_stopped_ollama_is_started_and_the_model_reloaded(monkeypatch, tmp_path):
    llm, warmed = _LLM(up=False), []
    done = self_repair.check(_context(monkeypatch, llm), now=NOW, path=tmp_path / "r.json", warm=warmed.append)
    assert llm.woken == 1 and [d["what"] for d in done] == ["ollama", "model"] and warmed == [llm.backend]


def test_a_running_ollama_is_left_alone(monkeypatch, tmp_path):
    llm = _LLM(up=True)
    assert self_repair.check(_context(monkeypatch, llm), now=NOW, path=tmp_path / "r.json") == []
    assert llm.woken == 0


def test_a_failed_start_is_said_plainly_and_nothing_is_reloaded(monkeypatch, tmp_path):
    llm = _LLM(up=False, wakes=False)
    done = self_repair.check(_context(monkeypatch, llm), now=NOW, path=tmp_path / "r.json", warm=lambda b: None)
    assert [d["what"] for d in done] == ["ollama"] and not done[0]["ok"] and "didn't answer" in done[0]["said"]


def test_each_repair_runs_at_most_twice_an_hour(monkeypatch, tmp_path):
    path, llm = tmp_path / "r.json", _LLM(up=False, wakes=False)
    for _ in range(4):
        self_repair.check(_context(monkeypatch, llm), now=NOW, path=path)
    assert llm.woken == self_repair.PER_HOUR


def _scheduler(failures):
    """A stand-in scheduler with one job that has failed `failures` times in a row."""
    job = SimpleNamespace(failures_in_a_row=failures, last_error="LLMUnavailableError: down", due=999.0)
    return SimpleNamespace(_jobs={"world_intel": job}, _clock=lambda: 5.0), job


def test_a_job_that_keeps_failing_is_run_again_once_an_hour(monkeypatch, tmp_path):
    path = tmp_path / "r.json"
    sched, job = _scheduler(BACKOFF_AFTER)
    ctx = _context(monkeypatch, _LLM(up=True))
    done = self_repair.check(ctx, sched, now=NOW, path=path)
    assert job.due == 5.0 and [d["what"] for d in done] == ["job:world_intel"]
    job.due = 999.0
    assert self_repair.check(ctx, sched, now=NOW, path=path) == [] and job.due == 999.0


def test_a_job_that_failed_less_than_backoff_is_left_to_its_schedule(monkeypatch, tmp_path):
    sched, job = _scheduler(BACKOFF_AFTER - 1)
    assert self_repair.check(_context(monkeypatch, _LLM(up=True)), sched, now=NOW, path=tmp_path / "r.json") == []


def test_what_she_did_is_told_once_through_the_gate(monkeypatch, tmp_path):
    path = tmp_path / "r.json"
    self_repair.check(_context(monkeypatch, _LLM(up=False)), now=NOW, path=path, warm=lambda b: None)
    told = self_repair.offer(None, path=path, now=NOW)
    assert len(told) == 1 and told[0].topic == self_repair.TOPIC and "started it again" in told[0].message
    assert self_repair.offer(None, path=path, now=NOW) == []


def test_the_self_repair_job_runs_every_five_minutes_even_while_stopped():
    from core.background_jobs import JOBS
    from core.stop import JOBS_THAT_RUN

    assert ("self_repair", 300, "_check_self_repair") in JOBS and "self_repair" in JOBS_THAT_RUN
