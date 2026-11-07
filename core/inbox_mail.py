"""
core.inbox_mail
==================

Optional email intake for the document inbox (core/inbox_manager.py,
2026-09-28). Two kinds of mailbox:
- **Dedicated** (a new address used only for sending MIA receipts and
  manuals): every new message is saved into the inbox folder as a .eml
  file and marked read.
- **Everyday** (the person's own mailbox, 2026-11-07, `fetch_receipts`):
  read without touching it (read-only, nothing marked read); only
  receipts, orders and service confirmations are taken, judged from the
  sender and subject (`looks_like_receipt`), and every other message is
  never downloaded. From a receipt the inbox works out what happened
  (core/receipt_effects.py).
MIA checks over IMAP, the standard mail-reading protocol (Python's own
imaplib, no new dependency). From there it's the same as any dropped
file.

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
import re
import threading
from datetime import date, timedelta
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
        """The inbox mailbox's settings, kept in the config under inbox.email.* (never the password)."""
        self.context = context

    def get(self, key: str, default=None):
        """One mailbox setting (inbox.email.<key>)."""
        return self.context.config.get(f"inbox.email.{key}", default)

    @property
    def configured(self) -> bool:
        """Whether a mailbox is set up: a host and username, and a stored (encrypted) password."""
        return bool(self.get("host") and self.get("username")) and _VAULT_FILE.exists()

    @property
    def everyday(self) -> bool:
        """Whether this is the person's own everyday mailbox (read without touching it, receipts only) rather than a
        mailbox kept just for MIA."""
        return self.get("mode", "dedicated") == "everyday"

    def save(self, host: str, username: str, port: int = 993, folder: str = "INBOX", everyday: bool = False) -> None:
        """Saves the mailbox's host, username, port (993 by default), folder (INBOX by default), and whether it's the
        person's everyday mailbox."""
        config = self.context.config
        config.set("inbox.email.mode", "everyday" if everyday else "dedicated")
        config.set("inbox.email.host", host.strip())
        config.set("inbox.email.username", username.strip())
        config.set("inbox.email.port", int(port))
        config.set("inbox.email.folder", folder.strip() or "INBOX")
        config.save()


class MailVault:
    """The mailbox password, encrypted with the person's passphrase in data/inbox_mail.enc (core/secrets_manager.py)
    and held in memory only while unlocked; locked, MIA just doesn't check mail.
    """
    def __init__(self) -> None:
        """Starts locked: nothing is read until unlock()."""
        self._password: Optional[str] = None

    @property
    def unlocked(self) -> bool:
        """Whether the password is in memory now."""
        return self._password is not None

    @staticmethod
    def exists() -> bool:
        """Whether a password has been stored."""
        return _VAULT_FILE.exists()

    def store(self, password: str, passphrase: str) -> None:
        """Encrypts and stores the password with the passphrase, and holds it unlocked."""
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
        """Unlocks with the passphrase; False (rather than an error) when it's wrong or nothing is stored."""
        try:
            self.unlock(passphrase)
            return True
        except (SecretsError, ValueError, KeyError):
            return False

    def lock(self) -> None:
        """Forgets the password in memory."""
        self._password = None

    @property
    def password(self) -> Optional[str]:
        """The password while unlocked, else None."""
        return self._password


_TIMEOUT_SECONDS = 30  # a dead network must not leave the check hanging forever


def _connect_ssl(host: str, port: int) -> imaplib.IMAP4:
    """An IMAP connection over SSL, with a timeout."""
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


# ------------------------------------------------------------------ an everyday mailbox (Zac, 2026-11-07)
#
# "Read my emails so she can gain context on things getting done, being purchased": the person's own mailbox, not
# a dedicated one. So it is read without touching it (the folder opened read-only, messages fetched with PEEK:
# nothing is marked read, moved or deleted), and only receipts, orders and service confirmations are taken: every
# other message is judged by its sender and subject alone and never downloaded. Which messages were already seen is
# kept by IMAP's message number (UID) in data/inbox_mail_state.json, never by anything in the mail.

_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "inbox_mail_state.json"
FIRST_LOOK_DAYS = 30  # the first check looks back this far

_RECEIPT_SUBJECT = re.compile(
    r"\b(receipt|e-?receipt|your order|order (confirmation|confirmed|#|number|placed|received|shipped|delivered|"
    r"is on (its|the) way|has shipped|has been delivered)|purchase|invoice|thank(s| you) for (your )?(order|purchase|"
    r"shopping|visit|business)|payment (received|confirmation)|service (complete|completed|summary|record|invoice)|"
    r"(appointment|reservation) confirm|transaction|pickup (ready|order)|curbside)\b", re.I)
_RECEIPT_SENDER = re.compile(
    r"(receipt|order|purchase|billing|invoice|lowes|homedepot|menards|acehardware|tractorsupply|walmart|target|"
    r"costco|samsclub|kroger|aldi|publix|instacart|amazon|jiffylube|valvoline|firestone|pepboys|discounttire|"
    r"goodyear|meineke|take5)", re.I)
_PROMOTION = re.compile(r"(\d+% off|\bsale\b|\bdeals?\b|\bsave \$|\bcoupon|\bnewsletter|\bwebinar|unsubscribe)",
                        re.I)


def looks_like_receipt(sender: str, subject: str) -> bool:
    """Pure logic. Whether a message is worth taking, from its sender and subject only: a receipt, an order, a
    payment or a service confirmation, not a promotion."""
    subject, sender = subject or "", sender or ""
    if _RECEIPT_SUBJECT.search(subject):
        return not (_PROMOTION.search(subject) and not re.search(r"receipt|order #|order number|invoice", subject, re.I))
    return bool(_RECEIPT_SENDER.search(sender)) and bool(re.search(r"order|receipt|purchase|thank", subject, re.I)) \
        and not _PROMOTION.search(subject)


def _header(raw: bytes, name: str) -> str:
    """One header's value from raw header bytes, decoded for reading."""
    from email import message_from_bytes, policy

    try:
        return str(message_from_bytes(raw, policy=policy.default).get(name, "") or "")
    except Exception:
        return ""


def load_state(path: Path = _STATE_FILE) -> dict:
    """Where the last check of the everyday mailbox got to: {uidvalidity, last_uid}; {} the first time."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict, path: Path = _STATE_FILE) -> None:
    """Keeps where the check got to (message numbers only, nothing from the mail)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(state))


def fetch_receipts(
    host: str, username: str, password: str, port: int = 993, folder: str = "INBOX",
    connect: Callable[[str, int], imaplib.IMAP4] = _connect_ssl, state: Optional[dict] = None, limit: int = 40,
    today: Optional[date] = None,
) -> tuple[list[bytes], dict]:
    """The receipts, orders and service confirmations that arrived since the last check, from an everyday mailbox
    left exactly as it was (read-only; nothing marked read). Returns (raw messages, the new state). The first check
    looks back FIRST_LOOK_DAYS. Raises imaplib.IMAP4.error / OSError on login or network failure."""
    state = dict(state or {})
    client = connect(host, port)
    try:
        client.login(username, password)
        client.select(folder, readonly=True)
        _typ, validity = client.response("UIDVALIDITY")
        uidvalidity = (validity[0].decode() if validity and isinstance(validity[0], bytes) else str(validity[0])) \
            if validity and validity[0] else ""
        last = int(state.get("last_uid", 0)) if state.get("uidvalidity") == uidvalidity else 0
        if last:
            status, data = client.uid("SEARCH", None, f"UID {last + 1}:*")
        else:
            since = (today or date.today()) - timedelta(days=FIRST_LOOK_DAYS)
            status, data = client.uid("SEARCH", None, "SINCE", since.strftime("%d-%b-%Y"))
        uids = sorted(int(u) for u in (data[0].split() if status == "OK" and data and data[0] else []))
        uids = [u for u in uids if u > last]
        messages = []
        for uid in uids[-limit:]:
            status, parts = client.uid("FETCH", str(uid), "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            head = next((p[1] for p in parts if isinstance(p, tuple) and len(p) > 1), b"") if status == "OK" else b""
            if not looks_like_receipt(_header(head, "From"), _header(head, "Subject")):
                continue
            status, parts = client.uid("FETCH", str(uid), "(BODY.PEEK[])")
            raw = next((p[1] for p in parts if isinstance(p, tuple) and len(p) > 1), None) if status == "OK" else None
            if raw:
                messages.append(raw)
        new_last = max(uids) if uids else last
        return messages, {"uidvalidity": uidvalidity, "last_uid": new_last}
    finally:
        try:
            client.logout()
        except Exception:
            pass


class MailChecker:
    """Runs one check at a time on a background thread."""

    def __init__(self, inbox, settings: MailSettings, vault: MailVault) -> None:
        """Checks the mailbox into the inbox, on a background thread; last_result says how the last check went; an
        everyday mailbox's place is kept in state_file."""
        self.inbox, self.settings, self.vault = inbox, settings, vault
        self.state_file = _STATE_FILE
        self._thread: Optional[threading.Thread] = None
        self.last_result = ""

    def check_now(self, fetch=None, wait: bool = False) -> bool:
        """Start a check (fetch: the mail reader, by default the one for this mailbox's kind). False when it can't
        run (not set up, locked, or already running)."""
        if not (self.settings.configured and self.vault.unlocked) or (self._thread and self._thread.is_alive()):
            return False
        self._thread = threading.Thread(target=self._run, args=(fetch,), name="mia-inbox-mail", daemon=True)
        self._thread.start()
        if wait:
            self._thread.join(timeout=60)
        return True

    def _run(self, fetch) -> None:
        """One check (on its thread): fetches the new messages (from an everyday mailbox, only receipts and orders,
        left unread), saves each into the inbox as an email file, and says how many came; a mail or network error is
        logged and said, never raised.
        """
        try:
            args = (self.settings.get("host"), self.settings.get("username"), self.vault.password,
                    int(self.settings.get("port", 993)), self.settings.get("folder", "INBOX"))
            if self.settings.everyday:
                reader = fetch or fetch_receipts
                messages, state = reader(*args, state=load_state(self.state_file))
                save_state(state, self.state_file)
            else:
                messages = (fetch or fetch_new_messages)(*args)
            for raw in messages:
                self.inbox.receive_file("message.eml", raw, source="email")
            self.last_result = (f"Checked email: {len(messages)} new receipts and orders." if self.settings.everyday
                                else f"Checked email: {len(messages)} new.")
        except (imaplib.IMAP4.error, OSError) as exc:
            log.warning("Email check failed: %s", exc)
            self.last_result = f"Couldn't check email: {exc}"
