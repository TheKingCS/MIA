"""
tools.vault_captions
======================

Describes the photos this PC keeps for the phone, so they can be found by what's in them
(core/vault_captions.py). MIA's daily check starts `run` between 2 and 5 at night.

    .venv\\Scripts\\python -m tools.vault_captions run                 a night's worth now
    .venv\\Scripts\\python -m tools.vault_captions run --minutes 5     a few minutes' worth
    .venv\\Scripts\\python -m tools.vault_captions status              how many are described, per person's vault
"""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str]) -> int:
    from core import vault_captions as vc
    from core.memory_vault import VaultShelf

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="tools.vault_captions")
    parser.add_argument("command", choices=("run", "status"))
    parser.add_argument("--minutes", type=float, default=vc.NIGHT_SECONDS / 60)
    args = parser.parse_args(argv)
    for folder in vc.shelves():
        shelf = VaultShelf(folder)
        if args.command == "run":
            done = vc.caption_shelf(shelf, seconds=args.minutes * 60)
            print(f"{folder.parent.name}: {done} described", flush=True)
        photos = [e for e in shelf.index.values() if e.get("kind", "photo") == "photo"]
        print(f"{folder.parent.name}: {sum(1 for e in photos if e.get('caption'))} of {len(photos)} photos described",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
