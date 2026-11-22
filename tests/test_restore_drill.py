"""
tests.test_restore_drill
==========================

WP-09 (DEC-0259, REQ-SEC-037): the monthly restore drill restores the newest backup into a scratch folder and opens
every store in it, sealed ones through their key, passing only when all open, telling a failure at once; and the
nightly backup's second copy goes to the place he chose off the PC, kept by the same rule, a missing drive said and
never a failed backup.
"""
import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from core import at_rest, auto_backup, restore_drill


class _Config:
    """A config that keeps what it's given."""

    def __init__(self, **values):
        """Starts with these values."""
        self.values = dict(values)

    def get(self, key, default=None):
        """A value, or the default."""
        return self.values.get(key, default)

    def set(self, key, value):
        """Keeps a value."""
        self.values[key] = value

    def save(self):
        """Nothing to write."""


def _backup(path: Path, files: dict) -> Path:
    """A backup zip holding these data files (name -> text)."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"app": "M.I.A."}))
        for name, text in files.items():
            zf.writestr("data/" + name, text)
    return path


def test_a_backup_whose_stores_all_open_passes_sealed_ones_too(tmp_path):
    """Plain, sealed and line-sealed stores each open; the scratch folder is gone afterwards."""
    sealed = at_rest.seal(json.dumps([{"id": 1}]))
    line = at_rest.seal(json.dumps({"kind": "sign_in"}))
    backup = _backup(tmp_path / "mia_auto_2026-11-20.zip", {
        "settings_like.json": "{}", "profiles/p1/conversations.json": sealed, "security_log.jsonl": line + "\n",
        "notes.txt": "not a store"})
    result = restore_drill.drill(backup)
    assert result["passed"] and (result["files"], result["opened"]) == (3, 3) and result["failed"] == []
    assert not list(Path(__import__("tempfile").gettempdir()).glob("mia_restore_drill_*"))


def test_a_store_that_wont_open_fails_the_drill_and_names_it(tmp_path):
    """One sealed under a key that's gone, or damaged, fails it, named."""
    at_rest.use_key(bytes(32))
    lost = at_rest.seal(json.dumps([1]))
    at_rest.use_key(bytes(range(32)))
    backup = _backup(tmp_path / "mia_auto_2026-11-20.zip", {"good.json": "[]", "people.json": lost, "bad.json": "{oops"})
    result = restore_drill.drill(backup)
    assert not result["passed"] and result["opened"] == 1
    assert sorted(f["file"] for f in result["failed"]) == ["bad.json", "people.json"]


def test_the_drill_runs_monthly_on_the_newest_unlocked_backup_and_tells_a_failure(tmp_path, monkeypatch):
    """Due from 3 a.m. after 28 days; a passphrase-locked backup is never the one drilled; a failure is told at once,
    a pass only kept."""
    import core.web_backups as web_backups

    folder = tmp_path / "backups"
    folder.mkdir()
    _backup(folder / "mia_backup_2026-11-01_0900.zip", {"a.json": "[]"})
    _backup(folder / "mia_auto_2026-11-19.zip", {"a.json": "{broken"})
    (folder / "mia_backup_2026-11-21_0900.miabackup").write_bytes(b"locked")
    monkeypatch.setattr(web_backups, "folder", lambda context: folder)
    told = []
    context = SimpleNamespace(config=_Config(), notifications=SimpleNamespace(
        notify=lambda title, message, **kw: told.append((title, kw.get("always")))))
    assert restore_drill.due(context.config, datetime(2026, 11, 22, 3, 5))
    assert not restore_drill.due(context.config, datetime(2026, 11, 22, 1, 5))
    result = restore_drill.run(context, datetime(2026, 11, 22, 3, 5))
    assert result["backup"] == "mia_auto_2026-11-19.zip" and not result["passed"]
    assert told == [("This month's backup check failed", True)]
    assert context.config.get("backup.drill")["backup"] == "mia_auto_2026-11-19.zip"
    assert not restore_drill.due(context.config, datetime(2026, 12, 5, 3, 5))
    assert restore_drill.due(context.config, datetime(2026, 12, 21, 3, 5))
    assert "FAILED" in restore_drill.words(result) and restore_drill.words(None).startswith("No restore check")


def test_the_second_copy_goes_off_the_pc_and_a_missing_drive_is_said(tmp_path):
    """Copied whole to the chosen folder and rotated by the same rule; a drive that isn't there is kept as a problem."""
    made = tmp_path / "mia_auto_2026-11-22.zip"
    made.write_bytes(b"PK backup")
    offsite = tmp_path / "drive" / "MIA Backups"
    offsite.mkdir(parents=True)
    (offsite / "mia_auto_2025-01-01.zip").write_bytes(b"old")
    config = _Config(**{"backup.offsite_folder": str(offsite)})
    done = auto_backup.copy_offsite(config, made, date(2026, 11, 22))
    assert done == {"copied": str(offsite), "removed": 1}
    assert sorted(p.name for p in offsite.iterdir()) == ["mia_auto_2026-11-22.zip"]
    assert config.get("backup.offsite_last") == "2026-11-22" and config.get("backup.offsite_problem") == ""
    assert auto_backup.copy_offsite(_Config(), made, date(2026, 11, 22)) == {"skipped": "no second place chosen"}


def test_a_drive_that_isnt_plugged_in_is_said_not_a_failed_backup(tmp_path, monkeypatch):
    """The chosen folder's drive isn't there: the problem is kept for the Backups section, nothing raised."""
    made = tmp_path / "mia_auto_2026-11-22.zip"
    made.write_bytes(b"PK backup")
    real_exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda self: False if str(self).startswith(str(tmp_path / "gone")) else real_exists(self))
    monkeypatch.setattr(Path, "anchor", property(lambda self: str(tmp_path / "gone")))
    away = _Config(**{"backup.offsite_folder": str(tmp_path / "gone" / "MIA Backups")})
    missing = auto_backup.copy_offsite(away, made, date(2026, 11, 22))
    assert "isn't connected" in missing["error"] and away.get("backup.offsite_problem").startswith("2026-11-22")


def test_the_backups_section_says_the_second_copy_and_the_last_drill(tmp_path, monkeypatch):
    """Settings, Backups and the backup tool read both from the status."""
    from core import web_backups

    config = _Config(**{"backup.folder": str(tmp_path), "backup.offsite_folder": "E:\\MIA Backups",
                        "backup.drill": {"at": "2026-11-22T03:05:00", "backup": "mia_auto_2026-11-21.zip", "files": 40,
                                         "opened": 40, "failed": [], "passed": True}})
    info = web_backups.status(SimpleNamespace(config=config))
    assert info["offsite"]["folder"] == "E:\\MIA Backups"
    assert info["drill"]["said"].startswith("Restore check 2026-11-22: mia_auto_2026-11-21.zip came back whole")
