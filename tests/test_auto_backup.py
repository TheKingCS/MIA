"""
tests.test_auto_backup
========================

The nightly backup (core/auto_backup.py): when it is due, which automatic
backups the rotation keeps (and that a hand-made one is never touched),
and a real round trip: stores written, backed up at night, changed, then
restored to what the backup held.
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import core.backup_manager as backup_module
from core import auto_backup


class _Config:
    """A config of plain values, with the backups folder in the test's own folder."""

    def __init__(self, folder):
        """Starts with only the backups folder set."""
        self.values = {"backup.folder": str(folder)}

    def get(self, key, default=None):
        """A value, or the default."""
        return self.values.get(key, default)

    def set(self, key, value):
        """Sets a value."""
        self.values[key] = value

    def save(self):
        """Nothing to write in a test."""


def test_tonight_s_backup_is_due_once_after_two_and_never_when_turned_off(tmp_path):
    config = _Config(tmp_path)
    assert not auto_backup.due(config, datetime(2026, 11, 10, 1, 30))
    assert auto_backup.due(config, datetime(2026, 11, 10, 2, 5))
    config.set("backup.auto_last", "2026-11-10")
    assert not auto_backup.due(config, datetime(2026, 11, 10, 23, 0))
    assert auto_backup.due(config, datetime(2026, 11, 11, 3, 0))
    config.set("backup.auto_enabled", False)
    assert not auto_backup.due(config, datetime(2026, 11, 11, 3, 0))


def test_the_rotation_keeps_a_week_of_nights_and_one_a_week_for_four_weeks():
    today = date(2026, 11, 30)
    names = [f"mia_auto_{date.fromordinal(today.toordinal() - n).isoformat()}.zip" for n in range(60)]
    kept = auto_backup.keep(names + ["mia_backup_2026-01-01_0900.zip"], today)
    nights = {f"mia_auto_{date.fromordinal(today.toordinal() - n).isoformat()}.zip" for n in range(7)}
    assert nights <= kept and len(kept) == 7 + 4
    assert "mia_backup_2026-01-01_0900.zip" not in kept  # never in question: run() only removes mia_auto_ files


def test_a_night_s_backup_rotates_only_automatic_ones_and_says_a_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_module, "_build_zip_bytes", lambda config=None: b"PK\x05\x06" + b"\0" * 18)
    folder = tmp_path / "backups"
    folder.mkdir()
    (folder / "mia_backup_2025-01-01_0900.zip").write_bytes(b"by hand")
    (folder / "mia_auto_2025-01-01.zip").write_bytes(b"old")
    context = SimpleNamespace(config=_Config(folder))
    done = auto_backup.run(context, datetime(2026, 11, 10, 2, 10))
    assert done == {"made": "mia_auto_2026-11-10.zip", "removed": 1}
    assert sorted(p.name for p in folder.iterdir()) == ["mia_auto_2026-11-10.zip", "mia_backup_2025-01-01_0900.zip"]
    assert context.config.get("backup.auto_last") == "2026-11-10" and context.config.get("backup.auto_problem") == ""

    def _full_disk(config=None):
        """The disk is full tonight."""
        raise OSError("No space left on device")

    monkeypatch.setattr(backup_module, "_build_zip_bytes", _full_disk)
    failed = auto_backup.run(context, datetime(2026, 11, 11, 2, 10))
    assert "No space left" in failed["error"] and context.config.get("backup.auto_problem").startswith("2026-11-11")
    assert not auto_backup.due(context.config, datetime(2026, 11, 11, 2, 15))  # tried once a night, not every tick


def test_a_nightly_backup_restores_the_stores_it_held(tmp_path, monkeypatch):
    """Round trip: what the stores held at night comes back after they were changed."""
    data, cfg = tmp_path / "data", tmp_path / "config" / "config.json"
    data.mkdir()
    cfg.parent.mkdir()
    cfg.write_text('{"a": 1}', encoding="utf-8")
    (data / "notes.json").write_text('[{"id": "n1"}]', encoding="utf-8")
    monkeypatch.setattr(backup_module, "_DATA_DIR", data)
    monkeypatch.setattr(backup_module, "_CONFIG_FILE", cfg)
    folder = tmp_path / "backups"
    context = SimpleNamespace(config=_Config(folder))
    made = auto_backup.run(context, datetime(2026, 11, 10, 2, 10))["made"]
    (data / "notes.json").write_text("[]", encoding="utf-8")
    assert backup_module.restore_backup(folder / made).passed
    assert (data / "notes.json").read_text(encoding="utf-8") == '[{"id": "n1"}]'
