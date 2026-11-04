"""
core.dev_store
================

Where the development history lives on this PC (DEC-0077, Zac 2026-11-04:
"a way to not take up a ton of memory while maintaining MIAs ability to
access the fullness of her memory and development";
`docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md` section 6.5).

- **Kept whole, kept small.** A `DevStore` is an append-only record in
  segments: the open one is plain JSON lines; a full one (`SEGMENT_BYTES`,
  or a new month) is gzipped, about a tenth of the size. Nothing is ever
  deleted or rewritten.
- **Never loaded whole.** Reading streams a line at a time; `tail()` reads
  only the newest segment (and the one before, if it must).
- **Found without loading.** One `DevIndex` (SQLite full-text search,
  contentless: it keeps the words' positions, not a second copy of the
  text) covers the PC's stores and the repo's own records
  (`work/activity.jsonl`, `work/council.jsonl`). A hit says where its
  record is, and only that record is read. The index can be deleted and
  rebuilt from the records at any time.

Device-level, in `data/dev/` (gitignored): development history, not any
person's. Nothing personal belongs here; the council's text is redacted
on its way into the repo (core/council.py).
"""

from __future__ import annotations

import gzip
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional

ROOT = Path(__file__).resolve().parent.parent
DEV_DATA = ROOT / "data" / "dev"
SEGMENT_BYTES = 2_000_000  # plain size before a segment closes; gzipped it's ~200 KB


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DevStore:
    """An append-only record in segments: `0001.jsonl` open, `0001.jsonl.gz` closed."""

    def __init__(self, folder: Path, segment_bytes: int = SEGMENT_BYTES) -> None:
        self.folder = Path(folder)
        self.segment_bytes = segment_bytes

    def _segments(self) -> list[str]:
        if not self.folder.exists():
            return []
        names = {p.name.split(".", 1)[0] for p in self.folder.glob("*.jsonl*") if p.name[:4].isdigit()}
        return sorted(names)

    def _plain(self, seg: str) -> Path:
        return self.folder / f"{seg}.jsonl"

    def _packed(self, seg: str) -> Path:
        return self.folder / f"{seg}.jsonl.gz"

    def _open_segment(self) -> str:
        segs = self._segments()
        if not segs:
            return "0001"
        last = segs[-1]
        plain, packed = self._plain(last), self._packed(last)
        if packed.exists():
            if plain.exists():  # stopped between packing and removing: the packed one is whole
                plain.unlink()
            return f"{int(last) + 1:04d}"
        return last

    def _lines(self, seg: str) -> Iterator[str]:
        plain, packed = self._plain(seg), self._packed(seg)
        if plain.exists():
            with open(plain, encoding="utf-8") as f:
                yield from f
        elif packed.exists():
            with gzip.open(packed, "rt", encoding="utf-8") as f:
                yield from f

    def _close(self, seg: str) -> None:
        plain, packed = self._plain(seg), self._packed(seg)
        tmp = packed.with_suffix(".gz.tmp")
        with open(plain, "rb") as src, gzip.open(tmp, "wb") as out:
            for block in iter(lambda: src.read(1 << 16), b""):
                out.write(block)
        os.replace(tmp, packed)
        plain.unlink()

    def _first_month(self, seg: str) -> str:
        for line in self._lines(seg):
            try:
                return str(json.loads(line).get("at", ""))[:7]
            except ValueError:
                return ""
        return ""

    def append(self, record: dict) -> tuple[dict, str]:
        """Add one record (given an `at` if it has none). Returns it and where it is."""
        record = {"at": _now(), **record}
        self.folder.mkdir(parents=True, exist_ok=True)
        seg = self._open_segment()
        plain = self._plain(seg)
        if plain.exists() and (plain.stat().st_size >= self.segment_bytes
                               or self._first_month(seg) not in ("", str(record["at"])[:7])):
            self._close(seg)
            seg = f"{int(seg) + 1:04d}"
            plain = self._plain(seg)
        line = sum(1 for _ in self._lines(seg)) if plain.exists() else 0
        with open(plain, "a", encoding="utf-8", newline="\n") as out:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record, f"seg:{self.folder.name}/{seg}:{line}"

    def records(self) -> Iterator[dict]:
        """Every record, oldest first, a line at a time."""
        for seg in self._segments():
            for line in self._lines(seg):
                try:
                    yield json.loads(line)
                except ValueError:
                    continue

    def tail(self, n: int) -> list[dict]:
        """The newest `n`, oldest first, reading as few segments as it can."""
        out: list[dict] = []
        for seg in reversed(self._segments()):
            found = []
            for line in self._lines(seg):
                try:
                    found.append(json.loads(line))
                except ValueError:
                    continue
            out = found[-(n - len(out)):] + out if n > len(out) else out
            if len(out) >= n:
                break
        return out[-n:] if n else []

    def at(self, seg: str, line: int) -> Optional[dict]:
        for i, text in enumerate(self._lines(seg)):
            if i == line:
                try:
                    return json.loads(text)
                except ValueError:
                    return None
        return None

    def size(self) -> int:
        return sum(p.stat().st_size for p in self.folder.glob("*.jsonl*")) if self.folder.exists() else 0


STOP = frozenset("a an and are at be but by did do does for from had has have how i in is it its me my "
                  "of on or so that the their them then there they this to was we were what when where which "
                  "who why will with you your".split())


def _fts_query(text: str) -> str:
    """Pure logic. Words to an FTS5 query that can't be misread as syntax: each a quoted term, any of
    them (ranked by how many and how rare), the asking words left out."""
    words = [w for w in re.findall(r"[\w'-]+", (text or "").lower()) if w not in STOP]
    seen: list[str] = []
    for w in words:
        w = w.replace('"', "")
        if w and w not in seen:
            seen.append(w)
    return " OR ".join('"' + w + '"' for w in seen[:12])


def _body(record: dict) -> str:
    return " ".join(str(record.get(k, "")) for k in ("who", "action", "task", "text", "detail", "kind", "title"))


class DevIndex:
    """One search over every development record: PC stores and the repo's files."""

    def __init__(self, path: Path = DEV_DATA / "index.sqlite", stores: Optional[dict] = None,
                 files: Optional[dict] = None) -> None:
        self.path = Path(path)
        self.stores = stores or {}  # name -> DevStore
        self.files = files or {}  # name -> a repo .jsonl file
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.executescript(
            "create table if not exists items(id integer primary key, source text, at text, who text,"
            " task text, loc text unique);"
            "create virtual table if not exists words using fts5(body, content='');"
            "create table if not exists synced(source text primary key, mark text);")

    def close(self) -> None:
        self.db.close()

    def _add(self, source: str, record: dict, loc: str) -> None:
        cur = self.db.execute("insert or ignore into items(source, at, who, task, loc) values (?,?,?,?,?)",
                              (source, str(record.get("at", "")), str(record.get("who", "")),
                               str(record.get("task", "")), loc))
        if cur.rowcount:
            self.db.execute("insert into words(rowid, body) values (?, ?)", (cur.lastrowid, _body(record)))

    def _mark(self, source: str) -> str:
        row = self.db.execute("select mark from synced where source = ?", (source,)).fetchone()
        return row[0] if row else ""

    def _set_mark(self, source: str, mark: str) -> None:
        self.db.execute("insert or replace into synced(source, mark) values (?, ?)", (source, mark))

    def sync(self) -> None:
        """Index whatever was added since last time. Reads only what's new."""
        for name, path in self.files.items():
            path = Path(path)
            if not path.exists():
                continue
            offset = int(self._mark(name) or 0)
            if offset > path.stat().st_size:  # the file was replaced: start again
                offset = 0
            with open(path, "rb") as f:
                f.seek(offset)
                while True:
                    start = f.tell()
                    raw = f.readline()
                    if not raw or not raw.endswith(b"\n"):
                        break
                    try:
                        self._add(name, json.loads(raw.decode("utf-8")), f"file:{name}:{start}")
                    except ValueError:
                        pass
                    offset = f.tell()
            self._set_mark(name, str(offset))
        for name, store in self.stores.items():
            seen = self._mark(name)
            for seg in store._segments():
                done_seg, _, done_line = seen.partition(":")
                if done_seg and seg < done_seg:
                    continue
                start = int(done_line) + 1 if seg == done_seg and done_line else 0
                last = start - 1
                for i, line in enumerate(store._lines(seg)):
                    if i < start:
                        continue
                    try:
                        self._add(name, json.loads(line), f"seg:{store.folder.name}/{seg}:{i}")
                    except ValueError:
                        pass
                    last = i
                if last >= 0:
                    seen = f"{seg}:{last}"
            self._set_mark(name, seen)
        self.db.commit()

    def _fetch(self, loc: str) -> Optional[dict]:
        kind, _, rest = loc.partition(":")
        if kind == "file":
            name, _, offset = rest.rpartition(":")
            path = self.files.get(name)
            if not path:
                return None
            with open(path, "rb") as f:
                f.seek(int(offset))
                try:
                    return json.loads(f.readline().decode("utf-8"))
                except ValueError:
                    return None
        where, _, line = rest.rpartition(":")
        folder, _, seg = where.rpartition("/")
        store = next((s for s in self.stores.values() if s.folder.name == folder), None)
        return store.at(seg, int(line)) if store else None

    def search(self, text: str, limit: int = 20, sources: Iterable[str] = ()) -> list[dict]:
        """The best matches, each record read from where it's kept, with its `source`."""
        query = _fts_query(text)
        if not query:
            return []
        self.sync()
        rows = self.db.execute(
            "select items.source, items.loc from words join items on items.id = words.rowid"
            " where words match ? order by bm25(words) limit ?", (query, limit * 3)).fetchall()
        wanted = set(sources)
        out = []
        for source, loc in rows:
            if wanted and source not in wanted:
                continue
            found = self._fetch(loc)
            if found is not None:
                out.append({**found, "source": source})
            if len(out) >= limit:
                break
        return out

    def size(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0
