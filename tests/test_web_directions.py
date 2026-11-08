"""My Directions (DEC-0141/0143): the screen, its direction.* actions and the voice tools that run the same actions."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.direction import DirectionBook
import core.web_directions as wd


@pytest.fixture
def person(tmp_path):
    """A person with an empty direction book and a workshop shelf with one material."""
    ctx = SimpleNamespace(materials=SimpleNamespace(all_materials=lambda: [SimpleNamespace(name="walnut scrap")]))
    ctx.direction = DirectionBook(ctx, data_dir=tmp_path)
    return ctx


def act(ctx, kind, **params):
    """Runs an action as the approval flow would: describe, then execute."""
    ACTION_TYPES[kind].describe(ctx, params)
    return ACTION_TYPES[kind].execute(ctx, params)


def test_an_empty_book_shows_no_directions_and_no_invented_seed(person):
    page = wd.screen(person, date(2026, 11, 8))
    assert page["available"] and page["directions"] == [] and page["seed"] == ""
    assert [f["name"] for f in page["forms"]["direction"]["fields"]] == ["title", "statement", "encourage", "nudges"]


def test_setting_one_puts_it_in_force_with_its_nudges_and_a_steady_seed(person):
    act(person, "direction.add", title="Make before buying", statement="Make or mend before buying new.",
        encourage="Offer the make way.", nudges="Anything to mend this week?\n\n  ")
    page = wd.screen(person, date(2026, 11, 8))
    [d] = page["directions"]
    assert d["active"] and d["nudges"] == ["Anything to mend this week?"] and page["in_force"] == 1
    assert page["seed"] and page["seed"] == wd.screen(person, date(2026, 11, 8))["seed"]
    assert d["values"]["nudges"] == "Anything to mend this week?"


def test_a_direction_needs_a_name_and_words_and_names_are_not_repeated(person):
    with pytest.raises(ActionError):
        ACTION_TYPES["direction.add"].describe(person, {"title": "", "statement": "x"})
    with pytest.raises(ActionError):
        ACTION_TYPES["direction.add"].describe(person, {"title": "Slow", "statement": "  "})
    act(person, "direction.add", title="Slow", statement="Leave room for quiet.")
    with pytest.raises(ActionError, match="already have"):
        ACTION_TYPES["direction.add"].describe(person, {"title": "slow", "statement": "again"})


def test_change_pause_resume_and_let_go_each_run_through_their_action(person):
    act(person, "direction.add", title="Slow", statement="Leave room for quiet.")
    did = person.direction.directions[0].direction_id
    act(person, "direction.edit", direction_id=did, statement="Leave room for drawing and walks.")
    assert person.direction.get(did).statement == "Leave room for drawing and walks."
    act(person, "direction.pause", direction_id=did)
    assert not person.direction.get(did).active and wd.screen(person)["in_force"] == 0
    with pytest.raises(ActionError, match="already paused"):
        ACTION_TYPES["direction.pause"].describe(person, {"direction_id": did})
    act(person, "direction.resume", direction_id=did)
    assert person.direction.get(did).active
    act(person, "direction.remove", direction_id=did)
    assert person.direction.directions == []
    with pytest.raises(ActionError, match="isn't one of yours"):
        ACTION_TYPES["direction.remove"].describe(person, {"direction_id": did})


def test_the_voice_tools_list_add_pause_and_inspire_by_name(person):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_direction_actions import register_direction_actions

    reg = AssistantActionRegistry()
    register_direction_actions(reg)
    tool = reg._actions
    run = lambda name, **args: tool[name].handler(person, args)  # noqa: E731
    assert "haven't set any" in run("list_directions")
    assert "grounded" in run("todays_seed")
    assert "one of your directions" in run("add_direction", statement="Grow and cook my own food", title="Grow my food")
    assert "Grow my food: Grow and cook my own food" in run("list_directions")
    assert "paused" in run("pause_direction", direction="grow")
    assert "(paused)" in run("list_directions")
    assert "Which direction" in run("resume_direction", direction="tennis")
    assert "back in force" in run("resume_direction", direction="Grow my food")
