"""Backups from the web's Settings (core/web_backups.py) and by voice (core/assistant_backup_actions.py): the PC
owner's backups folder, the newest backups, Back Up Now with or without a passphrase, and the status said aloud."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import core.backup_manager as backup_module
from core.web_backups import age_words, make, size_words, status


def test_the_words_for_age_and_size():
    assert [age_words(d) for d in (None, 0, 1, 12)] == ["never", "today", "yesterday", "12 days ago"]
    assert size_words(500) == "1 KB" and size_words(15_000_000) == "14.3 MB"


def test_a_backup_is_made_into_the_folder_and_listed(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_module, "_build_zip_bytes", lambda config=None: b"PK\\x05\\x06" + b"\\0" * 18)
    context = SimpleNamespace(config=SimpleNamespace(get=lambda key, default=None: str(tmp_path / "b") if key == "backup.folder" else default))
    assert status(context)["count"] == 0 and status(context)["last"] == "never"
    done = make(context, "", datetime(2026, 11, 7, 21, 30))
    assert done == {"made": "mia_backup_2026-11-07_2130.zip", "locked": False}
    locked = make(context, "correct horse", datetime(2026, 11, 7, 21, 31))
    assert locked["made"].endswith(".miabackup") and locked["locked"]
    info = status(context)
    assert info["count"] == 2 and info["last"] == "today" and {b["locked"] for b in info["backups"]} == {True, False}


def test_the_status_by_voice_is_the_owners(tmp_path, monkeypatch):
    import core.person_settings as person_settings
    from core.assistant_backup_actions import _status

    context = SimpleNamespace(config=SimpleNamespace(get=lambda key, default=None: str(tmp_path / "b") if key == "backup.folder" else default))
    monkeypatch.setattr(person_settings, "person_id", lambda ctx: "me")
    monkeypatch.setattr(person_settings, "_is_first_account", lambda ctx, pid: False)
    assert _status(context, {}) == "Backups are the PC owner's."
    monkeypatch.setattr(person_settings, "_is_first_account", lambda ctx, pid: True)
    assert _status(context, {}).startswith("There are no backups in")
