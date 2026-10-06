"""
DEC-0017 (2026-10-06): the web shell and Home dashboard, assembled in
core/web_surfaces.py so web/ holds no logic. The sidebar is the
person's own (child-safe, tucked-away apps hidden), Home is the
concept's dashboard: greeting, Today's Focus with each item's action,
Upcoming, glance cards.
"""

from datetime import date, datetime, timedelta

import pytest

from core.actions import ActionCenter
from core.child_accounts import make_child
from core.focus_presets import set_app_visible
from core.web_surfaces import APPS, dashboard, date_text, greeting, plural, shell
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.budget.add_bill("Electric", 120.0, (TODAY - timedelta(days=1)).isoformat(), recurrence="monthly")
    return context


def test_pure_bits():
    assert date_text(date(2026, 9, 16)) == "Wed, Sep 16, 2026"
    assert greeting(7, "Robin") == "Good morning, Robin"
    assert greeting(13, "Robin") == "Good afternoon, Robin"
    assert greeting(21, None) == "Good evening"
    assert len({a.module_id for a in APPS}) == len(APPS)
    assert (plural(1, "recipe"), plural(2, "property", "properties")) == ("1 recipe", "2 properties")
    from core.web_surfaces import tool_label

    assert tool_label("add_maintenance_task") == "Add maintenance task"
    assert tool_label("get_life_events") == "See life events" and tool_label("add_skill_xp") == "Add skill XP"


def test_the_shell_is_the_persons_own(world):
    data = shell(world, TODAY)
    assert data["person"]["name"] == "Robin" and data["person"]["level"] == 1
    ids = [a["id"] for a in data["apps"]]
    assert ids[:2] == ["web_home", "dashboard"] and "budget" in ids and "real_estate" in ids
    assert all(a["page"] for a in data["apps"])
    assert "Workshop" in data["on_pc_only"]

    set_app_visible(world, "kitchen", False)
    assert "kitchen" not in [a["id"] for a in shell(world, TODAY)["apps"]]


def test_a_child_sees_only_child_apps(world):
    make_child(world, world.me.profile_id, [world.other.profile_id])
    data = shell(world, TODAY)
    ids = {a["id"] for a in data["apps"]}
    assert data["person"]["child"]
    assert not ids & {"budget", "real_estate", "garage"}
    assert {"web_home", "dashboard", "missions", "kitchen"} <= ids
    page = dashboard(world, datetime.combine(TODAY, datetime.min.time()).replace(hour=9))
    assert page["child"] and not any(c["app"] == "budget" for c in page["glance"])


def test_the_dashboard(world):
    page = dashboard(world, datetime.combine(TODAY, datetime.min.time()).replace(hour=9))
    assert page["greeting"] == "Good morning, Robin"
    [bill] = [f for f in page["focus"] if f["title"] == "Pay Electric"]
    assert bill["when"] == "overdue" and bill["action"]["kind"] == "bill.pay" and bill["page"] == "money.html"
    assert any(c["app"] == "budget" and c["tone"] == "attention" for c in page["glance"])
    assert page["saying"] and [q["id"] for q in page["quick_actions"]][:2] == ["quick_add", "voice"]


def test_the_endpoints(world):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    assert client.get("/api/shell").status_code == 401
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.get("/api/shell").json()["person"]["name"] == "Robin"
    assert client.get("/api/dashboard").json()["focus"]


# ------------------------------------------------------------------ the Apps page


def _module_descriptions():
    """Every module's id and own description, read from modules/*/module.py."""
    import ast
    from pathlib import Path

    found = {}
    for path in sorted(Path(__file__).resolve().parent.parent.glob("modules/*/module.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                values = {t.id: n.value for n in node.body if isinstance(n, ast.Assign)
                          for t in n.targets if isinstance(t, ast.Name)}
                if "module_id" in values:
                    found[ast.literal_eval(values["module_id"])] = ast.literal_eval(values["description"])
    return found


def test_every_module_is_on_the_apps_page_with_its_own_description():
    from core.web_surfaces import APPS_BY_ID, GROUPS

    modules = _module_descriptions()
    assert set(modules) == set(APPS_BY_ID)
    for module_id, description in modules.items():
        assert APPS_BY_ID[module_id].description == description, module_id
        assert APPS_BY_ID[module_id].group in GROUPS


def test_every_assistant_tool_belongs_to_an_app():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    domains = set()
    for path in list(root.glob("core/*.py")) + list(root.glob("modules/*/*.py")):
        domains |= set(re.findall(r'domain="([a-z_]+)"', path.read_text(encoding="utf-8")))
    covered = {d for a in APPS for d in a.domains}
    assert domains - covered == set()


def test_the_apps_page(world):
    from core.assistant_actions import AssistantAction
    from core.web_surfaces import apps_page

    world.assistant_actions.register(AssistantAction(
        "add_bill", "Add a new bill. Use it when the user says so.", {"type": "object", "properties": {}},
        lambda c, a: "", domain="budget"))
    page = apps_page(world)
    apps = {a["id"]: a for g in page["groups"] for a in g["apps"]}
    assert apps["budget"]["on_web"] and apps["budget"]["tools"] == [
        {"name": "add_bill", "does": "Add bill", "detail": "Add a new bill."}]
    assert not apps["workshop"]["on_web"] and apps["workshop"]["ask"]
    assert not apps["module_browser"]["can_hide"] and apps["kitchen"]["can_hide"]
    assert page["counts"]["apps"] == len(apps)

    set_app_visible(world, "kitchen", False)
    assert not {a["id"]: a for g in apps_page(world)["groups"] for a in g["apps"]}["kitchen"]["shown"]


def test_a_child_sees_only_their_apps_and_tools(world):
    from core.assistant_actions import AssistantAction
    from core.web_surfaces import apps_page

    world.assistant_actions.register(AssistantAction(
        "add_bill", "Add a new bill.", {"type": "object", "properties": {}}, lambda c, a: "", domain="budget"))
    make_child(world, world.me.profile_id, [world.other.profile_id])
    ids = {a["id"] for g in apps_page(world)["groups"] for a in g["apps"]}
    assert "budget" not in ids and "missions" in ids


def test_show_and_hide_go_through_the_action_contract(world):
    from core.actions import ActionError

    proposal = world.actions.propose(world, "app.visibility", {"module_id": "kitchen", "visible": False})
    assert proposal.summary == "Hide Kitchen from your apps"
    done = world.actions.approve(world, proposal.proposal_id)
    assert "kitchen" not in [a["id"] for a in shell(world, TODAY)["apps"]]
    world.actions.undo(world, done.proposal_id)
    assert "kitchen" in [a["id"] for a in shell(world, TODAY)["apps"]]
    with pytest.raises(ActionError, match="always stays"):
        world.actions.propose(world, "app.visibility", {"module_id": "module_browser", "visible": False})
    with pytest.raises(ActionError):
        world.actions.propose(world, "app.visibility", {"module_id": "nope"})


def test_favorite_apps_in_the_order_starred_with_undo(world):
    from core.web_surfaces import apps_page

    for app_id in ("workout", "kitchen"):
        proposal = world.actions.propose(world, "app.favorite", {"module_id": app_id, "favorite": True})
        done = world.actions.approve(world, proposal.proposal_id)
    assert proposal.summary == "Add Kitchen to your favorites"
    page = apps_page(world)
    assert page["favorites"] == ["workout", "kitchen"]
    assert {a["id"] for g in page["groups"] for a in g["apps"] if a["favorite"]} == {"workout", "kitchen"}
    world.actions.undo(world, done.proposal_id)
    assert apps_page(world)["favorites"] == ["workout"]
    proposal = world.actions.propose(world, "app.favorite", {"module_id": "workout", "favorite": False})
    assert proposal.summary == "Remove Workout from your favorites"
    world.actions.approve(world, proposal.proposal_id)
    assert apps_page(world)["favorites"] == []


def test_a_child_cannot_favorite_an_app_they_cannot_open(world):
    from core.actions import ActionError

    make_child(world, world.me.profile_id, [world.other.profile_id])
    with pytest.raises(ActionError):
        world.actions.propose(world, "app.favorite", {"module_id": "budget"})
    assert world.actions.propose(world, "app.favorite", {"module_id": "kitchen"}).status == "proposed"


def test_the_published_examples_match_the_app_list():
    """The public preview renders docs/schema/*.example.json; when a web
    screen is added, its examples must be regenerated (2026-10-06: the
    preview's sidebar had no Apps link)."""
    import json
    from pathlib import Path

    schema = Path(__file__).resolve().parent.parent / "docs" / "schema"
    shell_ids = [a["id"] for a in json.loads((schema / "shell.example.json").read_text(encoding="utf-8"))["apps"]]
    assert shell_ids == [a.module_id for a in APPS if a.page]
    example = json.loads((schema / "apps.example.json").read_text(encoding="utf-8"))
    assert {a["id"] for g in example["groups"] for a in g["apps"]} == {a.module_id for a in APPS}
    assert {a["id"] for g in example["groups"] for a in g["apps"] if a["on_web"]} == {a.module_id for a in APPS if a.page}
