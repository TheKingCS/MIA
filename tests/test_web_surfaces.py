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
from core.web_surfaces import APPS, date_text, greeting, home, plural, shell
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


def test_the_shell_is_the_persons_own(world):
    data = shell(world, TODAY)
    assert data["person"]["name"] == "Robin" and data["person"]["level"] == 1
    ids = [a["id"] for a in data["apps"]]
    assert ids[0] == "dashboard" and "budget" in ids and "real_estate" in ids
    assert all(a["page"] for a in data["apps"])
    assert "Maintenance" in data["on_pc_only"]

    set_app_visible(world, "kitchen", False)
    assert "kitchen" not in [a["id"] for a in shell(world, TODAY)["apps"]]


def test_a_child_sees_only_child_apps(world):
    make_child(world, world.me.profile_id, [world.other.profile_id])
    data = shell(world, TODAY)
    ids = {a["id"] for a in data["apps"]}
    assert data["person"]["child"]
    assert not ids & {"budget", "real_estate", "garage"}
    assert {"dashboard", "missions", "kitchen"} <= ids
    page = home(world, datetime.combine(TODAY, datetime.min.time()).replace(hour=9))
    assert page["child"] and not any(c["app"] == "budget" for c in page["glance"])


def test_home_is_the_dashboard(world):
    page = home(world, datetime.combine(TODAY, datetime.min.time()).replace(hour=9))
    assert page["greeting"] == "Good morning, Robin"
    [bill] = [f for f in page["focus"] if f["title"] == "Pay Electric"]
    assert bill["when"] == "overdue" and bill["action"]["kind"] == "bill.pay" and bill["page"] == "finances.html"
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
    assert client.get("/api/home").json()["focus"]
