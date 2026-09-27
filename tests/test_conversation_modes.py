"""Explicit mode switches (core/conversation_modes.py): a sentence corpus, not wording."""

import pytest

from core.conversation_modes import (
    COMPANION, DIRECT, LISTEN, MOMENTUM, PLAN, detect_mode_change, looks_like_direct_command,
)

MODE_CORPUS = [
    ("MIA, just listen.", LISTEN),
    ("Can you just listen to me for a minute", LISTEN),
    ("I need to vent", LISTEN),
    ("Can I vent for a sec?", LISTEN),
    ("Don't try to fix it, I just need someone to listen", LISTEN),
    ("MIA, no bullshit. I need the hard truth.", DIRECT),
    ("Be straight with me", DIRECT),
    ("Don't sugarcoat it", DIRECT),
    ("MIA, hype me up", MOMENTUM),
    ("I need a pep talk", MOMENTUM),
    ("Get me through this shift", MOMENTUM),
    ("MIA, help me figure out what to do", PLAN),
    ("I'm so overwhelmed", PLAN),
    ("I don’t know what to do", PLAN),
    ("Back to normal", COMPANION),
]


@pytest.mark.parametrize("text, mode", MODE_CORPUS)
def test_mode_corpus(text, mode):
    assert detect_mode_change(text).mode == mode


NO_CHANGE = [
    "Good morning MIA",
    "Just listen to this song, it's great",
    "Play something I can just listen to while I work",
    "Of course, that makes sense",
    "The truth is I like the blue one better",
    "Add a journal entry to my notes about the fence",  # a Notes request, not journaling
    "Make a new journal entry in Notes",
]


@pytest.mark.parametrize("text", NO_CHANGE)
def test_no_change(text):
    assert detect_mode_change(text).is_empty


def test_journal_start_implies_listen():
    change = detect_mode_change("I want to journal")
    assert change.journal is True and change.mode == LISTEN


def test_journal_start_keeps_a_named_mode():
    change = detect_mode_change("Let's journal. No bullshit though.")
    assert change.journal is True and change.mode == DIRECT


def test_off_record_and_back():
    assert detect_mode_change("This is off the record").off_record is True
    assert detect_mode_change("Don't remember this, ok?").off_record is True
    back = detect_mode_change("Ok, back on the record")
    assert back.off_record is False and back.journal is False and back.mode == COMPANION


def test_done_journaling_ends_the_journal():
    change = detect_mode_change("I'm done journaling")
    assert change.journal is False and change.mode == COMPANION


@pytest.mark.parametrize("text, expected", [
    ("Add milk to the grocery list", True),
    ("MIA, remind me to call Sarah", True),
    ("Hey MIA, log 120 hours on the mower", True),
    ("How much have I spent this month?", True),
    ("The truck broke down again and I'm done", False),
    ("I hate that I have to add more hours", False),
    ("Work was awful", False),
])
def test_direct_command(text, expected):
    assert looks_like_direct_command(text) is expected
