"""
core.textbook_manager
========================

The textbook tutor's library (2026-09-28): "a feature where MIA gets
textbooks that can be added to her that she can reference to help
educate the user on subjects of their choice... understand it and
assist a user in understanding it."

Adding a book copies it into the textbooks folder (sibling of `data/`,
like `reference_library/`: books can be large, and `data/` is what the
backup copies wholesale), reads its text page by page
(core/document_text.py), finds its chapters, and splits it into
passages that remember their page. Questions are answered from the
passages that best match, so the tutor can always say which page it's
reading from.

**Retrieval is keyword scoring, not embeddings**, same reasoning as
core/device_help_manager.py: offline, instant on a Pi, and no model to
download. Each query word counts by how rare it is in the book (an
IDF weight), so "breaker" outweighs "the". Good enough for "what does
the book say about GFCI outlets"; a meaning-based index can come later
if real use shows keyword matching missing things.

**Chapters** are lines like "Chapter 3: Branch Circuits" (also Unit,
Lesson, Part) or Markdown "#" headings. A page with three or more such
lines is a table of contents and skipped, so the chapter list points at
real chapter pages. A book without recognizable chapters is one "Whole
book" chapter.

Scanned PDFs (images only) can't be read without OCR and are refused
with a plain message rather than added empty.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.document_text import PDF_SUFFIXES, TEXT_SUFFIXES, extract, first_heading
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = _PROJECT_ROOT / "textbooks"
_DATA_DIR = _PROJECT_ROOT / "data"
_LIBRARY_FILE = _DATA_DIR / "textbooks.json"
_INDEX_DIR = _DATA_DIR / "textbook_index"

SUPPORTED_SUFFIXES = PDF_SUFFIXES | TEXT_SUFFIXES
_PASSAGE_CHARS = 900

_CHAPTER_LINE = re.compile(
    r"^\s*(?:chapter|unit|lesson|part|module)\s+([0-9]{1,3}|[ivxlc]{1,7})\b[\s:.\-–—]*(.{0,80})$", re.IGNORECASE,
)
_MARKDOWN_HEADING = re.compile(r"^#{1,2}\s+(.{2,80})$")
_WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")
_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "your", "with", "this", "that", "from", "have", "has",
    "was", "were", "what", "when", "where", "which", "who", "how", "why", "does", "did", "can", "about",
    "into", "than", "then", "them", "they", "their", "there", "these", "those", "its", "our", "out", "all",
    "any", "may", "will", "would", "should", "could", "also", "each", "such", "more", "most", "some",
    "book", "say", "says", "tell", "explain", "mean", "means", "chapter", "page", "me", "is", "it", "of", "to",
}


def tokenize(text: str) -> list[str]:
    """Pure logic: lowercase content words, lightly stemmed."""
    words = []
    for word in _WORD.findall(text.lower()):
        word = word.strip("'-")
        if len(word) < 3 or word in _STOPWORDS:
            continue
        for suffix in ("ies", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)] + ("y" if suffix == "ies" else "")
                break
        words.append(word)
    return words


@dataclass
class Chapter:
    title: str
    page: int  # 1-based


@dataclass
class Passage:
    page: int  # 1-based
    chapter: int  # index into Textbook.chapters
    text: str


@dataclass
class Textbook:
    book_id: str
    title: str
    filename: str
    page_count: int
    chapters: list[Chapter] = field(default_factory=list)
    course_id: str = ""  # set once a Classroom course is made from it
    added_at: str = ""

    @staticmethod
    def from_dict(data: dict) -> "Textbook":
        return Textbook(
            book_id=data["book_id"], title=data.get("title", ""), filename=data.get("filename", ""),
            page_count=int(data.get("page_count", 0)),
            chapters=[Chapter(**c) for c in data.get("chapters", [])],
            course_id=data.get("course_id", ""), added_at=data.get("added_at", ""),
        )


@dataclass
class SearchHit:
    book: Textbook
    passage: Passage
    score: float

    @property
    def chapter_title(self) -> str:
        chapters = self.book.chapters
        return chapters[self.passage.chapter].title if 0 <= self.passage.chapter < len(chapters) else ""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def find_chapters(pages: list[str]) -> list[Chapter]:
    """Pure logic. Chapter starts, skipping table-of-contents pages."""
    chapters: list[Chapter] = []
    seen_numbers: set[str] = set()
    for number, page in enumerate(pages, start=1):
        matches = []
        for line in page.splitlines():
            line = line.strip()
            m = _CHAPTER_LINE.match(line)
            if m:
                label = m.group(2).strip(" .:-–—")
                # A dotted leader or trailing page number is a TOC entry, not a heading.
                if re.search(r"\.{3,}|\s\d{1,4}$", label):
                    matches.append(None)
                    continue
                matches.append((m.group(1).lower(), line if not label else f"{line.split()[0].title()} {m.group(1)}: {label}"))
                continue
            m = _MARKDOWN_HEADING.match(line)
            if m:
                matches.append((m.group(1).lower(), m.group(1).strip()))
        if len(matches) >= 3:
            continue  # a contents page
        for match in matches:
            if match is None or match[0] in seen_numbers:
                continue
            seen_numbers.add(match[0])
            chapters.append(Chapter(title=match[1], page=number))
    return chapters or [Chapter(title="Whole book", page=1)]


def chapter_for_page(chapters: list[Chapter], page: int) -> int:
    index = 0
    for i, chapter in enumerate(chapters):
        if chapter.page <= page:
            index = i
    return index


def split_passages(pages: list[str], chapters: list[Chapter], max_chars: int = _PASSAGE_CHARS) -> list[Passage]:
    """Pure logic. Paragraph-sized passages that never cross a page."""
    passages: list[Passage] = []
    for number, page in enumerate(pages, start=1):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page) if p.strip()]
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in page.splitlines() if p.strip()]
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) > max_chars:
                passages.append(Passage(number, chapter_for_page(chapters, number), current))
                current = ""
            current = f"{current}\n{paragraph}" if current else paragraph
            while len(current) > max_chars * 1.5:
                passages.append(Passage(number, chapter_for_page(chapters, number), current[:max_chars]))
                current = current[max_chars:]
        if current:
            passages.append(Passage(number, chapter_for_page(chapters, number), current))
    return passages


# ---------------------------------------------------------------------------
# The library
# ---------------------------------------------------------------------------


class TextbookManager:
    def __init__(self, context) -> None:
        self.context = context
        self._books: list[Textbook] = []
        self._passages: dict[str, list[Passage]] = {}  # loaded lazily per book
        self._load()

    @property
    def root(self) -> Path:
        configured = self.context.config.get("textbooks.root_path", "") if self.context.config else ""
        return Path(configured) if configured else _DEFAULT_ROOT

    def _load(self) -> None:
        if not _LIBRARY_FILE.exists():
            return
        try:
            self._books = [Textbook.from_dict(d) for d in json.loads(_LIBRARY_FILE.read_text(encoding="utf-8"))]
        except (json.JSONDecodeError, OSError, KeyError, TypeError):
            log.exception("textbooks.json unreadable — starting with an empty library.")
            notify_data_corruption(self.context, "textbooks.json")
            self._books = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_LIBRARY_FILE, json.dumps([asdict(b) for b in self._books], indent=2))

    def all_books(self) -> list[Textbook]:
        return list(self._books)

    def get_book(self, book_id: str) -> Optional[Textbook]:
        return next((b for b in self._books if b.book_id == book_id), None)

    def add_book(self, source: Path, title: str = "") -> Textbook:
        """Copy, read and index a book. Raises ValueError with a plain
        message for an unsupported or unreadable file."""
        source = Path(source)
        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"MIA can read PDF and text books; '{source.suffix}' isn't supported yet.")
        document = extract(source)
        if not document.readable or not any(p.strip() for p in document.pages):
            raise ValueError(document.note or "There's no readable text in that file.")
        book_id = uuid.uuid4().hex[:10]
        self.root.mkdir(parents=True, exist_ok=True)
        stored = self.root / f"{book_id}{source.suffix.lower()}"
        shutil.copy2(source, stored)
        pages = document.pages
        if source.suffix.lower() in TEXT_SUFFIXES:
            pages = self._split_text_pages(pages[0])
        chapters = find_chapters(pages)
        passages = split_passages(pages, chapters)
        name = title.strip() or document.title or first_heading(pages[0]) or source.stem.replace("_", " ")
        book = Textbook(
            book_id=book_id, title=name, filename=stored.name, page_count=len(pages),
            chapters=chapters, added_at=datetime.now().isoformat(timespec="seconds"),
        )
        _INDEX_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_INDEX_DIR / f"{book_id}.json", json.dumps([asdict(p) for p in passages]))
        self._passages[book_id] = passages
        self._books.append(book)
        self._save()
        log.info("Textbook added: '%s' (%d pages, %d chapters, %d passages)", name, len(pages), len(chapters), len(passages))
        return book

    @staticmethod
    def _split_text_pages(text: str, lines_per_page: int = 60) -> list[str]:
        """A plain-text book has no pages; make page-sized ones so
        answers can still point somewhere."""
        lines = text.splitlines()
        return ["\n".join(lines[i:i + lines_per_page]) for i in range(0, max(len(lines), 1), lines_per_page)]

    def remove_book(self, book_id: str) -> bool:
        book = self.get_book(book_id)
        if book is None:
            return False
        self._books = [b for b in self._books if b.book_id != book_id]
        self._passages.pop(book_id, None)
        for path in (self.root / book.filename, _INDEX_DIR / f"{book_id}.json"):
            try:
                path.unlink()
            except OSError:
                pass
        self._save()
        return True

    def passages(self, book_id: str) -> list[Passage]:
        if book_id not in self._passages:
            try:
                raw = json.loads((_INDEX_DIR / f"{book_id}.json").read_text(encoding="utf-8"))
                self._passages[book_id] = [Passage(**p) for p in raw]
            except (OSError, json.JSONDecodeError, TypeError):
                log.exception("Textbook index for %s unreadable.", book_id)
                self._passages[book_id] = []
        return self._passages[book_id]

    def search(self, query: str, book_id: Optional[str] = None, chapter: Optional[int] = None, limit: int = 4) -> list[SearchHit]:
        """Best-matching passages, across one book or all."""
        terms = tokenize(query)
        if not terms:
            return []
        hits: list[SearchHit] = []
        for book in self._books:
            if book_id and book.book_id != book_id:
                continue
            passages = self.passages(book.book_id)
            if chapter is not None:
                passages = [p for p in passages if p.chapter == chapter]
            if not passages:
                continue
            counts = [Counter(tokenize(p.text)) for p in passages]
            document_frequency = Counter(term for c in counts for term in set(c))
            n = len(passages)
            for passage, count in zip(passages, counts):
                score = 0.0
                for term in set(terms):
                    if count[term]:
                        idf = math.log(1 + n / document_frequency[term])
                        score += idf * (1 + math.log(count[term]))
                if score > 0:
                    hits.append(SearchHit(book, passage, round(score, 4)))
        hits.sort(key=lambda h: -h.score)
        return hits[:limit]

    def find_book(self, words: str) -> Optional[Textbook]:
        """The book whose title best overlaps `words`, if any overlap at all."""
        wanted = set(tokenize(words))
        best, best_overlap = None, 0
        for book in self._books:
            overlap = len(wanted & set(tokenize(book.title)))
            if overlap > best_overlap:
                best, best_overlap = book, overlap
        return best

    def find_chapter(self, book: Textbook, words: str) -> Optional[int]:
        """'chapter 3' or words from a chapter title -> chapter index."""
        m = re.search(r"\b(?:chapter|unit|lesson|part)\s+([0-9]{1,3}|[ivxlc]{1,7})\b", words.lower())
        if m:
            for i, chapter in enumerate(book.chapters):
                if re.search(rf"\b{re.escape(m.group(1))}\b", chapter.title.lower()):
                    return i
        wanted = set(tokenize(words))
        scored = [(len(wanted & set(tokenize(c.title))), i) for i, c in enumerate(book.chapters)]
        best = max(scored, default=(0, None))
        return best[1] if best[0] else None

    def make_course(self, book_id: str) -> Optional[str]:
        """A Classroom course from the book: one lesson per chapter. Returns the course id."""
        book = self.get_book(book_id)
        classroom = getattr(self.context, "classroom", None)
        if book is None or classroom is None:
            return None
        if book.course_id and classroom.get_course(book.course_id) is not None:
            return book.course_id
        subject = next((s for s in classroom.all_subjects() if s.name == "Textbooks"), None)
        if subject is None:
            subject = classroom.add_subject("Textbooks", category="Study", description="Courses made from your textbooks.")
        course = classroom.add_course(subject.subject_id, book.title, description=f"From your textbook ({book.page_count} pages).")
        for chapter in book.chapters:
            classroom.add_lesson(course.course_id, chapter.title, notes=f"Starts on page {chapter.page}.")
        book.course_id = course.course_id
        self._save()
        return course.course_id
