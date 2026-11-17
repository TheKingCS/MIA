"""The MIA Runtime (core/runtime.py, DEC-0155): the whole MIA built with no window, the same services and tools the
desktop has, her schedule on a thread, and how she says she's doing."""

import importlib
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def elsewhere(tmp_path, monkeypatch):
    """Every file MIA's core keeps (anything under the repo's data/ or config/config.json) moved to a temporary
    folder: each core module the runtime loads has its paths under data/ re-pointed, the generalised form of the
    server tests' fixture."""
    source = (ROOT / "core" / "runtime.py").read_text(encoding="utf-8") + (ROOT / "core" / "assistant_tools.py").read_text(
        encoding="utf-8") + (ROOT / "core" / "background_jobs.py").read_text(encoding="utf-8")
    for name in sorted(set(re.findall(r"from (core\.\w+) import", source)) | {
            f"core.{n}" for n in re.findall(r"from core import (\w+)", source)}):
        try:
            importlib.import_module(name)
        except ImportError:
            pass
    data, moved = ROOT / "data", tmp_path / "data"
    moved.mkdir()
    for seed in data.iterdir():  # the small files MIA ships with (skill definitions, pathways...)
        if seed.is_file() and seed.stat().st_size < 2_000_000:
            (moved / seed.name).write_bytes(seed.read_bytes())
    for name, module in list(sys.modules.items()):
        if not name.startswith(("core.", "server.")) or module is None:
            continue
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == data or data in value.parents):
                monkeypatch.setattr(module, attr, moved / value.relative_to(data))
    import core.config_manager

    monkeypatch.setattr(core.config_manager, "_CONFIG_FILE", tmp_path / "config.json")
    return moved


def test_the_runtime_imports_no_qt_and_nothing_from_the_gui():
    """In a fresh Python: importing the runtime loads no PySide6 and no gui code, so MIA OS and the Pi need neither
    to run her."""
    code = ("import sys; import core.runtime; "
            "bad = [m for m in sys.modules if m.split('.')[0] in ('PySide6', 'gui')]; print(bad); sys.exit(1 if bad else 0)")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180, cwd=ROOT)
    assert done.returncode == 0, done.stdout + done.stderr[-2000:]


def test_the_desktop_builds_its_services_through_the_same_function_as_the_runtime():
    source = (ROOT / "core" / "application.py").read_text(encoding="utf-8")
    assert "build_services(self.context)" in source
    assert "self.context.missions = " not in source and "self.context.budget = " not in source  # none built by hand


def test_a_headless_mia_has_every_service_and_tool_the_desktop_has(elsewhere):
    from core.background_jobs import JOBS
    from core.runtime import Runtime

    runtime = Runtime(take_lock=False)
    context = runtime.context
    # What the headless builder lacked before this (core/core_runtime.py): the gate, conversations, insights...
    for name in ("communication", "conversations", "insights", "finance", "homestead", "workout", "classroom",
                 "textbooks", "plans", "search", "online_reminders", "push_subscriptions", "store_lock", "missions",
                 "budget", "personal_data", "inbox", "inbox_mail", "plaid", "kitchen"):
        assert getattr(context, name, None) is not None, name
    tools = context.assistant_actions._actions
    assert len(tools) >= 400, len(tools)
    from tests.assistant_registry import build_desktop_registry

    assert set(tools) == set(build_desktop_registry()._actions)  # the very same tools as the desktop window's
    for tool in ("add_alarm", "what_to_wear", "run_taught_skill", "do_with_this", "get_sun_moon_info", "set_theme"):
        assert tool in tools, tool
    assert runtime.scheduler.names() == [name for name, _, _ in JOBS]
    said = context.assistant_actions.execute(context, "set_theme", {"theme_id": "dark_field"})
    assert "theme" in said.lower()  # plain words either way: a theme set, or no window here


def test_the_runtime_runs_the_schedule_on_a_thread_and_says_how_it_is_doing(elsewhere, monkeypatch):
    from core.runtime import Runtime

    runtime = Runtime(take_lock=False)
    ran = []
    monkeypatch.setattr(runtime.scheduler._jobs["alarms"], "run", lambda: ran.append("alarms"))
    monkeypatch.setattr(runtime.scheduler._jobs["power"], "run", lambda: 1 / 0)
    for job in runtime.scheduler._jobs.values():
        job.due = float("inf")
    runtime.scheduler._jobs["alarms"].due = 0
    runtime.scheduler._jobs["power"].due = 0
    assert runtime.health()["running"] is False
    runtime.start(serve=False)
    try:
        for _ in range(100):
            if ran and runtime.scheduler._jobs["power"].runs:
                break
            time.sleep(0.05)
        health = runtime.health()
    finally:
        runtime.stop()
    assert ran and health["running"] and health["window"] is False and health["started_at"]
    assert health["jobs_failing"] == ["power"] and len(health["jobs"]) == 13
    assert health["services"] >= 90 and health["tools"] >= 400
    assert runtime.health()["running"] is False  # stopped cleanly


def test_a_second_mia_on_the_same_data_folder_is_refused(elsewhere, monkeypatch):
    from core import instance_lock
    from core.runtime import Runtime, main

    monkeypatch.setattr(instance_lock, "acquire", lambda *a, **k: False)
    with pytest.raises(RuntimeError, match="already running"):
        Runtime()
    assert main() == 1


def test_the_health_endpoint_reports_the_runtime_to_a_signed_in_person(elsewhere):
    from fastapi.testclient import TestClient

    from core.runtime import Runtime
    from server.app import create_app

    runtime = Runtime(take_lock=False)
    alice = runtime.context.profiles.create_profile("Alice", password="hunter2")
    client = TestClient(create_app(runtime.context))
    assert client.get("/api/runtime/health").status_code == 401
    token = client.post("/api/login", json={"profile_id": alice.profile_id, "password": "hunter2"}).json()["token"]
    health = client.get("/api/runtime/health", headers={"Authorization": f"Bearer {token}"}).json()
    assert health["window"] is False and health["running"] is False and len(health["jobs"]) == 13
