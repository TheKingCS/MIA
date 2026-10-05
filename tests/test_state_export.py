"""
The state export (Engine Phase 1 step 4, 2026-10-05): Life State v2 as
JSON from `python -m tools.export_state` and `/api/state`, matching the
published schema docs/schema/life_state.schema.json.
"""

import json
from datetime import date, timedelta

import pytest

from core import schema_check
from core.child_accounts import make_child
from core.context_assembler import assemble_life_state_v2
from core.gamification import SkillWeight
from tests.engine_world import build_world

SCHEMA = schema_check.load("life_state.schema.json")
TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    lot = context.real_estate.add_property("Vacant lot", property_type="Land", current_value=50000.0)
    goal = context.intents.add_intent("Grow our own food", primary=True)
    greenhouse = context.projects.add_project("Greenhouse", intent_id=goal.intent_id)
    context.tasks.add_task(greenhouse.project_id, "Dig the pit")
    context.links.add(f"project:{greenhouse.project_id}", "DEPENDS_ON", f"property:{lot.property_id}")
    context.budget.add_income_source("Pay", 800.0, TODAY.isoformat(), recurrence="biweekly")
    bill = context.budget.add_bill("Phone", 60.0, (TODAY - timedelta(days=1)).isoformat(), recurrence="monthly")
    context.budget.add_bill("Water", 30.0, (TODAY + timedelta(days=3)).isoformat(), recurrence="monthly")
    context.budget.add_debt("Card", 900.0, 22.0, minimum_payment=35.0)
    context.budget.set_budget_target("Groceries", 100.0)
    context.budget.add_expense(150.0, "Groceries", "Market")
    context.workout.add_session(duration_minutes=30)
    mission = context.missions.add_mission("Plan the week", skill_rewards=[SkillWeight("organization", 5)])
    context.missions.update_mission(mission.mission_id, status="completed")
    context.paid_bill = bill
    return context


def test_the_schema_describes_exactly_the_sections_mia_produces(world):
    state = assemble_life_state_v2(world)
    assert set(SCHEMA["required"]) == set(state) == set(SCHEMA["properties"])


def test_a_full_state_matches_the_schema(world):
    state = assemble_life_state_v2(world)
    assert state["friction"]["items"] and state["goals"]["chains"] and state["finances"]["budget_targets"]
    assert schema_check.errors(state, SCHEMA) == []
    world.budget.mark_bill_paid(world.paid_bill.bill_id)
    assert schema_check.errors(assemble_life_state_v2(world), SCHEMA) == []


def test_a_child_s_and_an_empty_state_match_too(world, tmp_path, monkeypatch):
    kid = world.profiles.create_profile("Ari", make_active=False)
    make_child(world, kid.profile_id, [world.me.profile_id])
    world.profiles.set_active_profile(kid.profile_id)
    assert schema_check.errors(assemble_life_state_v2(world), SCHEMA) == []
    from core.app_context import AppContext
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus

    assert schema_check.errors(assemble_life_state_v2(AppContext(config=ConfigManager(), events=EventBus())),
                               SCHEMA) == []


def test_the_checker_catches_drift(world):
    state = json.loads(json.dumps(assemble_life_state_v2(world)))
    state["finances"]["status"] = "MAYBE"
    state["projects"]["items"][0]["tasks_open"] = "one"
    state["due"]["items"].append({"when": "someday"})
    state["surprise"] = 1
    del state["links"]
    problems = schema_check.errors(state, SCHEMA)
    assert any("$.finances.status" in p for p in problems)
    assert any("tasks_open: expected integer" in p for p in problems)
    assert any("someday" in p for p in problems) and any("missing 'title'" in p for p in problems)
    assert "$: unexpected 'surprise'" in problems and "$: missing 'links'" in problems
    assert schema_check.errors("x:1", {"type": "string", "pattern": "^[a-z]+:"}) == []


def test_the_export_command(tmp_path, monkeypatch):
    import core.config_manager as config_module
    import core.profile_manager as profile_module
    from core.app_context import AppContext
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus
    from core.profile_manager import ProfileManager
    from tools import export_state

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    seed = AppContext(config=ConfigManager(), events=EventBus())
    seed.profiles = ProfileManager(seed)
    seed.profiles.create_profile("Robin", password="pw", email="robin@example.com")
    out = tmp_path / "robin.state.json"
    assert export_state.main(["--who", "robin@example.com", "--out", str(out)]) == 0
    state = json.loads(out.read_text(encoding="utf-8"))
    assert state["person"]["name"] == "Robin" and schema_check.errors(state, SCHEMA) == []
    assert export_state.main(["--who", "nobody@example.com"]) == 1


def test_the_phone_gets_its_own_state(world):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    assert client.get("/api/state").status_code == 401
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    res = client.get("/api/state", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    state = res.json()
    assert state["person"]["name"] == "Robin" and schema_check.errors(state, SCHEMA) == []


def test_the_published_example_matches_the_schema():
    """docs/schema/life_state.example.json (placeholder data) is what
    designers render from; it must stay in the published shape."""
    example = json.loads((schema_check.SCHEMA_DIR / "life_state.example.json").read_text(encoding="utf-8"))
    assert schema_check.errors(example, SCHEMA) == []
