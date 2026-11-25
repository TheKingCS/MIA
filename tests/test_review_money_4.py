"""
tests.test_review_money_4
===========================

The fourth review (2026-11-25), each finding as its failing input: money and business planning in "scenario" or "quiz"
words never starts a drill; a program's id only as the whole subject; the connected sketch says MIA must listen on the
home network, sounds its alarm before reporting, and keeps its waits short; the snowball and a faulty return said
right.
"""

from types import SimpleNamespace

from core import bench_designs, drills, paths


def _said():
    """A conversation with nothing said yet."""
    return SimpleNamespace(messages=[])


def test_money_and_business_planning_words_never_start_a_drill():
    """A budget scenario, a business scenario, "quiz me on my budget": None; "give me a money drill": the drill."""
    for words in ("let's do a budget scenario for next month", "run a business scenario where sales drop 20%",
                  "run a scenario for my budget", "i want a debt scenario analysis", "quiz me on my budget",
                  "start the pricing scenario spreadsheet"):
        assert drills.reply(None, _said(), words) is None, words
    assert drills.reply(None, _said(), "give me a money drill").startswith("Drill: A surprise bill.")


def test_a_programs_id_counts_only_as_the_whole_subject():
    """"Grow vegetables for a market business": gardening; "get fit without spending money": fitness; "beekeeping for
    money": not Money basics; "learn money": Money basics."""
    assert paths.find_program(None, "grow vegetables for a market business").id == "gardening"
    assert paths.find_program(None, "get fit without spending money").id == "fitness"
    found = paths.find_program(None, "beekeeping for money")
    assert found is None or found.id != "money"
    assert paths.find_program(None, "learn money").id == "money"


def test_the_connected_sketch_can_reach_mia_and_never_holds_up_the_alarm():
    """The steps say to listen on the home network and open port 8765; the buzzer is set before the report; the HTTP
    waits are 2 seconds."""
    got = bench_designs.design(SimpleNamespace(), "temp_alarm", "esp32dev", report=True)
    assert "server.host 0.0.0.0" in got["report_steps"][0] and "8765" in got["report_steps"][0]
    sketch = got["sketch"]
    assert sketch.index("digitalWrite(BUZZER, alarm ? HIGH : LOW);") < sketch.index("reportToMia(c);")
    assert "http.setConnectTimeout(2000);" in sketch and "http.setTimeout(2000);" in sketch


def test_the_snowball_and_a_faulty_return_are_said_right():
    """The refund's wrong choice says the snowball is smallest balance; the return follows the law where he sells."""
    bill, market = drills.by_id("surprise_bill"), drills.by_id("market_day")
    assert "smallest balance" in drills.judge(bill, 4, 2)["why"]
    assert "the law where you sell" in drills.judge(market, 3, 0)["best"]
