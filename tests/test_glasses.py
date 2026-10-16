"""
The glasses' app cards and quick action menus (Zac 2026-10-16, H-0041
Phase 2; core/glasses.py): the person's own apps as cards, each with a
menu; a panel's lines carry only glasses-safe actions, and money stays
readouts; a change goes Propose -> Approve like everywhere else.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from core.actions import ACTION_TYPES, ActionCenter
from core.child_accounts import make_child
from core.focus_presets import set_app_visible
from core.glasses import ASKS, FIRST, GLASSES_KINDS, NOT_ON_GLASSES, PANELS, glasses_apps, glasses_panel
from core.web_surfaces import APPS_BY_ID
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.budget.add_bill("Electric", 120.0, (TODAY - timedelta(days=1)).isoformat(), recurrence="monthly")
    mower = context.maintenance.add_asset("Mower", category="Power Equipment")
    context.task = context.maintenance.add_task(mower.asset_id, "Check oil", interval_days=30,
                                                last_completed=(TODAY - timedelta(days=40)).isoformat())
    context.kitchen.add_grocery_item("Eggs", 12)
    return context


def _every_panel(context):
    for app, items in PANELS.items():
        for item, _label, _build in items:
            panel = glasses_panel(context, app, item, TODAY)
            if panel is not None:
                yield app, item, panel


def test_the_tables_name_real_apps_and_real_kinds():
    for app_id in set(FIRST) | set(PANELS) | set(ASKS) | set(NOT_ON_GLASSES):
        assert app_id in APPS_BY_ID, app_id
    assert not (set(PANELS) | set(ASKS)) & NOT_ON_GLASSES
    assert GLASSES_KINDS <= set(ACTION_TYPES)
    # nothing that deletes, moves money, or changes a record's details
    assert not any(k.endswith(("delete", ".edit", ".add")) or k.startswith(("bill.", "income", "debt.", "expense.", "inbox"))
                   for k in GLASSES_KINDS)
    # an ask is a question, never an example command that would change something
    assert all(say.endswith("?") for asks in ASKS.values() for say in asks)


def test_the_cards_are_the_persons_apps_with_menus(world):
    data = glasses_apps(world, TODAY)
    ids = [a["id"] for a in data["apps"]]
    assert not data["pinned"] and data["others"] == [] and data["hint"]
    # Missions right after the orb; Today's due items live in Missions now (Zac, 2026-10-16)
    assert ids[0] == "missions" and "dashboard" not in ids
    assert [i for i in ids if i in ("kitchen", "workout", "budget")] == ["kitchen", "workout", "budget"]
    assert not set(ids) & NOT_ON_GLASSES and len(ids) == len(set(ids))
    for card in data["apps"]:
        menu = [m for m in card["menu"] if m["type"] != "action"]
        assert 1 <= len(menu) <= 5, card["id"]
        assert len({m["id"] for m in card["menu"]}) == len(card["menu"])
        assert all(m["type"] == "panel" or m["say"] for m in menu)
        if card["id"] == "missions":  # always there, never pinned or unpinned
            assert all(m["id"] != "pin" for m in card["menu"])
            continue
        pin = card["menu"][-1]
        assert pin["id"] == "pin" and pin["action"] == {"kind": "app.favorite", "label": "Pin",
                                                         "params": {"module_id": card["id"], "favorite": True}}
    garage = next(a for a in data["apps"] if a["id"] == "garage")
    assert "1 needs attention" in garage["status"] and garage["tone"] == "attention"

    set_app_visible(world, "kitchen", False)
    assert "kitchen" not in [a["id"] for a in glasses_apps(world, TODAY)["apps"]]
    assert glasses_panel(world, "kitchen", "grocery", TODAY) is None


def test_favorites_are_pinned_for_the_glasses(world):
    """Zac, 2026-10-16: the apps a person favorites are pinned for the
    glasses, in the order they starred them; the rest wait behind All apps."""
    from core.focus_presets import set_app_favorite

    set_app_favorite(world, "kitchen", True)
    set_app_favorite(world, "garage", True)
    set_app_favorite(world, "settings", True)  # not a glasses app: ignored
    data = glasses_apps(world, TODAY)
    assert data["pinned"] and [a["id"] for a in data["apps"]] == ["missions", "kitchen", "garage"]
    assert "kitchen" not in [a["id"] for a in data["others"]] and data["others"][0]["id"] not in ("missions", "dashboard")
    kitchen = data["apps"][1]
    assert kitchen["pinned"] and kitchen["menu"][-1]["label"] == "Unpin From Glasses"
    assert kitchen["menu"][-1]["action"]["params"] == {"module_id": "kitchen", "favorite": False}

    # unpinning from the glasses is the favorite star, proposed then approved
    p = world.actions.propose(world, "app.favorite", kitchen["menu"][-1]["action"]["params"])
    world.actions.approve(world, p.proposal_id)
    assert [a["id"] for a in glasses_apps(world, TODAY)["apps"]] == ["missions", "garage"]


def test_household_people_and_inbox_panels(world, tmp_path):
    from core.inbox_manager import InboxManager
    from core.relationships_manager import RelationshipsManager

    world.relationships = RelationshipsManager(world, data_dir=tmp_path / "rel")
    soon = TODAY + timedelta(days=3)
    world.relationships.add_person("Sam", birthday=f"1990-{soon:%m-%d}")
    panel = glasses_panel(world, "relationships", "birthdays", TODAY)
    assert panel["lines"][0]["text"] == "Sam" and "in 3 days" in panel["lines"][0]["detail"]
    assert "action" not in panel["lines"][0]

    world.recurring_missions.add_template(name="Dishes", objective_description_template="Do the dishes",
                                          base_target=1, target_increment_per_week=0, daily_reward_xp=5,
                                          weekly_bonus_reward_xp=0, start_date=TODAY.isoformat(),
                                          category="Household")
    chores = glasses_panel(world, "household", "chores", TODAY)
    dishes = chores["lines"][0]
    assert dishes["text"] == "Dishes" and dishes["action"]["kind"] == "routine.log"
    world.actions.approve(world, world.actions.propose(world, "routine.log", dishes["action"]["params"]).proposal_id)
    after = glasses_panel(world, "household", "chores", TODAY)["lines"][0]
    assert after["tone"] == "ok" and "action" not in after

    world.inbox = InboxManager(world, data_dir=tmp_path / "inbox")
    assert glasses_panel(world, "inbox", "waiting", TODAY)["empty"].startswith("Nothing waiting")


def test_every_panel_builds_and_carries_only_glasses_safe_actions(world):
    seen = 0
    for app, item, panel in _every_panel(world):
        seen += 1
        assert panel["title"] and isinstance(panel["lines"], list) and len(panel["lines"]) <= 5, (app, item)
        assert panel["lines"] or panel["empty"] is not None
        for line in panel["lines"]:
            if "action" in line:
                assert line["action"]["kind"] in GLASSES_KINDS, (app, item, line)
        if app == "budget":
            assert not any("action" in line for line in panel["lines"]), "money stays readouts on the glasses"
    assert seen == sum(len(items) for items in PANELS.values())
    due = glasses_panel(world, "budget", "due", TODAY)
    assert any(line["text"].startswith("Electric") and line["tone"] == "bad" for line in due["lines"])
    assert glasses_panel(world, "kitchen", "nope", TODAY) is None


def test_a_change_from_the_glasses_is_proposed_then_approved(world):
    panel = glasses_panel(world, "garage", "past_due", TODAY)
    line = next(line for line in panel["lines"] if line["text"].startswith("Check oil"))
    proposal = world.actions.propose(world, line["action"]["kind"], line["action"]["params"])
    assert "Check oil" in proposal.summary and world.maintenance.get_task(world.task.task_id).last_completed != \
        TODAY.isoformat()
    world.actions.approve(world, proposal.proposal_id)
    assert world.maintenance.get_task(world.task.task_id).last_completed == TODAY.isoformat()
    after = glasses_panel(world, "garage", "past_due", TODAY)
    assert not any(line["text"].startswith("Check oil") for line in after["lines"])

    grocery = glasses_panel(world, "kitchen", "grocery", TODAY)
    eggs = grocery["lines"][0]
    assert eggs["text"] == "Eggs" and eggs["action"]["kind"] == "grocery.check"
    world.actions.approve(world, world.actions.propose(world, "grocery.check", eggs["action"]["params"]).proposal_id)
    assert glasses_panel(world, "kitchen", "grocery", TODAY)["lines"] == []


def test_a_child_gets_child_apps_only(world):
    make_child(world, world.me.profile_id, [world.other.profile_id])
    ids = {a["id"] for a in glasses_apps(world, TODAY)["apps"]}
    assert "kitchen" in ids and not ids & {"budget", "real_estate", "garage"}
    assert glasses_panel(world, "budget", "month", TODAY) is None


def test_the_endpoints(world):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    cards = client.get("/api/glasses")
    assert cards.status_code == 200 and cards.json()["apps"][0]["id"] == "missions"
    assert client.get("/api/glasses/kitchen/grocery").json()["lines"][0]["text"] == "Eggs"
    assert client.get("/api/glasses/kitchen/nope").status_code == 404
    assert client.get("/api/glasses/settings/anything").status_code == 404


def test_the_published_examples_match():
    """The public preview's glasses read docs/schema/glasses*.example.json."""
    schema = Path(__file__).resolve().parent.parent / "docs" / "schema"
    cards = json.loads((schema / "glasses.example.json").read_text(encoding="utf-8"))
    panels = json.loads((schema / "glasses_panels.example.json").read_text(encoding="utf-8"))
    for card in cards["apps"]:
        for item in card["menu"]:
            if item["type"] == "panel":
                assert f"{card['id']}/{item['id']}" in panels


def test_the_missions_card_shows_a_mission_you_pick(world):
    """Zac, 2026-10-16: the Missions card shows the active mission and its
    objectives; "Select mission" lists them all to pick the one shown."""
    first = world.missions.add_mission("Organize the garage")
    world.missions.add_objective(first.mission_id, "Sort the tools", "tally", 1)
    world.missions.add_objective(first.mission_id, "Hang the bikes", "tally", 2)
    second = world.missions.add_mission("Run a 5K")
    world.missions.add_objective(second.mission_id, "Run three times", "tally", 3)

    card = next(a for a in glasses_apps(world, TODAY)["apps"] if a["id"] == "missions")
    assert card["menu"][0]["label"] == "Select Mission"
    shown = card["mission"]
    assert shown["name"] in ("Organize the garage", "Run a 5K") and shown["objectives"][0]["text"]

    pick = glasses_panel(world, "missions", "pick", TODAY)
    missions = [line for line in pick["lines"] if "pick" in line]
    assert {"Organize the garage", "Run a 5K"} <= {line["text"] for line in missions}
    assert not any("action" in line for line in missions)
    # Today's due items are here too, sortable (Zac, 2026-10-16)
    due = [line for line in pick["lines"] if "pick" not in line]
    assert {"past_due"} == {line["bucket"] for line in due if line["text"].startswith(("Electric", "Check oil"))}
    assert [f["label"] for f in pick["filters"]] == ["All", "Past Due", "Due Today", "Due Soon"]
    assert pick["filters"][1]["count"] >= 2 and pick["lines"][0]["bucket"] == "past_due"

    card = next(a for a in glasses_apps(world, TODAY, mission_id=first.mission_id)["apps"] if a["id"] == "missions")
    assert [o["text"] for o in card["mission"]["objectives"]] == ["Sort the tools", "Hang the bikes"]

    progress = glasses_panel(world, "missions", "progress", TODAY, mission_id=first.mission_id)
    sort, hang = progress["lines"]
    assert (sort["action"]["label"], hang["action"]["label"], hang["detail"]) == ("Done", "+1", "0 of 2")
    world.actions.approve(world, world.actions.propose(world, "objective.tick", sort["action"]["params"]).proposal_id)
    card = next(a for a in glasses_apps(world, TODAY, mission_id=first.mission_id)["apps"] if a["id"] == "missions")
    assert card["mission"]["objectives"][0]["done"] and not card["mission"]["objectives"][1]["done"]


def test_an_exercise_done_from_the_glasses(world):
    """fitness.step counts from 1; the glasses' first exercise is step 1."""
    world.fitness.update_plan({"training": {"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                                            "rotation": [{"name": "Push", "exercises": [{"name": "Dips", "sets": 3, "reps": 8}]}]}})
    panel = glasses_panel(world, "workout", "training", TODAY)
    dips = panel["lines"][0]
    assert dips["text"] == "Dips" and dips["action"]["params"] == {"step": 1}
    p = world.actions.propose(world, "fitness.step", dips["action"]["params"])
    world.actions.approve(world, p.proposal_id)
    assert glasses_panel(world, "workout", "training", TODAY)["lines"][0]["tone"] == "ok"


def test_maintenance_and_property_are_folded_in(world):
    """Zac, 2026-10-16: Garage holds vehicles, equipment and tools; Real Estate
    holds buildings and appliances; Maintenance and Property are gone."""
    from core.focus_presets import menu_modules
    from core.web_equipment import equipment_page, scope_of
    from core.web_surfaces import RETIRED, apps_page, shell

    assert (scope_of("Tool"), scope_of("Other"), scope_of("Appliance"), scope_of("Property")) == \
        ("garage", "garage", "real_estate", "real_estate")
    furnace = world.maintenance.add_asset("Furnace", category="Appliance")
    world.maintenance.add_task(furnace.asset_id, "Replace filter", interval_days=90,
                               last_completed=(TODAY - timedelta(days=90)).isoformat())
    home = equipment_page(world, "real_estate", TODAY)
    assert [a["name"] for a in home["assets"]] == ["Furnace"]
    assert [t["bucket"] for t in home["tasks"]] == ["due_today"]
    assert "Furnace" not in [a["name"] for a in equipment_page(world, "garage", TODAY)["assets"]]

    ids = {a["id"] for a in shell(world, TODAY)["apps"]} | {a["id"] for g in apps_page(world)["groups"] for a in g["apps"]}
    assert not ids & RETIRED
    assert not {a["id"] for a in glasses_apps(world, TODAY)["apps"]} & RETIRED
    estate = [m["label"] for m in next(a for a in glasses_apps(world, TODAY)["apps"] if a["id"] == "real_estate")["menu"]]
    assert estate[:5] == ["Properties", "Home & Appliances", "Past Due", "Due Today", "Due Soon"]
    filters = glasses_panel(world, "real_estate", "due_today", TODAY)["lines"]
    assert [line["text"] for line in filters] == ["Replace filter: Furnace"]

    class M:
        def __init__(self, module_id):
            self.module_id = module_id
    listed = [m.module_id for m in menu_modules(world, [M("garage"), M("maintenance"), M("property"), M("real_estate")])]
    assert listed == ["garage", "real_estate"]
