"""
core.at_rest
==============

MIA encrypts her own data at rest (DEC-0126, docs/SECURITY.md step 2): the most private stores' files are sealed with
AES-256-GCM under one data key, so a drive read on another computer (a stolen PC, a pulled disk, a backup copied off)
shows nothing but noise.

**Where it happens.** In the one place stores already write through: `core.atomic_write.atomic_write_text` calls
`seal_text`, which seals a file whose name is in `SEALED` and leaves every other file as it was. The matching read is
`open_text` (and `open_bytes`, for sync and export, which want the person's real content): a sealed file is opened, a
plain one is returned as it is, so each store reads both ways while it moves. A store moves the next time it saves.

**The data key.** 32 random bytes, kept in data/.keys/data_key.json protected by Windows DPAPI (`_protect`): tied to
the Windows sign-in, so there's nothing to type when MIA starts, and the file is useless anywhere else. A sealed file
names the key it was sealed with (`_kid`); the key file can hold more than one, so a recovered key (`restore`) opens
old files while new ones use the current key. Where DPAPI isn't (Linux, the phone until its Keystore step) nothing is
sealed: files stay plain and `status()` says so.

**Never losing a file.** Two rules: a file that can't be opened (a key that's gone, a damaged file) is copied aside
(`<name>.unreadable-<time>`) before the error goes up, because a store that can't read its file starts empty and its
next save would replace it; and a key file that exists but won't open (another Windows account, Windows reinstalled)
is never replaced: sealing stops (`status()` reports it, the security log alerts) until the recovery key is entered.
The recovery key (`recovery_key()`, `python -m tools.data_key recovery`) is the data key written out to keep in a
password manager: with it, the files open on any computer.

Envelope: one text line, ``MIA-SEALED-1:<kid>:<base64(nonce + ciphertext)>``, so a sealed file is still a text file
(sync, undo and backups move it unchanged). The prefix and key id are the GCM associated data.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / "data" / ".keys"
KEY_NAME = "data_key.json"
PREFIX = "MIA-SEALED-1:"
_ENTROPY = b"MIA data key (DEC-0126)"

# The files sealed, most private first (DEC-0126: moved store by store). A name here is sealed in every folder.
SEALED = frozenset({
    "conversations.json",  # every conversation with MIA
    "user_memories.json",  # what she remembers about the person
    "journal_entries.json",  # their notes
    "life_notes.json",  # promises, decisions, ideas set aside
    # stage 2 (2026-11-08): people, money, where they've been, how they live
    "relationships_people.json",  # the people in their life, birthdays, notes
    "relationships_pets.json",
    "financial_snapshots.json",  # net worth, accounts, balances
    "insurance.json",  # policies, numbers, coverage
    "gps_tracks.json",  # walks, rides and drives
    "operating_journal.json",  # how they mean to operate, and how they do
    "turn_traces.jsonl",  # what they asked and what she said, turn by turn
    # 2026-11-08 (DEC-0129): health is sealed from its first save
    "health.json",  # sleep, doctor and dentist visits, medications, health records
    # stage 3 (2026-11-08): the rest of the private personal stores
    "intents.json",  # their reasons: why they do what they do
    "communication_log.json",  # what MIA chose to say to them, or hold back
    "freedom_log.json",  # the freedom fund's balance over time
    "recreation.json",  # games and sports played
    "paths.json",  # learning paths: practice and checks
    "browser_routines.json",  # tasks they showed MIA in her browser
})
# Every store reading a SEALED file uses open_text and catches ValueError (UnreadableFile is one) with OSError, so a
# file that won't open is copied aside and the store starts empty instead of MIA failing to start. Not yet: the
# budget's files (bills, income, expenses, debts) wait on the Plaid work in core/budget_manager.py.

_lock = threading.Lock()
_keys: Optional[dict] = None  # kid -> key, opened once
_current: Optional[str] = None
_blocked = ""  # why sealing stopped ("" while it works)
_test_key: Optional[bytes] = None


class UnreadableFile(ValueError):
    """A sealed file that couldn't be opened; it was copied aside first (`aside`)."""

    def __init__(self, path: Path, aside: Optional[Path], why: str) -> None:
        """The file, where its copy went, and why it didn't open."""
        super().__init__(f"{path.name} couldn't be opened ({why}); a copy is kept at {aside.name if aside else '-'}")
        self.path, self.aside = path, aside


# ------------------------------------------------------------------ DPAPI (Windows)


def dpapi_available() -> bool:
    """Whether Windows DPAPI is here to protect the key."""
    return sys.platform == "win32"


def _blob(data: bytes):
    """A DPAPI DATA_BLOB over `data` (and the buffer, which must outlive the call)."""
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        """crypt32's DATA_BLOB: a length and a pointer."""
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data, len(data))
    return DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer, DataBlob


def _dpapi(data: bytes, protect: bool) -> bytes:
    """CryptProtectData / CryptUnprotectData for the current Windows user, with MIA's entropy and no prompt."""
    import ctypes

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    given, keep, DataBlob = _blob(data)
    entropy, keep2, _ = _blob(_ENTROPY)
    out = DataBlob()
    call = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    ok = call(ctypes.byref(given), None, ctypes.byref(entropy), None, None, 0x1, ctypes.byref(out))
    if not ok:
        raise OSError(f"DPAPI refused ({ctypes.GetLastError()})")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


def _protect(key: bytes) -> bytes:
    """The key protected for this Windows user."""
    return _dpapi(key, True)


def _unprotect(blob: bytes) -> bytes:
    """The key back from its protected form; OSError when this Windows user can't open it."""
    return _dpapi(blob, False)


# ------------------------------------------------------------------ the data key


def _kid(key: bytes) -> str:
    """A key's short id, written in each file it seals (not secret: a hash of the key, cut to 8 hex)."""
    return hashlib.sha256(b"MIA key id" + key).hexdigest()[:8]


def key_file() -> Path:
    """Where the protected data key lives."""
    return KEY_DIR / KEY_NAME


def use_key(key: Optional[bytes]) -> None:
    """For tests: seal with this key instead of DPAPI's (None goes back to the real one)."""
    global _test_key
    _test_key = key
    forget()


def forget() -> None:
    """Drops the opened keys so the next use reads the key file again."""
    global _keys, _current, _blocked
    with _lock:
        _keys, _current, _blocked = None, None, ""


def _save(entries: list[dict], current: str) -> None:
    """Writes the key file (directly, never through atomic_write_text: it isn't a store, and must never be undone)."""
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = key_file().with_name(KEY_NAME + ".tmp")
    tmp.write_text(json.dumps({"v": 1, "protection": "dpapi", "current": current, "keys": entries}, indent=1),
                   encoding="utf-8")
    os.replace(tmp, key_file())


def _open_keys() -> None:
    """Opens the key file once (making the first key when there's none). Sets `_blocked` when it can't."""
    global _keys, _current, _blocked
    if _keys is not None or _blocked:
        return
    if _test_key is not None:
        _keys, _current = {_kid(_test_key): _test_key}, _kid(_test_key)
        return
    if not dpapi_available():
        _blocked = "this system has no DPAPI; files stay plain"
        return
    path = key_file()
    if not path.exists():
        key = secrets.token_bytes(32)
        _save([{"id": _kid(key), "blob": base64.b64encode(_protect(key)).decode("ascii")}], _kid(key))
        _keys, _current = {_kid(key): key}, _kid(key)
        log.info("Made MIA's data key (DEC-0126), protected by this Windows sign-in")
        return
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        opened = {e["id"]: _unprotect(base64.b64decode(e["blob"])) for e in record["keys"]}
        _keys, _current = opened, record["current"]
    except (OSError, ValueError, KeyError, TypeError) as problem:
        _blocked = f"the data key couldn't be opened ({type(problem).__name__}); enter the recovery key"
        log.error("MIA's data key couldn't be opened; sealing has stopped until the recovery key is entered")
        _alert("data_key_unopened")


def _alert(kind: str) -> None:
    """Records a key problem in the security log, never raising."""
    try:
        from core.security_log import SecurityLog

        SecurityLog().record(kind, None, detail="data key (DEC-0126)")
    except Exception:
        log.exception("Couldn't record %s in the security log", kind)


def _current_key() -> Optional[tuple[str, bytes]]:
    """(kid, key) to seal with, or None when sealing isn't possible here."""
    with _lock:
        _open_keys()
        if _keys is None or _current not in _keys:
            return None
        return _current, _keys[_current]


def _key_for(kid: str) -> Optional[bytes]:
    """The key with this id, if it's held."""
    with _lock:
        _open_keys()
        return (_keys or {}).get(kid)


# ------------------------------------------------------------------ sealing and opening


def sealed_name(path: Path) -> bool:
    """Whether a file of this name is one MIA seals."""
    return Path(path).name in SEALED


def is_sealed(text) -> bool:
    """Whether some file content (text or bytes) is a sealed envelope."""
    return text.startswith(PREFIX if isinstance(text, str) else PREFIX.encode("ascii"))


def seal(text: str) -> str:
    """Pure-ish: `text` sealed under the current key, or unchanged when there's no key here (or already sealed)."""
    if is_sealed(text):
        return text
    held = _current_key()
    if held is None:
        return text
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    kid, key = held
    nonce = secrets.token_bytes(12)
    head = f"{PREFIX}{kid}:"
    body = AESGCM(key).encrypt(nonce, text.encode("utf-8"), head.encode("ascii"))
    return head + base64.b64encode(nonce + body).decode("ascii")


def unseal(envelope: str) -> str:
    """The text inside a sealed envelope; ValueError when the key isn't held or the file was changed or damaged."""
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        kid, body = envelope[len(PREFIX):].strip().split(":", 1)
        raw = base64.b64decode(body, validate=True)
    except ValueError:
        raise ValueError("not a whole sealed file") from None
    key = _key_for(kid)
    if key is None:
        raise ValueError(f"its key ({kid}) isn't held here")
    try:
        return AESGCM(key).decrypt(raw[:12], raw[12:], f"{PREFIX}{kid}:".encode("ascii")).decode("utf-8")
    except InvalidTag:
        raise ValueError("it was changed or damaged") from None


def seal_text(path: Path, text: str) -> str:
    """What atomic_write_text writes for `path`: sealed when its name is in SEALED, else `text` as it is."""
    return seal(text) if sealed_name(path) else text


def _set_aside(path: Path) -> Optional[Path]:
    """A copy of an unopenable file beside it, so a store that starts empty can't lose it."""
    aside = path.with_name(f"{path.name}.unreadable-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    try:
        if not aside.exists():
            aside.write_bytes(path.read_bytes())
        return aside
    except OSError:
        log.exception("Couldn't keep a copy of %s", path.name)
        return None


def open_text(path: Path, encoding: str = "utf-8") -> str:
    """A store file's text, sealed or plain. A sealed one that won't open is copied aside, then UnreadableFile."""
    path = Path(path)
    text = path.read_text(encoding=encoding)
    if not is_sealed(text):
        return text
    try:
        return unseal(text)
    except ValueError as problem:
        raise UnreadableFile(path, _set_aside(path), str(problem)) from None


def open_bytes(path: Path) -> bytes:
    """A file's real content as bytes (sync and export): a sealed one opened, any other read as it is."""
    path = Path(path)
    data = path.read_bytes()
    return open_text(path).encode("utf-8") if is_sealed(data) else data


# ------------------------------------------------------------------ status and the recovery key


def status() -> dict:
    """Whether sealing works here, how the key is protected, and which files are sealed."""
    held = _current_key()
    return {"sealing": held is not None, "protection": "test" if _test_key is not None else
            ("dpapi" if held is not None else "none"), "why_not": _blocked, "files": sorted(SEALED),
            "key_id": held[0] if held else ""}


def _group(text: str) -> str:
    """Groups of five for reading out and typing."""
    return "-".join(text[i:i + 5] for i in range(0, len(text), 5))


def recovery_key() -> str:
    """The current data key written out (base32, in groups of five), to keep in a password manager."""
    held = _current_key()
    if held is None:
        raise ValueError(_blocked or "there's no data key here")
    return _group(base64.b32encode(held[1]).decode("ascii").rstrip("="))


def restore(code: str) -> str:
    """Takes a recovery key back: protected for this Windows user and made the current key, keeping any other key
    the key file opens. Returns its id. ValueError for a code that isn't a key."""
    global _keys, _current, _blocked
    clean = "".join(c for c in code.upper() if c.isalnum())
    try:
        key = base64.b32decode(clean + "=" * (-len(clean) % 8))
    except ValueError:
        raise ValueError("that isn't a recovery key") from None
    if len(key) != 32:
        raise ValueError("that isn't a recovery key")
    if not dpapi_available() and _test_key is None:
        raise ValueError("this system has no DPAPI to protect it")
    with _lock:
        entries, held = [], {}
        if _test_key is None and key_file().exists():
            try:
                for e in json.loads(key_file().read_text(encoding="utf-8"))["keys"]:
                    try:
                        held[e["id"]] = _unprotect(base64.b64decode(e["blob"]))
                        entries.append(e)
                    except OSError:
                        pass  # a key this Windows user can't open: the recovered one replaces it
            except (OSError, ValueError, KeyError, TypeError):
                pass
        kid = _kid(key)
        if _test_key is None:
            if kid not in held:
                entries.append({"id": kid, "blob": base64.b64encode(_protect(key)).decode("ascii")})
            _save(entries, kid)
        held[kid] = key
        _keys, _current, _blocked = held, kid, ""
    _alert("data_key_restored")
    return kid


def seal_now(folders: list[Path]) -> int:
    """Seals every plain SEALED file in these folders now (`python -m tools.data_key seal`) rather than at its
    store's next save; returns how many. Each goes through atomic_write_text."""
    from core.atomic_write import atomic_write_text

    if _current_key() is None:
        return 0
    done = 0
    for folder in folders:
        for name in sorted(SEALED):
            path = Path(folder) / name
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                if not is_sealed(text):
                    atomic_write_text(path, text)
                    done += 1
    return done
