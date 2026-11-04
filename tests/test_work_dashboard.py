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


def test_the_board_says_whose_move_it_is(tmp_path, monkeypatch):
    """Zac: "easy to view and understand the workflow ... what is building, who is building it"."""
    from core import work_review as rv
    from core.work_agents import parse
    from tests.test_work_loop import REGISTRY

    data = {**REGISTRY, "providers": {**REGISTRY["providers"], "codex": {"kind": "cli", "command": "codex",
                                                                       "can": ["review"]}},
            "roles": REGISTRY["roles"] + [{"role": "Security Auditor", "provider": "codex", "tier": "review"}]}
    monkeypatch.setattr("core.work_agents.load", lambda *a: parse(data))
    folder, log = tmp_path / "tasks", tmp_path / "activity.jsonl"
    tasks_mod.save(tasks_mod.Task(id="T-0001", title="Being built", status="claimed", owner="Software Engineer (claude-code)"), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0002", title="One review in", status="review", branch="lab/x"), folder)
    tasks_mod.save(tasks_mod.Task(id="T-0003", title="Ready to start"), folder)
    w = "Software Engineer (claude-code)"
    activity.record(w, "loop", "T-0001", "claim: core/x.py", log)
    activity.record(w, "loop", "T-0001", "lab: x", log)
    activity.record(w, "loop", "T-0002", "write: changed it", log)
    activity.record("QA Engineer (ollama)", "review", "T-0002", "approve: right", log)
    board = dash.page(None, tasks_dir=folder, log=log)["board"]
    building, = board["building"]
    assert building["id"] == "T-0001" and building["next"] == "Software Engineer (claude-code) is on it: next, write."
    assert [s["done"] for s in building["steps"]] == [True, True, False, False, False]
    waiting, = board["review"]
    assert waiting["needed"] == 2 and waiting["approvals"] == ["ollama"] and "1 of 2" in waiting["next"]
    assert board["next"][0]["command"] == 'python -m tools.work run T-0003 --as "<role>"'
    activity.record("Security Auditor (codex)", "review", "T-0002", "approve: fine", log)
    yours, = dash.page(None, tasks_dir=folder, log=log)["board"]["yours"]
    assert yours["id"] == "T-0002" and yours["command"] == "python -m tools.work approve T-0002"
    assert [e["action"] for e in yours["timeline"]] == ["loop", "review", "review"]
    activity.record("Security Auditor (codex)", "review", "T-0002", "changes: a hole", log)
    stuck, = dash.page(None, tasks_dir=folder, log=log)["board"]["review"]
    assert "Security Auditor (codex) asked for changes" in stuck["next"] and rv.open_objections("T-0002", log)


def test_its_own_window_serves_only_this_computer_and_this_run():
    import json as json_mod
    import urllib.error
    import urllib.request

    from tools import dev_window

    server, address = dev_window.serve()
    try:
        port, key = server.server_address[1], address.split("#key=")[1]
        base = f"http://127.0.0.1:{port}"
        assert b"MIA Development" in urllib.request.urlopen(base + "/").read()

        def code(url, headers):
            try:
                return urllib.request.urlopen(urllib.request.Request(url, headers=headers)).status
            except urllib.error.HTTPError as e:
                return e.code

        assert code(base + "/api/dev", {}) == 403 and code(base + "/api/dev", {"X-Dev-Key": "guess"}) == 403
        assert code(f"http://localhost:{port}/", {}) == 403  # another name for here: refused
        assert code(base + "/../core/actions.py", {}) == 404 and code(base + "/mia.js", {}) == 404
        found = json_mod.loads(urllib.request.urlopen(urllib.request.Request(base + "/api/dev",
                                                                            headers={"X-Dev-Key": key})).read())
        assert "board" in found or found == {"available": False}
    finally:
        server.shutdown()


def test_the_window_takes_zacs_messages_only_with_its_key(tmp_path, monkeypatch):
    import json as json_mod
    import time
    import urllib.error
    import urllib.request

    from core import council
    from core.dev_store import DevStore
    from tools import dev_window

    store, repo = DevStore(tmp_path / "dev" / "council"), tmp_path / "council.jsonl"
    monkeypatch.setattr(council, "_store", lambda: store)
    monkeypatch.setattr(council, "REPO_LOG", repo)
    monkeypatch.setattr(council, "here", lambda: ["mia"])
    monkeypatch.setattr("core.self_docs.answer", lambda q, **k: "From my docs.")
    monkeypatch.setattr("core.work_activity.ACTIVITY", tmp_path / "activity.jsonl")
    server, address = dev_window.serve()
    try:
        port, key = server.server_address[1], address.split("#key=")[1]

        def send(body, key_=key):
            request = urllib.request.Request(f"http://127.0.0.1:{port}/api/council", data=json_mod.dumps(body).encode(),
                                             headers={"X-Dev-Key": key_, "Content-Type": "application/json"}, method="POST")
            try:
                return urllib.request.urlopen(request).status
            except urllib.error.HTTPError as e:
                return e.code

        assert send({"text": "hi"}, key_="guess") == 403 and not repo.exists()
        assert send({"text": "  "}) == 400
        assert send({"text": "@mia what's the plan? @codex too"}) == 200
        for _ in range(50):
            if len(store.tail(10)) >= 3 and not dev_window.ASKING:
                break
            time.sleep(0.1)
        said = store.tail(10)
        zac = said[0]
        assert zac["who"] == "zac" and zac["asks"] == ["mia", "codex"] and zac["plan"]["order"] == ["mia", "codex"]
        mia = next(m for m in said if m["who"] == "mia" and m["kind"] == "answer")
        assert mia["text"].startswith("From my docs.") and mia["thread"] == zac["id"]
        skipped = next(m for m in said if m["kind"] == "note")
        assert "Codex isn't available" in skipped["text"]  # here only MIA is: nobody else is called
        assert len(repo.read_text(encoding="utf-8").splitlines()) == 3  # the repo's copy too
    finally:
        server.shutdown()
