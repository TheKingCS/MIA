"""
tests.test_direction
=======================

The standing directions MIA holds and encourages (core/direction.py, DEC-0141): a direction is set, persisted (sealed,
DEC-0126), and turns up in the context block she carries every turn — framed to lean her suggestions that way, never
to preach; turning one off removes it.
"""

import pytest

from core.at_rest import is_sealed
from core.direction import DirectionBook


@pytest.fixture
def book(tmp_path):
    """An empty directions book in a temporary folder."""
    return DirectionBook(data_dir=tmp_path)


def test_a_direction_is_set_persisted_and_sealed(tmp_path):
    book = DirectionBook(data_dir=tmp_path)
    d = book.add("From consumer to producer", "I make and restore before I buy; I grow my own food.",
                 encourage="offer the make/restore/upcycle angle; the from-scratch natural version")
    assert [x.title for x in book.active()] == ["From consumer to producer"]
    again = DirectionBook(data_dir=tmp_path)
    assert again.get(d.direction_id).statement.startswith("I make and restore")
    on_disk = (tmp_path / "directions.json").read_text(encoding="utf-8")
    assert is_sealed(on_disk) and "producer" not in on_disk


def test_the_context_block_carries_the_direction_and_how_to_encourage_it(book):
    book.add("From consumer to producer", "Make, don't buy.", encourage="suggest making or restoring first")
    block = book.context_block()
    assert "From consumer to producer" in block and "Make, don't buy." in block
    assert "suggest making or restoring first" in block
    assert "never preachy" in block or "never" in block  # framed not to preach


def test_an_inactive_direction_drops_out_of_the_context(book):
    d = book.add("Produce your own food", "Grow and cook from scratch.")
    assert book.context_block()
    book.set_active(d.direction_id, False)
    assert book.active() == [] and book.context_block() == ""
    with pytest.raises(ValueError):
        book.set_active("nope", True)


def test_no_directions_means_an_empty_block(book):
    assert book.context_block() == ""


def test_the_nudge_is_occasional_varied_and_remembered(tmp_path):
    """A nudge fires at most every few days (DEC-0141), varies by the roll, and the last-nudged date persists."""
    book = DirectionBook(data_dir=tmp_path)
    book.add("Produce", "Make things.", nudges=["Make a thing", "Grow a thing"])
    assert book.due_for_nudge("2026-01-10")  # never nudged -> due
    assert book.a_nudge(0.1) in ("Make a thing", "Grow a thing")
    assert book.a_nudge(0.9) in ("Make a thing", "Grow a thing")
    book.mark_nudged("2026-01-10")
    assert not book.due_for_nudge("2026-01-11")  # too soon
    assert book.due_for_nudge("2026-01-14")  # a few days later -> due again
    assert DirectionBook(data_dir=tmp_path).last_nudge == "2026-01-10"  # persists


def test_a_direction_without_nudges_is_never_due(tmp_path):
    book = DirectionBook(data_dir=tmp_path)
    book.add("Just a value", "no nudges here")
    assert not book.due_for_nudge("2026-01-10") and book.a_nudge(0.5) == ""
