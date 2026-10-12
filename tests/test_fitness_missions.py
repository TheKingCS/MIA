"""
The fitness plan as missions (core/fitness_missions.py, DEC-0020, H-0026):
made once per day and week from the plan, kept in step with the logs
(the logs are the truth), ticked through the logs, completing themselves,
and letting a missed day go quietly (DEC-0014). Placeholder plan values.
"""

from datetime import date, timedelta

import pytest

from core import fitness_missions as fx
from core.actions import ActionCenter
from tests.engine_world import build_world

MON = date(2026, 10, 12)

PLAN = {
    "targets": {"protein_g": 180, "workouts_per_week": 3},
    "training": {"days": ["Mon", "Wed", "Fri"], "rotation": [
        {"name": "Push", "exercises": [{"name": "Push-ups", "sets": 3, "reps": "8-12"},
                                       {"name": "Pike push-ups", "sets": 3, "reps": 8},
                                       {"name": "L-sit", "sets": 3, "hold_seconds": 15}]},
        {"name": "Pull", "exercises": [{"name": "Pull-ups", "sets": 4, "reps": 6}]},
        {"name": "Legs + carry", "exercises": []}]},
    "skill_tree": [{"skill": "Handstand", "daily_minutes": 12,
                    "practice": ["Wrist prep", "Wall work", "Frog pose", "Tuck attempts"]}],
    "meals": {"packed_lunch": True, "prep_day": "Sun"},
}


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.fitness.update_plan(PLAN)
    return context


def by_kind(world, today=MON):
    return {fx._kind(m): m for m in fx.ensure(world, today)}


def test_the_plan_makes_its_missions_once(world):
    missions = by_kind(world)
    assert set(missions) == {"training", "skill:handstand", "protein", "lunch", "prep", "week_workouts"}
    training = missions["training"]
    assert training.name == "Training: Push" and training.mission_type == "DAILY MISSION"
    assert [o.description for o in training.objectives] == ["Push-ups 3×8-12", "Pike push-ups 3×8", "L-sit 3×15 s"]
    assert training.profile_id == world.me.profile_id and training.assigned_by == "mia"
    assert [o.description for o in missions["skill:handstand"].objectives][0] == "Wrist prep"
    count = len(world.missions.all_missions())
    by_kind(world)
    assert len(world.missions.all_missions()) == count  # idempotent
    tuesday = by_kind(world, MON + timedelta(days=1))
    assert "training" not in tuesday  # a rest day: no training mission, and no miss either


def test_logs_drive_the_missions(world):
    missions = by_kind(world)
    world.fitness.complete_step(0, MON)
    world.fitness.log_food("lunch", "Chicken and rice", {"protein_g": 41}, on=MON.isoformat())
    fx.sync(world, MON)
    training, protein = world.missions.get_mission(missions["training"].mission_id), world.missions.get_mission(missions["protein"].mission_id)
    assert [o.progress for o in training.objectives] == [1, 0, 0]
    assert protein.objectives[0].progress == 41
    world.fitness.complete_training(MON)  # "workout complete"
    fx.sync(world, MON)
    assert world.missions.get_mission(training.mission_id).status == "completed"
    assert world.missions.get_mission(missions["week_workouts"].mission_id).objectives[0].progress == 1


def test_a_tap_logs_it_first_then_the_mission_follows(world):
    missions = by_kind(world)
    lunch = missions["lunch"]
    proposal = world.actions.propose(world, "objective.tick", {"mission_id": lunch.mission_id, "index": "0"})
    assert proposal.summary == "Done: Take a packed lunch"
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed" and done.result == "Packed lunch: done."
    assert world.fitness.has_habit("lunch", date.today().isoformat()) or world.fitness.has_habit("lunch", MON.isoformat())


def test_ticking_training_steps_finishes_the_day(world):
    training = by_kind(world)["training"]
    for index in range(3):
        fx.tick(world, world.missions.get_mission(training.mission_id), index, MON)
    assert world.missions.get_mission(training.mission_id).status == "completed"
    assert world.fitness.today_training(MON)["done"] is True
    assert world.fitness.today_training(MON + timedelta(days=2))["name"] == "Pull"  # the rotation moved on


def test_skill_practice_and_protein_by_tap(world):
    missions = by_kind(world)
    skill = missions["skill:handstand"]
    for index in range(4):
        fx.tick(world, world.missions.get_mission(skill.mission_id), index, MON)
    assert world.missions.get_mission(skill.mission_id).status == "completed"
    assert {s["step"] for s in world.fitness.skill_sessions("handstand")} == {"Wrist prep", "Wall work", "Frog pose", "Tuck attempts"}
    fx.tick(world, world.missions.get_mission(missions["protein"].mission_id), 0, MON)  # "hit my protein"
    assert world.missions.get_mission(missions["protein"].mission_id).status == "completed"
    assert world.fitness.day_totals(MON.isoformat())["totals"]["protein_g"] is None  # no food was invented


def test_a_missed_day_goes_quietly(world):
    yesterday = by_kind(world, MON)["lunch"]
    today = by_kind(world, MON + timedelta(days=1))
    assert world.missions.get_mission(yesterday.mission_id) is None  # gone, not "failed"
    assert today["lunch"].mission_id != yesterday.mission_id
    assert today["prep"].occurrence_key == by_kind(world, MON)["prep"].occurrence_key  # this week's prep stays


def test_completing_grants_the_missions_rewards(world):
    before = world.profiles.get_profile(world.me.profile_id).total_xp
    lunch = by_kind(world)["lunch"]
    fx.tick(world, world.missions.get_mission(lunch.mission_id), 0, MON)
    assert world.profiles.get_profile(world.me.profile_id).total_xp == before + 10


# ---------------------------------------------------------------- say it (core/quick_commands.py)

from core.quick_commands import handle, parse  # noqa: E402


@pytest.mark.parametrize("said, kind", [
    ("workout complete", "fitness.training_done"), ("Workout's done!", "fitness.training_done"),
    ("step one of today's workout complete", "fitness.step"), ("finished my pull-ups", "fitness.step"),
    ("today's lunch complete", "fitness.habit"), ("ate breakfast", "fitness.food"),
    ("week's meal plans complete", "fitness.habit"), ("meal prep done", "fitness.habit"),
    ("I weigh 182.4", "fitness.weigh_in"), ("had 40 g of protein", "fitness.protein"),
    ("handstand 45 seconds", "fitness.skill"), ("undo that", "undo"),
])
def test_plain_words_become_actions(said, kind):
    plan = {"meals": {"packed_lunch": True}, "skill_tree": [{"skill": "Handstand"}]}
    training = {"exercises": [{"name": "Pull-ups"}]}
    assert parse(said, plan, training)[0] == kind


@pytest.mark.parametrize("said", ["how was my workout?", "what should I eat for dinner",
                                  "I want to plan my meals for the week", "tell me about protein"])
def test_questions_and_conversation_go_to_the_model(said):
    assert parse(said, {}, None) is None


def test_saying_it_logs_everywhere_and_undo_takes_it_back(world, monkeypatch):
    import core.fitness_missions as fxm

    real = fxm.date

    class Monday(real):
        @classmethod
        def today(cls):
            return MON

    for module in (fxm, __import__("core.fitness_manager", fromlist=["x"]), __import__("core.fitness_actions", fromlist=["x"])):
        monkeypatch.setattr(module, "date", Monday)
    missions = by_kind(world)
    reply = handle(world, "step one of today's workout complete")
    assert reply.startswith("Step 1 done. 2 to go.") and "undo that" in reply
    assert world.missions.get_mission(missions["training"].mission_id).objectives[0].progress == 1
    assert handle(world, "workout complete").startswith("Push done")
    assert world.missions.get_mission(missions["training"].mission_id).status == "completed"
    assert handle(world, "I weigh 182.4").startswith("Logged 182.4 lb")
    assert world.fitness.weigh_ins()[-1]["weight"] == 182.4
    assert handle(world, "undo that") == "Undone."
    assert world.fitness.weigh_ins() == []
    assert handle(world, "what's for dinner?") is None
