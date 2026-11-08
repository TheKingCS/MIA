"""The Classroom's textbooks on the web (core/web_textbooks.py, DEC-0125): each book with its chapters on the
Classroom page, a search inside them, a course made from one and a book removed, as actions the voice tools agree
with."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.textbook_manager as textbook_module
from core import actions
from core.actions import ActionCenter, ActionError
from core.classroom_manager import ClassroomManager, screen
from core.textbook_manager import TextbookManager
from core.web_textbooks import search, section, snippet

BOOK = """# Welding Fundamentals

Chapter 1: Safety
Wear a helmet with the right shade. Keep a fire extinguisher close.

Chapter 2: Gas Metal Arc Welding
Hold the gun at a 10 to 15 degree push angle. Too steep an angle traps gas and leaves porosity in the bead.
"""


@pytest.fixture
def shop(tmp_path, monkeypatch):
    """A stand-in person with Classroom, a textbook library holding one welding book, and an action center."""
    monkeypatch.setattr(textbook_module, "_DEFAULT_ROOT", tmp_path / "books")
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    ctx = SimpleNamespace(config=None, undo=None, events=None, actions=ActionCenter(), skills=None)
    ctx.classroom = ClassroomManager(ctx, data_dir=tmp_path / "class")
    ctx.textbooks = TextbookManager(ctx, data_dir=tmp_path / "lib")
    source = tmp_path / "welding.txt"
    source.write_text(BOOK, encoding="utf-8")
    ctx.book = ctx.textbooks.add_book(source)
    return ctx


def act(ctx, kind, **params):
    """Proposes an action as the person and approves it; returns both."""
    proposal = ctx.actions.propose(ctx, kind, params, proposed_by="person")
    return proposal, ctx.actions.approve(ctx, proposal.proposal_id)


def test_a_book_is_listed_searched_made_a_course_and_removed(shop):
    from core.assistant_textbook_actions import _action_remove_textbook

    assert section(SimpleNamespace(textbooks=None)) == {"available": False, "books": []}
    [book] = screen(shop)["textbooks"]["books"]
    assert book["title"] == "Welding Fundamentals" and book["chapters"] and not book["reading"]
    found = search(shop, "porosity")
    assert found["hits"][0]["book"] == "Welding Fundamentals" and "porosity" in found["hits"][0]["text"]
    assert search(shop, "  ")["hits"] == [] and snippet("a  b\nc", 3) == "a b…"
    proposal, done = act(shop, "textbook.course", book_id=shop.book.book_id)
    assert proposal.summary.startswith("Make a Classroom course from Welding Fundamentals:")
    assert screen(shop)["textbooks"]["books"][0]["course"] == "Welding Fundamentals"
    with pytest.raises(ActionError, match="already has a course"):
        shop.actions.propose(shop, "textbook.course", {"book_id": shop.book.book_id})
    assert act(shop, "textbook.remove", book_id=shop.book.book_id)[0].summary.endswith("for good (its Classroom course stays)")
    assert screen(shop)["textbooks"]["books"] == [] and screen(shop)["subjects"][0]["name"] == "Textbooks"
    assert _action_remove_textbook(shop, {"book": "welding"}) == "Which book? Say its name."
