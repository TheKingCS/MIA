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
- **HTML**, tags stripped, as one page.
- **Email (.eml)**, through the standard library's email parser:
  subject, sender, date, the text body as a page, and every attachment
  returned as raw bytes so the caller can store and read it too.

**Not supported: photos and scanned pages.** Reading text out of an
image needs OCR (Tesseract or similar), which isn't installed and isn't
worth pulling in blind. A photo of a receipt still gets filed; it just
has no text, and callers say so instead of pretending.
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
    filename: str
    data: bytes
    content_type: str = ""


@dataclass
class ExtractedDocument:
    pages: list[str] = field(default_factory=list)  # page text, in order
    title: str = ""  # PDF title / email subject / first heading, if any
    sender: str = ""  # email only
    date: str = ""  # email only, ISO date
    attachments: list[Attachment] = field(default_factory=list)  # email only
    readable: bool = True  # False for images / unknown types: nothing could be read
    note: str = ""  # why not, when not readable

    @property
    def text(self) -> str:
        return "\n\n".join(self.pages)


class _TextFromHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextFromHtml()
    parser.feed(html)
    text = "".join(parser.parts)
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def _decode(data: bytes) -> str:
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
                return ExtractedDocument(pages=pages, title=title, readable=False,
                                         note="The PDF has no text layer (probably a scan), and MIA can't read images yet.")
            return ExtractedDocument(pages=pages, title=title)
        if suffix in TEXT_SUFFIXES:
            return ExtractedDocument(pages=[_decode(path.read_bytes())])
        if suffix in HTML_SUFFIXES:
            return ExtractedDocument(pages=[html_to_text(_decode(path.read_bytes()))])
        if suffix in EMAIL_SUFFIXES:
            return parse_email(path.read_bytes())
        if suffix in IMAGE_SUFFIXES:
            return ExtractedDocument(readable=False, note="It's a photo, and MIA can't read text from images yet (no OCR).")
        return ExtractedDocument(readable=False, note=f"MIA can't read '{suffix or 'unknown'}' files yet.")
    except (OSError, ValueError) as exc:
        log.warning("Couldn't read %s: %s", path, exc)
        return ExtractedDocument(readable=False, note=f"Couldn't read the file: {exc}")


def first_heading(text: str) -> Optional[str]:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if 3 <= len(line) <= 120:
            return line
    return None
