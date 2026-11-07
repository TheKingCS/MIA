"""
core.password_vault
=====================

Passwords (Zac, 2026-10-20, DEC-0035): every login a person has, kept
in a vault only their own master password opens.

**How it's locked.** The vault has one random 256-bit key. That key is
stored twice, each copy encrypted (AES-256-GCM): once with a key made
from the master password, once with a key made from a recovery code shown
once when the vault is made. Both are made with scrypt (slow and
memory-hard on purpose, so guessing is expensive). Every login is
encrypted on its own with the vault key, its id bound in (so records can't
be swapped), title included: a locked vault shows only how many there are.
Changing the master password re-locks the key, not every login.

**Unlocked** means the vault key is held in this process's memory only
(`_open`), for as long as the person keeps using it: it locks itself after
LOCK_AFTER_SECONDS without use, and on Lock. It's never written anywhere
unencrypted, never logged, and never given to MIA's assistant: no tool
can read a password, none appear in an action's record, the history, the
undo log (only the encrypted file), Life State or the glasses.

**Guessing** a master password: after a few wrong tries, a wait that
doubles each time.

**Sync** (core/sync.py): the file moves encrypted. Two devices sync
logins only when they hold the same vault (`vault_id`); each login merges
whole, the newer one winning.

Grown-ups only (not in CHILD_APPS). The forgotten-both case is final:
without the master password or the recovery code, nobody can open it.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import os
import secrets
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILE_NAME = "password_vault.json"
LOCK_AFTER_SECONDS = 5 * 60
MIN_MASTER_LENGTH = 10
SCRYPT = {"n": 2 ** 15, "r": 8, "p": 1}
FREE_TRIES = 5
_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I


class VaultError(Exception):
    """Something the person can act on ("That's not the master password.")."""


class VaultLocked(VaultError):
    """Raised when something needs the vault open and it's locked."""
    pass


@dataclass
class Login:
    """One login, as it is only while the vault is open: title, username, password, site, note, folder and when it
    last changed. Never stored like this: each is sealed on its own in the file.
    """
    entry_id: str
    title: str
    username: str = ""
    password: str = ""
    url: str = ""
    note: str = ""
    folder: str = ""
    updated_at: str = ""

    def public(self) -> dict:
        """What a list shows: everything but the password."""
        out = asdict(self)
        out.pop("password")
        out["has_password"] = bool(self.password)
        return out


# ------------------------------------------------------------------ crypto


def _b64(data: bytes) -> str:
    """Bytes as base64 text, for the JSON file."""
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    """Base64 text back to bytes."""
    return base64.b64decode(text.encode("ascii"))


def _derive(secret: str, salt: bytes, params: dict) -> bytes:
    """A 32-byte key from a secret (the master password or recovery code) with scrypt, using the salt and cost
    parameters stored with it (slow and memory-hard on purpose).
    """
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    return Scrypt(salt=salt, length=32, n=int(params["n"]), r=int(params["r"]), p=int(params["p"])).derive(
        secret.encode("utf-8"))


def _wrap(secret: str, vault_key: bytes) -> dict:
    """Seals the vault key with a secret: a fresh salt and nonce, a key derived from the secret, AES-256-GCM (bound to
    "mia-vault-key"). What's stored is the salt, nonce, sealed key and the scrypt parameters.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt, nonce = os.urandom(16), os.urandom(12)
    sealed = AESGCM(_derive(secret, salt, SCRYPT)).encrypt(nonce, vault_key, b"mia-vault-key")
    return {"salt": _b64(salt), "nonce": _b64(nonce), "key": _b64(sealed), **SCRYPT}


def _unwrap(secret: str, wrap: dict) -> Optional[bytes]:
    """The vault key opened with a secret, or None when the secret is wrong or the record is damaged (GCM's tag check
    fails).
    """
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        kek = _derive(secret, _unb64(wrap["salt"]), wrap)
        return AESGCM(kek).decrypt(_unb64(wrap["nonce"]), _unb64(wrap["key"]), b"mia-vault-key")
    except (InvalidTag, KeyError, ValueError, TypeError):
        return None


def _seal(vault_key: bytes, entry_id: str, payload: dict) -> dict:
    """Encrypts one login's fields with the vault key (AES-256-GCM, a fresh nonce), its id bound in so records can't
    be swapped between ids.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    data = AESGCM(vault_key).encrypt(nonce, json.dumps(payload).encode("utf-8"), entry_id.encode("utf-8"))
    return {"nonce": _b64(nonce), "data": _b64(data)}


def _open_record(vault_key: bytes, record: dict) -> Optional[dict]:
    """One login's fields decrypted, or None when it can't be (wrong key, damaged, or moved to another id)."""
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        raw = AESGCM(vault_key).decrypt(_unb64(record["nonce"]), _unb64(record["data"]),
                                        str(record["entry_id"]).encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except (InvalidTag, KeyError, ValueError, TypeError):
        return None


def recovery_code() -> str:
    """Pure logic. 25 characters in five groups: ABCDE-FGHJK-…"""
    raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(25))
    return "-".join(raw[i:i + 5] for i in range(0, 25, 5))


def _clean_code(code: str) -> str:
    """A recovery code as typed, reduced to its letters and digits in capitals (spaces and dashes don't matter)."""
    return "".join(ch for ch in str(code or "").upper() if ch.isalnum())


# ------------------------------------------------------------------ who has it open (memory only)

_open: dict[str, tuple[bytes, float]] = {}  # vault file → (vault key, last used, monotonic)
_tries: dict[str, tuple[int, float]] = {}  # vault file → (wrong tries, not before)
_lock = threading.Lock()


class PasswordVault:
    """One person's vault (a personal store: their folder)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Opens the person's vault file (in their folder, data/ by default). Nothing is decrypted here."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self._load()

    def _load(self) -> None:
        """Reads the header (the two sealed copies of the key) and the sealed logins; a file it can't read is logged and
        left unchanged on disk.
        """
        self.header: dict = {}
        self.records: list[dict] = []
        if not self._file.exists():
            return
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            self.header = dict(data.get("header") or {})
            self.records = list(data.get("entries") or [])
        except (OSError, ValueError, AttributeError):
            log.exception("Couldn't read %s (it's unchanged on disk).", FILE_NAME)

    def _save(self) -> None:
        """Writes the header and sealed logins atomically (the only form that's ever written)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "header": self.header, "entries": self.records},
                                                 indent=1))

    @property
    def _key_id(self) -> str:
        """Which vault this is, by its file's full path: the key held in memory is kept under it."""
        return str(self._file.resolve())

    # -- state
    def is_set_up(self) -> bool:
        """Whether a vault has been made (it has a master-password copy of the key)."""
        return bool(self.header.get("password"))

    def is_unlocked(self) -> bool:
        """Whether the vault is open now (without counting as a use)."""
        return self._vault_key(touch=False) is not None

    def _vault_key(self, touch: bool = True) -> Optional[bytes]:
        """The vault key from this process's memory, or None when it's locked or has gone unused for
        LOCK_AFTER_SECONDS (5 minutes: it locks itself then). touch=True counts this as a use.
        """
        with _lock:
            held = _open.get(self._key_id)
            if held is None:
                return None
            key, last = held
            if time.monotonic() - last > LOCK_AFTER_SECONDS:
                del _open[self._key_id]
                return None
            if touch:
                _open[self._key_id] = (key, time.monotonic())
            return key

    def _need_key(self) -> bytes:
        """The vault key, or VaultLocked."""
        key = self._vault_key()
        if key is None:
            raise VaultLocked("The vault is locked. Unlock it with your master password.")
        return key

    def count(self) -> int:
        """How many logins are in the vault (shown even while it's locked; nothing else is)."""
        return len(self.records)

    # -- making, opening, locking
    def setup(self, master: str) -> str:
        """Make the vault. Returns the recovery code (shown once, never stored)."""
        if self.is_set_up():
            raise VaultError("You already have a vault.")
        _check_master(master)
        key, code = os.urandom(32), recovery_code()
        self.header = {"vault_id": uuid.uuid4().hex, "password": _wrap(master, key),
                       "recovery": _wrap(_clean_code(code), key), "created_at": _now()}
        self.records = []
        self._save()
        with _lock:
            _open[self._key_id] = (key, time.monotonic())
        return code

    def unlock(self, master: str = "", recovery: str = "") -> None:
        """Opens the vault with the master password or the recovery code, holding its key in memory only. From the fifth
        wrong try, a wait of 15 s that doubles with each more (capped at about 4 hours), enforced here.
        """
        if not self.is_set_up():
            raise VaultError("There's no vault yet.")
        with _lock:
            wrong, not_before = _tries.get(self._key_id, (0, 0.0))
        wait = not_before - time.monotonic()
        if wait > 0:
            raise VaultError(f"Too many wrong tries. Wait {int(wait) + 1} seconds.")
        key = (_unwrap(_clean_code(recovery), self.header["recovery"]) if recovery
               else _unwrap(master, self.header["password"]))
        if key is None:
            wrong += 1
            delay = 0 if wrong < FREE_TRIES else 2 ** min(wrong - FREE_TRIES, 10) * 15
            with _lock:
                _tries[self._key_id] = (wrong, time.monotonic() + delay)
            raise VaultError("That's not the recovery code." if recovery else "That's not the master password.")
        with _lock:
            _tries.pop(self._key_id, None)
            _open[self._key_id] = (key, time.monotonic())

    def lock(self) -> None:
        """Locks the vault now (forgets the key in memory)."""
        with _lock:
            _open.pop(self._key_id, None)

    def change_master(self, current: str, new: str) -> None:
        """Changes the master password: checks the current one, then re-seals the same vault key with the new one (the
        logins aren't touched). Needs the vault open.
        """
        if _unwrap(current, self.header.get("password") or {}) is None:
            raise VaultError("That's not your current master password.")
        _check_master(new)
        key = self._need_key()
        self.header["password"] = _wrap(new, key)
        self._save()

    def reset_master(self, new: str) -> None:
        """After unlocking with the recovery code: a new master password."""
        _check_master(new)
        self.header["password"] = _wrap(new, self._need_key())
        self._save()

    # -- logins
    def logins(self) -> list[Login]:
        """Every login, decrypted (needs the vault open), by folder then title; one that can't be opened is logged and left
        as it is.
        """
        key = self._need_key()
        out = []
        for r in self.records:
            data = _open_record(key, r)
            if data is None:
                log.warning("A vault login couldn't be opened; it's left as it is.")
                continue
            out.append(Login(entry_id=r["entry_id"], updated_at=r.get("updated_at", ""),
                             **{k: str(data.get(k) or "") for k in ("title", "username", "password", "url", "note",
                                                                     "folder")}))
        return sorted(out, key=lambda l: (l.folder.lower(), l.title.lower()))

    def get(self, entry_id: str) -> Login:
        """One login by id, decrypted, or VaultError when it isn't there."""
        found = next((l for l in self.logins() if l.entry_id == entry_id), None)
        if found is None:
            raise VaultError("That login isn't in the vault anymore.")
        return found

    def save(self, title: str, username: str = "", password: str = "", url: str = "", note: str = "",
             folder: str = "", entry_id: str = "", keep_password: bool = False) -> Login:
        """Add a login, or change one (`entry_id`). keep_password: leave its password as it is."""
        key = self._need_key()
        title = " ".join(str(title or "").split())
        if not title:
            raise VaultError("Give the login a name, like the website or app.")
        if entry_id and keep_password:
            password = self.get(entry_id).password
        entry_id = entry_id or uuid.uuid4().hex[:12]
        login = Login(entry_id=entry_id, title=title, username=str(username or "").strip(), password=str(password or ""),
                      url=str(url or "").strip(), note=str(note or ""), folder=str(folder or "").strip(),
                      updated_at=_now())
        payload = {k: v for k, v in asdict(login).items() if k not in ("entry_id", "updated_at")}
        record = {"entry_id": entry_id, "updated_at": login.updated_at, **_seal(key, entry_id, payload)}
        self.records = [r for r in self.records if r.get("entry_id") != entry_id] + [record]
        self._save()
        return login

    def delete(self, entry_id: str) -> None:
        """Deletes a login (needs the vault open; VaultError when it isn't there)."""
        self._need_key()
        if not any(r.get("entry_id") == entry_id for r in self.records):
            raise VaultError("That login isn't in the vault anymore.")
        self.records = [r for r in self.records if r.get("entry_id") != entry_id]
        self._save()

    def import_csv(self, text: str) -> int:
        """Logins from a Chrome, Edge, Firefox, Bitwarden or 1Password CSV
        export. Returns how many came in (an identical one isn't doubled)."""
        self._need_key()
        have = {(l.title.lower(), l.username.lower(), l.password) for l in self.logins()}
        added = 0
        for row in read_csv(text):
            sig = (row["title"].lower(), row["username"].lower(), row["password"])
            if sig in have or not (row["password"] or row["username"]):
                continue
            self.save(**row)
            have.add(sig)
            added += 1
        return added

    def health(self) -> dict:
        """Reused and weak passwords (checked here, in memory, never stored)."""
        logins = self.logins()
        seen: dict[str, list[str]] = {}
        for l in logins:
            if l.password:
                seen.setdefault(l.password, []).append(l.entry_id)
        reused = {i for ids in seen.values() if len(ids) > 1 for i in ids}
        weak = {l.entry_id for l in logins if l.password and strength(l.password) < 3}
        return {"reused": sorted(reused), "weak": sorted(weak)}


def _check_master(master: str) -> None:
    """A master password must be at least 10 characters (VaultError suggesting a few unrelated words)."""
    if len(master or "") < MIN_MASTER_LENGTH:
        raise VaultError(f"Make the master password at least {MIN_MASTER_LENGTH} characters. "
                         "A few unrelated words make a strong one you can remember.")


def _now() -> str:
    """Now, as an ISO timestamp to the second."""
    return datetime.now().isoformat(timespec="seconds")


def strength(password: str) -> int:
    """Pure logic. 0 (very weak) to 4 (strong), roughly by length and variety."""
    if not password:
        return 0
    kinds = sum(any(test(ch) for ch in password) for test in (str.islower, str.isupper, str.isdigit,
                                                               lambda c: not c.isalnum()))
    n = len(password)
    if n < 8:
        return 0 if n < 6 else 1
    score = 1 + (n >= 12) + (n >= 16) + (kinds >= 3)
    return min(4, score)


# Column names in the exports people have (Chrome/Edge, Firefox, Bitwarden, 1Password, LastPass).
_CSV_COLUMNS = {
    "title": ("name", "title", "login_name"),
    "url": ("url", "login_uri", "website", "uri"),
    "username": ("username", "login_username", "user", "email"),
    "password": ("password", "login_password"),
    "note": ("note", "notes", "extra"),
    "folder": ("folder", "grouping", "group"),
}


def read_csv(text: str) -> list[dict]:
    """Pure logic. The logins in a password export, as save() takes them."""
    rows = []
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    fields_ = {(f or "").strip().lower(): f for f in reader.fieldnames or []}
    pick = {k: next((fields_[c] for c in cols if c in fields_), None) for k, cols in _CSV_COLUMNS.items()}
    if pick["password"] is None:
        raise VaultError("That doesn't look like a password export (no password column).")
    for raw in reader:
        row = {k: (raw.get(col) or "").strip() if col else "" for k, col in pick.items()}
        row["password"] = (raw.get(pick["password"]) or "")  # passwords keep their spaces
        if not row["title"]:
            row["title"] = _site_name(row["url"]) or row["username"] or "Login"
        rows.append(row)
    return rows


def _site_name(url: str) -> str:
    """A site's host name from a URL (or a bare domain), without "www.": an imported login's title when it has none,
    and the site a list shows.
    """
    from urllib.parse import urlparse

    host = urlparse(url if "://" in url else "https://" + url).hostname or ""
    host = host[4:] if host.startswith("www.") else host
    return host


# ------------------------------------------------------------------ the screen


def vault_page(context) -> dict:
    """The Passwords screen. Never a password: those come one at a time from reveal()."""
    vault = getattr(context, "passwords", None)
    if vault is None:
        return {"available": False}
    out = {"available": True, "set_up": vault.is_set_up(), "unlocked": vault.is_unlocked(), "count": vault.count(),
           "lock_after_minutes": LOCK_AFTER_SECONDS // 60, "min_master": MIN_MASTER_LENGTH}
    if out["unlocked"]:
        logins = vault.logins()
        health = vault.health()
        out["logins"] = [{**l.public(), "site": _site_name(l.url) if l.url else "",
                          "reused": l.entry_id in health["reused"], "weak": l.entry_id in health["weak"]}
                         for l in logins]
        out["folders"] = sorted({l.folder for l in logins if l.folder})
        out["health"] = {"reused": len(health["reused"]), "weak": len(health["weak"])}
    return out
