"""
core.assistant_textbook_actions
==================================

Assistant tools for the textbook tutor (core/textbook_manager.py):
what books MIA has, a quick "where does the book talk about X" lookup,
and making a Classroom course from a book. Studying and quizzing
themselves are conversation modes (core/textbook_study.py: "let's study
the wiring book", "quiz me on chapter 3"), not tools.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry

_S = {"type": "string"}


def _library(context: AppContext):
    return getattr(context, "textbooks", None)


def _action_list_textbooks(context: AppContext, arguments: dict) -> str:
    library = _library(context)
    books = library.all_books() if library is not None else []
    if not books:
        return "You don't have any textbooks yet. Add one in Classroom under Textbooks, a PDF or a text file."
    parts = [f"{b.title} ({b.page_count} pages, {len(b.chapters)} chapter{'s' if len(b.chapters) != 1 else ''})" for b in books]
    return f"You have {len(books)} textbook{'s' if len(books) != 1 else ''}: " + "; ".join(parts) + \
        ". Say \"let's study\" and a book's name, or \"quiz me on\" a chapter."


def _action_search_textbook(context: AppContext, arguments: dict) -> str:
    library = _library(context)
    if library is None or not library.all_books():
        return "You don't have any textbooks yet. Add one in Classroom under Textbooks."
    query = str(arguments.get("query") or "").strip()
    if not query:
        return "What should I look up in your books?"
    book_words = str(arguments.get("book") or "").strip()
    book = library.find_book(book_words) if book_words else None
    hits = library.search(query, book_id=book.book_id if book else None, limit=2)
    if not hits:
        where = f" in {book.title}" if book else " in your textbooks"
        return f"I couldn't find anything about {query}{where}."
    top = hits[0]
    snippet = " ".join(top.passage.text.split())
    snippet = snippet[:280] + ("…" if len(snippet) > 280 else "")
    reply = f"{top.book.title}, page {top.passage.page}"
    if top.chapter_title and top.chapter_title != "Whole book":
        reply += f" ({top.chapter_title})"
    reply += f": \"{snippet}\""
    if len(hits) > 1:
        reply += f" It also comes up on page {hits[1].passage.page}" + (
            f" of {hits[1].book.title}." if hits[1].book.book_id != top.book.book_id else "."
        )
    return reply


def _action_make_textbook_course(context: AppContext, arguments: dict) -> str:
    library = _library(context)
    if library is None or not library.all_books():
        return "You don't have any textbooks yet."
    words = str(arguments.get("book") or "").strip()
    books = library.all_books()
    book = library.find_book(words) if words else (books[0] if len(books) == 1 else None)
    if book is None:
        return "Which book? " + "; ".join(b.title for b in books) + "."
    if getattr(context, "classroom", None) is None:
        return "Classroom isn't available right now."
    already = bool(book.course_id)
    library.make_course(book.book_id)
    if already:
        return f"{book.title} already has a course in Classroom."
    return f"Made a Classroom course for {book.title}: {len(book.chapters)} lesson{'s' if len(book.chapters) != 1 else ''}, one per chapter."


def register_textbook_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="list_textbooks", domain="textbooks",
        description="List the textbooks the user has added to MIA.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_list_textbooks,
        trigger_phrases=("my textbooks", "what textbooks", "which textbooks", "what books do i have"),
    ))
    registry.register(AssistantAction(
        name="search_textbook", domain="textbooks",
        description="Find where the user's textbooks talk about something, with the page. For a quick lookup, not a lesson.",
        parameters={"type": "object", "properties": {
            "query": {**_S, "description": "What to look up, e.g. 'GFCI outlets'."},
            "book": {**_S, "description": "Which book, if the user said."},
        }, "required": ["query"]},
        handler=_action_search_textbook,
        trigger_phrases=("in my textbook", "in the textbook", "in my book", "what page", "which page",
                         "book say", "textbook say", "textbook talk", "book talk about", "look it up in"),
    ))
    registry.register(AssistantAction(
        name="make_textbook_course", domain="textbooks",
        description="Make a Classroom course from one of the user's textbooks, one lesson per chapter.",
        parameters={"type": "object", "properties": {"book": {**_S, "description": "Which book."}}, "required": []},
        handler=_action_make_textbook_course,
        trigger_phrases=("course from", "course out of", "make a course", "turn my textbook", "turn the book"),
    ))
