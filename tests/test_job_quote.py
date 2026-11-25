"""
tests.test_job_quote
======================

A quote from a job's words (core/job_quote.py; brainstorm round 14): "write a quote for Sarah's 12 by 16 deck" reads
the customer and the structure with its size, works the materials out with the calculators, prices what the workshop
has prices for (never guessing the rest), and drafts the quote (quote.add) for the customer he has, the known
materials as its extras, labor left for his hours; a quote that couldn't be made is said as such; a job with no
structure and size is make_quote's.
"""

from types import SimpleNamespace

import pytest

from core import job_quote


def test_the_customer_and_the_job_are_read_from_his_words():
    assert job_quote.job_of("write a quote for Sarah's 12 by 16 deck") == ("Sarah", "12 by 16 deck")
    assert job_quote.job_of("make a quote for a 12 by 16 deck for Sarah") == ("Sarah", "12 by 16 deck")
    assert job_quote.job_of("draft an estimate for a 200 foot fence for Tom") == ("Tom", "200 foot fence")
    assert job_quote.job_of("write a quote for the 10 by 12 shed") == ("", "the 10 by 12 shed")
    assert job_quote.job_of("did Sarah accept the deck quote?") is None


@pytest.fixture()
def shop(monkeypatch):
    """A workshop with two priced materials, a customer named Sarah, and quote.add recorded instead of run."""
    from core import assistant_correction_actions

    made = []
    monkeypatch.setattr(assistant_correction_actions, "_run", lambda context, kind, params: made.append(params) or
                        "Added the quote 12 x 16 ft deck frame. (Say “undo that” to take it back.)")
    stock = [SimpleNamespace(name="2x10 x 12 ft", unit_cost=18.5), SimpleNamespace(name="2x10 joist hangers",
                                                                                  unit_cost=1.25)]
    context = SimpleNamespace(materials=SimpleNamespace(all_materials=lambda: stock),
                              business=SimpleNamespace(customers=[SimpleNamespace(name="Sarah", customer_id="c1")]))
    return made, context


def test_the_draft_is_priced_from_the_workshop_for_the_customer(shop):
    made, context = shop
    said = job_quote.reply(context, "write a quote for Sarah's 12 by 16 deck")
    [params] = made
    assert params["customer_id"] == "c1" and params["extras"] > 0
    assert "Labor not included" in params["notes"] and "Not priced yet:" in params["notes"]
    assert "the materials I have prices for come to" in said and "Labor isn't in it" in said


def test_a_customer_he_doesnt_have_is_said_and_a_job_without_a_size_is_not_this(shop):
    made, context = shop
    said = job_quote.reply(context, "make a quote for a 12 by 16 deck for Tom")
    assert "customer_id" not in made[-1] and "I don't have Tom as a customer yet" in said
    assert job_quote.reply(context, "make a quote for Sarah's cutting board") is None


def test_a_quote_that_couldnt_be_made_says_why_and_nothing_else(monkeypatch):
    from core import assistant_correction_actions

    monkeypatch.setattr(assistant_correction_actions, "_run", lambda c, k, p: "That isn't available on this MIA.")
    context = SimpleNamespace(materials=None, business=None)
    assert job_quote.reply(context, "write a quote for the 10 by 12 shed") == "That isn't available on this MIA."
