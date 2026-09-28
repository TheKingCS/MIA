"""
core.ocr
===========

Reading text out of photos and scanned pages (2026-09-28), so a phone
photo of a paper receipt or a scanned manual/textbook works in the
document inbox (core/inbox_manager.py) and the textbook tutor
(core/textbook_manager.py).

**Engine: Tesseract**, the standard free, offline OCR program, run as a
separate program (`tesseract image.png -`), so there's no new Python
package: Linux/Pi `sudo apt install tesseract-ocr`; Windows, the
installer from github.com/UB-Mannheim/tesseract (MIA also looks in its
default install folder), or set `ocr.tesseract_path`. Without it,
everything else works and documents say how to enable reading them.

**Images are prepared with Qt first:** a phone photo's EXIF rotation is
applied (Tesseract ignores it, and a sideways receipt reads as noise),
it's turned to grayscale and capped in size. Scanned PDF pages are
rendered at 300 DPI onto white with QtPdf. HEIC photos (iPhone default)
can't be opened; the note says to share as JPEG.

**Slow, so it runs in the background.** A scanned 300-page textbook is
many minutes on a Pi, and even one page is a second or more. OcrQueue
reads one document at a time on its own thread. The thread only writes
its result file (`<output>.json`, pages plus any error); the inbox and
the textbook library pick results up on their normal GUI-thread checks,
so no managers are touched from the thread (CLAUDE.md: threading only
where a long task needs it, scoped to it). Progress of a long book is
saved every few pages to `<output>.partial.json`, so a restart resumes
instead of starting over. Tesseract runs at lower priority so the screen
and voice stay responsive.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
_WINDOWS_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
_PDF_DPI = 300
_MAX_SIDE = 4000  # pixels; bigger phone photos are scaled down (no gain, much slower)
_PAGE_TIMEOUT = 180  # seconds for one page
_SAVE_EVERY = 5  # pages between progress saves

INSTALL_HINT = "install Tesseract to let MIA read it (docs/SETUP_GUIDE.md, Part 1a)"


class OcrError(Exception):
    """A document that couldn't be read; the message is shown to the owner."""


def tesseract_path(config) -> Optional[str]:
    configured = str(config.get("ocr.tesseract_path", "") or "") if config else ""
    if configured:
        return configured if Path(configured).exists() else None
    found = shutil.which("tesseract")
    if found:
        return found
    return str(_WINDOWS_DEFAULT) if os.name == "nt" and _WINDOWS_DEFAULT.exists() else None


def available(config) -> bool:
    if config is not None and config.get("ocr.enabled", True) is False:
        return False
    return tesseract_path(config) is not None


def unavailable_note(kind: str) -> str:
    """kind: 'photo' or 'scan'."""
    what = "It's a photo" if kind == "photo" else "The PDF has no text layer (a scan)"
    return f"{what}; {INSTALL_HINT}."


# ---------------------------------------------------------------------------
# Reading one image / one PDF (runs on the queue's thread)
# ---------------------------------------------------------------------------


def run_tesseract(exe: str, image: Path, language: str = "eng", timeout: int = _PAGE_TIMEOUT) -> str:
    env = dict(os.environ, OMP_THREAD_LIMIT="1")  # one core: the rest of MIA keeps running smoothly
    command = [exe, str(image), "-", "-l", language]
    nice = shutil.which("nice") if os.name == "posix" else None
    if nice:
        command = [nice, "-n", "10"] + command  # lower priority (not preexec_fn: unsafe with threads)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        raise OcrError("Reading a page took too long.") from exc
    except OSError as exc:
        raise OcrError(f"Couldn't run Tesseract: {exc}") from exc
    if result.returncode != 0:
        raise OcrError(f"Tesseract failed: {(result.stderr or '').strip()[:200]}")
    return clean_text(result.stdout)


def clean_text(text: str) -> str:
    """Pure logic. Tesseract's output without form feeds and runs of blank lines."""
    lines = [line.rstrip() for line in text.replace("\f", "\n").splitlines()]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


def _prepare_image(image, target: Path) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage

    if max(image.width(), image.height()) > _MAX_SIDE:
        image = image.scaled(_MAX_SIDE, _MAX_SIDE, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    image = image.convertToFormat(QImage.Format.Format_Grayscale8)
    if not image.save(str(target), "PNG"):
        raise OcrError("Couldn't prepare the image for reading.")


def ocr_image(exe: str, path: Path, language: str = "eng") -> str:
    from PySide6.QtGui import QImageReader

    if path.suffix.lower() in (".heic", ".heif"):
        raise OcrError("HEIC photos can't be read; share or save it as a JPEG instead.")
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)  # apply the phone's EXIF rotation
    image = reader.read()
    if image.isNull():
        raise OcrError(f"Couldn't open the image ({reader.errorString()}).")
    with tempfile.TemporaryDirectory(prefix="mia_ocr_") as tmp:
        target = Path(tmp) / "page.png"
        _prepare_image(image, target)
        return run_tesseract(exe, target, language)


def ocr_pdf(
    exe: str, path: Path, language: str = "eng", done: Optional[list[str]] = None,
    on_page: Optional[Callable[[list[str], int], None]] = None, should_stop: Callable[[], bool] = lambda: False,
) -> list[str]:
    """Every page, continuing after `done` (pages already read).
    on_page(pages so far, total) after each page."""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtPdf import QPdfDocument

    document = QPdfDocument(None)
    if document.load(str(path)) != QPdfDocument.Error.None_:
        raise OcrError("Couldn't open the PDF.")
    total = document.pageCount()
    pages = list(done or [])[:total]
    try:
        with tempfile.TemporaryDirectory(prefix="mia_ocr_") as tmp:
            target = Path(tmp) / "page.png"
            for index in range(len(pages), total):
                if should_stop():
                    break
                size = document.pagePointSize(index)
                pixels = QSize(max(1, int(size.width() * _PDF_DPI / 72)), max(1, int(size.height() * _PDF_DPI / 72)))
                rendered = document.render(index, pixels)
                page = QImage(rendered.size(), QImage.Format.Format_RGB32)
                page.fill(QColor("white"))  # scans rendered with transparency read badly
                painter = QPainter(page)
                painter.drawImage(0, 0, rendered)
                painter.end()
                _prepare_image(page, target)
                pages.append(run_tesseract(exe, target, language))
                if on_page:
                    on_page(pages, total)
    finally:
        document.close()
    return pages


# ---------------------------------------------------------------------------
# Results on disk
# ---------------------------------------------------------------------------


@dataclass
class OcrResult:
    pages: list[str]
    error: str = ""

    @property
    def text(self) -> str:
        return "\n\n".join(self.pages)


def _partial(output: Path) -> Path:
    return output.with_name(output.stem + ".partial.json")


def read_result(output: Path) -> Optional[OcrResult]:
    """The finished result, or None while it isn't done."""
    if not output.exists():
        return None
    try:
        data = json.loads(output.read_text(encoding="utf-8"))
        return OcrResult(pages=list(data.get("pages", [])), error=str(data.get("error", "")))
    except (OSError, ValueError, AttributeError):
        return OcrResult(pages=[], error="The reading result was damaged; try again.")


def _write(path: Path, pages: list[str], error: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps({"pages": pages, "error": error}))


# ---------------------------------------------------------------------------
# The background queue
# ---------------------------------------------------------------------------


@dataclass
class OcrJob:
    key: str  # who asked, e.g. "inbox:<item>/<file>" or "textbook:<id>"
    source: Path
    output: Path
    done_pages: int = 0
    total_pages: int = 0
    cancelled: bool = False


Engine = Callable[[OcrJob, Callable[[list[str], int], None], Callable[[], bool]], list[str]]


class OcrQueue:
    """One document at a time, on one background thread. `engine` is
    replaceable for tests; the default runs Tesseract."""

    def __init__(self, context, engine: Optional[Engine] = None) -> None:
        self.context = context
        self._engine = engine or self._tesseract_engine
        self._jobs: deque[OcrJob] = deque()
        self._current: Optional[OcrJob] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._idle = threading.Event()
        self._idle.set()

    @property
    def available(self) -> bool:
        return available(self.context.config) if self._engine == self._tesseract_engine else True

    # -- asking ---------------------------------------------------------

    def submit(self, key: str, source: Path, output: Path) -> bool:
        """Queue a document. False when OCR isn't available. A key already
        queued or being read isn't added twice."""
        if not self.available:
            return False
        with self._lock:
            if (self._current and self._current.key == key and not self._current.cancelled) or any(j.key == key for j in self._jobs):
                return True
            self._jobs.append(OcrJob(key=key, source=Path(source), output=Path(output)))
            self._idle.clear()
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="mia-ocr", daemon=True)
                self._thread.start()
        return True

    def cancel(self, key: str) -> None:
        with self._lock:
            self._jobs = deque(j for j in self._jobs if j.key != key)
            if self._current and self._current.key == key:
                self._current.cancelled = True

    def is_queued(self, key: str) -> bool:
        with self._lock:
            return bool(self._current and self._current.key == key and not self._current.cancelled) or any(
                j.key == key for j in self._jobs)

    def progress(self, key: str) -> Optional[tuple[int, int]]:
        """(pages read, total pages) for the document being read, (0, 0)
        while waiting its turn, None when it isn't queued."""
        with self._lock:
            if self._current and self._current.key == key:
                return self._current.done_pages, self._current.total_pages
            return (0, 0) if any(j.key == key for j in self._jobs) else None

    def wait(self, timeout: float = 60) -> bool:
        """Block until everything queued is done (tests, shutdown)."""
        return self._idle.wait(timeout)

    # -- the thread -----------------------------------------------------

    def _run(self) -> None:
        while True:
            with self._lock:
                if not self._jobs:
                    self._current = None
                    self._idle.set()
                    return
                job = self._current = self._jobs.popleft()
            self._read(job)

    def _read(self, job: OcrJob) -> None:
        partial = _partial(job.output)

        def on_page(pages: list[str], total: int) -> None:
            job.done_pages, job.total_pages = len(pages), total
            if total > 1 and len(pages) % _SAVE_EVERY == 0:
                _write(partial, pages)

        try:
            pages = self._engine(job, on_page, lambda: job.cancelled)
            if job.cancelled:
                if pages and job.source.exists():  # paused, not deleted: keep the progress
                    _write(partial, pages)
                return
            _write(job.output, pages)
            log.info("OCR read %s (%d page%s).", job.source.name, len(pages), "s" if len(pages) != 1 else "")
        except OcrError as exc:
            _write(job.output, [], str(exc))
        except Exception as exc:  # never kill the thread; tell the owner instead
            log.exception("OCR failed on %s", job.source)
            _write(job.output, [], f"Couldn't read it: {exc}")
        partial.unlink(missing_ok=True)

    def _tesseract_engine(self, job: OcrJob, on_page, should_stop) -> list[str]:
        exe = tesseract_path(self.context.config)
        if exe is None:
            raise OcrError(f"Tesseract isn't installed; {INSTALL_HINT}.")
        language = str(self.context.config.get("ocr.language", "eng") or "eng")
        if job.source.suffix.lower() in IMAGE_SUFFIXES:
            text = ocr_image(exe, job.source, language)
            on_page([text], 1)
            return [text]
        done = read_result(_partial(job.output))
        return ocr_pdf(exe, job.source, language, done.pages if done else None, on_page, should_stop)
