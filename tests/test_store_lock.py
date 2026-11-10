"""
tests.test_store_lock
=======================

The server's store lock (core/store_lock.py, roadmap 2.3): released() lets
go of the locks this thread holds and takes them back; a turn lets go of it
while the model thinks, so another request (here /api/state) answers
meanwhile; and one conversation's turns still run one after another.
"""

from __future__ import annotations

import threading
import time

from fastapi.testclient import TestClient

import server.app as server_app_module
from core.llm_manager import ChatReply, LLMManager
from core.store_lock import StoreLock, conversation_lock, released
from tests.test_server_app import context  # noqa: F401  (the fixture)


def test_released_lets_go_of_the_held_locks_and_takes_them_back():
    first, second = StoreLock(), StoreLock()
    with first, second:
        with released():
            assert not first.locked() and not second.locked()
            got = []
            worker = threading.Thread(target=lambda: got.append(first.acquire(timeout=1) and (first.release() or True)))
            worker.start()
            worker.join()
            assert got == [True]  # another thread could take it meanwhile
        assert first.locked() and second.locked()
    assert not first.locked() and not second.locked()


def test_released_does_nothing_when_no_lock_is_held():
    lock = StoreLock()
    with released():
        assert not lock.locked()
    assert not lock.locked()


def test_one_conversation_s_lock_is_the_same_lock_each_time():
    assert conversation_lock(("me", "c1")) is conversation_lock(("me", "c1"))
    assert conversation_lock(("me", "c1")) is not conversation_lock(("me", "c2"))


class _SlowBackend:
    """A model that waits for the test to let it answer, saying when it has started."""

    def __init__(self):
        """Nothing started, nothing let go."""
        self._model = "slow"
        self.started, self.go = threading.Event(), threading.Event()

    def chat(self, messages, tools, timeout):
        """Says it started, then waits to be let go."""
        self.started.set()
        self.go.wait(10)
        return ChatReply(content="Here you go.")

    def generate(self, prompt, timeout):
        """No extraction from this model."""
        return ""

    def is_available(self, timeout):
        """Always up."""
        return True


def test_another_request_answers_while_the_model_is_thinking(context):  # noqa: F811
    backend = _SlowBackend()
    context.llm = LLMManager(context)
    context.llm.use_backend(backend)
    client = TestClient(server_app_module.create_app(context))
    token = client.post("/api/login", json={"profile_id": "Alice", "password": "hunter2"}).json()["token"]
    auth = {"Authorization": f"Bearer {token}"}
    replies = []
    turn = threading.Thread(target=lambda: replies.append(
        client.post("/api/voice/text", json={"text": "tell me a story about the garden"}, headers=auth).json()))
    turn.start()
    try:
        assert backend.started.wait(10), "the model was never asked"
        began = time.monotonic()
        assert client.get("/api/state", headers=auth).status_code == 200
        assert time.monotonic() - began < 5  # it didn't wait for the model to finish
    finally:
        backend.go.set()
        turn.join(15)
    assert replies and "Here you go." in " ".join(replies[0]["replies"])
