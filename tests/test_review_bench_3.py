"""
tests.test_review_bench_3
===========================

The third review (2026-11-25), each finding as its failing input: "build me a ..." only as a request at the start, never
a reminder, a note, a time or a stand; her designs only proper names, asked about exactly, and a plan said only when its
decision calls it one; parts matched by whole word, several never guessed; a saved build re-saved isn't built, and
none is marked built twice; the board from board words only.
"""

from types import SimpleNamespace

import pytest

from core import bench_builds, bench_designs, self_knowledge
from core.actions import ACTION_TYPES, ActionError
from core.part_specs import BUILTIN


def test_ordinary_messages_with_a_designs_words_arent_designs():
    """Reminders, notes, a time, a rain barrel stand: None; the requests themselves: designs, the ESP32 unless a board
    is named."""
    for words in ("make sure to water the plants tomorrow", "make me a watering reminder for 7am",
                  "remind me to make dinner when the soil is dry", "how do i build a rain barrel stand?",
                  "make a note: check the water level in the cistern", "make a temperature alarm at 6am"):
        assert bench_designs.reply(SimpleNamespace(), None, words) is None, words
    assert "on your ESP32" in bench_designs.reply(SimpleNamespace(), None, "build me a motion light")
    assert "on your Arduino Nano" in bench_designs.reply(SimpleNamespace(), None,
                                                         "can you design a tank level gauge for my nano")


def test_only_her_named_designs_asked_about_exactly_and_a_plan_only_when_its_decision_says_so():
    """"What is my critical path?", "what is least privilege?", "what's her face?": not hers; the Life Enrichment
    Protocol: a plan; "what is active training?" (built): never said to be a plan."""
    for words in ("what is my critical path?", "what is least privilege?", "whats her face?"):
        assert not self_knowledge.asks_about_her(words) and self_knowledge.plan_reply(words) is None, words
    assert self_knowledge.plan_reply("what is the life enrichment protocol?").startswith(
        "The Life Enrichment Protocol is one of my plans")
    assert self_knowledge.plan_reply("what is active training?") is None
    assert all(n == n.lower() and len(n.split()) >= 2 for n in self_knowledge._designs())


def test_parts_match_by_whole_word_and_several_are_never_guessed(tmp_path):
    """An LED never matches an OLED display; two resistors: neither taken, said as several; marked built twice:
    refused; re-saved: not built."""
    led = bench_designs.matching_parts([SimpleNamespace(name="SSD1306 OLED display", category=""),
                                        SimpleNamespace(name="5mm LED red", category="")], BUILTIN["led"])
    assert [c.name for c in led] == ["5mm LED red"]
    stock = [SimpleNamespace(component_id="a", name="Resistor 10k", category="", quantity=5),
             SimpleNamespace(component_id="b", name="Resistor 1k", category="", quantity=5)]
    context = SimpleNamespace(bench_builds=bench_builds.BuildBook(data_dir=tmp_path),
                              components=SimpleNamespace(all_components=lambda: stock,
                                                         adjust_quantity=lambda i, d: None))
    build = context.bench_builds.save("Divider", "esp32dev", [{"id": "r1", "spec": "resistor"}], [])
    assert "several of your parts could be it" in ACTION_TYPES["benchbuild.built"].describe(context,
                                                                                            {"build_id": build["id"]})
    ACTION_TYPES["benchbuild.built"].execute(context, {"build_id": build["id"]})
    with pytest.raises(ActionError, match="already marked built"):
        ACTION_TYPES["benchbuild.built"].execute(context, {"build_id": build["id"]})
    assert context.bench_builds.save("Divider", "esp32dev", [{"id": "r1", "spec": "resistor"}], [])["built"] == ""
