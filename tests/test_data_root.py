"""Where MIA keeps a person's files (core/data_root.py, MIA_HOME): the code's folder unless it's set; with it set,
nothing at all is written into the code's folder; and tools/move_home copies a MIA to a new home, checked."""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from core import data_root
from tools import move_home

ROOT = Path(__file__).resolve().parent.parent


def test_with_no_setting_her_home_is_the_codes_folder_as_it_always_was():
    if os.environ.get(data_root.ENV):
        pytest.skip("MIA_HOME is set in this environment")
    assert data_root.HOME == ROOT and data_root.DATA_DIR == ROOT / "data" and not data_root.SEPARATE
    assert data_root.CONFIG_DIR == ROOT / "config" and data_root.LOG_DIR == ROOT / "logs"
    assert data_root.work_path("parity.json") == ROOT / "work" / "parity.json"


def test_no_store_works_out_its_own_data_folder_anymore():
    """Every file under core/ and server/ asks core/data_root.py: none builds "<the code>/data" (or config, logs)
    itself, so one can't quietly stay behind when the home moves."""
    own = re.compile(r'parent\.parent / "(data|logs|config)"|(?<![\w.])(_PROJECT_ROOT|ROOT) / "data"')
    found = []
    for path in sorted(list((ROOT / "core").glob("*.py")) + list((ROOT / "server").glob("*.py"))):
        if path.name == "data_root.py":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if own.search(line) and not line.lstrip().startswith("#"):
                found.append(f"{path.relative_to(ROOT)}:{n}")
    assert found == []


RUN = """
import json, sys
from core import data_root
from core.runtime import Runtime
r = Runtime()
r.context.profiles.create_profile("Robin", make_active=True)
r.context.missions.add_mission("A mission in the new home")
for j in r.scheduler._jobs.values():
    j.due = 0
ran = r.scheduler.run_due()
print("RESULT " + json.dumps({"ran": len(ran), "failing": [j["name"] for j in r.scheduler.status() if j["last_error"]],
      "skills": len(r.context.skills.all_skills()), "home": data_root.describe()}))
"""


def _files(folder: Path) -> dict:
    """Every file under a folder (not .git or caches) with its size and modified time."""
    out = {}
    for path in folder.rglob("*"):
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts:
            stat = path.stat()
            out[str(path.relative_to(folder))] = (stat.st_size, stat.st_mtime_ns)
    return out


def test_with_a_home_set_mia_runs_whole_and_writes_nothing_into_the_codes_folder(tmp_path):
    """A fresh Python with MIA_HOME set: the runtime builds, a person and a mission are added, every scheduled job
    runs; her files are under the home, the skill tree still loads from the code's seed files, and not one file
    in the code's folder was added or changed."""
    import json

    home = tmp_path / "mia"
    before = _files(ROOT)
    time.sleep(0.05)
    done = subprocess.run([sys.executable, "-c", RUN], capture_output=True, text=True, timeout=300, cwd=ROOT,
                          env={**os.environ, data_root.ENV: str(home), "QT_QPA_PLATFORM": "offscreen"})
    line = next((l for l in done.stdout.splitlines() if l.startswith("RESULT ")), None)
    assert line, done.stdout[-1500:] + done.stderr[-3000:]
    got = json.loads(line[7:])
    assert got["ran"] == 14 and got["failing"] == [] and got["skills"] > 0  # every job, World Intelligence's and self-repair's too
    assert got["home"] == {"home": str(home.resolve()), "code": str(ROOT), "separate": True, "from": "MIA_HOME"}
    assert (home / "config" / "config.json").is_file() and (home / "data" / "missions.json").is_file()
    assert (home / "logs" / "mia.log").is_file() and (home / "data" / "profiles").is_dir()
    after = _files(ROOT)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert changed == [], changed[:10]


def _a_mia(folder: Path) -> Path:
    """A small MIA in a folder: stores, a profile's file, config, a photo, a sealed file, a log and the lock."""
    (folder / "data" / "profiles" / "p1").mkdir(parents=True)
    (folder / "data" / "missions.json").write_text('{"missions": []}', encoding="utf-8")
    (folder / "data" / "profiles" / "p1" / "notes.json").write_text("MIA-SEALED-1:abc", encoding="utf-8")
    (folder / "data" / ".mia.lock").write_text("", encoding="utf-8")
    (folder / "config").mkdir()
    (folder / "config" / "config.json").write_text("{}", encoding="utf-8")
    (folder / "config" / "default_config.json").write_text("{}", encoding="utf-8")
    (folder / "trip_photos" / "t1").mkdir(parents=True)
    (folder / "trip_photos" / "t1" / "a.jpg").write_bytes(b"\xff\xd8" + b"x" * 5000)
    (folder / "logs").mkdir()
    (folder / "logs" / "mia.log").write_text("log", encoding="utf-8")
    return folder


def test_a_mia_is_copied_whole_and_checked_and_the_old_folder_is_untouched(tmp_path):
    old, new = _a_mia(tmp_path / "old"), tmp_path / "new"
    before = _files(old)
    files = move_home.files_to_copy(old)
    assert [str(f).replace("\\", "/") for f in files] == ["config/config.json", "data/missions.json",
                                                           "data/profiles/p1/notes.json", "trip_photos/t1/a.jpg"]
    assert [str(f).replace("\\", "/") for f in move_home.sealed(old, files)] == ["data/profiles/p1/notes.json"]
    done = move_home.copy(old, new)
    assert done["files"] == 4 and (new / "trip_photos" / "t1" / "a.jpg").read_bytes() == (old / "trip_photos" / "t1" / "a.jpg").read_bytes()
    assert not (new / "logs").exists() and not (new / "data" / ".mia.lock").exists()  # logs and the lock stay behind
    assert not (new / "config" / "default_config.json").exists()  # the defaults ship with the code
    assert _files(old) == before  # nothing in the old folder was changed, moved or deleted


def test_a_copy_is_refused_onto_a_folder_that_already_holds_a_mia_or_sits_inside_the_old_one(tmp_path):
    old = _a_mia(tmp_path / "old")
    with pytest.raises(move_home.MoveError, match="already in"):
        move_home.copy(old, old)
    with pytest.raises(move_home.MoveError, match="inside one of the folders"):
        move_home.copy(old, old / "data" / "new")
    taken = _a_mia(tmp_path / "taken")
    with pytest.raises(move_home.MoveError, match="already holds a MIA"):
        move_home.copy(old, taken)


def test_a_copy_that_does_not_match_its_original_is_reported_and_never_called_done(tmp_path, monkeypatch):
    old, new = _a_mia(tmp_path / "old"), tmp_path / "new"
    real = move_home.shutil.copy2

    def torn(src, dst):
        """A copy that loses the end of the photo."""
        real(src, dst)
        if str(dst).endswith("a.jpg"):
            Path(dst).write_bytes(Path(dst).read_bytes()[:-10])
    monkeypatch.setattr(move_home.shutil, "copy2", torn)
    with pytest.raises(move_home.MoveError, match="didn't copy correctly"):
        move_home.copy(old, new)


def test_the_tool_stops_before_copying_sealed_files_to_a_system_that_cannot_open_them(tmp_path, monkeypatch, capsys):
    from core import at_rest, instance_lock

    old, new = _a_mia(tmp_path / "old"), tmp_path / "new"
    monkeypatch.setattr(data_root, "HOME", old)
    monkeypatch.setattr(at_rest, "status", lambda: {"sealing": False})
    monkeypatch.setattr(instance_lock, "acquire", lambda *a, **k: True)
    assert move_home.main([str(new)]) == 1 and not new.exists()
    assert "doesn't hold the key that opens them" in capsys.readouterr().out
    assert move_home.main([str(new), "--check"]) == 0 and not new.exists()
    assert move_home.main([str(new), "--sealed-ok"]) == 0 and (new / "data" / "missions.json").is_file()
    said = capsys.readouterr().out
    assert "Copied and checked 4 files" in said and "MIA_HOME" in said
    monkeypatch.setattr(instance_lock, "acquire", lambda *a, **k: False)
    assert move_home.main([str(tmp_path / "third"), "--sealed-ok"]) == 1
    assert "MIA is running" in capsys.readouterr().out
