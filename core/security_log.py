"""
core.security_log
===================

Who signed in, from where, and what changed about an account (docs/SECURITY.md step 3; Zac, 2026-11-08: "fortify our
security measures to industry standards and beyond"). One line per event in `security_log.jsonl` on this device:
sign-ins (and whether the device was new), wrong passwords, the waits they caused, sessions that ended, password and
recovery code changes, phones linked, and "sign out everywhere". Each says which device, in words and its address.

**Append-only, on purpose.** It's written by plain appends, not through core/atomic_write.py, so it is never in the
undo log: "undo that" can't erase a sign-in. It never holds a password, a token or a code; a name tried that matches
no account is kept cut short. The newest KEEP lines are kept, and the trim is itself a line.

**Hash-chained (WP-05, REQ-SEC-034, DEC-0254).** Each line holds the hash of the line before (`prev`) and its own
(`h`, `link`), so a changed line, or one removed or put in, breaks the chain (`verify`, `check_chain`). A chain can
be rewritten whole by whoever can write the file, so its head is copied to another device: the Sign-ins page
remembers the newest hash it saw, and asks next time whether the log still holds it (`holds`). One that doesn't
is logged (`log_changed`) and told.

**Changes made anywhere.** A password or sign-in email changed on this computer (not through the web, which logs
its own with the device) reaches the log through the event bus (`on_account_change`, wired in core/application.py),
so a change made at the desktop is never missing from it (2026-11-09).

**Alerts.** A sign-in from a device this account hasn't used before, the first wait after repeated wrong
passwords, and a changed sign-in email each tell the account's owner at once (a direct notification, like an alarm: they're about their
safety, not the daily message limit's kind of message), with what to do if it wasn't them.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import hashlib
import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.at_rest import flush_alerts, open_lines, open_text, seal_line, seal_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = DATA_DIR
KEEP = 5000
KINDS = ("sign_in", "sign_in_failed", "waiting", "session_ended", "signed_out", "signed_out_everywhere",
         "password_changed", "recovery_code", "phone_linked", "phone_unlinked", "two_step_on", "two_step_off", "data_key_unopened", "data_key_restored", "data_key_shown", "data_exported",
         "email_changed", "lockdown", "lockdown_lifted", "log_trimmed", "log_changed", "device_lost", "device_erased")
WORDS = {"sign_in": "Signed in", "sign_in_failed": "Wrong password", "waiting": "Too many wrong passwords: made to wait",
         "session_ended": "Session ended (unused too long)", "signed_out": "Signed out",
         "signed_out_everywhere": "Signed out everywhere", "password_changed": "Password changed",
         "email_changed": "Sign-in email changed",
         "lockdown": "Lockdown: everything signed out, the vaults locked", "lockdown_lifted": "Lockdown lifted with your password",
         "recovery_code": "New recovery code made", "phone_linked": "A phone linked to this computer",
         "phone_unlinked": "A linked phone was unlinked",
         "two_step_on": "Two-step sign-in turned on", "two_step_off": "Two-step sign-in turned off",
         "data_key_unopened": "The key to MIA's sealed files couldn't be opened",
         "data_key_restored": "The recovery key was entered",
         "data_key_shown": "The recovery key was shown",
         "data_exported": "Your data was exported",
         "log_trimmed": "The log was cut back to its newest lines",
         "log_changed": "This log no longer holds what another device saw in it",
         "device_lost": "A device reported lost: its key refused, told to erase when it reconnects",
         "device_erased": "A lost device reconnected and was told to erase"}


def device_of(user_agent: str, address: str) -> str:
    """Pure logic. A device in words from its browser's description and its address: "Android phone · 100.64.0.7",
    "Edge on Windows · 127.0.0.1"."""
    ua = (user_agent or "").lower()
    if "android" in ua:
        kind = "Android phone"
    elif "iphone" in ua or "ipad" in ua:
        kind = "iPhone"
    elif "edg/" in ua:
        kind = "Edge on " + ("Windows" if "windows" in ua else "a computer")
    elif "chrome" in ua:
        kind = "Chrome on " + ("Windows" if "windows" in ua else "Mac" if "mac os" in ua else "a computer")
    elif "firefox" in ua:
        kind = "Firefox"
    elif "safari" in ua:
        kind = "Safari"
    elif "python" in ua or "testclient" in ua or "okhttp" in ua:
        kind = "MIA app"
    else:
        kind = "A device"
    return f"{kind} · {address}" if address else kind


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_held = threading.local()


def writing() -> bool:
    """Whether this thread holds a security log's lock (core/at_rest.flush_alerts waits until it doesn't, since
    recording a key problem then would wait on that same lock)."""
    return getattr(_held, "depth", 0) > 0


def _lock_for(path: Path) -> threading.Lock:
    """One lock per log file, shared by every SecurityLog on it (core/at_rest.py makes its own to note a key
    problem), so two writers never chain onto the same line."""
    with _locks_guard:
        return _locks.setdefault(str(Path(path).resolve()), threading.Lock())


def link(entry: dict, prev: str) -> dict:
    """Pure logic. The entry chained onto the line before it (WP-05): `prev` is that line's hash ("" for the first),
    `h` this one's, a SHA-256 over the previous hash and the entry itself in a fixed form."""
    out = {k: v for k, v in entry.items() if k not in ("prev", "h")}
    out["prev"] = prev
    out["h"] = digest(out)
    return out


def digest(entry: dict) -> str:
    """Pure logic. An entry's hash: SHA-256 over it (without its own `h`) as sorted, compact JSON."""
    body = json.dumps({k: v for k, v in entry.items() if k != "h"}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def check_chain(lines: list[str]) -> dict:
    """Pure logic. Whether the chained lines are as written: each line's hash matches what it holds and its `prev` is
    the line before's hash. Lines from before the chain (no `h`) come first and are counted, not checked; the first
    chained line's `prev` can't be checked (the lines before it were trimmed). Returns {ok, chained, before_chain,
    head: {h, at} of the newest, broken: None or {line, at, why}}."""
    head, chained, before, prev = None, 0, 0, None
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            return _broken(chained, before, head, n, "", "a line that isn't a record (damaged, or it won't open)")
        if "h" not in entry:
            if chained:
                return _broken(chained, before, head, n, entry.get("at", ""), "an unchained line after the chain began")
            before += 1
            continue
        if digest(entry) != entry["h"]:
            return _broken(chained, before, head, n, entry.get("at", ""), "a line changed after it was written")
        if prev is not None and entry.get("prev") != prev:
            return _broken(chained, before, head, n, entry.get("at", ""), "a line removed or put in before this one")
        prev, chained = entry["h"], chained + 1
        head = {"h": entry["h"], "at": entry.get("at", "")}
    return {"ok": True, "chained": chained, "before_chain": before, "head": head, "broken": None}


def _broken(chained: int, before: int, head, line: int, at: str, why: str) -> dict:
    """check_chain's answer for a break found at `line`."""
    return {"ok": False, "chained": chained, "before_chain": before, "head": head,
            "broken": {"line": line, "at": at, "why": why}}


class SecurityLog:
    """The device's security log (security_log.jsonl), appended to and read under a lock shared by every instance on
    the same file, each line chained to the one before by its hash (WP-05, REQ-SEC-034)."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Points at the log's file in data/ (or the folder given), with the one lock every log on that file shares;
        nothing is read yet."""
        self.path = Path(data_dir if data_dir is not None else _DATA_DIR) / "security_log.jsonl"
        self._lock = _lock_for(self.path)

    @contextmanager
    def _holding(self):
        """The file's lock, marked as held by this thread (writing()), so a key problem met meanwhile is recorded
        once it's let go."""
        with self._lock:  # the one lock for this file (_lock_for)
            _held.depth = getattr(_held, "depth", 0) + 1
            try:
                yield
            finally:
                _held.depth -= 1

    def record(self, kind: str, profile_id: Optional[str], device: str = "", detail: str = "") -> dict:
        """Appends one event, with the trace id of what caused it, chained to the newest line by its hash, and returns
        it; the log is cut back to its newest KEEP lines when it grows past twice that. Each line is sealed as it's
        written (seal_line, WP-04)."""
        from core import trace

        entry = {"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "profile_id": profile_id or "",
                 "device": (device or "")[:80], "detail": (detail or "")[:120], "trace": trace.current()}
        with self._holding():
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                entry = link(entry, self._last_hash())
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(seal_line(self.path, json.dumps(entry)) + "\n")
                self._trim()
            except OSError:
                log.exception("Couldn't write the security log.")
        flush_alerts()  # a key problem met while the lock was held (core/at_rest.py)
        return entry

    def _last_hash(self) -> str:
        """The newest line's hash ("" when the log is empty or from before the chain); only that line is opened
        (called under the lock)."""
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return ""
        lines = [x for x in raw.splitlines() if x.strip()]
        if not lines:
            return ""
        try:
            return str(json.loads(open_lines(lines[-1])[0][0]).get("h", ""))
        except (ValueError, IndexError, AttributeError):
            return ""

    def _trim(self) -> None:
        """Keeps the newest KEEP lines once the file holds more than twice that (called under the lock), then notes the
        trim as a chained line, so the chain's start is explained. Written straight to a temporary file and moved into
        place, never through atomic_write_text: that would put the log in the undo log. Kept lines stay as stored
        (sealed); any plain one is sealed (WP-04)."""
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()  # as stored: kept lines stay sealed
        except OSError:
            return
        if len(lines) <= 2 * KEEP:
            return
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(seal_text(self.path, "\n".join(lines[-KEEP:]) + "\n"), encoding="utf-8")
        os.replace(tmp, self.path)
        note = link({"at": datetime.now().isoformat(timespec="seconds"), "kind": "log_trimmed", "profile_id": "",
                     "device": "", "detail": f"kept the newest {KEEP} of {len(lines)} lines", "trace": ""},
                    self._last_hash())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(seal_line(self.path, json.dumps(note)) + "\n")

    def entries(self) -> list[dict]:
        """Every event, oldest first (a damaged line is skipped), each with its chain fields (`prev`, `h`). Its sealed
        lines open through open_text (WP-04)."""
        with self._holding():
            try:
                lines = open_text(self.path).splitlines()
            except OSError:
                return []
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def verify(self) -> dict:
        """Whether the log is as it was written (check_chain over every line, each sealed one opened); a missing log is
        intact and empty."""
        with self._holding():
            try:
                lines = open_text(self.path).splitlines()
            except OSError:
                lines = []
        return check_chain(lines)

    def holds(self, h: str) -> bool:
        """Whether a hash another device saw as this log's head is still one of its lines (REQ-SEC-034): a log rewritten
        from before that point no longer holds it."""
        return bool(h) and any(e.get("h") == h for e in self.entries())

    def for_person(self, profile_id: str, limit: int = 100) -> list[dict]:
        """One account's events, newest first, each with its words."""
        mine = [dict(e, what=WORDS.get(e.get("kind"), e.get("kind"))) for e in self.entries()
                if e.get("profile_id") == profile_id]
        return list(reversed(mine))[:limit]

    def known_device(self, profile_id: str, device: str) -> bool:
        """Whether this account has signed in from this device before."""
        return any(e.get("kind") == "sign_in" and e.get("profile_id") == profile_id and e.get("device") == device
                   for e in self.entries())


_local = threading.local()


@contextmanager
def logged_by_caller():
    """Inside it, an account change the caller writes to the log itself (the web, which knows the device) isn't
    written again by the event bus's listener."""
    _local.depth = getattr(_local, "depth", 0) + 1
    try:
        yield
    finally:
        _local.depth -= 1


def on_account_change(context, kind: str):
    """An event bus handler for `profile.password_changed` / `profile.email_changed`: writes the change to the log as
    made on this computer (unless its caller logs it, `logged_by_caller`), and for a changed sign-in email tells the
    owner at once, since it's how an account is taken over."""
    def handle(data=None, **kwargs) -> None:
        """Logs one change (never fails what changed it)."""
        if getattr(_local, "depth", 0):
            return
        profile_id = (data or {}).get("profile_id") if isinstance(data, dict) else kwargs.get("profile_id")
        book = getattr(context, "security_log", None)
        try:
            if book is not None:
                book.record(kind, profile_id, "this computer")
        except Exception:
            log.exception("Couldn't write %s to the security log.", kind)
        if kind == "email_changed":
            alert(context, profile_id, "Your MIA sign-in email changed",
                  "The email you sign in with was changed on this computer. If it wasn't you, change your password "
                  "and sign out everywhere from Settings, Sign-ins and Security.")
    return handle


def alert(context, profile_id: Optional[str], title: str, message: str) -> None:
    """Tells an account's owner about something that touches their safety, straight away (a direct notification, kept
    even when MIA's messages are muted); never fails the sign-in it's about."""
    if not profile_id:
        return
    try:
        from core.personal_data import view_for

        notes = getattr(view_for(context, profile_id), "notifications", None)
        if notes is not None:
            notes.notify(title, message, level="warning", source="security", always=True)
    except Exception:
        log.exception("Couldn't send a security alert.")
