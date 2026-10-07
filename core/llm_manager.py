"""
core.llm_manager
==================

The Assistant's LLM backend core service — docs/ROADMAP.md milestone
5.1. Defines a small backend-agnostic interface (`LLMBackend`) with one
concrete implementation, `OllamaBackend`, talking to a local Ollama
server's HTTP API (https://github.com/ollama/ollama/blob/main/docs/api.md),
and a second, `OpenAIBackend` (2026-10-07), for llama.cpp's server on
the phone (`llm.backend: "openai"`).

Built on stdlib `urllib.request` rather than the `requests` package —
this is a single local JSON endpoint, and requirements.txt stays light
per this project's design principles (see CLAUDE.md). `docs/HARDWARE.md`
documents Hailo's own `hailo-ollama` as the intended real Pi 5 + AI
HAT+2 runtime, which *would* make prod a base_url/model config change
rather than a backend rewrite — but whether it's actually Ollama-API-
compatible for tool-calling specifically, on the real Hailo-10H
hardware, is **unverified** (see `docs/KNOWN_ISSUES.md`'s open "AI
HAT+2 inference path unconfirmed" item). Don't take this docstring's
framing as more settled than that until it's actually been tested
against real hardware — this dev sandbox only ever runs against
generic CPU Ollama.

Neither `ollama` itself nor a pulled model is assumed to exist in every
dev environment, and a kiosk device's assistant server can be down or
still starting at any time — so `LLMManager` never lets a connection
failure or missing model crash the caller. Every public method here
catches `LLMUnavailableError` and returns None/False, logging instead.
Same defensive-degrade pattern as a missing/corrupt `.zim` pack in
core/reference_library_manager.py.

`chat_with_tools()` (docs/ROADMAP.md milestone 5.5) is the tool-calling
half — Ollama's `/api/chat` endpoint, not `/api/generate` — used by
core/assistant_actions.py's action registry so the Assistant can
perform ordinary app actions, not just answer questions. Verified
against the real Ollama server (llama3.2:3b) that this model sometimes
emits a malformed tool-call-shaped JSON string as plain `content`
instead of either calling a tool or answering normally, when tools are
available but the query doesn't actually need one —
`_looks_like_malformed_tool_call()` detects this and `chat_with_tools()`
retries once without tools to get a clean textual answer instead.

`_DEFAULT_TIMEOUT_SECONDS` was bumped 30 -> 60 after a real cold
model-load request (first request after the model goes idle) exceeded
30s on this CPU-only dev machine — worth remembering if the Assistant
seems to "hang" right after Ollama restarts or an idle period.

`keep_alive` (docs/ROADMAP.md milestone 5.5 follow-up): measured a
real ~25s response on this CPU-only dev machine that turned out to be
almost entirely Ollama re-loading the model from disk, not inference —
by default Ollama unloads a model after 5 minutes idle
(`OLLAMA_KEEP_ALIVE`), so any real conversation with pauses longer than
that pays this cold-load cost on every next message, which reads as
"the Assistant is really slow" even though a warm request completes in
under 2s. Sent on every request here (config key `llm.keep_alive`,
default `"-1"` = keep loaded indefinitely) rather than relying on the
Ollama server's own environment config, so this fix travels with the
app regardless of how/where Ollama is deployed. `"-1"` is a reasonable
default specifically because this is a dedicated single-purpose kiosk
device, not a shared multi-model workstation — the ~2GB held for
llama3.2 isn't competing with anything else that needs it, and the AI
HAT+2's dedicated onboard RAM (docs/HARDWARE.md) means this doesn't
even compete with the Pi's own system RAM on the real target hardware.

`temperature` (docs/ROADMAP.md milestone 5.6 follow-up): default 0.0,
sent as `options.temperature` on every request. Found by chasing what
looked like a wording/dilution bug in device_help_manager.py's
grounding — the exact same prompt, byte-for-byte, gave a correct answer
on one run and "I don't know" on another. Ollama's default temperature
isn't 0, so identical prompts can genuinely sample different completions;
for a grounding/factual-QA/tool-calling assistant, deterministic,
repeatable answers matter far more than creative variation, so this is
pinned to 0 rather than left at Ollama's default. Verified directly
against the real server: the exact prompt that flip-flopped between
correct and "I don't know" across separate calls became reliably
correct, identically, across repeated calls once temperature was 0.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional, Protocol

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2"
_DEFAULT_TIMEOUT_SECONDS = 60.0
_DEFAULT_KEEP_ALIVE = "-1"
_DEFAULT_TEMPERATURE = 0.0


class LLMUnavailableError(RuntimeError):
    """Raised by a backend when the LLM server can't be reached or errors."""


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class ChatReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMBackend(Protocol):
    """Backend-agnostic interface a concrete LLM client must implement."""

    def generate(self, prompt: str, timeout: float) -> str:
        """Return the model's full reply, or raise LLMUnavailableError."""
        ...

    def chat(self, messages: list[dict], tools: list[dict], timeout: float) -> ChatReply:
        """Return a ChatReply (content and/or tool_calls), or raise LLMUnavailableError."""
        ...

    def is_available(self, timeout: float) -> bool:
        """Cheap reachability check. Never raises."""
        ...


class OllamaBackend:
    """LLMBackend implementation for a local Ollama server."""

    def __init__(self, base_url: str, model: str, keep_alive: str, temperature: float = _DEFAULT_TEMPERATURE) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        # Ollama's keep_alive must be a bare JSON number of seconds
        # (e.g. -1 to never unload) OR a Go duration *string* with a
        # unit suffix (e.g. "30m") — a quoted "-1" is rejected with
        # HTTP 400 ("missing unit in duration"), confirmed against the
        # real server. Config stores this as a string either way
        # (JSON has no bare-int-or-string union type), so normalize
        # once here: numeric-looking strings become a real int.
        try:
            self._keep_alive: object = int(keep_alive)
        except (TypeError, ValueError):
            self._keep_alive = keep_alive

    def generate(self, prompt: str, timeout: float) -> str:
        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": {"temperature": self._temperature},
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

    def chat(self, messages: list[dict], tools: list[dict], timeout: float) -> ChatReply:
        payload_dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": {"temperature": self._temperature},
        }
        if tools:
            payload_dict["tools"] = tools
        payload = json.dumps(payload_dict).encode("utf-8")

        request = urllib.request.Request(
            f"{self._base_url}/api/chat",
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
            message = body["message"]
        except KeyError as exc:
            raise LLMUnavailableError(f"Ollama response missing 'message' field: {body}") from exc

        tool_calls = [
            ToolCall(name=call["function"]["name"], arguments=call["function"].get("arguments", {}))
            for call in message.get("tool_calls", []) or []
        ]
        return ChatReply(content=message.get("content", ""), tool_calls=tool_calls)

    def is_available(self, timeout: float) -> bool:
        request = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout):
                return True
        except (urllib.error.URLError, OSError):
            return False


class OpenAIBackend:
    """LLMBackend for an OpenAI-compatible chat server: llama.cpp's
    `llama-server` (started with `--jinja` so tools work), which runs
    MIA's model on the phone (DEC-0019, docs/PHONE_MODEL_TEST.md). The
    tool list is the same shape Ollama takes. `last_timings` keeps the
    server's own speed report from the latest reply (tokens and
    milliseconds for reading the prompt and for writing the answer)."""

    def __init__(self, base_url: str, model: str, temperature: float = _DEFAULT_TEMPERATURE) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self.last_timings: dict = {}

    def _post(self, path: str, payload: dict, timeout: float) -> dict:
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise LLMUnavailableError(f"The model server at {self._base_url} said {exc.code}: {detail}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise LLMUnavailableError(f"Could not reach the model server at {self._base_url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError(f"The model server returned malformed JSON: {exc}") from exc
        if "error" in body:
            raise LLMUnavailableError(f"The model server returned an error: {body['error']}")
        self.last_timings = body.get("timings") or {}
        return body

    def generate(self, prompt: str, timeout: float) -> str:
        return self.chat([{"role": "user", "content": prompt}], [], timeout).content

    def chat(self, messages: list[dict], tools: list[dict], timeout: float) -> ChatReply:
        payload = {"model": self._model, "messages": messages, "temperature": self._temperature, "stream": False}
        if tools:
            payload["tools"] = tools
        body = self._post("/v1/chat/completions", payload, timeout)
        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailableError(f"The model server's reply had no message: {str(body)[:200]}") from exc
        tool_calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments.strip() else {}
                except json.JSONDecodeError:
                    arguments = {}
            tool_calls.append(ToolCall(name=function.get("name", ""), arguments=arguments))
        return ChatReply(content=message.get("content") or "", tool_calls=tool_calls)

    def is_available(self, timeout: float) -> bool:
        try:
            with urllib.request.urlopen(f"{self._base_url}/health", timeout=timeout):
                return True
        except (urllib.error.URLError, OSError):
            return False


def make_backend(config) -> "LLMBackend":
    """The backend `llm.backend` names: "ollama" (default) or "openai"
    (llama.cpp's server on the phone)."""
    base_url = config.get("llm.base_url", _DEFAULT_BASE_URL)
    model = config.get("llm.model", _DEFAULT_MODEL)
    temperature = float(config.get("llm.temperature", _DEFAULT_TEMPERATURE))
    if config.get("llm.backend", "ollama") == "openai":
        return OpenAIBackend(base_url, model, temperature)
    return OllamaBackend(base_url, model, config.get("llm.keep_alive", _DEFAULT_KEEP_ALIVE), temperature)


class LLMManager:
    """
    Core-level Assistant LLM service (`AppContext.llm`). Config-driven
    via `llm.base_url` / `llm.model` / `llm.timeout_seconds` /
    `llm.keep_alive` / `llm.temperature`, following the
    `modules.<id>.*` / top-level-service config convention CLAUDE.md
    documents.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._timeout = float(context.config.get("llm.timeout_seconds", _DEFAULT_TIMEOUT_SECONDS))
        self._backend: LLMBackend = make_backend(context.config)

    def use_backend(self, backend: "LLMBackend", timeout: Optional[float] = None) -> None:
        """Switch models while running (the phone, once its model is up)."""
        self._backend = backend
        if timeout is not None:
            self._timeout = float(timeout)

    @property
    def backend(self) -> "LLMBackend":
        return self._backend

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

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> Optional[ChatReply]:
        """
        Return a ChatReply (content and/or tool_calls), or None (logged)
        if the backend can't be reached. See this module's docstring
        for why a malformed tool-call-shaped `content` triggers one
        retry without tools.
        """
        try:
            reply = self._backend.chat(messages, tools, timeout=self._timeout)
        except LLMUnavailableError as exc:
            log.warning("Assistant unavailable: %s", exc)
            return None

        if not reply.tool_calls and _looks_like_malformed_tool_call(reply.content):
            log.info("Model emitted a malformed tool-call-shaped response; retrying without tools.")
            try:
                reply = self._backend.chat(messages, tools=[], timeout=self._timeout)
            except LLMUnavailableError as exc:
                log.warning("Assistant unavailable on retry: %s", exc)
                return None
        return reply


def _looks_like_malformed_tool_call(content: str) -> bool:
    """True if `content` looks like a hallucinated tool-call JSON blob rather than a real answer."""
    content = content.strip()
    if not content.startswith("{"):
        return False
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, dict) and "name" in parsed
