"""
core.textbook_study
======================

The study and quiz conversation modes of the textbook tutor
(2026-09-28): which book and chapter a conversation is on, and the
passages MIA answers from each turn. The library itself is
core/textbook_manager.py; the tone lines are in
core/conversation_modes.py (STUDY, QUIZ).

Same principle as the rest of MIA's personal modes: the facts come from
code, the model only phrases them. Every turn retrieves the book's
best-matching passages (with page numbers) for what the user just said
and hands them to the model with "use only these", so the tutor
teaches from the owner's book, not from whatever the small model half
remembers, and can say "page 42".
"""

from __future__ import annotations

import re
from typing import Optional

from core.conversation_modes import QUIZ, STUDY

_CHAPTER_WORDS = re.compile(r"\b(?:chapter|unit|lesson|part)\s+(?:[0-9]{1,3}|[ivxlc]{1,7})\b", re.IGNORECASE)
_PASSAGE_CHARS = 700
_PASSAGES = 4

NO_BOOKS_NOTICE = (
    "You don't have any textbooks in MIA yet. Add one in Classroom under Textbooks (a PDF or text file), "
    "then say \"let's study\" and the book's name."
)


def update_study_target(context, conversation, prompt: str) -> Optional[str]:
    """Called by core/talk_it_out.pre_turn() for study and quiz turns:
    pick up a book or chapter the user named. Returns a notice to say
    first when there's no book to study from, else None."""
    library = getattr(context, "textbooks", None)
    books = library.all_books() if library is not None else []
    if not books:
        return NO_BOOKS_NOTICE
    named = library.find_book(prompt)
    if named is not None and named.book_id != conversation.study_book_id:
        conversation.study_book_id = named.book_id
        conversation.study_chapter = None
    if conversation.study_book_id is None or library.get_book(conversation.study_book_id) is None:
        conversation.study_book_id = books[-1].book_id if len(books) == 1 or named is None else named.book_id
        conversation.study_chapter = None
    book = library.get_book(conversation.study_book_id)
    if _CHAPTER_WORDS.search(prompt):
        chapter = library.find_chapter(book, prompt)
        if chapter is not None:
            conversation.study_chapter = chapter
    return None


def study_block(context, conversation, prompt: str) -> str:
    """The passages for this turn, as a system-prompt block. Empty when
    there's no book (the notice already told the user)."""
    library = getattr(context, "textbooks", None)
    book = library.get_book(conversation.study_book_id) if library and conversation.study_book_id else None
    if book is None:
        return ""
    chapter = conversation.study_chapter
    query = prompt
    if conversation.mode == QUIZ:
        # An answer to MIA's question rarely repeats its keywords: search
        # with the question she asked, too.
        last_mia = next((m.content for m in reversed(conversation.messages[:-1]) if m.role == "assistant"), "")
        query = f"{last_mia} {prompt}"
    hits = library.search(query, book_id=book.book_id, chapter=chapter, limit=_PASSAGES)
    passages = [h.passage for h in hits]
    if len(passages) < 2:
        # "Quiz me on chapter 3" shares no words with the text: use the
        # chapter's (or book's) opening passages.
        pool = [p for p in library.passages(book.book_id) if chapter is None or p.chapter == chapter]
        passages += [p for p in pool[:_PASSAGES] if p not in passages][: _PASSAGES - len(passages)]
    where = f', {book.chapters[chapter].title}' if chapter is not None and chapter < len(book.chapters) else ""
    lines = [f'Passages from the user\'s textbook "{book.title}"{where}:']
    for passage in passages:
        text = passage.text if len(passage.text) <= _PASSAGE_CHARS else passage.text[:_PASSAGE_CHARS] + "…"
        lines.append(f"[Page {passage.page}] {text}")
    if not passages:
        lines.append("(No passages matched. Say the book doesn't seem to cover this.)")
    return "\n".join(lines)


def is_study_mode(mode: str) -> bool:
    return mode in (STUDY, QUIZ)
