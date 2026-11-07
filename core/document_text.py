"""
core.document_text
=====================

Text out of the documents the owner gives MIA: shared by the textbook
tutor (core/textbook_manager.py) and the document inbox
(core/inbox_manager.py). 2026-09-28.

Formats:
- **PDF**, page by page, through PySide6's own QtPdf (already a
  dependency via PySide6; confirmed to work with no display, so the
  headless Pi path can use it too). No new PDF library.
- **Plain text / Markdown**, as one page.
- **HTML**, tags stripped, as one page; a table row with text in two or
  more cells (an emailed receipt's item and price) stays one line
  (2026-11-07), so the receipt reader can find its lines.
- **Email (.eml)**, through the standard library's email parser:
  subject, sender, date, the text body as a page, and every attachment
  returned as raw bytes so the caller can store and read it too.

**Photos and scanned pages** have no text to extract here; they come
back readable=False with needs_ocr=True, and the caller hands them to
core/ocr.py (Tesseract, in the background) when it's installed.
"""

from __future__ import annotations

import email
import email.policy
import re
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

PDF_SUFFIXES = {".pdf"}
TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".text", ".csv"}
HTML_SUFFIXES = {".html", ".htm"}
EMAIL_SUFFIXES = {".eml"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
READABLE_SUFFIXES = PDF_SUFFIXES | TEXT_SUFFIXES | HTML_SUFFIXES | EMAIL_SUFFIXES


@dataclass
class Attachment:
    """A file attached to an email: its name, its bytes and its content type."""
    filename: str
    data: bytes
    content_type: str = ""


@dataclass
class ExtractedDocument:
    """What was read from a document: its pages' text, its title (PDF title, email subject or first heading), for an
    email the sender, date and attachments, whether anything could be read (and why not), and whether OCR could read
    it (a photo or scanned PDF).
    """
    pages: list[str] = field(default_factory=list)  # page text, in order
    title: str = ""  # PDF title / email subject / first heading, if any
    sender: str = ""  # email only
    date: str = ""  # email only, ISO date
    attachments: list[Attachment] = field(default_factory=list)  # email only
    readable: bool = True  # False for images / unknown types: nothing could be read
    note: str = ""  # why not, when not readable
    needs_ocr: bool = False  # a photo or scanned PDF: core/ocr.py can read it

    @property
    def text(self) -> str:
        """All the pages' text, a blank line between pages."""
        return "\n\n".join(self.pages)


class _TextFromHtml(HTMLParser):
    """An HTML parser that keeps the visible text: scripts and styles left out, a line break at each block
    (paragraph, line break, div, list item, heading). A table row whose cells hold text in two or more of them (an
    emailed receipt's "Whole milk | $3.49") becomes one line, its cells a gap apart, as the receipt reader needs;
    a row with one such cell (an email's layout table around everything) keeps that cell's own lines. Rows a message
    leaves unclosed are closed by the next row, or the end of their table.
    """
    def __init__(self) -> None:
        """Starts with no text collected and no table open."""
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0
        self._tables = 0  # how deep in tables the text is now
        self._rows: list[dict] = []  # open rows, innermost last: {"table": its table's depth, "cells": [[text]]}

    def _target(self) -> list:
        """Where text goes now: the innermost open row's last cell, else the page."""
        if self._rows:
            row = self._rows[-1]
            if not row["cells"]:
                row["cells"].append([])
            return row["cells"][-1]
        return self.parts

    def _close_rows(self, depth: int) -> None:
        """Closes the open rows of tables at this depth or deeper, each into the text around it."""
        while self._rows and self._rows[-1]["table"] >= depth:
            row = self._rows.pop()
            cells = [" ".join("".join(cell).split()) for cell in row["cells"]]
            filled = [c for c in cells if c]
            if len(filled) >= 2:
                text = "   ".join(filled)
            else:
                text = next(("".join(cell) for cell in row["cells"] if "".join(cell).strip()), "")
            self._target().append("\n" + text + "\n")

    def handle_starttag(self, tag, attrs):
        """Entering a script or style: stop collecting; a table, row or cell: start one (a new row closes the last
        row of its own table); another block tag: a new line."""
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "table":
            self._tables += 1
        elif tag == "tr":
            self._close_rows(self._tables)
            self._rows.append({"table": self._tables, "cells": []})
        elif tag in ("td", "th"):
            if self._rows and self._rows[-1]["table"] == self._tables:
                self._rows[-1]["cells"].append([])
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4"):
            self._target().append("\n")

    def handle_endtag(self, tag):
        """Leaving a script or style: collect again; a row: it's closed; a table: its open rows are, and it ends."""
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag == "tr":
            self._close_rows(self._tables)
        elif tag == "table" and self._tables:
            self._close_rows(self._tables)
            self._tables -= 1

    def handle_data(self, data):
        """Keeps text that isn't inside a script or style, in the cell it's in (or on the page)."""
        if not self._skip:
            self._target().append(data)

    def close(self) -> None:
        """Finishes reading, closing any rows a message left open."""
        super().close()
        self._close_rows(0)


def html_to_text(html: str) -> str:
    """Pure logic. HTML as plain text: tags out, a table row of several cells on one line, spaces collapsed, at most
    one blank line between blocks."""
    parser = _TextFromHtml()
    parser.feed(html)
    parser.close()
    text = "".join(parser.parts)
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def _decode(data: bytes) -> str:
    """Bytes as text: UTF-8, else Windows-1252, else Latin-1 (never fails)."""
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def pdf_pages(path: Path) -> tuple[list[str], str]:
    """(page texts, document title). Raises ValueError if unreadable."""
    from PySide6.QtPdf import QPdfDocument  # local: only PDF callers pay the import

    document = QPdfDocument(None)
    error = document.load(str(path))
    if error != QPdfDocument.Error.None_:
        raise ValueError(f"couldn't open the PDF ({error.name})")
    pages = [document.getAllText(i).text() for i in range(document.pageCount())]
    title = document.metaData(QPdfDocument.MetaDataField.Title) or ""
    document.close()
    return pages, str(title).strip()


def parse_email(data: bytes) -> ExtractedDocument:
    """Pure logic. An .eml file's subject, sender, date, its text body as pages (the HTML body when there's no plain
    one), and every attachment's bytes, so they can be stored and read too.
    """
    message = email.message_from_bytes(data, policy=email.policy.default)
    body_parts: list[str] = []
    attachments: list[Attachment] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        content_type = part.get_content_type()
        if filename:
            payload = part.get_payload(decode=True) or b""
            attachments.append(Attachment(filename=Path(filename).name, data=payload, content_type=content_type))
        elif content_type == "text/plain":
            body_parts.append(part.get_content())
        elif content_type == "text/html" and not body_parts:
            body_parts.append(html_to_text(part.get_content()))
    when = ""
    if message["date"]:
        try:
            when = parsedate_to_datetime(message["date"]).date().isoformat()
        except (TypeError, ValueError):
            when = ""
    return ExtractedDocument(
        pages=[p.strip() for p in body_parts if p.strip()],
        title=str(message["subject"] or "").strip(),
        sender=str(message["from"] or "").strip(),
        date=when,
        attachments=attachments,
    )


def extract(path: Path) -> ExtractedDocument:
    """Never raises for a bad file: returns readable=False with a note."""
    suffix = path.suffix.lower()
    try:
        if suffix in PDF_SUFFIXES:
            pages, title = pdf_pages(path)
            if not any(p.strip() for p in pages):
                return ExtractedDocument(pages=pages, title=title, readable=False, needs_ocr=True,
                                         note="The PDF has no text layer (probably a scan).")
            return ExtractedDocument(pages=pages, title=title)
        if suffix in TEXT_SUFFIXES:
            return ExtractedDocument(pages=[_decode(path.read_bytes())])
        if suffix in HTML_SUFFIXES:
            return ExtractedDocument(pages=[html_to_text(_decode(path.read_bytes()))])
        if suffix in EMAIL_SUFFIXES:
            return parse_email(path.read_bytes())
        if suffix in IMAGE_SUFFIXES:
            return ExtractedDocument(readable=False, needs_ocr=True, note="It's a photo.")
        return ExtractedDocument(readable=False, note=f"MIA can't read '{suffix or 'unknown'}' files yet.")
    except (OSError, ValueError) as exc:
        log.warning("Couldn't read %s: %s", path, exc)
        return ExtractedDocument(readable=False, note=f"Couldn't read the file: {exc}")


def first_heading(text: str) -> Optional[str]:
    """The first line of 3 to 120 characters (Markdown # stripped), as a title, or None."""
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if 3 <= len(line) <= 120:
            return line
    return None
