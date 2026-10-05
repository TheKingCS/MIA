"""
Life State v2 (core/context_assembler.py), Engine Phase 1 step 3,
2026-10-05: the whole picture as data, computed from the stores, the
life-event history and the links. No hand-written prose in the path.
"""

import json
from datetime import date, timedelta

import pytest

from core.app_context import AppContext
from core.child_accounts import make_child
from core.config_manager import ConfigManager
from core.context_assembler import (STATUSES, assemble_life_state_v2, describe_life_state_v2,
                                    monthly_equivalent)
from core.event_bus import EventBus
from core.gamification import SkillWeight
from tests.engine_world import build_world

SECTIONS = ("finances", "properties", "assets", "kitchen", "workout", "projects", "due", "missions_and_skills", "recent_wins", "friction",
            "goals", "links", "opportunities")
TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    return build_world(tmp_path, monkeypatch)


def test_every_section_says_what_it_is_and_where_from(world):
    state = assemble_life_state_v2(world)
    assert state["version"] == 2 and state["person"]["name"] == "Robin" and state["person"]["child"] is False
    for name in SECTIONS:
        assert state[name]["status"] in STATUSES and state[name]["source"], name
    assert state["opportunities"]["status"] == "PLANNED"  # MIA's reasoning over this is Phase 2
    json.dumps(state)  # plain data all the way down


def test_monthly_equivalents():
    assert monthly_equivalent(500, "weekly") == 2166.67 and monthly_equivalent(1200, "yearly") == 100.0
    assert monthly_equivalent(100, "biweekly") == 216.67 and monthly_equivalent(50, None) == 0.0


def test_the_monthly_plan_and_its_gap(world):
    world.budget.add_income_source("Pay", 500.0, TODAY.isoformat(), recurrence="weekly")
    world.budget.add_bill("Loan", 1000.0, (TODAY + timedelta(days=20)).isoformat(), recurrence="monthly")
    world.budget.add_bill("Insurance", 1200.0, (TODAY + timedelta(days=200)).isoformat(), recurrence="yearly")
    world.budget.add_debt("Card", 900.0, 20.0, minimum_payment=100.0)
    plan = assemble_life_state_v2(world)["finances"]["monthly_plan"]
    assert (plan["expected_income"], plan["bills"], plan["debt_minimums"], plan["gap"]) == (2166.67, 1100.0, 100.0,
                                                                                         966.67)
    world.budget.add_bill("Big", 2000.0, (TODAY + timedelta(days=9)).isoformat(), recurrence="monthly")
    state = assemble_life_state_v2(world)
    assert state["finances"]["monthly_plan"]["gap"] < 0
    assert any(f["kind"] == "money_gap" for f in state["friction"]["items"])


def test_paying_a_bill_moves_it_from_due_to_wins(world):
    """Kickoff acceptance #2: a bill_paid event, and the bill leaves the due views, with no UI involved."""
    bill = world.budget.add_bill("Electric", 127.87, (TODAY - timedelta(days=2)).isoformat(), recurrence="monthly")
    before = assemble_life_state_v2(world)
    assert any(i["title"] == "Pay Electric" and i["when"] == "overdue" for i in before["due"]["items"])
    assert any(f["kind"] == "overdue" and "Electric" in f["text"] for f in before["friction"]["items"])
    world.budget.mark_bill_paid(bill.bill_id)
    after = assemble_life_state_v2(world)
    assert not any("Electric" in i["title"] for i in after["due"]["items"])
    assert not any("Electric" in f["text"] for f in after["friction"]["items"])
    assert after["recent_wins"]["counts"] == {"bill_paid": 1}
    assert after["recent_wins"]["latest"][0]["summary"].startswith("Paid Electric")


def test_a_mission_trains_its_skills_with_evidence(world):
    """Kickoff acceptance #3: completing a mission logs evidence for each linked skill."""
    mission = world.missions.add_mission("Plan the week", reward_xp=10,
                                         skill_rewards=[SkillWeight("organization", 15)])
    world.missions.update_mission(mission.mission_id, status="completed")
    # Missions are device-level: their history is in data/, which on a
    # device is also the first household's folder.
    world.life_events.data_dir = world.device_dir
    state = assemble_life_state_v2(world)
    assert state["recent_wins"]["counts"].get("mission_completed") == 1
    assert any(e["type"] == "skill_evidence" and "skill:organization" in e["refs"]
               for e in state["recent_wins"]["latest"])
    assert world.skills.xp_earned_between(world.me.profile_id, "organization", TODAY,
                                         TODAY + timedelta(days=1)) == 15


def test_projects_goals_and_what_waits_on_what(world):
    lot = world.real_estate.add_property("Vacant lot", property_type="Land", current_value=80000.0)
    goal = world.intents.add_intent("Grow our own food", primary=True)
    greenhouse = world.projects.add_project("Greenhouse", intent_id=goal.intent_id)
    solar = world.projects.add_project("Solar")
    world.tasks.add_task(greenhouse.project_id, "Dig the pit")
    world.links.add(f"project:{greenhouse.project_id}", "DEPENDS_ON", f"property:{lot.property_id}")
    world.links.add(f"project:{solar.project_id}", "DEPENDS_ON", f"project:{greenhouse.project_id}")
    state = assemble_life_state_v2(world)
    green = next(p for p in state["projects"]["items"] if p["name"] == "Greenhouse")
    assert green["supports"] == "Grow our own food" and green["waiting_on"] == ["Vacant lot"]
    assert green["tasks_open"] == 1
    assert state["goals"]["items"][0]["supported_by"] == ["Greenhouse"]
    assert state["goals"]["chains"] == [["Vacant lot", "Greenhouse", "Solar"]]
    assert state["properties"]["items"][0]["equity"] == 80000.0
    assert state["links"]["stated"] == 2
    text = describe_life_state_v2(state)
    assert "Vacant lot → Greenhouse → Solar" in text and "Greenhouse waits on Vacant lot" in text


def test_a_child_sees_no_money_or_property(world):
    world.budget.add_bill("Electric", 120.0, TODAY.isoformat())
    world.real_estate.add_property("Rental A")
    kid = world.profiles.create_profile("Ari", make_active=False)
    make_child(world, kid.profile_id, [world.me.profile_id])
    world.profiles.set_active_profile(kid.profile_id)
    state = assemble_life_state_v2(world)
    assert state["person"]["child"] is True
    assert state["finances"]["hidden"] and state["properties"]["items"] == []
    assert not any("Electric" in i["title"] for i in state["due"]["items"])


def test_missing_stores_say_planned_instead_of_failing(tmp_path, monkeypatch):
    import core.config_manager as config_module

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    bare = AppContext(config=ConfigManager(), events=EventBus())
    state = assemble_life_state_v2(bare)
    assert state["finances"]["status"] == "PLANNED" and state["properties"]["status"] == "PLANNED"
    assert state["projects"]["status"] == "PLANNED" and state["person"]["profile_id"] is None
    json.dumps(state)


def test_what_s_going_on_with_me_uses_v2(world):
    from core.application import MIAApplication

    world.workout.add_session(duration_minutes=30)
    reply = MIAApplication._action_get_life_state(world, {})
    assert reply.startswith("This week: 1 workouts.")


def test_assets_kitchen_and_workout_for_muse_h_0004(world):
    """H-0004: Garage, Kitchen and Workout are in the read model."""
    truck = world.maintenance.add_asset("Truck", "Vehicle", owner_profile_id=world.me.profile_id)
    world.maintenance.add_task(truck.asset_id, "Oil change", interval_days=90,
                               last_completed=(TODAY - timedelta(days=100)).isoformat())
    world.maintenance.add_asset("Mower", "Power Equipment")
    world.kitchen.add_pantry_item("Milk", 1, "gal", expiration_date=(TODAY + timedelta(days=1)).isoformat())
    world.kitchen.add_grocery_item("Eggs", 12)
    chili = world.kitchen.add_recipe("Chili")
    world.kitchen.log_meal(chili.recipe_id)
    template = world.workout.add_template("Beginner full body")
    world.workout.add_session(template_id=template.template_id, duration_minutes=30)
    world.workout.add_session(duration_minutes=15, date_str=(TODAY - timedelta(days=20)).isoformat())
    state = assemble_life_state_v2(world)
    truck_item = next(a for a in state["assets"]["items"] if a["name"] == "Truck")
    assert (truck_item["owner"], truck_item["mine"], truck_item["tasks_overdue"]) == ("Robin", True, 1)
    assert truck_item["next_task"] == {"title": "Oil change", "days": -10}
    mower = next(a for a in state["assets"]["items"] if a["name"] == "Mower")
    assert mower["owner"] is None and mower["next_task"] is None  # the whole household's, no upkeep yet
    kitchen = state["kitchen"]
    assert kitchen["expiring_soon"] == [{"name": "Milk", "days": 1}]
    assert kitchen["grocery_list"] == [{"name": "Eggs", "checked": False}]
    assert kitchen["recent_meals"] == [{"recipe": "Chili", "date": TODAY.isoformat()}]
    workout = state["workout"]
    assert (workout["sessions"], workout["minutes"]) == (1, 30)  # the old one is outside the 7 days
    assert workout["last_session"]["template"] == "Beginner full body"
    # A child sees the kitchen and their workouts, not the household's vehicles.
    kid = world.profiles.create_profile("Ari", make_active=False)
    make_child(world, kid.profile_id, [world.me.profile_id])
    world.profiles.set_active_profile(kid.profile_id)
    child = assemble_life_state_v2(world)
    assert child["assets"]["hidden"] and child["assets"]["items"] == []
    assert child["kitchen"]["status"] == "REAL"
