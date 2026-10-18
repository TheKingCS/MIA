"""
core.home_link
================

Supercharged online (DEC-0022, level 2): when the phone can reach MIA on
the home computer (same Wi-Fi, or anywhere through Tailscale), Talk uses
the computer's bigger model; when it can't, mid-conversation or not, the
phone's own model answers. MIA always says which one did (`level`).

The phone never talks to the computer's model server directly: it links
to **MIA on the computer** once, with the person's own name and password
(`/api/model/link`, never creating an account), keeps the device key it
gets back (the computer keeps only its hash, so the link outlives a
restart), and sends each turn to `/api/model/chat` there. Disconnect
removes the key from the computer too. Nothing is opened to the internet;
the computer still needs that sign-in. The phone's own code still does
everything else (facts, actions, memory); only the model's wording moves.

- `HomeBackend`: an LLMBackend that is MIA-on-the-computer's model.
- `connect()`: sign in, check the model, remember the link (`home_pc.*`).
- `LLMManager` (core/llm_manager.py) tries the home computer first when
  linked and reachable, and falls back to the phone's model.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

PHONE, HOME_PC, THIS_COMPUTER = "PHONE", "HOME PC", "THIS COMPUTER"
RECHECK_SECONDS = 30  # how long "the computer is down" is believed before trying again
REACH_TIMEOUT = 2.5  # a quick look: is the computer there at all?


class HomeLinkError(RuntimeError):
    pass


def clean_url(raw: str) -> str:
    """Pure logic. "192.168.1.20:8765" → "http://192.168.1.20:8765"; only http(s)."""
    raw = str(raw or "").strip().rstrip("/")
    if not raw:
        raise HomeLinkError("Put in the computer's address (for example 192.168.1.20:8765).")
    if "://" not in raw:
        raw = "http://" + raw
    parts = urllib.parse.urlparse(raw)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise HomeLinkError("That doesn't look like an address: try 192.168.1.20:8765.")
    return raw


def _request(url: str, payload: Optional[dict], timeout: float, token: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


class HomeBackend:
    """The home computer's model, through MIA on the computer."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.model = ""

    def chat(self, messages: list[dict], tools: list[dict], timeout: float):
        from core.llm_manager import ChatReply, LLMUnavailableError, ToolCall

        try:
            body = _request(f"{self.url}/api/model/chat", {"messages": messages, "tools": tools}, timeout, self.token)
        except urllib.error.HTTPError as exc:
            raise LLMUnavailableError(f"The home computer said {exc.code}.") from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise LLMUnavailableError(f"The home computer isn't reachable: {exc}") from exc
        self.model = body.get("model") or self.model
        return ChatReply(content=body.get("content") or "",
                         tool_calls=[ToolCall(name=c.get("name", ""), arguments=c.get("arguments") or {})
                                     for c in body.get("tool_calls") or []])

    def generate(self, prompt: str, timeout: float) -> str:
        return self.chat([{"role": "user", "content": prompt}], [], timeout).content

    def is_available(self, timeout: float) -> bool:
        try:
            info = _request(f"{self.url}/api/model/info", None, timeout, self.token)
        except (urllib.error.URLError, OSError, ValueError):
            return False
        self.model = info.get("model") or self.model
        return bool(info.get("available"))


class Reach:
    """Whether the home computer answered lately: checked at most every
    RECHECK_SECONDS, so a phone away from home doesn't wait on it every turn."""

    def __init__(self, backend: HomeBackend, clock=time.monotonic) -> None:
        self.backend = backend
        self._clock = clock
        self._up: Optional[bool] = None
        self._checked = 0.0

    def up(self) -> bool:
        now = self._clock()
        if self._up is None or now - self._checked > RECHECK_SECONDS:
            self._up = self.backend.is_available(REACH_TIMEOUT)
            self._checked = now
        return bool(self._up)

    def down(self) -> None:
        self._up, self._checked = False, self._clock()


def connect(context, url: str, who: str, password: str) -> dict:
    """Sign in to MIA on the computer, check its model, remember the link."""
    url = clean_url(url)
    try:
        login = _request(f"{url}/api/model/link", {"profile_id": who, "password": password}, 8)
    except urllib.error.HTTPError as exc:
        raise HomeLinkError("The computer didn't accept that name and password." if exc.code in (401, 403, 404)
                            else f"The computer said {exc.code}.") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise HomeLinkError(f"Couldn't reach MIA at {url}. Is the computer on, with MIA running?") from exc
    token = login.get("key") or ""
    if not token:
        raise HomeLinkError("The computer didn't give a sign-in back.")
    backend = HomeBackend(url, token)
    available = backend.is_available(8)
    config = context.config
    config.set("home_pc.url", url)
    config.set("home_pc.token", token)
    config.set("home_pc.who", who)
    config.save()
    link(context)
    return {"url": url, "model": backend.model, "available": available}


def disconnect(context) -> None:
    config = context.config
    url, token = config.get("home_pc.url", ""), config.get("home_pc.token", "")
    if url and token:
        try:
            _request(f"{url}/api/model/unlink", {}, 4, token)
        except (urllib.error.URLError, OSError, ValueError):
            log.info("Couldn't reach the computer to unlink; the key stays there until it's removed.")
    for key in ("home_pc.url", "home_pc.token", "home_pc.who"):
        config.set(key, "")
    config.save()
    link(context)


def link(context) -> None:
    """Point Talk at the home computer the config names (or at nothing)."""
    llm = getattr(context, "llm", None)
    if llm is None:
        return
    url, token = context.config.get("home_pc.url", ""), context.config.get("home_pc.token", "")
    llm.use_home(HomeBackend(url, token) if url and token else None)


def linked(context) -> bool:
    """True when this device is linked to MIA on the home computer."""
    config = getattr(context, "config", None)
    return bool(config is not None and config.get("home_pc.url", "") and config.get("home_pc.token", ""))


def home_call(context, path: str, payload: Optional[dict] = None, timeout: float = 6.0, method: str = "",
              raw: bool = False, body: Optional[bytes] = None, headers: Optional[dict] = None):
    """Ask MIA on the home computer (with this device's link key): JSON
    back, or the raw bytes (a camera picture). Raises HomeLinkError with
    something a person can act on."""
    config = context.config
    url, token = config.get("home_pc.url", ""), config.get("home_pc.token", "")
    if not (url and token):
        raise HomeLinkError("Link the home computer first (Settings → Home Computer).")
    sent = {"Authorization": f"Bearer {token}", **(headers or {})}
    data = body
    if payload is not None:
        sent["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url.rstrip("/") + path, data=data, headers=sent,
                                     method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8") or "{}").get("detail")
        except (ValueError, OSError):
            detail = None
        raise HomeLinkError(detail or f"The home computer said {exc.code}.") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise HomeLinkError("Can't reach the home computer right now (is it on, and is Tailscale on here?).") from exc
    return body if raw else json.loads(body.decode("utf-8") or "{}")


def status(context) -> dict:
    llm = getattr(context, "llm", None)
    home = getattr(llm, "home", None)
    return {"linked": home is not None or linked(context), "url": context.config.get("home_pc.url", ""),
            "who": context.config.get("home_pc.who", ""),
            "reachable": bool(home is not None and llm.home_reach.up()),
            "model": getattr(home, "model", "") if home is not None else "",
            "level": getattr(llm, "level", "") if llm is not None else ""}
