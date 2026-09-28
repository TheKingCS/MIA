"""
The opt-in weekly journal reflection (core/journal_reflection.py): when
it's due, the content-free notice, the reflection itself, and that
asking for it is a private turn.
"""

from datetime import datetime
from types import SimpleNamespace

from core.journal_reflection import journal_reflection_action, reflection_due, reflection_notice, weekly_reflection
from core.private_journal import PrivateJournalEntry

SUNDAY_EVENING = datetime(2026, 9, 27, 19, 0)  # a Sunday


def entry(day, themes=(), mood=""):
    return PrivateJournalEntry(entry_id=str(day), themes=list(themes), mood=mood,
                               created_at=datetime(2026, 9, day, 20, 0).isoformat(timespec="seconds"))


def test_due_on_the_chosen_evening_once():
    assert reflection_due(SUNDAY_EVENING, 6, None)
    assert not reflection_due(SUNDAY_EVENING.replace(hour=9), 6, None)  # not in the morning
    assert not reflection_due(SUNDAY_EVENING, 6, "2026-09-27")  # already done today
    assert not reflection_due(SUNDAY_EVENING, 4, None)  # the owner chose Friday


def test_the_notice_never_carries_journal_content():
    assert reflection_notice(0) is None
    title, message = reflection_notice(3)
    assert message == "You had 3 journal sessions this week. Your reflection is ready: ask me \"how was my week?\""


def test_the_reflection():
    entries = [entry(26, ["the greenhouse", "work"], "hopeful"), entry(23, ["work", "money"], "drained"),
               entry(21, ["work"], "tired"), entry(2, ["old stuff"], "sad")]  # the last one is from weeks ago
    text = weekly_reflection(entries, SUNDAY_EVENING)
    assert text.startswith("This week you journaled 3 times.")
    assert "What came up most: work, " in text and "old stuff" not in text
    assert "You started the week feeling tired and your latest entry sounds hopeful." in text
    assert weekly_reflection([], SUNDAY_EVENING).startswith("You didn't journal this week")


def test_asking_needs_the_journal_unlocked():
    handler = journal_reflection_action().handler
    locked = SimpleNamespace(private_journal=SimpleNamespace(is_set_up=lambda: True, is_unlocked=lambda: False))
    assert "locked" in handler(locked, {})
    assert "set up" in handler(SimpleNamespace(private_journal=None), {})


def test_asking_is_a_private_turn():
    from core.conversation_manager import Conversation
    from core.talk_it_out import pre_turn

    conversation = Conversation(conversation_id="c")
    pre_turn(SimpleNamespace(), conversation, "How was my week?")
    assert conversation.private_turn


def test_the_daily_check_offers_the_notice_once(tmp_path, monkeypatch):
    import core.config_manager as config_module
    from core.application import MIAApplication
    from core.config_manager import ConfigManager

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    config = ConfigManager()
    offered = []
    journal = SimpleNamespace(is_set_up=lambda: True, count_since=lambda iso: 2)
    app = SimpleNamespace(context=SimpleNamespace(config=config, private_journal=journal),
                          _offer=lambda **kw: offered.append(kw))
    MIAApplication._check_journal_reflection(app, SUNDAY_EVENING, "2026-09-27")
    assert offered == []  # off unless the owner opts in
    config.set("journal.weekly_reflection", True)
    MIAApplication._check_journal_reflection(app, SUNDAY_EVENING, "2026-09-27")
    MIAApplication._check_journal_reflection(app, SUNDAY_EVENING, "2026-09-27")
    assert len(offered) == 1 and "2 journal sessions" in offered[0]["message"]
