"""
core.pack_index
=================

Her own search index for the offline packs Kiwix didn't index (core/offline_library.py). Many of the most useful ones
have no full-text index of their own: iFixit's repair guides, the USDA canning guide, the LibreTexts textbooks, and
the preppers' collections, which are PDFs inside the pack (water treatment, field medicine, food preserving,
post-disaster). libzim can only find those by title, so their words would be out of her reach.

**Building one** (`build`): every PDF in the pack (its text, page by page, through QtPdf, the same reader as
core/document_text.py, in a worker process so a PDF that crashes QtPdf loses only itself: `_PdfWorker`; skipped where
PySide6 isn't installed, or over PDF_BYTES), and its HTML pages too when Kiwix gave the pack no
full-text index (Kiwix's index covers a pack's pages, never the PDFs inside it), go into a SQLite FTS5 table beside
the packs, `.fetch/index/<pack file>.sqlite`, built under a temporary name and moved into place only when finished.
`index_missing` builds every one that's missing (an empty index for a pack with nothing to add, so it isn't looked at
again) and removes any whose pack is gone; a pack over BIG_PACK that Kiwix indexed (Wikipedia, the Q&A sites: pages,
no PDFs) is left to Kiwix's index.

**Searching** (`search`): the question's words, all of them first, then every set of all but one or two (the word left out
each left out in turn, `_queries`), then any of them, ranked by FTS5's bm25, each hit
with its page (for a PDF) and a passage around the words (or the page's whole text, for core/reference_reader.py to
cut its best window from); `page_text` gives one page to read further. The indexes hold the packs' own published text, never
anything of his.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

VERSION = "1"
BIG_PACK = 5 * 10**9  # an indexed pack this big is left to Kiwix's own index
PAGE_CHARS = 20_000  # of one page's text
PDF_PAGES = 600  # of one PDF
PDF_BYTES = 40 * 10**6  # a PDF larger than this isn't read (a scanned book: no text to find, and memory to spare)
PDF_SECONDS = 120  # one PDF's reading, at most


@dataclass
class Hit:
    """One passage found in an index, shaped like a reference library snippet."""
    pack_id: str
    pack_title: str
    article_title: str
    snippet: str
    path: str = ""
    page: int = 0


def index_folder(root: Path) -> Path:
    """Where the indexes live, beside the packs."""
    return Path(root) / ".fetch" / "index"


def index_path(root: Path, pack_file: Path) -> Path:
    """The index for one pack file."""
    return index_folder(root) / (Path(pack_file).stem + ".sqlite")


def needs_index(archive) -> bool:
    """Whether a pack has no full-text index of its own (so its pages go into hers too)."""
    try:
        return not archive.has_fulltext_index
    except Exception:  # noqa: BLE001 - one that can't say is treated as needing one
        return True


def _mimetype(entry) -> str:
    """An entry's type, read from its header (not its content)."""
    try:
        return entry.get_item().mimetype
    except Exception:  # noqa: BLE001
        return ""


def _html_text(data: bytes) -> str:
    """A page's text (core/document_text.html_to_text), trimmed."""
    from core.document_text import html_to_text

    return html_to_text(data.decode("utf-8", errors="replace"))[:PAGE_CHARS]


def _read_pdf(path: Path) -> tuple[list[str], str]:
    """A PDF file's pages as text and its own title, through QtPdf (in this process); ([], "") when it won't open."""
    try:
        from core.document_text import pdf_pages
    except Exception:  # noqa: BLE001 - no PySide6 here
        return [], ""
    try:
        pages, title = pdf_pages(Path(path))
        return [p[:PAGE_CHARS] for p in pages[:PDF_PAGES]], title
    except Exception:  # noqa: BLE001 - a damaged PDF is skipped
        return [], ""


class _PdfWorker:
    """A child process that reads PDFs (`python -m core.pack_index --pdf-worker`), one path a line in, one JSON line
    out. QtPdf can crash on a PDF in native code (2026-11-23: Windows exception 0xe0000008 on a ready.gov PDF), which
    no try can catch and which took the whole indexing with it; in a worker, only that PDF is lost: the worker is
    started again for the next. One that takes longer than PDF_SECONDS is ended the same way."""

    def __init__(self):
        """No process until the first PDF."""
        self.proc = None

    def _start(self) -> None:
        """Starts the worker (no window on Windows)."""
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        self.proc = subprocess.Popen([sys.executable, "-m", "core.pack_index", "--pdf-worker"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     cwd=str(Path(__file__).resolve().parent.parent), creationflags=flags,
                                     text=True, encoding="utf-8")

    def read(self, path: Path) -> tuple[list[str], str]:
        """One PDF through the worker; ([], "") when the worker died or ran out of time on it."""
        if self.proc is None or self.proc.poll() is not None:
            self._start()
        answer: list = []

        def listen():
            """The worker's one line back."""
            try:
                answer.append(self.proc.stdout.readline())
            except Exception:  # noqa: BLE001 - a dead worker answers nothing
                answer.append("")

        try:
            self.proc.stdin.write(str(path) + "\n")
            self.proc.stdin.flush()
        except OSError:
            self.close()
            return [], ""
        reader = threading.Thread(target=listen, daemon=True)
        reader.start()
        reader.join(PDF_SECONDS)
        line = answer[0] if answer else ""
        if not line:
            log.info("A PDF couldn't be read (the reader stopped on it); skipped.")
            self.close()
            return [], ""
        try:
            data = json.loads(line)
            return list(data.get("pages") or []), str(data.get("title") or "")
        except ValueError:
            return [], ""

    def close(self) -> None:
        """Ends the worker."""
        if self.proc is not None:
            try:
                self.proc.kill()
            except OSError:
                pass
            self.proc = None


def _worker_main() -> None:
    """The worker's loop: a path a line in, {pages, title} a line out, until its input ends."""
    for line in sys.stdin:
        pages, title = _read_pdf(Path(line.strip()))
        sys.stdout.write(json.dumps({"pages": pages, "title": title}) + "\n")
        sys.stdout.flush()


def _pdf_pages(data: bytes, worker: Optional[_PdfWorker] = None) -> tuple[list[str], str]:
    """A PDF's pages as text and its own title, through QtPdf in the worker (`_PdfWorker`; in this process without
    one); ([], "") where PySide6 isn't here, it won't open, it's over PDF_BYTES, or it crashed the reader."""
    if len(data) > PDF_BYTES:
        return [], ""
    handle, name = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(data)
        return worker.read(Path(name)) if worker is not None else _read_pdf(Path(name))
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass


def _entries(archive, pages: bool):
    """Every real entry worth indexing (redirects left out): (path, title, mimetype, bytes); the HTML pages only when
    `pages`, the PDFs always. Content is read only for those."""
    for i in range(archive.all_entry_count):
        try:
            entry = archive._get_entry_by_id(i)
            if entry.is_redirect:
                continue
            mime = _mimetype(entry)
            if mime == "application/pdf" or (pages and mime.startswith("text/html")):
                yield entry.path, entry.title, mime, bytes(entry.get_item().content)
        except Exception:  # noqa: BLE001 - one bad entry never stops the rest
            continue


def build(pack_file: Path, out: Path, archive=None, progress: Callable = lambda n: None,
          pages: Optional[bool] = None) -> int:
    """Builds the index for one pack into `out` (its PDFs, and its pages when it has no index of its own, or when
    `pages` says so; its PDFs read in one worker process, ended at the finish); how many rows. The file appears
    only when finished."""
    if archive is None:
        from libzim.reader import Archive

        archive = Archive(str(pack_file))
    pages = needs_index(archive) if pages is None else pages
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    rows = 0
    worker = None
    try:
        db.execute("CREATE VIRTUAL TABLE docs USING fts5(path UNINDEXED, title, page UNINDEXED, body, "
                   "tokenize='porter unicode61')")
        db.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
        batch = []
        for n, (path, title, mime, data) in enumerate(_entries(archive, pages)):
            if mime.startswith("text/html"):
                text = _html_text(data)
                if len(text) > 80:
                    batch.append((path, title, 0, text))
            elif mime == "application/pdf":
                worker = worker or _PdfWorker()
                texts, own = _pdf_pages(data, worker)
                name = pdf_name(path, title, own)
                for page, text in enumerate(texts, start=1):
                    if len(text.strip()) > 40:
                        batch.append((path, name, page, text))
            if len(batch) >= 500:
                db.executemany("INSERT INTO docs VALUES (?, ?, ?, ?)", batch)
                rows += len(batch)
                batch = []
                progress(n)
        db.executemany("INSERT INTO docs VALUES (?, ?, ?, ?)", batch)
        rows += len(batch)
        db.executemany("INSERT INTO meta VALUES (?, ?)", [("version", VERSION), ("pack", Path(pack_file).name)])
        db.commit()
    finally:
        db.close()
        if worker is not None:
            worker.close()
    os.replace(tmp, out)
    return rows


class _Empty:
    """A pack with nothing for her index: the marker for one left to Kiwix's own (so a start doesn't look again)."""

    has_fulltext_index = True
    all_entry_count = 0


def index_missing(library, root: Path, progress: Callable = lambda key, n: None) -> int:
    """Builds every index a pack wants and hasn't got (a pack copied in by hand too; a big pack left to Kiwix's own
    gets an empty one, a marker), and removes those whose pack file is gone (not one that merely failed to open); how
    many were built. Never raises."""
    built = 0
    folder = index_folder(root)
    packs = {Path(p.file_path).stem: p for p in library.list_packs()} if library is not None else {}
    on_disk = {p.stem for p in Path(root).glob("*.zim")}
    if folder.is_dir():
        for old in folder.glob("*.sqlite"):
            if old.stem not in on_disk:
                old.unlink(missing_ok=True)  # its pack is gone (one that merely failed to open keeps its index)
    for stem, pack in packs.items():
        out = index_path(root, Path(pack.file_path))
        if out.exists():
            continue
        try:
            archive = library._get_archive(pack.pack_id, Path(pack.file_path))
            if archive is None:
                continue
            if not needs_index(archive) and Path(pack.file_path).stat().st_size > BIG_PACK:
                build(Path(pack.file_path), out, _Empty(), pages=False)  # left to Kiwix's index: marked, not read
                continue
            rows = build(Path(pack.file_path), out, archive, lambda n, stem=stem: progress(stem, n))
            built += 1
            log.info("Indexed the offline pack %s (%d passages)", pack.title, rows)
        except Exception as problem:  # noqa: BLE001 - one pack's index never stops the rest
            log.warning("Couldn't index the offline pack %s: %s", pack.title, problem)
    return built


_JUNK = re.compile(r"^(microsoft (word|powerpoint|excel)\s*-\s*|untitled)", re.I)
_EXT = re.compile(r"\.(pdf|docx?|pptx?|xlsx?|rtf|txt)$", re.I)


def pdf_name(path: str, title: str, own: str = "") -> str:
    """Pure logic. A PDF's name: its own title, cleaned of what the program that made it added ("Microsoft Word -",
    ".doc"), else its entry's title, else its file name; never with the folder or the extension."""
    for name in (own, title if title != path else "", path.rsplit("/", 1)[-1]):
        name = _EXT.sub("", _JUNK.sub("", (name or "").strip())).strip()
        if len(name) > 3:
            return name
    return path


_WORD = re.compile(r"[A-Za-z0-9]{2,}")


def _match(terms: list[str], joiner: str) -> str:
    """Pure logic. An FTS5 query of the words, each quoted (so nothing in them is read as syntax)."""
    return f" {joiner} ".join('"' + t.replace('"', "") + '"' for t in terms)


def page_text(root: Path, pack_file: Path, path: str, page: int) -> tuple[str, str]:
    """One indexed page's whole text and its name (a PDF's page, or a page of a pack Kiwix didn't index); ("", "")
    when it isn't in the index."""
    db_file = index_path(root, pack_file)
    if not db_file.exists():
        return "", ""
    try:
        db = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        try:
            row = db.execute("SELECT body, title FROM docs WHERE path = ? AND page = ? LIMIT 1",
                             (path, int(page or 0))).fetchone()
        finally:
            db.close()
    except sqlite3.Error:
        return "", ""
    return (row[0], row[1]) if row else ("", "")


def _queries(terms: list[str]) -> list[list[str]]:
    """Pure logic. The FTS5 queries to try, in rounds: all the words; then every set of all but one; then all but
    two, and so on down to two words together; then any of them. A round's results are gathered together and the first round
    that finds any is used: which word to leave out can't be told from how common it is (in a canning guide
    "canning" is everywhere, yet it's the word that matters), so each is left out in turn and meaning picks."""
    from itertools import combinations

    rounds = [[_match(terms, "AND")]]
    for size in range(len(terms) - 1, 1, -1):  # down to two words together
        if size >= 2:
            rounds.append([_match(list(c), "AND") for c in combinations(terms, size)])
    rounds.append([_match(terms, "OR")])
    return rounds


def search(root: Path, library, query: str, limit: int = 20, full: bool = False, packs=None,
           per_index: int = 0) -> list[Hit]:
    """The question's words in every index here: all of them first, then any; best first, at most `limit`. With
    `full`, each hit carries its page's whole text instead of a passage around the words (`limit` from each index,
    so keep it small). `packs` is the library's list when the caller has it already. With `per_index`, each index's
    own best that many from each query of the first round that finds any (`_queries`), unranked against other
    indexes (their bm25 scores aren't one scale): the caller ranks them."""
    terms = [t.lower() for t in _WORD.findall(query or "")][:12]
    folder = index_folder(root)
    if not terms or not folder.is_dir():
        return []
    packs = packs if packs is not None else (library.list_packs() if library else [])
    titles = {Path(p.file_path).stem: (p.pack_id, p.title) for p in packs}
    hits: list[tuple[float, Hit]] = []
    for db_file in folder.glob("*.sqlite"):
        pack_id, pack_title = titles.get(db_file.stem, (db_file.stem, db_file.stem))
        try:
            db = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            body = "body" if full else "snippet(docs, 3, '', '', ' ... ', 40)"
            rows = []
            for queries in _queries(terms):
                found: dict = {}
                for query in queries:
                    for row in db.execute(f"SELECT path, title, page, {body}, bm25(docs) "
                                          "FROM docs WHERE docs MATCH ? ORDER BY bm25(docs) LIMIT ?",
                                          (query, per_index or limit)).fetchall():
                        found.setdefault((row[0], row[2]), row)
                rows = sorted(found.values(), key=lambda r: r[4])[:(per_index or limit) * max(1, len(queries))]
                if rows:
                    break
            for path, title, page, snip, score in rows:
                name = f"{title}, page {page}" if page else title
                hits.append((score, Hit(pack_id, pack_title, name, snip, path, int(page or 0))))
        except sqlite3.Error as problem:
            log.info("An offline index couldn't be searched (%s): %s", db_file.name, problem)
        finally:
            db.close()
    if per_index:  # each index's own best few: bm25 from different indexes isn't one scale (a big one wins)
        return [h for _s, h in hits]
    return [h for _s, h in sorted(hits, key=lambda sh: sh[0])][:limit]


if __name__ == "__main__" and "--pdf-worker" in sys.argv:
    _worker_main()
