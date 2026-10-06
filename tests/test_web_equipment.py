"""
DEC-0017 (2026-10-06): Garage, Property, Greenhouse and Maintenance on
the web, and one page per asset (Zac's mower concept): the data
(core/web_equipment.py) and every change as an action kind
(core/equipment_actions.py, maintenance.done with a meter value).
"""

from datetime import date, timedelta

import pytest

import core.maintenance_manager as maintenance_module
from core.actions import ACTION_TYPES, ActionCenter, ActionError
from core.child_accounts import make_child
from core.data_logger_manager import DataLoggerManager
from core.equipment_actions import RECORDS, form_spec
from core.web_equipment import asset_page, equipment_page, scope_of, task_status
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(maintenance_module, "_DOCUMENT_ROOT", tmp_path / "documents")
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.data_logger = DataLoggerManager(context, data_dir=context.home_dir)
    m = context.maintenance
    context.mower = m.add_asset("Mower", "Power Equipment", manufacturer="Acme", model="Z1")
    context.oil = m.add_task(context.mower.asset_id, "Check oil", interval_days=30,
                             last_completed=(TODAY - timedelta(days=43)).isoformat())
    context.blades = m.add_task(context.mower.asset_id, "Sharpen blades", interval_days=60,
                                last_completed=(TODAY - timedelta(days=36)).isoformat())
    context.hours = m.add_task(context.mower.asset_id, "Engine hours", trigger_type="runtime",
                               meter_unit="engine hours")
    context.fridge = m.add_asset("Fridge", "Appliance")
    context.tomatoes = m.add_asset("Tomatoes", "Garden/Plant")
    return context


def run(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    return proposal, world.actions.approve(world, proposal.proposal_id)


def test_scopes_follow_the_pc_modules():
    assert [scope_of(c) for c in ("Vehicle", "Power Equipment", "Appliance", "Tool", "Garden/Plant", "Other")] == [
        "garage", "garage", "property", "property", "greenhouse", "maintenance"]


def test_task_status_speaks_the_pc_apps_words(world):
    status = task_status(world.oil, [], TODAY)
    assert (status["text"], status["urgency"], status["needs_attention"]) == ("overdue 13d", "overdue", True)
    assert task_status(world.blades, [], TODAY)["text"] == "due in 24d"
    assert task_status(world.hours, [], TODAY)["quick_stat"]  # a pure reading, never overdue


def test_the_garage_page(world):
    page = equipment_page(world, "garage", TODAY)
    assert [a["name"] for a in page["assets"]] == ["Mower"]
    [mower] = page["assets"]
    assert mower["overdue"] == 1 and mower["make_model"] == "Acme Z1"
    assert [t["title"] for t in mower["tasks"]] == ["Check oil", "Sharpen blades"]
    assert mower["quick_stats"] == [{"title": "Engine hours", "text": "no reading logged"}]
    assert [r["title"] for r in page["attention"]] == ["Check oil"]
    assert page["attention"][0]["action"]["kind"] == "maintenance.done"
    assert [r["title"] for r in page["next_up"]] == ["Sharpen blades"]
    assert [a["name"] for a in equipment_page(world, "property", TODAY)["assets"]] == ["Fridge"]
    assert [a["name"] for a in equipment_page(world, "greenhouse", TODAY)["assets"]] == ["Tomatoes"]
    everything = equipment_page(world, "maintenance", TODAY)
    assert len(everything["assets"]) == 3 and [t["title"] for t in everything["tasks"]][:1] == ["Check oil"]
    assert any(c["title"] == "Sharpen blades" for c in everything["calendar"])


def test_the_asset_page(world):
    world.missions.add_mission("Mow the lawn", maintenance_asset_id=world.mower.asset_id, reward_xp=75)
    run(world, "asset.reading", asset_id=world.mower.asset_id, meter_name="Fuel", value="72", unit="%")
    run(world, "maintenance.reading", task_id=world.hours.task_id, value="12.8")
    run(world, "maintenance.done", task_id=world.oil.task_id)
    page = asset_page(world, world.mower.asset_id, TODAY)
    assert page["scope"] == "garage" and {"label": "Make", "value": "Acme"} in page["details"]
    stats = {s["title"]: s["text"] for s in page["quick_stats"]}
    assert stats == {"Engine hours": "12.8 engine hours", "Fuel": "72 %"}
    assert [m["name"] for m in page["missions"]] == ["Mow the lawn"] and page["missions"][0]["reward_xp"] == 75
    assert page["history"][0]["summary"] == "Check oil: Mower"
    assert page["attention"] == [] and page["parts"]["status"] == "PLANNED"
    assert asset_page(world, "nope", TODAY) is None


def test_add_edit_delete_an_asset_and_its_tasks_with_undo(world):
    proposal, _ = run(world, "asset.add", name="Truck", category="Vehicle", manufacturer="Make",
                      warranty_until=(TODAY + timedelta(days=300)).isoformat())
    assert proposal.summary.startswith("Add the asset Truck: kind Vehicle, make Make, warranty until ")
    truck = next(a for a in world.maintenance.all_assets() if a.name == "Truck")
    assert truck.warranty_until

    proposal, _ = run(world, "maintenance_task.add", asset_id=truck.asset_id, title="Oil change",
                      trigger_type="mileage", meter_unit="miles", meter_interval="5000")
    assert proposal.summary == "Add the maintenance task Oil change: for Truck, goes by mileage, unit miles, every 5000"
    task = next(t for t in world.maintenance.tasks_for_asset(truck.asset_id))
    proposal, _ = run(world, "maintenance_task.edit", task_id=task.task_id, meter_interval="6000")
    assert proposal.summary == "Change Oil change: every 5000 → 6000"
    # A form sends every field back; blanks that stay blank aren't changes.
    proposal, _ = run(world, "asset.edit", asset_id=truck.asset_id, name="Truck", model="X", serial_number="",
                      purchase_date="", notes="")
    assert proposal.summary == "Change Truck: model none → X"
    proposal, _ = run(world, "asset.edit", asset_id=truck.asset_id, warranty_until="")
    assert proposal.summary.startswith("Change Truck: warranty until ") and proposal.summary.endswith("→ none")
    assert world.maintenance.get_asset(truck.asset_id).warranty_until == ""

    proposal, deleted = run(world, "asset.delete", asset_id=truck.asset_id)
    assert proposal.summary == "Delete the asset Truck. Its maintenance tasks go with it; its documents are kept."
    assert world.maintenance.get_asset(truck.asset_id) is None and world.maintenance.get_task(task.task_id) is None
    world.actions.undo(world, deleted.proposal_id)
    assert world.maintenance.get_asset(truck.asset_id) is not None
    assert world.maintenance.get_task(task.task_id).meter_interval == 6000


def test_done_with_a_meter_value(world):
    task = world.maintenance.add_task(world.mower.asset_id, "Oil & filter", trigger_type="runtime",
                                      meter_unit="engine hours", meter_interval=50)
    proposal, _ = run(world, "maintenance.done", task_id=task.task_id, meter_value="120")
    assert proposal.summary == 'Mark "Oil & filter" done on Mower today at 120 engine hours'
    assert world.maintenance.get_task(task.task_id).last_completed_meter_value == 120
    with pytest.raises(ActionError, match="has to be a number"):
        world.actions.propose(world, "maintenance.done", {"task_id": task.task_id, "meter_value": "lots"})


def test_the_engine_keeps_the_rules(world):
    with pytest.raises(ActionError, match="isn't there anymore"):
        world.actions.propose(world, "maintenance_task.add", {"asset_id": "nope", "title": "x"})
    with pytest.raises(ActionError, match="whole number"):
        world.actions.propose(world, "maintenance_task.add",
                              {"asset_id": world.mower.asset_id, "title": "x", "interval_days": "2.5"})
    with pytest.raises(ActionError, match="can't be negative"):
        world.actions.propose(world, "maintenance_task.add",
                              {"asset_id": world.mower.asset_id, "title": "x", "meter_interval": "-5"})
    # A sensor reading can be below zero (a freezer).
    sensor = world.maintenance.add_task(world.fridge.asset_id, "Freezer temp", trigger_type="sensor")
    assert run(world, "maintenance.reading", task_id=sensor.task_id, value="-18")[0].summary == "Log -18 for Freezer temp on Fridge"


def test_documents(world, tmp_path):
    source = tmp_path / "manual.pdf"
    source.write_bytes(b"%PDF-1.4 placeholder")
    world.maintenance.add_document(world.mower.asset_id, source)
    assert asset_page(world, world.mower.asset_id, TODAY)["documents"] == [{"name": "manual.pdf"}]
    proposal, done = run(world, "asset.document_remove", asset_id=world.mower.asset_id, filename="manual.pdf")
    assert proposal.summary == "Remove manual.pdf from Mower"
    assert world.maintenance.get_asset(world.mower.asset_id).documents == []
    assert world.maintenance.document_path(world.mower.asset_id, "manual.pdf").exists()  # kept for undo
    world.actions.undo(world, done.proposal_id)
    assert world.maintenance.get_asset(world.mower.asset_id).documents == ["manual.pdf"]


def test_every_kind_has_a_form():
    for key, record in RECORDS.items():
        assert {f"{key}.add", f"{key}.edit", f"{key}.delete"} <= set(ACTION_TYPES)
        assert [f["name"] for f in form_spec()[key]["fields"]] == [f.name for f in record.fields]
    assert {"maintenance.reading", "asset.reading", "asset.document_remove"} <= set(ACTION_TYPES)


def test_the_endpoints_and_a_child(world, tmp_path):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.get("/api/equipment?scope=garage").json()["assets"][0]["name"] == "Mower"
    assert client.get(f"/api/assets/{world.mower.asset_id}").json()["name"] == "Mower"
    assert client.get("/api/assets/nope").status_code == 404

    sent = client.post(f"/api/assets/{world.mower.asset_id}/documents", content=b"receipt",
                       headers={"X-Filename": "../receipt.txt"})
    assert sent.json()["added"] == "receipt.txt"
    got = client.get(f"/api/assets/{world.mower.asset_id}/documents/receipt.txt")
    assert got.status_code == 200 and got.content == b"receipt"
    assert client.get(f"/api/assets/{world.mower.asset_id}/documents/secret.txt").status_code == 404

    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert client.get("/api/equipment?scope=garage").status_code == 403
    assert client.get(f"/api/assets/{world.mower.asset_id}").status_code == 403
    assert client.get("/api/equipment?scope=greenhouse").status_code == 200
