"""
core.llm_manager
==================

The Assistant's LLM backend core service — docs/ROADMAP.md milestone
5.1. Defines a small backend-agnostic interface (`LLMBackend`) with one
concrete implementation, `OllamaBackend`, talking to a local Ollama
server's HTTP API (https://github.com/ollama/ollama/blob/main/docs/api.md).

Built on stdlib `urllib.request` rather than the `requests` package —
this is a single local JSON endpoint, and requirements.txt stays light
per this project's design principles (see CLAUDE.md). Ollama is also
the runtime the real Pi 5 + AI HAT+2 deployment uses (Hailo's own
`hailo-ollama`), so moving from dev (this class against
localhost:11434) to prod is a base_url/model config change, not a
backend rewrite.

Neither `ollama` itself nor a pulled model is assumed to exist in every
dev environment, and a kiosk device's assistant server can be down or
still starting at any time — so `LLMManager` never lets a connection
failure or missing model crash the caller. Every public method here
catches `LLMUnavailableError` and returns None/False, logging instead.
Same defensive-degrade pattern as a missing/corrupt `.zim` pack in
core/reference_library_manager.py.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional, Protocol

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2"
_DEFAULT_TIMEOUT_SECONDS = 30.0


class LLMUnavailableError(RuntimeError):
    """Raised by a backend when the LLM server can't be reached or errors."""


class LLMBackend(Protocol):
    """Backend-agnostic interface a concrete LLM client must implement."""

    def generate(self, prompt: str, timeout: float) -> str:
        """Return the model's full reply, or raise LLMUnavailableError."""
        ...

    def is_available(self, timeout: float) -> bool:
        """Cheap reachability check. Never raises."""
        ...


class OllamaBackend:
    """LLMBackend implementation for a local Ollama server."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def generate(self, prompt: str, timeout: float) -> str:
        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            raise LLMUnavailableError(f"Could not reach Ollama at {self._base_url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError(f"Ollama returned malformed JSON: {exc}") from exc

        if "error" in body:
            raise LLMUnavailableError(f"Ollama returned an error: {body['error']}")
        try:
            return body["response"]
        except KeyError as exc:
            raise LLMUnavailableError(f"Ollama response missing 'response' field: {body}") from exc

    def is_available(self, timeout: float) -> bool:
        request = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout):
                return True
        except (urllib.error.URLError, OSError):
            return False


class LLMManager:
    """
    Core-level Assistant LLM service (`AppContext.llm`). Config-driven
    via `llm.base_url` / `llm.model` / `llm.timeout_seconds`, following
    the `modules.<id>.*` / top-level-service config convention
    CLAUDE.md documents.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        base_url = context.config.get("llm.base_url", _DEFAULT_BASE_URL)
        model = context.config.get("llm.model", _DEFAULT_MODEL)
        timeout = context.config.get("llm.timeout_seconds", _DEFAULT_TIMEOUT_SECONDS)
        self._timeout = float(timeout)
        self._backend: LLMBackend = OllamaBackend(base_url, model)

    def is_available(self) -> bool:
        """Cheap reachability check for surfacing an "assistant unavailable" state. Never raises."""
        return self._backend.is_available(timeout=self._timeout)

    def generate(self, prompt: str) -> Optional[str]:
        """Return the model's reply, or None (logged) if the backend can't be reached."""
        try:
            return self._backend.generate(prompt, timeout=self._timeout)
        except LLMUnavailableError as exc:
            log.warning("Assistant unavailable: %s", exc)
            return None
