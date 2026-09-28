"""
Textbook tutor: document text extraction (core/document_text.py), the
library and its index (core/textbook_manager.py), study and quiz turns
(core/textbook_study.py), the tools, and the Classroom page. A small
real PDF is generated per test with Qt's own PDF writer.
"""

from email.message import EmailMessage
from pathlib import Path

import pytest
from PySide6.QtGui import QPainter, QPdfWriter
from PySide6.QtWidgets import QApplication

import core.classroom_manager as classroom_module
import core.config_manager as config_module
import core.conversation_manager as conversation_module
import core.textbook_manager as textbook_module
from core.app_context import AppContext
from core.assistant_chat import build_chat_request
from core.classroom_manager import ClassroomManager
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.conversation_modes import MODE_INSTRUCTIONS, QUIZ, STUDY
from core.document_text import extract, html_to_text
from core.event_bus import EventBus
from core.talk_it_out import pre_turn
from core.textbook_manager import Chapter, TextbookManager, find_chapters, split_passages, tokenize
from core.textbook_study import NO_BOOKS_NOTICE
from tests.assistant_registry import build_desktop_registry

PAGES = [
    "Contents\nChapter 1 Circuit Breakers ........ 2\nChapter 2 GFCI Outlets ........ 3\nChapter 3 Grounding ........ 4",
    "Chapter 1: Circuit Breakers\nA breaker trips when current exceeds its rating.\nA 15 amp breaker protects 14 gauge wire.",
    "Chapter 2: GFCI Outlets\nA GFCI outlet compares hot and neutral current.\nIt trips at a 5 milliamp imbalance and protects people from shock.\nTest GFCI outlets monthly with the test button.",
    "Chapter 3: Grounding\nThe grounding conductor gives fault current a safe path back to the panel.",
]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def write_pdf(path: Path, pages: list[str], qapp) -> Path:
    writer = QPdfWriter(str(path))
    painter = QPainter(writer)
    for i, page in enumerate(pages):
        if i:
            writer.newPage()
        for n, line in enumerate(page.splitlines()):
            painter.drawText(200, 300 + n * 250, line)
    painter.end()
    return path


@pytest.fixture
def ctx(tmp_path, monkeypatch, qapp):
    for module in (classroom_module, textbook_module, conversation_module):
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    monkeypatch.setattr(textbook_module, "_DEFAULT_ROOT", tmp_path / "textbooks")
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.classroom = ClassroomManager(context)
    context.textbooks = TextbookManager(context)
    context.conversations = ConversationManager(context)
    context.assistant_actions = build_desktop_registry()
    context.tmp = tmp_path
    return context


def add_wiring_book(ctx):
    pdf = write_pdf(ctx.tmp / "Residential_Wiring.pdf", PAGES, None)
    return ctx.textbooks.add_book(pdf, title="Residential Wiring Basics")


# ------------------------------------------------------------------ text extraction


def test_extract_pdf_text_and_email_and_html(ctx):
    pdf = extract(write_pdf(ctx.tmp / "a.pdf", ["Replace the air filter every 25 hours.", "Page two"], None))
    assert pdf.readable and len(pdf.pages) == 2 and "every 25 hours" in pdf.pages[0]

    message = EmailMessage()
    message["Subject"] = "Your Lowe's receipt"
    message["From"] = "Lowe's <receipts@lowes.com>"
    message["Date"] = "Mon, 28 Sep 2026 10:00:00 -0400"
    message.set_content("Thanks for shopping. Total $42.17")
    message.add_attachment(b"%PDF-fake", maintype="application", subtype="pdf", filename="receipt.pdf")
    eml = ctx.tmp / "mail.eml"
    eml.write_bytes(bytes(message))
    parsed = extract(eml)
    assert (parsed.title, parsed.date) == ("Your Lowe's receipt", "2026-09-28")
    assert "Total $42.17" in parsed.text and parsed.attachments[0].filename == "receipt.pdf"

    assert html_to_text("<p>Hi<script>x()</script></p><p>there</p>") == "Hi\nthere"


def test_unreadable_files_say_why(ctx):
    photo = ctx.tmp / "receipt.jpg"
    photo.write_bytes(b"\xff\xd8")
    assert not extract(photo).readable and "OCR" in extract(photo).note
    blank = extract(write_pdf(ctx.tmp / "scan.pdf", [""], None))
    assert not blank.readable and "scan" in blank.note
    odd = ctx.tmp / "x.xyz"
    odd.write_text("?")
    assert not extract(odd).readable


# ------------------------------------------------------------------ chapters, passages, words


def test_find_chapters_skips_the_contents_page():
    chapters = find_chapters(PAGES)
    assert [(c.title, c.page) for c in chapters] == [
        ("Chapter 1: Circuit Breakers", 2), ("Chapter 2: GFCI Outlets", 3), ("Chapter 3: Grounding", 4),
    ]


def test_find_chapters_markdown_and_fallback():
    assert [c.title for c in find_chapters(["# Soil\ntext", "# Water\ntext"])] == ["Soil", "Water"]
    assert find_chapters(["no headings here"]) == [Chapter("Whole book", 1)]


def test_passages_keep_their_page_and_size():
    passages = split_passages(["short page", "x" * 3000], [Chapter("Whole book", 1)], max_chars=900)
    assert passages[0].page == 1 and all(p.page == 2 for p in passages[1:])
    assert max(len(p.text) for p in passages) <= 1350


def test_tokenize():
    assert tokenize("What does the book say about GFCI outlets and batteries?") == ["gfci", "outlet", "battery"]


# ------------------------------------------------------------------ the library


def test_add_search_and_reload(ctx):
    book = add_wiring_book(ctx)
    assert (book.page_count, len(book.chapters)) == (4, 3)
    [top, *_] = ctx.textbooks.search("when does a GFCI trip?")
    assert top.passage.page == 3 and top.chapter_title == "Chapter 2: GFCI Outlets"
    assert ctx.textbooks.search("breaker", chapter=2) == []  # chapter 3 has no breakers
    reloaded = TextbookManager(ctx)
    assert reloaded.get_book(book.book_id).title == "Residential Wiring Basics"
    assert reloaded.search("grounding conductor")[0].passage.page == 4


def test_find_book_and_chapter(ctx):
    book = add_wiring_book(ctx)
    assert ctx.textbooks.find_book("let's study the wiring book").book_id == book.book_id
    assert ctx.textbooks.find_book("something unrelated") is None
    assert ctx.textbooks.find_chapter(book, "quiz me on chapter 2") == 1
    assert ctx.textbooks.find_chapter(book, "the grounding one") == 2


def test_refuses_unsupported_and_scanned(ctx):
    with pytest.raises(ValueError, match="isn't supported"):
        ctx.textbooks.add_book(ctx.tmp / "book.epub")
    with pytest.raises(ValueError, match="scan"):
        ctx.textbooks.add_book(write_pdf(ctx.tmp / "scan.pdf", [""], None))
    assert ctx.textbooks.all_books() == []


def test_make_course_and_remove(ctx):
    book = add_wiring_book(ctx)
    course_id = ctx.textbooks.make_course(book.book_id)
    assert [l.name for l in ctx.classroom.lessons_for_course(course_id)] == [c.title for c in book.chapters]
    assert ctx.textbooks.make_course(book.book_id) == course_id  # not twice
    stored = ctx.textbooks.root / book.filename
    assert stored.exists() and ctx.textbooks.remove_book(book.book_id)
    assert not stored.exists() and ctx.textbooks.all_books() == []


def test_plain_text_book_gets_pages(ctx):
    text = ctx.tmp / "notes.md"
    text.write_text("# Soil\n" + "compost adds nitrogen\n" * 70 + "# Water\ndrip lines save water\n")
    book = ctx.textbooks.add_book(text)
    assert book.title == "Soil" and book.page_count == 2
    assert [c.title for c in book.chapters] == ["Soil", "Water"]


# ------------------------------------------------------------------ study and quiz turns


def study_turn(ctx, conversation, prompt):
    pre_turn(ctx, conversation, prompt)
    ctx.conversations.add_message(conversation.conversation_id, "user", prompt)
    return build_chat_request(ctx, conversation, prompt)


def test_study_turn_uses_the_books_passages(ctx):
    book = add_wiring_book(ctx)
    conversation = ctx.conversations.get_or_create_active_conversation()
    study_turn(ctx, conversation, "Let's study the wiring book")
    assert (conversation.mode, conversation.study_book_id) == (STUDY, book.book_id)
    messages, tools = study_turn(ctx, conversation, "When does a GFCI outlet trip?")
    system = messages[0]["content"]
    assert tools == [] and MODE_INSTRUCTIONS[STUDY] in system
    assert '"Residential Wiring Basics"' in system and "[Page 3]" in system and "5 milliamp" in system


def test_quiz_on_a_chapter_without_matching_words(ctx):
    add_wiring_book(ctx)
    conversation = ctx.conversations.get_or_create_active_conversation()
    messages, _ = study_turn(ctx, conversation, "Quiz me on chapter 3")
    assert (conversation.mode, conversation.study_chapter) == (QUIZ, 2)
    system = messages[0]["content"]
    assert MODE_INSTRUCTIONS[QUIZ] in system and "Chapter 3: Grounding" in system and "[Page 4]" in system
    assert "[Page 3]" not in system  # stays in the chapter


def test_study_without_books_says_so(ctx):
    conversation = ctx.conversations.get_or_create_active_conversation()
    assert pre_turn(ctx, conversation, "Let's study").notice == NO_BOOKS_NOTICE


# ------------------------------------------------------------------ tools and the page


def test_tools(ctx):
    say = lambda name, **a: ctx.assistant_actions.execute(ctx, name, a)  # noqa: E731
    assert "don't have any textbooks" in say("list_textbooks")
    add_wiring_book(ctx)
    assert say("list_textbooks").startswith("You have 1 textbook: Residential Wiring Basics (4 pages, 3 chapters).")
    reply = say("search_textbook", query="GFCI test button")
    assert reply.startswith("Residential Wiring Basics, page 3 (Chapter 2: GFCI Outlets):")
    assert say("search_textbook", query="quantum chromodynamics") == "I couldn't find anything about quantum chromodynamics in your textbooks."
    assert say("make_textbook_course").startswith("Made a Classroom course for Residential Wiring Basics: 3 lessons")
    assert say("make_textbook_course") == "Residential Wiring Basics already has a course in Classroom."


def test_textbooks_page(ctx):
    from gui.textbooks_panel import TextbooksPanel, format_textbook_row

    book = add_wiring_book(ctx)
    panel = TextbooksPanel(ctx)
    assert panel._list.count() == 1
    panel._list.setCurrentRow(0)
    assert "Chapter 2: GFCI Outlets (page 3)" in panel._details.text()
    assert format_textbook_row(book) == "Residential Wiring Basics  —  4 pages, 3 chapters"


def test_leaving_study_or_quiz_mode():
    from core.conversation_modes import COMPANION, detect_mode_change

    for phrase in ("I'm done studying", "stop the quiz", "done with the quiz", "end the study session"):
        assert detect_mode_change(phrase).mode == COMPANION, phrase
    assert detect_mode_change("I stopped studying yesterday").mode is None
