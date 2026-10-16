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
    assert not (set(PANELS) & set(ASKS)) and not (set(PANELS) | set(ASKS)) & NOT_ON_GLASSES
    assert GLASSES_KINDS <= set(ACTION_TYPES)
    # nothing that deletes, moves money, or changes a record's details
    assert not any(k.endswith(("delete", ".edit", ".add")) or k.startswith(("bill.", "income", "debt.", "expense."))
                   for k in GLASSES_KINDS)
    # an ask is a question, never an example command that would change something
    assert all(say.endswith("?") for asks in ASKS.values() for say in asks)


def test_the_cards_are_the_persons_apps_with_menus(world):
    data = glasses_apps(world, TODAY)
    ids = [a["id"] for a in data["apps"]]
    assert ids[:5] == ["dashboard", "missions", "kitchen", "workout", "budget"]
    assert not set(ids) & NOT_ON_GLASSES and len(ids) == len(set(ids))
    for card in data["apps"]:
        assert 1 <= len(card["menu"]) <= 4, card["id"]
        assert len({m["id"] for m in card["menu"]}) == len(card["menu"])
        assert all(m["type"] in ("panel", "ask") and (m["type"] == "panel" or m["say"]) for m in card["menu"])
    garage = next(a for a in data["apps"] if a["id"] == "garage")
    assert "1 needs attention" in garage["status"] and garage["tone"] == "attention"

    set_app_visible(world, "kitchen", False)
    assert "kitchen" not in [a["id"] for a in glasses_apps(world, TODAY)["apps"]]
    assert glasses_panel(world, "kitchen", "grocery", TODAY) is None


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
    panel = glasses_panel(world, "maintenance", "attention", TODAY)
    line = next(line for line in panel["lines"] if line["text"].startswith("Check oil"))
    proposal = world.actions.propose(world, line["action"]["kind"], line["action"]["params"])
    assert "Check oil" in proposal.summary and world.maintenance.get_task(world.task.task_id).last_completed != \
        TODAY.isoformat()
    world.actions.approve(world, proposal.proposal_id)
    assert world.maintenance.get_task(world.task.task_id).last_completed == TODAY.isoformat()
    after = glasses_panel(world, "maintenance", "attention", TODAY)
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
    assert cards.status_code == 200 and cards.json()["apps"][0]["id"] == "dashboard"
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
