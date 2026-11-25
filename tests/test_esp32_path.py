"""
tests.test_esp32_path
=======================

Build With ESP32 (core/esp32_path.py): the course has a sound shape, every lab its parts and a sketch that prints the
marker its check reads, the check passes from what the board said (seen, a mark, a spread, a range), a pass is kept as
an attempt on his path, and "I want to learn ESP32" finds it.
"""

import re
from types import SimpleNamespace

import pytest

from core import esp32_path as e
from core import paths


def test_the_course_is_sound_and_every_lab_prints_what_its_check_reads():
    """No shape problems; each lesson has a lab; each check's marker appears in its stage's sketches as MIA <MARKER>;
    the sketches keep their C escapes (\\n) and never hold a Wi-Fi password."""
    assert paths.problems(e.PROGRAM) == []
    for stage in e.STAGES:
        code = " ".join(e.LABS[lesson.id]["code"] for lesson in stage.lessons)
        for check in stage.checks:
            assert f"MIA {check.about.split()[0]}" in code, check.id
    for lesson_id, lab in e.LABS.items():
        assert lab["parts"] and "Serial.begin(115200)" in lab["code"], lesson_id
        assert "\\n" in lab["code"] or "println" in lab["code"], lesson_id
        assert not re.search(r"password\s*=\s*\"[^\"]+\"", lab["code"], re.I), lesson_id


@pytest.mark.parametrize("check_id,said,passed", [
    ("esp_blink", "MIA BLINK 1\nMIA BLINK 5\n", True),
    ("esp_blink", "MIA BLINK 2\n", False),
    ("esp_hello", "ets Jun  8 2016 boot\nMIA HELLO\n", True),
    ("esp_pot", "MIA ADC 12\nMIA ADC 4095\n", True),
    ("esp_pot", "MIA ADC 1800\nMIA ADC 2100\n", False),
    ("esp_dht", "MIA TEMP 21.4\nMIA HUMIDITY 40\n", True),
    ("esp_dht", "MIA SENSOR_ERROR\n", False),
    ("esp_wifi", "MIA WIFI_WAITING\nMIA WIFI 192.168.1.40\n", True),
])
def test_a_check_is_judged_from_what_the_board_said(check_id, said, passed):
    """Seen, at least a mark, spread and range, from the board's own lines; boot noise and other markers ignored."""
    check = e.PROGRAM.check(check_id)[1]
    assert e.judge(check, said)[0] is passed


def test_a_pass_is_kept_on_his_path(tmp_path):
    """The verifier keeps the attempt on the path: the blink passed from its serial output."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(e.PROGRAM, goal="build a soil node")
    context = SimpleNamespace(paths=book)
    got = paths.verify(context, e.PROGRAM, "esp_blink", {"serial": "MIA BLINK 6"})
    assert got["passed"] and book.passed("esp32", "esp_blink")
    with pytest.raises(ValueError):
        paths.verify(context, e.PROGRAM, "esp_hello", {"serial": ""})


def test_wanting_to_learn_esp32_finds_the_course():
    """By its words: "esp32", "microcontroller"."""
    assert paths.find_program(SimpleNamespace(paths=None), "I want to learn to build with ESP32").id == "esp32"
