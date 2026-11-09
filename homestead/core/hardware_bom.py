"""
MIA Homestead — Hardware BOM Export
v0.1

Usage:
    python3 core/hardware_bom.py --db mia_homestead.db
    python3 core/hardware_bom.py --db mia_homestead.db --by-module
    python3 core/hardware_bom.py --db mia_homestead.db --export bom.md
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hardware_registry import HardwareRegistry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--by-module", action="store_true", help="Group by module instead of aggregating by item")
    parser.add_argument("--export", help="Write to a markdown file instead of printing")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    bom = HardwareRegistry.render_bom(conn, group_by_module=args.by_module)

    if args.export:
        content = f"# MIA Homestead — Hardware Needs List\n\nAuto-generated from every module's declared requirements.\n\n```\n{bom}\n```\n"
        Path(args.export).write_text(content)
        print(f"Exported to {args.export}")
    else:
        print(bom)


if __name__ == "__main__":
    main()
