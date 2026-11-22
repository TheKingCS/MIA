"""
tests.test_degraded_intelligence
==================================

FW-12, the first version's part (REQ-AI-013, REQ-HW-029, DEC-0204): when the chosen local model fails or times out,
the next one the computer has answers and MIA says which; and one model call runs at a time, a conversation before
background work, so his turn waits at most for the one call already running.
"""
import threading
import time
from types import SimpleNamespace

from core import model_queue
from core.llm_manager import LLMManager, LLMUnavailableError, OllamaBackend


class _Config:
    """A config that answers from a dict."""

    def __init__(self, **values):
        """These values, the rest their defaults."""
        self.values = values

    def get(self, key, default=None):
        """A value, or the default."""
        return self.values.get(key, default)


def _manager(answers: dict, installed=("qwen2.5:14b", "qwen2.5:7b"), **config):
    """An LLMManager over a pretend Ollama whose models answer (or fail) as `answers` says."""
    manager = LLMManager(SimpleNamespace(config=_Config(**{"llm.model": "qwen2.5:14b", "llm.start_ollama": False,
                                                           **config})))
    asked = []

    def generate(self, prompt, timeout=None):
        """The pretend model's reply, or unavailable."""
        asked.append(self._model)
        said = answers.get(self._model)
        if said is None:
            raise LLMUnavailableError(f"{self._model} timed out")
        return said

    OllamaBackend.generate, OllamaBackend.installed = generate, lambda self, timeout=3.0: list(installed)
    return manager, asked


def test_when_the_chosen_model_fails_the_next_local_one_answers_and_says_so(monkeypatch):
    """REQ-AI-013: qwen2.5:14b times out, qwen2.5:7b answers, and the level names it."""
    real = (OllamaBackend.generate, getattr(OllamaBackend, "installed"))
    try:
        manager, asked = _manager({"qwen2.5:7b": "a shorter answer"})
        assert manager.generate("hello") == "a shorter answer"
        assert asked == ["qwen2.5:14b", "qwen2.5:7b"] and manager.fell_back == "qwen2.5:7b"
        assert manager.level == "THIS COMPUTER · qwen2.5:7b, the smaller model"
        manager2, _ = _manager({"qwen2.5:14b": "the full answer"})
        assert manager2.generate("hello") == "the full answer" and manager2.fell_back == ""
        assert manager2.level == "THIS COMPUTER"
    finally:
        OllamaBackend.generate, OllamaBackend.installed = real


def test_with_no_smaller_model_or_both_failing_the_turn_fails_as_before():
    """None of the fallback models installed, or the fallback failing too: unavailable (None), only one extra try."""
    real = (OllamaBackend.generate, getattr(OllamaBackend, "installed"))
    try:
        manager, asked = _manager({}, installed=("qwen2.5:14b",))
        assert manager.generate("hello") is None and asked == ["qwen2.5:14b"]
        manager, asked = _manager({}, installed=("qwen2.5:14b", "qwen2.5:7b", "qwen2.5:3b"))
        assert manager.generate("hello") is None and asked == ["qwen2.5:14b", "qwen2.5:7b"]
        manager, asked = _manager({"qwen2.5:7b": "x"}, **{"llm.fallback_models": []})
        assert manager.generate("hello") is None
    finally:
        OllamaBackend.generate, OllamaBackend.installed = real


def test_one_model_call_at_a_time_and_a_conversation_goes_before_waiting_background_work():
    """REQ-HW-029: background calls queued while one runs never go ahead of his turn that arrives after them."""
    order = []
    hold = threading.Event()

    def call(kind, name, first=False):
        """One model call of this kind."""
        with model_queue.as_kind(kind), model_queue.slot():
            order.append(name)
            if first:
                hold.wait(5)

    running = threading.Thread(target=call, args=("background", "bg-running", True))
    running.start()
    while model_queue.status()["running"] != "background":
        time.sleep(0.01)
    waiting = [threading.Thread(target=call, args=("background", f"bg-{i}")) for i in range(3)]
    for t in waiting:
        t.start()
    while len(model_queue.status()["waiting"]) < 3:
        time.sleep(0.01)
    turn = threading.Thread(target=call, args=("conversation", "his turn"))
    turn.start()
    while len(model_queue.status()["waiting"]) < 4:
        time.sleep(0.01)
    assert model_queue.status()["waiting"][0] == "conversation"
    hold.set()
    for t in [running, turn, *waiting]:
        t.join(5)
    assert order[:2] == ["bg-running", "his turn"] and sorted(order[2:]) == ["bg-0", "bg-1", "bg-2"]


def test_a_call_made_inside_another_never_waits_on_itself_and_the_schedule_is_background():
    """Re-entry passes through; the scheduler marks its jobs background; a kind that isn't one is refused."""
    with model_queue.slot():
        with model_queue.slot():
            assert model_queue.status()["running"] == "conversation"
    from core.scheduler import Scheduler

    seen = []
    schedule = Scheduler(clock=lambda: 1000.0)
    schedule.add("tick", 60, lambda: seen.append(model_queue.current_kind()), first_after=0)
    schedule.run_due()
    assert seen == ["background"] and model_queue.current_kind() == "conversation"
    try:
        with model_queue.as_kind("everything"):
            pass
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown kind was accepted")
