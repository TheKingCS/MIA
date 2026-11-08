"""
tests.test_response_style
===========================

Learning how the person likes MIA to answer (core/response_style.py, DEC-0138): a recorded A/B pick moves the
preferred value; confidence rises as picks agree; the next experiment targets the least-settled dimension; the style
instruction only names dimensions that have a pick; and it all persists (sealed, DEC-0126).
"""

import pytest

from core.at_rest import is_sealed
from core.response_style import DEFAULTS, DIMENSIONS, StyleBook


@pytest.fixture
def book(tmp_path):
    """An empty answer-style book in a temporary folder."""
    return StyleBook(data_dir=tmp_path)


def test_with_no_picks_she_uses_the_defaults_and_her_normal_style(book):
    assert book.profile() == DEFAULTS
    assert book.style_instruction() == "Answer in your normal style."
    assert book.confidence("length") == 0.0


def test_a_pick_moves_the_preferred_value_and_persists(tmp_path):
    book = StyleBook(data_dir=tmp_path)
    book.record_pick("length", chosen="brief", rejected="detailed")
    assert book.preferred("length") == "brief"
    # a fresh book on the same folder sees it (and it's sealed on disk)
    again = StyleBook(data_dir=tmp_path)
    assert again.preferred("length") == "brief"
    on_disk = (tmp_path / "response_styles.json").read_text(encoding="utf-8")
    assert is_sealed(on_disk) and "brief" not in on_disk


def test_confidence_rises_as_picks_agree_and_falls_when_split(book):
    book.record_pick("tone", "direct", "warm")
    book.record_pick("tone", "direct", "neutral")
    assert book.preferred("tone") == "direct" and book.confidence("tone") == 1.0
    book.record_pick("tone", "warm", "direct")  # now 2 direct, 1 warm
    assert book.preferred("tone") == "direct" and 0 < book.confidence("tone") < 1


def test_the_style_instruction_only_names_dimensions_with_a_pick(book):
    book.record_pick("length", "brief", "standard")
    book.record_pick("lead", "answer_first", "context_first")
    instruction = book.style_instruction()
    assert "short" in instruction and "lead with the answer" in instruction
    assert "tone" not in instruction and "bullet" not in instruction  # untouched dimensions aren't claimed


def test_the_next_experiment_targets_the_least_settled_dimension(book):
    # make three dimensions settled; the fourth (format) has no picks, so it's next
    for _ in range(2):
        book.record_pick("length", "brief", "standard")
        book.record_pick("tone", "direct", "warm")
        book.record_pick("lead", "answer_first", "context_first")
    exp = book.next_experiment()
    assert exp["dimension"] == "format"
    assert exp["a"] in DIMENSIONS["format"] and exp["b"] in DIMENSIONS["format"] and exp["a"] != exp["b"]


def test_a_bad_dimension_or_value_is_refused(book):
    with pytest.raises(ValueError):
        book.record_pick("speed", "fast", "slow")
    with pytest.raises(ValueError):
        book.record_pick("length", "epic", "brief")


def test_style_for_is_empty_until_there_are_picks_then_speaks(tmp_path):
    """The phrasing hook adds nothing until MIA has learned a preference, so the default turn is unchanged (DEC-0138)."""
    from types import SimpleNamespace

    from core.response_style import StyleBook, style_for

    book = StyleBook(data_dir=tmp_path)
    assert style_for(SimpleNamespace()) == ""  # no store on the context
    assert style_for(SimpleNamespace(response_style=book)) == ""  # store, but no picks yet
    book.record_pick("length", "brief", "standard")
    assert "short" in style_for(SimpleNamespace(response_style=book))
