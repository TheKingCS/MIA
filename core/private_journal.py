"""
core.private_journal
=======================

The encrypted private journal — slice A ("Talk it out") of
docs/COGNITIVE_EXTENSION_PROPOSAL.md. Conversations the user journals
with MIA are saved here, one entry per journaling session, organized
(title, mood, themes, summary) and kept encrypted at rest. Separate
from core/journal_manager.py (the Notes module's plain entries), which
stays unencrypted and unchanged.

**Write without the passphrase, read only with it.** The owner chose
encryption, and MIA is meant to run 24/7 on the home machine and take
journaling from the phone. If every write needed the passphrase, a
reboot would silently stop the journal until someone unlocked it at
the desk. So each entry is encrypted with its own random Fernet key,
and that key is wrapped with an RSA public key (RSA-OAEP, SHA-256).
The public key sits in plain text and can only lock things; the
matching private key is itself encrypted with the owner's passphrase
using core.secrets_manager (the same PBKDF2 + Fernet scheme as Plaid's
vault and encrypted backups). Result: MIA can always *write* an
entry, and nobody, MIA included, can *read* one until the owner
unlocks with the passphrase.

What stays readable on disk: each entry's id and created/updated
timestamps (so MIA can replace an entry and count them while locked).
Everything else, including the title, is inside the ciphertext.

Files (data/, gitignored like all runtime state):
- private_journal_keys.json: public key PEM + passphrase-encrypted private key
- private_journal.json: the encrypted entries

The unlocked private key lives only in memory for this run, never
re-persisted in plaintext, same discipline as core/plaid_manager.py.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from core.app_context import AppContext
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger
from core.secrets_manager import SecretsError, decrypt_bytes, encrypt_bytes

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_KEYS_FILE = _DATA_DIR / "private_journal_keys.json"
_ENTRIES_FILE = _DATA_DIR / "private_journal.json"

_OAEP = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
_MIN_PASSPHRASE_LENGTH = 8
_RSA_KEY_SIZE = 3072


class JournalLockedError(Exception):
    """Reading the private journal needs unlock(passphrase) first."""


@dataclass
class JournalExchange:
    role: str  # "user" | "assistant"
    content: str
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @staticmethod
    def from_dict(data: dict) -> "JournalExchange":
        return JournalExchange(data.get("role", "user"), data.get("content", ""), data.get("timestamp", ""))


@dataclass
class PrivateJournalEntry:
    entry_id: str
    title: str = "Journal session"
    summary: str = ""
    mood: str = ""  # the user's own word(s), never a score
    themes: list[str] = field(default_factory=list)
    exchanges: list[JournalExchange] = field(default_factory=list)
    conversation_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    @property
    def user_text(self) -> str:
        return "\n".join(e.content for e in self.exchanges if e.role == "user")

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "title": self.title,
            "summary": self.summary,
            "mood": self.mood,
            "themes": list(self.themes),
            "exchanges": [e.to_dict() for e in self.exchanges],
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PrivateJournalEntry":
        return PrivateJournalEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            title=data.get("title", "Journal session"),
            summary=data.get("summary", ""),
            mood=data.get("mood", ""),
            themes=list(data.get("themes", [])),
            exchanges=[JournalExchange.from_dict(d) for d in data.get("exchanges", [])],
            conversation_id=data.get("conversation_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


class PrivateJournalManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._public_key = None
        self._private_key = None  # set only while unlocked
        self._records: list[dict] = []  # {entry_id, created_at, updated_at, key, data}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if _KEYS_FILE.exists():
            try:
                keys = json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
                self._public_key = serialization.load_pem_public_key(keys["public_key"].encode("ascii"))
            except (json.JSONDecodeError, OSError, KeyError, ValueError):
                log.exception("Failed to load private_journal_keys.json — the private journal can't be written.")
                notify_data_corruption(self.context, "private_journal_keys.json")
                self._public_key = None
        if _ENTRIES_FILE.exists():
            try:
                self._records = list(json.loads(_ENTRIES_FILE.read_text(encoding="utf-8")).get("entries", []))
            except (json.JSONDecodeError, OSError, AttributeError):
                log.exception("Failed to load private_journal.json — starting with an empty list.")
                notify_data_corruption(self.context, "private_journal.json")
                self._records = []

    def _save_records(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_ENTRIES_FILE, json.dumps({"version": 1, "entries": self._records}, indent=2))

    # ------------------------------------------------------------------
    # Setup / lock state
    # ------------------------------------------------------------------

    def is_set_up(self) -> bool:
        return self._public_key is not None

    def is_unlocked(self) -> bool:
        return self._private_key is not None

    def setup(self, passphrase: str) -> None:
        """First-time setup. Creates the keypair and leaves the journal unlocked."""
        if self.is_set_up():
            raise SecretsError("The private journal is already set up.")
        if len(passphrase) < _MIN_PASSPHRASE_LENGTH:
            raise SecretsError(f"Use a passphrase of at least {_MIN_PASSPHRASE_LENGTH} characters.")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=_RSA_KEY_SIZE)
        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_KEYS_FILE, json.dumps({
            "version": 1,
            "public_key": public_pem.decode("ascii"),
            "private_key": _b64(encrypt_bytes(private_pem, passphrase)),
        }, indent=2))
        self._public_key = private_key.public_key()
        self._private_key = private_key
        log.info("Private journal set up.")

    def verify_passphrase(self, passphrase: str) -> bool:
        try:
            self._decrypt_private_key(passphrase)
        except SecretsError:
            return False
        return True

    def unlock(self, passphrase: str) -> None:
        """Raises SecretsError on a wrong passphrase or missing/corrupted key file."""
        self._private_key = self._decrypt_private_key(passphrase)
        log.info("Private journal unlocked (%d entries).", len(self._records))

    def lock(self) -> None:
        self._private_key = None

    def _decrypt_private_key(self, passphrase: str):
        if not _KEYS_FILE.exists():
            raise SecretsError("The private journal hasn't been set up yet.")
        try:
            keys = json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
            blob = _unb64(keys["private_key"])
        except (json.JSONDecodeError, OSError, KeyError, ValueError) as exc:
            raise SecretsError("The private journal's key file is unreadable.") from exc
        private_pem = decrypt_bytes(blob, passphrase)
        return serialization.load_pem_private_key(private_pem, password=None)

    # ------------------------------------------------------------------
    # Entries
    # ------------------------------------------------------------------

    def entry_count(self) -> int:
        """Works while locked."""
        return len(self._records)

    def save_entry(self, entry: PrivateJournalEntry) -> PrivateJournalEntry:
        """Insert or replace by entry_id. Works while locked (public key only)."""
        if not self.is_set_up():
            raise SecretsError("The private journal hasn't been set up yet.")
        now = datetime.now().isoformat(timespec="seconds")
        entry.created_at = entry.created_at or now
        entry.updated_at = now
        entry_key = Fernet.generate_key()
        record = {
            "entry_id": entry.entry_id,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "key": _b64(self._public_key.encrypt(entry_key, _OAEP)),
            "data": _b64(Fernet(entry_key).encrypt(json.dumps(entry.to_dict()).encode("utf-8"))),
        }
        self._records = [r for r in self._records if r.get("entry_id") != entry.entry_id] + [record]
        self._save_records()
        return entry

    def _decrypt_record(self, record: dict) -> Optional[PrivateJournalEntry]:
        try:
            entry_key = self._private_key.decrypt(_unb64(record["key"]), _OAEP)
            plaintext = Fernet(entry_key).decrypt(_unb64(record["data"]))
            return PrivateJournalEntry.from_dict(json.loads(plaintext))
        except Exception:
            log.exception("Couldn't decrypt private journal entry %s — skipped.", record.get("entry_id"))
            return None

    def all_entries(self) -> list[PrivateJournalEntry]:
        """Newest first. Raises JournalLockedError while locked."""
        if not self.is_unlocked():
            raise JournalLockedError("The private journal is locked.")
        entries = [e for e in (self._decrypt_record(r) for r in self._records) if e is not None]
        return sorted(entries, key=lambda e: e.created_at, reverse=True)

    def get_entry(self, entry_id: str) -> Optional[PrivateJournalEntry]:
        return next((e for e in self.all_entries() if e.entry_id == entry_id), None)

    def delete_entry(self, entry_id: str) -> bool:
        before = len(self._records)
        self._records = [r for r in self._records if r.get("entry_id") != entry_id]
        if len(self._records) == before:
            return False
        self._save_records()
        return True

    def search(self, query: str) -> list[PrivateJournalEntry]:
        """Entries whose title, themes, mood, summary or words match every query word. Newest first."""
        words = [w for w in re.findall(r"[a-z0-9']+", query.lower()) if len(w) > 2]
        entries = self.all_entries()
        if not words:
            return entries
        matches = []
        for entry in entries:
            haystack = " ".join([entry.title, entry.summary, entry.mood, " ".join(entry.themes), entry.user_text]).lower()
            if all(w.rstrip("s") in haystack for w in words):
                matches.append(entry)
        return matches
