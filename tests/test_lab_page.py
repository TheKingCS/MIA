"""
tests.test_lab_page
=====================

A course's labs (core/lab_page.py, web/course.html): the course page before and after he starts it (stages, the lab
chosen with its sketch and wiring, checks passed), an unknown course, and the action that starts a course
(`path.start`, core/path_actions.py), refused for one already started.
"""

from types import SimpleNamespace

import pytest

from core import lab_page
from core import paths
from core.actions import ACTION_TYPES, ActionError
from core.esp32_path import PROGRAM


@pytest.fixture
def no_board(monkeypatch):
    """No ESP32 plugged in and no PlatformIO, whatever this machine has."""
    from core import esp32_lab

    monkeypatch.setattr(esp32_lab, "board", lambda *a, **k: {"port": "", "description": "", "pio": [],
                                                             "missing": "no ESP32 on a USB port"})


def test_the_course_page_before_he_starts_shows_the_first_lab_and_the_map(tmp_path, no_board):
    """Not started: stage 1 current, the rest later, nothing passed; the blink lab with its sketch and ini; no board.
    The blink lab's circuit is there for the simulator, its build starting at GPIO 2."""
    context = SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path))
    page = lab_page.page(context, "esp32")
    assert page["available"] and not page["started"]
    assert [s["state"] for s in page["stages"]][:2] == ["current", "later"]
    assert not any(c["passed"] for s in page["stages"] for c in s["checks"])
    assert page["lab"]["id"] == "blink" and "MIA BLINK" in page["lab"]["code"] and "[env:" in page["lab"]["ini"]
    assert [s["a"] for s in page["lab"]["circuit"]["steps"]] == ["GPIO 2", "r1.b", "led1.cathode"]
    assert page["board"]["ready"] is False and page["course"]["name"] == "Build With ESP32"


def test_a_lab_asked_for_by_name_and_a_check_he_passed(tmp_path, no_board):
    """Started, the blink check passed: shown passed on the map; ?lesson=dht shows the dht lab and its wiring."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(PROGRAM, goal="a soil node")
    book.attempt(PROGRAM, "esp_blink", True, 5, "board_says", "")
    page = lab_page.page(SimpleNamespace(paths=book), "esp32", "dht")
    assert page["started"] and page["lab"]["id"] == "dht" and page["lab"]["wiring"]
    passed = {c["id"] for s in page["stages"] for c in s["checks"] if c["passed"]}
    assert "esp_blink" in passed
    assert lab_page.page(SimpleNamespace(paths=book), "esp32", "not-a-lab")["lab"]["id"] != "not-a-lab"


def test_a_course_that_isnt_on_the_paths_is_said_plainly(tmp_path):
    """An unknown course: not available, with why."""
    page = lab_page.page(SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path)), "underwater-basket")
    assert page == {"available": False, "why": "There's no course by that name on MIA's learning paths."}


def test_starting_a_course_is_an_action_with_its_own_plan_and_only_once(tmp_path):
    """path.start: described with the course's plan, started with it, then refused as already started."""
    kind = ACTION_TYPES["path.start"]
    context = SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path))
    assert "Build With ESP32" in kind.describe(context, {"path": "esp32"})
    assert kind.execute(context, {"path": "esp32", "goal": "a soil node"}).startswith("Started Build With ESP32.")
    assert context.paths.path("esp32") is not None
    with pytest.raises(ActionError, match="already started"):
        kind.describe(context, {"path": "esp32"})
    with pytest.raises(ActionError):
        kind.describe(context, {"path": "nope"})
