"""The numbers on an app's glasses screen, a vehicle's own page, and "I Made This"."""

from datetime import date

from core.actions import ActionCenter
from core.glasses import ASSET_ITEM, GLASSES_KINDS, TILES, glasses_apps, glasses_panel, priority_now
from tests.engine_world import build_world

TODAY = date(2026, 11, 2)


def make(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    world.actions = ActionCenter()
    return world


def card(world, app_id):
    data = glasses_apps(world, TODAY)
    return next(a for a in data["apps"] + data["others"] if a["id"] == app_id)


def test_kitchen_shows_its_numbers(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    world.kitchen.add_recipe("Tacos")
    tiles = {t["label"]: t["value"] for t in card(world, "kitchen")["tiles"]}
    assert tiles["Recipes"] == "1" and tiles["Grocery"] == "0" and tiles["Meals"] == "0/0"


def test_home_says_what_matters_now():
    assert priority_now([{"name": "Garage", "tone": "attention", "status": "1 past due"}]) == "Garage: 1 past due"
    mission = {"objectives": [{"text": "Sort", "done": True}, {"text": "Hang the bikes", "done": False}]}
    assert priority_now([{"name": "Missions", "tone": "calm", "status": "", "mission": mission}]) == "Hang the bikes"
    assert priority_now([]) == ""


def test_a_rest_day_says_so(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    assert card(world, "workout")["tiles"][0] == {"label": "Today", "value": "Rest", "tone": ""}


def test_no_tile_is_about_money():
    assert "budget" not in TILES and "real_estate" not in TILES and "freedom" not in TILES


def test_a_broken_app_loses_its_numbers_not_its_card(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    monkeypatch.setitem(TILES, "kitchen", lambda context, today: 1 / 0)
    assert card(world, "kitchen")["tiles"] == []


def test_i_made_this_is_on_the_recipe_and_allowed(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    recipe = world.kitchen.add_recipe("Tacos")
    line = glasses_panel(world, "kitchen", "recipes", TODAY)["lines"][0]
    action = line["recipe"]["action"]
    assert action["kind"] in GLASSES_KINDS
    proposal = world.actions.approve(world, world.actions.propose(world, action["kind"], action["params"]).proposal_id)
    assert proposal.status == "executed"
    assert world.kitchen.get_recipe(recipe.recipe_id).name == "Tacos"


def test_a_vehicle_opens_to_its_own_page(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    from core.web_equipment import equipment_page

    assets = equipment_page(world, "garage", TODAY).get("assets") or []
    if not assets:
        made = world.actions.propose(world, "asset.add", {"name": "Truck", "category": "Vehicle"})
        world.actions.approve(world, made.proposal_id)
        assets = equipment_page(world, "garage", TODAY)["assets"]
    line = glasses_panel(world, "garage", "assets", TODAY)["lines"][0]
    assert line["open"]["item"] == f"{ASSET_ITEM}{assets[0]['id']}"
    panel = glasses_panel(world, "garage", line["open"]["item"], TODAY)
    assert panel["title"] == assets[0]["name"]
    assert glasses_panel(world, "garage", f"{ASSET_ITEM}nope", TODAY) is None
    assert glasses_panel(world, "kitchen", line["open"]["item"], TODAY) is None
