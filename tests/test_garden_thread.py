"""
tests.test_garden_thread
==========================

The garden conversation check's fixes (2026-11-26): "my last frost is April 20" kept (her own suggested words had kept
nothing), a bare date after her frost ask kept too, and "and peppers?" after "when should I start tomatoes?".
"""

from types import SimpleNamespace

from core import follow_through, her_asks, planting_now


class _Config:
    """A config that keeps what's set."""

    def __init__(self):
        """Empty."""
        self.data = {}

    def get(self, key, default=None):
        """A setting."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Keep a setting."""
        self.data[key] = value

    def save(self):
        """Nothing to write."""


def test_his_frost_dates_are_kept(monkeypatch):
    monkeypatch.setattr(planting_now, "say_now", lambda c, t=None: "due")
    context = SimpleNamespace(config=_Config())
    assert planting_now.keep_frost(context, "my last frost is April 20") == \
        "Kept: your last spring frost is April 20. due"
    assert context.config.data["garden.last_frost"] == "04-20"
    assert planting_now.keep_frost(context, "our first fall frost is around Oct 15th").startswith(
        "Kept: your first fall frost is October 15")
    assert context.config.data["garden.first_frost"] == "10-15"
    assert planting_now.keep_frost(context, "my last frost was a disaster") is None
    ask = planting_now._ASK
    assert her_asks.reply(context, ask, "April 25").startswith("Kept: your last spring frost is April 25")


def test_and_peppers_after_a_planting_question():
    assert follow_through.merged("When should I start tomatoes?", "peppers") == "When should I start peppers?"
    assert follow_through.merged("How much is my truck loan?", "the mortgage") == "How much do I owe on my mortgage?"
