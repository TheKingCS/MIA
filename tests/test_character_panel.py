"""
tests.test_character_panel
=============================

Unit test for gui.character_panel.reaction_for_module — pure lookup
logic, no Qt event loop needed. The reactive subscribe/unsubscribe
widget behavior itself was verified with a headless offscreen-QPA
smoke test (this project's convention for Qt widget behavior — see
tests/test_assistant_module.py's docstring for the same reasoning).
"""

from __future__ import annotations

from gui.character_panel import _IDLE_LINES, MODULE_REACTIONS, idle_line, reaction_for_module


def test_known_module_returns_its_specific_reaction():
    icon, line = reaction_for_module("notes", "Notes")
    assert (icon, line) == MODULE_REACTIONS["notes"]


def test_unknown_module_falls_back_to_generic_line():
    icon, line = reaction_for_module("some_future_module", "Some Future Module")
    assert line == "Watching over Some Future Module."


def test_every_known_module_reaction_has_nonempty_icon_and_line():
    for module_id, (icon, line) in MODULE_REACTIONS.items():
        assert icon, f"{module_id} has an empty icon"
        assert line, f"{module_id} has an empty line"


def test_idle_line_cycles_in_order():
    assert [idle_line(i) for i in range(len(_IDLE_LINES))] == _IDLE_LINES


def test_idle_line_wraps_around():
    assert idle_line(len(_IDLE_LINES)) == _IDLE_LINES[0]
    assert idle_line(len(_IDLE_LINES) + 1) == _IDLE_LINES[1]
