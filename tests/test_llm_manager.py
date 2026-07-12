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
from core.llm_manager import LLMManager, LLMUnavailableError, OllamaBackend


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


def test_ollama_backend_raises_llm_unavailable_on_connection_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise OSError("network down")

    monkeypatch.setattr("core.llm_manager.urllib.request.urlopen", fake_urlopen)
    backend = OllamaBackend(base_url="http://localhost:11434", model="llama3.2")

    with pytest.raises(LLMUnavailableError):
        backend.generate("hi", timeout=5.0)
