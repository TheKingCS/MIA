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
