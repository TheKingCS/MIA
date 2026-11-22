"""
tests.test_migration
======================

FW-07a (REQ-CMP-002/003, REQ-IMP-009): the move's manifest records every store's count and a hash of what it holds
(so a store re-sealed under a new key still matches), a sample of his files and his programs with their answers on
MIA OS; comparing before and after names whatever didn't come across, a deliberately damaged record among them; and
it says nothing a store holds.
"""
import json
from pathlib import Path

from core import at_rest, migration


def _data(root: Path) -> Path:
    """A small data folder: a plain store, a sealed one, a line-sealed log, a person's folder, and the key folder."""
    (root / "profiles" / "p1").mkdir(parents=True)
    (root / ".keys").mkdir()
    (root / ".keys" / "data_key.json").write_text("{}", encoding="utf-8")
    (root / "inventory_items.json").write_text(json.dumps([{"id": 1, "name": "drill"}, {"id": 2, "name": "saw"}]),
                                              encoding="utf-8")
    (root / "profiles" / "p1" / "conversations.json").write_text(
        at_rest.seal(json.dumps({"conversations": [{"id": "c1", "said": "a private line"}]})), encoding="utf-8")
    (root / "profiles" / "p1" / "corrections.jsonl").write_text(
        at_rest.seal(json.dumps({"at": "2026-11-01", "kind": "fix"})) + "\n", encoding="utf-8")
    return root


def test_every_store_is_counted_and_hashed_by_what_it_holds_never_the_key(tmp_path):
    """Sealed or not, a store's records are counted and hashed; the key folder isn't a store that moves."""
    found = migration.stores(_data(tmp_path / "data"))
    assert set(found) == {"inventory_items.json", "profiles/p1/conversations.json", "profiles/p1/corrections.jsonl"}
    assert found["inventory_items.json"]["count"] == 2 and found["profiles/p1/conversations.json"]["count"] == 1
    assert "private line" not in json.dumps(found)


def test_a_store_resealed_under_a_new_key_or_in_another_order_still_matches(tmp_path):
    """The hash is of the records, in a canonical order: a new key or a different order changes nothing."""
    path = tmp_path / "inventory_items.json"
    path.write_text(json.dumps([{"name": "drill", "id": 1}, {"id": 2, "name": "saw"}]), encoding="utf-8")
    first = migration.store_entry(path)
    path.write_text(json.dumps([{"id": 2, "name": "saw"}, {"id": 1, "name": "drill"}]), encoding="utf-8")
    assert migration.store_entry(path) == first
    sealed = tmp_path / "conversations.json"
    sealed.write_text(at_rest.seal(json.dumps([{"a": 1}])), encoding="utf-8")
    before = migration.store_entry(sealed)
    at_rest.use_key(bytes(range(1, 33)))
    try:
        sealed.write_text(at_rest.seal(json.dumps([{"a": 1}])), encoding="utf-8")
        assert migration.store_entry(sealed) == before
    finally:
        at_rest.use_key(bytes(range(32)))


def test_a_damaged_record_a_lost_store_and_a_changed_file_are_each_named(tmp_path):
    """The plan's acceptance: everything matched passes; one damaged record, one store gone, one file changed fail."""
    data = _data(tmp_path / "data")
    home = tmp_path / "home"
    (home / "Documents").mkdir(parents=True)
    (home / "Documents" / "plans.txt").write_text("greenhouse plans", encoding="utf-8")
    before = {"stores": migration.stores(data), "files": migration.sample_files([home / "Documents"], home)}
    assert migration.compare(before, before)["ok"]
    (data / "inventory_items.json").write_text(json.dumps([{"id": 1, "name": "drill"}, {"id": 2, "name": "SAW"}]),
                                               encoding="utf-8")
    (data / "profiles" / "p1" / "corrections.jsonl").unlink()
    (home / "Documents" / "plans.txt").write_text("greenhouse plan", encoding="utf-8")
    after = {"stores": migration.stores(data), "files": migration.sample_files([home / "Documents"], home)}
    found = migration.compare(before, after)
    assert not found["ok"]
    assert found["stores"]["changed"] == [{"store": "inventory_items.json", "why": "the same count, different contents"}]
    assert found["stores"]["missing"] == ["profiles/p1/corrections.jsonl"]
    assert found["files"]["changed"] == ["Documents/plans.txt"]


def test_a_store_that_wont_open_after_the_move_is_a_mismatch(tmp_path):
    """Restored but sealed under a key not held there: unreadable, named."""
    data = _data(tmp_path / "data")
    before = {"stores": migration.stores(data)}
    at_rest.use_key(bytes(32))
    try:
        after = {"stores": migration.stores(data)}
    finally:
        at_rest.use_key(bytes(range(32)))
    found = migration.compare(before, after)
    assert "profiles/p1/conversations.json" in found["stores"]["unreadable"] and not found["ok"]


def test_his_programs_each_have_an_answer_on_mia_os_matched_as_whole_words():
    """REQ-CMP-003: known programs get their answer; an unknown one is his to decide; "git" isn't "Digital"."""
    rows = {p["name"]: p["answer"] for p in migration.programs(
        ["Microsoft Edge", "Steam", "Git", "Digital Photo Professional", "Notepad++", "Microsoft .NET Runtime"])}
    assert rows["Microsoft Edge"].startswith("Edge for Linux") and rows["Steam"].startswith("Steam")
    assert rows["Git"] == "Git (in the image)" and rows["Notepad++"].startswith("Kate")
    assert rows["Digital Photo Professional"].startswith("no known answer")
    assert rows["Microsoft .NET Runtime"].startswith("not needed")


def test_the_tool_writes_beside_the_backups_and_compare_stops_on_a_mismatch(tmp_path, monkeypatch, capsys):
    """write puts the manifest where it's told; compare exits 1 on a mismatch and says STOP."""
    from tools import migration_manifest

    monkeypatch.setattr(migration, "manifest", lambda **kw: {"version": 1, "stores": {"a.json": {"count": 1, "hash": "x"}},
                                                             "files": [], "programs": []})
    out = tmp_path / "before.json"
    assert migration_manifest.main(["write", "--out", str(out)]) == 0 and out.exists()
    after = tmp_path / "after.json"
    after.write_text(json.dumps({"stores": {}, "files": []}), encoding="utf-8")
    assert migration_manifest.main(["compare", str(out), str(after)]) == 1
    assert "STOP" in capsys.readouterr().out
    assert migration_manifest.main(["compare", str(out), str(out)]) == 0
