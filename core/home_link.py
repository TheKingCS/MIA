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
- **Reported lost** (WP-10, Q-90): when he reports this device lost on the
  computer's Sign-ins page, its key is refused there at once; the next time
  this device asks the computer anything (`home_call`), it's answered 410
  with X-MIA-Erase, and `erase_here` removes MIA's data on this device (its
  key folder too, so anything sealed left behind can't be opened) and
  forgets the link. Only that answer, to this device's own key, erases, and only
  proved: each call carries a fresh nonce (X-MIA-Erase-Nonce) and the 410 must
  carry `erase_proof` of it under the device's key (X-MIA-Erase-Proof), so
  nothing else answering at the address can order an erase. Besides the data
  folder, `other_folders` names what goes (his content folders, the config).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

PHONE, HOME_PC, THIS_COMPUTER = "PHONE", "HOME PC", "THIS COMPUTER"
RECHECK_SECONDS = 30  # how long "the computer is down" is believed before trying again
REACH_TIMEOUT = 2.5  # a quick look: is the computer there at all?


class HomeLinkError(RuntimeError):
    """Something a person can act on. `code` is the computer's HTTP answer
    (409: it changed there since), 0 when it couldn't be reached."""

    def __init__(self, message: str, code: int = 0) -> None:
        """A problem linking to the home computer, said in words, with the HTTP code when there was one."""
        super().__init__(message)
        self.code = code


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
    """One JSON request to MIA on the home computer (POST with a body, GET without), with the device key when there
    is one; the reply's JSON.
    """
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
        """MIA on the home computer as a model backend: its address and this phone's device key."""
        self.url = url.rstrip("/")
        self.token = token
        self.model = ""

    def chat(self, messages: list[dict], tools: list[dict], timeout: float):
        """One chat turn sent to the home computer's model (/api/model/chat); LLMUnavailableError when it says no or
        can't be reached, so the phone's own model answers instead.
        """
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
        """One completion, as a one-message chat."""
        return self.chat([{"role": "user", "content": prompt}], [], timeout).content

    def is_available(self, timeout: float) -> bool:
        """Whether the home computer's model answers (/api/model/info), noting its name."""
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
        """Whether the home computer can be reached, checked at most every RECHECK_SECONDS so a turn never waits on it."""
        self.backend = backend
        self._clock = clock
        self._up: Optional[bool] = None
        self._checked = 0.0

    def up(self) -> bool:
        """Whether the home computer was reachable at the last check (checking again when that's old)."""
        now = self._clock()
        if self._up is None or now - self._checked > RECHECK_SECONDS:
            self._up = self.backend.is_available(REACH_TIMEOUT)
            self._checked = now
        return bool(self._up)

    def down(self) -> None:
        """Marks it unreachable now (a turn just failed), so the next turns go straight to the phone's model."""
        self._up, self._checked = False, self._clock()


def connect(context, url: str, who: str, password: str, code: str = "") -> dict:
    """Sign in to MIA on the computer (with the authenticator's code when two-step sign-in is on there), check its
    model, remember the link. (A phone after the move takes the computer's copies first because the computer says it
    restored a backup, `sync.manifest`'s restored_at, not because it paired: pairing again after a lockdown or a
    password change keeps merging as usual.)"""
    url = clean_url(url)
    try:
        login = _request(f"{url}/api/model/link", {"profile_id": who, "password": password, "code": code}, 8)
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and exc.headers.get("X-MIA-Two-Step"):
            raise HomeLinkError("Two-step sign-in is on: enter the 6-digit code from your authenticator app too.") from exc
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
    """Unlinks: asks the computer to forget this phone's key (logged if it can't be reached), then forgets the link
    here.
    """
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
              raw: bool = False, body=None, headers: Optional[dict] = None, save_to: Optional[Path] = None):
    """Ask MIA on the home computer (with this device's link key): JSON
    back, or the raw bytes (a camera picture). `body` may be an open file
    (a photo going to the PC, with its Content-Length in `headers`), and
    `save_to` streams the answer into a file instead of memory (a photo
    coming back). Raises HomeLinkError with something a person can act on. Answered "erase" (410 with X-MIA-Erase:
    this device was reported lost, proved with this device's key against the nonce sent: `erase_proof`), it erases
    MIA's data here first (`erase_here`, WP-10); an order without that proof erases nothing."""
    config = context.config
    url, token = config.get("home_pc.url", ""), config.get("home_pc.token", "")
    if not (url and token):
        raise HomeLinkError("Link the home computer first (Settings → Home Computer).")
    nonce = secrets.token_hex(16)  # an erase order must prove it knows this device's key (erase_proof)
    sent = {"Authorization": f"Bearer {token}", "X-MIA-Erase-Nonce": nonce, **(headers or {})}
    data = body
    if payload is not None:
        sent["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url.rstrip("/") + path, data=data, headers=sent,
                                     method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if save_to is not None:
                save_to.parent.mkdir(parents=True, exist_ok=True)
                with open(save_to, "wb") as out:
                    shutil.copyfileobj(response, out, 1 << 20)
                return save_to
            body = response.read()
    except urllib.error.HTTPError as exc:
        told = exc.headers if exc.headers is not None else {}
        if exc.code == 410 and told.get("X-MIA-Erase") == "1" and hmac.compare_digest(
                str(told.get("X-MIA-Erase-Proof") or ""), erase_proof(token, nonce)):
            erase_here(context)  # reported lost on the computer that holds this device's key (WP-10)
            raise HomeLinkError("This device was reported lost on the home computer, so MIA's data on it has been "
                                "erased.", 410) from exc
        try:
            detail = json.loads(exc.read().decode("utf-8") or "{}").get("detail")
        except (ValueError, OSError):
            detail = None
        raise HomeLinkError(detail or f"The home computer said {exc.code}.", exc.code) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise HomeLinkError("Can't reach the home computer right now (is it on, and is Tailscale on here?).") from exc
    return body if raw else json.loads(body.decode("utf-8") or "{}")


def erase_proof(key: str, nonce: str) -> str:
    """Pure logic. What a genuine erase order carries: an HMAC of the device's nonce, keyed with the hash of its key
    (the computer keeps that hash, core/linked_devices.key_hash), so nothing else answering at the address can order
    an erase (Fable's review, 2026-11-22)."""
    secret = hashlib.sha256(str(key).encode()).hexdigest().encode()
    return hmac.new(secret, str(nonce).encode(), hashlib.sha256).hexdigest()


EXIT_AFTER_ERASE = True  # tests turn it off


def other_folders(config) -> list:
    """Besides the data folder, what a lost device's erase removes: the backup's external content folders (photos,
    documents, captures, as configured) and the config file. Never raises: [] when they can't be worked out. The test
    suite replaces this, so a test's erase never reaches the checkout's real folders."""
    try:
        from core.backup_manager import _CONFIG_FILE, _resolve_external_content_dirs

        return [Path(d) for _name, d in _resolve_external_content_dirs(config)] + [Path(_CONFIG_FILE)]
    except Exception:  # noqa: BLE001 - the data folder still goes
        log.exception("Couldn't work out the other folders to erase")
        return []


def erase_here(context, root: Optional[Path] = None) -> dict:
    """This device was reported lost (WP-10): forgets the link and removes everything in MIA's data folder here (the
    data key's folder with it, so a sealed file left anywhere can't be opened), her other folders of his things (the
    backup's external content folders: photos, documents, captures) and the config; then MIA stops, so nothing still
    in memory is written back. Returns {"removed": how many entries}. Never raises; what couldn't be removed is
    logged."""
    import shutil

    from core.data_root import DATA_DIR

    config = context.config
    for key in ("home_pc.url", "home_pc.token", "home_pc.who"):
        config.set(key, "")
    try:
        config.save()
    except Exception:  # noqa: BLE001 - erasing goes on
        log.exception("Couldn't save the forgotten link")
    folder = Path(root) if root is not None else Path(DATA_DIR)
    removed = 0
    extra = other_folders(config) if root is None else []
    for entry in (list(folder.iterdir()) if folder.is_dir() else []) + [e for e in extra if Path(e).exists()]:
        try:
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            removed += 1
        except OSError:
            log.exception("Couldn't erase %s", entry.name)
    try:
        from core import at_rest

        at_rest.forget()  # the opened key goes too
    except Exception:  # noqa: BLE001
        pass
    log.warning("This device was reported lost: MIA's data on it was erased (%d entries).", removed)
    if EXIT_AFTER_ERASE and root is None:
        import os
        import threading

        threading.Timer(1.0, os._exit, args=(0,)).start()  # nothing in memory may write a store back
    return {"removed": removed}


def status(context) -> dict:
    """The link's status for Settings: linked, the computer's address, who signed in, reachable now, its model, and
    which model answered last.
    """
    llm = getattr(context, "llm", None)
    home = getattr(llm, "home", None)
    return {"linked": home is not None or linked(context), "url": context.config.get("home_pc.url", ""),
            "who": context.config.get("home_pc.who", ""),
            "reachable": bool(home is not None and llm.home_reach.up()),
            "model": getattr(home, "model", "") if home is not None else "",
            "level": getattr(llm, "level", "") if llm is not None else ""}
