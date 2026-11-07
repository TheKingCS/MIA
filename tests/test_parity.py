"""
tests.test_parity
===================

Full use both ways on every device (DEC-0125, core/parity.py): every app can
be used by voice, on the PC, on the phone and on the glasses, or the gap is
decided in work/parity.json; parity can only grow, and docs/PARITY.md is
current.
"""

import pytest

from core import parity


@pytest.fixture(scope="module")
def rows():
    """The real matrix, from her tools as the PC registers them."""
    return parity.matrix(parity.desktop_registry())


def test_every_gap_has_a_decision_to_build_or_not(rows):
    """A new app or way that can't be used needs a line in work/parity.json."""
    decisions = parity.load_decisions()
    undecided = [g for g in parity.gaps(rows) if g not in decisions]
    assert not undecided, f"decide these in work/parity.json (todo or none, with why): {undecided}"


def test_a_decision_for_a_closed_gap_is_removed(rows):
    """Once a gap is built, its line goes, so the file stays the true list."""
    stale = sorted(set(parity.load_decisions()) - set(parity.gaps(rows)))
    assert not stale, f"these are built now; remove them from work/parity.json: {stale}"


def test_each_decision_says_todo_or_none_and_why():
    """Every decision is to build or deliberately not, with a reason."""
    for gap, decision in parity.load_decisions().items():
        assert decision.get("status") in ("todo", "none"), gap
        assert decision.get("why"), gap


def test_gaps_lists_each_app_and_way_that_cannot_be_used():
    """Pure logic: the gap names are app:way."""
    rows = [{"id": "a", "voice": True, "pc": True, "phone": False, "glasses": False}]
    assert parity.gaps(rows) == ["a:phone", "a:glasses"]


def test_the_parity_report_is_current(rows):
    """docs/PARITY.md matches the code; run python -m core.parity after a change."""
    assert parity.REPORT.read_text(encoding="utf-8") == parity.render(rows, parity.load_decisions())
