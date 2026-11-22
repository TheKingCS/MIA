"""
tools.migration_manifest
==========================

The move's checklist on the command line (FW-07a; core/migration.py). Before the move, on Windows:

    python -m tools.migration_manifest write

records every store's count and content hash, a sample of his files and his programs (each with its answer on MIA
OS) into the backups folder, beside the backup that goes across. After the restore on MIA OS, the same command there,
then

    python -m tools.migration_manifest compare BEFORE.json AFTER.json

says what matched and names anything that didn't (exit code 1 then: the move stops at the first mismatch, MV-01).
`programs` prints just his programs and their answers. Hashes and names only: nothing a store holds is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def _default_out() -> Path:
    """Beside his backups (core/web_backups.folder), named for today."""
    from core.config_manager import ConfigManager
    from core.web_backups import folder

    context = type("Context", (), {"config": ConfigManager()})()
    return folder(context) / f"mia_migration_manifest_{datetime.now():%Y-%m-%d_%H%M}.json"


def main(argv: Optional[list] = None) -> int:
    """Runs one of write, compare or programs; 0 on success (and a compare that matched), 1 on a mismatch."""
    from core import migration

    parser = argparse.ArgumentParser(prog="python -m tools.migration_manifest", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="what", required=True)
    w = sub.add_parser("write", help="record the stores, a sample of files and the programs")
    w.add_argument("--out", type=Path, default=None)
    w.add_argument("--sample", type=int, default=migration.SAMPLE)
    c = sub.add_parser("compare", help="compare a manifest from before the move with one from after")
    c.add_argument("before", type=Path)
    c.add_argument("after", type=Path)
    sub.add_parser("programs", help="his Windows programs and each one's answer on MIA OS")
    args = parser.parse_args(argv)

    if args.what == "write":
        out = migration.write(args.out or _default_out(), migration.manifest(sample=args.sample))
        data = json.loads(out.read_text(encoding="utf-8"))
        print(f"Written: {out}\n{len(data['stores'])} stores, {len(data['files'])} sample files, "
              f"{len(data['programs'])} programs.")
        return 0
    if args.what == "programs":
        for p in migration.programs():
            print(f"{p['name']}: {p['answer']}")
        return 0
    found = migration.compare(json.loads(args.before.read_text(encoding="utf-8")),
                              json.loads(args.after.read_text(encoding="utf-8")))
    s, f = found["stores"], found["files"]
    print(f"Stores: {s['matched']} matched, {len(s['changed'])} changed, {len(s['missing'])} missing, "
          f"{len(s['unreadable'])} unreadable. Files: {f['matched']} matched, {len(f['changed'])} changed, "
          f"{len(f['missing'])} missing.")
    for c in s["changed"]:
        print(f"  CHANGED {c['store']}: {c['why']}")
    for name in s["missing"] + s["unreadable"]:
        print(f"  MISSING OR UNREADABLE {name}")
    for path in f["changed"] + f["missing"]:
        print(f"  FILE {path}")
    print("Everything came across." if found["ok"] else "STOP: something didn't come across whole.")
    return 0 if found["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
