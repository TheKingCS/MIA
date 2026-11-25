"""
tests.test_drills
===================

Scenario drills (core/drills.py): every drill well formed (one best choice a question, a lesson its course has); a
drill run by voice from its start to its summary, the place riding in MIA's own message; answers by letter or by
ordinal, "stop the drill", and words that aren't a drill (a drill bit, a fire drill at home) left alone; the course
page's data; and a drill never touching his path.
The canning and carpentry drills by their courses' words, and the Classroom's list of courses with labs or drills.
And ordinary messages (a stud, a worst case scenario, a drill at work) that never start one, with commands let
through while one waits.
The power outage drill too, named by its own words.
"""

from types import SimpleNamespace

from core import drills
from core import lab_page
from core import paths


def _said(*texts):
    """A conversation whose assistant messages are these."""
    return SimpleNamespace(messages=[SimpleNamespace(role="assistant", content=t) for t in texts])


def test_every_drill_has_one_best_choice_a_question_and_a_lesson_its_course_teaches():
    """Each question: two to four choices, exactly one best, every verdict known and every why written; the lesson
    behind each drill is one its course has."""
    assert drills.DRILLS
    for drill in drills.DRILLS:
        assert drills.lesson_title(drill), drill.id
        for q in drill.questions:
            assert 2 <= len(q.choices) <= 4 and [c.verdict for c in q.choices].count("best") == 1, (drill.id, q.ask)
            assert all(c.verdict in ("best", "fine", "wrong") and c.why for c in q.choices)


def test_a_drill_by_voice_from_start_to_summary():
    """"Run the water drill": the situation and question 1; "B": right, then question 2 with 1 best so far; "the
    third one": close, with the best said; "a": right, and the summary names the lesson to read again."""
    first = drills.reply(None, _said(), "Run the water drill")
    assert first.startswith("Drill: Water on day two.") and "question 1 of 3, 0 best so far" in first
    second = drills.reply(None, _said(first), "B")
    assert second.startswith("Right.") and "question 2 of 3, 1 best so far" in second
    third = drills.reply(None, _said(first, second), "the third one")
    assert third.startswith("Close.") and "Best: A rolling boil for 1 minute" in third
    last = drills.reply(None, _said(first, second, third), "I'd go with a")
    assert "That's the drill: 2 of 3 best" in last and "Making water safe" in last


def test_stopping_and_words_that_arent_a_drill():
    """"Stop the drill" ends it; an answer with no drill asked, a drill bit, drilling a hole, a house fire drill,
    and a letter after another kind of reply are all left alone."""
    first = drills.reply(None, _said(), "give me a survival drill")
    assert first.startswith("Drill: ")
    assert drills.reply(None, _said(first), "stop the drill").startswith("Drill stopped: 0 of 0 best")
    for words in ("B", "I need a drill bit for concrete", "drill a hole in the wall", "let's do a fire drill"):
        assert drills.reply(None, _said(), words) is None, words
    assert drills.reply(None, _said(first, "Your shed needs lumber."), "B") is None
    assert drills.reply(None, _said(first), "hmm not sure").startswith("Which one: A, B or C?")
    assert drills.reply(None, _said(first), "repeat that").startswith(first.split("\n\n")[1][:30])


def test_canning_and_carpentry_drills_by_their_courses_words_and_the_classroom_lists_them():
    """"Give me a canning drill" is the green beans; "run a carpentry drill" the 2x6; water-bathing green beans is
    wrong. The Classroom's Hands-on labs lists the board courses first (ESP32, Arduino), then each course with drills,
    said with its count.
    Survival has four drills now, the power outage among them."""
    canning = drills.reply(None, _said(), "give me a canning drill")
    assert canning.startswith("Drill: Putting up green beans.")
    assert drills.reply(None, _said(), "run a carpentry drill").startswith("Drill: Cutting a 2x6 to length.")
    beans = drills.by_id("canning_day")
    assert drills.judge(beans, 2, 1)["verdict"] == "wrong" and "pressure canner" in drills.judge(beans, 2, 1)["best"]
    listed = lab_page.hands_on()
    assert [c["id"] for c in listed] == ["esp32", "arduino", "bushcraft", "gardening", "carpentry"]
    assert listed[3]["what"] == "Lessons, and 1 drill that judges each call"
    assert listed[2]["what"] == "Lessons, and 4 drills that judge each call"


def test_ordinary_messages_never_start_a_drill_and_a_waiting_drill_lets_commands_through():
    """The review's cases (2026-11-25): a stud, pilot holes, a worst case scenario, rent, a drill at work, and the
    sensor in the greenhouse start nothing; while a drill waits, "lights off" or "thanks" aren't asked for a letter,
    "e" or "not sure" are, and "drill me on canning" still starts one."""
    for words in ("can I drill into the stud?", "how far apart should I drill pilot holes for the shop shelves",
                  "what's the worst case scenario for water in the basement?",
                  "in a scenario where I can't pay rent, what happens?", "we had a drill at work today, a fire evacuation",
                  "let's do a fire drill with the family"):
        assert drills.reply(None, _said(), words) is None, words
    first = drills.reply(None, _said(), "give me a survival drill")
    for words in ("lights off", "thanks", "set alarm 7", "pause music"):
        assert drills.reply(None, _said(first), words) is None, words
    for words in ("e", "not sure"):
        assert drills.reply(None, _said(first), words).startswith("Which one: A, B or C?"), words
    assert drills.reply(None, _said(), "drill me on canning").startswith("Drill: Putting up green beans.")


def test_picking_by_letter_or_ordinal_within_the_choices():
    """"C", "(c)", "option b", "the second one": picked; "D" on a three-choice question, and a sentence: not."""
    assert drills.picked("C", 3) == 2 and drills.picked("(c)", 3) == 2 and drills.picked("option b", 3) == 1
    assert drills.picked("the second one", 3) == 1 and drills.picked("I think C", 3) == 2
    assert drills.picked("go with a then", 3) == 0 and drills.picked("a minute", 3) is None
    assert drills.picked("D", 3) is None and drills.picked("boil it for a minute", 3) is None


def test_the_survival_course_page_has_its_drills_and_a_drill_leaves_his_path_alone(tmp_path):
    """The Survival course page carries its drills with their verdicts; a whole drill run by voice records nothing."""
    book = paths.PathBook(None, data_dir=tmp_path)
    page = lab_page.page(SimpleNamespace(paths=book), "bushcraft")
    assert page["available"] and page["board"] is None
    assert [d["id"] for d in page["drills"]] == [d.id for d in drills.of_program("bushcraft")]
    assert page["drills"][0]["questions"][0]["choices"][1]["verdict"] == "best"
    assert lab_page.page(SimpleNamespace(paths=book), "esp32")["drills"] == []
    said = drills.start(drills.DRILLS[0])
    for letter in "BCAA":
        said = drills.reply(None, _said(said), letter)
    assert "That's the drill: Every call the best one." in said and book.paths == {}


def test_the_power_outage_drill_is_named_by_its_own_words_and_keeps_the_cdc_and_usda_rules():
    """"Give me the power outage drill" and "run a blackout drill" start it; the garage is wrong (carbon monoxide), 20
    feet out is best; a fridge at 50 °F means out with the perishables; "is the power out?" isn't a drill."""
    start = drills.reply(None, _said(), "give me the power outage drill")
    assert start.startswith("Drill: The power's out.")
    assert drills.reply(None, _said(), "run a blackout drill").startswith("Drill: The power's out.")
    outage = drills.by_id("power_out")
    assert drills.judge(outage, 1, 0)["verdict"] == "wrong" and "20 feet" in drills.judge(outage, 1, 0)["best"]
    assert "above 40 °F for more than 2 hours" in drills.judge(outage, 3, 0)["best"]
    assert drills.reply(None, _said(), "is the power out?") is None
