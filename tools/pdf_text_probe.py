"""Temporary diagnostic (2026-10-05, Windows CI): writes the textbook
test's PDF with Qt and prints what core.document_text extracts, so the
Windows chapter-detection difference can be seen. Remove once fixed."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtGui import QPainter, QPdfWriter
from PySide6.QtWidgets import QApplication

from core.document_text import pdf_pages
from core.textbook_manager import find_chapters

PAGES = [
    "Contents\nChapter 1 Circuit Breakers ........ 2\nChapter 2 GFCI Outlets ........ 3\nChapter 3 Grounding ........ 4",
    "Chapter 1: Circuit Breakers\nA breaker trips when current exceeds its rating.\nA 15 amp breaker protects 14 gauge wire.",
    "Chapter 2: GFCI Outlets\nA GFCI outlet compares hot and neutral current.\nIt trips at a 5 milliamp imbalance and protects people from shock.\nTest GFCI outlets monthly with the test button.",
    "Chapter 3: Grounding\nThe grounding conductor gives fault current a safe path back to the panel.",
]
app = QApplication.instance() or QApplication([])
path = Path(tempfile.mkdtemp()) / "probe.pdf"
writer = QPdfWriter(str(path))
painter = QPainter(writer)
for i, page in enumerate(PAGES):
    if i:
        writer.newPage()
    for n, line in enumerate(page.splitlines()):
        painter.drawText(200, 300 + n * 250, line)
painter.end()
pages, _title = pdf_pages(path)
for number, text in enumerate(pages, start=1):
    print(f"--- page {number}: {text!r}")
print("chapters:", [(c.title, c.page) for c in find_chapters(pages)])
