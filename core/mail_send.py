"""
core.mail_send
================

Sending an email draft from your own address (2026-10-01, accounts stage
3, core/email_drafts.py). Optional: without it, Copy and "open in my mail
app" always work.

Each person sets up their own sending (Settings → Sending Email): their
address and the mail server (guessed for Gmail, Outlook, Yahoo and
iCloud), kept in their settings (core/person_settings.py), and the
password, encrypted with a passphrase they choose
(`data/profiles/<id>/mail_send.enc`, core.secrets_manager, the same
scheme as the Plaid vault). For Gmail that's an app password (Google
Account → Security → 2-Step Verification → App passwords). The password
stays in memory only after the passphrase is typed, once per session.

A message is sent only by `send_draft()`, which only the Send buttons
call (desktop dialog, phone). Network waits happen off the screen's
thread; `send_in_background()` reports back on the main thread.
"""

from __future__ import annotations

import json
import smtplib
import threading
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Callable, Optional

from core import person_settings
from core.logger import get_logger
from core.profile_manager import looks_like_email
from core.secrets_manager import SecretsError, decrypt_bytes, encrypt_bytes

log = get_logger(__name__)

_TIMEOUT_SECONDS = 30
_VAULT_NAME = "mail_send.enc"

# (domain endings, host, port, security)
_KNOWN = (
    (("gmail.com", "googlemail.com"), "smtp.gmail.com", 465, "ssl"),
    (("outlook.com", "hotmail.com", "live.com", "msn.com"), "smtp.office365.com", 587, "starttls"),
    (("yahoo.com", "ymail.com"), "smtp.mail.yahoo.com", 465, "ssl"),
    (("icloud.com", "me.com", "mac.com"), "smtp.mail.me.com", 587, "starttls"),
    (("aol.com",), "smtp.aol.com", 465, "ssl"),
)


def guess_server(address: str) -> Optional[tuple[str, int, str]]:
    """Pure logic. (host, port, security) for well-known providers."""
    domain = (address or "").strip().lower().rpartition("@")[2]
    for endings, host, port, security in _KNOWN:
        if domain in endings:
            return host, port, security
    return None


def build_message(sender: str, to: list[str], subject: str, body: str, cc: Optional[list[str]] = None,
                  sender_name: str = "") -> EmailMessage:
    """Pure logic. A plain-text email."""
    message = EmailMessage()
    message["From"] = f"{sender_name} <{sender}>" if sender_name else sender
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=sender.rpartition("@")[2] or None)
    message.set_content(body)
    return message


def _connect(host: str, port: int, security: str) -> smtplib.SMTP:
    if security == "ssl":
        return smtplib.SMTP_SSL(host, port, timeout=_TIMEOUT_SECONDS)
    client = smtplib.SMTP(host, port, timeout=_TIMEOUT_SECONDS)
    client.starttls()
    return client


class SendError(Exception):
    """Something to tell the person, e.g. a wrong password."""


class MailSender:
    """One person's sending setup. `context` is that person's view (or the
    main context, for whoever is signed in)."""

    def __init__(self, context, folder: Optional[Path]) -> None:
        self.context = context
        self.folder = Path(folder) if folder is not None else None
        self._password: Optional[str] = None

    # ------------------------------------------------------------ settings

    def setting(self, key: str, default=None):
        return person_settings.get(self.context, f"email.send.{key}", default)

    @property
    def address(self) -> str:
        return self.setting("address", "") or ""

    @property
    def _vault(self) -> Optional[Path]:
        return self.folder / _VAULT_NAME if self.folder is not None else None

    @property
    def configured(self) -> bool:
        return bool(self.address and self.setting("host") and self._vault is not None and self._vault.exists())

    @property
    def unlocked(self) -> bool:
        return self._password is not None

    def setup(self, address: str, password: str, passphrase: str, host: str = "", port: int = 0,
              security: str = "") -> None:
        if not looks_like_email(address):
            raise SendError("That doesn't look like an email address.")
        if not password or not passphrase:
            raise SendError("The password and a passphrase are both needed.")
        guessed = guess_server(address)
        if not host and guessed is None:
            raise SendError("I don't know that provider's mail server; enter it (e.g. smtp.example.com).")
        host, port, security = (host or guessed[0], int(port or (guessed[1] if guessed else 587)),
                                security or (guessed[2] if guessed else "starttls"))
        for key, value in (("address", address.strip().lower()), ("host", host.strip()), ("port", port),
                           ("security", security)):
            person_settings.put(self.context, f"email.send.{key}", value)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._vault.write_bytes(encrypt_bytes(json.dumps({"password": password}).encode("utf-8"), passphrase))
        self._password = password

    def unlock(self, passphrase: str) -> bool:
        if self._vault is None or not self._vault.exists():
            return False
        try:
            self._password = json.loads(decrypt_bytes(self._vault.read_bytes(), passphrase))["password"]
            return True
        except (SecretsError, ValueError, KeyError):
            return False

    def forget(self) -> None:
        """Turn sending off: the stored password is deleted."""
        if self._vault is not None:
            self._vault.unlink(missing_ok=True)
        self._password = None
        person_settings.put(self.context, "email.send.address", "")

    # ------------------------------------------------------------ sending

    def send(self, draft, connect: Callable[[str, int, str], smtplib.SMTP] = _connect, sender_name: str = "") -> None:
        """Send now. Only the Send buttons call this. Raises SendError."""
        if not self.configured:
            raise SendError("Sending isn't set up. Use Copy or your mail app, or set it up in Settings.")
        if not self.unlocked:
            raise SendError("Sending is locked: enter your sending passphrase first.")
        recipients = [a for a in list(draft.to) + list(draft.cc) if looks_like_email(a)]
        if not recipients or len(recipients) != len(list(draft.to) + list(draft.cc)):
            raise SendError("Check the To address.")
        message = build_message(self.address, list(draft.to), draft.subject, draft.body, list(draft.cc), sender_name)
        try:
            client = connect(self.setting("host"), int(self.setting("port", 587)), self.setting("security", "starttls"))
            try:
                client.login(self.address, self._password)
                client.send_message(message)
            finally:
                try:
                    client.quit()
                except Exception:
                    pass
        except smtplib.SMTPAuthenticationError as exc:
            raise SendError("The mail server didn't accept the password. For Gmail, use an app password.") from exc
        except (smtplib.SMTPException, OSError) as exc:
            log.warning("Sending email failed: %s", exc)
            raise SendError("I couldn't reach the mail server. The draft is kept; try again or use Copy.") from exc
        log.info("Email sent to %d recipient(s).", len(recipients))


def sender_for(context, profile_id: Optional[str] = None) -> MailSender:
    """The sending setup of this person (or whoever is signed in). One per
    person per run, so the unlocked password is remembered for the session."""
    personal = getattr(context, "personal_data", None)
    profile_id = profile_id or person_settings.person_id(context)
    cache = getattr(context, "_mail_senders", None)
    if cache is None:
        cache = {}
        try:
            context._mail_senders = cache
        except AttributeError:
            pass
    if profile_id in cache:
        return cache[profile_id]
    view = personal.view(profile_id) if personal is not None and profile_id else context
    folder = personal.folder(profile_id) if personal is not None and profile_id else None
    sender = MailSender(view, folder)
    cache[profile_id] = sender
    return sender


def send_draft(context, profile_id: Optional[str], draft_id: str, connect=_connect) -> str:
    """Send one of this person's drafts and mark it sent. Returns what to
    tell them; raises SendError."""
    personal = getattr(context, "personal_data", None)
    view = personal.view(profile_id) if personal is not None and profile_id else context
    drafts = getattr(view, "email_drafts", None)
    draft = drafts.get(draft_id) if drafts is not None else None
    if draft is None or draft.status != "draft":
        raise SendError("That draft isn't there anymore (already sent?).")
    profiles = getattr(context, "profiles", None)
    person = profiles.get_profile(profile_id) if profiles is not None and profile_id else None
    sender_for(context, profile_id).send(draft, connect=connect, sender_name=person.name if person else "")
    drafts.mark(draft_id, "sent")
    return f"Sent to {', '.join(draft.to)}."


def send_in_background(context, profile_id: Optional[str], draft_id: str, done: Callable[[bool, str], None]) -> None:
    """For the desktop: send off the screen's thread, then call done(ok,
    message) back on the main thread."""
    def work() -> None:
        try:
            ok, message = True, send_draft(context, profile_id, draft_id)
        except SendError as exc:
            ok, message = False, str(exc)
        call = getattr(context, "main_thread_call", None)
        (call or (lambda fn: fn()))(lambda: done(ok, message))

    threading.Thread(target=work, daemon=True, name="mia-send-email").start()
