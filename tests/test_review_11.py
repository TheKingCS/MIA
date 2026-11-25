"""
tests.test_review_11
======================

The eleventh review's findings (2026-11-25), each kept fixed: money that wasn't spent (a quote, a refund, "it") is
never an expense, two amounts in one sentence are the model's, no name is hardcoded, grocery chicken is groceries,
goat feed never counts for the hens, a repair is Maintenance, a utility said without "bill" is the bill tools', and
"yesterday" dates it; the morning briefing never switches on from a sentence about his own morning or a reminder,
and is heard said the other way round; a quote reads "the Smiths'", "Sarah Miller's" and "for the Johnsons", never
"tomorrow" as a customer, two decks as two, and asks which customer when several match; and the D chord's why is
right.
"""

from types import SimpleNamespace

import pytest

from core import assistant_turn, drills, job_quote
from core.morning_briefing import asked


@pytest.fixture()
def spent():
    """What _spent_reply would run, with a flock."""
    ran = []
    context = SimpleNamespace(flock=SimpleNamespace(flocks=["layers"]), assistant_actions=SimpleNamespace(
        execute=lambda c, name, args: ran.append((name, args)) or "ok"))
    return ran, lambda words: assistant_turn._spent_reply(context, words)


def test_money_that_wasnt_spent_is_never_an_expense(spent):
    ran, say = spent
    for words in ("I got a quote for $3,000", "I got a refund for $20", "I got it for $20",
                  "I spent $5 on a coffee and $10 on gas", "paid $120 for the internet"):
        assert say(words) is None, words


def test_what_was_spent_lands_where_it_belongs(spent):
    ran, say = spent
    say("spent $12 on chicken breasts")
    assert ran[-1][1]["category"] == "Groceries"
    say("bought 50 lb of goat feed for $22")
    assert ran[-1][0] == "add_expense" and ran[-1][1]["category"] == "Animals & Feed"
    say("spent $200 on the truck repair")
    assert ran[-1][1]["category"] == "Maintenance"
    say("spent $30 on groceries yesterday")
    assert ran[-1][1]["description"] == "Groceries" and "date" in ran[-1][1]
    assert say("I paid $40 for Mike's birthday present") == "ok"


def test_the_briefing_never_switches_on_by_accident_and_hears_it_either_way():
    for words in ("every morning I give the dog his meds", "Every morning I read the Bible",
                  "I want the morning report from the greenhouse", "remind me every morning to give the dog his meds"):
        assert asked(words) is None, words
    assert asked("tell me the weather every morning") == ("on", 7)
    assert asked("send me the weather every morning at 6") == ("on", 6)


def test_a_quote_reads_its_customer_and_how_many():
    assert job_quote.job_of("write a quote for the Smiths' 12 by 16 deck") == ("Smiths", "12 by 16 deck")
    assert job_quote.job_of("write a quote for Sarah Miller's 12 by 16 deck") == ("Sarah Miller", "12 by 16 deck")
    assert job_quote.job_of("make a quote for a 12 by 16 deck for the Johnsons") == ("Johnsons", "12 by 16 deck")
    assert job_quote.job_of("make a quote for a 12 by 16 deck for tomorrow")[0] == ""


def test_two_decks_are_two_and_several_customers_are_asked(monkeypatch):
    from core import assistant_correction_actions

    made = []
    monkeypatch.setattr(assistant_correction_actions, "_run", lambda c, k, p: made.append(p) or
                        "Added it. (Say “undo that” to take it back.)")
    stock = [SimpleNamespace(name="2x10 x 12 ft", unit_cost=10.0)]
    customers = [SimpleNamespace(name="Sarah Miller", customer_id="c1"), SimpleNamespace(name="Sarah Lee", customer_id="c2")]
    context = SimpleNamespace(materials=SimpleNamespace(all_materials=lambda: stock),
                              business=SimpleNamespace(customers=customers))
    job_quote.reply(context, "write a quote for 2 12 by 16 decks")
    assert made[-1]["title"].startswith("2 × 12 x 16 ft deck")
    assert job_quote.reply(context, "write a quote for Sarah's 12 by 16 deck").startswith("Which customer?")
    assert len(made) == 1


def test_the_d_chords_why_is_right():
    jam = drills.by_id("first_jam")
    all_six = jam.questions[3].choices[0]
    assert "low E isn't in a D chord" in all_six.why and "A strings" not in all_six.why
