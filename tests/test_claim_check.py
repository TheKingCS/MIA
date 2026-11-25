"""
tests.test_claim_check
========================

Never "I've added a reminder" when nothing was added (core/claim_check.py; live sweep, 2026-11-25), and the three
calendar fixes from the same sweep: "remind me to X on a day" goes on the calendar in code
(core/assistant_turn._reminder_reply), the day his words name wins over the model's made-up date
(`with_his_day`: "Friday at 2pm" had gone on 2024-03-15), and "what's on my calendar tomorrow?" is tomorrow's, never
every event ever (core/calendar_move.listing).
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, claim_check
from core.calendar_manager import CalendarEvent
from core.calendar_move import listing


def test_a_claim_with_nothing_done_is_never_said():
    for text in ("You've been reminded to check the oil on Saturday. I'll send a notification to your device.",
                 "I've added a reminder to your calendar for Saturday.", "Your reminder is set for Saturday at 9."):
        assert claim_check.claims_done(text), text
    for text in ("I can add that to your calendar for Saturday.", "Want me to set a reminder?",
                 "I've put together a few ideas for the garden.", "If you'd like, I'll add it.", "You added 3 eggs."):
        assert not claim_check.claims_done(text), text


def test_asked_for_it_is_said_honestly_and_offhand_it_is_dropped():
    logged = []
    context = SimpleNamespace(failures=SimpleNamespace(record=lambda kind, **f: logged.append(kind)))
    assert claim_check.honest(context, "Remind me to check the oil", "You've been reminded.") == claim_check.HONEST
    assert claim_check.honest(context, "How are you?", "I'm well, thanks. I'll remind you when it's due.") == \
        "I'm well, thanks."
    assert logged == ["claimed_done", "claimed_done"]
    assert claim_check.honest(context, "How are you?", "I'm well, thanks.") == "I'm well, thanks."


def test_the_day_his_words_name_wins_over_the_models():
    today = date(2026, 11, 25)  # a Wednesday
    args = assistant_turn.with_his_day("add_calendar_event", {"title": "vet", "date": "2024-03-15"},
                                       "Put the vet on the calendar for Friday at 2pm", today)
    assert args["date"] == "2026-11-27"
    assert assistant_turn.with_his_day("add_calendar_event", {"date": "2026-12-24"}, "add dinner on 2026-12-24",
                                       today) == {"date": "2026-12-24"}
    assert assistant_turn.with_his_day("add_alarm", {"time": "06:00"}, "Friday at 6", today) == {"time": "06:00"}


def test_remind_me_on_a_day_goes_on_the_calendar():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(
        execute=lambda ctx, name, args: ran.append((name, args)) or "added"))
    assert assistant_turn._reminder_reply(context, "remind me to call the vet tomorrow at 9am") == "added"
    name, args = ran[0]
    assert name == "add_calendar_event" and args["title"] == "Call the vet" and args["time"] == "09:00"
    for words in ("remind me to water the garden every Saturday", "remind me to take the bread out in 20 minutes",
                  "Remind me why I started this"):
        assert assistant_turn._reminder_reply(context, words) is None, words


def test_the_calendar_says_the_day_asked_and_only_whats_coming():
    events = [CalendarEvent("1", "Doctor", "2026-08-14", "09:00"), CalendarEvent("2", "Vet", "2026-11-27", "14:00"),
              CalendarEvent("3", "Mom's birthday", "1960-12-02", None, "", "yearly")]
    today = date(2026, 11, 25)
    assert listing(events, "What's on my calendar tomorrow?", today) == \
        "Nothing on your calendar for Thursday, November 26. Next: Vet on 2026-11-27."
    assert listing(events, "anything Friday?", today) == "On your calendar:\n- 'Vet' on 2026-11-27 at 14:00"
    coming = listing(events, "what's on my calendar", today)
    assert "Doctor" not in coming and "'Mom's birthday' on 2026-12-02 (repeats yearly)" in coming
