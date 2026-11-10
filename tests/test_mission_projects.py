"""
tests.test_mission_projects
=============================

Projects and Missions, connected (core/mission_projects.py, core/mission_guide.py, DEC-0152): a mission joins or leaves
a project through mission.project (recorded, refused when there's nothing to change), the project page lists the same
missions with its progress worked out from tasks and missions (weights from config, Complete is 100, a set-aside
mission doesn't count), the Missions page names each mission's project, a standalone mission still works, and a guided
mission shows the step it's on with the buttons that move it.
"""

import pytest

from core.actions import ACTION_TYPES, ActionError
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The test world with a greenhouse project, two of its tasks, and two missions (one standalone)."""
    from core.actions import ActionCenter

    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.house = context.projects.add_project("Greenhouse Construction")
    context.tasks.add_task(context.house.project_id, "Order the panels")
    done = context.tasks.add_task(context.house.project_id, "Pick the site")
    context.tasks.toggle_done(done.task_id)
    context.foundation = context.missions.add_mission("Build the Greenhouse Foundation")
    for step in ("Prepare the area", "Lay out the foundation", "Verify level"):
        context.missions.add_objective(context.foundation.mission_id, step, "tally", 1)
    context.solo = context.missions.add_mission("Read a chapter")
    return context


def _do(world, kind, **params):
    """Describes then runs an action, as approving one does."""
    ACTION_TYPES[kind].describe(world, params)
    return ACTION_TYPES[kind].execute(world, params)


def test_a_mission_joins_a_project_and_both_pages_show_the_same_record(world):
    """mission.project makes the foundation mission part of the greenhouse; the project page lists it, the Missions
    page names the project, and the standalone mission names none."""
    from core.web_progress import missions_page
    from core.web_projects import projects_page

    said = _do(world, "mission.project", mission_id=world.foundation.mission_id, project_id=world.house.project_id)
    assert said.endswith("is part of Greenhouse Construction; its progress counts toward it.")
    [card] = projects_page(world)["projects"]
    assert [m["name"] for m in card["missions"]] == ["Build the Greenhouse Foundation"]
    cards = {c["name"]: c for c in missions_page(world)["active"]}
    assert cards["Build the Greenhouse Foundation"]["project"] == {"id": world.house.project_id,
                                                                    "name": "Greenhouse Construction"}
    assert cards["Read a chapter"]["project"] is None


def test_project_progress_counts_tasks_and_mission_progress_and_follows_the_weights(world):
    """One task of two done and a mission a third done: (1 + 0 + 1/3) / 3 = 44%; weighting missions 2 makes it
    (1 + 0 + 2/3) / 4 = 42%;
    a set-aside mission leaves the count; a project marked Complete is 100."""
    from core.mission_projects import progress

    world.missions.set_project(world.foundation.mission_id, world.house.project_id)
    world.missions.increment_tally(world.foundation.mission_id, 0, 1)
    assert progress(world, world.house)["percent"] == 44
    world.config.set("modules.projects.progress_weights", {"task": 1, "mission": 2})
    assert progress(world, world.house)["percent"] == 42
    world.missions.update_mission(world.foundation.mission_id, status="abandoned")
    assert progress(world, world.house)["missions_total"] == 0
    world.projects.update_project(world.house.project_id, status="Complete")
    assert progress(world, world.projects.get_project(world.house.project_id))["percent"] == 100


def test_taking_a_mission_out_and_refusing_what_changes_nothing(world):
    """Making it part of the project it's already in, or taking a standalone mission out, is refused; taking it out
    stands it on its own and the history notes both."""
    from core import life_events

    _do(world, "mission.project", mission_id=world.foundation.mission_id, project_id=world.house.project_id)
    with pytest.raises(ActionError):
        _do(world, "mission.project", mission_id=world.foundation.mission_id, project_id=world.house.project_id)
    with pytest.raises(ActionError):
        _do(world, "mission.project", mission_id=world.solo.mission_id, project_id="")
    assert _do(world, "mission.project", mission_id=world.foundation.mission_id, project_id="").endswith(
        "stands on its own now.")
    log = life_events.LifeEventLog(world, data_dir=life_events.folder_of(world.missions))  # the missions' own folder
    kinds = [e.type for e in log.all_events() if e.type in ("mission_project_set", "mission_project_cleared")]
    assert sorted(kinds) == ["mission_project_cleared", "mission_project_set"]


def test_a_trade_job_s_mission_is_guided_from_its_sheet(world):
    """A job started is its mission; the mission's guide is the live step with Next Step (or Checked at a hold point)
    and Stop; pressing Next Step moves it; stopped, the guide offers Start."""
    from core import trade_session as ts
    from core.mission_guide import guide_for
    from core.trade_actions import reply

    world.trade_session = ts.TradeStore(world, data_dir=world.my_dir)
    said = reply(world, "walk me through building the coop")
    assert "It's in your Missions" in said, said
    mission = next(m for m in world.missions.all_missions() if m.name == "Build: Chicken coop and run")
    guide = guide_for(world, mission)
    assert guide["live"] and guide["step"] == 1 and guide["actions"][0]["kind"] in ("trade.next", "trade.check")
    assert guide["actions"][-1]["kind"] == "trade.stop"
    if guide["actions"][0]["kind"] == "trade.next":
        ACTION_TYPES["trade.next"].execute(world, {})
        assert guide_for(world, mission)["step"] == 2
    reply(world, "stop the job")
    stopped = guide_for(world, mission)
    assert not stopped["live"] and stopped["actions"][0] == {"kind": "trade.start", "label": "Start",
                                                             "params": {"item_id": "chicken_coop"}}
    assert guide_for(world, world.solo) is None  # nothing guides an ordinary mission


def test_the_guide_lists_the_phase_s_steps_and_the_greenhouse_setup_joins_its_project(world, tmp_path, monkeypatch):
    """A live job's guide lists its phase's steps with the current one marked; the greenhouse setup's mission joins
    the one unfinished project with "greenhouse" in its name, and lists its 11 steps."""
    from core import greenhouse_link as gl
    from core import greenhouse_provision as gp
    from core import greenhouse_setup as gs
    from core import trade_session as ts
    from core.mission_guide import guide_for
    from core.trade_actions import reply

    world.trade_session = ts.TradeStore(world, data_dir=world.my_dir)
    reply(world, "walk me through building the coop")
    coop = next(m for m in world.missions.all_missions() if m.name == "Build: Chicken coop and run")
    steps = guide_for(world, coop)["steps"]
    assert steps[0]["current"] and not steps[0]["done"] and all(not s["current"] for s in steps[1:])
    reply(world, "stop the job")

    world.greenhouse_link = gl.GreenhouseLink(world, data_dir=tmp_path / "gh")
    monkeypatch.setattr(gp, "KEY", tmp_path / ".keys" / "node")
    monkeypatch.setattr(gp, "BUNDLE", tmp_path / "bundle")
    monkeypatch.setattr(gp, "platformio", lambda: None)
    gs.reply(world, "let's set up the greenhouse", lambda: None)
    setup = gs.mission(world)
    assert setup.project_id == world.house.project_id
    guide = guide_for(world, setup)
    assert len(guide["steps"]) == 11 and guide["steps"][0]["current"]


def test_by_voice_a_mission_joins_a_project_and_the_project_tells_its_missions(world):
    """set_mission_project and get_project_missions use the same action and records as the pages."""
    from core.assistant_game_actions import _get_project_missions, _set_mission_project

    said = _set_mission_project(world, {"mission": "greenhouse foundation", "project": "greenhouse construction"})
    assert said.endswith("is part of Greenhouse Construction; its progress counts toward it.")
    told = _get_project_missions(world, {"project": "greenhouse construction"})
    assert told.startswith("Greenhouse Construction: ") and "Build the Greenhouse Foundation (active, 0%" in told
    assert _set_mission_project(world, {"mission": "greenhouse foundation", "project": "none"}).endswith(
        "stands on its own now.")
