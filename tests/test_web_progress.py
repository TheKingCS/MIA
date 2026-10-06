"""
DEC-0017/0018 (2026-10-06), H-0013: Missions, Skills and Character on the
web. The pages (core/web_progress.py) and every change as an action kind
(core/mission_actions.py), each proposed, approved, recorded and
undoable, with rewards going to the person who approved it.
"""

from datetime import date

import pytest

from core.actions import ACTION_TYPES, ActionCenter, ActionError
from core.child_accounts import make_child
from core.personal_data import ScopedView
from core.web_progress import character_page, missions_page, skills_page
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def run(context, kind, actions=None, **params):
    centre = actions or context.actions
    proposal = centre.propose(context, kind, params)
    return proposal, centre.approve(context, proposal.proposal_id)


def as_person(world, profile):
    """The phone's view of one person (core.personal_data.view_for)."""
    return ScopedView(world, (), profile_id=profile.profile_id)


def xp(world, profile) -> int:
    return world.profiles.get_profile(profile.profile_id).total_xp


def test_a_mission_from_start_to_finish(world):
    proposal, _ = run(world, "mission.add", name="Fix the fence", difficulty="HARD", reward_xp="50", reward_credits="5")
    assert proposal.summary == "Add the mission Fix the fence: difficulty HARD, XP 50, credits 5"
    mission = world.missions.all_missions()[0]
    assert mission.profile_id == world.me.profile_id  # the person's own, not the household's

    run(world, "objective.add", mission_id=mission.mission_id, description="Buy posts", target="1")
    proposal, _ = run(world, "objective.add", mission_id=mission.mission_id, description="Set posts", target="4")
    assert proposal.summary == "Add to Fix the fence: Set posts (×4)"
    proposal, _ = run(world, "objective.tick", mission_id=mission.mission_id, index="1")
    assert proposal.summary == "Set posts: 0 → 1 of 4"

    [card] = missions_page(world, TODAY)["active"]
    assert (card["done"], card["total"], card["percent"], card["ready"]) == (0, 2, 0, False)
    assert card["objectives"][1]["progress"] == 1 and card["difficulty"] == "HARD"

    run(world, "mission.skill_reward", mission_id=mission.mission_id, skill_id="strength", xp="15")
    proposal, done = run(world, "mission.complete", mission_id=mission.mission_id)
    assert proposal.summary == "Complete the mission Fix the fence (0 of 2 objectives done): +50 XP, +5 credits, +15 Strength"
    assert xp(world, world.me) == 50 and world.skills.get_progress(world.me.profile_id, "strength").total_xp == 15
    page = missions_page(world, TODAY)
    assert page["completed"][0]["name"] == "Fix the fence" and page["me"]["total_xp"] == 50

    world.actions.undo(world, done.proposal_id)
    assert world.missions.get_mission(mission.mission_id).status == "active" and xp(world, world.me) == 0
    assert world.skills.get_progress(world.me.profile_id, "strength").total_xp == 0


def test_giving_up_and_picking_back_up_never_pays_twice(world):
    mission = world.missions.add_mission("Read a book", reward_xp=30)
    run(world, "mission.complete", mission_id=mission.mission_id)
    proposal, _ = run(world, "mission.reopen", mission_id=mission.mission_id)
    assert "won't come twice" in proposal.summary
    proposal, _ = run(world, "mission.complete", mission_id=mission.mission_id)
    assert proposal.summary.endswith("its rewards were already given") and xp(world, world.me) == 30

    other = world.missions.add_mission("Learn to juggle")
    proposal, _ = run(world, "mission.abandon", mission_id=other.mission_id, reason="Too hard for now")
    assert proposal.summary == "Give up on Learn to juggle for now (too hard for now)"
    assert world.missions.get_mission(other.mission_id).abandon_reason == "too_hard"
    assert missions_page(world, TODAY)["set_aside"][0]["abandon_reason"] == "Too hard for now"
    with pytest.raises(ActionError, match="already abandoned"):
        world.actions.propose(world, "mission.complete", {"mission_id": other.mission_id})


def test_rewards_go_to_whoever_approved_it_on_their_phone(world):
    """The PC has Robin signed in; Sam completes a mission from their phone."""
    sam = as_person(world, world.other)
    mission = world.missions.add_mission("Sam's run", reward_xp=40, profile_id=world.other.profile_id)
    run(sam, "mission.complete", mission_id=mission.mission_id)
    assert xp(world, world.other) == 40 and xp(world, world.me) == 0
    assert world.profiles.get_active_profile().profile_id == world.me.profile_id
    # and Robin never sees, or acts on, Sam's own mission
    assert all(c["id"] != mission.mission_id for c in missions_page(world, TODAY)["completed"])
    with pytest.raises(ActionError, match="isn't there"):
        world.actions.propose(world, "mission.reopen", {"mission_id": mission.mission_id})


def test_an_objective_that_counts_itself_cannot_be_ticked(world):
    mission = world.missions.add_mission("Plumbing")
    world.missions.add_objective(mission.mission_id, "Call them", "task_done", 1.0)
    with pytest.raises(ActionError, match="counts itself"):
        world.actions.propose(world, "objective.tick", {"mission_id": mission.mission_id, "index": 0})
    assert missions_page(world, TODAY)["active"][0]["objectives"][0]["counts_itself"]


def test_skills_page(world):
    world.skills.add_skill_xp(world.me.profile_id, "strength", 35)
    page = skills_page(world, TODAY)
    strength = next(s for s in page["skills"] if s["id"] == "strength")
    assert (strength["level"], strength["xp_into_level"], strength["xp_for_level"]) == (2, 15, 40)
    assert strength["status"] == "practiced" and strength["this_week"] == 35
    locked = next(s for s in page["skills"] if s["needs"])
    assert not locked["unlocked"] and locked["status"] == "locked"
    assert page["counts"]["touched"] == 1 and page["focus"]["id"] == "strength"
    assert {c["name"] for c in page["categories"]} == set(world.skills.categories())
    assert next(c for c in page["categories"] if c["name"] == "Body")["trend"] == "growing"


def test_character_and_prestige(world):
    from core.leveling import XP_PER_PRESTIGE_CYCLE
    from core.rewards_manager import RewardsManager

    world.rewards = RewardsManager(world)
    page = character_page(world, TODAY)
    assert page["me"]["name"] == "Robin" and page["stats"] and page["collection"] == []
    with pytest.raises(ActionError, match="level 100"):
        world.actions.propose(world, "character.prestige", {})
    world.profiles.add_xp(world.me.profile_id, XP_PER_PRESTIGE_CYCLE)
    assert character_page(world, TODAY)["me"]["can_prestige"]
    proposal, done = run(world, "character.prestige")
    assert proposal.summary.startswith("Prestige: start again at level 1 with a green badge")
    page = character_page(world, TODAY)
    assert page["me"]["prestige_tier"] == 1 and page["emblems"] == [{"name": "Prestige 1", "color": "green"}]
    world.actions.undo(world, done.proposal_id)
    assert world.profiles.get_profile(world.me.profile_id).prestige_tier == 0


def test_starting_a_pathway(world, tmp_path, monkeypatch):
    import core.pathway_manager as pathway_module
    from core.pathway_manager import PathwayManager

    monkeypatch.setattr(pathway_module, "_PROGRESS_FILE", tmp_path / "pathway_progress.json")
    world.pathways = PathwayManager(world)
    pathway = world.pathways.all_pathways()[0]
    proposal, _ = run(world, "pathway.start", pathway_id=pathway.pathway_id)
    assert proposal.summary.startswith(f"Start the pathway {pathway.name}: first, {pathway.steps[0].name}")
    [card] = [c for c in missions_page(world, TODAY)["active"] if c["pathway"]]
    assert card["pathway"].startswith(f"{pathway.name} · step 1 of") and card["from_mia"]
    with pytest.raises(ActionError, match="already on"):
        world.actions.propose(world, "pathway.start", {"pathway_id": pathway.pathway_id})
    skill_row = next(s for s in skills_page(world, TODAY)["skills"] if s["id"] == pathway.skill_id)
    assert next(p for p in skill_row["pathways"] if p["id"] == pathway.pathway_id)["status"] == "active"


def test_a_child_plays_too_but_cannot_delete_missions(world):
    mission = world.missions.add_mission("Tidy room", reward_xp=10)
    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert world.actions.propose(world, "mission.complete", {"mission_id": mission.mission_id}).status == "proposed"
    with pytest.raises(ActionError, match="grown-ups"):
        world.actions.propose(world, "mission.delete", {"mission_id": mission.mission_id})
    assert not ACTION_TYPES["mission.delete"].child_ok


def test_the_endpoints(world):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    for path in ("/api/missions", "/api/skills", "/api/character"):
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)
        assert response.json()["me"]["name"] == "Robin"
