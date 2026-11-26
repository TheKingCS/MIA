"""
tests.test_learned_week
=========================

What she learned this week (core/learned_week.py, 2026-11-25): the memories she kept, the skills he taught her and
how many of her changes he corrected, in words on "what did you learn this week?" and as numbers only in the
self-report.
"""

from datetime import datetime
from types import SimpleNamespace

from core import assistant_turn, learned_week

NOW = datetime(2026, 11, 29, 9)


def _context():
    memories = SimpleNamespace(all_memories=lambda: [SimpleNamespace(text="Likes his coffee black", created_at="2026-11-27T08:00:00"),
                                                     SimpleNamespace(text="Old one", created_at="2026-10-01T08:00:00")],
                               corrections=lambda days: [{"at": "2026-11-28"}])
    book = SimpleNamespace(skills=[SimpleNamespace(name="Logging the eggs", created_at="2026-11-26T10:00:00")])
    return SimpleNamespace(user_memories=memories, taught_skills=book)


def test_the_week_says_memories_skills_and_corrections(monkeypatch):
    from core import corrections

    monkeypatch.setattr(corrections, "summary", lambda c, days=30, now=None: {"money": {"changes": 9, "corrected": 2},
                                                                              "kitchen": {"changes": 3, "corrected": 0}})
    said = learned_week.say(_context(), NOW)
    assert "I kept 1 thing about you: Likes his coffee black." in said and "Old one" not in said
    assert "You taught me Logging the eggs." in said
    assert "You corrected 2 of the 12 changes I made (2 in money)." in said
    assert "You fixed 1 thing I'd remembered wrong." in said
    counted = learned_week.counts(_context(), NOW)
    assert counted == "From you this week: 1 memory kept, 1 skill taught, 2 of my 12 changes corrected."
    assert "coffee" not in counted


def test_a_quiet_week_says_so(monkeypatch):
    from core import corrections

    monkeypatch.setattr(corrections, "summary", lambda c, days=30, now=None: {})
    assert learned_week.say(SimpleNamespace(), NOW).startswith("A quiet week")
    assert learned_week.counts(SimpleNamespace(), NOW) == ""


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(learned_week, "say", lambda c, n=None: "the week")
    for words in ("What did you learn this week?", "what have you learned from me this week",
                  "what've you learned this week"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the week", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what have you learned about me") != "the week"
