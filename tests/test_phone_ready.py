"""
DEC-0019 (2026-10-07): MIA's engine runs on the phone. The phone has no
Qt, no desktop voice, no Plaid, no psutil, no offline library and no Web
Push sender, so the engine and server must start, serve every screen and
take an action without any of them. This builds both in a fresh process
with those packages blocked, so a new hard import of one fails here, not
on someone's phone.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DESKTOP_ONLY = ("PySide6", "numpy", "sounddevice", "vosk", "piper", "libzim", "serial", "plaid", "psutil",
                "pywebpush", "py_vapid", "requests")

_SCRIPT = r"""
import importlib.abc, json, os, sys
from pathlib import Path

BLOCKED = set(json.loads(sys.argv[1]))
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ModuleNotFoundError(f"{name} is desktop-only (blocked for the phone check)")
sys.meta_path.insert(0, Block())

root, home = Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(root))
import core.config_manager as config_module, core.profile_manager as profile_module
config_module._CONFIG_FILE = home / "config.json"
profile_module._DATA_PROFILES_DIR = home / "profiles"
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.app_context import AppContext
from core.profile_manager import ProfileManager
from core.mission_manager import MissionManager
import core.mission_manager as mission_module
mission_module._DATA_DIR, mission_module._MISSIONS_FILE = home, home / "missions.json"

import core.core_runtime  # the whole headless engine imports cleanly
import server.app as server_app
from fastapi.testclient import TestClient

context = AppContext(config=ConfigManager(), events=EventBus())
context.profiles = ProfileManager(context)
me = context.profiles.create_profile("Robin", make_active=True)
context.profiles.set_password(me.profile_id, "pw")
context.missions = MissionManager(context)
from core.actions import ActionCenter
context.actions = ActionCenter()
client = TestClient(server_app.create_app(context))
token = client.post("/api/login", json={"profile_id": me.profile_id, "password": "pw"}).json()["token"]
client.headers.update({"Authorization": f"Bearer {token}"})
codes = {p: client.get(p).status_code for p in ("/api/shell", "/api/dashboard", "/api/missions", "/api/skills")}
proposal = client.post("/api/actions/propose", json={"kind": "mission.add", "params": {"name": "Phone"}}).json()
assert "proposal_id" in proposal, proposal
done = client.post(f"/api/actions/{proposal['proposal_id']}/approve").json()
loaded = sorted({m.split(".")[0] for m in sys.modules} & BLOCKED)
print(json.dumps({"codes": codes, "action": done.get("status"), "loaded": loaded}))
"""


def test_the_engine_and_server_run_without_desktop_only_packages(tmp_path):
    result = subprocess.run([sys.executable, "-c", _SCRIPT, json.dumps(DESKTOP_ONLY), str(ROOT), str(tmp_path)],
                            capture_output=True, text=True, timeout=120, cwd=tmp_path)
    assert result.returncode == 0, result.stderr[-3000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert set(report["codes"].values()) == {200}, report
    assert report["action"] == "executed" and report["loaded"] == []
