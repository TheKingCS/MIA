"""The development dashboard (DEC-0068/0070, core/work_dashboard.py): the
device's owner sees the work, the queue and the history; nobody else does."""

from datetime import datetime, timezone

from core import work_activity as activity
from core import work_dashboard as dash
from core import work_tasks as tasks_mod
from tests.engine_world import build_world


def _world(tmp_path, monkeypatch):
    w = build_world(tmp_path, monkeypatch)
    w.profiles.create_profile("Owner", password="a-good-password", make_active=False)
    return w


def test_only_the_devices_first_real_account_sees_it(tmp_path, monkeypatch):
    w = _world(tmp_path, monkeypatch)
    owner = dash.owner_id(w)
    assert owner and dash.allowed(w, owner)
    assert not dash.allowed(w, w.me.profile_id) and not dash.allowed(w, "")


def test_the_page_shows_the_queue_the_work_and_the_history(tmp_path):
    folder, log = tmp_path / "tasks", tmp_path / "activity.jsonl"
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="Built", status="done"), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0002", title="Next", depends=["T-0001"]), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0003", title="Waiting on Zac", status="review", branch="lab/x"), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0004", title="Later", depends=["T-0002"]), folder)
    at = datetime(2026, 11, 3, tzinfo=timezone.utc)
    activity.record("QA Engineer (ollama)", "review", "T-0003", "approve: looks right", log, at)
    activity.record("claude", "note", "T-0002", "the relay part", log, at)
    p = dash.page(None, tasks_dir=folder, log=log)
    assert [t["id"] for t in p["queue"]] == ["T-0003"] and p["queue"][0]["verdict"] == "approve"
    statuses = {t["id"]: t["status"] for t in p["tasks"]}
    assert statuses == {"T-0003": "review", "T-0002": "ready", "T-0004": "open"}
    assert next(t for t in p["tasks"] if t["id"] == "T-0004")["waiting_on"] == ["T-0002"]
    assert [d["id"] for d in p["done"]] == ["T-0001"] and p["summary"]["review"] == 1
    assert [e["task"] for e in dash.page(None, "relay", tasks_dir=folder, log=log)["activity"]] == ["T-0002"]


def test_without_the_repo_it_says_so(tmp_path):
    assert dash.page(None, tasks_dir=tmp_path / "nowhere") == {"available": False}
