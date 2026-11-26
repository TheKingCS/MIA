"""
tests.test_reminder_part_of_day
=================================

"Remind me to go fishing Saturday morning" keeps its morning (core/assistant_turn._reminder_reply, the fishing
conversation check 2026-11-26: the event had no time): a part of the day with no hour is that part's usual time.
"""

from types import SimpleNamespace

from core import assistant_turn


def test_a_part_of_the_day_is_its_usual_time():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "Added."))
    assistant_turn._reminder_reply(context, "remind me to go fishing Saturday morning")
    assistant_turn._reminder_reply(context, "remind me to call mom tomorrow evening")
    assistant_turn._reminder_reply(context, "remind me to check the oil Saturday")
    assistant_turn._reminder_reply(context, "remind me to plant garlic Saturday morning at 10")
    assert [a.get("time") for a in ran] == ["08:00", "18:00", None, "10:00"]
