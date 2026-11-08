"""
tests.test_capability_reminders
=================================

The gentle "did you know you could go do X right now?" reminder MIA offers (core/capability_reminders.py, Zac
2026-11-08). It only ever fires with a real ability behind it (empty in, empty out), it wraps the ability in a warm,
low-pressure frame and appends the honest reason, and a given roll always yields the same line so the reminder is
deterministic and testable.
"""

from core import capability_reminders


def test_no_abilities_means_no_reminder():
    assert capability_reminders.a_reminder([], 0.5) == ""
    assert capability_reminders.a_reminder([("  ", "")], 0.5) == ""  # blanks don't count


def test_a_reminder_frames_the_ability_and_keeps_the_reason():
    line = capability_reminders.a_reminder([("pick the guitar back up", "You're a clean run from the next stage.")], 0.0)
    assert "pick the guitar back up" in line
    assert line.endswith("You're a clean run from the next stage.")
    # the frame is one of the warm openings, not a bare restatement
    assert line != "pick the guitar back up"


def test_a_reason_is_optional():
    line = capability_reminders.a_reminder([("get out on the trail", "")], 0.0)
    assert "get out on the trail" in line and line.strip() == line and not line.endswith(" ")


def test_the_same_roll_always_gives_the_same_line():
    abilities = [("put time into Guitar", "stage 2 is ready"), ("get back to your bookshelf project", "it's parked")]
    assert capability_reminders.a_reminder(abilities, 0.37) == capability_reminders.a_reminder(abilities, 0.37)


def test_the_frame_is_affirming_not_a_scold():
    # across the roll range the opening stays low-pressure — never "you should" / "you need to" / "you haven't"
    lines = [capability_reminders.a_reminder([("make a pour-over", "the beans are fresh")], r / 12) for r in range(12)]
    joined = " ".join(lines).lower()
    assert "you could" in joined or "within reach" in joined or "everything you need" in joined
    assert "you should" not in joined and "you haven't" not in joined and "why don't you" not in joined
