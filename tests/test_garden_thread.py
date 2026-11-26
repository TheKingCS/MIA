"""
tests.test_garden_thread
==========================

The garden conversation check's fixes (2026-11-26): "my last frost is April 20" kept (her own suggested words had kept
nothing), a bare date after her frost ask kept too, undoable, never a frost that happened or a date out of its
season; and "and peppers?" after "when should I start tomatoes?", never after "selling eggs".
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
    for said in ("the last frost was November 20", "my last frost is decent 5", "my last frost is December 5"):
        assert planting_now.keep_frost(context, said) is None, said
    assert planting_now.keep_frost(context, "maybe 5", "last") is None
    ask = planting_now._ASK
    assert her_asks.reply(context, ask, "April 25").startswith("Kept: your last spring frost is April 25")


def test_and_peppers_after_a_planting_question():
    assert follow_through.merged("When should I start tomatoes?", "peppers") == "When should I start peppers?"
    assert follow_through.merged("How much is my truck loan?", "the mortgage") == "How much do I owe on my mortgage?"
    assert follow_through.merged("When should I start selling eggs?", "tomatoes") is None
    assert follow_through.merged("What resistor do I need for an LED on 5 volts?", "on 12 volts") == \
        "What resistor do I need for an LED on 12 volts?"
    assert follow_through.merged("How many 12 volt batteries do I have?", "6 volt") == "How many 6 volt batteries do I have?"


def test_keeping_a_frost_is_undoable(tmp_path, monkeypatch):
    from core import undo_log
    from core.atomic_write import atomic_write_text

    monkeypatch.setattr(planting_now, "say_now", lambda c, t=None: "due")
    path = tmp_path / "config.json"

    class _Saved(_Config):
        """A config written to disk through atomic_write_text, as the real one is."""

        def save(self):
            """Write it."""
            atomic_write_text(path, repr(self.data))

    context = SimpleNamespace(config=_Saved(), undo=undo_log.UndoLog(), profile_id="p1")
    planting_now.keep_frost(context, "my last frost is April 20")
    assert [c.label for c in context.undo.recent("p1")] == ["frost_last"]
