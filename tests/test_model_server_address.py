"""Tests for LS-08: the model server's address is written in one place (core/llm_manager.py), every module asks
local_server_url() for it, and embeddings and vision go through the backend."""
import json
import re
from pathlib import Path
from types import SimpleNamespace

from core import llm_manager
from core.llm_manager import DEFAULT_SERVER, OllamaBackend, local_server_url

ROOT = Path(__file__).resolve().parent.parent


def test_the_address_is_written_only_in_the_model_manager():
    """No other file in core/, tools/, gui/, server/ or modules/ writes the server's port (os/poc's standalone
    benchmark is outside MIA and stays on its own)."""
    found = []
    for folder in ("core", "tools", "gui", "server", "modules"):
        for path in (ROOT / folder).rglob("*.py"):
            if path.name != "llm_manager.py" and re.search(r"11434", path.read_text(encoding="utf-8")):
                found.append(str(path.relative_to(ROOT)))
    assert found == []


def test_the_setting_moves_the_address_and_localhost_becomes_ipv4():
    """The context's llm.base_url is used, with localhost written as 127.0.0.1 and no trailing slash."""
    config = SimpleNamespace(get=lambda key, default=None: "http://localhost:9999/" if key == "llm.base_url" else default)
    assert local_server_url(SimpleNamespace(config=config)) == "http://127.0.0.1:9999"


def test_a_missing_or_broken_setting_falls_back_to_the_default():
    """An empty setting, or a config that raises, gives the default address."""
    empty = SimpleNamespace(get=lambda key, default=None: "")

    def broken(key, default=None):
        """A config whose read fails."""
        raise RuntimeError("unreadable")

    assert local_server_url(SimpleNamespace(config=empty)) == DEFAULT_SERVER
    assert local_server_url(SimpleNamespace(config=SimpleNamespace(get=broken))) == DEFAULT_SERVER


class _Answer:
    """A fake HTTP response holding one JSON body."""

    def __init__(self, body):
        """Keeps the body to return."""
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        """The body's bytes."""
        return self._body

    def __enter__(self):
        """Itself, as a context manager."""
        return self

    def __exit__(self, *exc):
        """Nothing to close."""
        return False


def test_embed_returns_vectors_or_none_when_the_count_is_wrong(monkeypatch):
    """embed posts to /api/embed on the backend's address and checks one vector per text."""
    seen = []

    def fake(request, timeout=0):
        """Records the request and answers with two vectors."""
        seen.append((request.full_url, json.loads(request.data)))
        return _Answer({"embeddings": [[1.0], [2.0]]})

    monkeypatch.setattr(llm_manager.urllib.request, "urlopen", fake)
    backend = OllamaBackend("http://localhost:5000", "m", "5m")
    assert backend.embed("e", ["a", "b"], 5) == [[1.0], [2.0]]
    assert seen[0][0] == "http://127.0.0.1:5000/api/embed" and seen[0][1] == {"model": "e", "input": ["a", "b"]}
    assert backend.embed("e", ["a"], 5) is None


def test_embed_is_none_when_the_server_is_down(monkeypatch):
    """A server that can't be reached gives None, never an exception."""
    def down(request, timeout=0):
        """Refuses the connection."""
        raise OSError("refused")

    monkeypatch.setattr(llm_manager.urllib.request, "urlopen", down)
    assert OllamaBackend(DEFAULT_SERVER, "m", "5m").embed("e", ["a"], 5) is None


def test_see_sends_the_image_and_returns_the_answer(monkeypatch):
    """see posts the image as base64 to /api/generate with the named vision model."""
    seen = []

    def fake(request, timeout=0):
        """Records the body and answers."""
        seen.append(json.loads(request.data))
        return _Answer({"response": "  a red barn  "})

    monkeypatch.setattr(llm_manager.urllib.request, "urlopen", fake)
    assert OllamaBackend(DEFAULT_SERVER, "m", "5m").see("v", "what is it?", b"img") == "a red barn"
    assert seen[0]["model"] == "v" and seen[0]["images"] == ["aW1n"] and seen[0]["stream"] is False
