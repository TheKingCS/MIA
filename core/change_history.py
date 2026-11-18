"""
core.change_history
=====================

The lasting history of what MIA changed, with undo by time and subject (prompt 23's review, UI-3; DEC-0188;
REQ-TRU-001, REQ-TRU-002; `docs/mia_os/MIA_OS_UNIVERSAL_INTELLIGENCE_REVIEW.md` sections 3 and 14). "Undo that"
(core/undo_log.py) keeps the last 20 changes in memory, so it's for "oops, just now"; this keeps every change for
`KEEP_DAYS`, on disk, so "undo what you did to the greenhouse this afternoon" works after a restart too.

**What is kept** (`keep`, called by UndoLog.add for every change MIA's tools and approved actions make): one line
per change in the person's `history/changes.jsonl` (sealed a line at a time): its id, what it was (the tool or
action and the sentence that was approved), whose, when, by whom, and for each file it changed the file's hash
before and after. The bytes before are kept once per content (`history/blobs/<sha256>.blob`, compressed and sealed
like the stores they came from), so the same file saved many times costs little. Append-only logs (`.jsonl`) are
never kept: they're history, and undo never takes history back.

**Undo by time and subject** (`find`, `undo`): the changes in a window ("this afternoon", "today", "in the last two
hours", `window`) whose description or files match some words, newest first. Each change is undone **whole or not
at all**: all its files are checked first and then restored together. A change is undone only where nothing changed
its files since (each file's hash now is its hash just after that change, or the change after it was undone in the
same pass); otherwise it's left as it is and said ("the greenhouse log changed again at 4:10, so I left it"). The
undo itself is one more thing that happened (a life event), and the changes are marked undone in the history.

Each person's own, under their profile folder; a device without a profile keeps it in data/. Nothing here decides
what to undo: the person names it, sees the list and says yes (the undo_by_time tool, the Recent Changes page).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

KEEP_DAYS = 30
FOLDER = "history"
LOG_NAME = "changes.jsonl"
_lock = threading.RLock()
_pruned: set = set()  # folders pruned this process (once at first use, then daily by the history.prune check)


def folder_for(profile_id: Optional[str]) -> Path:
    """Where a person's history lives: their profile folder's `history/`, else data/'s."""
    if profile_id:
        import core.profile_manager as profiles

        return Path(profiles._DATA_PROFILES_DIR) / profile_id / FOLDER
    return Path(DATA_DIR) / FOLDER


def _sha(data: Optional[bytes]) -> str:
    """Pure logic. A content's hash, "" for a file that didn't exist."""
    return "" if data is None else hashlib.sha256(data).hexdigest()


def _read(path: Path) -> Optional[bytes]:
    """A file's bytes now, None when it isn't there."""
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


def _rel(path: Path) -> str:
    """A path as kept: relative to MIA's data folder when inside it (so a moved MIA_HOME still finds it)."""
    try:
        return str(Path(path).resolve().relative_to(Path(DATA_DIR).resolve()))
    except ValueError:
        return str(Path(path).resolve())


def _abs(kept: str) -> Path:
    """A kept path back to a real one."""
    p = Path(kept)
    return p if p.is_absolute() else Path(DATA_DIR) / p


@dataclass
class Entry:
    """One change as the history keeps it (see the module's opening)."""
    change_id: str
    label: str
    summary: str
    profile_id: Optional[str]
    at: str
    by: str
    files: list = field(default_factory=list)  # [{"path", "before", "after"}] (hashes; "" = no file)
    events: list = field(default_factory=list)
    undone: str = ""  # when it was undone, if it was
    seq: int = 0  # its place in the history: changes in the same second keep the order they happened in

    @property
    def what(self) -> str:
        """It in a few words: the approved sentence when there is one, else the tool's name."""
        return self.summary or self.label.replace("action_", "").replace("_", " ")


# ------------------------------------------------------------------ keeping


def _blob_path(folder: Path, sha: str) -> Path:
    """Where the bytes with this hash are kept."""
    return folder / "blobs" / f"{sha}.blob"


def _put_blob(folder: Path, data: bytes) -> str:
    """Keeps bytes once (compressed, then sealed when this MIA holds a key); returns their hash."""
    from core.at_rest import seal

    sha = _sha(data)
    path = _blob_path(folder, sha)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        text = seal(base64.b64encode(zlib.compress(data, 6)).decode("ascii"))
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    return sha


def _get_blob(folder: Path, sha: str) -> Optional[bytes]:
    """The bytes with this hash, or None when they aren't kept (or won't open here)."""
    from core.at_rest import is_sealed, unseal

    try:
        text = _blob_path(folder, sha).read_text(encoding="utf-8")
        if is_sealed(text):
            text = unseal(text)
        return zlib.decompress(base64.b64decode(text))
    except (OSError, ValueError, zlib.error):
        return None


def _append(folder: Path, record: dict) -> None:
    """One line onto the person's history, sealed on its own when there's a key."""
    from core.at_rest import seal

    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / LOG_NAME, "a", encoding="utf-8") as f:
        f.write(seal(json.dumps(record, ensure_ascii=False)) + "\n")


def keep(change) -> Optional[str]:
    """Keeps a finished change (core/undo_log.Change) in its person's history: its files' hashes before and after
    and the bytes before, with the trace id of what caused it. Append-only logs are left out. Never raises: a history
    that can't be written leaves the change itself standing. Returns the change's id, or None when nothing was
    kept."""
    try:
        folder = folder_for(change.profile_id)
        files = []
        with _lock:
            for path, before in change.files.items():
                if str(path).endswith(".jsonl") or Path(path).parent.name == FOLDER:
                    continue
                if before is not None:
                    _put_blob(folder, before)
                files.append({"path": _rel(path), "before": _sha(before), "after": _sha(_read(path))})
            if not files:
                return None
            _append(folder, {"change_id": change.change_id, "label": change.label, "summary": change.summary[:200],
                             "profile_id": change.profile_id, "at": change.at, "by": change.by, "files": files,
                             "events": list(change.events), "trace": getattr(change, "trace", "")})
            if folder not in _pruned:
                _pruned.add(folder)
                prune(folder)
        return change.change_id
    except Exception:  # noqa: BLE001 - the history never breaks the change it records
        log.exception("Couldn't keep change %s in the history.", getattr(change, "label", "?"))
        return None


# ------------------------------------------------------------------ reading


def entries(profile_id: Optional[str]) -> list[Entry]:
    """Every change kept for a person, oldest first, with undone ones marked."""
    from core.at_rest import is_sealed, unseal

    path = folder_for(profile_id) / LOG_NAME
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    found: dict[str, Entry] = {}
    names = set(Entry.__dataclass_fields__)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(unseal(line) if is_sealed(line) else line)
        except (ValueError, TypeError):
            continue
        if "undone" in record and "change_id" in record and len(record) <= 3:
            if record["change_id"] in found:
                found[record["change_id"]].undone = record["undone"]
            continue
        try:
            found[record["change_id"]] = Entry(**{k: v for k, v in record.items() if k in names}, seq=len(found))
        except (TypeError, KeyError):
            continue
    return sorted(found.values(), key=_order)


def _order(e: Entry) -> tuple:
    """Pure logic. When a change happened, ties broken by the order it was written in."""
    return (e.at, e.seq)


def window(words: str, now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Pure logic. The time a phrase means: "this afternoon" (noon to six), "this morning", "tonight", "today",
    "yesterday", "in the last hour", "the last 3 hours", "the last 30 minutes", "this week"; anything else, today."""
    now = now or datetime.now()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    low = (words or "").lower()
    m = re.search(r"last\s+(\d+|an?|one|two|three|four|five|six)?\s*(minute|min|hour|hr|day)s?", low)
    if m:
        n = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}.get(m.group(1) or "a")
        n = n or int(m.group(1))
        unit = {"minute": "minutes", "min": "minutes", "hour": "hours", "hr": "hours", "day": "days"}[m.group(2)]
        return now - timedelta(**{unit: n}), now
    if "yesterday" in low:
        return day - timedelta(days=1), day
    if "this morning" in low:
        return day, day.replace(hour=12)
    if "this afternoon" in low:
        return day.replace(hour=12), min(now, day.replace(hour=18))
    if "tonight" in low or "this evening" in low:
        return day.replace(hour=17), now
    if "this week" in low:
        return day - timedelta(days=day.weekday()), now
    return day, now


_STOP = {"the", "a", "an", "my", "to", "in", "on", "of", "and", "what", "you", "did", "changes", "change", "made",
         "undo", "all", "that", "this", "with", "for", "from", "today", "afternoon", "morning", "yesterday"}


def find(profile_id: Optional[str], start: datetime, end: datetime, about: str = "") -> list[Entry]:
    """The changes not yet undone between start and end whose description, tool or files mention every meaningful
    word of `about` (all of them when it's empty), newest first."""
    want = {w for w in re.findall(r"[a-z0-9]+", (about or "").lower()) if w not in _STOP and len(w) > 2}
    out = []
    for e in entries(profile_id):
        if e.undone or not (start.isoformat(timespec="seconds") <= e.at <= end.isoformat(timespec="seconds")):
            continue
        said = " ".join([e.label, e.summary] + [f["path"] for f in e.files]).lower().replace("_", " ")
        if all(w in said or w.rstrip("s") in said for w in want):
            out.append(e)
    return sorted(out, key=_order, reverse=True)


# ------------------------------------------------------------------ undoing


def undo(context, profile_id: Optional[str], picked: list[Entry]) -> dict:
    """Undoes the picked changes, newest first, each whole or not at all, and only where nothing changed its files
    since (see the module's opening). The config file keeps today's stop and standing yeses
    (core/undo_log.keep_sticky). Returns {"undone": [Entry], "left": [(Entry, why)]}."""
    from core import live
    from core.undo_log import reload_stores

    folder = folder_for(profile_id)
    undone, left, touched = [], [], []
    with _lock:
        now_hash: dict[str, str] = {}
        for e in sorted(picked, key=_order, reverse=True):
            current = {f["path"]: now_hash.get(f["path"], _sha(_read(_abs(f["path"])))) for f in e.files}
            moved = [f for f in e.files if current[f["path"]] != f["after"]]
            if moved:
                name = Path(moved[0]["path"]).stem.replace("_", " ")
                left.append((e, f"the {name} changed again after it, so I left it as it is"))
                continue
            olds = {f["path"]: (_get_blob(folder, f["before"]) if f["before"] else None) for f in e.files}
            missing = [p for p, f in zip(olds, e.files) if f["before"] and olds[p] is None]
            if missing:
                left.append((e, "what it looked like before isn't kept anymore"))
                continue
            for f in e.files:  # all checked: now put every file back
                path, old = _abs(f["path"]), olds[f["path"]]
                from core.undo_log import keep_sticky

                old = keep_sticky(path, old)  # an undo by time never lifts a stop or revives a standing yes
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_name(f".{path.name}.undo")
                    tmp.write_bytes(old)
                    tmp.replace(path)
                now_hash[f["path"]] = f["before"]
                touched.append(path)
            _append(folder, {"change_id": e.change_id, "undone": datetime.now().isoformat(timespec="seconds")})
            e.undone = "now"
            undone.append(e)
    if undone:
        reload_stores(context, touched)
        live.bump()
        undo_log = getattr(context, "undo", None)
        if undo_log is not None:
            undo_log.forget({e.change_id for e in undone})  # "undo that" can't put back what's already back
        from core import life_events

        life_events.record(getattr(context, "life_events", None), "undone",
                           f"Undid {len(undone)} change{'s' if len(undone) != 1 else ''}",
                           [], {"changes": [e.change_id for e in undone],
                                "reverses": [ev for e in undone for ev in e.events]}, profile_id=profile_id)
    return {"undone": undone, "left": left}


def mark_undone(profile_id: Optional[str], change_id: str) -> None:
    """Notes in the history that a change was put back some other way ("undo that"), so it's never undone twice."""
    try:
        with _lock:
            _append(folder_for(profile_id), {"change_id": change_id,
                                             "undone": datetime.now().isoformat(timespec="seconds")})
    except OSError:
        log.exception("Couldn't mark change %s undone in the history.", change_id)


def say(found: list[Entry], limit: int = 8) -> str:
    """Pure logic. A list of changes in her words, newest first, with the time."""
    def when(at: str) -> str:
        try:
            return datetime.fromisoformat(at).strftime("%I:%M %p").lstrip("0")
        except ValueError:
            return at
    lines = [f"{when(e.at)}: {e.what}" for e in found[:limit]]
    more = len(found) - limit
    return "; ".join(lines) + (f"; and {more} more" if more > 0 else "")


def prune(folder: Path, now: Optional[datetime] = None) -> int:
    """Forgets changes older than KEEP_DAYS (and the marks saying they were undone) and any kept bytes nothing still
    points at. Returns how many changes went."""
    from core.at_rest import is_sealed, unseal

    path = folder / LOG_NAME
    cutoff = ((now or datetime.now()) - timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    parsed = []
    for line in lines:
        try:
            parsed.append((line, json.loads(unseal(line.strip()) if is_sealed(line.strip()) else line)))
        except (ValueError, TypeError):
            parsed.append((line, None))
    kept_ids = {r["change_id"] for _l, r in parsed if r and "at" in r and r["at"] >= cutoff}
    keep_lines, gone, needed = [], 0, set()
    for line, record in parsed:
        if record is None:
            keep_lines.append(line)
            continue
        if record.get("change_id") not in kept_ids:
            gone += "at" in record
            continue
        keep_lines.append(line)
        for f in record.get("files", []):
            needed.add(f.get("before", ""))
    if len(keep_lines) != len(lines):
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text("\n".join(keep_lines) + ("\n" if keep_lines else ""), encoding="utf-8")
        tmp.replace(path)
    for blob in (folder / "blobs").glob("*.blob") if (folder / "blobs").exists() else []:
        if blob.stem not in needed:
            blob.unlink(missing_ok=True)
    return gone
