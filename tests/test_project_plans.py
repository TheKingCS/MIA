"""
tests.test_project_plans
==========================

Plans made together, then missions (core/project_plans.py, core/garden_plans.py, T-0060; Zac, 2026-11-22: builds and
gardens both together): a garden's dates worked out from his frosts, plants and soil worked out in code, a build from
the Library's shelf walked by Trade Master, a draft changed, then confirmed into one project and a mission a stage,
guided step by step, and the whole of it taken back by one Undo.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from core import garden_plans as gp
from core.actions import ActionCenter, ActionError
from core.plan_library import PlanLibrary
from core.project_plans import ProjectPlanBook
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A small real world with the plans shelf, the plans made together and the action center."""
    context = build_world(tmp_path, monkeypatch)
    context.plans = PlanLibrary(context, data_dir=context.home_dir, files_dir=tmp_path / "plan_files")
    context.project_plans = ProjectPlanBook(context, data_dir=context.home_dir)
    context.actions = ActionCenter()
    return context


def _do(context, action_kind, **params):
    """Proposes and approves one action as the person; its result line."""
    card = context.actions.propose(context, action_kind, params)
    done = context.actions.approve(context, card.proposal_id)
    assert done.status == "executed", done.result
    return done.result


def test_a_crops_dates_come_from_his_frosts_and_a_tender_one_too_late_is_said():
    """Tomatoes 7 weeks before an April 20 last frost, out a week after, harvest 75 days on; too late is warned."""
    s = gp.schedule(gp.CROPS["tomato"], date(2027, 4, 20), date(2027, 10, 10))
    assert s["start_indoors"] == date(2027, 3, 2) and s["out"] == date(2027, 4, 27) and s["how"] == "transplant"
    assert s["harvest"] == date(2027, 7, 11) and not s["warning"]
    late = gp.schedule(gp.CROPS["pumpkin"], date(2027, 6, 1), date(2027, 9, 1))
    assert late["how"] == "sow" and "may not ripen" in late["warning"]
    assert gp.schedule(gp.CROPS["spinach"], date(2027, 4, 20))["out"] == date(2027, 3, 9)  # six weeks before


def test_plants_and_soil_are_worked_out_in_code():
    """Square-foot counts, and a 4 by 8 by 12 inch bed's soil."""
    assert gp.plants_for(gp.CROPS["carrot"], 4) == 64 and gp.plants_for(gp.CROPS["pumpkin"], 3) == 1
    assert gp.bed_soil(8, 4, 12) == {"cubic_feet": 32.0, "cubic_yards": 1.19, "bags_1_5": 22}
    assert gp.parse_day("April 20", 2027) == date(2027, 4, 20) == gp.parse_day("04-20", 2027)
    assert gp.parse_day("whenever", 2027) is None


def test_a_garden_draft_asks_for_the_last_frost_and_is_worked_out_once_given(world):
    """No frost date: a question, never a guess. Given: its stages in order, each step dated."""
    params = {"kind": "garden", "beds": [{"name": "Bed 1", "length_ft": 8, "width_ft": 4, "depth_in": 12}],
              "crops": [{"crop": "tomatoes", "bed": "Bed 1", "sqft": 8}, {"crop": "carrot", "bed": "Bed 1"}]}
    with pytest.raises(ActionError, match="last spring frost"):
        world.actions.propose(world, "projectplan.draft", params)
    _do(world, "projectplan.draft", **params, last_frost="April 20", first_frost="October 10")
    plan = world.project_plans.listed()[0]
    names = [s["name"] for s in plan.stages]
    assert names == ["Prepare the beds", "Start seeds indoors", "Harden off and transplant", "Sow outside",
                     "Care through the season", "Harvest"]
    assert "32.0 cubic feet" in plan.stages[0]["steps"][1]["do"] and plan.stages[1]["steps"][0]["when"].startswith("the week of March")
    assert any("seed packet" in w for w in plan.warnings) and world.config.get("garden.last_frost") == "April 20"


def test_a_build_is_its_shelf_plans_materials_then_trade_masters_phases(world):
    """The raised bed at 8 by 4: a materials stage, then the walkthrough's phases with their reasons and checks."""
    from core import trades

    trades._loaded()
    job = next(j for j in trades.JOBS.values() if j.plan == "raised-bed")
    _do(world, "projectplan.draft", kind="build", shelf_plan="raised-bed", sizes={"length_ft": 8, "width_ft": 4})
    plan = world.project_plans.listed()[0]
    assert plan.job == job.id and plan.stages[0]["name"] == "Get the materials"
    assert [s["name"] for s in plan.stages[1:]] == [p.name for p in job.phases]
    assert plan.stages[1]["steps"][0]["why"] == job.phases[0].steps[0].why


def test_confirming_makes_the_project_and_a_mission_a_stage_and_one_undo_takes_it_all_back(world):
    """Nothing is made before Confirm; then one project, a mission per stage, each step an objective; Undo removes
    them and the plan is a draft again."""
    from core.undo_log import undo_last

    _do(world, "projectplan.draft", kind="garden", beds=[{"name": "Bed 1", "length_ft": 4, "width_ft": 4}],
        crops=["lettuce", "radish"], last_frost="April 20")
    plan = world.project_plans.listed()[0]
    assert not world.missions.all_missions() and not world.projects.all_projects()
    said = _do(world, "projectplan.confirm", plan_id=plan.plan_id)
    plan = world.project_plans.get(plan.plan_id)
    missions = [world.missions.get_mission(m) for m in plan.mission_ids]
    assert plan.status == "confirmed" and len(missions) == len(plan.stages) and "missions" in said
    assert all(m.project_id == plan.project_id for m in missions)
    assert [o.description.split(" (")[0] for o in missions[0].objectives] == \
        [s["do"].split(" (")[0] for s in plan.stages[0]["steps"]]
    with pytest.raises(ActionError, match="already confirmed"):
        world.actions.propose(world, "projectplan.confirm", {"plan_id": plan.plan_id})
    undo_last(world, world.me.profile_id)
    assert not world.missions.all_missions() and not world.projects.all_projects()
    assert world.project_plans.get(plan.plan_id).status == "draft"


def test_a_missions_guide_is_its_next_step_with_why_watch_and_check(world, monkeypatch):
    """The plan guide: the first undone step, Done for it, and what the library says (looked up once)."""
    from core import mission_guide

    asked = []
    monkeypatch.setattr("core.offline_library.passages",
                        lambda lib, q, keep=4: asked.append(q) or [{"pack": "Gardening", "article": "Radish", "text": "x"}])
    world.reference_library = object()
    _do(world, "projectplan.draft", kind="garden", beds=[{"name": "Bed 1", "length_ft": 4, "width_ft": 4}],
        crops=["radish"], last_frost="April 20")
    plan = world.project_plans.listed()[0]
    _do(world, "projectplan.confirm", plan_id=plan.plan_id)
    plan = world.project_plans.get(plan.plan_id)
    mission = world.missions.get_mission(plan.mission_ids[0])
    guide = mission_guide.guide_for(world, mission)
    assert guide["source"] == "plan" and guide["step"] == 1 and guide["why"] and guide["check"]
    assert guide["actions"][0]["kind"] == "objective.tick" and guide["library"][0]["pack"] == "Gardening"
    _do(world, "objective.tick", mission_id=mission.mission_id, index=0)
    again = mission_guide.guide_for(world, world.missions.get_mission(mission.mission_id))
    assert again["step"] == 2 and len(asked) == 1


def test_a_draft_changes_and_a_stage_left_out_is_left_out_until_put_back(world):
    """change: new crops worked out again; leave_out and put_back; drop lets it go."""
    _do(world, "projectplan.draft", kind="garden", beds=[{"name": "Bed 1", "length_ft": 4, "width_ft": 4}],
        crops=["radish"], last_frost="April 20")
    plan = world.project_plans.listed()[0]
    _do(world, "projectplan.change", plan_id=plan.plan_id, leave_out="Care through the season", crops=["kale"])
    plan = world.project_plans.get(plan.plan_id)
    assert "Care through the season" not in [s["name"] for s in plan.stages] and plan.crops[0]["crop"] == "kale"
    _do(world, "projectplan.change", plan_id=plan.plan_id, put_back="Care through the season")
    assert "Care through the season" in [s["name"] for s in world.project_plans.get(plan.plan_id).stages]
    _do(world, "projectplan.drop", plan_id=plan.plan_id)
    assert not world.project_plans.listed()


def test_confirming_is_his_yes_and_drafting_is_within_a_grant():
    """The tiers in the Knowledge app's manifest."""
    tiers = json.loads((Path(__file__).resolve().parent.parent / "apps" / "knowledge" / "manifest.json")
                       .read_text(encoding="utf-8"))["capabilities"]["tiers"]
    assert tiers["projectplan.confirm"] == tiers["confirm_plan"] == "act_with_approval"
    assert tiers["projectplan.draft"] == tiers["plan_with_me"] == "act_within_grant" and tiers["show_plans"] == "observe"
