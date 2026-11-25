"""
core.llm_manager
==================

The Assistant's LLM backend core service — docs/ROADMAP.md milestone
5.1. Defines a small backend-agnostic interface (`LLMBackend`) with one
concrete implementation, `OllamaBackend`, talking to a local Ollama
server's HTTP API (https://github.com/ollama/ollama/blob/main/docs/api.md),
and a second, `OpenAIBackend` (2026-10-07), for llama.cpp's server on
the phone (`llm.backend: "openai"`). The server's address is written once
(`DEFAULT_SERVER`) and every module asks `local_server_url()` for it; embeddings
and vision go through `OllamaBackend.embed` and `see` (LS-08). When the chosen
model fails or times out, the first smaller one the server has (`llm.fallback_models`,
`OllamaBackend.installed`, `with_model`) answers and `level` names it, and the processor when none of it sits on
the graphics card (`on_gpu`, REQ-HW-012); every call
waits its turn for the GPU, a conversation first (core/model_queue.py) (FW-12).

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

`num_ctx` (2026-10-30, docs/TOOL_CALLING_RESEARCH.md R1): the context
window, sent as `options.num_ctx` on every request (`llm.num_ctx`,
default 16384). Ollama never errors on a prompt longer than its window:
it silently drops the start, which is where the instructions and tools
are, and its own default is 2048 or 4096 depending on the version. A
request asking for a different size than the loaded model has makes
Ollama reload it, so set `llm.num_ctx` to what the server loads with
(the home computer: 32768) and leave it.

**When Ollama isn't running** (2026-11-08, T-0054: the answers.model_down loop saw turns fail
because the PC's model server wasn't up): `LLMManager._ask` starts `ollama serve` with no window,
waits up to WAKE_WAIT seconds and tries the turn once more. Only for Ollama on this machine, at most
once every WAKE_COOLDOWN seconds, and never when `llm.start_ollama` is false.
A role label the model leaks at the start of a reply ("assistant" and a blank line) is taken off
(`without_role_label`).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Protocol

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

DEFAULT_SERVER = "http://127.0.0.1:11434"  # the one place the model server's address is written (LS-08)
_DEFAULT_BASE_URL = DEFAULT_SERVER
_DEFAULT_MODEL = "llama3.2"
_DEFAULT_TIMEOUT_SECONDS = 60.0
# FW-12 (REQ-AI-013): when the chosen model fails or times out, the first of these the computer has answers instead.
FALLBACK_MODELS = ("qwen2.5:7b", "qwen2.5:3b", "llama3.2")
_DEFAULT_KEEP_ALIVE = "-1"
_DEFAULT_TEMPERATURE = 0.0


class LLMUnavailableError(RuntimeError):
    """Raised by a backend when the LLM server can't be reached or errors."""


@dataclass
class ToolCall:
    """One tool the model asked to run: its name and arguments."""
    name: str
    arguments: dict


@dataclass
class ChatReply:
    """What a chat turn returned: the model's text and any tools it asked for."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


_ROLE_LABEL = re.compile(r"^\s*(?:assistant|mia)\s*:?\s*\n+", re.IGNORECASE)


def without_role_label(text: str) -> str:
    """Pure logic. The model's text without a role label it leaked at the start ("assistant" and a blank line: qwen2.5
    after reading a tool's result, the live check through run_assistant_turn, 2026-11-24); a word "assistant" inside
    a sentence stays."""
    return _ROLE_LABEL.sub("", text or "", count=1)


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


def local_server_url(context=None) -> str:
    """The model server's address: the `llm.base_url` setting (the context's, else the device's config), else the
    default; localhost becomes 127.0.0.1 (Windows tries IPv6 first). Every module that talks to the server asks
    here, so moving it is one setting (LS-08, REQ-LS-010)."""
    config = getattr(context, "config", None) if context is not None else None
    if config is None:
        try:
            from core.config_manager import ConfigManager

            config = ConfigManager()
        except Exception:  # noqa: BLE001 - no config: the default
            config = None
    try:
        url = (config.get("llm.base_url", DEFAULT_SERVER) if config is not None else DEFAULT_SERVER) or DEFAULT_SERVER
    except Exception:  # noqa: BLE001 - a setting that can't be read is the default
        url = DEFAULT_SERVER
    return str(url).rstrip("/").replace("://localhost", "://127.0.0.1")


class OllamaBackend:
    """LLMBackend implementation for a local Ollama server: generate and chat with its configured model, and
    `embed` and `see` with a model named for the call (embeddings and vision go through here too, LS-08)."""

    def __init__(self, base_url: str, model: str, keep_alive: str, temperature: float = _DEFAULT_TEMPERATURE,
                 num_ctx: int = 0, think: Optional[bool] = None, num_predict: int = 0) -> None:
        # Windows tries localhost's IPv6 address first, and Ollama isn't there:
        # 2 seconds lost on every call, enough to read as "the computer's down".
        """A local Ollama server: its address (localhost turned into 127.0.0.1, since Windows tries IPv6 first and
        loses two seconds), the model, how long to keep it loaded (a number of seconds, or a duration like "30m"),
        temperature, context size (0: the server's), whether a thinking model thinks, and the most a reply may
        run to (0: no limit; a specialist's model is capped, core/specialist_models.py).
        """
        self._base_url = base_url.rstrip("/").replace("://localhost", "://127.0.0.1")
        self._model = model
        self._temperature = temperature
        self._num_ctx = int(num_ctx or 0)  # 0: leave it to the server
        self._think = think  # None: the model's default; False: answer without a thinking pass (qwen3)
        self._num_predict = int(num_predict or 0)  # 0: no limit
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

    def _thinking(self) -> dict:
        """Ollama's `think`, only when set (llm.think): a thinking model
        (qwen3) otherwise reasons at length before every answer."""
        return {} if self._think is None else {"think": bool(self._think)}

    def _options(self) -> dict:
        """The request's model options: temperature, and the context size and reply limit when they're set."""
        options: dict = {"temperature": self._temperature}
        if self._num_ctx > 0:
            options["num_ctx"] = self._num_ctx
        if self._num_predict > 0:
            options["num_predict"] = self._num_predict
        return options

    def embed(self, model: str, texts: list[str], timeout: float) -> Optional[list]:
        """The vectors, each model call waiting its turn for the GPU (core/model_queue.py: Fable's review, 2026-11-22);
        see `_embed`."""
        from core import model_queue

        with model_queue.slot():
            return self._embed(model, texts, timeout)

    def _embed(self, model: str, texts: list[str], timeout: float) -> Optional[list]:
        """Vectors for `texts` from an embedding model (/api/embed); None when the server doesn't answer, answers
        wrongly, or returns a different count."""
        body = json.dumps({"model": model, "input": list(texts)}).encode("utf-8")
        request = urllib.request.Request(f"{self._base_url}/api/embed", data=body,
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                vectors = json.loads(response.read().decode("utf-8")).get("embeddings") or []
        except (urllib.error.URLError, OSError, ValueError) as problem:
            log.info("No embedding model at %s (%s)", self._base_url, problem)
            return None
        return vectors if len(vectors) == len(texts) else None

    def see(self, model: str, prompt: str, image: bytes, timeout: float = 300) -> str:
        """What the vision model says of a picture, waiting its turn for the GPU (core/model_queue.py); see `_see`."""
        from core import model_queue

        with model_queue.slot():
            return self._see(model, prompt, image, timeout)

    def _see(self, model: str, prompt: str, image: bytes, timeout: float = 300) -> str:
        """A vision model's answer about one image (/api/generate with the image as base64, temperature 0.2).
        Errors from the server are raised to the caller."""
        import base64

        body = json.dumps({"model": model, "prompt": prompt, "images": [base64.b64encode(image).decode("ascii")],
                           "stream": False, "options": {"temperature": 0.2}}).encode("utf-8")
        request = urllib.request.Request(f"{self._base_url}/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return str(json.loads(answer.read()).get("response", "")).strip()

    def generate(self, prompt: str, timeout: float) -> str:
        """One completion from a prompt (/api/generate, not streamed). LLMUnavailableError when the server can't be reached, answers with an error, or sends back something unreadable."""
        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": self._options(),
            **self._thinking(),
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
        """One chat turn with tools (/api/chat, not streamed): the reply's text and tool calls. LLMUnavailableError when the server can't be reached, answers with an error, or sends back something unreadable.
        Its text comes without a role label the model leaked (`without_role_label`).
        """
        payload_dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": self._options(),
            **self._thinking(),
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
        return ChatReply(content=without_role_label(message.get("content", "")), tool_calls=tool_calls)

    def installed(self, timeout: float = 3.0) -> list[str]:
        """The models this Ollama server has (/api/tags), by name; [] when it can't be asked."""
        request = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return [m.get("name", "") for m in json.loads(response.read().decode("utf-8")).get("models", [])]
        except (urllib.error.URLError, OSError, ValueError):
            return []

    def on_gpu(self, timeout: float = 2.0) -> Optional[float]:
        """How much of this backend's model sits on the graphics card now (0 to 1, from /api/ps), or None when it isn't
        loaded or the server can't be asked (REQ-HW-012: 0 means it ran on the processor). A name without a tag is
        read as :latest, as the server names it."""
        request = urllib.request.Request(f"{self._base_url}/api/ps", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                running = json.loads(response.read().decode("utf-8")).get("models", [])
        except (urllib.error.URLError, OSError, ValueError):
            return None
        wanted = {self._model, self._model if ":" in self._model else self._model + ":latest"}
        mine = next((m for m in running if wanted & {m.get("name"), m.get("model")}), None)
        size = float((mine or {}).get("size") or 0)
        return round(float(mine.get("size_vram") or 0) / size, 2) if mine and size else None

    def with_model(self, model: str) -> "OllamaBackend":
        """The same server and settings with another model (the fallback, FW-12)."""
        twin = OllamaBackend(self._base_url, model, "5m", self._temperature, num_ctx=self._num_ctx, think=self._think,
                             num_predict=self._num_predict)
        return twin

    def is_available(self, timeout: float) -> bool:
        """Whether the Ollama server answers (/api/tags)."""
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
        """An OpenAI-style model server (llama.cpp's, on the phone): its address, model and temperature; it keeps the
        last reply's timings.
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self.last_timings: dict = {}

    def _post(self, path: str, payload: dict, timeout: float) -> dict:
        """POSTs JSON to the server and returns its reply, keeping its timings. LLMUnavailableError when the server can't be reached, answers with an error, or sends back something unreadable."""
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
        """One completion, as a one-message chat."""
        return self.chat([{"role": "user", "content": prompt}], [], timeout).content

    def chat(self, messages: list[dict], tools: list[dict], timeout: float) -> ChatReply:
        """One chat turn with tools (/v1/chat/completions): the reply's text and tool calls (arguments sent as a JSON
        string are parsed; unreadable ones become empty). LLMUnavailableError when the server can't be reached, answers with an error, or sends back something unreadable.
        Its text comes without a role label the model leaked (`without_role_label`).
        """
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
        return ChatReply(content=without_role_label(message.get("content") or ""), tool_calls=tool_calls)

    def is_available(self, timeout: float) -> bool:
        """Whether the server answers (/health)."""
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
    return OllamaBackend(base_url, model, config.get("llm.keep_alive", _DEFAULT_KEEP_ALIVE), temperature,
                         num_ctx=int(config.get("llm.num_ctx", 0) or 0), think=config.get("llm.think", None))


class LLMManager:
    """
    Core-level Assistant LLM service (`AppContext.llm`). Config-driven
    via `llm.base_url` / `llm.model` / `llm.timeout_seconds` /
    `llm.keep_alive` / `llm.temperature`, following the
    `modules.<id>.*` / top-level-service config convention CLAUDE.md
    documents.
    """

    def __init__(self, context: AppContext) -> None:
        """The Assistant's model: the configured backend and timeout, plus, when the phone is linked, the home
        computer's model, tried first (DEC-0022); `level` says which answered last (and `fell_back` the smaller
        model, when the chosen one failed, FW-12); and when Ollama was last started for a turn (`_wake_local`).
        """
        self.context = context
        self._timeout = float(context.config.get("llm.timeout_seconds", _DEFAULT_TIMEOUT_SECONDS))
        self._backend: LLMBackend = make_backend(context.config)
        self._last_wake = float("-inf")  # when Ollama was last started for a turn (_wake_local)
        # DEC-0022 level 2 (core/home_link.py): the home computer's model,
        # tried first when linked and reachable; the backend above answers
        # when it isn't. `level` says which one answered last.
        self.home = None
        self.home_reach = None
        self.level = ""
        self.fell_back = ""  # the smaller model that answered last, when the chosen one failed (FW-12)
        self._installed: tuple = (float("-inf"), [])  # (when asked, the server's models), for the fallback

    def use_backend(self, backend: "LLMBackend", timeout: Optional[float] = None) -> None:
        """Switch models while running (the phone, once its model is up)."""
        self._backend = backend
        if timeout is not None:
            self._timeout = float(timeout)

    def use_home(self, backend) -> None:
        """Link (or unlink, with None) the home computer's model (core/home_link.py)."""
        from core.home_link import Reach

        self.home = backend
        self.home_reach = Reach(backend) if backend is not None else None

    def _local_level(self) -> str:
        """Which local model this is: the phone's (linked to a home computer, or llama.cpp) or this computer's."""
        from core.home_link import PHONE, THIS_COMPUTER

        return PHONE if self.home is not None or isinstance(self._backend, OpenAIBackend) else THIS_COMPUTER

    def _ask(self, call):
        """Run `call(backend)` on the home computer when it's there, else
        here; a home computer that stops answering mid-conversation hands
        the turn to this device's model. When this device's model doesn't
        answer, `_wake_local` may start Ollama and the call is tried once more.
        The server's store lock is let go while it runs (core/store_lock.py):
        the model touches no store, and the phone and pages needn't wait.
        Then it waits its turn for the GPU (core/model_queue.py, FW-12): one
        model call at a time, a conversation before background work."""
        from core import model_queue
        from core.store_lock import released

        with released(), model_queue.slot():
            return self._ask_unlocked(call)

    def _ask_unlocked(self, call):
        """_ask's work, with no store lock held: the home computer, else this device's model, else the next smaller
        one (`_fall_back`). Ollama is woken only when its server doesn't answer; a model that fails on a running
        server, or again after a wake, goes to the smaller one."""
        from core.home_link import HOME_PC

        if self.home is not None and self.home_reach.up():
            try:
                result = call(self.home)
                self.level = HOME_PC
                return result
            except LLMUnavailableError as exc:
                log.info("Home computer didn't answer (%s); using this device's model.", exc)
                self.home_reach.down()
        self.fell_back = ""
        try:
            result = call(self._backend)
        except LLMUnavailableError as failed:
            # T-0054 (the answers.model_down loop): on the PC the model server is Ollama, and when it isn't running
            # every turn failed. Start it once, quietly, and try the turn again: only when the server really isn't
            # answering (a model that failed on a running server goes straight to the smaller one, FW-12), and a
            # retry that fails too still falls back (Fable's review, 2026-11-22).
            retried = False
            if not self._backend.is_available(timeout=1.0) and self._wake_local():
                try:
                    result, retried = call(self._backend), True
                except LLMUnavailableError as again:
                    failed = again
            if not retried:
                return self._fall_back(call, failed)
        self.level = self._local_level()
        return result

    def _fall_back(self, call, failed: Exception):
        """The chosen model failed or timed out (REQ-AI-013): the next local model it has from `llm.fallback_models`
        answers instead, and `level` says which ("THIS COMPUTER · qwen2.5:7b, the smaller model"), and that it ran on
        the processor when none of it sat on the graphics card (REQ-HW-012, `OllamaBackend.on_gpu`). Only one is
        tried (a second wait would leave him waiting twice); the first failure is raised when none is there or it
        fails too."""
        backend = self._fallback()
        if backend is None:
            raise failed
        try:
            result = call(backend)
        except LLMUnavailableError:
            raise failed from None
        self.fell_back = backend._model
        share = backend.on_gpu()
        cpu = ", on the processor (the graphics card isn't available)" if share == 0 else ""  # REQ-HW-012
        self.level = f"{self._local_level()} · {backend._model}, the smaller model{cpu}"
        log.warning("The chosen model didn't answer (%s); %s answered instead.", failed, backend._model)
        return result

    def _fallback(self):
        """The first of `llm.fallback_models` this computer's Ollama has (asked at most every 5 minutes), as a
        backend; None for another kind of server or when it has none of them."""
        import time

        config = getattr(getattr(self, "context", None), "config", None)
        if not isinstance(self._backend, OllamaBackend) or config is None:
            return None
        wanted = [m for m in (config.get("llm.fallback_models", FALLBACK_MODELS) or []) if m and m != self._backend._model]
        if not wanted:
            return None
        asked, have = getattr(self, "_installed", (float("-inf"), []))
        if time.monotonic() - asked > 300:
            have = self._backend.installed()
            self._installed = (time.monotonic(), have)
        found = next((m for m in wanted if m in have or f"{m}:latest" in have), None)
        return self._backend.with_model(found) if found else None

    def _wake_local(self) -> bool:
        """When the local model is Ollama on this machine and isn't answering: start `ollama serve` with no window
        (core.dev_lab.quiet_job_flags) and wait up to WAKE_WAIT seconds for it to answer. At most once every
        WAKE_COOLDOWN seconds, never for another kind of server (the phone's), and off when `llm.start_ollama` is
        false. True when the model answers afterwards."""
        import time

        backend = self._backend
        if not isinstance(backend, OllamaBackend) or not _is_this_machine(getattr(backend, "_base_url", "")):
            return False
        if not self.context.config.get("llm.start_ollama", True):
            return False
        now = time.monotonic()
        if now - self._last_wake < WAKE_COOLDOWN:
            return False
        self._last_wake = now
        if not _start_ollama():
            return False
        deadline = now + WAKE_WAIT
        while time.monotonic() < deadline:
            if backend.is_available(timeout=1.0):
                log.info("Ollama wasn't running; started it and the model answered.")
                return True
            time.sleep(0.5)
        log.warning("Started Ollama, but the model didn't answer within %s seconds.", WAKE_WAIT)
        return False

    @property
    def backend(self) -> "LLMBackend":
        """The local backend in use."""
        return self._backend

    def _backend_answers(self) -> bool:
        """Whether this device's model server answers at all (a quick look, for the orb's offline). Never raises."""
        try:
            return bool(self._backend.is_available(timeout=1.0))
        except Exception:  # noqa: BLE001 - one that can't be asked doesn't answer
            return False

    def is_available(self) -> bool:
        """Cheap reachability check for surfacing an "assistant unavailable" state. Never raises. Her orb says
        "offline" while it's false (core/orb_state.py, DEC-0255)."""
        from core import orb_state

        up = (self.home is not None and self.home_reach.up()) or self._backend.is_available(timeout=self._timeout)
        orb_state.hold("offline", not up)
        return up

    def generate(self, prompt: str, timeout: Optional[float] = None) -> Optional[str]:
        """Return the model's reply, or None (logged) if the backend can't be reached. While it answers, MIA's presence
        is "thinking" (core/orb_state.py); a failure while the server itself doesn't answer holds her orb "offline"
        until an answer comes (DEC-0255, WP-07), never one slow or odd reply (`_backend_answers`)."""
        from core import orb_state

        wait = self._timeout if timeout is None else timeout
        try:
            with orb_state.active("thinking"):  # her orb shows it (core/orb_state.py)
                said = self._ask(lambda backend: backend.generate(prompt, timeout=wait))
            orb_state.hold("offline", False)  # an answer came: words are ready
            return said
        except LLMUnavailableError as exc:
            log.warning("Assistant unavailable: %s", exc)
            # her orb says words aren't ready (DEC-0255) only when the server itself doesn't answer, not for one
            # slow or odd reply (Fable's review, 2026-11-22)
            orb_state.hold("offline", not self._backend_answers())
            return None

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> Optional[ChatReply]:
        """
        Return a ChatReply (content and/or tool_calls), or None (logged)
        if the backend can't be reached; MIA's presence is "thinking" while
        the model answers (core/orb_state.py), and "offline" from a failure to reach it until an answer comes
        (WP-07; only when the server itself doesn't answer). See this module's docstring
        for why a malformed tool-call-shaped `content` triggers one
        retry without tools.
        """
        from core import orb_state

        try:
            with orb_state.active("thinking"):  # her orb shows it (core/orb_state.py)
                reply = self._ask(lambda backend: backend.chat(messages, tools, timeout=self._timeout))
            orb_state.hold("offline", False)  # an answer came: words are ready
        except LLMUnavailableError as exc:
            log.warning("Assistant unavailable: %s", exc)
            # her orb says words aren't ready (DEC-0255) only when the server itself doesn't answer, not for one
            # slow or odd reply (Fable's review, 2026-11-22)
            orb_state.hold("offline", not self._backend_answers())
            return None

        if not reply.tool_calls and _looks_like_malformed_tool_call(reply.content):
            log.info("Model emitted a malformed tool-call-shaped response; retrying without tools.")
            try:
                reply = self._ask(lambda backend: backend.chat(messages, tools=[], timeout=self._timeout))
            except LLMUnavailableError as exc:
                log.warning("Assistant unavailable on retry: %s", exc)
                return None
        return reply


WAKE_WAIT = 15.0  # seconds to wait for a just-started Ollama to answer
WAKE_COOLDOWN = 120.0  # never start it more often than this, so a broken install isn't hammered


def _is_this_machine(base_url: str) -> bool:
    """Pure logic. Whether a model server's address is this computer (so starting it here could help)."""
    from urllib.parse import urlparse

    return (urlparse(base_url).hostname or "") in ("127.0.0.1", "localhost", "::1")


def _start_ollama() -> bool:
    """Starts `ollama serve` in the background with no window; False when Ollama isn't installed or won't start."""
    import os
    import shutil
    import subprocess

    from core.dev_lab import quiet_job_flags

    exe = shutil.which("ollama") or next((str(p) for p in (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",) if p.is_file()), None)
    if not exe:
        log.info("The model isn't answering and Ollama isn't installed here to start.")
        return False
    try:
        subprocess.Popen([exe, "serve"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=quiet_job_flags(), close_fds=True)
    except OSError:
        log.exception("Couldn't start Ollama.")
        return False
    return True


# A tool call's own opening, whether or not the rest parses: the model wrote '{"name": "draft_email", "parameters":
# {... "\$$X" ...}}' as its answer (live sweep, 2026-11-25), invalid JSON, so it was neither caught nor retried
# Also a whole reply that is one fenced block, and the "input"/"args" keys (the thirteenth review); this only asks again
# without tools; what's replaced in the turn is narrower (core/assistant_turn._garbled)
_CALL_SHAPE = re.compile(r'^\s*(?:```(?:json)?\s*)?\{\s*"(?:name|function|tool)"\s*:\s*"[A-Za-z_][\w.]*"\s*,\s*'
                         r'"(?:parameters|arguments|args|input)"\s*:')


def _looks_like_malformed_tool_call(content: str) -> bool:
    """True if `content` looks like a hallucinated tool-call JSON blob rather than a real answer: JSON with a name,
    or a tool call's own opening even when the rest doesn't parse (`_CALL_SHAPE`)."""
    content = str(content or "").strip()
    if _CALL_SHAPE.match(content):
        return True
    if not content.startswith("{"):
        return False
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, dict) and "name" in parsed
