"""
"Paste a plan" (core/plan_import.py, 2026-10-14): a whole plan and its
recipes as text, the way a chat writes it, into MIA in one undoable
action. Placeholder values only (DEC-0002).
"""

from datetime import date

import pytest

from core.actions import ActionCenter, ActionError
from core.plan_import import parse
from tests.engine_world import build_world

PLAN = """
## GOALS
- Protein: 170 g a day
- Calories: 2,300
- Goal weight: 175 lb by 2027-03-01
- Workouts a week: 3
- Weigh-in days: Mon, Thu

## TRAINING
Days: Mon, Wed, Fri
Day: Push
1. Dips 3x8
2. Pike push-ups 3x10
3. L-sit 3x20s
Training day: Pull
- Pull-ups 5x5
- Dead hang 45s

## SKILL: Handstand (12 min a day)
Drills: Wrist prep, Wall walks, Kick-ups
1. Wall hold 60s
2. 30s chest-to-wall hold
3. Freestanding 10s

## MILESTONES
- [ ] 60 s wall handstand
- [ ] 15 strict pull-ups

## MEALS
Packed lunch: yes
Meal prep: Sunday
Diet: high protein
Allergies: peanuts
Don't eat: none
Lunch rotation: Turkey chili

## RECIPE: Turkey chili
Category: Lunch
Servings: 6
Prep: 15 min
Cook: 1 hr
Ingredients:
- 2 lb ground turkey
- 1 (10 oz) can Rotel
- Salt: to taste
Steps:
1. Brown the turkey.
2. Simmer 45 minutes.

Some chatty closing line.
"""


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def test_reading_a_plan_written_in_a_chat():
    found = parse(PLAN)
    plan = found["plan"]
    assert plan["targets"] == {"protein_g": "170", "calories": "2300", "target_weight": "175", "target_date": "2027-03-01",
                               "workouts_per_week": "3", "weigh_in_days": "Mon, Thu"}
    assert plan["units"] == "lb" and plan["training"]["days"] == "Mon, Wed, Fri"
    assert [d["name"] for d in plan["training"]["rotation"]] == ["Push", "Pull"]
    assert plan["training"]["rotation"][0]["exercises"] == ["Dips 3x8", "Pike push-ups 3x10", "L-sit 3x20s"]
    skill = plan["skill_tree"][0]
    assert skill["skill"] == "Handstand" and skill["daily_minutes"] == "12"
    assert skill["practice"] == ["Wrist prep", "Wall walks", "Kick-ups"]
    assert skill["steps"] == ["Wall hold 60s", "30s chest-to-wall hold", "Freestanding 10s"]
    assert plan["milestones"] == [{"name": "60 s wall handstand"}, {"name": "15 strict pull-ups"}]
    assert plan["meals"] == {"packed_lunch": True, "prep_day": "Sunday",
                             "preferences": {"diet": "high protein", "allergies": "peanuts", "dislikes": ""}}
    assert found["lunch_rotation"] == ["Turkey chili"]
    recipe = found["recipes"][0]
    assert recipe["name"] == "Turkey chili" and recipe["servings"] == "6" and recipe["cook_time_minutes"] == "60"
    assert recipe["ingredients"] == ["2 lb ground turkey", "1 (10 oz) can Rotel", "Salt: to taste"]
    assert recipe["steps"] == ["Brown the turkey.", "Simmer 45 minutes."]
    assert found["problems"] == ["Some chatty closing line."]


def test_protein_per_pound_is_flagged_not_guessed():
    found = parse("GOALS\nProtein: 1 g per lb of body weight")
    assert "protein_g" not in found["plan"].get("targets", {}) and "daily number" in found["problems"][0]


def test_pasting_a_plan_sets_everything_and_one_undo_takes_it_back(world):
    world.fitness.update_plan({"milestones": [{"name": "60 s wall handstand"}]})
    reached = world.fitness.plan["milestones"][0]["id"]
    world.fitness.complete_milestone(reached, on="2026-10-01")
    old = world.kitchen.add_recipe("Turkey chili", servings=4)
    proposal = world.actions.propose(world, "plan.import", {"text": PLAN})
    assert proposal.summary.startswith("Set from the pasted plan: goals (protein 170 g, 2300 kcal, goal weight 175, 3 workouts a week); "
                                       "2 training days (Push, Pull); skills: Handstand; 2 milestones; meals; update Turkey chili.")
    assert "skipped 1 line" in proposal.summary
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed"
    plan = world.fitness.plan
    assert plan["targets"]["protein_g"] == 170 and plan["training"]["days"] == ["Mon", "Wed", "Fri"]
    assert plan["training"]["rotation"][0]["exercises"][2] == {"name": "L-sit", "sets": 3, "hold_seconds": 20}
    assert plan["meals"]["prep_day"] == "Sun" and plan["meals"]["lunch_rotation"] == [old.recipe_id]
    assert plan["milestones"][0]["done_on"] == "2026-10-01"  # a reached milestone stays reached
    chili = world.kitchen.get_recipe(old.recipe_id)
    assert len(world.kitchen.all_recipes()) == 1 and chili.servings == 6 and chili.cook_time_minutes == 60
    assert [i["name"] for i in chili.ingredients] == ["ground turkey", "Rotel", "Salt: to taste"]
    from core.fitness_missions import _kind, is_fitness

    kinds = {_kind(m) for m in world.missions.all_missions() if is_fitness(m)}
    assert {"skill:handstand", "protein"} <= kinds  # the plan's missions are made at once
    world.actions.undo(world, done.proposal_id)
    assert world.fitness.plan["targets"]["protein_g"] is None
    assert world.kitchen.get_recipe(old.recipe_id).servings == 4


def test_new_recipes_are_added_and_bad_text_is_refused(world):
    world.actions.approve(world, world.actions.propose(world, "plan.import", {
        "text": "RECIPE: Protein oats\nServings: 1\nIngredients:\n1 cup oats\n1 scoop whey protein"}).proposal_id)
    assert [r.name for r in world.kitchen.all_recipes()] == ["Protein oats"]
    with pytest.raises(ActionError, match="couldn't find a plan"):
        world.actions.propose(world, "plan.import", {"text": "hello there"})
    lone = world.actions.propose(world, "plan.import", {"text": "MEALS\nLunch rotation: Mystery stew"})
    assert "Mystery stew by name only" in lone.summary  # a lunch with no recipe yet gets one
    with pytest.raises(ActionError, match="Days are"):
        world.actions.propose(world, "plan.import", {"text": "TRAINING\nDays: Funday"})


def test_the_documented_example_reads_cleanly(world):
    """docs/PLAN_TEXT_FORMAT.md's example is what Muse copies; it must read with nothing skipped."""
    from pathlib import Path

    doc = (Path(__file__).resolve().parent.parent / "docs" / "PLAN_TEXT_FORMAT.md").read_text(encoding="utf-8")
    example = doc.split("```")[1]
    found = parse(example)
    assert found["problems"] == []
    assert [d["name"] for d in found["plan"]["training"]["rotation"]] == ["Push", "Pull", "Legs"]
    proposal = world.actions.propose(world, "plan.import", {"text": example})
    world.actions.approve(world, proposal.proposal_id)
    assert world.fitness.plan["targets"]["protein_g"] == 150 and world.kitchen.all_recipes()[0].name == "Chicken rice bowl"


def test_a_childs_pasted_plan_has_no_goal_weight(world):
    from core.child_accounts import make_child

    make_child(world, world.me.profile_id, [world.other.profile_id])
    with pytest.raises(ActionError, match="Goal weights aren't part of a child's plan"):
        world.actions.propose(world, "plan.import", {"text": "GOALS\nGoal weight: 90 lb"})
    world.actions.approve(world, world.actions.propose(world, "plan.import", {"text": "SKILL: Cartwheel\nOne-handed 5 reps"}).proposal_id)
    assert world.fitness.plan["skill_tree"][0]["skill"] == "Cartwheel"


def test_a_plan_copied_out_of_a_chat_app(world):
    """Zac, 2026-10-16: pasting a plan "did nothing". Text copied from a chat
    comes with bold, emoji headings, code fences, "Day 1:" and "Mon/Tue";
    a lunch name a letter off (a plural) is matched, and one MIA doesn't
    know is a note in the summary, never a refusal of the whole plan."""
    from core.plan_import import normalize, parse

    text = """```
### 🎯 **GOALS**
**Protein:** 150 g
**Weigh-in days:** Mon/Thu

### 🏋️ TRAINING
**Days:** Mon, Tue, Thu, Fri
**Day 1: Pull**
• Pull-ups 4×6
• Rows — 3 x 10
- Squats 3 sets of 8

**MEALS**
Lunch rotation: Egg bowls, Mystery stew

**RECIPE: Egg bowl**
Servings: 4
Ingredients:
- 8 eggs
Steps:
1. Cook it.
```"""
    found = parse(text)
    assert found["plan"]["targets"]["protein_g"] == "150" and found["plan"]["training"]["rotation"][0]["name"] == "Pull"
    assert [r["name"] for r in found["recipes"]] == ["Egg bowl"] and not found["problems"]
    assert "**" not in normalize(text) and "```" not in normalize(text)
    p = world.actions.propose(world, "plan.import", {"text": text})
    assert "Mystery stew by name only" in p.summary and "add 2 recipes (Egg bowl, Mystery stew)" in p.summary
    world.actions.approve(world, p.proposal_id)
    plan = world.fitness.plan
    assert plan["training"]["days"] == ["Mon", "Tue", "Thu", "Fri"] and plan["targets"]["weigh_in_days"] == ["Mon", "Thu"]
    assert [e["name"] for e in plan["training"]["rotation"][0]["exercises"]] == ["Pull-ups", "Rows", "Squats"]
    egg = next(r for r in world.kitchen.all_recipes() if r.name == "Egg bowl")
    stew = next(r for r in world.kitchen.all_recipes() if r.name == "Mystery stew")
    assert stew.category == "Lunch" and not stew.ingredients
    assert plan["meals"]["lunch_rotation"] == [egg.recipe_id, stew.recipe_id]
    # pasting it again updates, never duplicates ("Egg bowls" is "Egg bowl")
    world.actions.approve(world, world.actions.propose(world, "plan.import", {"text": text}).proposal_id)
    assert sorted(r.name for r in world.kitchen.all_recipes()) == ["Egg bowl", "Mystery stew"]


def test_a_plan_pasted_as_one_line():
    from core.plan_import import parse

    found = parse("GOALS Protein: 150 g Calories: 2400 TRAINING Days: Mon, Tue")
    assert found["plan"]["targets"] == {"protein_g": "150", "calories": "2400"}
    assert found["plan"]["training"]["days"] == "Mon, Tue"
