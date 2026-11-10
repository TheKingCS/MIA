"""
tests.test_greenhouse_setup
=============================

The greenhouse's setup as one sequence (core/greenhouse_setup.py, DEC-0150): "let's set up the greenhouse" and
"what's next?" say the step you're on, with its device, what it needs and what to say; each step is done from what's
recorded (a job finished, the MCU flashed, the node pushed, PlatformIO found, the Pi prepared, the node read), "done"
only counts for a step only the person can see, and "skip that" moves past one. Started, it's a mission (Zac,
2026-11-09: in Missions, not on Today): one objective a step, a tick there moves it on, and the Greenhouse page's
What's Next shows the step.
"""

from types import SimpleNamespace

import pytest

from core import greenhouse_link as gl
from core import greenhouse_provision as gp
from core import greenhouse_setup as gs
from core import life_events
from core.life_events import LifeEventLog

NO_PIO = lambda: None  # noqa: E731
PIO = lambda: ["pio"]  # noqa: E731


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A context with the link and a history in a temp folder, and the Pi's key and bundle pointed there too."""
    context = SimpleNamespace()
    context.greenhouse_link = gl.GreenhouseLink(context, data_dir=tmp_path)
    context.life_events = LifeEventLog(context, tmp_path)
    monkeypatch.setattr(gp, "KEY", tmp_path / ".keys" / "node")
    monkeypatch.setattr(gp, "BUNDLE", tmp_path / "bundle")
    return context


def _finish(context, job_id):
    """Records a job walked to its end, as core/trade_actions.py does."""
    life_events.record(context.greenhouse_link, "trade_finished", "Finished", payload={"id": job_id})


def test_the_first_step_is_building_the_system_and_says_what_to_say(world):
    """Nothing done yet: step 1, with what it needs and the exact words to start it."""
    said = gs.reply(world, "Let's set up the greenhouse", NO_PIO)
    assert said.startswith("Let's set up the greenhouse. Step 1 of 11: Build the aquaponics system")
    assert "Say “walk me through building the aquaponics system”." in said
    assert world.greenhouse_link.setup_started


def test_each_recorded_step_moves_what_s_next_on(world):
    """The finished build job, then PlatformIO found, then the flash recorded: the next step follows each."""
    gs.reply(world, "let's set up the greenhouse", NO_PIO)
    _finish(world, "aquaponics_system")
    assert "Install PlatformIO" in gs.reply(world, "what's next?", NO_PIO)
    assert "Flash the safety MCU" in gs.reply(world, "ok what's next", PIO)
    life_events.record(world.life_events, "mcu_flashed", "Flashed")  # the household history MIA reads
    assert "walk me through installing the controller" in gs.reply(world, "what's next for the greenhouse", PIO)


def test_done_counts_only_for_a_step_only_the_person_can_see(world):
    """"done" on the build job points at the job; PlatformIO missing says so; "the Pi is ready" counts for the card."""
    gs.reply(world, "let's set up the greenhouse", NO_PIO)
    assert "I'll know" in gs.reply(world, "done", NO_PIO)
    _finish(world, "aquaponics_system")
    assert "can't find PlatformIO" in gs.reply(world, "done", NO_PIO)
    _finish(world, "aquaponics_controls")
    life_events.record(world.life_events, "mcu_flashed", "Flashed")  # the household history MIA reads
    gp.KEY.parent.mkdir(parents=True)
    gp.KEY.write_text("key")
    gp.BUNDLE.mkdir()
    (gp.BUNDLE / "PI_SETUP.md").write_text("steps")
    assert "Raspberry Pi Imager" in gs.where(world, PIO)[1].what
    said = gs.reply(world, "the Pi is ready", PIO)
    assert said.startswith("Got it. Step 7 of 11: Push the greenhouse node")


def test_skip_moves_past_a_step_and_the_end_says_it_s_handed_over(world):
    """"skip that" passes the step; once everything is done the sequence says so and lets "done" go by."""
    gs.reply(world, "let's set up the greenhouse", NO_PIO)
    assert "Install PlatformIO" in gs.reply(world, "skip that", NO_PIO)
    world.greenhouse_link.setup_said = [s.id for s in gs.STEPS]
    assert "handed over" in gs.reply(world, "what's next?", NO_PIO)
    assert gs.reply(world, "done", NO_PIO) is None


def test_a_step_only_the_person_sees_counts_once_a_later_one_is_done(world):
    """The SD card and the node started aren't recorded, but the node read proves them."""
    world.greenhouse_link.taken_over, world.greenhouse_link.state = True, {"cells": []}
    for job in ("aquaponics_system", "aquaponics_controls"):
        _finish(world, job)
    life_events.record(world.life_events, "mcu_flashed", "Flashed")  # the household history MIA reads
    life_events.record(world.greenhouse_link, "node_pushed", "Pushed")
    gp.KEY.parent.mkdir(parents=True)
    gp.KEY.write_text("key")
    gp.BUNDLE.mkdir()
    (gp.BUNDLE / "PI_SETUP.md").write_text("steps")
    assert gs.where(world, PIO)[1].id == "secret"  # a read node doesn't prove its email password was sent
    life_events.record(world.greenhouse_link, "node_secret_sent", "Sent")
    assert gs.where(world, PIO)[1].id == "commission"


def test_bare_what_s_next_is_left_alone_until_the_setup_has_started(world):
    """Outside the setup, "what's next?" is for something else; other words are never the setup's."""
    assert gs.reply(world, "what's next?", NO_PIO) is None
    assert gs.reply(world, "how's the weather", NO_PIO) is None


def test_a_flash_and_a_push_that_finish_are_recorded(world, monkeypatch):
    """"yes, flash it" and "yes, push it" that succeed put mcu_flashed and node_pushed in the history."""
    link = world.greenhouse_link
    link.pending = {"kind": "flash", "port": "COM5"}
    monkeypatch.setattr(gp, "platformio", PIO)
    assert gp.reply(world, "yes, flash it", run=lambda cmd, timeout: (0, "ok")).startswith("Flashed")
    gp.KEY.parent.mkdir(parents=True)
    gp.KEY.write_text("key")
    link.pending = {"kind": "push", "host": "mia-greenhouse", "user": "pi"}
    assert gp.reply(world, "yes, push it", run=lambda cmd, timeout: (0, "ok")).startswith("The greenhouse node is on")
    types = {e.type for e in life_events.events_for(world, types=("mcu_flashed", "node_pushed"))}
    assert types == {"mcu_flashed", "node_pushed"}


def test_starting_the_setup_makes_its_mission_and_a_tick_there_moves_it_on(tmp_path, monkeypatch):
    """DEC-0125 without voice, in Missions: "let's set up the greenhouse" makes the mission, one objective a step;
    ticking the first on the Missions screen (objective.tick) counts as done and the next step is said; a step MIA
    sees done herself is ticked for her; Today lists none of it; the Greenhouse page's card shows the step."""
    from core.actions import ACTION_TYPES
    from core.today import today_items
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.greenhouse_link = gl.GreenhouseLink(world, data_dir=tmp_path / "gh")
    monkeypatch.setattr(gp, "KEY", tmp_path / ".keys" / "node")
    monkeypatch.setattr(gp, "BUNDLE", tmp_path / "bundle")
    monkeypatch.setattr(gp, "platformio", NO_PIO)
    assert gs.page_card(world) is None  # not started
    assert "It's in your Missions as “Set up the greenhouse”" in gs.reply(world, "let's set up the greenhouse", NO_PIO)
    mission = gs.mission(world)
    assert [o.description for o in mission.objectives] == [gs.title_of(s) for s in gs.STEPS]
    gs.reply(world, "let's set up the greenhouse", NO_PIO)
    assert len([m for m in world.missions.all_missions() if m.name == gs.MISSION]) == 1  # never twice
    ACTION_TYPES["objective.tick"].execute(world, {"mission_id": mission.mission_id, "index": 0})
    assert gs.say_next(world, NO_PIO).startswith("Step 2 of 11: Install PlatformIO")
    life_events.record(world.life_events, "mcu_flashed", "Flashed")  # the household history MIA reads
    gs.where(world, NO_PIO)
    assert world.missions.get_mission(mission.mission_id).objectives[2].progress == 1  # ticked for her
    assert not any("reenhouse" in i.title for i in today_items(world))
    card = gs.page_card(world)
    assert card["title"] == "Install PlatformIO on this PC" and card["mission_id"] == mission.mission_id
