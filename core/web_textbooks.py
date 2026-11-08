"""
core.web_textbooks
====================

The Classroom's textbooks on the web (DEC-0125: the textbook tutor's library
was on the desktop and by voice only). Three parts:

- `section(context)`: each book for the Classroom page: title, pages,
  chapters (with the page each starts on), whether a scan is still being read
  or why reading failed, and the Classroom course made from it.
- `search(context, query, book_id)`: where the books talk about something:
  the best passages with their book, page and chapter (the same keyword
  search the tutor answers from: TextbookManager.search).
- Actions, so the page and voice agree: `textbook.course` (a course from
  the book, one lesson per chapter; make_textbook_course), and
  `textbook.remove` (the book, its index and its scan's reading deleted
  for good: the approval says so; remove_textbook).

Adding a book is an upload (server/app.py `/api/classroom/textbook`, a PDF
or a text file), read and indexed by TextbookManager.add_book.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

SNIPPET_CHARS = 280


def section(context) -> dict:
    """The textbooks for the Classroom page: {"available", "books": [...]}; each book with its pages, chapters, reading
    state and course."""
    library = getattr(context, "textbooks", None)
    if library is None:
        return {"available": False, "books": []}
    classroom = getattr(context, "classroom", None)
    books = []
    for b in library.all_books():
        course = classroom.get_course(b.course_id) if classroom is not None and b.course_id else None
        books.append({"id": b.book_id, "title": b.title, "pages": b.page_count,
                      "chapters": [{"title": c.title, "page": c.page} for c in b.chapters],
                      "reading": b.reading, "error": b.reading_error,
                      "course": course.name if course is not None else "", "added": (b.added_at or "")[:10]})
    return {"available": True, "books": books}


def snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    """Pure logic. A passage's words on one line, cut at `limit` characters with an ellipsis."""
    words = " ".join((text or "").split())
    return words[:limit] + ("…" if len(words) > limit else "")


def search(context, query: str, book_id: str = "", limit: int = 6) -> dict:
    """Where the books talk about `query` (all of them, or the one asked): each hit's book, page, chapter and a snippet,
    best first. {"hits": []} for no words or no books."""
    library = getattr(context, "textbooks", None)
    query = (query or "").strip()
    if library is None or not query:
        return {"query": query, "hits": []}
    hits = library.search(query, book_id=book_id or None, limit=limit)
    return {"query": query, "hits": [{"book_id": h.book.book_id, "book": h.book.title, "page": h.passage.page,
                                      "chapter": "" if h.chapter_title == "Whole book" else h.chapter_title,
                                      "text": snippet(h.passage.text)} for h in hits]}


def _book(context, params):
    """The book the params name; ActionError when it isn't in the library."""
    book = _need(context, "textbooks").get_book(str(params.get("book_id") or ""))
    if book is None:
        raise ActionError("That book isn't in your library.")
    return book


def _describe_course(context, params) -> str:
    """The approval sentence for textbook.course; a book still being read, or already with a course, is refused."""
    book = _book(context, params)
    classroom = _need(context, "classroom")
    if book.reading:
        raise ActionError(f"{book.title} is still being read. Its chapters come when that's done.")
    if book.course_id and classroom.get_course(book.course_id) is not None:
        raise ActionError(f"{book.title} already has a course in Classroom.")
    n = len(book.chapters)
    return f"Make a Classroom course from {book.title}: {n} lesson{'s' if n != 1 else ''}, one per chapter"


def _course(context, params) -> str:
    """Does textbook.course (TextbookManager.make_course: under the Textbooks subject, made once)."""
    book = _book(context, params)
    context.textbooks.make_course(book.book_id)
    return f"Made a course for {book.title} in Classroom."


def _describe_remove(context, params) -> str:
    """The approval sentence for textbook.remove: it says the file goes for good (undo can't bring a deleted book
    back)."""
    return f"Remove {_book(context, params).title} and its file for good (its Classroom course stays)"


def _remove(context, params) -> str:
    """Does textbook.remove."""
    book = _book(context, params)
    context.textbooks.remove_book(book.book_id)
    return f"Removed {book.title}."


TEXTBOOK_ACTIONS = {a.kind: a for a in (
    ActionType("textbook.course", "Make A Course", {"book_id": "the book"}, _describe_course, _course, child_ok=True),
    ActionType("textbook.remove", "Remove", {"book_id": "the book"}, _describe_remove, _remove),
)}
ACTION_TYPES.update(TEXTBOOK_ACTIONS)
