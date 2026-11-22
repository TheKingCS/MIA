"""
os/poc/vm/move_rehearsal.py
=============================

FW-07b's rehearsal of the move, on synthetic data (docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md FW-07; REQ-IMP-002,
REQ-IMP-009): stores laid out the way MIA on Windows leaves them, the manifest recorded (core/migration.py), a real
backup made and restored by MIA's own backup code (core/backup_manager.py) into a fresh data folder, the manifest
recorded again and compared: every store must match. Then one record is changed by hand and the compare must name it.

Run inside the MIA OS image by the VM test (.github/workflows/mia-os-vm.yml), with the image's own Python, and on any
machine by tests/test_move_rehearsal.py. Nothing of his is touched: everything is under the folder it's given.

    python os/poc/vm/move_rehearsal.py <repository> <scratch folder>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def synthetic(data: Path) -> None:
    """Stores as MIA on Windows leaves them: a household list, a person's conversations and an appended log."""
    (data / "profiles" / "p1").mkdir(parents=True, exist_ok=True)
    (data / "inventory_items.json").write_text(json.dumps([{"id": i, "name": f"tool {i}"} for i in range(50)]),
                                              encoding="utf-8")
    (data / "profiles" / "p1" / "conversations.json").write_text(
        json.dumps({"conversations": [{"id": f"c{i}", "said": "synthetic"} for i in range(5)]}), encoding="utf-8")
    (data / "profiles" / "p1" / "corrections.jsonl").write_text(
        "".join(json.dumps({"n": i}) + "\n" for i in range(20)), encoding="utf-8")


def rehearse(scratch: Path) -> dict:
    """The whole rehearsal under `scratch`: {matched, caught}. AssertionError when the move or the compare fails."""
    from core import backup_manager as bm
    from core import migration

    before, after = scratch / "windows" / "data", scratch / "mia-os" / "data"
    synthetic(before)
    (scratch / "mia-os").mkdir(parents=True, exist_ok=True)
    (scratch / "windows" / "config.json").write_text("{}", encoding="utf-8")
    saved = (bm._DATA_DIR, bm._CONFIG_FILE)
    try:
        bm._DATA_DIR, bm._CONFIG_FILE = before, scratch / "windows" / "config.json"
        first = migration.stores(before)
        made = bm.create_backup(scratch / "move.zip")
        assert made.passed, made.errors
        bm._DATA_DIR, bm._CONFIG_FILE = after, scratch / "mia-os" / "config.json"
        done = bm.restore_backup(scratch / "move.zip")
        assert done.passed, done.errors
    finally:
        bm._DATA_DIR, bm._CONFIG_FILE = saved
    found = migration.compare({"stores": first}, {"stores": migration.stores(after)})
    assert found["ok"] and found["stores"]["matched"] == len(first) == 3, found
    path = after / "inventory_items.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    records[7]["name"] = "changed after the move"
    path.write_text(json.dumps(records), encoding="utf-8")
    damaged = migration.compare({"stores": first}, {"stores": migration.stores(after)})
    assert not damaged["ok"] and [c["store"] for c in damaged["stores"]["changed"]] == ["inventory_items.json"], damaged
    return {"matched": found["stores"]["matched"], "caught": damaged["stores"]["changed"][0]["store"]}


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[1])
    result = rehearse(Path(sys.argv[2]))
    print(f"The move rehearsed: {result['matched']} stores matched after the restore; the damaged record in "
          f"{result['caught']} was caught.")
