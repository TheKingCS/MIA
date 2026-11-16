"""
core.shelf
============

The shelf (UI-4; prompt 23's review, G1; Zac's answer to Q-43, 2026-11-16: "only what is sent"): a short-lived
place for things the person captured and chose to keep, to look at together, combine and send on. The "universal
clipboard", without watching the clipboard: something goes on the shelf only when the person sends it there
(Keep On My Shelf in the selection menu, a drop on MIA's page, or "keep this on my shelf"). Watching everything
they copy stays off; it would be a separate switch, never built here.

**What an entry is:** a capture from the Universal Action Layer (`core.ual.Capture`), unchanged: the text, the
files' names, where it came from, the device, what couldn't be captured; plus when it was kept and when it goes.
So a selection from the phone, the palette and a drop land on the shelf the same way.

**Short-lived:** an entry goes after KEEP_DAYS unless the person keeps it longer (at most MAX_DAYS); gone entries are
dropped whenever the shelf is read. At most MAX_ENTRIES; keeping one more lets the oldest go.

**Always outside text:** an entry is information, never an instruction. Nothing on it is read by a model except
through `core.ual.framed()`, and the shelf never turns into a memory, a note or a record by itself: that takes one
of the catalogue's keep actions, which the person picks (`combined()` makes several entries into one capture for
them). Each person's own (PERSONAL_STORES), sealed at rest like every personal store, and written atomically so
"undo that" takes back a keep or a removal.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "shelf.json"
KEEP_DAYS = 7  # how long an entry stays unless the person says otherwise
MAX_DAYS = 30
MAX_ENTRIES = 50
COMBINED_LIMIT = 20_000  # characters of combined text handed to an action, as one selection (core.ual.TEXT_LIMIT)


class ShelfError(ValueError):
    """Something asked of the shelf can't be done; its message is a plain sentence for the person."""


@dataclass
class ShelfEntry:
    """One thing on the shelf: the capture's fields as `core.ual.Capture` has them, its id, when it was kept and when
    it goes (ISO times)."""
    entry_id: str
    kind: str = "text"
    text: str = ""
    files: list = field(default_factory=list)
    source_app: str = ""
    url: str = ""
    title: str = ""
    device: str = ""
    missing: list = field(default_factory=list)
    kept: str = ""
    until: str = ""

    def capture(self):
        """The entry as a `core.ual.Capture`, for the catalogue's actions."""
        from core.ual import Capture

        return Capture(kind=self.kind, text=self.text, files=list(self.files), source_app=self.source_app,
                       url=self.url, title=self.title, device=self.device, missing=list(self.missing))

    def label(self, cap: int = 60) -> str:
        """A few words saying what it is: its first line, or its files, with where it came from."""
        first = " ".join((self.text or "").split())[:cap] or ", ".join(self.files)[:cap] or "(empty)"
        where = self.capture().where_from()
        return f"{first} (from {where})" if where and where != "a selection" else first


def _days(days) -> int:
    """Pure logic. The days an entry is kept: KEEP_DAYS when not said, else between 1 and MAX_DAYS."""
    try:
        return max(1, min(MAX_DAYS, int(days))) if days not in (None, "") else KEEP_DAYS
    except (TypeError, ValueError):
        return KEEP_DAYS


class Shelf:
    """A person's shelf, in `shelf.json`: entries newest first, each with when it goes."""

    # The epistemic contract (DEC-0173, G3): each entry is what the person sent, from the app it came from, when kept.
    EPISTEMIC = {"record": ShelfEntry, "source": "source_app", "at": "kept", "how": "said"}

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the person's shelf (or data/'s)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        """Reads the file; a missing or unreadable one is an empty shelf (sealed at rest: open_text opens it)."""
        self.items: list[ShelfEntry] = []
        try:
            raw = json.loads(open_text(self._file)).get("entries", [])
        except (OSError, ValueError):
            return
        names = set(ShelfEntry.__dataclass_fields__)
        for item in raw:
            if isinstance(item, dict) and item.get("entry_id"):
                try:
                    self.items.append(ShelfEntry(**{k: v for k, v in item.items() if k in names}))
                except TypeError:
                    continue

    def _save(self) -> None:
        """Writes atomically (inside "undo that": a keep or a removal can be taken back)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "entries": [asdict(e) for e in self.items]},
                                                 indent=1, ensure_ascii=False))

    def _prune(self, now: datetime) -> bool:
        """Drops entries whose time has passed; True when any went."""
        stamp = now.isoformat(timespec="seconds")
        kept = [e for e in self.items if not e.until or e.until > stamp]
        gone = len(kept) != len(self.items)
        self.items = kept
        return gone

    def entries(self, now: Optional[datetime] = None) -> list[ShelfEntry]:
        """What's on the shelf now, newest first; entries past their time are dropped (and the file rewritten,
        outside "undo that", since an expiry isn't a change anyone made)."""
        from core.undo_log import outside_undo

        with self._lock:
            if self._prune(now or datetime.now()):
                with outside_undo():
                    self._save()
            return list(self.items)

    def keep(self, capture, days=None, now: Optional[datetime] = None) -> ShelfEntry:
        """Puts a capture on the shelf for `days` (KEEP_DAYS when not said). The same text from the same place
        already on it is moved to the top with the later time, not kept twice. At most MAX_ENTRIES: the oldest go."""
        now = now or datetime.now()
        if not (capture.text or capture.files):
            raise ShelfError("There's nothing to keep.")
        with self._lock:
            self._prune(now)
            same = next((e for e in self.items if e.text == capture.text and e.files == list(capture.files)
                         and e.url == capture.url and e.source_app == capture.source_app), None)
            if same is not None:
                self.items.remove(same)
            entry = ShelfEntry(entry_id=same.entry_id if same else uuid.uuid4().hex[:10], kind=capture.kind,
                               text=capture.text, files=list(capture.files), source_app=capture.source_app,
                               url=capture.url, title=capture.title, device=capture.device,
                               missing=list(capture.missing), kept=now.isoformat(timespec="seconds"),
                               until=(now + timedelta(days=_days(days))).isoformat(timespec="seconds"))
            self.items.insert(0, entry)
            del self.items[MAX_ENTRIES:]
            self._save()
            return entry

    def find(self, which) -> list[ShelfEntry]:
        """Entries by id, or by number as the shelf is listed (1 is the newest), or every one for "all"; in the
        shelf's order. ShelfError when one doesn't match."""
        items = self.entries()
        if which in ("all", ["all"], None, "", []):
            return items
        wanted = which if isinstance(which, (list, tuple)) else str(which).replace(" and ", ",").split(",")
        found = []
        for raw in wanted:
            word = str(raw).strip()
            if not word:
                continue
            hit = next((e for e in items if e.entry_id == word), None)
            if hit is None and word.isdigit() and 1 <= int(word) <= len(items):
                hit = items[int(word) - 1]
            if hit is None:
                raise ShelfError(f"Nothing on your shelf is \"{word}\".")
            if hit not in found:
                found.append(hit)
        return [e for e in items if e in found]

    def remove(self, entry_id: str) -> ShelfEntry:
        """Takes one entry off the shelf; ShelfError when it isn't there."""
        with self._lock:
            hit = next((e for e in self.items if e.entry_id == entry_id), None)
            if hit is None:
                raise ShelfError("That isn't on your shelf any more.")
            self.items.remove(hit)
            self._save()
            return hit

    def clear(self) -> int:
        """Takes everything off the shelf; how many went."""
        with self._lock:
            count = len(self.items)
            if count:
                self.items = []
                self._save()
            return count


def combined(entries: list[ShelfEntry]):
    """Pure logic. Several entries as one capture for the catalogue's actions: each one's text under a line saying
    where it came from, the files together, what wasn't captured kept, and the kind worked out again. ShelfError when
    none is given."""
    from core.ual import Capture, kind_of

    if not entries:
        raise ShelfError("Nothing on your shelf was picked.")
    if len(entries) == 1:
        return entries[0].capture()
    parts, files, missing = [], [], []
    for n, entry in enumerate(entries, 1):
        where = entry.capture().where_from()
        if entry.text:
            parts.append(f"--- {n}. from {where} ---\n{entry.text}")
        files += [f for f in entry.files if f not in files]
        missing += [f"{n}: {m}" for m in entry.missing]
    text = "\n\n".join(parts)
    if len(text) > COMBINED_LIMIT:
        text = text[:COMBINED_LIMIT]
        missing.append(f"the combined text past {COMBINED_LIMIT:,} characters")
    got = Capture(text=text, files=files[:20], source_app="mia:shelf", title=f"{len(entries)} things on your shelf",
                  device="", missing=missing[:8])
    got.kind = kind_of(got)
    return got


def shelf_of(context) -> Shelf:
    """The person's shelf: the context's (each person's own, core/personal_data.py), else one on data/."""
    found = getattr(context, "shelf", None)
    return found if found is not None else Shelf(context)


def said(context, now: Optional[datetime] = None) -> str:
    """What's on the shelf, in words, numbered as `find` reads numbers: for voice and the tool."""
    items = shelf_of(context).entries(now)
    if not items:
        return "Your shelf is empty. Say \"keep this on my shelf\" with something, or use Keep On My Shelf."
    now = now or datetime.now()
    lines = []
    for n, entry in enumerate(items, 1):
        try:
            left = (datetime.fromisoformat(entry.until) - now).days
        except ValueError:
            left = 0
        lines.append(f"{n}. {entry.label()}, {'goes today' if left < 1 else f'{left} days left'}")
    return f"On your shelf ({len(items)}):\n" + "\n".join(lines)


def as_dict(entry: ShelfEntry) -> dict:
    """What a screen shows of an entry: its id, kind, a label, the text (it's the person's own), files, where it came
    from, the device, when kept and when it goes."""
    return {"entry_id": entry.entry_id, "kind": entry.kind, "label": entry.label(), "text": entry.text,
            "files": list(entry.files), "from": entry.capture().where_from(), "device": entry.device,
            "kept": entry.kept, "until": entry.until, "missing": list(entry.missing)}
