"""What comes after User Sync (core/welcome.py, core/app_intro.py)."""

from core import first_boot, user_sync, welcome
from core.actions import ActionCenter
from core.app_intro import WHAT, app_intro
from core.glasses import PANELS
from core.glasses_voice import handle
from tests.engine_world import build_world


def make(tmp_path, monkeypatch):
    """Someone who's met MIA and finished User Sync."""
    world = build_world(tmp_path, monkeypatch)
    world.actions = ActionCenter()
    first_boot.skip(world)
    progress = {"started_at": "2026-11-02T08:00:00", "phone_done": True,
                "topics": {t: {"status": "done"} for t in user_sync.TOPICS}}
    user_sync._save(world, progress)
    return world


def mission(world):
    return next(m for m in world.missions.all_missions() if m.name == welcome.MISSION)


def done(world):
    return [world.missions.is_objective_complete(mission(world).mission_id, i) for i in range(4)]


def through_home(world):
    world_now = welcome.choose(world, "begin")
    for _ in welcome.HOME_TOUR:
        world_now = welcome.choose(world, "next")
    return world_now


def test_it_waits_for_user_sync(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    user_sync._save(world, {})
    assert welcome.state(world)["left"] is False
    assert welcome.choose(world, "begin")["stage"] == "none"


def test_nothing_is_added_before_lets_go(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    now = welcome.state(world)
    assert now["stage"] == "mission" and now["ready"] is True and now["mission"]["percent"] == 25
    assert not [m for m in world.missions.all_missions() if m.name == welcome.MISSION]
    assert welcome.choose(world, "begin")["stage"] == "home"
    assert done(world) == [True, False, False, False]
    assert mission(world).reward_xp == 100


def test_the_mission_can_be_undone_like_any_other(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    welcome.choose(world, "begin")
    added = next(p for p in world.actions._proposals.values() if p.kind == "mission.add")
    assert added.proposed_by == "mia"


def test_home_tour_ticks_only_when_finished(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    welcome.choose(world, "begin")
    now = welcome.choose(world, "next")
    assert now["tour"]["number"] == 2 and now["tour"]["tiles"][1]["on"] is True
    assert welcome.choose(world, "skip")["stage"] == "apps"
    assert done(world)[1] is False


def test_a_paused_tour_picks_up_at_its_step(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    now = through_home(world)
    assert now["stage"] == "apps" and done(world)[1] is True
    app = now["apps"][0]["id"]
    welcome.choose(world, "tour", app)
    welcome.choose(world, "next")
    now = welcome.choose(world, "skip")
    assert now["stage"] == "apps" and now["apps"][0]["status"] == "Paused · step 2"
    assert welcome.choose(world, "tour", app)["tour"]["number"] == 2


def test_finishing_a_tour_or_opening_an_app_explores(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    now = through_home(world)
    app = now["apps"][0]
    for _ in welcome.APP_TOURS[app["id"]]:
        now = welcome.choose(world, "tour", app["id"]) if now["stage"] == "apps" else welcome.choose(world, "next")
    now = welcome.choose(world, "next")
    assert now["stage"] == "apps" and now["apps"][0]["status"] == "Tour done" and done(world)[2] is True

    world2 = make(tmp_path / "two", monkeypatch)
    now = through_home(world2)
    assert welcome.choose(world2, "open", now["apps"][0]["id"])["open"] == now["apps"][0]["id"]
    assert done(world2)[2] is True


def test_talking_on_her_own_finishes_the_mission_and_pays(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    now = through_home(world)
    welcome.choose(world, "open", now["apps"][0]["id"])
    handle(world, world.me.profile_id, "what's on today", lambda words: {"reply_text": "Nothing."})
    assert mission(world).status == "completed"
    now = welcome.state(world)
    assert now["stage"] == "explore" and now["paused"] is False and [i["label"] for i in now["ideas"]][-1] == "Just talk"
    assert welcome.choose(world, "finish")["stage"] == "done"
    assert welcome.state(world)["left"] is False


def test_later_leaves_a_card_and_resume_returns(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    welcome.choose(world, "begin")
    now = welcome.choose(world, "later")
    assert now["paused"] is True and now["left"] is True
    assert welcome.hear(world, "what time is it") is None
    assert welcome.hear(world, "let's continue the tour")["paused"] is False


def test_words_on_the_glasses(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    assert welcome.hear(world, "Let's go!")["stage"] == "home"
    assert welcome.hear(world, "next")["tour"]["number"] == 2
    assert welcome.hear(world, "what's for dinner") is None
    assert welcome.hear(world, "skip the tour")["stage"] == "apps"


def test_a_removed_mission_stays_removed(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    welcome.choose(world, "begin")
    world.missions.delete_mission(mission(world).mission_id)
    assert welcome.choose(world, "next")["stage"] == "home"
    welcome.talked(world)
    assert not [m for m in world.missions.all_missions() if m.name == welcome.MISSION]


def test_every_tour_step_is_a_real_menu_item():
    for app, steps in welcome.APP_TOURS.items():
        assert app in WHAT
        real = {item for item, _label, _build in PANELS[app]}
        assert {item for item, _text in steps} <= real


def test_each_person_has_their_own(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    welcome.choose(world, "begin")
    world.profile_id = world.other.profile_id
    assert welcome.state(world)["left"] is False  # they haven't met her yet


def test_an_intro_only_says_what_exists(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch)
    assert app_intro(world, "kitchen")["yours"] == []
    world.kitchen.add_recipe("Tacos")
    world.missions.add_mission("Save for a van")
    assert "Tacos" in app_intro(world, "kitchen")["yours"][0]
    assert any("Save for a van" in line for line in app_intro(world, "budget")["yours"])
    assert app_intro(world, "kitchen")["status"] == "DERIVED"


def test_through_the_server(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world = make(tmp_path, monkeypatch)
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.get("/api/welcome").json()["stage"] == "mission"
    assert client.post("/api/welcome", json={"choice": "begin"}).json()["stage"] == "home"
    got = client.post("/api/glasses/voice", json={"text": "next"}).json()
    assert got["say"] == welcome.HOME_TOUR[1][1]
