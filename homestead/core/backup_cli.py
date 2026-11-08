"""
MIA Homestead — Backup CLI
v0.1

Usage:
    python3 core/backup_cli.py --db mia_homestead.db --snapshot "before pH target change"
    python3 core/backup_cli.py --db mia_homestead.db --list
    python3 core/backup_cli.py --db mia_homestead.db --restore 3
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.backup_manager import BackupManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--snapshot", help="Create a snapshot with this label")
    parser.add_argument("--reason", help="Optional reason for the snapshot")
    parser.add_argument("--list", action="store_true", help="List all snapshots")
    parser.add_argument("--restore", type=int, help="Restore a snapshot by id")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    mgr = BackupManager(conn)

    if args.snapshot:
        snapshot_id = mgr.create_snapshot(args.snapshot, reason=args.reason)
        print(f"Snapshot #{snapshot_id} created.")
        return

    if args.list:
        snapshots = mgr.list_snapshots()
        if not snapshots:
            print("No snapshots yet.")
            return
        for s in snapshots:
            print(f"#{s['id']}  {s['created_at']}  {s['label']}"
                  f"{'  [auto pre-update]' if s['is_auto_pre_update'] else ''}")
            if s['reason']:
                print(f"      reason: {s['reason']}")
        return

    if args.restore is not None:
        confirm = input(f"Restore snapshot #{args.restore}? This overwrites current config files "
                         f"and control-parameter tables (dosing limits, target overrides, device "
                         f"pairings, maintenance schedules) — NOT history/alerts/yield data. [y/N]: ")
        if confirm.strip().lower() != "y":
            print("Cancelled.")
            return
        result = mgr.restore_snapshot(args.restore)
        print("Restored.")
        print(f"  Files: {result['restored_files']}")
        print(f"  DB tables: {result['restored_tables']}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
