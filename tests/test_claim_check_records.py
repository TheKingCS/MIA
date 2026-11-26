"""
tests.test_claim_check_records
================================

A claim of a change to any of his records is caught (core/claim_check._RECORD, the conversation check 2026-11-26:
"I've added the lumber cost to your Garage Rewire project" with nothing done), and a plain answer isn't.
"""

from core import claim_check


def test_a_project_or_expense_claim_is_caught():
    said = "I've added the lumber cost to your Garage Rewire project. The total comes out to $1,043."
    assert claim_check.claims_done(said, True)
    assert claim_check.claims_done("I've logged the $40 expense for you.", False)
    assert not claim_check.claims_done("A 10 by 12 shed's lumber costs about what your prices say.", True)
