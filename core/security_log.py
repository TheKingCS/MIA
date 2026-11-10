"""
core.security_log
===================

Who signed in, from where, and what changed about an account (docs/SECURITY.md step 3; Zac, 2026-11-08: "fortify our
security measures to industry standards and beyond"). One line per event in `security_log.jsonl` on this device:
sign-ins (and whether the device was new), wrong passwords, the waits they caused, sessions that ended, password and
recovery code changes, phones linked, and "sign out everywhere". Each says which device, in words and its address.

**Append-only, on purpose.** It's written by plain appends, not through core/atomic_write.py, so it is never in the
undo log: "undo that" can't erase a sign-in. It never holds a password, a token or a code; a name tried that matches
no account is kept cut short. The newest KEEP lines are kept.

**Changes made anywhere.** A password or sign-in email changed on this computer (not through the web, which logs
its own with the device) reaches the log through the event bus (`on_account_change`, wired in core/application.py),
so a change made at the desktop is never missing from it (2026-11-09).

**Alerts.** A sign-in from a device this account hasn't used before, the first wait after repeated wrong
passwords, and a changed sign-in email each tell the account's owner at once (a direct notification, like an alarm: they're about their
safety, not the daily message limit's kind of message), with what to do if it wasn't them.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KEEP = 5000
KINDS = ("sign_in", "sign_in_failed", "waiting", "session_ended", "signed_out", "signed_out_everywhere",
         "password_changed", "recovery_code", "phone_linked", "phone_unlinked", "two_step_on", "two_step_off", "data_key_unopened", "data_key_restored", "data_key_shown", "data_exported",
         "email_changed")
WORDS = {"sign_in": "Signed in", "sign_in_failed": "Wrong password", "waiting": "Too many wrong passwords: made to wait",
         "session_ended": "Session ended (unused too long)", "signed_out": "Signed out",
         "signed_out_everywhere": "Signed out everywhere", "password_changed": "Password changed",
         "email_changed": "Sign-in email changed",
         "recovery_code": "New recovery code made", "phone_linked": "A phone linked to this computer",
         "phone_unlinked": "A linked phone was unlinked",
         "two_step_on": "Two-step sign-in turned on", "two_step_off": "Two-step sign-in turned off",
         "data_key_unopened": "The key to MIA's sealed files couldn't be opened",
         "data_key_restored": "The recovery key was entered",
         "data_key_shown": "The recovery key was shown",
         "data_exported": "Your data was exported"}


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


class SecurityLog:
    """The device's security log (security_log.jsonl), appended to and read under a lock."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Points at the log's file in data/ (or the folder given); nothing is read yet."""
        self.path = Path(data_dir if data_dir is not None else _DATA_DIR) / "security_log.jsonl"
        self._lock = threading.Lock()

    def record(self, kind: str, profile_id: Optional[str], device: str = "", detail: str = "") -> dict:
        """Appends one event and returns it; the log is cut back to its newest KEEP lines when it grows past twice
        that."""
        entry = {"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "profile_id": profile_id or "",
                 "device": (device or "")[:80], "detail": (detail or "")[:120]}
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
                self._trim()
            except OSError:
                log.exception("Couldn't write the security log.")
        return entry

    def _trim(self) -> None:
        """Keeps the newest KEEP lines once the file holds more than twice that (called under the lock)."""
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        if len(lines) > 2 * KEEP:
            self.path.write_text("\n".join(lines[-KEEP:]) + "\n", encoding="utf-8")

    def entries(self) -> list[dict]:
        """Every event, oldest first (a damaged line is skipped)."""
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

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
