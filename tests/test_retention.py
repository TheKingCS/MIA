"""Tests for LS-03: the retention registry (DEC-0286, core/retention.py) decides what syncs, and a field changed on two
devices keeps its losing value in the change history with one note that quotes no value (DEC-0285, core/sync.py)."""
import json
import re
from pathlib import Path

from core import retention, sync

ROOT = Path(__file__).resolve().parent.parent


def test_every_data_file_mia_names_is_in_the_retention_registry():
    """A `.json` or `.jsonl` file named in core/ or modules/ has a class, a keeping time, an end and a sync answer."""
    named = set()
    for path in list((ROOT / "core").glob("*.py")) + list((ROOT / "modules").glob("*/*.py")):
        named |= set(re.findall(r"\"([a-z0-9_-]+\.jsonl?)\"", path.read_text(encoding="utf-8")))
    assert sorted(named - set(retention.REGISTRY)) == []


def test_each_entry_says_its_class_keeping_and_end_and_sync_reads_it():
    """Classes are the known six, every entry says how long and what then, and sync's own list comes from here."""
    assert all(r.cls in retention.CLASSES and r.keep and r.end for r in retention.REGISTRY.values())
    assert sync.NEVER_SYNC == {n for n, r in retention.REGISTRY.items() if not r.syncs}
    assert set(sync.PC_ONLY) <= sync.NEVER_SYNC
    assert not sync.syncable("phone_link.json") and not sync.syncable("activity.json")
    assert sync.syncable("bills.json") and sync.syncable("life_events.jsonl")
    assert retention.of("changes.jsonl").keep.startswith("30 days")


def test_a_field_both_devices_changed_is_noted_by_its_path_and_the_rest_merges():
    """Only a field changed on both sides since the base is a conflict; its path names the record by id."""
    base = {"bills": [{"id": "b1", "name": "Power", "amount": 50, "note": ""}]}
    here = {"bills": [{"id": "b1", "name": "Power", "amount": 60, "note": "paid early"}]}
    there = {"bills": [{"id": "b1", "name": "Electric", "amount": 70, "note": ""}]}
    with sync.conflicts() as lost:
        merged = sync.merge_json(base, here, there, prefer_local=True)
    assert merged == {"bills": [{"id": "b1", "name": "Electric", "amount": 60, "note": "paid early"}]}
    assert lost == [("bills", "id=b1", "amount")]
    with sync.conflicts() as none:
        sync.merge_json(base, here, base, prefer_local=False)
    assert none == []


def test_the_losing_copy_goes_to_the_change_history_and_the_note_quotes_no_value(tmp_path, monkeypatch):
    """The losing side's file is kept as a change (so undo brings it back); the note names the file and field."""
    from core import change_history

    monkeypatch.setattr(change_history, "folder_for", lambda pid: tmp_path / "history")
    data = tmp_path / "bills.json"
    data.write_text(json.dumps({"bills": [{"id": "b1", "amount": 60}]}), encoding="utf-8")
    losing = json.dumps({"bills": [{"id": "b1", "amount": 70}]}).encode("utf-8")
    note = sync.keep_loser("p1", data, losing, [("bills", "id=b1", "amount")], local_won=True)
    assert note == ("bills: bills / id=b1 / amount changed on both devices; this device's was kept, and the other is in "
                    "your change history for 30 days.")
    assert "70" not in note and "60" not in note
    kept = change_history.entries("p1")
    assert len(kept) == 1 and kept[0].label == "sync_conflict"
