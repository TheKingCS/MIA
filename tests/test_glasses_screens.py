"""The numbers on an app's glasses screen, a vehicle's own page, and "I Made This"."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from core.actions import ActionCenter
from core.glasses import ASSET_ITEM, GLASSES_KINDS, TILES, glasses_apps, glasses_panel, priority_now
from tests.engine_world import build_world

TODAY = date(2026, 11, 2)


def make(tmp_path, monkeypatch):
    """The shared test world with an action center."""
    world = build_world(tmp_path, monkeypatch)
    world.actions = ActionCenter()
    return world


def card(world, app_id):
    """The glasses' card for an app."""
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
    line = glasses_panel(world, "kitchen", "recipes-all", TODAY)["lines"][0]
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


def signed_in(world):
    """A server client signed in as the world's person."""
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_a_linked_phone_reads_the_conversation_where_it_went(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    client = signed_in(world)
    monkeypatch.setattr("core.home_link.linked", lambda context: True)
    asked = []

    def home(context, path, *args, **kwargs):
        asked.append(path)
        return {"messages": [{"role": "user", "content": "from the computer"}]}

    monkeypatch.setattr("core.home_link.home_call", home)
    got = client.get("/api/talk/thread?limit=40&earlier=1").json()
    assert got["messages"][0]["content"] == "from the computer" and asked == ["/api/talk/thread?limit=40&earlier=1"]
    client.get("/api/glasses/feed?since=abc")
    assert asked[-1] == "/api/glasses/feed?since=abc"


def test_recipes_open_by_shelf(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    world.kitchen.add_recipe("Tacos", category="Dinner")
    world.kitchen.add_recipe("Pancakes", category="Breakfast")
    shelves = glasses_panel(world, "kitchen", "recipes", TODAY)["lines"]
    assert [s["text"] for s in shelves] == ["Breakfast", "Dinner", "All Recipes"]
    panel = glasses_panel(world, "kitchen", shelves[1]["open"]["item"], TODAY)
    assert panel["title"] == "Dinner" and [line["text"] for line in panel["lines"]] == ["Tacos"]
    assert glasses_panel(world, "kitchen", "recipes-nothing", TODAY) is None


class Songs:
    """A music library holding these tracks and playlists, none uploaded."""
    def __init__(self, tracks, playlists=()):
        """Keeps the tracks and playlists."""
        self.tracks, self.playlists = tracks, playlists
        self.root_path = Path(".")

    def all_tracks(self):
        """Every track."""
        return self.tracks

    def all_playlists(self):
        """Every playlist."""
        return self.playlists

    def uploaded(self, track):
        """No track is uploaded."""
        return False


def song(track_id, title, artist):
    """A three-minute track with a title and artist."""
    return SimpleNamespace(track_id=track_id, title=title, artist=artist, album="", genre="", duration_seconds=180, track_number=1)


def test_music_plays_the_list_it_was_picked_from(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    world.music = Songs([song("a", "One", "Ann"), song("b", "Two", "Bo"), song("c", "Three", "Bo")],
                        [SimpleNamespace(playlist_id="p1", name="Drive", track_ids=["c", "a", "gone"])])
    apps = card(world, "music")
    assert apps["menu"][0]["type"] == "player"
    songs = glasses_panel(world, "music", "songs", TODAY)["lines"]
    assert songs[1]["play"]["ids"] == ["a", "c", "b"] and songs[1]["play"]["at"] == 1
    playlist = glasses_panel(world, "music", "playlists", TODAY)["lines"][0]
    drive = glasses_panel(world, "music", playlist["open"]["item"], TODAY)
    assert [line["text"] for line in drive["lines"]] == ["Three", "One"] and drive["lines"][0]["play"]["ids"] == ["c", "a"]
    artist = glasses_panel(world, "music", "artists", TODAY)["lines"][1]
    assert [line["text"] for line in glasses_panel(world, "music", artist["open"]["item"], TODAY)["lines"]] == ["Three", "Two"]
    assert glasses_panel(world, "music", "list-a-99", TODAY) is None


def test_a_live_workout_moves_on_one_press(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    from core import glasses

    monkeypatch.setattr(glasses, "_workout_live_lines", lambda context, today: {"title": "t", "more": 0, "empty": "", "lines": [
        {"text": "Set done", "action": {"kind": "training.set", "label": "Next set", "params": {}}},
        {"text": "Finish", "action": {"kind": "training.finish", "label": "Finish", "params": {}}}]})
    panel = glasses_panel(world, "workout", "live", TODAY)
    assert panel["live"] is True
    assert panel["lines"][0]["action"]["quick"] is True and "quick" not in panel["lines"][1]["action"]
