"""
tests.test_live_sweep
=======================

The live sweep's checks (tools/live_sweep.py, 2026-11-25): each sign the day's sweeps found is flagged, and a plain
good answer is flagged with nothing; the corpus holds only strings and conversations of strings.
"""

from tools.live_sweep import flags_of
from tests.live_sweep_corpus import CORPUS


def test_each_sign_the_sweeps_found_is_flagged():
    assert "raw tool call" in flags_of('{"name": "add_alarm", "arguments": {}}', [])
    assert "sheet words" in flags_of("The fact sheet only mentions your schedule.", [])
    assert "no reply" in flags_of("", [])
    assert "name refused" in flags_of("I don't have a product called 'cutting boards'.", ["record_sale"])
    assert "claimed a change" in flags_of("I've added it to your calendar.", [])
    assert "said twice" in flags_of("The project you're planning: goats. The project you're planning: goats.", [])


def test_a_good_answer_is_flagged_with_nothing():
    assert flags_of("Thanksgiving is Thursday, November 26, 2026 (tomorrow).", []) == []
    assert flags_of("I've added it to your calendar.", ["add_calendar_event"]) == []


def test_the_corpus_is_phrasings_and_conversations():
    for area, phrasings in CORPUS.items():
        assert phrasings, area
        for said in phrasings:
            turns = said if isinstance(said, list) else [said]
            assert turns and all(isinstance(t, str) and t.strip() for t in turns), (area, said)
