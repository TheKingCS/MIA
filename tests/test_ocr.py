"""
Reading photos and scans (core/ocr.py) and how the inbox and the textbook
tutor use it. Most tests use a stand-in engine so they run anywhere; the
ones marked `needs_tesseract` run the real program when it's installed.
"""

import shutil
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QImage, QImageIOHandler, QImageWriter, QPageSize, QPainter, QPdfWriter
from PySide6.QtWidgets import QApplication

import core.ocr as ocr_module
from core.config_manager import ConfigManager
from core.ocr import OcrError, OcrQueue, clean_text, read_result
from core.textbook_manager import TextbookManager
from tests import test_inbox, test_textbook_tutor
from tests.test_inbox import RECEIPT_TEXT, drop
from tests.test_textbook_tutor import PAGES, write_pdf

needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract not installed")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def inbox_ctx(tmp_path, monkeypatch, qapp):
    return test_inbox.make_ctx(tmp_path, monkeypatch)


@pytest.fixture
def tutor_ctx(tmp_path, monkeypatch, qapp):
    return test_textbook_tutor.make_ctx(tmp_path, monkeypatch)


def fake_engine(texts_by_suffix):
    """Pages for a document by its file type; OcrError for a text of None."""
    calls = []

    def engine(job, on_page, should_stop):
        calls.append(job.source.name)
        pages = texts_by_suffix[job.source.suffix.lower()]
        if pages is None:
            raise OcrError("Couldn't open the image.")
        done = []
        for page in pages:
            done.append(page)
            on_page(done, len(pages))
        return done

    engine.calls = calls
    return engine


def text_image(lines, width=1400, height=1000) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    font = QFont("DejaVu Sans")
    font.setPixelSize(40)
    painter.setFont(font)
    painter.setPen(QColor("black"))
    for n, line in enumerate(lines):
        painter.drawText(60, 110 + n * 80, line)
    painter.end()
    return image


def scanned_pdf(path: Path, pages: list[list[str]]) -> Path:
    """A PDF whose pages are only pictures of text, like a scan."""
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
    writer.setResolution(150)
    painter = QPainter(writer)
    for i, lines in enumerate(pages):
        if i:
            writer.newPage()
        painter.drawImage(QRectF(0, 0, 1275, 1650), text_image(lines, 1275, 1650))
    painter.end()
    return path


# ------------------------------------------------------------------ the queue


def test_clean_text():
    assert clean_text("TOTAL 36.23  \n\n\n\nThanks\f\n") == "TOTAL 36.23\n\nThanks"


def test_queue_reads_in_the_background_and_writes_results(tmp_path):
    engine = fake_engine({".jpg": ["TOTAL 5.00"], ".png": None})
    queue = OcrQueue(None, engine=engine)
    assert queue.submit("a", tmp_path / "a.jpg", tmp_path / "a.json")
    assert queue.submit("b", tmp_path / "b.png", tmp_path / "b.json")
    assert queue.wait(10)
    assert read_result(tmp_path / "a.json").text == "TOTAL 5.00"
    failed = read_result(tmp_path / "b.json")
    assert failed.pages == [] and "Couldn't open" in failed.error
    assert read_result(tmp_path / "missing.json") is None
    assert queue.progress("a") is None and not queue.is_queued("a")


def test_queue_dedupes_reports_progress_and_cancels(tmp_path):
    release = threading.Event()

    def slow(job, on_page, should_stop):
        on_page(["p1"], 3)
        release.wait(5)
        return [] if should_stop() else ["p1", "p2", "p3"]

    queue = OcrQueue(None, engine=slow)
    queue.submit("book", tmp_path / "b.pdf", tmp_path / "b.json")
    queue.submit("book", tmp_path / "b.pdf", tmp_path / "b.json")  # not twice
    queue.submit("other", tmp_path / "o.pdf", tmp_path / "o.json")
    for _ in range(100):
        if queue.progress("book") == (1, 3):
            break
        threading.Event().wait(0.02)
    assert queue.progress("book") == (1, 3) and queue.progress("other") == (0, 0)
    queue.cancel("other")
    queue.cancel("book")
    release.set()
    assert queue.wait(5)
    assert not (tmp_path / "b.json").exists() and not (tmp_path / "o.json").exists()


def test_unavailable_without_tesseract(monkeypatch):
    monkeypatch.setattr(ocr_module.shutil, "which", lambda name: None)
    config = ConfigManager.__new__(ConfigManager)
    config.get = lambda key, default=None: default
    assert not ocr_module.available(config)
    assert not OcrQueue(type("C", (), {"config": config})()).submit("x", Path("x.jpg"), Path("x.json"))


# ------------------------------------------------------------------ the inbox


def test_a_receipt_photo_is_read_then_announced(inbox_ctx):
    ctx = inbox_ctx
    ctx.ocr = OcrQueue(ctx, engine=fake_engine({".jpg": [RECEIPT_TEXT]}))
    assert drop(ctx, "IMG_2041.jpg", b"\xff\xd8 photo bytes", source="phone") == []  # not announced while reading
    [item] = ctx.inbox.pending()
    assert item.reading and "Reading" in item.note
    ctx.ocr.wait(10)
    [ready] = ctx.inbox.scan(now=float("inf"))
    assert ready.item_id == item.item_id and not ready.reading and ready.readable
    assert ready.doc_type == "receipt" and ready.amount == 36.23 and ready.vendor == "Lowe's" and ready.note == ""
    assert ctx.inbox.scan(now=float("inf")) == []  # announced once


def test_a_failed_read_says_why_and_is_still_filable(inbox_ctx):
    ctx = inbox_ctx
    ctx.ocr = OcrQueue(ctx, engine=fake_engine({".jpg": None}))
    drop(ctx, "blurry.jpg", b"\xff\xd8")
    ctx.ocr.wait(10)
    [item] = ctx.inbox.scan(now=float("inf"))
    assert not item.readable and "Couldn't open" in item.note
    ctx.inbox.file_item(item.item_id, asset_id=ctx.mower.asset_id)
    assert ctx.maintenance.get_asset(ctx.mower.asset_id).documents == ["blurry.jpg"]


def test_without_ocr_a_photo_says_how_to_enable_it(inbox_ctx):
    [item] = drop(inbox_ctx, "receipt.jpg", b"\xff\xd8")
    assert not item.reading and "Tesseract" in item.note


def test_an_emailed_scan_attachment_is_read(inbox_ctx):
    from email.message import EmailMessage

    ctx = inbox_ctx
    ctx.ocr = OcrQueue(ctx, engine=fake_engine({".png": ["Operator's Manual Z315E\nChange engine oil every 50 hours."]}))
    message = EmailMessage()
    message["Subject"] = "photo of the manual page"
    message.set_content("From my phone.")
    message.add_attachment(b"\x89PNG fake", maintype="image", subtype="png", filename="page.png")
    drop(ctx, "message.eml", message.as_bytes(), source="email")
    ctx.ocr.wait(10)
    [item] = ctx.inbox.scan(now=float("inf"))
    assert item.asset_id == ctx.mower.asset_id and item.schedule[0]["task"] == "Change engine oil"


def test_reading_resumes_after_a_restart(inbox_ctx):
    from types import SimpleNamespace

    from core.inbox_manager import InboxManager

    ctx = inbox_ctx
    ctx.ocr = SimpleNamespace(submit=lambda *a: True)  # queued, then MIA closed before it ran
    drop(ctx, "receipt.jpg", b"\xff\xd8")
    ctx.ocr = OcrQueue(ctx, engine=fake_engine({".jpg": [RECEIPT_TEXT]}))
    restarted = InboxManager(ctx)
    assert restarted.pending()[0].reading
    assert restarted.scan(now=float("inf")) == []  # queues it again
    ctx.ocr.wait(10)
    [item] = restarted.scan(now=float("inf"))
    assert item.amount == 36.23


# ------------------------------------------------------------------ textbooks


def test_a_scanned_textbook_is_read_then_indexed(tutor_ctx):
    ctx = tutor_ctx
    ctx.ocr = OcrQueue(ctx, engine=fake_engine({".pdf": PAGES}))
    scan = write_pdf(ctx.tmp / "scan.pdf", ["", "", "", ""], None)
    book = ctx.textbooks.add_book(scan, title="Wiring (scanned)")
    assert book.reading and book.page_count == 4 and ctx.textbooks.passages(book.book_id) == []
    ctx.ocr.wait(10)
    assert ctx.textbooks.finish_reading()
    assert not book.reading and [c.page for c in book.chapters] == [2, 3, 4] and "Grounding" in book.chapters[2].title
    assert ctx.textbooks.search("GFCI trips")[0].passage.page == 3
    assert not ctx.textbooks.finish_reading()
    # Persisted.
    again = TextbookManager(ctx).get_book(book.book_id)
    assert not again.reading and len(again.chapters) == 3


def test_scanned_textbook_failures(tutor_ctx):
    ctx = tutor_ctx
    scan = write_pdf(ctx.tmp / "scan.pdf", [""], None)
    ctx.ocr = OcrQueue(ctx, engine=fake_engine({".pdf": [""]}))
    book = ctx.textbooks.add_book(scan)
    ctx.ocr.wait(10)
    ctx.textbooks.finish_reading()
    assert not book.reading and "No text" in book.reading_error


def test_removing_a_book_being_read(tutor_ctx):
    ctx = tutor_ctx
    release = threading.Event()
    ctx.ocr = OcrQueue(ctx, engine=lambda job, on_page, stop: release.wait(5) and [] or [])
    book = ctx.textbooks.add_book(write_pdf(ctx.tmp / "scan.pdf", [""], None))
    assert ctx.textbooks.reading_progress(book.book_id) is not None
    ctx.textbooks.remove_book(book.book_id)
    release.set()
    ctx.ocr.wait(5)
    assert ctx.textbooks.all_books() == [] and not ctx.ocr.is_queued(f"textbook:{book.book_id}")


def test_textbook_row_shows_progress(tutor_ctx):
    from gui.textbooks_panel import format_textbook_row
    from core.textbook_manager import Textbook

    book = Textbook(book_id="b", title="Wiring", filename="b.pdf", page_count=300, reading=True)
    assert "page 12 of 300" in format_textbook_row(book, (12, 300))
    assert "waiting" in format_textbook_row(book, (0, 0))
    book.reading, book.reading_error = False, "No text could be found on its pages."
    assert "couldn't be read" in format_textbook_row(book)


# ------------------------------------------------------------------ real Tesseract


@needs_tesseract
def test_real_ocr_of_a_sideways_phone_photo(tmp_path, qapp):
    """A phone stores a sideways photo plus an EXIF 'rotate me' tag;
    MIA must apply it or the receipt reads as garbage."""
    lines = ["LOWE'S HOME CENTERS", "09/28/2026", "DECK SCREWS 9.98", "SUBTOTAL 33.86", "TOTAL 36.23"]
    upright = text_image(lines)
    from PySide6.QtGui import QTransform

    sideways = upright.transformed(QTransform().rotate(-90))  # how the sensor saved it
    photo = tmp_path / "IMG_0001.jpg"
    writer = QImageWriter(str(photo), b"jpeg")
    writer.setTransformation(QImageIOHandler.Transformation.TransformationRotate90)
    assert writer.write(sideways)
    text = ocr_module.ocr_image(shutil.which("tesseract"), photo)
    assert "TOTAL 36.23" in text and "LOWE" in text


@needs_tesseract
def test_real_ocr_of_a_scanned_pdf_resumes(tmp_path, qapp):
    pdf = scanned_pdf(tmp_path / "scan.pdf", [["Chapter 1: Circuit Breakers"], ["Chapter 2: GFCI Outlets"]])
    exe = shutil.which("tesseract")
    first = ocr_module.ocr_pdf(exe, pdf, should_stop=lambda: False, done=None)
    assert "Circuit Breakers" in first[0] and "GFCI Outlets" in first[1]
    seen = []
    resumed = ocr_module.ocr_pdf(exe, pdf, done=["(already read)"], on_page=lambda pages, total: seen.append(len(pages)))
    assert resumed[0] == "(already read)" and seen == [2]  # only page 2 read again


@needs_tesseract
def test_real_ocr_through_the_inbox(inbox_ctx, qapp):
    ctx = inbox_ctx
    ctx.ocr = OcrQueue(ctx)
    photo = ctx.tmp / "receipt.png"
    text_image(["LOWE'S HOME CENTERS", "09/28/2026", "SUBTOTAL 33.86", "TOTAL 36.23"]).save(str(photo))
    drop(ctx, "receipt.png", photo.read_bytes(), source="phone")
    assert ctx.ocr.wait(60)
    [item] = ctx.inbox.scan(now=float("inf"))
    assert item.doc_type == "receipt" and item.amount == 36.23 and item.vendor == "Lowe's"
