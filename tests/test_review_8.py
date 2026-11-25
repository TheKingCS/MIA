"""
tests.test_review_8
=====================

The eighth review's findings (2026-11-25), each kept fixed: a family member named bare is an emergency only with
nothing after the verb ("grandma collapsed", never "mom passed out the cookies"), "he" is never found inside "the", and
paint, a movie or a list never bleed; "create a task" and "change my alarm" are changes asked for; "Tuesday's meeting"
is never the reminder's day; a rate never cancels the hours; a total adds the kids said apart from it; the next-lesson
route never takes "the next step for my money" or a meeting's lesson plan; a bare "ok" is a yes, not a pleasantry;
an entry's date said in words is read, and an update can't store "null".
"""

from datetime import date
from types import SimpleNamespace

from core import first_aid_floor as floor
from core import homestead_sums as sums
from core import paths
from core.assistant_path_actions import next_lesson_reply
from core.assistant_turn import named_day
from core.budget_manager import _entry_date
from core.claim_check import HONEST, honest
from core.personality import pleasantry_line


def test_the_floor_has_no_new_false_alarms_and_misses_no_real_one():
    for words in ("mom passed out flyers at the fair", "mom passed out the cookies", "granny passed out the hymn books",
                  "dad collapsed the tent", "mom collapsed the boxes", "my dog is choking, dad is at work",
                  "the bleeding won't stop on this paint job", "the movie had gushing blood", "I cut my finger off the list",
                  "the dog is choking"):
        assert floor.detect(words) is None, words
    for words in ("grandma collapsed", "mom collapsed", "dad just collapsed!", "he cut his finger off",
                  "pouring blood everywhere", "bleeding won't stop", "my arm is gushing blood", "my son collapsed",
                  "he is choking"):
        assert floor.detect(words) is not None, words


def test_changes_asked_for_in_other_words_are_held_to_the_claim_check():
    for prompt, text in (("create a task to call the vet tomorrow", "Done. Your task is created for tomorrow."),
                         ("change my alarm to 7", "Your alarm is now set for 7:00."),
                         ("make a note that the gate is broken", "Your note is saved.")):
        assert honest(None, prompt, text) == HONEST, prompt


def test_a_meetings_day_is_never_the_reminders():
    assert named_day("remind me to prep for Tuesday's meeting on Friday", date(2026, 11, 25)) == date(2026, 11, 27)


def test_the_sums_read_rates_and_groups_right():
    assert sums.days_in("water for 72 hours at a gallon a day each") == 3
    assert sums.people_in("for 2 people and 2 kids") == 4 and sums.people_in("the 2 of us and 3 kids") == 5
    assert sums.people_in("4 people, 2 adults and 2 kids") == 4 and sums.people_in("family of 4 with 1 child under 5") == 4


def test_the_next_lesson_route_takes_only_a_course_named(tmp_path):
    context = SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path))
    for words in ("what's the next step for my money", "what are the next steps for the business meeting",
                  "what's my next lesson plan for the business meeting"):
        assert next_lesson_reply(context, words) is None, words
    assert next_lesson_reply(context, "What's my next guitar lesson?").startswith("You haven't started Guitar")


def test_a_bare_ok_is_a_yes_and_a_date_in_words_is_read():
    for words in ("ok", "perfect", "ok mia", "got it"):
        assert pleasantry_line(words) == "", words
    today = date.today()
    assert _entry_date("11/20/2026") == "2026-11-20" and _entry_date("Nov 20, 2025") == "2025-11-20"
    assert _entry_date("yesterday") == date.fromordinal(today.toordinal() - 1).isoformat()
    assert _entry_date("null") == today.isoformat()
