"""
tools.offline_library
=======================

Her offline library from the command line (core/offline_library.py):

    python -m tools.offline_library list              # every pack she should have, by shelf: size, here or not
    python -m tools.offline_library sizes             # how big each set is, and the free space
    python -m tools.offline_library fetch essential   # queue a set (essential, standard, all) or pack keys, then run it
    python -m tools.offline_library run               # run what's waiting (one runner at a time)

The same rules as the Knowledge page's Fetch: only packs in her catalog, each checked against Kiwix's own hash, never
past the free-space floor. Run from the repository's root.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from core.actions import ActionError


def _context():
    """A context with this device's config and library, the way MIA has them."""
    from core.app_context import AppContext
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus
    from core.reference_library_manager import ReferenceLibraryManager

    context = AppContext(config=ConfigManager(), events=EventBus())
    context.reference_library = ReferenceLibraryManager(context)
    return context


def main(argv=None) -> int:
    """Runs list, sizes, fetch or run; 0 when it went as asked, 1 otherwise."""
    from core import offline_library as lib

    parser = argparse.ArgumentParser(description="MIA's offline library")
    parser.add_argument("command", choices=("list", "sizes", "fetch", "run"))
    parser.add_argument("what", nargs="*", help="for fetch: a set (essential, standard, all) or pack keys")
    args = parser.parse_args(argv)
    context = _context()
    root = Path(context.reference_library.root_path)
    catalog = lib.published(root)
    if args.command == "list":
        for row in lib.status(context, root, catalog):
            mark = "here" if row["here"] and not row["newer"] else ("newer" if row["newer"] else row["state"] or "-")
            print(f"{row['shelf'][:22]:<22} {row['set']:<9} {row['size_gb']:>7.2f} GB  {mark:<14} {row['key']}")
        return 0
    if args.command == "sizes":
        rows = lib.status(context, root, catalog)
        for which in ("essential", "standard", "all"):
            packs = [r for r in rows if lib.in_set(lib.Pack(r["key"], "", "", r["set"], ""), which)]
            print(f"{which:<10} {len(packs):>3} packs {sum(r['size_gb'] for r in packs):>8.1f} GB")
        print(f"free       {shutil.disk_usage(root).free / 1e9:.0f} GB in {root}")
        return 0
    if args.command == "fetch":
        sets = [w for w in args.what if w in ("essential", "standard", "all")]
        try:
            print(lib.describe(context, root, sets[0] if sets else "", [w for w in args.what if w not in sets]))
            lib.fetch(context, root, sets[0] if sets else "", [w for w in args.what if w not in sets], start=False)
        except ActionError as problem:
            print(problem)
            return 1
    result = lib.run_queue(context, root, catalog=catalog)
    print(result)
    return 0 if not result.get("failed") else 1


if __name__ == "__main__":
    sys.exit(main())
