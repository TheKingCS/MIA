"""
core.inbox_mail
==================

Optional email intake for the document inbox (core/inbox_manager.py,
2026-09-28). The owner picks a mailbox (a dedicated address is best,
e.g. a new Gmail account used only for sending MIA receipts and
manuals). MIA checks it over IMAP, the standard mail-reading protocol
(Python's own imaplib, no new dependency), saves every new message into
the inbox folder as a .eml file, and marks it read. From there it's the
same as any dropped file.

**The mailbox password is encrypted** with the owner's passphrase
(core.secrets_manager, the same scheme as the Plaid vault) in
data/inbox_mail.enc and held in memory only while unlocked. Unlocking
the Private Journal with the same passphrase unlocks this too, so it's
still one prompt per boot. Locked means MIA simply doesn't check mail;
nothing else stops working.

For Gmail, IMAP needs an "app password" (Google Account → Security →
2-Step Verification → App passwords), not the normal password. The
setup guide walks through it.

Checking happens on a background thread (network waits must not freeze
the screen); the thread only writes files into the folder, and the
normal folder scan on the GUI thread takes it from there.
"""

from __future__ import annotations

import imaplib
import json
import threading
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger
from core.secrets_manager import SecretsError, decrypt_bytes, encrypt_bytes

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_VAULT_FILE = _DATA_DIR / "inbox_mail.enc"


class MailSettings:
    """host/port/username/folder live in config (not secret); the password in the vault."""

    def __init__(self, context) -> None:
        self.context = context

    def get(self, key: str, default=None):
        return self.context.config.get(f"inbox.email.{key}", default)

    @property
    def configured(self) -> bool:
        return bool(self.get("host") and self.get("username")) and _VAULT_FILE.exists()

    def save(self, host: str, username: str, port: int = 993, folder: str = "INBOX") -> None:
        config = self.context.config
        config.set("inbox.email.host", host.strip())
        config.set("inbox.email.username", username.strip())
        config.set("inbox.email.port", int(port))
        config.set("inbox.email.folder", folder.strip() or "INBOX")
        config.save()


class MailVault:
    def __init__(self) -> None:
        self._password: Optional[str] = None

    @property
    def unlocked(self) -> bool:
        return self._password is not None

    @staticmethod
    def exists() -> bool:
        return _VAULT_FILE.exists()

    def store(self, password: str, passphrase: str) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        blob = encrypt_bytes(json.dumps({"password": password}).encode("utf-8"), passphrase)
        _VAULT_FILE.write_bytes(blob)
        self._password = password

    def unlock(self, passphrase: str) -> None:
        """Raises SecretsError on a wrong passphrase."""
        if not _VAULT_FILE.exists():
            raise SecretsError("No email password is stored.")
        self._password = json.loads(decrypt_bytes(_VAULT_FILE.read_bytes(), passphrase))["password"]

    def try_unlock(self, passphrase: str) -> bool:
        try:
            self.unlock(passphrase)
            return True
        except (SecretsError, ValueError, KeyError):
            return False

    def lock(self) -> None:
        self._password = None

    @property
    def password(self) -> Optional[str]:
        return self._password


_TIMEOUT_SECONDS = 30  # a dead network must not leave the check hanging forever


def _connect_ssl(host: str, port: int) -> imaplib.IMAP4:
    return imaplib.IMAP4_SSL(host, port, timeout=_TIMEOUT_SECONDS)


def fetch_new_messages(
    host: str, username: str, password: str, port: int = 993, folder: str = "INBOX",
    connect: Callable[[str, int], imaplib.IMAP4] = _connect_ssl, limit: int = 25,
) -> list[bytes]:
    """Unread messages as raw bytes, marked read on the server. Raises
    imaplib.IMAP4.error / OSError on login or network failure."""
    client = connect(host, port)
    try:
        client.login(username, password)
        client.select(folder)
        status, data = client.search(None, "UNSEEN")
        if status != "OK":
            return []
        messages = []
        for number in (data[0].split() if data and data[0] else [])[:limit]:
            status, parts = client.fetch(number, "(RFC822)")
            if status != "OK":
                continue
            raw = next((p[1] for p in parts if isinstance(p, tuple) and len(p) > 1), None)
            if raw:
                messages.append(raw)
                client.store(number, "+FLAGS", "\\Seen")
        return messages
    finally:
        try:
            client.logout()
        except Exception:
            pass


class MailChecker:
    """Runs one check at a time on a background thread."""

    def __init__(self, inbox, settings: MailSettings, vault: MailVault) -> None:
        self.inbox, self.settings, self.vault = inbox, settings, vault
        self._thread: Optional[threading.Thread] = None
        self.last_result = ""

    def check_now(self, fetch=fetch_new_messages, wait: bool = False) -> bool:
        """Start a check. False when it can't run (not set up, locked, or already running)."""
        if not (self.settings.configured and self.vault.unlocked) or (self._thread and self._thread.is_alive()):
            return False
        self._thread = threading.Thread(target=self._run, args=(fetch,), name="mia-inbox-mail", daemon=True)
        self._thread.start()
        if wait:
            self._thread.join(timeout=60)
        return True

    def _run(self, fetch) -> None:
        try:
            messages = fetch(
                self.settings.get("host"), self.settings.get("username"), self.vault.password,
                int(self.settings.get("port", 993)), self.settings.get("folder", "INBOX"),
            )
            for raw in messages:
                self.inbox.receive_file("message.eml", raw, source="email")
            self.last_result = f"Checked email: {len(messages)} new."
        except (imaplib.IMAP4.error, OSError) as exc:
            log.warning("Email check failed: %s", exc)
            self.last_result = f"Couldn't check email: {exc}"
