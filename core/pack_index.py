"""
core.pack_index
=================

Her own search index for the offline packs Kiwix didn't index (core/offline_library.py). Many of the most useful ones
have no full-text index of their own: iFixit's repair guides, the USDA canning guide, the LibreTexts textbooks, and
the preppers' collections, which are PDFs inside the pack (water treatment, field medicine, food preserving,
post-disaster). libzim can only find those by title, so their words would be out of her reach.

**Building one** (`build`): every PDF in the pack (its text, page by page, through QtPdf, the same reader as
core/document_text.py; skipped where PySide6 isn't installed), and its HTML pages too when Kiwix gave the pack no
full-text index (Kiwix's index covers a pack's pages, never the PDFs inside it), go into a SQLite FTS5 table beside
the packs, `.fetch/index/<pack file>.sqlite`, built under a temporary name and moved into place only when finished.
`index_missing` builds every one that's missing (an empty index for a pack with nothing to add, so it isn't looked at
again) and removes any whose pack is gone; a pack over BIG_PACK that Kiwix indexed (Wikipedia, the Q&A sites: pages,
no PDFs) is left to Kiwix's index.

**Searching** (`search`): the question's words, all of them first, then any of them, ranked by FTS5's bm25, each hit
with its page (for a PDF) and a passage around the words. The indexes hold the packs' own published text, never
anything of his.
"""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

VERSION = "1"
BIG_PACK = 5 * 10**9  # an indexed pack this big is left to Kiwix's own index
PAGE_CHARS = 20_000  # of one page's text
PDF_PAGES = 600  # of one PDF


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


def _pdf_pages(data: bytes) -> tuple[list[str], str]:
    """A PDF's pages as text and its own title, through QtPdf; ([], "") where PySide6 isn't here or it won't open."""
    try:
        from core.document_text import pdf_pages
    except Exception:  # noqa: BLE001
        return [], ""
    handle, name = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(data)
        pages, title = pdf_pages(Path(name))
        return [p[:PAGE_CHARS] for p in pages[:PDF_PAGES]], title
    except Exception:  # noqa: BLE001 - a damaged PDF is skipped
        return [], ""
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
    `pages` says so); how many rows. The file appears only when finished."""
    if archive is None:
        from libzim.reader import Archive

        archive = Archive(str(pack_file))
    pages = needs_index(archive) if pages is None else pages
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    rows = 0
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
                texts, own = _pdf_pages(data)
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
    os.replace(tmp, out)
    return rows


def index_missing(library, root: Path, progress: Callable = lambda key, n: None) -> int:
    """Builds every index a pack wants and hasn't got (a pack copied in by hand too), and removes those whose pack
    is gone; how many were built. Never raises."""
    built = 0
    folder = index_folder(root)
    packs = {Path(p.file_path).stem: p for p in library.list_packs()} if library is not None else {}
    if folder.is_dir():
        for old in folder.glob("*.sqlite"):
            if old.stem not in packs:
                old.unlink(missing_ok=True)
    for stem, pack in packs.items():
        out = index_path(root, Path(pack.file_path))
        if out.exists():
            continue
        try:
            archive = library._get_archive(pack.pack_id, Path(pack.file_path))
            if archive is None or (not needs_index(archive) and Path(pack.file_path).stat().st_size > BIG_PACK):
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


def search(root: Path, library, query: str, limit: int = 20) -> list[Hit]:
    """The question's words in every index here: all of them first, then any; best first, at most `limit`."""
    terms = [t.lower() for t in _WORD.findall(query or "")][:12]
    folder = index_folder(root)
    if not terms or not folder.is_dir():
        return []
    titles = {Path(p.file_path).stem: (p.pack_id, p.title) for p in library.list_packs()} if library else {}
    hits: list[tuple[float, Hit]] = []
    for db_file in folder.glob("*.sqlite"):
        pack_id, pack_title = titles.get(db_file.stem, (db_file.stem, db_file.stem))
        try:
            db = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            for joiner in ("AND", "OR"):
                rows = db.execute("SELECT path, title, page, snippet(docs, 3, '', '', ' ... ', 40), bm25(docs) "
                                  "FROM docs WHERE docs MATCH ? ORDER BY bm25(docs) LIMIT ?",
                                  (_match(terms, joiner), limit)).fetchall()
                if rows:
                    break
            for path, title, page, snip, score in rows:
                name = f"{title}, page {page}" if page else title
                hits.append((score, Hit(pack_id, pack_title, name, snip, path, int(page or 0))))
        except sqlite3.Error as problem:
            log.info("An offline index couldn't be searched (%s): %s", db_file.name, problem)
        finally:
            db.close()
    return [h for _s, h in sorted(hits, key=lambda sh: sh[0])][:limit]
