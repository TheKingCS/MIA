"""
tests.test_review_labs_5
==========================

The fifth review's findings (2026-11-25), each kept fixed: a photo of an ordinary thing never gets a part's spec and
the first part named wins; a check's question uses the same words its course was looked for by, and words a started
course uses for itself stay its; a lab's why never takes a request for a check, an upload or what it prints, nor
"simulate" one for building along in the simulator; BOOT alone never passes the watchdog's quiet check, and a dose
asked for just as one ends is refused as the board would.
"""

from types import SimpleNamespace

from core import assistant_path_actions as actions
from core import esp32_sim as sim
from core import part_specs, paths, sight
from core.carpentry import PROGRAM as CARPENTRY
from core.esp32_lab import checks_of
from core.esp32_path import judge

EMPTY = SimpleNamespace(messages=[])
GOOD_LED = [("GPIO 2", "r1.a"), ("r1.b", "led1.anode"), ("led1.cathode", "GND")]


def test_an_ordinary_photo_never_gets_a_parts_spec_and_the_first_part_named_wins():
    context = SimpleNamespace(config=None)
    for seen in ("A push mower on a lawn.", "A pushpin board in an office.", "A phone with a capacitive touchscreen.",
                 "A doorbell buzzer by a door."):
        said = sight.look(context, b"x", "what is this?", ask=lambda m, p, i, s=seen: s)["said"]
        assert "I know its spec" not in said, seen
    assert part_specs.named_spec(context, "looks like a DHT11, or possibly a DHT22", models_only=True).id == "dht11"
    assert part_specs.named_spec(context, "an HC SR04 on the bench", models_only=True).id == "hcsr04"
    assert part_specs.named_spec(context, "what's the pinout for the buzzer?").id == "buzzer"


def test_words_a_started_course_uses_for_itself_stay_its_and_a_check_asks_with_them(tmp_path):
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(CARPENTRY, "")
    context = SimpleNamespace(paths=book)
    assert not actions._action_lesson(context, {"topic": "woodworking basics"}).startswith("You haven't started")
    said = actions._action_check(context, {"check": "a woodworking joint"})
    assert not said.startswith("Which one?")


def test_a_labs_why_never_takes_a_check_an_upload_or_what_it_prints(tmp_path):
    context = SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path), llm=None, conversations=None)
    for words in ("what does the pot lab print?", "why won't the blink lab upload?",
                  "why does the relay lab keep failing?"):
        said = sim.reply(context, EMPTY, words)
        assert said is None or not said.startswith("I can't reach my model"), words
    assert sim.reply(context, EMPTY, "walk me through wiring the pot lab in the simulator").startswith(
        "Building the pot lab:")
    assert sim.reply(context, EMPTY, "can you simulate a day in the greenhouse like the web lab") is None


def test_boot_alone_never_passes_the_quiet_check_and_a_dose_as_one_ends_is_busy():
    fallback = {c.id: c for c in checks_of("watchdog")}["esp_fallback"]
    stopped = sim.simulate("watchdog", GOOD_LED, {"heartbeats": [1], "presses": [3]}, 20)
    lines = [t["line"] for t in stopped["trace"]]
    assert "MIA STOP 1" in lines and not judge(fallback, stopped["serial"])[0]
    again = [t["line"] for t in sim.simulate("watchdog", GOOD_LED, {"heartbeats": [1], "doses": [2, 3]}, 5)["trace"]]
    assert again[:5] == ["MIA SAFE_START", "MIA HEARTBEAT 1", "MIA DOSE 1", "MIA REFUSED busy", "MIA DOSED 1"]
