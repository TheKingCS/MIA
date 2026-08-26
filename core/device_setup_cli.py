"""
MIA Homestead — Device Setup CLI
v0.1

Designed to be usable by someone who has never seen this codebase.
No flags to memorize beyond --db (which a real deployment would bake
into a default so even that isn't needed).

Usage:
    python3 core/device_setup_cli.py --db mia_homestead.db
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from core.device_registry import DeviceRegistry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    registry = DeviceRegistry(conn)

    print("\n=== MIA Homestead — Device Setup ===\n")

    unpaired = registry.list_unpaired()
    if unpaired:
        print(f"{len(unpaired)} device(s) plugged in and waiting for you:\n")
        for i, d in enumerate(unpaired, 1):
            print(f"  {i}. Device {d['hardware_id'][:8]}... "
                  f"(requested role: {d['requested_role'] or 'not specified'})")
        print()

    print("What do you want to set up?\n")
    roles = registry.list_roles()
    for i, r in enumerate(roles, 1):
        print(f"  {i}. {r['display_name']}")
    print(f"  {len(roles) + 1}. Nothing right now, just show me what's already set up")
    print()

    choice = input("Enter a number: ").strip()
    try:
        idx = int(choice) - 1
    except ValueError:
        print("Please enter a number.")
        return

    if idx == len(roles):
        paired = registry.list_paired()
        if not paired:
            print("\nNothing paired yet.")
        else:
            print(f"\n{len(paired)} device(s) currently set up:")
            for p in paired:
                print(f"  - {p['role']} (cell {p['cell_id']})")
        return

    if idx < 0 or idx >= len(roles):
        print("That's not one of the options.")
        return

    role = roles[idx]["role"]
    print("\n" + registry.get_setup_instructions(role))
    print("\nOnce it's plugged in, this system checks for it automatically.")
    print("Come back to this menu if it doesn't show as connected after a minute.\n")


if __name__ == "__main__":
    main()
