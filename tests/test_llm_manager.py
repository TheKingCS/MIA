"""
tests.test_llm_manager
========================

Unit tests for core.llm_manager. No real Ollama server involved —
urllib.request.urlopen is monkeypatched to a fake so these exercise the
manager/backend's success and graceful-degradation paths in isolation,
same fake-dependency approach as test_reference_library_manager.py's
_FakeConfig.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from core.app_context import AppContext
from core.llm_manager import ChatReply, LLMManager, LLMUnavailableError, OllamaBackend, ToolCall


class _FakeConfig:
    """Minimal stand-in for ConfigManager, just enough for `.get(key, default)`."""

    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


def _make_manager(monkeypatch, urlopen_impl) -> LLMManager:
    monkeypatch.setattr("core.llm_manager.urllib.request.urlopen", urlopen_impl)
    context = AppContext(config=_FakeConfig({}), events=None)
    return LLMManager(context)


def test_generate_returns_model_reply_on_success(monkeypatch):
    def fake_urlopen(request, timeout):
        return _FakeResponse(json.dumps({"response": "hello there"}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    assert manager.generate("hi") == "hello there"


def test_generate_returns_none_when_server_unreachable(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    manager = _make_manager(monkeypatch, fake_urlopen)
    assert manager.generate("hi") is None


def test_generate_returns_none_on_malformed_json(monkeypatch):
    def fake_urlopen(request, timeout):
        return _FakeResponse(b"not json")

    manager = _make_manager(monkeypatch, fake_urlopen)
    assert manager.generate("hi") is None


def test_generate_returns_none_when_ollama_reports_error(monkeypatch):
    def fake_urlopen(request, timeout):
        return _FakeResponse(json.dumps({"error": "model not found"}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    assert manager.generate("hi") is None


def test_is_available_true_when_server_responds(monkeypatch):
    def fake_urlopen(request, timeout):
        return _FakeResponse(b"{}")

    manager = _make_manager(monkeypatch, fake_urlopen)
    assert manager.is_available() is True


def test_is_available_false_when_server_unreachable(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    manager = _make_manager(monkeypatch, fake_urlopen)
    assert manager.is_available() is False


def test_manager_reads_base_url_and_model_from_config(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"response": "ok"}).encode("utf-8"))

    monkeypatch.setattr("core.llm_manager.urllib.request.urlopen", fake_urlopen)
    context = AppContext(
        config=_FakeConfig({"llm.base_url": "http://example.local:1234", "llm.model": "custom-model"}),
        events=None,
    )
    manager = LLMManager(context)
    manager.generate("hi")

    assert seen["url"] == "http://example.local:1234/api/generate"
    assert seen["body"]["model"] == "custom-model"


def test_generate_sends_keep_alive_default_as_bare_int(monkeypatch):
    """
    Regression test: a real ~25s response on this dev machine turned
    out to be Ollama re-loading the model after its default 5-minute
    idle unload — keep_alive must be sent on every request so the
    model stays loaded, see this module's docstring. Also regression
    for a real HTTP 400 hit when this was sent as the string "-1"
    instead of the bare int -1 Ollama's Go duration parser requires.
    """
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"response": "ok"}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    manager.generate("hi")
    assert seen["body"]["keep_alive"] == -1
    assert isinstance(seen["body"]["keep_alive"], int)


def test_generate_sends_temperature_zero_by_default(monkeypatch):
    """
    Regression test: the exact same grounding prompt, byte-for-byte,
    gave a correct answer on one real call and "I don't know" on
    another — Ollama's default temperature isn't 0, so identical
    prompts can genuinely sample different completions. Pinned to 0 by
    default for deterministic, repeatable grounding/tool-calling
    answers; verified against the real server that this actually fixes
    the flip-flopping.
    """
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"response": "ok"}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    manager.generate("hi")
    assert seen["body"]["options"]["temperature"] == 0.0


def test_generate_sends_configured_temperature(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"response": "ok"}).encode("utf-8"))

    monkeypatch.setattr("core.llm_manager.urllib.request.urlopen", fake_urlopen)
    context = AppContext(config=_FakeConfig({"llm.temperature": 0.7}), events=None)
    manager = LLMManager(context)
    manager.generate("hi")
    assert seen["body"]["options"]["temperature"] == 0.7


def test_chat_with_tools_sends_temperature(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"message": {"role": "assistant", "content": "ok"}}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    manager.chat_with_tools([{"role": "user", "content": "hi"}], tools=[])
    assert seen["body"]["options"]["temperature"] == 0.0


def test_generate_sends_configured_keep_alive_duration_string(monkeypatch):
    """A non-numeric keep_alive (e.g. "10m") must stay a string — only numeric-looking values become an int."""
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"response": "ok"}).encode("utf-8"))

    monkeypatch.setattr("core.llm_manager.urllib.request.urlopen", fake_urlopen)
    context = AppContext(config=_FakeConfig({"llm.keep_alive": "10m"}), events=None)
    manager = LLMManager(context)
    manager.generate("hi")
    assert seen["body"]["keep_alive"] == "10m"


def test_chat_with_tools_sends_keep_alive(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"message": {"role": "assistant", "content": "ok"}}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    manager.chat_with_tools([{"role": "user", "content": "hi"}], tools=[])
    assert seen["body"]["keep_alive"] == -1


def test_ollama_backend_raises_llm_unavailable_on_connection_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise OSError("network down")

    monkeypatch.setattr("core.llm_manager.urllib.request.urlopen", fake_urlopen)
    backend = OllamaBackend(base_url="http://localhost:11434", model="llama3.2", keep_alive="-1")

    with pytest.raises(LLMUnavailableError):
        backend.generate("hi", timeout=5.0)


# ----------------------------------------------------------------------
# chat_with_tools / ToolCall / ChatReply
# ----------------------------------------------------------------------

def test_chat_with_tools_returns_plain_content_when_no_tool_called(monkeypatch):
    def fake_urlopen(request, timeout):
        return _FakeResponse(json.dumps({"message": {"role": "assistant", "content": "hello there"}}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    reply = manager.chat_with_tools([{"role": "user", "content": "hi"}], tools=[])
    assert reply == ChatReply(content="hello there", tool_calls=[])


def test_chat_with_tools_parses_tool_calls(monkeypatch):
    def fake_urlopen(request, timeout):
        body = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "add_alarm", "arguments": {"label": "Wake Up", "time": "07:00"}}}
                ],
            }
        }
        return _FakeResponse(json.dumps(body).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    reply = manager.chat_with_tools([{"role": "user", "content": "set an alarm"}], tools=[{"type": "function"}])
    assert reply.tool_calls == [ToolCall(name="add_alarm", arguments={"label": "Wake Up", "time": "07:00"})]


def test_chat_with_tools_returns_none_when_server_unreachable(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    manager = _make_manager(monkeypatch, fake_urlopen)
    assert manager.chat_with_tools([{"role": "user", "content": "hi"}], tools=[]) is None


def test_chat_with_tools_retries_without_tools_on_malformed_content(monkeypatch):
    """
    Regression test: verified against the real Ollama server that
    llama3.2:3b sometimes emits a malformed tool-call-shaped JSON
    string as plain `content` instead of answering normally when tools
    are available but unneeded — chat_with_tools() must retry once
    without tools to recover a clean answer.
    """
    calls = []

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        calls.append(payload)
        if payload.get("tools"):
            return _FakeResponse(
                json.dumps({"message": {"role": "assistant", "content": '{"name": "notes", "parameters": {}}'}}).encode(
                    "utf-8"
                )
            )
        return _FakeResponse(json.dumps({"message": {"role": "assistant", "content": "Notes stores journal entries."}}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    reply = manager.chat_with_tools([{"role": "user", "content": "what does notes do"}], tools=[{"type": "function"}])

    assert reply.content == "Notes stores journal entries."
    assert len(calls) == 2
    assert "tools" in calls[0]
    assert "tools" not in calls[1]


def test_chat_with_tools_does_not_retry_when_content_is_normal_prose(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(1)
        return _FakeResponse(json.dumps({"message": {"role": "assistant", "content": "Just a normal answer."}}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    reply = manager.chat_with_tools([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])

    assert reply.content == "Just a normal answer."
    assert len(calls) == 1


def test_chat_with_tools_does_not_retry_when_json_content_has_no_name_key(monkeypatch):
    """A JSON-shaped answer without a "name" key isn't a hallucinated tool call — don't retry."""
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(1)
        return _FakeResponse(json.dumps({"message": {"role": "assistant", "content": '{"result": 42}'}}).encode("utf-8"))

    manager = _make_manager(monkeypatch, fake_urlopen)
    reply = manager.chat_with_tools([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])

    assert reply.content == '{"result": 42}'
    assert len(calls) == 1
