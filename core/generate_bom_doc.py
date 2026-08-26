"""
MIA Homestead — Live Hardware BOM Document Generator
v0.1

Regenerates docs/HARDWARE_BOM_LIVE.md from hardware_requirements every
startup — this is the running total, distinct from
docs/HARDWARE_BOM_CURRENT.md (that one is hand-researched pricing
notes/sourcing, which can't be auto-generated). This fixes a real gap
found during a pass checking exactly this: HARDWARE_BOM_CURRENT.md had
hand-typed totals that could silently drift from the real registry.
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hardware_registry import HardwareRegistry

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "HARDWARE_BOM_LIVE.md"


def generate(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    bom = HardwareRegistry.render_bom(conn, group_by_module=False)
    return (
        f"# MIA Homestead — Live Hardware BOM\n\n"
        f"**Auto-generated {datetime.utcnow().isoformat()}Z from `hardware_requirements` — "
        f"never hand-edit this file, it will be overwritten every startup.**\n\n"
        f"For pricing research/sourcing notes (not auto-derivable), see "
        f"`docs/HARDWARE_BOM_CURRENT.md`.\n\n"
        f"```\n{bom}\n```\n"
    )


def generate_and_write(db_path: str) -> str:
    """The version main.py should actually call — generate() alone
    only returns a string, it doesn't touch disk."""
    content = generate(db_path)
    OUTPUT_PATH.write_text(content)
    return content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    args = parser.parse_args()
    content = generate(args.db)
    OUTPUT_PATH.write_text(content)
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
