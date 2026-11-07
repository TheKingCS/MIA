"""Cook mode (DEC-0113, core/cooking_session.py and core/cooking_actions.py): one recipe being cooked per person,
step by step, with named timers that keep running across steps, what each step uses, and "I made this" logging the
meal through the kitchen's own action; and all of it by voice (core/assistant_cooking_actions.py) and on the glasses (core/glasses.py)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import cooking_session as cs
from core.actions import ActionError

T0 = datetime(2026, 11, 7, 17, 0, 0)
STEPS = ["Brown the turkey with the onion.", "Stir in the beans, tomatoes and stock.",
         "Simmer for 18 minutes, covered.", "Serve."]
INGREDIENTS = [{"name": "Ground turkey", "quantity": 2, "unit": "lb"}, {"name": "Onion", "quantity": 1, "unit": ""},
               {"name": "Kidney beans", "quantity": 2, "unit": "cans"},
               {"name": "Crushed tomatoes", "quantity": 28, "unit": "oz"},
               {"name": "Chicken stock", "quantity": 2, "unit": "cups"}]


def test_a_step_offers_the_timer_its_own_words_give():
    assert cs.step_timer("Simmer for 18 minutes, covered.") == {"name": "Simmer", "seconds": 1080}
    assert cs.step_timer("Bake 1 hour 10 min")["seconds"] == 4200
    assert cs.step_timer("Roast 20 to 25 minutes until golden")["seconds"] == 1200  # the low end: check early
    assert cs.step_timer("Stir well.") is None


def test_a_step_lists_only_the_ingredients_it_names_with_amounts():
    assert cs.step_uses(STEPS[1], INGREDIENTS) == [{"name": "Kidney beans", "amount": "2 cans"},
                                                  {"name": "Crushed tomatoes", "amount": "28 oz"},
                                                  {"name": "Chicken stock", "amount": "2 cups"}]
    assert [u["name"] for u in cs.step_uses(STEPS[0], INGREDIENTS)] == ["Ground turkey", "Onion"]


def test_the_session_moves_step_by_step_and_refuses_past_either_end():
    s = cs.start("r1", "Turkey Chili", STEPS, T0)
    with pytest.raises(ValueError):
        cs.back(s)
    cs.next_step(s)
    cs.go_to(s, 4)
    assert cs.view(s, T0)["last"] is True
    with pytest.raises(ValueError):
        cs.next_step(s)
    with pytest.raises(ValueError):
        cs.start("r2", "Empty", [], T0)


def test_timers_keep_running_across_steps_and_say_when_done():
    s = cs.start("r1", "Turkey Chili", STEPS, T0)
    cs.add_timer(s, "Simmer", 1080, T0)
    cs.add_timer(s, "Rice", 60, T0)
    cs.next_step(s)
    later = cs.timers_left(s, T0 + timedelta(seconds=90))
    assert [(t["name"], t["done"]) for t in later] == [("Rice", True), ("Simmer", False)]
    assert later[1]["left"] == 990
    cs.cancel_timer(s, "rice")
    assert [t["name"] for t in s.timers] == ["Simmer"]
    with pytest.raises(ValueError):
        cs.add_timer(s, "Forever", 0, T0)


def test_the_store_keeps_one_session_across_a_restart(tmp_path):
    store = cs.CookingStore(SimpleNamespace(), data_dir=tmp_path)
    store.begin("r1", "Turkey Chili", STEPS, T0)
    with pytest.raises(ValueError):
        store.begin("r2", "Something else", STEPS, T0)
    again = cs.CookingStore(SimpleNamespace(), data_dir=tmp_path)
    assert again.live().title == "Turkey Chili"
    again.close()
    assert cs.CookingStore(SimpleNamespace(), data_dir=tmp_path).live() is None


def test_cooking_actions_move_the_session_and_made_logs_through_meal_cook(tmp_path, monkeypatch):
    from core import cooking_actions as ca

    calls = []
    recipe = SimpleNamespace(recipe_id="r1", name="Turkey Chili", locked=False, instructions="\n".join(STEPS),
                             ingredients=INGREDIENTS)
    kitchen = SimpleNamespace(get_recipe=lambda rid: recipe if rid == "r1" else None)
    context = SimpleNamespace(kitchen=kitchen, cooking=cs.CookingStore(SimpleNamespace(), data_dir=tmp_path))
    monkeypatch.setitem(__import__("core.kitchen_actions", fromlist=["KITCHEN_ACTIONS"]).KITCHEN_ACTIONS, "meal.cook",
                        SimpleNamespace(describe=lambda c, p: "I made Turkey Chili today",
                                        execute=lambda c, p: calls.append(p) or "Turkey Chili is in the meal log."))
    A = ca.COOKING_ACTIONS
    assert A["cooking.start"].describe(context, {"recipe_id": "r1"}) == "Start cooking Turkey Chili: 4 steps"
    A["cooking.start"].execute(context, {"recipe_id": "r1"})
    with pytest.raises(ActionError):
        A["cooking.start"].describe(context, {"recipe_id": "r1"})  # already cooking
    A["cooking.next"].execute(context, {})
    view = ca.screen(context)
    assert view["number"] == 2 and [u["name"] for u in view["uses"]][0] == "Kidney beans"
    A["cooking.timer"].execute(context, {"name": "Simmer", "minutes": "18"})
    assert ca.screen(context)["timers"][0]["name"] == "Simmer"
    assert A["cooking.made"].execute(context, {}) == "Turkey Chili is in the meal log."
    assert calls == [{"recipe_id": "r1"}]
    assert ca.screen(context) is None


def test_a_recipe_is_found_by_the_words_said():
    from core.assistant_cooking_actions import find_recipe

    recipes = [SimpleNamespace(name="Turkey Chili"), SimpleNamespace(name="Banana Bread"), SimpleNamespace(name="Rice")]
    assert find_recipe(recipes, "the chili").name == "Turkey Chili"
    assert find_recipe(recipes, "banana bread").name == "Banana Bread"
    assert find_recipe(recipes, "my turkey chili recipe").name == "Turkey Chili"
    assert find_recipe(recipes, "lasagna") is None and find_recipe(recipes, "") is None


def test_cook_mode_works_by_voice_the_same_as_its_buttons(tmp_path, monkeypatch):
    from core import assistant_cooking_actions as voice
    from core.assistant_actions import AssistantActionRegistry

    recipe = SimpleNamespace(recipe_id="r1", name="Turkey Chili", locked=False, instructions="\n".join(STEPS),
                             ingredients=INGREDIENTS)
    kitchen = SimpleNamespace(get_recipe=lambda rid: recipe if rid == "r1" else None, all_recipes=lambda: [recipe])
    context = SimpleNamespace(kitchen=kitchen, cooking=cs.CookingStore(SimpleNamespace(), data_dir=tmp_path))
    registry = AssistantActionRegistry()
    voice.register_cooking_actions(registry)
    tool = {name: registry._actions[name].handler for name in ("cook_start", "cook_step", "cook_timer", "cook_finish")}
    assert tool["cook_start"](context, {"recipe": "the chili"}).startswith("Step 1 of 4")
    assert tool["cook_step"](context, {"move": "next"}).startswith("Step 2 of 4")
    assert tool["cook_step"](context, {"step": 4}).startswith("Step 4 of 4")
    assert "last step" in tool["cook_step"](context, {"move": "next"})  # its own words, not an error
    assert tool["cook_timer"](context, {"name": "Rice", "minutes": 18}) == "Rice timer: 18 minutes."
    assert tool["cook_timer"](context, {"name": "Rice", "stop": "yes"}) == "Stopped the rice timer."
    assert tool["cook_finish"](context, {"made": "no"}) == "Stopped cooking Turkey Chili. Nothing was logged."
    assert "Nothing's cooking" in tool["cook_step"](context, {})


def test_cook_mode_on_the_glasses_shows_the_step_its_timers_and_one_press_moves(tmp_path):
    from core.glasses import GLASSES_KINDS, _kitchen_cooking, cooking_hero

    context = SimpleNamespace(cooking=cs.CookingStore(SimpleNamespace(), data_dir=tmp_path))
    assert _kitchen_cooking(context, None)["lines"] == []  # nothing cooking: a line saying how to start
    store = context.cooking
    s = store.begin("r1", "Turkey Chili", STEPS, datetime.now())
    s.index = 2  # "Simmer ... minutes": it offers its own timer
    store.save()
    panel = _kitchen_cooking(context, None)
    assert panel["live"] and panel["hero"]["set"] == "Step 3 of 4" and panel["hero"]["step"] == STEPS[2]
    kinds = [line["action"]["kind"] for line in panel["lines"]]
    assert kinds[0] == "cooking.next" and "cooking.back" in kinds and set(kinds) <= GLASSES_KINDS
    assert all(line["action"].get("quick") for line in panel["lines"])
    hero = cooking_hero({"title": "Chili", "number": 1, "steps_total": 2, "step": "Boil",
                         "timers": [{"name": "Rice", "left": 1062, "done": False}, {"name": "Oven", "left": 0, "done": True}]})
    assert hero["timers"] == [{"name": "Rice", "left": "17:42", "done": False}, {"name": "Oven", "left": "Done", "done": True}]
