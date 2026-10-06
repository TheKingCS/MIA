"""
The action contract and live updates (Phase 2 foundation, DEC-0013,
2026-10-05): Propose → Approve → Execute → Record → Undo, the endpoints
the web front end uses, and the state version that tells it to refresh.
"""

import json
from datetime import date, timedelta

import pytest

from core import live, schema_check
from core.actions import ACTION_TYPES, ActionCenter, ActionError
from core.child_accounts import ASK_A_PARENT, make_child
from core.context_assembler import assemble_life_state_v2
from core.gamification import SkillWeight
from core.life_events import events_for
from tests.engine_world import build_world

TODAY = date.today()
ACTION_SCHEMA = schema_check.load("action.schema.json")
STATE_SCHEMA = schema_check.load("life_state.schema.json")


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.bill = context.budget.add_bill("Electric", 120.0, (TODAY - timedelta(days=1)).isoformat(),
                                           recurrence="monthly")
    return context


def _due_action(state, title):
    return next(i["action"] for i in state["due"]["items"] if i["title"] == title)


def test_due_items_carry_the_action_to_propose(world):
    asset = world.maintenance.add_asset("Mower", "Power Equipment")
    task = world.maintenance.add_task(asset.asset_id, "Sharpen blades", interval_days=30,
                                      last_completed=(TODAY - timedelta(days=40)).isoformat())
    project = world.projects.add_project("Shed")
    todo = world.tasks.add_task(project.project_id, "Buy screws", due_date=TODAY.isoformat())
    state = assemble_life_state_v2(world)
    assert _due_action(state, "Pay Electric") == {"kind": "bill.pay", "label": "Mark paid",
                                                  "params": {"bill_id": world.bill.bill_id}}
    assert _due_action(state, "Sharpen blades: Mower")["params"] == {"task_id": task.task_id}
    assert _due_action(state, "Buy screws") == {"kind": "task.done", "label": "Done",
                                                "params": {"task_id": todo.task_id}}
    assert schema_check.errors(state, STATE_SCHEMA) == []


def test_the_five_steps(world):
    center = world.actions
    proposal = center.propose(world, "bill.pay", {"bill_id": world.bill.bill_id})
    assert proposal.summary == "Mark Electric paid ($120.00)" and proposal.status == "proposed"
    assert world.budget.all_expenses() == []  # proposing changes nothing
    assert schema_check.errors(proposal.as_dict(), ACTION_SCHEMA) == []
    assert [p.proposal_id for p in center.pending(world.me.profile_id)] == [proposal.proposal_id]
    before = live.version()
    done = center.approve(world, proposal.proposal_id)
    assert (done.status, done.result) == ("executed", "Electric is marked paid ($120.00).")
    assert done.as_dict()["undoable"] and live.version() > before
    [event] = events_for(world, types=["bill_paid"])  # recorded, as the person's own doing
    assert (event.source, event.profile_id) == ("manual", world.me.profile_id)
    assert not any(i["title"] == "Pay Electric" for i in assemble_life_state_v2(world)["due"]["items"])
    with pytest.raises(ActionError, match="already executed"):
        center.approve(world, proposal.proposal_id)
    undone = center.undo(world, proposal.proposal_id)
    assert undone.status == "undone" and world.budget.all_expenses() == []
    assert world.budget.get_bill(world.bill.bill_id).last_paid_date is None
    assert any(i["title"] == "Pay Electric" for i in assemble_life_state_v2(world)["due"]["items"])
    assert [e.type for e in events_for(world)][:2] == ["undone", "bill_paid"]  # history kept


def test_bad_proposals_and_other_people(world):
    center = world.actions
    with pytest.raises(ActionError, match="can't do"):
        center.propose(world, "house.sell", {})
    with pytest.raises(ActionError, match="isn't there"):
        center.propose(world, "bill.pay", {"bill_id": "nope"})
    with pytest.raises(ActionError, match="number"):
        center.propose(world, "bill.pay", {"bill_id": world.bill.bill_id, "amount": "lots"})
    mine = center.propose(world, "bill.pay", {"bill_id": world.bill.bill_id, "amount": 99})
    assert mine.summary == "Mark Electric paid ($99.00)"
    world.profiles.set_active_profile(world.other.profile_id)
    with pytest.raises(KeyError):  # someone else's proposal is invisible
        center.approve(world, mine.proposal_id)
    assert center.pending(world.other.profile_id) == []


def test_rejecting_and_undo_only_while_latest(world):
    center = world.actions
    no = center.propose(world, "bill.pay", {"bill_id": world.bill.bill_id})
    assert center.reject(world, no.proposal_id).status == "rejected"
    first = center.approve(world, center.propose(world, "bill.pay", {"bill_id": world.bill.bill_id}).proposal_id)
    water = world.budget.add_bill("Water", 30.0, TODAY.isoformat())
    center.approve(world, center.propose(world, "bill.pay", {"bill_id": water.bill_id}).proposal_id)
    with pytest.raises(ActionError, match="newer"):
        center.undo(world, first.proposal_id)


def test_tasks_routines_and_income(world):
    center = world.actions
    project = world.projects.add_project("Shed")
    todo = world.tasks.add_task(project.project_id, "Buy screws")
    assert center.approve(world, center.propose(world, "task.done", {"task_id": todo.task_id}).proposal_id).result \
        == '"Buy screws" is done.'
    with pytest.raises(ActionError, match="already done"):
        center.propose(world, "task.done", {"task_id": todo.task_id})
    template = world.recurring_missions.add_template(
        "Dishes", "Do the dishes ({target:g}x)", 2, 0, 10, 25, TODAY.isoformat(),
        daily_skill_rewards=[SkillWeight("household_management", 5)])
    logged = center.approve(world, center.propose(world, "routine.log", {"template_id": template.template_id}).proposal_id)
    assert logged.result == "Dishes: 1 of 2."
    source = world.budget.add_income_source("Pay", 800.0, TODAY.isoformat())
    paid = center.approve(world, center.propose(world, "income.receive", {"source_id": source.source_id}).proposal_id)
    assert paid.result == "Pay is marked received ($800.00)."


def test_a_child_can_only_take_child_actions(world):
    kid = world.profiles.create_profile("Ari", make_active=False)
    make_child(world, kid.profile_id, [world.me.profile_id])
    world.profiles.set_active_profile(kid.profile_id)
    with pytest.raises(ActionError, match="grown-ups"):
        world.actions.propose(world, "bill.pay", {"bill_id": world.bill.bill_id})
    project = world.projects.add_project("Room")
    todo = world.tasks.add_task(project.project_id, "Tidy desk")
    assert world.actions.propose(world, "task.done", {"task_id": todo.task_id}).status == "proposed"
    assert {k for k, a in ACTION_TYPES.items() if a.child_ok} == {"task.done", "routine.log"}


def test_mia_proposed_actions_are_recorded_as_hers(world):
    proposal = world.actions.propose(world, "bill.pay", {"bill_id": world.bill.bill_id}, proposed_by="mia")
    world.actions.approve(world, proposal.proposal_id)
    [event] = events_for(world, types=["bill_paid"])
    assert event.source == "assistant"


def test_any_write_moves_the_live_version(world):
    before = live.version()
    world.kitchen.add_grocery_item("Eggs", 12)
    middle = live.version()
    world.life_events.record("task_done", "x")
    assert before < middle < live.version()


# ------------------------------------------------------------------ the server


@pytest.fixture
def client(world):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    app = server_app.create_app(world)
    test_client = TestClient(app)
    token = test_client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    test_client.token = token
    return test_client


def test_the_endpoints_run_the_contract(client, world):
    kinds = client.get("/api/actions/kinds").json()["kinds"]
    assert {k["kind"] for k in kinds} == set(ACTION_TYPES)
    proposal = client.post("/api/actions/propose", json={"kind": "bill.pay",
                                                         "params": {"bill_id": world.bill.bill_id}}).json()
    assert proposal["summary"] == "Mark Electric paid ($120.00)"
    assert [p["proposal_id"] for p in client.get("/api/actions").json()["proposals"]] == [proposal["proposal_id"]]
    done = client.post(f"/api/actions/{proposal['proposal_id']}/approve").json()
    assert done["status"] == "executed" and done["undoable"] is True
    assert schema_check.errors(done, ACTION_SCHEMA) == []
    assert client.post(f"/api/actions/{proposal['proposal_id']}/approve").status_code == 409
    assert client.post(f"/api/actions/{proposal['proposal_id']}/undo").json()["status"] == "undone"
    assert client.post("/api/actions/nope/approve").status_code == 404
    bad = client.post("/api/actions/propose", json={"kind": "bill.pay", "params": {"bill_id": "nope"}})
    assert bad.status_code == 409 and "isn't there" in bad.json()["detail"]
    assert client.post("/api/actions/propose", json={"kind": "x"}, headers={"Authorization": ""}).status_code == 401


def test_live_version_and_stream(client, world):
    version = client.get("/api/live/version").json()["version"]
    assert version == live.version()
    assert client.get("/api/live?token=wrong&once=1").status_code == 401
    with client.stream("GET", f"/api/live?token={client.token}&since=-1&once=1") as response:
        body = "".join(response.iter_text())
    assert body.startswith("event: state\ndata: ") and json.loads(body.split("data: ")[1])["version"] == version


def test_the_web_front_end_and_schemas_are_served(client):
    page = client.get("/web/")
    assert page.status_code == 200 and "mia.js" in page.text
    assert "window.MIA" in client.get("/web/mia.js").text
    assert client.get("/schema/life_state.example.json").json()["version"] == 2
    assert client.get("/").status_code == 200  # the phone app keeps the root


def test_with_phone_access_off_outside_requests_are_turned_away(client, world):
    class Off:
        enabled = False

    world.phone_server = Off()
    assert client.get("/api/live/version").status_code == 200  # the desktop's own view
    blocked = client.get("/api/live/version", headers={"X-Forwarded-For": "100.64.0.2"})
    assert blocked.status_code == 403 and "Phone access is off" in blocked.json()["detail"]
    world.phone_server.enabled = True
    assert client.get("/api/live/version", headers={"X-Forwarded-For": "100.64.0.2"}).status_code == 200


def test_desktop_sessions_are_not_phones(world):
    from core.phone_server import PhoneServer
    import server.app as server_app

    world.voice = world.llm = world.push_subscriptions = None
    server = PhoneServer(world)
    server._app = server_app.create_app(world)
    token = server.local_session(world.me.profile_id)
    assert server._app.state.sessions[token] == world.me.profile_id
    assert token in server._local_tokens


def test_web_home_address():
    from modules.web_home.module import web_home_url

    assert web_home_url("http://127.0.0.1:8765", "abc") == "http://127.0.0.1:8765/web/#token=abc"
    assert web_home_url("http://h", "t", 1.25, True) == "http://h/web/?scale=1.25&contrast=high#token=t"


def test_the_pi_check_verdict():
    from tools.web_check import verdict

    assert verdict(56, 373, 60, 800).startswith("PASS")
    assert verdict(4000, 900, 20, 20000) == ("CHECK: slow browser start (20 s), slow to load (4000 ms), "
                                             "heavy (900 MB), choppy (20 fps).")


def test_undo_takes_back_the_xp_and_the_win(world):
    """2026-10-06, found driving the web Home: undoing "Done" on a
    maintenance task left its XP (the config held in memory was never
    re-read) and left it listed as a recent win."""
    from core.context_assembler import assemble_life_state_v2

    asset = world.maintenance.add_asset("Mower", "Power Equipment")
    task = world.maintenance.add_task(asset.asset_id, "Sharpen blades", interval_days=30,
                                      last_completed=(TODAY - timedelta(days=40)).isoformat())
    me = world.me.profile_id
    xp_before = world.profiles.get_profile(me).total_xp
    proposal = world.actions.propose(world, "maintenance.done", {"task_id": task.task_id})
    done = world.actions.approve(world, proposal.proposal_id)
    assert world.profiles.get_profile(me).total_xp > xp_before
    assert any(w["type"] == "maintenance_done" for w in assemble_life_state_v2(world)["recent_wins"]["latest"])

    world.actions.undo(world, done.proposal_id)
    assert world.profiles.get_profile(me).total_xp == xp_before
    world.config.save()  # the next save mustn't write the XP back
    assert world.profiles.get_profile(me).total_xp == xp_before
    latest = assemble_life_state_v2(world)["recent_wins"]["latest"]
    assert not any(w["type"] in ("maintenance_done", "undone") for w in latest)
    assert any(e.type == "maintenance_done" for e in world.life_events.all_events())  # history kept


def test_undo_through_a_persons_view_takes_back_the_xp(world):
    """The phone and the web run on a person's view (ScopedView), whose
    config lives on the main context underneath; undo must reload it there."""
    from core.personal_data import ScopedView

    view = ScopedView(world, ())
    asset = world.maintenance.add_asset("Mower", "Power Equipment")
    task = world.maintenance.add_task(asset.asset_id, "Sharpen blades", interval_days=30,
                                      last_completed=(TODAY - timedelta(days=40)).isoformat())
    me = world.me.profile_id
    xp_before = world.profiles.get_profile(me).total_xp
    done = world.actions.approve(view, world.actions.propose(view, "maintenance.done",
                                                             {"task_id": task.task_id}).proposal_id)
    assert world.profiles.get_profile(me).total_xp > xp_before
    world.actions.undo(view, done.proposal_id)
    world.config.save()
    assert world.profiles.get_profile(me).total_xp == xp_before
